#!/usr/bin/env python3
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = ROOT / "intelligence_warehouse" / "public_performance"
PUBLIC = ROOT / "commercial_web" / "public"
DIST = ROOT / "commercial_web" / "dist"
LEDGER = WAREHOUSE / "OFFICIAL_PUBLISHED_PICKS.jsonl"
POLICY = WAREHOUSE / "OFFICIAL_RECORD_POLICY.json"
OUT = PUBLIC / "performance_snapshot.json"

SPORTS = ["NFL", "CFB", "MLB", "NBA", "NHL"]
SETTLED = {"WIN", "LOSS", "PUSH"}


def now():
    return datetime.now(timezone.utc)


def now_iso():
    return now().isoformat()


def parse_dt(value):
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def num(value):
    try:
        x = float(value)
        return None if math.isnan(x) else x
    except Exception:
        return None


def ensure_policy():
    WAREHOUSE.mkdir(parents=True, exist_ok=True)
    if POLICY.exists():
        try:
            policy = json.loads(POLICY.read_text())
        except Exception:
            policy = {}
    else:
        policy = {}

    if not policy.get("record_started_at"):
        policy["record_started_at"] = now_iso()

    policy.update({
        "policy_version": 2,
        "title": "Official Published Record",
        "promotion_rule": (
            "Current pregame MONEYLINE picks already marked QUALIFIED_RESEARCH by the decision engine, "
            "with GOOD/HIGH market quality, provider agreement, at least 3 books and a captured American price."
        ),
        "unit_rule": "One unit risked per official moneyline pick for recordkeeping.",
        "rules": [
            "Only picks explicitly promoted to OFFICIAL after the record start are counted.",
            "Historical research recommendations are never backfilled into the official record.",
            "Published picks remain in the ledger after settlement; losses are not deleted.",
            "A publish-time American price is frozen and never replaced after the game.",
            "Win rate is not presented as profitability. Units/ROI are calculated only from captured official prices.",
        ],
    })
    POLICY.write_text(json.dumps(policy, indent=2) + "\n")

    if not LEDGER.exists():
        LEDGER.write_text("")
    return policy


def read_events():
    rows = []
    if not LEDGER.exists():
        return rows
    for line in LEDGER.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def append_event(row):
    with LEDGER.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def canonical_official(events=None):
    events = read_events() if events is None else events
    latest = {}
    for row in events:
        pick_id = str(row.get("pick_id") or "")
        if not pick_id:
            continue
        prior = latest.get(pick_id, {})
        merged = {**prior, **row}
        latest[pick_id] = merged
    return list(latest.values())


def current_json(name):
    for base in [DIST, PUBLIC]:
        path = base / name
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
    return {}


def pick_id(row):
    body = "|".join([
        "NFL",
        str(row.get("game_key") or ""),
        str(row.get("start") or ""),
        str(row.get("market") or ""),
        str(row.get("selection") or ""),
    ])
    return hashlib.sha256(body.encode()).hexdigest()


def promote_current_moneylines(policy):
    decisions = current_json("nfl_decisions.json")
    record_start = parse_dt(policy.get("record_started_at")) or now()
    existing = {row.get("pick_id") for row in canonical_official()}
    promoted = 0

    for row in decisions.get("games") or []:
        if str(row.get("market") or "").upper() != "MONEYLINE":
            continue
        if str(row.get("decision") or "").upper() != "QUALIFIED_RESEARCH":
            continue
        if str(row.get("market_data_quality") or "").upper() not in {"GOOD", "HIGH"}:
            continue
        if str(row.get("provider_agreement") or "").upper() != "AGREE":
            continue
        if int(num(row.get("sw_books")) or 0) < 3:
            continue

        price = num(row.get("line"))
        if price is None or abs(price) < 100:
            continue

        start = parse_dt(row.get("start"))
        if start is None or start <= now():
            continue

        generated = parse_dt(decisions.get("generated_at"))
        if generated is not None and generated < record_start:
            continue

        pid = pick_id(row)
        if pid in existing:
            continue

        event = {
            "event_type": "PUBLISHED",
            "pick_id": pid,
            "official": True,
            "published_at": now_iso(),
            "source_generated_at": decisions.get("generated_at"),
            "sport": "NFL",
            "lane": "GAME",
            "game_key": row.get("game_key"),
            "event_start": row.get("start"),
            "market": "MONEYLINE",
            "selection": row.get("selection"),
            "american_odds": price,
            "unit_stake": 1.0,
            "hulk_score": row.get("hulk_market_score"),
            "market_data_quality": row.get("market_data_quality"),
            "provider_agreement": row.get("provider_agreement"),
            "book_count": row.get("sw_books"),
            "decision": row.get("decision"),
            "grade": "PENDING",
            "unit_result": None,
        }
        append_event(event)
        existing.add(pid)
        promoted += 1

    return promoted


def score_game_key(game):
    away = str(game.get("away_abbr") or game.get("away_team") or "").upper().strip()
    home = str(game.get("home_abbr") or game.get("home_team") or "").upper().strip()
    return f"{away}@{home}" if away and home else ""


def same_team(selection, value):
    return str(selection or "").strip().lower() == str(value or "").strip().lower()


def american_profit(odds):
    odds = num(odds)
    if odds is None or odds == 0:
        return None
    return odds / 100.0 if odds > 0 else 100.0 / abs(odds)


def settle_official():
    scores = current_json("nfl_scores.json")
    games = {
        score_game_key(game): game
        for game in scores.get("games") or []
        if score_game_key(game)
    }
    current = canonical_official()
    settled_now = 0

    for pick in current:
        if str(pick.get("grade") or "PENDING").upper() in SETTLED:
            continue
        if pick.get("sport") != "NFL" or pick.get("market") != "MONEYLINE":
            continue

        game = games.get(str(pick.get("game_key") or ""))
        if not game or not bool(game.get("final")):
            continue

        away_score = num(game.get("away_score"))
        home_score = num(game.get("home_score"))
        if away_score is None or home_score is None:
            continue

        if away_score == home_score:
            grade = "PUSH"
        else:
            winner_name = game.get("away") if away_score > home_score else game.get("home")
            winner_abbr = game.get("away_abbr") if away_score > home_score else game.get("home_abbr")
            selection = pick.get("selection")
            grade = "WIN" if (
                same_team(selection, winner_name)
                or same_team(selection, winner_abbr)
            ) else "LOSS"

        if grade == "WIN":
            unit_result = american_profit(pick.get("american_odds"))
        elif grade == "LOSS":
            unit_result = -1.0
        else:
            unit_result = 0.0

        event = {
            "event_type": "SETTLED",
            "pick_id": pick.get("pick_id"),
            "grade": grade,
            "unit_result": None if unit_result is None else round(unit_result, 4),
            "settled_at": now_iso(),
            "result": f"{game.get('away_abbr')} {game.get('away_score')} - {game.get('home_score')} {game.get('home_abbr')}",
            "away_score": away_score,
            "home_score": home_score,
            "score_source_generated_at": scores.get("generated_at"),
        }
        append_event(event)
        settled_now += 1

    return settled_now


def read_official():
    rows = canonical_official()
    grades = [str(row.get("grade") or "PENDING").upper() for row in rows]
    wins = grades.count("WIN")
    losses = grades.count("LOSS")
    pushes = grades.count("PUSH")
    pending = sum(1 for grade in grades if grade not in SETTLED)
    denom = wins + losses
    settled = wins + losses + pushes

    unit_values = [
        num(row.get("unit_result"))
        for row in rows
        if str(row.get("grade") or "").upper() in SETTLED
    ]
    unit_values = [value for value in unit_values if value is not None]
    units = round(sum(unit_values), 3) if settled and len(unit_values) == settled else None
    roi = round(100 * units / settled, 1) if units is not None and settled else None

    return {
        "published": len(rows),
        "settled": settled,
        "pending": pending,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "hit_rate_pct": round(100 * wins / denom, 1) if denom else None,
        "units": units,
        "roi_pct": roi,
        "status": "TRACKING" if rows else "BUILDING_SAMPLE",
        "price_coverage_complete": bool(rows) and all(num(row.get("american_odds")) is not None for row in rows),
    }


def dedup_research(sport):
    path = ROOT / f"{sport.lower()}_live" / "decision" / "history" / f"{sport}_GRADED_RECOMMENDATIONS.csv"
    if not path.exists():
        return []

    frame = pd.read_csv(path, low_memory=False)
    if "grade" not in frame.columns:
        return []
    frame["grade"] = frame["grade"].astype(str).str.upper()
    frame = frame[frame["grade"].isin(SETTLED)].copy()
    if frame.empty:
        return []

    keys = [
        c for c in [
            "lane", "game_key", "event_id", "market", "player",
            "selection", "side", "line"
        ]
        if c in frame.columns
    ]
    for col in keys:
        frame[col] = frame[col].fillna("").astype(str)

    if "snapshot_at" in frame.columns:
        frame = frame.sort_values("snapshot_at")
    if keys:
        frame = frame.drop_duplicates(keys, keep="first")

    rows = []
    for lane, group in frame.groupby("lane"):
        wins = int((group["grade"] == "WIN").sum())
        losses = int((group["grade"] == "LOSS").sum())
        pushes = int((group["grade"] == "PUSH").sum())
        denom = wins + losses

        score = pd.to_numeric(group.get("score"), errors="coerce")
        high = group[score >= 85] if score is not None else group.iloc[0:0]
        high_wins = int((high["grade"] == "WIN").sum())
        high_losses = int((high["grade"] == "LOSS").sum())
        high_pushes = int((high["grade"] == "PUSH").sum())
        high_denom = high_wins + high_losses

        rows.append({
            "sport": sport,
            "lane": str(lane),
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "settled_distinct": wins + losses + pushes,
            "hit_rate_pct": round(100 * wins / denom, 1) if denom else None,
            "score85_wins": high_wins,
            "score85_losses": high_losses,
            "score85_pushes": high_pushes,
            "score85_settled": high_wins + high_losses + high_pushes,
            "score85_hit_rate_pct": round(100 * high_wins / high_denom, 1) if high_denom else None,
            "status": "RESEARCH_ARCHIVE_NOT_OFFICIAL",
        })
    return rows


def main():
    policy = ensure_policy()
    promoted = promote_current_moneylines(policy)
    settled_now = settle_official()

    research = []
    for sport in SPORTS:
        research.extend(dedup_research(sport))

    official = read_official()
    payload = {
        "generated_at": now_iso(),
        "official": official,
        "policy": policy,
        "official_recent": sorted(
            canonical_official(),
            key=lambda row: row.get("published_at") or "",
            reverse=True,
        )[:20],
        "research_validation": research,
        "notes": [
            "Research validation is historical model research, not the public official betting record.",
            "Distinct-bet deduplication removes repeated refresh snapshots of the same exact play.",
            "Hit rate alone is not ROI or profitability, especially for moneylines and parlays.",
            "Official moneyline units use one unit risked at the captured publish-time American price.",
        ],
    }

    PUBLIC.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2) + "\n"
    OUT.write_text(rendered)
    if DIST.exists():
        (DIST / "performance_snapshot.json").write_text(rendered)

    print(json.dumps({
        "status": "ok",
        "output": str(OUT),
        "promoted_now": promoted,
        "settled_now": settled_now,
        "official_published": official["published"],
        "official_pending": official["pending"],
        "research_rows": len(research),
    }))


if __name__ == "__main__":
    main()
