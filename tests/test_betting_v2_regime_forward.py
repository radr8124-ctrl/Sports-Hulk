import csv
import json
import tempfile
import unittest
from pathlib import Path

from intelligence_warehouse.betting_v2 import build_betting_v2_all_markets_forward as forward
from intelligence_warehouse.betting_v2.competition_regime import proof_version


class BettingV2RegimeForwardTests(unittest.TestCase):
    def setUp(self):
        self.original_paths = {
            "CURRENT": forward.CURRENT,
            "LEDGER": forward.LEDGER,
            "PRICE_LEDGER": forward.PRICE_LEDGER,
            "SUMMARY": forward.SUMMARY,
            "PUBLIC": forward.PUBLIC,
            "DIST": forward.DIST,
        }
        self.original_history_files = dict(forward.HISTORY_FILES)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        forward.CURRENT = self.root / "current.json"
        forward.LEDGER = self.root / "forward.jsonl"
        forward.PRICE_LEDGER = self.root / "prices.jsonl"
        forward.SUMMARY = self.root / "summary.json"
        forward.PUBLIC = self.root / "public.json"
        forward.DIST = self.root / "dist-does-not-exist"

    def tearDown(self):
        for name, value in self.original_paths.items():
            setattr(forward, name, value)
        forward.HISTORY_FILES.clear()
        forward.HISTORY_FILES.update(self.original_history_files)

    def _row(self, sport, regime, *, game_key="GAME", market="TOTAL"):
        lane_key = f"{sport}_{market}"
        return {
            "model_version": "BETTING_V2_ALL_MARKETS_2026_10_05",
            "sport": sport,
            "market": market,
            "lane_key": lane_key,
            "game_key": game_key,
            "selection": "OVER" if market == "TOTAL" else "HME",
            "selection_key": "OVER" if market == "TOTAL" else "HOME",
            "line": 220.5 if market == "TOTAL" else None,
            "event_start": "2099-10-20T20:00:00Z",
            "american_odds": -110,
            "market_reference_probability_pct": 52.4,
            "calibrated_win_probability_pct": 52.4,
            "edge_pct_points": 0.0,
            "expected_value_pct": 0.0,
            "conservative_expected_value_pct": -5.0,
            "historical_edge_confidence": "INSUFFICIENT_HISTORY",
            "selection_rule_status": "INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY",
            "data_quality_grade": "B",
            "shadow_decision": "PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE",
            "competition_regime": regime,
            "proof_lane_key": (
                f"{lane_key}|{regime}" if sport == "NBA" else lane_key
            ),
            "proof_version": proof_version(
                "BETTING_V2_ALL_MARKETS_2026_10_05",
                sport,
                regime,
            ),
            "book_count": 5,
        }

    def _read_jsonl(self, path):
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text().splitlines()
            if line.strip()
        ]

    def test_nba_forward_and_price_identities_are_regime_specific(self):
        preseason = self._row("NBA", "PRESEASON")
        regular = self._row("NBA", "REGULAR")

        self.assertNotEqual(
            forward.forward_identity(
                preseason,
                preseason["model_version"],
            ),
            forward.forward_identity(
                regular,
                regular["model_version"],
            ),
        )
        self.assertNotEqual(
            forward.price_identity(preseason),
            forward.price_identity(regular),
        )

    def test_cfb_identities_remain_legacy_compatible(self):
        row = self._row("CFB", "REGULAR")
        legacy_identity = forward.identity(row)

        self.assertEqual(
            forward.forward_identity(row, row["model_version"]),
            f'{row["model_version"]}|{legacy_identity}',
        )
        self.assertEqual(forward.price_identity(row), legacy_identity)

    def test_canonical_still_reads_legacy_entry_without_regime(self):
        legacy = {
            "event_type": "ENTRY",
            "forward_key": "legacy-version|CFB|GAME|TOTAL|OVER|220.5000",
            "model_version": "legacy-version",
            "sport": "CFB",
            "game_key": "GAME",
            "market": "TOTAL",
            "selection": "OVER",
            "selection_key": "OVER",
            "line": 220.5,
            "status": "PENDING",
            "grade": "PENDING",
        }
        forward.LEDGER.write_text(json.dumps(legacy) + "\n")

        canonical = forward.canonical()

        self.assertIn(legacy["forward_key"], canonical)
        self.assertNotIn("competition_regime", canonical[legacy["forward_key"]])
        self.assertNotIn("proof_version", canonical[legacy["forward_key"]])

    def test_capture_freezes_regime_metadata_into_entry_and_price(self):
        row = self._row("NBA", "PRESEASON")
        forward.CURRENT.write_text(json.dumps({
            "status": "READY",
            "model_version": row["model_version"],
            "picks": [row],
        }))

        result = forward.capture()

        self.assertEqual(result["entries_added"], 1)
        entry = self._read_jsonl(forward.LEDGER)[0]
        price = self._read_jsonl(forward.PRICE_LEDGER)[0]

        for event in (entry, price):
            self.assertEqual(event["competition_regime"], "PRESEASON")
            self.assertEqual(
                event["proof_lane_key"],
                "NBA_TOTAL|PRESEASON",
            )
            self.assertEqual(event["proof_version"], row["proof_version"])

    def test_regime_aware_nba_entry_settles_only_from_matching_regime(self):
        row = self._row("NBA", "PRESEASON")
        entry = {
            "event_type": "ENTRY",
            "forward_key": forward.forward_identity(row, row["model_version"]),
            "model_version": row["model_version"],
            "proof_version": row["proof_version"],
            "competition_regime": "PRESEASON",
            "proof_lane_key": "NBA_TOTAL|PRESEASON",
            "sport": "NBA",
            "game_key": row["game_key"],
            "market": "TOTAL",
            "selection": "OVER",
            "selection_key": "OVER",
            "line": 220.5,
            "status": "PENDING",
            "grade": "PENDING",
        }
        forward.LEDGER.write_text(json.dumps(entry) + "\n")

        history_path = self.root / "nba_history.csv"
        with history_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "lane",
                    "grade",
                    "market",
                    "snapshot_at",
                    "game_key",
                    "selection",
                    "line",
                    "season_type",
                    "away_score",
                    "home_score",
                ],
            )
            writer.writeheader()
            writer.writerow({
                "lane": "GAME",
                "grade": "WIN",
                "market": "TOTAL",
                "snapshot_at": "2026-10-01T12:00:00Z",
                "game_key": row["game_key"],
                "selection": "OVER",
                "line": 220.5,
                "season_type": 1,
                "away_score": 110,
                "home_score": 120,
            })
            writer.writerow({
                "lane": "GAME",
                "grade": "LOSS",
                "market": "TOTAL",
                "snapshot_at": "2026-10-01T13:00:00Z",
                "game_key": row["game_key"],
                "selection": "OVER",
                "line": 220.5,
                "season_type": 2,
                "away_score": 100,
                "home_score": 101,
            })
        forward.HISTORY_FILES["NBA"] = history_path

        settled = forward.settle()
        events = self._read_jsonl(forward.LEDGER)

        self.assertEqual(settled, 1)
        self.assertEqual(events[-1]["grade"], "WIN")
        self.assertEqual(events[-1]["competition_regime"], "PRESEASON")

    def test_unknown_regime_nba_entry_settles_only_from_unknown_history(self):
        row = self._row("NBA", "UNKNOWN")
        entry = {
            "event_type": "ENTRY",
            "forward_key": forward.forward_identity(row, row["model_version"]),
            "model_version": row["model_version"],
            "proof_version": row["proof_version"],
            "competition_regime": "UNKNOWN",
            "proof_lane_key": "NBA_TOTAL|UNKNOWN",
            "sport": "NBA",
            "game_key": row["game_key"],
            "market": "TOTAL",
            "selection": "OVER",
            "selection_key": "OVER",
            "line": 220.5,
            "status": "PENDING",
            "grade": "PENDING",
        }
        forward.LEDGER.write_text(json.dumps(entry) + "\n")

        history_path = self.root / "nba_unknown_history.csv"
        with history_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "lane",
                    "grade",
                    "market",
                    "snapshot_at",
                    "game_key",
                    "selection",
                    "line",
                    "season_type",
                    "away_score",
                    "home_score",
                ],
            )
            writer.writeheader()
            writer.writerow({
                "lane": "GAME",
                "grade": "WIN",
                "market": "TOTAL",
                "snapshot_at": "2026-10-01T12:00:00Z",
                "game_key": row["game_key"],
                "selection": "OVER",
                "line": 220.5,
                "season_type": "",
                "away_score": 110,
                "home_score": 120,
            })
            writer.writerow({
                "lane": "GAME",
                "grade": "LOSS",
                "market": "TOTAL",
                "snapshot_at": "2026-10-01T13:00:00Z",
                "game_key": row["game_key"],
                "selection": "OVER",
                "line": 220.5,
                "season_type": 1,
                "away_score": 100,
                "home_score": 101,
            })
        forward.HISTORY_FILES["NBA"] = history_path

        settled = forward.settle()
        events = self._read_jsonl(forward.LEDGER)

        self.assertEqual(settled, 1)
        self.assertEqual(events[-1]["grade"], "WIN")
        self.assertEqual(events[-1]["competition_regime"], "UNKNOWN")

    def test_legacy_entry_without_regime_keeps_legacy_settlement_behavior(self):
        row = self._row("NBA", "PRESEASON")
        entry = {
            "event_type": "ENTRY",
            "forward_key": "legacy|NBA|GAME|TOTAL|OVER|220.5000",
            "model_version": "legacy",
            "sport": "NBA",
            "game_key": row["game_key"],
            "market": "TOTAL",
            "selection": "OVER",
            "selection_key": "OVER",
            "line": 220.5,
            "status": "PENDING",
            "grade": "PENDING",
        }
        forward.LEDGER.write_text(json.dumps(entry) + "\n")

        history_path = self.root / "nba_legacy_history.csv"
        with history_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "lane",
                    "grade",
                    "market",
                    "snapshot_at",
                    "game_key",
                    "selection",
                    "line",
                    "season_type",
                ],
            )
            writer.writeheader()
            writer.writerow({
                "lane": "GAME",
                "grade": "WIN",
                "market": "TOTAL",
                "snapshot_at": "2026-10-01T12:00:00Z",
                "game_key": row["game_key"],
                "selection": "OVER",
                "line": 220.5,
                "season_type": 1,
            })
        forward.HISTORY_FILES["NBA"] = history_path

        settled = forward.settle()
        events = self._read_jsonl(forward.LEDGER)

        self.assertEqual(settled, 1)
        self.assertEqual(events[-1]["grade"], "WIN")

    def test_closing_reference_uses_regime_aware_nba_price_identity(self):
        row = self._row("NBA", "PRESEASON")
        row["captured_at"] = "2099-10-08T10:00:00+00:00"
        row["event_start"] = "2099-10-08T20:00:00+00:00"
        prices = {
            forward.price_identity(row): [
                {
                    "captured_at": "2099-10-08T19:00:00+00:00",
                    "market_reference_probability_pct": 55.0,
                }
            ]
        }

        close = forward.closing_reference(row, prices)

        self.assertIsNotNone(close)
        self.assertEqual(close["probability_pct"], 55.0)

    def test_forward_summary_exposes_separate_nba_proof_lanes(self):
        model_version = "BETTING_V2_ALL_MARKETS_2026_10_05"
        forward.CURRENT.write_text(json.dumps({
            "status": "READY",
            "model_version": model_version,
            "picks": [],
        }))
        entries = []
        for regime in ("PRESEASON", "REGULAR"):
            row = self._row(
                "NBA",
                regime,
                game_key=f"GAME_{regime}",
            )
            entries.append({
                "event_type": "ENTRY",
                "forward_key": forward.forward_identity(row, model_version),
                "model_version": model_version,
                "proof_version": row["proof_version"],
                "competition_regime": regime,
                "lane_key": "NBA_TOTAL",
                "proof_lane_key": f"NBA_TOTAL|{regime}",
                "sport": "NBA",
                "game_key": row["game_key"],
                "market": "TOTAL",
                "selection": "OVER",
                "selection_key": "OVER",
                "line": 220.5,
                "status": "PENDING",
                "grade": "PENDING",
                "shadow_selected": False,
            })
        forward.LEDGER.write_text(
            "".join(json.dumps(entry) + "\n" for entry in entries)
        )

        forward.main()
        payload = json.loads(forward.SUMMARY.read_text())

        self.assertEqual(payload["by_lane"]["NBA_TOTAL"]["all_predictions"]["tracked"], 2)
        self.assertEqual(
            set(payload["by_proof_lane"]),
            {"NBA_TOTAL|PRESEASON", "NBA_TOTAL|REGULAR"},
        )
        self.assertEqual(
            payload["by_proof_lane"]["NBA_TOTAL|PRESEASON"]["all_predictions"]["tracked"],
            1,
        )
        self.assertEqual(
            payload["by_proof_lane"]["NBA_TOTAL|REGULAR"]["all_predictions"]["tracked"],
            1,
        )


    def test_closing_reference_uses_regime_price_key_for_regime_aware_nba(self):
        row = self._row("NBA", "PRESEASON")
        row["captured_at"] = "2099-10-20T10:00:00Z"
        prices = {
            forward.price_identity(row): [{
                "captured_at": "2099-10-20T19:00:00Z",
                "market_reference_probability_pct": 55.0,
            }]
        }

        close = forward.closing_reference(row, prices)

        self.assertIsNotNone(close)
        self.assertEqual(close["probability_pct"], 55.0)

    def test_closing_reference_keeps_legacy_nba_price_key_for_legacy_row(self):
        row = self._row("NBA", "PRESEASON")
        row.pop("competition_regime")
        row.pop("proof_lane_key")
        row.pop("proof_version")
        row["captured_at"] = "2099-10-20T10:00:00Z"
        prices = {
            forward.identity(row): [{
                "captured_at": "2099-10-20T19:00:00Z",
                "market_reference_probability_pct": 54.0,
            }]
        }

        close = forward.closing_reference(row, prices)

        self.assertIsNotNone(close)
        self.assertEqual(close["probability_pct"], 54.0)

    def test_forward_identity_keeps_legacy_nba_key_without_regime_metadata(self):
        row = self._row("NBA", "PRESEASON")
        model_version = row["model_version"]
        row.pop("competition_regime")
        row.pop("proof_lane_key")
        row.pop("proof_version")

        self.assertEqual(
            forward.forward_identity(row, model_version),
            f"{model_version}|{forward.identity(row)}",
        )

    def test_forward_summary_separates_nba_proof_lanes_and_keeps_lane_view(self):
        preseason = self._row("NBA", "PRESEASON", game_key="GAME_PRE")
        regular = self._row("NBA", "REGULAR", game_key="GAME_REG")
        forward.CURRENT.write_text(json.dumps({
            "status": "READY",
            "model_version": preseason["model_version"],
            "picks": [preseason, regular],
        }))

        forward.main()

        summary = json.loads(forward.SUMMARY.read_text())

        self.assertIn("NBA_TOTAL", summary["by_lane"])
        self.assertEqual(
            summary["by_lane"]["NBA_TOTAL"]["all_predictions"]["tracked"],
            2,
        )
        self.assertEqual(
            set(summary["by_proof_lane"]),
            {"NBA_TOTAL|PRESEASON", "NBA_TOTAL|REGULAR"},
        )
        self.assertEqual(
            summary["by_proof_lane"]["NBA_TOTAL|PRESEASON"]["all_predictions"]["tracked"],
            1,
        )
        self.assertEqual(
            summary["by_proof_lane"]["NBA_TOTAL|REGULAR"]["all_predictions"]["tracked"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
