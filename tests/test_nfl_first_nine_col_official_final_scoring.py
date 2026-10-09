"""NFL moneyline original same-quote three probabilities vs later ESPN Final."""
from __future__ import annotations
import copy,json,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

from intelligence_warehouse.historical_recovery.nfl_nine_col_official_scoring import (
    score_original_nfl_games_against_verified_final,
    append_first_true_nfl_market_comparisons,
    score_cycle,
)

FIRST=datetime(2026,10,11,17,tzinfo=timezone.utc)
FINAL=datetime(2026,10,12,14,tzinfo=timezone.utc)
OBS=FINAL+timedelta(minutes=1)

def forecast(id='401872982',home='MIA',away='CIN',raw=.52,base=.55,model=.56):
    return {
        'schema':'NFL_2026_FIRST_RESEARCH_NINE_FEATURE_SAME_NEW_QUOTE_MARKET_COMPARISON_V1',
        'official_espn_event_id':id,'season':2026,'week':5,
        'home_team':home,'away_team':away,
        'source_first_real_future_prediction_frozen_at_utc':'2026-10-09T01:41:00Z',
        'source_context_features_frozen_at_utc':'2026-10-09T01:33:00Z',
        'source_qualified_book_quote_updated_at_utc':'2026-10-09T01:40:40Z',
        'official_first_pitch_utc':FIRST.isoformat(),
        'original_raw_book_home_fair':raw,
        'market_only_calibrated_home_win_prob':base,
        'nine_feature_score_form_home_win_prob':model,
        'source_frozen_model_sha256':'a'*64,
        'source_independent_2026_final_games_sha256':'b'*64,
        'source_book_name':'draftkings',
        'source_provider':'sportwizzard',
        'source_is_game_moneyline_not_player_proposition':True,
        'research_only':True,'betting_play_approved':False,'sportsbook_wager_created':False,
        'predicted_market_advantage_proven':False,
    }

def final(id='401872982',home='MIA',away='CIN',home_points=20,away_points=14):
    return {
        'schema':'NFL_2026_ESPN_GAME_ID_SCORE_FINAL_SOURCE_MATCH_V1',
        'official_espn_game_id':id,'season':2026,'week':5,
        'home_team':home,'away_team':away,
        'home_points':home_points,'away_points':away_points,
        'source_first_pitch_utc':FIRST.isoformat(),
        'final_observed_at_utc':FINAL.isoformat(),
        'official_espn_final_confirmed':True,
        'source_weekly_espn_payload_sha256':'c'*64,
        'source_season_schedule_sha256':'d'*64,
        'market_model_or_wager_created':False,
    }

class NFLRealAfterFinalModelComparisonTests(unittest.TestCase):
    def test_true_official_final_game_same_book_scores_three_first_frozen_probabilities(self):
        f=[forecast(raw=.6,base=.62,model=.63),
           forecast(id='401872983',home='NYJ',away='CLE',raw=.55,base=.54,model=.52)]
        g=[final(home_points=24,away_points=17),
           final(id='401872983',home='NYJ',away='CLE',home_points=14,away_points=28)]
        rows,summary=score_original_nfl_games_against_verified_final(f,g,now=OBS)
        self.assertEqual(len(rows),2)
        self.assertEqual(summary['independent_final_game_blocks'],2)
        self.assertEqual(summary['source_pairs_scored'],2)
        self.assertAlmostEqual(summary['raw_book_brier'],(.4**2+.55**2)/2,7)
        self.assertAlmostEqual(summary['market_only_brier'],(.38**2+.54**2)/2,7)
        self.assertAlmostEqual(summary['score_form_brier'],(.37**2+.52**2)/2,7)
        self.assertEqual(summary['remaining_final_games_to_first_floor'],28)
        self.assertFalse(summary['market_advantage_statistically_proven'])
        self.assertFalse(summary['live_play_approved'])

    def test_unfinalized_or_future_score_never_becomes_graded_loss(self):
        rows,status=score_original_nfl_games_against_verified_final([forecast()],[],now=OBS)
        self.assertEqual(rows,[])
        self.assertEqual(status['ungraded_future_game_forecasts'],1)
        self.assertEqual(status['status'],'WAITING_FOR_INDEPENDENT_OFFICIAL_FINAL_NFL_GAME')

    def test_tie_not_a_home_loss_and_never_a_normal_binary_win_label(self):
        rows,status=score_original_nfl_games_against_verified_final([forecast()],
                   [final(home_points=23,away_points=23)],now=OBS)
        self.assertEqual(rows,[])
        self.assertEqual(status['official_final_tie_games_held_separately'],1)

    def test_kickoff_already_passed_at_original_model_freeze_is_not_prospective(self):
        p=forecast()
        p['source_first_real_future_prediction_frozen_at_utc']=(FIRST+timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(ValueError,'pregame'):
            score_original_nfl_games_against_verified_final([p],[final()],now=OBS)
        p=forecast()
        p['source_qualified_book_quote_updated_at_utc']='2026-10-09T01:31:00Z'
        with self.assertRaisesRegex(ValueError,'original.*before|before kickoff'):
            score_original_nfl_games_against_verified_final([p],[final()],now=OBS)

    def test_wrong_game_team_week_id_and_duplicate_provider_grade_fail(self):
        with self.assertRaisesRegex(ValueError,'team'):
            score_original_nfl_games_against_verified_final([forecast()],
                 [final(home='BUF')],now=OBS)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            score_original_nfl_games_against_verified_final([forecast(),forecast()],
                 [final()],now=OBS)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            score_original_nfl_games_against_verified_final([forecast()],
                 [final(),final()],now=OBS)

    def test_late_unknown_or_unverified_final_rejected(self):
        future=final()
        future['final_observed_at_utc']=(OBS+timedelta(minutes=2)).isoformat()
        with self.assertRaisesRegex(ValueError,'after|future'):
            score_original_nfl_games_against_verified_final([forecast()],[future],now=OBS)
        unverified=final();unverified['official_espn_final_confirmed']=False
        with self.assertRaisesRegex(ValueError,'Final'):
            score_original_nfl_games_against_verified_final([forecast()],[unverified],now=OBS)

    def test_first_settled_nfl_game_source_immutable_profits_unproven(self):
        first,_=score_original_nfl_games_against_verified_final([forecast()],[final()],now=OBS)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'FROZEN_NFL_GAME_SCORES.jsonl'
            self.assertEqual(append_first_true_nfl_market_comparisons(path,first),1)
            original=path.read_bytes()
            self.assertEqual(append_first_true_nfl_market_comparisons(path,first),0)
            changed=copy.deepcopy(first)
            changed[0]['official_home_points']=300
            with self.assertRaisesRegex(ValueError,'conflict'):
                append_first_true_nfl_market_comparisons(path,changed)
            self.assertEqual(path.read_bytes(),original)

    def test_temporary_simulated_final_score_can_run_full_cycle_without_real_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);pred=root/'PREQUOTE.jsonl';official=root/'FINAL.jsonl';graded=root/'GRADE.jsonl'
            pred.write_text(json.dumps(forecast())+'\n');official.write_text('')
            pending=score_cycle(pred,official,graded,now=FIRST-timedelta(hours=1))
            self.assertEqual(pending['newly_scored_final_games'],0)
            self.assertFalse(graded.exists())
            official.write_text(json.dumps(final())+'\n')
            completed=score_cycle(pred,official,graded,now=OBS)
            self.assertEqual(completed['newly_scored_final_games'],1)
            again=score_cycle(pred,official,graded,now=OBS+timedelta(minutes=1))
            self.assertEqual(again['newly_scored_final_games'],0)
            self.assertEqual(len(graded.read_text().splitlines()),1)

if __name__=='__main__':unittest.main()
