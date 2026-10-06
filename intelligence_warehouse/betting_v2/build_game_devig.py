#!/usr/bin/env python3
from __future__ import annotations

import ast
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

SPORTS = ("NFL", "CFB", "MLB", "NBA", "NHL")
MAX_ARCHIVE_AGE_MINUTES = 30.0
MIN_PAIRED_BOOKS_FOR_MODEL = 2

CURRENT_MARKETS = {
    "NFL": ROOT / "nfl_live" / "game_fusion" / "NFL_GAME_SPORTWIZZARD_RAW.csv",
    "CFB": ROOT / "cfb_live" / "markets" / "current" / "CFB_GAME_MARKET.csv",
    "MLB": ROOT / "mlb_live" / "markets" / "current" / "MLB_GAME_MARKET.csv",
    "NBA": ROOT / "nba_live" / "markets" / "current" / "NBA_GAME_MARKET.csv",
    "NHL": ROOT / "nhl_live" / "markets" / "current" / "NHL_GAME_MARKET.csv",
}
HISTORY_GLOBS = {
    "NFL": ROOT / "nfl_live" / "game_fusion" / "history" / "NFL_GAME_SPORTWIZZARD_*.csv",
    "CFB": ROOT / "cfb_live" / "markets" / "history" / "CFB_GAME_MARKET_*.csv",
    "MLB": ROOT / "mlb_live" / "markets" / "history" / "MLB_GAME_MARKET_*.csv",
    "NBA": ROOT / "nba_live" / "markets" / "history" / "NBA_GAME_MARKET_*.csv",
    "NHL": ROOT / "nhl_live" / "markets" / "history" / "NHL_GAME_MARKET_*.csv",
}
GRADED = {
    sport: ROOT / f"{sport.lower()}_live" / "decision" / "history" / f"{sport}_GRADED_RECOMMENDATIONS.csv"
    for sport in SPORTS
}


def clean(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def num(value):
    try:
        x = float(value)
        return None if math.isnan(x) else x
    except Exception:
        return None


def norm(value):
    return re.sub(r"[^a-z0-9]+", "", clean(value).lower())


def parse_dt(value):
    try:
        d = pd.to_datetime(value, errors="coerce", utc=True)
        return None if pd.isna(d) else d
    except Exception:
        return None


def parse_payload(value):
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}


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


def literal_dict(path, variable):
    try:
        tree = ast.parse(Path(path).read_text())
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == variable:
                        value = ast.literal_eval(node.value)
                        if isinstance(value, dict):
                            return value
    except Exception:
        pass
    return {}


NBA_TEAM_MAP = literal_dict(ROOT / "nba_live" / "build_nba_fusion.py", "TEAM_MAP")
NHL_TEAM_MAP = literal_dict(ROOT / "nhl_live" / "build_nhl_fusion.py", "TEAM_NAMES")


def canonical_team(sport, value):
    value = clean(value)
    if not value:
        return ""
    compact = re.sub(r"[^A-Za-z0-9]+", "", value)
    if sport == "NBA":
        return clean(NBA_TEAM_MAP.get(compact.upper()))
    if sport == "NHL":
        return clean(NHL_TEAM_MAP.get(compact.lower()))
    return value


def minute_key(value):
    d = parse_dt(value)
    return "" if d is None else d.floor("min").isoformat()


def team_pair_key(start, away, home):
    return f"{minute_key(start)}|{norm(away)}|{norm(home)}"


def market_identity(sport, game_key, start, away, home, side):
    side = clean(side).upper()
    if side not in {"HOME", "AWAY"}:
        return ""
    if sport in {"NFL", "NBA", "NHL"}:
        if not clean(game_key):
            return ""
        return f"{clean(game_key)}|{side}"
    pair = team_pair_key(start, away, home)
    return "" if not pair else f"{pair}|{side}"


def raw_market_context(sport, frame):
    if frame.empty:
        return pd.DataFrame()
    d = frame.copy()
    required = {"sportsbook", "side", "price_american"}
    if not required.issubset(d.columns):
        return pd.DataFrame()

    market_col = "market" if "market" in d.columns else "market_canonical" if "market_canonical" in d.columns else None
    if market_col is None:
        return pd.DataFrame()
    d = d[d[market_col].astype(str).str.upper().eq("MONEYLINE")].copy()
    if d.empty:
        return d

    d["_side"] = d["side"].astype(str).str.upper()
    d["_implied"] = implied_array(d["price_american"])
    d = d[d["_side"].isin(["HOME", "AWAY"]) & d["_implied"].notna()].copy()
    if d.empty:
        return d

    if "event_id" not in d.columns:
        return pd.DataFrame()
    d["_event"] = d["event_id"].astype(str)
    d["_book"] = d["sportsbook"].astype(str).str.lower()
    d["_start"] = pd.to_datetime(
        d["start"] if "start" in d.columns else d.get("start_dt"),
        errors="coerce", utc=True
    )

    if sport == "NFL":
        d["_game_key"] = d.get("game_key", "").astype(str)
        d["_away_key"] = d.get("away_team", "").astype(str)
        d["_home_key"] = d.get("home_team", "").astype(str)
    elif sport in {"NBA", "NHL"}:
        d["_selection_canon"] = d["selection"].map(lambda x: canonical_team(sport, x))
        event_side = (
            d[d["_selection_canon"].ne("")]
            .groupby(["_event", "_side"])["_selection_canon"]
            .agg(lambda x: x.iloc[-1] if len(set(x)) == 1 else "")
            .unstack("_side")
        )
        event_side = event_side.rename(columns={"AWAY": "_away_canon", "HOME": "_home_canon"})
        d = d.merge(event_side, left_on="_event", right_index=True, how="left")
        date = d["_start"].dt.date.astype(str)
        d["_game_key"] = date + "|" + d["_away_canon"].fillna("") + "|" + d["_home_canon"].fillna("")
        d["_away_key"] = d["_away_canon"].fillna("")
        d["_home_key"] = d["_home_canon"].fillna("")
    else:
        d["_game_key"] = ""
        d["_away_key"] = d.get("away_team", "").astype(str)
        d["_home_key"] = d.get("home_team", "").astype(str)

    return d


def fair_map(path, sport):
    try:
        raw = pd.read_csv(path, low_memory=False)
    except Exception:
        return {}, {}
    d = raw_market_context(sport, raw)
    if d.empty:
        return {}, {}

    pivot = d.pivot_table(
        index=["_event", "_book"],
        columns="_side",
        values="_implied",
        aggfunc="last",
    )
    if "HOME" not in pivot.columns or "AWAY" not in pivot.columns:
        return {}, {}
    pivot = pivot.dropna(subset=["HOME", "AWAY"]).copy()
    if pivot.empty:
        return {}, {}

    denom = pivot["HOME"] + pivot["AWAY"]
    pivot["HOME_FAIR"] = pivot["HOME"] / denom
    pivot["AWAY_FAIR"] = pivot["AWAY"] / denom
    pivot = pivot.reset_index()

    event_meta = (
        d.sort_values("_start")
        .groupby("_event")
        .tail(1)
        .set_index("_event")[["_game_key", "_start", "_away_key", "_home_key"]]
    )
    pivot = pivot.join(event_meta, on="_event")

    rows = []
    for side in ("HOME", "AWAY"):
        y = pivot[["_event", "_book", "_game_key", "_start", "_away_key", "_home_key"]].copy()
        y["side"] = side
        y["fair_probability"] = pivot[f"{side}_FAIR"].astype(float)
        rows.append(y)
    fair = pd.concat(rows, ignore_index=True)

    fair["identity"] = fair.apply(
        lambda r: market_identity(
            sport,
            r["_game_key"],
            r["_start"],
            r["_away_key"],
            r["_home_key"],
            r["side"],
        ),
        axis=1,
    )
    fair = fair[fair["identity"].ne("")].copy()

    grouped = fair.groupby("identity", dropna=False).agg(
        fair_probability=("fair_probability", "median"),
        paired_books=("_book", "nunique"),
    ).reset_index()

    out = {
        row["identity"]: {
            "fair_probability": round(float(row["fair_probability"]), 8),
            "paired_books": int(row["paired_books"]),
        }
        for _, row in grouped.iterrows()
    }

    aliases = {}
    if sport == "NFL":
        for event, group in d.groupby("_game_key"):
            if not clean(event):
                continue
            aliases[event] = {
                "AWAY": sorted(set(
                    clean(v) for v in list(group.get("away_team", [])) + list(group[group["_side"].eq("AWAY")].get("selection", []))
                    if clean(v)
                )),
                "HOME": sorted(set(
                    clean(v) for v in list(group.get("home_team", [])) + list(group[group["_side"].eq("HOME")].get("selection", []))
                    if clean(v)
                )),
            }
    return out, aliases


def token_score(a, b):
    ta = {x for x in re.findall(r"[a-z]+", clean(a).lower()) if len(x) > 2}
    tb = {x for x in re.findall(r"[a-z]+", clean(b).lower()) if len(x) > 2}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, min(len(ta), len(tb)))


def infer_nfl_side(selection, game_key, aliases):
    choices = aliases.get(clean(game_key), {})
    best_side = ""
    best_score = 0.0
    for side in ("AWAY", "HOME"):
        for alias in choices.get(side, []):
            if norm(selection) == norm(alias):
                return side
            score = token_score(selection, alias)
            if score > best_score:
                best_score = score
                best_side = side
    return best_side if best_score >= 0.5 else ""


def recommendation_context(sport, row, aliases):
    payload = parse_payload(row.get("payload_json"))
    game_key = clean(payload.get("game_key") or row.get("game_key"))
    start = payload.get("start_dt") or payload.get("start") or row.get("start")
    selection = clean(
        payload.get("selection_canonical")
        or payload.get("selection")
        or row.get("selection")
    )

    side = clean(payload.get("selection_side") or payload.get("side")).upper()
    if side not in {"HOME", "AWAY"}:
        away = clean(payload.get("away_team_canonical") or payload.get("away_team"))
        home = clean(payload.get("home_team_canonical") or payload.get("home_team"))
        if selection and away and norm(selection) == norm(away):
            side = "AWAY"
        elif selection and home and norm(selection) == norm(home):
            side = "HOME"

    if side not in {"HOME", "AWAY"} and sport == "CFB":
        selected_id = num(payload.get("selection_team_id"))
        away_id = num(payload.get("away_team_id"))
        home_id = num(payload.get("home_team_id"))
        if selected_id is not None and away_id is not None and selected_id == away_id:
            side = "AWAY"
        elif selected_id is not None and home_id is not None and selected_id == home_id:
            side = "HOME"

    if side not in {"HOME", "AWAY"} and sport == "NFL":
        side = infer_nfl_side(selection, game_key, aliases)

    if sport == "CFB":
        away = payload.get("away_team_name") or payload.get("away_team")
        home = payload.get("home_team_name") or payload.get("home_team")
    elif sport == "MLB":
        away = payload.get("away_team")
        home = payload.get("home_team")
    else:
        away = payload.get("away_team_canonical") or payload.get("away_team")
        home = payload.get("home_team_canonical") or payload.get("home_team")

    identity = market_identity(sport, game_key, start, away, home, side)
    return identity, side


def historical_rows(sport):
    path = GRADED[sport]
    if not path.exists():
        return pd.DataFrame()
    d = pd.read_csv(path, low_memory=False)
    if d.empty or "lane" not in d.columns or "grade" not in d.columns:
        return pd.DataFrame()
    d = d[
        d["lane"].astype(str).str.upper().eq("GAME")
        & d["grade"].astype(str).str.upper().isin(["WIN", "LOSS"])
    ].copy()
    if "market" in d.columns:
        d = d[d["market"].astype(str).str.upper().eq("MONEYLINE")].copy()
    if "decision" in d.columns:
        d = d[d["decision"].astype(str).str.upper().eq("QUALIFIED_RESEARCH")].copy()
    if d.empty:
        return d

    d["_snapshot"] = pd.to_datetime(d.get("snapshot_at"), errors="coerce", utc=True)

    def event_start(row):
        payload = parse_payload(row.get("payload_json"))
        for value in [
            row.get("start"),
            payload.get("start"),
            payload.get("start_dt"),
            payload.get("start_sportsbook"),
            payload.get("start_dfs"),
        ]:
            parsed = parse_dt(value)
            if parsed is not None:
                return parsed
        return None

    d["_event_start"] = d.apply(event_start, axis=1)
    d = d[
        d.apply(
            lambda r: (
                r["_event_start"] is None
                or pd.isna(r["_snapshot"])
                or r["_snapshot"] < r["_event_start"]
            ),
            axis=1,
        )
    ].copy()
    if d.empty:
        return d

    d["_order"] = d["_snapshot"]
    d["_order"] = d["_order"].fillna(
        pd.to_datetime(d["_event_start"], errors="coerce", utc=True)
    )
    d["_order"] = d["_order"].fillna(pd.Timestamp("1970-01-01", tz="UTC"))
    d = d.sort_values("_order").drop_duplicates(
        ["game_key", "selection"], keep="first"
    )
    return d


def historical_files(sport):
    files = glob.glob(str(HISTORY_GLOBS[sport]))
    return sorted(
        (file_timestamp(f), f)
        for f in files
        if pd.notna(file_timestamp(f))
    )


def history_for_sport(sport):
    d = historical_rows(sport)
    if d.empty:
        return {}, {"settled": 0, "matched": 0, "matched_2plus": 0}

    index = historical_files(sport)
    times = [t for t, _ in index]
    assignments = {}
    for idx, row in d.iterrows():
        snap = pd.to_datetime(row.get("snapshot_at"), errors="coerce", utc=True)
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
    cache = {}
    alias_cache = {}
    for market_file, members in assignments.items():
        if market_file not in cache:
            cache[market_file], alias_cache[market_file] = fair_map(market_file, sport)
        fmap = cache[market_file]
        aliases = alias_cache[market_file]
        for idx, age in members:
            row = d.loc[idx]
            identity, side = recommendation_context(sport, row, aliases)
            result = fmap.get(identity)
            if not result:
                continue
            rec_key = clean(row.get("recommendation_key"))
            if not rec_key:
                rec_key = f"{sport}|{clean(row.get('snapshot_at'))}|{identity}"
            out[rec_key] = {
                **result,
                "side": side,
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


def current_for_sport(sport):
    path = CURRENT_MARKETS[sport]
    if not path.exists():
        return {}
    fmap, _ = fair_map(path, sport)
    return fmap


def main():
    current = {}
    history = {}
    coverage = {}
    for sport in SPORTS:
        current[sport] = current_for_sport(sport)
        history[sport], coverage[sport] = history_for_sport(sport)
        coverage[sport]["current_fair_sides"] = len(current[sport])

    payload = {
        "status": "READY",
        "method": "SAME_BOOK_TWO_SIDED_MONEYLINE_DEVIG_THEN_MEDIAN_ACROSS_BOOKS",
        "max_archive_age_minutes": MAX_ARCHIVE_AGE_MINUTES,
        "minimum_paired_books_for_model": MIN_PAIRED_BOOKS_FOR_MODEL,
        "coverage": coverage,
        "current": current,
        "history": history,
        "rules": [
            "Only HOME/AWAY moneyline prices from the same sportsbook are paired.",
            "Each sportsbook is de-vigged before fair probabilities are combined across books.",
            "Historical references use only the latest raw market snapshot at or before the frozen recommendation.",
            "Historical raw-market snapshots older than 30 minutes are rejected.",
            "At least two paired books are required before fair probability can replace the historical raw market baseline.",
            "No future or closing market information is used to train a pregame prediction.",
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
