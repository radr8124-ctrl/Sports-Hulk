from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
OUTS = [
    ROOT / "commercial_web" / "public" / "nfl_intelligence.json",
    ROOT / "commercial_web" / "dist" / "nfl_intelligence.json",
]


def age_hours(value):
    ts = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(ts):
        return None
    return round((pd.Timestamp.now(tz="UTC") - ts).total_seconds() / 3600, 1)


def csv_freshness(path, time_col):
    p = ROOT / path
    if not p.exists():
        return {"status": "MISSING", "rows": 0, "latest": None, "age_hours": None}
    try:
        df = pd.read_csv(p)
    except Exception:
        return {"status": "ERROR", "rows": 0, "latest": None, "age_hours": None}
    if df.empty or time_col not in df.columns:
        return {"status": "EMPTY", "rows": len(df), "latest": None, "age_hours": None}
    latest = pd.to_datetime(df[time_col], errors="coerce", utc=True).max()
    if pd.isna(latest):
        return {"status": "UNKNOWN", "rows": len(df), "latest": None, "age_hours": None}
    hours = round((pd.Timestamp.now(tz="UTC") - latest).total_seconds() / 3600, 1)
    status = "CURRENT" if hours <= 6 else "AGING" if hours <= 24 else "STALE"
    return {"status": status, "rows": len(df), "latest": latest.isoformat(), "age_hours": hours}


def main():
    sources = {
        "market": csv_freshness("nfl_live/derived/NFL_LIVE_MARKET.csv", "collected_at"),
        "survivor": csv_freshness("nfl_live/derived/NFL_SURVIVOR_HULK_DECISION.csv", "collected_at"),
        "props": csv_freshness("nfl_live/fusion/NFL_PROP_CONTEXT_IDENTITY_LOCKED.csv", "newest_update"),
        "prop_intelligence": csv_freshness("nfl_live/decision/NFL_PROP_FINALISTS.csv", "newest_update"),
    }
    overall = "READY"
    blockers = []
    for name, info in sources.items():
        if info["status"] in {"MISSING", "ERROR", "EMPTY", "UNKNOWN"}:
            blockers.append(f"{name}: {info['status']}")
        elif info["status"] == "STALE":
            blockers.append(f"{name}: STALE")

    if blockers:
        overall = "SOURCE ISSUE"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall,
        "sources": sources,
        "decision_gate": {
            "status": "PASS-FIRST",
            "rule": "No current pick, prop, parlay or survivor recommendation may render from stale or unverified source data.",
            "blockers": blockers,
        },
    }

    text = json.dumps(payload, indent=2)
    for target in OUTS:
        if target.parent.exists():
            target.write_text(text)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
