#!/usr/bin/env python3
"""Scheduled genuine NFL Final verification + scoring. Never forecasts or bets.

Verifies original frozen 13-game prediction prefix and Survivor shadow ledger,
reads member pick STATE only as a before/after checksum (without logging names),
collects ESPN Final only if NFLverse has score + original kickoff passed,
scores from independent frozen-original source, and checks validated same-game
Brier/logloss readback. Does not call the sportsbook or alter research model.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path('/home/ubuntu/sports-hulk')
VAULT=ROOT/'intelligence_warehouse/nfl_advanced_pregame'
ORIGINAL=VAULT/'NFL_FIRST_PREKICKOFF_NINE_FEATURE_SCORE_FORM_SHADOW.jsonl'
SURVIVOR_SHADOW=ROOT/'intelligence_warehouse/survivor_accountability/SURVIVOR_V2_FORWARD_LEDGER.jsonl'
MEMBERS=ROOT/'nfl_live/derived/SURVIVOR_ENTRIES.json'
RECEIPT=VAULT/'NFL_FORWARD_OFFICIAL_OBSERVER_CURRENT.json'
ORIGINAL_FIRST_13_SHA256='b74351d24c0cf591624a74c8dc2d33f84ea34f1374c65d782219bc5d95b60602'
ORIGINAL_SURVIVOR_LEDGER_FIRST_SHA256='3778bcff7ec9f87f29df739acf1f41dc75c4c7ddfc740c867b9078a51f426f55'
NODE=Path('/home/ubuntu/.nvm/versions/node/v22.23.3/bin/node')
PYTHON=ROOT/'.venv/bin/python'
FINAL_MODULE='intelligence_warehouse.historical_recovery.nfl_forward_individual_final_source'
SCORER_MODULE='intelligence_warehouse.historical_recovery.nfl_nine_col_official_scoring'


def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def first_n_lines_hash(data:bytes,count:int)->str:
    lines=data.splitlines(keepends=True)
    if len(lines)<count or count<1:
        raise ValueError('Original immutable source missing its required rows')
    return sha(b''.join(lines[:count]))


def private_pick_fingerprint(state:dict)->str:
    """Keeps names out of receipts; catches any private pick or status mutation."""
    if not isinstance(state,dict) or not isinstance(state.get('entries'),dict):
        raise ValueError('Private pool source schema not verified')
    pool_week=state.get('pool_current_week')
    if not isinstance(pool_week,int) or pool_week<1 or pool_week>18:
        raise ValueError('Missing live original season week')
    members=[]
    for name,item in sorted(state['entries'].items()):
        if not isinstance(item,dict):raise ValueError('Invalid member entry')
        memberships={k:({'picks':v.get('picks'),'submitted':v.get('submitted')})
            for k,v in item.items() if k.startswith('week_') and isinstance(v,dict)}
        members.append({'name':name,'status':item.get('status'),
            'used':item.get('used_teams'),'current':item.get('current_picks'),
            'past_submissions':memberships})
    return sha(json.dumps({'week':pool_week,'members':members},sort_keys=True,separators=(',',':'),
                         ensure_ascii=True).encode())


def snapshot_immutable_state()->dict:
    return {
      'original_13_sha256':first_n_lines_hash(ORIGINAL.read_bytes(),13),
      'survivor_original_1_sha256':first_n_lines_hash(SURVIVOR_SHADOW.read_bytes(),1),
      'private_pick_state_sha256':private_pick_fingerprint(json.loads(MEMBERS.read_text())),
    }


def require_original_intact(snapshot:dict)->None:
    if snapshot['original_13_sha256']!=ORIGINAL_FIRST_13_SHA256:
        raise ValueError('ORIGINAL_13_FORECAST_SHA_CHANGED')
    if snapshot['survivor_original_1_sha256']!=ORIGINAL_SURVIVOR_LEDGER_FIRST_SHA256:
        raise ValueError('ORIGINAL_SURVIVOR_MODEL_LEDGER_SHA_CHANGED')


def invoke(cmd:list[str],seconds:int)->str:
    work=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                        text=True,timeout=seconds,check=False)
    if work.returncode:
        # Never print raw stderr contents that may include source/private records.
        raise RuntimeError(f'PROTECTED_SCRIPT_FAILED_RC_{work.returncode}_COMMAND_{Path(cmd[0]).name}')
    return work.stdout


def readback()->dict:
    output=invoke([str(NODE),str(ROOT/'scripts/zenith_nfl_final_proof_readback.mjs')],15)
    rows=[line.strip() for line in output.splitlines() if line.strip()]
    if len(rows)!=1:raise ValueError('NFL model proof readback must be exactly one aggregate row')
    value=json.loads(rows[0])
    if value.get('research_only') is not True or value.get('frozen_games',0)<13:
        raise ValueError('NFL model proof returned unapproved public status')
    if value.get('forecast_source_sha256')!=sha(ORIGINAL.read_bytes()):
        raise ValueError('NFL original full forecast SHA readback mismatch')
    return value


def source_summary(prefix:str,stdout:str)->dict:
    for line in reversed(stdout.splitlines()):
        if line.startswith(prefix+' '):
            payload=json.loads(line[len(prefix)+1:])
            if not isinstance(payload,dict):raise ValueError('Non-dict protected source receipt')
            return payload
    raise ValueError('Official Final script did not return its original source receipt')


def atomic_receipt(value:dict)->None:
    RECEIPT.parent.mkdir(parents=True,exist_ok=True)
    data=json.dumps(value,sort_keys=True,indent=2)+'\n'
    fd,name=tempfile.mkstemp(prefix='.nfl-forward-observer-',suffix='.tmp',dir=RECEIPT.parent)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'w',encoding='utf8') as writer:
            writer.write(data)
            writer.flush();os.fsync(writer.fileno())
        if sha(Path(name).read_bytes())!=sha(data.encode()):raise ValueError('Receipt temporary SHA mismatch')
        os.replace(name,RECEIPT)
        if sha(RECEIPT.read_bytes())!=sha(data.encode()):raise ValueError('Receipt readback SHA mismatch')
    finally:
        if Path(name).exists():Path(name).unlink()


def main()->int:
    parser=argparse.ArgumentParser(description='Verified NFL forward official Final research observer; no bets or picks')
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--verify-only',action='store_true',help='No network calls, ledgers or receipt updates')
    modes.add_argument('--run',action='store_true',help='Collect independent Final after score available, then grade')
    args=parser.parse_args()
    started=time.monotonic()
    before=snapshot_immutable_state()
    require_original_intact(before)
    proof=readback()
    if args.verify_only:
        print(json.dumps({'status':proof['status'],'frozen_games':proof['frozen_games'],
             'compared_games':proof['compared_games'],'research_only':True,
             'automatic_betting':False,'network_requests':0},sort_keys=True))
        return 0
    try:
        collected=source_summary('NFL_TRUE_PREKICKOFF_MODEL_INDIVIDUAL_OFFICIAL_FINAL_RESEARCH',invoke([
          str(PYTHON),'-m',FINAL_MODULE,'--stage','collect_original_game_finals'],25),)
        graded=source_summary('NFL_FIRST_SCORE_FORM_VS_MARKET_OFFICIAL_FINAL_RESEARCH',invoke([
          str(PYTHON),'-m',SCORER_MODULE],20))
        after=snapshot_immutable_state()
        require_original_intact(after)
        if before!=after:raise ValueError('Original frozen model or private Survivor pick history changed during protected cycle')
        follow=readback()
        if follow.get('official_final_games')!=collected.get('total_saved_verified_final_games') or (
            follow.get('compared_games')!=graded.get('independent_final_game_blocks') or
            follow.get('compared_games')!=graded.get('source_pairs_scored')):
            raise ValueError('Cross-source final scoring readback mismatch')
        receipt={
          'schema':'SPORTS_ZENITH_NFL_AUTOMATIC_OFFICIAL_FINAL_PROOF_OBSERVER_V1',
          'generated_at_utc':datetime.now(timezone.utc).isoformat(),
          'status':'VERIFIED_PROTECTED_NO_CHANGE' if not collected.get('verified_new_independent_final_games') and not graded.get('newly_scored_final_games') else 'VERIFIED_NEW_NFL_FINAL_RESEARCH_SCORES',
          'original_13_forecasts_preserved_sha256':before['original_13_sha256'],
          'original_survivor_model_ledger_preserved_sha256':before['survivor_original_1_sha256'],
          'private_entry_picks_status_readback_verified_unchanged':True,
          'forecast_count':follow['frozen_games'],
          'official_final_count':follow['official_final_games'],
          'paired_final_score_count':follow['compared_games'],
          'research_source_http_calls':int(collected.get('source_HTTP_calls',0)),
          'new_official_finals':int(collected.get('verified_new_independent_final_games',0)),
          'newly_graded_research_games':int(graded.get('newly_scored_final_games',0)),
          'scorer_status':follow['status'],
          'independent_edge_proven':False,
          'sportsbook_executable_price_verified':False,
          'official_betting_allowed':False,
          'survivor_pick_or_external_pool_submission_changed':False,
          'duration_seconds':round(time.monotonic()-started,2),
        }
        atomic_receipt(receipt)
        # No participant names, lineups, account data or fabricated wins in logs.
        print(json.dumps(receipt,sort_keys=True))
        return 0
    except Exception:
        # Let the service fail loudly; never rewrite an original source to fix a conflict.
        print('PROTECTED_NFL_FINAL_SCORING_FAILED_NO_AUTOMATIC_RECOVERY',file=sys.stderr)
        raise


if __name__=='__main__':
    sys.exit(main())
