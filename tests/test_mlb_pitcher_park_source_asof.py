"""Prior completed pitcher games + prior-season venue only, no postgame leak."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from pathlib import Path
import copy
import hashlib
import json
import tempfile
import unittest

import pandas as pd

from intelligence_warehouse.historical_recovery.mlb_pitcher_park_source_asof import (
    reconcile_official_pitcher_history,
    prior_season_park,
    construct_true_pregame_pitcher_park,
    append_once_source_context,
)

NOW=datetime(2026,10,8,23,17,tzinfo=timezone.utc)
FIRST=datetime(2026,10,9,0,0,tzinfo=timezone.utc)
SOURCE_TIME=NOW-timedelta(hours=2)
FROZEN_TIME=NOW-timedelta(hours=2,minutes=-3)

def orig_event():
    p={
        'schema':'MLB_PREGAME_SOURCE_EVIDENCE_V1',
        'game_pk':849832,
        'evidence_id':'EVIDENCE_FIXTURE_V1',
        'captured_at_utc':SOURCE_TIME.isoformat(),
        'first_pitch_utc':FIRST.isoformat(),
        'fixture':{
          'venue_id':4,'venue':'Test Field','home_team':'Chicago White Sox',
          'away_team':'Cleveland Guardians','official_status_at_capture':'Pre-Game',
          'official_date':'2026-10-08',
        },
        'probable_pitchers':{
          'away_probable_pitcher_id':800048,
          'home_probable_pitcher_id':696146,
          'probable_status':'OFFICIAL_SCHEDULE_PROBABLE_NOT_CONFIRMED',
        },
        'lineups':{'status':'ONLY_ONE_TEAM_LINEUP_VISIBLE_PREGAME',
                   'home':{
                     'player_ids':list(range(501,510)),
                     'player_names':[f'Player {i}' for i in range(501,510)],
                     'source':'LIVE_FEED_OFFICIAL_BATTING_ORDER_CAPTURED_PREGAME',
                     'confirmed_asof_capture':True,
                   }},
        'weather':{
          'status':'CAPTURED_NWS_FORECAST_NOT_OBSERVED_WEATHER',
          'forecast_temperature_f':62,'forecast_wind_mph':10,
          'forecast_generated_at_utc':(SOURCE_TIME-timedelta(hours=1)).isoformat(),
          'source_captured_at_utc':SOURCE_TIME.isoformat(),
          'roof_status_asof':'UNKNOWN_NOT_CAPTURED',
        },
    }
    return p

def orig_and_frozen():
    e=orig_event()
    line=json.dumps(e,sort_keys=True)+'\n'
    sha=hashlib.sha256(line.encode()).hexdigest()
    player=[]
    for pid in range(501,510):
      player.append({
        'schema':'MLB_TRUE_PREGAME_RESEARCH_FEATURE_FREEZE_V2',
        'source_history_revision':'OFFICIAL_FINAL_REGULAR_AND_POSTSEASON_V2',
        'game_pk':849832,'player_id':pid,
        'team_side_at_capture':'home',
        'source_evidence_id':e['evidence_id'],
        'source_capture_at_utc':e['captured_at_utc'],
        'feature_frozen_at_utc':(SOURCE_TIME+timedelta(minutes=3)).isoformat(),
        'scheduled_first_pitch_utc':e['first_pitch_utc'],
        'original_append_only_line_sha256':sha,
        'opposing_probable_pitcher_id':800048,
        'live_play_approved':False,
        'betting_prediction_written':False,
      })
    return line,e,player

def games():
    l=[]
    for i in range(90):
        day=pd.Timestamp('2025-04-01T18:00:00Z')+pd.Timedelta(days=i)
        l.append({
          'gamePk':i+100,'officialDate':day.date().isoformat(),
          'gameDate':day.isoformat(),
          'gameType':'R','status':'Final',
          'venue_id':4,'home_team':'Chicago White Sox',
          'away_team':'Cleveland Guardians',
          'home_score':4,'away_score':5,
        })
    l.append({
      'gamePk':500,'officialDate':'2026-10-05','gameDate':'2026-10-05T18:00:00Z',
      'gameType':'D','status':'Final','venue_id':4,
      'home_team':'Chicago White Sox','away_team':'Cleveland Guardians',
      'home_score':4,'away_score':5,
    })
    l.append({
      'gamePk':501,'officialDate':'2026-10-07','gameDate':'2026-10-07T19:00:00Z',
      'gameType':'D','status':'Final','venue_id':4,
      'home_team':'Chicago White Sox','away_team':'Cleveland Guardians',
      'home_score':4,'away_score':5,
    })
    l.append({
      'gamePk':849832,'officialDate':'2026-10-08','gameDate':'2026-10-08T21:00:00Z',
      'gameType':'D','status':'Scheduled','venue_id':4,
      'home_team':'Chicago White Sox','away_team':'Cleveland Guardians',
      'home_score':None,'away_score':None,
    })
    return pd.DataFrame(l)

def old_pitching():
    return pd.DataFrame([
        {'game_pk':500,'player_id':800048,'season':2026,'official_date':'2026-10-05',
         'game_date':'2026-10-05T18:00:00Z','status':'Final','game_type':'D',
         'group':'PITCHING','team':'Cleveland Guardians','games_started':1,
         'outs':18,'hits_allowed':4,'walks_allowed':2,'strikeouts':6,'home_runs_allowed':0},
    ])

def recent_pitching():
    return pd.DataFrame([
        {'gamePk':500,'player_id':800048,'season':2026,'officialDate':'2026-10-05',
         'group':'PITCHING','team':'Cleveland Guardians','games_started':1,
         'outs':18,'hits_allowed':4,'walks_allowed':2,'pitcher_strikeouts':6,'home_runs_allowed':0},
        {'gamePk':501,'player_id':800048,'season':2026,'officialDate':'2026-10-07',
         'group':'PITCHING','team':'Cleveland Guardians','games_started':1,
         'outs':15,'hits_allowed':3,'walks_allowed':1,'pitcher_strikeouts':4,'home_runs_allowed':1},
    ])

class VerifiedMLBPitchParkResearchTests(unittest.TestCase):
    def test_2025_park_factor_never_reads_same_or_future_season(self):
        league=games()
        reference,proof=prior_season_park(league,venue_id=4,source_year=2026,
                                          home_team='Chicago White Sox',min_park_games=40)
        self.assertEqual(proof['source_completed_park_season'],2025)
        self.assertEqual(proof['prior_regular_season_park_games'],90)
        self.assertAlmostEqual(reference,1.)
        self.assertEqual(proof['same_season_or_future_games_used'],0)
        with self.assertRaisesRegex(ValueError,'prior.*park'):
            prior_season_park(league[league.officialDate.astype(str).str.startswith('2026')],
                              venue_id=4,source_year=2026,home_team='Chicago White Sox',min_park_games=40)

    def test_strict_incremental_pitcher_merge_conserves_stats_and_adds_new_final(self):
        reconciled,proof=reconcile_official_pitcher_history(old_pitching(),recent_pitching(),games())
        self.assertEqual(proof['verified_overlap_pitcher_player_games'],1)
        self.assertEqual(proof['new_final_pitcher_player_game_rows'],1)
        self.assertEqual(proof['stat_source_conflict_count'],0)
        self.assertEqual(len(reconciled),2)
        self.assertEqual(reconciled.game_pk.unique().tolist(),[500,501])

    def test_changed_old_vs_new_pitching_stats_halt_instead_of_rewriting(self):
        altered=recent_pitching()
        altered.loc[altered.gamePk.eq(500),'hits_allowed']=99
        with self.assertRaisesRegex(ValueError,'conflict'):
            reconcile_official_pitcher_history(old_pitching(),altered,games())
        altered=recent_pitching()
        altered.loc[altered.gamePk.eq(501),'officialDate']='2026-10-02'
        with self.assertRaisesRegex(ValueError,'official date'):
            reconcile_official_pitcher_history(old_pitching(),altered,games())

    def test_non_final_or_future_pitcher_games_never_in_pregame_features(self):
        untrusted=recent_pitching()
        invalid=untrusted.iloc[[-1]].copy()
        invalid.loc[:,'gamePk']=849832
        invalid.loc[:,'officialDate']='2026-10-08'
        invalid.loc[:,'hits_allowed']=1000
        joined=pd.concat([untrusted,invalid],ignore_index=True)
        verified,proof=reconcile_official_pitcher_history(old_pitching(),joined,games())
        self.assertEqual(len(verified),2)
        self.assertGreaterEqual(proof['not_final_or_unsupported_rows_rejected'],1)

    def test_original_event_source_sha_and_pitcher_probable_only_frozen(self):
        raw,event,v2=orig_and_frozen()
        hist,_=reconcile_official_pitcher_history(old_pitching(),recent_pitching(),games())
        feature,receipt=construct_true_pregame_pitcher_park(raw,event,v2,
                            hist,games(),now=NOW,min_pitcher_prior_games=2,min_park_games=40)
        self.assertEqual(len(feature),9)
        r=feature[0]
        self.assertEqual(r['opposing_probable_pitcher_id'],800048)
        self.assertEqual(r['opposing_probable_pitcher_prior_game_count'],2)
        self.assertEqual(r['opposing_probable_pitcher_prior_hits_allowed_total'],7)
        self.assertEqual(r['original_batting_order_line_sha256'],hashlib.sha256(raw.encode()).hexdigest())
        self.assertEqual(r['prior_park_venue_id'],4)
        self.assertFalse(r['opposing_probable_pitcher_confirmed_starter'])
        self.assertTrue(r['stale_game_master_first_pitch_disagreement_flag'])
        self.assertEqual(r['reference_prior_full_park_season'],2025)
        self.assertTrue(r['frozen_before_source_scheduled_first_pitch'])
        self.assertFalse(r['model_probabilities_predicted'])
        self.assertFalse(r['betting_picks_created'])

    def test_stale_latest_game_master_timestamp_is_not_accepted_as_truth(self):
        raw,event,v2=orig_and_frozen()
        hist,_=reconcile_official_pitcher_history(old_pitching(),recent_pitching(),games())
        out,_=construct_true_pregame_pitcher_park(raw,event,v2,hist,games(),now=NOW,
                                                   min_pitcher_prior_games=2,min_park_games=40)
        self.assertEqual(out[0]['official_source_game_first_pitch_utc'],FIRST.isoformat())
        self.assertNotEqual(out[0]['official_source_game_first_pitch_utc'],
                            games().loc[games().gamePk.eq(849832),'gameDate'].iloc[0])

    def test_same_day_past_game_cannot_poison_stats(self):
        raw,event,v2=orig_and_frozen()
        verified,_=reconcile_official_pitcher_history(old_pitching(),recent_pitching(),games())
        poisoned=verified.copy()
        additional=verified.iloc[[-1]].copy()
        additional['game_pk']=849832
        additional['official_date']='2026-10-08'
        additional['hits_allowed']=10000
        poisoned=pd.concat([poisoned,additional],ignore_index=True)
        output,_=construct_true_pregame_pitcher_park(raw,event,v2,poisoned,games(),now=NOW,min_pitcher_prior_games=2,min_park_games=40)
        self.assertEqual(output[0]['opposing_probable_pitcher_prior_hits_allowed_total'],7)
        self.assertEqual(output[0]['opposing_probable_pitcher_prior_game_count'],2)

    def test_forged_lineup_missing_sha_or_model_live_rejected(self):
        raw,event,v2=orig_and_frozen()
        verified,_=reconcile_official_pitcher_history(old_pitching(),recent_pitching(),games())
        bad=copy.deepcopy(v2)
        bad[0]['original_append_only_line_sha256']='e'*64
        with self.assertRaisesRegex(ValueError,'[Oo]riginal.*SHA|lineup'):
            construct_true_pregame_pitcher_park(raw,event,bad,verified,games(),now=NOW,min_pitcher_prior_games=2,min_park_games=40)
        bad=copy.deepcopy(v2)
        bad[0]['live_play_approved']=True
        with self.assertRaisesRegex(ValueError,'research'):
            construct_true_pregame_pitcher_park(raw,event,bad,verified,games(),now=NOW,min_pitcher_prior_games=2,min_park_games=40)

    def test_finished_game_never_backdates_pitch_park_context(self):
        raw,event,v2=orig_and_frozen()
        verified,_=reconcile_official_pitcher_history(old_pitching(),recent_pitching(),games())
        out,proof=construct_true_pregame_pitcher_park(raw,event,v2,verified,games(),
                                       now=FIRST+timedelta(minutes=1),
                                       min_pitcher_prior_games=2,min_park_games=40)
        self.assertEqual(out,[])
        self.assertEqual(proof['status'],'PAST_FIRST_PITCH_CONTEXT_FREEZE_REFUSED')

    def test_same_original_first_source_immutable_idempotent_append(self):
        raw,event,v2=orig_and_frozen()
        hist,_=reconcile_official_pitcher_history(old_pitching(),recent_pitching(),games())
        data,_=construct_true_pregame_pitcher_park(raw,event,v2,hist,games(),now=NOW,
                                             min_pitcher_prior_games=2,min_park_games=40)
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'MLB_V3_CONTEXT.jsonl'
            self.assertEqual(append_once_source_context(dest,data),9)
            before=dest.read_bytes()
            self.assertEqual(append_once_source_context(dest,data),0)
            self.assertEqual(dest.read_bytes(),before)
            changed=copy.deepcopy(data)
            changed[0]['opposing_probable_pitcher_prior_hits_allowed_total']=999
            with self.assertRaisesRegex(ValueError,'conflict'):
                append_once_source_context(dest,changed)
            self.assertEqual(dest.read_bytes(),before)

if __name__=='__main__':unittest.main()
