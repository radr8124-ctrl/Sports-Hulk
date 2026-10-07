#!/usr/bin/env python3
"""Attach explicit ESPN season type to NBA game decisions via exact event match.

Run AFTER build_nba_decision_brain.py; never infers season from date,
week, sportsbook labels or the NBA schedule. No model is promoted.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

import requests

try:
    from .espn_competition_regime import dates_to_query, fetch_scoreboard_events, label_decision
except ImportError:  # script execution from nba_live/decision
    from espn_competition_regime import dates_to_query, fetch_scoreboard_events, label_decision


def read_rows(path: Path) -> tuple[list[str], list[dict]]:
    if not path.is_file() or path.stat().st_size == 0:
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames or [], list(reader)


def write_rows(path: Path, fields: list[str], rows: list[dict]) -> None:
    for name in ("season_type", "competition_regime", "competition_regime_source", "espn_event_id"):
        if name not in fields:
            fields.append(name)
    with NamedTemporaryFile(
        "w", newline="", encoding="utf-8", dir=path.parent,
        prefix=".regime-", suffix=".tmp", delete=False,
    ) as out:
        temp = Path(out.name)
        writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def write_receipt(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=".regime-",
        suffix=".json.tmp", delete=False,
    ) as out:
        temp = Path(out.name)
        json.dump(report, out, indent=2)
        out.write("\n")
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def enrich(root: Path, session, dry_run: bool = False) -> dict:
    decision_dir = root / "nba_live" / "decision"
    files = [
        decision_dir / "NBA_GAME_DECISIONS.csv",
        decision_dir / "NBA_GAME_FINALISTS.csv",
    ]
    snapshots = {str(path): read_rows(path) for path in files}
    primary = snapshots[str(files[0])][1]
    all_rows = [row for _, rows in snapshots.values() for row in rows]
    requested_dates = dates_to_query(all_rows)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "ESPN_SITE_SCOREBOARD",
        "source_method": "EXPLICIT_SEASON_TYPE_EXACT_TEAM_AND_START_JOIN",
        "maximum_start_drift_seconds": 20 * 60,
        "status": "NO_GAME_DECISIONS" if not primary else "WAITING_FOR_SOURCE",
        "dry_run": dry_run,
        "proof_promotion_permitted": False,
        "dates": {}, "csv_files": {},
    }

    if not primary:
        return report

    events, receipt = fetch_scoreboard_events(requested_dates, session)
    report["dates"] = receipt
    receipt_path = decision_dir / "receipts" / "NBA_REGIME_SOURCE_RECEIPT.json"
    if not receipt["successful_dates"]:
        report["status"] = "SOURCE_UNAVAILABLE"
        if not dry_run:
            write_receipt(receipt_path, report)
        return report

    game_keys: set[str] = set()
    verified_games: set[str] = set()
    unknown_games: set[str] = set()
    for path in files:
        fields, rows = snapshots[str(path)]
        if not fields:
            report["csv_files"][path.name] = {"rows": 0, "status": "EMPTY"}
            continue
        revised = []
        reasons = Counter()
        for row in rows:
            labeled, reason = label_decision(row, events)
            revised.append(labeled)
            reasons[reason] += 1
            if path == files[0]:
                key = str(row.get("game_key") or "")
                game_keys.add(key)
                (verified_games if reason == "VERIFIED" else unknown_games).add(key)
        report["csv_files"][path.name] = {
            "rows": len(rows), "reason_counts": dict(sorted(reasons.items())),
            "status": "VALIDATED" if dry_run else "WRITTEN",
        }
        if not dry_run:
            write_rows(path, list(fields), revised)

    report["distinct_games"] = len(game_keys)
    report["verified_games"] = len(verified_games - unknown_games)
    report["unknown_games"] = len(unknown_games)
    report["status"] = (
        "PARTIAL_SOURCE" if receipt["failed_dates"] else "READY"
    )
    if not dry_run:
        write_receipt(receipt_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Sports HULK root; defaults to this script's repository",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = enrich(args.root, requests.Session(), dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    if result["status"] == "SOURCE_UNAVAILABLE":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
