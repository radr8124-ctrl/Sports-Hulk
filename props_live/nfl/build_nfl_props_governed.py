from pathlib import Path
from datetime import datetime, timezone
import os
import sys
import json
import requests
import pandas as pd
from dotenv import load_dotenv

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "props_live" / "nfl" / "derived"
HISTORY = ROOT / "props_live" / "nfl" / "history"

OUT.mkdir(parents=True, exist_ok=True)
HISTORY.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT / "api_control"))

from sgo_entity_budget import can_fetch, sync_usage

KEY = os.getenv("SPORTSGAMEODDS_API_KEY")

if not KEY:
    raise SystemExit("SPORTSGAMEODDS_API_KEY missing")


def get_usage():
    r = requests.get(
        "https://api.sportsgameodds.com/v2/account/usage",
        headers={"X-API-Key": KEY},
        timeout=20,
    )

    if r.status_code != 200:
        return None

    data = r.json().get("data", {})
    month = (
        data.get("rateLimits", {})
        .get("per-month", {})
    )

    used = month.get(
        "currentIntervalEntities",
        month.get("current-entities")
    )

    return int(used) if used is not None else None


print("=" * 88)
print("SPORTS HULK NFL PLAYER PROPS COLLECTOR")
print("=" * 88)

# ------------------------------------------------------------
# SYNC BEFORE CALL
# ------------------------------------------------------------

before_usage = get_usage()

if before_usage is not None:
    sync_usage(before_usage)

print("MONTHLY ENTITIES BEFORE:", before_usage)

# Current NFL slate is 16 games.
expected_events = 16

allowed, reason = can_fetch(
    "nfl_props",
    expected_entities=expected_events
)

print("GOVERNOR:", reason)

if not allowed:
    current = OUT / "NFL_PLAYER_PROPS.csv"

    if current.exists():
        cached = pd.read_csv(current)
        print("USING CACHE:", len(cached), "rows")
        print("RESULT: CACHE")
        raise SystemExit(0)

    raise SystemExit("BLOCKED AND NO CACHE")


# ------------------------------------------------------------
# FETCH NFL EVENTS + PROPS
# ------------------------------------------------------------

r = requests.get(
    "https://api.sportsgameodds.com/v2/events",
    headers={"X-API-Key": KEY},
    params={
        "leagueID": "NFL",
        "oddsAvailable": "true",
        "includeAltLines": "false",
        "limit": expected_events,
    },
    timeout=40,
)

print("HTTP:", r.status_code)

if r.status_code != 200:
    print(r.text[:1500])
    raise SystemExit("RESULT: FAIL")

payload = r.json()
events = payload.get("data", [])

print("EVENTS RETURNED:", len(events))

# ------------------------------------------------------------
# ARCHIVE RAW
# ------------------------------------------------------------

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

(HISTORY / f"NFL_PROPS_RAW_{stamp}.json").write_text(
    json.dumps(payload, indent=2)
)

# ------------------------------------------------------------
# NORMALIZE STANDARD O/U PLAYER PROPS
# ------------------------------------------------------------

rows = []

for event in events:

    event_id = event.get("eventID")
    teams = event.get("teams", {})

    home = (
        teams.get("home", {})
        .get("names", {})
        .get("long")
    )

    away = (
        teams.get("away", {})
        .get("names", {})
        .get("long")
    )

    start = (
        event.get("startsAt")
        or event.get("startTime")
        or event.get("scheduledTime")
    )

    odds = event.get("odds", {}) or {}

    for odd_id, item in odds.items():

        stat_entity = str(
            item.get("statEntityID", "")
        )

        if stat_entity in {
            "",
            "all",
            "home",
            "away"
        }:
            continue

        if item.get("betTypeID") != "ou":
            continue

        player = (
            stat_entity
            .replace("_NFL", "")
            .replace("_1", "")
            .replace("_", " ")
            .title()
        )

        rows.append({
            "event_id": event_id,
            "start": start,
            "away_team": away,
            "home_team": home,
            "player": player,
            "player_id": stat_entity,
            "stat": item.get("statID"),
            "market_name": item.get("marketName"),
            "side": item.get("sideID"),
            "line": item.get("bookOverUnder"),
            "fair_line": item.get("fairOverUnder"),
            "open_line": item.get("openBookOverUnder"),
            "open_fair_line": item.get("openFairOverUnder"),
            "book_odds": item.get("bookOdds"),
            "fair_odds": item.get("fairOdds"),
            "open_book_odds": item.get("openBookOdds"),
            "open_fair_odds": item.get("openFairOdds"),
            "by_bookmaker": json.dumps(
                item.get("byBookmaker", {})
            ),
            "odd_id": odd_id,
            "collected_at":
                datetime.now(timezone.utc).isoformat(),
        })

df = pd.DataFrame(rows)

if not df.empty:

    df["start"] = pd.to_datetime(
        df["start"],
        errors="coerce",
        utc=True
    )

    df = df.sort_values(
        [
            "start",
            "player",
            "stat",
            "side"
        ]
    )

# ------------------------------------------------------------
# SAVE CURRENT + HISTORY
# ------------------------------------------------------------

df.to_csv(
    OUT / "NFL_PLAYER_PROPS.csv",
    index=False
)

df.to_parquet(
    OUT / "NFL_PLAYER_PROPS.parquet",
    index=False
)

df.to_csv(
    HISTORY / f"NFL_PLAYER_PROPS_{stamp}.csv",
    index=False
)

df.to_parquet(
    HISTORY / f"NFL_PLAYER_PROPS_{stamp}.parquet",
    index=False
)

# ------------------------------------------------------------
# SYNC ACTUAL ENTITY COST AFTER CALL
# ------------------------------------------------------------

after_usage = get_usage()

if after_usage is not None:
    sync_usage(after_usage)

actual_cost = None

if (
    before_usage is not None
    and after_usage is not None
):
    actual_cost = max(
        0,
        after_usage - before_usage
    )

print()
print("MONTHLY ENTITIES AFTER:", after_usage)
print("ACTUAL ENTITY COST:", actual_cost)
print("NORMALIZED PROP ROWS:", len(df))

if not df.empty:

    show_cols = [
        "player",
        "stat",
        "side",
        "line",
        "book_odds",
        "fair_odds",
    ]

    print()
    print(
        df[show_cols]
        .head(30)
        .to_string(index=False)
    )

print()
print("RESULT: LIVE")
