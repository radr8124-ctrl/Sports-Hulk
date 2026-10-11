#!/usr/bin/env python3
"""Illustrative GENERAL taker fee on captured Kalshi entry costs; never marks a PLAY."""
from decimal import Decimal,ROUND_CEILING
import json,pathlib,datetime
ROOT=pathlib.Path('/home/ubuntu/sports-hulk/nfl_live/prediction_markets')
SOURCE='https://kalshi.com/docs/kalshi-fee-schedule.pdf'
def general_fee(price,contracts,rate='0.07'):
 p=Decimal(str(price));c=Decimal(str(contracts));r=Decimal(rate)
 if not (0<=p<=1 and c>0):raise ValueError('invalid price or size')
 return (r*c*p*(1-p)).quantize(Decimal('.01'),rounding=ROUND_CEILING)
def illustrate(doc):
 rows=[]
 for contract in doc['contracts']:
  samples=[]
  for s in contract['scenarios']:
   full=s['status']=='DEPTH_SUFFICIENT'
   p=s['gross_price_per_contract']
   q=s['requested_contracts']
   if full and p is not None:
    # Price-weighted average approximation; exact split-fill/order fee can differ.
    fee=general_fee(p,q)
    gross=Decimal(str(s['gross_total_dollars']))
    total=gross+fee
    samples.append({'contracts':q,'gross_estimate':float(gross),'illustrative_general_taker_fee':float(fee),'illustrative_total_cost':float(total),'illustrative_break_even_win_probability':float(total/Decimal(str(q))),'status':'UNVERIFIED_MARKET_FEE_AND_FILL'})
   else:samples.append({'contracts':q,'status':'INSUFFICIENT_QUOTED_DEPTH'})
  rows.append({'ticker':contract['ticker'],'scenarios':samples,'decision':'PASS'})
 return {'schema':'zenith.kalshi.nfl.illustrative_fee_scenarios.v1','generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_orderbook_utc':doc['orderbook_capture_utc'],'fee_formula_reference':SOURCE,'fee_rate_assumption':'GENERAL_TAKER_7_PERCENT_NOT_MARKET_VERIFIED','market_fee_verified':False,'independent_model_verified':False,'approved_picks':0,'contracts_evaluated':len(rows),'scenarios_evaluated':sum(len(r['scenarios']) for r in rows),'limitations':['General fee illustration only; market-specific multiplier/exemptions not verified','Price averaged across depth levels and rounded; actual execution can differ','Settlement ties, trading slippage, order rounding, and live fill not modeled','Break even assumes binary full $1 win payout; ties can settle $0.50','No edge or recommendations without independent forward-tested model'],'rows':rows}
def main():
 doc=json.loads((ROOT/'kalshi_nfl_simulated_entry_cost_latest.json').read_text())
 r=illustrate(doc)
 (ROOT/'kalshi_nfl_illustrative_fees_latest.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:r[k] for k in ['contracts_evaluated','scenarios_evaluated','market_fee_verified','approved_picks']}))
if __name__=='__main__':main()
