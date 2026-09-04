from pathlib import Path
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"
HISTORY=HERE/"history"
HISTORY.mkdir(parents=True,exist_ok=True)

def norm_gamepk(s):
    return pd.to_numeric(s,errors="coerce").astype("Int64")

def load_results():
    parts=[]
    rf=HISTORY/"MLB_RESULTS_HISTORY.csv"
    if rf.exists():
        r=pd.read_csv(rf,low_memory=False)
        if "gamePk" in r: parts.append(r)
    mf=DERIVED/"MLB_GAME_MASTER.csv"
    if mf.exists():
        m=pd.read_csv(mf,low_memory=False)
        keep=[c for c in ["gamePk","home_team","away_team","home_score","away_score","status"] if c in m.columns]
        if "gamePk" in keep: parts.append(m[keep])
    if not parts:
        raise SystemExit("No result source available.")
    r=pd.concat(parts,ignore_index=True,sort=False)
    r["gamePk"]=norm_gamepk(r["gamePk"])
    r["home_score"]=pd.to_numeric(r.get("home_score"),errors="coerce")
    r["away_score"]=pd.to_numeric(r.get("away_score"),errors="coerce")
    r["_has_score"]=r["home_score"].notna() & r["away_score"].notna()
    r=r.sort_values(["gamePk","_has_score"]).drop_duplicates("gamePk",keep="last")
    return r

def grade():
    histf=HISTORY/"MLB_PREDICTION_HISTORY.csv"
    if not histf.exists():
        raise SystemExit("No prediction history yet.")
    h=pd.read_csv(histf,low_memory=False)
    r=load_results()
    h["gamePk"]=norm_gamepk(h["gamePk"])
    r["finalized"]=r["home_score"].notna() & r["away_score"].notna()
    r["winner"]=np.where(r["home_score"]>r["away_score"],r["home_team"],
                np.where(r["away_score"]>r["home_score"],r["away_team"],"TIE"))
    cols=["gamePk","home_score","away_score","finalized","winner"]
    g=h.merge(r[cols],on="gamePk",how="left")
    g["graded"]=g["finalized"].fillna(False)
    g["lean_correct"]=np.where(g["graded"],g["lean"].astype(str)==g["winner"].astype(str),np.nan)
    g["abs_edge"]=pd.to_numeric(g["home_edge_score"],errors="coerce").abs()
    g.to_csv(HISTORY/"MLB_GRADED_PREDICTIONS.csv",index=False)
    print(f"Prediction rows: {len(g):,}")
    print(f"Graded rows: {int(g['graded'].sum()):,}")
    print(f"Pending rows: {int((~g['graded']).sum()):,}")
    print("SPORTS HULK MLB PREDICTION GRADER: DONE")

if __name__=="__main__":
    grade()
