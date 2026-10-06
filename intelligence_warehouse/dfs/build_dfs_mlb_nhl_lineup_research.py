#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import json
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
DFS=ROOT/"intelligence_warehouse"/"dfs"
SRC=DFS/"DFS_CONTEST_ARCHETYPES_CURRENT.csv"
OUT=DFS/"DFS_MLB_NHL_LINEUP_RESEARCH_CURRENT.csv"
RECEIPT=DFS/"DFS_MLB_NHL_LINEUP_RESEARCH_RECEIPT.json"
NOW=datetime.now(timezone.utc)

CONFIG={
    "MLB":{
        "cap":35000,
        "slots":["P","C/1B","2B","3B","SS","OF","OF","OF","UTIL"],
        "max_team":5,
        "max_hitters_team":4,
        "min_teams":3,
        "pool_limit":32,
    },
    "NHL":{
        "cap":55000,
        "slots":["C","C","W","W","D","D","UTIL","UTIL","G"],
        "max_team":4,
        "max_hitters_team":None,
        "min_teams":3,
        "pool_limit":38,
    },
}
BEAM=1200

def clean(v):
    if v is None:return ""
    try:
        if pd.isna(v):return ""
    except Exception:pass
    return str(v).strip()

def num(v):
    try:
        x=float(v)
        return None if pd.isna(x) else x
    except Exception:return None

def eligible(sport, slot, pos):
    p=clean(pos).upper()
    if sport=="MLB":
        if slot=="P": return p in {"P","SP","RP"}
        if slot=="C/1B": return p in {"C","1B"}
        if slot=="2B": return p=="2B"
        if slot=="3B": return p=="3B"
        if slot=="SS": return p=="SS"
        if slot=="OF": return p in {"OF","LF","CF","RF"}
        if slot=="UTIL": return p not in {"P","SP","RP"}
    if sport=="NHL":
        if slot=="C": return p=="C"
        if slot=="W": return p in {"W","LW","RW"}
        if slot=="D": return p=="D"
        if slot=="G": return p in {"G","GOALIE"}
        if slot=="UTIL": return p in {"C","W","LW","RW","D"}
    return False

def player_score(r):
    proj=num(r.get("projected_fantasy_points")) or 0.0
    value=num(r.get("value_percentile")) or 0.0
    score=proj+0.018*value
    ctx=clean(r.get("context_signal"))
    arch=clean(r.get("contest_archetype"))
    if ctx=="CONFIRMED_STARTER_VALUE": score+=1.4
    elif ctx=="VALUE_PLUS_ROLE_UP": score+=1.0
    elif ctx=="CONFIRMED_STARTER_CONTEXT": score+=0.5
    elif ctx=="ROLE_DOWN_CONTEXT": score-=1.0
    if arch=="CASH_CORE": score+=0.6
    elif arch=="GPP_CEILING": score+=0.9
    elif arch=="VALUE_PUNT": score+=0.5
    elif arch=="STARTER_VALUE": score+=0.5
    elif arch=="AVOID_AVAILABILITY_RISK": score-=8
    return score

def opp(r):
    team=clean(r.get("team"))
    home=clean(r.get("home_team"))
    away=clean(r.get("away_team"))
    if team==home:return away
    if team==away:return home
    return ""

def build_for_sport(d,sport):
    cfg=CONFIG[sport]
    x=d[(d["sport"].astype(str).str.upper()==sport)&(d["platform"].astype(str).str.upper()=="FANDUEL")].copy()
    x["salary"]=pd.to_numeric(x["salary"],errors="coerce")
    x["projected_fantasy_points"]=pd.to_numeric(x["projected_fantasy_points"],errors="coerce")
    x=x[x["salary"].notna()&x["projected_fantasy_points"].notna()].copy()
    x=x[x["contest_archetype"].astype(str)!="AVOID_AVAILABILITY_RISK"].copy()
    x["_research_score"]=x.apply(player_score,axis=1)
    x=x.sort_values(["_research_score","projected_fantasy_points"],ascending=False)

    pools={}
    for slot in set(cfg["slots"]):
        p=x[x["position"].map(lambda z:eligible(sport,slot,z))].head(cfg["pool_limit"])
        pools[slot]=p.to_dict("records")
        if not pools[slot]:
            return pd.DataFrame(),len(x)

    min_salary={slot:min(num(r.get("salary")) or 0 for r in pools[slot]) for slot in set(cfg["slots"])}
    states=[{
        "players":[],"used":set(),"salary":0.0,"proj":0.0,"research":0.0,
        "last":{},"team_counts":Counter(),"hitter_counts":Counter()
    }]
    repeat_slots={slot for slot in cfg["slots"] if cfg["slots"].count(slot)>1}

    for slot_index,slot in enumerate(cfg["slots"]):
        future_floor=sum(min_salary[s] for s in cfg["slots"][slot_index+1:])
        nxt=[]
        pool=pools[slot]
        for st in states:
            for idx,p in enumerate(pool):
                key=clean(p.get("player_key"))
                if not key or key in st["used"]:continue
                if slot in repeat_slots and idx<=st["last"].get(slot,-1):continue
                sal=num(p.get("salary")) or 0
                nsal=st["salary"]+sal
                if nsal>cfg["cap"] or nsal+future_floor>cfg["cap"]:continue

                team=clean(p.get("team")).upper()
                tc=Counter(st["team_counts"]); tc[team]+=1
                if tc[team]>cfg["max_team"]:continue

                hc=Counter(st["hitter_counts"])
                if sport=="MLB" and slot!="P":
                    hc[team]+=1
                    if hc[team]>cfg["max_hitters_team"]:continue

                last=dict(st["last"])
                if slot in repeat_slots:last[slot]=idx
                nxt.append({
                    "players":st["players"]+[(slot,p)],
                    "used":st["used"]|{key},
                    "salary":nsal,
                    "proj":st["proj"]+(num(p.get("projected_fantasy_points")) or 0),
                    "research":st["research"]+(num(p.get("_research_score")) or 0),
                    "last":last,"team_counts":tc,"hitter_counts":hc,
                })
        nxt.sort(key=lambda z:(z["research"],z["proj"]),reverse=True)
        states=nxt[:BEAM]
        if not states:break

    rows=[]; seen=set()
    for st in states:
        if len(st["players"])!=len(cfg["slots"]):continue
        teams={clean(p.get("team")).upper() for _,p in st["players"] if clean(p.get("team"))}
        if len(teams)<cfg["min_teams"]:continue
        keys=tuple(sorted(clean(p.get("player_key")) for _,p in st["players"]))
        if keys in seen:continue
        seen.add(keys)

        strategy=[]
        correlation_conflicts=0
        if sport=="MLB":
            pitcher=next((p for s,p in st["players"] if s=="P"),None)
            if pitcher:
                p_opp=opp(pitcher)
                correlation_conflicts=sum(
                    1
                    for s,p in st["players"]
                    if s!="P" and clean(p.get("team")).upper()==p_opp
                )
            if correlation_conflicts:
                continue
            max_hit=max(st["hitter_counts"].values()) if st["hitter_counts"] else 0
            if max_hit>=4:strategy.append("FOUR_HITTER_STACK")
            elif max_hit==3:strategy.append("THREE_HITTER_STACK")
        else:
            goalie=next((p for s,p in st["players"] if s=="G"),None)
            goalie_opp=opp(goalie) if goalie else ""
            correlation_conflicts=sum(
                1
                for s,p in st["players"]
                if s!="G" and goalie_opp and clean(p.get("team")).upper()==goalie_opp
            )
            if correlation_conflicts:
                continue
            skater_counts=Counter(clean(p.get("team")).upper() for s,p in st["players"] if s!="G")
            max_s=max(skater_counts.values()) if skater_counts else 0
            if max_s>=4:strategy.append("FOUR_SKATER_STACK")
            elif max_s==3:strategy.append("THREE_SKATER_STACK")
            elif max_s==2:strategy.append("PAIR_STACK")

        rows.append({
            "generated_at":NOW.isoformat(),"sport":sport,"platform":"FANDUEL",
            "slate_id":clean(st["players"][0][1].get("slate_id")) if st["players"] else "",
            "roster_slots":",".join(cfg["slots"]),"salary_cap":cfg["cap"],
            "salary_used":int(st["salary"]),"salary_remaining":int(cfg["cap"]-st["salary"]),
            "projected_fantasy_points":round(st["proj"],3),
            "research_score":round(st["research"],3),
            "teams_used":len(teams),
            "max_players_one_team":max(st["team_counts"].values()) if st["team_counts"] else 0,
            "max_hitters_one_team":max(st["hitter_counts"].values()) if sport=="MLB" and st["hitter_counts"] else None,
            "strategy_flags":" | ".join(strategy) if strategy else "BALANCED",
            "players":" | ".join(f"{s}:{clean(p.get('player'))}" for s,p in st["players"]),
            "verified_constraints":"ROSTER_SLOTS|SALARY_CAP|TEAM_LIMITS|MIN_TEAMS",
            "rule_verification":"CURRENT_EXTERNAL_CROSSCHECK_2026_10",
            "contest_submission_ready":False,
            "projected_ownership_used":False,
            "score_is_probability":False,
            "automatic_model_adjustment":False,
        })

    out=pd.DataFrame(rows)
    if not out.empty:
        picks=[]
        for col in ["projected_fantasy_points","research_score"]:
            picks.extend(out.sort_values(col,ascending=False).head(20).to_dict("records"))
        out=pd.DataFrame(picks).drop_duplicates("players").head(25)
    return out,len(x)

def main():
    d=pd.read_csv(SRC,low_memory=False)
    all_rows=[]; pool_rows={}
    for sport in ["MLB","NHL"]:
        out,n=build_for_sport(d,sport)
        pool_rows[sport]=n
        if not out.empty:all_rows.append(out)
    final=pd.concat(all_rows,ignore_index=True) if all_rows else pd.DataFrame()
    final.to_csv(OUT,index=False)
    receipt={
        "generated_at":NOW.isoformat(),
        "candidate_rows":int(len(final)),
        "candidate_rows_by_sport":final["sport"].value_counts().to_dict() if not final.empty else {},
        "player_pool_rows":pool_rows,
        "rules":{
            "MLB":{"slots":"P,C/1B,2B,3B,SS,OF,OF,OF,UTIL","cap":35000,"max_team":5,"max_hitters_team":4,"min_teams":3},
            "NHL":{"slots":"C,C,W,W,D,D,UTIL,UTIL,G","cap":55000,"max_team":4,"min_teams":3},
        },
        "rule_verification":"CURRENT_EXTERNAL_CROSSCHECK_2026_10",
        "contest_submission_ready":False,
        "projected_ownership_used":False,
        "score_is_probability":False,
        "automatic_model_adjustment":False,
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True))
    print(json.dumps(receipt,indent=2,sort_keys=True))
if __name__=="__main__":main()
