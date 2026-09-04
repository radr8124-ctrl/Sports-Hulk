from pathlib import Path
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"
LATEST=HERE/"latest"

FEATURES=[
 "home_pregame_rs_10","home_pregame_ra_10","home_pregame_winpct_10","home_pregame_rdiff_10",
 "away_pregame_rs_10","away_pregame_ra_10","away_pregame_winpct_10","away_pregame_rdiff_10",
 "park_run_factor","home_days_since_last","away_days_since_last"
]

def zdistance(hist,row,cols):
    dist=np.zeros(len(hist),dtype=float)
    used=0
    for c in cols:
        if c not in hist or c not in row or pd.isna(row[c]): continue
        s=pd.to_numeric(hist[c],errors="coerce")
        sd=s.std(ddof=0)
        if pd.isna(sd) or sd==0: continue
        z=(s-float(row[c]))/sd
        z=z.fillna(2.5).clip(-4,4)
        dist+=z.to_numpy()**2
        used+=1
    return np.sqrt(dist/max(used,1)),used

def current_rows():
    sched=pd.read_csv(LATEST/"MLB_SCHEDULE.csv",low_memory=False)
    form=pd.read_csv(DERIVED/"MLB_CURRENT_TEAM_FORM.csv",low_memory=False)
    enriched=pd.read_csv(DERIVED/"MLB_MATCHUP_BOARD_ENRICHED.csv",low_memory=False)
    fm={r["team"]:r for _,r in form.iterrows()}
    rows=[]
    for _,g in sched.iterrows():
        h=fm.get(g.home_team,{}); a=fm.get(g.away_team,{})
        rec={"gamePk":g.gamePk,"gameDate":g.get("gameDate"),"home_team":g.home_team,"away_team":g.away_team}
        for c in ["pregame_rs_10","pregame_ra_10","pregame_winpct_10","pregame_rdiff_10"]:
            rec[f"home_{c}"]=h.get(c,np.nan)
            rec[f"away_{c}"]=a.get(c,np.nan)
        # Rest inferred from schedule date minus last team game date.
        gd=pd.to_datetime(g.get("gameDate"),errors="coerce",utc=True)
        for side,obj in [("home",h),("away",a)]:
            ld=pd.to_datetime(obj.get("days_since_last_game_date"),errors="coerce",utc=True)
            rec[f"{side}_days_since_last"]=(gd.normalize()-ld.normalize()).days if pd.notna(gd) and pd.notna(ld) else np.nan
        e=enriched[enriched.gamePk==g.gamePk] if "gamePk" in enriched else pd.DataFrame()
        rec["park_run_factor"]=e.iloc[0].get("park_run_factor",np.nan) if len(e) else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)

def build(n=25):
    hist=pd.read_csv(DERIVED/"MLB_HISTORICAL_PREGAME_FEATURES.csv",low_memory=False)
    hist["officialDate"]=pd.to_datetime(hist["officialDate"],errors="coerce",utc=True)
    # Completed historical games only.
    hist=hist[hist["home_win"].notna()].copy()
    cur=current_rows()
    summary=[]; detail=[]
    for _,r in cur.iterrows():
        gd=pd.to_datetime(r.gameDate,errors="coerce",utc=True)
        pool=hist[hist.officialDate < gd].copy() if pd.notna(gd) else hist.copy()
        d,used=zdistance(pool,r,FEATURES)
        pool=pool.assign(comp_distance=d).sort_values("comp_distance").head(n)
        if pool.empty:
            continue
        summary.append({
          "gamePk":r.gamePk,"away_team":r.away_team,"home_team":r.home_team,
          "comp_count":len(pool),"features_used":used,
          "comp_home_win_rate":float(pd.to_numeric(pool.home_win,errors="coerce").mean()),
          "comp_avg_total_runs":float(pd.to_numeric(pool.total_runs,errors="coerce").mean()),
          "comp_avg_home_margin":float(pd.to_numeric(pool.home_margin,errors="coerce").mean()),
          "comp_median_distance":float(pool.comp_distance.median())
        })
        for rank,(_,x) in enumerate(pool.iterrows(),1):
            detail.append({
              "current_gamePk":r.gamePk,"rank":rank,"distance":x.comp_distance,
              "historical_gamePk":x.gamePk,"historical_date":x.officialDate,
              "historical_away":x.away_team,"historical_home":x.home_team,
              "historical_home_score":x.home_score,"historical_away_score":x.away_score,
              "historical_total_runs":x.total_runs,"historical_home_margin":x.home_margin
            })
    s=pd.DataFrame(summary); d=pd.DataFrame(detail)
    s.to_csv(DERIVED/"MLB_HISTORICAL_COMPS_SUMMARY.csv",index=False)
    s.to_parquet(DERIVED/"MLB_HISTORICAL_COMPS_SUMMARY.parquet",index=False)
    d.to_csv(DERIVED/"MLB_HISTORICAL_COMPS_DETAIL.csv",index=False)
    print(f"Current games with comps: {len(s):,}")
    print(f"Historical comp rows: {len(d):,}")
    print("SPORTS HULK MLB HISTORICAL COMPS: DONE")

if __name__=="__main__": build()
