#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
DFS=ROOT/"intelligence_warehouse"/"dfs"
SRC=DFS/"DFS_CONTEST_ARCHETYPES_CURRENT.csv"
OUT=DFS/"DFS_DK_NFL_LINEUP_RESEARCH_CURRENT.csv"
RECEIPT=DFS/"DFS_DK_NFL_LINEUP_RESEARCH_RECEIPT.json"
NOW=datetime.now(timezone.utc)

CAP=50000
SLOTS=["QB","RB","RB","WR","WR","WR","TE","FLEX","DST"]
BEAM=1800
POOL_LIMITS={"QB":26,"RB":46,"WR":60,"TE":32,"DST":24,"FLEX":78}

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

def eligible(slot,pos):
    p=clean(pos).upper().replace("D/ST","DST")
    if slot=="FLEX":return p in {"RB","WR","TE"}
    return p==slot

def opponent(r):
    return clean(r.get("opponent")).upper()

def game_key(r):
    team=clean(r.get("team")).upper()
    opp=opponent(r)
    if not team or not opp:return ""
    return "|".join(sorted([team,opp]))

def player_score(r):
    proj=num(r.get("projected_fantasy_points")) or 0
    value_pct=num(r.get("value_percentile")) or 0
    score=proj+0.018*value_pct
    ctx=clean(r.get("context_signal"))
    arch=clean(r.get("contest_archetype"))
    if ctx=="CONFIRMED_STARTER_VALUE":score+=1.5
    elif ctx=="VALUE_PLUS_ROLE_UP":score+=1.0
    elif ctx=="CONFIRMED_STARTER_CONTEXT":score+=0.5
    elif ctx=="ROLE_DOWN_CONTEXT":score-=1.0
    if arch=="CASH_CORE":score+=0.6
    elif arch=="GPP_CEILING":score+=0.9
    elif arch=="VALUE_PUNT":score+=0.5
    elif arch=="STARTER_VALUE":score+=0.4
    elif arch=="AVOID_AVAILABILITY_RISK":score-=8
    return score

def stack_bonus(players):
    qbs=[p for slot,p in players if slot=="QB"]
    if not qbs:return 0.0,"NO_QB"
    qb=qbs[0]
    team=clean(qb.get("team")).upper()
    opp=opponent(qb)
    catch=[p for slot,p in players if clean(p.get("team")).upper()==team and clean(p.get("position")).upper() in {"WR","TE"}]
    bring=[p for slot,p in players if clean(p.get("team")).upper()==opp and clean(p.get("position")).upper() in {"RB","WR","TE"}]
    bonus=0.0
    label="NAKED_QB"
    if len(catch)>=2:
        bonus+=4.0; label="QB_DOUBLE_STACK"
    elif len(catch)==1:
        bonus+=2.5; label="QB_STACK"
    if bring:
        bonus+=1.5; label+="_BRINGBACK"
    return bonus,label

def main():
    d=pd.read_csv(SRC,low_memory=False)
    d=d[
        d["sport"].astype(str).str.upper().eq("NFL")
        & d["platform"].astype(str).str.upper().eq("DRAFTKINGS")
    ].copy()
    d["position"]=d["position"].astype(str).str.upper().str.replace("D/ST","DST",regex=False)
    d["salary"]=pd.to_numeric(d["salary"],errors="coerce")
    d["projected_fantasy_points"]=pd.to_numeric(d["projected_fantasy_points"],errors="coerce")
    d=d[d["salary"].notna()&d["projected_fantasy_points"].notna()].copy()
    d=d[d["contest_archetype"].astype(str)!="AVOID_AVAILABILITY_RISK"].copy()
    d["_research_score"]=d.apply(player_score,axis=1)

    pools={}
    for slot in set(SLOTS):
        x=d[d["position"].map(lambda p:eligible(slot,p))].copy()
        x=x.sort_values(["_research_score","projected_fantasy_points"],ascending=False)
        pools[slot]=x.head(POOL_LIMITS[slot]).to_dict("records")
        if not pools[slot]:
            raise SystemExit(f"Missing DK NFL pool for {slot}")

    min_salary={slot:min(num(r.get("salary")) or 0 for r in pools[slot]) for slot in set(SLOTS)}
    repeat_slots={s for s in SLOTS if SLOTS.count(s)>1}
    states=[{"players":[],"used":set(),"salary":0.0,"proj":0.0,"research":0.0,"last":{}}]

    for slot_index,slot in enumerate(SLOTS):
        future_floor=sum(min_salary[s] for s in SLOTS[slot_index+1:])
        nxt=[]
        for st in states:
            for idx,p in enumerate(pools[slot]):
                key=clean(p.get("player_key"))
                if not key or key in st["used"]:continue
                if slot in repeat_slots and idx<=st["last"].get(slot,-1):continue
                sal=num(p.get("salary")) or 0
                nsal=st["salary"]+sal
                if nsal>CAP or nsal+future_floor>CAP:continue
                last=dict(st["last"])
                if slot in repeat_slots:last[slot]=idx
                nxt.append({
                    "players":st["players"]+[(slot,p)],
                    "used":st["used"]|{key},
                    "salary":nsal,
                    "proj":st["proj"]+(num(p.get("projected_fantasy_points")) or 0),
                    "research":st["research"]+(num(p.get("_research_score")) or 0),
                    "last":last,
                })
        nxt.sort(key=lambda x:(x["research"],x["proj"]),reverse=True)
        states=nxt[:BEAM]
        if not states:break

    rows=[]; seen=set()
    for st in states:
        if len(st["players"])!=9:continue
        names=[clean(p.get("player_key")) for _,p in st["players"]]
        if len(set(names))!=9:continue
        games={game_key(p) for _,p in st["players"] if game_key(p)}
        if len(games)<2:continue

        dst=next((p for slot,p in st["players"] if slot=="DST"),None)
        if dst:
            dst_opp=opponent(dst)
            offense_vs_dst=sum(
                1 for slot,p in st["players"]
                if slot!="DST" and clean(p.get("team")).upper()==dst_opp
            )
            if offense_vs_dst:
                continue

        keys=tuple(sorted(names))
        if keys in seen:continue
        seen.add(keys)
        bonus,pattern=stack_bonus(st["players"])
        balanced=st["research"]+bonus
        own_vals=[
            num(p.get("modelled_ownership_pct"))
            for _,p in st["players"]
            if num(p.get("modelled_ownership_pct")) is not None
        ]

        rows.append({
            "generated_at":NOW.isoformat(),
            "sport":"NFL","platform":"DRAFTKINGS",
            "slate_id":clean(st["players"][0][1].get("slate_id")),
            "roster_slots":"QB,RB,RB,WR,WR,WR,TE,FLEX,DST",
            "salary_cap":CAP,"salary_used":int(st["salary"]),
            "salary_remaining":int(CAP-st["salary"]),
            "projected_fantasy_points":round(st["proj"],3),
            "research_score":round(st["research"],3),
            "stack_bonus":round(bonus,3),
            "balanced_research_score":round(balanced,3),
            "stack_pattern":pattern,
            "games_used":len(games),
            "modelled_ownership_sum":round(sum(own_vals),2) if own_vals else None,
            "modelled_ownership_source":"SHARKSNIP_HEURISTIC" if own_vals else "",
            "players":" | ".join(f"{slot}:{clean(p.get('player'))}" for slot,p in st["players"]),
            "verified_constraints":"ROSTER_SLOTS|SALARY_CAP|MIN_2_GAMES",
            "rule_verification":"CURRENT_EXTERNAL_CROSSCHECK_2026_09_27",
            "contest_submission_ready":False,
            "projected_ownership_used":False,
            "modelled_ownership_used":False,
            "score_is_probability":False,
            "automatic_model_adjustment":False,
        })

    out=pd.DataFrame(rows)
    if not out.empty:
        selections=[]
        for col in ["projected_fantasy_points","balanced_research_score"]:
            selections.extend(out.sort_values(col,ascending=False).head(20).to_dict("records"))
        out=pd.DataFrame(selections).drop_duplicates("players").head(25)
    out.to_csv(OUT,index=False)

    receipt={
        "generated_at":NOW.isoformat(),
        "candidate_rows":int(len(out)),
        "projection_pool_rows":int(len(d)),
        "salary_cap":CAP,
        "verified_roster_slots":"QB,RB,RB,WR,WR,WR,TE,FLEX,DST",
        "minimum_games":2,
        "dst_offense_conflicts_allowed":False,
        "projected_ownership_used":False,
        "modelled_ownership_available":bool(pd.to_numeric(d.get("modelled_ownership_pct"),errors="coerce").notna().any()),
        "modelled_ownership_used":False,
        "contest_submission_ready":False,
        "score_is_probability":False,
        "automatic_model_adjustment":False,
        "dependency_free_beam_search":True,
        "rule_verification":"CURRENT_EXTERNAL_CROSSCHECK_2026_09_27",
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True))
    print(json.dumps(receipt,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
