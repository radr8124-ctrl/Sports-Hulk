#!/usr/bin/env python3
import csv
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STASH = ROOT / "intelligence_warehouse/fantasy_decisions/FANTASY_IR_STASH_CURRENT.csv"
SKILL_POSITIONS = {"QB", "RB", "WR", "TE", "K"}
LIKELY_PLATFORM_IR_STATUSES = {"IR", "PUP"}
POSSIBLE_PLATFORM_IR_STATUSES = {"OUT", "DOUBTFUL"}

def norm(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r"\b(jr|sr|ii|iii|iv)\.?\b", " ", text)
    return re.sub(r"[^a-z0-9]+", "", text)

def num(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None

def read_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))

def raw_name(item):
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get("name") or item.get("player") or ""
    return ""

def status_capacity_class(status):
    value = str(status or "").upper()
    if value in LIKELY_PLATFORM_IR_STATUSES:
        return "LIKELY_IR_DESIGNATION_PLATFORM_RULES_APPLY"
    if value in POSSIBLE_PLATFORM_IR_STATUSES:
        return "POSSIBLE_IR_ELIGIBILITY_PLATFORM_RULES_APPLY"
    if value == "QUESTIONABLE":
        return "QUESTIONABLE_NOT_ASSUMED_IR_ELIGIBLE"
    return "IR_ELIGIBILITY_UNKNOWN"

def roster_action(row, research_index=None):
    status = str(row.get("status") or "").upper()
    score = num(row.get("stash_research_score")) or 0.0
    disagreement = str(row.get("source_disagreement") or "").lower() in {"true", "1", "yes"}

    if disagreement:
        return "REVIEW_SOURCE_CONFLICT"
    if status in LIKELY_PLATFORM_IR_STATUSES and score > 0:
        return "IR_STASH_RESEARCH"
    if status in POSSIBLE_PLATFORM_IR_STATUSES and score > 0:
        return "HOLD_RESEARCH_IF_ELIGIBLE"
    if status == "QUESTIONABLE" and score > 0:
        return "BENCH_HOLD_RESEARCH"
    if research_index is not None and research_index >= 60:
        return "HOLD_VALUE_HIGH_STASH_SIGNAL_WEAK"
    return "LOW_PRIORITY_STASH_RESEARCH"

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"status":"ERROR","error":"Invalid JSON input"}))
        return 2

    roster = payload.get("roster") or []
    analysis = payload.get("roster_analysis") or {}
    ir_slots = int(max(0, min(20, round(num(payload.get("ir_slots")) or 0))))

    if not isinstance(roster, list) or not roster:
        print(json.dumps({"status":"ERROR","error":"roster must be a non-empty list"}))
        return 2

    analysis_by_name = {}
    for row in analysis.get("players") or []:
        key = norm(row.get("player"))
        if key:
            analysis_by_name[key] = row
    for row in analysis.get("recognized_without_decision") or []:
        key = norm(row.get("player"))
        if key and key not in analysis_by_name:
            analysis_by_name[key] = row

    nfl_rows = []
    by_name = {}
    for row in read_rows(STASH):
        if str(row.get("sport") or "").upper() != "NFL":
            continue
        nfl_rows.append(row)
        key = norm(row.get("player"))
        if not key:
            continue
        current = by_name.get(key)
        if current is None:
            by_name[key] = row
            continue
        current_score = num(current.get("stash_research_score")) or -9999
        candidate_score = num(row.get("stash_research_score")) or -9999
        current_sources = int(num(current.get("source_count")) or 0)
        candidate_sources = int(num(row.get("source_count")) or 0)
        if (candidate_sources, candidate_score) > (current_sources, current_score):
            by_name[key] = row

    roster_names = {norm(raw_name(item)) for item in roster if norm(raw_name(item))}
    roster_injured = []

    for item in roster:
        name = raw_name(item)
        key = norm(name)
        stash = by_name.get(key)
        if not stash:
            continue

        analysis_row = analysis_by_name.get(key) or {}
        research_index = num(analysis_row.get("research_index"))
        score = num(stash.get("stash_research_score"))
        disagreement = str(stash.get("source_disagreement") or "").lower() in {"true", "1", "yes"}

        roster_injured.append({
            "player": stash.get("player") or name,
            "player_key": stash.get("player_key") or analysis_row.get("player_key"),
            "team": stash.get("team") or analysis_row.get("team"),
            "position": stash.get("position") or analysis_row.get("position"),
            "status": stash.get("status"),
            "injury_type": stash.get("injury_type"),
            "return_window": stash.get("return_window"),
            "return_date": stash.get("return_date"),
            "source_count": int(num(stash.get("source_count")) or 0),
            "source_disagreement": disagreement,
            "role_signal": stash.get("role_signal") or analysis_row.get("role_signal"),
            "stash_research_score": score,
            "stash_tier": stash.get("stash_tier"),
            "roster_research_index": research_index,
            "ir_capacity_class": status_capacity_class(stash.get("status")),
            "roster_action_research": roster_action(stash, research_index),
            "platform_ir_eligibility_verified": False,
            "return_date_is_guarantee": False,
        })

    roster_injured.sort(
        key=lambda row: (
            1 if row["source_disagreement"] else 0,
            -(row["stash_research_score"] if row["stash_research_score"] is not None else -9999),
            -(row["roster_research_index"] if row["roster_research_index"] is not None else -9999),
        )
    )

    likely_capacity_candidates = [
        row for row in roster_injured
        if str(row.get("status") or "").upper() in LIKELY_PLATFORM_IR_STATUSES
    ]
    possible_capacity_candidates = [
        row for row in roster_injured
        if str(row.get("status") or "").upper() in POSSIBLE_PLATFORM_IR_STATUSES
    ]

    outside = []
    for row in nfl_rows:
        player = str(row.get("player") or "").strip()
        if not player or norm(player) in roster_names:
            continue
        position = str(row.get("position") or "").upper()
        if position not in SKILL_POSITIONS:
            continue

        status = str(row.get("status") or "").upper()
        if status not in {"IR", "PUP", "OUT"}:
            continue

        score = num(row.get("stash_research_score"))
        if score is None or score <= 0:
            continue

        disagreement = str(row.get("source_disagreement") or "").lower() in {"true", "1", "yes"}
        outside.append({
            "player": player,
            "player_key": row.get("player_key"),
            "team": row.get("team"),
            "position": position,
            "status": status,
            "injury_type": row.get("injury_type"),
            "return_window": row.get("return_window"),
            "return_date": row.get("return_date"),
            "source_count": int(num(row.get("source_count")) or 0),
            "source_disagreement": disagreement,
            "role_signal": row.get("role_signal"),
            "stash_research_score": score,
            "stash_tier": row.get("stash_tier"),
            "ir_capacity_class": status_capacity_class(status),
            "user_league_availability_verified": False,
            "platform_ir_eligibility_verified": False,
            "return_date_is_guarantee": False,
        })

    outside.sort(
        key=lambda row: (
            1 if row["source_disagreement"] else 0,
            -row["stash_research_score"],
            -row["source_count"],
        )
    )
    outside_targets = [row for row in outside if not row["source_disagreement"]][:6]
    outside_conflicts = [row for row in outside if row["source_disagreement"]][:4]

    result = {
        "status": "READY",
        "sport": "NFL",
        "personalization_level": "ROSTER_AWARE_IR_STASH_RESEARCH",
        "ir_slots_saved": ir_slots,
        "platform_ir_eligibility_verified": False,
        "league_availability_verified": False,
        "roster_injured_count": len(roster_injured),
        "likely_ir_designation_count": len(likely_capacity_candidates),
        "possible_ir_eligibility_count": len(possible_capacity_candidates),
        "ir_capacity": {
            "saved_ir_slots": ir_slots,
            "likely_ir_designation_count": len(likely_capacity_candidates),
            "possible_ir_eligibility_count": len(possible_capacity_candidates),
            "likely_open_slots": max(0, ir_slots - len(likely_capacity_candidates)),
            "likely_overflow_count": max(0, len(likely_capacity_candidates) - ir_slots),
            "capacity_is_platform_eligibility_prediction": False,
        },
        "roster_injured": roster_injured,
        "outside_targets_to_check": outside_targets,
        "outside_source_conflicts": outside_conflicts,
        "note": "IR-slot counts are used for capacity planning only. Actual IR eligibility depends on the fantasy platform and league rules and is not verified here.",
        "outside_note": "Outside stash candidates are research names to check, not confirmed free agents in the user's league.",
    }

    print(json.dumps(result, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
