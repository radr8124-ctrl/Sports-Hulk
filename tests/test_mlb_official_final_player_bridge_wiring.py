"""A real Final game must produce official hitter source BEFORE research scoring."""
from pathlib import Path
import json,hashlib,unittest

ROOT=Path(__file__).resolve().parents[1]
BASE='intelligence_warehouse/mlb_pregame_capture'
RECEIPTS=f'{BASE}/MLB_FINAL_PLAYER_BOX_SOURCE_RECEIPTS.jsonl'
SUMMARY=f'{BASE}/MLB_FINAL_PLAYER_BOX_BRIDGE_SUMMARY.json'

class FinalOnlyPlayerOutcomeBridgeWiringTests(unittest.TestCase):
    def test_results_refresh_calls_bridge_before_original_official_hitter_grades(self):
        code=(ROOT/'mlb_live/decision/run_mlb_learning_postrefresh.sh').read_text()
        item='intelligence_warehouse.historical_recovery.mlb_official_final_player_bridge'
        self.assertEqual(code.count(item),1)
        self.assertIn('SPORTS_LABEL=mlb-original-final-player-bridge',code)
        self.assertIn('SPORTS_MAX_SECONDS=35',code)
        self.assertLess(code.index('SPORTS_LABEL=mlb-results'),code.index(item))
        self.assertLess(code.index(item),code.index('SPORTS_LABEL=mlb-research-forward-official-labels'))
        self.assertIn('original player results preserved',code)

    def test_research_backup_and_content_catalog_include_original_final_boxscore_receipts(self):
        catalog=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        script=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        ignore=(ROOT/'.gitignore').read_text()
        for relative,lane in [
            (RECEIPTS,'mlb_genuine_official_final_boxscore_raw_snapshot_and_identity_proof'),
            (SUMMARY,'mlb_genuine_official_final_boxscore_recovery_receipt'),
        ]:
            with self.subTest(relative=relative):
                matches=[x for x in catalog['files'] if x.get('path')==relative]
                self.assertEqual(len(matches),1)
                self.assertEqual(matches[0]['sport'],'MLB')
                self.assertEqual(matches[0]['lane'],lane)
                self.assertTrue((ROOT/relative).is_file())
                self.assertIn(f'copy_if_exists "{relative}"',script)
                self.assertIn(relative,ignore)

    def test_future_actual_final_results_can_accumulate_without_fabricated_paid_bets(self):
        raw=ROOT/RECEIPTS
        rows=[json.loads(x) for x in raw.read_text().splitlines() if x.strip()]
        self.assertEqual(len({int(r['game_pk']) for r in rows}),len(rows))
        for record in rows:
            self.assertEqual(record['official_final_status'],'Final')
            self.assertFalse(record['sportsbook_wins_or_bets_inferred'])
            source=record['source_original_final_boxscore_full_payload']
            digest=hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            self.assertEqual(digest,record['source_original_final_boxscore_sha256'])
        summary=json.loads((ROOT/SUMMARY).read_text())
        self.assertGreaterEqual(summary['new_official_final_player_rows_added'],0)
        self.assertTrue(summary['betting_play_or_original_model_predictions_unchanged'])
        self.assertTrue(summary['original_first_pregame_lineups_rewritten'] is False)

    def test_existing_official_player_history_is_separately_versioned_and_in_protected_state(self):
        rel='intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_LEDGER.csv'
        catalog=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        records=[x for x in catalog['files'] if x['path']==rel]
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]['sport'],'MLB_PLAYER_HISTORY')
        backup=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        for source in [
            rel,
            'intelligence_warehouse/mlb_player_history/LAST_BUILD.json',
            'intelligence_warehouse/mlb_player_history/raw_boxscores',
        ]:
            self.assertIn(f'copy_if_exists "{source}"',backup)

    def test_no_existing_source_ledger_bytes_rewritten_when_final_player_rows_append(self):
        before=ROOT/'.deploy_backups/mlb_independent_final_hitter_ledger_bridge_BEFORE_CHANGE_20261008T235728Z/intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_LEDGER.csv'
        current=ROOT/'intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_LEDGER.csv'
        self.assertTrue(current.read_bytes().startswith(before.read_bytes()))

if __name__=='__main__':unittest.main()
