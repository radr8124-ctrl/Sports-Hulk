from pathlib import Path
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"

def run():
    f=DERIVED/"MLB_COMP_WALKFORWARD_RESULTS.csv"
    if not f.exists():
        raise SystemExit("Missing MLB_COMP_WALKFORWARD_RESULTS.csv")
    d=pd.read_csv(f,low_memory=False)

    # Study empirically strong comp subset only.
    # B_GOOD bucket is the currently validated bucket from the 750-game test.
    subset=d[d["distance_bucket"]=="B_GOOD"].copy()
    subset["strong_comp_signal"]=(
        ((subset["pred_home_win_rate"]>=0.60) | (subset["pred_home_win_rate"]<=0.40))
    )
    strong=subset[subset["strong_comp_signal"]].copy()

    rows=[]
    for name,g in [("B_GOOD_ALL",subset),("B_GOOD_STRONG_SIDE",strong)]:
        if len(g)==0:
            continue
        rows.append({
            "subset":name,
            "samples":len(g),
            "winner_accuracy":g["winner_correct"].mean(),
            "avg_pred_home_win_rate":g["pred_home_win_rate"].mean(),
            "total_mae":g["total_abs_error"].mean(),
            "margin_mae":g["margin_abs_error"].mean(),
        })
    out=pd.DataFrame(rows)
    out.to_csv(DERIVED/"MLB_HIGH_CONVICTION_BACKTEST.csv",index=False)

    print(out.to_string(index=False))
    print("SPORTS HULK MLB HIGH-CONVICTION BACKTEST: DONE")

if __name__=="__main__": run()
