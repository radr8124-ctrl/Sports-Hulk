#!/usr/bin/env python3
"""Join frozen NFL forecasts to Kalshi outcome contracts without treating them as independent edge."""
import json,pathlib,datetime,collections
ROOT=pathlib.Path('/home/ubuntu/sports-hulk')
DATA=ROOT/'nfl_live/prediction_markets'
def join(contracts,forecast_rows):
 by_event=collections.defaultdict(list)
 for r in forecast_rows:by_event[str(r.get('event_id'))].append(r)
 result=[]
 for c in contracts:
  candidates=by_event.get(str(c['espn_event_id']),[])
  reasons=[]
  if len(candidates)!=1:reasons.append('FORECAST_EVENT_MATCH_NOT_UNIQUE')
  model_pct=None
  if len(candidates)==1:
   f=candidates[0]
   # Source uses JAX while ESPN/Kalshi use JAC. No implicit alias allowed.
   alias={'JAC':'JAX'}
   team=alias.get(c['yes_team_abbr'],c['yes_team_abbr'])
   if team==f.get('home'):model_pct=f.get('forecast_home_pct')
   elif team==f.get('away'):model_pct=f.get('forecast_away_pct')
   else:reasons.append('FORECAST_TEAM_NOT_MATCHED')
   if f.get('model_uses_market_input'):reasons.append('FORECAST_INCLUDES_MARKET_INPUT')
   if not f.get('model_beats_market_out_of_sample_proven'):reasons.append('OUT_OF_SAMPLE_ADVANTAGE_NOT_PROVEN')
   if not f.get('actual_sportsbook_executable_current_price_verified'):reasons.append('SPORTSBOOK_EXECUTION_NOT_VERIFIED')
  reasons+=['KALSHI_MARKET_FEE_NOT_VERIFIED','SETTLEMENT_ADJUSTED_PROBABILITY_NOT_VERIFIED','FORWARD_MODEL_EDGE_NOT_PROVEN']
  result.append({'ticker':c['ticker'],'espn_event_id':c['espn_event_id'],'historical_frozen_model_win_pct':model_pct,'independent_win_probability':None,'fee_adjusted_expected_value':None,'decision':'PASS','reasons':list(dict.fromkeys(reasons))})
 return result
def main():
 c=json.loads((DATA/'kalshi_nfl_contract_audit_latest.json').read_text())
 f=json.loads((ROOT/'commercial_web/public/nfl_frozen_game_intelligence.json').read_text())
 rows=join(c['contracts'],f['rows'])
 out={'schema':'zenith.kalshi.nfl.frozen_model_crosswalk.v1','generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'contracts_seen':len(rows),'forecast_rows_seen':len(f['rows']),'mapped_frozen_forecasts':sum(isinstance(x['historical_frozen_model_win_pct'],(int,float)) for x in rows),'independent_edges_verified':0,'approved_picks':0,'forecast_data_kind':f['data_kind'],'forecast_generated_at':f['generated_at'],'rows':rows}
 (DATA/'kalshi_nfl_frozen_model_crosswalk_latest.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({k:out[k] for k in ('contracts_seen','forecast_rows_seen','mapped_frozen_forecasts','independent_edges_verified','approved_picks')}))
if __name__=='__main__':main()
