from premium_ui.components import (
    brand_header,
    explanation_box,
    hero,
    sport_strip,
)
from premium_ui.sport_config import (
    PAGE_EXPLAINERS,
)


def render_page_shell(
    title,
    page_key="today",
    sport="ALL",
    subtitle="",
):
    brand_header(
        live=True,
    )

    hero(
        title=title,
        subtitle=subtitle,
    )

    sport_strip(
        active=sport,
    )

    explanation = PAGE_EXPLAINERS.get(
        page_key
    )

    if explanation:
        explanation_box(
            explanation
        )
