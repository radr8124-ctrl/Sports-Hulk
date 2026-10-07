import csv
import json
import tempfile
import unittest
from pathlib import Path

from intelligence_warehouse.betting_v2 import build_betting_v2_all_markets as all_markets


class BettingV2RegimeHistoryTests(unittest.TestCase):
    def setUp(self):
        self.original_history_files = dict(all_markets.HISTORY_FILES)
        self.original_current_files = dict(all_markets.CURRENT_FILES)
        self.original_outputs = {
            "MODEL_OUT": all_markets.MODEL_OUT,
            "VALIDATION_OUT": all_markets.VALIDATION_OUT,
            "CURRENT_OUT": all_markets.CURRENT_OUT,
            "PUBLIC": all_markets.PUBLIC,
            "DIST": all_markets.DIST,
        }
        self.original_devig = all_markets._DEVIG
        all_markets._DEVIG = {
            "history": {},
            "current": {},
            "minimum_paired_books_for_model": 2,
        }

    def tearDown(self):
        all_markets.HISTORY_FILES.clear()
        all_markets.HISTORY_FILES.update(self.original_history_files)
        all_markets.CURRENT_FILES.clear()
        all_markets.CURRENT_FILES.update(self.original_current_files)
        for name, value in self.original_outputs.items():
            setattr(all_markets, name, value)
        all_markets._DEVIG = self.original_devig

    def _write_history(self, sport, rows):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / f"{sport}_GRADED_RECOMMENDATIONS.csv"
        fieldnames = [
            "snapshot_at",
            "lane",
            "grade",
            "market",
            "game_key",
            "selection",
            "line",
            "score",
            "start",
            "season_type",
            "payload_json",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        all_markets.HISTORY_FILES[sport] = path
        return path

    def _row(
        self,
        game_key,
        season_type,
        *,
        market="TOTAL",
        selection="OVER",
        line=220.5,
        score=80,
        grade="WIN",
    ):
        return {
            "snapshot_at": "2026-10-01T12:00:00Z",
            "lane": "GAME",
            "grade": grade,
            "market": market,
            "game_key": game_key,
            "selection": selection,
            "line": line,
            "score": score,
            "start": "2026-10-01T20:00:00Z",
            "season_type": season_type,
            "payload_json": json.dumps({"american_odds": -110}),
        }

    def test_nba_history_rows_preserve_preseason_regular_and_unknown_regimes(self):
        self._write_history(
            "NBA",
            [
                self._row("NBA_PRE", 1),
                self._row("NBA_REG", 2),
                self._row("NBA_UNKNOWN", ""),
            ],
        )

        frame = all_markets.build_history("NBA", "TOTAL")
        by_game = {row["game_key"]: row for _, row in frame.iterrows()}

        self.assertEqual(by_game["NBA_PRE"]["competition_regime"], "PRESEASON")
        self.assertEqual(by_game["NBA_PRE"]["lane_key"], "NBA_TOTAL")
        self.assertEqual(
            by_game["NBA_PRE"]["proof_lane_key"],
            "NBA_TOTAL|PRESEASON",
        )

        self.assertEqual(by_game["NBA_REG"]["competition_regime"], "REGULAR")
        self.assertEqual(by_game["NBA_REG"]["lane_key"], "NBA_TOTAL")
        self.assertEqual(
            by_game["NBA_REG"]["proof_lane_key"],
            "NBA_TOTAL|REGULAR",
        )

        self.assertEqual(
            by_game["NBA_UNKNOWN"]["competition_regime"],
            "UNKNOWN",
        )
        self.assertEqual(
            by_game["NBA_UNKNOWN"]["proof_lane_key"],
            "NBA_TOTAL|UNKNOWN",
        )

    def test_cfb_history_carries_regime_metadata_without_rekeying_proof(self):
        self._write_history(
            "CFB",
            [self._row("CFB_REG", 2)],
        )

        frame = all_markets.build_history("CFB", "TOTAL")
        row = frame.iloc[0]

        self.assertEqual(row["competition_regime"], "REGULAR")
        self.assertEqual(row["lane_key"], "CFB_TOTAL")
        self.assertEqual(row["proof_lane_key"], "CFB_TOTAL")

    def test_partition_proof_frames_separates_nba_regimes_but_not_cfb(self):
        self._write_history(
            "NBA",
            [
                self._row("NBA_PRE", 1),
                self._row("NBA_REG", 2),
            ],
        )
        nba_frame = all_markets.build_history("NBA", "TOTAL")
        nba_partitions = all_markets.partition_proof_frames(nba_frame)

        self.assertEqual(
            set(nba_partitions),
            {"NBA_TOTAL|PRESEASON", "NBA_TOTAL|REGULAR"},
        )
        self.assertEqual(len(nba_partitions["NBA_TOTAL|PRESEASON"]), 1)
        self.assertEqual(len(nba_partitions["NBA_TOTAL|REGULAR"]), 1)

        self._write_history(
            "CFB",
            [
                self._row("CFB_REG_A", 2),
                self._row("CFB_REG_B", 2),
            ],
        )
        cfb_frame = all_markets.build_history("CFB", "TOTAL")
        cfb_partitions = all_markets.partition_proof_frames(cfb_frame)

        self.assertEqual(set(cfb_partitions), {"CFB_TOTAL"})
        self.assertEqual(len(cfb_partitions["CFB_TOTAL"]), 2)

    def test_main_stores_models_by_proof_lane_and_keeps_lane_summary(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)

        for sport in all_markets.SPORTS:
            all_markets.HISTORY_FILES[sport] = root / f"missing-{sport}.csv"
            all_markets.CURRENT_FILES[sport] = root / f"missing-current-{sport}.csv"

        self._write_history(
            "NBA",
            [
                self._row("NBA_PRE", 1),
                self._row("NBA_REG", 2),
            ],
        )
        self._write_history(
            "CFB",
            [self._row("CFB_REG", 2)],
        )

        all_markets.MODEL_OUT = root / "models.json"
        all_markets.VALIDATION_OUT = root / "validation.json"
        all_markets.CURRENT_OUT = root / "current.json"
        all_markets.PUBLIC = root / "public"
        all_markets.DIST = root / "dist-does-not-exist"

        all_markets.main()

        validation = json.loads(all_markets.VALIDATION_OUT.read_text())
        models = json.loads(all_markets.MODEL_OUT.read_text())
        current = json.loads(all_markets.CURRENT_OUT.read_text())

        validation_keys = set(validation["lanes"])
        self.assertIn("NBA_TOTAL|PRESEASON", validation_keys)
        self.assertIn("NBA_TOTAL|REGULAR", validation_keys)
        self.assertNotIn("NBA_TOTAL", validation_keys)
        self.assertIn("CFB_TOTAL", validation_keys)
        self.assertEqual(set(models["models"]), validation_keys)
        self.assertEqual(set(current["by_proof_lane"]), validation_keys)
        self.assertIn("NBA_TOTAL", current["by_lane"])
        self.assertIn("CFB_TOTAL", current["by_lane"])
        self.assertEqual(current["by_lane"]["NBA_TOTAL"]["history_n"], 2)
        self.assertEqual(current["by_lane"]["CFB_TOTAL"]["history_n"], 1)

        nba_pre = models["models"]["NBA_TOTAL|PRESEASON"]
        nba_reg = models["models"]["NBA_TOTAL|REGULAR"]
        cfb_reg = models["models"]["CFB_TOTAL"]

        self.assertEqual(nba_pre["competition_regime"], "PRESEASON")
        self.assertEqual(nba_pre["lane_key"], "NBA_TOTAL")
        self.assertEqual(nba_pre["proof_lane_key"], "NBA_TOTAL|PRESEASON")
        self.assertEqual(nba_reg["competition_regime"], "REGULAR")
        self.assertEqual(cfb_reg["competition_regime"], "REGULAR")
        self.assertEqual(cfb_reg["proof_lane_key"], "CFB_TOTAL")


if __name__ == "__main__":
    unittest.main()
