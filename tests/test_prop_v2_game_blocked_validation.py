"""Forward model validation must isolate game blocks and source-available outcomes."""
import unittest

import pandas as pd

from intelligence_warehouse.betting_v2 import build_prop_v2 as v2

UTC = pd.Timestamp("2026-01-01T00:00:00Z")


def sample(games=42, forecasts_per_game=4, *, spacing_hours=24):
    rows = []
    for index in range(games):
        base = UTC + pd.Timedelta(hours=index * spacing_hours)
        start = base + pd.Timedelta(hours=8)
        for j in range(forecasts_per_game):
            rows.append({
                "block_key": "NHL|PROP|game|" + str(index),
                "time": base + pd.Timedelta(minutes=2 * j),
                "event_start": start,
                "outcome": (index + j) % 2,
                "market_logit": 0.02 * index,
                "score_z": 0.0,
                "context_signal": 0.0,
                "market_probability": 0.52,
                "market_raw_probability": 0.52,
                "devig_probability": 0.52,
            })
    return pd.DataFrame(rows).sort_values("time").reset_index(drop=True)


class ActualGameBlockedFoldTests(unittest.TestCase):
    def test_no_same_game_in_train_and_test_and_no_future_training_results(self):
        frame = sample(44)
        folds = v2.game_blocked_rolling_origin_folds(frame)
        self.assertGreater(len(folds), 0)
        tested = set()
        for train, test in folds:
            train_ids = set(train.block_key)
            test_ids = set(test.block_key)
            self.assertFalse(train_ids.intersection(test_ids))
            self.assertFalse(tested.intersection(test_ids))
            tested.update(test_ids)
            self.assertGreaterEqual(len(train_ids), 15)
            self.assertLess(
                train.time.max(),
                test.time.min(),
            )
            self.assertLessEqual(
                train.event_start.max() + pd.Timedelta(hours=24),
                test.time.min(),
            )
            # A game never contributes only a selected handful of test legs.
            self.assertTrue(test.groupby("block_key").size().eq(4).all())

    def test_contemporaneous_unfinished_games_never_train(self):
        frame = sample(42, spacing_hours=1)
        self.assertEqual(v2.game_blocked_rolling_origin_folds(frame), [])

    def test_conflicting_game_kickoff_is_quarantined_entirely(self):
        frame = sample(42)
        mismatch = frame.block_key.eq("NHL|PROP|game|30")
        frame.loc[mismatch & frame.index.isin(frame[mismatch].index[:1]),
                  "event_start"] += pd.Timedelta(minutes=10)
        folds = v2.game_blocked_rolling_origin_folds(frame)
        self.assertTrue(folds)
        for train, test in folds:
            self.assertNotIn("NHL|PROP|game|30", set(train.block_key) | set(test.block_key))

    def test_unknown_or_postkickoff_prediction_cannot_enter_validator(self):
        frame = sample(40)
        frame.loc[0, "time"] = frame.loc[0, "event_start"]
        with self.assertRaisesRegex(ValueError, "post-kickoff"):
            v2.game_blocked_rolling_origin_folds(frame)
        frame = sample(40)
        frame.loc[0, "event_start"] = pd.NaT
        with self.assertRaisesRegex(ValueError, "missing"):
            v2.game_blocked_rolling_origin_folds(frame)

    def test_partial_final_provenance_excludes_whole_game_from_training(self):
        frame = sample(44)
        frame["final_observed_at_utc"] = frame["event_start"] + pd.Timedelta(hours=3)
        target = "NHL|PROP|game|1"
        row_id = frame.index[frame.block_key.eq(target)][0]
        frame.loc[row_id, "final_observed_at_utc"] = pd.NaT
        folds = v2.game_blocked_rolling_origin_folds(frame)
        self.assertTrue(folds)
        for train, _ in folds:
            self.assertNotIn(target, set(train.block_key))

    def test_no_model_promotion_from_mean_improvement_without_confidence(self):
        choose = v2.choose_deployment_probability_source
        self.assertEqual(choose(True, True, False, False, False), "MARKET_REFERENCE")
        self.assertEqual(choose(False, False, False, True, False), "MARKET_REFERENCE")
        self.assertEqual(choose(True, True, True, False, False), "LANE_CORE_MODEL")
        self.assertEqual(choose(False, False, False, True, True), "MARKET_CALIBRATED")

    def test_many_prop_rows_but_too_few_games_is_untrained(self):
        frame = sample(16, forecasts_per_game=25)
        result = v2.walk_forward(frame, {"features": ["context_signal"]})
        self.assertEqual(result["status"], "INSUFFICIENT_HISTORY")
        self.assertEqual(result["independent_game_blocks"], 16)
        self.assertEqual(result["minimum_independent_game_blocks"], 30)

    def test_fitted_model_never_calls_rowwise_training(self):
        frame = sample(44)
        result = v2.walk_forward(frame, {"features": ["context_signal"]})
        self.assertEqual(result["status"], "READY")
        self.assertIn("GAME_BLOCKED", result["validation_split"])
        self.assertTrue(result["fold_provenance"])
        for fold in result["fold_provenance"]:
            self.assertEqual(fold["shared_train_test_games"], 0)
            self.assertEqual(
                fold["outcome_availability"],
                "24H_POST_KICKOFF_PROXY_NOT_VERIFIED_FINAL_PUBLICATION",
            )
        self.assertNotEqual(result["historical_edge_confidence"], "SUPPORTED")

    def test_same_game_kickoff_conflicts_do_not_enter_model_training(self):
        frame = sample(42)
        original = frame.to_csv(index=False)
        bad_game = frame.block_key.eq("NHL|PROP|game|30")
        frame.loc[frame[bad_game].index[0], "event_start"] += pd.Timedelta(minutes=10)
        original_with_conflict = frame.to_csv(index=False)
        kept = v2.quarantine_conflicting_game_starts(frame)
        evidence = kept.attrs["source_quarantine"]
        self.assertEqual(evidence["conflicting_game_blocks"], 1)
        self.assertEqual(evidence["quarantined_model_rows"], 4)
        self.assertEqual(len(kept), len(frame) - 4)
        self.assertNotIn("NHL|PROP|game|30", set(kept.block_key))
        self.assertEqual(frame.to_csv(index=False), original_with_conflict)
        self.assertNotEqual(original, original_with_conflict)
        self.assertFalse(evidence["raw_graded_source_was_modified"])

    def test_minor_same_game_clock_drift_is_kept_but_not_promoted(self):
        frame = sample(40)
        idx = frame[frame.block_key.eq("NHL|PROP|game|3")].index[0]
        frame.loc[idx, "event_start"] += pd.Timedelta(minutes=2)
        kept = v2.quarantine_conflicting_game_starts(frame)
        self.assertEqual(len(kept), len(frame))
        self.assertEqual(kept.attrs["source_quarantine"]["quarantined_model_rows"], 0)
        self.assertEqual(kept.attrs["source_quarantine"]["method"],
                         "QUARANTINE_WHOLE_GAME_IF_KICKOFF_DISAGREES_OVER_3_MIN")

    def test_actual_historical_source_quarantine_is_reported(self):
        for lane in ("NHL_PROP", "NHL_PRIZEPICKS"):
            with self.subTest(lane=lane):
                hist = v2.build_history(v2.LANES[lane])
                report = hist.attrs["source_quarantine"]
                self.assertEqual(report["original_model_eligible_rows"],
                                 len(hist) + report["quarantined_model_rows"])
                self.assertFalse(report["raw_graded_source_was_modified"])
                spread = hist.groupby("block_key")["event_start"].agg(lambda x: x.max()-x.min())
                self.assertTrue(spread.le(pd.Timedelta(minutes=3)).all())

    def test_original_live_nfl_mlb_nhl_lanes_have_no_block_overlap(self):
        for lane,cfg in v2.LANES.items():
            with self.subTest(lane=lane):
                frame = v2.build_history(cfg)
                if frame.empty:
                    continue
                for train, test in v2.game_blocked_rolling_origin_folds(frame):
                    self.assertTrue(set(train.block_key).isdisjoint(set(test.block_key)))
                    self.assertLessEqual(
                        train.event_start.max() + pd.Timedelta(hours=24),
                        test.time.min(),
                    )


if __name__ == "__main__":
    unittest.main()

class FrozenGameIdentityTests(unittest.TestCase):
    def test_game_or_event_only_never_calendar_date(self):
        self.assertIsNone(v2.verified_game_block_key('NFL','PROP','',''))
        self.assertEqual(v2.verified_game_block_key('NFL','PROP','BUF@NYJ',''), 'NFL|PROP|game|BUF@NYJ')
        self.assertEqual(v2.verified_game_block_key('NFL','PROP','','event-123'), 'NFL|PROP|event|event-123')

class VerifiedFinalAvailabilityTests(unittest.TestCase):
    def test_observation_timestamp_excludes_missing_or_future_final(self):
        frame = sample(games=44)
        frame['final_observed_at_utc'] = frame['event_start'] + pd.Timedelta(hours=5)
        frame.loc[frame.block_key.eq('NHL|PROP|game|0'),'final_observed_at_utc'] = pd.NaT
        frame.loc[frame.block_key.eq('NHL|PROP|game|1'),'final_observed_at_utc'] = frame['event_start'] + pd.Timedelta(days=100)
        folds = v2.game_blocked_rolling_origin_folds(frame)
        self.assertTrue(folds)
        for train,test in folds:
            self.assertFalse(set(train.block_key).intersection({'NHL|PROP|game|0','NHL|PROP|game|1'}))
            self.assertLessEqual(train.final_observed_at_utc.max(),test.time.min())
