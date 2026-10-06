from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import requests

ROOT = Path("/home/ubuntu/sports-hulk")
ET = ZoneInfo("America/New_York")
OUT_PUBLIC = ROOT / "commercial_web" / "public" / "mlb_scores.json"
OUT_DIST = ROOT / "commercial_web" / "dist" / "mlb_scores.json"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Sports-HULK/1.0"})


def get_json(url):
    r = SESSION.get(url, timeout=20)
    r.raise_for_status()
    return r.json()


def schedule_for(day):
    url = (
        "https://statsapi.mlb.com/api/v1/schedule"
        f"?sportId=1&date={day.isoformat()}&hydrate=linescore,team"
    )
    payload = get_json(url)
    return [g for b in payload.get("dates", []) for g in b.get("games", [])]


def team_name(side):
    return side.get("team", {}).get("name", "")


def game_summary(g):
    status = g.get("status", {})
    abstract = status.get("abstractGameState", "")
    detailed = status.get("detailedState", "")
    linescore = g.get("linescore", {})
    innings = []
    for inn in linescore.get("innings", []) or []:
        innings.append({
            "num": inn.get("num"),
            "away": (inn.get("away") or {}).get("runs"),
            "home": (inn.get("home") or {}).get("runs"),
        })
    return {
        "gamePk": g.get("gamePk"),
        "gameDate": g.get("gameDate"),
        "away": team_name(g.get("teams", {}).get("away", {})),
        "home": team_name(g.get("teams", {}).get("home", {})),
        "away_score": g.get("teams", {}).get("away", {}).get("score"),
        "home_score": g.get("teams", {}).get("home", {}).get("score"),
        "status": detailed,
        "live": abstract == "Live",
        "final": abstract == "Final" or str(detailed).startswith("Final"),
        "innings": innings,
        "source": "MLB StatsAPI",
    }
def batting_rows(team_box):
    players = team_box.get("players", {})
    rows = []
    for pid in team_box.get("batters", []) or []:
        p = players.get(f"ID{pid}", {})
        s = (p.get("stats") or {}).get("batting") or {}
        if not s:
            continue
        rows.append({
            "name": (p.get("person") or {}).get("fullName", str(pid)),
            "pos": ((p.get("position") or {}).get("abbreviation") or ""),
            "ab": s.get("atBats", 0),
            "r": s.get("runs", 0),
            "h": s.get("hits", 0),
            "rbi": s.get("rbi", 0),
            "bb": s.get("baseOnBalls", 0),
            "so": s.get("strikeOuts", 0),
            "hr": s.get("homeRuns", 0),
            "avg": s.get("avg"),
        })
    return rows


def pitching_rows(team_box):
    players = team_box.get("players", {})
    rows = []
    for pid in team_box.get("pitchers", []) or []:
        p = players.get(f"ID{pid}", {})
        s = (p.get("stats") or {}).get("pitching") or {}
        if not s:
            continue
        rows.append({
            "name": (p.get("person") or {}).get("fullName", str(pid)),
            "ip": s.get("inningsPitched"),
            "h": s.get("hits", 0),
            "r": s.get("runs", 0),
            "er": s.get("earnedRuns", 0),
            "bb": s.get("baseOnBalls", 0),
            "so": s.get("strikeOuts", 0),
            "hr": s.get("homeRuns", 0),
            "pitches": s.get("pitchesThrown"),
        })
    return rows


def boxscore(game_pk):
    payload = get_json(f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore")
    teams = payload.get("teams", {})
    return {
        "away": {
            "batting": batting_rows(teams.get("away", {})),
            "pitching": pitching_rows(teams.get("away", {})),
        },
        "home": {
            "batting": batting_rows(teams.get("home", {})),
            "pitching": pitching_rows(teams.get("home", {})),
        },
    }
def main():
    today = datetime.now(ET).date()
    recent_days = [today - timedelta(days=1), today]
    next_days = [today + timedelta(days=i) for i in range(1, 4)]

    recent = []
    today_games = []
    upcoming = []

    for day in recent_days:
        for raw in schedule_for(day):
            g = game_summary(raw)
            if day == today:
                today_games.append(g)
            else:
                recent.append(g)

    for day in next_days:
        for raw in schedule_for(day):
            upcoming.append(game_summary(raw))

    for g in recent + today_games:
        if g["live"] or g["final"]:
            try:
                g["boxscore"] = boxscore(g["gamePk"])
            except Exception as exc:
                g["boxscore_error"] = str(exc)

    payload = {
        "generated_at": datetime.now(ET).isoformat(),
        "source": "MLB StatsAPI",
        "today": today.isoformat(),
        "today_games": today_games,
        "recent_games": recent[-8:],
        "next_games": upcoming[:12],
    }

    text = json.dumps(payload, indent=2)
    OUT_PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    OUT_PUBLIC.write_text(text)
    if OUT_DIST.parent.exists():
        OUT_DIST.write_text(text)

    print(
        f"MLB sync PASS: today={len(today_games)} "
        f"recent={len(recent)} next={len(upcoming)}"
    )


if __name__ == "__main__":
    main()
