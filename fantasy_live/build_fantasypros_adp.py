from pathlib import Path
from datetime import datetime, timezone
import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "fantasy_live" / "derived"
HISTORY = ROOT / "fantasy_live" / "history"

OUT.mkdir(parents=True, exist_ok=True)
HISTORY.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

KEY = os.getenv("FANTASYPROS_API_KEY")

if not KEY:
    raise SystemExit("FANTASYPROS_API_KEY missing")

URL = (
    "https://api.fantasypros.com/public/v2/json/"
    "nfl/2026/consensus-rankings"
)

rows = []

print("=" * 80)
print("SPORTS HULK FANTASYPROS ADP BUILD")
print("=" * 80)

for pos in ["QB","RB","WR","TE"]:

    r = requests.get(
        URL,
        headers={"x-api-key": KEY},
        params={
            "position": pos,
            "scoring": "PPR",
        },
        timeout=30,
    )

    print(pos, "HTTP:", r.status_code)

    if r.status_code != 200:
        print(r.text[:1000])
        continue

    data = r.json()

    players = (
        data.get("players")
        or data.get("rankings")
        or data.get("data")
        or []
    )

    for p in players:

        name = (
            p.get("player_name")
            or p.get("name")
            or p.get("player")
        )

        team = (
            p.get("player_team_id")
            or p.get("team")
            or p.get("team_id")
        )

        adp = (
            p.get("rank_adp")
            or p.get("adp")
            or p.get("avg_adp")
        )

        ecr = (
            p.get("rank_ecr")
            or p.get("ecr")
            or p.get("rank")
        )

        tier = (
            p.get("tier")
            or p.get("rank_tier")
        )

        rows.append({
            "player": name,
            "team": team,
            "position": pos,
            "fantasypros_adp": adp,
            "fantasypros_ecr": ecr,
            "fantasypros_tier": tier,
            "collected_at":
                datetime.now(timezone.utc).isoformat(),
        })

df = pd.DataFrame(rows)

for c in [
    "fantasypros_adp",
    "fantasypros_ecr",
    "fantasypros_tier",
]:
    if c in df.columns:
        df[c] = pd.to_numeric(
            df[c],
            errors="coerce"
        )

df = df.dropna(subset=["player"]).copy()

df = df.sort_values(
    ["fantasypros_adp","fantasypros_ecr"],
    na_position="last"
)

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

df.to_csv(
    OUT / "FANTASYPROS_ADP.csv",
    index=False
)

df.to_parquet(
    OUT / "FANTASYPROS_ADP.parquet",
    index=False
)

df.to_csv(
    HISTORY / f"FANTASYPROS_ADP_{stamp}.csv",
    index=False
)

print()
print("ROWS:", len(df))

print(
    df[
        [
            "player",
            "team",
            "position",
            "fantasypros_adp",
            "fantasypros_ecr",
            "fantasypros_tier",
        ]
    ].head(30).to_string(index=False)
)

print()
print("RESULT: PASS")
