#!/usr/bin/env python3
from __future__ import annotations
import json, math, sys, unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUTDIR=ROOT/"intelligence_warehouse"/"fantasy_accountability"
CURRENT_OUT=OUTDIR/"FANTASY_V2_CURRENT.json"
LEDGER=OUTDIR/"FANTASY_V2_FORWARD_LEDGER.jsonl"
FORWARD_OUT=OUTDIR/"FANTASY_V2_FORWARD_SUMMARY.json"
PUBLIC=ROOT/"commercial_web"/"public"
DIST=ROOT/"commercial_web"/"dist"
FDEC=ROOT/"intelligence_warehouse"/"fantasy_decisions"
WEEKLY=FDEC/"FANTASY_WEEKLY_DECISIONS_CURRENT.csv"
FAAB=FDEC/"FANTASY_FAAB_RESEARCH_CURRENT.csv"
STASH=FDEC/"FANTASY_IR_STASH_CURRENT.csv"
DEFENSE=FDEC/"FANTASY_DEFENSE_STREAMING_CURRENT.csv"
IDP=FDEC/"FANTASY_IDP_OPPORTUNITY_CURRENT.csv"
SCHEDULE=ROOT/"nfl_live"/"derived"/"NFLVERSE_2026_SCHEDULE.csv"
STATS=ROOT/"nfl_live"/"player_context"/"derived"/"NFL_PLAYER_STATS_RECENT.csv"
MODEL_VERSION="FANTASY_V3_BASELINE_PROOF_2026_10_05"
OFF_POS={"QB","RB","WR","TE"}
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from intelligence_warehouse.dfs_accountability.build_dfs_accountability import defense_points,schedule_kickoff,team_game_final

def now(): return datetime.now(timezone.utc)
def iso(): return now().isoformat()
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
def csv(path):
    try:return pd.read_csv(path,low_memory=False) if path.exists() else pd.DataFrame()
    except Exception:return pd.DataFrame()
def write_json(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(json.dumps(payload,indent=2)); tmp.replace(path)
def read_jsonl(path):
    if not path.exists():return []
    out=[]
    for line in path.read_text().splitlines():
        try:out.append(json.loads(line))
        except Exception:pass
    return out
def append_jsonl(path,row):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as h:h.write(json.dumps(row,separators=(",",":"))+"\n")
def norm(v):
    text=unicodedata.normalize("NFKD",clean(v)).encode("ascii","ignore").decode("ascii").lower()
    return "".join(ch for ch in text if ch.isalnum())

def load_schedule():
    d=csv(SCHEDULE)
    if d.empty:return d
    d=d[d["season"].eq(2026)].copy()
    d["_kickoff"]=d.apply(schedule_kickoff,axis=1)
    return d
def next_game(schedule,team):
    if schedule.empty:return None
    team=clean(team).upper(); ref=pd.Timestamp(now())
    x=schedule[((schedule["away_team"].astype(str).str.upper()==team)|(schedule["home_team"].astype(str).str.upper()==team)) & schedule["_kickoff"].notna() & schedule["_kickoff"].ge(ref)].copy()
    if x.empty:return None
    return x.sort_values("_kickoff").iloc[0]

def readiness():
    w,f,s,d,i=map(csv,[WEEKLY,FAAB,STASH,DEFENSE,IDP])
    two=conf=0
    if not s.empty:
        two=int((pd.to_numeric(s.get("source_count"),errors="coerce")>=2).sum())
        conf=int(s.get("source_disagreement",pd.Series(False,index=s.index)).fillna(False).astype(bool).sum())
    return {
      "generated_at":iso(),"status":"READY","model_version":MODEL_VERSION,
      "lanes":{
       "WEEKLY":{"rows":len(w),"status":"GENERIC_RANKING_FORWARD_TEST","personal_roster_context_used":False,"fantasy_points_projection_used":False,"actionability":"RESEARCH_ONLY_UNTIL_LEAGUE_AND_ROSTER_CONTEXT","forward_grade_available":True},
       "FAAB":{"rows":len(f),"status":"ADD_QUALITY_FORWARD_TEST","faab_is_market_prediction":False,"league_size_context_used":False,"remaining_budget_context_used":False,"roster_need_context_used":False,"actionability":"RANKING_CAN_EARN_PROOF; BID_RANGE_REMAINS_RESEARCH_NOT_PERSONAL_BID","forward_grade_available":True},
       "IR_STASH":{"rows":len(s),"status":"FOUR_WEEK_STASH_UTILITY_FORWARD_TEST","two_plus_source_rows":two,"source_conflict_rows":conf,"return_date_is_guarantee":False,"roster_ir_slot_context_used":False,"dated_nfl_return_signals_available":False,"actionability":"SOURCE_SUPPORTED_STASH_RANK_CAN_EARN_UTILITY_PROOF; NO_RETURN_DATE_GUARANTEE","forward_grade_available":True},
       "DEFENSE_STREAMING":{"rows":len(d),"status":"GENERIC_STREAM_FORWARD_TEST","league_scoring_context_used":False,"actionability":"RESEARCH_ONLY_UNTIL_FORWARD_PROOF_AND_LEAGUE_CONTEXT","forward_grade_available":True},
       "IDP":{"rows":len(i),"status":"USAGE_RANK_FORWARD_TEST","fantasy_points_projection_available":False,"league_scoring_context_used":False,"waiver_market_coverage_available":False,"actionability":"USAGE_RANK_CAN_EARN_GENERIC_PRODUCTION_PROOF; NOT LEAGUE_SPECIFIC START_OR_FAAB","forward_grade_available":True},
       "TRADE_RATE_TEAM":{"rows":0,"status":"REQUIRES_CONNECTED_LEAGUE_CONTEXT","actionability":"NO_GENERIC_TRADE_OR_TEAM_GRADE","forward_grade_available":False}},
      "rules":["Research scores are not probabilities.","Weekly rankings are generic until league settings and roster context are available.","FAAB ranges are research ranges, not market-clearing or personalized bids.","IR return dates are not guarantees and source disagreement remains visible.","Defense streaming must earn forward rank value before strategy claims.","IDP remains usage research until scoring-aware projections exist.","Fantasy V3 must beat role/snap and recent-PPR baselines before weekly ranking review.", "No Fantasy V3 lane changes recommendations automatically."]}

def canonical():
    out={}
    for e in read_jsonl(LEDGER):
        k=e.get("forward_key")
        if k:out[k]={**out.get(k,{}),**e}
    return out

def prior_ppr_map(stats, target_week):
    out=defaultdict(list)
    if stats.empty:
        return {}
    x=stats[
        (pd.to_numeric(stats.get("week"),errors="coerce") < int(target_week))
        & stats["position"].astype(str).str.upper().isin(OFF_POS)
    ].copy()
    for _,r in x.iterrows():
        pk=norm(r.get("player_display_name") or r.get("player_name"))
        team=clean(r.get("team")).upper()
        pts=num(r.get("fantasy_points_ppr"))
        if pk and pts is not None:
            out[(pk,team)].append(float(pts))
            out[(pk,"")].append(float(pts))
    return {
        key:sum(vals[-3:])/len(vals[-3:])
        for key,vals in out.items() if vals
    }


def capture():
    sch=load_schedule()
    existing=canonical()
    added={"WEEKLY":0,"FAAB":0,"IR_STASH":0,"DEFENSE_STREAMING":0,"IDP":0}
    stats=csv(STATS)
    w=csv(WEEKLY)

    if not w.empty:
        w=w[
            (w["sport"].astype(str).str.upper()=="NFL")
            & w["position"].astype(str).str.upper().isin(OFF_POS)
        ].copy()

        week_by_index={}
        for idx,r in w.iterrows():
            g=next_game(sch,r.get("team"))
            if g is not None:
                week_by_index[idx]=int(num(g.get("week")) or 0)

        target_weeks=sorted({v for v in week_by_index.values() if v})
        ppr_maps={week:prior_ppr_map(stats,week) for week in target_weeks}

        w["_role_baseline_raw"]=(
            pd.to_numeric(w.get("recent_role_value"),errors="coerce").fillna(0)
            + 0.05*pd.to_numeric(w.get("snap_pct"),errors="coerce").fillna(0)
        )
        w["_recent_ppr_raw"]=None
        for idx,r in w.iterrows():
            week=week_by_index.get(idx,0)
            pk=norm(r.get("player_key") or r.get("player"))
            team=clean(r.get("team")).upper()
            pmap=ppr_maps.get(week,{})
            w.at[idx,"_recent_ppr_raw"]=pmap.get((pk,team),pmap.get((pk,"")))

        w["_role_baseline_pct"]=w.groupby(
            w["position"].astype(str).str.upper()
        )["_role_baseline_raw"].rank(pct=True,method="average")*100
        w["_recent_ppr_baseline_pct"]=w.groupby(
            w["position"].astype(str).str.upper()
        )["_recent_ppr_raw"].rank(pct=True,method="average")*100

        for idx,r in w.iterrows():
            g=next_game(sch,r.get("team"))
            if g is None:
                continue
            ko=g.get("_kickoff")
            if pd.isna(ko) or pd.Timestamp(ko).to_pydatetime()<=now():
                continue
            week=int(num(g.get("week")) or 0)
            pk=clean(r.get("player_key"))
            if not week or not pk:
                continue
            key=f"{MODEL_VERSION}|WEEKLY|{week}|{pk}"
            if key in existing:
                continue
            team=clean(r.get("team")).upper()
            opp=clean(
                g.get(
                    "home_team"
                    if clean(g.get("away_team")).upper()==team
                    else "away_team"
                )
            ).upper()
            e={
                "event_type":"ENTRY",
                "forward_key":key,
                "model_version":MODEL_VERSION,
                "lane":"WEEKLY",
                "captured_at":iso(),
                "week":week,
                "kickoff":pd.Timestamp(ko).isoformat(),
                "player":clean(r.get("player")),
                "player_key":pk,
                "team":team,
                "position":clean(r.get("position")).upper(),
                "opponent":opp,
                "weekly_research_score":num(r.get("weekly_research_score")),
                "weekly_tier":clean(r.get("weekly_tier")),
                "role_snap_baseline_pct":num(r.get("_role_baseline_pct")),
                "recent_ppr_baseline_pct":num(r.get("_recent_ppr_baseline_pct")),
                "status":"PENDING",
            }
            append_jsonl(LEDGER,e)
            existing[key]=e
            added["WEEKLY"]+=1

    d=csv(DEFENSE)
    if not d.empty:
        for _,r in d.iterrows():
            team=clean(r.get("team")).upper()
            g=next_game(sch,team)
            if g is None:
                continue
            ko=g.get("_kickoff")
            if pd.isna(ko) or pd.Timestamp(ko).to_pydatetime()<=now():
                continue
            week=int(num(g.get("week")) or 0)
            if not week:
                continue
            key=f"{MODEL_VERSION}|DEFENSE_STREAMING|{week}|{team}"
            if key in existing:
                continue
            opp=clean(
                g.get(
                    "home_team"
                    if clean(g.get("away_team")).upper()==team
                    else "away_team"
                )
            ).upper()
            e={
                "event_type":"ENTRY",
                "forward_key":key,
                "model_version":MODEL_VERSION,
                "lane":"DEFENSE_STREAMING",
                "captured_at":iso(),
                "week":week,
                "kickoff":pd.Timestamp(ko).isoformat(),
                "team":team,
                "opponent":opp,
                "weekly_stream_score":num(r.get("weekly_stream_score")),
                "weekly_stream_tier":clean(r.get("weekly_stream_tier")),
                "schedule_baseline_score":num(r.get("schedule_research_score")),
                "status":"PENDING",
            }
            append_jsonl(LEDGER,e)
            existing[key]=e
            added["DEFENSE_STREAMING"]+=1

    f=csv(FAAB)
    if not f.empty:
        f=f[
            (f["sport"].astype(str).str.upper()=="NFL")
            & f["position"].astype(str).str.upper().isin(OFF_POS)
        ].copy()
        if not f.empty:
            f["_market_raw"]=-pd.to_numeric(
                f.get("add_rank_24h"),errors="coerce"
            )
            f["_role_raw"]=pd.to_numeric(
                f.get("role_score"),errors="coerce"
            )
            f["_market_baseline_pct"]=f.groupby(
                f["position"].astype(str).str.upper()
            )["_market_raw"].rank(pct=True,method="average")*100
            f["_role_baseline_pct"]=f.groupby(
                f["position"].astype(str).str.upper()
            )["_role_raw"].rank(pct=True,method="average")*100

            faab_week_by_index={}
            for idx,r in f.iterrows():
                g=next_game(sch,r.get("team"))
                if g is not None:
                    faab_week_by_index[idx]=int(num(g.get("week")) or 0)
            faab_target_weeks=sorted({
                v for v in faab_week_by_index.values() if v
            })
            faab_ppr_maps={
                week:prior_ppr_map(stats,week)
                for week in faab_target_weeks
            }
            f["_recent_ppr_raw"]=None
            for idx,r in f.iterrows():
                week=faab_week_by_index.get(idx,0)
                pk=norm(r.get("player_key") or r.get("player"))
                team=clean(r.get("team")).upper()
                pmap=faab_ppr_maps.get(week,{})
                f.at[idx,"_recent_ppr_raw"]=pmap.get(
                    (pk,team),pmap.get((pk,""))
                )
            f["_recent_ppr_baseline_pct"]=f.groupby(
                f["position"].astype(str).str.upper()
            )["_recent_ppr_raw"].rank(pct=True,method="average")*100

            for idx,r in f.iterrows():
                team=clean(r.get("team")).upper()
                pk=clean(r.get("player_key"))
                g=next_game(sch,team)
                if not team or not pk or g is None:
                    continue
                ko=g.get("_kickoff")
                if pd.isna(ko) or pd.Timestamp(ko).to_pydatetime()<=now():
                    continue
                week=int(num(g.get("week")) or 0)
                if not week:
                    continue
                key=f"{MODEL_VERSION}|FAAB|{week}|{pk}"
                if key in existing:
                    continue
                e={
                    "event_type":"ENTRY",
                    "forward_key":key,
                    "model_version":MODEL_VERSION,
                    "lane":"FAAB",
                    "captured_at":iso(),
                    "week":week,
                    "kickoff":pd.Timestamp(ko).isoformat(),
                    "player":clean(r.get("player")),
                    "player_key":pk,
                    "team":team,
                    "position":clean(r.get("position")).upper(),
                    "waiver_research_score":num(r.get("waiver_research_score")),
                    "waiver_priority":clean(r.get("waiver_priority")),
                    "suggested_faab_low_pct":num(r.get("suggested_faab_low_pct")),
                    "suggested_faab_high_pct":num(r.get("suggested_faab_high_pct")),
                    "add_rank_24h":num(r.get("add_rank_24h")),
                    "net_adds_24h":num(r.get("net_adds_24h")),
                    "market_activity_baseline_pct":num(r.get("_market_baseline_pct")),
                    "role_baseline_pct":num(r.get("_role_baseline_pct")),
                    "recent_ppr_baseline_pct":num(r.get("_recent_ppr_baseline_pct")),
                    "status":"PENDING",
                }
                append_jsonl(LEDGER,e)
                existing[key]=e
                added["FAAB"]+=1

    s=csv(STASH)
    if not s.empty:
        s=s[
            (s["sport"].astype(str).str.upper()=="NFL")
            & s["position"].astype(str).str.upper().isin(OFF_POS)
            & (pd.to_numeric(s.get("source_count"),errors="coerce")>=2)
            & (~s.get("source_disagreement",pd.Series(False,index=s.index)).fillna(False).astype(bool))
            & (~s["status"].astype(str).str.upper().isin({"AVAILABLE","ACTIVE","HEALTHY"}))
        ].copy()
        for _,r in s.iterrows():
            team=clean(r.get("team")).upper()
            pk=clean(r.get("player_key"))
            g=next_game(sch,team)
            if not team or not pk or g is None:
                continue
            ko=g.get("_kickoff")
            if pd.isna(ko) or pd.Timestamp(ko).to_pydatetime()<=now():
                continue
            week=int(num(g.get("week")) or 0)
            if not week:
                continue
            deadline=min(18,week+3)
            key=f"{MODEL_VERSION}|IR_STASH|{week}|{pk}"
            if key in existing:
                continue
            e={
                "event_type":"ENTRY",
                "forward_key":key,
                "model_version":MODEL_VERSION,
                "lane":"IR_STASH",
                "captured_at":iso(),
                "week":week,
                "capture_week":week,
                "deadline_week":deadline,
                "window_start_kickoff":pd.Timestamp(ko).isoformat(),
                "player":clean(r.get("player")),
                "player_key":pk,
                "team":team,
                "position":clean(r.get("position")).upper(),
                "injury_status":clean(r.get("status")).upper(),
                "injury_type":clean(r.get("injury_type")),
                "source_count":int(num(r.get("source_count")) or 0),
                "source_disagreement":False,
                "stash_research_score":num(r.get("stash_research_score")),
                "stash_tier":clean(r.get("stash_tier")),
                "return_date_claimed":False,
                "proof_window":"RETURN_WITHIN_4_NFL_WEEKS",
                "status":"PENDING",
            }
            append_jsonl(LEDGER,e)
            existing[key]=e
            added["IR_STASH"]+=1

    i=csv(IDP)
    if not i.empty:
        i=i[i["sport"].astype(str).str.upper()=="NFL"].copy()
        hard={"OUT","INACTIVE","INJURED_RESERVE","INJURED RESERVE","IR","SUSPENDED","PUP","NFI"}
        if "availability_status" in i.columns:
            i=i[
                ~i["availability_status"].astype(str).str.upper().isin(hard)
            ].copy()
        i["_snap_raw"]=pd.to_numeric(i.get("snap_pct"),errors="coerce")
        i["_role_delta_raw"]=pd.to_numeric(i.get("role_delta"),errors="coerce")
        i["_snap_baseline_pct"]=i.groupby(
            i["idp_group"].astype(str).str.upper()
        )["_snap_raw"].rank(pct=True,method="average")*100
        i["_role_delta_baseline_pct"]=i.groupby(
            i["idp_group"].astype(str).str.upper()
        )["_role_delta_raw"].rank(pct=True,method="average")*100

        for _,r in i.iterrows():
            team=clean(r.get("team")).upper()
            pk=clean(r.get("player_key"))
            g=next_game(sch,team)
            if not team or not pk or g is None:
                continue
            ko=g.get("_kickoff")
            if pd.isna(ko) or pd.Timestamp(ko).to_pydatetime()<=now():
                continue
            week=int(num(g.get("week")) or 0)
            if not week:
                continue
            key=f"{MODEL_VERSION}|IDP|{week}|{pk}"
            if key in existing:
                continue
            e={
                "event_type":"ENTRY",
                "forward_key":key,
                "model_version":MODEL_VERSION,
                "lane":"IDP",
                "captured_at":iso(),
                "week":week,
                "kickoff":pd.Timestamp(ko).isoformat(),
                "player":clean(r.get("player")),
                "player_key":pk,
                "team":team,
                "position":clean(r.get("position")).upper(),
                "idp_group":clean(r.get("idp_group")).upper(),
                "idp_usage_score":num(r.get("idp_usage_score")),
                "idp_usage_tier":clean(r.get("idp_usage_tier")),
                "snap_pct":num(r.get("snap_pct")),
                "role_delta":num(r.get("role_delta")),
                "snap_baseline_pct":num(r.get("_snap_baseline_pct")),
                "role_delta_baseline_pct":num(r.get("_role_delta_baseline_pct")),
                "status":"PENDING",
            }
            append_jsonl(LEDGER,e)
            existing[key]=e
            added["IDP"]+=1

    return {
        "status":"READY",
        "entries_added":added,
        "current_model_version":MODEL_VERSION,
        "ledger_unique_entries":len(canonical()),
    }

def statmap(stats):
    out={}
    for _,r in stats.iterrows():
        w=int(num(r.get("week")) or 0); pk=norm(r.get("player_display_name") or r.get("player_name")); team=clean(r.get("team")).upper()
        if w and pk: out[(w,pk,team)]=r; out[(w,pk,"")]=r
    return out

def idp_production_index(row):
    if row is None:
        return 0.0
    return round(float(
        (num(row.get("def_tackles_solo")) or 0.0)
        + 0.5*(num(row.get("def_tackle_assists")) or 0.0)
        + 1.0*(num(row.get("def_tackles_for_loss")) or 0.0)
        + 2.0*(num(row.get("def_sacks")) or 0.0)
        + 0.5*(num(row.get("def_qb_hits")) or 0.0)
        + 3.0*(num(row.get("def_interceptions")) or 0.0)
        + 1.0*(num(row.get("def_pass_defended")) or 0.0)
        + 2.0*(num(row.get("def_fumbles_forced")) or 0.0)
        + 2.0*(num(row.get("fumble_recovery_opp")) or 0.0)
        + 6.0*(num(row.get("def_tds")) or 0.0)
        + 2.0*(num(row.get("def_safeties")) or 0.0)
    ),3)

def settle():
    sch=load_schedule(); stats=csv(STATS); mp=statmap(stats); entries=canonical(); count=0
    week_values=pd.to_numeric(stats.get("week"),errors="coerce").dropna() if not stats.empty and "week" in stats.columns else pd.Series(dtype=float)
    max_completed_week=int(week_values.max()) if not week_values.empty else 0
    for key,r in entries.items():
        if clean(r.get("status")).upper()=="SETTLED":continue
        w=int(num(r.get("week")) or 0); lane=clean(r.get("lane")).upper()
        if not w:continue
        if lane=="WEEKLY":
            team=clean(r.get("team")).upper()
            if not team_game_final(sch,team,w):continue
            st=mp.get((w,norm(r.get("player_key") or r.get("player")),team)) or mp.get((w,norm(r.get("player_key") or r.get("player")),""))
            pts=0.0 if st is None else (num(st.get("fantasy_points_ppr")) or 0.0)
            pos=clean(r.get("position") if st is None else st.get("position") or r.get("position")).upper()
            append_jsonl(LEDGER,{"event_type":"SETTLED","forward_key":key,"status":"SETTLED","settled_at":iso(),"actual_ppr_points":round(float(pts),3),"actual_position":pos}); count+=1
        elif lane=="FAAB":
            team=clean(r.get("team")).upper()
            if not team_game_final(sch,team,w):continue
            st=mp.get((w,norm(r.get("player_key") or r.get("player")),team)) or mp.get((w,norm(r.get("player_key") or r.get("player")),""))
            pts=0.0 if st is None else (num(st.get("fantasy_points_ppr")) or 0.0)
            pos=clean(r.get("position") if st is None else st.get("position") or r.get("position")).upper()
            append_jsonl(LEDGER,{"event_type":"SETTLED","forward_key":key,"status":"SETTLED","settled_at":iso(),"actual_ppr_points":round(float(pts),3),"actual_position":pos}); count+=1
        elif lane=="IR_STASH":
            team=clean(r.get("team")).upper()
            pk=norm(r.get("player_key") or r.get("player"))
            start_week=int(num(r.get("capture_week")) or w)
            deadline=int(num(r.get("deadline_week")) or min(18,start_week+3))
            returned=None
            for week in range(start_week,min(deadline,max_completed_week)+1):
                st=mp.get((week,pk,team)) or mp.get((week,pk,""))
                if st is not None:
                    returned=(week,st)
                    break
            if returned is not None:
                return_week,st=returned
                pts=num(st.get("fantasy_points_ppr")) or 0.0
                append_jsonl(LEDGER,{"event_type":"SETTLED","forward_key":key,"status":"SETTLED","settled_at":iso(),"returned_within_4_weeks":True,"return_week":int(return_week),"weeks_to_return":int(return_week-start_week),"first_return_ppr":round(float(pts),3)}); count+=1
            elif max_completed_week>=deadline:
                append_jsonl(LEDGER,{"event_type":"SETTLED","forward_key":key,"status":"SETTLED","settled_at":iso(),"returned_within_4_weeks":False,"return_week":None,"weeks_to_return":None,"first_return_ppr":0.0}); count+=1
        elif lane=="IDP":
            team=clean(r.get("team")).upper()
            if not team_game_final(sch,team,w):continue
            st=mp.get((w,norm(r.get("player_key") or r.get("player")),team)) or mp.get((w,norm(r.get("player_key") or r.get("player")),""))
            idx=idp_production_index(st)
            append_jsonl(LEDGER,{"event_type":"SETTLED","forward_key":key,"status":"SETTLED","settled_at":iso(),"actual_idp_production_index":idx}); count+=1
        elif lane=="DEFENSE_STREAMING":
            team=clean(r.get("team")).upper()
            if not team_game_final(sch,team,w):continue
            pts=defense_points(team,w,stats,sch)
            if pts is None:continue
            append_jsonl(LEDGER,{"event_type":"SETTLED","forward_key":key,"status":"SETTLED","settled_at":iso(),"actual_dst_points":round(float(pts),3)}); count+=1
    return count

def lcb90(vals):
    vals=[float(x) for x in vals if x is not None and not math.isnan(float(x))]
    if len(vals)<2:return len(vals),None
    avg=sum(vals)/len(vals); var=sum((x-avg)**2 for x in vals)/(len(vals)-1); se=math.sqrt(max(0,var)/len(vals))
    return len(vals),round(avg-1.645*se,4)

def weekly_summary(rows):
    settled=[
        r for r in rows
        if r.get("lane")=="WEEKLY"
        and clean(r.get("status")).upper()=="SETTLED"
        and num(r.get("weekly_research_score")) is not None
    ]

    groups=defaultdict(list)
    for r in settled:
        groups[
            (int(r.get("week") or 0),clean(r.get("position")).upper())
        ].append(r)

    for group in groups.values():
        vals=pd.Series(
            [num(r.get("actual_ppr_points")) or 0 for r in group],
            dtype=float,
        )
        ranks=vals.rank(pct=True,method="average")*100
        for r,p in zip(group,ranks):
            r["actual_position_percentile"]=round(float(p),2)

    blocks=[]
    if settled:
        frame=pd.DataFrame(settled)
        for week,g in frame.groupby("week"):
            if len(g)<30:
                continue
            actual=pd.to_numeric(
                g["actual_position_percentile"],errors="coerce"
            )
            hulk=pd.to_numeric(
                g["weekly_research_score"],errors="coerce"
            )
            role=pd.to_numeric(
                g.get("role_snap_baseline_pct"),errors="coerce"
            )
            recent=pd.to_numeric(
                g.get("recent_ppr_baseline_pct"),errors="coerce"
            )
            valid_h=hulk.notna()&actual.notna()
            if valid_h.sum()<30:
                continue

            h_corr=hulk[valid_h].corr(
                actual[valid_h],method="spearman"
            )
            role_corr=None
            recent_corr=None

            if role is not None:
                valid_r=role.notna()&actual.notna()
                if valid_r.sum()>=30:
                    rc=role[valid_r].corr(
                        actual[valid_r],method="spearman"
                    )
                    role_corr=None if pd.isna(rc) else float(rc)

            if recent is not None:
                valid_p=recent.notna()&actual.notna()
                if valid_p.sum()>=30:
                    pc=recent[valid_p].corr(
                        actual[valid_p],method="spearman"
                    )
                    recent_corr=None if pd.isna(pc) else float(pc)

            hulk_corr=None if pd.isna(h_corr) else float(h_corr)
            q=hulk[valid_h].quantile(.75)
            top=actual[valid_h][hulk[valid_h]>=q]
            rest=actual[valid_h][hulk[valid_h]<q]

            blocks.append({
                "week":int(week),
                "players":int(valid_h.sum()),
                "hulk_spearman":hulk_corr,
                "role_snap_spearman":role_corr,
                "recent_ppr_spearman":recent_corr,
                "hulk_minus_role_snap":(
                    None
                    if hulk_corr is None or role_corr is None
                    else hulk_corr-role_corr
                ),
                "hulk_minus_recent_ppr":(
                    None
                    if hulk_corr is None or recent_corr is None
                    else hulk_corr-recent_corr
                ),
                "top_quartile_actual_percentile_advantage":(
                    None
                    if not len(top) or not len(rest)
                    else float(top.mean()-rest.mean())
                ),
            })

    hulk_corrs=[
        x["hulk_spearman"] for x in blocks
        if x["hulk_spearman"] is not None
    ]
    role_corrs=[
        x["role_snap_spearman"] for x in blocks
        if x["role_snap_spearman"] is not None
    ]
    recent_corrs=[
        x["recent_ppr_spearman"] for x in blocks
        if x["recent_ppr_spearman"] is not None
    ]
    role_adv=[
        x["hulk_minus_role_snap"] for x in blocks
        if x["hulk_minus_role_snap"] is not None
    ]
    recent_adv=[
        x["hulk_minus_recent_ppr"] for x in blocks
        if x["hulk_minus_recent_ppr"] is not None
    ]
    quartile_adv=[
        x["top_quartile_actual_percentile_advantage"] for x in blocks
        if x["top_quartile_actual_percentile_advantage"] is not None
    ]

    wn,hulk_lcb=lcb90(hulk_corrs)
    _,role_adv_lcb=lcb90(role_adv)
    _,recent_adv_lcb=lcb90(recent_adv)
    _,quartile_lcb=lcb90(quartile_adv)

    sample_ready=len(settled)>=200 and wn>=6
    beats_baselines=(
        role_adv_lcb is not None and role_adv_lcb>0
        and recent_adv_lcb is not None and recent_adv_lcb>0
    )
    ranking_supported=(
        hulk_lcb is not None and hulk_lcb>0
        and quartile_lcb is not None and quartile_lcb>0
    )

    if not sample_ready:
        proof="BUILDING_FORWARD_SAMPLE"
    elif ranking_supported and beats_baselines:
        proof="RANKING_REVIEW_CANDIDATE"
    elif ranking_supported:
        proof="RANKING_SIGNAL_BUT_NO_BASELINE_EDGE"
    else:
        proof="RANKING_NOT_PROVEN"

    return {
        "tracked":sum(r.get("lane")=="WEEKLY" for r in rows),
        "settled":len(settled),
        "independent_weeks":len(blocks),
        "mean_weekly_spearman":(
            None if not hulk_corrs
            else round(sum(hulk_corrs)/len(hulk_corrs),4)
        ),
        "spearman_lcb90":hulk_lcb,
        "mean_role_snap_spearman":(
            None if not role_corrs
            else round(sum(role_corrs)/len(role_corrs),4)
        ),
        "mean_recent_ppr_spearman":(
            None if not recent_corrs
            else round(sum(recent_corrs)/len(recent_corrs),4)
        ),
        "mean_hulk_minus_role_snap":(
            None if not role_adv
            else round(sum(role_adv)/len(role_adv),4)
        ),
        "hulk_minus_role_snap_lcb90":role_adv_lcb,
        "mean_hulk_minus_recent_ppr":(
            None if not recent_adv
            else round(sum(recent_adv)/len(recent_adv),4)
        ),
        "hulk_minus_recent_ppr_lcb90":recent_adv_lcb,
        "mean_top_quartile_actual_percentile_advantage":(
            None if not quartile_adv
            else round(sum(quartile_adv)/len(quartile_adv),2)
        ),
        "top_quartile_advantage_lcb90":quartile_lcb,
        "proof_status":proof,
        "automatic_promotion":False,
    }

def defense_summary(rows):
    settled=[
        r for r in rows
        if r.get("lane")=="DEFENSE_STREAMING"
        and clean(r.get("status")).upper()=="SETTLED"
        and num(r.get("weekly_stream_score")) is not None
        and num(r.get("actual_dst_points")) is not None
    ]
    blocks=[]
    if settled:
        frame=pd.DataFrame(settled)
        for week,g in frame.groupby("week"):
            if len(g)<16:
                continue
            hulk=pd.to_numeric(g["weekly_stream_score"],errors="coerce")
            base=pd.to_numeric(g.get("schedule_baseline_score"),errors="coerce")
            actual=pd.to_numeric(g["actual_dst_points"],errors="coerce")
            valid=hulk.notna()&actual.notna()
            if valid.sum()<16:
                continue
            hc=hulk[valid].corr(actual[valid],method="spearman")
            hulk_corr=None if pd.isna(hc) else float(hc)

            base_corr=None
            if base is not None:
                valid_b=base.notna()&actual.notna()
                if valid_b.sum()>=16:
                    bc=base[valid_b].corr(actual[valid_b],method="spearman")
                    base_corr=None if pd.isna(bc) else float(bc)

            blocks.append({
                "week":int(week),
                "teams":int(valid.sum()),
                "hulk_spearman":hulk_corr,
                "schedule_baseline_spearman":base_corr,
                "hulk_minus_schedule":(
                    None
                    if hulk_corr is None or base_corr is None
                    else hulk_corr-base_corr
                ),
            })

    corrs=[
        x["hulk_spearman"] for x in blocks
        if x["hulk_spearman"] is not None
    ]
    base_corrs=[
        x["schedule_baseline_spearman"] for x in blocks
        if x["schedule_baseline_spearman"] is not None
    ]
    edge=[
        x["hulk_minus_schedule"] for x in blocks
        if x["hulk_minus_schedule"] is not None
    ]
    wn,hulk_lcb=lcb90(corrs)
    _,edge_lcb=lcb90(edge)

    if len(settled)<100 or wn<6:
        proof="BUILDING_FORWARD_SAMPLE"
    elif (
        hulk_lcb is not None and hulk_lcb>0
        and edge_lcb is not None and edge_lcb>0
    ):
        proof="STREAM_RANKING_REVIEW_CANDIDATE"
    elif hulk_lcb is not None and hulk_lcb>0:
        proof="STREAM_SIGNAL_BUT_NO_BASELINE_EDGE"
    else:
        proof="STREAM_RANKING_NOT_PROVEN"

    return {
        "tracked":sum(r.get("lane")=="DEFENSE_STREAMING" for r in rows),
        "settled":len(settled),
        "independent_weeks":len(blocks),
        "mean_weekly_spearman":(
            None if not corrs else round(sum(corrs)/len(corrs),4)
        ),
        "spearman_lcb90":hulk_lcb,
        "mean_schedule_baseline_spearman":(
            None if not base_corrs
            else round(sum(base_corrs)/len(base_corrs),4)
        ),
        "mean_hulk_minus_schedule":(
            None if not edge else round(sum(edge)/len(edge),4)
        ),
        "hulk_minus_schedule_lcb90":edge_lcb,
        "proof_status":proof,
        "automatic_promotion":False,
    }


def faab_summary(rows):
    settled=[
        r for r in rows
        if r.get("lane")=="FAAB"
        and clean(r.get("status")).upper()=="SETTLED"
        and num(r.get("waiver_research_score")) is not None
    ]

    groups=defaultdict(list)
    for r in settled:
        groups[
            (int(r.get("week") or 0),clean(r.get("position")).upper())
        ].append(r)
    for group in groups.values():
        vals=pd.Series(
            [num(r.get("actual_ppr_points")) or 0.0 for r in group],
            dtype=float,
        )
        ranks=vals.rank(pct=True,method="average")*100
        for r,p in zip(group,ranks):
            r["actual_waiver_position_percentile"]=round(float(p),2)

    blocks=[]
    if settled:
        frame=pd.DataFrame(settled)
        for week,g in frame.groupby("week"):
            if len(g)<40:
                continue
            actual=pd.to_numeric(
                g["actual_waiver_position_percentile"],errors="coerce"
            )
            hulk=pd.to_numeric(
                g["waiver_research_score"],errors="coerce"
            )
            market=pd.to_numeric(
                g.get("market_activity_baseline_pct"),errors="coerce"
            )
            role=pd.to_numeric(
                g.get("role_baseline_pct"),errors="coerce"
            )
            recent=pd.to_numeric(
                g.get("recent_ppr_baseline_pct"),errors="coerce"
            )
            valid=hulk.notna()&actual.notna()
            if valid.sum()<40:
                continue

            hc=hulk[valid].corr(actual[valid],method="spearman")
            hulk_corr=None if pd.isna(hc) else float(hc)

            def corr_of(series):
                if series is None:
                    return None
                mask=series.notna()&actual.notna()
                if mask.sum()<25:
                    return None
                value=series[mask].corr(actual[mask],method="spearman")
                return None if pd.isna(value) else float(value)

            market_corr=corr_of(market)
            role_corr=corr_of(role)
            recent_corr=corr_of(recent)

            q=hulk[valid].quantile(.75)
            top=actual[valid][hulk[valid]>=q]
            rest=actual[valid][hulk[valid]<q]

            blocks.append({
                "week":int(week),
                "players":int(valid.sum()),
                "hulk_spearman":hulk_corr,
                "market_activity_spearman":market_corr,
                "role_spearman":role_corr,
                "recent_ppr_spearman":recent_corr,
                "hulk_minus_market":(
                    None if hulk_corr is None or market_corr is None
                    else hulk_corr-market_corr
                ),
                "hulk_minus_role":(
                    None if hulk_corr is None or role_corr is None
                    else hulk_corr-role_corr
                ),
                "hulk_minus_recent_ppr":(
                    None if hulk_corr is None or recent_corr is None
                    else hulk_corr-recent_corr
                ),
                "top_quartile_actual_percentile_advantage":(
                    None if not len(top) or not len(rest)
                    else float(top.mean()-rest.mean())
                ),
            })

    hulk_corrs=[x["hulk_spearman"] for x in blocks if x["hulk_spearman"] is not None]
    market_corrs=[x["market_activity_spearman"] for x in blocks if x["market_activity_spearman"] is not None]
    role_corrs=[x["role_spearman"] for x in blocks if x["role_spearman"] is not None]
    recent_corrs=[x["recent_ppr_spearman"] for x in blocks if x["recent_ppr_spearman"] is not None]
    market_adv=[x["hulk_minus_market"] for x in blocks if x["hulk_minus_market"] is not None]
    role_adv=[x["hulk_minus_role"] for x in blocks if x["hulk_minus_role"] is not None]
    recent_adv=[x["hulk_minus_recent_ppr"] for x in blocks if x["hulk_minus_recent_ppr"] is not None]
    quartile_adv=[
        x["top_quartile_actual_percentile_advantage"]
        for x in blocks
        if x["top_quartile_actual_percentile_advantage"] is not None
    ]

    wn,hulk_lcb=lcb90(hulk_corrs)
    _,market_lcb=lcb90(market_adv)
    _,role_lcb=lcb90(role_adv)
    _,recent_lcb=lcb90(recent_adv)
    _,quartile_lcb=lcb90(quartile_adv)

    sample_ready=len(settled)>=100 and wn>=6
    baseline_edge=(
        market_lcb is not None and market_lcb>0
        and role_lcb is not None and role_lcb>0
        and (recent_lcb is None or recent_lcb>0)
    )
    ranking_supported=(
        hulk_lcb is not None and hulk_lcb>0
        and quartile_lcb is not None and quartile_lcb>0
    )

    if not sample_ready:
        proof="BUILDING_FORWARD_SAMPLE"
    elif ranking_supported and baseline_edge:
        proof="WAIVER_RANKING_REVIEW_CANDIDATE"
    elif ranking_supported:
        proof="WAIVER_SIGNAL_BUT_NO_BASELINE_EDGE"
    else:
        proof="WAIVER_RANKING_NOT_PROVEN"

    return {
        "tracked":sum(r.get("lane")=="FAAB" for r in rows),
        "settled":len(settled),
        "independent_weeks":len(blocks),
        "mean_weekly_spearman":None if not hulk_corrs else round(sum(hulk_corrs)/len(hulk_corrs),4),
        "spearman_lcb90":hulk_lcb,
        "mean_market_activity_spearman":None if not market_corrs else round(sum(market_corrs)/len(market_corrs),4),
        "mean_role_spearman":None if not role_corrs else round(sum(role_corrs)/len(role_corrs),4),
        "mean_recent_ppr_spearman":None if not recent_corrs else round(sum(recent_corrs)/len(recent_corrs),4),
        "hulk_minus_market_lcb90":market_lcb,
        "hulk_minus_role_lcb90":role_lcb,
        "hulk_minus_recent_ppr_lcb90":recent_lcb,
        "top_quartile_advantage_lcb90":quartile_lcb,
        "proof_status":proof,
        "faab_bid_range_proof_status":"NOT_MEASURED_NO_LEAGUE_TRANSACTION_PRICE_DATA",
        "automatic_promotion":False,
    }


def stash_summary(rows):
    settled=[
        r for r in rows
        if r.get("lane")=="IR_STASH"
        and clean(r.get("status")).upper()=="SETTLED"
        and num(r.get("stash_research_score")) is not None
    ]
    blocks=[]
    if settled:
        frame=pd.DataFrame(settled)
        for week,g in frame.groupby("capture_week"):
            if len(g)<10:
                continue
            score=pd.to_numeric(g["stash_research_score"],errors="coerce")
            returned=g["returned_within_4_weeks"].fillna(False).astype(bool).astype(float)
            ppr=pd.to_numeric(g["first_return_ppr"],errors="coerce").fillna(0)
            valid=score.notna()
            if valid.sum()<10:
                continue
            q=score[valid].quantile(.75)
            top=score[valid]>=q
            rest=score[valid]<q
            if top.sum()==0 or rest.sum()==0:
                continue
            blocks.append({
                "capture_week":int(week),
                "players":int(valid.sum()),
                "top_quartile_return_rate_advantage":float(
                    returned[valid][top].mean()-returned[valid][rest].mean()
                ),
                "top_quartile_first_return_ppr_advantage":float(
                    ppr[valid][top].mean()-ppr[valid][rest].mean()
                ),
                "overall_return_rate":float(returned[valid].mean()),
            })

    return_adv=[
        x["top_quartile_return_rate_advantage"]
        for x in blocks
    ]
    ppr_adv=[
        x["top_quartile_first_return_ppr_advantage"]
        for x in blocks
    ]
    _,return_lcb=lcb90(return_adv)
    wn,ppr_lcb=lcb90(ppr_adv)

    if len(settled)<60 or wn<6:
        proof="BUILDING_FORWARD_SAMPLE"
    elif (
        return_lcb is not None and return_lcb>0
        and ppr_lcb is not None and ppr_lcb>0
    ):
        proof="STASH_UTILITY_REVIEW_CANDIDATE"
    else:
        proof="STASH_UTILITY_NOT_PROVEN"

    return {
        "tracked":sum(r.get("lane")=="IR_STASH" for r in rows),
        "settled":len(settled),
        "independent_capture_weeks":len(blocks),
        "returned_within_4_weeks":sum(
            bool(r.get("returned_within_4_weeks")) for r in settled
        ),
        "return_within_4_weeks_rate_pct":(
            None if not settled else round(
                100*sum(bool(r.get("returned_within_4_weeks")) for r in settled)/len(settled),1
            )
        ),
        "mean_top_quartile_return_rate_advantage":(
            None if not return_adv else round(sum(return_adv)/len(return_adv),4)
        ),
        "return_rate_advantage_lcb90":return_lcb,
        "mean_top_quartile_first_return_ppr_advantage":(
            None if not ppr_adv else round(sum(ppr_adv)/len(ppr_adv),2)
        ),
        "first_return_ppr_advantage_lcb90":ppr_lcb,
        "dated_return_accuracy_status":"NOT_AVAILABLE_NO_DATED_NFL_RETURN_SIGNALS",
        "proof_status":proof,
        "automatic_promotion":False,
    }


def idp_summary(rows):
    settled=[
        r for r in rows
        if r.get("lane")=="IDP"
        and clean(r.get("status")).upper()=="SETTLED"
        and num(r.get("idp_usage_score")) is not None
        and num(r.get("actual_idp_production_index")) is not None
    ]

    groups=defaultdict(list)
    for r in settled:
        groups[
            (int(r.get("week") or 0),clean(r.get("idp_group")).upper())
        ].append(r)
    for group in groups.values():
        vals=pd.Series(
            [num(r.get("actual_idp_production_index")) or 0.0 for r in group],
            dtype=float,
        )
        ranks=vals.rank(pct=True,method="average")*100
        for r,p in zip(group,ranks):
            r["actual_idp_group_percentile"]=round(float(p),2)

    blocks=[]
    if settled:
        frame=pd.DataFrame(settled)
        for week,g in frame.groupby("week"):
            if len(g)<100:
                continue
            actual=pd.to_numeric(
                g["actual_idp_group_percentile"],errors="coerce"
            )
            hulk=pd.to_numeric(g["idp_usage_score"],errors="coerce")
            snap=pd.to_numeric(g.get("snap_baseline_pct"),errors="coerce")
            role=pd.to_numeric(g.get("role_delta_baseline_pct"),errors="coerce")
            valid=hulk.notna()&actual.notna()
            if valid.sum()<100:
                continue
            hc=hulk[valid].corr(actual[valid],method="spearman")
            hulk_corr=None if pd.isna(hc) else float(hc)

            def corr_of(series):
                if series is None:
                    return None
                mask=series.notna()&actual.notna()
                if mask.sum()<75:
                    return None
                value=series[mask].corr(actual[mask],method="spearman")
                return None if pd.isna(value) else float(value)

            snap_corr=corr_of(snap)
            role_corr=corr_of(role)
            q=hulk[valid].quantile(.75)
            top=actual[valid][hulk[valid]>=q]
            rest=actual[valid][hulk[valid]<q]
            blocks.append({
                "week":int(week),
                "players":int(valid.sum()),
                "hulk_spearman":hulk_corr,
                "snap_spearman":snap_corr,
                "role_delta_spearman":role_corr,
                "hulk_minus_snap":(
                    None if hulk_corr is None or snap_corr is None
                    else hulk_corr-snap_corr
                ),
                "hulk_minus_role_delta":(
                    None if hulk_corr is None or role_corr is None
                    else hulk_corr-role_corr
                ),
                "top_quartile_actual_percentile_advantage":(
                    None if not len(top) or not len(rest)
                    else float(top.mean()-rest.mean())
                ),
            })

    hulk_corrs=[x["hulk_spearman"] for x in blocks if x["hulk_spearman"] is not None]
    snap_adv=[x["hulk_minus_snap"] for x in blocks if x["hulk_minus_snap"] is not None]
    role_adv=[x["hulk_minus_role_delta"] for x in blocks if x["hulk_minus_role_delta"] is not None]
    quartile_adv=[
        x["top_quartile_actual_percentile_advantage"]
        for x in blocks
        if x["top_quartile_actual_percentile_advantage"] is not None
    ]
    wn,hulk_lcb=lcb90(hulk_corrs)
    _,snap_lcb=lcb90(snap_adv)
    _,role_lcb=lcb90(role_adv)
    _,quartile_lcb=lcb90(quartile_adv)

    sample_ready=len(settled)>=250 and wn>=6
    ranking_supported=(
        hulk_lcb is not None and hulk_lcb>0
        and quartile_lcb is not None and quartile_lcb>0
    )
    baseline_edge=(
        snap_lcb is not None and snap_lcb>0
        and (role_lcb is None or role_lcb>0)
    )
    if not sample_ready:
        proof="BUILDING_FORWARD_SAMPLE"
    elif ranking_supported and baseline_edge:
        proof="IDP_USAGE_REVIEW_CANDIDATE"
    elif ranking_supported:
        proof="IDP_SIGNAL_BUT_NO_BASELINE_EDGE"
    else:
        proof="IDP_USAGE_NOT_PROVEN"

    return {
        "tracked":sum(r.get("lane")=="IDP" for r in rows),
        "settled":len(settled),
        "independent_weeks":len(blocks),
        "mean_weekly_spearman":None if not hulk_corrs else round(sum(hulk_corrs)/len(hulk_corrs),4),
        "spearman_lcb90":hulk_lcb,
        "hulk_minus_snap_lcb90":snap_lcb,
        "hulk_minus_role_delta_lcb90":role_lcb,
        "top_quartile_advantage_lcb90":quartile_lcb,
        "production_metric":"GENERIC_IDP_PRODUCTION_INDEX_NOT_LEAGUE_FANTASY_POINTS",
        "league_scoring_proof_status":"NOT_MEASURED_WITHOUT_CONNECTED_SCORING_SETTINGS",
        "proof_status":proof,
        "automatic_promotion":False,
    }

def main():
    current=readiness()
    cap=capture()
    settled=settle()
    rows=[
        r for r in canonical().values()
        if clean(r.get("model_version"))==MODEL_VERSION
    ]
    forward={
        "generated_at":iso(),
        "status":"READY",
        "model_version":MODEL_VERSION,
        "capture":cap,
        "settled_now":settled,
        "weekly":weekly_summary(rows),
        "faab":faab_summary(rows),
        "ir_stash":stash_summary(rows),
        "defense_streaming":defense_summary(rows),
        "idp":idp_summary(rows),
        "trade_rate_team":{
            "proof_status":"REQUIRES_CONNECTED_LEAGUE_CONTEXT",
            "automatic_promotion":False,
        },
        "rules":[
            "Signals are frozen before kickoff or before the stash evaluation window begins.",
            "Weekly proof uses actual PPR results normalized within position and must beat role/snap and recent-PPR baselines.",
            "Waiver/FAAB ranking proof uses next-game PPR quality and must beat market-add activity and role baselines; FAAB bid percentages remain unvalidated without league transaction prices.",
            "IR stash proof measures source-supported four-NFL-week return utility; it does not claim return-date accuracy when no dated return signal exists.",
            "Defense proof uses a generic D/ST scoring benchmark and must beat the schedule-only ranking baseline.",
            "IDP proof uses a generic defensive production index and must beat snap-share/role-delta baselines; league-specific fantasy scoring is not claimed.",
            "Independent week count blocks one-week sample inflation.",
            "At least six independent weeks are required before any review-candidate status.",
            "Trade and Rate My Team remain blocked until connected league, roster and scoring context exists.",
            "No live changes occur automatically.",
        ],
    }
    for path,payload in [
        (CURRENT_OUT,current),
        (FORWARD_OUT,forward),
        (PUBLIC/"fantasy_v2_current.json",current),
        (PUBLIC/"fantasy_v2_forward.json",forward),
    ]:
        write_json(path,payload)
    if DIST.exists():
        write_json(DIST/"fantasy_v2_current.json",current)
        write_json(DIST/"fantasy_v2_forward.json",forward)
    print(json.dumps({
        "status":"READY",
        "current":current["lanes"],
        "capture":cap,
        "settled_now":settled,
        "weekly":forward["weekly"],
        "faab":forward["faab"],
        "ir_stash":forward["ir_stash"],
        "defense_streaming":forward["defense_streaming"],
        "idp":forward["idp"],
    },indent=2))
if __name__=="__main__":main()
