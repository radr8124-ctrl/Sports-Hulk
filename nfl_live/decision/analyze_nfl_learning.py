#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime, timezone

import json
import math

import numpy as np
import pandas as pd


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

HIST = (
    ROOT
    / "nfl_live"
    / "decision"
    / "history"
)

GRADED = (
    HIST
    / "NFL_GRADED_RECOMMENDATIONS.csv"
)

OUTCOMES = (
    HIST
    / "NFL_OUTCOME_REVIEW.csv"
)

SIGNALS = (
    HIST
    / "NFL_SIGNAL_PERFORMANCE.csv"
)

PARLAY_LEGS = (
    HIST
    / "NFL_PARLAY_LEG_PERFORMANCE.csv"
)

REPORT = (
    HIST
    / "NFL_LEARNING_REPORT.json"
)


MIN_REVIEW_SAMPLE = 5

MIN_SIGNAL_SAMPLE = 10

MIN_ADJUSTMENT_SAMPLE = 25


def number(
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


def payload(
    value,
):

    try:

        return json.loads(
            value
        )

    except Exception:

        return {}


def pct(
    wins,
    losses,
):

    denominator = (
        wins
        + losses
    )

    if denominator <= 0:
        return None

    return (
        wins
        / denominator
    )


def miss_size(
    actual,
    line,
):

    actual = number(
        actual
    )

    line = number(
        line
    )

    if (
        actual is None
        or line is None
    ):

        return None

    return abs(
        actual
        - line
    )


def outcome_shape(
    row,
):

    grade = str(
        row.get(
            "grade",
            ""
        )
    ).upper()


    if grade == "PENDING":

        return "PENDING"


    if grade == "PUSH":

        return "PUSH"


    if grade not in {
        "WIN",
        "LOSS",
    }:

        return "UNRESOLVED"


    lane = str(
        row.get(
            "lane",
            ""
        )
    ).upper()


    if lane in {
        "PROP",
        "PRIZEPICKS",
    }:

        distance = miss_size(
            row.get(
                "actual_value"
            ),
            row.get(
                "line"
            ),
        )


        if distance is None:

            return (
                "VERIFIED_WIN"
                if grade == "WIN"
                else "VERIFIED_LOSS"
            )


        if distance <= 0.5:

            prefix = "VERY_CLOSE"

        elif distance <= 2.0:

            prefix = "CLOSE"

        else:

            prefix = "CLEAR"


        return (
            prefix
            + "_"
            + grade
        )


    if lane == "GAME":

        margin = number(
            row.get(
                "line_margin"
            )
        )


        if margin is None:

            return (
                "VERIFIED_"
                + grade
            )


        distance = abs(
            margin
        )


        if distance <= 1.0:

            prefix = "VERY_CLOSE"

        elif distance <= 3.0:

            prefix = "CLOSE"

        else:

            prefix = "CLEAR"


        return (
            prefix
            + "_"
            + grade
        )


    return (
        "VERIFIED_"
        + grade
    )


def extract_features(
    row,
):

    p = payload(
        row.get(
            "payload_json",
            ""
        )
    )


    features = {}


    def add(
        name,
        value,
    ):

        value = str(
            value
            if value is not None
            else ""
        ).strip()

        if value and value.lower() != "nan":

            features[
                name
            ] = value


    add(
        "lane",
        row.get(
            "lane"
        ),
    )

    add(
        "market",
        row.get(
            "market"
        ),
    )

    add(
        "decision",
        row.get(
            "decision"
        ),
    )

    add(
        "side",
        row.get(
            "side"
        )
        or row.get(
            "selection"
        ),
    )


    # Shared player-prop evidence
    for field in [
        "coverage_grade",
        "context_direction",
        "context_coverage",
        "context_readiness",
        "sample_gate",
        "decision_before_sample_gate",
        "espn_injury_gate",
        "availability_flag",
        "identity_status",
        "player_key_sanity",
        "market_role",
    ]:

        add(
            field,
            p.get(
                field
            ),
        )


    # Game evidence
    for field in [
        "market_data_quality",
        "provider_agreement",
        "model_status",
        "oddspapi_status",
        "therundown_verified",
    ]:

        add(
            field,
            p.get(
                field
            ),
        )


    # Sample-count buckets
    meaningful = number(
        p.get(
            "meaningful_completed_games"
        )
    )


    if meaningful is not None:

        if meaningful < 3:
            bucket = "LT3"

        elif meaningful < 5:
            bucket = "3_TO_4"

        elif meaningful < 10:
            bucket = "5_TO_9"

        else:
            bucket = "10_PLUS"


        add(
            "meaningful_games_bucket",
            bucket,
        )


    books = number(
        p.get(
            "book_count"
        )
        or p.get(
            "oddspapi_bookmaker_count"
        )
    )


    if books is not None:

        if books < 2:
            bucket = "LT2"

        elif books < 5:
            bucket = "2_TO_4"

        elif books < 10:
            bucket = "5_TO_9"

        else:
            bucket = "10_PLUS"


        add(
            "book_count_bucket",
            bucket,
        )


    # Evidence-score buckets
    score = number(
        row.get(
            "score"
        )
    )


    if score is not None:

        if score >= 85:
            bucket = "85_PLUS"

        elif score >= 75:
            bucket = "75_TO_84"

        elif score >= 65:
            bucket = "65_TO_74"

        else:
            bucket = "LT65"


        add(
            "score_bucket",
            bucket,
        )


    return features


def Wilson_lower(
    wins,
    losses,
    z=1.96,
):

    n = (
        wins
        + losses
    )

    if n <= 0:
        return None


    phat = (
        wins
        / n
    )


    denominator = (
        1
        + z * z / n
    )


    centre = (
        phat
        + z * z / (2 * n)
    )


    spread = (
        z
        * math.sqrt(
            (
                phat
                * (
                    1 - phat
                )
                + z * z / (4 * n)
            )
            / n
        )
    )


    return (
        centre
        - spread
    ) / denominator


def Wilson_upper(
    wins,
    losses,
    z=1.96,
):

    n = (
        wins
        + losses
    )

    if n <= 0:
        return None


    phat = (
        wins
        / n
    )


    denominator = (
        1
        + z * z / n
    )


    centre = (
        phat
        + z * z / (2 * n)
    )


    spread = (
        z
        * math.sqrt(
            (
                phat
                * (
                    1 - phat
                )
                + z * z / (4 * n)
            )
            / n
        )
    )


    return (
        centre
        + spread
    ) / denominator


def main():

    if not GRADED.exists():

        raise SystemExit(
            "No graded NFL history found."
        )


    df = pd.read_csv(
        GRADED,
        low_memory=False,
    )


    print(
        "GRADED ROWS:",
        len(
            df
        ),
    )


    df[
        "outcome_shape"
    ] = df.apply(
        outcome_shape,
        axis=1,
    )


    df[
        "review_status"
    ] = np.where(
        df[
            "grade"
        ].isin(
            [
                "WIN",
                "LOSS",
                "PUSH",
            ]
        ),
        "SETTLED",
        "WAITING",
    )


    df.to_csv(
        OUTCOMES,
        index=False,
    )


    settled = df[
        df[
            "grade"
        ].isin(
            [
                "WIN",
                "LOSS",
                "PUSH",
            ]
        )
    ].copy()


    feature_rows = []


    for _, row in settled.iterrows():

        features = extract_features(
            row
        )


        for feature, value in (
            features.items()
        ):

            feature_rows.append(
                {
                    "lane":
                        row.get(
                            "lane",
                            "",
                        ),

                    "feature":
                        feature,

                    "value":
                        value,

                    "grade":
                        row.get(
                            "grade",
                            "",
                        ),

                    "recommendation_key":
                        row.get(
                            "recommendation_key",
                            "",
                        ),
                }
            )


    signal_df = pd.DataFrame(
        feature_rows
    )


    performance_rows = []


    if not signal_df.empty:

        for (
            lane,
            feature,
            value,
        ), group in signal_df.groupby(
            [
                "lane",
                "feature",
                "value",
            ],
            dropna=False,
        ):

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

            decisions = (
                wins
                + losses
            )


            hit_rate = pct(
                wins,
                losses,
            )


            performance_rows.append(
                {
                    "lane":
                        lane,

                    "feature":
                        feature,

                    "value":
                        value,

                    "samples":
                        len(
                            group
                        ),

                    "decisions":
                        decisions,

                    "wins":
                        wins,

                    "losses":
                        losses,

                    "pushes":
                        pushes,

                    "hit_rate":
                        hit_rate,

                    "wilson_low":
                        Wilson_lower(
                            wins,
                            losses,
                        ),

                    "wilson_high":
                        Wilson_upper(
                            wins,
                            losses,
                        ),

                    "review_ready":
                        decisions
                        >= MIN_REVIEW_SAMPLE,

                    "signal_ready":
                        decisions
                        >= MIN_SIGNAL_SAMPLE,

                    "adjustment_eligible":
                        decisions
                        >= MIN_ADJUSTMENT_SAMPLE,
                }
            )


    performance = pd.DataFrame(
        performance_rows
    )


    if not performance.empty:

        performance = (
            performance
            .sort_values(
                [
                    "decisions",
                    "hit_rate",
                ],
                ascending=[
                    False,
                    False,
                ],
            )
        )


    performance.to_csv(
        SIGNALS,
        index=False,
    )


    # =============================================
    # PARLAY LEG STUDY
    # =============================================

    parlays = df[
        df[
            "lane"
        ].eq(
            "PARLAY"
        )
    ].copy()


    leg_rows = []


    for _, row in parlays.iterrows():

        p = payload(
            row.get(
                "payload_json",
                ""
            )
        )


        for leg in [
            1,
            2,
        ]:

            grade = row.get(
                f"leg{leg}_grade",
                "",
            )


            leg_rows.append(
                {
                    "parlay_recommendation_key":
                        row.get(
                            "recommendation_key",
                            "",
                        ),

                    "parlay_grade":
                        row.get(
                            "grade",
                            "",
                        ),

                    "leg_number":
                        leg,

                    "leg_kind":
                        p.get(
                            f"leg{leg}_kind",
                            "",
                        ),

                    "leg_market":
                        p.get(
                            f"leg{leg}_market",
                            "",
                        ),

                    "leg_selection":
                        p.get(
                            f"leg{leg}_selection",
                            "",
                        ),

                    "leg_grade":
                        grade,
                }
            )


    pd.DataFrame(
        leg_rows
    ).to_csv(
        PARLAY_LEGS,
        index=False,
    )


    settled_count = int(
        len(
            settled
        )
    )


    report = {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "total_recommendations":
            int(
                len(
                    df
                )
            ),

        "settled":
            settled_count,

        "waiting":
            int(
                len(
                    df
                )
                - settled_count
            ),

        "minimum_samples": {
            "review":
                MIN_REVIEW_SAMPLE,

            "signal":
                MIN_SIGNAL_SAMPLE,

            "automatic_adjustment":
                MIN_ADJUSTMENT_SAMPLE,
        },

        "automatic_adjustment_enabled":
            False,

        "policy":
            (
                "OBSERVE_MEASURE_VALIDATE_"
                "BEFORE_MODEL_CHANGE"
            ),

        "signal_rows":
            int(
                len(
                    performance
                )
            ),

        "adjustment_eligible_signals":
            int(
                (
                    performance[
                        "adjustment_eligible"
                    ]
                    == True
                ).sum()
            )
            if (
                not performance.empty
                and "adjustment_eligible"
                in performance.columns
            )
            else 0,
    }


    REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )


    print()
    print(
        "SETTLED:",
        settled_count,
    )

    print(
        "WAITING:",
        report[
            "waiting"
        ],
    )

    print(
        "SIGNAL GROUPS:",
        report[
            "signal_rows"
        ],
    )

    print(
        "ADJUSTMENT ELIGIBLE:",
        report[
            "adjustment_eligible_signals"
        ],
    )

    print()
    print(
        "AUTOMATIC MODEL ADJUSTMENT: OFF"
    )

    print(
        "SPORTS HULK NFL OUTCOME REVIEW: DONE"
    )


if __name__ == "__main__":
    main()
