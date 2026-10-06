#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import json
import re
import sys
import unicodedata

import numpy as np
import pandas as pd
import requests


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prop_intelligence.market_pricing import consensus_for_exact_line

NHL = ROOT / "nhl_live"

DERIVED = NHL / "derived"
HISTORY = NHL / "history"

MARKETS = NHL / "markets"
CURRENT = MARKETS / "current"
RECEIPTS = MARKETS / "receipts"

NOW = pd.Timestamp.now(
    tz="UTC"
)

ET = ZoneInfo(
    "America/New_York"
)


ROSTERS = (
    DERIVED
    / "NHL_CURRENT_ROSTERS.csv"
)

PLAYER_HISTORY = (
    HISTORY
    / "NHL_PLAYER_GAME_HISTORY.csv"
)

GOALIE_HISTORY = (
    HISTORY
    / "NHL_GOALIE_GAME_HISTORY.csv"
)

RAW_GAMES = (
    CURRENT
    / "NHL_GAME_MARKET.csv"
)

RAW_PROPS = (
    CURRENT
    / "NHL_PLAYER_PROP_MARKET.csv"
)

RAW_PP = (
    CURRENT
    / "NHL_PRIZEPICKS_MARKET.csv"
)


INJURIES_OUT = (
    DERIVED
    / "NHL_INJURIES_CURRENT.csv"
)

GOALIES_OUT = (
    DERIVED
    / "NHL_GOALIE_LISTINGS_CURRENT.csv"
)

GAME_NORMALIZED_OUT = (
    CURRENT
    / "NHL_GAME_MARKET_NORMALIZED.csv"
)

GAME_FUSION_OUT = (
    CURRENT
    / "NHL_GAME_MARKET_FUSION.csv"
)

PROP_FUSION_OUT = (
    CURRENT
    / "NHL_PROP_FUSION.csv"
)

PP_FUSION_OUT = (
    CURRENT
    / "NHL_PRIZEPICKS_FUSION.csv"
)

FUSION_RECEIPT = (
    RECEIPTS
    / "NHL_FUSION_RECEIPT_LATEST.json"
)


TEAM_NAMES = {
    "anaheimducks": "ANA",
    "ana": "ANA",

    "bostonbruins": "BOS",
    "bos": "BOS",

    "buffalosabres": "BUF",
    "buf": "BUF",

    "calgaryflames": "CGY",
    "cgy": "CGY",

    "carolinahurricanes": "CAR",
    "car": "CAR",

    "chicagoblackhawks": "CHI",
    "chi": "CHI",

    "coloradoavalanche": "COL",
    "col": "COL",

    "columbusbluejackets": "CBJ",
    "cbj": "CBJ",

    "dallasstars": "DAL",
    "dal": "DAL",

    "detroitredwings": "DET",
    "det": "DET",

    "edmontonoilers": "EDM",
    "edm": "EDM",

    "floridapanthers": "FLA",
    "fla": "FLA",

    "losangeleskings": "LAK",
    "lak": "LAK",

    "minnesotawild": "MIN",
    "min": "MIN",

    "montrealcanadiens": "MTL",
    "mtl": "MTL",

    "nashvillepredators": "NSH",
    "nsh": "NSH",

    "newjerseydevils": "NJD",
    "njd": "NJD",

    "newyorkislanders": "NYI",
    "nyi": "NYI",

    "newyorkrangers": "NYR",
    "nyr": "NYR",

    "ottawasenators": "OTT",
    "ott": "OTT",

    "philadelphiaflyers": "PHI",
    "phi": "PHI",

    "pittsburghpenguins": "PIT",
    "pit": "PIT",

    "sanjosesharks": "SJS",
    "sjs": "SJS",

    "seattlekraken": "SEA",
    "sea": "SEA",

    "stlouisblues": "STL",
    "stl": "STL",

    "tampabaylightning": "TBL",
    "tbl": "TBL",

    "torontomapleleafs": "TOR",
    "tor": "TOR",

    "utahmammoth": "UTA",
    "utahhockeyclub": "UTA",
    "uta": "UTA",

    "vancouvercanucks": "VAN",
    "van": "VAN",

    "vegasgoldenknights": "VGK",
    "vgk": "VGK",

    "washingtoncapitals": "WSH",
    "wsh": "WSH",

    "winnipegjets": "WPG",
    "wpg": "WPG",
}


SPORTSBOOK_STAT_MAP = {
    "PLAYER_TOTAL_GOALS":
        (
            "goals",
            "SKATER",
        ),

    "PLAYER_TOTAL_ASSISTS":
        (
            "assists",
            "SKATER",
        ),

    "PLAYER_TOTAL_POINTS":
        (
            "points",
            "SKATER",
        ),

    "PLAYER_TOTAL_SHOTS":
        (
            "shots_on_goal",
            "SKATER",
        ),

    "PLAYER_TOTAL_SAVES":
        (
            "saves",
            "GOALIE",
        ),

    "PLAYER_TOTAL_GOALS_AGAINST":
        (
            "goals_against",
            "GOALIE",
        ),
}


PRIZEPICKS_STAT_MAP = {
    "PLAYER_TOTAL_POINTS":
        (
            "points",
            "SKATER",
        ),

    "PLAYER_TOTAL_ASSISTS":
        (
            "assists",
            "SKATER",
        ),

    "PLAYER_TOTAL_SHOTS":
        (
            "shots_on_goal",
            "SKATER",
        ),

    "PLAYER_TOTAL_HITS":
        (
            "hits",
            "SKATER",
        ),

    "PLAYER_TOTAL_BLOCKED_SHOTS":
        (
            "blocked_shots",
            "SKATER",
        ),

    "PLAYER_TOTAL_TIME_ON_ICE":
        (
            "toi_minutes",
            "SKATER",
        ),

    "PLAYER_TOTAL_SAVES":
        (
            "saves",
            "GOALIE",
        ),
}


def read_csv(
    path,
):

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

    value = str(
        value or ""
    )

    value = (
        value
        .split(
            "(",
            1,
        )[0]
        .strip()
    )

    return (
        unicodedata
        .normalize(
            "NFKD",
            value,
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


def name_alias(
    value,
):

    pieces = re.findall(
        r"[A-Za-z0-9]+",
        ascii_text(
            value
        ).lower(),
    )

    if not pieces:
        return ""

    return (
        pieces[
            0
        ][
            0
        ]
        + pieces[
            -1
        ]
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

        if np.isnan(
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

        if np.isnan(
            x
        ):
            return None

        return x

    except Exception:

        return None


def team_code(
    value,
):

    key = norm(
        value
    )

    return TEAM_NAMES.get(
        key,
        "",
    )


def pipe_unique(
    values,
):

    output = sorted(
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

    return "|".join(
        output
    )


# ============================================================
# CURRENT ROSTER IDENTITY
# ============================================================

roster = read_csv(
    ROSTERS
)

if roster.empty:

    raise SystemExit(
        "NHL current roster file missing."
    )


roster[
    "player_key"
] = roster[
    "player"
].map(
    norm
)

roster[
    "name_alias"
] = roster[
    "player"
].map(
    name_alias
)

roster[
    "nhl_player_id"
] = roster[
    "player_id"
].map(
    id_key
)


exact_lookup = {}

for key, group in roster.groupby(
    "player_key",
    dropna=False,
):

    if (
        key
        and len(
            group
        )
        == 1
    ):

        exact_lookup[
            key
        ] = group.iloc[
            0
        ].to_dict()


alias_lookup = {}

for key, group in roster.groupby(
    "name_alias",
    dropna=False,
):

    if (
        key
        and len(
            group
        )
        == 1
    ):

        alias_lookup[
            key
        ] = group.iloc[
            0
        ].to_dict()


def resolve_player(
    value,
):

    key = norm(
        value
    )

    if key in exact_lookup:

        return exact_lookup[
            key
        ]


    alias = name_alias(
        value
    )

    if alias in alias_lookup:

        return alias_lookup[
            alias
        ]


    return None


# ============================================================
# CURRENT ESPN INJURY CONTEXT
# SECONDARY FACT SOURCE — NOT NHL OFFICIAL
# ============================================================

def injury_gate(
    status,
    type_text,
    fantasy,
):

    blob = (
        str(
            status or ""
        )
        + " "
        + str(
            type_text or ""
        )
        + " "
        + str(
            fantasy or ""
        )
    ).upper()


    blocking = [
        "INJURED RESERVE",
        "LONG-TERM",
        "LONG TERM",
        "LTIR",
        "SUSPENSION",
        "OUT",
        "IR-NR",
    ]


    if any(
        word in blob
        for word in blocking
    ):

        return "BLOCK"


    review = [
        "DAY-TO-DAY",
        "DAY TO DAY",
        "QUESTIONABLE",
        "DOUBTFUL",
        "GTD",
        "DTD",
        "GAME-TIME",
        "GAME TIME",
    ]


    if any(
        word in blob
        for word in review
    ):

        return "REVIEW"


    return "REVIEW"


def collect_injuries():

    url = (
        "https://site.api.espn.com/"
        "apis/site/v2/sports/hockey/"
        "nhl/injuries"
    )


    try:

        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent":
                    "Sports-HULK/1.0",
            },
        )

        response.raise_for_status()

        payload = response.json()

    except Exception as exc:

        print(
            "NHL INJURY WARNING:",
            type(
                exc
            ).__name__,
        )

        pd.DataFrame().to_csv(
            INJURIES_OUT,
            index=False,
        )

        return pd.DataFrame()


    rows = []


    for team_block in (
        payload.get(
            "injuries"
        )
        or []
    ):

        team_name = (
            team_block.get(
                "displayName"
            )
            or ""
        )

        club = team_code(
            team_name
        )


        for item in (
            team_block.get(
                "injuries"
            )
            or []
        ):

            athlete = (
                item.get(
                    "athlete"
                )
                or {}
            )

            details = (
                item.get(
                    "details"
                )
                or {}
            )

            fantasy = (
                details.get(
                    "fantasyStatus"
                )
                or {}
            )

            type_obj = (
                item.get(
                    "type"
                )
                or {}
            )


            player = (
                athlete.get(
                    "displayName"
                )
                or (
                    (
                        athlete.get(
                            "firstName",
                            ""
                        )
                        + " "
                        + athlete.get(
                            "lastName",
                            ""
                        )
                    ).strip()
                )
            )


            resolved = resolve_player(
                player
            )


            nhl_id = (
                resolved.get(
                    "nhl_player_id",
                    ""
                )
                if resolved
                else ""
            )


            status = item.get(
                "status",
                ""
            )

            type_text = (
                type_obj.get(
                    "description"
                )
                or type_obj.get(
                    "name"
                )
                or ""
            )

            fantasy_text = (
                fantasy.get(
                    "description"
                )
                or fantasy.get(
                    "displayDescription"
                )
                or fantasy.get(
                    "abbreviation"
                )
                or ""
            )


            rows.append({
                "team":
                    club,

                "team_name":
                    team_name,

                "player":
                    player,

                "player_key":
                    norm(
                        player
                    ),

                "nhl_player_id":
                    nhl_id,

                "status":
                    status,

                "injury_type":
                    type_text,

                "fantasy_status":
                    fantasy_text,

                "detail":
                    details.get(
                        "detail",
                        ""
                    ),

                "side":
                    details.get(
                        "side",
                        ""
                    ),

                "return_date":
                    details.get(
                        "returnDate",
                        ""
                    ),

                "updated":
                    item.get(
                        "date",
                        ""
                    ),

                "injury_gate":
                    injury_gate(
                        status,
                        type_text,
                        fantasy_text,
                    ),

                "source":
                    "ESPN_PUBLIC_INJURY_CONTEXT",
            })


    injuries = pd.DataFrame(
        rows
    )


    if not injuries.empty:

        injuries = (
            injuries
            .sort_values(
                "updated"
            )
            .drop_duplicates(
                [
                    "team",
                    "player_key",
                ],
                keep="last",
            )
        )


    injuries.to_csv(
        INJURIES_OUT,
        index=False,
    )


    return injuries


# ============================================================
# TODAY'S GOALIE LISTINGS
# IMPORTANT: LISTED != CONFIRMED STARTER
# ============================================================

def collect_goalie_listings():

    date_text = datetime.now(
        ET
    ).strftime(
        "%Y%m%d"
    )

    base = (
        "https://site.api.espn.com/"
        "apis/site/v2/sports/hockey/nhl"
    )


    try:

        response = requests.get(
            base
            + "/scoreboard",
            params={
                "dates":
                    date_text,
            },
            timeout=25,
        )

        response.raise_for_status()

        scoreboard = response.json()

    except Exception as exc:

        print(
            "NHL GOALIE LISTING WARNING:",
            type(
                exc
            ).__name__,
        )

        pd.DataFrame().to_csv(
            GOALIES_OUT,
            index=False,
        )

        return pd.DataFrame()


    rows = []


    for event in (
        scoreboard.get(
            "events"
        )
        or []
    ):

        event_id = str(
            event.get(
                "id",
                ""
            )
        )


        team_ids = {}


        competitions = (
            event.get(
                "competitions"
            )
            or []
        )


        if competitions:

            for competitor in (
                competitions[
                    0
                ].get(
                    "competitors"
                )
                or []
            ):

                team_obj = (
                    competitor.get(
                        "team"
                    )
                    or {}
                )

                team_ids[
                    str(
                        team_obj.get(
                            "id",
                            ""
                        )
                    )
                ] = (
                    team_obj.get(
                        "abbreviation"
                    )
                    or ""
                )


        try:

            s = requests.get(
                base
                + "/summary",
                params={
                    "event":
                        event_id,
                },
                timeout=25,
            )

            s.raise_for_status()

            summary = s.json()

        except Exception:

            continue


        for _, block in (
            summary.get(
                "goalies"
            )
            or {}
        ).items():

            club = team_code(
                team_ids.get(
                    str(
                        block.get(
                            "teamId",
                            ""
                        )
                    ),
                    "",
                )
            )


            for athlete in (
                block.get(
                    "athletes"
                )
                or []
            ):

                player = (
                    athlete.get(
                        "displayName"
                    )
                    or ""
                )

                resolved = resolve_player(
                    player
                )


                rows.append({
                    "espn_event_id":
                        event_id,

                    "team":
                        club,

                    "player":
                        player,

                    "player_key":
                        norm(
                            player
                        ),

                    "nhl_player_id":
                        (
                            resolved.get(
                                "nhl_player_id",
                                ""
                            )
                            if resolved
                            else ""
                        ),

                    "listing_status":
                        "LISTED_NOT_CONFIRMED",

                    "source":
                        "ESPN_PUBLIC_GAME_SUMMARY",
                })


    listings = pd.DataFrame(
        rows
    )


    if not listings.empty:

        listings = listings.drop_duplicates(
            [
                "espn_event_id",
                "team",
                "player_key",
            ],
            keep="last",
        )


    listings.to_csv(
        GOALIES_OUT,
        index=False,
    )


    return listings


injuries = collect_injuries()
goalie_listings = (
    collect_goalie_listings()
)


injury_by_id = {}
injury_by_name = {}


if not injuries.empty:

    for _, row in injuries.iterrows():

        if row.get(
            "nhl_player_id"
        ):

            injury_by_id[
                str(
                    row[
                        "nhl_player_id"
                    ]
                )
            ] = row.to_dict()

        injury_by_name[
            norm(
                row.get(
                    "player"
                )
            )
        ] = row.to_dict()


listed_goalie_ids = set()
listed_goalie_names = set()


if not goalie_listings.empty:

    listed_goalie_ids = {
        str(
            x
        )
        for x in goalie_listings[
            "nhl_player_id"
        ]
        .fillna(
            ""
        )
        .astype(
            str
        )
        if x
        and x.lower()
        != "nan"
    }

    listed_goalie_names = {
        norm(
            x
        )
        for x in goalie_listings[
            "player"
        ]
        .fillna(
            ""
        )
    }


# ============================================================
# GAME MARKET NORMALIZATION
# ============================================================

def normalize_games():

    games = read_csv(
        RAW_GAMES
    )


    if games.empty:
        return pd.DataFrame()


    games[
        "start_dt"
    ] = pd.to_datetime(
        games[
            "start"
        ],
        utc=True,
        errors="coerce",
        format="mixed",
    )


    games = games[
        games[
            "start_dt"
        ].isna()
        |
        (
            games[
                "start_dt"
            ]
            >= NOW
            - pd.Timedelta(
                hours=1
            )
        )
    ].copy()


    games[
        "away_team_canonical"
    ] = games[
        "away_team"
    ].map(
        team_code
    )

    games[
        "home_team_canonical"
    ] = games[
        "home_team"
    ].map(
        team_code
    )


    market_map = {
        "H2H":
            "MONEYLINE",

        "MONEYLINE":
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


    games[
        "market_canonical"
    ] = (
        games[
            "market"
        ]
        .astype(
            str
        )
        .str.upper()
        .map(
            market_map
        )
    )


    games = games[
        games[
            "market_canonical"
        ].notna()
    ].copy()


    def selection(
        row,
    ):

        market = row[
            "market_canonical"
        ]

        side = str(
            row.get(
                "side",
                ""
            )
        ).upper()

        raw = row.get(
            "selection"
        )


        if market == "TOTAL":

            if side in {
                "OVER",
                "UNDER",
            }:

                return side

            raw_side = str(
                raw
            ).upper()

            if "OVER" in raw_side:
                return "OVER"

            if "UNDER" in raw_side:
                return "UNDER"

            return ""


        club = team_code(
            raw
        )

        if club:
            return club


        if side == "AWAY":

            return row[
                "away_team_canonical"
            ]


        if side == "HOME":

            return row[
                "home_team_canonical"
            ]


        return ""


    games[
        "selection_canonical"
    ] = games.apply(
        selection,
        axis=1,
    )


    games[
        "line_group"
    ] = pd.to_numeric(
        games[
            "line"
        ],
        errors="coerce",
    )


    def key(
        row,
    ):

        start = row[
            "start_dt"
        ]

        if pd.isna(
            start
        ):
            date = "UNKNOWN"
        else:
            date = (
                start
                .tz_convert(
                    ET
                )
                .strftime(
                    "%Y-%m-%d"
                )
            )


        return (
            date
            + "|"
            + row[
                "away_team_canonical"
            ]
            + "|"
            + row[
                "home_team_canonical"
            ]
        )


    games[
        "game_key"
    ] = games.apply(
        key,
        axis=1,
    )


    games[
        "price_american"
    ] = pd.to_numeric(
        games[
            "price_american"
        ],
        errors="coerce",
    )


    games = games[
        games[
            "away_team_canonical"
        ].ne(
            ""
        )
        &
        games[
            "home_team_canonical"
        ].ne(
            ""
        )
        &
        games[
            "selection_canonical"
        ].ne(
            ""
        )
    ].copy()


    games = games.drop_duplicates(
        [
            "provider",
            "sportsbook",
            "game_key",
            "market_canonical",
            "selection_canonical",
            "line_group",
            "price_american",
        ],
        keep="last",
    )


    games.to_csv(
        GAME_NORMALIZED_OUT,
        index=False,
    )


    grouped = (
        games.groupby(
            [
                "game_key",
                "away_team_canonical",
                "home_team_canonical",
                "market_canonical",
                "selection_canonical",
                "line_group",
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


    grouped.to_csv(
        GAME_FUSION_OUT,
        index=False,
    )


    return (
        games,
        grouped,
    )


game_normalized, game_fusion = (
    normalize_games()
)


# ============================================================
# HISTORICAL PLAYER GROUPS
# ============================================================

player_history = read_csv(
    PLAYER_HISTORY
)

goalie_history = read_csv(
    GOALIE_HISTORY
)


def prepare_history(
    frame,
):

    if frame.empty:
        return frame


    frame = frame.copy()


    frame[
        "player_id_key"
    ] = frame[
        "player_id"
    ].map(
        id_key
    )


    frame[
        "start_dt"
    ] = pd.to_datetime(
        frame[
            "start"
        ],
        utc=True,
        errors="coerce",
    )


    if "game_type" in frame.columns:

        game_type = pd.to_numeric(
            frame[
                "game_type"
            ],
            errors="coerce",
        )


        frame = frame[
            game_type.isin(
                [
                    2,
                    3,
                ]
            )
        ].copy()


    return frame.sort_values(
        "start_dt"
    )


player_history = prepare_history(
    player_history
)

goalie_history = prepare_history(
    goalie_history
)


player_groups = {
    key:
        group.sort_values(
            "start_dt"
        )

    for key, group
    in player_history.groupby(
        "player_id_key"
    )
}


goalie_groups = {
    key:
        group.sort_values(
            "start_dt"
        )

    for key, group
    in goalie_history.groupby(
        "player_id_key"
    )
}


def historical_context(
    nhl_player_id,
    stat_type,
    side,
    line,
    role,
):

    key = str(
        nhl_player_id
        or ""
    )


    group = (
        goalie_groups.get(
            key
        )
        if role
        == "GOALIE"
        else
        player_groups.get(
            key
        )
    )


    empty = {
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

        "toi_l5_avg":
            None,

        "context_direction":
            "NO_CONTEXT",

        "sample_gate":
            "INSUFFICIENT",
    }


    if (
        group is None
        or group.empty
        or stat_type
        not in group.columns
    ):

        return empty


    group = group.copy()


    if role == "GOALIE":

        starter = (
            group[
                "starter"
            ]
            .astype(
                str
            )
            .str.lower()
            .isin(
                [
                    "true",
                    "1",
                ]
            )
        )


        toi = pd.to_numeric(
            group[
                "toi_minutes"
            ],
            errors="coerce",
        )


        meaningful = group[
            starter
            &
            (
                toi
                >= 20
            )
        ].copy()


    else:

        toi = pd.to_numeric(
            group[
                "toi_minutes"
            ],
            errors="coerce",
        )


        meaningful = group[
            toi
            >= 8
        ].copy()


    values = pd.to_numeric(
        meaningful[
            stat_type
        ],
        errors="coerce",
    )


    valid = meaningful[
        values.notna()
    ].copy()


    values = pd.to_numeric(
        valid[
            stat_type
        ],
        errors="coerce",
    )


    if valid.empty:

        return empty


    line = number(
        line
    )


    def avg(
        n,
    ):

        return (
            values
            .tail(
                n
            )
            .mean()
        )


    def hit_rate(
        n,
    ):

        if line is None:
            return None


        recent = (
            values
            .tail(
                n
            )
        )


        if recent.empty:
            return None


        if str(
            side
        ).upper() == "OVER":

            return float(
                (
                    recent
                    > line
                ).mean()
            )


        if str(
            side
        ).upper() == "UNDER":

            return float(
                (
                    recent
                    < line
                ).mean()
            )


        return None


    l5 = hit_rate(
        5
    )

    l10 = hit_rate(
        10
    )


    if (
        l5 is not None
        and l10 is not None
        and l5 >= 0.60
        and l10 >= 0.60
    ):

        direction = "SUPPORT"


    elif (
        l5 is not None
        and l10 is not None
        and l5 <= 0.40
        and l10 <= 0.40
    ):

        direction = "OPPOSE"


    else:

        direction = "MIXED"


    minimum = (
        5
        if role
        == "GOALIE"
        else 10
    )


    sample_gate = (
        "QUALIFIED"
        if len(
            valid
        )
        >= minimum
        else "INSUFFICIENT"
    )


    return {
        "sample_games":
            int(
                len(
                    group
                )
            ),

        "meaningful_games":
            int(
                len(
                    valid
                )
            ),

        "stat_l3_avg":
            avg(
                3
            ),

        "stat_l5_avg":
            avg(
                5
            ),

        "stat_l10_avg":
            avg(
                10
            ),

        "stat_season_avg":
            values.mean(),

        "l3_hit_rate":
            hit_rate(
                3
            ),

        "l5_hit_rate":
            l5,

        "l10_hit_rate":
            l10,

        "toi_l5_avg":
            pd.to_numeric(
                valid[
                    "toi_minutes"
                ],
                errors="coerce",
            )
            .tail(
                5
            )
            .mean(),

        "context_direction":
            direction,

        "sample_gate":
            sample_gate,
    }


# ============================================================
# PLAYER MARKET ENRICHMENT
# ============================================================

def enrich_player_markets(
    raw,
    mapping,
    lane,
):

    if raw.empty:
        return pd.DataFrame()


    x = raw.copy()


    x[
        "market_subtype"
    ] = (
        x[
            "market_subtype"
        ]
        .astype(
            str
        )
        .str.upper()
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


    x[
        "line"
    ] = pd.to_numeric(
        x[
            "line"
        ],
        errors="coerce",
    )


    x = x[
        x[
            "market_subtype"
        ].isin(
            mapping
        )
        &
        x[
            "side"
        ].isin(
            [
                "OVER",
                "UNDER",
            ]
        )
        &
        x[
            "line"
        ].notna()
    ].copy()


    if lane == "SPORTSBOOK":

        x = x[
            x[
                "market"
            ]
            .astype(
                str
            )
            .str.upper()
            .eq(
                "PLAYER_TOTAL"
            )
        ].copy()


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
        "away_team_canonical"
    ] = x[
        "away_team"
    ].map(
        team_code
    )

    x[
        "home_team_canonical"
    ] = x[
        "home_team"
    ].map(
        team_code
    )


    enriched = []


    for _, row in x.iterrows():

        raw_player = row.get(
            "player"
        )


        resolved = resolve_player(
            raw_player
        )


        stat_type, role = mapping[
            row[
                "market_subtype"
            ]
        ]


        if resolved:

            nhl_id = resolved.get(
                "nhl_player_id",
                ""
            )

            canonical_player = resolved.get(
                "player",
                raw_player,
            )

            current_team = resolved.get(
                "team",
                ""
            )

            position = resolved.get(
                "position",
                ""
            )

            identity_status = "VERIFIED"

        else:

            nhl_id = ""

            canonical_player = raw_player

            current_team = ""

            position = ""

            identity_status = "UNRESOLVED"


        away = row[
            "away_team_canonical"
        ]

        home = row[
            "home_team_canonical"
        ]


        matchup_identity = (
            "VERIFIED"
            if (
                identity_status
                == "VERIFIED"
                and current_team
                in {
                    away,
                    home,
                }
            )
            else "REVIEW"
        )


        injury = (
            injury_by_id.get(
                str(
                    nhl_id
                )
            )
            if nhl_id
            else None
        )


        if not injury:

            injury = injury_by_name.get(
                norm(
                    raw_player
                )
            )


        current_injury_gate = (
            injury.get(
                "injury_gate"
            )
            if injury
            else "CLEAR"
        )


        injury_status = (
            injury.get(
                "status",
                ""
            )
            if injury
            else ""
        )


        goalie_listing = ""


        if role == "GOALIE":

            if (
                (
                    nhl_id
                    and str(
                        nhl_id
                    )
                    in listed_goalie_ids
                )
                or norm(
                    canonical_player
                )
                in listed_goalie_names
            ):

                goalie_listing = (
                    "LISTED_NOT_CONFIRMED"
                )

            else:

                goalie_listing = (
                    "START_NOT_CONFIRMED"
                )


        context = historical_context(
            nhl_id,
            stat_type,
            row[
                "side"
            ],
            row[
                "line"
            ],
            role,
        )


        if identity_status != "VERIFIED":

            status = "IDENTITY_REVIEW"


        elif matchup_identity != "VERIFIED":

            status = "MATCHUP_REVIEW"


        elif current_injury_gate == "BLOCK":

            status = "INJURY_BLOCK"


        elif current_injury_gate == "REVIEW":

            status = "INJURY_REVIEW"


        elif role == "GOALIE":

            # A listed goalie is useful information,
            # but not sufficient to claim a start.
            status = "GOALIE_START_REVIEW"


        elif (
            context[
                "sample_gate"
            ]
            == "QUALIFIED"
            and
            context[
                "context_direction"
            ]
            == "SUPPORT"
        ):

            status = "QUALIFIED_CONTEXT"


        else:

            status = "WATCH"


        start = row[
            "start_dt"
        ]


        local_date = (
            start
            .tz_convert(
                ET
            )
            .strftime(
                "%Y-%m-%d"
            )
            if pd.notna(
                start
            )
            else "UNKNOWN"
        )


        game_key = (
            local_date
            + "|"
            + away
            + "|"
            + home
        )


        enriched.append({
            **row.to_dict(),

            "game_key":
                game_key,

            "player_key":
                norm(
                    canonical_player
                ),

            "canonical_player":
                canonical_player,

            "nhl_player_id":
                nhl_id,

            "current_team":
                current_team,

            "position":
                position,

            "role":
                role,

            "stat_type":
                stat_type,

            "identity_status":
                identity_status,

            "matchup_identity":
                matchup_identity,

            "injury_gate":
                current_injury_gate,

            "injury_status":
                injury_status,

            "goalie_listing":
                goalie_listing,

            **context,

            "research_status":
                status,
        })


    return pd.DataFrame(
        enriched
    )


# ============================================================
# SPORTSBOOK PROP FUSION
# ============================================================

def build_prop_pricing_summary(prop_rows):
    """Same-book, exact-line no-vig pricing for player props."""
    if prop_rows.empty:
        return pd.DataFrame()

    key_cols = [
        "game_key",
        "nhl_player_id",
        "player_key",
        "market_subtype",
        "stat_type",
        "role",
        "line",
    ]

    summaries = []

    for keys, market_rows in prop_rows.groupby(
        key_cols,
        dropna=False,
    ):
        paired_rows = []

        for sportsbook, book_rows in market_rows.groupby(
            "sportsbook",
            dropna=False,
        ):
            sportsbook = str(sportsbook or "").strip()

            if not sportsbook:
                continue

            book_rows = book_rows.copy()

            if "captured_at" in book_rows.columns:
                book_rows["_captured"] = pd.to_datetime(
                    book_rows["captured_at"],
                    errors="coerce",
                    utc=True,
                )
                book_rows = book_rows.sort_values(
                    "_captured"
                )

            over = book_rows[
                book_rows["side"]
                .astype(str)
                .str.upper()
                .eq("OVER")
            ]

            under = book_rows[
                book_rows["side"]
                .astype(str)
                .str.upper()
                .eq("UNDER")
            ]

            if over.empty or under.empty:
                continue

            over_row = over.iloc[-1]
            under_row = under.iloc[-1]

            over_time = pd.to_datetime(
                over_row.get("captured_at"),
                errors="coerce",
                utc=True,
            )
            under_time = pd.to_datetime(
                under_row.get("captured_at"),
                errors="coerce",
                utc=True,
            )

            timestamps = [
                ts
                for ts in [over_time, under_time]
                if pd.notna(ts)
            ]

            # Use the older side timestamp so both halves of the pair
            # must be fresh enough.
            pair_time = (
                min(timestamps).isoformat()
                if timestamps
                else None
            )

            paired_rows.append(
                {
                    "bookmaker": sportsbook,
                    "line": float(keys[-1]),
                    "over_price": over_row.get(
                        "price_american"
                    ),
                    "under_price": under_row.get(
                        "price_american"
                    ),
                    "updated_at": pair_time,
                }
            )

        pricing = consensus_for_exact_line(
            paired_rows,
            target_line=float(keys[-1]),
            max_age_seconds=600,
        )

        summaries.append(
            {
                **dict(zip(key_cols, keys)),
                "market_pricing_status":
                    pricing.get("status"),
                "paired_book_count":
                    int(
                        pricing.get(
                            "paired_book_count",
                            0,
                        )
                        or 0
                    ),
                "fresh_book_count":
                    int(
                        pricing.get(
                            "fresh_book_count",
                            0,
                        )
                        or 0
                    ),
                "stale_quote_count":
                    int(
                        pricing.get(
                            "stale_count",
                            0,
                        )
                        or 0
                    ),
                "unknown_freshness_count":
                    int(
                        pricing.get(
                            "unknown_freshness_count",
                            0,
                        )
                        or 0
                    ),
                "over_fair_probability":
                    pricing.get(
                        "over_fair_probability"
                    ),
                "under_fair_probability":
                    pricing.get(
                        "under_fair_probability"
                    ),
                "fair_probability_mad":
                    pricing.get(
                        "over_fair_probability_mad"
                    ),
                "median_hold":
                    pricing.get(
                        "median_hold"
                    ),
                "best_over_price":
                    pricing.get(
                        "best_over_price"
                    ),
                "best_over_book":
                    pricing.get(
                        "best_over_book"
                    ),
                "best_under_price":
                    pricing.get(
                        "best_under_price"
                    ),
                "best_under_book":
                    pricing.get(
                        "best_under_book"
                    ),
                "market_data_quality_grade":
                    pricing.get(
                        "data_quality_grade",
                        "D",
                    ),
                "market_quality_warnings":
                    "|".join(
                        pricing.get(
                            "warnings",
                            [],
                        )
                    ),
            }
        )

    return pd.DataFrame(
        summaries
    )


raw_props = read_csv(
    RAW_PROPS
)

prop_rows = enrich_player_markets(
    raw_props,
    SPORTSBOOK_STAT_MAP,
    "SPORTSBOOK",
)


if prop_rows.empty:

    prop_fusion = pd.DataFrame()
    prop_pricing = pd.DataFrame()

else:

    prop_pricing = build_prop_pricing_summary(
        prop_rows
    )

    prop_rows[
        "price_american"
    ] = pd.to_numeric(
        prop_rows[
            "price_american"
        ],
        errors="coerce",
    )


    prop_fusion = (
        prop_rows.groupby(
            [
                "game_key",
                "nhl_player_id",
                "player_key",
                "market_subtype",
                "stat_type",
                "role",
                "side",
                "line",
            ],
            dropna=False,
        )
        .agg(
            event_id=(
                "event_id",
                "first",
            ),

            start_dt=(
                "start_dt",
                "min",
            ),

            away_team=(
                "away_team_canonical",
                "first",
            ),

            home_team=(
                "home_team_canonical",
                "first",
            ),

            player=(
                "canonical_player",
                "first",
            ),

            current_team=(
                "current_team",
                "first",
            ),

            position=(
                "position",
                "first",
            ),

            identity_status=(
                "identity_status",
                "first",
            ),

            matchup_identity=(
                "matchup_identity",
                "first",
            ),

            injury_gate=(
                "injury_gate",
                "first",
            ),

            injury_status=(
                "injury_status",
                "first",
            ),

            goalie_listing=(
                "goalie_listing",
                "first",
            ),

            book_count=(
                "sportsbook",
                "nunique",
            ),

            books=(
                "sportsbook",
                pipe_unique,
            ),

            median_price_american=(
                "price_american",
                "median",
            ),

            sample_games=(
                "sample_games",
                "first",
            ),

            meaningful_games=(
                "meaningful_games",
                "first",
            ),

            stat_l3_avg=(
                "stat_l3_avg",
                "first",
            ),

            stat_l5_avg=(
                "stat_l5_avg",
                "first",
            ),

            stat_l10_avg=(
                "stat_l10_avg",
                "first",
            ),

            stat_season_avg=(
                "stat_season_avg",
                "first",
            ),

            l3_hit_rate=(
                "l3_hit_rate",
                "first",
            ),

            l5_hit_rate=(
                "l5_hit_rate",
                "first",
            ),

            l10_hit_rate=(
                "l10_hit_rate",
                "first",
            ),

            toi_l5_avg=(
                "toi_l5_avg",
                "first",
            ),

            context_direction=(
                "context_direction",
                "first",
            ),

            sample_gate=(
                "sample_gate",
                "first",
            ),

            research_status=(
                "research_status",
                "first",
            ),
        )
        .reset_index()
    )

    if not prop_pricing.empty:
        pricing_keys = [
            "game_key",
            "nhl_player_id",
            "player_key",
            "market_subtype",
            "stat_type",
            "role",
            "line",
        ]

        prop_fusion = prop_fusion.merge(
            prop_pricing,
            on=pricing_keys,
            how="left",
        )

        side_upper = (
            prop_fusion["side"]
            .astype(str)
            .str.upper()
        )

        prop_fusion[
            "market_fair_probability"
        ] = np.where(
            side_upper.eq("OVER"),
            prop_fusion[
                "over_fair_probability"
            ],
            np.where(
                side_upper.eq("UNDER"),
                prop_fusion[
                    "under_fair_probability"
                ],
                np.nan,
            ),
        )

        prop_fusion[
            "best_executable_price_american"
        ] = np.where(
            side_upper.eq("OVER"),
            prop_fusion[
                "best_over_price"
            ],
            np.where(
                side_upper.eq("UNDER"),
                prop_fusion[
                    "best_under_price"
                ],
                np.nan,
            ),
        )

        prop_fusion[
            "best_executable_sportsbook"
        ] = np.where(
            side_upper.eq("OVER"),
            prop_fusion[
                "best_over_book"
            ],
            np.where(
                side_upper.eq("UNDER"),
                prop_fusion[
                    "best_under_book"
                ],
                None,
            ),
        )


prop_fusion.to_csv(
    PROP_FUSION_OUT,
    index=False,
)


# ============================================================
# PRIZEPICKS FUSION
# ============================================================

raw_pp = read_csv(
    RAW_PP
)

pp_rows = enrich_player_markets(
    raw_pp,
    PRIZEPICKS_STAT_MAP,
    "PRIZEPICKS",
)


if pp_rows.empty:

    pp_fusion = pd.DataFrame()

else:

    sportsbook_index = {}


    if not prop_fusion.empty:

        for _, row in prop_fusion.iterrows():

            key = (
                str(
                    row.get(
                        "nhl_player_id",
                        ""
                    )
                ),
                str(
                    row.get(
                        "stat_type",
                        ""
                    )
                ),
                str(
                    row.get(
                        "side",
                        ""
                    )
                ),
                float(
                    row.get(
                        "line"
                    )
                ),
            )


            sportsbook_index[
                key
            ] = {
                "count":
                    int(
                        row.get(
                            "book_count",
                            0,
                        )
                    ),

                "books":
                    row.get(
                        "books",
                        "",
                    ),

                "market_pricing_status":
                    row.get(
                        "market_pricing_status"
                    ),

                "paired_book_count":
                    int(
                        row.get(
                            "paired_book_count",
                            0,
                        )
                        or 0
                    ),

                "fresh_book_count":
                    int(
                        row.get(
                            "fresh_book_count",
                            0,
                        )
                        or 0
                    ),

                "stale_quote_count":
                    int(
                        row.get(
                            "stale_quote_count",
                            0,
                        )
                        or 0
                    ),

                "unknown_freshness_count":
                    int(
                        row.get(
                            "unknown_freshness_count",
                            0,
                        )
                        or 0
                    ),

                "market_fair_probability":
                    row.get(
                        "market_fair_probability"
                    ),

                "fair_probability_mad":
                    row.get(
                        "fair_probability_mad"
                    ),

                "median_hold":
                    row.get(
                        "median_hold"
                    ),

                "best_executable_price_american":
                    row.get(
                        "best_executable_price_american"
                    ),

                "best_executable_sportsbook":
                    row.get(
                        "best_executable_sportsbook"
                    ),

                "market_data_quality_grade":
                    row.get(
                        "market_data_quality_grade",
                        "D",
                    ),

                "market_quality_warnings":
                    row.get(
                        "market_quality_warnings",
                        "",
                    ),
            }


    counts = []
    books = []
    statuses = []
    pricing_matches = []


    for _, row in pp_rows.iterrows():

        try:

            line = float(
                row[
                    "line"
                ]
            )

        except Exception:

            line = np.nan


        key = (
            str(
                row.get(
                    "nhl_player_id",
                    ""
                )
            ),
            str(
                row.get(
                    "stat_type",
                    ""
                )
            ),
            str(
                row.get(
                    "side",
                    ""
                )
            ),
            line,
        )


        match = sportsbook_index.get(
            key,
            {
                "count":
                    0,

                "books":
                    "",

                "market_pricing_status":
                    "NO_EXACT_SPORTSBOOK_MATCH",

                "paired_book_count":
                    0,

                "fresh_book_count":
                    0,

                "stale_quote_count":
                    0,

                "unknown_freshness_count":
                    0,

                "market_fair_probability":
                    None,

                "fair_probability_mad":
                    None,

                "median_hold":
                    None,

                "best_executable_price_american":
                    None,

                "best_executable_sportsbook":
                    None,

                "market_data_quality_grade":
                    "D",

                "market_quality_warnings":
                    "NO_EXACT_SPORTSBOOK_MATCH",
            },
        )


        counts.append(
            match[
                "count"
            ]
        )

        books.append(
            match[
                "books"
            ]
        )

        pricing_matches.append(
            {
                "sportsbook_market_pricing_status":
                    match.get(
                        "market_pricing_status"
                    ),

                "sportsbook_paired_book_count":
                    int(
                        match.get(
                            "paired_book_count",
                            0,
                        )
                        or 0
                    ),

                "sportsbook_fresh_book_count":
                    int(
                        match.get(
                            "fresh_book_count",
                            0,
                        )
                        or 0
                    ),

                "sportsbook_stale_quote_count":
                    int(
                        match.get(
                            "stale_quote_count",
                            0,
                        )
                        or 0
                    ),

                "sportsbook_unknown_freshness_count":
                    int(
                        match.get(
                            "unknown_freshness_count",
                            0,
                        )
                        or 0
                    ),

                "sportsbook_market_fair_probability":
                    match.get(
                        "market_fair_probability"
                    ),

                "sportsbook_fair_probability_mad":
                    match.get(
                        "fair_probability_mad"
                    ),

                "sportsbook_median_hold":
                    match.get(
                        "median_hold"
                    ),

                "sportsbook_best_executable_price_american":
                    match.get(
                        "best_executable_price_american"
                    ),

                "sportsbook_best_executable":
                    match.get(
                        "best_executable_sportsbook"
                    ),

                "sportsbook_market_data_quality_grade":
                    match.get(
                        "market_data_quality_grade",
                        "D",
                    ),

                "sportsbook_market_quality_warnings":
                    match.get(
                        "market_quality_warnings",
                        "",
                    ),
            }
        )


        status = row[
            "research_status"
        ]


        if (
            status
            == "QUALIFIED_CONTEXT"
            and match[
                "count"
            ]
            < 1
        ):

            status = "WATCH"


        statuses.append(
            status
        )


    pp_rows[
        "sportsbook_book_count"
    ] = counts

    pp_rows[
        "sportsbook_books"
    ] = books

    if pricing_matches:
        pricing_frame = pd.DataFrame(
            pricing_matches,
            index=pp_rows.index,
        )

        for column in pricing_frame.columns:
            pp_rows[
                column
            ] = pricing_frame[
                column
            ]

    pp_rows[
        "research_status"
    ] = statuses


    pp_fusion = (
        pp_rows
        .sort_values(
            [
                "start_dt",
                "canonical_player",
                "market_subtype",
                "side",
            ]
        )
        .drop_duplicates(
            [
                "event_id",
                "nhl_player_id",
                "market_subtype",
                "side",
                "line",
            ],
            keep="last",
        )
    )


pp_fusion.to_csv(
    PP_FUSION_OUT,
    index=False,
)


# ============================================================
# RECEIPT
# ============================================================

prop_identity_rate = (
    float(
        prop_fusion[
            "identity_status"
        ]
        .eq(
            "VERIFIED"
        )
        .mean()
    )
    if (
        not prop_fusion.empty
        and "identity_status"
        in prop_fusion.columns
    )
    else 0.0
)


pp_identity_rate = (
    float(
        pp_fusion[
            "identity_status"
        ]
        .eq(
            "VERIFIED"
        )
        .mean()
    )
    if (
        not pp_fusion.empty
        and "identity_status"
        in pp_fusion.columns
    )
    else 0.0
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

    "injury_rows":
        int(
            len(
                injuries
            )
        ),

    "goalie_listing_rows":
        int(
            len(
                goalie_listings
            )
        ),

    "normalized_game_rows":
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

    "prop_identity_verified_pct":
        round(
            prop_identity_rate
            * 100,
            2,
        ),

    "prizepicks_identity_verified_pct":
        round(
            pp_identity_rate
            * 100,
            2,
        ),

    "policy":
        "MARKET_IS_EVIDENCE_NOT_PROBABILITY",

    "injury_source":
        "ESPN_PUBLIC_SECONDARY_CONTEXT",

    "goalie_listing_policy":
        "LISTED_IS_NOT_CONFIRMED_STARTER",

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
    "CURRENT INJURY ROWS:",
    len(
        injuries
    )
)

print(
    "TODAY GOALIE LISTINGS:",
    len(
        goalie_listings
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
    "RESULT: NHL_FUSION_READY"
)
