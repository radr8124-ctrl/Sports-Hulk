#!/usr/bin/env python3
"""Read-only bounded Kalshi NFL depth audit. No placement, no guaranteed fills."""
import json,urllib.request,urllib.parse,datetime,pathlib,time,os,tempfile
ROOT=pathlib.Path('/home/ubuntu/sports-hulk/nfl_live/prediction_markets')
SOURCE=ROOT/'kalshi_nfl_contract_audit_latest.json'
DEST=ROOT/'kalshi_nfl_orderbooks_latest.json'
def fetch(ticker):
 url='https://external-api.kalshi.com/trade-api/v2/markets/'+urllib.parse.quote(ticker,safe='')+'/orderbook?depth=5'
 request=urllib.request.Request(url,headers={'User-Agent':'SportsZenithPublicOrderbookResearch/1.0'})
 with urllib.request.urlopen(request,timeout=12) as response:return json.load(response)
def sanitize_side(raw):
 out=[]
 if not isinstance(raw,list):return out
 for level in raw[:5]:
  if not isinstance(level,list) or len(level)!=2:continue
  try:price=float(level[0]);size=float(level[1])
  except (TypeError,ValueError):continue
  if 0<=price<=1 and 0<=size<1e9:out.append({'price_dollars':price,'contracts':size})
 return out
def transform(raw):
 orderbook=raw.get('orderbook_fp') or {}
 yes=sanitize_side(orderbook.get('yes_dollars'))
 no=sanitize_side(orderbook.get('no_dollars'))
 return {'yes_bids':yes,'no_bids':no,'top_yes_bid':max((r['price_dollars'] for r in yes),default=None),'top_no_bid':max((r['price_dollars'] for r in no),default=None),'levels_present':bool(yes and no)}
def main():
 source=json.loads(SOURCE.read_text());rows=[];failures=[]
 for contract in source['contracts']:
  ticker=contract['ticker']
  try:
   data=transform(fetch(ticker))
   rows.append({'ticker':ticker,'event_ticker':contract['event_ticker'],'captured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),**data,'state':'ORDERBOOK_OBSERVED_NOT_EXECUTABLE_GUARANTEE'})
  except Exception as e:failures.append({'ticker':ticker,'error_kind':type(e).__name__})
  time.sleep(.08)
 out={'schema':'zenith.kalshi.nfl.orderbooks.v1','captured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'requested':len(source['contracts']),'observed':len(rows),'with_two_sided_depth':sum(r['levels_present'] for r in rows),'failures':failures,'fee_schedule_verified_for_each_market':False,'approved_picks':0,'limitations':['Depth observed at collection time and may disappear','Bids are not guaranteed executable asks','Maker/taker and special event fees still require current market-specific confirmation','No model probability, slippage simulation or execution'],'orderbooks':rows}
 ROOT.mkdir(parents=True,exist_ok=True)
 data=json.dumps(out,indent=2)+'\n'
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 (ROOT/f'kalshi_nfl_orderbooks_{stamp}.json').write_text(data)
 fd,tmp=tempfile.mkstemp(dir=ROOT,prefix='.kalshi_depth_')
 with os.fdopen(fd,'w') as f:f.write(data)
 os.replace(tmp,DEST)
 print(json.dumps({k:out[k] for k in ('requested','observed','with_two_sided_depth','approved_picks')}))
if __name__=='__main__':main()
