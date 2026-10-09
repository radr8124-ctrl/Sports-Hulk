"""Price-movement shadow is isolated, after official odds audit, never live picks."""
from pathlib import Path
import json
import unittest
from intelligence_warehouse.mlb_pregame_capture import freeze_source_price_movement as m

ROOT=Path(__file__).resolve().parents[1]


class TestPriceMovementFutureWiring(unittest.TestCase):
    def test_price_freeze_once_only_after_full_source_validation(self):
        shell=(ROOT/"mlb_live/run_mlb_refresh.sh").read_text()
        name="intelligence_warehouse.mlb_pregame_capture.freeze_source_price_movement"
        self.assertEqual(shell.count(name),1)
        self.assertIn("SPORTS_LABEL=mlb-frozen-source-price-movement",shell)
        self.assertIn("SPORTS_MAX_SECONDS=16",shell)
        self.assertLess(shell.index("mlb-official-fixture-readiness"),shell.index(name))
        self.assertLess(shell.index("mlb-source-book-official-alignment-audit"),shell.index(name))
        self.assertLess(shell.index("mlb-full16-selective70-future-research"),shell.index(name))
        self.assertIn("original full16 forecasts and historical book quotes preserved",shell)

    def test_model_and_original_pregame_snapshots_are_never_changed(self):
        assert m.OUT.parent==m.BASE
        self.assertIn("mlb_pregame_capture",str(m.OUT))
        self.assertNotIn("mlb_live/decision",str(m.OUT))
        s=json.loads(m.SPEC.read_text())
        self.assertEqual(s["primary_horizon_hours_before_kickoff"],4)
        self.assertEqual(s["earlier_comparison_quote_target_minutes"],120)
        self.assertFalse(s["automatic_bet_placement_or_live_decision_changes"])
        self.assertFalse(s["production_model_promotion_allowed"])
        self.assertTrue(s["original_full16_existing_18_game_forecasts_sha256"])


if __name__=="__main__":unittest.main()
