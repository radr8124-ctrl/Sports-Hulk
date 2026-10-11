import importlib.util,pathlib,unittest
p=pathlib.Path('/home/ubuntu/sports-hulk/scripts/audit_nfl_prospective_readiness.py')
spec=importlib.util.spec_from_file_location('a',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Prospective(unittest.TestCase):
 def test_zero_finals_blocked(self):
  d=m.assess({'source_pairs_scored':0,'independent_game_floor':30},{},{})
  self.assertEqual(d['remaining_to_floor'],30);self.assertFalse(d['kalshi_model_eligible'])
 def test_sample_floor_is_not_edge(self):
  d=m.assess({'source_pairs_scored':40,'independent_game_floor':30,'market_advantage_statistically_proven':False},{'independent_edge_proven':True,'official_betting_allowed':True},{})
  self.assertFalse(d['kalshi_model_eligible'])
 def test_no_implicit_pick_even_with_conditions(self):
  d=m.assess({'source_pairs_scored':40,'independent_game_floor':30,'market_advantage_statistically_proven':True},{'independent_edge_proven':True,'official_betting_allowed':True},{})
  self.assertFalse(d['pick_approval'])
if __name__=='__main__':unittest.main()
