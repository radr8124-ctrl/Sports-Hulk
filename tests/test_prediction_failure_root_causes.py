"""Independent grade/source consistency tests; no production prediction changes."""
import json
from pathlib import Path
from copy import deepcopy
import unittest
from intelligence_warehouse.brain_performance import audit_prediction_failure_root_causes as a
from intelligence_warehouse.betting_v2 import build_betting_v2_all_markets_forward as g
from intelligence_warehouse.betting_v2 import build_prop_v2_forward as p

class TestFailureRootCause(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=Path('reports/ZENITH_PREDICTION_FAILURE_ROOT_CAUSE_AUDIT_2026-10-09.json')
        cls.r=json.loads(cls.source.read_text())

    def test_market_mirror_all_game_line_probs_not_model_edge(self):
        r=self.r['game_predictions']
        self.assertEqual(r['original_settled_alternative_game_line_observations'],186)
        self.assertEqual(r['model_probability_exactly_equal_market_count'],186)
        self.assertTrue(r['no_independent_game_model_edge_shown'])
        self.assertEqual(r['original_frozen_research_decision_counts'],{
            'PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE':180,
            'PASS_CONTRADICTORY_GAME_SIDES':6,
        })
        self.assertEqual(sum(r['original_price_reference_type_counts'].values()),186)

    def test_nba_spreads_are_preseason_and_eight_game_blocks(self):
        spread=self.r['NBA_spread_eight_game_preseason']
        self.assertEqual(spread['independent_official_preseason_game_blocks'],8)
        self.assertEqual(spread['source_evidence_spread_lines']['entries'],39)
        self.assertEqual(spread['source_evidence_spread_lines']['wins'],10)
        self.assertEqual(spread['source_evidence_spread_lines']['losses'],29)
        first=spread['one_quote_per_game_RETROSPECTIVE_ONLY']
        self.assertEqual((first['entries'],first['wins'],first['losses']),(8,3,5))
        self.assertEqual(first['paper_roi_pct'],-31.63)
        self.assertTrue(spread['all_39_shadow_PASS_not_real_bets'])

    def test_NHL_true_feature_adjustments_worse_than_book_market(self):
        core=self.r['player_props']['NHL_core_model']
        self.assertEqual(core['correlated_player_quote_rows'],799)
        self.assertEqual(core['independent_game_blocks'],16)
        self.assertAlmostEqual(core['average_abs_model_market_probability_shift_pp'],7.214)
        self.assertAlmostEqual(core['model_minus_market_brier'],.013571,6)
        self.assertGreater(core['model_brier'],core['source_market_brier'])
        for group in ('PLAYER_TOTAL_ASSISTS','PLAYER_TOTAL_GOALS','PLAYER_TOTAL_POINTS','PLAYER_TOTAL_SHOTS'):
            self.assertGreater(core['by_player_prop_market'][group]['model_minus_market_brier'],0,group)

    def test_higher_confidence_not_equal_proven_calibration(self):
        buckets=self.r['player_props']['NHL_core_model']['model_confidence_buckets_diagnostic_only']
        for k in ('MODEL_70_TO_80','MODEL_OVER_80'):
            b=buckets[k]
            self.assertGreater(b['correlated_player_prop_rows'],0)
            self.assertLess(b['realized_grade_WIN_pct'],b['original_predicted_probability_mean_pct'])
            self.assertLessEqual(b['independent_games_not_line_count'],16)

    def test_MLB_props_high_win_but_negative_price_ROI(self):
        r=self.r['player_props']['source_MLB_prop_high_wins_not_necessarily_valuable']
        self.assertEqual(r['wins'],693)
        self.assertEqual(r['losses'],295)
        self.assertEqual(r['games'],9)
        self.assertEqual(r['original_priced_paper_roi_pct'],-.94)
        self.assertEqual(r['model_brier'],r['source_market_brier'])
        self.assertEqual(self.r['player_props']['market_reference_only_MLB_player_props'],988)

    def test_hugging_face_control_did_not_prove_model_market_edge(self):
        hf=self.r['hugging_face_independent_market_benchmark']
        self.assertEqual(hf['independent_historical_holdout_regular_season_games'],503)
        self.assertEqual(hf['original_regular_season_games_source_matched'],1214)
        self.assertGreater(hf['NBA_total_feature_model_Brier'],hf['NBA_total_market_Brier'])
        self.assertFalse(hf['NBA_spread_statistically_proven_edge'])
        self.assertFalse(hf['source_close_original_book_updated_at_and_executable_market_not_verified'] is False)

    def test_NBA_totals_overlap_original_ledger_not_prediction_success(self):
        r=self.r['NBA_totals_source_defects']
        self.assertEqual(r['duplicate_semantic_total_lines'],8)
        self.assertEqual(r['incorrect_original_tipoff_source_rows'],7)
        self.assertEqual(r['strict_qualified_unique_preseason_lines'],91)
        self.assertEqual(r['independent_strictly_verified_preseason_games'],19)
        self.assertTrue(r['model_brier_equals_bookmaker'])

    def test_original_audit_source_hashes_match_recoverable_frozen_snapshot(self):
        # The live game forward ledger legally refreshes hourly. Tests must
        # verify the ORIGINAL checked source snapshot, not expect live data
        # to remain byte-identical forever after new games are graded.
        backup=a.ROOT/'.deploy_backups/zenith_prediction_failure_root_cause_READBACK_20261009T110000Z/RESTORED'
        for label,expected in self.r['frozen_original_source_sha256'].items():
            self.assertRegex(expected,r'^[0-9a-f]{64}$')
            path=a.ROOT/a.SOURCE[label]
            historical=backup/a.SOURCE[label]
            if historical.is_file():
                self.assertEqual(a.digest(historical),expected,label)
            elif a.digest(path)==expected:
                self.assertEqual(a.digest(path),expected,label)
            else:
                self.skipTest('Original raw snapshot not mounted on this installation; saved audit hashes remain versioned')

    def test_game_source_bad_grade_count_rejected_no_recalibration(self):
        original=json.loads((a.ROOT/a.SOURCE['game_summary']).read_text())
        original['all_predictions']['wins']+=1
        rows=list(g.canonical().values())
        with self.assertRaisesRegex(ValueError,'ORIGINAL_GAME_WIN_AND_LOSS_TALLY_MISMATCH'):
            a.game_results(rows,original)

    def test_prop_source_malformed_probability_rejected(self):
        subset=[x for x in p.canonical().values() if x.get('model_version')==a.PROP_VERSION and x.get('lane_key')=='NHL_PROP' and x.get('probability_source')=='LANE_CORE_MODEL' and x.get('grade') in ('WIN','LOSS','PUSH')]
        fake=deepcopy(subset[:2])
        fake[0]['v2_probability_pct']=float('nan')
        with self.assertRaisesRegex(ValueError,'NONFINITE'):
            a.probabilities(fake)

    def test_NHL_16_independent_game_bootstrap_uses_frozen_original_prop_cohort(self):
        source=a.ROOT/'reports/NHL_ADJUSTED_PROP_GAME_CLUSTER_BRIER_AUDIT_2026-10-09.json'
        evidence=json.loads(source.read_text())
        self.assertEqual(evidence['original_prop_source_sha256'],
                         self.r['frozen_original_source_sha256']['prop_ledger'])
        self.assertEqual(evidence['correlated_nhl_player_prop_rows'],799)
        self.assertEqual(evidence['independent_game_blocks'],16)
        self.assertEqual(evidence['bootstrap_game_block_draws'],3000)
        self.assertEqual(evidence['bootstrap_seed'],20261009)
        lower,upper=evidence['independent_game_bootstrap_95ci_model_minus_market_Brier']
        self.assertLess(0,lower)
        self.assertLess(lower,upper)
        self.assertFalse(evidence['live_model_or_betting_picks_unchanged'] is False)
        self.assertTrue(evidence['not_future_independent_training_or_trial'])

    def test_no_live_model_bet_automation_or_trained_weights_changed(self):
        r=self.r
        self.assertFalse(r['actual_live_model_or_betting_play_modified'])
        self.assertFalse(r['statistically_or_commercially_proven_predictive_edge'])
        guard=r['experiment_release_guardrails']
        self.assertFalse(guard['live_bet_model_or_wager_changes_authorized'])
        self.assertTrue(guard['one_precommitted_line_or_team_per_independent_game_for_primary_profitability'])


if __name__=="__main__":unittest.main()
