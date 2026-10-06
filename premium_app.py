from textwrap import dedent
import streamlit as st

from premium_ui.html_render import html

from premium_ui.components import (
    brand_header,
    render_html,
)

from premium_ui.ask_sports_hulk import (
    ask_sports_hulk_dialog,
    render_ask_sports_hulk,
)

from premium_ui.final_routes import (
    feature_options,
    render_feature,
)

from premium_ui.member_ui import (
    render_member_center,
)

from premium_ui.pages import (
    render_news,
    render_prizepicks,
    render_today,
)

from premium_ui.sport_config import (
    SPORTS,
)

from premium_ui.theme import (
    apply_premium_theme,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Sports HULK",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_premium_theme()


# ============================================================
# FINAL PREMIUM NAV STYLING
# ============================================================

st.markdown(
    dedent("""
<style>

/* Hide Streamlit chrome */

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

[data-testid="stSidebar"] {
    display: none;
}

[data-testid="collapsedControl"] {
    display: none;
}

header[data-testid="stHeader"] {
    background: transparent;
}


/* =========================================================
   TOP NAVIGATION
   ========================================================= */

div[role="radiogroup"] {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 7px !important;
}


/* Turn radio controls into premium pills */

div[role="radiogroup"] > label {
    margin: 0 !important;

    padding:
        7px 13px !important;

    border-radius:
        999px !important;

    border:
        1px solid rgba(255,255,255,.08) !important;

    background:
        rgba(255,255,255,.045) !important;

    transition:
        transform .14s ease,
        background .14s ease,
        border-color .14s ease !important;
}


div[role="radiogroup"] > label:hover {
    transform:
        translateY(-1px);

    background:
        rgba(79,140,255,.12) !important;

    border-color:
        rgba(79,140,255,.30) !important;
}


/* Selected navigation pill */

div[role="radiogroup"] > label:has(
    input:checked
) {
    background:
        linear-gradient(
            135deg,
            rgba(79,140,255,.24),
            rgba(105,113,255,.17)
        ) !important;

    border-color:
        rgba(79,140,255,.48) !important;

    box-shadow:
        0 7px 18px rgba(32,78,150,.15);
}


/* Hide Streamlit's native radio control. The label itself is the tab. */

div[role="radiogroup"] > label > div:first-child {
    display: none !important;
}

div[role="radiogroup"] input[type="radio"],
div[role="radiogroup"] svg {
    position: absolute !important;
    opacity: 0 !important;
    pointer-events: none !important;
    width: 0 !important;
    height: 0 !important;
}

div[role="radiogroup"] > label {
    gap: 0 !important;
}


/* Navigation text */

div[role="radiogroup"] p {
    color:
        #dbe5f3 !important;

    font-size:
        12px !important;

    font-weight:
        720 !important;

    margin:
        0 !important;
}


/* =========================================================
   SPORT SUBNAV
   ========================================================= */

.sh-subnav-wrap {
    margin-top:
        4px;

    margin-bottom:
        12px;

    padding-top:
        9px;

    border-top:
        1px solid rgba(255,255,255,.055);
}


.sh-active-sport {
    display:
        inline-flex;

    align-items:
        center;

    gap:
        7px;

    margin-bottom:
        8px;

    color:
        #8293aa;

    font-size:
        10px;

    font-weight:
        800;

    letter-spacing:
        .11em;

    text-transform:
        uppercase;
}


.sh-active-dot {
    width:
        6px;

    height:
        6px;

    border-radius:
        50%;

    background:
        #4f8cff;

    box-shadow:
        0 0 10px rgba(79,140,255,.65);
}


/* =========================================================
   MOBILE
   ========================================================= */

@media (max-width: 768px) {

    .block-container {
        padding-top:
            .55rem !important;

        padding-left:
            .8rem !important;

        padding-right:
            .8rem !important;
    }

    div[role="radiogroup"] {
        gap:
            5px !important;
    }

    div[role="radiogroup"] > label {
        padding:
            6px 9px !important;
    }

    div[role="radiogroup"] p {
        font-size:
            11px !important;
    }

}


/* Very small phone */

@media (max-width: 480px) {

    div[role="radiogroup"] > label {
        padding:
            5px 8px !important;
    }

}

</style>
    """),
    unsafe_allow_html=True,
)


# ============================================================

# PREMIUM_READABILITY_POLISH_V2
html("""
<style>

/* PAGE INTRO / EXPLANATION TEXT */

.sh-hero-sub {
    font-size: 17px !important;
    line-height: 1.62 !important;
    font-weight: 620 !important;
    color: #455B75 !important;
    max-width: 850px !important;
}


/* SECTION SUPPORT TEXT */

.sh-section-sub {
    font-size: 16px !important;
    line-height: 1.58 !important;
    font-weight: 600 !important;
    color: #536A84 !important;
    margin-top: 5px !important;
}


/* QUICK GUIDE MAIN COPY */

.sh-explainer-text {
    font-size: 18px !important;
    line-height: 1.58 !important;
    font-weight: 720 !important;
    color: #203A59 !important;
}


/* GENERAL CAPTIONS */

[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
    font-size: 14.5px !important;
    line-height: 1.55 !important;
    color: #5C7088 !important;
}


/* INFO / WARNING / SUCCESS BOXES */

[data-testid="stAlert"] p {
    font-size: 15.5px !important;
    line-height: 1.58 !important;
    font-weight: 560 !important;
}


/* EXPANDER TITLES */

[data-testid="stExpander"] summary p {
    font-size: 15.5px !important;
    font-weight: 680 !important;
}


/* FORM LABELS */

.stTextInput label p,
.stMultiSelect label p,
.stSelectbox label p,
.stRadio label p,
.stToggle label p {
    font-size: 14.5px !important;
    font-weight: 600 !important;
}


/* MOBILE */

@media (max-width: 768px) {

    .sh-hero-sub {
        font-size: 16px !important;
    }

    .sh-section-sub {
        font-size: 15px !important;
    }

    .sh-explainer-text {
        font-size: 17px !important;
    }

}

</style>
""")

# BRAND — ONCE
# ============================================================

brand_header(
    live=True,
)

st.session_state[
    "_premium_shell_brand_rendered"
] = True


# ============================================================
# ONE MAIN NAVIGATION ROW
# ============================================================


# VISIBLE_SEMANTIC_NAV_V1
html("""
<style>

:root {
    --sh-active:
        #2563EB;

    --sh-active-soft:
        #DBEAFE;

    --sh-active-border:
        #93C5FD;
}


/* Inactive navigation now works on light background */

div[role="radiogroup"] > label {
    background:
        #F1F5F9 !important;

    border:
        1px solid #D8E1EB !important;

    box-shadow:
        none !important;
}


div[role="radiogroup"] > label p {
    color:
        #334155 !important;

    font-weight:
        760 !important;
}


/* Selected item becomes unmistakably colored */

div[role="radiogroup"] > label:has(
    input:checked
) {
    background:
        var(
            --sh-active-soft
        ) !important;

    border-color:
        var(
            --sh-active-border
        ) !important;

    box-shadow:
        0 4px 12px
        rgba(31,48,74,.08) !important;

    transform:
        translateY(-1px);
}


div[role="radiogroup"] > label:has(
    input:checked
) p {
    color:
        var(
            --sh-active
        ) !important;

    font-weight:
        850 !important;
}


/* Section titles visibly inherit the active product color */

.sh-section-title {
    color:
        #102A43 !important;

    border-left:
        5px solid
        var(
            --sh-active
        );

    padding-left:
        10px;

    line-height:
        1.25;
}


/* Explainer picks up current page identity */

.sh-explainer {
    border-left:
        5px solid
        var(
            --sh-active
        ) !important;
}

</style>
""")


NAV_PALETTES = {
    "Today":
        (
            "#0891B2",
            "#CFFAFE",
            "#67E8F9",
        ),

    "Ask Sports HULK":
        (
            "#059669",
            "#D1FAE5",
            "#6EE7B7",
        ),

    "NFL":
        (
            "#2563EB",
            "#DBEAFE",
            "#93C5FD",
        ),

    "MLB":
        (
            "#1D4ED8",
            "#DBEAFE",
            "#93C5FD",
        ),

    "CFB":
        (
            "#B91C1C",
            "#FEE2E2",
            "#FCA5A5",
        ),

    "NBA":
        (
            "#EA580C",
            "#FFEDD5",
            "#FDBA74",
        ),

    "CBB":
        (
            "#B45309",
            "#FEF3C7",
            "#FCD34D",
        ),

    "NHL":
        (
            "#0284C7",
            "#E0F2FE",
            "#7DD3FC",
        ),

    "PrizePicks":
        (
            "#C026D3",
            "#FAE8FF",
            "#F0ABFC",
        ),

    "News":
        (
            "#4F46E5",
            "#E0E7FF",
            "#A5B4FC",
        ),

    "My Sports":
        (
            "#0F766E",
            "#CCFBF1",
            "#5EEAD4",
        ),

    "Games":
        (
            "#E84A5F",
            "#FFE9EE",
            "#F4BCC7",
        ),

    "Picks":
        (
            "#2563EB",
            "#DBEAFE",
            "#93C5FD",
        ),

    "Props":
        (
            "#7C3AED",
            "#EDE9FE",
            "#C4B5FD",
        ),

    "Fantasy":
        (
            "#EA7C22",
            "#FFEDD5",
            "#FDBA74",
        ),

    "Parlays":
        (
            "#0F9F9A",
            "#CCFBF1",
            "#5EEAD4",
        ),

    "Survivor":
        (
            "#059669",
            "#D1FAE5",
            "#6EE7B7",
        ),

    "Rankings":
        (
            "#B45309",
            "#FEF3C7",
            "#FCD34D",
        ),

    "Research":
        (
            "#475569",
            "#F1F5F9",
            "#CBD5E1",
        ),
}


def apply_visible_nav_color(
    label,
):
    color, soft, border = (
        NAV_PALETTES.get(
            str(label),
            (
                "#2563EB",
                "#DBEAFE",
                "#93C5FD",
            ),
        )
    )

    html(
        f"""
        <style>
            :root {{
                --sh-active:
                    {color};

                --sh-active-soft:
                    {soft};

                --sh-active-border:
                    {border};
            }}
        </style>
        """
    )


MAIN_NAV = [
    "Today",
    "Ask Sports HULK",
    "NFL",
    "MLB",
    "NBA",
    "NHL",
    "College",
    "Fantasy",
    "PrizePicks",
    "My Sports",
]


current = st.session_state.get(
    "premium_main_nav_v2",
    "Today",
)

if current not in MAIN_NAV:
    current = "Today"


main = st.pills(
    "Main navigation",
    MAIN_NAV,
    default=current,
    required=True,
    label_visibility="collapsed",
    key="premium_main_nav_v2",
)


# APPLY_MAIN_VISIBLE_COLOR
apply_visible_nav_color(
    main
)


# ============================================================
# SPORT-FIRST ROUTES
# ============================================================

if main == "Today":
    render_today()


elif main == "Ask Sports HULK":
    render_ask_sports_hulk()


elif main in {
    "NFL",
    "MLB",
    "NBA",
    "NHL",
}:
    sport = main

    st.session_state[
        "last_selected_sport"
    ] = sport

    if sport == "NFL":
        sport_tabs = [
            "Overview",
            "Games & Box Scores",
            "Best Bets",
            "Props",
            "Parlays",
            "Survivor",
            "Fantasy",
            "DFS",
            "News",
        ]
    else:
        sport_tabs = [
            "Overview",
            "Games & Box Scores",
            "Best Bets",
            "Props",
            "Parlays",
            "Fantasy",
            "DFS",
            "News",
        ]

    selected_tab = st.pills(
        sport + " sections",
        sport_tabs,
        default="Overview",
        required=True,
        label_visibility="collapsed",
        key=(
            "sport_tabs_"
            + sport
        ),
    )

    apply_visible_nav_color(
        sport
    )

    if selected_tab == "Overview":
        render_today(
            sport_override=sport
        )
    else:
        feature_lookup = {
            "Games & Box Scores": "games",
            "Best Bets": "picks",
            "Props": "props",
            "Parlays": "parlays",
            "Survivor": "survivor",
            "Fantasy": "fantasy",
            "DFS": "dfs",
            "News": "news",
        }

        render_feature(
            sport,
            feature_lookup[
                selected_tab
            ],
        )


elif main == "Fantasy":
    apply_visible_nav_color(
        "Fantasy"
    )

    fantasy_mode = st.pills(
        "Fantasy type",
        [
            "Season-Long",
            "DFS",
        ],
        default="Season-Long",
        required=True,
        label_visibility="collapsed",
        key="fantasy_main_mode",
    )

    fantasy_default_sport = (
        st.session_state.get(
            "last_selected_sport",
            "NFL",
        )
    )

    if fantasy_default_sport not in {
        "NFL",
        "MLB",
        "NBA",
        "NHL",
    }:
        fantasy_default_sport = "NFL"

    fantasy_sport = st.pills(
        "Fantasy sport",
        [
            "NFL",
            "MLB",
            "NBA",
            "NHL",
        ],
        default=fantasy_default_sport,
        required=True,
        label_visibility="collapsed",
        key="fantasy_main_sport",
    )

    st.session_state[
        "last_selected_sport"
    ] = fantasy_sport

    render_feature(
        fantasy_sport,
        (
            "dfs"
            if fantasy_mode == "DFS"
            else "fantasy"
        ),
    )


elif main == "PrizePicks":
    apply_visible_nav_color(
        "PrizePicks"
    )

    prizepicks_default_sport = (
        st.session_state.get(
            "last_selected_sport",
            "NFL",
        )
    )

    if prizepicks_default_sport not in {
        "NFL",
        "MLB",
        "NBA",
        "NHL",
    }:
        prizepicks_default_sport = "NFL"

    prizepicks_sport = st.pills(
        "PrizePicks sport",
        [
            "NFL",
            "MLB",
            "NBA",
            "NHL",
        ],
        default=prizepicks_default_sport,
        required=True,
        label_visibility="collapsed",
        key="prizepicks_main_sport",
    )

    st.session_state[
        "last_selected_sport"
    ] = prizepicks_sport

    render_feature(
        prizepicks_sport,
        "prizepicks",
    )


elif main == "College":
    college_sport = st.pills(
        "College sport",
        [
            "CFB",
            "CBB",
        ],
        default="CFB",
        required=True,
        label_visibility="collapsed",
        key="college_sport",
    )

    college_tabs = [
        "Overview",
        "Games & Box Scores",
        "Best Bets",
        "Parlays",
        "Rankings",
        "Research",
        "News",
    ]

    college_tab = st.pills(
        college_sport + " sections",
        college_tabs,
        default="Overview",
        required=True,
        label_visibility="collapsed",
        key=(
            "college_tabs_"
            + college_sport
        ),
    )

    st.session_state[
        "last_selected_sport"
    ] = college_sport

    apply_visible_nav_color(
        college_sport
    )

    if college_tab == "Overview":
        render_today(
            sport_override=college_sport
        )
    else:
        college_lookup = {
            "Games & Box Scores": "games",
            "Best Bets": "picks",
            "Parlays": "parlays",
            "Rankings": "rankings",
            "Research": "research",
            "News": "news",
        }

        render_feature(
            college_sport,
            college_lookup[
                college_tab
            ],
        )


elif main == "My Sports":
    render_member_center()


# ============================================================
# PERSISTENT ASK SPORTS HULK LAUNCHER
# ============================================================

if main != "Ask Sports HULK":
    st.markdown(
        """
        <style>
        .st-key-ask_sports_hulk_floating {
            position: fixed;
            right: 18px;
            bottom: 18px;
            width: 190px;
            z-index: 1000;
        }

        .st-key-ask_sports_hulk_floating button {
            border-radius: 999px !important;
            border: 1px solid #6EE7B7 !important;
            background: #07131D !important;
            color: #FFFFFF !important;
            box-shadow:
                0 14px 34px
                rgba(6, 78, 59, .24) !important;
            font-weight: 850 !important;
        }

        .st-key-ask_sports_hulk_floating button:hover {
            border-color: #34D399 !important;
            transform: translateY(-1px);
        }

        @media (max-width: 768px) {
            .st-key-ask_sports_hulk_floating {
                right: 12px;
                bottom: 14px;
                width: 54px;
            }

            .st-key-ask_sports_hulk_floating button {
                width: 54px !important;
                height: 54px !important;
                min-height: 54px !important;
                padding: 0 !important;
                border-radius: 50% !important;
            }

            .st-key-ask_sports_hulk_floating button p {
                font-size: 0 !important;
                line-height: 0 !important;
            }

            .st-key-ask_sports_hulk_floating button p::after {
                content: "💬";
                font-size: 21px;
                line-height: 1;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(
        key="ask_sports_hulk_floating",
    ):
        if st.button(
            "💬 Ask Sports HULK",
            key="ask_sports_hulk_floating_button",
            use_container_width=True,
        ):
            ask_sports_hulk_dialog()
