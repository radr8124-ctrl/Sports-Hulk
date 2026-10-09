"""MLB future-only Full16 evaluation must stay after research grading, not bet decisions."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class TestMLBFull16SeventyResearchWiring(unittest.TestCase):
    def test_automatic_mlb_refresh_runs_after_result_learning(self):
        runner=(ROOT/'mlb_live/run_mlb_refresh.sh').read_text()
        target='intelligence_warehouse.selective_forward.mlb_70_forward_evidence'
        self.assertEqual(runner.count(target),1)
        self.assertIn('--stage both',runner)
        self.assertIn('SPORTS_LABEL=mlb-full16-selective70-future-research',runner)
        self.assertIn('SPORTS_MAX_SECONDS=15',runner)
        self.assertLess(runner.index('run_mlb_learning_postrefresh.sh'),runner.index(target))
        self.assertLess(runner.index(target),runner.index('mlb-official-fixture-readiness'))
        self.assertIn('original Full16 predictions and grades preserved',runner)

    def test_all_new_research_outputs_are_outside_live_betting(self):
        from intelligence_warehouse.selective_forward import mlb_70_forward_evidence as s
        for p in (s.OUT,s.GRADES,s.SUMMARY):
            self.assertIn('intelligence_warehouse/selective_forward',str(p))
            self.assertNotIn('mlb_live/decision',str(p))
        self.assertEqual(s.SPEC.name,'ZENITH_MLB_FULL16_SELECTIVE_70_FORWARD_PREREG_2026-10-09.json')

if __name__=='__main__':unittest.main()
