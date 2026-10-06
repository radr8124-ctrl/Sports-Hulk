#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json, math
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
FM=ROOT/"intelligence_warehouse"/"fantasy_market"/"FANTASY_MARKET_CONTEXT_CURRENT.csv"
FUT=ROOT/"intelligence_warehouse"/"schedule"/"FUTURE_SCHEDULE_DIFFICULTY.csv"
LOAD=ROOT/"intelligence_warehouse"/"schedule"/"TEAM_SCHEDULE_LOAD_CURRENT.csv"
OUTDIR=ROOT/"intelligence_warehouse"/"fantasy_decisions"
OUT=OUTDIR/"FANTASY_DEFENSE_STREAMING_CURRENT.csv"
RECEIPT=OUTDIR/"FANTASY_DEFENSE_STREAMING_RECEIPT.json"
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
    f=pd.read_csv(FM,low_memory=False)
    fut=pd.read_csv(FUT,low_memory=False)
    load=pd.read_csv(LOAD,low_memory=False)

    dst=f[(f["sport"].astype(str).str.upper()=="NFL") &
          (f["position"].astype(str).str.upper().isin(["DEF","DST","D/ST"]))].copy()
    market={}
    for r in dst.to_dict("records"):
        market[clean(r.get("team")).upper()]=r

    fs=fut[fut["sport"].astype(str).str.upper()=="NFL"].copy()
    ld=load[load["sport"].astype(str).str.upper()=="NFL"].copy()
    loadmap={clean(r.get("team")).upper():r for r in ld.to_dict("records")}

    rows=[]
    league_avg=pd.to_numeric(fs["opponent_strength_avg"],errors="coerce").mean()
    for r in fs.to_dict("records"):
        team=clean(r.get("team")).upper()
        m=market.get(team,{})
        l=loadmap.get(team,{})
        opp_avg=num(r.get("opponent_strength_avg"))
        schedule_score=50.0
        if opp_avg is not None and league_avg is not None:
            # Lower opponent-strength values are treated as the easier future schedule in this dataset.
            schedule_score=clamp(50+(league_avg-opp_avg)*1.4,0,100)
        add_rank=num(m.get("add_rank_24h"))
        net=num(m.get("net_adds_24h"))
        market_score=None
        if m:
            market_score=0.0
            if add_rank is not None: market_score+=max(0,45-add_rank)*1.4
            if net is not None and net>0: market_score+=min(math.log10(net+1)*8,28)
            elif net is not None and net<0: market_score-=min(math.log10(abs(net)+1)*6,24)
            market_score=clamp(market_score,0,100)
        rest=num(l.get("rest_days"))
        fatigue=num(l.get("fatigue_load_score")) or 0
        weekly_score=schedule_score
        if clean(l.get("next_side")).upper()=="HOME": weekly_score+=4
        if rest is not None and rest>=8: weekly_score+=3
        weekly_score-=min(fatigue,15)*0.4
        if market_score is not None: weekly_score+=0.18*(market_score-50)
        weekly_score=round(clamp(weekly_score,0,100),2)

        hold_score=round(clamp(schedule_score + (0.12*(market_score-50) if market_score is not None else 0),0,100),2)

        if weekly_score>=72:
            weekly_tier="STRONG_STREAM"
        elif weekly_score>=60:
            weekly_tier="STREAM"
        elif weekly_score>=48:
            weekly_tier="MATCHUP_DEPENDENT"
        else:
            weekly_tier="AVOID_STREAM"

        if hold_score>=72:
            hold_tier="MULTI_WEEK_HOLD"
        elif hold_score>=60:
            hold_tier="FUTURE_HOLD"
        elif hold_score>=48:
            hold_tier="SHORT_HOLD"
        else:
            hold_tier="ROTATE_OUT"

        rows.append({
            "generated_at":NOW.isoformat(),"sport":"NFL","team":team,
            "dst_player":m.get("player") if m else f"{team} D/ST",
            "next_opponent":l.get("next_opponent"),"next_side":l.get("next_side"),
            "rest_days":l.get("rest_days"),"fatigue_load_score":l.get("fatigue_load_score"),
            "next_5_sequence":l.get("next_5_sequence"),"next_opponents":r.get("next_opponents"),
            "opponent_strength_avg":r.get("opponent_strength_avg"),
            "future_schedule_signal":r.get("future_schedule_signal"),
            "market_data_available":bool(m),"adds_24h":m.get("adds_24h"),
            "add_rank_24h":m.get("add_rank_24h"),"drops_24h":m.get("drops_24h"),
            "net_adds_24h":m.get("net_adds_24h"),"market_activity_signal":m.get("market_activity_signal"),
            "schedule_research_score":round(schedule_score,2),
            "market_research_score":round(market_score,2) if market_score is not None else None,
            "weekly_stream_score":weekly_score,"weekly_stream_tier":weekly_tier,
            "multiweek_hold_score":hold_score,"multiweek_hold_tier":hold_tier,
            "score_is_probability":False,"automatic_model_adjustment":False,
        })

    out=pd.DataFrame(rows).sort_values(["weekly_stream_score","multiweek_hold_score"],ascending=False)
    out.to_csv(OUT,index=False)
    receipt={
        "generated_at":NOW.isoformat(),"rows":int(len(out)),
        "market_covered_teams":int(out["market_data_available"].sum()),
        "weekly_tier_counts":out["weekly_stream_tier"].value_counts().to_dict(),
        "hold_tier_counts":out["multiweek_hold_tier"].value_counts().to_dict(),
        "score_is_probability":False,"automatic_model_adjustment":False,
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True))
    print(json.dumps(receipt,indent=2,sort_keys=True))
if __name__=="__main__":main()
