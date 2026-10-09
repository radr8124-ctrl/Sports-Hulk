"""Zenith MLB postseason source context: maintain betting gates, widen data only."""
import unittest
from datetime import date,timedelta
from pathlib import Path
import pandas as pd
from mlb_live import build_mlb_fusion_v2 as fusion
from mlb_live.decision import build_mlb_decision_brain_v2 as decisions

class TestMLBPostseasonContextWindow(unittest.TestCase):
 def test_official_postseason_schedule_window_gives_twenty_eight_days(self):
  x=pd.DataFrame({'gameType':['R','D','L'],'officialDate':['2026-09-20','2026-10-11','2026-10-16']})
  self.assertEqual(fusion.recent_context_days(x,date(2026,10,9)),28)

 def test_regular_season_only_still_fourteen_days(self):
  x=pd.DataFrame({'gameType':['R','R'],'officialDate':['2026-07-20','2026-07-27']})
  self.assertEqual(fusion.recent_context_days(x,date(2026,7,28)),14)

 def test_old_postseason_outside_active_window_does_not_expand_regular_season(self):
  x=pd.DataFrame({'gameType':['L','R'],'officialDate':['2025-10-11','2026-04-08']})
  self.assertEqual(fusion.recent_context_days(x,date(2026,4,8)),14)

 def test_missing_incomplete_or_ambiguous_official_schedule_fails_unchanged(self):
  self.assertEqual(fusion.recent_context_days(None,date(2026,10,9)),14)
  self.assertEqual(fusion.recent_context_days(pd.DataFrame(),date(2026,10,9)),14)
  self.assertEqual(fusion.recent_context_days(pd.DataFrame({'gameType':['D']}),date(2026,10,9)),14)
  self.assertEqual(fusion.recent_context_days(pd.DataFrame({'gameType':['R'],'officialDate':['broken']}),date(2026,10,9)),14)

 def test_official_schedule_active_on_todays_real_MLB_fixtures(self):
  schedule=pd.read_csv(fusion.SCHEDULE)
  self.assertIn('gameType',schedule)
  self.assertIn('officialDate',schedule)
  self.assertEqual(fusion.recent_context_days(schedule,date(2026,10,9)),28)
  self.assertEqual(fusion.RECENT_LOOKBACK_DAYS,28)
  self.assertEqual(fusion.RECENT_START,fusion.TODAY-timedelta(days=28))

 def test_batter_and_pitcher_minimums_remain_unmodified(self):
  source=Path('mlb_live/decision/build_mlb_decision_brain_v2.py').read_text()
  self.assertIn('min_recent = 2 if group == "PITCHING" else 4',source)
  self.assertIn('if not enough_recent:',source)
  self.assertIn('decision = "INSUFFICIENT_RECENT_CONTEXT"',source)
  self.assertIn('if recent_games < 4:',source)
  self.assertIn('if recent_games < 2:',source)

 def test_existing_mlb_live_market_and_wager_model_not_modified(self):
  self.assertFalse(hasattr(fusion,'approve_bets'))
  source=Path('mlb_live/build_mlb_fusion_v2.py').read_text()
  self.assertIn('recent_context_not_a_validated_model_betting_edge',source)
  self.assertIn('recent_context_may_include_prior_regular_season_games',source)

 def test_pure_recent_gate_with_three_batter_games_is_hold(self):
  rows=pd.DataFrame([dict(group='HITTING',recent_games=3,season_games=150,market_subtype='PLAYER_TOTAL_HITS',
   line=1.5,side='OVER',recent_avg=2,season_avg=1.1,sportsbook_count=4,
   median_price_american=-110,event_id='mock-01',player='Synthetic Name',player_id=4321)])
  from tempfile import TemporaryDirectory
  with TemporaryDirectory(prefix='zenith_mlb_postseason_qa_') as d:
   path=Path(d)/'mock_fusion.csv'
   rows.to_csv(path,index=False)
   judged=decisions.player_decisions(path,'PROP')
   self.assertEqual(judged.iloc[0]['decision'],'INSUFFICIENT_RECENT_CONTEXT')

if __name__=='__main__':unittest.main()
