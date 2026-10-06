#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import csv
import json
import subprocess
import urllib.request

import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
WH = ROOT/"intelligence_warehouse"
OUT = WH/"freshness"
CATALOG = WH/"catalog.json"
DATASETS = OUT/"DATASET_FRESHNESS_CURRENT.csv"
PIPELINES_OUT = OUT/"PIPELINE_HEALTH_CURRENT.csv"
GAPS = OUT/"FRESHNESS_GAPS.csv"
RECEIPT = OUT/"FRESHNESS_RECEIPT.json"
NOW_DT = datetime.now(timezone.utc)
NOW = NOW_DT.isoformat()

PIPELINES = [
    ("NFL","sports-hulk-nfl-refresh.service",90,"nfl_live/decision/NFL_REFRESH_GOVERNANCE_RECEIPT.json"),
    ("NBA","sports-hulk-nba-refresh.service",25,"nba_live/decision/NBA_DECISION_SUMMARY.json"),
    ("NHL","sports-hulk-nhl-refresh.service",25,"nhl_live/decision/NHL_DECISION_SUMMARY.json"),
    ("MLB","sports-hulk-mlb-refresh.service",25,"mlb_live/decision/MLB_DECISION_SUMMARY.json"),
    ("CFB","sports-hulk-cfb-refresh.service",25,"cfb_live/decision/CFB_DECISION_SUMMARY.json"),
    ("CBB","sports-hulk-cbb-refresh.service",25,"cbb_live/decision/CBB_DECISION_SUMMARY.json"),
    ("CONTENT","sports-hulk-content-refresh.service",30,"sports_content/derived/ARTICLE_DRAFTS.csv"),
    ("ARCHIVE","sports-hulk-intelligence-archive.service",90,"intelligence_warehouse/registry/SNAPSHOT_RUNS.csv"),
]

def file_age_minutes(path):
    if not path.exists():
        return None
    ts = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    return max(0.0,(NOW_DT-ts).total_seconds()/60)

def count_rows(path):
    if not path.exists():
        return None
    try:
        if path.suffix.lower()==".csv":
            with path.open("r",encoding="utf-8",errors="ignore") as fh:
                return max(sum(1 for _ in fh)-1,0)
        if path.suffix.lower()==".json":
            obj=json.loads(path.read_text())
            if isinstance(obj,list):
                return len(obj)
            if isinstance(obj,dict):
                for k in ["rows","records","items","files"]:
                    if isinstance(obj.get(k),list):
                        return len(obj[k])
                return 1
    except Exception:
        return None
    return None

def max_age_minutes(sport,lane):
    sport=str(sport).upper()
    lane=str(lane).lower()
    if sport=="SURVIVOR":
        return 60*24*8
    if sport=="NFL":
        return 90
    if sport in {"NBA","NHL","MLB","CFB","CBB"}:
        return 25
    if sport=="CONTENT":
        return 30
    if sport in {
        "FEATURES", "SCHEDULE", "FANTASY_MARKET",
        "DFS", "NEWS_GRAPH", "STARTERS"
    }:
        return 30
    if sport=="TEAM_STYLE":
        return 180
    if sport=="MATCHUP_STYLE":
        return 30
    if sport=="PLAYER_OPPORTUNITY":
        return 30
    if sport=="DEFENSIVE_PRESSURE":
        return 30
    if sport=="MLB_PLAYER_HISTORY":
        if lane in {
            "player_game_history",
            "completed_game_index",
            "source_catalog",
            "feature_catalog",
            "receipt",
        }:
            return 60*24*30
        return 360
    if sport in {"FANTASY_DECISIONS","HISTORY_COVERAGE"}:
        return 30
    if sport=="SIGNAL_CALIBRATION":
        return 360
    if sport=="EVIDENCE_GATES":
        return 30 if lane=="current_player" else 360
    if sport=="SIGNAL_CONSENSUS":
        return 30
    if sport=="DECISION_READINESS":
        return 30
    if sport=="PREGAME_COHORTS":
        return 30
    if sport=="POSTGAME_GRADING":
        return 30
    if sport=="COHORT_LEARNING":
        return 30
    if sport=="LEARNING_GOVERNANCE":
        return 30
    if sport=="AVAILABILITY":
        if lane in {"timeline","transitions"}:
            return 60*24
        return 30
    if sport=="MARKETS":
        if lane=="pregame_closes":
            return 60*24*7
        return 30
    if sport=="CBB_EFFICIENCY":
        if lane in {"prior_raw","prior_baseline"}:
            return 60*24*30
        if lane=="possession_game_history":
            return 60*24
        return 30
    if sport=="FRESHNESS":
        return 30
    return 120

def freshness_status(exists,age,max_age):
    if not exists:
        return "MISSING"
    if age is None:
        return "UNKNOWN"
    if age <= max_age:
        return "FRESH"
    if age <= max_age*2:
        return "AGING"
    return "STALE"

def row_state(sport,lane,rows):
    if rows is None:
        return "UNKNOWN"
    if rows>0:
        return "HAS_ROWS"
    sport=str(sport).upper()
    lane=str(lane).lower()
    if sport=="CBB" and lane in {"market","game_decision","game_finalists"}:
        return "EMPTY_EXPECTED_PRESEASON"
    if sport=="CBB_EFFICIENCY" and lane=="possession_game_history":
        return "EMPTY_EXPECTED_PRESEASON"
    if sport=="STARTERS" and lane=="changes":
        return "EMPTY_EXPECTED_NO_CHANGES"
    if sport=="POSTGAME_GRADING" and lane=="summary":
        return "EMPTY_EXPECTED_NO_COMPLETED_GAMES"
    if sport=="COHORT_LEARNING" and lane=="performance":
        return "EMPTY_EXPECTED_NO_COMPLETED_GAMES"
    return "EMPTY_REVIEW"

def nfl_governance_mode():
    p=ROOT/"nfl_live/decision/NFL_REFRESH_GOVERNANCE_RECEIPT.json"
    try:
        return json.loads(p.read_text()).get("mode","")
    except Exception:
        return ""

def build_datasets():
    cfg=json.loads(CATALOG.read_text())
    rows=[]
    nfl_mode=nfl_governance_mode()
    nfl_paid_lanes={
        "game_decision","game_finalists","prop_decision",
        "pickem_decision","market","decision_receipt","parlay_receipt"
    }
    for entry in cfg["files"]:
        sport=entry["sport"]
        if str(sport).upper()=="FRESHNESS":
            continue
        lane=entry["lane"]
        rel=entry["path"]
        path=ROOT/rel
        exists=path.exists()
        age=file_age_minutes(path)
        max_age=max_age_minutes(sport,lane)
        n=count_rows(path)
        status=freshness_status(exists,age,max_age)
        if (
            str(sport).upper()=="NFL"
            and nfl_mode=="FREE_CONTEXT_ONLY"
            and lane in nfl_paid_lanes
            and status in {"AGING","STALE"}
        ):
            status="GOVERNED_IDLE"
        if (
            str(sport).upper()=="NFL"
            and nfl_mode!="FREE_CONTEXT_ONLY"
            and lane=="free_status_receipt"
            and status in {"AGING","STALE"}
        ):
            status="GOVERNED_IDLE"
        stat=path.stat() if exists else None
        rows.append({
            "sport":sport,
            "lane":lane,
            "path":rel,
            "exists":exists,
            "bytes":int(stat.st_size) if stat else None,
            "row_count":n,
            "source_mtime_utc":(
                datetime.fromtimestamp(
                    stat.st_mtime,timezone.utc
                ).isoformat() if stat else ""
            ),
            "age_minutes":round(age,2) if age is not None else None,
            "max_age_minutes":max_age,
            "freshness_status":status,
            "row_state":row_state(sport,lane,n),
            "checked_at":NOW,
        })
    return pd.DataFrame(rows)

def systemctl_state(unit):
    props=[
        "ActiveState","SubState","Result","ExecMainStatus",
        "ExecMainStartTimestamp","ExecMainExitTimestamp"
    ]
    cmd=["systemctl","show",unit,"--no-pager"]+[
        f"--property={p}" for p in props
    ]
    try:
        p=subprocess.run(
            cmd,capture_output=True,text=True,timeout=3
        )
        out={}
        for line in p.stdout.splitlines():
            if "=" in line:
                k,v=line.split("=",1)
                out[k]=v
        out["_returncode"]=p.returncode
        return out
    except Exception as exc:
        return {"_returncode":1,"_error":type(exc).__name__}

def pipeline_status(state,output_age,max_age,exists):
    active=state.get("ActiveState","")
    result=state.get("Result","")
    main_status=str(state.get("ExecMainStatus",""))
    if active=="activating":
        return "RUNNING"
    if result not in {"","success"} or main_status not in {"","0"}:
        return "ERROR"
    if not exists:
        return "MISSING_OUTPUT"
    if output_age is None:
        return "UNKNOWN"
    if output_age<=max_age:
        return "HEALTHY"
    if output_age<=max_age*2:
        return "AGING"
    return "STALE"

def build_pipelines():
    rows=[]
    for name,unit,max_age,rel in PIPELINES:
        state=systemctl_state(unit)
        path=ROOT/rel
        age=file_age_minutes(path)
        exists=path.exists()
        rows.append({
            "pipeline":name,
            "service_unit":unit,
            "active_state":state.get("ActiveState","UNKNOWN"),
            "sub_state":state.get("SubState","UNKNOWN"),
            "service_result":state.get("Result","UNKNOWN"),
            "exec_main_status":state.get("ExecMainStatus",""),
            "last_start":state.get("ExecMainStartTimestamp",""),
            "last_exit":state.get("ExecMainExitTimestamp",""),
            "output_path":rel,
            "output_exists":exists,
            "output_age_minutes":round(age,2) if age is not None else None,
            "max_age_minutes":max_age,
            "pipeline_status":pipeline_status(
                state,age,max_age,exists
            ),
            "checked_at":NOW,
        })
    return pd.DataFrame(rows)

def sports_app_health():
    code=None
    error=""
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:8502/",timeout=2
        ) as r:
            code=int(r.status)
    except Exception as exc:
        error=type(exc).__name__
    return {
        "http_status":code,
        "status":"HEALTHY" if code==200 else "ERROR",
        "error":error,
    }

def build_gaps(datasets,pipelines,app):
    rows=[]
    for _,r in datasets.iterrows():
        bad = (
            r.freshness_status not in {"FRESH","GOVERNED_IDLE"}
            or r.row_state=="EMPTY_REVIEW"
        )
        if not bad:
            continue
        rows.append({
            "kind":"DATASET",
            "name":f"{r.sport}:{r.lane}",
            "status":r.freshness_status,
            "age_minutes":r.age_minutes,
            "detail":f"{r.path} | {r.row_state}",
        })
    for _,r in pipelines.iterrows():
        if r.pipeline_status in {"HEALTHY","RUNNING"}:
            continue
        rows.append({
            "kind":"PIPELINE",
            "name":r.pipeline,
            "status":r.pipeline_status,
            "age_minutes":r.output_age_minutes,
            "detail":r.service_unit,
        })
    if app["status"]!="HEALTHY":
        rows.append({
            "kind":"APPLICATION","name":"SPORTS_APP",
            "status":app["status"],"age_minutes":None,
            "detail":app["error"],
        })
    return pd.DataFrame(rows)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    datasets=build_datasets()
    pipelines=build_pipelines()
    app=sports_app_health()
    gaps=build_gaps(datasets,pipelines,app)

    datasets.to_csv(DATASETS,index=False)
    pipelines.to_csv(PIPELINES_OUT,index=False)
    gaps.to_csv(GAPS,index=False)

    critical_dataset=int(
        datasets.freshness_status.isin(["MISSING","STALE"]).sum()
    )
    critical_pipeline=int(
        pipelines.pipeline_status.isin(
            ["ERROR","MISSING_OUTPUT","STALE"]
        ).sum()
    )
    receipt={
        "generated_at":NOW,
        "dataset_rows":int(len(datasets)),
        "dataset_status_counts":(
            datasets.freshness_status.value_counts().astype(int).to_dict()
        ),
        "row_state_counts":(
            datasets.row_state.value_counts().astype(int).to_dict()
        ),
        "pipeline_rows":int(len(pipelines)),
        "pipeline_status_counts":(
            pipelines.pipeline_status.value_counts().astype(int).to_dict()
        ),
        "gap_rows":int(len(gaps)),
        "critical_dataset_count":critical_dataset,
        "critical_pipeline_count":critical_pipeline,
        "sports_app":app,
        "automatic_model_adjustment":False,
    }
    receipt["critical_health_pass"]=bool(
        critical_dataset==0 and critical_pipeline==0
        and app["status"]=="HEALTHY"
    )
    RECEIPT.write_text(
        json.dumps(receipt,indent=2,sort_keys=True)
    )
    print(
        "DATASETS:",len(datasets),
        receipt["dataset_status_counts"]
    )
    print(
        "PIPELINES:",len(pipelines),
        receipt["pipeline_status_counts"]
    )
    print("GAPS:",len(gaps))
    print("SPORTS APP:",app)
    print("RESULT: FRESHNESS_MANIFEST_READY")

if __name__=="__main__":
    main()
