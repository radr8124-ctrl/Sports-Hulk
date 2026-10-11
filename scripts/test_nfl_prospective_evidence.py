import tempfile
import unittest
from pathlib import Path

try:
    from nfl_prospective_evidence import capture, eligibility
except ImportError:
    capture = eligibility = None


class ProspectiveEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(eligibility, "prospective cutoff gate is not implemented")
        self.record = dict(evidence_kind="injury_status", event_id="game1", team="KC",
                           player_id="p1", source_url="https://example.com/report",
                           source_published_at="2026-10-11T16:00:00Z",
                           source_ingested_at="2026-10-11T16:01:00Z",
                           captured_at="2026-10-11T16:02:00Z",
                           archive_sha256="a" * 64)
        self.quote = "2026-10-11T16:03:00Z"
        self.kickoff = "2026-10-11T17:00:00Z"

    def check(self, record=None, quote=None, kickoff=None):
        return eligibility(record or self.record, event_id="game1",
                           quote_at=quote or self.quote, kickoff_at=kickoff or self.kickoff)

    def test_complete_evidence_is_eligible_before_quote_and_kickoff(self):
        self.assertEqual(self.check(), [])

    def test_missing_publication_is_not_substituted_with_capture(self):
        self.record["source_published_at"] = ""
        self.assertIn("MISSING_PUBLICATION_TIME", self.check())

    def test_late_ingestion_or_capture_rejects_old_quotes(self):
        for field in ("source_ingested_at", "captured_at"):
            with self.subTest(field=field):
                r = dict(self.record, **{field: "2026-10-11T16:04:00Z"})
                self.assertIn("AFTER_QUOTE", self.check(r))

    def test_event_mismatch_and_missing_identity_rejected(self):
        self.record.update(event_id="other", player_id="")
        self.assertIn("EVENT_MISMATCH", self.check())
        self.assertIn("MISSING_PLAYER_ID", self.check())

    def test_naive_time_and_after_kickoff_rejected(self):
        self.record["source_published_at"] = "2026-10-11T16:00:00"
        self.assertIn("INVALID_PUBLICATION_TIME", self.check())
        self.assertIn("QUOTE_NOT_PREGAME", self.check(quote=self.kickoff))

    def test_news_is_not_verified_player_state_or_starting_qb(self):
        self.record["evidence_kind"] = "news_context"
        self.assertIn("CONTEXT_ONLY", self.check())
        self.record["evidence_kind"] = "confirmed_starting_qb"
        self.assertIn("STARTER_CONFIRMATION_NOT_VERIFIED", self.check())

    def test_snapshot_preserves_source_bytes_and_does_not_backdate_or_confirm_qb(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = root / "inputs"
            inputs.mkdir()
            (inputs / "AVAILABILITY_TIMELINE.csv").write_text(
                "sport,player_id,team,position,source,source_url,observed_at,source_record_at,event_id,status_normalized\n"
                "NFL,p1,KC,QB,ESPN,https://example.com,2026-10-11T16:00:00Z,,,OUT\n")
            (inputs / "AVAILABILITY_REPORTS_CURRENT.csv").write_text("sport,headline\n")
            receipt = capture(inputs, root / "out", "2026-10-11T16:02:00Z")
            self.assertEqual(receipt["injury_records"], 1)
            self.assertEqual(receipt["records_with_publication_time"], 0)
            self.assertEqual(receipt["confirmed_starting_qb_records"], 0)
            archive = Path(receipt["archive_directory"])
            self.assertEqual((archive / "AVAILABILITY_TIMELINE.csv").read_bytes(),
                             (inputs / "AVAILABILITY_TIMELINE.csv").read_bytes())
            import json
            row = json.loads((archive / "records.jsonl").read_text())
            self.assertEqual(row["source_published_at"], "")
            self.assertEqual(row["captured_at"], "2026-10-11T16:02:00Z")
            self.assertEqual(row["evidence_kind"], "injury_status")
            with self.assertRaises(FileExistsError):
                capture(inputs, root / "out", "2026-10-11T16:02:00Z")


if __name__ == "__main__":
    unittest.main()
