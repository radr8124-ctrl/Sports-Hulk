from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
ENTRIES = ROOT / "nfl_live/derived/SURVIVOR_ENTRIES.json"
SCHEDULE = ROOT / "nfl_live/derived/NFLVERSE_2026_SCHEDULE.csv"
STRATEGY = ROOT / "nfl_live/derived/NFL_SURVIVOR_HULK_STRATEGY.csv"

TEAM_MAP = {
    "ARI":"Arizona Cardinals","ATL":"Atlanta Falcons","BAL":"Baltimore Ravens",
    "BUF":"Buffalo Bills","CAR":"Carolina Panthers","CHI":"Chicago Bears",
    "CIN":"Cincinnati Bengals","CLE":"Cleveland Browns","DAL":"Dallas Cowboys",
    "DEN":"Denver Broncos","DET":"Detroit Lions","GB":"Green Bay Packers",
    "HOU":"Houston Texans","IND":"Indianapolis Colts","JAX":"Jacksonville Jaguars",
    "KC":"Kansas City Chiefs","LV":"Las Vegas Raiders","LAC":"Los Angeles Chargers",
    "LA":"Los Angeles Rams","MIA":"Miami Dolphins","MIN":"Minnesota Vikings",
    "NE":"New England Patriots","NO":"New Orleans Saints","NYG":"New York Giants",
    "NYJ":"New York Jets","PHI":"Philadelphia Eagles","PIT":"Pittsburgh Steelers",
    "SF":"San Francisco 49ers","SEA":"Seattle Seahawks","TB":"Tampa Bay Buccaneers",
    "TEN":"Tennessee Titans","WAS":"Washington Commanders",
}
REV = {v:k for k,v in TEAM_MAP.items()}

def load():
    return json.loads(ENTRIES.read_text())

def save(data):
    ENTRIES.write_text(json.dumps(data, indent=2))

def current_week(strategy, schedule):
    if not strategy.empty and "current_week" in strategy.columns:
        vals = pd.to_numeric(strategy["current_week"], errors="coerce").dropna()
        if not vals.empty:
            return int(vals.mode().iloc[0])

    future = schedule[
        (schedule["season"] == 2026)
        & (schedule["game_type"] == "REG")
        & schedule["home_score"].isna()
        & schedule["away_score"].isna()
    ]
    if not future.empty:
        return int(pd.to_numeric(future["week"], errors="coerce").dropna().min())

    done = schedule[
        (schedule["season"] == 2026)
        & (schedule["game_type"] == "REG")
        & schedule["home_score"].notna()
        & schedule["away_score"].notna()
    ]
    return int(done["week"].max()) + 1 if not done.empty else 1

def week_games(schedule, week):
    w = schedule[
        (schedule["season"] == 2026)
        & (schedule["week"] == week)
        & (schedule["game_type"] == "REG")
    ].copy()

    games = {}
    for _, row in w.iterrows():
        away = TEAM_MAP.get(str(row.get("away_team")), str(row.get("away_team")))
        home = TEAM_MAP.get(str(row.get("home_team")), str(row.get("home_team")))
        away_score = pd.to_numeric(row.get("away_score"), errors="coerce")
        home_score = pd.to_numeric(row.get("home_score"), errors="coerce")
        final = pd.notna(away_score) and pd.notna(home_score)

        winner = None
        if final:
            if home_score > away_score:
                winner = home
            elif away_score > home_score:
                winner = away
            else:
                winner = "TIE"

        detail = (
            f"FINAL: {away} {int(away_score)} - {home} {int(home_score)}"
            if final else "Game not final"
        )
        payload = {"final": final, "winner": winner, "detail": detail}
        games[away] = payload
        games[home] = payload

    return games

def settle_week(entry, week, schedule, now):
    key = f"week_{week}"
    state = entry.get(key)
    if not isinstance(state, dict):
        return False

    picks = state.get("picks") or []
    if not picks:
        return False

    games = week_games(schedule, week)
    results = []
    changed = False

    used = entry.setdefault("used_teams", [])
    history = entry.setdefault("history", [])

    for leg in picks:
        team = leg.get("team")
        if not team:
            continue

        game = games.get(team)
        if not game or not game["final"]:
            result = "PENDING"
            detail = "Game not final" if game else "Game not found"
        elif game["winner"] == team:
            result = "WIN"
            detail = game["detail"]
        else:
            result = "LOSS"
            detail = game["detail"]

        # A team is burned only after its Survivor leg resolves.
        # Pending/postponed games cannot silently consume future eligibility.
        if result in {"WIN", "LOSS"} and team not in used:
            used.append(team)

        if leg.get("result") != result or leg.get("game_status") != detail:
            changed = True

        leg["result"] = result
        leg["game_status"] = detail
        results.append(result)

        exists = any(
            int(h.get("week", -1)) == week
            and h.get("team") == team
            for h in history
            if isinstance(h, dict)
        )
        if result in {"WIN", "LOSS"} and not exists:
            history.append({
                "week": week,
                "team": team,
                "result": "SURVIVED" if result == "WIN" else "LOST",
                "source": "NFLVERSE_2026_SCHEDULE.csv",
            })
            changed = True

    if "LOSS" in results:
        state["entry_result"] = "LOSS"
        entry["status"] = "ELIMINATED"
    elif results and all(x == "WIN" for x in results):
        state["entry_result"] = "WIN"
        if entry.get("status") != "ELIMINATED":
            entry["status"] = "ALIVE"
    else:
        state["entry_result"] = "PENDING"

    state["last_checked_at"] = now
    entry[key] = state
    return changed

def open_current_week(entry, week, now):
    if entry.get("status") != "ALIVE":
        return

    prior_week = week - 1
    prior = entry.get(f"week_{prior_week}", {})
    if prior and prior.get("entry_result") not in {"WIN", "OPEN", None}:
        return

    previous_week = int(entry.get("current_week") or 0)

    if previous_week != week:
        entry["current_week"] = week
        entry["current_picks"] = []
        entry["current_pick"] = None
        entry["backup_pick"] = None
        entry["current_pick_status"] = "OPEN"
    else:
        entry["current_week"] = week
        entry.setdefault("current_picks", [])
        entry.setdefault("current_pick", None)
        entry.setdefault("backup_pick", None)
        entry.setdefault("current_pick_status", "OPEN")

    key = f"week_{week}"
    existing = entry.get(key)
    if not isinstance(existing, dict):
        entry[key] = {
            "required_picks": None,
            "rule_status": "AWAITING_OFFICIAL_WEEK_SHEET",
            "picks": [],
            "entry_result": "OPEN",
            "submitted": False,
            "last_checked_at": now,
        }
    else:
        existing.setdefault("required_picks", None)
        existing.setdefault("rule_status", "AWAITING_OFFICIAL_WEEK_SHEET")
        existing.setdefault("picks", [])
        existing.setdefault("entry_result", "OPEN")
        existing.setdefault("submitted", False)
        existing["last_checked_at"] = now
        entry[key] = existing

def main():
    data = load()
    schedule = pd.read_csv(SCHEDULE, low_memory=False)
    strategy = pd.read_csv(STRATEGY, low_memory=False) if STRATEGY.exists() else pd.DataFrame()
    week = current_week(strategy, schedule)
    now = datetime.now(timezone.utc).isoformat()

    entries = data.get("entries") or {}
    for name, entry in entries.items():
        if not isinstance(entry, dict):
            continue

        for w in range(1, week):
            settle_week(entry, w, schedule, now)

        open_current_week(entry, week, now)

    data["pool_current_week"] = week
    data["last_rollover_at"] = now
    save(data)

    active = data.get("active")
    print("CURRENT WEEK:", week)
    print("ACTIVE ENTRY:", active)
    if active in entries:
        e = entries[active]
        print("ACTIVE STATUS:", e.get("status"))
        print("USED:", ", ".join(e.get("used_teams") or []))
        print("CURRENT PICK STATUS:", e.get("current_pick_status"))
    print("RESULT: SURVIVOR_STATE_READY")

if __name__ == "__main__":
    main()
