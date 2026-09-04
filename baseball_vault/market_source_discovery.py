from pathlib import Path
import pandas as pd, json, re, numpy as np

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"
RAW=HERE/"raw"
LATEST=HERE/"latest"

def csvs():
    roots=[DERIVED,LATEST,RAW]
    out=[]
    for r in roots:
        if r.exists():
            out += list(r.rglob("*.csv"))
    return sorted(set(out))

def score_market_file(p):
    name=p.name.lower()
    score=sum(k in name for k in ["odd","market","sports","sgo","line"])
    try:
        d=pd.read_csv(p,nrows=100,low_memory=False)
    except Exception:
        return None
    cn=" ".join(c.lower() for c in d.columns)
    score += sum(k in cn for k in ["price","odds","spread","total","book","market","line"])
    return score,d

def run():
    ranked=[]
    for p in csvs():
        x=score_market_file(p)
        if x and x[0]>0:
            ranked.append((x[0],p,x[1]))
    ranked.sort(key=lambda x:x[0],reverse=True)

    rows=[]
    for sc,p,d in ranked[:12]:
        rows.append({
            "score":sc,
            "file":str(p),
            "rows_sampled":len(d),
            "columns":" | ".join(d.columns.astype(str))
        })
    pd.DataFrame(rows).to_csv(DERIVED/"MLB_MARKET_SOURCE_DISCOVERY.csv",index=False)
    print("Candidate market files:",len(rows))
    for r in rows[:8]:
        print(r["score"], Path(r["file"]).name)
    print("SPORTS HULK MLB MARKET SOURCE DISCOVERY: DONE")
if __name__=="__main__": run()
