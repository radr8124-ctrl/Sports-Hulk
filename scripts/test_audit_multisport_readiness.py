import importlib.util,pathlib,unittest
p=pathlib.Path('/home/ubuntu/sports-hulk/scripts/audit_multisport_readiness.py')
s=importlib.util.spec_from_file_location('multi',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Inventory(unittest.TestCase):
 def test_nhl_games_do_not_promote_edge(self):
  r=m.inspect('NHL',{'generated_at':'2026-10-11T14:00:00Z','status':'READY','games':[{'id':1}]})
  self.assertEqual(r['scoreboard_games'],1);self.assertFalse(r['verified_model_edge']);self.assertEqual(r['approved_prediction_market_picks'],0)
 def test_mlb_uses_three_buckets(self):
  r=m.inspect('MLB',{'today_games':[1],'recent_games':[2],'next_games':[3]})
  self.assertEqual(r['scoreboard_games'],3)
if __name__=='__main__':unittest.main()
