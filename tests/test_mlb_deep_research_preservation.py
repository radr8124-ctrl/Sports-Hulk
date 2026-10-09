"""MLB derived science vault and source receipts must survive regular archiving."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SMALL_HISTORIC={
    'pitcher_statcast_arsenal':'baseball_vault/derived/MLB_PITCHER_ARSENAL.csv',
    'batter_vs_pitch_type':'baseball_vault/derived/MLB_BATTER_VS_PITCH_TYPE.csv',
    'statcast_profile_build_receipt':'baseball_vault/derived/MLB_BLENDED_PROFILE_BUILD.csv',
    'historical_matchup_intelligence':'baseball_vault/derived/MLB_MATCHUP_BOARD_INTELLIGENCE.csv',
    'historical_comp_walkforward_legacy':'baseball_vault/derived/MLB_COMP_WALKFORWARD_RESULTS.csv',
    'historical_park_season_aggregate':'baseball_vault/derived/MLB_PARK_RUN_FACTORS.csv',
    'historical_weather_limited':'baseball_vault/derived/MLB_WEATHER_FEATURES.csv',
    'historical_game_master':'baseball_vault/derived/MLB_GAME_MASTER.csv',
    'historical_pregame_features_legacy_leak_review':'baseball_vault/derived/MLB_HISTORICAL_PREGAME_FEATURES.csv',
}
LARGE_HISTORIC=(
    'intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_HISTORY.csv',
    'intelligence_warehouse/mlb_player_history/MLB_PLAYER_PREGAME_FEATURES.csv',
    'baseball_vault/raw/game_master/mlb_schedule_2024.json',
    'baseball_vault/raw/game_master/mlb_schedule_2025.json',
    'baseball_vault/raw/game_master/mlb_schedule_2026.json',
)


class ResearchSourcePersistenceTests(unittest.TestCase):
    def test_deep_statcast_and_weather_features_enter_existing_hourly_content_archive(self):
        data=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        for lane,path in SMALL_HISTORIC.items():
            with self.subTest(lane=lane,path=path):
                entries=[entry for entry in data['files'] if entry.get('path')==path]
                self.assertEqual(len(entries),1)
                self.assertEqual(entries[0]['sport'],'MLB')
                self.assertEqual(entries[0]['lane'],lane)
                self.assertGreater((ROOT/path).stat().st_size,0)

    def test_both_small_and_large_historical_sources_are_in_private_protected_backup(self):
        body=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        for path in list(SMALL_HISTORIC.values())+list(LARGE_HISTORIC):
            with self.subTest(path=path):
                self.assertIn(f'copy_if_exists "{path}"',body)

    def test_old_pregame_park_features_are_labeled_legacy_not_proven(self):
        data=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        f='baseball_vault/derived/MLB_HISTORICAL_PREGAME_FEATURES.csv'
        x=next(v for v in data['files'] if v['path']==f)
        self.assertIn('legacy_leak_review',x['lane'])

if __name__=='__main__':unittest.main()
