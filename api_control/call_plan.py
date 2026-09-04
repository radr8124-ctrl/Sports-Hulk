from pathlib import Path
from datetime import datetime, timezone
import json
import math

from api_budget import provider_budget

ROOT = Path("/home/ubuntu/sports-hulk")
FEED_CONFIG = ROOT / "api_control" / "feed_budget_config.json"


def load_feed_config():
    return json.loads(FEED_CONFIG.read_text())


def hours_between_calls(daily_calls):
    if daily_calls <= 0:
        return None

    return 24.0 / daily_calls


def build_plan():
    cfg = load_feed_config()
    plans = []

    for provider, pcfg in cfg.items():

        budget = provider_budget(provider)

        if not budget.get("known_limit"):
            plans.append({
                "provider": provider,
                "feed": "ALL",
                "status": "LIMIT UNKNOWN",
            })
            continue

        safe_daily = float(
            budget.get("safe_daily_budget") or 0
        )

        usable_remaining = float(
            budget.get("usable_remaining") or 0
        )

        for feed, fcfg in pcfg["feeds"].items():

            share = float(
                fcfg.get("share_pct", 0)
            ) / 100.0

            cost = float(
                fcfg.get("estimated_cost", 1)
            )

            feed_daily_credits = safe_daily * share
            feed_remaining_credits = usable_remaining * share

            daily_calls = (
                feed_daily_credits / cost
                if cost > 0
                else 0
            )

            remaining_calls = (
                math.floor(feed_remaining_credits / cost)
                if cost > 0
                else 0
            )

            interval_hours = hours_between_calls(
                daily_calls
            )

            plans.append({
                "provider": provider,
                "feed": feed,
                "priority": fcfg.get(
                    "priority",
                    "MEDIUM"
                ),
                "estimated_cost": cost,
                "share_pct": fcfg.get(
                    "share_pct"
                ),
                "daily_credit_budget":
                    feed_daily_credits,
                "allowed_calls_per_day":
                    daily_calls,
                "minimum_interval_hours":
                    interval_hours,
                "remaining_safe_calls":
                    remaining_calls,
                "serves":
                    fcfg.get("serves", []),
                "status": "ACTIVE",
            })

    return plans


def recommended_interval_hours(
    provider,
    feed
):
    for row in build_plan():
        if (
            row.get("provider") == provider
            and row.get("feed") == feed
        ):
            return row.get(
                "minimum_interval_hours"
            )

    return None


if __name__ == "__main__":

    print("=" * 96)
    print("SPORTS HULK API CALL PLAN")
    print("=" * 96)

    for row in build_plan():

        print()

        if row.get("status") != "ACTIVE":

            print(
                f"{row['provider']} / "
                f"{row['feed']}: "
                f"{row['status']}"
            )
            continue

        print(
            f"PROVIDER: {row['provider']}"
        )

        print(
            f"FEED: {row['feed']}"
        )

        print(
            f"PRIORITY: {row['priority']}"
        )

        print(
            f"API COST/CALL: "
            f"{row['estimated_cost']:.1f}"
        )

        print(
            f"BUDGET SHARE: "
            f"{row['share_pct']}%"
        )

        print(
            "SAFE CREDITS/DAY: "
            f"{row['daily_credit_budget']:.2f}"
        )

        print(
            "SAFE CALLS/DAY: "
            f"{row['allowed_calls_per_day']:.2f}"
        )

        interval = row[
            "minimum_interval_hours"
        ]

        if interval:
            print(
                "MINIMUM NORMAL INTERVAL: "
                f"{interval:.1f} hours"
            )

        print(
            "SAFE CALLS LEFT THIS MONTH: "
            f"{row['remaining_safe_calls']}"
        )

        print(
            "ONE CALL SERVES:"
        )

        for item in row["serves"]:
            print(f"  - {item}")

    print()
    print("=" * 96)
    print(
        "RULE: PAGE VIEWS NEVER CALL AN API."
    )
    print(
        "RULE: SURVIVOR REUSES NFL CORE DATA."
    )
    print(
        "RULE: BETTING REUSES SPORT DATA."
    )
    print(
        "RULE: SAVED SNAPSHOTS ARE NEVER "
        "DISCARDED BECAUSE A NEW CALL IS BLOCKED."
    )
    print("=" * 96)
