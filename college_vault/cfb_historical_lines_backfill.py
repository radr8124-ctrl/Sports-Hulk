from __future__ import annotations

from pathlib import Path
from statistics import median
import json
import math
import os
import time

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path("/home/ubuntu/sports-hulk")
VAULT = ROOT / "college_vault"
RAW = VAULT / "raw" / "lines"
DERIVED = VAULT / "derived"
META = VAULT / "meta"
for path in (RAW, DERIVED, META):
    path.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env", override=True)
KEY = (
    os.getenv("COLLEGEFOOTBALLDATA_API_KEY")
    or os.getenv("CFBD_API_KEY")
    or ""
).strip()
BASE = "https://api.collegefootballdata.com"
YEARS = list(range(2016, 2026))
MIN_OVERROUND = 0.98
MAX_OVERROUND = 1.20


def num(value):
    try:
        value = float(value)
        return None if math.isnan(value) else value
    except Exception:
        return None


def valid_american(value):
    value = num(value)
    return value is not None and abs(value) >= 100


def implied(value):
    value = num(value)
    if value is None or abs(value) < 100:
        return None
    if value > 0:
        return 100.0 / (value + 100.0)
    return abs(value) / (abs(value) + 100.0)


def decimal_odds(value):
    value = num(value)
    if value is None or abs(value) < 100:
        return None
    return 1.0 + (value / 100.0 if value > 0 else 100.0 / abs(value))


def best_price(rows, field):
    best = None
    best_book = None
    best_decimal = None
    for row in rows:
        price = num(row.get(field))
        dec = decimal_odds(price)
        if dec is None:
            continue
        if best_decimal is None or dec > best_decimal:
            best_decimal = dec
            best = price
            best_book = row.get("provider")
    return best, best_book


def mad(values):
    values = [float(v) for v in values if v is not None]
    if not values:
        return None
    center = median(values)
    return median(abs(v - center) for v in values)


def fetch_year(year):
    path = RAW / f"lines_{year}.json"
    if path.exists():
        return json.loads(path.read_text())
    if not KEY:
        raise RuntimeError("CFBD API key missing.")
    response = requests.get(
        BASE + "/lines",
        headers={"Authorization": f"Bearer {KEY}"},
        params={"year": int(year)},
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    path.write_text(json.dumps(payload, indent=2))
    time.sleep(0.25)
    return payload


provider_rows = []
game_rows = []

for year in YEARS:
    payload = fetch_year(year)
    print(year, "games_with_line_payloads", len(payload))
    for game in payload:
        base = {
            "game_id": game.get("id"),
            "season": game.get("season"),
            "season_type": game.get("seasonType"),
            "week": game.get("week"),
            "start": game.get("startDate"),
            "home_team_id": game.get("homeTeamId"),
            "home_team": game.get("homeTeam"),
            "away_team_id": game.get("awayTeamId"),
            "away_team": game.get("awayTeam"),
            "home_score": game.get("homeScore"),
            "away_score": game.get("awayScore"),
        }
        valid_books = []
        for line in game.get("lines") or []:
            row = {
                **base,
                "provider": line.get("provider"),
                "spread": line.get("spread"),
                "spread_open": line.get("spreadOpen"),
                "over_under": line.get("overUnder"),
                "over_under_open": line.get("overUnderOpen"),
                "home_moneyline": line.get("homeMoneyline"),
                "away_moneyline": line.get("awayMoneyline"),
            }
            home_imp = implied(row["home_moneyline"])
            away_imp = implied(row["away_moneyline"])
            if home_imp is not None and away_imp is not None:
                overround = home_imp + away_imp
                row["moneyline_overround"] = overround
                row["home_fair_probability"] = (
                    home_imp / overround
                    if MIN_OVERROUND <= overround <= MAX_OVERROUND
                    else None
                )
                row["away_fair_probability"] = (
                    away_imp / overround
                    if MIN_OVERROUND <= overround <= MAX_OVERROUND
                    else None
                )
                if row["home_fair_probability"] is not None:
                    valid_books.append(row)
            else:
                row["moneyline_overround"] = None
                row["home_fair_probability"] = None
                row["away_fair_probability"] = None
            provider_rows.append(row)

        if not valid_books:
            continue

        home_probs = [r["home_fair_probability"] for r in valid_books]
        holds = [r["moneyline_overround"] - 1.0 for r in valid_books]
        best_home, best_home_book = best_price(valid_books, "home_moneyline")
        best_away, best_away_book = best_price(valid_books, "away_moneyline")
        home_fair = float(median(home_probs))
        game_rows.append({
            **base,
            "paired_provider_count": len(valid_books),
            "providers": "|".join(sorted({
                str(r.get("provider") or "").strip()
                for r in valid_books
                if str(r.get("provider") or "").strip()
            })),
            "home_fair_probability": home_fair,
            "away_fair_probability": 1.0 - home_fair,
            "home_fair_probability_mad": mad(home_probs),
            "median_hold": float(median(holds)),
            "best_home_moneyline": best_home,
            "best_home_book": best_home_book,
            "best_away_moneyline": best_away,
            "best_away_book": best_away_book,
        })

provider_df = pd.DataFrame(provider_rows)
consensus_df = pd.DataFrame(game_rows)

provider_out = DERIVED / "CFB_HISTORICAL_LINES_PROVIDER.csv"
consensus_out = DERIVED / "CFB_HISTORICAL_MONEYLINE_CONSENSUS.csv"
provider_df.to_csv(provider_out, index=False)
consensus_df.to_csv(consensus_out, index=False)

summary = {
    "years": YEARS,
    "provider_rows": int(len(provider_df)),
    "games_with_valid_two_sided_moneyline": int(len(consensus_df)),
    "paired_provider_count_distribution": (
        consensus_df["paired_provider_count"].value_counts().sort_index().to_dict()
        if not consensus_df.empty
        else {}
    ),
    "reasonable_overround_range": [MIN_OVERROUND, MAX_OVERROUND],
    "method": "SAME_PROVIDER_TWO_SIDED_PROPORTIONAL_DEVIG_THEN_MEDIAN_ACROSS_PROVIDERS",
    "rules": [
        "Home and away moneylines are paired only within the same provider.",
        "Each provider is de-vigged before consensus aggregation.",
        "Provider pairs outside the configured overround range are excluded.",
        "Consensus probability and best executable price are stored separately.",
        "Raw API responses are cached by season and reused on later runs.",
    ],
}
(META / "CFB_HISTORICAL_LINES_SUMMARY.json").write_text(
    json.dumps(summary, indent=2, default=str)
)
print(json.dumps(summary, indent=2, default=str))
