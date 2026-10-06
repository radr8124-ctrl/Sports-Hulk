from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import streamlit as st


ROOT = Path("/home/ubuntu/sports-hulk")
DEC = ROOT / "nfl_live/decision"


def load(name):

    p = DEC / name

    if (
        not p.exists()
        or p.stat().st_size <= 1
    ):
        return pd.DataFrame()

    try:
        return pd.read_csv(
            p,
            low_memory=False,
        )
    except Exception:
        return pd.DataFrame()


def age(name):

    p = DEC / name

    if not p.exists():
        return "unavailable"

    now = datetime.now(
        timezone.utc
    ).timestamp()

    mins = int(
        (
            now
            - p.stat().st_mtime
        )
        / 60
    )

    if mins < 1:
        return "just now"

    if mins < 60:
        return f"{mins} min ago"

    return (
        f"{mins // 60}h "
        f"{mins % 60}m ago"
    )


def header(title, subtitle):

    st.markdown(
        f"## {title}"
    )

    st.caption(
        subtitle
    )


def render_nfl_best_bets():

    header(
        "🏈 NFL Best Bets",
        (
            "Multi-source market research · "
            "HULK evidence scores are not "
            "probabilities."
        ),
    )

    d = load(
        "NFL_GAME_FINALISTS.csv"
    )

    if d.empty:
        st.info(
            "No NFL game finalists "
            "are currently available."
        )
        return

    st.caption(
        "Updated "
        + age(
            "NFL_GAME_FINALISTS.csv"
        )
    )

    ml = d[
        d["market"]
        .astype(str)
        .str.upper()
        .eq("MONEYLINE")
    ].copy()

    if not ml.empty:

        st.subheader(
            "Moneyline Research"
        )

        cols = [
            "game_key",
            "selection",
            "line",
            "hulk_market_score",
            "decision",
            "market_data_quality",
            "provider_agreement",
            "oddspapi_status",
        ]

        st.dataframe(
            ml[
                [
                    c
                    for c in cols
                    if c in ml.columns
                ]
            ],
            width="stretch",
            hide_index=True,
        )

    research = d[
        ~d["market"]
        .astype(str)
        .str.upper()
        .eq("MONEYLINE")
    ].copy()

    if not research.empty:

        st.subheader(
            "Spread / Total Research"
        )

        st.warning(
            "Spread and total rows are "
            "market-backed research only. "
            "Sports HULK does not yet claim "
            "a validated NFL ATS/totals model."
        )

        cols = [
            "game_key",
            "market",
            "selection",
            "line",
            "hulk_market_score",
            "decision",
            "provider_agreement",
        ]

        st.dataframe(
            research[
                [
                    c
                    for c in cols
                    if c
                    in research.columns
                ]
            ],
            width="stretch",
            hide_index=True,
        )


def render_nfl_player_props():

    header(
        "🎯 NFL Player Props",
        (
            "Sportsbook consensus + DFS "
            "+ completed-game usage + "
            "advanced player context."
        ),
    )

    d = load(
        "NFL_PROP_FINALISTS.csv"
    )

    if d.empty:
        st.info(
            "No player props meet "
            "HULK qualification right now."
        )
        return

    st.caption(
        "Updated "
        + age(
            "NFL_PROP_FINALISTS.csv"
        )
    )

    player_col = next(
        (
            c
            for c in [
                "player_dfs",
                "player",
                "player_sportsbook",
            ]
            if c in d.columns
        ),
        None,
    )

    cols = [
        player_col,
        "market",
        "side",
        "dfs_line",
        "sportsbook_line",
        "book_count",
        "book_probability",
        "meaningful_completed_games",
        "recent_metric",
        "hulk_prop_score",
        "decision",
    ]

    cols = [
        c
        for c in cols
        if c
        and c in d.columns
    ]

    st.dataframe(
        d[cols],
        width="stretch",
        hide_index=True,
    )

    st.caption(
        "HULK Score is an evidence score, "
        "not a probability. Props require "
        "verified player identity and at "
        "least two meaningful completed games."
    )


def render_nfl_prizepicks():

    header(
        "🟣 NFL PrizePicks",
        (
            "Live PrizePicks lines compared "
            "with sportsbook and independent "
            "player evidence."
        ),
    )

    d = load(
        "NFL_PRIZEPICKS_FINALISTS.csv"
    )

    if d.empty:
        st.info(
            "No PrizePicks entries currently "
            "meet HULK qualification."
        )
        return

    st.caption(
        "Updated "
        + age(
            "NFL_PRIZEPICKS_FINALISTS.csv"
        )
    )

    cols = [
        "player",
        "market_subtype",
        "side",
        "line",
        "book_count",
        "book_probability",
        "meaningful_completed_games",
        "hulk_prop_score",
        "decision",
    ]

    st.dataframe(
        d[
            [
                c
                for c in cols
                if c in d.columns
            ]
        ],
        width="stretch",
        hide_index=True,
    )


def render_nfl_parlays():

    header(
        "🧩 NFL Parlays",
        (
            "Qualified-leg research only · "
            "different games required at launch."
        ),
    )

    d = load(
        "NFL_PARLAYS_TODAY.csv"
    )

    if d.empty:
        st.info(
            "No qualified NFL parlays "
            "are available right now."
        )
        return

    st.caption(
        "Updated "
        + age(
            "NFL_PARLAYS_TODAY.csv"
        )
    )

    st.warning(
        "Parlay Score is not a probability. "
        "Sportsbook payout must be verified "
        "at the book before placing anything."
    )

    types = [
        "PLAYER_PROP_2_LEG",
        "PRIZEPICKS_2_PICK",
        "GAME_ML_2_LEG",
        "MIXED_ML_PROP_2_LEG",
    ]

    labels = {
        "PLAYER_PROP_2_LEG":
            "Player Prop Parlays",

        "PRIZEPICKS_2_PICK":
            "PrizePicks 2-Pick Cards",

        "GAME_ML_2_LEG":
            "Game Moneyline Parlays",

        "MIXED_ML_PROP_2_LEG":
            "Mixed Game + Prop",
    }

    for ptype in types:

        x = d[
            d["parlay_type"]
            .eq(ptype)
        ].copy()

        if x.empty:
            continue

        st.subheader(
            labels[ptype]
        )

        cols = [
            "parlay_score",
            "leg1_label",
            "leg2_label",
            "correlation_status",
            "payout_status",
        ]

        st.dataframe(
            x[
                [
                    c
                    for c in cols
                    if c in x.columns
                ]
            ],
            width="stretch",
            hide_index=True,
        )
