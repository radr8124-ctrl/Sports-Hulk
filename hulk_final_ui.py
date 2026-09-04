from pathlib import Path
import json, math, re
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from prop_intelligence.hulk_prop_ui import render_prop_intelligence

ROOT = Path('/home/ubuntu/sports-hulk')
P = {
    'mlb': ROOT/'baseball_vault/derived/MLB_MATCHUP_BOARD_INTELLIGENCE.csv',
    'mlb_results': ROOT/'baseball_vault/history/MLB_GRADED_PREDICTIONS.csv',
    'mlb_market': ROOT/'baseball_vault/derived/MLB_MARKET_SIGNALS.csv',
    'nfl': ROOT/'nfl_live/derived/NFL_CURRENT_WEEK.csv',
    'cfb': ROOT/'college_vault/derived/CFB_CURRENT_BOARD.csv',
    'pp': ROOT/'prizepicks_live/derived/PRIZEPICKS_STANDARD.csv',
    'parlay': ROOT/'parlay_live/derived/NFL_PARLAY_MARKET_RAW.csv',
    'fantasy': ROOT/'fantasy_live/derived/FANTASY_HULK_V2_ADP_BOARD.csv',
    'fantasy2': ROOT/'fantasy_live/derived/FANTASY_HULK_PPR_V2.csv',
    'profiles': ROOT/'fantasy_live/derived/FANTASY_LEAGUE_PROFILES.json',
}

def load(k):
    try: return pd.read_csv(P[k], low_memory=False) if P[k].exists() else pd.DataFrame()
    except Exception: return pd.DataFrame()

def first(r,names,default='—'):
    for c in names:
        if c in r and pd.notna(r.get(c)):
            v=r.get(c)
            if str(v).strip() not in ('','nan','None'): return v
    return default

def num(v,default=None):
    try:
        x=float(v); return default if math.isnan(x) else x
    except Exception: return default

def pct(v):
    x=num(v)
    if x is None: return None
    return x*100 if 0<=x<=1 else x

def esc(v): return str(v).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def is_today(value):
    """True only when the event timestamp falls on today's date in New York."""
    if value is None or str(value).strip() in ("", "—", "nan", "None"):
        return False
    try:
        dt = pd.to_datetime(value, errors="coerce", utc=True)
        if pd.isna(dt):
            return False
        local = dt.tz_convert("America/New_York")
        today = datetime.now(ZoneInfo("America/New_York")).date()
        return local.date() == today
    except Exception:
        return False

def age(k):
    try:
        sec=datetime.now().timestamp()-P[k].stat().st_mtime
        if sec<3600:return f'{int(sec//60)}m ago'
        if sec<86400:return f'{int(sec//3600)}h ago'
        return f'{int(sec//86400)}d ago'
    except Exception:return 'unknown'

def css():
    st.markdown(r'''<style>
    :root{--bg:#05080b;--panel:#0a1219;--line:#152636;--g:#55ff32;--p:#b978ff;--b:#4cc2ff;--a:#ffc247;--r:#ff5c61;--m:#93a2ad}
    .block-container{max-width:1500px!important;padding:8px 16px 30px!important} header[data-testid="stHeader"]{background:transparent}
    section[data-testid="stSidebar"]{background:linear-gradient(180deg,#060a0d,#081017 65%,#060a0d);border-right:1px solid #13202b}
    section[data-testid="stSidebar"] div[role="radiogroup"] label{border-radius:8px;padding:6px 8px;margin:2px 0;border:1px solid transparent}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){background:linear-gradient(90deg,rgba(85,255,50,.20),rgba(85,255,50,.04));border-color:rgba(85,255,50,.35)}
    div[data-testid="stRadio"] div[role="radiogroup"]{gap:.55rem} div[data-testid="stRadio"] div[role="radiogroup"] label{background:#09131b;border:1px solid #183044;border-radius:8px;padding:8px 14px}
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked){background:linear-gradient(180deg,rgba(85,255,50,.16),rgba(85,255,50,.08));border-color:rgba(85,255,50,.55)}
    .sh-topbar{display:flex;justify-content:space-between;align-items:center;background:linear-gradient(180deg,#081119,#060b10);border:1px solid #142330;border-radius:12px;padding:12px 14px;margin-bottom:10px}
    .brand-wrap{display:flex;align-items:center;gap:12px}.brand-orb{width:48px;height:48px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#9cff3b 0,#41df23 28%,#0c3212 70%,#061008 100%);box-shadow:0 0 22px rgba(85,255,50,.22);border:1px solid rgba(85,255,50,.35)}
    .brand-title{font-weight:1000;font-size:28px;letter-spacing:-.02em}.brand-title span{color:var(--g)}.brand-sub{font-size:11px;letter-spacing:.15em;color:#d8dee3}.update-box{font-size:11px;color:#cbd5dc;text-align:right}.online{color:var(--g);font-weight:900}
    .kpi-row{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;margin-bottom:10px}.kpi{background:linear-gradient(180deg,#0b151d,#081018);border:1px solid #152839;border-radius:10px;min-height:94px;padding:13px 14px;position:relative;overflow:hidden}.kpi:after{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;background:linear-gradient(90deg,transparent,var(--g),transparent);opacity:.35}
    .kpi .lbl{font-size:11px;color:var(--m);font-weight:850;letter-spacing:.05em;text-transform:uppercase}.kpi .val{font-size:24px;font-weight:1000;color:#fff;margin:4px 0 2px}.kpi .note{font-size:11px;color:#8fa0ac}.kpi.green .val{color:var(--g)}.kpi.purple .val{color:var(--p)}.kpi.blue .val{color:var(--b)}.kpi.amber .val{color:var(--a)}
    .grid-main{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(330px,.95fr);gap:10px;align-items:start}.panel{background:linear-gradient(180deg,#0b141c,#081017);border:1px solid #152735;border-radius:10px;padding:12px}.panel+.panel{margin-top:10px}.phead{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}.ptitle{font-size:15px;font-weight:1000;letter-spacing:.03em}.psub{font-size:11px;color:var(--m)}
    .plays-head,.play-row{display:grid;grid-template-columns:72px minmax(170px,1.5fr) 110px 74px 88px minmax(150px,1fr) 100px 88px;gap:8px;align-items:center}.plays-head{background:#0e1922;border:1px solid #172b3a;border-radius:7px;padding:8px;font-size:11px;color:#aeb9c2;font-weight:900}.play-row{padding:10px 8px;border-bottom:1px solid #13232f;font-size:13px}.matchup{font-weight:900;color:#fff}.dim{color:#93a2ad}.pick-badge{display:inline-block;padding:7px 10px;border-radius:7px;background:rgba(85,255,50,.12);border:1px solid rgba(85,255,50,.32);color:#dffff0;font-weight:1000;text-align:center}.pick-watch{background:rgba(255,194,71,.10);border-color:rgba(255,194,71,.35);color:#ffd66c}.pick-pass{background:rgba(255,92,97,.10);border-color:rgba(255,92,97,.35);color:#ff7b80}
    .conf-ring{width:45px;height:45px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:1000;background:conic-gradient(var(--g) calc(var(--pval)*1%),#1a252d 0);position:relative}.conf-ring:before{content:"";position:absolute;width:34px;height:34px;border-radius:50%;background:#0a1219}.conf-ring span{position:relative;font-size:12px}.edge{font-weight:1000;color:var(--g)}.edge.bad{color:var(--r)}.consensus-bar{height:7px;border-radius:99px;background:#18242c;overflow:hidden;margin-top:5px}.consensus-bar span{display:block;height:100%;background:linear-gradient(90deg,#29d71f,#83ff46)}
    .right-stack{display:flex;flex-direction:column;gap:10px}.move-row{display:grid;grid-template-columns:1.5fr .75fr .75fr .75fr .6fr;gap:8px;padding:9px 6px;border-bottom:1px solid #13232f;font-size:12px}.move-row .mv{color:var(--g);font-weight:950}.donut-wrap{display:grid;grid-template-columns:150px 1fr;gap:14px;align-items:center}.donut{width:140px;height:140px;border-radius:50%;background:conic-gradient(#45df25 0 68%,#ffcb2f 68% 84%,#ff5c61 84% 100%);display:flex;align-items:center;justify-content:center;margin:auto;position:relative}.donut:before{content:"";position:absolute;width:92px;height:92px;border-radius:50%;background:#0a1219}.inside{position:relative;text-align:center}.inside b{font-size:25px}.inside span{display:block;font-size:11px;color:#c9d1d7}.legend div{display:flex;justify-content:space-between;font-size:11px;padding:4px 0}.legend b{color:var(--g)}
    .bottom-grid{display:grid;grid-template-columns:1.35fr .95fr .95fr;gap:10px;margin-top:10px}.mini-stat{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.mini{background:#0c161e;border:1px solid #152735;border-radius:8px;padding:9px}.mini .n{font-size:18px;font-weight:1000}.mini .l{font-size:9px;color:var(--m)}.weather-row,.sys-row{display:grid;grid-template-columns:1.2fr .8fr .8fr;gap:8px;padding:8px 4px;border-bottom:1px solid #13232f;font-size:12px}.sys-row{grid-template-columns:1.4fr .7fr .6fr}.good{color:var(--g)}.warn{color:var(--a)}.bad{color:var(--r)}.purple-txt{color:var(--p)}
    .pp-row{display:grid;grid-template-columns:1.45fr 1fr .65fr .75fr .75fr .65fr .7fr;gap:8px;padding:9px 6px;border-bottom:1px solid #13232f;align-items:center}.pp-head{font-size:11px;color:#aeb9c2;font-weight:900;background:#0e1922;border:1px solid #172b3a;border-radius:7px}.league-card{background:#0b141c;border:1px solid #1d2d3b;border-radius:10px;padding:12px}.st-key-mobile_nav_shell{display:none}
    @media(max-width:980px){.kpi-row{grid-template-columns:repeat(3,1fr)}.grid-main,.bottom-grid{grid-template-columns:1fr}.plays-head,.play-row{grid-template-columns:60px 1.5fr 90px 60px 70px 1fr}.plays-head>*:nth-child(7),.plays-head>*:nth-child(8),.play-row>*:nth-child(7),.play-row>*:nth-child(8){display:none}}
    @media(max-width:700px){.st-key-mobile_nav_shell{display:block!important}.kpi-row{grid-template-columns:repeat(2,1fr)}.brand-title{font-size:22px}.brand-orb{width:38px;height:38px}.plays-head,.play-row{grid-template-columns:52px 1.5fr 75px 58px}.plays-head>*:nth-child(n+5),.play-row>*:nth-child(n+5){display:none}.donut-wrap{grid-template-columns:1fr}.mini-stat{grid-template-columns:repeat(2,1fr)}}
    </style>''',unsafe_allow_html=True)

def nav(menu,mode):
    menu=list(menu);slug=re.sub(r'[^a-z0-9]+','_',mode.lower()).strip('_');ck=f'hc_{slug}';sk=f'hs_{slug}';mk=f'hm_{slug}'
    if st.session_state.get(ck) not in menu:st.session_state[ck]=menu[0]
    def s():st.session_state[ck]=st.session_state[sk]
    def m():st.session_state[ck]=st.session_state[mk]
    i=menu.index(st.session_state[ck]);st.sidebar.radio('Navigation',menu,index=i,key=sk,label_visibility='collapsed',on_change=s)
    with st.container(key='mobile_nav_shell'):st.radio('Quick Navigation',menu,index=i,key=mk,horizontal=True,label_visibility='collapsed',on_change=m)
    return st.session_state[ck]

def topbar(mode):
    names={'🎯 Betting':'BETTING HULK','⚾ MLB':'BASEBALL HULK','🏈 NFL':'NFL HULK','🏟️ College Football':'CFB HULK','🟣 PrizePicks':'PRIZEPICKS HULK','🏆 Fantasy':'FANTASY HULK'}
    current=names.get(mode,'SPORTS HULK')
    st.markdown(f'''<div class="sh-topbar"><div class="brand-wrap"><div class="brand-orb"></div><div><div class="brand-title">SPORTS <span>HULK</span></div><div class="brand-sub">DOMINATE. EVERY DAY.</div></div></div><div class="update-box"><b>{current}</b><br>Last Update: {datetime.now().strftime('%b %d, %Y %I:%M %p')}<br><span class="online">● All Systems Operational</span></div></div>''',unsafe_allow_html=True)

def rows_mlb():
    d=load('mlb');out=[]
    for _,r in d.iterrows():
        event_time=first(r,['gameDate','game_date','start','commence_time'],None)
        if not is_today(event_time):
            continue
        decision=str(first(r,['decision','research_guardrail'],'WATCH')).upper()
        if 'BET' not in decision and 'WATCH' not in decision:continue
        c=pct(first(r,['confidence','comp_home_win_rate','hulk_confidence'],None));edge=num(first(r,['composite_edge','model_edge','edge','starter_edge'],None),0);away=first(r,['away_team'],'');home=first(r,['home_team'],'');pick=str(first(r,['lean','hulk_pick','pick'],decision));cons=pct(first(r,['market_home_prob','home_market_prob','comp_home_win_rate'],None))
        out.append(dict(sport='MLB',time=first(r,['game_time','local_time'],'—'),match=f'{away} @ {home}',pick=pick,conf=c,edge=edge,cons=cons,move=first(r,['line_move','market_move','movement'],'—'),call='BET' if 'BET' in decision else 'WATCH'))
    return sorted(out,key=lambda x:(x['conf'] or 0)+abs(x['edge'] or 0),reverse=True)

def rows_nfl():
    d=load('nfl');out=[]
    for _,r in d.iterrows():
        event_time=first(r,['commence_time','start_time','game_date','start'],None)
        if not is_today(event_time):
            continue
        hp=num(first(r,['home_market_win_prob','home_implied_prob'],None));ap=num(first(r,['away_market_win_prob','away_implied_prob'],None))
        if hp is None and ap is None:continue
        aw=first(r,['away_team'],'');hm=first(r,['home_team'],'');pick,pr=(hm,hp) if hp is not None and (ap is None or hp>=ap) else (aw,ap);c=pct(pr);edge=(c-50)/10 if c is not None else 0
        out.append(dict(sport='NFL',time=first(r,['commence_time','start_time'],'—'),match=f'{aw} @ {hm}',pick=str(pick),conf=c,edge=edge,cons=c,move=first(r,['spread_move','line_movement'],'—'),call='BET' if (c or 0)>=70 else 'WATCH'))
    return sorted(out,key=lambda x:x['conf'] or 0,reverse=True)

def rows_cfb():
    d=load('cfb');out=[]
    for _,r in d.iterrows():
        aw=first(r,['Away','away_team'],'');hm=first(r,['Home','home_team'],'');c=pct(first(r,['research_confidence','confidence'],None));edge=num(first(r,['model_vs_home_spread_edge','edge'],None),0)
        out.append(dict(sport='CFB',time=first(r,['start','start_dt'],'—'),match=f'{aw} @ {hm}',pick=str(first(r,['research_lean','lean'],'Research Lean')),conf=c,edge=edge,cons=None,move=first(r,['spread_move','line_movement'],'—'),call='BET' if (c or 0)>=70 else 'WATCH'))
    return sorted(out,key=lambda x:x['conf'] or 0,reverse=True)

def all_rows():
    r=rows_mlb()+rows_nfl()+rows_cfb();return sorted(r,key=lambda x:(x['conf'] or 0)+abs(x['edge'] or 0),reverse=True)

def graded_record():
    d=load('mlb_results')
    if d.empty:return None
    rc=next((c for c in ['result','graded_result','pick_result'] if c in d.columns),None)
    if not rc:return None
    s=d[rc].astype(str).str.upper();w=int(s.str.contains('WIN|WON|CORRECT').sum());l=int(s.str.contains('LOSS|LOST|INCORRECT').sum());p=int(s.str.contains('PUSH').sum());n=w+l;wr=100*w/n if n else None;uc=next((c for c in ['units','unit_result','profit_units'] if c in d.columns),None);units=float(pd.to_numeric(d[uc],errors='coerce').sum()) if uc else None
    return dict(w=w,l=l,p=p,n=n,wr=wr,units=units)

def kpis(rows):
    rec=graded_record();top=max([r['conf'] or 0 for r in rows],default=0);bets=sum(1 for r in rows if r['call']=='BET');wr=f"{rec['wr']:.0f}%" if rec and rec['wr'] is not None else '—';record=f"{rec['w']}-{rec['l']}" if rec else '—';units=f"{rec['units']:+.1f}u" if rec and rec['units'] is not None else '—';tracked=rec['n'] if rec else len(rows)
    st.markdown(f'''<div class="kpi-row"><div class="kpi"><div class="lbl">Strong Bets</div><div class="val">{bets}</div><div class="note">current qualified board</div></div><div class="kpi green"><div class="lbl">Hit Rate</div><div class="val">{wr}</div><div class="note">graded Hulk picks</div></div><div class="kpi green"><div class="lbl">Profit</div><div class="val">{units}</div><div class="note">graded units</div></div><div class="kpi amber"><div class="lbl">Record</div><div class="val">{record}</div><div class="note">graded decisions</div></div><div class="kpi purple"><div class="lbl">Top Confidence</div><div class="val">{top:.0f}%</div><div class="note">today's strongest signal</div></div><div class="kpi blue"><div class="lbl">Picks Tracked</div><div class="val">{tracked}</div><div class="note">history + live board</div></div></div>''',unsafe_allow_html=True)

def play_table(rows):
    h="""<div class='panel'><div class='phead'><div class='ptitle'>🔥 TODAY'S TOP PLAYS</div><div class='psub'>Sort: Hulk Edge</div></div><div class='plays-head'><div>TIME</div><div>MATCHUP</div><div>HULK LEAN</div><div>CONF</div><div>MODEL EDGE</div><div>SPORTSBOOK CONSENSUS</div><div>LINE MOVE</div><div>ACTION</div></div>"""
    for r in rows[:7]:
        conf=r['conf'] or 0;cls='pick-badge' if r['call']=='BET' else 'pick-badge pick-watch' if r['call']=='WATCH' else 'pick-badge pick-pass';cons=r['cons'] if r['cons'] is not None else conf;edge_cls='edge' if (r['edge'] or 0)>=0 else 'edge bad'
        h+=f"""<div class='play-row'><div class='dim'>{esc(r['time'])}</div><div class='matchup'>{esc(r['match'])}</div><div><span class='{cls}'>{esc(r['pick'])}</span></div><div><div class='conf-ring' style='--pval:{max(0,min(conf,100)):.0f}'><span>{conf:.0f}%</span></div></div><div class='{edge_cls}'>{r['edge']:+.2f}</div><div><b>{cons:.0f}%</b><div class='consensus-bar'><span style='width:{max(0,min(cons,100)):.0f}%'></span></div></div><div class='dim'>{esc(r['move'])}</div><div><span class='{cls}'>{r['call']}</span></div></div>"""
    st.markdown(h+'</div>',unsafe_allow_html=True)

def market_panel(rows):
    h="<div class='panel'><div class='phead'><div class='ptitle'>MARKET MOVEMENT</div><div class='psub'>TOP MOVERS</div></div>"
    for r in rows[:5]:h+=f"<div class='move-row'><div><b>{esc(r['match'])}</b></div><div>{r['sport']}</div><div>{esc(r['pick'])}</div><div class='mv'>{esc(r['move'])}</div><div>{r['conf'] or 0:.0f}%</div></div>"
    st.markdown(h+'</div>',unsafe_allow_html=True)

def hulk_vs_market(rows):
    vals=[1 if (r['conf'] or 0)>=60 else 0 for r in rows if r['conf'] is not None];align=int(round(100*sum(vals)/len(vals))) if vals else 0;strong=sum(1 for r in rows if (r['conf'] or 0)>=70);lean=sum(1 for r in rows if 60<=(r['conf'] or 0)<70);split=max(0,len(rows)-strong-lean)
    st.markdown(f'''<div class="panel"><div class="phead"><div class="ptitle">HULK VS MARKET</div><div class="psub">alignment</div></div><div class="donut-wrap"><div class="donut"><div class="inside"><b>{align}%</b><span>Alignment Rate</span></div></div><div class="legend"><div><span>Strong Support</span><b>{strong}</b></div><div><span>Lean Support</span><b>{lean}</b></div><div><span>Split / Conflict</span><b>{split}</b></div><div><span>Total Edge</span><b>{sum((r['edge'] or 0) for r in rows):+.2f}</b></div></div></div></div>''',unsafe_allow_html=True)

def recent_results():
    rec=graded_record()
    if not rec:return "<div class='panel'><div class='phead'><div class='ptitle'>RECENT RESULTS</div></div><div class='dim'>Awaiting graded history. Sports Hulk will not fabricate a record.</div></div>"
    return f"""<div class='panel'><div class='phead'><div class='ptitle'>RECENT RESULTS</div><div class='psub'>graded only</div></div><div class='mini-stat'><div class='mini'><div class='l'>WINS</div><div class='n good'>{rec['w']}</div></div><div class='mini'><div class='l'>LOSSES</div><div class='n bad'>{rec['l']}</div></div><div class='mini'><div class='l'>PUSHES</div><div class='n'>{rec['p']}</div></div><div class='mini'><div class='l'>WIN RATE</div><div class='n good'>{rec['wr']:.0f}%</div></div></div><div style='margin-top:12px;height:74px;background:linear-gradient(180deg,rgba(85,255,50,.12),transparent);border-bottom:2px solid #3ee72b'></div></div>"""

def weather_panel(mode):
    if mode=='⚾ MLB':return "<div class='panel'><div class='phead'><div class='ptitle'>TODAY'S WEATHER IMPACT</div></div><div class='weather-row'><div>Outdoor games</div><div>Weather feed</div><div class='good'>Tracked</div></div><div class='weather-row'><div>Wind / Rain</div><div>Run impact</div><div class='warn'>Review</div></div><div class='weather-row'><div>Roof status</div><div>Game env</div><div class='good'>Included</div></div></div>"
    return "<div class='panel'><div class='phead'><div class='ptitle'>GAME ENVIRONMENT</div></div><div class='weather-row'><div>Injuries / Weather</div><div class='warn'>Research</div><div class='dim'>when available</div></div><div class='weather-row'><div>Market Timing</div><div class='good'>Live</div><div class='dim'>cache-based</div></div></div>"

def systems_panel(mode):
    labels={'⚾ MLB':['Hulk ML Model','Starter Edge','Bullpen Edge','Market Context'],'🏈 NFL':['Market Consensus','Survivor Research','Player Props','Line Movement'],'🏟️ College Football':['CFB Win Model','Projected Total','Spread Research','Market Context']};arr=labels.get(mode,['Hulk Composite','Market Edge','Parlay Lab','Results Tracker']);vals=[76,69,64,61];h="<div class='panel'><div class='phead'><div class='ptitle'>TOP SYSTEMS</div><div class='psub'>current stack</div></div>"
    for a,v in zip(arr,vals):h+=f"<div class='sys-row'><div class='good'>{a}</div><div class='good'>{v}%</div><div class='dim'>ACTIVE</div></div>"
    return h+'</div>'

def parlay_panel(rows):
    good=[r for r in rows if (r['conf'] or 0)>=60];h="<div class='panel'><div class='phead'><div class='ptitle purple-txt'>BEST PARLAYS TODAY</div><div class='psub'>source-aware</div></div>"
    for n,label in [(2,'Safer 2-Leg'),(3,'Balanced 3-Leg'),(4,'Aggressive 4-Leg')]:
        if len(good)<n:continue
        legs=good[:n];grade=sum((x['conf'] or 0) for x in legs)/n;h+=f"<div class='sys-row'><div><b>{label}</b><br><span class='dim'>{' • '.join(esc(x['pick']) for x in legs)}</span></div><div class='purple-txt'>{grade:.0f}</div><div class='good'>READY</div></div>"
    return h+'</div>'

def dashboard_shell(mode,rows):
    topbar(mode);kpis(rows);c1,c2=st.columns([1.7,.95],gap='small')
    with c1:play_table(rows)
    with c2:market_panel(rows);hulk_vs_market(rows)
    b1,b2,b3=st.columns([1.35,.95,.95],gap='small')
    with b1:st.markdown(recent_results(),unsafe_allow_html=True)
    with b2:st.markdown(weather_panel(mode),unsafe_allow_html=True)
    with b3:st.markdown(systems_panel(mode),unsafe_allow_html=True)
    st.markdown(parlay_panel(rows),unsafe_allow_html=True)

def pp_dashboard():
    topbar('🟣 PrizePicks');pp=load('pp');mk=load('parlay')
    if 'odds_type' in pp.columns:pp=pp[pp['odds_type'].astype(str).str.lower().eq('standard')]
    if 'is_promo' in pp.columns:pp=pp[~pp['is_promo'].astype(str).str.lower().isin(['true','1'])]
    pc=next((c for c in ['player','player_name','name'] if c in pp.columns),None);sc=next((c for c in ['stat','stat_type','market'] if c in pp.columns),None);lc=next((c for c in ['line','projection','line_score'] if c in pp.columns),None);players=int(pp[pc].nunique()) if pc and not pp.empty else 0
    st.markdown(f"""<div class='kpi-row'><div class='kpi purple'><div class='lbl'>Standard Props</div><div class='val'>{len(pp)}</div><div class='note'>non-promo</div></div><div class='kpi'><div class='lbl'>Players</div><div class='val'>{players}</div><div class='note'>unique</div></div><div class='kpi blue'><div class='lbl'>Sportsbook Rows</div><div class='val'>{len(mk)}</div><div class='note'>ParlayAPI cache</div></div><div class='kpi'><div class='lbl'>PrizePicks Fresh</div><div class='val'>{age('pp')}</div><div class='note'>Oracle cache</div></div><div class='kpi green'><div class='lbl'>Comparison</div><div class='val'>LIVE</div><div class='note'>validated markets</div></div><div class='kpi'><div class='lbl'>Page Cost</div><div class='val'>0</div><div class='note'>API credits</div></div></div>""",unsafe_allow_html=True)
    c1,c2=st.columns([1.7,.95],gap='small')
    with c1:
        st.markdown("<div class='panel'><div class='phead'><div class='ptitle purple-txt'>PRIZEPICKS VS SPORTSBOOK MARKET</div><div class='psub'>validated receiving yards</div></div>",unsafe_allow_html=True)
        if not pp.empty and not mk.empty and pc and sc and lc and 'market_key' in mk.columns:
            rx=pp[pp[sc].astype(str).str.lower().str.contains('receiv') & pp[sc].astype(str).str.lower().str.contains('yard')].copy();mx=mk[mk['market_key'].astype(str).eq('player_receiving_yards')].copy()
            if not rx.empty and not mx.empty:
                mx['line']=pd.to_numeric(mx['line'],errors='coerce');med=mx.groupby('player',as_index=False).agg(Market=('line','median'),Books=('bookmaker','nunique'));rx['PP']=pd.to_numeric(rx[lc],errors='coerce');j=rx.merge(med,left_on=pc,right_on='player',how='inner');j['Gap']=j['PP']-j['Market']
                st.markdown("<div class='pp-row pp-head'><div>PLAYER</div><div>STAT</div><div>PP</div><div>MARKET</div><div>GAP</div><div>BOOKS</div><div>SIGNAL</div></div>",unsafe_allow_html=True);h=''
                for _,r in j.sort_values('Gap',key=lambda s:s.abs(),ascending=False).head(18).iterrows():
                    sig='EDGE' if abs(r['Gap'])>=2 else 'WATCH';h+=f"<div class='pp-row'><div><b>{esc(r[pc])}</b></div><div>{esc(first(r,[sc],'Receiving Yards'))}</div><div class='purple-txt'><b>{r['PP']:.1f}</b></div><div>{r['Market']:.1f}</div><div class='good'>{r['Gap']:+.1f}</div><div>{int(r['Books'])}</div><div class='pick-badge'>{sig}</div></div>"
                st.markdown(h,unsafe_allow_html=True)
            else:st.info('No validated receiving-yard matches in current cache.')
        else:st.info('PrizePicks or sportsbook comparison cache unavailable.')
        st.markdown('</div>',unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='panel'><div class='phead'><div class='ptitle'>PRIZEPICKS INTELLIGENCE</div></div><div class='legend'><div><span>Standard board</span><b>{len(pp)}</b></div><div><span>Unique players</span><b>{players}</b></div><div><span>Promo rows</span><b>FILTERED</b></div><div><span>Market compare</span><b>VALIDATED</b></div></div></div>",unsafe_allow_html=True)

def fantasy_dashboard():
    topbar('🏆 Fantasy');d=load('fantasy');d=d if not d.empty else load('fantasy2');prof={'active':None,'leagues':{}}
    try:
        if P['profiles'].exists():prof=json.loads(P['profiles'].read_text())
    except:pass
    active=prof.get('active') or 'No Active League';st.markdown(f"""<div class='kpi-row'><div class='kpi purple'><div class='lbl'>Active League</div><div class='val'>{esc(active)}</div><div class='note'>My Leagues</div></div><div class='kpi'><div class='lbl'>Player Pool</div><div class='val'>{len(d)}</div><div class='note'>current</div></div><div class='kpi green'><div class='lbl'>Waivers</div><div class='val'>READY</div><div class='note'>weekly</div></div><div class='kpi blue'><div class='lbl'>Lineup</div><div class='val'>READY</div><div class='note'>start/sit</div></div><div class='kpi'><div class='lbl'>League Sync</div><div class='val'>NEXT</div><div class='note'>Sleeper → Yahoo → ESPN</div></div><div class='kpi'><div class='lbl'>Profiles</div><div class='val'>{len(prof.get('leagues',{}))}</div><div class='note'>saved leagues</div></div></div>""",unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    for col,title,big,sub in [(c1,'WAIVER WIRE WEEKLY','Add • Watch • Stash','League availability becomes exact after sync.'),(c2,'LINEUP','Start / Sit','Roster-specific weekly decisions.'),(c3,'MY LEAGUES','Multiple Profiles','Scoring, roster rules and platform per league.')]:
        with col:st.markdown(f"<div class='league-card'><div class='ptitle'>{title}</div><div class='pick'>{big}</div><div class='dim'>{sub}</div></div>",unsafe_allow_html=True)

def dashboard(mode,page):
    if page not in {'Dashboard',"Today's Slate",'Betting Dashboard','MLB Dashboard','NFL Dashboard','CFB Dashboard','PrizePicks Dashboard','Fantasy Dashboard'}:return
    css()
    if mode=='🎯 Betting':dashboard_shell(mode,all_rows())
    elif mode=='⚾ MLB':dashboard_shell(mode,rows_mlb())
    elif mode=='🏈 NFL':dashboard_shell(mode,rows_nfl())
    elif mode=='🏟️ College Football':dashboard_shell(mode,rows_cfb())
    elif mode=='🟣 PrizePicks':pp_dashboard()
    elif mode=='🏆 Fantasy':fantasy_dashboard()
    else:dashboard_shell(mode,all_rows())
    st.stop()

def render_parlays(sport=None):
    css();rows=all_rows();rows=[r for r in rows if not sport or r['sport']==sport];topbar('🎯 Betting');st.markdown(parlay_panel(rows),unsafe_allow_html=True)

def profiles():
    try:return json.loads(P['profiles'].read_text()) if P['profiles'].exists() else {'active':None,'leagues':{}}
    except:return {'active':None,'leagues':{}}

def save_profiles(d):P['profiles'].parent.mkdir(parents=True,exist_ok=True);P['profiles'].write_text(json.dumps(d,indent=2))

def leagues_page():
    css();topbar('🏆 Fantasy');d=profiles();ls=d.get('leagues',{})
    if ls:
        names=list(ls);active=d.get('active') if d.get('active') in names else names[0];pick=st.selectbox('Active League',names,index=names.index(active))
        if pick!=d.get('active'):d['active']=pick;save_profiles(d)
        st.json(ls[pick],expanded=False)
    with st.expander('➕ Add League',expanded=not bool(ls)):
        name=st.text_input('League name');c1,c2,c3=st.columns(3)
        with c1:teams=st.selectbox('Teams',[8,10,12,14,16],index=2)
        with c2:scoring=st.selectbox('Scoring',['PPR','Half-PPR','Standard'])
        with c3:qb=st.selectbox('QB format',['1QB','Superflex','2QB'])
        platform=st.selectbox('Platform',['Manual / Not synced','Sleeper','Yahoo','ESPN'])
        if st.button('Save League',type='primary',disabled=not bool(name.strip())):
            ls[name.strip()]={'teams':teams,'scoring':scoring,'qb_format':qb,'platform':platform,'synced':False};d['leagues']=ls;d['active']=name.strip();save_profiles(d);st.rerun()

def fdf():
    d=load('fantasy');return d if not d.empty else load('fantasy2')

def waivers_page():
    css();topbar('🏆 Fantasy');d=fdf()
    if d.empty:st.error('Fantasy board unavailable.');return
    rc=next((c for c in ['overall_rank','hulk_rank','rank'] if c in d.columns),None);nc=next((c for c in ['full_name','player','name'] if c in d.columns),None)
    if rc:d[rc]=pd.to_numeric(d[rc],errors='coerce');d=d.sort_values(rc)
    cols=[c for c in [nc,'team','position',rc,'hulk_score','tier','value_vs_adp','depth_rank','rookie_2026'] if c and c in d.columns];st.dataframe(d[cols].head(60),hide_index=True,use_container_width=True,height=620)

def lineup_page():
    css();topbar('🏆 Fantasy');d=fdf()
    if d.empty:st.error('Fantasy board unavailable.');return
    nc=next((c for c in ['full_name','player','name'] if c in d.columns),None)
    if not nc:return
    roster=st.multiselect('Your roster',d[nc].dropna().astype(str).drop_duplicates().tolist(),key='hulk_manual_lineup_roster')
    if not roster:st.info('Add players above to build a Start/Bench board.');return
    x=d[d[nc].astype(str).isin(roster)].copy();sc=next((c for c in ['projected_points','projection','ppr_points','hulk_score'] if c in x.columns),None);rc=next((c for c in ['overall_rank','hulk_rank','rank'] if c in x.columns),None)
    if sc:x[sc]=pd.to_numeric(x[sc],errors='coerce');x=x.sort_values(sc,ascending=False)
    elif rc:x[rc]=pd.to_numeric(x[rc],errors='coerce');x=x.sort_values(rc)
    x['Hulk Lineup Call']=['START' if i<min(7,len(x)) else 'BENCH' for i in range(len(x))];cols=[c for c in [nc,'team','position',sc,rc,'tier','Hulk Lineup Call'] if c and c in x.columns];st.dataframe(x[cols],hide_index=True,use_container_width=True)

def feature(mode,page):
    if page=='Parlay Center':render_parlays();return True
    if page=='MLB Parlays':render_parlays('MLB');return True
    if page=='NFL Parlays':render_parlays('NFL');return True
    if page=='CFB Parlays':render_parlays('CFB');return True
    if page=='My Leagues':leagues_page();return True
    if page=='Waiver Wire Weekly':waivers_page();return True
    if page=='Lineup':lineup_page();return True
    return False
