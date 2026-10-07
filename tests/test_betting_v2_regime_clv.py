import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from intelligence_warehouse.betting_v2 import build_clv_tracker as clv
from intelligence_warehouse.betting_v2.competition_regime import (
    proof_lane_key,
    proof_version,
)


MODEL_VERSION = "BETTING_V2_ALL_MARKETS_2026_10_05"


class BettingV2RegimeClvTests(unittest.TestCase):
    def setUp(self):
        self.original_paths = {
            "CURRENT": clv.CURRENT,
            "PRICE_LEDGER": clv.PRICE_LEDGER,
            "PICK_LEDGER": clv.PICK_LEDGER,
            "OUT": clv.OUT,
            "PUBLIC_OUT": clv.PUBLIC_OUT,
            "DIST_OUT": clv.DIST_OUT,
        }
        self.had_regime_source = hasattr(clv, "REGIME_SOURCE")
        self.original_regime_source = getattr(
            clv,
            "REGIME_SOURCE",
            None,
        )
        self.original_now = clv.now

        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

        clv.CURRENT = self.root / "current.json"
        clv.PRICE_LEDGER = self.root / "prices.jsonl"
        clv.PICK_LEDGER = self.root / "picks.jsonl"
        clv.OUT = self.root / "clv.json"
        clv.PUBLIC_OUT = self.root / "public.json"
        clv.DIST_OUT = self.root / "dist.json"
        clv.REGIME_SOURCE = self.root / "all_markets_current.json"

        clv.now = lambda: datetime(
            2026, 10, 7, 12, 0, tzinfo=timezone.utc
        )

    def tearDown(self):
        for name, value in self.original_paths.items():
            setattr(clv, name, value)
        if self.had_regime_source:
            clv.REGIME_SOURCE = self.original_regime_source
        elif hasattr(clv, "REGIME_SOURCE"):
            delattr(clv, "REGIME_SOURCE")
        clv.now = self.original_now

    def _row(self, sport, regime, *, game_key="GAME", side="HOME"):
        row = {
            "sport": sport,
            "game_key": game_key,
            "selection": "Example Team",
            "side": side,
            "american_odds": -110,
            "event_start": "2026-10-08T20:00:00Z",
            "book_count": 5,
            "market_fair_probability_pct": 52.0,
            "market_reference_probability_pct": 52.0,
            "market_reference_type": "DEVIG_FAIR",
            "devig_paired_books": 5,
            "hulk_evidence_score": 80.0,
            "calibrated_win_probability_pct": 52.0,
            "expected_value_pct": 0.0,
            "conservative_expected_value_pct": -5.0,
            "data_quality_grade": "B",
            "shadow_decision": "PASS_NO_PROVEN_MODEL_EDGE",
            "probability_source": "MARKET_REFERENCE",
            "historical_edge_confidence": "NO_INDEPENDENT_EDGE",
            "selection_rule_status": "NO_INDEPENDENT_MODEL_EDGE",
            "competition_regime": regime,
            "proof_lane_key": proof_lane_key(
                sport,
                "MONEYLINE",
                regime,
            ),
            "proof_version": proof_version(
                MODEL_VERSION,
                sport,
                regime,
            ),
        }
        return row

    def _read_jsonl(self, path):
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text().splitlines()
            if line.strip()
        ]

    def test_nba_clv_key_is_regime_specific(self):
        preseason = self._row("NBA", "PRESEASON")
        regular = self._row("NBA", "REGULAR")

        self.assertNotEqual(
            clv.regime_clv_key(preseason),
            clv.regime_clv_key(regular),
        )

    def test_cfb_and_legacy_nba_keys_remain_legacy_compatible(self):
        cfb = self._row("CFB", "REGULAR")
        self.assertEqual(clv.regime_clv_key(cfb), clv.row_key(cfb))

        legacy_nba = self._row("NBA", "PRESEASON")
        legacy_nba.pop("competition_regime")
        legacy_nba.pop("proof_lane_key")
        legacy_nba.pop("proof_version")
        self.assertEqual(
            clv.regime_clv_key(legacy_nba),
            clv.row_key(legacy_nba),
        )

    def test_capture_freezes_regime_metadata_into_pick_and_market_price(self):
        row = self._row("NBA", "PRESEASON")
        clv.CURRENT.write_text(json.dumps({
            "status": "READY",
            "model_version": MODEL_VERSION,
            "picks": [row],
            "market_board": [row],
        }))

        price_added = clv.snapshot_market_board(
            json.loads(clv.CURRENT.read_text())
        )
        pick_added = clv.capture_v2_picks(
            json.loads(clv.CURRENT.read_text())
        )

        self.assertEqual(price_added, 1)
        self.assertEqual(pick_added, 1)

        price = self._read_jsonl(clv.PRICE_LEDGER)[0]
        pick = self._read_jsonl(clv.PICK_LEDGER)[0]
        for event in (price, pick):
            self.assertEqual(event["competition_regime"], "PRESEASON")
            self.assertEqual(
                event["proof_lane_key"],
                "NBA_MONEYLINE|PRESEASON",
            )
            self.assertEqual(event["proof_version"], row["proof_version"])

    def test_close_event_inherits_frozen_entry_regime_metadata(self):
        row = self._row("NBA", "PRESEASON")
        row["event_start"] = "2026-10-07T11:00:00Z"
        payload = {
            "status": "READY",
            "model_version": MODEL_VERSION,
            "picks": [row],
            "market_board": [row],
        }

        clv.now = lambda: datetime(
            2026, 10, 7, 10, 0, tzinfo=timezone.utc
        )
        clv.snapshot_market_board(payload)
        clv.capture_v2_picks(payload)

        clv.now = lambda: datetime(
            2026, 10, 7, 12, 0, tzinfo=timezone.utc
        )
        closed = clv.finalize_closes()
        events = self._read_jsonl(clv.PICK_LEDGER)
        close = events[-1]

        self.assertEqual(closed, 1)
        self.assertEqual(close["event_type"], "CLOSE")
        self.assertEqual(close["competition_regime"], "PRESEASON")
        self.assertEqual(
            close["proof_lane_key"],
            "NBA_MONEYLINE|PRESEASON",
        )
        self.assertEqual(
            close["proof_version"],
            row["proof_version"],
        )

    def test_clv_summary_separates_regimes_and_proof_lanes(self):
        events = []
        for regime, fair_clv in (("PRESEASON", 1.5), ("REGULAR", -0.5)):
            row = self._row(
                "NBA",
                regime,
                game_key=f"GAME_{regime}",
            )
            key = clv.regime_clv_key(row)
            events.extend([
                {
                    "event_type": "ENTRY",
                    "pick_key": key,
                    "sport": "NBA",
                    "game_key": row["game_key"],
                    "selection": row["selection"],
                    "side": row["side"],
                    "competition_regime": regime,
                    "proof_lane_key": row["proof_lane_key"],
                    "proof_version": row["proof_version"],
                    "status": "OPEN",
                    "entry_v2_shadow_decision": "PASS_NO_PROVEN_MODEL_EDGE",
                },
                {
                    "event_type": "CLOSE",
                    "pick_key": key,
                    "competition_regime": regime,
                    "proof_lane_key": row["proof_lane_key"],
                    "proof_version": row["proof_version"],
                    "status": "CLOSED",
                    "clv_direction": (
                        "BEAT_CLOSE" if fair_clv > 0 else "LOST_TO_CLOSE"
                    ),
                    "fair_clv_probability_pp": fair_clv,
                    "raw_clv_probability_pp": fair_clv,
                    "clv_ev_pct_at_entry_price": fair_clv,
                    "closed_at": "2026-10-07T12:00:00Z",
                },
            ])

        clv.PICK_LEDGER.write_text(
            "".join(json.dumps(event) + "\n" for event in events)
        )

        payload = clv.build_output()

        self.assertEqual(payload["summary"]["tracked"], 2)
        self.assertEqual(
            payload["by_regime"]["PRESEASON"]["tracked"],
            1,
        )
        self.assertEqual(
            payload["by_regime"]["REGULAR"]["tracked"],
            1,
        )
        self.assertEqual(
            payload["by_proof_lane"]["NBA_MONEYLINE|PRESEASON"]["tracked"],
            1,
        )
        self.assertEqual(
            payload["by_proof_lane"]["NBA_MONEYLINE|REGULAR"]["tracked"],
            1,
        )

    def test_main_enriches_missing_nba_regime_from_all_markets_current(self):
        legacy = self._row("NBA", "PRESEASON")
        legacy.pop("competition_regime")
        legacy.pop("proof_lane_key")
        legacy.pop("proof_version")

        source = self._row("NBA", "PRESEASON")
        clv.REGIME_SOURCE.write_text(json.dumps({
            "status": "READY",
            "model_version": MODEL_VERSION,
            "picks": [source],
        }))
        clv.CURRENT.write_text(json.dumps({
            "status": "READY",
            "model_version": MODEL_VERSION,
            "picks": [legacy],
            "market_board": [legacy],
        }))

        clv.main()

        pick = self._read_jsonl(clv.PICK_LEDGER)[0]
        price = self._read_jsonl(clv.PRICE_LEDGER)[0]
        self.assertEqual(pick["competition_regime"], "PRESEASON")
        self.assertEqual(price["competition_regime"], "PRESEASON")
        self.assertEqual(
            pick["proof_lane_key"],
            "NBA_MONEYLINE|PRESEASON",
        )

    def test_canonical_entries_still_reads_legacy_pick_without_regime(self):
        legacy = {
            "event_type": "ENTRY",
            "pick_key": "NBA|GAME|HOME",
            "sport": "NBA",
            "game_key": "GAME",
            "selection": "Example Team",
            "side": "HOME",
            "status": "OPEN",
        }
        clv.PICK_LEDGER.write_text(json.dumps(legacy) + "\n")

        entries = clv.canonical_entries()

        self.assertIn(legacy["pick_key"], entries)
        self.assertNotIn(
            "competition_regime",
            entries[legacy["pick_key"]],
        )

    def test_capture_can_bridge_regime_from_all_markets_current(self):
        self.assertTrue(hasattr(clv, "REGIME_SOURCE"))
        source_row = self._row("NBA", "PRESEASON")
        source_row["market"] = "MONEYLINE"
        clv.REGIME_SOURCE.write_text(json.dumps({
            "status": "READY",
            "model_version": MODEL_VERSION,
            "picks": [source_row],
        }))
        legacy_shape = dict(source_row)
        legacy_shape.pop("competition_regime")
        legacy_shape.pop("proof_lane_key")
        legacy_shape.pop("proof_version")
        payload = {
            "status": "READY",
            "model_version": "BETTING_V2_FAIR_MARKET_CONFIDENCE_2026_10_05",
            "picks": [legacy_shape],
            "market_board": [legacy_shape],
        }

        self.assertEqual(clv.snapshot_market_board(payload), 1)
        self.assertEqual(clv.capture_v2_picks(payload), 1)
        price = self._read_jsonl(clv.PRICE_LEDGER)[0]
        pick = self._read_jsonl(clv.PICK_LEDGER)[0]

        for event in (price, pick):
            self.assertEqual(event["competition_regime"], "PRESEASON")
            self.assertEqual(
                event["proof_lane_key"],
                "NBA_MONEYLINE|PRESEASON",
            )
            self.assertEqual(
                event["proof_version"],
                source_row["proof_version"],
            )

    def test_close_inherits_frozen_regime_metadata_from_entry(self):
        row = self._row("NBA", "PRESEASON")
        row["event_start"] = "2026-10-07T10:00:00Z"
        key = clv.regime_clv_key(row)
        entry = {
            "event_type": "ENTRY",
            "pick_key": key,
            "entry_at": "2026-10-07T08:00:00Z",
            "sport": "NBA",
            "game_key": row["game_key"],
            "selection": row["selection"],
            "side": row["side"],
            "event_start": row["event_start"],
            "entry_american_odds": -110,
            "entry_raw_implied_probability_pct": 52.381,
            "entry_market_fair_probability_pct": 52.0,
            "competition_regime": "PRESEASON",
            "proof_lane_key": row["proof_lane_key"],
            "proof_version": row["proof_version"],
            "status": "OPEN",
        }
        price = {
            "event_type": "MARKET_PRICE",
            "market_key": key,
            "captured_at": "2026-10-07T09:00:00Z",
            "american_odds": -115,
            "raw_implied_probability_pct": 53.4884,
            "market_fair_probability_pct": 53.0,
            "book_count": 5,
            "competition_regime": "PRESEASON",
            "proof_lane_key": row["proof_lane_key"],
            "proof_version": row["proof_version"],
        }
        clv.PICK_LEDGER.write_text(json.dumps(entry) + "\n")
        clv.PRICE_LEDGER.write_text(json.dumps(price) + "\n")

        self.assertEqual(clv.finalize_closes(), 1)
        close = self._read_jsonl(clv.PICK_LEDGER)[-1]

        self.assertEqual(close["competition_regime"], "PRESEASON")
        self.assertEqual(close["proof_lane_key"], row["proof_lane_key"])
        self.assertEqual(close["proof_version"], row["proof_version"])

    def test_clv_output_separates_regime_and_proof_lane(self):
        events = []
        for regime in ("PRESEASON", "REGULAR"):
            row = self._row("NBA", regime, game_key=f"GAME_{regime}")
            key = clv.regime_clv_key(row)
            events.extend([
                {
                    "event_type": "ENTRY",
                    "pick_key": key,
                    "sport": "NBA",
                    "game_key": row["game_key"],
                    "selection": row["selection"],
                    "side": row["side"],
                    "competition_regime": regime,
                    "proof_lane_key": row["proof_lane_key"],
                    "proof_version": row["proof_version"],
                    "status": "OPEN",
                },
                {
                    "event_type": "CLOSE",
                    "pick_key": key,
                    "competition_regime": regime,
                    "proof_lane_key": row["proof_lane_key"],
                    "proof_version": row["proof_version"],
                    "status": "CLOSED",
                    "clv_direction": "BEAT_CLOSE",
                    "fair_clv_probability_pp": 1.0,
                    "clv_ev_pct_at_entry_price": 1.0,
                    "closed_at": f"2026-10-07T0{8 if regime == 'PRESEASON' else 9}:00:00Z",
                },
            ])
        clv.PICK_LEDGER.write_text(
            "".join(json.dumps(event) + "\n" for event in events)
        )

        output = clv.build_output()

        self.assertEqual(output["summary"]["tracked"], 2)
        self.assertEqual(
            set(output["by_regime"]),
            {"PRESEASON", "REGULAR"},
        )
        self.assertEqual(output["by_regime"]["PRESEASON"]["tracked"], 1)
        self.assertEqual(output["by_regime"]["REGULAR"]["tracked"], 1)
        self.assertEqual(
            set(output["by_proof_lane"]),
            {"NBA_MONEYLINE|PRESEASON", "NBA_MONEYLINE|REGULAR"},
        )
        self.assertEqual(
            output["by_proof_lane"]["NBA_MONEYLINE|PRESEASON"]["tracked"],
            1,
        )
        self.assertEqual(
            output["by_proof_lane"]["NBA_MONEYLINE|REGULAR"]["tracked"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
