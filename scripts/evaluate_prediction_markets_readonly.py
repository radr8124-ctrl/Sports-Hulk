#!/usr/bin/env python3
"""Conservative offline research gate. Never produces a real-money trade or PLAY."""
import datetime,json,pathlib,os,tempfile,hashlib
ROOT=pathlib.Path('/home/ubuntu/sports-hulk/nfl_live/prediction_markets')
def evaluate(doc,now=None):
    now=now or datetime.datetime.now(datetime.timezone.utc)
    captured=datetime.datetime.fromisoformat(doc['captured_at_utc'].replace('Z','+00:00'))
    age=max(0,(now-captured).total_seconds())
    out=[]
    for r in doc.get('markets',[]):
        failures=[]
        if age>900:failures.append('SOURCE_STALE_OVER_15_MIN')
        if r.get('provider')=='KALSHI':
            bid=r.get('yes_bid');ask=r.get('yes_ask')
            if bid is None or ask is None:failures.append('EXECUTABLE_PRICE_UNVERIFIED')
            elif not (0<=bid<=ask<=1):failures.append('INVALID_BID_ASK')
            if r.get('volume') is None:failures.append('VOLUME_UNVERIFIED')
        else:failures.append('EXECUTABLE_PRICE_UNVERIFIED')
        # Strict requirements: not available in current collector, so NO PLAY.
        failures+=['INDEPENDENT_MODEL_UNAVAILABLE','MARKET_SETTLEMENT_NOT_VERIFIED','FEES_NOT_VERIFIED','CROSS_MARKET_MATCH_NOT_VERIFIED']
        out.append({'provider':r.get('provider'),'market_id':r.get('id'),'event':r.get('event'),'decision':'PASS','simulation_eligible':False,'reason_codes':failures,'market_snapshot_at':doc['captured_at_utc']})
    return {'schema':'zenith.prediction_markets.evaluation.v1','evaluated_at_utc':now.isoformat(),'source_captured_at_utc':doc['captured_at_utc'],'source_sha256':hashlib.sha256(json.dumps(doc,sort_keys=True).encode()).hexdigest(),'status':'NO_VERIFIED_PICKS','evaluated':len(out),'play':0,'monitor':0,'pass':len(out),'records':out,'real_trading_enabled':False}
def main():
    doc=json.loads((ROOT/'latest.json').read_text())
    report=evaluate(doc)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    raw=json.dumps(report,indent=2)+'\n'
    (ROOT/f'evaluation_{stamp}.json').write_text(raw)
    fd,tmp=tempfile.mkstemp(dir=ROOT,prefix='.evaluation_')
    with os.fdopen(fd,'w') as f:f.write(raw)
    os.replace(tmp,ROOT/'evaluation_latest.json')
    print(json.dumps({k:report[k] for k in ['evaluated','play','monitor','pass','status']}))
if __name__=='__main__':main()
