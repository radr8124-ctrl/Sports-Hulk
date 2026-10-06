#!/usr/bin/env python3
from pathlib import Path
import math, re
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
SRC=ROOT/"nfl_live/player_context/derived/NFL_PLAYER_CONTEXT_MASTER_V2.csv"
ESPN=ROOT/"nfl_live/decision/NFL_ESPN_INJURIES.csv"
OUT=ROOT/"nfl_live/decision/NFL_FANTASY_WATCHLIST.csv"

POSITIONS={"QB","RB","WR","TE"}

def num(v):
    try:
        x=float(v)
        return None if math.isnan(x) else x
    except Exception:
        return None

def pkey(v):
    return re.sub(r"[^a-z0-9]+","",str(v or "").lower())

df=pd.read_csv(SRC,low_memory=False)
df=df[df["position_stats"].astype(str).isin(POSITIONS)].copy()
df=df[df["latest_team"].notna()].copy()
df=df[df["player_name_stats"].notna()].copy()

inj={}
if ESPN.exists():
    ei=pd.read_csv(ESPN,low_memory=False)
    for _,r in ei.iterrows():
        k=str(r.get("player_key") or pkey(r.get("player")))
        if k:
            inj[k]={
                "espn_status":r.get("status"),
                "espn_injury_type":r.get("injury_type"),
                "espn_injury_detail":r.get("detail"),
            }

rows=[]
for _,r in df.iterrows():
    pos=str(r.get("position_stats") or "")
    snaps=num(r.get("latest_offense_pct")) or 0.0
    snap_change=num(r.get("offense_pct_change")) or 0.0
    targ2=num(r.get("targets_l2_avg")) or 0.0
    targS=num(r.get("targets_season_avg")) or 0.0
    car2=num(r.get("carries_l2_avg")) or 0.0
    carS=num(r.get("carries_season_avg")) or 0.0
    rec2=num(r.get("receiving_yards_l2_avg")) or 0.0
    recS=num(r.get("receiving_yards_season_avg")) or 0.0
    rush2=num(r.get("rushing_yards_l2_avg")) or 0.0
    rushS=num(r.get("rushing_yards_season_avg")) or 0.0
    pass2=num(r.get("passing_yards_l2_avg")) or 0.0
    passS=num(r.get("passing_yards_season_avg")) or 0.0
    share2=num(r.get("target_share_l2_avg")) or 0.0
    shareS=num(r.get("target_share_season_avg")) or 0.0
    wopr2=num(r.get("wopr_l2_avg")) or 0.0
    woprS=num(r.get("wopr_season_avg")) or 0.0

    role_now = targ2 + car2
    role_season = targS + carS
    role_delta = role_now-role_season
    yard_now = rec2+rush2+(pass2/25.0 if pos=="QB" else 0.0)
    yard_season = recS+rushS+(passS/25.0 if pos=="QB" else 0.0)
    yard_delta=yard_now-yard_season

    score=20.0
    score += min(25.0,snaps*0.25)
    score += min(18.0,role_now*1.2)
    score += max(-10.0,min(12.0,role_delta*2.0))
    score += max(-8.0,min(10.0,yard_delta*0.12))
    score += min(10.0,share2*25.0)
    score += min(7.0,wopr2*7.0)
    score += max(-8.0,min(8.0,snap_change*0.12))

    avail=str(r.get("availability_flag") or "")
    sleeper_injury=str(r.get("injury_status") or "")
    esp=inj.get(str(r.get("player_key") or ""),{})
    esp_status=str(esp.get("espn_status") or "")

    injury_review=(
        avail not in {"","CLEAR_SLEEPER_SCREEN"}
        or sleeper_injury not in {"","nan","None"}
        or esp_status.lower() in {"questionable","doubtful","out","injured reserve","ir"}
    )
    if injury_review:
        score-=12.0

    score=max(0.0,min(100.0,score))

    if injury_review:
        trend="INJURY_REVIEW"
    elif role_delta>=2.0 or snap_change>=12.0 or yard_delta>=18.0:
        trend="OPPORTUNITY_UP"
    elif role_delta<=-2.0 or snap_change<=-12.0 or yard_delta<=-18.0:
        trend="OPPORTUNITY_DOWN"
    else:
        trend="STEADY"

    rows.append({
        "player":r.get("player_name_stats"),
        "player_key":r.get("player_key"),
        "team":r.get("latest_team"),
        "position":pos,
        "latest_completed_week":r.get("latest_completed_week"),
        "opponent":r.get("latest_opponent"),
        "latest_offense_pct":snaps,
        "offense_pct_change":snap_change,
        "targets_l2_avg":targ2,
        "targets_season_avg":targS,
        "carries_l2_avg":car2,
        "carries_season_avg":carS,
        "receiving_yards_l2_avg":rec2,
        "receiving_yards_season_avg":recS,
        "rushing_yards_l2_avg":rush2,
        "rushing_yards_season_avg":rushS,
        "passing_yards_l2_avg":pass2,
        "passing_yards_season_avg":passS,
        "target_share_l2_avg":share2,
        "target_share_season_avg":shareS,
        "wopr_l2_avg":wopr2,
        "wopr_season_avg":woprS,
        "role_delta":role_delta,
        "yardage_delta":yard_delta,
        "availability_flag":avail,
        "sleeper_injury_status":sleeper_injury,
        "espn_injury_status":esp.get("espn_status"),
        "espn_injury_type":esp.get("espn_injury_type"),
        "espn_injury_detail":esp.get("espn_injury_detail"),
        "fantasy_trend":trend,
        "fantasy_context_score":round(score,1),
        "fantasy_points_claim":False,
        "start_sit_claim":False,
    })

out=pd.DataFrame(rows)
if not out.empty:
    # Keep one current record per player and show the most actionable 80.
    out=out.sort_values(
        ["fantasy_context_score","latest_offense_pct"],
        ascending=[False,False]
    ).drop_duplicates("player_key",keep="first").head(80)

out.to_csv(OUT,index=False)
print("NFL FANTASY ROWS:",len(out))
print("TRENDS:",out["fantasy_trend"].value_counts().to_dict() if len(out) else {})
print("RESULT: NFL_FANTASY_READY")
