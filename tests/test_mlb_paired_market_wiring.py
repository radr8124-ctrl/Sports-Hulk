"""Current sportsbook paired odds are retained in research after fusion only."""
from pathlib import Path
import json,unittest

ROOT=Path(__file__).resolve().parents[1]
DIR='intelligence_warehouse/mlb_pregame_capture'
RECORDS=f'{DIR}/MLB_V2_PREGAME_SAME_BOOK_FAIR_PRICE_BASELINES.jsonl'
RECEIPT=f'{DIR}/MLB_V2_PREGAME_FAIR_PRICE_BASELINE_SUMMARY.json'

class PairedMarketResearchWiringTests(unittest.TestCase):
    def test_after_market_fusion_and_before_decision_not_external_api(self):
        content=(ROOT/'mlb_live/run_mlb_refresh.sh').read_text()
        invoke='intelligence_warehouse.historical_recovery.mlb_paired_pregame_market_freeze'
        self.assertEqual(content.count(invoke),1)
        self.assertIn('SPORTS_LABEL=mlb-paired-book-source-research',content)
        self.assertIn('SPORTS_MAX_SECONDS=28',content)
        self.assertLess(content.index('=== MLB FUSION ==='),content.index(invoke))
        self.assertLess(content.index(invoke),content.index('=== MLB DECISION BRAIN ==='))
        self.assertIn('previous research book-price evidence preserved',content)

    def test_source_price_pairs_have_durable_hourly_content_archive_lanes(self):
        c=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        for rel,lane in (
            (RECORDS,'mlb_v2_true_pregame_paired_book_price_baselines'),
            (RECEIPT,'mlb_v2_true_pregame_paired_book_source_capture_receipt'),
        ):
            with self.subTest(file=rel):
                rows=[r for r in c['files'] if r.get('path')==rel]
                self.assertEqual(len(rows),1)
                self.assertEqual(rows[0]['sport'],'MLB')
                self.assertEqual(rows[0]['lane'],lane)
                self.assertTrue((ROOT/rel).is_file())

    def test_private_backup_and_gitignore_never_expose_market_source_rows(self):
        backup=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        ignore=(ROOT/'.gitignore').read_text()
        for rel in (RECORDS,RECEIPT):
            self.assertIn(f'copy_if_exists "{rel}"',backup)
            self.assertIn(rel,ignore)

    def test_genuine_current_market_source_is_from_one_game_not_fake_picks(self):
        rows=[json.loads(s) for s in (ROOT/RECORDS).read_text().splitlines() if s.strip()]
        self.assertGreaterEqual(len(rows),1)
        games={r['official_game_pk'] for r in rows}
        self.assertIn(849832,games)
        self.assertEqual(len({r['mlbam_player_id'] for r in rows if r['official_game_pk']==849832}),18)
        self.assertGreaterEqual(len(rows),107)
        self.assertTrue(all(r['quote_captured_before_first_pitch'] for r in rows))
        self.assertTrue(all(r['model_prediction_created'] is False and r['betting_selection_approved'] is False for r in rows))
        self.assertTrue(all(r['per_quote_is_independent_game_proof'] is False for r in rows))

if __name__=='__main__': unittest.main()
