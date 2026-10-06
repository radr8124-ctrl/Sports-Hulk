#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
import math
import re

import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "intelligence_warehouse" / "features"
ROLE_OUT = OUT / "PLAYER_ROLE_SIGNALS_CURRENT.csv"
CATALOG_OUT = OUT / "ADVANCED_FEATURE_CATALOG.csv"
RECEIPT = OUT / "ADVANCED_FEATURE_RECEIPT.json"
NOW = datetime.now(timezone.utc).isoformat()

def read(path):
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()

def num(v):
    try:
        x=float(v)
        return None if math.isnan(x) else x
    except Exception:
        return None

def clean(v):
    if v is None:
        return ""
    if isinstance(v,float) and pd.isna(v):
        return ""
    return re.sub(r"\s+"," ",str(v).strip())

def delta(recent, season):
    a,b=num(recent),num(season)
    if a is None or b is None:
        return None
    return a-b

def score_signal(score, sample):
    if sample is not None and sample < 2:
        return "INSUFFICIENT_SAMPLE"
    if score >= 12:
        return "ROLE_UP"
    if score <= -12:
        return "ROLE_DOWN"
    return "STEADY"

def nfl_rows():
    src=ROOT/"nfl_live/player_context/derived/NFL_PLAYER_CONTEXT_MASTER_V2.csv"
    d=read(src)
    rows=[]
    if d.empty:
        return rows
    d=d[d["player_name_stats"].notna()].copy()
    for _,r in d.iterrows():
        pos=clean(r.get("position_stats"))
        sample=num(r.get("latest_completed_week"))
        snap_delta=num(r.get("offense_pct_change")) or 0.0
        snap_delta_pct=snap_delta*100.0
        if pos=="QB":
            opp=delta(r.get("attempts_l2_avg"),r.get("attempts_season_avg"))
            prod=delta(r.get("passing_yards_l2_avg"),r.get("passing_yards_season_avg"))
            role=(snap_delta_pct*.25)+((opp or 0)*1.5)+((prod or 0)*.04)
            recent=num(r.get("attempts_l2_avg")); season=num(r.get("attempts_season_avg"))
            metric="pass_attempts"
        elif pos in {"RB","FB"}:
            recent=(num(r.get("carries_l2_avg")) or 0)+(num(r.get("targets_l2_avg")) or 0)
            season=(num(r.get("carries_season_avg")) or 0)+(num(r.get("targets_season_avg")) or 0)
            opp=recent-season
            prod=delta(r.get("rushing_yards_l2_avg"),r.get("rushing_yards_season_avg"))
            role=(snap_delta_pct*.30)+(opp*2.3)+((prod or 0)*.08)
            metric="carries_plus_targets"
        elif pos in {"WR","TE"}:
            recent=num(r.get("targets_l2_avg")) or 0
            season=num(r.get("targets_season_avg")) or 0
            opp=recent-season
            share=delta(r.get("target_share_l2_avg"),r.get("target_share_season_avg"))
            wopr=delta(r.get("wopr_l2_avg"),r.get("wopr_season_avg"))
            role=(snap_delta_pct*.30)+(opp*3.0)+((share or 0)*35)+((wopr or 0)*12)
            metric="targets"
        else:
            continue
        role=max(-50,min(50,role))
        rows.append({
            "sport":"NFL","player_key":clean(r.get("player_key")),
            "player":clean(r.get("player_name_stats")),"team":clean(r.get("latest_team")),
            "position":pos,"role_metric":metric,"recent_value":recent,
            "season_value":season,"role_delta":opp,
            "snap_pct":num(r.get("latest_offense_pct")),
            "snap_pct_change":snap_delta,"role_score":round(role,2),
            "signal":score_signal(role,sample),"sample_marker":sample,
            "source_file":str(src.relative_to(ROOT)),
            "evidence_score_is_probability":False,
        })

    # Add IDP defensive snap movement from the raw snap table.
    snaps=read(ROOT/"nfl_live/player_context/derived/NFL_SNAP_COUNTS_RECENT.csv")
    if not snaps.empty:
        snaps["_week"]=pd.to_numeric(snaps["week"],errors="coerce")
        for player,g in snaps.groupby("player"):
            g=g.sort_values("_week")
            latest=g.iloc[-1]
            pos=clean(latest.get("position"))
            if pos not in {"LB","ILB","OLB","DE","DT","DL","DB","CB","S","FS","SS"}:
                continue
            curr=num(latest.get("defense_pct"))
            prev=num(g.iloc[-2].get("defense_pct")) if len(g)>=2 else None
            if curr is None:
                continue
            change=(curr-prev) if prev is not None else 0.0
            change_pct=change*100.0
            role=max(-50,min(50,change_pct*.55))
            rows.append({
                "sport":"NFL","player_key":re.sub(r"[^a-z0-9]+","",clean(player).lower()),
                "player":clean(player),"team":clean(latest.get("team")),"position":pos,
                "role_metric":"defensive_snap_pct","recent_value":curr,
                "season_value":prev,"role_delta":change,"snap_pct":curr,
                "snap_pct_change":change,"role_score":round(role,2),
                "signal":score_signal(role,num(latest.get("week"))),
                "sample_marker":num(latest.get("week")),
                "source_file":"nfl_live/player_context/derived/NFL_SNAP_COUNTS_RECENT.csv",
                "evidence_score_is_probability":False,
            })
    return rows

def nba_rows():
    src=ROOT/"nba_live/derived/NBA_PLAYER_CONTEXT.csv"
    d=read(src); rows=[]
    for _,r in d.iterrows():
        games=num(r.get("games"))
        min_d=delta(r.get("minutes_l3_avg"),r.get("minutes_season_avg"))
        pra_d=delta(r.get("pra_l3_avg"),r.get("pra_season_avg"))
        if min_d is None and pra_d is None:
            continue
        role=((min_d or 0)*2.2)+((pra_d or 0)*1.0)
        role=max(-50,min(50,role))
        rows.append({
            "sport":"NBA","player_key":clean(r.get("player_id")),
            "player":clean(r.get("player")),"team":clean(r.get("team")),
            "position":clean(r.get("position")),"role_metric":"minutes_plus_pra",
            "recent_value":num(r.get("minutes_l3_avg")),
            "season_value":num(r.get("minutes_season_avg")),
            "role_delta":min_d,"snap_pct":None,"snap_pct_change":None,
            "role_score":round(role,2),"signal":score_signal(role,games),
            "sample_marker":games,"source_file":str(src.relative_to(ROOT)),
            "evidence_score_is_probability":False,
        })
    return rows

def nhl_rows():
    src=ROOT/"nhl_live/derived/NHL_PLAYER_CONTEXT.csv"
    d=read(src); rows=[]
    for _,r in d.iterrows():
        games=num(r.get("games"))
        toi_d=delta(r.get("toi_minutes_l3_avg"),r.get("toi_minutes_season_avg"))
        sog_d=delta(r.get("shots_on_goal_l3_avg"),r.get("shots_on_goal_season_avg"))
        pts_d=delta(r.get("points_l3_avg"),r.get("points_season_avg"))
        if toi_d is None and sog_d is None and pts_d is None:
            continue
        role=((toi_d or 0)*3.0)+((sog_d or 0)*4.0)+((pts_d or 0)*3.0)
        role=max(-50,min(50,role))
        rows.append({
            "sport":"NHL","player_key":clean(r.get("player_id")),
            "player":clean(r.get("player")),"team":clean(r.get("team")),
            "position":clean(r.get("position")),"role_metric":"toi_shots_points",
            "recent_value":num(r.get("toi_minutes_l3_avg")),
            "season_value":num(r.get("toi_minutes_season_avg")),
            "role_delta":toi_d,"snap_pct":None,"snap_pct_change":None,
            "role_score":round(role,2),"signal":score_signal(role,games),
            "sample_marker":games,"source_file":str(src.relative_to(ROOT)),
            "evidence_score_is_probability":False,
        })
    return rows

def mlb_rows():
    src=ROOT/"mlb_live/derived/MLB_PLAYER_CONTEXT.csv"
    d=read(src); rows=[]
    for _,r in d.iterrows():
        group=clean(r.get("group"))
        recent_games=num(r.get("recent_games"))
        season_games=num(r.get("season_games"))
        if recent_games is None or recent_games < 2:
            continue
        if group=="HITTING":
            recent=(num(r.get("recent_total_bases_pg")) or 0)+(num(r.get("recent_walks_pg")) or 0)
            season=(num(r.get("season_total_bases_pg")) or 0)+(num(r.get("season_walks_pg")) or 0)
            dlt=recent-season
            role=max(-50,min(50,dlt*10))
            metric="total_bases_plus_walks"
        else:
            recent=(num(r.get("recent_strikeouts_pg")) or 0)+(num(r.get("recent_outs_pg")) or 0)/3
            season=(num(r.get("season_strikeouts_pg")) or 0)+(num(r.get("season_outs_pg")) or 0)/3
            dlt=recent-season
            role=max(-50,min(50,dlt*4))
            metric="pitching_workload_plus_ks"
        rows.append({
            "sport":"MLB","player_key":clean(r.get("player_key")),
            "player":clean(r.get("player")),"team":clean(r.get("team")),
            "position":clean(r.get("position")),"role_metric":metric,
            "recent_value":recent,"season_value":season,"role_delta":dlt,
            "snap_pct":None,"snap_pct_change":None,"role_score":round(role,2),
            "signal":score_signal(role,recent_games),"sample_marker":recent_games,
            "source_file":str(src.relative_to(ROOT)),
            "evidence_score_is_probability":False,
        })
    return rows

def catalog():
    return [
        {"sport":"NFL","capability":"snap_share","dataset":"NFL_SNAP_COUNTS_RECENT.csv","depth":"PLAYER_WEEK","status":"LIVE","tracking_gap":False,"rights_status":"REVIEW_BEFORE_COMMERCIAL_REDISTRIBUTION"},
        {"sport":"NFL","capability":"next_gen_passing","dataset":"NFL_NGS_PASSING_2026.csv","depth":"PLAYER_WEEK","status":"LIVE","tracking_gap":False,"rights_status":"REVIEW_BEFORE_COMMERCIAL_REDISTRIBUTION"},
        {"sport":"NFL","capability":"next_gen_receiving","dataset":"NFL_NGS_RECEIVING_2026.csv","depth":"PLAYER_WEEK","status":"LIVE","tracking_gap":False,"rights_status":"REVIEW_BEFORE_COMMERCIAL_REDISTRIBUTION"},
        {"sport":"NFL","capability":"next_gen_rushing","dataset":"NFL_NGS_RUSHING_2026.csv","depth":"PLAYER_WEEK","status":"LIVE","tracking_gap":False,"rights_status":"REVIEW_BEFORE_COMMERCIAL_REDISTRIBUTION"},
        {"sport":"MLB","capability":"statcast_pitch_arsenal","dataset":"MLB_PITCHER_ARSENAL.csv","depth":"PLAYER_PITCH_TYPE","status":"LIVE","tracking_gap":False,"rights_status":"REVIEW_BEFORE_COMMERCIAL_REDISTRIBUTION"},
        {"sport":"MLB","capability":"statcast_batter_pitch_type","dataset":"MLB_BATTER_VS_PITCH_TYPE.csv","depth":"PLAYER_PITCH_TYPE","status":"LIVE","tracking_gap":False,"rights_status":"REVIEW_BEFORE_COMMERCIAL_REDISTRIBUTION"},
        {"sport":"MLB","capability":"park_weather","dataset":"MLB_PARK_RUN_FACTORS.csv|MLB_WEATHER_FEATURES.csv","depth":"GAME_ENVIRONMENT","status":"LIVE","tracking_gap":False,"rights_status":"REVIEW_BEFORE_COMMERCIAL_REDISTRIBUTION"},
        {"sport":"NBA","capability":"minutes_role_recent_form","dataset":"NBA_PLAYER_CONTEXT.csv","depth":"PLAYER_ROLLING","status":"LIVE","tracking_gap":True,"rights_status":"REVIEW_BEFORE_COMMERCIAL_REDISTRIBUTION"},
        {"sport":"NBA","capability":"spatial_tracking","dataset":"","depth":"PLAYER_EVENT","status":"GAP","tracking_gap":True,"rights_status":"SOURCE_AND_LICENSE_REQUIRED"},
        {"sport":"NHL","capability":"toi_shots_role","dataset":"NHL_PLAYER_CONTEXT.csv","depth":"PLAYER_ROLLING","status":"LIVE","tracking_gap":True,"rights_status":"REVIEW_BEFORE_COMMERCIAL_REDISTRIBUTION"},
        {"sport":"NHL","capability":"edge_spatial_tracking","dataset":"","depth":"PLAYER_EVENT","status":"GAP","tracking_gap":True,"rights_status":"SOURCE_AND_LICENSE_REQUIRED"},
    ]

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows=nfl_rows()+nba_rows()+nhl_rows()+mlb_rows()
    df=pd.DataFrame(rows)
    if not df.empty:
        df["generated_at"]=NOW
        df=df.sort_values(["sport","role_score"],ascending=[True,False])
    df.to_csv(ROLE_OUT,index=False)

    cat=pd.DataFrame(catalog())
    cat["generated_at"]=NOW
    cat.to_csv(CATALOG_OUT,index=False)

    receipt={
        "generated_at":NOW,
        "role_signal_rows":int(len(df)),
        "rows_by_sport":df["sport"].value_counts().astype(int).to_dict() if len(df) else {},
        "signal_counts":df["signal"].value_counts().astype(int).to_dict() if len(df) else {},
        "advanced_catalog_rows":int(len(cat)),
        "tracking_gaps":cat[cat["status"].eq("GAP")][["sport","capability"]].to_dict("records"),
        "evidence_score_is_probability":False,
        "automatic_model_adjustment":False,
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True))
    print("ROLE SIGNALS:",len(df))
    print("BY SPORT:",receipt["rows_by_sport"])
    print("SIGNALS:",receipt["signal_counts"])
    print("TRACKING GAPS:",receipt["tracking_gaps"])
    print("RESULT: ADVANCED_FEATURE_STORE_READY")

if __name__=="__main__":
    main()
