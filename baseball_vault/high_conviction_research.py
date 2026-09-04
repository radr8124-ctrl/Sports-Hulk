from pathlib import Path
import pandas as pd
import numpy as np
import re

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"

def norm_team(x):
    return re.sub(r"[^a-z0-9]+","",str(x).lower())

def numeric(s):
    return pd.to_numeric(s,errors="coerce")

def norm_market(x):
    s=str(x or "").lower().strip()
    s=re.sub(r"[^a-z0-9]+"," ",s)
    s=re.sub(r"\s+"," ",s).strip()
    if any(k in s for k in ["moneyline","money line","h2h","ml"]): return "MONEYLINE"
    if any(k in s for k in ["spread","run line","runline"]): return "RUN_LINE"
    if any(k in s for k in ["total","over under","overunder"]): return "TOTAL"
    return s.upper() if s else "UNKNOWN"

def norm_side(x):
    s=str(x or "").lower().strip()
    if "home" in s: return "HOME"
    if "away" in s: return "AWAY"
    if "over" in s: return "OVER"
    if "under" in s: return "UNDER"
    return re.sub(r"[^a-z0-9]+","_",s).strip("_").upper() if s else "UNKNOWN"

def run():
    brain=pd.read_csv(DERIVED/"MLB_DECISION_BRAIN_RESEARCH.csv",low_memory=False)
    mh=pd.read_csv(DERIVED/"MLB_MARKET_HISTORY_SUMMARY.csv",low_memory=False)

    # -----------------------------------------------------
    # CURRENT MARKET-HISTORY SCHEMA COMPATIBILITY
    # -----------------------------------------------------
    # Older research code called the provider event id
    # "provider_event_id".  The normalized market-history
    # builder now stores that same provider-event identity
    # in gamePk.  Keep a local compatibility alias so this
    # legacy research layer can continue to map provider
    # events to the real MLB numeric gamePk by teams/time.
    if "provider_event_id" not in mh.columns:
        if "gamePk" in mh.columns:
            mh["provider_event_id"] = mh["gamePk"].astype(str)
        else:
            raise SystemExit(
                "Market history has no provider_event_id or gamePk"
            )

    brain["_away_norm"]=brain["away_team"].map(norm_team)
    brain["_home_norm"]=brain["home_team"].map(norm_team)
    mh["_away_norm"]=mh["away_team"].map(norm_team)
    mh["_home_norm"]=mh["home_team"].map(norm_team)

    brain["_game_time"]=pd.to_datetime(brain["gameDate"],errors="coerce",utc=True)
    event_time_col = (
        "event_start_time"
        if "event_start_time" in mh.columns
        else "game_start"
        if "game_start" in mh.columns
        else None
    )

    if event_time_col is None:
        raise SystemExit(
            "Market history has no event_start_time or game_start column"
        )

    mh["_event_time"] = pd.to_datetime(
        mh[event_time_col],
        errors="coerce",
        utc=True,
        format="mixed",
    )

    mh["_market_type"]=mh["market"].map(norm_market) if "market" in mh.columns else "UNKNOWN"
    mh["_market_side"]=mh["side"].map(norm_side) if "side" in mh.columns else "UNKNOWN"

    # Assign each provider event to the nearest MLB game with the same teams.
    # Maximum tolerance is 12 hours; ties or multiple equally-near candidates stay ambiguous.
    event_map=[]
    event_keys=mh[["provider_event_id","_away_norm","_home_norm","_event_time"]].drop_duplicates()

    for _,e in event_keys.iterrows():
        cand=brain[
            (brain["_away_norm"]==e["_away_norm"]) &
            (brain["_home_norm"]==e["_home_norm"])
        ].copy()
        status="UNKNOWN"
        gamepk=np.nan
        delta_hours=np.nan

        if len(cand) and pd.notna(e["_event_time"]):
            cand["_delta"]=(cand["_game_time"]-e["_event_time"]).abs()
            cand=cand[cand["_delta"]<=pd.Timedelta(hours=12)]
            if len(cand):
                md=cand["_delta"].min()
                best=cand[cand["_delta"]==md]
                if len(best)==1:
                    status="KNOWN"
                    gamepk=best.iloc[0]["gamePk"]
                    delta_hours=md.total_seconds()/3600.0
                else:
                    status="AMBIGUOUS"
            else:
                status="UNKNOWN"

        event_map.append({
            "provider_event_id":e["provider_event_id"],
            "_away_norm":e["_away_norm"],
            "_home_norm":e["_home_norm"],
            "market_match_status":status,
            "matched_gamePk":gamepk,
            "market_game_time_delta_hours":delta_hours,
        })

    em=pd.DataFrame(event_map)
    mh=mh.merge(em,on=["provider_event_id","_away_norm","_home_norm"],how="left")

    # Market disagreement only within comparable quotes for the SAME matched game.
    known=mh[mh["market_match_status"]=="KNOWN"].copy()
    known["matched_gamePk"]=pd.to_numeric(known["matched_gamePk"],errors="coerce").astype("Int64")

    comp_rows=[]
    for keys,g in known.groupby(["matched_gamePk","_market_type","_market_side"],dropna=False):
        gamepk,mtype,mside=keys
        pstd=numeric(g["current_point"]).std() if "current_point" in g else np.nan
        prstd=numeric(g["current_price"]).std() if "current_price" in g else np.nan
        if mtype=="MONEYLINE":
            disagree=bool(pd.notna(prstd) and prstd>40)
        else:
            disagree=bool((pd.notna(pstd) and pstd>1.0) or (pd.notna(prstd) and prstd>40))
        comp_rows.append({
            "gamePk":int(gamepk) if pd.notna(gamepk) else np.nan,
            "market_type":mtype,
            "market_side":mside,
            "group_rows":len(g),
            "group_books":g["book"].nunique(dropna=True) if "book" in g else 0,
            "group_avg_abs_point_move":numeric(g["point_move"]).abs().mean() if "point_move" in g else np.nan,
            "group_avg_abs_price_move":numeric(g["price_move"]).abs().mean() if "price_move" in g else np.nan,
            "group_current_point_std":pstd,
            "group_current_price_std":prstd,
            "group_disagreement":disagree,
        })
    comp=pd.DataFrame(comp_rows)

    game_rows=[]
    if len(comp):
        for gamepk,g in comp.groupby("gamePk",dropna=False):
            game_rows.append({
                "gamePk":gamepk,
                "comparable_market_groups":len(g),
                "market_groups_with_2plus_books":int((numeric(g["group_books"])>=2).sum()),
                "current_point_std":numeric(g["group_current_point_std"]).max(),
                "current_price_std":numeric(g["group_current_price_std"]).max(),
                "avg_abs_point_move":numeric(g["group_avg_abs_point_move"]).mean(),
                "avg_abs_price_move":numeric(g["group_avg_abs_price_move"]).mean(),
                "comparable_market_disagreement":bool(g["group_disagreement"].fillna(False).any()),
            })
    agg=pd.DataFrame(game_rows)

    if len(known):
        cover=known.groupby("matched_gamePk").agg(
            market_rows=("provider_event_id","size"),
            books=("book","nunique"),
            matched_provider_events=("provider_event_id","nunique"),
            max_time_delta_hours=("market_game_time_delta_hours","max"),
        ).reset_index().rename(columns={"matched_gamePk":"gamePk"})
        cover["gamePk"]=pd.to_numeric(cover["gamePk"],errors="coerce").astype("Int64")
    else:
        cover=pd.DataFrame(columns=["gamePk","market_rows","books","matched_provider_events","max_time_delta_hours"])

    brain["gamePk"]=pd.to_numeric(brain["gamePk"],errors="coerce").astype("Int64")
    d=brain.merge(cover,on="gamePk",how="left")
    if len(agg):
        agg["gamePk"]=pd.to_numeric(agg["gamePk"],errors="coerce").astype("Int64")
        d=d.merge(agg,on="gamePk",how="left")

    # Per-brain-game status comes from actual event-time mapping.
    status_by_game={}
    for _,r in em.iterrows():
        if r["market_match_status"]=="KNOWN" and pd.notna(r["matched_gamePk"]):
            status_by_game[int(float(r["matched_gamePk"]))]="KNOWN"

    # Games without a known mapping: if same teams have provider events but those
    # events could not be uniquely assigned, mark AMBIGUOUS; otherwise UNKNOWN.
    event_team_pairs=set(zip(mh["_away_norm"],mh["_home_norm"]))
    d["market_data_status"]="UNKNOWN"
    for idx,r in d.iterrows():
        gp=int(r["gamePk"]) if pd.notna(r["gamePk"]) else None
        if gp in status_by_game:
            d.at[idx,"market_data_status"]="KNOWN"
        elif (r["_away_norm"],r["_home_norm"]) in event_team_pairs:
            d.at[idx,"market_data_status"]="AMBIGUOUS"

    is_known=d["market_data_status"]=="KNOWN"
    d["market_disagreement_flag"]=np.where(
        is_known,
        d.get("comparable_market_disagreement",pd.Series(False,index=d.index)).fillna(False),
        pd.NA
    )

    d["market_move_strength_0_1"]=(
        numeric(d.get("avg_abs_point_move",pd.Series(index=d.index,dtype=float)))/1.5
    ).clip(0,1)

    d["high_conviction_research"]=(
        (d.get("confidence","").astype(str)=="HIGH")
        & (d.get("comp_alignment","").astype(str)=="SUPPORT")
        & (numeric(d.get("comp_reliability_0_1",pd.Series(index=d.index,dtype=float))).fillna(0)>=0.5)
        & is_known
        & (d["market_disagreement_flag"]==False)
    )

    d["high_conviction_reason"]=np.select(
        [
            d["high_conviction_research"],
            d["market_data_status"]=="UNKNOWN",
            d["market_data_status"]=="AMBIGUOUS",
        ],
        [
            "HIGH confidence + calibrated comp support + event-time matched comparable markets with no major disagreement",
            "Market context UNKNOWN — no provider event matched this MLB game",
            "Market context AMBIGUOUS — provider event could not be uniquely matched by teams + start time",
        ],
        default=""
    )

    d=d.drop(columns=["_away_norm","_home_norm","_game_time"],errors="ignore")
    d.to_csv(DERIVED/"MLB_HIGH_CONVICTION_RESEARCH.csv",index=False)
    d.to_parquet(DERIVED/"MLB_HIGH_CONVICTION_RESEARCH.parquet",index=False)

    em.to_csv(DERIVED/"MLB_MARKET_EVENT_IDENTITY_MAP.csv",index=False)

    print("Identity mode: normalized teams + provider event start time -> MLB gamePk")
    print("Provider events mapped:", em["market_match_status"].value_counts(dropna=False).to_dict())
    print("High-conviction research games:",int(d["high_conviction_research"].sum()))
    print("Market status:",d["market_data_status"].value_counts(dropna=False).to_dict())
    print("Market disagreement flags (known only):",int((d["market_disagreement_flag"]==True).sum()))
    print("Comparable market groups:",int(numeric(d.get("comparable_market_groups",pd.Series(dtype=float))).fillna(0).sum()))
    print("SPORTS HULK MLB EVENT-TIME MARKET IDENTITY FIX: DONE")

if __name__=="__main__":
    run()
