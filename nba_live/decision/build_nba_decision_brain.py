#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

import itertools
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
MARKETS = NBA / "markets" / "current"
DERIVED = NBA / "derived"
HISTORY = NBA / "history"


GAME_FUSION = (
    MARKETS
    / "NBA_GAME_MARKET_FUSION.csv"
)

PROP_FUSION = (
    MARKETS
    / "NBA_PROP_FUSION.csv"
)

PP_FUSION = (
    MARKETS
    / "NBA_PRIZEPICKS_FUSION.csv"
)

GAME_HISTORY = (
    HISTORY
    / "NBA_GAME_HISTORY.csv"
)

PLAYER_CONTEXT = (
    DERIVED
    / "NBA_PLAYER_CONTEXT.csv"
)

ROSTERS = (
    DERIVED
    / "NBA_CURRENT_ROSTERS.csv"
)

INJURIES = (
    DERIVED
    / "NBA_INJURIES_CURRENT.csv"
)


GAME_DECISIONS = (
    DEC
    / "NBA_GAME_DECISIONS.csv"
)

GAME_FINALISTS = (
    DEC
    / "NBA_GAME_FINALISTS.csv"
)

PROP_DECISIONS = (
    DEC
    / "NBA_PROP_DECISIONS.csv"
)

PROP_FINALISTS = (
    DEC
    / "NBA_PROP_FINALISTS.csv"
)

PP_DECISIONS = (
    DEC
    / "NBA_PRIZEPICKS_DECISIONS.csv"
)

PP_FINALISTS = (
    DEC
    / "NBA_PRIZEPICKS_FINALISTS.csv"
)

FANTASY = (
    DEC
    / "NBA_FANTASY_WATCHLIST.csv"
)

PARLAYS = (
    DEC
    / "NBA_PARLAYS_TODAY.csv"
)

SUMMARY = (
    DEC
    / "NBA_DECISION_SUMMARY.json"
)


NOW = pd.Timestamp.now(
    tz="UTC"
)


TEAM_MAP = {
    "ATL": "ATL",
    "BOS": "BOS",
    "BKN": "BKN",
    "CHA": "CHA",
    "CHI": "CHI",
    "CLE": "CLE",
    "DAL": "DAL",
    "DEN": "DEN",
    "DET": "DET",
    "GS": "GSW",
    "GSW": "GSW",
    "HOU": "HOU",
    "IND": "IND",
    "LAC": "LAC",
    "LAL": "LAL",
    "MEM": "MEM",
    "MIA": "MIA",
    "MIL": "MIL",
    "MIN": "MIN",
    "NO": "NOP",
    "NOP": "NOP",
    "NY": "NYK",
    "NYK": "NYK",
    "OKC": "OKC",
    "ORL": "ORL",
    "PHI": "PHI",
    "PHX": "PHX",
    "POR": "POR",
    "SAC": "SAC",
    "SA": "SAS",
    "SAS": "SAS",
    "TOR": "TOR",
    "UTAH": "UTA",
    "UTA": "UTA",
    "WSH": "WAS",
    "WAS": "WAS",
}


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
    """
    Raw implied support from American market price.
    Includes vig and is NOT a Sports HULK probability.
    """

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


# ============================================================
# PRIOR-SEASON TEAM CONTEXT
# ============================================================

def build_team_form():

    games = read_csv(
        GAME_HISTORY
    )

    if games.empty:
        return {}


    if "season_type" in games.columns:

        stype = pd.to_numeric(
            games[
                "season_type"
            ],
            errors="coerce",
        )

        # Regular season + postseason.
        games = games[
            stype.isin(
                [
                    2,
                    3,
                ]
            )
        ].copy()


    games[
        "start_dt"
    ] = pd.to_datetime(
        games[
            "start"
        ],
        utc=True,
        errors="coerce",
    )


    rows = []


    for _, g in games.iterrows():

        away = team(
            g.get(
                "away_team"
            )
        )

        home = team(
            g.get(
                "home_team"
            )
        )

        away_score = number(
            g.get(
                "away_score"
            )
        )

        home_score = number(
            g.get(
                "home_score"
            )
        )


        if (
            not away
            or not home
            or away_score is None
            or home_score is None
        ):
            continue


        rows.append({
            "team":
                away,

            "opponent":
                home,

            "start_dt":
                g[
                    "start_dt"
                ],

            "points_for":
                away_score,

            "points_against":
                home_score,

            "margin":
                away_score
                - home_score,

            "game_total":
                away_score
                + home_score,

            "win":
                float(
                    away_score
                    > home_score
                ),
        })


        rows.append({
            "team":
                home,

            "opponent":
                away,

            "start_dt":
                g[
                    "start_dt"
                ],

            "points_for":
                home_score,

            "points_against":
                away_score,

            "margin":
                home_score
                - away_score,

            "game_total":
                home_score
                + away_score,

            "win":
                float(
                    home_score
                    > away_score
                ),
        })


    frame = pd.DataFrame(
        rows
    )


    if frame.empty:
        return {}


    frame = frame.sort_values(
        "start_dt"
    )


    result = {}


    for club, group in frame.groupby(
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


        result[
            club
        ] = {
            "historical_games":
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

            "margin_l5":
                float(
                    l5[
                        "margin"
                    ].mean()
                )
                if len(
                    l5
                )
                else None,

            "margin_l10":
                float(
                    l10[
                        "margin"
                    ].mean()
                )
                if len(
                    l10
                )
                else None,

            "total_l10":
                float(
                    l10[
                        "game_total"
                    ].mean()
                )
                if len(
                    l10
                )
                else None,

            "points_l10":
                float(
                    l10[
                        "points_for"
                    ].mean()
                )
                if len(
                    l10
                )
                else None,
        }


    return result


# ============================================================
# GAME DECISIONS
# ============================================================

def build_game_decisions(
    forms,
):

    df = read_csv(
        GAME_FUSION
    )


    if df.empty:
        return pd.DataFrame()


    rows = []


    for _, row in df.iterrows():

        start = row.get(
            "start_dt"
        )

        hours = hours_until(
            start
        )


        if (
            hours is None
            or hours < -1
            or hours > 21 * 24
        ):
            continue


        away = team(
            row.get(
                "away_team_canonical"
            )
        )

        home = team(
            row.get(
                "home_team_canonical"
            )
        )

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


        if market not in {
            "MONEYLINE",
            "SPREAD",
            "TOTAL",
        }:
            continue


        line = number(
            row.get(
                "line_group"
            )
        )

        book_count = approved_book_count(
            row.get(
                "sportsbooks"
            )
        )

        raw_support = raw_book_support(
            row.get(
                "median_price_american"
            )
        )


        score = 48.0
        context_direction = "MIXED"
        context_value = None


        if book_count >= 5:
            score += 16

        elif book_count >= 3:
            score += 12

        elif book_count >= 2:
            score += 8

        elif book_count >= 1:
            score += 3


        if raw_support is not None:

            if raw_support >= 0.58:
                score += 7

            elif raw_support >= 0.54:
                score += 4

            elif raw_support >= 0.51:
                score += 2


        away_form = forms.get(
            away,
            {}
        )

        home_form = forms.get(
            home,
            {}
        )


        if market in {
            "MONEYLINE",
            "SPREAD",
        }:

            selected = team(
                selection
            )

            opponent = (
                home
                if selected == away
                else away
            )


            selected_form = forms.get(
                selected,
                {}
            )

            opponent_form = forms.get(
                opponent,
                {}
            )


            margin = selected_form.get(
                "margin_l10"
            )

            opp_margin = opponent_form.get(
                "margin_l10"
            )

            win_rate = selected_form.get(
                "win_rate_l10"
            )


            context_value = margin


            if (
                margin is not None
                and margin > 2
            ):

                score += 8

            elif (
                margin is not None
                and margin < -2
            ):

                score -= 6


            if (
                opp_margin is not None
                and opp_margin < -2
            ):

                score += 4


            if (
                win_rate is not None
                and win_rate >= 0.60
            ):

                score += 6


            if (
                margin is not None
                and margin > 0
                and win_rate is not None
                and win_rate >= 0.50
            ):

                context_direction = "SUPPORT"

            elif (
                margin is not None
                and margin < 0
                and win_rate is not None
                and win_rate < 0.50
            ):

                context_direction = "OPPOSE"


        elif market == "TOTAL":

            a = away_form.get(
                "total_l10"
            )

            h = home_form.get(
                "total_l10"
            )


            if (
                a is not None
                and h is not None
                and line is not None
            ):

                expected_context = (
                    a + h
                ) / 2.0

                context_value = expected_context

                edge = (
                    expected_context
                    - line
                )


                if selection == "OVER":

                    if edge >= 5:
                        score += 10
                        context_direction = "SUPPORT"

                    elif edge <= -5:
                        score -= 8
                        context_direction = "OPPOSE"


                elif selection == "UNDER":

                    if edge <= -5:
                        score += 10
                        context_direction = "SUPPORT"

                    elif edge >= 5:
                        score -= 8
                        context_direction = "OPPOSE"


        score = clamp(
            score
        )


        if hours > 72:

            decision = (
                "EARLY_MARKET_WATCH"
            )

        elif book_count < 2:

            decision = "WATCH"

        elif (
            score >= 75
            and context_direction
            == "SUPPORT"
        ):

            decision = (
                "QUALIFIED_RESEARCH"
            )

        elif score >= 68:

            decision = "MARKET_LEAN"

        else:

            decision = "WATCH"


        rows.append({
            **row.to_dict(),

            "hours_to_start":
                hours,

            "approved_book_count":
                book_count,

            "raw_book_support":
                raw_support,

            "historical_context_value":
                context_value,

            "context_direction":
                context_direction,

            "evidence_score":
                score,

            "decision":
                decision,

            "context_basis":
                "PRIOR_SEASON_2025_26",

            "probability_claim":
                False,
        })


    decisions = pd.DataFrame(
        rows
    )


    if decisions.empty:
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


    # One side per game/market.
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
# PROP / PICK'EM DECISIONS
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
        1.0,
    )


    if str(
        side
    ).upper() == "OVER":

        return (
            avg - line
        ) / denominator


    if str(
        side
    ).upper() == "UNDER":

        return (
            line - avg
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

    books = number(
        row.get(
            book_field
        )
    ) or 0

    meaningful = number(
        row.get(
            "meaningful_games"
        )
    ) or 0

    minutes = number(
        row.get(
            "minutes_l5_avg"
        )
    ) or 0


    score = 38.0


    if l10 is not None:

        if l10 >= 0.80:
            score += 22

        elif l10 >= 0.70:
            score += 17

        elif l10 >= 0.60:
            score += 12


    if l5 is not None:

        if l5 >= 0.80:
            score += 12

        elif l5 >= 0.70:
            score += 9

        elif l5 >= 0.60:
            score += 6


    if (
        l3 is not None
        and l3 >= 0.67
    ):
        score += 5


    if books >= 3:
        score += 10

    elif books >= 2:
        score += 7

    elif books >= 1:
        score += 3


    if meaningful >= 20:
        score += 5

    elif meaningful >= 10:
        score += 3


    if minutes >= 30:
        score += 5

    elif minutes >= 24:
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

        if edge >= 0.10:
            score += 8

        elif edge >= 0.05:
            score += 5

        elif edge > 0:
            score += 2


    return (
        clamp(
            score
        ),
        edge,
    )


def classify_prop(
    row,
    score,
    hours,
    book_count,
):

    if str(
        row.get(
            "matchup_identity",
            ""
        )
    ) != "VERIFIED":

        return "IDENTITY_REVIEW"


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


    if (
        hours is None
        or hours < -1
    ):
        return "CLOSED"


    # We collect early lines, but do not finalize
    # a player recommendation days/weeks too early.
    if hours > 96:
        return "EARLY_MARKET_WATCH"


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
        book_count >= 1
    )


    if (
        qualified
        and score >= 82
        and l10 >= 0.70
        and book_count >= 2
    ):

        return "STRONG_RESEARCH"


    if (
        qualified
        and score >= 68
    ):

        return "QUALIFIED_RESEARCH"


    return "WATCH"


def build_prop_lane(
    source,
    decisions_path,
    finalists_path,
    book_field,
    lane,
):

    df = read_csv(
        source
    )


    if df.empty:

        pd.DataFrame().to_csv(
            decisions_path,
            index=False,
        )

        pd.DataFrame().to_csv(
            finalists_path,
            index=False,
        )

        return pd.DataFrame()


    rows = []


    for _, row in df.iterrows():

        base = row.to_dict()

        hours = hours_until(
            row.get(
                "start_dt"
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


        score, edge = prop_score(
            row,
            book_field,
        )


        decision = classify_prop(
            row,
            score,
            hours,
            books,
        )


        game_key = (
            pd.to_datetime(
                row.get(
                    "start_dt"
                ),
                utc=True,
                errors="coerce",
            ).strftime(
                "%Y-%m-%d"
            )
            if pd.notna(
                pd.to_datetime(
                    row.get(
                        "start_dt"
                    ),
                    utc=True,
                    errors="coerce",
                )
            )
            else ""
        )


        game_key = (
            game_key
            + "|"
            + str(
                row.get(
                    "away_team",
                    ""
                )
            )
            + "|"
            + str(
                row.get(
                    "home_team",
                    ""
                )
            )
        )


        rows.append({
            **base,

            "lane":
                lane,

            "game_key":
                game_key,

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
        ],
        ascending=[
            False,
            False,
        ],
    )


    finalist_statuses = {
        "STRONG_RESEARCH",
        "QUALIFIED_RESEARCH",
    }


    finalists = decisions[
        decisions[
            "decision"
        ].isin(
            finalist_statuses
        )
    ].copy()


    # One direction/line per player market/event.
    finalists = (
        finalists
        .sort_values(
            "evidence_score",
            ascending=False,
        )
        .drop_duplicates(
            [
                "event_id",
                "player_key",
                "market_subtype",
            ],
            keep="first",
        )
        .head(
            30
        )
    )


    decisions.to_csv(
        decisions_path,
        index=False,
    )

    finalists.to_csv(
        finalists_path,
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
        "player_key"
    ] = context[
        "player"
    ].map(
        pkey
    )

    roster[
        "player_key"
    ] = roster[
        "player"
    ].map(
        pkey
    )


    r = roster[
        [
            "player_key",
            "team",
            "position",
            "status",
        ]
    ].drop_duplicates(
        "player_key"
    )


    out = context.merge(
        r,
        on="player_key",
        how="inner",
        suffixes=(
            "_history",
            "_current",
        ),
    )


    injury_gate = {}


    if not injuries.empty:

        for _, row in injuries.iterrows():

            key = pkey(
                row.get(
                    "player"
                )
            )

            status = str(
                row.get(
                    "status",
                    ""
                )
            ).upper()

            fantasy_status = str(
                row.get(
                    "fantasy_status",
                    ""
                )
            ).upper()


            if (
                "OUT" in status
                or fantasy_status
                in {
                    "OUT",
                    "OFS",
                }
            ):

                injury_gate[
                    key
                ] = "BLOCK"

            elif (
                "DAY-TO-DAY"
                in status
                or fantasy_status
                in {
                    "GTD",
                    "DTD",
                }
            ):

                injury_gate.setdefault(
                    key,
                    "REVIEW",
                )


    out[
        "injury_gate"
    ] = out[
        "player_key"
    ].map(
        injury_gate
    ).fillna(
        "CLEAR"
    )


    mins = pd.to_numeric(
        out.get(
            "minutes_l5_avg"
        ),
        errors="coerce",
    )

    pra = pd.to_numeric(
        out.get(
            "pra_l5_avg"
        ),
        errors="coerce",
    )


    out[
        "recent_usage_index"
    ] = (
        mins.fillna(
            0
        )
        + (
            pra.fillna(
                0
            )
            * 0.50
        )
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
# SAFE 2-LEG PARLAY RESEARCH
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

                "decision":
                    row.get(
                        "decision"
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

                "decision":
                    row.get(
                        "decision"
                    ),
            })


    if len(
        legs
    ) < 2:

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

        pd.DataFrame(
            columns=columns
        ).to_csv(
            PARLAYS,
            index=False,
        )

        return pd.DataFrame(
            columns=columns
        )


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
        :30
    ]


    combos = []


    for a, b in itertools.combinations(
        legs,
        2,
    ):

        # No same-game correlation.
        if (
            a.get(
                "game_key"
            )
            == b.get(
                "game_key"
            )
        ):
            continue


        # No same-player duplicate exposure.
        if (
            a.get(
                "player"
            )
            and
            b.get(
                "player"
            )
            and pkey(
                a.get(
                    "player"
                )
            )
            == pkey(
                b.get(
                    "player"
                )
            )
        ):
            continue


        score = (
            float(
                a.get(
                    "evidence_score"
                )
                or 0
            )
            +
            float(
                b.get(
                    "evidence_score"
                )
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


    game_decisions = (
        build_game_decisions(
            forms
        )
    )


    if not GAME_FINALISTS.exists():

        game_decisions.head(
            0
        ).to_csv(
            GAME_FINALISTS,
            index=False,
        )


    prop_decisions = (
        build_prop_lane(
            PROP_FUSION,
            PROP_DECISIONS,
            PROP_FINALISTS,
            "book_count",
            "PROP",
        )
    )


    pp_decisions = (
        build_prop_lane(
            PP_FUSION,
            PP_DECISIONS,
            PP_FINALISTS,
            "sportsbook_book_count",
            "PRIZEPICKS",
        )
    )


    fantasy = build_fantasy()

    parlays = build_parlays()


    def rows(
        path,
    ):

        df = read_csv(
            path
        )

        return int(
            len(
                df
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

            "prizepicks_settlement_claim":
                False,

            "parlay_payout_claim":
                False,

            "player_finalist_horizon_hours":
                96,

            "game_finalist_horizon_hours":
                72,

            "same_game_parlays_allowed":
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
        "RESULT: NBA_DECISION_BRAIN_READY"
    )


if __name__ == "__main__":
    main()
