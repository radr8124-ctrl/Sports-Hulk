"""Preregistered single new model cannot use July results when fitting."""
from __future__ import annotations
import copy
import unittest
from datetime import datetime,timedelta,timezone
from intelligence_warehouse.betting_v2.hf_mlb_prop_context_model import (
    build_context_vector, freeze_context_model, evaluate_secondary_july,
)


def sample(i,*,start_day=1,status='VERIFIED_HISTORICAL',with_context=True):
    when=datetime(2026,4,1,tzinfo=timezone.utc)+timedelta(days=i)
    row=dict(status=status,asof_status='PREGAME_FEATURE_VERIFIED',pair_status='VERIFIED_SAME_BOOK_TIME_PAIR',
        market='player hits',side='over',line=.5,odds=1.9,
        market_fair_probability=.42 + ((i%5)*.025),
        official_game_pk=i+1000,official_start=when.isoformat(),
        ts=(when-timedelta(hours=8)).isoformat(),verified_win=bool(i%3==0),
        official_stat=float(i%4),
        context_status='PREGAME_CONTEXT_VERIFIED' if with_context else 'NO_PRIOR_SEASON_PARK_SAMPLE',
        context_version='HF_MLB_ASOF_OPPONENT_PARK_ROLE_V1_2026_10_08',
        context_feature_provenance='PRIOR_2025_REG_SEASON_PARK_AND_PRIOR_COMPLETED_TEAM_PLAYER_GAMES_ONLY',
        park_reference_season=2025,park_run_factor=1.04,
        feature_asof_date=(when-timedelta(days=1)).date().isoformat(),
        player_prior_latest_official_date=(when-timedelta(days=2)).date().isoformat(),
        opp_prior_latest_official_date=(when-timedelta(days=3)).date().isoformat(),
        pregame_context_signal=(i%5-2)*.1,
        opp_last10_pitching_hits_allowed_per_9=7.0+i%3,
        opp_last10_runs_allowed=3.5+i%4*.25,
        player_last10_pa_avg=4.1+i%3*.2,
        player_rest_days=2+i%7,
        hitter_vs_opponent_prior_games=3,
        hitter_vs_opponent_prior_hits_per_game=1.1,
        last5_stat_avg=1.0,
        player_home_flag=int(i%2==0),
        opposing_starter_verified_asof=False,confirmed_lineup_verified_asof=False,weather_verified_asof=False)
    return row


class PreregisteredContextModelTests(unittest.TestCase):
    def test_fixed_feature_vector_does_not_use_current_results(self):
        row=sample(3)
        features=build_context_vector(row)
        self.assertEqual(len(features),10)
        bad=copy.deepcopy(row)
        bad['official_stat']=99999
        bad['outcome']='WIN'
        bad['player_started_current_game']=False
        bad['current_opponent_starter_name']='Postgame-known star'
        self.assertEqual(features,build_context_vector(bad))

    def test_prior_year_park_required_and_2026_park_cannot_be_learned(self):
        row=sample(3);row['park_reference_season']=2026
        with self.assertRaisesRegex(ValueError,'park'):
            build_context_vector(row)

    def test_source_asof_must_precede_quote_and_match_prior_latest_dates(self):
        row=sample(3)
        row['player_prior_latest_official_date']=row['official_start'][:10]
        with self.assertRaisesRegex(ValueError,'prior'):
            build_context_vector(row)

    def test_freeze_cannot_train_on_vendor_missing_reconstructed_grade_or_july(self):
        train=[sample(i) for i in range(80)]
        train_cutoff=datetime(2026,7,1,tzinfo=timezone.utc)
        # This fixture has May/June samples and a freeze cutoff set July 1.
        model=freeze_context_model(train,training_end_exclusive=train_cutoff.isoformat())
        self.assertEqual(model['training_independent_games'],80)
        self.assertEqual(len(model['context_plus_market_beta']),10)
        self.assertEqual(len(model['market_calibrated_beta']),2)
        self.assertEqual(model['lambda'],16.0)
        self.assertEqual(model['production_picks_approved'],False)
        derived=[sample(i) for i in range(80)]
        derived[10]['status']='OFFICIAL_DERIVED_HISTORICAL'
        with self.assertRaisesRegex(ValueError,'vendor'):
            freeze_context_model(derived,training_end_exclusive=train_cutoff.isoformat())
        same=[sample(i) for i in range(80)]
        same[1]['official_start']=datetime(2026,7,3,tzinfo=timezone.utc).isoformat()
        with self.assertRaisesRegex(ValueError,'cutoff'):
            freeze_context_model(same,training_end_exclusive=train_cutoff.isoformat())

    def test_evaluate_secondary_holdout_locked_without_retraining(self):
        train=[sample(i) for i in range(70)]
        frozen=freeze_context_model(train,training_end_exclusive='2026-07-01T00:00:00+00:00')
        ref=copy.deepcopy(frozen)
        later=[sample(i+200,status='OFFICIAL_DERIVED_HISTORICAL') for i in range(32)]
        result=evaluate_secondary_july(frozen,later)
        self.assertEqual(result['status'],'SECONDARY_HISTORICAL_CONTEXT_CHECK_ONLY')
        self.assertEqual(result['holdout_independent_games'],32)
        self.assertFalse(result['production_picks_approved'])
        self.assertEqual(frozen,ref)
        self.assertTrue(result['training_and_test_game_ids_disjoint'])
        self.assertIn('calendar_day_bootstrap_95pct_brier_gain_ci',result)

    def test_cannot_evaluate_contemporaneous_or_repeated_games(self):
        frozen=freeze_context_model([sample(i) for i in range(70)],training_end_exclusive='2026-07-01T00:00:00+00:00')
        contemporaneous=evaluate_secondary_july(frozen,[sample(i,status='OFFICIAL_DERIVED_HISTORICAL') for i in range(10)])
        self.assertEqual(contemporaneous['status'],'NO_NEW_AFTER_TRAINING_GAMES')
        overlapping=[sample(i+200,status='OFFICIAL_DERIVED_HISTORICAL') for i in range(31)]
        overlapping[5]['official_game_pk']=frozen['training_official_game_pks'][0]
        result=evaluate_secondary_july(frozen,overlapping)
        self.assertEqual(result['holdout_independent_games'],30)

if __name__=='__main__':unittest.main()
