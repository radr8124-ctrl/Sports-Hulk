import streamlit as st

from premium_ui.alerts import (
    CHANNELS,
    DEFAULT_SPORTS,
    FREQUENCIES,
    SPORT_ALERTS,
)

from premium_ui.components import (
    brand_header,
    explanation_box,
    hero,
    section_header,
)

from premium_ui.member_store import (
    ensure_schema,
)


SPORTS = [
    "NFL",
    "MLB",
    "CFB",
    "NBA",
    "CBB",
    "NHL",
]


def render_member_center():

    ensure_schema()

    if not st.session_state.get(
        "_premium_shell_brand_rendered",
        False,
    ):
        brand_header(
            live=True,
        )

    hero(
        "My Sports",
        (
            "Choose what matters to you. "
            "Sports HULK will eventually use these "
            "preferences for your site, email and text alerts."
        ),
        kicker="Personalize",
    )

    explanation_box(
        (
            "Pick your sports and alerts here. "
            "Email and text delivery will activate "
            "after verified notification providers are connected."
        )
    )


    section_header(
        "Your Sports",
        "Only follow the leagues you care about.",
    )

    selected_sports = st.multiselect(
        "Sports",
        SPORTS,
        default=st.session_state.get(
            "member_sports",
            DEFAULT_SPORTS,
        ),
        label_visibility="collapsed",
    )

    st.session_state[
        "member_sports"
    ] = selected_sports


    section_header(
        "Favorite Teams",
        (
            "Team personalization is prepared now "
            "and becomes searchable when member accounts activate."
        ),
    )

    teams = st.text_input(
        "Favorite teams",
        value=st.session_state.get(
            "member_teams",
            "",
        ),
        placeholder=(
            "Example: Bills, Yankees, Knicks"
        ),
        label_visibility="collapsed",
    )

    st.session_state[
        "member_teams"
    ] = teams


    section_header(
        "Favorite Players",
        (
            "Used later for player news, fantasy "
            "and pro player-prop alerts."
        ),
    )

    players = st.text_input(
        "Favorite players",
        value=st.session_state.get(
            "member_players",
            "",
        ),
        placeholder=(
            "Example: Josh Allen, Aaron Judge"
        ),
        label_visibility="collapsed",
    )

    st.session_state[
        "member_players"
    ] = players


    section_header(
        "Delivery",
        "Choose how Sports HULK may reach you.",
    )

    channels = st.multiselect(
        "Delivery channels",
        CHANNELS,
        default=st.session_state.get(
            "member_channels",
            ["Email"],
        ),
        label_visibility="collapsed",
    )

    st.session_state[
        "member_channels"
    ] = channels


    frequency = st.radio(
        "Frequency",
        FREQUENCIES,
        index=FREQUENCIES.index(
            st.session_state.get(
                "member_frequency",
                "Daily Digest",
            )
        ),
        horizontal=True,
    )

    st.session_state[
        "member_frequency"
    ] = frequency


    section_header(
        "Alerts",
        (
            "College sports automatically exclude "
            "player props and fantasy."
        ),
    )

    alert_state = {}

    for sport in selected_sports:

        with st.expander(
            sport,
            expanded=(
                len(
                    selected_sports
                )
                == 1
            ),
        ):

            st.caption(
                (
                    "Choose the updates you want "
                    f"for {sport}."
                )
            )

            alert_state[
                sport
            ] = {}

            for alert in (
                SPORT_ALERTS[
                    sport
                ]
            ):

                key = (
                    "alert_"
                    + sport
                    + "_"
                    + alert
                    .lower()
                    .replace(
                        " ",
                        "_",
                    )
                    .replace(
                        "/",
                        "_",
                    )
                )

                alert_state[
                    sport
                ][
                    alert
                ] = st.toggle(
                    alert,
                    value=st.session_state.get(
                        key,
                        alert
                        in {
                            "Breaking News",
                            "Injuries",
                            "Game Picks",
                        },
                    ),
                    key=key,
                )


    section_header(
        "Quiet Hours",
        "Prevent non-urgent notifications while you sleep.",
    )

    quiet = st.toggle(
        "Use quiet hours",
        value=st.session_state.get(
            "quiet_enabled",
            True,
        ),
    )

    st.session_state[
        "quiet_enabled"
    ] = quiet

    if quiet:

        c1, c2 = st.columns(2)

        with c1:
            quiet_start = st.time_input(
                "Start",
            )

        with c2:
            quiet_end = st.time_input(
                "End",
            )

        st.session_state[
            "quiet_start"
        ] = str(
            quiet_start
        )

        st.session_state[
            "quiet_end"
        ] = str(
            quiet_end
        )


    section_header(
        "Account Status",
        "Signup and verified delivery are prepared but not activated yet.",
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Account",
            "Prepared",
        )

    with c2:
        st.metric(
            "Email",
            "Not Connected",
        )

    with c3:
        st.metric(
            "Text",
            "Not Connected",
        )


    st.info(
        (
            "Sports HULK will not send email or text "
            "until a member verifies that destination "
            "and explicitly opts in."
        )
    )


    if st.button(
        "Save My Preferences",
        type="primary",
        width="stretch",
    ):

        st.session_state[
            "member_alert_state"
        ] = alert_state

        st.success(
            (
                "Preferences saved for this session. "
                "Persistent account storage activates "
                "when member authentication is connected."
            )
        )
