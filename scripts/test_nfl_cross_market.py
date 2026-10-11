import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from scan_nfl_cross_market import evaluate

NOW=datetime(2026,10,11,19,tzinfo=timezone.utc)
ZERO=lambda q,p: Decimal(0)
class ScannerTests(unittest.TestCase):
    def legs(self):
        a=dict(event_id='game',team='DEN',provider='KALSHI',observed_ask=.45,
               observed_ask_depth=100,book_captured_at_utc=NOW.isoformat(),
               kickoff_utc=(NOW+timedelta(hours=1)).isoformat(),contract_or_token_id='a')
        return a,dict(a,team='LAC',provider='POLYMARKET',observed_ask=.5,contract_or_token_id='b')
    def test_conditional_math(self):
        r=evaluate(*self.legs(),ZERO,ZERO,NOW,rules_equivalent=True)
        self.assertAlmostEqual(r['conditional_net_profit'],5)
        self.assertAlmostEqual(r['conditional_net_roi'],5/95)
        self.assertAlmostEqual(r['one_cent_worse_fill_profit'],3)
        self.assertFalse(r['approved_pick'])
        self.assertFalse(r['execution_enabled'])
    def test_fees_eliminate_gap(self):
        fee=lambda q,p: Decimal(3)
        r=evaluate(*self.legs(),fee,fee,NOW,rules_equivalent=True)
        self.assertEqual(r['conditional_net_profit'],-1)
        self.assertIn('NO_POSITIVE_NET_GAP',r['blockers'])
    def test_default_settlement_gate(self):
        self.assertIn('SETTLEMENT_RULES_NOT_EQUIVALENT',evaluate(*self.legs(),ZERO,ZERO,NOW)['blockers'])
    def test_stale_and_future_quotes(self):
        for delta in (-901,1):
            a,b=self.legs();a['book_captured_at_utc']=(NOW+timedelta(seconds=delta)).isoformat()
            self.assertIn('STALE_OR_FUTURE_QUOTE',evaluate(a,b,ZERO,ZERO,NOW)['blockers'])
    def test_depth_game_started_and_skew(self):
        a,b=self.legs();a['observed_ask_depth']=99
        a['kickoff_utc']=NOW.isoformat()
        b['book_captured_at_utc']=(NOW-timedelta(seconds=31)).isoformat()
        codes=evaluate(a,b,ZERO,ZERO,NOW)['blockers']
        for code in ['INSUFFICIENT_TOP_LEVEL_DEPTH','GAME_STARTED','QUOTE_TIME_SKEW','KICKOFF_MISMATCH']:
            self.assertIn(code,codes)
    def test_unsupported_fee_blocks(self):
        def unavailable(q,p):raise ValueError('missing')
        r=evaluate(*self.legs(),unavailable,ZERO,NOW)
        self.assertIsNone(r['conditional_net_profit'])
        self.assertIn('FEE_EVIDENCE_UNAVAILABLE',r['blockers'])
    def test_invalid_identity_and_price(self):
        a,b=self.legs();b['team']=a['team']
        with self.assertRaises(ValueError):evaluate(a,b,ZERO,ZERO,NOW)
        a,b=self.legs();a['observed_ask']='NaN'
        with self.assertRaises(ValueError):evaluate(a,b,ZERO,ZERO,NOW)
    def test_naive_time_rejected(self):
        a,b=self.legs();a['book_captured_at_utc']='2026-10-11T19:00:00'
        self.assertIn('INVALID_QUOTE_EVIDENCE',evaluate(a,b,ZERO,ZERO,NOW)['blockers'])
if __name__=='__main__':unittest.main()
