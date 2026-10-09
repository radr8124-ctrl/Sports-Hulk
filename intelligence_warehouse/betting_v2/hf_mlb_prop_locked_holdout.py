"""Frozen independent-shard backtest for external MLB player-hits odds.

The model is a retrospective research experiment. No production Sports Zenith
model, staking method, PICK/PLAY approval or original forward record changes.
"""
from __future__ import annotations

import numpy as np
from .hf_mlb_prop_pilot import _unique_verified, safe_number
from .hf_mlb_prop_asof import _logit, _sigmoid, _fit_small_ridge_logistic


def _eligible_hits(rows:list[dict])->list[dict]:
    usable=[r for r in rows
            if r.get('status') in ('VERIFIED_HISTORICAL','OFFICIAL_DERIVED_HISTORICAL')
            and r.get('pair_status')=='VERIFIED_SAME_BOOK_TIME_PAIR'
            and r.get('asof_status')=='PREGAME_FEATURE_VERIFIED'
            and r.get('market')=='player hits'
            and isinstance(r.get('verified_win'),bool)
            and safe_number(r.get('market_fair_probability')) is not None
            and .001 < float(r['market_fair_probability']) < .999
            and safe_number(r.get('pregame_context_signal')) is not None
            and r.get('official_game_pk') is not None
            and r.get('official_start')]
    # Deduplicate independent game IDs without rewriting their source-grade
    # provenance. Only the original training freeze was vendor graded.
    usable.sort(key=lambda r:(str(r.get('official_start')),str(r.get('ts')),str(r.get('official_game_pk'))))
    by_game={}
    for row in usable:
        by_game.setdefault(int(row['official_game_pk']),row)
    return sorted(by_game.values(),key=lambda r:(r['official_start'],int(r['official_game_pk'])))


def _matrix(rows:list[dict],trend:bool)->np.ndarray:
    probs=np.array([float(row['market_fair_probability']) for row in rows])
    columns=[np.ones(len(rows)),_logit(probs)]
    if trend:columns.append(np.array([float(row['pregame_context_signal']) for row in rows]))
    return np.column_stack(columns)


def freeze_historical_hits_model(rows:list[dict])->dict:
    train=_eligible_hits(rows)
    if len(train)<30:
        raise ValueError('Need >=30 independent historically verified paired-price games before freezing an exploratory fit')
    yt=np.array([float(r['verified_win']) for r in train])
    cal=_fit_small_ridge_logistic(_matrix(train,False),yt)
    aug=_fit_small_ridge_logistic(_matrix(train,True),yt)
    return {
        'model_name':'HF_MLB_PLAYER_HITS_LOCKED_EXTERNAL_RESEARCH_20261008',
        'version':'V1_FIXED_RIDGE_LOGISTIC_MARKET_FAIR_PLUS_PRIOR_5_PLAYER_HITS',
        'market':'player hits',
        'train_independent_games':len(train),
        'train_last_start':train[-1]['official_start'],
        'train_first_start':train[0]['official_start'],
        'train_official_game_pks':[int(r['official_game_pk']) for r in train],
        'market_only_beta':[round(float(v),10) for v in cal],
        'market_plus_pregame_beta':[round(float(v),10) for v in aug],
        'regularization':4.0,
        'inclusion_rule':'Only exactly same-book-time paired odds and official grade plus strictly earlier player game stats.',
        'training_outcome_seen_only_before':'2026-06-19',
        'deployment':'RESEARCH_ONLY_NO_LIVE_MODEL_ACCESS',
        'training_regime':'RETROSPECTIVE_HISTORICAL_NO_ORIGINAL_HULK_FROZEN_PREDICTIONS',
    }


def evaluate_new_shard_holdout(frozen:dict, rows:list[dict], *, bootstrap_reps:int=2000,seed:int=20261008)->dict:
    base={'research_status':'EXTERNAL_HISTORICAL_ONLY',
          'production_play_approved':False,
          'model_is_frozen':True,
          'training_independent_games':frozen['train_independent_games'],
          'training_last_start':frozen['train_last_start'],
          'holdout_source':'PREVIOUSLY_UNSEEN_PUBLIC_HF_PARQUET_SHARD',
          'limitations':'Retrospective historical game set, selected markets/quotes/bookmakers and source-game identity uncertainty; not forward performance.'}
    training_games=set(frozen['train_official_game_pks'])
    unseen=[r for r in _eligible_hits(rows)
            if r['official_start']>frozen['train_last_start']
            and int(r['official_game_pk']) not in training_games]
    base['holdout_independent_games']=len(unseen)
    if not unseen:
        return {**base,'status':'NO_NEW_CHRONOLOGICALLY_LATER_GAMES'}
    if bootstrap_reps<200:raise ValueError('Bootstrap needs >=200 resamples')
    y=np.array([float(r['verified_win']) for r in unseen])
    raw=np.array([float(r['market_fair_probability']) for r in unseen])
    calibrated=_sigmoid(_matrix(unseen,False)@np.asarray(frozen['market_only_beta']))
    augmented=_sigmoid(_matrix(unseen,True)@np.asarray(frozen['market_plus_pregame_beta']))
    brier=lambda p:round(float(np.mean((p-y)**2)),6)
    diff=(calibrated-y)**2-(augmented-y)**2
    rng=np.random.default_rng(seed)
    draws=rng.integers(0,len(unseen),size=(bootstrap_reps,len(unseen)))
    boot=diff[draws].mean(axis=1)
    ci=np.percentile(boot,[2.5,5,95,97.5])
    return {**base,
            'status':'EXTERNAL_LOCKED_HOLDOUT_EVALUATED' if len(unseen)>=25 else 'SMALL_LOCKED_HOLDOUT_UNDER_25_GAMES',
            'holdout_first_start':unseen[0]['official_start'],
            'holdout_last_start':unseen[-1]['official_start'],
            'no_time_overlap':unseen[0]['official_start']>frozen['train_last_start'],
            'fair_market_brier':brier(raw),
            'frozen_market_only_brier':brier(calibrated),
            'frozen_market_plus_pregame_brier':brier(augmented),
            'feature_minus_market_calibrated_brier':round(-float(diff.mean()),6),
            'game_bootstrap_90pct_ci':[round(float(ci[1]),6),round(float(ci[2]),6)],
            'game_bootstrap_95pct_ci':[round(float(ci[0]),6),round(float(ci[3]),6)],
            'bootstrapped_95pct_advantage_lcb_positive':bool(ci[0]>0),
            'automatic_approval_allowed':False,
            'no_refit_on_test':True}
