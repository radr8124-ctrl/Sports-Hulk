import unittest
from audit_prediction_roi import summarize
def trade(identity,price,payout,fee=0,day=1):
 return dict(trade_id=identity,mode='PAPER',settled=True,fees_verified=True,settlement_verified=True,quantity=100,fill_price=price,entry_fee=fee,exit_fee=0,settlement_per_contract=payout,settled_at_utc=f'2026-10-{day:02d}T20:00:00Z')
class RoiTests(unittest.TestCase):
 def test_high_win_rate_can_lose_money(self):
  rows=[trade(str(i),.9,1 if i<8 else 0,day=i+1) for i in range(10)]
  r=summarize(rows,'PAPER')
  self.assertEqual(r['net_profit'],-100)
  self.assertAlmostEqual(r['net_roi'],-100/900)
  self.assertEqual(r['maximum_drawdown'],180)
 def test_fees_and_half_settlement(self):
  r=summarize([trade('a',.5,.5,fee=.75)],'PAPER')
  self.assertEqual(r['net_profit'],-.75)
  self.assertAlmostEqual(r['net_roi'],-.75/50.75)
 def test_empty_roi_is_unknown_and_bad_costs_block(self):
  self.assertIsNone(summarize([],'PAPER')['net_roi'])
  r=trade('a',.5,1);r['fees_verified']=False
  self.assertIsNone(summarize([r],'PAPER')['net_profit'])
 def test_duplicates_mixed_modes_and_invalid_prices_rejected(self):
  row=trade('a',.5,1)
  with self.assertRaises(ValueError):summarize([row,row],'PAPER')
  with self.assertRaises(ValueError):summarize([row],'ACTUAL')
  row['fill_price']=float('nan')
  with self.assertRaises(ValueError):summarize([row],'PAPER')
if __name__=='__main__':unittest.main()
