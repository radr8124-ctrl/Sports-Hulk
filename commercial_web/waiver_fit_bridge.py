#!/usr/bin/env python3
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAAB = ROOT / "intelligence_warehouse/fantasy_decisions/FANTASY_FAAB_RESEARCH_CURRENT.csv"
SKILL_POSITIONS = ["QB", "RB", "WR", "TE"]

def norm(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r"\b(jr|sr|ii|iii|iv)\.?\b", " ", text)
    return re.sub(r"[^a-z0-9]+", "", text)

def num(value):
    try:
        return float(value)
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

def need_tier(score):
    if score >= 65:
        return "HIGH_ROSTER_NEED_RESEARCH"
    if score >= 45:
        return "MODERATE_ROSTER_NEED_RESEARCH"
    if score >= 25:
        return "LOW_ROSTER_NEED_RESEARCH"
    return "DEPTH_LOOK_ONLY"

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"status":"ERROR","error":"Invalid JSON input"}))
        return 2

    roster = payload.get("roster") or []
    analysis = payload.get("roster_analysis") or {}
    if not isinstance(roster, list) or not roster:
        print(json.dumps({"status":"ERROR","error":"roster must be a non-empty list"}))
        return 2

    roster_names = {norm(raw_name(item)) for item in roster if norm(raw_name(item))}
    by_position = defaultdict(list)
    for row in analysis.get("players") or []:
        pos = str(row.get("position") or "").upper()
        idx = num(row.get("research_index"))
        if pos in SKILL_POSITIONS and idx is not None:
            by_position[pos].append(idx)

    needs = []
    need_scores = {}
    for pos in SKILL_POSITIONS:
        values = by_position.get(pos, [])
        if values:
            avg = round(sum(values) / len(values), 1)
            floor = round(min(values), 1)
            need = round(max(0.0, min(100.0, 100.0 - (0.7 * avg + 0.3 * floor))), 1)
        else:
            avg = None
            floor = None
            need = 100.0

        need_scores[pos] = need
        needs.append({
            "position": pos,
            "roster_count": len(values),
            "roster_average_research_index": avg,
            "roster_floor_research_index": floor,
            "roster_need_score": need,
            "roster_need_tier": need_tier(need),
            "starter_slot_context_used": False,
        })

    rows = []
    cautions = []
    for row in read_rows(FAAB):
        if str(row.get("sport") or "").upper() != "NFL":
            continue
        pos = str(row.get("position") or "").upper()
        if pos not in SKILL_POSITIONS:
            continue
        player = str(row.get("player") or "").strip()
        if not player or norm(player) in roster_names:
            continue

        waiver = num(row.get("waiver_research_score"))
        if waiver is None:
            continue
        availability = str(row.get("availability_status") or "").upper()
        if availability in {"OUT", "IR", "PUP", "DOUBTFUL"}:
            continue

        need = need_scores.get(pos, 50.0)
        fit = round(0.75 * waiver + 0.25 * need, 1)
        item = {
            "player": player,
            "player_key": row.get("player_key") or None,
            "team": row.get("team") or None,
            "position": pos,
            "availability_status": availability or "UNKNOWN",
            "role_signal": row.get("role_signal") or None,
            "market_activity_signal": row.get("market_activity_signal") or None,
            "waiver_research_score": waiver,
            "waiver_priority": row.get("waiver_priority") or None,
            "roster_need_score": need,
            "roster_need_tier": need_tier(need),
            "roster_fit_research_score": fit,
            "research_faab_low_pct": num(row.get("suggested_faab_low_pct")),
            "research_faab_high_pct": num(row.get("suggested_faab_high_pct")),
            "user_league_availability_verified": False,
            "faab_is_league_specific_bid": False,
            "score_is_probability": False,
        }
        if availability == "AVAILABLE":
            rows.append(item)
        else:
            cautions.append(item)

    rows.sort(key=lambda x: (x["roster_fit_research_score"], x["waiver_research_score"]), reverse=True)
    cautions.sort(key=lambda x: (x["roster_fit_research_score"], x["waiver_research_score"]), reverse=True)
    needs.sort(key=lambda x: x["roster_need_score"], reverse=True)

    focus_positions = {row["position"] for row in needs[:2]}
    focused = [row for row in rows if row["position"] in focus_positions][:8]
    if len(focused) < 8:
        used = {norm(row["player"]) for row in focused}
        focused.extend(row for row in rows if norm(row["player"]) not in used)
        focused = focused[:8]

    result = {
        "status": "READY",
        "sport": "NFL",
        "personalization_level": "ROSTER_AWARE_WAIVER_RESEARCH",
        "league_availability_status": "NOT_VERIFIED",
        "budget_context_status": "WAITING",
        "score_is_probability": False,
        "faab_is_league_specific_bid": False,
        "note": "Targets are roster-aware research candidates to check. Sports Zenith has not verified that these players are available in the user's league.",
        "faab_note": "FAAB percentages are generic research ranges from market/role signals, not a prediction of the winning bid in the user's league.",
        "position_needs": needs,
        "targets": focused,
        "availability_cautions": cautions[:5],
        "candidate_pool_count": len(rows),
    }
    print(json.dumps(result, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
