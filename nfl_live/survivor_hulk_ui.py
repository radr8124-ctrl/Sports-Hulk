from pathlib import Path
import pandas as pd
import streamlit as st


ROOT = Path("/home/ubuntu/sports-hulk")
DECISION = ROOT / "nfl_live" / "derived" / "NFL_SURVIVOR_HULK_DECISION.csv"


def _pct(v):
    try:
        return f"{float(v):.1f}%"
    except Exception:
        return "—"


def _num(v, digits=1):
    try:
        return f"{float(v):.{digits}f}"
    except Exception:
        return "—"


def render_hulk_survivor_decision():
    st.markdown("## 🏈 Survivor HULK")

    st.caption(
        "Live market data + HULK context. "
        "Market probability and HULK context are shown separately."
    )

    if not DECISION.exists():
        st.warning("HULK Survivor decision board is not available yet.")
        return

    df = pd.read_csv(DECISION)

    if df.empty:
        st.warning("HULK Survivor decision board is empty.")
        return

    # --------------------------------------------------
    # TOP DECISION CARDS
    # --------------------------------------------------

    top = df.head(5).copy()

    for _, r in top.iterrows():

        tier = str(r.get("hulk_decision_tier", "WATCH"))
        disagreement = str(r.get("hulk_disagreement", ""))

        risk = str(r.get("risk_signals") or "").replace("|", " · ")
        positive = str(r.get("positive_signals") or "").replace("|", " · ")

        market = _pct(r.get("market_prob_pct"))
        context = _num(r.get("hulk_context_score"))

        team = r.get("survivor_team", "")
        opp = r.get("opponent", "")
        spread = r.get("survivor_spread", "")

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2.2, 1, 1, 1])

            with c1:
                st.markdown(f"### {team}")
                st.caption(f"vs {opp}")

            with c2:
                st.metric("Market", market)

            with c3:
                st.metric("HULK Context", context)

            with c4:
                st.metric("Spread", spread)

            st.markdown(
                f"**{tier.replace('_', ' ')}**  ·  "
                f"{disagreement.replace('_', ' ')}"
            )

            if positive:
                st.caption(f"✅ {positive}")

            if risk:
                st.caption(f"⚠️ {risk}")

    # --------------------------------------------------
    # FULL BOARD
    # --------------------------------------------------

    st.markdown("### Full Survivor Board")

    cols = [
        "survivor_team",
        "opponent",
        "market_prob_pct",
        "hulk_context_score",
        "context_delta",
        "hulk_disagreement",
        "hulk_decision_tier",
        "survivor_spread",
        "positive_signals",
        "risk_signals",
    ]

    cols = [c for c in cols if c in df.columns]

    board = df[cols].copy()

    board = board.rename(
        columns={
            "survivor_team": "Team",
            "opponent": "Opponent",
            "market_prob_pct": "Market %",
            "hulk_context_score": "HULK Context",
            "context_delta": "HULK vs Market",
            "hulk_disagreement": "HULK View",
            "hulk_decision_tier": "Tier",
            "survivor_spread": "Spread",
            "positive_signals": "Positives",
            "risk_signals": "Risks",
        }
    )

    st.dataframe(
        board,
        width="stretch",
        hide_index=True,
    )

    st.caption(
        "HULK Context is a contextual intelligence score, "
        "not a calibrated win probability."
    )
