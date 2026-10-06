#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime, timedelta, timezone
import argparse
import json
import time

import pandas as pd
import requests


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

NBA = ROOT / "nba_live"
DERIVED = NBA / "derived"
HISTORY = NBA / "history"
RAW = NBA / "raw"
CHECKPOINTS = NBA / "checkpoints"
RECEIPTS = NBA / "receipts"

CURRENT_GAMES = (
    DERIVED
    / "NBA_GAMES_CURRENT.csv"
)

GAME_HISTORY = (
    HISTORY
    / "NBA_GAME_HISTORY.csv"
)

PLAYER_HISTORY = (
    HISTORY
    / "NBA_PLAYER_GAME_HISTORY.csv"
)

TEAM_HISTORY = (
    HISTORY
    / "NBA_TEAM_GAME_HISTORY.csv"
)

CURRENT_INJURIES = (
    DERIVED
    / "NBA_INJURIES_CURRENT.csv"
)

PLAYER_CONTEXT = (
    DERIVED
    / "NBA_PLAYER_CONTEXT.csv"
)

CHECKPOINT = (
    CHECKPOINTS
    / "NBA_HISTORY_CHECKPOINT.json"
)


SCOREBOARD = (
    "https://site.api.espn.com/"
    "apis/site/v2/sports/basketball/"
    "nba/scoreboard"
)

SUMMARY = (
    "https://site.api.espn.com/"
    "apis/site/v2/sports/basketball/"
    "nba/summary"
)

HEADERS = {
    "User-Agent":
        "Mozilla/5.0 "
        "(Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/154.0 Safari/537.36",

    "Accept":
        "application/json,text/plain,*/*",
}


SESSION = requests.Session()
SESSION.headers.update(
    HEADERS
)


def request_json(
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
                params=params,
                timeout=30,
            )

            r.raise_for_status()

            return r.json()

        except Exception as exc:

            last = exc

            if attempt + 1 < retries:
                time.sleep(
                    1.5
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

        if value in (
            None,
            "",
            "--",
        ):
            return None

        return float(
            value
        )

    except Exception:

        return None


def parse_minutes(
    value,
):

    value = clean(
        value
    )

    if not value:
        return None

    if ":" in value:

        try:

            minutes, seconds = (
                value.split(
                    ":",
                    1,
                )
            )

            return (
                float(
                    minutes
                )
                + float(
                    seconds
                )
                / 60.0
            )

        except Exception:
            pass

    return number(
        value
    )


def parse_made_attempt(
    value,
):

    value = clean(
        value
    )

    if "-" not in value:
        return (
            None,
            None,
        )

    left, right = value.split(
        "-",
        1,
    )

    return (
        number(
            left
        ),
        number(
            right
        ),
    )


def event_game_row(
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

    home = {}
    away = {}

    for c in competitors:

        side = clean(
            c.get(
                "homeAway"
            )
        ).lower()

        team = (
            c.get(
                "team"
            )
            or {}
        )

        row = {
            "team_id":
                clean(
                    team.get(
                        "id"
                    )
                ),

            "team":
                clean(
                    team.get(
                        "abbreviation"
                    )
                ).upper(),

            "team_name":
                clean(
                    team.get(
                        "displayName"
                    )
                ),

            "score":
                number(
                    c.get(
                        "score"
                    )
                ),
        }

        if side == "home":
            home = row

        elif side == "away":
            away = row


    status = (
        competition.get(
            "status"
        )
        or {}
    )

    stype = (
        status.get(
            "type"
        )
        or {}
    )

    completed = bool(
        stype.get(
            "completed"
        )
    )

    state = clean(
        stype.get(
            "state"
        )
    ).lower()

    if state == "post":
        completed = True


    return {
        "event_id":
            clean(
                event.get(
                    "id"
                )
            ),

        "start":
            clean(
                event.get(
                    "date"
                )
            ),

        "season":
            (
                event.get(
                    "season"
                )
                or {}
            ).get(
                "year"
            ),

        "season_type":
            (
                event.get(
                    "season"
                )
                or {}
            ).get(
                "type"
            ),

        "away_team_id":
            away.get(
                "team_id",
                "",
            ),

        "away_team":
            away.get(
                "team",
                "",
            ),

        "away_team_name":
            away.get(
                "team_name",
                "",
            ),

        "away_score":
            away.get(
                "score"
            ),

        "home_team_id":
            home.get(
                "team_id",
                "",
            ),

        "home_team":
            home.get(
                "team",
                "",
            ),

        "home_team_name":
            home.get(
                "team_name",
                "",
            ),

        "home_score":
            home.get(
                "score"
            ),

        "status":
            clean(
                stype.get(
                    "description"
                )
                or stype.get(
                    "name"
                )
            ),

        "completed":
            completed,
    }


def summary_player_rows(
    event_id,
    game,
    summary,
):

    boxscore = (
        summary.get(
            "boxscore"
        )
        or {}
    )

    teams = (
        boxscore.get(
            "players"
        )
        or []
    )

    rows = []


    for team_block in teams:

        team = (
            team_block.get(
                "team"
            )
            or {}
        )

        team_abbr = clean(
            team.get(
                "abbreviation"
            )
        ).upper()


        if (
            team_abbr
            == game.get(
                "home_team"
            )
        ):

            opponent = game.get(
                "away_team",
                "",
            )

        else:

            opponent = game.get(
                "home_team",
                "",
            )


        for stat_group in (
            team_block.get(
                "statistics"
            )
            or []
        ):

            names = (
                stat_group.get(
                    "names"
                )
                or []
            )

            name_to_index = {
                name:
                    idx

                for idx, name
                in enumerate(
                    names
                )
            }


            def stat(
                stats,
                name,
            ):

                idx = name_to_index.get(
                    name
                )

                if idx is None:
                    return None

                if idx >= len(
                    stats
                ):
                    return None

                return stats[
                    idx
                ]


            for item in (
                stat_group.get(
                    "athletes"
                )
                or []
            ):

                athlete = (
                    item.get(
                        "athlete"
                    )
                    or {}
                )

                stats = (
                    item.get(
                        "stats"
                    )
                    or []
                )

                fg_made, fg_att = (
                    parse_made_attempt(
                        stat(
                            stats,
                            "FG",
                        )
                    )
                )

                threes_made, threes_att = (
                    parse_made_attempt(
                        stat(
                            stats,
                            "3PT",
                        )
                    )
                )

                ft_made, ft_att = (
                    parse_made_attempt(
                        stat(
                            stats,
                            "FT",
                        )
                    )
                )


                points = number(
                    stat(
                        stats,
                        "PTS",
                    )
                )

                rebounds = number(
                    stat(
                        stats,
                        "REB",
                    )
                )

                assists = number(
                    stat(
                        stats,
                        "AST",
                    )
                )


                rows.append(
                    {
                        "event_id":
                            event_id,

                        "start":
                            game.get(
                                "start"
                            ),

                        "season":
                            game.get(
                                "season"
                            ),

                        "season_type":
                            game.get(
                                "season_type"
                            ),

                        "player_id":
                            clean(
                                athlete.get(
                                    "id"
                                )
                            ),

                        "player":
                            clean(
                                athlete.get(
                                    "displayName"
                                )
                            ),

                        "position":
                            clean(
                                (
                                    athlete.get(
                                        "position"
                                    )
                                    or {}
                                ).get(
                                    "abbreviation"
                                )
                            ),

                        "team":
                            team_abbr,

                        "opponent":
                            opponent,

                        "starter":
                            bool(
                                item.get(
                                    "starter"
                                )
                            ),

                        "active":
                            bool(
                                item.get(
                                    "active",
                                    True,
                                )
                            ),

                        "did_not_play":
                            bool(
                                item.get(
                                    "didNotPlay"
                                )
                            ),

                        "dnp_reason":
                            clean(
                                item.get(
                                    "reason"
                                )
                            ),

                        "minutes":
                            parse_minutes(
                                stat(
                                    stats,
                                    "MIN",
                                )
                            ),

                        "points":
                            points,

                        "rebounds":
                            rebounds,

                        "assists":
                            assists,

                        "turnovers":
                            number(
                                stat(
                                    stats,
                                    "TO",
                                )
                            ),

                        "steals":
                            number(
                                stat(
                                    stats,
                                    "STL",
                                )
                            ),

                        "blocks":
                            number(
                                stat(
                                    stats,
                                    "BLK",
                                )
                            ),

                        "off_rebounds":
                            number(
                                stat(
                                    stats,
                                    "OREB",
                                )
                            ),

                        "def_rebounds":
                            number(
                                stat(
                                    stats,
                                    "DREB",
                                )
                            ),

                        "fouls":
                            number(
                                stat(
                                    stats,
                                    "PF",
                                )
                            ),

                        "plus_minus":
                            number(
                                stat(
                                    stats,
                                    "+/-",
                                )
                            ),

                        "fg_made":
                            fg_made,

                        "fg_attempts":
                            fg_att,

                        "three_made":
                            threes_made,

                        "three_attempts":
                            threes_att,

                        "ft_made":
                            ft_made,

                        "ft_attempts":
                            ft_att,

                        "pra":
                            (
                                points
                                + rebounds
                                + assists
                            )
                            if (
                                points
                                is not None
                                and rebounds
                                is not None
                                and assists
                                is not None
                            )
                            else None,
                    }
                )


    return rows


def summary_team_rows(
    event_id,
    game,
    summary,
):

    boxscore = (
        summary.get(
            "boxscore"
        )
        or {}
    )

    rows = []


    for block in (
        boxscore.get(
            "teams"
        )
        or []
    ):

        team = (
            block.get(
                "team"
            )
            or {}
        )

        abbr = clean(
            team.get(
                "abbreviation"
            )
        ).upper()

        opponent = (
            game.get(
                "away_team"
            )
            if abbr
            == game.get(
                "home_team"
            )
            else game.get(
                "home_team"
            )
        )


        row = {
            "event_id":
                event_id,

            "start":
                game.get(
                    "start"
                ),

            "season":
                game.get(
                    "season"
                ),

            "season_type":
                game.get(
                    "season_type"
                ),

            "team":
                abbr,

            "opponent":
                opponent,
        }


        for stat in (
            block.get(
                "statistics"
            )
            or []
        ):

            name = clean(
                stat.get(
                    "name"
                )
            )

            if not name:
                continue

            row[
                name
            ] = stat.get(
                "displayValue",
                stat.get(
                    "value"
                ),
            )


        rows.append(
            row
        )


    return rows


def summary_injury_rows(
    event_id,
    game,
    summary,
):

    rows = []


    for team_block in (
        summary.get(
            "injuries"
        )
        or []
    ):

        team = (
            team_block.get(
                "team"
            )
            or {}
        )

        team_abbr = clean(
            team.get(
                "abbreviation"
            )
        ).upper()


        for injury in (
            team_block.get(
                "injuries"
            )
            or []
        ):

            athlete = (
                injury.get(
                    "athlete"
                )
                or {}
            )

            details = (
                injury.get(
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


            rows.append(
                {
                    "event_id":
                        event_id,

                    "start":
                        game.get(
                            "start"
                        ),

                    "team":
                        team_abbr,

                    "player_id":
                        clean(
                            athlete.get(
                                "id"
                            )
                        ),

                    "player":
                        clean(
                            athlete.get(
                                "displayName"
                            )
                        ),

                    "status":
                        clean(
                            injury.get(
                                "status"
                            )
                        ),

                    "fantasy_status":
                        clean(
                            fantasy.get(
                                "abbreviation"
                            )
                            or fantasy.get(
                                "description"
                            )
                        ),

                    "injury_type":
                        clean(
                            details.get(
                                "type"
                            )
                        ),

                    "location":
                        clean(
                            details.get(
                                "location"
                            )
                        ),

                    "detail":
                        clean(
                            details.get(
                                "detail"
                            )
                        ),

                    "side":
                        clean(
                            details.get(
                                "side"
                            )
                        ),

                    "return_date":
                        clean(
                            details.get(
                                "returnDate"
                            )
                        ),
                }
            )


    return rows


def merge_history(
    path,
    new,
    keys,
):

    if path.exists():

        try:

            old = pd.read_csv(
                path,
                low_memory=False,
            )

        except Exception:

            old = pd.DataFrame()

    else:

        old = pd.DataFrame()


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


    out = pd.concat(
        parts,
        ignore_index=True,
        sort=False,
    )


    usable_keys = [
        k
        for k in keys
        if k in out.columns
    ]


    if usable_keys:

        out = out.drop_duplicates(
            usable_keys,
            keep="last",
        )


    out.to_csv(
        path,
        index=False,
    )


    try:

        out.to_parquet(
            path.with_suffix(
                ".parquet"
            ),
            index=False,
        )

    except Exception:
        pass


    return out


def collect_date(
    date,
):

    payload = request_json(
        SCOREBOARD,
        params={
            "dates":
                date.strftime(
                    "%Y%m%d"
                ),

            "limit":
                100,
        },
    )


    game_rows = []
    player_rows = []
    team_rows = []


    events = (
        payload.get(
            "events"
        )
        or []
    )


    for event in events:

        game = event_game_row(
            event
        )

        if not game:
            continue


        game_rows.append(
            game
        )


        if not game.get(
            "completed"
        ):
            continue


        event_id = game[
            "event_id"
        ]


        try:

            summary = request_json(
                SUMMARY,
                params={
                    "event":
                        event_id
                },
            )

        except Exception as exc:

            print(
                "SUMMARY WARNING",
                event_id,
                type(
                    exc
                ).__name__,
                str(
                    exc
                )[:100],
            )

            continue


        player_rows.extend(
            summary_player_rows(
                event_id,
                game,
                summary,
            )
        )


        team_rows.extend(
            summary_team_rows(
                event_id,
                game,
                summary,
            )
        )


        time.sleep(
            0.05
        )


    return (
        pd.DataFrame(
            game_rows
        ),
        pd.DataFrame(
            player_rows
        ),
        pd.DataFrame(
            team_rows
        ),
    )


def current_injuries():

    if not CURRENT_GAMES.exists():

        return pd.DataFrame()


    games = pd.read_csv(
        CURRENT_GAMES,
        low_memory=False,
    )


    rows = []


    for _, game_row in (
        games.iterrows()
    ):

        event_id = clean(
            game_row.get(
                "event_id"
            )
        )

        if not event_id:
            continue


        try:

            summary = request_json(
                SUMMARY,
                params={
                    "event":
                        event_id
                },
            )

        except Exception as exc:

            print(
                "INJURY WARNING",
                event_id,
                type(
                    exc
                ).__name__,
            )

            continue


        rows.extend(
            summary_injury_rows(
                event_id,
                game_row.to_dict(),
                summary,
            )
        )


        time.sleep(
            0.03
        )


    injuries = pd.DataFrame(
        rows
    )


    if not injuries.empty:

        injuries = injuries.drop_duplicates(
            [
                "event_id",
                "team",
                "player_id",
            ],
            keep="last",
        )


    injuries.to_csv(
        CURRENT_INJURIES,
        index=False,
    )


    return injuries


def build_player_context(
    player_history,
):

    if player_history.empty:

        pd.DataFrame().to_csv(
            PLAYER_CONTEXT,
            index=False,
        )

        return pd.DataFrame()


    played = player_history[
        ~player_history[
            "did_not_play"
        ].astype(
            str
        ).str.lower().isin(
            [
                "true",
                "1",
            ]
        )
    ].copy()


    played[
        "start_dt"
    ] = pd.to_datetime(
        played[
            "start"
        ],
        utc=True,
        errors="coerce",
    )


    played = played.sort_values(
        [
            "player_id",
            "start_dt",
        ]
    )


    metrics = [
        "minutes",
        "points",
        "rebounds",
        "assists",
        "three_made",
        "turnovers",
        "steals",
        "blocks",
        "pra",
    ]


    rows = []


    for (
        player_id,
        player,
    ), group in played.groupby(
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

            "games":
                len(
                    group
                ),
        }


        for metric in metrics:

            if metric not in group.columns:
                continue


            values = pd.to_numeric(
                group[
                    metric
                ],
                errors="coerce",
            )


            row[
                f"{metric}_season_avg"
            ] = values.mean()


            for n in [
                3,
                5,
                10,
                20,
            ]:

                row[
                    f"{metric}_l{n}_avg"
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
                "last_completed_date":
                    date.isoformat(),

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
                datetime.fromisoformat(
                    cp[
                        "last_completed_date"
                    ]
                ).date()
                + timedelta(
                    days=1
                )
            )

            if saved > start:
                start = saved

        except Exception:
            pass


    day = start


    total_games = 0
    total_players = 0
    total_teams = 0


    while day <= end:

        games, players, teams = (
            collect_date(
                day
            )
        )


        game_hist = merge_history(
            GAME_HISTORY,
            games,
            [
                "event_id",
            ],
        )


        player_hist = merge_history(
            PLAYER_HISTORY,
            players,
            [
                "event_id",
                "player_id",
            ],
        )


        team_hist = merge_history(
            TEAM_HISTORY,
            teams,
            [
                "event_id",
                "team",
            ],
        )


        total_games += len(
            games
        )

        total_players += len(
            players
        )

        total_teams += len(
            teams
        )


        print(
            day,
            "games=",
            len(
                games
            ),
            "players=",
            len(
                players
            ),
            "teams=",
            len(
                teams
            ),
        )


        save_checkpoint(
            day
        )


        day += timedelta(
            days=1
        )


    player_hist = (
        pd.read_csv(
            PLAYER_HISTORY,
            low_memory=False,
        )
        if PLAYER_HISTORY.exists()
        else pd.DataFrame()
    )


    context = build_player_context(
        player_hist
    )


    injuries = current_injuries()


    receipt = {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "requested_start":
            start.isoformat(),

        "requested_end":
            end.isoformat(),

        "new_game_rows_seen":
            total_games,

        "new_player_rows_seen":
            total_players,

        "new_team_rows_seen":
            total_teams,

        "game_history_rows":
            int(
                len(
                    pd.read_csv(
                        GAME_HISTORY,
                        low_memory=False,
                    )
                )
            )
            if GAME_HISTORY.exists()
            else 0,

        "player_history_rows":
            int(
                len(
                    player_hist
                )
            ),

        "team_history_rows":
            int(
                len(
                    pd.read_csv(
                        TEAM_HISTORY,
                        low_memory=False,
                    )
                )
            )
            if TEAM_HISTORY.exists()
            else 0,

        "player_context_rows":
            int(
                len(
                    context
                )
            ),

        "current_injury_rows":
            int(
                len(
                    injuries
                )
            ),

        "source":
            "ESPN_PUBLIC_SUMMARY_AND_SCOREBOARD",

        "official_nba_stats_used":
            False,
    }


    RECEIPTS.joinpath(
        "NBA_HISTORY_RECEIPT_LATEST.json"
    ).write_text(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
        )
    )


    print()
    print(
        "GAME HISTORY:",
        receipt[
            "game_history_rows"
        ],
    )

    print(
        "PLAYER GAME HISTORY:",
        receipt[
            "player_history_rows"
        ],
    )

    print(
        "TEAM GAME HISTORY:",
        receipt[
            "team_history_rows"
        ],
    )

    print(
        "PLAYER CONTEXT:",
        receipt[
            "player_context_rows"
        ],
    )

    print(
        "CURRENT INJURIES:",
        receipt[
            "current_injury_rows"
        ],
    )

    print(
        "RESULT: NBA_HISTORY_READY"
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--start",
        default="2025-10-01",
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


    start = datetime.fromisoformat(
        args.start
    ).date()

    end = datetime.fromisoformat(
        args.end
    ).date()


    backfill(
        start,
        end,
        resume=not args.no_resume,
    )


if __name__ == "__main__":
    main()
