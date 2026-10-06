#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import json
import math
import re
import unicodedata

import pandas as pd


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

CBB = ROOT / "cbb_live"

DERIVED = CBB / "derived"
HISTORY = CBB / "history"

MARKETS = CBB / "markets"
CURRENT = MARKETS / "current"
RECEIPTS = MARKETS / "receipts"


RAW_MARKET = (
    CURRENT
    / "CBB_GAME_MARKET.csv"
)

CURRENT_GAMES = (
    DERIVED
    / "CBB_GAMES_CURRENT.csv"
)

GAME_HISTORY = (
    HISTORY
    / "CBB_GAME_HISTORY.csv"
)

ELO = (
    DERIVED
    / "CBB_ELO_CURRENT.csv"
)

SRS = (
    DERIVED
    / "CBB_SRS_CURRENT.csv"
)

RANKINGS = (
    DERIVED
    / "CBB_RANKINGS_CURRENT.csv"
)


NORMALIZED_OUT = (
    CURRENT
    / "CBB_GAME_MARKET_NORMALIZED.csv"
)

FUSION_OUT = (
    CURRENT
    / "CBB_GAME_MARKET_FUSION.csv"
)

RECEIPT_OUT = (
    RECEIPTS
    / "CBB_FUSION_RECEIPT_LATEST.json"
)


ET = ZoneInfo(
    "America/New_York"
)


def read_csv(
    path,
):

    if (
        not path.exists()
        or path.stat().st_size <= 1
    ):

        return pd.DataFrame()

    try:

        return pd.read_csv(
            path,
            low_memory=False,
        )

    except Exception:

        return pd.DataFrame()


def ascii_text(
    value,
):

    return (
        unicodedata
        .normalize(
            "NFKD",
            str(
                value or ""
            ),
        )
        .encode(
            "ascii",
            "ignore",
        )
        .decode()
    )


def norm(
    value,
):

    return re.sub(
        r"[^a-z0-9]+",
        "",
        ascii_text(
            value
        ).lower(),
    )


def id_key(
    value,
):

    if value is None:
        return ""

    try:

        x = float(
            value
        )

        if math.isnan(
            x
        ):
            return ""

        if x.is_integer():

            return str(
                int(
                    x
                )
            )

    except Exception:
        pass


    return str(
        value
    ).strip()


def number(
    value,
):

    try:

        x = float(
            value
        )

        if math.isnan(
            x
        ):
            return None

        return x

    except Exception:

        return None


def pipe_unique(
    values,
):

    return "|".join(
        sorted(
            {
                str(
                    x
                ).strip()

                for x in values
                if str(
                    x
                ).strip()
                and str(
                    x
                ).lower()
                != "nan"
            }
        )
    )


# ============================================================
# BUILD SAFE TEAM IDENTITY CATALOG
# ============================================================

current_games = read_csv(
    CURRENT_GAMES
)

history_games = read_csv(
    GAME_HISTORY
)


catalog_rows = []


for frame in [
    current_games,
    history_games,
]:

    if frame.empty:
        continue


    for prefix in [
        "away",
        "home",
    ]:

        needed = [
            f"{prefix}_team_id",
            f"{prefix}_team",
            f"{prefix}_team_name",
        ]


        if not all(
            col in frame.columns
            for col in needed
        ):

            continue


        for _, row in frame[
            needed
        ].iterrows():

            team_id = id_key(
                row[
                    f"{prefix}_team_id"
                ]
            )

            abbr = str(
                row[
                    f"{prefix}_team"
                ]
                or ""
            ).strip()

            name = str(
                row[
                    f"{prefix}_team_name"
                ]
                or ""
            ).strip()


            if not team_id:
                continue


            catalog_rows.append({
                "team_id":
                    team_id,

                "team":
                    abbr,

                "team_name":
                    name,
            })


catalog = pd.DataFrame(
    catalog_rows
)


if not catalog.empty:

    catalog = catalog.drop_duplicates(
        [
            "team_id",
            "team",
            "team_name",
        ]
    )


aliases = {}


def add_alias(
    alias,
    record,
):

    key = norm(
        alias
    )


    if not key:
        return


    aliases.setdefault(
        key,
        {},
    )


    aliases[
        key
    ][
        record[
            "team_id"
        ]
    ] = record


for _, row in catalog.iterrows():

    record = row.to_dict()


    add_alias(
        row.get(
            "team"
        ),
        record,
    )

    add_alias(
        row.get(
            "team_name"
        ),
        record,
    )


def resolve_team(
    value,
):

    key = norm(
        value
    )


    matches = aliases.get(
        key,
        {},
    )


    if len(
        matches
    ) == 1:

        return list(
            matches.values()
        )[
            0
        ]


    return None


# ============================================================
# CURRENT SCHEDULE INDEX
# ============================================================

schedule = {}


if not current_games.empty:

    for _, row in current_games.iterrows():

        away_id = id_key(
            row.get(
                "away_team_id"
            )
        )

        home_id = id_key(
            row.get(
                "home_team_id"
            )
        )

        game_date = str(
            row.get(
                "game_date"
            )
            or ""
        )


        if (
            away_id
            and home_id
            and game_date
        ):

            schedule[
                (
                    game_date,
                    away_id,
                    home_id,
                )
            ] = row.to_dict()


# ============================================================
# RATINGS
# ============================================================

elo = read_csv(
    ELO
)

srs = read_csv(
    SRS
)

rankings = read_csv(
    RANKINGS
)


elo_map = {}


if not elo.empty:

    for _, row in elo.iterrows():

        elo_map[
            id_key(
                row.get(
                    "team_id"
                )
            )
        ] = number(
            row.get(
                "elo"
            )
        )


srs_map = {}


if not srs.empty:

    for _, row in srs.iterrows():

        srs_map[
            id_key(
                row.get(
                    "team_id"
                )
            )
        ] = number(
            row.get(
                "srs"
            )
        )


current_rank_map = {}
prior_rank_map = {}


if not rankings.empty:

    ap = rankings[
        rankings[
            "poll"
        ]
        .astype(
            str
        )
        .str.contains(
            "AP",
            case=False,
            na=False,
        )
    ].copy()


    for _, row in ap.iterrows():

        team_id = id_key(
            row.get(
                "team_id"
            )
        )

        rank = number(
            row.get(
                "rank"
            )
        )


        if not team_id:
            continue


        if str(
            row.get(
                "current_season_match"
            )
        ).lower() in {
            "true",
            "1",
        }:

            current_rank_map[
                team_id
            ] = rank

        else:

            prior_rank_map[
                team_id
            ] = rank


ranking_freshness = (
    "CURRENT_SEASON"
    if current_rank_map
    else "PRIOR_SEASON_ONLY"
)


# ============================================================
# NORMALIZE MARKETS
# ============================================================

raw = read_csv(
    RAW_MARKET
)


NORMAL_COLUMNS = [
    "provider",
    "sportsbook",
    "event_id",
    "start_dt",
    "game_date",
    "away_team_raw",
    "home_team_raw",
    "away_team_id",
    "away_team",
    "away_team_name",
    "home_team_id",
    "home_team",
    "home_team_name",
    "market_canonical",
    "selection_canonical",
    "selection_team_id",
    "line",
    "price_american",
    "schedule_match",
    "schedule_event_id",
    "identity_status",
]


normal_rows = []


market_map = {
    "MONEYLINE":
        "MONEYLINE",

    "H2H":
        "MONEYLINE",

    "SPREAD":
        "SPREAD",

    "SPREADS":
        "SPREAD",

    "TOTAL":
        "TOTAL",

    "TOTALS":
        "TOTAL",
}


for _, row in raw.iterrows():

    away = resolve_team(
        row.get(
            "away_team"
        )
    )

    home = resolve_team(
        row.get(
            "home_team"
        )
    )


    start = pd.to_datetime(
        row.get(
            "start"
        ),
        utc=True,
        errors="coerce",
        format="mixed",
    )


    game_date = (
        start
        .tz_convert(
            ET
        )
        .date()
        .isoformat()
        if pd.notna(
            start
        )
        else ""
    )


    raw_market = str(
        row.get(
            "market"
        )
        or ""
    ).upper()


    market = market_map.get(
        raw_market
    )


    if not market:
        continue


    away_id = (
        away[
            "team_id"
        ]
        if away
        else ""
    )

    home_id = (
        home[
            "team_id"
        ]
        if home
        else ""
    )


    schedule_row = schedule.get(
        (
            game_date,
            away_id,
            home_id,
        )
    )


    side = str(
        row.get(
            "side"
        )
        or ""
    ).upper()


    raw_selection = row.get(
        "selection"
    )


    selection_team = None
    selection_canonical = ""
    selection_team_id = ""


    if market == "TOTAL":

        blob = str(
            raw_selection
            or side
        ).upper()


        if (
            side == "OVER"
            or "OVER" in blob
        ):

            selection_canonical = (
                "OVER"
            )


        elif (
            side == "UNDER"
            or "UNDER" in blob
        ):

            selection_canonical = (
                "UNDER"
            )


    else:

        selection_team = resolve_team(
            raw_selection
        )


        if selection_team:

            selection_team_id = (
                selection_team[
                    "team_id"
                ]
            )

            selection_canonical = (
                selection_team[
                    "team"
                ]
            )


        elif (
            side == "AWAY"
            and away
        ):

            selection_team_id = (
                away[
                    "team_id"
                ]
            )

            selection_canonical = (
                away[
                    "team"
                ]
            )


        elif (
            side == "HOME"
            and home
        ):

            selection_team_id = (
                home[
                    "team_id"
                ]
            )

            selection_canonical = (
                home[
                    "team"
                ]
            )


    identity_status = (
        "VERIFIED"
        if (
            away
            and home
            and selection_canonical
        )
        else "UNRESOLVED"
    )


    normal_rows.append({
        "provider":
            row.get(
                "provider"
            ),

        "sportsbook":
            row.get(
                "sportsbook"
            ),

        "event_id":
            row.get(
                "event_id"
            ),

        "start_dt":
            start,

        "game_date":
            game_date,

        "away_team_raw":
            row.get(
                "away_team"
            ),

        "home_team_raw":
            row.get(
                "home_team"
            ),

        "away_team_id":
            away_id,

        "away_team":
            (
                away[
                    "team"
                ]
                if away
                else ""
            ),

        "away_team_name":
            (
                away[
                    "team_name"
                ]
                if away
                else ""
            ),

        "home_team_id":
            home_id,

        "home_team":
            (
                home[
                    "team"
                ]
                if home
                else ""
            ),

        "home_team_name":
            (
                home[
                    "team_name"
                ]
                if home
                else ""
            ),

        "market_canonical":
            market,

        "selection_canonical":
            selection_canonical,

        "selection_team_id":
            selection_team_id,

        "line":
            number(
                row.get(
                    "line"
                )
            ),

        "price_american":
            number(
                row.get(
                    "price_american"
                )
            ),

        "schedule_match":
            bool(
                schedule_row
            ),

        "schedule_event_id":
            (
                schedule_row.get(
                    "event_id"
                )
                if schedule_row
                else ""
            ),

        "identity_status":
            identity_status,
    })


normalized = pd.DataFrame(
    normal_rows
)


if normalized.empty:

    normalized = pd.DataFrame(
        columns=NORMAL_COLUMNS
    )


normalized.to_csv(
    NORMALIZED_OUT,
    index=False,
)


# ============================================================
# FUSION — ONLY EXACT CURRENT-SCHEDULE MATCHES
# ============================================================

matched = normalized[
    normalized[
        "identity_status"
    ].eq(
        "VERIFIED"
    )
    &
    normalized[
        "schedule_match"
    ].eq(
        True
    )
].copy()


FUSION_COLUMNS = [
    "game_key",
    "schedule_event_id",
    "start_dt",
    "game_date",
    "away_team_id",
    "away_team",
    "away_team_name",
    "home_team_id",
    "home_team",
    "home_team_name",
    "market_canonical",
    "selection_canonical",
    "selection_team_id",
    "line",
    "sportsbook_count",
    "provider_count",
    "sportsbooks",
    "providers",
    "median_price_american",
    "selected_elo",
    "opponent_elo",
    "elo_edge",
    "selected_srs",
    "opponent_srs",
    "srs_edge",
    "selected_current_ap_rank",
    "selected_prior_ap_rank",
    "ranking_freshness",
    "context_basis",
]


if matched.empty:

    fusion = pd.DataFrame(
        columns=FUSION_COLUMNS
    )

else:

    matched[
        "game_key"
    ] = (
        matched[
            "game_date"
        ].astype(
            str
        )
        + "|"
        + matched[
            "away_team_id"
        ].astype(
            str
        )
        + "|"
        + matched[
            "home_team_id"
        ].astype(
            str
        )
    )


    fusion = (
        matched.groupby(
            [
                "game_key",
                "schedule_event_id",
                "game_date",
                "away_team_id",
                "away_team",
                "away_team_name",
                "home_team_id",
                "home_team",
                "home_team_name",
                "market_canonical",
                "selection_canonical",
                "selection_team_id",
                "line",
            ],
            dropna=False,
        )
        .agg(
            start_dt=(
                "start_dt",
                "min",
            ),

            sportsbook_count=(
                "sportsbook",
                "nunique",
            ),

            provider_count=(
                "provider",
                "nunique",
            ),

            sportsbooks=(
                "sportsbook",
                pipe_unique,
            ),

            providers=(
                "provider",
                pipe_unique,
            ),

            median_price_american=(
                "price_american",
                "median",
            ),
        )
        .reset_index()
    )


    selected_elo = []
    opponent_elo = []
    elo_edge = []

    selected_srs = []
    opponent_srs = []
    srs_edge = []

    current_rank = []
    prior_rank = []


    for _, row in fusion.iterrows():

        selected = str(
            row.get(
                "selection_team_id"
            )
            or ""
        )

        away = str(
            row.get(
                "away_team_id"
            )
            or ""
        )

        home = str(
            row.get(
                "home_team_id"
            )
            or ""
        )


        if selected == away:

            opponent = home

        elif selected == home:

            opponent = away

        else:

            opponent = ""


        se = elo_map.get(
            selected
        )

        oe = elo_map.get(
            opponent
        )

        ss = srs_map.get(
            selected
        )

        os = srs_map.get(
            opponent
        )


        selected_elo.append(
            se
        )

        opponent_elo.append(
            oe
        )

        elo_edge.append(
            (
                se - oe
            )
            if (
                se is not None
                and oe is not None
            )
            else None
        )


        selected_srs.append(
            ss
        )

        opponent_srs.append(
            os
        )

        srs_edge.append(
            (
                ss - os
            )
            if (
                ss is not None
                and os is not None
            )
            else None
        )


        current_rank.append(
            current_rank_map.get(
                selected
            )
        )

        prior_rank.append(
            prior_rank_map.get(
                selected
            )
        )


    fusion[
        "selected_elo"
    ] = selected_elo

    fusion[
        "opponent_elo"
    ] = opponent_elo

    fusion[
        "elo_edge"
    ] = elo_edge

    fusion[
        "selected_srs"
    ] = selected_srs

    fusion[
        "opponent_srs"
    ] = opponent_srs

    fusion[
        "srs_edge"
    ] = srs_edge

    fusion[
        "selected_current_ap_rank"
    ] = current_rank

    fusion[
        "selected_prior_ap_rank"
    ] = prior_rank

    fusion[
        "ranking_freshness"
    ] = ranking_freshness

    fusion[
        "context_basis"
    ] = (
        "PRIOR_SEASON_2025_26_BASELINE"
    )


fusion.to_csv(
    FUSION_OUT,
    index=False,
)


receipt = {
    "generated_at":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "team_catalog_rows":
        int(
            len(
                catalog
            )
        ),

    "raw_market_rows":
        int(
            len(
                raw
            )
        ),

    "normalized_market_rows":
        int(
            len(
                normalized
            )
        ),

    "identity_verified_rows":
        int(
            normalized[
                "identity_status"
            ]
            .eq(
                "VERIFIED"
            )
            .sum()
        )
        if not normalized.empty
        else 0,

    "schedule_matched_rows":
        int(
            normalized[
                "schedule_match"
            ]
            .eq(
                True
            )
            .sum()
        )
        if not normalized.empty
        else 0,

    "fusion_rows":
        int(
            len(
                fusion
            )
        ),

    "ranking_freshness":
        ranking_freshness,

    "prior_rankings_used_as_current_evidence":
        False,

    "market_is_probability":
        False,

    "college_player_props":
        False,

    "college_prizepicks":
        False,
}


RECEIPT_OUT.write_text(
    json.dumps(
        receipt,
        indent=2,
        sort_keys=True,
    )
)


print(
    "TEAM CATALOG ROWS:",
    receipt[
        "team_catalog_rows"
    ]
)

print(
    "RAW MARKET ROWS:",
    receipt[
        "raw_market_rows"
    ]
)

print(
    "NORMALIZED MARKET ROWS:",
    receipt[
        "normalized_market_rows"
    ]
)

print(
    "IDENTITY VERIFIED ROWS:",
    receipt[
        "identity_verified_rows"
    ]
)

print(
    "SCHEDULE MATCHED ROWS:",
    receipt[
        "schedule_matched_rows"
    ]
)

print(
    "FUSION ROWS:",
    receipt[
        "fusion_rows"
    ]
)

print(
    "RANKING FRESHNESS:",
    receipt[
        "ranking_freshness"
    ]
)

print()
print(
    "RESULT: CBB_MARKET_FUSION_READY"
)
