#!/usr/bin/env python3
import csv
import json
import math
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDP = ROOT / "intelligence_warehouse/fantasy_decisions/FANTASY_IDP_OPPORTUNITY_CURRENT.csv"
GROUPS = ("DL", "LB", "DB")
UNAVAILABLE = {"OUT", "IR", "INACTIVE", "DOUBTFUL"}

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

def boolish(value):
    return str(value or "").strip().lower() in {"true", "1", "yes"}

def read_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))

def roster_item(raw):
    if isinstance(raw, str):
        return {"name": raw, "team": "", "position": ""}
    if isinstance(raw, dict):
        return {
            "name": raw.get("name") or raw.get("player") or "",
            "team": raw.get("team") or "",
            "position": raw.get("position") or "",
        }
    return {"name": "", "team": "", "position": ""}

def active_for_slot(status):
    return str(status or "").upper() not in UNAVAILABLE

def action_for(row):
    tier = str(row.get("idp_usage_tier") or "").upper()
    status = str(row.get("availability_status") or "").upper()
    if status in UNAVAILABLE:
        return "UNAVAILABLE_NO_START"
    if status == "QUESTIONABLE":
        if tier in {"IDP_CORE_USAGE", "IDP_STRONG_USAGE"}:
            return "STRONG_USAGE_INJURY_CAUTION"
        return "INJURY_CAUTION"
    if tier == "IDP_CORE_USAGE":
        return "CORE_USAGE_RESEARCH"
    if tier == "IDP_STRONG_USAGE":
        return "STRONG_USAGE_RESEARCH"
    if tier == "IDP_WATCH":
        return "WATCH_USAGE_RESEARCH"
    if tier == "INACTIVE_NO_START":
        return "INACTIVE_NO_START"
    return "DEEP_ONLY_RESEARCH"

def serialize(row):
    snap = num(row.get("snap_pct"))
    snap_change = num(row.get("snap_pct_change"))
    score = num(row.get("idp_usage_score"))
    return {
        "player": row.get("player"),
        "player_key": row.get("player_key"),
        "team": row.get("team"),
        "position": row.get("position"),
        "idp_group": row.get("idp_group"),
        "next_opponent": row.get("next_opponent"),
        "next_side": row.get("next_side"),
        "rest_days": num(row.get("rest_days")),
        "availability_status": row.get("availability_status") or "UNKNOWN",
        "injury_type": row.get("injury_type") or None,
        "snap_pct": round(snap * 100.0, 1) if snap is not None and snap <= 1 else snap,
        "snap_pct_change": round(snap_change * 100.0, 1) if snap_change is not None and abs(snap_change) <= 1 else snap_change,
        "role_signal": row.get("role_signal") or None,
        "idp_usage_score": score,
        "idp_usage_tier": row.get("idp_usage_tier"),
        "usage_action_research": action_for(row),
        "fantasy_points_projection_available": boolish(row.get("fantasy_points_projection_available")),
        "waiver_market_coverage_available": boolish(row.get("waiver_market_coverage_available")),
        "score_is_probability": False,
        "user_league_availability_verified": False,
    }

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"status": "ERROR", "error": "Invalid JSON input"}))
        return 2

    roster = payload.get("roster") or []
    slots = payload.get("idp_slots") or {}
    if not isinstance(roster, list) or not roster:
        print(json.dumps({"status": "ERROR", "error": "roster must be a non-empty list"}))
        return 2

    slot_counts = {
        "DL": max(0, min(12, int(round(num(slots.get("dl")) or 0)))),
        "LB": max(0, min(12, int(round(num(slots.get("lb")) or 0)))),
        "DB": max(0, min(12, int(round(num(slots.get("db")) or 0)))),
        "IDP_FLEX": max(0, min(12, int(round(num(slots.get("idp_flex")) or 0)))),
    }
    slot_aware = sum(slot_counts.values()) > 0

    rows = read_rows(IDP)
    by_name = defaultdict(list)
    for row in rows:
        key = norm(row.get("player"))
        if key:
            by_name[key].append(row)

    matched = []
    unmatched = []
    roster_names = set()

    for raw in roster:
        item = roster_item(raw)
        name = str(item["name"] or "").strip()
        key = norm(name)
        if not key:
            continue
        roster_names.add(key)
        candidates = list(by_name.get(key, []))
        if len(candidates) > 1 and item["team"]:
            team = str(item["team"]).upper()
            filtered = [row for row in candidates if str(row.get("team") or "").upper() == team]
            if filtered:
                candidates = filtered
        if len(candidates) > 1 and item["position"]:
            pos = str(item["position"]).upper()
            filtered = [row for row in candidates if str(row.get("position") or "").upper() == pos]
            if filtered:
                candidates = filtered
        if candidates:
            candidates.sort(
                key=lambda row: (
                    num(row.get("idp_usage_score")) or -9999,
                    num(row.get("snap_pct")) or -9999,
                ),
                reverse=True,
            )
            matched.append(serialize(candidates[0]))
        elif str(item["position"] or "").upper() in {"DL", "DE", "DT", "LB", "DB", "CB", "S"}:
            unmatched.append({"input": name, "reason": "IDP_PLAYER_NOT_FOUND"})

    matched.sort(key=lambda row: row["idp_usage_score"] if row["idp_usage_score"] is not None else -9999, reverse=True)

    used = set()
    starter_candidates = []
    open_slots = []

    def identity(row):
        return str(row.get("player_key") or row.get("player") or "")

    def eligible(group=None):
        pool = [
            row for row in matched
            if identity(row) not in used
            and active_for_slot(row.get("availability_status"))
            and (group is None or row.get("idp_group") == group)
        ]
        pool.sort(key=lambda row: row["idp_usage_score"] if row["idp_usage_score"] is not None else -9999, reverse=True)
        return pool

    if slot_aware:
        for group in GROUPS:
            for index in range(1, slot_counts[group] + 1):
                pool = eligible(group)
                if not pool:
                    open_slots.append({
                        "slot": group,
                        "slot_index": index,
                        "reason": "NO_ACTIVE_MATCHED_IDP_PLAYER",
                    })
                    continue
                row = dict(pool[0])
                used.add(identity(row))
                row.update({
                    "assigned_slot": group,
                    "slot_index": index,
                    "lineup_research_status": "STARTER_CANDIDATE",
                })
                starter_candidates.append(row)

        for index in range(1, slot_counts["IDP_FLEX"] + 1):
            pool = eligible()
            if not pool:
                open_slots.append({
                    "slot": "IDP_FLEX",
                    "slot_index": index,
                    "reason": "NO_ACTIVE_MATCHED_IDP_PLAYER",
                })
                continue
            row = dict(pool[0])
            used.add(identity(row))
            row.update({
                "assigned_slot": "IDP_FLEX",
                "slot_index": index,
                "lineup_research_status": "STARTER_CANDIDATE",
            })
            starter_candidates.append(row)

    bench_candidates = [
        {**row, "lineup_research_status": "BENCH_OR_DEPTH_CANDIDATE"}
        for row in matched
        if identity(row) not in used and active_for_slot(row.get("availability_status"))
    ]
    unavailable_roster = [
        {**row, "lineup_research_status": "UNAVAILABLE_OR_INJURY_BLOCK"}
        for row in matched
        if not active_for_slot(row.get("availability_status"))
    ]

    group_summary = []
    for group in GROUPS:
        group_rows = [row for row in matched if row.get("idp_group") == group]
        active_rows = [row for row in group_rows if active_for_slot(row.get("availability_status"))]
        group_summary.append({
            "idp_group": group,
            "saved_count": len(group_rows),
            "active_saved_count": len(active_rows),
            "saved_slot_count": slot_counts[group],
            "slot_shortfall": max(0, slot_counts[group] - len(active_rows)),
            "best_saved_usage_score": max(
                [row["idp_usage_score"] for row in active_rows if row["idp_usage_score"] is not None],
                default=None,
            ),
        })

    external_pool = []
    for row in rows:
        key = norm(row.get("player"))
        if not key or key in roster_names:
            continue
        status = str(row.get("availability_status") or "").upper()
        if status in UNAVAILABLE:
            continue
        item = serialize(row)
        if item["idp_usage_score"] is None:
            continue
        external_pool.append(item)

    external_pool.sort(key=lambda row: row["idp_usage_score"], reverse=True)
    targets = []
    seen = set()

    need_groups = [
        summary["idp_group"] for summary in group_summary
        if summary["slot_shortfall"] > 0
    ]
    for group in need_groups:
        for row in external_pool:
            if row["idp_group"] != group:
                continue
            key = identity(row)
            if key in seen:
                continue
            targets.append({
                **row,
                "target_reason": "SAVED_SLOT_SHORTFALL",
            })
            seen.add(key)
            if sum(1 for x in targets if x["idp_group"] == group) >= 2:
                break

    for row in external_pool:
        if len(targets) >= 8:
            break
        key = identity(row)
        if key in seen:
            continue
        targets.append({
            **row,
            "target_reason": "TOP_USAGE_RESEARCH_TO_CHECK",
        })
        seen.add(key)

    questionables = [
        row for row in targets
        if str(row.get("availability_status") or "").upper() == "QUESTIONABLE"
    ]

    result = {
        "status": "READY",
        "sport": "NFL",
        "personalization_level": "ROSTER_AWARE_IDP_USAGE_RESEARCH",
        "slot_aware": slot_aware,
        "idp_slots": slot_counts,
        "saved_idp_count": len(matched),
        "matched_idp": matched,
        "starter_candidates": starter_candidates,
        "bench_candidates": bench_candidates,
        "unavailable_roster": unavailable_roster,
        "open_slots": open_slots,
        "group_summary": group_summary,
        "outside_targets_to_check": targets,
        "availability_cautions": questionables,
        "unmatched_idp": unmatched,
        "fantasy_points_projection_available": False,
        "league_availability_verified": False,
        "market_availability_verified": False,
        "score_is_probability": False,
        "note": "IDP personalization uses snap share, snap change, role and current usage research. It is not a fantasy-points projection and does not apply custom tackle/sack/turnover scoring.",
        "outside_note": "Outside IDP names are research targets to check, not confirmed free agents in the user's league.",
    }

    print(json.dumps(result, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
