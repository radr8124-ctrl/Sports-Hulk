from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, timezone
import argparse, csv, json, os, re, time, socket, urllib.parse, urllib.request, urllib.error

HERE = Path(__file__).resolve().parent
MASTER = HERE.parent
ENV_PATH = MASTER / ".env"
RAW = HERE / "raw"
LATEST = HERE / "latest"
HISTORY = HERE / "history"

def now_local():
    return datetime.now().astimezone()

def stamp():
    return now_local().strftime("%Y%m%d_%H%M%S")

def ensure_dirs():
    for p in (RAW, LATEST, HISTORY):
        p.mkdir(parents=True, exist_ok=True)

def load_env():
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)

def get_json(url, params=None, headers=None, timeout=90, retries=4):
    if params:
        q = urllib.parse.urlencode(params, doseq=True)
        url = url + ("&" if "?" in url else "?") + q

    base_headers = {
        "User-Agent": "Sports-HULK-Baseball/1.0",
        "Accept": "application/json",
        "Connection": "close",
    }

    if headers:
        base_headers.update(headers)

    last_error = None

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers=base_headers,
            )

            with urllib.request.urlopen(
                req,
                timeout=timeout,
            ) as r:
                body = r.read().decode("utf-8")
                return json.loads(body)

        except urllib.error.HTTPError:
            # HTTP errors such as 401/403/429 should remain visible
            # instead of being disguised as ordinary network retries.
            raise

        except (
            urllib.error.URLError,
            ConnectionResetError,
            TimeoutError,
            socket.timeout,
        ) as e:
            last_error = e

            if attempt >= retries:
                break

            wait = 2 ** (attempt - 1)

            print(
                f"HTTP connection error "
                f"(attempt {attempt}/{retries}): {repr(e)}"
            )

            print(
                f"Retrying in {wait}s..."
            )

            time.sleep(wait)

    raise RuntimeError(
        f"HTTP request failed after {retries} attempts: "
        f"{repr(last_error)}"
    )

def save_json(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2))

def write_csv(rows, path, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if fieldnames is None:
        keys = []
        seen = set()
        for row in rows:
            for k in row:
                if k not in seen:
                    seen.add(k)
                    keys.append(k)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

def mlb_schedule(start_date, end_date):
    return get_json(
        "https://statsapi.mlb.com/api/v1/schedule",
        {
            "sportId": 1,
            "startDate": start_date,
            "endDate": end_date,
            "hydrate": "team,venue,probablePitcher,linescore"
        }
    )

def flatten_schedule(data):
    rows = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            teams = g.get("teams", {})
            home = teams.get("home", {})
            away = teams.get("away", {})
            hs = home.get("score")
            aws = away.get("score")
            rows.append({
                "gamePk": g.get("gamePk"),
                "officialDate": g.get("officialDate") or d.get("date"),
                "gameDate": g.get("gameDate"),
                "gameType": g.get("gameType"),
                "status": g.get("status", {}).get("detailedState"),
                "abstractState": g.get("status", {}).get("abstractGameState"),
                "away_team": away.get("team", {}).get("name"),
                "away_team_id": away.get("team", {}).get("id"),
                "home_team": home.get("team", {}).get("name"),
                "home_team_id": home.get("team", {}).get("id"),
                "away_probable_pitcher": away.get("probablePitcher", {}).get("fullName"),
                "away_probable_pitcher_id": away.get("probablePitcher", {}).get("id"),
                "home_probable_pitcher": home.get("probablePitcher", {}).get("fullName"),
                "home_probable_pitcher_id": home.get("probablePitcher", {}).get("id"),
                "away_score": aws,
                "home_score": hs,
                "venue": g.get("venue", {}).get("name"),
                "venue_id": g.get("venue", {}).get("id"),
                "seriesDescription": g.get("seriesDescription"),
                "doubleHeader": g.get("doubleHeader"),
                "gameNumber": g.get("gameNumber"),
            })
    return rows

def mlb_boxscore(game_pk):
    return get_json(f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore")

def safe_float(x):
    try:
        return float(x)
    except Exception:
        return None

def parse_innings_to_outs(ip):
    if ip in (None, ""):
        return 0
    s = str(ip)
    if "." in s:
        a, b = s.split(".", 1)
        try:
            return int(a) * 3 + int(b[:1] or 0)
        except Exception:
            return 0
    try:
        return int(float(s)) * 3
    except Exception:
        return 0

def lineup_and_bullpen_from_box(game_row, box, game_date):
    lineup_rows = []
    bullpen_rows = []
    game_pk = game_row["gamePk"]

    for side in ("away", "home"):
        team_obj = box.get("teams", {}).get(side, {})
        team_name = team_obj.get("team", {}).get("name") or game_row.get(f"{side}_team")
        players = team_obj.get("players", {})
        order = team_obj.get("battingOrder") or []

        for idx, pid in enumerate(order, start=1):
            p = players.get(f"ID{pid}", {})
            lineup_rows.append({
                "gamePk": game_pk,
                "game_date": game_date,
                "side": side,
                "team": team_name,
                "batting_order": idx,
                "player_id": pid,
                "player": p.get("person", {}).get("fullName"),
                "position": p.get("position", {}).get("abbreviation"),
            })

        pitchers = team_obj.get("pitchers") or []
        for i, pid in enumerate(pitchers):
            p = players.get(f"ID{pid}", {})
            pit = p.get("stats", {}).get("pitching", {}) or {}
            pitches = pit.get("numberOfPitches")
            if pitches is None:
                pitches = pit.get("pitchesThrown")
            bullpen_rows.append({
                "gamePk": game_pk,
                "game_date": game_date,
                "side": side,
                "team": team_name,
                "pitcher_id": pid,
                "pitcher": p.get("person", {}).get("fullName"),
                "role": "starter" if i == 0 else "reliever",
                "inningsPitched": pit.get("inningsPitched"),
                "outs": parse_innings_to_outs(pit.get("inningsPitched")),
                "pitches": safe_float(pitches) or 0,
                "battersFaced": safe_float(pit.get("battersFaced")) or 0,
                "hits": safe_float(pit.get("hits")) or 0,
                "runs": safe_float(pit.get("runs")) or 0,
                "earnedRuns": safe_float(pit.get("earnedRuns")) or 0,
                "walks": safe_float(pit.get("baseOnBalls")) or 0,
                "strikeouts": safe_float(pit.get("strikeOuts")) or 0,
            })
    return lineup_rows, bullpen_rows

def aggregate_bullpen(reliever_rows, asof_date):
    by = {}
    for r in reliever_rows:
        if r.get("role") != "reliever":
            continue
        key = (r.get("team"), r.get("pitcher_id"), r.get("pitcher"))
        rec = by.setdefault(key, {
            "team": r.get("team"),
            "pitcher_id": r.get("pitcher_id"),
            "pitcher": r.get("pitcher"),
            "appearances_last3": 0,
            "pitches_last3": 0.0,
            "outs_last3": 0,
            "batters_faced_last3": 0.0,
            "days_used_last3": set(),
            "last_used": None
        })
        rec["appearances_last3"] += 1
        rec["pitches_last3"] += r.get("pitches") or 0
        rec["outs_last3"] += r.get("outs") or 0
        rec["batters_faced_last3"] += r.get("battersFaced") or 0
        gd = r.get("game_date")
        if gd:
            rec["days_used_last3"].add(gd)
            if rec["last_used"] is None or gd > rec["last_used"]:
                rec["last_used"] = gd

    out = []
    for rec in by.values():
        days = len(rec.pop("days_used_last3"))
        rec["days_used_last3"] = days
        # First-pass fatigue index. We keep components too so weighting can be tuned later.
        rec["HULK_bullpen_workload_score"] = round(
            rec["pitches_last3"] + 12 * max(0, days - 1) + 6 * max(0, rec["appearances_last3"] - 1),
            1
        )
        out.append(rec)
    return sorted(out, key=lambda r: (r["team"] or "", -(r["HULK_bullpen_workload_score"] or 0)))

def collect_recent_boxscores(today, lookback_days=3):
    start = today - timedelta(days=lookback_days)
    sched = mlb_schedule(start.isoformat(), today.isoformat())
    schedule_rows = flatten_schedule(sched)
    lineups = []
    pitchers = []
    errors = []

    for g in schedule_rows:
        state = str(g.get("abstractState") or "")
        status = str(g.get("status") or "")
        # completed and in-progress games are useful; scheduled future games may not have boxscore/lineups yet
        if state not in ("Final", "Live") and "Final" not in status and "Progress" not in status and "Delayed" not in status:
            continue
        try:
            box = mlb_boxscore(g["gamePk"])
            l, p = lineup_and_bullpen_from_box(g, box, g.get("officialDate"))
            lineups.extend(l)
            pitchers.extend(p)
        except Exception as e:
            errors.append({"gamePk": g.get("gamePk"), "error": repr(e)})

    return lineups, pitchers, errors

def sgo_mlb():
    key = os.environ.get("SPORTSGAMEODDS_API_KEY", "").strip()
    if not key:
        return None, "SPORTSGAMEODDS_API_KEY missing"
    try:
        data = get_json(
            "https://api.sportsgameodds.com/v2/events",
            {"leagueID":"MLB","oddsAvailable":"true","limit":25},
            {"x-api-key": key, "User-Agent":"Sports-HULK-Baseball/1.0"}
        )
        return data, None
    except Exception as e:
        return None, repr(e)

def flatten_sgo(data):
    rows = []
    if not data:
        return rows
    for e in data.get("data", []) or []:
        teams = e.get("teams", {})
        home = teams.get("home", {}).get("names", {}).get("long") or teams.get("home", {}).get("name")
        away = teams.get("away", {}).get("names", {}).get("long") or teams.get("away", {}).get("name")
        players = e.get("players", {}) or {}
        for odd_id, odd in (e.get("odds", {}) or {}).items():
            player_id = odd.get("playerID")
            p = players.get(str(player_id), {}) if player_id is not None else {}
            player_name = p.get("name") or p.get("names", {}).get("long")
            for book, b in (odd.get("byBookmaker") or {}).items():
                rows.append({
                    "eventID": e.get("eventID"),
                    "start": e.get("status", {}).get("startsAt"),
                    "away_team": away,
                    "home_team": home,
                    "oddID": odd_id,
                    "statID": odd.get("statID"),
                    "playerID": player_id,
                    "player": player_name,
                    "periodID": odd.get("periodID"),
                    "betTypeID": odd.get("betTypeID"),
                    "sideID": odd.get("sideID"),
                    "bookmaker": book,
                    "available": b.get("available"),
                    "odds": b.get("odds"),
                    "spread": b.get("spread"),
                    "overUnder": b.get("overUnder"),
                    "lastUpdatedAt": b.get("lastUpdatedAt"),
                })
    return rows

def odds_api_mlb():
    key = os.environ.get("THE_ODDS_API_KEY", "").strip()
    if not key:
        return None, "THE_ODDS_API_KEY missing"
    try:
        data = get_json(
            "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds",
            {
                "regions":"us",
                "markets":"h2h,spreads,totals",
                "oddsFormat":"american",
                "apiKey":key
            }
        )
        return data, None
    except Exception as e:
        return None, repr(e)

def flatten_odds_api(data):
    rows = []
    for e in (data or []):
        for b in e.get("bookmakers", []) or []:
            for m in b.get("markets", []) or []:
                for o in m.get("outcomes", []) or []:
                    rows.append({
                        "event_id": e.get("id"),
                        "commence_time": e.get("commence_time"),
                        "away_team": e.get("away_team"),
                        "home_team": e.get("home_team"),
                        "bookmaker": b.get("key"),
                        "bookmaker_title": b.get("title"),
                        "book_last_update": b.get("last_update"),
                        "market": m.get("key"),
                        "market_last_update": m.get("last_update"),
                        "outcome": o.get("name"),
                        "price": o.get("price"),
                        "point": o.get("point"),
                    })
    return rows

def append_history_csv(rows, path):
    rows = list(rows)
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = []
    seen = set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k); keys.append(k)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        if not exists:
            w.writeheader()
        w.writerows(rows)

def main():
    ap = argparse.ArgumentParser(description="SPORTS HULK Baseball live/nightly collector")
    ap.add_argument("--date", help="YYYY-MM-DD; defaults to local today")
    ap.add_argument("--days", type=int, default=2, help="Schedule window starting at date (default 2)")
    ap.add_argument("--lookback", type=int, default=3, help="Bullpen workload lookback days")
    ap.add_argument("--skip-sgo", action="store_true")
    ap.add_argument("--skip-odds-api", action="store_true")
    a = ap.parse_args()

    ensure_dirs()
    load_env()
    run_stamp = stamp()
    today = datetime.strptime(a.date, "%Y-%m-%d").date() if a.date else now_local().date()
    end = today + timedelta(days=max(1, a.days)-1)

    print(f"Baseball HULK collector: {today} through {end}")

    schedule_raw = mlb_schedule(today.isoformat(), end.isoformat())
    schedule_rows = flatten_schedule(schedule_raw)
    save_json(schedule_raw, RAW / f"mlb_schedule_{run_stamp}.json")
    write_csv(schedule_rows, LATEST / "MLB_SCHEDULE.csv")
    print(f"MLB schedule games: {len(schedule_rows)}")

    lineups, pitcher_usage, box_errors = collect_recent_boxscores(today, a.lookback)
    write_csv(lineups, LATEST / "MLB_LINEUPS_RECENT.csv")
    write_csv(pitcher_usage, LATEST / "MLB_PITCHER_USAGE_RECENT.csv")
    bullpen = aggregate_bullpen(pitcher_usage, today)
    write_csv(bullpen, LATEST / "MLB_BULLPEN_WORKLOAD.csv")
    if box_errors:
        save_json(box_errors, RAW / f"boxscore_errors_{run_stamp}.json")
    print(f"Recent lineup rows: {len(lineups)}")
    print(f"Pitcher usage rows: {len(pitcher_usage)}")
    print(f"Relievers in workload table: {len(bullpen)}")

    if not a.skip_sgo:
        sgo, err = sgo_mlb()
        if sgo is not None:
            save_json(sgo, RAW / f"sgo_mlb_{run_stamp}.json")
            sgo_rows = flatten_sgo(sgo)
            for r in sgo_rows:
                r["snapshot_at"] = now_local().isoformat()
            write_csv(sgo_rows, LATEST / "MLB_SGO_MARKETS.csv")
            append_history_csv(sgo_rows, HISTORY / "MLB_SGO_MARKET_HISTORY.csv")
            print(f"SportsGameOdds events: {len(sgo.get('data',[]) or [])}")
            print(f"SportsGameOdds flattened book-market rows: {len(sgo_rows)}")
        else:
            print(f"SportsGameOdds skipped/error: {err}")

    if not a.skip_odds_api:
        oa, err = odds_api_mlb()
        if oa is not None:
            save_json(oa, RAW / f"odds_api_mlb_{run_stamp}.json")
            oa_rows = flatten_odds_api(oa)
            for r in oa_rows:
                r["snapshot_at"] = now_local().isoformat()
            write_csv(oa_rows, LATEST / "MLB_ODDS_API_MARKETS.csv")
            append_history_csv(oa_rows, HISTORY / "MLB_ODDS_API_MARKET_HISTORY.csv")
            print(f"The Odds API events: {len(oa)}")
            print(f"The Odds API flattened rows: {len(oa_rows)}")
        else:
            print(f"The Odds API skipped/error: {err}")

    summary = {
        "run_at": now_local().isoformat(),
        "date_from": today.isoformat(),
        "date_to": end.isoformat(),
        "schedule_games": len(schedule_rows),
        "recent_lineup_rows": len(lineups),
        "pitcher_usage_rows": len(pitcher_usage),
        "bullpen_rows": len(bullpen),
        "boxscore_errors": len(box_errors),
    }
    save_json(summary, LATEST / "LAST_RUN.json")

    print("SPORTS HULK BASEBALL LIVE VAULT: DONE")

if __name__ == "__main__":
    main()
