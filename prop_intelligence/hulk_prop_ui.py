from pathlib import Path
import html
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "prop_intelligence" / "derived"
ET = ZoneInfo("America/New_York")

MLB_ABBR = {
    "Arizona Diamondbacks":"ari","Atlanta Braves":"atl","Baltimore Orioles":"bal","Boston Red Sox":"bos","Chicago Cubs":"chc","Chicago White Sox":"chw","Cincinnati Reds":"cin","Cleveland Guardians":"cle","Colorado Rockies":"col","Detroit Tigers":"det","Houston Astros":"hou","Kansas City Royals":"kc","Los Angeles Angels":"laa","Los Angeles Dodgers":"lad","Miami Marlins":"mia","Milwaukee Brewers":"mil","Minnesota Twins":"min","New York Mets":"nym","New York Yankees":"nyy","Athletics":"ath","Oakland Athletics":"oak","Philadelphia Phillies":"phi","Pittsburgh Pirates":"pit","San Diego Padres":"sd","San Francisco Giants":"sf","Seattle Mariners":"sea","St. Louis Cardinals":"stl","Tampa Bay Rays":"tb","Texas Rangers":"tex","Toronto Blue Jays":"tor","Washington Nationals":"wsh",
}
NFL_ABBR = {
    "Arizona Cardinals":"ari","Atlanta Falcons":"atl","Baltimore Ravens":"bal","Buffalo Bills":"buf","Carolina Panthers":"car","Chicago Bears":"chi","Cincinnati Bengals":"cin","Cleveland Browns":"cle","Dallas Cowboys":"dal","Denver Broncos":"den","Detroit Lions":"det","Green Bay Packers":"gb","Houston Texans":"hou","Indianapolis Colts":"ind","Jacksonville Jaguars":"jax","Kansas City Chiefs":"kc","Las Vegas Raiders":"lv","Los Angeles Chargers":"lac","Los Angeles Rams":"lar","Miami Dolphins":"mia","Minnesota Vikings":"min","New England Patriots":"ne","New Orleans Saints":"no","New York Giants":"nyg","New York Jets":"nyj","Philadelphia Eagles":"phi","Pittsburgh Steelers":"pit","San Francisco 49ers":"sf","Seattle Seahawks":"sea","Tampa Bay Buccaneers":"tb","Tennessee Titans":"ten","Washington Commanders":"wsh",
}


def _read(name):
    p = DERIVED / name
    try:
        return pd.read_csv(p, low_memory=False) if p.exists() and p.stat().st_size else pd.DataFrame()
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


def _time(v):
    try:
        d=pd.to_datetime(v,errors="coerce",utc=True)
        if pd.isna(d): return "—"
        return d.tz_convert(ET).strftime("%a %-m/%-d · %-I:%M %p ET")
    except Exception:
        return "—"


def _is_today(v):
    try:
        d=pd.to_datetime(v,errors="coerce",utc=True)
        return bool(pd.notna(d) and d.tz_convert(ET).date()==datetime.now(ET).date())
    except Exception:
        return False


def _logo(sport,team):
    mapping=MLB_ABBR if sport=="MLB" else NFL_ABBR if sport=="NFL" else {}
    code=mapping.get(str(team))
    if not code: return ""
    league="mlb" if sport=="MLB" else "nfl"
    return f'https://a.espncdn.com/i/teamlogos/{league}/500/{code}.png'


def _grade(score, books, signal):
    try: s=float(score)
    except Exception: s=0
    try: b=int(books)
    except Exception: b=0
    if str(signal).upper()=="STRONG" and b>=5: return "HULK EDGE"
    if s>=72 and b>=5: return "HULK LEAN"
    if s>=65 and b>=3: return "WATCH"
    return "PASS"


def _card(r,sport,deep=False):
    player=html.escape(str(r.get("player","—")))
    market=html.escape(str(r.get("canonical_market","—")).replace("_"," ").title())
    direction=html.escape(str(r.get("market_direction","NEUTRAL")).upper())
    team=str(r.get("team","—")); opp=str(r.get("opponent","—"))
    logo=_logo(sport,team); img=f'<img src="{logo}" alt="" loading="lazy">' if logo else ''
    try: books=int(float(r.get("book_count",0) or 0))
    except Exception: books=0
    score=_fmt(r.get("hulk_prop_score"),1); grade=_grade(r.get("hulk_prop_score"),books,r.get("signal"))
    med=_fmt(r.get("market_median"),1); low=_fmt(r.get("market_low"),1); high=_fmt(r.get("market_high"),1); agree=_pct(r.get("book_agreement_pct"))
    price_o=_fmt(r.get("over_price_median"),0); price_u=_fmt(r.get("under_price_median"),0); pp=_fmt(r.get("pp_line"),1); gap=_fmt(r.get("pp_gap"),1)
    recent=_fmt(r.get("recent_avg"),1); season=_fmt(r.get("season_avg"),1); h2h=_fmt(r.get("h2h"),1)
    meta=' · '.join(x for x in [team if team not in ("nan","—","") else "", f'vs {opp}' if opp not in ("nan","—","") else ""] if x)
    extra=''
    if deep:
        extra=(f'<div class="hprop-deep"><span>OVER PRICE <b>{price_o}</b></span><span>UNDER PRICE <b>{price_u}</b></span>'
               f'<span>RECENT AVG <b>{recent}</b></span><span>SEASON AVG <b>{season}</b></span><span>H2H <b>{h2h}</b></span>'
               f'<span>EVENT <b>{html.escape(_time(r.get("event_time")))}</b></span></div>')
    return (f'<div class="hprop-card"><div class="hprop-top"><div class="hprop-id">{img}<div><div class="hprop-player">{player}</div>'
            f'<div class="hprop-team">{html.escape(meta)}</div><div class="hprop-market">{market} · {direction}</div></div></div>'
            f'<div class="hprop-score"><span>{score}</span><small>HULK SCORE</small></div></div><div class="hprop-line">'
            f'<div><b>{med}</b><small>Consensus Line</small></div><div><b>{books}</b><small>Books</small></div>'
            f'<div><b>{agree}</b><small>Agreement</small></div><div><b>{low}–{high}</b><small>Market Range</small></div></div>'
            f'<div class="hprop-foot"><span class="hprop-badge">{html.escape(grade)}</span><span>PrizePicks <b>{pp}</b> · Gap <b>{gap}</b></span></div>{extra}</div>')


def render_prop_intelligence(sport):
    sport=str(sport).upper(); sig=_read("HULK_PROP_SIGNALS.csv"); parlays=_read("HULK_PARLAYS_TODAY.csv")
    if sig.empty:
        st.info("Hulk Prop Intelligence cache is not available yet."); return
    sig=sig[sig.get("sport",pd.Series(index=sig.index,dtype=str)).astype(str).str.upper().eq(sport)].copy()
    if sig.empty:
        st.info(f"No {sport} prop intelligence rows are currently cached."); return
    st.html("""
    <style>
    .hprop-wrap{font-family:Inter,system-ui,sans-serif;color:#f4f7f5}.hprop-hero{display:flex;justify-content:space-between;align-items:end;background:linear-gradient(135deg,#101713,#0b0e0c);border:1px solid #26352a;border-radius:18px;padding:18px 20px;margin:4px 0 14px}.hprop-hero h2{margin:0;font-size:28px}.hprop-hero p{margin:4px 0 0;color:#a3aea6;font-size:14px}.hprop-live{color:#8cff55;font-weight:900;font-size:12px;letter-spacing:.08em}.hprop-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:10px 0 16px}.hprop-card{background:#101411;border:1px solid #263128;border-radius:16px;padding:15px;box-shadow:0 6px 20px #0005}.hprop-top{display:flex;justify-content:space-between;gap:12px}.hprop-id{display:flex;gap:10px;align-items:center}.hprop-id img{width:44px;height:44px;object-fit:contain}.hprop-player{font-weight:900;font-size:19px}.hprop-team{color:#91a099;font-size:12px;margin-top:1px}.hprop-market{color:#abb6af;font-size:13px;margin-top:3px}.hprop-score{text-align:right;color:#8cff55}.hprop-score span{font-size:28px;font-weight:1000;display:block}.hprop-score small{font-size:9px;color:#839086}.hprop-line{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin:12px 0 9px}.hprop-line div{background:#0b0e0c;border-radius:10px;padding:9px}.hprop-line b{display:block;font-size:16px}.hprop-line small{display:block;color:#87928a;font-size:10px;margin-top:2px}.hprop-foot{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-top:10px;color:#aeb8b1;font-size:11px}.hprop-badge{background:#203221;color:#9aff63;border:1px solid #355239;border-radius:999px;padding:6px 9px;font-weight:900}.hprop-deep{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-top:10px}.hprop-deep span{background:#0b0f0c;border:1px solid #263128;border-radius:8px;padding:7px;color:#8e9a91;font-size:9px}.hprop-deep b{display:block;color:#fff;font-size:12px;margin-top:2px}.hdiag{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:10px 0 14px}.hdiag div{background:#0c1310;border:1px solid #28352c;border-radius:10px;padding:10px}.hdiag span{display:block;color:#829087;font-size:10px;font-weight:900}.hdiag b{display:block;color:#fff;font-size:20px;margin-top:2px}@media(max-width:800px){.hprop-grid{grid-template-columns:1fr}.hprop-line,.hdiag{grid-template-columns:repeat(2,1fr)}.hprop-deep{grid-template-columns:1fr 1fr}}
    </style>""")

    total=len(sig); today=int(sig["event_time"].apply(_is_today).sum()) if "event_time" in sig.columns else 0
    books=pd.to_numeric(sig.get("book_count",pd.Series(index=sig.index,dtype=float)),errors="coerce").fillna(0); min3=int(books.ge(3).sum())
    strong_mask=sig.get("signal",pd.Series(index=sig.index,dtype=str)).astype(str).str.upper().isin(["STRONG","LEAN"]); qualified=int((strong_mask & books.ge(3)).sum())
    latest="—"
    if "event_time" in sig.columns:
        dt=pd.to_datetime(sig["event_time"],errors="coerce",utc=True).dropna()
        if not dt.empty: latest=dt.max().tz_convert(ET).strftime("%a %-m/%-d %-I:%M %p ET")
    st.html(f'<div class="hprop-wrap"><div class="hprop-hero"><div><h2>🟢 {sport} Player Prop Intelligence</h2><p>Sportsbook consensus · PrizePicks comparison · market-quality score</p></div><div class="hprop-live">{total:,} CACHED MARKETS</div></div><div class="hdiag"><div><span>CACHED MARKETS</span><b>{total:,}</b></div><div><span>TODAY\'S EVENTS</span><b>{today:,}</b></div><div><span>3+ BOOK MARKETS</span><b>{min3:,}</b></div><div><span>QUALIFIED LEAN/STRONG</span><b>{qualified:,}</b></div></div></div>')
    if today==0:
        st.warning(f"No {sport} prop rows are tied to today's slate. Latest cached event: {latest}. This points to feed/slate freshness, not a reason to weaken thresholds.")
    elif qualified==0:
        st.info("Today's prop markets are present, but none clear the existing LEAN/STRONG + 3-book qualification rule. Thresholds were not lowered to fill the page.")

    today_sig=sig[sig["event_time"].apply(_is_today)].copy() if "event_time" in sig.columns else sig.copy()
    pool=today_sig if not today_sig.empty else sig.copy()
    pool["_score"]=pd.to_numeric(pool.get("hulk_prop_score",pd.Series(index=pool.index,dtype=float)),errors="coerce").fillna(0)
    pool_books=pd.to_numeric(pool.get("book_count",pd.Series(index=pool.index,dtype=float)),errors="coerce").fillna(0)
    pool_signal=pool.get("signal",pd.Series(index=pool.index,dtype=str)).astype(str).str.upper()
    q=pool[pool_signal.isin(["STRONG","LEAN"]) & pool_books.ge(3)].sort_values("_score",ascending=False)
    if not q.empty:
        st.subheader("Best Hulk Props Today")
        st.html('<div class="hprop-grid">'+''.join(_card(r,sport) for _,r in q.head(5).iterrows())+'</div>')
    watch=pool[~pool.index.isin(q.index)].sort_values("_score",ascending=False).head(8)
    if not watch.empty:
        st.subheader("Worth Watching")
        st.html('<div class="hprop-grid">'+''.join(_card(r,sport) for _,r in watch.iterrows())+'</div>')

    with st.expander("Deep Research Board",expanded=False):
        st.caption("Detailed cards keep every important column readable without a cut-off spreadsheet.")
        deep=pool.sort_values("_score",ascending=False).head(60)
        st.html('<div class="hprop-grid">'+''.join(_card(r,sport,deep=True) for _,r in deep.iterrows())+'</div>')
    with st.expander("Full Raw Prop Data",expanded=False):
        rename={"player":"Player","canonical_market":"Stat / Market","market_direction":"Lean","market_median":"Consensus Line","market_low":"Low","market_high":"High","book_count":"Books","book_agreement_pct":"Agreement %","over_price_median":"Over Price","under_price_median":"Under Price","pp_line":"PrizePicks Line","pp_gap":"PP Gap","l3":"L3","l5":"L5","l10":"L10","l20":"L20","season":"Season","h2h":"H2H","recent_avg":"Recent Avg","season_avg":"Season Avg","hulk_prop_score":"Hulk Score","signal":"Signal","event_time":"Start"}
        cols=[c for c in rename if c in sig.columns]; raw=sig[cols].rename(columns=rename)
        st.dataframe(raw,hide_index=True,width="stretch",height=560)

    if not parlays.empty and "sports" in parlays.columns:
        p=parlays[parlays["sports"].astype(str).str.contains(sport,case=False,na=False)]
        if not p.empty:
            st.subheader("Qualified Player-Prop Parlays Today")
            st.caption("These are player-prop parlays only. Game and mixed parlays live in the Parlay Center.")
            with st.expander("Qualified Prop Parlay Data",expanded=False): st.dataframe(p,hide_index=True,width="stretch")
        else:
            st.caption("No qualified player-prop parlays for today's slate. Game parlays are handled separately in Parlay Center.")
