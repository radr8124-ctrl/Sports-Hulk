from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import tempfile

ROOT = Path("/home/ubuntu/sports-hulk")
ENTRIES_PATH = ROOT / "nfl_live" / "derived" / "SURVIVOR_ENTRIES.json"
AUDIT_PATH = ROOT / "nfl_live" / "derived" / "SURVIVOR_ENTRY_AUDIT.jsonl"

NFL_TEAMS = [
    "Arizona Cardinals", "Atlanta Falcons", "Baltimore Ravens", "Buffalo Bills",
    "Carolina Panthers", "Chicago Bears", "Cincinnati Bengals", "Cleveland Browns",
    "Dallas Cowboys", "Denver Broncos", "Detroit Lions", "Green Bay Packers",
    "Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars", "Kansas City Chiefs",
    "Las Vegas Raiders", "Los Angeles Chargers", "Los Angeles Rams", "Miami Dolphins",
    "Minnesota Vikings", "New England Patriots", "New Orleans Saints", "New York Giants",
    "New York Jets", "Philadelphia Eagles", "Pittsburgh Steelers", "San Francisco 49ers",
    "Seattle Seahawks", "Tampa Bay Buccaneers", "Tennessee Titans", "Washington Commanders",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state() -> dict:
    if not ENTRIES_PATH.exists():
        return {"active": None, "entries": {}}
    return json.loads(ENTRIES_PATH.read_text())


def _atomic_write(data: dict) -> None:
    ENTRIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix="SURVIVOR_ENTRIES.",
        suffix=".tmp",
        dir=str(ENTRIES_PATH.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_name, ENTRIES_PATH)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _burned_teams(entry: dict) -> set[str]:
    burned = set()
    for item in entry.get("history") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("result") or "").upper() in {"SURVIVED", "LOST", "WIN", "LOSS"}:
            team = str(item.get("team") or "").strip()
            if team:
                burned.add(team)
    for key, state in entry.items():
        if not str(key).startswith("week_") or not isinstance(state, dict):
            continue
        for pick in state.get("picks") or []:
            if not isinstance(pick, dict):
                continue
            if str(pick.get("result") or "").upper() in {"WIN", "LOSS"}:
                team = str(pick.get("team") or "").strip()
                if team:
                    burned.add(team)
    return burned


def _append_audit(payload: dict) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, separators=(",", ":")) + "\n")


def save_entry(
    entry_name: str,
    *,
    used_teams: list[str] | None = None,
    current_week: int | None = None,
    current_picks: list[str] | None = None,
    make_active: bool = False,
) -> dict:
    data = load_state()
    entries = data.setdefault("entries", {})

    if entry_name not in entries:
        raise ValueError(f"Unknown Survivor entry: {entry_name}")

    entry = entries[entry_name]
    now = _now()
    pool_week = int(data.get("pool_current_week") or entry.get("current_week") or 1)
    burned = _burned_teams(entry)

    if used_teams is not None:
        normalized_used = []
        for team in used_teams:
            team = str(team).strip()
            if team and team not in normalized_used:
                normalized_used.append(team)
        # Resolved historical teams are immutable. A manual edit can add
        # extra burned teams, but it can never make a resolved team reusable.
        for team in burned:
            if team not in normalized_used:
                normalized_used.append(team)
        entry["used_teams"] = normalized_used
        entry["manual_used_teams_updated_at"] = now

    if current_week is not None:
        week = int(current_week)
        if week != pool_week:
            raise ValueError(
                f"Survivor picks can only be edited for current pool week {pool_week}."
            )
        if (
            str(entry.get("status") or "").upper() == "ELIMINATED"
            and str(entry.get("reentry_status") or "").upper() != "ACTIVE_REENTRY"
        ):
            raise ValueError(
                "This entry is eliminated. A buyback/re-entry must be explicitly recorded before new picks can be saved."
            )
        entry["current_week"] = pool_week

        key = f"week_{week}"
        week_state = entry.get(key)
        if not isinstance(week_state, dict):
            week_state = {
                "required_picks": None,
                "rule_status": "AWAITING_OFFICIAL_POOL_SHEET",
                "entry_result": "OPEN",
            }

        if str(week_state.get("entry_result") or "").upper() in {"WIN", "LOSS"}:
            raise ValueError("A resolved Survivor week cannot be edited.")
        if any(
            str(item.get("result") or "").upper() in {"WIN", "LOSS"}
            for item in (week_state.get("picks") or [])
            if isinstance(item, dict)
        ):
            raise ValueError("A Survivor pick that has already settled cannot be changed.")

        if current_picks is not None:
            picks = []
            for team in current_picks:
                team = str(team).strip()
                if team and team not in picks:
                    picks.append(team)

            reused = [team for team in picks if team in burned]
            if reused:
                raise ValueError(
                    "Used Survivor team cannot be reused: " + ", ".join(reused)
                )

            required = week_state.get("required_picks")
            try:
                required = int(required) if required is not None else None
            except Exception:
                required = None
            if required and len(picks) > required:
                raise ValueError(
                    f"Week {week} requires {required} pick(s); too many were selected."
                )

            entry["current_picks"] = picks
            entry["current_pick"] = picks[0] if len(picks) == 1 else None
            if not picks:
                pick_status = "OPEN"
            elif required is None:
                pick_status = "RULE_UNCONFIRMED_SAVED"
            elif len(picks) < required:
                pick_status = "INCOMPLETE_SAVED"
            else:
                pick_status = "SAVED_NOT_SUBMITTED"
            entry["current_pick_status"] = pick_status
            entry["manual_current_picks_updated_at"] = now

            existing_by_team = {
                str(item.get("team")): item
                for item in (week_state.get("picks") or [])
                if isinstance(item, dict) and item.get("team")
            }

            week_state["picks"] = [
                {
                    **existing_by_team.get(team, {}),
                    "team": team,
                    "result": existing_by_team.get(team, {}).get("result", "PENDING"),
                    "game_status": existing_by_team.get(team, {}).get(
                        "game_status",
                        "Saved in Sports HULK; not submitted to pool",
                    ),
                    "source": existing_by_team.get(team, {}).get(
                        "source",
                        "SPORTS_HULK_MANUAL_UI",
                    ),
                }
                for team in picks
            ]
            week_state["manual_saved"] = bool(picks)
            week_state["manual_saved_at"] = now
            # Sports HULK never submits a pick to the external pool.
            if week_state.get("official_pool_sheet_confirmed") is not True:
                week_state["submitted"] = False

            entry[key] = week_state

    if make_active:
        data["active"] = entry_name

    data["manual_state_updated_at"] = now
    _atomic_write(data)
    _append_audit({
        "changed_at": now,
        "entry_name": entry_name,
        "pool_current_week": pool_week,
        "entry_status": entry.get("status"),
        "used_teams": entry.get("used_teams") or [],
        "current_week": entry.get("current_week"),
        "current_picks": entry.get("current_picks") or [],
        "current_pick_status": entry.get("current_pick_status"),
        "source": "SPORTS_HULK_SURVIVOR_EDITOR",
    })
    return data


def create_entry(entry_name: str, pool_name: str = "NFL Knockout Pool 2026") -> dict:
    name = str(entry_name).strip()
    if not name:
        raise ValueError("Entry name is required.")

    data = load_state()
    entries = data.setdefault("entries", {})
    if name in entries:
        raise ValueError("That entry already exists.")

    week = int(data.get("pool_current_week") or 1)
    now = _now()

    entries[name] = {
        "pool": pool_name,
        "status": "ALIVE",
        "used_teams": [],
        "current_pick": None,
        "backup_pick": None,
        "future_picks": {},
        "history": [],
        "current_week": week,
        "current_picks": [],
        "current_pick_status": "OPEN",
        f"week_{week}": {
            "required_picks": None,
            "rule_status": "AWAITING_OFFICIAL_POOL_SHEET",
            "picks": [],
            "entry_result": "OPEN",
            "submitted": False,
            "opened_at": now,
        },
        "created_manually_at": now,
    }

    data["active"] = name
    data["manual_state_updated_at"] = now
    _atomic_write(data)
    return data
