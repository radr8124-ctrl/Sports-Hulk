from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

from premium_ui.live_scores import (
    fetch_nba_scores,
    fetch_nhl_scores,
    fetch_cfb_scores,
    fetch_cbb_scores,
)


ESPN_SUMMARY = {
    "NBA": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={event_id}",
    "CFB": "https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={event_id}",
    "CBB": "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/summary?event={event_id}",
}

FETCHERS = {
    "NBA": fetch_nba_scores,
    "NHL": fetch_nhl_scores,
    "CFB": fetch_cfb_scores,
    "CBB": fetch_cbb_scores,
}


def _safe(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value)


@st.cache_data(ttl=30, show_spinner=False)
def _get_json(url):
    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
        },
        timeout=12,
    )
    response.raise_for_status()
    return response.json()


def _game_label(game):
    away = _safe(game.get("away"))
    home = _safe(game.get("home"))
    away_score = game.get("away_score")
    home_score = game.get("home_score")
    status = _safe(game.get("status"))

    if away_score not in (None, "") and home_score not in (None, ""):
        return (
            f"{away} {away_score} · {home} {home_score}"
            + (f" · {status}" if status else "")
        )

    return (
        f"{away} @ {home}"
        + (f" · {status}" if status else "")
    )


def _active_games(sport):
    fetcher = FETCHERS.get(sport)
    if not fetcher:
        return []

    try:
        games = fetcher() or []
    except Exception:
        return []

    # Detailed boxes matter for live/final games first. If none exist,
    # keep scheduled games out of the detail selector.
    detailed = [
        game
        for game in games
        if game.get("event_id")
        and (
            bool(game.get("live"))
            or bool(game.get("final"))
            or str(game.get("state", "")).lower() in {"in", "post", "live", "final"}
        )
    ]

    return detailed


def _team_stat_rows(boxscore, sport):
    teams = (boxscore or {}).get("teams") or []
    rows = []

    preferred = {
        "NBA": {
            "FG", "FG%", "3PT", "3P%", "FT", "FT%",
            "REB", "AST", "STL", "BLK", "TO", "PIP",
        },
        "CBB": {
            "FG", "FG%", "3PT", "3P%", "FT", "FT%",
            "REB", "AST", "STL", "BLK", "TO",
        },
        "CFB": {
            "1st Downs", "3rd down efficiency", "4th down efficiency",
            "Total Yards", "Passing", "Rushing", "Turnovers",
            "Possession",
        },
    }

    wanted = preferred.get(sport, set())

    for item in teams:
        team = item.get("team") or {}
        row = {
            "Team": (
                team.get("displayName")
                or team.get("shortDisplayName")
                or team.get("abbreviation")
                or "Team"
            )
        }

        stats = item.get("statistics") or []
        fallback_count = 0

        for stat in stats:
            label = (
                stat.get("label")
                or stat.get("abbreviation")
                or stat.get("name")
            )
            if not label:
                continue

            if wanted:
                if label not in wanted and stat.get("abbreviation") not in wanted:
                    continue
            else:
                if fallback_count >= 12:
                    continue
                fallback_count += 1

            row[str(label)] = stat.get("displayValue")

        rows.append(row)

    return rows


def _render_espn_players(boxscore):
    player_teams = (boxscore or {}).get("players") or []

    if not player_teams:
        st.caption("Player box-score lines are not available yet.")
        return

    team_names = [
        (
            (item.get("team") or {}).get("displayName")
            or (item.get("team") or {}).get("shortDisplayName")
            or (item.get("team") or {}).get("abbreviation")
            or f"Team {i+1}"
        )
        for i, item in enumerate(player_teams)
    ]

    tabs = st.tabs(team_names)

    for tab, item in zip(tabs, player_teams):
        with tab:
            groups = item.get("statistics") or []

            any_group = False

            for group in groups:
                labels = group.get("labels") or []
                athletes = group.get("athletes") or []
                if not athletes:
                    continue

                rows = []
                for athlete_row in athletes:
                    athlete = athlete_row.get("athlete") or {}
                    stats = athlete_row.get("stats") or []

                    row = {
                        "Player": (
                            athlete.get("displayName")
                            or athlete.get("shortName")
                            or "Player"
                        ),
                        "Pos": (athlete.get("position") or {}).get("abbreviation"),
                        "Starter": bool(athlete_row.get("starter")),
                    }

                    for label, value in zip(labels, stats):
                        row[str(label)] = value

                    if athlete_row.get("didNotPlay"):
                        row["Status"] = (
                            athlete_row.get("reason")
                            or "DNP"
                        )

                    rows.append(row)

                if rows:
                    any_group = True
                    st.dataframe(
                        pd.DataFrame(rows),
                        width="stretch",
                        hide_index=True,
                    )

            if not any_group:
                st.caption("Player statistics are not available yet.")


def _render_espn_leaders(payload):
    leaders = payload.get("leaders") or []
    rows = []

    for team_block in leaders:
        team = team_block.get("team") or {}
        team_name = (
            team.get("displayName")
            or team.get("abbreviation")
            or "Team"
        )

        for category in team_block.get("leaders") or []:
            category_name = (
                category.get("displayName")
                or category.get("name")
                or "Leader"
            )

            for leader in category.get("leaders") or []:
                athlete = leader.get("athlete") or {}
                rows.append({
                    "Team": team_name,
                    "Category": category_name,
                    "Player": (
                        athlete.get("displayName")
                        or athlete.get("shortName")
                    ),
                    "Value": leader.get("displayValue"),
                    "Summary": leader.get("summary"),
                })

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            width="stretch",
            hide_index=True,
        )
    else:
        st.caption("Game leaders are not available yet.")


def _render_espn_scoring(payload):
    scoring = (
        payload.get("scoringPlays")
        or payload.get("scoringplays")
        or []
    )

    if not scoring:
        st.caption("Scoring-play detail is not available yet.")
        return

    rows = []

    for play in scoring:
        team = play.get("team") or {}
        clock = play.get("clock") or {}

        rows.append({
            "Period": play.get("period"),
            "Clock": clock.get("displayValue") if isinstance(clock, dict) else clock,
            "Team": (
                team.get("abbreviation")
                or team.get("displayName")
            ),
            "Play": (
                play.get("text")
                or play.get("type", {}).get("text")
            ),
            "Score": (
                play.get("awayScore")
                or play.get("homeScore")
                or ""
            ),
        })

    st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        hide_index=True,
    )


def _render_espn_box(sport, game):
    event_id = _safe(game.get("event_id"))
    url = ESPN_SUMMARY[sport].format(event_id=event_id)

    try:
        payload = _get_json(url)
    except Exception as exc:
        st.warning(
            "Detailed box score is temporarily unavailable: "
            + str(exc)
        )
        return

    boxscore = payload.get("boxscore") or {}
    team_rows = _team_stat_rows(boxscore, sport)

    tabs = st.tabs(
        [
            "Team Stats",
            "Players",
            "Leaders",
            "Scoring",
        ]
    )

    with tabs[0]:
        if team_rows:
            st.dataframe(
                pd.DataFrame(team_rows),
                width="stretch",
                hide_index=True,
            )
        else:
            st.caption("Team statistics are not available yet.")

    with tabs[1]:
        _render_espn_players(boxscore)

    with tabs[2]:
        _render_espn_leaders(payload)

    with tabs[3]:
        _render_espn_scoring(payload)


def _nhl_team_name(team):
    if not isinstance(team, dict):
        return "Team"

    place = team.get("placeName")
    if isinstance(place, dict):
        place = place.get("default")

    common = team.get("commonName")
    if isinstance(common, dict):
        common = common.get("default")

    text = " ".join(
        part
        for part in [
            _safe(place),
            _safe(common),
        ]
        if part
    ).strip()

    return (
        text
        or _safe(team.get("abbrev"))
        or "Team"
    )


def _render_nhl_box(game):
    event_id = _safe(game.get("event_id"))

    try:
        payload = _get_json(
            f"https://api-web.nhle.com/v1/gamecenter/{event_id}/boxscore"
        )
    except Exception as exc:
        st.warning(
            "Detailed NHL box score is temporarily unavailable: "
            + str(exc)
        )
        return

    away_team = payload.get("awayTeam") or {}
    home_team = payload.get("homeTeam") or {}
    away_name = _nhl_team_name(away_team)
    home_name = _nhl_team_name(home_team)

    summary_rows = [
        {
            "Team": away_name,
            "Score": away_team.get("score"),
            "Shots": away_team.get("sog"),
        },
        {
            "Team": home_name,
            "Score": home_team.get("score"),
            "Shots": home_team.get("sog"),
        },
    ]

    st.dataframe(
        pd.DataFrame(summary_rows),
        width="stretch",
        hide_index=True,
    )

    player_stats = payload.get("playerByGameStats") or {}
    tabs = st.tabs([away_name, home_name])

    for tab, side in zip(tabs, ["awayTeam", "homeTeam"]):
        with tab:
            side_data = player_stats.get(side) or {}

            skaters = []
            for group_name in ["forwards", "defense"]:
                for row in side_data.get(group_name) or []:
                    name = row.get("name")
                    if isinstance(name, dict):
                        name = name.get("default")

                    skaters.append({
                        "Player": name,
                        "Pos": row.get("position"),
                        "G": row.get("goals"),
                        "A": row.get("assists"),
                        "PTS": row.get("points"),
                        "+/-": row.get("plusMinus"),
                        "SOG": row.get("sog"),
                        "Hits": row.get("hits"),
                        "Blocks": row.get("blockedShots"),
                        "PIM": row.get("pim"),
                        "TOI": row.get("toi"),
                    })

            if skaters:
                st.markdown("#### Skaters")
                st.dataframe(
                    pd.DataFrame(skaters),
                    width="stretch",
                    hide_index=True,
                )

            goalies = []
            for row in side_data.get("goalies") or []:
                name = row.get("name")
                if isinstance(name, dict):
                    name = name.get("default")

                goalies.append({
                    "Goalie": name,
                    "Starter": bool(row.get("starter")),
                    "Decision": row.get("decision"),
                    "Saves": row.get("saves"),
                    "Shots": row.get("shotsAgainst"),
                    "GA": row.get("goalsAgainst"),
                    "SV%": row.get("savePctg"),
                    "TOI": row.get("toi"),
                })

            if goalies:
                st.markdown("#### Goalies")
                st.dataframe(
                    pd.DataFrame(goalies),
                    width="stretch",
                    hide_index=True,
                )

            if not skaters and not goalies:
                st.caption("Player statistics are not available yet.")


def render_extended_box_scores(sport):
    sport = str(sport).upper()

    if sport not in FETCHERS:
        return

    games = _active_games(sport)

    if not games:
        st.caption(
            "Detailed box scores will appear here when a game is live or final."
        )
        return

    st.markdown("### Box Score")
    st.caption(
        "Choose a live or completed game for team and player detail."
    )

    labels = [_game_label(game) for game in games]
    lookup = {
        label: game
        for label, game in zip(labels, games)
    }

    selected_label = st.selectbox(
        f"{sport} box score game",
        labels,
        index=0,
        label_visibility="collapsed",
        key=f"{sport.lower()}_box_score_game",
    )

    game = lookup[selected_label]

    if sport == "NHL":
        _render_nhl_box(game)
    else:
        _render_espn_box(sport, game)
