#!/usr/bin/env python3
"""Privacy/fail-closed checks for the separate Sports Zenith PostHog observer."""
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "zenith_posthog_monitor", HERE / "scripts" / "zenith_posthog_monitor.py"
)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def trace(**extra):
    row = {
        "recorded_at": "2026-10-10T11:59:00Z",
        "route_lane": "GENERIC",
        "intent": "ref_market_research",
        "status": "RESEARCH_ONLY",
        "latency_ms": 127,
        "source_count": 2,
        "claim_source_count": 1,
        "output_validation_valid": True,
        "error": False,
        "trace_id": "PRIVATE_TRACE_CANARY",
        "question_hash": "SECRET_QUESTION_HASH",
        "question": "SECRET_RAW_QUESTION",
        "page": "SECRET_URL_ROUTE",
        "confidence": "SECRET_UNBOUNDED_TEXT",
        "output_validation_errors": ["SECRET_INPUT_FRAGMENT"],
        "user_email": "SECRET_USER_EMAIL",
    }
    row.update(extra)
    return row


class PrivacyContract(unittest.TestCase):
    def test_payload_never_copies_untrusted_private_fields(self):
        payload = monitor.build_event(trace())
        self.assertEqual(payload["event"], "zenith_ask_review")
        self.assertEqual(payload["distinct_id"], "zenith-anonymous-server")
        self.assertFalse(payload["properties"]["$process_person_profile"])
        self.assertEqual(payload["properties"]["intent_bucket"], "ref_market_research")
        self.assertEqual(payload["properties"]["source_count"], 2)
        rendered = json.dumps(payload)
        for marker in (
            "SECRET_", "trace_id", "question", "email", "user", "page",
            "confidence", "source_ids", "event_id",
        ):
            self.assertNotIn(marker, rendered)

    def test_personal_fantasy_and_survivor_never_generate_events(self):
        for lane in ("PERSONAL_FANTASY", "PERSONAL_SURVIVOR", "UNKNOWN", "private"):
            self.assertIsNone(monitor.build_event(trace(route_lane=lane)))

    def test_unknown_text_buckets_and_counts_fail_closed(self):
        p = monitor.build_event(
            trace(intent="SECRET_UNBOUNDED_TEXT", status="SECRET_STATUS",
                  source_count=888, claim_source_count=-4, latency_ms=1e10,
                  output_validation_valid="true")
        )
        self.assertEqual(p["properties"]["intent_bucket"], "OTHER")
        self.assertEqual(p["properties"]["status_bucket"], "OTHER")
        self.assertLessEqual(p["properties"]["source_count"], 20)
        self.assertGreaterEqual(p["properties"]["claim_source_count"], 0)
        self.assertEqual(p["properties"]["output_valid"], False)
        self.assertLessEqual(p["properties"]["latency_ms"], 60_000)


class LedgerPolling(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = Path(self.tmp.name) / "trace.jsonl"
        self.state = Path(self.tmp.name) / "state.json"
        self.ledger.write_bytes((json.dumps(trace()) + "\n").encode())
        self.events = []
        self.send = lambda event: self.events.append(event) or True

    def append(self, record):
        with self.ledger.open("ab") as handle:
            handle.write((json.dumps(record) + "\n").encode())

    def run_monitor(self, sender=None, cap=50):
        return monitor.process_new_records(
            self.ledger, self.state,
            sender or self.send, now=NOW, daily_cap=cap,
        )

    def test_first_run_starts_at_end_never_backfills_old_questions(self):
        result = self.run_monitor()
        self.assertEqual(result["status"], "INITIALIZED")
        self.assertFalse(self.events)
        self.append(trace())
        result = self.run_monitor()
        self.assertEqual(result["sent"], 1)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.run_monitor()["sent"], 0)

    def test_private_lane_skipped_without_export(self):
        self.run_monitor()
        self.append(trace(route_lane="PERSONAL_SURVIVOR"))
        self.append(trace(route_lane="PERSONAL_FANTASY"))
        self.append(trace())
        result = self.run_monitor()
        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["private_skipped"], 2)
        self.assertEqual(len(self.events), 1)

    def test_network_failure_retries_without_dropping_cursor(self):
        self.run_monitor()
        self.append(trace())
        result = self.run_monitor(sender=lambda _: False)
        self.assertEqual(result["status"], "SEND_FAILED")
        self.assertEqual(len(self.events), 0)
        self.assertEqual(self.run_monitor()["sent"], 1)

    def test_daily_cap_discards_extra_records_instead_of_billing(self):
        self.run_monitor(cap=1)
        for _ in range(3):
            self.append(trace())
        result = self.run_monitor(cap=1)
        self.assertEqual(result["sent"], 1)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.run_monitor(cap=1)["sent"], 0)

    def test_recording_of_stale_rows_is_rejected(self):
        self.run_monitor()
        self.append(trace(recorded_at="2026-01-01T12:00:00Z"))
        result = self.run_monitor()
        self.assertEqual(result["sent"], 0)
        self.assertFalse(self.events)

    def test_incomplete_lines_wait_for_completion(self):
        self.run_monitor()
        with self.ledger.open("ab") as handle:
            handle.write(json.dumps(trace()).encode())
        self.assertEqual(self.run_monitor()["sent"], 0)
        with self.ledger.open("ab") as handle:
            handle.write(b"\n")
        self.assertEqual(self.run_monitor()["sent"], 1)


if __name__ == "__main__":
    unittest.main()
