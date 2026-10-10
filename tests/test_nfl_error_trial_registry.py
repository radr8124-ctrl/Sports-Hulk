"""Prevent failed retrospective NFL patches from being silently deployed."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

import numpy as np

from intelligence_warehouse.outcome_learning.error_trial_registry import (
    CANDIDATES,read_registry,review_report,SCHEMA,
)
from intelligence_warehouse.historical_recovery.nfl_error_recovery_shadow import (
    OUTPUT,variants,
)
from intelligence_warehouse.historical_recovery.nfl_prior_score_form_model import (
    MODEL,HISTORICAL,
)

ROOT=Path(__file__).resolve().parents[1]
FROZEN=ROOT/"intelligence_warehouse/nfl_advanced_pregame/NFL_FIRST_PREKICKOFF_NINE_FEATURE_SCORE_FORM_SHADOW.jsonl"


class OriginalErrorRecoveryTruthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive=json.loads(OUTPUT.read_text())
        cls.market_sha=hashlib.sha256(HISTORICAL.read_bytes()).hexdigest()
        cls.model_sha=hashlib.sha256(MODEL.read_bytes()).hexdigest()
        cls.frozen_sha=hashlib.sha256(FROZEN.read_bytes()).hexdigest()

    @classmethod
    def tearDownClass(cls):
        assert hashlib.sha256(HISTORICAL.read_bytes()).hexdigest()==cls.market_sha
        assert hashlib.sha256(MODEL.read_bytes()).hexdigest()==cls.model_sha
        assert hashlib.sha256(FROZEN.read_bytes()).hexdigest()==cls.frozen_sha

    def review(self,archive=None):
        return review_report(self.archive if archive is None else archive,
                             historical_sha=self.market_sha,
                             original_model_sha=self.model_sha)

    def test_frozen_original_2025_model_reproduced_and_never_overwritten(self):
        x=self.archive
        self.assertEqual(x["historical_source_sha256"],self.market_sha)
        self.assertEqual(x["original_frozen_model_sha256"],self.model_sha)
        self.assertEqual(x["years"],[2022,2023,2024,2025])
        self.assertEqual(x["independent_test_games"],1136)
        self.assertFalse(x["candidate_live_model_deployed"])
        self.assertFalse(x["original_frozen_2026_predictions_modified"])
        self.assertFalse(x["independent_positive_EV_proven"])
        self.assertTrue(x["new_future_frozen_predictions_required"])
        self.assertEqual(x["folds"][-1]["results"]["original_model"]["brier"],0.212617338)

    def test_guard_math_only_flags_incomplete_and_winner_flip_without_using_result(self):
        model=np.array([.65,.45,.75,.65])
        book=np.array([.6,.60,.40,.65])
        p,low,flip=variants(model,book,np.array([0,3,3,4]),np.array([0,3,3,4]))
        self.assertEqual(low.tolist(),[True,False,False,False])
        self.assertEqual(flip.tolist(),[False,True,True,False])
        self.assertEqual(p["low_form_market_fallback"].tolist(),[.6,.45,.75,.65])
        self.assertEqual(p["winner_disagreement_market_fallback"].tolist(),[.65,.6,.4,.65])
        self.assertEqual(p["both_guards_market_fallback"].tolist(),[.6,.6,.4,.65])

    def test_each_corrective_shadow_rule_failed_to_beat_market_over_all_game_blocks(self):
        report=self.review()
        self.assertEqual(report["schema"],SCHEMA)
        self.assertEqual(report["tested_hypotheses_count"],4)
        self.assertEqual(report["rejected_against_market_count"],4)
        self.assertEqual(report["proposed_correction_count"],3)
        self.assertEqual(report["rejected_proposed_corrections_count"],3)
        self.assertFalse(report["promotion_allowed_without_independent_future_evidence"])
        self.assertTrue(report["fresh_unseen_2026_outcomes_required"])
        for rule in report["candidate_models"]:
            self.assertEqual(rule["status"],"REJECTED_NOT_BETTER_THAN_BOOKMAKER")
            self.assertFalse(rule["live_model_update_approved"])
            self.assertLess(rule["market_minus_candidate_brier"],0)
            self.assertEqual(len(rule["tested_years"]),4)
        self.assertEqual(self.archive["folds"][-1]["model_disagreed_with_market_winner_games"],6)
        self.assertEqual(self.archive["folds"][-1]["disagreement_model_wrong_book_right"],4)
        self.assertEqual(self.archive["folds"][-1]["disagreement_model_right_book_wrong"],2)

    def test_rejects_forced_live_promotion_and_fake_positive_ev(self):
        for change in (
            {"candidate_live_model_deployed":True},
            {"original_frozen_2026_predictions_modified":True},
            {"independent_positive_EV_proven":True},
            {"new_future_frozen_predictions_required":False},
            {"study_status":"PROVEN_FUTURE_PROFIT"},
            {"years":[2022,2023,2024,2026]},
        ):
            with self.subTest(change=change):
                fake={**self.archive,**change}
                with self.assertRaises(ValueError):
                    self.review(fake)

    def test_rejects_forged_sharp_gain_or_missing_old_holdout_evidence(self):
        fake=copy.deepcopy(self.archive)
        fake["pooled"]["winner_disagreement_market_fallback"]["brier"]=.18
        with self.assertRaisesRegex(ValueError,"Pooled Brier"):
            self.review(fake)
        fake=copy.deepcopy(self.archive)
        fake["folds"][0]["results"]["market_original"].pop("brier")
        with self.assertRaises(ValueError):
            self.review(fake)

    def test_refuses_training_future_games_in_past_years(self):
        fake=copy.deepcopy(self.archive)
        fake["folds"][2]["train_seasons"].append(2025)
        with self.assertRaises(ValueError):
            self.review(fake)
        fake=copy.deepcopy(self.archive)
        fake["folds"][1]["test_independent_games"]+=1
        with self.assertRaises(ValueError):
            self.review(fake)

    def test_original_sources_are_readback_verified_not_reconstructed_from_guesses(self):
        report=read_registry()
        self.assertEqual(report["historical_accuracy_source_sha256"],self.market_sha)
        self.assertEqual(report["original_frozen_model_sha256"],self.model_sha)
        self.assertRegex(report["historical_report_sha256"],r"^[a-f0-9]{64}$")
        self.assertTrue(all(not x["causal_explanation_proven"] for x in report["candidate_models"]))
        self.assertEqual(report["original_game_cohort_count"],1136)
        with self.assertRaises(ValueError):
            review_report(self.archive,historical_sha="0"*64,original_model_sha=self.model_sha)
        with self.assertRaises(ValueError):
            review_report(self.archive,historical_sha=self.market_sha,original_model_sha="0"*64)

    def test_case_studies_do_not_invent_causal_injuries_or_result_predictions(self):
        cases=self.archive["historical_error_examples_2025"]
        self.assertEqual(len(cases),10)
        for row in cases:
            self.assertFalse(row["injury_weather_or_coaching_cause_verified"])
            self.assertIsNotNone(row["model_minus_book_brier"])
            self.assertTrue(isinstance(row["largest_score_form_terms"],list))
            self.assertGreaterEqual(row["home_prior_games"],0)
            self.assertGreaterEqual(row["away_prior_games"],0)


if __name__=="__main__":
    unittest.main()
