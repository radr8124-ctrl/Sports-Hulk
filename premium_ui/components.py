from html import escape
from textwrap import dedent

import streamlit as st


def render_html(value):
    """
    Render HTML directly.
    Do NOT pass premium components through Markdown.
    """
    st.html(
        dedent(
            str(value)
        ).strip()
    )


def brand_header(live=True):

    live_html = ""

    if live:
        live_html = """
        <div class="sh-live">
            <span class="sh-live-dot"></span>
            <span>LIVE DATA</span>
        </div>
        """

    render_html(
        f"""
        <div class="sh-brand-row">
            <div class="sh-brand">
                SPORTS HULK
            </div>

            {live_html}
        </div>
        """
    )


def hero(
    title,
    subtitle="",
    kicker="Sports Intelligence",
):

    render_html(
        f"""
        <section class="sh-hero">

            <div class="sh-kicker">
                {escape(str(kicker))}
            </div>

            <div class="sh-hero-title">
                {escape(str(title))}
            </div>

            <div class="sh-hero-sub">
                {escape(str(subtitle))}
            </div>

        </section>
        """
    )


def explanation_box(text):

    render_html(
        f"""
        <div class="sh-explainer">

            <div class="sh-explainer-icon">
                i
            </div>

            <div class="sh-explainer-text">
                {escape(str(text))}
            </div>

        </div>
        """
    )


def section_header(
    title,
    subtitle="",
):

    render_html(
        f"""
        <div class="sh-section">

            <div>
                <div class="sh-section-title">
                    {escape(str(title))}
                </div>

                <div class="sh-section-sub">
                    {escape(str(subtitle))}
                </div>
            </div>

        </div>
        """
    )


def chip(
    label,
    tone="blue",
):

    allowed = {
        "blue",
        "green",
        "amber",
        "red",
        "purple",
    }

    if tone not in allowed:
        tone = "blue"

    return (
        '<span class="sh-chip '
        f'sh-chip-{tone}">'
        f'{escape(str(label))}'
        '</span>'
    )


def card(
    title,
    body="",
    chips=None,
):

    chips = chips or []

    chip_html = "".join(
        chip(
            label,
            tone,
        )
        for label, tone in chips
    )

    render_html(
        f"""
        <article class="sh-card">

            <div class="sh-card-title">
                {escape(str(title))}
            </div>

            <div class="sh-card-body">
                {escape(str(body))}
            </div>

            <div class="sh-card-chips">
                {chip_html}
            </div>

        </article>
        """
    )


def sport_strip(active="ALL"):

    sports = [
        "ALL",
        "NFL",
        "MLB",
        "CFB",
        "NBA",
        "CBB",
        "NHL",
    ]

    pieces = [
        '<div class="sh-sports">'
    ]

    for sport in sports:

        cls = (
            "sh-sport sh-sport-active"
            if sport == active
            else "sh-sport"
        )

        pieces.append(
            f'<span class="{cls}">'
            f'{escape(sport)}'
            '</span>'
        )

    pieces.append("</div>")

    render_html(
        "".join(pieces)
    )
