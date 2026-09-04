from pathlib import Path
import pandas as pd
HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"

def run():
    f=DERIVED/"MLB_DECISION_BRAIN_RESEARCH.csv"
    d=pd.read_csv(f,low_memory=False)
    cols=[c for c in [
        "away_team","home_team","decision","confidence","decision_brain_edge_column",
        "hulk_model_side","comp_side","comp_alignment","comp_quality_grade",
        "comp_bucket_hist_accuracy","comp_bucket_hist_samples",
        "comp_reliability_0_1","comp_effective_strength_0_1",
        "research_guardrail","research_consensus_score"
    ] if c in d.columns]
    print("=== SPORTS HULK MLB DECISION BRAIN RESEARCH BOARD ===")
    print(d[cols].to_string(index=False))
    print("")
    print("Guardrail: this build cannot create a new BET.")
    print("It can only annotate PASS/WATCH while we accumulate clean graded predictions.")
    print("SPORTS HULK MLB DECISION BRAIN REPORT: DONE")
if __name__=="__main__": run()
