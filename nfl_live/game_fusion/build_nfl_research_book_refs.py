#!/usr/bin/env python3
"""Source-anchored, research-only NFL two-sided bookmaker quote references.

Never repairs the stale primary NFL market by quietly substituting a different
provider. Never emits a betting PLAY, an inferred main line, or an executable
price claim. Only publishes independently matched official fixtures and
exact two-sided, same-book, same-source-time archived sportsbook snapshots.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "SPORTWIZZARD_ARCHIVED_SAME_BOOK_TWO_SIDED_RESEARCH"
ARCHIVE_PATTERN = re.compile(r"^NFL_GAME_SPORTWIZZARD_(\d{8}T\d{6}Z)\.csv$")
CANONICAL_ESPN = {"JAC": "JAX", "WSH": "WAS", "LA": "LAR"}
PREFERRED = ("fanduel", "draftkings", "pinnacle", "betmgm",
             "fanatics", "caesars", "betparx", "ballybet", "hardrock", "thescore")
MAX_START_DIFF_SECONDS = 180
MARKETS = ("MONEYLINE", "SPREAD", "TOTAL")


def utc(value):
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError, OverflowError):
        return None


def canon(value):
    name = str(value or "").strip().upper()
    return CANONICAL_ESPN.get(name, name)


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None


def implied(american):
    a = number(american)
    if a is None or abs(a) < 100 or abs(a) > 20000:
        return None
    return (-a / (100 - a)) if a < 0 else (100 / (100 + a))


def archived_capture(root, original):
    """Timestamp only counts if the source bytes equal latest archived copy."""
    archive_dir = root / "nfl_live/game_fusion/history"
    candidates = sorted(archive_dir.glob("NFL_GAME_SPORTWIZZARD_*.csv"))
    if not candidates:
        return None, None
    snapshot = candidates[-1]
    match = ARCHIVE_PATTERN.fullmatch(snapshot.name)
    if not match or not original.exists():
        return None, None
    original_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    if hashlib.sha256(snapshot.read_bytes()).hexdigest() != original_hash:
        return None, None
    dt = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    return dt, {"archive": str(snapshot.relative_to(root)), "sha256": original_hash}


def _book_pair(book_rows, market, capture, now):
    """Select only UNIQUE paired lines; ambiguity is a reject, not guess."""
    subtype = {"MONEYLINE": "MONEYLINE", "SPREAD": "SPREAD",
               "TOTAL": "TOTAL_POINTS"}[market]
    candidates = [r for r in book_rows if
                  str(r.get("market", "")).upper() == market and
                  str(r.get("market_subtype", "")).upper() == subtype]
    if not candidates:
        return None

    groups = defaultdict(lambda: defaultdict(list))
    for row in candidates:
        side = str(row.get("team_side" if market != "TOTAL" else "side") or "").upper()
        if side not in (("HOME", "AWAY") if market != "TOTAL" else ("OVER", "UNDER")):
            continue
        price = number(row.get("price_american"))
        start = utc(row.get("start"))
        updated = utc(row.get("updated"))
        if (implied(price) is None or start is None or updated is None or
            updated > capture or updated > now or
            (capture - updated).total_seconds() < -300):
            continue
        line = number(row.get("line"))
        if market == "MONEYLINE":
            if line is not None:
                continue
            key = "moneyline"
        else:
            if line is None or abs(line) > 100:
                continue
            key = round(abs(line) if market == "SPREAD" else line, 3)
        groups[key][side].append((row, updated, price, line))

    valid = []
    side1, side2 = ("OVER", "UNDER") if market == "TOTAL" else ("HOME", "AWAY")
    for key, sides in groups.items():
        first, second = sides[side1], sides[side2]
        # This also quarantines conflicting duplicate same-book prices.
        if len(first) != 1 or len(second) != 1:
            continue
        a, b = first[0], second[0]
        if abs((a[1] - b[1]).total_seconds()) > 180:
            continue
        if market == "SPREAD" and abs(a[3] + b[3]) > 0.001:
            continue
        if market == "TOTAL" and abs(a[3] - b[3]) > 0.001:
            continue
        if market != "MONEYLINE":
            # Extremes are usually alternative lines. Do not call them main.
            if any(q < -140 or q > 115 for q in (a[2], b[2])):
                continue
        hold = implied(a[2]) + implied(b[2]) - 1
        if not (0 <= hold <= 0.16):
            continue
        valid.append((key, a, b))

    # More than one plausible line is ambiguous and must be excluded.
    if len(valid) != 1:
        return None
    key, a, b = valid[0]
    return {
        "market": market,
        "book": str(a[0]["sportsbook"]).lower(),
        "source_event_id": str(a[0]["event_id"]),
        "source_updated_at": min(a[1], b[1]).isoformat(),
        "source_captured_at": capture.isoformat(),
        "line": None if market == "MONEYLINE" else key,
        "home_line": a[3] if market == "SPREAD" else None,
        "away_line": b[3] if market == "SPREAD" else None,
        "home_price": int(a[2]) if market != "TOTAL" else None,
        "away_price": int(b[2]) if market != "TOTAL" else None,
        "over_price": int(a[2]) if market == "TOTAL" else None,
        "under_price": int(b[2]) if market == "TOTAL" else None,
        "quote_type": "TWO_SIDED_ARCHIVED_RESEARCH_SNAPSHOT",
        "is_verified_main_line": False,
        "is_executable_current_offer": False,
        "is_approved_bet": False,
    }


def quote_is_recent(quote, game_start, now):
    updated = utc(quote.get("source_updated_at"))
    captured = utc(quote.get("source_captured_at"))
    start = utc(game_start)
    if not updated or not captured or not start or now >= start:
        return False
    if updated > captured or captured > now:
        return False
    remaining = (start - now).total_seconds() / 3600
    allowed = 6.0 if remaining <= 24 else 24.0
    return (now - updated).total_seconds() / 3600 <= allowed and (now - captured).total_seconds() / 3600 <= allowed


def research_payload(rows, scoreboard, capture, original, now):
    official = {}
    for g in scoreboard.get("next_games", []):
        eid = str(g.get("event_id") or "").strip()
        start = utc(g.get("start_time"))
        away = canon(g.get("away_abbr"))
        home = canon(g.get("home_abbr"))
        if not eid or not start or not away or not home or away == home:
            continue
        key = (away, home)
        official[key] = None if key in official else {
            "official_espn_event_id": eid,
            "official_start": start, "away": away, "home": home,
            "source_game_label": str(g.get("away_abbr")) + "@" + str(g.get("home_abbr")),
        }

    source_games = defaultdict(list)
    for r in rows:
        away, home = canon(r.get("away_abbr")), canon(r.get("home_abbr"))
        game = official.get((away, home))
        event_start = utc(r.get("start"))
        if (not game or not event_start or
            str(r.get("game_key") or "") != f"{away}@{home}" or
            abs((event_start - game["official_start"]).total_seconds()) > MAX_START_DIFF_SECONDS or
            not str(r.get("event_id") or "").strip()):
            continue
        source_games[(away, home)].append(r)

    fixtures = []
    reasons = Counter()
    for (away, home), group in sorted(source_games.items()):
        official_game = official[(away, home)]
        source_ids = {str(r["event_id"]) for r in group}
        if len(source_ids) != 1 or official_game["official_start"] <= now:
            reasons["SOURCE_GAME_ID_CONFLICT_OR_ALREADY_STARTED"] += 1
            continue
        matched = {}
        by_book = defaultdict(list)
        for r in group:
            by_book[str(r.get("sportsbook") or "").lower()].append(r)
        for market in MARKETS:
            for bookmaker in PREFERRED:
                reference = _book_pair(by_book.get(bookmaker, []), market, capture, now)
                if reference is None:
                    continue
                # A research reference with a validated event is not a PLAY.
                if quote_is_recent(reference, official_game["official_start"], now):
                    matched[market] = reference
                    break
            if market not in matched:
                reasons[f"{market}_NO_RECENT_UNAMBIGUOUS_PAIR"] += 1
        if not matched:
            continue
        fixtures.append({
            "game_key": f"{away}@{home}",
            "official_espn_event_id": official_game["official_espn_event_id"],
            "official_start": official_game["official_start"].isoformat(),
            "away": away, "home": home,
            "source_game_label": official_game["source_game_label"],
            "source_event_id": next(iter(source_ids)),
            "markets": matched, "approved_play": False,
        })

    return {
        "generated_at": now.isoformat(), "status": "RESEARCH_ONLY",
        "original_source": SOURCE, "original_archive": original,
        "book_prices_live_or_executable_verified": False,
        "main_line_verified": False, "model_advantage_proven": False,
        "betting_decision_created": False,
        "official_match_method": "EXACT_TEAMS_START_WITHIN_3_MINUTES_UNIQUE_EVENT",
        "freshness_policy": "MAX_24H_IF_GT_24H_TO_KICKOFF_ELSE_6H",
        "paired_quote_games": len(fixtures),
        "paired_market_counts": dict(Counter(m for f in fixtures for m in f["markets"])),
        "reviews": dict(reasons), "fixtures": fixtures,
    }


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def atomic_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", dir=path.parent, suffix=".tmp", delete=False) as f:
        temp = Path(f.name)
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def run(root=ROOT, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("A real UTC observation clock is required")
    raw = root / "nfl_live/game_fusion/NFL_GAME_SPORTWIZZARD_RAW.csv"
    snapshot = root / "commercial_web/public/nfl_scores.json"
    if not raw.exists() or not snapshot.exists():
        raise RuntimeError("Source data or ESPN official game scoreboard unavailable; output untouched")
    capture, source = archived_capture(root, raw)
    if not capture or capture > now:
        raise RuntimeError("Original market source missing or archive checksum mismatch; output untouched")
    original_rows = read_csv(raw)
    official_scoreboard = json.loads(snapshot.read_text())
    payload = research_payload(original_rows, official_scoreboard, capture, source, now)
    # Independent historical comparison channel. Recompute from the same
    # archived SHA-verified rows at the original capture clock, *never* using
    # the current clock for eligibility or copying a stale quote into fixtures.
    # A later automatic refresh may have zero fresh quotes; this separate
    # archive still permits a prominently EXPIRED Saturday preview.
    archived = research_payload(original_rows, official_scoreboard, capture, source, capture)
    payload["archived_snapshot"] = {
        "status": "ARCHIVED_SOURCE_ONLY_NOT_CURRENT",
        "source_captured_at": capture.isoformat(),
        "original_archive_sha256": source["sha256"],
        "is_current_quote": False,
        "is_approved_bet": False,
        "model_advantage_proven": False,
        "paired_quote_games_at_capture": archived["paired_quote_games"],
        "fixtures": archived["fixtures"],
    }
    output = root / "commercial_web/public/nfl_research_book_refs.json"
    atomic_json(output, payload)
    if (root / "commercial_web/dist").is_dir():
        atomic_json(root / "commercial_web/dist/nfl_research_book_refs.json", payload)
    return payload


if __name__ == "__main__":
    output = run()
    print(json.dumps({
        "status": output["status"],
        "paired_quote_games": output["paired_quote_games"],
        "paired_market_counts": output["paired_market_counts"],
        "reviews": output["reviews"],
        "book_prices_live_or_executable_verified": False,
        "model_advantage_proven": False,
    }, indent=2))
