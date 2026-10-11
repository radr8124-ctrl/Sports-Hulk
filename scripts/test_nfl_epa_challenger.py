import unittest
from benchmark_nfl_epa_challenger import epa_vector
class EPATests(unittest.TestCase):
 def setUp(self):
  self.row=dict(game_id='g',season=2024,week=3,home_team='LA',away_team='SEA',features=[1,.3,0,0,0,0,.2,1,0])
  self.home=dict(season=2024,week=3,prior_max_week=2,def_prior_max_week=2,prior5_off_epa_per_play=.1,prior5_def_epa_allowed_per_play=-.1)
  self.away=dict(self.home,prior5_off_epa_per_play=0,prior5_def_epa_allowed_per_play=.1)
  self.index={('g','LAR'):self.home,('g','SEA'):self.away}
 def test_alias_sign_and_feature_order(self):
  self.assertEqual(epa_vector(self.row,self.index),[1,.3,.5,1,.2,0])
 def test_same_week_wrong_season_and_missing_identity_rejected(self):
  for field,value in [('prior_max_week',3),('def_prior_max_week',4),('season',2025),('week',4)]:
   with self.subTest(field=field):
    index=dict(self.index);index[('g','LAR')]=dict(self.home,**{field:value})
    with self.assertRaises(ValueError):epa_vector(self.row,index)
  with self.assertRaises(ValueError):epa_vector(self.row,{})
if __name__=='__main__':unittest.main()
