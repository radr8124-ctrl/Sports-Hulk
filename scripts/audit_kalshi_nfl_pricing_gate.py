#!/usr/bin/env python3
"""Read-only Kalshi NFL quote/fee/model comparison receipt, no recommendations."""
import datetime,json,pathlib,decimal,collections,hashlib
ROOT=pathlib.Path('/home/ubuntu/sports-hulk')
SRC=ROOT/'nfl_live/prediction_markets/kalshi_nfl_contract_audit_latest.json'
OUT=ROOT/'nfl_live/prediction_markets/kalshi_nfl_pricing_gate_latest.json'
def amount(v):
 try:
  d=decimal.Decimal(str(v))
  return float(d) if d.is_finite() and 0<=d<=1 else None
 except (ValueError,TypeError,decimal.InvalidOperation):return None
def report(contracts,source_time,model_ok=False,fees_ok=False):
 rows=[]
 for c in contracts:
  bid,ask=amount(c.get('yes_bid_dollars')),amount(c.get('yes_ask_dollars'))
  reasons=[]
  if bid is None or ask is None:reasons.append('TWO_SIDED_QUOTE_MISSING')
  elif bid>ask:reasons.append('CROSSED_OR_INVALID_SPREAD')
  if c.get('status')!='active':reasons.append('CONTRACT_NOT_ACTIVE')
  if not model_ok:reasons.append('INDEPENDENT_PROJECTION_NOT_VALIDATED')
  if not fees_ok:reasons.append('FEE_SCHEDULE_NOT_VALIDATED')
  reasons.extend(['ORDER_BOOK_DEPTH_UNVERIFIED','SETTLEMENT_AND_TIE_RISK_REQUIRES_MODEL'])
  rows.append({'ticker':c.get('ticker'),'espn_event_id':c.get('espn_event_id'),'yes_team_abbr':c.get('yes_team_abbr'),'bid_dollars':bid,'ask_dollars':ask,'display_spread_dollars':round(ask-bid,4) if bid is not None and ask is not None and bid<=ask else None,'gross_break_even_probability_before_fees':ask,'independent_projection_probability':None,'fee_adjusted_edge':None,'decision':'PASS','reason_codes':reasons})
 return {'schema':'zenith.kalshi.nfl.pricing_gate.v1','generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_contract_capture_utc':source_time,'contracts_evaluated':len(rows),'plays':0,'passes':len(rows),'quote_valid_count':sum(x['display_spread_dollars'] is not None for x in rows),'model_proven':False,'fees_verified':False,'real_money_trading_enabled':False,'rows':rows}
def main():
 d=json.loads(SRC.read_text())
 model=json.loads((ROOT/'commercial_web/public/nfl_intelligence.json').read_text())
 frozen=json.loads((ROOT/'commercial_web/public/nfl_frozen_game_intelligence.json').read_text())
 # We never accept source health as proof of independent, unseen forward edge.
 model_ok=bool(frozen.get('historic_2025_holdout_model_better_than_market')) and model.get('overall_status')=='CURRENT'
 out=report(d['contracts'],d['captured_at_utc'],model_ok=False,fees_ok=False)
 out['model_source_status']=model.get('overall_status')
 out['model_comparison_allowed']=False
 out['source_sha256']=hashlib.sha256(SRC.read_bytes()).hexdigest()
 OUT.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({k:out[k] for k in ('contracts_evaluated','quote_valid_count','plays','passes','model_source_status')}))
if __name__=='__main__':main()
