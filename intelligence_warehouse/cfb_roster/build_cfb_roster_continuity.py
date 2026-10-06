#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import json
import re
import time

import pandas as pd
import requests

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "intelligence_warehouse" / "cfb_roster"
RAW = OUT / "raw"
TEAM_CONTEXT = ROOT / "cfb_live" / "decision" / "CFB_TEAM_CONTEXT.csv"
TEAM_OUT = OUT / "CFB_ROSTER_CONTINUITY_CURRENT.csv"
POS_OUT = OUT / "CFB_POSITION_CONTINUITY_CURRENT.csv"
PLAYER_OUT = OUT / "CFB_ROSTER_PLAYERS_CURRENT.csv"
TRANSFER_OUT = OUT / "CFB_FBS_TRANSFER_INS_CURRENT.csv"
RECEIPT = OUT / "CFB_ROSTER_CONTINUITY_RECEIPT.json"

CURRENT_SEASON = 2026
PRIOR_SEASON = 2025
NOW = datetime.now(timezone.utc)
ap = argparse.ArgumentParser()
ap.add_argument("--force", action="store_true")
args = ap.parse_args()

OUT.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Sports-HULK/1.0 roster-continuity research",
    "Accept": "application/json",
}

def cache_age_hours(path: Path):
    if not path.exists():
        return None
    return (time.time() - path.stat().st_mtime) / 3600.0

def cached_json(url: str, path: Path, ttl_hours: float):
    age = cache_age_hours(path)
    if path.exists() and not args.force and age is not None and age < ttl_hours:
        return json.loads(path.read_text()), "CACHE"
    response = requests.get(url, headers=HEADERS, timeout=8)
    response.raise_for_status()
    data = response.json()
    path.write_text(json.dumps(data, separators=(",", ":")))
    return data, "LIVE"

def athlete_ids(payload):
    out = set()
    for item in payload.get("items", []) if isinstance(payload, dict) else []:
        ref = item.get("$ref", "") if isinstance(item, dict) else str(item)
        match = re.search(r"/athletes/(\d+)", ref)
        if match:
            out.add(match.group(1))
    return out

def position_group(position):
    pos = str(position or "").upper().strip()
    if pos == "QB":
        return "QB"
    if pos in {"RB", "FB"}:
        return "RB"
    if pos in {"WR", "TE"}:
        return "PASS_CATCHER"
    if pos in {"OT", "OG", "C", "OL", "G", "T"}:
        return "OL"
    if pos in {"DE", "DT", "DL", "NT"}:
        return "DL"
    if pos in {"LB", "ILB", "OLB"}:
        return "LB"
    if pos in {"CB", "S", "DB", "FS", "SS"}:
        return "DB"
    if pos in {"K", "P", "LS"}:
        return "SPECIAL_TEAMS"
    return "OTHER"

def roster_rows(payload, team_id, team, team_name):
    rows = []
    for group in payload.get("athletes", []) if isinstance(payload, dict) else []:
        group_name = group.get("position", "") or group.get("name", "")
        for athlete in group.get("items", []):
            aid = str(athlete.get("id") or "").strip()
            if not aid:
                continue
            position = (athlete.get("position") or {}).get("abbreviation", "")
            rows.append({
                "athlete_id": aid,
                "player": athlete.get("fullName") or athlete.get("displayName") or "",
                "team_id": int(team_id),
                "team": team,
                "team_name": team_name,
                "position": position,
                "position_group": position_group(position),
                "roster_group": group_name,
                "jersey": athlete.get("jersey"),
                "experience": (athlete.get("experience") or {}).get("displayValue"),
            })
    return rows

def group_parent_id(group_id):
    gid = str(group_id or "").strip()
    if not gid:
        return None
    url = (
        "https://sports.core.api.espn.com/v2/sports/football/leagues/"
        f"college-football/seasons/{CURRENT_SEASON}/types/2/groups/{gid}"
    )
    data, _ = cached_json(url, RAW / f"group_{CURRENT_SEASON}_{gid}.json", 168)
    ref = ((data.get("parent") or {}).get("$ref") or "")
    match = re.search(r"/groups/(\d+)", ref)
    return match.group(1) if match else None

def reaches_fbs(group_id):
    seen = set()
    gid = str(group_id or "").strip()
    for _ in range(6):
        if not gid or gid in seen:
            return False
        if gid == "80":
            return True
        if gid == "81":
            return False
        seen.add(gid)
        gid = group_parent_id(gid)
    return False

def team_meta_task(row):
    tid = int(row.team_id)
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/{tid}"
    data, source = cached_json(url, RAW / f"team_{tid}.json", 168)
    team = data.get("team", {})
    groups = team.get("groups") or {}
    parent = (groups.get("parent") or {}).get("id")
    return tid, {
        "team_id": tid,
        "team": row.team,
        "team_name": row.team_name,
        "conference_group_id": groups.get("id"),
        "division_parent_id": parent,
        "is_fbs": None,
        "source": source,
    }

def membership_task(season, team):
    tid = int(team["team_id"])
    url = (
        "https://sports.core.api.espn.com/v2/sports/football/leagues/"
        f"college-football/seasons/{season}/teams/{tid}/athletes?limit=250"
    )
    ttl = 720 if season == PRIOR_SEASON else 12
    data, source = cached_json(url, RAW / f"athletes_{season}_{tid}.json", ttl)
    return season, tid, athlete_ids(data), source, int(data.get("count") or 0)

def roster_task(team):
    tid = int(team["team_id"])
    url = (
        "https://site.api.espn.com/apis/site/v2/sports/football/"
        f"college-football/teams/{tid}/roster?season={CURRENT_SEASON}"
    )
    data, source = cached_json(url, RAW / f"roster_{CURRENT_SEASON}_{tid}.json", 12)
    rows = roster_rows(data, tid, team["team"], team["team_name"])
    return tid, rows, source

if not TEAM_CONTEXT.exists():
    raise SystemExit(f"missing team context: {TEAM_CONTEXT}")

teams_frame = pd.read_csv(TEAM_CONTEXT)
teams_frame = teams_frame[["team_id", "team", "team_name"]].drop_duplicates("team_id")
errors = []
team_meta = {}

with ThreadPoolExecutor(max_workers=24) as pool:
    futures = {pool.submit(team_meta_task, row): int(row.team_id) for row in teams_frame.itertuples()}
    for future in as_completed(futures):
        tid = futures[future]
        try:
            key, value = future.result()
            team_meta[key] = value
        except Exception as exc:
            errors.append({"stage": "team_meta", "team_id": tid, "error": repr(exc)})

for value in team_meta.values():
    try:
        value["is_fbs"] = reaches_fbs(value.get("conference_group_id"))
    except Exception as exc:
        value["is_fbs"] = False
        errors.append({
            "stage": "group_hierarchy",
            "team_id": value["team_id"],
            "error": repr(exc),
        })

fbs_teams = sorted(
    [value for value in team_meta.values() if value.get("is_fbs")],
    key=lambda x: x["team_name"],
)

prior_sets = {}
current_sets = {}
membership_sources = {}
membership_counts = {}

with ThreadPoolExecutor(max_workers=32) as pool:
    futures = {}
    for team in fbs_teams:
        for season in (PRIOR_SEASON, CURRENT_SEASON):
            future = pool.submit(membership_task, season, team)
            futures[future] = (season, int(team["team_id"]))
    for future in as_completed(futures):
        season, tid = futures[future]
        try:
            got_season, got_tid, ids, source, count = future.result()
            target = prior_sets if got_season == PRIOR_SEASON else current_sets
            target[got_tid] = ids
            membership_sources[(got_season, got_tid)] = source
            membership_counts[(got_season, got_tid)] = count
        except Exception as exc:
            errors.append({
                "stage": "membership",
                "season": season,
                "team_id": tid,
                "error": repr(exc),
            })

roster_detail = {}
roster_sources = {}

with ThreadPoolExecutor(max_workers=24) as pool:
    futures = {pool.submit(roster_task, team): int(team["team_id"]) for team in fbs_teams}
    for future in as_completed(futures):
        tid = futures[future]
        try:
            got_tid, rows, source = future.result()
            roster_detail[got_tid] = rows
            roster_sources[got_tid] = source
        except Exception as exc:
            errors.append({"stage": "current_roster", "team_id": tid, "error": repr(exc)})

prior_owner = {}
current_owner = {}
for tid, ids in prior_sets.items():
    for aid in ids:
        prior_owner.setdefault(aid, set()).add(tid)
for tid, ids in current_sets.items():
    for aid in ids:
        current_owner.setdefault(aid, set()).add(tid)

team_name_by_id = {int(t["team_id"]): t["team_name"] for t in fbs_teams}
team_abbr_by_id = {int(t["team_id"]): t["team"] for t in fbs_teams}
all_prior_ids = set(prior_owner)
all_current_ids = set(current_owner)

player_rows = []
transfer_rows = []

for team in fbs_teams:
    tid = int(team["team_id"])
    current_ids = current_sets.get(tid, set())
    prior_ids = prior_sets.get(tid, set())
    seen = set()
    for row in roster_detail.get(tid, []):
        aid = row["athlete_id"]
        if aid in seen:
            continue
        seen.add(aid)
        returning = aid in prior_ids
        prior_other = sorted(prior_owner.get(aid, set()) - {tid})
        transfer_in = (not returning) and bool(prior_other)
        row["returning_same_team"] = returning
        row["fbs_transfer_in"] = transfer_in
        row["prior_fbs_team_ids"] = "|".join(str(x) for x in prior_other)
        row["prior_fbs_teams"] = "|".join(team_abbr_by_id.get(x, str(x)) for x in prior_other)
        player_rows.append(row)
        if transfer_in:
            transfer_rows.append(row.copy())
players = pd.DataFrame(player_rows)
transfers = pd.DataFrame(transfer_rows)

team_rows = []
for team in fbs_teams:
    tid = int(team["team_id"])
    current_ids = current_sets.get(tid, set())
    prior_ids = prior_sets.get(tid, set())
    returning = current_ids & prior_ids
    transfer_in_ids = {
        aid for aid in current_ids
        if not (aid in prior_ids) and bool(prior_owner.get(aid, set()) - {tid})
    }
    transfer_out_ids = {
        aid for aid in prior_ids
        if not (aid in current_ids) and bool(current_owner.get(aid, set()) - {tid})
    }
    current_count = len(current_ids)
    prior_count = len(prior_ids)
    detail_count = len({
        row["athlete_id"] for row in roster_detail.get(tid, [])
    })
    team_rows.append({
        "team_id": tid,
        "team": team["team"],
        "team_name": team["team_name"],
        "prior_roster_members": prior_count,
        "current_roster_members": current_count,
        "returning_same_team": len(returning),
        "returning_share_current": round(len(returning) / current_count, 4) if current_count else None,
        "retained_share_prior": round(len(returning) / prior_count, 4) if prior_count else None,
        "fbs_transfer_ins": len(transfer_in_ids),
        "fbs_transfer_in_share_current": round(len(transfer_in_ids) / current_count, 4) if current_count else None,
        "fbs_transfer_outs": len(transfer_out_ids),
        "current_not_seen_on_prior_fbs_roster": len(current_ids - all_prior_ids),
        "prior_not_seen_on_current_fbs_roster": len(prior_ids - all_current_ids),
        "position_detail_players": detail_count,
        "position_detail_coverage": round(detail_count / current_count, 4) if current_count else None,
        "prior_membership_source": membership_sources.get((PRIOR_SEASON, tid), "ERROR"),
        "current_membership_source": membership_sources.get((CURRENT_SEASON, tid), "ERROR"),
        "current_roster_detail_source": roster_sources.get(tid, "ERROR"),
    })

summary = pd.DataFrame(team_rows)

if not summary.empty:
    valid = summary["returning_share_current"].dropna()
    q25 = float(valid.quantile(0.25)) if len(valid) else None
    q75 = float(valid.quantile(0.75)) if len(valid) else None
    summary["continuity_percentile"] = (
        summary["returning_share_current"].rank(pct=True, method="average") * 100
    ).round(1)
    def signal(value):
        if pd.isna(value) or q25 is None or q75 is None:
            return "LIMITED_SAMPLE"
        if value >= q75:
            return "HIGH_CONTINUITY"
        if value <= q25:
            return "LOW_CONTINUITY"
        return "MIDDLE_CONTINUITY"
    summary["continuity_signal"] = summary["returning_share_current"].apply(signal)
else:
    q25 = q75 = None
position_rows = []
if not players.empty:
    for (tid, team, team_name, group), frame in players.groupby(
        ["team_id", "team", "team_name", "position_group"], dropna=False
    ):
        count = len(frame)
        returning_count = int(frame["returning_same_team"].fillna(False).sum())
        transfer_count = int(frame["fbs_transfer_in"].fillna(False).sum())
        position_rows.append({
            "team_id": int(tid),
            "team": team,
            "team_name": team_name,
            "position_group": group,
            "players_in_detail_sample": count,
            "returning_same_team": returning_count,
            "returning_share_sample": round(returning_count / count, 4) if count else None,
            "fbs_transfer_ins_sample": transfer_count,
            "fbs_transfer_in_share_sample": round(transfer_count / count, 4) if count else None,
        })

positions = pd.DataFrame(position_rows)

generated_at = datetime.now(timezone.utc).isoformat()
for frame in (summary, positions, players, transfers):
    if not frame.empty:
        frame["generated_at"] = generated_at
        frame["score_is_probability"] = False
        frame["automatic_model_adjustment"] = False

summary.to_csv(TEAM_OUT, index=False)
positions.to_csv(POS_OUT, index=False)
players.to_csv(PLAYER_OUT, index=False)
transfers.to_csv(TRANSFER_OUT, index=False)
receipt = {
    "generated_at": generated_at,
    "prior_season": PRIOR_SEASON,
    "current_season": CURRENT_SEASON,
    "fbs_teams": len(fbs_teams),
    "team_summary_rows": len(summary),
    "position_rows": len(positions),
    "current_player_detail_rows": len(players),
    "fbs_transfer_in_player_rows": len(transfers),
    "prior_membership_unique_players": len(all_prior_ids),
    "current_membership_unique_players": len(all_current_ids),
    "continuity_signal_counts": summary["continuity_signal"].value_counts().to_dict() if not summary.empty else {},
    "returning_share_q25": q25,
    "returning_share_q75": q75,
    "mean_position_detail_coverage": round(float(summary["position_detail_coverage"].mean()), 4) if not summary.empty else None,
    "team_meta_http_errors": sum(1 for e in errors if e["stage"] == "team_meta"),
    "membership_http_errors": sum(1 for e in errors if e["stage"] == "membership"),
    "roster_detail_http_errors": sum(1 for e in errors if e["stage"] == "current_roster"),
    "errors": errors[:50],
    "fbs_to_fbs_transfer_detection_only": True,
    "production_weighted_continuity_available": False,
    "returning_production_not_inferred": True,
    "score_is_probability": False,
    "automatic_model_adjustment": False,
    "paid_provider_required": False,
}

RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True))
print("FBS TEAMS:", len(fbs_teams))
print("TEAM CONTINUITY:", len(summary))
print("POSITION CONTINUITY:", len(positions))
print("PLAYER DETAIL:", len(players))
print("FBS TRANSFER INS:", len(transfers))
print("SIGNALS:", receipt["continuity_signal_counts"])
print("ERRORS:", len(errors))
print("RESULT: CFB_ROSTER_CONTINUITY_READY")
