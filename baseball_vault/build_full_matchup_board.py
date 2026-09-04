from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"

def build():
    b=pd.read_csv(DERIVED/"MLB_MATCHUP_BOARD_ENRICHED.csv",low_memory=False)
    c=pd.read_csv(DERIVED/"MLB_HISTORICAL_COMPS_SUMMARY.csv",low_memory=False)
    out=b.merge(c,on=["gamePk","away_team","home_team"],how="left")
    out.to_csv(DERIVED/"MLB_MATCHUP_BOARD_FULL.csv",index=False)
    out.to_parquet(DERIVED/"MLB_MATCHUP_BOARD_FULL.parquet",index=False)
    print(f"Full matchup games: {len(out):,}")
    print(f"Games with historical comps: {int(out['comp_count'].notna().sum()):,}")
    print("SPORTS HULK MLB FULL MATCHUP BOARD: DONE")

if __name__=="__main__": build()
