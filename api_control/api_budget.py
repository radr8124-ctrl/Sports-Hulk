from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import calendar
import json
from typing import Optional

ROOT = Path("/home/ubuntu/sports-hulk")
STATE_DIR = ROOT / "api_control"
STATE_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = STATE_DIR / "api_budget_state.json"
CONFIG_FILE = STATE_DIR / "api_budget_config.json"


DEFAULT_CONFIG = {
    "reserve_pct": 20.0,
    "providers": {
        "the_odds_api": {
            "monthly_limit": None,
            "priority": "HIGH",
        },
        "sportsgameodds": {
            "monthly_limit": None,
            "priority": "HIGH",
        },
        "therundown": {
            "monthly_limit": None,
            "priority": "MEDIUM",
        },
        "propline": {
            "monthly_limit": None,
            "priority": "MEDIUM",
        },
        "balldontlie": {
            "monthly_limit": None,
            "priority": "LOW",
        },
        "cfbd": {
            "monthly_limit": None,
            "priority": "MEDIUM",
        },
    },
}


PRIORITY_FACTOR = {
    "CRITICAL": 1.50,
    "HIGH": 1.20,
    "MEDIUM": 1.00,
    "LOW": 0.70,
}


def utc_now():
    return datetime.now(timezone.utc)


def month_key(dt=None):
    dt = dt or utc_now()
    return f"{dt.year:04d}-{dt.month:02d}"


def days_remaining_in_month(dt=None):
    dt = dt or utc_now()
    total = calendar.monthrange(dt.year, dt.month)[1]
    return max(1, total - dt.day + 1)


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _save_json(path: Path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True))
    tmp.replace(path)


def ensure_config():
    if not CONFIG_FILE.exists():
        _save_json(CONFIG_FILE, DEFAULT_CONFIG)


def load_config():
    ensure_config()
    return _load_json(CONFIG_FILE, DEFAULT_CONFIG)


def load_state():
    return _load_json(
        STATE_FILE,
        {
            "month": month_key(),
            "providers": {},
        }
    )


def save_state(state):
    _save_json(STATE_FILE, state)


def reset_if_new_month(state):
    current = month_key()
    if state.get("month") != current:
        state = {
            "month": current,
            "providers": {},
        }
    return state


def get_provider_state(provider):
    state = reset_if_new_month(load_state())
    p = state["providers"].setdefault(
        provider,
        {
            "used": 0.0,
            "remaining_reported": None,
            "last_cost": None,
            "last_call_utc": None,
            "calls": 0,
        }
    )
    save_state(state)
    return state, p


def update_provider_headers(
    provider: str,
    used: Optional[float] = None,
    remaining: Optional[float] = None,
    last_cost: Optional[float] = None,
):
    state, p = get_provider_state(provider)

    if used is not None:
        p["used"] = float(used)

    if remaining is not None:
        p["remaining_reported"] = float(remaining)

    if last_cost is not None:
        p["last_cost"] = float(last_cost)

    save_state(state)


def record_call(
    provider: str,
    cost: float = 1.0,
    reported_used: Optional[float] = None,
    reported_remaining: Optional[float] = None,
):
    state, p = get_provider_state(provider)

    if reported_used is not None:
        p["used"] = float(reported_used)
    else:
        p["used"] = float(p.get("used", 0.0)) + float(cost)

    if reported_remaining is not None:
        p["remaining_reported"] = float(reported_remaining)

    p["last_cost"] = float(cost)
    p["last_call_utc"] = utc_now().isoformat()
    p["calls"] = int(p.get("calls", 0)) + 1

    save_state(state)


def provider_budget(provider: str):
    config = load_config()
    pconf = config["providers"].get(provider, {})
    monthly_limit = pconf.get("monthly_limit")
    priority = pconf.get("priority", "MEDIUM").upper()

    state, p = get_provider_state(provider)

    used = float(p.get("used", 0.0))
    reported_remaining = p.get("remaining_reported")

    reserve_pct = float(config.get("reserve_pct", 20.0))

    if monthly_limit is None and reported_remaining is not None:
        monthly_limit = used + float(reported_remaining)

    if monthly_limit is None:
        return {
            "provider": provider,
            "known_limit": False,
            "used": used,
            "remaining": reported_remaining,
            "reserve_pct": reserve_pct,
            "priority": priority,
            "days_left": days_remaining_in_month(),
            "safe_daily_budget": None,
            "usable_remaining": None,
        }

    monthly_limit = float(monthly_limit)

    if reported_remaining is not None:
        remaining = float(reported_remaining)
    else:
        remaining = max(0.0, monthly_limit - used)

    reserve_amount = monthly_limit * (reserve_pct / 100.0)
    usable_remaining = max(0.0, remaining - reserve_amount)

    safe_daily = usable_remaining / days_remaining_in_month()

    return {
        "provider": provider,
        "known_limit": True,
        "monthly_limit": monthly_limit,
        "used": used,
        "remaining": remaining,
        "reserve_pct": reserve_pct,
        "reserve_amount": reserve_amount,
        "priority": priority,
        "days_left": days_remaining_in_month(),
        "usable_remaining": usable_remaining,
        "safe_daily_budget": safe_daily,
    }


def can_call(
    provider: str,
    estimated_cost: float = 1.0,
    priority: Optional[str] = None,
):
    b = provider_budget(provider)

    if not b["known_limit"]:
        return True, "LIMIT UNKNOWN"

    effective_priority = (
        priority or b.get("priority", "MEDIUM")
    ).upper()

    factor = PRIORITY_FACTOR.get(effective_priority, 1.0)

    remaining = float(b["remaining"])
    reserve_amount = float(b["reserve_amount"])

    if remaining - estimated_cost < reserve_amount:
        return False, "RESERVE PROTECTED"

    safe_daily = float(b["safe_daily_budget"]) * factor

    # Conservative rule:
    # if one call alone exceeds today's safe allocation for this priority,
    # only CRITICAL calls are allowed.
    if estimated_cost > safe_daily and effective_priority != "CRITICAL":
        return False, "DAILY BUDGET TOO LOW"

    return True, "ALLOWED"


def status_rows():
    config = load_config()

    rows = []

    for provider in config["providers"]:
        b = provider_budget(provider)

        rows.append({
            "provider": provider,
            "priority": b.get("priority"),
            "known_limit": b.get("known_limit"),
            "used": b.get("used"),
            "remaining": b.get("remaining"),
            "reserve_pct": b.get("reserve_pct"),
            "days_left": b.get("days_left"),
            "safe_daily_budget": b.get("safe_daily_budget"),
        })

    return rows


if __name__ == "__main__":
    print("=" * 92)
    print("SPORTS HULK API BUDGET STATUS")
    print("=" * 92)

    for row in status_rows():
        print()
        print("PROVIDER:", row["provider"])
        print("PRIORITY:", row["priority"])
        print("KNOWN LIMIT:", row["known_limit"])
        print("USED:", row["used"])
        print("REMAINING:", row["remaining"])
        print("RESERVE %:", row["reserve_pct"])
        print("DAYS LEFT:", row["days_left"])
        print("SAFE DAILY:", row["safe_daily_budget"])

    print()
    print("=" * 92)
