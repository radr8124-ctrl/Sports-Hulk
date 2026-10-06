#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)
from zoneinfo import ZoneInfo

import argparse
import json
import math
import time

import pandas as pd
import requests


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

CFB = ROOT / "cfb_live"
DERIVED = CFB / "derived"
HISTORY = CFB / "history"
CHECKPOINTS = CFB / "checkpoints"
RECEIPTS = CFB / "receipts"


CURRENT_GAMES = (
    DERIVED
    / "CFB_GAMES_CURRENT.csv"
)

GAME_HISTORY = (
    HISTORY
    / "CFB_GAME_HISTORY.csv"
)

TEAM_HISTORY = (
    HISTORY
    / "CFB_TEAM_GAME_HISTORY.csv"
)

ELO_CURRENT = (
    DERIVED
    / "CFB_ELO_CURRENT.csv"
)

SRS_CURRENT = (
    DERIVED
    / "CFB_SRS_CURRENT.csv"
)

RANKINGS_CURRENT = (
    DERIVED
    / "CFB_RANKINGS_CURRENT.csv"
)

CHECKPOINT = (
    CHECKPOINTS
    / "CFB_HISTORY_CHECKPOINT.json"
)


BASE = (
    "https://site.api.espn.com/"
    "apis/site/v2/sports/football/"
    "college-football"
)

HEADERS = {
    "User-Agent":
        "Sports-HULK/1.0",
    "Accept":
        "application/json",
}

ET = ZoneInfo(
    "America/New_York"
)

SESSION = requests.Session()
SESSION.headers.update(
    HEADERS
)


def get_json(
    url,
    params=None,
    retries=3,
):

    last = None

    for attempt in range(
        retries
    ):

        try:

            r = SESSION.get(
                url,
                params=params or {},
                timeout=30,
            )

            r.raise_for_status()

            return r.json()

        except Exception as exc:

            last = exc

            if attempt + 1 < retries:

                time.sleep(
                    1.0
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


def bool_value(
    value,
):

    return str(
        value
    ).lower() in {
        "true",
        "1",
        "yes",
    }


def local_game_date(
    start,
):

    try:

        dt = datetime.fromisoformat(
            str(
                start
            ).replace(
                "Z",
                "+00:00",
            )
        )

        return (
            dt
            .astimezone(
                ET
            )
            .date()
            .isoformat()
        )

    except Exception:

        return ""


def parse_event(
    event,
):

    competitions = (
        event.get(
            "competitions"
        )
        or []
    )

    if not competitions:
        return None


    competition = competitions[
        0
    ]


    competitors = (
        competition.get(
            "competitors"
        )
        or []
    )


    away = None
    home = None


    for item in competitors:

        side = str(
            item.get(
                "homeAway",
                ""
            )
        ).lower()


        if side == "away":
            away = item

        elif side == "home":
            home = item


    if not away or not home:
        return None


    away_team = (
        away.get(
            "team"
        )
        or {}
    )

    home_team = (
        home.get(
            "team"
        )
        or {}
    )


    status = (
        competition.get(
            "status"
        )
        or event.get(
            "status"
        )
        or {}
    )

    status_type = (
        status.get(
            "type"
        )
        or {}
    )


    completed = bool(
        status_type.get(
            "completed",
            False,
        )
    )


    start = (
        event.get(
            "date"
        )
        or competition.get(
            "date"
        )
        or ""
    )


    season = (
        event.get(
            "season"
        )
        or {}
    )


    season_year = (
        season.get(
            "year"
        )
    )

    season_type = (
        season.get(
            "type"
        )
    )


    if isinstance(
        season_type,
        dict,
    ):

        season_type = (
            season_type.get(
                "type"
            )
            or season_type.get(
                "id"
            )
        )


    neutral = bool(
        competition.get(
            "neutralSite",
            False,
        )
    )


    venue = (
        competition.get(
            "venue"
        )
        or {}
    )


    address = (
        venue.get(
            "address"
        )
        or {}
    )


    away_rank = (
        away.get(
            "curatedRank"
        )
        or {}
    ).get(
        "current"
    )

    home_rank = (
        home.get(
            "curatedRank"
        )
        or {}
    ).get(
        "current"
    )


    return {
        "event_id":
            clean(
                event.get(
                    "id"
                )
            ),

        "start":
            start,

        "game_date":
            local_game_date(
                start
            ),

        "season":
            season_year,

        "season_type":
            season_type,

        "away_team_id":
            clean(
                away_team.get(
                    "id"
                )
            ),

        "away_team":
            (
                away_team.get(
                    "abbreviation"
                )
                or ""
            ),

        "away_team_name":
            (
                away_team.get(
                    "displayName"
                )
                or away_team.get(
                    "shortDisplayName"
                )
                or ""
            ),

        "away_team_location":
            (
                away_team.get(
                    "location"
                )
                or ""
            ),

        "away_team_short_name":
            (
                away_team.get(
                    "shortDisplayName"
                )
                or ""
            ),

        "away_score":
            number(
                away.get(
                    "score"
                )
            ),

        "away_rank":
            number(
                away_rank
            ),

        "home_team_id":
            clean(
                home_team.get(
                    "id"
                )
            ),

        "home_team":
            (
                home_team.get(
                    "abbreviation"
                )
                or ""
            ),

        "home_team_name":
            (
                home_team.get(
                    "displayName"
                )
                or home_team.get(
                    "shortDisplayName"
                )
                or ""
            ),

        "home_team_location":
            (
                home_team.get(
                    "location"
                )
                or ""
            ),

        "home_team_short_name":
            (
                home_team.get(
                    "shortDisplayName"
                )
                or ""
            ),

        "home_score":
            number(
                home.get(
                    "score"
                )
            ),

        "home_rank":
            number(
                home_rank
            ),

        "neutral_site":
            neutral,

        "venue":
            (
                venue.get(
                    "fullName"
                )
                or ""
            ),

        "venue_city":
            (
                address.get(
                    "city"
                )
                or ""
            ),

        "venue_state":
            (
                address.get(
                    "state"
                )
                or ""
            ),

        "status":
            (
                status_type.get(
                    "description"
                )
                or status_type.get(
                    "detail"
                )
                or status_type.get(
                    "name"
                )
                or ""
            ),

        "status_state":
            (
                status_type.get(
                    "state"
                )
                or ""
            ),

        "completed":
            completed,

        "conference_competition":
            bool(
                competition.get(
                    "conferenceCompetition",
                    False,
                )
            ),
    }


def fetch_day(
    day,
):

    payload = get_json(
        BASE
        + "/scoreboard",
        params={
            "dates":
                day.strftime(
                    "%Y%m%d"
                ),

            # groups=80 returns the FBS scoreboard.
            # Games against FCS opponents remain visible.
            "groups":
                "80",

            "limit":
                400,
        },
    )


    rows = []


    for event in (
        payload.get(
            "events"
        )
        or []
    ):

        row = parse_event(
            event
        )

        if row:
            rows.append(
                row
            )


    return rows


def merge_csv(
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


    if "start" in result.columns:

        result = result.sort_values(
            "start"
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


def team_rows(
    games,
):

    rows = []


    for _, game in games.iterrows():

        if not bool_value(
            game.get(
                "completed"
            )
        ):
            continue


        away_score = number(
            game.get(
                "away_score"
            )
        )

        home_score = number(
            game.get(
                "home_score"
            )
        )


        if (
            away_score is None
            or home_score is None
        ):
            continue


        rows.append({
            "event_id":
                game[
                    "event_id"
                ],

            "game_date":
                game[
                    "game_date"
                ],

            "start":
                game[
                    "start"
                ],

            "season":
                game.get(
                    "season"
                ),

            "season_type":
                game.get(
                    "season_type"
                ),

            "team_id":
                game[
                    "away_team_id"
                ],

            "team":
                game[
                    "away_team"
                ],

            "team_name":
                game[
                    "away_team_name"
                ],

            "opponent_id":
                game[
                    "home_team_id"
                ],

            "opponent":
                game[
                    "home_team"
                ],

            "opponent_name":
                game[
                    "home_team_name"
                ],

            "home_away":
                "AWAY",

            "neutral_site":
                game.get(
                    "neutral_site",
                    False,
                ),

            "score":
                away_score,

            "opponent_score":
                home_score,

            "margin":
                away_score
                - home_score,

            "win":
                float(
                    away_score
                    > home_score
                ),
        })


        rows.append({
            "event_id":
                game[
                    "event_id"
                ],

            "game_date":
                game[
                    "game_date"
                ],

            "start":
                game[
                    "start"
                ],

            "season":
                game.get(
                    "season"
                ),

            "season_type":
                game.get(
                    "season_type"
                ),

            "team_id":
                game[
                    "home_team_id"
                ],

            "team":
                game[
                    "home_team"
                ],

            "team_name":
                game[
                    "home_team_name"
                ],

            "opponent_id":
                game[
                    "away_team_id"
                ],

            "opponent":
                game[
                    "away_team"
                ],

            "opponent_name":
                game[
                    "away_team_name"
                ],

            "home_away":
                "HOME",

            "neutral_site":
                game.get(
                    "neutral_site",
                    False,
                ),

            "score":
                home_score,

            "opponent_score":
                away_score,

            "margin":
                home_score
                - away_score,

            "win":
                float(
                    home_score
                    > away_score
                ),
        })


    return pd.DataFrame(
        rows
    )


def build_elo(
    games,
):

    if games.empty:

        pd.DataFrame().to_csv(
            ELO_CURRENT,
            index=False,
        )

        return pd.DataFrame()


    games = games.copy()

    games[
        "start_dt"
    ] = pd.to_datetime(
        games[
            "start"
        ],
        utc=True,
        errors="coerce",
    )


    games = games[
        games[
            "completed"
        ].map(
            bool_value
        )
    ].copy()


    games = games.sort_values(
        "start_dt"
    )


    ratings = {}
    wins = {}
    losses = {}
    games_played = {}
    last_game = {}


    def rating(
        team_id,
    ):

        return ratings.get(
            team_id,
            1500.0,
        )


    K = 20.0
    HOME_ADV = 65.0


    for _, game in games.iterrows():

        away = str(
            game[
                "away_team_id"
            ]
        )

        home = str(
            game[
                "home_team_id"
            ]
        )

        away_score = number(
            game[
                "away_score"
            ]
        )

        home_score = number(
            game[
                "home_score"
            ]
        )


        if (
            not away
            or not home
            or away_score is None
            or home_score is None
            or away_score == home_score
        ):
            continue


        ra = rating(
            away
        )

        rh = rating(
            home
        )


        home_edge = (
            0.0
            if bool_value(
                game.get(
                    "neutral_site"
                )
            )
            else HOME_ADV
        )


        expected_home = (
            1.0
            / (
                1.0
                + 10.0
                ** (
                    (
                        ra
                        - (
                            rh
                            + home_edge
                        )
                    )
                    / 400.0
                )
            )
        )


        actual_home = float(
            home_score
            > away_score
        )


        delta = (
            K
            * (
                actual_home
                - expected_home
            )
        )


        ratings[
            home
        ] = (
            rh
            + delta
        )

        ratings[
            away
        ] = (
            ra
            - delta
        )


        for club in [
            home,
            away,
        ]:

            games_played[
                club
            ] = (
                games_played.get(
                    club,
                    0,
                )
                + 1
            )

            last_game[
                club
            ] = game.get(
                "start"
            )


        if actual_home == 1.0:

            wins[
                home
            ] = (
                wins.get(
                    home,
                    0,
                )
                + 1
            )

            losses[
                away
            ] = (
                losses.get(
                    away,
                    0,
                )
                + 1
            )

        else:

            wins[
                away
            ] = (
                wins.get(
                    away,
                    0,
                )
                + 1
            )

            losses[
                home
            ] = (
                losses.get(
                    home,
                    0,
                )
                + 1
            )


    name_lookup = {}


    for _, game in games.iterrows():

        name_lookup[
            str(
                game[
                    "away_team_id"
                ]
            )
        ] = {
            "team":
                game[
                    "away_team"
                ],

            "team_name":
                game[
                    "away_team_name"
                ],
        }

        name_lookup[
            str(
                game[
                    "home_team_id"
                ]
            )
        ] = {
            "team":
                game[
                    "home_team"
                ],

            "team_name":
                game[
                    "home_team_name"
                ],
        }


    rows = []


    for club, elo in ratings.items():

        names = name_lookup.get(
            club,
            {},
        )


        rows.append({
            "team_id":
                club,

            "team":
                names.get(
                    "team",
                    "",
                ),

            "team_name":
                names.get(
                    "team_name",
                    "",
                ),

            "elo":
                elo,

            "games":
                games_played.get(
                    club,
                    0,
                ),

            "wins":
                wins.get(
                    club,
                    0,
                ),

            "losses":
                losses.get(
                    club,
                    0,
                ),

            "last_game":
                last_game.get(
                    club,
                    "",
                ),
        })


    out = pd.DataFrame(
        rows
    )


    if not out.empty:

        out = out.sort_values(
            "elo",
            ascending=False,
        )


    out.to_csv(
        ELO_CURRENT,
        index=False,
    )


    return out


def build_srs(
    teams,
):

    if teams.empty:

        pd.DataFrame().to_csv(
            SRS_CURRENT,
            index=False,
        )

        return pd.DataFrame()


    teams = teams.copy()


    teams[
        "margin"
    ] = pd.to_numeric(
        teams[
            "margin"
        ],
        errors="coerce",
    )


    teams = teams[
        teams[
            "margin"
        ].notna()
    ].copy()


    if teams.empty:

        return pd.DataFrame()


    team_ids = sorted(
        set(
            teams[
                "team_id"
            ]
            .astype(
                str
            )
        )
    )


    ratings = {
        club:
            0.0
        for club in team_ids
    }


    grouped = {
        club:
            group.copy()
        for club, group
        in teams.groupby(
            teams[
                "team_id"
            ].astype(
                str
            )
        )
    }


    for _ in range(
        100
    ):

        updated = {}


        for club in team_ids:

            group = grouped.get(
                club
            )


            if (
                group is None
                or group.empty
            ):

                updated[
                    club
                ] = 0.0

                continue


            values = []


            for _, row in group.iterrows():

                opponent = str(
                    row[
                        "opponent_id"
                    ]
                )

                margin = number(
                    row[
                        "margin"
                    ]
                )


                if margin is None:
                    continue


                values.append(
                    margin
                    + ratings.get(
                        opponent,
                        0.0,
                    )
                )


            updated[
                club
            ] = (
                sum(
                    values
                )
                / len(
                    values
                )
                if values
                else 0.0
            )


        mean_rating = (
            sum(
                updated.values()
            )
            / len(
                updated
            )
            if updated
            else 0.0
        )


        ratings = {
            club:
                value
                - mean_rating

            for club, value
            in updated.items()
        }


    latest_names = (
        teams[
            [
                "team_id",
                "team",
                "team_name",
            ]
        ]
        .drop_duplicates(
            "team_id",
            keep="last",
        )
    )


    rows = []


    for _, name_row in (
        latest_names.iterrows()
    ):

        club = str(
            name_row[
                "team_id"
            ]
        )

        group = grouped.get(
            club
        )


        avg_margin = (
            pd.to_numeric(
                group[
                    "margin"
                ],
                errors="coerce",
            )
            .mean()
            if group is not None
            else None
        )


        schedule_values = []


        if group is not None:

            for opponent in (
                group[
                    "opponent_id"
                ]
                .astype(
                    str
                )
            ):

                schedule_values.append(
                    ratings.get(
                        opponent,
                        0.0,
                    )
                )


        sos = (
            sum(
                schedule_values
            )
            / len(
                schedule_values
            )
            if schedule_values
            else None
        )


        rows.append({
            "team_id":
                club,

            "team":
                name_row[
                    "team"
                ],

            "team_name":
                name_row[
                    "team_name"
                ],

            "games":
                len(
                    group
                )
                if group is not None
                else 0,

            "average_margin":
                avg_margin,

            "strength_of_schedule":
                sos,

            "srs":
                ratings.get(
                    club,
                    0.0,
                ),
        })


    out = pd.DataFrame(
        rows
    )


    if not out.empty:

        out = out.sort_values(
            "srs",
            ascending=False,
        )


    out.to_csv(
        SRS_CURRENT,
        index=False,
    )


    return out


def fetch_rankings():

    try:

        payload = get_json(
            BASE
            + "/rankings"
        )

    except Exception as exc:

        print(
            "RANKINGS WARNING:",
            type(
                exc
            ).__name__,
        )

        pd.DataFrame().to_csv(
            RANKINGS_CURRENT,
            index=False,
        )

        return pd.DataFrame()


    rows = []


    now = datetime.now(
        timezone.utc
    )


    expected_season = now.year


    for poll in (
        payload.get(
            "rankings"
        )
        or []
    ):

        season = (
            poll.get(
                "season"
            )
            or {}
        )


        poll_season = season.get(
            "year"
        )


        for rank in (
            poll.get(
                "ranks"
            )
            or []
        ):

            team = (
                rank.get(
                    "team"
                )
                or {}
            )


            rows.append({
                "poll_id":
                    poll.get(
                        "id"
                    ),

                "poll":
                    poll.get(
                        "name"
                    ),

                "poll_short":
                    poll.get(
                        "shortName"
                    ),

                "poll_type":
                    poll.get(
                        "type"
                    ),

                "poll_date":
                    poll.get(
                        "date"
                    ),

                "poll_season":
                    poll_season,

                "expected_current_season":
                    expected_season,

                "current_season_match":
                    (
                        poll_season
                        == expected_season
                    ),

                "rank":
                    rank.get(
                        "current"
                    ),

                "previous_rank":
                    rank.get(
                        "previous"
                    ),

                "trend":
                    rank.get(
                        "trend"
                    ),

                "points":
                    rank.get(
                        "points"
                    ),

                "first_place_votes":
                    rank.get(
                        "firstPlaceVotes"
                    ),

                "team_id":
                    team.get(
                        "id"
                    ),

                "team":
                    team.get(
                        "abbreviation"
                    ),

                "team_name":
                    (
                        team.get(
                            "nickname"
                        )
                        or team.get(
                            "location"
                        )
                        or team.get(
                            "displayName"
                        )
                        or ""
                    ),
            })


    out = pd.DataFrame(
        rows
    )


    out.to_csv(
        RANKINGS_CURRENT,
        index=False,
    )


    return out


def current_window():

    today = datetime.now(
        ET
    ).date()


    return (
        today
        - timedelta(
            days=1
        ),
        today
        + timedelta(
            days=8
        ),
    )


def refresh_current():

    start, end = current_window()

    rows = []

    cursor = start


    while cursor <= end:

        try:

            day = fetch_day(
                cursor
            )

            print(
                "CURRENT",
                cursor,
                "=>",
                len(
                    day
                ),
                "games",
            )

            rows.extend(
                day
            )

        except Exception as exc:

            print(
                "CURRENT WARNING:",
                cursor,
                type(
                    exc
                ).__name__,
            )


        cursor += timedelta(
            days=1
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


    return current


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
    day,
):

    CHECKPOINT.write_text(
        json.dumps(
            {
                "last_completed_date":
                    day.isoformat(),

                "updated_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
            },
            indent=2,
        )
    )


def backfill(
    start,
    end,
    resume=True,
):

    cp = load_checkpoint()


    if (
        resume
        and cp.get(
            "last_completed_date"
        )
    ):

        try:

            saved = (
                date.fromisoformat(
                    cp[
                        "last_completed_date"
                    ]
                )
                + timedelta(
                    days=1
                )
            )


            if saved > start:
                start = saved

        except Exception:
            pass


    cursor = start


    while cursor <= end:

        try:

            rows = fetch_day(
                cursor
            )

        except Exception as exc:

            print(
                "BACKFILL WARNING:",
                cursor,
                type(
                    exc
                ).__name__,
            )

            break


        games = pd.DataFrame(
            rows
        )


        finals = (
            games[
                games[
                    "completed"
                ].map(
                    bool_value
                )
            ].copy()
            if not games.empty
            else pd.DataFrame()
        )


        teams = team_rows(
            finals
        )


        merge_csv(
            GAME_HISTORY,
            finals,
            [
                "event_id",
            ],
        )


        merge_csv(
            TEAM_HISTORY,
            teams,
            [
                "event_id",
                "team_id",
            ],
        )


        print(
            "HISTORY",
            cursor,
            "games=",
            len(
                games
            ),
            "finals=",
            len(
                finals
            ),
            "team_rows=",
            len(
                teams
            ),
        )


        save_checkpoint(
            cursor
        )


        time.sleep(
            0.03
        )


        cursor += timedelta(
            days=1
        )


def main():

    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--backfill",
        action="store_true",
    )

    parser.add_argument(
        "--start",
        default="2026-08-22",
    )

    parser.add_argument(
        "--end",
        default="2026-10-02",
    )

    parser.add_argument(
        "--no-resume",
        action="store_true",
    )


    args = parser.parse_args()


    current = refresh_current()


    if args.backfill:

        backfill(
            date.fromisoformat(
                args.start
            ),
            date.fromisoformat(
                args.end
            ),
            resume=not args.no_resume,
        )


    history = pd.DataFrame()

    teams = pd.DataFrame()


    if GAME_HISTORY.exists():

        history = pd.read_csv(
            GAME_HISTORY,
            low_memory=False,
        )


    if TEAM_HISTORY.exists():

        teams = pd.read_csv(
            TEAM_HISTORY,
            low_memory=False,
        )


    elo = build_elo(
        history
    )

    srs = build_srs(
        teams
    )

    rankings = fetch_rankings()


    receipt = {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "source":
            "ESPN_PUBLIC_COLLEGE_FOOTBALL",

        "group":
            "FBS_GROUP_80",

        "current_games":
            int(
                len(
                    current
                )
            ),

        "historical_games":
            int(
                len(
                    history
                )
            ),

        "team_game_rows":
            int(
                len(
                    teams
                )
            ),

        "elo_teams":
            int(
                len(
                    elo
                )
            ),

        "srs_teams":
            int(
                len(
                    srs
                )
            ),

        "ranking_rows":
            int(
                len(
                    rankings
                )
            ),

        "rankings_current_season_rows":
            int(
                rankings[
                    "current_season_match"
                ]
                .sum()
            )
            if (
                not rankings.empty
                and "current_season_match"
                in rankings.columns
            )
            else 0,

        "college_player_props_enabled":
            False,

        "college_prizepicks_enabled":
            False,

        "college_fantasy_enabled":
            False,
    }


    (
        RECEIPTS
        / "CFB_CORE_RECEIPT_LATEST.json"
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
        ]
    )

    print(
        "HISTORICAL GAMES:",
        receipt[
            "historical_games"
        ]
    )

    print(
        "TEAM GAME ROWS:",
        receipt[
            "team_game_rows"
        ]
    )

    print(
        "ELO TEAMS:",
        receipt[
            "elo_teams"
        ]
    )

    print(
        "SRS TEAMS:",
        receipt[
            "srs_teams"
        ]
    )

    print(
        "RANKING ROWS:",
        receipt[
            "ranking_rows"
        ]
    )

    print(
        "CURRENT-SEASON RANKING ROWS:",
        receipt[
            "rankings_current_season_rows"
        ]
    )

    print()
    print(
        "RESULT: CFB_CORE_READY"
    )


if __name__ == "__main__":
    main()
