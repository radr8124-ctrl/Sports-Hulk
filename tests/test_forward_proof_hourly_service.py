"""The existing hourly intelligence archive owns the forward proof scorecard."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class TestForwardProofHourlyService(unittest.TestCase):
    def test_addon_is_versioned_and_matches_installed_service(self):
        saved=ROOT/'deploy/systemd/system/sports-hulk-intelligence-archive.service.d/forward-proof-research.conf'
        self.assertTrue(saved.is_file())
        text=saved.read_text()
        self.assertEqual(text.count('ExecStartPost='),1)
        self.assertIn('ExecStartPost=-/usr/bin/env',text)
        self.assertIn('SPORTS_MAX_SECONDS=12',text)
        self.assertIn('intelligence_warehouse.brain_performance.build_forward_proof_history',text)
        self.assertNotIn('ExecStart=',text)
        deployed=Path('/etc/systemd/system/sports-hulk-intelligence-archive.service.d/forward-proof-research.conf')
        if deployed.is_file():
            self.assertEqual(deployed.read_bytes(),saved.read_bytes())

    def test_original_hourly_archive_service_remains_unchanged(self):
        existing=(ROOT/'deploy/systemd/system/sports-hulk-intelligence-archive.service').read_text()
        self.assertIn('archive_hulk_state.py',existing)
        self.assertNotIn('build_forward_proof_history',existing)
        self.assertIn('ExecStart=',existing)
        addon=(ROOT/'deploy/systemd/system/sports-hulk-intelligence-archive.service.d/forward-proof-research.conf').read_text()
        self.assertIn('ExecStartPost=',addon)

    def test_live_readback_current_matches_hash_chained_history(self):
        from intelligence_warehouse.brain_performance import build_forward_proof_history as score
        path=ROOT/score.BASE/score.HISTORY
        current=ROOT/score.BASE/score.CURRENT
        if not path.exists() or not current.exists():
            self.skipTest('Source research service not deployed in this environment')
        import json
        history=score.verify_history(path)
        self.assertGreaterEqual(len(history),1)
        self.assertEqual(json.loads(current.read_text()),history[-1])
        self.assertFalse(history[-1]['view']['experiment_result']['profitable_70_percent_betting_strategy_proven'])
        self.assertEqual(history[-1]['view']['mlb_full16']['completed_independent_original_full16_games'],1)

if __name__=='__main__':unittest.main()
