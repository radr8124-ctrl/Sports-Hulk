#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
OUT=ROOT/"intelligence_warehouse"/"pregame_cohorts"
OUT.mkdir(parents=True,exist_ok=True)

INPUT=ROOT/"intelligence_warehouse"/"decision_readiness"/"PLAYER_DECISION_READINESS_CURRENT.csv"
OPPORTUNITY_INPUT=ROOT/"intelligence_warehouse"/"player_opportunity"/"PLAYER_OPPORTUNITY_CONTEXT_CURRENT.csv"
CONSENSUS_INPUT=ROOT/"intelligence_warehouse"/"signal_consensus"/"PLAYER_SIGNAL_CONSENSUS_CURRENT.csv"
NFL_SCHEDULE_INPUT=ROOT/"nfl_live"/"derived"/"NFL_CURRENT_WEEK.csv"
NFL_STATS_INPUT=ROOT/"nfl_live"/"player_context"/"raw"/"player_stats.parquet"

CURRENT_OUT=OUT/"PREGAME_RESEARCH_COHORT_CURRENT.csv"
TIMELINE_OUT=OUT/"PREGAME_RESEARCH_STATE_TIMELINE.csv"
SUMMARY_OUT=OUT/"PREGAME_RESEARCH_COHORT_SUMMARY.csv"
SOURCE_OUT=OUT/"PREGAME_RESEARCH_SOURCE_CATALOG.csv"
FEATURE_OUT=OUT/"PREGAME_RESEARCH_FEATURE_CATALOG.csv"
RECEIPT_OUT=OUT/"PREGAME_RESEARCH_RECEIPT.json"

NOW=datetime.now(timezone.utc)
NOW_TS=pd.Timestamp(NOW)

def clean(v):
    if v is None: return ""
    try:
        if pd.isna(v): return ""
    except Exception:
        pass
    s=str(v).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        return s[:-2]
    return s

def cohort_class(lane):
    lane=clean(lane)
    if lane.startswith("RESEARCH_READY"):
        return "RESEARCH_READY"
    if lane.startswith("HOLD_"):
        return "HOLD_REVIEW"
    if lane=="BLOCKED_AVAILABILITY":
        return "OPERATIONALLY_BLOCKED"
    if lane=="INVALID_PLAYER_IDENTITY":
        return "INVALID_IDENTITY"
    if lane in {"DESCRIPTIVE_ONLY_UNCALIBRATED"}:
        return "DESCRIPTIVE_CONTROL"
    if lane.startswith("OBSERVE_"):
        return "OBSERVE_CONTROL"
    return "OTHER_CONTROL"

def grading_eligible(cls):
    return cls in {"RESEARCH_READY","OBSERVE_CONTROL","DESCRIPTIVE_CONTROL","HOLD_REVIEW"}

NFL_FULL_TO_ABBR={
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

nfl_game_key_by_event={}
if NFL_SCHEDULE_INPUT.exists() and NFL_STATS_INPUT.exists():
    ns=pd.read_csv(NFL_SCHEDULE_INPUT,low_memory=False)
    ps=pd.read_parquet(NFL_STATS_INPUT)
    ps=ps[(ps["season"]==2026)&(ps["season_type"].astype(str).str.upper()=="REG")]
    current_week=int(pd.to_numeric(ps["week"],errors="coerce").max()) if len(ps) else 0
    for rr in ns.to_dict("records"):
        away=NFL_FULL_TO_ABBR.get(clean(rr.get("away_team")),clean(rr.get("away_team")))
        home=NFL_FULL_TO_ABBR.get(clean(rr.get("home_team")),clean(rr.get("home_team")))
        eid=clean(rr.get("event_id"))
        if eid and current_week:
            nfl_game_key_by_event[eid]=f"2026_{current_week:02d}_{away}_{home}"

d=pd.read_csv(INPUT,low_memory=False)
opp=pd.read_csv(OPPORTUNITY_INPUT,low_memory=False)
opp_keep=opp[[
    "sport","opportunity_identity_key","role_metric","recent_role_value",
    "season_role_value","role_delta","role_sample_marker",
    "environment_signal","position_style_context",
]].copy()
d=d.merge(
    opp_keep,
    on=["sport","opportunity_identity_key"],
    how="left",
)
cons=pd.read_csv(CONSENSUS_INPUT,low_memory=False)
cons_keep=cons[[
    "sport","opportunity_identity_key","current_role_signal",
    "current_opponent_context","role_direction","defense_direction",
    "role_direction_historically_supported",
    "role_controlled_defense_historically_supported",
    "role_and_defense_agree","role_and_defense_conflict",
    "supported_maturity_floor","supported_maturity_ceiling",
]].copy()
d=d.merge(
    cons_keep,
    on=["sport","opportunity_identity_key"],
    how="left",
)
d["start_dt"]=pd.to_datetime(d["start"],errors="coerce",utc=True,format="mixed")
pregame=d[
    d["start_dt"].notna()
    & (d["start_dt"]>NOW_TS)
].copy()

rows=[]
for r in pregame.to_dict("records"):
    cls=cohort_class(r.get("decision_readiness_lane"))
    identity="|".join([
        clean(r.get("sport")),
        clean(r.get("event_id")),
        clean(r.get("opportunity_identity_key")),
    ])
    source_game_key=(
        nfl_game_key_by_event.get(clean(r.get("event_id")),"")
        if clean(r.get("sport"))=="NFL"
        else clean(r.get("event_id"))
    )
    signature_source="|".join([
        clean(r.get("decision_readiness_lane")),
        clean(r.get("supported_direction")),
        clean(r.get("consensus_maturity")),
        clean(r.get("operational_gate")),
        clean(r.get("consensus_state")),
        clean(r.get("conflict_priority")),
        clean(r.get("availability_status")),
        clean(r.get("role_metric")),
        clean(r.get("recent_role_value")),
        clean(r.get("season_role_value")),
        clean(r.get("role_delta")),
        clean(r.get("environment_signal")),
        clean(r.get("position_style_context")),
        clean(r.get("current_role_signal")),
        clean(r.get("current_opponent_context")),
        clean(r.get("role_direction")),
        clean(r.get("defense_direction")),
        clean(r.get("supported_maturity_floor")),
        clean(r.get("supported_maturity_ceiling")),
    ])
    signature=hashlib.sha256(signature_source.encode()).hexdigest()[:16]
    rows.append({
        "cohort_identity_key":identity,
        "state_signature":signature,
        "sport":clean(r.get("sport")),
        "event_id":clean(r.get("event_id")),
        "source_game_key":source_game_key,
        "start":clean(r.get("start")),
        "opportunity_identity_key":clean(r.get("opportunity_identity_key")),
        "player_key":clean(r.get("player_key")),
        "player":clean(r.get("player")),
        "team":clean(r.get("team")),
        "position":clean(r.get("position")),
        "opponent":clean(r.get("opponent")),
        "cohort_class":cls,
        "grading_eligible":grading_eligible(cls),
        "decision_readiness_lane":clean(r.get("decision_readiness_lane")),
        "research_ready":bool(r.get("research_ready")),
        "needs_review":bool(r.get("needs_review")),
        "supported_direction":clean(r.get("supported_direction")),
        "consensus_state":clean(r.get("consensus_state")),
        "consensus_maturity":clean(r.get("consensus_maturity")),
        "operational_gate":clean(r.get("operational_gate")),
        "conflict_priority":clean(r.get("conflict_priority")),
        "conflict_types":clean(r.get("conflict_types")),
        "evidence_readiness":clean(r.get("evidence_readiness")),
        "availability_context":clean(r.get("availability_context")),
        "availability_status":clean(r.get("availability_status")),
        "starter_confirmed_or_probable":bool(r.get("starter_confirmed_or_probable")),
        "role_metric":clean(r.get("role_metric")),
        "pregame_recent_role_value":r.get("recent_role_value"),
        "pregame_season_role_value":r.get("season_role_value"),
        "pregame_role_delta":r.get("role_delta"),
        "pregame_role_sample_marker":r.get("role_sample_marker"),
        "environment_signal":clean(r.get("environment_signal")),
        "position_style_context":clean(r.get("position_style_context")),
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
        "observed_at":NOW.isoformat(),
        "pregame_only":True,
        "automatic_model_adjustment":False,
        "score_is_probability":False,
    })

current=pd.DataFrame(rows)

if TIMELINE_OUT.exists():
    try:
        timeline=pd.read_csv(TIMELINE_OUT,low_memory=False)
    except Exception:
        timeline=pd.DataFrame()
else:
    timeline=pd.DataFrame()

existing=set()
if not timeline.empty:
    existing=set(
        zip(
            timeline["cohort_identity_key"].astype(str),
            timeline["state_signature"].astype(str),
        )
    )

new_states=current[
    ~current.apply(
        lambda r:(str(r["cohort_identity_key"]),str(r["state_signature"])) in existing,
        axis=1,
    )
].copy()

if timeline.empty:
    timeline_out=new_states.copy()
else:
    timeline_out=pd.concat([timeline,new_states],ignore_index=True,sort=False)

timeline_out.to_csv(TIMELINE_OUT,index=False)
current.to_csv(CURRENT_OUT,index=False)

summary=(
    current.groupby(
        ["sport","cohort_class","decision_readiness_lane"],
        dropna=False,
    )
    .agg(
        player_rows=("cohort_identity_key","size"),
        unique_events=("event_id","nunique"),
        grading_eligible_rows=("grading_eligible","sum"),
        review_rows=("needs_review","sum"),
    )
    .reset_index()
)
summary["generated_at"]=NOW.isoformat()
summary.to_csv(SUMMARY_OUT,index=False)

sources=pd.DataFrame([
    {
        "source":"PLAYER_DECISION_READINESS_CURRENT.csv",
        "purpose":"freeze current pregame evidence-governance state into learning cohorts",
        "status":"ACTIVE",
    },
    {
        "source":"PLAYER_OPPORTUNITY_CONTEXT_CURRENT.csv",
        "purpose":"freeze role metric and pregame recent/season opportunity baselines",
        "status":"ACTIVE",
    },
])
sources["generated_at"]=NOW.isoformat()
sources.to_csv(SOURCE_OUT,index=False)

features=pd.DataFrame([
    {
        "feature":"cohort_class",
        "definition":"Broad pregame learning group: research-ready, observe control, descriptive control, hold review, operational block, or invalid identity.",
    },
    {
        "feature":"state_signature",
        "definition":"Stable hash of the pregame readiness/direction/maturity/availability/conflict state; a new timeline row is written only when this state changes.",
    },
    {
        "feature":"grading_eligible",
        "definition":"Whether the pregame row should later be compared with realized outcomes for evidence-learning research.",
    },
    {
        "feature":"pregame_only",
        "definition":"Always true; rows are included only when event start is strictly after observation time.",
    },
])
features["generated_at"]=NOW.isoformat()
features["automatic_model_adjustment"]=False
features["score_is_probability"]=False
features.to_csv(FEATURE_OUT,index=False)

receipt={
    "generated_at":NOW.isoformat(),
    "input_rows":int(len(d)),
    "current_pregame_rows":int(len(current)),
    "current_unique_events":int(current["event_id"].nunique()) if len(current) else 0,
    "current_rows_by_sport":current["sport"].value_counts().astype(int).to_dict() if len(current) else {},
    "current_cohort_counts":current["cohort_class"].value_counts().astype(int).to_dict() if len(current) else {},
    "current_lane_counts":current["decision_readiness_lane"].value_counts().astype(int).to_dict() if len(current) else {},
    "grading_eligible_rows":int(current["grading_eligible"].astype(bool).sum()) if len(current) else 0,
    "new_state_rows":int(len(new_states)),
    "timeline_rows":int(len(timeline_out)),
    "identity_duplicates":int(current.duplicated(["cohort_identity_key"]).sum()) if len(current) else 0,
    "post_start_rows":int((pd.to_datetime(current["start"],errors="coerce",utc=True,format="mixed")<=NOW_TS).sum()) if len(current) else 0,
    "automatic_model_adjustment":False,
    "score_is_probability":False,
    "paid_provider_required":False,
    "explicit_gaps":[
        "This layer freezes pregame evidence states only; no postgame outcome grading is performed here.",
        "Research-ready is an evidence-governance cohort, not a recommendation, ranking, wager, projection, or probability.",
        "Operationally blocked rows are preserved for audit but are not grading-eligible.",
    ],
}
RECEIPT_OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True))

print("CURRENT PREGAME:",len(current))
print("EVENTS:",receipt["current_unique_events"])
print("COHORTS:",receipt["current_cohort_counts"])
print("GRADING ELIGIBLE:",receipt["grading_eligible_rows"])
print("NEW STATES:",receipt["new_state_rows"])
print("TIMELINE:",receipt["timeline_rows"])
print("DUPS:",receipt["identity_duplicates"])
print("POST START:",receipt["post_start_rows"])
print("RESULT: PREGAME_COHORTS_READY")
