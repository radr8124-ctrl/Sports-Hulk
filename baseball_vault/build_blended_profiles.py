from pathlib import Path
import argparse, re
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
RAW=HERE/"raw"/"statcast"
DERIVED=HERE/"derived"
DERIVED.mkdir(parents=True,exist_ok=True)

def year_from_name(path):
    m=re.search(r"statcast_(\d{4})-", path.name)
    return int(m.group(1)) if m else None

def load_cached(years):
    files=[f for f in sorted(RAW.glob("statcast_*.parquet")) if year_from_name(f) in years]
    if not files:
        raise SystemExit(f"No cached Statcast chunks for years {years}")
    frames=[]
    for f in files:
        d=pd.read_parquet(f)
        if len(d):
            d["_source_year"]=year_from_name(f)
            frames.append(d)
    x=pd.concat(frames,ignore_index=True,sort=False)
    dedupe=[c for c in ["game_pk","at_bat_number","pitch_number","pitcher","batter"] if c in x.columns]
    x=x.drop_duplicates(subset=dedupe,keep="last") if dedupe else x.drop_duplicates()
    return x,files

def n(df,c):
    return pd.to_numeric(df[c],errors="coerce") if c in df else pd.Series(np.nan,index=df.index)

def wmean(v,w):
    v=pd.to_numeric(v,errors="coerce"); w=pd.to_numeric(w,errors="coerce")
    m=v.notna() & w.notna() & (w>0)
    return float(np.average(v[m],weights=w[m])) if m.any() else np.nan

def prep(x,weights):
    y=x.copy()
    y["_season_weight"]=y["_source_year"].map(weights).fillna(0.0)
    for c in ["release_speed","release_spin_rate","pfx_x","pfx_z","launch_speed","launch_angle","estimated_woba_using_speedangle"]:
        if c in y: y[c]=pd.to_numeric(y[c],errors="coerce")
    desc=y["description"].fillna("").astype(str)
    y["_swing"]=desc.str.contains("swing|foul|hit_into_play",case=False,regex=True).astype(int)
    y["_whiff"]=desc.str.contains("swinging_strike|missed_bunt",case=False,regex=True).astype(int)
    y["_in_play"]=desc.str.contains("hit_into_play",case=False,regex=True).astype(int)
    y["_hard_hit"]=(n(y,"launch_speed")>=95).astype(int)
    y["_barrel"]=((n(y,"launch_speed")>=98)&n(y,"launch_angle").between(26,30,inclusive="both")).astype(int)
    return y

def pitcher_profiles(x):
    keys=["pitcher","pitch_type"] + (["player_name"] if "player_name" in x.columns else [])
    rows=[]
    for key,g in x.groupby(keys,dropna=False):
        if not isinstance(key,tuple): key=(key,)
        rec=dict(zip(keys,key)); w=g["_season_weight"]
        rec.update({
            "pitches":len(g),"weighted_pitches":float(w.sum()),
            "avg_velocity":wmean(g["release_speed"],w) if "release_speed" in g else np.nan,
            "avg_spin":wmean(g["release_spin_rate"],w) if "release_spin_rate" in g else np.nan,
            "avg_pfx_x":wmean(g["pfx_x"],w) if "pfx_x" in g else np.nan,
            "avg_pfx_z":wmean(g["pfx_z"],w) if "pfx_z" in g else np.nan,
            "xwoba_allowed":wmean(g["estimated_woba_using_speedangle"],w) if "estimated_woba_using_speedangle" in g else np.nan,
            "swings":float((g["_swing"]*w).sum()),
            "whiffs":float((g["_whiff"]*w).sum()),
            "balls_in_play":float((g["_in_play"]*w).sum()),
            "hard_hits":float((g["_hard_hit"]*w).sum()),
            "latest_year":int(g["_source_year"].max())
        })
        rows.append(rec)
    out=pd.DataFrame(rows)
    out["usage_pct"]=out["weighted_pitches"]/out.groupby("pitcher")["weighted_pitches"].transform("sum")
    out["whiff_per_swing"]=out["whiffs"]/out["swings"].replace(0,np.nan)
    out["hard_hit_per_bip"]=out["hard_hits"]/out["balls_in_play"].replace(0,np.nan)
    return out

def batter_profiles(x):
    rows=[]
    for (batter,pitch_type),g in x.groupby(["batter","pitch_type"],dropna=False):
        w=g["_season_weight"]
        rows.append({
            "batter":batter,"pitch_type":pitch_type,"pitches":len(g),"weighted_pitches":float(w.sum()),
            "avg_xwoba":wmean(g["estimated_woba_using_speedangle"],w) if "estimated_woba_using_speedangle" in g else np.nan,
            "avg_exit_velo":wmean(g["launch_speed"],w) if "launch_speed" in g else np.nan,
            "swings":float((g["_swing"]*w).sum()),
            "whiffs":float((g["_whiff"]*w).sum()),
            "balls_in_play":float((g["_in_play"]*w).sum()),
            "hard_hits":float((g["_hard_hit"]*w).sum()),
            "barrels":float((g["_barrel"]*w).sum()),
            "latest_year":int(g["_source_year"].max())
        })
    out=pd.DataFrame(rows)
    out["whiff_per_swing"]=out["whiffs"]/out["swings"].replace(0,np.nan)
    out["hard_hit_per_bip"]=out["hard_hits"]/out["balls_in_play"].replace(0,np.nan)
    out["barrel_per_bip"]=out["barrels"]/out["balls_in_play"].replace(0,np.nan)
    return out

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--years",nargs="+",type=int,default=[2025,2026])
    a.add_argument("--current-weight",type=float,default=1.0)
    a.add_argument("--prior-weight",type=float,default=0.55)
    z=a.parse_args()
    years=sorted(set(z.years)); newest=max(years)
    weights={y:(z.current_weight if y==newest else z.prior_weight) for y in years}
    x,files=load_cached(years); x=prep(x,weights)
    pp=pitcher_profiles(x); bp=batter_profiles(x)
    pp.to_parquet(DERIVED/"MLB_PITCHER_ARSENAL.parquet",index=False)
    pp.to_csv(DERIVED/"MLB_PITCHER_ARSENAL.csv",index=False)
    bp.to_parquet(DERIVED/"MLB_BATTER_VS_PITCH_TYPE.parquet",index=False)
    bp.to_csv(DERIVED/"MLB_BATTER_VS_PITCH_TYPE.csv",index=False)
    pd.DataFrame([{
        "years":",".join(map(str,years)),
        "weights":",".join(f"{y}:{weights[y]}" for y in years),
        "raw_rows":len(x),"cached_files":len(files),
        "pitcher_rows":len(pp),"batter_rows":len(bp)
    }]).to_csv(DERIVED/"MLB_BLENDED_PROFILE_BUILD.csv",index=False)
    print(f"Cached Statcast files used: {len(files):,}")
    print(f"Blended Statcast rows: {len(x):,}")
    print(f"Pitcher arsenal rows: {len(pp):,}")
    print(f"Batter/pitch-type rows: {len(bp):,}")
    print("Weights:", weights)
    print("SPORTS HULK MLB BLENDED PROFILES: DONE")

if __name__=="__main__":
    main()
