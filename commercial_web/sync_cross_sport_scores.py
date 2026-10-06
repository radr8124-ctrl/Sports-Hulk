#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path("/home/ubuntu/sports-hulk")
PUBLIC = ROOT / "commercial_web" / "public"
DIST = ROOT / "commercial_web" / "dist"
ET = ZoneInfo("America/New_York")

LEAGUES = {
    "NBA": ("basketball", "nba", "ESPN NBA"),
    "NHL": ("hockey", "nhl", "ESPN NHL"),
    "CFB": ("football", "college-football", "ESPN FBS"),
    "CBB": ("basketball", "mens-college-basketball", "ESPN Division I"),
}
GROUPS = {"CFB": "80", "CBB": "50"}

def get_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 SportsZenith/1.0"})
    with urlopen(req, timeout=20) as resp:
        return json.load(resp)

def as_int(value):
    try:
        return int(float(value))
    except Exception:
        return None

def normalize_event(event: dict, league: str, source: str) -> dict | None:
    comps = event.get("competitions") or []
    if not comps:
        return None
    comp = comps[0]
    status = comp.get("status") or event.get("status") or {}
    stype = status.get("type") or {}
    state = str(stype.get("state") or "pre").lower()
    completed = bool(stype.get("completed"))
    competitors = comp.get("competitors") or []
    home = next((x for x in competitors if x.get("homeAway") == "home"), None)
    away = next((x for x in competitors if x.get("homeAway") == "away"), None)
    if not home or not away:
        return None

    def team_obj(row):
        team = row.get("team") or {}
        return {
            "name": team.get("displayName") or team.get("shortDisplayName") or team.get("name"),
            "abbr": team.get("abbreviation") or team.get("shortDisplayName"),
            "logo": team.get("logo"),
            "score": as_int(row.get("score")),
            "winner": bool(row.get("winner")),
            "record": ((row.get("records") or [{}])[0] or {}).get("summary"),
        }

    h, a = team_obj(home), team_obj(away)
    detail = stype.get("shortDetail") or stype.get("detail") or status.get("displayClock") or ""
    period = status.get("period")
    clock = status.get("displayClock")
    venue = ((comp.get("venue") or {}).get("fullName"))
    broadcasts = []
    for item in comp.get("broadcasts") or []:
        broadcasts += item.get("names") or []

    return {
        "event_id": str(event.get("id") or comp.get("id") or ""),
        "league": league,
        "start_time": event.get("date") or comp.get("date"),
        "name": event.get("shortName") or event.get("name"),
        "home": h["name"],
        "home_abbr": h["abbr"],
        "home_score": h["score"],
        "home_logo": h["logo"],
        "home_record": h["record"],
        "away": a["name"],
        "away_abbr": a["abbr"],
        "away_score": a["score"],
        "away_logo": a["logo"],
        "away_record": a["record"],
        "live": state == "in" and not completed,
        "final": completed or state == "post",
        "state": state,
        "status": detail,
        "period": period,
        "clock": clock,
        "venue": venue,
        "broadcasts": list(dict.fromkeys(broadcasts)),
        "source": source,
        "boxscore_available": bool(event.get("id") or comp.get("id")) and (state == "in" or completed or state == "post"),
    }

def fetch_day(league: str, date_text: str) -> list[dict]:
    sport, slug, source = LEAGUES[league]
    query = f"?dates={date_text}&limit=400"
    if league in GROUPS:
        query += f"&groups={GROUPS[league]}"
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{slug}/scoreboard{query}"
    payload = get_json(url)
    out = []
    for event in payload.get("events") or []:
        row = normalize_event(event, league, source)
        if row:
            out.append(row)
    return out

def build_league(league: str) -> dict:
    now = datetime.now(ET)
    dates = [(now + timedelta(days=offset)).strftime("%Y%m%d") for offset in (-1, 0, 1)]
    games = {}
    failures = []
    for date_text in dates:
        try:
            for game in fetch_day(league, date_text):
                games[game["event_id"]] = game
        except Exception as exc:
            failures.append({"date": date_text, "error": str(exc)[:200]})
    rows = sorted(games.values(), key=lambda x: x.get("start_time") or "")
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "league": league,
        "source": LEAGUES[league][2],
        "window": {"dates": dates},
        "status": "READY" if rows else ("ERROR" if failures else "NO_GAMES"),
        "games": rows,
        "counts": {
            "games": len(rows),
            "live": sum(bool(x["live"]) for x in rows),
            "final": sum(bool(x["final"]) for x in rows),
            "upcoming": sum(not x["live"] and not x["final"] for x in rows),
        },
        "failures": failures,
    }

def write_atomic(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, allow_nan=False))
    tmp.replace(path)

def main():
    summary = {}
    for league in LEAGUES:
        payload = build_league(league)
        filename = f"{league.lower()}_scores.json"
        write_atomic(PUBLIC / filename, payload)
        write_atomic(DIST / filename, payload)
        summary[league] = payload["counts"]
    print(json.dumps({"status": "READY", "leagues": summary}, indent=2))

if __name__ == "__main__":
    main()
