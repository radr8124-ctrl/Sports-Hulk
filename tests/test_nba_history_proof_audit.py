"""NBA historical proof audit never treats stale/unverified rows as bets."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from nba_live.decision.audit_nba_historical_proof import (
    atomic_receipt, run, summarize,
)
from nba_live.decision.nba_proof_source_digest import digest_rows, digest_csv


def example(*, market="TOTAL", grade="WIN", season_type="1",
            lane="GAME", game_key="2026-10-03|MIA|TOR",
            snap="2026-10-03T15:00:00+00:00",
            start="2026-10-03T23:00:00+00:00"):
    return {
        "lane": lane, "market": market, "grade": grade,
        "season_type": season_type, "game_key": game_key,
        "snapshot_at": snap, "start": start,
    }


class NbaProofAuditTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.validation = {
            "generated_at": self.now.isoformat(),
            "lanes": {
                "NBA_TOTAL|PRESEASON": {
                    "history_n": 10, "status": "INSUFFICIENT_HISTORY",
                    "competition_regime": "PRESEASON",
                },
                "NFL_TOTAL": {"history_n": 50, "status": "READY"},
            },
        }

    def test_groups_preseason_and_regular_independently(self):
        rows = [
            example(grade="WIN", season_type="1"),
            example(grade="LOSS", season_type="2", game_key="2026-10-20|PHI|NYK"),
            example(grade="PENDING", season_type="2"),
            example(grade="LOSS", market="PARLAY", lane="PARLAY"),
        ]
        doc = summarize(rows, validation=self.validation)
        self.assertEqual(doc["graded_game_observations"], 3)
        self.assertEqual(doc["graded_non_game_observations"], 1)
        self.assertEqual(doc["cohorts"]["NBA_TOTAL|PRESEASON"]["win"], 1)
        self.assertEqual(doc["cohorts"]["NBA_TOTAL|REGULAR"]["pending_or_review"], 1)
        self.assertEqual(doc["cohorts"]["NBA_TOTAL|REGULAR"]["observed_hit_rate_pct"], 0)
        self.assertFalse(doc["automatic_promotion_permitted"])
        self.assertTrue(doc["excludes_parlay_claims"])
        self.assertEqual(set(doc["betting_validation_nba_lanes"]), {"NBA_TOTAL|PRESEASON"})

    def test_unknown_stays_unknown_and_no_date_guessing(self):
        doc = summarize([example(season_type="", start="2026-10-20T23:00Z")],
                        validation=self.validation)
        self.assertIn("NBA_TOTAL|UNKNOWN", doc["cohorts"])
        self.assertNotIn("NBA_TOTAL|REGULAR", doc["cohorts"])

    def test_failed_source_result_is_not_settled_loss(self):
        doc = summarize([example(grade="REVIEW_SOURCE_CONFLICT")],
                        validation=self.validation)
        sample = doc["cohorts"]["NBA_TOTAL|PRESEASON"]
        self.assertEqual(sample["loss"], 0)
        self.assertEqual(sample["win"], 0)
        self.assertEqual(sample["pending_or_review"], 1)
        self.assertEqual(sample["conflicting_source_results"], 1)
        self.assertIsNone(sample["observed_hit_rate_pct"])

    def test_no_pregame_snapshot_claim_for_after_tipoff(self):
        doc = summarize([example(snap="2026-10-04T01:00:00Z")],
                        validation=self.validation)
        self.assertEqual(doc["cohorts"]["NBA_TOTAL|PRESEASON"]["pregame_snapshot_rows"], 0)

    def test_detects_stale_proof_after_grading(self):
        doc = summarize([example()],
                        graded_mtime=self.now + timedelta(seconds=3),
                        validation=self.validation)
        self.assertTrue(doc["betting_proof_stale"])
        self.assertEqual(doc["status"], "STALE_BETTING_PROOF")

    def test_fresh_proof_is_audited_not_promoted(self):
        doc = summarize([example()],
                        graded_mtime=self.now - timedelta(seconds=3),
                        validation=self.validation)
        self.assertEqual(doc["status"], "AUDITED")
        self.assertFalse(doc["betting_proof_stale"])
        self.assertFalse(doc["automatic_promotion_permitted"])

    def test_missing_validation_marks_unverified(self):
        doc = summarize([example()], graded_mtime=self.now, validation={})
        self.assertTrue(doc["betting_proof_stale"])
        self.assertEqual(doc["status"], "STALE_BETTING_PROOF")

    def test_atomic_receipt_does_not_change_history(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = root / "report.json"
            graded = root / "graded.csv"
            graded.write_text(
                "lane,market,grade,season_type,game_key,snapshot_at,start\n"
                "GAME,TOTAL,WIN,1,2026-10-03|MIA|TOR,2026-10-03T15:00:00Z,2026-10-03T23:00:00Z\n"
            )
            before = graded.read_bytes()
            result = run(graded, root / "missing.json")
            atomic_receipt(out, result)
            self.assertEqual(graded.read_bytes(), before)
            self.assertTrue(out.exists())
            self.assertFalse(json.loads(out.read_text())["automatic_promotion_permitted"])

    def test_digest_ignores_repeated_identical_exports_and_parlays(self):
        original = example(season_type="1.0")
        canonical = example(season_type="1")
        non_game = example(lane="PARLAY", market="PARLAY", grade="LOSS")
        self.assertEqual(digest_rows([original]), digest_rows([canonical, non_game]))
        self.assertNotEqual(digest_rows([original]), digest_rows([example(season_type="2")]))

    def test_digest_proves_fresh_history_despite_new_file_timestamp(self):
        source = digest_rows([example()])
        validation = {**self.validation, "source_fingerprints": {"nba_game_grades_sha256": source}}
        doc = summarize(
            [example()], graded_mtime=self.now + timedelta(minutes=35),
            validation=validation, source_digest=source,
        )
        self.assertEqual(doc["status"], "AUDITED")
        self.assertFalse(doc["betting_proof_stale"])
        self.assertEqual(doc["freshness_method"], "CANONICAL_GAME_SHA256")
        self.assertFalse(doc["automatic_promotion_permitted"])

    def test_digest_detects_real_grade_or_regime_change(self):
        old = digest_rows([example(grade="WIN", season_type="1")])
        validation = {**self.validation, "source_fingerprints": {"nba_game_grades_sha256": old}}
        doc = summarize(
            [example(grade="LOSS", season_type="2")],
            graded_mtime=self.now - timedelta(minutes=35),
            validation=validation,
            source_digest=digest_rows([example(grade="LOSS", season_type="2")]),
        )
        self.assertTrue(doc["betting_proof_stale"])
        self.assertEqual(doc["status"], "STALE_BETTING_PROOF")

    def test_absent_graded_history_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            doc = run(Path(d) / "does-not-exist.csv", Path(d) / "valid.json")
            self.assertEqual(doc["status"], "MISSING_GRADED_HISTORY")
            self.assertFalse(doc["automatic_promotion_permitted"])


if __name__ == "__main__":
    unittest.main()
