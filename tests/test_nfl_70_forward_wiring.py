"""NFL 70-percent research sidecar runs after official Final without touching live decisions."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class TestNFL70ForwardWiring(unittest.TestCase):
    def test_runs_exactly_once_after_official_source_scorer(self):
        driver=(ROOT/"nfl_live/decision/run_nfl_learning_postrefresh.sh").read_text()
        name="intelligence_warehouse.selective_forward.nfl_70_forward_evidence"
        self.assertEqual(driver.count(name),1)
        self.assertIn("--stage both",driver)
        self.assertLess(driver.index("nfl_forward_individual_final_source"),driver.index(name))
        self.assertLess(driver.index("nfl_nine_col_official_scoring"),driver.index(name))
        self.assertIn("SPORTS_MAX_SECONDS=15",driver)
        self.assertIn("original frozen forecasts and results preserved",driver)
        self.assertIn("Production refresh is never blocked",driver)

    def test_active_nfl_hourly_service_owns_separate_learning_runner(self):
        path=Path("/etc/systemd/system/sports-hulk-nfl-refresh.service.d/learning-history.conf")
        text=path.read_text()
        self.assertIn("ExecStartPost=/home/ubuntu/sports-hulk/nfl_live/decision/run_nfl_learning_postrefresh.sh",text)

    def test_price_and_grades_are_stored_only_in_research_not_live_nfl(self):
        from intelligence_warehouse.selective_forward import nfl_70_forward_evidence as s
        self.assertIn("intelligence_warehouse/selective_forward",str(s.OUT))
        self.assertNotIn("nfl_live/decision",str(s.OUT))
        self.assertNotIn("nfl_live/decision",str(s.GRADES))
        self.assertEqual(s.SPEC.name,"ZENITH_NFL_70_TRUE_FORWARD_PRICE_EXPERIMENT_PREREG_2026-10-09.json")


if __name__=="__main__":unittest.main()
