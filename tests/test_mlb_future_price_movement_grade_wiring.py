"""No live MLB decisions may be affected by future movement grading."""
from pathlib import Path
import unittest
from intelligence_warehouse.mlb_pregame_capture import grade_future_price_movement as g

ROOT=Path(__file__).resolve().parents[1]

class TestMLBPriceMoveOfficialResultWiring(unittest.TestCase):
    def test_timer_runs_post_original_score_then_move_and_independent_final(self):
        driver=(ROOT/'mlb_live/run_mlb_refresh.sh').read_text()
        move='intelligence_warehouse.mlb_pregame_capture.freeze_source_price_movement'
        grade='intelligence_warehouse.mlb_pregame_capture.grade_future_price_movement'
        self.assertEqual(driver.count(move),1)
        self.assertEqual(driver.count(grade),1)
        self.assertLess(driver.index('run_mlb_learning_postrefresh.sh'),driver.index(move))
        self.assertLess(driver.index('mlb-source-book-official-alignment-audit'),driver.index(move))
        self.assertLess(driver.index(move),driver.index(grade))
        self.assertLess(driver.index(grade),driver.index('MLB REFRESH COMPLETE'))
        self.assertIn('SPORTS_MAX_SECONDS=13',driver)
        self.assertIn('all frozen history and official grades preserved',driver)

    def test_results_are_private_research_not_any_live_bet_ledger(self):
        for p in (g.OUT,g.SUMMARY,g.move.OUT,g.move.SUMMARY):
            self.assertIn('intelligence_warehouse/mlb_pregame_capture/',str(p))
            self.assertNotIn('mlb_live/decision/',str(p))
        self.assertFalse(g.SPEC.read_text().count('"automatic_bet_placement_or_live_decision_changes": true'))


if __name__=='__main__':unittest.main()
