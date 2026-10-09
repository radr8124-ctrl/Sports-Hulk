"""Genuine market-control forecasts compared with later source-verified actual hits."""
from __future__ import annotations
import json,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

from intelligence_warehouse.historical_recovery.mlb_shadow_market_official_scoring import (
    score_graded_shadow_research,
    append_first_official_shadow_scores,
    score_cycle,
)

NOW=datetime(2026,10,9,10,0,tzinfo=timezone.utc)
FIRST=datetime(2026,10,9,0,0,tzinfo=timezone.utc)
LINEUP_SHA='a'*64

def shadow(pid=501,p=0.55,calibrated=0.57,game=849832):
    return {
        'schema':'MLB_V2_TRUE_FORWARD_MARKET_ONLY_CALIBRATION_SHADOW_V1',
        'game_pk':game,
        'mlbam_player_id':pid,
        'line':0.5,
        'market_metric':'hits',
        'market_subtype':'PLAYER_TOTAL_HITS',
        'frozen_shadow_at_utc':(FIRST-timedelta(hours=2)).isoformat(),
        'source_original_lineup_sha256':LINEUP_SHA,
        'raw_no_vig_market_probability_over':p,
        'calibrated_market_control_probability_over':calibrated,
        'actual_game_event_start_utc':FIRST.isoformat(),
        'baseline_model_coefficients_sha256':'b'*64,
        'proprietary_speed_walks_model_evaluated':False,
        'betting_play_authorized':False,
        'wager_submitted':False,
    }


def official(pid=501,hits=2,game=849832):
    return {
        'schema':'MLB_V2_OFFICIAL_FINAL_FORWARD_RESEARCH_LABEL_V1',
        'official_game_pk':game,
        'player_id':pid,
        'official_hits':float(hits),
        'official_game_date':'2026-10-08',
        'source_frozen_feature_at_utc':(FIRST-timedelta(hours=3)).isoformat(),
        'original_source_line_sha256':LINEUP_SHA,
        'official_final_status_from_mlb_master':'Final',
        'official_outcome_checked_at_utc':NOW.isoformat(),
        'sportsbook_bet_settled':False,
        'model_win_or_probability_qualified':False,
        'live_play_approved':False,
    }


class MLBOfficialModelVsMarketScoreTests(unittest.TestCase):
    def test_postgame_observations_score_truthful_binary_event_not_betting_win(self):
        scores,summary=score_graded_shadow_research(
            [shadow(pid=501,p=.6,calibrated=.62),shadow(pid=502,p=.5,calibrated=.53)],
            [official(pid=501,hits=1),official(pid=502,hits=0)],now=NOW
        )
        self.assertEqual(len(scores),2)
        self.assertEqual(summary['independent_games_with_settled_comparisons'],1)
        self.assertEqual(summary['settled_player_market_comparisons'],2)
        self.assertAlmostEqual(summary['market_raw_brier'],(.4**2+.5**2)/2,places=9)
        self.assertAlmostEqual(summary['market_calibrated_brier'],(.38**2+.53**2)/2,places=9)
        self.assertEqual(scores[0]['observed_player_hits'],1)
        self.assertEqual(scores[0]['hit_over_line_outcome'],1)
        self.assertEqual(scores[1]['hit_over_line_outcome'],0)
        self.assertEqual(summary['statistically_proven_market_improvement'],False)
        self.assertEqual(summary['live_play_approvals'],0)
        self.assertEqual(summary['minimum_independent_games_for_first_sample_floor'],30)
        self.assertEqual(summary['remaining_games_to_first_sample_floor'],29)

    def test_missing_unsettled_player_is_ungraded_never_fake_loss(self):
        result,summary=score_graded_shadow_research([shadow(501),shadow(502)],[official(501)],now=NOW)
        self.assertEqual(len(result),1)
        self.assertEqual(summary['ungraded_player_forecasts'],1)
        result,summary=score_graded_shadow_research([shadow(501)],[],now=NOW)
        self.assertEqual(result,[])
        self.assertEqual(summary['independent_games_with_settled_comparisons'],0)
        self.assertEqual(summary['status'],'AWAITING_NEW_FINAL_MLB_OFFICIAL_OUTCOME_EVIDENCE')

    def test_postgame_frozen_prediction_or_mismatched_original_sha_cannot_score(self):
        late=shadow()
        late['frozen_shadow_at_utc']=(FIRST+timedelta(minutes=1)).isoformat()
        with self.assertRaisesRegex(ValueError,'pregame'):
            score_graded_shadow_research([late],[official()],now=NOW)
        mismatch=official()
        mismatch['original_source_line_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'original.*source'):
            score_graded_shadow_research([shadow()],[mismatch],now=NOW)
        fake=shadow()
        fake['wager_submitted']=True
        with self.assertRaisesRegex(ValueError,'research'):
            score_graded_shadow_research([fake],[official()],now=NOW)

    def test_duplicate_player_game_shadow_rejected_and_original_result_corrections_blocked(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):
            score_graded_shadow_research([shadow(),shadow()],[official()],now=NOW)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            score_graded_shadow_research([shadow()],[official(),official()],now=NOW)

    def test_first_settled_research_score_is_immutable_across_later_provider_change(self):
        result,_=score_graded_shadow_research([shadow()],[official()],now=NOW)
        with tempfile.TemporaryDirectory() as folder:
            ledger=Path(folder)/'SCORED.jsonl'
            self.assertEqual(append_first_official_shadow_scores(ledger,result),1)
            first=ledger.read_bytes()
            self.assertEqual(append_first_official_shadow_scores(ledger,result),0)
            self.assertEqual(ledger.read_bytes(),first)
            revised,_=score_graded_shadow_research([shadow()],[official(hits=0)],now=NOW)
            with self.assertRaisesRegex(ValueError,'conflict'):
                append_first_official_shadow_scores(ledger,revised)
            self.assertEqual(ledger.read_bytes(),first)

    def test_pre_final_production_cycle_no_fabricated_calibration_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            shadow_file=root/'SHADOW.jsonl'
            grade_file=root/'OFFICIAL.jsonl'
            output=root/'SCORES.jsonl'
            shadow_file.write_text(json.dumps(shadow())+'\n')
            grade_file.write_text('')
            result=score_cycle(shadow_file,grade_file,output,now=FIRST-timedelta(minutes=2))
            self.assertEqual(result['independent_games_with_settled_comparisons'],0)
            self.assertEqual(result['newly_scored_research_rows'],0)
            self.assertFalse(output.exists())
            grade_file.write_text(json.dumps(official())+'\n')
            result=score_cycle(shadow_file,grade_file,output,now=NOW)
            self.assertEqual(result['newly_scored_research_rows'],1)
            self.assertEqual(result['independent_games_with_settled_comparisons'],1)
            again=score_cycle(shadow_file,grade_file,output,now=NOW+timedelta(minutes=5))
            self.assertEqual(again['newly_scored_research_rows'],0)
            self.assertEqual(output.read_text().count('\n'),1)
            self.assertFalse(result['commercial_betting_edge_claim_permitted'])

if __name__=='__main__':
    unittest.main()
