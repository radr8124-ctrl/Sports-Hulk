#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
DFS=ROOT/"intelligence_warehouse"/"dfs"
SRC=DFS/"DFS_CONTEST_ARCHETYPES_CURRENT.csv"
OUT=DFS/"DFS_NFL_LINEUP_RESEARCH_CURRENT.csv"
RECEIPT=DFS/"DFS_NFL_LINEUP_RESEARCH_RECEIPT.json"
NOW=datetime.now(timezone.utc)

CAP=60000
SLOTS=["QB","RB","RB","WR","WR","WR","TE","FLEX","D"]
POOL_LIMITS={"QB":20,"RB":40,"WR":55,"TE":30,"D":20,"FLEX":80}
BEAM=5000

def clean(v):
    if v is None: return ""
    try:
        if pd.isna(v): return ""
    except Exception: pass
    return str(v).strip()

def num(v):
    try:
        x=float(v)
        return None if pd.isna(x) else x
    except Exception:
        return None

def player_score(r):
    proj=num(r.get("projected_fantasy_points")) or 0
    val=num(r.get("value_percentile")) or 0
    score=proj + 0.02*val
    ctx=clean(r.get("context_signal"))
    arch=clean(r.get("contest_archetype"))
    if ctx=="CONFIRMED_STARTER_VALUE": score+=1.5
    elif ctx=="VALUE_PLUS_ROLE_UP": score+=1.0
    elif ctx=="CONFIRMED_STARTER_CONTEXT": score+=0.5
    elif ctx=="ROLE_DOWN_CONTEXT": score-=1.0
    if arch=="CASH_CORE": score+=0.6
    elif arch=="VALUE_PUNT": score+=0.5
    elif arch=="STARTER_VALUE": score+=0.4
    elif arch=="AVOID_AVAILABILITY_RISK": score-=5
    return score

def opponent_of(r):
    team=clean(r.get("team"))
    home=clean(r.get("home_team"))
    away=clean(r.get("away_team"))
    if team==home: return away
    if team==away: return home
    return ""

def build_pool(d,pos):
    if pos=="FLEX":
        x=d[d["position"].isin(["RB","WR","TE"])].copy()
    else:
        x=d[d["position"].eq(pos)].copy()
    x=x.sort_values(["_research_score","projected_fantasy_points"],ascending=False)
    return x.head(POOL_LIMITS[pos]).to_dict("records")

def stack_bonus(players):
    qbs=[p for p in players if clean(p.get("position"))=="QB"]
    if not qbs: return 0,"NO_QB_STACK"
    qb=qbs[0]
    team=clean(qb.get("team"))
    opp=opponent_of(qb)
    pass_catch=[p for p in players if clean(p.get("team"))==team and clean(p.get("position")) in {"WR","TE"}]
    bring=[p for p in players if clean(p.get("team"))==opp and clean(p.get("position")) in {"RB","WR","TE"}]
    bonus=0
    label="NAKED_QB"
    if len(pass_catch)>=2:
        bonus+=4
        label="QB_DOUBLE_STACK"
    elif len(pass_catch)==1:
        bonus+=2.5
        label="QB_STACK"
    if bring:
        bonus+=1.5
        label += "_BRINGBACK"
    return bonus,label

def main():
    d=pd.read_csv(SRC,low_memory=False)
    d=d[(d["sport"].astype(str).str.upper()=="NFL") & (d["platform"].astype(str).str.upper()=="FANDUEL")].copy()
    d["position"]=d["position"].astype(str).str.upper()
    d=d[d["position"].isin(["QB","RB","WR","TE","D"])].copy()
    d["salary"]=pd.to_numeric(d["salary"],errors="coerce")
    d["projected_fantasy_points"]=pd.to_numeric(d["projected_fantasy_points"],errors="coerce")
    d=d[d["salary"].notna() & d["projected_fantasy_points"].notna()].copy()
    d=d[d["contest_archetype"].astype(str)!="AVOID_AVAILABILITY_RISK"].copy()
    d["_research_score"]=d.apply(player_score,axis=1)

    pools={slot:build_pool(d,slot) for slot in set(SLOTS)}
    min_salary_by_slot={
        slot:min((num(x.get("salary")) or 0) for x in pools[slot])
        for slot in set(SLOTS)
    }
    states=[{"players":[],"used":set(),"salary":0.0,"proj":0.0,"research":0.0,"last":{"RB":-1,"WR":-1}}]

    for slot_index, slot in enumerate(SLOTS):
        future_floor=sum(
            min_salary_by_slot[s]
            for s in SLOTS[slot_index+1:]
        )
        next_states=[]
        pool=pools[slot]
        for st in states:
            for idx,p in enumerate(pool):
                key=clean(p.get("player_key"))
                if not key or key in st["used"]:
                    continue
                pos=clean(p.get("position"))
                if slot in {"RB","WR"}:
                    if idx<=st["last"].get(slot,-1):
                        continue
                sal=num(p.get("salary")) or 0
                nsal=st["salary"]+sal
                if nsal>CAP or nsal+future_floor>CAP:
                    continue
                last=dict(st["last"])
                if slot in {"RB","WR"}:
                    last[slot]=idx
                next_states.append({
                    "players":st["players"]+[p],
                    "used":st["used"]|{key},
                    "salary":nsal,
                    "proj":st["proj"]+(num(p.get("projected_fantasy_points")) or 0),
                    "research":st["research"]+num(p.get("_research_score")),
                    "last":last,
                })
        next_states.sort(key=lambda x:(x["research"],x["proj"]),reverse=True)
        states=next_states[:BEAM]
        if not states:
            break

    rows=[]
    seen=set()
    for st in states:
        if len(st["players"])!=9:
            continue
        keys=tuple(sorted(clean(p.get("player_key")) for p in st["players"]))
        if keys in seen: continue
        seen.add(keys)
        bonus,stack_label=stack_bonus(st["players"])
        balanced=st["research"]+bonus
        names=" | ".join(f"{clean(p.get('position'))}:{clean(p.get('player'))}" for p in st["players"])
        rows.append({
            "generated_at":NOW.isoformat(),
            "platform":"FANDUEL",
            "sport":"NFL",
            "slate_id":clean(st["players"][0].get("slate_id")) if st["players"] else "",
            "roster_slots":"QB,RB,RB,WR,WR,WR,TE,FLEX,D",
            "salary_cap":CAP,
            "salary_used":int(st["salary"]),
            "salary_remaining":int(CAP-st["salary"]),
            "projected_fantasy_points":round(st["proj"],3),
            "research_score":round(st["research"],3),
            "stack_bonus":round(bonus,3),
            "balanced_research_score":round(balanced,3),
            "stack_pattern":stack_label,
            "players":names,
            "verified_constraints":"ROSTER_SLOTS|SALARY_CAP",
            "contest_submission_ready":False,
            "projected_ownership_used":False,
            "score_is_probability":False,
            "automatic_model_adjustment":False,
        })

    out=pd.DataFrame(rows)
    if not out.empty:
        # Keep diverse research candidates from several objectives.
        selections=[]
        for col in ["projected_fantasy_points","balanced_research_score"]:
            for _,r in out.sort_values(col,ascending=False).head(15).iterrows():
                selections.append(r.to_dict())
        out=pd.DataFrame(selections).drop_duplicates("players").head(20)
    out.to_csv(OUT,index=False)

    receipt={
        "generated_at":NOW.isoformat(),
        "candidate_rows":int(len(out)),
        "player_pool_rows":int(len(d)),
        "salary_cap":CAP,
        "verified_roster_slots":"QB,RB,RB,WR,WR,WR,TE,FLEX,D",
        "projected_ownership_used":False,
        "contest_submission_ready":False,
        "score_is_probability":False,
        "automatic_model_adjustment":False,
        "dependency_free_beam_search":True,
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True))
    print(json.dumps(receipt,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
