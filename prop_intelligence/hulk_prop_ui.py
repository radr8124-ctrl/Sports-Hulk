
from pathlib import Path
import html
import pandas as pd
import streamlit as st

ROOT = Path("/home/ubuntu/sports-hulk")
DERIVED = ROOT / "prop_intelligence" / "derived"

def _read(name):
    p = DERIVED / name
    try:
        return pd.read_csv(p, low_memory=False) if p.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def _fmt(v, digits=1):
    try:
        if pd.isna(v): return "—"
        return f"{float(v):.{digits}f}"
    except Exception:
        return str(v) if v not in (None,"") else "—"

def _pct(v):
    try:
        if pd.isna(v): return "—"
        x=float(v)
        if 0 <= x <= 1: x*=100
        return f"{x:.0f}%"
    except Exception:
        return "—"

def _grade(score, books, signal):
    try: s=float(score)
    except Exception: s=0
    try: b=int(books)
    except Exception: b=0
    if str(signal).upper()=="STRONG" and b>=5: return "HULK EDGE"
    if s>=72 and b>=5: return "HULK LEAN"
    if s>=65 and b>=3: return "WATCH"
    return "PASS"

def _cards(rows):
    parts=[]
    for _,r in rows.iterrows():
        player=html.escape(str(r.get("player","")))
        market=html.escape(str(r.get("canonical_market","")).replace("_"," ").title())
        direction=html.escape(str(r.get("market_direction","NEUTRAL")).upper())
        score=_fmt(r.get("hulk_prop_score"),1)
        books=int(r.get("book_count",0) or 0)
        med=_fmt(r.get("market_median"),1)
        low=_fmt(r.get("market_low"),1)
        high=_fmt(r.get("market_high"),1)
        agree=_pct(r.get("book_agreement_pct"))
        pp=_fmt(r.get("pp_line"),1)
        gap=_fmt(r.get("pp_gap"),1)
        signal=html.escape(_grade(r.get("hulk_prop_score"),books,r.get("signal")))
        l5=_pct(r.get("l5")); l10=_pct(r.get("l10")); l20=_pct(r.get("l20")); season=_pct(r.get("season"))
        parts.append(f"""
        <div class="hprop-card">
          <div class="hprop-top">
            <div><div class="hprop-player">{player}</div><div class="hprop-market">{market} · {direction}</div></div>
            <div class="hprop-score"><span>{score}</span><small>HULK SCORE</small></div>
          </div>
          <div class="hprop-line">
            <div><b>{med}</b><small>Market Median</small></div>
            <div><b>{books}</b><small>Books</small></div>
            <div><b>{agree}</b><small>Agreement</small></div>
            <div><b>{low}–{high}</b><small>Market Range</small></div>
          </div>
          <div class="hprop-hit">
            <span>L5 <b>{l5}</b></span><span>L10 <b>{l10}</b></span><span>L20 <b>{l20}</b></span><span>Season <b>{season}</b></span>
          </div>
          <div class="hprop-foot">
            <span class="hprop-badge">{signal}</span>
            <span>PrizePicks: <b>{pp}</b> · Gap <b>{gap}</b></span>
          </div>
        </div>""")
    return "".join(parts)

def render_prop_intelligence(sport):
    sport=str(sport).upper()
    sig=_read("HULK_PROP_SIGNALS.csv")
    cons=_read("HULK_PROP_CONSENSUS.csv")
    parlays=_read("HULK_PARLAYS_TODAY.csv")

    if sig.empty:
        st.info("Hulk Prop Intelligence cache is not available yet.")
        return

    sig=sig[sig.get("sport",pd.Series(index=sig.index,dtype=str)).astype(str).str.upper().eq(sport)].copy()
    if sig.empty:
        st.info(f"No {sport} prop intelligence rows are currently cached.")
        return

    st.html("""
    <style>
    .hprop-wrap{font-family:Inter,system-ui,sans-serif;color:#f4f7f5}
    .hprop-hero{display:flex;justify-content:space-between;align-items:end;background:linear-gradient(135deg,#101713,#0b0e0c);border:1px solid #26352a;border-radius:18px;padding:18px 20px;margin:4px 0 14px}
    .hprop-hero h2{margin:0;font-size:25px}.hprop-hero p{margin:4px 0 0;color:#9aa59d;font-size:13px}
    .hprop-live{color:#8cff55;font-weight:800;font-size:12px;letter-spacing:.08em}
    .hprop-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:10px 0 16px}
    .hprop-card{background:#101411;border:1px solid #263128;border-radius:16px;padding:14px;box-shadow:0 6px 20px #0005}
    .hprop-top{display:flex;justify-content:space-between;gap:12px}.hprop-player{font-weight:850;font-size:17px}.hprop-market{color:#9ba69f;font-size:12px;margin-top:2px}
    .hprop-score{text-align:right;color:#8cff55}.hprop-score span{font-size:25px;font-weight:900;display:block}.hprop-score small{font-size:9px;color:#839086}
    .hprop-line{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin:12px 0 9px}.hprop-line div{background:#0b0e0c;border-radius:10px;padding:8px}
    .hprop-line b{display:block;font-size:14px}.hprop-line small{display:block;color:#7f8a82;font-size:9px;margin-top:2px}
    .hprop-hit{display:flex;flex-wrap:wrap;gap:7px}.hprop-hit span{background:#151b16;border:1px solid #29332b;border-radius:8px;padding:5px 7px;font-size:10px}
    .hprop-foot{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-top:10px;color:#aeb8b1;font-size:10px}
    .hprop-badge{background:#203221;color:#9aff63;border:1px solid #355239;border-radius:999px;padding:5px 8px;font-weight:800}
    @media(max-width:800px){.hprop-grid{grid-template-columns:1fr}.hprop-line{grid-template-columns:repeat(2,1fr)}}
    </style>
    """)

    strong=sig[sig["signal"].astype(str).str.upper().isin(["STRONG","LEAN"])].copy()
    strong=strong[strong.get("book_count",0)>=3] if "book_count" in strong else strong
    sort_cols=[c for c in ["hulk_prop_score","book_count"] if c in sig.columns]
    top=(strong if not strong.empty else sig).sort_values(sort_cols,ascending=False).head(10) if sort_cols else sig.head(10)

    n_books=int(pd.to_numeric(sig.get("book_count",pd.Series(dtype=float)),errors="coerce").max() or 0)
    n_lean=int(sig["signal"].astype(str).str.upper().isin(["LEAN","STRONG"]).sum())
    st.html(f"""
    <div class="hprop-wrap">
      <div class="hprop-hero">
        <div><h2>🟢 {sport} Player Prop Intelligence</h2><p>Sportsbook consensus · PrizePicks comparison · historical context · Hulk market-quality score</p></div>
        <div class="hprop-live">{len(sig):,} MARKETS · {n_lean} LEAN/STRONG · UP TO {n_books} BOOKS</div>
      </div>
      <div class="hprop-grid">{_cards(top)}</div>
    </div>
    """)

    with st.expander("Deep Research Board", expanded=False):
        show=[c for c in ["player","canonical_market","market_direction","market_median","market_low","market_high","book_count","book_agreement_pct","over_price_median","under_price_median","pp_line","pp_gap","l3","l5","l10","l20","season","h2h","recent_avg","season_avg","hulk_prop_score","signal","event_time"] if c in sig.columns]
        st.dataframe(sig[show].sort_values("hulk_prop_score",ascending=False) if "hulk_prop_score" in show else sig[show], use_container_width=True, hide_index=True)

    if not parlays.empty and "sports" in parlays.columns:
        p=parlays[parlays["sports"].astype(str).str.contains(sport,case=False,na=False)]
        if not p.empty:
            st.subheader("Best Player Prop Parlays Today")
            st.dataframe(p, use_container_width=True, hide_index=True)
        else:
            st.caption("No qualified player-prop parlays for today's slate. Hulk will not manufacture a parlay when the qualified pool is empty.")
