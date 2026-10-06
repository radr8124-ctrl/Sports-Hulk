#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta

import csv
import json
import math
import re

import pandas as pd
import requests


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

DEC = (
    ROOT
    / "nfl_live"
    / "decision"
)

HISTORY = (
    DEC
    / "history"
)

LEDGER = (
    HISTORY
    / "NFL_RECOMMENDATION_LEDGER.csv"
)

RESULT_HISTORY = (
    HISTORY
    / "NFL_GAME_RESULTS_HISTORY.csv"
)

GRADED_HISTORY = (
    HISTORY
    / "NFL_GRADED_SNAPSHOT_HISTORY.csv"
)

GRADED_LATEST = (
    HISTORY
    / "NFL_GRADED_RECOMMENDATIONS.csv"
)

PERFORMANCE = (
    HISTORY
    / "NFL_LEARNING_PERFORMANCE.csv"
)

SUMMARY = (
    HISTORY
    / "NFL_LEARNING_SUMMARY.json"
)

PLAYER_STATS = (
    ROOT
    / "nfl_live"
    / "player_context"
    / "derived"
    / "NFL_PLAYER_STATS_RECENT.csv"
)


CORE = (
    "https://sports.core.api.espn.com/"
    "v2/sports/football/leagues/nfl"
)

TIMEOUT = 25


# =========================================================
# NORMALIZATION
# =========================================================

TEAM_NAMES = {
    "ARI": [
        "ARI",
        "ARIZONA CARDINALS",
        "CARDINALS",
    ],

    "ATL": [
        "ATL",
        "ATLANTA FALCONS",
        "FALCONS",
    ],

    "BAL": [
        "BAL",
        "BALTIMORE RAVENS",
        "RAVENS",
    ],

    "BUF": [
        "BUF",
        "BUFFALO BILLS",
        "BILLS",
    ],

    "CAR": [
        "CAR",
        "CAROLINA PANTHERS",
        "PANTHERS",
    ],

    "CHI": [
        "CHI",
        "CHICAGO BEARS",
        "BEARS",
    ],

    "CIN": [
        "CIN",
        "CINCINNATI BENGALS",
        "BENGALS",
    ],

    "CLE": [
        "CLE",
        "CLEVELAND BROWNS",
        "BROWNS",
    ],

    "DAL": [
        "DAL",
        "DALLAS COWBOYS",
        "COWBOYS",
    ],

    "DEN": [
        "DEN",
        "DENVER BRONCOS",
        "BRONCOS",
    ],

    "DET": [
        "DET",
        "DETROIT LIONS",
        "LIONS",
    ],

    "GB": [
        "GB",
        "GREEN BAY PACKERS",
        "PACKERS",
    ],

    "HOU": [
        "HOU",
        "HOUSTON TEXANS",
        "TEXANS",
    ],

    "IND": [
        "IND",
        "INDIANAPOLIS COLTS",
        "COLTS",
    ],

    "JAX": [
        "JAX",
        "JACKSONVILLE JAGUARS",
        "JAGUARS",
    ],

    "KC": [
        "KC",
        "KANSAS CITY CHIEFS",
        "CHIEFS",
    ],

    "LV": [
        "LV",
        "LAS VEGAS RAIDERS",
        "RAIDERS",
    ],

    "LAC": [
        "LAC",
        "LOS ANGELES CHARGERS",
        "LA CHARGERS",
        "CHARGERS",
    ],

    "LAR": [
        "LAR",
        "LOS ANGELES RAMS",
        "LA RAMS",
        "RAMS",
    ],

    "MIA": [
        "MIA",
        "MIAMI DOLPHINS",
        "DOLPHINS",
    ],

    "MIN": [
        "MIN",
        "MINNESOTA VIKINGS",
        "VIKINGS",
    ],

    "NE": [
        "NE",
        "NEW ENGLAND PATRIOTS",
        "PATRIOTS",
    ],

    "NO": [
        "NO",
        "NEW ORLEANS SAINTS",
        "SAINTS",
    ],

    "NYG": [
        "NYG",
        "NEW YORK GIANTS",
        "GIANTS",
    ],

    "NYJ": [
        "NYJ",
        "NEW YORK JETS",
        "JETS",
    ],

    "PHI": [
        "PHI",
        "PHILADELPHIA EAGLES",
        "EAGLES",
    ],

    "PIT": [
        "PIT",
        "PITTSBURGH STEELERS",
        "STEELERS",
    ],

    "SEA": [
        "SEA",
        "SEATTLE SEAHAWKS",
        "SEAHAWKS",
    ],

    "SF": [
        "SF",
        "SAN FRANCISCO 49ERS",
        "49ERS",
        "NINERS",
    ],

    "TB": [
        "TB",
        "TAMPA BAY BUCCANEERS",
        "BUCCANEERS",
        "BUCS",
    ],

    "TEN": [
        "TEN",
        "TENNESSEE TITANS",
        "TITANS",
    ],

    "WAS": [
        "WAS",
        "WASHINGTON COMMANDERS",
        "COMMANDERS",
    ],
}


def text_norm(value):

    value = str(
        value or ""
    ).upper()

    value = re.sub(
        r"[^A-Z0-9]+",
        " ",
        value,
    )

    return " ".join(
        value.split()
    )


TEAM_LOOKUP = {}

for abbr, names in TEAM_NAMES.items():

    for name in names:

        TEAM_LOOKUP[
            text_norm(name)
        ] = abbr


def team_abbr(
    value,
):

    value = text_norm(
        value
    )

    return TEAM_LOOKUP.get(
        value,
        value
        if value in TEAM_NAMES
        else "",
    )


def player_norm(
    value,
):

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(
            value or ""
        ).lower(),
    )


def num(
    value,
):

    try:
        x = float(
            value
        )

        if math.isnan(x):
            return None

        return x

    except Exception:
        return None


def parse_dt(
    value,
):

    try:

        return pd.to_datetime(
            value,
            utc=True,
            errors="coerce",
        )

    except Exception:

        return pd.NaT


def https_ref(
    value,
):

    if not value:
        return ""

    return str(
        value
    ).replace(
        "http://",
        "https://",
        1,
    )


# =========================================================
# ESPN CORE
# =========================================================

SESSION = requests.Session()

SESSION.headers.update(
    {
        "User-Agent":
            "Sports-HULK/1.0 "
            "NFL-learning-results",
    }
)


def get_json(
    url,
):

    response = SESSION.get(
        https_ref(
            url
        ),
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    return response.json()


def ref_json(
    obj,
):

    if not isinstance(
        obj,
        dict,
    ):
        return obj

    ref = obj.get(
        "$ref"
    )

    if ref:

        return get_json(
            ref
        )

    return obj


def score_value(
    obj,
):

    if obj is None:
        return None

    if isinstance(
        obj,
        dict,
    ):

        try:
            obj = ref_json(
                obj
            )

        except Exception:
            pass

        for key in [
            "value",
            "displayValue",
            "score",
        ]:

            if key in obj:

                value = num(
                    obj.get(
                        key
                    )
                )

                if value is not None:
                    return value

    return num(
        obj
    )


def team_value(
    competitor,
):

    team = competitor.get(
        "team"
    )

    if not isinstance(
        team,
        dict,
    ):
        return ""

    try:
        team = ref_json(
            team
        )

    except Exception:
        pass

    for key in [
        "abbreviation",
        "shortDisplayName",
        "displayName",
        "name",
    ]:

        value = team_abbr(
            team.get(
                key
            )
        )

        if value:
            return value

    return ""


def event_week(
    event,
    competition,
):

    possible = [
        event.get(
            "week"
        ),
        competition.get(
            "week"
        ),
    ]

    for value in possible:

        if isinstance(
            value,
            dict,
        ):

            direct = num(
                value.get(
                    "number"
                )
            )

            if direct is not None:
                return int(
                    direct
                )

            ref = str(
                value.get(
                    "$ref",
                    "",
                )
            )

            match = re.search(
                r"/weeks/(\d+)",
                ref,
            )

            if match:
                return int(
                    match.group(1)
                )

    return None


def parse_core_event(
    event,
):

    competitions = event.get(
        "competitions"
    ) or []

    if not competitions:
        return None


    competition = competitions[0]

    try:
        competition = ref_json(
            competition
        )

    except Exception:
        return None


    status = competition.get(
        "status"
    ) or {}

    try:
        status = ref_json(
            status
        )

    except Exception:
        pass


    status_type = (
        status.get(
            "type"
        )
        or {}
    )


    final = bool(
        status_type.get(
            "completed"
        )
    )


    state = str(
        status_type.get(
            "state",
            "",
        )
    ).lower()


    name = str(
        status_type.get(
            "name",
            "",
        )
    ).upper()


    if (
        state == "post"
        or "FINAL" in name
    ):
        final = True


    home = ""
    away = ""

    home_score = None
    away_score = None


    for competitor in (
        competition.get(
            "competitors"
        )
        or []
    ):

        side = str(
            competitor.get(
                "homeAway",
                "",
            )
        ).lower()

        team = team_value(
            competitor
        )

        score = score_value(
            competitor.get(
                "score"
            )
        )

        if side == "home":
            home = team
            home_score = score

        elif side == "away":
            away = team
            away_score = score


    if (
        not home
        or not away
    ):

        short = str(
            event.get(
                "shortName",
                "",
            )
        )

        if "@" in short:

            left, right = (
                short.split(
                    "@",
                    1,
                )
            )

            away = (
                away
                or team_abbr(
                    left
                )
            )

            home = (
                home
                or team_abbr(
                    right
                )
            )


    return {
        "espn_event_id":
            str(
                event.get(
                    "id",
                    "",
                )
            ),

        "start":
            str(
                event.get(
                    "date",
                    "",
                )
            ),

        "week":
            event_week(
                event,
                competition,
            ),

        "away_team":
            away,

        "home_team":
            home,

        "away_score":
            away_score,

        "home_score":
            home_score,

        "final":
            final,

        "status":
            str(
                status_type.get(
                    "description",
                    name,
                )
            ),
    }


def fetch_core_date(
    date,
):

    url = (
        CORE
        + "/events"
        + "?dates="
        + date.strftime(
            "%Y%m%d"
        )
        + "&limit=100"
    )


    data = get_json(
        url
    )


    rows = []


    for item in (
        data.get(
            "items"
        )
        or []
    ):

        try:

            event = ref_json(
                item
            )

            parsed = parse_core_event(
                event
            )

            if parsed:
                rows.append(
                    parsed
                )

        except Exception as exc:

            print(
                "CORE EVENT WARNING:",
                type(
                    exc
                ).__name__,
                str(
                    exc
                )[:120],
            )


    return rows


# =========================================================
# GAME RESULT HISTORY
# =========================================================

def relevant_dates(
    ledger,
):

    dates = set()

    for value in ledger[
        "start"
    ].fillna(""):

        dt = parse_dt(
            value
        )

        if pd.isna(dt):
            continue

        base = dt.date()

        for offset in [
            -1,
            0,
            1,
        ]:

            dates.add(
                base
                + timedelta(
                    days=offset
                )
            )

    return sorted(
        dates
    )


def refresh_game_results(
    ledger,
):

    old = pd.DataFrame()

    if RESULT_HISTORY.exists():

        old = pd.read_csv(
            RESULT_HISTORY,
            low_memory=False,
        )


    new_rows = []


    for date in relevant_dates(
        ledger
    ):

        try:

            rows = fetch_core_date(
                date
            )

            new_rows.extend(
                rows
            )

            print(
                "ESPN CORE",
                date,
                "=>",
                len(
                    rows
                ),
                "events",
            )

        except Exception as exc:

            print(
                "ESPN CORE DATE WARNING:",
                date,
                type(
                    exc
                ).__name__,
                str(
                    exc
                )[:150],
            )


    new = pd.DataFrame(
        new_rows
    )


    parts = [
        x
        for x in [
            old,
            new,
        ]
        if not x.empty
    ]


    if not parts:

        return pd.DataFrame(
            columns=[
                "espn_event_id",
                "start",
                "week",
                "away_team",
                "home_team",
                "away_score",
                "home_score",
                "final",
                "status",
            ]
        )


    games = pd.concat(
        parts,
        ignore_index=True,
        sort=False,
    )


    games["espn_event_id"] = (
        games[
            "espn_event_id"
        ]
        .fillna("")
        .astype(str)
    )


    games["_final_rank"] = (
        games[
            "final"
        ]
        .astype(str)
        .str.lower()
        .isin(
            [
                "true",
                "1",
            ]
        )
        .astype(int)
    )


    games = (
        games
        .sort_values(
            [
                "espn_event_id",
                "_final_rank",
            ]
        )
        .drop_duplicates(
            "espn_event_id",
            keep="last",
        )
        .drop(
            columns=[
                "_final_rank"
            ]
        )
    )


    games.to_csv(
        RESULT_HISTORY,
        index=False,
    )


    return games


# =========================================================
# GAME MATCHING
# =========================================================

def final_bool(
    value,
):

    return str(
        value
    ).lower() in {
        "true",
        "1",
        "yes",
    }


def row_payload(
    ledger_row,
):

    raw = ledger_row.get(
        "payload_json",
        "",
    )

    try:
        return json.loads(
            raw
        )

    except Exception:
        return {}


def find_game(
    ledger_row,
    games,
):

    payload = row_payload(
        ledger_row
    )


    start = parse_dt(
        ledger_row.get(
            "start"
        )
        or payload.get(
            "start"
        )
        or payload.get(
            "start_dfs"
        )
        or payload.get(
            "start_sportsbook"
        )
    )


    team = team_abbr(
        ledger_row.get(
            "team"
        )
        or payload.get(
            "identity_team"
        )
        or payload.get(
            "player_team"
        )
        or payload.get(
            "prop_team"
        )
    )


    away = team_abbr(
        payload.get(
            "away_team"
        )
    )

    home = team_abbr(
        payload.get(
            "home_team"
        )
    )


    candidates = games.copy()


    if (
        away
        and home
    ):

        candidates = candidates[
            (
                candidates[
                    "away_team"
                ].eq(
                    away
                )
                &
                candidates[
                    "home_team"
                ].eq(
                    home
                )
            )
            |
            (
                candidates[
                    "away_team"
                ].eq(
                    home
                )
                &
                candidates[
                    "home_team"
                ].eq(
                    away
                )
            )
        ]


    elif team:

        candidates = candidates[
            candidates[
                "away_team"
            ].eq(
                team
            )
            |
            candidates[
                "home_team"
            ].eq(
                team
            )
        ]


    if candidates.empty:
        return None


    if not pd.isna(
        start
    ):

        candidates = (
            candidates
            .copy()
        )

        candidates[
            "_start"
        ] = pd.to_datetime(
            candidates[
                "start"
            ],
            utc=True,
            errors="coerce",
        )

        candidates[
            "_delta"
        ] = (
            candidates[
                "_start"
            ]
            - start
        ).abs()


        candidates = (
            candidates
            .sort_values(
                "_delta"
            )
        )


        if not candidates.empty:

            best = candidates.iloc[
                0
            ]

            if (
                pd.notna(
                    best[
                        "_delta"
                    ]
                )
                and best[
                    "_delta"
                ]
                > pd.Timedelta(
                    days=2
                )
            ):
                return None


    return candidates.iloc[
        0
    ].to_dict()


# =========================================================
# PLAYER STATS
# =========================================================

MARKET_TO_STAT = {
    "PLAYER_TOTAL_INTERCEPTIONS":
        "passing_interceptions",

    "PLAYER_TOTAL_PASS_ATTEMPTS":
        "attempts",

    "PLAYER_TOTAL_PASS_COMPLETIONS":
        "completions",

    "PLAYER_TOTAL_PASS_TDS":
        "passing_tds",

    "PLAYER_TOTAL_PASS_YARDS":
        "passing_yards",

    "PLAYER_TOTAL_RECEPTIONS":
        "receptions",

    "PLAYER_TOTAL_REC_YARDS":
        "receiving_yards",

    "PLAYER_TOTAL_REC_TDS":
        "receiving_tds",

    "PLAYER_TOTAL_RUSH_ATTEMPTS":
        "carries",

    "PLAYER_TOTAL_RUSH_YARDS":
        "rushing_yards",

    "PLAYER_TOTAL_RUSH_TDS":
        "rushing_tds",
}


def load_player_stats():

    if not PLAYER_STATS.exists():

        return pd.DataFrame()


    stats = pd.read_csv(
        PLAYER_STATS,
        low_memory=False,
    ).copy()


    if "player_display_name" in stats.columns:

        stats[
            "_player_key"
        ] = (
            stats[
                "player_display_name"
            ]
            .map(
                player_norm
            )
        )

    else:

        stats[
            "_player_key"
        ] = ""


    stats[
        "_team"
    ] = (
        stats[
            "team"
        ]
        .map(
            team_abbr
        )
        if "team"
        in stats.columns
        else ""
    )


    stats[
        "_opp"
    ] = (
        stats[
            "opponent_team"
        ]
        .map(
            team_abbr
        )
        if "opponent_team"
        in stats.columns
        else ""
    )


    return stats


def find_player_result(
    ledger_row,
    game,
    stats,
):

    if stats.empty:
        return None


    payload = row_payload(
        ledger_row
    )


    player = (
        ledger_row.get(
            "player"
        )
        or payload.get(
            "canonical_player_identity"
        )
        or payload.get(
            "player"
        )
        or payload.get(
            "player_dfs"
        )
        or payload.get(
            "player_sportsbook"
        )
    )


    player_key = player_norm(
        player
    )


    if not player_key:
        return None


    team = team_abbr(
        ledger_row.get(
            "team"
        )
        or payload.get(
            "identity_team"
        )
        or payload.get(
            "player_team"
        )
        or payload.get(
            "prop_team"
        )
    )


    x = stats[
        stats[
            "_player_key"
        ].eq(
            player_key
        )
    ].copy()


    if team:

        x = x[
            x[
                "_team"
            ].eq(
                team
            )
        ]


    if x.empty:
        return None


    if game:

        week = num(
            game.get(
                "week"
            )
        )

        if (
            week is not None
            and "week"
            in x.columns
        ):

            by_week = x[
                pd.to_numeric(
                    x[
                        "week"
                    ],
                    errors="coerce",
                ).eq(
                    week
                )
            ]

            if not by_week.empty:
                x = by_week


        away = team_abbr(
            game.get(
                "away_team"
            )
        )

        home = team_abbr(
            game.get(
                "home_team"
            )
        )


        opponent = ""

        if team == away:
            opponent = home

        elif team == home:
            opponent = away


        if opponent:

            by_opp = x[
                x[
                    "_opp"
                ].eq(
                    opponent
                )
            ]

            if not by_opp.empty:
                x = by_opp


    if len(
        x
    ) != 1:

        return None


    return x.iloc[
        0
    ].to_dict()


# =========================================================
# GRADING HELPERS
# =========================================================

def compare_line(
    actual,
    line,
    side,
):

    actual = num(
        actual
    )

    line = num(
        line
    )

    side = str(
        side or ""
    ).upper()


    if (
        actual is None
        or line is None
    ):
        return (
            "UNRESOLVED",
            None,
        )


    margin = (
        actual
        - line
    )


    if actual == line:

        return (
            "PUSH",
            margin,
        )


    if side == "OVER":

        return (
            "WIN"
            if actual > line
            else "LOSS",
            margin,
        )


    if side == "UNDER":

        return (
            "WIN"
            if actual < line
            else "LOSS",
            margin,
        )


    return (
        "UNSUPPORTED_SIDE",
        margin,
    )


def grade_prop(
    ledger_row,
    games,
    stats,
):

    payload = row_payload(
        ledger_row
    )


    game = find_game(
        ledger_row,
        games,
    )


    if not game:

        return {
            "grade":
                "PENDING_GAME_MATCH",

            "context_status":
                "NO_GAME_MATCH",
        }


    if not final_bool(
        game.get(
            "final"
        )
    ):

        return {
            "grade":
                "PENDING",

            "context_status":
                "GAME_NOT_FINAL",

            "espn_event_id":
                game.get(
                    "espn_event_id",
                    "",
                ),

            "week":
                game.get(
                    "week",
                    "",
                ),
        }


    market = str(
        ledger_row.get(
            "market"
        )
        or payload.get(
            "market_subtype"
        )
        or payload.get(
            "market"
        )
        or ""
    ).upper()


    stat_col = MARKET_TO_STAT.get(
        market
    )


    if not stat_col:

        return {
            "grade":
                "UNSUPPORTED_MARKET",

            "context_status":
                "NO_STAT_MAPPING",

            "espn_event_id":
                game.get(
                    "espn_event_id",
                    "",
                ),

            "week":
                game.get(
                    "week",
                    "",
                ),
        }


    player_result = find_player_result(
        ledger_row,
        game,
        stats,
    )


    if not player_result:

        return {
            "grade":
                "UNRESOLVED_PLAYER_RESULT",

            "context_status":
                "FINAL_GAME_NO_UNIQUE_STAT_ROW",

            "espn_event_id":
                game.get(
                    "espn_event_id",
                    "",
                ),

            "week":
                game.get(
                    "week",
                    "",
                ),

            "stat_column":
                stat_col,
        }


    actual = num(
        player_result.get(
            stat_col
        )
    )


    side = (
        ledger_row.get(
            "side"
        )
        or ledger_row.get(
            "selection"
        )
        or payload.get(
            "side"
        )
    )


    line = (
        ledger_row.get(
            "line"
        )
        or payload.get(
            "line"
        )
    )


    grade, margin = compare_line(
        actual,
        line,
        side,
    )


    return {
        "grade":
            grade,

        "context_status":
            "PLAYED_STAT_VERIFIED",

        "actual_value":
            actual,

        "line_margin":
            margin,

        "stat_column":
            stat_col,

        "espn_event_id":
            game.get(
                "espn_event_id",
                "",
            ),

        "week":
            game.get(
                "week",
                "",
            ),

        "game_status":
            game.get(
                "status",
                "",
            ),

        "home_score":
            game.get(
                "home_score",
                "",
            ),

        "away_score":
            game.get(
                "away_score",
                "",
            ),
    }


def selection_team(
    selection,
    game,
):

    value = str(
        selection or ""
    ).strip()


    normalized = text_norm(
        value
    )


    if normalized == "HOME":

        return team_abbr(
            game.get(
                "home_team"
            )
        )


    if normalized == "AWAY":

        return team_abbr(
            game.get(
                "away_team"
            )
        )


    return team_abbr(
        value
    )


def grade_game(
    ledger_row,
    games,
):

    payload = row_payload(
        ledger_row
    )


    game = find_game(
        ledger_row,
        games,
    )


    if not game:

        return {
            "grade":
                "PENDING_GAME_MATCH",

            "context_status":
                "NO_GAME_MATCH",
        }


    if not final_bool(
        game.get(
            "final"
        )
    ):

        return {
            "grade":
                "PENDING",

            "context_status":
                "GAME_NOT_FINAL",

            "espn_event_id":
                game.get(
                    "espn_event_id",
                    "",
                ),

            "week":
                game.get(
                    "week",
                    "",
                ),
        }


    market = str(
        ledger_row.get(
            "market"
        )
        or payload.get(
            "market"
        )
        or ""
    ).upper()


    selection = (
        ledger_row.get(
            "selection"
        )
        or payload.get(
            "selection"
        )
    )


    line = num(
        ledger_row.get(
            "line"
        )
        or payload.get(
            "line"
        )
    )


    home = team_abbr(
        game.get(
            "home_team"
        )
    )

    away = team_abbr(
        game.get(
            "away_team"
        )
    )


    hs = num(
        game.get(
            "home_score"
        )
    )

    aws = num(
        game.get(
            "away_score"
        )
    )


    base = {
        "espn_event_id":
            game.get(
                "espn_event_id",
                "",
            ),

        "week":
            game.get(
                "week",
                "",
            ),

        "game_status":
            game.get(
                "status",
                "",
            ),

        "home_score":
            hs,

        "away_score":
            aws,

        "context_status":
            "FINAL_SCORE_VERIFIED",
    }


    if (
        hs is None
        or aws is None
    ):

        return {
            **base,

            "grade":
                "UNRESOLVED_SCORE",
        }


    if (
        "MONEYLINE" in market
        or market in {
            "ML",
            "H2H",
            "WINNER",
        }
    ):

        pick = selection_team(
            selection,
            game,
        )


        if not pick:

            return {
                **base,

                "grade":
                    "UNRESOLVED_SELECTION",
            }


        if hs == aws:

            result = "PUSH"

        else:

            winner = (
                home
                if hs > aws
                else away
            )

            result = (
                "WIN"
                if pick == winner
                else "LOSS"
            )


        return {
            **base,

            "grade":
                result,

            "actual_value":
                (
                    hs - aws
                    if pick == home
                    else aws - hs
                ),
        }


    if "SPREAD" in market:

        pick = selection_team(
            selection,
            game,
        )


        if (
            not pick
            or line is None
        ):

            return {
                **base,

                "grade":
                    "UNRESOLVED_SELECTION",
            }


        if pick == home:

            adjusted = (
                hs
                + line
                - aws
            )

        elif pick == away:

            adjusted = (
                aws
                + line
                - hs
            )

        else:

            return {
                **base,

                "grade":
                    "UNRESOLVED_SELECTION",
            }


        if adjusted > 0:

            grade = "WIN"

        elif adjusted < 0:

            grade = "LOSS"

        else:

            grade = "PUSH"


        return {
            **base,

            "grade":
                grade,

            "actual_value":
                adjusted,

            "line_margin":
                adjusted,
        }


    if "TOTAL" in market:

        side = str(
            selection
            or payload.get(
                "side",
                ""
            )
        ).upper()


        total = (
            hs
            + aws
        )


        grade, margin = compare_line(
            total,
            line,
            side,
        )


        return {
            **base,

            "grade":
                grade,

            "actual_value":
                total,

            "line_margin":
                margin,
        }


    return {
        **base,

        "grade":
            "UNSUPPORTED_MARKET",

        "context_status":
            "GAME_MARKET_NOT_MAPPED",
    }


# =========================================================
# PARLAY MATCHING
# =========================================================

def norm_market(
    value,
):

    return text_norm(
        value
    )


def same_line(
    a,
    b,
):

    x = num(
        a
    )

    y = num(
        b
    )

    if (
        x is None
        or y is None
    ):
        return str(
            a or ""
        ) == str(
            b or ""
        )

    return abs(
        x - y
    ) < 0.001


def find_leg_grade(
    payload,
    leg_number,
    graded_non_parlay,
):

    kind = str(
        payload.get(
            f"leg{leg_number}_kind",
            "",
        )
    ).upper()


    player = player_norm(
        payload.get(
            f"leg{leg_number}_player"
        )
    )


    market = norm_market(
        payload.get(
            f"leg{leg_number}_market"
        )
    )


    selection = text_norm(
        payload.get(
            f"leg{leg_number}_selection"
        )
    )


    line = payload.get(
        f"leg{leg_number}_line"
    )


    if "PRIZE" in kind:

        lanes = {
            "PRIZEPICKS"
        }

    elif "PROP" in kind:

        lanes = {
            "PROP",
            "PRIZEPICKS",
        }

    elif "GAME" in kind:

        lanes = {
            "GAME"
        }

    else:

        lanes = {
            "GAME",
            "PROP",
            "PRIZEPICKS",
        }


    candidates = []


    for row in graded_non_parlay:

        if row.get(
            "lane"
        ) not in lanes:
            continue


        if player:

            if player_norm(
                row.get(
                    "player"
                )
            ) != player:
                continue


        if market:

            if norm_market(
                row.get(
                    "market"
                )
            ) != market:
                continue


        row_selection = text_norm(
            row.get(
                "selection"
            )
            or row.get(
                "side"
            )
        )


        if (
            selection
            and row_selection
            and selection
            != row_selection
        ):
            continue


        if (
            str(
                line or ""
            ).strip()
            and not same_line(
                line,
                row.get(
                    "line"
                ),
            )
        ):
            continue


        candidates.append(
            row
        )


    if not candidates:

        return (
            "UNRESOLVED",
            "",
        )


    candidates = sorted(
        candidates,
        key=lambda r:
            str(
                r.get(
                    "snapshot_at",
                    ""
                )
            ),
        reverse=True,
    )


    result = candidates[
        0
    ]


    return (
        result.get(
            "grade",
            "UNRESOLVED",
        ),
        result.get(
            "recommendation_key",
            "",
        ),
    )


def grade_parlay(
    ledger_row,
    graded_non_parlay,
):

    payload = row_payload(
        ledger_row
    )


    leg1, key1 = find_leg_grade(
        payload,
        1,
        graded_non_parlay,
    )


    leg2, key2 = find_leg_grade(
        payload,
        2,
        graded_non_parlay,
    )


    grades = [
        leg1,
        leg2,
    ]


    if "LOSS" in grades:

        result = "LOSS"


    elif all(
        x == "WIN"
        for x in grades
    ):

        result = "WIN"


    elif any(
        x.startswith(
            "PENDING"
        )
        for x in grades
    ):

        result = "PENDING"


    elif "PUSH" in grades:

        result = "PUSH_PRESENT"


    elif any(
        x in {
            "UNRESOLVED",
            "UNRESOLVED_PLAYER_RESULT",
            "UNSUPPORTED_MARKET",
            "UNSUPPORTED_SIDE",
        }
        for x in grades
    ):

        result = "UNRESOLVED"


    else:

        result = "PENDING"


    return {
        "grade":
            result,

        "context_status":
            "PARLAY_GRADED_FROM_LEGS",

        "leg1_grade":
            leg1,

        "leg2_grade":
            leg2,

        "leg1_recommendation_key":
            key1,

        "leg2_recommendation_key":
            key2,
    }


# =========================================================
# MAIN
# =========================================================

def main():

    if not LEDGER.exists():

        raise SystemExit(
            "NFL recommendation ledger missing."
        )


    ledger = pd.read_csv(
        LEDGER,
        low_memory=False,
    )


    print(
        "LEDGER ROWS:",
        len(
            ledger
        ),
    )


    games = refresh_game_results(
        ledger
    )


    print(
        "RESULT HISTORY ROWS:",
        len(
            games
        ),
    )


    stats = load_player_stats()


    print(
        "PLAYER STAT ROWS:",
        len(
            stats
        ),
    )


    graded_rows = []


    # First pass:
    # game / prop / PrizePicks
    for _, row in ledger.iterrows():

        lane = str(
            row.get(
                "lane",
                "",
            )
        ).upper()


        base = row.to_dict()


        if lane == "GAME":

            result = grade_game(
                base,
                games,
            )


        elif lane in {
            "PROP",
            "PRIZEPICKS",
        }:

            result = grade_prop(
                base,
                games,
                stats,
            )


        elif lane == "PARLAY":

            continue


        else:

            result = {
                "grade":
                    "UNSUPPORTED_LANE",

                "context_status":
                    "UNKNOWN_LANE",
            }


        graded_rows.append(
            {
                **base,
                **result,
            }
        )


    # One latest row per non-parlay key
    latest_non_parlay = (
        pd.DataFrame(
            graded_rows
        )
        .sort_values(
            "snapshot_at"
        )
        .drop_duplicates(
            "recommendation_key",
            keep="last",
        )
        .to_dict(
            "records"
        )
        if graded_rows
        else []
    )


    # Second pass:
    # parlays derive from their legs
    for _, row in ledger.iterrows():

        lane = str(
            row.get(
                "lane",
                "",
            )
        ).upper()


        if lane != "PARLAY":
            continue


        base = row.to_dict()


        result = grade_parlay(
            base,
            latest_non_parlay,
        )


        graded_rows.append(
            {
                **base,
                **result,
            }
        )


    graded = pd.DataFrame(
        graded_rows
    )


    graded = graded.sort_values(
        [
            "snapshot_at",
            "lane",
        ]
    )


    graded.to_csv(
        GRADED_HISTORY,
        index=False,
    )


    latest = (
        graded
        .sort_values(
            "snapshot_at"
        )
        .drop_duplicates(
            "recommendation_key",
            keep="last",
        )
        .copy()
    )


    latest.to_csv(
        GRADED_LATEST,
        index=False,
    )


    settled = latest[
        latest[
            "grade"
        ].isin(
            [
                "WIN",
                "LOSS",
                "PUSH",
            ]
        )
    ].copy()


    performance = pd.DataFrame()


    if not settled.empty:

        group_cols = [
            "lane",
            "decision",
            "market",
        ]


        for col in group_cols:

            if col not in settled.columns:
                settled[
                    col
                ] = ""


        performance = (
            settled
            .groupby(
                group_cols,
                dropna=False,
            )
            .agg(
                samples=(
                    "grade",
                    "size",
                ),

                wins=(
                    "grade",
                    lambda x:
                        int(
                            (
                                x == "WIN"
                            ).sum()
                        ),
                ),

                losses=(
                    "grade",
                    lambda x:
                        int(
                            (
                                x == "LOSS"
                            ).sum()
                        ),
                ),

                pushes=(
                    "grade",
                    lambda x:
                        int(
                            (
                                x == "PUSH"
                            ).sum()
                        ),
                ),
            )
            .reset_index()
        )


        decisions = (
            performance[
                "wins"
            ]
            + performance[
                "losses"
            ]
        )


        performance[
            "hit_rate"
        ] = (
            performance[
                "wins"
            ]
            / decisions.where(
                decisions > 0
            )
        )


    performance.to_csv(
        PERFORMANCE,
        index=False,
    )


    counts = (
        latest[
            "grade"
        ]
        .fillna(
            "UNKNOWN"
        )
        .value_counts()
        .to_dict()
    )


    lane_counts = (
        latest
        .groupby(
            [
                "lane",
                "grade",
            ],
            dropna=False,
        )
        .size()
        .to_dict()
    )


    lane_counts = {
        f"{lane}|{grade}":
            int(
                count
            )

        for (
            lane,
            grade
        ), count
        in lane_counts.items()
    }


    summary = {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "ledger_rows":
            int(
                len(
                    ledger
                )
            ),

        "unique_recommendations":
            int(
                len(
                    latest
                )
            ),

        "game_result_rows":
            int(
                len(
                    games
                )
            ),

        "player_stat_rows":
            int(
                len(
                    stats
                )
            ),

        "settled_recommendations":
            int(
                len(
                    settled
                )
            ),

        "grade_counts":
            {
                str(
                    k
                ):
                int(
                    v
                )

                for k, v
                in counts.items()
            },

        "lane_grade_counts":
            lane_counts,

        "learning_policy":
            (
                "DESCRIPTIVE_ONLY_"
                "NO_AUTOMATIC_WEIGHT_CHANGES"
            ),
    }


    SUMMARY.write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
    )


    print()
    print(
        "UNIQUE RECOMMENDATIONS:",
        len(
            latest
        ),
    )


    print(
        "SETTLED:",
        len(
            settled
        ),
    )


    print()
    print(
        "GRADE COUNTS:"
    )


    for grade, count in (
        latest[
            "grade"
        ]
        .fillna(
            "UNKNOWN"
        )
        .value_counts()
        .items()
    ):

        print(
            grade,
            int(
                count
            ),
        )


    print()
    print(
        "SPORTS HULK NFL RESULT GRADER: DONE"
    )


if __name__ == "__main__":
    main()
