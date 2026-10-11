#!/usr/bin/env python3
"""Documented-fee counterfactuals at saved asks, never realized ROI."""
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
from validate_prediction_contracts import poly_fee,kalshi_rounding,number
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'nfl_live/prediction_markets'
def kalshi_fee(quantity,price,multiplier=1,precision='.01'):
 q,p,m=map(number,(quantity,price,multiplier))
 if q<=0 or not 0<p<1 or m<0:raise ValueError('Invalid fee inputs')
 raw=q*Decimal('.07')*m*p*(1-p)
 rounded=kalshi_rounding(-q*p,raw,precision)
 return rounded['trade_fee']+rounded['rounding_fee']
def modeled_roi(probability,price,fee,quantity=100,tie_probability=0,slippage=0):
 p,a,f,q,t,s=map(number,(probability,price,fee,quantity,tie_probability,slippage))
 if not (0<=p<=1 and 0<a<1 and f>=0 and q>0 and 0<=t<=1 and 0<=s<1-a):raise ValueError('Invalid sensitivity inputs')
 acquisition=q*(a+s)+f
 payout=q*((1-t)*p+Decimal('.5')*t)
 return float((payout-acquisition)/acquisition)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 observed_path=DATA/'nfl_narrow_forward_quotes_latest.json';observed=json.loads(observed_path.read_text())
 validation_path=DATA/'contract_validation_latest.json';validation=json.loads(validation_path.read_text())
 execution_path=DATA/'execution_evidence_latest.json';execution=json.loads(execution_path.read_text())
 if observed['source_hashes']['execution']!=sha(execution_path):raise ValueError('Execution source changed')
 if not all(r['status']=='CAPTURED' for r in validation['documentation'][:2]):raise ValueError('Fee documentation unavailable')
 schedule_by_token={}
 contracts=json.loads((DATA/'polymarket_nfl_contract_audit_latest.json').read_text())['contracts']
 validations={r['id']:r for r in validation['polymarket']}
 for c in contracts:
  v=validations[c['id']]
  if not v['identity_checked'] or not v['documented_fee_calculation_checked']:continue
  for token in c['token_ids']:schedule_by_token[token]=v['fee_schedule']
 series=execution['kalshi_source_receipts']['series']['data']['series']
 if series['ticker']!='KXNFLGAME' or series['fee_multiplier']!=1 or series['fee_type']!='quadratic_with_maker_fees':raise ValueError('NFL series changed')
 kalshi_metadata={r['ticker']:r['fees']['metadata_complete'] for r in execution['kalshi']}
 rows=[]
 for r in observed['rows']:
  price=r['observed_ask'];quantity=100;fee=None;rate=None
  if r['provider']=='KALSHI' and kalshi_metadata.get(r['contract_or_token_id']):
   rate=.07;fee=kalshi_fee(quantity,price)
  elif r['provider']=='POLYMARKET':
   schedule=schedule_by_token.get(r['contract_or_token_id'])
   if schedule:rate=schedule['rate'];fee=poly_fee(quantity,price,schedule)
  if fee is None:continue
  p=r['conditional_model_win_probability'];base=modeled_roi(p,price,fee)
  stressed_price=number(price)+Decimal('.01')
  stress_fee=kalshi_fee(quantity,stressed_price) if r['provider']=='KALSHI' else poly_fee(quantity,stressed_price,schedule)
  rows.append(dict(provider=r['provider'],event_id=r['event_id'],team=r['team'],quantity=quantity,observed_ask=price,fee_rate=rate,documented_single_fill_entry_fee=float(fee),conditional_modeled_roi=base,conditional_modeled_roi_with_1c_worse_fill=modeled_roi(p,price,stress_fee,slippage='.01'),conditional_modeled_roi_with_1pct_tie_assumption=modeled_roi(p,price,fee,tie_probability='.01'),observed_depth_at_least_100=r['observed_ask_depth']>=100,actual_execution_fee_verified=False,settlement_adjusted_ev_verified=False,decision='OBSERVE_ONLY'))
 output=dict(schema='zenith.nfl.documented_fee_sensitivity.v1',checked_at_utc=datetime.now(timezone.utc).isoformat(),official_formula_sources=['https://kalshi.com/docs/kalshi-fee-schedule.pdf','https://docs.kalshi.com/getting_started/fee_rounding','https://docs.polymarket.com/trading/fees','https://docs.polymarket.com/market-data/market-details'],kalshi_schedule_review='Official July7 2026 PDF retrieved through web reader; NFL multiplier1 verified; direct VPS PDF retrieval unavailable',source_hashes=dict(observations=sha(observed_path),validation=sha(validation_path),execution=sha(execution_path)),source_observations_captured_at=observed['captured_at_utc'],outcomes_checked=len(rows),positive_before_fees=sum(r['raw_probability_minus_ask']>0 for r in observed['rows']),positive_after_documented_fees=sum(r['conditional_modeled_roi']>0 for r in rows),positive_with_1c_worse_fill=sum(r['conditional_modeled_roi_with_1c_worse_fill']>0 for r in rows),above_3pct_after_documented_fees=sum(r['conditional_modeled_roi']>=.03 for r in rows),best_conditional_modeled_roi=max((r['conditional_modeled_roi'] for r in rows),default=None),rows=rows,realized_roi=None,approved_picks=0,validated_profitable_edge=False,limitations=['Saved quote prices, not current offers or actual fills','100-contract single-fill assumption; depth and availability not guaranteed','Market-assisted probabilities unvalidated; zero-tie base is conditional','Fees documented, actual charged fees and legacy Polymarket parameter reconciliation unverified','No rebates, funding costs or cancellation assumptions credited'])
 path=DATA/'nfl_fee_sensitivity_latest.json';path.write_text(json.dumps(output,indent=2)+'\n')
 public=ROOT/'commercial_web/public/prediction_market_nfl_evidence.json';data=json.loads(public.read_text());data['fee_sensitivity']={k:v for k,v in output.items() if k!='rows'};public.write_text(json.dumps(data,indent=2)+'\n')
 print(json.dumps({k:output[k] for k in ['outcomes_checked','positive_before_fees','positive_after_documented_fees','above_3pct_after_documented_fees','best_conditional_modeled_roi']}))
if __name__=='__main__':main()
