"""A historical Statcast re-download must be provenance verified and quarantined."""
from __future__ import annotations
from datetime import date
from pathlib import Path
import tempfile
import unittest

from intelligence_warehouse.historical_recovery.mlb_statcast_quarantine import (
    validate_statcast_csv,
    save_quarantined_chunk,
    assert_recovery_manifest,
)

HEADER=('pitch_type,game_date,release_speed,release_spin_rate,pfx_x,pfx_z,'
        'launch_speed,launch_angle,pitcher,batter,game_pk,at_bat_number,pitch_number,description,events\n')
ROW1='FF,2026-09-01,97.2,2431,-0.8,1.1,98.7,16,1212,4321,823002,1,1,hit_into_play,field_out\n'
ROW2='CH,2026-09-02,87.3,1550,1.2,-0.5,65.1,37,1212,4321,823003,2,4,swinging_strike,strikeout\n'

class StatcastSourceRecoveryTests(unittest.TestCase):
    def test_bom_quoted_columns_and_bounded_date_are_accepted(self):
        raw=b'\xef\xbb\xbf'+(HEADER+ROW1+ROW2).encode()
        df,proof=validate_statcast_csv(raw,'2026-09-01','2026-09-03')
        self.assertEqual(len(df),2)
        self.assertEqual(proof['start_date'],'2026-09-01')
        self.assertEqual(proof['end_date'],'2026-09-03')
        self.assertEqual(proof['verified_pitch_rows'],2)
        self.assertEqual(proof['games'],2)
        self.assertTrue(proof['required_source_columns_present'])
        self.assertEqual(proof['source_csv_sha256'].__len__(),64)

    def test_html_invalid_game_date_or_wrong_time_span_rejected(self):
        with self.assertRaisesRegex(ValueError,'not valid Statcast CSV'):
            validate_statcast_csv(b'<!DOCTYPE html><html></html>', '2026-09-01','2026-09-03')
        with self.assertRaisesRegex(ValueError,'outside requested date range'):
            validate_statcast_csv((HEADER+ROW1+ROW2.replace('2026-09-02','2026-09-09')).encode(),'2026-09-01','2026-09-03')
        with self.assertRaisesRegex(ValueError,'invalid source fixture'):
            validate_statcast_csv((HEADER+ROW1.replace('823002','')).encode(),'2026-09-01','2026-09-03')

    def test_existing_quarantined_chunk_is_immutable_and_sha_checked(self):
        raw=(HEADER+ROW1+ROW2).encode()
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            df,proof=validate_statcast_csv(raw,'2026-09-01','2026-09-03')
            first=save_quarantined_chunk(folder,df,raw,proof)
            self.assertTrue((folder/'raw_statcast_2026-09-01_2026-09-03.csv.gz').exists())
            self.assertTrue((folder/'statcast_2026-09-01_2026-09-03.parquet').exists())
            assert_recovery_manifest(folder,first)
            second=save_quarantined_chunk(folder,df,raw,proof)
            self.assertEqual(first,second)
            with self.assertRaisesRegex(ValueError,'immutable'):
                save_quarantined_chunk(folder,df,raw+b'\n',proof)

    def test_manifest_detects_tampered_source_payload(self):
        raw=(HEADER+ROW1+ROW2).encode()
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            df,proof=validate_statcast_csv(raw,'2026-09-01','2026-09-03')
            entry=save_quarantined_chunk(folder,df,raw,proof)
            path=folder/'raw_statcast_2026-09-01_2026-09-03.csv.gz'
            path.write_bytes(b'INVALID_DATA')
            with self.assertRaisesRegex(ValueError,'SHA256'):
                assert_recovery_manifest(folder,entry)

if __name__=='__main__':
    unittest.main()
