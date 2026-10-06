#!/usr/bin/env python3
import csv
import json
import math
import sys
import unicodedata
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "nfl_live/player_context/derived/NFL_PLAYER_CONTEXT_MASTER_V2.csv"
POSITIONS = {"QB", "RB", "WR", "TE"}
VALID_FORMATS = {"standard", "half_ppr", "ppr"}

def norm(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r"\b(jr|sr|ii|iii|iv)\.?\b", " ", text)
    return re.sub(r"[^a-z0-9]+", "", text)

def num(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else 0.0
    except (TypeError, ValueError):
        return 0.0

def read_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))

def baseline_points(row, reception_points):
    passing = (
        num(row.get("passing_yards_season_avg")) / 25.0
        + num(row.get("passing_tds_season_avg")) * 4.0
        - num(row.get("passing_interceptions_season_avg")) * 2.0
    )
    rushing = (
        num(row.get("rushing_yards_season_avg")) / 10.0
        + num(row.get("rushing_tds_season_avg")) * 6.0
    )
    receiving = (
        num(row.get("receiving_yards_season_avg")) / 10.0
        + num(row.get("receiving_tds_season_avg")) * 6.0
        + num(row.get("receptions_season_avg")) * reception_points
    )
    return round(passing + rushing + receiving, 2)

def percentile_map(rows, key):
    by_position = defaultdict(list)
    for row in rows:
        position = str(row.get("position_stats") or "").upper()
        if position in POSITIONS:
            by_position[position].append((row["player_key"], row[key]))

    result = {}
    for position, values in by_position.items():
        ordered = sorted(values, key=lambda item: item[1])
        count = len(ordered)
        if not count:
            continue

        index = 0
        while index < count:
            value = ordered[index][1]
            end = index
            while end + 1 < count and ordered[end + 1][1] == value:
                end += 1
            average_rank = ((index + 1) + (end + 1)) / 2.0
            percentile = round(average_rank / count * 100.0, 1)
            for pos in range(index, end + 1):
                result[(position, ordered[pos][0])] = percentile
            index = end + 1
    return result

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"status":"ERROR","error":"Invalid JSON input"}))
        return 2

    players = payload.get("players") or []
    scoring_format = str(payload.get("scoring_format") or "").lower().strip()

    if scoring_format not in VALID_FORMATS:
        print(json.dumps({"status":"ERROR","error":"scoring_format must be standard, half_ppr or ppr"}))
        return 2
    if not isinstance(players, list):
        print(json.dumps({"status":"ERROR","error":"players must be a list"}))
        return 2

    reception_points = {
        "standard": 0.0,
        "half_ppr": 0.5,
        "ppr": 1.0,
    }[scoring_format]

    master_rows = []
    by_key = {}
    by_name = defaultdict(list)

    for row in read_rows(MASTER):
        position = str(row.get("position_stats") or "").upper()
        player_key = str(row.get("player_key") or "").strip()
        player_name = str(row.get("player_name_stats") or "").strip()
        if position not in POSITIONS or not player_key:
            continue

        enriched = dict(row)
        enriched["standard_context_ppg"] = baseline_points(row, 0.0)
        enriched["half_ppr_context_ppg"] = baseline_points(row, 0.5)
        enriched["ppr_context_ppg"] = baseline_points(row, 1.0)
        master_rows.append(enriched)
        by_key[norm(player_key)] = enriched
        if player_name:
            by_name[norm(player_name)].append(enriched)

    selected_key = {
        "standard": "standard_context_ppg",
        "half_ppr": "half_ppr_context_ppg",
        "ppr": "ppr_context_ppg",
    }[scoring_format]

    pct = percentile_map(master_rows, selected_key)

    enriched_players = []
    missing = []

    for player in players:
        if not isinstance(player, dict):
            continue

        position = str(player.get("position") or "").upper()
        player_key = norm(player.get("player_key"))
        name_key = norm(player.get("player"))

        row = by_key.get(player_key) if player_key else None
        if row is None and name_key:
            candidates = by_name.get(name_key, [])
            if len(candidates) == 1:
                row = candidates[0]

        output = dict(player)
        if row is None or position not in POSITIONS:
            output.update({
                "format_context_available": False,
                "format_context_status": "NO_HISTORICAL_CONTEXT",
            })
            enriched_players.append(output)
            missing.append(player.get("player"))
            continue

        selected = row[selected_key]
        standard = row["standard_context_ppg"]
        half = row["half_ppr_context_ppg"]
        ppr = row["ppr_context_ppg"]
        receptions = round(num(row.get("receptions_season_avg")), 2)
        targets = round(num(row.get("targets_season_avg")), 2)

        output.update({
            "format_context_available": True,
            "format_context_status": "HISTORICAL_SEASON_AVERAGE",
            "format_context_scoring": scoring_format,
            "historical_format_points_per_game": selected,
            "historical_standard_points_per_game": standard,
            "historical_half_ppr_points_per_game": half,
            "historical_ppr_points_per_game": ppr,
            "historical_receptions_per_game": receptions,
            "historical_targets_per_game": targets,
            "format_reception_bonus_vs_standard": round(selected - standard, 2),
            "format_context_position_percentile": pct.get((position, row["player_key"])),
            "format_context_is_projection": False,
            "format_context_basis": "SEASON_AVERAGE_ACTUAL_PRODUCTION",
        })
        enriched_players.append(output)

    result = {
        "status": "READY",
        "scoring_format": scoring_format,
        "reception_points": reception_points,
        "players": enriched_players,
        "coverage": {
            "input_players": len(players),
            "context_available": sum(1 for row in enriched_players if row.get("format_context_available")),
            "missing": sum(1 for row in enriched_players if not row.get("format_context_available")),
        },
        "assumptions": {
            "passing_yards_per_point": 25,
            "passing_td_points": 4,
            "interception_points": -2,
            "rushing_yards_per_point": 10,
            "rushing_td_points": 6,
            "receiving_yards_per_point": 10,
            "receiving_td_points": 6,
            "reception_points": reception_points,
        },
        "is_projection": False,
        "note": "Historical season-average scoring context only. It is not a next-game fantasy projection and does not include every possible custom league scoring rule.",
        "missing_players": [name for name in missing if name],
    }

    print(json.dumps(result, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
