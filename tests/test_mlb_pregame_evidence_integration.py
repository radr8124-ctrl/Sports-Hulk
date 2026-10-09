"""The append-only pregame source must be scheduled and archived."""
from __future__ import annotations
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
SOURCE='intelligence_warehouse/mlb_pregame_capture'
LEDGER=f'{SOURCE}/MLB_PREGAME_SOURCE_EVIDENCE.jsonl'
SUMMARY=f'{SOURCE}/MLB_PREGAME_CAPTURE_SUMMARY.json'


class CaptureWiringTests(unittest.TestCase):
    def test_existing_timed_mlb_refresh_runs_capped_source_capture_before_betting_brain(self):
        script=(ROOT/'mlb_live/run_mlb_refresh.sh').read_text()
        expected='intelligence_warehouse.mlb_pregame_capture.capture_evidence'
        self.assertEqual(script.count(expected),1)
        self.assertIn('SPORTS_LABEL=mlb-pregame-evidence',script)
        self.assertIn('SPORTS_MAX_SECONDS=35',script)
        self.assertLess(script.index(expected),script.index('=== MLB MARKETS ==='))
        self.assertIn('prior data preserved',script)

    def test_intelligence_archive_includes_both_evidence_ledger_and_summary(self):
        cfg=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        for lane,path in [('pregame_evidence',LEDGER),('pregame_evidence_receipt',SUMMARY)]:
            matches=[e for e in cfg['files'] if e['path']==path]
            self.assertEqual(len(matches),1)
            self.assertEqual(matches[0]['sport'],'MLB')
            self.assertEqual(matches[0]['lane'],lane)

    def test_private_backups_preserve_pregame_evidence_as_first_class_asset(self):
        content=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        self.assertIn(f'copy_if_exists "{LEDGER}"',content)
        self.assertIn(f'copy_if_exists "{SUMMARY}"',content)

    def test_generated_proof_never_tracked_in_source_control(self):
        content=(ROOT/'.gitignore').read_text()
        self.assertIn(LEDGER,content)
        self.assertIn(SUMMARY,content)

if __name__=='__main__':unittest.main()
