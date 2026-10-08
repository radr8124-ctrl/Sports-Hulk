"""Authenticated Survivor pick save bridge; no pool-site submission, no public data."""
from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from premium_ui import survivor_editor as editor


SCORES_PATH = ROOT / "commercial_web/public/nfl_scores.json"
MAX_PICKS = 4


def _kickoff(team: str, scores: dict) -> datetime | None:
    games = (scores.get("games") or []) + (scores.get("next_games") or [])
    for game in games:
        if not isinstance(game, dict):
            continue
        if team not in {game.get("home"), game.get("away")}:
            continue
        try:
            started = datetime.fromisoformat(
                str(game.get("start_time") or "").replace("Z", "+00:00")
            )
        except ValueError:
            continue
        if started.tzinfo is not None:
            return started.astimezone(timezone.utc)
    return None


def save_week(payload: dict, *, now: datetime | None = None,
              scores_path: Path = SCORES_PATH) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Invalid Survivor pick request.")
    entry_name = payload.get("entry_name")
    week = payload.get("week")
    teams = payload.get("teams")
    if not isinstance(entry_name, str) or not 0 < len(entry_name.strip()) <= 160:
        raise ValueError("Choose your linked Survivor entry.")
    if isinstance(week, bool) or not isinstance(week, int) or not 1 <= week <= 25:
        raise ValueError("A valid current pool week is required.")
    if not isinstance(teams, list) or len(teams) > MAX_PICKS:
        raise ValueError("Choose up to four NFL teams.")
    if any(not isinstance(t, str) or t not in editor.NFL_TEAMS for t in teams):
        raise ValueError("A saved selection must be an official NFL team.")
    if len(set(teams)) != len(teams):
        raise ValueError("Duplicate Survivor selections are not allowed.")

    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("A timezone-aware cutoff is required.")

    # Cooperative lock prevents concurrent saves issued through this bridge.
    lock_file = editor.ENTRIES_PATH.with_suffix(".save.lock")
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with lock_file.open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = editor.load_state()
        entry = (state.get("entries") or {}).get(entry_name.strip())
        if not isinstance(entry, dict):
            raise ValueError("Linked Survivor entry is no longer available.")
        if int(state.get("pool_current_week") or 0) != week:
            raise ValueError("The pool week changed. Refresh before saving.")

        # Do not rewrite a previously saved pick after its actual kickoff.
        week_state = entry.get(f"week_{week}") or {}
        recorded = [
            item.get("team") for item in week_state.get("picks") or []
            if isinstance(item, dict)
        ]
        old_picks = recorded or (
            entry.get("current_picks") or [] if entry.get("current_week") == week else []
        )
        with scores_path.open("r", encoding="utf-8") as handle:
            scores = json.load(handle)

        for team in set(old_picks) | set(teams):
            start = _kickoff(team, scores)
            if start is None:
                raise ValueError(
                    f"Kickoff cannot be verified for {team}. Try again after the score feed updates."
                )
            if now >= start:
                raise ValueError(f"Kickoff has passed for {team}; this saved pick is locked.")

        result = editor.save_entry(
            entry_name.strip(), current_week=week, current_picks=teams,
        )
        saved = result["entries"][entry_name.strip()]
        return {
            "status": "SAVED_NOT_SUBMITTED",
            "entry_name": entry_name.strip(),
            "week": week,
            "teams": saved.get("current_picks") or [],
            "pick_status": saved.get("current_pick_status"),
            "pool_submitted": False,
        }


def main() -> int:
    try:
        payload = json.loads(sys.stdin.buffer.read(16_384).decode("utf-8"))
        answer = save_week(payload)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        answer = {"status": "ERROR", "message": str(exc)}
    except Exception:
        answer = {"status": "ERROR", "message": "Survivor pick storage is temporarily unavailable."}
    sys.stdout.write(json.dumps(answer, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
