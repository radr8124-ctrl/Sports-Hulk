#!/usr/bin/env python3
"""Refresh only recent official MLB status/score rows in the historical master.

Preserve every gamePk and all historical columns; never replace a finalized
box with stale Scheduled status. This runs after the live StatsAPI collector.
No wagers, grade history, player stats, or model predictions are modified.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import unicodedata
import re

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "baseball_vault/derived/MLB_GAME_MASTER.csv"
PARQUET = ROOT / "baseball_vault/derived/MLB_GAME_MASTER.parquet"
RECEIPT = ROOT / "baseball_vault/derived/MLB_MASTER_FRESHNESS_RECEIPT.json"
SCHEDULE = "https://statsapi.mlb.com/api/v1/schedule"
FINAL = {"Final", "Game Over"}
LIVE = {"In Progress", "Manager Challenge", "Delayed", "Warmup"}


def clean(value):
    folded = unicodedata.normalize("NFKD", str(value or ""))
    return re.sub(r"[^a-z0-9]", "", folded.encode("ascii", "ignore").decode("ascii").lower())


def id_value(value):
    try:
        if pd.isna(value):
            return ""
        x = str(value).strip()
        if re.fullmatch(r"[0-9]+(?:\.0)?", x):
            return x[:-2] if x.endswith(".0") else x
    except (ValueError, TypeError):
        pass
    return ""


def official_score(value):
    try:
        if value is None:
            return None
        val = float(value)
        if math.isfinite(val) and val >= 0 and val.is_integer():
            return int(val)
    except (TypeError, ValueError):
        pass
    return None


def parse_datetime(value):
    try:
        d = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (TypeError, ValueError):
        return None


def parse_schedule(data):
    if not isinstance(data, dict) or not isinstance(data.get("dates"), list):
        raise ValueError("Invalid official schedule")
    by_id = {}
    conflicting = set()
    for day in data["dates"]:
        for g in day.get("games", []):
            gamepk = id_value(g.get("gamePk"))
            teams = g.get("teams") or {}
            away = (teams.get("away") or {}).get("team") or {}
            home = (teams.get("home") or {}).get("team") or {}
            row = {
                "gamePk": gamepk,
                "officialDate": str(g.get("officialDate") or day.get("date") or ""),
                "gameDate": str(g.get("gameDate") or ""),
                "gameType": str(g.get("gameType") or ""),
                "status": str((g.get("status") or {}).get("detailedState") or ""),
                "away_team": str(away.get("name") or ""),
                "away_team_id": id_value(away.get("id")),
                "home_team": str(home.get("name") or ""),
                "home_team_id": id_value(home.get("id")),
                "away_score": official_score((teams.get("away") or {}).get("score")),
                "home_score": official_score((teams.get("home") or {}).get("score")),
                "gameNumber": id_value(g.get("gameNumber")),
            }
            if not gamepk or not row["gameDate"] or not row["away_team"] or not row["home_team"]:
                continue
            if gamepk in by_id and by_id[gamepk] != row:
                conflicting.add(gamepk)
            else:
                by_id[gamepk] = row
    for gamepk in conflicting:
        by_id.pop(gamepk, None)
    return by_id, conflicting


def update_frame(master, official):
    """Return new frame + immutable result summary; no file I/O."""
    required = {
        "gamePk", "gameDate", "officialDate", "gameType", "status",
        "away_team", "away_team_id", "home_team", "home_team_id",
        "away_score", "home_score", "total_runs", "home_run_margin",
    }
    missing = sorted(required - set(master.columns))
    if missing or master.gamePk.isna().any() or master.gamePk.duplicated().any():
        raise ValueError("Master missing columns or contains duplicate official game IDs: " + str(missing))

    latest = master.copy(deep=True)
    game_positions = {id_value(pk): idx for idx, pk in enumerate(latest["gamePk"])}
    changes = []
    review = []
    unknown = []
    for gamepk, new in official.items():
        if gamepk not in game_positions:
            unknown.append(gamepk)
            continue
        rowi = game_positions[gamepk]
        old = latest.loc[rowi]
        if (
            clean(old["away_team"]) != clean(new["away_team"])
            or clean(old["home_team"]) != clean(new["home_team"])
            or id_value(old["away_team_id"]) != new["away_team_id"]
            or id_value(old["home_team_id"]) != new["home_team_id"]
            or str(old["gameType"]) != new["gameType"]
        ):
            review.append({"gamePk": gamepk, "reason": "OFFICIAL_GAME_TEAM_OR_TYPE_CONFLICT"})
            continue
        official_start, old_start = parse_datetime(new["gameDate"]), parse_datetime(old["gameDate"])
        if not official_start or not old_start or abs((official_start - old_start).total_seconds()) > 2 * 3600:
            review.append({"gamePk": gamepk, "reason": "KICKOFF_CHANGED_BEYOND_TWO_HOURS"})
            continue
        current = str(old.get("status") or "")
        status = new["status"]
        rank = {"Scheduled": 0, "Pre-Game": 1, "Warmup": 1,
                "Delayed": 1, "In Progress": 2, "Manager Challenge": 2,
                "Final": 3, "Game Over": 3}
        if current in rank and status in rank and rank[status] < rank[current]:
            review.append({"gamePk": gamepk, "reason": "ATTEMPTED_OFFICIAL_STATUS_DOWNGRADE"})
            continue
        if status in FINAL:
            if new["away_score"] is None or new["home_score"] is None:
                review.append({"gamePk": gamepk, "reason": "OFFICIAL_FINAL_MISSING_SCORES"})
                continue
            if current in FINAL:
                already = (official_score(old["away_score"]), official_score(old["home_score"]))
                desired = (new["away_score"], new["home_score"])
                if already != desired:
                    review.append({"gamePk": gamepk, "reason": "CONTRADICTORY_FINAL_SCORE"})
                    continue
        if status not in FINAL | LIVE | {"Scheduled", "Pre-Game"}:
            review.append({"gamePk": gamepk, "reason": "UNSUPPORTED_STATUS"})
            continue

        fields = {"status": status, "gameDate": new["gameDate"]}
        if status in FINAL | LIVE:
            for side in ("away", "home"):
                value = new[f"{side}_score"]
                if value is not None:
                    fields[f"{side}_score"] = value
            if new["away_score"] is not None and new["home_score"] is not None:
                fields["total_runs"] = new["away_score"] + new["home_score"]
                fields["home_run_margin"] = new["home_score"] - new["away_score"]

        modified = False
        for field, value in fields.items():
            old_value = old[field]
            numeric = field in {"away_score", "home_score", "total_runs", "home_run_margin"}
            if numeric:
                old_numeric = pd.to_numeric(old_value, errors="coerce")
                equivalent = (pd.isna(old_numeric) and value is None) or (
                    not pd.isna(old_numeric) and value is not None
                    and abs(float(old_numeric) - float(value)) < 1e-9
                )
            else:
                equivalent = (pd.isna(old_value) and value is None) or (
                    not pd.isna(old_value) and str(old_value) == str(value)
                )
            if not equivalent:
                latest.at[rowi, field] = value
                modified = True
        if modified:
            changes.append({"gamePk": gamepk, "before_status": current, "after_status": status})

    summary = {
        "updated_games": len(changes),
        "updated_game_ids": [x["gamePk"] for x in changes],
        "changes": changes,
        "held_for_review": review,
        "new_games_not_in_cached_master": unknown,
        "historical_row_count_preserved": len(latest) == len(master),
    }
    return latest, summary


def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", dir=path.parent, encoding="utf-8",
                            prefix=".mlb-master-receipt-", delete=False) as f:
        temp = Path(f.name)
        json.dump(payload, f, indent=2)
        f.write("\n")
    os.replace(temp, path)


def run(root=ROOT, session=None, days_back=8, days_forward=3, clock=None, dry_run=False):
    root = Path(root)
    clock = clock or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise ValueError("Need timezone-aware date")
    session = session or requests.Session()
    master = root / "baseball_vault/derived/MLB_GAME_MASTER.csv"
    parquet = root / "baseball_vault/derived/MLB_GAME_MASTER.parquet"
    receipt_file = root / "baseball_vault/derived/MLB_MASTER_FRESHNESS_RECEIPT.json"
    receipt = {
        "generated_at": clock.isoformat(), "status": "WAITING",
        "dry_run": dry_run, "source": "MLB_STATSAPI_OFFICIAL_SCHEDULE",
        "automatic_model_adjustment": False,
    }
    try:
        before = master.read_bytes()
        prior_hash = sha256(before).hexdigest()
        data = pd.read_csv(master, low_memory=False)
        start = clock.date() - timedelta(days=days_back)
        end = clock.date() + timedelta(days=days_forward)
        r = session.get(SCHEDULE, params={
            "sportId": 1, "startDate": start.isoformat(),
            "endDate": end.isoformat(), "hydrate": "team,linescore",
        }, timeout=20)
        r.raise_for_status()
        official, duplicates = parse_schedule(r.json())
        merged, result = update_frame(data, official)
        receipt.update({
            **result, "source_start": start.isoformat(),
            "source_end": end.isoformat(),
            "official_games_read": len(official),
            "duplicate_official_ids": sorted(duplicates),
            "master_sha256_before": prior_hash,
        })
        if not result["historical_row_count_preserved"] or duplicates:
            receipt["status"] = "INTEGRITY_HOLD"
        elif any(x["reason"] == "CONTRADICTORY_FINAL_SCORE" for x in result["held_for_review"]):
            receipt["status"] = "INTEGRITY_HOLD"
        elif sha256(master.read_bytes()).hexdigest() != prior_hash:
            receipt["status"] = "MASTER_CHANGED_DURING_REFRESH"
        elif not result["updated_games"]:
            receipt["status"] = "NO_UPDATES"
        elif dry_run:
            receipt["status"] = "DRY_RUN_READY"
        else:
            with NamedTemporaryFile("w", dir=master.parent, encoding="utf-8",
                                    newline="", prefix=".mlb-master-", suffix=".csv",
                                    delete=False) as f:
                csv_temp = Path(f.name)
                merged.to_csv(f, index=False)
            pq_temp = parquet.with_name("." + parquet.name + ".pending")
            try:
                merged.to_parquet(pq_temp, index=False)
                if sha256(master.read_bytes()).hexdigest() != prior_hash:
                    receipt["status"] = "MASTER_CHANGED_BEFORE_PUBLISH"
                else:
                    os.replace(pq_temp, parquet)
                    os.replace(csv_temp, master)
                    receipt["status"] = "UPDATED"
            finally:
                csv_temp.unlink(missing_ok=True)
                pq_temp.unlink(missing_ok=True)
    except (ValueError, KeyError, OSError, requests.exceptions.RequestException) as exc:
        receipt["status"] = "SOURCE_UNAVAILABLE_OR_INVALID"
        receipt["error_type"] = type(exc).__name__
    if not dry_run:
        atomic_json(receipt_file, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days-back", type=int, default=8)
    parser.add_argument("--days-forward", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    opts = parser.parse_args()
    if not 0 <= opts.days_back <= 30 or not 0 <= opts.days_forward <= 30:
        parser.error("Day windows must each be within 0-30 days")
    result = run(days_back=opts.days_back, days_forward=opts.days_forward,
                 dry_run=opts.dry_run)
    print(json.dumps(result, indent=2))
    if result["status"] in {"INTEGRITY_HOLD", "SOURCE_UNAVAILABLE_OR_INVALID", "MASTER_CHANGED_DURING_REFRESH", "MASTER_CHANGED_BEFORE_PUBLISH"}:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
