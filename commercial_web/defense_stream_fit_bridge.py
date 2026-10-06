#!/usr/bin/env python3
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFENSE = ROOT / "intelligence_warehouse/fantasy_decisions/FANTASY_DEFENSE_STREAMING_CURRENT.csv"

def num(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None

def read_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))

def rank_map(rows, field):
    ordered = sorted(
        [(str(row.get("team") or "").upper(), num(row.get(field))) for row in rows],
        key=lambda item: item[1] if item[1] is not None else -9999,
        reverse=True,
    )
    return {team: index + 1 for index, (team, _) in enumerate(ordered)}

def research_action(row, best_weekly_gap, best_multi_gap):
    weekly_tier = str(row.get("weekly_stream_tier") or "").upper()
    hold_tier = str(row.get("multiweek_hold_tier") or "").upper()
    weekly = num(row.get("weekly_stream_score")) or 0
    multi = num(row.get("multiweek_hold_score")) or 0

    if weekly_tier == "STRONG_STREAM" and hold_tier == "MULTI_WEEK_HOLD":
        return "HOLD_RESEARCH_STRONG"
    if weekly >= 60 and multi >= 55:
        return "HOLD_RESEARCH"
    if weekly_tier == "AVOID_STREAM" and best_weekly_gap >= 12:
        return "COMPARE_STREAMERS_RESEARCH"
    if hold_tier == "ROTATE_OUT" and best_multi_gap >= 10:
        return "COMPARE_ROTATION_RESEARCH"
    if weekly_tier == "MATCHUP_DEPENDENT":
        return "MATCHUP_COMPARE_RESEARCH"
    return "HOLD_OR_COMPARE_RESEARCH"

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"status":"ERROR","error":"Invalid JSON input"}))
        return 2

    analysis = payload.get("roster_analysis") or {}
    players = analysis.get("players") or []
    saved = [
        row for row in players
        if str(row.get("position") or "").upper() == "DST"
    ]

    rows = read_rows(DEFENSE)
    by_team = {str(row.get("team") or "").upper(): row for row in rows}
    weekly_ranks = rank_map(rows, "weekly_stream_score")
    multi_ranks = rank_map(rows, "multiweek_hold_score")

    saved_teams = {str(row.get("team") or "").upper() for row in saved if row.get("team")}
    alternatives = [
        row for row in rows
        if str(row.get("team") or "").upper() not in saved_teams
    ]
    alternatives.sort(
        key=lambda row: (
            num(row.get("weekly_stream_score")) or -9999,
            num(row.get("multiweek_hold_score")) or -9999,
        ),
        reverse=True,
    )

    top_weekly = alternatives[0] if alternatives else None
    top_multi = max(
        alternatives,
        key=lambda row: num(row.get("multiweek_hold_score")) or -9999,
        default=None,
    )

    saved_out = []
    for player in saved:
        team = str(player.get("team") or "").upper()
        row = by_team.get(team)
        if not row:
            saved_out.append({
                "player": player.get("player"),
                "team": team or None,
                "status": "NO_CURRENT_DEFENSE_STREAMING_ROW",
            })
            continue

        weekly = num(row.get("weekly_stream_score"))
        multi = num(row.get("multiweek_hold_score"))
        best_weekly = num(top_weekly.get("weekly_stream_score")) if top_weekly else None
        best_multi = num(top_multi.get("multiweek_hold_score")) if top_multi else None
        weekly_gap = round(max(0.0, (best_weekly or 0) - (weekly or 0)), 1)
        multi_gap = round(max(0.0, (best_multi or 0) - (multi or 0)), 1)

        saved_out.append({
            "player": row.get("dst_player") or player.get("player"),
            "team": team,
            "next_opponent": row.get("next_opponent"),
            "next_side": row.get("next_side"),
            "rest_days": num(row.get("rest_days")),
            "fatigue_load_score": num(row.get("fatigue_load_score")),
            "future_schedule_signal": row.get("future_schedule_signal"),
            "next_opponents": row.get("next_opponents"),
            "weekly_stream_score": weekly,
            "weekly_stream_tier": row.get("weekly_stream_tier"),
            "weekly_rank": weekly_ranks.get(team),
            "multiweek_hold_score": multi,
            "multiweek_hold_tier": row.get("multiweek_hold_tier"),
            "multiweek_rank": multi_ranks.get(team),
            "market_data_available": str(row.get("market_data_available") or "").lower() in {"true","1","yes"},
            "market_activity_signal": row.get("market_activity_signal"),
            "adds_24h": num(row.get("adds_24h")),
            "drops_24h": num(row.get("drops_24h")),
            "best_outside_weekly_gap": weekly_gap,
            "best_outside_multiweek_gap": multi_gap,
            "research_action": research_action(row, weekly_gap, multi_gap),
            "user_league_availability_verified": False,
            "drop_recommendation": False,
            "score_is_probability": False,
        })

    candidate_rows = []
    for row in alternatives[:8]:
        team = str(row.get("team") or "").upper()
        candidate_rows.append({
            "player": row.get("dst_player") or f"{team} D/ST",
            "team": team,
            "next_opponent": row.get("next_opponent"),
            "next_side": row.get("next_side"),
            "rest_days": num(row.get("rest_days")),
            "future_schedule_signal": row.get("future_schedule_signal"),
            "weekly_stream_score": num(row.get("weekly_stream_score")),
            "weekly_stream_tier": row.get("weekly_stream_tier"),
            "weekly_rank": weekly_ranks.get(team),
            "multiweek_hold_score": num(row.get("multiweek_hold_score")),
            "multiweek_hold_tier": row.get("multiweek_hold_tier"),
            "multiweek_rank": multi_ranks.get(team),
            "market_data_available": str(row.get("market_data_available") or "").lower() in {"true","1","yes"},
            "market_activity_signal": row.get("market_activity_signal"),
            "user_league_availability_verified": False,
            "score_is_probability": False,
        })

    result = {
        "status": "READY",
        "sport": "NFL",
        "personalization_level": "ROSTER_AWARE_DEFENSE_STREAMING_RESEARCH",
        "saved_defense_count": len(saved_out),
        "saved_defenses": saved_out,
        "alternatives_to_check": candidate_rows,
        "league_availability_verified": False,
        "market_data_is_league_availability": False,
        "drop_recommendation_generated": False,
        "note": "Saved D/ST is compared against league-wide defense-streaming research. Outside defenses are candidates to check, not confirmed available defenses in the user's league.",
        "market_note": "Market add/drop context is generic research and does not prove a defense is available in the user's league.",
    }

    print(json.dumps(result, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
