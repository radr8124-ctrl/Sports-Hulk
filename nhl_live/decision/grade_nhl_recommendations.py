#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

import json
import math
import re
import unicodedata

import pandas as pd


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

NHL = ROOT / "nhl_live"
DEC = NHL / "decision"
HIST = DEC / "history"


LEDGER = (
    HIST
    / "NHL_RECOMMENDATION_LEDGER.csv"
)

CURRENT_GAMES = (
    NHL
    / "derived"
    / "NHL_GAMES_CURRENT.csv"
)

GAME_HISTORY = (
    NHL
    / "history"
    / "NHL_GAME_HISTORY.csv"
)

PLAYER_HISTORY = (
    NHL
    / "history"
    / "NHL_PLAYER_GAME_HISTORY.csv"
)

GOALIE_HISTORY = (
    NHL
    / "history"
    / "NHL_GOALIE_GAME_HISTORY.csv"
)


EPISODES_OUT = (
    HIST
    / "NHL_RECOMMENDATION_EPISODES.csv"
)

GRADED_OUT = (
    HIST
    / "NHL_GRADED_RECOMMENDATIONS.csv"
)

SIGNALS_OUT = (
    HIST
    / "NHL_SIGNAL_PERFORMANCE.csv"
)

OUTCOME_OUT = (
    HIST
    / "NHL_OUTCOME_REVIEW.csv"
)

SUMMARY_OUT = (
    HIST
    / "NHL_LEARNING_SUMMARY.json"
)


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


def ascii_key(
    value,
):

    text = (
        unicodedata
        .normalize(
            "NFKD",
            str(
                value or ""
            ),
        )
        .encode(
            "ascii",
            "ignore",
        )
        .decode()
    )

    return re.sub(
        r"[^a-z0-9]+",
        "",
        text.lower(),
    )


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


    if (
        actual is None
        or line is None
    ):

        return (
            "UNRESOLVED",
            None,
        )


    side = str(
        side or ""
    ).upper()


    raw_margin = (
        actual
        - line
    )


    if actual == line:

        return (
            "PUSH",
            0.0,
        )


    if side == "OVER":

        return (
            (
                "WIN"
                if actual > line
                else "LOSS"
            ),
            raw_margin,
        )


    if side == "UNDER":

        return (
            (
                "WIN"
                if actual < line
                else "LOSS"
            ),
            -raw_margin,
        )


    return (
        "UNRESOLVED",
        None,
    )


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

    away = parts[
        1
    ]

    home = parts[
        2
    ]


    match = games[
        games[
            "game_date"
        ]
        .astype(
            str
        )
        .eq(
            date_key
        )
        &
        games[
            "away_team"
        ]
        .astype(
            str
        )
        .eq(
            away
        )
        &
        games[
            "home_team"
        ]
        .astype(
            str
        )
        .eq(
            home
        )
    ]


    if match.empty:
        return None


    finals = match[
        match[
            "completed"
        ].map(
            truth
        )
    ]


    if not finals.empty:

        return finals.iloc[
            -1
        ].to_dict()


    return match.iloc[
        -1
    ].to_dict()


def load_player_history():

    players = read_csv(
        PLAYER_HISTORY
    )


    if players.empty:
        return players


    players[
        "event_id_key"
    ] = players[
        "event_id"
    ].map(
        id_key
    )

    players[
        "player_id_key"
    ] = players[
        "player_id"
    ].map(
        id_key
    )


    return players


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
                ""
            ),

        "game_type":
            game.get(
                "game_type",
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
    ).upper()


    away = str(
        game.get(
            "away_team",
            ""
        )
    ).upper()

    home = str(
        game.get(
            "home_team",
            ""
        )
    ).upper()


    if market == "MONEYLINE":

        winner = (
            home
            if home_score
            > away_score
            else away
        )


        selected_margin = (
            home_score
            - away_score
            if selection
            == home
            else
            away_score
            - home_score
        )


        return {
            **base,

            "grade":
                (
                    "WIN"
                    if selection
                    == winner
                    else "LOSS"
                ),

            "context_status":
                "FINAL_SCORE_VERIFIED",

            "actual_value":
                selected_margin,

            "result_margin":
                selected_margin,
        }


    return {
        **base,

        "grade":
            "UNSUPPORTED_MARKET",

        "context_status":
            "GAME_MARKET_NOT_VALIDATED",
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
                ""
            ),

        "game_type":
            game.get(
                "game_type",
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


    if players.empty:

        return {
            **base,

            "grade":
                "UNRESOLVED_PLAYER_RESULT",

            "context_status":
                "NO_PLAYER_HISTORY",
        }


    event_id = id_key(
        game.get(
            "event_id"
        )
    )

    player_id = id_key(
        row.get(
            "nhl_player_id"
        )
    )


    result = players[
        players[
            "event_id_key"
        ].eq(
            event_id
        )
        &
        players[
            "player_id_key"
        ].eq(
            player_id
        )
    ]


    if result.empty:

        return {
            **base,

            "grade":
                "DNP",

            "context_status":
                (
                    "FINAL_GAME_PLAYER_NOT_IN_BOXSCORE_"
                    "NO_PLATFORM_SETTLEMENT_CLAIM"
                ),
        }


    result = result.iloc[
        -1
    ]


    stat_type = str(
        row.get(
            "stat_type",
            ""
        )
    )


    if stat_type not in result.index:

        return {
            **base,

            "grade":
                "UNSUPPORTED_STAT",

            "context_status":
                "STAT_NOT_IN_BOXSCORE_HISTORY",
        }


    actual = number(
        result.get(
            stat_type
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


    return {
        **base,

        "grade":
            grade,

        "context_status":
            (
                "ANALYTIC_STAT_GRADE_"
                "NO_PLATFORM_SETTLEMENT_CLAIM"
                if prizepicks
                else
                "OFFICIAL_BOXSCORE_STAT_VERIFIED"
            ),

        "actual_value":
            actual,

        "result_margin":
            margin,

        "stat_column":
            stat_type,

        "toi_minutes":
            result.get(
                "toi_minutes",
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


def parlay_leg(
    payload_row,
    leg,
    graded,
):

    lane = str(
        payload_row.get(
            f"leg{leg}_lane",
            ""
        )
    ).upper()

    game_key = str(
        payload_row.get(
            f"leg{leg}_game",
            ""
        )
    )

    player = ascii_key(
        payload_row.get(
            f"leg{leg}_player",
            ""
        )
    )

    market = str(
        payload_row.get(
            f"leg{leg}_market",
            ""
        )
    ).upper()

    selection = str(
        payload_row.get(
            f"leg{leg}_selection",
            ""
        )
    ).upper()

    line = payload_row.get(
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

            if ascii_key(
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


        side = str(
            row.get(
                "selection"
            )
            or row.get(
                "side"
            )
            or ""
        ).upper()


        if side != selection:

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
    non_parlay,
):

    p = payload(
        row
    )


    g1, k1 = parlay_leg(
        p,
        1,
        non_parlay,
    )

    g2, k2 = parlay_leg(
        p,
        2,
        non_parlay,
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
        x == "PENDING"
        for x in states
    ):

        grade = "PENDING"


    elif (
        "DNP" in states
        or "PUSH" in states
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
            g1,

        "leg2_grade":
            g2,

        "leg1_recommendation_key":
            k1,

        "leg2_recommendation_key":
            k2,
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

    return "<70"


def build_outcome_review(
    graded,
):

    out = graded.copy()


    if out.empty:

        out.to_csv(
            OUTCOME_OUT,
            index=False,
        )

        return out


    def label(
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

            return (
                "WIN"
                if grade
                == "WIN"
                else "LOSS"
            )


        if grade == "WIN":

            return (
                "CLEAR_WIN"
                if margin >= 1.0
                else "CLOSE_WIN"
            )


        return (
            "CLEAR_LOSS"
            if margin <= -1.0
            else "CLOSE_LOSS"
        )


    out[
        "outcome_review"
    ] = out.apply(
        label,
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
        OUTCOME_OUT,
        index=False,
    )


    return out


def build_signals(
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


    columns = [
        "lane",
        "game_type",
        "decision",
        "market",
        "stat_type",
        "side",
        "evidence_bucket",
        "samples",
        "wins",
        "losses",
        "pushes",
        "hit_rate",
        "adjustment_eligible",
    ]


    if settled.empty:

        out = pd.DataFrame(
            columns=columns
        )

        out.to_csv(
            SIGNALS_OUT,
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
            "game_type",
            "decision",
            "market",
            "stat_type",
            "side",
            "evidence_bucket",
        ],
        dropna=False,
    ):

        (
            lane,
            game_type,
            decision,
            market,
            stat_type,
            side,
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

            "game_type":
                game_type,

            "decision":
                decision,

            "market":
                market,

            "stat_type":
                stat_type,

            "side":
                side,

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
            "NHL recommendation ledger missing."
        )


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
        EPISODES_OUT,
        index=False,
    )


    games = load_games()

    players = load_player_history()


    graded_rows = []


    for _, row in episodes.iterrows():

        base = row.to_dict()

        lane = str(
            row.get(
                "lane",
                ""
            )
        ).upper()


        if lane == "PARLAY":
            continue


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


    outcome = build_outcome_review(
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
                    outcome
                )
            ),

        "minimum_samples_before_adjustment":
            25,

        "automatic_model_adjustment":
            False,

        "game_types_kept_separate":
            True,

        "prizepicks_platform_settlement_claim":
            False,

        "parlay_payout_claim":
            False,

        "dnp_is_not_loss":
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
        "RESULT: NHL_LEARNING_READY"
    )


if __name__ == "__main__":
    main()
