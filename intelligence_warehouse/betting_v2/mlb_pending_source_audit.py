"""Read-only proof for why frozen MLB predictions still await final grades.

The MLB forward receipt is generated from exact original-game and official
MLB box-score evidence. Counts are useful only when they reconcile to the
currently frozen append-only ledger. Never treat a stale or partial source
receipt as proof that games were final, players did not play, or bets voided.
"""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

SOURCE_RECEIPT = (
    "intelligence_warehouse/betting_v2/"
    "MLB_OFFICIAL_BOX_FORWARD_RECEIPT.json"
)
FINAL_AWAIT = "NO_OFFICIAL_FINAL_BOX"
APPEARANCE = "PLAYER_NOT_VERIFIED_PLAYED"
INVALID_CAPTURE = "NOT_VERIFIED_PREGAME_OR_START"


def natural_number(value):
    return (
        value if isinstance(value, int) and not isinstance(value, bool)
        and value >= 0 else None
    )


def official_pending_breakdown(root: Path, *, pending: int, settled: int) -> dict:
    """Return verified bucket counts, or explicitly refuse stale evidence."""
    initial = {
        "status": "UNVERIFIED_OFFICIAL_RECEIPT",
        "pending_total": pending,
        "settled_total": settled,
        "official_receipt_generated_at": None,
        "awaiting_official_final": None,
        "unverified_player_participation": None,
        "unverified_pregame_capture": None,
        "other_source_holds": None,
        "verified_ready_next_batch": None,
        "manual_evidence_review": None,
        "wager_void_or_payout_claimed": False,
        "automatic_model_promotion": False,
        "message": (
            "Pending is not a loss. No official-source classification is "
            "claimed until the current ledger and receipt reconcile."
        ),
    }
    try:
        payload = json.loads((Path(root) / SOURCE_RECEIPT).read_text())
    except (OSError, ValueError, TypeError):
        return initial
    if not isinstance(payload, dict):
        return initial

    initial["official_receipt_generated_at"] = payload.get("generated_at")
    if payload.get("status") != "READY":
        initial["status"] = "OFFICIAL_SOURCE_NOT_READY"
        return initial

    reasons = payload.get("review_reasons")
    if not isinstance(reasons, dict) or any(
        not isinstance(reason, str) or natural_number(count) is None
        for reason, count in reasons.items()
    ):
        initial["status"] = "INVALID_OFFICIAL_RECEIPT"
        return initial

    batches = payload.get("batch_results")
    if not isinstance(batches, list) or not batches:
        initial["status"] = "INVALID_OFFICIAL_RECEIPT"
        return initial
    last = batches[-1]
    if not isinstance(last, dict):
        initial["status"] = "INVALID_OFFICIAL_RECEIPT"
        return initial
    last_settled = natural_number(last.get("settled"))
    verified_waiting = natural_number(
        payload.get("verified_remaining_for_future_refresh")
    )
    existing_verified = natural_number(payload.get("existing_verified"))
    conflicts = natural_number(payload.get("conflicting_previous_grades_count"))
    if (
        last_settled is None or verified_waiting is None
        or existing_verified is None or conflicts is None or conflicts
        or natural_number(pending) is None or natural_number(settled) is None
    ):
        initial["status"] = "INVALID_OFFICIAL_RECEIPT"
        return initial

    if sum(reasons.values()) + verified_waiting != pending or (
        existing_verified + last_settled != settled
    ):
        initial["status"] = "STALE_OFFICIAL_RECEIPT"
        return initial

    expected_digest = payload.get("forward_ledger_sha256")
    expected_bytes = natural_number(payload.get("forward_ledger_bytes"))
    if (not isinstance(expected_digest, str) or len(expected_digest) != 64
            or any(c not in "0123456789abcdef" for c in expected_digest)
            or expected_bytes is None):
        initial["status"] = "NO_EXACT_FROZEN_LEDGER_SOURCE_PROOF"
        return initial
    try:
        ledger = Path(root) / "intelligence_warehouse/betting_v2/PROP_V2_FORWARD_LEDGER.jsonl"
        if ledger.stat().st_size != expected_bytes:
            initial["status"] = "STALE_OFFICIAL_RECEIPT"
            return initial
        digest = sha256()
        with ledger.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != expected_digest:
            initial["status"] = "STALE_OFFICIAL_RECEIPT"
            return initial
    except OSError:
        initial["status"] = "STALE_OFFICIAL_RECEIPT"
        return initial

    future = reasons.get(FINAL_AWAIT, 0)
    unplayed = reasons.get(APPEARANCE, 0)
    bad_capture = reasons.get(INVALID_CAPTURE, 0)
    other = sum(v for k, v in reasons.items()
                if k not in {FINAL_AWAIT, APPEARANCE, INVALID_CAPTURE})
    initial.update({
        "status": "SOURCE_RECONCILED",
        "awaiting_official_final": future,
        "unverified_player_participation": unplayed,
        "unverified_pregame_capture": bad_capture,
        "other_source_holds": other,
        "verified_ready_next_batch": verified_waiting,
        "manual_evidence_review": unplayed + bad_capture + other,
        "message": (
            "Official final-game waits, unverified player participation, "
            "and invalid pregame captures are distinct. None implies a "
            "sportsbook void or a loss. Generic age-based overdue counts "
            "do not mean an officially gradeable result is available."
        ),
    })
    return initial
