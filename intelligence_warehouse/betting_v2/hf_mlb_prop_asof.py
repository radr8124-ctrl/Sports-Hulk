"""As-of historical MLB player-form experiment for verified HF odds samples.

Not an existing Sports Zenith trained production model; never writes live model
state, official results, forward ledgers, or alters betting thresholds.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
import math

import numpy as np
import pandas as pd

from .hf_mlb_prop_pilot import (
    MARKETS, HITTING_MARKETS, OFFICIAL_HISTORY, ROOT, _unique_verified,
    _utc_timestamp, clean_player_name, safe_number,
)


def enrich_strictly_pregame(verified_rows: list[dict], official_history: pd.DataFrame,
                             *, minimum_games: int = 5) -> list[dict]:
    """Use only completed official games dated strictly before the bet snapshot.

    Current-game official data may establish an unambiguous player ID, but
    current-game statistics NEVER become input features.
    """
    h=official_history.copy()
    needed={'game_pk','player_id','player','group','official_date','game_date','status','game_type'}
    if not needed.issubset(h.columns):
        raise ValueError('Missing historical player identity/timestamp fields')
    h=h[h.game_type.astype(str).str.upper().eq('R')]
    h=h[h.status.astype(str).str.upper().isin(['FINAL','COMPLETED EARLY'])].copy()
    h['_player_norm']=h.player.map(clean_player_name)
    h['_official_date']=pd.to_datetime(h.official_date,errors='coerce').dt.date
    h['_game_start']=pd.to_datetime(h.game_date,errors='coerce',utc=True)
    h=h[h._game_start.notna()].copy()
    outputs=[]
    for row in verified_rows:
        r=dict(row)
        r['asof_status']='NOT_ELIGIBLE_FOR_PREGAME_FEATURES'
        if r.get('status') not in ('VERIFIED_HISTORICAL','OFFICIAL_DERIVED_HISTORICAL'):
            outputs.append(r)
            continue
        name=clean_player_name(r.get('player'))
        current=h[(h.game_pk==r.get('official_game_pk'))&(h._player_norm==name)]
        group=str(r.get('official_group') or '').upper()
        if group:
            current=current[current.group.astype(str).str.upper()==group]
        if len(current)!=1:
            r['asof_status']='NO_UNIQUE_PLAYER_ID_MATCH'
            outputs.append(r);continue
        player_id=current.iloc[0].player_id
        if pd.isna(player_id):
            r['asof_status']='NO_UNIQUE_PLAYER_ID_MATCH'
            outputs.append(r);continue
        market=str(r.get('market') or '').lower()
        field=MARKETS.get(market)
        if field is None or field not in h.columns:
            r['asof_status']='UNSUPPORTED_PREGAME_STAT'
            outputs.append(r);continue
        quote=_utc_timestamp(r.get('ts'))
        if quote is None:
            r['asof_status']='INVALID_BET_CAPTURE_TIMESTAMP'
            outputs.append(r);continue
        cutoff=quote.date()
        prior=h[(h.player_id==player_id)&
                (h.group.astype(str).str.upper()==str(current.iloc[0]['group']).upper())&
                (h._official_date<cutoff)&
                (h._game_start<quote)].sort_values(['_game_start','game_pk']).drop_duplicates(['game_pk','group'])
        r['prior_games_available']=len(prior)
        prior=prior[pd.to_numeric(prior[field],errors='coerce').notna()]
        if len(prior)<minimum_games:
            r['asof_status']='INSUFFICIENT_PREGAME_PLAYER_GAMES'
            outputs.append(r);continue
        last5=prior.tail(5)
        avg5=float(pd.to_numeric(last5[field]).mean())
        avg10=float(pd.to_numeric(prior.tail(10)[field]).mean())
        line=safe_number(r.get('line'))
        if line is None:
            r['asof_status']='INVALID_MARKET_LINE'
            outputs.append(r);continue
        side=str(r.get('side') or '').lower()
        direction=1 if side=='over' else -1 if side=='under' else 0
        if direction==0:
            r['asof_status']='INVALID_BET_SIDE'
            outputs.append(r);continue
        feature=direction*(avg5-line)/math.sqrt(max(1.0,line+1.0))
        feature=max(-4.0,min(4.0,feature))
        r.update({
            'asof_status':'PREGAME_FEATURE_VERIFIED',
            'official_player_id':int(player_id),
            'pregame_stat_name':field,
            'prior_stat_samples':len(prior),
            'last5_stat_avg':round(avg5,6),
            'last10_stat_avg':round(avg10,6),
            'pregame_context_signal':round(feature,6),
            'prior_latest_date':str(prior['_official_date'].max()),
            'bet_quote_date_utc':str(cutoff),
            'feature_rule':'STRICTLY_PRIOR_COMPLETED_DATE_ONLY;TARGET_AND_LATER_GAMES_EXCLUDED',
        })
        outputs.append(r)
    return outputs


def _logit(p: np.ndarray) -> np.ndarray:
    p=np.clip(p,0.001,0.999)
    return np.log(p/(1-p))


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1/(1+np.exp(-np.clip(x,-30,30)))


def _fit_small_ridge_logistic(features: np.ndarray, y: np.ndarray,
                              *, regularization: float = 4.0) -> np.ndarray:
    """Regularize to raw market baseline, NOT to winning postgame features."""
    n=features.shape[1]
    prior=np.zeros(n,dtype=float)
    prior[1]=1.0  # intercept=0, market logit coefficient=1
    beta=prior.copy()
    penalty=np.eye(n,dtype=float)*regularization
    penalty[0,0]=0.0
    for _ in range(100):
        probs=_sigmoid(features@beta)
        weights=np.maximum(probs*(1-probs),1e-6)
        gradient=features.T@(probs-y)+penalty@(beta-prior)
        hessian=features.T@(features*weights[:,None])+penalty
        try:
            step=np.linalg.solve(hessian,gradient)
        except np.linalg.LinAlgError:
            step=np.linalg.pinv(hessian)@gradient
        beta-=step
        if max(abs(step))<1e-8:break
    return beta


def compare_model_vs_market(asof_rows: list[dict], *, train_fraction: float = .6) -> dict:
    # Exclude any row without pregame features or whose verified historical
    # game identity is unclear. Holdout is strictly AFTER training by kickoff.
    valid=[r for r in asof_rows if r.get('status')=='VERIFIED_HISTORICAL'
           and r.get('asof_status')=='PREGAME_FEATURE_VERIFIED'
           and safe_number(r.get('market_implied_probability')) is not None
           and safe_number(r.get('pregame_context_signal')) is not None]
    valid=_unique_verified(valid)
    n=len(valid)
    if n<30:
        return {'historical_scope':'RESEARCH_ONLY_NOT_PRODUCTION_APPROVED',
                'status':'INSUFFICIENT_ASOF_HOLDOUT_GAMES',
                'pregame_ready_independent_games':n}
    boundary=max(1,min(n-1,int(n*train_fraction)))
    while boundary<n and valid[boundary-1]['official_start']==valid[boundary]['official_start']:
        boundary+=1
    if boundary==n:
        return {'historical_scope':'RESEARCH_ONLY_NOT_PRODUCTION_APPROVED','status':'NO_SEPARATE_HOLDOUT_TIME_BLOCK'}
    train=valid[:boundary];holdout=valid[boundary:]
    assert set(x['official_game_pk'] for x in train).isdisjoint({x['official_game_pk'] for x in holdout})
    assert train[-1]['official_start'] < holdout[0]['official_start']

    def features(rows,with_trend):
        p=np.asarray([float(r['market_implied_probability']) for r in rows])
        cols=[np.ones(len(rows)),_logit(p)]
        if with_trend:cols.append(np.asarray([float(r['pregame_context_signal']) for r in rows]))
        return np.column_stack(cols)

    yt=np.asarray([float(r['verified_win']) for r in train])
    yh=np.asarray([float(r['verified_win']) for r in holdout])
    beta_market=_fit_small_ridge_logistic(features(train,False),yt)
    beta_augmented=_fit_small_ridge_logistic(features(train,True),yt)
    market=np.asarray([float(r['market_implied_probability']) for r in holdout])
    calibrated=_sigmoid(features(holdout,False)@beta_market)
    augmented=_sigmoid(features(holdout,True)@beta_augmented)
    brier=lambda p: round(float(np.mean((p-yh)**2)),6)
    ll=lambda p:round(float(np.mean(-(yh*np.log(np.clip(p,1e-6,1-1e-6))+(1-yh)*np.log(np.clip(1-p,1e-6,1-1e-6))))),6)
    raw_brier,cal_brier,aug_brier=brier(market),brier(calibrated),brier(augmented)
    return {
        'historical_scope':'RESEARCH_ONLY_NOT_PRODUCTION_APPROVED',
        'status':'CHRONOLOGICAL_EXPERIMENT_COMPLETED',
        'experimental_model':'RIDGE_LOGISTIC_MARKET_PLUS_ASOF_PLAYER_STAT_TREND',
        'no_original_hulk_model_predictions':True,
        'train_games':len(train),
        'holdout_games':len(holdout),
        'train_last_start':train[-1]['official_start'],
        'holdout_first_start':holdout[0]['official_start'],
        'chronological_no_game_overlap':True,
        'chronological_no_time_overlap':True,
        'market_only_raw_brier':raw_brier,
        'market_recalibrated_brier':cal_brier,
        'market_plus_pregame_brier':aug_brier,
        'augmented_minus_market_raw_brier':round(aug_brier-raw_brier,6),
        'augmented_minus_calibrated_market_brier':round(aug_brier-cal_brier,6),
        'market_raw_logloss':ll(market),
        'market_recalibrated_logloss':ll(calibrated),
        'market_plus_pregame_logloss':ll(augmented),
        'market_only_coefficients':[round(float(x),6) for x in beta_market],
        'augmented_coefficients':[round(float(x),6) for x in beta_augmented],
        'pre_match_features':'LAST_5_OFFICIAL_STAT_MEAN_MINUS_BET_LINE;ONLY_PRIOR_COMPLETED_DATES',
        'sample_limitations':'54 offset-selected bets from heterogeneous markets; 22-game holdout; outcomes selected after the fact; external rights unverified.',
        'automatic_live_model_approval':False,
    }


def main() -> int:
    parser=argparse.ArgumentParser(description='Research-only historical as-of MLB prop experiment')
    parser.add_argument('--verified-audit',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if any(folder in args.output_dir.parts for folder in ('commercial_web','decision','latest','public')):
        raise SystemExit('Refusing to write any experimental data into live model or UI folders')
    audit=json.loads(args.verified_audit.read_text())
    history=pd.read_csv(OFFICIAL_HISTORY,low_memory=False,usecols=[
        'game_pk','player','player_id','group','official_date','game_date','game_type','status',
        *set(MARKETS.values())])
    enriched=enrich_strictly_pregame(audit,history)
    result=compare_model_vs_market(enriched)
    from collections import Counter
    report={
        'source':'SmartStake/mlb-player-props',
        'generated_at':datetime.now(timezone.utc).isoformat(),
        'features_by_status':dict(Counter(r['asof_status'] for r in enriched)),
        'eligible_independent_games':len({r['official_game_pk'] for r in enriched if r.get('asof_status')=='PREGAME_FEATURE_VERIFIED'}),
        'experimental_holdout':result,
        'deployment':'NOT_DEPLOYED_RESEARCH_ONLY',
    }
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/'asof_audit.json').write_text(json.dumps(enriched,indent=2,default=str)+'\n')
    (args.output_dir/'asof_experiment.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    print(json.dumps(report,indent=2))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
