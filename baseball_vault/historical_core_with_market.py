from pathlib import Path
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"

def run():
    hist=pd.read_csv(DERIVED/"MLB_HISTORICAL_PREGAME_FEATURES.csv",low_memory=False)
    # Normalize MLB game IDs so values such as 824633 and 824633.0 join cleanly.
    hist["gamePk"]=pd.to_numeric(hist["gamePk"],errors="coerce").astype("Int64").astype(str)

    cov=pd.read_csv(DERIVED/"MLB_MARKET_GAME_COVERAGE.csv",low_memory=False)
    cov["gamePk"]=pd.to_numeric(cov["gamePk"],errors="coerce").astype("Int64").astype(str)

    mh=pd.read_csv(DERIVED/"MLB_MARKET_HISTORY_RECONCILED.csv",low_memory=False)
    mh["gamePk"]=pd.to_numeric(mh["gamePk"],errors="coerce").astype("Int64").astype(str)

    # Aggregate movement context to game level without inventing direction.
    agg=mh.groupby("gamePk").agg(
        hist_market_rows=("gamePk","size"),
        hist_market_books=("book","nunique"),
        hist_avg_abs_point_move=("point_move",lambda s:pd.to_numeric(s,errors="coerce").abs().mean()),
        hist_avg_abs_price_move=("price_move",lambda s:pd.to_numeric(s,errors="coerce").abs().mean()),
        hist_point_move_std=("point_move",lambda s:pd.to_numeric(s,errors="coerce").std()),
        hist_price_move_std=("price_move",lambda s:pd.to_numeric(s,errors="coerce").std()),
    ).reset_index()

    out=hist.merge(agg,on="gamePk",how="left")
    out["historical_market_known"]=out["hist_market_rows"].notna()

    out.to_csv(DERIVED/"MLB_HISTORICAL_CORE_WITH_MARKET.csv",index=False)
    out.to_parquet(DERIVED/"MLB_HISTORICAL_CORE_WITH_MARKET.parquet",index=False)

    print(f"Historical core games: {len(out):,}")
    print(f"Games with reconciled market context: {int(out.historical_market_known.sum()):,}")
    print("SPORTS HULK MLB HISTORICAL CORE WITH MARKET: DONE")

if __name__=="__main__":
    run()
