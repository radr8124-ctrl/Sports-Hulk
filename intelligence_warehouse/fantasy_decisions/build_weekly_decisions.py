#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json, math
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
MATCH=ROOT/"intelligence_warehouse"/"defensive_pressure"/"PLAYER_DEFENSIVE_MATCHUP_CURRENT.csv"
MARKET=ROOT/"intelligence_warehouse"/"fantasy_market"/"FANTASY_MARKET_CONTEXT_CURRENT.csv"
FUTURE=ROOT/"intelligence_warehouse"/"schedule"/"FUTURE_SCHEDULE_DIFFICULTY.csv"
ROLE=ROOT/"intelligence_warehouse"/"features"/"PLAYER_ROLE_SIGNALS_CURRENT.csv"
OUTDIR=ROOT/"intelligence_warehouse"/"fantasy_decisions"
OUT=OUTDIR/"FANTASY_WEEKLY_DECISIONS_CURRENT.csv"
RECEIPT=OUTDIR/"FANTASY_WEEKLY_DECISIONS_RECEIPT.json"
NOW=datetime.now(timezone.utc)

OFF_POS={"QB","RB","WR","TE"}

def clean(v):
    if v is None:return ""
    try:
        if pd.isna(v):return ""
    except Exception:pass
    return str(v).strip()

def num(v):
    try:
        x=float(v)
        return None if math.isnan(x) else x
    except Exception:
        return None

def clamp(x,a,b):
    return max(a,min(b,x))

def role_points(signal):
    s=clean(signal).upper()
    if s=="ROLE_UP": return 18
    if s=="ROLE_DOWN": return -18
    if s=="STEADY": return 2
    return -5

def matchup_points(context):
    c=clean(context).upper()
    return {
        "STRONG_PERMISSIVE_PROFILE":24,
        "PERMISSIVE_LEAN":12,
        "NEUTRAL_PRESSURE_PROFILE":0,
        "MIXED_PRESSURE_PROFILE":-2,
        "SUPPRESSIVE_LEAN":-12,
        "STRONG_SUPPRESSIVE_PROFILE":-24,
        "NO_UPCOMING_MODELED_GAME":-35,
    }.get(c,0)

def opportunity_points(context):
    c=clean(context).upper()
    if "EXPANDING_ROLE_WITH_ENVIRONMENT_SUPPORT" in c:return 15
    if "EXPANDING_ROLE" in c:return 10
    if "LIMITED_ROLE_SAMPLE" in c:return -12
    if "AVAILABILITY_LIMITED_CONTEXT" in c:return -10
    if "NO_UPCOMING_MODELED_GAME" in c:return -30
    return 0

def schedule_points(signal):
    s=clean(signal).upper()
    if s=="EASIER_THAN_LEAGUE_BASELINE":return 12
    if s=="HARDER_THAN_LEAGUE_BASELINE":return -12
    if s=="BALANCED":return 0
    return -3

def main():
    m=pd.read_csv(MATCH,low_memory=False)
    market=pd.read_csv(MARKET,low_memory=False) if MARKET.exists() else pd.DataFrame()
    future=pd.read_csv(FUTURE,low_memory=False) if FUTURE.exists() else pd.DataFrame()
    roles=pd.read_csv(ROLE,low_memory=False) if ROLE.exists() else pd.DataFrame()

    n=m[
        (m["sport"].astype(str).str.upper()=="NFL")
        & m["position"].astype(str).str.upper().isin(OFF_POS)
    ].copy()

    mmap={}
    if not market.empty:
        for r in market[market["sport"].astype(str).str.upper()=="NFL"].to_dict("records"):
            mmap[clean(r.get("player_key"))]=r

    fmap={}
    if not future.empty:
        for r in future[future["sport"].astype(str).str.upper()=="NFL"].to_dict("records"):
            fmap[clean(r.get("team")).upper()]=r

    rmap={}
    if not roles.empty:
        for r in roles[
            roles["sport"].astype(str).str.upper().eq("NFL")
            & roles["position"].astype(str).str.upper().isin(OFF_POS)
        ].to_dict("records"):
            rmap[clean(r.get("player_key"))]=r

    rows=[]
    for r in n.to_dict("records"):
        pkey=clean(r.get("player_key"))
        team=clean(r.get("team")).upper()
        mk=mmap.get(pkey,{})
        fs=fmap.get(team,{})
        rr=rmap.get(pkey,{})
        status=clean(mk.get("availability_status")).upper()

        weekly=50.0
        weekly+=role_points(r.get("role_signal"))
        weekly+=matchup_points(r.get("defensive_pressure_context"))
        weekly+=opportunity_points(r.get("opportunity_context"))

        add_rank=num(mk.get("add_rank_24h"))
        net=num(mk.get("net_adds_24h"))
        if add_rank is not None and add_rank<=25: weekly+=8
        if net is not None and net>0: weekly+=min(math.log10(net+1)*2.5,8)
        elif net is not None and net<0: weekly-=min(math.log10(abs(net)+1)*2.0,7)

        if status in {"OUT","IR","PUP","SUSPENDED"}:
            weekly=-50
        elif status=="DOUBTFUL":
            weekly-=30
        elif status in {"QUESTIONABLE","DAY_TO_DAY"}:
            weekly-=10

        weekly=round(clamp(weekly,-50,100),2)

        if status in {"OUT","IR","PUP","SUSPENDED"}:
            weekly_tier="INACTIVE"
        elif weekly>=78:
            weekly_tier="CORE_START_RESEARCH"
        elif weekly>=65:
            weekly_tier="START_LEAN"
        elif weekly>=52:
            weekly_tier="FLEX_START"
        elif weekly>=40:
            weekly_tier="MATCHUP_DEPENDENT"
        else:
            weekly_tier="SIT_CAUTION"

        ros=50.0
        ros+=role_points(r.get("role_signal"))
        ros+=schedule_points(fs.get("future_schedule_signal"))
        role_delta=num(r.get("role_delta"))
        if role_delta is not None:
            ros+=clamp(role_delta*8,-12,12)
        if add_rank is not None and add_rank<=25: ros+=6
        if status in {"OUT","IR","PUP","SUSPENDED"}: ros-=15
        elif status in {"QUESTIONABLE","DAY_TO_DAY"}: ros-=4
        ros=round(clamp(ros,0,100),2)

        if ros>=75: ros_tier="ROS_RISER"
        elif ros>=60: ros_tier="ROS_HOLD_PLUS"
        elif ros>=45: ros_tier="ROS_HOLD"
        else: ros_tier="ROS_CAUTION"

        reasons=[]
        rs=clean(r.get("role_signal")).upper()
        if rs=="ROLE_UP": reasons.append("role expanding")
        elif rs=="ROLE_DOWN": reasons.append("role declining")
        mp=clean(r.get("defensive_pressure_context")).upper()
        if "PERMISSIVE" in mp: reasons.append("favorable matchup")
        elif "SUPPRESSIVE" in mp: reasons.append("tough matchup")
        opp=clean(r.get("opportunity_context")).upper()
        if "ENVIRONMENT_SUPPORT" in opp: reasons.append("environment supports role")
        if add_rank is not None and add_rank<=25: reasons.append("strong add demand")
        sched=clean(fs.get("future_schedule_signal")).upper()
        if sched=="EASIER_THAN_LEAGUE_BASELINE": reasons.append("easier future schedule")
        elif sched=="HARDER_THAN_LEAGUE_BASELINE": reasons.append("harder future schedule")
        if status in {"QUESTIONABLE","DAY_TO_DAY","DOUBTFUL"}: reasons.append(status.lower())

        rows.append({
            "generated_at":NOW.isoformat(),
            "sport":"NFL",
            "player":r.get("player"),
            "player_key":pkey,
            "team":team,
            "position":clean(r.get("position")).upper(),
            "opponent":r.get("opponent"),
            "role_signal":r.get("role_signal"),
            "role_delta":r.get("role_delta"),
            "role_metric":rr.get("role_metric"),
            "recent_role_value":rr.get("recent_value"),
            "season_role_value":rr.get("season_value"),
            "snap_pct":rr.get("snap_pct"),
            "role_sample_marker":rr.get("sample_marker"),
            "opportunity_context":r.get("opportunity_context"),
            "defensive_pressure_context":r.get("defensive_pressure_context"),
            "volume_pressure_signal":r.get("volume_pressure_signal"),
            "production_pressure_signal":r.get("production_pressure_signal"),
            "availability_status":mk.get("availability_status"),
            "add_rank_24h":mk.get("add_rank_24h"),
            "net_adds_24h":mk.get("net_adds_24h"),
            "future_schedule_signal":fs.get("future_schedule_signal"),
            "next_opponents":fs.get("next_opponents"),
            "weekly_raw_score":weekly,
            "weekly_research_score":weekly,
            "weekly_tier":weekly_tier,
            "ros_raw_score":ros,
            "ros_research_score":ros,
            "ros_tier":ros_tier,
            "research_reasons":" · ".join(reasons[:5]),
            "personal_roster_context_used":False,
            "fantasy_points_projection_used":False,
            "score_is_probability":False,
            "automatic_model_adjustment":False,
        })

    out=pd.DataFrame(rows)
    if not out.empty:
        active=~out["weekly_tier"].astype(str).eq("INACTIVE")

        out["recent_role_value"]=pd.to_numeric(
            out["recent_role_value"],
            errors="coerce",
        )
        out["snap_pct"]=pd.to_numeric(
            out["snap_pct"],
            errors="coerce",
        )

        out["_weekly_raw_pct"]=(
            out.groupby("position")["weekly_raw_score"]
            .rank(pct=True,method="average")
            .mul(100)
        )
        out["_ros_raw_pct"]=(
            out.groupby("position")["ros_raw_score"]
            .rank(pct=True,method="average")
            .mul(100)
        )
        out["_volume_pct"]=(
            out.groupby("position")["recent_role_value"]
            .rank(pct=True,method="average")
            .mul(100)
        )
        out["_snap_pct_rank"]=(
            out.groupby("position")["snap_pct"]
            .rank(pct=True,method="average")
            .mul(100)
        )

        volume=out["_volume_pct"].fillna(0)
        snap=out["_snap_pct_rank"].fillna(0)

        out["weekly_research_score"]=(
            0.45*out["_weekly_raw_pct"].fillna(0)
            + 0.40*volume
            + 0.15*snap
        ).round(1)
        out.loc[~active,"weekly_research_score"]=0.0

        out["ros_research_score"]=(
            0.55*out["_ros_raw_pct"].fillna(0)
            + 0.30*volume
            + 0.15*snap
        ).round(1)

        def weekly_tier_from_rank(row):
            if str(row["weekly_tier"])=="INACTIVE":
                return "INACTIVE"
            score=float(row["weekly_research_score"])
            if score>=90:return "CORE_START_RESEARCH"
            if score>=70:return "START_LEAN"
            if score>=45:return "FLEX_START"
            if score>=25:return "MATCHUP_DEPENDENT"
            return "SIT_CAUTION"

        def ros_tier_from_rank(score):
            score=float(score)
            if score>=90:return "ROS_RISER"
            if score>=65:return "ROS_HOLD_PLUS"
            if score>=35:return "ROS_HOLD"
            return "ROS_CAUTION"

        out["weekly_tier"]=out.apply(
            weekly_tier_from_rank,
            axis=1,
        )
        out["ros_tier"]=out["ros_research_score"].map(
            ros_tier_from_rank
        )

        out=out.sort_values(
            ["weekly_research_score","ros_research_score"],
            ascending=False,
        )
    out.to_csv(OUT,index=False)

    receipt={
        "generated_at":NOW.isoformat(),
        "rows":int(len(out)),
        "weekly_tier_counts":out["weekly_tier"].value_counts().to_dict() if not out.empty else {},
        "ros_tier_counts":out["ros_tier"].value_counts().to_dict() if not out.empty else {},
        "personal_roster_context_used":False,
        "fantasy_points_projection_used":False,
        "score_is_probability":False,
        "automatic_model_adjustment":False,
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True))
    print(json.dumps(receipt,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
