"""Learning must explain settled mistakes without contaminating future predictions."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from intelligence_warehouse.outcome_learning import learning_core as core
from intelligence_warehouse.outcome_learning import build_outcome_learning as report

START=datetime(2026,10,11,17,tzinfo=timezone.utc)
CAPTURE=START-timedelta(days=2)
SETTLED=START+timedelta(hours=5)


def entry(key="e1",sport="NFL",market="SPREAD",side="AWAY",line=-5,
          capture=CAPTURE,start=START,p=.65,q=.65):
    return {
        "event_type":"ENTRY","forward_key":key,"model_version":"ORIGINAL",
        "captured_at":capture.isoformat(),"sport":sport,
        "lane_key":sport+"_"+market,"game_key":"KC@LV",
        "market":market,"selection_key":side,"selection":"Kansas City Chiefs",
        "line":line,"event_start":start.isoformat(),
        "entry_v2_probability_pct":100*p,"entry_market_reference_probability_pct":100*q,
        "entry_american_odds":-110,"entry_shadow_decision":"PASS_NO_PROVEN_EDGE",
    }


def result(key="e1",grade="LOSS",home=27,away=30,start=START,settled=SETTLED):
    return {
        "event_type":"SETTLED","forward_key":key,"grade":grade,
        "status":"SETTLED","home_score":home,"away_score":away,
        "settled_at":settled.isoformat(),
        "grade_snapshot_at":(start-timedelta(hours=2)).isoformat(),
        "settlement_source_event_id":"401872976",
    }


class OutcomeLearningEvidenceTests(unittest.TestCase):
    def test_chiefs_win_does_not_mean_chiefs_negative_spread_cover(self):
        r={**entry(),**result()}
        self.assertEqual(core.scored_grade(r),"LOSS")
        self.assertEqual(core.diagnosis(r)[0],"WINNER_DID_NOT_COVER")
        ml={**entry(market="MONEYLINE",line=None),**result(grade="WIN")}
        self.assertEqual(core.scored_grade(ml),"WIN")
        total={**entry(market="TOTAL",side="OVER",line=47.5),**result(grade="WIN")}
        self.assertEqual(core.scored_grade(total),"WIN")

    def test_never_guess_why_an_outcome_lost(self):
        a={**entry(),**result()}
        label,text=core.diagnosis(a)
        self.assertEqual(label,"WINNER_DID_NOT_COVER")
        self.assertNotIn("injury caused",text.lower())
        self.assertNotIn("weather caused",text.lower())

    def test_canonical_freezes_pregame_entry_and_preserves_grade_clock_distinction(self):
        saved,invalid=core.canonical([entry(),result()])
        self.assertEqual(len(saved),1)
        self.assertFalse(invalid)
        self.assertEqual(saved[0]["grade"],"LOSS")
        self.assertTrue(saved[0]["grade_snapshot_is_original_pregame_time"])
        self.assertEqual(saved[0]["original_capture_utc"],CAPTURE.isoformat())
        self.assertEqual(saved[0]["settled_at_utc"],SETTLED.isoformat())
        self.assertEqual(saved[0]["market_probability_pct"],65)
        self.assertFalse(saved[0]["independent_official_boxscore_double_checked"])

    def test_contradictory_grade_or_final_score_gets_quarantined(self):
        for modification in [
            {"grade":"WIN"},
            {"home_score":19},
        ]:
            with self.subTest(modification=modification):
                invalid_result={**result(),**modification}
                rows,reasons=core.canonical([entry(),result(),invalid_result])
                self.assertEqual(rows,[])
                self.assertEqual(reasons["QUARANTINED_CONFLICT"],1)

    def test_poststart_or_time_travel_predictions_or_results_are_excluded(self):
        r,reasons=core.canonical([entry(capture=START+timedelta(seconds=1)),result()])
        self.assertEqual(r,[])
        self.assertEqual(reasons["INVALID_PREGAME_CLOCK"],1)
        r,reasons=core.canonical([entry(),result(settled=START-timedelta(minutes=1))])
        self.assertEqual(r,[])
        self.assertEqual(reasons["INVALID_SETTLED_EVENT_CLOCK"],1)

    def test_push_vs_win_and_loss_using_exact_total_or_spread(self):
        total={**entry(market="TOTAL",side="UNDER",line=57),**result(grade="PUSH")}
        self.assertEqual(core.scored_grade(total),"PUSH")
        exact={**entry(market="SPREAD",line=-3),**result(grade="PUSH")}
        self.assertEqual(core.scored_grade(exact),"PUSH")
        exact["line"]=-2.5
        self.assertEqual(core.scored_grade(exact),"WIN")
        exact["line"]=-3.5
        self.assertEqual(core.scored_grade(exact),"LOSS")

    def test_last_predicted_entrant_cannot_replace_first_frozen_snapshot(self):
        r1=entry()
        altered={**r1,"captured_at":(CAPTURE+timedelta(hours=1)).isoformat(),
                 "entry_v2_probability_pct":99}
        r,reasons=core.canonical([r1,altered,result()])
        self.assertEqual(r,[])
        self.assertEqual(reasons["CONFLICTING_ENTRY"],1)

    def test_market_copy_stays_no_independent_edge_even_when_result_win(self):
        e=entry(market="MONEYLINE",line=None)
        r=core.canonical([e,result(grade="WIN")])[0][0]
        summary=core.lane_rollup([r])[0]
        self.assertEqual(summary["model_equal_to_market_probability_rows"],1)
        self.assertEqual(summary["market_brier_equal_game_weighted"],
                         summary["model_brier_equal_game_weighted"])
        self.assertFalse(summary["independently_proven_predictive_advantage"])


def settled_row(i,now_base=CAPTURE,market="MONEYLINE",p=55,y="WIN",
                released_early=True,game=None):
    key=f"old{i}"
    previous_start=now_base-timedelta(days=12)+(timedelta(hours=i))
    published=previous_start+timedelta(hours=4)
    if not released_early:
        published=now_base+timedelta(hours=3)
    return {
        "forward_key":key,"sport":"NFL","game_key":game or f"G{i}",
        "market":market,"grade":y,"result_source_identity_recorded":True,
        "original_start_utc":previous_start.isoformat(),
        "original_capture_utc":(previous_start-timedelta(hours=1)).isoformat(),
        "settled_at_utc":published.isoformat(),
        "market_probability_pct":p,"model_probability_pct":p,
    }


class AsOfChallengerTests(unittest.TestCase):
    def frozen(self):
        return {"forward_key":"new","sport":"NFL","market":"MONEYLINE",
                "game_key":"LAST","original_capture_utc":CAPTURE.isoformat(),
                "original_start_utc":START.isoformat(),
                "market_probability_pct":55}

    def test_shrinker_uses_only_older_settled_games_and_never_the_test_game(self):
        old=[settled_row(i) for i in range(30)]
        old2=[{**r,"forward_key":r["forward_key"]+"_2"} for r in old]
        res=core.shadow_calibration(self.frozen(),old+old2)
        self.assertEqual(res["status"],"ASOF_SHADOW_RESEARCH_ONLY")
        self.assertEqual(res["training_independent_games"],30)
        self.assertEqual(res["training_rows"],60)
        self.assertGreater(res["shadow_probability_pct"],55)
        self.assertLessEqual(res["shadow_probability_pct"],60)
        self.assertFalse(res["bet_or_automatic_production_change_created"])
        self.assertLess(core.when(res["latest_training_result_available_utc"]),CAPTURE)

    def test_no_outcome_after_original_capture_can_train_candidate(self):
        old=[settled_row(i,released_early=False) for i in range(40)]
        res=core.shadow_calibration(self.frozen(),old)
        self.assertEqual(res["status"],"WAIT_FOR_SOURCE_VALID_OUT_OF_TIME_GAMES")
        self.assertEqual(res["training_rows"],0)

    def test_nba_preseason_never_trains_on_regular_or_unverified_phase(self):
        future={**self.frozen(),"sport":"NBA","competition_regime":"PRESEASON"}
        past=[{**settled_row(i),"sport":"NBA","competition_regime":"REGULAR"} for i in range(35)]
        past+=[{**settled_row(100+i),"sport":"NBA"} for i in range(35)]
        self.assertEqual(core.shadow_calibration(future,past)["training_rows"],0)
        past=[{**settled_row(i),"sport":"NBA","competition_regime":"PRESEASON"} for i in range(35)]
        self.assertEqual(core.shadow_calibration(future,past)["training_independent_games"],35)

    def test_same_game_and_unlinked_outcome_cannot_train(self):
        old=[settled_row(i,game="LAST") for i in range(30)]
        old += [{**settled_row(100+i),"result_source_identity_recorded":False} for i in range(30)]
        res=core.shadow_calibration(self.frozen(),old)
        self.assertEqual(res["status"],"WAIT_FOR_SOURCE_VALID_OUT_OF_TIME_GAMES")

    def test_insufficient_different_games_cannot_be_stuffed_with_200_lines(self):
        old=[settled_row(i,game=f"D{i%2}") for i in range(200)]
        res=core.shadow_calibration(self.frozen(),old)
        self.assertEqual(res["training_independent_games"],2)
        self.assertEqual(res["status"],"WAIT_FOR_SOURCE_VALID_OUT_OF_TIME_GAMES")

    def test_calibration_cannot_promote_before_50_settled_shadow_rows_30_games(self):
        original=[]
        shadows=[]
        for i in range(30):
            for j in range(2):
                key=f"k{i}_{j}"
                row={**self.frozen(),"forward_key":key,"game_key":f"GAME{i}",
                     "grade":"WIN","market_probability_pct":55}
                original.append(row)
                shadows.append({
                    "status":"ASOF_SHADOW_RESEARCH_ONLY",
                    "original_forward_key":key,
                    "game_start_utc":START.isoformat(),
                    "frozen_at_utc":CAPTURE.isoformat(),
                    "shadow_probability_pct":60,
                })
        low=core.shadow_metrics(original,shadows[:10])
        self.assertEqual(low["mode"],"UNPROVEN_FORWARD_SHADOW")
        good=core.shadow_metrics(original,shadows)
        self.assertTrue(good["review_eligible"])
        self.assertEqual(good["mode"],"MANUAL_MODEL_REVIEW_ONLY")
        self.assertFalse(good["automated_live_model_adjustment_allowed"])
        self.assertFalse(good["verified_positive_expected_value_betting_proven"])


class FutureNflAutopsyTests(unittest.TestCase):
    def forecast(self):
        return {
            "official_espn_event_id":"401872986","home_team":"NE","away_team":"LV",
            "research_only":True,"betting_play_approved":False,
            "source_frozen_model_sha256":"a"*64,
            "source_first_real_future_prediction_frozen_at_utc":CAPTURE.isoformat(),
            "official_first_pitch_utc":START.isoformat(),
            "original_raw_book_home_fair":.63,
            "nine_feature_score_form_home_win_prob":.65,
        }

    def final(self):
        return {
            "schema":"NFL_2026_RESEARCH_NINE_FEATURE_SAME_BOOK_VS_INDEPENDENT_ESPN_FINAL_SCORE_V1",
            "official_espn_event_id":"401872986","home_team":"NE","away_team":"LV",
            "research_only":True,"sportsbook_wager_executed":False,
            "profitable_market_edge_proven":False,
            "original_model_sha256":"a"*64,
            "source_real_original_final_observed_at_utc":SETTLED.isoformat(),
            "official_home_points":21,"official_away_points":24,
            "original_home_moneyline_win_binary_outcome":0,
            "score_form_original_pregame_home_win_probability":.65,
            "raw_book_original_pregame_home_win_probability":.63,
            "score_form_squared_error":.4225,"raw_book_squared_error":.3969,
        }

    def test_real_postgame_candidate_catches_market_assisted_favorite_loss(self):
        review=report.nfl_first13_error_review([self.forecast()],[self.final()])
        self.assertEqual(review["independently_verified_graded_games"],1)
        self.assertEqual(review["wrong_winner_count"],1)
        self.assertEqual(review["individual_games"][0]["predicted_winner"],"NE")
        self.assertEqual(review["individual_games"][0]["actual_winner"],"LV")
        self.assertEqual(review["individual_games"][0]["observed_error_type"],"WRONG_MONEYLINE_WINNER")
        self.assertFalse(review["individual_games"][0]["feature_root_cause_verified"])
        self.assertGreater(review["individual_games"][0]["model_minus_book_brier"],0)

    def test_real_future_original_has_no_final_before_game(self):
        res=report.nfl_first13_error_review([self.forecast()],[])
        self.assertEqual(res["independently_verified_graded_games"],0)
        self.assertEqual(res["pending_original_nfl_games"],1)
        self.assertEqual(res["individual_games"],[])

    def test_source_relabel_or_tamper_is_quarantined_not_learned(self):
        for delta in [
            {"home_team":"BUF"},
            {"original_model_sha256":"b"*64},
            {"score_form_original_pregame_home_win_probability":.61},
            {"source_real_original_final_observed_at_utc":(START-timedelta(minutes=1)).isoformat()},
            {"sportsbook_wager_executed":True},
            {"official_home_points":28},
        ]:
            with self.subTest(change=delta):
                bad={**self.final(),**delta}
                with self.assertRaises(ValueError):
                    report.nfl_first13_error_review([self.forecast()],[bad])


class AuthenticRecordedGameTests(unittest.TestCase):
    def test_oct4_original_research_scores_are_not_calibrated_probabilities(self):
        source=report.GRADED_NFL.read_bytes()
        case=report.score_week4_case(source)
        self.assertEqual(case["status"],"ARCHIVED_PREGAME_RESEARCH_ONLY")
        self.assertEqual(case["number_of_original_game_market_cases"],3)
        result={v["market"]:v for v in case["original_cases"]}
        self.assertEqual([result[m]["grade"] for m in ["MONEYLINE","SPREAD","TOTAL"]],
                         ["WIN","LOSS","WIN"])
        self.assertEqual(result["SPREAD"]["line"],-5)
        self.assertEqual(result["SPREAD"]["diagnostic_code"],"WINNER_DID_NOT_COVER")
        self.assertFalse(case["postgame_feature_cause_proven"])
        self.assertFalse(result["MONEYLINE"]["model_nine_feature_forecast_replayed_from_2026_week4"])

    def test_authentic_forward_passes_without_rewriting_original_ledger(self):
        before=report.ORIGINAL.read_bytes()
        current,queued,sha=report.generate()
        after=report.ORIGINAL.read_bytes()
        self.assertEqual(before,after)
        self.assertEqual(sha,__import__("hashlib").sha256(before).hexdigest())
        self.assertEqual(current["snapshot"]["market_based_predictions_same_as_market"],
                         current["snapshot"]["valid_settled_market_research"])
        self.assertEqual(current["snapshot"]["live_new_model_adjustments_applied"],0)
        self.assertTrue(current["snapshot"]["distinct_settled_game_blocks"]>=30)
        self.assertFalse(current["frozen_forward_challenger_score"]["review_eligible"])
        self.assertEqual(queued,[])


if __name__=="__main__":
    unittest.main()
