"""Research-only Hugging Face 4-market challenger hard provenance gates."""
from copy import deepcopy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from intelligence_warehouse.betting_v2.hf_multimarket_secondary import (
    eligible, one_game_rows, verify_spec, selected, scores, stamp, SPEC, sha,
)


def example():
    return dict(
        status="VERIFIED_HISTORICAL",
        pair_status="VERIFIED_SAME_BOOK_TIME_PAIR",
        asof_status="PREGAME_FEATURE_VERIFIED",
        feature_rule="STRICTLY_PRIOR_COMPLETED_DATE_ONLY;TARGET_AND_LATER_GAMES_EXCLUDED",
        verified_win=True,
        official_game_pk=812345,
        official_player_id=999,
        game_id="m~1",
        book="fanduel",
        side="over",
        market="player hits",
        official_start="2026-06-15T21:00:00+00:00",
        ts="2026-06-15T17:00:00",
        prior_latest_date="2026-06-14",
        market_fair_probability=0.6,
        pregame_context_signal=0.2,
        odds=1.8,
        line=0.5,
    )


class TestHuggingFaceMultimarket(unittest.TestCase):
    def test_existing_frozen_spec_unchanged(self):
        spec=json.loads(SPEC.read_text())
        files=verify_spec(spec)
        self.assertEqual(len(files),3)
        self.assertFalse(spec["model_promotion_allowed"])
        self.assertEqual(spec["ridge_lambda"],16.0)

    def test_training_requires_truly_prior_player_stat(self):
        x=example()
        self.assertTrue(eligible(x,"train"))
        x["prior_latest_date"]="2026-06-15"
        self.assertFalse(eligible(x,"train"))

    def test_holdout_must_not_contaminate_training(self):
        x=example(); x["official_start"]="2026-07-02T21:00:00+00:00"
        self.assertFalse(eligible(x,"train"))
        x["status"]="OFFICIAL_DERIVED_HISTORICAL"
        self.assertTrue(eligible(x,"test"))
        x["official_start"]="2026-06-18T21:00:00+00:00"
        self.assertFalse(eligible(x,"test"))

    def test_unverified_pair_blocked(self):
        x=example();x["pair_status"]="ONLY_ONE_SIDE"
        self.assertFalse(eligible(x,"train"))

    def test_missing_unique_player_identity_blocked(self):
        x=example();x["official_player_id"]=None
        self.assertFalse(eligible(x,"train"))

    def test_impossible_price_rejected(self):
        x=example();x["odds"]=1.0
        self.assertFalse(eligible(x,"train"))

    def test_after_event_quote_rejected(self):
        x=example();x["ts"]="2026-06-15T22:00:00"
        self.assertFalse(eligible(x,"train"))

    def test_duplicate_official_games_cannot_gain_extra_independence(self):
        x=example()
        with self.assertRaisesRegex(ValueError,"DUPLICATE_OFFICIAL_GAME"):
            one_game_rows([x,deepcopy(x)],"player hits","train")

    def test_incomplete_source_never_automatically_win(self):
        x=example();x["verified_win"]=None
        self.assertFalse(eligible(x,"train"))

    def test_selected_threshold_uses_probability_and_actual_price(self):
        r=example()
        out=selected([r], np.asarray([0.74]),min_prob=0.7,min_ev=0.03)
        self.assertEqual(out["count"],1)
        self.assertEqual(out["paper_units"],0.8)
        low=selected([r], np.asarray([0.7]),min_prob=0.7,min_ev=0.3)
        self.assertEqual(low["count"],0)

    def test_selection_respects_70_probability_before_roi(self):
        r=example()
        out=selected([r],np.asarray([0.69]),min_prob=0.7,min_ev=0.03)
        self.assertEqual(out["count"],0)

    def test_lower_brier_better(self):
        actual=np.asarray([1.0,0.0])
        good=scores(actual,np.asarray([0.9,0.1]))
        bad=scores(actual,np.asarray([0.1,0.9]))
        self.assertLess(good["brier"],bad["brier"])

    def test_freeze_blocks_changed_inputs(self):
        spec=json.loads(SPEC.read_text())
        spec["frozen_inputs_sha256"]["historical_june_train"]="0"*64
        with self.assertRaisesRegex(ValueError,"FROZEN_INPUT_FILE_CHANGED"):
            verify_spec(spec)


if __name__=="__main__":
    unittest.main()
