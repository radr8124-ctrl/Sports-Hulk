from textwrap import dedent
import streamlit as st


def html(content):
    """
    Render trusted Sports HULK UI HTML/CSS directly.
    Bypasses Markdown so HTML never appears as code.
    """
    content = dedent(
        str(content)
    ).strip()

    st.html(content)
