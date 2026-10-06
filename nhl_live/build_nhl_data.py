#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, timezone
import argparse
import json
import math
import time

import pandas as pd
import requests


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

NHL = ROOT / "nhl_live"
DERIVED = NHL / "derived"
HISTORY = NHL / "history"
CHECKPOINTS = NHL / "checkpoints"
RECEIPTS = NHL / "receipts"


CURRENT_GAMES = (
    DERIVED
    / "NHL_GAMES_CURRENT.csv"
)

RESULTS = (
    HISTORY
    / "NHL_RESULTS_HISTORY.csv"
)

GAME_HISTORY = (
    HISTORY
    / "NHL_GAME_HISTORY.csv"
)

PLAYER_HISTORY = (
    HISTORY
    / "NHL_PLAYER_GAME_HISTORY.csv"
)

TEAM_HISTORY = (
    HISTORY
    / "NHL_TEAM_GAME_HISTORY.csv"
)

GOALIE_HISTORY = (
    HISTORY
    / "NHL_GOALIE_GAME_HISTORY.csv"
)

PLAYER_CONTEXT = (
    DERIVED
    / "NHL_PLAYER_CONTEXT.csv"
)

GOALIE_CONTEXT = (
    DERIVED
    / "NHL_GOALIE_CONTEXT.csv"
)

ROSTERS = (
    DERIVED
    / "NHL_CURRENT_ROSTERS.csv"
)

CHECKPOINT = (
    CHECKPOINTS
    / "NHL_HISTORY_CHECKPOINT.json"
)


BASE = (
    "https://api-web.nhle.com/v1"
)

HEADERS = {
    "User-Agent":
        "Sports-HULK/1.0",
    "Accept":
        "application/json",
}


TEAMS = [
    "ANA",
    "BOS",
    "BUF",
    "CAR",
    "CBJ",
    "CGY",
    "CHI",
    "COL",
    "DAL",
    "DET",
    "EDM",
    "FLA",
    "LAK",
    "MIN",
    "MTL",
    "NJD",
    "NSH",
    "NYI",
    "NYR",
    "OTT",
    "PHI",
    "PIT",
    "SEA",
    "SJS",
    "STL",
    "TBL",
    "TOR",
    "UTA",
    "VAN",
    "VGK",
    "WPG",
    "WSH",
]


SESSION = requests.Session()
SESSION.headers.update(
    HEADERS
)


def get_json(
    url,
    retries=3,
):

    last = None

    for attempt in range(
        retries
    ):

        try:

            r = SESSION.get(
                url,
                timeout=30,
            )

            r.raise_for_status()

            return r.json()

        except Exception as exc:

            last = exc

            if attempt + 1 < retries:

                time.sleep(
                    1.25
                    * (
                        attempt + 1
                    )
                )

    raise last


def clean(
    value,
):

    if value is None:
        return ""

    if isinstance(
        value,
        dict,
    ):

        return str(
            value.get(
                "default",
                ""
            )
        ).strip()

    return str(
        value
    ).strip()


def number(
    value,
):

    try:

        if value in {
            None,
            "",
            "--",
        }:

            return None

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


def toi_minutes(
    value,
):

    value = clean(
        value
    )

    if not value:
        return None

    if ":" not in value:
        return number(
            value
        )

    try:

        minute, second = (
            value.split(
                ":",
                1,
            )
        )

        return (
            float(
                minute
            )
            + float(
                second
            )
            / 60.0
        )

    except Exception:

        return None


def final_state(
    state,
):

    return str(
        state or ""
    ).upper() in {
        "OFF",
        "FINAL",
    }


def game_row(
    game,
):

    away = (
        game.get(
            "awayTeam"
        )
        or {}
    )

    home = (
        game.get(
            "homeTeam"
        )
        or {}
    )

    state = clean(
        game.get(
            "gameState"
        )
    ).upper()


    return {
        "event_id":
            clean(
                game.get(
                    "id"
                )
            ),

        "season":
            game.get(
                "season"
            ),

        "game_type":
            game.get(
                "gameType"
            ),

        "game_date":
            clean(
                game.get(
                    "gameDate"
                )
            ),

        "start":
            clean(
                game.get(
                    "startTimeUTC"
                )
            ),

        "away_team_id":
            away.get(
                "id"
            ),

        "away_team":
            clean(
                away.get(
                    "abbrev"
                )
            ),

        "away_team_name":
            (
                clean(
                    away.get(
                        "placeName"
                    )
                )
                + " "
                + clean(
                    away.get(
                        "commonName"
                    )
                )
            ).strip(),

        "away_score":
            number(
                away.get(
                    "score"
                )
            ),

        "home_team_id":
            home.get(
                "id"
            ),

        "home_team":
            clean(
                home.get(
                    "abbrev"
                )
            ),

        "home_team_name":
            (
                clean(
                    home.get(
                        "placeName"
                    )
                )
                + " "
                + clean(
                    home.get(
                        "commonName"
                    )
                )
            ).strip(),

        "home_score":
            number(
                home.get(
                    "score"
                )
            ),

        "game_state":
            state,

        "completed":
            final_state(
                state
            ),

        "venue":
            clean(
                game.get(
                    "venue"
                )
            ),
    }


def fetch_score_date(
    date,
):

    payload = get_json(
        BASE
        + "/score/"
        + date.strftime(
            "%Y-%m-%d"
        )
    )

    return [
        game_row(
            game
        )
        for game in (
            payload.get(
                "games"
            )
            or []
        )
    ]


def fetch_schedule_week(
    date,
):

    payload = get_json(
        BASE
        + "/schedule/"
        + date.strftime(
            "%Y-%m-%d"
        )
    )

    rows = []


    for block in (
        payload.get(
            "gameWeek"
        )
        or []
    ):

        block_date = clean(
            block.get(
                "date"
            )
        )

        for game in (
            block.get(
                "games"
            )
            or []
        ):

            # NHL schedule responses carry the
            # calendar date on the gameWeek block.
            # Individual games may omit gameDate.
            game = dict(
                game
            )

            if (
                not clean(
                    game.get(
                        "gameDate"
                    )
                )
                and block_date
            ):

                game[
                    "gameDate"
                ] = block_date

            rows.append(
                game_row(
                    game
                )
            )


    return rows


def merge_history(
    path,
    new,
    keys,
):

    old = pd.DataFrame()


    if path.exists():

        try:

            old = pd.read_csv(
                path,
                low_memory=False,
            )

        except Exception:

            pass


    parts = [
        x
        for x in [
            old,
            new,
        ]
        if not x.empty
    ]


    if not parts:

        return pd.DataFrame()


    result = pd.concat(
        parts,
        ignore_index=True,
        sort=False,
    )


    usable = [
        key
        for key in keys
        if key in result.columns
    ]


    if usable:

        result = result.drop_duplicates(
            usable,
            keep="last",
        )


    result.to_csv(
        path,
        index=False,
    )


    try:

        result.to_parquet(
            path.with_suffix(
                ".parquet"
            ),
            index=False,
        )

    except Exception:
        pass


    return result


def player_rows_from_boxscore(
    game,
    box,
):

    event_id = game[
        "event_id"
    ]

    results = []
    goalies = []
    team_results = []


    pstats = (
        box.get(
            "playerByGameStats"
        )
        or {}
    )


    for side, team_side in [
        (
            "awayTeam",
            "away",
        ),
        (
            "homeTeam",
            "home",
        ),
    ]:

        team = game[
            team_side
            + "_team"
        ]

        opponent = game[
            (
                "home"
                if team_side
                == "away"
                else "away"
            )
            + "_team"
        ]


        block = (
            pstats.get(
                side
            )
            or {}
        )


        team_sog = 0.0
        team_hits = 0.0
        team_blocks = 0.0
        team_pp_goals = 0.0
        team_giveaways = 0.0
        team_takeaways = 0.0


        for group in [
            "forwards",
            "defense",
        ]:

            for player in (
                block.get(
                    group
                )
                or []
            ):

                row = {
                    "event_id":
                        event_id,

                    "game_date":
                        game[
                            "game_date"
                        ],

                    "start":
                        game[
                            "start"
                        ],

                    "season":
                        game[
                            "season"
                        ],

                    "game_type":
                        game[
                            "game_type"
                        ],

                    "team":
                        team,

                    "opponent":
                        opponent,

                    "player_id":
                        player.get(
                            "playerId"
                        ),

                    "player":
                        clean(
                            player.get(
                                "name"
                            )
                        ),

                    "position":
                        clean(
                            player.get(
                                "position"
                            )
                        ),

                    "role":
                        "SKATER",

                    "goals":
                        number(
                            player.get(
                                "goals"
                            )
                        ),

                    "assists":
                        number(
                            player.get(
                                "assists"
                            )
                        ),

                    "points":
                        number(
                            player.get(
                                "points"
                            )
                        ),

                    "plus_minus":
                        number(
                            player.get(
                                "plusMinus"
                            )
                        ),

                    "pim":
                        number(
                            player.get(
                                "pim"
                            )
                        ),

                    "hits":
                        number(
                            player.get(
                                "hits"
                            )
                        ),

                    "power_play_goals":
                        number(
                            player.get(
                                "powerPlayGoals"
                            )
                        ),

                    "shots_on_goal":
                        number(
                            player.get(
                                "sog"
                            )
                        ),

                    "faceoff_win_pct":
                        number(
                            player.get(
                                "faceoffWinningPctg"
                            )
                        ),

                    "toi":
                        clean(
                            player.get(
                                "toi"
                            )
                        ),

                    "toi_minutes":
                        toi_minutes(
                            player.get(
                                "toi"
                            )
                        ),

                    "blocked_shots":
                        number(
                            player.get(
                                "blockedShots"
                            )
                        ),

                    "shifts":
                        number(
                            player.get(
                                "shifts"
                            )
                        ),

                    "giveaways":
                        number(
                            player.get(
                                "giveaways"
                            )
                        ),

                    "takeaways":
                        number(
                            player.get(
                                "takeaways"
                            )
                        ),
                }


                results.append(
                    row
                )


                team_sog += (
                    row[
                        "shots_on_goal"
                    ]
                    or 0
                )

                team_hits += (
                    row[
                        "hits"
                    ]
                    or 0
                )

                team_blocks += (
                    row[
                        "blocked_shots"
                    ]
                    or 0
                )

                team_pp_goals += (
                    row[
                        "power_play_goals"
                    ]
                    or 0
                )

                team_giveaways += (
                    row[
                        "giveaways"
                    ]
                    or 0
                )

                team_takeaways += (
                    row[
                        "takeaways"
                    ]
                    or 0
                )


        goalie_rows = []


        for goalie in (
            block.get(
                "goalies"
            )
            or []
        ):

            row = {
                "event_id":
                    event_id,

                "game_date":
                    game[
                        "game_date"
                    ],

                "start":
                    game[
                        "start"
                    ],

                "season":
                    game[
                        "season"
                    ],

                "game_type":
                    game[
                        "game_type"
                    ],

                "team":
                    team,

                "opponent":
                    opponent,

                "player_id":
                    goalie.get(
                        "playerId"
                    ),

                "player":
                    clean(
                        goalie.get(
                            "name"
                        )
                    ),

                "position":
                    "G",

                "starter":
                    bool(
                        goalie.get(
                            "starter"
                        )
                    ),

                "decision":
                    clean(
                        goalie.get(
                            "decision"
                        )
                    ),

                "toi":
                    clean(
                        goalie.get(
                            "toi"
                        )
                    ),

                "toi_minutes":
                    toi_minutes(
                        goalie.get(
                            "toi"
                        )
                    ),

                "shots_against":
                    number(
                        goalie.get(
                            "shotsAgainst"
                        )
                    ),

                "saves":
                    number(
                        goalie.get(
                            "saves"
                        )
                    ),

                "save_pct":
                    number(
                        goalie.get(
                            "savePctg"
                        )
                    ),

                "goals_against":
                    number(
                        goalie.get(
                            "goalsAgainst"
                        )
                    ),
            }


            goalies.append(
                row
            )

            goalie_rows.append(
                row
            )


        starter = None


        starters = [
            g
            for g in goalie_rows
            if g[
                "starter"
            ]
        ]


        if starters:

            starter = max(
                starters,
                key=lambda x:
                    x[
                        "toi_minutes"
                    ]
                    or 0,
            )


        elif goalie_rows:

            starter = max(
                goalie_rows,
                key=lambda x:
                    x[
                        "toi_minutes"
                    ]
                    or 0,
            )


        goals_for = game[
            team_side
            + "_score"
        ]


        goals_against = game[
            (
                "home"
                if team_side
                == "away"
                else "away"
            )
            + "_score"
        ]


        team_results.append({
            "event_id":
                event_id,

            "game_date":
                game[
                    "game_date"
                ],

            "start":
                game[
                    "start"
                ],

            "season":
                game[
                    "season"
                ],

            "game_type":
                game[
                    "game_type"
                ],

            "team":
                team,

            "opponent":
                opponent,

            "goals_for":
                goals_for,

            "goals_against":
                goals_against,

            "win":
                (
                    float(
                        goals_for
                        > goals_against
                    )
                    if (
                        goals_for
                        is not None
                        and goals_against
                        is not None
                    )
                    else None
                ),

            "shots_on_goal":
                team_sog,

            "hits":
                team_hits,

            "blocked_shots":
                team_blocks,

            "power_play_goals":
                team_pp_goals,

            "giveaways":
                team_giveaways,

            "takeaways":
                team_takeaways,

            "starting_goalie":
                (
                    starter[
                        "player"
                    ]
                    if starter
                    else ""
                ),

            "starting_goalie_id":
                (
                    starter[
                        "player_id"
                    ]
                    if starter
                    else ""
                ),

            "starting_goalie_save_pct":
                (
                    starter[
                        "save_pct"
                    ]
                    if starter
                    else None
                ),

            "starting_goalie_saves":
                (
                    starter[
                        "saves"
                    ]
                    if starter
                    else None
                ),

            "starting_goalie_shots_against":
                (
                    starter[
                        "shots_against"
                    ]
                    if starter
                    else None
                ),
        })


    return (
        pd.DataFrame(
            results
        ),
        pd.DataFrame(
            goalies
        ),
        pd.DataFrame(
            team_results
        ),
    )


def collect_rosters():

    rows = []


    for club in TEAMS:

        try:

            payload = get_json(
                BASE
                + "/roster/"
                + club
                + "/current"
            )

        except Exception as exc:

            print(
                "ROSTER WARNING:",
                club,
                type(
                    exc
                ).__name__,
            )

            continue


        groups = [
            (
                "forwards",
                payload.get(
                    "forwards"
                )
                or [],
            ),
            (
                "defensemen",
                payload.get(
                    "defensemen"
                )
                or [],
            ),
            (
                "goalies",
                payload.get(
                    "goalies"
                )
                or [],
            ),
        ]


        for group_name, players in groups:

            for player in players:

                first = clean(
                    player.get(
                        "firstName"
                    )
                )

                last = clean(
                    player.get(
                        "lastName"
                    )
                )

                rows.append({
                    "team":
                        club,

                    "player_id":
                        player.get(
                            "id"
                        ),

                    "player":
                        (
                            first
                            + " "
                            + last
                        ).strip(),

                    "position":
                        clean(
                            player.get(
                                "positionCode"
                            )
                        ),

                    "group":
                        group_name,

                    "sweater_number":
                        player.get(
                            "sweaterNumber"
                        ),

                    "shoots_catches":
                        clean(
                            player.get(
                                "shootsCatches"
                            )
                        ),

                    "height_in":
                        player.get(
                            "heightInInches"
                        ),

                    "weight_lb":
                        player.get(
                            "weightInPounds"
                        ),

                    "birth_date":
                        clean(
                            player.get(
                                "birthDate"
                            )
                        ),
                })


    roster = pd.DataFrame(
        rows
    )


    if not roster.empty:

        roster = roster.drop_duplicates(
            [
                "team",
                "player_id",
            ],
            keep="last",
        )


    roster.to_csv(
        ROSTERS,
        index=False,
    )


    return roster


def build_player_context():

    players = pd.DataFrame()


    if PLAYER_HISTORY.exists():

        players = pd.read_csv(
            PLAYER_HISTORY,
            low_memory=False,
        )


    if players.empty:

        pd.DataFrame().to_csv(
            PLAYER_CONTEXT,
            index=False,
        )

        return pd.DataFrame()


    # Context for NHL decisions uses
    # regular season + playoffs only.
    game_type = pd.to_numeric(
        players[
            "game_type"
        ],
        errors="coerce",
    )


    players = players[
        game_type.isin(
            [
                2,
                3,
            ]
        )
    ].copy()


    players[
        "start_dt"
    ] = pd.to_datetime(
        players[
            "start"
        ],
        utc=True,
        errors="coerce",
    )


    players = players.sort_values(
        [
            "player_id",
            "start_dt",
        ]
    )


    metrics = [
        "toi_minutes",
        "goals",
        "assists",
        "points",
        "shots_on_goal",
        "hits",
        "blocked_shots",
        "power_play_goals",
        "giveaways",
        "takeaways",
    ]


    rows = []


    for (
        player_id,
        player,
    ), group in players.groupby(
        [
            "player_id",
            "player",
        ],
        dropna=False,
    ):

        group = group.sort_values(
            "start_dt"
        )


        latest = group.iloc[
            -1
        ]


        row = {
            "player_id":
                player_id,

            "player":
                player,

            "team":
                latest.get(
                    "team",
                    "",
                ),

            "position":
                latest.get(
                    "position",
                    "",
                ),

            "games":
                len(
                    group
                ),

            "latest_event_id":
                latest.get(
                    "event_id",
                    "",
                ),

            "latest_start":
                latest.get(
                    "start",
                    "",
                ),
        }


        for metric in metrics:

            values = pd.to_numeric(
                group[
                    metric
                ],
                errors="coerce",
            )


            row[
                metric
                + "_season_avg"
            ] = values.mean()


            for n in [
                3,
                5,
                10,
                20,
            ]:

                row[
                    metric
                    + f"_l{n}_avg"
                ] = (
                    values
                    .tail(
                        n
                    )
                    .mean()
                )


        rows.append(
            row
        )


    context = pd.DataFrame(
        rows
    )


    context.to_csv(
        PLAYER_CONTEXT,
        index=False,
    )


    try:

        context.to_parquet(
            PLAYER_CONTEXT.with_suffix(
                ".parquet"
            ),
            index=False,
        )

    except Exception:
        pass


    return context


def build_goalie_context():

    goalies = pd.DataFrame()


    if GOALIE_HISTORY.exists():

        goalies = pd.read_csv(
            GOALIE_HISTORY,
            low_memory=False,
        )


    if goalies.empty:

        pd.DataFrame().to_csv(
            GOALIE_CONTEXT,
            index=False,
        )

        return pd.DataFrame()


    game_type = pd.to_numeric(
        goalies[
            "game_type"
        ],
        errors="coerce",
    )


    goalies = goalies[
        game_type.isin(
            [
                2,
                3,
            ]
        )
    ].copy()


    goalies[
        "start_dt"
    ] = pd.to_datetime(
        goalies[
            "start"
        ],
        utc=True,
        errors="coerce",
    )


    goalies = goalies.sort_values(
        [
            "player_id",
            "start_dt",
        ]
    )


    rows = []


    for (
        player_id,
        player,
    ), group in goalies.groupby(
        [
            "player_id",
            "player",
        ],
        dropna=False,
    ):

        group = group.sort_values(
            "start_dt"
        )


        latest = group.iloc[
            -1
        ]


        starts = group[
            group[
                "starter"
            ]
            .astype(str)
            .str.lower()
            .isin(
                [
                    "true",
                    "1",
                ]
            )
        ]


        row = {
            "player_id":
                player_id,

            "player":
                player,

            "team":
                latest.get(
                    "team",
                    "",
                ),

            "games":
                len(
                    group
                ),

            "starts":
                len(
                    starts
                ),

            "latest_start":
                latest.get(
                    "start",
                    "",
                ),
        }


        for metric in [
            "save_pct",
            "saves",
            "shots_against",
            "goals_against",
            "toi_minutes",
        ]:

            values = pd.to_numeric(
                group[
                    metric
                ],
                errors="coerce",
            )


            row[
                metric
                + "_season_avg"
            ] = values.mean()


            for n in [
                3,
                5,
                10,
                20,
            ]:

                row[
                    metric
                    + f"_l{n}_avg"
                ] = (
                    values
                    .tail(
                        n
                    )
                    .mean()
                )


        rows.append(
            row
        )


    context = pd.DataFrame(
        rows
    )


    context.to_csv(
        GOALIE_CONTEXT,
        index=False,
    )


    try:

        context.to_parquet(
            GOALIE_CONTEXT.with_suffix(
                ".parquet"
            ),
            index=False,
        )

    except Exception:
        pass


    return context


def refresh_current():

    now = datetime.now(
        timezone.utc
    )


    rows = []


    for offset in range(
        -3,
        8,
    ):

        date = (
            now.date()
            + timedelta(
                days=offset
            )
        )


        try:

            day_rows = fetch_score_date(
                date
            )

            print(
                "CURRENT",
                date,
                "=>",
                len(
                    day_rows
                ),
                "games",
            )

            rows.extend(
                day_rows
            )

        except Exception as exc:

            print(
                "CURRENT WARNING:",
                date,
                type(
                    exc
                ).__name__,
            )


    current = pd.DataFrame(
        rows
    )


    if not current.empty:

        current = (
            current
            .drop_duplicates(
                "event_id",
                keep="last",
            )
            .sort_values(
                "start"
            )
        )


    current.to_csv(
        CURRENT_GAMES,
        index=False,
    )


    finals = (
        current[
            current[
                "completed"
            ]
            .astype(str)
            .str.lower()
            .isin(
                [
                    "true",
                    "1",
                ]
            )
        ].copy()
        if not current.empty
        else pd.DataFrame()
    )


    results = merge_history(
        RESULTS,
        finals,
        [
            "event_id",
        ],
    )


    return (
        current,
        results,
    )


def load_checkpoint():

    if not CHECKPOINT.exists():
        return {}


    try:

        return json.loads(
            CHECKPOINT.read_text()
        )

    except Exception:

        return {}


def save_checkpoint(
    date,
):

    CHECKPOINT.write_text(
        json.dumps(
            {
                "last_completed_week":
                    date.isoformat(),

                "updated_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
            },
            indent=2,
        )
    )


def historical_backfill(
    start,
    end,
    resume=True,
):

    cp = load_checkpoint()


    if (
        resume
        and cp.get(
            "last_completed_week"
        )
    ):

        try:

            saved = (
                datetime.fromisoformat(
                    cp[
                        "last_completed_week"
                    ]
                ).date()
                + timedelta(
                    days=7
                )
            )

            if saved > start:
                start = saved

        except Exception:
            pass


    week = start


    while week <= end:

        print()
        print(
            "WEEK:",
            week,
        )


        try:

            scheduled = fetch_schedule_week(
                week
            )

        except Exception as exc:

            print(
                "SCHEDULE WARNING:",
                type(
                    exc
                ).__name__,
            )

            break


        # Only dates inside requested historical range.
        scheduled = [
            row
            for row in scheduled
            if (
                row[
                    "game_date"
                ]
                and start.isoformat()
                <= row[
                    "game_date"
                ]
                <= end.isoformat()
            )
        ]


        games = pd.DataFrame(
            scheduled
        )


        final_games = [
            row
            for row in scheduled
            if row[
                "completed"
            ]
        ]


        player_parts = []
        goalie_parts = []
        team_parts = []


        for game in final_games:

            event_id = game[
                "event_id"
            ]


            try:

                box = get_json(
                    BASE
                    + "/gamecenter/"
                    + str(
                        event_id
                    )
                    + "/boxscore"
                )

            except Exception as exc:

                print(
                    "BOX WARNING:",
                    event_id,
                    type(
                        exc
                    ).__name__,
                )

                continue


            players, goalies, teams = (
                player_rows_from_boxscore(
                    game,
                    box,
                )
            )


            if not players.empty:
                player_parts.append(
                    players
                )

            if not goalies.empty:
                goalie_parts.append(
                    goalies
                )

            if not teams.empty:
                team_parts.append(
                    teams
                )


            time.sleep(
                0.04
            )


        player_new = (
            pd.concat(
                player_parts,
                ignore_index=True,
                sort=False,
            )
            if player_parts
            else pd.DataFrame()
        )


        goalie_new = (
            pd.concat(
                goalie_parts,
                ignore_index=True,
                sort=False,
            )
            if goalie_parts
            else pd.DataFrame()
        )


        team_new = (
            pd.concat(
                team_parts,
                ignore_index=True,
                sort=False,
            )
            if team_parts
            else pd.DataFrame()
        )


        merge_history(
            GAME_HISTORY,
            games,
            [
                "event_id",
            ],
        )


        merge_history(
            PLAYER_HISTORY,
            player_new,
            [
                "event_id",
                "player_id",
            ],
        )


        merge_history(
            GOALIE_HISTORY,
            goalie_new,
            [
                "event_id",
                "player_id",
            ],
        )


        merge_history(
            TEAM_HISTORY,
            team_new,
            [
                "event_id",
                "team",
            ],
        )


        print(
            "games=",
            len(
                games
            ),
            "finals=",
            len(
                final_games
            ),
            "skaters=",
            len(
                player_new
            ),
            "goalies=",
            len(
                goalie_new
            ),
            "teams=",
            len(
                team_new
            ),
        )


        save_checkpoint(
            week
        )


        week += timedelta(
            days=7
        )


def main():

    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--backfill",
        action="store_true",
    )

    parser.add_argument(
        "--start",
        default="2025-09-20",
    )

    parser.add_argument(
        "--end",
        default="2026-06-30",
    )

    parser.add_argument(
        "--no-resume",
        action="store_true",
    )


    args = parser.parse_args()


    current, results = (
        refresh_current()
    )


    if args.backfill:

        historical_backfill(
            datetime.fromisoformat(
                args.start
            ).date(),
            datetime.fromisoformat(
                args.end
            ).date(),
            resume=not args.no_resume,
        )


    roster = collect_rosters()

    player_context = (
        build_player_context()
    )

    goalie_context = (
        build_goalie_context()
    )


    def rows(
        path,
    ):

        try:

            return len(
                pd.read_csv(
                    path,
                    low_memory=False,
                )
            )

        except Exception:

            return 0


    receipt = {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "source":
            "NHL_OFFICIAL_API",

        "current_games":
            int(
                len(
                    current
                )
            ),

        "result_history":
            int(
                len(
                    results
                )
            ),

        "game_history":
            rows(
                GAME_HISTORY
            ),

        "player_game_history":
            rows(
                PLAYER_HISTORY
            ),

        "goalie_game_history":
            rows(
                GOALIE_HISTORY
            ),

        "team_game_history":
            rows(
                TEAM_HISTORY
            ),

        "current_rosters":
            int(
                len(
                    roster
                )
            ),

        "player_context":
            int(
                len(
                    player_context
                )
            ),

        "goalie_context":
            int(
                len(
                    goalie_context
                )
            ),

        "context_game_types":
            [
                2,
                3,
            ],
    }


    (
        RECEIPTS
        / "NHL_DATA_RECEIPT_LATEST.json"
    ).write_text(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
        )
    )


    print()
    print(
        "CURRENT GAMES:",
        receipt[
            "current_games"
        ],
    )

    print(
        "GAME HISTORY:",
        receipt[
            "game_history"
        ],
    )

    print(
        "PLAYER GAME HISTORY:",
        receipt[
            "player_game_history"
        ],
    )

    print(
        "GOALIE GAME HISTORY:",
        receipt[
            "goalie_game_history"
        ],
    )

    print(
        "TEAM GAME HISTORY:",
        receipt[
            "team_game_history"
        ],
    )

    print(
        "CURRENT ROSTERS:",
        receipt[
            "current_rosters"
        ],
    )

    print(
        "PLAYER CONTEXT:",
        receipt[
            "player_context"
        ],
    )

    print(
        "GOALIE CONTEXT:",
        receipt[
            "goalie_context"
        ],
    )

    print()
    print(
        "RESULT: NHL_DATA_READY"
    )


if __name__ == "__main__":
    main()
