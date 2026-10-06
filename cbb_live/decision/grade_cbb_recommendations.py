#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

import json
import math

import pandas as pd


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

CBB = ROOT / "cbb_live"
DEC = CBB / "decision"
HIST = DEC / "history"


LEDGER = (
    HIST
    / "CBB_RECOMMENDATION_LEDGER.csv"
)

CURRENT_GAMES = (
    CBB
    / "derived"
    / "CBB_GAMES_CURRENT.csv"
)

GAME_HISTORY = (
    CBB
    / "history"
    / "CBB_GAME_HISTORY.csv"
)


EPISODES = (
    HIST
    / "CBB_RECOMMENDATION_EPISODES.csv"
)

GRADED = (
    HIST
    / "CBB_GRADED_RECOMMENDATIONS.csv"
)

SIGNALS = (
    HIST
    / "CBB_SIGNAL_PERFORMANCE.csv"
)

OUTCOMES = (
    HIST
    / "CBB_OUTCOME_REVIEW.csv"
)

SUMMARY = (
    HIST
    / "CBB_LEARNING_SUMMARY.json"
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


def id_key(
    value,
):

    x = number(
        value
    )


    if x is not None:

        return str(
            int(
                x
            )
        )


    return str(
        value or ""
    ).strip()


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


def load_games():

    parts = []


    for path in [
        CURRENT_GAMES,
        GAME_HISTORY,
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
        "event_id_key"
    ] = games[
        "event_id"
    ].map(
        id_key
    )


    games[
        "_completed"
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
                "event_id_key",
                "_completed",
            ]
        )
        .drop_duplicates(
            "event_id_key",
            keep="last",
        )
        .drop(
            columns=[
                "_completed"
            ]
        )
    )


    return games


def find_game(
    row,
    games,
):

    if games.empty:
        return None


    event_id = id_key(
        row.get(
            "schedule_event_id"
        )
    )


    if event_id:

        match = games[
            games[
                "event_id_key"
            ].eq(
                event_id
            )
        ]


        if not match.empty:

            return match.iloc[
                -1
            ].to_dict()


    parts = str(
        row.get(
            "game_key",
            ""
        )
    ).split(
        "|"
    )


    if len(
        parts
    ) != 3:

        return None


    game_date = parts[
        0
    ]

    away_id = id_key(
        parts[
            1
        ]
    )

    home_id = id_key(
        parts[
            2
        ]
    )


    match = games[
        games[
            "game_date"
        ]
        .astype(
            str
        )
        .eq(
            game_date
        )
        &
        games[
            "away_team_id"
        ]
        .map(
            id_key
        )
        .eq(
            away_id
        )
        &
        games[
            "home_team_id"
        ]
        .map(
            id_key
        )
        .eq(
            home_id
        )
    ]


    if match.empty:

        return None


    return match.iloc[
        -1
    ].to_dict()


def selected_margin(
    game,
    selection,
):

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

        return None


    selection = str(
        selection
    )


    away = str(
        game.get(
            "away_team",
            ""
        )
    )

    home = str(
        game.get(
            "home_team",
            ""
        )
    )


    if selection == away:

        return (
            away_score
            - home_score
        )


    if selection == home:

        return (
            home_score
            - away_score
        )


    return None


def grade_game(
    row,
    games,
):

    game = find_game(
        row,
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
                ""
            ),

        "season":
            game.get(
                "season",
                ""
            ),

        "season_type":
            game.get(
                "season_type",
                ""
            ),

        "away_score":
            game.get(
                "away_score",
                ""
            ),

        "home_score":
            game.get(
                "home_score",
                ""
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


    selection = str(
        row.get(
            "selection"
        )
        or p.get(
            "selection_canonical"
        )
        or ""
    )


    line = number(
        row.get(
            "line"
        )
    )


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

        return {
            **base,

            "grade":
                "UNRESOLVED_SCORE",

            "context_status":
                "FINAL_WITHOUT_SCORE",
        }


    if market == "MONEYLINE":

        margin = selected_margin(
            game,
            selection,
        )


        if margin is None:

            return {
                **base,

                "grade":
                    "UNRESOLVED_SELECTION",

                "context_status":
                    "TEAM_SELECTION_NOT_MATCHED",
            }


        return {
            **base,

            "grade":
                (
                    "WIN"
                    if margin > 0
                    else "LOSS"
                ),

            "context_status":
                "FINAL_SCORE_VERIFIED",

            "actual_value":
                margin,

            "result_margin":
                margin,
        }


    if market == "SPREAD":

        margin = selected_margin(
            game,
            selection,
        )


        if (
            margin is None
            or line is None
        ):

            return {
                **base,

                "grade":
                    "UNRESOLVED_SPREAD",

                "context_status":
                    "SPREAD_INPUT_MISSING",
            }


        covered = (
            margin
            + line
        )


        if covered > 0:

            grade = "WIN"

        elif covered < 0:

            grade = "LOSS"

        else:

            grade = "PUSH"


        return {
            **base,

            "grade":
                grade,

            "context_status":
                "ANALYTIC_SPREAD_GRADE",

            "actual_value":
                margin,

            "result_margin":
                covered,
        }


    if market == "TOTAL":

        if line is None:

            return {
                **base,

                "grade":
                    "UNRESOLVED_TOTAL",

                "context_status":
                    "TOTAL_LINE_MISSING",
            }


        total = (
            away_score
            + home_score
        )


        if total == line:

            grade = "PUSH"
            margin = 0.0


        elif selection.upper() == "OVER":

            grade = (
                "WIN"
                if total > line
                else "LOSS"
            )

            margin = (
                total
                - line
            )


        elif selection.upper() == "UNDER":

            grade = (
                "WIN"
                if total < line
                else "LOSS"
            )

            margin = (
                line
                - total
            )


        else:

            return {
                **base,

                "grade":
                    "UNRESOLVED_TOTAL",

                "context_status":
                    "TOTAL_SIDE_UNKNOWN",
            }


        return {
            **base,

            "grade":
                grade,

            "context_status":
                "ANALYTIC_TOTAL_GRADE",

            "actual_value":
                total,

            "result_margin":
                margin,
        }


    return {
        **base,

        "grade":
            "UNSUPPORTED_MARKET",

        "context_status":
            "UNKNOWN_MARKET",
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


def grade_parlay(
    row,
    graded_games,
):

    p = payload(
        row
    )


    leg_grades = []


    for leg in [
        1,
        2,
    ]:

        game_key = str(
            p.get(
                f"leg{leg}_game",
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
        )

        line = p.get(
            f"leg{leg}_line"
        )


        found = None


        for candidate in graded_games:

            if (
                candidate.get(
                    "game_key"
                )
                != game_key
            ):

                continue


            if str(
                candidate.get(
                    "market",
                    ""
                )
            ).upper() != market:

                continue


            if str(
                candidate.get(
                    "selection",
                    ""
                )
            ) != selection:

                continue


            if not same_line(
                candidate.get(
                    "line"
                ),
                line,
            ):

                continue


            found = candidate
            break


        if found:

            leg_grades.append(
                found.get(
                    "grade",
                    "UNRESOLVED",
                )
            )

        else:

            leg_grades.append(
                "UNRESOLVED"
            )


    if "LOSS" in leg_grades:

        grade = "LOSS"


    elif all(
        x == "WIN"
        for x in leg_grades
    ):

        grade = "WIN"


    elif any(
        x == "PENDING"
        for x in leg_grades
    ):

        grade = "PENDING"


    elif any(
        x == "PUSH"
        for x in leg_grades
    ):

        grade = "REVIEW"


    else:

        grade = "UNRESOLVED"


    return {
        "grade":
            grade,

        "context_status":
            "ANALYTIC_PARLAY_GRADE_NO_PAYOUT_CLAIM",

        "leg1_grade":
            leg_grades[
                0
            ],

        "leg2_grade":
            leg_grades[
                1
            ],
    }


def evidence_bucket(
    value,
):

    value = number(
        value
    )


    if value is None:
        return "UNKNOWN"

    if value >= 90:
        return "90+"

    if value >= 80:
        return "80-89"

    if value >= 70:
        return "70-79"

    if value >= 60:
        return "60-69"

    return "<60"


def build_outcomes(
    graded,
):

    if graded.empty:

        out = graded.copy()

        out.to_csv(
            OUTCOMES,
            index=False,
        )

        return out


    out = graded.copy()


    def review(
        row,
    ):

        grade = row.get(
            "grade"
        )


        if grade not in {
            "WIN",
            "LOSS",
        }:

            return "UNSETTLED"


        margin = number(
            row.get(
                "result_margin"
            )
        )


        if margin is None:

            return grade


        if grade == "WIN":

            return (
                "CLEAR_WIN"
                if margin >= 3.0
                else "CLOSE_WIN"
            )


        return (
            "CLEAR_LOSS"
            if margin <= -3.0
            else "CLOSE_LOSS"
        )


    out[
        "outcome_review"
    ] = out.apply(
        review,
        axis=1,
    )

    out[
        "evidence_bucket"
    ] = out[
        "score"
    ].map(
        evidence_bucket
    )


    out.to_csv(
        OUTCOMES,
        index=False,
    )


    return out


def build_signals(
    graded,
):

    columns = [
        "lane",
        "season",
        "season_type",
        "market",
        "decision",
        "context_stage",
        "evidence_bucket",
        "samples",
        "wins",
        "losses",
        "pushes",
        "hit_rate",
        "adjustment_eligible",
        "lane_validation_eligible",
    ]


    if graded.empty:

        out = pd.DataFrame(
            columns=columns
        )

        out.to_csv(
            SIGNALS,
            index=False,
        )

        return out


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

        out = pd.DataFrame(
            columns=columns
        )

        out.to_csv(
            SIGNALS,
            index=False,
        )

        return out


    settled[
        "evidence_bucket"
    ] = settled[
        "score"
    ].map(
        evidence_bucket
    )


    rows = []


    for keys, group in settled.groupby(
        [
            "lane",
            "season",
            "season_type",
            "market",
            "decision",
            "context_stage",
            "evidence_bucket",
        ],
        dropna=False,
    ):

        (
            lane,
            season,
            season_type,
            market,
            decision,
            context_stage,
            bucket,
        ) = keys


        wins = int(
            group[
                "grade"
            ]
            .eq(
                "WIN"
            )
            .sum()
        )

        losses = int(
            group[
                "grade"
            ]
            .eq(
                "LOSS"
            )
            .sum()
        )

        pushes = int(
            group[
                "grade"
            ]
            .eq(
                "PUSH"
            )
            .sum()
        )


        denominator = (
            wins
            + losses
        )


        rows.append({
            "lane":
                lane,

            "season":
                season,

            "season_type":
                season_type,

            "market":
                market,

            "decision":
                decision,

            "context_stage":
                context_stage,

            "evidence_bucket":
                bucket,

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

            # Spread/total lane promotion requires
            # a substantially larger settled sample.
            "lane_validation_eligible":
                (
                    denominator >= 100
                ),
        })


    out = pd.DataFrame(
        rows
    )


    out.to_csv(
        SIGNALS,
        index=False,
    )


    return out


def write_empty_outputs():

    empty_columns = [
        "snapshot_at",
        "bundle_hash",
        "lane",
        "recommendation_key",
        "source_file",
        "game_key",
        "schedule_event_id",
        "market",
        "selection",
        "line",
        "decision",
        "score",
        "context_stage",
        "payload_json",
    ]


    episodes = pd.DataFrame(
        columns=empty_columns
    )

    episodes.to_csv(
        EPISODES,
        index=False,
    )


    graded_columns = (
        empty_columns
        + [
            "grade",
            "context_status",
            "result_event_id",
            "season",
            "season_type",
            "away_score",
            "home_score",
            "actual_value",
            "result_margin",
        ]
    )


    graded = pd.DataFrame(
        columns=graded_columns
    )


    graded.to_csv(
        GRADED,
        index=False,
    )

    build_outcomes(
        graded
    )

    signals = build_signals(
        graded
    )


    summary = {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "ledger_rows":
            0,

        "unique_recommendations":
            0,

        "graded_rows":
            0,

        "settled":
            0,

        "grade_counts":
            {},

        "signal_rows":
            int(
                len(
                    signals
                )
            ),

        "minimum_samples_before_adjustment":
            25,

        "minimum_samples_before_lane_validation":
            100,

        "automatic_model_adjustment":
            False,

        "spread_model_validated":
            False,

        "totals_model_validated":
            False,

        "season_types_kept_separate":
            True,

        "parlay_payout_claim":
            False,
    }


    SUMMARY.write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
    )


    print(
        "LEDGER ROWS: 0"
    )

    print(
        "UNIQUE RECOMMENDATIONS: 0"
    )

    print(
        "SETTLED: 0"
    )

    print(
        "RESULT: CBB_LEARNING_READY"
    )


def main():

    ledger = read_csv(
        LEDGER
    )


    if ledger.empty:

        write_empty_outputs()

        return


    ledger[
        "_snapshot"
    ] = pd.to_datetime(
        ledger[
            "snapshot_at"
        ],
        utc=True,
        errors="coerce",
    )


    episodes = (
        ledger
        .sort_values(
            "_snapshot"
        )
        .drop_duplicates(
            "recommendation_key",
            keep="last",
        )
        .drop(
            columns=[
                "_snapshot"
            ]
        )
    )


    episodes.to_csv(
        EPISODES,
        index=False,
    )


    games = load_games()


    graded_rows = []


    for _, row in episodes.iterrows():

        lane = str(
            row.get(
                "lane",
                ""
            )
        ).upper()


        if lane == "PARLAY":
            continue


        result = grade_game(
            row.to_dict(),
            games,
        )


        graded_rows.append({
            **row.to_dict(),
            **result,
        })


    graded_games = list(
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


        graded_rows.append({
            **row.to_dict(),

            **grade_parlay(
                row.to_dict(),
                graded_games,
            ),
        })


    graded = pd.DataFrame(
        graded_rows
    )


    if graded.empty:

        write_empty_outputs()

        return


    graded.to_csv(
        GRADED,
        index=False,
    )


    outcomes = build_outcomes(
        graded
    )

    signals = build_signals(
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
                str(
                    key
                ):
                    int(
                        value
                    )

                for key, value
                in counts.items()
            },

        "signal_rows":
            int(
                len(
                    signals
                )
            ),

        "outcome_review_rows":
            int(
                len(
                    outcomes
                )
            ),

        "minimum_samples_before_adjustment":
            25,

        "minimum_samples_before_lane_validation":
            100,

        "automatic_model_adjustment":
            False,

        "spread_model_validated":
            False,

        "totals_model_validated":
            False,

        "season_types_kept_separate":
            True,

        "parlay_payout_claim":
            False,
    }


    SUMMARY.write_text(
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
        "RESULT: CBB_LEARNING_READY"
    )


if __name__ == "__main__":
    main()
