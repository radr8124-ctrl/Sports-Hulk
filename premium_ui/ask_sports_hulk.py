from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

from premium_ui.components import section_header


ASK_API_URL = os.getenv(
    "ASK_SPORTS_HULK_API_URL",
    "http://127.0.0.1:8510/api/ask",
)

QUICK_PROMPTS = [
    ("Survivor", "What Survivor team should I use?"),
    ("Start / Sit", "Who should I start this week?"),
    ("Waivers", "Who are the top waiver adds?"),
    ("Live Scores", "What are the live NFL scores?"),
    ("Best Bet", "What is the best NFL bet right now?"),
    ("DFS", "Who are the best DraftKings DFS plays?"),
]


def _messages_key(compact: bool = False) -> str:
    return (
        "ask_sports_hulk_dialog_messages"
        if compact
        else "ask_sports_hulk_messages"
    )


def ask_question(question: str) -> dict[str, Any]:
    q = str(question or "").strip()

    if not q:
        return {
            "take": "Ask me a sports question.",
            "confidence": "WAITING",
            "risk": [],
            "why": [],
            "sources": [],
        }

    try:
        response = requests.post(
            ASK_API_URL,
            json={"question": q},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "Unexpected assistant response."
            )

        return payload

    except Exception as exc:
        return {
            "take": "Ask Sports HULK is temporarily unavailable.",
            "confidence": "WAITING",
            "why": [],
            "risk": [
                str(
                    exc
                )
            ],
            "sources": [],
        }


def _submit(
    question: str,
    *,
    compact: bool = False,
) -> None:
    q = str(
        question
        or ""
    ).strip()

    if not q:
        return

    key = _messages_key(
        compact
    )

    messages = st.session_state.setdefault(
        key,
        [],
    )

    messages.append(
        {
            "role": "user",
            "text": q,
        }
    )

    messages.append(
        {
            "role": "assistant",
            "answer": ask_question(
                q
            ),
        }
    )


def _card_detail(
    card: dict[str, Any],
) -> str:
    if card.get(
        "state"
    ):
        away = card.get(
            "away"
        ) or ""
        home = card.get(
            "home"
        ) or ""
        away_score = card.get(
            "away_score"
        )
        home_score = card.get(
            "home_score"
        )

        score = ""

        if (
            away_score is not None
            and home_score is not None
        ):
            score = (
                str(
                    away_score
                )
                + " - "
                + str(
                    home_score
                )
            )

        return " · ".join(
            x
            for x in [
                (
                    str(
                        away
                    )
                    + " @ "
                    + str(
                        home
                    )
                ).strip(
                    " @"
                ),
                score,
                str(
                    card.get(
                        "status"
                    )
                    or card.get(
                        "state"
                    )
                    or ""
                ),
            ]
            if x
        )

    if card.get(
        "opponent"
    ):
        return " · ".join(
            x
            for x in [
                (
                    "vs "
                    + str(
                        card.get(
                            "opponent"
                        )
                    )
                ),
                (
                    "Market "
                    + str(
                        card.get(
                            "market_prob"
                        )
                    )
                    + "%"
                    if card.get(
                        "market_prob"
                    )
                    is not None
                    else ""
                ),
                (
                    "Context "
                    + str(
                        card.get(
                            "context_score"
                        )
                    )
                    if card.get(
                        "context_score"
                    )
                    is not None
                    else ""
                ),
            ]
            if x
        )

    if card.get(
        "projection"
    ) is not None:
        parts = [
            str(
                card.get(
                    "projection"
                )
            )
            + " projected"
        ]

        if card.get(
            "salary"
        ) is not None:
            parts.append(
                "$"
                + str(
                    card.get(
                        "salary"
                    )
                )
                + " salary"
            )

        return " · ".join(
            parts
        )

    if card.get(
        "selection"
    ):
        parts = [
            str(
                card.get(
                    "market"
                )
                or ""
            ),
            str(
                card.get(
                    "selection"
                )
                or ""
            ),
            str(
                card.get(
                    "line"
                )
                if card.get(
                    "line"
                )
                is not None
                else ""
            ),
        ]

        return " ".join(
            x
            for x in parts
            if x
        ).strip()

    return str(
        card.get(
            "source"
        )
        or card.get(
            "team"
        )
        or card.get(
            "position"
        )
        or ""
    )


def render_answer(
    answer: dict[str, Any],
    *,
    compact: bool = False,
) -> None:
    confidence = str(
        answer.get(
            "confidence"
        )
        or answer.get(
            "status"
        )
        or "RESEARCH"
    )

    take = str(
        answer.get(
            "take"
        )
        or "No current take."
    )

    st.markdown(
        """
        <div class="sh-ask-answer">
          <div class="sh-ask-label">HULK TAKE</div>
          <div class="sh-ask-take">"""
        + take
        + """</div>
          <div class="sh-ask-confidence">"""
        + confidence
        + """</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    why = answer.get(
        "why"
    ) or []

    if why:
        with st.expander(
            "Why",
            expanded=(
                not compact
            ),
        ):
            for item in why:
                st.markdown(
                    "- "
                    + str(
                        item
                    )
                )

    risk = answer.get(
        "risk"
    ) or []

    if risk:
        with st.expander(
            "Risk / what could change it",
            expanded=False,
        ):
            for item in risk:
                st.markdown(
                    "- "
                    + str(
                        item
                    )
                )

    cards = answer.get(
        "cards"
    ) or []

    if (
        cards
        and not compact
    ):
        cols = st.columns(
            min(
                3,
                len(
                    cards
                ),
            )
        )

        for idx, card in enumerate(
            cards[:6]
        ):
            with cols[
                idx
                % len(
                    cols
                )
            ]:
                title = str(
                    card.get(
                        "title"
                    )
                    or card.get(
                        "selection"
                    )
                    or "Research"
                )

                kind = str(
                    card.get(
                        "type"
                    )
                    or answer.get(
                        "intent"
                    )
                    or "research"
                ).replace(
                    "_",
                    " ",
                )

                st.markdown(
                    """
                    <div class="sh-ask-card">
                      <div class="sh-ask-card-kind">"""
                    + kind
                    + """</div>
                      <div class="sh-ask-card-title">"""
                    + title
                    + """</div>
                      <div class="sh-ask-card-detail">"""
                    + _card_detail(
                        card
                    )
                    + """</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    sources = answer.get(
        "sources"
    ) or []

    updated = (
        answer.get(
            "updated_at"
        )
        or answer.get(
            "generated_at"
        )
    )

    source_names = [
        str(
            item.get(
                "source"
            )
            or item.get(
                "label"
            )
            or ""
        )
        for item in sources
        if isinstance(
            item,
            dict,
        )
    ]

    footer_parts = []

    if any(
        source_names
    ):
        footer_parts.append(
            "Sources: "
            + " · ".join(
                x
                for x in source_names[:3]
                if x
            )
        )

    if updated:
        footer_parts.append(
            "Updated: "
            + str(
                updated
            )
        )

    if footer_parts:
        st.caption(
            " · ".join(
                footer_parts
            )
        )


def _render_messages(
    *,
    compact: bool = False,
) -> None:
    key = _messages_key(
        compact
    )

    messages = st.session_state.setdefault(
        key,
        [],
    )

    if not messages:
        st.info(
            "Ask about a score, player, Survivor pick, fantasy decision, "
            "waiver add, DFS play, prop, bet or current sports news. "
            "If the data is not verified, HULK should say so."
        )
        return

    visible = (
        messages[-8:]
        if compact
        else messages
    )

    for message in visible:
        role = message.get(
            "role"
        )

        if role == "user":
            with st.chat_message(
                "user"
            ):
                st.markdown(
                    str(
                        message.get(
                            "text",
                            "",
                        )
                    )
                )

        else:
            with st.chat_message(
                "assistant"
            ):
                render_answer(
                    message.get(
                        "answer",
                        {},
                    ),
                    compact=compact,
                )


def _styles() -> None:
    st.markdown(
        """
        <style>
        .sh-ask-hero {
            border: 1px solid #183249;
            border-radius: 28px;
            padding: 24px;
            background:
                radial-gradient(circle at top right, rgba(16,185,129,.16), transparent 35%),
                linear-gradient(135deg, #07131d, #07171a);
            color: white;
            margin-bottom: 18px;
        }
        .sh-ask-kicker {
            color: #6ee7b7;
            font-size: 11px;
            font-weight: 900;
            letter-spacing: .16em;
        }
        .sh-ask-hero h1 {
            color: white;
            margin: 6px 0 4px 0;
            font-size: 34px;
        }
        .sh-ask-hero p {
            color: #94a3b8;
            margin: 0;
            font-size: 15px;
        }
        .sh-ask-answer {
            position: relative;
            border: 1px solid #bdd7cd;
            border-radius: 20px;
            padding: 16px 18px;
            background: #f7fbf9;
            margin-bottom: 8px;
        }
        .sh-ask-label {
            color: #047857;
            font-size: 10px;
            font-weight: 950;
            letter-spacing: .14em;
        }
        .sh-ask-take {
            color: #102a43;
            font-size: 18px;
            font-weight: 850;
            line-height: 1.4;
            margin-top: 5px;
            padding-right: 100px;
        }
        .sh-ask-confidence {
            position: absolute;
            top: 14px;
            right: 14px;
            border: 1px solid #a7f3d0;
            background: #ecfdf5;
            color: #047857;
            border-radius: 999px;
            padding: 5px 9px;
            font-size: 10px;
            font-weight: 900;
        }
        .sh-ask-card {
            min-height: 125px;
            border: 1px solid #d8e1eb;
            border-radius: 18px;
            padding: 14px;
            background: white;
            margin: 5px 0;
        }
        .sh-ask-card-kind {
            color: #64748b;
            font-size: 9px;
            font-weight: 900;
            letter-spacing: .12em;
            text-transform: uppercase;
        }
        .sh-ask-card-title {
            color: #0f172a;
            font-size: 15px;
            font-weight: 850;
            margin-top: 6px;
        }
        .sh-ask-card-detail {
            color: #64748b;
            font-size: 12px;
            line-height: 1.45;
            margin-top: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_ask_sports_hulk() -> None:
    _styles()

    st.markdown(
        """
        <div class="sh-ask-hero">
          <div class="sh-ask-kicker">SPORTS INTELLIGENCE ANALYST</div>
          <h1>Ask Sports HULK</h1>
          <p>One conversational front door to live scores, fantasy, DFS,
          Survivor, props, betting research, injuries, schedules and news.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(
        3
    )

    for idx, (
        label,
        prompt,
    ) in enumerate(
        QUICK_PROMPTS
    ):
        with cols[
            idx
            % len(
                cols
            )
        ]:
            if st.button(
                label,
                key=(
                    "ask_quick_"
                    + str(
                        idx
                    )
                ),
                use_container_width=True,
            ):
                _submit(
                    prompt
                )
                st.rerun()

    section_header(
        "Conversation",
        "Sports HULK uses the current governed data behind the app. UNKNOWN stays UNKNOWN.",
    )

    _render_messages()

    question = st.chat_input(
        "Ask Sports HULK anything…",
        key="ask_sports_hulk_input",
    )

    if question:
        _submit(
            question
        )
        st.rerun()


@st.dialog(
    "Ask Sports HULK",
    width="large",
)
def ask_sports_hulk_dialog() -> None:
    _styles()

    st.caption(
        "Live Sports HULK intelligence without leaving the page."
    )

    cols = st.columns(
        2
    )

    for idx, (
        label,
        prompt,
    ) in enumerate(
        QUICK_PROMPTS[:4]
    ):
        with cols[
            idx
            % 2
        ]:
            if st.button(
                label,
                key=(
                    "ask_dialog_quick_"
                    + str(
                        idx
                    )
                ),
                use_container_width=True,
            ):
                _submit(
                    prompt,
                    compact=True,
                )
                st.rerun(
                    scope="fragment"
                )

    _render_messages(
        compact=True,
    )

    with st.form(
        "ask_sports_hulk_dialog_form",
        clear_on_submit=True,
    ):
        question = st.text_input(
            "Question",
            placeholder=(
                "Ask about this page, a player, Survivor, "
                "fantasy, DFS, props or scores…"
            ),
            label_visibility="collapsed",
        )

        send = st.form_submit_button(
            "Ask",
            use_container_width=True,
        )

    if (
        send
        and question.strip()
    ):
        _submit(
            question,
            compact=True,
        )
        st.rerun(
            scope="fragment"
        )
