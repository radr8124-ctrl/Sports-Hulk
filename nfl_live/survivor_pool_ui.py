from pathlib import Path

import pandas as pd
import streamlit as st

from nfl_live.survivor_pool_import import import_pdf


ROOT = Path("/home/ubuntu/sports-hulk")

DERIVED = (
    ROOT
    / "nfl_live"
    / "survivor_pool"
    / "derived"
)


def render_survivor_pool_import():

    st.markdown("### 📄 Weekly Pool Import")

    st.caption(
        "Upload the official Sunday Survivor PDF. "
        "HULK stores a permanent snapshot and "
        "rebuilds the pool ledger and ownership data."
    )

    uploaded = st.file_uploader(
        "Upload Sunday pool PDF",
        type=["pdf"],
        key="survivor_pool_pdf",
    )

    if uploaded is not None:

        if st.button(
            "Import Pool PDF",
            type="primary",
            key="import_survivor_pdf",
        ):

            try:
                result = import_pdf(
                    uploaded.getvalue(),
                    uploaded.name,
                )

                st.success(
                    "Pool import complete."
                )

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "Entries parsed",
                    result["entries"],
                )

                c2.metric(
                    "Pick records",
                    result["ledger_rows"],
                )

                c3.metric(
                    "Annie G entries",
                    result["annie_entries"],
                )

                st.caption(
                    result["snapshot_path"]
                )

            except Exception as exc:
                st.error(
                    f"Pool import failed: {exc}"
                )

    current = (
        DERIVED
        / "SURVIVOR_POOL_CURRENT.csv"
    )

    ownership = (
        DERIVED
        / "SURVIVOR_POOL_OWNERSHIP.csv"
    )

    annie = (
        DERIVED
        / "ANNIE_G_POOL_ENTRIES.csv"
    )

    if current.exists():

        df = pd.read_csv(current)

        st.markdown("#### Current Pool")

        c1, c2 = st.columns(2)

        c1.metric(
            "Imported Entries",
            len(df),
        )

        c2.metric(
            "Rows marked eliminated",
            int(
                (
                    df["status"]
                    == "ELIMINATED"
                ).sum()
            ),
        )

    if annie.exists():

        adf = pd.read_csv(annie)

        if not adf.empty:

            st.markdown(
                "#### Annie G Entries"
            )

            cols = [
                c for c in [
                    "entry_name",
                    "status",
                    "used_teams",
                    "last_pick",
                ]
                if c in adf.columns
            ]

            st.dataframe(
                adf[cols],
                width="stretch",
                hide_index=True,
            )

    if ownership.exists():

        own = pd.read_csv(ownership)

        if not own.empty:

            latest_week = int(
                own["week_position"].max()
            )

            latest = own[
                own["week_position"]
                == latest_week
            ].sort_values(
                "pick_count",
                ascending=False,
            )

            st.markdown(
                f"#### Week {latest_week} "
                "Pool Pick Distribution"
            )

            st.dataframe(
                latest[
                    [
                        "team",
                        "pick_count",
                        "pick_share_pct",
                    ]
                ],
                width="stretch",
                hide_index=True,
            )
