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


def _odds(value):
    try:
        number = int(round(float(value)))
        return f"+{number}" if number > 0 else str(number)
    except Exception:
        return "—"


def _line(value):
    try:
        number = float(value)
        if pd.isna(number):
            return ""
        if number > 0:
            return f"+{number:g}"
        return f"{number:g}"
    except Exception:
        return ""


def _evidence_label(value):
    try:
        score = float(value)
    except Exception:
        return "Research"

    if score >= 92:
        return "Elite evidence"
    if score >= 85:
        return "Strong evidence"
    if score >= 78:
        return "Good evidence"
    return "Qualified research"


def _sport_reason(row, sport):
    pieces = []

    if sport == "MLB":
        form = pd.to_numeric(row.get("form_edge"), errors="coerce")
        pitcher = pd.to_numeric(row.get("pitcher_edge"), errors="coerce")
        winpct = pd.to_numeric(row.get("winpct_edge"), errors="coerce")

        if pd.notna(form):
            pieces.append("form edge " + _num(form))
        if pd.notna(pitcher):
            pieces.append("pitcher edge " + _num(pitcher))
        if pd.notna(winpct):
            pieces.append("win% edge " + _num(winpct))

        away_sp = _safe(row.get("away_probable_pitcher"))
        home_sp = _safe(row.get("home_probable_pitcher"))
        if away_sp and home_sp:
            pieces.append(f"{away_sp} vs {home_sp}")

    elif sport == "NBA":
        context = pd.to_numeric(row.get("historical_context_value"), errors="coerce")
        direction = _safe(row.get("context_direction"))
        if pd.notna(context):
            pieces.append("historical edge " + _num(context))
        if direction:
            pieces.append(_friendly(direction) + " context")

    elif sport == "NHL":
        context = pd.to_numeric(row.get("historical_context_value"), errors="coerce")
        direction = _safe(row.get("context_direction"))
        if pd.notna(context):
            pieces.append("form edge " + _num(context))
        if direction:
            pieces.append(_friendly(direction) + " context")

    return pieces


def _risk(row, sport):
    if sport == "NHL":
        blocks = sum(
            int(pd.to_numeric(row.get(col), errors="coerce") or 0)
            for col in ["away_injury_blocks", "home_injury_blocks"]
        )
        reviews = sum(
            int(pd.to_numeric(row.get(col), errors="coerce") or 0)
            for col in ["away_injury_reviews", "home_injury_reviews"]
        )
        if blocks:
            return f"{blocks} injury block(s)"
        if reviews:
            return f"{reviews} injury review(s)"

    if sport == "NBA":
        basis = _safe(row.get("context_basis"))
        if "PRIOR_SEASON" in basis.upper():
            return "Prior-season context"

    if sport == "MLB":
        away_work = pd.to_numeric(row.get("away_bullpen_workload"), errors="coerce")
        home_work = pd.to_numeric(row.get("home_bullpen_workload"), errors="coerce")
        if pd.notna(away_work) and pd.notna(home_work):
            high = max(away_work, home_work)
            if high >= 80:
                return "Heavy bullpen workload"

    return "No major research flag"


def render_game_betting_board(
    data,
    *,
    sport,
    accent,
    title,
    away_col,
    home_col,
    market_col,
    selection_col,
    line_col,
    evidence_col="evidence_score",
    book_col="sportsbook_count",
    approved_book_col=None,
    price_col="median_price_american",
    full_data=None,
    full_title=None,
):
    if data is None or data.empty:
        st.info(f"No qualified {sport} game research is available right now.")
        return

    board = data.copy()
    board["_score"] = pd.to_numeric(board.get(evidence_col), errors="coerce")
    board["_books"] = pd.to_numeric(
        board.get(
            approved_book_col
            if approved_book_col and approved_book_col in board.columns
            else book_col
        ),
        errors="coerce",
    )
    board["_price"] = pd.to_numeric(board.get(price_col), errors="coerce")

    board = board.sort_values(
        ["_score", "_books"],
        ascending=[False, False],
        na_position="last",
    )

    markets = [
        str(value).upper()
        for value in board[market_col].dropna().unique().tolist()
    ]

    ordered = [
        label
        for label in ["MONEYLINE", "SPREAD", "TOTAL"]
        if label in markets
    ]

    market_options = ["All"] + [
        {
            "MONEYLINE": "Moneyline",
            "SPREAD": "Spread",
            "TOTAL": "Total",
        }[market]
        for market in ordered
    ]

    if len(market_options) > 1:
        selected_market = st.pills(
            f"{sport} bet market",
            market_options,
            default="All",
            required=True,
            label_visibility="collapsed",
            key=f"{sport.lower()}_best_bets_market",
        )
    else:
        selected_market = "All"

    if selected_market == "All":
        visible = board.head(12).copy()
    else:
        reverse = {
            "Moneyline": "MONEYLINE",
            "Spread": "SPREAD",
            "Total": "TOTAL",
        }
        visible = board[
            board[market_col].astype(str).str.upper().eq(
                reverse[selected_market]
            )
        ].head(12).copy()

    counts = board[market_col].astype(str).str.upper().value_counts()

    count_bits = []
    for market in ordered:
        count_bits.append(
            f"{int(counts.get(market, 0))} "
            + {
                "MONEYLINE": "moneylines",
                "SPREAD": "spreads",
                "TOTAL": "totals",
            }[market]
        )

    st.caption(
        f"{len(board)} qualified {sport} game bet"
        + ("" if len(board) == 1 else "s")
        + ((" · " + " · ".join(count_bits)) if count_bits else "")
    )

    st.markdown(
        f"### {title if selected_market == 'All' else selected_market}"
    )
    st.caption(
        "Every visible bet already cleared the sport's qualification gates. "
        "The deeper evidence stays in the full board."
    )

    for start in range(0, len(visible), 3):
        cols = st.columns(3)

        for col, (_, row) in zip(cols, visible.iloc[start:start + 3].iterrows()):
            away = _safe(row.get(away_col))
            home = _safe(row.get(home_col))
            market = _safe(row.get(market_col)).upper()
            selection = _safe(row.get(selection_col))
            line = _line(row.get(line_col))

            if market == "MONEYLINE":
                pick = selection + " ML"
            else:
                pick = (selection + " " + line).strip()

            books = pd.to_numeric(row.get("_books"), errors="coerce")
            price = pd.to_numeric(row.get("_price"), errors="coerce")

            why = []
            if pd.notna(books):
                why.append(f"{int(books)} books")
            if pd.notna(price):
                why.append("market " + _odds(price))

            why.extend(_sport_reason(row, sport))

            risk = _risk(row, sport)

            with col:
                # Reuse the app's native premium card through Streamlit markup
                # so this helper stays visually consistent without importing pages.
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
                            {escape(away)} @ {escape(home)}
                        </div>
                        <div style="margin-top:4px;font-size:12px;font-weight:800;color:#64748B;text-transform:uppercase;">
                            {escape(_friendly(market))}
                        </div>
                        <div style="margin-top:5px;font-size:22px;font-weight:860;color:#102A43;line-height:1.1;">
                            {escape(pick)}
                        </div>
                        <div style="margin-top:7px;font-size:13.5px;font-weight:590;color:#435A73;line-height:1.42;">
                            {escape(" · ".join(why[:4]))}
                        </div>
                        <div style="margin-top:8px;display:flex;gap:5px;flex-wrap:wrap;">
                            <span style="padding:4px 8px;border-radius:999px;background:#ECFDF5;color:#047857;font-size:11.5px;font-weight:820;">
                                {escape(_evidence_label(row.get(evidence_col)))}
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
            full_title or f"Open full {sport} game research",
            expanded=False,
        ):
            st.dataframe(
                deep.drop(
                    columns=["_score", "_books", "_price"],
                    errors="ignore",
                ),
                width="stretch",
                hide_index=True,
            )
