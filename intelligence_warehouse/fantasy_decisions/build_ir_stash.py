#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json, math
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
RET=ROOT/"intelligence_warehouse"/"availability"/"RETURN_WATCH.csv"
FM=ROOT/"intelligence_warehouse"/"fantasy_market"/"FANTASY_MARKET_CONTEXT_CURRENT.csv"
ROLE=ROOT/"intelligence_warehouse"/"features"/"PLAYER_ROLE_SIGNALS_CURRENT.csv"
OUTDIR=ROOT/"intelligence_warehouse"/"fantasy_decisions"
OUT=OUTDIR/"FANTASY_IR_STASH_CURRENT.csv"
RECEIPT=OUTDIR/"FANTASY_IR_STASH_RECEIPT.json"
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
    r=pd.read_csv(RET,low_memory=False)
    f=pd.read_csv(FM,low_memory=False) if FM.exists() else pd.DataFrame()
    roles=pd.read_csv(ROLE,low_memory=False) if ROLE.exists() else pd.DataFrame()
    fmap={}
    if not f.empty:
        for x in f.to_dict("records"):
            fmap[(clean(x.get("sport")).upper(),clean(x.get("player_key")))]=x
    rolemap={}
    if not roles.empty:
        for x in roles.to_dict("records"):
            rolemap[(clean(x.get("sport")).upper(),clean(x.get("player_key")))]=x

    rows=[]
    for x in r.to_dict("records"):
        sport=clean(x.get("sport")).upper()
        if sport not in {"NFL","NBA","NHL"}: continue
        status=clean(x.get("status_normalized")).upper()
        stash_flag=bool(x.get("stash_research_signal"))
        if status not in {"IR","PUP","OUT","DAY_TO_DAY","QUESTIONABLE","DOUBTFUL"} and not stash_flag:
            continue
        key=(sport,clean(x.get("player_key")))
        fm=fmap.get(key,{})
        rr=rolemap.get(key,{})
        days=num(x.get("days_to_return"))
        window=clean(x.get("return_window")).upper()
        disagreement=bool(x.get("source_disagreement"))
        role_sig=clean(rr.get("signal")).upper()
        role_score=num(rr.get("role_score")) or 0
        add_rank=num(fm.get("add_rank_24h"))
        net_adds=num(fm.get("net_adds_24h")) or 0

        score=0.0
        if stash_flag: score+=25
        if window=="TODAY_OR_NEXT_DAY": score+=30
        elif window=="WITHIN_3_DAYS": score+=25
        elif window=="WITHIN_7_DAYS": score+=18
        elif window=="WITHIN_14_DAYS": score+=12
        elif window in {"WITHIN_30_DAYS","WITHIN_4_WEEKS"}: score+=6
        elif window=="UNKNOWN": score-=8
        if days is not None:
            score+=clamp(18-days, -10, 18)
        if role_sig=="ROLE_UP": score+=15
        elif role_sig=="STEADY": score+=4
        elif role_sig=="ROLE_DOWN": score-=10
        score+=clamp(role_score/6,-8,8)
        if add_rank is not None: score+=max(0,25-add_rank)*0.7
        if net_adds>0: score+=min(math.log10(net_adds+1)*4,12)
        elif net_adds<0: score-=min(math.log10(abs(net_adds)+1)*3,10)
        if disagreement: score-=15
        if status in {"DAY_TO_DAY","QUESTIONABLE"}: score-=4
        score=round(clamp(score,-30,100),2)

        if disagreement:
            tier="REVIEW_SOURCE_CONFLICT"
        elif score>=70:
            tier="HIGH_PRIORITY_STASH"
        elif score>=50:
            tier="STRONG_STASH"
        elif score>=30:
            tier="WATCH_STASH"
        else:
            tier="LOW_PRIORITY_STASH"

        rows.append({
            "generated_at":NOW.isoformat(),"sport":sport,"player":x.get("player"),
            "player_key":x.get("player_key"),"team":x.get("team"),"position":x.get("position"),
            "status":status,"injury_type":x.get("injury_type"),"return_date":x.get("return_date"),
            "days_to_return":x.get("days_to_return"),"return_window":x.get("return_window"),
            "source_count":x.get("source_count"),"source_disagreement":disagreement,
            "stash_source_signal":stash_flag,"role_signal":rr.get("signal"),"role_score":rr.get("role_score"),
            "add_rank_24h":fm.get("add_rank_24h"),"net_adds_24h":fm.get("net_adds_24h"),
            "stash_research_score":score,"stash_tier":tier,
            "score_is_probability":False,"return_date_is_guarantee":False,
            "automatic_model_adjustment":False,
        })
    out=pd.DataFrame(rows)
    if not out.empty:
        out=out.sort_values(["sport","stash_research_score"],ascending=[True,False])
    out.to_csv(OUT,index=False)
    receipt={
        "generated_at":NOW.isoformat(),"rows":int(len(out)),
        "rows_by_sport":out["sport"].value_counts().to_dict() if not out.empty else {},
        "tier_counts":out["stash_tier"].value_counts().to_dict() if not out.empty else {},
        "source_conflict_rows":int(out["source_disagreement"].fillna(False).astype(bool).sum()) if not out.empty else 0,
        "score_is_probability":False,"return_date_is_guarantee":False,
        "automatic_model_adjustment":False,
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True))
    print(json.dumps(receipt,indent=2,sort_keys=True))
if __name__=="__main__": main()
