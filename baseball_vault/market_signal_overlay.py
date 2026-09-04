from pathlib import Path
import pandas as pd
import numpy as np

HERE = Path(__file__).resolve().parent
DERIVED = HERE / "derived"

brain_file = DERIVED / "MLB_DECISION_BRAIN_RESEARCH.csv"
signal_file = DERIVED / "MLB_MARKET_SIGNALS.csv"

if not brain_file.exists():
    raise SystemExit("Missing MLB_DECISION_BRAIN_RESEARCH.csv")

if not signal_file.exists():
    raise SystemExit("Missing MLB_MARKET_SIGNALS.csv")

brain = pd.read_csv(brain_file, low_memory=False)
sig = pd.read_csv(signal_file, low_memory=False)

# =========================================================
# NORMALIZE
# =========================================================

def norm(s):
    return (
        s.astype(str)
        .str.strip()
        .str.lower()
    )

for c in ["away_team", "home_team"]:
    brain[f"_{c}"] = norm(brain[c])
    sig[f"_{c}"] = norm(sig[c])

brain["_brain_dt"] = pd.to_datetime(
    brain["gameDate"],
    errors="coerce",
    utc=True,
    format="mixed",
)

sig["_market_dt"] = pd.to_datetime(
    sig["game_start"],
    errors="coerce",
    utc=True,
    format="mixed",
)

# =========================================================
# UNIQUE MARKET EVENTS
# =========================================================

events = (
    sig[
        [
            "_away_team",
            "_home_team",
            "game_start",
            "_market_dt",
        ]
    ]
    .drop_duplicates()
    .reset_index(drop=True)
)

# =========================================================
# MATCH EACH MLB GAME TO NEAREST MARKET EVENT
# =========================================================
#
# Same teams required.
# Market scheduled start must be within 15 minutes of MLB time.
#
# This handles provider differences such as:
# 20:10 vs 20:11
# 18:35 vs 18:36
#
# while preventing tomorrow's game from inheriting today's market.
# =========================================================

MAX_DIFF_MINUTES = 15

matches = []

for idx, r in brain.iterrows():
    away = r["_away_team"]
    home = r["_home_team"]
    game_dt = r["_brain_dt"]

    candidates = events[
        (events["_away_team"] == away)
        & (events["_home_team"] == home)
    ].copy()

    matched_start = np.nan
    diff_minutes = np.nan

    if (
        pd.notna(game_dt)
        and not candidates.empty
    ):
        candidates["_diff_seconds"] = (
            candidates["_market_dt"] - game_dt
        ).abs().dt.total_seconds()

        candidates = candidates.sort_values(
            "_diff_seconds"
        )

        best = candidates.iloc[0]

        diff_minutes = (
            float(best["_diff_seconds"]) / 60.0
        )

        if diff_minutes <= MAX_DIFF_MINUTES:
            matched_start = best["game_start"]

    matches.append(
        {
            "_brain_index": idx,
            "_matched_market_start": matched_start,
            "market_game_time_diff_minutes": diff_minutes,
        }
    )

match_df = pd.DataFrame(matches)

brain = (
    brain
    .reset_index()
    .rename(columns={"index": "_brain_index"})
    .merge(
        match_df,
        on="_brain_index",
        how="left",
    )
)

# =========================================================
# MARKET SLICES
# =========================================================

def market_slice(market, prefix):
    x = sig[
        sig["core_market"] == market
    ].copy()

    keep = [
        "_away_team",
        "_home_team",
        "game_start",
        "signal_target",
        "signal_strength",
        "books_reporting",
        "books_moving",
        "consensus_among_movers_pct",
        "whole_market_share_pct",
        "avg_implied_prob_move",
        "market_signal",
    ]

    x = x[keep]

    return x.rename(
        columns={
            "game_start":
                "_matched_market_start",

            "signal_target":
                f"{prefix}_signal_target",

            "signal_strength":
                f"{prefix}_signal_strength",

            "books_reporting":
                f"{prefix}_books_reporting",

            "books_moving":
                f"{prefix}_books_moving",

            "consensus_among_movers_pct":
                f"{prefix}_consensus_among_movers_pct",

            "whole_market_share_pct":
                f"{prefix}_whole_market_share_pct",

            "avg_implied_prob_move":
                f"{prefix}_avg_implied_prob_move",

            "market_signal":
                f"{prefix}_market_signal",
        }
    )

join_keys = [
    "_away_team",
    "_home_team",
    "_matched_market_start",
]

for market, prefix in [
    ("moneyline", "market_ml"),
    ("spread", "market_spread"),
    ("total", "market_total"),
]:
    x = market_slice(
        market,
        prefix,
    )

    brain = brain.merge(
        x,
        on=join_keys,
        how="left",
    )

out = brain.copy()

# =========================================================
# TEAM MARKET ALIGNMENT
# =========================================================

out["_lean_norm"] = norm(
    out["lean"]
) if "lean" in out.columns else ""

def alignment(row, target_col, strength_col):
    target = str(
        row.get(target_col, "")
    ).strip().lower()

    strength = str(
        row.get(strength_col, "")
    ).strip().lower()

    lean = str(
        row.get("_lean_norm", "")
    ).strip().lower()

    if target in ["", "nan", "mixed"]:
        return "NO_SIGNAL"

    if lean in ["", "nan", "none"]:
        return "UNSCORED"

    if target == lean:
        if strength == "strong":
            return "STRONG_SUPPORT"

        if strength == "medium":
            return "MEDIUM_SUPPORT"

        return "WEAK_SUPPORT"

    if strength == "strong":
        return "STRONG_CONFLICT"

    if strength == "medium":
        return "MEDIUM_CONFLICT"

    return "WEAK_CONFLICT"

out["market_ml_alignment"] = out.apply(
    alignment,
    axis=1,
    args=(
        "market_ml_signal_target",
        "market_ml_signal_strength",
    ),
)

out["market_spread_alignment"] = out.apply(
    alignment,
    axis=1,
    args=(
        "market_spread_signal_target",
        "market_spread_signal_strength",
    ),
)

# =========================================================
# TOTAL CONTEXT
# =========================================================

out["market_total_context"] = np.where(
    out["market_total_signal_target"].notna(),
    out["market_total_signal_strength"].astype(str)
    + "_"
    + out["market_total_signal_target"].astype(str),
    "NO_SIGNAL",
)

# =========================================================
# OVERALL RESEARCH ALIGNMENT
# =========================================================

def overall(row):
    vals = {
        str(row.get("market_ml_alignment", "")),
        str(row.get("market_spread_alignment", "")),
    }

    if "STRONG_CONFLICT" in vals:
        return "STRONG_MARKET_CONFLICT"

    if "STRONG_SUPPORT" in vals:
        if "MEDIUM_CONFLICT" in vals:
            return "MIXED_MARKET"

        return "STRONG_MARKET_SUPPORT"

    if "MEDIUM_CONFLICT" in vals:
        return "MEDIUM_MARKET_CONFLICT"

    if "MEDIUM_SUPPORT" in vals:
        return "MEDIUM_MARKET_SUPPORT"

    if any(
        "CONFLICT" in x
        for x in vals
    ):
        return "WEAK_MARKET_CONFLICT"

    if any(
        "SUPPORT" in x
        for x in vals
    ):
        return "WEAK_MARKET_SUPPORT"

    return "NO_CLEAR_MARKET_SIGNAL"

out["market_research_alignment"] = out.apply(
    overall,
    axis=1,
)

# =========================================================
# PRODUCTION SAFETY
# =========================================================

out["market_changes_official_decision"] = False

# Restore original brain order.
out = out.sort_values(
    "_brain_index"
)

out = out.drop(
    columns=[
        "_brain_index",
        "_away_team",
        "_home_team",
        "_brain_dt",
        "_lean_norm",
    ],
    errors="ignore",
)

# =========================================================
# HARD ROW IDENTITY VALIDATION
# =========================================================

if "gamePk" in out.columns:
    if out["gamePk"].duplicated().any():
        raise SystemExit(
            "ERROR: market overlay duplicated MLB gamePk rows"
        )

csv_out = (
    DERIVED /
    "MLB_DECISION_BRAIN_MARKET_RESEARCH.csv"
)

pq_out = (
    DERIVED /
    "MLB_DECISION_BRAIN_MARKET_RESEARCH.parquet"
)

out.to_csv(
    csv_out,
    index=False,
)

out.to_parquet(
    pq_out,
    index=False,
)

print(
    "SPORTS HULK MARKET RESEARCH OVERLAY: DONE"
)

print("Rows:", len(out))

if "gamePk" in out.columns:
    print(
        "Unique gamePk:",
        out["gamePk"].nunique()
    )

matched = out[
    out["market_ml_signal_target"].notna()
    | out["market_spread_signal_target"].notna()
    | out["market_total_signal_target"].notna()
]

print(
    "Games matched to market:",
    len(matched)
)

print(
    "Games without market:",
    len(out) - len(matched)
)

if len(matched):
    print(
        "Max matched time difference:",
        round(
            matched[
                "market_game_time_diff_minutes"
            ].max(),
            3,
        ),
        "minutes",
    )

print("\nMarket alignment:")

print(
    out[
        "market_research_alignment"
    ]
    .value_counts(dropna=False)
    .to_string()
)

print(
    "\nOfficial decisions changed:",
    int(
        out[
            "market_changes_official_decision"
        ].sum()
    )
)
