#!/usr/bin/env python3
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEEKLY = ROOT / "intelligence_warehouse/fantasy_decisions/FANTASY_WEEKLY_DECISIONS_CURRENT.csv"
DEFENSE = ROOT / "intelligence_warehouse/fantasy_decisions/FANTASY_DEFENSE_STREAMING_CURRENT.csv"
MASTER = ROOT / "nfl_live/player_context/derived/NFL_PLAYER_CONTEXT_MASTER_V2.csv"
TEAM_ALIASES = ROOT / "nfl_live/identity/team_aliases.json"

SKILL_POSITIONS = {"QB", "RB", "WR", "TE"}

def norm(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = text.replace("&", " and ")
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

def index_band(score):
    if score is None:
        return "NO_SCORE"
    if score >= 85:
        return "ELITE_RESEARCH"
    if score >= 75:
        return "STRONG_RESEARCH"
    if score >= 60:
        return "ABOVE_AVERAGE_RESEARCH"
    if score >= 45:
        return "MIXED_RESEARCH"
    if score >= 30:
        return "THIN_RESEARCH"
    return "HIGH_RISK_RESEARCH"

def player_record(row):
    weekly = num(row.get("weekly_research_score"))
    ros = num(row.get("ros_research_score"))
    combined = None if weekly is None or ros is None else round(0.45 * weekly + 0.55 * ros, 1)
    return {
        "player": row.get("player"),
        "player_key": row.get("player_key"),
        "team": row.get("team"),
        "position": row.get("position"),
        "opponent": row.get("opponent"),
        "availability_status": row.get("availability_status") or None,
        "role_signal": row.get("role_signal") or None,
        "weekly_research_score": weekly,
        "weekly_tier": row.get("weekly_tier") or None,
        "ros_research_score": ros,
        "ros_tier": row.get("ros_tier") or None,
        "research_index": combined,
        "research_band": index_band(combined),
        "research_reasons": row.get("research_reasons") or None,
        "score_is_probability": False,
        "source_lane": "WEEKLY_DECISIONS",
    }

def defense_record(row):
    weekly = num(row.get("weekly_stream_score"))
    multiweek = num(row.get("multiweek_hold_score"))
    combined = None if weekly is None or multiweek is None else round(0.60 * weekly + 0.40 * multiweek, 1)
    return {
        "player": row.get("dst_player") or f'{row.get("team")} D/ST',
        "player_key": f'dst:{row.get("team")}',
        "team": row.get("team"),
        "position": "DST",
        "opponent": row.get("next_opponent"),
        "availability_status": None,
        "role_signal": row.get("future_schedule_signal") or None,
        "weekly_research_score": weekly,
        "weekly_tier": row.get("weekly_stream_tier") or None,
        "ros_research_score": multiweek,
        "ros_tier": row.get("multiweek_hold_tier") or None,
        "research_index": combined,
        "research_band": index_band(combined),
        "research_reasons": "Defense streaming + multi-week hold research.",
        "score_is_probability": False,
        "source_lane": "DEFENSE_STREAMING",
    }

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"status": "ERROR", "error": "Invalid JSON input"}))
        return 2

    roster = payload.get("roster") or []
    if not isinstance(roster, list) or not roster:
        print(json.dumps({"status": "ERROR", "error": "roster must be a non-empty list"}))
        return 2
    if len(roster) > 60:
        print(json.dumps({"status": "ERROR", "error": "roster exceeds 60 entries"}))
        return 2

    weekly_rows = read_rows(WEEKLY)
    by_name = defaultdict(list)
    by_key = defaultdict(list)

    for row in weekly_rows:
        if (row.get("position") or "").upper() not in SKILL_POSITIONS:
            continue
        by_name[norm(row.get("player"))].append(row)
        by_key[norm(row.get("player_key"))].append(row)

    master_names = defaultdict(list)
    if MASTER.exists():
        for row in read_rows(MASTER):
            name = row.get("player_name_stats")
            if not name:
                continue
            master_names[norm(name)].append({
                "player": name,
                "team": row.get("latest_team") or row.get("sleeper_team") or None,
                "position": row.get("position_stats") or row.get("sleeper_position") or None,
                "player_key": row.get("player_key") or None,
                "availability_status": row.get("availability_flag") or None,
            })

    defense_by_team = {}
    if DEFENSE.exists():
        for row in read_rows(DEFENSE):
            abbr = str(row.get("team") or "").upper()
            if abbr:
                defense_by_team[abbr] = row

    alias_candidates = defaultdict(set)
    if TEAM_ALIASES.exists():
        aliases = json.loads(TEAM_ALIASES.read_text())
        for abbr, values in aliases.items():
            for value in [abbr, *(values or [])]:
                alias_candidates[norm(value)].add(abbr)
            full_names = [str(value) for value in (values or []) if " " in str(value)]
            for full in full_names:
                alias_candidates[norm(full.split()[-1])].add(abbr)
    team_alias = {
        alias: next(iter(abbrs))
        for alias, abbrs in alias_candidates.items()
        if alias and len(abbrs) == 1
    }

    matched = []
    recognized_without_decision = []
    unmatched = []
    ambiguous = []

    for raw in roster:
        if isinstance(raw, str):
            item = {"name": raw}
        elif isinstance(raw, dict):
            item = raw
        else:
            unmatched.append({"input": str(raw), "reason": "INVALID_ENTRY"})
            continue

        name = str(item.get("name") or item.get("player") or "").strip()
        team_hint = str(item.get("team") or "").strip().upper()
        position_hint = str(item.get("position") or "").strip().upper()
        key = norm(name)

        if not key:
            unmatched.append({"input": name, "reason": "EMPTY_NAME"})
            continue

        defense_requested = (
            position_hint in {"DST", "D/ST", "DEF", "DEFENSE"}
            or bool(re.search(r"(?i)\b(d\s*/?\s*st|dst|defense)\b", name))
        )
        if defense_requested:
            cleaned_team = re.sub(r"(?i)\b(d\s*/?\s*st|dst|defense)\b", " ", name).strip()
            defense_abbr = team_alias.get(norm(cleaned_team))
            if not defense_abbr and team_hint:
                defense_abbr = team_alias.get(norm(team_hint)) or team_hint
            defense_row = defense_by_team.get(str(defense_abbr or "").upper())
            if defense_row:
                rec = defense_record(defense_row)
                rec["input_name"] = name
                matched.append(rec)
            else:
                unmatched.append({"input": name, "reason": "DEFENSE_NOT_FOUND"})
            continue

        candidates = list(by_name.get(key, []))
        if not candidates:
            candidates = list(by_key.get(key, []))

        if len(candidates) > 1 and team_hint:
            filtered = [r for r in candidates if str(r.get("team") or "").upper() == team_hint]
            if filtered:
                candidates = filtered
        if len(candidates) > 1 and position_hint:
            filtered = [r for r in candidates if str(r.get("position") or "").upper() == position_hint]
            if filtered:
                candidates = filtered

        if len(candidates) == 1:
            rec = player_record(candidates[0])
            rec["input_name"] = name
            matched.append(rec)
            continue
        if len(candidates) > 1:
            ambiguous.append({
                "input": name,
                "candidates": [
                    {"player": r.get("player"), "team": r.get("team"), "position": r.get("position")}
                    for r in candidates[:6]
                ],
            })
            continue

        master = list(master_names.get(key, []))
        if len(master) > 1 and team_hint:
            filtered = [r for r in master if str(r.get("team") or "").upper() == team_hint]
            if filtered:
                master = filtered
        if len(master) > 1 and position_hint:
            filtered = [r for r in master if str(r.get("position") or "").upper() == position_hint]
            if filtered:
                master = filtered

        if len(master) == 1:
            rec = dict(master[0])
            rec.update({
                "input_name": name,
                "research_index": None,
                "research_band": "NO_CURRENT_FANTASY_DECISION",
                "score_is_probability": False,
            })
            recognized_without_decision.append(rec)
        elif len(master) > 1:
            ambiguous.append({"input": name, "candidates": master[:6]})
        else:
            unmatched.append({"input": name, "reason": "PLAYER_NOT_FOUND"})

    scored = [r for r in matched if r.get("research_index") is not None]
    decision_coverage_pct = round(100 * len(matched) / len(roster), 1)
    overall = None
    if len(scored) >= 4 and decision_coverage_pct >= 60:
        overall = round(sum(r["research_index"] for r in scored) / len(scored), 1)

    position_summary = []
    for pos in ["QB", "RB", "WR", "TE", "DST"]:
        rows = [r for r in scored if r.get("position") == pos]
        if not rows:
            continue
        position_summary.append({
            "position": pos,
            "count": len(rows),
            "research_index": round(sum(r["research_index"] for r in rows) / len(rows), 1),
            "weekly_average": round(sum(r["weekly_research_score"] for r in rows) / len(rows), 1),
            "ros_average": round(sum(r["ros_research_score"] for r in rows) / len(rows), 1),
        })

    sorted_scored = sorted(scored, key=lambda r: r["research_index"], reverse=True)
    risk_rows = sorted(
        [r for r in scored if r["research_index"] < 60 or r.get("availability_status") not in (None, "", "AVAILABLE")],
        key=lambda r: r["research_index"],
    )[:3]

    result = {
        "status": "READY",
        "sport": "NFL",
        "roster_size": len(roster),
        "matched_count": len(matched),
        "recognized_without_decision_count": len(recognized_without_decision),
        "ambiguous_count": len(ambiguous),
        "unmatched_count": len(unmatched),
        "coverage_pct": round(100 * (len(matched) + len(recognized_without_decision)) / len(roster), 1),
        "decision_coverage_pct": decision_coverage_pct,
        "roster_research_index": overall,
        "roster_research_band": index_band(overall),
        "score_is_probability": False,
        "index_note": "Position-adjusted Sports Zenith research index. It is not a win probability, projected fantasy score, or league-specific team grade.",
        "personalization_note": "League scoring and starter-slot settings are not yet applied in this quick roster scan.",
        "position_summary": position_summary,
        "strengths": sorted_scored[:3],
        "risks": risk_rows,
        "players": matched,
        "recognized_without_decision": recognized_without_decision,
        "ambiguous": ambiguous,
        "unmatched": unmatched,
    }

    print(json.dumps(result, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
