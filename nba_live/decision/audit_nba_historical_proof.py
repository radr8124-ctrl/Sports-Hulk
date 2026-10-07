#!/usr/bin/env python3
"""Audit NBA historical results and Betting V2 proof freshness.

Read-only input. The output is a descriptive receipt, never a performance
promotion, a wager recommendation, or a rewrite of historical ledgers.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

try:
    from .nba_result_reconciliation import explicit_type
    from .nba_proof_source_digest import digest_csv
except ImportError:
    from nba_result_reconciliation import explicit_type
    from nba_proof_source_digest import digest_csv


ROOT = Path(__file__).resolve().parents[2]
GRADED = ROOT / "nba_live/decision/history/NBA_GRADED_RECOMMENDATIONS.csv"
VALIDATION = ROOT / "intelligence_warehouse/betting_v2/BETTING_V2_ALL_MARKETS_VALIDATION.json"
RECEIPT = ROOT / "nba_live/decision/history/NBA_PROOF_INTEGRITY_RECEIPT.json"
REGIME = {"1": "PRESEASON", "2": "REGULAR", "3": "POSTSEASON"}
SETTLED = {"WIN", "LOSS", "PUSH"}


def parse_time(value: object) -> datetime | None:
    try:
        t = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        return t.astimezone(timezone.utc) if t.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


def summarize(rows: list[dict], *, graded_mtime: datetime | None = None,
              validation: dict | None = None, source_digest: str | None = None) -> dict:
    validation = validation or {}
    proof_generated = parse_time(validation.get("generated_at"))
    games = [r for r in rows if str(r.get("lane") or "").upper() == "GAME"]
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in games:
        market = str(row.get("market") or "").strip().upper()
        regime = REGIME.get(explicit_type(row.get("season_type")), "UNKNOWN")
        grouped[(market, regime)].append(row)

    by_cohort = {}
    total_conflicts = 0
    for (market, regime), group in sorted(grouped.items()):
        counts = Counter(str(r.get("grade") or "").upper() for r in group)
        conflicts = sum(
            str(r.get("grade") or "").upper() == "REVIEW_SOURCE_CONFLICT"
            for r in group
        )
        total_conflicts += conflicts
        pregame = sum(
            (parse_time(r.get("snapshot_at")) is not None)
            and (parse_time(r.get("start")) is not None)
            and (parse_time(r.get("snapshot_at")) < parse_time(r.get("start")))
            for r in group
        )
        names = {str(r.get("game_key") or "") for r in group}
        by_cohort[f"NBA_{market}|{regime}"] = {
            "observations": len(group),
            "unique_game_blocks": len(names - {""}),
            "win": counts["WIN"], "loss": counts["LOSS"],
            "push": counts["PUSH"],
            "pending_or_review": len(group) - sum(counts[v] for v in SETTLED),
            "conflicting_source_results": conflicts,
            "pregame_snapshot_rows": pregame,
            # This observed rate does NOT attest to independent profit,
            # calibrated probabilities, or a strategy valid for promotion.
            "observed_hit_rate_pct": (
                round(100 * counts["WIN"] / (counts["WIN"] + counts["LOSS"]), 2)
                if counts["WIN"] + counts["LOSS"] else None
            ),
            "eligible_for_model_promotion": False,
        }

    reported_lanes = validation.get("lanes") or {}
    proof_lanes = {}
    for key, value in reported_lanes.items():
        if str(key).startswith("NBA_") and isinstance(value, dict):
            proof_lanes[key] = {
                "history_n": value.get("history_n"),
                "status": value.get("status"),
                "competition_regime": value.get("competition_regime"),
            }
    proof_digest = (validation.get("source_fingerprints") or {}).get(
        "nba_game_grades_sha256"
    )
    # Hash beats modification time: the NBA grader can re-export unchanged
    # evidence every ten minutes without invalidating an hourly proof build.
    if source_digest is not None and proof_digest is not None:
        stale = source_digest != proof_digest
        freshness_method = "CANONICAL_GAME_SHA256"
    else:
        stale = (
            graded_mtime is not None and
            (proof_generated is None or proof_generated < graded_mtime)
        )
        freshness_method = "LEGACY_MODIFICATION_TIME_FALLBACK"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "STALE_BETTING_PROOF" if stale else (
            "NO_PROOF_TIMESTAMP" if proof_generated is None else "AUDITED"
        ),
        "automatic_promotion_permitted": False,
        "excludes_parlay_claims": True,
        "graded_game_observations": len(games),
        "graded_non_game_observations": len(rows) - len(games),
        "unique_graded_game_keys": len({
            str(r.get("game_key") or "") for r in games if r.get("game_key")
        }),
        "conflicting_result_observations": total_conflicts,
        "graded_source_modified_at": (
            graded_mtime.isoformat() if graded_mtime is not None else None
        ),
        "betting_proof_generated_at": (
            proof_generated.isoformat() if proof_generated is not None else None
        ),
        "betting_proof_stale": stale,
        "freshness_method": freshness_method,
        "graded_game_evidence_sha256": source_digest,
        "validated_game_evidence_sha256": proof_digest,
        "cohorts": by_cohort,
        "betting_validation_nba_lanes": proof_lanes,
        "rules": {
            "regime_source": "EXPLICIT_GRADED_OFFICIAL_SEASON_TYPE",
            "unknown_never_reassigned_from_calendar": True,
            "unsettled_not_a_loss": True,
            "raw_observed_hit_rate_not_model_edge": True,
            "ledger_rewrites_permitted": False,
        },
    }


def run(graded: Path, validation: Path) -> dict:
    if not graded.exists():
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "MISSING_GRADED_HISTORY",
            "automatic_promotion_permitted": False,
        }
    with graded.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    doc = {}
    if validation.exists():
        try:
            doc = json.loads(validation.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            doc = {}
    mtime = datetime.fromtimestamp(graded.stat().st_mtime, timezone.utc)
    return summarize(
        rows, graded_mtime=mtime, validation=doc,
        source_digest=digest_csv(graded),
    )


def atomic_receipt(path: Path, result: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w", dir=path.parent, encoding="utf-8", delete=False,
        prefix=".nba-proof-audit-", suffix=".tmp"
    ) as f:
        temp = Path(f.name)
        json.dump(result, f, indent=2)
        f.write("\n")
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graded", type=Path, default=GRADED)
    parser.add_argument("--validation", type=Path, default=VALIDATION)
    parser.add_argument("--output", type=Path, default=RECEIPT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run(args.graded, args.validation)
    if not args.dry_run:
        atomic_receipt(args.output, result)
    print(json.dumps(result, indent=2))
    return 1 if result["status"] == "MISSING_GRADED_HISTORY" else 0


if __name__ == "__main__":
    raise SystemExit(main())
