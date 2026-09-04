from pathlib import Path
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
HISTORY=HERE/"history"
DERIVED=HERE/"derived"
DERIVED.mkdir(parents=True,exist_ok=True)

BUCKETS=[0,.10,.20,.30,.40,.55,.75,1.0,999]
LABELS=["0-.10",".10-.20",".20-.30",".30-.40",".40-.55",".55-.75",".75-1.0","1.0+"]

def american_profit(odds):
    try:o=float(odds)
    except:return np.nan
    if o==0:return np.nan
    return o/100 if o>0 else 100/abs(o)

def build():
    f=HISTORY/"MLB_GRADED_PREDICTIONS.csv"
    if not f.exists():
        raise SystemExit("No graded predictions. Run result_grader.py first.")
    d=pd.read_csv(f,low_memory=False)
    d=d[d["graded"]==True].copy()
    if d.empty:
        print("No finalized predictions yet. Calibration will begin after games are graded.")
        return
    raw = d["lean_correct"].copy()
    num = __import__("pandas").to_numeric(raw, errors="coerce")
    text = raw.astype(str).str.strip().str.lower()
    num[text.isin(["true","t","yes","y"])] = 1.0
    num[text.isin(["false","f","no","n"])] = 0.0
    d["lean_correct"] = num
    d["abs_edge"]=pd.to_numeric(d["abs_edge"],errors="coerce")
    d["edge_bucket"]=pd.cut(d["abs_edge"],bins=BUCKETS,labels=LABELS,right=False)

    rows=[]
    for bucket,g in d.groupby("edge_bucket",observed=False):
        if len(g)==0: continue
        rows.append({
          "edge_bucket":str(bucket),
          "samples":len(g),
          "wins":int(g["lean_correct"].fillna(0).sum()),
          "hit_rate":float(g["lean_correct"].mean())
        })
    edge=pd.DataFrame(rows)
    edge.to_csv(DERIVED/"MLB_CALIBRATION_EDGE_BUCKETS.csv",index=False)

    groups=[]
    for (conf,decision),g in d.groupby(["confidence","decision"],dropna=False):
        groups.append({
          "confidence":conf,"decision":decision,"samples":len(g),
          "wins":int(g["lean_correct"].fillna(0).sum()),
          "hit_rate":float(g["lean_correct"].mean()),
          "avg_abs_edge":float(g["abs_edge"].mean())
        })
    grp=pd.DataFrame(groups)
    grp.to_csv(DERIVED/"MLB_CALIBRATION_BY_CONFIDENCE_DECISION.csv",index=False)

    # Threshold recommendation is informational only and sample-gated.
    eligible=edge[edge["samples"]>=50].copy()
    recommendation="INSUFFICIENT SAMPLE"
    if not eligible.empty:
        # first bucket with >=55% hit rate, conservative starter target.
        e=eligible[eligible["hit_rate"]>=.55]
        if not e.empty:
            recommendation=f"REVIEW {e.iloc[0]['edge_bucket']} AS POSSIBLE WATCH/BET REGION"
        else:
            recommendation="NO EDGE BUCKET CLEARS 55% YET"

    (DERIVED/"MLB_CALIBRATION_SUMMARY.txt").write_text(
      f"Graded samples: {len(d)}\n"
      f"Overall lean hit rate: {d['lean_correct'].mean():.3f}\n"
      f"Recommendation: {recommendation}\n"
      "NOTE: thresholds are NOT changed automatically.\n"
    )

    print(f"Graded samples used: {len(d):,}")
    print(f"Overall lean hit rate: {d['lean_correct'].mean():.3f}")
    print(f"Recommendation: {recommendation}")
    print("SPORTS HULK MLB CALIBRATION REPORT: DONE")

if __name__=="__main__": build()
