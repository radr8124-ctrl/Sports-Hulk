from pathlib import Path
import argparse, numpy as np, pandas as pd
P=Path(__file__).resolve().parent/"derived"/"NFL_HISTORICAL_COMPS_BASE.parquet"
def main():
    a=argparse.ArgumentParser(); a.add_argument("--game-id",required=True); a.add_argument("--n",type=int,default=50); z=a.parse_args()
    d=pd.read_parquet(P); t=d[d.game_id.astype(str)==str(z.game_id)]
    if t.empty: raise SystemExit("game_id not found")
    t=t.iloc[0]; h=d[d.game_id.astype(str)!=str(z.game_id)].copy()
    if "gameday" in d and pd.notna(t.get("gameday")):
        h=h[pd.to_datetime(h.gameday,errors="coerce")<pd.to_datetime(t.gameday)]
    feats=[c for c in d if c.startswith("home_pre5_") or c.startswith("away_pre5_")]
    feats += [c for c in ["spread_line","total_line","home_rest","away_rest","temp","wind"] if c in d]
    parts=[]; used=0
    for c in feats:
        v=pd.to_numeric(h[c],errors="coerce"); tv=pd.to_numeric(pd.Series([t[c]]),errors="coerce").iloc[0]; sd=v.std()
        if pd.isna(tv) or pd.isna(sd) or sd==0: continue
        parts.append(((v-tv)/sd)**2); used+=1
    h["HULK_similarity_distance"]=np.sqrt(sum(parts)/used)
    cols=[c for c in ["game_id","gameday","away_team","home_team","spread_line","total_line","home_ats_result","ou_result","HULK_similarity_distance"] if c in h]
    print(h.sort_values("HULK_similarity_distance")[cols].head(z.n).to_string(index=False))
if __name__=="__main__": main()
