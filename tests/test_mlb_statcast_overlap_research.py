"""Overlap reports are descriptive pitcher/batted-ball research, never validated bets."""
from __future__ import annotations
import unittest
import pandas as pd
from intelligence_warehouse.historical_recovery.mlb_statcast_overlap import compare_profile_overlap

class StatcastProfileOverlapTests(unittest.TestCase):
    def test_persisted_older_and_newer_pitcher_samples_are_independent_qualified_counts(self):
        oldp=pd.DataFrame([
            {'pitcher':111,'pitch_type':'FF','pitches':350,'avg_velocity':92.0},
            {'pitcher':222,'pitch_type':'CH','pitches':80,'avg_velocity':86.0},
        ])
        newp=pd.DataFrame([
            {'pitcher':111,'pitch_type':'FF','pitches':52,'avg_velocity':94.0},
            {'pitcher':222,'pitch_type':'CH','pitches':52,'avg_velocity':85.0},
        ])
        oldb=pd.DataFrame([{'batter':700,'pitch_type':'FF','pitches':130,'avg_exit_velo':90.1}])
        newb=pd.DataFrame([{'batter':700,'pitch_type':'FF','pitches':19,'avg_exit_velo':96.3}])
        result=compare_profile_overlap(oldp,newp,oldb,newb)
        self.assertEqual(result['qualified_pitcher_pitch_types'],1)
        self.assertEqual(result['qualified_batter_pitch_types'],1)
        self.assertEqual(result['qualified_pitcher_ids'],1)
        self.assertEqual(result['qualified_batter_ids'],1)
        self.assertFalse(result['direct_batter_sprint_speed_available'])
        self.assertFalse(result['betting_edge_proven'])
        self.assertEqual(result['new_pitches_are_historical_not_forward_evidence'],True)

    def test_ambiguous_duplicate_player_pitch_type_keys_rejected(self):
        oldp=pd.DataFrame([
            {'pitcher':111,'pitch_type':'FF','pitches':350,'avg_velocity':92},
            {'pitcher':111,'pitch_type':'FF','pitches':450,'avg_velocity':92.2},
        ])
        newp=pd.DataFrame([{'pitcher':111,'pitch_type':'FF','pitches':52,'avg_velocity':94}])
        empty=pd.DataFrame(columns=['batter','pitch_type','pitches','avg_exit_velo'])
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            compare_profile_overlap(oldp,newp,empty,empty)

if __name__=='__main__':
    unittest.main()
