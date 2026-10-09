"""Owner research must show source-priced future evidence, never presumed betting edge."""
from pathlib import Path
import hashlib,json,unittest

ROOT=Path(__file__).resolve().parents[1]
CAPTURE=ROOT/'intelligence_warehouse/mlb_pregame_capture'
REPORT='reports/SPORTS_ZENITH_MLB_TRUE_FORWARD_MARKET_CONTROL_AND_OUTCOME_LEARNING_2026-10-08.md'

class MLBFirstTrueMarketAdvantageTruthAuditTests(unittest.TestCase):
 def test_source_provenance_and_report_version_survive_hourly_archive_and_private_backup(self):
  j=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
  docs=[x for x in j['files'] if x.get('path')==REPORT]
  self.assertEqual(len(docs),1)
  self.assertEqual(docs[0]['lane'],'mlb_v2_first_book_vs_market_shadow_acceptance')
  self.assertIn(f'copy_if_exists "{REPORT}"',(ROOT/'scripts/backup_sports_zenith_state.sh').read_text())

 def test_pre_game_18_hitter_shadow_records_have_true_original_lineup_references(self):
  source=CAPTURE/'MLB_PREGAME_SOURCE_EVIDENCE.jsonl'
  hashes={hashlib.sha256(line.encode()).hexdigest() for line in source.read_text().splitlines(keepends=True) if line.strip()}
  model=ROOT/'reports/mlb_feature_integration_20261008/MLB_SPEED_WALKS_FROZEN_RESEARCH_MODEL.json'
  modelsha=hashlib.sha256(model.read_bytes()).hexdigest()
  file=CAPTURE/'MLB_V2_MARKET_CALIBRATION_SHADOW_FORECASTS.jsonl'
  snapshots=[json.loads(line) for line in file.read_text().splitlines() if line.strip()]
  first=[r for r in snapshots if r['game_pk']==849832]
  self.assertEqual(len(first),18)
  self.assertEqual(len({r['mlbam_player_id'] for r in first}),18)
  self.assertTrue(all(r['source_original_lineup_sha256'] in hashes for r in first))
  self.assertTrue(all(r['baseline_model_coefficients_sha256']==modelsha for r in first))
  self.assertTrue(all(r['frozen_shadow_at_utc']<r['actual_game_event_start_utc'] for r in first))
  self.assertTrue(all(not r['betting_play_authorized'] and not r['wager_submitted'] for r in first))
  self.assertTrue(all(r['proprietary_speed_walks_model_evaluated'] is False for r in first))

 def test_real_quoted_pairs_have_same_book_sides_and_no_automatic_plays(self):
  file=CAPTURE/'MLB_V2_PREGAME_SAME_BOOK_FAIR_PRICE_BASELINES.jsonl'
  rows=[json.loads(line) for line in file.read_text().splitlines() if line.strip()]
  first=[r for r in rows if r['official_game_pk']==849832]
  self.assertGreaterEqual(len(first),106)
  for r in first:
   self.assertEqual(r['over_provider_source_row']['sportsbook'],r['under_provider_source_row']['sportsbook'])
   self.assertEqual(r['over_provider_source_row']['line'],r['under_provider_source_row']['line'])
   self.assertEqual(r['over_provider_source_row']['captured_at'],r['under_provider_source_row']['captured_at'])
   self.assertEqual(r['over_provider_source_row']['player_id'],r['under_provider_source_row']['player_id'])
   self.assertFalse(r['betting_selection_approved'])
   self.assertFalse(r['model_prediction_created'])

 def test_status_report_cannot_falsely_call_one_game_a_proven_advantage(self):
  summary=CAPTURE/'MLB_V2_MARKET_SHADOW_OFFICIAL_COMPARISON_SUMMARY.json'
  data=json.loads(summary.read_text())
  self.assertFalse(data['commercial_betting_edge_claim_permitted'])
  self.assertFalse(data['statistically_proven_market_improvement'])
  self.assertEqual(data['minimum_independent_games_for_first_sample_floor'],30)
  self.assertTrue(data['official_players_graded_are_not_independent_games'])

if __name__=='__main__':unittest.main()
