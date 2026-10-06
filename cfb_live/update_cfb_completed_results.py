#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

if str(
    ROOT
) not in sys.path:

    sys.path.insert(
        0,
        str(
            ROOT
        ),
    )


from cfb_live.build_cfb_core import (
    CURRENT_GAMES,
    GAME_HISTORY,
    TEAM_HISTORY,
    bool_value,
    build_elo,
    build_srs,
    merge_csv,
    team_rows,
)


def read_csv(
    path,
):

    if (
        not Path(
            path
        ).exists()
        or Path(
            path
        ).stat().st_size <= 1
    ):

        return pd.DataFrame()


    try:

        return pd.read_csv(
            path,
            low_memory=False,
        )

    except Exception:

        return pd.DataFrame()


def main():

    current = read_csv(
        CURRENT_GAMES
    )


    if current.empty:

        print(
            "NO CURRENT CFB SCHEDULE"
        )

        return


    finals = current[
        current[
            "completed"
        ].map(
            bool_value
        )
    ].copy()


    if finals.empty:

        print(
            "CURRENT COMPLETED CFB GAMES: 0"
        )

        print(
            "RESULT: CFB_RESULTS_CURRENT"
        )

        return


    old_games = read_csv(
        GAME_HISTORY
    )


    existing = (
        set(
            old_games[
                "event_id"
            ]
            .astype(
                str
            )
        )
        if not old_games.empty
        else set()
    )


    new_finals = finals[
        ~finals[
            "event_id"
        ]
        .astype(
            str
        )
        .isin(
            existing
        )
    ].copy()


    updated_games = merge_csv(
        GAME_HISTORY,
        finals,
        [
            "event_id",
        ],
    )


    new_team_rows = team_rows(
        new_finals
    )


    all_team_rows = team_rows(
        finals
    )


    updated_teams = merge_csv(
        TEAM_HISTORY,
        all_team_rows,
        [
            "event_id",
            "team_id",
        ],
    )


    elo = build_elo(
        updated_games
    )

    srs = build_srs(
        updated_teams
    )


    print(
        "CURRENT COMPLETED CFB GAMES:",
        len(
            finals
        )
    )

    print(
        "NEW COMPLETED GAMES:",
        len(
            new_finals
        )
    )

    print(
        "NEW TEAM-GAME ROWS:",
        len(
            new_team_rows
        )
    )

    print(
        "TOTAL GAME HISTORY:",
        len(
            updated_games
        )
    )

    print(
        "TOTAL TEAM HISTORY:",
        len(
            updated_teams
        )
    )

    print(
        "ELO TEAMS:",
        len(
            elo
        )
    )

    print(
        "SRS TEAMS:",
        len(
            srs
        )
    )

    print()
    print(
        "RESULT: CFB_RESULTS_CURRENT"
    )


if __name__ == "__main__":
    main()
