import pandas as pd
import streamlit as st

from premium_ui.data import (
    age_text,
    cbb_game_decisions,
    cbb_game_finalists,
    cbb_games_current,
    cbb_learning_summary,
    cbb_parlays,
    cbb_rankings,
    cbb_team_context,
    cbb_team_research,
)

from premium_ui.live_scores import (
    favorite_teams_from_session,
    render_live_scores,
)
from premium_ui.extended_box_scores import (
    render_extended_box_scores,
)

from premium_ui.pages import (
    empty_card,
    friendly,
    line_text,
    number,
    page_intro,
    premium_card,
    safe,
    section_header,
)


CBB_ACCENT = "#E3B341"


def _truth(
    value,
):

    return str(
        value
    ).lower() in {
        "true",
        "1",
        "yes",
    }


def _sort_evidence(
    df,
):

    if (
        df.empty
        or "evidence_score"
        not in df.columns
    ):
        return df


    df = df.copy()

    df[
        "_sort"
    ] = pd.to_numeric(
        df[
            "evidence_score"
        ],
        errors="coerce",
    )


    return df.sort_values(
        "_sort",
        ascending=False,
    )


def _game_headline(
    row,
):

    selection = safe(
        row.get(
            "selection_canonical"
        )
    )

    market = str(
        row.get(
            "market_canonical",
            "",
        )
    ).upper()

    line = line_text(
        row.get(
            "line"
        )
    )


    if (
        market == "MONEYLINE"
        or line == "—"
    ):
        return selection


    return (
        selection
        + " "
        + line
    ).strip()


def render_cbb_games():

    page_intro(
        "College Basketball Games",
        "college",
        "CBB",
        (
            "Live scores and the upcoming Division I "
            "schedule in one clean view."
        ),
    )


    favorites = (
        favorite_teams_from_session()
    )


    render_live_scores(
        "CBB",
        pinned_teams=favorites,
        title=(
            "My Games"
            if favorites
            else "Live & Today"
        ),
    )

    render_extended_box_scores(
        "CBB"
    )


    schedule = cbb_games_current()


    section_header(
        "Upcoming",
        (
            "The current 2026-27 Division I schedule. "
            "Qualified research stays separate."
        ),
    )


    if schedule.empty:

        st.info(
            "No current college basketball "
            "schedule data is available."
        )

        return


    schedule = schedule.copy()


    schedule[
        "_start"
    ] = pd.to_datetime(
        schedule[
            "start"
        ],
        utc=True,
        errors="coerce",
    )


    schedule = schedule.sort_values(
        "_start"
    )


    upcoming = schedule[
        ~schedule[
            "completed"
        ].map(
            _truth
        )
    ].head(
        18
    )


    for start in range(
        0,
        len(
            upcoming
        ),
        3,
    ):

        cols = st.columns(
            3
        )


        for col, (_, row) in zip(
            cols,
            upcoming.iloc[
                start:start + 3
            ].iterrows(),
        ):

            with col:

                start_dt = pd.to_datetime(
                    row.get(
                        "start"
                    ),
                    utc=True,
                    errors="coerce",
                )


                when = (
                    start_dt
                    .tz_convert(
                        "America/New_York"
                    )
                    .strftime(
                        "%a %-I:%M %p ET"
                    )
                    if pd.notna(
                        start_dt
                    )
                    else safe(
                        row.get(
                            "status"
                        )
                    )
                )


                premium_card(
                    (
                        safe(
                            row.get(
                                "away_team_name"
                            )
                        )
                        + " @ "
                        + safe(
                            row.get(
                                "home_team_name"
                            )
                        )
                    ),
                    when,
                    safe(
                        row.get(
                            "status"
                        )
                    ),
                    (
                        "Division I schedule · "
                        + (
                            "Neutral site"
                            if _truth(
                                row.get(
                                    "neutral_site"
                                )
                            )
                            else safe(
                                row.get(
                                    "venue"
                                )
                            )
                        )
                    ),
                    [
                        (
                            "Upcoming",
                            "blue",
                        ),
                    ],
                    CBB_ACCENT,
                )


    section_header(
        "Qualified Game Research",
        (
            "Nothing appears here until the current-season "
            "and market gates are satisfied."
        ),
    )


    finalists = _sort_evidence(
        cbb_game_finalists()
    )


    if finalists.empty:

        premium_card(
            "No Qualified CBB Picks Yet",
            "Preseason / Early Season Gate",
            "0 finalists",
            (
                "Sports HULK requires at least five "
                "current-season games for both teams "
                "before a game can become a finalist."
            ),
            [
                (
                    "No forced picks",
                    "green",
                ),
                (
                    "Prior season ≠ current season",
                    "amber",
                ),
            ],
            CBB_ACCENT,
        )

        return


    for start in range(
        0,
        min(
            len(
                finalists
            ),
            12,
        ),
        3,
    ):

        cols = st.columns(
            3
        )


        for col, (_, row) in zip(
            cols,
            finalists.iloc[
                start:start + 3
            ].iterrows(),
        ):

            with col:

                premium_card(
                    safe(
                        row.get(
                            "game_key"
                        )
                    ),
                    friendly(
                        row.get(
                            "market_canonical"
                        )
                    ),
                    _game_headline(
                        row
                    ),
                    (
                        safe(
                            row.get(
                                "sportsbook_count",
                                "0",
                            )
                        )
                        + " books · "
                        + friendly(
                            row.get(
                                "context_direction"
                            )
                        )
                    ),
                    [
                        (
                            "Evidence "
                            + number(
                                row.get(
                                    "evidence_score"
                                )
                            ),
                            "blue",
                        ),
                        (
                            friendly(
                                row.get(
                                    "decision"
                                )
                            ),
                            "green",
                        ),
                    ],
                    CBB_ACCENT,
                )


def render_cbb_picks():

    page_intro(
        "College Basketball Picks",
        "college",
        "CBB",
        (
            "Team-level research only. Current-season "
            "evidence must exist before anything becomes a pick."
        ),
    )


    data = _sort_evidence(
        cbb_game_finalists()
    )


    st.caption(
        age_text(
            "/home/ubuntu/sports-hulk/"
            "cbb_live/decision/"
            "CBB_GAME_FINALISTS.csv"
        )
    )


    if data.empty:

        empty_card(
            "No Qualified Picks Right Now",
            (
                "The 2026-27 season has not produced enough "
                "current evidence yet. Prior-season Elo and SRS "
                "remain background context only."
            ),
            CBB_ACCENT,
        )


        decisions = cbb_game_decisions()


        if not decisions.empty:

            with st.expander(
                "Open current market research"
            ):

                st.dataframe(
                    _sort_evidence(
                        decisions
                    ),
                    width="stretch",
                    hide_index=True,
                )


        return


    for start in range(
        0,
        min(
            len(
                data
            ),
            15,
        ),
        3,
    ):

        cols = st.columns(
            3
        )


        for col, (_, row) in zip(
            cols,
            data.iloc[
                start:start + 3
            ].iterrows(),
        ):

            with col:

                premium_card(
                    (
                        safe(
                            row.get(
                                "away_team_name"
                            )
                        )
                        + " @ "
                        + safe(
                            row.get(
                                "home_team_name"
                            )
                        )
                    ),
                    friendly(
                        row.get(
                            "market_canonical"
                        )
                    ),
                    _game_headline(
                        row
                    ),
                    (
                        "Current games: "
                        + safe(
                            row.get(
                                "selected_current_games",
                                "0",
                            )
                        )
                        + " / "
                        + safe(
                            row.get(
                                "opponent_current_games",
                                "0",
                            )
                        )
                    ),
                    [
                        (
                            "Evidence "
                            + number(
                                row.get(
                                    "evidence_score"
                                )
                            ),
                            "blue",
                        ),
                        (
                            friendly(
                                row.get(
                                    "decision"
                                )
                            ),
                            "green",
                        ),
                    ],
                    CBB_ACCENT,
                )


    with st.expander(
        "Open full CBB pick research"
    ):

        st.dataframe(
            data.drop(
                columns=[
                    "_sort"
                ],
                errors="ignore",
            ),
            width="stretch",
            hide_index=True,
        )


def render_cbb_parlays():

    page_intro(
        "College Basketball Parlays",
        "parlays",
        "CBB",
        (
            "Two-leg research combinations are created "
            "only from already-qualified game finalists."
        ),
    )


    data = _sort_evidence(
        cbb_parlays()
    )


    if data.empty:

        empty_card(
            "No Qualified CBB Combinations",
            (
                "There are no qualified game finalists yet, "
                "so Sports HULK will not manufacture a parlay."
            ),
            "#0F9F9A",
        )

        return


    for start in range(
        0,
        min(
            len(
                data
            ),
            12,
        ),
        3,
    ):

        cols = st.columns(
            3
        )


        for col, (_, row) in zip(
            cols,
            data.iloc[
                start:start + 3
            ].iterrows(),
        ):

            with col:

                leg1 = (
                    safe(
                        row.get(
                            "leg1_game"
                        )
                    )
                    + " · "
                    + safe(
                        row.get(
                            "leg1_selection"
                        )
                    )
                )

                leg2 = (
                    safe(
                        row.get(
                            "leg2_game"
                        )
                    )
                    + " · "
                    + safe(
                        row.get(
                            "leg2_selection"
                        )
                    )
                )


                premium_card(
                    "2-Leg Research",
                    safe(
                        row.get(
                            "status"
                        )
                    ),
                    (
                        "Evidence "
                        + number(
                            row.get(
                                "evidence_score"
                            )
                        )
                    ),
                    (
                        leg1
                        + "  +  "
                        + leg2
                    ),
                    [
                        (
                            "Different games",
                            "green",
                        ),
                        (
                            "No payout inferred",
                            "amber",
                        ),
                    ],
                    "#0F9F9A",
                )


    st.caption(
        (
            "Evidence scores are not probabilities. "
            "No sportsbook payout is inferred."
        )
    )


def render_cbb_rankings():

    page_intro(
        "College Basketball Rankings",
        "college",
        "CBB",
        (
            "Poll rankings with season freshness shown "
            "explicitly so stale rankings are never mistaken "
            "for current evidence."
        ),
    )


    data = cbb_rankings()


    if data.empty:

        st.info(
            "No college basketball ranking "
            "data is available."
        )

        return


    data = data.copy()


    current = (
        data[
            "current_season_match"
        ].map(
            _truth
        )
        if "current_season_match"
        in data.columns
        else pd.Series(
            False,
            index=data.index,
        )
    )


    current_count = int(
        current.sum()
    )


    if current_count == 0:

        st.warning(
            (
                "The latest available AP and Coaches polls "
                "are from the completed 2025-26 season. "
                "They are shown for reference only and are "
                "not being used as current 2026-27 evidence."
            )
        )


    polls = list(
        data[
            "poll"
        ]
        .dropna()
        .unique()
    )


    for poll in polls:

        section_header(
            poll,
            (
                "Current-season poll"
                if current_count
                else "Latest available prior-season poll"
            ),
        )


        subset = (
            data[
                data[
                    "poll"
                ].eq(
                    poll
                )
            ]
            .sort_values(
                "rank"
            )
            .head(
                25
            )
        )


        for start in range(
            0,
            len(
                subset
            ),
            5,
        ):

            cols = st.columns(
                5
            )


            for col, (_, row) in zip(
                cols,
                subset.iloc[
                    start:start + 5
                ].iterrows(),
            ):

                with col:

                    premium_card(
                        (
                            "#"
                            + safe(
                                row.get(
                                    "rank"
                                )
                            )
                        ),
                        safe(
                            row.get(
                                "team_name"
                            )
                        ),
                        safe(
                            row.get(
                                "team"
                            )
                        ),
                        (
                            "Previous: #"
                            + safe(
                                row.get(
                                    "previous_rank"
                                )
                            )
                            + " · "
                            + safe(
                                row.get(
                                    "trend"
                                )
                            )
                        ),
                        [
                            (
                                (
                                    "Current"
                                    if _truth(
                                        row.get(
                                            "current_season_match"
                                        )
                                    )
                                    else "Prior season"
                                ),
                                (
                                    "green"
                                    if _truth(
                                        row.get(
                                            "current_season_match"
                                        )
                                    )
                                    else "amber"
                                ),
                            ),
                        ],
                        CBB_ACCENT,
                    )


def render_cbb_research():

    page_intro(
        "College Basketball Research",
        "college",
        "CBB",
        (
            "Deeper team context stays here so the "
            "games and picks pages remain simple."
        ),
    )


    research = cbb_team_research()

    context = cbb_team_context()

    learning = cbb_learning_summary()


    section_header(
        "Current Research State",
        (
            "The system separates preseason baseline "
            "from current-season evidence."
        ),
    )


    ready = 0


    if (
        not context.empty
        and "finalist_eligible"
        in context.columns
    ):

        ready = int(
            context[
                "finalist_eligible"
            ].map(
                _truth
            ).sum()
        )


    cols = st.columns(
        3
    )


    with cols[
        0
    ]:

        premium_card(
            "Team Context",
            "Current",
            str(
                len(
                    context
                )
            ),
            "Teams tracked in the research layer.",
            [
                (
                    "Team-level only",
                    "blue",
                ),
            ],
            CBB_ACCENT,
        )


    with cols[
        1
    ]:

        premium_card(
            "Finalist Eligible",
            "5-game gate",
            str(
                ready
            ),
            (
                "Teams with enough current-season "
                "games to enter the finalist process."
            ),
            [
                (
                    "Current evidence",
                    "green",
                ),
            ],
            CBB_ACCENT,
        )


    with cols[
        2
    ]:

        premium_card(
            "Learning",
            "Settled results",
            str(
                learning.get(
                    "settled",
                    0,
                )
            ),
            (
                "Automatic model adjustment remains "
                "off until evidence thresholds are met."
            ),
            [
                (
                    "Auto-adjust OFF",
                    "amber",
                ),
            ],
            CBB_ACCENT,
        )


    section_header(
        "Upcoming Team Research",
        (
            "Prior-season Elo/SRS is visible as baseline "
            "context, never as a current-season pick."
        ),
    )


    if research.empty:

        st.info(
            "No CBB team research is available."
        )

        return


    shown = research.copy()


    shown[
        "_gap"
    ] = pd.to_numeric(
        shown[
            "prior_srs_gap_home"
        ],
        errors="coerce",
    ).abs()


    shown = shown.sort_values(
        [
            "game_date",
            "_gap",
        ],
        ascending=[
            True,
            False,
        ],
    ).head(
        30
    )


    for start in range(
        0,
        min(
            len(
                shown
            ),
            15,
        ),
        3,
    ):

        cols = st.columns(
            3
        )


        for col, (_, row) in zip(
            cols,
            shown.iloc[
                start:start + 3
            ].iterrows(),
        ):

            with col:

                premium_card(
                    (
                        safe(
                            row.get(
                                "away_team_name"
                            )
                        )
                        + " @ "
                        + safe(
                            row.get(
                                "home_team_name"
                            )
                        )
                    ),
                    safe(
                        row.get(
                            "game_date"
                        )
                    ),
                    friendly(
                        row.get(
                            "context_stage"
                        )
                    ),
                    (
                        "Prior Elo gap (home): "
                        + number(
                            row.get(
                                "prior_elo_gap_home"
                            )
                        )
                        + " · Prior SRS gap: "
                        + number(
                            row.get(
                                "prior_srs_gap_home"
                            )
                        )
                    ),
                    [
                        (
                            friendly(
                                row.get(
                                    "research_status"
                                )
                            ),
                            "amber",
                        ),
                        (
                            "Not a pick",
                            "green",
                        ),
                    ],
                    CBB_ACCENT,
                )


    with st.expander(
        "Open full CBB research table"
    ):

        st.dataframe(
            research,
            width="stretch",
            hide_index=True,
        )


def render_cbb_feature(
    feature,
):

    routes = {
        "games":
            render_cbb_games,

        "picks":
            render_cbb_picks,

        "parlays":
            render_cbb_parlays,

        "rankings":
            render_cbb_rankings,

        "research":
            render_cbb_research,
    }


    fn = routes.get(
        feature
    )


    if not fn:

        return False


    fn()

    return True
