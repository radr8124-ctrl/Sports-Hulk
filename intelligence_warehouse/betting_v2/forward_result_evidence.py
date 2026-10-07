"""Cross-sport settlement evidence rules.

The same frozen game/player/market key may occur in multiple historical
snapshots. Agreement is mandatory; contradictory official outcomes must not
silently overwrite one another or auto-settle forward predictions.
"""
from __future__ import annotations

from math import isfinite
from typing import Any


def as_number(value: Any) -> float | None:
    try:
        result = float(value)
        return result if isfinite(result) else None
    except (ValueError, TypeError):
        return None


def register_evidence(lookup: dict, key: str, candidate: dict) -> None:
    """Merge only consistent source evidence; contradictory keys are poisoned."""
    if not key:
        return
    prior = lookup.get(key)
    if prior is None:
        lookup[key] = dict(candidate)
        return
    if prior.get("ambiguous"):
        return

    reasons = []
    if prior.get("grade") != candidate.get("grade"):
        reasons.append("CONFLICTING_GRADES")
    for field in ("actual_value", "home_score", "away_score"):
        old = as_number(prior.get(field))
        new = as_number(candidate.get(field))
        if old is not None and new is not None and abs(old - new) > 1e-8:
            reasons.append("CONFLICTING_" + field.upper())
    for field in ("source_event_id", "game_key", "leg1_grade", "leg2_grade"):
        old = str(prior.get(field) or "").strip()
        new = str(candidate.get(field) or "").strip()
        if old and new and old != new:
            reasons.append("CONFLICTING_" + field.upper())
    if reasons:
        lookup[key] = {
            "ambiguous": True,
            "reason": "|".join(sorted(set(reasons))),
        }
        return

    # Preserve the most complete proof, and the latest corroborating
    # graded observation if completeness ties.
    old_present = sum(prior.get(k) is not None for k in
                      ("actual_value", "home_score", "away_score"))
    new_present = sum(candidate.get(k) is not None for k in
                      ("actual_value", "home_score", "away_score"))
    if new_present > old_present or (
        new_present == old_present
        and str(candidate.get("grade_snapshot_at") or "") >=
        str(prior.get("grade_snapshot_at") or "")
    ):
        lookup[key] = dict(candidate)


def trusted_result(match: dict | None) -> bool:
    return bool(
        match and not match.get("ambiguous") and
        match.get("grade") in {"WIN", "LOSS", "PUSH"}
    )
