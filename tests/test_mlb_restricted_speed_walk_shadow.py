"""Restricted source-time speed/bat/walks prospective model is research-only."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import copy
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from intelligence_warehouse.historical_recovery.mlb_restricted_speed_walk_shadow import (
    restricted_train_vector,restricted_live_vector,fit_restricted_training,
    pair_forward_with_live_asof,append_first_restricted_shadow,
    RESTRICTED_NAMES,
)

NOW=datetime(2026,10,8,22,20,tzinfo=timezone.utc)
START=datetime(2026,10,9,0,0,tzinfo=timezone.utc)

def current_v2(*,game=849832,player=123):
    return {
      'schema':'MLB_TRUE_PREGAME_RESEARCH_FEATURE_FREEZE_V2',
      'source_history_revision':'OFFICIAL_FINAL_REGULAR_AND_POSTSEASON_V2',
      'game_pk':game,'player_id':player,
      'team_side_at_capture':'home',
      'source_evidence_id':'official-original-future-lineup-01',
      'original_append_only_line_sha256':'a'*64,
      'source_capture_at_utc':'2026-10-08T20:44:56+00:00',
      'feature_frozen_at_utc':'2026-10-08T20:49:50+00:00',
      'scheduled_first_pitch_utc':START.isoformat(),
      'frozen_before_scheduled_first_pitch':True,
      'completed_season_biomechanics_year':2025,
      'prior_speed_observed':True,'prior_sprint_speed_ft_per_sec':29.0,
      'prior_bat_observed':True,'prior_bat_speed_mph':75.5,
      'prior_history_at_least_5_completed_games':True,
      'prior_last5_walks_avg':0.8,'last_prior_date':'2026-10-07',
      'betting_prediction_written':False,'live_play_approved':False,
    }

def market_control(*,game=849832,player=123,quote='2026-10-08T21:59:44Z',p=.58):
    return {
      'schema':'MLB_V2_TRUE_FORWARD_MARKET_ONLY_CALIBRATION_SHADOW_V1',
      'game_pk':game,'mlbam_player_id':player,
      'market_metric':'hits','market_subtype':'PLAYER_TOTAL_HITS','line':0.5,
      'canonical_model_side':'OVER',
      'raw_no_vig_market_probability_over':p,
      'calibrated_market_control_probability_over':.59,
      'baseline_model_coefficients_sha256':'b'*64,
      'source_original_lineup_sha256':'a'*64,
      'source_original_market_quote_at_utc':quote,
      'source_original_mlb_lineup_at_utc':'2026-10-08T20:49:50+00:00',
      'frozen_shadow_at_utc':'2026-10-08T21:59:44Z',
      'actual_game_event_start_utc':START.isoformat(),
      'proprietary_speed_walks_model_evaluated':False,
      'betting_play_authorized':False,'wager_submitted':False,
      'sportsbook_selected':'draftkings','source_provider':'sportwizzard',
    }

def restricted_frozen():
    return {
      'model_version':'MLB_RESTRICTED_PREQUOTE_SPEED_WALKS_HITS_SHADOW_20261008_V1',
      'coefficients':[.2,.88,.02,.01,.07,-.04,.03,.01],
      'base_market_beta':[.2,.88],
      'training_independent_games':90,
      'training_end_exclusive_utc':'2026-07-01T00:00:00+00:00',
      'training_last_start':'2026-06-18T18:00:00+00:00',
      'training_official_game_pks':list(range(100000,100090)),
      'features':list(RESTRICTED_NAMES),
      'live_betting_approved':False,
      'July_results_used_in_fit':False,
      'is_full_advanced_16_feature_model':False,
    }

class LimitedForwardModelTests(unittest.TestCase):
    def test_exact_live_feature_vector_and_missingness_masks(self):
        v=restricted_live_vector(market_control(),current_v2())
        self.assertEqual(len(v),8)
        self.assertEqual(v[0],1)
        self.assertEqual(v[3],1)
        self.assertEqual(v[5],1)
        self.assertEqual(v[7],1)
        self.assertAlmostEqual(v[2],(29-27)/3)
        self.assertAlmostEqual(v[4],(75.5-72)/7)
        self.assertAlmostEqual(v[6],(.8-.5)/1.5)

    def test_prior_season_is_strictly_previous_and_completed_before_game(self):
        source=current_v2()
        source['completed_season_biomechanics_year']=2026
        with self.assertRaisesRegex(ValueError,'prior'):
            restricted_live_vector(market_control(),source)
        source=current_v2()
        source['last_prior_date']='2026-10-08'
        vec=restricted_live_vector(market_control(),source)
        self.assertEqual(vec[6:], [0,0])

    def test_verified_source_precedes_quote_and_quote_precedes_game(self):
        late=market_control(quote='2026-10-08T20:45:00Z')
        with self.assertRaisesRegex(ValueError,'before.*feature|precedes'):
            restricted_live_vector(late,current_v2())
        after=market_control(quote='2026-10-09T00:00:00Z')
        with self.assertRaisesRegex(ValueError,'first.pitch'):
            restricted_live_vector(after,current_v2())

    def test_never_score_current_game_result_or_missing_value_as_zero_measurement(self):
        original=current_v2()
        original['prior_speed_observed']=False
        original['prior_sprint_speed_ft_per_sec']=None
        original['prior_bat_observed']=False
        original['prior_bat_speed_mph']=None
        original['prior_history_at_least_5_completed_games']=False
        original['prior_last5_walks_avg']=None
        vec=restricted_live_vector(market_control(),original)
        self.assertEqual(vec[2:],[0,0,0,0,0,0])
        original['current_game_hits']=500
        self.assertEqual(restricted_live_vector(market_control(),original),vec)

    def test_research_shadow_has_same_exact_player_game_and_one_original_book(self):
        control=market_control()
        source=current_v2()
        result=pair_forward_with_live_asof([control],[source],restricted_frozen(),
                                          frozen_model_sha256='e'*64,now=NOW)
        self.assertEqual(len(result),1)
        r=result[0]
        self.assertEqual(r['game_pk'],849832)
        self.assertEqual(r['mlbam_player_id'],123)
        self.assertEqual(r['sportsbook_selected'],'draftkings')
        self.assertEqual(r['market_fair_over_at_original_quote'],.58)
        self.assertFalse(r['full_advanced_pitchem_park_features_used'])
        self.assertFalse(r['live_play_approved'])
        self.assertFalse(r['wager_executed'])
        self.assertFalse(r['advanced_edge_proven'])

    def test_mismatched_original_lineup_sha_and_player_game_rejected(self):
        source=current_v2()
        source['original_append_only_line_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'source.*hash|original'):
            pair_forward_with_live_asof([market_control()],[source],restricted_frozen(),
                                        frozen_model_sha256='e'*64,now=NOW)
        source=current_v2(player=999)
        with self.assertRaisesRegex(ValueError,'game.player'):
            pair_forward_with_live_asof([market_control()],[source],restricted_frozen(),
                                        frozen_model_sha256='e'*64,now=NOW)

    def test_not_after_game_and_not_coefficient_changed_between_source_runs(self):
        result=pair_forward_with_live_asof([market_control()],[current_v2()],restricted_frozen(),
                                           frozen_model_sha256='e'*64,
                                           now=START+timedelta(minutes=1))
        self.assertEqual(result,[])
        bad=restricted_frozen();bad['live_betting_approved']=True
        with self.assertRaisesRegex(ValueError,'approved|research'):
            pair_forward_with_live_asof([market_control()],[current_v2()],bad,
                                        frozen_model_sha256='e'*64,now=NOW)

    def test_immutable_first_forecast_survives_changed_source_odds_and_rejects_changed_model(self):
        first=pair_forward_with_live_asof([market_control()],[current_v2()],restricted_frozen(),
                                          frozen_model_sha256='e'*64,now=NOW)
        with tempfile.TemporaryDirectory() as folder:
            ledger=Path(folder)/'FROZEN.jsonl'
            self.assertEqual(append_first_restricted_shadow(ledger,first),1)
            before=ledger.read_bytes()
            self.assertEqual(append_first_restricted_shadow(ledger,first),0)
            self.assertEqual(ledger.read_bytes(),before)
            changed=copy.deepcopy(first)
            changed[0]['calibrated_restricted_speed_walk_probability_over']=.11
            with self.assertRaisesRegex(ValueError,'conflict'):
                append_first_restricted_shadow(ledger,changed)
            self.assertEqual(ledger.read_bytes(),before)

    def test_pre_registered_training_reproduces_two_column_market_calibrator(self):
        from intelligence_warehouse.historical_recovery.mlb_speed_walks_research import (
            enrich_provenance_sample,
        )
        import json
        from intelligence_warehouse.historical_recovery.mlb_asof_feature_store import ROOT
        data=[r for r in json.loads((ROOT/'reports/hf_mlb_expanded_20261008/context_train_research_only.json').read_text())
              if r.get('context_status')=='PREGAME_CONTEXT_VERIFIED']
        store=pd.read_parquet(ROOT/'reports/mlb_feature_integration_20261008/MLB_2026_ASOF_HITTER_RESEARCH_FEATURES.parquet')
        enriched=enrich_provenance_sample(data,store)
        frozen=json.loads((ROOT/'reports/mlb_feature_integration_20261008/MLB_SPEED_WALKS_FROZEN_RESEARCH_MODEL.json').read_text())
        result=fit_restricted_training(enriched,frozen)
        self.assertEqual(result['training_independent_games'],90)
        self.assertEqual(len(result['coefficients']),8)
        self.assertFalse(result['July_results_used_in_fit'])
        self.assertLess(max(abs(a-b) for a,b in zip(result['base_market_beta'],frozen['market_calibration_beta'])),1e-10)
        self.assertEqual(set(result['training_official_game_pks']),set(frozen['training_official_game_pks']))

if __name__=='__main__':unittest.main()
