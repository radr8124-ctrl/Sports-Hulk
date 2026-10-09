"""Live MLB source features must be frozen BEFORE kickoff, from observed lineups."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
import json,tempfile,unittest

import pandas as pd

from intelligence_warehouse.historical_recovery.mlb_live_research_feature_freeze import (
    make_live_features,append_first_observation_once,freeze_cycle,
)

NOW=datetime(2026,10,8,20,40,tzinfo=timezone.utc)
CAPTURE=NOW-timedelta(minutes=4)
START=NOW+timedelta(hours=3)


def source(*,captured=CAPTURE,first_pitch=START,lineup_sides=('home',),season=2026):
    lineups={'status':'ONLY_ONE_TEAM_LINEUP_VISIBLE_PREGAME'}
    for side in lineup_sides:
        lineups[side]={
            'player_ids':list(range(501,510)) if side=='home' else list(range(701,710)),
            'player_names':[f'Player {idx}' for idx in range(9)],
            'source':'LIVE_FEED_OFFICIAL_BATTING_ORDER_CAPTURED_PREGAME',
            'confirmed_asof_capture':True,
        }
    if len(lineup_sides)==2:lineups['status']='OFFICIAL_BATTING_ORDER_VISIBLE_BEFORE_KICKOFF'
    return {
        'schema':'MLB_PREGAME_SOURCE_EVIDENCE_V1',
        'evidence_id':'TEST-MOCK-PREGAME-RECORD',
        'captured_at_utc':captured.isoformat(),
        'first_pitch_utc':first_pitch.isoformat(),
        'game_pk':999001,
        'fixture':{'official_date':first_pitch.date().isoformat(),
                   'official_game_type':'D',
                   'home_team':'Cleveland Guardians',
                   'away_team':'Chicago White Sox',
                   'official_status_at_capture':'Pre-Game'},
        'lineups':lineups,
        'probable_pitchers':{'away_probable_pitcher_id':51,
                            'away_probable_pitcher_name':'Possible Starter Away',
                            'home_probable_pitcher_id':91,
                            'home_probable_pitcher_name':'Possible Starter Home',
                            'probable_status':'OFFICIAL_SCHEDULE_PROBABLE_NOT_CONFIRMED'},
        'weather':{'status':'CAPTURED_NWS_FORECAST_NOT_OBSERVED_WEATHER',
                   'source_captured_at_utc':captured.isoformat(),
                   'forecast_generated_at_utc':(captured-timedelta(minutes=10)).isoformat(),
                   'forecast_temperature_f':61.,
                   'forecast_wind_mph':9.,
                   'forecast_precipitation_probability_pct':15,
                   'roof_status_asof':'UNKNOWN_NOT_CAPTURED'},
    }


def prior_year_speed():
    rows=[]
    for pid in range(501,510):
        rows.append({'player_id':pid,
          'source_completed_season':2025,'feature_research_season':2026,
          'prior_season_sprint_speed_ft_per_sec':28.7,
          'prior_season_bat_speed_mph':74.2,
          'prior_season_sprint_qualified':True,'prior_season_bat_qualified':True,
          'approved_for_live_model':False})
    return pd.DataFrame(rows)


def past_player_games():
    prior=[]
    for day in range(1,9):
        dt=f'2026-10-{day:02d}'
        for pid in range(501,510):
            prior.append({
              'game_pk':day*100+pid,
              'player_id':pid,
              'official_date':dt,
              'game_date':f'{dt}T15:00:00Z',
              'season':2026,
              'group':'HITTING','game_type':'R','status':'Final',
              'hits':float(day%3),'walks':float(day%2),
              'plate_appearances':4.,'stolen_bases':0.,
            })
    # Deliberate target/same-day outcome that should not affect pregame form.
    prior.append({
        'game_pk':999001,'player_id':501,'official_date':'2026-10-08',
        'game_date':'2026-10-08T18:00:00Z','season':2026,
        'group':'HITTING','game_type':'D','status':'Final',
        'hits':9000.,'walks':8000.,'plate_appearances':1500.,'stolen_bases':5000.,
    })
    return pd.DataFrame(prior)


class MLBFirstObservedResearchFreezeTests(unittest.TestCase):
    def test_first_official_lineup_frozen_with_real_completed_season_source_and_prior_dates(self):
        rows=make_live_features(source(),past_player_games(),prior_year_speed(),now=NOW)
        self.assertEqual(len(rows),9)
        self.assertEqual(len({r['player_id'] for r in rows}),9)
        first=next(r for r in rows if r['player_id']==501)
        self.assertEqual(first['game_pk'],999001)
        self.assertEqual(first['lineup_source_status'],'OFFICIAL_BATTING_ORDER_CAPTURED_BEFORE_FIRST_PITCH')
        self.assertEqual(first['prior_sprint_speed_ft_per_sec'],28.7)
        self.assertEqual(first['prior_bat_speed_mph'],74.2)
        self.assertEqual(first['prior_games_available'],7)
        self.assertEqual(first['last_prior_date'],'2026-10-07')
        self.assertLess(first['prior_last5_hits_avg'],9000)
        self.assertEqual(first['opposing_probable_pitcher_id'],51)
        self.assertEqual(first['opposing_pitcher_confirmation_status'],'PROBABLE_NOT_CONFIRMED')
        self.assertEqual(first['forecast_temperature_f'],61)
        self.assertEqual(first['source_capture_at_utc'],CAPTURE.isoformat(timespec='seconds'))
        self.assertEqual(first['feature_frozen_at_utc'],NOW.isoformat(timespec='seconds'))
        self.assertTrue(first['frozen_before_scheduled_first_pitch'])
        self.assertFalse(first['betting_prediction_written'])
        self.assertFalse(first['live_play_approved'])
        self.assertTrue(first['sportsbook_quote_time_or_price_not_observed'])
        self.assertFalse(first['starter_confirmed'])

    def test_todays_or_future_game_outcomes_never_enter_feature(self):
        source_row=source()
        history=past_player_games()
        original=make_live_features(source_row,history,prior_year_speed(),now=NOW)
        corrupt=history.copy()
        corrupt.loc[corrupt.official_date.eq('2026-10-08'),'hits']=10**7
        corrupt.loc[corrupt.official_date.eq('2026-10-08'),'walks']=10**7
        rebuilt=make_live_features(source_row,corrupt,prior_year_speed(),now=NOW)
        self.assertEqual(original,rebuilt)

    def test_capture_after_start_or_stale_observation_cannot_be_frozen_retroactively(self):
        after=make_live_features(source(),past_player_games(),prior_year_speed(),now=START+timedelta(minutes=1))
        self.assertEqual(after,[])
        old=make_live_features(source(captured=NOW-timedelta(minutes=40)),past_player_games(),prior_year_speed(),now=NOW)
        self.assertEqual(old,[])
        future=source(captured=NOW+timedelta(minutes=1))
        self.assertEqual(make_live_features(future,past_player_games(),prior_year_speed(),now=NOW),[])

    def test_unverified_boxscore_based_or_non_unique_lineup_never_frozen(self):
        row=source()
        row['lineups']['home']['source']='POSTGAME_BOXSCORE'
        self.assertEqual(make_live_features(row,past_player_games(),prior_year_speed(),now=NOW),[])
        bad=source()
        bad['lineups']['home']['player_ids']=[501]*9
        self.assertEqual(make_live_features(bad,past_player_games(),prior_year_speed(),now=NOW),[])
        invalid=source()
        invalid['lineups']['status']='NOT_YET_PUBLISHED'
        self.assertEqual(make_live_features(invalid,past_player_games(),prior_year_speed(),now=NOW),[])

    def test_wrong_season_speed_is_never_promoted(self):
        sp=prior_year_speed()
        sp['source_completed_season']=2026
        with self.assertRaisesRegex(ValueError,'prior season'):
            make_live_features(source(),past_player_games(),sp,now=NOW)

    def test_appending_first_pregame_player_once_preserves_original_receipt_and_later_other_team(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=Path(folder)/'FROZEN_FEATURES.jsonl'
            row=make_live_features(source(),past_player_games(),prior_year_speed(),now=NOW)
            count=append_first_observation_once(ledger,row)
            self.assertEqual(count,9)
            before=ledger.read_bytes()
            self.assertEqual(append_first_observation_once(ledger,row),0)
            self.assertEqual(before,ledger.read_bytes())
            later_source=source(lineup_sides=('home','away'))
            later=make_live_features(later_source,past_player_games(),prior_year_speed(),now=NOW)
            count=append_first_observation_once(ledger,later)
            self.assertEqual(count,9)
            self.assertEqual(len(ledger.read_text().splitlines()),18)
            self.assertEqual(len({(x['game_pk'],x['player_id']) for x in map(json.loads,ledger.read_text().splitlines())}),18)

    def test_repeated_live_refresh_skips_85mb_player_history_if_all_player_ids_already_frozen(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=Path(folder)/'SOURCE.jsonl'
            output=Path(folder)/'FREEZE.jsonl'
            src=source()
            ledger.write_text(json.dumps(src)+'\n')
            previous=make_live_features(src,past_player_games(),prior_year_speed(),now=NOW)
            self.assertEqual(append_first_observation_once(output,previous),9)
            before=output.read_bytes()
            with patch('intelligence_warehouse.historical_recovery.mlb_live_research_feature_freeze.pd.read_csv',
                       side_effect=AssertionError('Never reload 85MB history for zero new players')):
                result=freeze_cycle(ledger,output,now=NOW,
                                    history_file=Path(folder)/'NO_HISTORY.csv',
                                    prior_file=Path(folder)/'NO_SOURCE.parquet')
            self.assertEqual(result['fresh_frozen_lineup_player_observations_added'],0)
            self.assertEqual(result['existing_player_ids_already_frozen'],9)
            self.assertEqual(output.read_bytes(),before)

    def test_unverified_forecast_does_not_turn_into_known_actual_weather(self):
        row=source()
        row['weather']['forecast_generated_at_utc']=(CAPTURE+timedelta(minutes=1)).isoformat()
        res=make_live_features(row,past_player_games(),prior_year_speed(),now=NOW)
        self.assertEqual(len(res),9)
        self.assertEqual(res[0]['forecast_source_status'],'UNVERIFIED_ASOF_NOT_USED')
        self.assertIsNone(res[0]['forecast_temperature_f'])
        self.assertFalse(res[0]['actual_weather_at_first_pitch_verified'])

if __name__=='__main__':unittest.main()
