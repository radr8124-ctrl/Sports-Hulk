from pathlib import Path
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"
DERIVED.mkdir(parents=True,exist_ok=True)

def build():
    f=DERIVED/"MLB_GAME_MASTER.csv"
    if not f.exists():
        raise SystemExit("Missing MLB_GAME_MASTER.csv")
    d=pd.read_csv(f,low_memory=False)
    d["officialDate"]=pd.to_datetime(d["officialDate"],errors="coerce")
    d["home_score"]=pd.to_numeric(d["home_score"],errors="coerce")
    d["away_score"]=pd.to_numeric(d["away_score"],errors="coerce")
    d=d[d["home_score"].notna() & d["away_score"].notna()].copy()
    d["total_runs"]=d["home_score"]+d["away_score"]
    d["season"]=d["officialDate"].dt.year

    # Build park run factor from completed historical games.
    league=d.groupby("season")["total_runs"].mean().rename("league_runs_per_game")
    rows=[]
    for (season,venue,venue_id),g in d.groupby(["season","venue","venue_id"],dropna=False):
        lg=float(league.get(season,np.nan))
        avg=float(g["total_runs"].mean())
        factor=avg/lg if lg and not np.isnan(lg) else np.nan
        rows.append({
            "season":season,"venue":venue,"venue_id":venue_id,
            "games":len(g),"avg_total_runs":avg,
            "league_runs_per_game":lg,"run_factor":factor
        })
    out=pd.DataFrame(rows)
    out.to_csv(DERIVED/"MLB_PARK_RUN_FACTORS.csv",index=False)
    out.to_parquet(DERIVED/"MLB_PARK_RUN_FACTORS.parquet",index=False)
    print(f"Park-factor rows: {len(out):,}")
    print("SPORTS HULK MLB PARK FACTORS: DONE")

if __name__=="__main__":
    build()
