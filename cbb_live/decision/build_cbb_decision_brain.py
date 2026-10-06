#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import itertools
import json
import math

import pandas as pd


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

CBB = ROOT / "cbb_live"
DEC = CBB / "decision"

DERIVED = CBB / "derived"
HISTORY = CBB / "history"
MARKETS = CBB / "markets" / "current"


CURRENT_GAMES = (
    DERIVED
    / "CBB_GAMES_CURRENT.csv"
)

GAME_HISTORY = (
    HISTORY
    / "CBB_GAME_HISTORY.csv"
)

TEAM_HISTORY = (
    HISTORY
    / "CBB_TEAM_GAME_HISTORY.csv"
)

ELO_CURRENT = (
    DERIVED
    / "CBB_ELO_CURRENT.csv"
)

SRS_CURRENT = (
    DERIVED
    / "CBB_SRS_CURRENT.csv"
)

RANKINGS = (
    DERIVED
    / "CBB_RANKINGS_CURRENT.csv"
)

FUSION = (
    MARKETS
    / "CBB_GAME_MARKET_FUSION.csv"
)


PRESEASON_BASELINE = (
    DEC
    / "CBB_PRESEASON_BASELINE.csv"
)

TEAM_CONTEXT = (
    DEC
    / "CBB_TEAM_CONTEXT.csv"
)

TEAM_RESEARCH = (
    DEC
    / "CBB_TEAM_RESEARCH.csv"
)

GAME_DECISIONS = (
    DEC
    / "CBB_GAME_DECISIONS.csv"
)

GAME_FINALISTS = (
    DEC
    / "CBB_GAME_FINALISTS.csv"
)

PARLAYS = (
    DEC
    / "CBB_PARLAYS_TODAY.csv"
)

SUMMARY = (
    DEC
    / "CBB_DECISION_SUMMARY.json"
)


NOW = pd.Timestamp.now(
    tz="UTC"
)

ET = ZoneInfo(
    "America/New_York"
)


MIN_CURRENT_GAMES = 5

FINALIST_HORIZON_HOURS = 72


def read_csv(
    path,
):

    path = Path(
        path
    )


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
        dt
        - NOW
    ).total_seconds() / 3600.0


def market_support(
    price,
):

    # Raw sportsbook implied support.
    # Contains vig.
    # NOT a HULK probability.
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


# ============================================================
# IMMUTABLE PRESEASON BASELINE
# ============================================================

def build_preseason_baseline():

    if PRESEASON_BASELINE.exists():

        baseline = read_csv(
            PRESEASON_BASELINE
        )


        if not baseline.empty:

            return baseline


    elo = read_csv(
        ELO_CURRENT
    )

    srs = read_csv(
        SRS_CURRENT
    )

    rankings = read_csv(
        RANKINGS
    )


    if elo.empty:

        baseline = pd.DataFrame()

        baseline.to_csv(
            PRESEASON_BASELINE,
            index=False,
        )

        return baseline


    elo = elo.copy()

    elo[
        "team_id_key"
    ] = elo[
        "team_id"
    ].map(
        id_key
    )


    if not srs.empty:

        srs = srs.copy()

        srs[
            "team_id_key"
        ] = srs[
            "team_id"
        ].map(
            id_key
        )


        baseline = elo.merge(
            srs[
                [
                    "team_id_key",
                    "srs",
                    "strength_of_schedule",
                    "average_margin",
                ]
            ],
            on="team_id_key",
            how="left",
        )

    else:

        baseline = elo.copy()

        baseline[
            "srs"
        ] = None

        baseline[
            "strength_of_schedule"
        ] = None

        baseline[
            "average_margin"
        ] = None


    baseline[
        "prior_ap_rank"
    ] = None


    if not rankings.empty:

        ap = rankings[
            rankings[
                "poll"
            ]
            .astype(
                str
            )
            .str.contains(
                "AP",
                case=False,
                na=False,
            )
        ].copy()


        prior_rank = {}


        for _, row in ap.iterrows():

            if truth(
                row.get(
                    "current_season_match"
                )
            ):

                continue


            prior_rank[
                id_key(
                    row.get(
                        "team_id"
                    )
                )
            ] = number(
                row.get(
                    "rank"
                )
            )


        baseline[
            "prior_ap_rank"
        ] = baseline[
            "team_id_key"
        ].map(
            prior_rank
        )


    baseline[
        "baseline_created_at"
    ] = datetime.now(
        timezone.utc
    ).isoformat()

    baseline[
        "baseline_source"
    ] = (
        "2025_26_FINAL_SEASON"
    )

    baseline[
        "baseline_is_current_season"
    ] = False


    baseline.to_csv(
        PRESEASON_BASELINE,
        index=False,
    )


    return baseline


# ============================================================
# CURRENT-SEASON TEAM CONTEXT
# ============================================================

def detect_current_season():

    current = read_csv(
        CURRENT_GAMES
    )


    if (
        not current.empty
        and "season"
        in current.columns
    ):

        values = pd.to_numeric(
            current[
                "season"
            ],
            errors="coerce",
        ).dropna()


        if len(
            values
        ):

            return int(
                values.max()
            )


    now = datetime.now(
        ET
    )


    return (
        now.year
        + 1
        if now.month >= 7
        else now.year
    )


def build_team_context(
    baseline,
    current_season,
):

    team_history = read_csv(
        TEAM_HISTORY
    )


    base_map = {}


    if not baseline.empty:

        for _, row in baseline.iterrows():

            base_map[
                id_key(
                    row.get(
                        "team_id_key",
                        row.get(
                            "team_id"
                        ),
                    )
                )
            ] = row.to_dict()


    current_rows = pd.DataFrame()


    if (
        not team_history.empty
        and "season"
        in team_history.columns
    ):

        season = pd.to_numeric(
            team_history[
                "season"
            ],
            errors="coerce",
        )


        current_rows = team_history[
            season.eq(
                current_season
            )
        ].copy()


    current_groups = {}


    if not current_rows.empty:

        current_rows[
            "start_dt"
        ] = pd.to_datetime(
            current_rows[
                "start"
            ],
            utc=True,
            errors="coerce",
        )


        current_rows = current_rows.sort_values(
            "start_dt"
        )


        current_groups = {
            id_key(
                team_id
            ):
                group.copy()

            for team_id, group
            in current_rows.groupby(
                "team_id"
            )
        }


    ids = set(
        base_map
    )


    ids.update(
        current_groups
    )


    rows = []


    for team_id in ids:

        base = base_map.get(
            team_id,
            {},
        )

        group = current_groups.get(
            team_id,
        )


        if (
            group is None
            or group.empty
        ):

            current_games = 0
            current_wins = 0
            current_losses = 0
            win_rate = None
            avg_margin = None
            l3_margin = None
            l5_margin = None
            avg_score = None
            avg_allowed = None
            team = base.get(
                "team",
                "",
            )
            team_name = base.get(
                "team_name",
                "",
            )

        else:

            current_games = len(
                group
            )

            wins = pd.to_numeric(
                group[
                    "win"
                ],
                errors="coerce",
            )


            margins = pd.to_numeric(
                group[
                    "margin"
                ],
                errors="coerce",
            )


            scores = pd.to_numeric(
                group[
                    "score"
                ],
                errors="coerce",
            )


            allowed = pd.to_numeric(
                group[
                    "opponent_score"
                ],
                errors="coerce",
            )


            current_wins = int(
                wins.eq(
                    1
                ).sum()
            )

            current_losses = int(
                wins.eq(
                    0
                ).sum()
            )

            win_rate = wins.mean()

            avg_margin = margins.mean()

            l3_margin = (
                margins
                .tail(
                    3
                )
                .mean()
            )

            l5_margin = (
                margins
                .tail(
                    5
                )
                .mean()
            )

            avg_score = scores.mean()

            avg_allowed = allowed.mean()

            team = (
                group.iloc[
                    -1
                ].get(
                    "team"
                )
                or base.get(
                    "team",
                    "",
                )
            )

            team_name = (
                group.iloc[
                    -1
                ].get(
                    "team_name"
                )
                or base.get(
                    "team_name",
                    "",
                )
            )


        if current_games >= MIN_CURRENT_GAMES:

            stage = (
                "CURRENT_SEASON_READY"
            )

        elif current_games > 0:

            stage = (
                "EARLY_SEASON"
            )

        else:

            stage = (
                "PRESEASON_BASELINE"
            )


        rows.append({
            "team_id":
                team_id,

            "team":
                team,

            "team_name":
                team_name,

            "prior_elo":
                number(
                    base.get(
                        "elo"
                    )
                ),

            "prior_srs":
                number(
                    base.get(
                        "srs"
                    )
                ),

            "prior_ap_rank":
                number(
                    base.get(
                        "prior_ap_rank"
                    )
                ),

            "current_season":
                current_season,

            "current_games":
                current_games,

            "current_wins":
                current_wins,

            "current_losses":
                current_losses,

            "current_win_rate":
                win_rate,

            "current_avg_margin":
                avg_margin,

            "current_l3_margin":
                l3_margin,

            "current_l5_margin":
                l5_margin,

            "current_points_for":
                avg_score,

            "current_points_against":
                avg_allowed,

            "context_stage":
                stage,

            "finalist_eligible":
                (
                    current_games
                    >= MIN_CURRENT_GAMES
                ),
        })


    out = pd.DataFrame(
        rows
    )


    if not out.empty:

        out = out.sort_values(
            [
                "current_games",
                "prior_elo",
            ],
            ascending=[
                False,
                False,
            ],
        )


    out.to_csv(
        TEAM_CONTEXT,
        index=False,
    )


    return out


# ============================================================
# UPCOMING TEAM RESEARCH
# Not picks.
# ============================================================

def build_team_research(
    context,
):

    games = read_csv(
        CURRENT_GAMES
    )


    columns = [
        "event_id",
        "start",
        "game_date",
        "away_team_id",
        "away_team",
        "away_team_name",
        "home_team_id",
        "home_team",
        "home_team_name",
        "neutral_site",
        "away_prior_elo",
        "home_prior_elo",
        "prior_elo_gap_home",
        "away_prior_srs",
        "home_prior_srs",
        "prior_srs_gap_home",
        "away_current_games",
        "home_current_games",
        "away_current_margin",
        "home_current_margin",
        "context_stage",
        "research_status",
    ]


    if games.empty:

        out = pd.DataFrame(
            columns=columns
        )

        out.to_csv(
            TEAM_RESEARCH,
            index=False,
        )

        return out


    context_map = {
        id_key(
            row[
                "team_id"
            ]
        ):
            row.to_dict()

        for _, row
        in context.iterrows()
    }


    rows = []


    for _, game in games.iterrows():

        if truth(
            game.get(
                "completed"
            )
        ):

            continue


        away_id = id_key(
            game.get(
                "away_team_id"
            )
        )

        home_id = id_key(
            game.get(
                "home_team_id"
            )
        )


        away = context_map.get(
            away_id,
            {},
        )

        home = context_map.get(
            home_id,
            {},
        )


        if (
            not away
            or not home
        ):

            continue


        away_games = int(
            number(
                away.get(
                    "current_games"
                )
            )
            or 0
        )

        home_games = int(
            number(
                home.get(
                    "current_games"
                )
            )
            or 0
        )


        if (
            away_games >= MIN_CURRENT_GAMES
            and home_games >= MIN_CURRENT_GAMES
        ):

            stage = (
                "CURRENT_SEASON_READY"
            )

            status = (
                "MARKET_REQUIRED"
            )


        elif (
            away_games > 0
            or home_games > 0
        ):

            stage = (
                "EARLY_SEASON"
            )

            status = (
                "EARLY_SEASON_RESEARCH"
            )


        else:

            stage = (
                "PRESEASON_BASELINE"
            )

            status = (
                "PRESEASON_RESEARCH_ONLY"
            )


        away_elo = number(
            away.get(
                "prior_elo"
            )
        )

        home_elo = number(
            home.get(
                "prior_elo"
            )
        )

        away_srs = number(
            away.get(
                "prior_srs"
            )
        )

        home_srs = number(
            home.get(
                "prior_srs"
            )
        )


        rows.append({
            "event_id":
                game.get(
                    "event_id"
                ),

            "start":
                game.get(
                    "start"
                ),

            "game_date":
                game.get(
                    "game_date"
                ),

            "away_team_id":
                away_id,

            "away_team":
                game.get(
                    "away_team"
                ),

            "away_team_name":
                game.get(
                    "away_team_name"
                ),

            "home_team_id":
                home_id,

            "home_team":
                game.get(
                    "home_team"
                ),

            "home_team_name":
                game.get(
                    "home_team_name"
                ),

            "neutral_site":
                game.get(
                    "neutral_site"
                ),

            "away_prior_elo":
                away_elo,

            "home_prior_elo":
                home_elo,

            "prior_elo_gap_home":
                (
                    home_elo
                    - away_elo
                    if (
                        home_elo is not None
                        and away_elo is not None
                    )
                    else None
                ),

            "away_prior_srs":
                away_srs,

            "home_prior_srs":
                home_srs,

            "prior_srs_gap_home":
                (
                    home_srs
                    - away_srs
                    if (
                        home_srs is not None
                        and away_srs is not None
                    )
                    else None
                ),

            "away_current_games":
                away_games,

            "home_current_games":
                home_games,

            "away_current_margin":
                away.get(
                    "current_avg_margin"
                ),

            "home_current_margin":
                home.get(
                    "current_avg_margin"
                ),

            "context_stage":
                stage,

            "research_status":
                status,
        })


    out = pd.DataFrame(
        rows
    )


    if not out.empty:

        out[
            "_start"
        ] = pd.to_datetime(
            out[
                "start"
            ],
            utc=True,
            errors="coerce",
        )


        out = out.sort_values(
            "_start"
        ).drop(
            columns=[
                "_start"
            ]
        )


    out.to_csv(
        TEAM_RESEARCH,
        index=False,
    )


    return out


# ============================================================
# MARKET DECISION BRAIN
# ============================================================

def build_game_decisions(
    context,
):

    fusion = read_csv(
        FUSION
    )


    output_columns = [
        "game_key",
        "schedule_event_id",
        "start_dt",
        "game_date",
        "away_team_id",
        "away_team",
        "away_team_name",
        "home_team_id",
        "home_team",
        "home_team_name",
        "market_canonical",
        "selection_canonical",
        "selection_team_id",
        "line",
        "sportsbook_count",
        "provider_count",
        "sportsbooks",
        "providers",
        "median_price_american",
        "hours_to_start",
        "raw_market_support",
        "selected_current_games",
        "opponent_current_games",
        "selected_prior_elo",
        "opponent_prior_elo",
        "prior_elo_edge",
        "selected_prior_srs",
        "opponent_prior_srs",
        "prior_srs_edge",
        "selected_current_margin",
        "opponent_current_margin",
        "current_margin_edge",
        "context_stage",
        "context_direction",
        "evidence_score",
        "decision",
        "probability_claim",
        "spread_model_validated",
        "totals_model_validated",
    ]


    if fusion.empty:

        empty = pd.DataFrame(
            columns=output_columns
        )

        empty.to_csv(
            GAME_DECISIONS,
            index=False,
        )

        empty.to_csv(
            GAME_FINALISTS,
            index=False,
        )

        return empty


    context_map = {
        id_key(
            row[
                "team_id"
            ]
        ):
            row.to_dict()

        for _, row
        in context.iterrows()
    }


    rows = []


    for _, row in fusion.iterrows():

        market = str(
            row.get(
                "market_canonical",
                ""
            )
        ).upper()


        away_id = id_key(
            row.get(
                "away_team_id"
            )
        )

        home_id = id_key(
            row.get(
                "home_team_id"
            )
        )

        selected_id = id_key(
            row.get(
                "selection_team_id"
            )
        )


        away_context = context_map.get(
            away_id,
            {},
        )

        home_context = context_map.get(
            home_id,
            {},
        )


        selected = {}

        opponent = {}


        if selected_id == away_id:

            selected = away_context
            opponent = home_context


        elif selected_id == home_id:

            selected = home_context
            opponent = away_context


        selected_games = int(
            number(
                selected.get(
                    "current_games"
                )
            )
            or 0
        )

        opponent_games = int(
            number(
                opponent.get(
                    "current_games"
                )
            )
            or 0
        )


        away_games = int(
            number(
                away_context.get(
                    "current_games"
                )
            )
            or 0
        )

        home_games = int(
            number(
                home_context.get(
                    "current_games"
                )
            )
            or 0
        )


        both_ready = (
            away_games
            >= MIN_CURRENT_GAMES
            and home_games
            >= MIN_CURRENT_GAMES
        )


        if both_ready:

            stage = (
                "CURRENT_SEASON_READY"
            )


        elif (
            away_games > 0
            or home_games > 0
        ):

            stage = (
                "EARLY_SEASON"
            )


        else:

            stage = (
                "PRESEASON_BASELINE"
            )


        books = int(
            number(
                row.get(
                    "sportsbook_count"
                )
            )
            or 0
        )

        providers = int(
            number(
                row.get(
                    "provider_count"
                )
            )
            or 0
        )


        support = market_support(
            row.get(
                "median_price_american"
            )
        )


        hours = hours_until(
            row.get(
                "start_dt"
            )
        )


        score = 35.0


        if books >= 8:

            score += 17

        elif books >= 5:

            score += 13

        elif books >= 3:

            score += 9

        elif books >= 2:

            score += 5


        if providers >= 2:

            score += 6


        if (
            support is not None
            and support >= 0.60
        ):

            score += 5


        context_direction = (
            "MIXED"
        )


        selected_elo = number(
            selected.get(
                "prior_elo"
            )
        )

        opponent_elo = number(
            opponent.get(
                "prior_elo"
            )
        )

        selected_srs = number(
            selected.get(
                "prior_srs"
            )
        )

        opponent_srs = number(
            opponent.get(
                "prior_srs"
            )
        )

        selected_margin = number(
            selected.get(
                "current_avg_margin"
            )
        )

        opponent_margin = number(
            opponent.get(
                "current_avg_margin"
            )
        )


        elo_edge = (
            selected_elo
            - opponent_elo
            if (
                selected_elo is not None
                and opponent_elo is not None
            )
            else None
        )


        srs_edge = (
            selected_srs
            - opponent_srs
            if (
                selected_srs is not None
                and opponent_srs is not None
            )
            else None
        )


        current_margin_edge = (
            selected_margin
            - opponent_margin
            if (
                selected_margin is not None
                and opponent_margin is not None
            )
            else None
        )


        # Prior-season context is deliberately
        # low weight because CBB rosters turn over.
        if elo_edge is not None:

            if elo_edge >= 100:

                score += 4

            elif elo_edge <= -100:

                score -= 3


        if srs_edge is not None:

            if srs_edge >= 8:

                score += 4

            elif srs_edge <= -8:

                score -= 3


        # Current-season context becomes the
        # dominant independent evidence.
        if both_ready:

            score += 10


            if (
                current_margin_edge is not None
                and current_margin_edge >= 5
            ):

                score += 12


            elif (
                current_margin_edge is not None
                and current_margin_edge >= 2
            ):

                score += 7


            elif (
                current_margin_edge is not None
                and current_margin_edge <= -5
            ):

                score -= 10


            if (
                current_margin_edge is not None
                and current_margin_edge > 0
                and (
                    elo_edge is None
                    or elo_edge > -75
                )
            ):

                context_direction = (
                    "SUPPORT"
                )


            elif (
                current_margin_edge is not None
                and current_margin_edge < 0
            ):

                context_direction = (
                    "OPPOSE"
                )


        score = clamp(
            score
        )


        if (
            hours is None
            or hours < -1
        ):

            decision = "CLOSED"


        elif hours > FINALIST_HORIZON_HOURS:

            decision = (
                "EARLY_MARKET_WATCH"
            )


        elif not both_ready:

            decision = (
                "EARLY_SEASON_RESEARCH"
            )


        elif market != "MONEYLINE":

            # Spread and totals will not become
            # finalists until their own historical
            # grading is validated.
            decision = (
                "MARKET_RESEARCH"
            )


        elif (
            books >= 3
            and providers >= 1
            and context_direction
            == "SUPPORT"
            and score >= 75
        ):

            decision = (
                "QUALIFIED_RESEARCH"
            )


        elif score >= 65:

            decision = (
                "MARKET_LEAN"
            )


        else:

            decision = "WATCH"


        rows.append({
            **row.to_dict(),

            "hours_to_start":
                hours,

            "raw_market_support":
                support,

            "selected_current_games":
                selected_games,

            "opponent_current_games":
                opponent_games,

            "selected_prior_elo":
                selected_elo,

            "opponent_prior_elo":
                opponent_elo,

            "prior_elo_edge":
                elo_edge,

            "selected_prior_srs":
                selected_srs,

            "opponent_prior_srs":
                opponent_srs,

            "prior_srs_edge":
                srs_edge,

            "selected_current_margin":
                selected_margin,

            "opponent_current_margin":
                opponent_margin,

            "current_margin_edge":
                current_margin_edge,

            "context_stage":
                stage,

            "context_direction":
                context_direction,

            "evidence_score":
                score,

            "decision":
                decision,

            "probability_claim":
                False,

            "spread_model_validated":
                False,

            "totals_model_validated":
                False,
        })


    decisions = pd.DataFrame(
        rows
    )


    decisions = decisions.sort_values(
        [
            "evidence_score",
            "sportsbook_count",
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
            15
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
# PARLAYS — ONLY REAL FINALISTS
# ============================================================

def build_parlays():

    finalists = read_csv(
        GAME_FINALISTS
    )


    columns = [
        "leg1_game",
        "leg1_selection",
        "leg1_market",
        "leg1_line",
        "leg1_score",
        "leg2_game",
        "leg2_selection",
        "leg2_market",
        "leg2_line",
        "leg2_score",
        "evidence_score",
        "status",
        "probability_claim",
        "payout_claim",
    ]


    if len(
        finalists
    ) < 2:

        out = pd.DataFrame(
            columns=columns
        )

        out.to_csv(
            PARLAYS,
            index=False,
        )

        return out


    legs = []


    for _, row in finalists.iterrows():

        legs.append({
            "game":
                row.get(
                    "game_key"
                ),

            "selection":
                row.get(
                    "selection_canonical"
                ),

            "market":
                row.get(
                    "market_canonical"
                ),

            "line":
                row.get(
                    "line"
                ),

            "score":
                row.get(
                    "evidence_score"
                ),
        })


    rows = []


    for a, b in itertools.combinations(
        legs,
        2,
    ):

        if (
            a[
                "game"
            ]
            == b[
                "game"
            ]
        ):

            continue


        score = (
            float(
                a[
                    "score"
                ]
            )
            +
            float(
                b[
                    "score"
                ]
            )
        ) / 2.0


        rows.append({
            "leg1_game":
                a[
                    "game"
                ],

            "leg1_selection":
                a[
                    "selection"
                ],

            "leg1_market":
                a[
                    "market"
                ],

            "leg1_line":
                a[
                    "line"
                ],

            "leg1_score":
                a[
                    "score"
                ],

            "leg2_game":
                b[
                    "game"
                ],

            "leg2_selection":
                b[
                    "selection"
                ],

            "leg2_market":
                b[
                    "market"
                ],

            "leg2_line":
                b[
                    "line"
                ],

            "leg2_score":
                b[
                    "score"
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
        rows
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


    baseline = (
        build_preseason_baseline()
    )


    current_season = (
        detect_current_season()
    )


    context = build_team_context(
        baseline,
        current_season,
    )


    research = build_team_research(
        context
    )


    decisions = build_game_decisions(
        context
    )


    parlays = build_parlays()


    finalists = read_csv(
        GAME_FINALISTS
    )


    current_ready = (
        int(
            context[
                "finalist_eligible"
            ]
            .map(
                truth
            )
            .sum()
        )
        if (
            not context.empty
            and "finalist_eligible"
            in context.columns
        )
        else 0
    )


    summary = {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "current_season":
            current_season,

        "preseason_baseline_teams":
            int(
                len(
                    baseline
                )
            ),

        "team_context_rows":
            int(
                len(
                    context
                )
            ),

        "current_season_ready_teams":
            current_ready,

        "upcoming_team_research":
            int(
                len(
                    research
                )
            ),

        "game_decisions":
            int(
                len(
                    decisions
                )
            ),

        "game_finalists":
            int(
                len(
                    finalists
                )
            ),

        "parlays":
            int(
                len(
                    parlays
                )
            ),

        "policies": {
            "minimum_current_season_games":
                MIN_CURRENT_GAMES,

            "prior_season_baseline_can_finalize":
                False,

            "moneyline_finalist_lane":
                True,

            "spread_model_validated":
                False,

            "totals_model_validated":
                False,

            "market_is_probability":
                False,

            "hulk_score_is_probability":
                False,

            "college_player_props":
                False,

            "college_prizepicks":
                False,

            "college_fantasy":
                False,

            "same_game_parlays":
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
        "CURRENT SEASON:",
        current_season
    )

    print(
        "PRESEASON BASELINE TEAMS:",
        len(
            baseline
        )
    )

    print(
        "TEAM CONTEXT ROWS:",
        len(
            context
        )
    )

    print(
        "CURRENT-SEASON READY TEAMS:",
        current_ready
    )

    print(
        "UPCOMING TEAM RESEARCH:",
        len(
            research
        )
    )

    print(
        "GAME DECISIONS:",
        len(
            decisions
        )
    )

    print(
        "GAME FINALISTS:",
        len(
            finalists
        )
    )

    print(
        "PARLAYS:",
        len(
            parlays
        )
    )

    print()
    print(
        "RESULT: CBB_DECISION_BRAIN_READY"
    )


if __name__ == "__main__":
    main()
