from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st


def _safe(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value)


def _friendly(value):
    return _safe(value).replace("_", " ").title()


def _num(value, digits=1):
    try:
        number = float(value)
        if pd.isna(number):
            return "—"
        if digits == 0:
            return str(int(round(number)))
        return f"{number:.{digits}f}"
    except Exception:
        return "—"


def _line(value):
    try:
        n = float(value)
        if pd.isna(n):
            return "—"
        return f"{n:g}"
    except Exception:
        return "—"


def _odds(value):
    try:
        number = int(round(float(value)))
        return f"+{number}" if number > 0 else str(number)
    except Exception:
        return "—"


def _category(sport, row):
    raw = (
        _safe(row.get("stat_type"))
        or _safe(row.get("metric"))
        or _safe(row.get("market_subtype"))
    ).upper()

    if sport == "MLB":
        if "STRIKE" in raw:
            return "Strikeouts"
        if "HIT" in raw and "HHR" not in raw:
            return "Hits"
        if "RUN" in raw:
            return "Runs"
        if "RBI" in raw:
            return "RBIs"
        if "BASE" in raw:
            return "Total Bases"
        if "WALK" in raw:
            return "Walks"
        return "Other"

    if sport == "NBA":
        if "POINT" in raw:
            return "Points"
        if "REBOUND" in raw:
            return "Rebounds"
        if "ASSIST" in raw:
            return "Assists"
        if "THREE" in raw or "3PM" in raw:
            return "3PM"
        if "PRA" in raw or "PTS_REB_AST" in raw:
            return "PRA"
        return "Other"

    if sport == "NHL":
        if "SHOT" in raw:
            return "Shots"
        if "SAVE" in raw:
            return "Saves"
        if "GOAL" in raw:
            return "Goals"
        if "POINT" in raw:
            return "Points"
        if "BLOCK" in raw:
            return "Blocks"
        return "Other"

    return "Other"


def _recent_value(row):
    for col in [
        "recent_avg",
        "stat_l5_avg",
        "recent_metric",
    ]:
        value = pd.to_numeric(row.get(col), errors="coerce")
        if pd.notna(value):
            return value
    return None


def _season_value(row):
    for col in [
        "season_avg",
        "stat_season_avg",
    ]:
        value = pd.to_numeric(row.get(col), errors="coerce")
        if pd.notna(value):
            return value
    return None


def _hit_rate(row):
    for col in [
        "l10_hit_rate",
        "l5_hit_rate",
    ]:
        value = pd.to_numeric(row.get(col), errors="coerce")
        if pd.notna(value):
            return value * 100 if value <= 1 else value
    return None


def _sample(row):
    for col in [
        "meaningful_games",
        "recent_games",
        "sample_games",
        "season_games",
    ]:
        value = pd.to_numeric(row.get(col), errors="coerce")
        if pd.notna(value):
            return int(value)
    return None


def _book_count(row):
    for col in [
        "book_count",
        "sportsbook_count",
    ]:
        value = pd.to_numeric(row.get(col), errors="coerce")
        if pd.notna(value):
            return int(value)
    return None


def _injury_risk(row):
    for col in [
        "injury_gate",
        "injury_status",
        "espn_injury_gate",
    ]:
        value = _safe(row.get(col)).upper()
        if value and value not in {
            "PASS",
            "CLEAR",
            "ACTIVE",
            "NO_ESPN_LISTING",
            "NONE",
            "UNKNOWN",
        }:
            return _friendly(value)
    return None


def _evidence(value):
    try:
        score = float(value)
    except Exception:
        return "Qualified"

    if score >= 92:
        return "Elite research"
    if score >= 85:
        return "Strong research"
    if score >= 78:
        return "Good research"
    return "Qualified"


def render_player_prop_board(
    data,
    *,
    sport,
    accent,
    title,
    full_data=None,
    full_title=None,
):
    if data is None or data.empty:
        st.info(
            f"No qualified {sport} player-prop research is available right now."
        )
        return

    board = data.copy()
    board["_score"] = pd.to_numeric(
        board.get("evidence_score"),
        errors="coerce",
    )
    board["_category"] = board.apply(
        lambda row: _category(sport, row),
        axis=1,
    )

    # Respect sample gates where the sport has them.
    if "sample_gate" in board.columns:
        passed = board[
            board["sample_gate"].astype(str).str.upper().eq("PASS")
        ].copy()
        if not passed.empty:
            board = passed

    board = board.sort_values(
        "_score",
        ascending=False,
        na_position="last",
    )

    ordered_categories = {
        "MLB": ["Hits", "Runs", "RBIs", "Total Bases", "Walks", "Strikeouts", "Other"],
        "NBA": ["Points", "Rebounds", "Assists", "3PM", "PRA", "Other"],
        "NHL": ["Shots", "Points", "Goals", "Saves", "Blocks", "Other"],
    }.get(sport, ["Other"])

    present = [
        category
        for category in ordered_categories
        if category in set(board["_category"])
    ]

    options = ["All"] + present

    if len(options) > 1:
        selected_category = st.pills(
            f"{sport} prop category",
            options,
            default="All",
            required=True,
            label_visibility="collapsed",
            key=f"{sport.lower()}_prop_category",
        )
    else:
        selected_category = "All"

    visible = (
        board.copy()
        if selected_category == "All"
        else board[board["_category"].eq(selected_category)].copy()
    )

    st.caption(
        f"{len(board)} qualified {sport} prop"
        + ("" if len(board) == 1 else "s")
        + (
            f" · {len(visible)} in {selected_category}"
            if selected_category != "All"
            else ""
        )
    )

    st.markdown(
        f"### {title if selected_category == 'All' else selected_category}"
    )
    st.caption(
        "The card shows the decision context. Full model fields stay in the research table."
    )

    for start in range(0, min(len(visible), 9), 3):
        cols = st.columns(3)

        for col, (_, row) in zip(cols, visible.iloc[start:start + 3].iterrows()):
            player = _safe(
                row.get("player")
                or row.get("player_dfs")
                or row.get("player_sportsbook")
            )

            market = (
                _safe(row.get("market_subtype"))
                or _safe(row.get("stat_type"))
                or _safe(row.get("metric"))
            )

            side = _safe(row.get("side")).upper()
            line_value = row.get("line")
            recent = _recent_value(row)
            season = _season_value(row)
            hit_rate = _hit_rate(row)
            sample = _sample(row)
            books = _book_count(row)
            price = pd.to_numeric(
                row.get("median_price_american"),
                errors="coerce",
            )

            why = []
            if recent is not None:
                why.append(f"recent {_num(recent)} vs line {_line(line_value)}")
            if hit_rate is not None:
                why.append(f"hit {_num(hit_rate, 0)}%")
            elif season is not None:
                why.append(f"season avg {_num(season)}")
            if books is not None:
                why.append(f"{books} books")
            if pd.notna(price):
                why.append("market " + _odds(price))

            risk = _injury_risk(row)
            if risk is None and sample is not None and sample < 5:
                risk = "Small sample"
            if risk is None:
                risk = "No major research flag"

            with col:
                st.markdown(
                    f"""
                    <div style="
                        min-height:148px;
                        padding:15px 16px 14px 19px;
                        margin-bottom:10px;
                        border-radius:15px;
                        border:1px solid #E5E7EB;
                        border-left:5px solid {accent};
                        background:white;
                        box-shadow:0 5px 16px rgba(31,48,74,.07);
                    ">
                        <div style="font-size:17px;font-weight:820;color:#102A43;line-height:1.18;">
                            {escape(player)}
                        </div>
                        <div style="margin-top:4px;font-size:12px;font-weight:800;color:#64748B;text-transform:uppercase;">
                            {escape(_friendly(market))}
                        </div>
                        <div style="margin-top:5px;font-size:22px;font-weight:860;color:#102A43;line-height:1.1;">
                            {escape((side + " " + _line(line_value)).strip())}
                        </div>
                        <div style="margin-top:7px;font-size:13.5px;font-weight:590;color:#435A73;line-height:1.42;">
                            {escape(" · ".join(why[:4]))}
                        </div>
                        <div style="margin-top:8px;display:flex;gap:5px;flex-wrap:wrap;">
                            <span style="padding:4px 8px;border-radius:999px;background:#ECFDF5;color:#047857;font-size:11.5px;font-weight:820;">
                                {escape(_evidence(row.get("evidence_score")))}
                            </span>
                            <span style="padding:4px 8px;border-radius:999px;background:{'#FFF7ED' if risk != 'No major research flag' else '#EFF6FF'};color:{'#C2410C' if risk != 'No major research flag' else '#1D4ED8'};font-size:11.5px;font-weight:820;">
                                {escape(risk)}
                            </span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    deep = full_data if full_data is not None else board

    if deep is not None and not deep.empty:
        with st.expander(
            full_title or f"Open full {sport} prop research",
            expanded=False,
        ):
            st.dataframe(
                deep.drop(
                    columns=["_score", "_category"],
                    errors="ignore",
                ),
                width="stretch",
                hide_index=True,
            )
