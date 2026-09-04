from pathlib import Path
from datetime import datetime, timedelta
import argparse, io, time, urllib.parse, urllib.request, urllib.error, random
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
RAW=HERE/"raw"/"statcast"
DERIVED=HERE/"derived"
SAVANT="https://baseballsavant.mlb.com/statcast_search/csv"

def request_chunk(start_date,end_date,timeout=180,retries=5):
    params={
      "all":"true","type":"details","player_type":"pitcher",
      "game_date_gt":start_date,"game_date_lt":end_date,
      "hfGT":"R|PO|S|","min_pitches":"0","min_results":"0",
      "group_by":"name","sort_col":"pitches","sort_order":"desc","min_abs":"0"
    }
    url=SAVANT+"?"+urllib.parse.urlencode(params)
    last=None
    for attempt in range(1,retries+1):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Sports-HULK-Baseball/1.1"})
            with urllib.request.urlopen(req,timeout=timeout) as r:
                raw=r.read().decode("utf-8",errors="replace")
            return pd.read_csv(io.StringIO(raw),low_memory=False)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionResetError) as e:
            last=e
            if attempt>=retries:
                break
            wait=min(30, 2**attempt + random.random()*2)
            print(f"{start_date}..{end_date}: temporary error {type(e).__name__}; retry {attempt}/{retries-1} in {wait:.1f}s")
            time.sleep(wait)
    raise last

def daterange_chunks(start,end,days=3):
    s=datetime.strptime(start,"%Y-%m-%d").date()
    e=datetime.strptime(end,"%Y-%m-%d").date()
    cur=s
    while cur<=e:
        stop=min(e,cur+timedelta(days=days-1))
        yield cur.isoformat(),stop.isoformat()
        cur=stop+timedelta(days=1)

def backfill(start,end,chunk_days=3,pause=0.7,force=False,retries=5,continue_on_error=True):
    RAW.mkdir(parents=True,exist_ok=True); DERIVED.mkdir(parents=True,exist_ok=True)
    frames=[]; failures=[]
    for a,b in daterange_chunks(start,end,chunk_days):
        out=RAW/f"statcast_{a}_{b}.parquet"
        if out.exists() and out.stat().st_size>0 and not force:
            d=pd.read_parquet(out)
            print(f"{a}..{b}: cached {len(d):,}")
        else:
            try:
                d=request_chunk(a,b,retries=retries)
                d.to_parquet(out,index=False)
                print(f"{a}..{b}: downloaded {len(d):,}")
                time.sleep(pause)
            except Exception as e:
                failures.append((a,b,repr(e)))
                print(f"{a}..{b}: FAILED after retries: {repr(e)}")
                if not continue_on_error:
                    raise
                continue
        if not d.empty: frames.append(d)
    if not frames:
        raise SystemExit("No Statcast rows available for requested range.")
    all_df=pd.concat(frames,ignore_index=True,sort=False).drop_duplicates()
    all_df.to_parquet(DERIVED/f"MLB_STATCAST_{start}_{end}.parquet",index=False)
    if failures:
        pd.DataFrame(failures,columns=["start","end","error"]).to_csv(DERIVED/"MLB_STATCAST_FAILED_CHUNKS.csv",index=False)
    return all_df, failures

def bnum(df,c):
    return pd.to_numeric(df[c],errors="coerce") if c in df else pd.Series(np.nan,index=df.index)

def derive_profiles(d):
    DERIVED.mkdir(parents=True,exist_ok=True)
    x=d.copy()
    for c in ["release_speed","release_spin_rate","pfx_x","pfx_z","launch_speed",
              "estimated_woba_using_speedangle","zone","launch_angle"]:
        if c in x: x[c]=pd.to_numeric(x[c],errors="coerce")
    desc=x["description"].fillna("").astype(str) if "description" in x else pd.Series("",index=x.index)
    events=x["events"].fillna("").astype(str) if "events" in x else pd.Series("",index=x.index)
    x["_swing"]=desc.str.contains("swing|foul|hit_into_play",case=False,regex=True).astype(int)
    x["_whiff"]=desc.str.contains("swinging_strike|missed_bunt",case=False,regex=True).astype(int)
    x["_in_play"]=desc.str.contains("hit_into_play",case=False,regex=True).astype(int)
    x["_hard_hit"]=(bnum(x,"launch_speed")>=95).astype(int)
    x["_barrel"]=((bnum(x,"launch_speed")>=98)&(bnum(x,"launch_angle").between(26,30,inclusive="both"))).astype(int)
    x["_strikeout"]=events.eq("strikeout").astype(int)
    x["_walk"]=events.isin(["walk","intent_walk"]).astype(int)

    if {"pitcher","pitch_type"}<=set(x):
        keys=["pitcher","pitch_type"]
        if "player_name" in x: keys.insert(1,"player_name")
        g=x.groupby(keys,dropna=False)
        pa=g.agg(
          pitches=("pitch_type","size"), avg_velocity=("release_speed","mean"),
          avg_spin=("release_spin_rate","mean"), avg_pfx_x=("pfx_x","mean"),
          avg_pfx_z=("pfx_z","mean"), swings=("_swing","sum"), whiffs=("_whiff","sum"),
          balls_in_play=("_in_play","sum"), hard_hits=("_hard_hit","sum"),
          xwoba_allowed=("estimated_woba_using_speedangle","mean"),
          strikeouts=("_strikeout","sum"), walks=("_walk","sum")
        ).reset_index()
        pa["usage_pct"]=pa["pitches"]/pa.groupby("pitcher")["pitches"].transform("sum")
        pa["whiff_per_swing"]=pa["whiffs"]/pa["swings"].replace(0,np.nan)
        pa["hard_hit_per_bip"]=pa["hard_hits"]/pa["balls_in_play"].replace(0,np.nan)
        pa.to_parquet(DERIVED/"MLB_PITCHER_ARSENAL.parquet",index=False)
        pa.to_csv(DERIVED/"MLB_PITCHER_ARSENAL.csv",index=False)
    else: pa=pd.DataFrame()

    if {"batter","pitch_type"}<=set(x):
        g=x.groupby(["batter","pitch_type"],dropna=False)
        bp=g.agg(
          pitches=("pitch_type","size"), swings=("_swing","sum"), whiffs=("_whiff","sum"),
          balls_in_play=("_in_play","sum"), hard_hits=("_hard_hit","sum"), barrels=("_barrel","sum"),
          avg_exit_velo=("launch_speed","mean"),
          avg_xwoba=("estimated_woba_using_speedangle","mean"),
          strikeouts=("_strikeout","sum"), walks=("_walk","sum")
        ).reset_index()
        bp["whiff_per_swing"]=bp["whiffs"]/bp["swings"].replace(0,np.nan)
        bp["hard_hit_per_bip"]=bp["hard_hits"]/bp["balls_in_play"].replace(0,np.nan)
        bp["barrel_per_bip"]=bp["barrels"]/bp["balls_in_play"].replace(0,np.nan)
        bp.to_parquet(DERIVED/"MLB_BATTER_VS_PITCH_TYPE.parquet",index=False)
        bp.to_csv(DERIVED/"MLB_BATTER_VS_PITCH_TYPE.csv",index=False)
    else: bp=pd.DataFrame()
    return pa,bp

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--start",required=True); a.add_argument("--end",required=True)
    a.add_argument("--chunk-days",type=int,default=3); a.add_argument("--retries",type=int,default=5)
    a.add_argument("--force",action="store_true"); a.add_argument("--stop-on-error",action="store_true")
    z=a.parse_args()
    d,failures=backfill(z.start,z.end,z.chunk_days,force=z.force,retries=z.retries,
                        continue_on_error=not z.stop_on_error)
    pa,bp=derive_profiles(d)
    print(f"Statcast rows: {len(d):,}")
    print(f"Pitcher arsenal rows: {len(pa):,}")
    print(f"Batter/pitch-type rows: {len(bp):,}")
    print(f"Failed chunks remaining: {len(failures)}")
    print("SPORTS HULK BASEBALL STATCAST: DONE")
if __name__=="__main__": main()
