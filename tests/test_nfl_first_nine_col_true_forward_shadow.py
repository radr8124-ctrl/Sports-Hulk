"""First fixed NFL market-vs-score-form same-quote source-time research only."""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
from pathlib import Path
import copy,json,tempfile,unittest

from intelligence_warehouse.historical_recovery.nfl_first_nine_col_forward_shadow import (
    build_same_quote_nfl_shadow,
    append_first_immutable_game_shadow,
    SCHEMA,
)

NOW=datetime(2026,10,9,1,49,tzinfo=timezone.utc)
FROZEN=datetime(2026,10,9,1,33,tzinfo=timezone.utc)
PRICE=datetime(2026,10,9,1,41,tzinfo=timezone.utc)
FIRST=datetime(2026,10,11,17,tzinfo=timezone.utc)
SOURCE_SHA='a'*64
MODEL_SHA='b'*64

def context():
    return {
      'schema':'NFL_2026_PREGAME_SOURCE_FROZEN_PRIOR_TEAM_SCORE_FORM_V1',
      'official_espn_event_id':'401872982',
      'source_schedule_game_id':'2026_05_CIN_MIA',
      'home_team':'MIA','away_team':'CIN',
      'season':2026,'week':5,
      'source_team_form_first_frozen_at_utc':FROZEN.isoformat(),
      'original_pregame_espn_captured_at_utc':'2026-10-09T00:40:37Z',
      'official_first_pitch_utc':FIRST.isoformat(),
      'nine_features_excluding_market':[0.1,0.2,-0.1,0.1,0.0,1.0,0.0],
      'source_2026_prior_final_team_home_games':3,
      'source_2026_prior_final_team_away_games':3,
      'source_original_2026_scoreboard_sha256':SOURCE_SHA,
      'source_2026_schedule_sha256':'c'*64,
      'source_frozen_training_model_sha256':MODEL_SHA,
      'source_prior_2016_2025_epa_replayed_from_original_pbp':False,
      'actual_stadium_roof_state_confirmed':False,
      'betting_play_authorized':False,
      'wager_executed':False,
    }

def book(update=PRICE,away=110,home=-120):
    vig=100/220+120/220 if False else 100/(100+away)+home/(home-100)
    home_raw=(-home)/((-home)+100)
    away_raw=100/(100+away)
    vig=home_raw+away_raw
    return {
        'schema':'NFL_FIRST_VALIDATED_POST_ESPN_PREKICKOFF_BOOK_MONEYLINE_SOURCE_ONLY_V1',
        'official_espn_event_id':'401872982',
        'away_team_abbr':'CIN','home_team_abbr':'MIA',
        'official_espn_kickoff_utc':FIRST.isoformat(),
        'source_original_book_quote_updated_at_utc':update.isoformat(),
        'observed_source_only_research_frozen_at_utc':NOW.isoformat(),
        'source_book':'draftkings','source_provider':'sportwizzard',
        'source_provider_event_id':'game-source-abc',
        'original_book_home_american':home,
        'original_book_away_american':away,
        'raw_fair_home_prob':home_raw/vig,
        'raw_fair_away_prob':away_raw/vig,
        'raw_book_overround':vig,
        'betting_play_approved':False,'model_prediction_calculated':False,
        'sportsbook_wager_executed':False,
    }

def model():
    return {
      'model_version':'NFL_PREQUOTE_SCORE_FORM_9COL_2016_2024_RIDGE20_RESEARCH_V1',
      'features':['intercept','historical_same_game_home_no_vig_market_logit',
          'prior_same_season_last3_home_away_point_margin_difference_scaled14',
          'prior_same_season_score_vs_opp_defense_matchup_scaled20',
          'prior_same_season_home_minus_away_points_scored_scaled12',
          'prior_same_season_away_minus_home_points_allowed_scaled12',
          'prior_original_schedule_home_minus_away_rest_days_scaled7',
          'min_three_prior_completed_games_for_both_teams_divided3',
          'original_scheduled_neutral_venue_indicator'],
      'coefficients':[0.1,.94,.07,.04,.1,.02,.09,.05,-.08],
      'two_col_market_only_coefficients':[-.04,1.07],
      'training_independent_games':2465,
      'training_seasons':list(range(2016,2025)),
      'secondary_holdout_seasons':[2025],
      'trained_frozen_at_utc':'2026-10-09T01:32:39Z',
      'training_2025_outcomes_used':False,
      'training_2026_outcomes_used':False,
      '2026_live_betting_play_approved':False,
      'real_bookmaker_market_edge_proven':False,
      'retrospective_2025_secondary_validation':{
          'historical_prior_week_score_form_ridge':{'brier':.213},
          'raw_compiled_market_home_no_vig':{'brier':.210},
      },
    }

class NFLFirstRealPregameModelOverMarketShadowTests(unittest.TestCase):
    def test_rams_source_alias_matches_without_changing_frozen_context(self):
        c=context();c['home_team']='LA';c['away_team']='BUF'
        b=book();b['home_team_abbr']='LAR';b['away_team_abbr']='BUF'
        original=copy.deepcopy(c)
        out,_=build_same_quote_nfl_shadow([c],[b],model(),now=NOW,
            model_file_sha256=MODEL_SHA,source_market_sha256='e'*64)
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]['home_team'],'LA')
        self.assertEqual(c,original)
        b['home_team_abbr']='LAC'
        with self.assertRaisesRegex(ValueError,'team'):
            build_same_quote_nfl_shadow([c],[b],model(),now=NOW,
                model_file_sha256=MODEL_SHA,source_market_sha256='e'*64)
        b['home_team_abbr']='LAR'
        b['source_original_book_quote_updated_at_utc']=FROZEN.isoformat()
        out,_=build_same_quote_nfl_shadow([c],[b],model(),now=NOW,
            model_file_sha256=MODEL_SHA,source_market_sha256='e'*64)
        self.assertEqual(out,[])

    def test_prequoted_score_form_calibration_uses_same_future_bookmaker_price(self):
        out,summary=build_same_quote_nfl_shadow([context()],[book()],model(),now=NOW,
                                                 model_file_sha256=MODEL_SHA,source_market_sha256='e'*64)
        self.assertEqual(len(out),1)
        item=out[0]
        self.assertEqual(item['official_espn_event_id'],'401872982')
        self.assertEqual(len(item['model_feature_vector']),9)
        self.assertAlmostEqual(item['original_raw_book_home_fair'],book()['raw_fair_home_prob'])
        self.assertTrue(0<item['market_only_calibrated_home_win_prob']<1)
        self.assertTrue(0<item['nine_feature_score_form_home_win_prob']<1)
        self.assertFalse(item['same_game_result_used_for_features'])
        self.assertFalse(item['betting_play_approved'])
        self.assertFalse(item['predicted_market_advantage_proven'])
        self.assertFalse(item['sportsbook_wager_created'])
        self.assertEqual(summary['independent_forward_game_blocks'],1)

    def test_any_quote_before_frozen_feature_cutoff_or_after_kickoff_refused(self):
        older=book(update=FROZEN-timedelta(minutes=1))
        out,_=build_same_quote_nfl_shadow([context()],[older],model(),now=NOW,
            model_file_sha256=MODEL_SHA,source_market_sha256='e'*64)
        self.assertEqual(out,[])
        later=book(update=FIRST+timedelta(minutes=2))
        out,_=build_same_quote_nfl_shadow([context()],[later],model(),now=NOW,
            model_file_sha256=MODEL_SHA,source_market_sha256='e'*64)
        self.assertEqual(out,[])
        out,_=build_same_quote_nfl_shadow([context()],[book()],model(),
            now=FIRST+timedelta(minutes=1),model_file_sha256=MODEL_SHA,source_market_sha256='e'*64)
        self.assertEqual(out,[])

    def test_unknown_espn_game_and_wrong_team_identity_fail_closed(self):
        wrong=context();wrong['home_team']='NYJ'
        with self.assertRaisesRegex(ValueError,'team'):
            build_same_quote_nfl_shadow([wrong],[book()],model(),now=NOW,
                model_file_sha256=MODEL_SHA,source_market_sha256='e'*64)
        wrong=context();wrong['official_espn_event_id']='888888888'
        with self.assertRaisesRegex(ValueError,'match|identity'):
            build_same_quote_nfl_shadow([wrong],[book()],model(),now=NOW,
                model_file_sha256=MODEL_SHA,source_market_sha256='e'*64)

    def test_changed_coefficient_and_original_source_final_bet_flag_rejected(self):
        m=model();m['2026_live_betting_play_approved']=True
        with self.assertRaisesRegex(ValueError,'research|approved'):
            build_same_quote_nfl_shadow([context()],[book()],m,now=NOW,
                model_file_sha256=MODEL_SHA,source_market_sha256='e'*64)
        b=book();b['betting_play_approved']=True
        with self.assertRaisesRegex(ValueError,'book|research'):
            build_same_quote_nfl_shadow([context()],[b],model(),now=NOW,
                model_file_sha256=MODEL_SHA,source_market_sha256='e'*64)

    def test_original_game_id_first_probabilistic_shadow_immutable(self):
        predictions,_=build_same_quote_nfl_shadow([context()],[book()],model(),now=NOW,
            model_file_sha256=MODEL_SHA,source_market_sha256='e'*64)
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'NFL_FIRST_FROZEN.jsonl'
            self.assertEqual(append_first_immutable_game_shadow(file,predictions),1)
            first=file.read_bytes()
            self.assertEqual(append_first_immutable_game_shadow(file,predictions),0)
            amended=copy.deepcopy(predictions)
            amended[0]['nine_feature_score_form_home_win_prob']=.999
            with self.assertRaisesRegex(ValueError,'conflict'):
                append_first_immutable_game_shadow(file,amended)
            self.assertEqual(first,file.read_bytes())

if __name__=='__main__':unittest.main()
