#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict, deque
import json
import math
import re

import pandas as pd
import numpy as np

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "intelligence_warehouse" / "signal_calibration"
OUT.mkdir(parents=True, exist_ok=True)

HISTORY_OUT = OUT / "PLAYER_SIGNAL_WALKFORWARD_HISTORY.csv"
SUMMARY_OUT = OUT / "PLAYER_SIGNAL_CALIBRATION_SUMMARY.csv"
COMBO_OUT = OUT / "PLAYER_SIGNAL_COMBINATION_CALIBRATION.csv"
CONTRAST_OUT = OUT / "PLAYER_SIGNAL_DEFENSE_CONTRASTS.csv"
SOURCE_OUT = OUT / "PLAYER_SIGNAL_CALIBRATION_SOURCE_CATALOG.csv"
RECEIPT_OUT = OUT / "PLAYER_SIGNAL_CALIBRATION_RECEIPT.json"

NOW = datetime.now(timezone.utc)
def clean(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    return "" if text.lower() in {"nan","none","nat","<na>"} else text

def norm(value):
    return re.sub(r"[^a-z0-9]+","",clean(value).lower())

def num(value):
    try:
        x=float(value)
        return None if math.isnan(x) else x
    except Exception:
        return None

def mean(values):
    vals=[num(v) for v in values]
    vals=[v for v in vals if v is not None]
    return float(np.mean(vals)) if vals else None

def score_signal(score, sample):
    if sample < 2:
        return "INSUFFICIENT_SAMPLE"
    if score >= 12:
        return "ROLE_UP"
    if score <= -12:
        return "ROLE_DOWN"
    return "STEADY"

def pressure_label(value, low, high):
    v=num(value)
    if v is None:
        return "LIMITED_SAMPLE"
    if v <= low:
        return "SUPPRESSIVE"
    if v >= high:
        return "PERMISSIVE"
    return "NEUTRAL"

def combine_pressure(volume_signal, production_signal):
    if volume_signal=="SUPPRESSIVE" and production_signal=="SUPPRESSIVE":
        return "STRONG_SUPPRESSIVE_PROFILE"
    if volume_signal=="PERMISSIVE" and production_signal=="PERMISSIVE":
        return "STRONG_PERMISSIVE_PROFILE"
    if "LIMITED_SAMPLE" in {volume_signal,production_signal}:
        return "LIMITED_SAMPLE"
    if {volume_signal,production_signal}=={"SUPPRESSIVE","PERMISSIVE"}:
        return "MIXED_PRESSURE_PROFILE"
    if "SUPPRESSIVE" in {volume_signal,production_signal}:
        return "SUPPRESSIVE_LEAN"
    if "PERMISSIVE" in {volume_signal,production_signal}:
        return "PERMISSIVE_LEAN"
    return "NEUTRAL_PRESSURE_PROFILE"
def sample_status(n):
    n=int(n)
    if n >= 200:
        return "LARGE_SAMPLE"
    if n >= 75:
        return "MODERATE_SAMPLE"
    if n >= 25:
        return "SMALL_SAMPLE"
    return "THIN_SAMPLE"

def defense_profiles(state, position_group, min_games, min_profiles):
    profiles=[]
    for defense, by_pos in state.items():
        hist=by_pos.get(position_group, [])
        if len(hist) < min_games:
            continue
        vol=mean([x[0] for x in hist])
        prod=mean([x[1] for x in hist])
        profiles.append((defense,vol,prod,len(hist)))
    if len(profiles) < min_profiles:
        return {}
    vols=pd.Series([x[1] for x in profiles],dtype=float)
    prods=pd.Series([x[2] for x in profiles],dtype=float)
    v25,v75=vols.quantile(.25),vols.quantile(.75)
    p25,p75=prods.quantile(.25),prods.quantile(.75)
    return {
        x[0]:{
            "volume":x[1],
            "production":x[2],
            "volume_signal":pressure_label(x[1],v25,v75),
            "production_signal":pressure_label(x[2],p25,p75),
            "context":combine_pressure(
                pressure_label(x[1],v25,v75),
                pressure_label(x[2],p25,p75),
            ),
            "games":x[3],
        }
        for x in profiles
    }

def player_history_stats(history, keys, recent_n):
    out={}
    for key in keys:
        vals=[num(r.get(key)) for r in history]
        vals=[v for v in vals if v is not None]
        out[f"{key}_season"]=mean(vals)
        out[f"{key}_recent"]=mean(vals[-recent_n:])
    return out
NBA_ALIAS={"NOP":"NO","WAS":"WSH","NYK":"NY","UTA":"UTAH","GSW":"GS","SAS":"SA"}
NHL_ALIAS={"LAK":"LA","NJD":"NJ","SJS":"SJ","TBL":"TB","UTA":"UTAH"}

def team_key(sport, value):
    text=clean(value)
    if sport=="NBA":
        return NBA_ALIAS.get(text,text)
    if sport=="NHL":
        return NHL_ALIAS.get(text,text)
    return text

def current_teams(sport):
    path=ROOT/"intelligence_warehouse"/"team_style"/"TEAM_STYLE_CURRENT.csv"
    d=pd.read_csv(path,low_memory=False)
    return {
        team_key(sport,x)
        for x in d[d["sport"].astype(str)==sport]["team"].dropna().astype(str)
    }
def nba_walkforward():
    path=ROOT/"nba_live"/"history"/"NBA_PLAYER_GAME_HISTORY.csv"
    d=pd.read_csv(path,low_memory=False)
    d=d[(d["season"]==2026)&(d["season_type"]==2)].copy()
    d["start_dt"]=pd.to_datetime(d["start"],errors="coerce",utc=True,format="mixed")
    d["minutes"]=pd.to_numeric(d["minutes"],errors="coerce")
    d["pra"]=pd.to_numeric(d["pra"],errors="coerce")
    d["fg_attempts"]=pd.to_numeric(d["fg_attempts"],errors="coerce")
    d=d[
        d["start_dt"].notna()
        & (d["minutes"]>0)
        & (~d["did_not_play"].astype(bool))
    ].copy()
    teams=current_teams("NBA")
    d["team"]=d["team"].map(lambda x:team_key("NBA",x))
    d["opponent"]=d["opponent"].map(lambda x:team_key("NBA",x))
    d=d[d["team"].isin(teams)&d["opponent"].isin(teams)].copy()

    def pos_group(value):
        p=clean(value).upper()
        if p in {"G","PG","SG"}: return "G"
        if p in {"F","SF","PF"}: return "F"
        if p=="C": return "C"
        return "OTHER"

    d["position_group"]=d["position"].map(pos_group)
    d=d[d["position_group"]!="OTHER"].copy()
    player_hist=defaultdict(list)
    defense_state=defaultdict(lambda:defaultdict(list))
    rows=[]
    for start_dt,batch in d.sort_values(["start_dt","event_id"]).groupby("start_dt",sort=True):
        defense_maps={
            pos:defense_profiles(defense_state,pos,5,15)
            for pos in ["G","F","C"]
        }

        for r in batch.to_dict("records"):
            pid=clean(r.get("player_id"))
            hist=player_hist[pid]
            sample=len(hist)
            stats=player_history_stats(hist,["minutes","pra"],3)
            min_season=stats.get("minutes_season")
            min_recent=stats.get("minutes_recent")
            pra_season=stats.get("pra_season")
            pra_recent=stats.get("pra_recent")

            if None not in (min_season,min_recent,pra_season,pra_recent):
                role_score=max(-50,min(50,((min_recent-min_season)*2.2)+(pra_recent-pra_season)))
            else:
                role_score=0.0
            role_signal=score_signal(role_score,sample)

            pos=clean(r.get("position_group"))
            defense=clean(r.get("opponent"))
            profile=defense_maps.get(pos,{}).get(defense)
            defense_context=profile.get("context") if profile else "LIMITED_SAMPLE"
            volume_signal=profile.get("volume_signal") if profile else "LIMITED_SAMPLE"
            production_signal=profile.get("production_signal") if profile else "LIMITED_SAMPLE"
            defense_games=profile.get("games",0) if profile else 0
            current_minutes=num(r.get("minutes"))
            current_pra=num(r.get("pra"))
            if min_season is not None and pra_season is not None:
                outcome_delta=((current_minutes-min_season)*2.2)+(current_pra-pra_season)
                above_baseline=bool(outcome_delta>0)
            else:
                outcome_delta=None
                above_baseline=None

            rows.append({
                "sport":"NBA",
                "interaction_family":"PLAYER_ROLE_X_DEFENSE_POSITION",
                "event_id":clean(r.get("event_id")),
                "start":clean(r.get("start")),
                "season":"2025-26",
                "player_id":pid,
                "player":clean(r.get("player")),
                "team":clean(r.get("team")),
                "opponent":defense,
                "position":clean(r.get("position")),
                "position_group":pos,
                "pregame_player_games":sample,
                "pregame_role_score":role_score,
                "pregame_role_signal":role_signal,
                "pregame_role_recent_value":min_recent,
                "pregame_role_season_value":min_season,
                "pregame_defense_games":defense_games,
                "pregame_volume_pressure_signal":volume_signal,
                "pregame_production_pressure_signal":production_signal,
                "pregame_defense_context":defense_context,
                "pregame_defense_volume_value":profile.get("volume") if profile else None,
                "pregame_defense_production_value":profile.get("production") if profile else None,
                "realized_primary_value":current_minutes,
                "realized_secondary_value":current_pra,
                "realized_outcome_delta":outcome_delta,
                "realized_above_baseline":above_baseline,
                "calibration_eligible":bool(
                    sample>=2 and defense_context!="LIMITED_SAMPLE" and outcome_delta is not None
                ),
                "role_reconstruction":"EXACT_CURRENT_FORMULA_FROM_PRIOR_GAMES",
                "leakage_guard":"FEATURES_COMPUTED_BEFORE_EVENT_UPDATE",
            })
        # Update player histories only after every row in this start-time batch is scored.
        for r in batch.to_dict("records"):
            pid=clean(r.get("player_id"))
            player_hist[pid].append({
                "minutes":num(r.get("minutes")),
                "pra":num(r.get("pra")),
            })

        # Update opponent allowed-production history after the batch is scored.
        grouped=batch.groupby(
            ["opponent","event_id","position_group"],as_index=False
        ).agg(
            fg_attempts_allowed=("fg_attempts","sum"),
            pra_allowed=("pra","sum"),
        )
        for r in grouped.to_dict("records"):
            defense_state[clean(r.get("opponent"))][clean(r.get("position_group"))].append(
                (num(r.get("fg_attempts_allowed")),num(r.get("pra_allowed")))
            )

    return rows,{
        "status":"WALKFORWARD_READY",
        "rows":len(rows),
        "eligible":sum(bool(r.get("calibration_eligible")) for r in rows),
        "source_file":str(path.relative_to(ROOT)),
        "role_reconstruction":"EXACT_CURRENT_FORMULA_FROM_PRIOR_GAMES",
        "defense_min_games":5,
    }
def nhl_walkforward():
    path=ROOT/"nhl_live"/"history"/"NHL_PLAYER_GAME_HISTORY.csv"
    d=pd.read_csv(path,low_memory=False)
    d=d[(d["season"]==20252026)&(d["game_type"]==2)].copy()
    d["start_dt"]=pd.to_datetime(d["start"],errors="coerce",utc=True,format="mixed")
    for c in ["toi_minutes","shots_on_goal","points"]:
        d[c]=pd.to_numeric(d[c],errors="coerce")
    d=d[d["start_dt"].notna()&(d["toi_minutes"]>0)].copy()
    teams=current_teams("NHL")
    d["team"]=d["team"].map(lambda x:team_key("NHL",x))
    d["opponent"]=d["opponent"].map(lambda x:team_key("NHL",x))
    d=d[d["team"].isin(teams)&d["opponent"].isin(teams)].copy()

    def pos_group(value):
        p=clean(value).upper()
        if p=="D": return "D"
        if p=="C": return "C"
        if p in {"L","R"}: return "W"
        return "OTHER"

    d["position_group"]=d["position"].map(pos_group)
    d=d[d["position_group"]!="OTHER"].copy()
    player_hist=defaultdict(list)
    defense_state=defaultdict(lambda:defaultdict(list))
    rows=[]
    for start_dt,batch in d.sort_values(["start_dt","event_id"]).groupby("start_dt",sort=True):
        defense_maps={
            pos:defense_profiles(defense_state,pos,5,15)
            for pos in ["C","W","D"]
        }

        for r in batch.to_dict("records"):
            pid=clean(r.get("player_id"))
            hist=player_hist[pid]
            sample=len(hist)
            stats=player_history_stats(hist,["toi_minutes","shots_on_goal","points"],3)

            toi_s=stats.get("toi_minutes_season")
            toi_r=stats.get("toi_minutes_recent")
            sog_s=stats.get("shots_on_goal_season")
            sog_r=stats.get("shots_on_goal_recent")
            pts_s=stats.get("points_season")
            pts_r=stats.get("points_recent")

            if None not in (toi_s,toi_r,sog_s,sog_r,pts_s,pts_r):
                role_score=max(
                    -50,min(
                        50,
                        ((toi_r-toi_s)*3.0)+((sog_r-sog_s)*4.0)+((pts_r-pts_s)*3.0),
                    ),
                )
            else:
                role_score=0.0
            role_signal=score_signal(role_score,sample)

            pos=clean(r.get("position_group"))
            defense=clean(r.get("opponent"))
            profile=defense_maps.get(pos,{}).get(defense)
            defense_context=profile.get("context") if profile else "LIMITED_SAMPLE"
            current_toi=num(r.get("toi_minutes"))
            current_sog=num(r.get("shots_on_goal"))
            current_pts=num(r.get("points"))
            if toi_s is not None and sog_s is not None and pts_s is not None:
                outcome_delta=(
                    ((current_toi-toi_s)*3.0)
                    +((current_sog-sog_s)*4.0)
                    +((current_pts-pts_s)*3.0)
                )
                above_baseline=bool(outcome_delta>0)
            else:
                outcome_delta=None
                above_baseline=None

            rows.append({
                "sport":"NHL",
                "interaction_family":"PLAYER_ROLE_X_DEFENSE_POSITION",
                "event_id":clean(r.get("event_id")),
                "start":clean(r.get("start")),
                "season":"2025-26",
                "player_id":pid,
                "player":clean(r.get("player")),
                "team":clean(r.get("team")),
                "opponent":defense,
                "position":clean(r.get("position")),
                "position_group":pos,
                "pregame_player_games":sample,
                "pregame_role_score":role_score,
                "pregame_role_signal":role_signal,
                "pregame_role_recent_value":toi_r,
                "pregame_role_season_value":toi_s,
                "pregame_defense_games":profile.get("games",0) if profile else 0,
                "pregame_volume_pressure_signal":profile.get("volume_signal") if profile else "LIMITED_SAMPLE",
                "pregame_production_pressure_signal":profile.get("production_signal") if profile else "LIMITED_SAMPLE",
                "pregame_defense_context":defense_context,
                "pregame_defense_volume_value":profile.get("volume") if profile else None,
                "pregame_defense_production_value":profile.get("production") if profile else None,
                "realized_primary_value":current_toi,
                "realized_secondary_value":(current_sog or 0)+(current_pts or 0),
                "realized_outcome_delta":outcome_delta,
                "realized_above_baseline":above_baseline,
                "calibration_eligible":bool(
                    sample>=2 and defense_context!="LIMITED_SAMPLE" and outcome_delta is not None
                ),
                "role_reconstruction":"EXACT_CURRENT_FORMULA_FROM_PRIOR_GAMES",
                "leakage_guard":"FEATURES_COMPUTED_BEFORE_EVENT_UPDATE",
            })
        for r in batch.to_dict("records"):
            pid=clean(r.get("player_id"))
            player_hist[pid].append({
                "toi_minutes":num(r.get("toi_minutes")),
                "shots_on_goal":num(r.get("shots_on_goal")),
                "points":num(r.get("points")),
            })

        grouped=batch.groupby(
            ["opponent","event_id","position_group"],as_index=False
        ).agg(
            shots_allowed=("shots_on_goal","sum"),
            points_allowed=("points","sum"),
        )
        for r in grouped.to_dict("records"):
            defense_state[clean(r.get("opponent"))][clean(r.get("position_group"))].append(
                (num(r.get("shots_allowed")),num(r.get("points_allowed")))
            )

    return rows,{
        "status":"WALKFORWARD_READY",
        "rows":len(rows),
        "eligible":sum(bool(r.get("calibration_eligible")) for r in rows),
        "source_file":str(path.relative_to(ROOT)),
        "role_reconstruction":"EXACT_CURRENT_FORMULA_FROM_PRIOR_GAMES",
        "defense_min_games":5,
    }
def nfl_offense_walkforward():
    path=ROOT/"nfl_live"/"player_context"/"raw"/"player_stats.parquet"
    d=pd.read_parquet(path)
    d=d[(d["season"]==2026)&(d["season_type"].astype(str).str.upper()=="REG")].copy()

    def pos_group(value):
        p=clean(value).upper()
        if p=="QB": return "QB"
        if p in {"RB","FB"}: return "RB"
        if p=="WR": return "WR"
        if p=="TE": return "TE"
        return "OTHER"

    d["position_group"]=d["position"].map(pos_group)
    skill=d[d["position_group"]!="OTHER"].copy()
    numeric=[
        "attempts","passing_yards","sacks_suffered","carries","rushing_yards",
        "targets","receiving_yards","target_share","wopr",
    ]
    for c in numeric:
        skill[c]=pd.to_numeric(skill[c],errors="coerce").fillna(0)

    snaps=pd.read_parquet(
        ROOT/"nfl_live"/"player_context"/"raw"/"snap_counts.parquet"
    )
    snaps=snaps[
        (snaps["season"]==2026)
        &(snaps["game_type"].astype(str).str.upper()=="REG")
    ].copy()
    skill["_name_key"]=skill["player_display_name"].map(norm)
    snaps["_name_key"]=snaps["player"].map(norm)
    skill=skill.merge(
        snaps[["game_id","team","_name_key","offense_pct"]],
        on=["game_id","team","_name_key"],
        how="left",
    )
    skill["offense_pct"]=pd.to_numeric(skill["offense_pct"],errors="coerce")

    player_hist=defaultdict(list)
    defense_state=defaultdict(lambda:defaultdict(list))
    rows=[]
    for week,batch in skill.sort_values(["week","game_id"]).groupby("week",sort=True):
        defense_maps={
            pos:defense_profiles(defense_state,pos,2,16)
            for pos in ["QB","RB","WR","TE"]
        }

        for r in batch.to_dict("records"):
            pid=clean(r.get("player_id")) or norm(r.get("player_display_name"))
            hist=player_hist[pid]
            sample=len(hist)
            pos=clean(r.get("position_group"))
            snap_ready=(
                sample>=2
                and num(hist[-1].get("offense_pct")) is not None
                and num(hist[-2].get("offense_pct")) is not None
            )
            snap_delta_pct=(
                (num(hist[-1].get("offense_pct"))-num(hist[-2].get("offense_pct")))*100.0
                if snap_ready else 0.0
            )
            reconstruction=(
                "EXACT_CORRECTED_FORMULA_WITH_SNAP_HISTORY"
                if snap_ready
                else "PARTIAL_SNAP_HISTORY_FALLBACK"
            )

            if pos=="QB":
                stats=player_history_stats(hist,["attempts","passing_yards"],2)
                season=stats.get("attempts_season")
                recent=stats.get("attempts_recent")
                prod_s=stats.get("passing_yards_season")
                prod_r=stats.get("passing_yards_recent")
                role_score=(
                    (snap_delta_pct*.25)
                    +((recent-season)*1.5)
                    +((prod_r-prod_s)*.04)
                    if None not in (season,recent,prod_s,prod_r) else 0.0
                )
                current_primary=num(r.get("attempts"))
                current_secondary=num(r.get("passing_yards"))
            elif pos=="RB":
                hist2=[]
                for h in hist:
                    hist2.append({
                        "opportunities":(num(h.get("carries")) or 0)+(num(h.get("targets")) or 0),
                        "rushing_yards":num(h.get("rushing_yards")) or 0,
                    })
                stats=player_history_stats(hist2,["opportunities","rushing_yards"],2)
                season=stats.get("opportunities_season")
                recent=stats.get("opportunities_recent")
                prod_s=stats.get("rushing_yards_season")
                prod_r=stats.get("rushing_yards_recent")
                role_score=(
                    (snap_delta_pct*.30)
                    +((recent-season)*2.3)
                    +((prod_r-prod_s)*.08)
                    if None not in (season,recent,prod_s,prod_r) else 0.0
                )
                current_primary=(num(r.get("carries")) or 0)+(num(r.get("targets")) or 0)
                current_secondary=num(r.get("rushing_yards"))
            else:
                stats=player_history_stats(hist,["targets","target_share","wopr"],2)
                season=stats.get("targets_season")
                recent=stats.get("targets_recent")
                share_s=stats.get("target_share_season")
                share_r=stats.get("target_share_recent")
                wopr_s=stats.get("wopr_season")
                wopr_r=stats.get("wopr_recent")
                role_score=(
                    (snap_delta_pct*.30)
                    +((recent-season)*3.0)
                    +((share_r-share_s)*35.0)
                    +((wopr_r-wopr_s)*12.0)
                    if None not in (season,recent,share_s,share_r,wopr_s,wopr_r)
                    else 0.0
                )
                current_primary=num(r.get("targets"))
                current_secondary=num(r.get("receiving_yards"))

            role_score=max(-50,min(50,role_score))
            role_signal=score_signal(role_score,sample)
            defense=clean(r.get("opponent_team"))
            profile=defense_maps.get(pos,{}).get(defense)
            defense_context=profile.get("context") if profile else "LIMITED_SAMPLE"

            outcome_delta=(
                current_primary-season
                if current_primary is not None and season is not None else None
            )
            rows.append({
                "sport":"NFL",
                "interaction_family":"PLAYER_ROLE_X_DEFENSE_POSITION",
                "event_id":clean(r.get("game_id")),
                "start":f"2026-W{int(week):02d}",
                "season":"2026",
                "player_id":pid,
                "player":clean(r.get("player_display_name")),
                "team":clean(r.get("team")),
                "opponent":defense,
                "position":clean(r.get("position")),
                "position_group":pos,
                "pregame_player_games":sample,
                "pregame_role_score":role_score,
                "pregame_role_signal":role_signal,
                "pregame_role_recent_value":recent,
                "pregame_role_season_value":season,
                "pregame_defense_games":profile.get("games",0) if profile else 0,
                "pregame_volume_pressure_signal":profile.get("volume_signal") if profile else "LIMITED_SAMPLE",
                "pregame_production_pressure_signal":profile.get("production_signal") if profile else "LIMITED_SAMPLE",
                "pregame_defense_context":defense_context,
                "pregame_defense_volume_value":profile.get("volume") if profile else None,
                "pregame_defense_production_value":profile.get("production") if profile else None,
                "realized_primary_value":current_primary,
                "realized_secondary_value":current_secondary,
                "realized_outcome_delta":outcome_delta,
                "realized_above_baseline":(
                    bool(outcome_delta>0) if outcome_delta is not None else None
                ),
                "calibration_eligible":bool(
                    sample>=2 and defense_context!="LIMITED_SAMPLE" and outcome_delta is not None
                ),
                "role_reconstruction":reconstruction,
                "leakage_guard":"FEATURES_COMPUTED_FROM_PRIOR_WEEKS_ONLY",
            })
        for r in batch.to_dict("records"):
            pid=clean(r.get("player_id")) or norm(r.get("player_display_name"))
            player_hist[pid].append({
                "attempts":num(r.get("attempts")) or 0,
                "passing_yards":num(r.get("passing_yards")) or 0,
                "carries":num(r.get("carries")) or 0,
                "rushing_yards":num(r.get("rushing_yards")) or 0,
                "targets":num(r.get("targets")) or 0,
                "receiving_yards":num(r.get("receiving_yards")) or 0,
                "target_share":num(r.get("target_share")) or 0,
                "wopr":num(r.get("wopr")) or 0,
                "offense_pct":num(r.get("offense_pct")),
            })

        b=batch.copy()
        b["opportunities"]=b["carries"]+b["targets"]
        b["scrimmage_yards"]=b["rushing_yards"]+b["receiving_yards"]
        grouped=b.groupby(
            ["opponent_team","game_id","position_group"],as_index=False
        ).agg(
            attempts=("attempts","sum"),
            passing_yards=("passing_yards","sum"),
            opportunities=("opportunities","sum"),
            scrimmage_yards=("scrimmage_yards","sum"),
            targets=("targets","sum"),
            receiving_yards=("receiving_yards","sum"),
        )
        for r in grouped.to_dict("records"):
            pos=clean(r.get("position_group"))
            if pos=="QB":
                vol,prod=num(r.get("attempts")),num(r.get("passing_yards"))
            elif pos=="RB":
                vol,prod=num(r.get("opportunities")),num(r.get("scrimmage_yards"))
            else:
                vol,prod=num(r.get("targets")),num(r.get("receiving_yards"))
            defense_state[clean(r.get("opponent_team"))][pos].append((vol,prod))

    return rows,{
        "status":"WALKFORWARD_READY",
        "rows":len(rows),
        "eligible":sum(bool(r.get("calibration_eligible")) for r in rows),
        "source_file":str(path.relative_to(ROOT)),
        "role_reconstruction":"SNAP_AWARE_CORRECTED_FORMULA_WITH_ROW_FALLBACK",
        "defense_min_games":2,
    }
def nfl_idp_walkforward():
    snap_path=ROOT/"nfl_live"/"player_context"/"raw"/"snap_counts.parquet"
    stat_path=ROOT/"nfl_live"/"player_context"/"raw"/"player_stats.parquet"
    snaps=pd.read_parquet(snap_path)
    stats=pd.read_parquet(stat_path)
    snaps=snaps[(snaps["season"]==2026)&(snaps["game_type"].astype(str).str.upper()=="REG")].copy()
    stats=stats[(stats["season"]==2026)&(stats["season_type"].astype(str).str.upper()=="REG")].copy()

    idp_positions={"LB","ILB","OLB","DE","DT","DL","DB","CB","S","FS","SS"}
    snaps=snaps[snaps["position"].astype(str).str.upper().isin(idp_positions)].copy()
    snaps["defense_pct"]=pd.to_numeric(snaps["defense_pct"],errors="coerce")
    snaps["defense_snaps"]=pd.to_numeric(snaps["defense_snaps"],errors="coerce")
    snaps=snaps[snaps["defense_pct"].notna()].copy()

    for c in ["attempts","sacks_suffered","carries"]:
        stats[c]=pd.to_numeric(stats[c],errors="coerce").fillna(0)
    team_games=stats.groupby(["week","game_id","team"],as_index=False).agg(
        attempts=("attempts","sum"),
        sacks=("sacks_suffered","sum"),
        carries=("carries","sum"),
    )
    team_games["plays"]=team_games["attempts"]+team_games["sacks"]+team_games["carries"]

    player_hist=defaultdict(list)
    offense_state=defaultdict(list)
    rows=[]
    weeks=sorted(pd.to_numeric(snaps["week"],errors="coerce").dropna().astype(int).unique())
    for week in weeks:
        profiles=[]
        for team,hist in offense_state.items():
            if len(hist) < 2:
                continue
            profiles.append((team,mean(hist),len(hist)))

        volume_map={}
        if len(profiles) >= 16:
            vals=pd.Series([x[1] for x in profiles],dtype=float)
            q25,q75=vals.quantile(.25),vals.quantile(.75)
            for team,value,games in profiles:
                if value <= q25:
                    signal="LOW_OPPONENT_VOLUME"
                elif value >= q75:
                    signal="HIGH_OPPONENT_VOLUME"
                else:
                    signal="MID_OPPONENT_VOLUME"
                volume_map[team]={
                    "plays_per_game":value,
                    "games":games,
                    "signal":signal,
                }

        batch=snaps[pd.to_numeric(snaps["week"],errors="coerce")==week].copy()
        for r in batch.to_dict("records"):
            pid=clean(r.get("pfr_player_id")) or norm(r.get("player"))
            hist=player_hist[pid]
            sample=len(hist)
            if sample >= 2:
                prior_change=(num(hist[-1].get("defense_pct")) or 0)-(num(hist[-2].get("defense_pct")) or 0)
                role_score=max(-50,min(50,(prior_change*100.0)*.55))
            else:
                role_score=0.0
            role_signal=score_signal(role_score,sample)

            season_pct=mean([h.get("defense_pct") for h in hist])
            current_pct=num(r.get("defense_pct"))
            outcome_delta=(
                current_pct-season_pct
                if current_pct is not None and season_pct is not None else None
            )
            opponent=clean(r.get("opponent"))
            volume=volume_map.get(opponent)
            defense_context=volume.get("signal") if volume else "LIMITED_SAMPLE"
            rows.append({
                "sport":"NFL",
                "interaction_family":"IDP_ROLE_X_OPPOSING_OFFENSE_VOLUME",
                "event_id":clean(r.get("game_id")),
                "start":f"2026-W{int(week):02d}",
                "season":"2026",
                "player_id":pid,
                "player":clean(r.get("player")),
                "team":clean(r.get("team")),
                "opponent":opponent,
                "position":clean(r.get("position")),
                "position_group":"IDP",
                "pregame_player_games":sample,
                "pregame_role_score":role_score,
                "pregame_role_signal":role_signal,
                "pregame_role_recent_value":(
                    num(hist[-1].get("defense_pct")) if hist else None
                ),
                "pregame_role_season_value":season_pct,
                "pregame_defense_games":volume.get("games",0) if volume else 0,
                "pregame_volume_pressure_signal":(
                    volume.get("signal") if volume else "LIMITED_SAMPLE"
                ),
                "pregame_production_pressure_signal":"NOT_APPLICABLE",
                "pregame_defense_context":defense_context,
                "pregame_defense_volume_value":(
                    volume.get("plays_per_game") if volume else None
                ),
                "pregame_defense_production_value":None,
                "realized_primary_value":current_pct,
                "realized_secondary_value":num(r.get("defense_snaps")),
                "realized_outcome_delta":outcome_delta,
                "realized_above_baseline":(
                    bool(outcome_delta>0) if outcome_delta is not None else None
                ),
                "calibration_eligible":bool(
                    sample>=2 and defense_context!="LIMITED_SAMPLE" and outcome_delta is not None
                ),
                "role_reconstruction":"EXACT_DEFENSIVE_SNAP_CHANGE_FORMULA",
                "leakage_guard":"FEATURES_COMPUTED_FROM_PRIOR_WEEKS_ONLY",
            })

        for r in batch.to_dict("records"):
            pid=clean(r.get("pfr_player_id")) or norm(r.get("player"))
            player_hist[pid].append({
                "defense_pct":num(r.get("defense_pct")),
                "defense_snaps":num(r.get("defense_snaps")),
            })

        current_team_games=team_games[pd.to_numeric(team_games["week"],errors="coerce")==week]
        for r in current_team_games.to_dict("records"):
            offense_state[clean(r.get("team"))].append(num(r.get("plays")))

    return rows,{
        "status":"WALKFORWARD_READY",
        "rows":len(rows),
        "eligible":sum(bool(r.get("calibration_eligible")) for r in rows),
        "source_file":str(snap_path.relative_to(ROOT)),
        "role_reconstruction":"EXACT_DEFENSIVE_SNAP_CHANGE_FORMULA",
        "defense_min_games":2,
    }

def mlb_role_walkforward():
    path=ROOT/"intelligence_warehouse"/"mlb_player_history"/"MLB_PLAYER_GAME_HISTORY.csv"
    d=pd.read_csv(path,low_memory=False)
    d=d[(d["game_type"]=="R") & d["season"].isin([2025,2026])].copy()
    d["start_dt"]=pd.to_datetime(d["game_date"],errors="coerce",utc=True,format="mixed")
    d["role_value"]=pd.to_numeric(d["role_value"],errors="coerce")
    d=d[d["start_dt"].notna() & d["role_value"].notna()].copy()
    d["player_id"]=d["player_id"].astype(str).str.replace(r"\.0$","",regex=True)

    rows=[]
    fourteen=pd.Timedelta(days=14)

    for (season,pid,grp),g in d.sort_values(
        ["season","player_id","group","start_dt","game_pk"]
    ).groupby(["season","player_id","group"],sort=False):
        season_sum=0.0
        season_count=0
        recent=deque()
        multiplier=10.0 if grp=="HITTING" else 4.0
        role_metric=(
            "total_bases_plus_walks"
            if grp=="HITTING"
            else "pitching_workload_plus_ks"
        )

        for rr in g.itertuples(index=False):
            current_time=rr.start_dt
            while recent and current_time-recent[0][0] > fourteen:
                recent.popleft()

            season_mean=(season_sum/season_count) if season_count else None
            recent_vals=[x[1] for x in recent]
            recent_mean=mean(recent_vals)
            recent_count=len(recent_vals)

            if season_mean is not None and recent_mean is not None:
                role_score=max(-50,min(50,(recent_mean-season_mean)*multiplier))
            else:
                role_score=0.0
            role_signal=score_signal(role_score,recent_count)
            realized=float(rr.role_value)
            outcome_delta=(
                realized-season_mean
                if season_mean is not None
                else None
            )

            rows.append({
                "sport":"MLB",
                "interaction_family":"MLB_PLAYER_ROLE_HISTORY",
                "event_id":clean(rr.game_pk),
                "start":clean(rr.game_date),
                "season":str(season),
                "player_id":pid,
                "player":clean(rr.player),
                "team":clean(rr.team),
                "opponent":clean(rr.opponent),
                "position":clean(rr.position),
                "position_group":clean(grp),
                "pregame_player_games":recent_count,
                "pregame_season_games":season_count,
                "pregame_role_score":role_score,
                "pregame_role_signal":role_signal,
                "pregame_role_recent_value":recent_mean,
                "pregame_role_season_value":season_mean,
                "pregame_defense_games":0,
                "pregame_volume_pressure_signal":"NOT_MODELED",
                "pregame_production_pressure_signal":"NOT_MODELED",
                "pregame_defense_context":"NOT_MODELED",
                "pregame_defense_volume_value":None,
                "pregame_defense_production_value":None,
                "realized_primary_value":realized,
                "realized_secondary_value":None,
                "realized_outcome_delta":outcome_delta,
                "realized_above_baseline":(
                    bool(outcome_delta>0) if outcome_delta is not None else None
                ),
                "calibration_eligible":False,
                "role_reconstruction":"EXACT_CURRENT_MLB_ROLE_FORMULA_14D_PRIOR_WINDOW",
                "leakage_guard":"FEATURES_COMPUTED_FROM_PRIOR_GAMES_ONLY",
                "role_metric":role_metric,
            })

            season_sum+=realized
            season_count+=1
            recent.append((current_time,realized))

    return rows,{
        "status":"WALKFORWARD_ROLE_ONLY_READY",
        "rows":len(rows),
        "eligible":0,
        "source_file":str(path.relative_to(ROOT)),
        "role_reconstruction":"EXACT_CURRENT_MLB_ROLE_FORMULA_14D_PRIOR_WINDOW",
        "defense_min_games":None,
    }

def outcome_unit(row):
    sport=clean(row.get("sport"))
    family=clean(row.get("interaction_family"))
    pos=clean(row.get("position_group"))
    if sport=="NFL" and family=="IDP_ROLE_X_OPPOSING_OFFENSE_VOLUME":
        return "DEFENSE_SNAP_PCT_DELTA"
    if sport=="NFL":
        if pos=="QB": return "PASS_ATTEMPTS_DELTA"
        if pos=="RB": return "CARRIES_PLUS_TARGETS_DELTA"
        if pos in {"WR","TE"}: return "TARGETS_DELTA"
    if sport=="NBA":
        return "2.2_MINUTES_PLUS_PRA_DELTA_COMPOSITE"
    if sport=="NHL":
        return "3_TOI_PLUS_4_SOG_PLUS_3_POINTS_DELTA_COMPOSITE"
    if sport=="MLB":
        return "ROLE_VALUE_DELTA_FROM_PREGAME_SEASON_BASELINE"
    return "UNKNOWN"

def aggregate_metrics(frame):
    x=frame[pd.to_numeric(frame["realized_outcome_delta"],errors="coerce").notna()].copy()
    vals=pd.to_numeric(x["realized_outcome_delta"],errors="coerce")
    n=len(x)
    if n==0:
        return {
            "n":0,"mean_outcome_delta":None,"median_outcome_delta":None,
            "above_baseline_rate":None,"outcome_std":None,"outcome_sem":None,
            "sample_status":"THIN_SAMPLE",
        }
    std=float(vals.std(ddof=1)) if n>1 else None
    sem=(std/math.sqrt(n)) if std is not None else None
    above=pd.to_numeric(x["realized_above_baseline"],errors="coerce")
    return {
        "n":n,
        "mean_outcome_delta":float(vals.mean()),
        "median_outcome_delta":float(vals.median()),
        "above_baseline_rate":float(above.mean()) if above.notna().any() else None,
        "outcome_std":std,
        "outcome_sem":sem,
        "sample_status":sample_status(n),
    }
def build_factor_summary(history):
    rows=[]
    for keys,factor_type,factor_col,mask in [
        (
            ["sport","interaction_family","position_group","pregame_role_signal"],
            "ROLE_SIGNAL","pregame_role_signal",
            history["pregame_role_signal"].ne("INSUFFICIENT_SAMPLE"),
        ),
        (
            ["sport","interaction_family","position_group","pregame_defense_context"],
            "OPPONENT_CONTEXT","pregame_defense_context",
            ~history["pregame_defense_context"].isin(["LIMITED_SAMPLE","","NOT_MODELED","NOT_APPLICABLE"]),
        ),
    ]:
        subset=history[mask].copy()
        for group_vals,frame in subset.groupby(keys,dropna=False):
            if not isinstance(group_vals,tuple):
                group_vals=(group_vals,)
            data=dict(zip(keys,group_vals))
            metrics=aggregate_metrics(frame)
            row={
                "factor_type":factor_type,
                "factor_value":clean(data.get(factor_col)),
                "sport":clean(data.get("sport")),
                "interaction_family":clean(data.get("interaction_family")),
                "position_group":clean(data.get("position_group")),
                "outcome_unit":clean(frame["outcome_unit"].iloc[0]) if len(frame) else "",
                **metrics,
            }
            rows.append(row)
    return pd.DataFrame(rows)

def build_combo_summary(history):
    eligible=history[history["calibration_eligible"].astype(bool)].copy()
    rows=[]
    keys=[
        "sport","interaction_family","position_group",
        "pregame_role_signal","pregame_defense_context",
    ]
    for group_vals,frame in eligible.groupby(keys,dropna=False):
        data=dict(zip(keys,group_vals))
        rows.append({
            **data,
            "outcome_unit":clean(frame["outcome_unit"].iloc[0]) if len(frame) else "",
            **aggregate_metrics(frame),
        })
    return pd.DataFrame(rows)
def build_defense_contrasts(combo):
    rows=[]
    keys=["sport","interaction_family","position_group","pregame_role_signal"]
    for group_vals,g in combo.groupby(keys,dropna=False):
        data=dict(zip(keys,group_vals))
        permissive=g[g["pregame_defense_context"]=="STRONG_PERMISSIVE_PROFILE"]
        suppressive=g[g["pregame_defense_context"]=="STRONG_SUPPRESSIVE_PROFILE"]
        if len(permissive)!=1 or len(suppressive)!=1:
            continue
        p=permissive.iloc[0]
        s=suppressive.iloc[0]
        n_min=min(int(p["n"]),int(s["n"]))
        rows.append({
            **data,
            "outcome_unit":clean(p.get("outcome_unit")),
            "permissive_n":int(p["n"]),
            "suppressive_n":int(s["n"]),
            "permissive_mean_outcome_delta":num(p.get("mean_outcome_delta")),
            "suppressive_mean_outcome_delta":num(s.get("mean_outcome_delta")),
            "permissive_minus_suppressive_mean":(
                num(p.get("mean_outcome_delta"))-num(s.get("mean_outcome_delta"))
            ),
            "permissive_above_baseline_rate":num(p.get("above_baseline_rate")),
            "suppressive_above_baseline_rate":num(s.get("above_baseline_rate")),
            "permissive_minus_suppressive_above_rate":(
                num(p.get("above_baseline_rate"))-num(s.get("above_baseline_rate"))
            ),
            "contrast_sample_status":sample_status(n_min),
        })
    return pd.DataFrame(rows)

builders=[
    ("NFL_OFFENSE",nfl_offense_walkforward),
    ("NFL_IDP",nfl_idp_walkforward),
    ("NBA",nba_walkforward),
    ("NHL",nhl_walkforward),
    ("MLB_ROLE",mlb_role_walkforward),
]

history_rows=[]
source_rows=[]
errors=[]
for label,builder in builders:
    try:
        rows,meta=builder()
        history_rows.extend(rows)
        source_rows.append({
            "lane":label,
            "status":meta.get("status","UNKNOWN"),
            "rows":int(meta.get("rows",len(rows))),
            "eligible_rows":int(meta.get("eligible",0)),
            "source_file":clean(meta.get("source_file")),
            "role_reconstruction":clean(meta.get("role_reconstruction")),
            "defense_min_games":meta.get("defense_min_games"),
            "generated_at":NOW.isoformat(),
        })
    except Exception as exc:
        errors.append({"lane":label,"error":repr(exc)})
        source_rows.append({
            "lane":label,"status":"ERROR","rows":0,"eligible_rows":0,
            "source_file":"","role_reconstruction":"","defense_min_games":None,
            "generated_at":NOW.isoformat(),
        })

for label,reason in [
    ("CBB","NO_GOVERNED_PLAYER_ROLE_HISTORY"),
    ("CFB","NO_GOVERNED_PLAYER_ROLE_AND_DEFENSE_HISTORY"),
]:
    source_rows.append({
        "lane":label,"status":reason,"rows":0,"eligible_rows":0,
        "source_file":"","role_reconstruction":"","defense_min_games":None,
        "generated_at":NOW.isoformat(),
    })
history=pd.DataFrame(history_rows)
if not history.empty:
    history["outcome_unit"]=history.apply(lambda r:outcome_unit(r),axis=1)
    history["walkforward_identity_key"]=history.apply(
        lambda r:"|".join([
            clean(r.get("sport")),
            clean(r.get("interaction_family")),
            clean(r.get("event_id")),
            clean(r.get("player_id")) or norm(r.get("player")),
            clean(r.get("position_group")),
        ]),
        axis=1,
    )
    history["generated_at"]=NOW.isoformat()
    history["score_is_probability"]=False
    history["automatic_model_adjustment"]=False
    history=history.sort_values(
        ["sport","interaction_family","start","event_id","player_id"],
        na_position="last",
    )

summary=build_factor_summary(history) if not history.empty else pd.DataFrame()
combo=build_combo_summary(history) if not history.empty else pd.DataFrame()
contrast=build_defense_contrasts(combo) if not combo.empty else pd.DataFrame()
sources=pd.DataFrame(source_rows)

for frame in [summary,combo,contrast,sources]:
    if not frame.empty:
        frame["generated_at"]=NOW.isoformat()
if not summary.empty:
    summary["score_is_probability"]=False
    summary["automatic_model_adjustment"]=False
if not combo.empty:
    combo["score_is_probability"]=False
    combo["automatic_model_adjustment"]=False
if not contrast.empty:
    contrast["score_is_probability"]=False
    contrast["automatic_model_adjustment"]=False

history.to_csv(HISTORY_OUT,index=False)
summary.to_csv(SUMMARY_OUT,index=False)
combo.to_csv(COMBO_OUT,index=False)
contrast.to_csv(CONTRAST_OUT,index=False)
sources.to_csv(SOURCE_OUT,index=False)
eligible=history[history["calibration_eligible"].astype(bool)].copy() if not history.empty else pd.DataFrame()
identity_duplicates=int(
    history.duplicated(["walkforward_identity_key"]).sum()
) if not history.empty else 0

eligible_guard_failures=0
if not eligible.empty:
    eligible_guard_failures=int(
        (
            (pd.to_numeric(eligible["pregame_player_games"],errors="coerce")<2)
            | (eligible["pregame_defense_context"].astype(str)=="LIMITED_SAMPLE")
            | pd.to_numeric(eligible["realized_outcome_delta"],errors="coerce").isna()
        ).sum()
    )

receipt={
    "generated_at":NOW.isoformat(),
    "walkforward_rows":int(len(history)),
    "eligible_rows":int(len(eligible)),
    "rows_by_sport":(
        history["sport"].value_counts().astype(int).to_dict()
        if not history.empty else {}
    ),
    "rows_by_family":(
        history["interaction_family"].value_counts().astype(int).to_dict()
        if not history.empty else {}
    ),
    "eligible_by_sport":(
        eligible["sport"].value_counts().astype(int).to_dict()
        if not eligible.empty else {}
    ),
    "role_reconstruction_counts":(
        history["role_reconstruction"].value_counts().astype(int).to_dict()
        if not history.empty else {}
    ),
    "factor_summary_rows":int(len(summary)),
    "combination_summary_rows":int(len(combo)),
    "defense_contrast_rows":int(len(contrast)),
    "identity_duplicates":identity_duplicates,
    "eligible_guard_failures":eligible_guard_failures,
    "source_status":{row["lane"]:row["status"] for row in source_rows},
    "errors":errors,
    "leakage_guards":[
        "Historical features are computed before the current event is appended to player or opponent histories.",
        "NBA and NHL simultaneous start-time batches are scored before any game in that batch updates history.",
        "NFL features are computed from prior weeks only; the current week is updated only after all games are scored.",
        "MLB role features use only prior same-season games, with a rolling 14-day recent window evaluated before each game.",
        "Defense pressure thresholds are recomputed from only previously observed team profiles at each historical point.",
        "Calibration eligibility requires at least two prior player games and a mature opponent context.",
    ],
    "explicit_gaps":[
        "NFL offensive historical role uses the corrected snap-aware live formula when prior snap history is available; rows without sufficient snap matching are explicitly labeled PARTIAL_SNAP_HISTORY_FALLBACK.",
        "MLB role calibration is now modeled from governed player-game history; opponent-pitching interaction calibration remains intentionally unmodeled.",
        "CBB player-level calibration is unavailable until a governed CBB player-role history exists.",
        "CFB player-level calibration is unavailable until governed player-role and current defensive histories exist.",
        "Calibration results are descriptive historical evidence only and do not alter model weights automatically.",
    ],
    "score_is_probability":False,
    "automatic_model_adjustment":False,
    "paid_provider_required":False,
}
RECEIPT_OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True))

print("WALKFORWARD ROWS:",len(history))
print("ELIGIBLE:",len(eligible))
print("BY SPORT:",receipt["rows_by_sport"])
print("BY FAMILY:",receipt["rows_by_family"])
print("ELIGIBLE BY SPORT:",receipt["eligible_by_sport"])
print("FACTOR SUMMARY:",len(summary))
print("COMBO SUMMARY:",len(combo))
print("DEFENSE CONTRASTS:",len(contrast))
print("IDENTITY DUPLICATES:",identity_duplicates)
print("GUARD FAILURES:",eligible_guard_failures)
print("ERRORS:",len(errors))
print("RESULT: SIGNAL_CALIBRATION_READY")
