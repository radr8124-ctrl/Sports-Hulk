from pathlib import Path
import pandas as pd
import numpy as np

HERE = Path(__file__).resolve().parent
DERIVED = HERE / "derived"

src = DERIVED / "MLB_CORE_GAME_MARKET_HISTORY.csv"

if not src.exists():
    raise SystemExit("Missing MLB_CORE_GAME_MARKET_HISTORY.csv")

d = pd.read_csv(src, low_memory=False)

# ---------------------------------------------------------
# NORMALIZE
# ---------------------------------------------------------

for c in [
    "away_team",
    "home_team",
    "book",
    "core_market",
    "core_side",
]:
    d[c] = (
        d[c]
        .astype(str)
        .str.strip()
        .str.lower()
    )

for c in [
    "open_point",
    "current_point",
    "open_price",
    "current_price",
    "implied_prob_move",
]:
    d[c] = pd.to_numeric(
        d[c],
        errors="coerce",
    )

# ---------------------------------------------------------
# CANONICAL LINE
# ---------------------------------------------------------
#
# For moneyline there is no point.
#
# For spread/total, use current_point as the current exact
# market identity.
#
# This prevents:
#   total 7.5
#   total 8.0
#   total 4.5
# from being treated as the same sportsbook market.

d["canonical_line"] = np.where(
    d["core_market"] == "moneyline",
    np.nan,
    d["current_point"],
)

# ---------------------------------------------------------
# DEDUPLICATION IDENTITY
# ---------------------------------------------------------

keys = [
    "away_team",
    "home_team",
    "book",
    "core_market",
    "core_side",
    "canonical_line",
]

# Prefer Odds API for the canonical duplicate row when both
# providers describe the same sportsbook/current market.
#
# We still preserve which sources reported it.
d["_source_priority"] = np.where(
    d["market_source_type"] == "ODDS_API",
    0,
    1,
)

# More observations wins after provider priority.
d["_obs_priority"] = -pd.to_numeric(
    d["observation_count"],
    errors="coerce",
).fillna(0)

d = d.sort_values(
    keys + ["_source_priority", "_obs_priority"],
    na_position="first",
)

# Source coverage metadata before dedup.
coverage = (
    d.groupby(keys, dropna=False)
    .agg(
        reporting_sources=(
            "market_source_type",
            lambda x: ",".join(
                sorted(set(x.astype(str)))
            ),
        ),
        provider_row_count=(
            "market_source_type",
            "size",
        ),
    )
    .reset_index()
)

# Keep one canonical row per exact sportsbook market.
dedup = (
    d.drop_duplicates(
        subset=keys,
        keep="first",
    )
    .copy()
)

dedup = dedup.merge(
    coverage,
    on=keys,
    how="left",
)

dedup["reported_by_both"] = (
    dedup["reporting_sources"]
    .str.contains("ODDS_API", na=False)
    &
    dedup["reporting_sources"]
    .str.contains("SGO", na=False)
)

dedup = dedup.drop(
    columns=[
        "_source_priority",
        "_obs_priority",
    ],
    errors="ignore",
)

# ---------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------

out_csv = (
    DERIVED /
    "MLB_CORE_GAME_MARKET_DEDUPED.csv"
)

out_parquet = (
    DERIVED /
    "MLB_CORE_GAME_MARKET_DEDUPED.parquet"
)

dedup.to_csv(out_csv, index=False)
dedup.to_parquet(out_parquet, index=False)

print("SPORTS HULK CORE MARKET DEDUPE: DONE")
print()
print("Input rows:", f"{len(d):,}")
print("Deduped rows:", f"{len(dedup):,}")
print(
    "Rows removed:",
    f"{len(d) - len(dedup):,}",
)

print(
    "Exact markets reported by both sources:",
    f"{int(dedup['reported_by_both'].sum()):,}",
)

print("\nMarkets:")
print(
    dedup["core_market"]
    .value_counts()
    .to_string()
)

print("\nCanonical source kept:")
print(
    dedup["market_source_type"]
    .value_counts()
    .to_string()
)
