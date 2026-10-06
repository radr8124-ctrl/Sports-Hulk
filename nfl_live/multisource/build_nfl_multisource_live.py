from pathlib import Path
from datetime import datetime, timezone
import json
import os
import time

import pandas as pd
import requests

try:
    from dotenv import load_dotenv
    load_dotenv("/home/ubuntu/sports-hulk/.env")
except Exception:
    pass

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "nfl_live/multisource"
HIST = OUT / "history"

OUT.mkdir(parents=True, exist_ok=True)
HIST.mkdir(parents=True, exist_ok=True)

NOW = datetime.now(timezone.utc)
STAMP = NOW.strftime("%Y%m%dT%H%M%SZ")

TIMEOUT = 30


def get_json(url, *, headers=None, params=None):
    r = requests.get(
        url,
        headers=headers or {},
        params=params or {},
        timeout=TIMEOUT,
    )

    try:
        payload = r.json()
    except Exception:
        payload = None

    return r, payload


def save_json(name, payload):
    p = HIST / f"{name}_{STAMP}.json"

    p.write_text(
        json.dumps(
            payload,
            indent=2,
            default=str,
        )
    )

    return p


def list_data(payload):
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in [
            "data",
            "events",
            "fixtures",
            "results",
        ]:
            x = payload.get(key)

            if isinstance(x, list):
                return x

    return []


report = {
    "generated_at": NOW.isoformat(),
    "providers": {},
}


# ==================================================
# SPORTWIZZARD
# ==================================================

sw = (
    os.getenv("SPORTWIZZARD_API_KEY")
    or ""
).strip()

sw_odds_rows = []
sw_pp_rows = []
sw_edge_rows = []
sw_event_rows = []

if sw:

    headers = {
        "X-Api-Key": sw,
    }

    base = "https://api.sportwizzard.com/api/v1"

    requests_to_make = [
        (
            "events",
            "/events",
            {
                "league": "nfl",
                "limit": 100,
            },
        ),
        (
            "odds",
            "/odds",
            {
                "league": "nfl",
                "scope": "event",
                "limit": 500,
            },
        ),
        (
            "prizepicks",
            "/odds",
            {
                "league": "nfl",
                "scope": "event",
                "sportsbook": "prizepicks",
                "limit": 500,
            },
        ),
        (
            "edges",
            "/edges",
            {
                "league": "nfl",
                "limit": 500,
            },
        ),
    ]

    for label, endpoint, params in requests_to_make:

        r, payload = get_json(
            base + endpoint,
            headers=headers,
            params=params,
        )

        report["providers"][
            f"sportwizzard_{label}"
        ] = {
            "http": r.status_code,
            "rows": len(
                list_data(payload)
            ),
        }

        save_json(
            f"SPORTWIZZARD_{label.upper()}",
            payload,
        )

        rows = list_data(payload)

        if label == "events":
            sw_event_rows = rows
        elif label == "odds":
            sw_odds_rows = rows
        elif label == "prizepicks":
            sw_pp_rows = rows
        elif label == "edges":
            sw_edge_rows = rows


# ==================================================
# THERUNDOWN
# ==================================================

rd = (
    os.getenv("THERUNDOWN_API_KEY")
    or ""
).strip()

rd_rows = []

if rd:

    headers = {
        "X-TheRundown-Key": rd,
    }

    today = NOW.date().isoformat()

    r, payload = get_json(
        f"https://therundown.io/api/v2/sports/2/events/{today}",
        headers=headers,
        params={
            "market_ids": "1,2,3",
            "main_line": "true",
            "hide_closed": "true",
        },
    )

    rd_rows = list_data(payload)

    report["providers"][
        "therundown"
    ] = {
        "http": r.status_code,
        "rows": len(rd_rows),
        "datapoints_used": (
            r.headers.get(
                "X-Datapoints-Used"
            )
        ),
        "datapoints_remaining": (
            r.headers.get(
                "X-Datapoints-Remaining"
            )
        ),
        "delay_seconds": (
            r.headers.get(
                "X-Data-Delay-Seconds"
            )
        ),
    }

    save_json(
        "THERUNDOWN_NFL",
        payload,
    )


# ==================================================
# ODDSPAPI
# ==================================================

op = (
    os.getenv("ODDSPAPI_API_KEY")
    or ""
).strip()

op_fixture_rows = []
op_odds_rows = []

if op:

    base = "https://api.oddspapi.io/v4"

    r, payload = get_json(
        base + "/fixtures",
        params={
            "apiKey": op,
            "sportId": 14,
            "statusId": 0,
            "hasOdds": "true",
            "language": "en",
        },
    )

    op_fixture_rows = list_data(payload)

    report["providers"][
        "oddspapi_fixtures"
    ] = {
        "http": r.status_code,
        "rows": len(
            op_fixture_rows
        ),
    }

    save_json(
        "ODDSPAPI_FIXTURES",
        payload,
    )

    # Current NFL fixtures only.
    nfl_fixtures = []

    for row in op_fixture_rows:

        tournament = str(
            row.get(
                "tournamentName",
                "",
            )
        ).lower()

        category = str(
            row.get(
                "categoryName",
                "",
            )
        ).lower()

        p1 = str(
            row.get(
                "participant1Name",
                "",
            )
        )

        p2 = str(
            row.get(
                "participant2Name",
                "",
            )
        )

        # NFL team fixtures from today's slate.
        if (
            "nfl" in tournament
            or "nfl" in category
            or (
                p1
                and p2
                and row.get("sportId") == 14
            )
        ):
            nfl_fixtures.append(row)

    # Limit live discovery calls.
    for fixture in nfl_fixtures[:20]:

        fid = fixture.get(
            "fixtureId"
        )

        if not fid:
            continue

        time.sleep(1.05)

        r2, p2 = get_json(
            base + "/odds",
            params={
                "apiKey": op,
                "fixtureId": fid,
                "oddsFormat": "american",
                "language": "en",
                "verbosity": 2,
            },
        )

        if r2.status_code != 200:
            continue

        op_odds_rows.append(p2)

    report["providers"][
        "oddspapi_odds"
    ] = {
        "fixtures_requested": min(
            len(nfl_fixtures),
            20,
        ),
        "fixtures_returned": len(
            op_odds_rows
        ),
    }

    save_json(
        "ODDSPAPI_ODDS",
        op_odds_rows,
    )


# ==================================================
# NORMALIZED SPORTWIZZARD EVENTS
# ==================================================

event_lookup = {}

for e in sw_event_rows:

    event_id = e.get("id")

    if not event_id:
        continue

    event_lookup[event_id] = {
        "home_team": (
            e.get("homeTeamName")
        ),
        "away_team": (
            e.get("awayTeamName")
        ),
        "start": (
            e.get("startTime")
        ),
    }


# ==================================================
# NORMALIZED SPORTWIZZARD GAME ODDS
# ==================================================

game_rows = []

for x in sw_odds_rows:

    eid = x.get("eventId")

    ev = event_lookup.get(
        eid,
        {},
    )

    game_rows.append(
        {
            "provider": "sportwizzard",
            "event_id": eid,
            "start": (
                x.get("eventStartTime")
                or ev.get("start")
            ),
            "away_team": ev.get(
                "away_team"
            ),
            "home_team": ev.get(
                "home_team"
            ),
            "sportsbook": x.get(
                "sportsbook"
            ),
            "market": x.get(
                "market"
            ),
            "market_subtype": x.get(
                "marketSubtype"
            ),
            "period": x.get(
                "period"
            ),
            "selection": x.get(
                "selection"
            ),
            "side": x.get(
                "side"
            ),
            "team_name": x.get(
                "teamName"
            ),
            "line": x.get(
                "line"
            ),
            "price_american": x.get(
                "priceAmerican"
            ),
            "price_decimal": x.get(
                "priceDecimal"
            ),
            "suspended": x.get(
                "suspended"
            ),
            "updated": x.get(
                "updated"
            ),
            "collected_at": (
                NOW.isoformat()
            ),
        }
    )

game_df = pd.DataFrame(
    game_rows
)

game_path = (
    OUT
    / "NFL_SPORTWIZZARD_ODDS.csv"
)

game_df.to_csv(
    game_path,
    index=False,
)


# ==================================================
# NORMALIZED PRIZEPICKS
# ==================================================

pp_rows = []

for x in sw_pp_rows:

    eid = x.get("eventId")

    ev = event_lookup.get(
        eid,
        {},
    )

    pp_rows.append(
        {
            "provider": "sportwizzard",
            "dfs_source": (
                x.get("sportsbook")
            ),
            "event_id": eid,
            "start": (
                x.get("eventStartTime")
                or ev.get("start")
            ),
            "away_team": ev.get(
                "away_team"
            ),
            "home_team": ev.get(
                "home_team"
            ),
            "player_id": x.get(
                "playerId"
            ),
            "player": x.get(
                "playerName"
            ),
            "market": x.get(
                "market"
            ),
            "market_subtype": x.get(
                "marketSubtype"
            ),
            "period": x.get(
                "period"
            ),
            "side": x.get(
                "side"
            ),
            "line": x.get(
                "line"
            ),
            "dfs_multiplier": x.get(
                "dfsMultiplier"
            ),
            "suspended": x.get(
                "suspended"
            ),
            "updated": x.get(
                "updated"
            ),
            "collected_at": (
                NOW.isoformat()
            ),
        }
    )

pp_df = pd.DataFrame(
    pp_rows
)

pp_path = (
    OUT
    / "NFL_PRIZEPICKS_LIVE.csv"
)

pp_df.to_csv(
    pp_path,
    index=False,
)


# ==================================================
# NORMALIZED DFS EDGES
# ==================================================

edge_rows = []

for x in sw_edge_rows:

    edge_rows.append(
        {
            "provider": "sportwizzard",
            "event_id": x.get(
                "eventId"
            ),
            "start": x.get(
                "eventStartTime"
            ),
            "home_team": x.get(
                "eventHomeTeam"
            ),
            "away_team": x.get(
                "eventAwayTeam"
            ),
            "player_id": x.get(
                "playerId"
            ),
            "player": x.get(
                "playerName"
            ),
            "player_team": x.get(
                "playerTeamName"
            ),
            "market": x.get(
                "market"
            ),
            "stat_type": x.get(
                "statType"
            ),
            "period": x.get(
                "period"
            ),
            "line": x.get(
                "line"
            ),
            "side": x.get(
                "side"
            ),
            "dfs_source": x.get(
                "dfsSource"
            ),
            "dfs_multiplier": x.get(
                "dfsMultiplier"
            ),
            "dfs_label": x.get(
                "dfsSelectionLabel"
            ),
            "book_source": x.get(
                "bookSource"
            ),
            "book_implied_probability": (
                x.get(
                    "bookImpliedProbability"
                )
            ),
            "odds_by_book": json.dumps(
                x.get(
                    "oddsByBook"
                ),
                default=str,
            ),
            "collected_at": (
                NOW.isoformat()
            ),
        }
    )

edge_df = pd.DataFrame(
    edge_rows
)

edge_path = (
    OUT
    / "NFL_DFS_EDGES.csv"
)

edge_df.to_csv(
    edge_path,
    index=False,
)


# ==================================================
# RECEIPT
# ==================================================

report["outputs"] = {
    "sportwizzard_odds_rows": len(
        game_df
    ),
    "prizepicks_rows": len(
        pp_df
    ),
    "edge_rows": len(
        edge_df
    ),
    "therundown_events": len(
        rd_rows
    ),
    "oddspapi_fixtures": len(
        op_fixture_rows
    ),
    "oddspapi_odds_objects": len(
        op_odds_rows
    ),
}

receipt = (
    OUT
    / "NFL_MULTISOURCE_RECEIPT.json"
)

receipt.write_text(
    json.dumps(
        report,
        indent=2,
    )
)


print()
print("==================================================")
print("NFL MULTI-SOURCE LIVE INTAKE")
print("==================================================")

print(
    "SportWizzard game odds:",
    len(game_df),
)

print(
    "SportWizzard PrizePicks:",
    len(pp_df),
)

print(
    "SportWizzard DFS edges:",
    len(edge_df),
)

print(
    "TheRundown events:",
    len(rd_rows),
)

print(
    "OddsPapi fixtures:",
    len(op_fixture_rows),
)

print(
    "OddsPapi odds objects:",
    len(op_odds_rows),
)

if not game_df.empty:

    print()
    print("SPORTSWIZZARD SPORTSBOOKS:")

    print(
        sorted(
            game_df[
                "sportsbook"
            ]
            .dropna()
            .astype(str)
            .unique()
        )
    )

    print()
    print("SPORTSWIZZARD MARKETS:")

    print(
        sorted(
            game_df[
                "market_subtype"
            ]
            .dropna()
            .astype(str)
            .unique()
        )[:80]
    )

if not pp_df.empty:

    print()
    print("PRIZEPICKS PLAYERS:", len(
        pp_df["player"]
        .dropna()
        .unique()
    ))

    print(
        "PRIZEPICKS MARKETS:"
    )

    print(
        sorted(
            pp_df[
                "market_subtype"
            ]
            .dropna()
            .astype(str)
            .unique()
        )[:100]
    )

if not edge_df.empty:

    print()
    print("DFS EDGE SOURCES:")

    print(
        sorted(
            edge_df[
                "dfs_source"
            ]
            .dropna()
            .astype(str)
            .unique()
        )
    )

    print()
    print("DFS EDGE SAMPLE:")

    cols = [
        "player",
        "market",
        "side",
        "line",
        "dfs_source",
        "book_source",
        "book_implied_probability",
    ]

    print(
        edge_df[
            [
                c for c in cols
                if c in edge_df.columns
            ]
        ]
        .head(12)
        .to_string(
            index=False
        )
    )

print()
print("RECEIPT:", receipt)
print()
print("IMPORTANT:")
print(
    "These files are isolated intake data."
)
print(
    "Existing production betting/prop/"
    "PrizePicks outputs were NOT overwritten."
)
