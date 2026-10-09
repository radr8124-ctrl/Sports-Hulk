"""Frozen independent 2026 NFL player prop research source/grade guard tests."""
import unittest,json,hashlib
from collections import Counter
from datetime import datetime,timezone,timedelta
from pathlib import Path
from intelligence_warehouse.brain_performance import freeze_nfl_player_prop_baseline as model

class TestNFLPlayerFormFrozen(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.d=json.loads(model.FROZEN.read_text())
  cls.a=json.loads(model.ADDENDUM.read_text())
  cls.p=json.loads(model.PUBLIC.read_text())
  cls.original_checksum=model.checksum(model.FROZEN)

 def test_frozen_source_ids_lanes_and_counts(self):
  p=self.d
  self.assertEqual((p['all_selection_lanes_input_count'],p['unique_player_line_event_opportunity_count'],p['overlap_source_rows_not_independent_outcomes']),(40,26,14))
  self.assertEqual(p['unique_official_game_blocks'],11)
  self.assertEqual(len(p['rows']),26)
  self.assertEqual(sum(len(x['same_player_prop_opportunity_source_lanes']) for x in p['rows']),40)
  self.assertEqual(sum(any(l['lane']=='NFL_PRIZEPICKS' for l in x['same_player_prop_opportunity_source_lanes']) for x in p['rows']),14)
  self.assertEqual(len({(x['source_game_id'],x['player'],x['market'],x['side'],x['line']) for x in p['rows']}),26)

 def test_only_prior_reg_week1_to4_games_in_features(self):
  for x in self.d['rows']:
   self.assertEqual(x['historical_week_numbers'],[1,2,3,4])
   self.assertEqual(len(x['historical_previous_four_regular_2026_week_stats']),4)
   self.assertFalse(x['approved_play'])
   self.assertFalse(x['official_pre_kickoff_player_injury_and_active_confirmation_verified'])
   self.assertFalse(x['quoted_price_confirmed_executable_now'])
  self.assertTrue(self.d['no_preexisting_final_game_week5_outcome_as_model_feature'])

 def test_independent_baseline_math_and_blend_predeclared_formula(self):
  for x in self.d['rows']:
   self.assertEqual(x['empirical_smoothed_success_frequency_pct_NOT_CALIBRATED'],round(100*(x['prior_week_hit_count']+2)/8,3))
   for source in x['same_player_prop_opportunity_source_lanes']:
    self.assertAlmostEqual(source['market_plus_empirical_20pct_challenger_pct'],
     round(.8*source['market_reference_pct']+.2*x['empirical_smoothed_success_frequency_pct_NOT_CALIBRATED'],3),3)
    self.assertEqual(source['model_current_pct_equal_market_pct'],source['market_reference_pct'])
    self.assertFalse(source['original_line_was_approved_play'])

 def test_source_input_hash_pinned_separate_from_regular_updates(self):
  for key,p in self.a['pinned_inputs'].items():
   self.assertEqual(self.d['input_sha256'][key],p['sha256'])
   self.assertEqual(hashlib.sha256(Path(p['path']).read_bytes()).hexdigest(),p['sha256'])
  self.assertEqual(self.d['prior_prereg_file_sha256'],model.checksum(model.REGISTER))
  self.assertEqual(self.d['pinned_source_addendum_sha256'],model.checksum(model.ADDENDUM))

 def test_public_contains_no_private_ids_and_is_source_safe(self):
  self.assertTrue(self.p['unproven_model_not_recommendations'])
  self.assertFalse(self.p['real_wagers_placed'])
  self.assertTrue(self.p['prizepicks_payout_not_sportsbook_american_odds'])
  self.assertEqual((self.p['original_lane_observations'],self.p['independent_player_line_opportunities_at_freeze'],self.p['source_PP_and_PROP_overlap_rows']),(40,26,14))
  self.assertEqual(len(self.p['rows']),26)
  for row in self.p['rows']:
   self.assertNotIn('player_id',row)
   self.assertNotIn('book_provider_event_uuid',row)
   self.assertFalse(row['approved_play'])
   self.assertFalse(row['independent_model_beats_sportsbook_proven'])
  self.assertEqual(model.checksum(model.PUBLIC),model.checksum(model.DIST))

 def test_expired_opportunities_removed_on_new_public_view_without_mutating_original(self):
  after=datetime(2026,10,13,2,0,tzinfo=timezone.utc)
  x=model.publish_view(self.d,now=after)
  self.assertEqual(x['rows'],[])
  self.assertEqual(x['current_future_research_opportunities'],0)
  self.assertEqual(self.original_checksum,model.checksum(model.FROZEN))

 def test_recent_provider_ref_age_is_recomputed_not_relabelled_fresh(self):
  after=datetime(2026,10,10,19,0,tzinfo=timezone.utc)
  x=model.publish_view(self.d,now=after)
  self.assertEqual(len(x['rows']),26)
  self.assertTrue(all(r['original_quote_over_24h_old'] for r in x['rows']))
  self.assertFalse(x['real_wagers_placed'])
  self.assertEqual(self.original_checksum,model.checksum(model.FROZEN))

 def test_bad_or_missing_stat_original_is_not_silently_regenerated(self):
  # Running the regular CLI with frozen output present must never derive again
  # from freshly updated odds or completed outcomes.
  self.assertTrue(model.FROZEN.is_file())
  self.assertEqual(self.d['schema'],model.SCHEMA)
  self.assertGreater(len(self.d['rows']),0)
  self.assertNotIn('future_week5_player_outcome',self.d)

if __name__=='__main__':unittest.main()
