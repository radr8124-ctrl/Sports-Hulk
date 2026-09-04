from pathlib import Path
import pandas as pd
import numpy as np

HERE = Path(__file__).resolve().parent
DERIVED = HERE / "derived"
HISTORY = HERE / "history"

HISTORY.mkdir(parents=True, exist_ok=True)

def norm_gamepk(s):
    return (
        pd.to_numeric(
            s,
            errors="coerce",
        )
        .astype("Int64")
    )

def load_results():
    parts = []

    rf = HISTORY / "MLB_RESULTS_HISTORY.csv"

    if rf.exists():
        r = pd.read_csv(
            rf,
            low_memory=False,
        )

        if "gamePk" in r.columns:
            parts.append(r)

    mf = DERIVED / "MLB_GAME_MASTER.csv"

    if mf.exists():
        m = pd.read_csv(
            mf,
            low_memory=False,
        )

        keep = [
            c for c in [
                "gamePk",
                "home_team",
                "away_team",
                "home_score",
                "away_score",
                "status",
            ]
            if c in m.columns
        ]

        if "gamePk" in keep:
            parts.append(
                m[keep]
            )

    if not parts:
        raise SystemExit(
            "No result source available"
        )

    r = pd.concat(
        parts,
        ignore_index=True,
        sort=False,
    )

    r["gamePk"] = norm_gamepk(
        r["gamePk"]
    )

    r["home_score"] = pd.to_numeric(
        r.get("home_score"),
        errors="coerce",
    )

    r["away_score"] = pd.to_numeric(
        r.get("away_score"),
        errors="coerce",
    )

    r["_has_score"] = (
        r["home_score"].notna()
        & r["away_score"].notna()
    )

    r = (
        r.sort_values(
            [
                "gamePk",
                "_has_score",
            ]
        )
        .drop_duplicates(
            "gamePk",
            keep="last",
        )
    )

    return r

histf = (
    HISTORY /
    "MLB_MARKET_RESEARCH_HISTORY.csv"
)

if not histf.exists():
    raise SystemExit(
        "No market research history yet"
    )

h = pd.read_csv(
    histf,
    low_memory=False,
)

h["gamePk"] = norm_gamepk(
    h["gamePk"]
)

r = load_results()

r["finalized"] = (
    r["home_score"].notna()
    & r["away_score"].notna()
)

r["winner"] = np.where(
    r["home_score"] > r["away_score"],
    r["home_team"],
    np.where(
        r["away_score"] > r["home_score"],
        r["away_team"],
        "TIE",
    ),
)

cols = [
    "gamePk",
    "home_score",
    "away_score",
    "finalized",
    "winner",
]

g = h.merge(
    r[cols],
    on="gamePk",
    how="left",
)

g["graded"] = (
    g["finalized"]
    .fillna(False)
)

g["lean_correct"] = np.where(
    g["graded"],
    g["lean"].astype(str)
    == g["winner"].astype(str),
    np.nan,
)

# =========================================================
# MARKET TARGET RESULTS
# =========================================================

def target_correct(target, winner):
    if pd.isna(target) or pd.isna(winner):
        return np.nan

    t = str(target).strip().lower()
    w = str(winner).strip().lower()

    if t in [
        "",
        "nan",
        "mixed",
    ]:
        return np.nan

    return float(t == w)

g["market_ml_target_correct"] = [
    target_correct(t, w)
    if graded else np.nan

    for t, w, graded in zip(
        g.get(
            "market_ml_signal_target",
            pd.Series(
                [np.nan] * len(g)
            ),
        ),
        g["winner"],
        g["graded"],
    )
]

g["market_spread_target_winner"] = [
    target_correct(t, w)
    if graded else np.nan

    for t, w, graded in zip(
        g.get(
            "market_spread_signal_target",
            pd.Series(
                [np.nan] * len(g)
            ),
        ),
        g["winner"],
        g["graded"],
    )
]

# Important:
# spread_target_winner only measures whether the targeted team
# won outright. It does NOT grade against the run-line price.
# We keep the name explicit so it cannot be mistaken for ATS.

# =========================================================
# OUTPUT
# =========================================================

out = (
    HISTORY /
    "MLB_GRADED_MARKET_RESEARCH.csv"
)

g.to_csv(
    out,
    index=False,
)

print(
    "SPORTS HULK MARKET RESEARCH GRADER: DONE"
)

print(
    "Research rows:",
    len(g)
)

print(
    "Graded rows:",
    int(g["graded"].sum())
)

print(
    "Pending rows:",
    int((~g["graded"]).sum())
)

graded = g[
    g["graded"]
].copy()

if len(graded):
    print(
        "\n=== HULK ACCURACY BY MARKET ALIGNMENT ==="
    )

    board = (
        graded
        .groupby(
            "market_research_alignment",
            dropna=False,
        )
        .agg(
            samples=(
                "lean_correct",
                "size",
            ),
            hulk_wins=(
                "lean_correct",
                "sum",
            ),
            hulk_accuracy=(
                "lean_correct",
                "mean",
            ),
        )
        .reset_index()
    )

    board["hulk_accuracy_pct"] = (
        board["hulk_accuracy"]
        * 100.0
    )

    print(
        board[
            [
                "market_research_alignment",
                "samples",
                "hulk_wins",
                "hulk_accuracy_pct",
            ]
        ]
        .sort_values(
            [
                "samples",
                "hulk_accuracy_pct",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .to_string(index=False)
    )

    if (
        "market_ml_signal_strength"
        in graded.columns
    ):
        print(
            "\n=== MONEYLINE SIGNAL RESULTS ==="
        )

        ml = graded[
            graded[
                "market_ml_target_correct"
            ].notna()
        ]

        if len(ml):
            x = (
                ml.groupby(
                    "market_ml_signal_strength",
                    dropna=False,
                )
                .agg(
                    samples=(
                        "market_ml_target_correct",
                        "size",
                    ),
                    correct=(
                        "market_ml_target_correct",
                        "sum",
                    ),
                    accuracy=(
                        "market_ml_target_correct",
                        "mean",
                    ),
                )
                .reset_index()
            )

            x["accuracy_pct"] = (
                x["accuracy"] * 100.0
            )

            print(
                x[
                    [
                        "market_ml_signal_strength",
                        "samples",
                        "correct",
                        "accuracy_pct",
                    ]
                ]
                .to_string(index=False)
            )
        else:
            print(
                "No graded moneyline signals yet."
            )
else:
    print(
        "\nNo finalized market-research games yet."
    )
