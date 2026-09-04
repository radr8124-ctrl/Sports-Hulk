from pathlib import Path
import pandas as pd
import numpy as np

HERE = Path(__file__).resolve().parent
DERIVED = HERE / "derived"

src = DERIVED / "MLB_MARKET_CONSENSUS.csv"

if not src.exists():
    raise SystemExit("Missing MLB_MARKET_CONSENSUS.csv")

d = pd.read_csv(src, low_memory=False)

for c in [
    "books_reporting",
    "prob_books_up",
    "prob_books_down",
    "prob_books_flat",
    "prob_books_moving",
    "prob_consensus_pct",
    "prob_market_share_pct",
    "avg_implied_prob_move",
]:
    d[c] = pd.to_numeric(d[c], errors="coerce")

# ---------------------------------------------------------
# SCORE EACH SIDE
# ---------------------------------------------------------
#
# Positive score means the market moved TOWARD that side.
# Negative means away.
#
# Participation matters, agreement matters, magnitude matters.

direction = np.where(
    d["prob_direction_label"] == "toward_side",
    1,
    np.where(
        d["prob_direction_label"] == "away_from_side",
        -1,
        0,
    ),
)

d["direction_sign"] = direction

d["market_signal_score"] = (
    d["direction_sign"]
    * (d["prob_market_share_pct"] / 100.0)
    * (d["prob_consensus_pct"] / 100.0)
)

# ---------------------------------------------------------
# COLLAPSE MIRRORED SIDES
# ---------------------------------------------------------

keys = [
    "away_team",
    "home_team",
    "game_start",
    "core_market",
]

rows = []

for _, g in d.groupby(keys, dropna=False):

    g = g.copy()

    # Prefer the side with the strongest positive signal.
    toward = g[
        g["direction_sign"] > 0
    ].copy()

    if not toward.empty:
        chosen = toward.sort_values(
            [
                "market_signal_score",
                "prob_market_share_pct",
                "prob_books_moving",
            ],
            ascending=False,
        ).iloc[0]
    else:
        # If nothing clearly moved toward a side,
        # preserve the strongest available row as mixed/weak.
        chosen = g.assign(
            abs_signal=g["market_signal_score"].abs()
        ).sort_values(
            "abs_signal",
            ascending=False,
        ).iloc[0]

    market = str(chosen["core_market"])
    side = str(chosen["core_side"])

    if chosen["direction_sign"] > 0:
        signal_target = side
    elif chosen["direction_sign"] < 0:
        # Mirrored row says market moved away from side.
        # For totals, invert over/under.
        if market == "total":
            signal_target = (
                "under" if side == "over"
                else "over" if side == "under"
                else side
            )
        else:
            # Find opposite team side if available.
            others = g[
                g["core_side"].astype(str) != side
            ]

            toward_other = others[
                others["direction_sign"] > 0
            ]

            if not toward_other.empty:
                signal_target = (
                    toward_other
                    .sort_values(
                        "market_signal_score",
                        ascending=False,
                    )
                    .iloc[0]["core_side"]
                )
            else:
                signal_target = "mixed"
    else:
        signal_target = "mixed"

    strength = chosen["consensus_strength"]

    rows.append({
        "away_team": chosen["away_team"],
        "home_team": chosen["home_team"],
        "game_start": chosen["game_start"],
        "core_market": market,

        "signal_target": signal_target,
        "signal_strength": strength,

        "books_reporting":
            chosen["books_reporting"],

        "books_moving":
            chosen["prob_books_moving"],

        "consensus_among_movers_pct":
            chosen["prob_consensus_pct"],

        "whole_market_share_pct":
            chosen["prob_market_share_pct"],

        "avg_implied_prob_move":
            chosen["avg_implied_prob_move"],

        "market_signal_score":
            abs(chosen["market_signal_score"]),
    })

out = pd.DataFrame(rows)

# ---------------------------------------------------------
# HUMAN-READABLE SIGNAL
# ---------------------------------------------------------

def describe(r):
    market = r["core_market"]
    target = r["signal_target"]
    strength = r["signal_strength"]

    if target == "mixed":
        return f"{market}: mixed/no clear market direction"

    if market == "moneyline":
        return f"Moneyline market moved toward {target}"

    if market == "spread":
        return f"Spread market moved toward {target}"

    if market == "total":
        return f"Total market moved toward {str(target).upper()}"

    return f"{market} market moved toward {target}"

out["market_signal"] = out.apply(
    describe,
    axis=1,
)

# Highest-quality signals first.
strength_rank = {
    "strong": 0,
    "medium": 1,
    "weak": 2,
}

out["_rank"] = (
    out["signal_strength"]
    .map(strength_rank)
    .fillna(9)
)

out = out.sort_values(
    [
        "_rank",
        "whole_market_share_pct",
        "market_signal_score",
    ],
    ascending=[
        True,
        False,
        False,
    ],
).drop(columns="_rank")

# ---------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------

csv_out = DERIVED / "MLB_MARKET_SIGNALS.csv"
parquet_out = DERIVED / "MLB_MARKET_SIGNALS.parquet"

out.to_csv(csv_out, index=False)
out.to_parquet(parquet_out, index=False)

print("SPORTS HULK MARKET SIGNAL BUILDER: DONE")
print()
print("Market signals:", len(out))

print("\nStrength:")
print(
    out["signal_strength"]
    .value_counts()
    .to_string()
)

print("\nStrong signals:",
      int((out["signal_strength"] == "strong").sum()))

print("\nStrong signal preview:")

cols = [
    "away_team",
    "home_team",
    "core_market",
    "signal_target",
    "books_reporting",
    "books_moving",
    "consensus_among_movers_pct",
    "whole_market_share_pct",
    "avg_implied_prob_move",
    "signal_strength",
    "market_signal",
]

print(
    out[out["signal_strength"] == "strong"][cols]
    .head(50)
    .to_string(index=False)
)
