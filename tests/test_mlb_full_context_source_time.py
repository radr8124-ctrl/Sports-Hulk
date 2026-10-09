"""Pre-quote 16-term context is built from ONLY earlier completed official games."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import tempfile
import unittest

import pandas as pd

from intelligence_warehouse.historical_recovery.mlb_full_context_source_time import (
    build_frozen_prequote_full_context,
    append_original_prequote_full_context,
    BASE_CONTEXT_KEYS,
)

NOW=datetime(2026,10,8,23,22,tzinfo=timezone.utc)
START=datetime(2026,10,9,0,0,tzinfo=timezone.utc)
CUTOFF='2026-10-08'
SHA='a'*64

def original_v2():
    return {
      'schema':'MLB_TRUE_PREGAME_RESEARCH_FEATURE_FREEZE_V2',
      'source_history_revision':'OFFICIAL_FINAL_REGULAR_AND_POSTSEASON_V2',
      'game_pk':849832,'player_id':501,'team_side_at_capture':'home',
      'source_evidence_id':'OFFICIAL_V1_SOURCE',
      'original_append_only_line_sha256':SHA,
      'source_capture_at_utc':'2026-10-08T20:45:00Z',
      'feature_frozen_at_utc':'2026-10-08T20:50:00Z',
      'scheduled_first_pitch_utc':START.isoformat(),
      'prior_last5_hits_avg':1.2,'prior_last5_walks_avg':0.6,
      'prior_history_at_least_5_completed_games':True,
      'last_prior_date':'2026-10-07',
      'prior_speed_observed':True,'prior_sprint_speed_ft_per_sec':29.,
      'prior_bat_observed':True,'prior_bat_speed_mph':75.,
      'live_play_approved':False,'betting_prediction_written':False,
    }

def original_v3():
    return {
      'schema':'MLB_V3_TRUE_PREGAME_PROBABLE_PITCHER_AND_PRIOR_2025_PARK_RESEARCH_V1',
      'official_game_pk':849832,'mlbam_player_id':501,
      'original_batting_order_line_sha256':SHA,
      'original_pregame_evidence_id':'OFFICIAL_V1_SOURCE',
      'source_pitcher_and_park_context_frozen_at_utc':'2026-10-08T23:16:17Z',
      'official_source_game_first_pitch_utc':START.isoformat(),
      'reference_prior_full_park_season':2025,
      'prior_regular_season_park_games':79,
      'prior_park_run_factor':0.955922,
      'source_opponent_team':'Cleveland Guardians',
      'source_team_side':'home',
      'opposing_probable_pitcher_id':800048,
      'opposing_probable_pitcher_confirmed_starter':False,
      'live_play_approved':False,'model_probabilities_predicted':False,
    }

def hitter_games():
    result=[]
    for n in range(1,12):
        day=f'2026-09-{n:02d}'
        result.append({
          'game_pk':1000+n,'player_id':501,'group':'HITTING',
          'source_verified_before_quote_required':True,
          'status':'Final','game_type':'R',
          'official_date':day,'game_date':pd.Timestamp(day+'T18:00:00Z'),
          'team':'Chicago White Sox','opponent':'Cleveland Guardians',
          'plate_appearances':4.,'hits':1.,
          'walks':1.,'stolen_bases':0.,
        })
    return pd.DataFrame(result)

def pitcher_games():
    result=[]
    for n in range(1,12):
        day=f'2026-09-{n:02d}'
        result.append({
            'game_pk':1000+n,'player_id':660000+n,'group':'PITCHING',
            'source_verified_before_quote_required':True,
            'status':'Final','game_type':'R',
            'official_date':day,'game_date':pd.Timestamp(day+'T18:00:00Z'),
            'team':'Cleveland Guardians','outs':27.,
            'hits_allowed':9.,'strikeouts':8.,'walks_allowed':1.,
        })
    return pd.DataFrame(result)

def game_master():
    games=[]
    for n in range(1,12):
        day=f'2026-09-{n:02d}'
        games.append({
          'gamePk':1000+n,
          'officialDate':day,'gameDate':day+'T18:00:00Z',
          'gameType':'R','status':'Final',
          'home_team':'Chicago White Sox','away_team':'Cleveland Guardians',
          'home_score':4.,'away_score':5.,
        })
    return pd.DataFrame(games)

class MLBFullContextFromEarlierObservedSourceTests(unittest.TestCase):
    def test_all_fifteen_price_free_inputs_exist_and_source_times_are_prospective(self):
        result,summary=build_frozen_prequote_full_context(
            [original_v2()],[original_v3()],hitter_games(),pitcher_games(),game_master(),now=NOW)
        self.assertEqual(len(result),1)
        first=result[0]
        self.assertEqual(summary['eligible_source_complete_player_contexts'],1)
        self.assertEqual(first['game_pk'],849832)
        self.assertEqual(first['player_id'],501)
        self.assertEqual(len(first['sixteen_model_components_except_market']),14)
        self.assertEqual(first['original_prequote_hitter_source_sha256'],SHA)
        self.assertEqual(first['original_park_completed_season'],2025)
        self.assertEqual(first['prior_opponent_pitching_games'],10)
        self.assertAlmostEqual(first['opp_prior_pitching_hits_allowed_per_9'],9.)
        self.assertAlmostEqual(first['opp_prior_runs_allowed_last10'],4.)
        self.assertAlmostEqual(first['prior_player_last10_pa_role'],4.)
        self.assertAlmostEqual(first['park_prior_year_factor'],0.955922)
        self.assertEqual(first['prior_player_last_date'],'2026-09-11')
        self.assertTrue(first['needs_new_sportsbook_quote_after_context_freeze'])
        self.assertFalse(first['probable_pitcher_is_confirmed'])
        self.assertFalse(first['live_play_approved'])

    def test_same_day_final_or_future_player_and_pitcher_outcome_cannot_poison(self):
        base,_=build_frozen_prequote_full_context(
            [original_v2()],[original_v3()],hitter_games(),pitcher_games(),game_master(),now=NOW)
        h=hitter_games()
        r=h.iloc[[-1]].copy()
        r['game_pk']=949832;r['official_date']=CUTOFF
        r['game_date']=pd.Timestamp('2026-10-08T16:00:00Z')
        r['hits']=99999.;r['plate_appearances']=99999.
        h=pd.concat([h,r],ignore_index=True)
        p=pitcher_games()
        item=p.iloc[[-1]].copy()
        item['game_pk']=949832;item['official_date']=CUTOFF
        item['game_date']=pd.Timestamp('2026-10-08T16:00:00Z')
        item['hits_allowed']=99999.
        p=pd.concat([p,item],ignore_index=True)
        g=game_master()
        extra=g.iloc[[-1]].copy()
        extra['gamePk']=949832;extra['officialDate']=CUTOFF
        extra['gameDate']='2026-10-08T16:00:00Z'
        extra['away_score']=99999.
        g=pd.concat([g,extra],ignore_index=True)
        result,_=build_frozen_prequote_full_context(
            [original_v2()],[original_v3()],h,p,g,now=NOW)
        self.assertEqual(base,result)

    def test_stale_or_forged_pitcher_park_extra_inputs_refused(self):
        v3=original_v3()
        v3['reference_prior_full_park_season']=2026
        with self.assertRaisesRegex(ValueError,'park.*season'):
            build_frozen_prequote_full_context([original_v2()],[v3],
                                               hitter_games(),pitcher_games(),game_master(),now=NOW)
        v3=original_v3()
        v3['original_batting_order_line_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'source.*SHA'):
            build_frozen_prequote_full_context([original_v2()],[v3],
                                               hitter_games(),pitcher_games(),game_master(),now=NOW)
        v3=original_v3()
        v3['source_pitcher_and_park_context_frozen_at_utc']='2026-10-09T00:01:00Z'
        with self.assertRaisesRegex(ValueError,'future.*context|source.*chronology'):
            build_frozen_prequote_full_context([original_v2()],[v3],
                                               hitter_games(),pitcher_games(),game_master(),now=NOW)

    def test_incomplete_opponent_pitcher_history_cannot_make_fabricated_full_model(self):
        p=pitcher_games().iloc[:2]
        rows,audit=build_frozen_prequote_full_context([original_v2()],[original_v3()],
                                            hitter_games(),p,game_master(),now=NOW)
        self.assertEqual(rows,[])
        self.assertEqual(audit['source_ineligible_player_contexts'],1)
        self.assertFalse(audit['full_model_ever_trained_or_changed'])

    def test_missing_official_hitter_role_refuses_full_16_feature_vector(self):
        h=hitter_games().iloc[:3]
        rows,audit=build_frozen_prequote_full_context([original_v2()],[original_v3()],
                                      h,pitcher_games(),game_master(),now=NOW)
        self.assertEqual(rows,[])
        self.assertEqual(audit['eligible_source_complete_player_contexts'],0)

    def test_first_completed_context_immutable_even_if_previous_source_corrected(self):
        good,_=build_frozen_prequote_full_context([original_v2()],[original_v3()],
                                      hitter_games(),pitcher_games(),game_master(),now=NOW)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ORIGINAL_CONTEXT.jsonl'
            self.assertEqual(append_original_prequote_full_context(p,good),1)
            old=p.read_bytes()
            self.assertEqual(append_original_prequote_full_context(p,good),0)
            self.assertEqual(old,p.read_bytes())
            changed=deepcopy(good)
            changed[0]['opp_prior_runs_allowed_last10']=888
            with self.assertRaisesRegex(ValueError,'conflict'):
                append_original_prequote_full_context(p,changed)
            self.assertEqual(old,p.read_bytes())

    def test_no_context_backfill_after_first_pitch(self):
        result,proof=build_frozen_prequote_full_context(
            [original_v2()],[original_v3()],hitter_games(),pitcher_games(),game_master(),
            now=START+timedelta(minutes=1))
        self.assertEqual(result,[])
        self.assertEqual(proof['status'],'FIRST_PITCH_ALREADY_PASSED_NO_CONTEXT_FREEZE')

if __name__=='__main__':unittest.main()
