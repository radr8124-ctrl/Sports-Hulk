"""Research-only per-market MLB prop fair-price chronology and uncertainty.

No automatic eligibility promotion: external retrospectively recovered bets do
NOT constitute original Sports HULK forward predictions.
"""
from __future__ import annotations

import math
import numpy as np
from .hf_mlb_prop_asof import _fit_small_ridge_logistic, _logit, _sigmoid
from .hf_mlb_prop_pilot import _unique_verified, safe_number


def evaluate_fair_price_lane(rows: list[dict], *, train_fraction: float=.6,
                             seed: int=20261008, bootstrap_reps: int=2000) -> dict:
    header={'historical_scope':'EXTERNAL_BACKTEST_ONLY','live_play_approved':False,
            'independent_forward_outcomes_recorded':0,
            'warning':'Retrospectively assembled cross-source dataset. Not original HULK predictions, not a proof of profitable executable odds.'}
    prelim=[r for r in rows if r.get('status')=='VERIFIED_HISTORICAL'
            and r.get('asof_status')=='PREGAME_FEATURE_VERIFIED']
    markets={str(r.get('market') or '').lower() for r in prelim}
    if len(markets)>1:
        return {**header,'status':'MIXED_MARKET_LANES_FORBIDDEN',
                'eligible_independent_games':0,'markets':sorted(markets)}
    valid=[r for r in prelim
           if r.get('pair_status')=='VERIFIED_SAME_BOOK_TIME_PAIR'
           and safe_number(r.get('market_fair_probability')) is not None
           and .001 < float(r['market_fair_probability']) < .999
           and safe_number(r.get('pregame_context_signal')) is not None
           and isinstance(r.get('verified_win'),bool)]
    unique=_unique_verified(valid)
    n=len(unique)
    header.update({'status':'INSUFFICIENT_LANE_INDEPENDENT_GAMES','market':next(iter(markets),'UNSPECIFIED'),
                   'eligible_independent_games':n,'minimum_games_for_exploratory_holdout':30})
    if n<30:return header
    if not 0<train_fraction<1:raise ValueError('train fraction must be between 0 and 1')
    idx=max(1,min(n-1,int(n*train_fraction)))
    while idx<n and unique[idx-1]['official_start']==unique[idx]['official_start']:
        idx+=1
    if idx>=n:return {**header,'status':'NO_SEPARATE_HOLDOUT_TIME_BLOCK'}
    train,test=unique[:idx],unique[idx:]
    assert train[-1]['official_start'] < test[0]['official_start']
    assert not set(r['official_game_pk'] for r in train)&set(r['official_game_pk'] for r in test)
    def matrix(part,trend):
        p=np.array([float(r['market_fair_probability']) for r in part])
        arr=[np.ones(len(part)),_logit(p)]
        if trend:arr.append(np.array([float(r['pregame_context_signal']) for r in part]))
        return np.column_stack(arr)
    yt=np.array([float(r['verified_win']) for r in train])
    y=np.array([float(r['verified_win']) for r in test])
    raw=np.array([float(r['market_fair_probability']) for r in test])
    beta_cal=_fit_small_ridge_logistic(matrix(train,False),yt)
    beta_aug=_fit_small_ridge_logistic(matrix(train,True),yt)
    cal=_sigmoid(matrix(test,False)@beta_cal)
    augmented=_sigmoid(matrix(test,True)@beta_aug)
    brier=lambda p:round(float(np.mean((p-y)**2)),6)
    ll=lambda p:round(float(-np.mean(y*np.log(np.clip(p,1e-6,1-1e-6))+(1-y)*np.log(np.clip(1-p,1e-6,1-1e-6)))),6)
    delta=(cal-y)**2-(augmented-y)**2  # positive means new feature improved Brier
    rng=np.random.default_rng(seed)
    if bootstrap_reps<200:raise ValueError('Require at least 200 paired game bootstrap iterations')
    indices=rng.integers(0,len(test),size=(bootstrap_reps,len(test)))
    trials=delta[indices].mean(axis=1)
    ci=np.percentile(trials,[0.625,2.5,5,95,97.5,99.375])
    improved=float(delta.mean())>0
    return {
        **header,'status':'HISTORICAL_HOLDOUT_COMPLETED',
        'training_independent_games':len(train),
        'holdout_independent_games':len(test),
        'training_last_start':train[-1]['official_start'],
        'holdout_first_start':test[0]['official_start'],
        'no_game_or_time_overlap':True,
        'fair_market_brier':brier(raw),
        'market_calibrated_brier':brier(cal),
        'fair_market_plus_pregame_brier':brier(augmented),
        'fair_market_logloss':ll(raw),
        'market_calibrated_logloss':ll(cal),
        'fair_market_plus_pregame_logloss':ll(augmented),
        'feature_minus_calibrated_brier':round(-float(delta.mean()),6),
        'paired_game_brier_delta_mean':round(float(delta.mean()),6),
        'paired_game_brier_delta_lcb90':round(float(ci[2]),6),
        'paired_game_brier_delta_ucb90':round(float(ci[3]),6),
        'paired_game_brier_delta_lcb95':round(float(ci[1]),6),
        'paired_game_brier_delta_ucb95':round(float(ci[4]),6),
        'paired_game_brier_delta_lcb9875':round(float(ci[0]),6),
        'paired_game_brier_delta_ucb9875':round(float(ci[5]),6),
        'paired_game_bootstrap_repetitions':bootstrap_reps,
        'augmented_lower_brier_on_this_holdout':improved,
        'bootstrap_90pct_interval_excludes_zero':bool(ci[2]>0 or ci[3]<0),
        'bootstrap_95pct_interval_excludes_zero':bool(ci[1]>0 or ci[4]<0),
        'bootstrap_98_75pct_familywise_four_market_interval_excludes_zero':bool(ci[0]>0 or ci[5]<0),
        'sufficient_sample_for_proof_claim':False,
        'selection_based_on_outcomes':False,
        'sampling_warning':'Sparse externally selected 3-shard pilot, not all games or books, possible label bias. Bootstrap CI describes this holdout only.',
    }
