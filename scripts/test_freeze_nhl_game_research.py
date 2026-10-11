import importlib.util,pathlib,unittest
p=pathlib.Path('/home/ubuntu/sports-hulk/scripts/freeze_nhl_game_research.py')
s=importlib.util.spec_from_file_location('nhl',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class NHLLedger(unittest.TestCase):
 def test_finals_are_not_backfilled_as_predictions(self):
  r=m.summarize({'games':[{'event_id':1,'final':True,'home_score':3,'away_score':1}]})[0]
  self.assertEqual(r['state'],'FINAL_RESULT_ONLY');self.assertIsNone(r['frozen_pregame_projection']);self.assertFalse(r['approved_pick'])
 def test_upcoming_never_has_score(self):
  r=m.summarize({'games':[{'event_id':2,'final':False,'live':False,'home_score':0}]})[0]
  self.assertEqual(r['state'],'UPCOMING_RESEARCH_ONLY');self.assertIsNone(r['score'])
 def test_live_not_mistaken_for_pregame(self):
  self.assertEqual(m.summarize({'games':[{'live':True,'final':False}]})[0]['state'],'LIVE_NO_PREGAME_PICK')
if __name__=='__main__':unittest.main()
