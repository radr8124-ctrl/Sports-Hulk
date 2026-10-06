import pandas as pd
import streamlit as st

from premium_ui.betting_boards import render_game_betting_board
from premium_ui.prop_boards import render_player_prop_board

from premium_ui.data import (
    age_text,
    nba_fantasy,
    nba_game_finalists,
    nba_games_current,
    nba_parlays,
    nba_pickem_decisions,
    nba_pickem_finalists,
    nba_prop_decisions,
    nba_prop_finalists,
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


NBA_ACCENT = "#EA580C"


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


def render_nba_games():

    page_intro(
        "NBA Games",
        "today",
        "NBA",
        (
            "Live scores, upcoming games and "
            "qualified research in one place."
        ),
    )

    favorites = (
        favorite_teams_from_session()
    )

    render_live_scores(
        "NBA",
        pinned_teams=favorites,
        title=(
            "My Games"
            if favorites
            else "Live & Today"
        ),
    )

    render_extended_box_scores(
        "NBA"
    )

    schedule = nba_games_current()

    section_header(
        "Upcoming",
        (
            "Current schedule and game status. "
            "Research appears separately below."
        ),
    )

    if schedule.empty:

        st.info(
            "No current NBA schedule data is available."
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
                                "status"
                            )
                        ),
                        "Official game status and schedule.",
                        [
                            (
                                "Upcoming",
                                "blue",
                            ),
                        ],
                        NBA_ACCENT,
                    )

    finalists = _sort_evidence(
        nba_game_finalists()
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
            "No qualified NBA game research "
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
                    NBA_ACCENT,
                )


def render_nba_picks():
    page_intro(
        "NBA Best Bets",
        "picks",
        "NBA",
        (
            "Qualified NBA bets with sportsbook depth, "
            "market price and independent basketball context."
        ),
    )

    data = nba_game_finalists()

    st.caption(
        age_text(
            "/home/ubuntu/sports-hulk/"
            "nba_live/decision/"
            "NBA_GAME_FINALISTS.csv"
        )
    )

    render_game_betting_board(
        data,
        sport="NBA",
        accent=NBA_ACCENT,
        title="NBA Best Bets",
        away_col="away_team_canonical",
        home_col="home_team_canonical",
        market_col="market_canonical",
        selection_col="selection_canonical",
        line_col="line_group",
        evidence_col="evidence_score",
        book_col="sportsbook_count",
        approved_book_col="approved_book_count",
        price_col="median_price_american",
        full_data=nba_game_finalists(),
        full_title="Open full NBA game research",
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


def render_nba_props():

    page_intro(
        "NBA Player Props",
        "props",
        "NBA",
        (
            "Historical performance, minutes, injury "
            "status and sportsbook evidence."
        ),
    )

    finalists = nba_prop_finalists()
    decisions = nba_prop_decisions()

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


def render_nba_prizepicks():

    page_intro(
        "NBA PrizePicks",
        "prizepicks",
        "NBA",
        (
            "Projection research cross-checked against "
            "historical performance and sportsbook lines."
        ),
    )

    finalists = (
        nba_pickem_finalists()
    )

    decisions = (
        nba_pickem_decisions()
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


def render_nba_fantasy():

    page_intro(
        "NBA Fantasy",
        "fantasy",
        "NBA",
        (
            "Minutes, recent production, role and "
            "injury context without fake start/sit calls."
        ),
    )

    data = nba_fantasy()

    if data.empty:

        st.info(
            "No current NBA fantasy context "
            "is available."
        )

        return

    section_header(
        "Usage & Opportunity",
        (
            "Current roster players ranked by recent "
            "minutes and production context."
        ),
    )

    shown = data.head(
        18
    )

    for start in range(
        0,
        len(shown),
        3,
    ):

        cols = st.columns(3)

        for col, (_, row) in zip(
            cols,
            shown.iloc[
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
                                "minutes_l5_avg"
                            )
                        )
                        + " MIN"
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
                                "rebounds_l5_avg"
                            )
                        )
                        + " REB · "
                        + number(
                            row.get(
                                "assists_l5_avg"
                            )
                        )
                        + " AST"
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
        "Open full fantasy context"
    ):

        st.dataframe(
            data,
            width="stretch",
            hide_index=True,
        )

    decision_dir = (
        "/home/ubuntu/sports-hulk/"
        "intelligence_warehouse/fantasy_decisions/"
    )

    try:
        faab = pd.read_csv(
            decision_dir
            + "FANTASY_FAAB_RESEARCH_CURRENT.csv",
            low_memory=False,
        )
    except Exception:
        faab = pd.DataFrame()

    try:
        stash = pd.read_csv(
            decision_dir
            + "FANTASY_IR_STASH_CURRENT.csv",
            low_memory=False,
        )
    except Exception:
        stash = pd.DataFrame()

    if not faab.empty:
        waiver = faab[
            faab["sport"].astype(str).eq("NBA")
            & faab["waiver_priority"].astype(str).isin(
                [
                    "AGGRESSIVE_ADD",
                    "STRONG_ADD",
                    "TARGET_ADD",
                    "WATCH_ADD",
                ]
            )
        ].copy()

        waiver["_score"] = pd.to_numeric(
            waiver.get(
                "waiver_research_score"
            ),
            errors="coerce",
        )
        waiver = waiver.sort_values(
            "_score",
            ascending=False,
        )

        if not waiver.empty:
            section_header(
                "Waiver & FAAB",
                (
                    "Add velocity, role movement and availability "
                    "combined into a research budget range."
                ),
            )

            for start in range(
                0,
                min(len(waiver), 9),
                3,
            ):
                cols = st.columns(3)

                for col, (_, row) in zip(
                    cols,
                    waiver.iloc[
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
                                    "waiver_priority"
                                )
                            ),
                            (
                                "FAAB "
                                + safe(
                                    row.get(
                                        "suggested_faab_low_pct"
                                    )
                                )
                                + "–"
                                + safe(
                                    row.get(
                                        "suggested_faab_high_pct"
                                    )
                                )
                                + "%"
                            ),
                            [
                                (
                                    friendly(
                                        row.get(
                                            "role_signal"
                                        )
                                    ),
                                    "green",
                                ),
                            ],
                            "#EA7C22",
                        )

            with st.expander(
                "Open full NBA waiver / FAAB research"
            ):
                st.dataframe(
                    waiver.drop(
                        columns=[
                            "_score"
                        ],
                        errors="ignore",
                    ),
                    width="stretch",
                    hide_index=True,
                )

    if not stash.empty:
        stash_nba = stash[
            stash["sport"].astype(str).eq("NBA")
            & stash["stash_tier"].astype(str).isin(
                [
                    "HIGH_PRIORITY_STASH",
                    "STRONG_STASH",
                    "WATCH_STASH",
                    "REVIEW_SOURCE_CONFLICT",
                ]
            )
        ].copy()

        stash_nba["_score"] = pd.to_numeric(
            stash_nba.get(
                "stash_research_score"
            ),
            errors="coerce",
        )
        stash_nba = stash_nba.sort_values(
            "_score",
            ascending=False,
        )

        if not stash_nba.empty:
            section_header(
                "IR & Return Stash",
                (
                    "Return timing, role context and source "
                    "agreement kept separate from normal waivers."
                ),
            )

            for start in range(
                0,
                min(len(stash_nba), 9),
                3,
            ):
                cols = st.columns(3)

                for col, (_, row) in zip(
                    cols,
                    stash_nba.iloc[
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
                            safe(
                                row.get(
                                    "team"
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
                                    (
                                        "Source conflict"
                                        if row.get(
                                            "source_disagreement"
                                        )
                                        is True
                                        else "Return research"
                                    ),
                                    (
                                        "amber"
                                        if row.get(
                                            "source_disagreement"
                                        )
                                        is True
                                        else "blue"
                                    ),
                                ),
                            ],
                            "#EA7C22",
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


def render_nba_parlays():

    page_intro(
        "NBA Parlays",
        "parlays",
        "NBA",
        (
            "Two-leg research combinations built only "
            "from already-qualified legs."
        ),
    )

    data = _sort_evidence(
        nba_parlays()
    )

    if data.empty:

        st.info(
            "No qualified NBA research combinations "
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


def render_nba_feature(
    feature,
):

    routes = {
        "games":
            render_nba_games,

        "picks":
            render_nba_picks,

        "props":
            render_nba_props,

        "prizepicks":
            render_nba_prizepicks,

        "fantasy":
            render_nba_fantasy,

        "parlays":
            render_nba_parlays,
    }

    fn = routes.get(
        feature
    )

    if not fn:
        return False

    fn()

    return True
