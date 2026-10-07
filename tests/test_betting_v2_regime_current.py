import csv
import tempfile
import unittest
from pathlib import Path

from intelligence_warehouse.betting_v2 import build_betting_v2_all_markets as all_markets
from intelligence_warehouse.betting_v2.competition_regime import proof_version


class BettingV2RegimeCurrentTests(unittest.TestCase):
    def setUp(self):
        self.original_current_files = dict(all_markets.CURRENT_FILES)
        self.original_devig = all_markets._DEVIG
        all_markets._DEVIG = {
            "history": {},
            "current": {},
            "minimum_paired_books_for_model": 2,
        }
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        for sport in all_markets.SPORTS:
            all_markets.CURRENT_FILES[sport] = root / f"missing-{sport}.csv"

    def tearDown(self):
        all_markets.CURRENT_FILES.clear()
        all_markets.CURRENT_FILES.update(self.original_current_files)
        all_markets._DEVIG = self.original_devig

    def _write_current(self, sport, rows):
        path = Path(self.temp_dir.name) / f"{sport}_GAME_DECISIONS.csv"
        fieldnames = [
            "game_key",
            "market_canonical",
            "selection_canonical",
            "selection_side",
            "line_group",
            "median_price_american",
            "evidence_score",
            "decision",
            "start_dt",
            "sportsbook_count",
            "away_team",
            "home_team",
            "season_type",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        all_markets.CURRENT_FILES[sport] = path

    def _row(self, game_key, season_type, *, selection="HME"):
        return {
            "game_key": game_key,
            "market_canonical": "MONEYLINE",
            "selection_canonical": selection,
            "selection_side": "HOME",
            "line_group": "",
            "median_price_american": -110,
            "evidence_score": 90,
            "decision": "QUALIFIED_RESEARCH",
            "start_dt": "2026-10-20T20:00:00Z",
            "sportsbook_count": 5,
            "away_team": "AWY",
            "home_team": "HME",
            "season_type": season_type,
        }

    def _strong_model(self, sport, regime, lane_key):
        return {
            "sport": sport,
            "market": "MONEYLINE",
            "lane_key": lane_key,
            "proof_lane_key": (
                f"{lane_key}|{regime}" if sport == "NBA" else lane_key
            ),
            "competition_regime": regime,
            "proof_version": proof_version(
                all_markets.MODEL_VERSION,
                sport,
                regime,
            ),
            "model_version": all_markets.MODEL_VERSION,
            "history_n": 100,
            "coefficients": {
                "market_calibrated": [0.0, 1.0],
                "market_plus_hulk": [0.0, 1.0, 1.0],
            },
            "deployment_probability_source": "MARKET_PLUS_HULK",
            "historical_edge_confidence": "SUPPORTED",
            "selection_rule_status": "SUPPORTED",
            "hulk_score_confidence_supported": True,
            "old_score_status": "SUPPORTED",
            "old_score_coefficient": 0.1,
        }

    def _validation(self):
        return {
            "status": "READY",
            "metrics": {
                "market_plus_hulk": {
                    "ece": 0.01,
                }
            },
        }

    def test_nba_preseason_candidate_uses_preseason_proof(self):
        self._write_current(
            "NBA",
            [self._row("NBA_PRE_GAME", 1)],
        )
        key = "NBA_MONEYLINE|PRESEASON"
        models = {
            key: self._strong_model("NBA", "PRESEASON", "NBA_MONEYLINE"),
        }
        validations = {
            key: self._validation(),
        }

        rows = all_markets.build_current(models, validations)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["competition_regime"], "PRESEASON")
        self.assertEqual(row["proof_lane_key"], key)
        self.assertEqual(
            row["proof_version"],
            proof_version(
                all_markets.MODEL_VERSION,
                "NBA",
                "PRESEASON",
            ),
        )
        self.assertEqual(row["probability_source"], "MARKET_PLUS_HULK")
        self.assertGreater(
            row["calibrated_win_probability_pct"],
            row["market_reference_probability_pct"],
        )

    def test_nba_regular_candidate_cannot_borrow_preseason_model(self):
        self._write_current(
            "NBA",
            [self._row("NBA_REG_GAME", 2)],
        )
        preseason_key = "NBA_MONEYLINE|PRESEASON"
        models = {
            preseason_key: self._strong_model(
                "NBA",
                "PRESEASON",
                "NBA_MONEYLINE",
            ),
        }
        validations = {
            preseason_key: self._validation(),
        }

        rows = all_markets.build_current(models, validations)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["competition_regime"], "REGULAR")
        self.assertEqual(row["proof_lane_key"], "NBA_MONEYLINE|REGULAR")
        self.assertEqual(
            row["probability_source"],
            "MARKET_REFERENCE_INSUFFICIENT_HISTORY",
        )
        self.assertEqual(
            row["calibrated_win_probability_pct"],
            row["market_reference_probability_pct"],
        )

    def test_nba_unknown_candidate_cannot_borrow_known_regime_model(self):
        self._write_current(
            "NBA",
            [self._row("NBA_UNKNOWN_GAME", "")],
        )
        preseason_key = "NBA_MONEYLINE|PRESEASON"
        models = {
            preseason_key: self._strong_model(
                "NBA",
                "PRESEASON",
                "NBA_MONEYLINE",
            ),
        }
        validations = {
            preseason_key: self._validation(),
        }

        rows = all_markets.build_current(models, validations)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["competition_regime"], "UNKNOWN")
        self.assertEqual(row["proof_lane_key"], "NBA_MONEYLINE|UNKNOWN")
        self.assertEqual(
            row["probability_source"],
            "MARKET_REFERENCE_INSUFFICIENT_HISTORY",
        )

    def test_cfb_regular_candidate_keeps_legacy_proof_key(self):
        self._write_current(
            "CFB",
            [self._row("CFB_REG_GAME", 2)],
        )
        key = "CFB_MONEYLINE"
        models = {
            key: self._strong_model("CFB", "REGULAR", key),
        }
        validations = {
            key: self._validation(),
        }

        rows = all_markets.build_current(models, validations)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["competition_regime"], "REGULAR")
        self.assertEqual(row["proof_lane_key"], key)
        self.assertEqual(
            row["proof_version"],
            all_markets.MODEL_VERSION,
        )
        self.assertEqual(row["probability_source"], "MARKET_PLUS_HULK")


if __name__ == "__main__":
    unittest.main()
