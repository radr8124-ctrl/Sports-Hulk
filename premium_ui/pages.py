from html import escape
from textwrap import dedent
import hashlib
import json

import pandas as pd
import streamlit as st

from premium_ui.html_render import html

from premium_ui.live_scores import (
    favorite_teams_from_session,
    render_live_scores,
    render_survivor_live_entries,
)

from premium_ui.components import (
    brand_header,
    explanation_box,
    hero,
    section_header,
    render_html,
)
from premium_ui.data import (
    age_text,
    nfl_fantasy,
    nfl_games,
    nfl_parlays,
    nfl_pickem,
    nfl_props,
    nfl_score_snapshot,
    sports_article_drafts,
    sports_news_current,
    survivor_entries,
    survivor_field,
    survivor_pairs,
    survivor_pick2,
    survivor_strategy,
    survivor_summary,
    survivor_pool_current,
    survivor_pool_ownership,
)
from premium_ui.sport_config import (
    PAGE_EXPLAINERS,
    SPORTS,
)
from premium_ui.survivor_editor import (
    NFL_TEAMS,
    create_entry as create_survivor_entry,
    save_entry as save_survivor_entry,
)
from nfl_live.survivor_pool_upload import (
    parse_upload as parse_survivor_pool_upload,
    commit_preview as commit_survivor_pool_upload,
)


# ============================================================
# PLAIN-ENGLISH PRESENTATION
# ============================================================

DECISIONS = {
    "STRONG_RESEARCH":
        "Strong Research",

    "QUALIFIED_RESEARCH":
        "Qualified",

    "HIGH_JUICE_SAFETY":
        "Market Favorite",

    "MARKET_LEAN":
        "Market Lean",

    "INJURY_REVIEW":
        "Check Injury",

    "WATCH":
        "Watch",

    "PASS":
        "Pass",
}


def friendly(value):
    value = str(value or "").strip()

    return DECISIONS.get(
        value,
        value.replace(
            "_",
            " ",
        ).title(),
    )


def number(value, digits=1):
    x = pd.to_numeric(
        value,
        errors="coerce",
    )

    if pd.isna(x):
        return "—"

    return (
        f"{float(x):.{digits}f}"
    )


def line_text(value):
    x = pd.to_numeric(
        value,
        errors="coerce",
    )

    if pd.isna(x):
        return "—"

    return f"{x:g}"


def safe(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value)


# ============================================================
# VISUAL COMPONENTS
# ============================================================

SEMANTIC_COLORS = {
    "picks": "#2563EB",
    "props": "#7C3AED",
    "prizepicks": "#C026D3",
    "parlays": "#0F9F9A",
    "fantasy": "#EA7C22",
    "survivor": "#059669",
    "news": "#4F46E5",

    "live": "#E84A5F",
    "win": "#059669",
    "loss": "#DC3545",
    "watch": "#D97706",

    "over": "#2563EB",
    "under": "#7C3AED",

    "neutral": "#64748B",
}


def _semantic_rgba(
    hex_color,
    alpha,
):
    value = str(
        hex_color
    ).lstrip("#")

    if len(value) != 6:
        return (
            f"rgba(37,99,235,{alpha})"
        )

    r = int(value[0:2], 16)
    g = int(value[2:4], 16)
    b = int(value[4:6], 16)

    return (
        f"rgba({r},{g},{b},{alpha})"
    )


def semantic_accent(
    text,
    fallback="#2563EB",
):
    value = str(
        text or ""
    ).upper()

    if (
        "PRIZEPICKS" in value
        or "PICK'EM" in value
    ):
        return SEMANTIC_COLORS[
            "prizepicks"
        ]

    if "PARLAY" in value:
        return SEMANTIC_COLORS[
            "parlays"
        ]

    if "FANTASY" in value:
        return SEMANTIC_COLORS[
            "fantasy"
        ]

    if "SURVIVOR" in value:
        return SEMANTIC_COLORS[
            "survivor"
        ]

    if "NEWS" in value:
        return SEMANTIC_COLORS[
            "news"
        ]

    if "INJURY" in value:
        return SEMANTIC_COLORS[
            "loss"
        ]

    if "LOSS" in value:
        return SEMANTIC_COLORS[
            "loss"
        ]

    if "LIVE" in value:
        return SEMANTIC_COLORS[
            "live"
        ]

    if "OVER" in value:
        return SEMANTIC_COLORS[
            "over"
        ]

    if "UNDER" in value:
        return SEMANTIC_COLORS[
            "under"
        ]

    if "PROP" in value:
        return SEMANTIC_COLORS[
            "props"
        ]

    if "PICK" in value:
        return SEMANTIC_COLORS[
            "picks"
        ]

    return fallback


def evidence_tone(
    label,
):
    value = str(label or "")

    if "EVIDENCE" not in value.upper():
        return None

    score = None

    for token in (
        value
        .replace("%", "")
        .replace(":", " ")
        .split()
    ):
        try:
            score = float(token)
        except Exception:
            continue

    if score is None:
        return "blue"

    # Visual presentation only.
    # These are not probabilities and do not
    # alter Sports HULK decision thresholds.
    if score >= 80:
        return "green"

    if score >= 70:
        return "blue"

    if score >= 60:
        return "amber"

    return "gray"


def automatic_chip_tone(
    label,
    requested="blue",
):
    value = str(
        label or ""
    ).upper()

    evidence = evidence_tone(
        label
    )

    if evidence:
        return evidence

    if (
        "QUALIFIED" in value
        or "STRONG RESEARCH" in value
        or "WIN" == value.strip()
        or "ADVANCED" in value
        or "CLEAR" in value
    ):
        return "green"

    if (
        "LOSS" in value
        or "INJURY" in value
        or "ENTRY OUT" in value
        or "PROBLEM" in value
    ):
        return "red"

    if (
        "WATCH" in value
        or "CAUTION" in value
        or "VERIFY" in value
    ):
        return "amber"

    if (
        "PRIZEPICKS" in value
        or "PICK'EM" in value
    ):
        return "magenta"

    if "PARLAY" in value:
        return "teal"

    if "FANTASY" in value:
        return "orange"

    if "NEWS" in value:
        return "indigo"

    if "LIVE" == value.strip():
        return "red"

    if "OVER" == value.strip():
        return "blue"

    if "UNDER" == value.strip():
        return "purple"

    if "PASS" == value.strip():
        return "gray"

    return requested


def status_chip(
    text,
    tone="blue",
):
    tone = automatic_chip_tone(
        text,
        tone,
    )

    colors = {
        "blue": (
            "#1E40AF",
            "#DBEAFE",
            "#93C5FD",
        ),

        "green": (
            "#047857",
            "#D1FAE5",
            "#6EE7B7",
        ),

        "amber": (
            "#92400E",
            "#FEF3C7",
            "#FCD34D",
        ),

        "purple": (
            "#6D28D9",
            "#EDE9FE",
            "#C4B5FD",
        ),

        "red": (
            "#B91C1C",
            "#FEE2E2",
            "#FCA5A5",
        ),

        "teal": (
            "#0F766E",
            "#CCFBF1",
            "#5EEAD4",
        ),

        "magenta": (
            "#A21CAF",
            "#FAE8FF",
            "#F0ABFC",
        ),

        "orange": (
            "#C2410C",
            "#FFEDD5",
            "#FDBA74",
        ),

        "indigo": (
            "#4338CA",
            "#E0E7FF",
            "#A5B4FC",
        ),

        "gray": (
            "#475569",
            "#F1F5F9",
            "#CBD5E1",
        ),
    }

    fg, bg, border = colors.get(
        tone,
        colors["blue"],
    )

    return f"""
    <span style="
        display:inline-flex;
        align-items:center;
        justify-content:center;

        padding:4px 8px;
        margin:2px 5px 2px 0;

        border-radius:999px;

        color:{fg};
        background:{bg};
        border:1px solid {border};

        font-size:11.5px;
        font-weight:820;
        line-height:1;

        white-space:nowrap;

        box-shadow:
            0 1px 0 rgba(16,24,40,.03);
    ">
        {escape(str(text))}
    </span>
    """


def premium_card(
    eyebrow,
    title,
    headline="",
    body="",
    chips=None,
    accent="#2563EB",
):
    chips = chips or []

    combined = (
        str(eyebrow)
        + " "
        + str(title)
        + " "
        + str(headline)
    )

    semantic = semantic_accent(
        combined,
        accent,
    )

    # If the content itself has a semantic meaning,
    # let that color win over the generic page accent.
    semantic_upper = combined.upper()

    semantic_override = any(
        keyword in semantic_upper
        for keyword in [
            "OVER",
            "UNDER",
            "PRIZEPICKS",
            "PICK'EM",
            "PARLAY",
            "FANTASY",
            "SURVIVOR",
            "NEWS",
        ]
    )

    if semantic_override:
        accent = semantic

    headline_color = (
        accent
        if semantic_override
        else "#101828"
    )

    card_tint = _semantic_rgba(
        accent,
        .085,
    )

    card_border = _semantic_rgba(
        accent,
        .30,
    )

    accent_shadow = _semantic_rgba(
        accent,
        .12,
    )

    chip_html = "".join(
        status_chip(
            label,
            tone,
        )
        for label, tone in chips
    )

    html(
        f"""
        <div style="
            position:relative;
            overflow:hidden;

            min-height:148px;

            padding:
                15px 16px 14px 19px;

            margin-bottom:
                10px;

            border-radius:
                15px;

            border:
                1px solid {card_border};

            background:
                linear-gradient(
                    135deg,
                    {card_tint} 0%,
                    #FFFFFF 45%,
                    #FFFFFF 100%
                );

            box-shadow:
                0 5px 16px rgba(31,48,74,.07);
        ">

            <div style="
                position:absolute;
                left:0;
                top:0;
                bottom:0;

                width:5px;

                background:
                    linear-gradient(
                        180deg,
                        {accent},
                        {accent}
                    );

                box-shadow:
                    2px 0 10px
                    {accent_shadow};
            "></div>


            <div style="
                color:#142033;

                font-size:17px;
                font-weight:820;

                line-height:1.18;

                letter-spacing:-.012em;

                margin-bottom:4px;
            ">
                {escape(safe(eyebrow))}
            </div>


            <div style="
                color:#52647B;

                font-size:13.5px;
                font-weight:670;

                line-height:1.3;

                margin-bottom:5px;
            ">
                {escape(safe(title))}
            </div>


            <div style="
                color:{headline_color};

                font-size:22px;
                font-weight:860;

                letter-spacing:-.025em;

                margin-top:1px;

                line-height:1.1;
            ">
                {escape(safe(headline))}
            </div>


            <div style="
                color:#536A84;

                font-size:13.5px;
                font-weight:590;

                line-height:1.42;

                margin-top:7px;
                margin-bottom:8px;
            ">
                {escape(safe(body))}
            </div>


            <div>
                {chip_html}
            </div>

        </div>
        """
    )


def empty_card(
    title,
    body,
    accent="#4F8CFF",
):
    premium_card(
        "Prepared",
        title,
        "Ready for data",
        body,
        [
            (
                "No fake information",
                "green",
            ),
        ],
        accent,
    )


def page_intro(
    title,
    page_key,
    sport="ALL",
    subtitle="",
):
    if not st.session_state.get(
        "_premium_shell_brand_rendered",
        False,
    ):
        brand_header(
            live=True,
        )


    page_colors = {
        "today": (
            "#06B6D4",
            "#2563EB",
        ),

        "picks": (
            "#2563EB",
            "#60A5FA",
        ),

        "props": (
            "#7C3AED",
            "#A78BFA",
        ),

        "prizepicks": (
            "#C026D3",
            "#E879F9",
        ),

        "fantasy": (
            "#EA7C22",
            "#FDBA74",
        ),

        "parlays": (
            "#0F9F9A",
            "#5EEAD4",
        ),

        "survivor": (
            "#059669",
            "#6EE7B7",
        ),

        "news": (
            "#4F46E5",
            "#818CF8",
        ),

        "college": (
            "#B45309",
            "#F59E0B",
        ),
    }


    color_a, color_b = (
        page_colors.get(
            page_key,
            (
                "#2563EB",
                "#06B6D4",
            ),
        )
    )


    soft = _semantic_rgba(
        color_a,
        .105,
    )

    border = _semantic_rgba(
        color_a,
        .30,
    )


    kicker = (
        sport
        if sport != "ALL"
        else "Sports Intelligence"
    )


    html(
        f"""
        <div style="
            position:relative;
            overflow:hidden;

            margin:2px 0 8px 0;

            border-radius:0;

            border:none;

            background:transparent;

            box-shadow:none;
        ">

            <div style="
                height:3px;
                width:52px;

                border-radius:999px;

                background:
                    linear-gradient(
                        90deg,
                        {color_a},
                        {color_b}
                    );
            "></div>


            <div style="
                padding:
                    8px 0 9px 0;
            ">

                <div style="
                    color:#102A43;

                    font-size:
                        clamp(
                            25px,
                            2.8vw,
                            32px
                        );

                    font-weight:
                        880;

                    letter-spacing:
                        -.035em;

                    line-height:
                        1.08;
                ">
                    {escape(str(title))}
                </div>


                <div style="
                    max-width:
                        850px;

                    margin-top:
                        5px;

                    color:#435A73;

                    font-size:
                        14.5px;

                    font-weight:
                        620;

                    line-height:
                        1.42;
                ">
                    {escape(str(subtitle))}
                </div>

            </div>

        </div>
        """
    )


    # Keep the page shell compact. Page-specific context belongs
    # in the subtitle or the first decision section, not a second explainer box.


def sport_selector(
    key,
    default="NFL",
):
    sports = [
        "NFL",
        "MLB",
        "CFB",
        "NBA",
        "CBB",
        "NHL",
    ]

    try:
        index = sports.index(
            default
        )
    except ValueError:
        index = 0

    return st.pills(
        "Sport",
        sports,
        default=(
            sports[
                index
            ]
        ),
        required=True,
        label_visibility="collapsed",
        key=key,
    )


def metric_row(items):
    cols = st.columns(
        len(items)
    )

    for col, item in zip(
        cols,
        items,
    ):
        label, value = item

        with col:
            st.metric(
                label,
                value,
            )


# ============================================================
# TODAY
# ============================================================

def render_today(sport_override=None):
    page_intro(
        (
            "Today"
            if not sport_override
            else sport_override + " Overview"
        ),
        "today",
        (
            sport_override
            if sport_override
            else "ALL"
        ),
        subtitle=(
            "Scores, strongest decisions and the updates "
            "that can actually change what you do."
        ),
    )

    sport = (
        sport_override
        if sport_override
        else sport_selector(
            "premium_today_sport",
            "NFL",
        )
    )

    favorites = favorite_teams_from_session()

    render_live_scores(
        sport,
        pinned_teams=favorites,
        title=(
            "My Games"
            if favorites
            else "Live & Upcoming"
        ),
        limit=9,
    )

    def _read_today_csv(path):
        try:
            return pd.read_csv(
                path,
                low_memory=False,
            )
        except Exception:
            return pd.DataFrame()

    def _first(row, names, default=None):
        for name in names:
            value = row.get(name)
            if value is None:
                continue
            try:
                if pd.isna(value):
                    continue
            except Exception:
                pass
            if str(value).strip():
                return value
        return default

    def _decision_tier(score):
        value = pd.to_numeric(
            score,
            errors="coerce",
        )
        if pd.isna(value):
            return "Research"
        if value >= 90:
            return "Strong evidence"
        if value >= 80:
            return "Good evidence"
        if value >= 70:
            return "Worth a look"
        return "Watch"

    def _matchup(row):
        away = _first(
            row,
            [
                "away_team_name",
                "away_team_canonical",
                "away_team",
            ],
            "",
        )
        home = _first(
            row,
            [
                "home_team_name",
                "home_team_canonical",
                "home_team",
            ],
            "",
        )
        if away and home:
            return (
                safe(away)
                + " @ "
                + safe(home)
            )
        return safe(
            row.get(
                "game_key",
                "Game",
            )
        )

    def _game_reason(row, selected_sport):
        books = pd.to_numeric(
            _first(
                row,
                [
                    "sportsbook_count",
                    "approved_book_count",
                    "sw_books",
                ],
            ),
            errors="coerce",
        )

        pieces = []

        if pd.notna(books):
            pieces.append(
                f"{int(books)} books"
            )

        agreement = safe(
            _first(
                row,
                [
                    "provider_agreement",
                    "context_direction",
                    "context_status",
                ],
                "",
            )
        )

        if agreement:
            pretty = friendly(
                agreement
            )
            if pretty not in {
                "Research Ready",
            }:
                pieces.append(
                    pretty
                )

        if selected_sport == "NFL":
            spread_move = pd.to_numeric(
                row.get(
                    "home_spread_move"
                ),
                errors="coerce",
            )
            total_move = pd.to_numeric(
                row.get(
                    "total_move"
                ),
                errors="coerce",
            )
            if pd.notna(spread_move) and spread_move != 0:
                pieces.append(
                    "spread moved "
                    + line_text(
                        spread_move
                    )
                )
            elif pd.notna(total_move) and total_move != 0:
                pieces.append(
                    "total moved "
                    + line_text(
                        total_move
                    )
                )

        elif selected_sport == "MLB":
            form_edge = pd.to_numeric(
                row.get(
                    "form_edge"
                ),
                errors="coerce",
            )
            if pd.notna(form_edge):
                pieces.append(
                    "recent-form edge "
                    + number(
                        form_edge
                    )
                )

        elif selected_sport == "CFB":
            margin_edge = pd.to_numeric(
                row.get(
                    "current_margin_edge"
                ),
                errors="coerce",
            )
            if pd.notna(margin_edge):
                pieces.append(
                    "current margin edge "
                    + number(
                        margin_edge
                    )
                )

        elif selected_sport in {
            "NBA",
            "NHL",
        }:
            context_value = pd.to_numeric(
                row.get(
                    "historical_context_value"
                ),
                errors="coerce",
            )
            if pd.notna(context_value):
                pieces.append(
                    "context edge "
                    + number(
                        context_value
                    )
                )

        return (
            " · ".join(
                pieces[:3]
            )
            if pieces
            else "Current market and matchup research."
        )

    if sport == "NFL":
        decisions = nfl_games().copy()
    else:
        decision_path = (
            "/home/ubuntu/sports-hulk/"
            + sport.lower()
            + "_live/decision/"
            + sport
            + "_GAME_DECISIONS.csv"
        )
        decisions = _read_today_csv(
            decision_path
        )

    if not decisions.empty:
        decisions = decisions.copy()

        score_col = (
            "hulk_market_score"
            if "hulk_market_score"
            in decisions.columns
            else "evidence_score"
        )

        decisions["_score"] = pd.to_numeric(
            decisions.get(
                score_col
            ),
            errors="coerce",
        )

        start_col = next(
            (
                col
                for col in [
                    "start",
                    "start_dt",
                ]
                if col in decisions.columns
            ),
            None,
        )

        if start_col:
            decisions["_start"] = pd.to_datetime(
                decisions[
                    start_col
                ],
                utc=True,
                errors="coerce",
            )
            now = pd.Timestamp.now(
                tz="UTC"
            )
            future = decisions[
                decisions["_start"].isna()
                | (
                    decisions["_start"]
                    >= now
                    - pd.Timedelta(
                        hours=4
                    )
                )
            ].copy()
            if not future.empty:
                decisions = future

            decisions["_hours"] = (
                decisions["_start"]
                - now
            ).dt.total_seconds() / 3600

            decisions["_soon"] = (
                decisions["_hours"]
                .fillna(9999)
                .clip(lower=0)
            )

            decisions = decisions.sort_values(
                [
                    "_soon",
                    "_score",
                ],
                ascending=[
                    True,
                    False,
                ],
            )
        else:
            decisions = decisions.sort_values(
                "_score",
                ascending=False,
            )

        if "game_key" in decisions.columns:
            decisions = decisions.drop_duplicates(
                "game_key",
                keep="first",
            )

        best_games = decisions.head(
            3
        )
    else:
        best_games = pd.DataFrame()

    section_header(
        "Best Right Now",
        (
            "Three unique game decisions. "
            "No duplicate markets from the same matchup."
        ),
    )

    if best_games.empty:
        st.info(
            (
                "No current "
                + sport
                + " game decision is ready yet."
            )
        )
    else:
        cols = st.columns(
            min(
                3,
                len(best_games),
            )
        )

        for col, (_, row) in zip(
            cols,
            best_games.iterrows(),
        ):
            with col:
                market = friendly(
                    _first(
                        row,
                        [
                            "market",
                            "market_canonical",
                        ],
                        "Game",
                    )
                )
                selection = safe(
                    _first(
                        row,
                        [
                            "selection",
                            "selection_canonical",
                        ],
                        "",
                    )
                )
                line = _first(
                    row,
                    [
                        "line",
                        "line_group",
                    ],
                )
                pick_text = selection

                if (
                    line is not None
                    and line_text(
                        line
                    )
                    != "—"
                ):
                    pick_text = (
                        pick_text
                        + " "
                        + line_text(
                            line
                        )
                    ).strip()

                score = _first(
                    row,
                    [
                        "hulk_market_score",
                        "evidence_score",
                    ],
                )

                premium_card(
                    _matchup(
                        row
                    ),
                    market,
                    pick_text
                    or "Research",
                    _game_reason(
                        row,
                        sport,
                    ),
                    [
                        (
                            _decision_tier(
                                score
                            ),
                            "green",
                        ),
                        (
                            friendly(
                                row.get(
                                    "decision",
                                    "Research",
                                )
                            ),
                            "blue",
                        ),
                    ],
                    SPORTS.get(
                        sport,
                        {},
                    ).get(
                        "accent",
                        "#2563EB",
                    ),
                )

    if sport == "NFL":
        props = nfl_props().copy()

        if not props.empty:
            props["_score"] = pd.to_numeric(
                props.get(
                    "hulk_prop_score"
                ),
                errors="coerce",
            )

            if "sample_gate" in props.columns:
                passed = props[
                    props["sample_gate"]
                    .astype(str)
                    .str.upper()
                    .eq("PASS")
                ]
                if not passed.empty:
                    props = passed

            props = props.sort_values(
                "_score",
                ascending=False,
            ).head(
                3
            )

        section_header(
            "Best Player Props",
            (
                "Recent production vs the line, "
                "with market and injury context."
            ),
        )

        if props.empty:
            st.info(
                "No player prop currently clears the sample gates."
            )
        else:
            cols = st.columns(
                min(
                    3,
                    len(props),
                )
            )

            for col, (_, row) in zip(
                cols,
                props.iterrows(),
            ):
                with col:
                    player = safe(
                        _first(
                            row,
                            [
                                "player_dfs",
                                "player",
                                "player_sportsbook",
                            ],
                            "Player",
                        )
                    )
                    side = safe(
                        row.get(
                            "side"
                        )
                    )
                    prop_line = _first(
                        row,
                        [
                            "dfs_line",
                            "line",
                        ],
                    )
                    recent = pd.to_numeric(
                        row.get(
                            "recent_metric"
                        ),
                        errors="coerce",
                    )
                    books = pd.to_numeric(
                        row.get(
                            "book_count"
                        ),
                        errors="coerce",
                    )
                    sample = pd.to_numeric(
                        row.get(
                            "meaningful_completed_games"
                        ),
                        errors="coerce",
                    )

                    reason = (
                        "Recent avg "
                        + number(
                            recent
                        )
                        + " vs line "
                        + line_text(
                            prop_line
                        )
                    )

                    if pd.notna(
                        books
                    ):
                        reason += (
                            " · "
                            + str(
                                int(
                                    books
                                )
                            )
                            + " books"
                        )

                    injury = safe(
                        row.get(
                            "espn_injury_gate"
                        )
                    )

                    if (
                        injury
                        and injury
                        not in {
                            "NO_ESPN_LISTING",
                            "CLEAR",
                        }
                    ):
                        reason += (
                            " · "
                            + friendly(
                                injury
                            )
                        )

                    premium_card(
                        player,
                        friendly(
                            row.get(
                                "market"
                            )
                        ),
                        (
                            side
                            + " "
                            + line_text(
                                prop_line
                            )
                        ).strip(),
                        reason,
                        [
                            (
                                friendly(
                                    row.get(
                                        "decision"
                                    )
                                ),
                                "green",
                            ),
                            (
                                (
                                    str(
                                        int(
                                            sample
                                        )
                                    )
                                    + "-game sample"
                                    if pd.notna(
                                        sample
                                    )
                                    else "Sample checked"
                                ),
                                "blue",
                            ),
                        ],
                        "#7C3AED",
                    )

        survivor_state = survivor_entries()
        active_name = survivor_state.get(
            "active",
            "",
        )
        active_entry = (
            survivor_state.get(
                "entries",
                {},
            ).get(
                active_name,
                {},
            )
            if active_name
            else {}
        )

        if active_entry:
            week = active_entry.get(
                "current_week",
                survivor_state.get(
                    "pool_current_week",
                    "—",
                ),
            )
            status = safe(
                active_entry.get(
                    "status",
                    "OPEN",
                )
            )
            used = active_entry.get(
                "used_teams",
                [],
            )
            current_picks = active_entry.get(
                "current_picks",
                [],
            )
            week_key = (
                "week_"
                + str(
                    week
                )
            )
            week_state = active_entry.get(
                week_key,
                {},
            )
            rule_status = safe(
                week_state.get(
                    "rule_status",
                    "",
                )
            )

            section_header(
                "Your Survivor",
                (
                    active_name
                    + " · Week "
                    + str(
                        week
                    )
                ),
            )

            cols = st.columns(2)

            with cols[0]:
                if current_picks:
                    headline = (
                        " + ".join(
                            current_picks
                        )
                    )
                    body = (
                        "Current picks are saved for Week "
                        + str(
                            week
                        )
                        + "."
                    )
                else:
                    headline = "Pick still open"
                    body = (
                        "Official Week "
                        + str(
                            week
                        )
                        + " requirement is still pending."
                        if "AWAITING_OFFICIAL"
                        in rule_status
                        else "No Week "
                        + str(
                            week
                        )
                        + " pick is saved yet."
                    )

                premium_card(
                    active_name,
                    "Week "
                    + str(
                        week
                    ),
                    headline,
                    body,
                    [
                        (
                            status,
                            "green",
                        ),
                        (
                            str(
                                len(
                                    used
                                )
                            )
                            + " teams used",
                            "blue",
                        ),
                    ],
                    "#059669",
                )

            strategy = survivor_strategy()

            if not strategy.empty:
                strategy = strategy[
                    ~strategy[
                        "survivor_team"
                    ].isin(
                        used
                    )
                ].copy()

                strategy["_score"] = pd.to_numeric(
                    strategy.get(
                        "strategy_index"
                    ),
                    errors="coerce",
                )

                strategy = strategy.sort_values(
                    "_score",
                    ascending=False,
                )

                if not strategy.empty:
                    top = strategy.iloc[
                        0
                    ]

                    with cols[1]:
                        premium_card(
                            "Best available option",
                            safe(
                                top.get(
                                    "survivor_team"
                                )
                            ),
                            (
                                safe(
                                    top.get(
                                        "survivor_team"
                                    )
                                )
                                + " "
                                + line_text(
                                    top.get(
                                        "survivor_spread"
                                    )
                                )
                            ),
                            (
                                "vs "
                                + safe(
                                    top.get(
                                        "opponent"
                                    )
                                )
                                + " · "
                                + friendly(
                                    top.get(
                                        "strategy_action"
                                    )
                                )
                            ),
                            [
                                (
                                    friendly(
                                        top.get(
                                            "hulk_decision_tier"
                                        )
                                    ),
                                    "green",
                                ),
                                (
                                    friendly(
                                        top.get(
                                            "future_value_label"
                                        )
                                    ),
                                    "blue",
                                ),
                            ],
                            "#059669",
                        )

        fantasy = nfl_fantasy().copy()

        if not fantasy.empty:
            fantasy["_score"] = pd.to_numeric(
                fantasy.get(
                    "fantasy_context_score"
                ),
                errors="coerce",
            )
            fantasy = fantasy.sort_values(
                "_score",
                ascending=False,
            ).head(
                3
            )

            section_header(
                "Fantasy Movers",
                (
                    "Only the biggest verified role and usage changes."
                ),
            )

            cols = st.columns(
                min(
                    3,
                    len(fantasy),
                )
            )

            for col, (_, row) in zip(
                cols,
                fantasy.iterrows(),
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
                                "fantasy_trend"
                            )
                        ),
                        (
                            "Snaps "
                            + number(
                                row.get(
                                    "latest_offense_pct"
                                )
                            )
                            + "% · "
                            + number(
                                row.get(
                                    "targets_l2_avg"
                                )
                            )
                            + " targets · "
                            + number(
                                row.get(
                                    "carries_l2_avg"
                                )
                            )
                            + " carries"
                        ),
                        [
                            (
                                (
                                    "Usage up"
                                    if pd.to_numeric(
                                        row.get(
                                            "role_delta"
                                        ),
                                        errors="coerce",
                                    )
                                    > 0
                                    else "Usage watch"
                                ),
                                "green",
                            ),
                        ],
                        "#EA7C22",
                    )

    news = sports_news_current()

    if not news.empty:
        news = news[
            news["sport"]
            .astype(str)
            .eq(
                sport
            )
        ].copy()

    if not news.empty:
        priority = {
            "INJURY": 0,
            "TRANSACTION": 1,
            "LINEUP_ROLE": 2,
            "FANTASY": 3,
            "NEWS": 4,
            "RECAP": 5,
            "RANKINGS": 6,
        }

        news["_priority"] = (
            news["news_type"]
            .astype(str)
            .map(
                priority
            )
            .fillna(
                9
            )
        )

        news["_published"] = pd.to_datetime(
            news.get(
                "published_at"
            ),
            utc=True,
            errors="coerce",
        )

        news = news.sort_values(
            [
                "_priority",
                "_published",
            ],
            ascending=[
                True,
                False,
            ],
        ).head(
            3
        )

        section_header(
            "News That Matters",
            "Only updates likely to affect a decision.",
        )

        cols = st.columns(
            min(
                3,
                len(news),
            )
        )

        for col, (_, row) in zip(
            cols,
            news.iterrows(),
        ):
            with col:
                premium_card(
                    safe(
                        row.get(
                            "headline"
                        )
                    ),
                    (
                        safe(
                            row.get(
                                "source"
                            )
                        )
                        + " · "
                        + friendly(
                            row.get(
                                "news_type"
                            )
                        )
                    ),
                    "What changed",
                    safe(
                        _first(
                            row,
                            [
                                "summary",
                                "description",
                                "why_it_matters",
                            ],
                            "",
                        )
                    )[:240],
                    [
                        (
                            friendly(
                                row.get(
                                    "news_type"
                                )
                            ),
                            "amber",
                        ),
                    ],
                    "#4F46E5",
                )

    with st.expander(
        "System health",
        expanded=False,
    ):
        health_dir = (
            "/home/ubuntu/sports-hulk/"
            "intelligence_warehouse/"
        )

        coverage = _read_today_csv(
            health_dir
            + "history_coverage/"
            + "CROSS_SPORT_HISTORY_COVERAGE.csv"
        )
        grades = _read_today_csv(
            health_dir
            + "postgame_grading/"
            + "POSTGAME_RESEARCH_GRADES_CURRENT.csv"
        )
        governance = _read_today_csv(
            health_dir
            + "learning_governance/"
            + "SIGNAL_CHANGE_ELIGIBILITY_CURRENT.csv"
        )

        historical_ready = (
            int(
                coverage[
                    "historical_coverage_ready"
                ].fillna(False).astype(bool).sum()
            )
            if (
                not coverage.empty
                and "historical_coverage_ready"
                in coverage.columns
            )
            else 0
        )

        historical_total = (
            len(
                coverage
            )
            if not coverage.empty
            else 0
        )

        live_graded = (
            int(
                grades[
                    "graded"
                ].fillna(False).astype(bool).sum()
            )
            if (
                not grades.empty
                and "graded"
                in grades.columns
            )
            else 0
        )

        auto_changes = (
            int(
                governance[
                    "automatic_weight_change_allowed"
                ].fillna(False).astype(bool).sum()
            )
            if (
                not governance.empty
                and "automatic_weight_change_allowed"
                in governance.columns
            )
            else 0
        )

        health_cols = st.columns(
            3
        )

        with health_cols[0]:
            st.metric(
                "History ready",
                (
                    str(
                        historical_ready
                    )
                    + "/"
                    + str(
                        historical_total
                    )
                ),
            )

        with health_cols[1]:
            st.metric(
                "Live outcomes graded",
                live_graded,
            )

        with health_cols[2]:
            st.metric(
                "Automatic changes",
                auto_changes,
            )

        st.caption(
            (
                "Automatic model changes remain locked "
                "until live sample gates are met."
            )
        )


def render_picks(
    sport="NFL",
):
    page_intro(
        f"{sport} Best Bets",
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
            "A real betting board: more qualified options, "
            "market context and the reason each bet is here."
        ),
    )

    if sport != "NFL":
        render_prepared_sport(
            sport
        )
        return

    games = nfl_games().copy()

    if games.empty:
        st.info(
            "No qualified NFL game research is available right now."
        )
        return

    games["_score"] = pd.to_numeric(
        games.get(
            "hulk_market_score"
        ),
        errors="coerce",
    )
    games["_books"] = pd.to_numeric(
        games.get(
            "sw_books",
            games.get(
                "oddspapi_bookmaker_count"
            ),
        ),
        errors="coerce",
    )
    games["_start"] = pd.to_datetime(
        games.get(
            "start"
        ),
        utc=True,
        errors="coerce",
    )

    now = pd.Timestamp.now(
        tz="UTC"
    )
    current_games = games[
        games["_start"].isna()
        | (
            games["_start"]
            >= now
            - pd.Timedelta(
                hours=4
            )
        )
    ].copy()

    if not current_games.empty:
        games = current_games

    games = games.sort_values(
        [
            "_score",
            "_books",
        ],
        ascending=[
            False,
            False,
        ],
    )

    market_filter = st.pills(
        "Bet market",
        [
            "All",
            "Moneyline",
            "Spread",
            "Total",
        ],
        default="All",
        required=True,
        label_visibility="collapsed",
        key="nfl_best_bets_market",
    )

    if market_filter == "All":
        visible = games.head(
            12
        ).copy()
    else:
        visible = games[
            games[
                "market"
            ].astype(str).str.upper().eq(
                market_filter.upper()
            )
        ].head(
            12
        ).copy()

    market_counts = (
        games[
            "market"
        ].astype(str).str.upper().value_counts()
    )

    st.caption(
        (
            str(
                len(
                    games
                )
            )
            + " current NFL game bets · "
            + str(
                int(
                    market_counts.get(
                        "MONEYLINE",
                        0,
                    )
                )
            )
            + " moneylines · "
            + str(
                int(
                    market_counts.get(
                        "SPREAD",
                        0,
                    )
                )
            )
            + " spreads · "
            + str(
                int(
                    market_counts.get(
                        "TOTAL",
                        0,
                    )
                )
            )
            + " totals"
        )
    )

    def _evidence_label(
        value,
    ):
        score = pd.to_numeric(
            value,
            errors="coerce",
        )
        if pd.isna(
            score
        ):
            return "Research"
        if score >= 95:
            return "Elite evidence"
        if score >= 88:
            return "Strong evidence"
        if score >= 80:
            return "Good evidence"
        return "Market lean"

    def _why(
        row,
    ):
        pieces = []

        books = pd.to_numeric(
            row.get(
                "_books"
            ),
            errors="coerce",
        )
        if pd.notna(
            books
        ):
            pieces.append(
                str(
                    int(
                        books
                    )
                )
                + " books"
            )

        if safe(
            row.get(
                "provider_agreement"
            )
        ).upper() == "AGREE":
            pieces.append(
                "providers agree"
            )
        else:
            pieces.append(
                "mixed provider view"
            )

        market = safe(
            row.get(
                "market"
            )
        ).upper()

        if market == "MONEYLINE":
            safety = pd.to_numeric(
                row.get(
                    "market_implied_safety"
                ),
                errors="coerce",
            )
            if pd.notna(
                safety
            ):
                pieces.append(
                    number(
                        safety
                    )
                    + "% market implied"
                )

        elif market == "SPREAD":
            move = pd.to_numeric(
                row.get(
                    "home_spread_move"
                ),
                errors="coerce",
            )
            if pd.notna(
                move
            ) and move != 0:
                pieces.append(
                    "spread moved "
                    + line_text(
                        move
                    )
                )

        elif market == "TOTAL":
            move = pd.to_numeric(
                row.get(
                    "total_move"
                ),
                errors="coerce",
            )
            if pd.notna(
                move
            ) and move != 0:
                pieces.append(
                    "total moved "
                    + line_text(
                        move
                    )
                )

        quality = safe(
            row.get(
                "market_data_quality"
            )
        )
        if quality:
            pieces.append(
                friendly(
                    quality
                )
                + " market depth"
            )

        return " · ".join(
            pieces[
                :4
            ]
        )

    def _risk(
        row,
    ):
        market = safe(
            row.get(
                "market"
            )
        ).upper()
        line = pd.to_numeric(
            row.get(
                "line"
            ),
            errors="coerce",
        )

        if (
            market == "MONEYLINE"
            and pd.notna(
                line
            )
            and abs(
                line
            )
            >= 300
        ):
            return (
                "High juice"
            )

        if safe(
            row.get(
                "provider_agreement"
            )
        ).upper() != "AGREE":
            return (
                "Provider disagreement"
            )

        if market in {
            "SPREAD",
            "TOTAL",
        }:
            return (
                "Market-led research"
            )

        return (
            "No major market flag"
        )

    section_header(
        (
            "All Best Bets"
            if market_filter == "All"
            else market_filter
        ),
        (
            "Ranked by current evidence. "
            "These are research candidates, not guaranteed outcomes."
        ),
    )

    if visible.empty:
        st.info(
            "No bets are available in this market right now."
        )
    else:
        for start in range(
            0,
            len(
                visible
            ),
            3,
        ):
            cols = st.columns(
                3
            )

            for col, (_, row) in zip(
                cols,
                visible.iloc[
                    start:start + 3
                ].iterrows(),
            ):
                market = safe(
                    row.get(
                        "market"
                    )
                ).upper()

                selection = safe(
                    row.get(
                        "selection"
                    )
                )
                bet_line = line_text(
                    row.get(
                        "line"
                    )
                )
                headline = (
                    selection
                    + " "
                    + bet_line
                ).strip()

                with col:
                    premium_card(
                        safe(
                            row.get(
                                "game_key",
                                "NFL Game",
                            )
                        ),
                        friendly(
                            market
                        ),
                        headline,
                        _why(
                            row
                        ),
                        [
                            (
                                _evidence_label(
                                    row.get(
                                        "hulk_market_score"
                                    )
                                ),
                                "green",
                            ),
                            (
                                _risk(
                                    row
                                ),
                                (
                                    "amber"
                                    if _risk(
                                        row
                                    )
                                    != "No major market flag"
                                    else "blue"
                                ),
                            ),
                        ],
                        "#2563EB",
                    )

    with st.expander(
        "Open full 43-bet NFL board",
        expanded=False,
    ):
        show_cols = [
            col
            for col in [
                "game_key",
                "start",
                "market",
                "selection",
                "line",
                "decision",
                "hulk_market_score",
                "market_implied_safety",
                "market_data_quality",
                "provider_agreement",
                "sw_books",
                "home_spread_move",
                "total_move",
                "model_status",
            ]
            if col
            in games.columns
        ]

        st.dataframe(
            games[
                show_cols
            ],
            width="stretch",
            hide_index=True,
        )


def render_props(
    sport="NFL",
    start_pickem=False,
):
    if sport in {
        "CFB",
        "CBB",
    }:
        render_college_no_props(
            sport
        )
        return

    page_intro(
        f"{sport} Props",
        "props",
        sport,
        (
            "Find the prop, understand why it stands out, "
            "and see the best current sportsbook price when available."
        ),
    )

    if sport != "NFL":
        render_prepared_sport(
            sport
        )
        return

    props = nfl_props().copy()
    pickem = nfl_pickem().copy()

    mode_options = [
        "Sportsbooks",
        "Pick'em",
    ]

    mode = st.pills(
        "Prop type",
        mode_options,
        default=(
            "Pick'em"
            if start_pickem
            else "Sportsbooks"
        ),
        required=True,
        label_visibility="collapsed",
        key="nfl_props_mode",
    )

    data = (
        pickem.copy()
        if mode
        == "Pick'em"
        else props.copy()
    )

    if data.empty:
        st.info(
            "No qualified player opportunities are available right now."
        )
        return

    data["_score"] = pd.to_numeric(
        data.get(
            "hulk_prop_score"
        ),
        errors="coerce",
    )
    data["_sample"] = pd.to_numeric(
        data.get(
            "meaningful_completed_games"
        ),
        errors="coerce",
    )

    if "sample_gate" in data.columns:
        passed = data[
            data[
                "sample_gate"
            ].astype(str).str.upper().eq(
                "PASS"
            )
        ].copy()
        if not passed.empty:
            data = passed

    def _prop_category(
        row,
    ):
        market = safe(
            row.get(
                "market"
            )
        ).upper()

        if (
            "TOUCHDOWN"
            in market
            or market.endswith(
                "_TDS"
            )
        ):
            return "TDs"

        if (
            "PASS"
            in market
            or "INTERCEPTION"
            in market
            or "COMPLETION"
            in market
        ):
            return "Passing"

        if "RUSH" in market:
            return "Rushing"

        if (
            "REC"
            in market
            or "TARGET"
            in market
        ):
            return "Receiving"

        if (
            "SACK"
            in market
            or "TACKLE"
            in market
            or "QB_HIT"
            in market
        ):
            return "Defense"

        return "Other"

    data["_category"] = data.apply(
        _prop_category,
        axis=1,
    )

    category_options = [
        "All",
    ] + [
        cat
        for cat in [
            "Passing",
            "Rushing",
            "Receiving",
            "TDs",
            "Defense",
            "Other",
        ]
        if cat
        in set(
            data[
                "_category"
            ]
        )
    ]

    category = st.pills(
        "Prop category",
        category_options,
        default="All",
        required=True,
        label_visibility="collapsed",
        key=(
            "nfl_props_category_"
            + mode.replace(
                "'",
                "",
            ).replace(
                " ",
                "_",
            )
        ),
    )

    visible = (
        data.copy()
        if category == "All"
        else data[
            data[
                "_category"
            ].eq(
                category
            )
        ].copy()
    )

    visible = visible.sort_values(
        [
            "_score",
            "_sample",
        ],
        ascending=[
            False,
            False,
        ],
    )

    best_price = {}

    if mode == "Sportsbooks":
        try:
            multibook = pd.read_csv(
                (
                    "/home/ubuntu/sports-hulk/"
                    "nfl_live/fusion/"
                    "NFL_MULTIBOOK_PLAYER_PROPS.csv"
                ),
                low_memory=False,
            )
        except Exception:
            multibook = pd.DataFrame()

        if not multibook.empty:
            multibook = multibook.copy()
            multibook[
                "_line"
            ] = pd.to_numeric(
                multibook.get(
                    "line"
                ),
                errors="coerce",
            )
            multibook[
                "_price"
            ] = pd.to_numeric(
                multibook.get(
                    "price_american"
                ),
                errors="coerce",
            )

            multibook = multibook[
                multibook[
                    "_price"
                ].notna()
            ].copy()

            multibook = multibook.sort_values(
                "_price",
                ascending=False,
            )

            for _, raw in multibook.iterrows():
                key = (
                    safe(
                        raw.get(
                            "player_key"
                        )
                    ),
                    safe(
                        raw.get(
                            "market_subtype"
                        )
                    ).upper(),
                    safe(
                        raw.get(
                            "side"
                        )
                    ).upper(),
                    (
                        round(
                            float(
                                raw.get(
                                    "_line"
                                )
                            ),
                            3,
                        )
                        if pd.notna(
                            raw.get(
                                "_line"
                            )
                        )
                        else None
                    ),
                )

                if key not in best_price:
                    best_price[
                        key
                    ] = {
                        "sportsbook":
                            safe(
                                raw.get(
                                    "sportsbook"
                                )
                            ),
                        "price":
                            raw.get(
                                "_price"
                            ),
                    }

    def _best(
        row,
    ):
        line_value = pd.to_numeric(
            row.get(
                "sportsbook_line",
                row.get(
                    "dfs_line",
                    row.get(
                        "line"
                    ),
                ),
            ),
            errors="coerce",
        )

        key = (
            safe(
                row.get(
                    "player_key"
                )
            ),
            safe(
                row.get(
                    "market"
                )
            ).upper(),
            safe(
                row.get(
                    "side"
                )
            ).upper(),
            (
                round(
                    float(
                        line_value
                    ),
                    3,
                )
                if pd.notna(
                    line_value
                )
                else None
            ),
        )

        return best_price.get(
            key,
            {},
        )

    def _odds_text(
        value,
    ):
        number_value = pd.to_numeric(
            value,
            errors="coerce",
        )
        if pd.isna(
            number_value
        ):
            return "—"
        integer = int(
            round(
                number_value
            )
        )
        return (
            "+"
            + str(
                integer
            )
            if integer
            > 0
            else str(
                integer
            )
        )

    def _why(
        row,
    ):
        pieces = []

        recent = pd.to_numeric(
            row.get(
                "recent_metric"
            ),
            errors="coerce",
        )
        line_value = pd.to_numeric(
            row.get(
                "dfs_line",
                row.get(
                    "line"
                ),
            ),
            errors="coerce",
        )

        if (
            pd.notna(
                recent
            )
            and pd.notna(
                line_value
            )
        ):
            pieces.append(
                "recent avg "
                + number(
                    recent
                )
                + " vs "
                + number(
                    line_value
                )
            )

        direction = safe(
            row.get(
                "context_direction"
            )
        )
        if direction:
            pieces.append(
                friendly(
                    direction
                )
                + " context"
            )

        books = pd.to_numeric(
            row.get(
                "book_count"
            ),
            errors="coerce",
        )
        if pd.notna(
            books
        ):
            pieces.append(
                str(
                    int(
                        books
                    )
                )
                + " books"
            )

        line_gap = pd.to_numeric(
            row.get(
                "line_gap"
            ),
            errors="coerce",
        )
        if (
            pd.notna(
                line_gap
            )
            and line_gap
            != 0
        ):
            pieces.append(
                "market gap "
                + line_text(
                    line_gap
                )
            )

        return " · ".join(
            pieces[
                :4
            ]
        )

    def _risk(
        row,
    ):
        injury = safe(
            row.get(
                "espn_injury_gate"
            )
        ).upper()

        if injury not in {
            "",
            "NO_ESPN_LISTING",
            "CLEAR",
            "PASS",
        }:
            return friendly(
                injury
            )

        sample = pd.to_numeric(
            row.get(
                "meaningful_completed_games"
            ),
            errors="coerce",
        )

        if (
            pd.notna(
                sample
            )
            and sample
            < 5
        ):
            return (
                "Small sample"
            )

        return (
            "No major injury flag"
        )

    player_col = next(
        (
            col
            for col in [
                "player_dfs",
                "player",
                "player_sportsbook",
            ]
            if col
            in visible.columns
        ),
        None,
    )

    market_col = (
        "market_subtype"
        if (
            mode
            == "Pick'em"
            and "market_subtype"
            in visible.columns
        )
        else "market"
    )

    line_col = (
        "line"
        if (
            mode
            == "Pick'em"
            and "line"
            in visible.columns
        )
        else "dfs_line"
    )

    st.caption(
        (
            str(
                len(
                    data
                )
            )
            + " qualified NFL prop opportunities"
            + (
                " · "
                + str(
                    len(
                        visible
                    )
                )
                + " in "
                + category
                if category
                != "All"
                else ""
            )
        )
    )

    section_header(
        (
            mode
            + " Props"
        ),
        (
            "Ranked by current research score after sample "
            "and availability gates."
        ),
    )

    display_rows = visible.head(
        9
    )

    for start in range(
        0,
        len(
            display_rows
        ),
        3,
    ):
        cols = st.columns(
            3
        )

        for col, (_, row) in zip(
            cols,
            display_rows.iloc[
                start:start + 3
            ].iterrows(),
        ):
            player = (
                safe(
                    row.get(
                        player_col
                    )
                )
                if player_col
                else "Player"
            )

            side = safe(
                row.get(
                    "side"
                )
            )

            prop_line = line_text(
                row.get(
                    line_col
                )
            )

            best = _best(
                row
            )

            if mode == "Sportsbooks":
                if best:
                    price_line = (
                        "Best "
                        + friendly(
                            best.get(
                                "sportsbook"
                            )
                        )
                        + " "
                        + _odds_text(
                            best.get(
                                "price"
                            )
                        )
                    )
                else:
                    median_price = row.get(
                        "price_median"
                    )
                    price_line = (
                        "Market median "
                        + _odds_text(
                            median_price
                        )
                    )
            else:
                price_line = (
                    safe(
                        row.get(
                            "dfs_source",
                            "Pick'em",
                        )
                    )
                    + " · "
                    + safe(
                        row.get(
                            "dfs_multiplier",
                            "—",
                        )
                    )
                    + "x"
                )

            with col:
                premium_card(
                    player,
                    friendly(
                        row.get(
                            market_col
                        )
                    ),
                    (
                        side
                        + " "
                        + prop_line
                    ).strip(),
                    (
                        _why(
                            row
                        )
                        + (
                            " · "
                            + price_line
                            if price_line
                            else ""
                        )
                    ),
                    [
                        (
                            friendly(
                                row.get(
                                    "decision"
                                )
                            ),
                            "green",
                        ),
                        (
                            _risk(
                                row
                            ),
                            (
                                "amber"
                                if _risk(
                                    row
                                )
                                != "No major injury flag"
                                else "blue"
                            ),
                        ),
                    ],
                    (
                        "#9B7CFF"
                        if mode
                        == "Pick'em"
                        else "#4F8CFF"
                    ),
                )

    with st.expander(
        "Open full prop board",
        expanded=False,
    ):
        show_cols = [
            col
            for col in [
                player_col,
                market_col,
                "side",
                line_col,
                "recent_metric",
                "context_direction",
                "book_count",
                "books",
                "price_median",
                "line_gap",
                "meaningful_completed_games",
                "decision",
                "hulk_prop_score",
                "espn_injury_gate",
            ]
            if col
            and col
            in data.columns
        ]

        st.dataframe(
            data[
                show_cols
            ].sort_values(
                "hulk_prop_score",
                ascending=False,
            )
            if "hulk_prop_score"
            in data.columns
            else data[
                show_cols
            ],
            width="stretch",
            hide_index=True,
        )


def render_prizepicks(
    sport="NFL",
):
    # NBA_GLOBAL_PP_BUILD_6
    if sport == "NBA":

        from premium_ui.nba_ui import (
            render_nba_prizepicks,
        )

        render_nba_prizepicks()
        return


    # NHL_GLOBAL_PP_BUILD_6
    if sport == "NHL":

        from premium_ui.nhl_ui import (
            render_nhl_prizepicks,
        )

        render_nhl_prizepicks()
        return


    # MLB_GLOBAL_PP_BUILD_V2
    if sport == "MLB":

        from premium_ui.mlb_ui import (
            render_mlb_prizepicks,
        )

        render_mlb_prizepicks()
        return


    page_intro(
        f"{sport} PrizePicks",
        "prizepicks",
        sport,
        (
            "PrizePicks projections with independent "
            "player research and sportsbook comparison."
        ),
    )

    # College sports intentionally excluded.
    if sport in {
        "CFB",
        "CBB",
    }:
        empty_card(
            "PrizePicks Not Included",
            (
                "College player props are intentionally "
                "not part of Sports HULK."
            ),
            "#C026D3",
        )
        return

    # Other pro sports are prepared but not
    # populated until their engines are connected.
    if sport != "NFL":
        empty_card(
            f"{sport} PrizePicks",
            (
                "The premium PrizePicks layout is ready. "
                "Verified player-projection intelligence "
                "will appear here when this sport engine "
                "is connected."
            ),
            "#C026D3",
        )
        return

    data = nfl_pickem()

    if data.empty:
        empty_card(
            "No Qualified PrizePicks Right Now",
            (
                "No current projections meet the "
                "qualification rules. Sports HULK will "
                "not manufacture a selection just to "
                "fill the page."
            ),
            "#C026D3",
        )
        return

    data = data.copy()

    if "hulk_prop_score" in data.columns:
        data["_sort"] = pd.to_numeric(
            data["hulk_prop_score"],
            errors="coerce",
        )

        data = data.sort_values(
            "_sort",
            ascending=False,
        )

    player_col = next(
        (
            c
            for c in [
                "player",
                "player_dfs",
                "player_sportsbook",
            ]
            if c in data.columns
        ),
        None,
    )

    market_col = (
        "market_subtype"
        if "market_subtype" in data.columns
        else "market"
    )

    line_col = (
        "line"
        if "line" in data.columns
        else "dfs_line"
    )

    for start in range(
        0,
        min(len(data), 18),
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

                player = (
                    safe(
                        row.get(player_col)
                    )
                    if player_col
                    else "Player"
                )

                premium_card(
                    player,
                    friendly(
                        row.get(
                            market_col
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
                                line_col
                            )
                        )
                    ).strip(),
                    (
                        safe(
                            row.get(
                                "book_count",
                                "—",
                            )
                        )
                        + " books · "
                        + safe(
                            row.get(
                                "meaningful_completed_games",
                                "—",
                            )
                        )
                        + " meaningful games"
                    ),
                    [
                        (
                            "Evidence "
                            + number(
                                row.get(
                                    "hulk_prop_score"
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
                    "#C026D3",
                )


# ============================================================
# PARLAYS
# ============================================================

def render_parlays(
    sport="NFL",
):
    page_intro(
        f"{sport} Parlays",
        "parlays",
        sport,
        (
            "Multiple qualified combinations, with leg quality "
            "and correlation checks visible before you use them."
        ),
    )

    if sport != "NFL":
        render_prepared_sport(
            sport
        )
        return

    data = nfl_parlays().copy()

    if data.empty:
        st.info(
            "No qualified parlays are available right now."
        )
        return

    data["_score"] = pd.to_numeric(
        data.get(
            "parlay_score"
        ),
        errors="coerce",
    )
    data["_leg1"] = pd.to_numeric(
        data.get(
            "leg1_score"
        ),
        errors="coerce",
    )
    data["_leg2"] = pd.to_numeric(
        data.get(
            "leg2_score"
        ),
        errors="coerce",
    )

    data = data.sort_values(
        [
            "_score",
            "_leg1",
            "_leg2",
        ],
        ascending=[
            False,
            False,
            False,
        ],
    )

    type_map = {
        "All": None,
        "Game ML": "GAME_ML_2_LEG",
        "Mixed": "MIXED_ML_PROP_2_LEG",
        "Player Props": "PLAYER_PROP_2_LEG",
    }

    available_filters = [
        "All",
    ]

    for label, raw_type in [
        (
            "Game ML",
            "GAME_ML_2_LEG",
        ),
        (
            "Mixed",
            "MIXED_ML_PROP_2_LEG",
        ),
        (
            "Player Props",
            "PLAYER_PROP_2_LEG",
        ),
    ]:
        if data[
            "parlay_type"
        ].astype(str).eq(
            raw_type
        ).any():
            available_filters.append(
                label
            )

    selected_type = st.pills(
        "Parlay type",
        available_filters,
        default="All",
        required=True,
        label_visibility="collapsed",
        key="nfl_parlay_type",
    )

    raw_type = type_map.get(
        selected_type
    )

    visible = (
        data.copy()
        if raw_type is None
        else data[
            data[
                "parlay_type"
            ].astype(str).eq(
                raw_type
            )
        ].copy()
    )

    st.caption(
        (
            str(
                len(
                    data
                )
            )
            + " qualified two-leg combinations"
            + (
                " · "
                + str(
                    len(
                        visible
                    )
                )
                + " in "
                + selected_type
                if selected_type
                != "All"
                else ""
            )
        )
    )

    section_header(
        (
            selected_type
            + " Parlays"
        ),
        (
            "Every visible leg already qualifies on its own. "
            "Different-game combinations are kept separate to reduce hidden correlation."
        ),
    )

    display_rows = visible.head(
        9
    )

    for start in range(
        0,
        len(
            display_rows
        ),
        3,
    ):
        cols = st.columns(
            3
        )

        for col, (_, row) in zip(
            cols,
            display_rows.iloc[
                start:start + 3
            ].iterrows(),
        ):
            leg1 = safe(
                row.get(
                    "leg1_label"
                )
            )
            leg2 = safe(
                row.get(
                    "leg2_label"
                )
            )

            correlation = safe(
                row.get(
                    "correlation_status"
                )
            )

            if correlation == "VERIFIED_DIFFERENT_GAMES":
                correlation_text = (
                    "Different games"
                )
                correlation_tone = (
                    "green"
                )
            else:
                correlation_text = friendly(
                    correlation
                )
                correlation_tone = (
                    "amber"
                )

            with col:
                premium_card(
                    friendly(
                        row.get(
                            "parlay_type"
                        )
                    ),
                    "2-Leg Research",
                    (
                        leg1
                        + " + "
                        + leg2
                    ),
                    (
                        "Leg strength "
                        + number(
                            row.get(
                                "leg1_score"
                            )
                        )
                        + " / "
                        + number(
                            row.get(
                                "leg2_score"
                            )
                        )
                        + " · Combined research "
                        + number(
                            row.get(
                                "parlay_score"
                            )
                        )
                    ),
                    [
                        (
                            correlation_text,
                            correlation_tone,
                        ),
                        (
                            "Verify payout at book",
                            "amber",
                        ),
                    ],
                    "#0F9F9A",
                )

    with st.expander(
        "Open all 30 parlay combinations",
        expanded=False,
    ):
        show_cols = [
            col
            for col in [
                "parlay_type",
                "parlay_score",
                "leg1_label",
                "leg1_score",
                "leg2_label",
                "leg2_score",
                "correlation_status",
                "status",
                "payout_status",
            ]
            if col
            in data.columns
        ]

        st.dataframe(
            data[
                show_cols
            ],
            width="stretch",
            hide_index=True,
        )

    st.caption(
        (
            "Parlay research score is not a win probability. "
            "Sportsbook payout and final available lines must be verified before placing."
        )
    )


def render_survivor():
    page_intro(
        "Survivor",
        "survivor",
        "NFL",
        (
            "Your live entry and the next decision. "
            "Everything else stays one tap deeper."
        ),
    )

    summary = survivor_summary()
    entries_data = survivor_entries()
    strategy = survivor_strategy()

    entries = (
        entries_data.get(
            "entries",
            {},
        )
        if isinstance(
            entries_data,
            dict,
        )
        else {}
    )

    strategy_weeks = (
        pd.to_numeric(
            strategy.get(
                "current_week",
                pd.Series(dtype=float),
            ),
            errors="coerce",
        ).dropna()
        if not strategy.empty
        else pd.Series(
            dtype=float
        )
    )

    current_week = (
        int(
            strategy_weeks.mode().iloc[
                0
            ]
        )
        if not strategy_weeks.empty
        else int(
            summary.get(
                "pool_week",
                4,
            )
            or 4
        )
    )

    starting = int(
        summary.get(
            "parsed_entries",
            0,
        )
        or 0
    )

    remaining = int(
        summary.get(
            f"week{current_week}_entries_entering",
            summary.get(
                "imported_active_or_unconfirmed",
                summary.get(
                    "week3_survivors_final",
                    0,
                ),
            ),
        )
        or 0
    )

    eliminated = max(
        starting - remaining,
        0,
    )

    survival_pct = (
        (remaining / starting) * 100
        if starting
        else 0
    )

    owned_names = sorted(
        [
            name
            for name, entry in entries.items()
            if (
                str(
                    name
                ).startswith(
                    "ANNIE G"
                )
                or bool(
                    (
                        entry
                        if isinstance(
                            entry,
                            dict,
                        )
                        else {}
                    ).get(
                        "created_manually_at"
                    )
                )
            )
        ]
    )

    alive_names = [
        name
        for name in owned_names
        if safe(
            entries.get(
                name,
                {},
            ).get(
                "status"
            )
        ).upper()
        == "ALIVE"
    ]

    active_name = (
        entries_data.get(
            "active"
        )
        if isinstance(
            entries_data,
            dict,
        )
        else None
    )

    if active_name not in alive_names:
        active_name = (
            alive_names[0]
            if alive_names
            else None
        )

    active_entry = (
        entries.get(
            active_name,
            {},
        )
        if active_name
        else {}
    )

    used = [
        str(
            team
        )
        for team in (
            active_entry.get(
                "used_teams"
            )
            or []
        )
        if str(
            team
        ).strip()
    ]

    current_picks = (
        active_entry.get(
            "current_picks"
        )
        or []
    )

    last_week = max(
        current_week - 1,
        1,
    )

    last_week_state = active_entry.get(
        "week_"
        + str(
            last_week
        ),
        {},
    )

    live_board = strategy.copy()

    if (
        not live_board.empty
        and "current_week"
        in live_board.columns
    ):
        live_weeks = pd.to_numeric(
            live_board[
                "current_week"
            ],
            errors="coerce",
        )
        live_board = live_board[
            live_weeks.eq(
                current_week
            )
        ].copy()

    if (
        not live_board.empty
        and "start"
        in live_board.columns
    ):
        live_starts = pd.to_datetime(
            live_board[
                "start"
            ],
            errors="coerce",
            utc=True,
        )
        live_board = live_board[
            (
                live_starts.isna()
                | (
                    live_starts
                    >= pd.Timestamp.now(
                        tz="UTC"
                    )
                    - pd.Timedelta(
                        hours=1
                    )
                )
            )
        ].copy()

    if (
        not live_board.empty
        and "survivor_team"
        in live_board.columns
    ):
        live_board = live_board[
            ~live_board[
                "survivor_team"
            ].astype(str).isin(
                set(
                    used
                )
            )
        ].copy()

    if not live_board.empty:
        live_board[
            "_sort"
        ] = pd.to_numeric(
            live_board.get(
                "strategy_index"
            ),
            errors="coerce",
        )
        live_board = live_board.sort_values(
            "_sort",
            ascending=False,
        )

    week_state = active_entry.get(
        "week_"
        + str(
            current_week
        ),
        {},
    )

    rule_status = safe(
        week_state.get(
            "rule_status",
            summary.get(
                "current_week_rule_status",
                "",
            ),
        )
    )

    required_picks = week_state.get(
        "required_picks",
        summary.get(
            "current_week_required_picks"
        ),
    )

    if (
        required_picks is None
        and "AWAITING_OFFICIAL"
        in rule_status
    ):
        st.warning(
            (
                "Week "
                + str(
                    current_week
                )
                + " official pool sheet is still pending. "
                "Pick count and field ownership are not confirmed yet."
            )
        )
    elif required_picks is not None:
        st.success(
            (
                "Official Week "
                + str(
                    current_week
                )
                + " requirement: "
                + str(
                    int(
                        required_picks
                    )
                )
                + (
                    " picks."
                    if int(
                        required_picks
                    )
                    != 1
                    else " pick."
                )
            )
        )

    last_week_picks = (
        last_week_state.get(
            "picks"
        )
        or []
    )

    last_week_result = safe(
        last_week_state.get(
            "entry_result",
            "",
        )
    ).upper()

    last_week_pick_text = " · ".join(
        [
            (
                safe(
                    item.get(
                        "team"
                    )
                )
                + (
                    " — "
                    + safe(
                        item.get(
                            "result"
                        )
                    )
                    if safe(
                        item.get(
                            "result"
                        )
                    )
                    else ""
                )
            )
            for item in last_week_picks
            if isinstance(
                item,
                dict,
            )
            and safe(
                item.get(
                    "team"
                )
            )
        ]
    )

    last_week_status_text = " · ".join(
        [
            safe(
                item.get(
                    "game_status"
                )
            )
            for item in last_week_picks
            if isinstance(
                item,
                dict,
            )
            and safe(
                item.get(
                    "game_status"
                )
            )
        ]
    )

    recommendation_board = (
        live_board[
            ~live_board[
                "strategy_action"
            ].astype(str).eq(
                "AVOID"
            )
        ].copy()
        if (
            not live_board.empty
            and "strategy_action"
            in live_board.columns
        )
        else live_board.copy()
    )

    featured_row = (
        recommendation_board.iloc[
            0
        ]
        if not recommendation_board.empty
        else None
    )

    section_header(
        "Last Week & This Week",
        "Your actual result first, then the current Sports HULK recommendation and why.",
    )

    recap_cols = st.columns(
        2
    )

    with recap_cols[0]:
        if last_week_picks:
            last_headline = (
                "SURVIVED"
                if last_week_result
                in {
                    "WIN",
                    "SURVIVED",
                }
                else (
                    last_week_result
                    or "Complete"
                )
            )

            premium_card(
                (
                    "Week "
                    + str(
                        last_week
                    )
                    + " Result"
                ),
                active_name
                or "Your Entry",
                last_headline,
                (
                    last_week_pick_text
                    + (
                        " · "
                        + last_week_status_text
                        if last_week_status_text
                        else ""
                    )
                ),
                [
                    (
                        last_headline,
                        (
                            "green"
                            if last_headline
                            == "SURVIVED"
                            else "amber"
                        ),
                    ),
                ],
                "#059669",
            )
        else:
            premium_card(
                (
                    "Week "
                    + str(
                        last_week
                    )
                    + " Result"
                ),
                active_name
                or "Your Entry",
                "No saved result",
                "The entry ledger has no prior-week result recorded yet.",
                [
                    (
                        "History",
                        "blue",
                    ),
                ],
                "#059669",
            )

    with recap_cols[1]:
        if featured_row is not None:
            positive_tokens = [
                friendly(
                    token
                )
                for token
                in safe(
                    featured_row.get(
                        "positive_signals"
                    )
                ).split(
                    "|"
                )
                if token
                and token
                != "nan"
            ]

            risk_tokens = [
                friendly(
                    token
                )
                for token
                in safe(
                    featured_row.get(
                        "risk_signals"
                    )
                ).split(
                    "|"
                )
                if token
                and token
                != "nan"
            ]

            why_parts = [
                (
                    number(
                        featured_row.get(
                            "market_prob_pct"
                        )
                    )
                    + "% market safety"
                ),
                (
                    "spread "
                    + line_text(
                        featured_row.get(
                            "survivor_spread"
                        )
                    )
                ),
                (
                    "HULK context "
                    + number(
                        featured_row.get(
                            "hulk_context_score"
                        )
                    )
                ),
            ]

            if positive_tokens:
                why_parts.append(
                    ", ".join(
                        positive_tokens[
                            :3
                        ]
                    )
                )

            if risk_tokens:
                why_parts.append(
                    "Risk: "
                    + ", ".join(
                        risk_tokens[
                            :2
                        ]
                    )
                )

            premium_card(
                (
                    "Week "
                    + str(
                        current_week
                    )
                    + " HULK Pick"
                ),
                (
                    "vs "
                    + safe(
                        featured_row.get(
                            "opponent"
                        )
                    )
                ),
                safe(
                    featured_row.get(
                        "survivor_team"
                    )
                ),
                " · ".join(
                    why_parts
                ),
                [
                    (
                        friendly(
                            featured_row.get(
                                "hulk_decision_tier"
                            )
                        ),
                        "green",
                    ),
                    (
                        friendly(
                            featured_row.get(
                                "strategy_action"
                            )
                        ),
                        "blue",
                    ),
                ],
                "#059669",
            )

            next_options = [
                safe(
                    row.get(
                        "survivor_team"
                    )
                )
                for _, row
                in recommendation_board.iloc[
                    1:3
                ].iterrows()
                if safe(
                    row.get(
                        "survivor_team"
                    )
                )
            ]

            if next_options:
                st.caption(
                    (
                        "Next options: "
                        + " · ".join(
                            next_options
                        )
                    )
                )
        else:
            premium_card(
                (
                    "Week "
                    + str(
                        current_week
                    )
                    + " HULK Pick"
                ),
                "Current board",
                "Waiting for board",
                "No unused current-week Survivor recommendation is available yet.",
                [
                    (
                        "Waiting",
                        "blue",
                    ),
                ],
                "#059669",
            )

    section_header(
        "Your Entry",
        "Current status first. No pool spreadsheet needed.",
    )

    cols = st.columns(
        2
    )

    with cols[0]:
        if active_name:
            headline = (
                " + ".join(
                    current_picks
                )
                if current_picks
                else "Pick still open"
            )

            body = (
                "Used: "
                + (
                    " · ".join(
                        used
                    )
                    if used
                    else "None"
                )
            )

            premium_card(
                active_name,
                (
                    "Week "
                    + str(
                        current_week
                    )
                ),
                headline,
                body,
                [
                    (
                        safe(
                            active_entry.get(
                                "status",
                                "OPEN",
                            )
                        ),
                        "green",
                    ),
                    (
                        str(
                            len(
                                used
                            )
                        )
                        + " teams used",
                        "blue",
                    ),
                ],
                "#059669",
            )
        else:
            st.error(
                "No surviving entry is currently recorded."
            )

    with cols[1]:
        premium_card(
            "Pool",
            (
                str(
                    remaining
                )
                + " of "
                + str(
                    starting
                )
                + " remain"
            ),
            (
                number(
                    survival_pct
                )
                + "% alive"
            ),
            (
                str(
                    eliminated
                )
                + " entries have been eliminated."
            ),
            [
                (
                    "Week "
                    + str(
                        current_week
                    ),
                    "blue",
                ),
            ],
            "#059669",
        )

    if current_picks:
        score_payload = nfl_score_snapshot()
        score_games = []

        if isinstance(
            score_payload,
            dict,
        ):
            score_games = (
                score_payload.get(
                    "games"
                )
                or []
            ) + (
                score_payload.get(
                    "next_games"
                )
                or []
            )

        section_header(
            "My Pick Score",
            (
                "Live status for the team(s) you saved for Week "
                + str(
                    current_week
                )
                + "."
            ),
        )

        score_cols = st.columns(
            min(
                2,
                len(
                    current_picks
                ),
            )
        )

        for col, pick_team in zip(
            score_cols,
            current_picks,
        ):
            game = next(
                (
                    item
                    for item
                    in score_games
                    if pick_team
                    in {
                        safe(
                            item.get(
                                "away"
                            )
                        ),
                        safe(
                            item.get(
                                "home"
                            )
                        ),
                    }
                ),
                None,
            )

            with col:
                if not game:
                    premium_card(
                        pick_team,
                        (
                            "Week "
                            + str(
                                current_week
                            )
                        ),
                        "Score waiting",
                        (
                            "This pick is saved. "
                            "The live score will appear when the game enters the current scoreboard feed."
                        ),
                        [
                            (
                                "Saved",
                                "blue",
                            ),
                        ],
                        "#059669",
                    )
                    continue

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

                pick_is_away = (
                    pick_team
                    == away
                )

                opponent = (
                    home
                    if pick_is_away
                    else away
                )

                pick_score = pd.to_numeric(
                    (
                        game.get(
                            "away_score"
                        )
                        if pick_is_away
                        else game.get(
                            "home_score"
                        )
                    ),
                    errors="coerce",
                )

                opponent_score = pd.to_numeric(
                    (
                        game.get(
                            "home_score"
                        )
                        if pick_is_away
                        else game.get(
                            "away_score"
                        )
                    ),
                    errors="coerce",
                )

                is_final = bool(
                    game.get(
                        "final"
                    )
                )
                is_live = bool(
                    game.get(
                        "live"
                    )
                )

                if is_final:
                    if (
                        pd.notna(
                            pick_score
                        )
                        and pd.notna(
                            opponent_score
                        )
                    ):
                        if (
                            pick_score
                            > opponent_score
                        ):
                            pick_state = "SURVIVED"
                            pick_tone = "green"
                        elif (
                            pick_score
                            < opponent_score
                        ):
                            pick_state = "LOST"
                            pick_tone = "amber"
                        else:
                            pick_state = "TIED FINAL"
                            pick_tone = "amber"
                    else:
                        pick_state = "FINAL"
                        pick_tone = "blue"

                elif is_live:
                    if (
                        pd.notna(
                            pick_score
                        )
                        and pd.notna(
                            opponent_score
                        )
                    ):
                        if (
                            pick_score
                            > opponent_score
                        ):
                            pick_state = "AHEAD"
                            pick_tone = "green"
                        elif (
                            pick_score
                            < opponent_score
                        ):
                            pick_state = "BEHIND"
                            pick_tone = "amber"
                        else:
                            pick_state = "TIED"
                            pick_tone = "blue"
                    else:
                        pick_state = "LIVE"
                        pick_tone = "blue"

                else:
                    pick_state = "UPCOMING"
                    pick_tone = "blue"

                score_text = (
                    (
                        number(
                            pick_score,
                            0,
                        )
                        + " – "
                        + number(
                            opponent_score,
                            0,
                        )
                    )
                    if (
                        pd.notna(
                            pick_score
                        )
                        and pd.notna(
                            opponent_score
                        )
                    )
                    else safe(
                        game.get(
                            "status",
                            "Upcoming",
                        )
                    )
                )

                game_status = safe(
                    game.get(
                        "status"
                    )
                )

                detail = score_text

                if (
                    game_status
                    and game_status
                    not in detail
                ):
                    detail += (
                        " · "
                        + game_status
                    )

                premium_card(
                    pick_team,
                    (
                        "vs "
                        + opponent
                    ),
                    pick_state,
                    detail,
                    [
                        (
                            pick_state,
                            pick_tone,
                        ),
                        (
                            "Week "
                            + str(
                                current_week
                            ),
                            "blue",
                        ),
                    ],
                    "#059669",
                )

    section_header(
        "My Teams & Picks",
        (
            "Add teams you already used and save this week's pick. "
            "Sports HULK never submits to the external pool."
        ),
    )

    with st.expander(
        "Manage my Survivor entries",
        expanded=False,
    ):
        st.caption(
            (
                "Changes here are personal Sports HULK state. "
                "Official pool/PDF results remain separate."
            )
        )

        if owned_names:
            managed_default = (
                owned_names.index(
                    active_name
                )
                if active_name
                in owned_names
                else 0
            )

            managed_name = st.selectbox(
                "Entry",
                owned_names,
                index=managed_default,
                key="survivor_manage_entry",
            )

            managed_entry = entries.get(
                managed_name,
                {},
            )

            managed_status = safe(
                managed_entry.get(
                    "status",
                    "OPEN",
                )
            ).upper()

            managed_week = max(
                int(
                    managed_entry.get(
                        "current_week",
                        current_week,
                    )
                    or current_week
                ),
                int(
                    current_week
                ),
            )

            managed_week_state = managed_entry.get(
                "week_"
                + str(
                    managed_week
                ),
                {},
            )

            managed_required = managed_week_state.get(
                "required_picks"
            )

            existing_used = [
                str(
                    team
                )
                for team
                in (
                    managed_entry.get(
                        "used_teams"
                    )
                    or []
                )
                if str(
                    team
                ).strip()
            ]

            existing_picks = [
                str(
                    team
                )
                for team
                in (
                    managed_entry.get(
                        "current_picks"
                    )
                    or []
                )
                if str(
                    team
                ).strip()
            ]

            team_options = sorted(
                set(
                    NFL_TEAMS
                    + existing_used
                    + existing_picks
                )
            )

            with st.form(
                "survivor_entry_editor"
            ):
                st.markdown(
                    "**Past Teams Used**"
                )
                st.caption(
                    "Teams you already burned in earlier Survivor weeks."
                )

                used_input = st.multiselect(
                    "Past teams used",
                    team_options,
                    default=existing_used,
                    help=(
                        "These teams are removed from your Survivor strategy board."
                    ),
                )

                st.markdown(
                    (
                        "**This Week's Pick(s) — Week "
                        + str(
                            managed_week
                        )
                        + "**"
                    )
                )
                st.caption(
                    "Saved in Sports HULK only. This does not submit to your external pool."
                )

                current_input = st.multiselect(
                    (
                        "Week "
                        + str(
                            managed_week
                        )
                        + " current pick(s)"
                    ),
                    team_options,
                    default=existing_picks,
                    disabled=(
                        managed_status
                        != "ALIVE"
                    ),
                    help=(
                        "Saved in Sports HULK only. This does not submit your pool pick."
                    ),
                )

                make_active = st.checkbox(
                    "Use this as my active entry",
                    value=(
                        managed_name
                        == active_name
                    ),
                    disabled=(
                        managed_status
                        != "ALIVE"
                    ),
                )

                saved = st.form_submit_button(
                    "Save Entry Changes",
                    type="primary",
                    width="stretch",
                )

            if saved:
                duplicate_pick = sorted(
                    set(
                        current_input
                    )
                    & set(
                        used_input
                    )
                )

                too_many = (
                    managed_required
                    is not None
                    and len(
                        current_input
                    )
                    > int(
                        managed_required
                    )
                )

                if duplicate_pick:
                    st.error(
                        (
                            "Current-week picks cannot already be in Used Teams: "
                            + ", ".join(
                                duplicate_pick
                            )
                        )
                    )
                elif too_many:
                    st.error(
                        (
                            "This week's official requirement is "
                            + str(
                                int(
                                    managed_required
                                )
                            )
                            + " pick(s)."
                        )
                    )
                else:
                    save_survivor_entry(
                        managed_name,
                        used_teams=used_input,
                        current_week=managed_week,
                        current_picks=current_input,
                        make_active=make_active,
                    )

                    if (
                        managed_required
                        is not None
                        and current_input
                        and len(
                            current_input
                        )
                        < int(
                            managed_required
                        )
                    ):
                        st.warning(
                            (
                                "Saved, but you still need "
                                + str(
                                    int(
                                        managed_required
                                    )
                                    - len(
                                        current_input
                                    )
                                )
                                + " more pick(s) for the official requirement."
                            )
                        )
                    else:
                        st.success(
                            (
                                "Saved in Sports HULK. "
                                "Your strategy board will now exclude the teams you marked as used."
                            )
                        )

                    st.rerun()

        else:
            st.info(
                "No personal Survivor entry exists yet."
            )

        st.divider()
        st.markdown(
            "**Add another entry**"
        )

        with st.form(
            "survivor_new_entry"
        ):
            new_entry_name = st.text_input(
                "Entry name",
                placeholder=(
                    "Example: ANNIE G 05"
                ),
            )

            add_entry = st.form_submit_button(
                "Add entry",
                width="stretch",
            )

        if add_entry:
            try:
                create_survivor_entry(
                    new_entry_name
                )
                st.success(
                    (
                        "Entry added and set active. "
                        "You can now add its used teams and current pick."
                    )
                )
                st.rerun()
            except ValueError as exc:
                st.error(
                    str(
                        exc
                    )
                )

    section_header(
        "Import Full Pool",
        (
            "Drop the complete pool sheet to update every entry, "
            "weekly team usage and field ownership."
        ),
    )

    import_flash = st.session_state.pop(
        "survivor_pool_import_flash",
        None,
    )

    if import_flash:
        st.success(
            import_flash
        )

    if (
        isinstance(
            summary,
            dict,
        )
        and summary.get(
            "whole_pool_import"
        )
        and summary.get(
            "source_filename"
        )
    ):
        imported_rule = summary.get(
            "current_week_required_picks"
        )

        accepted_text = (
            "Current pool file accepted: "
            + str(
                summary.get(
                    "source_filename"
                )
            )
            + " · "
            + str(
                summary.get(
                    "parsed_entries",
                    0,
                )
            )
            + " entries · Week "
            + str(
                summary.get(
                    "pool_week",
                    current_week,
                )
            )
        )

        if imported_rule is not None:
            accepted_text += (
                " · "
                + str(
                    int(
                        imported_rule
                    )
                )
                + (
                    " pick required"
                    if int(
                        imported_rule
                    )
                    == 1
                    else " picks required"
                )
            )

        st.success(
            accepted_text
        )

    with st.expander(
        "Upload PDF / Excel / CSV",
        expanded=False,
    ):
        st.caption(
            (
                "Supported: PDF, XLSX and CSV. "
                "Your personal My Teams & Picks state is preserved separately."
            )
        )

        pool_file = st.file_uploader(
            "Pool file",
            type=[
                "pdf",
                "xlsx",
                "csv",
            ],
            key="survivor_pool_upload_file",
            help=(
                "Excel can be one row per entry (Week 1, Week 2...) "
                "or one row per pick (Entry, Week, Team)."
            ),
        )

        preview_key = "survivor_pool_upload_preview"

        if pool_file is not None:
            pool_bytes = pool_file.getvalue()
            pool_sha = hashlib.sha256(
                pool_bytes
            ).hexdigest()

            already_imported = (
                isinstance(
                    summary,
                    dict,
                )
                and summary.get(
                    "whole_pool_import"
                )
                and str(
                    summary.get(
                        "source_sha256"
                    )
                    or ""
                )
                == pool_sha
            )

            if already_imported:
                st.success(
                    (
                        "This pool file is already accepted and imported. "
                        "You do not need to upload or confirm it again."
                    )
                )

            preview = st.session_state.get(
                preview_key
            )

            preview_matches_file = (
                isinstance(
                    preview,
                    dict,
                )
                and preview.get(
                    "filename"
                )
                == pool_file.name
                and preview.get(
                    "sha256"
                )
                == pool_sha
            )

            if not preview_matches_file:
                try:
                    preview = parse_survivor_pool_upload(
                        pool_bytes,
                        pool_file.name,
                    )
                    st.session_state[
                        preview_key
                    ] = preview

                    if already_imported:
                        st.caption(
                            "Accepted file preview is shown below."
                        )
                    else:
                        st.success(
                            "Pool file preview is ready below. "
                            "Review it, then confirm the import."
                        )
                except Exception as exc:
                    st.session_state.pop(
                        preview_key,
                        None,
                    )
                    preview = None
                    st.error(
                        (
                            "Could not parse this pool file: "
                            + str(
                                exc
                            )
                        )
                    )
            else:
                if already_imported:
                    st.caption(
                        "Accepted file preview is shown below."
                    )
                else:
                    st.caption(
                        "Pool file preview is ready. "
                        "Nothing changes until you confirm the import."
                    )

            preview = st.session_state.get(
                preview_key
            )

            if (
                isinstance(
                    preview,
                    dict,
                )
                and preview.get(
                    "filename"
                )
                == pool_file.name
            ):
                meta = preview.get(
                    "meta",
                    {},
                )

                preview_cols = st.columns(
                    4
                )

                with preview_cols[0]:
                    st.markdown(
                        (
                            "**"
                            + str(
                                preview.get(
                                    "entry_count",
                                    0,
                                )
                            )
                            + "** entries"
                        )
                    )

                with preview_cols[1]:
                    st.markdown(
                        (
                            "**"
                            + str(
                                preview.get(
                                    "pick_rows",
                                    0,
                                )
                            )
                            + "** pick rows"
                        )
                    )

                with preview_cols[2]:
                    st.markdown(
                        (
                            "**Week "
                            + str(
                                preview.get(
                                    "max_week",
                                    0,
                                )
                            )
                            + "** max"
                        )
                    )

                with preview_cols[3]:
                    st.markdown(
                        (
                            "**"
                            + safe(
                                meta.get(
                                    "format",
                                    "FILE",
                                )
                            )
                            + "** format"
                        )
                    )

                sheet_names = meta.get(
                    "sheet_names"
                ) or []

                if sheet_names:
                    st.caption(
                        (
                            "Sheets: "
                            + " · ".join(
                                [
                                    str(
                                        name
                                    )
                                    for name
                                    in sheet_names
                                ]
                            )
                        )
                    )

                warnings = meta.get(
                    "warnings"
                ) or []

                if warnings:
                    st.warning(
                        (
                            "Some sheets were skipped: "
                            + " | ".join(
                                [
                                    str(
                                        warning
                                    )
                                    for warning
                                    in warnings[
                                        :4
                                    ]
                                ]
                            )
                        )
                    )

                duplicates = int(preview.get("duplicate_ticket_instances") or 0)
                if duplicates:
                    st.info(
                        str(duplicates)
                        + " repeated-name pool ticket(s) kept as separate entries."
                    )

                sample_rows = []

                for entry in (
                    preview.get(
                        "entries"
                    )
                    or []
                )[
                    :12
                ]:
                    picks = sorted(
                        entry.get(
                            "picks"
                        )
                        or [],
                        key=lambda item: item.get(
                            "week_position",
                            0,
                        ),
                    )

                    sample_rows.append(
                        {
                            "Entry":
                                entry.get(
                                    "entry_name"
                                ),
                            "Weeks":
                                len(
                                    picks
                                ),
                            "Last Pick":
                                (
                                    picks[
                                        -1
                                    ].get(
                                        "team"
                                    )
                                    if picks
                                    else None
                                ),
                            "Used Teams":
                                " · ".join(
                                    [
                                        str(
                                            pick.get(
                                                "team"
                                            )
                                        )
                                        for pick
                                        in picks
                                    ]
                                ),
                        }
                    )

                if sample_rows:
                    st.markdown(
                        "#### Import preview"
                    )
                    st.dataframe(
                        pd.DataFrame(
                            sample_rows
                        ),
                        width="stretch",
                        hide_index=True,
                    )

                if already_imported:
                    st.caption(
                        "Accepted pool file is already active. "
                        "Upload a different file only when the pool sends a new sheet."
                    )

                else:
                    confirm_import = st.checkbox(
                        (
                            "I reviewed the preview and want to replace "
                            "the current whole-pool field snapshot."
                        ),
                        key="survivor_pool_confirm_import",
                    )

                    if st.button(
                        "Confirm whole-pool import",
                        type="primary",
                        width="stretch",
                        disabled=(
                            not confirm_import
                        ),
                        key="survivor_pool_commit_button",
                    ):
                        try:
                            fresh_preview = parse_survivor_pool_upload(
                                pool_bytes,
                                pool_file.name,
                            )

                            if (
                                fresh_preview.get(
                                    "sha256"
                                )
                                != preview.get(
                                    "sha256"
                                )
                            ):
                                raise ValueError(
                                    (
                                        "The selected file changed after preview. "
                                        "Preview it again before importing."
                                    )
                                )

                            result = commit_survivor_pool_upload(
                                fresh_preview,
                                pool_bytes,
                            )

                            st.session_state.pop(
                                preview_key,
                                None,
                            )

                            st.session_state[
                                "survivor_pool_import_flash"
                            ] = (
                                "Pool file accepted and imported: "
                                + str(
                                    result.get(
                                        "entries",
                                        0,
                                    )
                                )
                                + " pool entries and "
                                + str(
                                    result.get(
                                        "ledger_rows",
                                        0,
                                    )
                                )
                                + " weekly picks. "
                                + "Your personal entry state was preserved."
                            )

                            st.rerun()

                        except Exception as exc:
                            st.error(
                                (
                                    "Pool import failed safely. "
                                    "The previous field snapshot was backed up. "
                                    + str(
                                        exc
                                    )
                                )
                            )


        else:
            st.info(
                (
                    "Choose a PDF, XLSX or CSV to preview the full field. "
                    "Nothing is replaced until you confirm the import."
                )
            )

    if (
        not active_name
        or strategy.empty
    ):
        st.info(
            "No current Survivor strategy board is available."
        )
        return

    board = strategy.copy()

    if "current_week" in board.columns:
        weeks = pd.to_numeric(
            board[
                "current_week"
            ],
            errors="coerce",
        )
        board = board[
            weeks.eq(
                current_week
            )
        ].copy()

    if "start" in board.columns:
        starts = pd.to_datetime(
            board[
                "start"
            ],
            errors="coerce",
            utc=True,
        )
        future_mask = (
            starts.isna()
            | (
                starts
                >= pd.Timestamp.now(
                    tz="UTC"
                )
                - pd.Timedelta(
                    hours=1
                )
            )
        )
        board = board[
            future_mask
        ].copy()

    board = board[
        ~board[
            "survivor_team"
        ].astype(str).isin(
            set(
                used
            )
        )
    ].copy()

    board["_sort"] = pd.to_numeric(
        board.get(
            "strategy_index"
        ),
        errors="coerce",
    )

    board = board.sort_values(
        "_sort",
        ascending=False,
    )

    signal_map = {
        "ELITE_MARKET":
            "elite market favorite",
        "STRONG_MARKET":
            "strong market favorite",
        "BIG_SPREAD":
            "large favorite spread",
        "HOME_FIELD":
            "home field",
        "RECENT_FORM":
            "strong recent form",
        "POINT_DIFF":
            "strong point differential",
        "REST":
            "rest advantage",
    }

    risk_map = {
        "ROAD_FAVORITE":
            "road favorite",
        "HIGH_WIND":
            "high wind",
        "WIND":
            "wind caution",
        "PRECIP":
            "precipitation risk",
        "PRECIP_CAUTION":
            "precipitation caution",
        "SHORT_REST":
            "short rest",
        "WEAK_FORM":
            "weak recent form",
        "NEG_POINT_DIFF":
            "negative point differential",
    }

    def _parts(
        value,
        mapping,
    ):
        return [
            mapping.get(
                token,
                token.replace(
                    "_",
                    " ",
                ).lower(),
            )
            for token in safe(
                value
            ).split(
                "|"
            )
            if token
            and token
            != "nan"
        ]

    def _kickoff(
        value,
    ):
        dt = pd.to_datetime(
            value,
            errors="coerce",
            utc=True,
        )

        if pd.isna(
            dt
        ):
            return "Time TBD"

        try:
            return (
                dt.tz_convert(
                    "America/New_York"
                )
                .strftime(
                    "%a %I:%M %p ET"
                )
                .replace(
                    " 0",
                    " ",
                )
            )
        except Exception:
            return safe(
                value
            )

    section_header(
        "Top 3 Options",
        (
            "Safety, current context and future value together — "
            "not just the biggest spread."
        ),
    )

    if board.empty:
        st.info(
            (
                "No unused Week "
                + str(
                    current_week
                )
                + " candidates are available."
            )
        )
    else:
        top = board[
            ~board[
                "strategy_action"
            ].astype(str).eq(
                "AVOID"
            )
        ].head(
            3
        )

        top_cols = st.columns(
            len(
                top
            )
        )

        for rank, (
            col,
            (
                _,
                row,
            ),
        ) in enumerate(
            zip(
                top_cols,
                top.iterrows(),
            ),
            start=1,
        ):
            positives = _parts(
                row.get(
                    "positive_signals"
                ),
                signal_map,
            )

            risks = _parts(
                row.get(
                    "risk_signals"
                ),
                risk_map,
            )

            reason = (
                "Market "
                + number(
                    row.get(
                        "market_prob_pct"
                    )
                )
                + "% · spread "
                + line_text(
                    row.get(
                        "survivor_spread"
                    )
                )
            )

            if positives:
                reason += (
                    " · "
                    + ", ".join(
                        positives[
                            :2
                        ]
                    )
                )

            if risks:
                reason += (
                    " · Risk: "
                    + risks[
                        0
                    ]
                )

            with col:
                premium_card(
                    (
                        "#"
                        + str(
                            rank
                        )
                        + " "
                        + safe(
                            row.get(
                                "survivor_team"
                            )
                        )
                    ),
                    (
                        "vs "
                        + safe(
                            row.get(
                                "opponent"
                            )
                        )
                        + " · "
                        + _kickoff(
                            row.get(
                                "start"
                            )
                        )
                    ),
                    friendly(
                        row.get(
                            "strategy_action"
                        )
                    ),
                    reason,
                    [
                        (
                            friendly(
                                row.get(
                                    "hulk_decision_tier"
                                )
                            ),
                            (
                                "green"
                                if rank
                                == 1
                                else "blue"
                            ),
                        ),
                        (
                            friendly(
                                row.get(
                                    "future_value_label"
                                )
                            ),
                            "amber",
                        ),
                    ],
                    "#059669",
                )

    with st.expander(
        "More strategy",
        expanded=False,
    ):
        st.markdown(
            "#### Use now vs save"
        )

        use_now = board[
            board[
                "strategy_action"
            ].astype(str).eq(
                "USE_NOW_VALUE"
            )
        ].head(
            5
        )

        save = board.copy()

        save["_future"] = pd.to_numeric(
            save.get(
                "future_value_index"
            ),
            errors="coerce",
        )

        save = save.sort_values(
            "_future",
            ascending=False,
        ).head(
            5
        )

        strategy_cols = st.columns(
            2
        )

        with strategy_cols[0]:
            st.markdown(
                "**Best to use now**"
            )

            if use_now.empty:
                st.caption(
                    "No clear use-now candidate."
                )
            else:
                for _, row in use_now.iterrows():
                    st.markdown(
                        (
                            "**"
                            + safe(
                                row.get(
                                    "survivor_team"
                                )
                            )
                            + "** — "
                            + number(
                                row.get(
                                    "market_prob_pct"
                                )
                            )
                            + "% market · "
                            + friendly(
                                row.get(
                                    "future_value_label"
                                )
                            )
                        )
                    )

        with strategy_cols[1]:
            st.markdown(
                "**Best to preserve**"
            )

            if save.empty:
                st.caption(
                    "No future-value candidates available."
                )
            else:
                for _, row in save.iterrows():
                    st.markdown(
                        (
                            "**"
                            + safe(
                                row.get(
                                    "survivor_team"
                                )
                            )
                            + "** — future "
                            + number(
                                row.get(
                                    "future_value_index"
                                )
                            )
                            + " · "
                            + friendly(
                                row.get(
                                    "future_value_label"
                                )
                            )
                        )
                    )

        future_cols = [
            col
            for col in [
                "survivor_team",
                "opponent",
                "strategy_action",
                "market_prob_pct",
                "survivor_spread",
                "future_value_index",
                "future_value_label",
                "next_four_week_schedule",
            ]
            if col
            in board.columns
        ]

        if future_cols:
            st.markdown(
                "#### Full candidate board"
            )
            st.dataframe(
                board[
                    future_cols
                ].head(
                    15
                ),
                width="stretch",
                hide_index=True,
            )

    with st.expander(
        "History & field details",
        expanded=False,
    ):
        st.markdown(
            (
                "**Pool:** "
                + str(
                    remaining
                )
                + " of "
                + str(
                    starting
                )
                + " remain · "
                + number(
                    survival_pct
                )
                + "% alive"
            )
        )

        entry_rows = []
        history_rows = []

        for name in owned_names:
            entry = entries.get(
                name,
                {},
            )

            entry_rows.append(
                {
                    "Entry":
                        name,
                    "Status":
                        safe(
                            entry.get(
                                "status"
                            )
                        ).upper(),
                    "Used":
                        len(
                            entry.get(
                                "used_teams"
                            )
                            or []
                        ),
                    "Used Teams":
                        " · ".join(
                            [
                                str(
                                    team
                                )
                                for team
                                in (
                                    entry.get(
                                        "used_teams"
                                    )
                                    or []
                                )
                            ]
                        ),
                }
            )

            for item in (
                entry.get(
                    "history"
                )
                or []
            ):
                history_rows.append(
                    {
                        "Entry":
                            name,
                        "Week":
                            item.get(
                                "week"
                            ),
                        "Team":
                            item.get(
                                "team"
                            ),
                        "Result":
                            item.get(
                                "result"
                            ),
                    }
                )

        if entry_rows:
            st.markdown(
                "#### My entries"
            )
            st.dataframe(
                pd.DataFrame(
                    entry_rows
                ),
                width="stretch",
                hide_index=True,
            )

        if history_rows:
            st.markdown(
                "#### Week-by-week picks"
            )
            st.dataframe(
                pd.DataFrame(
                    history_rows
                ).sort_values(
                    [
                        "Week",
                        "Entry",
                    ]
                ),
                width="stretch",
                hide_index=True,
            )

        if not pool_current.empty:
            st.markdown(
                "#### Imported full field"
            )

            field_cols = [
                col
                for col in [
                    "entry_name",
                    "status",
                    "weeks_recorded",
                    "last_pick",
                    "used_teams",
                ]
                if col
                in pool_current.columns
            ]

            st.dataframe(
                pool_current[
                    field_cols
                ].head(
                    100
                ),
                width="stretch",
                hide_index=True,
            )

        if not pool_ownership.empty:
            ownership_view = pool_ownership.copy()

            ownership_view[
                "_week"
            ] = pd.to_numeric(
                ownership_view.get(
                    "week_position"
                ),
                errors="coerce",
            )

            latest_week = ownership_view[
                "_week"
            ].dropna().max()

            if pd.notna(
                latest_week
            ):
                ownership_view = ownership_view[
                    ownership_view[
                        "_week"
                    ].eq(
                        latest_week
                    )
                ].copy()

            ownership_view[
                "_share"
            ] = pd.to_numeric(
                ownership_view.get(
                    "pick_share_pct"
                ),
                errors="coerce",
            )

            ownership_view = ownership_view.sort_values(
                "_share",
                ascending=False,
            )

            st.markdown(
                (
                    "#### Latest imported field ownership"
                    + (
                        " — Week "
                        + str(
                            int(
                                latest_week
                            )
                        )
                        if pd.notna(
                            latest_week
                        )
                        else ""
                    )
                )
            )

            show_cols = [
                col
                for col in [
                    "team",
                    "pick_count",
                    "pool_rows_with_pick",
                    "pick_share_pct",
                ]
                if col
                in ownership_view.columns
            ]

            st.dataframe(
                ownership_view[
                    show_cols
                ].head(
                    20
                ),
                width="stretch",
                hide_index=True,
            )

        elif not ownership.empty:
            st.markdown(
                "#### Previous field ownership"
            )
            st.dataframe(
                ownership.head(
                    20
                ),
                width="stretch",
                hide_index=True,
            )

        if not pairs.empty:
            st.markdown(
                "#### Previous common pick pairs"
            )
            st.dataframe(
                pairs.head(
                    20
                ),
                width="stretch",
                hide_index=True,
            )


def render_fantasy(
    sport="NFL",
):
    if sport in {
        "CFB",
        "CBB",
    }:
        render_college_no_fantasy(
            sport
        )
        return

    page_intro(
        f"{sport} Fantasy",
        "fantasy",
        sport,
        (
            "Who to start, add, stash or stream. "
            "Deeper research stays underneath."
        ),
    )

    if sport != "NFL":
        empty_card(
            "Fantasy",
            (
                "Current fantasy research for this sport "
                "is available from its sport-specific page."
            ),
            SPORTS.get(
                sport,
                {},
            ).get(
                "accent",
                "#EA7C22",
            ),
        )
        return

    data = nfl_fantasy().copy()

    decision_dir = (
        "/home/ubuntu/sports-hulk/"
        "intelligence_warehouse/fantasy_decisions/"
    )

    def _fantasy_file(
        name,
    ):
        try:
            return pd.read_csv(
                decision_dir
                + name,
                low_memory=False,
            )
        except Exception:
            return pd.DataFrame()

    weekly = _fantasy_file(
        "FANTASY_WEEKLY_DECISIONS_CURRENT.csv"
    )
    faab = _fantasy_file(
        "FANTASY_FAAB_RESEARCH_CURRENT.csv"
    )
    stash = _fantasy_file(
        "FANTASY_IR_STASH_CURRENT.csv"
    )
    defenses = _fantasy_file(
        "FANTASY_DEFENSE_STREAMING_CURRENT.csv"
    )
    idp = _fantasy_file(
        "FANTASY_IDP_OPPORTUNITY_CURRENT.csv"
    )

    weekly_nfl = (
        weekly[
            weekly["sport"].astype(str).eq(
                "NFL"
            )
        ].copy()
        if (
            not weekly.empty
            and "sport" in weekly.columns
        )
        else pd.DataFrame()
    )

    faab_nfl = (
        faab[
            faab["sport"].astype(str).eq(
                "NFL"
            )
        ].copy()
        if (
            not faab.empty
            and "sport" in faab.columns
        )
        else pd.DataFrame()
    )

    stash_nfl = (
        stash[
            stash["sport"].astype(str).eq(
                "NFL"
            )
        ].copy()
        if (
            not stash.empty
            and "sport" in stash.columns
        )
        else pd.DataFrame()
    )

    tier_labels = {
        "CORE_START_RESEARCH":
            "Start research",
        "STRONG_START_RESEARCH":
            "Strong start research",
        "FLEX_START_RESEARCH":
            "Flex / matchup research",
        "START_RESEARCH":
            "Start research",
        "WATCH":
            "Watch",
        "HOLD_REVIEW":
            "Review",
        "INACTIVE":
            "Inactive",
    }

    section_header(
        "This Week",
        (
            "Best current start research by position. "
            "Generic until your league roster is connected."
        ),
    )

    if weekly_nfl.empty:
        st.info(
            "No current weekly fantasy decision board is available."
        )
    else:
        weekly_nfl["_weekly"] = pd.to_numeric(
            weekly_nfl.get(
                "weekly_research_score"
            ),
            errors="coerce",
        )

        start_rows = []

        for position in [
            "QB",
            "RB",
            "WR",
            "TE",
        ]:
            group = weekly_nfl[
                weekly_nfl[
                    "position"
                ].astype(str).eq(
                    position
                )
                & ~weekly_nfl[
                    "weekly_tier"
                ].astype(str).eq(
                    "INACTIVE"
                )
            ].sort_values(
                "_weekly",
                ascending=False,
            ).head(
                1
            )

            if not group.empty:
                start_rows.append(
                    group.iloc[
                        0
                    ].to_dict()
                )

        cols = st.columns(
            max(
                1,
                len(
                    start_rows
                ),
            )
        )

        for col, row in zip(
            cols,
            start_rows,
        ):
            weekly_tier = safe(
                row.get(
                    "weekly_tier"
                )
            )

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
                        + " vs "
                        + safe(
                            row.get(
                                "opponent"
                            )
                        )
                    ),
                    tier_labels.get(
                        weekly_tier,
                        friendly(
                            weekly_tier
                        ),
                    ),
                    safe(
                        row.get(
                            "research_reasons",
                            "Current role and matchup research.",
                        )
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
                        (
                            friendly(
                                row.get(
                                    "defensive_pressure_context"
                                )
                            ),
                            "blue",
                        ),
                    ],
                    "#EA7C22",
                )

    section_header(
        "Waiver & FAAB",
        (
            "The three adds most worth your attention right now."
        ),
    )

    waiver = pd.DataFrame()

    if not faab_nfl.empty:
        waiver = faab_nfl[
            faab_nfl[
                "waiver_priority"
            ].astype(str).isin(
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

    if waiver.empty:
        st.info(
            "No current waiver add clears the research filters."
        )
    else:
        cols = st.columns(
            min(
                3,
                len(
                    waiver
                ),
            )
        )

        for col, (_, row) in zip(
            cols,
            waiver.head(
                3
            ).iterrows(),
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
                        + "% · add rank "
                        + number(
                            row.get(
                                "add_rank_24h"
                            ),
                            0,
                        )
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

    section_header(
        "IR & Return Stash",
        (
            "Best injured-player stashes with return timing kept explicit."
        ),
    )

    stash_show = pd.DataFrame()

    if not stash_nfl.empty:
        stash_show = stash_nfl[
            stash_nfl[
                "stash_tier"
            ].astype(str).isin(
                [
                    "HIGH_PRIORITY_STASH",
                    "STRONG_STASH",
                    "WATCH_STASH",
                    "REVIEW_SOURCE_CONFLICT",
                ]
            )
        ].copy()

        stash_show["_score"] = pd.to_numeric(
            stash_show.get(
                "stash_research_score"
            ),
            errors="coerce",
        )

        stash_show = stash_show.sort_values(
            [
                "source_disagreement",
                "_score",
            ],
            ascending=[
                True,
                False,
            ],
        )

    if stash_show.empty:
        st.info(
            "No current NFL stash candidate clears the return filters."
        )
    else:
        cols = st.columns(
            min(
                3,
                len(
                    stash_show
                ),
            )
        )

        for col, (_, row) in zip(
            cols,
            stash_show.head(
                3
            ).iterrows(),
        ):
            with col:
                conflict = bool(
                    row.get(
                        "source_disagreement"
                    )
                )

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
                            (
                                "Source conflict"
                                if conflict
                                else "Return research"
                            ),
                            (
                                "amber"
                                if conflict
                                else "blue"
                            ),
                        ),
                    ],
                    "#EA7C22",
                )

    section_header(
        "Defense Stream",
        (
            "Best one-week D/ST options, with hold value shown separately."
        ),
    )

    dst = pd.DataFrame()

    if not defenses.empty:
        dst = defenses.copy()

        dst["_score"] = pd.to_numeric(
            dst.get(
                "weekly_stream_score"
            ),
            errors="coerce",
        )

        dst = dst.sort_values(
            "_score",
            ascending=False,
        )

    if dst.empty:
        st.info(
            "No defense streaming board is available."
        )
    else:
        cols = st.columns(
            min(
                3,
                len(
                    dst
                ),
            )
        )

        for col, (_, row) in zip(
            cols,
            dst.head(
                3
            ).iterrows(),
        ):
            with col:
                premium_card(
                    safe(
                        row.get(
                            "dst_player"
                        )
                    ),
                    (
                        "vs "
                        + safe(
                            row.get(
                                "next_opponent"
                            )
                        )
                    ),
                    friendly(
                        row.get(
                            "weekly_stream_tier"
                        )
                    ),
                    (
                        "This week "
                        + number(
                            row.get(
                                "weekly_stream_score"
                            )
                        )
                        + " · multi-week "
                        + number(
                            row.get(
                                "multiweek_hold_score"
                            )
                        )
                    ),
                    [
                        (
                            friendly(
                                row.get(
                                    "multiweek_hold_tier"
                                )
                            ),
                            "blue",
                        ),
                    ],
                    "#EA7C22",
                )

    with st.expander(
        "More fantasy research",
        expanded=False,
    ):
        if not weekly_nfl.empty:
            st.markdown(
                "#### Full Start / Sit board"
            )

            weekly_cols = [
                col
                for col in [
                    "player",
                    "team",
                    "position",
                    "opponent",
                    "weekly_tier",
                    "weekly_research_score",
                    "recent_role_value",
                    "snap_pct",
                    "role_signal",
                    "defensive_pressure_context",
                    "availability_status",
                    "research_reasons",
                ]
                if col
                in weekly_nfl.columns
            ]

            st.dataframe(
                weekly_nfl[
                    weekly_cols
                ].sort_values(
                    "weekly_research_score",
                    ascending=False,
                ),
                width="stretch",
                hide_index=True,
            )

            st.markdown(
                "#### Rest-of-season board"
            )

            ros_cols = [
                col
                for col in [
                    "player",
                    "team",
                    "position",
                    "ros_tier",
                    "ros_research_score",
                    "future_schedule_signal",
                    "next_opponents",
                ]
                if col
                in weekly_nfl.columns
            ]

            st.dataframe(
                weekly_nfl[
                    ros_cols
                ].sort_values(
                    "ros_research_score",
                    ascending=False,
                ).head(
                    30
                ),
                width="stretch",
                hide_index=True,
            )

        if not data.empty:
            st.markdown(
                "#### Usage movers"
            )

            usage_cols = [
                col
                for col in [
                    "player",
                    "team",
                    "position",
                    "fantasy_trend",
                    "latest_offense_pct",
                    "offense_pct_change",
                    "targets_l2_avg",
                    "carries_l2_avg",
                    "receiving_yards_l2_avg",
                    "rushing_yards_l2_avg",
                    "availability_flag",
                ]
                if col
                in data.columns
            ]

            st.dataframe(
                data[
                    usage_cols
                ].head(
                    30
                ),
                width="stretch",
                hide_index=True,
            )

        if not waiver.empty:
            st.markdown(
                "#### Full waiver / FAAB board"
            )

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

        if not dst.empty:
            st.markdown(
                "#### Full defense streaming board"
            )

            st.dataframe(
                dst.drop(
                    columns=[
                        "_score"
                    ],
                    errors="ignore",
                ),
                width="stretch",
                hide_index=True,
            )

        if not idp.empty:
            idp_show = idp[
                idp[
                    "idp_usage_tier"
                ].astype(str).isin(
                    [
                        "IDP_CORE_USAGE",
                        "IDP_STRONG_USAGE",
                        "IDP_WATCH",
                    ]
                )
            ].copy()

            idp_show["_score"] = pd.to_numeric(
                idp_show.get(
                    "idp_usage_score"
                ),
                errors="coerce",
            )

            idp_show = idp_show.sort_values(
                "_score",
                ascending=False,
            )

            st.markdown(
                "#### IDP opportunity"
            )

            idp_cols = [
                col
                for col in [
                    "player",
                    "team",
                    "position",
                    "idp_group",
                    "snap_pct",
                    "snap_pct_change",
                    "role_signal",
                    "next_opponent",
                    "idp_usage_tier",
                ]
                if col
                in idp_show.columns
            ]

            st.dataframe(
                idp_show[
                    idp_cols
                ].head(
                    40
                ),
                width="stretch",
                hide_index=True,
            )


def render_dfs(
    sport="NFL",
):
    page_intro(
        f"{sport} DFS",
        "fantasy",
        sport,
        (
            "Top values, clean stacks and lineup research. "
            "One platform at a time."
        ),
    )

    dfs_dir = (
        "/home/ubuntu/sports-hulk/"
        "intelligence_warehouse/dfs/"
    )

    def _dfs_file(
        name,
    ):
        try:
            return pd.read_csv(
                dfs_dir
                + name,
                low_memory=False,
            )
        except Exception:
            return pd.DataFrame()

    archetypes = _dfs_file(
        "DFS_CONTEST_ARCHETYPES_CURRENT.csv"
    )
    stacks = _dfs_file(
        "DFS_STACK_RESEARCH_CURRENT.csv"
    )
    fd_nfl_lineups = _dfs_file(
        "DFS_NFL_LINEUP_RESEARCH_CURRENT.csv"
    )
    dk_nfl_lineups = _dfs_file(
        "DFS_DK_NFL_LINEUP_RESEARCH_CURRENT.csv"
    )
    dk_leverage = _dfs_file(
        "DFS_DK_LEVERAGE_CURRENT.csv"
    )
    mlb_nhl_lineups = _dfs_file(
        "DFS_MLB_NHL_LINEUP_RESEARCH_CURRENT.csv"
    )

    sport_key = safe(
        sport
    ).upper()

    current = (
        archetypes[
            archetypes[
                "sport"
            ].astype(str).str.upper().eq(
                sport_key
            )
        ].copy()
        if (
            not archetypes.empty
            and "sport"
            in archetypes.columns
        )
        else pd.DataFrame()
    )

    if current.empty:
        st.info(
            (
                "No current verified "
                + sport_key
                + " DFS slate is available."
            )
        )
        return

    platform_values = []

    if current[
        "platform"
    ].astype(str).str.upper().eq(
        "FANDUEL"
    ).any():
        platform_values.append(
            "FanDuel"
        )

    if current[
        "platform"
    ].astype(str).str.upper().eq(
        "DRAFTKINGS"
    ).any():
        platform_values.append(
            "DraftKings"
        )

    if not platform_values:
        st.info(
            "No current DFS platform feed is available."
        )
        return

    if len(
        platform_values
    ) > 1:
        platform_label = st.pills(
            "DFS platform",
            platform_values,
            default=platform_values[
                0
            ],
            required=True,
            label_visibility="collapsed",
            key=(
                "dfs_platform_"
                + sport_key
            ),
        )
    else:
        platform_label = platform_values[
            0
        ]
        st.caption(
            platform_label
            + " current slate"
        )

    platform_key = (
        "FANDUEL"
        if platform_label
        == "FanDuel"
        else "DRAFTKINGS"
    )

    if sport_key == "NFL":
        dfs_view = st.pills(
            "DFS view",
            [
                "Research",
                "Lineup Builder",
            ],
            default="Research",
            required=True,
            label_visibility="collapsed",
            key=(
                "dfs_view_"
                + platform_key
            ),
        )

        if dfs_view == "Lineup Builder":
            from premium_ui.dfs_builder_ui import (
                render_nfl_lineup_builder,
            )

            render_nfl_lineup_builder(
                archetypes,
                platform_key,
            )
            return

    selected = current[
        current[
            "platform"
        ].astype(str).str.upper().eq(
            platform_key
        )
    ].copy()

    selected["_proj"] = pd.to_numeric(
        selected.get(
            "projected_fantasy_points"
        ),
        errors="coerce",
    )
    selected["_value"] = pd.to_numeric(
        selected.get(
            "audit_value_per_1000"
        ),
        errors="coerce",
    )
    selected["_proj_pct"] = pd.to_numeric(
        selected.get(
            "projection_percentile"
        ),
        errors="coerce",
    )
    selected["_value_pct"] = pd.to_numeric(
        selected.get(
            "value_percentile"
        ),
        errors="coerce",
    )

    selected["_display_score"] = (
        selected[
            "_proj_pct"
        ].fillna(
            0
        )
        + selected[
            "_value_pct"
        ].fillna(
            0
        )
    )

    featured = selected[
        selected[
            "_proj"
        ].notna()
        & ~selected[
            "contest_archetype"
        ].astype(str).eq(
            "AVOID_AVAILABILITY_RISK"
        )
    ].sort_values(
        [
            "_display_score",
            "_proj",
        ],
        ascending=[
            False,
            False,
        ],
    )

    section_header(
        "Top Values",
        (
            "Best blend of projection and salary value "
            "with current availability gates applied."
        ),
    )

    if featured.empty:
        st.info(
            (
                "No current "
                + platform_label
                + " projection clears the value filters."
            )
        )
    else:
        value_cols = st.columns(
            min(
                3,
                len(
                    featured
                ),
            )
        )

        for col, (_, row) in zip(
            value_cols,
            featured.head(
                3
            ).iterrows(),
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
                    (
                        number(
                            row.get(
                                "projected_fantasy_points"
                            )
                        )
                        + " proj"
                    ),
                    (
                        "$"
                        + number(
                            row.get(
                                "salary"
                            ),
                            0,
                        )
                        + " · "
                        + number(
                            row.get(
                                "audit_value_per_1000"
                            ),
                            2,
                        )
                        + " / $1K"
                    ),
                    [
                        (
                            friendly(
                                row.get(
                                    "contest_archetype"
                                )
                            ),
                            "green",
                        ),
                        (
                            friendly(
                                row.get(
                                    "context_signal"
                                )
                            ),
                            "blue",
                        ),
                    ],
                    SPORTS.get(
                        sport_key,
                        {},
                    ).get(
                        "accent",
                        "#54C6EB",
                    ),
                )

    clean_stacks = pd.DataFrame()

    if (
        platform_key
        == "FANDUEL"
        and not stacks.empty
    ):
        clean_stacks = stacks[
            stacks[
                "sport"
            ].astype(str).str.upper().eq(
                sport_key
            )
            & stacks[
                "research_eligible"
            ].astype(str).str.lower().eq(
                "true"
            )
        ].copy()

        clean_stacks["_score"] = pd.to_numeric(
            clean_stacks.get(
                "stack_research_score"
            ),
            errors="coerce",
        )

        clean_stacks = clean_stacks.sort_values(
            "_score",
            ascending=False,
        )

        if not clean_stacks.empty:
            section_header(
                "Best Stacks",
                (
                    "Only clean stacks with no current "
                    "availability or role-risk flag."
                ),
            )

            stack_cols = st.columns(
                min(
                    3,
                    len(
                        clean_stacks
                    ),
                )
            )

            for col, (_, row) in zip(
                stack_cols,
                clean_stacks.head(
                    3
                ).iterrows(),
            ):
                with col:
                    premium_card(
                        (
                            safe(
                                row.get(
                                    "team"
                                )
                            )
                            + " "
                            + friendly(
                                row.get(
                                    "stack_type"
                                )
                            )
                        ),
                        (
                            "vs "
                            + safe(
                                row.get(
                                    "opponent"
                                )
                            )
                        ),
                        (
                            "Stack "
                            + number(
                                row.get(
                                    "stack_research_score"
                                )
                            )
                        ),
                        safe(
                            row.get(
                                "members"
                            )
                        ),
                        [
                            (
                                "Clean",
                                "green",
                            ),
                        ],
                        "#0F9F9A",
                    )

    lineup_data = pd.DataFrame()
    lineup_title = ""

    if (
        sport_key
        == "NFL"
        and platform_key
        == "FANDUEL"
    ):
        lineup_data = fd_nfl_lineups.copy()
        lineup_title = (
            "Top FanDuel Lineup Builds"
        )

        if (
            not lineup_data.empty
            and "balanced_research_score"
            in lineup_data.columns
        ):
            lineup_data = lineup_data.sort_values(
                "balanced_research_score",
                ascending=False,
            )

    elif (
        sport_key
        == "NFL"
        and platform_key
        == "DRAFTKINGS"
    ):
        lineup_data = dk_nfl_lineups.copy()
        lineup_title = (
            "Top DraftKings Lineup Builds"
        )

        if (
            not lineup_data.empty
            and "balanced_research_score"
            in lineup_data.columns
        ):
            lineup_data = lineup_data.sort_values(
                "balanced_research_score",
                ascending=False,
            )

    elif (
        sport_key
        in {
            "MLB",
            "NHL",
        }
        and platform_key
        == "FANDUEL"
        and not mlb_nhl_lineups.empty
    ):
        lineup_data = mlb_nhl_lineups[
            mlb_nhl_lineups[
                "sport"
            ].astype(str).str.upper().eq(
                sport_key
            )
        ].copy()

        lineup_title = (
            "Top FanDuel Lineup Builds"
        )

        if (
            not lineup_data.empty
            and "research_score"
            in lineup_data.columns
        ):
            lineup_data = lineup_data.sort_values(
                "research_score",
                ascending=False,
            )

    if not lineup_data.empty:
        section_header(
            lineup_title,
            (
                "Rule-checked research candidates. "
                "Nothing is submitted automatically."
            ),
        )

        lineup_cols = st.columns(
            min(
                3,
                len(
                    lineup_data
                ),
            )
        )

        for col, (_, row) in zip(
            lineup_cols,
            lineup_data.head(
                3
            ).iterrows(),
        ):
            with col:
                strategy = safe(
                    row.get(
                        "stack_pattern",
                        row.get(
                            "strategy_flags",
                            "Balanced",
                        ),
                    )
                )

                salary_cap = pd.to_numeric(
                    row.get(
                        "salary_cap"
                    ),
                    errors="coerce",
                )

                salary_text = (
                    "$"
                    + number(
                        row.get(
                            "salary_used"
                        ),
                        0,
                    )
                )

                if pd.notna(
                    salary_cap
                ):
                    salary_text += (
                        " / $"
                        + number(
                            salary_cap,
                            0,
                        )
                    )

                premium_card(
                    friendly(
                        strategy
                    ),
                    platform_label,
                    (
                        number(
                            row.get(
                                "projected_fantasy_points"
                            )
                        )
                        + " proj"
                    ),
                    (
                        salary_text
                        + " · "
                        + safe(
                            row.get(
                                "players"
                            )
                        )
                    ),
                    [
                        (
                            "Research only",
                            "amber",
                        ),
                    ],
                    "#EA7C22",
                )

    with st.expander(
        "More DFS research",
        expanded=False,
    ):
        st.markdown(
            "#### Full player board"
        )

        show_cols = [
            col
            for col in [
                "player",
                "team",
                "position",
                "salary",
                "projected_fantasy_points",
                "audit_value_per_1000",
                "contest_archetype",
                "context_signal",
                "availability_status",
                "salary_change",
                "modelled_ownership_pct",
            ]
            if col
            in selected.columns
        ]

        st.dataframe(
            (
                selected.sort_values(
                    "_display_score",
                    ascending=False,
                )[
                    show_cols
                ]
                if "_display_score"
                in selected.columns
                else selected[
                    show_cols
                ]
            ),
            width="stretch",
            hide_index=True,
        )

        if not clean_stacks.empty:
            st.markdown(
                "#### Full stack board"
            )
            st.dataframe(
                clean_stacks.drop(
                    columns=[
                        "_score"
                    ],
                    errors="ignore",
                ),
                width="stretch",
                hide_index=True,
            )

        if not lineup_data.empty:
            st.markdown(
                "#### All lineup research"
            )
            st.dataframe(
                lineup_data,
                width="stretch",
                hide_index=True,
            )

        if (
            sport_key
            == "NFL"
            and platform_key
            == "DRAFTKINGS"
            and not dk_leverage.empty
        ):
            leverage = dk_leverage.copy()

            leverage["_score"] = pd.to_numeric(
                leverage.get(
                    "leverage_research_score"
                ),
                errors="coerce",
            )

            leverage = leverage.sort_values(
                "_score",
                ascending=False,
            )

            st.markdown(
                "#### DraftKings leverage"
            )
            st.caption(
                (
                    "Ownership is modelled/heuristic, "
                    "not observed field ownership."
                )
            )

            leverage_cols = [
                col
                for col in [
                    "player",
                    "position",
                    "team",
                    "salary",
                    "projected_fantasy_points",
                    "modelled_ownership_pct",
                    "leverage_research_score",
                    "leverage_tier",
                ]
                if col
                in leverage.columns
            ]

            st.dataframe(
                leverage[
                    leverage_cols
                ].head(
                    50
                ),
                width="stretch",
                hide_index=True,
            )

    if platform_key == "DRAFTKINGS":
        st.caption(
            (
                "DraftKings ownership is stored only as a "
                "modelled heuristic and is not treated as "
                "verified field ownership or used for automatic model changes."
            )
        )


def render_news(
    sport="ALL",
):
    page_intro(
        (
            "Sports News"
            if sport == "ALL"
            else f"{sport} News"
        ),
        "news",
        sport,
        (
            "Verified source reports plus original "
            "Sports HULK analysis drafts."
        ),
    )

    news = sports_news_current()
    drafts = sports_article_drafts()

    if sport != "ALL":
        if not news.empty:
            news = news[
                news["sport"].astype(str).eq(
                    sport
                )
            ].copy()

        if not drafts.empty:
            drafts = drafts[
                drafts["sport"].astype(str).eq(
                    sport
                )
            ].copy()

    section_header(
        "Breaking & Context",
        (
            "Injuries, transactions, lineup changes, "
            "fantasy news, recaps and other developments."
        ),
    )

    if news.empty:
        st.info(
            "No current sourced sports news is available."
        )
    else:
        news = news.copy()

        priority = {
            "INJURY": 0,
            "TRANSACTION": 1,
            "LINEUP_ROLE": 2,
            "FANTASY": 3,
            "RECAP": 4,
            "RANKINGS": 5,
            "NEWS": 6,
        }

        news["_priority"] = (
            news["news_type"]
            .astype(str)
            .map(priority)
            .fillna(9)
        )

        news["_published"] = pd.to_datetime(
            news["published_at"],
            utc=True,
            errors="coerce",
        )

        news = news.sort_values(
            [
                "_priority",
                "_published",
            ],
            ascending=[
                True,
                False,
            ],
        ).head(
            15
        )

        for start in range(
            0,
            len(news),
            3,
        ):
            cols = st.columns(3)

            for col, (_, row) in zip(
                cols,
                news.iloc[
                    start:start + 3
                ].iterrows(),
            ):
                with col:
                    news_type = safe(
                        row.get(
                            "news_type"
                        )
                    )

                    tone = (
                        "amber"
                        if news_type
                        in {
                            "INJURY",
                            "TRANSACTION",
                            "LINEUP_ROLE",
                        }
                        else "blue"
                    )

                    premium_card(
                        safe(
                            row.get(
                                "headline"
                            )
                        ),
                        (
                            safe(
                                row.get(
                                    "sport"
                                )
                            )
                            + " · "
                            + safe(
                                row.get(
                                    "source"
                                )
                            )
                        ),
                        friendly(
                            news_type
                        ),
                        safe(
                            row.get(
                                "description"
                            )
                        ),
                        [
                            (
                                friendly(
                                    news_type
                                ),
                                tone,
                            ),
                            (
                                "Source preserved",
                                "green",
                            ),
                        ],
                        "#EF5A68",
                    )

                    url = safe(
                        row.get(
                            "source_url"
                        )
                    )

                    if url:
                        st.link_button(
                            "Open source",
                            url,
                            width="stretch",
                        )

    section_header(
        "Sports HULK Article Drafts",
        (
            "Original analysis generated from HULK intelligence "
            "and sourced facts. Human approval is required."
        ),
    )

    if drafts.empty:
        st.info(
            "No HULK article drafts are available right now."
        )
    else:
        drafts = drafts.copy()

        drafts["_updated"] = pd.to_datetime(
            drafts["updated_at"],
            utc=True,
            errors="coerce",
        )

        drafts = drafts.sort_values(
            "_updated",
            ascending=False,
        ).head(
            12
        )

        for _, row in drafts.iterrows():
            title = safe(
                row.get(
                    "title"
                )
            )

            status = safe(
                row.get(
                    "status"
                )
            )

            article_type = friendly(
                row.get(
                    "article_type"
                )
            )

            with st.expander(
                (
                    f"{title} · "
                    f"{article_type} · "
                    f"{status}"
                )
            ):
                dek = safe(
                    row.get(
                        "dek"
                    )
                )

                if dek:
                    st.caption(
                        dek
                    )

                body = safe(
                    row.get(
                        "body_markdown"
                    )
                )

                if body:
                    st.markdown(
                        body
                    )

                source_urls = []

                try:
                    source_urls = json.loads(
                        row.get(
                            "source_urls"
                        )
                        or "[]"
                    )
                except Exception:
                    source_urls = []

                for index, url in enumerate(
                    source_urls[
                        :3
                    ]
                ):
                    if url:
                        st.link_button(
                            (
                                "Open supporting source"
                                if index == 0
                                else
                                f"Open supporting source {index + 1}"
                            ),
                            str(url),
                        )

                st.caption(
                    (
                        "Draft only · Human approval required · "
                        "External article bodies are not copied."
                    )
                )


# ============================================================
# SPORTS HUB
# ============================================================

def render_sports():
    page_intro(
        "Sports",
        "today",
        "ALL",
        (
            "One consistent experience across "
            "every supported sport."
        ),
    )

    section_header(
        "Choose a Sport",
        "Same clean controls. Different intelligence.",
    )

    status = {
        "NFL":
            (
                "Live",
                "Picks, props, PrizePicks, fantasy, parlays, Survivor and news.",
                "green",
            ),

        "MLB":
            (
                "Live",
                "Games, picks, props, PrizePicks, fantasy, parlays and live scores.",
                "green",
            ),

        "CFB":
            (
                "Live",
                "Games, team-level picks, parlays, rankings, research and live scores.",
                "green",
            ),

        "NBA":
            (
                "Live",
                "Games, picks, props, PrizePicks, fantasy, parlays and live scores.",
                "green",
            ),

        "CBB":
            (
                "Live",
                "Games, team-level picks, parlays, rankings, research and live scores.",
                "green",
            ),

        "NHL":
            (
                "Live",
                "Games, picks, props, PrizePicks, fantasy, parlays and live scores.",
                "green",
            ),
    }

    sports = list(
        SPORTS.keys()
    )

    for start in range(
        0,
        len(sports),
        3,
    ):
        cols = st.columns(3)

        for col, sport in zip(
            cols,
            sports[
                start:start + 3
            ],
        ):
            state, body, tone = status[
                sport
            ]

            with col:
                premium_card(
                    SPORTS[
                        sport
                    ][
                        "label"
                    ],
                    state,
                    "Ready",
                    body,
                    [
                        (
                            state,
                            tone,
                        ),
                    ],
                    SPORTS[
                        sport
                    ][
                        "accent"
                    ],
                )


# ============================================================
# PREPARED / COLLEGE
# ============================================================

def render_prepared_sport(
    sport,
    compact=False,
):
    config = SPORTS.get(
        sport,
        {},
    )

    accent = config.get(
        "accent",
        "#4F8CFF",
    )

    if not compact:
        section_header(
            f"{sport} Experience",
            (
                "The premium interface is ready. "
                "Verified data activates each section."
            ),
        )

    if sport in {
        "CFB",
        "CBB",
    }:
        body = (
            "Games, picks, parlays, rankings, "
            "research and news are prepared. "
            "Player props and fantasy are intentionally excluded."
        )
    else:
        body = (
            "Games, picks, player props, fantasy, "
            "parlays and news are prepared for this sport."
        )

    empty_card(
        f"{sport} Intelligence",
        body,
        accent,
    )


def render_college_no_props(
    sport,
):
    page_intro(
        f"{sport} Picks",
        "college",
        sport,
        (
            "College sports stay focused on "
            "game-level intelligence."
        ),
    )

    empty_card(
        "No Player Props",
        (
            "Sports HULK intentionally does not "
            "include college player props."
        ),
        SPORTS[
            sport
        ][
            "accent"
        ],
    )


def render_college_no_fantasy(
    sport,
):
    page_intro(
        sport,
        "college",
        sport,
        (
            "College sports stay focused on "
            "games and team-level research."
        ),
    )

    empty_card(
        "No College Fantasy",
        (
            "Sports HULK intentionally does not "
            "include fantasy tools for college sports."
        ),
        SPORTS[
            sport
        ][
            "accent"
        ],
    )


# ============================================================
# PREMIUM ROUTER
# ============================================================

def dispatch_premium_page(
    page,
):
    page = str(
        page or ""
    ).strip()

    lower = page.lower()

    if page in {
        "Dashboard",
        "Home",
        "Today",
        "Overview",
    }:
        render_today()
        return True

    if page == "Sports":
        render_sports()
        return True

    if page == "Picks":
        render_picks("NFL")
        return True

    if page == "News":
        render_news()
        return True

    # PREMIUM_MEMBER_ROUTE_BUILD_3
    if page in {
        "My",
        "My Sports",
        "My Alerts",
        "Account",
    }:
        from premium_ui.member_ui import render_member_center
        render_member_center()
        return True

    if page == "NFL Best Bets":
        render_picks("NFL")
        return True

    if page == "MLB Best Bets":
        from premium_ui.mlb_ui import render_mlb_picks
        render_mlb_picks()
        return True

    if page == "CFB Best Bets":
        render_picks("CFB")
        return True

    if page == "NFL Player Props":
        render_props("NFL")
        return True

    if page == "PrizePicks Dashboard":
        render_props(
            "NFL",
            start_pickem=True,
        )
        return True

    if page == "NFL Parlays":
        render_parlays("NFL")
        return True

    if "survivor" in lower:
        render_survivor()
        return True

    if page in {
        "Fantasy",
        "Fantasy Football",
        "NFL Fantasy",
    }:
        render_fantasy("NFL")
        return True

    return False
