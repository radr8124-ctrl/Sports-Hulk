from pathlib import Path
from datetime import datetime, timezone
import os
import sys
import json
import requests
import pandas as pd
from dotenv import load_dotenv

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "prizepicks_live" / "derived"
HISTORY = ROOT / "prizepicks_live" / "history"

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


def fetch_league(league, expected_events):

    allowed, reason = can_fetch(
        "flex",
        expected_entities=expected_events
    )

    print()
    print("LEAGUE:", league)
    print("GOVERNOR:", reason)

    if not allowed:
        return []

    r = requests.get(
        "https://api.sportsgameodds.com/v2/events",
        headers={"X-API-Key": KEY},
        params={
            "leagueID": league,
            "bookmakerID": "prizepicks",
            "oddsAvailable": "true",
            "includeAltLines": "false",
            "limit": expected_events,
        },
        timeout=45,
    )

    print("HTTP:", r.status_code)

    if r.status_code != 200:
        print(r.text[:1000])
        return []

    payload = r.json()

    stamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    (
        HISTORY
        / f"{league}_PRIZEPICKS_RAW_{stamp}.json"
    ).write_text(
        json.dumps(payload, indent=2)
    )

    return payload.get("data", [])


def normalize(events, league):

    rows = []

    for event in events:

        event_id = event.get("eventID")
        teams = event.get("teams", {}) or {}

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

            if item.get("betTypeID") != "ou":
                continue

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

            by_book = (
                item.get("byBookmaker", {})
                or {}
            )

            pp = by_book.get("prizepicks")

            if not pp:
                continue

            if isinstance(pp, list):
                pp_items = pp
            else:
                pp_items = [pp]

            for pp_item in pp_items:

                if not isinstance(pp_item, dict):
                    continue

                available = pp_item.get(
                    "available",
                    True
                )

                if available is False:
                    continue

                player = (
                    stat_entity
                    .replace(f"_{league}", "")
                    .replace("_1", "")
                    .replace("_", " ")
                    .title()
                )

                line = (
                    pp_item.get("bookOverUnder")
                    or pp_item.get("overUnder")
                    or pp_item.get("line")
                    or item.get("bookOverUnder")
                )

                side = (
                    pp_item.get("sideID")
                    or item.get("sideID")
                )

                rows.append({
                    "league": league,
                    "event_id": event_id,
                    "start": start,
                    "away_team": away,
                    "home_team": home,
                    "player": player,
                    "player_id": stat_entity,
                    "stat": item.get("statID"),
                    "market_name": item.get("marketName"),
                    "side": side,
                    "prizepicks_line": line,
                    "fair_line": item.get("fairOverUnder"),
                    "fair_odds": item.get("fairOdds"),
                    "open_fair_line": item.get(
                        "openFairOverUnder"
                    ),
                    "odd_id": odd_id,
                    "collected_at":
                        datetime.now(
                            timezone.utc
                        ).isoformat(),
                })

    return pd.DataFrame(rows)


print("=" * 88)
print("SPORTS HULK PRIZEPICKS COLLECTOR")
print("=" * 88)

before = get_usage()

if before is not None:
    sync_usage(before)

print("MONTHLY ENTITIES BEFORE:", before)

# Keep this conservative.
# NFL current slate ≈16 games.
# MLB ≈15 games.
nfl_events = fetch_league("NFL", 16)
mlb_events = fetch_league("MLB", 15)

nfl = normalize(nfl_events, "NFL")
mlb = normalize(mlb_events, "MLB")

for league, df in [
    ("NFL", nfl),
    ("MLB", mlb),
]:

    path = (
        OUT
        / f"{league}_PRIZEPICKS.csv"
    )

    df.to_csv(
        path,
        index=False
    )

    stamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    df.to_csv(
        HISTORY
        / f"{league}_PRIZEPICKS_{stamp}.csv",
        index=False
    )

    print()
    print(league)
    print("ROWS:", len(df))
    print("FILE:", path)

    if not df.empty:
        print(
            df[
                [
                    "player",
                    "stat",
                    "side",
                    "prizepicks_line",
                    "fair_line",
                ]
            ]
            .head(20)
            .to_string(index=False)
        )

after = get_usage()

if after is not None:
    sync_usage(after)

print()
print("MONTHLY ENTITIES AFTER:", after)

if before is not None and after is not None:
    print(
        "ENTITIES USED THIS RUN:",
        after - before
    )

print("\nRESULT: PASS")
