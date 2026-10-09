"""Preregistered historical prior-only NFL nine-feature logistic shadow.

No 2026 scoring outcomes enter model FIT; those completed, ESPN-verifed games
are only current-season, prior-week TEAM scoring/defense inputs. Historical
2016-2024 ML prices were originally *retrospectively compiled* and have no
per-book timestamp; 2025 is a deliberately not-pristine secondary diagnostic.
Model must freeze BEFORE any source-time 2026 *post-context* bookmaker quote.

Original offense/defense per-play EPA fields were built using shift(1) in the
old builder but their original NFLverse play-by-play parquet source files are
NOT mounted now for independent full replay. This first model doesn't use
them, nor historical postgame weather/roof, stale injuries or QB future info.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import argparse,hashlib,json,math

import numpy as np
import pandas as pd

from .mlb_asof_feature_store import ROOT,sha_file
from .nfl_verified_2026_score_form import make_features

HISTORICAL=ROOT/'data_vault/derived/NFL_GAME_MASTER.csv'
PRE=ROOT/'reports/SPORTS_ZENITH_NFL_2026_SCORE_FORM_MARKET_CHALLENGER_PREREGISTRATION_2026-10-09.md'
MODEL=ROOT/'reports/NFL_2016_2024_PRIOR_SCORE_FORM_9COL_FROZEN_MODEL_20261009.json'
HOLDOUT=ROOT/'reports/NFL_2016_2024_SCORE_FORM_HOLDOUT_2025_CHECKPOINT_20261009.json'
VERSION='NFL_PREQUOTE_SCORE_FORM_9COL_2016_2024_RIDGE20_RESEARCH_V1'
SOURCE_FEATURE_NAMES=(
 'intercept',
 'historical_same_game_home_no_vig_market_logit',
 'prior_same_season_last3_home_away_point_margin_difference_scaled14',
 'prior_same_season_score_vs_opp_defense_matchup_scaled20',
 'prior_same_season_home_minus_away_points_scored_scaled12',
 'prior_same_season_away_minus_home_points_allowed_scaled12',
 'prior_original_schedule_home_minus_away_rest_days_scaled7',
 'min_three_prior_completed_games_for_both_teams_divided3',
 'original_scheduled_neutral_venue_indicator',
)
TRAIN_SEASONS=list(range(2016,2025))
HOLDOUT_YEAR=2025
LAMBDA=20.


def _book_p(american):
    try:odd=float(american)
    except (ValueError,TypeError):return None
    if not np.isfinite(odd) or not 100<=abs(odd)<=10000:return None
    return float(100/(100+odd) if odd>0 else (-odd)/(100-odd))


def _sigmoid(z):
    val=np.asarray(z,dtype=float)
    return np.where(val>=0,1/(1+np.exp(-np.clip(val,-700,700))),
                    np.exp(np.clip(val,-700,700))/(1+np.exp(np.clip(val,-700,700))))


def _logit(p):
    if not np.isfinite(p) or not .001<p<.999:
        raise ValueError('Original historical fair home moneyline outside (0,1)')
    return math.log(p/(1-p))


def _prob(x,coefficients)->float:
    return float(_sigmoid(np.dot(np.asarray(x,dtype=float),np.asarray(coefficients,dtype=float))))


def _prior_form(earlier,team):
    latest=earlier.get(team,[])[-3:]
    if not latest:
        return {'games_available':0,'prior_last_3_mean_points_scored':None,
                'prior_last_3_mean_points_allowed':None,
                'prior_last_3_mean_point_margin':None}
    pf=float(np.mean([game[0] for game in latest]))
    pa=float(np.mean([game[1] for game in latest]))
    return {'games_available':len(latest),
            'prior_last_3_mean_points_scored':pf,
            'prior_last_3_mean_points_allowed':pa,
            'prior_last_3_mean_point_margin':pf-pa}


def historical_prior_scoring_matrix(master:pd.DataFrame)->tuple[list[dict],dict]:
    required={
        'game_id','season','week','game_type','gameday','home_team','away_team',
        'home_score','away_score','home_moneyline','away_moneyline',
        'home_rest','away_rest','location'
    }
    if missing:=required-set(master.columns):
        raise ValueError(f'Original historical 10-year NFL source missing required features: {sorted(missing)}')
    if master.game_id.isna().any() or master.duplicated(['game_id']).any():
        raise ValueError('Duplicate historical NFL game original IDs')
    years={int(x) for x in master.season.dropna()}
    if not years.issubset(set(range(2016,2026))) or 2026 in years or len(years)!=len(set(years)):
        raise ValueError('Refusing historical 2016-2025 training source polluted with 2026 future outcomes')
    if not len(master):raise ValueError('No historical completed games')
    s=master.copy()
    s['gameday']=pd.to_datetime(s.gameday,errors='coerce')
    if s.gameday.isna().any():raise ValueError('Invalid completed historical NFL game calendar dates')
    s['week']=pd.to_numeric(s.week,errors='raise').astype(int)
    if not s.week.between(1,24).all():raise ValueError('Invalid NFL source game week')
    s=s.sort_values(['season','week','gameday','game_id'])
    result=[];skipped=defaultdict(int);used_games=0
    for season,year in s.groupby('season',sort=True):
        earlier=defaultdict(list)
        for week,slate in year.groupby('week',sort=True):
            frozen=[]
            for r in slate.itertuples(index=False):
                home=str(r.home_team);away=str(r.away_team)
                if home==away or not home or not away:
                    raise ValueError('Invalid NFL original identical home and away team')
                home_form=_prior_form(earlier,home)
                away_form=_prior_form(earlier,away)
                form=make_features(home_form,away_form,r.home_rest,r.away_rest,
                    str(r.location).lower()=='neutral')
                implied_home=_book_p(r.home_moneyline)
                implied_away=_book_p(r.away_moneyline)
                score_home=pd.to_numeric(r.home_score,errors='coerce')
                score_away=pd.to_numeric(r.away_score,errors='coerce')
                if pd.isna(score_home) or pd.isna(score_away):
                    raise ValueError('Historical NFL game result is not independently completed')
                if not (np.isfinite(score_home) and np.isfinite(score_away) and
                        0<=score_home<=150 and 0<=score_away<=150):
                    raise ValueError('Corrupt original historical completed NFL game score')
                if implied_home is None or implied_away is None:
                    skipped['missing_or_invalid_american_odds']+=1
                elif not 1.000001<implied_home+implied_away<=1.25:
                    skipped['implausible_book_overround']+=1
                elif score_home==score_away:
                    skipped['tied_game_not_binary_home_win']+=1
                else:
                    fair=float(implied_home/(implied_home+implied_away))
                    row={
                        'game_id':str(r.game_id),'season':int(season),
                        'week':int(week),'original_scheduled_day':r.gameday.date().isoformat(),
                        'home_team':home,'away_team':away,
                        'original_compiled_home_moneyline':float(r.home_moneyline),
                        'original_compiled_away_moneyline':float(r.away_moneyline),
                        'original_historical_book_overround':round(implied_home+implied_away,12),
                        'raw_market_home_win_prob':round(fair,12),
                        'features':[1.,round(_logit(fair),12),*form],
                        'observed_home_win':int(score_home>score_away),
                        'prior_home_games_available':home_form['games_available'],
                        'prior_away_games_available':away_form['games_available'],
                        'prior_week_max_for_team_home':max((a[2] for a in earlier.get(home,[])),default=None),
                        'prior_week_max_for_team_away':max((a[2] for a in earlier.get(away,[])),default=None),
                        'historic_actual_weather_or_roof_not_used':True,
                        'source_historical_market_prices_compiled_not_original_quote_timestamped':True,
                        'prior_week_team_stats_only_not_same_game_result':True,
                        'historical_2026_games_not_used_in_training_or_holdout':True,
                    }
                    frozen.append(row)
                    used_games+=1
            # The entire week's predictions were built BEFORE updating state
            # from results of any game in that week (no same-week leakage).
            result.extend(frozen)
            for game in slate.itertuples(index=False):
                earlier[str(game.home_team)].append((float(game.home_score),float(game.away_score),int(week),str(game.game_id)))
                earlier[str(game.away_team)].append((float(game.away_score),float(game.home_score),int(week),str(game.game_id)))
    result.sort(key=lambda r:(r['season'],r['week'],r['game_id']))
    if len({x['game_id'] for x in result})!=len(result):
        raise ValueError('Historical model source game identity duplicated')
    return result,{
        'raw_historical_games':len(master),
        'usable_original_market_price_and_binary_final_games':len(result),
        'seasons':sorted(years),
        'source_historical_prices_not_original_individual_bookmakers_timestamped':True,
        'future_game_scores_used':0,
        'same_game_or_same_week_outcomes_used_as_feature_inputs':False,
        'tied_games_skipped':skipped['tied_game_not_binary_home_win'],
        'reasons_skipped':dict(skipped),
        'seasonal_team_form_resets_each_nfl_season':True,
        'historical_observed_weather_and_roof_not_in_model':True,
        'historical_original_pbp_source_currently_not_replay_available':True,
    }


def _fit_ridge(x,y,l2=LAMBDA):
    # Exact small-parameter Newton ridge fit, same no-future-label principle
    # as the independently validated earlier MLB calibration; do not add
    # dependencies/paid APIs to an already running production server.
    nfeat=x.shape[1]
    prior=np.zeros(nfeat,dtype=float)
    prior[1]=1.
    beta=prior.copy()
    penalty=np.eye(nfeat,dtype=float)*float(l2)
    penalty[0,0]=0.
    for _ in range(150):
        probs=np.asarray(_sigmoid(x@beta),dtype=float)
        weights=np.maximum(probs*(1-probs),1e-6)
        gradient=x.T@(probs-y)+penalty@(beta-prior)
        hessian=x.T@(x*weights[:,None])+penalty
        try:step=np.linalg.solve(hessian,gradient)
        except np.linalg.LinAlgError:
            step=np.linalg.pinv(hessian)@gradient
        beta-=step
        if np.max(np.abs(step))<1e-9:break
    if not np.isfinite(beta).all():
        raise ValueError('Frozen NFL ridge fit diverged')
    return np.asarray(beta,dtype=float)


def _loss(pred,y):
    p=np.clip(np.asarray(pred,dtype=float),1e-7,1-1e-7)
    return {
        'brier':round(float(np.mean((p-y)**2)),9),
        'log_loss':round(float(-np.mean(y*np.log(p)+(1-y)*np.log1p(-p))),9)
    }


def fit_nfl_team_score_model(matrix:list[dict],meta:dict)->dict:
    if not matrix:raise ValueError('No original NHL/NFL historical source games')
    grouped=defaultdict(list)
    for r in matrix:
        season=int(r['season'])
        if season not in set(TRAIN_SEASONS+[HOLDOUT_YEAR]):
            raise ValueError('Model training/validation source outside 2016-2025')
        if len(r.get('features') or [])!=9:
            raise ValueError('Historical NFL model row not nine dimensions')
        if not r.get('prior_week_team_stats_only_not_same_game_result'):
            raise ValueError('Historical source is contaminated with the same game outcome')
        grouped[season].append(r)
    tr=[r for y in TRAIN_SEASONS for r in grouped[y]]
    validation=list(grouped[HOLDOUT_YEAR])
    if not len(tr)>=100 and len(meta.get('seasons',[]))>1:
        raise ValueError('Insufficient original historical market+final training games')
    ids=[r['game_id'] for r in tr]
    if len(ids)!=len(set(ids)) or set(ids).intersection(x['game_id'] for x in validation):
        raise ValueError('Historical team-score train/2025 holdout overlapping game identity')
    X=np.asarray([r['features'] for r in tr],dtype=float)
    y=np.asarray([r['observed_home_win'] for r in tr],dtype=float)
    if not np.isfinite(X).all() or not np.isin(y,[0,1]).all():
        raise ValueError('Unknown original historical training probability/result values')
    beta_market=_fit_ridge(X[:,:2],y)
    beta_full=_fit_ridge(X,y)
    if not np.isfinite(beta_market).all() or not np.isfinite(beta_full).all():
        raise ValueError('Invalid fitted fixed nine-parameter source model')
    holdX=np.asarray([r['features'] for r in validation],dtype=float)
    holdY=np.asarray([r['observed_home_win'] for r in validation],dtype=float)
    if not len(validation):raise ValueError('Missing 2025 independent secondary diagnostic games')
    pure=np.asarray([r['raw_market_home_win_prob'] for r in validation],dtype=float)
    calibrated=_sigmoid(holdX[:,:2]@beta_market)
    challenger=_sigmoid(holdX@beta_full)
    recs={
        'raw_compiled_market_home_no_vig':_loss(pure,holdY),
        'same_train_market_only_ridge':_loss(calibrated,holdY),
        'historical_prior_week_score_form_ridge':_loss(challenger,holdY),
    }
    # Team game outcomes within one NFL week are correlated. Report an
    # explicitly secondary/inspected retrospective week-block bootstrap CI.
    blocks=defaultdict(list)
    for i,r in enumerate(validation):blocks[int(r['week'])].append(i)
    rng=np.random.default_rng(20261009)
    weeks=sorted(blocks)
    deltas=[]
    for _ in range(500):
        selected=rng.choice(weeks,size=len(weeks),replace=True)
        idx=[i for week in selected for i in blocks[int(week)]]
        deltas.append(float(np.mean((pure[idx]-holdY[idx])**2-(challenger[idx]-holdY[idx])**2)))
    bounds=[round(float(q),8) for q in np.quantile(deltas,[.025,.975])]
    material={
        'features':SOURCE_FEATURE_NAMES,'ids':ids,
        'X':np.round(X,10).tolist(),'y':y.astype(int).tolist(),
    }
    return {
        'model_version':VERSION,
        'features':list(SOURCE_FEATURE_NAMES),
        'training_seasons':TRAIN_SEASONS,
        'secondary_holdout_seasons':[HOLDOUT_YEAR],
        'training_independent_games':len(tr),
        'training_game_ids':ids,
        'historical_train_matrix_and_results_sha256':hashlib.sha256(
            json.dumps(material,sort_keys=True,default=list,separators=(',',':')).encode()).hexdigest(),
        'preregistered_fixed_ridge_lambda':LAMBDA,
        'original_prior_mean_coefficients':[0.,1.]+[0.]*7,
        'two_col_market_only_coefficients':[round(float(v),12) for v in beta_market],
        'coefficients':[round(float(v),12) for v in beta_full],
        'holdout_2025_independent_games':len(validation),
        'retrospective_2025_secondary_validation':recs,
        'retrospective_2025_games_seen_in_this_analysis':True,
        'retrospective_2025_week_cluster_market_minus_model_brier_lcb95_ucb95':bounds,
        'historical_game_weather_used_as_first_future_forecast':False,
        'historical_EPA_pbp_original_source_fully_replayed':False,
        'original_compiled_historical_moneyline_not_timestamped_live_book':True,
        'training_2025_outcomes_used':False,
        'training_2026_outcomes_used':False,
        'actual_2026_final_result_used_in_prospective_training':False,
        '2026_live_betting_play_approved':False,
        'real_bookmaker_market_edge_proven':False,
        'model_out_of_sample_proof_not_established_from_one_inspected_2025_season':True,
    }


def freeze_once()->dict:
    if MODEL.exists():raise ValueError('Frozen NFL original coefficient set already exists; cannot retrain')
    data=pd.read_csv(HISTORICAL,low_memory=False)
    matrix,audit=historical_prior_scoring_matrix(data)
    training=fit_nfl_team_score_model(matrix,audit)
    training['trained_frozen_at_utc']=datetime.now(timezone.utc).isoformat()
    training['source_sha256']={
        str(HISTORICAL.relative_to(ROOT)):sha_file(HISTORICAL),
        str(PRE.relative_to(ROOT)):sha_file(PRE),
    }
    training['original_historical_source_rows']=audit['raw_historical_games']
    training['historical_source_quality_summary']=audit
    MODEL.parent.mkdir(parents=True,exist_ok=True)
    MODEL.write_text(json.dumps(training,indent=2,sort_keys=True)+'\n')
    HOLDOUT.write_text(json.dumps({
        'model_version':VERSION,
        'historical_2025_seen_diagnostic_not_pristine_future':True,
        'source_model_sha256':sha_file(MODEL),
        'game_count':training['holdout_2025_independent_games'],
        'evaluations':training['retrospective_2025_secondary_validation'],
        'paired_week_block_95ci_market_minus_advanced_model':
            training['retrospective_2025_week_cluster_market_minus_model_brier_lcb95_ucb95'],
        'live_picks_promoted':0,
    },indent=2,sort_keys=True)+'\n')
    return training


def main():
    ap=argparse.ArgumentParser(description='Fit previously preregistered market/prior-score-form NFL model exactly once')
    ap.add_argument('--stage',required=True,choices=['train_once'])
    ap.parse_args()
    result=freeze_once()
    print('NFL_PREQUOTE_2016_2024_RIDGE_SCORE_FORM_FROZEN',json.dumps({
        k:result[k] for k in ('training_independent_games',
            'holdout_2025_independent_games','coefficients',
            'two_col_market_only_coefficients',
            'retrospective_2025_secondary_validation','real_bookmaker_market_edge_proven')
    },sort_keys=True))


if __name__=='__main__':main()
