"""Reject incompatible DraftKings-formatted sports data before shadow learning."""
import unittest
from datetime import datetime,timedelta,timezone

from intelligence_warehouse.historical_recovery.draftkings_stat_definition_gate import (
    check_game_yards,assess_team_ppg,pregame_feature_admission,score_fixture_match,
)

OFFICIAL={
    "away":"KC","home":"LV","kickoff_utc":"2026-10-04T20:25:00Z",
    "away_points":30,"home_points":27,"final":True,
    "away_net_yards":399,
}
DK={
    "away":"KC","home":"LV","kickoff_utc":"2026-10-04T20:25:00Z",
    "away_points":30,"home_points":27,"final":True,
    "away_total_yards":407,"away_passing_yards":218,
    "away_rushing_yards":189,
}


class DraftKingsExternalStatsGateTests(unittest.TestCase):
    def test_real_oct4_same_final_different_yardage_semantics(self):
        r=check_game_yards(official=OFFICIAL,external=DK)
        self.assertEqual(r["status"],"QUARANTINE_POSSIBLE_GROSS_VS_NET_STAT_DEFINITION")
        self.assertEqual(r["external_pass_plus_rush_yards"],407)
        self.assertEqual(r["official_net_yards"],399)
        self.assertEqual(r["yardage_difference"],8)
        self.assertTrue(r["same_fixture_and_final_score"])
        self.assertFalse(r["training_admitted"])

    def test_same_points_not_enough_to_prove_game_identity_or_allow_training(self):
        for fake in [
            {**DK,"away":"NE"},
            {**DK,"home":"NE"},
            {**DK,"kickoff_utc":"2026-10-05T20:25:00Z"},
            {**DK,"away_points":27},
            {**DK,"final":False},
        ]:
            with self.subTest(fake=fake):
                self.assertFalse(score_fixture_match(OFFICIAL,fake))
                self.assertEqual(check_game_yards(official=OFFICIAL,external=fake)["status"],
                                 "QUARANTINE_UNVERIFIED_GAME_IDENTITY_OR_SCORE")

    def test_same_number_might_still_be_different_stat_definition(self):
        near={**DK,"away_total_yards":399,"away_passing_yards":210}
        r=check_game_yards(official=OFFICIAL,external=near)
        self.assertEqual(r["status"],"SOURCE_NUMBERS_AGREE_SEMANTICS_NOT_INDEPENDENTLY_VERIFIED")
        self.assertFalse(r["training_admitted"])

    def test_external_total_conflicting_with_own_passing_rushing_invalid(self):
        fake={**DK,"away_total_yards":410}
        r=check_game_yards(official=OFFICIAL,external=fake)
        self.assertEqual(r["status"],"QUARANTINE_EXTERNAL_TOTAL_INTERNAL_INCONSISTENCY")
        self.assertFalse(r["training_admitted"])

    def test_missing_stats_or_nonfinite_stats_fail_closed(self):
        for bad in [None,"",float("nan"),float("inf")]:
            with self.subTest(value=bad):
                fake={**DK,"away_passing_yards":bad}
                r=check_game_yards(official=OFFICIAL,external=fake)
                self.assertFalse(r["training_admitted"])
                self.assertEqual(r["status"],"QUARANTINE_MISSING_YARDAGE_DEFINITION")

    def test_draftkings_season_points_offense_and_official_scoreboard_are_not_proven_same_metric(self):
        lv=assess_team_ppg(
            official_game_scores=[27,26,35,27],external_ppg=28.2,scope=None
        )
        ne=assess_team_ppg(
            official_game_scores=[10,20,6,29],external_ppg=14.8,scope=None
        )
        self.assertEqual(lv["official_scoreboard_ppg"],28.75)
        self.assertEqual(ne["official_scoreboard_ppg"],16.25)
        for x in (lv,ne):
            self.assertEqual(x["status"],"QUARANTINE_SCOPE_OR_DENOMINATOR_UNKNOWN")
            self.assertFalse(x["training_admitted"])
        explicit=assess_team_ppg(official_game_scores=[10,20,6,29],
              external_ppg=14.8,scope="SCOREBOARD_TOTAL_POINTS_PER_COMPLETED_REGULAR_SEASON_GAME")
        self.assertEqual(explicit["status"],"QUARANTINE_OFFICIAL_SCOREBOARD_CONFLICT")

    def test_external_snapshot_after_game_cannot_be_added_as_pregame_predictor(self):
        kwargs=dict(source_received_at="2026-10-09T21:50:00-04:00",
            target_kickoff="2026-10-04T16:25:00-04:00",
            source_event_id="974082",official_event_id="401872976",
            official_match_verified=True,competition_phase="REGULAR",
            metric_semantics_verified=True,already_completed_games=10)
        r=pregame_feature_admission(**kwargs)
        self.assertIn("MISSING_OR_POSTSTART_PREGAME_CAPTURE",r["blocking_reasons"])
        self.assertFalse(r["source_value_used_for_training"])

    def test_outcome_predictor_fails_missing_identity_semantics_phase_and_window(self):
        r=pregame_feature_admission(
            source_received_at="2026-10-09T22:25:00-04:00",
            target_kickoff="2026-10-11T13:00:00-04:00",
            source_event_id="974090",official_event_id="401872986",
            official_match_verified=False,competition_phase="UNKNOWN",
            metric_semantics_verified=False,already_completed_games=4,rolling_window=5
        )
        self.assertEqual(r["status"],"QUARANTINE_EXTERNAL_MODEL_INPUT")
        self.assertEqual(set(r["blocking_reasons"]),{
           "EVENT_ID_NOT_INDEPENDENTLY_MATCHED",
           "UNVERIFIED_COMPETITION_PHASE",
           "METRIC_DEFINITION_UNKNOWN",
           "INSUFFICIENT_PREVIOUS_GAMES_FOR_WINDOW",
        })

    def test_even_eligible_cannot_go_directly_to_live_predictions(self):
        r=pregame_feature_admission(
            source_received_at="2026-10-09T22:25:00-04:00",
            target_kickoff="2026-10-11T13:00:00-04:00",
            source_event_id="974090",official_event_id="401872986",
            official_match_verified=True,competition_phase="REGULAR",
            metric_semantics_verified=True,already_completed_games=10,rolling_window=5
        )
        self.assertEqual(r["status"],"SOURCE_CANDIDATE_ELIGIBLE_FOR_FURTHER_ASOF_AUDIT")
        self.assertFalse(r["source_value_used_for_training"])
        self.assertFalse(r["independent_model_edge_proven"])


if __name__=="__main__":
    unittest.main()
