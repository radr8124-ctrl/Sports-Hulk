#!/usr/bin/env python3
"""Sports Zenith: read-only, source-attributed prediction-market research snapshot.
No credentials, orders, recommendations, implied edge, or personal data.
"""
import json, urllib.request, datetime, os, pathlib, tempfile
from urllib.error import URLError

ROOT=pathlib.Path('/home/ubuntu/sports-hulk/nfl_live/prediction_markets')
SPORT_TAGS={'nfl','nba','nhl','mlb','cfb','cbb','soccer','tennis','golf','mma','ufc','f1','formula-1','baseball','basketball','football','hockey','cricket'}
SPORT_WORDS=(' NFL ',' NBA ',' NHL ',' MLB ',' NCAA ',' SUPER BOWL ',' WORLD SERIES ',' STANLEY CUP ',' PREMIER LEAGUE ',' CHAMPIONS LEAGUE ')
def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'SportsZenithPublicMarketResearch/1.0','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=16) as r:return json.load(r)
def num(v):
    try:return float(v)
    except (TypeError,ValueError):return None
def short(v,n=180):return str(v or '')[:n]
def polymarket():
    endpoint='https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false&tag_slug=sports'
    data=get(endpoint)
    rows=[]
    for event in data:
        tags={str(t.get('slug','')).lower() for t in event.get('tags',[]) if isinstance(t,dict)}
        if not (tags&SPORT_TAGS) and not any(w in f" {event.get('title','').upper()} " for w in SPORT_WORDS):continue
        for market in event.get('markets',[])[:80]:
            if market.get('closed') or not market.get('active',True):continue
            prices=market.get('outcomePrices')
            if isinstance(prices,str):
                try:prices=json.loads(prices)
                except (ValueError,TypeError):prices=[]
            outcomes=market.get('outcomes')
            if isinstance(outcomes,str):
                try:outcomes=json.loads(outcomes)
                except (ValueError,TypeError):outcomes=[]
            if not isinstance(prices,list): prices=[]
            if not isinstance(outcomes,list):outcomes=[]
            rows.append(dict(provider='POLYMARKET',id=short(market.get('id'),80),event=short(event.get('title')),question=short(market.get('question')),outcomes=[short(x,60) for x in outcomes[:5]],display_prices=[num(x) for x in prices[:5]],liquidity=num(market.get('liquidityNum',market.get('liquidity'))),volume=num(market.get('volumeNum',market.get('volume'))),end_date=short(market.get('endDate'),50),price_basis='display price, not executable quote',source_endpoint=endpoint))
    return rows
def kalshi():
    endpoint='https://external-api.kalshi.com/trade-api/v2/events?limit=200&status=open&with_nested_markets=true'
    data=get(endpoint)
    rows=[]
    for event in data.get('events',[]):
        if str(event.get('category','')).lower()!='sports':continue
        for market in event.get('markets',[])[:80]:
            rows.append(dict(provider='KALSHI',id=short(market.get('ticker'),100),event=short(event.get('title')),question=short(market.get('title')),yes_bid=num(market.get('yes_bid_dollars')),yes_ask=num(market.get('yes_ask_dollars')),no_bid=num(market.get('no_bid_dollars')),no_ask=num(market.get('no_ask_dollars')),last_price=num(market.get('last_price_dollars')),volume=num(market.get('volume_fp')),open_interest=num(market.get('open_interest_fp')),expiration=short(market.get('expiration_time'),50),price_basis='provider display quote; execution and fees unverified',source_endpoint=endpoint))
    return rows
def main():
    captured=datetime.datetime.now(datetime.timezone.utc).isoformat()
    providers={};allrows=[]
    for name,fn in [('KALSHI',kalshi),('POLYMARKET',polymarket)]:
        try:
            rows=fn();providers[name]={'status':'FETCHED','market_count':len(rows)};allrows+=rows
        except (URLError,TimeoutError,ValueError,KeyError,TypeError) as exc:
            providers[name]={'status':'SOURCE_FAILURE','reason':type(exc).__name__}
    doc={'schema':'zenith.prediction_market.snapshot.v1','captured_at_utc':captured,'status':'RESEARCH_ONLY_NO_APPROVED_PICKS','providers':providers,'market_count':len(allrows),'markets':allrows,'limitations':['Sampling only: does not cover all provider markets','Polymarket prices are indicative, not firm executable bids or asks','No cross-platform event mapping verified','No model projections, fees, settlement or liquidity checks; no picks']}
    ROOT.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(doc,ensure_ascii=False,indent=2)+'\n'
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    (ROOT/f'snapshot_{stamp}.json').write_text(raw)
    fd,path=tempfile.mkstemp(prefix='.next_',dir=ROOT)
    with os.fdopen(fd,'w') as f:f.write(raw)
    os.replace(path,ROOT/'latest.json')
    print(json.dumps({'captured_at':captured,'providers':providers,'total':len(allrows),'output':str(ROOT/'latest.json')}))
if __name__=='__main__':main()
