"""One-at-a-time, original-source-attested FUTURE NL bracket fixture repair.

No bulk MLB master rebuild, no odds or outcome edits, no model/pick promotion.
The original LIVE MLB schedule is refetched independently of two timestamped
previous public MLB source observations. Only seven future fixture cells may
change; every other historical game cell must remain identical.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from datetime import datetime,timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
import pandas as pd
import requests

from baseball_vault.refresh_mlb_master_status import parse_schedule
from baseball_vault.mlb_future_bracket_attestation import (
    load_archived_original_responses,verified_nl_placeholder_overrides,
)

ROOT=Path(__file__).resolve().parents[1]
MASTER_REL="baseball_vault/derived/MLB_GAME_MASTER.csv"
PARQUET_REL="baseball_vault/derived/MLB_GAME_MASTER.parquet"
EVIDENCE_REL="intelligence_warehouse/mlb_pregame_capture/MLB_PREGAME_SOURCE_EVIDENCE.jsonl"
FROZEN_REL="intelligence_warehouse/mlb_pregame_capture/MLB_V4_SIXTEEN_FEATURE_ACTUAL_FORWARD_SHADOW.jsonl"
RAW_ODDS_REL="intelligence_warehouse/mlb_pregame_capture/MLB_V4_FULL16_SAME_NEW_QUOTE_OFFICIAL_THREEWAY_SCORES.jsonl"
RECEIPT_REL="reports/MLB_NL_BRACKET_849809_SINGLE_CELL_RECONCILIATION_2026-10-09.json"
WHITELIST={"gameDate","home_team","home_team_id","away_team","away_team_id","venue","venue_id"}
FIRST_FULL16_SHA="0cea5e38c94451cacbc1ff552276c5df7aa1e341296b127fd0cfa6a2d19c66a8"
TARGET="849809"


def sha(raw):return hashlib.sha256(raw).hexdigest()


def live_schedule(session,now):
    params={"sportId":1,"startDate":"2026-10-10","endDate":"2026-10-13",
            "hydrate":"team,venue"}
    response=session.get("https://statsapi.mlb.com/api/v1/schedule",
                         params=params,timeout=(3,15))
    response.raise_for_status()
    if len(response.content)>180000:
        raise ValueError("CURRENT_MLB_SOURCE_RESPONSE_OVERSIZED")
    official,duplicated=parse_schedule(response.json())
    if duplicated:raise ValueError("CURRENT_MLB_SOURCE_DUPLICATE_GAME_IDENTITIES")
    if TARGET not in official or official[TARGET]["status"]!="Scheduled":
        raise ValueError("TARGET_OFFICIAL_MLB_GAME_NOT_CURRENTLY_SCHEDULED")
    return official,sha(response.content)


def one_cellset(master,proof,target=TARGET):
    if set(proof)!={target}:
        raise ValueError("ZERO_OR_MULTIPLE_NEW_MLB_FUTURE_BRACKET_CANDIDATES")
    m=master.copy(deep=True)
    selected=m[m.gamePk.astype(str).eq(target)]
    if len(selected)!=1:raise ValueError("ORIGINAL_PLACEHOLDER_GAME_MISSING_OR_DUPLICATED")
    i=selected.index[0]
    original=m.loc[i]
    p=proof[target]
    if (p["original_old_start"]!=original["gameDate"]
        or p["original_placeholder_home"]!=original["home_team"]
        or p["original_placeholder_away"]!=original["away_team"]
        or p["original_placeholder_game_type"]!=original["gameType"]
        or p["official_date"]!=original["officialDate"]
        or p["proof_type"]!="NL_FUTURE_PLACEHOLDER_REPLACEMENT_FROM_TWO_ORIGINAL_OFFICIAL_SOURCE_CAPTURES"
        or p["independent_original_captures"]!=2
        or p["original_batting_orders_or_starters_verified"] is not False):
        raise ValueError("HISTORICAL_OR_SOURCE_PROVENANCE_DID_NOT_MATCH_MASTER")
    mapping={
        "gameDate":p["verified_real_start"],
        "home_team":p["resolved_home_team_name"],
        "home_team_id":p["resolved_home_team_id"],
        "away_team":p["resolved_away_team_name"],
        "away_team_id":p["resolved_away_team_id"],
        "venue":p["resolved_venue_name"],
        "venue_id":p["resolved_venue_id"],
    }
    for col,value in mapping.items():m.at[i,col]=value
    before=master.fillna("").astype(str)
    after=m.fillna("").astype(str)
    modifications=[]
    for col in master.columns:
        for idx in before.index[before[col].ne(after[col])]:
            modifications.append({
                "gamePk":str(master.loc[idx,"gamePk"]),
                "field":col,"old":before.at[idx,col],"new":after.at[idx,col],
            })
    if (len(modifications)!=7 or
        {x["field"] for x in modifications}!=WHITELIST or
        any(x["gamePk"]!=target for x in modifications) or
        len(m)!=len(master) or not (m.gamePk.astype(str)==master.gamePk.astype(str)).all()):
        raise ValueError("SCHEDULE_PLACEHOLDER_REPAIR_WOULD_TOUCH_OTHER_MASTER_FACTS")
    return m,modifications


def run(*,root=ROOT,session=None,now=None,game_pk=TARGET,dry_run=True):
    root=Path(root)
    now=now or datetime.now(timezone.utc)
    if not now.tzinfo or game_pk!=TARGET:
        raise ValueError("TARGETED_ONE_FIXTURE_SOURCE_RECONCILIATION_ONLY")
    src=root/EVIDENCE_REL
    source_bytes=src.read_bytes()
    observations=[]
    for line in source_bytes.splitlines(keepends=True):
        if not line.strip():continue
        x=json.loads(line)
        x["_raw_source_line_sha256"]=sha(line)
        observations.append(x)
    raw_files=load_archived_original_responses(root)
    master_file=root/MASTER_REL
    parquet_file=root/PARQUET_REL
    original_bytes=master_file.read_bytes()
    master=pd.read_csv(master_file,dtype=str,low_memory=False)
    if not parquet_file.exists():raise ValueError("MLB_DERIVED_PARQUET_NOT_PRESENT")
    pq_original=sha(parquet_file.read_bytes())
    frozen_file=root/FROZEN_REL
    freeze_sha=sha(frozen_file.read_bytes())
    if freeze_sha!=FIRST_FULL16_SHA:raise ValueError("ORIGINAL_18_FULL16_MODEL_SOURCE_CHANGED")
    if any(str(json.loads(row).get("official_game_pk"))==TARGET
           for row in frozen_file.read_text().splitlines() if row.strip()):
        raise ValueError("MODEL_ALREADY_FROZEN_FOR_FUTURE_PLACEHOLDER")
    grade_sha=sha((root/RAW_ODDS_REL).read_bytes())
    official,official_hash=live_schedule(session or requests.Session(),now)
    proof=verified_nl_placeholder_overrides(master,official,observations,raw_files,clock=now)
    new,changes=one_cellset(master,proof,game_pk)
    result={
        "source_attestation":"VERIFIED_TWO_DISTINCT_EARLIER_ORIGINAL_OFFICIAL_MLB_CAPTURES_AND_FRESH_THIRD_PUBLIC_MLB_SCHEDULE",
        "state":"DRY_RUN_ONLY" if dry_run else "VERIFIED_FUTURE_FIXTURE_MASTER_CORRECTED",
        "gamePk":int(game_pk),"checked_at_utc":now.isoformat(),
        "source_game_first_pitch_utc":proof[game_pk]["verified_real_start"],
        "original_gamepk_rows_count":len(master),"new_gamepk_rows_count":len(new),
        "changes":changes,"proof":proof[game_pk],
        "original_source_evidence_sha256":sha(source_bytes),
        "source_archived_second_raw_sha256":proof[game_pk]["second_original_schedule_response_sha256"],
        "fresh_third_schedule_sha256":official_hash,
        "original_master_sha256":sha(original_bytes),
        "original_parquet_sha256":pq_original,
        "original_18_full16_frozen_forecast_sha256":freeze_sha,
        "original_18_completed_game_official_scores_sha256":grade_sha,
        "real_batting_orders_verified":False,
        "future_play_or_proven_edge_claim":False,
        "retroactive_prediction_modified":False,
        "off_vps_source_restore_verified":False,
    }
    if dry_run:return result
    tmpcsv=master_file.parent/(".nl849809-source-reconcile."+str(os.getpid())+".csv")
    tmppq=parquet_file.parent/(".nl849809-source-reconcile."+str(os.getpid())+".parquet")
    if tmpcsv.exists() or tmppq.exists():raise ValueError("SOURCE_TEMPS_ALREADY_EXIST")
    try:
        new.to_csv(tmpcsv,index=False)
        new.to_parquet(tmppq,index=False)
        check=pd.read_csv(tmpcsv,dtype=str,low_memory=False)
        _,verified_changes=one_cellset(master,proof,game_pk)
        if len(check)!=len(master) or verified_changes!=changes:
            raise ValueError("TARGETED_MASTER_REPAIR_CSV_REPLAY_FAILED")
        if len(pd.read_parquet(tmppq))!=len(master):
            raise ValueError("TARGETED_MASTER_REPAIR_PARQUET_REPLAY_FAILED")
        if (sha(master_file.read_bytes())!=sha(original_bytes)
            or sha(src.read_bytes())!=sha(source_bytes)
            or sha(frozen_file.read_bytes())!=freeze_sha
            or sha((root/RAW_ODDS_REL).read_bytes())!=grade_sha):
            raise ValueError("MLB_SOURCE_CHANGED_WHILE_REPAIR_PREPARING")
        os.replace(tmppq,parquet_file)
        os.replace(tmpcsv,master_file)
        result["corrected_master_sha256"]=sha(master_file.read_bytes())
        result["corrected_parquet_sha256"]=sha(parquet_file.read_bytes())
    finally:
        tmpcsv.unlink(missing_ok=True)
        tmppq.unlink(missing_ok=True)
    receipt=root/RECEIPT_REL
    receipt.parent.mkdir(parents=True,exist_ok=True)
    with receipt.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write("\n");f.flush();os.fsync(f.fileno())
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--game-pk",default=TARGET)
    p.add_argument("--apply",action="store_true")
    args=p.parse_args()
    result=run(game_pk=args.game_pk,dry_run=not args.apply)
    print("MLB_ATTESTED_FUTURE_BRACKET_MASTER",json.dumps(result,sort_keys=True))


if __name__=="__main__":main()
