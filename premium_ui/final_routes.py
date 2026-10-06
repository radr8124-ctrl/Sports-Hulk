import pandas as pd
import streamlit as st

from premium_ui.live_scores import (
    favorite_teams_from_session,
    render_live_scores,
)

from premium_ui.data import (
    nfl_games,
    nfl_score_snapshot,
)

from premium_ui.pages import (
    empty_card,
    friendly,
    line_text,
    number,
    page_intro,
    premium_card,
    render_fantasy,
    render_dfs,
    render_news,
    render_parlays,
    render_picks,
    render_props,
    render_prizepicks,
    render_survivor,
    safe,
    section_header,
)

from premium_ui.sport_config import (
    SPORTS,
)


FEATURE_LABELS = {
    "games":
        "Games",

    "picks":
        "Picks",

    "props":
        "Props",

    "prizepicks":
        "PrizePicks",

    "fantasy":
        "Fantasy",

    "dfs":
        "DFS",

    "parlays":
        "Parlays",

    "survivor":
        "Survivor",

    "news":
        "News",

    "rankings":
        "Rankings",

    "research":
        "Research",
}


def _render_nfl_box_scores():
    payload = nfl_score_snapshot()

    if not isinstance(
        payload,
        dict,
    ):
        return

    games = (
        payload.get(
            "games"
        )
        or []
    )

    detailed = [
        game
        for game
        in games
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
            "Detailed NFL box scores will appear here when live/final game data is available."
        )
        return

    section_header(
        "Box Score",
        (
            "Choose one live or completed game for team stats, "
            "player lines, scoring plays and leaders."
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
        "NFL box score game",
        labels,
        index=0,
        label_visibility="collapsed",
        key="nfl_box_score_game",
    )

    game = lookup[
        selected_label
    ]
    box = game.get(
        "boxscore"
    ) or {}

    tabs = st.tabs(
        [
            "Team Stats",
            "Players",
            "Scoring",
        ]
    )

    with tabs[0]:
        team_stats = box.get(
            "team_stats"
        ) or {}

        rows = []

        for team, stats in team_stats.items():
            if not isinstance(
                stats,
                dict,
            ):
                continue

            rows.append({
                "Team": team,
                "1st Downs": stats.get(
                    "firstDowns"
                ),
                "3rd Down": stats.get(
                    "thirdDownEff"
                ),
                "Total Yards": stats.get(
                    "totalYards"
                ),
                "Pass Yards": stats.get(
                    "netPassingYards"
                ),
                "Rush Yards": stats.get(
                    "rushingYards"
                ),
                "Sacks/Yards": stats.get(
                    "sacksYardsLost"
                ),
                "Turnovers": stats.get(
                    "turnovers"
                ),
                "Possession": stats.get(
                    "possessionTime"
                ),
            })

        if rows:
            st.dataframe(
                pd.DataFrame(
                    rows
                ),
                width="stretch",
                hide_index=True,
            )
        else:
            st.caption(
                "Team statistics are not available yet."
            )

    with tabs[1]:
        players = box.get(
            "players"
        ) or {}

        any_players = False

        for category in [
            "passing",
            "rushing",
            "receiving",
        ]:
            player_rows = []

            for team, team_data in players.items():
                if not isinstance(
                    team_data,
                    dict,
                ):
                    continue

                for item in (
                    team_data.get(
                        category
                    )
                    or []
                ):
                    if not isinstance(
                        item,
                        dict,
                    ):
                        continue

                    row = {
                        "Team": team,
                        "Player": item.get(
                            "name"
                        ),
                    }

                    stats = item.get(
                        "stats"
                    ) or {}

                    if isinstance(
                        stats,
                        dict,
                    ):
                        row.update(
                            stats
                        )

                    player_rows.append(
                        row
                    )

            if player_rows:
                any_players = True

                st.markdown(
                    (
                        "#### "
                        + category.title()
                    )
                )

                st.dataframe(
                    pd.DataFrame(
                        player_rows
                    ),
                    width="stretch",
                    hide_index=True,
                )

        if not any_players:
            st.caption(
                "Player box-score lines are not available yet."
            )

    with tabs[2]:
        scoring = box.get(
            "scoring_plays"
        ) or []

        if scoring:
            scoring_rows = []

            for play in scoring:
                if not isinstance(
                    play,
                    dict,
                ):
                    continue

                scoring_rows.append({
                    "Qtr": play.get(
                        "period"
                    ),
                    "Clock": play.get(
                        "clock"
                    ),
                    "Team": play.get(
                        "team"
                    ),
                    "Play": play.get(
                        "text"
                    ),
                    "Score": (
                        str(
                            play.get(
                                "away_score",
                                "—",
                            )
                        )
                        + "-"
                        + str(
                            play.get(
                                "home_score",
                                "—",
                            )
                        )
                    ),
                })

            st.markdown(
                "#### Scoring Plays"
            )

            st.dataframe(
                pd.DataFrame(
                    scoring_rows
                ),
                width="stretch",
                hide_index=True,
            )

        leaders = box.get(
            "leaders"
        ) or []

        if leaders:
            leader_rows = [
                {
                    "Team": row.get(
                        "team"
                    ),
                    "Category": row.get(
                        "category"
                    ),
                    "Player": row.get(
                        "player"
                    ),
                    "Value": row.get(
                        "value"
                    ),
                }
                for row in leaders
                if isinstance(
                    row,
                    dict,
                )
            ]

            if leader_rows:
                st.markdown(
                    "#### Leaders"
                )

                st.dataframe(
                    pd.DataFrame(
                        leader_rows
                    ),
                    width="stretch",
                    hide_index=True,
                )

        if (
            not scoring
            and not leaders
        ):
            st.caption(
                "Scoring detail is not available yet."
            )

def render_games(
    sport,
):
    page_intro(
        f"{sport} Games",
        "today",
        sport,
        (
            "Today's matchups and the information "
            "that matters most."
        ),
    )

    if sport in {
        "NFL",
        "MLB",
    }:

        favorites = (
            favorite_teams_from_session()
        )

        render_live_scores(
            sport,
            pinned_teams=favorites,
            title=(
                "My Games"
                if favorites
                else "Live & Upcoming"
            ),
        )

        if sport == "NFL":
            _render_nfl_box_scores()


    if sport == "MLB":

        empty_card(
            "MLB Research",
            (
                "Live scoring is active. "
                "The upgraded MLB research engine "
                "will connect directly below."
            ),
            SPORTS[
                sport
            ][
                "accent"
            ],
        )

        return


    if sport != "NFL":

        empty_card(
            f"{sport} Games",
            (
                "The premium scoreboard layout "
                "is prepared for this sport."
            ),
            SPORTS[
                sport
            ][
                "accent"
            ],
        )

        return


    games = nfl_games()

    if games.empty:

        st.info(
            "No current NFL game research "
            "is available."
        )

        return


    if (
        "hulk_market_score"
        in games.columns
    ):
        games = games.copy()

        games[
            "_score"
        ] = pd.to_numeric(
            games[
                "hulk_market_score"
            ],
            errors="coerce",
        )

        games = games.sort_values(
            "_score",
            ascending=False,
        )


    section_header(
        "Today's Games",
        (
            "Tap into Picks for deeper "
            "game-level analysis."
        ),
    )


    for start in range(
        0,
        min(
            len(games),
            15,
        ),
        3,
    ):

        cols = st.columns(3)

        for col, (_, row) in zip(
            cols,
            games.iloc[
                start:start + 3
            ].iterrows(),
        ):

            with col:

                premium_card(
                    safe(
                        row.get(
                            "game_key",
                            "NFL Game",
                        )
                    ),
                    friendly(
                        row.get(
                            "market"
                        )
                    ),
                    (
                        safe(
                            row.get(
                                "selection"
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
                        "Current multi-source "
                        "game research."
                    ),
                    [
                        (
                            "Evidence "
                            + number(
                                row.get(
                                    "hulk_market_score"
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
                    SPORTS[
                        sport
                    ][
                        "accent"
                    ],
                )


def render_rankings(
    sport,
):
    page_intro(
        f"{sport} Rankings",
        "college",
        sport,
        (
            "Rankings and team context in "
            "a simple, readable view."
        ),
    )

    empty_card(
        "Rankings",
        (
            "The rankings presentation layer "
            "is ready for the verified college "
            "data connection."
        ),
        SPORTS[
            sport
        ][
            "accent"
        ],
    )


def render_research(
    sport,
):
    page_intro(
        f"{sport} Research",
        (
            "college"
            if sport in {
                "CFB",
                "CBB",
            }
            else "picks"
        ),
        sport,
        (
            "Deeper numbers live here so "
            "the main pages stay clean."
        ),
    )

    empty_card(
        "Deep Research",
        (
            "Advanced data belongs here rather "
            "than cluttering the everyday experience."
        ),
        SPORTS[
            sport
        ][
            "accent"
        ],
    )


def render_feature(
    sport,
    feature,
):

    # NBA_REAL_ROUTE_BUILD_6
    if sport == "NBA":

        from premium_ui.nba_ui import (
            render_nba_feature,
        )

        if render_nba_feature(
            feature
        ):
            return


    # NHL_REAL_ROUTE_BUILD_6
    if sport == "NHL":

        from premium_ui.nhl_ui import (
            render_nhl_feature,
        )

        if render_nhl_feature(
            feature
        ):
            return


    # CBB_REAL_ROUTE_BUILD_5
    if sport == "CBB":

        from premium_ui.cbb_ui import (
            render_cbb_feature,
        )

        if render_cbb_feature(
            feature
        ):
            return


    # CFB_REAL_ROUTE_BUILD_5
    if sport == "CFB":

        from premium_ui.cfb_ui import (
            render_cfb_feature,
        )

        if render_cfb_feature(
            feature
        ):
            return


    # MLB_REAL_ROUTE_BUILD_V2
    if sport == "MLB":

        from premium_ui.mlb_ui import (
            render_mlb_feature,
        )

        if render_mlb_feature(
            feature
        ):
            return


    if feature == "games":
        render_games(
            sport
        )
        return

    if feature == "picks":
        render_picks(
            sport
        )
        return

    if feature == "props":
        render_props(
            sport
        )
        return

    if feature == "prizepicks":
        render_prizepicks(
            sport
        )
        return

    if feature == "fantasy":
        render_fantasy(
            sport
        )
        return

    if feature == "dfs":
        render_dfs(
            sport
        )
        return

    if feature == "parlays":
        render_parlays(
            sport
        )
        return

    if feature == "survivor":

        if sport == "NFL":
            render_survivor()

        return

    if feature == "news":
        render_news(
            sport
        )
        return

    if feature == "rankings":
        render_rankings(
            sport
        )
        return

    if feature == "research":
        render_research(
            sport
        )
        return


def feature_options(
    sport,
):
    return [
        (
            FEATURE_LABELS[
                feature
            ],
            feature,
        )
        for feature in (
            SPORTS[
                sport
            ][
                "features"
            ]
        )
    ]
