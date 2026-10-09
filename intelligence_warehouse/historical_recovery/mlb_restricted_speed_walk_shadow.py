"""Pre-registered 8-col prospective MLB hits-only speed/bat/walk research model.

Model fits ONCE to original 90 pre-July vendor-graded hits selections; these
selections can be OVER or UNDER. Candidate uses prior completed season measured
sprint/bat swing speed and strictly earlier-date walks + same-book no-vig odds.
No July model fitting. Today only official lineup + first pregame V2 source +
the exactly same paired-book market selected by the frozen market-only control.

This is NOT the unavailable full 16-feature context model; no enhanced edge or
paid sportsbook recommendation can be claimed from one future game.
"""
from __future__ import annotations

from datetime import datetime,timezone
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import math

import numpy as np
import pandas as pd

from intelligence_warehouse.betting_v2.hf_mlb_prop_asof import _fit_small_ridge_logistic
from .mlb_asof_feature_store import ROOT,sha_file,FEATURE_VERSION
from .mlb_speed_walks_research import (
    enrich_provenance_sample,speed_walk_vector,
    TRAIN,FEATURES,MODEL_VERSION as SIXTEEN_FEATURES_MODEL_VERSION
)
from .mlb_shadow_market_control import (
    OUTPUT as CONTROL_LEDGER,MODEL_FILE as CONTROL_MODEL,
    SCHEMA as MARKET_CONTROL_SCHEMA,
)
from .mlb_live_research_feature_freeze_v2 import (
    OUTPUT as LIVE_ADVANCED,SCHEMA as LIVE_SCHEMA,
    REVISION as LIVE_REVISION,
)
from .mlb_research_forward_labels import (
    ORIGINAL_PREGAME_LINEUPS,verify_original_pregame_source,
)

MODEL_VERSION='MLB_RESTRICTED_PREQUOTE_SPEED_WALKS_HITS_SHADOW_20261008_V1'
PREREGISTRATION=ROOT/'reports/mlb_feature_integration_20261008/MLB_RESTRICTED_SPEED_WALKS_FORWARD_SHADOW_PREREGISTRATION_2026-10-08.md'
FROZEN_MODEL=ROOT/'reports/mlb_feature_integration_20261008/MLB_RESTRICTED_SPEED_WALKS_FROZEN_TRAINING_V1.json'
OUTPUT=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V2_RESTRICTED_SPEED_WALKS_SHADOW_FORECASTS.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V2_RESTRICTED_SPEED_WALKS_SHADOW_SUMMARY.json'
SCHEMA='MLB_V2_RESTRICTED_2025_SPEED_BAT_WALKS_TRUE_FORWARD_SHADOW_V1'
RESTRICTED_NAMES=(
 'intercept',
 'paired_book_selected_side_fair_market_logit',
 'signed_prior_2025_sprint_ftps',
 'qualified_sprint_present',
 'signed_prior_2025_bat_swing_mph',
 'qualified_bat_swing_present',
 'signed_prequote_last_5_official_games_mean_walks',
 'at_least_5_true_prequote_prior_games_present',
)
PENALTY=16.0
FIT_END='2026-07-01T00:00:00+00:00'


def _utc(date)->pd.Timestamp:
    a=pd.to_datetime(date,utc=True,errors='coerce')
    if pd.isna(a):raise ValueError('Source has invalid/unknown captured or first-pitch timestamp')
    return a


def _clamp(value:float,center:float,scale:float)->float:
    if not np.isfinite(value):raise ValueError('Nonfinite model feature, refuse to invent')
    return float(np.clip((value-center)/scale,-2.0,2.0))


def _logit(p:float)->float:
    p=float(p)
    if not np.isfinite(p) or not .001<p<.999:
        raise ValueError('Invalid no-vig market probability')
    return math.log(p/(1.0-p))


def _sigmoid(x:float)->float:
    if x>=0:
        z=math.exp(-min(x,700))
        return 1/(1+z)
    z=math.exp(max(x,-700))
    return z/(1+z)


def restricted_train_vector(verified_training_row:dict)->list[float]:
    """Reuse previously validated side-adjusted research columns 0:2+10:16."""
    v=speed_walk_vector(verified_training_row)
    selection_side=str(verified_training_row.get('side') or '').lower()
    if selection_side not in ('over','under'):
        raise ValueError('Training selection is neither OVER nor UNDER')
    x=v[:2]+v[10:16]
    if len(x)!=8 or not np.isfinite(x).all():
        raise ValueError('Invalid historical 8-column train data')
    return x


def restricted_live_vector(source_book_control:dict,original_v2:dict)->list[float]:
    if source_book_control.get('schema')!=MARKET_CONTROL_SCHEMA:
        raise ValueError('This is not an authentic original market-only source-time control')
    if source_book_control.get('market_metric')!='hits' or float(source_book_control.get('line',-1))!=.5:
        raise ValueError('Hits OVER 0.5 is the only previously fitted market')
    if source_book_control.get('canonical_model_side')!='OVER':
        raise ValueError('Pre-registered forward research uses literal OVER, not postgame winning side')
    if original_v2.get('schema')!=LIVE_SCHEMA or original_v2.get('source_history_revision')!=LIVE_REVISION:
        raise ValueError('Only original source-hashed pregame V2 feature snapshots are accepted')
    if source_book_control.get('source_original_lineup_sha256')!=original_v2.get('original_append_only_line_sha256'):
        raise ValueError('Original lineup source hash mismatch')
    if int(source_book_control['game_pk'])!=int(original_v2['game_pk']) or int(source_book_control['mlbam_player_id'])!=int(original_v2['player_id']):
        raise ValueError('Mismatched original MLB official game.player ID in forward sources')
    if source_book_control.get('betting_play_authorized') is not False or source_book_control.get('wager_submitted') is not False:
        raise ValueError('Paid bet cannot masquerade as research-only source')
    if original_v2.get('betting_prediction_written') is not False or original_v2.get('live_play_approved') is not False:
        raise ValueError('Original true source features were not research-only')
    if original_v2.get('frozen_before_scheduled_first_pitch') is not True:
        raise ValueError('Missing original pregame source feature authorization')
    start=_utc(source_book_control['actual_game_event_start_utc'])
    source_start=_utc(original_v2['scheduled_first_pitch_utc'])
    captured=_utc(original_v2['source_capture_at_utc'])
    frozen=_utc(original_v2['feature_frozen_at_utc'])
    quote=_utc(source_book_control['source_original_market_quote_at_utc'])
    control_frozen=_utc(source_book_control['frozen_shadow_at_utc'])
    if source_start!=start:
        raise ValueError('Original official fixture start mismatch')
    if not captured<=frozen<=quote<=control_frozen<start:
        raise ValueError('Source quote captured before pregame feature freeze or after first pitch')
    season=start.year
    if original_v2.get('completed_season_biomechanics_year')!=season-1:
        raise ValueError('Completed prior season true speed data must be from the immediately prior year')
    fair=float(source_book_control.get('raw_no_vig_market_probability_over'))
    x=[1.0,_logit(fair)]
    sp_ok=original_v2.get('prior_speed_observed') is True
    bat_ok=original_v2.get('prior_bat_observed') is True
    speed=original_v2.get('prior_sprint_speed_ft_per_sec')
    bat=original_v2.get('prior_bat_speed_mph')
    if sp_ok and (not isinstance(speed,(int,float)) or not 10<=float(speed)<=36):
        raise ValueError('Invalid observed true sprint feet/sec')
    if bat_ok and (not isinstance(bat,(int,float)) or not 35<=float(bat)<=105):
        raise ValueError('Invalid observed bat swing miles/hour')
    speed_component=_clamp(float(speed),27.,3.) if sp_ok else 0.
    bat_component=_clamp(float(bat),72.,7.) if bat_ok else 0.
    last_day=original_v2.get('last_prior_date')
    valid_walks=(original_v2.get('prior_history_at_least_5_completed_games') is True
                 and last_day is not None
                 and pd.notna(last_day)
                 and pd.Timestamp(last_day).date()<quote.date()
                 and original_v2.get('prior_last5_walks_avg') is not None)
    w=original_v2.get('prior_last5_walks_avg')
    if valid_walks and (not isinstance(w,(float,int)) or not 0<=float(w)<=5):
        raise ValueError('Prior five-game source walks value implausible')
    walk_component=_clamp(float(w),.5,1.5) if valid_walks else 0.
    x.extend([speed_component,1. if sp_ok else 0.,
              bat_component,1. if bat_ok else 0.,
              walk_component,1. if valid_walks else 0.])
    if len(x)!=8 or not np.isfinite(x).all():
        raise ValueError('Invalid source-time prior completed season model feature vector')
    return x


def fit_restricted_training(history:list[dict],previous_research_model:dict)->dict:
    if not history or len(history)!=90:
        raise ValueError('Expected same original fixed 90 externally vendor-graded independent MLB games')
    if previous_research_model.get('model_version')!=SIXTEEN_FEATURES_MODEL_VERSION or previous_research_model.get('live_plays_approved') is not False:
        raise ValueError('Prior frozen 90-game model provenance missing or falsely approved')
    if previous_research_model.get('training_independent_games')!=90 or previous_research_model.get('train_july_outcomes_used') is not False:
        raise ValueError('July was used in calibration training; refuse')
    history=sorted(history,key=lambda x:(str(x['official_start']),int(x['official_game_pk'])))
    keys=[int(x['official_game_pk']) for x in history]
    if len(keys)!=len(set(keys)) or keys!=previous_research_model['training_official_game_pks']:
        raise ValueError('Training independent official game IDs differ from frozen model')
    if any(x.get('status')!='VERIFIED_HISTORICAL' for x in history):
        raise ValueError('Training source is not original vendor-verified game grade')
    if any(_utc(x['official_start'])>=_utc(FIT_END) for x in history):
        raise ValueError('Later July/future game must never enter original 90-game fit')
    if any(x.get('original_live_feature_capture_verified') is not False for x in history):
        raise ValueError('Historical research postgame participant source falsely called true pregame')
    X=np.asarray([restricted_train_vector(row) for row in history],dtype=float)
    y=np.asarray([int(row['verified_win']) for row in history],dtype=float)
    if not np.isin(y,[0,1]).all():
        raise ValueError('Nonbinary original vendor outcomes')
    fitted_base=_fit_small_ridge_logistic(X[:,:2],y,regularization=PENALTY)
    saved=np.asarray(previous_research_model['market_calibration_beta'],dtype=float)
    if np.max(np.abs(fitted_base-saved))>1e-9:
        raise ValueError('Original market-only calibration beta changed; do not fit new research model')
    fitted=_fit_small_ridge_logistic(X,y,regularization=PENALTY)
    material={
        'game_ids':keys,
        'X':X.round(9).tolist(),
        'y':y.astype(int).tolist(),
        'feature_names':RESTRICTED_NAMES,
    }
    fingerprint=hashlib.sha256(json.dumps(material,sort_keys=True,default=list,separators=(',',':')).encode()).hexdigest()
    return {
        'model_version':MODEL_VERSION,
        'features':list(RESTRICTED_NAMES),
        'coefficients':[round(float(v),12) for v in fitted],
        'base_market_beta':[round(float(v),12) for v in fitted_base],
        'training_independent_games':len(history),
        'training_first_start':history[0]['official_start'],
        'training_last_start':history[-1]['official_start'],
        'training_end_exclusive_utc':FIT_END,
        'training_official_game_pks':keys,
        'training_feature_and_label_fingerprint_sha256':fingerprint,
        'training_sprint_present':sum(x.get('sprint_speed_observed') is True for x in history),
        'training_bat_present':sum(x.get('bat_speed_observed') is True for x in history),
        'training_prior5_walk_present':sum(x.get('walks_quote_time_safe') is True for x in history),
        'preregistered_l2_ridge_lambda':PENALTY,
        'selection_side_directions':{'OVER':sum(x['side']=='over' for x in history),
                                     'UNDER':sum(x['side']=='under' for x in history)},
        'source_completed_2025_season_retrieved_october_2026':True,
        'not_yet_a_pristine_proven_predictive_market_edge':True,
        'July_results_used_in_fit':False,
        'is_full_advanced_16_feature_model':False,
        'live_betting_approved':False,
        'betting_model_promotion_forbidden':True,
        'probability_predictions_must_be_frozen_before_first_pitch':True,
    }


def _validate_frozen_model(m:dict):
    if m.get('model_version')!=MODEL_VERSION or m.get('training_independent_games')!=90:
        raise ValueError('Expected specific prior vendor-trained restricted 8-feature model')
    if m.get('features')!=list(RESTRICTED_NAMES) or len(m.get('coefficients') or [])!=8:
        raise ValueError('Unexpected model schema or coefficients')
    if m.get('live_betting_approved') is not False or m.get('July_results_used_in_fit') is not False:
        raise ValueError('Restricted research-only model already approved or used July labels')
    if m.get('is_full_advanced_16_feature_model') is not False:
        raise ValueError('Missing opposing/park source cannot be marked as full model')
    if len(set(m.get('training_official_game_pks') or []))!=90:
        raise ValueError('Corrupt or duplicate historical independent training sample IDs')
    if not np.isfinite(np.asarray(m['coefficients'],dtype=float)).all():
        raise ValueError('Invalid fitted model coefficient source')


def pair_forward_with_live_asof(
    original_market_controls:list[dict],
    official_pregame_player_features:list[dict],
    model:dict,
    *,frozen_model_sha256:str,now:datetime
)->list[dict]:
    _validate_frozen_model(model)
    if now.tzinfo is None:raise ValueError('Observed pregame clock must be offset aware')
    if len(frozen_model_sha256)!=64:
        raise ValueError('Missing immutable frozen model SHA256')
    by_identity={}
    for source in official_pregame_player_features:
        key=(int(source['game_pk']),int(source['player_id']))
        if key in by_identity:raise ValueError('Duplicate source frozen game.player ID')
        by_identity[key]=source
    out=[];seen=set()
    for source in original_market_controls:
        key=(int(source['game_pk']),int(source['mlbam_player_id']))
        if key in seen:raise ValueError('Duplicate original independent game/player frozen hits-control market')
        seen.add(key)
        if key not in by_identity:
            raise ValueError('Original market control game.player ID does not match V2 frozen lineup/feature source')
        feature=by_identity[key]
        start=_utc(source['actual_game_event_start_utc'])
        if _utc(now)>=start:
            continue
        if _utc(source['frozen_shadow_at_utc'])>_utc(now):
            raise ValueError('Original market-only forecast capture is in the future of this model freeze')
        if key[0] in model['training_official_game_pks'] or _utc(model['training_last_start'])>=start:
            raise ValueError('Original training game or future-only model cannot be a forward prediction')
        vec=restricted_live_vector(source,feature)
        predicted=_sigmoid(float(np.dot(vec,np.asarray(model['coefficients'],dtype=float))))
        if not .001<predicted<.999:
            raise ValueError('Invalid prospective restricted model probability')
        out.append({
            'schema':SCHEMA,
            'game_pk':key[0],
            'mlbam_player_id':key[1],
            'player_name_official':source.get('player_name_official'),
            'source_true_lineup_team_side':feature['team_side_at_capture'],
            'market_metric':'hits',
            'line':float(source['line']),
            'canonical_model_side':'OVER',
            'sportsbook_selected':source['sportsbook_selected'],
            'source_provider':source['source_provider'],
            'model_version':MODEL_VERSION,
            'model_coefficients_frozen_sha256':frozen_model_sha256,
            'features':dict(zip(RESTRICTED_NAMES,[round(float(x),10) for x in vec])),
            'prior_2025_sprint_observed':feature['prior_speed_observed'] is True,
            'prior_2025_bat_observed':feature['prior_bat_observed'] is True,
            'prior_walk5_asof_available':bool(vec[7]),
            'original_source_frozen_player_at_utc':feature['feature_frozen_at_utc'],
            'original_source_lineup_sha256':feature['original_append_only_line_sha256'],
            'original_market_control_sha256':source['baseline_model_coefficients_sha256'],
            'source_original_market_quote_at_utc':source['source_original_market_quote_at_utc'],
            'market_fair_over_at_original_quote':float(source['raw_no_vig_market_probability_over']),
            'market_only_calibrated_over_at_original_quote':float(source['calibrated_market_control_probability_over']),
            'calibrated_restricted_speed_walk_probability_over':round(float(predicted),12),
            'original_game_start_at_utc':source['actual_game_event_start_utc'],
            'first_prospective_prediction_frozen_at_utc':_utc(now).isoformat(),
            'source_provenance_class':'BEFORE_FIRST_PITCH_ORIGINAL_LINEUP_BEFORE_ODDS_PRIOR_2025_SPEED_WALKS_ONLY',
            'full_advanced_pitchem_park_features_used':False,
            'full_context_model_used':False,
            'probable_pitcher_not_treated_as_confirmed':True,
            'current_game_outcome_not_available_at_freeze':True,
            'true_source_time_ridge_research_only':True,
            'July_test_has_previously_been_seen':True,
            'live_play_approved':False,
            'wager_executed':False,
            'advanced_edge_proven':False,
            'market_profitability_evaluated':False,
            'correlated_players_are_not_independent_game_blocks':True,
        })
    return sorted(out,key=lambda x:(x['game_pk'],x['mlbam_player_id']))


def _key(record:dict)->tuple[int,int,str,float]:
    return (int(record['game_pk']),int(record['mlbam_player_id']),
            str(record['market_metric']),float(record['line']))


def _read_jsonl(file:Path)->list[dict]:
    if not file.exists():return []
    with file.open('r',encoding='utf-8') as f:
        return [json.loads(s) for s in f if s.strip()]


def append_first_restricted_shadow(path:Path,rows:list[dict])->int:
    if not rows:return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+'.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        already={}
        for r in _read_jsonl(path):
            if r.get('schema')!=SCHEMA:raise ValueError('Unrecognized existing restricted shadow source')
            key=_key(r)
            if key in already:raise ValueError('Duplicate existing research shadow key')
            already[key]=r
        new=[];batch=set()
        for r in rows:
            if r.get('schema')!=SCHEMA or r.get('live_play_approved') is not False or r.get('wager_executed') is not False:
                raise ValueError('Only research-only pregame shadow eligible')
            if _utc(r['first_prospective_prediction_frozen_at_utc'])>=_utc(r['original_game_start_at_utc']):
                raise ValueError('Cannot create a shadow after kickoff')
            key=_key(r)
            if key in batch:raise ValueError('Duplicated prospective game/player/market')
            batch.add(key)
            if key in already:
                for k in ('model_coefficients_frozen_sha256','calibrated_restricted_speed_walk_probability_over',
                          'original_source_lineup_sha256','source_original_market_quote_at_utc',
                          'market_fair_over_at_original_quote'):
                    if already[key].get(k)!=r.get(k):
                        raise ValueError('First prospective model forecast conflict; never rewrite a frozen shadow')
                continue
            new.append(r);already[key]=r
        if new:
            with path.open('a',encoding='utf-8') as dst:
                for row in new:
                    dst.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n')
                dst.flush();os.fsync(dst.fileno())
        return len(new)


def freeze_model_once()->dict:
    if FROZEN_MODEL.exists():
        raise ValueError('Restricted source-time model already frozen; no retraining or overwriting')
    base=json.loads(CONTROL_MODEL.read_text())
    if base.get('model_version')!=SIXTEEN_FEATURES_MODEL_VERSION:
        raise ValueError('Old 90-game frozen model has an unexpected version')
    current=json.loads(TRAIN.read_text())
    train=[r for r in current if r.get('context_status')=='PREGAME_CONTEXT_VERIFIED']
    store=pd.read_parquet(FEATURES)
    train=enrich_provenance_sample(train,store)
    out=fit_restricted_training(train,base)
    out['created_at_utc']=datetime.now(timezone.utc).isoformat()
    out['source_sha256']={str(p.relative_to(ROOT)):sha_file(p) for p in
                          (TRAIN,FEATURES,CONTROL_MODEL,PREREGISTRATION)}
    FROZEN_MODEL.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print('RESTRICTED_SPEED_BAT_WALKS_FITTED_ON_PREJULY_90',
          json.dumps({k:out[k] for k in (
              'model_version','training_independent_games',
              'training_sprint_present','training_bat_present',
              'training_prior5_walk_present','features','coefficients')},sort_keys=True))
    return out


def shadow_cycle(
    controls_file:Path=CONTROL_LEDGER,
    v2_file:Path=LIVE_ADVANCED,
    model_file:Path=FROZEN_MODEL,
    original_file:Path=ORIGINAL_PREGAME_LINEUPS,
    output:Path=OUTPUT,*,now:datetime|None=None,
)->dict:
    observed=now or datetime.now(timezone.utc)
    if observed.tzinfo is None:raise ValueError('Need exact observer timezone')
    controls=_read_jsonl(controls_file)
    official=_read_jsonl(v2_file)
    frozen=json.loads(model_file.read_text())
    _validate_frozen_model(frozen)
    expected_hashes=frozen.get('source_sha256')
    if not expected_hashes:
        raise ValueError('Frozen research model missing source manifests')
    for rel,digest in expected_hashes.items():
        if sha_file(ROOT/rel)!=digest:
            raise ValueError('Fitted model training source or preregistration was modified')
    # Restore the 90-game original market control relation exactly. Never
    # allow coeffs from a new/unrecognized training cohort.
    base=json.loads(CONTROL_MODEL.read_text())
    if len(frozen.get('base_market_beta') or [])!=2 or any(
        abs(a-b)>1e-9 for a,b in zip(frozen['base_market_beta'],base['market_calibration_beta'])
    ):
        raise ValueError('Restricted new source model lost correspondence with previously frozen market calibrator')
    existing=_read_jsonl(output)
    known={_key(x) for x in existing}
    model_sha=sha_file(model_file)
    for record in existing:
        if record.get('schema')!=SCHEMA or record.get('model_coefficients_frozen_sha256')!=model_sha:
            raise ValueError('Already frozen restricted model/source SHA changed; manual audit needed')
    pending=[r for r in controls if (
        int(r['game_pk']),int(r['mlbam_player_id']),str(r['market_metric']),float(r['line'])
    ) not in known]
    if pending and observed<min(_utc(x['actual_game_event_start_utc']) for x in pending):
        matches={(int(r['game_pk']),int(r['player_id'])) for r in official}
        if any((int(c['game_pk']),int(c['mlbam_player_id'])) not in matches for c in pending):
            raise ValueError('Unable to map a first frozen market control to exact official pregame lineup player ID')
        verify_original_pregame_source(official,original_file)
        predictions=pair_forward_with_live_asof(pending,official,frozen,
                         frozen_model_sha256=model_sha,now=observed)
    else:
        predictions=[]
    newly=append_first_restricted_shadow(output,predictions)
    final=_read_jsonl(output)
    return {
        'schema':SCHEMA,
        'observed_at_utc':_utc(observed).isoformat(),
        'original_market_only_shadow_file_sha256':sha_file(controls_file),
        'original_true_pregame_feature_file_sha256':sha_file(v2_file),
        'frozen_restricted_training_model_sha256':model_sha,
        'features_frozen_at_first_market_control_player_sample':True,
        'initial_market_control_forecast_game_blocks':len({r['game_pk'] for r in controls}),
        'new_restricted_source_time_forecasts':newly,
        'total_immutable_restricted_player_forecasts':len(final),
        'independent_forward_games':len({r['game_pk'] for r in final}),
        'source_2025_speed_sprint_bat_and_prior5_walk_features_truly_used':True,
        'uses_full_16_feature_pitcher_park_model':False,
        'actual_prior_original_model_approved_as_live_bet':False,
        'winner_or_profitable_market_advantage_proven':False,
        'funds_spent_or_bet_submitted':False,
        'status':'RESTRICTED_ADVANCED_SOURCE_TIME_PROSPECTIVE_RESEARCH_ONLY',
    }


def main():
    ap=argparse.ArgumentParser(description='Pre-registered bounded MLB speed/bat/walks forward shadow model')
    ap.add_argument('--stage',choices=['train_once','freeze_forecasts'],required=True)
    args=ap.parse_args()
    if args.stage=='train_once':
        freeze_model_once()
        return
    state=shadow_cycle()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    tmp=SUMMARY.with_suffix('.tmp')
    tmp.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
    os.replace(tmp,SUMMARY)
    print('MLB_RESTRICTED_ADVANCED_TRUE_FORWARD_RESEARCH',json.dumps(state,sort_keys=True))


if __name__=='__main__':
    main()
