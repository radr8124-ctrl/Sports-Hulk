#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re

import pandas as pd
import requests

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "intelligence_warehouse" / "starters"
RAW = OUT / "raw"
OUT.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

CURRENT_OUT = OUT / "STARTER_STATUS_CURRENT.csv"
TIMELINE_OUT = OUT / "STARTER_STATE_TIMELINE.csv"
CHANGES_OUT = OUT / "STARTER_CHANGES.csv"
SOURCE_OUT = OUT / "STARTER_SOURCE_CATALOG.csv"
RECEIPT_OUT = OUT / "STARTER_LIFECYCLE_RECEIPT.json"

MLB_SCHEDULE = ROOT / "baseball_vault" / "latest" / "MLB_SCHEDULE.csv"
NBA_GAMES = ROOT / "nba_live" / "derived" / "NBA_GAMES_CURRENT.csv"
CBB_GAMES = ROOT / "cbb_live" / "derived" / "CBB_GAMES_CURRENT.csv"
NHL_GAMES = ROOT / "nhl_live" / "derived" / "NHL_GAMES_CURRENT.csv"

NOW = datetime.now(timezone.utc)
WINDOW_START = NOW - timedelta(hours=3)
WINDOW_END = NOW + timedelta(hours=48)
HEADERS = {"User-Agent": "Sports-HULK/1.0 starter-lifecycle"}
def clean(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "nat", "<na>"} else text

def norm(value):
    return re.sub(r"[^a-z0-9]+", "", clean(value).lower())

def read_csv(path):
    try:
        return pd.read_csv(path, low_memory=False) if path.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def to_utc(value):
    try:
        return pd.to_datetime(value, utc=True).to_pydatetime()
    except Exception:
        return None

def observation_phase(start):
    dt = to_utc(start)
    if dt is None:
        return "UNKNOWN"
    return "PRE_GAME" if NOW < dt else "LIVE_OR_POST"

def fetch_json(url, raw_name):
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    data = response.json()
    (RAW / raw_name).write_text(json.dumps(data, separators=(",", ":")))
    return data

def in_window(value):
    dt = to_utc(value)
    return bool(dt and WINDOW_START <= dt <= WINDOW_END)
def mlb_task(row):
    game_id = int(row.gamePk)
    data = fetch_json(
        f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live",
        f"mlb_{game_id}.json",
    )
    return "MLB", game_id, row._asdict(), data

def nba_task(row):
    event_id = int(row.event_id)
    data = fetch_json(
        "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/"
        f"summary?event={event_id}",
        f"nba_{event_id}.json",
    )
    return "NBA", event_id, row._asdict(), data

def cbb_task(row):
    event_id = int(row.event_id)
    data = fetch_json(
        "https://site.api.espn.com/apis/site/v2/sports/basketball/"
        f"mens-college-basketball/summary?event={event_id}",
        f"cbb_{event_id}.json",
    )
    return "CBB", event_id, row._asdict(), data

def nhl_task(row):
    event_id = int(row.event_id)
    data = fetch_json(
        f"https://api-web.nhle.com/v1/gamecenter/{event_id}/boxscore",
        f"nhl_{event_id}.json",
    )
    return "NHL", event_id, row._asdict(), data

tasks = []
mlb = read_csv(MLB_SCHEDULE)
if not mlb.empty:
    for row in mlb.itertuples(index=False):
        if in_window(getattr(row, "gameDate", None)):
            tasks.append(("MLB", row))

nba = read_csv(NBA_GAMES)
if not nba.empty:
    for row in nba.itertuples(index=False):
        if in_window(getattr(row, "start", None)):
            tasks.append(("NBA", row))

cbb = read_csv(CBB_GAMES)
if not cbb.empty:
    for row in cbb.itertuples(index=False):
        if in_window(getattr(row, "start", None)):
            tasks.append(("CBB", row))

nhl = read_csv(NHL_GAMES)
if not nhl.empty:
    for row in nhl.itertuples(index=False):
        if in_window(getattr(row, "start", None)):
            tasks.append(("NHL", row))

fetched = []
errors = []
with ThreadPoolExecutor(max_workers=12) as pool:
    future_map = {}
    for sport, row in tasks:
        fn = {
            "MLB": mlb_task,
            "NBA": nba_task,
            "CBB": cbb_task,
            "NHL": nhl_task,
        }[sport]
        future_map[pool.submit(fn, row)] = (sport, row)
    for future in as_completed(future_map):
        sport, row = future_map[future]
        try:
            fetched.append(future.result())
        except Exception as exc:
            errors.append({
                "sport": sport,
                "event_id": clean(getattr(row, "event_id", getattr(row, "gamePk", ""))),
                "error": repr(exc),
            })
def base_row(sport, event_id, start, team, opponent, side, role, state, source, tier):
    return {
        "observed_at": NOW.isoformat(),
        "sport": sport,
        "event_id": str(event_id),
        "start": clean(start),
        "team": clean(team),
        "opponent": clean(opponent),
        "side": side.upper(),
        "entity_type": "TEAM",
        "player_id": "",
        "player": "",
        "player_key": "",
        "position": "",
        "role": role,
        "state": state,
        "order_number": None,
        "source": source,
        "source_tier": tier,
        "observation_phase": observation_phase(start),
        "automatic_model_adjustment": False,
    }

def player_row(base, player_id, player, position, order_number=None):
    row = dict(base)
    row.update({
        "entity_type": "PLAYER",
        "player_id": clean(player_id),
        "player": clean(player),
        "player_key": norm(player),
        "position": clean(position),
        "order_number": order_number,
    })
    return row

def parse_mlb(event_id, meta, data):
    rows = []
    start = meta.get("gameDate")
    game_data = data.get("gameData") or {}
    live = data.get("liveData") or {}
    box = live.get("boxscore") or {}
    probable = game_data.get("probablePitchers") or {}

    for side in ("away", "home"):
        other = "home" if side == "away" else "away"
        team = meta.get(f"{side}_team")
        opponent = meta.get(f"{other}_team")
        side_box = ((box.get("teams") or {}).get(side) or {})
        pitchers = probable.get(side) or {}

        pitcher_base = base_row(
            "MLB", event_id, start, team, opponent, side,
            "STARTING_PITCHER",
            "POSTED" if pitchers else "NOT_POSTED",
            "MLB_STATSAPI", "OFFICIAL_LEAGUE_FEED",
        )
        rows.append(pitcher_base)
        if pitchers:
            rows.append(player_row(
                {**pitcher_base, "state": "PROBABLE_OFFICIAL"},
                pitchers.get("id"), pitchers.get("fullName"), "P",
            ))
        batting_order = side_box.get("battingOrder") or []
        lineup_base = base_row(
            "MLB", event_id, start, team, opponent, side,
            "BATTING_LINEUP",
            "POSTED" if batting_order else "NOT_POSTED",
            "MLB_STATSAPI", "OFFICIAL_LEAGUE_FEED",
        )
        rows.append(lineup_base)

        players = side_box.get("players") or {}
        for index, player_id in enumerate(batting_order, start=1):
            info = players.get(f"ID{player_id}") or {}
            person = info.get("person") or {}
            position = info.get("position") or {}
            rows.append(player_row(
                {**lineup_base, "state": "CONFIRMED_OFFICIAL"},
                player_id,
                person.get("fullName"),
                position.get("abbreviation"),
                index,
            ))
    return rows
def parse_basketball(sport, event_id, meta, data):
    rows = []
    start = meta.get("start")
    blocks = (data.get("boxscore") or {}).get("players") or []
    by_team = {}
    for block in blocks:
        team = block.get("team") or {}
        abbr = clean(team.get("abbreviation"))
        starters = []
        for stat_block in block.get("statistics") or []:
            for item in stat_block.get("athletes") or []:
                if item.get("starter") is True:
                    starters.append(item)
        if abbr:
            by_team[abbr] = starters

    for side in ("away", "home"):
        other = "home" if side == "away" else "away"
        team = clean(meta.get(f"{side}_team"))
        opponent = clean(meta.get(f"{other}_team"))
        starters = by_team.get(team, [])
        state = "POSTED" if len(starters) >= 5 else ("PARTIAL" if starters else "NOT_POSTED")
        team_row = base_row(
            sport, event_id, start, team, opponent, side,
            "STARTING_FIVE", state,
            "ESPN_PUBLIC_GAME_SUMMARY", "STRUCTURED_GAME_FEED",
        )
        rows.append(team_row)
        for index, item in enumerate(starters, start=1):
            athlete = item.get("athlete") or {}
            position = athlete.get("position") or {}
            rows.append(player_row(
                {**team_row, "state": "CONFIRMED_SOURCE"},
                athlete.get("id"),
                athlete.get("displayName"),
                position.get("abbreviation"),
                index,
            ))
    return rows

def parse_nhl(event_id, meta, data):
    rows = []
    start = meta.get("start")
    stats = data.get("playerByGameStats") or {}
    for side in ("away", "home"):
        other = "home" if side == "away" else "away"
        team = clean(meta.get(f"{side}_team"))
        opponent = clean(meta.get(f"{other}_team"))
        block = stats.get(f"{side}Team") or {}
        goalies = block.get("goalies") or []
        starters = [g for g in goalies if g.get("starter") is True]

        team_row = base_row(
            "NHL", event_id, start, team, opponent, side,
            "STARTING_GOALIE",
            "POSTED" if starters else "NOT_POSTED",
            "NHL_GAMECENTER", "OFFICIAL_LEAGUE_FEED",
        )
        rows.append(team_row)
        for goalie in starters:
            name = (goalie.get("name") or {}).get("default")
            rows.append(player_row(
                {**team_row, "state": "CONFIRMED_OFFICIAL"},
                goalie.get("playerId"), name, "G", 1,
            ))
    return rows
current_rows = []
for sport, event_id, meta, data in fetched:
    try:
        if sport == "MLB":
            current_rows.extend(parse_mlb(event_id, meta, data))
        elif sport in {"NBA", "CBB"}:
            current_rows.extend(parse_basketball(sport, event_id, meta, data))
        elif sport == "NHL":
            current_rows.extend(parse_nhl(event_id, meta, data))
    except Exception as exc:
        errors.append({
            "sport": sport,
            "event_id": str(event_id),
            "stage": "parse",
            "error": repr(exc),
        })

current = pd.DataFrame(current_rows)
if not current.empty:
    current = current.drop_duplicates(
        ["sport", "event_id", "team", "role", "entity_type", "player_key", "order_number"],
        keep="last",
    ).reset_index(drop=True)

def role_signature(frame):
    team_rows = frame[frame["entity_type"] == "TEAM"]
    state = clean(team_rows.iloc[0]["state"]) if not team_rows.empty else "UNKNOWN"
    players = frame[frame["entity_type"] == "PLAYER"].copy()
    if not players.empty:
        players["_order"] = pd.to_numeric(players["order_number"], errors="coerce").fillna(999)
        players = players.sort_values(["_order", "player_key"])
        parts = [
            f"{clean(r.player_key)}:{clean(r.order_number)}:{clean(r.state)}"
            for r in players.itertuples()
        ]
    else:
        parts = []
    return state, state + "|" + "|".join(parts)
state_rows = []
if not current.empty:
    for keys, frame in current.groupby(["sport", "event_id", "team", "role"], dropna=False):
        sport, event_id, team, role = keys
        team_row = frame[frame["entity_type"] == "TEAM"].iloc[0]
        state, signature = role_signature(frame)
        state_rows.append({
            "sport": sport,
            "event_id": str(event_id),
            "start": clean(team_row.get("start")),
            "team": clean(team),
            "opponent": clean(team_row.get("opponent")),
            "side": clean(team_row.get("side")),
            "role": clean(role),
            "state": state,
            "signature": signature,
            "source": clean(team_row.get("source")),
            "source_tier": clean(team_row.get("source_tier")),
            "observation_phase": clean(team_row.get("observation_phase")),
        })

state_current = pd.DataFrame(state_rows)
prior_timeline = read_csv(TIMELINE_OUT)
timeline_rows = prior_timeline.to_dict("records") if not prior_timeline.empty else []
latest = {}
for row in timeline_rows:
    key = (
        clean(row.get("sport")),
        clean(row.get("event_id")),
        clean(row.get("team")),
        clean(row.get("role")),
    )
    latest[key] = row

prior_changes = read_csv(CHANGES_OUT)
change_rows = prior_changes.to_dict("records") if not prior_changes.empty else []
CHANGE_NAMES = {
    "BATTING_LINEUP": ("LINEUP_POSTED", "LINEUP_CHANGED"),
    "STARTING_PITCHER": ("PROBABLE_PITCHER_POSTED", "PROBABLE_PITCHER_CHANGED"),
    "STARTING_FIVE": ("STARTERS_POSTED", "STARTERS_CHANGED"),
    "STARTING_GOALIE": ("GOALIE_POSTED", "GOALIE_CHANGED"),
}

new_timeline = 0
new_changes = 0
for row in state_current.to_dict("records") if not state_current.empty else []:
    key = (row["sport"], row["event_id"], row["team"], row["role"])
    previous = latest.get(key)
    if previous and clean(previous.get("signature")) == clean(row.get("signature")):
        continue

    entry = {
        "observed_at": NOW.isoformat(),
        **row,
    }
    timeline_rows.append(entry)
    latest[key] = entry
    new_timeline += 1

    if previous:
        posted_name, changed_name = CHANGE_NAMES.get(
            row["role"], ("STATE_POSTED", "STATE_CHANGED")
        )
        before_state = clean(previous.get("state"))
        after_state = clean(row.get("state"))
        if before_state in {"NOT_POSTED", "PARTIAL"} and after_state == "POSTED":
            change_type = posted_name
        else:
            change_type = changed_name
        change_rows.append({
            "changed_at": NOW.isoformat(),
            "sport": row["sport"],
            "event_id": row["event_id"],
            "start": row["start"],
            "team": row["team"],
            "opponent": row["opponent"],
            "role": row["role"],
            "change_type": change_type,
            "before_state": before_state,
            "after_state": after_state,
            "before_signature": clean(previous.get("signature")),
            "after_signature": clean(row.get("signature")),
            "observation_phase": row["observation_phase"],
            "source": row["source"],
            "source_tier": row["source_tier"],
        })
        new_changes += 1

timeline = pd.DataFrame(timeline_rows)
changes = pd.DataFrame(change_rows)
source_rows = []
for sport, source, tier in [
    ("MLB", "MLB_STATSAPI", "OFFICIAL_LEAGUE_FEED"),
    ("NBA", "ESPN_PUBLIC_GAME_SUMMARY", "STRUCTURED_GAME_FEED"),
    ("CBB", "ESPN_PUBLIC_GAME_SUMMARY", "STRUCTURED_GAME_FEED"),
    ("NHL", "NHL_GAMECENTER", "OFFICIAL_LEAGUE_FEED"),
]:
    event_ids = {
        str(event_id) for got_sport, event_id, _, _ in fetched if got_sport == sport
    }
    sport_states = (
        state_current[state_current["sport"] == sport]
        if not state_current.empty else pd.DataFrame()
    )
    posted = int((sport_states["state"] == "POSTED").sum()) if not sport_states.empty else 0
    partial = int((sport_states["state"] == "PARTIAL").sum()) if not sport_states.empty else 0
    pregame_posted = int(
        ((sport_states["state"] == "POSTED") & (sport_states["observation_phase"] == "PRE_GAME")).sum()
    ) if not sport_states.empty else 0
    sport_errors = [x for x in errors if x.get("sport") == sport]
    if sport_errors:
        status = "PARTIAL_ERRORS"
    elif not event_ids:
        status = "NO_GAMES_IN_WINDOW"
    elif posted:
        status = "ACTIVE_POSTINGS"
    else:
        status = "NO_STARTERS_POSTED_YET"
    source_rows.append({
        "sport": sport,
        "source": source,
        "source_tier": tier,
        "status": status,
        "events_checked": len(event_ids),
        "team_role_states": len(sport_states),
        "posted_role_states": posted,
        "partial_role_states": partial,
        "pregame_posted_role_states": pregame_posted,
        "window_hours_forward": 48,
        "generated_at": NOW.isoformat(),
    })
for sport in ("NFL", "CFB"):
    source_rows.append({
        "sport": sport,
        "source": "EXISTING_AVAILABILITY_ROLE_SYSTEM",
        "source_tier": "GOVERNED_EXISTING_CONTEXT",
        "status": "STARTER_FEED_NOT_MODELED",
        "events_checked": 0,
        "team_role_states": 0,
        "posted_role_states": 0,
        "partial_role_states": 0,
        "pregame_posted_role_states": 0,
        "window_hours_forward": 48,
        "generated_at": NOW.isoformat(),
    })

sources = pd.DataFrame(source_rows)

current.to_csv(CURRENT_OUT, index=False)
timeline.to_csv(TIMELINE_OUT, index=False)
changes.to_csv(CHANGES_OUT, index=False)
sources.to_csv(SOURCE_OUT, index=False)

posted_by_role = {}
phase_counts = {}
player_confirmations = 0
if not current.empty:
    team_rows = current[current["entity_type"] == "TEAM"]
    player_rows = current[current["entity_type"] == "PLAYER"]
    player_confirmations = len(player_rows)
    posted_by_role = (
        team_rows.groupby(["role", "state"]).size().to_dict()
        if not team_rows.empty else {}
    )
    phase_counts = current["observation_phase"].value_counts().to_dict()

posted_by_role_json = {
    f"{role}:{state}": int(count)
    for (role, state), count in posted_by_role.items()
}

receipt = {
    "generated_at": NOW.isoformat(),
    "window_start": WINDOW_START.isoformat(),
    "window_end": WINDOW_END.isoformat(),
    "events_requested": len(tasks),
    "events_fetched": len(fetched),
    "current_rows": len(current),
    "team_role_states": len(state_current),
    "player_confirmation_rows": player_confirmations,
    "posted_by_role_state": posted_by_role_json,
    "observation_phase_counts": phase_counts,
    "timeline_rows": len(timeline),
    "new_timeline_states": new_timeline,
    "change_rows": len(changes),
    "new_changes": new_changes,
    "source_status": {
        row["sport"]: row["status"] for row in source_rows
    },
    "leakage_guard": (
        "Every observation records PRE_GAME vs LIVE_OR_POST; "
        "post-start confirmations must not be used as pregame features."
    ),
    "explicit_gaps": [
        {
            "sport": "NHL",
            "capability": "pregame_starting_goalie",
            "status": "source may remain NOT_POSTED until official game feed exposes starter",
        },
        {
            "sport": "NBA",
            "capability": "pregame_starting_five",
            "status": "captured when structured game summary exposes starter flags",
        },
        {
            "sport": "CBB",
            "capability": "pregame_starting_five",
            "status": "future-ready; no games currently inside 48h window",
        },
        {
            "sport": "NFL",
            "capability": "starter_confirmation",
            "status": "not modeled; availability/inactives and role/depth context are more meaningful",
        },
        {
            "sport": "CFB",
            "capability": "starter_confirmation",
            "status": "not modeled; roster/availability/role context retained separately",
        },
    ],
    "score_is_probability": False,
    "automatic_model_adjustment": False,
    "paid_provider_required": False,
    "errors": errors,
}
RECEIPT_OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True))

print("EVENTS REQUESTED:", len(tasks))
print("EVENTS FETCHED:", len(fetched))
print("CURRENT ROWS:", len(current))
print("TEAM ROLE STATES:", len(state_current))
print("PLAYER CONFIRMATIONS:", player_confirmations)
print("POSTED STATES:", posted_by_role_json)
print("NEW TIMELINE STATES:", new_timeline)
print("NEW CHANGES:", new_changes)
print("SOURCE STATUS:", receipt["source_status"])
print("ERRORS:", len(errors))
print("RESULT: STARTER_LIFECYCLE_READY")
