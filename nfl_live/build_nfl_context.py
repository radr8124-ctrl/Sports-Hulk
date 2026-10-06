from pathlib import Path
from datetime import datetime, timezone
import json
import requests
import pandas as pd
import sys

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "nfl_live" / "derived"
CACHE = ROOT / "nfl_live" / "context_cache"

OUT.mkdir(parents=True, exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))

from connectors.espn_public import ESPNPublicClient


MARKET_PATH = OUT / "NFL_LIVE_MARKET.csv"
SURVIVOR_PATH = OUT / "NFL_SURVIVOR_BOARD.csv"

if not MARKET_PATH.exists():
    raise SystemExit("NFL_LIVE_MARKET.csv missing")

if not SURVIVOR_PATH.exists():
    raise SystemExit("NFL_SURVIVOR_BOARD.csv missing")


def norm_team(value):
    return str(value or "").strip().lower()


# ------------------------------------------------------------
# ESPN CURRENT CONTEXT
# ------------------------------------------------------------

espn = ESPNPublicClient()

score = espn.scoreboard()

print("ESPN HTTP:", score["http_status"])

if score["http_status"] != 200:
    print(score["text"])
    raise SystemExit("ESPN scoreboard failed")

data = score["data"] or {}
events = data.get("events") or []

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

(CACHE / f"ESPN_NFL_SCOREBOARD_{stamp}.json").write_text(
    json.dumps(data, indent=2)
)

espn_rows = []

for event in events:
    competition = (event.get("competitions") or [{}])[0]

    competitors = competition.get("competitors") or []

    home = None
    away = None

    for comp in competitors:
        team = comp.get("team") or {}

        name = (
            team.get("displayName")
            or team.get("shortDisplayName")
            or team.get("name")
        )

        if comp.get("homeAway") == "home":
            home = name
        elif comp.get("homeAway") == "away":
            away = name

    venue = competition.get("venue") or {}
    address = venue.get("address") or {}

    status = event.get("status") or {}
    status_type = status.get("type") or {}

    espn_rows.append(
        {
            "espn_event_id": event.get("id"),
            "start": event.get("date"),
            "away_team": away,
            "home_team": home,
            "venue_name": venue.get("fullName"),
            "venue_city": address.get("city"),
            "venue_state": address.get("state"),
            "venue_indoor": venue.get("indoor"),
            "game_status": status_type.get("name"),
            "game_status_detail": status_type.get("detail"),
            "espn_completed": status_type.get("completed"),
            "espn_context_retrieved_at":
                datetime.now(timezone.utc).isoformat(),
        }
    )

espn_df = pd.DataFrame(espn_rows)

if not espn_df.empty:
    espn_df["start"] = pd.to_datetime(
        espn_df["start"],
        errors="coerce",
        utc=True,
    )

espn_df.to_csv(
    OUT / "NFL_ESPN_CONTEXT.csv",
    index=False,
)

print("ESPN events:", len(espn_df))


# ------------------------------------------------------------
# NFLVERSE SCHEDULE / BACKGROUND
# ------------------------------------------------------------

schedule_url = (
    "https://raw.githubusercontent.com/"
    "nflverse/nfldata/master/data/games.csv"
)

try:
    r = requests.get(
        schedule_url,
        timeout=30,
        headers={"User-Agent": "Sports-HULK/1.0"},
    )

    print("NFLVERSE SCHEDULE HTTP:", r.status_code)

    if r.status_code == 200:
        schedule_cache = (
            CACHE / f"NFLVERSE_SCHEDULES_{stamp}.csv"
        )
        schedule_cache.write_bytes(r.content)

        nv = pd.read_csv(schedule_cache)

        if "season" in nv.columns:
            nv = nv[nv["season"] == 2026].copy()

        nv.to_csv(
            OUT / "NFLVERSE_2026_SCHEDULE.csv",
            index=False,
        )

        print("NFLverse 2026 schedule rows:", len(nv))
    else:
        nv = pd.DataFrame()
        print("NFLverse schedule unavailable")
except Exception as exc:
    nv = pd.DataFrame()
    print("NFLverse warning:", exc)


# ------------------------------------------------------------
# JOIN CURRENT SURVIVOR BOARD TO ESPN
# ------------------------------------------------------------

survivor = pd.read_csv(SURVIVOR_PATH)
survivor["start"] = pd.to_datetime(
    survivor["start"],
    errors="coerce",
    utc=True,
)

if not espn_df.empty:

    survivor["_home"] = survivor["home_team"].map(norm_team)
    survivor["_away"] = survivor["away_team"].map(norm_team)

    espn_df["_home"] = espn_df["home_team"].map(norm_team)
    espn_df["_away"] = espn_df["away_team"].map(norm_team)

    context = survivor.merge(
        espn_df[
            [
                "_home",
                "_away",
                "espn_event_id",
                "venue_name",
                "venue_city",
                "venue_state",
                "venue_indoor",
                "game_status",
                "game_status_detail",
                "espn_context_retrieved_at",
            ]
        ],
        on=["_home", "_away"],
        how="left",
    )

    context = context.drop(
        columns=["_home", "_away"],
        errors="ignore",
    )
else:
    context = survivor.copy()


context["context_source"] = "espn+nflverse"

context.to_csv(
    OUT / "NFL_SURVIVOR_CONTEXT.csv",
    index=False,
)

print()
print("SURVIVOR CONTEXT ROWS:", len(context))

show_cols = [
    c for c in [
        "survivor_team",
        "away_team",
        "home_team",
        "survivor_win_prob",
        "survivor_spread",
        "market_source",
        "venue_name",
        "venue_city",
        "venue_state",
        "venue_indoor",
        "game_status_detail",
    ]
    if c in context.columns
]

show = context[show_cols].copy()

if "survivor_win_prob" in show.columns:
    show["survivor_win_prob"] = (
        show["survivor_win_prob"] * 100
    ).round(1)

print()
print(show.to_string(index=False))

print()
print("RESULT: CONTEXT_READY")
