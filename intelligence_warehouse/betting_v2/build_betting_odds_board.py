#!/usr/bin/env python3
"""Publish a priced *research* board without inventing verified bet opportunities.

Exact sportsbook-market-line pairs only; user-facing price shopping does NOT
constitute positive EV, real-time executable pricing, model edge, or a bet.
No provider API calls. Never writes original sources/ledgers.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "commercial_web/public/betting_odds_board.json"
DIST = ROOT / "commercial_web/dist/betting_odds_board.json"
SOURCES = {
    "NFL": "nfl_live/game_fusion/NFL_GAME_SPORTWIZZARD_RAW.csv",
    "CFB": "cfb_live/markets/current/CFB_GAME_MARKET.csv",
    "CBB": "cbb_live/markets/current/CBB_GAME_MARKET.csv",
    "MLB": "mlb_live/markets/current/MLB_GAME_MARKET.csv",
    "NBA": "nba_live/markets/current/NBA_GAME_MARKET.csv",
    "NHL": "nhl_live/markets/current/NHL_GAME_MARKET.csv",
}
TOTAL_SUBTYPES = {
    "NFL": "TOTAL_POINTS", "CFB": "TOTAL_POINTS",
    "CBB": "TOTAL_POINTS", "MLB": "TOTAL_RUNS",
    "NBA": "TOTAL_POINTS", "NHL": "TOTAL_GOALS",
}
SUPPORTED = ("MONEYLINE", "SPREAD", "TOTAL")
SIDES = {
    "MONEYLINE": ("AWAY", "HOME"),
    "SPREAD": ("AWAY", "HOME"),
    "TOTAL": ("OVER", "UNDER"),
}
# Compare common, recognizable sportsbook markets. Source availability, legal
# eligibility and quote executability are NOT verified or implied.
COMPARABLE_BOOKS = {
    "fanduel", "draftkings", "betmgm", "caesars", "fanatics",
    "betrivers", "hardrock", "pinnacle", "bet365", "betparx",
    "espnbet", "ballybet", "betway", "unibet", "thescore",
    "betonlineag", "betus", "bovada", "circa",
}


def ts(value):
    try:
        date = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        return date.astimezone(timezone.utc) if date.tzinfo else None
    except (ValueError, TypeError):
        return None


def number(value):
    try:
        if value is None or value == "":
            return None
        v = float(value)
        return v if math.isfinite(v) else None
    except (ValueError, TypeError):
        return None


def implied(american):
    a = number(american)
    if a is None or not (100 <= abs(a) <= 20000):
        return None
    return abs(a) / (100 + abs(a)) if a < 0 else 100 / (100 + a)


def valid_main_market(row, sport):
    market = str(row.get("market") or "").upper()
    subtype = str(row.get("market_subtype") or "").upper()
    return (market in SUPPORTED and subtype == (
        "MONEYLINE" if market == "MONEYLINE"
        else "SPREAD" if market == "SPREAD"
        else TOTAL_SUBTYPES[sport]
    ))


def canonical_source(row, sport, now, nfl_capture=None):
    if not valid_main_market(row, sport):
        return None
    book = str(row.get("sportsbook") or "").lower().strip()
    side = str(row.get("side") or "").upper().strip()
    market = str(row.get("market") or "").upper()
    if book not in COMPARABLE_BOOKS or side not in SIDES[market]:
        return None
    start = ts(row.get("start"))
    observed = ts(row.get("updated" if sport == "NFL" else "captured_at"))
    capture = nfl_capture if sport == "NFL" else observed
    odds = number(row.get("price_american"))
    line = number(row.get("line"))
    if (start is None or observed is None or capture is None
            or observed > now or capture > now
            or start <= now
            or implied(odds) is None):
        return None
    if (observed - capture).total_seconds() > 180:
        return None
    if market == "MONEYLINE" and line is not None:
        return None
    if market != "MONEYLINE" and (line is None or abs(line) > 500):
        return None
    # NHL puck line ±1.5 is normally juiced; we accept real quoted alternatives
    # while ranking the exact opposing line on a same-market, same-book basis.
    return {
        "provider_event_id": str(row.get("event_id") or "").strip(),
        "sport": sport, "market": market, "subtype": str(row.get("market_subtype")),
        "side": side, "book": book, "american": int(odds), "line": line,
        "away": str(row.get("away_team") or "").strip(),
        "home": str(row.get("home_team") or "").strip(),
        "game_key": str(row.get("game_key") or "").strip(),
        "start": start, "observed": observed, "capture": capture,
    }


def pair_key(r):
    market = r["market"]
    if market == "MONEYLINE":
        return ("MONEYLINE", "")
    if market == "SPREAD":
        # Keep opposing spread orientation. Absolute line alone incorrectly
        # merges FAVORITE and UNDERDOG alternatives across bookmakers.
        return ("SPREAD", round(r["line"] if r["side"] == "AWAY"
                                else -r["line"], 3))
    return ("TOTAL", round(r["line"], 3))


def paired_quotes(rows):
    by_book = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for row in rows:
        by_book[(row["market"], pair_key(row)[1])][row["book"]][row["side"]].append(row)
    output = defaultdict(list)
    for key, books in by_book.items():
        market = key[0]
        first, second = SIDES[market]
        for book, sides in books.items():
            a = sides.get(first, [])
            b = sides.get(second, [])
            # Identical exact-source duplicates are fine; conflicting
            # bookmaker prices for the same outcome/line are quarantined.
            unique_a = {(x["american"], x["line"], x["observed"]): x for x in a}
            unique_b = {(x["american"], x["line"], x["observed"]): x for x in b}
            if len(unique_a) != 1 or len(unique_b) != 1:
                continue
            x, y = next(iter(unique_a.values())), next(iter(unique_b.values()))
            if (abs((x["observed"] - y["observed"]).total_seconds()) > 180
                    or abs((x["start"] - y["start"]).total_seconds()) > 180):
                continue
            if market == "SPREAD" and abs(x["line"] + y["line"]) > 0.001:
                continue
            if market == "TOTAL" and abs(x["line"] - y["line"]) > 0.001:
                continue
            pa, pb = implied(x["american"]), implied(y["american"])
            if pa is None or pb is None:
                continue
            overround = pa + pb - 1.0
            if not (0.0 <= overround <= .16):
                continue
            output[key].append({
                "book": book, "first": x, "second": y,
                "fair_first": pa / (pa + pb),
                "fair_second": pb / (pa + pb),
                "overround": overround,
            })
    return output


def best_group(groups, market):
    candidates = [(line, quotes) for (m, line), quotes in groups.items()
                  if m == market and len(quotes) >= 2]
    if not candidates:
        return None
    def score(item):
        line, quotes = item
        # First source corroboration across paired books, then balanced
        # close-to-standard prices (not a guarantee of official main line).
        typical = statistics.median(abs(q["fair_first"] - .5) for q in quotes)
        return (-len(quotes), typical, abs(float(line or 0)))
    candidates.sort(key=score)
    return candidates[0]


def research_side(market, side, quotes):
    position = SIDES[market].index(side)
    key = "first" if position == 0 else "second"
    fair = "fair_first" if position == 0 else "fair_second"
    prices = [q[key]["american"] for q in quotes]
    # Numerically larger American odds pay more for the same market+line.
    best = max(quotes, key=lambda q: q[key]["american"])
    source_row = best[key]
    typical = statistics.median(prices)
    p_best = implied(source_row["american"])
    p_typical = statistics.median(implied(x) for x in prices)
    best_vs_typical = round(100 * (p_typical - p_best), 2)
    consensus = statistics.median(q[fair] for q in quotes)
    # Shopping highlight is selective: at least three full paired books and
    # a meaningful 2.0 percentage-point improvement in break-even price.
    if best_vs_typical >= 2.0 and len(quotes) >= 3:
        label = "BETTER PRICE THAN PEERS"
    elif best_vs_typical >= .40:
        label = "SMALL PRICE IMPROVEMENT"
    else:
        label = "NEAR TYPICAL PRICE"
    return {
        "side": side,
        "line": source_row["line"],
        "best_american_odds": source_row["american"],
        "best_sportsbook": source_row["book"],
        "median_book_american_odds": int(round(typical)),
        "best_price_break_even_probability_pct": round(100 * p_best, 1),
        "typical_price_break_even_probability_pct": round(100 * p_typical, 1),
        "market_consensus_no_vig_probability_pct": round(100 * consensus, 1),
        "price_improvement_pct_points": best_vs_typical,
        "price_assessment": label,
        "source_updated_at": source_row["observed"].isoformat(),
        "provider_source_captured_at": source_row["capture"].isoformat(),
        "independent_zenith_model_probability_pct": None,
        "proven_positive_expected_value": False,
        "book_accessibility_or_executability_verified": False,
        "verified_main_line": False,
    }


def quality(rows, start, now):
    youngest = max(q["capture"] for q in rows)
    # Always historical observed quotes, never a guarantee of executable offer.
    hours_old = (now - youngest).total_seconds() / 3600
    hours_until = (start - now).total_seconds() / 3600
    allowed = 6 if hours_until <= 24 else 24
    return "RECENT_CAPTURE" if hours_old <= allowed else "STALE_RECHECK_REQUIRED"


def build_event(event_rows, now):
    orig = event_rows[0]
    sport = orig["sport"]
    starts = {r["start"] for r in event_rows}
    away = {r["away"].lower() for r in event_rows}
    home = {r["home"].lower() for r in event_rows}
    if len(away) != 1 or len(home) != 1 or not starts:
        return None
    # Original providers disagree by up to 10 minutes within the SAME UUID;
    # that is common scheduled/puck-drop clock drift, not a new game. Bound
    # it strictly and use the EARLIEST time to avoid leaking a started game.
    if (max(starts) - min(starts)).total_seconds() > 15 * 60:
        return None
    canonical_start = min(starts)
    if canonical_start <= now:
        return None
    if not orig["away"] or not orig["home"] or orig["away"].lower() == orig["home"].lower():
        return None
    groups = paired_quotes(event_rows)
    markets = {}
    for market in SUPPORTED:
        chosen = best_group(groups, market)
        if chosen is None:
            continue
        line, paired = chosen
        sides = {side: research_side(market, side, paired) for side in SIDES[market]}
        markets[market] = {
            "market": market, "line": line if market != "MONEYLINE" else None,
            "market_subtype": (TOTAL_SUBTYPES[sport] if market == "TOTAL"
                               else market),
            "paired_book_count": len(paired),
            "sides": sides,
            "best_price_is_independent_model_edge": False,
        }
    if not markets:
        return None
    freshest = max(r["capture"] for r in event_rows)
    return {
        "sport": sport,
        "provider_event_id": orig["provider_event_id"],
        "game_key": orig["game_key"] or None,
        "away": orig["away"], "home": orig["home"],
        "start": canonical_start.isoformat(),
        "provider_source_clock_spread_minutes": round((max(starts)-min(starts)).total_seconds()/60, 1),
        "source_capture_at": freshest.isoformat(),
        "capture_status": quality(event_rows, canonical_start, now),
        "event_identity_status": "SOURCE_EVENT_HOME_AWAY_KICKOFF_ONLY",
        "independent_model_value_proven": False,
        "book_price_is_not_live_or_executable": True,
        "markets": markets,
    }


def original_archive_proof(root, source_path):
    path = root / source_path
    if not path.exists():
        return None
    # Strong source readback; per-row capture and date are still required.
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"path": source_path, "sha256": sha, "size_bytes": path.stat().st_size}


def build(root=ROOT, now=None):
    now = now or datetime.now(timezone.utc)
    if not now.tzinfo:
        raise ValueError("A real timezone-aware observation clock is required")
    nfl_proof_file = root / "commercial_web/public/nfl_research_book_refs.json"
    nfl_proof = {}
    if nfl_proof_file.exists():
        nfl_proof = json.loads(nfl_proof_file.read_text())
    nfl_sha = original_archive_proof(root, SOURCES["NFL"])
    if nfl_sha and (nfl_proof.get("original_source") !=
                    "SPORTWIZZARD_ARCHIVED_SAME_BOOK_TWO_SIDED_RESEARCH" or
                    nfl_proof.get("original_archive", {}).get("sha256") != nfl_sha["sha256"]):
        nfl_sha = None
    nfl_capture = None
    # The source's original collector time is a UTC timestamp embedded in the
    # exactly SHA-equal preserved archive filename, NOT current filesystem mtime.
    if nfl_sha:
        import re
        path = str(nfl_proof["original_archive"].get("archive", ""))
        match = re.search(r"_(\d{8}T\d{6}Z)\.csv$", path)
        if match:
            nfl_capture = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        else:
            nfl_sha = None
    nfl_verified = {}
    if nfl_sha:
        for row in nfl_proof.get("archived_snapshot", {}).get("fixtures", []):
            nfl_verified[str(row.get("game_key"))] = {
                "official_espn_event_id": row.get("official_espn_event_id"),
                "event_uuid": row.get("source_event_id"),
                "official_start": ts(row.get("official_start")),
            }
    games, coverage, proofs = [], {}, {}
    for sport, source_path in SOURCES.items():
        source = original_archive_proof(root, source_path)
        if not source or (sport == "NFL" and not nfl_sha):
            coverage[sport] = {"source_rows": 0, "source_matched_games": 0, "source_status": "NO_VERIFIED_SOURCE"}
            continue
        proofs[sport] = source
        # Read source bytes once and prove that the exact bytes parsed equal
        # the published SHA256. A concurrent collector rewrite fails closed.
        raw_bytes = (root / source_path).read_bytes()
        if hashlib.sha256(raw_bytes).hexdigest() != source["sha256"]:
            coverage[sport] = {
                "source_rows": 0, "source_matched_games": 0,
                "source_status": "SOURCE_CHANGED_DURING_READ",
            }
            continue
        data = list(csv.DictReader(io.StringIO(raw_bytes.decode("utf-8"))))
        normalized = []
        for line in data:
            item = canonical_source(line, sport, now, nfl_capture=nfl_capture)
            if item and item["provider_event_id"]:
                normalized.append(item)
        by_game = defaultdict(list)
        for line in normalized:
            by_game[line["provider_event_id"]].append(line)
        count = 0
        for original_id, observed in by_game.items():
            if sport == "NFL":
                game_key = observed[0]["game_key"]
                proof = nfl_verified.get(game_key)
                if (not proof or proof["event_uuid"] != original_id or
                    proof["official_start"] is None or
                    abs((proof["official_start"] - min(r["start"] for r in observed)).total_seconds()) > 180):
                    continue
            game = build_event(observed, now)
            if not game:
                continue
            if sport == "NFL":
                game["event_identity_status"] = "EXACT_ESPN_TEAMS_KICKOFF_UNIQUE_EVENT"
                game["official_espn_event_id"] = proof["official_espn_event_id"]
            games.append(game)
            count += 1
        coverage[sport] = {
            "source_rows": len(data), "rows_valid_quote_clock_and_market": len(normalized),
            "source_matched_games": count, "source_status": "RESEARCH_ONLY",
        }
    games.sort(key=lambda game: (game["start"], game["sport"], game["away"], game["home"]))
    return {
        "generated_at": now.isoformat(), "status": "RESEARCH_ONLY",
        "method": "SAME_BOOK_TWO_SIDED_MATCH_SAME_MARKET_AND_EXACT_LINE_PRICE_SHOPPING",
        "source_proofs": proofs, "coverage": coverage,
        "game_count": len(games),
        "markets_count": dict(Counter(k for game in games for k in game["markets"])),
        "verified_positive_expected_value_bets": 0,
        "all_prices_observed_not_executable": True,
        "no_approved_pick_or_bet_created": True,
        "no_independent_market_beating_model_assumed": True,
        "price_assessment_meaning": "The observed bookmaker price has a lower break-even requirement than the median comparable book quoting that exact side and line. This is price shopping, not a proven profitable bet.",
        "games": games,
    }


def publish(root=ROOT, now=None):
    result = build(root, now)
    for target in (root / "commercial_web/public/betting_odds_board.json",
                   root / "commercial_web/dist/betting_odds_board.json"):
        if target.parent.exists():
            with NamedTemporaryFile("w", dir=target.parent, delete=False, suffix=".tmp") as out:
                temp = Path(out.name)
                json.dump(result, out, indent=2, sort_keys=True)
                out.write("\n")
                out.flush()
                os.fsync(out.fileno())
            os.replace(temp, target)
    return result


if __name__ == "__main__":
    result = publish()
    print(json.dumps({
        "status": result["status"], "games": result["game_count"],
        "markets": result["markets_count"], "coverage": result["coverage"],
        "verified_bets": result["verified_positive_expected_value_bets"],
    }, indent=2))
