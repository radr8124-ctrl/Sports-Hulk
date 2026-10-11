import unittest
from audit_nfl_selective_value import profit_multiple,select,summarize
class ValueTests(unittest.TestCase):
 def fixture(self,p=.6,label=1):
  home,away=100/110,1.
  market=(1/(1+home))/(1/(1+home)+1/(1+away))
  return dict(game_id='fixture',season=2024,week=1,candidate=p,label=label,market=market),dict(season=2024,week=1,home_score=21 if label else 7,away_score=7 if label else 21,home_moneyline=-110,away_moneyline=100)
 def test_actual_odds_and_stress_cost(self):
  row,source=self.fixture();r=select(row,source,.03,.02)
  self.assertTrue(r['selected']);self.assertEqual(r['side'],'home')
  self.assertAlmostEqual(r['expected_net_return'],.6*(100/110)-.4-.02)
  self.assertAlmostEqual(r['stress_net_profit_units'],100/110-.02)
  self.assertEqual(profit_multiple(180),1.8)
 def test_select_losing_away_side_once(self):
  row,source=self.fixture(.4,1);r=select(row,source,.03,.02)
  self.assertEqual(r['side'],'away');self.assertTrue(r['selected'])
  self.assertEqual(r['stress_net_profit_units'],-1.02)
 def test_cost_threshold_and_no_bets_roi(self):
  row,source=self.fixture(.54);r=select(row,source,.03,.02)
  self.assertFalse(r['selected']);summary=summarize([r],100,1)
  self.assertIsNone(summary['stress_net_roi']);self.assertIsNone(summary['week_block_stress_roi_95ci'])
 def test_bad_prices_identity_and_ties_rejected(self):
  with self.assertRaises(ValueError):profit_multiple(float('nan'))
  for field,value in [('week',2),('home_score',7),('home_moneyline',-150)]:
   row,source=self.fixture();source[field]=value
   with self.assertRaises(ValueError):select(row,source,.03,.02)
if __name__=='__main__':unittest.main()
