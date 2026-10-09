"""Public NBA source-quality warning must be sanitized and anchored to frozen data."""
from __future__ import annotations
import hashlib,json,tempfile,unittest
from copy import deepcopy
from pathlib import Path
from intelligence_warehouse.brain_performance import publish_nba_source_quality as m


class TestPublicNBAQualityWarning(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.a=json.loads(m.AUDIT.read_text())
        self.audit_raw=m.AUDIT.read_bytes()
        self.r=json.loads(m.SENSITIVITY.read_text())

    def test_public_source_warning_has_only_aggregate_counts(self):
        out=self.base/'site/nba_total_source_quality.json'
        receipt=m.publish(paths=[out])
        self.assertTrue(out.is_file())
        self.assertEqual(receipt['output_count'],1)
        self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(),receipt['public_aggregate_sha256'])
        r=json.loads(out.read_text())
        self.assertEqual(r['retrospective_original_game_lines']['original_quoted_paper_roi_pct'],4.98)
        self.assertEqual(r['isolated_source_quality_sensitivity']['hypothetical_quote_paper_roi_pct'],-.69)
        self.assertEqual(r['nba_preseason_audit']['duplicate_regime_positions'],8)
        self.assertEqual(r['nba_preseason_audit']['incorrect_original_start_rows_held'],7)
        self.assertEqual(r['nba_preseason_audit']['independent_preseason_games'],19)
        self.assertFalse(r['real_money_wagers_or_executable_prices_verified'])
        self.assertFalse(r['genuine_unseen_NBA_regular_season_profitability_proven'])
        text=out.read_text().lower()
        for secret in ('access_token','api_key','password','player_uuid','event_id','street',
                       'source_filename','original_game_key','address','stripe'):
            self.assertNotIn(secret,text)

    def test_raw_audit_tampering_blocks_publication(self):
        changed=deepcopy(self.a)
        changed['source_de_duplicated_exact_same_game_market_side_line_first_quote']['wins']=70
        with self.assertRaisesRegex(ValueError,'UNVERIFIED_NBA_AUDIT_OR_POOLED'):
            m.project(changed,self.r,original_audit_sha=hashlib.sha256(json.dumps(changed).encode()).hexdigest())

    def test_loss_count_cannot_disappear_in_public_quality_sensitivity(self):
        changed=deepcopy(self.r)
        changed['sensitivity_unique_line_all_game_lines_losses']=0
        with self.assertRaisesRegex(ValueError,'NBA_SOURCE_QUALITY_CANNOT_HIDE_OLD_LOSSES'):
            m.project(self.a,changed,original_audit_sha=hashlib.sha256(self.audit_raw).hexdigest())

    def test_unverified_early_win_model_promotion_cannot_be_exported(self):
        changed=deepcopy(self.a)
        changed['probability_market_edge_statistically_proven']=True
        with self.assertRaisesRegex(ValueError,'UNVERIFIED_NBA_AUDIT'):
            m.project(changed,self.r,original_audit_sha=hashlib.sha256(self.audit_raw).hexdigest())

    def test_public_output_is_not_main_immutable_scorecard(self):
        self.assertNotEqual(m.PUBLIC_NAME,'forward_proof_current.json')
        self.assertFalse(m.AUDIT.name.startswith('BETTING_V2_'))


if __name__=='__main__':
    unittest.main()
