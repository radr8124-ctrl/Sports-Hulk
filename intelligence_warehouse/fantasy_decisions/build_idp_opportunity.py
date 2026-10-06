#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json, math
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
ROLE=ROOT/"intelligence_warehouse"/"features"/"PLAYER_ROLE_SIGNALS_CURRENT.csv"
AV=ROOT/"intelligence_warehouse"/"availability"/"AVAILABILITY_CURRENT.csv"
LOAD=ROOT/"intelligence_warehouse"/"schedule"/"TEAM_SCHEDULE_LOAD_CURRENT.csv"
OUTDIR=ROOT/"intelligence_warehouse"/"fantasy_decisions"
OUT=OUTDIR/"FANTASY_IDP_OPPORTUNITY_CURRENT.csv"
RECEIPT=OUTDIR/"FANTASY_IDP_RECEIPT.json"
NOW=datetime.now(timezone.utc)
IDP_POS={"LB","ILB","OLB","DE","DL","DT","NT","CB","DB","S","FS","SS","EDGE"}

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

def group_pos(pos):
    p=clean(pos).upper()
    if p in {"LB","ILB","OLB","EDGE"}: return "LB"
    if p in {"DE","DL","DT","NT"}: return "DL"
    if p in {"CB","DB","S","FS","SS"}: return "DB"
    return "OTHER"

def main():
    r=pd.read_csv(ROLE,low_memory=False)
    r=r[(r["sport"].astype(str).str.upper()=="NFL") & r["position"].astype(str).str.upper().isin(IDP_POS)].copy()
    av=pd.read_csv(AV,low_memory=False) if AV.exists() else pd.DataFrame()
    ld=pd.read_csv(LOAD,low_memory=False) if LOAD.exists() else pd.DataFrame()
    amap={}
    if not av.empty:
        for x in av.to_dict("records"):
            amap[(clean(x.get("sport")).upper(),clean(x.get("player_key")))]=x
    lmap={}
    if not ld.empty:
        for x in ld[ld["sport"].astype(str).str.upper()=="NFL"].to_dict("records"):
            lmap[clean(x.get("team")).upper()]=x

    rows=[]
    for x in r.to_dict("records"):
        key=("NFL",clean(x.get("player_key")))
        a=amap.get(key,{})
        l=lmap.get(clean(x.get("team")).upper(),{})
        status=clean(a.get("status_normalized")).upper()
        snap=num(x.get("snap_pct"))
        change=num(x.get("snap_pct_change"))
        role=clean(x.get("signal")).upper()
        sample=num(x.get("sample_marker")) or 0

        score=0.0
        if snap is not None: score+=snap*65
        if change is not None: score+=clamp(change*55,-20,20)
        if role=="ROLE_UP": score+=15
        elif role=="ROLE_DOWN": score-=15
        elif role=="STEADY": score+=4
        if sample>=4: score+=5
        elif sample<2: score-=8
        if status in {"OUT","IR","PUP","SUSPENDED"}: score-=60
        elif status in {"DOUBTFUL"}: score-=25
        elif status in {"QUESTIONABLE","DAY_TO_DAY"}: score-=8
        score=round(clamp(score,-50,100),2)

        if status in {"OUT","IR","PUP","SUSPENDED"}:
            tier="INACTIVE_NO_START"
        elif score>=78:
            tier="IDP_CORE_USAGE"
        elif score>=62:
            tier="IDP_STRONG_USAGE"
        elif score>=48:
            tier="IDP_WATCH"
        else:
            tier="IDP_DEEP_ONLY"

        rows.append({
            "generated_at":NOW.isoformat(),"sport":"NFL","player":x.get("player"),
            "player_key":x.get("player_key"),"team":x.get("team"),"position":x.get("position"),
            "idp_group":group_pos(x.get("position")),"snap_pct":x.get("snap_pct"),
            "snap_pct_change":x.get("snap_pct_change"),"recent_role_value":x.get("recent_value"),
            "season_role_value":x.get("season_value"),"role_delta":x.get("role_delta"),
            "role_signal":x.get("signal"),"role_sample_marker":x.get("sample_marker"),
            "availability_status":a.get("status_normalized"),"injury_type":a.get("injury_type"),
            "next_opponent":l.get("next_opponent"),"next_side":l.get("next_side"),
            "rest_days":l.get("rest_days"),"idp_usage_score":score,"idp_usage_tier":tier,
            "fantasy_points_projection_available":False,
            "waiver_market_coverage_available":False,
            "score_is_probability":False,"automatic_model_adjustment":False,
        })
    out=pd.DataFrame(rows)
    if not out.empty:
        out=out.sort_values(["idp_group","idp_usage_score","snap_pct"],ascending=[True,False,False],na_position="last")
    out.to_csv(OUT,index=False)
    receipt={
        "generated_at":NOW.isoformat(),"rows":int(len(out)),
        "rows_by_group":out["idp_group"].value_counts().to_dict() if not out.empty else {},
        "tier_counts":out["idp_usage_tier"].value_counts().to_dict() if not out.empty else {},
        "fantasy_points_projection_available":False,
        "waiver_market_coverage_available":False,
        "basis":"DEFENSIVE_SNAP_SHARE_ROLE_CHANGE_AVAILABILITY",
        "score_is_probability":False,"automatic_model_adjustment":False,
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True))
    print(json.dumps(receipt,indent=2,sort_keys=True))
if __name__=="__main__":main()
