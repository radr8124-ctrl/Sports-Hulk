from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"

def run():
    d=pd.read_csv(DERIVED/"MLB_HIGH_CONVICTION_RESEARCH.csv",low_memory=False)
    cols=[c for c in [
        "away_team","home_team","decision","confidence","hulk_model_side","comp_side",
        "comp_alignment","comp_quality_grade","comp_bucket_hist_accuracy",
        "comp_bucket_hist_samples","market_rows","books","avg_abs_point_move",
        "current_point_std","market_disagreement_flag","high_conviction_research",
        "high_conviction_reason"
    ] if c in d.columns]
    print("=== SPORTS HULK MLB MARKET + HIGH-CONVICTION BOARD ===")
    print(d[cols].to_string(index=False))
    print("")
    print("NOTE: high_conviction_research is a research flag, NOT a live BET promotion.")
    print("SPORTS HULK MLB MARKET CONTEXT REPORT: DONE")

if __name__=="__main__": run()
