from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "nfl_live" / "derived"

SRC = OUT / "NFL_SURVIVOR_HULK_CONTEXT.csv"

if not SRC.exists():
    raise SystemExit("NFL_SURVIVOR_HULK_CONTEXT.csv missing")

df = pd.read_csv(SRC)

def f(v):
    try:
        return float(v)
    except Exception:
        return np.nan


rows = []

for _, row in df.iterrows():
    out = row.to_dict()

    market_prob = f(row.get("survivor_win_prob"))
    context = f(row.get("hulk_context_score"))
    spread = f(row.get("survivor_spread"))

    flags = str(row.get("hulk_context_flags") or "").split("|")
    flags = [x for x in flags if x]

    if pd.isna(market_prob):
        market_pct = np.nan
    else:
        market_pct = market_prob * 100

    delta = (
        context - market_pct
        if not pd.isna(context) and not pd.isna(market_pct)
        else np.nan
    )

    warnings = []
    positives = []

    # --------------------------------------------------------
    # POSITIVE SIGNALS
    # --------------------------------------------------------

    if "ELITE_MARKET_FAVORITE" in flags:
        positives.append("ELITE_MARKET")

    if "STRONG_MARKET_FAVORITE" in flags:
        positives.append("STRONG_MARKET")

    if "TD_PLUS_FAVORITE" in flags:
        positives.append("BIG_SPREAD")

    if "HOME" in flags:
        positives.append("HOME_FIELD")

    if "STRONG_RECENT_RECORD" in flags:
        positives.append("RECENT_FORM")

    if "STRONG_POINT_DIFFERENTIAL" in flags:
        positives.append("POINT_DIFF")

    if "REST_ADVANTAGE" in flags:
        positives.append("REST")

    # --------------------------------------------------------
    # RISK SIGNALS
    # --------------------------------------------------------

    if "ROAD_FAVORITE" in flags:
        warnings.append("ROAD_FAVORITE")

    if "HIGH_WIND_RISK" in flags:
        warnings.append("HIGH_WIND")

    if "WIND_CAUTION" in flags:
        warnings.append("WIND")

    if "PRECIP_RISK" in flags:
        warnings.append("PRECIP")

    if "PRECIP_CAUTION" in flags:
        warnings.append("PRECIP_CAUTION")

    if "SHORT_REST" in flags:
        warnings.append("SHORT_REST")

    if "WEAK_RECENT_RECORD" in flags:
        warnings.append("WEAK_FORM")

    if "NEGATIVE_POINT_DIFFERENTIAL" in flags:
        warnings.append("NEG_POINT_DIFF")

    # --------------------------------------------------------
    # DISAGREEMENT CLASS
    # --------------------------------------------------------

    if pd.isna(delta):
        disagreement = "NO_CONTEXT"

    elif delta >= 7:
        disagreement = "HULK_STRONGER"

    elif delta <= -7:
        disagreement = "HULK_MAJOR_WARNING"

    elif delta <= -3:
        disagreement = "HULK_CAUTION"

    else:
        disagreement = "MARKET_HULK_AGREE"

    # Additional warning escalation.
    severe_warning_count = sum(
        x in warnings
        for x in [
            "HIGH_WIND",
            "WEAK_FORM",
            "NEG_POINT_DIFF",
            "SHORT_REST",
        ]
    )

    if severe_warning_count >= 2:
        disagreement = "HULK_MAJOR_WARNING"

    # --------------------------------------------------------
    # DECISION TIER
    #
    # NOT a probability.
    # NOT an auto-pick.
    # --------------------------------------------------------

    tier = "WATCH"

    if (
        not pd.isna(market_pct)
        and market_pct >= 80
        and context >= 78
        and severe_warning_count == 0
    ):
        tier = "TOP_TIER"

    elif (
        not pd.isna(market_pct)
        and market_pct >= 72
        and context >= 75
        and severe_warning_count == 0
    ):
        tier = "STRONG"

    elif (
        not pd.isna(market_pct)
        and market_pct >= 65
        and context >= 65
    ):
        tier = "VIABLE"

    if disagreement == "HULK_MAJOR_WARNING":
        tier = "CAUTION"

    out.update({
        "market_prob_pct": round(market_pct, 1)
            if not pd.isna(market_pct) else None,

        "context_delta": round(delta, 1)
            if not pd.isna(delta) else None,

        "hulk_disagreement": disagreement,
        "hulk_decision_tier": tier,

        "positive_signals": "|".join(positives),
        "risk_signals": "|".join(warnings),
    })

    rows.append(out)


result = pd.DataFrame(rows)

tier_rank = {
    "TOP_TIER": 0,
    "STRONG": 1,
    "VIABLE": 2,
    "WATCH": 3,
    "CAUTION": 4,
}

result["_tier_rank"] = (
    result["hulk_decision_tier"]
    .map(tier_rank)
    .fillna(9)
)

result = result.sort_values(
    [
        "_tier_rank",
        "hulk_context_score",
        "market_prob_pct",
    ],
    ascending=[True, False, False],
).drop(columns=["_tier_rank"])

result.to_csv(
    OUT / "NFL_SURVIVOR_HULK_DECISION.csv",
    index=False,
)

result.to_parquet(
    OUT / "NFL_SURVIVOR_HULK_DECISION.parquet",
    index=False,
)

print("=" * 120)
print("SPORTS HULK — SURVIVOR DECISION BOARD")
print("=" * 120)

cols = [
    "survivor_team",
    "opponent",
    "market_prob_pct",
    "hulk_context_score",
    "context_delta",
    "hulk_disagreement",
    "hulk_decision_tier",
    "survivor_spread",
    "positive_signals",
    "risk_signals",
]

print(result[cols].to_string(index=False))

print()
print("IMPORTANT:")
print("Decision tiers are context classifications, not win probabilities.")
print("No Survivor selection is submitted automatically.")
print("RESULT: DISAGREEMENT_ENGINE_READY")
