"""Official MLB pending receipt classification must match the frozen ledger."""
import json
from hashlib import sha256
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from intelligence_warehouse.betting_v2.forward_results_audit import audit_forward_ledgers
from intelligence_warehouse.betting_v2.mlb_pending_source_audit import (
    official_pending_breakdown, SOURCE_RECEIPT,
)


def source_receipt(**replacements):
    base = {
        "status": "READY",
        "generated_at": "2026-10-08T00:19:45+00:00",
        "existing_verified": 2090,
        "conflicting_previous_grades_count": 0,
        "review_reasons": {
            "NO_OFFICIAL_FINAL_BOX": 368,
            "PLAYER_NOT_VERIFIED_PLAYED": 37,
            "NOT_VERIFIED_PREGAME_OR_START": 3,
        },
        "batch_results": [
            {"batch": 1, "status": "READY", "settled": 0, "verified_waiting": 0}
        ],
        "verified_remaining_for_future_refresh": 0,
    }
    base.update(replacements)
    return base


class MlbPendingSourceProofTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.path = self.root / SOURCE_RECEIPT
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger = self.path.parent / "PROP_V2_FORWARD_LEDGER.jsonl"
        self.ledger.write_bytes(b"frozen-unique-proof-fixture")

    def store(self, data):
        data = dict(data)
        evidence = self.ledger.read_bytes()
        data.setdefault("forward_ledger_sha256", sha256(evidence).hexdigest())
        data.setdefault("forward_ledger_bytes", len(evidence))
        self.path.write_text(json.dumps(data))

    def inspect(self, *, pending=408, settled=2090):
        return official_pending_breakdown(
            self.root, pending=pending, settled=settled,
        )

    def test_exact_live_source_reconciles_all_408_pending(self):
        self.store(source_receipt())
        result = self.inspect()
        self.assertEqual(result["status"], "SOURCE_RECONCILED")
        self.assertEqual(result["awaiting_official_final"], 368)
        self.assertEqual(result["unverified_player_participation"], 37)
        self.assertEqual(result["unverified_pregame_capture"], 3)
        self.assertEqual(result["manual_evidence_review"], 40)
        self.assertEqual(result["verified_ready_next_batch"], 0)
        self.assertEqual(result["other_source_holds"], 0)
        self.assertFalse(result["wager_void_or_payout_claimed"])
        self.assertFalse(result["automatic_model_promotion"])
        self.assertIn("Generic age-based overdue", result["message"])

    def test_unreported_new_frozen_predictions_make_receipt_stale_not_false_ready(self):
        self.store(source_receipt())
        result = self.inspect(pending=409)
        self.assertEqual(result["status"], "STALE_OFFICIAL_RECEIPT")
        self.assertIsNone(result["awaiting_official_final"])
        self.assertIsNone(result["manual_evidence_review"])

    def test_new_settled_result_after_last_official_receipt_invalidates_current_totals(self):
        self.store(source_receipt())
        result = self.inspect(settled=2091)
        self.assertEqual(result["status"], "STALE_OFFICIAL_RECEIPT")

    def test_last_batch_100_grade_and_verified_waiting_safely_accounted(self):
        r = source_receipt(
            existing_verified=2000,
            batch_results=[{"batch": 2, "status": "READY",
                            "settled": 100, "verified_waiting": 50}],
            verified_remaining_for_future_refresh=50,
        )
        self.store(r)
        result = self.inspect(pending=458, settled=2100)
        self.assertEqual(result["status"], "SOURCE_RECONCILED")
        self.assertEqual(result["verified_ready_next_batch"], 50)
        self.assertEqual(result["awaiting_official_final"], 368)

    def test_partial_source_failure_fails_closed_even_after_previous_verified_batch(self):
        self.store(source_receipt(
            status="PARTIAL_SOURCE_HOLD", existing_verified=1990,
            batch_results=[
                {"batch": 1, "status": "READY", "settled": 100},
                {"batch": 2, "status": "OFFICIAL_API_UNAVAILABLE", "settled": 0},
            ],
            verified_remaining_for_future_refresh=None,
        ))
        result = self.inspect()
        self.assertEqual(result["status"], "OFFICIAL_SOURCE_NOT_READY")
        self.assertIsNone(result["awaiting_official_final"])

    def test_missing_receipt_yields_no_claim(self):
        result = self.inspect()
        self.assertEqual(result["status"], "UNVERIFIED_OFFICIAL_RECEIPT")
        self.assertIsNone(result["unverified_player_participation"])

    def test_corrupt_or_wrong_format_receipt_yields_no_claim(self):
        for content in ('invalid json', '[]', '"text"', 'null'):
            with self.subTest(content=content):
                self.path.write_text(content)
                result = self.inspect()
                self.assertIn(result["status"], {
                    "UNVERIFIED_OFFICIAL_RECEIPT",
                    "INVALID_OFFICIAL_RECEIPT",
                })
                self.assertIsNone(result["awaiting_official_final"])

    def test_negative_noninteger_and_boolean_counts_are_rejected(self):
        cases = [
            {"NO_OFFICIAL_FINAL_BOX": -1},
            {"NO_OFFICIAL_FINAL_BOX": True},
            {"NO_OFFICIAL_FINAL_BOX": 368.0},
            {"NO_OFFICIAL_FINAL_BOX": "368"},
        ]
        for reasons in cases:
            with self.subTest(reasons=reasons):
                self.store(source_receipt(review_reasons=reasons))
                self.assertEqual(self.inspect()["status"], "INVALID_OFFICIAL_RECEIPT")

    def test_conflicting_previous_results_block_receipt(self):
        self.store(source_receipt(conflicting_previous_grades_count=1))
        result = self.inspect()
        self.assertEqual(result["status"], "INVALID_OFFICIAL_RECEIPT")

    def test_legacy_receipt_without_exact_ledger_digest_is_not_trusted(self):
        self.path.write_text(json.dumps(source_receipt()))
        self.assertEqual(
            self.inspect()["status"], "NO_EXACT_FROZEN_LEDGER_SOURCE_PROOF"
        )

    def test_same_size_ledger_mutation_poison_source_reason_counts(self):
        self.store(source_receipt())
        self.ledger.write_bytes(b"F" + self.ledger.read_bytes()[1:])
        out = self.inspect()
        self.assertEqual(out["status"], "STALE_OFFICIAL_RECEIPT")
        self.assertIsNone(out["manual_evidence_review"])

    def test_changed_ledger_size_poison_source_reason_counts(self):
        self.store(source_receipt())
        with self.ledger.open("ab") as f:
            f.write(b"new-original-entry")
        self.assertEqual(self.inspect()["status"], "STALE_OFFICIAL_RECEIPT")

    def test_other_new_integrity_holds_are_preserved_without_guessing(self):
        r = source_receipt(review_reasons={
            "NO_OFFICIAL_FINAL_BOX": 365,
            "PLAYER_NOT_VERIFIED_PLAYED": 37,
            "NOT_VERIFIED_PREGAME_OR_START": 3,
            "AMBIGUOUS_PROVIDER_OFFICIAL_GAME": 3,
        })
        self.store(r)
        result = self.inspect()
        self.assertEqual(result["status"], "SOURCE_RECONCILED")
        self.assertEqual(result["other_source_holds"], 3)
        self.assertEqual(result["manual_evidence_review"], 43)

    def test_brain_forward_includes_same_source_truthed_bucket_in_both_views(self):
        dir_ = self.root / "intelligence_warehouse/betting_v2"
        dir_.mkdir(parents=True, exist_ok=True)
        rows = [
            {"event_type": "ENTRY", "forward_key": "frozen-entry-1",
             "sport": "MLB", "grade": "PENDING",
             "event_start": "2026-10-05T21:00:00Z"},
            {"event_type": "ENTRY", "forward_key": "frozen-entry-2",
             "sport": "MLB", "grade": "WIN",
             "event_start": "2026-10-05T21:00:00Z"},
        ]
        (dir_/"PROP_V2_FORWARD_LEDGER.jsonl").write_text(
            "".join(json.dumps(x) + "\n" for x in rows)
        )
        self.store(source_receipt(
            existing_verified=1,
            review_reasons={"PLAYER_NOT_VERIFIED_PLAYED": 1},
        ))
        output = audit_forward_ledgers(
            self.root, at=datetime(2026, 10, 8, 20, tzinfo=timezone.utc),
        )
        mlb = output["by_sport"]["MLB"]["PROPS"]
        first = mlb["official_pending_breakdown"]
        second = output["mlb_official_pending_breakdown"]
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "SOURCE_RECONCILED")
        self.assertEqual(first["unverified_player_participation"], 1)
        self.assertEqual(mlb["pending"], 1)
        self.assertEqual(mlb["pending_overdue_12h"], 1)
        self.assertEqual(mlb["losses"], 0)

    def test_no_official_receipt_preserves_generic_ledger_statistics(self):
        d = self.root / "intelligence_warehouse/betting_v2"
        (d/"PROP_V2_FORWARD_LEDGER.jsonl").write_text(
            json.dumps({"event_type": "ENTRY", "forward_key": "mlb-1",
                        "sport": "MLB", "grade": "PENDING",
                        "event_start": "2026-10-05T21:00:00Z"}) + "\n"
        )
        out = audit_forward_ledgers(
            self.root, at=datetime(2026, 10, 8, 20, tzinfo=timezone.utc),
        )
        mlb = out["by_sport"]["MLB"]["PROPS"]
        self.assertEqual(mlb["status"], "SETTLEMENT_BACKLOG")
        self.assertEqual(mlb["pending_overdue_12h"], 1)
        self.assertEqual(
            mlb["official_pending_breakdown"]["status"],
            "UNVERIFIED_OFFICIAL_RECEIPT",
        )
        self.assertEqual(out["summary"]["tracked"], 1)


if __name__ == "__main__":
    unittest.main()
