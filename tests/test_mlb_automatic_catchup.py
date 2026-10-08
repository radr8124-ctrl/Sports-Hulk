"""Automatic MLB results catch-up uses repeatable 100-result proof batches."""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from intelligence_warehouse.betting_v2 import build_prop_v2_forward as forward
from intelligence_warehouse.betting_v2 import mlb_official_box_forward as official
from test_mlb_official_box_forward import (
    ENTRY, SOURCE_ROW, FakeSession, csvfile,
)


def synthetic_frozen_rows(count):
    return [
        dict(ENTRY, forward_key=f"mlb-frozen-proof-{n:04d}", line=0.5 + n * 0.001)
        for n in range(count)
    ]


class FlakyAfterFirstVerifiedSession(FakeSession):
    def __init__(self):
        super().__init__()
        self.schedule_calls = 0

    def get(self, url, **kwargs):
        if url == official.SCHEDULE_URL:
            self.schedule_calls += 1
            if self.schedule_calls > 1:
                raise TimeoutError("MLB official source unavailable on next batch")
        return super().get(url, **kwargs)


class MlbAutomaticCatchUpTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        path = self.root / (
            "mlb_live/decision/history/snapshots/20261005T180000Z_fixture"
            "/MLB_PROP_CANDIDATES.csv"
        )
        csvfile(path, [dict(SOURCE_ROW)])
        out = self.root / "intelligence_warehouse/betting_v2"
        out.mkdir(parents=True, exist_ok=True)
        self.ledger = out / "PROP_V2_FORWARD_LEDGER.jsonl"
        self.receipt = out / "MLB_OFFICIAL_BOX_FORWARD_RECEIPT.json"

    def setup_frozen(self, size):
        entries = synthetic_frozen_rows(size)
        self.ledger.write_text("".join(json.dumps(row) + "\n" for row in entries))
        return self.ledger.read_bytes()

    def catchup(self, session=None, **opts):
        with patch.object(forward, "ROOT", self.root), \
             patch.object(forward, "LEDGER", self.ledger), \
             patch.object(forward, "MLB_BOX_RECEIPT", self.receipt):
            report = forward.settle_mlb_official_backlog(
                session=session or FakeSession(), **opts
            )
            canonical = forward.canonical()
        return report, canonical

    def test_350_complete_results_clear_in_four_verified_100_bounded_batches(self):
        before = self.setup_frozen(350)
        report, after = self.catchup()
        self.assertEqual(report["status"], "READY")
        self.assertEqual(report["max_batches_per_refresh"], 4)
        self.assertEqual(report["batch_limit"], 100)
        self.assertEqual(report["settled_now"], 350)
        self.assertEqual(report["batches_executed"], 4)
        self.assertEqual(
            [b["settled"] for b in report["batch_results"]],
            [100, 100, 100, 50],
        )
        self.assertEqual(report["verified_remaining_for_future_refresh"], 0)
        self.assertEqual(len(after), 350)
        self.assertTrue(all(x["grade"] == "WIN" for x in after.values()))
        new = self.ledger.read_bytes()
        self.assertTrue(new.startswith(before))
        self.assertEqual(len(new.decode().splitlines()), 700)
        self.assertFalse(report["automatic_model_promotion"])
        self.assertFalse(report["platform_payout_claimed"])
        self.assertEqual(json.loads(self.receipt.read_text())["settled_now"], 350)
        self.assertEqual(report["forward_ledger_sha256"],
                         sha256(self.ledger.read_bytes()).hexdigest())
        self.assertEqual(report["forward_ledger_bytes"], self.ledger.stat().st_size)

    def test_four_batch_refresh_limit_defers_then_resumes_five_more(self):
        before = self.setup_frozen(405)
        report, after = self.catchup()
        self.assertEqual(report["status"], "READY")
        self.assertEqual(report["settled_now"], 400)
        self.assertEqual(report["verified_remaining_for_future_refresh"], 5)
        self.assertEqual([b["settled"] for b in report["batch_results"]],
                         [100, 100, 100, 100])
        self.assertEqual(sum(r["grade"] == "PENDING" for r in after.values()), 5)
        self.assertTrue(self.ledger.read_bytes().startswith(before))
        second, next_state = self.catchup()
        self.assertEqual(second["settled_now"], 5)
        self.assertEqual(second["batches_executed"], 1)
        self.assertEqual(second["verified_remaining_for_future_refresh"], 0)
        self.assertTrue(all(r["grade"] == "WIN" for r in next_state.values()))
        last, final_state = self.catchup()
        self.assertEqual(last["settled_now"], 0)
        self.assertEqual(last["batches_executed"], 1)
        self.assertEqual(last["existing_verified"], 405)
        self.assertEqual(len(self.ledger.read_text().splitlines()), 810)

    def test_second_source_failure_keeps_first_verified_100_but_fails_closed(self):
        before = self.setup_frozen(120)
        fake = FlakyAfterFirstVerifiedSession()
        report, state = self.catchup(session=fake)
        self.assertEqual(report["status"], "PARTIAL_SOURCE_HOLD")
        self.assertEqual(report["last_batch_status"], "OFFICIAL_API_UNAVAILABLE")
        self.assertEqual(report["batches_executed"], 2)
        self.assertEqual([b["settled"] for b in report["batch_results"]], [100, 0])
        self.assertEqual(report["settled_now"], 100)
        self.assertIsNone(report["verified_remaining_for_future_refresh"])
        self.assertTrue(report["remaining_count_source_hold"])
        self.assertEqual(sum(r["grade"] == "PENDING" for r in state.values()), 20)
        self.assertTrue(self.ledger.read_bytes().startswith(before))
        self.assertEqual(json.loads(self.receipt.read_text())["status"],
                         "PARTIAL_SOURCE_HOLD")
        self.assertEqual(fake.schedule_calls, 2)

    def test_only_final_games_are_eligible_and_empty_pass_does_not_loop(self):
        self.setup_frozen(11)
        fake = FakeSession()
        fake.schedule["dates"][0]["games"][0]["status"]["detailedState"] = "In Progress"
        report, state = self.catchup(session=fake)
        self.assertEqual(report["status"], "READY")
        self.assertEqual(report["settled_now"], 0)
        self.assertEqual(report["batches_executed"], 1)
        self.assertEqual(len(fake.calls), 1)
        self.assertTrue(all(r["grade"] == "PENDING" for r in state.values()))

    def test_safe_on_existing_previously_graded_entries(self):
        rows = synthetic_frozen_rows(105)
        for row in rows[:40]:
            row["grade"] = "WIN"
        self.ledger.write_text("".join(json.dumps(r) + "\n" for r in rows))
        before = self.ledger.read_bytes()
        report, after = self.catchup()
        self.assertEqual(report["status"], "READY")
        self.assertEqual(report["settled_now"], 65)
        self.assertEqual(report["existing_verified"], 40)
        self.assertEqual(len(after), 105)
        self.assertEqual(len(self.ledger.read_text().splitlines()), 170)
        self.assertTrue(self.ledger.read_bytes().startswith(before))
        self.assertTrue(all(v["grade"] == "WIN" for v in after.values()))

    def test_reject_unsafe_batch_sizes_or_recursion(self):
        for opts in (
            {"batch_size": 0}, {"batch_size": 101}, {"batch_size": True},
            {"batch_size": None}, {"max_batches": 0},
            {"max_batches": 5}, {"max_batches": True},
        ):
            with self.subTest(opts=opts):
                with self.assertRaises(ValueError):
                    forward.settle_mlb_official_backlog(session=FakeSession(), **opts)

    def test_hourly_main_uses_catchup_total_for_public_forward_summary(self):
        fake_receipt = {
            "status": "READY", "settled_now": 250,
            "batches_executed": 3,
            "batch_results": [
                {"batch": 1, "settled": 100, "verified_waiting": 150, "status": "READY"},
                {"batch": 2, "settled": 100, "verified_waiting": 50, "status": "READY"},
                {"batch": 3, "settled": 50, "verified_waiting": 0, "status": "READY"},
            ],
            "verified_remaining_for_future_refresh": 0,
            "existing_verified": 300, "conflicting_previous_grades_count": 0,
        }
        summary = {
            "status": "READY", "all_predictions": {},
            "monitor_selection": {}, "by_lane": {},
        }
        with patch.object(forward, "capture", return_value={"entries_added": 0}), \
             patch.object(forward, "settle", return_value=0), \
             patch.object(forward, "settle_nhl_official_box",
                          return_value={"settled_now": 0, "status": "READY"}), \
             patch.object(forward, "settle_mlb_official_backlog",
                          return_value=fake_receipt) as batch_run, \
             patch.object(forward, "build_summary", return_value=summary) as build, \
             patch.object(forward, "write_json") as write, \
             patch("builtins.print"), \
             patch.object(forward, "DIST", Path("/does-not-exist/prop.json")):
            forward.main()
        batch_run.assert_called_once_with()
        build.assert_called_once_with({"entries_added": 0}, 250)
        self.assertEqual(summary["mlb_official_box"]["settled_now"], 250)
        self.assertEqual(summary["mlb_official_box"]["batches_executed"], 3)
        self.assertFalse(summary["mlb_official_box"]["automatic_model_promotion"])
        self.assertTrue(write.called)


if __name__ == "__main__":
    unittest.main()
