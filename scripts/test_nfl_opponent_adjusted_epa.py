import unittest
from copy import deepcopy
from benchmark_nfl_opponent_adjusted_epa import ratings
class OpponentTests(unittest.TestCase):
 def setUp(self):
  self.games=[dict(season=2024,week=1,game_id='1',team='A',opponent='B',epa=.2,plays=60),dict(season=2024,week=1,game_id='1',team='B',opponent='A',epa=-.1,plays=60),dict(season=2024,week=2,game_id='2',team='A',opponent='C',epa=.1,plays=60),dict(season=2024,week=2,game_id='2',team='C',opponent='A',epa=-.1,plays=60)]
 def test_current_future_and_other_seasons_cannot_change_ratings(self):
  base=ratings(self.games,2024,3)
  changed=self.games+[dict(season=2024,week=3,game_id='now',team='A',opponent='B',epa=99,plays=60),dict(season=2025,week=1,game_id='other',team='A',opponent='B',epa=99,plays=60)]
  self.assertEqual(ratings(changed,2024,3),base)
  self.assertGreater(base['A']['offense'],base['B']['offense'])
 def test_empty_history_is_empty_and_duplicate_observation_rejected(self):
  self.assertEqual(ratings(self.games,2024,1),{})
  with self.assertRaises(ValueError):ratings(self.games+[deepcopy(self.games[0])],2024,3)
if __name__=='__main__':unittest.main()
