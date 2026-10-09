"""Historical biomechanics speed sources must not contain silently misdated bat data."""
from __future__ import annotations
import hashlib,json,unittest
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/mlb_statcast_recovery_20261008/biomechanics'

class VerifiedHistoricalBiomechanicsAcceptance(unittest.TestCase):
    def test_distinct_verified_bat_years_and_ten_sprint_seasons(self):
        for year in range(2016,2026):
            source=json.loads((BASE/f'sprint_speed_{year}_receipt.json').read_text())
            self.assertEqual(source['season'],year)
            self.assertEqual(source['kind'],'sprint_speed')
        bat=[]
        for year in (2024,2025):
            record=json.loads((BASE/f'bat_speed_verified_{year}_receipt.json').read_text())
            self.assertEqual(record['season'],year)
            self.assertEqual(record['kind'],'bat_speed')
            self.assertEqual(record['transport']['query_params']['seasonStart'],year)
            self.assertEqual(record['transport']['query_params']['seasonEnd'],year)
            bat.append(record['source_csv_sha256'])
        self.assertNotEqual(bat[0],bat[1])

    def test_old_false_year_artifacts_are_quarantined_out_of_usable_data_path(self):
        prior=BASE/'rejected_year_filters'
        quarantine=json.loads((prior/'REJECTED_MISFILTERED_SOURCES.json').read_text())
        self.assertEqual(quarantine['rejection_reason'],'YEAR_QUERY_SILENTLY_IGNORED_BY_BASEBALL_SAVANT_BAT_TRACKING_CSV')
        self.assertEqual(quarantine['verified_replacement_scheme'],'bat_speed_verified_YYYY with seasonStart=seasonEnd=YYYY')
        self.assertEqual(len(quarantine['files']),8)
        for rec in quarantine['files']:
            p=prior/rec['filename']
            self.assertTrue(p.is_file())
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),rec['sha256'])
        for year in (2024,2025):
            self.assertFalse((BASE/f'bat_speed_{year}_receipt.json').exists())
        self.assertFalse((BASE/'MLB_2026_PRIOR_2025_BIOMECHANICS_RESEARCH_ONLY.parquet').exists())

    def test_every_verified_and_rejected_biomechanics_record_is_source_archived_and_private(self):
        catalog=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        source_paths={e['path'] for e in catalog['files'] if e.get('sport')=='MLB'}
        files=[p for p in BASE.rglob('*') if p.is_file()]
        self.assertGreaterEqual(len(files),40)
        for path in files:
            with self.subTest(path=path.name):
                relative=str(path.relative_to(ROOT))
                self.assertIn(relative,source_paths)
        backup=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        self.assertIn('copy_if_exists "reports/mlb_statcast_recovery_20261008"',backup)
        self.assertIn('/reports/mlb_statcast_recovery_20261008/',(ROOT/'.gitignore').read_text())

    def test_official_2026_player_id_coverage_receipt_is_archived_and_not_an_approved_prediction(self):
        path=BASE/'MLB_2026_PRIOR_2025_BIOMECHANICS_OFFICIAL_COVERAGE.json'
        receipt=json.loads(path.read_text())
        self.assertEqual(receipt['independent_2026_hitter_ids_in_official_game_history'],751)
        self.assertEqual(receipt['qualified_both_measurement_player_ids'],222)
        self.assertTrue(receipt['not_live_model_approved'])
        catalog=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        self.assertEqual(len([entry for entry in catalog['files'] if entry['path']==str(path.relative_to(ROOT))]),1)

    def test_prior_year_join_is_research_only_and_no_sprint_vs_exit_velocity_mixup(self):
        prior=pd.read_parquet(BASE/'MLB_2026_PRIOR_2025_BIOMECHANICS_VERIFIED_RESEARCH_ONLY.parquet')
        self.assertEqual(len(prior),617)
        self.assertEqual(prior.prior_season_sprint_speed_ft_per_sec.notna().sum(),579)
        self.assertEqual(prior.prior_season_bat_speed_mph.notna().sum(),226)
        self.assertEqual((prior.prior_season_sprint_speed_ft_per_sec.notna()&prior.prior_season_bat_speed_mph.notna()).sum(),226)
        self.assertTrue((prior.source_completed_season==2025).all())
        self.assertTrue((prior.feature_research_season==2026).all())
        self.assertFalse(prior.approved_for_live_model.any())
        self.assertNotIn('avg_exit_velo',prior.columns)

if __name__=='__main__':unittest.main()
