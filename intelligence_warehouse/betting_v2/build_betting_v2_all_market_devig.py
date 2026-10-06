#!/usr/bin/env python3
from __future__ import annotations

import bisect
import glob
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
OUT = OUT_DIR / "BETTING_V2_ALL_MARKET_DEVIG.json"
PUBLIC = ROOT / "commercial_web" / "public" / "betting_v2_all_market_devig.json"
DIST = ROOT / "commercial_web" / "dist" / "betting_v2_all_market_devig.json"

if str(OUT_DIR) not in sys.path:
    sys.path.insert(0, str(OUT_DIR))
import build_betting_v2_game_devig as base

SPORTS = ("NFL", "CFB", "CBB", "MLB", "NBA", "NHL")
MARKETS = ("MONEYLINE", "SPREAD", "TOTAL")
MAX_ARCHIVE_AGE_MINUTES = 30.0
MIN_PAIRED_BOOKS_FOR_MODEL = 2

HISTORY_FILES = base.HISTORY_FILES
CURRENT_DECISIONS = base.CURRENT_DECISIONS


def clean(value):
    return base.clean(value)


def num(value):
    return base.num(value)


def parse_dt(value):
    return base.parse_dt(value)


def parse_json(value):
    return base.parse_json(value)


def implied_array(odds):
    return base.implied_array(odds)


def fair_map_all(sport, path, targets=None):
    try:
        d = pd.read_csv(path, low_memory=False)
    except Exception:
        return {}, {}
    required = {"sportsbook", "side", "price_american"}
    if not required.issubset(d.columns):
        return {}, {}

    market_col = (
        "market" if "market" in d.columns
        else "market_canonical" if "market_canonical" in d.columns
        else None
    )
    if not market_col:
        return {}, {}

    d = d[d[market_col].astype(str).str.upper().isin(MARKETS)].copy()
    if d.empty:
        return {}, {}

    d["_market"] = d[market_col].astype(str).str.upper()
    d["_side"] = d["side"].astype(str).str.upper()
    d["_line"] = pd.to_numeric(d.get("line"), errors="coerce")

    if targets:
        mask = pd.Series(False, index=d.index)
        if "MONEYLINE" in targets:
            mask |= d["_market"].eq("MONEYLINE")
        spread_lines = targets.get("SPREAD") or set()
        if spread_lines:
            wanted_abs = {round(abs(float(v)), 4) for v in spread_lines}
            mask |= (
                d["_market"].eq("SPREAD")
                & d["_line"].abs().round(4).isin(wanted_abs)
            )
        total_lines = targets.get("TOTAL") or set()
        if total_lines:
            wanted_total = {round(float(v), 4) for v in total_lines}
            mask |= (
                d["_market"].eq("TOTAL")
                & d["_line"].round(4).isin(wanted_total)
            )
        d = d[mask].copy()
        if d.empty:
            return {}, {}

    d["_book"] = d["sportsbook"].astype(str).str.lower()
    d["_implied"] = implied_array(d["price_american"])

    if sport != "NFL":
        d["_away_can"] = d.get(
            "away_team", pd.Series("", index=d.index)
        ).map(lambda v: base.canonical_team(sport, v))
        d["_home_can"] = d.get(
            "home_team", pd.Series("", index=d.index)
        ).map(lambda v: base.canonical_team(sport, v))
        d["_selection_can"] = d.get(
            "selection", pd.Series("", index=d.index)
        ).map(lambda v: base.canonical_team(sport, v))
        if "event_id" in d.columns:
            for _, idx in d.groupby("event_id").groups.items():
                g = d.loc[idx]
                away_sel = [
                    clean(v)
                    for v in g.loc[
                        g["_side"].eq("AWAY"), "_selection_can"
                    ].tolist()
                    if clean(v)
                ]
                home_sel = [
                    clean(v)
                    for v in g.loc[
                        g["_side"].eq("HOME"), "_selection_can"
                    ].tolist()
                    if clean(v)
                ]
                if sport in {"NBA", "NHL"}:
                    if away_sel:
                        d.loc[idx, "_away_can"] = away_sel[-1]
                    if home_sel:
                        d.loc[idx, "_home_can"] = home_sel[-1]
                else:
                    if away_sel and not any(
                        clean(v) for v in g["_away_can"].tolist()
                    ):
                        d.loc[idx, "_away_can"] = away_sel[-1]
                    if home_sel and not any(
                        clean(v) for v in g["_home_can"].tolist()
                    ):
                        d.loc[idx, "_home_can"] = home_sel[-1]

    d["_event"] = d.apply(
        lambda r: base.event_identity_from_raw(sport, r),
        axis=1,
    )
    d = d[
        d["_event"].ne("")
        & d["_implied"].notna()
        & d["_market"].isin(MARKETS)
    ].copy()
    if d.empty:
        return {}, {}

    out_rows = []

    # MONEYLINE: same-book HOME/AWAY pair.
    ml = d[
        d["_market"].eq("MONEYLINE")
        & d["_side"].isin(["HOME", "AWAY"])
    ].copy()
    if not ml.empty:
        idx_cols = ["_event", "_book"]
        p = ml.pivot_table(
            index=idx_cols,
            columns="_side",
            values=["_implied", "price_american"],
            aggfunc="last",
        )
        if (
            ("_implied", "HOME") in p.columns
            and ("_implied", "AWAY") in p.columns
        ):
            p = p.dropna(
                subset=[
                    ("_implied", "HOME"),
                    ("_implied", "AWAY"),
                ]
            )
            for (event, book), row in p.iterrows():
                ph = float(row[("_implied", "HOME")])
                pa = float(row[("_implied", "AWAY")])
                denom = ph + pa
                if denom <= 0:
                    continue
                for side, raw_p in (("HOME", ph), ("AWAY", pa)):
                    odds = num(row.get(("price_american", side)))
                    out_rows.append({
                        "event": event,
                        "market": "MONEYLINE",
                        "selection_key": side,
                        "line": None,
                        "book": book,
                        "fair_probability": raw_p / denom,
                        "selected_odds": odds,
                    })

    # SPREAD: same book, complementary HOME/AWAY lines.
    sp = d[
        d["_market"].eq("SPREAD")
        & d["_side"].isin(["HOME", "AWAY"])
        & d["_line"].notna()
    ].copy()
    if not sp.empty:
        sp["_abs_line"] = sp["_line"].abs().round(4)
        for (event, book, abs_line), g in sp.groupby(
            ["_event", "_book", "_abs_line"], dropna=False
        ):
            home = g[g["_side"].eq("HOME")]
            away = g[g["_side"].eq("AWAY")]
            if home.empty or away.empty:
                continue
            h = home.iloc[-1]
            a = away.iloc[-1]
            hline = num(h["_line"])
            aline = num(a["_line"])
            if hline is None or aline is None:
                continue
            if abs(hline + aline) > 1e-6:
                continue
            ph = num(h["_implied"])
            pa = num(a["_implied"])
            if ph is None or pa is None or ph + pa <= 0:
                continue
            denom = ph + pa
            out_rows.extend([
                {
                    "event": event,
                    "market": "SPREAD",
                    "selection_key": "HOME",
                    "line": hline,
                    "book": book,
                    "fair_probability": ph / denom,
                    "selected_odds": num(h.get("price_american")),
                },
                {
                    "event": event,
                    "market": "SPREAD",
                    "selection_key": "AWAY",
                    "line": aline,
                    "book": book,
                    "fair_probability": pa / denom,
                    "selected_odds": num(a.get("price_american")),
                },
            ])

    # TOTAL: same book, exact line OVER/UNDER pair.
    tot = d[
        d["_market"].eq("TOTAL")
        & d["_side"].isin(["OVER", "UNDER"])
        & d["_line"].notna()
    ].copy()
    if not tot.empty:
        tot["_line_key"] = tot["_line"].round(4)
        for (event, book, line), g in tot.groupby(
            ["_event", "_book", "_line_key"], dropna=False
        ):
            over = g[g["_side"].eq("OVER")]
            under = g[g["_side"].eq("UNDER")]
            if over.empty or under.empty:
                continue
            o = over.iloc[-1]
            u = under.iloc[-1]
            po = num(o["_implied"])
            pu = num(u["_implied"])
            if po is None or pu is None or po + pu <= 0:
                continue
            denom = po + pu
            out_rows.extend([
                {
                    "event": event,
                    "market": "TOTAL",
                    "selection_key": "OVER",
                    "line": float(line),
                    "book": book,
                    "fair_probability": po / denom,
                    "selected_odds": num(o.get("price_american")),
                },
                {
                    "event": event,
                    "market": "TOTAL",
                    "selection_key": "UNDER",
                    "line": float(line),
                    "book": book,
                    "fair_probability": pu / denom,
                    "selected_odds": num(u.get("price_american")),
                },
            ])

    if not out_rows:
        return {}, {}

    fair = pd.DataFrame(out_rows)
    result = {}
    group_cols = [
        "event", "market", "selection_key", "line"
    ]
    for keys, g in fair.groupby(
        group_cols, dropna=False
    ):
        event, market, selection_key, line = keys
        line_num = None if pd.isna(line) else float(line)
        line_text = "" if line_num is None else f"{line_num:.4f}"
        key = "|".join([
            clean(event),
            clean(market).upper(),
            clean(selection_key).upper(),
            line_text,
        ])
        result[key] = {
            "fair_probability": round(
                float(g["fair_probability"].median()), 8
            ),
            "paired_books": int(g["book"].nunique()),
            "median_selected_odds": (
                None
                if g["selected_odds"].dropna().empty
                else round(
                    float(g["selected_odds"].dropna().median()),
                    2,
                )
            ),
        }

    meta = {}
    for event, g in d.groupby("_event"):
        meta[event] = {
            "away_team": clean(g.iloc[-1].get("away_team")),
            "home_team": clean(g.iloc[-1].get("home_team")),
        }
    return result, meta


def history_market(row):
    return clean(row.get("market")).upper()


def history_line(row):
    payload = parse_json(row.get("payload_json"))
    for value in [
        row.get("line"),
        payload.get("line_group"),
        payload.get("line"),
    ]:
        x = num(value)
        if x is not None:
            return x
    return None


def history_selection_key(sport, row, meta, event):
    market = history_market(row)
    payload = parse_json(row.get("payload_json"))
    if market == "TOTAL":
        selection = clean(
            payload.get("selection_canonical")
            or payload.get("selection")
            or row.get("selection")
        ).upper()
        return selection if selection in {"OVER", "UNDER"} else None

    side = base.history_side(sport, row)
    if sport == "NFL" and side is None:
        side = base.resolve_nfl_side(row, meta, event)
    return side if side in {"HOME", "AWAY"} else None


def current_market(row):
    return clean(
        row.get("market")
        or row.get("market_canonical")
    ).upper()


def current_line(row):
    for key in ["line_group", "line"]:
        x = num(row.get(key))
        if x is not None:
            return x
    return None


def current_selection_key(sport, row, meta, event):
    market = current_market(row)
    if market == "TOTAL":
        selection = clean(
            row.get("selection_canonical")
            or row.get("selection")
        ).upper()
        return selection if selection in {"OVER", "UNDER"} else None

    side = base.current_side(sport, row)
    if sport == "NFL" and side is None:
        selection = base.norm(row.get("selection"))
        m = meta.get(event, {})
        if selection == base.norm(m.get("away_team")):
            side = "AWAY"
        elif selection == base.norm(m.get("home_team")):
            side = "HOME"
    return side if side in {"HOME", "AWAY"} else None


def market_lookup_key(event, market, selection_key, line):
    line_text = ""
    if market != "MONEYLINE":
        line = num(line)
        if line is None:
            return ""
        line_text = f"{line:.4f}"
    return "|".join([
        clean(event),
        clean(market).upper(),
        clean(selection_key).upper(),
        line_text,
    ])


def historical_rows(sport):
    path = HISTORY_FILES[sport]
    if not path.exists():
        return pd.DataFrame()
    d = pd.read_csv(path, low_memory=False)
    if (
        d.empty
        or "lane" not in d.columns
        or "grade" not in d.columns
        or "market" not in d.columns
    ):
        return pd.DataFrame()
    d = d[
        d["lane"].astype(str).str.upper().eq("GAME")
        & d["market"].astype(str).str.upper().isin(MARKETS)
        & d["grade"].astype(str).str.upper().isin(["WIN", "LOSS"])
    ].copy()
    if d.empty:
        return d

    d["_snapshot_sort"] = pd.to_datetime(
        d.get("snapshot_at"), errors="coerce", utc=True
    )
    d["_market_key"] = d["market"].astype(str).str.upper()
    d["_selection_key"] = d.get(
        "selection", pd.Series("", index=d.index)
    ).map(base.norm)

    # Freeze the first available pregame decision snapshot per game/market.
    first_snapshot = d.groupby(
        ["game_key", "_market_key"], dropna=False
    )["_snapshot_sort"].transform("min")
    d = d[d["_snapshot_sort"].eq(first_snapshot)].copy()
    if d.empty:
        return d

    def price_and_books(row):
        payload = parse_json(row.get("payload_json"))
        price = num(payload.get("median_price_american"))
        if price is None or abs(price) < 100:
            price = num(payload.get("price_median"))
        if (
            (price is None or abs(price) < 100)
            and clean(row.get("market")).upper() == "MONEYLINE"
        ):
            candidate = num(row.get("line"))
            if candidate is not None and abs(candidate) >= 100:
                price = candidate
        books = int(num(payload.get("sportsbook_count")) or 0)
        if price is None or abs(price) < 100:
            return 999.0, books
        implied = (
            100.0 / (price + 100.0)
            if price > 0
            else abs(price) / (abs(price) + 100.0)
        )
        return abs(implied - 0.5), books

    ranked = d.apply(price_and_books, axis=1)
    d["_price_distance"] = [x[0] for x in ranked]
    d["_book_count_rank"] = [x[1] for x in ranked]

    # Keep one canonical line per game/market/selection from that frozen
    # snapshot. This prevents alternate-line menus from multiplying evidence.
    d = (
        d.sort_values(
            [
                "game_key",
                "_market_key",
                "_selection_key",
                "_price_distance",
                "_book_count_rank",
            ],
            ascending=[True, True, True, True, False],
        )
        .drop_duplicates(
            ["game_key", "_market_key", "_selection_key"],
            keep="first",
        )
        .copy()
    )
    return d


def history_for_sport(sport, prior_history=None):
    d = historical_rows(sport)
    prior_history = dict(prior_history or {})
    stats = {
        market: {
            "settled_pregame_rows": 0,
            "matched": 0,
            "matched_2plus": 0,
            "no_recent_snapshot": 0,
            "no_exact_market": 0,
            "no_selection_key": 0,
            "post_start_rejected": 0,
        }
        for market in MARKETS
    }
    if d.empty:
        return {}, stats

    files = base.history_market_files(sport)
    index = sorted(
        (base.file_timestamp(f), f)
        for f in files
        if pd.notna(base.file_timestamp(f))
    )
    times = [t for t, _ in index]
    assignments = {}

    for idx, row in d.iterrows():
        market = history_market(row)
        snap = parse_dt(row.get("snapshot_at"))
        payload = parse_json(row.get("payload_json"))
        start = (
            parse_dt(row.get("start"))
            or parse_dt(payload.get("start_dt"))
            or parse_dt(payload.get("start"))
        )
        if snap is None:
            continue
        if start is not None and snap >= start:
            stats[market]["post_start_rejected"] += 1
            continue
        stats[market]["settled_pregame_rows"] += 1
        rec_key = base.recommendation_key(sport, row)
        cached = prior_history.get(rec_key)
        if cached:
            stats[market]["matched"] += 1
            if int(num(cached.get("paired_books")) or 0) >= MIN_PAIRED_BOOKS_FOR_MODEL:
                stats[market]["matched_2plus"] += 1
            continue

        pos = bisect.bisect_right(times, snap) - 1
        if pos < 0:
            stats[market]["no_recent_snapshot"] += 1
            continue
        market_time, market_file = index[pos]
        age = (snap - market_time).total_seconds() / 60.0
        if age < 0 or age > MAX_ARCHIVE_AGE_MINUTES:
            stats[market]["no_recent_snapshot"] += 1
            continue
        assignments.setdefault(
            market_file, []
        ).append((idx, age))

    out = dict(prior_history)
    for market_file, members in assignments.items():
        targets = {}
        for member_idx, _ in members:
            member = d.loc[member_idx]
            member_market = history_market(member)
            if member_market == "MONEYLINE":
                targets["MONEYLINE"] = None
            else:
                member_line = history_line(member)
                if member_line is not None:
                    targets.setdefault(member_market, set()).add(member_line)

        fmap, meta = fair_map_all(sport, market_file, targets=targets)
        for idx, age in members:
            row = d.loc[idx]
            market = history_market(row)
            event = base.event_identity_from_history(sport, row)
            if not event:
                stats[market]["no_exact_market"] += 1
                continue
            selection_key = history_selection_key(
                sport, row, meta, event
            )
            if not selection_key:
                stats[market]["no_selection_key"] += 1
                continue
            line = None if market == "MONEYLINE" else history_line(row)
            key = market_lookup_key(
                event, market, selection_key, line
            )
            result = fmap.get(key)
            if not result:
                stats[market]["no_exact_market"] += 1
                continue
            rec_key = base.recommendation_key(sport, row)
            out[rec_key] = {
                **result,
                "market": market,
                "selection_key": selection_key,
                "line": line,
                "market_snapshot_age_minutes": round(
                    float(age), 3
                ),
                "event_identity": event,
            }
            stats[market]["matched"] += 1
            if result["paired_books"] >= MIN_PAIRED_BOOKS_FOR_MODEL:
                stats[market]["matched_2plus"] += 1

    for market in MARKETS:
        n = stats[market]["settled_pregame_rows"]
        stats[market]["coverage_pct"] = (
            round(100 * stats[market]["matched"] / n, 1)
            if n else None
        )
        stats[market]["coverage_2plus_pct"] = (
            round(
                100 * stats[market]["matched_2plus"] / n,
                1,
            )
            if n else None
        )
    return out, stats


def current_for_sport(sport):
    raw_path = base.raw_current_path(sport)
    fmap, meta = (
        fair_map_all(sport, raw_path)
        if raw_path.exists()
        else ({}, {})
    )
    decision_path = CURRENT_DECISIONS[sport]
    stats = {
        market: {
            "decision_rows": 0,
            "matched": 0,
            "matched_2plus": 0,
        }
        for market in MARKETS
    }
    if not decision_path.exists():
        return {}, stats
    d = pd.read_csv(decision_path, low_memory=False)
    if d.empty:
        return {}, stats

    out = {}
    for _, row in d.iterrows():
        market = current_market(row)
        if market not in MARKETS:
            continue
        stats[market]["decision_rows"] += 1
        event = base.event_identity_from_current(sport, row)
        if not event:
            continue
        selection_key = current_selection_key(
            sport, row, meta, event
        )
        if not selection_key:
            continue
        line = None if market == "MONEYLINE" else current_line(row)
        key = market_lookup_key(
            event, market, selection_key, line
        )
        result = fmap.get(key)
        if not result:
            continue
        current_key = "|".join([
            clean(row.get("game_key")),
            market,
            selection_key,
            "" if line is None else f"{line:.4f}",
        ])
        out[current_key] = {
            **result,
            "market": market,
            "selection_key": selection_key,
            "line": line,
            "event_identity": event,
        }
        stats[market]["matched"] += 1
        if result["paired_books"] >= MIN_PAIRED_BOOKS_FOR_MODEL:
            stats[market]["matched_2plus"] += 1
    return out, stats


def main():
    current_only = "--current-only" in sys.argv
    prior = {}
    if current_only and OUT.exists():
        try:
            prior = json.loads(OUT.read_text())
        except Exception:
            prior = {}

    history = {}
    current = {}
    coverage = {}
    for sport in SPORTS:
        if current_only and prior.get("history", {}).get(sport) is not None:
            history[sport] = prior.get("history", {}).get(sport, {})
            prior_cov = prior.get("coverage", {}).get(sport, {})
            hist = {
                market: {
                    k: v
                    for k, v in prior_cov.get(market, {}).items()
                    if not str(k).startswith("current_")
                }
                for market in MARKETS
            }
        else:
            history[sport], hist = history_for_sport(sport)

        current[sport], cur = current_for_sport(sport)
        coverage[sport] = {}
        for market in MARKETS:
            coverage[sport][market] = {
                **hist.get(market, {}),
                **{
                    f"current_{k}": v
                    for k, v in cur[market].items()
                },
                "current_fair_keys": sum(
                    1
                    for value in current[sport].values()
                    if value.get("market") == market
                ),
            }

    payload = {
        "status": "READY",
        "method": (
            "SAME_BOOK_PAIR_DEVIG_BY_GAME_MARKET_LINE_"
            "THEN_MEDIAN_ACROSS_BOOKS"
        ),
        "markets": list(MARKETS),
        "max_archive_age_minutes": MAX_ARCHIVE_AGE_MINUTES,
        "minimum_paired_books_for_model": MIN_PAIRED_BOOKS_FOR_MODEL,
        "coverage": coverage,
        "history": history,
        "current": current,
        "rules": [
            "Moneyline requires a same-book HOME/AWAY pair.",
            "Spread requires complementary HOME/AWAY lines at the same sportsbook.",
            "Total requires an exact-line OVER/UNDER pair at the same sportsbook.",
            "Each sportsbook is de-vigged before fair probabilities are combined across books.",
            "Historical snapshots must be pregame, at or before the frozen recommendation, and no more than 30 minutes old.",
            "At least two paired sportsbooks are required before fair probability can replace raw implied probability in V2.",
            "A spread or total number is never interpreted as American odds.",
        ],
    }
    for path in (OUT, PUBLIC):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))
    if DIST.exists():
        DIST.write_text(json.dumps(payload, indent=2))

    print(json.dumps({
        "status": "READY",
        "coverage": coverage,
    }, indent=2))


if __name__ == "__main__":
    main()
