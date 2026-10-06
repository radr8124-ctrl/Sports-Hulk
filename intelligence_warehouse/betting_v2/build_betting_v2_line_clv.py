#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
DEVIG = OUT_DIR / "BETTING_V2_ALL_MARKET_DEVIG.json"
FORWARD_LEDGER = OUT_DIR / "BETTING_V2_ALL_MARKETS_FORWARD_LEDGER.jsonl"
TIMELINE = OUT_DIR / "BETTING_V2_LINE_CLV_TIMELINE.jsonl"
STATE = OUT_DIR / "BETTING_V2_LINE_CLV_BACKFILL_STATE.json"
OUT = OUT_DIR / "BETTING_V2_LINE_CLV.json"
PUBLIC = ROOT / "commercial_web" / "public" / "betting_v2_line_clv.json"
DIST = ROOT / "commercial_web" / "dist" / "betting_v2_line_clv.json"

if str(OUT_DIR) not in sys.path:
    sys.path.insert(0, str(OUT_DIR))
import build_betting_v2_all_market_devig as rawdevig


def now():
    return datetime.now(timezone.utc)


def now_iso():
    return now().isoformat()


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


def parse_dt(v):
    if not v:
        return None
    text = str(v).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def read_json(path, fallback=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {} if fallback is None else fallback


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def read_jsonl(path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as h:
        h.write(json.dumps(row, separators=(",", ":")) + "\n")


def canonical_forward():
    out = {}
    for event in read_jsonl(FORWARD_LEDGER):
        key = event.get("forward_key")
        if key:
            out[key] = {**out.get(key, {}), **event}
    return out


def histories():
    out = defaultdict(list)
    for row in read_jsonl(TIMELINE):
        key = row.get("forward_key")
        if key:
            out[key].append(row)
    for rows in out.values():
        rows.sort(key=lambda r: r.get("captured_at") or "")
    return out


def parse_devig_key(key):
    parts = clean(key).split("|")
    if len(parts) < 4:
        return None
    return {
        "game_key": "|".join(parts[:-3]),
        "market": parts[-3].upper(),
        "selection_key": parts[-2].upper(),
        "line": num(parts[-1]),
    }


def implied_probability(odds):
    odds = num(odds)
    if odds is None or abs(odds) < 100:
        return None
    return (
        100.0 / (odds + 100.0)
        if odds > 0
        else abs(odds) / (abs(odds) + 100.0)
    )


def devig_index():
    payload = read_json(DEVIG, {})
    index = defaultdict(list)
    for sport, rows in (payload.get("current") or {}).items():
        for key, value in (rows or {}).items():
            parsed = parse_devig_key(key)
            if not parsed:
                continue
            index[(
                clean(sport).upper(),
                parsed["game_key"],
                parsed["market"],
                parsed["selection_key"],
            )].append({
                **parsed,
                "fair_probability": num(value.get("fair_probability")),
                "paired_books": int(num(value.get("paired_books")) or 0),
                "median_selected_odds": num(value.get("median_selected_odds")),
            })
    return index


def line_family_window(sport, market):
    sport = clean(sport).upper()
    market = clean(market).upper()
    if market == "TOTAL":
        return {
            "NBA": 30.0,
            "CFB": 20.0,
            "NFL": 20.0,
            "MLB": 4.0,
            "NHL": 2.5,
        }.get(sport, 15.0)
    if market == "SPREAD":
        return {
            "NBA": 15.0,
            "CFB": 20.0,
            "NFL": 20.0,
            "MLB": 5.0,
            "NHL": 4.0,
        }.get(sport, 12.0)
    return None


def choose_main_quote(records, entry_line=None, sport=None, market=None):
    family_records = list(records)
    entry_line = num(entry_line)
    window = line_family_window(sport, market)
    if entry_line is not None and window is not None:
        nearby = [
            r for r in family_records
            if r.get("line") is not None
            and abs(float(r["line"]) - entry_line) <= window
        ]
        if nearby:
            family_records = nearby

    usable = [
        r for r in family_records
        if r.get("fair_probability") is not None
        and int(r.get("paired_books") or 0) >= 2
    ]
    if not usable:
        usable = [
            r for r in family_records
            if r.get("fair_probability") is not None
            and int(r.get("paired_books") or 0) >= 1
        ]
    if not usable:
        return None

    max_books = max(int(r.get("paired_books") or 0) for r in usable)
    finalists = [
        r for r in usable
        if int(r.get("paired_books") or 0) >= max(1, max_books - 1)
    ]
    finalists.sort(
        key=lambda r: (
            abs(float(r["fair_probability"]) - 0.5),
            -int(r.get("paired_books") or 0),
            abs(
                (implied_probability(r.get("median_selected_odds")) or 0.5)
                - 0.5
            ),
        )
    )
    return finalists[0]


def choose_exact_quote(records, entry_line):
    entry_line = num(entry_line)
    if entry_line is None:
        return None
    exact = [
        r for r in records
        if r.get("line") is not None
        and abs(float(r["line"]) - entry_line) < 1e-6
        and r.get("fair_probability") is not None
    ]
    if not exact:
        return None
    exact.sort(
        key=lambda r: (
            -int(r.get("paired_books") or 0),
            abs(float(r["fair_probability"]) - 0.5),
        )
    )
    return exact[0]


def quote_quality(event_start, captured_at):
    start = parse_dt(event_start)
    captured = parse_dt(captured_at)
    if start is None or captured is None:
        return None, "UNKNOWN"
    minutes = (start - captured).total_seconds() / 60.0
    if minutes < 0:
        return round(minutes, 2), "POST_START_INVALID"
    if minutes <= 60:
        return round(minutes, 2), "CLOSE_PROXY"
    if minutes <= 120:
        return round(minutes, 2), "NEAR_CLOSE"
    return round(minutes, 2), "EARLY_LAST_AVAILABLE"


def timeline_event(entry, records, captured_at, source):
    main = choose_main_quote(
        records,
        entry_line=entry.get("line"),
        sport=entry.get("sport"),
        market=entry.get("market"),
    )
    if main is None:
        return None
    exact = choose_exact_quote(records, entry.get("line"))
    minutes, quality = quote_quality(
        entry.get("event_start"), captured_at
    )
    return {
        "event_type": "LINE_MARKET_SNAPSHOT",
        "captured_at": captured_at,
        "snapshot_source": source,
        "forward_key": entry.get("forward_key"),
        "model_version": entry.get("model_version"),
        "lane_key": entry.get("lane_key"),
        "sport": clean(entry.get("sport")).upper(),
        "game_key": clean(entry.get("game_key")),
        "market": clean(entry.get("market")).upper(),
        "selection": entry.get("selection"),
        "selection_key": clean(entry.get("selection_key")).upper(),
        "entry_line": num(entry.get("line")),
        "entry_probability_pct": num(
            entry.get("entry_market_reference_probability_pct")
        ),
        "event_start": entry.get("event_start"),
        "minutes_before_start": minutes,
        "quote_quality": quality,
        "main_line": num(main.get("line")),
        "main_fair_probability_pct": (
            None
            if main.get("fair_probability") is None
            else round(100 * float(main["fair_probability"]), 4)
        ),
        "main_selected_odds": num(main.get("median_selected_odds")),
        "main_paired_books": int(main.get("paired_books") or 0),
        "exact_entry_line_fair_probability_pct": (
            None
            if exact is None or exact.get("fair_probability") is None
            else round(100 * float(exact["fair_probability"]), 4)
        ),
        "exact_entry_line_selected_odds": (
            None if exact is None else num(exact.get("median_selected_odds"))
        ),
        "exact_entry_line_paired_books": (
            0 if exact is None else int(exact.get("paired_books") or 0)
        ),
    }


def signature(row):
    return (
        row.get("main_line"),
        row.get("main_fair_probability_pct"),
        row.get("main_paired_books"),
        row.get("exact_entry_line_fair_probability_pct"),
        row.get("exact_entry_line_paired_books"),
        row.get("quote_quality"),
    )


def latest_signatures():
    latest = {}
    for key, rows in histories().items():
        if rows:
            latest[key] = signature(rows[-1])
    return latest


def snapshot_current():
    entries = canonical_forward()
    index = devig_index()
    latest = latest_signatures()
    added = 0
    skipped = 0

    for key, entry in entries.items():
        start = parse_dt(entry.get("event_start"))
        captured = parse_dt(entry.get("captured_at"))
        if start is None or captured is None or now() >= start:
            continue

        sport = clean(entry.get("sport")).upper()
        market = clean(entry.get("market")).upper()
        selection_key = clean(entry.get("selection_key")).upper()
        game_key = clean(entry.get("game_key"))
        records = index.get(
            (sport, game_key, market, selection_key), []
        )
        if not records:
            skipped += 1
            continue

        event = timeline_event(
            entry, records, now_iso(), "CURRENT_DEVIG_MARKET"
        )
        if event is None:
            skipped += 1
            continue
        if latest.get(key) == signature(event):
            continue
        append_jsonl(TIMELINE, event)
        latest[key] = signature(event)
        added += 1

    return {
        "current_snapshots_added": added,
        "current_market_missing": skipped,
    }


def game_pair(entry):
    sport = clean(entry.get("sport")).upper()
    game_key = clean(entry.get("game_key"))
    if sport == "NFL" and "@" in game_key:
        away, home = game_key.split("@", 1)
        return away, home
    parts = game_key.split("|")
    if sport in {"NBA", "NHL", "MLB"} and len(parts) >= 3:
        return parts[-2], parts[-1]
    return None


def canonical_raw_team(sport, value):
    value = clean(value)
    if not value:
        return ""
    return clean(rawdevig.base.canonical_team(sport, value))


def normalize_archived_side(sport, raw_side, away_target, home_target):
    side = clean(raw_side).upper()
    if side in {"HOME", "AWAY", "OVER", "UNDER"}:
        return side
    side_can = canonical_raw_team(sport, raw_side)
    if side_can and side_can == away_target:
        return "AWAY"
    if side_can and side_can == home_target:
        return "HOME"
    # Some historical books put Over/Under into title case or another
    # text field that canonicalizes cleanly.
    if side_can.upper() in {"OVER", "UNDER"}:
        return side_can.upper()
    return side


def target_event_frame(sport, path, pair, nfl_game_key=None):
    try:
        d = pd.read_csv(path, low_memory=False)
    except Exception:
        return None
    if d.empty:
        return None

    if sport == "NFL":
        if "game_key" not in d.columns or not nfl_game_key:
            return None
        hit = d[d["game_key"].astype(str).eq(nfl_game_key)].copy()
        if hit.empty:
            return None
        hit["_normalized_side"] = hit["side"].astype(str).str.upper()
        return hit

    if not {"event_id", "selection", "side"}.issubset(d.columns):
        return None

    away_target, home_target = pair

    # Resolve each raw event against the frozen away/home pair. Historical
    # feeds may label side as HOME/AWAY or as the actual team name, so both
    # side and team identity must agree before the event is accepted.
    event_ids = []
    for event_id, group in d.groupby("event_id"):
        # Strongest check: explicit away/home columns, when the feed populated them.
        explicit_match = False
        if "away_team" in group.columns and "home_team" in group.columns:
            for _, erow in group[["away_team", "home_team"]].drop_duplicates().iterrows():
                away_can = canonical_raw_team(sport, erow.get("away_team"))
                home_can = canonical_raw_team(sport, erow.get("home_team"))
                if away_can == away_target and home_can == home_target:
                    explicit_match = True
                    break
        if explicit_match:
            event_ids.append(event_id)
            break

        normalized_sides = group["side"].map(
            lambda v: normalize_archived_side(
                sport, v, away_target, home_target
            )
        )
        selection_can = group["selection"].map(
            lambda v: canonical_raw_team(sport, v)
        )

        away_match = (
            normalized_sides.eq("AWAY")
            & selection_can.eq(away_target)
        ).any()
        home_match = (
            normalized_sides.eq("HOME")
            & selection_can.eq(home_target)
        ).any()
        if away_match and home_match:
            event_ids.append(event_id)
            break

    if not event_ids:
        return None

    hit = d[d["event_id"].astype(str).eq(clean(event_ids[0]))].copy()
    if hit.empty:
        return None
    hit["_normalized_side"] = hit["side"].map(
        lambda v: normalize_archived_side(
            sport, v, away_target, home_target
        )
    )
    return hit


def event_fair_records(frame):
    if frame is None or frame.empty:
        return []
    market_col = (
        "market"
        if "market" in frame.columns
        else "market_subtype"
        if "market_subtype" in frame.columns
        else None
    )
    if market_col is None:
        return []
    needed = {"sportsbook", "side", "price_american"}
    if not needed.issubset(frame.columns):
        return []

    d = frame.copy()
    raw_market = d[market_col].astype(str).str.upper()
    d["_market"] = raw_market.replace({
        "H2H": "MONEYLINE",
        "MONEY LINE": "MONEYLINE",
        "SPREADS": "SPREAD",
        "TOTALS": "TOTAL",
    })
    side_source = (
        "_normalized_side"
        if "_normalized_side" in d.columns
        else "side"
    )
    d["_side"] = d[side_source].astype(str).str.upper()
    d["_line"] = pd.to_numeric(d.get("line"), errors="coerce")
    d["_odds"] = pd.to_numeric(d["price_american"], errors="coerce")
    d["_book"] = d["sportsbook"].astype(str).str.lower()
    d["_implied"] = d["_odds"].map(implied_probability)
    d = d[d["_implied"].notna()].copy()

    rows = []

    # Moneyline
    ml = d[
        d["_market"].eq("MONEYLINE")
        & d["_side"].isin(["HOME", "AWAY"])
    ]
    for book, g in ml.groupby("_book"):
        sides = {}
        for side in ("HOME", "AWAY"):
            q = g[g["_side"].eq(side)]
            if not q.empty:
                sides[side] = q.iloc[-1]
        if len(sides) != 2:
            continue
        ph = num(sides["HOME"]["_implied"])
        pa = num(sides["AWAY"]["_implied"])
        if ph is None or pa is None or ph + pa <= 0:
            continue
        denom = ph + pa
        for side, rawp in (("HOME", ph), ("AWAY", pa)):
            rows.append({
                "market": "MONEYLINE",
                "selection_key": side,
                "line": None,
                "book": book,
                "fair_probability": rawp / denom,
                "selected_odds": num(sides[side]["_odds"]),
            })

    # Spread
    sp = d[
        d["_market"].eq("SPREAD")
        & d["_side"].isin(["HOME", "AWAY"])
        & d["_line"].notna()
    ].copy()
    if not sp.empty:
        sp["_abs_line"] = sp["_line"].abs().round(4)
        for (book, abs_line), g in sp.groupby(["_book", "_abs_line"]):
            home = g[g["_side"].eq("HOME")]
            away = g[g["_side"].eq("AWAY")]
            if home.empty or away.empty:
                continue
            h = home.iloc[-1]
            a = away.iloc[-1]
            hline = num(h["_line"])
            aline = num(a["_line"])
            if hline is None or aline is None or abs(hline + aline) > 1e-6:
                continue
            ph = num(h["_implied"])
            pa = num(a["_implied"])
            if ph is None or pa is None or ph + pa <= 0:
                continue
            denom = ph + pa
            rows.extend([
                {
                    "market": "SPREAD",
                    "selection_key": "HOME",
                    "line": hline,
                    "book": book,
                    "fair_probability": ph / denom,
                    "selected_odds": num(h["_odds"]),
                },
                {
                    "market": "SPREAD",
                    "selection_key": "AWAY",
                    "line": aline,
                    "book": book,
                    "fair_probability": pa / denom,
                    "selected_odds": num(a["_odds"]),
                },
            ])

    # Total
    tot = d[
        d["_market"].eq("TOTAL")
        & d["_side"].isin(["OVER", "UNDER"])
        & d["_line"].notna()
    ].copy()
    if not tot.empty:
        tot["_line_key"] = tot["_line"].round(4)
        for (book, line), g in tot.groupby(["_book", "_line_key"]):
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
            rows.extend([
                {
                    "market": "TOTAL",
                    "selection_key": "OVER",
                    "line": float(line),
                    "book": book,
                    "fair_probability": po / denom,
                    "selected_odds": num(o["_odds"]),
                },
                {
                    "market": "TOTAL",
                    "selection_key": "UNDER",
                    "line": float(line),
                    "book": book,
                    "fair_probability": pu / denom,
                    "selected_odds": num(u["_odds"]),
                },
            ])

    if not rows:
        return []

    f = pd.DataFrame(rows)
    out = []
    for (market, selection_key, line), g in f.groupby(
        ["market", "selection_key", "line"],
        dropna=False,
    ):
        line_value = None if pd.isna(line) else float(line)
        out.append({
            "market": market,
            "selection_key": selection_key,
            "line": line_value,
            "fair_probability": float(g["fair_probability"].median()),
            "paired_books": int(g["book"].nunique()),
            "median_selected_odds": (
                None
                if g["selected_odds"].dropna().empty
                else float(g["selected_odds"].dropna().median())
            ),
        })
    return out


def archive_file_index(sport):
    rows = []
    for path in rawdevig.base.history_market_files(sport):
        stamp = rawdevig.base.file_timestamp(path)
        if stamp is not None:
            rows.append((stamp.to_pydatetime(), path))
    return sorted(rows, key=lambda x: x[0])


def archive_backfill():
    entries = canonical_forward()
    hist = histories()
    state = read_json(STATE, {})
    groups = defaultdict(list)

    for key, entry in entries.items():
        start = parse_dt(entry.get("event_start"))
        captured = parse_dt(entry.get("captured_at"))
        market = clean(entry.get("market")).upper()
        if start is None or captured is None:
            continue
        if market not in {"MONEYLINE", "SPREAD", "TOTAL"}:
            continue
        pair = game_pair(entry)
        if pair is None:
            continue
        groups[(clean(entry.get("sport")).upper(), clean(entry.get("game_key")))].append(
            (key, entry)
        )

    added = 0
    games_found = 0
    games_scanned = 0

    by_sport = defaultdict(dict)
    for (sport, game_key), rows in groups.items():
        by_sport[sport][game_key] = rows

    for sport, sport_games in by_sport.items():
        files = archive_file_index(sport)
        if not files:
            continue

        for game_key, rows in sport_games.items():
            state_key = f"{sport}|{game_key}"
            prior_state = state.get(state_key, {})
            previous_scan = parse_dt(prior_state.get("last_archive_scan_at"))

            starts = [
                parse_dt(entry.get("event_start"))
                for _, entry in rows
                if parse_dt(entry.get("event_start")) is not None
            ]
            captures = [
                parse_dt(entry.get("captured_at"))
                for _, entry in rows
                if parse_dt(entry.get("captured_at")) is not None
            ]
            if not starts or not captures:
                continue
            horizon = min(min(starts), now())
            earliest_capture = min(captures)
            if horizon <= earliest_capture:
                continue

            # If this game has timeline data newer than the archive watermark,
            # do not search behind the latest known quote.
            latest_timeline = None
            for key, _ in rows:
                for q in hist.get(key, []):
                    qt = parse_dt(q.get("captured_at"))
                    if qt is not None and (
                        latest_timeline is None or qt > latest_timeline
                    ):
                        latest_timeline = qt
            search_after = previous_scan
            if latest_timeline is not None and (
                search_after is None or latest_timeline > search_after
            ):
                search_after = latest_timeline

            candidates = [
                (stamp, path)
                for stamp, path in files
                if earliest_capture <= stamp <= horizon
                and (search_after is None or stamp > search_after)
            ]
            if not candidates:
                continue

            games_scanned += 1
            pair = game_pair(rows[0][1])
            found = None
            found_stamp = None
            # Latest first: first matching file is last available prestart.
            for stamp, path in reversed(candidates):
                frame = target_event_frame(
                    sport,
                    path,
                    pair,
                    nfl_game_key=game_key if sport == "NFL" else None,
                )
                if frame is None or frame.empty:
                    continue
                fair_records = event_fair_records(frame)
                if fair_records:
                    found = fair_records
                    found_stamp = stamp
                    break

            # Watermark the full searched horizon even when the event was absent.
            state[state_key] = {
                "last_archive_scan_at": max(stamp for stamp, _ in candidates).isoformat(),
                "latest_found_at": (
                    found_stamp.isoformat() if found_stamp is not None
                    else prior_state.get("latest_found_at")
                ),
                "last_scan_result": "FOUND" if found is not None else "NOT_FOUND",
            }

            if found is None or found_stamp is None:
                continue

            games_found += 1
            captured_at = found_stamp.isoformat()
            for key, entry in rows:
                entry_captured = parse_dt(entry.get("captured_at"))
                if entry_captured is None or found_stamp < entry_captured:
                    continue
                market = clean(entry.get("market")).upper()
                selection_key = clean(entry.get("selection_key")).upper()
                entry_records = [
                    r for r in found
                    if r.get("market") == market
                    and r.get("selection_key") == selection_key
                ]
                if not entry_records:
                    continue
                event = timeline_event(
                    entry,
                    entry_records,
                    captured_at,
                    "ARCHIVE_LAST_AVAILABLE_PRESTART",
                )
                if event is None:
                    continue
                existing_rows = hist.get(key, [])
                if existing_rows and signature(existing_rows[-1]) == signature(event):
                    continue
                append_jsonl(TIMELINE, event)
                hist[key].append(event)
                hist[key].sort(key=lambda r: r.get("captured_at") or "")
                added += 1

    write_json(STATE, state)
    return {
        "archive_snapshots_added": added,
        "archive_games_scanned": games_scanned,
        "archive_games_found": games_found,
    }


def entry_is_main_line_like(entry):
    market = clean(entry.get("market")).upper()
    if market not in {"SPREAD", "TOTAL"}:
        return False
    ref = num(entry.get("entry_market_reference_probability_pct"))
    raw = implied_probability(entry.get("entry_american_odds"))
    if ref is None or raw is None:
        return False
    return 45.0 <= ref <= 55.0 and 0.43 <= raw <= 0.57


def line_clv(entry, quote):
    market = clean(entry.get("market")).upper()
    entry_line = num(entry.get("line"))
    close_line = num(quote.get("main_line"))
    if entry_line is None or close_line is None:
        return None
    if market == "SPREAD":
        return round(entry_line - close_line, 4)
    if market == "TOTAL":
        selection = clean(entry.get("selection_key")).upper()
        if selection == "OVER":
            return round(close_line - entry_line, 4)
        if selection == "UNDER":
            return round(entry_line - close_line, 4)
    return None


def exact_probability_clv(entry, quote):
    entry_p = num(entry.get("entry_market_reference_probability_pct"))
    close_p = num(quote.get("exact_entry_line_fair_probability_pct"))
    if entry_p is None or close_p is None:
        return None
    return round(close_p - entry_p, 4)


def closed_rows():
    entries = canonical_forward()
    hist = histories()
    out = []
    now_dt = now()

    for key, entry in entries.items():
        start = parse_dt(entry.get("event_start"))
        captured = parse_dt(entry.get("captured_at"))
        if start is None or captured is None or now_dt < start:
            continue

        candidates = []
        for quote in hist.get(key, []):
            qt = parse_dt(quote.get("captured_at"))
            if qt is None or qt < captured or qt > start:
                continue
            candidates.append(quote)

        if not candidates:
            out.append({
                **entry,
                "entry_main_line_like": entry_is_main_line_like(entry),
                "line_clv_status": "NO_PRESTART_LINE_SNAPSHOT",
                "closing_line_quote_at": None,
                "closing_quote_quality": None,
                "closing_minutes_before_start": None,
                "closing_main_line": None,
                "line_clv_points": None,
                "exact_probability_clv_pp": None,
            })
            continue

        quote = candidates[-1]
        clv = line_clv(entry, quote)
        prob_clv = exact_probability_clv(entry, quote)
        out.append({
            **entry,
            "entry_main_line_like": entry_is_main_line_like(entry),
            "line_clv_status": (
                "AVAILABLE"
                if clv is not None
                else "NOT_APPLICABLE_MONEYLINE"
                if clean(entry.get("market")).upper() == "MONEYLINE"
                else "NO_COMPARABLE_LINE"
            ),
            "closing_line_quote_at": quote.get("captured_at"),
            "closing_snapshot_source": quote.get("snapshot_source"),
            "closing_quote_quality": quote.get("quote_quality"),
            "closing_minutes_before_start": num(
                quote.get("minutes_before_start")
            ),
            "closing_main_line": num(quote.get("main_line")),
            "closing_main_fair_probability_pct": num(
                quote.get("main_fair_probability_pct")
            ),
            "closing_main_paired_books": int(
                num(quote.get("main_paired_books")) or 0
            ),
            "line_clv_points": clv,
            "exact_probability_clv_pp": prob_clv,
        })
    return out


def mean(values):
    vals = [float(v) for v in values if v is not None]
    return None if not vals else round(sum(vals) / len(vals), 4)


def lcb90_by_game(rows, field):
    grouped = defaultdict(list)
    for row in rows:
        value = num(row.get(field))
        if value is None:
            continue
        block = "|".join([
            clean(row.get("sport")).upper(),
            clean(row.get("game_key")),
        ])
        grouped[block].append(value)
    values = [
        sum(vs) / len(vs)
        for vs in grouped.values()
        if vs
    ]
    n = len(values)
    if n < 2:
        return n, None
    avg = sum(values) / n
    var = sum((v-avg)**2 for v in values) / (n-1)
    se = math.sqrt(max(0.0, var) / n)
    return n, round(avg - 1.645 * se, 4)


def summarize(rows):
    spread_total_closed = [
        r for r in rows
        if clean(r.get("market")).upper() in {"SPREAD", "TOTAL"}
    ]
    diagnostic = [
        r for r in spread_total_closed
        if r.get("line_clv_status") == "AVAILABLE"
        and num(r.get("line_clv_points")) is not None
    ]
    main_like_closed = [
        r for r in spread_total_closed
        if bool(r.get("entry_main_line_like"))
    ]
    main_like = [
        r for r in diagnostic
        if bool(r.get("entry_main_line_like"))
    ]
    alt_line = [
        r for r in diagnostic
        if not bool(r.get("entry_main_line_like"))
    ]
    close_proxy = [
        r for r in main_like
        if r.get("closing_quote_quality") == "CLOSE_PROXY"
    ]
    near_close = [
        r for r in main_like
        if r.get("closing_quote_quality") == "NEAR_CLOSE"
    ]
    early = [
        r for r in main_like
        if r.get("closing_quote_quality") == "EARLY_LAST_AVAILABLE"
    ]

    proof_blocks, proof_lcb = lcb90_by_game(
        close_proxy, "line_clv_points"
    )
    exact_close_proxy = [
        r for r in close_proxy
        if num(r.get("exact_probability_clv_pp")) is not None
    ]
    exact_blocks, exact_lcb = lcb90_by_game(
        exact_close_proxy, "exact_probability_clv_pp"
    )

    return {
        "closed_spread_total_entries": len(spread_total_closed),
        "main_line_like_closed_entries": len(main_like_closed),
        "line_clv_available_any": len(diagnostic),
        "main_line_clv_available_any": len(main_like),
        "alternate_line_diagnostic_entries": len(alt_line),
        "close_proxy_line_clv_available": len(close_proxy),
        "near_close_line_clv_available": len(near_close),
        "early_last_available_line_clv": len(early),
        "missing_line_snapshot": sum(
            r.get("line_clv_status") == "NO_PRESTART_LINE_SNAPSHOT"
            for r in spread_total_closed
        ),
        "close_proxy_coverage_pct": (
            None
            if not main_like_closed
            else round(100 * len(close_proxy) / len(main_like_closed), 1)
        ),
        "avg_last_available_line_clv_points": mean([
            num(r.get("line_clv_points")) for r in main_like
        ]),
        "avg_close_proxy_line_clv_points": mean([
            num(r.get("line_clv_points")) for r in close_proxy
        ]),
        "positive_close_proxy_line_clv_rate_pct": (
            None
            if not close_proxy
            else round(
                100 * sum(
                    (num(r.get("line_clv_points")) or 0) > 0
                    for r in close_proxy
                ) / len(close_proxy),
                1,
            )
        ),
        "independent_close_proxy_games": proof_blocks,
        "close_proxy_line_clv_lcb90_points": proof_lcb,
        "exact_probability_close_proxy_available": len(exact_close_proxy),
        "independent_exact_probability_games": exact_blocks,
        "avg_exact_probability_close_proxy_clv_pp": mean([
            num(r.get("exact_probability_clv_pp"))
            for r in exact_close_proxy
        ]),
        "exact_probability_close_proxy_lcb90_pp": exact_lcb,
    }


def build_output(run):
    entries = canonical_forward()
    closed = closed_rows()
    tracked_spread_total = [
        r for r in entries.values()
        if clean(r.get("market")).upper() in {"SPREAD", "TOTAL"}
    ]
    tracked_main_like = [
        r for r in tracked_spread_total
        if entry_is_main_line_like(r)
    ]
    by_lane = {}
    lanes = sorted({
        clean(r.get("lane_key"))
        for r in entries.values()
        if clean(r.get("lane_key"))
    })
    for lane in lanes:
        by_lane[lane] = summarize([
            r for r in closed
            if clean(r.get("lane_key")) == lane
        ])

    overall_summary = summarize(closed)
    overall_summary["tracked_spread_total_entries"] = len(tracked_spread_total)
    overall_summary["tracked_main_line_like_entries"] = len(tracked_main_like)
    overall_summary["tracked_alternate_price_entries"] = (
        len(tracked_spread_total) - len(tracked_main_like)
    )
    overall_summary["timeline_snapshots"] = len(read_jsonl(TIMELINE))

    return {
        "generated_at": now_iso(),
        "status": "READY",
        "method": "FROZEN_ENTRY_TO_LAST_AVAILABLE_PRESTART_MAIN_LINE_WITH_CLOSE_QUALITY",
        "last_run": run,
        "summary": overall_summary,
        "by_lane": by_lane,
        "recent_closed": sorted(
            closed,
            key=lambda r: r.get("event_start") or "",
            reverse=True,
        )[:100],
        "definitions": {
            "close_proxy": "Last available market snapshot no more than 60 minutes before kickoff.",
            "near_close": "Last available market snapshot 61 to 120 minutes before kickoff; diagnostic only.",
            "early_last_available": "Last available market snapshot more than 120 minutes before kickoff; diagnostic only.",
            "positive_spread_clv": "Entry selected-side spread was better than the last available closing-number proxy.",
            "positive_total_clv": "Over was captured lower than the closing-number proxy or Under was captured higher.",
        },
        "rules": [
            "Entry lines come only from immutable Best Bets forward records.",
            "Current quotes use the full de-vigged market ladder even if a frozen pick is no longer qualified.",
            "Archived recovery resolves each frozen game once and reuses it across alternate-line variants.",
            "Only snapshots within 60 minutes of kickoff count as closing-line proof.",
            "Older last-available archived quotes remain diagnostic and never receive closing-line proof credit.",
            "Spread CLV is entry selected-side line minus closing selected-side line; positive is better.",
            "Over CLV is closing total minus entry total; Under CLV is entry total minus closing total; positive is better.",
            "The consensus main line comes from the most broadly paired sportsbook lines, then the fair probability nearest 50%.",
            "Exact-line probability CLV is tracked separately when the original line still exists.",
            "Alternate lines from one game are collapsed to game-block means for confidence bounds.",
            "No missing quote is replaced with the entry quote.",
        ],
    }


def main():
    current = snapshot_current()
    archive = archive_backfill()
    run = {**current, **archive}
    payload = build_output(run)
    for path in (OUT, PUBLIC):
        write_json(path, payload)
    if DIST.exists():
        write_json(DIST, payload)
    print(json.dumps({
        "status": payload["status"],
        "last_run": payload["last_run"],
        "summary": payload["summary"],
        "lanes_with_line_data": {
            lane: row
            for lane, row in payload["by_lane"].items()
            if row.get("line_clv_available_any")
        },
    }, indent=2))


if __name__ == "__main__":
    main()
