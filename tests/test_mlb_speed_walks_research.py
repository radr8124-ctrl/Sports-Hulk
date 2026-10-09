"""Expanded MLB model may learn ONLY from prior-season speed and prequote walks."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime,timedelta,timezone
import unittest

import numpy as np
import pandas as pd

from intelligence_warehouse.historical_recovery.mlb_speed_walks_research import (
    enrich_provenance_sample, speed_walk_vector, freeze_speed_walks_model,
    evaluate_known_july_diagnostic, NEW_FEATURE_NAMES,
)
from tests.test_hf_mlb_prop_context_model import sample
from intelligence_warehouse.historical_recovery.mlb_asof_feature_store import (
    FEATURE_SCOPE,FEATURE_VERSION,
)


def record(i=0,*,status='VERIFIED_HISTORICAL',start_day=4):
    row=sample(i,status=status)
    row['official_player_id']=501
    return row


def game_store(rows):
    entries=[]
    for i,r in enumerate(rows):
        start=pd.to_datetime(r['official_start'],utc=True)
        entries.append({
            'game_pk':r['official_game_pk'],'player_id':501,
            'official_start':start.isoformat(),
            'prior_sprint_speed_ft_per_sec':29.2,
            'prior_bat_speed_mph':75.4,
            'sprint_speed_observed':True,
            'bat_speed_observed':True,
            'prior_last5_walks_avg':0.75,
            'prior_pregame_sample_floor_5_games_met':True,
            'prior_games_count':7,
            'prior_last_date':(start-timedelta(days=2)).date().isoformat(),
            'source_time_class':FEATURE_SCOPE,
            'feature_version':FEATURE_VERSION,
            'prior_completed_season':2025,
            'source_proven_at_time_of_original_quote':False,
            'roster_selection_known_before_game':False,
            'live_betting_approved':False,
        })
    return pd.DataFrame(entries)


class MLBNewSpeedWalksTests(unittest.TestCase):
    def test_exact_identity_and_quote_time_enrichment(self):
        rows=[record()]
        out=enrich_provenance_sample(rows,game_store(rows),target_season=2026)
        self.assertEqual(len(out),1)
        self.assertTrue(out[0]['sprint_speed_observed'])
        self.assertTrue(out[0]['bat_speed_observed'])
        self.assertTrue(out[0]['walks_quote_time_safe'])
        self.assertEqual(len(speed_walk_vector(out[0])),16)
        self.assertEqual(len(NEW_FEATURE_NAMES),6)
        self.assertFalse(out[0]['original_live_feature_capture_verified'])

    def test_same_season_or_wrong_game_key_fails_closed(self):
        rows=[record()]
        source=game_store(rows)
        source.loc[0,'prior_completed_season']=2026
        with self.assertRaisesRegex(ValueError,'prior.*season'):
            enrich_provenance_sample(rows,source)
        source=game_store(rows)
        source.loc[0,'player_id']=999
        with self.assertRaisesRegex(ValueError,'game.player'):
            enrich_provenance_sample(rows,source)

    def test_postquote_walking_stats_not_available_even_before_first_pitch(self):
        rows=[record()]
        source=game_store(rows)
        quote=pd.to_datetime(rows[0]['ts'],utc=True)
        source.loc[0,'prior_last_date']=quote.date().isoformat()
        out=enrich_provenance_sample(rows,source)[0]
        vec=speed_walk_vector(out)
        self.assertFalse(out['walks_quote_time_safe'])
        self.assertEqual(vec[-2],0)
        self.assertEqual(vec[-1],0)

    def test_missing_sprint_or_bat_does_not_filter_bookmaker_odds(self):
        rows=[record()]
        source=game_store(rows)
        source.loc[0,'prior_sprint_speed_ft_per_sec']=None
        source.loc[0,'prior_bat_speed_mph']=None
        source.loc[0,'sprint_speed_observed']=False
        source.loc[0,'bat_speed_observed']=False
        out=enrich_provenance_sample(rows,source)
        self.assertEqual(len(out),1)
        vec=speed_walk_vector(out[0])
        self.assertEqual(vec[10:14],[0,0,0,0])
        self.assertEqual(vec[14],(0.75-0.5)/1.5)

    def test_changing_eventual_result_or_event_side_only_uses_side_for_feature_direction(self):
        rows=[record()]
        enriched=enrich_provenance_sample(rows,game_store(rows))
        a=speed_walk_vector(enriched[0])
        changed=deepcopy(enriched[0])
        changed['verified_win']=not changed['verified_win']
        changed['official_stat']=99999
        self.assertEqual(a,speed_walk_vector(changed))
        side=deepcopy(enriched[0])
        side['side']='under'
        b=speed_walk_vector(side)
        self.assertAlmostEqual(a[10],-b[10])
        self.assertAlmostEqual(a[12],-b[12])
        self.assertAlmostEqual(a[14],-b[14])

    def test_invalid_market_price_or_duplicate_game_ids_cannot_train(self):
        rows=[record(i) for i in range(70)]
        for i,r in enumerate(rows):r['official_player_id']=501
        table=game_store(rows)
        enriched=enrich_provenance_sample(rows,table)
        frozen=freeze_speed_walks_model(enriched)
        self.assertEqual(frozen['training_independent_games'],70)
        self.assertEqual(len(frozen['market_calibration_beta']),2)
        self.assertEqual(len(frozen['prior_context_beta']),10)
        self.assertEqual(len(frozen['with_speed_walks_beta']),16)
        self.assertFalse(frozen['live_plays_approved'])
        enriched[4]['official_game_pk']=enriched[3]['official_game_pk']
        with self.assertRaisesRegex(ValueError,'[Dd]uplicate'):
            freeze_speed_walks_model(enriched)

    def test_only_vendor_graded_training_and_after_cutoff_july_evaluation(self):
        train=[record(i) for i in range(70)]
        enriched=enrich_provenance_sample(train,game_store(train))
        frozen=freeze_speed_walks_model(enriched)
        before=deepcopy(frozen)
        later=[record(110+i,status='OFFICIAL_DERIVED_HISTORICAL') for i in range(30)]
        test=enrich_provenance_sample(later,game_store(later))
        result=evaluate_known_july_diagnostic(frozen,test)
        self.assertEqual(result['status'],'SECONDARY_HISTORICAL_RECHECK_NOT_UNSEEN')
        self.assertEqual(result['test_independent_games'],30)
        self.assertTrue(result['no_game_id_overlap'])
        self.assertEqual(result['live_plays_approved'],False)
        self.assertIn('speed_walks_vs_prior_context_clustered_95pct_brier_gain_interval',result)
        self.assertEqual(frozen,before)
        bad=deepcopy(enriched);bad[0]['status']='OFFICIAL_DERIVED_HISTORICAL'
        with self.assertRaisesRegex(ValueError,'vendor'):
            freeze_speed_walks_model(bad)

if __name__=='__main__':unittest.main()
