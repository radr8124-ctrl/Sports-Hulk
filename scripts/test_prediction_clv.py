import unittest
from datetime import datetime,timezone
from prediction_clv import summarize_clv

NOW=datetime(2026,10,11,20,tzinfo=timezone.utc)
def row(identity='one',quantity=100,price=.4,close=.5):
 return dict(trade_id=identity,mode='PAPER',quantity=quantity,fill_price=price,entry_fee=1,fees_verified=True,
             provider='KALSHI',contract_or_token_id='game-team',entry_at_utc='2026-10-11T18:00:00Z',
             kickoff_utc='2026-10-11T20:00:00Z',closing_quote=dict(provider='KALSHI',contract_or_token_id='game-team',
             ask=close,ask_depth=1000,captured_at_utc='2026-10-11T19:55:00Z',source_verified=True,
             source_sha256='a'*64,fees_verified=True,fee_for_quantity=2))
class ClvTests(unittest.TestCase):
 def summarize(self,rows):return summarize_clv(rows,now=NOW)
 def test_raw_and_fee_adjusted_clv(self):
  r=self.summarize([row()])
  self.assertAlmostEqual(r['quantity_weighted_raw_clv'],.1)
  self.assertAlmostEqual(r['quantity_weighted_cost_clv'],.11)
  self.assertFalse(r['validated_profitable_edge'])
 def test_quantity_weighting_includes_losses(self):
  r=self.summarize([row('a',100,.4,.5),row('b',300,.6,.5)])
  self.assertAlmostEqual(r['quantity_weighted_raw_clv'],-.05)
  self.assertEqual(r['positive_entry_fraction'],.5)
 def test_empty_or_missing_close_is_unknown(self):
  self.assertIsNone(self.summarize([])['quantity_weighted_raw_clv'])
  r=row();del r['closing_quote']
  self.assertEqual(self.summarize([r])['exclusion_counts'],{'CLOSING_QUOTE_MISSING':1})
 def test_after_kickoff_old_future_and_before_entry_rejected(self):
  for at in ['2026-10-11T20:00:00Z','2026-10-11T19:44:00Z','2026-10-11T17:55:00Z']:
   r=row();r['closing_quote']['captured_at_utc']=at
   self.assertEqual(self.summarize([r])['compared_entries'],0)
  self.assertEqual(summarize_clv([row()],now=datetime(2026,10,11,19,tzinfo=timezone.utc))['compared_entries'],0)
 def test_different_contract_or_provider_rejected(self):
  for field,value in [('contract_or_token_id','other'),('provider','POLYMARKET')]:
   r=row();r['closing_quote'][field]=value
   self.assertEqual(self.summarize([r])['compared_entries'],0)
 def test_depth_source_and_invalid_price_rejected(self):
  for field,value in [('ask_depth',99),('source_sha256','bad'),('source_verified',False),('ask','NaN')]:
   r=row();r['closing_quote'][field]=value
   self.assertEqual(self.summarize([r])['compared_entries'],0)
 def test_unknown_cost_keeps_raw_diagnostic_only(self):
  r=row();r['fees_verified']=False
  out=self.summarize([r]);self.assertEqual(out['compared_entries'],1)
  self.assertIsNone(out['quantity_weighted_cost_clv'])
 def test_duplicate_and_mixed_modes_rejected(self):
  with self.assertRaises(ValueError):self.summarize([row(),row()])
  r=row();r['mode']='ACTUAL'
  with self.assertRaises(ValueError):self.summarize([r])
if __name__=='__main__':unittest.main()
