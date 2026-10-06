#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json, math
import pandas as pd
ROOT=Path("/home/ubuntu/sports-hulk")
FM=ROOT/"intelligence_warehouse"/"fantasy_market"/"FANTASY_MARKET_CONTEXT_CURRENT.csv"
OUTDIR=ROOT/"intelligence_warehouse"/"fantasy_decisions"
FAAB=OUTDIR/"FANTASY_FAAB_RESEARCH_CURRENT.csv"
RECEIPT=OUTDIR/"FANTASY_FAAB_RECEIPT.json"
NOW=datetime.now(timezone.utc)
def clean(v):
    if v is None:return ""
    try:
        if pd.isna(v):return ""
    except Exception:pass
    return str(v).strip()
def num(v):
    try:
        x=float(v); return None if math.isnan(x) else x
    except Exception:return None
def clamp(x,a,b): return max(a,min(b,x))
def main():
    d=pd.read_csv(FM,low_memory=False)
    d=d[d["sport"].astype(str).str.upper().isin(["NFL","NBA"])].copy()
    d=d[~d["position"].astype(str).str.upper().isin(["DEF","D/ST","DST","K"])].copy()
    rows=[]
    for r in d.to_dict("records"):
        status=clean(r.get("availability_status")).upper()
        immediate=status not in {"OUT","IR","PUP","SUSPENDED"}
        add_rank=num(r.get("add_rank_24h")); add7=num(r.get("add_rank_168h"))
        net24=num(r.get("net_adds_24h")) or 0
        role=clean(r.get("role_signal")).upper(); role_score=num(r.get("role_score")) or 0
        score=0.0
        if add_rank is not None: score+=max(0,45-add_rank)*1.35
        if add7 is not None: score+=max(0,30-add7)*0.55
        if net24>0: score+=min(math.log10(net24+1)*7,25)
        elif net24<0: score-=min(math.log10(abs(net24)+1)*5,18)
        if role=="ROLE_UP": score+=18
        elif role=="ROLE_DOWN": score-=18
        elif role=="STEADY": score+=3
        score+=clamp(role_score/5,-10,10)
        if status=="QUESTIONABLE": score-=5
        elif status=="DOUBTFUL": score-=12
        if not immediate: score-=50
        score=round(clamp(score,-50,100),2)
        if not immediate:
            priority="STASH_NOT_STANDARD_ADD"; low=high=0
        elif score>=75: priority="AGGRESSIVE_ADD"; low,high=18,30
        elif score>=60: priority="STRONG_ADD"; low,high=10,18
        elif score>=45: priority="TARGET_ADD"; low,high=5,10
        elif score>=30: priority="WATCH_ADD"; low,high=2,5
        else: priority="LOW_PRIORITY"; low,high=0,2
        if immediate and role=="ROLE_UP" and add_rank is not None and add_rank<=10:
            high=min(35,high+5)
        rows.append({
            "generated_at":NOW.isoformat(),"sport":clean(r.get("sport")).upper(),
            "player":r.get("player"),"player_key":r.get("player_key"),"team":r.get("team"),
            "position":r.get("position"),"availability_status":r.get("availability_status"),
            "market_activity_signal":r.get("market_activity_signal"),"adds_24h":r.get("adds_24h"),
            "add_rank_24h":r.get("add_rank_24h"),"net_adds_24h":r.get("net_adds_24h"),
            "add_rank_168h":r.get("add_rank_168h"),"role_signal":r.get("role_signal"),
            "role_delta":r.get("role_delta"),"role_score":r.get("role_score"),
            "waiver_research_score":score,"waiver_priority":priority,
            "suggested_faab_low_pct":low,"suggested_faab_high_pct":high,
            "faab_basis":"100_PERCENT_SEASON_BUDGET",
            "trend_feed_rank_limited":bool(r.get("trend_feed_rank_limited")),
            "score_is_probability":False,"faab_is_market_prediction":False,
            "automatic_model_adjustment":False,
        })
    out=pd.DataFrame(rows)
    if not out.empty:
        out=out.sort_values(["sport","waiver_research_score","add_rank_24h"],ascending=[True,False,True],na_position="last")
    out.to_csv(FAAB,index=False)
    receipt={"generated_at":NOW.isoformat(),"rows":int(len(out)),
        "rows_by_sport":out["sport"].value_counts().to_dict() if not out.empty else {},
        "priority_counts":out["waiver_priority"].value_counts().to_dict() if not out.empty else {},
        "defense_and_kicker_excluded":True,"injured_stash_separated":True,
        "faab_basis":"100_PERCENT_SEASON_BUDGET","faab_is_market_prediction":False,
        "score_is_probability":False,"automatic_model_adjustment":False}
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True))
    print(json.dumps(receipt,indent=2,sort_keys=True))
if __name__=="__main__": main()
