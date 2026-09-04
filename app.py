from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd
import textwrap
import numpy as np
import streamlit as st
from hulk_final_ui import nav as hulk_nav, feature as render_hulk_feature_page, dashboard as render_dashboard_boost, css as inject_hulk_final_css
from dotenv import load_dotenv
from prop_intelligence.hulk_prop_ui import render_prop_intelligence


# ============================================================
# SPORTS HULK V2.1
# Functional sportsbook-style rebuild
# ============================================================

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

MLB = ROOT / "baseball_vault" / "derived"
MLB_HISTORY = ROOT / "baseball_vault" / "history"
MLB_LATEST = ROOT / "baseball_vault" / "latest"
CFB = ROOT / "college_vault" / "derived"
NFL = ROOT / "data_vault" / "derived"

st.set_page_config(
    page_title="Sports Hulk",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>
:root{
    --green:#45ff2a;
    --green2:#1fc91a;
    --purple:#a64dff;
    --blue:#40a7ff;
    --gold:#ffc83d;
    --red:#ff4e57;
    --bg:#050807;
    --panel:#0c1210;
    --panel2:#101814;
    --panel3:#141d18;
    --border:rgba(255,255,255,.075);
    --gborder:rgba(69,255,42,.25);
    --text:#f6f8f6;
    --muted:#849188;
}

html,body,[class*="css"]{
    font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}

.stApp{
    background:
      radial-gradient(circle at 35% -10%,rgba(69,255,42,.055),transparent 28%),
      #050807;
}

.block-container{
    max-width:1600px;
    padding-top:.7rem;
    padding-bottom:3rem;
}

header,#MainMenu,footer{
    visibility:hidden;
}

[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#070b09,#080d0a);
    border-right:1px solid rgba(255,255,255,.065);
}

[data-testid="stSidebar"] .block-container{
    padding-top:1rem;
}

.brand{
    padding:4px 0 18px;
}
.brand-main{
    color:#fff;
    font-size:27px;
    font-weight:950;
    letter-spacing:-1px;
}
.brand-main span{color:var(--green);}
.brand-sub{
    color:#9ca69f;
    font-size:10px;
    letter-spacing:1.9px;
    font-weight:800;
    text-transform:uppercase;
}

.mode-label{
    color:#6f7c73;
    font-size:9px;
    text-transform:uppercase;
    letter-spacing:1.5px;
    font-weight:900;
    margin-bottom:5px;
}

.page-title{
    font-size:29px;
    font-weight:950;
    letter-spacing:-.7px;
    color:white;
}
.page-sub{
    color:#87948c;
    font-size:12px;
    margin-top:3px;
}

.kicker{
    color:var(--green);
    font-size:9px;
    font-weight:900;
    letter-spacing:1.6px;
    text-transform:uppercase;
    margin-bottom:3px;
}

.topbar{
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:20px;
    border-bottom:1px solid rgba(255,255,255,.06);
    padding:5px 0 12px 0;
    margin-bottom:12px;
}

.status{
    font-size:10px;
    color:#89968e;
}
.live{
    display:inline-block;
    width:7px;
    height:7px;
    border-radius:50%;
    background:var(--green);
    margin-right:5px;
    box-shadow:0 0 9px rgba(69,255,42,.9);
}

.kpi{
    min-height:100px;
    border:1px solid var(--border);
    border-radius:12px;
    background:linear-gradient(180deg,#101713,#0b100d);
    padding:14px 15px;
}
.kpi-label{
    color:#78857d;
    font-size:9px;
    font-weight:850;
    letter-spacing:1px;
    text-transform:uppercase;
}
.kpi-value{
    font-size:25px;
    font-weight:950;
    margin-top:5px;
    color:white;
}
.kpi-value.green{color:var(--green);}
.kpi-value.purple{color:#c07aff;}
.kpi-value.gold{color:#ffd45b;}
.kpi-sub{
    color:#76837b;
    font-size:10px;
    margin-top:3px;
}

.panel{
    border:1px solid var(--border);
    border-radius:13px;
    background:linear-gradient(180deg,#0e1511,#090e0b);
    padding:15px;
    margin-bottom:11px;
}
.panel-title{
    font-weight:900;
    color:#fff;
    font-size:14px;
    margin-bottom:3px;
}
.panel-sub{
    color:#718078;
    font-size:10px;
}

.section{
    color:white;
    font-weight:950;
    font-size:16px;
    margin:21px 0 8px;
}
.section span{
    color:var(--green);
    font-size:10px;
    margin-left:5px;
    font-weight:800;
}

.play{
    display:grid;
    grid-template-columns:75px 2.0fr 1.25fr .75fr .9fr .9fr .9fr;
    gap:8px;
    align-items:center;
    border-bottom:1px solid rgba(255,255,255,.055);
    padding:11px 8px;
}
.play:hover{
    background:rgba(69,255,42,.018);
}

.play > div{
    min-width:0;
    overflow:hidden;
}

.play .team{
    min-width:0;
    overflow:hidden;
}
.headrow{
    color:#7b8980;
    font-size:8px;
    text-transform:uppercase;
    letter-spacing:.8px;
    font-weight:900;
    background:#111815;
    border-radius:7px;
}
.team{
    color:white;
    font-size:12px;
    font-weight:900;
}
.sub{
    color:#77857c;
    font-size:9px;
    margin-top:2px;
}
.lean{
    display:inline-flex;
    align-items:center;
    justify-content:center;
    min-width:46px;
    max-width:64px;
    white-space:nowrap;
    overflow:hidden;
    display:inline-block;
    padding:6px 10px;
    border:1px solid rgba(69,255,42,.3);
    background:rgba(69,255,42,.09);
    color:#b9ffae;
    border-radius:7px;
    font-weight:900;
    font-size:11px;
}
.conf-high{color:var(--green);font-weight:900;}
.conf-med{color:var(--gold);font-weight:900;}
.conf-low{color:#ff8b72;font-weight:900;}

.bet{
    display:inline-block;
    color:#071007;
    background:var(--green);
    border-radius:7px;
    font-size:10px;
    font-weight:950;
    padding:6px 10px;
}
.watch{
    display:inline-block;
    color:#171006;
    background:var(--gold);
    border-radius:7px;
    font-size:10px;
    font-weight:950;
    padding:6px 10px;
}
.pass{
    display:inline-block;
    color:#b0bab4;
    background:#242c27;
    border:1px solid #323d36;
    border-radius:7px;
    font-size:10px;
    font-weight:900;
    padding:6px 10px;
}
.research{
    display:inline-block;
    color:#ead8ff;
    background:#472967;
    border-radius:7px;
    font-size:9px;
    font-weight:900;
    padding:6px 9px;
}

.move-row{
    display:grid;
    grid-template-columns:1.7fr .7fr .65fr .65fr .6fr;
    gap:8px;
    border-bottom:1px solid rgba(255,255,255,.05);
    padding:9px 4px;
    font-size:10px;
}
.move-head{
    color:#6e7b73;
    font-size:8px;
    text-transform:uppercase;
    font-weight:900;
}
.good{color:var(--green);font-weight:900;}
.bad{color:var(--red);font-weight:900;}
.muted{color:var(--muted);}

.systembox{
    border:1px solid rgba(69,255,42,.14);
    background:linear-gradient(180deg,rgba(69,255,42,.04),transparent);
    border-radius:12px;
    padding:13px;
    margin-top:10px;
}
.system-title{
    color:var(--green);
    font-size:10px;
    font-weight:900;
    letter-spacing:1px;
}

[data-testid="stRadio"] > div{
    gap:7px;
}
[data-testid="stRadio"] label{
    background:#0d1410;
    border:1px solid rgba(255,255,255,.065);
    border-radius:8px;
    padding:6px 10px;
}
[data-testid="stRadio"] label:has(input:checked){
    border-color:rgba(69,255,42,.45);
    background:rgba(69,255,42,.08);
}

[data-testid="stDataFrame"]{
    border:1px solid rgba(255,255,255,.07);
    border-radius:10px;
    overflow:hidden;
}

[data-testid="stExpander"]{
    background:#0b110d;
    border:1px solid rgba(255,255,255,.065);
    border-radius:9px;
}

.stButton button{
    border:1px solid rgba(69,255,42,.28);
    border-radius:8px;
    background:#101913;
    color:#d6ffd0;
    font-weight:850;
}

.stButton button:hover{
    border-color:var(--green);
}

@media(max-width:1000px){
    .play{
        grid-template-columns:1fr 1fr 1fr;
    }
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPERS
# ============================================================

def load_csv(path):
    try:
        if Path(path).exists():
            return pd.read_csv(path)
    except Exception:
        pass
    return pd.DataFrame()


def safe(v, fallback="—"):
    try:
        if pd.isna(v):
            return fallback
    except Exception:
        pass
    if v is None:
        return fallback
    s = str(v)
    return fallback if s.lower() in ("nan","none","nat") else s


def num(v, dec=1):
    try:
        if pd.isna(v):
            return "—"
        return f"{float(v):.{dec}f}"
    except Exception:
        return "—"


def pct(v, dec=0):
    try:
        if pd.isna(v):
            return "—"
        x=float(v)
        if abs(x)<=1:
            x*=100
        return f"{x:.{dec}f}%"
    except Exception:
        return "—"


def odds(v):
    try:
        if pd.isna(v):
            return "—"
        x=int(round(float(v)))
        return f"+{x}" if x>0 else str(x)
    except Exception:
        return "—"


def spread(v):
    try:
        if pd.isna(v):
            return "—"
        return f"{float(v):+.1f}"
    except Exception:
        return "—"


def local_time(v):
    try:
        t=pd.to_datetime(v,utc=True)
        return t.tz_convert("America/New_York").strftime("%-I:%M %p")
    except Exception:
        return "—"


def local_date(v):
    try:
        t=pd.to_datetime(v,utc=True)
        return t.tz_convert("America/New_York").strftime("%a %b %-d")
    except Exception:
        return "—"


def age(path):
    try:
        t=datetime.fromtimestamp(Path(path).stat().st_mtime,tz=timezone.utc)
        d=datetime.now(timezone.utc)-t
        mins=int(d.total_seconds()/60)
        if mins<60:
            return f"{mins}m ago"
        if mins<1440:
            return f"{mins/60:.1f}h ago"
        return f"{mins/1440:.1f}d ago"
    except Exception:
        return "unknown"


def kpi(label,value,sub="",tone=""):
    st.markdown(f"""
    <div class="kpi">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value {tone}">{value}</div>
      <div class="kpi-sub">{sub}</div>
    </div>
    """,unsafe_allow_html=True)



MLB_LOGOS = {
    "Arizona Diamondbacks":"ari",
    "Athletics":"ath",
    "Atlanta Braves":"atl",
    "Baltimore Orioles":"bal",
    "Boston Red Sox":"bos",
    "Chicago Cubs":"chc",
    "Chicago White Sox":"chw",
    "Cincinnati Reds":"cin",
    "Cleveland Guardians":"cle",
    "Colorado Rockies":"col",
    "Detroit Tigers":"det",
    "Houston Astros":"hou",
    "Kansas City Royals":"kc",
    "Los Angeles Angels":"laa",
    "Los Angeles Dodgers":"lad",
    "Miami Marlins":"mia",
    "Milwaukee Brewers":"mil",
    "Minnesota Twins":"min",
    "New York Mets":"nym",
    "New York Yankees":"nyy",
    "Philadelphia Phillies":"phi",
    "Pittsburgh Pirates":"pit",
    "San Diego Padres":"sd",
    "San Francisco Giants":"sf",
    "Seattle Mariners":"sea",
    "St. Louis Cardinals":"stl",
    "Tampa Bay Rays":"tb",
    "Texas Rangers":"tex",
    "Toronto Blue Jays":"tor",
    "Washington Nationals":"wsh",
}

def mlb_logo(team):
    code = MLB_LOGOS.get(str(team))
    if not code:
        return ""
    url = f"https://a.espncdn.com/i/teamlogos/mlb/500/{code}.png"
    return (
        f'<img src="{url}" '
        f'style="width:30px;height:30px;object-fit:contain;'
        f'vertical-align:middle;margin-right:7px;">'
    )


def mlb_team_code(team):
    codes = {
        "Arizona Diamondbacks":"ARI",
        "Athletics":"ATH",
        "Atlanta Braves":"ATL",
        "Baltimore Orioles":"BAL",
        "Boston Red Sox":"BOS",
        "Chicago Cubs":"CHC",
        "Chicago White Sox":"CWS",
        "Cincinnati Reds":"CIN",
        "Cleveland Guardians":"CLE",
        "Colorado Rockies":"COL",
        "Detroit Tigers":"DET",
        "Houston Astros":"HOU",
        "Kansas City Royals":"KC",
        "Los Angeles Angels":"LAA",
        "Los Angeles Dodgers":"LAD",
        "Miami Marlins":"MIA",
        "Milwaukee Brewers":"MIL",
        "Minnesota Twins":"MIN",
        "New York Mets":"NYM",
        "New York Yankees":"NYY",
        "Philadelphia Phillies":"PHI",
        "Pittsburgh Pirates":"PIT",
        "San Diego Padres":"SD",
        "San Francisco Giants":"SF",
        "Seattle Mariners":"SEA",
        "St. Louis Cardinals":"STL",
        "Tampa Bay Rays":"TB",
        "Texas Rangers":"TEX",
        "Toronto Blue Jays":"TOR",
        "Washington Nationals":"WSH",
    }
    return codes.get(str(team), str(team)[:3].upper())


def mlb_matchup_compact_html(away, home):
    return (
        f'<div style="display:flex;flex-direction:column;gap:5px;'
        f'width:100%;max-width:115px;overflow:hidden;">'

        f'<div style="display:flex;align-items:center;gap:7px;'
        f'width:100%;min-width:0;overflow:hidden;">'
        f'{mlb_logo(away)}'
        f'<span style="font-size:12px;font-weight:950;color:white;'
        f'white-space:nowrap;">{mlb_team_code(away)}</span>'
        f'</div>'

        f'<div style="display:flex;align-items:center;gap:7px;'
        f'width:100%;min-width:0;overflow:hidden;">'
        f'{mlb_logo(home)}'
        f'<span style="font-size:12px;font-weight:950;color:white;'
        f'white-space:nowrap;">{mlb_team_code(home)}</span>'
        f'</div>'

        f'</div>'
    )

def mlb_matchup_html(away, home):
    return (
        f'<div style="display:flex;align-items:center;gap:4px;">'
        f'{mlb_logo(away)}'
        f'<span style="font-weight:900;color:white;">{safe(away)}</span>'
        f'<span style="color:#68766d;margin:0 3px;">@</span>'
        f'{mlb_logo(home)}'
        f'<span style="font-weight:900;color:white;">{safe(home)}</span>'
        f'</div>'
    )


NFL_LOGO_CODES = {
    "ARI":"ari","ATL":"atl","BAL":"bal","BUF":"buf",
    "CAR":"car","CHI":"chi","CIN":"cin","CLE":"cle",
    "DAL":"dal","DEN":"den","DET":"det","GB":"gb",
    "HOU":"hou","IND":"ind","JAX":"jax","KC":"kc",
    "LV":"lv","LAC":"lac","LAR":"lar","MIA":"mia",
    "MIN":"min","NE":"ne","NO":"no","NYG":"nyg",
    "NYJ":"nyj","PHI":"phi","PIT":"pit","SEA":"sea",
    "SF":"sf","TB":"tb","TEN":"ten","WAS":"wsh",
}


def clean_prop_name(stat):
    mapping = {
        "batting_hits": "Hits",
        "batting_totalBases": "Total Bases",
        "batting_homeRuns": "Home Runs",
        "batting_RBI": "RBIs",
        "batting_runs": "Runs",
        "batting_hits+runs+rbi": "Hits + Runs + RBI",
        "batting_basesOnBalls": "Walks",
        "batting_doubles": "Doubles",
        "batting_singles": "Singles",
        "batting_triples": "Triples",
        "pitching_strikeouts": "Strikeouts",
        "pitching_hitsAllowed": "Hits Allowed",
        "pitching_earnedRuns": "Earned Runs",
        "passing_yards": "Passing Yards",
        "passing_touchdowns": "Passing TDs",
        "passing_completions": "Completions",
        "rushing_yards": "Rushing Yards",
        "rushing_attempts": "Rush Attempts",
        "receiving_yards": "Receiving Yards",
        "receiving_receptions": "Receptions",
        "receiving_targets": "Targets",
        "receiving_touchdowns": "Receiving TDs",
    }

    s = str(stat)

    if s in mapping:
        return mapping[s]

    s = s.replace("_", " ")
    s = s.replace("batting ", "")
    s = s.replace("pitching ", "")
    s = s.replace("receiving ", "")
    s = s.replace("rushing ", "")
    s = s.replace("passing ", "")

    return s.title()


def prop_odds(v):
    if pd.isna(v):
        return "—"

    s = str(v)

    if s.endswith(".0"):
        s = s[:-2]

    return s


def prop_line(v):
    if pd.isna(v):
        return "—"

    try:
        x = float(v)

        if x.is_integer():
            return str(int(x))

        return str(x)

    except:
        return safe(v)



NFL_TEAM_NAME_TO_CODE = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LAR",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WSH",
}

NFL_CODE_ALIASES = {
    "ARZ": "ARI",
    "BLT": "BAL",
    "CLV": "CLE",
    "GB": "GB",
    "GNB": "GB",
    "HST": "HOU",
    "JAC": "JAX",
    "KAN": "KC",
    "KC": "KC",
    "LAR": "LAR",
    "LA": "LAR",
    "LAC": "LAC",
    "LV": "LV",
    "LVR": "LV",
    "NE": "NE",
    "NWE": "NE",
    "NO": "NO",
    "NOR": "NO",
    "SF": "SF",
    "SFO": "SF",
    "TB": "TB",
    "TAM": "TB",
    "TEN": "TEN",
    "WSH": "WSH",
    "WAS": "WSH",
}

def nfl_team_code(team):
    value = str(team or "").strip()

    if not value:
        return ""

    if value in NFL_TEAM_NAME_TO_CODE:
        return NFL_TEAM_NAME_TO_CODE[value]

    upper = value.upper()

    if upper in NFL_CODE_ALIASES:
        return NFL_CODE_ALIASES[upper]

    if upper in NFL_LOGO_CODES:
        return upper

    return upper


def nfl_team_display(team, size=28, show_name=True):
    value = str(team or "").strip()

    if not value:
        return "—"

    code = nfl_team_code(value)

    logo = nfl_logo(code, size)

    if value in NFL_TEAM_NAME_TO_CODE:
        label = value
    else:
        label = code or value

    if show_name:
        return (
            f'<span style="display:inline-flex;'
            f'align-items:center;gap:7px;">'
            f'{logo}'
            f'<span>{safe(label)}</span>'
            f'</span>'
        )

    return logo


def nfl_matchup_html(away, home, size=27):
    return (
        f'{nfl_team_display(away, size)}'
        f'<span style="margin:0 9px;opacity:.55;">@</span>'
        f'{nfl_team_display(home, size)}'
    )


def nfl_logo(team, size=28):
    code = NFL_LOGO_CODES.get(str(team).upper())
    if not code:
        return ""
    url = f"https://a.espncdn.com/i/teamlogos/nfl/500/{code}.png"
    return (
        f'<img src="{url}" '
        f'style="width:{size}px;height:{size}px;object-fit:contain;'
        f'vertical-align:middle;flex-shrink:0;">'
    )

def fantasy_player_html(name, team, pos):
    return (
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'{nfl_logo(team, 27)}'
        f'<div>'
        f'<div style="font-weight:900;color:white;font-size:12px;">{safe(name)}</div>'
        f'<div class="sub">{safe(team)} • {safe(pos)}</div>'
        f'</div></div>'
    )

def decision_html(v):
    v=safe(v,"PASS").upper()
    if v=="BET":
        return '<span class="bet">BET</span>'
    if v=="WATCH":
        return '<span class="watch">WATCH</span>'
    return '<span class="pass">PASS</span>'



def mlb_display_confidence(r):
    score = 0

    # Official decision contributes, but does not control confidence alone.
    decision = str(r.get("decision", "")).upper()
    if decision == "BET":
        score += 3
    elif decision == "WATCH":
        score += 1

    # Historical comp quality.
    grade = str(r.get("comp_quality_grade", "")).upper()
    if grade == "A":
        score += 3
    elif grade == "B":
        score += 2
    elif grade == "C":
        score += 1

    # Historical bucket evidence.
    try:
        acc = float(r.get("comp_bucket_hist_accuracy"))
        samples = float(r.get("comp_bucket_hist_samples"))

        if samples >= 150:
            score += 1

        if acc >= 0.60:
            score += 2
        elif acc >= 0.55:
            score += 1
        elif acc < 0.50:
            score -= 1
    except Exception:
        pass

    # Market depth.
    try:
        books = float(r.get("h2h_book_count"))
        if books >= 8:
            score += 2
        elif books >= 5:
            score += 1
    except Exception:
        pass

    # Data completeness.
    if str(r.get("both_starter_matchups_present")).lower() == "true":
        score += 1

    if str(r.get("bullpen_data_present")).lower() == "true":
        score += 1

    # Model / comp agreement only when actually scored.
    alignment = str(r.get("comp_alignment", "")).upper()
    if alignment in {"ALIGNED", "MATCH", "SUPPORT"}:
        score += 2
    elif alignment in {"CONFLICT", "OPPOSED"}:
        score -= 2

    if score >= 9:
        return "HIGH"
    elif score >= 5:
        return "MEDIUM"
    return "LOW"

def confidence_html(v):
    v=safe(v,"LOW").upper()
    if v=="HIGH":
        return '<span class="conf-high">HIGH</span>'
    if v=="MEDIUM":
        return '<span class="conf-med">MED</span>'
    return '<span class="conf-low">LOW</span>'


def title(kicker,title,sub):
    st.markdown(f"""
    <div class="topbar">
      <div>
        <div class="kicker">{kicker}</div>
        <div class="page-title">{title}</div>
        <div class="page-sub">{sub}</div>
      </div>
      <div class="status">
        <span class="live"></span>Sports Hulk Online
      </div>
    </div>
    """,unsafe_allow_html=True)


# ============================================================
# DATA
# ============================================================


@st.cache_data(ttl=300, show_spinner=False)
def load_live_mlb_market():
    """
    CACHE-ONLY MLB market loader.
    Page views never call an external API.
    Governed collectors update the saved files.
    """

    live_market = (
        ROOT / "mlb_live" / "derived" /
        "MLB_LIVE_MARKET.csv"
    )

    if not live_market.exists():
        return pd.DataFrame()

    df = pd.read_csv(live_market)

    if "start" in df.columns:
        df["start"] = pd.to_datetime(
            df["start"],
            errors="coerce",
            utc=True
        )

    df["live_source"] = "Oracle cached market snapshot"

    return df


mlb_live_market = load_live_mlb_market()

mlb=load_csv(MLB/"MLB_MATCHUP_BOARD_INTELLIGENCE.csv")
signals=load_csv(MLB/"MLB_MARKET_SIGNALS.csv")
cfb=load_csv(CFB/"CFB_CURRENT_BOARD.csv")
nfl=load_csv(NFL/"NFL_GAME_MASTER.csv")

FANTASY = ROOT / "fantasy_vault" / "derived"

FANTASY_V2_FILE = (
    ROOT
    / "fantasy_live"
    / "derived"
    / "FANTASY_HULK_V2_ADP_BOARD.csv"
)

fantasy = load_csv(FANTASY_V2_FILE)

# ------------------------------------------------------------
# Fantasy V2 compatibility layer
#
# Keep existing Fantasy UI working while it is upgraded page
# by page to the new Hulk V2 + multi-source ADP system.
# ------------------------------------------------------------

if not fantasy.empty:

    if "hulk_v2_rank" in fantasy.columns:
        fantasy["overall_rank"] = pd.to_numeric(
            fantasy["hulk_v2_rank"],
            errors="coerce"
        )

    if "hulk_v2_position_rank" in fantasy.columns:
        fantasy["position_rank"] = pd.to_numeric(
            fantasy["hulk_v2_position_rank"],
            errors="coerce"
        )

    if "hulk_v2_tier" in fantasy.columns:
        fantasy["tier"] = pd.to_numeric(
            fantasy["hulk_v2_tier"],
            errors="coerce"
        )

    if "hulk_v2_score" in fantasy.columns:
        fantasy["hulk_score"] = pd.to_numeric(
            fantasy["hulk_v2_score"],
            errors="coerce"
        )

    if "current_team" in fantasy.columns:
        fantasy["team"] = (
            fantasy["current_team"]
            .fillna(fantasy.get("team"))
        )

    if "consensus_adp" in fantasy.columns:
        fantasy["adp"] = pd.to_numeric(
            fantasy["consensus_adp"],
            errors="coerce"
        )

    if "hulk_value_vs_consensus" in fantasy.columns:
        fantasy["value_vs_adp"] = pd.to_numeric(
            fantasy["hulk_value_vs_consensus"],
            errors="coerce"
        )
mlb_results=load_csv(MLB_HISTORY/"MLB_GRADED_PREDICTIONS.csv")


# ============================================================
# NFL PLAYER PROP DISPLAY LABELS
# ============================================================

NFL_PROP_LABELS = {
    "rushing_yards": "Rushing Yards",
    "receiving_yards": "Receiving Yards",
    "rushing+receiving_yards": "Rushing + Receiving Yards",
    "passing_yards": "Passing Yards",
    "passing+rushing_yards": "Passing + Rushing Yards",
    "receiving_receptions": "Receptions",
    "receiving_longestReception": "Longest Reception",
    "rushing_attempts": "Rushing Attempts",
    "rushing_longestRush": "Longest Rush",
    "passing_attempts": "Passing Attempts",
    "passing_completions": "Passing Completions",
    "passing_longestCompletion": "Longest Completion",
    "passing_touchdowns": "Passing Touchdowns",
    "passing_interceptions": "Passing Interceptions",
    "rushing_touchdowns": "Rushing Touchdowns",
    "touchdowns": "Anytime Touchdown",
    "defense_sacks": "Sacks",
    "defense_soloTackles": "Solo Tackles",
    "defense_combinedTackles": "Combined Tackles",
    "defense_assistedTackles": "Assisted Tackles",
    "defense_interceptions": "Defensive Interceptions",
    "kicking_totalPoints": "Kicking Points",
    "fieldGoals_made": "Field Goals Made",
    "extraPoints_kicksMade": "Extra Points Made",
    "fantasyScore": "Fantasy Score",
}

def nfl_prop_label(x):
    return NFL_PROP_LABELS.get(
        str(x),
        clean_prop_name(x)
    )


MLB_PROPS_FILE = ROOT / "props_live" / "mlb" / "derived" / "MLB_PLAYER_PROPS.csv"
NFL_PROPS_FILE = ROOT / "props_live" / "nfl" / "derived" / "NFL_PLAYER_PROPS.csv"

NFL_CURRENT_WEEK_FILE = (
    ROOT
    / "nfl_live"
    / "derived"
    / "NFL_CURRENT_WEEK.csv"
)

nfl_current_week = load_csv(
    NFL_CURRENT_WEEK_FILE
)

NFL_SURVIVOR_FILE = (
    ROOT
    / "nfl_live"
    / "derived"
    / "NFL_SURVIVOR_BOARD.csv"
)

nfl_survivor = load_csv(
    NFL_SURVIVOR_FILE
)

mlb_props = load_csv(MLB_PROPS_FILE)
nfl_props = load_csv(NFL_PROPS_FILE)


if not mlb.empty:
    mlb["_dt"]=pd.to_datetime(mlb["gameDate"],errors="coerce",utc=True)

if not cfb.empty:
    cfb["_dt"]=pd.to_datetime(
        cfb["start_dt"] if "start_dt" in cfb.columns else cfb["start"],
        errors="coerce",
        utc=True
    )



# ============================================================
# SPORTS HULK GLOBAL RESPONSIVE LAYER
# ============================================================

st.markdown("""
<style>

/* ---------------------------------------------------------
   GLOBAL SAFETY
   --------------------------------------------------------- */

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.block-container {
    max-width: 100%;
    overflow-x: hidden;
}

* {
    box-sizing: border-box;
}

.panel,
.systembox,
.section {
    max-width: 100%;
}

.panel-title,
.panel-sub,
.team,
.sub,
.lean {
    overflow-wrap: anywhere;
    word-break: normal;
}


/* ---------------------------------------------------------
   STREAMLIT COLUMN WRAPPING
   --------------------------------------------------------- */

div[data-testid="stHorizontalBlock"] {
    width: 100%;
    align-items: stretch;
}

div[data-testid="column"] {
    min-width: 0;
}


/* ---------------------------------------------------------
   INPUTS / FILTERS
   --------------------------------------------------------- */

div[data-baseweb="select"],
div[data-testid="stSelectbox"],
div[data-testid="stMultiSelect"],
div[data-testid="stNumberInput"],
div[data-testid="stRadio"] {
    max-width: 100%;
}

div[data-testid="stRadio"] > div {
    flex-wrap: wrap !important;
}


/* ---------------------------------------------------------
   TABLES
   --------------------------------------------------------- */

div[data-testid="stDataFrame"],
div[data-testid="stTable"] {
    max-width: 100%;
    overflow-x: auto !important;
}


/* ---------------------------------------------------------
   IMAGES / TEAM LOGOS
   --------------------------------------------------------- */

.panel img {
    max-width: 42px;
    height: auto;
    object-fit: contain;
    flex-shrink: 0;
}



/* ---------------------------------------------------------
   SECTION SELECTOR READABILITY
   --------------------------------------------------------- */

div[data-testid="stRadio"] label {
    color: #f3f5f4 !important;
    opacity: 1 !important;
    font-weight: 700 !important;
}

div[data-testid="stRadio"] label p,
div[data-testid="stRadio"] label span {
    color: #f3f5f4 !important;
    opacity: 1 !important;
}

/* selected section stays bright */
div[data-testid="stRadio"] label:has(input:checked) p,
div[data-testid="stRadio"] label:has(input:checked) span {
    color: #ffffff !important;
    font-weight: 800 !important;
}

/* =========================================================
   TABLET
   ========================================================= */

@media (max-width: 900px) {

    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1rem !important;
    }

    /*
       Any inline Hulk card grid that currently has
       3, 4, 5, 6, 7 or 8 fixed columns becomes 2 columns.
    */
    .panel > div[style*="display:grid"],
    .panel div[style*="display: grid"] {
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 12px !important;
    }

    .panel > div[style*="display:flex"],
    .panel div[style*="display: flex"] {
        flex-wrap: wrap !important;
        gap: 10px !important;
    }

    /* Streamlit KPI/filter rows */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }

    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 calc(50% - 12px) !important;
        width: calc(50% - 12px) !important;
        min-width: 220px !important;
    }

    .panel {
        padding: 14px !important;
    }

}


/* =========================================================
   PHONE
   ========================================================= */

@media (max-width: 640px) {

    .block-container {
        padding-left: .65rem !important;
        padding-right: .65rem !important;
        padding-top: .65rem !important;
    }

    /*
       Every custom card becomes a clean single-column card.
       This fixes NFL props, Survivor, Fantasy rankings,
       MLB cards, CFB cards, etc.
    */
    .panel > div[style*="display:grid"],
    .panel div[style*="display: grid"] {
        grid-template-columns: minmax(0, 1fr) !important;
        width: 100% !important;
        gap: 10px !important;
    }

    .panel > div[style*="display:flex"],
    .panel div[style*="display: flex"] {
        flex-direction: column !important;
        align-items: flex-start !important;
        width: 100% !important;
        gap: 8px !important;
    }

    /* Streamlit columns become full width */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: column !important;
        gap: .55rem !important;
    }

    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 100% !important;
        width: 100% !important;
        min-width: 0 !important;
    }

    /* Full-width controls */
    div[data-baseweb="select"],
    div[data-testid="stSelectbox"],
    div[data-testid="stMultiSelect"],
    div[data-testid="stNumberInput"],
    div[data-testid="stTextInput"] {
        width: 100% !important;
    }

    /* Radio options wrap cleanly */
    div[data-testid="stRadio"] > div {
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 6px !important;
    }

    .panel {
        padding: 12px !important;
        margin-bottom: 10px !important;
        border-radius: 12px !important;
    }

    .panel-title {
        font-size: 17px !important;
        line-height: 1.25 !important;
    }

    .panel-sub {
        font-size: 12px !important;
        line-height: 1.35 !important;
    }

    .team {
        font-size: 15px !important;
    }

    .sub {
        font-size: 10px !important;
        letter-spacing: .35px !important;
    }

    .section {
        font-size: 15px !important;
        line-height: 1.25 !important;
        margin-top: 18px !important;
        margin-bottom: 8px !important;
    }

    .panel img {
        max-width: 30px !important;
        max-height: 30px !important;
    }

    /* Prevent long sportsbook/player/team text overflow */
    .panel span,
    .panel div {
        max-width: 100%;
    }

    /* Buttons become thumb-friendly */
    .stButton button,
    .stDownloadButton button {
        width: 100% !important;
        min-height: 42px !important;
    }

}


/* =========================================================
   VERY SMALL PHONES
   ========================================================= */

@media (max-width: 390px) {

    .block-container {
        padding-left: .45rem !important;
        padding-right: .45rem !important;
    }

    .panel {
        padding: 10px !important;
    }

    .panel-title {
        font-size: 16px !important;
    }

    .team {
        font-size: 14px !important;
    }

    .panel img {
        max-width: 26px !important;
        max-height: 26px !important;
    }

}

</style>
""", unsafe_allow_html=True)


# ============================================================
# BRAND / TOP SECTION SWITCH
# ============================================================

st.sidebar.markdown("""
<div class="brand">
  <div class="brand-main">SPORTS <span>HULK</span></div>
  <div class="brand-sub">Sports Intelligence</div>
</div>
""",unsafe_allow_html=True)

st.markdown('<div class="mode-label">SECTION</div>',unsafe_allow_html=True)

section_mode = st.radio(
    "Section",
    [
        "🎯 Betting",
        "⚾ MLB",
        "🏈 NFL",
        "🏟️ College Football",
        "🏀 NBA · Soon",
        "🏀 College Basketball · Soon",
        "🏒 NHL · Soon",
        "🟣 PrizePicks",
        "🏆 Fantasy",
    ],
    horizontal=True,
    label_visibility="collapsed",
    key="top_mode"
)

# Preserve the old variable name so the rest of the app
# can keep working while we transition each section.
mode = section_mode


# ============================================================
# CONTEXTUAL SIDEBAR
# ============================================================

if mode == "🎯 Betting":
    menu = [
        "Command Center",
        "Today's Slate",
        "Best Bets",
        "Parlay Center",
        "Game Research",
        "Bet Tracker",
        "Performance Lab",
        "Line Movement",
        "Results",
        "Research",
        "Historical Explorer",
    ]

elif mode == "⚾ MLB":
    menu = [
        "MLB Best Bets",
        "MLB Player Props",
        "MLB Parlays",
        "MLB Matchups",
        "Starting Pitching",
        "Weather",
        "MLB Market",
        "MLB Results",
    ]

elif mode == "🏈 NFL":
    menu = [
        "NFL Command Center",
        "NFL Best Bets",
        "NFL Player Props",
        "NFL Parlays",
        "NFL Matchups",
        "Survivor",
        "NFL Weather",
        "NFL Research",
    ]

elif mode == "🏟️ College Football":
    menu = [
        "CFB Command Center",
        "CFB Best Bets",
        "CFB Over / Unders",
        "CFB Parlays",
        "CFB Matchups",
        "CFB Research",
    ]

elif mode == "🟣 PrizePicks":
    menu = [
        "PrizePicks Dashboard",
        "NFL PrizePicks",
        "MLB PrizePicks",
    ]

elif mode == "🏆 Fantasy":
    menu = [
        "Fantasy Dashboard",
        "League Settings",
        "My Leagues",
        "Draft Kit",
        "Top 300 Cheat Sheet",
        "Rankings",
        "Tiers",
        "ADP / Value",
        "Sleepers",
        "Waiver Wire Weekly",
        "Lineup",
        "Roster Builder",
        "Trade Finder",
        "NFL Research",
    ]

elif mode in {
    "🏀 NBA · Soon",
    "🏀 College Basketball · Soon",
    "🏒 NHL · Soon",
}:
    menu = ["Coming Soon"]

else:
    menu = ["Dashboard"]

page = hulk_nav(menu, mode)
inject_hulk_final_css()
render_dashboard_boost(mode, page)
if render_hulk_feature_page(mode, page):
    st.stop()


st.sidebar.markdown("---")

st.sidebar.markdown("""
<div class="systembox">
  <div class="system-title">SPORTS HULK</div>
  <div style="font-size:18px;font-weight:950;color:white;margin-top:6px;">SYSTEM ONLINE</div>
  <div class="sub" style="margin-top:6px;">
    Hulk Pick • Hulk Confidence • Hulk Edge
  </div>
</div>
""",unsafe_allow_html=True)

st.sidebar.caption(f"MLB refreshed {age(MLB/'MLB_MATCHUP_BOARD_INTELLIGENCE.csv')}")
st.sidebar.caption(f"CFB refreshed {age(CFB/'CFB_CURRENT_BOARD.csv')}")

# ============================================================
# SHARED SLATE BUILDER
# ============================================================

def unified_slate():

    rows=[]

    if not mlb.empty:
        for _,r in mlb.iterrows():
            rows.append({
                "Sport":"MLB",
                "Start":r.get("_dt"),
                "Time":local_time(r.get("gameDate")),
                "Matchup":f"{safe(r.get('away_team'))} @ {safe(r.get('home_team'))}",
                "Lean":safe(r.get("lean")),
                "Confidence":safe(r.get("confidence")),
                "Decision":safe(r.get("decision")),
                "WinProb":r.get("comp_home_win_rate"),
                "Spread":r.get("spreads_median_point"),
                "Total":r.get("totals_median_point"),
                "Books":r.get("h2h_book_count"),
                "Type":"Official"
            })

    if not cfb.empty:
        for _,r in cfb.iterrows():
            rows.append({
                "Sport":"CFB",
                "Start":r.get("_dt"),
                "Time":local_time(r.get("start")),
                "Matchup":f"{safe(r.get('away'))} @ {safe(r.get('home'))}",
                "Lean":safe(r.get("research_lean")),
                "Confidence":safe(r.get("research_confidence")),
                "Decision":"RESEARCH",
                "WinProb":r.get("comp_home_win_prob"),
                "Spread":r.get("Home_spread"),
                "Total":r.get("Total"),
                "Books":r.get("Odds_books"),
                "Type":"Research"
            })

    return pd.DataFrame(rows)


slate=unified_slate()


# ============================================================
# BETTING HULK
# ============================================================

if mode=="🎯 Betting" and page=="Dashboard":

    title(
        "BETTING",
        "Sports Intelligence Command Center",
        "Official plays, research signals, market movement and today's slate."
    )

    mlb_bets=0
    mlb_watch=0
    if not mlb.empty:
        mlb_bets=int((mlb["decision"].astype(str).str.upper()=="BET").sum())
        mlb_watch=int((mlb["decision"].astype(str).str.upper()=="WATCH").sum())

    cfb_high=0
    if not cfb.empty:
        cfb_high=int((cfb["research_confidence"].astype(str).str.upper()=="HIGH").sum())

    strong_signals=0
    if not signals.empty and "signal_strength" in signals.columns:
        strong_signals=int(
            signals["signal_strength"].astype(str).str.lower().isin(["strong","medium"]).sum()
        )

    cols=st.columns(6)
    with cols[0]: kpi("Official Bets",mlb_bets,"MLB decisions","green")
    with cols[1]: kpi("Watch List",mlb_watch,"MLB watch decisions","gold")
    with cols[2]: kpi("CFB Top Picks",cfb_high,"Not official bets","purple")
    with cols[3]: kpi("MLB Games",len(mlb),"Games Loaded")
    with cols[4]: kpi("CFB Games",len(cfb),"Games Loaded")
    with cols[5]: kpi("Market Signals",strong_signals,"Medium/strong")

    left,right=st.columns([1.6,.9])

    with left:
        st.markdown('<div class="section">TODAY\'S TOP PLAYS <span>RANKED BY HULK</span></div>',unsafe_allow_html=True)

        if mlb.empty:
            st.info("No MLB board available.")
        else:
            x=mlb.copy()
            dr={"BET":3,"WATCH":2,"PASS":1}
            cr={"HIGH":3,"MEDIUM":2,"LOW":1}
            x["_score"]=(
                x["decision"].astype(str).str.upper().map(dr).fillna(0)*10+
                x["confidence"].astype(str).str.upper().map(cr).fillna(0)
            )
            x=x.sort_values(["_score","_dt"],ascending=[False,True]).head(8)

            st.markdown("""
            <div class="play headrow">
              <div>TIME</div><div>MATCHUP</div><div>HULK PICK</div>
              <div>CONF</div><div>HIST. WIN %</div><div>SPORTSBOOKS</div><div>PLAY</div>
            </div>
            """,unsafe_allow_html=True)

            for _,r in x.iterrows():
                st.markdown(f"""
                <div class="play">
                  <div><div class="team">{local_time(r.get('gameDate'))}</div></div>
                  <div>
                    <div class="team">{mlb_matchup_compact_html(r.get('away_team'), r.get('home_team'))}</div>
                    <div class="sub">{safe(r.get('away_probable_pitcher'))} vs {safe(r.get('home_probable_pitcher'))}</div>
                  </div>
                  <div><span class="lean">{mlb_team_code(r.get('lean'))}</span></div>
                  <div>{confidence_html(mlb_display_confidence(r))}</div>
                  <div class="team">{pct(r.get('comp_home_win_rate'))}</div>
                  <div class="team">{safe(r.get('h2h_book_count'))}</div>
                  <div>{decision_html(r.get('decision'))}</div>
                </div>
                """,unsafe_allow_html=True)

            if mlb_bets==0:
                st.caption("Hulk currently has no official BET decisions. The board is not manufacturing one.")

    with right:
        st.markdown('<div class="section">MARKET MOVEMENT</div>',unsafe_allow_html=True)

        if signals.empty:
            st.info("No market signals available.")
        else:
            sx=signals.copy()
            if "market_signal_score" in sx.columns:
                sx=sx.sort_values("market_signal_score",ascending=False)
            sx=sx.head(7)

            st.markdown("""
            <div class="move-row move-head">
              <div>MATCHUP</div><div>MARKET</div><div>MOVERS</div><div>SHARE</div><div>SCORE</div>
            </div>
            """,unsafe_allow_html=True)

            for _,r in sx.iterrows():
                st.markdown(f"""
                <div class="move-row">
                  <div>{safe(r.get('away_team')).title()} @ {safe(r.get('home_team')).title()}</div>
                  <div>{safe(r.get('core_market')).upper()}</div>
                  <div class="good">{safe(r.get('books_moving'))}</div>
                  <div>{num(r.get('whole_market_share_pct'),0)}%</div>
                  <div class="good">{num(r.get('market_signal_score'),1)}</div>
                </div>
                """,unsafe_allow_html=True)

        st.markdown('<div class="section">HULK / MARKET AGREEMENT</div>',unsafe_allow_html=True)

        support=0
        split=0
        weak=0

        if not signals.empty and "signal_strength" in signals.columns:
            ss=signals["signal_strength"].astype(str).str.lower()
            support=int((ss=="strong").sum())
            split=int((ss=="medium").sum())
            weak=int((ss=="weak").sum())

        st.markdown(f"""
        <div class="panel">
          <div class="panel-title">Market Agreement</div>
          <div class="panel-sub">Research overlay only</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;margin-top:12px;gap:8px;">
            <div><span class="good">Strong</span><br><span class="team">{support}</span></div>
            <div><span class="conf-med">Medium</span><br><span class="team">{split}</span></div>
            <div><span class="muted">Weak</span><br><span class="team">{weak}</span></div>
            <div><span class="muted">Official Bets</span><br><span class="team">{mlb_bets}</span></div>
          </div>
        </div>
        """,unsafe_allow_html=True)

    b1,b2,b3=st.columns(3)

    with b1:
        st.markdown('<div class="section">COLLEGE FOOTBALL</div>',unsafe_allow_html=True)
        if cfb.empty:
            st.info("No CFB board.")
        else:
            cx=cfb.copy()
            cr={"HIGH":3,"MEDIUM":2,"LOW":1}
            cx["_rank"]=cx["research_confidence"].astype(str).str.upper().map(cr).fillna(0)
            now=pd.Timestamp.now(tz="UTC")
            cx=cx[cx["_dt"].isna()|(cx["_dt"]>=now-pd.Timedelta(hours=4))]
            cx=cx.sort_values(["_rank","_dt"],ascending=[False,True]).head(5)

            for _,r in cx.iterrows():
                st.markdown(f"""
                <div class="panel">
                  <div class="panel-title">{safe(r.get('away'))} @ {safe(r.get('home'))}</div>
                  <div class="panel-sub">{local_date(r.get('start'))} • {local_time(r.get('start'))}</div>
                  <div style="margin-top:8px;">
                    <span class="research">RESEARCH</span>
                    &nbsp; <span class="lean">{safe(r.get('research_lean'))}</span>
                    &nbsp; {confidence_html(r.get('research_confidence'))}
                  </div>
                  <div class="sub" style="margin-top:8px;">
                    Historical Win % {pct(r.get('comp_home_win_prob'))} •
                    Projected margin {num(r.get('comp_projected_margin'))}
                  </div>
                </div>
                """,unsafe_allow_html=True)

    with b2:
        st.markdown('<div class="section">WEATHER IMPACT</div>',unsafe_allow_html=True)

        if mlb.empty:
            st.info("No weather data.")
        else:
            wx=mlb.sort_values("_dt").head(6)
            for _,r in wx.iterrows():
                wind=num(r.get("wind_mph"))
                temp=num(r.get("temperature_f"),0)
                flag=safe(r.get("run_environment_flag"))
                st.markdown(f"""
                <div class="panel">
                  <div class="panel-title">{safe(r.get('away_team'))} @ {safe(r.get('home_team'))}</div>
                  <div class="panel-sub">{temp}°F • Wind {wind} mph • {flag}</div>
                </div>
                """,unsafe_allow_html=True)

    with b3:
        st.markdown('<div class="section">DATA STATUS</div>',unsafe_allow_html=True)

        st.markdown(f"""
        <div class="panel">
          <div class="panel-title">MLB Intelligence</div>
          <div class="panel-sub">Updated {age(MLB/'MLB_MATCHUP_BOARD_INTELLIGENCE.csv')}</div>
        </div>
        <div class="panel">
          <div class="panel-title">CFB Intelligence</div>
          <div class="panel-sub">Updated {age(CFB/'CFB_CURRENT_BOARD.csv')}</div>
        </div>
        <div class="panel">
          <div class="panel-title">NFL Historical Vault</div>
          <div class="panel-sub">{len(nfl):,} game-master rows available</div>
        </div>
        """,unsafe_allow_html=True)


# ============================================================
# TODAY'S SLATE
# ============================================================

elif mode=="🎯 Betting" and page=="Today's Slate":

    title(
        "BETTING",
        "Today's Slate",
        "MLB official decisions and CFB research in one sortable board."
    )

    if slate.empty:
        st.info("No slate data available.")
    else:
        c1,c2,c3=st.columns(3)

        with c1:
            sports=st.multiselect("Sports",["MLB","CFB"],default=["MLB","CFB"])

        with c2:
            conf=st.multiselect(
                "Confidence",
                ["HIGH","MEDIUM","LOW"],
                default=["HIGH","MEDIUM","LOW"]
            )

        with c3:
            actionable=st.toggle("Actionable only",False)

        x=slate[
            slate["Sport"].isin(sports) &
            slate["Confidence"].astype(str).str.upper().isin(conf)
        ].copy()

        if actionable:
            x=x[
                x["Decision"].astype(str).str.upper().isin(["BET","WATCH"]) |
                (
                    (x["Sport"]=="CFB") &
                    (x["Confidence"].astype(str).str.upper()=="HIGH")
                )
            ]

        now=pd.Timestamp.now(tz="UTC")
        x=x[x["Start"].isna()|(x["Start"]>=now-pd.Timedelta(hours=5))]
        x=x.sort_values("Start")

        show=x[
            ["Sport","Time","Matchup","Lean","Confidence","Decision","WinProb","Spread","Total","Books"]
        ].copy()

        show["WinProb"]=show["WinProb"].apply(lambda z:pct(z))
        show["Spread"]=show["Spread"].apply(lambda z:spread(z))
        show["Total"]=show["Total"].apply(lambda z:num(z))

        st.dataframe(show,hide_index=True,use_container_width=True,height=680)


# ============================================================
# BEST BETS
# ============================================================

elif mode=="🎯 Betting" and page=="Best Bets":

    title(
        "BETTING",
        "Best Bets",
        "Official model decisions stay separate from research-only college football."
    )

    st.markdown('<div class="section">OFFICIAL MLB BETS</div>',unsafe_allow_html=True)

    if mlb.empty:
        st.info("MLB board unavailable.")
    else:
        bets=mlb[mlb["decision"].astype(str).str.upper()=="BET"].copy()

        if bets.empty:
            st.markdown("""
            <div class="panel">
              <div class="panel-title">No official BETS right now</div>
              <div class="panel-sub">
                Hulk is staying disciplined instead of promoting WATCH or PASS plays.
              </div>
            </div>
            """,unsafe_allow_html=True)
        else:
            for _,r in bets.sort_values("_dt").iterrows():
                st.markdown(f"""
                <div class="panel">
                  <div style="display:flex;justify-content:space-between;">
                    <div>
                      <div class="panel-title">{mlb_matchup_html(r.get('away_team'), r.get('home_team'))}</div>
                      <div class="panel-sub">{local_date(r.get('gameDate'))} • {local_time(r.get('gameDate'))}</div>
                    </div>
                    <div>{decision_html('BET')}</div>
                  </div>
                  <div style="margin-top:10px;">
                    <span class="lean">{mlb_team_code(r.get('lean'))}</span>
                    &nbsp; {confidence_html(mlb_display_confidence(r))}
                  </div>
                </div>
                """,unsafe_allow_html=True)

    st.markdown('<div class="section">HIGH-CONFIDENCE CFB RESEARCH</div>',unsafe_allow_html=True)

    if cfb.empty:
        st.info("CFB board unavailable.")
    else:
        cx=cfb[
            (cfb["model_status"].astype(str)=="RESEARCH_READY") &
            (cfb["research_confidence"].astype(str).str.upper()=="HIGH")
        ].copy()

        now=pd.Timestamp.now(tz="UTC")
        cx=cx[cx["_dt"].isna()|(cx["_dt"]>=now-pd.Timedelta(hours=5))]
        cx=cx.sort_values("_dt")

        for _,r in cx.head(15).iterrows():
            st.markdown(f"""
            <div class="panel">
              <div style="display:flex;justify-content:space-between;">
                <div>
                  <div class="panel-title">{safe(r.get('away'))} @ {safe(r.get('home'))}</div>
                  <div class="panel-sub">{local_date(r.get('start'))} • {local_time(r.get('start'))}</div>
                </div>
                <div><span class="research">RESEARCH ONLY</span></div>
              </div>
              <div style="margin-top:9px;">
                <span class="lean">{safe(r.get('research_lean'))}</span>
                &nbsp; Home comp win {pct(r.get('comp_home_win_prob'))}
                &nbsp; Projected margin {num(r.get('comp_projected_margin'))}
              </div>
            </div>
            """,unsafe_allow_html=True)


# ============================================================
# LINE MOVEMENT
# ============================================================

elif mode=="🎯 Betting" and page=="Line Movement":

    title(
        "MARKET",
        "Line Movement",
        "Book consensus and movement research from the MLB market-history engine."
    )

    if signals.empty:
        st.info("No current signal data.")
    else:
        market=st.selectbox(
            "Market",
            ["All"]+sorted(signals["core_market"].dropna().astype(str).unique().tolist())
        )

        x=signals.copy()

        if market!="All":
            x=x[x["core_market"].astype(str)==market]

        if "market_signal_score" in x.columns:
            x=x.sort_values("market_signal_score",ascending=False)

        cols=[
            "away_team",
            "home_team",
            "core_market",
            "signal_target",
            "signal_strength",
            "books_reporting",
            "books_moving",
            "consensus_among_movers_pct",
            "whole_market_share_pct",
            "avg_implied_prob_move",
            "market_signal_score",
            "market_signal"
        ]
        cols=[c for c in cols if c in x.columns]

        st.dataframe(
            x[cols],
            hide_index=True,
            use_container_width=True,
            height=700
        )


# ============================================================
# MARKET TREND
# ============================================================

elif mode=="🎯 Betting" and page=="Market Signals":

    title(
        "MARKET",
        "Market Signals",
        "Consensus support, conflict and movement context."
    )

    if signals.empty:
        st.info("No current signals.")
    else:
        strengths=["All"]+sorted(signals["signal_strength"].dropna().astype(str).unique().tolist())
        strength=st.selectbox("Signal strength",strengths)

        x=signals.copy()

        if strength!="All":
            x=x[x["signal_strength"].astype(str)==strength]

        if "market_signal_score" in x.columns:
            x=x.sort_values("market_signal_score",ascending=False)

        for _,r in x.head(30).iterrows():
            st.markdown(f"""
            <div class="panel">
              <div class="panel-title">
                {safe(r.get('away_team')).title()} @ {safe(r.get('home_team')).title()}
              </div>
              <div class="panel-sub">
                {safe(r.get('core_market')).upper()} •
                {safe(r.get('signal_strength')).upper()} •
                {safe(r.get('books_reporting'))} books reporting
              </div>
              <div style="margin-top:8px;color:#dce5df;font-size:11px;">
                {safe(r.get('market_signal'))}
              </div>
            </div>
            """,unsafe_allow_html=True)


# ============================================================
# RESULTS
# ============================================================

elif mode=="🎯 Betting" and page=="Results":

    title(
        "TRACKING",
        "Results",
        "Historical prediction grading from the Sports Hulk vault."
    )

    if mlb_results.empty:
        st.markdown("""
        <div class="panel">
          <div class="panel-title">Results tracking file is currently empty or unavailable.</div>
          <div class="panel-sub">
            Once graded official predictions accumulate, this page will calculate actual hit rate and performance.
          </div>
        </div>
        """,unsafe_allow_html=True)
    else:
        st.dataframe(
            mlb_results.tail(250),
            hide_index=True,
            use_container_width=True,
            height=700
        )


# ============================================================
# SURVIVOR
# ============================================================

elif mode=="🎯 Betting" and page=="Survivor":

    title(
        "NFL",
        "Survivor Hulk",
        "Weekly survivor engine built from win probability and future team value."
    )

    st.markdown("""
    <div class="panel">
      <div class="panel-title">2026 live survivor board is not connected yet.</div>
      <div class="panel-sub">
        Historical NFL game master, team features and comps are online.
        Live weekly schedule/market input is the remaining piece.
      </div>
    </div>
    """,unsafe_allow_html=True)


# ============================================================
# RESEARCH
# ============================================================

elif mode=="🎯 Betting" and page=="Research":

    title(
        "MODEL LAB",
        "Research",
        "Calibration and historical model evidence."
    )

    cfb_cal=load_csv(CFB/"CFB_CALIBRATION.csv")
    mlb_cal=load_csv(MLB/"MLB_CALIBRATION_BY_CONFIDENCE_DECISION.csv")

    a,b=st.columns(2)

    with a:
        st.markdown('<div class="section">COLLEGE FOOTBALL</div>',unsafe_allow_html=True)
        if not cfb_cal.empty:
            st.dataframe(cfb_cal,hide_index=True,use_container_width=True)

    with b:
        st.markdown('<div class="section">BASEBALL</div>',unsafe_allow_html=True)
        if not mlb_cal.empty:
            st.dataframe(mlb_cal,hide_index=True,use_container_width=True)


# ============================================================
# BASEBALL HULK
# ============================================================

elif mode=="⚾ MLB":

    if page=="MLB Dashboard":

        title(
            "MLB",
            "MLB Command Center",
            "Starting pitching, bullpen, weather, comps and market context."
        )

        bets=int((mlb["decision"].astype(str).str.upper()=="BET").sum()) if not mlb.empty else 0
        high=int((mlb["confidence"].astype(str).str.upper()=="HIGH").sum()) if not mlb.empty else 0

        cs=st.columns(5)
        with cs[0]: kpi("Games",len(mlb),"Games Loaded")
        with cs[1]: kpi("Official Bets",bets,"Model decision","green")
        with cs[2]: kpi("High Confidence",high,"All decisions","gold")
        with cs[3]: kpi("Market Signals",len(signals),"Current signals")
        with cs[4]: kpi("Data Freshness",age(MLB/"MLB_MATCHUP_BOARD_INTELLIGENCE.csv"),"Matchup board")

        st.markdown('<div class="section">CURRENT MLB BOARD</div>',unsafe_allow_html=True)

        if not mlb.empty:
            for _,r in mlb.sort_values("_dt").iterrows():
                st.markdown(f"""
                <div class="panel">
                  <div style="display:flex;justify-content:space-between;">
                    <div>
                      <div class="panel-title">{mlb_matchup_html(r.get('away_team'), r.get('home_team'))}</div>
                      <div class="panel-sub">
                        {local_time(r.get('gameDate'))} •
                        {safe(r.get('away_probable_pitcher'))} vs {safe(r.get('home_probable_pitcher'))}
                      </div>
                    </div>
                    <div>{decision_html(r.get('decision'))}</div>
                  </div>
                  <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:11px;">
                    <div><div class="sub">HULK PICK</div><div class="team">{mlb_team_code(r.get('lean'))}</div></div>
                    <div><div class="sub">CONFIDENCE</div><div>{confidence_html(mlb_display_confidence(r))}</div></div>
                    <div><div class="sub">HIST. WIN % WIN</div><div class="team">{pct(r.get('comp_home_win_rate'))}</div></div>
                    <div><div class="sub">TOTAL</div><div class="team">{num(r.get('totals_median_point'))}</div></div>
                    <div><div class="sub">SPORTSBOOKS</div><div class="team">{safe(r.get('h2h_book_count'))}</div></div>
                  </div>
                </div>
                """,unsafe_allow_html=True)


    elif page=="MLB Best Bets":

        title(
            "MLB",
            "MLB Best Bets",
            "Official Hulk MLB model bets only."
        )

        if mlb.empty:

            st.info("MLB board unavailable.")

        else:

            bx = mlb[
                mlb["decision"]
                .astype(str)
                .str.upper()
                .eq("BET")
            ].copy()

            now = pd.Timestamp.now(tz="UTC")

            if "_dt" in bx.columns:
                bx = bx[
                    bx["_dt"].isna()
                    | (
                        bx["_dt"]
                        >= now - pd.Timedelta(hours=5)
                    )
                ]

            if bx.empty:

                st.markdown("""
                <div class="panel">
                  <div class="panel-title">
                    No official MLB BETS right now
                  </div>
                  <div class="panel-sub">
                    Hulk is staying disciplined instead of promoting
                    WATCH or PASS plays.
                  </div>
                </div>
                """, unsafe_allow_html=True)

            else:

                bx = bx.sort_values("_dt")

                st.markdown(
                    '<div class="section">OFFICIAL '
                    '<span>HULK MLB BETS</span></div>',
                    unsafe_allow_html=True
                )

                for _,r in bx.iterrows():

                    lean = r.get("lean")

                    st.html(textwrap.dedent(f"""
                    <div class="panel">

                      <div style="
                        display:flex;
                        justify-content:space-between;
                        gap:12px;
                        align-items:flex-start;
                      ">

                        <div>
                          <div class="panel-title">
                            {mlb_matchup_html(
                                r.get('away_team'),
                                r.get('home_team')
                            )}
                          </div>

                          <div class="panel-sub">
                            {local_date(r.get('gameDate'))}
                            •
                            {local_time(r.get('gameDate'))}
                          </div>
                        </div>

                        <div>
                          {decision_html('BET')}
                        </div>

                      </div>

                      <div style="
                        display:grid;
                        grid-template-columns:
                            1.2fr .9fr .9fr .9fr;
                        gap:10px;
                        margin-top:12px;
                      ">

                        <div>
                          <div class="sub">HULK PICK</div>
                          <div class="team">
                            {mlb_team_code(lean)}
                          </div>
                        </div>

                        <div>
                          <div class="sub">CONFIDENCE</div>
                          <div>
                            {confidence_html(
                                mlb_display_confidence(r)
                            )}
                          </div>
                        </div>

                        <div>
                          <div class="sub">STARTER EDGE</div>
                          <div class="team">
                            {num(r.get('starter_edge'), 3)}
                          </div>
                        </div>

                        <div>
                          <div class="sub">BULLPEN EDGE</div>
                          <div class="team">
                            {num(r.get('bullpen_edge'), 3)}
                          </div>
                        </div>

                      </div>

                      <div style="
                        display:grid;
                        grid-template-columns:
                            1fr 1fr 1fr;
                        gap:10px;
                        margin-top:10px;
                      ">

                        <div>
                          <div class="sub">COMPOSITE EDGE</div>
                          <div class="team">
                            {num(r.get('composite_edge'), 3)}
                          </div>
                        </div>

                        <div>
                          <div class="sub">HISTORICAL WIN RATE</div>
                          <div class="team">
                            {pct(r.get('comp_home_win_rate'))}
                          </div>
                        </div>

                        <div>
                          <div class="sub">SPORTSBOOKS</div>
                          <div class="team">
                            {safe(r.get('h2h_book_count'))}
                          </div>
                        </div>

                      </div>

                    </div>
                    """))

                st.caption(
                    "Only official MLB model BET decisions appear here. "
                    "WATCH and PASS plays are intentionally excluded."
                )

    elif page=="MLB Matchups":

        title("MLB","MLB Matchups","Full matchup research.")

        if not mlb.empty:
            choice=st.selectbox(
                "Game",
                mlb.index,
                format_func=lambda i:f"{mlb.loc[i,'away_team']} @ {mlb.loc[i,'home_team']}"
            )

            r=mlb.loc[choice]

            a,b,c=st.columns(3)

            with a:
                st.markdown("### Starting Pitching")
                st.write("Away:",safe(r.get("away_probable_pitcher")))
                st.write("Home:",safe(r.get("home_probable_pitcher")))
                st.write("Away matchup:",num(r.get("away_starter_vs_home_lineup"),3))
                st.write("Home matchup:",num(r.get("home_starter_vs_away_lineup"),3))

            with b:
                st.markdown("### Bullpen")
                st.write("Away workload:",num(r.get("away_bullpen_workload")))
                st.write("Home workload:",num(r.get("home_bullpen_workload")))
                st.write("Data present:",safe(r.get("bullpen_data_present")))

            with c:
                st.markdown("### Historical Comps")
                st.write("Samples:",safe(r.get("comp_count")))
                st.write("Quality:",safe(r.get("comp_quality_grade")))
                st.write("Home win:",pct(r.get("comp_home_win_rate")))
                st.write("Average total:",num(r.get("comp_avg_total_runs")))

    elif page=="Starting Pitching":

        title("MLB","Starting Pitching","Today's probable starters and matchup scores.")

        if not mlb.empty:
            cols=[
                "away_team","away_probable_pitcher","away_starter_vs_home_lineup",
                "home_team","home_probable_pitcher","home_starter_vs_away_lineup",
                "sample_pitches","pitch_types_matched"
            ]
            st.dataframe(
                mlb[[c for c in cols if c in mlb.columns]],
                hide_index=True,
                use_container_width=True
            )


    elif page=="MLB Player Props":



        render_prop_intelligence("MLB")
        st.stop()
        title(
            "MLB",
            "MLB Player Props",
            "Cached MLB sportsbook props ranked by fair-line edge and market movement."
        )

        if mlb_props.empty:

            st.info("No cached MLB player props available.")

        else:

            px = mlb_props.copy()

            for col in [
                "line",
                "fair_line",
                "open_line",
                "open_fair_line",
                "book_odds",
                "fair_odds",
            ]:
                if col in px.columns:
                    px[col] = pd.to_numeric(
                        px[col],
                        errors="coerce"
                    )

            px["side"] = (
                px["side"]
                .astype(str)
                .str.lower()
                .str.strip()
            )

            px = px[
                px["side"].isin(["over","under"])
                & px["line"].notna()
            ].copy()

            # ---------------------------------------------
            # MARKET EDGE
            # ---------------------------------------------

            px["market_edge"] = 0.0

            over = px["side"].eq("over")
            under = px["side"].eq("under")

            px.loc[over, "market_edge"] = (
                px.loc[over, "fair_line"]
                - px.loc[over, "line"]
            )

            px.loc[under, "market_edge"] = (
                px.loc[under, "line"]
                - px.loc[under, "fair_line"]
            )

            px["edge_pct"] = (
                px["market_edge"]
                / px["line"].abs().clip(lower=1.0)
            ) * 100

            px["line_move"] = (
                px["line"]
                - px["open_line"]
            )

            def mlb_prop_call(row):

                edge = row.get("edge_pct")

                if pd.isna(edge):
                    return "NO EDGE"

                if edge >= 12:
                    return "BET"

                if edge >= 5:
                    return "WATCH"

                return "PASS"

            def mlb_prop_conf(row):

                edge = row.get("edge_pct")

                if pd.isna(edge):
                    return "LOW"

                if edge >= 15:
                    return "HIGH"

                if edge >= 7:
                    return "MEDIUM"

                return "LOW"

            px["hulk_call"] = px.apply(
                mlb_prop_call,
                axis=1
            )

            px["hulk_confidence"] = px.apply(
                mlb_prop_conf,
                axis=1
            )

            # ---------------------------------------------
            # FILTERS
            # ---------------------------------------------

            players = sorted(
                px["player"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            stats = sorted(
                px["stat"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            NFL_PROP_LABELS = {
                "rushing_yards": "Rushing Yards",
                "receiving_yards": "Receiving Yards",
                "rushing+receiving_yards": "Rushing + Receiving Yards",
                "passing_yards": "Passing Yards",
                "passing+rushing_yards": "Passing + Rushing Yards",
                "receiving_receptions": "Receptions",
                "rushing_attempts": "Rushing Attempts",
                "passing_touchdowns": "Passing Touchdowns",
                "passing_interceptions": "Passing Interceptions",
                "defense_sacks": "Sacks",
                "defense_soloTackles": "Solo Tackles",
                "defense_combinedTackles": "Combined Tackles",
                "defense_assistedTackles": "Assisted Tackles",
                "defense_interceptions": "Defensive Interceptions",
                "touchdowns": "Anytime Touchdown",
                "fantasyScore": "Fantasy Score",
            }

            def nfl_prop_label(x):
                return NFL_PROP_LABELS.get(
                    x,
                    clean_prop_name(x)
                )

            c1,c2,c3,c4 = st.columns(4)

            with c1:
                player_filter = st.selectbox(
                    "Player",
                    ["All Players"] + players,
                    key="mlb_prop_player_v2"
                )

            with c2:
                stat_filter = st.selectbox(
                    "Prop",
                    ["All Props"] + stats,
                    format_func=lambda x:
                        x if x=="All Props"
                        else nfl_prop_label(x),
                    key="mlb_prop_stat_v2"
                )

            with c3:
                side_filter = st.selectbox(
                    "Side",
                    ["Both","Over","Under"],
                    key="mlb_prop_side_v2"
                )

            with c4:
                call_filter = st.selectbox(
                    "Hulk Call",
                    ["All","BET","WATCH","PASS"],
                    key="mlb_prop_call_v2"
                )

            fx = px.copy()

            if player_filter != "All Players":
                fx = fx[
                    fx["player"] == player_filter
                ]

            if stat_filter != "All Props":
                fx = fx[
                    fx["stat"] == stat_filter
                ]

            if side_filter != "Both":
                fx = fx[
                    fx["side"] == side_filter.lower()
                ]

            if call_filter != "All":
                fx = fx[
                    fx["hulk_call"] == call_filter
                ]

            fx = fx.sort_values(
                ["edge_pct","market_edge"],
                ascending=False
            )

            # ---------------------------------------------
            # KPIs
            # ---------------------------------------------

            bets = int(
                (fx["hulk_call"]=="BET").sum()
            )

            watches = int(
                (fx["hulk_call"]=="WATCH").sum()
            )

            high = int(
                (fx["hulk_confidence"]=="HIGH").sum()
            )

            players_shown = int(
                fx["player"].nunique()
            )

            k1,k2,k3,k4 = st.columns(4)

            with k1:
                kpi(
                    "Props",
                    f"{len(fx):,}",
                    "Filtered market"
                )

            with k2:
                kpi(
                    "Hulk BET",
                    bets,
                    "Largest market edges",
                    "green"
                )

            with k3:
                kpi(
                    "WATCH",
                    watches,
                    "Secondary edges",
                    "gold"
                )

            with k4:
                kpi(
                    "Players",
                    players_shown,
                    f"{high} high-confidence"
                )

            st.markdown(
                '<div class="section">MLB PLAYER PROPS '
                '<span>HULK MARKET EDGE</span></div>',
                unsafe_allow_html=True
            )

            if fx.empty:

                st.info(
                    "No MLB props match the selected filters."
                )

            else:

                for _,r in fx.head(100).iterrows():

                    player = safe(r.get("player"))

                    prop = clean_prop_name(
                        r.get("stat")
                    )

                    side = str(
                        r.get("side","")
                    ).upper()

                    line = r.get("line")
                    fair = r.get("fair_line")
                    opener = r.get("open_line")
                    move = r.get("line_move")
                    edge = r.get("market_edge")
                    edge_pct = r.get("edge_pct")
                    odds = r.get("book_odds")

                    line_txt = (
                        f"{float(line):g}"
                        if pd.notna(line)
                        else "—"
                    )

                    fair_txt = (
                        f"{float(fair):g}"
                        if pd.notna(fair)
                        else "—"
                    )

                    opener_txt = (
                        f"{float(opener):g}"
                        if pd.notna(opener)
                        else "—"
                    )

                    move_txt = (
                        f"{float(move):+.1f}"
                        if pd.notna(move)
                        else "—"
                    )

                    edge_txt = (
                        f"{float(edge):+.1f}"
                        if pd.notna(edge)
                        else "—"
                    )

                    edge_pct_txt = (
                        f"{float(edge_pct):+.1f}%"
                        if pd.notna(edge_pct)
                        else "—"
                    )

                    odds_txt = (
                        prop_odds(odds)
                        if pd.notna(odds)
                        else "—"
                    )

                    away = safe(
                        r.get("away_team")
                    )

                    home = safe(
                        r.get("home_team")
                    )

                    matchup = (
                        f"{away} @ {home}"
                        if away != "—" and home != "—"
                        else "Matchup unavailable"
                    )

                    call = safe(
                        r.get("hulk_call")
                    )

                    conf = safe(
                        r.get("hulk_confidence")
                    )

                    st.html(textwrap.dedent(f"""
                    <div class="panel">
                      <div style="
                        display:grid;
                        grid-template-columns:
                          minmax(190px,2fr)
                          .8fr .7fr .7fr .7fr .7fr .8fr .8fr;
                        gap:12px;
                        align-items:center;
                      ">

                        <div>
                          <div class="panel-title">
                            {player}
                          </div>

                          <div class="panel-sub">
                            {matchup}
                          </div>

                          <div class="sub"
                               style="margin-top:5px;">
                            {prop}
                          </div>
                        </div>

                        <div>
                          <div class="sub">SIDE</div>
                          <div class="team">{side}</div>
                        </div>

                        <div>
                          <div class="sub">LINE</div>
                          <div class="team">{line_txt}</div>
                        </div>

                        <div>
                          <div class="sub">FAIR</div>
                          <div class="team">{fair_txt}</div>
                        </div>

                        <div>
                          <div class="sub">OPEN</div>
                          <div class="team">{opener_txt}</div>
                        </div>

                        <div>
                          <div class="sub">MOVE</div>
                          <div class="team">{move_txt}</div>
                        </div>

                        <div>
                          <div class="sub">EDGE</div>
                          <div class="team">{edge_txt}</div>
                          <div class="sub">{edge_pct_txt}</div>
                        </div>

                        <div>
                          <div class="sub">ODDS</div>
                          <div class="team">{odds_txt}</div>
                        </div>

                      </div>

                      <div style="
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                        margin-top:10px;
                        padding-top:9px;
                        border-top:1px solid rgba(255,255,255,.08);
                      ">

                        <div class="sub">
                          HULK CONFIDENCE:
                          <strong>{conf}</strong>
                        </div>

                        <div class="team">
                          {call}
                        </div>

                      </div>
                    </div>
                    """))

            st.caption(
                "Hulk Market Edge compares the cached sportsbook line "
                "with the market-derived fair line. Positive edge favors "
                "the displayed OVER or UNDER."
            )

            st.caption(
                "This is market research, not an independently validated "
                "MLB player projection model. Page refreshes read Oracle "
                "cache only and spend zero API entities."
            )


    elif page=="Weather":

        title("MLB","Weather Impact","Park and game-weather research.")

        cols=[
            "away_team","home_team","venue",
            "temperature_f","precipitation","wind_mph",
            "wind_gust_mph","humidity_pct","park_run_factor",
            "run_environment_flag"
        ]

        if not mlb.empty:
            st.dataframe(
                mlb[[c for c in cols if c in mlb.columns]],
                hide_index=True,
                use_container_width=True
            )

    elif page=="MLB Market":

        title("MLB","MLB Market","Movement and consensus overlay.")

        if not signals.empty:
            st.dataframe(signals,hide_index=True,use_container_width=True,height=700)

    elif page=="MLB Results":

        title("MLB","MLB Results","Graded prediction history.")

        if not mlb_results.empty:
            st.dataframe(
                mlb_results.tail(300),
                hide_index=True,
                use_container_width=True,
                height=700
            )
        else:
            st.info("No graded results available yet.")


# ============================================================
# FANTASY
# ============================================================

elif mode=="🏆 Fantasy":

    # --------------------------------------------------------
    # SHARED FANTASY PREP
    # --------------------------------------------------------

    fb = fantasy.copy()

    if not fb.empty:
        fb["overall_rank"] = pd.to_numeric(
            fb["overall_rank"], errors="coerce"
        )
        fb["position_rank"] = pd.to_numeric(
            fb["position_rank"], errors="coerce"
        )
        fb["tier"] = pd.to_numeric(
            fb["tier"], errors="coerce"
        )
        fb["hulk_score"] = pd.to_numeric(
            fb["hulk_score"], errors="coerce"
        )

        fb = fb.sort_values("overall_rank")


    # --------------------------------------------------------
    # LEAGUE SETTINGS / DYNAMIC FANTASY MODEL
    # --------------------------------------------------------

    if "fantasy_league_settings" not in st.session_state:
        st.session_state["fantasy_league_settings"] = {
            "teams": 12,
            "scoring": "PPR",
            "qb_format": "1QB",
            "pass_td": 4,
            "te_premium": 0.0,
            "start_qb": 1,
            "start_rb": 2,
            "start_wr": 2,
            "start_te": 1,
            "start_flex": 1,
            "start_sf": 0,
            "start_k": 1,
            "start_dst": 1,
            "bench": 6,
        }

    league = st.session_state["fantasy_league_settings"].copy()

    def apply_league_model(df, cfg):
        if df.empty:
            return df

        x = df.copy()

        scoring = cfg["scoring"]

        if scoring == "PPR":
            base_col = "proj_ppr_points"
            sleeper_col = "sleeper_ppr_adp"
        elif scoring == "Half-PPR":
            base_col = "proj_ppr_points"
            sleeper_col = "sleeper_half_adp"
        else:
            base_col = "proj_ppr_points"
            sleeper_col = "sleeper_std_adp"

        x["league_proj_points"] = pd.to_numeric(
            x.get(base_col),
            errors="coerce"
        )

        # Reception scoring adjustment from PPR baseline.
        rec = pd.to_numeric(
            x.get("proj_rec"),
            errors="coerce"
        ).fillna(0)

        if scoring == "Half-PPR":
            x["league_proj_points"] = (
                x["league_proj_points"] - rec * 0.5
            )

        elif scoring == "Standard":
            x["league_proj_points"] = (
                x["league_proj_points"] - rec
            )

        # Passing TD adjustment from 4-point baseline.
        if cfg["pass_td"] == 6:
            pass_td = pd.to_numeric(
                x.get("proj_pass_td"),
                errors="coerce"
            ).fillna(0)

            x["league_proj_points"] = (
                x["league_proj_points"] + pass_td * 2
            )

        # TE premium.
        if cfg["te_premium"] > 0:
            te = x["position"].astype(str).eq("TE")

            x.loc[te, "league_proj_points"] = (
                x.loc[te, "league_proj_points"]
                + rec.loc[te] * cfg["te_premium"]
            )

        teams = int(cfg["teams"])

        qb_repl = max(
            teams * int(cfg["start_qb"] + cfg["start_sf"]),
            teams if cfg["qb_format"] == "1QB" else teams * 2
        )

        rb_repl = (
            teams * int(cfg["start_rb"])
            + int(round(teams * cfg["start_flex"] * 0.45))
        )

        wr_repl = (
            teams * int(cfg["start_wr"])
            + int(round(teams * cfg["start_flex"] * 0.45))
        )

        te_repl = (
            teams * int(cfg["start_te"])
            + int(round(teams * cfg["start_flex"] * 0.10))
        )

        replacement_slot = {
            "QB": max(1, qb_repl),
            "RB": max(1, rb_repl),
            "WR": max(1, wr_repl),
            "TE": max(1, te_repl),
        }

        replacement_points = {}

        for pos, slot in replacement_slot.items():
            q = (
                x[
                    (x["position"] == pos)
                    & x["league_proj_points"].notna()
                ]
                .sort_values(
                    "league_proj_points",
                    ascending=False
                )
            )

            if len(q) >= slot:
                replacement_points[pos] = float(
                    q.iloc[slot - 1]["league_proj_points"]
                )
            elif len(q):
                replacement_points[pos] = float(
                    q["league_proj_points"].min()
                )
            else:
                replacement_points[pos] = 0.0

        x["league_replacement_points"] = (
            x["position"].map(replacement_points)
        )

        x["league_vorp"] = (
            x["league_proj_points"]
            - x["league_replacement_points"]
        )

        # Scarcity changes with format.
        scarcity = {
            "RB": 1.08,
            "WR": 1.00,
            "TE": 1.05,
            "QB": 0.90,
        }

        if cfg["qb_format"] in {"2QB", "Superflex"}:
            scarcity["QB"] = 1.30

        if cfg["te_premium"] >= 0.5:
            scarcity["TE"] = 1.12

        x["league_scarcity"] = (
            x["position"]
            .map(scarcity)
            .fillna(1.0)
        )

        role = pd.to_numeric(
            x.get("role_adjustment"),
            errors="coerce"
        ).fillna(0)

        x["league_hulk_score"] = (
            x["league_vorp"]
            * x["league_scarcity"]
            + role
        )

        # Keep players without projections at bottom.
        x.loc[
            x["league_proj_points"].isna(),
            "league_hulk_score"
        ] = -999

        # K / DST are optional.
        # Current V2 player feed does not include usable K/DST projections,
        # so they are represented as roster requirements for now.
        # They should not be invented or ranked from missing data.

        x = (
            x.sort_values(
                ["league_hulk_score", "league_proj_points"],
                ascending=[False, False]
            )
            .reset_index(drop=True)
        )

        x["overall_rank"] = range(
            1,
            len(x) + 1
        )

        x["position_rank"] = (
            x.groupby("position")[
                "league_hulk_score"
            ]
            .rank(
                method="first",
                ascending=False
            )
            .astype(int)
        )

        x["tier"] = x["position_rank"].map(
            lambda r:
                1 if r <= 5 else
                2 if r <= 12 else
                3 if r <= 24 else
                4 if r <= 36 else
                5 if r <= 60 else
                6
        )

        # Scoring-specific Sleeper ADP comparison.
        if sleeper_col in x.columns:
            x["selected_sleeper_adp"] = pd.to_numeric(
                x[sleeper_col],
                errors="coerce"
            )
        else:
            x["selected_sleeper_adp"] = pd.NA

        x["league_value_vs_sleeper"] = (
            x["selected_sleeper_adp"]
            - x["overall_rank"]
        )

        return x


    fb = apply_league_model(
        fb,
        league
    )


    if page=="League Settings":

        title(
            "FANTASY",
            "League Settings",
            "Adjust scoring and roster structure. Hulk rankings recalculate automatically."
        )

        c1,c2,c3 = st.columns(3)

        with c1:
            teams = st.selectbox(
                "League Teams",
                [8,10,12,14,16],
                index=[8,10,12,14,16].index(
                    league["teams"]
                )
            )

            scoring = st.selectbox(
                "Scoring",
                ["Standard","Half-PPR","PPR"],
                index=["Standard","Half-PPR","PPR"].index(
                    league["scoring"]
                )
            )

            qb_format = st.selectbox(
                "QB Format",
                ["1QB","2QB","Superflex"],
                index=["1QB","2QB","Superflex"].index(
                    league["qb_format"]
                )
            )

            pass_td = st.selectbox(
                "Passing TD",
                [4,6],
                index=[4,6].index(
                    league["pass_td"]
                )
            )

        with c2:
            te_premium = st.selectbox(
                "TE Premium / Reception",
                [0.0,0.5,1.0],
                index=[0.0,0.5,1.0].index(
                    league["te_premium"]
                )
            )

            start_qb = st.number_input(
                "Starting QB",
                0, 3,
                int(league["start_qb"])
            )

            start_rb = st.number_input(
                "Starting RB",
                0, 5,
                int(league["start_rb"])
            )

            start_wr = st.number_input(
                "Starting WR",
                0, 5,
                int(league["start_wr"])
            )

        with c3:
            start_te = st.number_input(
                "Starting TE",
                0, 3,
                int(league["start_te"])
            )

            start_flex = st.number_input(
                "Starting FLEX",
                0, 4,
                int(league["start_flex"])
            )

            start_sf = st.number_input(
                "Starting Superflex",
                0, 2,
                int(league["start_sf"])
            )

            start_k = st.number_input(
                "Starting Kicker",
                0, 2,
                int(league["start_k"])
            )

            start_dst = st.number_input(
                "Starting Team Defense",
                0, 2,
                int(league["start_dst"])
            )

            bench = st.number_input(
                "Bench Spots",
                0, 15,
                int(league["bench"])
            )

        new_settings = {
            "teams": int(teams),
            "scoring": scoring,
            "qb_format": qb_format,
            "pass_td": int(pass_td),
            "te_premium": float(te_premium),
            "start_qb": int(start_qb),
            "start_rb": int(start_rb),
            "start_wr": int(start_wr),
            "start_te": int(start_te),
            "start_flex": int(start_flex),
            "start_sf": int(start_sf),
            "start_k": int(start_k),
            "start_dst": int(start_dst),
            "bench": int(bench),
        }

        st.session_state[
            "fantasy_league_settings"
        ] = new_settings

        # Recalculate immediately for display.
        preview = apply_league_model(
            fantasy.copy(),
            new_settings
        )

        c1,c2,c3,c4 = st.columns(4)

        with c1:
            kpi(
                "Format",
                scoring,
                f"{teams}-team"
            )

        with c2:
            kpi(
                "QB",
                qb_format,
                f"{pass_td}-pt pass TD"
            )

        with c3:
            kpi(
                "TE Premium",
                f"+{te_premium:.1f}",
                "Per TE reception"
            )

        with c4:
            kpi(
                "K / DST",
                f"{start_k} / {start_dst}",
                "Starting slots"
            )

        st.caption(
            "Kicker and DST roster settings are saved, but Hulk will not fabricate "
            "rankings for them until a reliable 2026 K/DST projection source is connected."
        )

        st.markdown(
            '<div class="section">TOP 25 '
            '<span>ADJUSTED HULK RANKINGS</span></div>',
            unsafe_allow_html=True
        )

        for _,r in preview.head(25).iterrows():

            proj = (
                f"{float(r.get('league_proj_points')):.1f}"
                if pd.notna(r.get("league_proj_points"))
                else "—"
            )

            st.html(textwrap.dedent(f"""
            <div class="panel">
              <div style="
                display:grid;
                grid-template-columns:55px 2fr .7fr .8fr .8fr;
                gap:10px;
                align-items:center;
              ">

                <div style="font-size:21px;font-weight:950;color:#45ff2a;">
                  #{int(r.get('overall_rank'))}
                </div>

                <div>
                  {fantasy_player_html(
                      r.get('full_name'),
                      r.get('team'),
                      r.get('position')
                  )}
                </div>

                <div>
                  <div class="sub">POS</div>
                  <div class="team">
                    {safe(r.get('position'))}{int(r.get('position_rank'))}
                  </div>
                </div>

                <div>
                  <div class="sub">PROJ</div>
                  <div class="team">{proj}</div>
                </div>

                <div>
                  <div class="sub">TIER</div>
                  <div class="team">{int(r.get('tier'))}</div>
                </div>

              </div>
            </div>
            """))


    # --------------------------------------------------------
    # FANTASY DASHBOARD
    # --------------------------------------------------------

    if page=="Fantasy Dashboard":

        title(
            "FANTASY",
            "Fantasy Dashboard",
            "2026 player pool, Hulk rankings, tiers and draft tools."
        )

        if fb.empty:
            st.error("Fantasy current board is unavailable.")

        else:
            top250 = fb[fb["overall_rank"] <= 250]

            qbs = int((fb["position"]=="QB").sum())
            rbs = int((fb["position"]=="RB").sum())
            wrs = int((fb["position"]=="WR").sum())
            tes = int((fb["position"]=="TE").sum())

            cs=st.columns(5)

            with cs[0]:
                kpi("Top Board","250","Draftable priority list","green")

            with cs[1]:
                kpi("QB",qbs,"Current player pool")

            with cs[2]:
                kpi("RB",rbs,"Current player pool")

            with cs[3]:
                kpi("WR",wrs,"Current player pool")

            with cs[4]:
                kpi("TE",tes,"Current player pool")

            st.markdown(
                '<div class="section">TOP OF THE BOARD '
                '<span>HULK RANKINGS</span></div>',
                unsafe_allow_html=True
            )

            for _,r in top250.head(12).iterrows():

                rookie = (
                    '<span class="research">ROOKIE</span>'
                    if bool(r.get("rookie_2026",False))
                    else ""
                )

                st.html(textwrap.dedent(f"""
                <div class="panel">
                  <div style="display:grid;
                              grid-template-columns:55px 2fr .6fr .6fr .7fr;
                              gap:10px;align-items:center;">
                    <div style="font-size:21px;font-weight:950;color:#45ff2a;">
                      #{int(r.get('overall_rank'))}
                    </div>

                    <div>
                      {fantasy_player_html(
                          r.get('full_name'),
                          r.get('team'),
                          r.get('position')
                      )}
                    </div>

                    <div>
                      <div class="sub">POS RANK</div>
                      <div class="team">
                        {safe(r.get('position'))}{int(r.get('position_rank'))}
                      </div>
                    </div>

                    <div>
                      <div class="sub">TIER</div>
                      <div class="team">{int(r.get('tier'))}</div>
                    </div>

                    <div>{rookie}</div>
                  </div>
                </div>
                """))

            st.caption(
                "ADP is intentionally not shown yet because a live ADP source "
                "has not been connected."
            )



    # --------------------------------------------------------
    # DRAFT KIT
    # --------------------------------------------------------

    elif page=="Draft Kit":

        title(
            "FANTASY",
            "Live Draft Kit",
            "Cross players off as they are drafted and use your draft-room platform to time picks."
        )

        if fb.empty:
            st.error("Fantasy board unavailable.")

        else:
            top = fb[
                fb["overall_rank"] <= 250
            ].copy()

            platform = st.radio(
                "Draft Platform",
                ["ESPN","Sleeper","Yahoo","CBS","Consensus"],
                horizontal=True,
                key="fantasy_draft_platform"
            )

            if platform=="ESPN":
                top["room_adp"] = pd.to_numeric(
                    top["espn_ppr_room_rank"],
                    errors="coerce"
                )
            elif platform=="Sleeper":
                top["room_adp"] = pd.to_numeric(
                    top["sleeper_ppr_adp"],
                    errors="coerce"
                )
            elif platform=="Yahoo":
                top["room_adp"] = pd.to_numeric(
                    top["yahoo_adp"],
                    errors="coerce"
                )
            elif platform=="CBS":
                top["room_adp"] = pd.to_numeric(
                    top["cbs_adp"],
                    errors="coerce"
                )
            else:
                top["room_adp"] = pd.to_numeric(
                    top["consensus_adp"],
                    errors="coerce"
                )

            top["room_value"] = (
                top["room_adp"]
                - top["overall_rank"]
            )

            names = (
                top["full_name"]
                .dropna()
                .tolist()
            )

            drafted = st.multiselect(
                "Mark players already drafted",
                names,
                key="fantasy_drafted_players",
                placeholder="Search player name..."
            )

            available = top[
                ~top["full_name"].isin(drafted)
            ].copy()

            available = available.sort_values(
                "overall_rank"
            )

            c1,c2,c3,c4 = st.columns(4)

            with c1:
                kpi(
                    "Players Left",
                    len(available),
                    "Top 250 remaining",
                    "green"
                )

            with c2:
                kpi(
                    "Drafted",
                    len(drafted),
                    "Crossed off"
                )

            with c3:
                next_player = (
                    available.iloc[0]["full_name"]
                    if len(available)
                    else "—"
                )

                kpi(
                    "Best Available",
                    safe(next_player),
                    "Highest Hulk rank"
                )

            with c4:
                value_count = int(
                    (
                        pd.to_numeric(
                            available["room_value"],
                            errors="coerce"
                        ) >= 8
                    ).sum()
                )

                kpi(
                    f"{platform} Values",
                    value_count,
                    "8+ picks of room"
                )

            st.markdown(
                '<div class="section">BEST AVAILABLE '
                '<span>DRAFT DECISIONS</span></div>',
                unsafe_allow_html=True
            )

            for _,r in available.head(30).iterrows():

                rank = int(r.get("overall_rank"))

                pos_rank = (
                    int(r.get("position_rank"))
                    if pd.notna(r.get("position_rank"))
                    else "—"
                )

                room = r.get("room_adp")
                room_value = r.get("room_value")

                room_txt = (
                    f"{float(room):.1f}"
                    if pd.notna(room)
                    else "—"
                )

                value_txt = (
                    f"{float(room_value):+.1f}"
                    if pd.notna(room_value)
                    else "—"
                )

                if pd.isna(room_value):
                    decision = "NO MARKET"

                elif room_value >= 15:
                    decision = "WAIT"

                elif room_value >= 8:
                    decision = "VALUE"

                elif room_value <= -8:
                    decision = "TAKE NOW"

                else:
                    decision = "FAIR VALUE"

                proj = (
                    f"{float(r.get('proj_ppr_points')):.1f}"
                    if pd.notna(r.get("proj_ppr_points"))
                    else "—"
                )

                rookie = (
                    '<span class="research">ROOKIE</span>'
                    if bool(r.get("rookie_2026",False))
                    else ""
                )

                st.html(textwrap.dedent(f"""
                <div class="panel">
                  <div style="
                    display:grid;
                    grid-template-columns:60px 2fr .7fr .8fr .8fr .8fr 1fr;
                    gap:10px;
                    align-items:center;
                  ">

                    <div style="font-size:21px;font-weight:950;color:#45ff2a;">
                      #{rank}
                    </div>

                    <div>
                      {fantasy_player_html(
                          r.get('full_name'),
                          r.get('team'),
                          r.get('position')
                      )}
                      <div style="margin-top:4px;">{rookie}</div>
                    </div>

                    <div>
                      <div class="sub">POS</div>
                      <div class="team">
                        {safe(r.get('position'))}{pos_rank}
                      </div>
                    </div>

                    <div>
                      <div class="sub">PPR PROJ</div>
                      <div class="team">{proj}</div>
                    </div>

                    <div>
                      <div class="sub">{platform.upper()}</div>
                      <div class="team">{room_txt}</div>
                    </div>

                    <div>
                      <div class="sub">ROOM VALUE</div>
                      <div class="team">{value_txt}</div>
                    </div>

                    <div>
                      <div class="sub">DECISION</div>
                      <div class="team">{decision}</div>
                    </div>

                  </div>
                </div>
                """))

            st.caption(
                "Room Value = selected platform rank minus Hulk Rank. "
                "Positive means the room is letting the player fall relative to Hulk."
            )

    # --------------------------------------------------------
    # RANKINGS
    # --------------------------------------------------------

    elif page=="Rankings":

        title(
            "FANTASY",
            "Fantasy Rankings",
            "Hulk V2 PPR rankings with live multi-source market context."
        )

        if fb.empty:
            st.error("Fantasy board unavailable.")

        else:
            position = st.radio(
                "Position",
                ["OVERALL","QB","RB","WR","TE"],
                horizontal=True,
                key="fantasy_rank_position"
            )

            if position=="OVERALL":
                x = fb[
                    fb["overall_rank"] <= 250
                ].copy()
            else:
                x = fb[
                    fb["position"] == position
                ].copy().sort_values("position_rank")

            x = x.head(250)

            for _,r in x.iterrows():

                rank = (
                    int(r.get("overall_rank"))
                    if pd.notna(r.get("overall_rank"))
                    else "—"
                )

                pos_rank = (
                    int(r.get("position_rank"))
                    if pd.notna(r.get("position_rank"))
                    else "—"
                )

                proj = (
                    f"{float(r.get('proj_ppr_points')):.1f}"
                    if pd.notna(r.get("proj_ppr_points"))
                    else "—"
                )

                adp = (
                    f"{float(r.get('consensus_adp')):.1f}"
                    if pd.notna(r.get("consensus_adp"))
                    else "—"
                )

                value = r.get("hulk_value_vs_consensus")

                if pd.notna(value):
                    value_txt = f"{float(value):+.1f}"
                else:
                    value_txt = "—"

                action = safe(r.get("draft_action"))

                st.html(textwrap.dedent(f"""
                <div class="panel">
                  <div style="
                    display:grid;
                    grid-template-columns:60px 2.2fr .7fr .8fr .8fr .8fr 1fr;
                    gap:12px;
                    align-items:center;
                  ">

                    <div style="font-size:22px;font-weight:950;color:#45ff2a;">
                      #{rank}
                    </div>

                    <div>
                      {fantasy_player_html(
                          r.get('full_name'),
                          r.get('team'),
                          r.get('position')
                      )}
                    </div>

                    <div>
                      <div class="sub">POS</div>
                      <div class="team">{safe(r.get('position'))}{pos_rank}</div>
                    </div>

                    <div>
                      <div class="sub">PPR PROJ</div>
                      <div class="team">{proj}</div>
                    </div>

                    <div>
                      <div class="sub">CONS ADP</div>
                      <div class="team">{adp}</div>
                    </div>

                    <div>
                      <div class="sub">HULK VALUE</div>
                      <div class="team">{value_txt}</div>
                    </div>

                    <div>
                      <div class="sub">ACTION</div>
                      <div class="team">{action}</div>
                    </div>

                  </div>
                </div>
                """))

    # --------------------------------------------------------
    # ADP / VALUE
    # --------------------------------------------------------

    elif page=="ADP / Value":

        title(
            "FANTASY",
            "ADP / Value",
            "Sleeper, ESPN, Yahoo and CBS compared against Hulk V2."
        )

        if fb.empty:
            st.error("Fantasy board unavailable.")

        else:
            market = fb[
                fb["consensus_adp"].notna()
            ].copy()

            platform = st.radio(
                "Draft Platform",
                ["Consensus","ESPN","Sleeper","Yahoo","CBS"],
                horizontal=True,
                key="fantasy_adp_platform"
            )

            if platform=="ESPN":
                market["platform_adp"] = pd.to_numeric(
                    market["espn_ppr_room_rank"],
                    errors="coerce"
                )
            elif platform=="Sleeper":
                market["platform_adp"] = pd.to_numeric(
                    market["sleeper_ppr_adp"],
                    errors="coerce"
                )
            elif platform=="Yahoo":
                market["platform_adp"] = pd.to_numeric(
                    market["yahoo_adp"],
                    errors="coerce"
                )
            elif platform=="CBS":
                market["platform_adp"] = pd.to_numeric(
                    market["cbs_adp"],
                    errors="coerce"
                )
            else:
                market["platform_adp"] = pd.to_numeric(
                    market["consensus_adp"],
                    errors="coerce"
                )

            market["platform_value"] = (
                market["platform_adp"]
                - market["overall_rank"]
            )

            c1,c2,c3,c4 = st.columns(4)

            with c1:
                kpi(
                    "4-Source Players",
                    int((market["adp_source_count"]==4).sum()),
                    "Sleeper + ESPN + Yahoo + CBS",
                    "green"
                )

            with c2:
                kpi(
                    "3+ Sources",
                    int((market["adp_source_count"]>=3).sum()),
                    "Strong consensus coverage"
                )

            with c3:
                steals = int(
                    (market["platform_value"] >= 10).sum()
                )
                kpi(
                    f"{platform} Values",
                    steals,
                    "10+ picks of room"
                )

            with c4:
                waits = int(
                    (market["platform_value"] <= -10).sum()
                )
                kpi(
                    f"{platform} Reaches",
                    waits,
                    "Market earlier than Hulk"
                )

            filt = st.radio(
                "View",
                ["All","Values","Wait / Reach","Big Platform Gaps"],
                horizontal=True,
                key="fantasy_value_filter"
            )

            show = market.copy()

            if filt=="Values":
                show = show[
                    show["platform_value"] >= 8
                ]
            elif filt=="Wait / Reach":
                show = show[
                    show["platform_value"] <= -8
                ]
            elif filt=="Big Platform Gaps":
                show = show[
                    pd.to_numeric(
                        show["platform_spread"],
                        errors="coerce"
                    ) >= 8
                ]

            show = show.sort_values(
                "overall_rank"
            ).head(150)

            for _,r in show.iterrows():

                def n(v):
                    return (
                        f"{float(v):.1f}"
                        if pd.notna(v)
                        else "—"
                    )

                value = r.get("platform_value")

                value_txt = (
                    f"{float(value):+.1f}"
                    if pd.notna(value)
                    else "—"
                )

                st.html(textwrap.dedent(f"""
                <div class="panel">
                  <div style="
                    display:grid;
                    grid-template-columns:55px 2fr repeat(6,.65fr) 1fr;
                    gap:10px;
                    align-items:center;
                  ">

                    <div style="font-size:20px;font-weight:950;color:#45ff2a;">
                      #{int(r.get('overall_rank'))}
                    </div>

                    <div>
                      {fantasy_player_html(
                          r.get('full_name'),
                          r.get('team'),
                          r.get('position')
                      )}
                    </div>

                    <div>
                      <div class="sub">SLEEPER</div>
                      <div class="team">{n(r.get('sleeper_ppr_adp'))}</div>
                    </div>

                    <div>
                      <div class="sub">ESPN</div>
                      <div class="team">{n(r.get('espn_ppr_room_rank'))}</div>
                    </div>

                    <div>
                      <div class="sub">YAHOO</div>
                      <div class="team">{n(r.get('yahoo_adp'))}</div>
                    </div>

                    <div>
                      <div class="sub">CBS</div>
                      <div class="team">{n(r.get('cbs_adp'))}</div>
                    </div>

                    <div>
                      <div class="sub">CONS</div>
                      <div class="team">{n(r.get('consensus_adp'))}</div>
                    </div>

                    <div>
                      <div class="sub">{platform.upper()} VALUE</div>
                      <div class="team">{value_txt}</div>
                    </div>

                    <div>
                      <div class="sub">BEST ROOM</div>
                      <div class="team">
                        {safe(r.get('best_value_platform'))}
                        {n(r.get('best_platform_value'))}
                      </div>
                    </div>

                  </div>
                </div>
                """))

            st.caption(
                "Positive value means Hulk ranks the player earlier than the selected "
                "draft room. ADP and room rank remain separate from the Hulk model."
            )

    # --------------------------------------------------------
    # SLEEPERS
    # --------------------------------------------------------

    elif page=="Sleepers":

        title(
            "FANTASY",
            "Hulk Sleepers",
            "Players Hulk ranks materially earlier than the multi-source fantasy market."
        )

        if fb.empty:
            st.error("Fantasy board unavailable.")

        else:
            sx = fb[
                fb["consensus_adp"].notna()
                & fb["hulk_value_vs_consensus"].notna()
            ].copy()

            sx = sx[
                sx["hulk_value_vs_consensus"] >= 8
            ].sort_values(
                "hulk_value_vs_consensus",
                ascending=False
            ).head(40)

            st.caption(
                "Sleepers now require real market value. Positive Hulk Value means "
                "the player is ranked earlier by Hulk than the multi-source consensus."
            )

            for _,r in sx.iterrows():

                value = float(
                    r.get("hulk_value_vs_consensus")
                )

                consensus = float(
                    r.get("consensus_adp")
                )

                rank = int(
                    r.get("overall_rank")
                )

                st.html(textwrap.dedent(f"""
                <div class="panel">
                  <div style="
                    display:grid;
                    grid-template-columns:60px 2fr .8fr .8fr .8fr 1fr;
                    gap:10px;
                    align-items:center;
                  ">

                    <div style="font-size:20px;font-weight:950;color:#45ff2a;">
                      #{rank}
                    </div>

                    <div>
                      {fantasy_player_html(
                          r.get('full_name'),
                          r.get('team'),
                          r.get('position')
                      )}
                    </div>

                    <div>
                      <div class="sub">CONS ADP</div>
                      <div class="team">{consensus:.1f}</div>
                    </div>

                    <div>
                      <div class="sub">HULK EDGE</div>
                      <div class="team">+{value:.1f}</div>
                    </div>

                    <div>
                      <div class="sub">BEST ROOM</div>
                      <div class="team">
                        {safe(r.get('best_value_platform'))}
                      </div>
                    </div>

                    <div>
                      <div class="sub">ACTION</div>
                      <div class="team">
                        {safe(r.get('draft_action'))}
                      </div>
                    </div>

                  </div>
                </div>
                """))

    # --------------------------------------------------------
    # ROSTER BUILDER
    # --------------------------------------------------------

    elif page=="Roster Builder":

        title(
            "FANTASY",
            "Roster Builder",
            "Track your drafted team and see positional needs."
        )

        if fb.empty:
            st.error("Fantasy board unavailable.")

        else:
            player_names = (
                fb[fb["overall_rank"]<=250]
                ["full_name"]
                .dropna()
                .tolist()
            )

            roster_players = st.multiselect(
                "Players on my team",
                player_names,
                key="fantasy_my_roster"
            )

            mine = fb[
                fb["full_name"].isin(roster_players)
            ].copy()

            c1,c2,c3,c4 = st.columns(4)

            with c1:
                kpi(
                    "QB",
                    int((mine["position"]=="QB").sum())
                    if len(mine) else 0,
                    "On roster"
                )

            with c2:
                kpi(
                    "RB",
                    int((mine["position"]=="RB").sum())
                    if len(mine) else 0,
                    "On roster"
                )

            with c3:
                kpi(
                    "WR",
                    int((mine["position"]=="WR").sum())
                    if len(mine) else 0,
                    "On roster"
                )

            with c4:
                kpi(
                    "TE",
                    int((mine["position"]=="TE").sum())
                    if len(mine) else 0,
                    "On roster"
                )

            if mine.empty:
                st.info("Add players above as you draft them.")

            else:
                mine = mine.sort_values("overall_rank")

                for _,r in mine.iterrows():
                    st.html(textwrap.dedent(f"""
                    <div class="panel">
                      {fantasy_player_html(
                          r.get('full_name'),
                          r.get('team'),
                          r.get('position')
                      )}
                      <div class="sub" style="margin-top:6px;">
                        Hulk #{int(r.get('overall_rank'))}
                        • {safe(r.get('position'))}{int(r.get('position_rank'))}
                        • Tier {int(r.get('tier'))}
                      </div>
                    </div>
                    """))


    # --------------------------------------------------------
    # NFL RESEARCH
    # --------------------------------------------------------

    elif page=="NFL Research":

        title(
            "FANTASY",
            "NFL Player Research",
            "Historical production supporting the Fantasy board."
        )

        if fb.empty:
            st.error("Fantasy board unavailable.")

        else:
            player = st.selectbox(
                "Player",
                fb["full_name"].dropna().tolist()
            )

            r = fb[
                fb["full_name"] == player
            ].iloc[0]

            a,b,c = st.columns(3)

            with a:
                kpi(
                    "Hulk Rank",
                    f"#{int(r.get('overall_rank'))}",
                    f"{safe(r.get('position'))}{int(r.get('position_rank'))}",
                    "green"
                )

            with b:
                kpi(
                    "Tier",
                    int(r.get("tier")),
                    safe(r.get("team"))
                )

            with c:
                kpi(
                    "ADP",
                    "Pending",
                    "Live source"
                )

            stat_rows = []

            pos = safe(r.get("position"))

            if pos=="QB":
                stat_rows = [
                    ["Pass Yards", num(r.get("pass_yards"),0)],
                    ["Pass TD", num(r.get("pass_td"),0)],
                    ["Rush Yards", num(r.get("rush_yards"),0)],
                    ["Rush TD", num(r.get("rush_td"),0)],
                ]

            elif pos=="RB":
                stat_rows = [
                    ["Rush Yards", num(r.get("rush_yards"),0)],
                    ["Rush TD", num(r.get("rush_td"),0)],
                    ["Targets", num(r.get("targets"),0)],
                    ["Rec Yards", num(r.get("rec_yards"),0)],
                    ["Rec TD", num(r.get("rec_td"),0)],
                ]

            else:
                stat_rows = [
                    ["Targets", num(r.get("targets"),0)],
                    ["Receptions", num(r.get("receptions"),0)],
                    ["Rec Yards", num(r.get("rec_yards"),0)],
                    ["Rec TD", num(r.get("rec_td"),0)],
                    ["Air Yard Share", num(r.get("air_yard_share"),1)],
                ]

            st.dataframe(
                pd.DataFrame(
                    stat_rows,
                    columns=["2025 Regular Season","Value"]
                ),
                hide_index=True,
                use_container_width=True
            )




# ============================================================
# NFL SECTION
# ============================================================

elif mode=="🏈 NFL":

    if page in {"NFL Dashboard","NFL Command Center"}:

        title(
            "NFL",
            "NFL Dashboard",
            "Current-week sportsbook board with market probabilities, lines and Survivor context."
        )

        if nfl_current_week.empty:

            st.info("No cached NFL current-week board available.")

        else:

            nx = nfl_current_week.copy()

            nx["start"] = pd.to_datetime(
                nx["start"],
                errors="coerce",
                utc=True
            )

            for col in [
                "away_moneyline",
                "home_moneyline",
                "away_spread",
                "home_spread",
                "total",
                "home_market_win_prob",
                "away_market_win_prob",
                "survivor_win_prob",
            ]:
                if col in nx.columns:
                    nx[col] = pd.to_numeric(
                        nx[col],
                        errors="coerce"
                    )

            games = len(nx)

            strong_favs = int(
                (
                    nx[
                        [
                            "home_market_win_prob",
                            "away_market_win_prob"
                        ]
                    ].max(axis=1)
                    >= 0.65
                ).sum()
            )

            avg_total = (
                nx["total"].mean()
                if "total" in nx.columns
                else None
            )

            books = int(
                pd.to_numeric(
                    nx.get("sportsbooks"),
                    errors="coerce"
                ).max()
            ) if "sportsbooks" in nx.columns else 0

            c1,c2,c3,c4 = st.columns(4)

            with c1:
                kpi(
                    "Games",
                    games,
                    "Current week"
                )

            with c2:
                kpi(
                    "65%+ Favorites",
                    strong_favs,
                    "No-vig market probability",
                    "green"
                )

            with c3:
                kpi(
                    "Avg Total",
                    f"{avg_total:.1f}" if pd.notna(avg_total) else "—",
                    "Current board"
                )

            with c4:
                kpi(
                    "Sportsbooks",
                    books,
                    "Consensus coverage"
                )

            st.markdown(
                '<div class="section">CURRENT NFL '
                '<span>MARKET BOARD</span></div>',
                unsafe_allow_html=True
            )

            for _,r in nx.sort_values("start").iterrows():

                away = r.get("away_team")
                home = r.get("home_team")

                away_prob = r.get(
                    "away_market_win_prob"
                )

                home_prob = r.get(
                    "home_market_win_prob"
                )

                favorite = (
                    away
                    if pd.notna(away_prob)
                    and pd.notna(home_prob)
                    and away_prob > home_prob
                    else home
                )

                favorite_prob = (
                    max(away_prob, home_prob)
                    if pd.notna(away_prob)
                    and pd.notna(home_prob)
                    else None
                )

                fav_prob_txt = (
                    f"{favorite_prob*100:.1f}%"
                    if pd.notna(favorite_prob)
                    else "—"
                )

                st.html(textwrap.dedent(f"""
                <div class="panel">
                  <div style="
                    display:grid;
                    grid-template-columns:2fr .8fr .8fr .8fr .9fr;
                    gap:12px;
                    align-items:center;
                  ">

                    <div>
                      <div class="panel-title">
                        {nfl_matchup_html(away, home, 28)}
                      </div>
                      <div class="panel-sub">
                        {local_date(r.get('start'))} • {local_time(r.get('start'))}
                      </div>
                    </div>

                    <div>
                      <div class="sub">FAVORITE</div>
                      <div class="team">
                        {nfl_team_display(favorite, 22)}
                      </div>
                    </div>

                    <div>
                      <div class="sub">WIN PROB</div>
                      <div class="team">{fav_prob_txt}</div>
                    </div>

                    <div>
                      <div class="sub">TOTAL</div>
                      <div class="team">
                        {num(r.get('total'))}
                      </div>
                    </div>

                    <div>
                      <div class="sub">BOOKS</div>
                      <div class="team">
                        {safe(r.get('sportsbooks'))}
                      </div>
                    </div>

                  </div>
                </div>
                """))

            st.caption(
                "NFL probabilities shown here are no-vig sportsbook-implied market probabilities, "
                "not an official Hulk NFL model."
            )

            st.caption(
                "This page reads Oracle cache only. Refreshing it does not spend API credits."
            )


    elif page=="NFL Best Bets":

        title(
            "NFL",
            "NFL Best Bets",
            "Strongest current-week market favorites. Market research only until the official Hulk NFL model is validated."
        )

        if nfl_current_week.empty:

            st.info("No cached NFL current-week board available.")

        else:

            bx = nfl_current_week.copy()

            bx["start"] = pd.to_datetime(
                bx["start"],
                errors="coerce",
                utc=True
            )

            for col in [
                "home_market_win_prob",
                "away_market_win_prob",
                "home_spread",
                "away_spread",
                "home_moneyline",
                "away_moneyline",
                "total",
            ]:
                bx[col] = pd.to_numeric(
                    bx[col],
                    errors="coerce"
                )

            rows = []

            for _,r in bx.iterrows():

                hp = r.get("home_market_win_prob")
                ap = r.get("away_market_win_prob")

                if pd.isna(hp) or pd.isna(ap):
                    continue

                if hp >= ap:
                    team = r.get("home_team")
                    prob = hp
                    spread_val = r.get("home_spread")
                    ml = r.get("home_moneyline")
                    opponent = r.get("away_team")
                else:
                    team = r.get("away_team")
                    prob = ap
                    spread_val = r.get("away_spread")
                    ml = r.get("away_moneyline")
                    opponent = r.get("home_team")

                if prob >= 0.72:
                    call = "STRONG MARKET LEAN"
                    confidence = "HIGH"
                elif prob >= 0.65:
                    call = "MARKET LEAN"
                    confidence = "MEDIUM"
                else:
                    call = "PASS"
                    confidence = "LOW"

                rows.append({
                    "team": team,
                    "opponent": opponent,
                    "prob": prob,
                    "spread": spread_val,
                    "moneyline": ml,
                    "total": r.get("total"),
                    "start": r.get("start"),
                    "call": call,
                    "confidence": confidence,
                    "sportsbooks": r.get("sportsbooks"),
                })

            best = pd.DataFrame(rows)

            best = best[
                best["call"] != "PASS"
            ].sort_values(
                "prob",
                ascending=False
            )

            c1,c2,c3 = st.columns(3)

            with c1:
                kpi(
                    "Strong Leans",
                    len(best),
                    "65%+ market favorites",
                    "green"
                )

            with c2:
                kpi(
                    "High Confidence",
                    int(
                        (best["confidence"]=="HIGH").sum()
                    ),
                    "72%+ market probability"
                )

            with c3:
                top_team = (
                    best.iloc[0]["team"]
                    if len(best)
                    else "—"
                )
                kpi(
                    "Top Market Side",
                    top_team,
                    "Highest no-vig probability"
                )

            st.markdown(
                '<div class="section">NFL '
                '<span>BEST MARKET LEANS</span></div>',
                unsafe_allow_html=True
            )

            if best.empty:

                st.info(
                    "No NFL market leans currently meet the display threshold."
                )

            else:

                for _,r in best.iterrows():

                    prob_txt = (
                        f"{float(r.get('prob'))*100:.1f}%"
                    )

                    spread_txt = (
                        f"{float(r.get('spread')):+.1f}"
                        if pd.notna(r.get("spread"))
                        else "—"
                    )

                    ml = r.get("moneyline")

                    ml_txt = (
                        f"{int(ml):+d}"
                        if pd.notna(ml)
                        else "—"
                    )

                    st.html(textwrap.dedent(f"""
                    <div class="panel">
                      <div style="
                        display:grid;
                        grid-template-columns:2fr .8fr .8fr .8fr .9fr;
                        gap:12px;
                        align-items:center;
                      ">

                        <div>
                          <div class="panel-title">
                            {nfl_team_display(r.get('team'), 30)}
                          </div>
                          <div class="panel-sub">
                            vs {nfl_team_display(r.get('opponent'), 20)}
                          </div>
                        </div>

                        <div>
                          <div class="sub">WIN PROB</div>
                          <div class="team">
                            {prob_txt}
                          </div>
                        </div>

                        <div>
                          <div class="sub">SPREAD</div>
                          <div class="team">
                            {spread_txt}
                          </div>
                        </div>

                        <div>
                          <div class="sub">MONEYLINE</div>
                          <div class="team">
                            {ml_txt}
                          </div>
                        </div>

                        <div>
                          <div class="sub">HULK CALL</div>
                          <div class="team">
                            {safe(r.get('call'))}
                          </div>
                          <div class="sub">
                            {safe(r.get('confidence'))}
                          </div>
                        </div>

                      </div>
                    </div>
                    """))

            st.caption(
                "These are market-based NFL leans, not official Hulk NFL bets. "
                "No-vig sportsbook probabilities are kept separate from Hulk model predictions."
            )


    elif page=="NFL Matchups":

        title(
            "NFL",
            "NFL Matchups",
            "Full current-week matchup board with moneyline, spread, total and no-vig market probabilities."
        )

        if nfl_current_week.empty:

            st.info("No cached NFL current-week board available.")

        else:

            mx = nfl_current_week.copy()

            mx["start"] = pd.to_datetime(
                mx["start"],
                errors="coerce",
                utc=True
            )

            for col in [
                "away_moneyline",
                "home_moneyline",
                "away_spread",
                "home_spread",
                "total",
                "home_market_win_prob",
                "away_market_win_prob",
            ]:
                mx[col] = pd.to_numeric(
                    mx[col],
                    errors="coerce"
                )

            for _,r in mx.sort_values("start").iterrows():

                away_prob = r.get(
                    "away_market_win_prob"
                )

                home_prob = r.get(
                    "home_market_win_prob"
                )

                away_prob_txt = (
                    f"{float(away_prob)*100:.1f}%"
                    if pd.notna(away_prob)
                    else "—"
                )

                home_prob_txt = (
                    f"{float(home_prob)*100:.1f}%"
                    if pd.notna(home_prob)
                    else "—"
                )

                away_spread_txt = (
                    f"{float(r.get('away_spread')):+.1f}"
                    if pd.notna(r.get("away_spread"))
                    else "—"
                )

                home_spread_txt = (
                    f"{float(r.get('home_spread')):+.1f}"
                    if pd.notna(r.get("home_spread"))
                    else "—"
                )

                away_ml = r.get("away_moneyline")
                home_ml = r.get("home_moneyline")

                away_ml_txt = (
                    f"{int(away_ml):+d}"
                    if pd.notna(away_ml)
                    else "—"
                )

                home_ml_txt = (
                    f"{int(home_ml):+d}"
                    if pd.notna(home_ml)
                    else "—"
                )

                st.html(textwrap.dedent(f"""
                <div class="panel">

                  <div class="panel-title">
                    {nfl_matchup_html(
                        r.get('away_team'),
                        r.get('home_team'),
                        30
                    )}
                  </div>

                  <div class="panel-sub">
                    {local_date(r.get('start'))} • {local_time(r.get('start'))}
                  </div>

                  <div style="
                    display:grid;
                    grid-template-columns:1.2fr .8fr .8fr .8fr;
                    gap:10px;
                    margin-top:12px;
                  ">

                    <div>
                      <div class="sub">
                        {safe(r.get('away_team'))}
                      </div>
                      <div class="team">
                        ML {away_ml_txt}
                      </div>
                      <div class="team">
                        Spread {away_spread_txt}
                      </div>
                      <div class="team">
                        Win {away_prob_txt}
                      </div>
                    </div>

                    <div>
                      <div class="sub">
                        {safe(r.get('home_team'))}
                      </div>
                      <div class="team">
                        ML {home_ml_txt}
                      </div>
                      <div class="team">
                        Spread {home_spread_txt}
                      </div>
                      <div class="team">
                        Win {home_prob_txt}
                      </div>
                    </div>

                    <div>
                      <div class="sub">TOTAL</div>
                      <div class="team">
                        {num(r.get('total'))}
                      </div>
                    </div>

                    <div>
                      <div class="sub">SPORTSBOOKS</div>
                      <div class="team">
                        {safe(r.get('sportsbooks'))}
                      </div>
                    </div>

                  </div>

                </div>
                """))

            st.caption(
                "Market win probabilities are no-vig sportsbook-implied probabilities. "
                "They are not Hulk model probabilities."
            )

    elif page=="NFL Player Props":


        render_prop_intelligence("NFL")
        st.stop()
        title(
            "NFL",
            "NFL Player Props",
            "Cached sportsbook props ranked by current line, fair line and market movement."
        )

        if nfl_props.empty:

            st.info("No cached NFL player props available.")

        else:

            px = nfl_props.copy()

            # ------------------------------------------------
            # CLEAN DATA
            # ------------------------------------------------

            for col in [
                "line",
                "fair_line",
                "open_line",
                "book_odds",
                "fair_odds",
                "open_book_odds",
            ]:
                if col in px.columns:
                    px[col] = pd.to_numeric(
                        px[col],
                        errors="coerce"
                    )

            px["side"] = (
                px["side"]
                .astype(str)
                .str.lower()
                .str.strip()
            )

            px = px[
                px["side"].isin(["over","under"])
                & px["line"].notna()
            ].copy()

            # ------------------------------------------------
            # MARKET EDGE
            #
            # OVER:
            # fair line above offered line = favorable
            #
            # UNDER:
            # fair line below offered line = favorable
            # ------------------------------------------------

            px["market_edge"] = 0.0

            over_mask = px["side"].eq("over")
            under_mask = px["side"].eq("under")

            px.loc[over_mask, "market_edge"] = (
                px.loc[over_mask, "fair_line"]
                - px.loc[over_mask, "line"]
            )

            px.loc[under_mask, "market_edge"] = (
                px.loc[under_mask, "line"]
                - px.loc[under_mask, "fair_line"]
            )

            # Relative edge helps compare yards, receptions,
            # touchdowns, attempts, etc.
            px["edge_pct"] = (
                px["market_edge"]
                / px["line"].abs().clip(lower=1.0)
            ) * 100

            # Opening movement: current line minus opener.
            px["line_move"] = (
                px["line"] - px["open_line"]
            )

            # ------------------------------------------------
            # RESEARCH CALL
            # Not an official NFL player projection model.
            # ------------------------------------------------

            def prop_signal(row):

                edge = row.get("edge_pct")

                if pd.isna(edge):
                    return "NO EDGE"

                if edge >= 12:
                    return "BET"

                if edge >= 5:
                    return "WATCH"

                return "PASS"

            def prop_confidence(row):

                edge = row.get("edge_pct")

                if pd.isna(edge):
                    return "LOW"

                if edge >= 15:
                    return "HIGH"

                if edge >= 7:
                    return "MEDIUM"

                return "LOW"

            px["hulk_call"] = px.apply(
                prop_signal,
                axis=1
            )

            px["hulk_confidence"] = px.apply(
                prop_confidence,
                axis=1
            )

            # ------------------------------------------------
            # FILTERS
            # ------------------------------------------------

            players = sorted(
                px["player"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            stats = sorted(
                px["stat"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            c1,c2,c3,c4 = st.columns(4)

            with c1:
                player_filter = st.selectbox(
                    "Player",
                    ["All Players"] + players,
                    key="nfl_prop_player_v2"
                )

            with c2:
                stat_filter = st.selectbox(
                    "Prop",
                    ["All Props"] + stats,
                    format_func=lambda x:
                        x if x=="All Props"
                        else clean_prop_name(x),
                    key="nfl_prop_stat_v2"
                )

            with c3:
                side_filter = st.selectbox(
                    "Side",
                    ["Both","Over","Under"],
                    key="nfl_prop_side_v2"
                )

            with c4:
                call_filter = st.selectbox(
                    "Hulk Call",
                    ["All","BET","WATCH","PASS"],
                    key="nfl_prop_call_v2"
                )

            fx = px.copy()

            if player_filter != "All Players":
                fx = fx[
                    fx["player"] == player_filter
                ]

            if stat_filter != "All Props":
                fx = fx[
                    fx["stat"] == stat_filter
                ]

            if side_filter != "Both":
                fx = fx[
                    fx["side"]
                    == side_filter.lower()
                ]

            if call_filter != "All":
                fx = fx[
                    fx["hulk_call"]
                    == call_filter
                ]

            # Highest favorable market edge first.
            fx = fx.sort_values(
                [
                    "edge_pct",
                    "market_edge"
                ],
                ascending=False
            )

            # ------------------------------------------------
            # KPIs
            # ------------------------------------------------

            bets = int(
                (fx["hulk_call"]=="BET").sum()
            )

            watches = int(
                (fx["hulk_call"]=="WATCH").sum()
            )

            high = int(
                (
                    fx["hulk_confidence"]
                    =="HIGH"
                ).sum()
            )

            players_shown = int(
                fx["player"]
                .nunique()
            )

            k1,k2,k3,k4 = st.columns(4)

            with k1:
                kpi(
                    "Props",
                    f"{len(fx):,}",
                    "Filtered market"
                )

            with k2:
                kpi(
                    "Hulk BET",
                    bets,
                    "Largest market edges",
                    "green"
                )

            with k3:
                kpi(
                    "WATCH",
                    watches,
                    "Secondary edges",
                    "gold"
                )

            with k4:
                kpi(
                    "Players",
                    players_shown,
                    f"{high} high-confidence signals"
                )

            # ------------------------------------------------
            # BEST MARKET EDGES
            # ------------------------------------------------

            st.markdown(
                '<div class="section">PLAYER PROPS '
                '<span>HULK MARKET EDGE</span></div>',
                unsafe_allow_html=True
            )

            if fx.empty:

                st.info(
                    "No props match the selected filters."
                )

            else:

                for _,r in fx.head(100).iterrows():

                    player = safe(
                        r.get("player")
                    )

                    prop = nfl_prop_label(
                        r.get("stat")
                    )

                    side = str(
                        r.get("side","")
                    ).upper()

                    line = r.get("line")
                    fair = r.get("fair_line")
                    opener = r.get("open_line")
                    move = r.get("line_move")
                    edge = r.get("market_edge")
                    edge_pct = r.get("edge_pct")
                    odds = r.get("book_odds")

                    line_txt = (
                        f"{float(line):g}"
                        if pd.notna(line)
                        else "—"
                    )

                    fair_txt = (
                        f"{float(fair):g}"
                        if pd.notna(fair)
                        else "—"
                    )

                    opener_txt = (
                        f"{float(opener):g}"
                        if pd.notna(opener)
                        else "—"
                    )

                    move_txt = (
                        f"{float(move):+.1f}"
                        if pd.notna(move)
                        else "—"
                    )

                    edge_txt = (
                        f"{float(edge):+.1f}"
                        if pd.notna(edge)
                        else "—"
                    )

                    edge_pct_txt = (
                        f"{float(edge_pct):+.1f}%"
                        if pd.notna(edge_pct)
                        else "—"
                    )

                    odds_txt = (
                        prop_odds(odds)
                        if pd.notna(odds)
                        else "—"
                    )

                    away = safe(
                        r.get("away_team")
                    )

                    home = safe(
                        r.get("home_team")
                    )

                    matchup = (
                        nfl_matchup_html(
                            away,
                            home,
                            23
                        )
                        if away != "—"
                        and home != "—"
                        else "Matchup unavailable"
                    )

                    call = safe(
                        r.get("hulk_call")
                    )

                    conf = safe(
                        r.get("hulk_confidence")
                    )

                    st.html(textwrap.dedent(f"""
                    <div class="panel">
                      <div style="
                        display:grid;
                        grid-template-columns:
                          minmax(190px,2fr)
                          .9fr
                          .75fr
                          .75fr
                          .75fr
                          .8fr
                          .8fr
                          .9fr;
                        gap:12px;
                        align-items:center;
                      ">

                        <div>
                          <div class="panel-title">
                            {player}
                          </div>

                          <div class="panel-sub">
                            {matchup}
                          </div>

                          <div class="sub"
                               style="margin-top:5px;">
                            {prop}
                          </div>
                        </div>

                        <div>
                          <div class="sub">SIDE</div>
                          <div class="team">
                            {side}
                          </div>
                        </div>

                        <div>
                          <div class="sub">LINE</div>
                          <div class="team">
                            {line_txt}
                          </div>
                        </div>

                        <div>
                          <div class="sub">FAIR</div>
                          <div class="team">
                            {fair_txt}
                          </div>
                        </div>

                        <div>
                          <div class="sub">OPEN</div>
                          <div class="team">
                            {opener_txt}
                          </div>
                        </div>

                        <div>
                          <div class="sub">MOVE</div>
                          <div class="team">
                            {move_txt}
                          </div>
                        </div>

                        <div>
                          <div class="sub">EDGE</div>
                          <div class="team">
                            {edge_txt}
                          </div>
                          <div class="sub">
                            {edge_pct_txt}
                          </div>
                        </div>

                        <div>
                          <div class="sub">ODDS</div>
                          <div class="team">
                            {odds_txt}
                          </div>
                        </div>

                      </div>

                      <div style="
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                        margin-top:10px;
                        padding-top:9px;
                        border-top:1px solid rgba(255,255,255,.08);
                      ">

                        <div class="sub">
                          HULK CONFIDENCE:
                          <strong>{conf}</strong>
                        </div>

                        <div class="team">
                          {call}
                        </div>

                      </div>
                    </div>
                    """))

            st.caption(
                "Hulk Market Edge compares the cached sportsbook line with "
                "the market-derived fair line. Positive edge favors the displayed "
                "OVER or UNDER. This is market research, not an independently "
                "validated Hulk player projection."
            )

            st.caption(
                "Opening movement is shown separately and does not automatically "
                "create a BET. The by-bookmaker field is currently empty, so "
                "Sports Hulk does not claim sportsbook consensus on this page."
            )

            st.caption(
                "All props are read from Oracle cache. Reloading this page "
                "does not spend SportsGameOdds API entities."
            )

    elif page=="Survivor":

        title(
            "NFL",
            "Survivor",
            "Current-week survivor board using cached sportsbook-implied win probability."
        )

        if nfl_survivor.empty:

            st.info(
                "No cached NFL Survivor board is currently available."
            )

        else:

            sx = nfl_survivor.copy()

            sx["survivor_win_prob"] = pd.to_numeric(
                sx["survivor_win_prob"],
                errors="coerce"
            )

            sx["survivor_spread"] = pd.to_numeric(
                sx["survivor_spread"],
                errors="coerce"
            )

            sx["start"] = pd.to_datetime(
                sx["start"],
                errors="coerce",
                utc=True
            )

            sx = sx.sort_values(
                "survivor_win_prob",
                ascending=False
            )

            # ------------------------------------------------
            # USED TEAM TRACKER
            # ------------------------------------------------

            teams = sorted(
                sx["survivor_team"]
                .dropna()
                .unique()
                .tolist()
            )

            used_teams = st.multiselect(
                "Teams already used",
                teams,
                key="survivor_used_teams",
                placeholder="Select any teams you can no longer use..."
            )

            available = sx[
                ~sx["survivor_team"].isin(
                    used_teams
                )
            ].copy()

            # ------------------------------------------------
            # KPI CARDS
            # ------------------------------------------------

            best = (
                available.iloc[0]
                if len(available)
                else None
            )

            best_team = (
                safe(best.get("survivor_team"))
                if best is not None
                else "—"
            )

            best_prob = (
                f"{float(best.get('survivor_win_prob')) * 100:.1f}%"
                if best is not None
                and pd.notna(best.get("survivor_win_prob"))
                else "—"
            )

            a_grades = int(
                available[
                    "survivor_grade"
                ].astype(str).isin(
                    ["A+","A"]
                ).sum()
            )

            strong = int(
                (
                    available["survivor_win_prob"]
                    >= 0.70
                ).sum()
            )

            c1,c2,c3,c4 = st.columns(4)

            with c1:
                kpi(
                    "Best Available",
                    best_team,
                    "Highest market win probability",
                    "green"
                )

            with c2:
                kpi(
                    "Win Probability",
                    best_prob,
                    "No-vig sportsbook implied"
                )

            with c3:
                kpi(
                    "70%+ Options",
                    strong,
                    "Current week"
                )

            with c4:
                kpi(
                    "A / A+",
                    a_grades,
                    "Highest survivor grades"
                )

            # ------------------------------------------------
            # PRIMARY PICK
            # ------------------------------------------------

            if best is not None:

                opponent = (
                    best.get("away_team")
                    if best.get("survivor_team")
                    == best.get("home_team")
                    else best.get("home_team")
                )

                st.markdown(
                    '<div class="section">HULK SURVIVOR '
                    '<span>TOP AVAILABLE</span></div>',
                    unsafe_allow_html=True
                )

                st.html(textwrap.dedent(f"""
                <div class="panel">
                  <div style="
                    display:grid;
                    grid-template-columns:2fr .9fr .8fr .7fr;
                    gap:14px;
                    align-items:center;
                  ">

                    <div>
                      <div class="sub">TOP AVAILABLE TEAM</div>
                      <div class="panel-title">
                        {nfl_team_display(best.get('survivor_team'), 34)}
                      </div>
                      <div class="panel-sub">
                        vs {safe(opponent)}
                      </div>
                    </div>

                    <div>
                      <div class="sub">WIN PROB</div>
                      <div class="team">
                        {float(best.get('survivor_win_prob')) * 100:.1f}%
                      </div>
                    </div>

                    <div>
                      <div class="sub">SPREAD</div>
                      <div class="team">
                        {float(best.get('survivor_spread')):+.1f}
                      </div>
                    </div>

                    <div>
                      <div class="sub">GRADE</div>
                      <div class="team">
                        {safe(best.get('survivor_grade'))}
                      </div>
                    </div>

                  </div>
                </div>
                """))

            # ------------------------------------------------
            # FULL BOARD
            # ------------------------------------------------

            st.markdown(
                '<div class="section">CURRENT WEEK '
                '<span>SURVIVOR BOARD</span></div>',
                unsafe_allow_html=True
            )

            for _,r in available.iterrows():

                team = r.get("survivor_team")

                opponent = (
                    r.get("away_team")
                    if team == r.get("home_team")
                    else r.get("home_team")
                )

                prob = r.get("survivor_win_prob")

                prob_txt = (
                    f"{float(prob) * 100:.1f}%"
                    if pd.notna(prob)
                    else "—"
                )

                spr = r.get("survivor_spread")

                spread_txt = (
                    f"{float(spr):+.1f}"
                    if pd.notna(spr)
                    else "—"
                )

                grade = safe(
                    r.get("survivor_grade")
                )

                # Current-week decision only.
                # Do not pretend we have future-value modeling yet.
                if pd.isna(prob):
                    decision = "NO DATA"

                elif prob >= 0.75:
                    decision = "TOP PICK"

                elif prob >= 0.68:
                    decision = "STRONG"

                elif prob >= 0.62:
                    decision = "WATCH"

                else:
                    decision = "AVOID"

                st.html(textwrap.dedent(f"""
                <div class="panel">
                  <div style="
                    display:grid;
                    grid-template-columns:2.1fr .8fr .7fr .6fr .8fr;
                    gap:12px;
                    align-items:center;
                  ">

                    <div>
                      {nfl_team_display(team, 30)}
                      <div class="panel-sub">
                        vs {safe(opponent)}
                      </div>
                    </div>

                    <div>
                      <div class="sub">WIN PROB</div>
                      <div class="team">{prob_txt}</div>
                    </div>

                    <div>
                      <div class="sub">SPREAD</div>
                      <div class="team">{spread_txt}</div>
                    </div>

                    <div>
                      <div class="sub">GRADE</div>
                      <div class="team">{grade}</div>
                    </div>

                    <div>
                      <div class="sub">HULK CALL</div>
                      <div class="team">{decision}</div>
                    </div>

                  </div>
                </div>
                """))

            st.caption(
                "Win probabilities are no-vig sportsbook-implied market probabilities, "
                "not an official Hulk NFL model. Page refreshes read Oracle cache only "
                "and spend zero API credits."
            )

            st.caption(
                "Future-value strategy is the next Survivor layer. Current recommendations "
                "rank this week's safest available teams only."
            )

    elif page=="NFL Research":
        title("NFL","NFL Research","Historical NFL game master and matchup features.")
        if not nfl.empty:
            st.dataframe(
                nfl.sort_values(["season","week"],ascending=False).head(100),
                hide_index=True,
                use_container_width=True,
                height=700
            )


# ============================================================
# COLLEGE FOOTBALL SECTION
# ============================================================

elif mode=="🏟️ College Football":

    if page in {"CFB Dashboard","CFB Command Center"}:
        title(
            "COLLEGE FOOTBALL",
            "College Football Dashboard",
            "Current board, historical comps and research confidence."
        )

        high = 0
        if not cfb.empty:
            high = int(
                (cfb["research_confidence"].astype(str).str.upper()=="HIGH").sum()
            )

        cs=st.columns(4)
        with cs[0]: kpi("Games",len(cfb),"Current board")
        with cs[1]: kpi("High Confidence",high,"Research picks","green")
        with cs[2]: kpi("Historical Games","8,643","Completed-game master")
        with cs[3]: kpi("Walk-Forward","8,052","Historical comp tests")

        if not cfb.empty:
            cx=cfb.copy()
            now=pd.Timestamp.now(tz="UTC")
            cx=cx[cx["_dt"].isna()|(cx["_dt"]>=now-pd.Timedelta(hours=5))]
            cr={"HIGH":3,"MEDIUM":2,"LOW":1}
            cx["_rank"]=cx["research_confidence"].astype(str).str.upper().map(cr).fillna(0)
            cx=cx.sort_values(["_rank","_dt"],ascending=[False,True]).head(12)

            for _,r in cx.iterrows():
                st.markdown(f"""
                <div class="panel">
                  <div class="panel-title">{safe(r.get('away'))} @ {safe(r.get('home'))}</div>
                  <div class="panel-sub">{local_date(r.get('start'))} • {local_time(r.get('start'))}</div>
                  <div style="margin-top:8px;">
                    <span class="lean">{safe(r.get('research_lean'))}</span>
                    &nbsp; {confidence_html(r.get('research_confidence'))}
                  </div>
                  <div class="sub" style="margin-top:7px;">
                    Home win {pct(r.get('comp_home_win_prob'))} •
                    Projected margin {num(r.get('comp_projected_margin'))} •
                    Spread {spread(r.get('Home_spread'))} •
                    O/U {num(r.get('Total'))}
                  </div>
                </div>
                """,unsafe_allow_html=True)

    elif page=="CFB Best Bets":
        title(
            "COLLEGE FOOTBALL",
            "CFB Best Bets",
            "Highest-confidence research picks. Research stays separate from official sportsbook bets."
        )

        if not cfb.empty:
            cx=cfb[
                (cfb["model_status"].astype(str)=="RESEARCH_READY") &
                (cfb["research_confidence"].astype(str).str.upper()=="HIGH")
            ].copy()

            now=pd.Timestamp.now(tz="UTC")
            cx=cx[cx["_dt"].isna()|(cx["_dt"]>=now-pd.Timedelta(hours=5))]
            cx=cx.sort_values("_dt")

            for _,r in cx.head(20).iterrows():
                st.markdown(f"""
                <div class="panel">
                  <div class="panel-title">{safe(r.get('away'))} @ {safe(r.get('home'))}</div>
                  <div class="panel-sub">{local_date(r.get('start'))} • {local_time(r.get('start'))}</div>
                  <div style="margin-top:8px;">
                    <span class="lean">{safe(r.get('research_lean'))}</span>
                    &nbsp; {confidence_html(r.get('research_confidence'))}
                  </div>
                  <div class="sub" style="margin-top:7px;">
                    Historical win {pct(r.get('comp_home_win_prob'))} •
                    Edge vs line {num(r.get('model_vs_home_spread_edge'))}
                  </div>
                </div>
                """,unsafe_allow_html=True)

    elif page=="CFB Matchups":
        title("COLLEGE FOOTBALL","CFB Matchups","Full current college football board.")

        if not cfb.empty:

            st.markdown(
                '<div class="section">GAME LINES '
                '<span>SPREAD + OVER / UNDER</span></div>',
                unsafe_allow_html=True
            )

            for _,r in cfb.sort_values("_dt").head(60).iterrows():

                home_spread = r.get("Home_spread")
                total = r.get("Total")
                proj_total = r.get("comp_projected_total")

                spread_txt = (
                    f"{float(home_spread):+.1f}"
                    if pd.notna(home_spread)
                    else "—"
                )

                total_txt = (
                    f"{float(total):.1f}"
                    if pd.notna(total)
                    else "—"
                )

                proj_total_txt = (
                    f"{float(proj_total):.1f}"
                    if pd.notna(proj_total)
                    else "—"
                )

                if pd.notna(total) and pd.notna(proj_total):

                    total_edge = float(proj_total) - float(total)

                    if total_edge >= 3:
                        total_lean = "OVER"

                    elif total_edge <= -3:
                        total_lean = "UNDER"

                    else:
                        total_lean = "PASS"

                    total_edge_txt = f"{total_edge:+.1f}"

                else:
                    total_lean = "NO DATA"
                    total_edge_txt = "—"

                st.html(textwrap.dedent(f"""
                <div class="panel">

                  <div style="
                    display:grid;
                    grid-template-columns:2fr .8fr .8fr .8fr .9fr;
                    gap:12px;
                    align-items:center;
                  ">

                    <div>
                      <div class="panel-title">
                        {safe(r.get('away'))} @ {safe(r.get('home'))}
                      </div>
                      <div class="panel-sub">
                        {local_date(r.get('start'))} • {local_time(r.get('start'))}
                      </div>
                    </div>

                    <div>
                      <div class="sub">HOME SPREAD</div>
                      <div class="team">{spread_txt}</div>
                    </div>

                    <div>
                      <div class="sub">O/U</div>
                      <div class="team">{total_txt}</div>
                    </div>

                    <div>
                      <div class="sub">PROJECTED TOTAL</div>
                      <div class="team">{proj_total_txt}</div>
                    </div>

                    <div>
                      <div class="sub">TOTAL LEAN</div>
                      <div class="team">{total_lean}</div>
                      <div class="sub">{total_edge_txt}</div>
                    </div>

                  </div>

                </div>
                """))


        if not cfb.empty:
            cols=[
                "start","week","away","home",
                "research_lean","research_confidence",
                "Home_moneyline","Away_moneyline",
                "Home_spread","Total",
                "comp_home_win_prob",
                "comp_projected_margin",
                "model_vs_home_spread_edge"
            ]
            cols=[c for c in cols if c in cfb.columns]
            st.dataframe(cfb[cols],hide_index=True,use_container_width=True,height=700)

    elif page=="CFB Research":
        title("COLLEGE FOOTBALL","CFB Research","Historical calibration and comps.")

        cfb_cal=load_csv(CFB/"CFB_CALIBRATION.csv")
        if not cfb_cal.empty:
            st.dataframe(cfb_cal,hide_index=True,use_container_width=True)


# ============================================================
# PRIZEPICKS SECTION
# ============================================================

elif mode=="🟣 PrizePicks":

    title(
        "PRIZEPICKS",
        page,
        "PrizePicks line vs sportsbook consensus vs independent Hulk projection."
    )

    st.markdown("""
    <div class="panel">
      <div class="panel-title">PrizePicks feed validation still pending</div>
      <div class="panel-sub">
        No plays will appear until the PrizePicks line, sportsbook consensus and Hulk projection are all available.
      </div>
    </div>
    """,unsafe_allow_html=True)

    df=pd.DataFrame(columns=[
        "Player","Sport","Stat","PrizePicks Line",
        "Hulk Projection","Sportsbook Consensus",
        "Edge","More/Less","Confidence","Usage Trend"
    ])
    st.dataframe(df,hide_index=True,use_container_width=True)


# ============================================================
# COMING SOON SPORTS
# ============================================================

elif mode in {
    "🏀 NBA · Soon",
    "🏀 College Basketball · Soon",
    "🏒 NHL · Soon",
}:

    sport_name = mode.split(" · ")[0]

    title(
        "COMING SOON",
        sport_name,
        "This sport has a reserved place in Sports Hulk and will use the same clean workflow."
    )

    st.markdown("""
    <div class="panel">
      <div class="panel-title">Planned structure</div>
      <div class="panel-sub">
        Dashboard • Best Bets • Matchups • Player Props • Results • Research
      </div>
    </div>
    """,unsafe_allow_html=True)


st.markdown("---")
st.caption("SPORTS HULK V2.1 • Official model decisions and research context remain separate.")
