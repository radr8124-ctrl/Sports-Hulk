from pathlib import Path
from datetime import date,datetime,timedelta
import argparse, json, urllib.parse, urllib.request
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
RAW=HERE/"raw"/"game_master"
DERIVED=HERE/"derived"
BASE="https://statsapi.mlb.com/api/v1/schedule"

def get_json(url,params):
    u=url+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(u,headers={"User-Agent":"Sports-HULK-Baseball/1.0"})
    with urllib.request.urlopen(req,timeout=120) as r: return json.loads(r.read().decode())

def season_dates(year):
    # broad window; StatsAPI returns only actual MLB games.
    return f"{year}-03-15",f"{year}-11-15"

def fetch_year(year,force=False):
    RAW.mkdir(parents=True,exist_ok=True)
    out=RAW/f"mlb_schedule_{year}.json"
    if out.exists() and not force: return json.loads(out.read_text())
    a,b=season_dates(year)
    d=get_json(BASE,{"sportId":1,"startDate":a,"endDate":b,"hydrate":"team,venue,linescore"})
    out.write_text(json.dumps(d))
    return d

def flatten(d):
    rows=[]
    for day in d.get("dates",[]):
      for g in day.get("games",[]):
        t=g.get("teams",{}); h=t.get("home",{}); a=t.get("away",{})
        rows.append({
          "gamePk":g.get("gamePk"),"officialDate":g.get("officialDate") or day.get("date"),
          "gameDate":g.get("gameDate"),"gameType":g.get("gameType"),
          "status":g.get("status",{}).get("detailedState"),
          "away_team":a.get("team",{}).get("name"),"away_team_id":a.get("team",{}).get("id"),
          "home_team":h.get("team",{}).get("name"),"home_team_id":h.get("team",{}).get("id"),
          "away_score":a.get("score"),"home_score":h.get("score"),
          "venue":g.get("venue",{}).get("name"),"venue_id":g.get("venue",{}).get("id"),
          "seriesDescription":g.get("seriesDescription"),"gameNumber":g.get("gameNumber")
        })
    return rows


def dedupe_gamepk(df):
    d=df.copy()
    d["_has_scores"]=(
        pd.to_numeric(d.get("home_score"),errors="coerce").notna()
        & pd.to_numeric(d.get("away_score"),errors="coerce").notna()
    )
    status=d.get("status",pd.Series("",index=d.index)).fillna("").astype(str).str.lower()
    d["_is_final"]=status.str.contains("final|completed",regex=True)
    d["_game_dt"]=pd.to_datetime(d.get("gameDate"),errors="coerce",utc=True)
    d=d.sort_values(
        ["gamePk","_has_scores","_is_final","_game_dt"],
        ascending=[True,True,True,True]
    )
    d=d.drop_duplicates("gamePk",keep="last")
    return d.drop(columns=["_has_scores","_is_final","_game_dt"],errors="ignore")

def add_rest(df):
    d=df.copy()
    d["officialDate"]=pd.to_datetime(d["officialDate"],errors="coerce")
    teamrows=[]
    for side in ["home","away"]:
        z=d[["gamePk","officialDate",f"{side}_team"]].rename(columns={f"{side}_team":"team"})
        teamrows.append(z)
    t=pd.concat(teamrows).sort_values(["team","officialDate","gamePk"])
    t["days_since_last_game"]=t.groupby("team")["officialDate"].diff().dt.days
    h=t.merge(d[["gamePk","home_team"]],left_on=["gamePk","team"],right_on=["gamePk","home_team"],how="inner")[["gamePk","days_since_last_game"]].rename(columns={"days_since_last_game":"home_days_since_last"})
    a=t.merge(d[["gamePk","away_team"]],left_on=["gamePk","team"],right_on=["gamePk","away_team"],how="inner")[["gamePk","days_since_last_game"]].rename(columns={"days_since_last_game":"away_days_since_last"})
    return d.merge(h,on="gamePk",how="left").merge(a,on="gamePk",how="left")

def merge_latest_market(m):
    f=HERE/"latest"/"MLB_ODDS_API_MARKETS.csv"
    if not f.exists(): return m
    o=pd.read_csv(f,low_memory=False)
    # keep consensus per current event/team using median point/price; preserved as current snapshot, not historical truth.
    rows=[]
    for (away,home),g in o.groupby(["away_team","home_team"]):
        rec={"away_team":away,"home_team":home}
        for market in ["h2h","spreads","totals"]:
            q=g[g.market==market]
            if q.empty: continue
            rec[f"current_{market}_books"]=q.bookmaker.nunique()
        rows.append(rec)
    cur=pd.DataFrame(rows)
    return m.merge(cur,on=["away_team","home_team"],how="left") if len(cur) else m

def build(years,force=False):
    frames=[]
    for y in years: frames.append(pd.DataFrame(flatten(fetch_year(y,force))))
    m=pd.concat(frames,ignore_index=True,sort=False)
    m=dedupe_gamepk(m)
    m=add_rest(m)
    m["total_runs"]=pd.to_numeric(m.home_score,errors="coerce")+pd.to_numeric(m.away_score,errors="coerce")
    m["home_run_margin"]=pd.to_numeric(m.home_score,errors="coerce")-pd.to_numeric(m.away_score,errors="coerce")
    m=merge_latest_market(m)
    DERIVED.mkdir(parents=True,exist_ok=True)
    m.to_parquet(DERIVED/"MLB_GAME_MASTER.parquet",index=False)
    m.to_csv(DERIVED/"MLB_GAME_MASTER.csv",index=False)
    print(f"MLB_GAME_MASTER rows: {len(m):,}")
    print("SPORTS HULK MLB GAME MASTER: DONE")
if __name__=="__main__":
    a=argparse.ArgumentParser(); a.add_argument("--years",nargs="+",type=int,default=[2024,2025,2026]); a.add_argument("--force",action="store_true"); z=a.parse_args()
    build(z.years,z.force)
