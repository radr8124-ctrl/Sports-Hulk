"""NFL decade of descriptive weather + first truly prior paired book prices.

A game first-frozen AFTER kickoff is NOT a forward research forecast. The
new source-only baseline applies ONLY to games where the currently observed
clock is before ESPN's original source-recorded kickoff, and the true provider
paired moneyline price is after original pregame capture and before kickoff.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from pathlib import Path
import copy
import hashlib
import json
import tempfile
import unittest

import pandas as pd

from intelligence_warehouse.historical_recovery.nfl_tenyear_forward_market_provenance import (
    audit_nfl_tenyear_history,
    build_verified_nfl_bookmaker_baselines,
    append_immutable_nfl_book_control,
    freeze_cycle,
)

NOW=datetime(2026,10,9,0,25,tzinfo=timezone.utc)
START=datetime(2026,10,11,17,tzinfo=timezone.utc)
QUOTE=NOW-timedelta(minutes=32)
FIRST=NOW-timedelta(hours=3)

def capture(start=START,at=FIRST,venue_indoor=True):
    return {
      'schema':'SPORTS_NHL_NFL_PREGAME_SOURCE_V1',
      'official_game_id':'401872982',
      'captured_at_utc':at.isoformat(),
      'scheduled_start_utc':start.isoformat(),
      'fixture':{
        'game_state_asof':'STATUS_SCHEDULED',
        'home_team':'MIA','away_team':'CIN',
        'home_espn_team_id':'15','away_espn_team_id':'4',
        'home_espn_team_name':'Miami Dolphins',
        'away_espn_team_name':'Cincinnati Bengals',
        'venue_name':'Hard Rock Stadium',
        'venue_indoor_attribute':venue_indoor,
        'actual_stadium_roof_state':'UNKNOWN_NOT_OBSERVED',
        'week':5,'season_year':2026,
      },
      'injuries':{
        'status':'SOURCE_INJURIES_REPORTED_NOT_CONFIRMED_GAME_STATUS',
        'home':[{
           'athlete_id':None,'athlete_name':'Sample Athlete',
           'status':'Active',
           'source_reported_at_utc':(FIRST-timedelta(days=8)).isoformat(),
           'report_only_not_final_game_availability':True,
        }],
        'away':[],
      },
      'model_pick_approved':False,
      'starter_confirmed':False,
      'bankroll_or_sportsbook_action':False,
    }

def quote(side,*,book='draftkings',event='provider-event-aaa',when=QUOTE,
          home_price=-120,away_price=110,home_team='Miami Dolphins',away_team='Cincinnati Bengals',
          kickoff=START):
    return {
        'provider':'sportwizzard','sportsbook':book,
        'event_id':event,'game_key':'CIN@MIA',
        'away_team':away_team,'home_team':home_team,
        'start':kickoff.isoformat(),
        'market':'MONEYLINE','market_subtype':'MONEYLINE',
        'side':side,'team_side':side,
        'line':None,
        'selection':'Miami Dolphins' if side=='HOME' else 'Cincinnati Bengals',
        'price_american':home_price if side=='HOME' else away_price,
        'updated':when.isoformat(),
    }

def prices(**args):
    return pd.DataFrame([quote('HOME',**args),quote('AWAY',**args)])

def history():
    rows=[]
    for season in range(2016,2026):
        rows.append({
          'game_id':f'{season}_01_CIN_MIA','season':season,
          'game_type':'REG','gameday':f'{season}-09-10',
          'away_team':'CIN','home_team':'MIA',
          'home_score':23,'away_score':17,
          'roof':'outdoors','temp':78.,'wind':10.,
          'home_pre5_off_epa_per_play':-0.01,'away_pre5_def_epa_per_play':0.03,
          'spread_line':-3.5,'total_line':40.5,
        })
    return pd.DataFrame(rows)

class NFLHistoricalProvenanceAndTrueFutureBookmakerPriceTests(unittest.TestCase):
    def test_ten_year_archive_is_not_twelve_month_old_weather_forecast(self):
        _,audit=audit_nfl_tenyear_history(history())
        self.assertEqual(audit['seasons'],list(range(2016,2026)))
        self.assertEqual(audit['historical_games'],10)
        self.assertEqual(audit['unique_game_ids'],10)
        self.assertEqual(audit['historical_weather_is_original_pregame_forecast'],False)
        self.assertEqual(audit['stored_roof_is_verified_future_2026_open_closed_state'],False)
        self.assertTrue(audit['pre5_epa_columns_require_provenance_before_forward_model'])
        self.assertTrue(audit['current_2026_games_must_be_separately_captured'])

    def test_strict_real_ESPN_game_moneyline_same_book_and_two_sides_only(self):
        candidates,receipt=build_verified_nfl_bookmaker_baselines(
            [capture()],prices(),now=NOW,
            market_file_mtime_utc=QUOTE+timedelta(minutes=1),
            original_source_file_sha256='a'*64,
            source_market_file_sha256='b'*64,
            tenyear_history_sha256='c'*64,
        )
        self.assertEqual(len(candidates),1)
        a=candidates[0]
        self.assertEqual(a['official_espn_event_id'],'401872982')
        self.assertEqual(a['week'],5)
        self.assertEqual(a['source_book'],'draftkings')
        self.assertEqual(a['source_provider_event_id'],'provider-event-aaa')
        self.assertAlmostEqual(a['raw_fair_home_prob']+a['raw_fair_away_prob'],1,places=10)
        self.assertGreater(a['raw_book_overround'],1.)
        self.assertEqual(a['actual_stadium_roof_status'],'UNKNOWN_NOT_OBSERVED')
        self.assertTrue(a['indoor_venue_does_not_confirm_roof'])
        self.assertEqual(a['stale_injury_reported_as_game_clearance'],False)
        self.assertEqual(receipt['independent_future_game_blocks'],1)
        self.assertFalse(a['betting_play_approved'])
        self.assertFalse(a['model_prediction_calculated'])

    def test_same_book_exact_quote_time_never_mix_books_or_teams(self):
        mixed=prices()
        mixed.loc[mixed.side.eq('AWAY'),'sportsbook']='fanduel'
        rows,_=build_verified_nfl_bookmaker_baselines(
            [capture()],mixed,now=NOW,
            market_file_mtime_utc=QUOTE,original_source_file_sha256='a'*64,
            source_market_file_sha256='b'*64,tenyear_history_sha256='c'*64)
        self.assertEqual(rows,[])
        wrong=prices()
        wrong.loc[wrong.side.eq('AWAY'),'home_team']='Dallas Cowboys'
        rows,_=build_verified_nfl_bookmaker_baselines(
            [capture()],wrong,now=NOW,
            market_file_mtime_utc=QUOTE,original_source_file_sha256='a'*64,
            source_market_file_sha256='b'*64,tenyear_history_sha256='c'*64)
        self.assertEqual(rows,[])
        changed=prices()
        changed.loc[changed.side.eq('AWAY'),'updated']=(QUOTE+timedelta(minutes=1)).isoformat()
        rows,_=build_verified_nfl_bookmaker_baselines(
            [capture()],changed,now=NOW,
            market_file_mtime_utc=QUOTE,original_source_file_sha256='a'*64,
            source_market_file_sha256='b'*64,tenyear_history_sha256='c'*64)
        self.assertEqual(rows,[])

    def test_quote_before_pregame_source_or_game_already_started_not_original_forward(self):
        before=prices(when=FIRST-timedelta(minutes=1))
        rows,_=build_verified_nfl_bookmaker_baselines(
            [capture()],before,now=NOW,
            market_file_mtime_utc=QUOTE,original_source_file_sha256='a'*64,
            source_market_file_sha256='b'*64,tenyear_history_sha256='c'*64)
        self.assertEqual(rows,[])
        started=NOW-timedelta(minutes=10)
        rows,_=build_verified_nfl_bookmaker_baselines(
            [capture(start=started)],prices(kickoff=started),now=NOW,
            market_file_mtime_utc=QUOTE,original_source_file_sha256='a'*64,
            source_market_file_sha256='b'*64,tenyear_history_sha256='c'*64)
        self.assertEqual(rows,[])
        afterkick=prices(when=START+timedelta(minutes=1))
        rows,_=build_verified_nfl_bookmaker_baselines(
            [capture()],afterkick,now=START-timedelta(minutes=3),
            market_file_mtime_utc=START-timedelta(minutes=3),
            original_source_file_sha256='a'*64,
            source_market_file_sha256='b'*64,tenyear_history_sha256='c'*64)
        self.assertEqual(rows,[])

    def test_very_stale_or_future_source_not_claimed_as_live_market(self):
        stale=prices(when=NOW-timedelta(hours=5))
        source=capture(at=NOW-timedelta(hours=9))
        rows,_=build_verified_nfl_bookmaker_baselines(
            [source],stale,now=NOW,
            market_file_mtime_utc=QUOTE,
            original_source_file_sha256='a'*64,
            source_market_file_sha256='b'*64,tenyear_history_sha256='c'*64)
        self.assertEqual(rows,[])
        rows,_=build_verified_nfl_bookmaker_baselines(
            [capture()],prices(),now=NOW,
            market_file_mtime_utc=NOW+timedelta(minutes=1),
            original_source_file_sha256='a'*64,
            source_market_file_sha256='b'*64,tenyear_history_sha256='c'*64)
        self.assertEqual(rows,[])

    def test_exact_espn_team_identity_and_start_must_match_provider(self):
        bad=capture()
        bad['fixture']['home_espn_team_name']='Dallas Cowboys'
        with self.assertRaisesRegex(ValueError,'ESPN|team'):
            build_verified_nfl_bookmaker_baselines(
                [bad],prices(),now=NOW,market_file_mtime_utc=QUOTE,
                original_source_file_sha256='a'*64,
                source_market_file_sha256='b'*64,tenyear_history_sha256='c'*64)
        rows,_=build_verified_nfl_bookmaker_baselines(
            [capture()],prices(kickoff=START+timedelta(minutes=8)),now=NOW,
            market_file_mtime_utc=QUOTE,original_source_file_sha256='a'*64,
            source_market_file_sha256='b'*64,tenyear_history_sha256='c'*64)
        self.assertEqual(rows,[])

    def test_new_advanced_model_requires_quote_AFTER_original_feature_capture(self):
        after_context=QUOTE+timedelta(minutes=1)
        earlier=prices(book='draftkings',when=QUOTE)
        later=prices(book='fanduel',when=after_context)
        source=pd.concat([earlier,later],ignore_index=True)
        result,receipt=build_verified_nfl_bookmaker_baselines(
            [capture()],source,now=NOW,
            market_file_mtime_utc=NOW,
            original_source_file_sha256='a'*64,
            source_market_file_sha256='b'*64,
            tenyear_history_sha256='c'*64,
            minimum_quote_time_by_espn_event_id={'401872982':QUOTE},
        )
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['source_book'],'fanduel')
        self.assertGreater(pd.Timestamp(result[0]['source_original_book_quote_updated_at_utc']),
                           pd.Timestamp(QUOTE))

    def test_conflicting_duplicate_same_provider_book_timestamp_is_excluded_not_selected(self):
        source=capture()
        identical=prices(book='caesars')
        changed=identical.copy()
        changed['price_american']=[-200,180]
        source_rows=pd.concat([identical,changed,prices(book='draftkings')],ignore_index=True)
        accepted,report=build_verified_nfl_bookmaker_baselines(
            [source],source_rows,now=NOW,market_file_mtime_utc=QUOTE,
            original_source_file_sha256='a'*64,
            source_market_file_sha256='b'*64,
            tenyear_history_sha256='c'*64,
        )
        self.assertEqual(len(accepted),1)
        self.assertEqual(accepted[0]['source_book'],'draftkings')
        self.assertGreater(report['book_groups_rejected']['ambiguous_duplicate_book_side_source'],0)

    def test_original_espn_wsh_alias_is_only_admissible_for_official_WAS_team_id(self):
        f=capture()
        f['fixture']['home_espn_team_id']='28'
        f['fixture']['home_team']='WSH'
        f['fixture']['home_espn_team_name']='Washington Commanders'
        q=prices(home_team='Washington Commanders')
        result,_=build_verified_nfl_bookmaker_baselines(
            [f],q,now=NOW,market_file_mtime_utc=QUOTE,
            original_source_file_sha256='a'*64,
            source_market_file_sha256='b'*64,
            tenyear_history_sha256='c'*64,
        )
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['home_team_abbr'],'WAS')
        f['fixture']['home_espn_team_id']='99'
        with self.assertRaisesRegex(ValueError,'team'):
            build_verified_nfl_bookmaker_baselines(
                [f],q,now=NOW,market_file_mtime_utc=QUOTE,
                original_source_file_sha256='a'*64,
                source_market_file_sha256='b'*64,
                tenyear_history_sha256='c'*64,
            )

    def test_idempotent_first_real_future_game_baseline_not_repriced_later(self):
        rows,_=build_verified_nfl_bookmaker_baselines(
            [capture()],prices(),now=NOW,market_file_mtime_utc=QUOTE,
            original_source_file_sha256='a'*64,
            source_market_file_sha256='b'*64,tenyear_history_sha256='c'*64)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'NFL_GAME_FAIR.jsonl'
            self.assertEqual(append_immutable_nfl_book_control(path,rows),1)
            before=path.read_bytes()
            self.assertEqual(append_immutable_nfl_book_control(path,rows),0)
            self.assertEqual(before,path.read_bytes())
            changed=copy.deepcopy(rows)
            changed[0]['raw_fair_home_prob']=.99
            self.assertEqual(append_immutable_nfl_book_control(path,changed),0)
            self.assertEqual(before,path.read_bytes())

    def test_truly_old_historical_results_and_2026_regime_separated(self):
        frame=history()
        frame.loc[len(frame)]={
            **frame.iloc[-1].to_dict(),
            'game_id':'2026_01_CIN_MIA','season':2026,
        }
        with self.assertRaisesRegex(ValueError,'2016.*2025|historical.*season'):
            audit_nfl_tenyear_history(frame)

if __name__=='__main__':unittest.main()
