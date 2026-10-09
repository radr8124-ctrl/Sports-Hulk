"""Automatic evidence->feature bridge must run without changing wagering engines."""
from pathlib import Path
import json,unittest

ROOT=Path(__file__).resolve().parents[1]
PREFIX='intelligence_warehouse/mlb_pregame_capture'
TARGETS={
    'mlb_true_pregame_research_feature_ledger':f'{PREFIX}/MLB_RESEARCH_ASOF_FEATURE_FREEZE.jsonl',
    'mlb_true_pregame_research_feature_receipt':f'{PREFIX}/MLB_RESEARCH_FEATURE_FREEZE_SUMMARY.json',
}

class MLBTruePregameSourceWiringTests(unittest.TestCase):
    def test_research_freeze_after_immutable_source_and_before_market_production(self):
        script=(ROOT/'mlb_live/run_mlb_refresh.sh').read_text()
        # Original V1 research continues to exist as an immutable audit file;
        # only the verified postseason-aware V2 capture runs each timer cycle.
        text='intelligence_warehouse.historical_recovery.mlb_live_research_feature_freeze_v2'
        self.assertEqual(script.count(text),1)
        self.assertIn('SPORTS_LABEL=mlb-asof-research-v2',script)
        self.assertIn('SPORTS_MAX_SECONDS=35',script)
        self.assertLess(script.index('intelligence_warehouse.mlb_pregame_capture.capture_evidence'),
                        script.index(text))
        self.assertLess(script.index(text),script.index('=== MLB MARKETS ==='))
        self.assertIn('source research prior records preserved',script)

    def test_hourly_archive_has_immutable_ledger_and_mutable_operational_receipt(self):
        catalog=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        for lane,rel in TARGETS.items():
            with self.subTest(rel=rel):
                matches=[r for r in catalog['files'] if r['path']==rel]
                self.assertEqual(len(matches),1)
                self.assertEqual(matches[0]['sport'],'MLB')
                self.assertEqual(matches[0]['lane'],lane)
                self.assertTrue((ROOT/rel).exists())

    def test_private_backup_and_gitignore_protect_real_snapshot_content(self):
        script=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        ignore=(ROOT/'.gitignore').read_text()
        for path in TARGETS.values():
            self.assertIn(f'copy_if_exists "{path}"',script)
            self.assertIn(path,ignore)
        self.assertIn(f'{PREFIX}/*.lock',ignore)

    def test_current_existing_true_pregame_freeze_not_a_paid_bet(self):
        log=ROOT/TARGETS['mlb_true_pregame_research_feature_ledger']
        data=[json.loads(x) for x in log.read_text().splitlines() if x.strip()]
        self.assertGreaterEqual(len(data),9)
        self.assertTrue(all(r['source_capture_at_utc']<=r['feature_frozen_at_utc']<r['scheduled_first_pitch_utc'] for r in data))
        self.assertTrue(all(not r['live_play_approved'] and not r['betting_prediction_written'] for r in data))
        self.assertEqual(len({(r['game_pk'],r['player_id']) for r in data}),len(data))

if __name__=='__main__':unittest.main()
