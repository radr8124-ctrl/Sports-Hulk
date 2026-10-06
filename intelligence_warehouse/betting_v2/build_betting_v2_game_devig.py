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
OUT = OUT_DIR / "BETTING_V2_GAME_DEVIG.json"
PUBLIC = ROOT / "commercial_web" / "public" / "betting_v2_game_devig.json"
DIST = ROOT / "commercial_web" / "dist" / "betting_v2_game_devig.json"

SPORTS = ("NFL", "CFB", "CBB", "MLB", "NBA", "NHL")
MAX_ARCHIVE_AGE_MINUTES = 30.0
MIN_PAIRED_BOOKS_FOR_MODEL = 2

HISTORY_FILES = {
    sport: ROOT / f"{sport.lower()}_live" / "decision" / "history" / f"{sport}_GRADED_RECOMMENDATIONS.csv"
    for sport in SPORTS
}
CURRENT_DECISIONS = {
    sport: ROOT / f"{sport.lower()}_live" / "decision" / f"{sport}_GAME_DECISIONS.csv"
    for sport in SPORTS
}


def clean(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    return str(v).strip()


def num(v):
    try:
        x = float(v)
        return None if math.isnan(x) else x
    except Exception:
        return None


def parse_json(v):
    try:
        return json.loads(v or "{}")
    except Exception:
        return {}


def norm(v):
    return re.sub(r"[^a-z0-9]+", "", clean(v).lower())


def parse_dt(v):
    try:
        d = pd.to_datetime(v, errors="coerce", utc=True)
        return None if pd.isna(d) else d
    except Exception:
        return None


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


def raw_current_path(sport):
    if sport == "NFL":
        return ROOT / "nfl_live" / "game_fusion" / "NFL_GAME_SPORTWIZZARD_RAW.csv"
    return ROOT / f"{sport.lower()}_live" / "markets" / "current" / f"{sport}_GAME_MARKET.csv"


def history_market_files(sport):
    if sport == "NFL":
        pattern = ROOT / "nfl_live" / "game_fusion" / "history" / "NFL_GAME_SPORTWIZZARD_*.csv"
    else:
        pattern = ROOT / f"{sport.lower()}_live" / "markets" / "history" / f"{sport}_GAME_MARKET_*.csv"
    return glob.glob(str(pattern))


def alias_map(sport):
    out = {}
    if sport in {"CFB", "CBB"}:
        path = ROOT / f"{sport.lower()}_live" / "markets" / "current" / f"{sport}_GAME_MARKET_NORMALIZED.csv"
        if path.exists():
            d = pd.read_csv(path, low_memory=False)
            for raw_col, can_col in (("away_team_raw", "away_team"), ("home_team_raw", "home_team")):
                if raw_col in d.columns and can_col in d.columns:
                    for raw, can in d[[raw_col, can_col]].dropna().drop_duplicates().itertuples(index=False):
                        out[norm(raw)] = clean(can).upper()
    elif sport in {"NBA", "NHL"}:
        path = ROOT / f"{sport.lower()}_live" / "markets" / "current" / f"{sport}_GAME_MARKET_NORMALIZED.csv"
        if path.exists():
            d = pd.read_csv(path, low_memory=False)
            for raw_col, can_col in (
                ("away_team", "away_team_canonical"),
                ("home_team", "home_team_canonical"),
                ("selection", "selection_canonical"),
            ):
                if raw_col in d.columns and can_col in d.columns:
                    for raw, can in d[[raw_col, can_col]].dropna().drop_duplicates().itertuples(index=False):
                        out[norm(raw)] = clean(can).upper()
    return out


ALIASES = {sport: alias_map(sport) for sport in SPORTS}


def canonical_team(sport, value):
    if sport == "MLB":
        return norm(value)
    if sport == "NFL":
        return norm(value)
    mapped = ALIASES.get(sport, {}).get(norm(value))
    return mapped or clean(value).upper()


def event_key(sport, start, away, home):
    start = parse_dt(start)
    if start is None or not away or not home:
        return ""
    if sport == "MLB":
        return f"START|{start.strftime('%Y-%m-%dT%H:%M')}|{away}|{home}"
    return f"DATE|{start.date().isoformat()}|{away}|{home}"


def event_identity_from_raw(sport, row):
    if sport == "NFL":
        game_key = clean(row.get("game_key"))
        return f"GAME|{game_key}" if game_key else ""
    away = clean(row.get("_away_can")) or canonical_team(sport, row.get("away_team"))
    home = clean(row.get("_home_can")) or canonical_team(sport, row.get("home_team"))
    return event_key(sport, row.get("start"), away, home)


def event_identity_from_history(sport, row):
    payload = parse_json(row.get("payload_json"))
    if sport == "NFL":
        game_key = clean(payload.get("game_key") or row.get("game_key"))
        return f"GAME|{game_key}" if game_key else ""

    start = (
        parse_dt(payload.get("start_dt"))
        or parse_dt(payload.get("start"))
        or parse_dt(row.get("start"))
    )
    if sport in {"CFB", "CBB"}:
        away = clean(payload.get("away_team")).upper()
        home = clean(payload.get("home_team")).upper()
    elif sport in {"NBA", "NHL"}:
        away = clean(payload.get("away_team_canonical")).upper()
        home = clean(payload.get("home_team_canonical")).upper()
    else:
        away = canonical_team(sport, payload.get("away_team"))
        home = canonical_team(sport, payload.get("home_team"))
    return event_key(sport, start, away, home)


def event_identity_from_current(sport, row):
    if sport == "NFL":
        game_key = clean(row.get("game_key"))
        return f"GAME|{game_key}" if game_key else ""
    start = parse_dt(row.get("start_dt") or row.get("start"))
    if sport in {"CFB", "CBB"}:
        away = clean(row.get("away_team")).upper()
        home = clean(row.get("home_team")).upper()
    elif sport in {"NBA", "NHL"}:
        away = clean(row.get("away_team_canonical")).upper()
        home = clean(row.get("home_team_canonical")).upper()
    else:
        away = canonical_team(sport, row.get("away_team"))
        home = canonical_team(sport, row.get("home_team"))
    return event_key(sport, start, away, home)


def history_side(sport, row):
    payload = parse_json(row.get("payload_json"))
    side = clean(payload.get("selection_side")).upper()
    if side in {"HOME", "AWAY"}:
        return side

    selection = clean(payload.get("selection_canonical") or payload.get("selection") or row.get("selection")).upper()
    if sport in {"CFB", "CBB"}:
        away = clean(payload.get("away_team")).upper()
        home = clean(payload.get("home_team")).upper()
    elif sport in {"NBA", "NHL"}:
        away = clean(payload.get("away_team_canonical")).upper()
        home = clean(payload.get("home_team_canonical")).upper()
    elif sport == "MLB":
        away = clean(payload.get("away_team")).upper()
        home = clean(payload.get("home_team")).upper()
    else:
        # NFL selection is a full team name. Side is resolved later from raw event metadata.
        return None

    if selection and away and selection == away:
        return "AWAY"
    if selection and home and selection == home:
        return "HOME"
    return None


def current_side(sport, row):
    side = clean(row.get("selection_side")).upper()
    if side in {"HOME", "AWAY"}:
        return side
    selection = clean(row.get("selection_canonical") or row.get("selection")).upper()
    if sport in {"CFB", "CBB"}:
        away = clean(row.get("away_team")).upper()
        home = clean(row.get("home_team")).upper()
    elif sport in {"NBA", "NHL"}:
        away = clean(row.get("away_team_canonical")).upper()
        home = clean(row.get("home_team_canonical")).upper()
    elif sport == "MLB":
        away = clean(row.get("away_team")).upper()
        home = clean(row.get("home_team")).upper()
    else:
        return None
    if selection and away and selection == away:
        return "AWAY"
    if selection and home and selection == home:
        return "HOME"
    return None


def fair_map(sport, path):
    try:
        d = pd.read_csv(path, low_memory=False)
    except Exception:
        return {}, {}
    required = {"sportsbook", "side", "price_american"}
    if not required.issubset(d.columns):
        return {}, {}

    market_col = "market" if "market" in d.columns else "market_canonical" if "market_canonical" in d.columns else None
    if market_col:
        d = d[d[market_col].astype(str).str.upper().eq("MONEYLINE")].copy()
    if d.empty:
        return {}, {}

    d["_side"] = d["side"].astype(str).str.upper()
    if sport != "NFL":
        d["_away_can"] = d.get("away_team", pd.Series("", index=d.index)).map(
            lambda v: canonical_team(sport, v)
        )
        d["_home_can"] = d.get("home_team", pd.Series("", index=d.index)).map(
            lambda v: canonical_team(sport, v)
        )
        d["_selection_can"] = d.get("selection", pd.Series("", index=d.index)).map(
            lambda v: canonical_team(sport, v)
        )
        if "event_id" in d.columns:
            for _, idx in d.groupby("event_id").groups.items():
                g = d.loc[idx]
                away_sel = [
                    clean(v)
                    for v in g.loc[g["_side"].eq("AWAY"), "_selection_can"].tolist()
                    if clean(v)
                ]
                home_sel = [
                    clean(v)
                    for v in g.loc[g["_side"].eq("HOME"), "_selection_can"].tolist()
                    if clean(v)
                ]
                if sport in {"NBA", "NHL"}:
                    if away_sel:
                        d.loc[idx, "_away_can"] = away_sel[-1]
                    if home_sel:
                        d.loc[idx, "_home_can"] = home_sel[-1]
                else:
                    if away_sel and not any(clean(v) for v in g["_away_can"].tolist()):
                        d.loc[idx, "_away_can"] = away_sel[-1]
                    if home_sel and not any(clean(v) for v in g["_home_can"].tolist()):
                        d.loc[idx, "_home_can"] = home_sel[-1]

    d["_event"] = d.apply(lambda r: event_identity_from_raw(sport, r), axis=1)
    d["_book"] = d["sportsbook"].astype(str).str.lower()
    d["_implied"] = implied_array(d["price_american"])
    d = d[
        d["_event"].ne("")
        & d["_side"].isin(["HOME", "AWAY"])
        & d["_implied"].notna()
    ].copy()
    if d.empty:
        return {}, {}

    keys = ["_event", "_book"]
    pivot = d.pivot_table(index=keys, columns="_side", values="_implied", aggfunc="last")
    if "HOME" not in pivot.columns or "AWAY" not in pivot.columns:
        return {}, {}
    pivot = pivot.dropna(subset=["HOME", "AWAY"]).copy()
    if pivot.empty:
        return {}, {}

    denom = pivot["HOME"] + pivot["AWAY"]
    pivot["HOME_FAIR"] = pivot["HOME"] / denom
    pivot["AWAY_FAIR"] = pivot["AWAY"] / denom
    pivot = pivot.reset_index()

    out = {}
    for side in ("HOME", "AWAY"):
        y = pivot[["_event", "_book"]].copy()
        y["side"] = side
        y["fair_probability"] = pivot[f"{side}_FAIR"]
        grouped = y.groupby(["_event", "side"], dropna=False).agg(
            fair_probability=("fair_probability", "median"),
            paired_books=("_book", "nunique"),
        ).reset_index()
        for _, row in grouped.iterrows():
            out[f"{row['_event']}|{side}"] = {
                "fair_probability": round(float(row["fair_probability"]), 8),
                "paired_books": int(row["paired_books"]),
            }

    meta = {}
    for event, g in d.groupby("_event"):
        meta[event] = {
            "away_team": clean(g.iloc[-1].get("away_team")),
            "home_team": clean(g.iloc[-1].get("home_team")),
        }
    return out, meta


def recommendation_key(sport, row):
    key = clean(row.get("recommendation_key"))
    if key:
        return key
    return "|".join([
        sport,
        clean(row.get("snapshot_at")),
        clean(row.get("game_key")),
        clean(row.get("selection")),
    ])


def historical_rows(sport):
    path = HISTORY_FILES[sport]
    if not path.exists():
        return pd.DataFrame()
    d = pd.read_csv(path, low_memory=False)
    if d.empty or "lane" not in d.columns or "grade" not in d.columns:
        return pd.DataFrame()
    d = d[
        d["lane"].astype(str).str.upper().eq("GAME")
        & d["market"].astype(str).str.upper().eq("MONEYLINE")
        & d["grade"].astype(str).str.upper().isin(["WIN", "LOSS"])
    ].copy()
    return d


def resolve_nfl_side(row, meta, event):
    selection = norm(parse_json(row.get("payload_json")).get("selection") or row.get("selection"))
    if not selection:
        return None
    m = meta.get(event, {})
    if selection == norm(m.get("away_team")):
        return "AWAY"
    if selection == norm(m.get("home_team")):
        return "HOME"
    return None


def history_for_sport(sport):
    d = historical_rows(sport)
    stats = {
        "settled_pregame_rows": 0,
        "matched": 0,
        "matched_2plus": 0,
        "no_recent_snapshot": 0,
        "no_exact_event": 0,
        "no_side": 0,
        "post_start_rejected": 0,
    }
    if d.empty:
        return {}, stats

    files = history_market_files(sport)
    index = sorted((file_timestamp(f), f) for f in files if pd.notna(file_timestamp(f)))
    times = [t for t, _ in index]
    assignments = {}

    for idx, row in d.iterrows():
        snap = parse_dt(row.get("snapshot_at"))
        start = parse_dt(row.get("start"))
        if start is None:
            payload = parse_json(row.get("payload_json"))
            start = parse_dt(payload.get("start_dt") or payload.get("start"))
        if snap is None:
            continue
        if start is not None and snap >= start:
            stats["post_start_rejected"] += 1
            continue
        stats["settled_pregame_rows"] += 1

        pos = bisect.bisect_right(times, snap) - 1
        if pos < 0:
            stats["no_recent_snapshot"] += 1
            continue
        market_time, market_file = index[pos]
        age = (snap - market_time).total_seconds() / 60.0
        if age < 0 or age > MAX_ARCHIVE_AGE_MINUTES:
            stats["no_recent_snapshot"] += 1
            continue
        assignments.setdefault(market_file, []).append((idx, age))

    out = {}
    for market_file, members in assignments.items():
        fmap, meta = fair_map(sport, market_file)
        for idx, age in members:
            row = d.loc[idx]
            event = event_identity_from_history(sport, row)
            if not event:
                stats["no_exact_event"] += 1
                continue
            side = history_side(sport, row)
            if sport == "NFL" and side is None:
                side = resolve_nfl_side(row, meta, event)
            if side not in {"HOME", "AWAY"}:
                stats["no_side"] += 1
                continue
            result = fmap.get(f"{event}|{side}")
            if not result:
                stats["no_exact_event"] += 1
                continue
            key = recommendation_key(sport, row)
            out[key] = {
                **result,
                "market_snapshot_age_minutes": round(float(age), 3),
                "event_identity": event,
                "side": side,
            }
            stats["matched"] += 1
            if result["paired_books"] >= MIN_PAIRED_BOOKS_FOR_MODEL:
                stats["matched_2plus"] += 1

    n = stats["settled_pregame_rows"]
    stats["coverage_pct"] = round(100 * stats["matched"] / n, 1) if n else None
    stats["coverage_2plus_pct"] = round(100 * stats["matched_2plus"] / n, 1) if n else None
    return out, stats


def current_for_sport(sport):
    path = raw_current_path(sport)
    fmap, meta = fair_map(sport, path) if path.exists() else ({}, {})
    decision_path = CURRENT_DECISIONS[sport]
    if not decision_path.exists():
        return {}, {"current_moneyline_rows": 0, "matched": 0, "matched_2plus": 0}
    d = pd.read_csv(decision_path, low_memory=False)
    market_col = "market" if "market" in d.columns else "market_canonical" if "market_canonical" in d.columns else None
    if not market_col:
        return {}, {"current_moneyline_rows": 0, "matched": 0, "matched_2plus": 0}
    d = d[d[market_col].astype(str).str.upper().eq("MONEYLINE")].copy()

    out = {}
    matched = matched2 = 0
    for _, row in d.iterrows():
        event = event_identity_from_current(sport, row)
        side = current_side(sport, row)
        if sport == "NFL" and side is None:
            selection = norm(row.get("selection"))
            m = meta.get(event, {})
            if selection == norm(m.get("away_team")):
                side = "AWAY"
            elif selection == norm(m.get("home_team")):
                side = "HOME"
        if not event or side not in {"HOME", "AWAY"}:
            continue
        result = fmap.get(f"{event}|{side}")
        if not result:
            continue
        key = f"{clean(row.get('game_key'))}|{side}"
        out[key] = {**result, "event_identity": event}
        matched += 1
        if result["paired_books"] >= MIN_PAIRED_BOOKS_FOR_MODEL:
            matched2 += 1
    return out, {
        "current_moneyline_rows": int(len(d)),
        "matched": matched,
        "matched_2plus": matched2,
    }


def main():
    history = {}
    current = {}
    coverage = {}
    for sport in SPORTS:
        history[sport], hist_stats = history_for_sport(sport)
        current[sport], current_stats = current_for_sport(sport)
        coverage[sport] = {
            **hist_stats,
            **{f"current_{k}": v for k, v in current_stats.items()},
            "current_fair_keys": len(current[sport]),
        }

    payload = {
        "status": "READY",
        "method": "SAME_BOOK_HOME_AWAY_PROPORTIONAL_DEVIG_THEN_MEDIAN_ACROSS_BOOKS",
        "max_archive_age_minutes": MAX_ARCHIVE_AGE_MINUTES,
        "minimum_paired_books_for_model": MIN_PAIRED_BOOKS_FOR_MODEL,
        "coverage": coverage,
        "history": history,
        "current": current,
        "rules": [
            "Only pregame settled GAME moneyline observations are eligible for historical matching.",
            "HOME and AWAY prices must exist at the same sportsbook before de-vigging.",
            "Each sportsbook is de-vigged before fair probabilities are combined across books.",
            "Historical market snapshots must exist at or before the frozen recommendation and be no more than 30 minutes old.",
            "At least two paired sportsbooks are required before fair probability can replace the raw market reference in model training or live V2.",
            "Official Best Bets records remain separate from the expanded research-training sample.",
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
