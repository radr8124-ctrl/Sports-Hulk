from pathlib import Path
from datetime import datetime, timezone
import os
import sys
import json
import requests
import pandas as pd
from dotenv import load_dotenv

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "nfl_live" / "derived"
HISTORY = ROOT / "nfl_live" / "history"

OUT.mkdir(parents=True, exist_ok=True)
HISTORY.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT / "api_control"))

from api_budget import can_call, record_call

PROVIDER = "the_odds_api"
FEED = "nfl_core"
ESTIMATED_COST = 3.0

CURRENT_CSV = OUT / "NFL_LIVE_MARKET.csv"
CURRENT_PQ = OUT / "NFL_LIVE_MARKET.parquet"

allowed, reason = can_call(
    PROVIDER,
    estimated_cost=ESTIMATED_COST,
    priority="HIGH",
)

print("=" * 80)
print("SPORTS HULK GOVERNED NFL COLLECTOR")
print("=" * 80)
print("Provider:", PROVIDER)
print("Feed:", FEED)
print("Allowed:", allowed)
print("Reason:", reason)

if not allowed:
    if CURRENT_CSV.exists():
        cached = pd.read_csv(CURRENT_CSV)
        print("API CALL SKIPPED")
        print("Using cached rows:", len(cached))
        print("RESULT: CACHE")
        raise SystemExit(0)

    raise SystemExit("CALL BLOCKED AND NO CACHE EXISTS")

key = os.getenv("THE_ODDS_API_KEY")

if not key:
    raise SystemExit("THE_ODDS_API_KEY missing")

url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/"

params = {
    "apiKey": key,
    "regions": "us",
    "markets": "h2h,spreads,totals",
    "oddsFormat": "american",
    "dateFormat": "iso",
}

r = requests.get(
    url,
    params=params,
    timeout=30,
)

print("HTTP:", r.status_code)

if r.status_code != 200:
    print(r.text[:1000])

    if CURRENT_CSV.exists():
        cached = pd.read_csv(CURRENT_CSV)
        print("LIVE CALL FAILED — USING CACHE")
        print("Cached rows:", len(cached))
        print("RESULT: CACHE")
        raise SystemExit(0)

    raise SystemExit("RESULT: FAIL")

# ------------------------------------------------------------
# RECORD REAL API USAGE
# ------------------------------------------------------------

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

# ------------------------------------------------------------
# ARCHIVE RAW RESPONSE
# ------------------------------------------------------------

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

raw_path = HISTORY / f"NFL_ODDS_RAW_{stamp}.json"

raw_path.write_text(
    json.dumps(events, indent=2)
)

# ------------------------------------------------------------
# NORMALIZE
# ------------------------------------------------------------

rows = []

for event in events:

    home = event.get("home_team")
    away = event.get("away_team")
    commence = event.get("commence_time")
    event_id = event.get("id")

    home_ml = []
    away_ml = []

    home_spreads = []
    away_spreads = []

    totals = []

    books = set()

    for book in event.get("bookmakers", []):

        book_name = book.get("title")

        if book_name:
            books.add(book_name)

        for market in book.get("markets", []):

            key_name = market.get("key")

            if key_name == "h2h":

                for o in market.get("outcomes", []):

                    if o.get("name") == home:
                        home_ml.append(o.get("price"))

                    elif o.get("name") == away:
                        away_ml.append(o.get("price"))

            elif key_name == "spreads":

                for o in market.get("outcomes", []):

                    if o.get("name") == home:
                        home_spreads.append(o.get("point"))

                    elif o.get("name") == away:
                        away_spreads.append(o.get("point"))

            elif key_name == "totals":

                for o in market.get("outcomes", []):

                    if o.get("name") == "Over":
                        totals.append(o.get("point"))

    def median(values):
        vals = pd.to_numeric(
            pd.Series(values),
            errors="coerce"
        ).dropna()

        return float(vals.median()) if len(vals) else None

    rows.append({
        "event_id": event_id,
        "start": commence,
        "away_team": away,
        "home_team": home,
        "away_moneyline": median(away_ml),
        "home_moneyline": median(home_ml),
        "away_spread": median(away_spreads),
        "home_spread": median(home_spreads),
        "total": median(totals),
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

# ------------------------------------------------------------
# SAVE CURRENT SNAPSHOT
# ------------------------------------------------------------

df.to_csv(
    CURRENT_CSV,
    index=False
)

df.to_parquet(
    CURRENT_PQ,
    index=False
)

# ------------------------------------------------------------
# SAVE NORMALIZED HISTORY SNAPSHOT
# ------------------------------------------------------------

hist_csv = HISTORY / f"NFL_LIVE_MARKET_{stamp}.csv"
hist_pq = HISTORY / f"NFL_LIVE_MARKET_{stamp}.parquet"

df.to_csv(
    hist_csv,
    index=False
)

df.to_parquet(
    hist_pq,
    index=False
)

print()
print("Rows:", len(df))
print("Raw archive:", raw_path)
print("Normalized archive:", hist_csv)
print("RESULT: LIVE")
