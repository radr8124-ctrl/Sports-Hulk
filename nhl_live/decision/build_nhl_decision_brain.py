#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import itertools
import json
import math
import re
import unicodedata

import numpy as np
import pandas as pd


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

NHL = ROOT / "nhl_live"
DEC = NHL / "decision"
MARKETS = NHL / "markets" / "current"
DERIVED = NHL / "derived"
HISTORY = NHL / "history"


GAME_FUSION = (
    MARKETS
    / "NHL_GAME_MARKET_FUSION.csv"
)

PROP_FUSION = (
    MARKETS
    / "NHL_PROP_FUSION.csv"
)

PP_FUSION = (
    MARKETS
    / "NHL_PRIZEPICKS_FUSION.csv"
)

TEAM_HISTORY = (
    HISTORY
    / "NHL_TEAM_GAME_HISTORY.csv"
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

INJURIES = (
    DERIVED
    / "NHL_INJURIES_CURRENT.csv"
)


GAME_DECISIONS = (
    DEC
    / "NHL_GAME_DECISIONS.csv"
)

GAME_FINALISTS = (
    DEC
    / "NHL_GAME_FINALISTS.csv"
)

PROP_DECISIONS = (
    DEC
    / "NHL_PROP_DECISIONS.csv"
)

PROP_FINALISTS = (
    DEC
    / "NHL_PROP_FINALISTS.csv"
)

PP_DECISIONS = (
    DEC
    / "NHL_PRIZEPICKS_DECISIONS.csv"
)

PP_FINALISTS = (
    DEC
    / "NHL_PRIZEPICKS_FINALISTS.csv"
)

FANTASY = (
    DEC
    / "NHL_FANTASY_WATCHLIST.csv"
)

PARLAYS = (
    DEC
    / "NHL_PARLAYS_TODAY.csv"
)

SUMMARY = (
    DEC
    / "NHL_DECISION_SUMMARY.json"
)


NOW = pd.Timestamp.now(
    tz="UTC"
)

ET = ZoneInfo(
    "America/New_York"
)


NON_BOOKS = {
    "kalshi",
    "polymarket",
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


def canonical_numeric_id(value):

    numeric = number(value)

    if numeric is not None and float(numeric).is_integer():
        return str(int(numeric))

    return str(value or "").strip()


def clamp(
    value,
    low=0.0,
    high=100.0,
):

    return max(
        low,
        min(
            high,
            float(
                value
            ),
        ),
    )


def ascii_key(
    value,
):

    value = (
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
        value.lower(),
    )


def hours_until(
    value,
):

    dt = pd.to_datetime(
        value,
        utc=True,
        errors="coerce",
        format="mixed",
    )

    if pd.isna(
        dt
    ):
        return None

    return (
        dt - NOW
    ).total_seconds() / 3600


def raw_book_support(
    price,
):

    price = number(
        price
    )

    if price is None:
        return None

    if price < 0:

        return (
            -price
            / (
                -price
                + 100.0
            )
        )

    if price > 0:

        return (
            100.0
            / (
                price
                + 100.0
            )
        )

    return 0.5


def approved_book_count(
    books,
):

    values = {
        str(
            x
        ).strip().lower()

        for x in str(
            books or ""
        ).split(
            "|"
        )

        if str(
            x
        ).strip()
    }

    return len(
        values
        - NON_BOOKS
    )


def sane_prop_price(
    price,
):

    price = number(
        price
    )

    if price is None:
        return False

    # Avoid turning extreme juice into a
    # "strong" research recommendation.
    return (
        -250
        <= price
        <= 250
    )


# ============================================================
# TEAM CONTEXT
# ============================================================

def build_team_form():

    df = read_csv(
        TEAM_HISTORY
    )

    if df.empty:
        return {}


    if "game_type" in df.columns:

        gt = pd.to_numeric(
            df[
                "game_type"
            ],
            errors="coerce",
        )

        # Regular season + postseason only.
        df = df[
            gt.isin(
                [
                    2,
                    3,
                ]
            )
        ].copy()


    df[
        "start_dt"
    ] = pd.to_datetime(
        df[
            "start"
        ],
        utc=True,
        errors="coerce",
    )


    numeric = [
        "goals_for",
        "goals_against",
        "win",
        "shots_on_goal",
        "power_play_goals",
        "starting_goalie_save_pct",
    ]


    for col in numeric:

        if col in df.columns:

            df[
                col
            ] = pd.to_numeric(
                df[
                    col
                ],
                errors="coerce",
            )


    df[
        "goal_margin"
    ] = (
        df[
            "goals_for"
        ]
        - df[
            "goals_against"
        ]
    )


    out = {}


    for club, group in df.groupby(
        "team"
    ):

        group = group.sort_values(
            "start_dt"
        )

        l5 = group.tail(
            5
        )

        l10 = group.tail(
            10
        )


        out[
            str(
                club
            )
        ] = {
            "games":
                int(
                    len(
                        group
                    )
                ),

            "win_rate_l5":
                float(
                    l5[
                        "win"
                    ].mean()
                )
                if len(
                    l5
                )
                else None,

            "win_rate_l10":
                float(
                    l10[
                        "win"
                    ].mean()
                )
                if len(
                    l10
                )
                else None,

            "goal_margin_l5":
                float(
                    l5[
                        "goal_margin"
                    ].mean()
                )
                if len(
                    l5
                )
                else None,

            "goal_margin_l10":
                float(
                    l10[
                        "goal_margin"
                    ].mean()
                )
                if len(
                    l10
                )
                else None,

            "goals_for_l10":
                float(
                    l10[
                        "goals_for"
                    ].mean()
                )
                if len(
                    l10
                )
                else None,

            "goals_against_l10":
                float(
                    l10[
                        "goals_against"
                    ].mean()
                )
                if len(
                    l10
                )
                else None,

            "shots_for_l10":
                float(
                    l10[
                        "shots_on_goal"
                    ].mean()
                )
                if len(
                    l10
                )
                else None,

            "pp_goals_l10":
                float(
                    l10[
                        "power_play_goals"
                    ].mean()
                )
                if len(
                    l10
                )
                else None,

            "goalie_save_pct_l10":
                float(
                    l10[
                        "starting_goalie_save_pct"
                    ].mean()
                )
                if (
                    len(
                        l10
                    )
                    and
                    "starting_goalie_save_pct"
                    in l10.columns
                )
                else None,
        }


    return out


# ============================================================
# INJURY COUNTS FOR CONTEXT DISPLAY
# ============================================================

def current_injury_counts():

    df = read_csv(
        INJURIES
    )

    if df.empty:
        return {}


    counts = {}


    for club, group in df.groupby(
        "team"
    ):

        blocked = int(
            group[
                "injury_gate"
            ]
            .astype(
                str
            )
            .eq(
                "BLOCK"
            )
            .sum()
        )

        review = int(
            group[
                "injury_gate"
            ]
            .astype(
                str
            )
            .eq(
                "REVIEW"
            )
            .sum()
        )


        counts[
            str(
                club
            )
        ] = {
            "block":
                blocked,

            "review":
                review,
        }


    return counts


# ============================================================
# GAME DECISIONS
# ============================================================

def build_game_decisions(
    forms,
    injuries,
):

    df = read_csv(
        GAME_FUSION
    )


    if df.empty:

        pd.DataFrame().to_csv(
            GAME_DECISIONS,
            index=False,
        )

        pd.DataFrame().to_csv(
            GAME_FINALISTS,
            index=False,
        )

        return pd.DataFrame()


    rows = []


    for _, row in df.iterrows():

        hours = hours_until(
            row.get(
                "start_dt"
            )
        )


        if (
            hours is None
            or hours < -1
            or hours > 14 * 24
        ):
            continue


        market = str(
            row.get(
                "market_canonical",
                ""
            )
        ).upper()

        selection = str(
            row.get(
                "selection_canonical",
                ""
            )
        ).upper()

        away = str(
            row.get(
                "away_team_canonical",
                ""
            )
        )

        home = str(
            row.get(
                "home_team_canonical",
                ""
            )
        )


        books = approved_book_count(
            row.get(
                "sportsbooks"
            )
        )

        providers = int(
            number(
                row.get(
                    "provider_count"
                )
            )
            or 0
        )

        support = raw_book_support(
            row.get(
                "median_price_american"
            )
        )


        score = 42.0


        if books >= 8:
            score += 18

        elif books >= 5:
            score += 14

        elif books >= 3:
            score += 10

        elif books >= 2:
            score += 6


        if providers >= 2:
            score += 6


        if support is not None:

            if support >= 0.62:
                score += 8

            elif support >= 0.57:
                score += 5

            elif support >= 0.53:
                score += 3


        context_direction = "MIXED"
        historical_value = None


        if market in {
            "MONEYLINE",
            "SPREAD",
        }:

            selected = selection

            opponent = (
                home
                if selected == away
                else away
            )


            sf = forms.get(
                selected,
                {}
            )

            of = forms.get(
                opponent,
                {}
            )


            margin = sf.get(
                "goal_margin_l10"
            )

            opp_margin = of.get(
                "goal_margin_l10"
            )

            wins = sf.get(
                "win_rate_l10"
            )

            shots = sf.get(
                "shots_for_l10"
            )

            opp_shots = of.get(
                "shots_for_l10"
            )


            historical_value = margin


            if (
                margin is not None
                and margin >= 0.6
            ):

                score += 9

            elif (
                margin is not None
                and margin <= -0.6
            ):

                score -= 7


            if (
                wins is not None
                and wins >= 0.60
            ):

                score += 7


            if (
                opp_margin is not None
                and opp_margin <= -0.5
            ):

                score += 4


            if (
                shots is not None
                and opp_shots is not None
                and shots
                >= opp_shots
                + 2.0
            ):

                score += 4


            if (
                margin is not None
                and margin > 0
                and wins is not None
                and wins >= 0.50
            ):

                context_direction = "SUPPORT"


            elif (
                margin is not None
                and margin < 0
                and wins is not None
                and wins < 0.50
            ):

                context_direction = "OPPOSE"


        elif market == "TOTAL":

            af = forms.get(
                away,
                {}
            )

            hf = forms.get(
                home,
                {}
            )

            line = number(
                row.get(
                    "line_group"
                )
            )


            if line is not None:

                values = [
                    af.get(
                        "goals_for_l10"
                    ),
                    af.get(
                        "goals_against_l10"
                    ),
                    hf.get(
                        "goals_for_l10"
                    ),
                    hf.get(
                        "goals_against_l10"
                    ),
                ]


                values = [
                    x
                    for x in values
                    if x is not None
                ]


                if len(
                    values
                ) == 4:

                    expected = (
                        (
                            af[
                                "goals_for_l10"
                            ]
                            + hf[
                                "goals_against_l10"
                            ]
                        )
                        / 2.0
                        +
                        (
                            hf[
                                "goals_for_l10"
                            ]
                            + af[
                                "goals_against_l10"
                            ]
                        )
                        / 2.0
                    )

                    historical_value = expected

                    edge = (
                        expected
                        - line
                    )


                    if (
                        selection == "OVER"
                        and edge >= 0.75
                    ):

                        context_direction = "SUPPORT"
                        score += 8


                    elif (
                        selection == "UNDER"
                        and edge <= -0.75
                    ):

                        context_direction = "SUPPORT"
                        score += 8


                    elif abs(
                        edge
                    ) >= 0.75:

                        context_direction = "OPPOSE"
                        score -= 6


        score = clamp(
            score
        )


        away_inj = injuries.get(
            away,
            {
                "block":
                    0,

                "review":
                    0,
            },
        )

        home_inj = injuries.get(
            home,
            {
                "block":
                    0,

                "review":
                    0,
            },
        )


        # NHL game finalists are deliberately
        # MONEYLINE only until puckline/total
        # grading history proves those lanes.
        if hours > 48:

            decision = (
                "EARLY_MARKET_WATCH"
            )


        elif market != "MONEYLINE":

            decision = (
                "MARKET_RESEARCH"
            )


        elif (
            books >= 3
            and providers >= 1
            and context_direction
            == "SUPPORT"
            and score >= 72
        ):

            decision = (
                "QUALIFIED_RESEARCH"
            )


        elif score >= 65:

            decision = "MARKET_LEAN"


        else:

            decision = "WATCH"


        rows.append({
            **row.to_dict(),

            "hours_to_start":
                hours,

            "approved_book_count":
                books,

            "provider_evidence_count":
                providers,

            "raw_book_support":
                support,

            "historical_context_value":
                historical_value,

            "context_direction":
                context_direction,

            "away_injury_blocks":
                away_inj[
                    "block"
                ],

            "away_injury_reviews":
                away_inj[
                    "review"
                ],

            "home_injury_blocks":
                home_inj[
                    "block"
                ],

            "home_injury_reviews":
                home_inj[
                    "review"
                ],

            "evidence_score":
                score,

            "decision":
                decision,

            "context_basis":
                "PRIOR_REGULAR_AND_PLAYOFF_FORM",

            "probability_claim":
                False,

            "puckline_model_validated":
                False,

            "totals_model_validated":
                False,
        })


    decisions = pd.DataFrame(
        rows
    )


    if decisions.empty:

        decisions.to_csv(
            GAME_DECISIONS,
            index=False,
        )

        decisions.to_csv(
            GAME_FINALISTS,
            index=False,
        )

        return decisions


    decisions = decisions.sort_values(
        [
            "evidence_score",
            "approved_book_count",
        ],
        ascending=[
            False,
            False,
        ],
    )


    finalists = (
        decisions[
            decisions[
                "decision"
            ].eq(
                "QUALIFIED_RESEARCH"
            )
        ]
        .sort_values(
            "evidence_score",
            ascending=False,
        )
        .drop_duplicates(
            [
                "game_key",
                "market_canonical",
            ],
            keep="first",
        )
        .head(
            12
        )
    )


    decisions.to_csv(
        GAME_DECISIONS,
        index=False,
    )

    finalists.to_csv(
        GAME_FINALISTS,
        index=False,
    )


    return decisions


# ============================================================
# PLAYER PROP SCORING
# ============================================================

def relative_edge(
    avg,
    line,
    side,
):

    avg = number(
        avg
    )

    line = number(
        line
    )


    if (
        avg is None
        or line is None
    ):

        return None


    denominator = max(
        abs(
            line
        ),
        0.5,
    )


    if str(
        side
    ).upper() == "OVER":

        return (
            avg
            - line
        ) / denominator


    if str(
        side
    ).upper() == "UNDER":

        return (
            line
            - avg
        ) / denominator


    return None


def prop_score(
    row,
    book_field,
):

    l3 = number(
        row.get(
            "l3_hit_rate"
        )
    )

    l5 = number(
        row.get(
            "l5_hit_rate"
        )
    )

    l10 = number(
        row.get(
            "l10_hit_rate"
        )
    )

    books = int(
        number(
            row.get(
                book_field
            )
        )
        or 0
    )

    meaningful = int(
        number(
            row.get(
                "meaningful_games"
            )
        )
        or 0
    )

    toi = number(
        row.get(
            "toi_l5_avg"
        )
    ) or 0


    score = 34.0


    if l10 is not None:

        if l10 >= 0.80:
            score += 24

        elif l10 >= 0.70:
            score += 18

        elif l10 >= 0.60:
            score += 12


    if l5 is not None:

        if l5 >= 0.80:
            score += 14

        elif l5 >= 0.70:
            score += 10

        elif l5 >= 0.60:
            score += 6


    if (
        l3 is not None
        and l3 >= 0.67
    ):

        score += 4


    if books >= 3:
        score += 10

    elif books >= 2:
        score += 7

    elif books >= 1:
        score += 3


    if meaningful >= 30:
        score += 6

    elif meaningful >= 15:
        score += 4

    elif meaningful >= 10:
        score += 2


    if str(
        row.get(
            "role",
            ""
        )
    ) == "SKATER":

        if toi >= 20:
            score += 5

        elif toi >= 15:
            score += 3


    edge = relative_edge(
        row.get(
            "stat_l5_avg"
        ),
        row.get(
            "line"
        ),
        row.get(
            "side"
        ),
    )


    if edge is not None:

        if edge >= 0.20:
            score += 8

        elif edge >= 0.10:
            score += 5

        elif edge > 0:
            score += 2


    return (
        clamp(
            score
        ),
        edge,
    )


def classify_player(
    row,
    score,
    hours,
    book_count,
    price_required,
):

    if str(
        row.get(
            "identity_status",
            ""
        )
    ) != "VERIFIED":

        return "IDENTITY_REVIEW"


    if str(
        row.get(
            "matchup_identity",
            ""
        )
    ) != "VERIFIED":

        return "MATCHUP_REVIEW"


    injury = str(
        row.get(
            "injury_gate",
            ""
        )
    ).upper()


    if injury == "BLOCK":
        return "INJURY_BLOCK"


    if injury == "REVIEW":
        return "INJURY_REVIEW"


    # Goalie props remain review-only until
    # a genuine confirmed-start source exists.
    if str(
        row.get(
            "role",
            ""
        )
    ).upper() == "GOALIE":

        return "GOALIE_START_REVIEW"


    if (
        hours is None
        or hours < -1
    ):

        return "CLOSED"


    # NHL line combinations can move fast.
    if hours > 30:

        return "EARLY_MARKET_WATCH"


    if (
        price_required
        and not sane_prop_price(
            row.get(
                "median_price_american"
            )
        )
    ):

        return "HIGH_JUICE_WATCH"


    l5 = number(
        row.get(
            "l5_hit_rate"
        )
    )

    l10 = number(
        row.get(
            "l10_hit_rate"
        )
    )


    qualified = (
        str(
            row.get(
                "sample_gate",
                ""
            )
        )
        == "QUALIFIED"
        and
        str(
            row.get(
                "context_direction",
                ""
            )
        )
        == "SUPPORT"
        and
        l5 is not None
        and l5 >= 0.60
        and
        l10 is not None
        and l10 >= 0.60
        and
        book_count >= 2
    )


    if (
        qualified
        and score >= 82
        and l10 >= 0.70
    ):

        return "STRONG_RESEARCH"


    if (
        qualified
        and score >= 70
    ):

        return "QUALIFIED_RESEARCH"


    return "WATCH"


def build_prop_decisions():

    df = read_csv(
        PROP_FUSION
    )


    if df.empty:

        pd.DataFrame().to_csv(
            PROP_DECISIONS,
            index=False,
        )

        pd.DataFrame().to_csv(
            PROP_FINALISTS,
            index=False,
        )

        return pd.DataFrame()


    rows = []


    for _, row in df.iterrows():

        hours = hours_until(
            row.get(
                "start_dt"
            )
        )

        books = int(
            number(
                row.get(
                    "book_count"
                )
            )
            or 0
        )


        score, edge = prop_score(
            row,
            "book_count",
        )


        decision = classify_player(
            row,
            score,
            hours,
            books,
            price_required=True,
        )


        rows.append({
            **row.to_dict(),

            "lane":
                "PROP",

            "hours_to_start":
                hours,

            "context_edge":
                edge,

            "evidence_score":
                score,

            "decision":
                decision,

            "probability_claim":
                False,
        })


    decisions = pd.DataFrame(
        rows
    )


    decisions = decisions.sort_values(
        [
            "evidence_score",
            "l10_hit_rate",
            "book_count",
        ],
        ascending=[
            False,
            False,
            False,
        ],
    )


    finalists = (
        decisions[
            decisions[
                "decision"
            ].isin(
                [
                    "STRONG_RESEARCH",
                    "QUALIFIED_RESEARCH",
                ]
            )
        ]
        .sort_values(
            "evidence_score",
            ascending=False,
        )
        .drop_duplicates(
            [
                "game_key",
                "nhl_player_id",
                "market_subtype",
            ],
            keep="first",
        )
        .head(
            25
        )
    )


    decisions.to_csv(
        PROP_DECISIONS,
        index=False,
    )

    finalists.to_csv(
        PROP_FINALISTS,
        index=False,
    )


    return decisions


# ============================================================
# PRIZEPICKS
# ============================================================

def sportsbook_match_index():

    props = read_csv(
        PROP_FUSION
    )


    index = {}


    if props.empty:
        return index


    for _, row in props.iterrows():

        line = number(
            row.get(
                "line"
            )
        )


        if line is None:
            continue


        key = (
            canonical_numeric_id(
                row.get(
                    "nhl_player_id",
                    ""
                )
            ),
            str(
                row.get(
                    "stat_type",
                    ""
                )
            ),
            str(
                row.get(
                    "side",
                    ""
                )
            ).upper(),
            round(
                line,
                3,
            ),
        )


        existing = index.get(
            key
        )


        candidate = {
            "book_count":
                int(
                    number(
                        row.get(
                            "book_count"
                        )
                    )
                    or 0
                ),

            "paired_book_count":
                int(
                    number(
                        row.get(
                            "paired_book_count"
                        )
                    )
                    or 0
                ),

            "price":
                number(
                    row.get(
                        "median_price_american"
                    )
                ),

            "fair_probability":
                number(
                    row.get(
                        "market_fair_probability"
                    )
                ),

            "best_price":
                number(
                    row.get(
                        "best_executable_price_american"
                    )
                ),

            "best_book":
                row.get(
                    "best_executable_sportsbook",
                    "",
                ),

            "pricing_status":
                row.get(
                    "market_pricing_status",
                    "",
                ),

            "data_quality_grade":
                row.get(
                    "market_data_quality_grade",
                    "D",
                ),

            "fair_probability_mad":
                number(
                    row.get(
                        "fair_probability_mad"
                    )
                ),

            "books":
                row.get(
                    "books",
                    "",
                ),
        }


        if (
            existing is None
            or candidate[
                "book_count"
            ]
            > existing[
                "book_count"
            ]
        ):

            index[
                key
            ] = candidate


    return index


def build_pp_decisions():

    df = read_csv(
        PP_FUSION
    )


    if df.empty:

        pd.DataFrame().to_csv(
            PP_DECISIONS,
            index=False,
        )

        pd.DataFrame().to_csv(
            PP_FINALISTS,
            index=False,
        )

        return pd.DataFrame()


    sportsbook = (
        sportsbook_match_index()
    )


    rows = []


    for _, row in df.iterrows():

        hours = hours_until(
            row.get(
                "start_dt"
            )
        )


        line = number(
            row.get(
                "line"
            )
        )


        key = (
            canonical_numeric_id(
                row.get(
                    "nhl_player_id",
                    ""
                )
            ),
            str(
                row.get(
                    "stat_type",
                    ""
                )
            ),
            str(
                row.get(
                    "side",
                    ""
                )
            ).upper(),
            round(
                line,
                3,
            )
            if line is not None
            else None,
        )


        market = sportsbook.get(
            key,
            {
                "book_count":
                    int(
                        number(
                            row.get(
                                "sportsbook_book_count"
                            )
                        )
                        or 0
                    ),

                "price":
                    None,

                "paired_book_count":
                    0,

                "fair_probability":
                    None,

                "best_price":
                    None,

                "best_book":
                    "",

                "pricing_status":
                    "",

                "data_quality_grade":
                    "D",

                "fair_probability_mad":
                    None,

                "books":
                    row.get(
                        "sportsbook_books",
                        "",
                    ),
            },
        )


        book_count = int(
            market[
                "book_count"
            ]
            or 0
        )


        enriched = row.to_dict()

        enriched[
            "sportsbook_book_count"
        ] = book_count

        enriched[
            "sportsbook_books"
        ] = market[
            "books"
        ]

        enriched[
            "sportsbook_median_price_american"
        ] = market[
            "price"
        ]

        enriched[
            "sportsbook_paired_book_count"
        ] = market[
            "paired_book_count"
        ]

        enriched[
            "sportsbook_fair_probability"
        ] = market[
            "fair_probability"
        ]

        enriched[
            "sportsbook_best_executable_price_american"
        ] = market[
            "best_price"
        ]

        enriched[
            "sportsbook_best_executable_sportsbook"
        ] = market[
            "best_book"
        ]

        enriched[
            "sportsbook_market_pricing_status"
        ] = market[
            "pricing_status"
        ]

        enriched[
            "sportsbook_market_data_quality_grade"
        ] = market[
            "data_quality_grade"
        ]

        enriched[
            "sportsbook_fair_probability_mad"
        ] = market[
            "fair_probability_mad"
        ]


        score, edge = prop_score(
            enriched,
            "sportsbook_book_count",
        )


        decision = classify_player(
            {
                **enriched,

                "median_price_american":
                    market[
                        "price"
                    ],
            },
            score,
            hours,
            book_count,
            price_required=True,
        )


        # PrizePicks additionally requires
        # a sportsbook line match.
        if (
            decision
            in {
                "STRONG_RESEARCH",
                "QUALIFIED_RESEARCH",
            }
            and book_count < 2
        ):

            decision = "WATCH"


        rows.append({
            **enriched,

            "lane":
                "PRIZEPICKS",

            "hours_to_start":
                hours,

            "context_edge":
                edge,

            "evidence_score":
                score,

            "decision":
                decision,

            "probability_claim":
                False,

            "platform_settlement_claim":
                False,
        })


    decisions = pd.DataFrame(
        rows
    )


    decisions = decisions.sort_values(
        [
            "evidence_score",
            "l10_hit_rate",
            "sportsbook_book_count",
        ],
        ascending=[
            False,
            False,
            False,
        ],
    )


    finalists = (
        decisions[
            decisions[
                "decision"
            ].isin(
                [
                    "STRONG_RESEARCH",
                    "QUALIFIED_RESEARCH",
                ]
            )
        ]
        .sort_values(
            "evidence_score",
            ascending=False,
        )
        .drop_duplicates(
            [
                "game_key",
                "nhl_player_id",
                "market_subtype",
            ],
            keep="first",
        )
        .head(
            25
        )
    )


    decisions.to_csv(
        PP_DECISIONS,
        index=False,
    )

    finalists.to_csv(
        PP_FINALISTS,
        index=False,
    )


    return decisions


# ============================================================
# FANTASY WATCHLIST
# ============================================================

def build_fantasy():

    context = read_csv(
        PLAYER_CONTEXT
    )

    roster = read_csv(
        ROSTERS
    )

    injuries = read_csv(
        INJURIES
    )


    if (
        context.empty
        or roster.empty
    ):

        pd.DataFrame().to_csv(
            FANTASY,
            index=False,
        )

        return pd.DataFrame()


    context[
        "_id"
    ] = (
        pd.to_numeric(
            context[
                "player_id"
            ],
            errors="coerce",
        )
        .astype(
            "Int64"
        )
        .astype(
            str
        )
    )


    roster[
        "_id"
    ] = (
        pd.to_numeric(
            roster[
                "player_id"
            ],
            errors="coerce",
        )
        .astype(
            "Int64"
        )
        .astype(
            str
        )
    )


    current = (
        roster[
            [
                "_id",
                "team",
                "player",
                "position",
            ]
        ]
        .drop_duplicates(
            "_id"
        )
    )


    out = context.merge(
        current,
        on="_id",
        how="inner",
        suffixes=(
            "_history",
            "_current",
        ),
    )


    injury_by_id = {}


    if not injuries.empty:

        for _, row in injuries.iterrows():

            raw = number(
                row.get(
                    "nhl_player_id"
                )
            )


            if raw is None:
                continue


            key = str(
                int(
                    raw
                )
            )


            injury_by_id[
                key
            ] = row.get(
                "injury_gate",
                "REVIEW",
            )


    out[
        "injury_gate"
    ] = out[
        "_id"
    ].map(
        injury_by_id
    ).fillna(
        "CLEAR"
    )


    toi = pd.to_numeric(
        out[
            "toi_minutes_l5_avg"
        ],
        errors="coerce",
    ).fillna(
        0
    )

    points = pd.to_numeric(
        out[
            "points_l5_avg"
        ],
        errors="coerce",
    ).fillna(
        0
    )

    shots = pd.to_numeric(
        out[
            "shots_on_goal_l5_avg"
        ],
        errors="coerce",
    ).fillna(
        0
    )

    hits = pd.to_numeric(
        out[
            "hits_l5_avg"
        ],
        errors="coerce",
    ).fillna(
        0
    )

    blocks = pd.to_numeric(
        out[
            "blocked_shots_l5_avg"
        ],
        errors="coerce",
    ).fillna(
        0
    )


    out[
        "recent_usage_index"
    ] = (
        toi
        + points
        * 5.0
        + shots
        * 1.2
        + hits
        * 0.5
        + blocks
        * 0.5
    )


    out[
        "fantasy_status"
    ] = np.where(
        out[
            "injury_gate"
        ].eq(
            "BLOCK"
        ),
        "INJURY_BLOCK",
        np.where(
            out[
                "injury_gate"
            ].eq(
                "REVIEW"
            ),
            "INJURY_REVIEW",
            "HISTORICAL_USAGE_WATCH",
        ),
    )


    out = (
        out
        .sort_values(
            "recent_usage_index",
            ascending=False,
        )
        .head(
            60
        )
    )


    out.to_csv(
        FANTASY,
        index=False,
    )


    return out


# ============================================================
# TWO-LEG RESEARCH COMBOS
# ============================================================

def build_parlays():

    games = read_csv(
        GAME_FINALISTS
    )

    props = read_csv(
        PROP_FINALISTS
    )


    legs = []


    if not games.empty:

        for _, row in games.iterrows():

            legs.append({
                "lane":
                    "GAME",

                "game_key":
                    row.get(
                        "game_key"
                    ),

                "player":
                    "",

                "market":
                    row.get(
                        "market_canonical"
                    ),

                "selection":
                    row.get(
                        "selection_canonical"
                    ),

                "line":
                    row.get(
                        "line_group"
                    ),

                "evidence_score":
                    row.get(
                        "evidence_score"
                    ),
            })


    if not props.empty:

        for _, row in props.iterrows():

            legs.append({
                "lane":
                    "PROP",

                "game_key":
                    row.get(
                        "game_key"
                    ),

                "player":
                    row.get(
                        "player"
                    ),

                "market":
                    row.get(
                        "market_subtype"
                    ),

                "selection":
                    row.get(
                        "side"
                    ),

                "line":
                    row.get(
                        "line"
                    ),

                "evidence_score":
                    row.get(
                        "evidence_score"
                    ),
            })


    columns = [
        "leg1_lane",
        "leg1_game",
        "leg1_player",
        "leg1_market",
        "leg1_selection",
        "leg1_line",
        "leg1_score",
        "leg2_lane",
        "leg2_game",
        "leg2_player",
        "leg2_market",
        "leg2_selection",
        "leg2_line",
        "leg2_score",
        "evidence_score",
        "status",
        "probability_claim",
        "payout_claim",
    ]


    if len(
        legs
    ) < 2:

        out = pd.DataFrame(
            columns=columns
        )

        out.to_csv(
            PARLAYS,
            index=False,
        )

        return out


    legs = sorted(
        legs,
        key=lambda x:
            float(
                x.get(
                    "evidence_score"
                )
                or 0
            ),
        reverse=True,
    )[
        :35
    ]


    combos = []


    for a, b in itertools.combinations(
        legs,
        2,
    ):

        if (
            a[
                "game_key"
            ]
            == b[
                "game_key"
            ]
        ):

            continue


        if (
            a[
                "player"
            ]
            and b[
                "player"
            ]
            and ascii_key(
                a[
                    "player"
                ]
            )
            == ascii_key(
                b[
                    "player"
                ]
            )
        ):

            continue


        score = (
            float(
                a[
                    "evidence_score"
                ]
                or 0
            )
            +
            float(
                b[
                    "evidence_score"
                ]
                or 0
            )
        ) / 2.0


        combos.append({
            "leg1_lane":
                a[
                    "lane"
                ],

            "leg1_game":
                a[
                    "game_key"
                ],

            "leg1_player":
                a[
                    "player"
                ],

            "leg1_market":
                a[
                    "market"
                ],

            "leg1_selection":
                a[
                    "selection"
                ],

            "leg1_line":
                a[
                    "line"
                ],

            "leg1_score":
                a[
                    "evidence_score"
                ],

            "leg2_lane":
                b[
                    "lane"
                ],

            "leg2_game":
                b[
                    "game_key"
                ],

            "leg2_player":
                b[
                    "player"
                ],

            "leg2_market":
                b[
                    "market"
                ],

            "leg2_selection":
                b[
                    "selection"
                ],

            "leg2_line":
                b[
                    "line"
                ],

            "leg2_score":
                b[
                    "evidence_score"
                ],

            "evidence_score":
                score,

            "status":
                "RESEARCH_COMBO",

            "probability_claim":
                False,

            "payout_claim":
                False,
        })


    out = pd.DataFrame(
        combos
    )


    if not out.empty:

        out = (
            out
            .sort_values(
                "evidence_score",
                ascending=False,
            )
            .head(
                30
            )
        )


    out.to_csv(
        PARLAYS,
        index=False,
    )


    return out


# ============================================================
# MAIN
# ============================================================

def main():

    DEC.mkdir(
        parents=True,
        exist_ok=True,
    )


    forms = build_team_form()

    injuries = current_injury_counts()


    games = build_game_decisions(
        forms,
        injuries,
    )

    props = build_prop_decisions()

    pp = build_pp_decisions()

    fantasy = build_fantasy()

    parlays = build_parlays()


    def rows(
        path,
    ):

        return int(
            len(
                read_csv(
                    path
                )
            )
        )


    summary = {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "game_decisions":
            rows(
                GAME_DECISIONS
            ),

        "game_finalists":
            rows(
                GAME_FINALISTS
            ),

        "prop_decisions":
            rows(
                PROP_DECISIONS
            ),

        "prop_finalists":
            rows(
                PROP_FINALISTS
            ),

        "prizepicks_decisions":
            rows(
                PP_DECISIONS
            ),

        "prizepicks_finalists":
            rows(
                PP_FINALISTS
            ),

        "fantasy_watchlist":
            rows(
                FANTASY
            ),

        "parlays":
            rows(
                PARLAYS
            ),

        "policies": {
            "market_is_probability":
                False,

            "hulk_score_is_probability":
                False,

            "game_finalist_horizon_hours":
                48,

            "player_finalist_horizon_hours":
                30,

            "moneyline_model_live":
                True,

            "puckline_model_validated":
                False,

            "totals_model_validated":
                False,

            "goalie_unconfirmed_can_finalize":
                False,

            "same_game_parlays_allowed":
                False,

            "prizepicks_platform_settlement_claim":
                False,

            "parlay_payout_claim":
                False,

            "automatic_model_adjustment":
                False,
        },
    }


    SUMMARY.write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
    )


    print(
        "GAME DECISIONS:",
        summary[
            "game_decisions"
        ]
    )

    print(
        "GAME FINALISTS:",
        summary[
            "game_finalists"
        ]
    )

    print(
        "PROP DECISIONS:",
        summary[
            "prop_decisions"
        ]
    )

    print(
        "PROP FINALISTS:",
        summary[
            "prop_finalists"
        ]
    )

    print(
        "PRIZEPICKS DECISIONS:",
        summary[
            "prizepicks_decisions"
        ]
    )

    print(
        "PRIZEPICKS FINALISTS:",
        summary[
            "prizepicks_finalists"
        ]
    )

    print(
        "FANTASY WATCHLIST:",
        summary[
            "fantasy_watchlist"
        ]
    )

    print(
        "PARLAYS:",
        summary[
            "parlays"
        ]
    )

    print()
    print(
        "RESULT: NHL_DECISION_BRAIN_READY"
    )


if __name__ == "__main__":
    main()
