"""Frozen bookmaker baseline and prior-fitted market calibrator shadow forecast.

One canonical paired sportsbook price per MLB game/player/market+line. This
calibration is a research-only comparison model trained on 90 previously
verified earlier games; it DOES NOT use the advanced 16-feature velocity,
weather, field or batter model because the original future source-time
inputs for all those model features remain incomplete. No live picks or
odds/settlement/ROI claims. Never refit on seen July results.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime,timezone
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from .mlb_asof_feature_store import ROOT,sha_file
from .mlb_paired_pregame_market_freeze import (
    OUTPUT as BOOK_BASELINE,
    SCHEMA as BOOK_SCHEMA,
)

MODEL_FILE=ROOT/'reports/mlb_feature_integration_20261008/MLB_SPEED_WALKS_FROZEN_RESEARCH_MODEL.json'
OUTPUT=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V2_MARKET_CALIBRATION_SHADOW_FORECASTS.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V2_MARKET_CALIBRATION_SHADOW_SUMMARY.json'
SCHEMA='MLB_V2_TRUE_FORWARD_MARKET_ONLY_CALIBRATION_SHADOW_V1'
MODEL_VERSION='MLB_HF_SPORTS_ZENITH_ASOF_MARKET_CONTEXT_SPEED_WALKS_RESEARCH_V1_20261008'
AGE_CONSTRAINT='QUOTE_FROZEN_PRE_FIRST_PITCH_AND_AFTER_ORIGINAL_OFFICIAL_LINEUP'


def _utc(v)->pd.Timestamp:
    result=pd.to_datetime(v,errors='coerce',utc=True)
    if pd.isna(result):raise ValueError('Invalid MLB quote/model source date')
    return result


def _sigmoid(x:float)->float:
    if x>=0:
        z=np.exp(-x)
        return float(1/(1+z))
    z=np.exp(x)
    return float(z/(1+z))


def _key(r:dict)->tuple[int,int,str,float]:
    return (int(r['official_game_pk']),int(r['mlbam_player_id']),
            str(r['market_metric']),float(r['line']))


def _validate_model(model:dict)->None:
    if model.get('model_version')!=MODEL_VERSION:
        raise ValueError('Unknown or unversioned 90-game pre-July calibration model')
    if model.get('training_independent_games',0)<50:
        raise ValueError('Too few earlier independent calibration training games')
    if model.get('live_plays_approved') is not False or model.get('train_july_outcomes_used') is not False:
        raise ValueError('Training used later graded games or pretends to be a live approved model')
    if len(model.get('market_calibration_beta') or [])!=2:
        raise ValueError('Missing fixed two-parameter market-only calibrator')
    if not np.isfinite(np.asarray(model['market_calibration_beta'],dtype=float)).all():
        raise ValueError('Calibration coefficients not finite')
    ids=model.get('training_official_game_pks') or []
    if len(ids)!=len(set(ids)) or len(ids)!=model['training_independent_games']:
        raise ValueError('Duplicate or fabricated independent training IDs')


def build_shadow_market_control(
    paired_baselines:list[dict],
    model:dict,
    *,now:datetime,
    original_model_sha256:str,
)->tuple[list[dict],dict]:
    if now.tzinfo is None:
        raise ValueError('Require true current timezone-aware observation clock')
    _validate_model(model)
    if len(original_model_sha256)!=64:
        raise ValueError('Frozen versioned research model file must have SHA-256')
    groups=defaultdict(list)
    for source in paired_baselines:
        if source.get('schema')!=BOOK_SCHEMA or source.get('betting_selection_approved') is not False or source.get('model_prediction_created') is not False:
            raise ValueError('Baseline inputs must be original research-only bookmaker market prices')
        gid=int(source['official_game_pk'])
        if gid in model['training_official_game_pks']:
            raise ValueError('New forward research game overlaps historical model training')
        start=_utc(source['fixture_scheduled_start_utc'])
        quote=_utc(source['source_snapshot_quote_at_utc'])
        if _utc(model['training_last_start'])>=start:
            raise ValueError('Model training data not earlier than forward research game')
        if quote>=start:
            # Individual prices captured after kickoff can NEVER be forward.
            continue
        if _utc(now)>=start or quote>_utc(now):
            continue
        if _utc(source['original_frozen_lineup_feature_at_utc'])>quote:
            raise ValueError('Captured odds predate verified original frozen lineup')
        if not source.get('original_lineup_source_line_sha256') or len(source['original_lineup_source_line_sha256'])!=64:
            raise ValueError('Missing exact original pregame lineup reference')
        metric=source.get('market_metric')
        # 90-game frozen calibration trained ONLY on MLB player hits. Walks,
        # stolen bases and total bases have separate market source baselines,
        # but NO proven fitted historical calibrator. Do not generalize.
        if metric!='hits':
            continue
        fair=source.get('market_fair_probability_over')
        if not isinstance(fair,(int,float)) or not .001<float(fair)<.999:
            raise ValueError('Missing or impossible same-book no-vig over-probability')
        if abs(float(fair)+float(source['market_fair_probability_under'])-1)>1e-5:
            raise ValueError('De-vigged over/under sides do not sum to one')
        vig=float(source.get('book_overround',0))
        if not 1<vig<=1.25:
            raise ValueError('Unexpected bookmaker overround for paired source quote')
        groups[_key(source)].append(source)
    generated=[]
    beta=np.asarray(model['market_calibration_beta'],dtype=float)
    for key,quotes in groups.items():
        game,player,metric,line=key
        # Deterministic first-observed cheapest-vig book among source quotes;
        # this is NOT choosing the side/bet with a hindsight-derived win.
        quote=min(quotes,key=lambda r:(
            float(r['book_overround']),
            str(r['source_snapshot_quote_at_utc']),
            str(r['sportsbook']),
            str(r['provider']),
        ))
        fair=float(quote['market_fair_probability_over'])
        calibrated=_sigmoid(float(beta[0]+beta[1]*np.log(fair/(1-fair))))
        row={
            'schema':SCHEMA,
            'frozen_shadow_at_utc':_utc(now).isoformat(),
            'game_pk':game,
            'mlbam_player_id':player,
            'player_name_official':quote['player_name_official'],
            'market_metric':metric,
            'market_subtype':quote['market_subtype'],
            'line':line,
            'canonical_model_side':'OVER',
            'sportsbook_selected':str(quote['sportsbook']),
            'source_provider':str(quote['provider']),
            'original_book_price_over_american':quote['price_over_american'],
            'original_book_price_under_american':quote['price_under_american'],
            'raw_no_vig_market_probability_over':fair,
            'calibrated_market_control_probability_over':round(calibrated,12),
            'baseline_model_coefficients_sha256':original_model_sha256,
            'calibrated_model_version':model['model_version'],
            'calibration_training_independent_games':model['training_independent_games'],
            'calibration_model_last_training_game_utc':model['training_last_start'],
            'source_original_market_quote_at_utc':quote['source_snapshot_quote_at_utc'],
            'source_original_mlb_lineup_at_utc':quote['original_frozen_lineup_feature_at_utc'],
            'source_original_lineup_sha256':quote['original_lineup_source_line_sha256'],
            'source_market_snapshot_sha256':quote['source_raw_market_csv_sha256'],
            'provider_book_even_within_two_sided_quote_not_independently_verified_live_on_sportsbook':True,
            'actual_game_event_start_utc':quote['fixture_scheduled_start_utc'],
            'research_only_market_calibration_control':True,
            'proprietary_speed_walks_model_evaluated':False,
            'market_edge_proven':False,
            'bookmaker_market_roi_evaluated':False,
            'betting_play_authorized':False,
            'wager_submitted':False,
            'actual_official_outcome_not_known_at_freeze':True,
            'correlated_market_quote_rows_are_not_independent_game_blocks':True,
        }
        generated.append(row)
    generated.sort(key=lambda x:(x['game_pk'],x['mlbam_player_id'],x['market_metric'],x['line']))
    return generated,{
        'schema':SCHEMA,
        'player_game_forecasts':len(generated),
        'independent_games':len({r['game_pk'] for r in generated}),
        'source_book_quotes_considered':sum(map(len,groups.values())),
        'markets_by_type':{k:sum(r['market_metric']==k for r in generated) for k in ('hits','walks','total_bases','stolen_bases')},
        'research_model':'FIXED_MARKET_ONLY_PRIOR_TRAINING_CONTROL_NOT_ADVANCED_PLAYER_MODEL',
        'advanced_feature_model_not_proven_asof':True,
        'never_retrained_on_future_or_july_results':True,
        'live_play_status':'RESEARCH_ONLY_NO_PREDICTION_MARKET_ADVANTAGE_CLAIM',
        'bets_executed':0,
    }


def append_immutable_shadow_predictions(path:Path,rows:list[dict])->int:
    if not rows:return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+'.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        prior={}
        if path.exists():
            with path.open('r',encoding='utf-8') as src:
                for line in src:
                    if not line.strip():continue
                    record=json.loads(line)
                    if record.get('schema')!=SCHEMA:
                        raise ValueError('Foreign source in frozen market calibration control')
                    key=_key({'official_game_pk':record['game_pk'],'mlbam_player_id':record['mlbam_player_id'],
                              'market_metric':record['market_metric'],'line':record['line']})
                    if key in prior:
                        raise ValueError('Duplicate immutable market-control player/game forecast')
                    prior[key]=record
        seen=set();new=[]
        for record in rows:
            if record.get('schema')!=SCHEMA or record.get('betting_play_authorized') is not False or record.get('wager_submitted') is not False:
                raise ValueError('Only zero-wager research shadow rows allowed')
            if _utc(record['frozen_shadow_at_utc'])>=_utc(record['actual_game_event_start_utc']):
                raise ValueError('A market control cannot be frozen after first pitch')
            key=_key({'official_game_pk':record['game_pk'],'mlbam_player_id':record['mlbam_player_id'],
                      'market_metric':record['market_metric'],'line':record['line']})
            if key in seen:
                raise ValueError('Duplicate source player-market within frozen shadow batch')
            seen.add(key)
            if key in prior:
                saved=prior[key]
                # Replay accepts exact same static forecast even though the
                # current clock changes, but refuses coefficient/probability
                # changes for a first accepted model prediction.
                for immutable in ('calibrated_market_control_probability_over',
                                  'baseline_model_coefficients_sha256','raw_no_vig_market_probability_over'):
                    if saved.get(immutable)!=record.get(immutable):
                        raise ValueError('Source prediction conflicts with already frozen shadow')
                continue
            new.append(record);prior[key]=record
        if new:
            with path.open('a',encoding='utf-8') as fd:
                for row in new:
                    fd.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n')
                fd.flush();os.fsync(fd.fileno())
        return len(new)


def _read_lines(path:Path)->list[dict]:
    if not path.is_file():raise ValueError('Missing genuine source market baseline ledger')
    with path.open('r',encoding='utf-8') as f:
        return [json.loads(s) for s in f if s.strip()]


def shadow_cycle(
    source:Path=BOOK_BASELINE,
    model_file:Path=MODEL_FILE,
    target:Path=OUTPUT,
    *,now:datetime|None=None,
)->dict:
    observed=now or datetime.now(timezone.utc)
    if observed.tzinfo is None:raise ValueError('Current time requires timezone')
    src=_read_lines(source)
    model=json.loads(model_file.read_text())
    model_sha=sha_file(model_file)
    _validate_model(model)
    # Original shadow coefficients and forecasts are immutable. Newly observed
    # lower-vig books are market movements, NOT a reason to overwrite
    # an earlier frozen probability. Any changed original model SHA fails.
    earlier=_read_lines(target) if target.exists() else []
    existing_keys=set()
    for record in earlier:
        if record.get('schema')!=SCHEMA:
            raise ValueError('Corrupted or foreign existing market shadow ledger')
        if record.get('baseline_model_coefficients_sha256')!=model_sha:
            raise ValueError('Previously frozen market model SHA differs from current model; manual audit required')
        key=(int(record['game_pk']),int(record['mlbam_player_id']),
             str(record['market_metric']),float(record['line']))
        if key in existing_keys:
            raise ValueError('Previously frozen shadow source contains duplicate player/market identity')
        existing_keys.add(key)
    new,details=build_shadow_market_control(
        src,model,now=observed,original_model_sha256=model_sha,
    )
    # Existing first frozen player+line forecasts must never get repriced or
    # overwritten by later market snapshots (even if overround improves).
    pending=[r for r in new if (
        int(r['game_pk']),int(r['mlbam_player_id']),str(r['market_metric']),float(r['line'])
    ) not in existing_keys]
    original=append_immutable_shadow_predictions(target,pending)
    actual=_read_lines(target) if target.exists() else []
    return {
        'schema':SCHEMA,
        'run_at_utc':_utc(observed).isoformat(),
        'source_paired_book_ledger_sha256':sha_file(source),
        'source_frozen_old_market_training_model_sha256':sha_file(model_file),
        'eligible_pregame_market_control_forecasts':details['player_game_forecasts'],
        'new_shadow_forecasts':original,
        'all_original_shadow_records':len(actual),
        'already_frozen_forecasts_preserved':len(existing_keys),
        'unique_independent_games':len({v['game_pk'] for v in actual}),
        'market_metric_shadow_counts':dict((k,sum(v['market_metric']==k for v in actual))
                                           for k in ('hits','walks','total_bases','stolen_bases')),
        'actual_model_uses_sprint_speed_or_bat_speed':False,
        'paid_play_approved':False,
        'profitability_or_betting_edge_proven':False,
        'currently_available_forecast_status':'RESEARCH_ONLY_MARKET_CALIBRATION_CONTROL_UNPROVEN',
    }


def main():
    ap=argparse.ArgumentParser(description='Source-time true forward market-only MLB calibration control')
    ap.add_argument('--source',type=Path,default=BOOK_BASELINE)
    ap.add_argument('--model',type=Path,default=MODEL_FILE)
    ap.add_argument('--output',type=Path,default=OUTPUT)
    args=ap.parse_args()
    if args.source.resolve()!=BOOK_BASELINE.resolve() or args.model.resolve()!=MODEL_FILE.resolve() or args.output.resolve()!=OUTPUT.resolve():
        raise SystemExit('Refuse unseen or mutable alternate shadow model data path')
    receipt=shadow_cycle(args.source,args.model,args.output)
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temp=SUMMARY.with_suffix('.tmp')
    temp.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    os.replace(temp,SUMMARY)
    print('MLB_SHADOW_MARKET_PROOF_CONTROL',json.dumps(receipt,sort_keys=True))


if __name__=='__main__':
    main()
