from pathlib import Path
from datetime import datetime, timezone
import json
import sys

import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "nfl_live" / "derived"
HISTORY = ROOT / "nfl_live" / "history"
RECEIPTS = ROOT / "nfl_live" / "propline_receipts"

OUT.mkdir(parents=True, exist_ok=True)
HISTORY.mkdir(parents=True, exist_ok=True)
RECEIPTS.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))

from connectors.propline import PropLineClient

try:
    from api_control.api_budget import record_call
except Exception:
    record_call = None


SPORT = "football_nfl"
MARKETS = "h2h,spreads,totals"

client = PropLineClient()

if not client.connected:
    raise SystemExit("PROPLINE_API_KEY missing")

print("=" * 80)
print("SPORTS HULK — PROPLINE NFL LIVE MARKET")
print("=" * 80)

result = client.odds(
    SPORT,
    markets=MARKETS,
)

status = result["http_status"]
quota = result["quota"]

print("HTTP:", status)

print("QUOTA:")
for k, v in quota.items():
    if v is not None:
        print(k, "=", v)

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

receipt_path = RECEIPTS / f"PROPLINE_NFL_{stamp}.json"

receipt_path.write_text(
    json.dumps(
        {
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "sport": SPORT,
            "markets": MARKETS,
            "http_status": status,
            "quota": quota,
        },
        indent=2,
    )
)

print("Receipt:", receipt_path)

if status != 200:
    print(result["text"])
    raise SystemExit("PROPLINE LIVE CALL FAILED")

events = result["data"]

if not isinstance(events, list):
    raise SystemExit("Unexpected PropLine NFL response format")

# Record real provider usage.
used = quota.get("X-Daily-Used")
remaining = quota.get("X-Daily-Remaining")

if record_call is not None:
    try:
        record_call(
            "propline",
            cost=1.0,
            reported_used=float(used) if used is not None else None,
            reported_remaining=float(remaining) if remaining is not None else None,
        )
    except Exception as exc:
        print("Budget ledger warning:", exc)

raw_path = HISTORY / f"PROPLINE_NFL_RAW_{stamp}.json"
raw_path.write_text(json.dumps(events, indent=2))

rows = []

def median(values):
    vals = pd.to_numeric(
        pd.Series(values),
        errors="coerce"
    ).dropna()

    return float(vals.median()) if len(vals) else None


for event in events:
    if not isinstance(event, dict):
        continue

    home = event.get("home_team")
    away = event.get("away_team")
    commence = event.get("commence_time")
    event_id = event.get("id")

    if not home or not away or not commence:
        continue

    home_ml = []
    away_ml = []

    home_spreads = []
    away_spreads = []

    game_totals = []

    books = set()

    for book in event.get("bookmakers") or []:
        if not isinstance(book, dict):
            continue

        book_name = book.get("title") or book.get("key")

        if book_name:
            books.add(str(book_name))

        for market in book.get("markets") or []:
            if not isinstance(market, dict):
                continue

            key = market.get("key")

            # Ignore team-specific totals.
            # We only want the full-game total.
            if key == "totals" and market.get("team"):
                continue

            outcomes = market.get("outcomes") or []

            if key == "h2h":
                for o in outcomes:
                    name = o.get("name")
                    price = o.get("price")

                    if name == home:
                        home_ml.append(price)

                    elif name == away:
                        away_ml.append(price)

            elif key == "spreads":
                for o in outcomes:
                    name = o.get("name")
                    point = o.get("point")

                    if name == home:
                        home_spreads.append(point)

                    elif name == away:
                        away_spreads.append(point)

            elif key == "totals":
                for o in outcomes:
                    if o.get("name") == "Over":
                        game_totals.append(o.get("point"))

    # Require both sides of moneyline before allowing
    # this event into Survivor market calculations.
    home_ml_med = median(home_ml)
    away_ml_med = median(away_ml)

    if home_ml_med is None or away_ml_med is None:
        continue

    rows.append(
        {
            "event_id": event_id,
            "start": commence,
            "away_team": away,
            "home_team": home,
            "away_moneyline": away_ml_med,
            "home_moneyline": home_ml_med,
            "away_spread": median(away_spreads),
            "home_spread": median(home_spreads),
            "total": median(game_totals),
            "sportsbooks": len(books),
            "books_list": ", ".join(sorted(books)),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "market_source": "propline",
            "market_status": "LIVE",
            "source_event_last_update": event.get("last_update"),
        }
    )


df = pd.DataFrame(rows)

if df.empty:
    raise SystemExit(
        "PropLine returned no complete NFL game-line rows. "
        "Existing NFL market files were NOT replaced."
    )

df["start"] = pd.to_datetime(
    df["start"],
    errors="coerce",
    utc=True,
)

df = df.dropna(subset=["start"])

now = pd.Timestamp.now(tz="UTC")

future = df[df["start"] >= now].copy()

if future.empty:
    raise SystemExit(
        "PropLine produced no FUTURE NFL events. "
        "Existing NFL market files were NOT replaced."
    )

future = future.sort_values("start").reset_index(drop=True)

print()
print("Normalized complete future NFL games:", len(future))

print()
print(
    future[
        [
            "away_team",
            "home_team",
            "away_moneyline",
            "home_moneyline",
            "home_spread",
            "total",
            "sportsbooks",
            "market_source",
        ]
    ].head(20).to_string(index=False)
)

# Write temporary files first.
temp_csv = OUT / "NFL_LIVE_MARKET.propline.tmp.csv"
temp_pq = OUT / "NFL_LIVE_MARKET.propline.tmp.parquet"

future.to_csv(temp_csv, index=False)
future.to_parquet(temp_pq, index=False)

# Archive normalized result.
hist_csv = HISTORY / f"PROPLINE_NFL_NORMALIZED_{stamp}.csv"
hist_pq = HISTORY / f"PROPLINE_NFL_NORMALIZED_{stamp}.parquet"

future.to_csv(hist_csv, index=False)
future.to_parquet(hist_pq, index=False)

# Atomic-ish replacement only after validation succeeded.
final_csv = OUT / "NFL_LIVE_MARKET.csv"
final_pq = OUT / "NFL_LIVE_MARKET.parquet"

temp_csv.replace(final_csv)
temp_pq.replace(final_pq)

print()
print("LIVE MARKET UPDATED")
print("CSV:", final_csv)
print("Parquet:", final_pq)
print("Raw archive:", raw_path)
print("Normalized archive:", hist_csv)

print()
print("RESULT: LIVE_PROPLINE")
