from pathlib import Path
import os
import json
import time
import requests
import pandas as pd
from dotenv import load_dotenv

ROOT = Path("/home/ubuntu/sports-hulk")
VAULT = ROOT / "college_vault"
RAW = VAULT / "raw"
DERIVED = VAULT / "derived"
META = VAULT / "meta"

for p in (RAW, DERIVED, META):
    p.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env", override=True)

KEY = os.getenv("COLLEGEFOOTBALLDATA_API_KEY", "").strip()
BASE = "https://api.collegefootballdata.com"
HEADERS = {"Authorization": f"Bearer {KEY}"}

YEARS = list(range(2016, 2027))

def get(path, params):
    r = requests.get(
        BASE + path,
        headers=HEADERS,
        params=params,
        timeout=90,
    )
    r.raise_for_status()
    time.sleep(0.25)
    return r.json()

all_games = []
all_core = []
all_srs = []
all_elo = []

print("=" * 72)
print("SPORTS HULK CFB HISTORICAL BACKFILL")
print("=" * 72)

for year in YEARS:
    print(f"\n=== {year} ===")

    games = get(
        "/games",
        {
            "year": year,
            "seasonType": "both",
            "classification": "fbs",
        },
    )

    print("games:", len(games))

    for row in games:
        row["source_year"] = year
    all_games.extend(games)

    (RAW / f"games_{year}.json").write_text(
        json.dumps(games, indent=2),
        encoding="utf-8",
    )

    try:
        core = get("/ratings/core", {"year": year})
        print("core:", len(core))
        for row in core:
            row["source_year"] = year
        all_core.extend(core)

        (RAW / f"core_{year}.json").write_text(
            json.dumps(core, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print("core unavailable:", e)

    try:
        srs = get("/ratings/srs", {"year": year})
        print("srs:", len(srs))
        for row in srs:
            row["source_year"] = year
        all_srs.extend(srs)

        (RAW / f"srs_{year}.json").write_text(
            json.dumps(srs, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print("srs unavailable:", e)

    try:
        elo = get(
            "/ratings/elo",
            {
                "year": year,
                "seasonType": "both",
            },
        )
        print("elo:", len(elo))
        for row in elo:
            row["source_year"] = year
        all_elo.extend(elo)

        (RAW / f"elo_{year}.json").write_text(
            json.dumps(elo, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print("elo unavailable:", e)


print("\n=== BUILD MASTER TABLES ===")

games_df = pd.json_normalize(all_games)
core_df = pd.json_normalize(all_core)
srs_df = pd.json_normalize(all_srs)
elo_df = pd.json_normalize(all_elo)

games_csv = DERIVED / "CFB_GAMES_HISTORY.csv"
games_parquet = DERIVED / "CFB_GAMES_HISTORY.parquet"

games_df.to_csv(games_csv, index=False)
games_df.to_parquet(games_parquet, index=False)

if not core_df.empty:
    core_df.to_csv(DERIVED / "CFB_CORE_HISTORY.csv", index=False)
    core_df.to_parquet(DERIVED / "CFB_CORE_HISTORY.parquet", index=False)

if not srs_df.empty:
    srs_df.to_csv(DERIVED / "CFB_SRS_HISTORY.csv", index=False)
    srs_df.to_parquet(DERIVED / "CFB_SRS_HISTORY.parquet", index=False)

if not elo_df.empty:
    elo_df.to_csv(DERIVED / "CFB_ELO_HISTORY.csv", index=False)
    elo_df.to_parquet(DERIVED / "CFB_ELO_HISTORY.parquet", index=False)

summary = {
    "years": YEARS,
    "games_rows": len(games_df),
    "core_rows": len(core_df),
    "srs_rows": len(srs_df),
    "elo_rows": len(elo_df),
}

(META / "CFB_BACKFILL_SUMMARY.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8",
)

print()
print("=" * 72)
print("BACKFILL SUMMARY")
print("=" * 72)
print("YEARS:", f"{YEARS[0]}-{YEARS[-1]}")
print("GAMES:", len(games_df))
print("CORE:", len(core_df))
print("SRS:", len(srs_df))
print("ELO:", len(elo_df))
print("OUTPUT:", DERIVED)
print("RESULT: PASS")
print("=" * 72)
