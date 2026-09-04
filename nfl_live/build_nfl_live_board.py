from pathlib import Path
from datetime import datetime, timezone
import os
import requests
import pandas as pd
from dotenv import load_dotenv

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "nfl_live" / "derived"
OUT.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

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

print("=" * 76)
print("NFL LIVE MARKET BUILD")
print("=" * 76)

r = requests.get(url, params=params, timeout=30)

print("HTTP:", r.status_code)

if r.status_code != 200:
    print(r.text[:1000])
    raise SystemExit("RESULT: FAIL")

events = r.json()

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
        vals = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
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
    df["start"] = pd.to_datetime(df["start"], errors="coerce", utc=True)
    df = df.sort_values("start")

csv_path = OUT / "NFL_LIVE_MARKET.csv"
pq_path = OUT / "NFL_LIVE_MARKET.parquet"

df.to_csv(csv_path, index=False)
df.to_parquet(pq_path, index=False)

print()
print("Games:", len(df))

if len(df):
    print()
    print(
        df[
            [
                "away_team",
                "home_team",
                "away_moneyline",
                "home_moneyline",
                "home_spread",
                "total",
                "sportsbooks",
            ]
        ].to_string(index=False)
    )

print()
print("CSV:", csv_path)
print("RESULT: PASS")
