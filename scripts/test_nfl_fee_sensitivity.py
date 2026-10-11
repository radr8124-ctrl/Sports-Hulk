import unittest
from decimal import Decimal
from audit_nfl_fee_sensitivity import kalshi_fee,modeled_roi
from validate_prediction_contracts import poly_fee
class FeeTests(unittest.TestCase):
 def test_official_kalshi_examples_and_precisions(self):
  self.assertEqual(kalshi_fee(100,'.5'),Decimal('1.75'))
  self.assertEqual(kalshi_fee(1,'.5'),Decimal('.02'))
  self.assertEqual(kalshi_fee(1,'.5',precision='.0001'),Decimal('.0175'))
  self.assertEqual(kalshi_fee(100,'.7'),Decimal('1.47'))
 def test_market_specific_poly_rate(self):
  schedule=dict(rate=.03,exponent=1,takerOnly=True)
  self.assertEqual(poly_fee(100,'.5',schedule),Decimal('.75000'))
  schedule['rate']=.05
  self.assertEqual(poly_fee(100,'.5',schedule),Decimal('1.25000'))
 def test_fee_can_remove_positive_gap_and_roi_uses_total_cost(self):
  self.assertLess(modeled_roi('.712','.7',kalshi_fee(100,'.7')),0)
  self.assertAlmostEqual(modeled_roi('.6','.5',1),9/51)
  self.assertLess(modeled_roi('.6','.5',1,slippage='.01'),modeled_roi('.6','.5',1))
 def test_tie_adjustment_and_unknown_inputs(self):
  self.assertLess(modeled_roi('.7','.5',1,tie_probability='.01'),modeled_roi('.7','.5',1))
  with self.assertRaises(ValueError):modeled_roi('.7','.5',-1)
if __name__=='__main__':unittest.main()
