"""Three pre-frozen MLB hits probabilities compared with source-verified Final."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

from intelligence_warehouse.historical_recovery.mlb_restricted_speed_walk_official_scoring import (
    compare_restricted_vs_market_after_final,append_first_restricted_model_scores,score_cycle,
)

FIRST=datetime(2026,10,9,0,0,tzinfo=timezone.utc)
FINAL=datetime(2026,10,9,10,0,tzinfo=timezone.utc)
LINEUP_SHA='a'*64
MODEL_SHA='f'*64
CONTROL_SHA='c'*64

def restricted(pid=501,p=.57,game=849832,quote=.54,market=.55):
    return {
        'schema':'MLB_V2_RESTRICTED_2025_SPEED_BAT_WALKS_TRUE_FORWARD_SHADOW_V1',
        'game_pk':game,'mlbam_player_id':pid,'market_metric':'hits','line':.5,
        'model_coefficients_frozen_sha256':MODEL_SHA,
        'original_market_control_sha256':CONTROL_SHA,
        'original_source_lineup_sha256':LINEUP_SHA,
        'source_original_market_quote_at_utc':'2026-10-08T21:45:56Z',
        'market_fair_over_at_original_quote':quote,
        'market_only_calibrated_over_at_original_quote':market,
        'calibrated_restricted_speed_walk_probability_over':p,
        'first_prospective_prediction_frozen_at_utc':'2026-10-08T22:18:27Z',
        'original_game_start_at_utc':FIRST.isoformat(),
        'full_context_model_used':False,'live_play_approved':False,'wager_executed':False,
        'advanced_edge_proven':False,
        'prior_2025_sprint_observed':True,'prior_2025_bat_observed':True,
        'prior_walk5_asof_available':True,
    }

def control(pid=501,p=.54,market=.55,game=849832):
    return {
        'schema':'MLB_V2_TRUE_FORWARD_MARKET_ONLY_CALIBRATION_SHADOW_V1',
        'game_pk':game,'mlbam_player_id':pid,'market_metric':'hits','line':.5,
        'raw_no_vig_market_probability_over':p,
        'calibrated_market_control_probability_over':market,
        'source_original_lineup_sha256':LINEUP_SHA,
        'frozen_shadow_at_utc':'2026-10-08T21:59:44Z',
        'actual_game_event_start_utc':FIRST.isoformat(),
        'baseline_model_coefficients_sha256':CONTROL_SHA,
        'betting_play_authorized':False,'wager_submitted':False,
    }

def official(pid=501,hits=2,game=849832):
    return {
        'schema':'MLB_V2_OFFICIAL_FINAL_FORWARD_RESEARCH_LABEL_V1',
        'official_game_pk':game,'player_id':pid,
        'official_hits':hits,
        'original_source_line_sha256':LINEUP_SHA,
        'official_final_status_from_mlb_master':'Final',
        'official_outcome_checked_at_utc':FINAL.isoformat(),
        'sportsbook_bet_settled':False,
        'model_win_or_probability_qualified':False,
        'live_play_approved':False,
    }


class RestrictedAdvancedTrueForwardTest(unittest.TestCase):
    def test_all_three_prediction_scores_same_original_official_hit_result(self):
        rows,summary=compare_restricted_vs_market_after_final(
            [restricted(),restricted(pid=502,p=.48,quote=.51,market=.52)],
            [control(),control(pid=502,p=.51,market=.52)],
            [official(),official(pid=502,hits=0)],now=FINAL+timedelta(minutes=1)
        )
        self.assertEqual(len(rows),2)
        self.assertEqual(summary['source_true_independent_game_blocks'],1)
        self.assertEqual(summary['official_player_hit_events_scored'],2)
        self.assertEqual(summary['statistically_proven_enhanced_market_edge'],False)
        self.assertEqual(summary['remaining_game_blocks_to_first_evidence_floor'],29)
        self.assertEqual(summary['model_scope'],'LIMITED_PRIOR_2025_SPEED_BAT_WALKS_NOT_FULL_PITCHER_PARK_16')
        self.assertAlmostEqual(summary['raw_no_vig_market_brier'],(.46**2+.51**2)/2,places=6)
        self.assertAlmostEqual(summary['market_only_control_brier'],(.45**2+.52**2)/2,places=6)
        self.assertAlmostEqual(summary['restricted_speed_walk_brier'],(.43**2+.48**2)/2,places=6)
        self.assertFalse(rows[0]['sportsbook_wager_executed'])

    def test_no_true_official_final_result_yet_is_pending_not_a_loss(self):
        rows,summary=compare_restricted_vs_market_after_final([restricted()],[control()],[],now=FINAL)
        self.assertEqual(rows,[])
        self.assertEqual(summary['ungraded_restricted_player_forecasts'],1)
        self.assertEqual(summary['status'],'AWAITING_VERIFIED_FINAL_OFFICIAL_MLB_HITS')

    def test_invalid_source_chain_mismatched_player_and_unknown_grade_rejected(self):
        r=restricted()
        r['original_source_lineup_sha256']='9'*64
        with self.assertRaisesRegex(ValueError,'lineup.*SHA|[Oo]riginal'):
            compare_restricted_vs_market_after_final([r],[control()],[official()],now=FINAL+timedelta(minutes=1))
        wrong=official(pid=502)
        out,summary=compare_restricted_vs_market_after_final([restricted()],[control()],[wrong],now=FINAL+timedelta(minutes=1))
        self.assertEqual(out,[])
        self.assertEqual(summary['ungraded_restricted_player_forecasts'],1)
        with self.assertRaisesRegex(ValueError,'market-only.*source|missing.*market'):
            compare_restricted_vs_market_after_final([restricted()],[],[official()],now=FINAL+timedelta(minutes=1))

    def test_outcome_cannot_precede_first_pitch_or_shadow_freeze(self):
        future=restricted()
        future['first_prospective_prediction_frozen_at_utc']=(FIRST+timedelta(minutes=2)).isoformat()
        with self.assertRaisesRegex(ValueError,'pregame'):
            compare_restricted_vs_market_after_final([future],[control()],[official()],now=FINAL)
        g=official()
        g['official_outcome_checked_at_utc']=(FIRST-timedelta(minutes=30)).isoformat()
        with self.assertRaisesRegex(ValueError,'Final.*after|[Oo]fficial.*after'):
            compare_restricted_vs_market_after_final([restricted()],[control()],[g],now=FINAL)

    def test_duplicate_source_graded_player_and_changed_first_result_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):
            compare_restricted_vs_market_after_final([restricted(),restricted()],[control()],[official()],now=FINAL)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            compare_restricted_vs_market_after_final([restricted()],[control()],[official(),official()],now=FINAL)
        rows,_=compare_restricted_vs_market_after_final([restricted()],[control()],[official()],now=FINAL+timedelta(minutes=1))
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/'SCORES.jsonl'
            self.assertEqual(append_first_restricted_model_scores(dest,rows),1)
            before=dest.read_bytes()
            self.assertEqual(append_first_restricted_model_scores(dest,rows),0)
            self.assertEqual(dest.read_bytes(),before)
            modified=[{**rows[0],'official_hits':0,'actual_hits_over_0_5':0}]
            with self.assertRaisesRegex(ValueError,'conflict'):
                append_first_restricted_model_scores(dest,modified)
            self.assertEqual(dest.read_bytes(),before)

    def test_real_cycle_before_game_has_no_fake_new_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            adv=root/'ADV.jsonl';market=root/'MARKET.jsonl';labels=root/'OFFICIAL.jsonl';scores=root/'SCORES.jsonl'
            adv.write_text(json.dumps(restricted())+'\n')
            market.write_text(json.dumps(control())+'\n')
            labels.write_text('')
            result=score_cycle(adv,market,labels,scores,now=FIRST-timedelta(minutes=20))
            self.assertEqual(result['newly_scored_restricted_research_rows'],0)
            self.assertEqual(result['source_true_independent_game_blocks'],0)
            self.assertFalse(scores.exists())
            labels.write_text(json.dumps(official())+'\n')
            finished=score_cycle(adv,market,labels,scores,now=FINAL+timedelta(minutes=1))
            self.assertEqual(finished['newly_scored_restricted_research_rows'],1)
            self.assertEqual(finished['source_true_independent_game_blocks'],1)
            again=score_cycle(adv,market,labels,scores,now=FINAL+timedelta(minutes=5))
            self.assertEqual(again['newly_scored_restricted_research_rows'],0)

if __name__=='__main__':unittest.main()
