import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path("/home/ubuntu/sports-hulk")
load_dotenv(ROOT / ".env")

from api_budget import (
    load_config,
    update_provider_headers,
)

CONFIG = ROOT / "api_control" / "api_budget_config.json"


def show(name, status, details):
    print(f"{name}: {status}")
    print(details)
    print("-" * 72)


# ============================================================
# THE ODDS API
# ============================================================

try:
    key = os.getenv("THE_ODDS_API_KEY")

    r = requests.get(
        "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/",
        params={
            "apiKey": key,
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "american",
        },
        timeout=20,
    )

    used = r.headers.get("x-requests-used")
    remaining = r.headers.get("x-requests-remaining")
    last = r.headers.get("x-requests-last")

    if r.status_code == 200 and used is not None and remaining is not None:

        update_provider_headers(
            "the_odds_api",
            used=float(used),
            remaining=float(remaining),
            last_cost=float(last or 1),
        )

        total = float(used) + float(remaining)

        cfg = json.loads(CONFIG.read_text())
        cfg["providers"]["the_odds_api"]["monthly_limit"] = total
        CONFIG.write_text(json.dumps(cfg, indent=2, sort_keys=True))

        show(
            "The Odds API",
            "PASS",
            f"used={used} remaining={remaining} "
            f"last_cost={last} inferred_limit={total}"
        )

    else:
        show(
            "The Odds API",
            "FAIL",
            f"HTTP {r.status_code}"
        )

except Exception as e:
    show("The Odds API", "FAIL", repr(e))


# ============================================================
# OTHER PROVIDERS
# We only inspect safely here. No quota numbers are invented.
# ============================================================

providers = {
    "sportsgameodds": "SPORTSGAMEODDS_API_KEY",
    "therundown": "THERUNDOWN_API_KEY",
    "propline": "PROPLINE_API_KEY",
    "balldontlie": "BALLDONTLIE_API_KEY",
    "cfbd": "COLLEGEFOOTBALLDATA_API_KEY",
}

for provider, env_key in providers.items():

    present = bool(os.getenv(env_key))

    show(
        provider,
        "KEY PRESENT" if present else "NO KEY",
        "Quota sync pending provider-specific usage endpoint/header."
    )


print()
print("SYNC COMPLETE")
