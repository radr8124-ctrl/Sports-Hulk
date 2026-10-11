"""Describe observed slate timing separately from solver feasibility."""
from datetime import datetime, timezone


def slate_timing_evidence(rows, slate_id, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Timing checks require a timezone-aware clock")
    now = now.astimezone(timezone.utc)
    selected = [row for row in rows if slate_id is None or str(row.get("slate_id")) == str(slate_id)]
    times = []
    missing = 0
    for row in selected:
        try:
            value = str(row.get("game_time") or "").strip()
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("Missing timezone")
            times.append(parsed.astimezone(timezone.utc))
        except (ValueError, TypeError, OverflowError):
            missing += 1
    first = min(times) if times else None
    if first is not None and first <= now:
        status = "SLATE_STARTED"
    elif not selected or missing:
        status = "GAME_TIMES_UNVERIFIED"
    else:
        status = "PREGAME_TIMES_OBSERVED"
    return {
        "status": status,
        "checked_at": now.isoformat(),
        "slate_id": str(slate_id) if slate_id is not None else None,
        "first_game_time": first.isoformat() if first else None,
        "rows_checked": len(selected),
        "missing_game_time_rows": missing,
        "pregame_timing_observed": status == "PREGAME_TIMES_OBSERVED",
        "contest_entry_verified": False,
        "late_swap_verified": False,
        "purpose": "PAPER_RESEARCH",
    }
