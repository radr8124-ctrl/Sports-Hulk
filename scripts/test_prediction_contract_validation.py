import unittest
from decimal import Decimal
from validate_prediction_contracts import poly_fee, kalshi_rounding, poly_terms
class ValidationTests(unittest.TestCase):
 def test_documented_fee_table_and_market_override(self):
  self.assertEqual(poly_fee(100,'.5',{'rate':'.05','exponent':1,'takerOnly':True}),Decimal('1.25000'))
  self.assertEqual(poly_fee(100,'.5',{'rate':'.03','exponent':1,'takerOnly':True}),Decimal('.75000'))
  self.assertEqual(poly_fee(100,'.5',{'rate':'.03','exponent':1,'takerOnly':True},maker=True),Decimal('0'))
  for rate in ['NaN','-.03','2']:
   with self.assertRaises(ValueError):poly_fee(100,'.5',{'rate':rate,'exponent':1,'takerOnly':True})
  with self.assertRaises(ValueError):poly_fee(100,'.5',{'rate':'.03','exponent':2,'takerOnly':True})
 def test_official_rounding_example(self):
  result=kalshi_rounding('-.055','.00363825','.01')
  self.assertEqual(result,dict(trade_fee=Decimal('.003639'),rounding_fee=Decimal('.001361'),aligned_change=Decimal('-.06')))
 def test_settlement_template_requires_all_clauses(self):
  rules='This market will resolve to "Eagles" if Eagles win the game. This market will resolve to "Jaguars" if Jaguars win the game. Overtime is included if played. If the game ends in a tie, this market will resolve 50-50. If the game is postponed, this market will remain open until the game has been completed. If the game is canceled entirely, with no make-up game, this market will resolve 50-50.'
  self.assertTrue(poly_terms(rules,['Eagles','Jaguars'])['review_passed'])
  self.assertFalse(poly_terms(rules.replace('50-50','winner takes all'),['Eagles','Jaguars'])['review_passed'])
  self.assertFalse(poly_terms(rules,['Bears','Jaguars'])['review_passed'])
if __name__=='__main__':unittest.main()
