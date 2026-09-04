from pathlib import Path
import pandas as pd
import numpy as np

HERE = Path(__file__).resolve().parent
DERIVED = HERE / "derived"

def run():
    f = DERIVED / "MLB_MATCHUP_BOARD_INTELLIGENCE.csv"
    if not f.exists():
        raise SystemExit("Missing MLB_MATCHUP_BOARD_INTELLIGENCE.csv")
    d = pd.read_csv(f, low_memory=False)

    cols = [c for c in [
        "away_team","home_team","decision","confidence",
        "comp_quality_grade","comp_side","comp_alignment",
        "comp_home_win_rate","comp_avg_total_runs",
        "comp_avg_home_margin","comp_median_distance",
        "comp_bucket_hist_accuracy","comp_bucket_hist_samples"
    ] if c in d.columns]

    print("=== SPORTS HULK MLB INTELLIGENCE BOARD ===")
    print(d[cols].sort_values(
        ["comp_quality_grade","comp_median_distance"],
        na_position="last"
    ).to_string(index=False))

    print("")
    print("NOTE: Historical comps remain RESEARCH-ONLY in this build.")
    print("BET/WATCH/PASS thresholds were NOT changed.")
    print("SPORTS HULK MLB INTELLIGENCE REPORT: DONE")

if __name__ == "__main__":
    run()
