"""Grade frozen MLB props from exact archived provider IDs and MLB StatsAPI boxes.

Never infer a game from its date or a player ID from a name alone. The archived
decision snapshot supplies the official player ID, the provider quote supplies
the original teams/start, and MLB StatsAPI independently confirms the unique
official gamePk, final state, participating player and recorded stat.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import csv
import json
import math
from pathlib import Path
import re
import unicodedata
import requests

SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
FEED_URL = "https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
ARCHIVE_GLOB = "mlb_live/decision/history/snapshots/*/MLB_*_CANDIDATES.csv"
SOURCE = "MLB_STATSAPI_FINAL_GAME_BOX_EXACT_ARCHIVED_EVENT_PLAYER"
SETTLED = {"WIN", "LOSS", "PUSH"}
MAX_TIME_DRIFT = timedelta(minutes=20)
MAX_SCHEDULE_SPAN_DAYS = 31
MARKETS = {
    "PLAYER_TOTAL_HITS": ("batting", "hits"),
    "PLAYER_TOTAL_RUNS": ("batting", "runs"),
    "PLAYER_TOTAL_RBIS": ("batting", "rbi"),
    "PLAYER_TOTAL_DOUBLES": ("batting", "doubles"),
    "PLAYER_TOTAL_HOME_RUNS": ("batting", "homeRuns"),
    "PLAYER_TOTAL_STOLEN_BASES": ("batting", "stolenBases"),
    "PLAYER_TOTAL_BATTER_WALKS": ("batting", "baseOnBalls"),
    "PLAYER_TOTAL_TOTAL_BASES": ("batting", "totalBases"),
    "PLAYER_TOTAL_SINGLES": ("batting", "singles"),
    "PLAYER_TOTAL_HITS_+_RUNS_+_RBIS": ("batting", "hrr"),
    "PLAYER_TOTAL_EARNED_RUNS_ALLOWED": ("pitching", "earnedRuns"),
    "PLAYER_TOTAL_WALKS_ALLOWED": ("pitching", "baseOnBalls"),
    "PLAYER_TOTAL_PITCHER_STRIKEOUTS": ("pitching", "strikeOuts"),
    "PLAYER_TOTAL_HITS_ALLOWED": ("pitching", "hits"),
    "PLAYER_TOTAL_PITCHING_OUTS": ("pitching", "outs"),
}


def clean(value):
    return unicodedata.normalize("NFKD", str(value or "")).encode(
        "ascii", "ignore"
    ).decode("ascii").strip().lower()


def person_key(value):
    return re.sub(r"[^a-z0-9]", "", clean(value))


def time_utc(value):
    try:
        result = datetime.fromisoformat(str(value or "").strip().replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (TypeError, ValueError, OverflowError):
        return None


def official_id(value):
    raw = str(value or "").strip()
    if re.fullmatch(r"[0-9]+(?:\.0)?", raw):
        return raw[:-2] if raw.endswith(".0") else raw
    return ""


def real_number(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def archive_files(root):
    return sorted(
        p for p in root.glob(ARCHIVE_GLOB)
        if p.name.startswith(("MLB_PROP_", "MLB_PRIZEPICKS_"))
    )


def archive_fingerprint(root):
    """Detect newly created, truncated or rewritten snapshots during release."""
    paths = archive_files(root)
    if not paths:
        return None
    total = sha256()
    for path in paths:
        b = path.read_bytes()
        total.update(str(path.relative_to(root)).encode("utf-8") + b"\0")
        total.update(sha256(b).digest())
    return {"sha256": total.hexdigest(), "files": len(paths)}


def load_archived_identity(root, needed):
    evidence = defaultdict(set)
    players = defaultdict(set)
    for path in archive_files(root):
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as inp:
                for row in csv.DictReader(inp):
                    uuid = str(row.get("event_id") or "").strip()
                    if uuid not in needed:
                        continue
                    away = person_key(row.get("away_team"))
                    home = person_key(row.get("home_team"))
                    start = time_utc(row.get("start"))
                    if away and home and start:
                        evidence[uuid].add((away, home, start))
                    player = person_key(row.get("player_key"))
                    playerid = official_id(row.get("player_id"))
                    team = person_key(row.get("team"))
                    name = person_key(row.get("player"))
                    if player and playerid and team and name:
                        players[(uuid, player)].add((playerid, team, name))
        except (OSError, csv.Error):
            raise
    return evidence, players


def read_schedule(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("dates"), list):
        raise ValueError("Missing MLB schedule dates")
    games = []
    for day in payload["dates"]:
        for row in day.get("games", []):
            teams = row.get("teams", {})
            away = (teams.get("away") or {}).get("team") or {}
            home = (teams.get("home") or {}).get("team") or {}
            game_pk = official_id(row.get("gamePk"))
            start = time_utc(row.get("gameDate"))
            if game_pk and start and person_key(away.get("name")) and person_key(home.get("name")):
                games.append({
                    "game_pk": game_pk,
                    "away": person_key(away["name"]),
                    "home": person_key(home["name"]),
                    "away_id": official_id(away.get("id")),
                    "home_id": official_id(home.get("id")),
                    "start": start,
                    "status": str((row.get("status") or {}).get("detailedState") or ""),
                    "game_number": official_id(row.get("gameNumber")),
                    "game_type": str(row.get("gameType") or ""),
                })
    return games


def map_official_games(events, games):
    mapped = {}
    unresolved = {}
    for uuid, forms in events.items():
        matched = set()
        rejected = False
        for away, home, start in forms:
            eligible = [
                g for g in games
                if g["away"] == away and g["home"] == home
                and abs(g["start"] - start) <= MAX_TIME_DRIFT
            ]
            if len(eligible) != 1:
                rejected = True
                break
            matched.add(eligible[0]["game_pk"])
        if rejected or len(matched) != 1:
            unresolved[uuid] = "AMBIGUOUS_PROVIDER_OFFICIAL_GAME"
        else:
            pk = next(iter(matched))
            matching = [g for g in games if g["game_pk"] == pk]
            if len(matching) != 1:
                unresolved[uuid] = "DUPLICATED_OFFICIAL_GAME_ID"
            else:
                mapped[uuid] = matching[0]
    return mapped, unresolved


def official_box(feed, game):
    """Return unique participated player IDs in their actual official side."""
    if not isinstance(feed, dict):
        return None
    gd = feed.get("gameData") or {}
    status = gd.get("status") or {}
    actual = gd.get("game") or {}
    teams = gd.get("teams") or {}
    recorded_start = time_utc((gd.get("datetime") or {}).get("dateTime"))
    if (
        status.get("abstractGameState") != "Final"
        or status.get("detailedState") != "Final"
        or official_id(actual.get("pk")) != game["game_pk"]
        or not recorded_start
        or abs(recorded_start - game["start"]) > MAX_TIME_DRIFT
        or str(actual.get("type") or "") != game["game_type"]
        or any(
            person_key((teams.get(side) or {}).get("name")) != game[side]
            or (game.get(f"{side}_id") and
                official_id((teams.get(side) or {}).get("id")) != game[f"{side}_id"])
            for side in ("away", "home")
        )
    ):
        return None
    box = ((feed.get("liveData") or {}).get("boxscore") or {}).get("teams") or {}
    if any(side not in box for side in ("away", "home")):
        return None
    scor = ((feed.get("liveData") or {}).get("linescore") or {}).get("teams") or {}
    scores = {}
    for side in ("away", "home"):
        v = real_number((scor.get(side) or {}).get("runs"))
        if v is None or v < 0 or not v.is_integer():
            return None
        scores[side] = int(v)

    people = defaultdict(list)
    for side in ("away", "home"):
        block = box[side]
        batters = {official_id(pid) for pid in (block.get("batters") or [])}
        pitchers = {official_id(pid) for pid in (block.get("pitchers") or [])}
        for record in (block.get("players") or {}).values():
            pid = official_id((record.get("person") or {}).get("id"))
            if pid:
                people[pid].append({
                    "side": side,
                    "name": person_key((record.get("person") or {}).get("fullName")),
                    "batting_played": pid in batters,
                    "pitching_played": pid in pitchers,
                    "batting": (record.get("stats") or {}).get("batting") or {},
                    "pitching": (record.get("stats") or {}).get("pitching") or {},
                })
    return {"players": people, "scores": scores}


def nonnegative_int(stats, field):
    value = real_number(stats.get(field))
    if value is None or value < 0 or not value.is_integer():
        return None
    return int(value)


def stat_actual(record, market):
    definition = MARKETS.get(market)
    if not definition:
        return None, "UNSUPPORTED_FROZEN_MARKET"
    group, field = definition
    if not record.get(group + "_played") or not record.get(group):
        return None, "PLAYER_NOT_VERIFIED_PLAYED"
    stats = record[group]
    if field == "hrr":
        parts = [nonnegative_int(stats, k) for k in ("hits", "runs", "rbi")]
        result = sum(parts) if all(x is not None for x in parts) else None
    elif field == "singles":
        parts = [nonnegative_int(stats, k) for k in ("hits", "doubles", "triples", "homeRuns")]
        result = parts[0] - sum(parts[1:]) if all(x is not None for x in parts) else None
    elif field == "outs":
        text = str(stats.get("inningsPitched") or "")
        m = re.fullmatch(r"(\d+)\.([012])", text)
        result = int(m.group(1)) * 3 + int(m.group(2)) if m else None
    else:
        result = nonnegative_int(stats, field)
    if result is None or result < 0:
        return None, "OFFICIAL_METRIC_UNAVAILABLE"
    return result, "VERIFIED"


def verify_prediction(row, mapped, archived_players, boxes):
    event = str(row.get("event_id") or "").strip()
    game = mapped.get(event)
    if game is None:
        return None, "NO_UNIQUE_OFFICIAL_GAME_MAPPING"
    if game["status"] != "Final" or game["game_pk"] not in boxes:
        return None, "NO_OFFICIAL_FINAL_BOX"
    frozen_start = time_utc(row.get("event_start"))
    frozen_at = time_utc(row.get("captured_at"))
    if (
        not frozen_at or not frozen_start or
        abs(frozen_start - game["start"]) > MAX_TIME_DRIFT or
        frozen_at >= min(frozen_start, game["start"])
    ):
        return None, "NOT_VERIFIED_PREGAME_OR_START"
    players = archived_players.get((event, person_key(row.get("player_key"))), set())
    if len(players) != 1:
        return None, "NO_UNIQUE_ARCHIVED_OFFICIAL_PLAYER_ID"
    player_id, source_team, archived_name = next(iter(players))
    official_rows = boxes[game["game_pk"]]["players"].get(player_id, [])
    if len(official_rows) != 1:
        return None, "PLAYER_MISSING_OR_DUPLICATED_IN_FINAL_BOX"
    person = official_rows[0]
    if (
        source_team != game[person["side"]]
        or person["name"] != archived_name
        or person["name"] != person_key(row.get("player_key"))
    ):
        return None, "OFFICIAL_PLAYER_ID_TEAM_NAME_CONFLICT"
    market = str(row.get("market") or "").upper().strip()
    actual, reason = stat_actual(person, market)
    if actual is None:
        return None, reason
    line = real_number(row.get("line"))
    side = str(row.get("side") or "").upper().strip()
    if line is None or line < 0 or side not in {"OVER", "UNDER"}:
        return None, "BAD_FROZEN_MARKET_LINE_SIDE"
    grade = (
        "PUSH" if actual == line else
        "WIN" if (actual > line if side == "OVER" else actual < line)
        else "LOSS"
    )
    return {
        "grade": grade, "actual_value": actual,
        "stat_column": market, "official_game_pk": game["game_pk"],
        "official_player_id": player_id,
        "official_game_type": game["game_type"],
        "official_start": game["start"].isoformat(),
        "away_score": boxes[game["game_pk"]]["scores"]["away"],
        "home_score": boxes[game["game_pk"]]["scores"]["home"],
    }, "VERIFIED"


def plan_mlb_settlement(root, frozen, session, now=None):
    now = now or datetime.now(timezone.utc)
    receipt = {
        "generated_at": now.isoformat(), "source": SOURCE,
        "status": "SOURCE_UNAVAILABLE",
        "verified_new": 0, "existing_verified": 0,
        "prior_unverified": 0,
        "conflicting_previous_grades": [],
        "conflicting_previous_grades_count": 0,
        "review_reasons": {},
        "automatic_model_promotion": False,
        "platform_payout_claimed": False,
    }
    mlb = {
        key: row for key, row in frozen.items()
        if str(row.get("sport") or "").upper() == "MLB"
    }
    if not mlb:
        receipt["status"] = "NO_FROZEN_MLB_PREDICTIONS"
        return receipt, []

    try:
        beginning = archive_fingerprint(root)
        if beginning is None:
            return receipt, []
        needed = {str(row.get("event_id") or "").strip() for row in mlb.values()}
        events, players = load_archived_identity(root, needed)
        receipt["archive_source"] = beginning
        receipt["mapped_archived_events"] = len(events)
        starts = [start for records in events.values() for _, _, start in records]
        if not starts:
            receipt["status"] = "NO_ARCHIVED_EVENT_IDENTITIES"
            return receipt, []
        start_day = min(starts).date() - timedelta(days=1)
        end_day = max(starts).date() + timedelta(days=1)
        if (end_day - start_day).days > MAX_SCHEDULE_SPAN_DAYS:
            receipt["status"] = "SCHEDULE_SPAN_EXCEEDS_SAFETY_LIMIT"
            return receipt, []
        response = session.get(
            SCHEDULE_URL,
            params={"sportId": 1, "startDate": start_day.isoformat(),
                    "endDate": end_day.isoformat(), "hydrate": "team"},
            timeout=20,
        )
        response.raise_for_status()
        official_games = read_schedule(response.json())
        mapped, rejects = map_official_games(events, official_games)
        receipt["mapped_official_events"] = len(mapped)
        receipt["unmatched_events"] = rejects

        boxes = {}
        box_hashes = {}
        finals = {g["game_pk"]: g for g in mapped.values() if g["status"] == "Final"}
        for game_pk, game in sorted(finals.items()):
            response = session.get(FEED_URL.format(game_pk=game_pk), timeout=20)
            response.raise_for_status()
            payload = response.json()
            proof = official_box(payload, game)
            if proof is None:
                receipt["status"] = "INVALID_OFFICIAL_FINAL_BOX"
                return receipt, []
            boxes[game_pk] = proof
            box_hashes[game_pk] = sha256(
                json.dumps(payload, sort_keys=True).encode("utf-8")
            ).hexdigest()
        receipt["official_final_games"] = len(boxes)
        receipt["box_sha256"] = box_hashes
        if archive_fingerprint(root) != beginning:
            receipt["status"] = "ARCHIVE_CHANGED_DURING_RESEARCH"
            return receipt, []
    except (requests.exceptions.RequestException, TimeoutError, ConnectionError) as exc:
        receipt["status"] = "OFFICIAL_API_UNAVAILABLE"
        receipt["error_type"] = type(exc).__name__
        return receipt, []
    except (OSError, ValueError, KeyError, TypeError, csv.Error) as exc:
        receipt["status"] = "SOURCE_VALIDATION_FAILED"
        receipt["error_type"] = type(exc).__name__
        return receipt, []
    except Exception as exc:
        receipt["status"] = "OFFICIAL_API_UNAVAILABLE"
        receipt["error_type"] = type(exc).__name__
        return receipt, []

    problems = Counter()
    output = []
    contradictions = []
    for key, row in mlb.items():
        proof, reason = verify_prediction(row, mapped, players, boxes)
        prior = str(row.get("grade") or "").upper()
        if proof is None:
            problems[reason] += 1
            if prior in SETTLED:
                receipt["prior_unverified"] += 1
            continue
        if prior in SETTLED:
            if prior == proof["grade"]:
                receipt["existing_verified"] += 1
            else:
                contradictions.append({
                    "forward_key": key,
                    "recorded": prior, "official": proof["grade"],
                    "official_game_pk": proof["official_game_pk"],
                })
            continue
        if prior not in {"", "PENDING"}:
            problems["UNSUPPORTED_PREVIOUS_FORWARD_STATE"] += 1
            continue
        output.append({
            "event_type": "SETTLED", "forward_key": key,
            "sport": "MLB", "status": "SETTLED",
            "grade": proof["grade"], "actual_value": proof["actual_value"],
            "settled_at": receipt["generated_at"],
            "grade_snapshot_at": receipt["generated_at"],
            "settlement_match_type": "MLB_OFFICIAL_GAME_AND_PLAYER_ID",
            "settlement_source": SOURCE,
            "original_provider_event_id": row.get("event_id"),
            "official_game_pk": proof["official_game_pk"],
            "official_player_id": proof["official_player_id"],
            "stat_column": proof["stat_column"],
            "official_game_type": proof["official_game_type"],
            "official_game_start": proof["official_start"],
            "away_score": proof["away_score"],
            "home_score": proof["home_score"],
            "platform_payout_claimed": False,
            "automatic_model_promotion": False,
        })
    receipt["review_reasons"] = dict(sorted(problems.items()))
    receipt["conflicting_previous_grades_count"] = len(contradictions)
    receipt["conflicting_previous_grades"] = contradictions[:20]
    receipt["verified_new"] = len(output)
    if contradictions:
        receipt["status"] = "INTEGRITY_HOLD_PREVIOUS_GRADE_CONFLICT"
        return receipt, []
    receipt["status"] = "READY"
    return receipt, output
