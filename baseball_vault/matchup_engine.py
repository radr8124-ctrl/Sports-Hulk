from pathlib import Path
import re
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
LATEST=HERE/"latest"
DERIVED=HERE/"derived"
DERIVED.mkdir(parents=True,exist_ok=True)

def read_any(pathstem):
    for ext in [".parquet",".csv"]:
        p=Path(str(pathstem)+ext)
        if p.exists():
            return pd.read_parquet(p) if ext==".parquet" else pd.read_csv(p,low_memory=False)
    return pd.DataFrame()

def norm(s):
    return re.sub(r"[^a-z0-9]+","",str(s).lower())

def first_col(df,candidates):
    m={norm(c):c for c in df.columns}
    for x in candidates:
        if norm(x) in m: return m[norm(x)]
    return None

def safe_num(s):
    return pd.to_numeric(s,errors="coerce")

def lineup_batter_ids(lineups):
    c=first_col(lineups,["batter_id","player_id","person_id","id","mlbam_id"])
    team=first_col(lineups,["team","team_name","club"])
    if c is None or team is None:return {}
    out={}
    for t,g in lineups.groupby(team):
        ids=safe_num(g[c]).dropna().astype(int).tolist()
        if ids:out[str(t)]=ids
    return out

def probable_pitchers(schedule):
    return (
      first_col(schedule,["home_probable_pitcher_id","home_probable_id","home_pitcher_id"]),
      first_col(schedule,["away_probable_pitcher_id","away_probable_id","away_pitcher_id"]),
      first_col(schedule,["home_probable_pitcher","home_probable_pitcher_name","home_starter"]),
      first_col(schedule,["away_probable_pitcher","away_probable_pitcher_name","away_starter"])
    )

def arsenal_vs_hitters(arsenal,batter,hitter_ids,pitcher_id):
    if pitcher_id is None or pd.isna(pitcher_id) or not hitter_ids:
        return {"arsenal_matchup_score":np.nan,"arsenal_sample_pitches":0,"pitch_types_matched":0}
    a=arsenal[safe_num(arsenal["pitcher"])==int(float(pitcher_id))].copy() if "pitcher" in arsenal else pd.DataFrame()
    b=batter[safe_num(batter["batter"]).isin(hitter_ids)].copy() if "batter" in batter else pd.DataFrame()
    if a.empty or b.empty:return {"arsenal_matchup_score":np.nan,"arsenal_sample_pitches":0,"pitch_types_matched":0}
    keep=["pitch_type","usage_pct","whiff_per_swing","hard_hit_per_bip","xwoba_allowed","pitches"]
    a=a[[c for c in keep if c in a.columns]]
    metrics=["avg_xwoba","whiff_per_swing","hard_hit_per_bip","barrel_per_bip","pitches"]
    bg=b.groupby("pitch_type").agg({c:"mean" if c!="pitches" else "sum" for c in metrics if c in b.columns}).reset_index()
    m=a.merge(bg,on="pitch_type",how="inner",suffixes=("_pitcher","_batters"))
    if m.empty:return {"arsenal_matchup_score":np.nan,"arsenal_sample_pitches":0,"pitch_types_matched":0}
    w=safe_num(m.get("usage_pct",pd.Series(1/len(m),index=m.index))).fillna(0)
    w=w/w.sum() if w.sum()>0 else pd.Series(1/len(m),index=m.index)
    comps=[]
    if "avg_xwoba" in m: comps.append((-safe_num(m["avg_xwoba"]).fillna(.320)+.320)/.08)
    if "whiff_per_swing_batters" in m: comps.append((safe_num(m["whiff_per_swing_batters"]).fillna(.25)-.25)/.10)
    elif "whiff_per_swing" in m: comps.append((safe_num(m["whiff_per_swing"]).fillna(.25)-.25)/.10)
    if "hard_hit_per_bip_batters" in m: comps.append((.40-safe_num(m["hard_hit_per_bip_batters"]).fillna(.40))/.15)
    elif "hard_hit_per_bip" in m: comps.append((.40-safe_num(m["hard_hit_per_bip"]).fillna(.40))/.15)
    if "barrel_per_bip" in m: comps.append((.10-safe_num(m["barrel_per_bip"]).fillna(.10))/.08)
    if not comps:return {"arsenal_matchup_score":np.nan,"arsenal_sample_pitches":0,"pitch_types_matched":len(m)}
    score=sum(comps)/len(comps)
    weighted=float(np.nansum(score*w))
    sample=int(safe_num(m.get("pitches_pitcher",m.get("pitches",0))).fillna(0).sum())
    return {"arsenal_matchup_score":round(weighted,3),"arsenal_sample_pitches":sample,"pitch_types_matched":len(m)}

def bullpen_map(df):
    if df.empty:return {}
    team=first_col(df,["team","team_name","club"])
    score=first_col(df,[
        "HULK_bullpen_workload_score",
        "workload_score",
        "bullpen_workload_score",
        "fatigue_score"
    ])
    if team is None or score is None:return {}
    out={}
    for t,g in df.groupby(team):
        v=safe_num(g[score]).dropna()
        if len(v): out[str(t)]=float(v.mean())
    return out

def market_summary():
    f=LATEST/"MLB_ODDS_API_MARKETS.csv"
    if not f.exists():return pd.DataFrame()
    o=pd.read_csv(f,low_memory=False)
    if not {"away_team","home_team","market"}<=set(o):return pd.DataFrame()
    point=first_col(o,["point","line","spread"])
    price=first_col(o,["price","odds","american_odds"])
    rows=[]
    for (away,home),g in o.groupby(["away_team","home_team"]):
        r={"away_team":away,"home_team":home}
        for market in ["h2h","spreads","totals"]:
            q=g[g.market==market]
            r[f"{market}_book_count"]=q["bookmaker"].nunique() if "bookmaker" in q else len(q)
            if point and not q.empty:r[f"{market}_median_point"]=safe_num(q[point]).median()
            if price and not q.empty:r[f"{market}_median_price"]=safe_num(q[price]).median()
        rows.append(r)
    return pd.DataFrame(rows)

def confidence(sample,matched,has_market,has_bullpen,has_both_starters=True):
    pts=0
    if sample>=500:pts+=2
    elif sample>=150:pts+=1
    if matched>=3:pts+=1
    if has_market:pts+=1
    if has_bullpen:pts+=1
    label="HIGH" if pts>=4 else ("MEDIUM" if pts>=2 else "LOW")
    if not has_bullpen and label=="HIGH":
        label="MEDIUM"
    if not has_both_starters:
        label="LOW"
    return label

def classify(score,conf):
    if pd.isna(score):return "PASS"
    threshold=.55 if conf=="HIGH" else (.75 if conf=="MEDIUM" else 1.0)
    if abs(score)>=threshold:return "BET CANDIDATE"
    if abs(score)>=threshold*.6:return "WATCH"
    return "PASS"

def build():
    schedule=pd.read_csv(LATEST/"MLB_SCHEDULE.csv",low_memory=False)
    lineups=pd.read_csv(LATEST/"MLB_LINEUPS_RECENT.csv",low_memory=False) if (LATEST/"MLB_LINEUPS_RECENT.csv").exists() else pd.DataFrame()
    bullpen=pd.read_csv(LATEST/"MLB_BULLPEN_WORKLOAD.csv",low_memory=False) if (LATEST/"MLB_BULLPEN_WORKLOAD.csv").exists() else pd.DataFrame()
    arsenal=read_any(DERIVED/"MLB_PITCHER_ARSENAL")
    batter=read_any(DERIVED/"MLB_BATTER_VS_PITCH_TYPE")
    if arsenal.empty or batter.empty: raise SystemExit("Missing Statcast-derived profiles.")
    hitters=lineup_batter_ids(lineups); bpmap=bullpen_map(bullpen)
    hpid,apid,hpn,apn=probable_pitchers(schedule)
    rows=[]
    for _,g in schedule.iterrows():
        home=str(g.get("home_team","")); away=str(g.get("away_team",""))
        hp=g.get(hpid) if hpid else None; ap=g.get(apid) if apid else None
        hs=arsenal_vs_hitters(arsenal,batter,hitters.get(away,[]),hp)
        as_=arsenal_vs_hitters(arsenal,batter,hitters.get(home,[]),ap)
        home_bp=bpmap.get(home,np.nan); away_bp=bpmap.get(away,np.nan)
        starter_edge=(hs["arsenal_matchup_score"] if not pd.isna(hs["arsenal_matchup_score"]) else 0) - (as_["arsenal_matchup_score"] if not pd.isna(as_["arsenal_matchup_score"]) else 0)
        bullpen_edge=0.0
        has_bp=not(pd.isna(home_bp) or pd.isna(away_bp))
        if has_bp: bullpen_edge=(away_bp-home_bp)/max(abs(home_bp)+abs(away_bp),1)
        composite=.8*starter_edge+.2*bullpen_edge
        sample=hs["arsenal_sample_pitches"]+as_["arsenal_sample_pitches"]
        matched=hs["pitch_types_matched"]+as_["pitch_types_matched"]
        has_both_starters=not(pd.isna(as_["arsenal_matchup_score"]) or pd.isna(hs["arsenal_matchup_score"]))
        rows.append({
          "gamePk":g.get("gamePk"),"gameDate":g.get("gameDate"),
          "away_team":away,"home_team":home,
          "away_probable_pitcher":g.get(apn) if apn else None,
          "home_probable_pitcher":g.get(hpn) if hpn else None,
          "away_starter_vs_home_lineup":as_["arsenal_matchup_score"],
          "home_starter_vs_away_lineup":hs["arsenal_matchup_score"],
          "home_bullpen_workload":home_bp,"away_bullpen_workload":away_bp,
          "bullpen_data_present":has_bp,
          "both_starter_matchups_present":has_both_starters,
          "home_edge_score":round(float(composite),3),
          "sample_pitches":sample,"pitch_types_matched":matched
        })
    out=pd.DataFrame(rows)
    mk=market_summary()
    if not mk.empty: out=out.merge(mk,on=["away_team","home_team"],how="left")
    has_market=out.filter(regex="_book_count$").fillna(0).sum(axis=1)>0 if any(c.endswith("_book_count") for c in out.columns) else pd.Series(False,index=out.index)
    out["confidence"]=[confidence(int(s),int(m),bool(hm),bool(bp),bool(st))
                       for s,m,hm,bp,st in zip(out.sample_pitches,out.pitch_types_matched,has_market,out.bullpen_data_present,out.both_starter_matchups_present)]
    out["lean"]=np.where(out.home_edge_score>0,out.home_team,np.where(out.home_edge_score<0,out.away_team,"NONE"))
    out["decision"]=[classify(s,c) if bool(st) else "PASS"
                     for s,c,st in zip(out.home_edge_score,out.confidence,out.both_starter_matchups_present)]
    out.to_parquet(DERIVED/"MLB_MATCHUP_BOARD.parquet",index=False)
    out.to_csv(DERIVED/"MLB_MATCHUP_BOARD.csv",index=False)
    print(f"MLB matchup games: {len(out):,}")
    print(f"Games with bullpen data: {int(out.bullpen_data_present.sum())}/{len(out)}")
    print("Decision counts:",out.decision.value_counts(dropna=False).to_dict())
    print("SPORTS HULK MLB MATCHUP ENGINE: DONE")
    return out

if __name__=="__main__": build()
