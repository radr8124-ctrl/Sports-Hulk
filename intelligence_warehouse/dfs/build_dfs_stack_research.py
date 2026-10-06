#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
DFS = ROOT / "intelligence_warehouse" / "dfs"
VALUE = DFS / "DFS_VALUE_SIGNALS_CURRENT.csv"
ARCH = DFS / "DFS_CONTEST_ARCHETYPES_CURRENT.csv"
STACKS = DFS / "DFS_STACK_RESEARCH_CURRENT.csv"
RECEIPT = DFS / "DFS_STACK_RESEARCH_RECEIPT.json"

NOW = datetime.now(timezone.utc)

def clean(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    return str(v).strip()

def num(v):
    try:
        x=float(v)
        return None if pd.isna(x) else x
    except Exception:
        return None

def archetype(row):
    if clean(row.get("platform")).upper()=="DRAFTKINGS" and num(row.get("projected_fantasy_points")) is None:
        return "SALARY_ONLY_RESEARCH"
    status=clean(row.get("availability_status")).upper()
    if status in {"OUT","IR","PUP","SUSPENDED"}:
        return "AVOID_AVAILABILITY_RISK"
    proj=num(row.get("projection_percentile"))
    val=num(row.get("value_percentile"))
    sal=num(row.get("salary_percentile"))
    ctx=clean(row.get("context_signal"))
    starter=bool(row.get("starter_context_usable_pregame"))
    if proj is not None and proj>=85 and val is not None and val>=70:
        return "CASH_CORE"
    if proj is not None and proj>=90:
        return "GPP_CEILING"
    if val is not None and val>=85 and (sal is None or sal<=60):
        return "VALUE_PUNT"
    if starter and ctx in {"CONFIRMED_STARTER_VALUE","CONFIRMED_STARTER_CONTEXT"}:
        return "STARTER_VALUE"
    if clean(row.get("value_signal")) in {"TOP_VALUE","UNDERPRICED_VS_PROJECTION"}:
        return "VALUE_RESEARCH"
    return "BALANCED_RESEARCH"

def context_points(row):
    score=0.0
    sig=clean(row.get("context_signal"))
    if sig=="CONFIRMED_STARTER_VALUE": score+=12
    elif sig=="CONFIRMED_STARTER_CONTEXT": score+=7
    elif sig=="VALUE_PLUS_ROLE_UP": score+=8
    elif sig=="VALUE_PLUS_FANTASY_ADDS": score+=5
    elif sig=="ROLE_DOWN_CONTEXT": score-=8
    elif sig=="AVAILABILITY_RISK": score-=20
    elif sig=="AVAILABILITY_CONTEXT": score-=2
    value=clean(row.get("value_signal"))
    if value=="TOP_VALUE": score+=10
    elif value=="PREMIUM_PROJECTION": score+=7
    elif value=="UNDERPRICED_VS_PROJECTION": score+=8
    elif value=="SALARY_HEAVY_VS_PROJECTION": score-=5
    return score

def add_stack(rows, sport, platform, slate_id, stack_type, team, opponent, members):
    if not members:
        return
    names=[clean(x.get("player")) for x in members]
    salary=sum(num(x.get("salary")) or 0 for x in members)
    proj_vals=[num(x.get("projected_fantasy_points")) for x in members]
    proj=sum(x for x in proj_vals if x is not None)
    vals=[num(x.get("audit_value_per_1000")) for x in members if num(x.get("audit_value_per_1000")) is not None]
    avg_val=sum(vals)/len(vals) if vals else None
    risks=sum(1 for x in members if clean(x.get("context_signal")) in {"AVAILABILITY_RISK","ROLE_DOWN_CONTEXT"})
    boosts=sum(1 for x in members if clean(x.get("context_signal")) in {"CONFIRMED_STARTER_VALUE","VALUE_PLUS_ROLE_UP","TOP_VALUE"})
    score=sum(context_points(x) for x in members)
    proj_pct=[num(x.get("projection_percentile")) for x in members if num(x.get("projection_percentile")) is not None]
    if proj_pct:
        score += sum(proj_pct)/len(proj_pct)/5.0
    if avg_val is not None:
        score += min(avg_val*3.0, 15)
    score -= risks*8
    rows.append({
        "generated_at": NOW.isoformat(),
        "sport": sport,
        "platform": platform,
        "slate_id": slate_id,
        "stack_type": stack_type,
        "team": team,
        "opponent": opponent,
        "member_count": len(members),
        "members": " | ".join(names),
        "combined_salary": salary if salary else None,
        "combined_projection": round(proj,3) if proj_vals else None,
        "average_value_per_1000": round(avg_val,3) if avg_val is not None else None,
        "context_boost_count": boosts,
        "risk_count": risks,
        "stack_quality": (
            "CLEAN"
            if risks == 0
            else "CAUTION"
            if risks == 1
            else "HIGH_RISK"
        ),
        "research_eligible": risks == 0,
        "stack_research_score": round(score,2),
        "score_is_probability": False,
        "measured_correlation": False,
        "projected_ownership_used": False,
        "automatic_model_adjustment": False,
    })

def main():
    if not VALUE.exists():
        raise SystemExit("DFS value file missing")
    d=pd.read_csv(VALUE,low_memory=False)
    if d.empty:
        pd.DataFrame().to_csv(ARCH,index=False)
        pd.DataFrame().to_csv(STACKS,index=False)
        return

    d["contest_archetype"]=d.apply(archetype,axis=1)
    d["contest_score_is_probability"]=False
    d["projected_ownership_used"]=False
    d["automatic_model_adjustment"]=False
    d.to_csv(ARCH,index=False)

    rows=[]
    fd=d[(d["platform"].astype(str).str.upper()=="FANDUEL") & d["projected_fantasy_points"].notna()].copy()

    for (sport,platform,slate), slate_df in fd.groupby(["sport","platform","slate_id"],dropna=False):
        sport=clean(sport).upper()
        if sport=="NFL":
            for team, team_df in slate_df.groupby("team",dropna=False):
                team=clean(team)
                if not team:
                    continue
                qbs=team_df[team_df["position"].astype(str).str.upper()=="QB"].sort_values("projected_fantasy_points",ascending=False)
                catch=team_df[team_df["position"].astype(str).str.upper().isin(["WR","TE"])].sort_values("projected_fantasy_points",ascending=False)
                if qbs.empty or catch.empty:
                    continue
                qb=qbs.iloc[0].to_dict()
                opponent=""
                home=clean(qb.get("home_team")); away=clean(qb.get("away_team"))
                if team==home: opponent=away
                elif team==away: opponent=home
                add_stack(rows,sport,platform,slate,"QB_PASS_CATCHER",team,opponent,[qb,catch.iloc[0].to_dict()])
                if len(catch)>=2:
                    add_stack(rows,sport,platform,slate,"QB_DOUBLE_STACK",team,opponent,[qb,catch.iloc[0].to_dict(),catch.iloc[1].to_dict()])
                opp_df=slate_df[slate_df["team"].astype(str)==opponent]
                bring=opp_df[opp_df["position"].astype(str).str.upper().isin(["WR","TE","RB"])].sort_values("projected_fantasy_points",ascending=False)
                if not bring.empty:
                    add_stack(rows,sport,platform,slate,"QB_STACK_BRINGBACK",team,opponent,[qb,catch.iloc[0].to_dict(),bring.iloc[0].to_dict()])
        elif sport=="MLB":
            for team, team_df in slate_df.groupby("team",dropna=False):
                hitters=team_df[~team_df["position"].astype(str).str.upper().isin(["P","SP","RP"])].sort_values("projected_fantasy_points",ascending=False)
                if len(hitters)<3:
                    continue
                first=hitters.iloc[0].to_dict()
                home=clean(first.get("home_team")); away=clean(first.get("away_team"))
                opponent=away if clean(team)==home else home if clean(team)==away else ""
                add_stack(rows,sport,platform,slate,"TEAM_HITTER_3",clean(team),opponent,[hitters.iloc[i].to_dict() for i in range(3)])
                if len(hitters)>=4:
                    add_stack(rows,sport,platform,slate,"TEAM_HITTER_4",clean(team),opponent,[hitters.iloc[i].to_dict() for i in range(4)])
        elif sport=="NHL":
            for team, team_df in slate_df.groupby("team",dropna=False):
                skaters=team_df[~team_df["position"].astype(str).str.upper().isin(["G","GOALIE"])].sort_values("projected_fantasy_points",ascending=False)
                if len(skaters)<2:
                    continue
                first=skaters.iloc[0].to_dict()
                home=clean(first.get("home_team")); away=clean(first.get("away_team"))
                opponent=away if clean(team)==home else home if clean(team)==away else ""
                add_stack(rows,sport,platform,slate,"SKATER_PAIR",clean(team),opponent,[skaters.iloc[0].to_dict(),skaters.iloc[1].to_dict()])
                if len(skaters)>=3:
                    add_stack(rows,sport,platform,slate,"SKATER_TRIO",clean(team),opponent,[skaters.iloc[i].to_dict() for i in range(3)])

    stacks=pd.DataFrame(rows)
    if not stacks.empty:
        stacks=stacks.sort_values(["sport","platform","slate_id","stack_research_score"],ascending=[True,True,True,False])
    stacks.to_csv(STACKS,index=False)

    dk_projection_rows = int(
        (
            d["platform"].astype(str).str.upper().eq("DRAFTKINGS")
            & pd.to_numeric(
                d.get(
                    "projected_fantasy_points",
                    pd.Series(index=d.index, dtype=float),
                ),
                errors="coerce",
            ).notna()
        ).sum()
    )

    receipt={
        "generated_at":NOW.isoformat(),
        "archetype_rows":int(len(d)),
        "archetype_counts":d["contest_archetype"].value_counts().to_dict(),
        "stack_rows":int(len(stacks)),
        "stack_rows_by_sport":stacks["sport"].value_counts().to_dict() if not stacks.empty else {},
        "stack_quality_counts":stacks["stack_quality"].value_counts().to_dict() if not stacks.empty else {},
        "research_eligible_stacks":int(stacks["research_eligible"].fillna(False).astype(bool).sum()) if not stacks.empty else 0,
        "projected_ownership_used":False,
        "measured_correlation":False,
        "score_is_probability":False,
        "automatic_model_adjustment":False,
        "draftkings_projection_rows":dk_projection_rows,
        "draftkings_projection_available":dk_projection_rows > 0,
        "draftkings_projection_gap_preserved":dk_projection_rows == 0,
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True))
    print(json.dumps(receipt,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
