#!/usr/bin/env python3
"""Fixed conditional historical simulation; never executable exchange P&L."""
import hashlib,json,math
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def profit_multiple(odds):
 odds=float(odds)
 if not math.isfinite(odds) or not 100<=abs(odds)<=10000:raise ValueError("Invalid American odds")
 return odds/100 if odds>0 else 100/abs(odds)
def select(row,source,threshold,cost):
 p=float(row['candidate'])
 if not math.isfinite(p) or not 0<=p<=1:raise ValueError("Invalid probability")
 if int(row['label'])!=row['label'] or row['label'] not in (0,1):raise ValueError("Nonbinary outcome")
 if int(source['season'])!=row['season'] or int(source['week'])!=row['week']:raise ValueError("Fixture mismatch")
 if source['home_score']==source['away_score']:raise ValueError("Tie excluded from binary simulation")
 if int(source['home_score']>source['away_score'])!=row['label']:raise ValueError("Outcome mismatch")
 home=profit_multiple(source['home_moneyline']);away=profit_multiple(source['away_moneyline'])
 pair=1/(1+home)+1/(1+away)
 if not 1.000001<pair<=1.25:raise ValueError("Invalid paired overround")
 market=(1/(1+home))/pair
 if abs(market-row['market'])>1e-9:raise ValueError("Price/prediction source mismatch")
 values=[p*home-(1-p)-cost,(1-p)*away-p-cost]
 side=0 if values[0]>=values[1] else 1
 chosen=values[side]>=threshold
 win=bool(row['label']==(1 if side==0 else 0))
 gross=(home if side==0 else away) if win else -1.
 return dict(game_id=row['game_id'],season=row['season'],week=row['week'],selected=chosen,side='home' if side==0 else 'away',model_probability=p if side==0 else 1-p,american_odds=float(source['home_moneyline'] if side==0 else source['away_moneyline']),expected_net_return=values[side],won=win,gross_profit_units=gross if chosen else 0.,stress_net_profit_units=(gross-cost) if chosen else 0.)
def summarize(rows,reps,seed):
 bets=[r for r in rows if r['selected']];n=len(bets)
 groups={}
 for r in rows:
  key=(r['season'],r['week'])
  group=groups.setdefault(key,[0.,0])
  group[0]+=r['stress_net_profit_units'];group[1]+=int(r['selected'])
 ci=None
 if n>=30 and len({(r['season'],r['week']) for r in bets})>=10:
  groups=np.array(list(groups.values()));rng=np.random.default_rng(seed)
  ids=rng.integers(0,len(groups),size=(reps,len(groups)))
  sums=groups[ids].sum(axis=1);valid=sums[:,1]>0
  ci=np.quantile(sums[valid,0]/sums[valid,1],[.025,.975]).tolist()
 return dict(games=len(rows),selections=n,wins=sum(r['won'] for r in bets),gross_profit_units=sum(r['gross_profit_units'] for r in rows),stress_net_profit_units=sum(r['stress_net_profit_units'] for r in rows),stress_net_roi=sum(r['stress_net_profit_units'] for r in rows)/n if n else None,week_block_stress_roi_95ci=ci,roi_interval_status='DESCRIPTIVE_ONLY' if ci else 'INSUFFICIENT_SELECTIONS')
def main():
 protocol_path=ROOT/'reports/NFL_SELECTIVE_VALUE_PROTOCOL_20261011.json';protocol=json.loads(protocol_path.read_text())
 if protocol['minimum_expected_return_after_stress']!=.03 or protocol['hypothetical_cost_per_unit_stake']!=.02:raise ValueError("New protocol required")
 source_path=ROOT/'data_vault/derived/NFL_GAME_MASTER.csv';prediction_path=ROOT/'nfl_live/prediction_markets/nfl_opponent_epa_challenger_latest.json'
 data=pd.read_csv(source_path,low_memory=False)
 if data.game_id.duplicated().any():raise ValueError("Duplicate master identity")
 master=data.set_index('game_id').to_dict('index');pred=json.loads(prediction_path.read_text())
 if sha(source_path)!=pred['historical_master_sha256']:raise ValueError("Master changed since predictions")
 cohorts={}
 for key in ('predictions','secondary_predictions'):
  source=pred[key]
  if len({r['game_id'] for r in source})!=len(source):raise ValueError("Duplicate prediction")
  expected=protocol['rolling_seasons'] if key=='predictions' else [protocol['secondary_seen_season']]
  if sorted({r['season'] for r in source})!=expected:raise ValueError("Unexpected seasons")
  cohorts[key]=[select(r,master[r['game_id']],.03,.02) for r in source]
 if set(r['game_id'] for r in cohorts['predictions'])&set(r['game_id'] for r in cohorts['secondary_predictions']):raise ValueError("Cohort overlap")
 out=dict(schema='zenith.nfl.selective_value_audit.v1',checked_at_utc=datetime.now(timezone.utc).isoformat(),protocol=protocol,protocol_sha256=sha(protocol_path),prediction_sha256=sha(prediction_path),master_sha256=sha(source_path),rolling=summarize(cohorts['predictions'],10000,61011),secondary_seen_2025=summarize(cohorts['secondary_predictions'],10000,61012),by_season={str(year):summarize([r for r in cohorts['predictions'] if r['season']==year],10000,61011+year) for year in protocol['rolling_seasons']},records=cohorts,validated_exchange_profit=False,validated_edge=False,approved_picks=0,production_model_changed=False)
 path=ROOT/'nfl_live/prediction_markets/nfl_selective_value_latest.json';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(out,indent=2)+'\n');tmp.replace(path)
 public_path=ROOT/'commercial_web/public/prediction_market_nfl_evidence.json';public=json.loads(public_path.read_text())
 public['selective_value_audit']={k:out[k] for k in ('checked_at_utc','rolling','secondary_seen_2025','validated_edge','production_model_changed')}
 public['selective_value_audit']['protocol']=protocol
 tmp=public_path.with_suffix('.tmp');tmp.write_text(json.dumps(public,indent=2)+'\n');tmp.replace(public_path)
 print(json.dumps({k:out[k] for k in ('rolling','secondary_seen_2025','by_season','validated_edge')}))
if __name__=='__main__':main()
