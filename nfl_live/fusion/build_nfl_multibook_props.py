from pathlib import Path
from datetime import datetime, timezone
import json
import os
import re
import requests
import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv("/home/ubuntu/sports-hulk/.env")
except Exception:
    pass

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "nfl_live/fusion"
HIST = OUT / "history"

OUT.mkdir(parents=True, exist_ok=True)
HIST.mkdir(parents=True, exist_ok=True)

NOW = datetime.now(timezone.utc)
STAMP = NOW.strftime("%Y%m%dT%H%M%SZ")

KEY = (
    os.getenv("SPORTWIZZARD_API_KEY")
    or ""
).strip()

if not KEY:
    raise SystemExit(
        "SPORTWIZZARD_API_KEY missing"
    )

BASE = (
    "https://api.sportwizzard.com"
    "/api/v1"
)

HEADERS = {
    "X-Api-Key": KEY,
}

TIMEOUT = 30


def request(path, params=None):
    r = requests.get(
        BASE + path,
        headers=HEADERS,
        params=params or {},
        timeout=TIMEOUT,
    )

    r.raise_for_status()

    return r.json()


def paginate(path, params, max_pages=3):

    rows = []
    cursor = None
    receipts = []

    for page in range(
        1,
        max_pages + 1,
    ):
        q = dict(params)

        if cursor:
            q["cursor"] = cursor

        payload = request(
            path,
            q,
        )

        data = payload.get(
            "data",
            [],
        )

        cursor = payload.get(
            "nextCursor"
        )

        receipts.append({
            "page": page,
            "rows": len(data),
            "next": bool(cursor),
        })

        rows.extend(data)

        if not cursor:
            break

    return rows, receipts


def norm(value):
    value = str(
        value or ""
    ).lower()

    return re.sub(
        r"[^a-z0-9]+",
        "",
        value,
    )


# ==================================================
# DISCOVER ACTUAL SPORTSBOOK IDS
# ==================================================

books_payload = request(
    "/sportsbooks"
)

available = {
    str(x.get("id", "")).lower()
    for x in books_payload.get(
        "data",
        [],
    )
    if x.get("id")
}

preferred = [
    "draftkings",
    "fanduel",
    "betmgm",
    "caesars",
    "fanatics",
    "hardrock",
    "pinnacle",
    "bet365",
    "thescore",
    "betparx",
    "ballybet",
]

selected = [
    book
    for book in preferred
    if book in available
]

print()
print("AVAILABLE BOOKS:", len(available))
print(
    "SELECTED BOOKS:",
    selected,
)

if len(selected) < 3:
    print(
        "WARNING: fewer than 3 preferred "
        "books available."
    )


# ==================================================
# EVENT LOOKUP
# ==================================================

events, event_receipts = paginate(
    "/events",
    {
        "league": "nfl",
        "limit": 100,
    },
    max_pages=2,
)

event_map = {}

for e in events:

    eid = e.get("id")

    if not eid:
        continue

    event_map[eid] = {
        "home_team": e.get(
            "homeTeamName"
        ),
        "away_team": e.get(
            "awayTeamName"
        ),
        "start": e.get(
            "startTime"
        ),
    }


# ==================================================
# COLLECT EACH SPORTSBOOK SEPARATELY
# ==================================================

all_rows = []
book_receipts = {}

for book in selected:

    print()
    print(
        "COLLECTING:",
        book,
    )

    rows, receipts = paginate(
        "/odds",
        {
            "league": "nfl",
            "scope": "event",
            "sportsbook": book,
            "limit": 500,
        },
        max_pages=3,
    )

    book_receipts[book] = {
        "rows": len(rows),
        "pages": receipts,
    }

    print(
        "  ROWS:",
        len(rows),
    )

    for x in rows:

        eid = x.get("eventId")

        ev = event_map.get(
            eid,
            {},
        )

        player = x.get(
            "playerName"
        )

        player_id = x.get(
            "playerId"
        )

        # Player props only.
        if not player and not player_id:
            continue

        period = str(
            x.get("period")
            or ""
        ).upper()

        # FULL GAME ONLY.
        if period != "FULL":
            continue

        if x.get("suspended") is True:
            continue

        start = pd.to_datetime(
            x.get(
                "eventStartTime"
            )
            or ev.get("start"),
            utc=True,
            errors="coerce",
        )

        if pd.isna(start):
            continue

        if (
            start
            < pd.Timestamp(NOW)
        ):
            continue

        line = pd.to_numeric(
            x.get("line"),
            errors="coerce",
        )

        price = pd.to_numeric(
            x.get(
                "priceAmerican"
            ),
            errors="coerce",
        )

        if pd.isna(line):
            continue

        all_rows.append({
            "provider":
                "sportwizzard",

            "sportsbook":
                book,

            "event_id":
                eid,

            "start":
                start,

            "away_team":
                ev.get(
                    "away_team"
                ),

            "home_team":
                ev.get(
                    "home_team"
                ),

            "player_id":
                player_id,

            "player":
                player,

            "player_key":
                norm(player),

            "market":
                x.get(
                    "market"
                ),

            "market_subtype":
                x.get(
                    "marketSubtype"
                ),

            "period":
                period,

            "side":
                str(
                    x.get(
                        "side"
                    )
                    or ""
                ).upper(),

            "line":
                line,

            "price_american":
                price,

            "price_decimal":
                x.get(
                    "priceDecimal"
                ),

            "updated":
                x.get(
                    "updated"
                ),

            "collected_at":
                NOW.isoformat(),
        })


raw = pd.DataFrame(
    all_rows
)

if raw.empty:
    raise SystemExit(
        "No live full-game "
        "sportsbook player props returned."
    )

raw["market_subtype"] = (
    raw["market_subtype"]
    .fillna("")
    .astype(str)
    .str.upper()
)

raw["side"] = (
    raw["side"]
    .fillna("")
    .astype(str)
    .str.upper()
)

raw = raw[
    raw["side"].isin(
        [
            "OVER",
            "UNDER",
        ]
    )
].copy()


# ==================================================
# SAVE RAW MULTI-BOOK PLAYER PROPS
# ==================================================

raw.to_csv(
    OUT
    / "NFL_MULTIBOOK_PLAYER_PROPS.csv",
    index=False,
)

raw.to_csv(
    HIST
    / (
        "NFL_MULTIBOOK_PLAYER_PROPS_"
        + STAMP
        + ".csv"
    ),
    index=False,
)


# ==================================================
# CONSENSUS BY PLAYER / MARKET / SIDE
# ==================================================

group = [
    "event_id",
    "start",
    "away_team",
    "home_team",
    "player_key",
    "player",
    "market_subtype",
    "side",
]


def american_implied(odds):

    odds = pd.to_numeric(
        odds,
        errors="coerce",
    )

    if pd.isna(odds):
        return None

    if odds < 0:
        return (
            abs(odds)
            / (
                abs(odds)
                + 100
            )
            * 100
        )

    if odds > 0:
        return (
            100
            / (
                odds
                + 100
            )
            * 100
        )

    return None


raw[
    "implied_probability_raw"
] = raw[
    "price_american"
].map(
    american_implied
)


cons = (
    raw
    .groupby(
        group,
        dropna=False,
    )
    .agg(
        book_count=(
            "sportsbook",
            "nunique",
        ),

        books=(
            "sportsbook",
            lambda x:
                ",".join(
                    sorted(
                        set(
                            str(v)
                            for v in x
                        )
                    )
                ),
        ),

        line_median=(
            "line",
            "median",
        ),

        line_low=(
            "line",
            "min",
        ),

        line_high=(
            "line",
            "max",
        ),

        price_median=(
            "price_american",
            "median",
        ),

        implied_probability_median_raw=(
            "implied_probability_raw",
            "median",
        ),

        newest_update=(
            "updated",
            "max",
        ),
    )
    .reset_index()
)


# ==================================================
# MARKET QUALITY
# ==================================================

def quality(row):

    books = int(
        row["book_count"]
    )

    spread = (
        row["line_high"]
        - row["line_low"]
    )

    if (
        books >= 5
        and spread <= 1.0
    ):
        return "HIGH"

    if (
        books >= 3
        and spread <= 2.0
    ):
        return "GOOD"

    if books >= 2:
        return "LIMITED"

    return "SINGLE_BOOK"


cons["coverage_grade"] = (
    cons.apply(
        quality,
        axis=1,
    )
)


cons.to_csv(
    OUT
    / "NFL_MULTIBOOK_PROP_CONSENSUS.csv",
    index=False,
)


# ==================================================
# MATCH AGAINST LIVE DFS / PRIZEPICKS
# ==================================================

dfs_file = (
    OUT
    / "NFL_DFS_ALL_RESEARCH.csv"
)

matches = pd.DataFrame()

if dfs_file.exists():

    dfs = pd.read_csv(
        dfs_file,
        low_memory=False,
    )

    dfs["player_key"] = (
        dfs["player"]
        .map(norm)
    )

    dfs["market"] = (
        dfs["market"]
        .fillna("")
        .astype(str)
        .str.upper()
    )

    dfs["side"] = (
        dfs["side"]
        .fillna("")
        .astype(str)
        .str.upper()
    )

    dfs["line"] = pd.to_numeric(
        dfs["line"],
        errors="coerce",
    )

    # Join player + market + side.
    # We intentionally do NOT require
    # identical lines here so Hulk can
    # see actual line differences.
    matches = dfs.merge(
        cons,
        left_on=[
            "player_key",
            "market",
            "side",
        ],
        right_on=[
            "player_key",
            "market_subtype",
            "side",
        ],
        how="inner",
        suffixes=(
            "_dfs",
            "_sportsbook",
        ),
    )

    matches[
        "dfs_line"
    ] = pd.to_numeric(
        matches[
            "line"
        ],
        errors="coerce",
    )

    matches[
        "sportsbook_line"
    ] = pd.to_numeric(
        matches[
            "line_median"
        ],
        errors="coerce",
    )

    matches[
        "line_gap"
    ] = (
        matches[
            "sportsbook_line"
        ]
        - matches[
            "dfs_line"
        ]
    )

    matches.to_csv(
        OUT
        / "NFL_DFS_VS_MULTIBOOK.csv",
        index=False,
    )


# ==================================================
# ACCEPTANCE REPORT
# ==================================================

print()
print("==================================================")
print("NFL TRUE MULTI-BOOK PLAYER PROPS")
print("==================================================")

print(
    "Selected books:",
    len(selected),
)

print(
    "Raw full-game prop rows:",
    len(raw),
)

print(
    "Unique players:",
    raw["player"]
    .dropna()
    .nunique(),
)

print(
    "Unique prop markets:",
    raw[
        "market_subtype"
    ]
    .dropna()
    .nunique(),
)

print(
    "Consensus rows:",
    len(cons),
)

print()
print("COVERAGE GRADES:")

print(
    cons[
        "coverage_grade"
    ]
    .value_counts()
    .to_string()
)

print()
print("BOOK COVERAGE:")

print(
    raw.groupby(
        "sportsbook"
    )
    .size()
    .sort_values(
        ascending=False
    )
    .to_string()
)

print()
print("TOP MARKETS:")

print(
    raw[
        "market_subtype"
    ]
    .value_counts()
    .head(30)
    .to_string()
)

print()
print(
    "DFS ↔ SPORTSBOOK MATCHES:",
    len(matches),
)


if not matches.empty:

    show = [
        "player_dfs",
        "market",
        "side",
        "dfs_line",
        "sportsbook_line",
        "line_gap",
        "book_count",
        "books",
        "coverage_grade",
        "book_probability",
    ]

    show = [
        x for x in show
        if x in matches.columns
    ]

    print()
    print(
        "=== SAMPLE MATCHES ==="
    )

    print(
        matches[
            show
        ]
        .sort_values(
            [
                "book_count",
                "book_probability",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .head(30)
        .to_string(
            index=False
        )
    )


receipt = {
    "generated_at":
        NOW.isoformat(),

    "selected_books":
        selected,

    "book_receipts":
        book_receipts,

    "raw_prop_rows":
        len(raw),

    "unique_players":
        int(
            raw["player"]
            .dropna()
            .nunique()
        ),

    "unique_markets":
        int(
            raw[
                "market_subtype"
            ]
            .dropna()
            .nunique()
        ),

    "consensus_rows":
        len(cons),

    "dfs_sportsbook_matches":
        len(matches),
}

(
    OUT
    / "NFL_MULTIBOOK_PROP_RECEIPT.json"
).write_text(
    json.dumps(
        receipt,
        indent=2,
        default=str,
    )
)


print()
print("IMPORTANT:")
print(
    "No recommendation thresholds "
    "were changed."
)

print(
    "No production UI changed."
)

print(
    "No parlays generated."
)
