"""The newly fetched September source must be in archive, protected backup, and private."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='reports/mlb_statcast_recovery_20261008'
SOURCE_FILES=tuple(
    f'{BASE}/quarantine/{fn}' for fn in (
        'raw_statcast_2026-09-01_2026-09-03.csv.gz',
        'raw_statcast_2026-09-04_2026-09-05.csv.gz',
        'statcast_2026-09-01_2026-09-03.parquet',
        'statcast_2026-09-04_2026-09-05.parquet',
        'proof_statcast_2026-09-01_2026-09-03.json',
        'proof_statcast_2026-09-04_2026-09-05.json',
    )
)
STAGED_FILES=tuple(f'{BASE}/staged_addendum/{fn}' for fn in (
    'MLB_PITCHER_ARSENAL.csv','MLB_BATTER_VS_PITCH_TYPE.csv',
    'MLB_PITCHER_ARSENAL.parquet','MLB_BATTER_VS_PITCH_TYPE.parquet',
    'STAGING_ADDENDUM_PROOF.json',
))
RECEIPT=f'{BASE}/STAGING_RECOVERY_SUMMARY.json'
SUPPLEMENTAL_FILES=[f'{BASE}/staged_addendum/PROFILE_COMPARISON_RESEARCH_ONLY.json',f'{BASE}/RECOVERY_ACCEPTANCE_2026-10-08.md']

class RecoveredStatcastSourceDurabilityTests(unittest.TestCase):
    def test_all_new_source_and_staged_research_is_content_archived(self):
        catalog=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        for path in [*SOURCE_FILES,*STAGED_FILES,RECEIPT,*SUPPLEMENTAL_FILES]:
            with self.subTest(path=path):
                matches=[row for row in catalog['files'] if row['path']==path]
                self.assertEqual(len(matches),1)
                self.assertEqual(matches[0]['sport'],'MLB')
                self.assertIn('statcast_recovery',matches[0]['lane'])
                self.assertTrue((ROOT/path).is_file())

    def test_protected_private_state_backup_includes_recovery_folder(self):
        script=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        self.assertIn(f'copy_if_exists "{BASE}"',script)
        self.assertIn('copy_if_exists "intelligence_warehouse/mlb_pregame_capture/MLB_PREGAME_SOURCE_EVIDENCE.jsonl"',script)

    def test_private_recovery_raw_and_proofs_are_never_git_staged(self):
        ignore=(ROOT/'.gitignore').read_text()
        self.assertIn('/reports/mlb_statcast_recovery_20261008/',ignore)

if __name__=='__main__':unittest.main()
