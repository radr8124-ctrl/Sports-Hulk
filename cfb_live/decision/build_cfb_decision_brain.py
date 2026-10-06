#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import itertools, json, math
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
CFB=ROOT/"cfb_live"
DEC=CFB/"decision"
DEC.mkdir(parents=True,exist_ok=True)

FUSION=CFB/"markets/current/CFB_GAME_MARKET_FUSION.csv"
TEAM_HIST=CFB/"history/CFB_TEAM_GAME_HISTORY.csv"
GAMES=CFB/"derived/CFB_GAMES_CURRENT.csv"
RANKINGS=CFB/"derived/CFB_RANKINGS_CURRENT.csv"
LEGACY=ROOT/"college_vault/meta/CFB_MODEL_SUMMARY.json"

TEAM_CONTEXT=DEC/"CFB_TEAM_CONTEXT.csv"
TEAM_RESEARCH=DEC/"CFB_TEAM_RESEARCH.csv"
DECISIONS=DEC/"CFB_GAME_DECISIONS.csv"
FINALISTS=DEC/"CFB_GAME_FINALISTS.csv"
PARLAYS=DEC/"CFB_PARLAYS_TODAY.csv"
SUMMARY=DEC/"CFB_DECISION_SUMMARY.json"

NOW=pd.Timestamp.now(tz="UTC")
MIN_CURRENT_GAMES=3
FINALIST_HORIZON_HOURS=72

def read(path):
    try: return pd.read_csv(path,low_memory=False)
    except Exception: return pd.DataFrame()

def num(v):
    try:
        x=float(v)
        return None if math.isnan(x) else x
    except Exception: return None

def key(v):
    x=num(v)
    return str(int(x)) if x is not None and float(x).is_integer() else str(v or "").strip()

def truth(v): return str(v).lower() in {"true","1","yes"}

def implied(price):
    p=num(price)
    if p is None: return None
    if p<0: return (-p)/((-p)+100.0)
    if p>0: return 100.0/(p+100.0)
    return 0.5

def clamp(x): return max(0.0,min(100.0,float(x)))

def hours_to(v):
    dt=pd.to_datetime(v,utc=True,errors="coerce",format="mixed")
    return None if pd.isna(dt) else (dt-NOW).total_seconds()/3600.0

th=read(TEAM_HIST)
ctx_rows=[]
if not th.empty:
    th["_dt"]=pd.to_datetime(th["start"],utc=True,errors="coerce")
    th=th.sort_values("_dt")
    for team_id,g in th.groupby(th["team_id"].map(key)):
        margins=pd.to_numeric(g["margin"],errors="coerce")
        wins=pd.to_numeric(g["win"],errors="coerce")
        scores=pd.to_numeric(g["score"],errors="coerce")
        allowed=pd.to_numeric(g["opponent_score"],errors="coerce")
        last=g.iloc[-1]
        ctx_rows.append({
            "team_id":team_id,
            "team":last.get("team",""),
            "team_name":last.get("team_name",""),
            "current_games":len(g),
            "current_wins":int(wins.eq(1).sum()),
            "current_losses":int(wins.eq(0).sum()),
            "current_win_rate":wins.mean(),
            "current_avg_margin":margins.mean(),
            "current_l3_margin":margins.tail(3).mean(),
            "current_l5_margin":margins.tail(5).mean(),
            "current_points_for":scores.mean(),
            "current_points_against":allowed.mean(),
            "finalist_eligible":len(g)>=MIN_CURRENT_GAMES,
        })
context=pd.DataFrame(ctx_rows)
context.to_csv(TEAM_CONTEXT,index=False)
ctx={key(r["team_id"]):r.to_dict() for _,r in context.iterrows()} if not context.empty else {}

rank=read(RANKINGS)
rank_map={}
if not rank.empty:
    ap=rank[rank["poll"].astype(str).str.contains("AP",case=False,na=False)]
    ap=ap[ap["current_season_match"].map(truth)]
    for _,r in ap.iterrows(): rank_map[key(r.get("team_id"))]=num(r.get("rank"))

games=read(GAMES)
research=[]
if not games.empty:
    for _,g in games.iterrows():
        if truth(g.get("completed")): continue
        aid,hid=key(g.get("away_team_id")),key(g.get("home_team_id"))
        a,h=ctx.get(aid,{}),ctx.get(hid,{})
        research.append({
            "event_id":g.get("event_id"),"start":g.get("start"),"game_date":g.get("game_date"),
            "away_team_id":aid,"away_team":g.get("away_team"),"away_team_name":g.get("away_team_name"),
            "home_team_id":hid,"home_team":g.get("home_team"),"home_team_name":g.get("home_team_name"),
            "away_current_games":a.get("current_games",0),"home_current_games":h.get("current_games",0),
            "away_avg_margin":a.get("current_avg_margin"),"home_avg_margin":h.get("current_avg_margin"),
            "away_l3_margin":a.get("current_l3_margin"),"home_l3_margin":h.get("current_l3_margin"),
            "away_ap_rank":rank_map.get(aid),"home_ap_rank":rank_map.get(hid),
            "research_status":"CURRENT_SEASON_RESEARCH",
        })
research_df=pd.DataFrame(research)
research_df.to_csv(TEAM_RESEARCH,index=False)

fusion=read(FUSION)
rows=[]
if not fusion.empty:
    for _,r in fusion.iterrows():
        aid,hid=key(r.get("away_team_id")),key(r.get("home_team_id"))
        sid=key(r.get("selection_team_id"))
        if sid==aid: oid=hid
        elif sid==hid: oid=aid
        else: oid=""
        s,o=ctx.get(sid,{}),ctx.get(oid,{})
        sg=int(num(s.get("current_games")) or 0); og=int(num(o.get("current_games")) or 0)
        market=str(r.get("market_canonical","")).upper()
        books=int(num(r.get("sportsbook_count")) or 0); providers=int(num(r.get("provider_count")) or 0)
        support=implied(r.get("median_price_american"))
        form=(num(s.get("current_avg_margin"))-num(o.get("current_avg_margin"))) if num(s.get("current_avg_margin")) is not None and num(o.get("current_avg_margin")) is not None else None
        l3=(num(s.get("current_l3_margin"))-num(o.get("current_l3_margin"))) if num(s.get("current_l3_margin")) is not None and num(o.get("current_l3_margin")) is not None else None
        elo=num(r.get("elo_edge")); srs=num(r.get("srs_edge"))
        srank=rank_map.get(sid); orank=rank_map.get(oid)
        score=35.0
        if books>=10: score+=18
        elif books>=5: score+=14
        elif books>=3: score+=9
        elif books>=2: score+=5
        if providers>=2: score+=5
        if support is not None and support>=0.60: score+=4
        if sg>=MIN_CURRENT_GAMES and og>=MIN_CURRENT_GAMES: score+=10
        if form is not None:
            if form>=8: score+=12
            elif form>=4: score+=8
            elif form>0: score+=4
            elif form<=-8: score-=10
            elif form<0: score-=5
        if l3 is not None:
            if l3>=6: score+=6
            elif l3<=-6: score-=5
        if elo is not None:
            if elo>=80: score+=5
            elif elo<=-80: score-=5
        if srs is not None:
            if srs>=6: score+=5
            elif srs<=-6: score-=5
        if srank and (not orank or srank<orank): score+=3
        score=clamp(score)
        direction="SUPPORT" if form is not None and form>0 and (elo is None or elo>-100) and (srs is None or srs>-8) else "MIXED"
        h=hours_to(r.get("start_dt"))
        if h is None or h < -1: decision="CLOSED"
        elif h>FINALIST_HORIZON_HOURS: decision="EARLY_MARKET_WATCH"
        elif sg<MIN_CURRENT_GAMES or og<MIN_CURRENT_GAMES: decision="INSUFFICIENT_CURRENT_HISTORY"
        elif market!="MONEYLINE": decision="MARKET_RESEARCH"
        elif books>=3 and direction=="SUPPORT" and score>=74: decision="QUALIFIED_RESEARCH"
        elif score>=64: decision="MARKET_LEAN"
        else: decision="WATCH"
        out=r.to_dict()
        out.update({
            "hours_to_start":h,"raw_market_support":support,
            "selected_current_games":sg,"opponent_current_games":og,
            "selected_current_margin":s.get("current_avg_margin"),"opponent_current_margin":o.get("current_avg_margin"),
            "current_margin_edge":form,"selected_l3_margin":s.get("current_l3_margin"),"opponent_l3_margin":o.get("current_l3_margin"),
            "l3_margin_edge":l3,"selected_current_ap_rank":srank,"opponent_current_ap_rank":orank,
            "context_direction":direction,"evidence_score":score,"decision":decision,
            "probability_claim":False,"spread_model_validated":False,"totals_model_validated":False,
        })
        rows.append(out)

dec=pd.DataFrame(rows)
if not dec.empty:
    dec=dec.sort_values(["evidence_score","sportsbook_count"],ascending=[False,False])
dec.to_csv(DECISIONS,index=False)

final=dec[dec["decision"].eq("QUALIFIED_RESEARCH")].copy() if not dec.empty else pd.DataFrame()
if not final.empty:
    final=final.sort_values("evidence_score",ascending=False).drop_duplicates(["game_key","market_canonical"],keep="first").head(20)
final.to_csv(FINALISTS,index=False)

parlay_rows=[]
if len(final)>=2:
    legs=final.to_dict("records")
    for a,b in itertools.combinations(legs,2):
        if a.get("game_key")==b.get("game_key"): continue
        parlay_rows.append({
            "leg1_game":a.get("game_key"),"leg1_selection":a.get("selection_canonical"),"leg1_market":a.get("market_canonical"),"leg1_line":a.get("line"),"leg1_score":a.get("evidence_score"),
            "leg2_game":b.get("game_key"),"leg2_selection":b.get("selection_canonical"),"leg2_market":b.get("market_canonical"),"leg2_line":b.get("line"),"leg2_score":b.get("evidence_score"),
            "evidence_score":(float(a.get("evidence_score"))+float(b.get("evidence_score")))/2.0,
            "status":"RESEARCH_COMBO","probability_claim":False,"payout_claim":False,
        })
parlays=pd.DataFrame(parlay_rows)
if not parlays.empty: parlays=parlays.sort_values("evidence_score",ascending=False).head(30)
parlays.to_csv(PARLAYS,index=False)

legacy={}
try: legacy=json.loads(LEGACY.read_text())
except Exception: pass
summary={
    "generated_at":datetime.now(timezone.utc).isoformat(),
    "team_context_rows":len(context),"team_research_rows":len(research_df),
    "game_decisions":len(dec),"game_finalists":len(final),"parlays":len(parlays),
    "minimum_current_games":MIN_CURRENT_GAMES,
    "legacy_historical_games":legacy.get("historical_games"),
    "legacy_walkforward_games":legacy.get("walkforward_games"),
    "legacy_winner_accuracy":legacy.get("winner_accuracy"),
    "historical_model_used_as_calibration_context":True,
    "market_is_probability":False,"hulk_score_is_probability":False,
    "moneyline_finalist_lane":True,"spread_model_validated":False,"totals_model_validated":False,
    "college_player_props":False,"college_prizepicks":False,"college_fantasy":False,
    "automatic_model_adjustment":False,"parlay_payout_claim":False,
}
SUMMARY.write_text(json.dumps(summary,indent=2,sort_keys=True))
print("TEAM CONTEXT:",len(context))
print("TEAM RESEARCH:",len(research_df))
print("GAME DECISIONS:",len(dec))
print("GAME FINALISTS:",len(final))
print("PARLAYS:",len(parlays))
print("DECISION COUNTS:",dec["decision"].value_counts().to_dict() if not dec.empty else {})
print("RESULT: CFB_DECISION_BRAIN_READY")
