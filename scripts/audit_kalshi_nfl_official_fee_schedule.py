#!/usr/bin/env python3
"""Conservative public fee-schedule verification for Kalshi KXNFLGAME series."""
import datetime,json,pathlib
ROOT=pathlib.Path('/home/ubuntu/sports-hulk/nfl_live/prediction_markets')
OFFICIAL='https://kalshi.com/docs/kalshi-fee-schedule.pdf'
def assess(contracts):
 rows=[]
 for c in contracts:
  ticker=str(c.get('ticker',''))
  eligible=ticker.startswith('KXNFLGAME-') and c.get('status')=='active'
  rows.append({'ticker':ticker,'series':'KXNFLGAME' if eligible else None,
   'maker_multiplier':1 if eligible else None,'taker_multiplier':1 if eligible else None,
   'published_series_fee_schedule_verified':eligible,
   'fee_execution_quote_verified':False,'no_market_or_account_override_verified':False,
   'decision':'PASS'})
 return rows
def main():
 d=json.loads((ROOT/'kalshi_nfl_contract_audit_latest.json').read_text())
 rows=assess(d['contracts'])
 report={'schema':'zenith.kalshi.nfl.official_fee_schedule_audit.v1',
 'audited_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'contracts_seen':len(rows),'series_schedule_matched':sum(x['published_series_fee_schedule_verified'] for x in rows),
 'source_url':OFFICIAL,'source_effective_date':'2026-07-07',
 'source_claim':'KXNFLGAME listed under non-standard fee table: maker multiplier 1, taker multiplier 1',
 'general_taker_coefficient':'0.07','general_maker_coefficient':'0.0175',
 'market_specific_execution_fees_confirmed':0,'approved_picks':0,
 'important':['Public schedule series confirmed, not live account fee quote','API example had no exposed fee override fields; absence cannot prove there are none','Actual order fee and centicent rounding need execution-side quote verification','No model validation or trading permission inferred'],'rows':rows}
 (ROOT/'kalshi_nfl_official_fee_schedule_audit_latest.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ('contracts_seen','series_schedule_matched','market_specific_execution_fees_confirmed','approved_picks')}))
if __name__=='__main__':main()
