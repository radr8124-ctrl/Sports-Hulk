import unittest
from datetime import datetime,timezone
from capture_nfl_narrow_forward_quotes import eligible,model_probability,best_ask
class NarrowTests(unittest.TestCase):
 def test_only_observed_after_forecast_before_kickoff_and_fresh(self):
  f={'source_first_real_future_prediction_frozen_at_utc':'2026-10-11T16:00:00Z','official_first_pitch_utc':'2026-10-11T20:00:00Z'}
  now=datetime(2026,10,11,17,tzinfo=timezone.utc)
  self.assertTrue(eligible(f,'2026-10-11T16:59:00Z',now))
  for t in ['2026-10-11T15:59:00Z','2026-10-11T16:40:00Z','2026-10-11T17:01:00Z','2026-10-11T16:59:00']:
   self.assertFalse(eligible(f,t,now))
  self.assertFalse(eligible(f,'2026-10-11T20:00:00Z',datetime(2026,10,11,20,tzinfo=timezone.utc)))
 def test_rams_alias_and_side_probability_preserve_model(self):
  f={'home_team':'LA','away_team':'BUF','nine_feature_score_form_home_win_prob':.6}
  self.assertEqual(model_probability(f,'LAR'),.6)
  self.assertAlmostEqual(model_probability(f,'BUF'),.4)
  with self.assertRaises(ValueError):model_probability(f,'LAC')
 def test_unsorted_book_minimum_price_and_aggregate_depth(self):
  p,q=best_ask({'asks':[{'price':'.99','size':'100'},{'price':'.53','size':'7'},{'price':'.53','size':'3'},{'price':'.50','size':'0'},{'price':'nan','size':'5'}]})
  self.assertEqual((p,q),(.53,10))
  self.assertEqual(best_ask({}), (None,None))
if __name__=='__main__':unittest.main()
