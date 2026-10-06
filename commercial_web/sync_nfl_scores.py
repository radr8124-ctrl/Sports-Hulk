from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import subprocess
import sys
import json

ROOT = Path("/home/ubuntu/sports-hulk")
ET = ZoneInfo("America/New_York")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from premium_ui.live_scores import get_json, _https_ref, _parse_core_event, team_key


def sql_text(value):
    if value is None:
        return "null"
    return "'" + str(value).replace("'", "''") + "'"


def sql_int(value):
    if value in (None, ""):
        return "null"
    try:
        return str(int(float(value)))
    except Exception:
        return "null"


def fetch_date(day_yyyymmdd: str):
    url = (
        "https://sports.core.api.espn.com/"
        "v2/sports/football/leagues/nfl/events"
        f"?dates={day_yyyymmdd}&limit=50&lang=en&region=us"
    )
    payload = get_json(url)
    refs = [_https_ref(item) for item in payload.get("items", [])]
    refs = [ref for ref in refs if ref]
    with ThreadPoolExecutor(max_workers=8) as pool:
        games = list(pool.map(_parse_core_event, refs))
    return [game for game in games if game]


def normalize_status(game):
    if game.get("final"):
        return "final"
    if game.get("live"):
        return "live"
    return "scheduled"


def fetch_boxscore(event_id):
    payload = get_json(
        "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary"
        f"?event={event_id}"
    )
    box = payload.get("boxscore", {})

    team_stats = {}
    for team in box.get("teams", []) or []:
        abbr = (team.get("team") or {}).get("abbreviation")
        if not abbr:
            continue
        wanted = {}
        for stat in team.get("statistics", []) or []:
            name = stat.get("name")
            if name in {
                "firstDowns", "thirdDownEff", "totalYards", "netPassingYards",
                "rushingYards", "turnovers", "possessionTime", "sacksYardsLost"
            }:
                wanted[name] = stat.get("displayValue")
        team_stats[abbr] = wanted

    players = {}
    for team in box.get("players", []) or []:
        abbr = (team.get("team") or {}).get("abbreviation")
        if not abbr:
            continue
        groups = {}
        for group in team.get("statistics", []) or []:
            name = group.get("name")
            if name not in {"passing", "rushing", "receiving"}:
                continue
            labels = group.get("labels", []) or []
            rows = []
            for item in group.get("athletes", []) or []:
                athlete = item.get("athlete") or {}
                rows.append({
                    "name": athlete.get("displayName"),
                    "headshot": (athlete.get("headshot") or {}).get("href"),
                    "stats": dict(zip(labels, item.get("stats", []) or [])),
                })
            groups[name] = rows
        players[abbr] = groups

    scoring = []
    for item in payload.get("scoringPlays", []) or []:
        scoring.append({
            "period": item.get("period", {}).get("number") if isinstance(item.get("period"), dict) else item.get("period"),
            "clock": (item.get("clock") or {}).get("displayValue") if isinstance(item.get("clock"), dict) else item.get("clock"),
            "text": item.get("text") or item.get("shortText"),
            "away_score": item.get("awayScore"),
            "home_score": item.get("homeScore"),
            "team": (item.get("team") or {}).get("abbreviation") if isinstance(item.get("team"), dict) else None,
        })

    leaders = []
    for side in payload.get("leaders", []) or []:
        team = (side.get("team") or {}).get("abbreviation") if isinstance(side.get("team"), dict) else None
        for category in side.get("leaders", []) or []:
            cat = category.get("displayName") or category.get("name")
            for lead in category.get("leaders", [])[:2] or []:
                athlete = lead.get("athlete") or {}
                leaders.append({
                    "team": team,
                    "category": cat,
                    "player": athlete.get("displayName"),
                    "value": lead.get("displayValue"),
                })

    return {"team_stats": team_stats, "players": players, "scoring_plays": scoring[-12:], "leaders": leaders[:12]}
def build_upsert(games):
    values = []
    for game in games:
        start_time = game.get("start_time")
        if not start_time:
            continue
        values.append(
            "("
            + ",".join([
                sql_text("NFL"),
                sql_text("NFL"),
                sql_text(game.get("event_id")),
                sql_text(start_time),
                sql_text(game.get("home_abbr") or game.get("home")),
                sql_text(game.get("away_abbr") or game.get("away")),
                sql_text(normalize_status(game)),
                sql_text(game.get("status")),
                "null",
                sql_int(game.get("home_score")),
                sql_int(game.get("away_score")),
                "null",
                "null",
                "now()",
                sql_text(game.get("source") or "ESPN Core"),
                "now()",
                "now()",
            ])
            + ")"
        )

    if not values:
        return None

    return f"""
insert into public.games (
  sport, league, provider_game_id, start_time, home_team, away_team,
  status, period, clock, home_score, away_score, possession, venue,
  last_verified_at, source, created_at, updated_at
)
values
{",".join(values)}
on conflict (league, provider_game_id) do update set
  start_time = excluded.start_time,
  home_team = excluded.home_team,
  away_team = excluded.away_team,
  status = excluded.status,
  period = excluded.period,
  clock = excluded.clock,
  home_score = excluded.home_score,
  away_score = excluded.away_score,
  last_verified_at = excluded.last_verified_at,
  source = excluded.source,
  updated_at = now();
"""
def run():
    today = datetime.now(ET).date()
    days = [today - timedelta(days=1), today]
    games = []
    for day in days:
        games.extend(fetch_date(day.strftime("%Y%m%d")))

    upcoming = []
    for offset in range(1, 8):
        day = today + timedelta(days=offset)
        upcoming.extend(fetch_date(day.strftime("%Y%m%d")))

    for game in games + upcoming:
        if not game.get("away_abbr"):
            game["away_abbr"] = team_key(game.get("away"))
        if not game.get("home_abbr"):
            game["home_abbr"] = team_key(game.get("home"))

    for game in games:
        if game.get("live") or game.get("final"):
            try:
                game["boxscore"] = fetch_boxscore(game.get("event_id"))
            except Exception as exc:
                game["boxscore_error"] = str(exc)

    snapshot = {
        "generated_at": datetime.now(ET).isoformat(),
        "source": "ESPN Core",
        "games": games,
        "next_games": upcoming,
    }
    for target in [
        ROOT / "commercial_web" / "public" / "nfl_scores.json",
        ROOT / "commercial_web" / "dist" / "nfl_scores.json",
    ]:
        if target.parent.exists():
            target.write_text(json.dumps(snapshot, indent=2))

    sql = build_upsert(games)
    if sql:
        subprocess.run(
            ["npx", "@insforge/cli", "db", "query", sql],
            cwd=ROOT,
            check=True,
        )

    health_sql = f"""
insert into public.system_health(component,status,last_success_at,last_attempt_at,source,message,updated_at)
values (
  'live_scores',
  'CURRENT',
  now(),
  now(),
  'ESPN Core',
  'NFL score sync completed: {len(games)} games across yesterday/today',
  now()
)
on conflict(component) do update set
  status=excluded.status,
  last_success_at=excluded.last_success_at,
  last_attempt_at=excluded.last_attempt_at,
  source=excluded.source,
  message=excluded.message,
  updated_at=now();
"""
    subprocess.run(
        ["npx", "@insforge/cli", "db", "query", health_sql],
        cwd=ROOT,
        check=True,
    )
    print(f"NFL score sync PASS: {len(games)} games")


if __name__ == "__main__":
    run()
