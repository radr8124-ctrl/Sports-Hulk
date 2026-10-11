#!/usr/bin/env python3
"""One fixed opponent-adjusted EPA experiment, never approval or production mutation."""
import hashlib,json,math,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from benchmark_nfl_epa_challenger import canonical
from benchmark_nfl_compact_challenger import chronological_split,advantage_gate,metrics,interval,write,digest
from intelligence_warehouse.historical_recovery.nfl_prior_score_form_model import historical_prior_scoring_matrix,HISTORICAL,_fit_ridge,_sigmoid
VERSION='NFL_MARKET_PRIOR_OPPONENT_ADJUSTED_EPA_RIDGE200_RESEARCH_V1'
FEATURES=['intercept','market_logit','adjusted_home_minus_away_offense_scaled_point2','adjusted_away_minus_home_defense_allowed_scaled_point2','rest_difference_scaled7','neutral_venue']
def ratings(games,season,week):
 past=[r for r in games if int(r['season'])==season and int(r['week'])<week]
 if not past:return {}
 if len({(r['game_id'],r['team']) for r in past})!=len(past):raise ValueError('Duplicate team-game EPA')
 teams=sorted(set(r['team'] for r in past)|set(r['opponent'] for r in past));index={team:i for i,team in enumerate(teams)};n=len(teams)
 x=np.zeros((len(past),1+2*n));y=np.zeros(len(past));weights=np.zeros(len(past))
 for i,r in enumerate(past):
  if r['team']==r['opponent'] or not math.isfinite(float(r['epa'])) or not 0<float(r['plays'])<=300:raise ValueError('Invalid observed EPA')
  x[i,0]=1;x[i,1+index[r['team']]]=1;x[i,1+n+index[r['opponent']]]=1;y[i]=r['epa']
  weights[i]=float(np.clip(r['plays']/60,.5,1.5))*.9**(week-int(r['week'])-1)
 penalty=np.eye(x.shape[1])*5;penalty[0,0]=0
 beta=np.linalg.solve(x.T@(x*weights[:,None])+penalty,x.T@(weights*y))
 if not np.isfinite(beta).all():raise ValueError('Rating fit nonfinite')
 return {team:dict(offense=float(beta[1+i]),defense_allowed=float(beta[1+n+i]),prior_max_week=max(int(r['week']) for r in past),league_mean=float(beta[0])) for team,i in index.items()}
def main():
 protocol_path=ROOT/'reports/NFL_OPPONENT_EPA_PROTOCOL_20261011.json';protocol=json.loads(protocol_path.read_text())
 if protocol['features']!=FEATURES or protocol['game_win_ridge']!=200 or protocol['rating_ridge']!=5 or protocol['weekly_decay']!=.9:raise ValueError('Protocol mismatch')
 directory=ROOT/'data_vault/raw/nflverse_research_replay';observations=[];receipts=[]
 for year in range(2016,2026):
  receipt=json.loads((ROOT/f'reports/NFL_{year}_PBP_REPLAY_V2_RECEIPT_20261011.json').read_text());path=directory/f'play_by_play_{year}.parquet'
  if hashlib.sha256(path.read_bytes()).hexdigest()!=receipt['source_sha256']:raise ValueError('Raw source hash mismatch')
  raw=pd.read_parquet(path,columns=['game_id','play_id','season','week','posteam','defteam','epa','rush_attempt','pass_attempt','qb_kneel','qb_spike'])
  if not raw.season.eq(year).all() or raw.duplicated(['game_id','play_id']).any():raise ValueError('Raw source identity mismatch')
  plays=raw[raw.epa.notna()&raw.posteam.notna()&raw.defteam.notna()&((raw.rush_attempt==1)|(raw.pass_attempt==1))&(raw.qb_kneel!=1)&(raw.qb_spike!=1)]
  games=plays.groupby(['season','week','game_id','posteam','defteam']).epa.agg(['mean','size']).reset_index().rename(columns={'posteam':'team','defteam':'opponent','mean':'epa','size':'plays'})
  for r in games.to_dict('records'):r['team']=canonical(r['team']);r['opponent']=canonical(r['opponent']);observations.append(r)
  receipts.append(receipt)
 matrix,audit=historical_prior_scoring_matrix(pd.read_csv(HISTORICAL,low_memory=False));cache={};feature_rows=[]
 for row in matrix:
  key=(row['season'],row['week'])
  if key not in cache:cache[key]=ratings(observations,*key)
  adjusted=cache[key];home=adjusted.get(canonical(row['home_team']),{});away=adjusted.get(canonical(row['away_team']),{})
  off=(home.get('offense',0)-away.get('offense',0))/.2;defense=(away.get('defense_allowed',0)-home.get('defense_allowed',0))/.2
  row['adjusted_features']=[1,row['features'][1],float(np.clip(off,-2,2)),float(np.clip(defense,-2,2)),row['features'][6],row['features'][8]]
  feature_rows.append(dict(game_id=row['game_id'],season=row['season'],week=row['week'],home=home,away=away,features=row['adjusted_features']))
 folds=[];predictions=[];secondary=[];frozen=None
 for year in protocol['rolling_test_seasons']+[2025]:
  train,test=chronological_split(matrix,year);x=np.array([r['adjusted_features'] for r in train]);y=np.array([r['observed_home_win'] for r in train]);tx=np.array([r['adjusted_features'] for r in test])
  beta=_fit_ridge(x,y,l2=200);old=_fit_ridge(np.array([r['features'] for r in train]),y,l2=20)
  prob=_sigmoid(tx@beta);oldprob=_sigmoid(np.array([r['features'] for r in test])@old)
  rows=[dict(game_id=r['game_id'],season=year,week=r['week'],label=r['observed_home_win'],market=r['raw_market_home_win_prob'],candidate=float(p),old_nine_feature=float(o)) for r,p,o in zip(test,prob,oldprob)]
  folds.append(dict(season=year,training_seasons=sorted(set(r['season'] for r in train)),training_ids_sha256=digest([r['game_id'] for r in train]),coefficients=beta.tolist(),**metrics(rows)))
  if year==2025:secondary=rows;frozen=dict(version=VERSION,features=FEATURES,coefficients=beta.tolist(),training_through=2024,training_matrix_sha256=digest(train),research_only=True,approved_picks=0)
  else:predictions+=rows
 summary=metrics(predictions);ci=interval(predictions,2000,20261011);gain=summary['market']['brier']-summary['candidate']['brier'];ll=summary['market']['log_loss']-summary['candidate']['log_loss']
 out=dict(schema='zenith.nfl.opponent_epa_challenger.v1',candidate=VERSION,checked_at_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=hashlib.sha256(protocol_path.read_bytes()).hexdigest(),historical_master_sha256=hashlib.sha256(HISTORICAL.read_bytes()).hexdigest(),source_receipts=receipts,rolling_summary=summary,rolling_brier_gain=gain,rolling_logloss_gain=ll,rolling_week_block_95ci=ci,secondary_seen_2025=metrics(secondary),folds=folds,predictions=predictions,secondary_predictions=secondary,feature_rows=feature_rows,historical_data_previously_inspected=True,forward_games_scored=0,validated_edge=advantage_gate(gain,ll,ci,False),approved_picks=0,production_model_changed=False)
 model_path=ROOT/'reports/NFL_OPPONENT_EPA_RESEARCH_MODEL_20261011.json'
 if model_path.exists():
  if json.loads(model_path.read_text())!=frozen:raise ValueError('Different model already frozen')
 else:write(model_path,frozen)
 dest=ROOT/'nfl_live/prediction_markets';write(dest/'nfl_opponent_epa_challenger_latest.json',out);write(dest/('nfl_opponent_epa_challenger_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json'),out)
 public_path=ROOT/'commercial_web/public/prediction_market_nfl_evidence.json';public=json.loads(public_path.read_text());public['opponent_epa_benchmark']={k:out[k] for k in ('candidate','checked_at_utc','rolling_summary','rolling_brier_gain','rolling_logloss_gain','rolling_week_block_95ci','secondary_seen_2025','validated_edge','forward_games_scored','production_model_changed')};write(public_path,public)
 print(json.dumps(public['opponent_epa_benchmark']))
if __name__=='__main__':main()
