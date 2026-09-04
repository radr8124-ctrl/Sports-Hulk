from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
import pandas as pd

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"
HISTORY=HERE/"history"
HISTORY.mkdir(parents=True,exist_ok=True)

def snapshot():
    src=DERIVED/"MLB_MATCHUP_BOARD.csv"
    if not src.exists():
        raise SystemExit("Missing MLB_MATCHUP_BOARD.csv. Run matchup_engine.py first.")
    df=pd.read_csv(src,low_memory=False)
    now=datetime.now(timezone.utc).isoformat()
    df["prediction_timestamp_utc"]=now
    # Stable snapshot id tied to board contents + timestamp.
    payload=(df.to_csv(index=False)+now).encode()
    sid=hashlib.sha256(payload).hexdigest()[:16]
    df["snapshot_id"]=sid

    out=HISTORY/"MLB_PREDICTION_HISTORY.csv"
    if out.exists():
        old=pd.read_csv(out,low_memory=False)
        merged=pd.concat([old,df],ignore_index=True,sort=False)
    else:
        merged=df
    merged.to_csv(out,index=False)

    snap=HISTORY/f"MLB_PREDICTION_SNAPSHOT_{sid}.csv"
    df.to_csv(snap,index=False)

    print(f"Snapshot ID: {sid}")
    print(f"Predictions saved: {len(df):,}")
    print(f"Prediction history rows: {len(merged):,}")
    print("SPORTS HULK MLB PREDICTION SNAPSHOT: DONE")

if __name__=="__main__": snapshot()
