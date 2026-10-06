#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

import json
import math
import re

import numpy as np
import pandas as pd


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

NBA = ROOT / "nba_live"
DEC = NBA / "decision"
HIST = DEC / "history"


LEDGER = (
    HIST
    / "NBA_RECOMMENDATION_LEDGER.csv"
)

GAME_HISTORY = (
    NBA
    / "history"
    / "NBA_GAME_HISTORY.csv"
)

CURRENT_GAMES = (
    NBA
    / "derived"
    / "NBA_GAMES_CURRENT.csv"
)

RESULT_HISTORY = (
    NBA
    / "history"
    / "NBA_RESULTS_HISTORY.csv"
)

PLAYER_HISTORY = (
    NBA
    / "history"
    / "NBA_PLAYER_GAME_HISTORY.csv"
)


EPISODES_OUT = (
    HIST
    / "NBA_RECOMMENDATION_EPISODES.csv"
)

GRADED_OUT = (
    HIST
    / "NBA_GRADED_RECOMMENDATIONS.csv"
)

SIGNALS_OUT = (
    HIST
    / "NBA_SIGNAL_PERFORMANCE.csv"
)

SUMMARY_OUT = (
    HIST
    / "NBA_LEARNING_SUMMARY.json"
)


TEAM_MAP = {
    "GS": "GSW",
    "GSW": "GSW",
    "NY": "NYK",
    "NYK": "NYK",
    "NO": "NOP",
    "NOP": "NOP",
    "SA": "SAS",
    "SAS": "SAS",
    "UTAH": "UTA",
    "UTA": "UTA",
    "WSH": "WAS",
    "WAS": "WAS",
}


STAT_MAP = {
    "points":
        "points",

    "rebounds":
        "rebounds",

    "assists":
        "assists",

    "three_made":
        "three_made",

    "points_rebounds":
        "points_rebounds",

    "points_assists":
        "points_assists",

    "rebounds_assists":
        "rebounds_assists",

    "pra":
        "pra",
}


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


def team(
    value,
):

    value = str(
        value or ""
    ).upper().strip()

    return TEAM_MAP.get(
        value,
        value,
    )


def pkey(
    value,
):

    return re.sub(
        r"[^a-z0-9]+",
        "",
        str(
            value or ""
        ).lower(),
    )


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


def payload(
    row,
):

    try:

        return json.loads(
            row.get(
                "payload_json",
                ""
            )
        )

    except Exception:

        return {}


def compare(
    actual,
    line,
    side,
):

    actual = number(
        actual
    )

    line = number(
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
        "UNRESOLVED",
        margin,
    )


def load_games():

    parts = []


    for path in [
        CURRENT_GAMES,
        GAME_HISTORY,
        RESULT_HISTORY,
    ]:

        df = read_csv(
            path
        )

        if not df.empty:
            parts.append(
                df
            )


    if not parts:

        return pd.DataFrame()


    games = pd.concat(
        parts,
        ignore_index=True,
        sort=False,
    )


    games[
        "away_team_norm"
    ] = games[
        "away_team"
    ].map(
        team
    )

    games[
        "home_team_norm"
    ] = games[
        "home_team"
    ].map(
        team
    )

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

    games[
        "date_key"
    ] = games[
        "start_dt"
    ].dt.strftime(
        "%Y-%m-%d"
    )


    games[
        "_final_rank"
    ] = games[
        "completed"
    ].map(
        truth
    ).astype(
        int
    )


    games = (
        games
        .sort_values(
            [
                "event_id",
                "_final_rank",
            ]
        )
        .drop_duplicates(
            "event_id",
            keep="last",
        )
        .drop(
            columns=[
                "_final_rank"
            ]
        )
    )


    return games


def load_players():

    players = read_csv(
        PLAYER_HISTORY
    )


    if players.empty:
        return players


    players[
        "player_key"
    ] = players[
        "player"
    ].map(
        pkey
    )


    players[
        "team_norm"
    ] = players[
        "team"
    ].map(
        team
    )


    players[
        "opponent_norm"
    ] = players[
        "opponent"
    ].map(
        team
    )


    for col in [
        "points",
        "rebounds",
        "assists",
        "three_made",
        "pra",
    ]:

        if col in players.columns:

            players[
                col
            ] = pd.to_numeric(
                players[
                    col
                ],
                errors="coerce",
            )


    players[
        "points_rebounds"
    ] = (
        players[
            "points"
        ]
        + players[
            "rebounds"
        ]
    )


    players[
        "points_assists"
    ] = (
        players[
            "points"
        ]
        + players[
            "assists"
        ]
    )


    players[
        "rebounds_assists"
    ] = (
        players[
            "rebounds"
        ]
        + players[
            "assists"
        ]
    )


    return players


def game_from_key(
    game_key,
    games,
):

    if games.empty:
        return None


    parts = str(
        game_key or ""
    ).split(
        "|"
    )


    if len(
        parts
    ) != 3:

        return None


    date_key = parts[
        0
    ]

    away = team(
        parts[
            1
        ]
    )

    home = team(
        parts[
            2
        ]
    )


    match = games[
        games[
            "date_key"
        ].eq(
            date_key
        )
        &
        games[
            "away_team_norm"
        ].eq(
            away
        )
        &
        games[
            "home_team_norm"
        ].eq(
            home
        )
    ]


    if match.empty:
        return None


    final = match[
        match[
            "completed"
        ].map(
            truth
        )
    ]


    if not final.empty:

        return final.iloc[
            -1
        ].to_dict()


    return match.iloc[
        -1
    ].to_dict()


def grade_game(
    row,
    games,
):

    game = game_from_key(
        row.get(
            "game_key"
        ),
        games,
    )


    if not game:

        return {
            "grade":
                "PENDING_GAME_MATCH",

            "context_status":
                "NO_GAME_MATCH",
        }


    base = {
        "result_event_id":
            game.get(
                "event_id",
                "",
            ),

        "season_type":
            game.get(
                "season_type",
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


    if not truth(
        game.get(
            "completed"
        )
    ):

        return {
            **base,

            "grade":
                "PENDING",

            "context_status":
                "GAME_NOT_FINAL",
        }


    home_score = number(
        game.get(
            "home_score"
        )
    )

    away_score = number(
        game.get(
            "away_score"
        )
    )


    if (
        home_score is None
        or away_score is None
    ):

        return {
            **base,

            "grade":
                "UNRESOLVED_SCORE",

            "context_status":
                "FINAL_WITHOUT_SCORE",
        }


    p = payload(
        row
    )


    market = str(
        row.get(
            "market"
        )
        or p.get(
            "market_canonical"
        )
        or ""
    ).upper()


    selection = team(
        row.get(
            "selection"
        )
        or p.get(
            "selection_canonical"
        )
    )


    line = number(
        row.get(
            "line"
        )
        or p.get(
            "line_group"
        )
    )


    home = team(
        game.get(
            "home_team"
        )
    )

    away = team(
        game.get(
            "away_team"
        )
    )


    if market == "MONEYLINE":

        if home_score == away_score:

            grade = "PUSH"

        else:

            winner = (
                home
                if home_score
                > away_score
                else away
            )

            grade = (
                "WIN"
                if selection
                == winner
                else "LOSS"
            )


        return {
            **base,

            "grade":
                grade,

            "context_status":
                "FINAL_SCORE_VERIFIED",

            "actual_value":
                (
                    home_score
                    - away_score
                    if selection
                    == home
                    else
                    away_score
                    - home_score
                ),
        }


    if market == "SPREAD":

        if line is None:

            return {
                **base,

                "grade":
                    "UNRESOLVED_LINE",

                "context_status":
                    "FINAL_SCORE_VERIFIED",
            }


        if selection == home:

            adjusted = (
                home_score
                + line
                - away_score
            )

        elif selection == away:

            adjusted = (
                away_score
                + line
                - home_score
            )

        else:

            return {
                **base,

                "grade":
                    "UNRESOLVED_SELECTION",

                "context_status":
                    "FINAL_SCORE_VERIFIED",
            }


        grade = (
            "WIN"
            if adjusted > 0
            else (
                "LOSS"
                if adjusted < 0
                else "PUSH"
            )
        )


        return {
            **base,

            "grade":
                grade,

            "context_status":
                "FINAL_SCORE_VERIFIED",

            "actual_value":
                adjusted,

            "line_margin":
                adjusted,
        }


    if market == "TOTAL":

        total = (
            home_score
            + away_score
        )


        grade, margin = compare(
            total,
            line,
            row.get(
                "side"
            )
            or row.get(
                "selection"
            ),
        )


        return {
            **base,

            "grade":
                grade,

            "context_status":
                "FINAL_SCORE_VERIFIED",

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
            "MARKET_NOT_MAPPED",
    }


def grade_player(
    row,
    games,
    players,
    prizepicks=False,
):

    game = game_from_key(
        row.get(
            "game_key"
        ),
        games,
    )


    if not game:

        return {
            "grade":
                "PENDING_GAME_MATCH",

            "context_status":
                "NO_GAME_MATCH",
        }


    base = {
        "result_event_id":
            game.get(
                "event_id",
                "",
            ),

        "season_type":
            game.get(
                "season_type",
                "",
            ),
    }


    if not truth(
        game.get(
            "completed"
        )
    ):

        return {
            **base,

            "grade":
                "PENDING",

            "context_status":
                "GAME_NOT_FINAL",
        }


    if players.empty:

        return {
            **base,

            "grade":
                "UNRESOLVED_PLAYER_RESULT",

            "context_status":
                "NO_PLAYER_HISTORY",
        }


    p = payload(
        row
    )


    key = (
        p.get(
            "player_key"
        )
        or pkey(
            row.get(
                "player"
            )
        )
    )


    event_id = str(
        game.get(
            "event_id",
            ""
        )
    )


    result = players[
        players[
            "event_id"
        ].astype(
            str
        ).eq(
            event_id
        )
        &
        players[
            "player_key"
        ].eq(
            key
        )
    ]


    if result.empty:

        return {
            **base,

            "grade":
                "UNRESOLVED_PLAYER_RESULT",

            "context_status":
                "FINAL_GAME_NO_PLAYER_ROW",
        }


    result = result.iloc[
        -1
    ]


    if truth(
        result.get(
            "did_not_play"
        )
    ):

        return {
            **base,

            "grade":
                "VOID",

            "context_status":
                "DNP_VERIFIED",

            "dnp_reason":
                result.get(
                    "dnp_reason",
                    "",
                ),
        }


    stat_type = (
        p.get(
            "stat_type"
        )
        or ""
    )


    stat_col = STAT_MAP.get(
        stat_type
    )


    if not stat_col:

        return {
            **base,

            "grade":
                "UNSUPPORTED_MARKET",

            "context_status":
                "STAT_NOT_MAPPED",
        }


    actual = number(
        result.get(
            stat_col
        )
    )


    if actual is None:

        return {
            **base,

            "grade":
                "UNRESOLVED_PLAYER_RESULT",

            "context_status":
                "STAT_VALUE_MISSING",
        }


    grade, margin = compare(
        actual,
        row.get(
            "line"
        ),
        row.get(
            "side"
        ),
    )


    context_status = (
        "ANALYTIC_STAT_GRADE_"
        "NOT_PLATFORM_SETTLEMENT"
        if prizepicks
        else
        "PLAYED_STAT_VERIFIED"
    )


    return {
        **base,

        "grade":
            grade,

        "context_status":
            context_status,

        "actual_value":
            actual,

        "line_margin":
            margin,

        "stat_column":
            stat_col,

        "minutes":
            result.get(
                "minutes",
                "",
            ),

        "starter":
            result.get(
                "starter",
                "",
            ),

        "dnp_reason":
            result.get(
                "dnp_reason",
                "",
            ),
    }


def same_line(
    a,
    b,
):

    x = number(
        a
    )

    y = number(
        b
    )


    if (
        x is None
        and y is None
    ):
        return True


    if (
        x is None
        or y is None
    ):
        return False


    return abs(
        x - y
    ) < 0.001


def parlay_leg_grade(
    p,
    leg,
    graded,
):

    lane = str(
        p.get(
            f"leg{leg}_lane",
            ""
        )
    ).upper()

    game_key = str(
        p.get(
            f"leg{leg}_game",
            ""
        )
    )

    player = pkey(
        p.get(
            f"leg{leg}_player",
            ""
        )
    )

    market = str(
        p.get(
            f"leg{leg}_market",
            ""
        )
    ).upper()

    selection = str(
        p.get(
            f"leg{leg}_selection",
            ""
        )
    ).upper()

    line = p.get(
        f"leg{leg}_line"
    )


    for row in graded:

        if str(
            row.get(
                "lane",
                ""
            )
        ).upper() != lane:
            continue


        if str(
            row.get(
                "game_key",
                ""
            )
        ) != game_key:
            continue


        if player:

            if pkey(
                row.get(
                    "player"
                )
            ) != player:
                continue


        if str(
            row.get(
                "market",
                ""
            )
        ).upper() != market:
            continue


        pick = str(
            row.get(
                "selection"
            )
            or row.get(
                "side"
            )
            or ""
        ).upper()


        if selection != pick:
            continue


        if not same_line(
            line,
            row.get(
                "line"
            ),
        ):
            continue


        return (
            row.get(
                "grade",
                "UNRESOLVED",
            ),
            row.get(
                "recommendation_key",
                "",
            ),
        )


    return (
        "UNRESOLVED",
        "",
    )


def grade_parlay(
    row,
    graded,
):

    p = payload(
        row
    )


    g1, k1 = parlay_leg_grade(
        p,
        1,
        graded,
    )

    g2, k2 = parlay_leg_grade(
        p,
        2,
        graded,
    )


    states = [
        g1,
        g2,
    ]


    if "LOSS" in states:

        grade = "LOSS"

    elif all(
        x == "WIN"
        for x in states
    ):

        grade = "WIN"

    elif any(
        str(x).startswith(
            "PENDING"
        )
        for x in states
    ):

        grade = "PENDING"

    elif (
        "PUSH" in states
        or "VOID" in states
    ):

        grade = "REVIEW"

    else:

        grade = "UNRESOLVED"


    return {
        "grade":
            grade,

        "context_status":
            "ANALYTIC_PARLAY_GRADE_"
            "NO_PAYOUT_CLAIM",

        "leg1_grade":
            g1,

        "leg2_grade":
            g2,

        "leg1_recommendation_key":
            k1,

        "leg2_recommendation_key":
            k2,
    }


def signal_performance(
    graded,
):

    settled = graded[
        graded[
            "grade"
        ].isin(
            [
                "WIN",
                "LOSS",
                "PUSH",
            ]
        )
    ].copy()


    if settled.empty:

        pd.DataFrame(
            columns=[
                "lane",
                "season_type",
                "decision",
                "market",
                "side",
                "samples",
                "wins",
                "losses",
                "pushes",
                "hit_rate",
                "adjustment_eligible",
            ]
        ).to_csv(
            SIGNALS_OUT,
            index=False,
        )

        return pd.DataFrame()


    rows = []


    for keys, group in settled.groupby(
        [
            "lane",
            "season_type",
            "decision",
            "market",
            "side",
        ],
        dropna=False,
    ):

        (
            lane,
            season_type,
            decision,
            market,
            side,
        ) = keys


        wins = int(
            (
                group[
                    "grade"
                ]
                == "WIN"
            ).sum()
        )

        losses = int(
            (
                group[
                    "grade"
                ]
                == "LOSS"
            ).sum()
        )

        pushes = int(
            (
                group[
                    "grade"
                ]
                == "PUSH"
            ).sum()
        )


        denominator = (
            wins + losses
        )


        rows.append({
            "lane":
                lane,

            "season_type":
                season_type,

            "decision":
                decision,

            "market":
                market,

            "side":
                side,

            "samples":
                len(
                    group
                ),

            "wins":
                wins,

            "losses":
                losses,

            "pushes":
                pushes,

            "hit_rate":
                (
                    wins
                    / denominator
                    if denominator
                    else None
                ),

            "adjustment_eligible":
                denominator >= 25,
        })


    out = pd.DataFrame(
        rows
    )


    out.to_csv(
        SIGNALS_OUT,
        index=False,
    )


    return out


def main():

    ledger = read_csv(
        LEDGER
    )


    if ledger.empty:

        raise SystemExit(
            "NBA recommendation ledger missing."
        )


    ledger[
        "_snap"
    ] = pd.to_datetime(
        ledger[
            "snapshot_at"
        ],
        utc=True,
        errors="coerce",
    )


    # Same recommendation may exist across multiple
    # changed bundles. Grade the latest version once.
    episodes = (
        ledger
        .sort_values(
            "_snap"
        )
        .drop_duplicates(
            "recommendation_key",
            keep="last",
        )
        .drop(
            columns=[
                "_snap"
            ]
        )
    )


    episodes.to_csv(
        EPISODES_OUT,
        index=False,
    )


    games = load_games()

    players = load_players()


    graded_rows = []


    for _, row in episodes.iterrows():

        base = row.to_dict()

        lane = str(
            row.get(
                "lane",
                ""
            )
        ).upper()


        if lane == "GAME":

            result = grade_game(
                base,
                games,
            )


        elif lane == "PROP":

            result = grade_player(
                base,
                games,
                players,
                prizepicks=False,
            )


        elif lane == "PRIZEPICKS":

            result = grade_player(
                base,
                games,
                players,
                prizepicks=True,
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


        graded_rows.append({
            **base,
            **result,
        })


    non_parlay = list(
        graded_rows
    )


    for _, row in episodes.iterrows():

        if str(
            row.get(
                "lane",
                ""
            )
        ).upper() != "PARLAY":

            continue


        base = row.to_dict()


        graded_rows.append({
            **base,

            **grade_parlay(
                base,
                non_parlay,
            ),
        })


    graded = pd.DataFrame(
        graded_rows
    )


    graded.to_csv(
        GRADED_OUT,
        index=False,
    )


    signals = signal_performance(
        graded
    )


    counts = (
        graded[
            "grade"
        ]
        .fillna(
            "UNKNOWN"
        )
        .value_counts()
        .to_dict()
    )


    settled = int(
        graded[
            "grade"
        ].isin(
            [
                "WIN",
                "LOSS",
                "PUSH",
                "VOID",
            ]
        ).sum()
    )


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
                    episodes
                )
            ),

        "graded_rows":
            int(
                len(
                    graded
                )
            ),

        "settled":
            settled,

        "grade_counts":
            {
                str(k):
                    int(v)

                for k, v
                in counts.items()
            },

        "signal_rows":
            int(
                len(
                    signals
                )
            ),

        "minimum_samples_before_adjustment":
            25,

        "automatic_model_adjustment":
            False,

        "prizepicks_platform_settlement_claim":
            False,

        "parlay_payout_claim":
            False,

        "season_types_kept_separate":
            True,
    }


    SUMMARY_OUT.write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
    )


    print(
        "LEDGER ROWS:",
        len(
            ledger
        )
    )

    print(
        "UNIQUE RECOMMENDATIONS:",
        len(
            episodes
        )
    )

    print(
        "SETTLED:",
        settled
    )

    print(
        "GRADE COUNTS:",
        counts
    )

    print(
        "SIGNAL GROUPS:",
        len(
            signals
        )
    )

    print()
    print(
        "RESULT: NBA_LEARNING_READY"
    )


if __name__ == "__main__":
    main()
