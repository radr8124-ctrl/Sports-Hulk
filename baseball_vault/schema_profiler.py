from pathlib import Path
import pandas as pd, json, re

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"
LATEST=HERE/"latest"
OUT=DERIVED/"MLB_SCHEMA_PROFILE.json"

FILES=[
    DERIVED/"MLB_MATCHUP_BOARD_INTELLIGENCE.csv",
    DERIVED/"MLB_MATCHUP_BOARD_FULL.csv",
    DERIVED/"MLB_MATCHUP_BOARD_ENRICHED.csv",
    LATEST/"MLB_ODDS.csv",
    LATEST/"MLB_MARKETS.csv",
]

def profile_file(p):
    if not p.exists():
        return None
    try:
        d=pd.read_csv(p,low_memory=False)
    except Exception:
        return None
    cols=[]
    for c in d.columns:
        s=d[c]
        sample=s.dropna().astype(str).head(3).tolist()
        cols.append({
            "name":c,
            "dtype":str(s.dtype),
            "non_null":int(s.notna().sum()),
            "unique":int(s.nunique(dropna=True)),
            "sample":sample,
        })
    return {"path":str(p),"rows":len(d),"columns":cols}

def run():
    info=[x for x in (profile_file(p) for p in FILES) if x]
    OUT.write_text(json.dumps(info,indent=2))
    print("Schema files profiled:",len(info))
    for f in info:
        print(Path(f["path"]).name, "rows=",f["rows"], "cols=",len(f["columns"]))
    print("SPORTS HULK MLB SCHEMA PROFILER: DONE")
if __name__=="__main__": run()
