from pathlib import Path
import html
import json
import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
ET = ZoneInfo("America/New_York")
PROP_SCORE_GUARDRAIL = "Hulk Prop Score is not a calibrated win probability."

P = {
    "mlb": ROOT / "baseball_vault/derived/MLB_MATCHUP_BOARD_INTELLIGENCE.csv",
    "mlb_results": ROOT / "baseball_vault/history/MLB_GRADED_PREDICTIONS.csv",
    "mlb_market": ROOT / "baseball_vault/derived/MLB_MARKET_SIGNALS.csv",
    "nfl": ROOT / "nfl_live/derived/NFL_CURRENT_WEEK.csv",
    "cfb": ROOT / "college_vault/derived/CFB_CURRENT_BOARD.csv",
    "pp": ROOT / "prizepicks_live/derived/PRIZEPICKS_STANDARD.csv",
    "parlay": ROOT / "parlay_live/derived/NFL_PARLAY_MARKET_RAW.csv",
    "qualified_parlays": ROOT / "prop_intelligence/derived/HULK_PARLAYS_TODAY.csv",
    "fantasy": ROOT / "fantasy_live/derived/FANTASY_HULK_V2_ADP_BOARD.csv",
    "fantasy2": ROOT / "fantasy_live/derived/FANTASY_HULK_PPR_V2.csv",
    "profiles": ROOT / "fantasy_live/derived/FANTASY_LEAGUE_PROFILES.json",
    "survivor_entries": ROOT / "nfl_live/derived/SURVIVOR_ENTRIES.json",
    "mlb_history": ROOT / "baseball_vault/derived/MLB_GAME_MASTER.csv",
    "nfl_history": ROOT / "data_vault/derived/NFL_GAME_MASTER.csv",
    "cfb_history": ROOT / "college_vault/derived/CFB_GAME_MASTER.csv",
    "nfl_survivor": ROOT / "nfl_live/derived/NFL_SURVIVOR_BOARD.csv",
    "prop_signals": ROOT / "prop_intelligence/derived/HULK_PROP_SIGNALS.csv",
    "bet_tracker": ROOT / "data/derived/HULK_BET_TRACKER.json",
}

MLB_ABBR = {
    "Arizona Diamondbacks":"ari","Atlanta Braves":"atl","Baltimore Orioles":"bal","Boston Red Sox":"bos",
    "Chicago Cubs":"chc","Chicago White Sox":"chw","Cincinnati Reds":"cin","Cleveland Guardians":"cle",
    "Colorado Rockies":"col","Detroit Tigers":"det","Houston Astros":"hou","Kansas City Royals":"kc",
    "Los Angeles Angels":"laa","Los Angeles Dodgers":"lad","Miami Marlins":"mia","Milwaukee Brewers":"mil",
    "Minnesota Twins":"min","New York Mets":"nym","New York Yankees":"nyy","Athletics":"ath",
    "Oakland Athletics":"oak","Philadelphia Phillies":"phi","Pittsburgh Pirates":"pit","San Diego Padres":"sd",
    "San Francisco Giants":"sf","Seattle Mariners":"sea","St. Louis Cardinals":"stl","Tampa Bay Rays":"tb",
    "Texas Rangers":"tex","Toronto Blue Jays":"tor","Washington Nationals":"wsh",
}
NFL_ABBR = {
    "Arizona Cardinals":"ari","Atlanta Falcons":"atl","Baltimore Ravens":"bal","Buffalo Bills":"buf",
    "Carolina Panthers":"car","Chicago Bears":"chi","Cincinnati Bengals":"cin","Cleveland Browns":"cle",
    "Dallas Cowboys":"dal","Denver Broncos":"den","Detroit Lions":"det","Green Bay Packers":"gb",
    "Houston Texans":"hou","Indianapolis Colts":"ind","Jacksonville Jaguars":"jax","Kansas City Chiefs":"kc",
    "Las Vegas Raiders":"lv","Los Angeles Chargers":"lac","Los Angeles Rams":"lar","Miami Dolphins":"mia",
    "Minnesota Vikings":"min","New England Patriots":"ne","New Orleans Saints":"no","New York Giants":"nyg",
    "New York Jets":"nyj","Philadelphia Eagles":"phi","Pittsburgh Steelers":"pit","San Francisco 49ers":"sf",
    "Seattle Seahawks":"sea","Tampa Bay Buccaneers":"tb","Tennessee Titans":"ten","Washington Commanders":"wsh",
}


def load(key):
    path = P[key]
    try:
        return pd.read_csv(path, low_memory=False) if path.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def esc(v):
    return html.escape(str(v if v is not None else "—"))


def num(v, default=None):
    try:
        x = float(v)
        return default if math.isnan(x) else x
    except Exception:
        return default


def first(row, names, default="—"):
    for name in names:
        if name in row and pd.notna(row.get(name)):
            value = row.get(name)
            if str(value).strip() not in ("", "nan", "None"):
                return value
    return default


def parse_dt(value):
    try:
        dt = pd.to_datetime(value, errors="coerce", utc=True)
        return None if pd.isna(dt) else dt
    except Exception:
        return None


def is_today(value):
    dt = parse_dt(value)
    return bool(dt is not None and dt.tz_convert(ET).date() == datetime.now(ET).date())


def fmt_time(value):
    dt = parse_dt(value)
    if dt is None:
        return "—"
    return dt.tz_convert(ET).strftime("%-I:%M %p")


def age(key):
    try:
        sec = datetime.now().timestamp() - P[key].stat().st_mtime
        if sec < 60:
            return "just now"
        if sec < 3600:
            return f"{int(sec // 60)}m ago"
        if sec < 86400:
            return f"{int(sec // 3600)}h ago"
        return f"{int(sec // 86400)}d ago"
    except Exception:
        return "unknown"


def logo_url(sport, team):
    mapping = MLB_ABBR if sport == "MLB" else NFL_ABBR if sport == "NFL" else {}
    abbr = mapping.get(str(team))
    if not abbr:
        return ""
    league = "mlb" if sport == "MLB" else "nfl"
    return f"https://a.espncdn.com/i/teamlogos/{league}/500/{abbr}.png"


def matchup_html(sport, away, home):
    def one(team):
        url = logo_url(sport, team)
        img = f'<img src="{url}" alt="" loading="lazy">' if url else ""
        return f'<span class="team-chip">{img}<b>{esc(team)}</b></span>'
    return f'{one(away)}<span class="at">@</span>{one(home)}'


def fmt_datetime(value):
    dt = parse_dt(value)
    if dt is None:
        return "—"
    return dt.tz_convert(ET).strftime("%a %-m/%-d · %-I:%M %p ET")


def pct_value(value):
    x = num(value)
    if x is None:
        return "—"
    if 0 <= x <= 1:
        x *= 100
    return f"{x:.0f}%"


def research_table(df, cols=None, title="Deep Research / Full Data", height=520, rename=None):
    """Keep raw research available without making the spreadsheet the product surface."""
    if df is None or df.empty:
        return
    show = df.copy()
    if cols:
        cols = [c for c in cols if c in show.columns]
        if cols:
            show = show[cols]
    if rename:
        show = show.rename(columns={k:v for k,v in rename.items() if k in show.columns})
    with st.expander(title, expanded=False):
        st.caption("Full research data is preserved here for auditing. The main page above is the cleaned sports view.")
        st.dataframe((show if len(show.columns) <= 7 else show.iloc[:, :7]), hide_index=True, width="stretch", height=height, row_height=36)


def matchup_card(sport, away, home, start=None, metrics=None, badge=None, note=None, accent="blue"):
    metrics = metrics or []
    logos = matchup_html(sport, away, home) if sport in {"MLB","NFL"} else f'<b>{esc(away)}</b><span class="at">@</span><b>{esc(home)}</b>'
    items = ''.join(
        f'<div class="clean-metric"><span>{esc(label)}</span><b>{esc(value)}</b></div>'
        for label,value in metrics if value not in (None, "", "nan")
    )
    badge_html = f'<span class="clean-badge {esc(str(accent))}">{esc(badge)}</span>' if badge else ''
    note_html = f'<div class="clean-note">{esc(note)}</div>' if note else ''
    return (
        f'<div class="clean-game-card {esc(str(accent))}">'
        f'<div class="clean-game-top"><div><div class="clean-matchup">{logos}</div><div class="clean-time">{esc(fmt_datetime(start) if start is not None else "")}</div></div>{badge_html}</div>'
        f'<div class="clean-metrics">{items}</div>{note_html}</div>'
    )


def player_card(name, team="—", position="", metrics=None, badge=None, sport=None, accent="green", note=None):
    metrics = metrics or []
    img = ''
    if sport in {"MLB","NFL"} and team not in (None,"","—"):
        u = logo_url(sport, team)
        if u:
            img = f'<img src="{u}" alt="" loading="lazy">'
    meta = ' · '.join(x for x in [str(team) if team not in (None,"","—") else "", str(position) if position not in (None,"","—") else ""] if x)
    items=''.join(f'<div class="clean-metric"><span>{esc(k)}</span><b>{esc(v)}</b></div>' for k,v in metrics if v not in (None,"","nan"))
    badge_html=f'<span class="clean-badge {esc(str(accent))}">{esc(badge)}</span>' if badge else ''
    note_html=f'<div class="clean-note">{esc(note)}</div>' if note else ''
    return f'<div class="clean-player-card {esc(str(accent))}"><div class="clean-player-top">{img}<div><div class="clean-player-name">{esc(name)}</div><div class="clean-player-meta">{esc(meta)}</div></div>{badge_html}</div><div class="clean-metrics">{items}</div>{note_html}</div>'


def _prop_rows_for_today(sport=None):
    d=load("prop_signals")
    if d.empty:
        return d
    if sport and "sport" in d.columns:
        d=d[d["sport"].astype(str).str.upper().eq(str(sport).upper())].copy()
    if "event_time" in d.columns:
        d=d[d["event_time"].apply(is_today)].copy()
    return d


def _game_leg_pool(sport):
    rows={"MLB":rows_mlb,"NFL":rows_nfl,"CFB":rows_cfb}.get(sport,lambda:[])()
    if sport=="MLB":
        rows=[r for r in rows if r.get("action") in {"BET","WATCH"}]
    elif sport=="CFB":
        rows=[r for r in rows if str(r.get("confidence","")).upper() in {"HIGH","MEDIUM"}]
    # NFL rows are market research; retain strongest market-backed rows.
    out=[]
    for r in rows:
        out.append({
            "kind":"GAME","sport":sport,"event":f'{r.get("away")} @ {r.get("home")}',"pick":r.get("pick","—"),
            "market":r.get("metric_label","GAME"),"line":r.get("metric","—"),"source":("Hulk MLB model" if sport=="MLB" else "Sportsbook market research" if sport=="NFL" else "CFB research"),
            "action":r.get("action","RESEARCH"),"start":r.get("start"),"away":r.get("away"),"home":r.get("home"),"confidence":r.get("confidence","—")
        })
    return out


def _prop_leg_pool(sport):
    d=_prop_rows_for_today(sport)
    if d.empty:
        return []
    books=pd.to_numeric(d.get("book_count",pd.Series(index=d.index,dtype=float)),errors="coerce").fillna(0)
    sig=d.get("signal",pd.Series(index=d.index,dtype=str)).astype(str).str.upper()
    d=d[sig.isin(["STRONG","LEAN"]) & books.ge(3)].copy()
    if d.empty:
        return []
    d["_score"]=pd.to_numeric(d.get("hulk_prop_score",pd.Series(index=d.index,dtype=float)),errors="coerce").fillna(0)
    d=d.sort_values(["_score"],ascending=False)
    out=[]
    seen=set()
    for _,r in d.iterrows():
        event=str(r.get("event_id") or r.get("event_time") or "")
        key=(event,str(r.get("player")),str(r.get("canonical_market")))
        if key in seen: continue
        seen.add(key)
        out.append({"kind":"PROP","sport":sport,"event":event,"pick":f'{r.get("player","—")} {str(r.get("market_direction","—")).upper()}',"market":str(r.get("canonical_market","—")).replace("_"," ").title(),"line":r.get("market_median","—"),"source":f'{int(num(r.get("book_count"),0) or 0)}-book consensus',"action":str(r.get("signal","LEAN")).upper(),"start":r.get("event_time"),"player":r.get("player","—"),"score":r.get("hulk_prop_score","—")})
    return out


def css():
    st.markdown(r"""
    <style>
    :root{--bg:#05080b;--panel:#0a1219;--panel2:#0d1720;--line:#172936;--g:#55ff32;--p:#b978ff;--b:#4cc2ff;--a:#ffc247;--r:#ff5c61;--m:#93a2ad;--txt:#f6f8fa}
    .block-container{max-width:1640px!important;padding:12px 24px 40px!important} .stApp{font-size:17px} .stMarkdown p,.stCaption,.stAlert{font-size:16px!important;line-height:1.52!important} div[data-testid="stDataFrame"]{font-size:16px!important}
    header[data-testid="stHeader"]{background:transparent}
    section[data-testid="stSidebar"]{background:linear-gradient(180deg,#060a0d,#081017 65%,#060a0d);border-right:1px solid #13202b}
    section[data-testid="stSidebar"] div[role="radiogroup"] label{border-radius:9px;padding:9px 10px;margin:3px 0;border:1px solid transparent;font-size:15px!important;font-weight:800}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){background:linear-gradient(90deg,rgba(85,255,50,.20),rgba(85,255,50,.04));border-color:rgba(85,255,50,.35)}
    div[data-testid="stRadio"] div[role="radiogroup"]{gap:.45rem}
    div[data-testid="stRadio"] div[role="radiogroup"] label{background:#09131b;border:1px solid #183044;border-radius:8px;padding:10px 15px;font-size:15px!important;font-weight:800}
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked){background:linear-gradient(180deg,rgba(85,255,50,.16),rgba(85,255,50,.08));border-color:rgba(85,255,50,.55)}
    .sh-topbar{display:flex;justify-content:space-between;align-items:center;background:linear-gradient(180deg,#081119,#060b10);border:1px solid #142330;border-radius:12px;padding:12px 15px;margin-bottom:10px}
    .brand-wrap{display:flex;align-items:center;gap:12px}.brand-orb{width:46px;height:46px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#a3ff52 0,#41df23 28%,#0c3212 70%,#061008 100%);box-shadow:0 0 22px rgba(85,255,50,.22);border:1px solid rgba(85,255,50,.35)}
    .brand-title{font-weight:1000;font-size:35px;letter-spacing:-.02em}.brand-title span{color:var(--g)}.brand-sub{font-size:12px;letter-spacing:.17em;color:#d8dee3}.update-box{font-size:13px;color:#cbd5dc;text-align:right}.online{color:var(--g);font-weight:900}
    .sport-banner{display:flex;justify-content:space-between;align-items:end;gap:16px;margin:2px 0 10px;padding:0 2px}.sport-name{font-size:35px;font-weight:1000}.sport-sub{font-size:16px;color:var(--m);margin-top:2px}.source-pill{padding:7px 11px;border-radius:999px;border:1px solid #244052;background:#0b1720;color:#b9c7d1;font-size:10px;font-weight:850}
    .kpi-row{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:9px;margin-bottom:10px}.kpi{background:linear-gradient(180deg,#0b151d,#081018);border:1px solid #152839;border-radius:10px;min-height:88px;padding:12px 13px;position:relative;overflow:hidden}.kpi:after{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;background:linear-gradient(90deg,transparent,var(--g),transparent);opacity:.35}
    .kpi .lbl{font-size:12px;color:var(--m);font-weight:850;letter-spacing:.05em;text-transform:uppercase}.kpi .val{font-size:27px;font-weight:1000;color:#fff;margin:4px 0 2px}.kpi .note{font-size:12px;color:#8fa0ac}.kpi.green .val{color:var(--g)}.kpi.purple .val{color:var(--p)}.kpi.blue .val{color:var(--b)}.kpi.amber .val{color:var(--a)}
    .panel{background:linear-gradient(180deg,#0b141c,#081017);border:1px solid #152735;border-radius:10px;padding:12px}.panel+.panel{margin-top:10px}.phead{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}.ptitle{font-size:22px;font-weight:1000;letter-spacing:.025em}.psub{font-size:12px;color:var(--m)}
    .plays-head,.play-row{display:grid;grid-template-columns:70px minmax(240px,1.7fr) minmax(120px,.9fr) 95px 105px 110px 88px;gap:8px;align-items:center}.plays-head{background:#0e1922;border:1px solid #172b3a;border-radius:7px;padding:10px;font-size:12px;color:#aeb9c2;font-weight:900}.play-row{padding:12px 9px;border-bottom:1px solid #13232f;font-size:15px}.matchup-flex{display:flex;align-items:center;gap:6px;min-width:0}.team-chip{display:inline-flex;align-items:center;gap:5px;min-width:0}.team-chip img{width:24px;height:24px;object-fit:contain}.team-chip b{white-space:normal;overflow:visible;text-overflow:clip;line-height:1.15;overflow-wrap:anywhere}.at{color:#657681;font-weight:800}.dim{color:#93a2ad}.pick{font-weight:950;color:#fff}.badge{display:inline-flex;align-items:center;justify-content:center;padding:8px 11px;border-radius:8px;font-weight:1000;text-align:center;border:1px solid;font-size:14px;line-height:1.15;white-space:normal;overflow-wrap:anywhere;max-width:180px}.bet{background:rgba(85,255,50,.12);border-color:rgba(85,255,50,.34);color:#a9ff8f}.watch{background:rgba(255,194,71,.10);border-color:rgba(255,194,71,.34);color:#ffd66c}.research{background:rgba(76,194,255,.10);border-color:rgba(76,194,255,.34);color:#8ed8ff}.pass{background:rgba(255,92,97,.10);border-color:rgba(255,92,97,.34);color:#ff8589}.good{color:var(--g)}.warn{color:var(--a)}.bad{color:var(--r)}.blue{color:var(--b)}.purple{color:var(--p)}
    .two-col{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(320px,.8fr);gap:10px;align-items:start}.stack{display:flex;flex-direction:column;gap:10px}.info-row{display:grid;grid-template-columns:minmax(0,1.5fr) .7fr .7fr;gap:8px;padding:9px 5px;border-bottom:1px solid #13232f;font-size:13px}.info-row b{color:#fff}.empty{padding:28px 16px;text-align:center;border:1px dashed #284052;border-radius:9px;background:#091119}.empty b{font-size:16px}.empty span{display:block;color:var(--m);font-size:13px;margin-top:5px}
    .mini-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:10px}.system-row{display:flex;justify-content:space-between;gap:12px;padding:9px 4px;border-bottom:1px solid #13232f;font-size:13px}.system-row .status-ok{color:var(--g);font-weight:900}.system-row .status-info{color:var(--b);font-weight:900}
    .command-hero{position:relative;overflow:hidden;background:radial-gradient(circle at 80% 20%,rgba(85,255,50,.24),transparent 34%),linear-gradient(135deg,#0b1b13,#071019 55%,#0a0d12);border:1px solid rgba(85,255,50,.38);border-radius:18px;padding:22px 24px;margin:4px 0 12px;box-shadow:0 0 34px rgba(85,255,50,.08)}
    .command-eyebrow{font-size:12px;letter-spacing:.18em;color:#9aff76;font-weight:950}.command-title{font-size:46px;line-height:1.05;font-weight:1000;margin:4px 0;color:#fff}.command-title span{color:var(--g)}.command-sub{font-size:16px;color:#b8c5cd;max-width:940px}.command-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:10px 0}.action-card{background:linear-gradient(145deg,#0c171f,#081017);border:1px solid #193142;border-radius:12px;padding:14px;min-height:118px}.action-card.green{border-color:rgba(85,255,50,.32)}.action-card.purple{border-color:rgba(185,120,255,.35)}.action-card.amber{border-color:rgba(255,194,71,.35)}.action-kicker{font-size:11px;color:#8fa0ac;font-weight:900;letter-spacing:.07em}.action-value{font-size:25px;font-weight:1000;margin:5px 0}.action-copy{font-size:14px;color:#9fb0ba;line-height:1.45}.vault-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.vault-item{background:#0c161e;border:1px solid #172a38;border-radius:9px;padding:11px}.vault-item b{font-size:22px;color:#fff;display:block}.vault-item span{font-size:11px;color:#91a0aa}.pp-card-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.pp-player-card{background:linear-gradient(180deg,#121020,#0c0b16);border:1px solid rgba(185,120,255,.30);border-radius:12px;padding:13px}.pp-player-top{display:flex;align-items:center;gap:9px}.pp-player-top img{width:34px;height:34px;object-fit:contain}.pp-player{font-size:16px;font-weight:950}.pp-team{font-size:11px;color:#9c90aa}.pp-stat{font-size:12px;color:#bdb4ca;margin-top:8px}.pp-line-big{font-size:26px;font-weight:1000;color:var(--p);margin-top:2px}.pp-start{font-size:10px;color:#83798e;margin-top:3px}
    .league-actions{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px;margin:0 0 12px}.league-action{background:linear-gradient(180deg,#0d1922,#091119);border:1px solid #1b3445;border-radius:11px;padding:11px 12px}.league-action b{display:block;color:#fff;font-size:14px}.league-action span{display:block;color:#91a3ae;font-size:11px;margin-top:2px}.command-hero:before{content:"";position:absolute;inset:-2px;background:linear-gradient(90deg,transparent,rgba(85,255,50,.12),transparent);filter:blur(22px);pointer-events:none}.pp-research{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin-top:9px}.pp-research span{background:#0a1118;border:1px solid #20293a;border-radius:6px;padding:6px;font-size:10px}.survivor-warning{border:1px solid rgba(255,194,71,.36);background:rgba(255,194,71,.07);padding:10px 12px;border-radius:8px;margin:7px 0;color:#ffd66c;font-weight:800}
    .accent-blue{border-color:rgba(61,151,255,.48)!important;box-shadow:inset 0 1px 0 rgba(61,151,255,.12)}
    .accent-purple{border-color:rgba(181,93,255,.48)!important;box-shadow:inset 0 1px 0 rgba(181,93,255,.12)}
    .accent-gold{border-color:rgba(255,180,48,.50)!important;box-shadow:inset 0 1px 0 rgba(255,180,48,.12)}
    .accent-red{border-color:rgba(255,80,85,.46)!important;box-shadow:inset 0 1px 0 rgba(255,80,85,.11)}
    .accent-cyan{border-color:rgba(39,218,255,.45)!important;box-shadow:inset 0 1px 0 rgba(39,218,255,.11)}
    .spectrum-strip{height:4px;border-radius:999px;background:linear-gradient(90deg,#62ff37,#2f9cff,#b568ff,#ffb62e,#ff515b,#22d8ff);margin:0 0 12px}
    .market-card{border:1px solid #1d3140;border-radius:10px;padding:11px 12px;margin:7px 0;background:linear-gradient(135deg,#0b151e,#0a1118);display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center}
    .market-match{font-size:15px;font-weight:950;color:#fff}.market-signal{font-size:12px;color:#93a6b3;margin-top:3px;line-height:1.35}.market-meta{text-align:right}.market-books{font-size:12px;color:#a9b8c2}.market-strength{font-size:17px;font-weight:1000;color:#66ff48;margin-top:3px}
    .league-hero{border-radius:16px;padding:18px 20px;margin:4px 0 12px;border:1px solid #24374a;background:linear-gradient(115deg,#0a1219,#111521);position:relative;overflow:hidden}.league-hero:after{content:"";position:absolute;inset:auto -8% -55% 35%;height:180px;background:radial-gradient(circle,rgba(71,150,255,.18),rgba(181,93,255,.10),transparent 70%);pointer-events:none}.league-hero.cfb{border-color:rgba(255,180,48,.40);background:linear-gradient(115deg,#171007,#10131b 45%,#111024)}.league-hero.mlb{border-color:rgba(61,151,255,.43);background:linear-gradient(115deg,#07131f,#0b1119 45%,#101023)}
    .league-eyebrow{font-size:12px;font-weight:950;letter-spacing:.15em;color:#9db0bd}.league-title{font-size:36px;font-weight:1000;color:#fff;line-height:1.08;margin:4px 0}.league-title .blue{color:#54a4ff}.league-title .gold{color:#ffc14e}.league-copy{font-size:15px;color:#b4c1ca;max-width:920px}.league-stat-row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin:10px 0 12px}.league-stat{background:#0b141c;border:1px solid #1b2c3a;border-radius:11px;padding:13px}.league-stat .t{font-size:11px;color:#8da0ad;font-weight:900;text-transform:uppercase}.league-stat .n{font-size:28px;font-weight:1000;margin-top:2px;color:#fff}.league-stat.blue .n{color:#54a4ff}.league-stat.purple .n{color:#c47cff}.league-stat.gold .n{color:#ffc14e}.league-stat.red .n{color:#ff7378}
    .pick-card{background:linear-gradient(145deg,#0b151e,#091119);border:1px solid #203444;border-radius:12px;padding:14px;margin:8px 0}.pick-card.cfb{border-left:4px solid #ffc14e}.pick-card.mlb{border-left:4px solid #54a4ff}.pick-top{display:flex;justify-content:space-between;gap:10px;align-items:start}.pick-match{font-size:17px;font-weight:1000;color:#fff}.pick-time{font-size:12px;color:#91a3af;margin-top:2px}.pick-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-top:11px}.pick-metric{background:#0b1219;border:1px solid #172736;border-radius:8px;padding:8px}.pick-metric .l{font-size:10px;color:#7f919e;font-weight:900}.pick-metric .v{font-size:17px;color:#fff;font-weight:1000;margin-top:3px;line-height:1.18;overflow-wrap:anywhere;word-break:normal}.empty-rich{padding:18px;border-radius:12px;background:linear-gradient(135deg,rgba(61,151,255,.10),rgba(181,93,255,.08));border:1px solid rgba(61,151,255,.24)}.empty-rich b{font-size:18px;color:#fff}.empty-rich span{display:block;font-size:14px;color:#aab8c2;margin-top:5px;line-height:1.45}

    .clean-game-grid,.clean-player-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:10px 0 14px}
    .clean-game-card,.clean-player-card{background:linear-gradient(145deg,#0b151e,#081017);border:1px solid #203444;border-left:4px solid #4cc2ff;border-radius:14px;padding:15px;box-shadow:0 7px 20px #0004}
    .clean-game-card.green,.clean-player-card.green{border-left-color:#55ff32}.clean-game-card.purple,.clean-player-card.purple{border-left-color:#b978ff}.clean-game-card.gold,.clean-player-card.gold{border-left-color:#ffc247}.clean-game-card.red,.clean-player-card.red{border-left-color:#ff5c61}.clean-game-card.cyan,.clean-player-card.cyan{border-left-color:#22d8ff}
    .clean-game-top,.clean-player-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.clean-player-top{align-items:center}.clean-player-top img{width:46px;height:46px;object-fit:contain;flex:0 0 auto}
    .clean-matchup{font-size:20px;font-weight:1000;color:#fff;line-height:1.2;overflow-wrap:anywhere}.clean-matchup .team-chip img{width:34px;height:34px}.clean-time{font-size:13px;color:#9dafba;margin-top:5px}.clean-player-name{font-size:19px;font-weight:1000;color:#fff}.clean-player-meta{font-size:12px;color:#91a3ae;margin-top:2px}
    .clean-badge{margin-left:auto;border-radius:12px;padding:10px 14px;border:1px solid #2a4050;font-size:18px;line-height:1.05;font-weight:1000;white-space:normal;overflow-wrap:anywhere;text-align:center;min-width:54px;max-width:180px;background:#0d1820;box-shadow:0 0 0 1px #0003 inset}.clean-badge.green{color:#b8ff9f;border-color:#4c8d48;background:linear-gradient(180deg,#17311a,#0e1d10)}.clean-badge.blue{color:#8ad5ff;border-color:#3275a5;background:linear-gradient(180deg,#112a3d,#0b1b28)}.clean-badge.purple{color:#ddb9ff;border-color:#744fa1;background:linear-gradient(180deg,#28173a,#180f23)}.clean-badge.gold{color:#ffe08d;border-color:#8e6b29;background:linear-gradient(180deg,#34270d,#201805)}.clean-badge.red{color:#ff9ba0;border-color:#9c454a;background:linear-gradient(180deg,#351719,#211011)}.clean-badge.cyan{color:#8ff3ff;border-color:#2f7f8b;background:linear-gradient(180deg,#0e3036,#0a1d21)}
    .clean-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-top:13px}.clean-metric{background:#091119;border:1px solid #172a38;border-radius:9px;padding:9px;min-width:0}.clean-metric span{display:block;color:#93a6b3;font-size:12px;line-height:1.15;font-weight:950;text-transform:uppercase;letter-spacing:.035em}.clean-metric b{display:block;color:#fff;font-size:18px;line-height:1.18;margin-top:4px;overflow-wrap:anywhere;word-break:normal}.clean-note{font-size:12px;line-height:1.45;color:#aab8c2;margin-top:10px}
    .matchup-hero{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:18px;background:radial-gradient(circle at 50% 0,rgba(76,194,255,.15),transparent 48%),linear-gradient(135deg,#0a151e,#080f15);border:1px solid #203848;border-radius:18px;padding:20px;margin:10px 0 14px}.matchup-team{text-align:center}.matchup-team img{width:86px;height:86px;object-fit:contain}.matchup-team b{display:block;font-size:24px;color:#fff;margin-top:6px}.matchup-mid{text-align:center;color:#8fa0ac}.matchup-mid strong{display:block;font-size:20px;color:#fff;margin:4px 0}.research-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:10px 0}.research-summary>div{background:#0a131b;border:1px solid #1a2e3d;border-radius:10px;padding:11px}.research-summary span{display:block;color:#8295a1;font-size:10px;font-weight:900;text-transform:uppercase}.research-summary b{display:block;color:#fff;font-size:18px;margin-top:3px}
    @media(max-width:1180px){.clean-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.mock-play-head,.mock-play{grid-template-columns:64px minmax(190px,1.35fr) minmax(130px,.9fr) 84px 88px 76px}.mock-match{font-size:13px}.mock-pick{font-size:14px;padding:8px 10px}.clean-badge{font-size:17px}.pick-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
    @media(max-width:900px){.clean-game-grid,.clean-player-grid{grid-template-columns:1fr}.clean-metrics,.research-summary{grid-template-columns:repeat(2,1fr)}.matchup-hero{grid-template-columns:1fr}.matchup-team img{width:64px;height:64px}}
    @media(max-width:1050px){.league-stat-row,.pick-grid{grid-template-columns:repeat(2,1fr)}}
    .st-key-mobile_nav_shell{display:none}
    @media(max-width:1050px){.league-actions{grid-template-columns:repeat(3,1fr)}.command-grid,.pp-card-grid{grid-template-columns:1fr 1fr}.kpi-row{grid-template-columns:repeat(3,1fr)}.two-col,.mini-grid{grid-template-columns:1fr}.plays-head,.play-row{grid-template-columns:62px minmax(190px,1.6fr) 110px 90px 88px}.plays-head>*:nth-child(6),.plays-head>*:nth-child(7),.play-row>*:nth-child(6),.play-row>*:nth-child(7){display:none}}
    @media(max-width:720px){.league-actions,.command-grid,.pp-card-grid,.vault-grid{grid-template-columns:1fr}.command-title{font-size:30px}.st-key-mobile_nav_shell{display:block!important}.kpi-row{grid-template-columns:repeat(2,1fr)}.brand-title{font-size:22px}.brand-orb{width:38px;height:38px}.update-box{display:none}.plays-head,.play-row{grid-template-columns:56px minmax(145px,1.5fr) 90px 78px}.plays-head>*:nth-child(n+5),.play-row>*:nth-child(n+5){display:none}.team-chip img{width:20px;height:20px}.sport-banner{align-items:start;flex-direction:column}}
    </style>
    """, unsafe_allow_html=True)


def nav(menu, mode):
    menu = list(menu)
    slug = re.sub(r"[^a-z0-9]+", "_", mode.lower()).strip("_")
    current_key, side_key, mobile_key = f"hc_{slug}", f"hs_{slug}", f"hm_{slug}"
    if st.session_state.get(current_key) not in menu:
        st.session_state[current_key] = menu[0]
    def side_changed():
        st.session_state[current_key] = st.session_state[side_key]
    def mobile_changed():
        st.session_state[current_key] = st.session_state[mobile_key]
    idx = menu.index(st.session_state[current_key])
    st.sidebar.radio("Navigation", menu, index=idx, key=side_key, label_visibility="collapsed", on_change=side_changed)
    with st.container(key="mobile_nav_shell"):
        st.radio("Quick Navigation", menu, index=idx, key=mobile_key, horizontal=True, label_visibility="collapsed", on_change=mobile_changed)
    return st.session_state[current_key]


def topbar(mode, source="Oracle cache"):
    names = {"🎯 Betting":"BETTING HULK","⚾ MLB":"BASEBALL HULK","🏈 NFL":"NFL HULK","🏟️ College Football":"CFB HULK","🟣 PrizePicks":"PRIZEPICKS HULK","🏆 Fantasy":"FANTASY HULK"}
    current = names.get(mode, "SPORTS HULK")
    st.markdown(f'''<div class="sh-topbar"><div class="brand-wrap"><div class="brand-orb"></div><div><div class="brand-title">SPORTS <span>HULK</span></div><div class="brand-sub">DOMINATE. EVERY DAY.</div></div></div><div class="update-box"><b>{current}</b><br>{esc(source)}<br><span class="online">● SYSTEM ONLINE</span></div></div>''', unsafe_allow_html=True)


def rows_mlb():
    d = load("mlb")
    out = []
    for _, r in d.iterrows():
        start = first(r, ["gameDate", "game_date", "start"], None)
        if not is_today(start):
            continue
        decision = str(first(r, ["decision"], "PASS")).upper()
        if decision not in {"BET", "WATCH", "PASS"}:
            decision = "WATCH"
        away, home = first(r, ["away_team"], ""), first(r, ["home_team"], "")
        lean = first(r, ["lean", "hulk_model_side"], "—")
        conf = str(first(r, ["confidence"], "—")).upper()
        edge = num(first(r, ["home_edge_score"], None))
        hist = num(first(r, ["comp_bucket_hist_accuracy", "comp_home_win_rate"], None))
        books = int(num(first(r, ["h2h_book_count"], 0), 0) or 0)
        out.append({
            "sport":"MLB","start":start,"time":fmt_time(start),"away":away,"home":home,"pick":lean,
            "confidence":conf,"metric":f"{edge:+.3f}" if edge is not None else "—","metric_label":"MODEL EDGE",
            "market":f"{books} books" if books else "—","detail":f"Hist {hist*100:.0f}%" if hist is not None and 0 <= hist <= 1 else "Official MLB model",
            "action":decision,"sort":3 if decision=="BET" else 2 if decision=="WATCH" else 1,
        })
    return sorted(out, key=lambda x:(x["sort"], x["confidence"]=="HIGH"), reverse=True)


def rows_nfl():
    d = load("nfl")
    out = []
    for _, r in d.iterrows():
        start = first(r, ["start", "commence_time", "start_time"], None)
        if not is_today(start):
            continue
        hp = num(first(r, ["home_market_win_prob"], None)); ap = num(first(r, ["away_market_win_prob"], None))
        if hp is None and ap is None:
            continue
        away, home = first(r, ["away_team"], ""), first(r, ["home_team"], "")
        pick, prob = (home, hp) if hp is not None and (ap is None or hp >= ap) else (away, ap)
        books = int(num(first(r, ["sportsbooks"], 0), 0) or 0)
        spread = first(r, ["home_spread"], "—") if pick == home else first(r, ["away_spread"], "—")
        out.append({
            "sport":"NFL","start":start,"time":fmt_time(start),"away":away,"home":home,"pick":pick,
            "confidence":f"{prob*100:.0f}% MKT" if prob is not None else "—","metric":str(spread),"metric_label":"SPREAD",
            "market":f"{books} books" if books else "—","detail":"Sportsbook market research — not Hulk win probability",
            "action":"RESEARCH","sort":prob or 0,
        })
    return sorted(out, key=lambda x:x["sort"], reverse=True)


def rows_cfb():
    d = load("cfb")
    out = []
    for _, r in d.iterrows():
        start = first(r, ["start", "start_dt"], None)
        if not is_today(start):
            continue
        away, home = first(r, ["away", "Away"], ""), first(r, ["home", "Home"], "")
        conf = str(first(r, ["research_confidence"], "—")).upper()
        gap = num(first(r, ["model_vs_home_spread_edge"], None))
        books = int(num(first(r, ["Odds_books"], 0), 0) or 0)
        out.append({
            "sport":"CFB","start":start,"time":fmt_time(start),"away":away,"home":home,"pick":first(r,["research_lean"],"—"),
            "confidence":conf,"metric":f"{gap:+.1f}" if gap is not None else "—","metric_label":"RESEARCH GAP",
            "market":f"{books} books" if books else "No matched odds","detail":"Research-only; historical accuracy is straight-up, not ATS",
            "action":"RESEARCH","sort":3 if conf=="HIGH" else 2 if conf=="MEDIUM" else 1,
        })
    return sorted(out, key=lambda x:x["sort"], reverse=True)


def all_rows():
    rows = rows_mlb() + rows_nfl() + rows_cfb()
    priority = {"BET": 4, "WATCH": 3, "RESEARCH": 2, "PASS": 1}
    return sorted(rows, key=lambda r: (priority.get(r.get("action"), 0), r.get("sort", 0)), reverse=True)


def latest_slate_date(key, date_cols):
    d = load(key)
    dates = []
    for c in date_cols:
        if c in d.columns:
            x = pd.to_datetime(d[c], errors="coerce", utc=True).dropna()
            dates.extend([v.tz_convert(ET).date() for v in x])
    return max(dates).strftime("%b %-d") if dates else "none"


def mlb_record():
    d = load("mlb_results")
    if d.empty:
        return None
    rc = next((c for c in ["result", "graded_result", "pick_result"] if c in d.columns), None)
    if not rc:
        return None
    s = d[rc].astype(str).str.upper()
    w = int(s.str.contains("WIN|WON|CORRECT", regex=True).sum())
    l = int(s.str.contains("LOSS|LOST|INCORRECT", regex=True).sum())
    p = int(s.str.contains("PUSH", regex=True).sum())
    n = w + l
    uc = next((c for c in ["units", "unit_result", "profit_units"] if c in d.columns), None)
    units = float(pd.to_numeric(d[uc], errors="coerce").sum()) if uc else None
    return {"w":w,"l":l,"p":p,"wr":100*w/n if n else None,"units":units}


def render_kpis(mode, rows):
    today_n = len(rows)
    if mode == "⚾ MLB":
        d = load("mlb"); bets = sum(r["action"]=="BET" for r in rows); watches = sum(r["action"]=="WATCH" for r in rows)
        values = [("Today's Games",today_n,"actual ET date","green"),("Official BET",bets,"MLB model only","green"),("WATCH",watches,"discipline preserved","amber"),("Cached Games",len(d),"latest board","") ,("Latest Slate",latest_slate_date("mlb",["gameDate"]),"in cache","blue"),("Freshness",age("mlb"),"Oracle cache","")]
    elif mode == "🏈 NFL":
        d=load("nfl"); books=max([int(num(v,0) or 0) for v in d.get("sportsbooks",pd.Series(dtype=float))],default=0)
        values=[("Today's Games",today_n,"actual ET date","green"),("Hulk BET",0,"no validated NFL Hulk model",""),("Market Research",today_n,"today only","blue"),("Cached Games",len(d),"current week","") ,("Max Books",books,"market depth","blue"),("Freshness",age("nfl"),"Oracle cache","")]
    elif mode == "🏟️ College Football":
        d=load("cfb"); matched=int(pd.to_numeric(d.get("Odds_books",pd.Series(dtype=float)),errors="coerce").fillna(0).gt(0).sum())
        values=[("Today's Games",today_n,"actual ET date","green"),("Official ATS Bets",0,"not validated ATS",""),("Research Leans",today_n,"today only","blue"),("Cached Games",len(d),"current board","") ,("Odds Matched",matched,"cached board","blue"),("Freshness",age("cfb"),"Oracle cache","")]
    else:
        bets=sum(r["action"]=="BET" for r in rows)
        values=[("Today's Games",today_n,"all supported sports","green"),("Official Bets",bets,"MLB official only","green"),("NFL Research",sum(r["sport"]=="NFL" for r in rows),"market-backed","blue"),("CFB Research",sum(r["sport"]=="CFB" for r in rows),"research-only","blue"),("Sports",len(set(r["sport"] for r in rows)),"active today","") ,("Page API Cost",0,"cache only","")]
    cards="".join(f'<div class="kpi {cls}"><div class="lbl">{esc(lbl)}</div><div class="val">{esc(val)}</div><div class="note">{esc(note)}</div></div>' for lbl,val,note,cls in values)
    st.markdown(f'<div class="kpi-row">{cards}</div>', unsafe_allow_html=True)


def action_class(action):
    return {"BET":"bet","WATCH":"watch","RESEARCH":"research","PASS":"pass"}.get(action,"research")


def play_table(mode, rows):
    title = "🔥 TODAY'S TOP PLAYS" if mode == "🎯 Betting" else "TODAY'S BOARD"
    h=f'<div class="panel"><div class="phead"><div class="ptitle">{title}</div><div class="psub">ET date · sport isolated</div></div>'
    if not rows:
        h += '<div class="empty"><b>No games from this sport are in today\'s cached slate.</b><span>Sports Hulk will not substitute another sport or promote stale games. The rest of the dashboard remains available for status and research context.</span></div></div>'
        st.markdown(h, unsafe_allow_html=True); return
    h += '<div class="plays-head"><div>TIME</div><div>MATCHUP</div><div>PICK / LEAN</div><div>CONF</div><div>EDGE / LINE</div><div>MARKET</div><div>ACTION</div></div>'
    for r in rows[:7]:
        cls=action_class(r["action"])
        h += f'''<div class="play-row"><div class="dim">{esc(r['time'])}</div><div class="matchup-flex">{matchup_html(r['sport'],r['away'],r['home'])}</div><div><div class="pick">{esc(r['pick'])}</div><div class="dim">{esc(r['detail'])}</div></div><div><b>{esc(r['confidence'])}</b></div><div><b>{esc(r['metric'])}</b><div class="dim">{esc(r['metric_label'])}</div></div><div>{esc(r['market'])}</div><div><span class="badge {cls}">{esc(r['action'])}</span></div></div>'''
    st.markdown(h+'</div>', unsafe_allow_html=True)


def mlb_market_panel():
    d=load("mlb_market")
    if not d.empty and "game_start" in d.columns:
        d=d[d["game_start"].apply(is_today)].copy()
    st.markdown('<div class="panel accent-cyan"><div class="phead"><div class="ptitle">MARKET MOVEMENT</div><div class="psub">game-first · MLB today</div></div>',unsafe_allow_html=True)
    if d.empty:
        st.markdown('<div class="empty-rich"><b>No current MLB movement signal.</b><span>Nothing is substituted from another sport. Check feed freshness in Deep Research if today should have games.</span></div></div>',unsafe_allow_html=True)
        return
    score=pd.to_numeric(d.get("market_signal_score",pd.Series(index=d.index,dtype=float)),errors="coerce")
    d=d.assign(_score=score).sort_values("_score",ascending=False)
    cards=[]
    for _,r in d.head(8).iterrows():
        away=str(first(r,["away_team"],"")).title(); home=str(first(r,["home_team"],"")).title()
        metrics=[("Market",str(first(r,["core_market"],"—")).title()),("Target",str(first(r,["signal_target"],"—")).title()),("Books",f'{int(num(first(r,["books_moving"],0),0) or 0)}/{int(num(first(r,["books_reporting"],0),0) or 0)} moving'),("Strength",str(first(r,["signal_strength"],"—")).upper())]
        cards.append(matchup_card("MLB",away,home,first(r,["game_start"],None),metrics,badge="MARKET MOVE",accent="cyan",note=first(r,["market_signal"],"Market move detected")))
    st.markdown('<div class="clean-game-grid">'+''.join(cards)+'</div></div>',unsafe_allow_html=True)
    research_table(d,["away_team","home_team","game_start","core_market","signal_target","signal_strength","books_reporting","books_moving","consensus_among_movers_pct","whole_market_share_pct","avg_implied_prob_move","market_signal_score","market_signal"],"Deep Market Research",520,rename={"game_start":"Start","core_market":"Market","signal_target":"Target","signal_strength":"Strength","books_reporting":"Books Reporting","books_moving":"Books Moving","consensus_among_movers_pct":"Mover Agreement %","whole_market_share_pct":"Whole Market Share %","avg_implied_prob_move":"Avg Implied Move","market_signal_score":"Signal Score","market_signal":"Signal"})


def generic_market_panel(mode, rows):
    h='<div class="panel"><div class="phead"><div class="ptitle">MARKET / RESEARCH CONTEXT</div><div class="psub">today only</div></div>'
    if not rows:
        h+='<div class="empty"><b>No same-day market rows.</b><span>Upcoming cached games stay out of Today\'s Board.</span></div>'
    else:
        for r in rows[:6]:
            h+=f'<div class="info-row"><div><b>{esc(r["away"])} @ {esc(r["home"])}</b><br><span class="dim">{esc(r["detail"])}</span></div><div>{esc(r["market"])}</div><div class="blue">{esc(r["confidence"])}</div></div>'
    st.markdown(h+'</div>',unsafe_allow_html=True)


def results_panel(mode):
    if mode not in {"🎯 Betting","⚾ MLB"}:
        return '<div class="panel"><div class="phead"><div class="ptitle">RESULTS STATUS</div></div><div class="empty"><b>No official graded Hulk model record for this sport.</b><span>Sports Hulk will not reuse MLB results or fabricate a record.</span></div></div>'
    rec=mlb_record()
    if not rec:
        return '<div class="panel"><div class="phead"><div class="ptitle">RECENT RESULTS</div></div><div class="empty"><b>Awaiting graded MLB history.</b><span>No fabricated record.</span></div></div>'
    units='—' if rec['units'] is None else f"{rec['units']:+.2f}u"
    wr='—' if rec['wr'] is None else f"{rec['wr']:.1f}%"
    return f'<div class="panel"><div class="phead"><div class="ptitle">MLB GRADED RESULTS</div><div class="psub">official graded history only</div></div><div class="system-row"><span>Record</span><b>{rec["w"]}-{rec["l"]}-{rec["p"]}</b></div><div class="system-row"><span>Win rate</span><b class="good">{wr}</b></div><div class="system-row"><span>Units</span><b>{units}</b></div></div>'


def environment_panel(mode, rows):
    if mode == "⚾ MLB":
        d=load("mlb")
        if not d.empty and "gameDate" in d.columns: d=d[d["gameDate"].apply(is_today)]
        weather=int(d.get("temperature_f",pd.Series(index=d.index,dtype=float)).notna().sum()) if not d.empty else 0
        hitter=int(d.get("run_environment_flag",pd.Series(index=d.index,dtype=str)).astype(str).eq("HITTER_FRIENDLY").sum()) if not d.empty else 0
        return f'<div class="panel"><div class="phead"><div class="ptitle">WEATHER IMPACT</div></div><div class="system-row"><span>Games with weather</span><b>{weather}</b></div><div class="system-row"><span>Hitter-friendly flags</span><b class="warn">{hitter}</b></div><div class="system-row"><span>Source</span><b class="status-info">cached MLB board</b></div></div>'
    return f'<div class="panel"><div class="phead"><div class="ptitle">GAME ENVIRONMENT</div></div><div class="system-row"><span>Today\'s rows</span><b>{len(rows)}</b></div><div class="system-row"><span>Live page API calls</span><b class="status-ok">0</b></div><div class="system-row"><span>Data policy</span><b class="status-info">cache first</b></div></div>'


def systems_panel(mode):
    checks=[]
    if mode=="⚾ MLB": checks=[("MLB matchup model",P["mlb"].exists()),("MLB market signals",P["mlb_market"].exists()),("Graded history",P["mlb_results"].exists())]
    elif mode=="🏈 NFL": checks=[("NFL market board",P["nfl"].exists()),("Prop intelligence",(ROOT/"prop_intelligence/derived/HULK_PROP_SIGNALS.csv").exists()),("Survivor board",(ROOT/"nfl_live/derived/NFL_SURVIVOR_BOARD.csv").exists())]
    elif mode=="🏟️ College Football": checks=[("CFB research board",P["cfb"].exists()),("Odds context","Odds_books" in load("cfb").columns),("Player props disabled",True)]
    else: checks=[("MLB",P["mlb"].exists()),("NFL",P["nfl"].exists()),("CFB",P["cfb"].exists())]
    h='<div class="panel"><div class="phead"><div class="ptitle">SYSTEM STATUS</div><div class="psub">real availability</div></div>'
    for label,ok in checks:
        h+=f'<div class="system-row"><span>{esc(label)}</span><b class="{("status-ok" if ok else "bad")}">{("READY" if ok else "UNAVAILABLE")}</b></div>'
    return h+'</div>'


def parlay_panel(mode):
    d=load("qualified_parlays")
    sport={"⚾ MLB":"MLB","🏈 NFL":"NFL","🏟️ College Football":"CFB"}.get(mode)
    if not d.empty and sport and "sports" in d.columns:
        d=d[d["sports"].astype(str).str.contains(sport,case=False,na=False)]
    h='<div class="panel"><div class="phead"><div class="ptitle purple">BEST PARLAYS TODAY</div><div class="psub">qualified output only</div></div>'
    if d.empty:
        h+='<div class="empty"><b>No qualified parlay is available today.</b><span>Sports Hulk will not manufacture legs to fill this panel.</span></div>'
    else:
        for _,r in d.head(4).iterrows():
            label=first(r,["parlay_type","type"],"Qualified Parlay"); score=first(r,["parlay_score","score"],"—"); legs=first(r,["leg_summary","legs_text","selections"],"See research board")
            h+=f'<div class="info-row"><div><b>{esc(label)}</b><br><span class="dim">{esc(legs)}</span></div><div>{esc(score)}</div><div class="purple">QUALIFIED</div></div>'
    return h+'</div>'



def prop_preview_panel(sport):
    path = ROOT / "prop_intelligence/derived/HULK_PROP_SIGNALS.csv"
    try:
        d = pd.read_csv(path, low_memory=False) if path.exists() else pd.DataFrame()
    except Exception:
        d = pd.DataFrame()
    h = '<div class="panel"><div class="phead"><div class="ptitle green">PLAYER PROP INTELLIGENCE</div><div class="psub">selective preview</div></div>'
    if d.empty or "sport" not in d.columns:
        return h + '<div class="empty"><b>Prop cache unavailable.</b><span>No props are promoted without cached research.</span></div></div>'
    d = d[d["sport"].astype(str).str.upper().eq(sport)].copy()
    if "event_time" in d.columns:
        d = d[d["event_time"].apply(is_today)]
    if d.empty:
        return h + '<div class="empty"><b>No same-day prop rows.</b><span>Open Player Props for the full research board when the slate is populated.</span></div></div>'
    d["_score"] = pd.to_numeric(d.get("hulk_prop_score", pd.Series(index=d.index,dtype=float)), errors="coerce").fillna(0)
    d["_books"] = pd.to_numeric(d.get("book_count", pd.Series(index=d.index,dtype=float)), errors="coerce").fillna(0)
    sig = d.get("signal", pd.Series(index=d.index,dtype=str)).astype(str).str.upper()
    d = d[sig.isin(["STRONG","LEAN"]) & d["_books"].ge(3)].sort_values("_score", ascending=False).head(4)
    if d.empty:
        return h + '<div class="empty"><b>No qualified prop preview.</b><span>Sports Hulk will not fill the dashboard with weak props.</span></div></div>'
    for _,r in d.iterrows():
        h += f'<div class="info-row"><div><b>{esc(r.get("player","—"))}</b><br><span class="dim">{esc(str(r.get("canonical_market","—")).replace("_"," ").title())} · {esc(r.get("market_direction","—"))}</span></div><div>{esc(r.get("market_median","—"))}</div><div class="good">{esc(r.get("hulk_prop_score","—"))}</div></div>'
    return h + '</div>'


def cfb_totals_preview_panel():
    d=load("cfb")
    rows=[]
    for _,r in d.iterrows():
        if not is_today(first(r,["start","start_dt"],None)):
            continue
        total=num(r.get("Total")); proj=num(r.get("comp_projected_total"))
        if total is None or proj is None:
            continue
        edge=proj-total
        rows.append((abs(edge), first(r,["away"],"—"), first(r,["home"],"—"), total, proj, edge))
    rows=sorted(rows, reverse=True)[:4]
    h='<div class="panel"><div class="phead"><div class="ptitle amber">OVER / UNDER RESEARCH</div><div class="psub">historical comps</div></div>'
    if not rows:
        return h+'<div class="empty"><b>No same-day total research.</b><span>Totals appear only when both market and comparable-game projection exist.</span></div></div>'
    for _,away,home,total,proj,edge in rows:
        lean="OVER" if edge>=3 else "UNDER" if edge<=-3 else "PASS"
        h+=f'<div class="info-row"><div><b>{esc(away)} @ {esc(home)}</b><br><span class="dim">Market {total:.1f} · Projection {proj:.1f}</span></div><div>{lean}</div><div class="warn">{edge:+.1f}</div></div>'
    return h+'</div>'


def _set_mode_page(mode, page):
    slug = re.sub(r"[^a-z0-9]+", "_", mode.lower()).strip("_")
    st.session_state[f"hc_{slug}"] = page


def league_action_strip(mode):
    actions = {
        "⚾ MLB": [("🔥 Best Bets", "MLB Best Bets"), ("🎯 Player Props", "MLB Player Props"), ("🧩 Parlays", "MLB Parlays"), ("⚾ Matchups", "MLB Matchups"), ("🌦 Weather", "Weather")],
        "🏈 NFL": [("🔥 Best Bets", "NFL Best Bets"), ("🎯 Player Props", "NFL Player Props"), ("🧩 Parlays", "NFL Parlays"), ("🏈 Survivor", "Survivor"), ("🌦 Weather", "NFL Weather")],
        "🏟️ College Football": [("🔥 Best Bets", "CFB Best Bets"), ("↕ Over / Unders", "CFB Over / Unders"), ("🧩 Parlays", "CFB Parlays"), ("🏟️ Matchups", "CFB Matchups"), ("🔬 Research", "CFB Research")],
    }.get(mode, [])
    if not actions:
        return
    cols = st.columns(len(actions), gap="small")
    for col, (label, page) in zip(cols, actions):
        col.button(label, use_container_width=True, key=f"quick_{mode}_{page}", on_click=_set_mode_page, args=(mode, page))


def dashboard_shell(mode, rows):
    source_key={"⚾ MLB":"mlb","🏈 NFL":"nfl","🏟️ College Football":"cfb"}.get(mode)
    source=f"Cache updated {age(source_key)}" if source_key else "Oracle cache · 0 page API calls"
    topbar(mode,source)
    names={"🎯 Betting":("Betting Command Center","Only same-day supported-sport rows; official bets are MLB model only."),"⚾ MLB":("MLB Command Center","Official MLB model + same-day market and weather context."),"🏈 NFL":("NFL Command Center","Market-backed research only until a validated Hulk NFL model exists."),"🏟️ College Football":("College Football Command Center","Research leans only; historical straight-up accuracy is not ATS accuracy.")}
    name,sub=names.get(mode,("Sports Hulk","Sports intelligence"))
    st.markdown(f'<div class="sport-banner"><div><div class="sport-name">{name}</div><div class="sport-sub">{sub}</div></div><div class="source-pill">TODAY = {datetime.now(ET).strftime("%b %-d · ET")}</div></div>',unsafe_allow_html=True)
    league_action_strip(mode)
    render_kpis(mode,rows)
    c1,c2=st.columns([1.75,.85],gap="small")
    with c1: play_table(mode,rows)
    with c2:
        if mode=="⚾ MLB": mlb_market_panel()
        else: generic_market_panel(mode,rows)
        st.markdown(systems_panel(mode),unsafe_allow_html=True)
    b1,b2=st.columns([1,1],gap="small")
    with b1: st.markdown(results_panel(mode),unsafe_allow_html=True)
    with b2: st.markdown(environment_panel(mode,rows),unsafe_allow_html=True)
    st.markdown(parlay_panel(mode),unsafe_allow_html=True)
    if mode=="🏈 NFL":
        st.markdown(prop_preview_panel("NFL"),unsafe_allow_html=True)
    elif mode=="🏟️ College Football":
        st.markdown(cfb_totals_preview_panel(),unsafe_allow_html=True)


def pp_dashboard():
    topbar("🟣 PrizePicks",f"Cache updated {age('pp')}")
    pp=load("pp"); mk=load("parlay")
    if "odds_type" in pp.columns: pp=pp[pp["odds_type"].astype(str).str.lower().eq("standard")]
    if "is_promo" in pp.columns: pp=pp[~pp["is_promo"].astype(str).str.lower().isin(["true","1"])]
    player_col=next((c for c in ["player","player_name","name"] if c in pp.columns),None)
    players=int(pp[player_col].nunique()) if player_col and not pp.empty else 0
    cards=[("Standard Props",len(pp),"non-promo","purple"),("Players",players,"unique","") ,("Sportsbook Rows",len(mk),"cached compare","blue"),("Freshness",age("pp"),"Oracle cache","") ,("Promos","FILTERED","canonical board","green"),("Page API Cost",0,"cache only","")]
    st.markdown('<div class="kpi-row">'+''.join(f'<div class="kpi {c}"><div class="lbl">{esc(a)}</div><div class="val">{esc(b)}</div><div class="note">{esc(n)}</div></div>' for a,b,n,c in cards)+'</div>',unsafe_allow_html=True)
    st.markdown('<div class="panel"><div class="phead"><div class="ptitle purple">PRIZEPICKS INTELLIGENCE</div><div class="psub">separate from Fantasy</div></div><div class="empty"><b>Canonical Standard board loaded.</b><span>Use the NFL/MLB PrizePicks pages for detailed sport views. Promo rows remain filtered.</span></div></div>',unsafe_allow_html=True)


def fantasy_dashboard():
    topbar("🏆 Fantasy")
    d=load("fantasy"); d=d if not d.empty else load("fantasy2"); prof={"active":None,"leagues":{}}
    try:
        if P["profiles"].exists(): prof=json.loads(P["profiles"].read_text())
    except Exception: pass
    active=prof.get("active") or "No Active League"
    cards=[("Active League",active,"My Leagues","purple"),("Player Pool",len(d),"current","") ,("Waivers","READY","weekly","green"),("Lineup","READY","start/sit","blue"),("League Sync","NEXT","Sleeper → Yahoo → ESPN","") ,("Profiles",len(prof.get("leagues",{})),"saved leagues","")]
    st.markdown('<div class="kpi-row">'+''.join(f'<div class="kpi {c}"><div class="lbl">{esc(a)}</div><div class="val">{esc(b)}</div><div class="note">{esc(n)}</div></div>' for a,b,n,c in cards)+'</div>',unsafe_allow_html=True)


def dashboard(mode,page):
    if page not in {"Command Center","Dashboard","Today's Slate","Betting Dashboard","MLB Dashboard","NFL Dashboard","CFB Dashboard","PrizePicks Dashboard","Fantasy Dashboard"}: return
    css()
    if mode=="🎯 Betting": command_center()
    elif mode=="⚾ MLB": dashboard_shell(mode,rows_mlb())
    elif mode=="🏈 NFL": dashboard_shell(mode,rows_nfl())
    elif mode=="🏟️ College Football": cfb_command_center()
    elif mode=="🟣 PrizePicks": prizepicks_page()
    elif mode=="🏆 Fantasy": fantasy_command_center()
    else: dashboard_shell(mode,[])
    st.stop()


def render_parlays(sport=None):
    css(); mode={"MLB":"⚾ MLB","NFL":"🏈 NFL","CFB":"🏟️ College Football"}.get(sport,"🎯 Betting")
    topbar(mode,"Game + prop + mixed parlay research")
    st.markdown('<div class="command-hero"><div class="command-eyebrow">HULK PARLAY CENTER</div><div class="command-title">PARLAYS ARE <span>MORE THAN PROPS.</span></div><div class="command-sub">Game legs, qualified player props and mixed research are separated. Hulk does not lower thresholds or invent legs to fill a card.</div></div>',unsafe_allow_html=True)
    if sport is None:
        sport=st.selectbox("Sport",["MLB","NFL","CFB"],key="parlay_sport")
    games=_game_leg_pool(sport); props=_prop_leg_pool(sport)
    qualified=load("qualified_parlays")
    if not qualified.empty and "sports" in qualified.columns:
        qualified=qualified[qualified["sports"].astype(str).str.contains(sport,case=False,na=False)].copy()
    cards=[("Game Leg Pool",len(games),"today · non-PASS" if sport=="MLB" else "today · research eligible","blue"),("Qualified Prop Legs",len(props),"LEAN/STRONG · 3+ books","green"),("Qualified Prop Parlays",len(qualified),"engine output only","purple"),("Sport",sport,"isolated","gold")]
    st.markdown('<div class="league-stat-row">'+''.join(f'<div class="league-stat {c}"><div class="t">{esc(a)}</div><div class="n">{esc(b)}</div><div class="sport-sub">{esc(n)}</div></div>' for a,b,n,c in cards)+'</div>',unsafe_allow_html=True)

    st.subheader("Game Parlays")
    if len(games)>=2:
        builds=[(2,"2-LEG SAFER","blue"),(3,"3-LEG BALANCED","gold"),(4,"4-LEG AGGRESSIVE","red")]
        out=[]
        for n,label,accent in builds:
            if len(games)<n: continue
            legs=games[:n]
            source="Hulk Model Parlay" if sport=="MLB" and all(x.get("action")=="BET" for x in legs) else ("MLB Research Parlay" if sport=="MLB" else "Market-Backed Research Parlay")
            metrics=[("Legs",n),("Source",source),("Correlation","Different games preferred"),("Status","RESEARCH" if source!="Hulk Model Parlay" else "BET/WATCH")]
            leg_html=''.join(
                f'<div class="clean-metric"><span>LEG {i+1}</span><b>{esc(x.get("pick","—"))}</b><div class="sport-sub">{esc(x.get("event","—"))} · {esc(x.get("market","GAME"))} {esc(x.get("line",""))}</div></div>'
                for i,x in enumerate(legs)
            )
            out.append(f'<div class="clean-game-card {accent}"><div class="clean-game-top"><div><div class="clean-matchup">{label}</div><div class="clean-time">{esc(source)}</div></div><span class="clean-badge {accent}">PARLAY</span></div><div class="clean-metrics">'+leg_html+'</div><div class="clean-note">Every leg is shown above. Different games are preferred unless a validated correlation rule supports otherwise.</div></div>')
        st.markdown('<div class="clean-game-grid">'+''.join(out)+'</div>',unsafe_allow_html=True)
    else:
        st.info(f"Only {len(games)} eligible {sport} game leg(s) are available today. Two are required before Hulk can form a game parlay.")

    st.subheader("Player-Prop Parlays")
    if not qualified.empty:
        qcards=[]
        for _,r in qualified.head(6).iterrows():
            qcards.append(player_card(first(r,["parlay_type","type"],"Qualified Prop Parlay"),sport,metrics=[("Score",first(r,["parlay_score","score"],"—")),("Legs",first(r,["leg_count","legs"],"—"))],badge="QUALIFIED",accent="purple",note=first(r,["leg_summary","legs_text","selections"],"Qualified engine output")))
        st.markdown('<div class="clean-player-grid">'+''.join(qcards)+'</div>',unsafe_allow_html=True)
    else:
        st.info("No qualified player-prop parlays for today. This does not block game parlays above.")

    st.subheader("Mixed Game + Prop Parlays")
    if games and props:
        mixed=[]
        # Basic correlation guardrail: do not use duplicate event IDs when prop event identity is available.
        for g in games:
            mixed.append(g)
            if len(mixed)>=2: break
        for pr in props:
            mixed.append(pr)
            if len(mixed)>=3: break
        note=' · '.join(f'{x.get("pick")} [{x.get("market")}]' for x in mixed)
        st.markdown('<div class="clean-game-card purple"><div class="clean-game-top"><div><div class="clean-matchup">MIXED RESEARCH BUILD</div><div class="clean-time">game + qualified prop inputs</div></div><span class="clean-badge purple">RESEARCH</span></div><div class="clean-note">'+esc(note)+'</div></div>',unsafe_allow_html=True)
        st.caption("Mixed builds are research combinations. Advanced same-game correlation modeling is not claimed until that engine exists.")
    else:
        st.info("Mixed parlays need at least one eligible game leg and one qualified prop leg on today’s slate.")

    if not qualified.empty:
        research_table(qualified,None,"Deep Qualified Parlay Data",420)


def profiles():
    try: return json.loads(P["profiles"].read_text()) if P["profiles"].exists() else {"active":None,"leagues":{}}
    except Exception: return {"active":None,"leagues":{}}


def save_profiles(data):
    P["profiles"].parent.mkdir(parents=True,exist_ok=True); P["profiles"].write_text(json.dumps(data,indent=2))


def active_league_context():
    data = profiles()
    leagues = data.get("leagues", {}) if isinstance(data, dict) else {}
    names = list(leagues)
    active = data.get("active") if isinstance(data, dict) else None
    if active not in leagues:
        active = names[0] if names else None
    league = leagues.get(active, {}) if active else {}
    return data, leagues, active, league if isinstance(league, dict) else {}


def _split_names(value):
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if value is None:
        return []
    return [x.strip() for x in re.split(r"[\n,;]+", str(value)) if x.strip()]


def _norm_name(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def fantasy_command_center():
    css(); topbar("🏆 Fantasy", "League-aware fantasy command center")
    d = fdf()
    data, leagues, active, league = active_league_context()
    platform = league.get("platform", "Manual / Not synced") if active else "—"
    synced = bool(league.get("synced")) if active else False
    roster = _split_names(league.get("roster", []))
    free_agents = _split_names(league.get("free_agents", []))
    st.markdown(
        '<div class="command-hero"><div class="command-eyebrow">FANTASY HULK COMMAND CENTER</div>'
        '<div class="command-title">YOUR LEAGUE. <span>YOUR PLAYERS.</span></div>'
        '<div class="command-sub">Rankings, Top 300, waivers, lineup decisions and trade research become league-aware as roster and free-agent data are synced.</div></div>',
        unsafe_allow_html=True,
    )
    cards = [
        ("Active League", active or "NONE", platform, "purple"),
        ("League Sync", "CONNECTED" if synced else "NOT CONNECTED", "Sleeper / Yahoo / ESPN / Manual", "green" if synced else "amber"),
        ("Roster", len(roster), "players known to Hulk", "blue"),
        ("Free Agents", len(free_agents), "league-specific availability", "green"),
        ("Top 300", min(len(d), 300) if not d.empty else 0, "draft cheat sheet", "purple"),
        ("Saved Leagues", len(leagues), "multi-league profiles", ""),
    ]
    st.markdown('<div class="kpi-row">'+''.join(
        f'<div class="kpi {c}"><div class="lbl">{esc(a)}</div><div class="val">{esc(b)}</div><div class="note">{esc(n)}</div></div>'
        for a,b,n,c in cards
    )+'</div>', unsafe_allow_html=True)
    c1,c2 = st.columns([1.35, .9], gap="small")
    with c1:
        st.markdown('<div class="panel"><div class="phead"><div class="ptitle green">TODAY\'S FANTASY ACTIONS</div><div class="psub">active-league aware</div></div>', unsafe_allow_html=True)
        if not active:
            st.info("Add a league in My Leagues to turn on personalized roster, waiver and lineup views.")
        elif not synced and not roster and not free_agents:
            st.info("League profile is ready. Connect the provider later or add roster/free-agent data manually in My Leagues; Hulk will never pretend an unsynced league is connected.")
        else:
            if roster:
                st.success(f"Roster loaded: {len(roster)} players. Lineup can use this roster automatically.")
            if free_agents:
                st.success(f"Free-agent pool loaded: {len(free_agents)} players. Waiver Wire will rank only players available in {active}.")
            if not free_agents:
                st.warning("No league-specific free-agent pool is loaded yet, so waiver recommendations remain generic.")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(
            '<div class="panel"><div class="phead"><div class="ptitle purple">SYNC ROADMAP</div><div class="psub">safe provider architecture</div></div>'
            '<div class="info-row"><div><b>Sleeper</b><br><span class="dim">direct public/API league path</span></div><div class="good">FIRST</div></div>'
            '<div class="info-row"><div><b>Yahoo</b><br><span class="dim">OAuth authorization</span></div><div>OAUTH</div></div>'
            '<div class="info-row"><div><b>ESPN</b><br><span class="dim">browser-extension assisted private league sync</span></div><div>EXTENSION</div></div>'
            '<div class="info-row"><div><b>Manual</b><br><span class="dim">always available fallback</span></div><div>READY</div></div></div>',
            unsafe_allow_html=True,
        )


def leagues_page():
    css(); topbar("🏆 Fantasy", "Multi-league profiles")
    data=profiles(); leagues=data.get("leagues",{})
    if leagues:
        names=list(leagues); active=data.get("active") if data.get("active") in names else names[0]
        pick=st.selectbox("Active League",names,index=names.index(active))
        if pick!=data.get("active"):
            data["active"]=pick; save_profiles(data); st.rerun()
        league=leagues[pick]
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Platform", league.get("platform","Manual"))
        c2.metric("Teams", league.get("teams","—"))
        c3.metric("Scoring", league.get("scoring","—"))
        c4.metric("Sync", "Connected" if league.get("synced") else "Not connected")
        st.caption("Provider credentials are never entered on this page. Yahoo will use OAuth; ESPN sync is designed for a browser-extension bridge; Sleeper can use league/API identifiers.")
        with st.expander("League roster & availability", expanded=True):
            roster_text=st.text_area("Roster players", value="\n".join(_split_names(league.get("roster",[]))), height=150, help="One player per line. This is the manual fallback until provider sync populates the roster automatically.")
            fa_text=st.text_area("Available free agents", value="\n".join(_split_names(league.get("free_agents",[]))), height=150, help="One player per line. When a provider is synced, this list should be refreshed by the connector rather than typed manually.")
            c1,c2=st.columns(2)
            with c1:
                league_id=st.text_input("League ID / reference", value=str(league.get("league_id","")), help="Non-secret league identifier only. Do not paste passwords, cookies or tokens.")
            with c2:
                faab=st.number_input("FAAB budget", min_value=0, max_value=10000, value=int(league.get("faab_budget",100) or 100), step=1)
            if st.button("Save League Data", type="primary"):
                league["roster"]=_split_names(roster_text)
                league["free_agents"]=_split_names(fa_text)
                league["league_id"]=league_id.strip()
                league["faab_budget"]=int(faab)
                leagues[pick]=league; data["leagues"]=leagues; save_profiles(data); st.rerun()
    with st.expander("➕ Add League",expanded=not bool(leagues)):
        name=st.text_input("League name"); c1,c2,c3=st.columns(3)
        with c1: teams=st.selectbox("Teams",[8,10,12,14,16],index=2)
        with c2: scoring=st.selectbox("Scoring",["PPR","Half-PPR","Standard"])
        with c3: qb=st.selectbox("QB format",["1QB","Superflex","2QB"])
        platform=st.selectbox("Platform",["Manual / Not synced","Sleeper","Yahoo","ESPN"])
        if st.button("Save League",type="primary",disabled=not bool(name.strip())):
            leagues[name.strip()]={"teams":teams,"scoring":scoring,"qb_format":qb,"platform":platform,"synced":False,"roster":[],"free_agents":[],"league_id":"","faab_budget":100}
            data["leagues"]=leagues; data["active"]=name.strip(); save_profiles(data); st.rerun()


def fdf():
    d=load("fantasy"); return d if not d.empty else load("fantasy2")


def _fantasy_ranked_board():
    d=fdf().copy()
    if d.empty:
        return d, None, None
    rank=next((c for c in ["hulk_v2_rank","overall_rank","hulk_rank","rank"] if c in d.columns),None)
    name=next((c for c in ["full_name","player","name"] if c in d.columns),None)
    if rank:
        d[rank]=pd.to_numeric(d[rank],errors="coerce"); d=d.sort_values(rank)
    return d, rank, name


def waivers_page():
    css(); topbar("🏆 Fantasy", "League-aware waiver board")
    d,rank,name=_fantasy_ranked_board()
    if d.empty or not name: st.error("Fantasy board unavailable."); return
    data,leagues,active,league=active_league_context(); free_agents=_split_names(league.get("free_agents",[])) if active else []; roster=_split_names(league.get("roster",[])) if active else []
    if active: st.markdown(f'<div class="sport-banner"><div><div class="sport-name">Waiver Wire · {esc(active)}</div><div class="sport-sub">League-available players first.</div></div><div class="source-pill">{esc(league.get("platform","MANUAL"))}</div></div>',unsafe_allow_html=True)
    else: st.warning("No active league. Showing the generic fantasy board until a league is added.")
    if free_agents: keys={_norm_name(x) for x in free_agents}; d=d[d[name].map(_norm_name).isin(keys)].copy()
    elif roster: roster_keys={_norm_name(x) for x in roster}; d=d[~d[name].map(_norm_name).isin(roster_keys)].copy(); st.info("Roster is known, but the provider free-agent pool is not. Hulk removed your rostered players only.")
    if d.empty: st.info("No available players matched the current Hulk fantasy board."); return
    d=d.copy(); d["Waiver Call"]=["ADD" if i<10 else "WATCH" if i<30 else "DEEP STASH" for i in range(len(d))]; proj=next((c for c in ["proj_ppr_points","projected_points","projection"] if c in d.columns),None)
    cards=[]
    for _,r in d.head(60).iterrows(): cards.append(player_card(r.get(name,"—"),r.get("team","—"),r.get("position",""),[("Rank",r.get(rank,"—") if rank else "—"),("Projection",r.get(proj,"—") if proj else "—"),("ADP",r.get("consensus_adp","—")),("Tier",r.get("hulk_v2_tier",r.get("tier","—")))],badge=r.get("Waiver Call","WATCH"),accent="green" if r.get("Waiver Call")=="ADD" else "gold"))
    st.markdown('<div class="clean-player-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    research_table(d,None,"Full Waiver Research Data",560)


def lineup_page():
    css(); topbar("🏆 Fantasy", "League-aware lineup board")
    d,rank,name=_fantasy_ranked_board()
    if d.empty or not name: st.error("Fantasy board unavailable."); return
    _,_,active,league=active_league_context(); saved_roster=_split_names(league.get("roster",[])) if active else []; options=d[name].dropna().astype(str).drop_duplicates().tolist(); matched=[]
    if saved_roster:
        lookup={_norm_name(x):x for x in options}; matched=[lookup[k] for k in [_norm_name(x) for x in saved_roster] if k in lookup]
    roster=st.multiselect("Roster",options,default=matched,key=f"hulk_lineup_{active or 'manual'}")
    if not roster: st.info("Add players above or save a roster in My Leagues to build a Start/Bench board."); return
    x=d[d[name].astype(str).isin(roster)].copy(); score=next((c for c in ["proj_ppr_points","projected_points","projection","hulk_v2_score","hulk_score"] if c in x.columns),None)
    if score: x[score]=pd.to_numeric(x[score],errors="coerce"); x=x.sort_values(score,ascending=False)
    elif rank: x[rank]=pd.to_numeric(x[rank],errors="coerce"); x=x.sort_values(rank)
    x["Hulk Lineup Call"]=["START" if i<min(7,len(x)) else "BENCH" for i in range(len(x))]
    cards=[player_card(r.get(name,"—"),r.get("team","—"),r.get("position",""),[("Projection",r.get(score,"—") if score else "—"),("Rank",r.get(rank,"—") if rank else "—"),("Tier",r.get("hulk_v2_tier",r.get("tier","—")))],badge=r.get("Hulk Lineup Call"),accent="green" if r.get("Hulk Lineup Call")=="START" else "blue") for _,r in x.iterrows()]
    st.markdown('<div class="clean-player-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True); research_table(x,None,"Full Lineup Research Data",500)
    st.caption("Start/Bench is currently a roster ordering aid, not a full slot optimizer yet.")


def trade_finder_page():
    css(); topbar("🏆 Fantasy", "Trade research")
    d,rank,name=_fantasy_ranked_board()
    if d.empty or not name: st.error("Fantasy board unavailable."); return
    _,_,active,league=active_league_context(); roster=_split_names(league.get("roster",[])) if active else []
    st.markdown('<div class="sport-banner"><div><div class="sport-name">Hulk Trade Finder</div><div class="sport-sub">Roster-aware trade assets, not isolated spreadsheet grades.</div></div><div class="source-pill">FOUNDATION</div></div>',unsafe_allow_html=True)
    if not active: st.info("Add and select a league first."); return
    if not roster: st.info("Save this league's roster in My Leagues."); return
    lookup={_norm_name(v):v for v in d[name].astype(str)}; mine=[lookup[k] for k in [_norm_name(x) for x in roster] if k in lookup]; x=d[d[name].astype(str).isin(mine)].copy(); cards=[]
    for _,r in x.iterrows(): cards.append(player_card(r.get(name,"—"),r.get("team","—"),r.get("position",""),[("Rank",r.get(rank,"—") if rank else "—"),("Tier",r.get("hulk_v2_tier","—")),("ADP",r.get("consensus_adp","—")),("Projection",r.get("proj_ppr_points","—")),("VORP",r.get("vorp","—"))],badge="YOUR ASSET",accent="purple"))
    st.markdown('<div class="clean-player-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True); research_table(x,None,"Full Trade Asset Data",480)
    st.info("Opponent-roster sync is required before Hulk proposes trades. It will not invent targets.")


def historical_explorer_page():
    css(); topbar("🎯 Betting", "Historical vault explorer")
    st.markdown('<div class="command-hero"><div class="command-eyebrow">HULK HISTORICAL INTELLIGENCE</div><div class="command-title">FILTER FIRST. <span>READ GAMES, NOT ROWS.</span></div><div class="command-sub">Use the vault filters, then review recent matching games as cards. Full raw history remains collapsed underneath.</div></div>',unsafe_allow_html=True)
    sport=st.selectbox("Sport",["NFL","MLB","CFB"],key="hist_sport"); d=load({"NFL":"nfl_history","MLB":"mlb_history","CFB":"cfb_history"}[sport])
    if d.empty: st.info(f"{sport} historical vault is unavailable."); return
    home="home_team" if "home_team" in d.columns else None; away="away_team" if "away_team" in d.columns else None; teams=sorted(set(d[home].dropna().astype(str)).union(set(d[away].dropna().astype(str)))) if home and away else []
    c1,c2,c3=st.columns([1.2,1.2,.8])
    with c1: team=st.selectbox("Team",["ALL"]+teams)
    with c2: opponent=st.selectbox("Opponent",["ALL"]+teams)
    with c3: venue_side=st.selectbox("Team location",["ANY","HOME","AWAY"])
    x=d.copy()
    if team!="ALL" and home and away:
        if venue_side=="HOME": x=x[x[home].astype(str).eq(team)]
        elif venue_side=="AWAY": x=x[x[away].astype(str).eq(team)]
        else: x=x[x[home].astype(str).eq(team)|x[away].astype(str).eq(team)]
    if opponent!="ALL" and home and away:
        if team!="ALL": x=x[((x[home].astype(str).eq(team))&x[away].astype(str).eq(opponent))|((x[away].astype(str).eq(team))&x[home].astype(str).eq(opponent))]
        else: x=x[x[home].astype(str).eq(opponent)|x[away].astype(str).eq(opponent)]
    if sport=="NFL":
        f1,f2,f3=st.columns(3)
        if "roof" in x.columns:
            vals=["ALL"]+sorted(x["roof"].dropna().astype(str).unique().tolist()); roof=f1.selectbox("Roof",vals); x=x if roof=="ALL" else x[x["roof"].astype(str).eq(roof)]
        if "surface" in x.columns:
            vals=["ALL"]+sorted(x["surface"].dropna().astype(str).unique().tolist()); surface=f2.selectbox("Surface",vals); x=x if surface=="ALL" else x[x["surface"].astype(str).eq(surface)]
        if "wind" in x.columns:
            maxwind=f3.slider("Max wind",0,50,50); w=pd.to_numeric(x["wind"],errors="coerce"); x=x[w.isna()|w.le(maxwind)]
    st.markdown(f'<div class="research-summary"><div><span>Matching Games</span><b>{len(x):,}</b></div><div><span>Sport</span><b>{esc(sport)}</b></div><div><span>Team</span><b>{esc(team)}</b></div><div><span>Opponent</span><b>{esc(opponent)}</b></div></div>',unsafe_allow_html=True)
    if x.empty: st.info("No historical games match those filters."); return
    date_col=next((c for c in ["gameday","officialDate","game_date"] if c in x.columns),None)
    if date_col: x=x.sort_values(date_col,ascending=False)
    cards=[]
    for _,r in x.head(16).iterrows():
        a=first(r,[away],"—") if away else "—"; h=first(r,[home],"—") if home else "—"
        if sport=="NFL": metrics=[("Score",f'{first(r,["away_score"],"—")}–{first(r,["home_score"],"—")}'),("Spread",first(r,["spread_line"],"—")),("Total",first(r,["total_line"],"—")),("Weather",f'{first(r,["temp"],"—")}° · {first(r,["wind"],"—")} mph')]; note=first(r,["stadium"],"")
        elif sport=="MLB": metrics=[("Score",f'{first(r,["away_score"],"—")}–{first(r,["home_score"],"—")}'),("Runs",first(r,["total_runs"],"—")),("Venue",first(r,["venue"],"—"))]; note=""
        else: metrics=[("Score",f'{first(r,["away_points"],"—")}–{first(r,["home_points"],"—")}'),("Margin",first(r,["home_margin"],"—")),("Total",first(r,["total_points"],"—")),("Conference",first(r,["conference_game"],"—"))]; note=""
        cards.append(matchup_card(sport,a,h,first(r,[date_col],None) if date_col else None,metrics,badge="HISTORY",accent="blue",note=note))
    st.markdown('<div class="clean-game-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    research_table(x,None,"Full Historical Research Data",620)


def count_rows(path):
    try:
        if not path.exists():
            return 0
        return max(sum(1 for _ in path.open("r", errors="ignore")) - 1, 0)
    except Exception:
        return 0


def _load_json(path, default):
    try:
        return json.loads(path.read_text()) if path.exists() else default
    except Exception:
        return default


def _save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def prop_action_counts():
    path = ROOT / "prop_intelligence/derived/HULK_PROP_SIGNALS.csv"
    try:
        d = pd.read_csv(path, low_memory=False) if path.exists() else pd.DataFrame()
    except Exception:
        d = pd.DataFrame()
    if d.empty:
        return 0, 0, []
    if "event_time" in d.columns:
        d = d[d["event_time"].apply(is_today)].copy()
    if d.empty:
        return 0, 0, []
    d["_score"] = pd.to_numeric(d.get("hulk_prop_score", pd.Series(index=d.index, dtype=float)), errors="coerce").fillna(0)
    d["_books"] = pd.to_numeric(d.get("book_count", pd.Series(index=d.index, dtype=float)), errors="coerce").fillna(0)
    sig = d.get("signal", pd.Series(index=d.index, dtype=str)).astype(str).str.upper()
    edge = d[sig.eq("STRONG") & d["_books"].ge(5) & d["_score"].ge(80)].copy()
    lean = d[sig.isin(["STRONG", "LEAN"]) & d["_books"].ge(5) & d["_score"].ge(72)].copy()
    top = edge.sort_values("_score", ascending=False).head(4).to_dict("records") if not edge.empty else []
    return len(edge), len(lean), top


def fantasy_profile_counts():
    d = profiles()
    leagues = d.get("leagues", {})
    synced = sum(bool(v.get("synced")) for v in leagues.values() if isinstance(v, dict))
    return len(leagues), synced, d.get("active")


def survivor_data():
    return _load_json(P["survivor_entries"], {"active": None, "entries": {}})



def prizepicks_preview_panel(sport):
    d=load("pp")
    if d.empty:
        return '<div class="panel accent-purple"><div class="phead"><div class="ptitle purple">PRIZEPICKS</div></div><div class="empty-rich"><b>PrizePicks cache unavailable.</b><span>No lines shown until the cached Standard feed is available.</span></div></div>'
    if "odds_type" in d.columns:
        d=d[d["odds_type"].astype(str).str.lower().eq("standard")]
    if "is_promo" in d.columns:
        d=d[~d["is_promo"].astype(str).str.lower().isin(["true","1"])]
    if "league" in d.columns:
        d=d[d["league"].astype(str).str.upper().eq(sport)]
    if "start_time" in d.columns:
        dt=pd.to_datetime(d["start_time"],errors="coerce",utc=True)
        d=d[dt.isna()|(dt>=pd.Timestamp.now(tz="UTC")-pd.Timedelta(hours=1))]
    h=f'<div class="panel accent-purple"><div class="phead"><div class="ptitle purple">🟣 {esc(sport)} PRIZEPICKS</div><div class="psub">{len(d):,} standard lines</div></div>'
    if d.empty:
        return h+'<div class="empty-rich"><b>No upcoming standard lines.</b><span>The page stays empty rather than showing stale or promo rows.</span></div></div>'
    for _,r in d.head(5).iterrows():
        h+=f'<div class="market-card"><div><div class="market-match">{esc(r.get("player","—"))}</div><div class="market-signal">{esc(r.get("stat","—"))} · {esc(r.get("team","—"))}</div></div><div class="market-meta"><div class="market-books">LINE</div><div class="market-strength" style="color:#c47cff">{esc(r.get("line","—"))}</div></div></div>'
    return h+'</div>'


def mlb_best_bets_page():
    css(); topbar("⚾ MLB","Official model + props + PrizePicks + market")
    rows=rows_mlb(); bets=[r for r in rows if r.get("action")=="BET"]
    pp=load("pp")
    if not pp.empty and "league" in pp.columns: pp=pp[pp["league"].astype(str).str.upper().eq("MLB")]
    prop_edges, prop_leans, _=prop_action_counts()
    st.markdown('<div class="league-hero mlb"><div class="league-eyebrow">MLB INTELLIGENCE</div><div class="league-title">BASEBALL <span class="blue">WITHOUT THE CLUTTER.</span></div><div class="league-copy">Official Hulk bets stay disciplined. Games are shown first with team logos; props, PrizePicks, market, weather and parlays sit underneath.</div></div><div class="spectrum-strip"></div>',unsafe_allow_html=True)
    stats=[("Official Bets",len(bets),"blue"),("Today’s Games",len(rows),""),("MLB PrizePicks",len(pp),"purple"),("Qualified Prop Edges",prop_edges,"gold")]
    st.markdown('<div class="league-stat-row">'+''.join(f'<div class="league-stat {c}"><div class="t">{esc(a)}</div><div class="n">{esc(b)}</div></div>' for a,b,c in stats)+'</div>',unsafe_allow_html=True)
    if rows:
        cards=[]
        for r in rows:
            accent="green" if r.get("action")=="BET" else "gold" if r.get("action")=="WATCH" else "blue"
            metrics=[("Hulk Pick",r.get("pick","—")),("Decision",r.get("action","—")),("Confidence",r.get("confidence","—")),("Model Edge",r.get("metric","—")),("Market",r.get("market","—"))]
            cards.append(matchup_card("MLB",r.get("away"),r.get("home"),r.get("start"),metrics,badge=r.get("action"),accent=accent,note=r.get("detail")))
        st.markdown('<div class="panel"><div class="phead"><div class="ptitle">🔥 TODAY’S MLB BOARD</div><div class="psub">game first · official decision visible</div></div><div class="clean-game-grid">'+''.join(cards)+'</div></div>',unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-rich"><b>No same-day MLB games in cache.</b><span>Sports Hulk will not show stale games as today.</span></div>',unsafe_allow_html=True)
    c1,c2=st.columns(2,gap="small")
    with c1: st.markdown(prop_preview_panel("MLB"),unsafe_allow_html=True)
    with c2: st.markdown(prizepicks_preview_panel("MLB"),unsafe_allow_html=True)
    c3,c4=st.columns(2,gap="small")
    with c3: mlb_market_panel()
    with c4: st.markdown(environment_panel("⚾ MLB",rows),unsafe_allow_html=True)
    st.markdown(parlay_panel("⚾ MLB"),unsafe_allow_html=True)


def cfb_command_center():
    css(); topbar("🏟️ College Football","Best bets + totals + parlays + research")
    rows=rows_cfb(); d=load("cfb")
    high=sum(str(r.get("confidence","")).upper()=="HIGH" for r in rows)
    matched=int(pd.to_numeric(d.get("Odds_books",pd.Series(dtype=float)),errors="coerce").fillna(0).gt(0).sum()) if not d.empty else 0
    st.markdown('<div class="league-hero cfb"><div class="league-eyebrow">COLLEGE FOOTBALL INTELLIGENCE</div><div class="league-title">SATURDAY BOARD. <span class="gold">FAST TO READ.</span></div><div class="league-copy">Best research leans, spreads, moneylines, totals and parlays — no college player props, no fake ATS model confidence.</div></div><div class="spectrum-strip"></div>',unsafe_allow_html=True)
    stats=[("Today’s Games",len(rows),"gold"),("High Research",high,"purple"),("Odds Matched",matched,"blue"),("Official ATS Bets",0,"red")]
    st.markdown('<div class="league-stat-row">'+''.join(f'<div class="league-stat {c}"><div class="t">{esc(a)}</div><div class="n">{esc(b)}</div></div>' for a,b,c in stats)+'</div>',unsafe_allow_html=True)
    if rows:
        h='<div class="panel accent-gold"><div class="phead"><div class="ptitle">🔥 TODAY’S BEST CFB RESEARCH</div><div class="psub">team/game research only</div></div>'
        for r in rows[:6]:
            h+=f'<div class="pick-card cfb"><div class="pick-top"><div><div class="pick-match">{esc(r["away"])} @ {esc(r["home"])}</div><div class="pick-time">{esc(r["time"])} ET</div></div><span class="badge research">RESEARCH</span></div><div class="pick-grid"><div class="pick-metric"><div class="l">LEAN</div><div class="v">{esc(r["pick"])}</div></div><div class="pick-metric"><div class="l">CONFIDENCE</div><div class="v">{esc(r["confidence"])}</div></div><div class="pick-metric"><div class="l">RESEARCH GAP</div><div class="v">{esc(r["metric"])}</div></div><div class="pick-metric"><div class="l">MARKET</div><div class="v">{esc(r["market"])}</div></div></div></div>'
        st.markdown(h+'</div>',unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-rich"><b>No same-day CFB games in cache.</b><span>Upcoming rows stay out of Today’s Board.</span></div>',unsafe_allow_html=True)
    c1,c2=st.columns(2,gap="small")
    with c1: st.markdown(cfb_totals_preview_panel(),unsafe_allow_html=True)
    with c2: st.markdown(parlay_panel("🏟️ College Football"),unsafe_allow_html=True)
    st.markdown(generic_market_panel("🏟️ College Football",rows),unsafe_allow_html=True)


def cfb_best_bets_page():
    css(); topbar("🏟️ College Football","Research leans · spreads · totals")
    rows=rows_cfb()
    st.markdown('<div class="league-hero cfb"><div class="league-eyebrow">CFB BEST BETS</div><div class="league-title">BEST RESEARCH. <span class="gold">NO FAKE ATS MODEL.</span></div><div class="league-copy">High-confidence research is clearly separated from official model bets. Totals are featured alongside sides.</div></div>',unsafe_allow_html=True)
    if not rows:
        st.markdown('<div class="empty-rich"><b>No CFB research rows today.</b><span>Sports Hulk will not fill the page with stale games.</span></div>',unsafe_allow_html=True)
        return
    play_table("🏟️ College Football",rows)
    st.markdown(cfb_totals_preview_panel(),unsafe_allow_html=True)

def command_center():
    css()
    topbar("🎯 Betting", "Oracle cache · one-shop intelligence")
    rows = all_rows()
    mlb_bets = sum(r.get("sport") == "MLB" and r.get("action") == "BET" for r in rows)
    prop_edges, prop_leans, top_props = prop_action_counts()
    pp = load("pp")
    if "odds_type" in pp.columns:
        pp = pp[pp["odds_type"].astype(str).str.lower().eq("standard")]
    if "is_promo" in pp.columns:
        pp = pp[~pp["is_promo"].astype(str).str.lower().isin(["true", "1"])]
    if not pp.empty and "league" in pp.columns:
        pp = pp[pp["league"].astype(str).str.upper().isin(["NFL", "MLB"])]
    leagues, synced, active = fantasy_profile_counts()
    surv = survivor_data()
    survivor_entries = len(surv.get("entries", {}))
    tracker = _tracker_summary()

    st.markdown(r'''<style>
    .mock-hero{position:relative;overflow:hidden;border:1px solid #234765;border-radius:16px;padding:22px 28px 20px;background:radial-gradient(circle at 7% 35%,rgba(53,255,48,.42),transparent 23%),radial-gradient(circle at 78% 15%,rgba(127,50,255,.31),transparent 27%),radial-gradient(circle at 96% 48%,rgba(37,128,255,.24),transparent 24%),linear-gradient(105deg,#07160b 0%,#08131b 46%,#0b0b1e 100%);box-shadow:0 18px 52px rgba(0,0,0,.42)}
    .mock-hero:before{content:"";position:absolute;inset:0;background:linear-gradient(115deg,transparent 0 60%,rgba(64,111,255,.18) 61%,transparent 63%),linear-gradient(103deg,transparent 0 70%,rgba(186,75,255,.18) 71%,transparent 73%);pointer-events:none}
    .mock-eyebrow{position:relative;color:#a6ff7b;font-size:13px;font-weight:1000;letter-spacing:.18em}.mock-title{position:relative;color:#fff;font-size:44px;font-weight:1000;letter-spacing:-.025em;line-height:1.02;margin:5px 0 7px}.mock-title span{color:#63ff37}.mock-copy{position:relative;color:#d5e0e6;font-size:16px;max-width:900px;line-height:1.45}
    .mock-kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;margin:12px 0}.mock-kpi{position:relative;overflow:hidden;border-radius:13px;padding:14px;background:linear-gradient(180deg,#0d1720,#081018);border:1px solid #1d3140;min-height:96px}.mock-kpi:before{content:"";position:absolute;left:0;right:0;top:0;height:3px;background:var(--accent)}.mock-kpi .klabel{font-size:11px;font-weight:950;letter-spacing:.07em;color:#9eb0bc}.mock-kpi .knum{font-size:31px;font-weight:1000;color:#fff;margin:4px 0 1px}.mock-kpi .knote{font-size:12px;color:#94a6b3}.mock-kpi.green{--accent:#65ff34}.mock-kpi.blue{--accent:#3e9cff}.mock-kpi.purple{--accent:#b95eff}.mock-kpi.gold{--accent:#ffb62b}.mock-kpi.red{--accent:#ff525b}.mock-kpi.cyan{--accent:#26d7ff}.mock-kpi.green .knum{color:#68ff3a}.mock-kpi.blue .knum{color:#62b4ff}.mock-kpi.purple .knum{color:#c27cff}.mock-kpi.gold .knum{color:#ffc454}.mock-kpi.red .knum{color:#ff757b}.mock-kpi.cyan .knum{color:#52e5ff}
    .mock-grid{display:grid;grid-template-columns:minmax(0,1.85fr) minmax(340px,.9fr);gap:12px;align-items:start}.mock-panel{background:linear-gradient(180deg,#0c151d,#081018);border:1px solid #1b3040;border-radius:13px;overflow:hidden}.mock-phead{display:flex;justify-content:space-between;align-items:center;padding:13px 14px;border-bottom:1px solid #172936}.mock-ptitle{font-size:18px;font-weight:1000;color:#fff}.mock-sub{font-size:11px;color:#8498a6}.mock-tabs{display:flex;gap:5px;flex-wrap:wrap}.mock-tab{font-size:10px;font-weight:900;padding:5px 8px;border-radius:999px;background:#0c1821;border:1px solid #1e3443;color:#98aab6}.mock-tab.active{background:linear-gradient(180deg,#2c5f16,#17380e);border-color:#65ff34;color:#fff}
    .mock-play-head,.mock-play{display:grid;grid-template-columns:70px minmax(210px,1.5fr) minmax(120px,.8fr) 92px 95px 78px;gap:8px;align-items:center}.mock-play-head{padding:9px 13px;background:#09131b;color:#8598a6;font-size:10px;font-weight:950}.mock-play{padding:11px 13px;border-top:1px solid #132431}.mock-play:hover{background:#0d1922}.mock-time{font-size:12px;color:#c4d1d9;font-weight:800}.mock-match{font-size:14px;color:#fff}.mock-pick{display:inline-flex;align-items:center;justify-content:center;border-radius:9px;padding:9px 12px;font-size:15px;line-height:1.15;font-weight:1000;border:1px solid;white-space:normal;overflow-wrap:anywhere;max-width:100%;min-height:38px;text-align:center}.mock-pick.green{color:#8aff64;background:#102a13;border-color:#3d7c2f}.mock-pick.blue{color:#79beff;background:#0d2133;border-color:#285f8e}.mock-pick.gold{color:#ffd06c;background:#2a210c;border-color:#7d6424}.mock-pick.red{color:#ff8a8e;background:#301214;border-color:#7d3438}.mock-conf{font-size:14px;color:#d8e1e6;font-weight:900;line-height:1.2}.mock-edge{font-size:15px;font-weight:1000;color:#fff}.mock-action{display:inline-flex;align-items:center;justify-content:center;padding:8px 10px;border-radius:8px;font-size:13px;line-height:1.15;font-weight:1000;white-space:normal;text-align:center}.mock-action.bet{background:#154d19;color:#8cff6d;border:1px solid #337d37}.mock-action.watch{background:#46320e;color:#ffd66c;border:1px solid #89651f}.mock-action.research{background:#102a43;color:#7dc5ff;border:1px solid #2b5f86}.mock-action.pass{background:#461416;color:#ff8c91;border:1px solid #833237}
    .market-card2{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center;padding:11px 12px;border-top:1px solid #142431}.market-card2 .mname{font-size:13px;font-weight:950;color:#fff}.market-card2 .msub{font-size:11px;color:#8fa2af;margin-top:2px}.market-card2 .mval{text-align:right;font-size:15px;font-weight:1000;color:#64ff40}.market-card2 .mbooks{font-size:10px;color:#8ea0ac;margin-top:2px}.mock-donut-wrap{display:flex;align-items:center;gap:16px;padding:16px}.mock-donut{width:110px;height:110px;border-radius:50%;display:grid;place-items:center;background:var(--donut);position:relative}.mock-donut:after{content:"";position:absolute;width:70px;height:70px;border-radius:50%;background:#0a1218}.mock-donut strong{position:relative;z-index:1;font-size:25px;color:#fff}.mock-legend{flex:1}.mock-legend div{display:flex;justify-content:space-between;padding:4px 0;font-size:12px;color:#d3dde3}.mock-legend b{color:#fff}
    .mock-lower{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:12px}.mock-mini{background:linear-gradient(180deg,#0c151e,#081018);border:1px solid #1a2d3b;border-radius:12px;overflow:hidden}.mock-mini.green{border-color:#2d5e2d}.mock-mini.purple{border-color:#5a3475}.mock-mini.gold{border-color:#755818}.mock-mini.blue{border-color:#26567f}.mock-mini-title{padding:11px 12px;font-size:13px;font-weight:1000;color:#fff;border-bottom:1px solid #162733}.mock-mini-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;padding:9px 11px;border-top:1px solid #13232f}.mock-mini-row b{font-size:12px;color:#fff}.mock-mini-row span{font-size:10px;color:#879aa7}.mock-mini-row .v{font-size:14px;font-weight:1000;color:#68ff3c}.mock-mini-row .p{font-size:14px;font-weight:1000;color:#ca83ff}.mock-mini-row .g{font-size:14px;font-weight:1000;color:#ffc550}.mock-empty{padding:14px;color:#8fa2af;font-size:12px;line-height:1.45}.mock-foot{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
    @media(max-width:1100px){.mock-kpis{grid-template-columns:repeat(3,1fr)}.mock-grid{grid-template-columns:1fr}.mock-lower{grid-template-columns:repeat(2,1fr)}}
    @media(max-width:760px){.mock-kpis{grid-template-columns:repeat(2,1fr)}.mock-lower,.mock-foot{grid-template-columns:1fr}.mock-title{font-size:31px}.mock-play-head,.mock-play{grid-template-columns:58px minmax(160px,1fr) 95px 70px}.mock-play-head>*:nth-child(n+5),.mock-play>*:nth-child(n+5){display:none}}
    </style>''', unsafe_allow_html=True)

    st.markdown('<div class="mock-hero"><div class="mock-eyebrow">SPORTS INTELLIGENCE COMMAND CENTER</div><div class="mock-title">EVERYTHING THAT MATTERS. <span>RIGHT NOW.</span></div><div class="mock-copy">Best bets, player props, PrizePicks, parlays, fantasy, Survivor, weather, market movement and historical research — all in one place.</div></div>', unsafe_allow_html=True)

    cards=[("OFFICIAL BETS",mlb_bets,"Validated MLB model","green"),("PROP EDGES",prop_edges,"Qualified edges","blue"),("PRIZEPICKS LINES",len(pp),"Standard NFL + MLB","purple"),("FANTASY LEAGUES",leagues,"Active league profiles","gold"),("SURVIVOR ENTRIES",survivor_entries,"Tracked separately","red"),("PICKS TRACKED",tracker.get("total",0),"All sports","cyan")]
    st.markdown('<div class="mock-kpis">'+''.join(f'<div class="mock-kpi {c}"><div class="klabel">{esc(a)}</div><div class="knum">{esc(b)}</div><div class="knote">{esc(n)}</div></div>' for a,b,n,c in cards)+'</div>',unsafe_allow_html=True)

    top=rows[:6]
    plays='<div class="mock-panel"><div class="mock-phead"><div><div class="mock-ptitle">🔥 TODAY’S TOP PLAYS</div><div class="mock-sub">Same-day only · no stale substitutions</div></div><div class="mock-tabs"><span class="mock-tab active">ALL</span><span class="mock-tab">MLB</span><span class="mock-tab">NFL</span><span class="mock-tab">CFB</span><span class="mock-tab">PROPS</span><span class="mock-tab">PARLAYS</span></div></div><div class="mock-play-head"><div>TIME</div><div>MATCHUP</div><div>PICK / LEAN</div><div>CONF</div><div>EDGE</div><div>STATUS</div></div>'
    if not top: plays+='<div class="mock-empty">No qualified same-day plays right now.</div>'
    else:
        for r in top:
            sport=r.get('sport',''); pill='blue' if sport=='NFL' else 'gold' if sport=='CFB' else 'green'; pill='red' if r.get('action')=='PASS' else pill; ac={'BET':'bet','WATCH':'watch','RESEARCH':'research','PASS':'pass'}.get(str(r.get('action','')).upper(),'research'); match=matchup_html(sport,r.get('away',''),r.get('home',''))
            plays+=f'<div class="mock-play"><div class="mock-time">{esc(r.get("time","—"))}</div><div class="mock-match">{match}</div><div><span class="mock-pick {pill}">{esc(r.get("pick","—"))}</span></div><div class="mock-conf">{esc(r.get("confidence","—"))}</div><div class="mock-edge">{esc(r.get("metric","—"))}<div class="tiny">{esc(r.get("metric_label",""))}</div></div><div><span class="mock-action {ac}">{esc(r.get("action","—"))}</span></div></div>'
    plays+='</div>'

    md=load("mlb_market")
    if not md.empty and "game_start" in md.columns: md=md[md["game_start"].apply(is_today)]
    market='<div class="mock-panel"><div class="mock-phead"><div><div class="mock-ptitle">MARKET MOVEMENT</div><div class="mock-sub">Biggest same-day moves</div></div></div>'
    if md.empty: market+='<div class="mock-empty">No same-day MLB movement signal available.</div>'
    else:
        score=pd.to_numeric(md.get("market_signal_score",pd.Series(index=md.index,dtype=float)),errors="coerce"); md=md.assign(_score=score).sort_values("_score",ascending=False).head(5)
        for _,r in md.iterrows():
            m=f'{str(first(r,["away_team"],"")).title()} @ {str(first(r,["home_team"],"")).title()}'; books=first(r,["books_moving"],"—"); strength=first(r,["signal_strength"],"—"); sig=first(r,["market_signal"],"—")
            market+=f'<div class="market-card2"><div><div class="mname">{esc(m)}</div><div class="msub">{esc(sig)}</div></div><div><div class="mval">{esc(strength)}</div><div class="mbooks">{esc(books)} books</div></div></div>'
    market+='</div>'

    counts={k:sum(1 for r in rows if str(r.get('action','')).upper()==k) for k in ['BET','WATCH','RESEARCH','PASS']}; total=max(sum(counts.values()),1); pct=[counts[k]/total*100 for k in ['BET','WATCH','RESEARCH','PASS']]; a=pct[0]; b=a+pct[1]; c=b+pct[2]; donut=f'conic-gradient(#52e932 0 {a:.2f}%,#ffc146 {a:.2f}% {b:.2f}%,#3d9dff {b:.2f}% {c:.2f}%,#ff4e58 {c:.2f}% 100%)'; alignment=round((counts['BET']+counts['WATCH'])/total*100)
    mix=f'<div class="mock-panel" style="margin-top:10px"><div class="mock-phead"><div><div class="mock-ptitle">HULK VS MARKET</div><div class="mock-sub">Board action mix · not win probability</div></div></div><div class="mock-donut-wrap"><div class="mock-donut" style="--donut:{donut}"><strong>{alignment}%</strong></div><div class="mock-legend"><div><span style="color:#72ff59">BET</span><b>{counts["BET"]}</b></div><div><span style="color:#ffd05a">WATCH</span><b>{counts["WATCH"]}</b></div><div><span style="color:#67b7ff">RESEARCH</span><b>{counts["RESEARCH"]}</b></div><div><span style="color:#ff7479">PASS</span><b>{counts["PASS"]}</b></div></div></div></div>'
    st.markdown(f'<div class="mock-grid"><div>{plays}</div><div>{market}{mix}</div></div>',unsafe_allow_html=True)

    prop_html='<div class="mock-mini green"><div class="mock-mini-title">PLAYER PROPS SPOTLIGHT</div>'
    if top_props:
        for r in top_props[:3]: prop_html+=f'<div class="mock-mini-row"><div><b>{esc(r.get("player","—"))}</b><br><span>{esc(str(r.get("canonical_market","—")).replace("_"," ").title())}</span></div><div class="v">{esc(r.get("hulk_prop_score","—"))}</div></div>'
    else: prop_html+='<div class="mock-empty">No qualified prop edges right now.</div>'
    prop_html+='</div>'
    qd=load("qualified_parlays"); parlay_html='<div class="mock-mini purple"><div class="mock-mini-title">PARLAY CHEMISTRY</div>'
    if qd.empty: parlay_html+='<div class="mock-empty">No qualified parlays today. Hulk will not force legs.</div>'
    else:
        for _,r in qd.head(3).iterrows(): parlay_html+=f'<div class="mock-mini-row"><div><b>{esc(first(r,["parlay_type","type"],"Qualified"))}</b></div><div class="p">{esc(first(r,["parlay_score","score"],"—"))}</div></div>'
    parlay_html+='</div>'
    pp_html='<div class="mock-mini blue"><div class="mock-mini-title">PRIZEPICKS BOARD</div>'
    if pp.empty: pp_html+='<div class="mock-empty">No standard NFL/MLB PrizePicks lines in cache.</div>'
    else:
        for _,r in pp.head(3).iterrows():
            player=first(r,["player_name","player","name"],"—"); stat=first(r,["stat_type","stat","market"],"—"); line=first(r,["line_score","line","projection"],"—"); pp_html+=f'<div class="mock-mini-row"><div><b>{esc(player)}</b><br><span>{esc(stat)}</span></div><div class="p">{esc(line)}</div></div>'
    pp_html+='</div>'
    fantasy_html=f'<div class="mock-mini gold"><div class="mock-mini-title">FANTASY / WAIVER WIRE</div><div class="mock-mini-row"><div><b>{esc(active or "No active league")}</b><br><span>{synced} synced leagues</span></div><div class="g">{leagues}</div></div><div class="mock-empty">Connect a league to turn waivers and lineup advice into league-aware recommendations.</div></div>'
    st.markdown(f'<div class="mock-lower">{prop_html}{parlay_html}{pp_html}{fantasy_html}</div>',unsafe_allow_html=True)

    weather_count=0; mlb=load("mlb")
    if not mlb.empty and "temperature_f" in mlb.columns: weather_count=int(pd.to_numeric(mlb["temperature_f"],errors="coerce").notna().sum())
    weather=f'<div class="mock-mini blue"><div class="mock-mini-title">WEATHER IMPACT</div><div class="mock-mini-row"><div><b>MLB games with weather</b></div><div class="v">{weather_count}</div></div><div class="mock-mini-row"><div><b>NFL Weather</b><br><span>Wind · precipitation · roof</span></div><div class="v">→</div></div></div>'
    pulse=f'<div class="mock-mini green"><div class="mock-mini-title">LINEUP / ACCOUNT PULSE</div><div class="mock-mini-row"><div><b>Active fantasy league</b></div><div class="g">{esc(active or "—")}</div></div><div class="mock-mini-row"><div><b>Survivor entries</b></div><div class="v">{survivor_entries}</div></div></div>'
    st.markdown(f'<div class="mock-foot">{weather}{pulse}</div>',unsafe_allow_html=True)

    st.markdown('<div class="mock-phead" style="margin-top:10px"><div><div class="mock-ptitle">QUICK DEEP DIVE</div><div class="mock-sub">Jump straight into the research layer</div></div></div>', unsafe_allow_html=True)
    q1,q2,q3=st.columns(3)
    q1.button("🎮 Game Research",use_container_width=True,on_click=_set_betting_page,args=("Game Research",))
    q2.button("🧾 Bet Tracker",use_container_width=True,on_click=_set_betting_page,args=("Bet Tracker",))
    q3.button("📈 Performance Lab",use_container_width=True,on_click=_set_betting_page,args=("Performance Lab",))

def _prop_market_from_pp(stat):
    key = re.sub(r"[^a-z0-9]+", " ", str(stat).lower()).strip()
    exact = {
        "pass yards":"passing_yards", "pass attempts":"pass_attempts", "pass comp":"pass_completions",
        "pass tds":"passing_tds", "int":"interceptions", "rec yards":"receiving_yards",
        "recs":"receptions", "rush yards":"rushing_yards", "rush atts":"rush_attempts",
        "longest rec":"longest_reception", "longest rush":"longest_rush", "kicking points":"kicking_points",
        "player tds":"anytime_td", "hits":"hits", "hits allowed":"hits_allowed", "hits runs rbis":"hits_runs_rbis",
        "runs":"runs", "singles":"singles", "tb":"total_bases", "walks":"walks",
        "earned runs allowed":"earned_runs", "ks":"pitcher_strikeouts", "po":"pitcher_outs",
    }
    return exact.get(key)


def _prop_signal_index(sport=None):
    d = load("prop_signals")
    if d.empty:
        return {}
    if sport and "sport" in d.columns:
        d = d[d["sport"].astype(str).str.upper().eq(str(sport).upper())]
    out = {}
    for _, r in d.iterrows():
        player = _norm_name(r.get("player", ""))
        market = str(r.get("canonical_market", "")).strip().lower()
        if not player or not market:
            continue
        k = (player, market)
        score = num(r.get("hulk_prop_score"), 0) or 0
        if k not in out or score > (num(out[k].get("hulk_prop_score"), 0) or 0):
            out[k] = r.to_dict()
    return out


def _tracked_bets():
    data = _load_json(P["bet_tracker"], {"bets": []})
    bets = data.get("bets", []) if isinstance(data, dict) else []
    return [x for x in bets if isinstance(x, dict)]


def _save_tracked_bets(bets):
    _save_json(P["bet_tracker"], {"bets": bets})


def _american_profit(odds, stake):
    o = num(odds); s = num(stake, 0) or 0
    if o is None or o == 0:
        return None
    return s * (o / 100.0) if o > 0 else s * (100.0 / abs(o))


def _implied_prob(odds):
    o = num(odds)
    if o is None or o == 0:
        return None
    return 100.0 / (o + 100.0) if o > 0 else abs(o) / (abs(o) + 100.0)


def _bet_clv(b):
    market = str(b.get("market", "")).upper()
    side = str(b.get("side", "")).upper()
    bet_line = num(b.get("line")); close_line = num(b.get("closing_line"))
    if market in {"TOTAL", "PROP"} and bet_line is not None and close_line is not None:
        if side == "OVER": return close_line - bet_line
        if side == "UNDER": return bet_line - close_line
    if market == "SPREAD" and bet_line is not None and close_line is not None:
        return bet_line - close_line
    p0, p1 = _implied_prob(b.get("odds")), _implied_prob(b.get("closing_odds"))
    if p0 is not None and p1 is not None:
        return (p1 - p0) * 100.0
    return None


def _tracker_summary():
    bets = _tracked_bets()
    graded = [b for b in bets if str(b.get("result", "")).upper() in {"WIN", "LOSS", "PUSH"}]
    units = 0.0; risked = 0.0; w = l = psh = 0; clvs = []
    for b in graded:
        stake = num(b.get("stake"), 0) or 0
        risked += stake
        result = str(b.get("result", "")).upper()
        if result == "WIN":
            w += 1; units += (_american_profit(b.get("odds"), stake) or 0)
        elif result == "LOSS":
            l += 1; units -= stake
        else: psh += 1
        c = _bet_clv(b)
        if c is not None: clvs.append(c)
    roi = (units / risked * 100.0) if risked else None
    return {"bets":len(bets), "graded":len(graded), "w":w, "l":l, "p":psh, "units":units, "risked":risked, "roi":roi, "avg_clv":(sum(clvs)/len(clvs) if clvs else None)}


def _set_betting_page(page):
    st.session_state["hc_betting"] = page


def bet_tracker_page():
    css(); topbar("🎯 Betting", "Personal bet log · local Oracle storage")
    st.markdown('<div class="command-hero"><div class="command-eyebrow">HULK BET TRACKER</div><div class="command-title">PICK THE GAME. <span>TRACK THE BET.</span></div><div class="command-sub">Guided sport → game → market entry. Closing information stays optional until known; Hulk never invents CLV.</div></div>',unsafe_allow_html=True)
    summary=_tracker_summary(); cards=[("Tracked",summary["bets"],"all bets","blue"),("Record",f'{summary["w"]}-{summary["l"]}-{summary["p"]}',"graded only","green"),("Units",f'{summary["units"]:+.2f}u',"entered stake + odds","green"),("ROI","—" if summary["roi"] is None else f'{summary["roi"]:+.1f}%',"graded risk only","blue"),("Avg CLV","—" if summary["avg_clv"] is None else f'{summary["avg_clv"]:+.2f}',"when close entered","purple"),("Storage","LOCAL","Oracle JSON","gold")]
    st.markdown('<div class="kpi-row">'+''.join(f'<div class="kpi {c}"><div class="lbl">{esc(a)}</div><div class="val">{esc(b)}</div><div class="note">{esc(n)}</div></div>' for a,b,n,c in cards)+'</div>',unsafe_allow_html=True)
    with st.expander("➕ Track a bet",expanded=not bool(summary["bets"])):
        sport=st.selectbox("1. Sport",["MLB","NFL","CFB","OTHER"],key="bt_sport")
        rows={"MLB":rows_mlb,"NFL":rows_nfl,"CFB":rows_cfb}.get(sport,lambda:[])()
        options=[f'{r["away"]} @ {r["home"]} · {r["time"]} ET' for r in rows]
        game=st.selectbox("2. Game",options+["Manual / other"] if options else ["Manual / other"],key="bt_game")
        market=st.selectbox("3. Market",["MONEYLINE","SPREAD","TOTAL","PROP","PARLAY","PRIZEPICKS","OTHER"],key="bt_market")
        chosen=None
        if game!="Manual / other" and game in options: chosen=rows[options.index(game)]
        event=(f'{chosen["away"]} @ {chosen["home"]}' if chosen else st.text_input("Game / player / entry",placeholder="Manual description"))
        if chosen:
            st.markdown(matchup_card(sport,chosen["away"],chosen["home"],chosen["start"],[("Hulk/Research Lean",chosen.get("pick")),("Status",chosen.get("action")),("Market Context",chosen.get("market"))],badge=market,accent="blue"),unsafe_allow_html=True)
        if market=="MONEYLINE" and chosen:
            side=st.selectbox("4. Side",[chosen["away"],chosen["home"]])
            line=None
        elif market=="SPREAD" and chosen:
            side=st.selectbox("4. Side",[chosen["away"],chosen["home"]]); line=st.number_input("Spread",value=0.0,step=0.5)
        elif market=="TOTAL":
            side=st.selectbox("4. Side",["OVER","UNDER"]); line=st.number_input("Total",value=0.0,step=0.5)
        else:
            side=st.text_input("4. Side / selection",placeholder="OVER / UNDER / team / player"); line=st.number_input("Bet line",value=None,step=0.5,placeholder="Optional")
        c1,c2,c3=st.columns(3)
        with c1: odds=st.number_input("American odds",value=-110,step=1)
        with c2: stake=st.number_input("Stake (units)",min_value=0.0,value=1.0,step=0.25)
        with c3: result=st.selectbox("Result",["OPEN","WIN","LOSS","PUSH"],key="bt_result")
        c1,c2=st.columns(2)
        with c1: close_line=st.number_input("Closing line",value=None,step=0.5,placeholder="Add later")
        with c2: close_odds=st.number_input("Closing odds",value=None,step=1,placeholder="Add later")
        notes=st.text_input("Notes",placeholder="Book, reason, Hulk context, etc.")
        if st.button("Save Bet",type="primary",disabled=not bool(str(event).strip())):
            bets=_tracked_bets(); bets.append({"id":datetime.now(ET).strftime("%Y%m%d%H%M%S%f"),"created_at":datetime.now(ET).isoformat(),"sport":sport,"market":market,"event":str(event).strip(),"side":str(side).strip(),"line":line,"odds":int(odds),"stake":float(stake),"result":result,"closing_line":close_line,"closing_odds":close_odds,"notes":notes.strip()}); _save_tracked_bets(bets); st.rerun()
    bets=_tracked_bets()
    if not bets: st.info("No tracked bets yet. The Performance Lab stays empty until real bets are recorded."); return
    cards=[]
    for b in reversed(bets[-30:]):
        c=_bet_clv(b); accent="green" if str(b.get("result")).upper()=="WIN" else "red" if str(b.get("result")).upper()=="LOSS" else "blue"
        cards.append(player_card(b.get("event","—"),b.get("sport","—"),b.get("market",""),[("Side",b.get("side","—")),("Line",b.get("line","—")),("Odds",b.get("odds","—")),("Stake",b.get("stake","—")),("CLV","—" if c is None else round(c,2))],badge=b.get("result","OPEN"),accent=accent,note=str(b.get("created_at",""))[:16].replace("T"," ")))
    st.markdown('<div class="clean-player-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    raw=pd.DataFrame([{**b,"CLV":_bet_clv(b)} for b in bets])
    research_table(raw,None,"Full Bet Log",520)


def performance_lab_page():
    css(); topbar("🎯 Betting", "Personal performance · no fabricated record")
    bets=_tracked_bets(); st.markdown('<div class="sport-banner"><div><div class="sport-name">Hulk Performance Lab</div><div class="sport-sub">Your tracked results by sport and market. Official model records remain separate.</div></div><div class="source-pill">TRACKED BETS ONLY</div></div>',unsafe_allow_html=True)
    if not bets: st.info("Performance Lab activates after you log bets in Bet Tracker."); return
    graded=[b for b in bets if str(b.get("result","")).upper() in {"WIN","LOSS","PUSH"}]
    if not graded: st.info("Bets are tracked, but none are graded yet."); return
    rows=[]
    for b in graded:
        stake=num(b.get("stake"),0) or 0; res=str(b.get("result","")).upper(); profit=0.0
        if res=="WIN": profit=_american_profit(b.get("odds"),stake) or 0
        elif res=="LOSS": profit=-stake
        rows.append({"Sport":b.get("sport","—"),"Market":b.get("market","—"),"Result":res,"Stake":stake,"Profit":profit,"CLV":_bet_clv(b)})
    df=pd.DataFrame(rows)
    for group in ["Sport","Market"]:
        g=df.groupby(group,dropna=False).agg(Bets=("Result","size"),Wins=("Result",lambda x:(x=="WIN").sum()),Losses=("Result",lambda x:(x=="LOSS").sum()),Risked=("Stake","sum"),Units=("Profit","sum"),Avg_CLV=("CLV","mean")).reset_index()
        g["ROI %"]=(g["Units"]/g["Risked"]*100).where(g["Risked"].ne(0)).round(1); g["Units"]=g["Units"].round(2); g["Avg_CLV"]=g["Avg_CLV"].round(2)
        cards=[]
        for _,r in g.iterrows():
            cards.append(player_card(r[group],group,metrics=[("Bets",r["Bets"]),("Record",f'{r["Wins"]}-{r["Losses"]}'),("Units",f'{r["Units"]:+.2f}'),("ROI",f'{r["ROI %"]:+.1f}%' if pd.notna(r["ROI %"]) else "—"),("Avg CLV",r["Avg_CLV"] if pd.notna(r["Avg_CLV"]) else "—")],badge="PERFORMANCE",accent="green" if r["Units"]>=0 else "red"))
        st.subheader(f"By {group}"); st.markdown('<div class="clean-player-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    research_table(df,None,"Full Performance Data",420)


def game_research_page():
    css(); topbar("🎯 Betting", "Current matchup + historical vault")
    st.markdown('<div class="command-hero"><div class="command-eyebrow">ONE-GAME DEEP DIVE</div><div class="command-title">THE GAME FIRST. <span>EVERYTHING ELSE BELOW.</span></div><div class="command-sub">Choose the matchup once. Team logos, start time and key game context stay at the top; deeper stats and raw research live underneath.</div></div>',unsafe_allow_html=True)
    sport=st.selectbox("Sport",["MLB","NFL","CFB"],key="game_research_sport")
    board=load({"MLB":"mlb","NFL":"nfl","CFB":"cfb"}[sport])
    if board.empty: st.info(f"{sport} current board unavailable."); return
    ac,hc=("away_team","home_team") if sport!="CFB" else ("away","home"); sc="gameDate" if sport=="MLB" else "start"
    labels=[]; idxs=[]
    for i,r in board.iterrows(): labels.append(f'{first(r,[ac],"—")} @ {first(r,[hc],"—")} · {fmt_time(first(r,[sc],None))} ET'); idxs.append(i)
    pick=st.selectbox("Matchup",labels); r=board.loc[idxs[labels.index(pick)]]; away,home=str(first(r,[ac],"—")),str(first(r,[hc],"—")); start=first(r,[sc],None)
    if sport in {"MLB","NFL"}:
        au,hu=logo_url(sport,away),logo_url(sport,home); ai=f'<img src="{au}" alt="">' if au else ''; hi=f'<img src="{hu}" alt="">' if hu else ''
        middle=f'<div class="matchup-mid">{esc(sport)} DEEP DIVE<strong>@</strong>{esc(fmt_datetime(start))}</div>'
        st.markdown(f'<div class="matchup-hero"><div class="matchup-team">{ai}<b>{esc(away)}</b></div>{middle}<div class="matchup-team">{hi}<b>{esc(home)}</b></div></div>',unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="matchup-hero"><div class="matchup-team"><b>{esc(away)}</b></div><div class="matchup-mid">CFB DEEP DIVE<strong>@</strong>{esc(fmt_datetime(start))}</div><div class="matchup-team"><b>{esc(home)}</b></div></div>',unsafe_allow_html=True)
    if sport=="MLB":
        vals=[("Hulk Pick",first(r,["lean","hulk_model_side"],"—")),("Decision",first(r,["decision"],"—")),("Confidence",first(r,["confidence"],"—")),("Total",first(r,["totals_median_point"],"—")),("Venue",first(r,["venue"],"—")),("Weather",f'{first(r,["temperature_f"],"—")}°F · {first(r,["wind_mph"],"—")} mph')]
        st.markdown('<div class="research-summary">'+''.join(f'<div><span>{esc(a)}</span><b>{esc(b)}</b></div>' for a,b in vals)+'</div>',unsafe_allow_html=True)
        cards=[player_card(first(r,["away_probable_pitcher"],"—"),away,"Away Starter",[("Starter Matchup Score",first(r,["away_starter_vs_home_lineup"],"—")),("Bullpen Workload",first(r,["away_bullpen_workload"],"—"))],badge="AWAY",sport="MLB",accent="blue"),player_card(first(r,["home_probable_pitcher"],"—"),home,"Home Starter",[("Starter Matchup Score",first(r,["home_starter_vs_away_lineup"],"—")),("Bullpen Workload",first(r,["home_bullpen_workload"],"—"))],badge="HOME",sport="MLB",accent="blue")]
        st.markdown('<div class="clean-player-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
        st.markdown(matchup_card("MLB",away,home,start,[("Park Factor",round(num(r.get("park_run_factor"),0),3) if num(r.get("park_run_factor")) is not None else "—"),("Run Environment",first(r,["run_environment_flag"],"—")),("Pitch Types Matched",first(r,["pitch_types_matched"],"—")),("Sample Pitches",first(r,["sample_pitches"],"—"))],badge="ENVIRONMENT",accent="cyan"),unsafe_allow_html=True)
        hist=load("mlb_history")
        if not hist.empty and {"away_team","home_team"}.issubset(hist.columns):
            x=hist[((hist["away_team"].astype(str).eq(away))&(hist["home_team"].astype(str).eq(home)))|((hist["away_team"].astype(str).eq(home))&(hist["home_team"].astype(str).eq(away)))].copy()
            avg=pd.to_numeric(x.get("total_runs"),errors="coerce").mean() if not x.empty else None
            st.markdown(f'<div class="research-summary"><div><span>H2H Games in Vault</span><b>{len(x)}</b></div><div><span>Average Total Runs</span><b>{"—" if avg is None or pd.isna(avg) else f"{avg:.2f}"}</b></div></div>',unsafe_allow_html=True)
            research_table(x,None,"Historical Matchup — Full Data",440)
        research_table(pd.DataFrame([r]),None,"Current Game — Full Research Row",420)
    elif sport=="NFL":
        vals=[("Home Market",pct_value(r.get("home_market_win_prob"))),("Away Market",pct_value(r.get("away_market_win_prob"))),("Spread",first(r,["home_spread"],"—")),("Total",first(r,["total"],"—")),("Books",first(r,["sportsbooks"],"—")),("Survivor",first(r,["survivor_grade"],"—"))]
        st.markdown('<div class="research-summary">'+''.join(f'<div><span>{esc(a)}</span><b>{esc(b)}</b></div>' for a,b in vals)+'</div>',unsafe_allow_html=True)
        hist=load("nfl_history")
        if not hist.empty:
            rev={k:v.upper() for k,v in NFL_ABBR.items()}; aa=rev.get(away,away); hh=rev.get(home,home)
            h2h=hist[((hist["away_team"].astype(str).eq(aa))&(hist["home_team"].astype(str).eq(hh)))|((hist["away_team"].astype(str).eq(hh))&(hist["home_team"].astype(str).eq(aa)))].copy()
            cards=[]
            for _,hr in h2h.sort_values("gameday",ascending=False).head(10).iterrows(): cards.append(matchup_card("NFL",hr.get("away_team","—"),hr.get("home_team","—"),hr.get("gameday"),[("Score",f'{hr.get("away_score","—")}–{hr.get("home_score","—")}'),("Spread",hr.get("spread_line","—")),("Total",hr.get("total_line","—")),("Weather",f'{hr.get("temp","—")}° · {hr.get("wind","—")} mph')],badge="HISTORY",accent="blue",note=hr.get("stadium","")))
            if cards: st.markdown('<div class="clean-game-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
            research_table(h2h,None,"NFL Historical H2H — Full Data",440)
        research_table(pd.DataFrame([r]),None,"Current Game — Full Research Row",420)
    else:
        vals=[("Research Lean",first(r,["research_lean"],"—")),("Confidence",first(r,["research_confidence"],"—")),("Home Win Comp",pct_value(r.get("comp_home_win_prob"))),("Proj Margin",round(num(r.get("comp_projected_margin"),0) or 0,1)),("Market Total",first(r,["Total"],"—")),("Proj Total",round(num(r.get("comp_projected_total"),0) or 0,1))]
        st.markdown('<div class="research-summary">'+''.join(f'<div><span>{esc(a)}</span><b>{esc(b)}</b></div>' for a,b in vals)+'</div>',unsafe_allow_html=True)
        hist=load("cfb_history")
        if not hist.empty and {"away_team","home_team"}.issubset(hist.columns):
            x=hist[((hist["away_team"].astype(str).eq(away))&(hist["home_team"].astype(str).eq(home)))|((hist["away_team"].astype(str).eq(home))&(hist["home_team"].astype(str).eq(away)))].copy(); st.metric("Historical H2H rows",len(x)); research_table(x,None,"CFB Historical H2H — Full Data",440)
        research_table(pd.DataFrame([r]),None,"Current Game — Full Research Row",420)
        st.caption("College football remains team/game research only. No college player props are introduced here.")


def prizepicks_page(sport=None):
    css(); topbar("🟣 PrizePicks", f"Cache updated {age('pp')}")
    raw=load("pp")
    if raw.empty:
        st.info("PrizePicks Standard cache is unavailable."); return
    d=raw.copy()
    if "odds_type" in d.columns: d=d[d["odds_type"].astype(str).str.lower().eq("standard")]
    if "is_promo" in d.columns: d=d[~d["is_promo"].astype(str).str.lower().isin(["true","1"])]
    if "league" in d.columns: d=d[d["league"].astype(str).str.upper().isin(["NFL","MLB"])]
    if sport and "league" in d.columns: d=d[d["league"].astype(str).str.upper().eq(sport)]
    eligible_before_time=d.copy()
    if "start_time" in d.columns:
        dt=pd.to_datetime(d["start_time"],errors="coerce",utc=True); now=pd.Timestamp.now(tz="UTC")
        d=d[dt.isna()|(dt>=now-pd.Timedelta(hours=1))].copy()
    title=(sport+" PrizePicks") if sport else "PrizePicks Command Center"
    st.markdown(f'<div class="sport-banner"><div><div class="sport-name">{esc(title)}</div><div class="sport-sub">Standard lines only · promos filtered · player-first display</div></div><div class="source-pill">{len(d):,} UPCOMING LINES</div></div>',unsafe_allow_html=True)
    if d.empty:
        latest="—"
        if not eligible_before_time.empty and "start_time" in eligible_before_time.columns:
            dt=pd.to_datetime(eligible_before_time["start_time"],errors="coerce",utc=True).dropna()
            if not dt.empty: latest=dt.max().tz_convert(ET).strftime("%a %-m/%-d %-I:%M %p ET")
        st.markdown(f'<div class="empty-rich"><b>No upcoming standard {esc(sport or "NFL/MLB")} lines.</b><span>The cache contains {len(eligible_before_time):,} matching standard rows before the future-time filter. Latest scheduled line: {esc(latest)}. If today should have lines, refresh the PrizePicks collector rather than showing stale rows.</span></div>',unsafe_allow_html=True)
        research_table(eligible_before_time,None,"PrizePicks Feed Diagnostics",420)
        return
    sig_index=_prop_signal_index(sport)
    cards=[]; matched_research=0
    for _,r in d.sort_values([c for c in ["rank","player"] if c in d.columns]).head(36).iterrows():
        sp=str(r.get("league","")).upper(); team=str(r.get("team","—")); start=fmt_datetime(r.get("start_time"))
        market_key=_prop_market_from_pp(r.get("stat","")); sig=sig_index.get((_norm_name(r.get("player","")),market_key)) if market_key else None
        metrics=[("Line",r.get("line","—")),("Stat",r.get("stat","—")),("Start",start)]
        note=r.get("description","")
        if sig:
            matched_research+=1
            metrics += [("Sportsbook Median",sig.get("market_median","—")),("Books",sig.get("book_count","—")),("Agreement",f'{sig.get("book_agreement_pct","—")}%'),("Hulk Score",sig.get("hulk_prop_score","—"))]
            note=f'{sig.get("market_direction","—")} research lean · {note}'
        cards.append(player_card(r.get("player","—"),team,r.get("position",""),metrics,badge=sp,sport=sp,accent="purple",note=note))
    st.markdown(f'<div class="panel"><div class="phead"><div class="ptitle purple">PRIZEPICKS × HULK RESEARCH</div><div class="psub">{matched_research} visible lines matched to sportsbook consensus</div></div></div>',unsafe_allow_html=True)
    st.markdown('<div class="clean-player-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    research_table(d,None,"Full PrizePicks Research Data",520)


def cfb_totals_page():
    css(); topbar("🏟️ College Football",f"Cache updated {age('cfb')}")
    d=load("cfb")
    if d.empty: st.info("CFB board unavailable."); return
    rows=[]
    for _,r in d.iterrows():
        total=num(r.get("Total")); proj=num(r.get("comp_projected_total")); start=first(r,["start","start_dt"],None)
        if total is None or proj is None: continue
        edge=proj-total; rows.append({"start":start,"away":first(r,["away"],"—"),"home":first(r,["home"],"—"),"market":total,"proj":round(proj,1),"edge":round(edge,1),"lean":"OVER" if edge>=3 else "UNDER" if edge<=-3 else "PASS","conf":first(r,["research_confidence"],"—"),"samples":first(r,["comp_samples"],"—")})
    rows=sorted(rows,key=lambda z:abs(z["edge"]),reverse=True)
    st.markdown('<div class="sport-banner"><div><div class="sport-name">CFB Over / Unders</div><div class="sport-sub">Historical-comp total research. No college player props.</div></div><div class="source-pill">RESEARCH ONLY</div></div>',unsafe_allow_html=True)
    if not rows: st.info("No CFB totals have both a market total and comparable-game projection in the current cache."); return
    cards=[matchup_card("CFB",r["away"],r["home"],r["start"],[("Market O/U",r["market"]),("Projected",r["proj"]),("Edge",f'{r["edge"]:+.1f}'),("Samples",r["samples"]),("Confidence",r["conf"])],badge=r["lean"],accent="green" if r["lean"] in {"OVER","UNDER"} else "blue") for r in rows]
    st.markdown('<div class="clean-game-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    research_table(pd.DataFrame(rows),None,"Full CFB Totals Research",520)
    st.caption("Research leans from comparable-game total projections, not a validated official CFB totals betting model.")


def nfl_weather_page():
    css(); topbar("🏈 NFL","Historical weather vault ready · live forecast collector pending")
    try: hist=pd.read_csv(P["nfl_history"],low_memory=False)
    except Exception: hist=pd.DataFrame()
    st.markdown('<div class="sport-banner"><div><div class="sport-name">NFL Weather</div><div class="sport-sub">Weather belongs inside matchup, props, totals and Survivor context.</div></div><div class="source-pill">NFL WEATHER</div></div>',unsafe_allow_html=True)
    if hist.empty: st.info("NFL historical weather vault unavailable."); return
    sort_cols=[c for c in ["season","week"] if c in hist.columns]
    show=hist.sort_values(sort_cols,ascending=False).head(20) if sort_cols else hist.tail(20)
    cards=[]
    for _,r in show.iterrows():
        cards.append(matchup_card("NFL",r.get("away_team","—"),r.get("home_team","—"),r.get("gameday"),[("Temp",f'{r.get("temp","—")}°F'),("Wind",f'{r.get("wind","—")} mph'),("Roof",r.get("roof","—")),("Surface",r.get("surface","—")),("Total",r.get("total_line",r.get("total","—")))],badge=f'WEEK {r.get("week","—")}',accent="cyan",note=r.get("stadium","")))
    st.markdown('<div class="clean-game-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    research_table(hist,None,"Full NFL Weather / Stadium Vault",560)
    st.info("Current-game forecast ingestion remains separate. This page does not fabricate live forecasts when the collector has not populated them.")


def survivor_page():
    css(); topbar("🏈 NFL","Multi-entry Survivor manager")
    data=survivor_data(); entries=data.get("entries",{})
    st.markdown('<div class="sport-banner"><div><div class="sport-name">Survivor / Suicide Pool</div><div class="sport-sub">Every entry keeps its own used teams, current pick and future plan.</div></div><div class="source-pill">MULTI-ENTRY</div></div>',unsafe_allow_html=True)
    if entries:
        names=list(entries); active=data.get("active") if data.get("active") in names else names[0]; pick=st.selectbox("Active Entry",names,index=names.index(active))
        if pick!=data.get("active"): data["active"]=pick; _save_json(P["survivor_entries"],data)
        e=entries[pick]; c1,c2,c3,c4=st.columns(4)
        with c1: status=st.selectbox("Status",["ALIVE","ELIMINATED"],index=0 if e.get("status","ALIVE")=="ALIVE" else 1,key=f"status_{pick}")
        with c2: st.metric("Teams Used",len(e.get("used_teams",[])))
        with c3: st.metric("Future Picks",len(e.get("future_picks",{})))
        with c4: st.metric("Pool",e.get("pool") or "—")
        teams=sorted(NFL_ABBR.keys()); used=st.multiselect("Teams already used",teams,default=[x for x in e.get("used_teams",[]) if x in NFL_ABBR],key=f"used_{pick}"); choices=["—"]+teams
        saved_current=e.get("current_pick") if e.get("current_pick") in teams else "—"; saved_backup=e.get("backup_pick") if e.get("backup_pick") in teams else "—"; c1,c2=st.columns(2)
        with c1: current=st.selectbox("This week's pick",choices,index=choices.index(saved_current),key=f"cur_{pick}")
        with c2: backup=st.selectbox("Backup pick",choices,index=choices.index(saved_backup),key=f"bak_{pick}")
        if current!="—" and current in used: st.markdown("<div class='survivor-warning'>⚠️ This week's pick is already in this entry's used-team list.</div>",unsafe_allow_html=True)
        if current!="—" and backup==current: st.markdown('<div class="survivor-warning">⚠️ Backup pick must be different from the primary pick.</div>',unsafe_allow_html=True)
        plan=st.text_area("Future pick plan",value="\n".join(f"Week {k}: {v}" for k,v in sorted(e.get("future_picks",{}).items(),key=lambda kv:str(kv[0]))),placeholder="Week 2: Buffalo Bills\nWeek 3: Kansas City Chiefs")
        if st.button("Save Survivor Entry",type="primary"):
            fp={}
            for line in plan.splitlines():
                m=re.match(r"\s*Week\s*(\d+)\s*:\s*(.+)\s*$",line,re.I)
                if m: fp[m.group(1)]=m.group(2)
            e.update({"status":status,"used_teams":used,"current_pick":None if current=="—" else current,"backup_pick":None if backup=="—" else backup,"future_picks":fp}); entries[pick]=e; data["entries"]=entries; _save_json(P["survivor_entries"],data); st.success("Entry saved.")
    with st.expander("➕ Add Survivor Entry",expanded=not bool(entries)):
        name=st.text_input("Entry name",placeholder="Office Pool - Entry 1"); pool=st.text_input("Pool name",placeholder="Office Survivor")
        if st.button("Create Entry",disabled=not bool(name.strip())):
            entries[name.strip()]={"pool":pool.strip(),"status":"ALIVE","used_teams":[],"current_pick":None,"backup_pick":None,"future_picks":{},"history":[]}; data["entries"]=entries; data["active"]=name.strip(); _save_json(P["survivor_entries"],data); st.rerun()
    try: board=pd.read_csv(P["nfl_survivor"],low_memory=False) if P["nfl_survivor"].exists() else pd.DataFrame()
    except Exception: board=pd.DataFrame()
    if not board.empty:
        st.subheader("Hulk Survivor Board")
        cards=[]
        for _,r in board.head(20).iterrows():
            cards.append(matchup_card("NFL",r.get("away_team","—"),r.get("home_team","—"),r.get("start"),[("Survivor Pick",r.get("survivor_team","—")),("Win Chance",pct_value(r.get("survivor_win_prob"))),("Spread",r.get("survivor_spread","—")),("Books",r.get("sportsbooks","—"))],badge=r.get("survivor_grade","—"),accent="green" if str(r.get("survivor_grade","")) in {"A+","A"} else "blue"))
        st.markdown('<div class="clean-game-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
        research_table(board,None,"Full Survivor Research Data",480)
    st.caption("Future-value optimization will rank this week's safety against the value of saving strong teams for later weeks.")


def top300_page():
    css(); topbar("🏆 Fantasy", "Top 300 draft board")
    d=fdf()
    if d.empty: st.info("Fantasy board unavailable."); return
    rank=next((c for c in ["hulk_v2_rank","overall_rank","hulk_rank","rank"] if c in d.columns),None)
    if rank: d[rank]=pd.to_numeric(d[rank],errors="coerce"); d=d.sort_values(rank)
    st.markdown('<div class="sport-banner"><div><div class="sport-name">Fantasy Top 300 Cheat Sheet</div><div class="sport-sub">Player cards first; dense full board remains one click down.</div></div><div class="source-pill">TOP 300</div></div>',unsafe_allow_html=True)
    positions=sorted(d.get("position",pd.Series(dtype=str)).dropna().astype(str).unique().tolist()); pos=st.selectbox("Position",["ALL"]+positions)
    show=d if pos=="ALL" else d[d["position"].astype(str).eq(pos)]; limit=st.select_slider("Cards shown",options=[25,50,100,150,300],value=50)
    cards=[]
    for _,r in show.head(limit).iterrows():
        nm=first(r,["full_name","player","name"],"—"); action=first(r,["draft_action"],"DRAFT"); cards.append(player_card(nm,r.get("team","—"),r.get("position",""),[("Overall",r.get(rank,"—") if rank else "—"),("Tier",r.get("hulk_v2_tier","—")),("Consensus ADP",r.get("consensus_adp","—")),("Value vs ADP",r.get("hulk_value_vs_consensus","—")),("Proj PPR",r.get("proj_ppr_points","—"))],badge=action,accent="green" if "VALUE" in str(action).upper() else "blue"))
    st.markdown('<div class="clean-player-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    research_table(d.head(300),None,"Full Top 300 Draft Board",760)


def _safe_pct(v):
    x=num(v)
    if x is None:
        return "—"
    if 0 <= x <= 1:
        x*=100
    return f"{x:.0f}%"


def _money(v):
    x=num(v)
    if x is None:
        return "—"
    return f"{x:+.0f}"


def _short_team(v):
    s=str(v if v is not None else "—").strip()
    return s.title() if s.islower() else s


def betting_slate_page():
    css(); topbar("🎯 Betting","Today / upcoming cached slate")
    st.markdown('<div class="sport-banner"><div><div class="sport-name">Today’s Slate</div><div class="sport-sub">Game cards first. Full source data stays collapsed below.</div></div><div class="source-pill">NO RAW TABLES</div></div>',unsafe_allow_html=True)
    groups=[]
    for sport,key,start_col,away_col,home_col in [
        ("MLB","mlb","gameDate","away_team","home_team"),
        ("NFL","nfl","start","away_team","home_team"),
        ("CFB","cfb","start","away","home"),
    ]:
        d=load(key)
        if d.empty: continue
        cards=[]
        for _,r in d.head(24).iterrows():
            if sport=="MLB":
                metrics=[("Decision",first(r,["decision"],"—")),("Lean",first(r,["lean"],"—")),("Total",first(r,["totals_median_point"],"—")),("Books",first(r,["h2h_book_count","spreads_book_count"],"—"))]
                badge=first(r,["decision"],"MLB")
            elif sport=="NFL":
                metrics=[("Home ML",_money(r.get("home_moneyline"))),("Spread",first(r,["home_spread"],"—")),("Total",first(r,["total"],"—")),("Books",first(r,["sportsbooks"],"—"))]
                badge="NFL"
            else:
                metrics=[("Research Lean",first(r,["research_lean"],"—")),("Confidence",first(r,["research_confidence"],"—")),("Spread",first(r,["Home_spread"],"—")),("Total",first(r,["Total"],"—"))]
                badge="RESEARCH"
            cards.append(matchup_card(sport,_short_team(r.get(away_col,"—")),_short_team(r.get(home_col,"—")),r.get(start_col),metrics,badge=badge,accent="green" if str(badge).upper() in {"BET","A+","A"} else "blue"))
        groups.append((sport,d,cards))
    if not groups:
        st.info("No cached slate rows are available.")
        return
    for sport,d,cards in groups:
        st.subheader(sport)
        st.markdown('<div class="clean-game-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
        research_table(d,None,f"Full {sport} Slate Data",480)


def line_movement_clean_page():
    css(); topbar("🎯 Betting","MLB market movement cache")
    d=load("mlb_market")
    st.markdown('<div class="sport-banner"><div><div class="sport-name">Line Movement</div><div class="sport-sub">Grouped by game and market instead of spreadsheet columns.</div></div><div class="source-pill">MARKET</div></div>',unsafe_allow_html=True)
    if d.empty:
        st.info("No market movement cache is available."); return
    cards=[]
    for (away,home,start),g in d.groupby(["away_team","home_team","game_start"],dropna=False,sort=False):
        bits=[]; strength="—"
        for _,r in g.head(4).iterrows():
            market=str(r.get("core_market","market")).replace("_"," ").title()
            target=str(r.get("signal_target","—")).title()
            movers=first(r,["books_moving"],"—"); reporting=first(r,["books_reporting"],"—")
            bits.append((market,f"{target} · {movers}/{reporting} books"))
            strength=first(r,["signal_strength"],strength)
        cards.append(matchup_card("MLB",_short_team(away),_short_team(home),start,bits,badge=str(strength).upper(),accent="green" if str(strength).lower()=="strong" else "blue"))
    st.markdown('<div class="clean-game-grid">'+''.join(cards[:30])+'</div>',unsafe_allow_html=True)
    research_table(d,None,"Full Market Movement Data",560,rename={"away_team":"Away","home_team":"Home","game_start":"Start","core_market":"Market","signal_target":"Move","signal_strength":"Strength","books_reporting":"Books Reporting","books_moving":"Books Moving","consensus_among_movers_pct":"Mover Agreement %"})


def betting_results_clean_page():
    css(); topbar("🎯 Betting","Official graded history only")
    d=load("mlb_results")
    st.markdown('<div class="sport-banner"><div><div class="sport-name">Results</div><div class="sport-sub">Readable graded cards. Internal IDs and model plumbing stay out of the main view.</div></div><div class="source-pill">GRADED</div></div>',unsafe_allow_html=True)
    if d.empty:
        st.info("No graded official MLB results are available yet."); return
    show=d.tail(40).iloc[::-1]
    cards=[]
    for _,r in show.iterrows():
        away=first(r,["away_team","away"],"Away"); home=first(r,["home_team","home"],"Home"); start=first(r,["gameDate","game_date","start"],None)
        pick=first(r,["pick","hulk_model_side","lean","decision"],"—")
        result=first(r,["result","grade","bet_result","outcome"],"—")
        final=first(r,["final_score","score","final"],"—")
        metrics=[("Hulk Pick",pick),("Result",result),("Final",final),("Decision",first(r,["decision"],"—"))]
        cards.append(matchup_card("MLB",away,home,start,metrics,badge=str(result).upper(),accent="green" if str(result).upper() in {"WIN","W"} else "red" if str(result).upper() in {"LOSS","L"} else "blue"))
    st.markdown('<div class="clean-game-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    research_table(d,None,"Full Graded Results Data",560)


def research_clean_page():
    css(); topbar("🎯 Betting","Historical evidence and calibration")
    st.markdown('<div class="sport-banner"><div><div class="sport-name">Research</div><div class="sport-sub">Research summaries first. Calibration files remain available one click down.</div></div><div class="source-pill">EVIDENCE</div></div>',unsafe_allow_html=True)
    blocks=[]
    for label,key in [("MLB Historical Games","mlb_history"),("NFL Historical Games","nfl_history"),("CFB Historical Games","cfb_history")]:
        path=P.get(key)
        try: d=pd.read_csv(path,low_memory=False) if path and path.exists() else pd.DataFrame()
        except Exception: d=pd.DataFrame()
        blocks.append((label,d))
    cards=[]
    for label,d in blocks:
        seasons="—"
        if not d.empty and "season" in d.columns:
            vals=pd.to_numeric(d["season"],errors="coerce").dropna()
            if not vals.empty: seasons=f"{int(vals.min())}–{int(vals.max())}"
        cards.append(f'<div class="clean-game-card blue"><div class="clean-game-top"><div><div class="clean-matchup">{esc(label)}</div><div class="clean-time">Historical research vault</div></div><span class="clean-badge blue">{len(d):,} ROWS</span></div><div class="clean-metrics"><div class="clean-metric"><span>Coverage</span><b>{esc(seasons)}</b></div><div class="clean-metric"><span>Status</span><b>{"READY" if not d.empty else "UNAVAILABLE"}</b></div></div></div>')
    st.markdown('<div class="clean-game-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    for label,d in blocks:
        research_table(d,None,f"{label} — Full Data",520)


def mlb_starting_pitching_page():
    css(); topbar("⚾ MLB","Probable starters and matchup context")
    d=load("mlb")
    st.markdown('<div class="sport-banner"><div><div class="sport-name">Starting Pitching</div><div class="sport-sub">Pitcher matchup cards replace the old wide table.</div></div><div class="source-pill">STARTERS</div></div>',unsafe_allow_html=True)
    if d.empty:
        st.info("MLB matchup board unavailable."); return
    cards=[]
    for _,r in d.head(30).iterrows():
        away=first(r,["away_team"],"—"); home=first(r,["home_team"],"—")
        metrics=[("Away Starter",first(r,["away_probable_pitcher"],"—")),("Away Matchup",first(r,["away_starter_vs_home_lineup"],"—")),("Home Starter",first(r,["home_probable_pitcher"],"—")),("Home Matchup",first(r,["home_starter_vs_away_lineup"],"—")),("Pitch Sample",first(r,["sample_pitches"],"—")),("Pitch Types",first(r,["pitch_types_matched"],"—"))]
        cards.append(matchup_card("MLB",away,home,first(r,["gameDate"],None),metrics,badge=first(r,["confidence"],"MLB"),accent="green" if str(first(r,["confidence"],"")).upper()=="HIGH" else "blue"))
    st.markdown('<div class="clean-game-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    research_table(d,["gameDate","away_team","away_probable_pitcher","away_starter_vs_home_lineup","home_team","home_probable_pitcher","home_starter_vs_away_lineup","sample_pitches","pitch_types_matched"],"Full Starting Pitching Research",520,rename={"gameDate":"Start","away_team":"Away","away_probable_pitcher":"Away Starter","away_starter_vs_home_lineup":"Away Starter Matchup","home_team":"Home","home_probable_pitcher":"Home Starter","home_starter_vs_away_lineup":"Home Starter Matchup","sample_pitches":"Pitch Sample","pitch_types_matched":"Pitch Types"})


def mlb_weather_clean_page():
    css(); topbar("⚾ MLB","Game weather and park context")
    d=load("mlb")
    st.markdown('<div class="sport-banner"><div><div class="sport-name">Weather Impact</div><div class="sport-sub">Game-by-game weather cards with park context.</div></div><div class="source-pill">WEATHER</div></div>',unsafe_allow_html=True)
    if d.empty:
        st.info("MLB weather board unavailable."); return
    cards=[]
    for _,r in d.head(30).iterrows():
        metrics=[("Temperature",f'{first(r,["temperature_f"],"—")}°F'),("Wind",f'{first(r,["wind_mph"],"—")} mph'),("Gusts",f'{first(r,["wind_gust_mph"],"—")} mph'),("Humidity",f'{first(r,["humidity_pct"],"—")}%'),("Rain",first(r,["precipitation"],"—")),("Park Factor",first(r,["park_run_factor"],"—"))]
        cards.append(matchup_card("MLB",first(r,["away_team"],"—"),first(r,["home_team"],"—"),first(r,["gameDate"],None),metrics,badge=first(r,["run_environment_flag"],"WEATHER"),accent="cyan",note=first(r,["venue"],"")))
    st.markdown('<div class="clean-game-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    research_table(d,["gameDate","away_team","home_team","venue","temperature_f","precipitation","wind_mph","wind_gust_mph","humidity_pct","park_run_factor","run_environment_flag"],"Full MLB Weather Data",520,rename={"gameDate":"Start","away_team":"Away","home_team":"Home","venue":"Ballpark","temperature_f":"Temp °F","precipitation":"Rain","wind_mph":"Wind mph","wind_gust_mph":"Gust mph","humidity_pct":"Humidity %","park_run_factor":"Park Factor","run_environment_flag":"Run Environment"})


def mlb_market_clean_page():
    css(); topbar("⚾ MLB","Movement and consensus overlay")
    d=load("mlb_market")
    st.markdown('<div class="sport-banner"><div><div class="sport-name">MLB Market</div><div class="sport-sub">One card per game with moneyline, spread and total movement grouped together.</div></div><div class="source-pill">CONSENSUS</div></div>',unsafe_allow_html=True)
    if d.empty:
        st.info("MLB market signal cache unavailable."); return
    cards=[]
    for (away,home,start),g in d.groupby(["away_team","home_team","game_start"],dropna=False,sort=False):
        metrics=[]; strongest="—"
        for _,r in g.iterrows():
            mk=str(r.get("core_market","market")).replace("_"," ").title()
            target=str(r.get("signal_target","—")).title()
            metrics.append((mk,f'{target} · {first(r,["books_moving"],"—")}/{first(r,["books_reporting"],"—")} books'))
            if str(r.get("signal_strength","")).lower()=="strong": strongest="STRONG"
        cards.append(matchup_card("MLB",_short_team(away),_short_team(home),start,metrics[:4],badge=strongest,accent="green" if strongest=="STRONG" else "blue"))
    st.markdown('<div class="clean-game-grid">'+''.join(cards[:30])+'</div>',unsafe_allow_html=True)
    research_table(d,None,"Full MLB Market Research",560,rename={"away_team":"Away","home_team":"Home","game_start":"Start","core_market":"Market","signal_target":"Target","signal_strength":"Strength","books_reporting":"Books","books_moving":"Books Moving","consensus_among_movers_pct":"Mover Agreement %","whole_market_share_pct":"Market Share %"})


def mlb_results_clean_page():
    return betting_results_clean_page()


def nfl_research_clean_page():
    css(); topbar("🏈 NFL","Historical game research")
    path=P["nfl_history"]
    try: d=pd.read_csv(path,low_memory=False) if path.exists() else pd.DataFrame()
    except Exception: d=pd.DataFrame()
    st.markdown('<div class="sport-banner"><div><div class="sport-name">NFL Research</div><div class="sport-sub">Historical matchup cards first; the full vault stays collapsed.</div></div><div class="source-pill">HISTORY</div></div>',unsafe_allow_html=True)
    if d.empty:
        st.info("NFL historical vault unavailable."); return
    sort_cols=[c for c in ["season","week"] if c in d.columns]
    show=d.sort_values(sort_cols,ascending=False).head(40) if sort_cols else d.tail(40)
    cards=[]
    for _,r in show.iterrows():
        final=f'{first(r,["away_score"],"—")}–{first(r,["home_score"],"—")}'
        metrics=[("Final",final),("Spread",first(r,["spread_line"],"—")),("Total",first(r,["total_line","total"],"—")),("Roof",first(r,["roof"],"—")),("Temp",f'{first(r,["temp"],"—")}°F'),("Wind",f'{first(r,["wind"],"—")} mph')]
        cards.append(matchup_card("NFL",first(r,["away_team"],"—"),first(r,["home_team"],"—"),first(r,["gameday"],None),metrics,badge=f'WEEK {first(r,["week"],"—")}',accent="blue",note=first(r,["stadium"],"")))
    st.markdown('<div class="clean-game-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    research_table(d,None,"Full NFL Historical Research",620)


def cfb_matchups_clean_page():
    css(); topbar("🏟️ College Football","Current research board")
    d=load("cfb")
    st.markdown('<div class="sport-banner"><div><div class="sport-name">CFB Matchups</div><div class="sport-sub">Game cards with research lean, market and comparable-game context.</div></div><div class="source-pill">RESEARCH ONLY</div></div>',unsafe_allow_html=True)
    if d.empty:
        st.info("CFB research board unavailable."); return
    cards=[]
    for _,r in d.head(40).iterrows():
        metrics=[("Research Lean",first(r,["research_lean"],"—")),("Confidence",first(r,["research_confidence"],"—")),("Home Spread",first(r,["Home_spread"],"—")),("Total",first(r,["Total"],"—")),("Comp Win",_safe_pct(first(r,["comp_home_win_prob"],None))),("Proj Margin",first(r,["comp_projected_margin"],"—"))]
        cards.append(matchup_card("CFB",first(r,["away"],"—"),first(r,["home"],"—"),first(r,["start"],None),metrics,badge=first(r,["research_confidence"],"RESEARCH"),accent="gold"))
    st.markdown('<div class="clean-game-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    research_table(d,None,"Full CFB Matchup Research",560)


def cfb_research_clean_page():
    css(); topbar("🏟️ College Football","Historical comps and calibration")
    d=load("cfb")
    path=P["cfb_history"]
    try: hist=pd.read_csv(path,low_memory=False) if path.exists() else pd.DataFrame()
    except Exception: hist=pd.DataFrame()
    st.markdown('<div class="sport-banner"><div><div class="sport-name">CFB Research</div><div class="sport-sub">Current research summaries first. Historical vault remains available below.</div></div><div class="source-pill">COMPS</div></div>',unsafe_allow_html=True)
    cards=[]
    for _,r in d.head(30).iterrows():
        metrics=[("Lean",first(r,["research_lean"],"—")),("Confidence",first(r,["research_confidence"],"—")),("Comp Samples",first(r,["comp_samples"],"—")),("Home Win Comp",_safe_pct(first(r,["comp_home_win_prob"],None))),("Projected Margin",first(r,["comp_projected_margin"],"—")),("Projected Total",first(r,["comp_projected_total"],"—"))]
        cards.append(matchup_card("CFB",first(r,["away"],"—"),first(r,["home"],"—"),first(r,["start"],None),metrics,badge="RESEARCH",accent="gold"))
    if cards: st.markdown('<div class="clean-game-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    research_table(d,None,"Full Current CFB Research",560)
    research_table(hist,None,"Full Historical CFB Vault",560)


def feature(mode,page):
    if mode=="🎯 Betting" and page=="Today's Slate": betting_slate_page(); return True
    if mode=="🎯 Betting" and page=="Line Movement": line_movement_clean_page(); return True
    if mode=="🎯 Betting" and page=="Results": betting_results_clean_page(); return True
    if mode=="🎯 Betting" and page=="Research": research_clean_page(); return True
    if page=="MLB Best Bets": mlb_best_bets_page(); return True
    if page=="CFB Best Bets": cfb_best_bets_page(); return True
    if page=="Game Research": game_research_page(); return True
    if page=="Bet Tracker": bet_tracker_page(); return True
    if page=="Performance Lab": performance_lab_page(); return True
    if page=="Parlay Center": render_parlays(); return True
    if page=="MLB Parlays": render_parlays("MLB"); return True
    if page=="NFL Parlays": render_parlays("NFL"); return True
    if page=="CFB Parlays": render_parlays("CFB"); return True
    if page=="PrizePicks Dashboard": prizepicks_page(); return True
    if page=="NFL PrizePicks": prizepicks_page("NFL"); return True
    if page=="MLB PrizePicks": prizepicks_page("MLB"); return True
    if page=="My Leagues": leagues_page(); return True
    if page=="Top 300 Cheat Sheet": top300_page(); return True
    if page=="Waiver Wire Weekly": waivers_page(); return True
    if page=="Lineup": lineup_page(); return True
    if page=="Trade Finder": trade_finder_page(); return True
    if page=="Historical Explorer": historical_explorer_page(); return True
    if page=="Survivor": survivor_page(); return True
    if page=="NFL Weather": nfl_weather_page(); return True
    if page=="CFB Over / Unders": cfb_totals_page(); return True
    if mode=="⚾ MLB" and page=="Starting Pitching": mlb_starting_pitching_page(); return True
    if mode=="⚾ MLB" and page=="Weather": mlb_weather_clean_page(); return True
    if mode=="⚾ MLB" and page=="MLB Market": mlb_market_clean_page(); return True
    if mode=="⚾ MLB" and page=="MLB Results": mlb_results_clean_page(); return True
    if mode=="🏈 NFL" and page=="NFL Research": nfl_research_clean_page(); return True
    if mode=="🏟️ College Football" and page=="CFB Matchups": cfb_matchups_clean_page(); return True
    if mode=="🏟️ College Football" and page=="CFB Research": cfb_research_clean_page(); return True
    if mode=="🏆 Fantasy" and page=="NFL Research": nfl_research_clean_page(); return True
    return False
