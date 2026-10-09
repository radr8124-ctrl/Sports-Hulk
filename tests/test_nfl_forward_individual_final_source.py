"""Individually scored NFL games must not wait for a whole football week to end."""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch,MagicMock
import copy,json,tempfile,unittest
import pandas as pd

from intelligence_warehouse.historical_recovery.nfl_forward_individual_final_source import (
    verify_future_final_events,
    append_first_espn_event_final,
    collect_cycle,
)

FIRST=datetime(2026,10,11,17,0,tzinfo=timezone.utc)
LATER=datetime(2026,10,12,1,5,tzinfo=timezone.utc)
MODEL=datetime(2026,10,9,1,41,tzinfo=timezone.utc)

def forecast(game='401872982',home='MIA',away='CIN',start=FIRST):
    return {
      'schema':'NFL_2026_FIRST_RESEARCH_NINE_FEATURE_SAME_NEW_QUOTE_MARKET_COMPARISON_V1',
      'official_espn_event_id':game,'season':2026,'week':5,
      'home_team':home,'away_team':away,
      'source_first_real_future_prediction_frozen_at_utc':MODEL.isoformat(),
      'official_first_pitch_utc':start.isoformat(),
      'sportsbook_wager_created':False,
      'betting_play_approved':False,'research_only':True,
    }

def fixture(*,played=True,home='MIA',away='CIN'):
    return {
        'game_id':'2026_05_CIN_MIA','season':2026,'game_type':'REG',
        'espn':401872982,'week':5,'gameday':'2026-10-11',
        'home_team':home,'away_team':away,
        'home_score':27 if played else None,
        'away_score':20 if played else None,
    }

def original_event(*,final=True,home='MIA',away='CIN',score=(27,20),game='401872982'):
    code={'MIA':'15','CIN':'4','WAS':'28','WSH':'28','LA':'14','LAR':'14','NYJ':'20'}
    return {
        'id':game,'date':FIRST.isoformat(),'season':{'year':2026,'type':2},
        'week':{'number':5},
        'status':{'type':{'name':'STATUS_FINAL' if final else 'STATUS_IN_PROGRESS','completed':final}},
        'competitions':[{'competitors':[
            {'homeAway':'home','team':{'id':code.get(home,'999'),'abbreviation':home},'score':str(score[0])},
            {'homeAway':'away','team':{'id':code.get(away,'999'),'abbreviation':away},'score':str(score[1])},
        ]}],
    }

class NFLForwardIndividualGameOfficialFinalCollectionTests(unittest.TestCase):
    def test_exact_game_team_id_time_score_final_and_original_pregame_model_identity(self):
        rows,status=verify_future_final_events([forecast()],pd.DataFrame([fixture()]),
                                                {'events':[original_event()]},now=LATER,
                                                schedule_sha256='a'*64)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['official_espn_game_id'],'401872982')
        self.assertEqual(rows[0]['home_points'],27)
        self.assertEqual(rows[0]['away_points'],20)
        self.assertTrue(rows[0]['official_espn_final_confirmed'])
        self.assertTrue(rows[0]['real_original_ESPN_game_event_payload_retained'])
        self.assertEqual(status['independent_football_games_with_verified_Final'],1)
        self.assertEqual(status['final_source_score_disagreements'],0)

    def test_partial_week_can_grade_one_game_even_if_other_football_games_unplayed(self):
        schedule=pd.DataFrame([fixture(),{**fixture(played=False),
                                            'game_id':'2026_05_OTHER',
                                            'espn':401872993,'away_team':'NYJ'}])
        rows,status=verify_future_final_events([forecast()],schedule,
                                                {'events':[original_event()]},now=LATER,
                                                schedule_sha256='a'*64)
        self.assertEqual(len(rows),1)
        self.assertTrue(status['does_not_wait_for_whole_week_to_finish'])
        self.assertEqual(status['independent_football_games_with_verified_Final'],1)

    def test_scheduled_but_unfinished_game_never_invokes_official_result_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/'MODEL.jsonl';source.write_text(json.dumps(forecast())+'\n')
            schedule=root/'SCHEDULE.csv';pd.DataFrame([fixture(played=False)]).to_csv(schedule,index=False)
            output=root/'EVENT_FINAL.jsonl'
            with patch('intelligence_warehouse.historical_recovery.nfl_forward_individual_final_source.requests.get',
                       side_effect=AssertionError('Never request unplayed NFL game')):
                report=collect_cycle(source,schedule,output,now=MODEL+timedelta(minutes=1))
            self.assertEqual(report['verified_new_independent_final_games'],0)
            self.assertEqual(report['source_HTTP_calls'],0)
            self.assertFalse(output.exists())

    def test_live_score_or_missing_independent_schedule_fails_to_grade(self):
        rows,status=verify_future_final_events([forecast()],pd.DataFrame([fixture()]),
                                                {'events':[original_event(final=False)]},now=LATER,
                                                schedule_sha256='a'*64)
        self.assertEqual(rows,[])
        self.assertEqual(status['independent_football_games_with_verified_Final'],0)
        rows,status=verify_future_final_events([forecast()],pd.DataFrame([fixture(played=False)]),
                                                {'events':[original_event()]},now=LATER,
                                                schedule_sha256='a'*64)
        self.assertEqual(rows,[])
        self.assertEqual(status['independent_nflverse_final_scores_still_missing'],1)

    def test_wrong_team_numeric_id_and_wrong_independent_score_block(self):
        wrong=original_event(home='NYJ')
        with self.assertRaisesRegex(ValueError,'team'):
            verify_future_final_events([forecast()],pd.DataFrame([fixture()]),
                                        {'events':[wrong]},now=LATER,schedule_sha256='a'*64)
        wrong=original_event(score=(31,20))
        with self.assertRaisesRegex(ValueError,'score'):
            verify_future_final_events([forecast()],pd.DataFrame([fixture()]),
                                        {'events':[wrong]},now=LATER,schedule_sha256='a'*64)

    def test_original_prediction_must_precede_first_pitch_even_if_current_source_final(self):
        model=forecast()
        model['source_first_real_future_prediction_frozen_at_utc']=(FIRST+timedelta(seconds=2)).isoformat()
        with self.assertRaisesRegex(ValueError,'pregame'):
            verify_future_final_events([model],pd.DataFrame([fixture()]),
                                        {'events':[original_event()]},now=LATER,schedule_sha256='a'*64)

    def test_exact_original_ESPN_event_immutable_conflict_does_not_rewrite(self):
        rows,_=verify_future_final_events([forecast()],pd.DataFrame([fixture()]),
                                            {'events':[original_event()]},now=LATER,
                                            schedule_sha256='a'*64)
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'NFL_FINAL_SOURCE.jsonl'
            self.assertEqual(append_first_espn_event_final(output,rows),1)
            original=output.read_bytes()
            self.assertEqual(append_first_espn_event_final(output,rows),0)
            edited=copy.deepcopy(rows);edited[0]['home_points']=14
            with self.assertRaisesRegex(ValueError,'conflict'):
                append_first_espn_event_final(output,edited)
            self.assertEqual(original,output.read_bytes())

    def test_exact_event_record_reusable_by_three_probability_official_scorer(self):
        from intelligence_warehouse.historical_recovery.nfl_nine_col_official_scoring import score_original_nfl_games_against_verified_final
        rows,_=verify_future_final_events([forecast()],pd.DataFrame([fixture()]),
                                            {'events':[original_event()]},now=LATER,
                                            schedule_sha256='a'*64)
        full=forecast()
        full.update({
            'source_context_features_frozen_at_utc':'2026-10-09T01:33:00Z',
            'source_qualified_book_quote_updated_at_utc':'2026-10-09T01:40:40Z',
            'original_raw_book_home_fair':.52,'market_only_calibrated_home_win_prob':.53,
            'nine_feature_score_form_home_win_prob':.54,'source_is_game_moneyline_not_player_proposition':True,
            'source_book_name':'pinnacle','source_frozen_model_sha256':'b'*64,
        })
        score,receipt=score_original_nfl_games_against_verified_final([full],rows,now=LATER+timedelta(minutes=2))
        self.assertEqual(len(score),1)
        self.assertEqual(receipt['independent_final_game_blocks'],1)
        self.assertFalse(receipt['market_advantage_statistically_proven'])

if __name__=='__main__':unittest.main()
