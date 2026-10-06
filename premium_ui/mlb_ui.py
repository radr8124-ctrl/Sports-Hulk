import pandas as pd
import streamlit as st

from premium_ui.betting_boards import render_game_betting_board
from premium_ui.prop_boards import render_player_prop_board

from premium_ui.data import (
    age_text,
    mlb_fantasy,
    mlb_game_decisions,
    mlb_game_finalists,
    mlb_games_current,
    mlb_learning_summary,
    mlb_parlays,
    mlb_score_snapshot,
    mlb_pickem_decisions,
    mlb_pickem_finalists,
    mlb_prop_decisions,
    mlb_prop_finalists,
)

from premium_ui.live_scores import (
    favorite_teams_from_session,
    render_live_scores,
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


MLB_ACCENT = "#EF5A68"


def _sort_evidence(df):
    if (
        df.empty
        or "evidence_score" not in df.columns
    ):
        return df

    d = df.copy()
    d["_sort"] = pd.to_numeric(
        d["evidence_score"],
        errors="coerce",
    )

    return d.sort_values(
        "_sort",
        ascending=False,
    )


def _game_pick(row):
    selection = safe(
        row.get("selection_canonical")
    )
    market = str(
        row.get("market_canonical") or ""
    ).upper()
    line = line_text(
        row.get("line")
    )

    if market == "MONEYLINE":
        return selection

    return (
        selection
        + " "
        + line
    ).strip()


def _player_pick(row):
    return (
        friendly(
            row.get("side")
        )
        + " "
        + line_text(
            row.get("line")
        )
    ).strip()


def _render_mlb_box_scores():
    payload = mlb_score_snapshot()

    if not isinstance(
        payload,
        dict,
    ):
        return

    games = payload.get(
        "today_games"
    ) or []

    detailed = [
        game
        for game in games
        if isinstance(
            game.get(
                "boxscore"
            ),
            dict,
        )
        and game.get(
            "boxscore"
        )
    ]

    if not detailed:
        st.caption(
            "Detailed MLB box scores will appear here when live/final game data is available."
        )
        return

    section_header(
        "Box Score",
        (
            "Choose one live or completed game for batting "
            "and pitching lines."
        ),
    )

    labels = []
    lookup = {}

    for game in detailed:
        away = safe(
            game.get(
                "away"
            )
        )
        home = safe(
            game.get(
                "home"
            )
        )
        away_score = safe(
            game.get(
                "away_score"
            )
        )
        home_score = safe(
            game.get(
                "home_score"
            )
        )
        status = safe(
            game.get(
                "status"
            )
        )

        label = (
            away
            + " "
            + away_score
            + " · "
            + home
            + " "
            + home_score
            + (
                " · "
                + status
                if status
                else ""
            )
        )

        labels.append(
            label
        )
        lookup[
            label
        ] = game

    selected_label = st.selectbox(
        "MLB box score game",
        labels,
        index=0,
        label_visibility="collapsed",
        key="mlb_box_score_game",
    )

    game = lookup[
        selected_label
    ]

    away = safe(
        game.get(
            "away"
        )
    )
    home = safe(
        game.get(
            "home"
        )
    )
    box = game.get(
        "boxscore"
    ) or {}

    tabs = st.tabs(
        [
            away,
            home,
        ]
    )

    for tab, side, team_name in [
        (
            tabs[0],
            "away",
            away,
        ),
        (
            tabs[1],
            "home",
            home,
        ),
    ]:
        with tab:
            team_box = box.get(
                side
            ) or {}

            batting = team_box.get(
                "batting"
            ) or []

            pitching = team_box.get(
                "pitching"
            ) or []

            if batting:
                st.markdown(
                    "#### Batting"
                )

                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Player": row.get(
                                    "name"
                                ),
                                "Pos": row.get(
                                    "pos"
                                ),
                                "AB": row.get(
                                    "ab"
                                ),
                                "R": row.get(
                                    "r"
                                ),
                                "H": row.get(
                                    "h"
                                ),
                                "RBI": row.get(
                                    "rbi"
                                ),
                                "BB": row.get(
                                    "bb"
                                ),
                                "SO": row.get(
                                    "so"
                                ),
                                "HR": row.get(
                                    "hr"
                                ),
                                "AVG": row.get(
                                    "avg"
                                ),
                            }
                            for row in batting
                            if isinstance(
                                row,
                                dict,
                            )
                        ]
                    ),
                    width="stretch",
                    hide_index=True,
                )

            if pitching:
                st.markdown(
                    "#### Pitching"
                )

                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Pitcher": row.get(
                                    "name"
                                ),
                                "IP": row.get(
                                    "ip"
                                ),
                                "H": row.get(
                                    "h"
                                ),
                                "R": row.get(
                                    "r"
                                ),
                                "ER": row.get(
                                    "er"
                                ),
                                "BB": row.get(
                                    "bb"
                                ),
                                "SO": row.get(
                                    "so"
                                ),
                                "HR": row.get(
                                    "hr"
                                ),
                                "Pitches": row.get(
                                    "pitches"
                                ),
                            }
                            for row in pitching
                            if isinstance(
                                row,
                                dict,
                            )
                        ]
                    ),
                    width="stretch",
                    hide_index=True,
                )

            if (
                not batting
                and not pitching
            ):
                st.caption(
                    team_name
                    + " box-score detail is not available yet."
                )

def render_mlb_games():
    page_intro(
        "MLB Games",
        "today",
        "MLB",
        (
            "Official live scores, postseason schedule "
            "and qualified game research."
        ),
    )

    favorites = favorite_teams_from_session()

    render_live_scores(
        "MLB",
        pinned_teams=favorites,
        title=(
            "My Games"
            if favorites
            else "Live & Today"
        ),
    )

    _render_mlb_box_scores()

    schedule = mlb_games_current()

    section_header(
        "Current Schedule",
        (
            "Official MLB schedule and probable-pitcher "
            "context when available."
        ),
    )

    if schedule.empty:
        st.info(
            "No current MLB schedule data is available."
        )
    else:
        d = schedule.copy()
        d["_start"] = pd.to_datetime(
            d["gameDate"],
            utc=True,
            errors="coerce",
        )
        d = d.sort_values("_start").head(15)

        for start in range(
            0,
            len(d),
            3,
        ):
            cols = st.columns(3)

            for col, (_, row) in zip(
                cols,
                d.iloc[
                    start:start + 3
                ].iterrows(),
            ):
                with col:
                    dt = row.get("_start")

                    when = (
                        dt.tz_convert(
                            "America/New_York"
                        ).strftime(
                            "%a %-I:%M %p ET"
                        )
                        if pd.notna(dt)
                        else safe(
                            row.get("status")
                        )
                    )

                    pitchers = (
                        safe(
                            row.get(
                                "away_probable_pitcher"
                            )
                        )
                        + " vs "
                        + safe(
                            row.get(
                                "home_probable_pitcher"
                            )
                        )
                    )

                    premium_card(
                        (
                            safe(
                                row.get("away_team")
                            )
                            + " @ "
                            + safe(
                                row.get("home_team")
                            )
                        ),
                        when,
                        safe(
                            row.get("status")
                        ),
                        pitchers,
                        [
                            (
                                safe(
                                    row.get(
                                        "seriesDescription"
                                    )
                                ),
                                "blue",
                            ),
                        ],
                        MLB_ACCENT,
                    )

    finalists = _sort_evidence(
        mlb_game_finalists()
    )

    section_header(
        "Qualified Game Research",
        (
            "Moneyline finalists only. Spread and total "
            "lanes remain research-only."
        ),
    )

    if finalists.empty:
        empty_card(
            "No Qualified MLB Game Research",
            (
                "Nothing currently passes all game-level "
                "qualification gates."
            ),
            MLB_ACCENT,
        )
        return

    for start in range(
        0,
        len(finalists),
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
                    (
                        safe(
                            row.get("away_team")
                        )
                        + " @ "
                        + safe(
                            row.get("home_team")
                        )
                    ),
                    friendly(
                        row.get(
                            "market_canonical"
                        )
                    ),
                    _game_pick(row),
                    (
                        safe(
                            row.get(
                                "sportsbook_count",
                                "0",
                            )
                        )
                        + " books · "
                        + safe(
                            row.get(
                                "provider_count",
                                "0",
                            )
                        )
                        + " providers"
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
                                row.get("decision")
                            ),
                            "green",
                        ),
                    ],
                    MLB_ACCENT,
                )


def render_mlb_picks():
    page_intro(
        "MLB Best Bets",
        "picks",
        "MLB",
        (
            "Qualified game bets with current sportsbook depth, "
            "probable-pitcher context and recent form."
        ),
    )

    data = mlb_game_finalists()

    st.caption(
        age_text(
            "/home/ubuntu/sports-hulk/"
            "mlb_live/decision/"
            "MLB_GAME_FINALISTS.csv"
        )
    )

    render_game_betting_board(
        data,
        sport="MLB",
        accent=MLB_ACCENT,
        title="MLB Best Bets",
        away_col="away_team",
        home_col="home_team",
        market_col="market_canonical",
        selection_col="selection_canonical",
        line_col="line",
        evidence_col="evidence_score",
        book_col="sportsbook_count",
        price_col="median_price_american",
        full_data=mlb_game_decisions(),
        full_title="Open full MLB game research",
    )

def render_mlb_props():
    page_intro(
        "MLB Player Props",
        "props",
        "MLB",
        (
            "Player lines compared with official MLB "
            "season and recent performance context."
        ),
    )

    data = _sort_evidence(
        mlb_prop_finalists()
    )

    if data.empty:
        st.info(
            "No qualified MLB player-prop research "
            "is available right now."
        )
        return

    for start in range(
        0,
        min(len(data), 24),
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
                        row.get("player")
                    ),
                    friendly(
                        row.get("metric")
                    ),
                    _player_pick(row),
                    (
                        "Recent "
                        + number(
                            row.get("recent_avg")
                        )
                        + " · Season "
                        + number(
                            row.get("season_avg")
                        )
                    ),
                    [
                        (
                            safe(
                                row.get(
                                    "sportsbook_count",
                                    "0",
                                )
                            )
                            + " books",
                            "blue",
                        ),
                        (
                            "Evidence "
                            + number(
                                row.get(
                                    "evidence_score"
                                )
                            ),
                            "green",
                        ),
                    ],
                    "#4F8CFF",
                )

    with st.expander(
        "Open full MLB prop research"
    ):
        st.dataframe(
            mlb_prop_decisions(),
            width="stretch",
            hide_index=True,
        )


def render_mlb_prizepicks():
    page_intro(
        "MLB PrizePicks",
        "prizepicks",
        "MLB",
        (
            "PrizePicks lines must match independent "
            "sportsbook lines before they can qualify."
        ),
    )

    data = _sort_evidence(
        mlb_pickem_finalists()
    )

    if data.empty:
        empty_card(
            "No Qualified MLB PrizePicks",
            (
                "No current projections satisfy the "
                "independent market-match requirements."
            ),
            "#C026D3",
        )
        return

    for start in range(
        0,
        len(data),
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
                        row.get("player")
                    ),
                    friendly(
                        row.get("metric")
                    ),
                    _player_pick(row),
                    (
                        "Recent "
                        + number(
                            row.get("recent_avg")
                        )
                        + " · Season "
                        + number(
                            row.get("season_avg")
                        )
                    ),
                    [
                        (
                            safe(
                                row.get(
                                    "sportsbook_count",
                                    "0",
                                )
                            )
                            + " matching books",
                            "green",
                        ),
                        (
                            "Evidence "
                            + number(
                                row.get(
                                    "evidence_score"
                                )
                            ),
                            "magenta",
                        ),
                    ],
                    "#C026D3",
                )

    st.caption(
        (
            "Sports HULK does not claim PrizePicks "
            "platform settlement outcomes."
        )
    )

    with st.expander(
        "Open all MLB PrizePicks research"
    ):
        st.dataframe(
            mlb_pickem_decisions(),
            width="stretch",
            hide_index=True,
        )


def render_mlb_fantasy():
    page_intro(
        "MLB Fantasy",
        "fantasy",
        "MLB",
        (
            "Current player opportunity and performance "
            "context without inventing a platform scoring system."
        ),
    )

    data = mlb_fantasy()

    if data.empty:
        st.info(
            "No current MLB fantasy context is available."
        )
        return

    for start in range(
        0,
        min(len(data), 24),
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
                        row.get("player")
                    ),
                    (
                        safe(
                            row.get("team")
                        )
                        + " · "
                        + safe(
                            row.get("position")
                        )
                    ),
                    (
                        "Context "
                        + number(
                            row.get("context_score")
                        )
                    ),
                    (
                        "Trend vs season "
                        + number(
                            row.get("trend_vs_season")
                        )
                    ),
                    [
                        (
                            safe(
                                row.get(
                                    "recent_games",
                                    "0",
                                )
                            )
                            + " recent games",
                            "orange",
                        ),
                        (
                            friendly(
                                row.get("group")
                            ),
                            "blue",
                        ),
                    ],
                    "#EA7C22",
                )

    st.caption(
        (
            "Context scores are Sports HULK research "
            "signals, not fantasy-platform point projections."
        )
    )


def render_mlb_parlays():
    page_intro(
        "MLB Parlays",
        "parlays",
        "MLB",
        (
            "Two-leg research combinations using already-"
            "qualified MLB game and player-prop legs."
        ),
    )

    data = _sort_evidence(
        mlb_parlays()
    )

    if data.empty:
        st.info(
            "No qualified MLB research combinations "
            "are available right now."
        )
        return

    for start in range(
        0,
        min(len(data), 15),
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
                leg1 = (
                    safe(
                        row.get("leg1_subject")
                    )
                    + " · "
                    + friendly(
                        row.get("leg1_market")
                    )
                    + " "
                    + safe(
                        row.get("leg1_selection")
                    )
                    + " "
                    + line_text(
                        row.get("leg1_line")
                    )
                )

                leg2 = (
                    safe(
                        row.get("leg2_subject")
                    )
                    + " · "
                    + friendly(
                        row.get("leg2_market")
                    )
                    + " "
                    + safe(
                        row.get("leg2_selection")
                    )
                    + " "
                    + line_text(
                        row.get("leg2_line")
                    )
                )

                premium_card(
                    "2-Leg Research",
                    safe(
                        row.get("status")
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
                        + " + "
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
            "Sportsbook payout is never inferred."
        )
    )


def render_mlb_feature(feature):
    routes = {
        "games": render_mlb_games,
        "picks": render_mlb_picks,
        "props": render_mlb_props,
        "prizepicks": render_mlb_prizepicks,
        "fantasy": render_mlb_fantasy,
        "parlays": render_mlb_parlays,
    }

    fn = routes.get(feature)

    if not fn:
        return False

    fn()
    return True
