from pathlib import Path
import pandas as pd
import numpy as np

HERE = Path(__file__).resolve().parent
DERIVED = HERE / "derived"

src = DERIVED / "MLB_CORE_GAME_MARKET_DEDUPED.csv"

if not src.exists():
    raise SystemExit(
        "Missing MLB_CORE_GAME_MARKET_DEDUPED.csv"
    )

d = pd.read_csv(src, low_memory=False)

# =========================================================
# CLEAN
# =========================================================

numeric_cols = [
    "open_point",
    "current_point",
    "point_move",
    "open_price",
    "current_price",
    "open_implied_prob",
    "current_implied_prob",
    "implied_prob_move",
    "observation_count",
    "reported_by_both",
]

for c in numeric_cols:
    if c in d.columns:
        d[c] = pd.to_numeric(
            d[c],
            errors="coerce",
        )

for c in [
    "away_team",
    "home_team",
    "book",
    "core_market",
    "core_side",
    "market_source_type",
]:
    if c in d.columns:
        d[c] = (
            d[c]
            .astype(str)
            .str.strip()
            .str.lower()
        )

# Only rows with actual observed history vote.
h = d[
    d["observation_count"].fillna(0) >= 2
].copy()

# =========================================================
# CANONICAL GAME START
# =========================================================
#
# Providers have shown one-minute schedule differences:
# 17:05 vs 17:06, 23:40 vs 23:41, etc.
#
# Floor to a five-minute window so these become one event.
# =========================================================

h["_game_dt"] = pd.to_datetime(
    h["game_start"],
    errors="coerce",
    utc=True,
    format="mixed",
)

h = h[h["_game_dt"].notna()].copy()

h["_game_bucket"] = h["_game_dt"].dt.floor("5min")

# =========================================================
# ROW-LEVEL DIRECTION
# =========================================================

EPS = 1e-9

h["prob_direction"] = np.select(
    [
        h["implied_prob_move"] > EPS,
        h["implied_prob_move"] < -EPS,
    ],
    [
        1,
        -1,
    ],
    default=0,
)

h["line_direction"] = np.select(
    [
        h["point_move"] > EPS,
        h["point_move"] < -EPS,
    ],
    [
        1,
        -1,
    ],
    default=0,
)

# =========================================================
# MAIN-LINE REFERENCE
# =========================================================
#
# Odds API standard markets are preferred as the reference.
# If no Odds API line exists, use the median of all rows.
#
# Moneyline has no point, so reference is not needed.
# =========================================================

side_keys = [
    "away_team",
    "home_team",
    "_game_bucket",
    "core_market",
    "core_side",
]

line_ref_rows = []

for key, g in h.groupby(
    side_keys,
    dropna=False,
):
    market = str(g["core_market"].iloc[0])

    ref = np.nan

    if market in ["spread", "total"]:
        odds = g[
            g["market_source_type"] == "odds_api"
        ]

        odds_points = pd.to_numeric(
            odds["current_point"],
            errors="coerce",
        ).dropna()

        if len(odds_points):
            ref = float(odds_points.median())
        else:
            all_points = pd.to_numeric(
                g["current_point"],
                errors="coerce",
            ).dropna()

            if len(all_points):
                ref = float(all_points.median())

    row = dict(zip(side_keys, key))
    row["_reference_line"] = ref
    line_ref_rows.append(row)

refs = pd.DataFrame(line_ref_rows)

h = h.merge(
    refs,
    on=side_keys,
    how="left",
)

# =========================================================
# ONE SPORTSBOOK = ONE VOTE
# =========================================================
#
# For every book/game/market/side:
#
# 1. Prefer an Odds API row if that book has one.
# 2. For spread/total, choose the line closest to the
#    reference main line.
# 3. Prefer rows reported by both sources.
# 4. Prefer more observations as final tiebreaker.
#
# This prevents SGO alternate lines from casting extra votes.
# =========================================================

book_keys = side_keys + ["book"]

selected = []

for _, g in h.groupby(
    book_keys,
    dropna=False,
):
    x = g.copy()

    market = str(
        x["core_market"].iloc[0]
    )

    # Prefer Odds API standard market when available.
    odds = x[
        x["market_source_type"] == "odds_api"
    ].copy()

    if not odds.empty:
        x = odds

    if market in ["spread", "total"]:
        ref = pd.to_numeric(
            x["_reference_line"],
            errors="coerce",
        ).dropna()

        ref = (
            float(ref.iloc[0])
            if len(ref)
            else np.nan
        )

        point = pd.to_numeric(
            x["current_point"],
            errors="coerce",
        )

        if pd.notna(ref):
            x["_line_distance"] = (
                point - ref
            ).abs()
        else:
            x["_line_distance"] = np.inf

    else:
        x["_line_distance"] = 0.0

    if "reported_by_both" in x.columns:
        both = pd.to_numeric(
            x["reported_by_both"],
            errors="coerce",
        ).fillna(0)
    else:
        both = pd.Series(
            0,
            index=x.index,
        )

    x["_both_priority"] = both

    x["_obs_priority"] = pd.to_numeric(
        x["observation_count"],
        errors="coerce",
    ).fillna(0)

    x = x.sort_values(
        [
            "_line_distance",
            "_both_priority",
            "_obs_priority",
        ],
        ascending=[
            True,
            False,
            False,
        ],
    )

    selected.append(
        x.iloc[0]
    )

votes = pd.DataFrame(selected).reset_index(
    drop=True
)

# Canonical game_start passed downstream.
votes["game_start"] = (
    votes["_game_bucket"]
    .dt.strftime("%Y-%m-%d %H:%M:%S+00:00")
)

# =========================================================
# HARD VALIDATION: ONE BOOK ONE VOTE
# =========================================================

dup_vote = votes.duplicated(
    book_keys,
    keep=False,
)

if dup_vote.any():
    bad = votes.loc[
        dup_vote,
        book_keys,
    ]

    print(
        bad.to_string(index=False)
    )

    raise SystemExit(
        "ERROR: duplicate sportsbook votes remain"
    )

# =========================================================
# CONSENSUS
# =========================================================

keys = [
    "away_team",
    "home_team",
    "game_start",
    "core_market",
    "core_side",
]

def build_group(g):
    books = int(
        g["book"].nunique()
    )

    prob_up = int(
        (g["prob_direction"] > 0).sum()
    )

    prob_down = int(
        (g["prob_direction"] < 0).sum()
    )

    prob_flat = int(
        (g["prob_direction"] == 0).sum()
    )

    moving_books = (
        prob_up + prob_down
    )

    # This must now equal books exactly.
    vote_total = (
        prob_up
        + prob_down
        + prob_flat
    )

    if vote_total != books:
        raise ValueError(
            f"Vote invariant failed: "
            f"books={books}, votes={vote_total}"
        )

    if moving_books:
        prob_consensus = (
            max(prob_up, prob_down)
            / moving_books
        )
    else:
        prob_consensus = 0.0

    if books:
        prob_market_share = (
            max(prob_up, prob_down)
            / books
        )
    else:
        prob_market_share = 0.0

    if prob_up > prob_down:
        prob_consensus_direction = 1

    elif prob_down > prob_up:
        prob_consensus_direction = -1

    else:
        prob_consensus_direction = 0

    line_up = int(
        (g["line_direction"] > 0).sum()
    )

    line_down = int(
        (g["line_direction"] < 0).sum()
    )

    line_flat = int(
        (g["line_direction"] == 0).sum()
    )

    line_moving = (
        line_up + line_down
    )

    line_vote_total = (
        line_up
        + line_down
        + line_flat
    )

    if line_vote_total != books:
        raise ValueError(
            f"Line vote invariant failed: "
            f"books={books}, "
            f"votes={line_vote_total}"
        )

    if line_moving:
        line_consensus = (
            max(line_up, line_down)
            / line_moving
        )
    else:
        line_consensus = 0.0

    return pd.Series({
        "books_reporting":
            books,

        "prob_books_up":
            prob_up,

        "prob_books_down":
            prob_down,

        "prob_books_flat":
            prob_flat,

        "prob_books_moving":
            moving_books,

        "prob_consensus_direction":
            prob_consensus_direction,

        "prob_consensus_pct":
            prob_consensus * 100.0,

        "prob_market_share_pct":
            prob_market_share * 100.0,

        "avg_implied_prob_move":
            g["implied_prob_move"].mean(),

        "median_implied_prob_move":
            g["implied_prob_move"].median(),

        "max_abs_implied_prob_move":
            g["implied_prob_move"].abs().max(),

        "line_books_up":
            line_up,

        "line_books_down":
            line_down,

        "line_books_flat":
            line_flat,

        "line_books_moving":
            line_moving,

        "line_consensus_pct":
            line_consensus * 100.0,

        "avg_point_move":
            g["point_move"].mean(),

        "median_point_move":
            g["point_move"].median(),
    })

consensus = (
    votes
    .groupby(
        keys,
        dropna=False,
    )
    .apply(
        build_group,
        include_groups=False,
    )
    .reset_index()
)

# =========================================================
# CONSERVATIVE STRENGTH
# =========================================================

conditions = [
    (
        (consensus["books_reporting"] >= 5)
        & (consensus["prob_books_moving"] >= 4)
        & (consensus["prob_consensus_pct"] >= 75)
        & (consensus["prob_market_share_pct"] >= 60)
    ),
    (
        (consensus["books_reporting"] >= 4)
        & (consensus["prob_books_moving"] >= 3)
        & (consensus["prob_consensus_pct"] >= 66)
        & (consensus["prob_market_share_pct"] >= 40)
    ),
]

choices = [
    "strong",
    "medium",
]

consensus["consensus_strength"] = np.select(
    conditions,
    choices,
    default="weak",
)

consensus["prob_direction_label"] = np.select(
    [
        consensus[
            "prob_consensus_direction"
        ] > 0,

        consensus[
            "prob_consensus_direction"
        ] < 0,
    ],
    [
        "toward_side",
        "away_from_side",
    ],
    default="mixed_flat",
)

# =========================================================
# FINAL INVARIANTS
# =========================================================

consensus["_prob_vote_total"] = (
    consensus["prob_books_up"]
    + consensus["prob_books_down"]
    + consensus["prob_books_flat"]
)

consensus["_line_vote_total"] = (
    consensus["line_books_up"]
    + consensus["line_books_down"]
    + consensus["line_books_flat"]
)

bad_prob = consensus[
    consensus["_prob_vote_total"]
    != consensus["books_reporting"]
]

bad_line = consensus[
    consensus["_line_vote_total"]
    != consensus["books_reporting"]
]

if len(bad_prob) or len(bad_line):
    raise SystemExit(
        "ERROR: one-book-one-vote validation failed"
    )

if (
    consensus["prob_books_moving"]
    > consensus["books_reporting"]
).any():
    raise SystemExit(
        "ERROR: moving books exceed books reporting"
    )

consensus = consensus.drop(
    columns=[
        "_prob_vote_total",
        "_line_vote_total",
    ]
)

# =========================================================
# OUTPUT
# =========================================================

out_csv = (
    DERIVED /
    "MLB_MARKET_CONSENSUS.csv"
)

out_parquet = (
    DERIVED /
    "MLB_MARKET_CONSENSUS.parquet"
)

consensus.to_csv(
    out_csv,
    index=False,
)

consensus.to_parquet(
    out_parquet,
    index=False,
)

print(
    "SPORTS HULK MARKET CONSENSUS: DONE"
)

print(
    "Selected sportsbook votes:",
    f"{len(votes):,}",
)

print(
    "Consensus rows:",
    f"{len(consensus):,}",
)

print(
    "\nStrength:"
)

print(
    consensus[
        "consensus_strength"
    ]
    .value_counts()
    .to_string()
)

print(
    "\nONE BOOK = ONE VOTE: PASS"
)

print(
    "Moving books never exceed reporting books:",
    bool(
        (
            consensus["prob_books_moving"]
            <= consensus["books_reporting"]
        ).all()
    )
)

print(
    "Probability vote totals valid:",
    bool(
        (
            consensus["prob_books_up"]
            + consensus["prob_books_down"]
            + consensus["prob_books_flat"]
            == consensus["books_reporting"]
        ).all()
    )
)

print(
    "Line vote totals valid:",
    bool(
        (
            consensus["line_books_up"]
            + consensus["line_books_down"]
            + consensus["line_books_flat"]
            == consensus["books_reporting"]
        ).all()
    )
)
