from pathlib import Path
import pandas as pd
import numpy as np
import re, json
from team_normalization import normalize_team

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"
LATEST=HERE/"latest"
RAW=HERE/"raw"

def pick_col(d, aliases):
    low={c.lower():c for c in d.columns}
    for a in aliases:
        if a in low: return low[a]
    return None

def standardize_market_file(p):
    try:
        d=pd.read_csv(p,low_memory=False)
    except Exception:
        return pd.DataFrame()

    c_home=pick_col(d,["home_team","home","hometeam"])
    c_away=pick_col(d,["away_team","away","awayteam"])
    c_time=pick_col(d,["commence_time","game_date","game_datetime","timestamp","event_time","start_time","date"])
    c_book=pick_col(d,["book","bookmaker","sportsbook","provider"])
    c_market=pick_col(d,["market","market_type","bet_type","type"])
    c_side=pick_col(d,["side","outcome","selection","name","label"])
    c_price=pick_col(d,["price","odds","american_odds","decimal_odds"])
    c_point=pick_col(d,["point","line","spread","total"])
    c_event=pick_col(d,["event_id","eventid","id","gamepk"])

    if not c_home or not c_away:
        return pd.DataFrame()

    out=pd.DataFrame({
        "source_file":p.name,
        "source_event_id":d[c_event] if c_event else np.nan,
        "away_raw":d[c_away],
        "home_raw":d[c_home],
        "away_norm":d[c_away].map(normalize_team),
        "home_norm":d[c_home].map(normalize_team),
        "market_time":pd.to_datetime(d[c_time],errors="coerce",utc=True) if c_time else pd.NaT,
        "book":d[c_book] if c_book else np.nan,
        "market":d[c_market] if c_market else np.nan,
        "side":d[c_side] if c_side else np.nan,
        "price":pd.to_numeric(d[c_price],errors="coerce") if c_price else np.nan,
        "point":pd.to_numeric(d[c_point],errors="coerce") if c_point else np.nan,
    })
    return out

def market_files():
    files=[]
    for p in [LATEST/"MLB_ODDS_API_MARKETS.csv",LATEST/"MLB_SGO_MARKETS.csv"]:
        if p.exists(): files.append(p)
    if RAW.exists():
        for p in RAW.rglob("*.csv"):
            n=p.name.lower()
            if any(k in n for k in ["odds","market","sgo"]) and "history" not in n:
                files.append(p)
    # de-dup paths
    return list(dict.fromkeys(files))

def run():
    gm=pd.read_csv(DERIVED/"MLB_GAME_MASTER.csv",low_memory=False)
    gm["gamePk"]=gm["gamePk"].astype(str)
    gm["away_norm"]=gm["away_team"].map(normalize_team)
    gm["home_norm"]=gm["home_team"].map(normalize_team)
    gm["game_dt"]=pd.to_datetime(gm["gameDate"],errors="coerce",utc=True)
    gm["game_date"]=gm["game_dt"].dt.date

    frames=[standardize_market_file(p) for p in market_files()]
    frames=[x for x in frames if not x.empty]
    if not frames:
        raise SystemExit("No usable market files with team names found")
    m=pd.concat(frames,ignore_index=True,sort=False)
    # Re-coerce after concatenation because files with no timestamp column can
    # force market_time to object dtype, which breaks the .dt accessor.
    m["market_time"]=pd.to_datetime(m["market_time"],errors="coerce",utc=True)
    # Re-coerce after concatenation because files with no timestamp column can
    # force market_time to object dtype, which breaks the .dt accessor.
    m["market_time"]=pd.to_datetime(m["market_time"],errors="coerce",utc=True)
    m["market_date"]=m["market_time"].dt.date

    exact_index={}
    for _,g in gm.iterrows():
        exact_index.setdefault((g.away_norm,g.home_norm,g.game_date),[]).append(g)

    results=[]
    ambiguous=0
    unmatched=0
    matched=0

    for _,r in m.iterrows():
        candidates=[]
        key=(r.away_norm,r.home_norm,r.market_date)
        if pd.notna(r.market_date):
            candidates=exact_index.get(key,[])

        # fallback +/- 1 day because sportsbook timestamps can cross UTC/local date
        if not candidates and pd.notna(r.market_date):
            for delta in [-1,1]:
                dt=pd.Timestamp(r.market_date)+pd.Timedelta(days=delta)
                candidates += exact_index.get((r.away_norm,r.home_norm,dt.date()),[])

        # final fallback: same teams with nearest time within 36h
        if not candidates and pd.notna(r.market_time):
            same=gm[(gm.away_norm==r.away_norm)&(gm.home_norm==r.home_norm)].copy()
            if not same.empty:
                same["tdiff"]=(same.game_dt-r.market_time).abs()
                same=same[same.tdiff<=pd.Timedelta(hours=36)]
                if not same.empty:
                    mind=same.tdiff.min()
                    candidates=[x for _,x in same[same.tdiff==mind].iterrows()]

        rec=r.to_dict()
        if len(candidates)==1:
            g=candidates[0]
            rec.update({
                "match_status":"MATCHED",
                "gamePk":str(g.gamePk),
                "mlb_game_dt":g.game_dt,
                "mlb_away_team":g.away_team,
                "mlb_home_team":g.home_team,
            })
            matched+=1
        elif len(candidates)>1:
            rec.update({"match_status":"AMBIGUOUS","gamePk":np.nan})
            ambiguous+=1
        else:
            rec.update({"match_status":"UNMATCHED","gamePk":np.nan})
            unmatched+=1
        results.append(rec)

    out=pd.DataFrame(results)
    out.to_csv(DERIVED/"MLB_MARKET_RECONCILED_ROWS.csv",index=False)
    out.to_parquet(DERIVED/"MLB_MARKET_RECONCILED_ROWS.parquet",index=False)

    total=len(out)
    summary=pd.DataFrame([{
        "total_market_rows":total,
        "matched_rows":matched,
        "ambiguous_rows":ambiguous,
        "unmatched_rows":unmatched,
        "match_rate":matched/total if total else np.nan,
        "matched_unique_games":out.loc[out.match_status=="MATCHED","gamePk"].nunique(),
        "source_files":out["source_file"].nunique(),
    }])
    summary.to_csv(DERIVED/"MLB_MARKET_RECON_VALIDATION.csv",index=False)

    print(summary.to_string(index=False))
    print("SPORTS HULK MLB MARKET RECONCILIATION: DONE")

if __name__=="__main__":
    run()
