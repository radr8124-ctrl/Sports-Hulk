from pathlib import Path
import json
import pandas as pd
import streamlit as st


ROOT = Path("/home/ubuntu/sports-hulk")

STRATEGY = (
    ROOT
    / "nfl_live"
    / "derived"
    / "NFL_SURVIVOR_HULK_STRATEGY.csv"
)

ENTRIES = (
    ROOT
    / "nfl_live"
    / "derived"
    / "SURVIVOR_ENTRIES.json"
)


def _entry_data():
    if not ENTRIES.exists():
        return {"active": None, "entries": {}}

    try:
        return json.loads(
            ENTRIES.read_text()
        )
    except Exception:
        return {"active": None, "entries": {}}


def render_survivor_strategy():

    st.markdown("### 🧠 HULK Survivor Strategy")

    if not STRATEGY.exists():
        st.info(
            "Future-value strategy has not been built yet."
        )
        return

    df = pd.read_csv(STRATEGY)

    if df.empty:
        st.info("No Survivor strategy data available.")
        return

    data = _entry_data()

    entries = data.get("entries") or {}
    active = data.get("active")

    used = []

    if active in entries:
        used = entries[active].get(
            "used_teams", []
        ) or []

        st.caption(
            f"Active entry: {active} · "
            f"{len(used)} teams already used"
        )
    else:
        st.caption(
            "No active Survivor entry selected. "
            "Showing the generic strategy board."
        )

    df["used_by_entry"] = (
        df["survivor_team"].isin(used)
    )

    available = df[
        ~df["used_by_entry"]
    ].copy()

    if available.empty:
        st.warning(
            "Every candidate on this week's board "
            "is already marked used for this entry."
        )
        return

    st.markdown("#### Best Available Strategy Options")

    top = available.head(6)

    for _, r in top.iterrows():

        action = str(
            r.get("strategy_action", "WATCH")
        ).replace("_", " ")

        with st.container(border=True):

            c1, c2, c3, c4 = st.columns(
                [2, 1, 1, 1]
            )

            with c1:
                st.markdown(
                    f"**{r.get('survivor_team', '—')}**"
                )
                st.caption(
                    f"vs {r.get('opponent', '—')}"
                )

            with c2:
                st.metric(
                    "Market",
                    f"{r.get('market_prob_pct', 0):.1f}%"
                )

            with c3:
                st.metric(
                    "HULK",
                    f"{r.get('hulk_context_score', 0):.1f}"
                )

            with c4:
                st.metric(
                    "Future Value",
                    f"{r.get('future_value_index', 0):.0f}"
                )

            st.markdown(f"**{action}**")

            future = str(
                r.get("next_four_week_schedule", "")
            )

            if future:
                st.caption(
                    "Next 4 weeks: " + future
                )

    st.markdown("#### Entry-Aware Full Board")

    cols = [
        "survivor_team",
        "opponent",
        "market_prob_pct",
        "hulk_context_score",
        "future_value_index",
        "future_value_label",
        "strategy_index",
        "strategy_action",
        "used_by_entry",
        "risk_signals",
    ]

    cols = [
        c for c in cols
        if c in available.columns
    ]

    table = available[cols].copy()

    table = table.rename(
        columns={
            "survivor_team": "Team",
            "opponent": "Opponent",
            "market_prob_pct": "Market %",
            "hulk_context_score": "HULK",
            "future_value_index": "Future Value",
            "future_value_label": "Future Label",
            "strategy_index": "Strategy Index",
            "strategy_action": "Strategy",
            "used_by_entry": "Used",
            "risk_signals": "Risks",
        }
    )

    st.dataframe(
        table,
        width="stretch",
        hide_index=True,
    )

    st.caption(
        "Future Value estimates the opportunity cost "
        "of spending a team now. Strategy Index is "
        "not a calibrated win probability."
    )
