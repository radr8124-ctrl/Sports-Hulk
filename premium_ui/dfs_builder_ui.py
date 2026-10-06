import pandas as pd
import streamlit as st

from premium_ui.dfs_optimizer import (
    optimize_nfl,
    lineup_frame,
    prepare_pool,
)


def _fmt_money(value):
    try:
        return "$" + f"{int(float(value)):,}"
    except Exception:
        return "—"


def _fmt_proj(value):
    try:
        return f"{float(value):.1f}"
    except Exception:
        return "—"


def _label(row):
    player = str(row.get("player") or "Player")
    pos = str(row.get("position") or "")
    team = str(row.get("team") or "")
    opp = str(row.get("opponent") or "")
    salary = _fmt_money(row.get("salary"))
    proj = _fmt_proj(row.get("projected_fantasy_points"))
    matchup = f"{team} vs {opp}" if opp else team
    return f"{player} · {pos} · {matchup} · {salary} · {proj} proj"


def render_nfl_lineup_builder(source, platform):
    platform = str(platform).upper()

    pool = prepare_pool(
        source,
        platform,
    ).copy()

    if pool.empty:
        st.info(
            "No projected player pool is available for this slate."
        )
        return

    st.markdown(
        "### Build My Lineup"
    )
    st.caption(
        (
            "Search players by typing their name. Lock anyone you want "
            "in the lineup, exclude anyone you do not want, then let "
            "HULK optimize the remaining slots from its current projections."
        )
    )

    strategy = st.pills(
        "Optimization style",
        [
            "Balanced",
            "Max Projection",
            "Value",
            "GPP",
        ],
        default="Balanced",
        required=True,
        key=(
            "dfs_builder_strategy_"
            + platform
        ),
    )

    pool = pool.sort_values(
        [
            "position",
            "projected_fantasy_points",
        ],
        ascending=[
            True,
            False,
        ],
    )

    option_labels = {}
    ordered_labels = []

    for _, row in pool.iterrows():
        label = _label(
            row
        )
        key = str(
            row.get(
                "player_key"
            )
        )
        if label in option_labels:
            label = (
                label
                + " · "
                + key
            )
        option_labels[
            label
        ] = key
        ordered_labels.append(
            label
        )

    control_cols = st.columns(
        2
    )

    with control_cols[0]:
        locked_labels = st.multiselect(
            "Lock players",
            ordered_labels,
            default=[],
            placeholder=(
                "Type a player name…"
            ),
            key=(
                "dfs_builder_locks_"
                + platform
            ),
            help=(
                "Locked players are forced into every optimized lineup."
            ),
        )

    with control_cols[1]:
        excluded_labels = st.multiselect(
            "Exclude players",
            ordered_labels,
            default=[],
            placeholder=(
                "Type a player name…"
            ),
            key=(
                "dfs_builder_excludes_"
                + platform
            ),
            help=(
                "Excluded players are removed from the optimizer pool."
            ),
        )

    locked_keys = [
        option_labels[
            label
        ]
        for label in locked_labels
        if label in option_labels
    ]

    excluded_keys = [
        option_labels[
            label
        ]
        for label in excluded_labels
        if label in option_labels
    ]

    overlap = set(
        locked_keys
    ) & set(
        excluded_keys
    )

    if overlap:
        st.error(
            "A player cannot be both locked and excluded."
        )

    search = st.text_input(
        "Browse player pool",
        placeholder=(
            "Search name, team or position…"
        ),
        key=(
            "dfs_builder_search_"
            + platform
        ),
    )

    browse = pool.copy()

    if search.strip():
        q = search.strip().lower()
        mask = (
            browse["player"].astype(str).str.lower().str.contains(
                q,
                regex=False,
            )
            | browse["team"].astype(str).str.lower().str.contains(
                q,
                regex=False,
            )
            | browse["position"].astype(str).str.lower().str.contains(
                q,
                regex=False,
            )
        )
        browse = browse[
            mask
        ].copy()

    browse_cols = [
        col
        for col in [
            "player",
            "position",
            "team",
            "opponent",
            "salary",
            "projected_fantasy_points",
            "audit_value_per_1000",
            "contest_archetype",
            "context_signal",
            "availability_status",
        ]
        if col
        in browse.columns
    ]

    with st.expander(
        "Player pool",
        expanded=bool(
            search.strip()
        ),
    ):
        st.dataframe(
            browse[
                browse_cols
            ].sort_values(
                "projected_fantasy_points",
                ascending=False,
            ).head(
                60
            ),
            width="stretch",
            hide_index=True,
        )

    action_cols = st.columns(
        [
            1,
            1,
            3,
        ]
    )

    optimize_clicked = False

    with action_cols[0]:
        optimize_clicked = st.button(
            "Optimize lineup",
            type="primary",
            width="stretch",
            disabled=bool(
                overlap
            ),
            key=(
                "dfs_builder_optimize_"
                + platform
            ),
        )

    with action_cols[1]:
        if st.button(
            "Clear",
            width="stretch",
            key=(
                "dfs_builder_clear_"
                + platform
            ),
        ):
            for suffix in [
                "locks_",
                "excludes_",
                "search_",
                "result_",
            ]:
                st.session_state.pop(
                    "dfs_builder_"
                    + suffix
                    + platform,
                    None,
                )
            st.rerun()

    result_key = (
        "dfs_builder_result_"
        + platform
    )

    if optimize_clicked:
        with st.spinner(
            "Optimizing with HULK projections…"
        ):
            try:
                results = optimize_nfl(
                    source,
                    platform,
                    locked_keys=locked_keys,
                    excluded_keys=excluded_keys,
                    strategy=strategy,
                    alternatives=3,
                )
            except Exception as exc:
                results = []
                st.error(
                    str(
                        exc
                    )
                )

        if not results:
            st.warning(
                (
                    "No legal lineup fits those selections. "
                    "Try unlocking a player or removing an exclusion."
                )
            )
            st.session_state.pop(
                result_key,
                None,
            )
        else:
            st.session_state[
                result_key
            ] = {
                "results":
                    results,
                "strategy":
                    strategy,
                "locked_keys":
                    locked_keys,
            }

    saved = st.session_state.get(
        result_key
    )

    if not saved:
        st.info(
            (
                "Choose any players you want to force in or remove, "
                "then tap **Optimize lineup**."
            )
        )
        return

    results = saved.get(
        "results",
        []
    )
    saved_strategy = saved.get(
        "strategy",
        strategy,
    )
    saved_locks = saved.get(
        "locked_keys",
        locked_keys,
    )

    if not results:
        return

    alternatives = [
        "Lineup "
        + str(
            i + 1
        )
        for i in range(
            len(
                results
            )
        )
    ]

    selected_lineup = st.pills(
        "Optimized lineups",
        alternatives,
        default=alternatives[
            0
        ],
        required=True,
        key=(
            "dfs_builder_result_select_"
            + platform
        ),
    )

    idx = alternatives.index(
        selected_lineup
    )
    result = results[
        idx
    ]

    summary_cols = st.columns(
        4
    )

    with summary_cols[0]:
        st.metric(
            "Projected",
            f"{result['projected_points']:.1f}",
        )

    with summary_cols[1]:
        st.metric(
            "Salary",
            _fmt_money(
                result[
                    "salary_used"
                ]
            ),
        )

    with summary_cols[2]:
        st.metric(
            "Remaining",
            _fmt_money(
                result[
                    "salary_remaining"
                ]
            ),
        )

    with summary_cols[3]:
        st.metric(
            "Build",
            result[
                "stack_pattern"
            ].replace(
                "_",
                " ",
            ).title(),
        )

    lineup = lineup_frame(
        result,
        saved_strategy,
        locked_keys=saved_locks,
    )

    st.dataframe(
        lineup,
        width="stretch",
        hide_index=True,
        column_config={
            "Salary":
                st.column_config.NumberColumn(
                    format="$%d"
                ),
            "Projection":
                st.column_config.NumberColumn(
                    format="%.2f"
                ),
            "Value/$1K":
                st.column_config.NumberColumn(
                    format="%.2f"
                ),
        },
    )

    st.caption(
        (
            "HULK optimizer score is a lineup-construction score, "
            "not a probability of winning. Projections and player status "
            "can change before lock."
        )
    )

    with st.expander(
        "How HULK built this lineup",
        expanded=False,
    ):
        st.markdown(
            (
                "**Strategy:** "
                + saved_strategy
                + "  \n"
                + "**Locked by you:** "
                + (
                    str(
                        int(
                            lineup[
                                "Locked"
                            ].sum()
                        )
                    )
                    if "Locked"
                    in lineup.columns
                    else "0"
                )
                + "  \n"
                + "**Games represented:** "
                + str(
                    result[
                        "games_used"
                    ]
                )
            )
        )

        explain = lineup[
            [
                "Slot",
                "Player",
                "Projection",
                "Value/$1K",
                "Why",
            ]
        ].copy()

        st.dataframe(
            explain,
            width="stretch",
            hide_index=True,
        )
