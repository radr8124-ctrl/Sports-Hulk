from pathlib import Path
import pandas as pd
import numpy as np

HERE = Path(__file__).resolve().parent
DERIVED = HERE / "derived"

src = DERIVED / "MLB_PREGAME_MARKET_HISTORY.csv"

if not src.exists():
    raise SystemExit("Missing MLB_PREGAME_MARKET_HISTORY.csv")

d = pd.read_csv(src, low_memory=False)

# ---------------------------------------------------------
# IDENTIFY CORE FULL-GAME MARKETS
# ---------------------------------------------------------

source = d["source_file"].astype(str)

# Odds API already gives us only the standard game markets
# we requested: h2h, spreads, totals.
odds_api_core = (
    source.str.contains("ODDS_API", case=False, na=False)
    & d["market"].isin(["h2h", "spreads", "totals"])
)

# SportsGameOdds includes many props and inning markets.
# Core game markets are:
#   statID = points
#   periodID = game
#   market = ml / sp / ou
sgo_core = (
    source.str.contains("SGO", case=False, na=False)
    & (d["statID"].astype(str) == "points")
    & (d["periodID"].astype(str) == "game")
    & d["market"].isin(["ml", "sp", "ou"])

    # Exclude player props that SGO also labels as "points".
    & d["player"].isna()
    & d["playerID"].isna()
)

core = d[odds_api_core | sgo_core].copy()

# ---------------------------------------------------------
# STANDARDIZE MARKET NAMES
# ---------------------------------------------------------

market_map = {
    "ml": "moneyline",
    "h2h": "moneyline",

    "sp": "spread",
    "spreads": "spread",

    "ou": "total",
    "totals": "total",
}

core["core_market"] = (
    core["market"]
    .map(market_map)
    .fillna(core["market"])
)

# ---------------------------------------------------------
# STANDARDIZE SIDE
# ---------------------------------------------------------

def normalize_side(row):
    market = row["core_market"]
    side = str(row.get("side", "")).strip()
    away = str(row.get("away_team", "")).strip()
    home = str(row.get("home_team", "")).strip()

    low = side.lower()

    if market == "total":
        if low == "over":
            return "over"
        if low == "under":
            return "under"

    if low == "away":
        return away

    if low == "home":
        return home

    return side

core["core_side"] = core.apply(
    normalize_side,
    axis=1,
)

# ---------------------------------------------------------
# HISTORY QUALITY
# ---------------------------------------------------------

core["has_history"] = (
    core["observation_count"] >= 2
)

core["has_price_move"] = (
    core["implied_prob_move"]
    .fillna(0)
    .abs() > 0
)

core["has_line_move"] = (
    core["point_move"]
    .fillna(0)
    .abs() > 0
)

# Mark the source type
core["market_source_type"] = np.where(
    source.loc[core.index].str.contains(
        "SGO",
        case=False,
        na=False,
    ),
    "SGO",
    "ODDS_API",
)

# ---------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------

out_csv = DERIVED / "MLB_CORE_GAME_MARKET_HISTORY.csv"
out_parquet = DERIVED / "MLB_CORE_GAME_MARKET_HISTORY.parquet"

core.to_csv(out_csv, index=False)
core.to_parquet(out_parquet, index=False)

print("SPORTS HULK CORE GAME MARKET BUILDER: DONE")
print()
print("Core market rows:", f"{len(core):,}")
print(
    "With 2+ observations:",
    f"{int(core.has_history.sum()):,}",
)
print(
    "With line movement:",
    f"{int(core.has_line_move.sum()):,}",
)
print(
    "With implied-probability movement:",
    f"{int(core.has_price_move.sum()):,}",
)

print("\nCore markets:")
print(
    core["core_market"]
    .value_counts(dropna=False)
    .to_string()
)

print("\nSources:")
print(
    core["market_source_type"]
    .value_counts(dropna=False)
    .to_string()
)

print("\nPlayer props accidentally present:")
print(
    int(core["player"].notna().sum())
)

print("\nNon-game SGO periods accidentally present:")
bad_period = (
    (core["market_source_type"] == "SGO")
    & (core["periodID"].astype(str) != "game")
)
print(int(bad_period.sum()))
