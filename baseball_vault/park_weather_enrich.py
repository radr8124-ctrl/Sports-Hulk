from pathlib import Path
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"
LATEST=HERE/"latest"

def latest_park_factor():
    f=DERIVED/"MLB_PARK_RUN_FACTORS.csv"
    if not f.exists(): return pd.DataFrame()
    p=pd.read_csv(f,low_memory=False)
    p["season"]=pd.to_numeric(p["season"],errors="coerce")
    p["games"]=pd.to_numeric(p["games"],errors="coerce")
    p=p[p["games"]>=20].copy()
    if p.empty:return p
    p=p.sort_values("season").groupby("venue",as_index=False).tail(1)
    return p[["venue","run_factor","games","season"]].rename(columns={
        "run_factor":"park_run_factor",
        "games":"park_factor_games",
        "season":"park_factor_season"
    })

def build():
    bf=DERIVED/"MLB_MATCHUP_BOARD.csv"
    sf=LATEST/"MLB_SCHEDULE.csv"
    if not bf.exists() or not sf.exists():
        raise SystemExit("Missing matchup board or latest schedule.")
    b=pd.read_csv(bf,low_memory=False)
    s=pd.read_csv(sf,low_memory=False)
    keep=[c for c in ["gamePk","venue","venue_id"] if c in s.columns]
    if keep:
        b=b.merge(s[keep].drop_duplicates("gamePk"),on="gamePk",how="left")

    p=latest_park_factor()
    if not p.empty and "venue" in b.columns:
        b=b.merge(p,on="venue",how="left")

    wf=DERIVED/"MLB_WEATHER_FEATURES.csv"
    if wf.exists():
        w=pd.read_csv(wf,low_memory=False)
        keep=[c for c in ["gamePk","temperature_f","precipitation","wind_mph","wind_gust_mph","humidity_pct","weather_hour_utc"] if c in w.columns]
        b=b.merge(w[keep].drop_duplicates("gamePk"),on="gamePk",how="left")

    # Transparent environment flags only; do not force betting decisions yet.
    b["run_environment_flag"]="NEUTRAL"
    if "park_run_factor" in b.columns:
        b.loc[pd.to_numeric(b["park_run_factor"],errors="coerce")>=1.08,"run_environment_flag"]="HITTER_FRIENDLY"
        b.loc[pd.to_numeric(b["park_run_factor"],errors="coerce")<=0.92,"run_environment_flag"]="PITCHER_FRIENDLY"

    b.to_csv(DERIVED/"MLB_MATCHUP_BOARD_ENRICHED.csv",index=False)
    b.to_parquet(DERIVED/"MLB_MATCHUP_BOARD_ENRICHED.parquet",index=False)
    print(f"Enriched matchup games: {len(b):,}")
    print("SPORTS HULK MLB PARK/WEATHER ENRICHMENT: DONE")

if __name__=="__main__":
    build()
