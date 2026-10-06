#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import re
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
OUT=ROOT/"intelligence_warehouse"/"postgame_grading"
OUT.mkdir(parents=True,exist_ok=True)

COHORT_FILE=ROOT/"intelligence_warehouse"/"pregame_cohorts"/"PREGAME_RESEARCH_STATE_TIMELINE.csv"
NBA_PLAYER=ROOT/"nba_live"/"history"/"NBA_PLAYER_GAME_HISTORY.csv"
NBA_TEAM=ROOT/"nba_live"/"history"/"NBA_TEAM_GAME_HISTORY.csv"
NHL_PLAYER=ROOT/"nhl_live"/"history"/"NHL_PLAYER_GAME_HISTORY.csv"
NHL_TEAM=ROOT/"nhl_live"/"history"/"NHL_TEAM_GAME_HISTORY.csv"
NFL_STATS=ROOT/"nfl_live"/"player_context"/"raw"/"player_stats.parquet"
NFL_SNAPS=ROOT/"nfl_live"/"player_context"/"raw"/"snap_counts.parquet"
MLB_PLAYER=ROOT/"intelligence_warehouse"/"mlb_player_history"/"MLB_PLAYER_GAME_LEDGER.csv"

CURRENT_OUT=OUT/"POSTGAME_RESEARCH_GRADES_CURRENT.csv"
TIMELINE_OUT=OUT/"POSTGAME_RESEARCH_GRADE_TIMELINE.csv"
SUMMARY_OUT=OUT/"POSTGAME_RESEARCH_GRADE_SUMMARY.csv"
SOURCE_OUT=OUT/"POSTGAME_RESEARCH_SOURCE_CATALOG.csv"
FEATURE_OUT=OUT/"POSTGAME_RESEARCH_FEATURE_CATALOG.csv"
RECEIPT_OUT=OUT/"POSTGAME_RESEARCH_RECEIPT.json"
NOW=datetime.now(timezone.utc)

def clean(v):
    if v is None: return ""
    try:
        if pd.isna(v): return ""
    except Exception:
        pass
    s=str(v).strip()
    if s.endswith(".0") and s[:-2].isdigit(): return s[:-2]
    return s

def norm(v):
    return re.sub(r"[^a-z0-9]+","",clean(v).lower())

def num(v):
    try: return float(v)
    except Exception: return None

def outcome_direction(v):
    x=num(v)
    if x is None: return "UNKNOWN"
    if x>0: return "POSITIVE"
    if x<0: return "NEGATIVE"
    return "NEUTRAL"

def alignment(expected,actual):
    e=clean(expected); a=clean(actual)
    if e not in {"POSITIVE","NEGATIVE"}: return "NOT_DIRECTIONALLY_SCORED"
    if a=="UNKNOWN": return "UNKNOWN"
    return "ALIGNED" if e==a else "NOT_ALIGNED"

coh=pd.read_csv(COHORT_FILE,low_memory=False)
coh["observed_dt"]=pd.to_datetime(coh["observed_at"],errors="coerce",utc=True,format="mixed")
coh["start_dt"]=pd.to_datetime(coh["start"],errors="coerce",utc=True,format="mixed")
coh=coh[
    coh["observed_dt"].notna()
    & coh["start_dt"].notna()
    & (coh["observed_dt"]<coh["start_dt"])
].copy()
coh=(
    coh.sort_values(["cohort_identity_key","observed_dt"])
    .groupby("cohort_identity_key",as_index=False)
    .tail(1)
)
coh=coh[coh["grading_eligible"].fillna(False).astype(bool)].copy()

nba_p=pd.read_csv(NBA_PLAYER,low_memory=False) if NBA_PLAYER.exists() else pd.DataFrame()
nba_t=pd.read_csv(NBA_TEAM,low_memory=False) if NBA_TEAM.exists() else pd.DataFrame()
nhl_p=pd.read_csv(NHL_PLAYER,low_memory=False) if NHL_PLAYER.exists() else pd.DataFrame()
nhl_t=pd.read_csv(NHL_TEAM,low_memory=False) if NHL_TEAM.exists() else pd.DataFrame()
nfl_s=pd.read_parquet(NFL_STATS) if NFL_STATS.exists() else pd.DataFrame()
nfl_snap=pd.read_parquet(NFL_SNAPS) if NFL_SNAPS.exists() else pd.DataFrame()
mlb_p=pd.read_csv(MLB_PLAYER,low_memory=False) if MLB_PLAYER.exists() else pd.DataFrame()

if not nfl_s.empty: nfl_s["_name_key"]=nfl_s["player_display_name"].map(norm)
if not nfl_snap.empty: nfl_snap["_name_key"]=nfl_snap["player"].map(norm)
if not mlb_p.empty: mlb_p["_name_key"]=mlb_p["player"].map(norm)

nba_complete={clean(x) for x in nba_t["event_id"].dropna()} if not nba_t.empty else set()
nhl_complete={clean(x) for x in nhl_t["event_id"].dropna()} if not nhl_t.empty else set()
nfl_complete={clean(x) for x in nfl_s["game_id"].dropna()} if not nfl_s.empty else set()
mlb_complete={clean(x) for x in mlb_p["gamePk"].dropna()} if not mlb_p.empty else set()

def grade_nba(r):
    event=clean(r.get("event_id")); pid=clean(r.get("player_key"))
    if event not in nba_complete: return "NOT_GRADED_YET",None
    x=nba_p[
        (nba_p["event_id"].map(clean)==event)
        & (nba_p["player_id"].map(clean)==pid)
    ] if not nba_p.empty else pd.DataFrame()
    if x.empty: return "COMPLETED_NO_PLAYER_ROW",None
    z=x.iloc[-1]
    value=num(z.get("minutes")); secondary=num(z.get("pra"))
    baseline=num(r.get("pregame_season_role_value"))
    if value is None or baseline is None: return "COMPLETED_EVENT_BASELINE_UNAVAILABLE",None
    return "GRADED",{
        "source_match_method":"EVENT_ID_PLUS_PLAYER_ID",
        "realized_primary_metric":"minutes",
        "realized_primary_value":value,
        "realized_secondary_metric":"pra",
        "realized_secondary_value":secondary,
        "pregame_primary_baseline":baseline,
        "realized_delta_vs_pregame_baseline":value-baseline,
        "outcome_unit":"MINUTES_DELTA_FROM_FROZEN_SEASON_ROLE_VALUE",
    }

def grade_nhl(r):
    event=clean(r.get("event_id")); pid=clean(r.get("player_key"))
    if event not in nhl_complete: return "NOT_GRADED_YET",None
    x=nhl_p[
        (nhl_p["event_id"].map(clean)==event)
        & (nhl_p["player_id"].map(clean)==pid)
    ] if not nhl_p.empty else pd.DataFrame()
    if x.empty: return "COMPLETED_NO_PLAYER_ROW",None
    z=x.iloc[-1]
    value=num(z.get("toi_minutes"))
    secondary=(num(z.get("shots_on_goal")) or 0)+(num(z.get("points")) or 0)
    baseline=num(r.get("pregame_season_role_value"))
    if value is None or baseline is None: return "COMPLETED_EVENT_BASELINE_UNAVAILABLE",None
    return "GRADED",{
        "source_match_method":"EVENT_ID_PLUS_PLAYER_ID",
        "realized_primary_metric":"toi_minutes",
        "realized_primary_value":value,
        "realized_secondary_metric":"shots_plus_points",
        "realized_secondary_value":secondary,
        "pregame_primary_baseline":baseline,
        "realized_delta_vs_pregame_baseline":value-baseline,
        "outcome_unit":"TOI_MINUTES_DELTA_FROM_FROZEN_SEASON_ROLE_VALUE",
    }

def grade_nfl(r):
    game=clean(r.get("source_game_key"))
    if not game or game not in nfl_complete: return "NOT_GRADED_YET",None
    name=norm(r.get("player")); team=clean(r.get("team"))
    metric=clean(r.get("role_metric"))
    baseline=num(r.get("pregame_season_role_value"))

    if metric=="defensive_snap_pct":
        x=nfl_snap[
            (nfl_snap["game_id"].map(clean)==game)
            & (nfl_snap["team"].astype(str)==team)
            & (nfl_snap["_name_key"]==name)
        ] if not nfl_snap.empty else pd.DataFrame()
        if x.empty: return "COMPLETED_NO_PLAYER_ROW",None
        z=x.iloc[-1]; value=num(z.get("defense_pct"))
        if value is None or baseline is None: return "COMPLETED_EVENT_BASELINE_UNAVAILABLE",None
        return "GRADED",{
            "source_match_method":"NFLVERSE_GAME_TEAM_EXACT_NAME",
            "realized_primary_metric":"defense_snap_pct",
            "realized_primary_value":value,
            "realized_secondary_metric":"defense_snaps",
            "realized_secondary_value":num(z.get("defense_snaps")),
            "pregame_primary_baseline":baseline,
            "realized_delta_vs_pregame_baseline":value-baseline,
            "outcome_unit":"DEFENSE_SNAP_PCT_DELTA_FROM_FROZEN_BASELINE",
        }

    x=nfl_s[
        (nfl_s["game_id"].map(clean)==game)
        & (nfl_s["team"].astype(str)==team)
        & (nfl_s["_name_key"]==name)
    ] if not nfl_s.empty else pd.DataFrame()
    if x.empty: return "COMPLETED_NO_PLAYER_ROW",None
    z=x.iloc[-1]
    if metric=="pass_attempts":
        value=num(z.get("attempts")); second=num(z.get("passing_yards")); second_name="passing_yards"
    elif metric=="carries_plus_targets":
        value=(num(z.get("carries")) or 0)+(num(z.get("targets")) or 0)
        second=(num(z.get("rushing_yards")) or 0)+(num(z.get("receiving_yards")) or 0); second_name="scrimmage_yards"
    elif metric=="targets":
        value=num(z.get("targets")); second=num(z.get("receiving_yards")); second_name="receiving_yards"
    else:
        return "ROLE_METRIC_NOT_GRADED",None
    if value is None or baseline is None: return "COMPLETED_EVENT_BASELINE_UNAVAILABLE",None
    return "GRADED",{
        "source_match_method":"NFLVERSE_GAME_TEAM_EXACT_NAME",
        "realized_primary_metric":metric,
        "realized_primary_value":value,
        "realized_secondary_metric":second_name,
        "realized_secondary_value":second,
        "pregame_primary_baseline":baseline,
        "realized_delta_vs_pregame_baseline":value-baseline,
        "outcome_unit":f"{metric.upper()}_DELTA_FROM_FROZEN_BASELINE",
    }

def grade_mlb(r):
    game=clean(r.get("source_game_key") or r.get("event_id"))
    if not game or game not in mlb_complete:
        return "NOT_GRADED_YET",None

    name=norm(r.get("player"))
    metric=clean(r.get("role_metric"))
    baseline=num(r.get("pregame_season_role_value"))
    x=mlb_p[
        (mlb_p["gamePk"].map(clean)==game)
        & (mlb_p["_name_key"]==name)
    ] if not mlb_p.empty else pd.DataFrame()

    if metric=="total_bases_plus_walks":
        x=x[x["group"].astype(str).str.upper()=="HITTING"] if not x.empty else x
    elif metric=="pitching_workload_plus_ks":
        x=x[x["group"].astype(str).str.upper()=="PITCHING"] if not x.empty else x
    else:
        return "ROLE_METRIC_NOT_GRADED",None

    if x.empty:
        return "COMPLETED_NO_PLAYER_ROW",None
    z=x.iloc[-1]

    if metric=="total_bases_plus_walks":
        value=(num(z.get("total_bases")) or 0)+(num(z.get("walks")) or 0)
        secondary=num(z.get("hrr"))
        second_name="hits_runs_rbi"
        outcome_unit="TOTAL_BASES_PLUS_WALKS_DELTA_FROM_FROZEN_BASELINE"
    else:
        value=(num(z.get("pitcher_strikeouts")) or 0)+((num(z.get("outs")) or 0)/3.0)
        secondary=num(z.get("pitcher_strikeouts"))
        second_name="pitcher_strikeouts"
        outcome_unit="PITCHING_WORKLOAD_PLUS_KS_DELTA_FROM_FROZEN_BASELINE"

    if baseline is None:
        return "COMPLETED_EVENT_BASELINE_UNAVAILABLE",None

    return "GRADED",{
        "source_match_method":"MLB_GAMEPK_EXACT_PLAYER_NAME",
        "realized_primary_metric":metric,
        "realized_primary_value":value,
        "realized_secondary_metric":second_name,
        "realized_secondary_value":secondary,
        "pregame_primary_baseline":baseline,
        "realized_delta_vs_pregame_baseline":value-baseline,
        "outcome_unit":outcome_unit,
    }

rows=[]
for r in coh.to_dict("records"):
    sport=clean(r.get("sport"))
    if sport=="NBA":
        status,result=grade_nba(r)
    elif sport=="NHL":
        status,result=grade_nhl(r)
    elif sport=="NFL":
        status,result=grade_nfl(r)
    elif sport=="MLB":
        status,result=grade_mlb(r)
    else:
        status,result="SPORT_NOT_GRADED",None

    delta=num(result.get("realized_delta_vs_pregame_baseline")) if result else None
    realized_dir=outcome_direction(delta)
    supported_dir=clean(r.get("supported_direction"))

    out={
        "cohort_identity_key":clean(r.get("cohort_identity_key")),
        "state_signature":clean(r.get("state_signature")),
        "sport":sport,
        "event_id":clean(r.get("event_id")),
        "source_game_key":clean(r.get("source_game_key")),
        "start":clean(r.get("start")),
        "observed_at":clean(r.get("observed_at")),
        "player_key":clean(r.get("player_key")),
        "player":clean(r.get("player")),
        "team":clean(r.get("team")),
        "position":clean(r.get("position")),
        "opponent":clean(r.get("opponent")),
        "cohort_class":clean(r.get("cohort_class")),
        "decision_readiness_lane":clean(r.get("decision_readiness_lane")),
        "supported_direction":supported_dir,
        "consensus_maturity":clean(r.get("consensus_maturity")),
        "current_role_signal":clean(r.get("current_role_signal")),
        "current_opponent_context":clean(r.get("current_opponent_context")),
        "role_direction":clean(r.get("role_direction")),
        "defense_direction":clean(r.get("defense_direction")),
        "role_direction_historically_supported":bool(r.get("role_direction_historically_supported")),
        "role_controlled_defense_historically_supported":bool(r.get("role_controlled_defense_historically_supported")),
        "role_and_defense_agree":bool(r.get("role_and_defense_agree")),
        "role_and_defense_conflict":bool(r.get("role_and_defense_conflict")),
        "supported_maturity_floor":clean(r.get("supported_maturity_floor")),
        "supported_maturity_ceiling":clean(r.get("supported_maturity_ceiling")),
        "role_metric":clean(r.get("role_metric")),
        "pregame_recent_role_value":num(r.get("pregame_recent_role_value")),
        "pregame_season_role_value":num(r.get("pregame_season_role_value")),
        "pregame_role_delta":num(r.get("pregame_role_delta")),
        "grade_status":status,
        "graded":status=="GRADED",
        "realized_direction_vs_baseline":realized_dir,
        "directional_alignment":alignment(supported_dir,realized_dir),
        "graded_at":NOW.isoformat(),
        "automatic_model_adjustment":False,
        "score_is_probability":False,
    }
    if result:
        out.update(result)
    else:
        out.update({
            "source_match_method":"",
            "realized_primary_metric":"",
            "realized_primary_value":None,
            "realized_secondary_metric":"",
            "realized_secondary_value":None,
            "pregame_primary_baseline":num(r.get("pregame_season_role_value")),
            "realized_delta_vs_pregame_baseline":None,
            "outcome_unit":"",
        })
    rows.append(out)

current=pd.DataFrame(rows)

if TIMELINE_OUT.exists():
    try:
        old=pd.read_csv(TIMELINE_OUT,low_memory=False)
    except Exception:
        old=pd.DataFrame()
else:
    old=pd.DataFrame()

key_cols=["cohort_identity_key","state_signature","grade_status"]
existing=set()
if not old.empty and all(c in old.columns for c in key_cols):
    existing=set(zip(
        old["cohort_identity_key"].astype(str),
        old["state_signature"].astype(str),
        old["grade_status"].astype(str),
    ))

new=current[
    ~current.apply(
        lambda r:(str(r["cohort_identity_key"]),str(r["state_signature"]),str(r["grade_status"])) in existing,
        axis=1,
    )
].copy()
timeline=new.copy() if old.empty else pd.concat([old,new],ignore_index=True,sort=False)

current.to_csv(CURRENT_OUT,index=False)
timeline.to_csv(TIMELINE_OUT,index=False)

graded=current[current["graded"].astype(bool)].copy()
summary_rows=[]
if not graded.empty:
    for keys,g in graded.groupby(
        ["sport","cohort_class","decision_readiness_lane","supported_direction"],
        dropna=False,
    ):
        sport,cohort,lane,direction=keys
        delta=pd.to_numeric(g["realized_delta_vs_pregame_baseline"],errors="coerce")
        directional=g["directional_alignment"].astype(str).isin(["ALIGNED","NOT_ALIGNED"])
        summary_rows.append({
            "sport":clean(sport),"cohort_class":clean(cohort),
            "decision_readiness_lane":clean(lane),"supported_direction":clean(direction),
            "graded_rows":len(g),"unique_events":g["event_id"].nunique(),
            "mean_delta_vs_pregame_baseline":float(delta.mean()) if delta.notna().any() else None,
            "median_delta_vs_pregame_baseline":float(delta.median()) if delta.notna().any() else None,
            "above_baseline_rate":float((delta>0).mean()) if delta.notna().any() else None,
            "below_baseline_rate":float((delta<0).mean()) if delta.notna().any() else None,
            "directional_alignment_rate":float((g.loc[directional,"directional_alignment"]=="ALIGNED").mean()) if directional.any() else None,
            "generated_at":NOW.isoformat(),
        })

SUMMARY_COLUMNS=[
    "sport","cohort_class","decision_readiness_lane","supported_direction",
    "graded_rows","unique_events","mean_delta_vs_pregame_baseline",
    "median_delta_vs_pregame_baseline","above_baseline_rate",
    "below_baseline_rate","directional_alignment_rate","generated_at",
]
summary=pd.DataFrame(summary_rows,columns=SUMMARY_COLUMNS)
summary.to_csv(SUMMARY_OUT,index=False)

features=pd.DataFrame([
    {"feature":"grade_status","definition":"Exact postgame grading state; no completed/player match is inferred."},
    {"feature":"realized_delta_vs_pregame_baseline","definition":"Realized primary opportunity minus frozen pregame season-role baseline."},
    {"feature":"directional_alignment","definition":"Whether realized delta direction aligned with the frozen supported direction."},
    {"feature":"current_role_signal/current_opponent_context","definition":"Exact frozen signal ingredients preserved into the grade ledger for signal-specific live validation."},
])
features["generated_at"]=NOW.isoformat()
features["automatic_model_adjustment"]=False
features["score_is_probability"]=False
features.to_csv(FEATURE_OUT,index=False)

sources=pd.DataFrame([
    {"source":"PREGAME_RESEARCH_STATE_TIMELINE.csv","purpose":"latest valid frozen pregame state","status":"ACTIVE"},
    {"source":"NBA_PLAYER_GAME_HISTORY.csv","purpose":"NBA realized player outcomes","status":"ACTIVE"},
    {"source":"NHL_PLAYER_GAME_HISTORY.csv","purpose":"NHL realized player outcomes","status":"ACTIVE"},
    {"source":"NFL player_stats.parquet + snap_counts.parquet","purpose":"NFL realized player opportunity outcomes","status":"ACTIVE"},
    {"source":"MLB_PLAYER_GAME_LEDGER.csv","purpose":"MLB realized player role outcomes from governed completed-game history","status":"ACTIVE"},
])
sources["generated_at"]=NOW.isoformat()
sources.to_csv(SOURCE_OUT,index=False)

receipt={
    "generated_at":NOW.isoformat(),
    "eligible_pregame_rows":int(len(coh)),
    "current_grade_rows":int(len(current)),
    "graded_rows":int(len(graded)),
    "grade_status_counts":current["grade_status"].value_counts().astype(int).to_dict() if len(current) else {},
    "graded_by_sport":graded["sport"].value_counts().astype(int).to_dict() if len(graded) else {},
    "graded_by_cohort":graded["cohort_class"].value_counts().astype(int).to_dict() if len(graded) else {},
    "new_grade_rows":int(len(new)),
    "grade_timeline_rows":int(len(timeline)),
    "summary_rows":int(len(summary)),
    "identity_duplicates":int(current.duplicated(["cohort_identity_key"]).sum()) if len(current) else 0,
    "signal_context_columns_preserved":all(
        c in current.columns for c in [
            "current_role_signal","current_opponent_context",
            "role_direction","defense_direction",
        ]
    ),
    "automatic_model_adjustment":False,
    "prediction_weight_change_allowed":False,
    "score_is_probability":False,
    "paid_provider_required":False,
    "explicit_gaps":[
        "MLB player-level grading is active for completed game IDs present in the governed player-game store; uncovered games remain ungraded until backfill reaches them.",
        "Rows are graded only from exact completed-game/player matches; unmatched rows remain ungraded.",
        "NBA/NHL grading currently uses primary opportunity baselines (minutes/TOI) frozen pregame.",
        "Postgame grades are learning evidence only and do not alter prediction weights automatically.",
    ],
}
RECEIPT_OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True))

print("ELIGIBLE PREGAME:",len(coh))
print("CURRENT GRADES:",len(current))
print("GRADED:",len(graded))
print("GRADE STATUS:",receipt["grade_status_counts"])
print("GRADED BY SPORT:",receipt["graded_by_sport"])
print("GRADED BY COHORT:",receipt["graded_by_cohort"])
print("NEW GRADE ROWS:",receipt["new_grade_rows"])
print("TIMELINE:",receipt["grade_timeline_rows"])
print("DUPS:",receipt["identity_duplicates"])
print("SIGNAL CONTEXT:",receipt["signal_context_columns_preserved"])
print("RESULT: POSTGAME_GRADING_READY")
