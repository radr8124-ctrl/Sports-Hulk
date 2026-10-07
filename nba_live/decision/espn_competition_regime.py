"""Official ESPN game-to-regime matching, without calendar inference.

Only an explicitly supplied ESPN event season.type, paired with a unique
team-and-start-time event match, can label a decision's competition regime.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

SOURCE = "ESPN_SITE_SCOREBOARD_EXACT_GAME"
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
SEASON_TYPES = {1: "PRESEASON", 2: "REGULAR", 3: "POSTSEASON"}
TEAM_ALIASES = {
    "NY": "NYK", "GS": "GSW", "SA": "SAS",
    "NO": "NOP", "WSH": "WAS", "UTAH": "UTA",
}
MAX_KICKOFF_DRIFT_SECONDS = 20 * 60


def team_code(value: Any) -> str:
    value = str(value or "").strip().upper()
    return TEAM_ALIASES.get(value, value)


def parse_utc(value: Any) -> datetime | None:
    try:
        if not isinstance(value, str) or not value.strip():
            return None
        result = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if result.tzinfo is None:
            return None
        return result.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def season_type_value(value: Any) -> tuple[str, str]:
    """Only ESPN's explicit season.type 1/2/3 can generate a proof regime."""
    if type(value) is int and value in SEASON_TYPES:
        return str(value), SEASON_TYPES[value]
    if isinstance(value, str) and value in {"1", "2", "3"}:
        return value, SEASON_TYPES[int(value)]
    return "", "UNKNOWN"


def parse_scoreboard_event(event: dict) -> dict | None:
    if not isinstance(event, dict):
        return None
    event_id = str(event.get("id") or "").strip()
    start = parse_utc(event.get("date"))
    competitions = event.get("competitions") or []
    if not event_id or not start or not isinstance(competitions, list) or len(competitions) != 1:
        return None
    competitors = competitions[0].get("competitors") or []
    if not isinstance(competitors, list):
        return None
    sides = {}
    for competitor in competitors:
        if not isinstance(competitor, dict):
            continue
        side = str(competitor.get("homeAway") or "").strip().lower()
        code = team_code((competitor.get("team") or {}).get("abbreviation"))
        if side in {"home", "away"} and code and side not in sides:
            sides[side] = code
        elif side in sides:
            return None
    if set(sides) != {"home", "away"} or sides["home"] == sides["away"]:
        return None
    season = event.get("season") or {}
    raw_type = season.get("type") if isinstance(season, dict) else None
    stype, regime = season_type_value(raw_type)
    return {
        "event_id": event_id, "start": start,
        "away": sides["away"], "home": sides["home"],
        "season_type": stype, "competition_regime": regime,
    }


def dates_to_query(rows: list[dict]) -> list[str]:
    dates = set()
    for row in rows:
        start = parse_utc(row.get("start_dt"))
        if start is not None:
            # ESPN dates are keyed to the North American game day. Request
            # the start's UTC date and the prior day; this is discovery ONLY.
            # Competition regime is never deduced from either date.
            dates.update(
                (start.date().strftime("%Y%m%d"),
                 (start - timedelta(days=1)).date().strftime("%Y%m%d"))
            )
    return sorted(dates)


def fetch_scoreboard_events(dates: list[str], session, timeout: int = 12) -> tuple[list[dict], dict]:
    events = {}
    failed = {}
    successful = []
    for day in dates:
        try:
            response = session.get(
                ESPN_SCOREBOARD, params={"dates": day, "limit": 200}, timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
                raise ValueError("Scoreboard response has no events array")
            successful.append(day)
            for raw in payload["events"]:
                parsed = parse_scoreboard_event(raw)
                if parsed is None:
                    continue
                event_id = parsed["event_id"]
                # A duplicated ID with conflicting content is not authoritative.
                if event_id in events and events[event_id] != parsed:
                    events[event_id] = None
                elif event_id not in events:
                    events[event_id] = parsed
        except Exception as exc:
            failed[day] = f"{type(exc).__name__}: {str(exc)[:120]}"
    return (
        [entry for entry in events.values() if entry is not None],
        {"queried_dates": dates, "successful_dates": successful,
         "failed_dates": failed, "unique_valid_events": sum(v is not None for v in events.values()),
         "conflicting_event_ids": sum(v is None for v in events.values())},
    )


def label_decision(row: dict, events: list[dict]) -> tuple[dict, str]:
    result = dict(row)
    result.update({
        "season_type": "", "competition_regime": "UNKNOWN",
        "competition_regime_source": "", "espn_event_id": "",
    })
    start = parse_utc(row.get("start_dt"))
    away = team_code(row.get("away_team_canonical"))
    home = team_code(row.get("home_team_canonical"))
    if start is None or not away or not home or away == home:
        return result, "INVALID_GAME"
    key = str(row.get("game_key") or "").strip()
    expected_key = f"{start.date().isoformat()}|{away}|{home}"
    if key != expected_key:
        return result, "GAME_KEY_MISMATCH"

    candidates = [
        event for event in events
        if event["away"] == away
        and event["home"] == home
        and abs((event["start"] - start).total_seconds()) <= MAX_KICKOFF_DRIFT_SECONDS
    ]
    if len(candidates) != 1:
        return result, "AMBIGUOUS" if len(candidates) > 1 else "NO_EXACT_EVENT"
    event = candidates[0]
    if event["competition_regime"] == "UNKNOWN":
        return result, "NO_EXPLICIT_SEASON_TYPE"

    for field in ("season_type", "competition_regime"):
        previous = str(row.get(field) or "").strip().upper()
        if previous and previous != "UNKNOWN" and previous != str(event[field]):
            return result, "CONFLICTING_EXISTING_REGIME"

    result.update({
        "season_type": event["season_type"],
        "competition_regime": event["competition_regime"],
        "competition_regime_source": SOURCE,
        "espn_event_id": event["event_id"],
    })
    return result, "VERIFIED"
