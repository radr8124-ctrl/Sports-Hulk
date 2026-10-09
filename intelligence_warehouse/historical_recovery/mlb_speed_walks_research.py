"""MLB historical player-hits model with strictly prior completed-season speed.

Research-only extension of existing market+as-of opponent/venue hitter context.
The July comparison has been seen before and is NOT a new blind holdout.
No source, prediction, grade, model threshold or website in production changes.
"""
from __future__ import annotations

from collections import Counter,defaultdict
from copy import deepcopy
from datetime import datetime,timezone
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from intelligence_warehouse.betting_v2.hf_mlb_prop_context_model import (
    build_context_vector,FEATURE_NAMES as BASE_FEATURE_NAMES,
)
from intelligence_warehouse.betting_v2.hf_mlb_prop_asof import (
    _sigmoid,_fit_small_ridge_logistic,
)
from intelligence_warehouse.historical_recovery.mlb_asof_feature_store import (
    ROOT,OUTPUT as STORE_DIR,FEATURE_SCOPE,FEATURE_VERSION,sha_file,
)

EXTRA_FEATURE_NAMES=(
    'prior_2025_sprint_ftps_side_normalized',
    'prior_2025_sprint_measurement_present',
    'prior_2025_bat_swing_mph_side_normalized',
    'prior_2025_bat_measurement_present',
    'prior_2026_strictly_prequote_last5_walks_side_normalized',
    'prior_2026_strictly_prequote_walks_min5_present',
)
NEW_FEATURE_NAMES=EXTRA_FEATURE_NAMES
MODEL_VERSION='MLB_HF_SPORTS_ZENITH_ASOF_MARKET_CONTEXT_SPEED_WALKS_RESEARCH_V1_20261008'
RESEARCH=ROOT/'reports/mlb_feature_integration_20261008'
PREREGISTRATION=RESEARCH/'MLB_PRIOR_SPEED_WALKS_MODEL_PREREGISTRATION.md'
TRAIN=ROOT/'reports/hf_mlb_expanded_20261008/context_train_research_only.json'
JULY=ROOT/'reports/hf_mlb_expanded_20261008/context_july_research_only.json'
FEATURES=STORE_DIR/'MLB_2026_ASOF_HITTER_RESEARCH_FEATURES.parquet'
FROZEN=RESEARCH/'MLB_SPEED_WALKS_FROZEN_RESEARCH_MODEL.json'
EXPERIMENT=RESEARCH/'MLB_SPEED_WALKS_SECONDARY_JULY_EXPERIMENT.json'
RIDGE=16.0
TRAIN_END='2026-07-01T00:00:00+00:00'


def iso_utc(value:object)->pd.Timestamp:
    result=pd.to_datetime(value,errors='coerce',utc=True)
    if pd.isna(result):
        raise ValueError('Invalid source timestamp for historical games and quotes')
    return result


def normal_eligible(value,center,scale):
    if value is None or pd.isna(value):
        raise ValueError('Missing a value claimed to be source-qualified')
    return float(np.clip((float(value)-center)/scale,-2,2))


def enrich_provenance_sample(source_rows:list[dict],stored:pd.DataFrame,*,target_season:int=2026)->list[dict]:
    """Only exact gamePk + MLBAM ID; source full season BEFORE target season."""
    must={
        'game_pk','player_id','official_start',
        'source_time_class','feature_version','prior_completed_season',
        'prior_sprint_speed_ft_per_sec','prior_bat_speed_mph',
        'sprint_speed_observed','bat_speed_observed',
        'prior_last5_walks_avg','prior_pregame_sample_floor_5_games_met',
        'prior_games_count','prior_last_date',
        'source_proven_at_time_of_original_quote',
        'roster_selection_known_before_game','live_betting_approved',
    }
    if missing:=must-set(stored.columns):
        raise ValueError(f'Historical as-of feature store is missing: {sorted(missing)}')
    if stored[['game_pk','player_id']].isna().any().any() or stored.duplicated(['game_pk','player_id']).any():
        raise ValueError('Source feature store has duplicate/invalid game.player IDs')
    if set(stored.feature_version)!={FEATURE_VERSION} or set(stored.source_time_class)!={FEATURE_SCOPE}:
        raise ValueError('Unknown as-of feature-store provenance')
    if set(stored.prior_completed_season)!={target_season-1}:
        raise ValueError('Wrong immediately prior completed season for source speed')
    if any(stored.live_betting_approved.fillna(False)) or any(stored.source_proven_at_time_of_original_quote.fillna(False)):
        raise ValueError('Retrospective research store falsely claimed original frozen capture or live approval')
    if not source_rows:
        raise ValueError('No auditable historical sportsbook sample supplied')
    table=stored.set_index(['game_pk','player_id'])
    found=[]
    seen=set()
    for source in source_rows:
        row=deepcopy(source)
        if row.get('market')!='player hits' or row.get('pair_status')!='VERIFIED_SAME_BOOK_TIME_PAIR' or row.get('context_status')!='PREGAME_CONTEXT_VERIFIED':
            raise ValueError('Only existing as-of verified, exact paired-book player-hit evidence is allowed')
        gid=row.get('official_game_pk')
        player=row.get('official_player_id')
        if gid is None or player is None:
            raise ValueError('Historical game.player identity missing')
        key=(int(gid),int(player))
        if key in seen:
            raise ValueError('Duplicate game.player IDs in historical quoted selections')
        seen.add(key)
        if key not in table.index:
            raise ValueError(f'Missing official game.player exact identity in feature store: {key}')
        src=table.loc[key]
        quote=iso_utc(row.get('ts'))
        kickoff=iso_utc(row.get('official_start'))
        fixture_start=iso_utc(src['official_start'])
        if quote.year!=target_season or kickoff.year!=target_season or quote>=kickoff or abs((fixture_start-kickoff).total_seconds())>180:
            raise ValueError('Historical game timestamp and bookmaker quote do not match the source fixture')
        if bool(src['roster_selection_known_before_game']):
            raise ValueError('A postgame participant universe cannot be rewritten as true pregame roster selection')
        row['feature_store_version']=FEATURE_VERSION
        row['speed_data_completed_source_season']=target_season-1
        row['speed_source_time_status']='PRIOR_COMPLETED_SEASON_RETROSPECTIVE_REDOWNLOAD_NOT_ORIGINAL_FROZEN_AT_QUOTE'
        row['original_live_feature_capture_verified']=False
        row['roster_membership_prequote_evidenced_by_this_store']=False
        row['sprint_speed_observed']=bool(src['sprint_speed_observed'])
        row['bat_speed_observed']=bool(src['bat_speed_observed'])
        row['prior_2025_sprint_ftps']=float(src['prior_sprint_speed_ft_per_sec']) if row['sprint_speed_observed'] else None
        row['prior_2025_bat_speed_mph']=float(src['prior_bat_speed_mph']) if row['bat_speed_observed'] else None
        last=src['prior_last_date']
        prequote_last_date=last is None or pd.isna(last) or pd.Timestamp(last).date()<quote.date()
        ok=(bool(src['prior_pregame_sample_floor_5_games_met']) and
            prequote_last_date and pd.notna(src['prior_last5_walks_avg']))
        row['walks_quote_time_safe']=bool(ok)
        row['prior_prequote_last5_walks_avg']=float(src['prior_last5_walks_avg']) if ok else None
        row['prior_history_walks_status']='PRIOR_5_OFFICIAL_GAMES_BEFORE_QUOTE' if ok else 'NOT_ENOUGH_GAMES_OR_NOT_PROVEN_BEFORE_QUOTE'
        row['walks_last_prior_day']=str(last) if last is not None and pd.notna(last) else None
        row['live_plays_approved']=False
        found.append(row)
    if len(found)!=len(source_rows):
        raise RuntimeError('MLB identity join inadvertently dropped an original sportsbook source row')
    return found


def speed_walk_vector(row:dict)->list[float]:
    baseline=build_context_vector(row)
    if row.get('feature_store_version')!=FEATURE_VERSION or row.get('original_live_feature_capture_verified') is not False:
        raise ValueError('Unverified source/time context cannot be attached to the model')
    side=str(row.get('side') or '').lower()
    if side not in ('over','under'):
        raise ValueError('Betting direction requires literal over or under for signed stats')
    direction=1 if side=='over' else -1
    speed=normal_eligible(row.get('prior_2025_sprint_ftps'),27,3)*direction if row.get('sprint_speed_observed') else 0.
    bat=normal_eligible(row.get('prior_2025_bat_speed_mph'),72,7)*direction if row.get('bat_speed_observed') else 0.
    walks=normal_eligible(row.get('prior_prequote_last5_walks_avg'),.5,1.5)*direction if row.get('walks_quote_time_safe') else 0.
    out=baseline+[
        speed,1. if row.get('sprint_speed_observed') else 0.,
        bat,1. if row.get('bat_speed_observed') else 0.,
        walks,1. if row.get('walks_quote_time_safe') else 0.,
    ]
    if len(out)!=16 or not np.isfinite(out).all():
        raise ValueError('Model has invalid prior-only research feature vector')
    return out


def _sort_unique_games(rows:list[dict])->list[dict]:
    seen=set()
    output=sorted(rows,key=lambda r:(str(r.get('official_start')),int(r['official_game_pk'])))
    for row in output:
        key=int(row['official_game_pk'])
        if key in seen:
            raise ValueError('Duplicate independent MLB game in feature model')
        seen.add(key)
    return output


def freeze_speed_walks_model(rows:list[dict])->dict:
    if len(rows)<50 or any(r.get('status')!='VERIFIED_HISTORICAL' for r in rows):
        raise ValueError('Require >=50 vendor-verified pregame source grades for frozen research training')
    train=_sort_unique_games(rows)
    cutoff=iso_utc(TRAIN_END)
    if any(iso_utc(r['official_start'])>=cutoff for r in train):
        raise ValueError('July or later outcomes forbidden in pre-July training cutoff')
    if any(r.get('original_live_feature_capture_verified') is not False for r in train):
        raise ValueError('Historical source-time status misrepresented')
    X=np.asarray([speed_walk_vector(row) for row in train],dtype=float)
    y=np.asarray([float(r['verified_win']) for r in train])
    if not np.isin(y,[0,1]).all():
        raise ValueError('Missing/unclear true settled historical outcome')
    market=_fit_small_ridge_logistic(X[:,:2],y,regularization=RIDGE)
    prior=_fit_small_ridge_logistic(X[:,:10],y,regularization=RIDGE)
    expanded=_fit_small_ridge_logistic(X,y,regularization=RIDGE)
    evidence={
        'features':X.round(8).tolist(),
        'outcomes':y.astype(int).tolist(),
        'official_game_ids':[int(r['official_game_pk']) for r in train],
        'market_quote_source_ids':[r.get('quote_fingerprint') for r in train],
    }
    digest=hashlib.sha256(json.dumps(evidence,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {
        'model_version':MODEL_VERSION,
        'model_training_source':'ORIGINAL_VENDOR_GRADED_EXTERNAL_HISTORY_ONLY',
        'base_feature_names':list(BASE_FEATURE_NAMES),
        'extra_feature_names':list(EXTRA_FEATURE_NAMES),
        'feature_names':list(BASE_FEATURE_NAMES)+list(EXTRA_FEATURE_NAMES),
        'source_time_class':'COMPLETED_PRIOR_YEAR_AND_STRICTLY_PREQUOTE_PRIOR_GAMES_RECONSTRUCTED',
        'frozen_history_is_not_true_forward_prediction_proof':True,
        'training_independent_games':len(train),
        'training_first_start':train[0]['official_start'],
        'training_last_start':train[-1]['official_start'],
        'training_end_exclusive_utc':TRAIN_END,
        'training_official_game_pks':[int(r['official_game_pk']) for r in train],
        'training_matrix_and_outcomes_sha256':digest,
        'sprint_coverage':sum(bool(r.get('sprint_speed_observed')) for r in train),
        'bat_coverage':sum(bool(r.get('bat_speed_observed')) for r in train),
        'safe_prior5_walk_coverage':sum(bool(r.get('walks_quote_time_safe')) for r in train),
        'lambda':RIDGE,
        'market_calibration_beta':[round(float(v),12) for v in market],
        'prior_context_beta':[round(float(v),12) for v in prior],
        'with_speed_walks_beta':[round(float(v),12) for v in expanded],
        'train_july_outcomes_used':False,
        'july_outcomes_already_previously_examined_in_other_research':True,
        'research_only':True,
        'live_plays_approved':False,
        'payout_or_roi_proven':False,
    }


def _metrics(y:np.ndarray,p:np.ndarray)->dict:
    prob=np.clip(p,1e-6,1-1e-6)
    return {
        'brier':round(float(np.mean((prob-y)**2)),6),
        'log_loss':round(float(-np.mean(y*np.log(prob)+(1-y)*np.log(1-prob))),6),
    }


def evaluate_known_july_diagnostic(frozen:dict,rows:list[dict],*,bootstrap:int=4000,seed:int=20261008)->dict:
    result={
        'model_version':MODEL_VERSION,
        'status':'NOT_EVALUATED',
        'train_independent_games':frozen['training_independent_games'],
        'training_last_start':frozen['training_last_start'],
        'july_outcomes_previously_seen':True,
        'july_is_truly_blind_independent_evaluation':False,
        'live_plays_approved':False,
        'proven_market_edge':False,
        'calendar_day_cluster_required':True,
        'no_refit_on_july':True,
    }
    samples=_sort_unique_games(rows)
    priorids=set(frozen['training_official_game_pks'])
    if any(r.get('status') not in ('OFFICIAL_DERIVED_HISTORICAL','VERIFIED_HISTORICAL') for r in samples):
        raise ValueError('Unexpected source grading claim in July experiment')
    if priorids.intersection({int(r['official_game_pk']) for r in samples}):
        raise ValueError('Train and test official game ID overlap')
    if any(iso_utc(r['official_start'])<=iso_utc(frozen['training_last_start']) for r in samples):
        raise ValueError('July cannot be used for testing before last training game')
    result['test_independent_games']=len(samples)
    result['no_game_id_overlap']=True
    if len(samples)<25:
        result['status']='TOO_FEW_INDEPENDENT_JULY_GAMES'
        return result
    X=np.asarray([speed_walk_vector(row) for row in samples])
    y=np.asarray([float(r['verified_win']) for r in samples],dtype=float)
    if not np.isin(y,[0,1]).all():
        raise ValueError('Official July outcome missing or not binary')
    book=np.asarray([float(r['market_fair_probability']) for r in samples])
    control=_sigmoid(X[:,:2]@np.asarray(frozen['market_calibration_beta']))
    context=_sigmoid(X[:,:10]@np.asarray(frozen['prior_context_beta']))
    expanded=_sigmoid(X@np.asarray(frozen['with_speed_walks_beta']))
    delta=(context-y)**2-(expanded-y)**2  # positive = speed/walk better
    n=len(samples)
    if bootstrap<1000:
        raise ValueError('Require 1000 or more paired bootstrap replicates')
    rng=np.random.default_rng(seed)
    randoms=rng.integers(0,n,size=(bootstrap,n))
    game_delta=delta[randoms].mean(axis=1)
    ci_game=np.percentile(game_delta,[2.5,97.5])
    byday=defaultdict(list)
    for i,r in enumerate(samples):
        byday[str(r['official_start'])[:10]].append(i)
    days=sorted(byday)
    draw=rng.integers(0,len(days),size=(bootstrap,len(days)))
    grouped=[]
    for row in draw:
        indices=[i for j in row for i in byday[days[int(j)]]]
        grouped.append(float(np.mean(delta[indices])))
    day_ci=np.percentile(grouped,[2.5,97.5])
    result.update({
        'status':'SECONDARY_HISTORICAL_RECHECK_NOT_UNSEEN',
        'test_first_start':samples[0]['official_start'],
        'test_last_start':samples[-1]['official_start'],
        'test_calendar_day_blocks':len(days),
        'test_official_derived_grade_count':sum(r['status']=='OFFICIAL_DERIVED_HISTORICAL' for r in samples),
        'test_sprint_available_count':sum(bool(r.get('sprint_speed_observed')) for r in samples),
        'test_bat_available_count':sum(bool(r.get('bat_speed_observed')) for r in samples),
        'test_walks_eligible_count':sum(bool(r.get('walks_quote_time_safe')) for r in samples),
        'raw_de_vigged_book':_metrics(y,book),
        'market_calibrated_control':_metrics(y,control),
        'prior_8_context_control':_metrics(y,context),
        'new_8_context_plus_speed_walks':_metrics(y,expanded),
        'expanded_minus_prior_context_brier':round(_metrics(y,expanded)['brier']-_metrics(y,context)['brier'],6),
        'speed_walks_vs_prior_context_game_95pct_brier_gain_interval':[round(float(v),6) for v in ci_game],
        'speed_walks_vs_prior_context_clustered_95pct_brier_gain_interval':[round(float(v),6) for v in day_ci],
        'bootstrap_repetitions':bootstrap,
        'preexisting_test_outcomes_seen':True,
        'model_selected_based_on_test_result':False,
        'profitability_claim_eligible':False,
    })
    return result


def _read_context(path:Path)->list[dict]:
    if path.stat().st_size>2*1024*1024:
        raise ValueError('Research-only pilot source is unexpectedly large')
    data=json.loads(path.read_text())
    return [row for row in data if row.get('context_status')=='PREGAME_CONTEXT_VERIFIED']


def freeze_main()->dict:
    if FROZEN.exists():
        raise RuntimeError('Frozen model already exists: replay must not silently refit/overwrite its artifact')
    data=_read_context(TRAIN)
    store=pd.read_parquet(FEATURES)
    joined=enrich_provenance_sample(data,store)
    frozen=freeze_speed_walks_model(joined)
    if frozen['training_independent_games']!=90:
        raise ValueError('Expected 90 pre-July games; differing source provenance requires review')
    sources={str(p.relative_to(ROOT)):sha_file(p) for p in [PREREGISTRATION,TRAIN,FEATURES]}
    frozen['actual_source_sha256']=sources
    frozen['frozen_created_at_utc']=datetime.now(timezone.utc).isoformat()
    FROZEN.write_text(json.dumps(frozen,indent=2,sort_keys=True)+'\n')
    print('NEW_MLB_RESEARCH_MODEL_FROZEN',json.dumps({
        k:frozen[k] for k in (
        'training_independent_games','sprint_coverage','bat_coverage',
        'safe_prior5_walk_coverage','training_last_start','training_matrix_and_outcomes_sha256')
    },sort_keys=True))
    return frozen


def evaluate_main()->dict:
    if not FROZEN.is_file() or EXPERIMENT.exists():
        raise RuntimeError('Frozen model missing, or July evaluation already exists; refuse repeated model-selection process')
    source_hash=sha_file(FROZEN)
    frozen=json.loads(FROZEN.read_text())
    for path,sha in frozen['actual_source_sha256'].items():
        if sha_file(ROOT/path)!=sha:
            raise ValueError(f'Frozen training source changed before evaluation: {path}')
    juli=_read_context(JULY)
    store=pd.read_parquet(FEATURES)
    rows=enrich_provenance_sample(juli,store)
    result=evaluate_known_july_diagnostic(frozen,rows)
    if result['test_independent_games']!=46:
        raise RuntimeError('July external player hits test game coverage changed')
    result['frozen_model_sha256']=source_hash
    result['july_source_sha256']=sha_file(JULY)
    result['feature_store_source_sha256']=sha_file(FEATURES)
    result['evaluated_at_utc']=datetime.now(timezone.utc).isoformat()
    if sha_file(FROZEN)!=source_hash:
        raise RuntimeError('Frozen training model unexpectedly changed during evaluation')
    EXPERIMENT.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print('NEW_MLB_SECONDARY_RESEARCH_CHECK',json.dumps({
        k:result[k] for k in (
        'status','test_independent_games','test_calendar_day_blocks',
        'market_calibrated_control','prior_8_context_control',
        'new_8_context_plus_speed_walks','expanded_minus_prior_context_brier',
        'speed_walks_vs_prior_context_clustered_95pct_brier_gain_interval')
    },sort_keys=True))
    return result


def main():
    ap=argparse.ArgumentParser(description='Frozen, research-only MLB market+completed-year speed/walks')
    ap.add_argument('--stage',required=True,choices=['freeze_training','evaluate_known_july'])
    args=ap.parse_args()
    if args.stage=='freeze_training':freeze_main()
    else:evaluate_main()


if __name__=='__main__':
    main()
