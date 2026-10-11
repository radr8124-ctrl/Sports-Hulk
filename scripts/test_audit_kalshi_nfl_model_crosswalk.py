import importlib.util,pathlib,unittest
p=pathlib.Path('/home/ubuntu/sports-hulk/scripts/audit_kalshi_nfl_model_crosswalk.py')
s=importlib.util.spec_from_file_location('crosswalk',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class CrosswalkTests(unittest.TestCase):
 def setUp(self):
  self.contract=[{'ticker':'t','espn_event_id':'401','yes_team_abbr':'JAC'}]
  self.forecast=[{'event_id':'401','home':'JAX','away':'PHI','forecast_home_pct':75,'forecast_away_pct':25,'model_uses_market_input':True,'model_beats_market_out_of_sample_proven':False,'actual_sportsbook_executable_current_price_verified':False}]
 def test_alias_is_explicit(self):
  r=m.join(self.contract,self.forecast)[0];self.assertEqual(r['historical_frozen_model_win_pct'],75);self.assertIsNone(r['independent_win_probability'])
 def test_no_independent_edge(self):
  r=m.join(self.contract,self.forecast)[0];self.assertEqual(r['decision'],'PASS');self.assertIn('FORECAST_INCLUDES_MARKET_INPUT',r['reasons'])
 def test_no_match_does_not_make_up_probability(self):
  self.forecast[0]['event_id']='notmatching';r=m.join(self.contract,self.forecast)[0];self.assertIsNone(r['historical_frozen_model_win_pct'])
if __name__=='__main__':unittest.main()
