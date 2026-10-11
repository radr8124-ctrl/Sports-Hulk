import copy
import unittest
from datetime import datetime,timezone
import scan_nfl_cross_market as scanner

NOW=datetime(2026,10,11,19,tzinfo=timezone.utc)
class CoverageTests(unittest.TestCase):
 def fixtures(self):
  games=[dict(event_id='future-without-model',sport='NFL',start_time='2026-10-18T17:00:00Z',home_abbr='LAR',away_abbr='BUF')]
  aliases={'LAR':['Los Angeles Rams'],'BUF':['Buffalo Bills']}
  kalshi=[dict(ticker='k-rams',espn_event_id='future-without-model',yes_team_abbr='LA',rules_sha256='k'),
          dict(ticker='k-bills',espn_event_id='future-without-model',yes_team_abbr='BUF',rules_sha256='k')]
  poly=[dict(id='p',espn_event_id='future-without-model',kickoff='2026-10-18T17:00:00Z',
             outcome_teams=['Los Angeles Rams','Buffalo Bills'],token_ids=['p-rams','p-bills'],rules_sha256='p')]
  validation=dict(kalshi=[dict(id=c['ticker'],terms_reviewed=True,live_open=True) for c in kalshi],
                  polymarket=[dict(id='p',identity_checked=True,terms_reviewed=True,live_open=True)])
  execution=dict(kalshi=[dict(ticker=c['ticker'],book_status='CAPTURED',captured_at_utc=NOW.isoformat(),
                   book=dict(yes_ask=.5,ask_contracts=150,usable_observed_spread=True)) for c in kalshi],
   polymarket_probes=[dict(source_url='https://clob.polymarket.com/book?token_id='+t,status='CAPTURED',
     captured_at_utc=NOW.isoformat(),data=dict(asset_id=t,asks=[dict(price='.9',size='1000'),dict(price='.4',size='150')])) for t in ['p-rams','p-bills']])
  return [execution,kalshi,poly,validation,games,aliases,NOW]
 def collect(self,args):
  self.assertTrue(hasattr(scanner,'collect_scan_quotes'),'Scanner must collect all matched games independently of model forecasts')
  return scanner.collect_scan_quotes(*args)
 def test_future_game_without_any_model_forecast_is_scanned(self):
  result=self.collect(self.fixtures())
  self.assertEqual(len(result['rows']),4)
  self.assertEqual({r['event_id'] for r in result['rows']},{'future-without-model'})
  self.assertEqual({r['team'] for r in result['rows']},{'LAR','BUF'})
  self.assertEqual(result['rows'][-1]['observed_ask_depth'],150)
 def test_kickoff_mismatch_blocks_poly(self):
  args=self.fixtures();args[2][0]['kickoff']='2026-10-18T18:00:00Z'
  self.assertEqual(len(self.collect(args)['rows']),2)
 def test_wrong_outcome_team_blocks_poly(self):
  args=self.fixtures();args[5]['DEN']=['Denver Broncos'];args[2][0]['outcome_teams'][0]='Denver Broncos'
  self.assertEqual(len(self.collect(args)['rows']),2)
 def test_started_game_not_scanned(self):
  args=self.fixtures();args[4][0]['start_time']='2026-10-11T18:00:00Z'
  self.assertEqual(len(self.collect(args)['rows']),0)
 def test_closed_or_unreviewed_contract_not_scanned(self):
  for field in ['live_open','terms_reviewed']:
   args=self.fixtures();args[3]['polymarket'][0][field]=False
   self.assertEqual(len(self.collect(args)['rows']),2)
 def test_stale_or_crossed_book_not_scanned(self):
  args=self.fixtures();args[0]['kalshi'][0]['book']['usable_observed_spread']=False
  self.assertEqual(len(self.collect(args)['rows']),3)
  args=self.fixtures();args[0]['kalshi'][0]['captured_at_utc']='2026-10-11T18:44:59Z'
  self.assertEqual(len(self.collect(args)['rows']),3)
 def test_wrong_token_receipt_not_scanned(self):
  args=self.fixtures();args[0]['polymarket_probes'][0]['data']['asset_id']='wrong'
  self.assertEqual(len(self.collect(args)['rows']),3)
 def test_conflicting_schedule_identity_rejected(self):
  args=self.fixtures();args[4].append(dict(args[4][0],home_abbr='DEN'))
  self.assertEqual(len(self.collect(args)['rows']),0)
if __name__=='__main__':unittest.main()
