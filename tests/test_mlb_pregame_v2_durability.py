"""Migration to V2 keeps original pregame V1 immutable and archived."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
DIR='intelligence_warehouse/mlb_pregame_capture'
V1=f'{DIR}/MLB_RESEARCH_ASOF_FEATURE_FREEZE.jsonl'
V2=f'{DIR}/MLB_RESEARCH_ASOF_FEATURE_FREEZE_V2.jsonl'
V2_RECEIPT=f'{DIR}/MLB_RESEARCH_FEATURE_FREEZE_V2_SUMMARY.json'
RECONCILIATION='reports/mlb_feature_integration_20261008/MLB_INCREMENTAL_POSTSEASON_HISTORY_RECONCILIATION.json'

class V2PersistenceAndLiveTimerChecks(unittest.TestCase):
    def test_only_verified_v2_runs_between_official_pregame_source_and_market(self):
        script=(ROOT/'mlb_live/run_mlb_refresh.sh').read_text()
        source='intelligence_warehouse.mlb_pregame_capture.capture_evidence'
        v2='intelligence_warehouse.historical_recovery.mlb_live_research_feature_freeze_v2'
        legacy='intelligence_warehouse.historical_recovery.mlb_live_research_feature_freeze'
        self.assertEqual(script.count(v2),1)
        self.assertNotIn(legacy+' \\\n',script)
        self.assertIn('SPORTS_LABEL=mlb-asof-research-v2',script)
        self.assertIn('SPORTS_MAX_SECONDS=35',script)
        self.assertLess(script.index(source),script.index(v2))
        self.assertLess(script.index(v2),script.index('=== MLB MARKETS ==='))
        self.assertIn('previous V1 frozen history preserved',script)

    def test_new_v2_ledger_and_original_v1_both_archived_and_recoverable(self):
        c=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        for path,lane in [
            (V1,'mlb_true_pregame_research_feature_ledger'),
            (V2,'mlb_reconciled_postseason_pregame_v2_forward_feature_ledger'),
            (V2_RECEIPT,'mlb_reconciled_postseason_pregame_v2_receipt'),
            (RECONCILIATION,'asof_speed_walks_research_postseason_history_crosscheck_receipt')
        ]:
            with self.subTest(path=path):
                candidates=[v for v in c['files'] if v['path']==path]
                self.assertEqual(len(candidates),1)
                self.assertEqual(candidates[0]['sport'],'MLB')
                self.assertEqual(candidates[0]['lane'],lane)
                self.assertTrue((ROOT/path).is_file())

    def test_protected_state_backup_includes_both_original_frozen_versions(self):
        s=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        ignore=(ROOT/'.gitignore').read_text()
        for p in (V1,V2,V2_RECEIPT):
            self.assertIn(f'copy_if_exists "{p}"',s)
            self.assertIn(p,ignore)
        self.assertIn('copy_if_exists "reports/mlb_feature_integration_20261008"',s)

    def test_existing_true_live_pregame_18_player_source_remains_distinct(self):
        snapshots=[]
        for p in (V1,V2):
            rows=[json.loads(line) for line in (ROOT/p).read_text().splitlines() if line.strip()]
            first=[r for r in rows if r['game_pk']==849832]
            self.assertEqual(len(first),18)
            self.assertEqual(len({(r['game_pk'],r['player_id']) for r in rows}),len(rows))
            self.assertTrue(all(r['source_capture_at_utc']<r['feature_frozen_at_utc']<r['scheduled_first_pitch_utc'] for r in rows))
            self.assertFalse(any(r['betting_prediction_written'] or r['live_play_approved'] for r in rows))
            initial_lines=(ROOT/p).read_text().splitlines(keepends=True)[:18]
            snapshots.append(hashlib.sha256(''.join(initial_lines).encode()).hexdigest())
        self.assertEqual(snapshots[0],'896d34cd06592a6c0b0ee73272a76129fffe58ef7eb3f0ce4063a4b55119aee4')
        self.assertEqual(snapshots[1],'fbd5950597434da107538085213fa2f6d1fc2ca430e440d604ed981aebeb3f1d')

if __name__=='__main__':
    unittest.main()
