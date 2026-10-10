"""Proof constraints for isolated NFL 5/10/20 research; never touch live model."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import unittest

import pandas as pd

from intelligence_warehouse.historical_recovery.nfl_rolling_score_form_diagnostic import (
    SOURCE, OUTPUT, source_matrix, evaluate, WINDOWS,
)


class NFLRollingFormShadowDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_bytes=SOURCE.read_bytes()
        cls.source_sha=hashlib.sha256(cls.original_bytes).hexdigest()
        cls.frame=pd.read_csv(SOURCE,low_memory=False)
        cls.records,cls.invalid=source_matrix(cls.frame)
        cls.by_id={r["game_id"]:r for r in cls.records}

    @classmethod
    def tearDownClass(cls):
        assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==cls.source_sha

    def test_no_future_seasons_and_unique_game_blocks(self):
        self.assertEqual(len(self.by_id),len(self.records))
        self.assertTrue(all(2016<=r["season"]<=2025 for r in self.records))
        self.assertTrue(all(len(r["features"])==16 for r in self.records))
        self.assertTrue(all(r["current_week_outcome_not_in_inputs"] for r in self.records))
        self.assertGreater(len(self.records),2700)

    def test_year_openers_do_not_inherit_later_current_season_results(self):
        first=[r for r in self.records if r["season"]==2025 and r["week"]==1]
        self.assertGreater(len(first),10)
        for r in first:
            for width in WINDOWS:
                self.assertEqual(r["prior_counts"][width],(0,0))
                self.assertEqual(r["features"][{5:5,10:9,20:13}[width]],0)

    def test_changing_current_week_scores_cannot_change_that_week_features(self):
        changed=self.frame.copy(deep=True)
        current=changed.loc[(changed.season==2025)&(changed.week==1)].iloc[0]
        target=str(current.game_id)
        current_year_week=(int(current.season),int(current.week))
        changed.loc[changed.game_id==target,"home_score"]=float(current.home_score)+21
        changed.loc[changed.game_id==target,"away_score"]=float(current.away_score)+7
        altered,_=source_matrix(changed)
        altered_by_id={r["game_id"]:r for r in altered}
        for original in self.records:
            if (original["season"],original["week"])==current_year_week:
                self.assertEqual(original["features"],
                                 altered_by_id[original["game_id"]]["features"])
        # At least one later game should incorporate the changed team's
        # prior scoring, establishing that the feature collector works.
        next_games=[r for r in self.records
                    if r["season"]==2025 and r["week"]>1 and
                    (r["home"]==str(current.home_team) or
                     r["away"]==str(current.home_team))]
        self.assertGreater(len(next_games),0)
        self.assertTrue(any(r["features"]!=altered_by_id[r["game_id"]]["features"]
                            for r in next_games))

    def test_no_duplicate_or_2026_game_allowed(self):
        duplicate=pd.concat([self.frame,self.frame.iloc[[0]]],ignore_index=True)
        with self.assertRaisesRegex(ValueError,"Duplicate original"):
            source_matrix(duplicate)
        future=self.frame.copy()
        future.loc[0,"season"]=2026
        with self.assertRaisesRegex(ValueError,"Only the original"):
            source_matrix(future)

    def test_walk_forward_four_years_remain_retrospective_no_promotion(self):
        j=json.loads(OUTPUT.read_text())
        self.assertEqual(j["original_source_sha256"],self.source_sha)
        self.assertEqual(j["schema"],"NFL_ASOF_ROLLING_5_10_20_DIAGNOSTIC_V1")
        self.assertEqual(j["test_years"],[2022,2023,2024,2025])
        self.assertEqual(j["total_heldout_game_observations"],1136)
        self.assertEqual(len(j["folds"]),4)
        self.assertEqual(sum(x["test_games"] for x in j["folds"]),1136)
        self.assertTrue(all(f["training_and_test_game_ids_disjoint"] for f in j["folds"]))
        self.assertTrue(all(f["all_form_sources_prior_same_season_weeks_only"] for f in j["folds"]))
        self.assertTrue(j["historical_prices_individual_quote_timestamps_available"] is False)
        self.assertTrue(j["new_forward_2026_holdout_required"])
        self.assertFalse(j["positive_EV_or_actual_profit_proven"])
        self.assertFalse(j["live_model_promoted"])

    def test_no_false_accuracy_claim_from_rolling_form(self):
        j=json.loads(OUTPUT.read_text())
        self.assertEqual(j["folds_rolling_beats_book"],2)
        f={x["year"]:x for x in j["folds"]}
        self.assertLess(f[2025]["winner_accuracy_pct"]["rolling_5_10_20_opponent_score_form"],
                        f[2025]["winner_accuracy_pct"]["paired_book_no_vig"])
        self.assertLess(f[2025]["book_brier_minus_rolling_brier"],0)
        for x in j["folds"]:
            self.assertLess(x["paired_week_bootstrap95"][0],0)
            self.assertGreater(x["paired_week_bootstrap95"][1],0)
        self.assertEqual(j["pooled_book_minus_rolling_brier"],0.00028092)

if __name__=="__main__":
    unittest.main()
