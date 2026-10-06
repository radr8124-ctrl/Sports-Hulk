import pandas as pd
import streamlit as st

from premium_ui.betting_boards import render_game_betting_board
from premium_ui.prop_boards import render_player_prop_board

from premium_ui.data import (
    age_text,
    nhl_fantasy,
    nhl_game_finalists,
    nhl_games_current,
    nhl_parlays,
    nhl_pickem_decisions,
    nhl_pickem_finalists,
    nhl_prop_decisions,
    nhl_prop_finalists,
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


NHL_ACCENT = "#54C6EB"


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

    df["_sort"] = pd.to_numeric(
        df["evidence_score"],
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
            "line_group"
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


def render_nhl_games():

    page_intro(
        "NHL Games",
        "today",
        "NHL",
        (
            "Live scores, upcoming games and "
            "qualified research in one place."
        ),
    )

    favorites = (
        favorite_teams_from_session()
    )

    render_live_scores(
        "NHL",
        pinned_teams=favorites,
        title=(
            "My Games"
            if favorites
            else "Live & Today"
        ),
    )

    render_extended_box_scores(
        "NHL"
    )

    schedule = nhl_games_current()

    section_header(
        "Upcoming",
        (
            "Current schedule and game status. "
            "Research appears separately below."
        ),
    )

    if schedule.empty:

        st.info(
            "No current NHL schedule data is available."
        )

    else:

        schedule = schedule.copy()

        schedule["_start"] = pd.to_datetime(
            schedule["start"],
            utc=True,
            errors="coerce",
        )

        schedule = schedule.sort_values(
            "_start"
        )

        upcoming = schedule[
            ~schedule[
                "completed"
            ]
            .astype(str)
            .str.lower()
            .isin(
                [
                    "true",
                    "1",
                ]
            )
        ].head(
            15
        )

        for start in range(
            0,
            len(upcoming),
            3,
        ):

            cols = st.columns(3)

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

                    display_time = (
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
                                    "away_team"
                                )
                            )
                            + " @ "
                            + safe(
                                row.get(
                                    "home_team"
                                )
                            )
                        ),
                        display_time,
                        safe(
                            row.get(
                                "game_state"
                            )
                        ),
                        "Official NHL game status and schedule.",
                        [
                            (
                                "Upcoming",
                                "blue",
                            ),
                        ],
                        NHL_ACCENT,
                    )

    finalists = _sort_evidence(
        nhl_game_finalists()
    )

    section_header(
        "Qualified Game Research",
        (
            "Only games clearing the current "
            "evidence gates appear here."
        ),
    )

    if finalists.empty:

        st.info(
            "No qualified NHL game research "
            "is available right now."
        )

        return

    for start in range(
        0,
        min(
            len(finalists),
            12,
        ),
        3,
    ):

        cols = st.columns(3)

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
                                "approved_book_count",
                                "0",
                            )
                        )
                        + " sportsbook sources · "
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
                    NHL_ACCENT,
                )


def render_nhl_picks():
    page_intro(
        "NHL Best Bets",
        "picks",
        "NHL",
        (
            "Qualified NHL bets with sportsbook depth, "
            "historical form and injury review context."
        ),
    )

    data = nhl_game_finalists()

    st.caption(
        age_text(
            "/home/ubuntu/sports-hulk/"
            "nhl_live/decision/"
            "NHL_GAME_FINALISTS.csv"
        )
    )

    render_game_betting_board(
        data,
        sport="NHL",
        accent=NHL_ACCENT,
        title="NHL Best Bets",
        away_col="away_team_canonical",
        home_col="home_team_canonical",
        market_col="market_canonical",
        selection_col="selection_canonical",
        line_col="line_group",
        evidence_col="evidence_score",
        book_col="sportsbook_count",
        approved_book_col="approved_book_count",
        price_col="median_price_american",
        full_data=nhl_game_finalists(),
        full_title="Open full NHL game research",
    )

def _render_player_cards(
    data,
    accent,
    limit=18,
    book_col="book_count",
):

    data = _sort_evidence(
        data
    )

    for start in range(
        0,
        min(
            len(data),
            limit,
        ),
        3,
    ):

        cols = st.columns(3)

        for col, (_, row) in zip(
            cols,
            data.iloc[
                start:start + 3
            ].iterrows(),
        ):

            with col:

                premium_card(
                    safe(
                        row.get(
                            "player"
                        )
                    ),
                    friendly(
                        row.get(
                            "market_subtype"
                        )
                    ),
                    (
                        safe(
                            row.get(
                                "side"
                            )
                        )
                        + " "
                        + line_text(
                            row.get(
                                "line"
                            )
                        )
                    ).strip(),
                    (
                        "L5 "
                        + number(
                            row.get(
                                "stat_l5_avg"
                            )
                        )
                        + " · L10 hit "
                        + (
                            number(
                                (
                                    pd.to_numeric(
                                        row.get(
                                            "l10_hit_rate"
                                        ),
                                        errors="coerce",
                                    )
                                    * 100
                                )
                            )
                            + "%"
                            if pd.notna(
                                pd.to_numeric(
                                    row.get(
                                        "l10_hit_rate"
                                    ),
                                    errors="coerce",
                                )
                            )
                            else "—"
                        )
                        + " · "
                        + safe(
                            row.get(
                                book_col,
                                "0",
                            )
                        )
                        + " books"
                    ),
                    [
                        (
                            "Evidence "
                            + number(
                                row.get(
                                    "evidence_score"
                                )
                            ),
                            "purple",
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
                    accent,
                )


def render_nhl_props():

    page_intro(
        "NHL Player Props",
        "props",
        "NHL",
        (
            "Historical performance, minutes, injury "
            "status and sportsbook evidence."
        ),
    )

    finalists = nhl_prop_finalists()
    decisions = nhl_prop_decisions()

    if finalists.empty:

        early = 0

        if (
            not decisions.empty
            and "decision"
            in decisions.columns
        ):

            early = int(
                decisions[
                    "decision"
                ]
                .eq(
                    "EARLY_MARKET_WATCH"
                )
                .sum()
            )

        premium_card(
            "No Qualified Props Yet",
            "Early Market Collection",
            f"{early} tracked",
            (
                "The lines are being archived and analyzed, "
                "but they are too early to lock as finalists."
            ),
            [
                (
                    "No forced picks",
                    "green",
                ),
            ],
            "#7C3AED",
        )

        if not decisions.empty:

            with st.expander(
                "View early prop research"
            ):

                cols = [
                    c
                    for c in [
                        "player",
                        "current_team",
                        "market_subtype",
                        "side",
                        "line",
                        "stat_l5_avg",
                        "stat_l10_avg",
                        "l10_hit_rate",
                        "book_count",
                        "injury_gate",
                        "evidence_score",
                        "decision",
                    ]
                    if c in decisions.columns
                ]

                st.dataframe(
                    _sort_evidence(
                        decisions
                    )[
                        cols
                    ].head(
                        40
                    ),
                    width="stretch",
                    hide_index=True,
                )

        return

    _render_player_cards(
        finalists,
        "#7C3AED",
    )


def render_nhl_prizepicks():

    page_intro(
        "NHL PrizePicks",
        "prizepicks",
        "NHL",
        (
            "Projection research cross-checked against "
            "historical performance and sportsbook lines."
        ),
    )

    finalists = (
        nhl_pickem_finalists()
    )

    decisions = (
        nhl_pickem_decisions()
    )

    if finalists.empty:

        early = 0

        if (
            not decisions.empty
            and "decision"
            in decisions.columns
        ):

            early = int(
                decisions[
                    "decision"
                ]
                .eq(
                    "EARLY_MARKET_WATCH"
                )
                .sum()
            )

        premium_card(
            "No Qualified PrizePicks Yet",
            "Early Projection Watch",
            f"{early} tracked",
            (
                "Current projections are being stored "
                "and compared, but they are still outside "
                "the finalist time window."
            ),
            [
                (
                    "No manufactured selections",
                    "green",
                ),
            ],
            "#C026D3",
        )

        if not decisions.empty:

            with st.expander(
                "View early PrizePicks research"
            ):

                cols = [
                    c
                    for c in [
                        "player",
                        "current_team",
                        "market_subtype",
                        "side",
                        "line",
                        "sportsbook_book_count",
                        "stat_l5_avg",
                        "stat_l10_avg",
                        "l10_hit_rate",
                        "injury_gate",
                        "evidence_score",
                        "decision",
                    ]
                    if c in decisions.columns
                ]

                st.dataframe(
                    _sort_evidence(
                        decisions
                    )[
                        cols
                    ].head(
                        40
                    ),
                    width="stretch",
                    hide_index=True,
                )

        return

    _render_player_cards(
        finalists,
        "#C026D3",
        book_col=(
            "sportsbook_book_count"
        ),
    )


def render_nhl_fantasy():

    page_intro(
        "NHL Fantasy",
        "fantasy",
        "NHL",
        (
            "Recent ice time, production, shots, "
            "physical stats and injury context."
        ),
    )

    data = nhl_fantasy()

    if data.empty:

        st.info(
            "No current NHL fantasy context "
            "is available."
        )

        return


    section_header(
        "Usage & Opportunity",
        (
            "Current NHL roster players ranked by "
            "recent ice time and production context."
        ),
    )


    shown = data.head(
        18
    )


    for start in range(
        0,
        len(
            shown
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

                player = (
                    safe(
                        row.get(
                            "player_current"
                        )
                    )
                    or safe(
                        row.get(
                            "player_history"
                        )
                    )
                )


                premium_card(
                    player,
                    (
                        safe(
                            row.get(
                                "team_current"
                            )
                        )
                        + " · "
                        + safe(
                            row.get(
                                "position_current"
                            )
                        )
                    ),
                    (
                        number(
                            row.get(
                                "toi_minutes_l5_avg"
                            )
                        )
                        + " TOI"
                    ),
                    (
                        "L5: "
                        + number(
                            row.get(
                                "points_l5_avg"
                            )
                        )
                        + " PTS · "
                        + number(
                            row.get(
                                "shots_on_goal_l5_avg"
                            )
                        )
                        + " SOG · "
                        + number(
                            row.get(
                                "hits_l5_avg"
                            )
                        )
                        + " HIT · "
                        + number(
                            row.get(
                                "blocked_shots_l5_avg"
                            )
                        )
                        + " BLK"
                    ),
                    [
                        (
                            friendly(
                                row.get(
                                    "injury_gate",
                                    "CLEAR",
                                )
                            ),
                            (
                                "green"
                                if row.get(
                                    "injury_gate"
                                )
                                == "CLEAR"
                                else "amber"
                            ),
                        ),
                        (
                            "Usage Watch",
                            "orange",
                        ),
                    ],
                    "#EA7C22",
                )


    with st.expander(
        "Open full NHL fantasy context"
    ):

        st.dataframe(
            data,
            width="stretch",
            hide_index=True,
        )

    try:
        stash = pd.read_csv(
            (
                "/home/ubuntu/sports-hulk/"
                "intelligence_warehouse/fantasy_decisions/"
                "FANTASY_IR_STASH_CURRENT.csv"
            ),
            low_memory=False,
        )
    except Exception:
        stash = pd.DataFrame()

    if not stash.empty:
        stash_nhl = stash[
            stash["sport"].astype(str).eq("NHL")
            & stash["stash_tier"].astype(str).isin(
                [
                    "HIGH_PRIORITY_STASH",
                    "STRONG_STASH",
                    "WATCH_STASH",
                    "REVIEW_SOURCE_CONFLICT",
                ]
            )
        ].copy()

        stash_nhl["_score"] = pd.to_numeric(
            stash_nhl.get(
                "stash_research_score"
            ),
            errors="coerce",
        )
        stash_nhl = stash_nhl.sort_values(
            "_score",
            ascending=False,
        )

        if not stash_nhl.empty:
            section_header(
                "IR & Return Stash",
                (
                    "Return timing, role context and source "
                    "agreement for injured players."
                ),
            )

            for start in range(
                0,
                min(len(stash_nhl), 9),
                3,
            ):
                cols = st.columns(3)

                for col, (_, row) in zip(
                    cols,
                    stash_nhl.iloc[
                        start:start + 3
                    ].iterrows(),
                ):
                    with col:
                        premium_card(
                            safe(
                                row.get(
                                    "player"
                                )
                            ),
                            (
                                safe(
                                    row.get(
                                        "team"
                                    )
                                )
                                + " · "
                                + safe(
                                    row.get(
                                        "position"
                                    )
                                )
                            ),
                            friendly(
                                row.get(
                                    "stash_tier"
                                )
                            ),
                            (
                                friendly(
                                    row.get(
                                        "return_window"
                                    )
                                )
                                + " · "
                                + safe(
                                    row.get(
                                        "status"
                                    )
                                )
                            ),
                            [
                                (
                                    "Return research",
                                    "blue",
                                ),
                            ],
                            "#EA7C22",
                        )

            with st.expander(
                "Open full NHL return / stash research"
            ):
                st.dataframe(
                    stash_nhl.drop(
                        columns=[
                            "_score"
                        ],
                        errors="ignore",
                    ),
                    width="stretch",
                    hide_index=True,
                )


def _leg_text(
    row,
    leg,
):

    lane = safe(
        row.get(
            f"leg{leg}_lane"
        )
    )

    player = safe(
        row.get(
            f"leg{leg}_player"
        )
    )

    game = safe(
        row.get(
            f"leg{leg}_game"
        )
    )

    market = friendly(
        row.get(
            f"leg{leg}_market"
        )
    )

    selection = safe(
        row.get(
            f"leg{leg}_selection"
        )
    )

    line = line_text(
        row.get(
            f"leg{leg}_line"
        )
    )

    subject = (
        player
        if player
        else game
    )

    pick = selection

    if line != "—":
        pick = (
            pick
            + " "
            + line
        ).strip()

    return (
        f"{lane}: {subject} · "
        f"{market} {pick}"
    ).strip()


def render_nhl_parlays():

    page_intro(
        "NHL Parlays",
        "parlays",
        "NHL",
        (
            "Two-leg research combinations built only "
            "from already-qualified legs."
        ),
    )

    data = _sort_evidence(
        nhl_parlays()
    )

    if data.empty:

        st.info(
            "No qualified NHL research combinations "
            "are available right now."
        )

        return

    for start in range(
        0,
        min(
            len(data),
            12,
        ),
        3,
    ):

        cols = st.columns(3)

        for col, (_, row) in zip(
            cols,
            data.iloc[
                start:start + 3
            ].iterrows(),
        ):

            with col:

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
                        _leg_text(
                            row,
                            1,
                        )
                        + "  +  "
                        + _leg_text(
                            row,
                            2,
                        )
                    ),
                    [
                        (
                            "Different games",
                            "green",
                        ),
                        (
                            "Verify payout",
                            "amber",
                        ),
                    ],
                    "#0F9F9A",
                )

    st.caption(
        (
            "Evidence scores are not win probabilities. "
            "No sportsbook payout is inferred."
        )
    )


def render_nhl_feature(
    feature,
):

    routes = {
        "games":
            render_nhl_games,

        "picks":
            render_nhl_picks,

        "props":
            render_nhl_props,

        "prizepicks":
            render_nhl_prizepicks,

        "fantasy":
            render_nhl_fantasy,

        "parlays":
            render_nhl_parlays,
    }

    fn = routes.get(
        feature
    )

    if not fn:
        return False

    fn()

    return True
