"""Genuinely pre-first-pitch advanced restricted model source is durably scheduled."""
from pathlib import Path
import json
import hashlib
import unittest

ROOT=Path(__file__).resolve().parents[1]
PRE='reports/mlb_feature_integration_20261008/MLB_RESTRICTED_SPEED_WALKS_FORWARD_SHADOW_PREREGISTRATION_2026-10-08.md'
MODEL='reports/mlb_feature_integration_20261008/MLB_RESTRICTED_SPEED_WALKS_FROZEN_TRAINING_V1.json'
PREFIX='intelligence_warehouse/mlb_pregame_capture'
FORECAST=PREFIX+'/MLB_V2_RESTRICTED_SPEED_WALKS_SHADOW_FORECASTS.jsonl'
F_RECEIPT=PREFIX+'/MLB_V2_RESTRICTED_SPEED_WALKS_SHADOW_SUMMARY.json'
SCORED=PREFIX+'/MLB_V2_RESTRICTED_SPEED_WALKS_OFFICIAL_THREEWAY_SCORES.jsonl'
S_RECEIPT=PREFIX+'/MLB_V2_RESTRICTED_SPEED_WALKS_OFFICIAL_THREEWAY_SUMMARY.json'


class VersionedProspectiveAdvancedModelDurability(unittest.TestCase):
    def test_model_uses_original_prejuly_cohort_and_no_july_label_or_later_first_pitch(self):
        path=ROOT/MODEL
        j=json.loads(path.read_text())
        self.assertEqual(j['training_independent_games'],90)
        self.assertEqual(len(j['training_official_game_pks']),90)
        self.assertEqual(j['features'].__len__(),8)
        self.assertFalse(j['July_results_used_in_fit'])
        self.assertFalse(j['live_betting_approved'])
        self.assertFalse(j['is_full_advanced_16_feature_model'])
        self.assertGreater((ROOT/PRE).stat().st_size,500)
        for rel,digest in j['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),digest)

    def test_source_version_wires_after_market_control_and_before_existing_decision(self):
        script=(ROOT/'mlb_live/run_mlb_refresh.sh').read_text()
        first='intelligence_warehouse.historical_recovery.mlb_shadow_market_control'
        next_='intelligence_warehouse.historical_recovery.mlb_restricted_speed_walk_shadow --stage freeze_forecasts'
        self.assertEqual(script.count(next_),1)
        self.assertLess(script.index(first),script.index(next_))
        self.assertLess(script.index(next_),script.index('=== MLB DECISION BRAIN ==='))
        self.assertIn('SPORTS_LABEL=mlb-restricted-speed-walk-shadow',script)
        self.assertIn('SPORTS_MAX_SECONDS=20',script)
        self.assertIn('original source-time advanced shadow records preserved',script)
        # A scheduled source job must never silently re-train a previously
        # accepted coefficient set on fresh/outcome-contaminated source data.
        self.assertNotIn('mlb_restricted_speed_walk_shadow --stage train_once',script)

    def test_source_time_threeway_grader_runs_after_true_final_and_market_grades(self):
        script=(ROOT/'mlb_live/decision/run_mlb_learning_postrefresh.sh').read_text()
        self.assertIn('SPORTS_LABEL=mlb-restricted-speed-walk-official-score',script)
        self.assertIn('SPORTS_MAX_SECONDS=15',script)
        self.assertEqual(script.count('intelligence_warehouse.historical_recovery.mlb_restricted_speed_walk_official_scoring'),1)
        self.assertLess(script.index('intelligence_warehouse.historical_recovery.mlb_research_forward_labels'),
                        script.index('intelligence_warehouse.historical_recovery.mlb_restricted_speed_walk_official_scoring'))
        self.assertIn('original triple-score evidence preserved',script)

    def test_all_new_model_training_evidence_is_archived_and_backup_restorable(self):
        c=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        for path,lane in [
            (PRE,'mlb_forward_restricted_8col_training_preregistration'),
            (MODEL,'mlb_forward_restricted_8col_90game_frozen_training'),
            (FORECAST,'mlb_forward_restricted_8col_prospective_immutable_forecasts'),
            (F_RECEIPT,'mlb_forward_restricted_8col_prospective_capture_receipt'),
            (SCORED,'mlb_forward_restricted_8col_threeway_actual_game_scores'),
            (S_RECEIPT,'mlb_forward_restricted_8col_threeway_actual_grade_receipt')
        ]:
            with self.subTest(path=path):
                rows=[r for r in c['files'] if r['path']==path]
                self.assertEqual(len(rows),1)
                self.assertEqual(rows[0]['sport'],'MLB')
                self.assertEqual(rows[0]['lane'],lane)
                self.assertTrue((ROOT/path).is_file())

    def test_private_protected_backup_and_git_exclusion(self):
        backup=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        ignore=(ROOT/'.gitignore').read_text()
        for path in (FORECAST,F_RECEIPT,SCORED,S_RECEIPT):
            self.assertIn(f'copy_if_exists "{path}"',backup)
            self.assertIn(path,ignore)
        self.assertIn('copy_if_exists "reports/mlb_feature_integration_20261008"',backup)

    def test_18_advanced_frozen_prospective_not_18_independent_games(self):
        p=ROOT/FORECAST
        rows=[json.loads(s) for s in p.read_text().splitlines() if s.strip()]
        first=[r for r in rows if r['game_pk']==849832]
        self.assertEqual(len(first),18)
        self.assertGreaterEqual(len({r['game_pk'] for r in rows}),1)
        self.assertEqual(len({(r['game_pk'],r['mlbam_player_id']) for r in rows}),len(rows))
        self.assertEqual(hashlib.sha256(''.join(p.read_text().splitlines(keepends=True)[:18]).encode()).hexdigest(),
                         '23267a3176615ef5adb5945c4ddb22a00e05e743c24576a7a9127fd2ba87d2f2')
        self.assertTrue(all(r['first_prospective_prediction_frozen_at_utc']<r['original_game_start_at_utc'] for r in rows))
        self.assertTrue(all(r['market_metric']=='hits' and float(r['line'])==.5 for r in rows))
        self.assertTrue(all(r['full_context_model_used'] is False and r['live_play_approved'] is False for r in rows))
        model_hash=hashlib.sha256((ROOT/MODEL).read_bytes()).hexdigest()
        self.assertTrue(all(r['model_coefficients_frozen_sha256']==model_hash for r in rows))

    def test_earliest_pending_game_correctly_has_no_threeway_model_win(self):
        graded=[json.loads(s) for s in (ROOT/SCORED).read_text().splitlines() if s.strip()]
        r=json.loads((ROOT/S_RECEIPT).read_text())
        self.assertEqual(r['source_true_independent_game_blocks'],len({x['official_game_pk'] for x in graded}))
        self.assertGreaterEqual(r['original_restricted_forecasts'],18)
        self.assertEqual(r['official_player_hit_events_scored'],len(graded))
        self.assertFalse(any(x['sportsbook_wager_executed'] for x in graded))
        self.assertFalse(r['statistically_proven_enhanced_market_edge'])
        self.assertEqual(r['remaining_game_blocks_to_first_evidence_floor'],
                         max(0,30-r['source_true_independent_game_blocks']))

if __name__=='__main__':
    unittest.main()
