#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

# NHL_BUILD5A_IMPORT_FIX
ROOT_PATH = Path(
    "/home/ubuntu/sports-hulk"
)

if str(ROOT_PATH) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT_PATH),
    )

from nhl_live.build_nhl_data import (
    BASE,
    GAME_HISTORY,
    GOALIE_HISTORY,
    PLAYER_HISTORY,
    TEAM_HISTORY,
    build_goalie_context,
    build_player_context,
    get_json,
    merge_history,
    player_rows_from_boxscore,
)


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

NHL = ROOT / "nhl_live"

CURRENT = (
    NHL
    / "derived"
    / "NHL_GAMES_CURRENT.csv"
)


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


def truth(
    value,
):

    return str(
        value
    ).lower() in {
        "true",
        "1",
        "yes",
    }


def main():

    current = read_csv(
        CURRENT
    )

    if current.empty:

        print(
            "NO CURRENT NHL GAMES"
        )

        return


    finals = current[
        current[
            "completed"
        ].map(
            truth
        )
    ].copy()


    if finals.empty:

        print(
            "NO COMPLETED NHL GAMES TO INGEST"
        )

        return


    players_existing = read_csv(
        PLAYER_HISTORY
    )

    teams_existing = read_csv(
        TEAM_HISTORY
    )


    player_events = set()

    team_events = set()


    if not players_existing.empty:

        player_events = set(
            players_existing[
                "event_id"
            ]
            .astype(
                str
            )
        )


    if not teams_existing.empty:

        team_events = set(
            teams_existing[
                "event_id"
            ]
            .astype(
                str
            )
        )


    player_parts = []
    goalie_parts = []
    team_parts = []

    fetched = 0
    skipped = 0


    for _, row in finals.iterrows():

        event_id = str(
            row[
                "event_id"
            ]
        )


        if (
            event_id in player_events
            and event_id in team_events
        ):

            skipped += 1
            continue


        game = row.to_dict()


        try:

            box = get_json(
                BASE
                + "/gamecenter/"
                + event_id
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


        fetched += 1


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
        finals,
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


    player_context = (
        build_player_context()
    )

    goalie_context = (
        build_goalie_context()
    )


    print(
        "COMPLETED CURRENT GAMES:",
        len(
            finals
        )
    )

    print(
        "NEW BOXSCORES FETCHED:",
        fetched
    )

    print(
        "ALREADY INGESTED:",
        skipped
    )

    print(
        "NEW SKATER ROWS:",
        len(
            player_new
        )
    )

    print(
        "NEW GOALIE ROWS:",
        len(
            goalie_new
        )
    )

    print(
        "NEW TEAM ROWS:",
        len(
            team_new
        )
    )

    print(
        "PLAYER CONTEXT:",
        len(
            player_context
        )
    )

    print(
        "GOALIE CONTEXT:",
        len(
            goalie_context
        )
    )

    print()
    print(
        "RESULT: NHL_COMPLETED_RESULTS_UPDATED"
    )


if __name__ == "__main__":
    main()
