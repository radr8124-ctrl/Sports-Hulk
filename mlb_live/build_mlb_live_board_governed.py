from pathlib import Path
from datetime import datetime, timezone
import os
import sys
import json
import requests
import pandas as pd
from dotenv import load_dotenv

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "mlb_live" / "derived"
HISTORY = ROOT / "mlb_live" / "history"

OUT.mkdir(parents=True, exist_ok=True)
HISTORY.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT / "api_control"))

from api_budget import can_call, record_call

PROVIDER = "the_odds_api"
ESTIMATED_COST = 3.0

CURRENT_CSV = OUT / "MLB_LIVE_MARKET.csv"
CURRENT_PQ = OUT / "MLB_LIVE_MARKET.parquet"

allowed, reason = can_call(
    PROVIDER,
    estimated_cost=ESTIMATED_COST,
    priority="HIGH",
)

print("=" * 80)
print("SPORTS HULK GOVERNED MLB COLLECTOR")
print("=" * 80)
print("Allowed:", allowed)
print("Reason:", reason)

if not allowed:
    if CURRENT_CSV.exists():
        cached = pd.read_csv(CURRENT_CSV)
        print("API CALL SKIPPED")
        print("Using cached rows:", len(cached))
        print("RESULT: CACHE")
        raise SystemExit(0)

    raise SystemExit("CALL BLOCKED AND NO MLB CACHE EXISTS")

key = os.getenv("THE_ODDS_API_KEY")

if not key:
    raise SystemExit("THE_ODDS_API_KEY missing")

r = requests.get(
    "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/",
    params={
        "apiKey": key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "dateFormat": "iso",
    },
    timeout=30,
)

print("HTTP:", r.status_code)

if r.status_code != 200:
    print(r.text[:1000])

    if CURRENT_CSV.exists():
        print("LIVE CALL FAILED — USING CACHE")
        print("RESULT: CACHE")
        raise SystemExit(0)

    raise SystemExit("RESULT: FAIL")

used = r.headers.get("x-requests-used")
remaining = r.headers.get("x-requests-remaining")
last_cost = r.headers.get("x-requests-last")

actual_cost = float(last_cost or ESTIMATED_COST)

record_call(
    PROVIDER,
    cost=actual_cost,
    reported_used=float(used) if used is not None else None,
    reported_remaining=float(remaining) if remaining is not None else None,
)

print("API COST:", actual_cost)
print("USED:", used)
print("REMAINING:", remaining)

events = r.json()

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

(HISTORY / f"MLB_ODDS_RAW_{stamp}.json").write_text(
    json.dumps(events, indent=2)
)

rows = []

for event in events:

    home = event.get("home_team")
    away = event.get("away_team")

    home_ml = []
    away_ml = []
    home_spread = []
    away_spread = []
    totals = []
    books = set()

    for book in event.get("bookmakers", []):

        if book.get("title"):
            books.add(book.get("title"))

        for market in book.get("markets", []):

            key = market.get("key")

            if key == "h2h":
                for o in market.get("outcomes", []):
                    if o.get("name") == home:
                        home_ml.append(o.get("price"))
                    elif o.get("name") == away:
                        away_ml.append(o.get("price"))

            elif key == "spreads":
                for o in market.get("outcomes", []):
                    if o.get("name") == home:
                        home_spread.append(o.get("point"))
                    elif o.get("name") == away:
                        away_spread.append(o.get("point"))

            elif key == "totals":
                for o in market.get("outcomes", []):
                    if o.get("name") == "Over":
                        totals.append(o.get("point"))

    def med(vals):
        x = pd.to_numeric(
            pd.Series(vals),
            errors="coerce"
        ).dropna()

        return float(x.median()) if len(x) else None

    rows.append({
        "event_id": event.get("id"),
        "start": event.get("commence_time"),
        "away_team": away,
        "home_team": home,
        "away_moneyline": med(away_ml),
        "home_moneyline": med(home_ml),
        "away_spread": med(away_spread),
        "home_spread": med(home_spread),
        "total": med(totals),
        "sportsbooks": len(books),
        "books_list": ", ".join(sorted(books)),
        "collected_at": datetime.now(timezone.utc).isoformat(),
    })

df = pd.DataFrame(rows)

if not df.empty:
    df["start"] = pd.to_datetime(
        df["start"],
        errors="coerce",
        utc=True
    )
    df = df.sort_values("start")

df.to_csv(CURRENT_CSV, index=False)
df.to_parquet(CURRENT_PQ, index=False)

df.to_csv(
    HISTORY / f"MLB_LIVE_MARKET_{stamp}.csv",
    index=False
)

df.to_parquet(
    HISTORY / f"MLB_LIVE_MARKET_{stamp}.parquet",
    index=False
)

print("Rows:", len(df))
print("RESULT: LIVE")
