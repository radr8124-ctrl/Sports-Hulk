from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import html

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "prop_intelligence" / "derived"
ET = ZoneInfo("America/New_York")


def _read(name):
    p = DERIVED / name
    try:
        return pd.read_csv(p, low_memory=False) if p.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _fmt(v, digits=1):
    try:
        if pd.isna(v):
            return "—"
        return f"{float(v):.{digits}f}"
    except Exception:
        return str(v) if v not in (None, "") else "—"


def _pct(v):
    try:
        if pd.isna(v):
            return "—"
        x = float(v)
        if 0 <= x <= 1:
            x *= 100
        return f"{x:.0f}%"
    except Exception:
        return "—"


def _event_day(v):
    try:
        dt = pd.to_datetime(v, errors="coerce", utc=True)
        if pd.isna(dt):
            return None
        return dt.tz_convert(ET).date()
    except Exception:
        return None


def _is_future_today(v):
    try:
        dt = pd.to_datetime(v, errors="coerce", utc=True)
        if pd.isna(dt):
            return False
        local = dt.tz_convert(ET)
        now = pd.Timestamp.now(tz="America/New_York")
        return local.date() == now.date() and local >= now
    except Exception:
        return False


def _ui_grade(row):
    """UI label only. Hulk Prop Score is market-quality research, not win probability."""
    try:
        score = float(row.get("hulk_prop_score", 0) or 0)
    except Exception:
        score = 0
    try:
        books = int(row.get("book_count", 0) or 0)
    except Exception:
        books = 0
    try:
        agree = float(row.get("book_agreement_pct", 0) or 0)
        if agree <= 1:
            agree *= 100
    except Exception:
        agree = 0
    signal = str(row.get("signal", "")).upper()

    if signal == "STRONG" and score >= 80 and books >= 5 and agree >= 75:
        return "HULK EDGE"
    if signal in {"STRONG", "LEAN"} and score >= 72 and books >= 5 and agree >= 70:
        return "HULK LEAN"
    if score >= 65 and books >= 3:
        return "WATCH"
    return "PASS"


def _card(row):
    player = html.escape(str(row.get("player", "")))
    market = html.escape(str(row.get("canonical_market", "")).replace("_", " ").title())
    direction = html.escape(str(row.get("market_direction", "NEUTRAL")).upper())
    score = _fmt(row.get("hulk_prop_score"), 1)
    books = int(row.get("book_count", 0) or 0)
    med = _fmt(row.get("market_median"), 1)
    low = _fmt(row.get("market_low"), 1)
    high = _fmt(row.get("market_high"), 1)
    agree = _pct(row.get("book_agreement_pct"))
    pp = _fmt(row.get("pp_line"), 1)
    gap = _fmt(row.get("pp_gap"), 1)
    grade = _ui_grade(row)
    badge = "edge" if grade == "HULK EDGE" else "lean" if grade == "HULK LEAN" else "watch"
    l5, l10, l20, season = (_pct(row.get(c)) for c in ["l5", "l10", "l20", "season"])
    return f"""
    <div class="hprop-card">
      <div class="hprop-top">
        <div><div class="hprop-player">{player}</div><div class="hprop-market">{market} · {direction}</div></div>
        <div class="hprop-score"><span>{score}</span><small>HULK PROP SCORE</small></div>
      </div>
      <div class="hprop-line">
        <div><b>{med}</b><small>Market Median</small></div>
        <div><b>{books}</b><small>Books</small></div>
        <div><b>{agree}</b><small>Agreement</small></div>
        <div><b>{low}–{high}</b><small>Market Range</small></div>
      </div>
      <div class="hprop-hit"><span>L5 <b>{l5}</b></span><span>L10 <b>{l10}</b></span><span>L20 <b>{l20}</b></span><span>Season <b>{season}</b></span></div>
      <div class="hprop-foot"><span class="hprop-badge {badge}">{grade}</span><span>PrizePicks <b>{pp}</b> · Gap <b>{gap}</b></span></div>
    </div>"""


def render_prop_intelligence(sport):
    sport = str(sport).upper()
    sig = _read("HULK_PROP_SIGNALS.csv")
    parlays = _read("HULK_PARLAYS_TODAY.csv")

    if sig.empty:
        st.info("Hulk Prop Intelligence cache is not available yet.")
        return

    sig = sig[sig.get("sport", pd.Series(index=sig.index, dtype=str)).astype(str).str.upper().eq(sport)].copy()
    if sig.empty:
        st.info(f"No {sport} prop intelligence rows are currently cached.")
        return

    st.html("""
    <style>
    .hprop-hero{display:flex;justify-content:space-between;align-items:end;background:linear-gradient(135deg,#101713,#0b0e0c);border:1px solid #26352a;border-radius:14px;padding:16px 18px;margin:4px 0 12px}
    .hprop-hero h2{margin:0;font-size:24px}.hprop-hero p{margin:4px 0 0;color:#9aa59d;font-size:12px}.hprop-live{color:#8cff55;font-weight:850;font-size:11px;letter-spacing:.06em}
    .hprop-section{font-size:15px;font-weight:950;margin:14px 0 7px}.hprop-section small{color:#87958b;font-size:10px;margin-left:7px}
    .hprop-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:8px 0 14px}.hprop-card{background:#101411;border:1px solid #263128;border-radius:14px;padding:13px;box-shadow:0 6px 18px #0004}
    .hprop-top{display:flex;justify-content:space-between;gap:12px}.hprop-player{font-weight:850;font-size:16px}.hprop-market{color:#9ba69f;font-size:11px;margin-top:2px}.hprop-score{text-align:right;color:#8cff55}.hprop-score span{font-size:23px;font-weight:900;display:block}.hprop-score small{font-size:8px;color:#839086}
    .hprop-line{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:11px 0 8px}.hprop-line div{background:#0b0e0c;border-radius:9px;padding:7px}.hprop-line b{display:block;font-size:13px}.hprop-line small{display:block;color:#7f8a82;font-size:8px;margin-top:2px}
    .hprop-hit{display:flex;flex-wrap:wrap;gap:6px}.hprop-hit span{background:#151b16;border:1px solid #29332b;border-radius:8px;padding:5px 7px;font-size:9px}.hprop-foot{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-top:9px;color:#aeb8b1;font-size:9px}
    .hprop-badge{border-radius:999px;padding:5px 8px;font-weight:850;border:1px solid}.hprop-badge.edge{background:#203221;color:#9aff63;border-color:#355239}.hprop-badge.lean{background:#1b2a20;color:#bdf49f;border-color:#355239}.hprop-badge.watch{background:#2f2918;color:#ffd96d;border-color:#5a4c24}
    .hprop-empty{padding:22px;text-align:center;border:1px dashed #304137;border-radius:12px;background:#0d110e;color:#98a39b}.hprop-empty b{display:block;color:#fff;font-size:15px;margin-bottom:4px}
    @media(max-width:800px){.hprop-grid{grid-template-columns:1fr}.hprop-line{grid-template-columns:repeat(2,1fr)}.hprop-live{display:none}}
    </style>
    """)

    # Daily action surface: today + not started. Upcoming research remains available only in the expander.
    today = sig[sig.get("event_time", pd.Series(index=sig.index, dtype=str)).apply(_is_future_today)].copy()
    if "hulk_prop_score" in today.columns:
        today["_ui_grade"] = today.apply(_ui_grade, axis=1)
        today = today.sort_values(["hulk_prop_score", "book_count"], ascending=False)
    else:
        today["_ui_grade"] = "PASS"

    edges = today[today["_ui_grade"].eq("HULK EDGE")].head(5)
    leans = today[today["_ui_grade"].eq("HULK LEAN")].head(5)
    watches = today[today["_ui_grade"].eq("WATCH")].head(8)

    st.html(f"""
    <div class="hprop-hero">
      <div><h2>🟢 {sport} Player Prop Intelligence</h2><p>Selective daily surface · sportsbook consensus · PrizePicks comparison · Hulk market-quality score</p></div>
      <div class="hprop-live">TODAY: {len(today)} MARKETS · {len(edges)} EDGE · {len(leans)} LEAN</div>
    </div>
    """)

    if edges.empty:
        st.html('<div class="hprop-empty"><b>No HULK EDGE qualifies right now.</b>Sports Hulk will not promote weaker props just to fill the page.</div>')
    else:
        st.html('<div class="hprop-section">🔥 BEST HULK PROPS TODAY <small>maximum 5</small></div>')
        st.html('<div class="hprop-grid">' + ''.join(_card(r) for _, r in edges.iterrows()) + '</div>')

    if not leans.empty:
        st.html('<div class="hprop-section">🟢 HULK LEANS <small>research-worthy, not promoted as bets</small></div>')
        st.html('<div class="hprop-grid">' + ''.join(_card(r) for _, r in leans.iterrows()) + '</div>')

    if not watches.empty:
        st.html('<div class="hprop-section">🟡 WORTH WATCHING <small>secondary market signals</small></div>')
        st.html('<div class="hprop-grid">' + ''.join(_card(r) for _, r in watches.iterrows()) + '</div>')

    with st.expander("🔬 Deep Research Board", expanded=False):
        research = sig.copy()
        research["UI Grade"] = research.apply(_ui_grade, axis=1)
        show = [c for c in ["player","canonical_market","market_direction","market_median","market_low","market_high","book_count","book_agreement_pct","over_price_median","under_price_median","pp_line","pp_gap","l3","l5","l10","l20","season","h2h","recent_avg","season_avg","hulk_prop_score","signal","UI Grade","event_time"] if c in research.columns]
        if "hulk_prop_score" in research.columns:
            research = research.sort_values("hulk_prop_score", ascending=False)
        st.dataframe(research[show], width="stretch", hide_index=True)

    if not parlays.empty and "sports" in parlays.columns:
        p = parlays[parlays["sports"].astype(str).str.contains(sport, case=False, na=False)]
        if not p.empty:
            st.subheader("Best Player Prop Parlays Today")
            st.dataframe(p, width="stretch", hide_index=True)
        else:
            st.caption("No qualified player-prop parlays for today's slate. Hulk will not manufacture a parlay when the qualified pool is empty.")
    else:
        st.caption("No qualified player-prop parlays for today's slate. Hulk will not manufacture a parlay when the qualified pool is empty.")

    st.caption("Hulk Prop Score is a market-quality research score, not a calibrated win probability.")
