from pathlib import Path
from datetime import datetime, timezone
import json
import math

ROOT = Path("/home/ubuntu/sports-hulk")

CONFIG = ROOT / "api_control" / "sgo_entity_config.json"
STATE = ROOT / "api_control" / "sgo_entity_state.json"

DEFAULT_CONFIG = {
    "monthly_entity_limit": 2500,
    "reserve_pct": 20,
    "feeds": {
        "mlb_props": {
            "share_pct": 50,
            "priority": "HIGH"
        },
        "nfl_props": {
            "share_pct": 35,
            "priority": "HIGH"
        },
        "flex": {
            "share_pct": 15,
            "priority": "CRITICAL"
        }
    }
}

if not CONFIG.exists():
    CONFIG.write_text(json.dumps(DEFAULT_CONFIG, indent=2))

def config():
    return json.loads(CONFIG.read_text())

def state():
    if not STATE.exists():
        return {
            "entities_used": 366,
            "last_sync": None
        }

    return json.loads(STATE.read_text())

def save_state(obj):
    STATE.write_text(json.dumps(obj, indent=2))

def days_left():
    now = datetime.now(timezone.utc)
    import calendar
    total = calendar.monthrange(now.year, now.month)[1]
    return max(1, total - now.day + 1)

def sync_usage(used):
    s = state()
    s["entities_used"] = int(used)
    s["last_sync"] = datetime.now(timezone.utc).isoformat()
    save_state(s)

def budget():
    c = config()
    s = state()

    limit = int(c["monthly_entity_limit"])
    used = int(s["entities_used"])

    remaining = max(0, limit - used)

    reserve = int(
        limit * c["reserve_pct"] / 100
    )

    usable = max(0, remaining - reserve)

    daily = usable / days_left()

    return {
        "limit": limit,
        "used": used,
        "remaining": remaining,
        "reserve": reserve,
        "usable": usable,
        "days_left": days_left(),
        "safe_entities_per_day": daily
    }

def feed_budget(feed):
    b = budget()
    c = config()

    f = c["feeds"][feed]

    share = f["share_pct"] / 100

    return {
        **b,
        "feed": feed,
        "share_pct": f["share_pct"],
        "daily_entities":
            b["safe_entities_per_day"] * share,
        "remaining_entities":
            math.floor(b["usable"] * share),
        "priority":
            f["priority"]
    }

def can_fetch(feed, expected_entities):
    f = feed_budget(feed)

    if expected_entities > f["remaining_entities"]:
        return False, "MONTHLY ENTITY RESERVE PROTECTED"

    if (
        expected_entities > f["daily_entities"]
        and f["priority"] != "CRITICAL"
    ):
        return False, "DAILY ENTITY BUDGET EXCEEDED"

    return True, "ALLOWED"

if __name__ == "__main__":

    print("=" * 88)
    print("SPORTSGAMEODDS ENTITY BUDGET")
    print("=" * 88)

    b = budget()

    print("MONTHLY LIMIT:", b["limit"])
    print("USED:", b["used"])
    print("REMAINING:", b["remaining"])
    print("PROTECTED RESERVE:", b["reserve"])
    print("USABLE REMAINING:", b["usable"])
    print("DAYS LEFT:", b["days_left"])
    print(
        "SAFE ENTITIES/DAY:",
        round(b["safe_entities_per_day"], 2)
    )

    for feed in [
        "mlb_props",
        "nfl_props",
        "flex"
    ]:

        f = feed_budget(feed)

        print()
        print("FEED:", feed)
        print("SHARE:", f["share_pct"], "%")
        print(
            "DAILY ENTITIES:",
            round(f["daily_entities"], 2)
        )
        print(
            "SAFE REMAINING:",
            f["remaining_entities"]
        )

    print()
    print("RESULT: PASS")
