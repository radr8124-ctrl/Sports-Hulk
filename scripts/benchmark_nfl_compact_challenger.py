#!/usr/bin/env python3
"""One fixed research challenger; chronological diagnostics never prove prospective edge."""
import hashlib,json,math,sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from intelligence_warehouse.historical_recovery.nfl_prior_score_form_model import historical_prior_scoring_matrix,HISTORICAL,_fit_ridge,_sigmoid,_loss

def chronological_split(rows,season):
 if len({r['game_id'] for r in rows})!=len(rows):raise ValueError('Duplicate game identity')
 train=[r for r in rows if 2016<=int(r['season'])<season]
 test=[r for r in rows if int(r['season'])==season]
 if not train or not test:raise ValueError('Empty chronological split')
 return train,test

def advantage_gate(brier_gain,logloss_gain,ci,forward_proven):
 values=[brier_gain,logloss_gain]+list(ci or [])
 return bool(len(ci or [])==2 and all(math.isfinite(float(v)) for v in values) and brier_gain>0 and logloss_gain>0 and 0<ci[0]<=ci[1] and forward_proven)

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write(path,data):
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(path)
def metrics(rows):
 y=np.array([r['label'] for r in rows]);market=np.array([r['market'] for r in rows]);candidate=np.array([r['candidate'] for r in rows]);old=np.array([r['old_nine_feature'] for r in rows])
 return dict(games=len(rows),market=_loss(market,y),candidate=_loss(candidate,y),old_nine_feature=_loss(old,y))
def interval(rows,reps,seed):
 blocks=defaultdict(list)
 for row in rows:blocks[(row['season'],row['week'])].append((row['market']-row['label'])**2-(row['candidate']-row['label'])**2)
 groups=[np.array(v) for v in blocks.values()];sums=np.array([x.sum() for x in groups]);counts=np.array([len(x) for x in groups]);rng=np.random.default_rng(seed)
 draws=rng.integers(0,len(groups),size=(reps,len(groups)))
 deltas=sums[draws].sum(axis=1)/counts[draws].sum(axis=1)
 return [float(x) for x in np.quantile(deltas,[.025,.975])]
def main():
 protocol_path=ROOT/'reports/NFL_COMPACT_CHALLENGER_PROTOCOL_20261011.json'
 protocol_bytes=protocol_path.read_bytes();protocol=json.loads(protocol_bytes)
 if protocol['columns']!=[0,1,2,6,8] or protocol['ridge_lambda']!=200:raise ValueError('Protocol changed; new research version required')
 matrix,source_audit=historical_prior_scoring_matrix(pd.read_csv(HISTORICAL,low_memory=False))
 folds=[];predictions=[];secondary=[];frozen=None
 for year in protocol['rolling_test_seasons']+[protocol['secondary_seen_diagnostic']]:
  train,test=chronological_split(matrix,year)
  x=np.array([r['features'] for r in train]);y=np.array([r['observed_home_win'] for r in train]);tx=np.array([r['features'] for r in test])
  beta=_fit_ridge(x[:,protocol['columns']],y,l2=protocol['ridge_lambda'])
  old=_fit_ridge(x,y,l2=20)
  candidate=_sigmoid(tx[:,protocol['columns']]@beta);nine=_sigmoid(tx@old)
  rows=[dict(game_id=r['game_id'],season=year,week=r['week'],label=r['observed_home_win'],market=r['raw_market_home_win_prob'],candidate=float(p),old_nine_feature=float(o)) for r,p,o in zip(test,candidate,nine)]
  result=dict(season=year,training_seasons=sorted(set(r['season'] for r in train)),training_games=len(train),training_ids_sha256=digest([r['game_id'] for r in train]),coefficients=beta.tolist(),**metrics(rows))
  folds.append(result)
  if year==2025:
   secondary=rows;frozen=dict(version=protocol['candidate'],coefficients=beta.tolist(),features=protocol['columns'],training_through=2024,training_data_sha256=digest(train),research_only=True,approved_picks=0)
  else:predictions+=rows
 summary=metrics(predictions);ci=interval(predictions,protocol['bootstrap_replicates'],protocol['seed']);gain=summary['market']['brier']-summary['candidate']['brier'];ll=summary['market']['log_loss']-summary['candidate']['log_loss']
 out=dict(schema='zenith.nfl.compact_challenger_benchmark.v1',checked_at_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=hashlib.sha256(protocol_bytes).hexdigest(),source_sha256=hashlib.sha256(HISTORICAL.read_bytes()).hexdigest(),candidate=protocol['candidate'],folds=folds,rolling_summary=summary,rolling_brier_gain=gain,rolling_logloss_gain=ll,rolling_week_block_95ci=ci,secondary_seen_2025=metrics(secondary),historical_data_previously_inspected=True,forward_games_scored=0,validated_edge=advantage_gate(gain,ll,ci,False),approved_picks=0,production_model_changed=False,predictions=predictions,secondary_predictions=secondary,source_audit=source_audit)
 dest=ROOT/'nfl_live/prediction_markets'
 write(dest/'nfl_compact_challenger_latest.json',out)
 write(dest/('nfl_compact_challenger_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json'),out)
 model_path=ROOT/'reports/NFL_COMPACT_RIDGE200_RESEARCH_MODEL_20261011.json'
 if model_path.exists():
  if json.loads(model_path.read_text())!=frozen:raise ValueError('Research model already frozen differently')
 else:write(model_path,frozen)
 public_path=ROOT/'commercial_web/public/prediction_market_nfl_evidence.json';public=json.loads(public_path.read_text())
 public['challenger_benchmark']={k:out[k] for k in ('checked_at_utc','candidate','rolling_summary','rolling_brier_gain','rolling_logloss_gain','rolling_week_block_95ci','secondary_seen_2025','validated_edge','forward_games_scored','production_model_changed')}
 write(public_path,public)
 print(json.dumps(public['challenger_benchmark']))
if __name__=='__main__':main()
