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
    .plays-head,.play-row{display:grid;grid-template-columns:70px minmax(240px,1.7fr) minmax(120px,.9fr) 95px 105px 110px 88px;gap:8px;align-items:center}.plays-head{background:#0e1922;border:1px solid #172b3a;border-radius:7px;padding:10px;font-size:12px;color:#aeb9c2;font-weight:900}.play-row{padding:12px 9px;border-bottom:1px solid #13232f;font-size:15px}.matchup-flex{display:flex;align-items:center;gap:6px;min-width:0}.team-chip{display:inline-flex;align-items:center;gap:5px;min-width:0}.team-chip img{width:24px;height:24px;object-fit:contain}.team-chip b{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.at{color:#657681;font-weight:800}.dim{color:#93a2ad}.pick{font-weight:950;color:#fff}.badge{display:inline-block;padding:6px 9px;border-radius:7px;font-weight:1000;text-align:center;border:1px solid}.bet{background:rgba(85,255,50,.12);border-color:rgba(85,255,50,.34);color:#a9ff8f}.watch{background:rgba(255,194,71,.10);border-color:rgba(255,194,71,.34);color:#ffd66c}.research{background:rgba(76,194,255,.10);border-color:rgba(76,194,255,.34);color:#8ed8ff}.pass{background:rgba(255,92,97,.10);border-color:rgba(255,92,97,.34);color:#ff8589}.good{color:var(--g)}.warn{color:var(--a)}.bad{color:var(--r)}.blue{color:var(--b)}.purple{color:var(--p)}
    .two-col{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(320px,.8fr);gap:10px;align-items:start}.stack{display:flex;flex-direction:column;gap:10px}.info-row{display:grid;grid-template-columns:minmax(0,1.5fr) .7fr .7fr;gap:8px;padding:9px 5px;border-bottom:1px solid #13232f;font-size:13px}.info-row b{color:#fff}.empty{padding:28px 16px;text-align:center;border:1px dashed #284052;border-radius:9px;background:#091119}.empty b{font-size:16px}.empty span{display:block;color:var(--m);font-size:13px;margin-top:5px}
    .mini-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:10px}.system-row{display:flex;justify-content:space-between;gap:12px;padding:9px 4px;border-bottom:1px solid #13232f;font-size:13px}.system-row .status-ok{color:var(--g);font-weight:900}.system-row .status-info{color:var(--b);font-weight:900}
    .command-hero{position:relative;overflow:hidden;background:radial-gradient(circle at 80% 20%,rgba(85,255,50,.24),transparent 34%),linear-gradient(135deg,#0b1b13,#071019 55%,#0a0d12);border:1px solid rgba(85,255,50,.38);border-radius:18px;padding:22px 24px;margin:4px 0 12px;box-shadow:0 0 34px rgba(85,255,50,.08)}
    .command-eyebrow{font-size:12px;letter-spacing:.18em;color:#9aff76;font-weight:950}.command-title{font-size:46px;line-height:1.05;font-weight:1000;margin:4px 0;color:#fff}.command-title span{color:var(--g)}.command-sub{font-size:16px;color:#b8c5cd;max-width:940px}.command-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:10px 0}.action-card{background:linear-gradient(145deg,#0c171f,#081017);border:1px solid #193142;border-radius:12px;padding:14px;min-height:118px}.action-card.green{border-color:rgba(85,255,50,.32)}.action-card.purple{border-color:rgba(185,120,255,.35)}.action-card.amber{border-color:rgba(255,194,71,.35)}.action-kicker{font-size:11px;color:#8fa0ac;font-weight:900;letter-spacing:.07em}.action-value{font-size:25px;font-weight:1000;margin:5px 0}.action-copy{font-size:14px;color:#9fb0ba;line-height:1.45}.vault-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.vault-item{background:#0c161e;border:1px solid #172a38;border-radius:9px;padding:11px}.vault-item b{font-size:22px;color:#fff;display:block}.vault-item span{font-size:11px;color:#91a0aa}.pp-card-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.pp-player-card{background:linear-gradient(180deg,#121020,#0c0b16);border:1px solid rgba(185,120,255,.30);border-radius:12px;padding:13px}.pp-player-top{display:flex;align-items:center;gap:9px}.pp-player-top img{width:34px;height:34px;object-fit:contain}.pp-player{font-size:16px;font-weight:950}.pp-team{font-size:11px;color:#9c90aa}.pp-stat{font-size:12px;color:#bdb4ca;margin-top:8px}.pp-line-big{font-size:26px;font-weight:1000;color:var(--p);margin-top:2px}.pp-start{font-size:10px;color:#83798e;margin-top:3px}
    .league-actions{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px;margin:0 0 12px}.league-action{background:linear-gradient(180deg,#0d1922,#091119);border:1px solid #1b3445;border-radius:11px;padding:11px 12px}.league-action b{display:block;color:#fff;font-size:14px}.league-action span{display:block;color:#91a3ae;font-size:11px;margin-top:2px}.command-hero:before{content:"";position:absolute;inset:-2px;background:linear-gradient(90deg,transparent,rgba(85,255,50,.12),transparent);filter:blur(22px);pointer-events:none}.pp-research{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin-top:9px}.pp-research span{background:#0a1118;border:1px solid #20293a;border-radius:6px;padding:6px;font-size:10px}.survivor-warning{border:1px solid rgba(255,194,71,.36);background:rgba(255,194,71,.07);padding:10px 12px;border-radius:8px;margin:7px 0;color:#ffd66c;font-weight:800}
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
        d=d[d["game_start"].apply(is_today)]
    h='<div class="panel"><div class="phead"><div class="ptitle">MARKET MOVEMENT</div><div class="psub">MLB signals today</div></div>'
    if d.empty:
        h+='<div class="empty"><b>No current MLB movement signals.</b><span>No cross-sport market data is substituted.</span></div>'
    else:
        score=pd.to_numeric(d.get("market_signal_score",pd.Series(index=d.index,dtype=float)),errors="coerce")
        d=d.assign(_score=score).sort_values("_score",ascending=False).head(6)
        for _,r in d.iterrows():
            h+=f'<div class="info-row"><div><b>{esc(str(first(r,["away_team"],"" )).title())} @ {esc(str(first(r,["home_team"],"")).title())}</b><br><span class="dim">{esc(first(r,["market_signal"],"—"))}</span></div><div>{esc(first(r,["books_moving"],"—"))} moving</div><div class="good">{esc(first(r,["signal_strength"],"—"))}</div></div>'
    st.markdown(h+'</div>',unsafe_allow_html=True)


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
    elif mode=="🏟️ College Football": dashboard_shell(mode,rows_cfb())
    elif mode=="🟣 PrizePicks": prizepicks_page()
    elif mode=="🏆 Fantasy": fantasy_command_center()
    else: dashboard_shell(mode,[])
    st.stop()


def render_parlays(sport=None):
    css(); mode={"MLB":"⚾ MLB","NFL":"🏈 NFL","CFB":"🏟️ College Football"}.get(sport,"🎯 Betting")
    topbar(mode); st.markdown(parlay_panel(mode),unsafe_allow_html=True)


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
    css(); topbar("🏆 Fantasy", "League-aware waiver wire")
    d, rank, name = _fantasy_ranked_board()
    if d.empty or not name: st.error("Fantasy board unavailable."); return
    data, leagues, active, league = active_league_context()
    free_agents=_split_names(league.get("free_agents",[])) if active else []
    roster=_split_names(league.get("roster",[])) if active else []
    if active:
        st.markdown(f'<div class="sport-banner"><div><div class="sport-name">Waiver Wire · {esc(active)}</div><div class="sport-sub">Only league-available players are ranked when the free-agent pool is synced or entered.</div></div><div class="source-pill">{esc(league.get("platform","MANUAL"))}</div></div>',unsafe_allow_html=True)
    else:
        st.warning("No active league. Showing the generic fantasy board until a league is added.")
    if free_agents:
        keys={_norm_name(x) for x in free_agents}
        d=d[d[name].map(_norm_name).isin(keys)].copy()
    elif roster:
        roster_keys={_norm_name(x) for x in roster}
        d=d[~d[name].map(_norm_name).isin(roster_keys)].copy()
        st.info("Roster is known, but the provider free-agent pool is not. Hulk has removed your rostered players, but cannot know which players belong to other teams yet.")
    elif active:
        st.info("This league has no roster/free-agent data yet. Add it in My Leagues or connect a provider later; generic rankings are shown for now.")
    if d.empty:
        st.info("No available players from the league pool matched the current Hulk fantasy board."); return
    d=d.copy()
    d["Waiver Call"]=["ADD" if i<10 else "WATCH" if i<30 else "DEEP STASH" for i in range(len(d))]
    proj=next((c for c in ["proj_ppr_points","projected_points","projection"] if c in d.columns),None)
    cols=[c for c in [name,"team","position",rank,"hulk_v2_tier","tier",proj,"consensus_adp","depth_rank","status","Waiver Call"] if c and c in d.columns]
    st.dataframe(d[cols].head(75),hide_index=True,width="stretch",height=700)


def lineup_page():
    css(); topbar("🏆 Fantasy", "League-aware lineup board")
    d, rank, name = _fantasy_ranked_board()
    if d.empty or not name: st.error("Fantasy board unavailable."); return
    _, _, active, league = active_league_context()
    saved_roster=_split_names(league.get("roster",[])) if active else []
    options=d[name].dropna().astype(str).drop_duplicates().tolist()
    matched=[]
    if saved_roster:
        lookup={_norm_name(x):x for x in options}
        matched=[lookup[k] for k in [_norm_name(x) for x in saved_roster] if k in lookup]
        st.caption(f"Using roster from {active}. You can adjust the selection below without changing the saved league profile.")
    roster=st.multiselect("Roster",options,default=matched,key=f"hulk_lineup_{active or 'manual'}")
    if not roster: st.info("Add players above or save a roster in My Leagues to build a Start/Bench board."); return
    x=d[d[name].astype(str).isin(roster)].copy()
    score=next((c for c in ["proj_ppr_points","projected_points","projection","hulk_v2_score","hulk_score"] if c in x.columns),None)
    if score:
        x[score]=pd.to_numeric(x[score],errors="coerce"); x=x.sort_values(score,ascending=False)
    elif rank:
        x[rank]=pd.to_numeric(x[rank],errors="coerce"); x=x.sort_values(rank)
    x["Hulk Lineup Call"]=["START" if i<min(7,len(x)) else "BENCH" for i in range(len(x))]
    cols=[c for c in [name,"team","position",score,rank,"hulk_v2_tier","tier","status","Hulk Lineup Call"] if c and c in x.columns]
    st.dataframe(x[cols],hide_index=True,width="stretch")
    st.caption("The current Start/Bench label is a roster ordering aid, not a full slot optimizer yet. Exact starting-slot constraints will come from synced league settings.")


def trade_finder_page():
    css(); topbar("🏆 Fantasy", "Trade research")
    d, rank, name = _fantasy_ranked_board()
    if d.empty or not name: st.error("Fantasy board unavailable."); return
    _, _, active, league = active_league_context()
    roster=_split_names(league.get("roster",[])) if active else []
    st.markdown('<div class="sport-banner"><div><div class="sport-name">Hulk Trade Finder</div><div class="sport-sub">Built for roster-aware trades, not isolated player-vs-player grades.</div></div><div class="source-pill">FOUNDATION</div></div>',unsafe_allow_html=True)
    if not active:
        st.info("Add and select a league first. Trade Finder needs the active roster and eventually every opponent roster from league sync."); return
    if not roster:
        st.info("Save this league\'s roster in My Leagues. Once provider sync supplies opponent rosters, Hulk can search for trades that improve both teams."); return
    lookup={_norm_name(v):v for v in d[name].astype(str)}
    mine=[lookup[k] for k in [_norm_name(x) for x in roster] if k in lookup]
    x=d[d[name].astype(str).isin(mine)].copy()
    cols=[c for c in [name,"team","position",rank,"hulk_v2_tier","consensus_adp","proj_ppr_points","vorp"] if c and c in x.columns]
    st.subheader(f"{active} · Your Trade Assets")
    st.dataframe(x[cols],hide_index=True,width="stretch")
    st.info("Opponent-roster sync is required before Hulk generates proposed trades. It will not invent targets from players who are not actually on another team in your league.")


def historical_explorer_page():
    css(); topbar("🎯 Betting", "Historical vault explorer")
    st.markdown('<div class="command-hero"><div class="command-eyebrow">HULK HISTORICAL INTELLIGENCE</div><div class="command-title">DON\'T JUST SEE THE PICK. <span>SEE THE HISTORY.</span></div><div class="command-sub">Search the actual MLB, NFL and college football vaults by teams and context. Filters only appear for fields that exist in the cached historical data.</div></div>',unsafe_allow_html=True)
    sport=st.selectbox("Sport",["NFL","MLB","CFB"],key="hist_sport")
    key={"NFL":"nfl_history","MLB":"mlb_history","CFB":"cfb_history"}[sport]
    d=load(key)
    if d.empty: st.info(f"{sport} historical vault is unavailable."); return
    home="home_team" if "home_team" in d.columns else None
    away="away_team" if "away_team" in d.columns else None
    teams=sorted(set(d[home].dropna().astype(str)).union(set(d[away].dropna().astype(str)))) if home and away else []
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
        if team!="ALL":
            x=x[((x[home].astype(str).eq(team)) & x[away].astype(str).eq(opponent)) | ((x[away].astype(str).eq(team)) & x[home].astype(str).eq(opponent))]
        else:
            x=x[x[home].astype(str).eq(opponent)|x[away].astype(str).eq(opponent)]
    if sport=="NFL":
        f1,f2,f3=st.columns(3)
        if "roof" in x.columns:
            vals=["ALL"]+sorted(x["roof"].dropna().astype(str).unique().tolist()); roof=f1.selectbox("Roof",vals)
            if roof!="ALL": x=x[x["roof"].astype(str).eq(roof)]
        if "surface" in x.columns:
            vals=["ALL"]+sorted(x["surface"].dropna().astype(str).unique().tolist()); surface=f2.selectbox("Surface",vals)
            if surface!="ALL": x=x[x["surface"].astype(str).eq(surface)]
        if "wind" in x.columns:
            maxwind=f3.slider("Max wind",0,50,50); w=pd.to_numeric(x["wind"],errors="coerce"); x=x[w.isna()|w.le(maxwind)]
    st.markdown(f'<div class="kpi-row"><div class="kpi green"><div class="lbl">MATCHING GAMES</div><div class="val">{len(x):,}</div><div class="note">real rows from {sport} vault</div></div></div>',unsafe_allow_html=True)
    if x.empty: st.info("No historical games match those filters."); return
    if sport=="NFL":
        cols=[c for c in ["gameday","season","week","away_team","away_score","home_team","home_score","spread_line","total_line","roof","surface","temp","wind","stadium","home_ats_result","ou_result"] if c in x.columns]
    elif sport=="MLB":
        cols=[c for c in ["officialDate","away_team","away_score","home_team","home_score","total_runs","venue","home_days_since_last","away_days_since_last","current_h2h_books","current_totals_books"] if c in x.columns]
    else:
        cols=[c for c in ["game_date","season","week","away_team","away_points","home_team","home_points","home_margin","total_points","neutral","conference_game","home_rest_days","away_rest_days","home_margin_last5","away_margin_last5"] if c in x.columns]
    date_col=next((c for c in ["gameday","officialDate","game_date"] if c in x.columns),None)
    if date_col: x=x.sort_values(date_col,ascending=False)
    st.dataframe(x[cols].head(500),hide_index=True,width="stretch",height=720)
    if sport=="MLB":
        st.caption("Pitch-level research is stored separately in MLB_PITCHER_ARSENAL and MLB_BATTER_VS_PITCH_TYPE. This explorer does not fabricate pitch context that is not present in the game-master rows.")


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
    hist = {
        "MLB": count_rows(P["mlb_history"]),
        "NFL": count_rows(P["nfl_history"]),
        "CFB": count_rows(P["cfb_history"]),
    }
    st.markdown(
        '<div class="command-hero">'
        '<div class="command-eyebrow">SPORTS INTELLIGENCE COMMAND CENTER</div>'
        '<div class="command-title">EVERYTHING THAT MATTERS. <span>RIGHT NOW.</span></div>'
        '<div class="command-sub">Best bets, player props, PrizePicks, parlays, fantasy, Survivor, weather, market movement and historical research — one surface with the deeper vault one click away.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    cards = [
        ("Official MLB Bets", mlb_bets, "validated Hulk MLB model", "green"),
        ("Hulk Prop Edges", prop_edges, f"{prop_leans} qualified leans · score is not probability", "green"),
        ("PrizePicks Lines", len(pp), "NFL + MLB standard lines", "purple"),
        ("Fantasy Leagues", leagues, f"{synced} synced · {active or 'no active league'}", "purple"),
        ("Survivor Entries", survivor_entries, "multi-entry tracking", "amber"),
        ("Tracked Bets", tracker["bets"], ("ROI —" if tracker["roi"] is None else f'ROI {tracker["roi"]:+.1f}%'), "blue"),
    ]
    st.markdown(
        '<div class="kpi-row">' + ''.join(
            f'<div class="kpi {c}"><div class="lbl">{esc(a)}</div><div class="val">{esc(b)}</div><div class="note">{esc(n)}</div></div>'
            for a, b, n, c in cards
        ) + '</div>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([1.75, .85], gap="small")
    with c1:
        play_table("🎯 Betting", rows)
    with c2:
        action_cards = [
            ("🟣 PRIZEPICKS", f"{len(pp):,} standard NFL/MLB lines", "Open PrizePicks to compare player lines against Hulk prop research.", "purple"),
            ("🏆 FANTASY", active or "No active league", "League-aware waivers, lineup and roster actions become personalized as leagues sync.", "green"),
            ("🏈 SURVIVOR", f"{survivor_entries} saved entries", "Track used teams and future picks independently for every pool entry.", "amber"),
        ]
        st.markdown(
            '<div class="command-grid" style="grid-template-columns:1fr">' + ''.join(
                f'<div class="action-card {c}"><div class="action-kicker">{esc(k)}</div><div class="action-value">{esc(v)}</div><div class="action-copy">{esc(cp)}</div></div>'
                for k, v, cp, c in action_cards
            ) + '</div>',
            unsafe_allow_html=True,
        )
    b1, b2, b3 = st.columns([1.05, 1.05, .9], gap="small")
    with b1:
        mlb_market_panel()
    with b2:
        st.markdown(parlay_panel("🎯 Betting"), unsafe_allow_html=True)
    with b3:
        vault = ''.join(
            f'<div class="vault-item"><b>{v:,}</b><span>{k} games</span></div>' for k, v in hist.items()
        )
        st.markdown(
            '<div class="panel"><div class="phead"><div class="ptitle">HISTORICAL VAULT</div><div class="psub">deep research foundation</div></div>'
            f'<div class="vault-grid">{vault}</div>'
            '<div class="action-copy" style="margin-top:10px">Home/away, weather, pitchers, park/stadium, market and matchup context can surface from the historical vault where the underlying columns support it.</div></div>',
            unsafe_allow_html=True,
        )
    if top_props:
        h = '<div class="panel"><div class="phead"><div class="ptitle green">🔥 TOP PROP RESEARCH TODAY</div><div class="psub">strongest qualified market-quality signals</div></div>'
        for r in top_props:
            h += (
                f'<div class="info-row"><div><b>{esc(r.get("player", "—"))}</b><br>'
                f'<span class="dim">{esc(str(r.get("canonical_market", "—")).replace("_", " ").title())} · {esc(r.get("market_direction", "—"))}</span></div>'
                f'<div>{esc(r.get("market_median", "—"))}</div><div class="good">{esc(r.get("hulk_prop_score", "—"))}</div></div>'
            )
        st.markdown(h + '</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel"><div class="phead"><div class="ptitle">QUICK DEEP DIVE</div><div class="psub">stay inside the Betting command center</div></div></div>',unsafe_allow_html=True)
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
    st.markdown('<div class="command-hero"><div class="command-eyebrow">HULK BET TRACKER</div><div class="command-title">TRACK THE BET. <span>LEARN FROM THE CLOSE.</span></div><div class="command-sub">Record the exact line and odds you actually bet. Closing information stays optional until it is known; Hulk does not invent CLV.</div></div>', unsafe_allow_html=True)
    summary = _tracker_summary()
    cards=[("Tracked",summary["bets"],"all bets","blue"),("Record",f'{summary["w"]}-{summary["l"]}-{summary["p"]}',"graded only","green"),("Units",f'{summary["units"]:+.2f}u',"from entered stake + odds","green"),("ROI","—" if summary["roi"] is None else f'{summary["roi"]:+.1f}%',"graded risk only","blue"),("Avg CLV","—" if summary["avg_clv"] is None else f'{summary["avg_clv"]:+.2f}',"line pts or implied-prob pts","purple"),("Page API Cost",0,"local tracker","green")]
    st.markdown('<div class="kpi-row">'+''.join(f'<div class="kpi {c}"><div class="lbl">{esc(a)}</div><div class="val">{esc(b)}</div><div class="note">{esc(n)}</div></div>' for a,b,n,c in cards)+'</div>',unsafe_allow_html=True)
    with st.expander("➕ Track a bet", expanded=not bool(summary["bets"])):
        c1,c2,c3=st.columns(3)
        with c1: sport=st.selectbox("Sport",["MLB","NFL","CFB","NBA","NCAAB","NHL","OTHER"],key="bt_sport")
        with c2: market=st.selectbox("Market",["MONEYLINE","SPREAD","TOTAL","PROP","PARLAY","PRIZEPICKS","OTHER"],key="bt_market")
        with c3: result=st.selectbox("Result",["OPEN","WIN","LOSS","PUSH"],key="bt_result")
        event=st.text_input("Game / player / entry",placeholder="Yankees @ Red Sox · Aaron Judge hits")
        c1,c2,c3,c4=st.columns(4)
        with c1: side=st.text_input("Side",placeholder="OVER / UNDER / team")
        with c2: line=st.number_input("Bet line",value=None,step=0.5,placeholder="Optional")
        with c3: odds=st.number_input("American odds",value=-110,step=1)
        with c4: stake=st.number_input("Stake (units)",min_value=0.0,value=1.0,step=0.25)
        c1,c2=st.columns(2)
        with c1: close_line=st.number_input("Closing line",value=None,step=0.5,placeholder="Add later")
        with c2: close_odds=st.number_input("Closing odds",value=None,step=1,placeholder="Add later")
        notes=st.text_input("Notes",placeholder="Book, why you bet it, Hulk pick, etc.")
        if st.button("Save Bet",type="primary",disabled=not bool(event.strip())):
            bets=_tracked_bets(); bets.append({"id":datetime.now(ET).strftime("%Y%m%d%H%M%S%f"),"created_at":datetime.now(ET).isoformat(),"sport":sport,"market":market,"event":event.strip(),"side":side.strip(),"line":line,"odds":int(odds),"stake":float(stake),"result":result,"closing_line":close_line,"closing_odds":close_odds,"notes":notes.strip()}); _save_tracked_bets(bets); st.rerun()
    bets=_tracked_bets()
    if not bets:
        st.info("No tracked bets yet. The Performance Lab stays empty until real bets are recorded."); return
    rows=[]
    for b in reversed(bets):
        c=_bet_clv(b)
        rows.append({"Date":str(b.get("created_at",""))[:16].replace("T"," "),"Sport":b.get("sport"),"Market":b.get("market"),"Game / Player":b.get("event"),"Side":b.get("side"),"Line":b.get("line"),"Odds":b.get("odds"),"Stake":b.get("stake"),"Result":b.get("result"),"Close":b.get("closing_line"),"Close Odds":b.get("closing_odds"),"CLV":None if c is None else round(c,2)})
    st.dataframe(pd.DataFrame(rows),hide_index=True,width="stretch",height=620)
    st.caption("For totals/props/spreads, CLV is expressed in line points from the side you bet. For markets with only odds available, it is the change in implied probability points. These are not mixed into one calibrated performance metric.")


def performance_lab_page():
    css(); topbar("🎯 Betting", "Personal performance · no fabricated record")
    bets=_tracked_bets(); summary=_tracker_summary()
    st.markdown('<div class="sport-banner"><div><div class="sport-name">Hulk Performance Lab</div><div class="sport-sub">Your actual tracked results by sport and market. Official model records remain separate from personal wagers.</div></div><div class="source-pill">TRACKED BETS ONLY</div></div>',unsafe_allow_html=True)
    if not bets:
        st.info("Performance Lab activates after you log bets in Bet Tracker."); return
    graded=[b for b in bets if str(b.get("result","")).upper() in {"WIN","LOSS","PUSH"}]
    if not graded:
        st.info("Bets are tracked, but none are graded yet."); return
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
        st.subheader(f"By {group}"); st.dataframe(g,hide_index=True,width="stretch")
    st.caption("CLV is shown only where closing data was entered. The lab never fills missing closes or results automatically.")


def game_research_page():
    css(); topbar("🎯 Betting", "Current matchup + historical vault")
    st.markdown('<div class="command-hero"><div class="command-eyebrow">ONE-GAME DEEP DIVE</div><div class="command-title">ONE MATCHUP. <span>EVERY LAYER.</span></div><div class="command-sub">Current market/model context on top; historical team, venue, scoring and environment context underneath. Only fields actually present in the cache are shown.</div></div>',unsafe_allow_html=True)
    sport=st.selectbox("Sport",["MLB","NFL","CFB"],key="game_research_sport")
    board=load({"MLB":"mlb","NFL":"nfl","CFB":"cfb"}[sport])
    if board.empty: st.info(f"{sport} current board unavailable."); return
    ac, hc = ("away_team","home_team") if sport!="CFB" else ("away","home")
    sc = "gameDate" if sport=="MLB" else "start"
    labels=[]; idxs=[]
    for i,r in board.iterrows():
        labels.append(f'{first(r,[ac],"—")} @ {first(r,[hc],"—")} · {fmt_time(first(r,[sc],None))} ET'); idxs.append(i)
    pick=st.selectbox("Matchup",labels); r=board.loc[idxs[labels.index(pick)]]
    away,home=str(first(r,[ac],"—")),str(first(r,[hc],"—"))
    st.markdown(f'<div class="sport-banner"><div><div class="sport-name">{matchup_html(sport,away,home) if sport in {"MLB","NFL"} else esc(away)+" @ "+esc(home)}</div><div class="sport-sub">{esc(fmt_time(first(r,[sc],None)))} ET</div></div><div class="source-pill">{esc(sport)} DEEP DIVE</div></div>',unsafe_allow_html=True)
    if sport=="MLB":
        vals=[("Hulk Pick",first(r,["lean","hulk_model_side"],"—")),("Decision",first(r,["decision"],"—")),("Confidence",first(r,["confidence"],"—")),("Total",first(r,["totals_median_point"],"—")),("Park Factor",round(num(r.get("park_run_factor"),0),3) if num(r.get("park_run_factor")) is not None else "—"),("Weather",f'{first(r,["temperature_f"],"—")}°F · {first(r,["wind_mph"],"—")} mph')]
        st.markdown('<div class="kpi-row">'+''.join(f'<div class="kpi"><div class="lbl">{esc(a)}</div><div class="val">{esc(b)}</div></div>' for a,b in vals)+'</div>',unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1:
            st.markdown(f'<div class="panel"><div class="ptitle">STARTING PITCHING</div><div class="info-row"><div><b>{esc(away)}</b><br><span class="dim">{esc(first(r,["away_probable_pitcher"],"—"))}</span></div><div>{esc(first(r,["away_starter_vs_home_lineup"],"—"))}</div></div><div class="info-row"><div><b>{esc(home)}</b><br><span class="dim">{esc(first(r,["home_probable_pitcher"],"—"))}</span></div><div>{esc(first(r,["home_starter_vs_away_lineup"],"—"))}</div></div></div>',unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="panel"><div class="ptitle">ENVIRONMENT + BULLPEN</div><div class="system-row"><span>Venue</span><b>{esc(first(r,["venue"],"—"))}</b></div><div class="system-row"><span>Run environment</span><b>{esc(first(r,["run_environment_flag"],"—"))}</b></div><div class="system-row"><span>Away bullpen workload</span><b>{esc(first(r,["away_bullpen_workload"],"—"))}</b></div><div class="system-row"><span>Home bullpen workload</span><b>{esc(first(r,["home_bullpen_workload"],"—"))}</b></div></div>',unsafe_allow_html=True)
        hist=load("mlb_history")
        if not hist.empty:
            x=hist[((hist["away_team"].astype(str).eq(away))&(hist["home_team"].astype(str).eq(home)))|((hist["away_team"].astype(str).eq(home))&(hist["home_team"].astype(str).eq(away)))].copy()
            avg=pd.to_numeric(x.get("total_runs"),errors="coerce").mean() if not x.empty else None
            st.markdown(f'<div class="panel"><div class="phead"><div class="ptitle">HISTORICAL MATCHUP</div><div class="psub">actual game-master rows</div></div><div class="system-row"><span>Head-to-head games in vault</span><b>{len(x)}</b></div><div class="system-row"><span>Average total runs</span><b>{"—" if pd.isna(avg) else f"{avg:.2f}"}</b></div></div>',unsafe_allow_html=True)
        st.caption("Pitch repertoire and batter-vs-pitch-type history live in separate MLB pitch vaults; this page does not pretend those rows are joined until the research engine does that explicitly.")
    elif sport=="NFL":
        vals=[("Home Market",f'{(num(r.get("home_market_win_prob"),0) or 0)*100:.1f}%'),("Away Market",f'{(num(r.get("away_market_win_prob"),0) or 0)*100:.1f}%'),("Spread",first(r,["home_spread"],"—")),("Total",first(r,["total"],"—")),("Books",first(r,["sportsbooks"],"—")),("Survivor",first(r,["survivor_grade"],"—"))]
        st.markdown('<div class="kpi-row">'+''.join(f'<div class="kpi"><div class="lbl">{esc(a)}</div><div class="val">{esc(b)}</div></div>' for a,b in vals)+'</div>',unsafe_allow_html=True)
        hist=load("nfl_history")
        if not hist.empty:
            # history uses abbreviations; translate current full names where possible
            rev={k:v.upper() for k,v in NFL_ABBR.items()}; aa=rev.get(away,away); hh=rev.get(home,home)
            h2h=hist[((hist["away_team"].astype(str).eq(aa))&(hist["home_team"].astype(str).eq(hh)))|((hist["away_team"].astype(str).eq(hh))&(hist["home_team"].astype(str).eq(aa)))].copy()
            total_now=num(r.get("total")); similar=hist.copy()
            if total_now is not None and "total_line" in similar.columns:
                tl=pd.to_numeric(similar["total_line"],errors="coerce"); similar=similar[tl.between(total_now-3,total_now+3)]
            c1,c2=st.columns(2)
            with c1: st.metric("H2H games in vault",len(h2h))
            with c2: st.metric("Similar total-line games",len(similar))
            cols=[c for c in ["gameday","away_team","away_score","home_team","home_score","spread_line","total_line","roof","surface","temp","wind","stadium","home_ats_result","ou_result"] if c in h2h.columns]
            if not h2h.empty: st.dataframe(h2h.sort_values("gameday",ascending=False)[cols].head(20),hide_index=True,width="stretch")
        st.info("Current NFL forecast ingestion is still separate. Historical weather/stadium data is real; a current-game weather card appears only after the forecast collector populates it.")
    else:
        vals=[("Research Lean",first(r,["research_lean"],"—")),("Confidence",first(r,["research_confidence"],"—")),("Home Win Comp",f'{(num(r.get("comp_home_win_prob"),0) or 0)*100:.1f}%'),("Proj Margin",round(num(r.get("comp_projected_margin"),0) or 0,1)),("Market Total",first(r,["Total"],"—")),("Proj Total",round(num(r.get("comp_projected_total"),0) or 0,1))]
        st.markdown('<div class="kpi-row">'+''.join(f'<div class="kpi"><div class="lbl">{esc(a)}</div><div class="val">{esc(b)}</div></div>' for a,b in vals)+'</div>',unsafe_allow_html=True)
        hist=load("cfb_history")
        if not hist.empty and "away_team" in hist.columns and "home_team" in hist.columns:
            x=hist[((hist["away_team"].astype(str).eq(away))&(hist["home_team"].astype(str).eq(home)))|((hist["away_team"].astype(str).eq(home))&(hist["home_team"].astype(str).eq(away)))].copy()
            st.metric("Historical H2H rows",len(x))
        st.caption("College football remains team/game research only. No college player props are introduced here.")

def prizepicks_page(sport=None):
    css()
    topbar("🟣 PrizePicks", f"Cache updated {age('pp')}")
    d = load("pp")
    if d.empty:
        st.info("PrizePicks Standard cache is unavailable.")
        return
    if "odds_type" in d.columns:
        d = d[d["odds_type"].astype(str).str.lower().eq("standard")]
    if "is_promo" in d.columns:
        d = d[~d["is_promo"].astype(str).str.lower().isin(["true", "1"])]
    d = d[d.get("league", pd.Series(index=d.index, dtype=str)).astype(str).str.upper().isin(["NFL", "MLB"])]
    if sport:
        d = d[d["league"].astype(str).str.upper().eq(sport)]
    d = d.copy()
    if "start_time" in d.columns:
        dt = pd.to_datetime(d["start_time"], errors="coerce", utc=True)
        now = pd.Timestamp.now(tz="UTC")
        d = d[dt.isna() | (dt >= now - pd.Timedelta(hours=1))]
    title = (sport + " PrizePicks") if sport else "PrizePicks Command Center"
    st.markdown(
        f'<div class="sport-banner"><div><div class="sport-name">{esc(title)}</div><div class="sport-sub">Standard lines only · promos filtered · player-first display</div></div><div class="source-pill">{len(d):,} LINES</div></div>',
        unsafe_allow_html=True,
    )
    if d.empty:
        st.info("No upcoming standard PrizePicks lines are cached for this view.")
        return
    c1, c2 = st.columns([1, 2])
    with c1:
        choices = ["ALL", "NFL", "MLB"]
        league = st.selectbox("Sport", choices, index=0 if not sport else choices.index(sport), disabled=bool(sport))
    with c2:
        q = st.text_input("Search player or stat", placeholder="Player name, passing yards, strikeouts...")
    if not sport and league != "ALL":
        d = d[d["league"].astype(str).str.upper().eq(league)]
    if q.strip():
        mask = d["player"].astype(str).str.contains(q, case=False, na=False) | d["stat"].astype(str).str.contains(q, case=False, na=False)
        d = d[mask]
    player_count = d["player"].nunique() if "player" in d.columns else 0
    team_count = d["team"].nunique() if "team" in d.columns else 0
    m1, m2, m3 = st.columns(3)
    m1.metric("Visible Lines", len(d))
    m2.metric("Players", player_count)
    m3.metric("Teams", team_count)
    sort_cols = [c for c in ["start_time", "rank"] if c in d.columns]
    if sort_cols:
        d = d.sort_values(sort_cols)
    d = d.head(60)
    sig_index = _prop_signal_index(sport)
    matched_research = 0
    cards = []
    for _, r in d.iterrows():
        sp = str(r.get("league", "")).upper()
        team = str(r.get("team", "—"))
        code = team.lower().replace("cws", "chw")
        league_name = "nfl" if sp == "NFL" else "mlb"
        logo = f'https://a.espncdn.com/i/teamlogos/{league_name}/500/{code}.png' if team not in ("", "—", "nan") and "/" not in team else ""
        img = f'<img src="{logo}" alt="" loading="lazy">' if logo else ''
        start = fmt_time(r.get("start_time"))
        market_key = _prop_market_from_pp(r.get("stat", ""))
        sig = sig_index.get((_norm_name(r.get("player", "")), market_key)) if market_key else None
        research = ''
        if sig:
            matched_research += 1
            pp_line = num(r.get("line")); med = num(sig.get("market_median")); gap = None if pp_line is None or med is None else pp_line-med
            research = (f'<div class="pp-research"><span>SPORTSBOOK MEDIAN <b>{esc(sig.get("market_median","—"))}</b></span>'
                        f'<span>GAP <b>{"—" if gap is None else f"{gap:+.1f}"}</b></span>'
                        f'<span>{esc(sig.get("book_count","—"))} BOOKS</span>'
                        f'<span>AGREE {esc(sig.get("book_agreement_pct","—"))}%</span>'
                        f'<span class="good">{esc(sig.get("market_direction","—"))} · SCORE {esc(sig.get("hulk_prop_score","—"))}</span>'
                        f'<span>{esc(sig.get("signal","—"))}</span></div>')
        cards.append(
            f'<div class="pp-player-card"><div class="pp-player-top">{img}<div><div class="pp-player">{esc(r.get("player", "—"))}</div>'
            f'<div class="pp-team">{esc(sp)} · {esc(team)} · {esc(r.get("position", ""))}</div></div></div>'
            f'<div class="pp-stat">{esc(r.get("stat", "—"))}</div><div class="pp-line-big">{esc(r.get("line", "—"))}</div>'
            f'{research}<div class="pp-start">{esc(start)} ET · {esc(r.get("description", ""))}</div></div>'
        )
    st.markdown(f'<div class="panel"><div class="phead"><div class="ptitle purple">PRIZEPICKS × HULK RESEARCH</div><div class="psub">{matched_research} visible lines matched to sportsbook consensus</div></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="pp-card-grid">' + ''.join(cards) + '</div>', unsafe_allow_html=True)
    st.caption("Hulk Prop Score is a market-quality research score, not a calibrated win probability. Player photos will be added only from a reliable player-image source; team-logo fallback remains safe.")


def cfb_totals_page():
    css()
    topbar("🏟️ College Football", f"Cache updated {age('cfb')}")
    d = load("cfb")
    if d.empty:
        st.info("CFB board unavailable.")
        return
    rows = []
    for _, r in d.iterrows():
        total = num(r.get("Total"))
        proj = num(r.get("comp_projected_total"))
        start = first(r, ["start", "start_dt"], None)
        if total is None or proj is None:
            continue
        edge = proj - total
        rows.append({
            "Start": fmt_time(start), "Away": first(r, ["away"], "—"), "Home": first(r, ["home"], "—"),
            "Market O/U": total, "Projected Total": round(proj, 1), "Edge": round(edge, 1),
            "Research Lean": "OVER" if edge >= 3 else "UNDER" if edge <= -3 else "PASS",
            "Confidence": first(r, ["research_confidence"], "—"), "Comp Samples": first(r, ["comp_samples"], "—"),
        })
    x = pd.DataFrame(rows)
    st.markdown('<div class="sport-banner"><div><div class="sport-name">CFB Over / Unders</div><div class="sport-sub">Historical-comp total research. No college player props.</div></div><div class="source-pill">RESEARCH ONLY</div></div>', unsafe_allow_html=True)
    if x.empty:
        st.info("No CFB totals have both a market total and comparable-game projection in the current cache.")
        return
    x = x.loc[x["Edge"].abs().sort_values(ascending=False).index]
    st.dataframe(x, width="stretch", hide_index=True, height=720)
    st.caption("These are research leans from comparable-game total projections, not a validated official CFB totals betting model.")


def nfl_weather_page():
    css()
    topbar("🏈 NFL", "Historical weather vault ready · live forecast collector pending")
    hist = pd.DataFrame()
    try:
        hist = pd.read_csv(P["nfl_history"], low_memory=False)
    except Exception:
        pass
    st.markdown('<div class="sport-banner"><div><div class="sport-name">NFL Weather</div><div class="sport-sub">Weather belongs inside matchup, props, totals and Survivor context — not as a decorative forecast page.</div></div><div class="source-pill">NFL WEATHER</div></div>', unsafe_allow_html=True)
    cols = [c for c in ["season", "week", "away_team", "home_team", "stadium", "roof", "surface", "temp", "wind", "total", "home_spread"] if c in hist.columns]
    if cols:
        st.markdown('<div class="panel"><div class="phead"><div class="ptitle">HISTORICAL WEATHER + STADIUM CONTEXT</div><div class="psub">existing NFL vault</div></div></div>', unsafe_allow_html=True)
        show = hist[cols].tail(250)
        sort_cols = [c for c in ["season", "week"] if c in show.columns]
        if sort_cols:
            show = show.sort_values(sort_cols, ascending=False)
        st.dataframe(show, width="stretch", hide_index=True, height=560)
    st.info("Current-game forecast ingestion is the next data collector: temperature, wind, precipitation and roof status will be cached before kickoff and reused by Best Bets, Player Props, Survivor and matchup research. No page-view weather API calls will be used.")


def survivor_page():
    css()
    topbar("🏈 NFL", "Multi-entry Survivor manager")
    data = survivor_data()
    entries = data.get("entries", {})
    st.markdown('<div class="sport-banner"><div><div class="sport-name">Survivor / Suicide Pool</div><div class="sport-sub">Every entry keeps its own used teams, current pick and future plan.</div></div><div class="source-pill">MULTI-ENTRY</div></div>', unsafe_allow_html=True)
    if entries:
        names = list(entries)
        active = data.get("active") if data.get("active") in names else names[0]
        pick = st.selectbox("Active Entry", names, index=names.index(active))
        if pick != data.get("active"):
            data["active"] = pick
            _save_json(P["survivor_entries"], data)
        e = entries[pick]
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            status = st.selectbox("Status", ["ALIVE", "ELIMINATED"], index=0 if e.get("status", "ALIVE") == "ALIVE" else 1, key=f"status_{pick}")
        with c2:
            st.metric("Teams Used", len(e.get("used_teams", [])))
        with c3:
            st.metric("Future Picks", len(e.get("future_picks", {})))
        with c4:
            st.metric("Pool", e.get("pool") or "—")
        teams = sorted(NFL_ABBR.keys())
        used = st.multiselect("Teams already used", teams, default=[x for x in e.get("used_teams", []) if x in NFL_ABBR], key=f"used_{pick}")
        choices = ["—"] + teams
        saved_current = e.get("current_pick") if e.get("current_pick") in teams else "—"
        saved_backup = e.get("backup_pick") if e.get("backup_pick") in teams else "—"
        c1, c2 = st.columns(2)
        with c1:
            current = st.selectbox("This week's pick", choices, index=choices.index(saved_current), key=f"cur_{pick}")
        with c2:
            backup = st.selectbox("Backup pick", choices, index=choices.index(saved_backup), key=f"bak_{pick}")
        if current != "—" and current in used:
            st.markdown("<div class='survivor-warning'>⚠️ This week's pick is already in this entry's used-team list.</div>", unsafe_allow_html=True)
        if current != "—" and backup == current:
            st.markdown('<div class="survivor-warning">⚠️ Backup pick must be different from the primary pick.</div>', unsafe_allow_html=True)
        plan = st.text_area("Future pick plan", value="\n".join(f"Week {k}: {v}" for k, v in sorted(e.get("future_picks", {}).items(), key=lambda kv: str(kv[0]))), placeholder="Week 2: Buffalo Bills\nWeek 3: Kansas City Chiefs")
        if st.button("Save Survivor Entry", type="primary"):
            fp = {}
            for line in plan.splitlines():
                m = re.match(r"\s*Week\s*(\d+)\s*:\s*(.+)\s*$", line, re.I)
                if m:
                    fp[m.group(1)] = m.group(2)
            e.update({"status": status, "used_teams": used, "current_pick": None if current == "—" else current, "backup_pick": None if backup == "—" else backup, "future_picks": fp})
            entries[pick] = e
            data["entries"] = entries
            _save_json(P["survivor_entries"], data)
            st.success("Entry saved.")
    with st.expander("➕ Add Survivor Entry", expanded=not bool(entries)):
        name = st.text_input("Entry name", placeholder="Office Pool - Entry 1")
        pool = st.text_input("Pool name", placeholder="Office Survivor")
        if st.button("Create Entry", disabled=not bool(name.strip())):
            entries[name.strip()] = {"pool": pool.strip(), "status": "ALIVE", "used_teams": [], "current_pick": None, "backup_pick": None, "future_picks": {}, "history": []}
            data["entries"] = entries
            data["active"] = name.strip()
            _save_json(P["survivor_entries"], data)
            st.rerun()
    board = pd.DataFrame()
    try:
        board = pd.read_csv(P["nfl_survivor"], low_memory=False) if P["nfl_survivor"].exists() else pd.DataFrame()
    except Exception:
        pass
    if not board.empty:
        st.subheader("Hulk Survivor Board")
        st.dataframe(board, width="stretch", hide_index=True, height=430)
    st.caption("Future-value optimization will rank this week's safety against the value of saving strong teams for later weeks.")


def top300_page():
    css()
    topbar("🏆 Fantasy", "Top 300 draft board")
    d = fdf()
    if d.empty:
        st.info("Fantasy board unavailable.")
        return
    rank = next((c for c in ["hulk_v2_rank", "overall_rank", "hulk_rank", "rank"] if c in d.columns), None)
    if rank:
        d[rank] = pd.to_numeric(d[rank], errors="coerce")
        d = d.sort_values(rank)
    cols = [c for c in [rank, "full_name", "position", "team", "hulk_v2_tier", "consensus_adp", "espn_adp", "yahoo_adp", "sleeper_ppr_adp", "cbs_adp", "hulk_value_vs_consensus", "draft_action", "proj_ppr_points"] if c and c in d.columns]
    st.markdown('<div class="sport-banner"><div><div class="sport-name">Fantasy Top 300 Cheat Sheet</div><div class="sport-sub">Overall board + positional value + platform ADP in the dense draft-sheet style.</div></div><div class="source-pill">TOP 300</div></div>', unsafe_allow_html=True)
    st.dataframe(d[cols].head(300), width="stretch", hide_index=True, height=820)


def feature(mode,page):
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
    return False
