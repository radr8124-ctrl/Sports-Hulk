from pathlib import Path
import json
import streamlit as st

ROOT = Path("/home/ubuntu/sports-hulk")

ENTRIES = (
    ROOT
    / "nfl_live"
    / "derived"
    / "SURVIVOR_ENTRIES.json"
)


def render_annie_week3_status():

    if not ENTRIES.exists():
        return

    try:
        data = json.loads(
            ENTRIES.read_text()
        )
    except Exception:
        return

    entries = data.get("entries", {})

    targets = [
        "ANNIE G 01",
        "ANNIE G 03",
    ]

    st.markdown(
        "### 🏈 Annie G — Week 3 Live"
    )

    for name in targets:

        e = entries.get(name)

        if not e:
            continue

        week3 = e.get("week_3", {})

        picks = week3.get("picks", [])

        entry_result = week3.get(
            "entry_result",
            "PENDING",
        )

        if entry_result == "WIN":
            icon = "✅"
        elif entry_result == "LOSS":
            icon = "❌"
        else:
            icon = "⏳"

        with st.container(border=True):

            st.markdown(
                f"**{icon} {name}**"
            )

            cols = st.columns(
                max(len(picks), 1)
            )

            for i, leg in enumerate(picks):

                result = leg.get(
                    "result",
                    "PENDING",
                )

                status = leg.get(
                    "game_status",
                    "Waiting",
                )

                if result == "WIN":
                    marker = "✅"
                elif result == "LOSS":
                    marker = "❌"
                else:
                    marker = "⏳"

                with cols[i]:
                    st.markdown(
                        f"**{marker} "
                        f"{leg.get('team','—')}**"
                    )

                    st.caption(status)

            st.markdown(
                f"Entry result: "
                f"**{entry_result}**"
            )
