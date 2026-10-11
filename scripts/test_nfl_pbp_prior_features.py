import unittest
import pandas as pd
from restore_nfl_pbp_research_source import prior_features
class PriorFeaturesTests(unittest.TestCase):
 def test_same_week_future_and_other_seasons_excluded(self):
  rows=[dict(season=2024,team='A',week=w,game_id=str(i),epa=e) for i,(w,e) in enumerate([(1,1),(2,3),(2,99),(3,900)])]
  rows.append(dict(season=2025,team='A',week=1,game_id='new',epa=8))
  result=prior_features(pd.DataFrame(rows)).set_index('game_id')
  self.assertEqual(result.loc['1','prior5_off_epa_per_play'],1)
  self.assertEqual(result.loc['2','prior5_off_epa_per_play'],1)
  self.assertTrue(pd.isna(result.loc['new','prior5_off_epa_per_play']))
  self.assertEqual(result.loc['3','prior_max_week'],2)
if __name__=='__main__':unittest.main()
