from pathlib import Path
import os
import json
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

KEY = os.getenv("COLLEGEFOOTBALLDATA_API_KEY", "").strip()

if not KEY:
    raise SystemExit("COLLEGEFOOTBALLDATA_API_KEY missing")

BASE = "https://api.collegefootballdata.com"
HEADERS = {"Authorization": f"Bearer {KEY}"}

TEST_YEAR = 2025

tests = [
    (
        "historical_games",
        "/games",
        {
            "year": TEST_YEAR,
            "seasonType": "both",
            "classification": "fbs",
        },
    ),
    (
        "core_ratings",
        "/ratings/core",
        {
            "year": TEST_YEAR,
        },
    ),
    (
        "srs_ratings",
        "/ratings/srs",
        {
            "year": TEST_YEAR,
        },
    ),
    (
        "elo_ratings",
        "/ratings/elo",
        {
            "year": TEST_YEAR,
            "seasonType": "both",
        },
    ),
]

results = {}

print("=" * 72)
print("SPORTS HULK CFB HISTORICAL DATA AUDIT")
print("=" * 72)

for name, path, params in tests:
    print(f"\nTEST: {name}")
    print(f"GET {path}")

    try:
        r = requests.get(
            BASE + path,
            headers=HEADERS,
            params=params,
            timeout=90,
        )

        print("STATUS:", r.status_code)

        if r.status_code == 200:
            payload = r.json()
            count = len(payload) if isinstance(payload, list) else 1

            print("ROWS:", count)

            results[name] = {
                "status": 200,
                "rows": count,
            }

            out = (
                ROOT
                / "college_vault"
                / "raw"
                / f"audit_{name}_{TEST_YEAR}.json"
            )

            out.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )

            if isinstance(payload, list) and payload:
                print(
                    "SAMPLE KEYS:",
                    sorted(payload[0].keys())[:30]
                )

        else:
            text = r.text[:500].replace("\n", " ")
            print("RESPONSE:", text)

            results[name] = {
                "status": r.status_code,
                "response": text,
            }

    except Exception as e:
        print("ERROR:", e)

        results[name] = {
            "status": "ERROR",
            "response": str(e),
        }


# One team-box-score test by week.
# Current CFBD rules require week/team/conference with year.
print("\nTEST: team_box_scores")
try:
    r = requests.get(
        BASE + "/games/teams",
        headers=HEADERS,
        params={
            "year": TEST_YEAR,
            "week": 1,
            "seasonType": "regular",
            "classification": "fbs",
        },
        timeout=90,
    )

    print("STATUS:", r.status_code)

    if r.status_code == 200:
        payload = r.json()
        print("ROWS:", len(payload))

        results["team_box_scores"] = {
            "status": 200,
            "rows": len(payload),
        }

        out = (
            ROOT
            / "college_vault"
            / "raw"
            / f"audit_team_box_scores_{TEST_YEAR}_week1.json"
        )

        out.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

        if payload:
            print(
                "SAMPLE KEYS:",
                sorted(payload[0].keys())[:30]
            )

    else:
        text = r.text[:500].replace("\n", " ")
        print("RESPONSE:", text)

        results["team_box_scores"] = {
            "status": r.status_code,
            "response": text,
        }

except Exception as e:
    print("ERROR:", e)

    results["team_box_scores"] = {
        "status": "ERROR",
        "response": str(e),
    }


meta = (
    ROOT
    / "college_vault"
    / "meta"
    / "CFB_HISTORICAL_AUDIT.json"
)

meta.write_text(
    json.dumps(results, indent=2),
    encoding="utf-8",
)

print("\n" + "=" * 72)
print("AUDIT SUMMARY")
print("=" * 72)

for k, v in results.items():
    print(
        f"{k:22} "
        f"status={v.get('status')} "
        f"rows={v.get('rows', '-')}"
    )

good = sum(
    1 for v in results.values()
    if v.get("status") == 200
)

print()
print(f"WORKING ENDPOINTS: {good}/{len(results)}")
print("AUDIT FILE:", meta)
print("=" * 72)
