from pathlib import Path
import pandas as pd
import numpy as np

HERE = Path(__file__).resolve().parent
DERIVED = HERE / "derived"

def quality_from_distance(x):
    if pd.isna(x):
        return "UNKNOWN"
    if x < 0.35:
        return "A"
    if x < 0.50:
        return "B"
    if x < 0.70:
        return "C"
    return "D"

def run():
    board = DERIVED / "MLB_MATCHUP_BOARD_FULL.csv"
    comps = DERIVED / "MLB_HISTORICAL_COMPS_SUMMARY.csv"
    cal = DERIVED / "MLB_COMP_CALIBRATION_SUMMARY.csv"

    if not board.exists():
        raise SystemExit("Missing MLB_MATCHUP_BOARD_FULL.csv")
    if not comps.exists():
        raise SystemExit("Missing MLB_HISTORICAL_COMPS_SUMMARY.csv")

    b = pd.read_csv(board, low_memory=False)
    c = pd.read_csv(comps, low_memory=False)

    # Avoid duplicate comp columns if board already has an older merge.
    comp_cols = [
        "gamePk","away_team","home_team","comp_count","features_used",
        "comp_home_win_rate","comp_avg_total_runs","comp_avg_home_margin",
        "comp_median_distance"
    ]
    c = c[[x for x in comp_cols if x in c.columns]].copy()

    drop = [x for x in c.columns if x in b.columns and x not in ["gamePk","away_team","home_team"]]
    if drop:
        b = b.drop(columns=drop)

    out = b.merge(c, on=["gamePk","away_team","home_team"], how="left")
    out["comp_quality_grade"] = out["comp_median_distance"].map(quality_from_distance)

    # Descriptive comp directional signal only. Does NOT alter HULK decision.
    out["comp_side"] = np.select(
        [
            out["comp_home_win_rate"] >= 0.60,
            out["comp_home_win_rate"] <= 0.40,
        ],
        ["HOME", "AWAY"],
        default="NEUTRAL"
    )

    # If a legacy/home_edge field is available, compare directions for research only.
    edge_col = None
    for cnd in ["home_edge","edge_score","matchup_edge","HULK_edge"]:
        if cnd in out.columns:
            edge_col = cnd
            break

    if edge_col:
        edge = pd.to_numeric(out[edge_col], errors="coerce")
        hulk_side = np.where(edge > 0, "HOME", np.where(edge < 0, "AWAY", "NEUTRAL"))
        out["hulk_model_side"] = hulk_side
        out["comp_alignment"] = np.where(
            out["comp_side"] == "NEUTRAL",
            "NEUTRAL",
            np.where(out["comp_side"] == out["hulk_model_side"], "SUPPORT", "CONFLICT")
        )
    else:
        out["hulk_model_side"] = "UNKNOWN"
        out["comp_alignment"] = "UNSCORED"

    # Add historical bucket calibration as reference, still no threshold change.
    if cal.exists():
        k = pd.read_csv(cal, low_memory=False)
        m = {
            "A": "A_CLOSE",
            "B": "B_GOOD",
            "C": "C_FAIR",
            "D": "D_LOOSE",
        }
        lookup = k[k["bucket"] != "ALL"].set_index("bucket")
        def bucket_stat(grade, col):
            key = m.get(grade)
            if key in lookup.index and col in lookup.columns:
                return lookup.loc[key, col]
            return np.nan
        out["comp_bucket_hist_accuracy"] = [
            bucket_stat(g, "winner_accuracy") for g in out["comp_quality_grade"]
        ]
        out["comp_bucket_hist_samples"] = [
            bucket_stat(g, "samples") for g in out["comp_quality_grade"]
        ]

    out.to_csv(DERIVED / "MLB_MATCHUP_BOARD_INTELLIGENCE.csv", index=False)
    out.to_parquet(DERIVED / "MLB_MATCHUP_BOARD_INTELLIGENCE.parquet", index=False)

    print(f"Intelligence board games: {len(out):,}")
    print("Comp quality grades:", out["comp_quality_grade"].value_counts(dropna=False).to_dict())
    print("Comp sides:", out["comp_side"].value_counts(dropna=False).to_dict())
    print("Comp alignment:", out["comp_alignment"].value_counts(dropna=False).to_dict())
    print("SPORTS HULK MLB COMP INTELLIGENCE OVERLAY: DONE")

if __name__ == "__main__":
    run()
