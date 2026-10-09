"""MLB public sprint and bat-tracking season measurements are not exit velocity."""
from __future__ import annotations
import io
import unittest
import pandas as pd
from intelligence_warehouse.historical_recovery.mlb_statcast_biomechanics import (
    validate_leaderboard_csv, eligible_prior_season,
    join_prior_season_biomechanics, leaderboard_spec,
)

SPRINT=(b'player_id,team,sprint_speed,competitive_runs,bolts,hp_to_1b\n'
        b'1001,KC,28.9,104,21,4.2\n1002,NY,27.4,4,0,4.5\n')
BAT=(b'id,name,swings_competitive,avg_bat_speed,swing_length,'
     b'hard_swing_rate,whiff_per_swing,batted_ball_events\n'
     b'1001,"Sample, Person",700,75.2,7.1,0.38,0.25,210\n')

class HistoricalBiomechanicsCaptureTests(unittest.TestCase):
    def test_sprint_is_feet_per_second_and_bat_speed_is_a_different_column(self):
        s,proof=validate_leaderboard_csv(SPRINT,'sprint_speed',2025)
        self.assertEqual(proof['rows'],2)
        self.assertEqual(s['sprint_speed'].iloc[0],28.9)
        self.assertTrue(s['qualifies_minimum_opportunities'].iloc[0])
        self.assertFalse(s['qualifies_minimum_opportunities'].iloc[1])
        self.assertEqual(s['feature_first_eligible_season'].iloc[0],2026)
        self.assertNotIn('avg_bat_speed',s.columns)
        b,other=validate_leaderboard_csv(BAT,'bat_speed',2025)
        self.assertEqual(other['rows'],1)
        self.assertEqual(b['avg_bat_speed'].iloc[0],75.2)
        self.assertNotIn('sprint_speed',b.columns)

    def test_bat_tracking_source_must_use_real_season_start_and_end_filters(self):
        _,params=leaderboard_spec('bat_speed',2024)
        self.assertEqual(params.get('seasonStart'),2024)
        self.assertEqual(params.get('seasonEnd'),2024)
        self.assertNotIn('year',params)
        _,p2=leaderboard_spec('bat_speed',2025)
        self.assertEqual(p2.get('seasonStart'),2025)
        self.assertEqual(p2.get('seasonEnd'),2025)

    def test_future_or_same_season_cannot_be_used_as_earlier_game_feature(self):
        self.assertFalse(eligible_prior_season('2025-08-10',2025))
        self.assertTrue(eligible_prior_season('2026-04-21',2025))
        self.assertFalse(eligible_prior_season('2024-04-21',2025))

    def test_invalid_ids_mph_or_fps_values_rejected(self):
        with self.assertRaisesRegex(ValueError,'player identifiers'):
            validate_leaderboard_csv(SPRINT.replace(b'1001',b'0'),'sprint_speed',2025)
        with self.assertRaisesRegex(ValueError,'implausible'):
            validate_leaderboard_csv(SPRINT.replace(b'28.9',b'999.9'),'sprint_speed',2025)
        with self.assertRaisesRegex(ValueError,'implausible'):
            validate_leaderboard_csv(BAT.replace(b'75.2',b'999.9'),'bat_speed',2025)

    def test_prior_season_merge_only_and_player_id_not_name_matching(self):
        sprint,_=validate_leaderboard_csv(SPRINT,'sprint_speed',2025)
        bat,_=validate_leaderboard_csv(BAT,'bat_speed',2025)
        result=join_prior_season_biomechanics(sprint,bat,target_season=2026)
        self.assertEqual(len(result),2)
        a=result.set_index('player_id').loc[1001]
        self.assertEqual(a['prior_season_sprint_speed_ft_per_sec'],28.9)
        self.assertEqual(a['prior_season_bat_speed_mph'],75.2)
        self.assertFalse(a['approved_for_live_model'])
        self.assertEqual(a['source_completed_season'],2025)
        self.assertTrue(pd.isna(result.set_index('player_id').loc[1002]['prior_season_bat_speed_mph']))
        with self.assertRaisesRegex(ValueError,'prior season'):
            join_prior_season_biomechanics(sprint,bat,target_season=2025)

if __name__=='__main__':
    unittest.main()
