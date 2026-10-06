from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/home/ubuntu/sports-hulk")
SRC = ROOT / "nfl_live" / "derived" / "NFL_LIVE_MARKET.csv"
OUT = ROOT / "nfl_live" / "derived"

df = pd.read_csv(SRC)

df["start"] = pd.to_datetime(
    df["start"],
    errors="coerce",
    utc=True
)

now = pd.Timestamp.now(tz="UTC")

# ------------------------------------------------------------
# FUTURE GAMES ONLY
# ------------------------------------------------------------

df = df[df["start"] >= now].copy()

if df.empty:
    raise SystemExit("NO FUTURE NFL GAMES FOUND")

# ------------------------------------------------------------
# CLEAN OBVIOUSLY INVALID AMERICAN ODDS
# valid American prices should generally be <= -100 or >= +100
# ------------------------------------------------------------

def clean_price(v):
    try:
        x = float(v)
    except:
        return np.nan

    if x <= -100 or x >= 100:
        return x

    return np.nan

df["home_moneyline"] = df["home_moneyline"].apply(clean_price)
df["away_moneyline"] = df["away_moneyline"].apply(clean_price)

# ------------------------------------------------------------
# CURRENT / NEXT NFL SLATE
# Start with the first upcoming game and capture 7 days
# ------------------------------------------------------------

first_start = df["start"].min()

# ------------------------------------------------------------
# CURRENT NFL WEEK BOUNDARY
#
# Anchor the remaining slate to the first upcoming Sunday.
# Keep future games through early Tuesday ET so Sunday games
# and Monday Night Football remain included, but the following
# Thursday/Sunday do not leak into this week's Survivor board.
# ------------------------------------------------------------

start_et = df["start"].dt.tz_convert("America/New_York")

sunday_mask = start_et.dt.weekday == 6

if sunday_mask.any():
    first_sunday = start_et[sunday_mask].min()
    sunday_date = first_sunday.normalize()

    slate_end_et = (
        sunday_date
        + pd.Timedelta(days=2)
        + pd.Timedelta(hours=6)
    )

    slate_end = slate_end_et.tz_convert("UTC")
else:
    # Conservative fallback if no Sunday game is present.
    slate_end = first_start + pd.Timedelta(days=3)

week = df[
    (df["start"] >= now) &
    (df["start"] < slate_end)
].copy()

week = week.sort_values("start")

# ------------------------------------------------------------
# MONEYLINE -> IMPLIED WIN PROBABILITY
# ------------------------------------------------------------

def implied_prob(odds):
    if pd.isna(odds):
        return np.nan

    odds = float(odds)

    if odds < 0:
        return abs(odds) / (abs(odds) + 100)

    return 100 / (odds + 100)

week["home_implied_prob"] = week["home_moneyline"].apply(implied_prob)
week["away_implied_prob"] = week["away_moneyline"].apply(implied_prob)

# Remove vig by normalizing both sides.
total_prob = (
    week["home_implied_prob"] +
    week["away_implied_prob"]
)

week["home_market_win_prob"] = (
    week["home_implied_prob"] / total_prob
)

week["away_market_win_prob"] = (
    week["away_implied_prob"] / total_prob
)

# ------------------------------------------------------------
# SURVIVOR FAVORITE
# ------------------------------------------------------------

week["survivor_team"] = np.where(
    week["home_market_win_prob"] >= week["away_market_win_prob"],
    week["home_team"],
    week["away_team"]
)

week["survivor_win_prob"] = np.maximum(
    week["home_market_win_prob"],
    week["away_market_win_prob"]
)

week["survivor_spread"] = np.where(
    week["survivor_team"] == week["home_team"],
    week["home_spread"],
    week["away_spread"]
)

def survivor_grade(p):
    if pd.isna(p):
        return "NO GRADE"
    if p >= .80:
        return "A+"
    if p >= .75:
        return "A"
    if p >= .70:
        return "B+"
    if p >= .65:
        return "B"
    if p >= .60:
        return "C"
    return "AVOID"

week["survivor_grade"] = week["survivor_win_prob"].apply(
    survivor_grade
)

# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

week.to_csv(
    OUT / "NFL_CURRENT_WEEK.csv",
    index=False
)

week.to_parquet(
    OUT / "NFL_CURRENT_WEEK.parquet",
    index=False
)

survivor_columns = [
    "start",
    "away_team",
    "home_team",
    "survivor_team",
    "survivor_win_prob",
    "survivor_spread",
    "survivor_grade",
    "sportsbooks",
]

# Preserve market provenance when supplied by the collector.
for optional_col in [
    "market_source",
    "market_status",
    "collected_at",
]:
    if optional_col in week.columns:
        survivor_columns.append(optional_col)

survivor = week[
    survivor_columns
].sort_values(
    "survivor_win_prob",
    ascending=False
)

survivor.to_csv(
    OUT / "NFL_SURVIVOR_BOARD.csv",
    index=False
)

survivor.to_parquet(
    OUT / "NFL_SURVIVOR_BOARD.parquet",
    index=False
)

print("=" * 76)
print("NFL CURRENT WEEK + SURVIVOR")
print("=" * 76)

print("First game:", first_start)
print("Games this slate:", len(week))

print()
print("TOP SURVIVOR OPTIONS")
print()

show = survivor.head(12).copy()
show["survivor_win_prob"] = (
    show["survivor_win_prob"] * 100
).round(1)

print(
    show[
        [
            "survivor_team",
            "survivor_win_prob",
            "survivor_spread",
            "survivor_grade",
            "sportsbooks",
        ]
    ].to_string(index=False)
)

print()
print("RESULT: PASS")
