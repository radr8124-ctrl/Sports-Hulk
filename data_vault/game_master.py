from pathlib import Path
import argparse, urllib.request
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
RAW=HERE/"raw"; DERIVED=HERE/"derived"
SCHEDULE_URL="https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
FEATURES=["off_epa_per_play","def_epa_per_play","off_success_rate","def_success_rate",
          "off_explosive_rate","def_explosive_rate","pass_rate","sack_rate",
          "turnover_rate","plays_per_game"]

def ensure_schedule(force=False):
    dest=RAW/"schedules"/"games.csv"; dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists() and dest.stat().st_size>0 and not force: return dest
    tmp=dest.with_suffix(".csv.part")
    req=urllib.request.Request(SCHEDULE_URL,headers={"User-Agent":"Sports-HULK/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=90) as r, open(tmp,"wb") as f:
            while True:
                b=r.read(1024*1024)
                if not b: break
                f.write(b)
        tmp.replace(dest)
    except Exception:
        if tmp.exists(): tmp.unlink()
        raise
    return dest

def read_pbp(seasons):
    frames=[]
    for s in seasons:
        p=RAW/"pbp"/f"pbp_{s}.parquet"
        if not p.exists(): raise FileNotFoundError(f"Missing {p}")
        d=pd.read_parquet(p)
        if "season" not in d: d["season"]=s
        frames.append(d)
    return pd.concat(frames,ignore_index=True,sort=False)

def num(s): return pd.to_numeric(s,errors="coerce").fillna(0.0)

def derive_team_games(pbp):
    need={"game_id","posteam","defteam"}
    if not need<=set(pbp): raise ValueError(f"Missing columns: {need-set(pbp)}")
    x=pbp[pbp.posteam.notna() & pbp.defteam.notna()].copy()
    pt=x["play_type"].astype(str) if "play_type" in x else pd.Series("",index=x.index)
    pas=num(x["pass"]) if "pass" in x else pt.eq("pass").astype(float)
    rush=num(x["rush"]) if "rush" in x else pt.eq("run").astype(float)
    scr=((pas>0)|(rush>0))
    x=x[scr].copy(); pas=pas.loc[x.index]
    epa=pd.to_numeric(x["epa"],errors="coerce") if "epa" in x else pd.Series(np.nan,index=x.index)
    suc=pd.to_numeric(x["success"],errors="coerce") if "success" in x else (epa>0).astype(float)
    y=pd.to_numeric(x["yards_gained"],errors="coerce").fillna(0) if "yards_gained" in x else pd.Series(0,index=x.index)
    explosive=(((pas>0)&(y>=20))|((pas<=0)&(y>=10))).astype(float)
    sack=num(x["sack"]) if "sack" in x else pd.Series(0,index=x.index)
    itc=num(x["interception"]) if "interception" in x else pd.Series(0,index=x.index)
    fum=num(x["fumble_lost"]) if "fumble_lost" in x else pd.Series(0,index=x.index)
    x["_epa"]=epa; x["_success"]=suc; x["_explosive"]=explosive
    x["_pass"]=pas; x["_sack"]=sack; x["_turnover"]=((itc>0)|(fum>0)).astype(float); x["_play"]=1
    off=x.groupby(["game_id","posteam","defteam"]).agg(
      plays_per_game=("_play","sum"),off_epa_per_play=("_epa","mean"),
      off_success_rate=("_success","mean"),off_explosive_rate=("_explosive","mean"),
      pass_rate=("_pass","mean"),sack_rate=("_sack","mean"),turnover_rate=("_turnover","mean")).reset_index()
    de=off[["game_id","posteam","defteam","off_epa_per_play","off_success_rate","off_explosive_rate"]].rename(columns={
      "posteam":"opp_team","defteam":"team","off_epa_per_play":"def_epa_per_play",
      "off_success_rate":"def_success_rate","off_explosive_rate":"def_explosive_rate"})
    off=off.rename(columns={"posteam":"team","defteam":"opp_team"})
    return off.merge(de,on=["game_id","team","opp_team"],how="left")

def add_pregame(team_games,schedule):
    cols=[c for c in ["game_id","season","week","gameday","home_team","away_team"] if c in schedule]
    x=team_games.merge(schedule[cols].drop_duplicates("game_id"),on="game_id",how="left")
    if "gameday" in x: x["gameday"]=pd.to_datetime(x["gameday"],errors="coerce")
    x=x.sort_values([c for c in ["team","season","gameday","week","game_id"] if c in x])
    for f in FEATURES:
        if f not in x: continue
        g=x.groupby(["team","season"])[f]
        x["pre5_"+f]=g.transform(lambda s:s.shift(1).rolling(5,min_periods=1).mean())
        x["preseason_"+f]=g.transform(lambda s:s.shift(1).expanding(min_periods=1).mean())
    return x

def build(seasons,refresh_schedule=False):
    sched=pd.read_csv(ensure_schedule(refresh_schedule),low_memory=False)
    sched=sched[sched.season.isin(seasons)].copy()
    tg=add_pregame(derive_team_games(read_pbp(seasons)),sched)
    pre=[c for c in tg if c.startswith("pre5_") or c.startswith("preseason_")]
    home=tg[["game_id","team"]+pre].rename(columns={"team":"home_team",**{c:"home_"+c for c in pre}})
    away=tg[["game_id","team"]+pre].rename(columns={"team":"away_team",**{c:"away_"+c for c in pre}})
    m=sched.merge(home,on=["game_id","home_team"],how="left").merge(away,on=["game_id","away_team"],how="left")
    for c in ["result","total","spread_line","total_line","home_rest","away_rest","temp","wind"]:
        if c in m: m[c]=pd.to_numeric(m[c],errors="coerce")
    if {"result","spread_line"}<=set(m):
        m["home_ats_margin"]=m["result"]-m["spread_line"]
        m["home_ats_result"]=np.select([m.home_ats_margin>0,m.home_ats_margin<0],["COVER","NO_COVER"],default="PUSH")
    if {"total","total_line"}<=set(m):
        m["ou_margin"]=m["total"]-m["total_line"]
        m["ou_result"]=np.select([m.ou_margin>0,m.ou_margin<0],["OVER","UNDER"],default="PUSH")
    DERIVED.mkdir(parents=True,exist_ok=True)
    m.to_parquet(DERIVED/"NFL_GAME_MASTER.parquet",index=False)
    m.to_csv(DERIVED/"NFL_GAME_MASTER.csv",index=False)
    tg.to_parquet(DERIVED/"NFL_TEAM_GAME_FEATURES.parquet",index=False)
    compcols=[c for c in m if c.startswith("home_pre") or c.startswith("away_pre")]
    base=[c for c in ["game_id","season","week","gameday","game_type","away_team","home_team","away_score","home_score",
      "result","total","away_rest","home_rest","away_moneyline","home_moneyline","spread_line","total_line","roof","surface",
      "temp","wind","stadium","referee","home_ats_margin","home_ats_result","ou_margin","ou_result"] if c in m]
    comps=m[base+compcols].copy()
    comps.to_parquet(DERIVED/"NFL_HISTORICAL_COMPS_BASE.parquet",index=False)
    comps.to_csv(DERIVED/"NFL_HISTORICAL_COMPS_BASE.csv",index=False)
    return m,tg,comps

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--seasons",nargs="+",type=int,default=list(range(2016,2026))); p.add_argument("--refresh-schedule",action="store_true")
    a=p.parse_args(); m,t,c=build(a.seasons,a.refresh_schedule)
    print(f"NFL_GAME_MASTER rows: {len(m):,}")
    print(f"NFL_TEAM_GAME_FEATURES rows: {len(t):,}")
    print(f"NFL_HISTORICAL_COMPS_BASE rows: {len(c):,}")
    print("SPORTS HULK NFL GAME MASTER: DONE")
