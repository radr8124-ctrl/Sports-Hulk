"""Forward-results accountability across NFL/CFB/CBB/MLB/NBA/NHL.

This is a read-only audit of already-frozen predictions. An unmatched
prediction remains PENDING, never an implied loss or a fabricated settlement.
Parlays become overdue only after the latest known leg starts.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

SPORTS = ("NFL", "CFB", "CBB", "MLB", "NBA", "NHL")
FILES = {
    "BEST_BETS": "BETTING_V2_ALL_MARKETS_FORWARD_LEDGER.jsonl",
    "GAME_V2": "BETTING_V2_FORWARD_LEDGER.jsonl",
    "PROPS": "PROP_V2_FORWARD_LEDGER.jsonl",
    "PARLAYS": "PARLAY_V2_FORWARD_LEDGER.jsonl",
}
FINALS = {"WIN", "LOSS", "PUSH"}
OVERDUE_HOURS = 12


def iso_time(raw: Any) -> datetime | None:
    try:
        t = datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00"))
        return t.astimezone(timezone.utc) if t.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


def canonical_ledger(path: Path) -> tuple[dict[str, dict], dict]:
    entries: dict[str, dict] = {}
    issues = Counter()
    if not path.is_file():
        return entries, {"status": "MISSING_FILE", "issues": {"MISSING_FILE": 1}}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError("not object")
                key = str(event.get("forward_key") or "")
                if not key:
                    issues["MISSING_FORWARD_KEY"] += 1
                    continue
                old = entries.get(key, {})
                # Never let a later non-entry without an actual ENTRY
                # manufacture a settled prediction.
                if event.get("event_type") != "ENTRY" and not old:
                    issues["ORPHAN_EVENT"] += 1
                    continue
                if event.get("event_type") == "SETTLED" and event.get("grade") not in FINALS:
                    issues["INVALID_SETTLEMENT"] += 1
                    continue
                # If later source events contradict frozen grade, flag
                # rather than silently replacing the first settlement.
                if old.get("grade") in FINALS and event.get("event_type") == "SETTLED":
                    if old["grade"] != event.get("grade"):
                        issues["CONFLICTING_SETTLEMENT"] += 1
                        continue
                entries[key] = {**old, **event}
            except (ValueError, TypeError, json.JSONDecodeError):
                issues["MALFORMED_JSON"] += 1
    return entries, {
        "status": "READY" if not issues else "WARN",
        "issues": dict(sorted(issues.items())),
    }


def event_start(row: dict, lane: str) -> datetime | None:
    if lane == "PARLAYS":
        legs = row.get("legs") or []
        if not isinstance(legs, list) or not legs:
            return None
        leg_starts = [
            iso_time(
                leg.get("source_event_start")
                or leg.get("event_start")
                or leg.get("start")
            ) if isinstance(leg, dict) else None
            for leg in legs
        ]
        # Earliest leg is NOT a completed multi-leg parlay.
        return max(leg_starts) if all(leg_starts) else None
    return iso_time(row.get("event_start"))


def summarize(rows: list[dict], lane: str, now_utc: datetime) -> dict:
    counts = Counter()
    counts["entries"] = len(rows)
    ages = []
    sport_games = set()
    for row in rows:
        if row.get("game_key"):
            sport_games.add(str(row["game_key"]))
        grade = str(row.get("grade") or "").upper()
        if grade in FINALS:
            counts["settled"] += 1
            counts[grade.lower()] += 1
            continue
        counts["pending"] += 1
        start = event_start(row, lane)
        if start is None:
            counts["pending_missing_verified_start"] += 1
        elif start + timedelta(hours=OVERDUE_HOURS) <= now_utc:
            counts["pending_overdue_12h"] += 1
            ages.append((now_utc - start).total_seconds() / 3600)
            if start + timedelta(hours=48) <= now_utc:
                counts["pending_overdue_48h"] += 1
        else:
            counts["pending_future_or_grace"] += 1
    return {
        "entries": counts["entries"],
        "settled": counts["settled"],
        "wins": counts["win"],
        "losses": counts["loss"],
        "pushes": counts["push"],
        "pending": counts["pending"],
        "pending_overdue_12h": counts["pending_overdue_12h"],
        "pending_overdue_48h": counts["pending_overdue_48h"],
        "pending_future_or_grace": counts["pending_future_or_grace"],
        "pending_missing_verified_start": counts["pending_missing_verified_start"],
        "unique_game_keys": len(sport_games),
        "max_unresolved_age_hours": round(max(ages), 1) if ages else None,
        "status": (
            "NO_FORWARD_ENTRIES" if not rows
            else "SETTLEMENT_BACKLOG" if counts["pending_overdue_12h"]
            else "AWAITING_RESULTS" if counts["pending"] else "SETTLED"
        ),
    }


def audit_forward_ledgers(root: Path, *, at: datetime | None = None) -> dict:
    at = at or datetime.now(timezone.utc)
    if at.tzinfo is None:
        raise ValueError("An offset-aware audit timestamp is required")
    at = at.astimezone(timezone.utc)
    ledger_dir = root / "intelligence_warehouse" / "betting_v2"
    lane_rows = {}
    errors = {}
    for lane, name in FILES.items():
        rows, state = canonical_ledger(ledger_dir / name)
        lane_rows[lane] = list(rows.values())
        if state["issues"]:
            errors[lane] = state["issues"]
    by_lane = {}
    for lane, rows in lane_rows.items():
        by_lane[lane] = {
            "summary": summarize(rows, lane, at),
            "by_sport": {
                sport: summarize(
                    [row for row in rows if row.get("sport") == sport],
                    lane, at,
                ) for sport in SPORTS
            },
        }
    by_sport = {}
    for sport in SPORTS:
        by_sport[sport] = {
            lane: by_lane[lane]["by_sport"][sport] for lane in FILES
        }
    # Counts are from distinct proof families, not an assertion these are
    # unique bets or independent, actually placed wagers.
    total_overdue = sum(
        by_lane[lane]["summary"]["pending_overdue_12h"] for lane in FILES
    )
    return {
        "generated_at": at.isoformat(),
        "status": "DATA_INTEGRITY_REVIEW" if errors
                  else "SETTLEMENT_BACKLOG" if total_overdue else "READY",
        "mode": "FORWARD_ACCOUNTABILITY_ONLY",
        "sports": list(SPORTS),
        "by_lane": by_lane,
        "by_sport": by_sport,
        "integrity_issues": errors,
        "summary": {
            "pending_overdue_12h": total_overdue,
            "pending_overdue_48h": sum(
                by_lane[lane]["summary"]["pending_overdue_48h"]
                for lane in FILES
            ),
            "tracked": sum(
                by_lane[lane]["summary"]["entries"] for lane in FILES
            ),
            "settled": sum(
                by_lane[lane]["summary"]["settled"] for lane in FILES
            ),
        },
        "rules": {
            "no_unverified_settlements": True,
            "pending_is_not_loss": True,
            "parlay_overdue_after_last_confirmed_leg_start_only": True,
            "auto_model_promotion": False,
            "overdue_grace_hours": OVERDUE_HOURS,
            "cross_family_counts_not_unique_wagers": True,
        },
    }
