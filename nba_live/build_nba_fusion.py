#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime, timezone

import json
import math
import re

import numpy as np
import pandas as pd
import requests


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

NBA = ROOT / "nba_live"

CURRENT = (
    NBA
    / "markets"
    / "current"
)

DERIVED = (
    NBA
    / "derived"
)

HISTORY = (
    NBA
    / "history"
)

RECEIPTS = (
    NBA
    / "markets"
    / "receipts"
)


GAME_RAW = (
    CURRENT
    / "NBA_GAME_MARKET.csv"
)

PROP_RAW = (
    CURRENT
    / "NBA_PLAYER_PROP_MARKET.csv"
)

PP_RAW = (
    CURRENT
    / "NBA_PRIZEPICKS_MARKET.csv"
)

PLAYER_HISTORY = (
    HISTORY
    / "NBA_PLAYER_GAME_HISTORY.csv"
)

INJURIES = (
    DERIVED
    / "NBA_INJURIES_CURRENT.csv"
)


ROSTERS = (
    DERIVED
    / "NBA_CURRENT_ROSTERS.csv"
)

GAME_NORMALIZED = (
    CURRENT
    / "NBA_GAME_MARKET_NORMALIZED.csv"
)

GAME_FUSION = (
    CURRENT
    / "NBA_GAME_MARKET_FUSION.csv"
)

PROP_FUSION = (
    CURRENT
    / "NBA_PROP_FUSION.csv"
)

PP_FUSION = (
    CURRENT
    / "NBA_PRIZEPICKS_FUSION.csv"
)

FUSION_RECEIPT = (
    RECEIPTS
    / "NBA_FUSION_RECEIPT_LATEST.json"
)


TEAM_MAP = {
    "ATLANTAHAWKS": "ATL",
    "HAWKS": "ATL",
    "ATL": "ATL",

    "BOSTONCELTICS": "BOS",
    "CELTICS": "BOS",
    "BOS": "BOS",

    "BROOKLYNNETS": "BKN",
    "NETS": "BKN",
    "BKN": "BKN",

    "CHARLOTTEHORNETS": "CHA",
    "HORNETS": "CHA",
    "CHA": "CHA",

    "CHICAGOBULLS": "CHI",
    "BULLS": "CHI",
    "CHI": "CHI",

    "CLEVELANDCAVALIERS": "CLE",
    "CAVALIERS": "CLE",
    "CAVS": "CLE",
    "CLE": "CLE",

    "DALLASMAVERICKS": "DAL",
    "MAVERICKS": "DAL",
    "MAVS": "DAL",
    "DAL": "DAL",

    "DENVERNUGGETS": "DEN",
    "NUGGETS": "DEN",
    "DEN": "DEN",

    "DETROITPISTONS": "DET",
    "PISTONS": "DET",
    "DET": "DET",

    "GOLDENSTATEWARRIORS": "GSW",
    "WARRIORS": "GSW",
    "GS": "GSW",
    "GSW": "GSW",

    "HOUSTONROCKETS": "HOU",
    "ROCKETS": "HOU",
    "HOU": "HOU",

    "INDIANAPACERS": "IND",
    "PACERS": "IND",
    "IND": "IND",

    "LACLIPPERS": "LAC",
    "CLIPPERS": "LAC",
    "LOSANGELESCLIPPERS": "LAC",
    "LAC": "LAC",

    "LOSANGELESLAKERS": "LAL",
    "LAKERS": "LAL",
    "LAL": "LAL",

    "MEMPHISGRIZZLIES": "MEM",
    "GRIZZLIES": "MEM",
    "MEM": "MEM",

    "MIAMIHEAT": "MIA",
    "HEAT": "MIA",
    "MIA": "MIA",

    "MILWAUKEEBUCKS": "MIL",
    "BUCKS": "MIL",
    "MIL": "MIL",

    "MINNESOTATIMBERWOLVES": "MIN",
    "TIMBERWOLVES": "MIN",
    "WOLVES": "MIN",
    "MIN": "MIN",

    "NEWORLEANSPELICANS": "NOP",
    "PELICANS": "NOP",
    "NO": "NOP",
    "NOP": "NOP",

    "NEWYORKKNICKS": "NYK",
    "KNICKS": "NYK",
    "NY": "NYK",
    "NYK": "NYK",

    "OKLAHOMACITYTHUNDER": "OKC",
    "THUNDER": "OKC",
    "OKC": "OKC",

    "ORLANDOMAGIC": "ORL",
    "MAGIC": "ORL",
    "ORL": "ORL",

    "PHILADELPHIA76ERS": "PHI",
    "76ERS": "PHI",
    "SIXERS": "PHI",
    "PHI": "PHI",

    "PHOENIXSUNS": "PHX",
    "SUNS": "PHX",
    "PHX": "PHX",

    "PORTLANDTRAILBLAZERS": "POR",
    "TRAILBLAZERS": "POR",
    "BLAZERS": "POR",
    "POR": "POR",

    "SACRAMENTOKINGS": "SAC",
    "KINGS": "SAC",
    "SAC": "SAC",

    "SANANTONIOSPURS": "SAS",
    "SPURS": "SAS",
    "SA": "SAS",
    "SAS": "SAS",

    "TORONTORAPTORS": "TOR",
    "RAPTORS": "TOR",
    "TOR": "TOR",

    "UTAHJAZZ": "UTA",
    "JAZZ": "UTA",
    "UTAH": "UTA",
    "UTA": "UTA",

    "WASHINGTONWIZARDS": "WAS",
    "WIZARDS": "WAS",
    "WSH": "WAS",
    "WAS": "WAS",
}


ESPN_TEAM_SLUGS = [
    "atl",
    "bos",
    "bkn",
    "cha",
    "chi",
    "cle",
    "dal",
    "den",
    "det",
    "gs",
    "hou",
    "ind",
    "lac",
    "lal",
    "mem",
    "mia",
    "mil",
    "min",
    "no",
    "ny",
    "okc",
    "orl",
    "phi",
    "phx",
    "por",
    "sac",
    "sa",
    "tor",
    "utah",
    "wsh",
]


MARKET_STAT = {
    "PLAYER_TOTAL_POINTS":
        "points",

    "PLAYER_TOTAL_REBOUNDS":
        "rebounds",

    "PLAYER_TOTAL_ASSISTS":
        "assists",

    "PLAYER_TOTAL_THREES":
        "three_made",

    "PLAYER_TOTAL_POINTS_+_REBOUNDS":
        "points_rebounds",

    "PLAYER_TOTAL_POINTS_+_ASSISTS":
        "points_assists",

    "PLAYER_TOTAL_REBOUNDS_+_ASSISTS":
        "rebounds_assists",

    "PLAYER_TOTAL_POINTS_+_REBOUNDS_+_ASSISTS":
        "pra",
}


HEADERS = {
    "User-Agent":
        "Mozilla/5.0 "
        "(Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/154.0 Safari/537.36",
}


def compact(
    value,
):

    return re.sub(
        r"[^A-Z0-9]+",
        "",
        str(
            value or ""
        ).upper(),
    )


def team_key(
    value,
):

    value = compact(
        value
    )

    return TEAM_MAP.get(
        value,
        value,
    )


def player_key(
    value,
):

    return re.sub(
        r"[^a-z0-9]+",
        "",
        str(
            value or ""
        ).lower(),
    )


def player_parts(
    value,
):

    raw = re.sub(
        r"[^A-Za-z0-9 -]+",
        "",
        str(
            value or ""
        ),
    ).strip()

    parts = [
        p
        for p in raw.split()
        if p
    ]

    if not parts:
        return (
            "",
            "",
        )

    first = (
        parts[0][0].lower()
        if parts[0]
        else ""
    )

    last = re.sub(
        r"[^a-z0-9]+",
        "",
        parts[-1].lower(),
    )

    return (
        first,
        last,
    )


def numeric(
    value,
):

    try:

        value = float(
            value
        )

        if math.isnan(
            value
        ):
            return None

        return value

    except Exception:

        return None


def read_csv(
    path,
):

    if (
        not path.exists()
        or path.stat().st_size <= 1
    ):

        return pd.DataFrame()

    return pd.read_csv(
        path,
        low_memory=False,
    )


# ============================================================
# CURRENT ROSTERS
# ============================================================

def collect_rosters():

    rows = []

    for slug in ESPN_TEAM_SLUGS:

        url = (
            "https://site.api.espn.com/"
            "apis/site/v2/sports/basketball/"
            "nba/teams/"
            + slug
            + "/roster"
        )

        try:

            r = requests.get(
                url,
                headers=HEADERS,
                timeout=20,
            )

            if r.status_code != 200:

                print(
                    "ROSTER WARNING:",
                    slug,
                    r.status_code,
                )

                continue

            payload = r.json()

        except Exception as exc:

            print(
                "ROSTER ERROR:",
                slug,
                type(
                    exc
                ).__name__,
            )

            continue


        team = (
            payload.get(
                "team"
            )
            or {}
        )

        abbreviation = team_key(
            team.get(
                "abbreviation"
            )
            or slug
        )


        for athlete in (
            payload.get(
                "athletes"
            )
            or []
        ):

            name = (
                athlete.get(
                    "displayName"
                )
                or athlete.get(
                    "fullName"
                )
                or ""
            )

            rows.append({
                "player_id":
                    athlete.get(
                        "id"
                    ),

                "player":
                    name,

                "player_key":
                    player_key(
                        name
                    ),

                "team":
                    abbreviation,

                "position":
                    (
                        athlete.get(
                            "position"
                        )
                        or {}
                    ).get(
                        "abbreviation"
                    ),

                "jersey":
                    athlete.get(
                        "jersey"
                    ),

                "status":
                    (
                        athlete.get(
                            "status"
                        )
                        or {}
                    ).get(
                        "name"
                    ),
            })


    roster = pd.DataFrame(
        rows
    )

    if not roster.empty:

        roster = roster.drop_duplicates(
            [
                "player_key",
                "team",
            ],
            keep="last",
        )

    roster.to_csv(
        ROSTERS,
        index=False,
    )

    return roster


# ============================================================
# REBUILD SPORTWIZZARD EVENT IDENTITY FROM ITS ODDS
# ============================================================

def normalize_game_markets(
    games,
):

    if games.empty:

        return (
            pd.DataFrame(),
            {},
        )


    x = games.copy()

    x[
        "start_dt"
    ] = pd.to_datetime(
        x[
            "start"
        ],
        utc=True,
        errors="coerce",
        format="mixed",
    )


    # SportWizzard odds themselves contain HOME/AWAY
    # team selections even when /events returns nothing.
    sw = x[
        x[
            "provider"
        ].eq(
            "sportwizzard"
        )
    ].copy()


    event_map = {}


    for event_id, group in sw.groupby(
        "event_id",
        dropna=False,
    ):

        away = ""
        home = ""


        away_rows = group[
            group[
                "side"
            ]
            .astype(str)
            .str.upper()
            .eq(
                "AWAY"
            )
        ]


        home_rows = group[
            group[
                "side"
            ]
            .astype(str)
            .str.upper()
            .eq(
                "HOME"
            )
        ]


        if not away_rows.empty:

            away = team_key(
                away_rows.iloc[
                    0
                ].get(
                    "selection"
                )
            )


        if not home_rows.empty:

            home = team_key(
                home_rows.iloc[
                    0
                ].get(
                    "selection"
                )
            )


        start = group[
            "start_dt"
        ].dropna()


        event_map[
            str(
                event_id
            )
        ] = {
            "away_team":
                away,

            "home_team":
                home,

            "start":
                (
                    start.iloc[
                        0
                    ]
                    if len(
                        start
                    )
                    else pd.NaT
                ),
        }


    def get_team(
        row,
        side,
    ):

        provider = str(
            row.get(
                "provider",
                ""
            )
        )


        if provider == "sportwizzard":

            ev = event_map.get(
                str(
                    row.get(
                        "event_id"
                    )
                ),
                {},
            )

            return ev.get(
                side
                + "_team",
                "",
            )


        return team_key(
            row.get(
                side
                + "_team"
            )
        )


    x[
        "away_team_canonical"
    ] = x.apply(
        lambda row:
            get_team(
                row,
                "away",
            ),
        axis=1,
    )


    x[
        "home_team_canonical"
    ] = x.apply(
        lambda row:
            get_team(
                row,
                "home",
            ),
        axis=1,
    )


    def canonical_market(
        value,
    ):

        value = str(
            value or ""
        ).upper()

        if value in {
            "H2H",
            "MONEYLINE",
        }:
            return "MONEYLINE"

        if value in {
            "SPREAD",
            "SPREADS",
        }:
            return "SPREAD"

        if value in {
            "TOTAL",
            "TOTALS",
        }:
            return "TOTAL"

        return value


    x[
        "market_canonical"
    ] = x[
        "market"
    ].map(
        canonical_market
    )


    def selection_value(
        row,
    ):

        market = row[
            "market_canonical"
        ]

        selection = row.get(
            "selection"
        )

        side = str(
            row.get(
                "side",
                ""
            )
        ).upper()


        if market in {
            "MONEYLINE",
            "SPREAD",
        }:

            if side == "HOME":

                return row[
                    "home_team_canonical"
                ]

            if side == "AWAY":

                return row[
                    "away_team_canonical"
                ]

            return team_key(
                selection
            )


        if market == "TOTAL":

            value = str(
                selection
                or side
            ).upper()

            if "OVER" in value:
                return "OVER"

            if "UNDER" in value:
                return "UNDER"


        return str(
            selection or ""
        )


    x[
        "selection_canonical"
    ] = x.apply(
        selection_value,
        axis=1,
    )


    x[
        "game_key"
    ] = (
        x[
            "start_dt"
        ]
        .dt.strftime(
            "%Y-%m-%d"
        )
        .fillna(
            ""
        )
        + "|"
        + x[
            "away_team_canonical"
        ].fillna(
            ""
        )
        + "|"
        + x[
            "home_team_canonical"
        ].fillna(
            ""
        )
    )


    now = pd.Timestamp.now(
        tz="UTC"
    )


    x = x[
        x[
            "start_dt"
        ].notna()
        &
        (
            x[
                "start_dt"
            ]
            >= (
                now
                - pd.Timedelta(
                    hours=1
                )
            )
        )
    ].copy()


    x = x.drop_duplicates(
        [
            "provider",
            "sportsbook",
            "game_key",
            "market_canonical",
            "selection_canonical",
            "line",
            "price_american",
        ],
        keep="last",
    )


    x.to_csv(
        GAME_NORMALIZED,
        index=False,
    )


    group = x.copy()

    group[
        "line_group"
    ] = (
        pd.to_numeric(
            group[
                "line"
            ],
            errors="coerce",
        )
        .astype(
            "Float64"
        )
        .astype(
            str
        )
    )


    fusion = (
        group
        .groupby(
            [
                "game_key",
                "start_dt",
                "away_team_canonical",
                "home_team_canonical",
                "market_canonical",
                "selection_canonical",
                "line_group",
            ],
            dropna=False,
        )
        .agg(
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
                lambda s:
                    "|".join(
                        sorted(
                            set(
                                str(v)
                                for v
                                in s.dropna()
                            )
                        )
                    ),
            ),

            providers=(
                "provider",
                lambda s:
                    "|".join(
                        sorted(
                            set(
                                str(v)
                                for v
                                in s.dropna()
                            )
                        )
                    ),
            ),

            median_price_american=(
                "price_american",
                lambda s:
                    pd.to_numeric(
                        s,
                        errors="coerce",
                    ).median(),
            ),
        )
        .reset_index()
    )


    fusion.to_csv(
        GAME_FUSION,
        index=False,
    )


    return (
        x,
        event_map,
    )


# ============================================================
# PLAYER HISTORY PREP
# ============================================================

def prepare_history():

    history = read_csv(
        PLAYER_HISTORY
    )

    if history.empty:
        return history


    history[
        "player_key"
    ] = history[
        "player"
    ].map(
        player_key
    )


    for col in [
        "points",
        "rebounds",
        "assists",
        "three_made",
        "minutes",
        "pra",
    ]:

        if col in history.columns:

            history[
                col
            ] = pd.to_numeric(
                history[
                    col
                ],
                errors="coerce",
            )


    history[
        "points_rebounds"
    ] = (
        history[
            "points"
        ]
        + history[
            "rebounds"
        ]
    )


    history[
        "points_assists"
    ] = (
        history[
            "points"
        ]
        + history[
            "assists"
        ]
    )


    history[
        "rebounds_assists"
    ] = (
        history[
            "rebounds"
        ]
        + history[
            "assists"
        ]
    )


    history[
        "start_dt"
    ] = pd.to_datetime(
        history[
            "start"
        ],
        utc=True,
        errors="coerce",
        format="mixed",
    )


    return history.sort_values(
        "start_dt"
    )


def injury_map():

    injuries = read_csv(
        INJURIES
    )

    result = {}


    if injuries.empty:
        return result


    for _, row in injuries.iterrows():

        key = player_key(
            row.get(
                "player"
            )
        )

        if not key:
            continue


        status = str(
            row.get(
                "status",
                ""
            )
        ).upper()


        fantasy = str(
            row.get(
                "fantasy_status",
                ""
            )
        ).upper()


        if (
            "OUT" in status
            or fantasy in {
                "OUT",
                "OFS",
            }
        ):

            gate = "BLOCK"

        elif (
            "DAY-TO-DAY" in status
            or fantasy in {
                "GTD",
                "DTD",
            }
        ):

            gate = "REVIEW"

        else:

            gate = "CLEAR"


        previous = result.get(
            key,
            {
                "gate":
                    "CLEAR",
            },
        )


        rank = {
            "CLEAR": 0,
            "REVIEW": 1,
            "BLOCK": 2,
        }


        if (
            rank[
                gate
            ]
            >= rank[
                previous[
                    "gate"
                ]
            ]
        ):

            result[
                key
            ] = {
                "gate":
                    gate,

                "status":
                    row.get(
                        "status",
                        "",
                    ),

                "fantasy_status":
                    row.get(
                        "fantasy_status",
                        "",
                    ),

                "injury_type":
                    row.get(
                        "injury_type",
                        "",
                    ),
            }


    return result


# ============================================================
# PROP CONTEXT
# ============================================================

def context_for_prop(
    row,
    player_history,
):

    key = row[
        "player_key"
    ]

    stat = row[
        "stat_type"
    ]

    line = numeric(
        row.get(
            "line"
        )
    )

    side = str(
        row.get(
            "side",
            ""
        )
    ).upper()


    result = {
        "sample_games":
            0,

        "meaningful_games":
            0,

        "stat_l3_avg":
            None,

        "stat_l5_avg":
            None,

        "stat_l10_avg":
            None,

        "stat_season_avg":
            None,

        "l3_hit_rate":
            None,

        "l5_hit_rate":
            None,

        "l10_hit_rate":
            None,

        "minutes_l5_avg":
            None,

        "context_direction":
            "NO_CONTEXT",

        "sample_gate":
            "LIMITED",
    }


    if (
        not key
        or stat
        not in player_history.columns
        or line is None
    ):

        return result


    h = player_history[
        player_history[
            "player_key"
        ].eq(
            key
        )
    ].copy()


    if h.empty:
        return result


    values = pd.to_numeric(
        h[
            stat
        ],
        errors="coerce",
    )


    valid = h[
        values.notna()
    ].copy()

    if valid.empty:
        return result


    values = pd.to_numeric(
        valid[
            stat
        ],
        errors="coerce",
    )


    result[
        "sample_games"
    ] = int(
        len(
            valid
        )
    )


    if "minutes" in valid.columns:

        mins = pd.to_numeric(
            valid[
                "minutes"
            ],
            errors="coerce",
        )

        result[
            "meaningful_games"
        ] = int(
            (
                mins >= 12
            ).sum()
        )

        result[
            "minutes_l5_avg"
        ] = (
            mins
            .tail(
                5
            )
            .mean()
        )


    for n in [
        3,
        5,
        10,
    ]:

        recent = values.tail(
            n
        )

        result[
            f"stat_l{n}_avg"
        ] = recent.mean()


        if side == "OVER":

            decisions = recent[
                recent != line
            ]

            result[
                f"l{n}_hit_rate"
            ] = (
                (
                    decisions
                    > line
                ).mean()
                if len(
                    decisions
                )
                else None
            )


        elif side == "UNDER":

            decisions = recent[
                recent != line
            ]

            result[
                f"l{n}_hit_rate"
            ] = (
                (
                    decisions
                    < line
                ).mean()
                if len(
                    decisions
                )
                else None
            )


    result[
        "stat_season_avg"
    ] = values.mean()


    if (
        result[
            "sample_games"
        ]
        >= 10
        and result[
            "meaningful_games"
        ]
        >= 5
    ):

        result[
            "sample_gate"
        ] = "QUALIFIED"


    l5 = result[
        "l5_hit_rate"
    ]

    l10 = result[
        "l10_hit_rate"
    ]


    if (
        l5 is not None
        and l10 is not None
    ):

        if (
            l5 >= 0.60
            and l10 >= 0.60
        ):

            result[
                "context_direction"
            ] = "SUPPORT"


        elif (
            l5 <= 0.40
            and l10 <= 0.40
        ):

            result[
                "context_direction"
            ] = "OPPOSE"


        else:

            result[
                "context_direction"
            ] = "MIXED"


    return result


# ============================================================
# PROP FUSION
# ============================================================

def build_prop_fusion(
    props,
    pp,
    event_map,
    roster,
    history,
):

    roster_lookup = {}
    roster_alias = {}


    if not roster.empty:

        for _, row in roster.iterrows():

            roster_lookup[
                row[
                    "player_key"
                ]
            ] = row[
                "team"
            ]


        alias_candidates = {}

        for _, row in roster.iterrows():

            first, last = player_parts(
                row.get(
                    "player"
                )
            )

            if (
                not first
                or not last
            ):
                continue

            alias = (
                first
                + last
            )

            alias_candidates.setdefault(
                alias,
                [],
            ).append(
                row[
                    "player_key"
                ]
            )


        for alias, keys in (
            alias_candidates.items()
        ):

            unique = sorted(
                set(
                    keys
                )
            )

            if len(
                unique
            ) == 1:

                roster_alias[
                    alias
                ] = unique[
                    0
                ]


    injuries = injury_map()


    def prepare(
        df,
        prizepicks=False,
    ):

        if df.empty:
            return df


        x = df.copy()


        x[
            "player_key_raw"
        ] = x[
            "player"
        ].map(
            player_key
        )


        def resolve_player_key(
            value,
        ):

            exact = player_key(
                value
            )

            if exact in roster_lookup:

                return exact


            first, last = player_parts(
                value
            )

            alias = (
                first
                + last
            )


            return roster_alias.get(
                alias,
                exact,
            )


        x[
            "player_key"
        ] = x[
            "player"
        ].map(
            resolve_player_key
        )


        x[
            "event_id"
        ] = x[
            "event_id"
        ].astype(
            str
        )


        x[
            "away_team"
        ] = x[
            "event_id"
        ].map(
            lambda eid:
                event_map.get(
                    eid,
                    {},
                ).get(
                    "away_team",
                    "",
                )
        )


        x[
            "home_team"
        ] = x[
            "event_id"
        ].map(
            lambda eid:
                event_map.get(
                    eid,
                    {},
                ).get(
                    "home_team",
                    "",
                )
        )


        x[
            "start_dt"
        ] = pd.to_datetime(
            x[
                "start"
            ],
            utc=True,
            errors="coerce",
            format="mixed",
        )


        x[
            "current_team"
        ] = x[
            "player_key"
        ].map(
            roster_lookup
        )


        x[
            "roster_match"
        ] = x[
            "current_team"
        ].notna()


        x[
            "matchup_identity"
        ] = x.apply(
            lambda row:
                (
                    "VERIFIED"
                    if (
                        pd.notna(
                            row.get(
                                "current_team"
                            )
                        )
                        and row.get(
                            "current_team"
                        )
                        in {
                            row.get(
                                "away_team"
                            ),
                            row.get(
                                "home_team"
                            ),
                        }
                    )
                    else "REVIEW"
                ),
            axis=1,
        )


        x[
            "stat_type"
        ] = x[
            "market_subtype"
        ].map(
            MARKET_STAT
        )


        x[
            "line"
        ] = pd.to_numeric(
            x[
                "line"
            ],
            errors="coerce",
        )


        x[
            "side"
        ] = (
            x[
                "side"
            ]
            .astype(
                str
            )
            .str.upper()
        )


        # Research-ready totals only.
        x = x[
            x[
                "stat_type"
            ].notna()
            &
            x[
                "line"
            ].notna()
            &
            x[
                "side"
            ].isin(
                [
                    "OVER",
                    "UNDER",
                ]
            )
        ].copy()


        x[
            "injury_gate"
        ] = x[
            "player_key"
        ].map(
            lambda key:
                injuries.get(
                    key,
                    {
                        "gate":
                            "CLEAR"
                    },
                )[
                    "gate"
                ]
        )


        x[
            "injury_status"
        ] = x[
            "player_key"
        ].map(
            lambda key:
                injuries.get(
                    key,
                    {},
                ).get(
                    "status",
                    "",
                )
        )


        return x


    prop = prepare(
        props
    )

    pickem = prepare(
        pp,
        prizepicks=True,
    )


    # --------------------------
    # Sportsbook consensus
    # --------------------------

    if prop.empty:

        prop_fusion = pd.DataFrame()

    else:

        grouped = (
            prop
            .groupby(
                [
                    "event_id",
                    "start_dt",
                    "away_team",
                    "home_team",
                    "player_key",
                    "player",
                    "current_team",
                    "market_subtype",
                    "stat_type",
                    "side",
                    "line",
                    "matchup_identity",
                    "injury_gate",
                    "injury_status",
                ],
                dropna=False,
            )
            .agg(
                book_count=(
                    "sportsbook",
                    "nunique",
                ),

                books=(
                    "sportsbook",
                    lambda s:
                        "|".join(
                            sorted(
                                set(
                                    str(v)
                                    for v
                                    in s.dropna()
                                )
                            )
                        ),
                ),

                median_price_american=(
                    "price_american",
                    lambda s:
                        pd.to_numeric(
                            s,
                            errors="coerce",
                        ).median(),
                ),
            )
            .reset_index()
        )


        contexts = []

        for _, row in (
            grouped.iterrows()
        ):

            contexts.append(
                context_for_prop(
                    row,
                    history,
                )
            )


        context_df = pd.DataFrame(
            contexts
        )


        prop_fusion = pd.concat(
            [
                grouped.reset_index(
                    drop=True
                ),
                context_df.reset_index(
                    drop=True
                ),
            ],
            axis=1,
        )


        prop_fusion[
            "research_status"
        ] = prop_fusion.apply(
            lambda row:
                (
                    "INJURY_BLOCK"
                    if row[
                        "injury_gate"
                    ] == "BLOCK"

                    else (
                        "IDENTITY_REVIEW"
                        if row[
                            "matchup_identity"
                        ] != "VERIFIED"

                        else (
                            "INJURY_REVIEW"
                            if row[
                                "injury_gate"
                            ] == "REVIEW"

                            else (
                                "QUALIFIED_CONTEXT"
                                if (
                                    row[
                                        "sample_gate"
                                    ]
                                    == "QUALIFIED"
                                    and row[
                                        "context_direction"
                                    ]
                                    == "SUPPORT"
                                )

                                else "WATCH"
                            )
                        )
                    )
                ),
            axis=1,
        )


    # --------------------------
    # PrizePicks context
    # --------------------------

    if pickem.empty:

        pickem_fusion = pd.DataFrame()

    else:

        rows = []

        for _, row in pickem.iterrows():

            base = row.to_dict()


            context = context_for_prop(
                base,
                history,
            )


            book_count = 0
            books = ""


            if not prop_fusion.empty:

                match = prop_fusion[
                    prop_fusion[
                        "player_key"
                    ].eq(
                        base[
                            "player_key"
                        ]
                    )
                    &
                    prop_fusion[
                        "market_subtype"
                    ].eq(
                        base[
                            "market_subtype"
                        ]
                    )
                    &
                    prop_fusion[
                        "side"
                    ].eq(
                        base[
                            "side"
                        ]
                    )
                    &
                    np.isclose(
                        pd.to_numeric(
                            prop_fusion[
                                "line"
                            ],
                            errors="coerce",
                        ),
                        base[
                            "line"
                        ],
                        equal_nan=False,
                    )
                ]


                if not match.empty:

                    best = match.sort_values(
                        "book_count",
                        ascending=False,
                    ).iloc[
                        0
                    ]

                    book_count = int(
                        best[
                            "book_count"
                        ]
                    )

                    books = best[
                        "books"
                    ]


            result = {
                **base,
                **context,

                "sportsbook_book_count":
                    book_count,

                "sportsbook_books":
                    books,
            }


            if result[
                "injury_gate"
            ] == "BLOCK":

                status = "INJURY_BLOCK"

            elif (
                result[
                    "matchup_identity"
                ]
                != "VERIFIED"
            ):

                status = "IDENTITY_REVIEW"

            elif (
                result[
                    "injury_gate"
                ]
                == "REVIEW"
            ):

                status = "INJURY_REVIEW"

            elif (
                result[
                    "sample_gate"
                ]
                == "QUALIFIED"
                and result[
                    "context_direction"
                ]
                == "SUPPORT"
                and book_count >= 1
            ):

                status = "QUALIFIED_CONTEXT"

            else:

                status = "WATCH"


            result[
                "research_status"
            ] = status


            rows.append(
                result
            )


        pickem_fusion = pd.DataFrame(
            rows
        )


    prop_fusion.to_csv(
        PROP_FUSION,
        index=False,
    )


    pickem_fusion.to_csv(
        PP_FUSION,
        index=False,
    )


    return (
        prop_fusion,
        pickem_fusion,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    games = read_csv(
        GAME_RAW
    )

    props = read_csv(
        PROP_RAW
    )

    pp = read_csv(
        PP_RAW
    )


    roster = collect_rosters()

    history = prepare_history()


    game_normalized, event_map = (
        normalize_game_markets(
            games
        )
    )


    prop_fusion, pp_fusion = (
        build_prop_fusion(
            props,
            pp,
            event_map,
            roster,
            history,
        )
    )


    game_fusion = read_csv(
        GAME_FUSION
    )


    def verified_rate(
        df,
    ):

        if (
            df.empty
            or "matchup_identity"
            not in df.columns
        ):
            return 0.0

        return float(
            (
                df[
                    "matchup_identity"
                ]
                == "VERIFIED"
            ).mean()
        )


    receipt = {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "current_roster_rows":
            int(
                len(
                    roster
                )
            ),

        "historical_player_rows":
            int(
                len(
                    history
                )
            ),

        "normalized_game_market_rows":
            int(
                len(
                    game_normalized
                )
            ),

        "game_fusion_rows":
            int(
                len(
                    game_fusion
                )
            ),

        "prop_fusion_rows":
            int(
                len(
                    prop_fusion
                )
            ),

        "prizepicks_fusion_rows":
            int(
                len(
                    pp_fusion
                )
            ),

        "prop_identity_verified_rate":
            verified_rate(
                prop_fusion
            ),

        "prizepicks_identity_verified_rate":
            verified_rate(
                pp_fusion
            ),

        "policy":
            (
                "MARKET_IS_EVIDENCE_"
                "NOT_PROBABILITY"
            ),

        "therundown_zero_rows_not_counted":
            True,

        "oddspapi_zero_rows_not_counted":
            True,
    }


    FUSION_RECEIPT.write_text(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
        )
    )


    print(
        "CURRENT ROSTER ROWS:",
        len(
            roster
        )
    )

    print(
        "HISTORICAL PLAYER ROWS:",
        len(
            history
        )
    )

    print(
        "NORMALIZED GAME MARKET ROWS:",
        len(
            game_normalized
        )
    )

    print(
        "GAME FUSION ROWS:",
        len(
            game_fusion
        )
    )

    print(
        "PROP FUSION ROWS:",
        len(
            prop_fusion
        )
    )

    print(
        "PRIZEPICKS FUSION ROWS:",
        len(
            pp_fusion
        )
    )


    if not prop_fusion.empty:

        print()
        print(
            "PROP RESEARCH STATUS:"
        )

        print(
            prop_fusion[
                "research_status"
            ]
            .value_counts()
            .to_dict()
        )


    if not pp_fusion.empty:

        print()
        print(
            "PRIZEPICKS RESEARCH STATUS:"
        )

        print(
            pp_fusion[
                "research_status"
            ]
            .value_counts()
            .to_dict()
        )


    print()
    print(
        "RESULT: NBA_FUSION_READY"
    )


if __name__ == "__main__":
    main()
