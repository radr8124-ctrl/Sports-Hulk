#!/usr/bin/env python3
"""Fixed market-informed EPA challenger; historical diagnostics, never live approval."""
import hashlib,json,math,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from benchmark_nfl_compact_challenger import chronological_split,advantage_gate,metrics,interval,write,digest
from intelligence_warehouse.historical_recovery.nfl_prior_score_form_model import historical_prior_scoring_matrix,HISTORICAL,_fit_ridge,_sigmoid
VERSION='NFL_MARKET_PRIOR_OFF_DEF_EPA_RIDGE200_RESEARCH_V1'
FEATURES=['intercept','market_logit','prior5_home_minus_away_off_epa_scaled_point2','prior5_away_minus_home_def_epa_allowed_scaled_point2','rest_difference_scaled7','neutral_venue']
def canonical(team):return {'LA':'LAR','WSH':'WAS','JAC':'JAX','SD':'LAC','OAK':'LV','STL':'LAR'}.get(team,team)
def epa_vector(row,index):
 records=[]
 for side in ('home_team','away_team'):
  source=index.get((row['game_id'],canonical(row[side])))
  if source is None or int(source['season'])!=row['season'] or int(source['week'])!=row['week']:raise ValueError('EPA fixture mismatch')
  for cutoff in ('prior_max_week','def_prior_max_week'):
   if pd.notna(source[cutoff]) and float(source[cutoff])>=row['week']:raise ValueError('Same-week or future EPA contamination')
  records.append(source)
 def value(record,key):
  v=record[key]
  if pd.isna(v):return 0.
  if not math.isfinite(float(v)):raise ValueError('Nonfinite EPA')
  return float(v)
 home,away=records
 off=(value(home,'prior5_off_epa_per_play')-value(away,'prior5_off_epa_per_play'))/.2
 defense=(value(away,'prior5_def_epa_allowed_per_play')-value(home,'prior5_def_epa_allowed_per_play'))/.2
 return [1,row['features'][1],float(np.clip(off,-2,2)),float(np.clip(defense,-2,2)),row['features'][6],row['features'][8]]
def main():
 protocol_path=ROOT/'reports/NFL_EPA_CHALLENGER_PROTOCOL_20261011.json'
 protocol=json.loads(protocol_path.read_text())
 if protocol['features']!=FEATURES or protocol['ridge_lambda']!=200:raise ValueError('Protocol mismatch')
 source_receipts=[];tables=[]
 directory=ROOT/'data_vault/raw/nflverse_research_replay'
 for year in range(2016,2026):
  receipt=json.loads((ROOT/f'reports/NFL_{year}_PBP_REPLAY_V2_RECEIPT_20261011.json').read_text())
  feature_path=directory/f'prior_week_epa_{year}.csv'
  if hashlib.sha256(feature_path.read_bytes()).hexdigest()!=receipt['feature_sha256']:raise ValueError('Feature hash mismatch')
  if hashlib.sha256((directory/f'play_by_play_{year}.parquet').read_bytes()).hexdigest()!=receipt['source_sha256']:raise ValueError('Raw source hash mismatch')
  source_receipts.append(receipt);tables.append(pd.read_csv(feature_path))
 table=pd.concat(tables,ignore_index=True);index={}
 for record in table.to_dict('records'):
  key=(record['game_id'],canonical(record['team']))
  if key in index:raise ValueError('Duplicate EPA game-team identity')
  index[key]=record
 matrix,audit=historical_prior_scoring_matrix(pd.read_csv(HISTORICAL,low_memory=False))
 for row in matrix:row['epa_features']=epa_vector(row,index)
 predictions=[];secondary=[];folds=[];frozen=None
 for year in protocol['rolling_test_seasons']+[2025]:
  train,test=chronological_split(matrix,year)
  x=np.array([r['epa_features'] for r in train]);y=np.array([r['observed_home_win'] for r in train]);tx=np.array([r['epa_features'] for r in test])
  beta=_fit_ridge(x,y,l2=200)
  old=_fit_ridge(np.array([r['features'] for r in train]),y,l2=20)
  prob=_sigmoid(tx@beta);oldprob=_sigmoid(np.array([r['features'] for r in test])@old)
  rows=[dict(game_id=r['game_id'],season=year,week=r['week'],label=r['observed_home_win'],market=r['raw_market_home_win_prob'],candidate=float(p),old_nine_feature=float(o)) for r,p,o in zip(test,prob,oldprob)]
  folds.append(dict(season=year,training_seasons=sorted(set(r['season'] for r in train)),training_ids_sha256=digest([r['game_id'] for r in train]),coefficients=beta.tolist(),**metrics(rows)))
  if year==2025:
   secondary=rows;frozen=dict(version=VERSION,features=FEATURES,coefficients=beta.tolist(),training_through=2024,training_matrix_sha256=digest(train),research_only=True,approved_picks=0)
  else:predictions+=rows
 summary=metrics(predictions);ci=interval(predictions,2000,20261011);gain=summary['market']['brier']-summary['candidate']['brier'];ll=summary['market']['log_loss']-summary['candidate']['log_loss']
 out=dict(schema='zenith.nfl.epa_challenger.v1',candidate=VERSION,checked_at_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=hashlib.sha256(protocol_path.read_bytes()).hexdigest(),historical_master_sha256=hashlib.sha256(HISTORICAL.read_bytes()).hexdigest(),source_receipts=source_receipts,rolling_summary=summary,rolling_brier_gain=gain,rolling_logloss_gain=ll,rolling_week_block_95ci=ci,secondary_seen_2025=metrics(secondary),folds=folds,predictions=predictions,secondary_predictions=secondary,historical_data_previously_inspected=True,forward_games_scored=0,validated_edge=advantage_gate(gain,ll,ci,False),approved_picks=0,production_model_changed=False)
 model_path=ROOT/'reports/NFL_EPA_RIDGE200_RESEARCH_MODEL_20261011.json'
 if model_path.exists():
  if json.loads(model_path.read_text())!=frozen:raise ValueError('Different research model already frozen')
 else:write(model_path,frozen)
 dest=ROOT/'nfl_live/prediction_markets';write(dest/'nfl_epa_challenger_latest.json',out);write(dest/('nfl_epa_challenger_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json'),out)
 public_path=ROOT/'commercial_web/public/prediction_market_nfl_evidence.json';public=json.loads(public_path.read_text());public['epa_challenger_benchmark']={k:out[k] for k in ('candidate','checked_at_utc','rolling_summary','rolling_brier_gain','rolling_logloss_gain','rolling_week_block_95ci','secondary_seen_2025','validated_edge','forward_games_scored','production_model_changed')};write(public_path,public)
 print(json.dumps(public['epa_challenger_benchmark']))
if __name__=='__main__':main()
