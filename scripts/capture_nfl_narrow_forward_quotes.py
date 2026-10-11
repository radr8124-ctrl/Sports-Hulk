#!/usr/bin/env python3
"""One frozen NFL model, fresh pre-kickoff exchange observations; no bets."""
import json,hashlib,math
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'nfl_live/prediction_markets'
def stamp(value):return datetime.fromisoformat(str(value).replace('Z','+00:00'))
def eligible(forecast,capture,now):
 try:
  freeze=stamp(forecast['source_first_real_future_prediction_frozen_at_utc'])
  kickoff=stamp(forecast['official_first_pitch_utc']);observed=stamp(capture)
  return bool(freeze<=observed<=now<kickoff and 0<=(now-observed).total_seconds()<=900)
 except (KeyError,ValueError,TypeError):return False
def canonical(team):return {'LA':'LAR','JAC':'JAX','WSH':'WAS'}.get(team,team)
def model_probability(forecast,team):
 p=forecast['nine_feature_score_form_home_win_prob']
 if not isinstance(p,(int,float)) or not math.isfinite(p) or not 0<p<1:raise ValueError('Invalid model probability')
 if canonical(team)==canonical(forecast['home_team']):return p
 if canonical(team)==canonical(forecast['away_team']):return 1-p
 raise ValueError('Outcome team not matched')
def best_ask(book):
 levels=[]
 for item in book.get('asks',[]):
  try:
   p=float(item['price']);q=float(item['size'])
   if math.isfinite(p) and math.isfinite(q) and 0<p<1 and q>0:levels.append((p,q))
  except (KeyError,TypeError,ValueError):continue
 if not levels:return None,None
 price=min(p for p,q in levels)
 return price,sum(q for p,q in levels if p==price)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 now=datetime.now(timezone.utc);protocol_path=ROOT/'reports/NFL_NARROW_FORWARD_PROTOCOL_20261011.json'
 protocol=json.loads(protocol_path.read_text())
 forecast_path=ROOT/'intelligence_warehouse/nfl_advanced_pregame/NFL_FIRST_PREKICKOFF_NINE_FEATURE_SCORE_FORM_SHADOW.jsonl'
 forecasts=[json.loads(x) for x in forecast_path.read_text().splitlines()];by_event={}
 for f in forecasts:
  eid=f['official_espn_event_id']
  if eid in by_event:raise ValueError('Duplicate forecast identity')
  if f['source_frozen_model_sha256']!=protocol['model_sha256']:raise ValueError('Wrong model')
  by_event[eid]=f
 execution_path=DATA/'execution_evidence_latest.json';execution=json.loads(execution_path.read_text())
 kalshi={x['ticker']:x for x in execution['kalshi']}
 probes={x.get('data',{}).get('asset_id'):x for x in execution['polymarket_probes'] if '/book?' in x['source_url'] and x['status']=='CAPTURED'}
 aliases=json.loads((ROOT/'nfl_live/identity/team_aliases.json').read_text())
 name_map={name:team for team,names in aliases.items() for name in names}
 contracts={provider:json.loads((DATA/(provider.lower()+'_nfl_contract_audit_latest.json')).read_text())['contracts'] for provider in ['KALSHI','POLYMARKET']}
 rows=[];rejected={}
 def add(provider,identity,team,f,capture,ask,depth,rules_hash):
  if not eligible(f,capture,now):rejected['STALE_OR_NOT_PREKICKOFF']=rejected.get('STALE_OR_NOT_PREKICKOFF',0)+1;return
  if ask is None or depth is None or not 0<ask<1 or depth<=0:rejected['ASK_DEPTH_UNAVAILABLE']=rejected.get('ASK_DEPTH_UNAVAILABLE',0)+1;return
  p=model_probability(f,team)
  rows.append(dict(provider=provider,contract_or_token_id=identity,event_id=f['official_espn_event_id'],team=canonical(team),kickoff_utc=f['official_first_pitch_utc'],model_frozen_at_utc=f['source_first_real_future_prediction_frozen_at_utc'],book_captured_at_utc=capture,conditional_model_win_probability=p,observed_ask=ask,observed_ask_depth=depth,raw_probability_minus_ask=round(p-ask,9),rules_sha256=rules_hash,fee_adjusted_expected_value=None,settlement_adjusted_probability=None,decision='OBSERVE_ONLY',approved_pick=False,fill_guaranteed=False))
 for c in contracts['KALSHI']:
  f=by_event.get(str(c['espn_event_id']));b=kalshi.get(c['ticker'])
  if f and b and b['book_status']=='CAPTURED':add('KALSHI',c['ticker'],c['yes_team_abbr'],f,b['captured_at_utc'],b['book']['yes_ask'],b['book']['ask_contracts'],c['rules_sha256'])
 for c in contracts['POLYMARKET']:
  f=by_event.get(str(c['espn_event_id']))
  if not f:continue
  if not (len(c['token_ids'])==len(c['outcome_teams'])==2):raise ValueError('Ambiguous token outcomes')
  for token,name in zip(c['token_ids'],c['outcome_teams']):
   b=probes.get(token)
   if not b:continue
   if name not in name_map:raise ValueError('Unknown exact team name')
   ask,depth=best_ask(b['data']);add('POLYMARKET',token,name_map[name],f,b['captured_at_utc'],ask,depth,c['rules_sha256'])
 output=dict(schema='zenith.nfl.narrow_forward_quotes.v1',captured_at_utc=now.isoformat(),protocol=protocol,source_hashes=dict(protocol=sha(protocol_path),forecasts=sha(forecast_path),execution=sha(execution_path)),frozen_forecasts=len(forecasts),future_forecasts=sum(now<stamp(f['official_first_pitch_utc']) for f in forecasts),observed_games=len({r['event_id'] for r in rows}),observed_outcomes=len(rows),rejected=rejected,rows=rows,validated_edge=False,approved_picks=0,limitations=['Market-assisted model lacks proven advantage','Conditional win probability is not exchange settlement-adjusted value','Raw gap omits fees, ties and cancellation; not expected profit','Observed asks/depth are not actual fills'])
 target=DATA/('nfl_narrow_forward_quotes_'+now.strftime('%Y%m%dT%H%M%SZ')+'.json');target.write_text(json.dumps(output,indent=2)+'\n')
 (DATA/'nfl_narrow_forward_quotes_latest.json').write_text(target.read_text())
 print(json.dumps({k:output[k] for k in ('frozen_forecasts','future_forecasts','observed_games','observed_outcomes','rejected','validated_edge')}))
if __name__=='__main__':main()
