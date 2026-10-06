from pathlib import Path
from datetime import datetime, timezone, timedelta
import json
import os
import time
import requests
import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv("/home/ubuntu/sports-hulk/.env")
except Exception:
    pass

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "nfl_live/multisource"
QUALITY = OUT / "quality"
QUALITY.mkdir(parents=True, exist_ok=True)

NOW = datetime.now(timezone.utc)
TIMEOUT = 30


def get_json(url, headers=None, params=None):
    r = requests.get(
        url,
        headers=headers or {},
        params=params or {},
        timeout=TIMEOUT,
    )

    try:
        payload = r.json()
    except Exception:
        payload = {}

    return r, payload


def sw_paginate(endpoint, params, max_pages=4):
    key = (
        os.getenv("SPORTWIZZARD_API_KEY")
        or ""
    ).strip()

    if not key:
        return [], []

    headers = {"X-Api-Key": key}

    url = (
        "https://api.sportwizzard.com"
        "/api/v1"
        + endpoint
    )

    rows = []
    receipts = []
    cursor = None

    for page in range(1, max_pages + 1):

        q = dict(params)

        if cursor:
            q["cursor"] = cursor

        r, payload = get_json(
            url,
            headers=headers,
            params=q,
        )

        data = (
            payload.get("data", [])
            if isinstance(payload, dict)
            else []
        )

        next_cursor = (
            payload.get("nextCursor")
            if isinstance(payload, dict)
            else None
        )

        receipts.append({
            "page": page,
            "http": r.status_code,
            "rows": len(data),
            "next_cursor_present": bool(
                next_cursor
            ),
        })

        if r.status_code != 200:
            break

        rows.extend(data)

        if not next_cursor:
            break

        cursor = next_cursor

    return rows, receipts


print()
print("=== SPORTWIZZARD MULTI-BOOK ODDS ===")

odds, odds_receipts = sw_paginate(
    "/odds",
    {
        "league": "nfl",
        "scope": "event",
        "limit": 500,
    },
    max_pages=4,
)

print(
    "PAGE RECEIPTS:",
    odds_receipts,
)

print(
    "TOTAL ROWS:",
    len(odds),
)

books = sorted({
    str(x.get("sportsbook"))
    for x in odds
    if x.get("sportsbook")
})

print(
    "SPORTSBOOK COUNT:",
    len(books),
)

print(
    "SPORTSBOOKS:",
    books,
)


print()
print("=== SPORTWIZZARD PRIZEPICKS ===")

pp, pp_receipts = sw_paginate(
    "/odds",
    {
        "league": "nfl",
        "scope": "event",
        "sportsbook": "prizepicks",
        "limit": 500,
    },
    max_pages=4,
)

print(
    "PAGE RECEIPTS:",
    pp_receipts,
)

print(
    "TOTAL ROWS:",
    len(pp),
)


print()
print("=== SPORTWIZZARD DFS EDGES ===")

edges, edge_receipts = sw_paginate(
    "/edges",
    {
        "league": "nfl",
        "limit": 500,
    },
    max_pages=4,
)

print(
    "PAGE RECEIPTS:",
    edge_receipts,
)

print(
    "TOTAL ROWS:",
    len(edges),
)


# ==================================================
# PROP QUALITY
# ==================================================

rows = []

for x in pp:

    start = pd.to_datetime(
        x.get("eventStartTime"),
        utc=True,
        errors="coerce",
    )

    rows.append({
        "event_id": x.get("eventId"),
        "start": start,
        "player": x.get("playerName"),
        "market": x.get("market"),
        "market_subtype": (
            x.get("marketSubtype")
        ),
        "period": x.get("period"),
        "side": x.get("side"),
        "line": x.get("line"),
        "dfs_multiplier": (
            x.get("dfsMultiplier")
        ),
        "suspended": x.get("suspended"),
        "updated": x.get("updated"),
    })

ppdf = pd.DataFrame(rows)

if not ppdf.empty:

    ppdf["line"] = pd.to_numeric(
        ppdf["line"],
        errors="coerce",
    )

    print()
    print("=== PRIZEPICKS PERIODS ===")

    print(
        ppdf["period"]
        .fillna("NULL")
        .value_counts()
        .head(30)
        .to_string()
    )

    print()
    print("=== DFS MULTIPLIERS ===")

    print(
        ppdf["dfs_multiplier"]
        .fillna("NULL")
        .value_counts()
        .head(30)
        .to_string()
    )

    print()
    print("=== SUSPENDED ===")

    print(
        ppdf["suspended"]
        .fillna("NULL")
        .value_counts()
        .to_string()
    )

    future = ppdf[
        ppdf["start"].notna()
        & (
            ppdf["start"]
            >= pd.Timestamp(NOW)
        )
    ].copy()

    usable = future.copy()

    if "suspended" in usable:
        usable = usable[
            usable["suspended"]
            .fillna(False)
            .eq(False)
        ]

    print()
    print(
        "FUTURE PRIZEPICKS ROWS:",
        len(future),
    )

    print(
        "UNSUSPENDED FUTURE ROWS:",
        len(usable),
    )

    print(
        "UNIQUE PLAYERS:",
        usable["player"]
        .dropna()
        .nunique(),
    )

    print()
    print("TOP PROP MARKETS:")

    print(
        usable["market_subtype"]
        .value_counts()
        .head(40)
        .to_string()
    )

    ppdf.to_csv(
        QUALITY
        / "NFL_PRIZEPICKS_ALL_PAGED.csv",
        index=False,
    )


# ==================================================
# EDGE QUALITY
# ==================================================

erows = []

for x in edges:

    erows.append({
        "event_id": x.get("eventId"),
        "start": x.get(
            "eventStartTime"
        ),
        "player": x.get(
            "playerName"
        ),
        "player_team": x.get(
            "playerTeamName"
        ),
        "market": x.get("market"),
        "stat_type": x.get(
            "statType"
        ),
        "period": x.get("period"),
        "side": x.get("side"),
        "line": x.get("line"),
        "dfs_source": x.get(
            "dfsSource"
        ),
        "dfs_multiplier": x.get(
            "dfsMultiplier"
        ),
        "book_source": x.get(
            "bookSource"
        ),
        "book_probability": x.get(
            "bookImpliedProbability"
        ),
    })

edf = pd.DataFrame(erows)

if not edf.empty:

    edf["book_probability"] = (
        pd.to_numeric(
            edf["book_probability"],
            errors="coerce",
        )
    )

    print()
    print("=== DFS SOURCES ===")

    print(
        edf["dfs_source"]
        .value_counts()
        .to_string()
    )

    print()
    print("=== EDGE PERIODS ===")

    print(
        edf["period"]
        .fillna("NULL")
        .value_counts()
        .head(30)
        .to_string()
    )

    print()
    print("=== STRONGEST RAW EDGE ROWS ===")

    cols = [
        "player",
        "market",
        "period",
        "side",
        "line",
        "dfs_source",
        "book_source",
        "book_probability",
    ]

    print(
        edf.sort_values(
            "book_probability",
            ascending=False,
        )[cols]
        .head(25)
        .to_string(index=False)
    )

    edf.to_csv(
        QUALITY
        / "NFL_DFS_EDGES_ALL_PAGED.csv",
        index=False,
    )


# ==================================================
# ODDSPAPI — CORRECT WINDOW
# ==================================================

op = (
    os.getenv("ODDSPAPI_API_KEY")
    or ""
).strip()

fixture_count = 0

if op:

    later = NOW + timedelta(
        hours=48
    )

    r, payload = get_json(
        "https://api.oddspapi.io/v4/fixtures",
        params={
            "apiKey": op,
            "sportId": 14,
            "from": NOW.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "to": later.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "statusId": 0,
            "hasOdds": "true",
            "language": "en",
        },
    )

    fixtures = (
        payload
        if isinstance(payload, list)
        else payload.get(
            "data",
            payload.get(
                "fixtures",
                [],
            ),
        )
        if isinstance(payload, dict)
        else []
    )

    fixture_count = len(fixtures)

    print()
    print("=== ODDSPAPI ===")
    print("HTTP:", r.status_code)
    print(
        "48-HOUR FIXTURES:",
        fixture_count,
    )

    if fixtures:

        for f in fixtures[:20]:
            print(
                f.get(
                    "participant1Name"
                ),
                "vs",
                f.get(
                    "participant2Name"
                ),
                "|",
                f.get("startTime"),
                "|",
                f.get(
                    "tournamentName"
                ),
            )


# ==================================================
# SAVE AUDIT
# ==================================================

summary = {
    "generated_at": NOW.isoformat(),
    "sportwizzard_odds_rows": (
        len(odds)
    ),
    "sportwizzard_sportsbooks": (
        books
    ),
    "sportwizzard_sportsbook_count": (
        len(books)
    ),
    "prizepicks_rows": len(pp),
    "dfs_edge_rows": len(edges),
    "oddspapi_48h_fixtures": (
        fixture_count
    ),
    "odds_pages": odds_receipts,
    "prizepicks_pages": pp_receipts,
    "edge_pages": edge_receipts,
}

(
    QUALITY
    / "NFL_SOURCE_QUALITY.json"
).write_text(
    json.dumps(
        summary,
        indent=2,
    )
)

print()
print("==================================================")
print("PHASE 15E QUALITY RESULT")
print("==================================================")

print(
    "SPORTSWIZZARD BOOKS:",
    len(books),
)

print(
    "PRIZEPICKS ROWS:",
    len(pp),
)

print(
    "DFS EDGE ROWS:",
    len(edges),
)

print(
    "ODDSPAPI FIXTURES:",
    fixture_count,
)

print()
print(
    "No production betting board changed."
)

print(
    "No prop recommendation generated."
)
