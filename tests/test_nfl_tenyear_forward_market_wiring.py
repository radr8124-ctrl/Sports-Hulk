"""NFL future fair-market research stays separate from live money and Survivor."""
from pathlib import Path
import hashlib
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
PREFIX='intelligence_warehouse/pregame_source_evidence'
BASE=f'{PREFIX}/NFL_FIRST_TRUE_PREGAME_PAIRED_BOOK_MONEYLINE_CONTROL.jsonl'
RECEIPT=f'{PREFIX}/NFL_FIRST_TRUE_PREGAME_MARKET_HISTORY_PROVENANCE_SUMMARY.json'
REPORT='reports/SPORTS_ZENITH_NFL_TENYEAR_HISTORICAL_AND_NEXT_GAMES_FIRST_MARKET_CHECKPOINT_2026-10-09.md'

class NFLDecadeOnlySourceMoneylineSafeguards(unittest.TestCase):
    def test_only_new_source_no_model_ingest_after_provider_game_fusion(self):
        script=(ROOT/'nfl_live/decision/run_nfl_production_refresh.sh').read_text()
        name='intelligence_warehouse.historical_recovery.nfl_tenyear_forward_market_provenance'
        self.assertEqual(script.count(name),1)
        self.assertIn('SPORTS_LABEL=nfl-tenyear-source-only-paired-moneyline',script)
        self.assertIn('SPORTS_MAX_SECONDS=20',script)
        self.assertLess(script.index('=== GAME MARKET FUSION ==='),script.index(name))
        self.assertLess(script.index(name),script.index('=== DECISION BRAIN ==='))
        self.assertIn('prior genuine NFL market research preserved',script)
        self.assertNotIn('nfl_tenyear_forward_market_provenance --stage train',script)

    def test_immutable_market_odds_and_acceptance_report_are_versioned_and_private(self):
        j=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        backup=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        ignore=(ROOT/'.gitignore').read_text()
        for file,lane in [
            (BASE,'nfl_first_genuine_future_paired_moneyline_market_control'),
            (RECEIPT,'nfl_decade_historical_coverage_and_first_future_book_baseline_provenance'),
            (REPORT,'nfl_decade_original_market_provenance_first_acceptance_report'),
        ]:
            with self.subTest(file=file):
                matches=[r for r in j['files'] if r['path']==file]
                self.assertEqual(len(matches),1)
                self.assertEqual(matches[0]['sport'],'NFL')
                self.assertEqual(matches[0]['lane'],lane)
                self.assertTrue((ROOT/file).is_file())
                self.assertIn(f'copy_if_exists "{file}"',backup)
                if file!=REPORT:self.assertIn(file,ignore)

    def test_original_historical_ten_year_and_sportsbook_snapshot_are_recoverable(self):
        registry=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        backup=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        for rel,lane in [
            ('data_vault/derived/NFL_GAME_MASTER.csv',
             'nfl_source_original_2016_2025_ten_year_historical_game_master'),
            ('data_vault/derived/NFL_HISTORICAL_COMPS_BASE.csv',
             'nfl_source_original_2016_2025_historical_comparisons'),
            ('nfl_live/game_fusion/NFL_GAME_SPORTWIZZARD_RAW.csv',
             'nfl_source_original_current_multibook_unredacted_game_quotes'),
        ]:
            with self.subTest(path=rel):
                records=[x for x in registry['files'] if x.get('path')==rel]
                self.assertEqual(len(records),1)
                self.assertEqual(records[0]['sport'],'NFL')
                self.assertEqual(records[0]['lane'],lane)
                self.assertTrue((ROOT/rel).is_file())
                self.assertIn(f'copy_if_exists "{rel}"',backup)

    def test_original_12_source_future_games_are_not_twelve_paid_or_trained_predictions(self):
        source=ROOT/BASE
        raw=[json.loads(s) for s in source.read_text().splitlines() if s.strip()]
        original=[r for r in raw if r['season']==2026 and r['week']==5]
        self.assertGreaterEqual(len(original),12)
        self.assertEqual(len({r['official_espn_event_id'] for r in original}),len(original))
        # Source ledger is append-only; earlier first 12 original price
        # references cannot change just because a new NFL game is added.
        original_lines=source.read_text().splitlines(keepends=True)
        self.assertEqual(
            hashlib.sha256(''.join(original_lines[:12]).encode()).hexdigest(),
            '42da2e5b20834b2c0908be7f8d5a82aa4773eb73973183fb0be04197a47ab672',
        )
        self.assertTrue(all(r['source_original_book_quote_updated_at_utc']<r['official_espn_kickoff_utc'] for r in original))
        self.assertTrue(all(r['observed_source_only_research_frozen_at_utc']<r['official_espn_kickoff_utc'] for r in original))
        self.assertFalse(any(r['model_prediction_calculated'] or r['betting_play_approved'] for r in original))
        self.assertTrue(all(r['actual_stadium_roof_status']=='UNKNOWN_NOT_OBSERVED' for r in original))
        self.assertFalse(any(r['stale_injury_reported_as_game_clearance'] for r in original))

    def test_ten_year_historical_exact_season_coverage_not_extra_current_outcomes(self):
        j=json.loads((ROOT/RECEIPT).read_text())
        hist=j['historical_ten_year_source']
        self.assertEqual(hist['seasons'],list(range(2016,2026)))
        self.assertEqual(hist['historical_games'],2761)
        self.assertFalse(hist['historical_weather_is_original_pregame_forecast'])
        self.assertFalse(hist['stored_roof_is_verified_future_2026_open_closed_state'])
        self.assertEqual(
            j['total_immutable_game_moneyline_price_baselines'],
            len([line for line in (ROOT/BASE).read_text().splitlines() if line.strip()]),
        )
        self.assertFalse(j['real_money_bets_created'])
        self.assertFalse(j['model_with_proven_market_edge_deployed'])

if __name__=='__main__':unittest.main()
