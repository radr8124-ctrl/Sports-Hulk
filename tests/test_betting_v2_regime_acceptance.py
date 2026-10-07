import json
import sys
import tempfile
import unittest
from pathlib import Path

BRAIN_DIR = (
    Path(__file__).resolve().parents[1]
    / "intelligence_warehouse"
    / "brain_performance"
)
if str(BRAIN_DIR) not in sys.path:
    sys.path.insert(0, str(BRAIN_DIR))

from intelligence_warehouse.brain_performance import build_brain_performance as brain


class BettingV2RegimeAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

        names = [
            "OUT",
            "SELECTIVITY_OUT",
            "PUBLIC",
            "PUBLIC_SELECTIVITY",
            "DIST",
            "DIST_SELECTIVITY",
            "BETTING_V2_ALL_CURRENT",
            "BETTING_V2_ALL_VALIDATION",
            "BETTING_V2_ALL_MODELS",
            "BETTING_V2_ALL_FORWARD",
            "BETTING_V2_ALL_DEVIG",
            "BETTING_V2_CLV",
        ]
        self.original_paths = {
            name: getattr(brain, name)
            for name in names
        }
        self.original_sport_files = brain.SPORT_FILES

        brain.OUT = self.root / "brain.json"
        brain.SELECTIVITY_OUT = self.root / "selectivity.json"
        brain.PUBLIC = self.root / "public-brain.json"
        brain.PUBLIC_SELECTIVITY = self.root / "public-selectivity.json"
        brain.DIST = self.root / "missing-dist" / "brain.json"
        brain.DIST_SELECTIVITY = (
            self.root / "missing-dist" / "selectivity.json"
        )
        brain.BETTING_V2_ALL_CURRENT = self.root / "all-current.json"
        brain.BETTING_V2_ALL_VALIDATION = self.root / "all-validation.json"
        brain.BETTING_V2_ALL_MODELS = self.root / "all-models.json"
        brain.BETTING_V2_ALL_FORWARD = self.root / "all-forward.json"
        brain.BETTING_V2_ALL_DEVIG = self.root / "all-devig.json"
        brain.BETTING_V2_CLV = self.root / "clv.json"
        brain.SPORT_FILES = {}

    def tearDown(self):
        for name, value in self.original_paths.items():
            setattr(brain, name, value)
        brain.SPORT_FILES = self.original_sport_files

    def _write(self, path, payload):
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_brain_record_preserves_regime_aware_betting_proof(self):
        preseason_current = {
            "status": "READY",
            "summary": {"candidates": 1},
            "by_lane": {
                "NBA_TOTAL": {"candidates": 1},
            },
            "by_proof_lane": {
                "NBA_TOTAL|PRESEASON": {
                    "competition_regime": "PRESEASON",
                    "candidates": 1,
                    "history_n": 20,
                },
            },
            "picks": [
                {
                    "sport": "NBA",
                    "lane_key": "NBA_TOTAL",
                    "proof_lane_key": "NBA_TOTAL|PRESEASON",
                    "competition_regime": "PRESEASON",
                }
            ],
        }
        preseason_forward = {
            "status": "READY",
            "by_lane": {
                "NBA_TOTAL": {
                    "all_predictions": {"tracked": 1},
                }
            },
            "by_proof_lane": {
                "NBA_TOTAL|PRESEASON": {
                    "all_predictions": {"tracked": 1},
                    "promotion": {
                        "recommendation": "HOLD_PROBABILITY_PROOF_REQUIRED"
                    },
                }
            },
        }
        clv_payload = {
            "status": "READY",
            "summary": {"tracked": 1},
            "by_sport": {"NBA": {"tracked": 1}},
            "by_regime": {
                "PRESEASON": {"tracked": 1},
            },
            "by_proof_lane": {
                "NBA_MONEYLINE|PRESEASON": {"tracked": 1},
            },
            "open_picks": [],
            "recent_closed": [],
        }

        self._write(brain.BETTING_V2_ALL_CURRENT, preseason_current)
        self._write(
            brain.BETTING_V2_ALL_VALIDATION,
            {
                "status": "READY",
                "by_proof_lane": {
                    "NBA_TOTAL|PRESEASON": {
                        "competition_regime": "PRESEASON"
                    }
                },
            },
        )
        self._write(
            brain.BETTING_V2_ALL_MODELS,
            {
                "status": "READY",
                "models": {
                    "NBA_TOTAL|PRESEASON": {
                        "competition_regime": "PRESEASON"
                    }
                },
            },
        )
        self._write(brain.BETTING_V2_ALL_FORWARD, preseason_forward)
        self._write(brain.BETTING_V2_ALL_DEVIG, {"status": "READY"})
        self._write(brain.BETTING_V2_CLV, clv_payload)

        brain.main()
        output = json.loads(brain.OUT.read_text())

        current = output["betting_v2_all_markets"]["current"]
        forward = output["betting_v2_all_markets"]["forward"]
        clv = output["betting_v2"]["clv"]

        self.assertEqual(
            set(current["by_proof_lane"]),
            {"NBA_TOTAL|PRESEASON"},
        )
        self.assertEqual(
            current["by_proof_lane"]["NBA_TOTAL|PRESEASON"][
                "competition_regime"
            ],
            "PRESEASON",
        )
        self.assertNotIn("NBA_TOTAL|REGULAR", current["by_proof_lane"])
        self.assertEqual(
            set(forward["by_proof_lane"]),
            {"NBA_TOTAL|PRESEASON"},
        )
        self.assertEqual(
            set(clv["by_regime"]),
            {"PRESEASON"},
        )
        self.assertEqual(
            set(clv["by_proof_lane"]),
            {"NBA_MONEYLINE|PRESEASON"},
        )


if __name__ == "__main__":
    unittest.main()
