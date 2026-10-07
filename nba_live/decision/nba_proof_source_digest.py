"""Stable fingerprint for NBA graded GAME evidence (excludes parlay claims).

Normalizes ESPN season codes 1, 1.0, and PRESEASON to the same proof
regime. Input order and routine CSV rewrites do not change this digest.
"""
from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path

try:
    from .nba_result_reconciliation import explicit_type
except ImportError:
    from nba_result_reconciliation import explicit_type

FIELDS = (
    "recommendation_key", "snapshot_at", "game_key", "start",
    "market", "selection", "side", "line", "grade",
    "season_type", "score", "payload_json",
)


def digest_rows(rows: list[dict]) -> str:
    frozen = []
    for row in rows:
        if str(row.get("lane") or "").strip().upper() != "GAME":
            continue
        values = [
            explicit_type(row.get(k)) if k == "season_type"
            else str(row.get(k) or "").strip()
            for k in FIELDS
        ]
        frozen.append(values)
    frozen.sort()
    serialized = json.dumps(frozen, separators=(",", ":"), ensure_ascii=False)
    return sha256(serialized.encode("utf-8")).hexdigest()


def digest_csv(path: Path) -> str | None:
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return digest_rows(list(csv.DictReader(f)))
