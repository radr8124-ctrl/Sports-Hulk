"""Only information actually observed before first pitch may become MLB evidence."""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
import pandas as pd
from intelligence_warehouse.mlb_pregame_capture.capture_evidence import (
    parse_schedule, extract_official_pregame_lineups, extract_nws_hourly_forecast,
    resolve_venue_coordinates, compose_evidence, append_snapshot_once, capture_once,
)

NOW=datetime(2026,10,8,13,0,tzinfo=timezone.utc)
START='2026-10-09T00:00:00Z'

def fixture_game(*,status='Scheduled',start=START,venue_id=4,game_pk=849832):
 return {
 'gamePk':game_pk,'gameDate':start,'officialDate':'2026-10-08','gameType':'D','venue':{'id':venue_id,'name':'Rate Field'},
 'status':{'detailedState':status,'abstractGameState':'Preview' if status=='Scheduled' else 'Live'},
 'teams':{'away':{'team':{'id':114,'name':'Cleveland Guardians'},'probablePitcher':{'id':800048,'fullName':'Parker Messick'}},
          'home':{'team':{'id':145,'name':'Chicago White Sox'},'probablePitcher':{'id':696146,'fullName':'Hagen Smith'}}}}

def fixture_schedule(*games):
 return {'dates':[{'date':'2026-10-08','games':list(games or [fixture_game()])}]}

def fixture_feed(*,status='Scheduled',nine=False,start=START):
 order=list(range(110001,110010)) if nine else []
 players={f'ID{k}':{'person':{'id':k,'fullName':f'Batter {k}'},'position':{'abbreviation':'OF'}} for k in order}
 return {'gamePk':849832,'gameData':{'status':{'detailedState':status,'abstractGameState':'Preview' if status=='Scheduled' else 'Live'},'datetime':{'dateTime':start}},
         'liveData':{'boxscore':{'teams':{'away':{'battingOrder':order,'players':players},
                                           'home':{'battingOrder':order,'players':players}}},
                     'linescore':{'currentInning':None}}}

def fixture_nws():
 return {'properties':{'updateTime':'2026-10-08T12:20:00+00:00','generatedAt':'2026-10-08T12:40:00+00:00',
         'periods':[{'startTime':'2026-10-08T19:00:00-05:00','endTime':'2026-10-08T20:00:00-05:00',
                     'temperature':57,'temperatureUnit':'F','windSpeed':'9 mph','shortForecast':'Partly Cloudy',
                     'probabilityOfPrecipitation':{'unitCode':'wmoUnit:percent','value':10}}]}}


class SourceTimeSafetyTests(unittest.TestCase):
 def test_schedule_capture_retains_probable_status_not_confirmed(self):
  rows=parse_schedule(fixture_schedule(),NOW,lookahead_hours=48)
  self.assertEqual(len(rows),1)
  row=rows[0]
  self.assertEqual(row['game_pk'],849832)
  self.assertEqual(row['home_probable_pitcher_id'],696146)
  self.assertEqual(row['away_probable_pitcher_id'],800048)
  self.assertEqual(row['probable_status'],'OFFICIAL_SCHEDULE_PROBABLE_NOT_CONFIRMED')
  self.assertGreater(row['lead_minutes'],600)
  self.assertLess(row['lead_minutes'],720)

 def test_live_or_after_kickoff_or_start_time_tbd_never_captured(self):
  self.assertEqual(parse_schedule(fixture_schedule(fixture_game(status='In Progress')),NOW),[])
  self.assertEqual(parse_schedule(fixture_schedule(fixture_game(start='2026-10-08T12:50:00Z')),NOW),[])
  self.assertEqual(parse_schedule(fixture_schedule(fixture_game(start='2026-10-15T00:00:00Z')),NOW,lookahead_hours=48),[])
  source=fixture_game();source['startTimeTBD']=True
  self.assertEqual(parse_schedule(fixture_schedule(source),NOW),[])

 def test_postgame_boxscore_lineup_cannot_masquerade_as_pregame(self):
  self.assertEqual(extract_official_pregame_lineups(fixture_feed(nine=False),849832,NOW,START)['status'],'NOT_YET_PUBLISHED')
  rec=extract_official_pregame_lineups(fixture_feed(nine=True),849832,NOW,START)
  self.assertEqual(rec['status'],'OFFICIAL_BATTING_ORDER_VISIBLE_BEFORE_KICKOFF')
  self.assertEqual(len(rec['away']['player_ids']),9)
  self.assertEqual(rec['away']['source'],'LIVE_FEED_OFFICIAL_BATTING_ORDER_CAPTURED_PREGAME')
  live=extract_official_pregame_lineups(fixture_feed(status='In Progress',nine=True),849832,NOW,START)
  self.assertEqual(live['status'],'FEED_IS_NOT_PREGAME')
  after=extract_official_pregame_lineups(fixture_feed(nine=True),849832,datetime(2026,10,9,1,tzinfo=timezone.utc),START)
  self.assertEqual(after['status'],'CAPTURE_NOT_BEFORE_KICKOFF')

 def test_nws_forecast_is_asof_and_event_hour_not_future_actual_weather(self):
  x=extract_nws_hourly_forecast(fixture_nws(),NOW,START,source_url='https://api.weather.gov/gridpoints/LOT/76,71/forecast/hourly')
  self.assertEqual(x['status'],'CAPTURED_NWS_FORECAST_NOT_OBSERVED_WEATHER')
  self.assertEqual(x['forecast_temperature_f'],57)
  self.assertEqual(x['forecast_wind_mph'],9)
  self.assertEqual(x['forecast_precipitation_probability_pct'],10)
  self.assertLess(x['forecast_generated_at_utc'],NOW.isoformat())
  j=fixture_nws();j['properties']['generatedAt']='2026-10-08T15:00:00Z'
  self.assertEqual(extract_nws_hourly_forecast(j,NOW,START,source_url='noaa')['status'],'FORECAST_GENERATED_AFTER_CAPTURE')

 def test_park_coordinates_not_used_when_neutral_venue_differs_from_prior_official_home(self):
  master=pd.DataFrame([dict(gamePk=i,officialDate='2025-07-10',gameType='R',status='Final',
      home_team='Chicago White Sox',venue_id=4,venue='Rate Field') for i in range(80)])
  good=resolve_venue_coordinates(fixture_game(),master)
  self.assertEqual(good['status'],'PRIOR_OFFICIAL_VENUE_ID_MATCHED')
  self.assertIsInstance(good['latitude'],float)
  wrong=resolve_venue_coordinates(fixture_game(venue_id=999),master)
  self.assertEqual(wrong['status'],'VENUE_COORDINATES_NOT_VERIFIED')
  self.assertNotIn('latitude',wrong)

 def test_evidence_fields_exclude_results_and_only_actual_asof_sources(self):
  schedule=parse_schedule(fixture_schedule(),NOW)[0]
  rec=compose_evidence(schedule,NOW,feed_lineups={'status':'NOT_YET_PUBLISHED'},weather={'status':'NOT_CHECKED'})
  self.assertEqual(rec['schema'],'MLB_PREGAME_SOURCE_EVIDENCE_V1')
  self.assertLess(rec['captured_at_utc'],rec['first_pitch_utc'])
  self.assertNotIn('home_score',str(rec))
  self.assertNotIn('away_score',str(rec))
  self.assertNotIn('settled',json.dumps(rec).lower())
  self.assertFalse(rec['historical_model_approved'])
  self.assertFalse(rec['is_confirmed_starting_pitcher'])


class CollectorBehaviorTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.ledger=Path(self.tmp.name)/'MLB_PREGAME_EVIDENCE.jsonl'

 def test_append_only_replay_same_interval_is_idempotent_with_prior_record_unchanged(self):
  schedule=parse_schedule(fixture_schedule(),NOW)[0]
  rec=compose_evidence(schedule,NOW,feed_lineups={'status':'NOT_YET_PUBLISHED'},weather={'status':'NOT_CHECKED'})
  self.assertTrue(append_snapshot_once(self.ledger,rec))
  before=self.ledger.read_bytes()
  self.assertFalse(append_snapshot_once(self.ledger,rec))
  self.assertEqual(self.ledger.read_bytes(),before)
  later=compose_evidence(schedule,NOW+timedelta(minutes=11),feed_lineups={'status':'NOT_YET_PUBLISHED'},weather={'status':'NOT_CHECKED'})
  self.assertTrue(append_snapshot_once(self.ledger,later))
  self.assertEqual(len(self.ledger.read_text().splitlines()),2)
  self.assertEqual(json.loads(self.ledger.read_text().splitlines()[0]),rec)

 def test_full_slate_preserves_all_probable_pitcher_rows_and_caps_expensive_live_feed(self):
  games=[]
  for index in range(15):
   game=fixture_game(game_pk=900001+index,start='2026-10-08T16:00:00Z')
   game['teams']['home']['team']['id']=145+index
   game['teams']['home']['team']['name']=f'Home Team {index}'
   game['teams']['away']['team']['id']=300+index
   game['teams']['away']['team']['name']=f'Away Team {index}'
   games.append(game)
  fetched=[]
  def mock_get(url,params=None):
   fetched.append(url)
   if '/schedule' in url:return fixture_schedule(*games)
   if '/feed/live' in url:
    pk=int(url.split('/game/')[1].split('/')[0]);j=fixture_feed(start='2026-10-08T16:00:00Z');j['gamePk']=pk
    return j
   raise AssertionError(url)
  outcome=capture_once(self.ledger,now=NOW,fetch_json=mock_get,weather_enabled=False,feed_max_games=4)
  self.assertEqual(outcome['games_eligible'],15)
  self.assertEqual(outcome['added'],15)
  self.assertEqual(len([u for u in fetched if '/feed/live' in u]),4)
  self.assertEqual(len(self.ledger.read_text().splitlines()),15)
  self.assertEqual(len({json.loads(v)['game_pk'] for v in self.ledger.read_text().splitlines()}),15)

 def test_hourly_snapshots_avoid_repeated_full_history_for_games_far_from_kickoff(self):
  calls=[]
  def fetch(url,params=None):
   calls.append(url)
   if '/schedule' in url:return fixture_schedule()
   raise AssertionError('Should not query live boxscore 11h before first pitch')
  a=capture_once(self.ledger,now=NOW,fetch_json=fetch,weather_enabled=False)
  b=capture_once(self.ledger,now=NOW+timedelta(minutes=10),fetch_json=fetch,weather_enabled=False)
  c=capture_once(self.ledger,now=NOW+timedelta(hours=1),fetch_json=fetch,weather_enabled=False)
  self.assertEqual((a['added'],b['added'],c['added']),(1,0,1))
  self.assertEqual(c['existing_time_slots_preserved'],0)
  self.assertEqual(len(self.ledger.read_text().splitlines()),2)
  self.assertTrue(all(json.loads(v)['capture_interval_minutes']==60 for v in self.ledger.read_text().splitlines()))

 def test_if_live_feed_reports_already_started_do_not_store_as_pregame(self):
  soon='2026-10-08T16:00:00Z'
  def fetch(url,params=None):
   if '/schedule' in url:return fixture_schedule(fixture_game(start=soon))
   return fixture_feed(start=soon,status='In Progress',nine=True)
  out=capture_once(self.ledger,now=NOW,fetch_json=fetch,weather_enabled=False)
  self.assertEqual(out['added'],0)
  self.assertEqual(out['started_during_capture'],1)
  self.assertFalse(self.ledger.exists())

 def test_rotating_live_feed_budget_covers_full_slate_before_first_pitch(self):
  soon='2026-10-08T16:00:00Z'
  games=[]
  for i in range(15):
   game=fixture_game(game_pk=900100+i,start=soon)
   game['teams']['home']['team']={'id':100+i,'name':f'Home {i}'}
   game['teams']['away']['team']={'id':300+i,'name':f'Away {i}'}
   games.append(game)
  queried=[]
  def fetch(url,params=None):
   if '/schedule' in url:return fixture_schedule(*games)
   pk=int(url.split('/game/')[1].split('/')[0]);queried.append(pk)
   j=fixture_feed(start=soon);j['gamePk']=pk
   return j
  for tick in range(15):
   outcome=capture_once(self.ledger,now=NOW+timedelta(minutes=tick*10),
        fetch_json=fetch,weather_enabled=False,feed_max_games=4)
   self.assertEqual(outcome['games_eligible'],15)
  self.assertEqual(len(set(queried)),15)
  self.assertLessEqual(len(queried),15*4)

 def test_mock_api_collector_does_not_fetch_game_after_start_or_postgame_feed(self):
  called=[]
  def mock_fetch(url,params=None):
   called.append(url)
   if '/schedule' in url:return fixture_schedule(fixture_game(start='2026-10-08T16:00:00Z'))
   if '/feed/live' in url:return fixture_feed(nine=False,start='2026-10-08T16:00:00Z')
   raise AssertionError(f'Unexpected network: {url}')
  output=capture_once(self.ledger,now=NOW,fetch_json=mock_fetch,weather_enabled=False)
  self.assertEqual(output['added'],1)
  self.assertEqual(output['lineups']['NOT_YET_PUBLISHED'],1)
  self.assertEqual(output['games_eligible'],1)
  self.assertEqual(output['errors'],0)
  self.assertEqual(len(called),2)
  self.assertEqual(capture_once(self.ledger,now=NOW,fetch_json=mock_fetch,weather_enabled=False)['added'],0)

if __name__=='__main__':unittest.main()
