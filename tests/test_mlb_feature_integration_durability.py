"""MLB research assets and frozen outcomes must survive cleanup and replay."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
BASE='reports/mlb_feature_integration_20261008'
FILES=(
    'MLB_2026_ASOF_HITTER_RESEARCH_FEATURES.parquet',
    'MLB_2026_HITTER_OFFICIAL_RESEARCH_LABELS.parquet',
    'MLB_ASOF_FEATURE_STORE_MANIFEST.json',
    'MLB_PRIOR_SPEED_WALKS_MODEL_PREREGISTRATION.md',
    'MLB_SPEED_WALKS_FROZEN_RESEARCH_MODEL.json',
    'MLB_SPEED_WALKS_SECONDARY_JULY_EXPERIMENT.json',
    'MLB_FEATURE_STORE_SPEED_WALKS_ACCEPTANCE_2026-10-08.md',
)


class MLBSourceDurabilityAndTruthTests(unittest.TestCase):
    def test_all_generated_historical_science_sources_are_versioned_in_archive(self):
        catalog=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        for name in FILES:
            with self.subTest(name=name):
                target=f'{BASE}/{name}'
                matches=[x for x in catalog['files'] if x.get('path')==target]
                self.assertEqual(len(matches),1)
                self.assertEqual(matches[0]['sport'],'MLB')
                self.assertTrue(matches[0]['lane'].startswith('asof_speed_walks_research'))
                self.assertTrue((ROOT/target).is_file())

    def test_protected_backup_references_complete_derived_folder(self):
        backup=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        self.assertIn(f'copy_if_exists "{BASE}"',backup)
        ignore=(ROOT/'.gitignore').read_text()
        self.assertIn(f'/{BASE}/',ignore)

    def test_original_2026_frozen_model_provenance_and_separate_labels(self):
        features=pd.read_parquet(ROOT/BASE/FILES[0])
        labels=pd.read_parquet(ROOT/BASE/FILES[1])
        manifest=json.loads((ROOT/BASE/FILES[2]).read_text())
        frozen_path=ROOT/BASE/FILES[4]
        frozen=json.loads(frozen_path.read_text())
        test=json.loads((ROOT/BASE/FILES[5]).read_text())
        self.assertEqual(len(features),len(labels))
        self.assertFalse(features.duplicated(['game_pk','player_id']).any())
        self.assertFalse(labels.duplicated(['game_pk','player_id']).any())
        self.assertNotIn('realized_hits',features.columns)
        self.assertTrue(features['source_time_class'].str.startswith('RETROSPECTIVE_').all())
        self.assertFalse(features.live_betting_approved.any())
        self.assertEqual(manifest['features'][FILES[0]]['rows'],len(features))
        self.assertEqual(manifest['features'][FILES[1]]['rows'],len(labels))
        self.assertEqual(hashlib.sha256(frozen_path.read_bytes()).hexdigest(),test['frozen_model_sha256'])
        self.assertEqual(frozen['training_independent_games'],90)
        self.assertEqual(test['test_independent_games'],46)
        self.assertEqual(len(set(frozen['training_official_game_pks'])),90)
        self.assertFalse(frozen['live_plays_approved'])
        self.assertFalse(test['proven_market_edge'])
        self.assertFalse(test['live_plays_approved'])

if __name__=='__main__':unittest.main()
