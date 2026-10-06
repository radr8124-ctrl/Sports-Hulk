from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "nfl_live" / "derived"

DECISION = OUT / "NFL_SURVIVOR_HULK_DECISION.csv"
SCHEDULE = OUT / "NFLVERSE_2026_SCHEDULE.csv"

if not DECISION.exists():
    raise SystemExit("Decision board missing")

if not SCHEDULE.exists():
    raise SystemExit("NFLverse schedule missing")

board = pd.read_csv(DECISION)
games = pd.read_csv(SCHEDULE)

board["start"] = pd.to_datetime(
    board["start"],
    utc=True,
    errors="coerce",
)

games["gameday"] = pd.to_datetime(
    games["gameday"],
    errors="coerce",
)

TEAM_MAP = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS",
}

REV = {v: k for k, v in TEAM_MAP.items()}


def num(v):
    try:
        return float(v)
    except Exception:
        return np.nan


first_game = board["start"].min()

completed = games[
    (games["gameday"] < first_game.tz_convert(None).normalize())
    & games["home_score"].notna()
    & games["away_score"].notna()
].copy()

# Derive the current week from the matchups actually on the Survivor board.
# This avoids advancing to the next week after a Thursday game has finished
# while the rest of the same NFL week is still upcoming.
board_weeks = []
board_actual_weeks = []
for _, r in board.iterrows():
    team = TEAM_MAP.get(r.get("survivor_team"))
    opp = TEAM_MAP.get(r.get("opponent"))
    matched_week = np.nan
    if team and opp:
        hit = games[
            (((games["home_team"] == team) & (games["away_team"] == opp))
             | ((games["away_team"] == team) & (games["home_team"] == opp)))
            & (games["game_type"] == "REG")
        ]
        if not hit.empty:
            board_start = pd.to_datetime(
                r.get("start"),
                errors="coerce",
                utc=True,
            )
            if pd.notna(board_start):
                hit = hit.copy()
                hit["_date_distance"] = (
                    pd.to_datetime(
                        hit["gameday"],
                        errors="coerce",
                    )
                    - board_start.tz_convert(
                        None
                    ).normalize()
                ).abs()
                hit = hit.sort_values(
                    "_date_distance"
                )
            weeks = pd.to_numeric(
                hit["week"],
                errors="coerce",
            ).dropna().astype(int)
            if not weeks.empty:
                matched_week = int(weeks.iloc[0])
                board_weeks.append(matched_week)
    board_actual_weeks.append(matched_week)

if board_weeks:
    current_week = int(pd.Series(board_weeks).mode().iloc[0])
elif completed.empty:
    current_week = 1
else:
    current_week = int(completed["week"].max()) + 1

print("CURRENT NFL WEEK:", current_week)

board = board.copy()
board["_actual_week"] = board_actual_weeks
board = board[
    pd.to_numeric(
        board["_actual_week"],
        errors="coerce",
    ).eq(current_week)
].copy()
board = board.drop(
    columns=["_actual_week"],
    errors="ignore",
)

print("CURRENT WEEK BOARD ROWS:", len(board))


def current_record(team):
    t = completed[
        (completed["home_team"] == team)
        | (completed["away_team"] == team)
    ]

    wins = 0
    played = 0

    for _, g in t.iterrows():
        home = g["home_team"] == team

        pts = num(
            g["home_score"] if home else g["away_score"]
        )

        opp = num(
            g["away_score"] if home else g["home_score"]
        )

        if pd.isna(pts) or pd.isna(opp):
            continue

        played += 1

        if pts > opp:
            wins += 1

    return (
        wins / played if played else np.nan
    )


future = games[
    (games["week"] > current_week)
    & (games["week"] <= current_week + 4)
    & (games["game_type"] == "REG")
].copy()


rows = []

for _, r in board.iterrows():
    team_name = r["survivor_team"]
    team = TEAM_MAP.get(team_name)

    team_future = future[
        (future["home_team"] == team)
        | (future["away_team"] == team)
    ].sort_values(["week", "gameday"])

    strong_spots = 0
    viable_spots = 0
    home_weak_spots = 0
    descriptions = []

    for _, g in team_future.iterrows():

        is_home = g["home_team"] == team

        opp = (
            g["away_team"]
            if is_home
            else g["home_team"]
        )

        team_ml = num(
            g["home_moneyline"]
            if is_home
            else g["away_moneyline"]
        )

        opp_wp = current_record(opp)

        if not pd.isna(team_ml):
            if team_ml <= -200:
                strong_spots += 1
            elif team_ml <= -150:
                viable_spots += 1

        if (
            is_home
            and not pd.isna(opp_wp)
            and opp_wp <= .25
        ):
            home_weak_spots += 1

        place = "H" if is_home else "A"

        descriptions.append(
            f"W{int(g['week'])} "
            f"{place} vs {REV.get(opp, opp)}"
        )

    future_index = (
        strong_spots * 25
        + viable_spots * 15
        + home_weak_spots * 10
    )

    future_index = float(
        np.clip(future_index, 0, 100)
    )

    if future_index >= 45:
        value_label = "SAVE_VALUE"
    elif future_index >= 20:
        value_label = "SOME_FUTURE_VALUE"
    else:
        value_label = "LOW_FUTURE_VALUE"

    context = num(r.get("hulk_context_score"))

    # Separate strategy index.
    # Not a win probability.
    strategy_index = (
        context - (future_index * 0.15)
        if not pd.isna(context)
        else np.nan
    )

    tier = str(
        r.get("hulk_decision_tier", "")
    )

    disagreement = str(
        r.get("hulk_disagreement", "")
    )

    if disagreement == "HULK_MAJOR_WARNING":
        action = "AVOID"
    elif (
        tier in {"TOP_TIER", "STRONG"}
        and future_index < 20
    ):
        action = "USE_NOW_VALUE"
    elif (
        tier in {"TOP_TIER", "STRONG"}
        and future_index >= 45
    ):
        action = "STRONG_BUT_SAVE_VALUE"
    elif tier in {"TOP_TIER", "STRONG"}:
        action = "STRONG_OPTION"
    elif tier == "VIABLE":
        action = "VIABLE"
    else:
        action = "WATCH"

    out = r.to_dict()

    out.update({
        "current_week": current_week,
        "future_window_weeks": 4,
        "future_strong_spots": strong_spots,
        "future_viable_spots": viable_spots,
        "future_home_vs_weak": home_weak_spots,
        "future_value_index": round(
            future_index, 1
        ),
        "future_value_label": value_label,
        "next_four_week_schedule":
            " | ".join(descriptions),
        "strategy_index": (
            round(strategy_index, 1)
            if not pd.isna(strategy_index)
            else None
        ),
        "strategy_action": action,
    })

    rows.append(out)


result = pd.DataFrame(rows)

result = result.sort_values(
    [
        "strategy_index",
        "market_prob_pct",
    ],
    ascending=[False, False],
)

result.to_csv(
    OUT / "NFL_SURVIVOR_HULK_STRATEGY.csv",
    index=False,
)

result.to_parquet(
    OUT / "NFL_SURVIVOR_HULK_STRATEGY.parquet",
    index=False,
)

print()
print("=" * 120)
print("SPORTS HULK — FUTURE VALUE STRATEGY")
print("=" * 120)

cols = [
    "survivor_team",
    "market_prob_pct",
    "hulk_context_score",
    "future_value_index",
    "future_value_label",
    "strategy_index",
    "strategy_action",
    "next_four_week_schedule",
]

print(result[cols].to_string(index=False))

print()
print("Strategy Index is NOT a win probability.")
print("RESULT: FUTURE_VALUE_READY")
