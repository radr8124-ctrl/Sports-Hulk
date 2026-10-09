"""Whitelisted public view cannot expose source sportsbook/private HULK artifacts."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json,hashlib,tempfile,unittest

from intelligence_warehouse.brain_performance import build_forward_proof_history as p


class TestForwardPublicOnlyFromVerifiedSource(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        current=self.root/p.BASE/p.CURRENT
        hist=self.root/p.BASE/p.HISTORY
        current.parent.mkdir(parents=True)
        current.write_bytes((p.ROOT/p.BASE/p.CURRENT).read_bytes())
        hist.write_bytes((p.ROOT/p.BASE/p.HISTORY).read_bytes())

    def test_output_matches_verifiable_original_and_contains_aggregate_only(self):
        output=self.root/'site/public/forward_proof_current.json'
        report=p.publish_public_proof(root=self.root,output_paths=[output])
        payload=json.loads(output.read_text())
        self.assertEqual(payload["schema"],p.PUBLIC_SCHEMA)
        self.assertEqual(payload["verified_append_only_history_checkpoints"],report['history_checkpoint_count'])
        self.assertEqual(payload['game_lines']['wins'],115)
        self.assertEqual(payload['game_lines']['losses'],71)
        self.assertEqual(payload['props_and_pickem']['wins'],1763)
        self.assertEqual(payload['props_and_pickem']['losses'],1080)
        self.assertGreaterEqual(payload['mlb_price_movement']['frozen_source_observations'],29)
        self.assertFalse(payload['game_lines']['actual_real_money_roi_proven'])
        self.assertFalse(payload['truthfulness']['automatic_model_promotion_allowed'])
        self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(),report['public_payload_sha256'])
        content=output.read_text().lower()
        for forbidden in ('snapshot_ledger','player_uuid','access_token','api_key',
                          'source_path','source_filename','phone','password','radr8124',
                          'betting_play_approved','real_money_wagers'):
            self.assertNotIn(forbidden,content,forbidden)

    def test_public_tampered_chain_is_fail_closed(self):
        history=self.root/p.BASE/p.HISTORY
        history.write_bytes(history.read_bytes().replace(b'"wins":115',b'"wins":199',1))
        output=self.root/'site/public/forward_proof_current.json'
        with self.assertRaisesRegex(ValueError,'HASH_CHAIN_CHANGED'):
            p.publish_public_proof(root=self.root,output_paths=[output])
        self.assertFalse(output.exists())

    def test_current_view_conflict_cannot_be_published(self):
        current=self.root/p.BASE/p.CURRENT
        wrong=json.loads(current.read_text())
        wrong['view']['game_lines']['hit_rate_pct']=100.
        current.write_text(json.dumps(wrong))
        output=self.root/'site/public/forward_proof_current.json'
        with self.assertRaisesRegex(ValueError,'PRIVATE_CURRENT_NOT_EQUAL_VERIFIED'):
            p.publish_public_proof(root=self.root,output_paths=[output])
        self.assertFalse(output.exists())

    def test_research_proof_cannot_claim_real_profit(self):
        original=p.verify_history(self.root/p.BASE/p.HISTORY)[-1]
        bad=deepcopy(original)
        bad['view']['experiment_result']['profitable_70_percent_betting_strategy_proven']=True
        with self.assertRaisesRegex(ValueError,'MUST_DERIVE_FROM_VERIFIED'):
            p.public_projection(bad,history_entries=3)


if __name__=='__main__':
    unittest.main()
