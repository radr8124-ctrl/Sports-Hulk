#!/usr/bin/env python3
"""Validate supported contract mechanics; never invent model advantage or authorize orders."""
import datetime as dt
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
import re
import urllib.request
from audit_prediction_execution_evidence import ROOT, DEST, BASE, get, save, now
from review_kalshi_nfl_settlement_terms import review
from audit_polymarket_nfl_contracts import instant

def number(value):
 try:
  value=Decimal(str(value))
  if not value.is_finite():raise ValueError('Nonfinite')
  return value
 except (InvalidOperation,TypeError):raise ValueError('Invalid decimal')
def poly_fee(shares,price,schedule,maker=False):
 c,p,r=number(shares),number(price),number(schedule.get('rate'))
 if not (c>0 and 0<p<1 and 0<=r<=1) or schedule.get('exponent')!=1 or schedule.get('takerOnly') is not True:raise ValueError('Unsupported fee inputs')
 return Decimal(0) if maker else (c*r*p*(1-p)).quantize(Decimal('.00001'),rounding=ROUND_HALF_UP)
def kalshi_rounding(revenue,model_fee,precision):
 revenue,fee,precision=map(number,(revenue,model_fee,precision))
 if fee<0 or precision not in (Decimal('.01'),Decimal('.0001')):raise ValueError('Unsupported rounding')
 trade=fee.quantize(Decimal('.000001'),rounding=ROUND_CEILING)
 aligned=((revenue-trade)/precision).to_integral_value(rounding=ROUND_FLOOR)*precision
 return dict(trade_fee=trade,rounding_fee=revenue-trade-aligned,aligned_change=aligned)
def normalize(text):return re.sub(r'\s+',' ',text or '').strip()
def poly_terms(text,outcomes):
 text=normalize(text)
 checks=dict(outcomes=len(outcomes)==2 and len(set(outcomes))==2 and all(f'This market will resolve to "{o}" if {o} win the game.' in text for o in outcomes),overtime='Overtime is included if played.' in text,tie='If the game ends in a tie, this market will resolve 50-50.' in text,postponement='If the game is postponed, this market will remain open until the game has been completed.' in text,cancellation='If the game is canceled entirely, with no make-up game, this market will resolve 50-50.' in text)
 return dict(review_passed=all(checks.values()),checks=checks,payout_scenarios=dict(win=1,loss=0,tie=.5,postponed='WAIT_FOR_COMPLETION',cancelled_no_makeup=.5),final_exchange_settlement_verified=False)
def documentation(url):
 receipt=dict(source_url=url,captured_at_utc=now())
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'SportsZenithReadOnlyEvidence/1.0'}),timeout=15) as response:raw=response.read()
  receipt.update(status='CAPTURED',sha256=hashlib.sha256(raw).hexdigest(),text=raw.decode())
 except Exception as error:receipt.update(status='UNAVAILABLE',error_kind=type(error).__name__)
 return receipt

def main():
 poly=json.loads((DEST/'polymarket_nfl_contract_audit_latest.json').read_text())
 kalshi=json.loads((DEST/'kalshi_nfl_contract_audit_latest.json').read_text())
 docs=[documentation(url) for url in ('https://docs.polymarket.com/trading/fees.md','https://docs.polymarket.com/market-data/market-details.md','https://docs.kalshi.com/getting_started/fee_rounding.md')]
 formula_supported=all(d['status']=='CAPTURED' for d in docs[:2]) and 'fee = C × feeRate × p × (1 - p)' in docs[0].get('text','') and 'feeSchedule' in docs[1].get('text','')
 requests=['https://gamma-api.polymarket.com/markets/'+r['id'] for r in poly['contracts']]+[BASE+'/markets/'+r['ticker'] for r in kalshi['contracts']]
 with ThreadPoolExecutor(max_workers=4) as pool:receipts=list(pool.map(get,requests))
 gammas=receipts[:len(poly['contracts'])]
 clob_urls=['https://clob.polymarket.com/markets/'+r.get('data',{}).get('conditionId','UNAVAILABLE') for r in gammas]
 with ThreadPoolExecutor(max_workers=4) as pool:clobs=list(pool.map(get,clob_urls))
 poly_rows=[]
 for saved,gamma,clob in zip(poly['contracts'],gammas,clobs):
  g,c=gamma.get('data',{}),clob.get('data',{})
  try:
   identities=str(g.get('id'))==saved['id'] and g.get('conditionId')==c.get('condition_id') and g.get('version')==c.get('version')=='v1' and json.loads(g.get('clobTokenIds','[]'))==saved['token_ids'] and [t['token_id'] for t in c.get('tokens',[])]==saved['token_ids'] and [t['outcome'] for t in c.get('tokens',[])]==saved['outcomes'] and instant(g['gameStartTime'])==instant(saved['kickoff'])
  except (ValueError,TypeError,KeyError):identities=False
  terms=poly_terms(g.get('description'),saved['outcomes'])
  terms_match=normalize(g.get('description'))==normalize(c.get('description'))==normalize(saved['rules'])
  fee=None
  try:
   if formula_supported and identities and g.get('feesEnabled') is True:fee=str(poly_fee(100,'.5',g.get('feeSchedule') or {}))
  except (ValueError,TypeError):pass
  poly_rows.append(dict(id=saved['id'],identity_checked=identities,live_open=g.get('active') is True and g.get('closed') is False and g.get('acceptingOrders') is True and c.get('accepting_orders') is True,terms_reviewed=identities and terms_match and terms['review_passed'],payout_scenarios=terms['payout_scenarios'],documented_fee_calculation_checked=fee is not None,taker_fee_100_shares_at_50c=fee,fee_schedule=g.get('feeSchedule'),clob_base_fee=c.get('taker_base_fee'),execution_fees_verified=False,final_exchange_settlement_verified=False,approved_pick=False))
 krows=[]
 for saved,receipt in zip(kalshi['contracts'],receipts[len(poly['contracts']):]):
  current=receipt.get('data',{}).get('market',{})
  fresh=dict(saved,rules_primary=current.get('rules_primary'),rules_secondary=current.get('rules_secondary'))
  same=current.get('ticker')==saved['ticker'] and current.get('event_ticker')==saved['event_ticker'] and current.get('rules_primary')==saved['rules_primary'] and current.get('rules_secondary')==saved['rules_secondary']
  result=review(fresh)
  krows.append(dict(id=saved['ticker'],terms_reviewed=same and result['literal_rule_check_passed'],live_open=current.get('status')=='active',payout_scenarios=dict(win=1,loss=0,tie=.5,postponed_starts_within_48h='OFFICIAL_RESULT',not_started_within_48h='EXCHANGE_FAIR_PRICE'),final_exchange_settlement_verified=False,approved_pick=False))
 model=json.loads((DEST/'nfl_independent_model_validation_latest.json').read_text())
 forward=json.loads((DEST/'nfl_prospective_readiness_latest.json').read_text())
 out=dict(schema='zenith.prediction.contract_validation.v1',checked_at_utc=now(),polymarket=poly_rows,kalshi=krows,documentation=docs,source_receipts=receipts+clobs,model_validation=model,prospective_validation=forward,approved_picks=0,execution_enabled=False)
 save(DEST/'contract_validation_latest.json',out)
 save(DEST/('contract_validation_'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json'),out)
 public_path=ROOT/'commercial_web/public/prediction_market_nfl_evidence.json'
 public=json.loads(public_path.read_text())
 for provider,rows in [('POLYMARKET',poly_rows),('KALSHI',krows)]:
  public['providers'][provider]['validation']=dict(checked_at_utc=out['checked_at_utc'],terms_reviewed=sum(r['terms_reviewed'] for r in rows),live_open=sum(r['live_open'] for r in rows),contracts_checked=len(rows),documented_fee_calculations_checked=sum(r.get('documented_fee_calculation_checked',False) for r in rows),execution_fees_verified=False,final_exchange_settlement_verified=False)
 public['model_validation']=dict(checked_at_utc=model['checked_at_utc'],holdout_games=model['holdout_games'],market_brier=model['market_baseline']['brier'],model_brier=model['candidate_model']['brier'],validated_edge=model['validated_independent_edge'],prospective_finals=forward['independently_scored_final_games'],minimum_finals=forward['minimum_floor'],status='HISTORICAL_ADVANTAGE_NOT_DEMONSTRATED')
 save(public_path,public)
 print(json.dumps({p:public['providers'][p]['validation'] for p in ('POLYMARKET','KALSHI')}))
if __name__=='__main__':main()
