#!/usr/bin/env python3
"""Public read-only book and fee evidence. Captures never authorize a trade."""
import datetime as dt
from decimal import Decimal, InvalidOperation
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'nfl_live/prediction_markets'
BASE='https://external-api.kalshi.com/trade-api/v2'
def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def get(url):
    receipt={'source_url':url,'captured_at_utc':now()}
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'SportsZenithReadOnlyEvidence/1.0'}),timeout=15) as response: raw=response.read()
        receipt.update(status='CAPTURED',sha256=hashlib.sha256(raw).hexdigest(),data=json.loads(raw))
    except urllib.error.HTTPError as error: receipt.update(status='HTTP_ERROR',http_status=error.code)
    except Exception as error: receipt.update(status='SOURCE_UNAVAILABLE',error_kind=type(error).__name__)
    return receipt

def book_summary(data):
    def levels(values):
        valid=[]
        for row in values or []:
            try:
                p,q=map(lambda v:Decimal(str(v)),row)
                if p.is_finite() and q.is_finite() and 0<p<1 and 0<q<1000000000:valid.append((p,q))
            except (ValueError,TypeError,InvalidOperation): continue
        return sorted(valid,reverse=True)
    raw=data.get('orderbook_fp') or {}
    yes,no=levels(raw.get('yes_dollars')),levels(raw.get('no_dollars'))
    bid=yes[0][0] if yes else None
    ask=1-no[0][0] if no else None
    return dict(yes_bid=float(bid) if bid is not None else None,yes_ask=float(ask) if ask is not None else None,ask_contracts=float(no[0][1]) if no else None,usable_observed_spread=bid is not None and ask is not None and bid<=ask,execution_verified=False)

def fee_summary(series,changes,event,complete):
    matching=all(c.get('event_ticker')==event for c in changes)
    supported=series.get('ticker')=='KXNFLGAME' and series.get('fee_type') in ('quadratic','quadratic_with_maker_fees') and isinstance(series.get('fee_multiplier'),(int,float))
    return dict(series_fee_type=series.get('fee_type'),series_fee_multiplier=series.get('fee_multiplier'),event_fee_changes_captured=len(changes),metadata_complete=bool(complete and matching and supported),execution_fees_verified=False)

def fee_changes(event):
    receipts=[];changes=[];cursor='';complete=False
    for _ in range(5):
        url=BASE+'/events/fee_changes?'+urllib.parse.urlencode(dict(event_ticker=event,limit=200,cursor=cursor))
        receipt=get(url);receipts.append(receipt)
        if receipt['status']!='CAPTURED':break
        data=receipt['data']
        if not isinstance(data.get('event_fee_changes'),list):break
        changes.extend(data['event_fee_changes']);cursor=data.get('cursor')
        if not cursor:complete=True;break
    return event,changes,complete,receipts

def save(path,data):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(path)

def main():
    contracts=json.loads((DEST/'kalshi_nfl_contract_audit_latest.json').read_text())['contracts']
    series_receipt=get(BASE+'/series/KXNFLGAME')
    series=series_receipt.get('data',{}).get('series',{})
    events=sorted(set(c['event_ticker'] for c in contracts))
    with ThreadPoolExecutor(max_workers=4) as pool:
        fees={e:(changes,complete,receipts) for e,changes,complete,receipts in pool.map(fee_changes,events)}
        books=list(pool.map(lambda c:get(BASE+'/markets/'+urllib.parse.quote(c['ticker'],safe='')+'/orderbook?depth=100'),contracts))
    rows=[]
    for contract,receipt in zip(contracts,books):
        event=contract['event_ticker'];changes,complete,receipts=fees[event]
        rows.append(dict(ticker=contract['ticker'],captured_at_utc=receipt['captured_at_utc'],book_status=receipt['status'],book=book_summary(receipt.get('data',{})),fees=fee_summary(series,changes,event,complete),approved_pick=False))
    poly=json.loads((DEST/'polymarket_nfl_contract_audit_latest.json').read_text())
    tokens=[token for contract in poly['contracts'] for token in contract['token_ids']]
    urls=['https://clob.polymarket.com/'+endpoint+'?token_id='+token for token in tokens for endpoint in ('book','fee-rate')]
    with ThreadPoolExecutor(max_workers=4) as pool: probes=list(pool.map(get,urls))
    poly_rows=[]
    for i,token in enumerate(tokens):
        book,fee=probes[i*2:i*2+2]
        data=book.get('data',{})
        valid_identity=str(data.get('asset_id',''))==token
        poly_rows.append(dict(token_id=token,book_captured=book['status']=='CAPTURED' and valid_identity,fee_parameter_captured=fee['status']=='CAPTURED' and isinstance(fee.get('data',{}).get('base_fee'),(int,float)),base_fee_parameter=fee.get('data',{}).get('base_fee'),execution_verified=False))
    output=dict(schema='zenith.prediction.execution_evidence.v1',captured_at_utc=now(),kalshi=rows,kalshi_source_receipts=dict(series=series_receipt,events=[r for _,_,rs in fees.values() for r in rs],books=books),polymarket_probes=probes,polymarket_tokens=poly_rows,approved_picks=0,execution_enabled=False)
    save(DEST/'execution_evidence_latest.json',output)
    save(DEST/('execution_evidence_'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json'),output)
    public_path=ROOT/'commercial_web/public/prediction_market_nfl_evidence.json'
    public=json.loads(public_path.read_text());k=public['providers']['KALSHI']
    k['execution_evidence']=dict(captured_at_utc=output['captured_at_utc'],books_observed=sum(r['book_status']=='CAPTURED' for r in rows),usable_spreads=sum(r['book']['usable_observed_spread'] for r in rows),fee_metadata_complete=sum(r['fees']['metadata_complete'] for r in rows),execution_fees_verified=False)
    byid={r['ticker']:r for r in rows}
    for market in k['markets']:
        row=byid.get(market['id'])
        if row:market['book_evidence']=dict(captured_at_utc=row['captured_at_utc'],**row['book'])
    public['providers']['POLYMARKET']['execution_evidence']=dict(captured_at_utc=output['captured_at_utc'],tokens_requested=len(tokens),books_observed=sum(r['book_captured'] for r in poly_rows),fee_parameters_captured=sum(r['fee_parameter_captured'] for r in poly_rows),http_403_count=sum(r.get('http_status')==403 for r in probes),execution_fees_verified=False)
    save(public_path,public)
    print(json.dumps(k['execution_evidence']))
if __name__=='__main__':main()
