"""A source shard read after freeze must never retrain on its own grades."""
import unittest
from datetime import datetime,timedelta,timezone
from tests.test_hf_mlb_prop_expanded_analysis import offer,history
from tests.test_hf_mlb_prop_locked_holdout import data
from intelligence_warehouse.betting_v2.hf_mlb_prop_locked_holdout import freeze_historical_hits_model
from intelligence_warehouse.betting_v2.hf_mlb_prop_unseen_shard import audit_unseen_shard

class UnseenShardTests(unittest.TestCase):
    def test_locked_evaluation_uses_original_coefs_on_new_external_official_grade(self):
        frozen=freeze_historical_hits_model(data(40))
        before=dict(frozen)
        src=offer();src['source_shard']='0017.parquet'
        r=audit_unseen_shard(frozen,[src],history())
        self.assertEqual(r['summary']['officially_verified_records'],1)
        self.assertEqual(r['summary']['eligible_new_game_hits'],1)
        self.assertTrue(r['summary']['no_refit_on_holdout'])
        self.assertFalse(r['locked']['production_play_approved'])
        self.assertEqual(frozen,before)

    def test_reject_mismatched_source_shard(self):
        frozen=freeze_historical_hits_model(data(40))
        frozen['new_source_shard_reserved']='0017.parquet'
        src=offer();src['source_shard']='0000.parquet'
        with self.assertRaisesRegex(ValueError,'source shard'):
            audit_unseen_shard(frozen,[src],history())

if __name__=='__main__':unittest.main()
