#!/usr/bin/env python3
"""Read-only Kalshi NFL outcome contracts, using exact previously audited event tickers."""
import datetime,json,pathlib,urllib.request,urllib.parse,hashlib,time
ROOT=pathlib.Path('/home/ubuntu/sports-hulk/nfl_live/prediction_markets')
def get(ticker):
 url='https://external-api.kalshi.com/trade-api/v2/events/'+urllib.parse.quote(ticker,safe='')+'?with_nested_markets=true'
 request=urllib.request.Request(url,headers={'User-Agent':'SportsZenithResearch/1.0'})
 with urllib.request.urlopen(request,timeout=12) as response:return json.load(response)
def extract(candidate,data):
 ev=data.get('event') or {}
 if ev.get('event_ticker')!=candidate['event_ticker']:return [],'EVENT_ID_MISMATCH'
 rows=[]
 for m in ev.get('markets',[]):
  ticker=m.get('ticker','')
  suffix=ticker.rsplit('-',1)[-1]
  if suffix not in [candidate['away_abbr'],candidate['home_abbr']]:continue
  rules=str(m.get('rules_primary') or '')
  secondary=str(m.get('rules_secondary') or '')
  if not (rules.startswith('If ') and 'then the market resolves to Yes' in rules and 'If the game ends in a tie' in secondary):continue
  rows.append({'ticker':ticker,'event_ticker':ev['event_ticker'],'espn_event_id':candidate['espn_event_id'],'yes_team_abbr':suffix,'title':m.get('title'),'status':m.get('status'),'yes_bid_dollars':m.get('yes_bid_dollars'),'yes_ask_dollars':m.get('yes_ask_dollars'),'no_bid_dollars':m.get('no_bid_dollars'),'no_ask_dollars':m.get('no_ask_dollars'),'volume_fp':m.get('volume_fp'),'open_interest_fp':m.get('open_interest_fp'),'rules_primary':rules,'rules_secondary':secondary,'rules_sha256':hashlib.sha256((rules+'\n'+secondary).encode()).hexdigest(),'contract_status':'RULES_CAPTURED_NO_FEES_OR_EXECUTION_VERIFICATION','approved_pick':False})
 return rows,'CAPTURED' if rows else 'CONTRACT_RULES_UNVERIFIED'
def main():
 audit=json.loads((ROOT/'kalshi_nfl_schedule_candidates_latest.json').read_text())
 rows=[];failures=[]
 for match in audit['matches']:
  try:
   extracted,status=extract(match,get(match['event_ticker']))
   rows+=extracted
   if status!='CAPTURED':failures.append({'event':match['event_ticker'],'reason':status})
  except Exception as error:failures.append({'event':match['event_ticker'],'reason':type(error).__name__})
  time.sleep(.12)
 report={'schema':'zenith.kalshi.nfl.contract_audit.v1','captured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'events_requested':len(audit['matches']),'contracts_captured':len(rows),'failure_count':len(failures),'failures':failures,'contracts':rows,'approved_picks':0,'risk_notes':['Outcome and settlement text recorded but independent validation remains pending','Tie and postponement clauses differ from standard moneyline','Quotes are sampled and may change or be unavailable','Fees, order book depth, and independent probabilities unverified']}
 (ROOT/'kalshi_nfl_contract_audit_latest.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'events':report['events_requested'],'contracts':len(rows),'failures':len(failures),'examples':[(r['ticker'],r['yes_bid_dollars'],r['yes_ask_dollars']) for r in rows[:3]]}))
if __name__=='__main__':main()
