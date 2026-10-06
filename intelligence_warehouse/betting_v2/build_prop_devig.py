#!/usr/bin/env python3
from __future__ import annotations

import bisect
import glob
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
OUT = OUT_DIR / "PROP_V2_DEVIG.json"
PUBLIC = ROOT / "commercial_web" / "public" / "prop_v2_devig.json"
DIST = ROOT / "commercial_web" / "dist" / "prop_v2_devig.json"
SPORTS = ("NFL", "NBA", "NHL", "MLB")
RAW_MARKET_SPORTS = ("NFL", "NBA", "NHL", "MLB")
MAX_ARCHIVE_AGE_MINUTES = 30.0
CURRENT_MAX_QUOTE_AGE_MINUTES = 15.0
MIN_PAIRED_BOOKS_FOR_MODEL = 2
MIN_REASONABLE_OVERROUND = 0.98
MAX_REASONABLE_OVERROUND = 1.15


def clean(value):
    return str(value or "").strip()


def num(value):
    try:
        x = float(value)
        return None if math.isnan(x) else x
    except Exception:
        return None


def player_key(value):
    return re.sub(r"[^a-z0-9]+", "", clean(value).lower())


def implied_array(odds):
    o = pd.to_numeric(odds, errors="coerce").astype(float)
    valid = o.abs().ge(100)
    p = np.where(o > 0, 100.0 / (o + 100.0), o.abs() / (o.abs() + 100.0))
    return pd.Series(np.where(valid, p, np.nan), index=o.index)


def file_timestamp(path):
    m = re.search(r"_(\d{8}T\d{6}Z)\.csv$", str(path))
    if not m:
        return pd.NaT
    return pd.to_datetime(m.group(1), format="%Y%m%dT%H%M%SZ", utc=True, errors="coerce")


def identity(event_id, player, market, line, side):
    line = num(line)
    if line is None:
        return ""
    return "|".join([
        clean(event_id),
        player_key(player),
        clean(market).upper(),
        f"{line:.4f}",
        clean(side).upper(),
    ])


def fair_map(path, max_quote_age_minutes=None):
    try:
        d = pd.read_csv(path, low_memory=False)
    except Exception:
        return {}
    required = {"event_id", "player", "market_subtype", "side", "line", "sportsbook", "price_american"}
    if not required.issubset(d.columns):
        return {}

    columns = list(required)
    if "captured_at" in d.columns:
        columns.append("captured_at")
    x = d[columns].copy()
    x["pk"] = x["player"].map(player_key)
    x["market"] = x["market_subtype"].astype(str).str.upper()
    x["side"] = x["side"].astype(str).str.upper()
    x["line_num"] = pd.to_numeric(x["line"], errors="coerce").round(4)
    x["implied"] = implied_array(x["price_american"])

    if "captured_at" in x.columns:
        x["_captured"] = pd.to_datetime(x["captured_at"], errors="coerce", utc=True)
        if max_quote_age_minutes is not None:
            now = pd.Timestamp.now(tz="UTC")
            age_minutes = (now - x["_captured"]).dt.total_seconds() / 60.0
            x = x[
                x["_captured"].notna()
                & age_minutes.ge(0)
                & age_minutes.le(float(max_quote_age_minutes))
            ].copy()

    x = x[
        x["side"].isin(["OVER", "UNDER"])
        & x["line_num"].notna()
        & x["implied"].notna()
    ]
    if x.empty:
        return {}

    keys = ["event_id", "pk", "market", "line_num", "sportsbook"]
    if "_captured" in x.columns:
        x = x.sort_values("_captured")
    x = x.drop_duplicates(keys + ["side"], keep="last")

    pivot = x.pivot_table(index=keys, columns="side", values="implied", aggfunc="last")
    if "OVER" not in pivot.columns or "UNDER" not in pivot.columns:
        return {}
    pivot = pivot.dropna(subset=["OVER", "UNDER"]).copy()
    if pivot.empty:
        return {}

    denom = pivot["OVER"] + pivot["UNDER"]
    pivot = pivot[
        denom.ge(MIN_REASONABLE_OVERROUND)
        & denom.le(MAX_REASONABLE_OVERROUND)
    ].copy()
    if pivot.empty:
        return {}

    denom = pivot["OVER"] + pivot["UNDER"]
    pivot["OVER_FAIR"] = pivot["OVER"] / denom
    pivot["UNDER_FAIR"] = pivot["UNDER"] / denom
    pivot = pivot.reset_index()

    rows = []
    for side in ("OVER", "UNDER"):
        y = pivot[keys].copy()
        y["side"] = side
        y["fair_probability"] = pivot[f"{side}_FAIR"]
        rows.append(y)
    fair = pd.concat(rows, ignore_index=True)
    grouped = fair.groupby(["event_id", "pk", "market", "line_num", "side"], dropna=False).agg(
        fair_probability=("fair_probability", "median"),
        paired_books=("sportsbook", "nunique"),
    ).reset_index()

    out = {}
    for _, row in grouped.iterrows():
        key = identity(row["event_id"], row["pk"], row["market"], row["line_num"], row["side"])
        out[key] = {
            "fair_probability": round(float(row["fair_probability"]), 8),
            "paired_books": int(row["paired_books"]),
        }
    return out


def historical_rows(sport):
    path = ROOT / f"{sport.lower()}_live" / "decision" / "history" / f"{sport}_GRADED_RECOMMENDATIONS.csv"
    if not path.exists():
        return pd.DataFrame()
    d = pd.read_csv(path, low_memory=False)
    if d.empty or "lane" not in d.columns or "grade" not in d.columns:
        return pd.DataFrame()
    return d[
        d["lane"].astype(str).str.upper().isin(["PROP", "PRIZEPICKS"])
        & d["grade"].astype(str).str.upper().isin(["WIN", "LOSS"])
    ].copy()


def recommendation_identity(row):
    try:
        payload = json.loads(row.get("payload_json") or "{}")
    except Exception:
        payload = {}
    event_id = payload.get("event_id") or row.get("event_id")
    player = payload.get("player_key") or payload.get("player") or row.get("player")
    market = payload.get("market_subtype") or row.get("market")
    side = payload.get("side") or row.get("side")
    line = payload.get("line") if payload.get("line") is not None else row.get("line")
    return identity(event_id, player, market, line, side)


def current_market_path(sport):
    if sport == "NFL":
        return ROOT / "nfl_live" / "fusion" / "NFL_MULTIBOOK_PLAYER_PROPS.csv"
    return ROOT / f"{sport.lower()}_live" / "markets" / "current" / f"{sport}_PLAYER_PROP_MARKET.csv"


def historical_market_files(sport):
    if sport == "NFL":
        return glob.glob(str(
            ROOT / "nfl_live" / "fusion" / "history" /
            "NFL_MULTIBOOK_PLAYER_PROPS_*.csv"
        ))
    return glob.glob(str(
        ROOT / f"{sport.lower()}_live" / "markets" / "history" /
        f"{sport}_PLAYER_PROP_MARKET_*.csv"
    ))


def current_for_sport(sport):
    path = current_market_path(sport)
    return (
        fair_map(path, max_quote_age_minutes=CURRENT_MAX_QUOTE_AGE_MINUTES)
        if path.exists()
        else {}
    )


def history_for_sport(sport):
    if sport not in RAW_MARKET_SPORTS:
        return {}, {"settled": 0, "matched": 0, "matched_2plus": 0}
    d = historical_rows(sport)
    if d.empty:
        return {}, {"settled": 0, "matched": 0, "matched_2plus": 0}

    files = historical_market_files(sport)
    index = sorted((file_timestamp(f), f) for f in files if pd.notna(file_timestamp(f)))
    times = [t for t, _ in index]
    assignments = {}

    for idx, row in d.iterrows():
        snap = pd.to_datetime(row.get("snapshot_at"), utc=True, errors="coerce")
        if pd.isna(snap):
            continue
        pos = bisect.bisect_right(times, snap) - 1
        if pos < 0:
            continue
        market_time, market_file = index[pos]
        age = (snap - market_time).total_seconds() / 60.0
        if age < 0 or age > MAX_ARCHIVE_AGE_MINUTES:
            continue
        assignments.setdefault(market_file, []).append((idx, age))

    out = {}
    matched = 0
    matched_2plus = 0
    for market_file, members in assignments.items():
        fmap = fair_map(market_file)
        for idx, age in members:
            row = d.loc[idx]
            key = recommendation_identity(row)
            result = fmap.get(key)
            if not result:
                continue
            rec_key = clean(row.get("recommendation_key"))
            if not rec_key:
                rec_key = f"{sport}|{clean(row.get('lane')).upper()}|{clean(row.get('snapshot_at'))}|{key}"
            out[rec_key] = {
                **result,
                "lane": clean(row.get("lane")).upper(),
                "market_snapshot_age_minutes": round(float(age), 2),
            }
            matched += 1
            if result["paired_books"] >= MIN_PAIRED_BOOKS_FOR_MODEL:
                matched_2plus += 1

    return out, {
        "settled": int(len(d)),
        "matched": matched,
        "matched_2plus": matched_2plus,
        "coverage_pct": round(100.0 * matched / len(d), 1) if len(d) else None,
        "coverage_2plus_pct": round(100.0 * matched_2plus / len(d), 1) if len(d) else None,
    }


def main():
    current = {}
    history = {}
    coverage = {}
    for sport in SPORTS:
        current[sport] = current_for_sport(sport) if sport in RAW_MARKET_SPORTS else {}
        history[sport], coverage[sport] = history_for_sport(sport)
        coverage[sport]["current_fair_markets"] = len(current[sport])

    payload = {
        "status": "READY",
        "method": "SAME_BOOK_TWO_SIDED_PROPORTIONAL_DEVIG_THEN_MEDIAN_ACROSS_BOOKS",
        "max_archive_age_minutes": MAX_ARCHIVE_AGE_MINUTES,
        "current_max_quote_age_minutes": CURRENT_MAX_QUOTE_AGE_MINUTES,
        "minimum_paired_books_for_model": MIN_PAIRED_BOOKS_FOR_MODEL,
        "reasonable_overround_range": [
            MIN_REASONABLE_OVERROUND,
            MAX_REASONABLE_OVERROUND,
        ],
        "coverage": coverage,
        "current": current,
        "history": history,
        "rules": [
            "Only exact event/player/market/line OVER-UNDER pairs from the same sportsbook are de-vigged.",
            "Each book is de-vigged before fair probabilities are combined across books.",
            "Book pairs with implied-probability sums outside the configured reasonable overround range are rejected.",
            "Current de-vig references reject quotes older than the configured freshness window.",
            "Historical references use only the latest archived market snapshot at or before the frozen recommendation.",
            "Historical matches older than 30 minutes are rejected.",
            "V2 requires at least two paired books before de-vigged historical probability can replace the raw market reference.",
            "NFL uses its multibook fusion archive; NBA, NHL and MLB use their normalized player-prop market archives.",
        ],
    }
    for path in (OUT, PUBLIC):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))
    if DIST.exists():
        DIST.write_text(json.dumps(payload, indent=2))
    print(json.dumps({"status": "READY", "coverage": coverage}, indent=2))


if __name__ == "__main__":
    main()
