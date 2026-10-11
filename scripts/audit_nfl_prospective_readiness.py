#!/usr/bin/env python3
"""Audit existing prospective NFL model evidence; never modify protected ledgers."""
import json,datetime,pathlib,hashlib
ROOT=pathlib.Path('/home/ubuntu/sports-hulk')
DIR=ROOT/'intelligence_warehouse/nfl_advanced_pregame'
OUT=ROOT/'nfl_live/prediction_markets/nfl_prospective_readiness_latest.json'
FILES={'summary':'NFL_NINE_FEATURE_OFFICIAL_FINAL_COMPARISON_SUMMARY.json','observer':'NFL_FORWARD_OFFICIAL_OBSERVER_CURRENT.json','source':'NFL_NINE_FEATURE_PROSPECTIVE_SHADOW_SOURCE_SUMMARY.json'}
def assess(s,o,source):
 count=int(s.get('source_pairs_scored') or 0)
 floor=int(s.get('independent_game_floor') or 30)
 eligible=(count>=floor and bool(s.get('market_advantage_statistically_proven')) and bool(o.get('independent_edge_proven')) and not bool(o.get('official_betting_allowed') is False))
 return {'frozen_forecasts':int(s.get('original_source_model_game_forecasts') or 0),'independently_scored_final_games':count,'minimum_floor':floor,'remaining_to_floor':max(0,floor-count),'book_quote_research_status':source.get('status'),'official_final_status':s.get('status'),'new_source_quote_pairing':int(source.get('new_9feature_original_game_forecasts') or 0),'model_advantage_verified':bool(s.get('market_advantage_statistically_proven')),'kalshi_model_eligible':eligible,'pick_approval':False,'blocked_reasons':(['INSUFFICIENT_INDEPENDENT_OFFICIAL_FINALS'] if count<floor else [])+(['UNPROVEN_MARKET_ADVANTAGE'] if not s.get('market_advantage_statistically_proven') else [])+(['NEW_VERIFIED_BOOK_QUOTE_PAIRING_UNAVAILABLE'] if not source.get('new_9feature_original_game_forecasts') else [])}
def main():
 raw={k:(DIR/v).read_bytes() for k,v in FILES.items()}
 payload={k:json.loads(v) for k,v in raw.items()}
 data=assess(payload['summary'],payload['observer'],payload['source'])
 data.update({'schema':'zenith.nfl.prospective_readiness.v1','audited_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_checksums_sha256':{k:hashlib.sha256(v).hexdigest() for k,v in raw.items()}})
 OUT.write_text(json.dumps(data,indent=2)+'\n')
 print(json.dumps({k:data[k] for k in ['frozen_forecasts','independently_scored_final_games','minimum_floor','remaining_to_floor','kalshi_model_eligible','blocked_reasons']}))
if __name__=='__main__':main()
