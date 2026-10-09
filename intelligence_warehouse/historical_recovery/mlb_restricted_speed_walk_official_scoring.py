"""Prospective three-way MLB hits Brier/logloss after original official Final.

Source 1: first frozen no-vig book + fitted market calibration BEFORE kickoff.
Source 2: first frozen newly trained restricted speed/bat/walks forecast BEFORE
kickoff, using only completed 2025 and prior actual games.
Source 3: independently graded MLB StatsAPI official game Final hitter hits,
tied cryptographically to the ORIGINAL published pregame lineup player ID.
This is research-only descriptive probability evaluation; not a wager result,
not a demonstrated proprietary market edge, and not independent per-player
game sample inflation.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime,timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

from .mlb_asof_feature_store import ROOT,sha_file
from .mlb_restricted_speed_walk_shadow import (
    OUTPUT as RESTRICTED,SCHEMA as RESTRICTED_SCHEMA
)
from .mlb_shadow_market_control import (
    OUTPUT as MARKET,SCHEMA as MARKET_SCHEMA
)
from .mlb_research_forward_labels import (
    OUTPUT as OFFICIAL,SCHEMA as OFFICIAL_SCHEMA
)

OUTPUT=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V2_RESTRICTED_SPEED_WALKS_OFFICIAL_THREEWAY_SCORES.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V2_RESTRICTED_SPEED_WALKS_OFFICIAL_THREEWAY_SUMMARY.json'
SCHEMA='MLB_V2_RESTRICTED_SPEED_WALKS_OFFICIAL_HITS_THREEWAY_SHADOW_SCORE_V1'
SAMPLE_FLOOR=30
MODEL_SCOPE='LIMITED_PRIOR_2025_SPEED_BAT_WALKS_NOT_FULL_PITCHER_PARK_16'


def _utc(raw)->pd.Timestamp:
    value=pd.to_datetime(raw,utc=True,errors='coerce')
    if pd.isna(value):raise ValueError('Missing original pregame or official result timestamp')
    return value


def _read_jsonl(file:Path)->list[dict]:
    if not file.is_file():return []
    with file.open('r',encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def _market_key(r:dict)->tuple[int,int]:
    return (int(r['game_pk']),int(r['mlbam_player_id']))


def _graded_key(r:dict)->tuple[int,int]:
    return (int(r['official_game_pk']),int(r['player_id']))


def _metrics(rows:list[dict])->dict:
    out={}
    for name in ('raw_no_vig_market','market_only_control','restricted_speed_walk'):
        if not rows:
            out[f'{name}_brier']=None
            out[f'{name}_logloss']=None
        else:
            out[f'{name}_brier']=round(float(np.mean([x[f'{name}_squared_error'] for x in rows])),9)
            out[f'{name}_logloss']=round(float(np.mean([x[f'{name}_logloss'] for x in rows])),9)
    return out


def compare_restricted_vs_market_after_final(
    restricted:list[dict],
    market:list[dict],
    final_labels:list[dict],
    *,now:datetime,
)->tuple[list[dict],dict]:
    if now.tzinfo is None:
        raise ValueError('Official research score requires timezone-aware observation time')
    observed=_utc(now)
    rindex={};mindex={};gindex={}
    for x in restricted:
        key=_market_key(x)
        if key in rindex:raise ValueError('Restricted prospective model contains duplicate player/game')
        rindex[key]=x
        if x.get('schema')!=RESTRICTED_SCHEMA:
            raise ValueError('Unknown original restricted-speed source schema')
        if x.get('live_play_approved') is not False or x.get('wager_executed') is not False:
            raise ValueError('Source must be research-only, never an approved wager')
        if x.get('market_metric')!='hits' or float(x.get('line',-1))!=.5:
            raise ValueError('Model was trained only on the hits over 0.5 market')
        start=_utc(x['original_game_start_at_utc'])
        modeltime=_utc(x['first_prospective_prediction_frozen_at_utc'])
        if modeltime>=start:
            raise ValueError('Restricted speed/bat/walks model is not a pregame frozen prediction')
        if not x.get('original_source_lineup_sha256') or len(x['original_source_lineup_sha256'])!=64:
            raise ValueError('Missing original official pregame lineup proof')
        if len(str(x.get('model_coefficients_frozen_sha256') or ''))!=64:
            raise ValueError('Frozen prior-trained restricted model checksum missing')
    for x in market:
        key=_market_key(x)
        if key in mindex:raise ValueError('Original market-only control has duplicate player/game')
        mindex[key]=x
        if x.get('schema')!=MARKET_SCHEMA:
            raise ValueError('Unknown original pregame market calibration model')
    for x in final_labels:
        key=_graded_key(x)
        if key in gindex:raise ValueError('Independent official hitter grades duplicate player/game')
        gindex[key]=x
        if x.get('schema')!=OFFICIAL_SCHEMA:
            raise ValueError('Official source grade schema is not the authenticated source')
    out=[]
    for key,r in rindex.items():
        if key not in mindex:
            raise ValueError('Missing original market-only source for a prospective restricted model')
        m=mindex[key]
        if (
            m.get('betting_play_authorized') is not False or m.get('wager_submitted') is not False
            or m.get('market_metric')!='hits' or float(m.get('line',-1))!=.5
            or r.get('original_source_lineup_sha256')!=m.get('source_original_lineup_sha256')
            or r.get('original_market_control_sha256')!=m.get('baseline_model_coefficients_sha256')
        ):
            raise ValueError('Original market-only source and restricted model are not the same pregame player/lineup')
        start=_utc(r['original_game_start_at_utc'])
        if start!=_utc(m['actual_game_event_start_utc']):
            raise ValueError('Current official scheduled start differs from original book/model source')
        if _utc(m['frozen_shadow_at_utc'])>=start:
            raise ValueError('Original bookmaker market model was not frozen before first pitch')
        expected_market=float(r['market_fair_over_at_original_quote'])
        expected_control=float(r['market_only_calibrated_over_at_original_quote'])
        market_p=float(m['raw_no_vig_market_probability_over'])
        control_p=float(m['calibrated_market_control_probability_over'])
        adv_p=float(r['calibrated_restricted_speed_walk_probability_over'])
        if abs(expected_market-market_p)>1e-8 or abs(expected_control-control_p)>1e-8:
            raise ValueError('Prospective restricted model was tied to different original price/control values')
        if not all(.001<p<.999 and np.isfinite(p) for p in (market_p,control_p,adv_p)):
            raise ValueError('One of the three original pregame probabilities was invalid')
        grade=gindex.get(key)
        if grade is None:
            continue
        if (
            grade.get('official_final_status_from_mlb_master')!='Final'
            or grade.get('live_play_approved') is not False
            or grade.get('sportsbook_bet_settled') is not False
            or grade.get('model_win_or_probability_qualified') is not False
        ):
            raise ValueError('Official result is not the final independent research-only player grade')
        if grade.get('original_source_line_sha256')!=r['original_source_lineup_sha256']:
            raise ValueError('Research forecast and true Final grade have different original source lineup SHA')
        grade_time=_utc(grade['official_outcome_checked_at_utc'])
        if not start<grade_time<=observed:
            raise ValueError('Official Final outcome was not observed strictly after first pitch')
        hits=pd.to_numeric(grade.get('official_hits'),errors='coerce')
        if pd.isna(hits) or not np.isfinite(hits) or hits<0:
            raise ValueError('Official player had no valid hits record: never fabricate zero/loss')
        observed_hits=int(hits)
        binary=int(hits>.5)
        loss_data={}
        for name,p in [('raw_no_vig_market',market_p),
                       ('market_only_control',control_p),
                       ('restricted_speed_walk',adv_p)]:
            loss_data[f'{name}_over_probability']=p
            loss_data[f'{name}_squared_error']=round((p-binary)**2,12)
            loss_data[f'{name}_logloss']=round(-math.log(p if binary else 1-p),12)
        out.append({
            'schema':SCHEMA,
            'official_game_pk':key[0],
            'mlbam_player_id':key[1],
            'market_metric':'hits',
            'line':.5,
            'original_market_no_vig_price_time_utc':r['source_original_market_quote_at_utc'],
            'original_frozen_market_model_at_utc':m['frozen_shadow_at_utc'],
            'original_restricted_8_feature_model_at_utc':r['first_prospective_prediction_frozen_at_utc'],
            'scheduled_game_start_utc':r['original_game_start_at_utc'],
            'original_pregame_lineup_sha256':r['original_source_lineup_sha256'],
            'frozen_restricted_model_sha256':r['model_coefficients_frozen_sha256'],
            'source_official_grade_at_utc':grade['official_outcome_checked_at_utc'],
            'official_source_game_status':'Final',
            'official_hits':observed_hits,
            'actual_hits_over_0_5':binary,
            'unique_game_block_id':str(key[0]),
            'research_only':True,
            'compares_three_frozen_probabilities':True,
            'full_sixteen_feature_model_used':False,
            'sportsbook_wager_executed':False,
            'commercial_profitability_demonstrated':False,
            'model_promoted_to_live_play':False,
            **loss_data,
        })
    out.sort(key=lambda x:(x['official_game_pk'],x['mlbam_player_id']))
    independent=len({x['official_game_pk'] for x in out})
    summary={
        'schema':SCHEMA,
        'status':('AWAITING_VERIFIED_FINAL_OFFICIAL_MLB_HITS' if not out
                  else 'BUILDING_INDEPENDENT_GAME_BLOCKS_NO_MARKET_EDGE_ESTABLISHED' if independent<SAMPLE_FLOOR
                  else 'SAMPLE_FLOOR_ONLY_NOT_AN_ACCEPTANCE_OF_BETTING_MARKET_EDGE'),
        'model_scope':MODEL_SCOPE,
        'official_player_hit_events_scored':len(out),
        'original_restricted_forecasts':len(restricted),
        'ungraded_restricted_player_forecasts':len(restricted)-len(out),
        'source_true_independent_game_blocks':independent,
        'minimum_independent_game_blocks_for_first_evidence_floor':SAMPLE_FLOOR,
        'remaining_game_blocks_to_first_evidence_floor':max(0,SAMPLE_FLOOR-independent),
        'statistically_proven_enhanced_market_edge':False,
        'live_play_approvals':0,
        'source_grades_not_sportsbook_settlements':True,
        'source_provider_model_future_leakage_excluded':True,
        'thirty_games_only_sample_size_floor_not_proof':True,
        **_metrics(out)
    }
    return out,summary


def append_first_restricted_model_scores(path:Path,records:list[dict])->int:
    if not records:return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+'.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        old={}
        for row in _read_jsonl(path):
            if row.get('schema')!=SCHEMA:raise ValueError('Invalid persisted three-way model source grade')
            key=(int(row['official_game_pk']),int(row['mlbam_player_id']))
            if key in old:raise ValueError('Duplicated prior settled research result')
            old[key]=row
        seen=set();pending=[]
        for item in records:
            if item.get('schema')!=SCHEMA or item.get('sportsbook_wager_executed') is not False:
                raise ValueError('Only source-authenticated three-way no-wager research scores allowed')
            key=(int(item['official_game_pk']),int(item['mlbam_player_id']))
            if key in seen:raise ValueError('Duplicate new source grade batch')
            seen.add(key)
            if key in old:
                if old[key]!=item:
                    raise ValueError('Immutable original grade conflicts with a later provider correction')
                continue
            pending.append(item);old[key]=item
        if pending:
            with path.open('a',encoding='utf-8') as fd:
                for row in pending:
                    fd.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n')
                fd.flush();os.fsync(fd.fileno())
        return len(pending)


def score_cycle(
    restricted:Path=RESTRICTED,
    market:Path=MARKET,
    official:Path=OFFICIAL,
    output:Path=OUTPUT,*,now:datetime|None=None,
)->dict:
    clock=now or datetime.now(timezone.utc)
    if clock.tzinfo is None:raise ValueError('Official scorer cannot use naive clock')
    sources=_read_jsonl(restricted)
    controls=_read_jsonl(market)
    grades=_read_jsonl(official)
    proposed,summary=compare_restricted_vs_market_after_final(sources,controls,grades,now=clock)
    written=append_first_restricted_model_scores(output,proposed)
    stored=_read_jsonl(output)
    if len(stored)!=len(proposed):
        raise ValueError('Previous source-frozen official score disappeared from independent result ledger')
    summary.update({
        'observed_at_utc':_utc(clock).isoformat(),
        'newly_scored_restricted_research_rows':written,
        'source_restricted_frozen_sha256':sha_file(restricted) if restricted.exists() else None,
        'source_original_market_only_frozen_sha256':sha_file(market) if market.exists() else None,
        'source_true_official_final_player_labels_sha256':sha_file(official) if official.exists() else None,
        'full_model_or_profitability_proven':False,
        'paid_picks_approved':False,
        'betting_thresholds_or_wager_changes':0,
    })
    return summary


def main():
    ap=argparse.ArgumentParser(description='Source-only 3-way restricted MLB prospective market model grader')
    ap.add_argument('--restricted',type=Path,default=RESTRICTED)
    ap.add_argument('--market',type=Path,default=MARKET)
    ap.add_argument('--official',type=Path,default=OFFICIAL)
    ap.add_argument('--output',type=Path,default=OUTPUT)
    args=ap.parse_args()
    if any([
        args.restricted.resolve()!=RESTRICTED.resolve(),
        args.market.resolve()!=MARKET.resolve(),
        args.official.resolve()!=OFFICIAL.resolve(),
        args.output.resolve()!=OUTPUT.resolve()
    ]):
        raise SystemExit('Refusing unknown result/odds/model ledgers')
    r=score_cycle()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    tmp=SUMMARY.with_suffix('.tmp')
    tmp.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    os.replace(tmp,SUMMARY)
    print('MLB_SPEED_WALKS_VS_PAIRED_MARKET_TRUE_FORWARD_SCORE',json.dumps(r,sort_keys=True))


if __name__=='__main__':
    main()
