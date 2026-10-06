#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re
import time

import pandas as pd
import requests

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "intelligence_warehouse" / "defensive_pressure"
RAW = OUT / "raw"
OUT.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

PROFILE_OUT = OUT / "OPPONENT_DEFENSIVE_PRESSURE_CURRENT.csv"
PLAYER_OUT = OUT / "PLAYER_DEFENSIVE_MATCHUP_CURRENT.csv"
SOURCE_OUT = OUT / "OPPONENT_DEFENSIVE_SOURCE_CATALOG.csv"
FEATURE_OUT = OUT / "OPPONENT_DEFENSIVE_FEATURE_CATALOG.csv"
RECEIPT_OUT = OUT / "OPPONENT_DEFENSIVE_RECEIPT.json"

NOW = datetime.now(timezone.utc)
HEADERS = {"User-Agent":"Sports-HULK/1.0 defensive-pressure"}
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
        return float(value)
    except Exception:
        return None

def read_csv(path):
    try:
        return pd.read_csv(path, low_memory=False) if Path(path).exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def cache_json(url, name, ttl_minutes=60):
    path = RAW / name
    if path.exists():
        age = (time.time() - path.stat().st_mtime) / 60.0
        if age <= ttl_minutes:
            try:
                return json.loads(path.read_text()), "CACHE"
            except Exception:
                pass
    response = requests.get(url, headers=HEADERS, timeout=12)
    response.raise_for_status()
    payload = response.json()
    path.write_text(json.dumps(payload, separators=(",",":")))
    return payload, "LIVE"

def pressure_label(value, low, high):
    value = num(value)
    if value is None:
        return "LIMITED_SAMPLE"
    if value <= low:
        return "SUPPRESSIVE"
    if value >= high:
        return "PERMISSIVE"
    return "NEUTRAL"
NFL_FULL_TO_ABBR = {
    "Arizona Cardinals":"ARI","Atlanta Falcons":"ATL","Baltimore Ravens":"BAL",
    "Buffalo Bills":"BUF","Carolina Panthers":"CAR","Chicago Bears":"CHI",
    "Cincinnati Bengals":"CIN","Cleveland Browns":"CLE","Dallas Cowboys":"DAL",
    "Denver Broncos":"DEN","Detroit Lions":"DET","Green Bay Packers":"GB",
    "Houston Texans":"HOU","Indianapolis Colts":"IND","Jacksonville Jaguars":"JAX",
    "Kansas City Chiefs":"KC","Las Vegas Raiders":"LV","Los Angeles Chargers":"LAC",
    "Los Angeles Rams":"LA","Miami Dolphins":"MIA","Minnesota Vikings":"MIN",
    "New England Patriots":"NE","New Orleans Saints":"NO","New York Giants":"NYG",
    "New York Jets":"NYJ","Philadelphia Eagles":"PHI","Pittsburgh Steelers":"PIT",
    "San Francisco 49ers":"SF","Seattle Seahawks":"SEA","Tampa Bay Buccaneers":"TB",
    "Tennessee Titans":"TEN","Washington Commanders":"WAS",
}
NBA_ALIAS={"NOP":"NO","WAS":"WSH","NYK":"NY","UTA":"UTAH","GSW":"GS","SAS":"SA"}
NHL_ALIAS={"LAK":"LA","NJD":"NJ","SJS":"SJ","TBL":"TB","UTA":"UTAH"}

def team_key(sport, value):
    text=clean(value)
    if sport=="NFL":
        return NFL_FULL_TO_ABBR.get(text,text)
    if sport=="NBA":
        return NBA_ALIAS.get(text,text)
    if sport=="NHL":
        return NHL_ALIAS.get(text,text)
    return text

def combine_pressure(volume_signal, production_signal):
    if volume_signal=="SUPPRESSIVE" and production_signal=="SUPPRESSIVE":
        return "STRONG_SUPPRESSIVE_PROFILE"
    if volume_signal=="PERMISSIVE" and production_signal=="PERMISSIVE":
        return "STRONG_PERMISSIVE_PROFILE"
    if volume_signal=="SUPPRESSIVE" or production_signal=="SUPPRESSIVE":
        if volume_signal=="PERMISSIVE" or production_signal=="PERMISSIVE":
            return "MIXED_PRESSURE_PROFILE"
        return "SUPPRESSIVE_LEAN"
    if volume_signal=="PERMISSIVE" or production_signal=="PERMISSIVE":
        return "PERMISSIVE_LEAN"
    if "LIMITED_SAMPLE" in {volume_signal,production_signal}:
        return "LIMITED_SAMPLE"
    return "NEUTRAL_PRESSURE_PROFILE"
def build_nfl_profiles():
    path=ROOT/"nfl_live"/"player_context"/"raw"/"player_stats.parquet"
    if not path.exists():
        return [], {"status":"MISSING_PLAYER_STATS"}
    d=pd.read_parquet(path)
    d=d[(d["season"]==2026)&(d["season_type"].astype(str).str.upper()=="REG")].copy()
    if d.empty:
        return [], {"status":"NO_CURRENT_ROWS"}
    def pos_group(value):
        p=clean(value).upper()
        if p=="QB": return "QB"
        if p in {"RB","FB"}: return "RB"
        if p=="WR": return "WR"
        if p=="TE": return "TE"
        return "OTHER"
    d["position_group"]=d["position"].map(pos_group)
    d=d[d["position_group"]!="OTHER"].copy()
    numeric=[
        "attempts","passing_yards","passing_tds","passing_epa","targets","carries",
        "receptions","receiving_yards","rushing_yards","receiving_tds","rushing_tds",
    ]
    for c in numeric:
        d[c]=pd.to_numeric(d[c],errors="coerce").fillna(0)
    d["touches_targets"]=d["carries"]+d["targets"]
    d["scrimmage_yards"]=d["rushing_yards"]+d["receiving_yards"]

    per_game=d.groupby(
        ["opponent_team","game_id","position_group"],as_index=False
    ).agg(
        attempts=("attempts","sum"),
        passing_yards=("passing_yards","sum"),
        passing_tds=("passing_tds","sum"),
        passing_epa=("passing_epa","sum"),
        targets=("targets","sum"),
        carries=("carries","sum"),
        receptions=("receptions","sum"),
        receiving_yards=("receiving_yards","sum"),
        rushing_yards=("rushing_yards","sum"),
        receiving_tds=("receiving_tds","sum"),
        rushing_tds=("rushing_tds","sum"),
        touches_targets=("touches_targets","sum"),
        scrimmage_yards=("scrimmage_yards","sum"),
    )
    base=per_game.groupby(
        ["opponent_team","position_group"],as_index=False
    ).agg(
        games=("game_id","nunique"),
        attempts_allowed=("attempts","mean"),
        passing_yards_allowed=("passing_yards","mean"),
        passing_tds_allowed=("passing_tds","mean"),
        passing_epa_allowed=("passing_epa","mean"),
        targets_allowed=("targets","mean"),
        carries_allowed=("carries","mean"),
        receptions_allowed=("receptions","mean"),
        receiving_yards_allowed=("receiving_yards","mean"),
        rushing_yards_allowed=("rushing_yards","mean"),
        receiving_tds_allowed=("receiving_tds","mean"),
        rushing_tds_allowed=("rushing_tds","mean"),
        opportunities_allowed=("touches_targets","mean"),
        scrimmage_yards_allowed=("scrimmage_yards","mean"),
    )

    primary={
        "QB":("attempts_allowed","passing_yards_allowed"),
        "RB":("opportunities_allowed","scrimmage_yards_allowed"),
        "WR":("targets_allowed","receiving_yards_allowed"),
        "TE":("targets_allowed","receiving_yards_allowed"),
    }
    rows=[]
    for pos,(volume_col,prod_col) in primary.items():
        x=base[base["position_group"]==pos].copy()
        v=pd.to_numeric(x[volume_col],errors="coerce")
        pvals=pd.to_numeric(x[prod_col],errors="coerce")
        v25,v75=v.quantile(.25),v.quantile(.75)
        p25,p75=pvals.quantile(.25),pvals.quantile(.75)
        for r in x.to_dict("records"):
            vol=pressure_label(r.get(volume_col),v25,v75)
            prod=pressure_label(r.get(prod_col),p25,p75)
            rows.append({
                "sport":"NFL","event_id":"","defense_team":clean(r.get("opponent_team")),
                "position_group":pos,"sample_stage":"CURRENT_SEASON_2026",
                "games":int(r.get("games") or 0),
                "volume_metric_name":volume_col,
                "volume_metric_value":num(r.get(volume_col)),
                "production_metric_name":prod_col,
                "production_metric_value":num(r.get(prod_col)),
                "volume_pressure_signal":vol,
                "production_pressure_signal":prod,
                "defensive_pressure_context":combine_pressure(vol,prod),
                "attempts_allowed":num(r.get("attempts_allowed")),
                "passing_yards_allowed":num(r.get("passing_yards_allowed")),
                "passing_tds_allowed":num(r.get("passing_tds_allowed")),
                "passing_epa_allowed":num(r.get("passing_epa_allowed")),
                "targets_allowed":num(r.get("targets_allowed")),
                "carries_allowed":num(r.get("carries_allowed")),
                "receptions_allowed":num(r.get("receptions_allowed")),
                "receiving_yards_allowed":num(r.get("receiving_yards_allowed")),
                "rushing_yards_allowed":num(r.get("rushing_yards_allowed")),
                "opportunities_allowed":num(r.get("opportunities_allowed")),
                "scrimmage_yards_allowed":num(r.get("scrimmage_yards_allowed")),
                "source":"NFLVERSE_PLAYER_STATS_2026",
                "source_tier":"CURRENT_STRUCTURED_PLAYER_STATS",
            })
    return rows, {"status":"CURRENT_SEASON_LIVE","rows":len(rows)}
def current_team_set(sport):
    style=read_csv(ROOT/"intelligence_warehouse"/"team_style"/"TEAM_STYLE_CURRENT.csv")
    x=style[style["sport"].astype(str)==sport].copy()
    return {team_key(sport,v) for v in x["team"].dropna().astype(str)}

def build_nba_profiles():
    path=ROOT/"nba_live"/"history"/"NBA_PLAYER_GAME_HISTORY.csv"
    d=read_csv(path)
    if d.empty:
        return [], {"status":"MISSING_HISTORY"}
    d=d[(d["season"]==2026)&(d["season_type"]==2)].copy()
    d["minutes"]=pd.to_numeric(d["minutes"],errors="coerce")
    d=d[(d["minutes"]>0)&(~d["did_not_play"].astype(bool))].copy()
    def pos_group(value):
        p=clean(value).upper()
        if p in {"G","PG","SG"}: return "G"
        if p in {"F","SF","PF"}: return "F"
        if p=="C": return "C"
        return "OTHER"
    d["position_group"]=d["position"].map(pos_group)
    d=d[d["position_group"]!="OTHER"].copy()
    teams=current_team_set("NBA")
    d["defense_team"]=d["opponent"].map(lambda v: team_key("NBA",v))
    d=d[d["defense_team"].isin(teams)].copy()
    numeric=["points","rebounds","assists","pra","three_made","fg_attempts","turnovers"]
    for c in numeric:
        d[c]=pd.to_numeric(d[c],errors="coerce").fillna(0)
    per_game=d.groupby(
        ["defense_team","event_id","position_group"],as_index=False
    ).agg(
        points_allowed=("points","sum"),
        rebounds_allowed=("rebounds","sum"),
        assists_allowed=("assists","sum"),
        pra_allowed=("pra","sum"),
        three_made_allowed=("three_made","sum"),
        fg_attempts_allowed=("fg_attempts","sum"),
        turnovers_forced=("turnovers","sum"),
        players_used=("player_id","nunique"),
    )
    base=per_game.groupby(
        ["defense_team","position_group"],as_index=False
    ).agg(
        games=("event_id","nunique"),
        points_allowed=("points_allowed","mean"),
        rebounds_allowed=("rebounds_allowed","mean"),
        assists_allowed=("assists_allowed","mean"),
        pra_allowed=("pra_allowed","mean"),
        three_made_allowed=("three_made_allowed","mean"),
        fg_attempts_allowed=("fg_attempts_allowed","mean"),
        turnovers_forced=("turnovers_forced","mean"),
        players_used=("players_used","mean"),
    )
    rows=[]
    for pos in ["G","F","C"]:
        x=base[base["position_group"]==pos].copy()
        volume_col="fg_attempts_allowed"
        prod_col="pra_allowed"
        v=pd.to_numeric(x[volume_col],errors="coerce")
        pvals=pd.to_numeric(x[prod_col],errors="coerce")
        v25,v75=v.quantile(.25),v.quantile(.75)
        p25,p75=pvals.quantile(.25),pvals.quantile(.75)
        for r in x.to_dict("records"):
            vol=pressure_label(r.get(volume_col),v25,v75)
            prod=pressure_label(r.get(prod_col),p25,p75)
            rows.append({
                "sport":"NBA","event_id":"","defense_team":clean(r.get("defense_team")),
                "position_group":pos,"sample_stage":"PRIOR_REGULAR_SEASON_2025_26",
                "games":int(r.get("games") or 0),
                "volume_metric_name":volume_col,
                "volume_metric_value":num(r.get(volume_col)),
                "production_metric_name":prod_col,
                "production_metric_value":num(r.get(prod_col)),
                "volume_pressure_signal":vol,
                "production_pressure_signal":prod,
                "defensive_pressure_context":combine_pressure(vol,prod),
                "points_allowed":num(r.get("points_allowed")),
                "rebounds_allowed":num(r.get("rebounds_allowed")),
                "assists_allowed":num(r.get("assists_allowed")),
                "pra_allowed":num(r.get("pra_allowed")),
                "three_made_allowed":num(r.get("three_made_allowed")),
                "fg_attempts_allowed":num(r.get("fg_attempts_allowed")),
                "turnovers_forced":num(r.get("turnovers_forced")),
                "players_used":num(r.get("players_used")),
                "source":"NBA_PLAYER_GAME_HISTORY",
                "source_tier":"PRIOR_REGULAR_SEASON_PLAYER_GAME_HISTORY",
            })
    return rows, {"status":"PRIOR_SEASON_BASELINE","rows":len(rows)}
def build_nhl_profiles():
    path=ROOT/"nhl_live"/"history"/"NHL_PLAYER_GAME_HISTORY.csv"
    d=read_csv(path)
    if d.empty:
        return [], {"status":"MISSING_HISTORY"}
    d=d[(d["season"]==20252026)&(d["game_type"]==2)].copy()
    d["toi_minutes"]=pd.to_numeric(d["toi_minutes"],errors="coerce")
    d=d[d["toi_minutes"]>0].copy()
    def pos_group(value):
        p=clean(value).upper()
        if p=="D": return "D"
        if p=="C": return "C"
        if p in {"L","R"}: return "W"
        return "OTHER"
    d["position_group"]=d["position"].map(pos_group)
    d=d[d["position_group"]!="OTHER"].copy()
    teams=current_team_set("NHL")
    d["defense_team"]=d["opponent"].map(lambda v: team_key("NHL",v))
    d=d[d["defense_team"].isin(teams)].copy()
    numeric=["points","shots_on_goal","hits","blocked_shots","goals","assists"]
    for c in numeric:
        d[c]=pd.to_numeric(d[c],errors="coerce").fillna(0)
    per_game=d.groupby(
        ["defense_team","event_id","position_group"],as_index=False
    ).agg(
        points_allowed=("points","sum"),
        shots_allowed=("shots_on_goal","sum"),
        hits_allowed=("hits","sum"),
        blocks_allowed=("blocked_shots","sum"),
        goals_allowed=("goals","sum"),
        assists_allowed=("assists","sum"),
        players_used=("player_id","nunique"),
    )
    base=per_game.groupby(
        ["defense_team","position_group"],as_index=False
    ).agg(
        games=("event_id","nunique"),
        points_allowed=("points_allowed","mean"),
        shots_allowed=("shots_allowed","mean"),
        hits_allowed=("hits_allowed","mean"),
        blocks_allowed=("blocks_allowed","mean"),
        goals_allowed=("goals_allowed","mean"),
        assists_allowed=("assists_allowed","mean"),
        players_used=("players_used","mean"),
    )
    rows=[]
    for pos in ["C","W","D"]:
        x=base[base["position_group"]==pos].copy()
        volume_col="shots_allowed"
        prod_col="points_allowed"
        v=pd.to_numeric(x[volume_col],errors="coerce")
        pvals=pd.to_numeric(x[prod_col],errors="coerce")
        v25,v75=v.quantile(.25),v.quantile(.75)
        p25,p75=pvals.quantile(.25),pvals.quantile(.75)
        for r in x.to_dict("records"):
            vol=pressure_label(r.get(volume_col),v25,v75)
            prod=pressure_label(r.get(prod_col),p25,p75)
            rows.append({
                "sport":"NHL","event_id":"","defense_team":clean(r.get("defense_team")),
                "position_group":pos,"sample_stage":"PRIOR_REGULAR_SEASON_2025_26",
                "games":int(r.get("games") or 0),
                "volume_metric_name":volume_col,
                "volume_metric_value":num(r.get(volume_col)),
                "production_metric_name":prod_col,
                "production_metric_value":num(r.get(prod_col)),
                "volume_pressure_signal":vol,
                "production_pressure_signal":prod,
                "defensive_pressure_context":combine_pressure(vol,prod),
                "points_allowed":num(r.get("points_allowed")),
                "shots_allowed":num(r.get("shots_allowed")),
                "hits_allowed":num(r.get("hits_allowed")),
                "blocks_allowed":num(r.get("blocks_allowed")),
                "goals_allowed":num(r.get("goals_allowed")),
                "assists_allowed":num(r.get("assists_allowed")),
                "players_used":num(r.get("players_used")),
                "source":"NHL_PLAYER_GAME_HISTORY",
                "source_tier":"PRIOR_REGULAR_SEASON_PLAYER_GAME_HISTORY",
            })
    return rows, {"status":"PRIOR_SEASON_BASELINE","rows":len(rows)}
def inverse_pressure_label(value, low, high):
    value=num(value)
    if value is None:
        return "LIMITED_SAMPLE"
    if value >= high:
        return "SUPPRESSIVE"
    if value <= low:
        return "PERMISSIVE"
    return "NEUTRAL"

def fetch_mlb_team_pitching():
    style=read_csv(ROOT/"intelligence_warehouse"/"team_style"/"TEAM_STYLE_CURRENT.csv")
    teams=style[style["sport"].astype(str)=="MLB"][["team_id","team_name"]].drop_duplicates()
    specs=[]
    meta={}
    for r in teams.itertuples():
        tid=clean(r.team_id)
        meta[tid]=clean(r.team_name)
        specs.append((
            tid,
            f"https://statsapi.mlb.com/api/v1/teams/{tid}/stats?stats=season&group=pitching&season=2026",
            f"mlb_{tid}_2026_pitching.json",
        ))
    out={}
    errors=[]
    modes=[]
    def one(spec):
        tid,url,name=spec
        payload,mode=cache_json(url,name,60)
        return tid,payload,mode
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures={pool.submit(one,s):s[0] for s in specs}
        for future in as_completed(futures):
            tid=futures[future]
            try:
                key,payload,mode=future.result()
                stat={}
                for block in payload.get("stats") or []:
                    splits=block.get("splits") or []
                    if splits:
                        stat=(splits[0].get("stat") or {})
                        break
                out[key]={"team":meta.get(key,key),"stat":stat}
                modes.append(mode)
            except Exception as exc:
                errors.append({"team_id":tid,"error":repr(exc)})
    return out, errors, modes
def build_mlb_profiles():
    team_stats,errors,modes=fetch_mlb_team_pitching()
    if not team_stats:
        return [], {"status":"NO_TEAM_PITCHING","errors":errors}

    season_rows=[]
    for tid,item in team_stats.items():
        s=item.get("stat") or {}
        season_rows.append({
            "team_id":tid,
            "defense_team":clean(item.get("team")),
            "games":num(s.get("gamesPlayed")),
            "era":num(s.get("era")),
            "whip":num(s.get("whip")),
            "ops_allowed":num(s.get("ops")),
            "k9":num(s.get("strikeoutsPer9Inn")),
            "bb9":num(s.get("walksPer9Inn")),
            "h9":num(s.get("hitsPer9Inn")),
            "hr9":num(s.get("homeRunsPer9")),
            "runs9":num(s.get("runsScoredPer9")),
        })
    season=pd.DataFrame(season_rows)
    whip25,whip75=season["whip"].quantile(.25),season["whip"].quantile(.75)
    ops25,ops75=season["ops_allowed"].quantile(.25),season["ops_allowed"].quantile(.75)
    k25,k75=season["k9"].quantile(.25),season["k9"].quantile(.75)

    pitcher_ctx=read_csv(ROOT/"mlb_live"/"derived"/"MLB_PLAYER_CONTEXT.csv")
    pitcher_ctx=pitcher_ctx[pitcher_ctx["group"].astype(str).str.upper()=="PITCHING"].copy()
    pitcher_by_id={}
    for r in pitcher_ctx.to_dict("records"):
        pid=clean(r.get("player_id"))
        if pid.endswith(".0"):
            pid=pid[:-2]
        if pid:
            pitcher_by_id[pid]=r

    schedule=read_csv(ROOT/"baseball_vault"/"latest"/"MLB_SCHEDULE.csv")
    schedule=schedule[schedule["abstractState"].astype(str).str.lower()=="preview"].copy()

    bullpen=read_csv(ROOT/"baseball_vault"/"latest"/"MLB_BULLPEN_WORKLOAD.csv")
    bullpen_team={}
    if not bullpen.empty:
        b=(
            bullpen.groupby("team",as_index=False)
            .agg(
                bullpen_relief_arms=("pitcher_id","nunique"),
                bullpen_avg_workload=("HULK_bullpen_workload_score","mean"),
                bullpen_max_workload=("HULK_bullpen_workload_score","max"),
                bullpen_pitches_last3=("pitches_last3","sum"),
                bullpen_last_used=("last_used","max"),
            )
        )
        bullpen_team={clean(r["team"]):r for r in b.to_dict("records")}
    starter_metrics=[]
    for r in schedule.itertuples(index=False):
        for side in ["away","home"]:
            pid=clean(getattr(r,f"{side}_probable_pitcher_id"))
            if pid.endswith(".0"):
                pid=pid[:-2]
            if not pid:
                continue
            ctx=pitcher_by_id.get(pid)
            if not ctx:
                continue
            outs=num(ctx.get("season_outs_pg"))
            er=num(ctx.get("season_earned_runs_pg"))
            hits=num(ctx.get("season_hits_allowed_pg"))
            walks=num(ctx.get("season_walks_allowed_pg"))
            ks=num(ctx.get("season_strikeouts_pg"))
            starter_metrics.append({
                "event_id":clean(r.gamePk),"pitcher_id":pid,
                "pitcher":clean(getattr(r,f"{side}_probable_pitcher")),
                "defense_team":clean(getattr(r,f"{side}_team")),
                "era_proxy":(er*27/outs) if outs and er is not None else None,
                "whip_proxy":((hits+walks)*3/outs) if outs and hits is not None and walks is not None else None,
                "k9_proxy":(ks*27/outs) if outs and ks is not None else None,
                "season_games_started":num(ctx.get("season_games_started")),
                "recent_games":num(ctx.get("recent_games")),
            })
    starter_df=pd.DataFrame(starter_metrics)
    if not starter_df.empty:
        se25,se75=starter_df["era_proxy"].quantile(.25),starter_df["era_proxy"].quantile(.75)
        sw25,sw75=starter_df["whip_proxy"].quantile(.25),starter_df["whip_proxy"].quantile(.75)
        sk25,sk75=starter_df["k9_proxy"].quantile(.25),starter_df["k9_proxy"].quantile(.75)
    else:
        se25=se75=sw25=sw75=sk25=sk75=None

    season_map={clean(r["defense_team"]):r for r in season.to_dict("records")}
    starter_map={(clean(r["event_id"]),clean(r["defense_team"])):r for r in starter_metrics}
    rows=[]
    for g in schedule.to_dict("records"):
        event_id=clean(g.get("gamePk"))
        for side in ["away","home"]:
            defense_team=clean(g.get(f"{side}_team"))
            s=season_map.get(defense_team,{})
            vol=pressure_label(s.get("whip"),whip25,whip75)
            prod=pressure_label(s.get("ops_allowed"),ops25,ops75)
            team_context=combine_pressure(vol,prod)
            k_signal=inverse_pressure_label(s.get("k9"),k25,k75)
            starter=starter_map.get((event_id,defense_team),{})
            starter_era_signal=(
                pressure_label(starter.get("era_proxy"),se25,se75)
                if se25 is not None else "LIMITED_SAMPLE"
            )
            starter_whip_signal=(
                pressure_label(starter.get("whip_proxy"),sw25,sw75)
                if sw25 is not None else "LIMITED_SAMPLE"
            )
            starter_k_signal=(
                inverse_pressure_label(starter.get("k9_proxy"),sk25,sk75)
                if sk25 is not None else "LIMITED_SAMPLE"
            )
            starter_context=combine_pressure(starter_whip_signal,starter_era_signal)
            bp=bullpen_team.get(defense_team,{})
            workload=num(bp.get("bullpen_avg_workload"))
            if workload is None:
                bullpen_signal="NO_RECENT_BULLPEN_USAGE_ROWS"
            elif workload>=35:
                bullpen_signal="HEAVY_RECENT_BULLPEN_WORKLOAD"
            elif workload<=18:
                bullpen_signal="LIGHT_RECENT_BULLPEN_WORKLOAD"
            else:
                bullpen_signal="MODERATE_RECENT_BULLPEN_WORKLOAD"
            rows.append({
                "sport":"MLB",
                "event_id":event_id,
                "defense_team":defense_team,
                "position_group":"BATTER",
                "sample_stage":"CURRENT_2026_TEAM_PITCHING_PLUS_GAME_STARTER",
                "games":int(s.get("games") or 0),
                "volume_metric_name":"whip",
                "volume_metric_value":num(s.get("whip")),
                "production_metric_name":"ops_allowed",
                "production_metric_value":num(s.get("ops_allowed")),
                "volume_pressure_signal":vol,
                "production_pressure_signal":prod,
                "defensive_pressure_context":team_context,
                "team_strikeout_pressure_signal":k_signal,
                "team_era":num(s.get("era")),
                "team_whip":num(s.get("whip")),
                "team_ops_allowed":num(s.get("ops_allowed")),
                "team_k9":num(s.get("k9")),
                "team_bb9":num(s.get("bb9")),
                "team_h9":num(s.get("h9")),
                "team_hr9":num(s.get("hr9")),
                "team_runs9":num(s.get("runs9")),
                "probable_starter":clean(starter.get("pitcher")),
                "probable_starter_id":clean(starter.get("pitcher_id")),
                "starter_era_proxy":num(starter.get("era_proxy")),
                "starter_whip_proxy":num(starter.get("whip_proxy")),
                "starter_k9_proxy":num(starter.get("k9_proxy")),
                "starter_run_pressure_signal":starter_context,
                "starter_strikeout_pressure_signal":starter_k_signal,
                "starter_season_games_started":num(starter.get("season_games_started")),
                "bullpen_workload_signal":bullpen_signal,
                "bullpen_relief_arms":num(bp.get("bullpen_relief_arms")),
                "bullpen_avg_workload":workload,
                "bullpen_max_workload":num(bp.get("bullpen_max_workload")),
                "bullpen_pitches_last3":num(bp.get("bullpen_pitches_last3")),
                "bullpen_last_used":clean(bp.get("bullpen_last_used")),
                "source":"MLB_STATSAPI_TEAM_PITCHING + MLB_PLAYER_CONTEXT + MLB_BULLPEN_WORKLOAD",
                "source_tier":"OFFICIAL_CURRENT_TEAM_STATS_PLUS_INTERNAL_CURRENT_CONTEXT",
            })
    return rows, {
        "status":"CURRENT_SEASON_LIVE",
        "rows":len(rows),
        "errors":errors,
        "live_fetches":modes.count("LIVE"),
        "cache_hits":modes.count("CACHE"),
        "starter_profiles":len(starter_metrics),
    }
def build_cbb_profiles():
    d=read_csv(
        ROOT/"intelligence_warehouse"/"cbb_efficiency"/"CBB_EFFICIENCY_CURRENT.csv"
    )
    if d.empty:
        return [], {"status":"MISSING_CBB_EFFICIENCY"}
    vals=pd.to_numeric(d["prior_def_rating"],errors="coerce")
    q25,q75=vals.quantile(.25),vals.quantile(.75)
    rows=[]
    for r in d.to_dict("records"):
        signal=pressure_label(r.get("prior_def_rating"),q25,q75)
        rows.append({
            "sport":"CBB","event_id":"","defense_team":clean(r.get("team")),
            "defense_team_id":clean(r.get("team_id")),
            "defense_team_name":clean(r.get("team_name")),
            "position_group":"TEAM","sample_stage":"PRESEASON_PRIOR_DEFENSIVE_EFFICIENCY",
            "games":int(num(r.get("prior_games")) or 0),
            "volume_metric_name":"",
            "volume_metric_value":None,
            "production_metric_name":"prior_def_rating",
            "production_metric_value":num(r.get("prior_def_rating")),
            "volume_pressure_signal":"NOT_MODELED",
            "production_pressure_signal":signal,
            "defensive_pressure_context":(
                "SUPPRESSIVE_TEAM_DEFENSE" if signal=="SUPPRESSIVE"
                else "PERMISSIVE_TEAM_DEFENSE" if signal=="PERMISSIVE"
                else "NEUTRAL_TEAM_DEFENSE" if signal=="NEUTRAL"
                else "LIMITED_SAMPLE"
            ),
            "prior_def_rating":num(r.get("prior_def_rating")),
            "prior_off_rating":num(r.get("prior_off_rating")),
            "prior_net_rating":num(r.get("prior_net_rating")),
            "source":"HULK_CBB_EFFICIENCY_BASELINE",
            "source_tier":"DERIVED_PRIOR_SEASON_EFFICIENCY",
        })
    return rows, {"status":"PRESEASON_BASELINE","rows":len(rows)}
builders=[
    ("NFL",build_nfl_profiles),
    ("NBA",build_nba_profiles),
    ("NHL",build_nhl_profiles),
    ("MLB",build_mlb_profiles),
    ("CBB",build_cbb_profiles),
]
profile_rows=[]
source_rows=[]
errors=[]
for sport,builder in builders:
    try:
        rows,meta=builder()
        profile_rows.extend(rows)
        source_rows.append({
            "sport":sport,
            "status":meta.get("status","UNKNOWN"),
            "profile_rows":int(meta.get("rows",len(rows))),
            "live_fetches":int(meta.get("live_fetches",0)),
            "cache_hits":int(meta.get("cache_hits",0)),
            "starter_profiles":int(meta.get("starter_profiles",0)),
            "error_count":len(meta.get("errors",[])),
            "generated_at":NOW.isoformat(),
        })
        errors.extend([{"sport":sport,**e} for e in meta.get("errors",[])])
    except Exception as exc:
        errors.append({"sport":sport,"error":repr(exc)})
        source_rows.append({
            "sport":sport,"status":"ERROR","profile_rows":0,
            "live_fetches":0,"cache_hits":0,"starter_profiles":0,
            "error_count":1,"generated_at":NOW.isoformat(),
        })

source_rows.append({
    "sport":"CFB","status":"CURRENT_DEFENSE_HISTORY_NOT_TRUSTWORTHY",
    "profile_rows":0,"live_fetches":0,"cache_hits":0,"starter_profiles":0,
    "error_count":0,"generated_at":NOW.isoformat(),
})

profiles=pd.DataFrame(profile_rows)
if "defense_team_id" not in profiles.columns:
    profiles["defense_team_id"]=""
if "defense_team_name" not in profiles.columns:
    profiles["defense_team_name"]=""
profiles["defense_profile_identity_key"]=profiles.apply(
    lambda r: "|".join([
        clean(r.get("sport")),
        clean(r.get("event_id")),
        clean(r.get("defense_team_id")) or norm(r.get("defense_team")),
        clean(r.get("position_group")),
    ]),
    axis=1,
)
profiles["generated_at"]=NOW.isoformat()
profiles["automatic_model_adjustment"]=False
profiles["score_is_probability"]=False
static_lookup={}
mlb_event_lookup={}
for r in profiles.to_dict("records"):
    sport=clean(r.get("sport"))
    defense=team_key(sport,r.get("defense_team"))
    pos=clean(r.get("position_group"))
    event=clean(r.get("event_id"))
    if sport=="MLB" and event:
        mlb_event_lookup[(event,norm(defense),pos)]=r
    else:
        static_lookup[(sport,norm(defense),pos)]=r

def player_position_group(sport, position):
    p=clean(position).upper()
    if sport=="NFL":
        if p=="QB": return "QB"
        if p in {"RB","FB"}: return "RB"
        if p=="WR": return "WR"
        if p=="TE": return "TE"
        return "NOT_APPLICABLE_IDP"
    if sport=="NBA":
        if p in {"G","PG","SG"}: return "G"
        if p in {"F","SF","PF"}: return "F"
        if p=="C": return "C"
        return "UNMAPPED_POSITION"
    if sport=="NHL":
        if p=="D": return "D"
        if p=="C": return "C"
        if p in {"L","R","LW","RW"}: return "W"
        return "UNMAPPED_POSITION"
    if sport=="MLB":
        return "NOT_APPLICABLE_PITCHER" if p=="P" else "BATTER"
    return "NOT_MODELED"

player_base=read_csv(
    ROOT/"intelligence_warehouse"/"player_opportunity"/"PLAYER_OPPORTUNITY_CONTEXT_CURRENT.csv"
)
player_rows=[]
for p in player_base.to_dict("records"):
    sport=clean(p.get("sport")).upper()
    invalid_identity=(
        not clean(p.get("player_key"))
        or not clean(p.get("player"))
        or not clean(p.get("position"))
    )
    pos_group=(
        "INVALID_PLAYER_IDENTITY"
        if invalid_identity
        else player_position_group(sport,p.get("position"))
    )
    opponent=team_key(sport,p.get("opponent"))
    event=clean(p.get("event_id"))
    if event.endswith(".0"):
        event=event[:-2]

    if clean(p.get("matchup_coverage_status"))=="NO_UPCOMING_MODELED_GAME":
        profile=None
        join_status="NO_UPCOMING_MODELED_GAME"
    elif pos_group.startswith("NOT_APPLICABLE"):
        profile=None
        join_status=pos_group
    elif pos_group in {"UNMAPPED_POSITION","NOT_MODELED","INVALID_PLAYER_IDENTITY"}:
        profile=None
        join_status=pos_group
    elif sport=="MLB":
        profile=mlb_event_lookup.get((event,norm(opponent),pos_group))
        join_status="MATCHED_EVENT_DEFENSE_PROFILE" if profile else "DEFENSE_PROFILE_MISSING"
    else:
        profile=static_lookup.get((sport,norm(opponent),pos_group))
        join_status="MATCHED_DEFENSE_POSITION_PROFILE" if profile else "DEFENSE_PROFILE_MISSING"
    out={
        "sport":sport,
        "opportunity_identity_key":clean(p.get("opportunity_identity_key")),
        "player_key":clean(p.get("player_key")),
        "player":clean(p.get("player")),
        "team":clean(p.get("team")),
        "position":clean(p.get("position")),
        "event_id":event,
        "start":clean(p.get("start")),
        "opponent":clean(p.get("opponent")),
        "role_signal":clean(p.get("role_signal")),
        "opportunity_context":clean(p.get("opportunity_context")),
        "availability_context":clean(p.get("availability_context")),
        "defense_position_group":pos_group,
        "defense_join_status":join_status,
        "opponent_defense_team":clean(profile.get("defense_team")) if profile else opponent,
        "defense_sample_stage":clean(profile.get("sample_stage")) if profile else "",
        "defense_games":num(profile.get("games")) if profile else None,
        "volume_pressure_signal":clean(profile.get("volume_pressure_signal")) if profile else "NOT_AVAILABLE",
        "production_pressure_signal":clean(profile.get("production_pressure_signal")) if profile else "NOT_AVAILABLE",
        "defensive_pressure_context":clean(profile.get("defensive_pressure_context")) if profile else join_status,
        "volume_metric_name":clean(profile.get("volume_metric_name")) if profile else "",
        "volume_metric_value":num(profile.get("volume_metric_value")) if profile else None,
        "production_metric_name":clean(profile.get("production_metric_name")) if profile else "",
        "production_metric_value":num(profile.get("production_metric_value")) if profile else None,
    }
    if profile:
        extra=[
            "attempts_allowed","passing_yards_allowed","passing_tds_allowed","passing_epa_allowed",
            "targets_allowed","carries_allowed","receptions_allowed","receiving_yards_allowed",
            "rushing_yards_allowed","opportunities_allowed","scrimmage_yards_allowed",
            "points_allowed","rebounds_allowed","assists_allowed","pra_allowed","three_made_allowed",
            "fg_attempts_allowed","turnovers_forced","shots_allowed","hits_allowed","blocks_allowed",
            "goals_allowed","team_strikeout_pressure_signal","team_era","team_whip",
            "team_ops_allowed","team_k9","team_bb9","team_h9","team_hr9","team_runs9",
            "probable_starter","probable_starter_id","starter_era_proxy","starter_whip_proxy",
            "starter_k9_proxy","starter_run_pressure_signal","starter_strikeout_pressure_signal",
            "starter_season_games_started","bullpen_workload_signal","bullpen_relief_arms",
            "bullpen_avg_workload","bullpen_max_workload","bullpen_pitches_last3","bullpen_last_used",
        ]
        for field in extra:
            out[field]=profile.get(field)
    out["generated_at"]=NOW.isoformat()
    out["automatic_model_adjustment"]=False
    out["score_is_probability"]=False
    player_rows.append(out)

player_matchups=pd.DataFrame(player_rows)
features=pd.DataFrame([
    {
        "sport_scope":"NFL",
        "feature":"defense_position_profile",
        "definition":"2026 opponent production allowed per game by QB/RB/WR/TE; volume and production pressure are classified separately.",
        "data_stage":"CURRENT_SEASON",
    },
    {
        "sport_scope":"NBA",
        "feature":"defense_position_profile",
        "definition":"2025-26 regular-season opponent production allowed per game by G/F/C; FGA allowed is volume and PRA allowed is production.",
        "data_stage":"PRIOR_REGULAR_SEASON_BASELINE",
    },
    {
        "sport_scope":"NHL",
        "feature":"defense_position_profile",
        "definition":"2025-26 regular-season opponent production allowed per game by C/W/D; shots allowed is volume and points allowed is production.",
        "data_stage":"PRIOR_REGULAR_SEASON_BASELINE",
    },
    {
        "sport_scope":"MLB",
        "feature":"team_pitching_pressure",
        "definition":"Official 2026 team pitching WHIP/OPS/K9 baseline for the defense team.",
        "data_stage":"CURRENT_SEASON",
    },
    {
        "sport_scope":"MLB",
        "feature":"probable_starter_pressure",
        "definition":"Upcoming-game probable starter ERA/WHIP/K9 proxies from current pitcher context; kept separate from team baseline.",
        "data_stage":"CURRENT_GAME",
    },
    {
        "sport_scope":"MLB",
        "feature":"bullpen_workload_signal",
        "definition":"Current recent-reliever workload overlay when workload rows exist; missing rows are not treated as fresh bullpen evidence.",
        "data_stage":"CURRENT_WORKLOAD",
    },
    {
        "sport_scope":"CBB",
        "feature":"team_defensive_efficiency",
        "definition":"Prior-season defensive rating baseline; team-level only because a governed CBB player-role store is not yet available.",
        "data_stage":"PRESEASON_BASELINE",
    },
])
features["score_is_probability"]=False
features["automatic_model_adjustment"]=False
sources=pd.DataFrame(source_rows)
profile_counts=profiles["sport"].value_counts().to_dict() if not profiles.empty else {}
player_join_counts={}
if not player_matchups.empty:
    for sport,frame in player_matchups.groupby("sport"):
        player_join_counts[sport]={
            "rows":len(frame),
            "matched":int(frame["defense_join_status"].astype(str).str.startswith("MATCHED").sum()),
            "no_upcoming":int((frame["defense_join_status"]=="NO_UPCOMING_MODELED_GAME").sum()),
            "not_applicable":int(frame["defense_join_status"].astype(str).str.startswith("NOT_APPLICABLE").sum()),
            "missing":int((frame["defense_join_status"]=="DEFENSE_PROFILE_MISSING").sum()),
            "unmapped":int((frame["defense_join_status"]=="UNMAPPED_POSITION").sum()),
            "invalid_identity":int((frame["defense_join_status"]=="INVALID_PLAYER_IDENTITY").sum()),
        }

profiles.to_csv(PROFILE_OUT,index=False)
player_matchups.to_csv(PLAYER_OUT,index=False)
sources.to_csv(SOURCE_OUT,index=False)
features.to_csv(FEATURE_OUT,index=False)

receipt={
    "generated_at":NOW.isoformat(),
    "profile_rows":len(profiles),
    "profile_rows_by_sport":{str(k):int(v) for k,v in profile_counts.items()},
    "player_matchup_rows":len(player_matchups),
    "player_join_counts":player_join_counts,
    "profile_identity_duplicates":int(profiles.duplicated(["defense_profile_identity_key"]).sum()),
    "player_identity_duplicates":int(player_matchups.duplicated(["sport","opportunity_identity_key"]).sum()),
    "source_status":{row["sport"]:row["status"] for row in source_rows},
    "errors":errors,
    "explicit_gaps":[
        "CFB defense pressure is not modeled because the local current defensive game history is not sufficiently current for a trustworthy layer.",
        "CBB defense pressure is team-level only; there is no governed CBB player-role/position-allowed store yet.",
        "NFL IDP rows are not assigned opponent defensive pressure because IDP opportunity is driven by opposing offense volume, already handled in player opportunity context.",
        "NBA and NHL position pressure use completed 2025-26 regular-season baselines until current-season samples mature.",
        "MLB pitcher rows are not assigned opponent defensive pressure; pitchers face opponent offense, which is handled in the player opportunity layer.",
        "MLB bullpen workload is an overlay only when current reliever workload rows exist; missing workload rows are not interpreted as a fresh bullpen.",
        "Pressure labels are descriptive league-relative allowed-production context, not projections, probabilities, recommendations, or automatic model weights.",
    ],
    "score_is_probability":False,
    "automatic_model_adjustment":False,
    "paid_provider_required":False,
}
RECEIPT_OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True))

print("DEFENSE PROFILES:",len(profiles))
print("BY SPORT:",receipt["profile_rows_by_sport"])
print("PLAYER MATCHUPS:",len(player_matchups))
print("JOINS:",receipt["player_join_counts"])
print("ERRORS:",len(errors))
print("RESULT: DEFENSIVE_PRESSURE_READY")
