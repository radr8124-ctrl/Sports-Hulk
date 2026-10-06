from pathlib import Path
from datetime import datetime, timezone, timedelta
import json
import os
import re
import time

import numpy as np
import pandas as pd
import requests

try:
    from dotenv import load_dotenv
    load_dotenv(
        "/home/ubuntu/sports-hulk/.env"
    )
except Exception:
    pass


ROOT = Path("/home/ubuntu/sports-hulk")

DEC = ROOT / "nfl_live/decision"

RAW_STATS = (
    ROOT
    / "nfl_live/player_context/raw/"
      "player_stats.parquet"
)

SCHEDULE = (
    ROOT
    / "nfl_live/derived/"
      "NFLVERSE_2026_SCHEDULE.csv"
)

ALIAS = (
    ROOT
    / "nfl_live/identity/"
      "team_aliases.json"
)

NOW = datetime.now(timezone.utc)


# ==================================================
# HELPERS
# ==================================================

def clean(v):
    if v is None or pd.isna(v):
        return ""
    return str(v).strip()


def norm_name(v):

    x = clean(v).lower()

    x = re.sub(
        r"\b(jr|sr|ii|iii|iv)\b\.?",
        "",
        x,
    )

    return re.sub(
        r"[^a-z0-9]+",
        "",
        x,
    )


aliases = json.loads(
    ALIAS.read_text()
)

TEAM_MAP = {}


def team_token(v):
    return re.sub(
        r"[^a-z0-9]+",
        "",
        clean(v).lower(),
    )


for abbr, vals in aliases.items():

    TEAM_MAP[
        team_token(abbr)
    ] = abbr

    for v in vals:
        TEAM_MAP[
            team_token(v)
        ] = abbr


def team(v):

    k = team_token(v)

    if not k:
        return ""

    return TEAM_MAP.get(
        k,
        clean(v).upper(),
    )


def team_pair(a, b):

    return "|".join(
        sorted(
            [
                team(a),
                team(b),
            ]
        )
    )


def num(v):
    return pd.to_numeric(
        v,
        errors="coerce",
    )


# ==================================================
# COMPLETED REGULAR-SEASON GAME IDS
# ==================================================

schedule = pd.read_csv(
    SCHEDULE,
    low_memory=False,
)

schedule[
    "home_score_num"
] = pd.to_numeric(
    schedule.get(
        "home_score"
    ),
    errors="coerce",
)

schedule[
    "away_score_num"
] = pd.to_numeric(
    schedule.get(
        "away_score"
    ),
    errors="coerce",
)

completed = schedule[
    schedule[
        "home_score_num"
    ].notna()
    &
    schedule[
        "away_score_num"
    ].notna()
].copy()

completed_ids = set(
    completed[
        "game_id"
    ].astype(str)
)


# ==================================================
# PLAYER SAMPLE DATA
# ==================================================

stats = pd.read_parquet(
    RAW_STATS
)

name_col = (
    "player_display_name"
    if "player_display_name"
    in stats.columns
    else "player_name"
)

stats = stats[
    pd.to_numeric(
        stats["season"],
        errors="coerce",
    ).eq(2026)
].copy()

if "game_id" in stats.columns:

    stats = stats[
        stats[
            "game_id"
        ].astype(str)
        .isin(
            completed_ids
        )
    ].copy()


stats[
    "player_key"
] = stats[
    name_col
].map(
    norm_name
)


for c in [
    "attempts",
    "targets",
    "carries",
    "receptions",
    "passing_yards",
    "receiving_yards",
    "rushing_yards",
]:

    if c in stats.columns:
        stats[c] = pd.to_numeric(
            stats[c],
            errors="coerce",
        ).fillna(0)


# ==================================================
# MEANINGFUL SAMPLE COUNT BY MARKET
# ==================================================

def meaningful_games(
    player_key,
    market,
):

    p = stats[
        stats[
            "player_key"
        ].eq(
            player_key
        )
    ].copy()

    if p.empty:
        return 0

    market = clean(
        market
    ).upper()

    if any(
        x in market
        for x in [
            "PASS_YARDS",
            "PASS_ATTEMPTS",
            "PASS_COMPLETIONS",
            "PASS_TDS",
            "INTERCEPTIONS",
        ]
    ):

        if "attempts" not in p:
            return 0

        # Removes cameos / tiny partial games
        # from the evidence sample.
        return int(
            (
                p["attempts"]
                >= 10
            ).sum()
        )


    if any(
        x in market
        for x in [
            "REC_YARDS",
            "RECEPTIONS",
            "TARGETS",
            "LONGEST_RECEPTION",
        ]
    ):

        if "targets" not in p:
            return 0

        return int(
            (
                p["targets"]
                >= 2
            ).sum()
        )


    if any(
        x in market
        for x in [
            "RUSH_YARDS",
            "RUSH_ATTEMPTS",
            "LONGEST_RUSH",
        ]
    ):

        if "carries" not in p:
            return 0

        return int(
            (
                p["carries"]
                >= 3
            ).sum()
        )


    # Defensive / kicking / unusual props:
    # require two completed appearances.
    return int(
        p[
            "game_id"
        ].nunique()
        if "game_id" in p.columns
        else len(p)
    )


# ==================================================
# APPLY TO PROP DECISIONS
# ==================================================

props = pd.read_csv(
    DEC
    / "NFL_PROP_DECISIONS.csv",
    low_memory=False,
)

player_col = next(
    c for c in [
        "player_dfs",
        "player",
        "player_sportsbook",
    ]
    if c in props.columns
)

props[
    "player_key_sanity"
] = props[
    player_col
].map(
    norm_name
)


props[
    "meaningful_completed_games"
] = props.apply(
    lambda r:
        meaningful_games(
            r[
                "player_key_sanity"
            ],
            r.get(
                "market"
            ),
        ),
    axis=1,
)


props[
    "sample_gate"
] = np.where(
    props[
        "meaningful_completed_games"
    ] >= 2,
    "PASS",
    np.where(
        props[
            "meaningful_completed_games"
        ] == 1,
        "LIMITED_SAMPLE",
        "NO_MEANINGFUL_SAMPLE",
    ),
)


props[
    "decision_before_sample_gate"
] = props[
    "decision"
]


def apply_sample_gate(row):

    decision = clean(
        row.get(
            "decision"
        )
    )

    sample = clean(
        row.get(
            "sample_gate"
        )
    )

    # Injury / identity blocks always win.
    if decision in {
        "BLOCK_IDENTITY",
        "BLOCK_INJURY",
        "INJURY_REVIEW",
        "PASS",
    }:
        return decision

    if sample != "PASS":

        if decision in {
            "STRONG_RESEARCH",
            "QUALIFIED_RESEARCH",
        }:
            return "WATCH"

    return decision


props[
    "decision"
] = props.apply(
    apply_sample_gate,
    axis=1,
)


props.to_csv(
    DEC
    / "NFL_PROP_DECISIONS.csv",
    index=False,
)


finalists = props[
    props[
        "decision"
    ].isin(
        [
            "STRONG_RESEARCH",
            "QUALIFIED_RESEARCH",
        ]
    )
].copy()

finalists.to_csv(
    DEC
    / "NFL_PROP_FINALISTS.csv",
    index=False,
)


# ==================================================
# PRIZEPICKS GETS SAME SAMPLE GATE
# ==================================================

pp_path = (
    DEC
    / "NFL_PRIZEPICKS_DECISIONS.csv"
)

pp_final_count = 0

if pp_path.exists():

    pp = pd.read_csv(
        pp_path,
        low_memory=False,
    )

    pp[
        "player_key_sanity"
    ] = pp[
        "player"
    ].map(
        norm_name
    )

    pp[
        "meaningful_completed_games"
    ] = pp.apply(
        lambda r:
            meaningful_games(
                r[
                    "player_key_sanity"
                ],
                r.get(
                    "market_subtype"
                ),
            ),
        axis=1,
    )

    pp[
        "sample_gate"
    ] = np.where(
        pp[
            "meaningful_completed_games"
        ] >= 2,
        "PASS",
        np.where(
            pp[
                "meaningful_completed_games"
            ] == 1,
            "LIMITED_SAMPLE",
            "NO_MEANINGFUL_SAMPLE",
        ),
    )

    pp[
        "decision_before_sample_gate"
    ] = pp[
        "decision"
    ]

    pp[
        "decision"
    ] = pp.apply(
        apply_sample_gate,
        axis=1,
    )

    pp.to_csv(
        pp_path,
        index=False,
    )

    pp_final = pp[
        pp[
            "decision"
        ].isin(
            [
                "STRONG_RESEARCH",
                "QUALIFIED_RESEARCH",
            ]
        )
    ].copy()

    pp_final.to_csv(
        DEC
        / "NFL_PRIZEPICKS_FINALISTS.csv",
        index=False,
    )

    pp_final_count = len(
        pp_final
    )


# ==================================================
# ODDSPAPI FIXTURE MATCH CORRECTION
# ==================================================

print()
print(
    "=== ODDSPAPI TEAM-PAIR MATCH ==="
)

games_path = (
    DEC
    / "NFL_GAME_DECISIONS.csv"
)

games = pd.read_csv(
    games_path,
    low_memory=False,
)


games[
    "game_pair"
] = games[
    "game_key"
].apply(
    lambda x:
        team_pair(
            str(x).split(
                "@"
            )[0]
            if "@"
            in str(x)
            else "",
            str(x).split(
                "@"
            )[1]
            if "@"
            in str(x)
            else "",
        )
)


op_key = clean(
    os.getenv(
        "ODDSPAPI_API_KEY"
    )
)

checked = {}

if op_key:

    later = (
        NOW
        + timedelta(
            hours=48
        )
    )

    r = requests.get(
        "https://api.oddspapi.io/v4/fixtures",
        params={
            "apiKey":
                op_key,
            "sportId":
                14,
            "from":
                NOW.strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
            "to":
                later.strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
            "statusId":
                0,
            "hasOdds":
                "true",
            "language":
                "en",
        },
        timeout=30,
    )

    if r.status_code == 200:

        payload = r.json()

        fixtures = (
            payload
            if isinstance(
                payload,
                list,
            )
            else payload.get(
                "data",
                payload.get(
                    "fixtures",
                    [],
                ),
            )
        )

        fixture_map = {}

        for f in fixtures:

            pair = team_pair(
                f.get(
                    "participant1Name"
                ),
                f.get(
                    "participant2Name"
                ),
            )

            if pair:
                fixture_map[
                    pair
                ] = f.get(
                    "fixtureId"
                )


        top_pairs = (
            games.sort_values(
                "hulk_market_score",
                ascending=False,
            )[
                "game_pair"
            ]
            .dropna()
            .drop_duplicates()
            .head(5)
            .tolist()
        )


        for pair in top_pairs:

            fid = fixture_map.get(
                pair
            )

            if not fid:

                checked[pair] = {
                    "status":
                        "NO_FIXTURE_MATCH",
                    "bookmakers":
                        0,
                }

                continue

            time.sleep(1.05)

            ro = requests.get(
                "https://api.oddspapi.io/v4/odds",
                params={
                    "apiKey":
                        op_key,
                    "fixtureId":
                        fid,
                    "oddsFormat":
                        "american",
                    "language":
                        "en",
                    "verbosity":
                        2,
                },
                timeout=30,
            )

            if ro.status_code != 200:

                checked[pair] = {
                    "status":
                        "HTTP_ERROR",
                    "bookmakers":
                        0,
                }

                continue

            odds = ro.json()

            books = odds.get(
                "bookmakerOdds"
            )

            if isinstance(
                books,
                dict,
            ):
                count = len(
                    books
                )

            elif isinstance(
                books,
                list,
            ):
                count = len(
                    books
                )

            else:
                count = 0

            checked[pair] = {
                "status":
                    (
                        "LIVE_ODDS_PRESENT"
                        if count
                        else
                        "NO_BOOKMAKER_ODDS"
                    ),
                "bookmakers":
                    count,
            }


for pair, result in (
    checked.items()
):

    mask = games[
        "game_pair"
    ].eq(pair)

    games.loc[
        mask,
        "oddspapi_status",
    ] = result[
        "status"
    ]

    games.loc[
        mask,
        "oddspapi_bookmaker_count",
    ] = result[
        "bookmakers"
    ]


games.to_csv(
    games_path,
    index=False,
)


game_final = games[
    games[
        "decision"
    ].isin(
        [
            "QUALIFIED_RESEARCH",
            "MARKET_LEAN",
            "HIGH_JUICE_SAFETY",
        ]
    )
].copy()

game_final.to_csv(
    DEC
    / "NFL_GAME_FINALISTS.csv",
    index=False,
)


# ==================================================
# QA
# ==================================================

print()
print(
    "=== SAMPLE GATE COUNTS ==="
)

print(
    props[
        "sample_gate"
    ]
    .value_counts()
    .to_string()
)


print()
print(
    "=== FINAL PROP DECISIONS ==="
)

print(
    props[
        "decision"
    ]
    .value_counts()
    .to_string()
)


print()
print(
    "=== DOWNGRADED BY SAMPLE GATE ==="
)

downgraded = props[
    (
        props[
            "decision_before_sample_gate"
        ]
        .isin(
            [
                "STRONG_RESEARCH",
                "QUALIFIED_RESEARCH",
            ]
        )
    )
    &
    (
        props[
            "decision"
        ]
        .eq("WATCH")
    )
]

show = [
    player_col,
    "market",
    "side",
    "dfs_line",
    "meaningful_completed_games",
    "hulk_prop_score",
    "decision_before_sample_gate",
    "decision",
]

print(
    downgraded[
        [
            c for c in show
            if c in downgraded.columns
        ]
    ]
    .head(30)
    .to_string(
        index=False
    )
)


print()
print(
    "=== TOP FINAL PROPS ==="
)

final_show = [
    player_col,
    "market",
    "side",
    "dfs_line",
    "sportsbook_line",
    "book_count",
    "book_probability",
    "meaningful_completed_games",
    "recent_metric",
    "hulk_prop_score",
    "decision",
]

print(
    finalists[
        [
            c for c in final_show
            if c in finalists.columns
        ]
    ]
    .head(30)
    .to_string(
        index=False
    )
)


print()
print(
    "=== ODDSPAPI PAIR CHECK ==="
)

for pair, result in (
    checked.items()
):
    print(
        pair,
        "=>",
        result,
    )


receipt = {
    "generated_at":
        NOW.isoformat(),

    "prop_finalists_after_sample_gate":
        len(finalists),

    "prizepicks_finalists_after_sample_gate":
        pp_final_count,

    "sample_downgrades":
        len(downgraded),

    "oddspapi_pair_checks":
        checked,

    "rules": {
        "minimum_meaningful_games_for_promotion":
            2,

        "small_sample_can_be_watch":
            True,

        "small_sample_can_be_strong":
            False,
    },
}

(
    DEC
    / "NFL_DECISION_SANITY_RECEIPT.json"
).write_text(
    json.dumps(
        receipt,
        indent=2,
    )
)
