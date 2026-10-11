#!/usr/bin/env python3
"""Read-only simulated YES buys from opposing NO bids. No fees or fills assumed."""
import json,pathlib,datetime
ROOT=pathlib.Path('/home/ubuntu/sports-hulk/nfl_live/prediction_markets')
def estimate_yes_buy(levels,quantity):
    if quantity<=0:return {'status':'INVALID_SIZE'}
    offers=[]
    for x in levels:
        try:p=float(x['price_dollars']);size=float(x['contracts'])
        except (KeyError,TypeError,ValueError):continue
        if 0<=p<=1 and size>0:offers.append((1-p,size))
    offers.sort()
    remaining=float(quantity);cost=0.0;filled=0.0
    for price,size in offers:
        take=min(remaining,size)
        cost+=take*price;filled+=take;remaining-=take
        if remaining<=1e-8:break
    return {'status':'DEPTH_SUFFICIENT' if remaining<=1e-8 else 'INSUFFICIENT_DEPTH',
            'requested_contracts':quantity,'observed_fillable_contracts':round(filled,4),
            'gross_price_per_contract':round(cost/filled,6) if filled else None,
            'gross_total_dollars':round(cost,4) if filled else None,
            'fee_included':False,'guaranteed_fill':False}
def main():
    raw=json.loads((ROOT/'kalshi_nfl_orderbooks_latest.json').read_text())
    contracts=[]
    for row in raw['orderbooks']:
        scenarios=[{'buy_yes_contracts':q,**estimate_yes_buy(row['no_bids'],q)} for q in (1,10,100)]
        contracts.append({'ticker':row['ticker'],'depth_sample_utc':row['captured_at_utc'],
                          'side':'BUY_YES_VIA_OPPOSING_NO_BIDS','scenarios':scenarios,
                          'independent_probability':None,'fee_adjusted_edge':None,'decision':'PASS'})
    output={'schema':'zenith.kalshi.nfl.simulated_entry_cost.v1',
            'generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'orderbook_capture_utc':raw['captured_at_utc'],'contracts':contracts,
            'contracts_evaluated':len(contracts),'approved_picks':0,
            'notes':['Historical snapshot simulation only; quotes may have changed',
                     'BUY YES is priced against NO bids: price = $1 minus NO bid',
                     'No transaction fees, independent win probabilities, or verified executions',
                     'Liquidity and matching are not guaranteed']}
    (ROOT/'kalshi_nfl_simulated_entry_cost_latest.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'contracts_evaluated':len(contracts),'scenarios':sum(len(x['scenarios']) for x in contracts),'approved_picks':0}))
if __name__=='__main__':main()
