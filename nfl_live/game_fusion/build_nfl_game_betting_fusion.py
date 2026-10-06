from pathlib import Path
from datetime import datetime, timezone, timedelta
import json
import os
import re

import numpy as np
import pandas as pd
import requests

try:
    from dotenv import load_dotenv
    load_dotenv("/home/ubuntu/sports-hulk/.env")
except Exception:
    pass


ROOT = Path("/home/ubuntu/sports-hulk")

OUT = (
    ROOT
    / "nfl_live"
    / "game_fusion"
)

HIST_OUT = OUT / "history"

OUT.mkdir(parents=True, exist_ok=True)
HIST_OUT.mkdir(parents=True, exist_ok=True)

NOW = datetime.now(timezone.utc)
STAMP = NOW.strftime("%Y%m%dT%H%M%SZ")

TIMEOUT = 30


# ==================================================
# CANONICAL NFL TEAM MAP
# ==================================================

alias_file = (
    ROOT
    / "nfl_live"
    / "identity"
    / "team_aliases.json"
)

aliases = json.loads(
    alias_file.read_text()
)


def token(v):
    if v is None or pd.isna(v):
        return ""

    s = str(v).lower()

    return re.sub(
        r"[^a-z0-9]+",
        "",
        s,
    )


TEAM_MAP = {}

for abbr, names in aliases.items():

    TEAM_MAP[token(abbr)] = abbr

    for name in names:
        TEAM_MAP[token(name)] = abbr


def team(v):
    k = token(v)

    if not k:
        return ""

    return TEAM_MAP.get(
        k,
        str(v).strip().upper(),
    )


def game_key(away, home):
    return (
        team(away)
        + "@"
        + team(home)
    )


def num(v):
    return pd.to_numeric(
        v,
        errors="coerce",
    )


def american_implied(v):

    try:
        x = float(v)
    except Exception:
        return np.nan

    if x < 0:
        return (
            abs(x)
            / (
                abs(x)
                + 100
            )
        )

    if x > 0:
        return (
            100
            / (
                x
                + 100
            )
        )

    return np.nan


def devig_pair(a, b):

    pa = american_implied(a)
    pb = american_implied(b)

    if (
        pd.isna(pa)
        or pd.isna(pb)
        or (
            pa + pb
        ) <= 0
    ):
        return (
            np.nan,
            np.nan,
        )

    total = pa + pb

    return (
        pa / total,
        pb / total,
    )


def get_json(
    url,
    *,
    headers=None,
    params=None,
):

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


# ==================================================
# PROPLINE — CURRENT CANONICAL GAME BOARD
# ==================================================

pl_file = (
    ROOT
    / "nfl_live"
    / "derived"
    / "NFL_LIVE_MARKET.csv"
)

if not pl_file.exists():
    raise SystemExit(
        "NFL_LIVE_MARKET.csv missing"
    )

pl = pd.read_csv(
    pl_file,
    low_memory=False,
)

pl["start"] = pd.to_datetime(
    pl["start"],
    utc=True,
    errors="coerce",
)

cutoff = (
    pd.Timestamp(NOW)
    + pd.Timedelta(hours=72)
)

pl = pl[
    pl["start"].notna()
    & (
        pl["start"]
        >= pd.Timestamp(NOW)
    )
    & (
        pl["start"]
        <= cutoff
    )
].copy()

pl["away_abbr"] = (
    pl["away_team"]
    .map(team)
)

pl["home_abbr"] = (
    pl["home_team"]
    .map(team)
)

pl["game_key"] = (
    pl.apply(
        lambda r:
            game_key(
                r["away_team"],
                r["home_team"],
            ),
        axis=1,
    )
)


pl[
    "away_moneyline"
] = num(
    pl["away_moneyline"]
)

pl[
    "home_moneyline"
] = num(
    pl["home_moneyline"]
)

pl[
    "away_spread"
] = num(
    pl["away_spread"]
)

pl[
    "home_spread"
] = num(
    pl["home_spread"]
)

pl["total"] = num(
    pl["total"]
)


devig = pl.apply(
    lambda r:
        devig_pair(
            r["away_moneyline"],
            r["home_moneyline"],
        ),
    axis=1,
)

pl[
    "propline_away_devig_prob"
] = [
    x[0]
    for x in devig
]

pl[
    "propline_home_devig_prob"
] = [
    x[1]
    for x in devig
]


print()
print(
    "PROPLINE UPCOMING GAMES:",
    len(pl),
)


# ==================================================
# SPORTWIZZARD — EVENTS
# ==================================================

sw_key = (
    os.getenv(
        "SPORTWIZZARD_API_KEY"
    )
    or ""
).strip()

if not sw_key:
    raise SystemExit(
        "SPORTWIZZARD_API_KEY missing"
    )

SW = (
    "https://api.sportwizzard.com"
    "/api/v1"
)

SW_HEADERS = {
    "X-Api-Key": sw_key,
}


def sw_paginate(
    path,
    params,
    max_pages=3,
):

    rows = []
    receipts = []
    cursor = None

    for page in range(
        1,
        max_pages + 1,
    ):

        q = dict(params)

        if cursor:
            q["cursor"] = cursor

        r, payload = get_json(
            SW + path,
            headers=SW_HEADERS,
            params=q,
        )

        data = (
            payload.get(
                "data",
                [],
            )
            if isinstance(
                payload,
                dict,
            )
            else []
        )

        cursor = (
            payload.get(
                "nextCursor"
            )
            if isinstance(
                payload,
                dict,
            )
            else None
        )

        receipts.append({
            "page": page,
            "http": r.status_code,
            "rows": len(data),
            "next": bool(cursor),
        })

        if r.status_code != 200:
            break

        rows.extend(data)

        if not cursor:
            break

    return rows, receipts


events, event_receipts = (
    sw_paginate(
        "/events",
        {
            "league": "nfl",
            "limit": 100,
        },
        max_pages=2,
    )
)

event_map = {}

for e in events:

    eid = e.get("id")

    if not eid:
        continue

    away = e.get(
        "awayTeamName"
    )

    home = e.get(
        "homeTeamName"
    )

    event_map[eid] = {
        "away_team": away,
        "home_team": home,
        "away_abbr": team(away),
        "home_abbr": team(home),
        "game_key": game_key(
            away,
            home,
        ),
        "start": e.get(
            "startTime"
        ),
    }


# ==================================================
# SPORTWIZZARD — BOOK DISCOVERY
# ==================================================

r, book_payload = get_json(
    SW + "/sportsbooks",
    headers=SW_HEADERS,
)

if r.status_code != 200:
    raise SystemExit(
        "SportWizzard books failed"
    )

available = {
    str(
        x.get(
            "id",
            "",
        )
    ).lower()
    for x in book_payload.get(
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
    "thescore",
    "betparx",
    "ballybet",
]

books = [
    b
    for b in preferred
    if b in available
]

print(
    "SPORTWIZZARD BOOKS:",
    books,
)


# ==================================================
# COLLECT EACH BOOK SEPARATELY
# ==================================================

sw_core = []

book_receipts = {}

for book in books:

    rows, receipts = (
        sw_paginate(
            "/odds",
            {
                "league": "nfl",
                "scope": "event",
                "sportsbook": book,
                "market":
                    "MONEYLINE,SPREAD,TOTAL",
                "limit": 500,
            },
            max_pages=2,
        )
    )

    book_receipts[
        book
    ] = {
        "raw_rows":
            len(rows),
        "pages":
            receipts,
    }

    accepted = 0

    for x in rows:

        if x.get(
            "suspended"
        ) is True:
            continue

        if str(
            x.get(
                "period"
            )
            or ""
        ).upper() != "FULL":
            continue

        market = str(
            x.get(
                "market"
            )
            or ""
        ).upper()

        if market not in {
            "MONEYLINE",
            "SPREAD",
            "TOTAL",
        }:
            continue

        eid = x.get(
            "eventId"
        )

        ev = event_map.get(
            eid
        )

        if not ev:
            continue

        start = pd.to_datetime(
            x.get(
                "eventStartTime"
            )
            or ev.get(
                "start"
            ),
            utc=True,
            errors="coerce",
        )

        if pd.isna(start):
            continue

        if start < pd.Timestamp(NOW):
            continue

        if start > cutoff:
            continue

        sw_core.append({
            "provider":
                "sportwizzard",

            "sportsbook":
                book,

            "event_id":
                eid,

            "game_key":
                ev[
                    "game_key"
                ],

            "away_team":
                ev[
                    "away_team"
                ],

            "home_team":
                ev[
                    "home_team"
                ],

            "away_abbr":
                ev[
                    "away_abbr"
                ],

            "home_abbr":
                ev[
                    "home_abbr"
                ],

            "start":
                start,

            "market":
                market,

            "market_subtype":
                str(
                    x.get(
                        "marketSubtype"
                    )
                    or ""
                ).upper(),

            "side":
                str(
                    x.get(
                        "side"
                    )
                    or ""
                ).upper(),

            "team_side":
                str(
                    x.get(
                        "teamSide"
                    )
                    or ""
                ).upper(),

            "team_name":
                x.get(
                    "teamName"
                ),

            "selection":
                x.get(
                    "selection"
                ),

            "line":
                num(
                    x.get(
                        "line"
                    )
                ),

            "price_american":
                num(
                    x.get(
                        "priceAmerican"
                    )
                ),

            "updated":
                x.get(
                    "updated"
                ),
        })

        accepted += 1

    book_receipts[
        book
    ][
        "accepted_core_rows"
    ] = accepted


sw = pd.DataFrame(
    sw_core
)

if sw.empty:
    raise SystemExit(
        "No SportWizzard core rows"
    )

sw.to_csv(
    OUT
    / "NFL_GAME_SPORTWIZZARD_RAW.csv",
    index=False,
)

sw.to_csv(
    HIST_OUT
    / (
        "NFL_GAME_SPORTWIZZARD_"
        + STAMP
        + ".csv"
    ),
    index=False,
)


print(
    "SPORTWIZZARD CORE ROWS:",
    len(sw),
)

print()
print("CORE BOOK COVERAGE:")

print(
    sw.groupby(
        "sportsbook"
    )
    .size()
    .sort_values(
        ascending=False
    )
    .to_string()
)


# ==================================================
# SPORTWIZZARD GAME-WIDE CONSENSUS
# ==================================================

def subset_value(
    frame,
    market,
    side=None,
    team_side=None,
):

    x = frame[
        frame[
            "market"
        ].eq(market)
    ].copy()

    if side is not None:
        x = x[
            x[
                "side"
            ].eq(side)
        ]

    if team_side is not None:
        x = x[
            x[
                "team_side"
            ].eq(team_side)
        ]

    return x


summary_rows = []

for gkey, g in (
    sw.groupby(
        "game_key"
    )
):

    first = g.iloc[0]

    row = {
        "game_key":
            gkey,

        "start":
            first[
                "start"
            ],

        "away_team":
            first[
                "away_team"
            ],

        "home_team":
            first[
                "home_team"
            ],

        "away_abbr":
            first[
                "away_abbr"
            ],

        "home_abbr":
            first[
                "home_abbr"
            ],

        "sw_unique_books":
            g[
                "sportsbook"
            ].nunique(),

        "sw_books":
            ",".join(
                sorted(
                    g[
                        "sportsbook"
                    ]
                    .dropna()
                    .astype(str)
                    .unique()
                )
            ),
    }

    for side_name in [
        "HOME",
        "AWAY",
    ]:

        ml = subset_value(
            g,
            "MONEYLINE",
            team_side=side_name,
        )

        spread = subset_value(
            g,
            "SPREAD",
            team_side=side_name,
        )

        p = side_name.lower()

        row[
            f"sw_{p}_ml"
        ] = (
            ml[
                "price_american"
            ].median()
            if not ml.empty
            else np.nan
        )

        row[
            f"sw_{p}_ml_books"
        ] = (
            ml[
                "sportsbook"
            ].nunique()
            if not ml.empty
            else 0
        )

        row[
            f"sw_{p}_spread"
        ] = (
            spread[
                "line"
            ].median()
            if not spread.empty
            else np.nan
        )

        row[
            f"sw_{p}_spread_low"
        ] = (
            spread[
                "line"
            ].min()
            if not spread.empty
            else np.nan
        )

        row[
            f"sw_{p}_spread_high"
        ] = (
            spread[
                "line"
            ].max()
            if not spread.empty
            else np.nan
        )

        row[
            f"sw_{p}_spread_books"
        ] = (
            spread[
                "sportsbook"
            ].nunique()
            if not spread.empty
            else 0
        )

    totals = g[
        g[
            "market"
        ].eq("TOTAL")
    ]

    row[
        "sw_total"
    ] = (
        totals[
            "line"
        ].median()
        if not totals.empty
        else np.nan
    )

    row[
        "sw_total_low"
    ] = (
        totals[
            "line"
        ].min()
        if not totals.empty
        else np.nan
    )

    row[
        "sw_total_high"
    ] = (
        totals[
            "line"
        ].max()
        if not totals.empty
        else np.nan
    )

    row[
        "sw_total_books"
    ] = (
        totals[
            "sportsbook"
        ].nunique()
        if not totals.empty
        else 0
    )

    away_p, home_p = devig_pair(
        row.get(
            "sw_away_ml"
        ),
        row.get(
            "sw_home_ml"
        ),
    )

    row[
        "sw_away_devig_prob"
    ] = away_p

    row[
        "sw_home_devig_prob"
    ] = home_p

    summary_rows.append(
        row
    )


sw_game = pd.DataFrame(
    summary_rows
)

sw_game.to_csv(
    OUT
    / "NFL_GAME_SPORTWIZZARD_CONSENSUS.csv",
    index=False,
)


# ==================================================
# THERUNDOWN — VERIFICATION LAYER
# ==================================================

rd_key = (
    os.getenv(
        "THERUNDOWN_API_KEY"
    )
    or ""
).strip()

rd_games = []
rd_receipts = []

if rd_key:

    for offset in [
        0,
        1,
    ]:

        d = (
            NOW
            + timedelta(
                days=offset
            )
        ).date()

        r, payload = get_json(
            (
                "https://therundown.io/"
                "api/v2/sports/2/events/"
                + d.isoformat()
            ),
            headers={
                "X-TheRundown-Key":
                    rd_key
            },
            params={
                "market_ids":
                    "1,2,3",

                "main_line":
                    "true",

                "hide_closed":
                    "true",
            },
        )

        events = (
            payload.get(
                "events",
                [],
            )
            if isinstance(
                payload,
                dict,
            )
            else []
        )

        rd_receipts.append({
            "date":
                d.isoformat(),
            "http":
                r.status_code,
            "events":
                len(events),
            "remaining":
                r.headers.get(
                    "X-Datapoints-Remaining"
                ),
            "delay_seconds":
                r.headers.get(
                    "X-Data-Delay-Seconds"
                ),
        })

        (
            HIST_OUT
            / (
                "THERUNDOWN_"
                + d.isoformat()
                + "_"
                + STAMP
                + ".json"
            )
        ).write_text(
            json.dumps(
                payload,
                indent=2,
                default=str,
            )
        )

        for event in events:

            teams = event.get(
                "teams",
                []
            )

            home = None
            away = None

            for t in teams:

                name = (
                    t.get(
                        "name"
                    )
                    or t.get(
                        "full_name"
                    )
                )

                if t.get(
                    "is_home"
                ) is True:
                    home = name

                if t.get(
                    "is_away"
                ) is True:
                    away = name

            if (
                not home
                and len(teams) >= 2
            ):
                home = teams[-1].get(
                    "name"
                )

            if (
                not away
                and len(teams) >= 2
            ):
                away = teams[0].get(
                    "name"
                )

            rd_games.append({
                "therundown_event_id":
                    event.get(
                        "event_id"
                    ),

                "game_key":
                    game_key(
                        away,
                        home,
                    ),

                "therundown_market_count":
                    len(
                        event.get(
                            "markets",
                            [],
                        )
                    ),
            })


rd = pd.DataFrame(
    rd_games
)

if not rd.empty:

    rd = (
        rd.sort_values(
            "therundown_market_count",
            ascending=False,
        )
        .drop_duplicates(
            "game_key",
            keep="first",
        )
    )

rd.to_csv(
    OUT
    / "NFL_GAME_THERUNDOWN_COVERAGE.csv",
    index=False,
)


# ==================================================
# PROPLINE HISTORICAL MOVEMENT
# ==================================================

history_dir = (
    ROOT
    / "nfl_live"
    / "history"
)

hist_frames = []

for p in sorted(
    history_dir.glob(
        "PROPLINE_NFL_NORMALIZED_*.csv"
    )
):

    try:
        h = pd.read_csv(
            p,
            low_memory=False,
        )

        if h.empty:
            continue

        h["start"] = pd.to_datetime(
            h["start"],
            utc=True,
            errors="coerce",
        )

        h["game_key"] = h.apply(
            lambda r:
                game_key(
                    r.get(
                        "away_team"
                    ),
                    r.get(
                        "home_team"
                    ),
                ),
            axis=1,
        )

        if "collected_at" in h.columns:

            h[
                "_snapshot"
            ] = pd.to_datetime(
                h[
                    "collected_at"
                ],
                utc=True,
                errors="coerce",
            )

        else:

            stamp = (
                p.stem
                .replace(
                    "PROPLINE_NFL_NORMALIZED_",
                    "",
                )
            )

            h[
                "_snapshot"
            ] = pd.to_datetime(
                stamp,
                format="%Y%m%dT%H%M%SZ",
                utc=True,
                errors="coerce",
            )

        hist_frames.append(
            h
        )

    except Exception:
        continue


movement_rows = []

if hist_frames:

    hist = pd.concat(
        hist_frames,
        ignore_index=True,
    )

    hist = hist[
        hist[
            "game_key"
        ].isin(
            pl[
                "game_key"
            ]
        )
    ].copy()

    for gkey, g in (
        hist.groupby(
            "game_key"
        )
    ):

        g = g.sort_values(
            "_snapshot"
        )

        first = g.iloc[0]
        latest = g.iloc[-1]

        movement_rows.append({
            "game_key":
                gkey,

            "opening_snapshot":
                first[
                    "_snapshot"
                ],

            "latest_snapshot":
                latest[
                    "_snapshot"
                ],

            "opening_home_spread":
                num(
                    first.get(
                        "home_spread"
                    )
                ),

            "latest_home_spread":
                num(
                    latest.get(
                        "home_spread"
                    )
                ),

            "home_spread_move":
                (
                    num(
                        latest.get(
                            "home_spread"
                        )
                    )
                    -
                    num(
                        first.get(
                            "home_spread"
                        )
                    )
                ),

            "opening_total":
                num(
                    first.get(
                        "total"
                    )
                ),

            "latest_total":
                num(
                    latest.get(
                        "total"
                    )
                ),

            "total_move":
                (
                    num(
                        latest.get(
                            "total"
                        )
                    )
                    -
                    num(
                        first.get(
                            "total"
                        )
                    )
                ),

            "opening_home_ml":
                num(
                    first.get(
                        "home_moneyline"
                    )
                ),

            "latest_home_ml":
                num(
                    latest.get(
                        "home_moneyline"
                    )
                ),

            "snapshot_count":
                len(g),
        })


movement = pd.DataFrame(
    movement_rows
)

movement.to_csv(
    OUT
    / "NFL_GAME_MARKET_MOVEMENT.csv",
    index=False,
)


# ==================================================
# INDEPENDENT FOOTBALL CONTEXT
# ==================================================

context_candidates = [
    ROOT
    / "nfl_live"
    / "derived"
    / "NFL_SURVIVOR_CONTEXT_WEATHER.csv",

    ROOT
    / "nfl_live"
    / "derived"
    / "NFL_ESPN_CONTEXT.csv",
]

context = None
context_source = None

for path in context_candidates:

    if not path.exists():
        continue

    try:
        c = pd.read_csv(
            path,
            low_memory=False,
        )

        if (
            "away_team"
            in c.columns
            and
            "home_team"
            in c.columns
        ):

            c[
                "game_key"
            ] = c.apply(
                lambda r:
                    game_key(
                        r[
                            "away_team"
                        ],
                        r[
                            "home_team"
                        ],
                    ),
                axis=1,
            )

            context = c
            context_source = (
                path.name
            )

            break

    except Exception:
        continue


# ==================================================
# MASTER RESEARCH BOARD
# ==================================================

board = pl.copy()

board = board.merge(
    sw_game[
        [
            c
            for c in sw_game.columns
            if c not in {
                "away_team",
                "home_team",
                "away_abbr",
                "home_abbr",
                "start",
            }
        ]
    ],
    on="game_key",
    how="left",
)


if not rd.empty:

    board = board.merge(
        rd[
            [
                "game_key",
                "therundown_event_id",
                "therundown_market_count",
            ]
        ],
        on="game_key",
        how="left",
    )

else:

    board[
        "therundown_event_id"
    ] = pd.NA

    board[
        "therundown_market_count"
    ] = pd.NA


if not movement.empty:

    board = board.merge(
        movement,
        on="game_key",
        how="left",
    )


if context is not None:

    # Preserve independent source columns
    # with a clear prefix.
    ctx = context.copy()

    rename = {}

    for c in ctx.columns:

        if c == "game_key":
            continue

        rename[c] = (
            "ctx_" + c
        )

    ctx = ctx.rename(
        columns=rename
    )

    ctx = (
        ctx
        .drop_duplicates(
            "game_key"
        )
    )

    board = board.merge(
        ctx,
        on="game_key",
        how="left",
    )


# ==================================================
# PROVIDER AGREEMENT
# ==================================================

board[
    "spread_difference"
] = (
    num(
        board[
            "home_spread"
        ]
    )
    -
    num(
        board[
            "sw_home_spread"
        ]
    )
).abs()

board[
    "total_difference"
] = (
    num(
        board[
            "total"
        ]
    )
    -
    num(
        board[
            "sw_total"
        ]
    )
).abs()

board[
    "home_prob_difference"
] = (
    num(
        board[
            "propline_home_devig_prob"
        ]
    )
    -
    num(
        board[
            "sw_home_devig_prob"
        ]
    )
).abs()


board[
    "spread_provider_agreement"
] = np.where(
    board[
        "spread_difference"
    ].le(0.5),
    "AGREE",
    np.where(
        board[
            "spread_difference"
        ].le(1.0),
        "CLOSE",
        "DISAGREE",
    ),
)


board[
    "total_provider_agreement"
] = np.where(
    board[
        "total_difference"
    ].le(0.5),
    "AGREE",
    np.where(
        board[
            "total_difference"
        ].le(1.5),
        "CLOSE",
        "DISAGREE",
    ),
)


board[
    "moneyline_provider_agreement"
] = np.where(
    board[
        "home_prob_difference"
    ].le(0.03),
    "AGREE",
    np.where(
        board[
            "home_prob_difference"
        ].le(0.06),
        "CLOSE",
        "DISAGREE",
    ),
)


# ==================================================
# DATA QUALITY ONLY — NOT A PICK SCORE
# ==================================================

def quality(r):

    sw_books = num(
        r.get(
            "sw_unique_books"
        )
    )

    rd_ok = pd.notna(
        r.get(
            "therundown_event_id"
        )
    )

    spread = r.get(
        "spread_provider_agreement"
    )

    total = r.get(
        "total_provider_agreement"
    )

    ml = r.get(
        "moneyline_provider_agreement"
    )

    agreement_count = sum(
        x in {
            "AGREE",
            "CLOSE",
        }
        for x in [
            spread,
            total,
            ml,
        ]
    )

    if (
        pd.notna(sw_books)
        and sw_books >= 5
        and rd_ok
        and agreement_count >= 2
    ):
        return "HIGH"

    if (
        pd.notna(sw_books)
        and sw_books >= 3
        and agreement_count >= 2
    ):
        return "GOOD"

    if (
        pd.notna(sw_books)
        and sw_books >= 2
    ):
        return "LIMITED"

    return "INSUFFICIENT"


board[
    "market_data_quality"
] = board.apply(
    quality,
    axis=1,
)


board[
    "independent_context_source"
] = (
    context_source
    if context_source
    else "NONE"
)


# ==================================================
# SAVE
# ==================================================

board = board.sort_values(
    "start"
)

board.to_csv(
    OUT
    / "NFL_GAME_BETTING_RESEARCH.csv",
    index=False,
)

board.to_parquet(
    OUT
    / "NFL_GAME_BETTING_RESEARCH.parquet",
    index=False,
)


provider_matrix = board[
    [
        c
        for c in [
            "game_key",
            "start",
            "away_team",
            "home_team",
            "sportsbooks",
            "books_list",
            "sw_unique_books",
            "sw_books",
            "therundown_event_id",
            "spread_provider_agreement",
            "total_provider_agreement",
            "moneyline_provider_agreement",
            "market_data_quality",
        ]
        if c in board.columns
    ]
].copy()

provider_matrix.to_csv(
    OUT
    / "NFL_GAME_PROVIDER_MATRIX.csv",
    index=False,
)


receipt = {
    "generated_at":
        NOW.isoformat(),

    "games":
        len(board),

    "propline_games":
        len(pl),

    "sportwizzard_core_rows":
        len(sw),

    "sportwizzard_books":
        sorted(
            sw[
                "sportsbook"
            ]
            .dropna()
            .unique()
            .tolist()
        ),

    "therundown_games":
        len(rd),

    "therundown_receipts":
        rd_receipts,

    "independent_context_source":
        context_source,

    "quality_counts":
        board[
            "market_data_quality"
        ]
        .value_counts()
        .to_dict(),

    "rule":
        (
            "This is a market/context "
            "research board, not a "
            "bet recommendation board."
        ),
}

(
    OUT
    / "NFL_GAME_BETTING_FUSION_RECEIPT.json"
).write_text(
    json.dumps(
        receipt,
        indent=2,
        default=str,
    )
)


# ==================================================
# ACCEPTANCE REPORT
# ==================================================

print()
print("==================================================")
print("BUILD 17 — NFL GAME BETTING FUSION")
print("==================================================")

print(
    "Games:",
    len(board),
)

print(
    "SportWizzard core rows:",
    len(sw),
)

print(
    "SportWizzard books:",
    sw[
        "sportsbook"
    ].nunique(),
)

print(
    "TheRundown games:",
    len(rd),
)

print(
    "Independent context:",
    context_source,
)

print()
print("MARKET DATA QUALITY:")

print(
    board[
        "market_data_quality"
    ]
    .value_counts()
    .to_string()
)


print()
print("=== CURRENT NFL MARKET BOARD ===")

show = [
    "game_key",
    "start",
    "away_moneyline",
    "home_moneyline",
    "sw_away_ml",
    "sw_home_ml",
    "away_spread",
    "home_spread",
    "sw_home_spread",
    "total",
    "sw_total",
    "home_spread_move",
    "total_move",
    "spread_provider_agreement",
    "total_provider_agreement",
    "moneyline_provider_agreement",
    "market_data_quality",
]

show = [
    c
    for c in show
    if c in board.columns
]

print(
    board[
        show
    ]
    .to_string(
        index=False
    )
)


print()
print("=== SPORTWIZZARD BOOK RECEIPTS ===")

for book, info in (
    book_receipts.items()
):
    print(
        book,
        "raw=",
        info[
            "raw_rows"
        ],
        "accepted=",
        info[
            "accepted_core_rows"
        ],
    )


print()
print("=== THERUNDOWN RECEIPTS ===")

for item in rd_receipts:
    print(item)


print()
print("IMPORTANT:")
print(
    "Market-data quality is NOT "
    "a betting confidence score."
)

print(
    "No BEST BET has been generated."
)

print(
    "No player prop has been promoted."
)

print(
    "No parlay generated."
)

print(
    "OddsPapi is reserved for "
    "Build 18 finalist verification."
)

print(
    "No production UI changed."
)
