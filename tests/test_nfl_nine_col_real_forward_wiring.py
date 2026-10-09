"""No NFL price/model training is retroactively attached to Week5 pregame odds."""
from pathlib import Path
import hashlib,json,unittest

ROOT=Path(__file__).resolve().parents[1]
DIR='intelligence_warehouse/nfl_advanced_pregame'
MODEL='reports/NFL_2016_2024_PRIOR_SCORE_FORM_9COL_FROZEN_MODEL_20261009.json'
DIAG='reports/NFL_2016_2024_SCORE_FORM_HOLDOUT_2025_CHECKPOINT_20261009.json'
PRE='reports/SPORTS_ZENITH_NFL_2026_SCORE_FORM_MARKET_CHALLENGER_PREREGISTRATION_2026-10-09.md'
SCORES=f'{DIR}/NFL_2026_VERIFIED_PRIOR_FINAL_SCORES.jsonl'
RAW=f'{DIR}/NFL_2026_ORIGINAL_ESPN_FINAL_WEEKLY_SCOREBOARDS.jsonl'
CONTEXT=f'{DIR}/NFL_2026_FIRST_PREGAME_TEAM_FORM_CONTEXT.jsonl'
FORECAST=f'{DIR}/NFL_FIRST_PREKICKOFF_NINE_FEATURE_SCORE_FORM_SHADOW.jsonl'
RECEIPT=f'{DIR}/NFL_NINE_FEATURE_PROSPECTIVE_SHADOW_SOURCE_SUMMARY.json'
SOURCE_REPORT=f'{DIR}/NFL_2026_FINAL_GAME_AND_TEAM_FORM_SOURCE_RECEIPT.json'

class NFLForwardSourceDurability(unittest.TestCase):
    def test_model_trained_only_through_2024_and_not_approved_to_win_bets(self):
        model=json.loads((ROOT/MODEL).read_text())
        self.assertEqual(model['training_seasons'],list(range(2016,2025)))
        self.assertEqual(model['secondary_holdout_seasons'],[2025])
        self.assertEqual(model['training_independent_games'],2465)
        self.assertEqual(model['holdout_2025_independent_games'],284)
        self.assertEqual(len(model['coefficients']),9)
        self.assertFalse(model['real_bookmaker_market_edge_proven'])
        self.assertFalse(model['2026_live_betting_play_approved'])
        # The 2025 retrospective market baseline beat the new scoring form.
        metric=model['retrospective_2025_secondary_validation']
        self.assertLess(metric['raw_compiled_market_home_no_vig']['brier'],
                        metric['historical_prior_week_score_form_ridge']['brier'])
        self.assertEqual(hashlib.sha256((ROOT/MODEL).read_bytes()).hexdigest(),
                         '7871fa9047146a81a557c3ba339840eb6dc703dd1bd97410ce6d93526a3b5ffd')

    def test_real_original_espm_team_games_and_future_prequote_context_unchanged(self):
        verified=[json.loads(x) for x in (ROOT/SCORES).read_text().splitlines() if x.strip()]
        future=[json.loads(x) for x in (ROOT/CONTEXT).read_text().splitlines() if x.strip()]
        self.assertEqual(len([x for x in verified if x['week']<=4]),64)
        self.assertEqual(len({x['official_espn_game_id'] for x in verified}),len(verified))
        first=[x for x in future if x['week']==5]
        self.assertEqual(len(first),14)
        self.assertEqual(len({x['official_espn_event_id'] for x in future}),len(future))
        self.assertTrue(all(x['source_team_form_first_frozen_at_utc']<x['official_first_pitch_utc'] for x in future))
        self.assertFalse(any(x['betting_play_authorized'] for x in future))
        self.assertEqual(hashlib.sha256(''.join((ROOT/SCORES).read_text().splitlines(keepends=True)[:64]).encode()).hexdigest(),
                         '7bdf4b1f1a173968687fae4612de4ee4d9f5f4810dddc8481fbebd3d13edaa46')
        self.assertEqual(hashlib.sha256(''.join((ROOT/CONTEXT).read_text().splitlines(keepends=True)[:14]).encode()).hexdigest(),
                         'b25c73a35af43f5b11e13850d0c71c98ec917f7f85e8f072bce05b3a52cbcfcf')

    def test_nfl_hourly_order_independent_final_first_team_form_before_markets(self):
        code=(ROOT/'nfl_live/decision/run_nfl_production_refresh.sh').read_text()
        weekly='intelligence_warehouse.historical_recovery.nfl_verified_2026_score_form --stage verify_prior_finals'
        form='intelligence_warehouse.historical_recovery.nfl_verified_2026_score_form --stage freeze_future_team_form'
        market='intelligence_warehouse.historical_recovery.nfl_tenyear_forward_market_provenance --stage freeze_source_only'
        forecast='intelligence_warehouse.historical_recovery.nfl_first_nine_col_forward_shadow --stage freeze_after_new_quote'
        for item in (weekly,form,market,forecast):self.assertEqual(code.count(item),1)
        self.assertIn('SPORTS_MAX_SECONDS=25',code)
        self.assertLess(code.index(weekly),code.index(form))
        self.assertLess(code.index(form),code.index('=== GAME MARKET FUSION ==='))
        self.assertLess(code.index('=== GAME MARKET FUSION ==='),code.index(market))
        self.assertLess(code.index(market),code.index(forecast))
        self.assertLess(code.index(forecast),code.index('=== DECISION BRAIN ==='))
        self.assertNotIn('nfl_prior_score_form_model --stage train_once',code)
        self.assertIn('prior NFL shadow source preserved',code)

    def test_original_and_new_source_archive_plus_restorable_private_state(self):
        registry=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        backup=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        ignore=(ROOT/'.gitignore').read_text()
        sources=[
            (RAW,'nfl_2026_original_espn_final_weekly_full_source_payloads'),
            (SCORES,'nfl_2026_independent_final_game_scores_verified_vs_schedule'),
            (CONTEXT,'nfl_2026_future_prior_week_team_form_context_before_book'),
            (SOURCE_REPORT,'nfl_2026_independent_final_score_and_current_team_source_receipt'),
            (FORECAST,'nfl_2026_first_9_feature_same_new_book_moneyline_shadow'),
            (RECEIPT,'nfl_2026_first_9_feature_future_shadow_source_receipt'),
            (MODEL,'nfl_2016_2024_first_fixed_nine_feature_model'),
            (DIAG,'nfl_2025_inspected_secondary_holdout_market_better_diagnostic'),
            (PRE,'nfl_2016_24_score_model_original_before_training_preregistration'),
            ('nfl_live/derived/NFLVERSE_2026_SCHEDULE.csv','nfl_2026_original_schedule_current_week_source'),
        ]
        for path,lane in sources:
            with self.subTest(path=path):
                matches=[x for x in registry['files'] if x['path']==path]
                self.assertEqual(len(matches),1)
                self.assertEqual(matches[0]['sport'],'NFL')
                self.assertEqual(matches[0]['lane'],lane)
                self.assertTrue((ROOT/path).is_file())
                self.assertIn(f'copy_if_exists "{path}"',backup)
                if path.startswith(DIR):
                    self.assertIn(path,ignore)

if __name__=='__main__':unittest.main()
