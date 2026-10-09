"""Fail-closed NHL derived starting-goalie reconciliation.

The official per-goalie 'starter' field, not postgame time on ice, is the
source of truth. This tool never changes official goalie rows or predictions.
Default is audit-only; --apply repairs only derived team-history starter fields.
"""
import argparse
import csv
import hashlib
import json
import os
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GOALIE = ROOT / "nhl_live/history/NHL_GOALIE_GAME_HISTORY.csv"
TEAM = ROOT / "nhl_live/history/NHL_TEAM_GAME_HISTORY.csv"
PARQUET = TEAM.with_suffix(".parquet")
FIELDS = (
    "starting_goalie", "starting_goalie_id", "starting_goalie_save_pct",
    "starting_goalie_saves", "starting_goalie_shots_against",
)
RECEIPT = ROOT / "reports/NHL_HISTORICAL_GOALIE_STARTER_SOURCE_AUDIT_LATEST.json"


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            sha.update(block)
    return sha.hexdigest()


def csvrows(path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), reader.fieldnames


def canonical_nhl_player_id(value):
    """Normalize pandas' integer ID serialized as N.0, not arbitrary decimals."""
    value = str(value).strip()
    if value.endswith(".0"):
        value = value[:-2]
    return str(int(value)) if value.isdigit() else ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    before = {str(p.relative_to(ROOT)): digest(p) for p in (GOALIE, TEAM, PARQUET)}
    goalie, _ = csvrows(GOALIE)
    teams, columns = csvrows(TEAM)
    if not set(FIELDS).issubset(columns):
        raise ValueError("Team history has missing starter fields")
    goalie_by_block = defaultdict(list)
    for g in goalie:
        goalie_by_block[(g["event_id"], g["team"])].append(g)
    if len(teams) != len(goalie_by_block):
        raise ValueError("Team and goalie game-team blocks differ")
    corrections = []
    flags_by_key = {}
    for row in teams:
        key = (row["event_id"], row["team"])
        entries = goalie_by_block.get(key)
        if not entries:
            raise ValueError(f"Missing goalie source: {key}")
        flagged = [g for g in entries if g["starter"].strip().lower() == "true"]
        if len(flagged) > 1:
            raise ValueError(f"Conflicting source starter flags: {key}")
        flags_by_key[key] = bool(flagged)
        if flagged:
            official_id = canonical_nhl_player_id(flagged[0]["player_id"])
            derived_id = canonical_nhl_player_id(row["starting_goalie_id"])
            if not official_id or derived_id != official_id:
                raise ValueError(f"Historical verified starter mismatch: {key}")
        else:
            if any(row[field] for field in FIELDS):
                corrections.append((key, row["season"], row["game_type"]))
    if len({(r["event_id"], r["team"]) for r in teams}) != len(teams):
        raise ValueError("Duplicate team-game rows: cannot reconcile")
    season_type = Counter((season, typ) for _, season, typ in corrections)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "NHL_GAME_GOALIE_HISTORY_EXPLICIT_STARTER_BOOLEAN",
        "game_team_blocks": len(teams),
        "explicit_starter_blocks": sum(flags_by_key.values()),
        "without_flag_blocks": len(flags_by_key) - sum(flags_by_key.values()),
        "historical_false_starter_rows_to_clear": len(corrections),
        "false_rows_by_season_game_type": {
            f"{k[0]}/type{k[1]}": v for k, v in sorted(season_type.items())
        },
        "applied": False, "before_sha256": before,
    }
    if args.apply and corrections:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = ROOT / ".deploy_backups" / f"nhl_starter_derived_reconcile_{stamp}"
        backup.mkdir(parents=True, exist_ok=False)
        for p in (GOALIE, TEAM, PARQUET):
            shutil.copy2(p, backup / p.name)
        if any(digest(p) != before[str(p.relative_to(ROOT))] for p in (GOALIE, TEAM, PARQUET)):
            raise RuntimeError("Concurrent writer changed source before apply")
        corrected_keys = {key for key, _, _ in corrections}
        for row in teams:
            if (row["event_id"], row["team"]) in corrected_keys:
                for field in FIELDS:
                    row[field] = ""
        temp_csv = TEAM.with_name(TEAM.stem + ".starter-verified.tmp.csv")
        temp_parquet = PARQUET.with_name(PARQUET.stem + ".starter-verified.tmp.parquet")
        try:
            with temp_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=columns)
                writer.writeheader()
                writer.writerows(teams)
                handle.flush()
                os.fsync(handle.fileno())
            frame = pd.read_parquet(PARQUET)
            if len(frame) != len(teams):
                raise ValueError("Parquet team row count differs")
            keys = pd.Series(list(zip(frame["event_id"].astype(str), frame["team"].astype(str))))
            if len(set(keys)) != len(keys) or set(keys) != set(flags_by_key):
                raise ValueError("Parquet team keys differ from original game-team source")
            mask = keys.isin(corrected_keys)
            if int(mask.sum()) != len(corrected_keys):
                raise ValueError("Parquet correction count differs")
            for field in FIELDS:
                frame.loc[mask.to_numpy(), field] = None
            frame.to_parquet(temp_parquet, index=False)
            verify_rows, _ = csvrows(temp_csv)
            if len(verify_rows) != len(teams):
                raise ValueError("Invalid CSV output")
            for row in verify_rows:
                key = (row["event_id"], row["team"])
                if key in corrected_keys and any(row[field] for field in FIELDS):
                    raise ValueError("Unverified starter not cleared")
            if any(digest(p) != before[str(p.relative_to(ROOT))] for p in (GOALIE, TEAM, PARQUET)):
                raise RuntimeError("Concurrent writer changed source during apply")
            try:
                os.replace(temp_csv, TEAM)
                os.replace(temp_parquet, PARQUET)
            except Exception:
                shutil.copy2(backup / TEAM.name, TEAM)
                shutil.copy2(backup / PARQUET.name, PARQUET)
                raise
        finally:
            temp_csv.unlink(missing_ok=True)
            temp_parquet.unlink(missing_ok=True)
        if digest(GOALIE) != before[str(GOALIE.relative_to(ROOT))]:
            raise ValueError("Official goalie source altered")
        report["applied"] = True
        report["backup_path"] = str(backup)
        report["corrected_csv_parquet_rows"] = len(corrections)
    report["after_sha256"] = {
        str(p.relative_to(ROOT)): digest(p) for p in (GOALIE, TEAM, PARQUET)
    }
    if args.apply:
        RECEIPT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
