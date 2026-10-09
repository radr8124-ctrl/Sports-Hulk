"""ONE preregistered, source-time-safe external MLB hits model experiment.

Research-only; never an official HULK forward pick. Features/penalty frozen by
reports/HF_MLB_CONTEXT_MODEL_PREREGISTRATION_2026-10-08.md before evaluation.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .hf_mlb_prop_asof import _fit_small_ridge_logistic, _sigmoid
from .hf_mlb_prop_context import CONTEXT_VERSION
from .hf_mlb_prop_pilot import _utc_timestamp,safe_number

MODEL_VERSION = 'HF_MLB_CONTEXT_MARKET_RIDGE_V1_RESEARCH_ONLY_2026_10_08'
FIXED_LAMBDA = 16.0
FEATURE_NAMES = (
    'intercept', 'market_fair_logit',
    'prior_player_trend',
    'opposing_pitchers_hits_allowed_per9',
    'opposing_team_runs_allowed',
    'prior_season_park_factor',
    'prior_player_plate_appearances_role',
    'prior_player_rest_days',
    'previous_player_vs_opp_hits',
    'fixture_home_flag',
)


def _clip(x:object,scale:float,shift:float,bottom:float,top:float)->float:
    n=safe_number(x)
    if n is None:
        raise ValueError('Missing required prior-only player/opponent feature')
    return float(np.clip((n-shift)/scale,bottom,top))


def build_context_vector(row:dict)->list[float]:
    if row.get('market')!='player hits' or row.get('asof_status')!='PREGAME_FEATURE_VERIFIED' or row.get('context_status')!='PREGAME_CONTEXT_VERIFIED' or row.get('pair_status')!='VERIFIED_SAME_BOOK_TIME_PAIR':
        raise ValueError('Only previously audited player-hits odds with all as-of evidence are accepted')
    if row.get('context_version')!=CONTEXT_VERSION:
        raise ValueError('Different as-of context model/provenance')
    if row.get('context_feature_provenance')!='PRIOR_2025_REG_SEASON_PARK_AND_PRIOR_COMPLETED_TEAM_PLAYER_GAMES_ONLY':
        raise ValueError('Prior-only venue and team provenance missing')
    quote=_utc_timestamp(row.get('ts'))
    game=_utc_timestamp(row.get('official_start'))
    if quote is None or game is None or quote>=game:
        raise ValueError('Invalid pregame capture/official first pitch')
    try:park_year=int(row.get('park_reference_season'))
    except (TypeError,ValueError):park_year=0
    if park_year!=quote.year-1:
        raise ValueError('park factor must be from the completed prior season, never current or future season')
    for field in ('feature_asof_date','player_prior_latest_official_date','opp_prior_latest_official_date'):
        dt=pd.to_datetime(row.get(field),errors='coerce')
        if pd.isna(dt):
            raise ValueError(f'prior-only feature timestamp missing: {field}')
        if field=='feature_asof_date':
            permitted=dt.date()<=quote.date()
        else:
            permitted=dt.date()<quote.date()
        if not permitted:
            raise ValueError(f'prior-only feature timestamp invalid: {field}')
    prob=safe_number(row.get('market_fair_probability'))
    if prob is None or not .001<prob<.999:
        raise ValueError('Missing market fair implied probability from exactly paired sportsbook offers')
    rest=safe_number(row.get('player_rest_days'))
    if rest is None or rest<1:
        raise ValueError('Missing or future player rest history')
    home=safe_number(row.get('player_home_flag'))
    if home not in (0,1):
        raise ValueError('Known fixture home/away identity required')
    prior_matchups=safe_number(row.get('hitter_vs_opponent_prior_games'))
    if prior_matchups is None or prior_matchups<0:
        raise ValueError('Prior opponent matchup sample count required')
    if prior_matchups>=2:
        matchup_delta=_clip(row.get('hitter_vs_opponent_prior_hits_per_game'),1.0,
                            safe_number(row.get('last5_stat_avg')) or 0.0,-1.5,1.5)
    else:
        matchup_delta=0.0
    return [
        1.0,
        float(np.log(prob/(1-prob))),
        _clip(row.get('pregame_context_signal'),1.0,0,-3,3),
        _clip(row.get('opp_last10_pitching_hits_allowed_per_9'),3.0,8.5,-2,2),
        _clip(row.get('opp_last10_runs_allowed'),2.5,4.5,-2,2),
        _clip(row.get('park_run_factor'),.2,1.0,-1.5,1.5),
        _clip(row.get('player_last10_pa_avg'),1.4,4.2,-2,2),
        _clip(min(rest,14.0),5.0,2.0,-1.5,2.5),
        matchup_delta,
        float(home)-.5,
    ]


def _unique(rows:list[dict])->list[dict]:
    by_game={}
    for row in sorted(rows,key=lambda r:(str(r.get('official_start')),str(r.get('ts')),str(r.get('official_game_pk')))):
        pk=row.get('official_game_pk')
        if pk is None:
            raise ValueError('Missing independent MLB game identity')
        key=int(pk)
        if key in by_game:
            raise ValueError('Duplicate independent MLB game in fixed-model training/evaluation')
        by_game[key]=row
    return sorted(by_game.values(),key=lambda r:(r['official_start'],int(r['official_game_pk'])))


def freeze_context_model(training:list[dict],*,training_end_exclusive:str='2026-06-19T00:00:00+00:00')->dict:
    cutoff=_utc_timestamp(training_end_exclusive)
    if cutoff is None:
        raise ValueError('Need explicit training cutoff')
    if any(r.get('status')!='VERIFIED_HISTORICAL' for r in training):
        raise ValueError('Training source must have original verified vendor grades, not official-derived/unknown vendor outcomes')
    if any(_utc_timestamp(r.get('official_start')) is None or _utc_timestamp(r.get('official_start'))>=cutoff for r in training):
        raise ValueError('Training crosses preregistered cutoff; no July outcome in fit')
    train=_unique(training)
    if len(train)<50:
        raise ValueError('At least 50 independent, context-complete vendor-graded games required for research fit')
    matrix=np.asarray([build_context_vector(r) for r in train],dtype=float)
    y=np.asarray([float(r['verified_win']) for r in train],dtype=float)
    if not np.isfinite(matrix).all() or not np.isfinite(y).all():
        raise ValueError('Nonfinite training input')
    market_model=_fit_small_ridge_logistic(matrix[:,:2],y,regularization=FIXED_LAMBDA)
    context_model=_fit_small_ridge_logistic(matrix,y,regularization=FIXED_LAMBDA)
    return {
        'model_version':MODEL_VERSION,
        'preregistration':'reports/HF_MLB_CONTEXT_MODEL_PREREGISTRATION_2026-10-08.md',
        'lambda':FIXED_LAMBDA,
        'feature_names':list(FEATURE_NAMES),
        'training_grade_provenance':'ORIGINAL_VENDOR_WIN_LOSS_CROSSCHECKED_WITH_OFFICIAL_MLB',
        'training_independent_games':len(train),
        'training_first_start':train[0]['official_start'],
        'training_last_start':train[-1]['official_start'],
        'training_end_exclusive':cutoff.isoformat(),
        'training_official_game_pks':[int(r['official_game_pk']) for r in train],
        'market_calibrated_beta':[round(float(k),12) for k in market_model],
        'context_plus_market_beta':[round(float(k),12) for k in context_model],
        'not_original_hulk_model':True,
        'july_outcomes_previously_seen':True,
        'production_picks_approved':False,
        'live_model_deployment':'DENIED_RESEARCH_ONLY',
    }


def _loss(y:np.ndarray,prob:np.ndarray)->tuple[float,float]:
    brier=float(np.mean((prob-y)**2))
    lp=np.clip(prob,1e-6,1-1e-6)
    logloss=float(-np.mean(y*np.log(lp)+(1-y)*np.log(1-lp)))
    return round(brier,6),round(logloss,6)


def evaluate_secondary_july(frozen:dict,holdout:list[dict],*,bootstraps:int=4000,seed:int=20261008)->dict:
    meta={
        'experiment':MODEL_VERSION,
        'status':'NO_NEW_AFTER_TRAINING_GAMES',
        'production_picks_approved':False,
        'july_outcomes_previously_seen_in_other_research':True,
        'holdout_not_pristine':True,
        'training_independent_games':frozen['training_independent_games'],
        'training_last_start':frozen['training_last_start'],
        'feature_count':len(FEATURE_NAMES)-2,
        'no_refit_on_july_outcomes':True,
    }
    seen=set(frozen['training_official_game_pks'])
    keep=[r for r in holdout if r.get('status') in ('OFFICIAL_DERIVED_HISTORICAL','VERIFIED_HISTORICAL')
          and r.get('market')=='player hits' and r.get('context_status')=='PREGAME_CONTEXT_VERIFIED'
          and r.get('asof_status')=='PREGAME_FEATURE_VERIFIED' and r.get('pair_status')=='VERIFIED_SAME_BOOK_TIME_PAIR'
          and r.get('official_game_pk') not in seen and r.get('official_start')>frozen['training_last_start']]
    test=_unique(keep)
    meta['holdout_independent_games']=len(test)
    if len(test)<25:
        return meta
    X=np.asarray([build_context_vector(r) for r in test],dtype=float)
    y=np.asarray([float(r['verified_win']) for r in test],dtype=float)
    p_market=np.asarray([float(r['market_fair_probability']) for r in test],dtype=float)
    p_cal=_sigmoid(X[:,:2]@np.asarray(frozen['market_calibrated_beta']))
    p_ctx=_sigmoid(X@np.asarray(frozen['context_plus_market_beta']))
    m_b,m_l=_loss(y,p_market)
    c_b,c_l=_loss(y,p_cal)
    x_b,x_l=_loss(y,p_ctx)
    gains=(p_cal-y)**2-(p_ctx-y)**2
    if bootstraps<1000:raise ValueError('Bootstrap count too small for descriptive interval')
    rng=np.random.default_rng(seed)
    indices=rng.integers(0,len(test),size=(bootstraps,len(test)))
    by_game=gains[indices].mean(axis=1)
    game_ci=np.percentile(by_game,[2.5,97.5])
    by_day=defaultdict(list)
    for i,row in enumerate(test):
        by_day[str(row['official_start'])[:10]].append(i)
    days=sorted(by_day)
    day_idxs=rng.integers(0,len(days),size=(bootstraps,len(days)))
    day_sim=[]
    for draw in day_idxs:
        picks=[ix for k in draw for ix in by_day[days[int(k)]]]
        day_sim.append(float(np.mean(gains[picks])))
    day_ci=np.percentile(day_sim,[2.5,97.5])
    meta.update({
        'status':'SECONDARY_HISTORICAL_CONTEXT_CHECK_ONLY',
        'holdout_first_start':test[0]['official_start'],
        'holdout_last_start':test[-1]['official_start'],
        'holdout_calendar_days':len(days),
        'training_and_test_game_ids_disjoint':True,
        'no_heldout_result_used_for_coefficients':True,
        'raw_fair_market_brier':m_b,
        'market_only_calibrated_brier':c_b,
        'full_context_brier':x_b,
        'raw_fair_market_logloss':m_l,
        'market_only_calibrated_logloss':c_l,
        'full_context_logloss':x_l,
        'context_minus_market_calibrated_brier':round(x_b-c_b,6),
        'game_bootstrap_95pct_brier_gain_ci':[round(float(v),6) for v in game_ci],
        'calendar_day_bootstrap_95pct_brier_gain_ci':[round(float(v),6) for v in day_ci],
        'calendar_day_bootstrap_dates':days,
        'robust_betting_edge_claim_eligible':False,
        'warning':'Model was specified before this evaluation but July game outcomes have been viewed in earlier research; results cannot be called an unseen holdout.',
    })
    return meta
