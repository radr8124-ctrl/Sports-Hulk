"""Hugging Face NBA published closing lines: strict source and research gates."""
import unittest
from copy import deepcopy
import numpy as np
import pandas as pd

from intelligence_warehouse.betting_v2.hf_nba_market_challenger import (
    source_verified_rows, matrix, labels, scores, winning_pct, side, norm, intervals,
)


def fixtures():
    hf=pd.DataFrame([{
        "game_id":"HF-1",
        "start_time_utc":"2025-10-21T23:30:00Z",
        "home_team":"Oklahoma City Thunder",
        "away_team":"Houston Rockets",
        "home_score":125,
        "away_score":124,
        "season_type":"regular",
        "close_total":225.5,"open_total":227.5,
        "close_spread_home":-6.5,"open_spread_home":-7.5,
        "close_over_prob":0.51,"close_home_cover_prob":0.5,
        "close_home_win_prob":0.6869,
        "open_home_win_prob":0.692,
        "close_fair_home_odds":1/0.6869,"close_fair_away_odds":1/(1-0.6869),
        "total_result":"over","ats_result":"away","moneyline_winner":"home",
    }])
    official=pd.DataFrame([{
        "event_id":401812480,"start":"2025-10-21T23:30Z",
        "season":2026,"season_type":2,"completed":True,
        "home_team_name":"Oklahoma City Thunder","away_team_name":"Houston Rockets",
        "home_score":125,"away_score":124,
    }])
    return hf,official


class TestHistoricalNbaHuggingFaceSource(unittest.TestCase):
    def test_official_exact_game_and_grade_passes(self):
        hf,official=fixtures()
        rows,report=source_verified_rows(hf,official)
        self.assertEqual(len(rows),1)
        self.assertEqual(report["verified_regular_game_rows"],1)
        self.assertEqual(rows[0]["official_home_score"],125)
        self.assertEqual(rows[0]["over_result"],"over")
        self.assertEqual(rows[0]["cover_result"],"away")
        self.assertFalse(rows[0]["book_source_verified"])

    def test_official_score_disagreement_rejected(self):
        hf,official=fixtures()
        official.loc[0,"home_score"]=124
        rows,report=source_verified_rows(hf,official)
        self.assertFalse(rows)
        self.assertEqual(report["source_rejection_counts"]["FINAL_SCORE_CONFLICT"],1)

    def test_reject_wrong_source_result_label(self):
        hf,official=fixtures()
        hf.loc[0,"ats_result"]="home"
        rows,report=source_verified_rows(hf,official)
        self.assertFalse(rows)
        self.assertEqual(report["source_rejection_counts"]["PUBLISHER_RESULT_GRADE_CONFLICT"],1)

    def test_wrong_kickoff_time_rejected(self):
        hf,official=fixtures()
        hf.loc[0,"start_time_utc"]="2025-10-21T23:38:00Z"
        rows,report=source_verified_rows(hf,official)
        self.assertFalse(rows)
        self.assertEqual(report["source_rejection_counts"]["NO_UNIQUE_OFFICIAL_MATCH"],1)

    def test_pregame_source_not_from_future_game(self):
        hf,official=fixtures()
        official.loc[0,"completed"]=False
        rows,_=source_verified_rows(hf,official)
        self.assertFalse(rows)

    def test_preseason_explicitly_excluded(self):
        hf,official=fixtures()
        hf.loc[0,"season_type"]="preseason"
        rows,report=source_verified_rows(hf,official)
        self.assertFalse(rows)
        self.assertEqual(report["source_rejection_counts"]["NOT_REGULAR_SEASON"],1)

    def test_altered_moneyline_fair_prob_rejected(self):
        hf,official=fixtures()
        hf.loc[0,"close_fair_home_odds"]=2.5
        rows,report=source_verified_rows(hf,official)
        self.assertFalse(rows)
        self.assertEqual(report["source_rejection_counts"]["SOURCE_FAIR_MONEYLINE_CONFLICT"],1)

    def test_one_hf_row_per_game_identity(self):
        hf,official=fixtures()
        hf=pd.concat([hf,hf],ignore_index=True)
        with self.assertRaisesRegex(ValueError,"DUPLICATE_PUBLISHER_GAME_IDS"):
            source_verified_rows(hf,official)

    def test_market_predictors_do_not_reference_game_results(self):
        hf,official=fixtures()
        rows,_=source_verified_rows(hf,official)
        first=matrix(rows,"NBA_TOTAL_REGULAR_SEASON",True)
        altered=[dict(rows[0],official_home_score=42,official_away_score=12,
                      over_result="under",cover_result="home",home_win_result="away")]
        second=matrix(altered,"NBA_TOTAL_REGULAR_SEASON",True)
        np.testing.assert_array_equal(first,second)
        self.assertEqual(first.shape,(1,5))

    def test_high_confidence_requires_seventy_and_honest_coverage(self):
        rows=[{"official_event_id":"game1"},{"official_event_id":"game2"}]
        out=winning_pct(rows,np.array([1.,0.]),np.array([.75,.49]))
        self.assertEqual(out["selected_games"],1)
        self.assertEqual(out["hit_rate_pct"],100.0)
        self.assertIsNone(out["profit_and_roi"])

    def test_one_game_per_historical_proof_block(self):
        rows=[{"start":"2026-03-20T00:00:00+00:00","official_event_id":"1"},
              {"start":"2026-03-21T00:00:00+00:00","official_event_id":"2"}]
        report=intervals(rows,np.asarray([.01,-.02]),100,42)
        self.assertEqual(report["independent_games"],2)
        self.assertFalse(report["statistical_advantage_proven"])

    def test_clippers_explicit_alias_only(self):
        self.assertEqual(norm("Los Angeles Clippers"),"la clippers")
        self.assertNotEqual(norm("Los Angeles Lakers"),"la clippers")


if __name__=="__main__":
    unittest.main()
