from pathlib import Path
from datetime import datetime, timezone
import os
import sys
import json
import requests
import pandas as pd
from dotenv import load_dotenv

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "props_live" / "mlb" / "derived"
HISTORY = ROOT / "props_live" / "mlb" / "history"

OUT.mkdir(parents=True, exist_ok=True)
HISTORY.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT / "api_control"))

from sgo_entity_budget import can_fetch, sync_usage

KEY = os.getenv("SPORTSGAMEODDS_API_KEY")

if not KEY:
    raise SystemExit("SPORTSGAMEODDS_API_KEY missing")

print("=" * 88)
print("SPORTS HULK MLB PLAYER PROPS COLLECTOR")
print("=" * 88)

# ------------------------------------------------------------
# FIRST GET ACCOUNT USAGE
# ------------------------------------------------------------

usage = requests.get(
    "https://api.sportsgameodds.com/v2/account/usage",
    headers={"X-API-Key": KEY},
    timeout=20,
)

if usage.status_code == 200:
    udata = usage.json().get("data", {})
    limits = udata.get("rateLimits", {})
    monthly = limits.get("per-month", {})

    used_entities = monthly.get(
        "currentIntervalEntities",
        monthly.get("current-entities")
    )

    if used_entities is not None:
        sync_usage(int(used_entities))
        print("MONTHLY ENTITIES USED:", used_entities)

# ------------------------------------------------------------
# FETCH UPCOMING MLB EVENTS
# ------------------------------------------------------------

r = requests.get(
    "https://api.sportsgameodds.com/v2/events",
    headers={"X-API-Key": KEY},
    params={
        "leagueID": "MLB",
        "oddsAvailable": "true",
        "includeAltLines": "false",
        "limit": 15,
    },
    timeout=30,
)

print("HTTP:", r.status_code)

if r.status_code != 200:
    print(r.text[:1500])
    raise SystemExit("RESULT: FAIL")

payload = r.json()
events = payload.get("data", [])

print("EVENTS RETURNED:", len(events))

allowed, reason = can_fetch(
    "mlb_props",
    expected_entities=len(events)
)

print("GOVERNOR:", reason)

if not allowed:
    current = OUT / "MLB_PLAYER_PROPS.csv"

    if current.exists():
        cached = pd.read_csv(current)
        print("USING CACHE:", len(cached), "rows")
        print("RESULT: CACHE")
        raise SystemExit(0)

    raise SystemExit("BLOCKED AND NO CACHE")

# ------------------------------------------------------------
# ARCHIVE RAW RESPONSE
# ------------------------------------------------------------

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

(HISTORY / f"MLB_PROPS_RAW_{stamp}.json").write_text(
    json.dumps(payload, indent=2)
)

# ------------------------------------------------------------
# NORMALIZE PROPS
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

        stat_id = item.get("statID")
        bet_type = item.get("betTypeID")
        side = item.get("sideID")

        # Only standard over/under props for clean V1
        if bet_type != "ou":
            continue

        player = (
            stat_entity
            .replace("_MLB", "")
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
            "stat": stat_id,
            "bet_type": bet_type,
            "side": side,
            "book_odds": item.get("bookOdds"),
            "fair_odds": item.get("fairOdds"),
            "line": item.get("bookOverUnder"),
            "fair_line": item.get("fairOverUnder"),
            "open_line": item.get("openBookOverUnder"),
            "open_fair_line": item.get("openFairOverUnder"),
            "market_name": item.get("marketName"),
            "by_bookmaker": json.dumps(item.get("byBookmaker", {})),
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

current_csv = OUT / "MLB_PLAYER_PROPS.csv"
current_pq = OUT / "MLB_PLAYER_PROPS.parquet"

df.to_csv(
    current_csv,
    index=False
)

df.to_parquet(
    current_pq,
    index=False
)

df.to_csv(
    HISTORY / f"MLB_PLAYER_PROPS_{stamp}.csv",
    index=False
)

df.to_parquet(
    HISTORY / f"MLB_PLAYER_PROPS_{stamp}.parquet",
    index=False
)

print()
print("NORMALIZED PROP ROWS:", len(df))

if not df.empty:
    print()
    print(
        df[
            [
                "player",
                "stat",
                "side",
                "line",
                "book_odds",
                "fair_odds",
            ]
        ].head(30).to_string(index=False)
    )

print()
print("RESULT: LIVE")
