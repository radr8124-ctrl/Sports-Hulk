"""Regression for pandas-Series truth-value failure in fantasy accountability."""
from pathlib import Path
import unittest
import pandas as pd
from intelligence_warehouse.fantasy_accountability import build_fantasy_v2 as f

class TestFantasyStatSeriesLookup(unittest.TestCase):
 def setUp(self):
  self.row=pd.Series({'player_display_name':'Demo Athlete','team':'DET','fantasy_points_ppr':12.5,'position':'WR'})

 def test_direct_team_key_returns_series_not_boolean(self):
  index={(5,'demoathlete','DET'):self.row,(5,'demoathlete',''):pd.Series({'fantasy_points_ppr':1})}
  found=f.source_stat_row(index,5,'demoathlete','DET')
  self.assertIs(found,self.row)
  self.assertAlmostEqual(float(found['fantasy_points_ppr']),12.5)

 def test_empty_team_fallback_returns_series(self):
  index={(5,'demoathlete',''):self.row}
  self.assertIs(f.source_stat_row(index,5,'demoathlete','NYG'),self.row)

 def test_absent_key_returns_none(self):
  self.assertIsNone(f.source_stat_row({},5,'demoathlete','DET'))

 def test_team_series_with_zero_numeric_values_is_not_falsified(self):
  zero=pd.Series({'fantasy_points_ppr':0.,'position':'QB'})
  index={(5,'demoathlete','DET'):zero,(5,'demoathlete',''):self.row}
  self.assertIs(f.source_stat_row(index,5,'demoathlete','DET'),zero)

 def test_no_pandas_series_or_short_circuit_remains_in_settlement(self):
  s=Path('intelligence_warehouse/fantasy_accountability/build_fantasy_v2.py').read_text()
  self.assertNotIn('or mp.get(',s)
  self.assertEqual(s.count('st=source_stat_row('),4)

if __name__=='__main__':unittest.main()
