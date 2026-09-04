from pathlib import Path
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"
LATEST=HERE/"latest"
DERIVED.mkdir(parents=True,exist_ok=True)

def team_game_rows(g):
    home=pd.DataFrame({
        "gamePk":g.gamePk,"date":g.officialDate,"team":g.home_team,"opp":g.away_team,
        "is_home":1,"runs_for":g.home_score,"runs_against":g.away_score,
        "days_since_last":g.get("home_days_since_last",np.nan)
    })
    away=pd.DataFrame({
        "gamePk":g.gamePk,"date":g.officialDate,"team":g.away_team,"opp":g.home_team,
        "is_home":0,"runs_for":g.away_score,"runs_against":g.home_score,
        "days_since_last":g.get("away_days_since_last",np.nan)
    })
    return pd.concat([home,away],ignore_index=True)

def build():
    f=DERIVED/"MLB_GAME_MASTER.csv"
    if not f.exists(): raise SystemExit("Missing MLB_GAME_MASTER.csv")
    g=pd.read_csv(f,low_memory=False)
    g["officialDate"]=pd.to_datetime(g["officialDate"],errors="coerce")
    g["home_score"]=pd.to_numeric(g["home_score"],errors="coerce")
    g["away_score"]=pd.to_numeric(g["away_score"],errors="coerce")
    g=g[g["officialDate"].notna()].copy().sort_values(["officialDate","gamePk"])

    t=team_game_rows(g)
    t["runs_for"]=pd.to_numeric(t["runs_for"],errors="coerce")
    t["runs_against"]=pd.to_numeric(t["runs_against"],errors="coerce")
    t["win"]=(t["runs_for"]>t["runs_against"]).astype(float)
    # Incomplete/future games must not create fake wins.
    incomplete=t["runs_for"].isna() | t["runs_against"].isna()
    t.loc[incomplete,"win"]=np.nan

    t=t.sort_values(["team","date","gamePk"]).reset_index(drop=True)
    grp=t.groupby("team",group_keys=False)

    # Leakage-safe: every rolling value is shifted one game.
    for window in [5,10,20]:
        t[f"pregame_rs_{window}"]=grp["runs_for"].transform(lambda s:s.shift(1).rolling(window,min_periods=max(2,window//2)).mean())
        t[f"pregame_ra_{window}"]=grp["runs_against"].transform(lambda s:s.shift(1).rolling(window,min_periods=max(2,window//2)).mean())
        t[f"pregame_winpct_{window}"]=grp["win"].transform(lambda s:s.shift(1).rolling(window,min_periods=max(2,window//2)).mean())
        t[f"pregame_rdiff_{window}"]=t[f"pregame_rs_{window}"]-t[f"pregame_ra_{window}"]

    # Keep rest-day columns from MLB_GAME_MASTER itself. Re-merging team-game
    # rest here would create duplicate home/away column names and pandas suffixes.
    keep=["gamePk","team"]+[c for c in t.columns if c.startswith("pregame_")]
    h=t[t.is_home==1][keep].copy()
    a=t[t.is_home==0][keep].copy()
    h=h.rename(columns={c:f"home_{c}" for c in h.columns if c not in ["gamePk","team"]}).rename(columns={"team":"home_team"})
    a=a.rename(columns={c:f"away_{c}" for c in a.columns if c not in ["gamePk","team"]}).rename(columns={"team":"away_team"})

    hist=g.merge(h,on=["gamePk","home_team"],how="left").merge(a,on=["gamePk","away_team"],how="left")
    hist["month"]=hist["officialDate"].dt.month
    hist["home_win"]=np.where(hist.home_score>hist.away_score,1,np.where(hist.home_score<hist.away_score,0,np.nan))
    hist["total_runs"]=hist.home_score+hist.away_score
    hist["home_margin"]=hist.home_score-hist.away_score

    # Attach historical park factor for the same season/venue where available.
    pf=DERIVED/"MLB_PARK_RUN_FACTORS.csv"
    if pf.exists():
        p=pd.read_csv(pf,low_memory=False)
        p["season"]=pd.to_numeric(p["season"],errors="coerce")
        hist["season"]=hist["officialDate"].dt.year
        hist=hist.merge(p[["season","venue","run_factor"]],on=["season","venue"],how="left")
        hist=hist.rename(columns={"run_factor":"park_run_factor"})

    hist.to_csv(DERIVED/"MLB_HISTORICAL_PREGAME_FEATURES.csv",index=False)
    hist.to_parquet(DERIVED/"MLB_HISTORICAL_PREGAME_FEATURES.parquet",index=False)

    # Current team feature state = latest completed/known pregame line plus updates from most recent result.
    latest=[]
    for team,gg in t.groupby("team"):
        gg=gg.sort_values(["date","gamePk"]).copy()

        # Current form must come from completed games only.
        # Future/postponed rows can create long NaN tails and wipe out rolling form.
        completed=gg[gg["runs_for"].notna() & gg["runs_against"].notna()].copy()
        if completed.empty:
            continue

        last_completed=completed.iloc[-1]
        rec={"team":team}

        # Recalculate rolling form directly from the most recent completed results.
        # This represents information known after the last completed game and before
        # the next scheduled game.
        for window in [5,10,20]:
            tail=completed.tail(window)
            minp=max(2,window//2)
            if len(tail) >= minp:
                rec[f"pregame_rs_{window}"]=tail["runs_for"].mean()
                rec[f"pregame_ra_{window}"]=tail["runs_against"].mean()
                rec[f"pregame_winpct_{window}"]=tail["win"].mean()
                rec[f"pregame_rdiff_{window}"]=rec[f"pregame_rs_{window}"]-rec[f"pregame_ra_{window}"]
            else:
                rec[f"pregame_rs_{window}"]=float("nan")
                rec[f"pregame_ra_{window}"]=float("nan")
                rec[f"pregame_winpct_{window}"]=float("nan")
                rec[f"pregame_rdiff_{window}"]=float("nan")

        rec["days_since_last_game_date"]=last_completed.get("date")
        latest.append(rec)

    pd.DataFrame(latest).to_csv(DERIVED/"MLB_CURRENT_TEAM_FORM.csv",index=False)

    print(f"Historical games with pregame features: {len(hist):,}")
    print(f"Current team-form rows: {len(latest):,}")
    print("SPORTS HULK MLB HISTORICAL PREGAME FEATURES: DONE")

if __name__=="__main__": build()
