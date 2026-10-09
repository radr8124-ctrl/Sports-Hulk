"""MLB official schedule fixture / source time acceptance, source-only research.

Never change a sportsbook selection or grade merely to pass the gate.
"""
import copy
import json
import unittest
from pathlib import Path
import pandas as pd
from intelligence_warehouse.betting_v2 import mlb_official_fixture_clock as clock
from intelligence_warehouse.betting_v2.mlb_forward_capture_identity import frozen_mlb_identity

SCHEDULE=pd.DataFrame([
 {'gamePk':849831,'gameType':'D','gameDate':'2026-10-11T00:00:00Z',
  'away_team':'Chicago White Sox','home_team':'Cleveland Guardians'},
 {'gamePk':849809,'gameType':'L','gameDate':'2026-10-12T00:00:00Z',
  'away_team':'Los Angeles Dodgers','home_team':'Milwaukee Brewers'},
])
IDENTITY={
 'mlb_source_player_id':'672275','mlb_source_player_name':'Patrick Bailey',
 'mlb_source_player_team':'Cleveland Guardians',
 'mlb_source_away_team':'Chicago White Sox',
 'mlb_source_home_team':'Cleveland Guardians',
 'mlb_source_original_start':'2026-10-11T00:00:00Z',
 'mlb_source_identity_provenance':'MLB_DECISION_EXPLICIT_PLAYER_ID_TEAM',
}

class TestMLBOfficialClockGate(unittest.TestCase):
 def setUp(self):
  self.games=clock.schedule_index(SCHEDULE)

 def test_exact_official_match_returns_proven_game_and_competition(self):
  result=clock.crosswalk(IDENTITY,self.games)
  self.assertEqual(result['mlb_official_gamePk'],'849831')
  self.assertEqual(result['competition_regime'],'POSTSEASON_DIVISION_SERIES')
  self.assertEqual(result['mlb_provider_start_delta_seconds'],0)
  self.assertTrue(result['mlb_official_fixture_verified'])
  self.assertFalse(result['mlb_original_source_market_offer_executable_verified'])
  self.assertFalse(result['mlb_roster_membership_officially_verified_for_this_game'])

 def test_three_hour_source_clock_mismatch_never_passes_as_current(self):
  variant={**IDENTITY,'mlb_source_original_start':'2026-10-10T21:00:00+00:00'}
  self.assertIsNone(clock.crosswalk(variant,self.games))
  correct={**IDENTITY,'mlb_source_original_start':'2026-10-11T00:01:00+00:00'}
  matched=clock.crosswalk(correct,self.games)
  self.assertEqual(matched['mlb_provider_start_delta_seconds'],60)

 def test_conflicting_official_schedule_games_or_doubleheader_fail_closed(self):
  suspect=pd.concat([SCHEDULE,SCHEDULE.iloc[[0]]],ignore_index=True)
  suspect.at[2,'gamePk']=849999
  self.assertIsNone(clock.crosswalk(IDENTITY,clock.schedule_index(suspect)))

 def test_player_must_belong_to_competing_club_in_original_source(self):
  fake={**IDENTITY,'mlb_source_player_team':'New York Mets'}
  self.assertIsNone(clock.crosswalk(fake,self.games))
  fake2={**IDENTITY,'mlb_source_away_team':'Milwaukee Brewers'}
  self.assertIsNone(clock.crosswalk(fake2,self.games))
  fake3={**IDENTITY,'mlb_source_identity_provenance':'INFERRED_FROM_PLAYER_NAME'}
  self.assertIsNone(clock.crosswalk(fake3,self.games))

 def test_no_sportsbook_uuid_is_reported_as_official_gamePk(self):
  r=clock.crosswalk(IDENTITY,self.games)
  self.assertEqual(r['mlb_official_gamePk'],'849831')
  self.assertNotIn('event_id',r)
  self.assertNotIn('mlb_player_id',r)
  self.assertNotIn('american_odds',r)

 def test_unsupported_schedule_game_type_and_missing_data_fail(self):
  wrong=SCHEDULE.copy()
  wrong.at[0,'gameType']='UNKNOWN'
  self.assertIsNone(clock.crosswalk(IDENTITY,clock.schedule_index(wrong)))
  self.assertEqual(clock.schedule_index(pd.DataFrame()),{})
  self.assertIsNone(clock.crosswalk({},self.games))
  self.assertEqual(clock.int_pk(None),None)
  self.assertEqual(clock.int_pk(True),None)

 def test_original_pinned_246_records_have_228_verified_and_18_quarantined(self):
  b=Path('.deploy_backups/zenith_mlb_official_fixture_clock_gate_20261009T201600Z')
  if not (b/'prop_v2_current.json').is_file() or not (b/'MLB_SCHEDULE.csv').is_file():
   self.skipTest('Frozen original source audit snapshot is local to the VPS')
  original=json.loads((b/'prop_v2_current.json').read_text())
  recorded=[p for p in original['picks'] if p.get('sport')=='MLB']
  games=clock.schedule_index(pd.read_csv(b/'MLB_SCHEDULE.csv'))
  x=[clock.crosswalk(frozen_mlb_identity(p),games) for p in recorded]
  valid=[row for row,value in zip(recorded,x) if value]
  held=[row for row,value in zip(recorded,x) if not value]
  self.assertEqual(len(recorded),246)
  self.assertEqual((len(valid),len(held)),(228,18))
  self.assertEqual({r['event_start'] for r in held},{'2026-10-10 21:00:00+00:00'})
  self.assertEqual({r['event_id'] for r in held},{'d138f690-86fb-4c9b-ba5f-53e580a469d5'})
  self.assertEqual({value['mlb_official_gamePk'] for value in x if value},{'849831','849809'})
  self.assertFalse(any(r['shadow_decision'] in ('SHADOW_PLAY','SHADOW_LEG') for r in recorded))


if __name__=='__main__':unittest.main()
