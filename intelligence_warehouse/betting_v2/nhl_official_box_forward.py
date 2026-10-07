"""Settle frozen NHL prop predictions from official NHL API game/box history.

No odds, model probabilities, frozen decisions, or prior SETTLED events are
rewritten. Player/game must resolve through a unique NHL roster ID and an
actual completed NHL API boxscore; sportsbook UUIDs are NOT NHL game IDs.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
from hashlib import sha256
import math
from pathlib import Path
import re
import unicodedata

MARKETS = {
    "PLAYER_TOTAL_GOALS": "goals",
    "PLAYER_TOTAL_ASSISTS": "assists",
    "PLAYER_TOTAL_POINTS": "points",
    "PLAYER_TOTAL_SHOTS": "shots_on_goal",
}
FINAL_GRADES = {"WIN", "LOSS", "PUSH"}
SOURCES = (
    "nhl_live/history/NHL_GAME_HISTORY.csv",
    "nhl_live/derived/NHL_GAMES_CURRENT.csv",
    "nhl_live/history/NHL_PLAYER_GAME_HISTORY.csv",
    "nhl_live/derived/NHL_CURRENT_ROSTERS.csv",
)
MAX_START_DRIFT_SECONDS = 2 * 60 * 60
GAME_KEY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\|[A-Z]{2,3}\|[A-Z]{2,3}$")
NHL_SOURCE = "NHL_OFFICIAL_API_FINAL_BOXSCORE_AND_ROSTER"


def name_key(value):
    folded = unicodedata.normalize("NFKD", str(value or ""))
    ascii_name = folded.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "", ascii_name)


def official_id(value):
    text = str(value or "").strip()
    if re.fullmatch(r"[0-9]+(?:\.0)?", text):
        return text[:-2] if text.endswith(".0") else text
    return ""


def utc_time(value):
    try:
        dt = datetime.fromisoformat(str(value or "").strip().replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo is not None else None
    except (ValueError, TypeError, OverflowError):
        return None


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def csv_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def file_digests(root):
    result = {}
    for rel in SOURCES:
        path = root / rel
        if not path.is_file() or path.stat().st_size == 0:
            return None
        result[rel] = sha256(path.read_bytes()).hexdigest()
    return result


def game_record(raw):
    if str(raw.get("completed") or "").strip().lower() not in {"true", "1", "yes"}:
        return None
    if str(raw.get("game_state") or "").strip().upper() not in {"FINAL", "OFF"}:
        return None
    game_id = official_id(raw.get("event_id"))
    start = utc_time(raw.get("start"))
    away = str(raw.get("away_team") or "").upper().strip()
    home = str(raw.get("home_team") or "").upper().strip()
    date = str(raw.get("game_date") or "").strip()
    gametype = official_id(raw.get("game_type"))
    season = official_id(raw.get("season"))
    away_score = number(raw.get("away_score"))
    home_score = number(raw.get("home_score"))
    if (
        not game_id or not start or not date
        or not away or not home or away == home
        or gametype not in {"1", "2", "3"} or not season
        or away_score is None or home_score is None
        or away_score < 0 or home_score < 0
        or start.date() < datetime.fromisoformat(date).date()
    ):
        return None
    return {
        "official_game_id": game_id,
        "game_key": f"{date}|{away}|{home}",
        "start": start, "away": away, "home": home,
        "game_type": gametype, "season": season,
        "away_score": away_score, "home_score": home_score,
    }


def indexes(raw_games, raw_box, raw_rosters):
    invalid = Counter()
    ids = defaultdict(list)
    for raw in raw_games:
        try:
            game = game_record(raw)
        except (ValueError, TypeError):
            game = None
        if game is None:
            invalid["UNUSABLE_OR_NONFINAL_GAME"] += 1
            continue
        ids[game["official_game_id"]].append(game)

    by_key = defaultdict(list)
    for game_id, records in ids.items():
        # If two official exports disagree about the same game, never
        # grade using whichever happened to be read last.
        if any(record != records[0] for record in records[1:]):
            invalid["CONFLICTING_OFFICIAL_GAME_EXPORTS"] += 1
            continue
        by_key[records[0]["game_key"]].append(records[0])

    by_player_name = defaultdict(set)
    for raw in raw_rosters:
        name = name_key(raw.get("player"))
        player_id = official_id(raw.get("player_id"))
        team = str(raw.get("team") or "").strip().upper()
        if name and player_id and team:
            by_player_name[name].add((player_id, team))

    by_box = defaultdict(list)
    for raw in raw_box:
        game_id, player_id = official_id(raw.get("event_id")), official_id(raw.get("player_id"))
        if game_id and player_id:
            by_box[(game_id, player_id)].append(raw)
    return by_key, by_player_name, by_box, dict(invalid)


def verify(row, by_key, names, boxes):
    if str(row.get("sport") or "").upper() != "NHL":
        return None, "NOT_NHL"
    game_key = str(row.get("game_key") or "").strip()
    if not GAME_KEY_PATTERN.fullmatch(game_key):
        return None, "MISSING_EXACT_GAME_KEY"
    matches = by_key.get(game_key, ())
    if not matches:
        return None, "NO_COMPLETED_OFFICIAL_GAME"
    if len(matches) != 1:
        return None, "AMBIGUOUS_OFFICIAL_GAME"
    game = matches[0]
    frozen_start, frozen_at = utc_time(row.get("event_start")), utc_time(row.get("captured_at"))
    if frozen_start is None or frozen_at is None:
        return None, "NO_FROZEN_PREGAME_TIMESTAMPS"
    if abs((frozen_start - game["start"]).total_seconds()) > MAX_START_DRIFT_SECONDS:
        return None, "EVENT_START_MISMATCH"
    if frozen_at >= min(frozen_start, game["start"]):
        return None, "NOT_FROZEN_PREGAME"

    player_key = name_key(row.get("player_key"))
    roster = names.get(player_key, set())
    if len(roster) != 1:
        return None, "AMBIGUOUS_OR_MISSING_ROSTER_ID"
    player_id, roster_team = next(iter(roster))
    boxrows = boxes.get((game["official_game_id"], player_id), ())
    if len(boxrows) != 1:
        return None, "MISSING_OR_DUPLICATE_PLAYER_BOX"
    box = boxrows[0]
    team = str(box.get("team") or "").upper().strip()
    opponent = str(box.get("opponent") or "").upper().strip()
    if (
        (team, opponent) not in {(game["away"], game["home"]), (game["home"], game["away"])}
        or roster_team != team
        or str(box.get("role") or "").upper().strip() != "SKATER"
    ):
        return None, "PLAYER_GAME_TEAM_CONFLICT"
    if (
        official_id(box.get("game_type")) != game["game_type"]
        or official_id(box.get("season")) != game["season"]
    ):
        return None, "COMPETITION_REGIME_CONFLICT"
    toi = number(box.get("toi_minutes"))
    if toi is None or toi <= 0:
        return None, "NO_VERIFIED_PLAYED_MINUTES"

    market = str(row.get("market") or "").strip().upper()
    stat = MARKETS.get(market)
    if stat is None:
        return None, "UNSUPPORTED_FROZEN_MARKET"
    actual, line = number(box.get(stat)), number(row.get("line"))
    side = str(row.get("side") or "").strip().upper()
    if actual is None or actual < 0 or not actual.is_integer():
        return None, "NO_VALID_OFFICIAL_STAT"
    if line is None or line < 0 or side not in {"OVER", "UNDER"}:
        return None, "NO_VALID_FROZEN_LINE_SIDE"
    grade = (
        "PUSH" if actual == line else
        "WIN" if (actual > line if side == "OVER" else actual < line)
        else "LOSS"
    )
    return {
        "grade": grade,
        "actual_value": int(actual),
        "stat_column": stat,
        "official_game_id": game["official_game_id"],
        "official_player_id": player_id,
        "official_game_type": game["game_type"],
        "official_season": game["season"],
        "official_game_start": game["start"].isoformat(),
        "away_score": game["away_score"],
        "home_score": game["home_score"],
    }, "VERIFIED"


def plan_nhl_settlement(root, canonical):
    """Entire decision is read-only: returns a receipt and events to append."""
    from datetime import datetime, timezone
    receipt = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": NHL_SOURCE,
        "status": "WAITING_FOR_OFFICIAL_SOURCE",
        "source_digests": {},
        "existing_verified": 0, "new_verified": 0,
        "already_settled_unverifiable": 0,
        "review_reasons": {}, "conflicting_previous_grades": [],
        "automatic_model_promotion": False,
        "official_box_is_not_platform_payout_proof": True,
        "frozen_probabilities_untouched": True,
    }
    before = file_digests(root)
    if before is None:
        receipt["status"] = "SOURCE_UNAVAILABLE"
        return receipt, []
    try:
        games = csv_rows(root / SOURCES[0]) + csv_rows(root / SOURCES[1])
        box = csv_rows(root / SOURCES[2])
        rosters = csv_rows(root / SOURCES[3])
    except (OSError, csv.Error) as exc:
        receipt["status"] = "SOURCE_READ_FAILED"
        receipt["source_error"] = type(exc).__name__
        return receipt, []

    if before != file_digests(root):
        receipt["status"] = "SOURCE_CHANGED_DURING_READ"
        return receipt, []
    receipt["source_digests"] = before
    by_key, names, boxes, invalid = indexes(games, box, rosters)
    receipt["source_counts"] = {
        "final_games": sum(map(len, by_key.values())),
        "roster_names": len(names), "player_box_keys": len(boxes),
        "source_warnings": invalid,
    }
    reasons = Counter()
    planned = []
    conflicts = []
    for key, row in canonical.items():
        if str(row.get("sport") or "").upper() != "NHL":
            continue
        proof, reason = verify(row, by_key, names, boxes)
        if proof is None:
            reasons[reason] += 1
            if str(row.get("grade") or "").upper() in FINAL_GRADES:
                receipt["already_settled_unverifiable"] += 1
            continue
        prior = str(row.get("grade") or "").upper()
        if prior in FINAL_GRADES:
            if prior != proof["grade"]:
                conflicts.append({
                    "forward_key": key,
                    "recorded_grade": prior, "official_grade": proof["grade"],
                    "official_game_id": proof["official_game_id"],
                })
            else:
                receipt["existing_verified"] += 1
            continue
        if prior not in {"PENDING", ""}:
            reasons["UNSUPPORTED_FROZEN_GRADE_STATE"] += 1
            continue
        planned.append({
            "event_type": "SETTLED",
            "forward_key": key,
            "sport": "NHL",
            "status": "SETTLED",
            "grade": proof["grade"],
            "actual_value": proof["actual_value"],
            "settled_at": receipt["generated_at"],
            "grade_snapshot_at": receipt["generated_at"],
            "settlement_match_type": "NHL_OFFICIAL_GAME_PLAYER_BOX",
            "settlement_source": NHL_SOURCE,
            "result_event_id": proof["official_game_id"],
            "official_player_id": proof["official_player_id"],
            "stat_column": proof["stat_column"],
            "official_game_type": proof["official_game_type"],
            "official_season": proof["official_season"],
            "official_game_start": proof["official_game_start"],
            "away_score": proof["away_score"],
            "home_score": proof["home_score"],
            "platform_settlement_claimed": False,
        })

    receipt["review_reasons"] = dict(sorted(reasons.items()))
    receipt["new_verified"] = len(planned)
    receipt["conflicting_previous_grades"] = conflicts[:30]
    receipt["conflicting_previous_grades_count"] = len(conflicts)
    if conflicts:
        receipt["status"] = "INTEGRITY_HOLD_CONTRADICTORY_SETTLEMENT"
        return receipt, []
    receipt["status"] = "READY"
    return receipt, planned
