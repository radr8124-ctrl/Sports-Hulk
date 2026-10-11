import importlib.util
import unittest

class EloTests(unittest.TestCase):
 def module(self):
  self.assertIsNotNone(importlib.util.find_spec('nfl_elo_challenger'),'Separate fixed Elo challenger must exist')
  import nfl_elo_challenger
  return nfl_elo_challenger
 def test_neutral_equal_teams_and_home_advantage(self):
  m=self.module().SportElo()
  self.assertEqual(m.win_prob('A','B',True),.5)
  self.assertGreater(m.win_prob('A','B'),.5)
 def test_winner_update_conserves_rating_sum(self):
  m=self.module().SportElo();m.update('A','B',21,7)
  self.assertGreater(m.r['A'],1500)
  self.assertAlmostEqual(m.r['A']+m.r['B'],3000)
 def test_tie_moves_favorite_toward_half_result(self):
  m=self.module().SportElo();m.r['A']=1600;m.r['B']=1400
  m.update('A','B',14,14,True)
  self.assertLess(m.r['A'],1600)
  self.assertGreater(m.r['B'],1400)
 def test_season_regression(self):
  m=self.module().SportElo();m.r['A']=1600;m.new_season()
  self.assertEqual(m.r['A'],1575)
 def games(self):
  return [dict(game_id='g1',season=2018,gameday='2018-09-01',home_team='A',away_team='B',home_score=35,away_score=0,location='Home'),
          dict(game_id='g2',season=2018,gameday='2018-09-01',home_team='A',away_team='C',home_score=7,away_score=14,location='Home'),
          dict(game_id='g3',season=2019,gameday='2019-09-01',home_team='A',away_team='B',home_score=21,away_score=7,location='Home')]
 def test_same_day_prediction_cannot_use_same_day_results(self):
  run=self.module().replay
  games=self.games();before=run(games)
  games[0]['home_score']=0;games[0]['away_score']=35
  after=run(games)
  self.assertEqual(before['g2'],after['g2'])
  self.assertNotEqual(before['g3'],after['g3'])
 def test_replay_sorts_and_rejects_duplicate_identity(self):
  run=self.module().replay;games=self.games()
  self.assertEqual(run(games),run(list(reversed(games))))
  with self.assertRaises(ValueError):run(games+[games[0]])
 def test_invalid_scores_rejected(self):
  m=self.module().SportElo()
  for value in [float('nan'),-1,True]:
   with self.assertRaises(ValueError):m.update('A','B',value,7)
if __name__=='__main__':unittest.main()
