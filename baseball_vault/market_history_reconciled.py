from pathlib import Path
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"

def run():
    f=DERIVED/"MLB_MARKET_RECONCILED_ROWS.csv"
    d=pd.read_csv(f,low_memory=False)
    d=d[d["match_status"]=="MATCHED"].copy()
    if d.empty:
        raise SystemExit("No matched market rows")

    d["market_time"]=pd.to_datetime(d["market_time"],errors="coerce",utc=True)
    d["price"]=pd.to_numeric(d["price"],errors="coerce")
    d["point"]=pd.to_numeric(d["point"],errors="coerce")

    keys=["gamePk","book","market","side"]
    d["_ord"]=np.arange(len(d))
    d=d.sort_values(["gamePk","book","market","side","market_time","_ord"],na_position="first")

    first=d.groupby(keys,dropna=False).first(numeric_only=False).reset_index()
    last=d.groupby(keys,dropna=False).last(numeric_only=False).reset_index()

    keep=keys+["price","point","market_time"]
    first=first[keep].rename(columns={"price":"open_price","point":"open_point","market_time":"open_time"})
    last=last[keep+["mlb_away_team","mlb_home_team"]].rename(columns={"price":"current_price","point":"current_point","market_time":"current_time"})

    out=last.merge(first,on=keys,how="left")
    out["price_move"]=out["current_price"]-out["open_price"]
    out["point_move"]=out["current_point"]-out["open_point"]

    out.to_csv(DERIVED/"MLB_MARKET_HISTORY_RECONCILED.csv",index=False)
    out.to_parquet(DERIVED/"MLB_MARKET_HISTORY_RECONCILED.parquet",index=False)

    coverage=out.groupby("gamePk").agg(
        market_rows=("gamePk","size"),
        books=("book","nunique"),
        open_price_rows=("open_price",lambda s:s.notna().sum()),
        current_price_rows=("current_price",lambda s:s.notna().sum()),
        open_point_rows=("open_point",lambda s:s.notna().sum()),
        current_point_rows=("current_point",lambda s:s.notna().sum()),
    ).reset_index()
    coverage.to_csv(DERIVED/"MLB_MARKET_GAME_COVERAGE.csv",index=False)

    print(f"Reconciled market-history rows: {len(out):,}")
    print(f"Unique MLB games with market history: {out.gamePk.nunique():,}")
    print("SPORTS HULK MLB RECONCILED MARKET HISTORY: DONE")

if __name__=="__main__":
    run()
