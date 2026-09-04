from pathlib import Path
from datetime import datetime, timezone
import json
import os
import requests
from dotenv import load_dotenv

ROOT = Path("/home/ubuntu/sports-hulk")
load_dotenv(ROOT / ".env")

STATE = ROOT / "api_control" / "sgo_entity_state.json"
KEY = os.getenv("SPORTSGAMEODDS_API_KEY")

def load_state():
    if not STATE.exists():
        return {
            "entities_used": 0,
            "last_sync": None,
            "last_delta": 0
        }
    return json.loads(STATE.read_text())

def save_state(s):
    STATE.write_text(json.dumps(s, indent=2))

def live_used():
    r = requests.get(
        "https://api.sportsgameodds.com/v2/account/usage",
        headers={"X-API-Key": KEY},
        timeout=20,
    )

    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")

    data = r.json().get("data", {})
    monthly = data.get("rateLimits", {}).get("per-month", {})

    used = monthly.get(
        "currentIntervalEntities",
        monthly.get("current-entities")
    )

    if used is None:
        raise RuntimeError("Monthly entity usage missing")

    return int(used)

def sync():
    s = load_state()

    old = int(s.get("entities_used", 0))
    new = live_used()

    delta = max(0, new - old)

    s["previous_entities_used"] = old
    s["entities_used"] = new
    s["last_delta"] = delta
    s["last_sync"] = datetime.now(timezone.utc).isoformat()

    save_state(s)

    return old, new, delta

if __name__ == "__main__":
    old, new, delta = sync()

    print("=" * 80)
    print("SPORTSGAMEODDS USAGE SYNC")
    print("=" * 80)
    print("PREVIOUS USED:", old)
    print("CURRENT USED:", new)
    print("DELTA SINCE LAST SYNC:", delta)
    print("RESULT: PASS")
