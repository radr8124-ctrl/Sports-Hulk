"""Strict official Final only: compare 16-feature model to SAME new quote baseline."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import copy
import tempfile
import unittest

from intelligence_warehouse.historical_recovery.mlb_full16_forward_official_scoring import (
    score_after_original_final,
    append_immutable_full16_scores,
    score_cycle,
)

NOW=datetime(2026,10,9,9,0,tzinfo=timezone.utc)
GAME=datetime(2026,10,9,0,0,tzinfo=timezone.utc)
SHA='b'*64


def source(pid=501,over=.58,market=.59,full=.60,game=849832):
    return {
        'schema':'MLB_V4_FULL_16_FEATURE_PREQUOTE_POST_CONTEXT_SAME_BOOK_SHADOW_V1',
        'official_game_pk':game,'mlbam_player_id':pid,
        'market_metric':'hits','line':.5,
        'market_fair_prob_at_exact_new_quote':over,
        'market_only_calibrated_prob_at_same_new_quote':market,
        'sixteen_feature_context_shadow_prob':full,
        'source_quote_at_utc':'2026-10-08T23:27:30Z',
        'source_team_context_frozen_at_utc':'2026-10-08T23:23:22Z',
        'first_full_context_shadow_frozen_at_utc':'2026-10-08T23:28:06Z',
        'official_first_pitch_utc':GAME.isoformat(),
        'original_lineup_sha256':SHA,
        'frozen_prejuly_model_sha256':'a'*64,
        'selected_sportsbook':'draftkings',
        'full_context_is_pre_first_pitch_source_frozen':True,
        'betting_play_approved':False,'wager_executed':False,
        'full_context_is_pre_first_pitch_source_frozen':True,
        'full_context_is_after_first_earlier_price_not_backdated':True,
        'model_16_features':[1.,.5]+[.2]*14,
        'model_market_edge_proven':False,
    }


def official(pid=501,hits=1,game=849832):
    return {
        'schema':'MLB_V2_OFFICIAL_FINAL_FORWARD_RESEARCH_LABEL_V1',
        'official_game_pk':game,'player_id':pid,
        'original_source_line_sha256':SHA,
        'official_final_status_from_mlb_master':'Final',
        'official_outcome_checked_at_utc':NOW.isoformat(),
        'official_hits':float(hits),
        'sportsbook_bet_settled':False,
        'model_win_or_probability_qualified':False,
        'live_play_approved':False,
    }


class Full16SourceTimeFinalLearningTests(unittest.TestCase):
    def test_official_0_5_hits_event_brier_and_logloss_all_same_original_quote(self):
        rows,meta=score_after_original_final(
            [source(pid=501,over=.6,market=.61,full=.62),
             source(pid=502,over=.55,market=.54,full=.50)],
            [official(pid=501,hits=2),official(pid=502,hits=0)],now=NOW+timedelta(minutes=1),
        )
        self.assertEqual(len(rows),2)
        self.assertEqual(meta['independent_official_game_blocks'],1)
        self.assertEqual(meta['source_player_comparisons'],2)
        self.assertAlmostEqual(meta['book_raw_brier'],(.4**2+.55**2)/2,places=7)
        self.assertAlmostEqual(meta['market_only_brier'],(.39**2+.54**2)/2,places=7)
        self.assertAlmostEqual(meta['full16_brier'],(.38**2+.50**2)/2,places=7)
        self.assertFalse(meta['profitable_market_edge_qualified'])
        self.assertFalse(meta['play_authorized'])
        self.assertEqual(meta['sample_floor_independent_games'],30)
        self.assertEqual(meta['games_remaining_until_first_floor'],29)
        self.assertEqual(rows[0]['actual_hits_over_half'],1)
        self.assertEqual(rows[1]['actual_hits_over_half'],0)

    def test_before_official_result_never_creates_false_losses(self):
        rows,meta=score_after_original_final([source() ],[],now=NOW)
        self.assertEqual(rows,[])
        self.assertEqual(meta['pending_ungraded_player_forecasts'],1)
        self.assertEqual(meta['status'],'WAITING_FOR_AUTHENTIC_MLB_FINAL_PLAYER_HITS')

    def test_wrong_lineup_sha_disqualified_and_other_player_missing_is_pending(self):
        bad=official();bad['original_source_line_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'original.*SHA'):
            score_after_original_final([source()],[bad],now=NOW+timedelta(minutes=1))
        missing,meta=score_after_original_final([source(pid=501)],[official(pid=502)],now=NOW+timedelta(minutes=1))
        self.assertEqual(missing,[])
        self.assertEqual(meta['pending_ungraded_player_forecasts'],1)

    def test_future_postgame_16model_or_prices_refused_without_mutation(self):
        bad=source()
        bad['first_full_context_shadow_frozen_at_utc']='2026-10-09T00:01:00Z'
        with self.assertRaisesRegex(ValueError,'pregame'):
            score_after_original_final([bad],[official()],now=NOW+timedelta(minutes=1))
        bad=source()
        bad['source_quote_at_utc']='2026-10-08T23:22:00Z'
        with self.assertRaisesRegex(ValueError,'context/quote/forecast.*before'):
            score_after_original_final([bad],[official()],now=NOW+timedelta(minutes=1))
        bad=source();bad['wager_executed']=True
        with self.assertRaisesRegex(ValueError,'research'):
            score_after_original_final([bad],[official()],now=NOW+timedelta(minutes=1))

    def test_invalid_nonfinal_or_outcome_clock_prior_kickoff_not_grading(self):
        grade=official();grade['official_final_status_from_mlb_master']='In Progress'
        with self.assertRaisesRegex(ValueError,'Final'):
            score_after_original_final([source()],[grade],now=NOW+timedelta(minutes=1))
        grade=official();grade['official_outcome_checked_at_utc']='2026-10-08T23:29:00Z'
        with self.assertRaisesRegex(ValueError,'after.*first.pitch'):
            score_after_original_final([source()],[grade],now=NOW+timedelta(minutes=1))

    def test_no_duplicate_sources_allowed_to_inflate_18_players_as_games(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):
            score_after_original_final([source(),source()],[official()],now=NOW+timedelta(minutes=1))
        with self.assertRaisesRegex(ValueError,'duplicate'):
            score_after_original_final([source()],[official(),official()],now=NOW+timedelta(minutes=1))

    def test_immutable_first_grade_cannot_be_overwritten_by_provider_corrections(self):
        rows,_=score_after_original_final([source()],[official()],now=NOW+timedelta(minutes=1))
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'OFFICIAL.jsonl'
            self.assertEqual(append_immutable_full16_scores(target,rows),1)
            before=target.read_bytes()
            self.assertEqual(append_immutable_full16_scores(target,rows),0)
            modified=copy.deepcopy(rows)
            modified[0]['official_player_hits']=0
            with self.assertRaisesRegex(ValueError,'conflict'):
                append_immutable_full16_scores(target,modified)
            self.assertEqual(target.read_bytes(),before)

    def test_private_zero_grade_cycle_then_final_grade_cycle_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            src=tmp/'MODEL.jsonl';grade=tmp/'FINAL.jsonl';out=tmp/'GRADE.jsonl'
            src.write_text(json.dumps(source())+'\n')
            grade.write_text('')
            before=score_cycle(src,grade,out,now=NOW)
            self.assertEqual(before['newly_official_player_results_compared'],0)
            self.assertEqual(before['independent_official_game_blocks'],0)
            self.assertFalse(out.exists())
            grade.write_text(json.dumps(official())+'\n')
            first=score_cycle(src,grade,out,now=NOW+timedelta(minutes=1))
            self.assertEqual(first['newly_official_player_results_compared'],1)
            self.assertEqual(first['independent_official_game_blocks'],1)
            repeat=score_cycle(src,grade,out,now=NOW+timedelta(minutes=2))
            self.assertEqual(repeat['newly_official_player_results_compared'],0)
            self.assertEqual(len(out.read_text().splitlines()),1)

if __name__=='__main__':
    unittest.main()
