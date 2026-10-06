#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import math
import re

import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "intelligence_warehouse" / "evidence_gates"
OUT.mkdir(parents=True, exist_ok=True)

CAL = ROOT / "intelligence_warehouse" / "signal_calibration"
SUMMARY_FILE = CAL / "PLAYER_SIGNAL_CALIBRATION_SUMMARY.csv"
COMBO_FILE = CAL / "PLAYER_SIGNAL_COMBINATION_CALIBRATION.csv"
CONTRAST_FILE = CAL / "PLAYER_SIGNAL_DEFENSE_CONTRASTS.csv"
PLAYER_FILE = ROOT / "intelligence_warehouse" / "defensive_pressure" / "PLAYER_DEFENSIVE_MATCHUP_CURRENT.csv"
OPPORTUNITY_FILE = ROOT / "intelligence_warehouse" / "player_opportunity" / "PLAYER_OPPORTUNITY_CONTEXT_CURRENT.csv"

FACTOR_OUT = OUT / "SIGNAL_EVIDENCE_GATES_CURRENT.csv"
COMBO_GATE_OUT = OUT / "SIGNAL_COMBINATION_EVIDENCE_GATES.csv"
CONTRAST_OUT = OUT / "DEFENSE_CONTRAST_EVIDENCE_GATES.csv"
PLAYER_OUT = OUT / "PLAYER_EVIDENCE_CONTEXT_CURRENT.csv"
SOURCE_OUT = OUT / "EVIDENCE_GATE_SOURCE_CATALOG.csv"
FEATURE_OUT = OUT / "EVIDENCE_GATE_FEATURE_CATALOG.csv"
RECEIPT_OUT = OUT / "EVIDENCE_GATE_RECEIPT.json"

NOW = datetime.now(timezone.utc)
def clean(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text=str(value).strip()
    return "" if text.lower() in {"nan","none","nat","<na>"} else text

def num(value):
    try:
        x=float(value)
        return None if math.isnan(x) else x
    except Exception:
        return None

def direction(value, tol=1e-12):
    v=num(value)
    if v is None:
        return "UNKNOWN"
    if v > tol:
        return "POSITIVE"
    if v < -tol:
        return "NEGATIVE"
    return "NEUTRAL"

def expected_factor_direction(factor_type, factor_value):
    factor_type=clean(factor_type)
    value=clean(factor_value)
    if factor_type=="ROLE_SIGNAL":
        if value=="ROLE_UP": return "POSITIVE"
        if value=="ROLE_DOWN": return "NEGATIVE"
        if value=="STEADY": return "NEUTRAL"
    if factor_type=="OPPONENT_CONTEXT":
        if "PERMISSIVE" in value: return "POSITIVE"
        if "SUPPRESSIVE" in value: return "NEGATIVE"
        if value in {"NEUTRAL_PRESSURE_PROFILE","MID_OPPONENT_VOLUME"}:
            return "NEUTRAL"
        if value=="HIGH_OPPONENT_VOLUME": return "POSITIVE"
        if value=="LOW_OPPONENT_VOLUME": return "NEGATIVE"
    return "UNKNOWN"

def sample_tier(n):
    n=int(n or 0)
    if n>=200: return "MATURE_SAMPLE"
    if n>=75: return "MODERATE_SAMPLE"
    if n>=25: return "DEVELOPING_SAMPLE"
    return "THIN_SAMPLE"
def factor_gate(row):
    n=int(num(row.get("n")) or 0)
    tier=sample_tier(n)
    factor_type=clean(row.get("factor_type"))
    factor_value=clean(row.get("factor_value"))
    expected=expected_factor_direction(factor_type,factor_value)

    mean_dir=direction(row.get("mean_outcome_delta"))
    median_dir=direction(row.get("median_outcome_delta"))
    rate=num(row.get("above_baseline_rate"))
    rate_dir=direction((rate-0.5) if rate is not None else None, tol=0.01)

    if factor_value=="STEADY":
        gate=(
            "MATURE_REFERENCE" if n>=200
            else "MODERATE_REFERENCE" if n>=75
            else "DEVELOPING_REFERENCE" if n>=25
            else "THIN_REFERENCE"
        )
        return gate,expected,mean_dir,median_dir,rate_dir,0

    if expected=="UNKNOWN":
        return (
            "DESCRIPTIVE_ONLY_UNKNOWN_DIRECTION",
            expected,mean_dir,median_dir,rate_dir,0
        )

    votes=sum(x==expected for x in [mean_dir,median_dir,rate_dir])
    opposite={"POSITIVE":"NEGATIVE","NEGATIVE":"POSITIVE"}.get(expected)
    opposite_votes=sum(x==opposite for x in [mean_dir,median_dir,rate_dir])

    if n<25:
        gate="THIN_DIRECTIONAL_EVIDENCE"
    elif n<75:
        gate=(
            "DEVELOPING_DIRECTIONAL_CONSISTENT"
            if votes>=2
            else "DEVELOPING_MIXED_EVIDENCE"
        )
    elif n<200:
        gate=(
            "MODERATE_DIRECTIONAL_CONSISTENT"
            if votes>=2
            else "MODERATE_MIXED_EVIDENCE"
        )
    else:
        if votes==3:
            gate="MATURE_DIRECTIONAL_CONSISTENT"
        elif votes>=2:
            gate="MATURE_DIRECTIONAL_MOSTLY_CONSISTENT"
        elif opposite_votes>=2:
            gate="MATURE_DIRECTIONAL_CONTRADICTED"
        else:
            gate="MATURE_MIXED_EVIDENCE"

    return gate,expected,mean_dir,median_dir,rate_dir,votes
def contrast_gate(row):
    p_n=int(num(row.get("permissive_n")) or 0)
    s_n=int(num(row.get("suppressive_n")) or 0)
    n_min=min(p_n,s_n)
    mean_gap=num(row.get("permissive_minus_suppressive_mean"))
    rate_gap=num(row.get("permissive_minus_suppressive_above_rate"))
    mean_positive=mean_gap is not None and mean_gap>0
    rate_positive=rate_gap is not None and rate_gap>0

    if n_min<25:
        gate="THIN_ROLE_CONTROLLED_DEFENSE_EVIDENCE"
    elif n_min<75:
        gate=(
            "DEVELOPING_ROLE_CONTROLLED_SUPPORT"
            if mean_positive and rate_positive
            else "DEVELOPING_ROLE_CONTROLLED_MIXED"
        )
    elif n_min<200:
        gate=(
            "MODERATE_ROLE_CONTROLLED_SUPPORT"
            if mean_positive and rate_positive
            else "MODERATE_ROLE_CONTROLLED_MIXED"
        )
    else:
        if mean_positive and rate_positive:
            gate="MATURE_ROLE_CONTROLLED_SUPPORT"
        elif mean_positive or rate_positive:
            gate="MATURE_ROLE_CONTROLLED_MIXED"
        else:
            gate="MATURE_ROLE_CONTROLLED_CONTRADICTED"

    return gate,n_min,mean_positive,rate_positive
summary=pd.read_csv(SUMMARY_FILE,low_memory=False)
combo=pd.read_csv(COMBO_FILE,low_memory=False)
contrast=pd.read_csv(CONTRAST_FILE,low_memory=False)
players=pd.read_csv(PLAYER_FILE,low_memory=False)
opportunity=pd.read_csv(OPPORTUNITY_FILE,low_memory=False)

factor_rows=[]
for r in summary.to_dict("records"):
    gate,expected,mean_dir,median_dir,rate_dir,votes=factor_gate(r)
    factor_rows.append({
        "sport":clean(r.get("sport")),
        "interaction_family":clean(r.get("interaction_family")),
        "position_group":clean(r.get("position_group")),
        "factor_type":clean(r.get("factor_type")),
        "factor_value":clean(r.get("factor_value")),
        "outcome_unit":clean(r.get("outcome_unit")),
        "n":int(num(r.get("n")) or 0),
        "sample_tier":sample_tier(num(r.get("n")) or 0),
        "mean_outcome_delta":num(r.get("mean_outcome_delta")),
        "median_outcome_delta":num(r.get("median_outcome_delta")),
        "above_baseline_rate":num(r.get("above_baseline_rate")),
        "outcome_sem":num(r.get("outcome_sem")),
        "expected_direction":expected,
        "observed_mean_direction":mean_dir,
        "observed_median_direction":median_dir,
        "observed_rate_direction":rate_dir,
        "directional_votes":votes,
        "evidence_gate":gate,
        "role_confounding_caution":(
            clean(r.get("factor_type"))=="OPPONENT_CONTEXT"
        ),
        "generated_at":NOW.isoformat(),
        "automatic_model_adjustment":False,
        "score_is_probability":False,
    })
factor_gates=pd.DataFrame(factor_rows)
def combo_gate(row):
    n=int(num(row.get("n")) or 0)
    mean_dir=direction(row.get("mean_outcome_delta"))
    median_dir=direction(row.get("median_outcome_delta"))
    rate=num(row.get("above_baseline_rate"))
    rate_dir=direction((rate-0.5) if rate is not None else None, tol=0.01)
    dirs=[mean_dir,median_dir,rate_dir]
    pos=sum(x=="POSITIVE" for x in dirs)
    neg=sum(x=="NEGATIVE" for x in dirs)

    if n<25:
        return "THIN_COMBINATION_EVIDENCE",mean_dir,median_dir,rate_dir
    prefix=(
        "MATURE" if n>=200
        else "MODERATE" if n>=75
        else "DEVELOPING"
    )
    if pos==3:
        gate=f"{prefix}_POSITIVE_PATTERN"
    elif neg==3:
        gate=f"{prefix}_NEGATIVE_PATTERN"
    elif pos>=2:
        gate=f"{prefix}_MOSTLY_POSITIVE_PATTERN"
    elif neg>=2:
        gate=f"{prefix}_MOSTLY_NEGATIVE_PATTERN"
    else:
        gate=f"{prefix}_MIXED_PATTERN"
    return gate,mean_dir,median_dir,rate_dir

combo_rows=[]
for r in combo.to_dict("records"):
    gate,mean_dir,median_dir,rate_dir=combo_gate(r)
    combo_rows.append({
        **{k:r.get(k) for k in [
            "sport","interaction_family","position_group",
            "pregame_role_signal","pregame_defense_context","outcome_unit"
        ]},
        "n":int(num(r.get("n")) or 0),
        "sample_tier":sample_tier(num(r.get("n")) or 0),
        "mean_outcome_delta":num(r.get("mean_outcome_delta")),
        "median_outcome_delta":num(r.get("median_outcome_delta")),
        "above_baseline_rate":num(r.get("above_baseline_rate")),
        "observed_mean_direction":mean_dir,
        "observed_median_direction":median_dir,
        "observed_rate_direction":rate_dir,
        "combination_evidence_gate":gate,
        "generated_at":NOW.isoformat(),
        "automatic_model_adjustment":False,
        "score_is_probability":False,
    })
combo_gates=pd.DataFrame(combo_rows)

contrast_rows=[]
for r in contrast.to_dict("records"):
    gate,n_min,mean_positive,rate_positive=contrast_gate(r)
    contrast_rows.append({
        **{k:r.get(k) for k in [
            "sport","interaction_family","position_group",
            "pregame_role_signal","outcome_unit"
        ]},
        "permissive_n":int(num(r.get("permissive_n")) or 0),
        "suppressive_n":int(num(r.get("suppressive_n")) or 0),
        "minimum_side_n":n_min,
        "contrast_sample_tier":sample_tier(n_min),
        "permissive_mean_outcome_delta":num(r.get("permissive_mean_outcome_delta")),
        "suppressive_mean_outcome_delta":num(r.get("suppressive_mean_outcome_delta")),
        "permissive_minus_suppressive_mean":num(r.get("permissive_minus_suppressive_mean")),
        "permissive_above_baseline_rate":num(r.get("permissive_above_baseline_rate")),
        "suppressive_above_baseline_rate":num(r.get("suppressive_above_baseline_rate")),
        "permissive_minus_suppressive_above_rate":num(r.get("permissive_minus_suppressive_above_rate")),
        "mean_contrast_supports_expected_order":mean_positive,
        "rate_contrast_supports_expected_order":rate_positive,
        "defense_contrast_evidence_gate":gate,
        "generated_at":NOW.isoformat(),
        "automatic_model_adjustment":False,
        "score_is_probability":False,
    })
contrast_gates=pd.DataFrame(contrast_rows)
opp_extra=opportunity[[
    "sport","opportunity_identity_key","role_metric",
    "position_style_context","matchup_coverage_status"
]].copy()
current=players.merge(
    opp_extra,
    on=["sport","opportunity_identity_key"],
    how="left",
    suffixes=("","_opp"),
)

role_gate_lookup={}
for r in factor_gates[
    factor_gates["factor_type"].astype(str)=="ROLE_SIGNAL"
].to_dict("records"):
    role_gate_lookup[(
        clean(r.get("sport")),
        clean(r.get("interaction_family")),
        clean(r.get("position_group")),
        clean(r.get("factor_value")),
    )]=r

combo_gate_lookup={}
for r in combo_gates.to_dict("records"):
    combo_gate_lookup[(
        clean(r.get("sport")),
        clean(r.get("interaction_family")),
        clean(r.get("position_group")),
        clean(r.get("pregame_role_signal")),
        clean(r.get("pregame_defense_context")),
    )]=r

contrast_gate_lookup={}
for r in contrast_gates.to_dict("records"):
    contrast_gate_lookup[(
        clean(r.get("sport")),
        clean(r.get("interaction_family")),
        clean(r.get("position_group")),
        clean(r.get("pregame_role_signal")),
    )]=r

def current_family_and_context(row):
    sport=clean(row.get("sport"))
    role_metric=clean(row.get("role_metric"))
    pos_group=clean(row.get("defense_position_group"))
    if sport=="NFL" and role_metric=="defensive_snap_pct":
        mapping={
            "IDP_VOLUME_SUPPORT":"HIGH_OPPONENT_VOLUME",
            "IDP_VOLUME_CONSTRAINT":"LOW_OPPONENT_VOLUME",
            "IDP_VOLUME_NEUTRAL":"MID_OPPONENT_VOLUME",
        }
        return (
            "IDP_ROLE_X_OPPOSING_OFFENSE_VOLUME",
            "IDP",
            mapping.get(clean(row.get("position_style_context")),"LIMITED_SAMPLE"),
        )
    if sport in {"NFL","NBA","NHL"}:
        return (
            "PLAYER_ROLE_X_DEFENSE_POSITION",
            pos_group,
            clean(row.get("defensive_pressure_context")),
        )
    if sport=="MLB":
        mlb_group=(
            "PITCHING"
            if role_metric=="pitching_workload_plus_ks"
            else "HITTING"
            if role_metric=="total_bases_plus_walks"
            else "NOT_CALIBRATED"
        )
        return (
            "MLB_PLAYER_ROLE_HISTORY",
            mlb_group,
            "NOT_MODELED",
        )
    return "NOT_CALIBRATED","NOT_CALIBRATED","NOT_CALIBRATED"
player_rows=[]
for r in current.to_dict("records"):
    sport=clean(r.get("sport"))
    family,pos_group,def_context=current_family_and_context(r)
    role_signal=clean(r.get("role_signal"))

    role_gate=role_gate_lookup.get((sport,family,pos_group,role_signal),{})
    combo_gate_row=combo_gate_lookup.get((
        sport,family,pos_group,role_signal,def_context
    ),{})
    contrast_gate_row=contrast_gate_lookup.get((
        sport,family,pos_group,role_signal
    ),{})

    if clean(r.get("matchup_coverage_status"))=="NO_UPCOMING_MODELED_GAME":
        readiness="NO_UPCOMING_MODELED_GAME"
    elif sport not in {"NFL","NBA","NHL","MLB"}:
        readiness="NOT_YET_CALIBRATED_SPORT"
    elif clean(r.get("defense_join_status"))=="INVALID_PLAYER_IDENTITY":
        readiness="INVALID_PLAYER_IDENTITY"
    elif combo_gate_row:
        cg=clean(combo_gate_row.get("combination_evidence_gate"))
        rg=clean(role_gate.get("evidence_gate"))
        if cg.startswith("MATURE") and rg.startswith("MATURE"):
            readiness="MATURE_CURRENT_COMBINATION_EVIDENCE"
        elif cg.startswith(("MATURE","MODERATE")):
            readiness="USABLE_DESCRIPTIVE_COMBINATION_EVIDENCE"
        elif cg.startswith("DEVELOPING"):
            readiness="DEVELOPING_CURRENT_COMBINATION_EVIDENCE"
        else:
            readiness="THIN_CURRENT_COMBINATION_EVIDENCE"
    elif role_gate:
        readiness="ROLE_FACTOR_EVIDENCE_ONLY"
    else:
        readiness="NO_MATCHED_HISTORICAL_EVIDENCE"

    player_rows.append({
        "sport":sport,
        "opportunity_identity_key":clean(r.get("opportunity_identity_key")),
        "player_key":clean(r.get("player_key")),
        "player":clean(r.get("player")),
        "team":clean(r.get("team")),
        "position":clean(r.get("position")),
        "event_id":clean(r.get("event_id")),
        "start":clean(r.get("start")),
        "opponent":clean(r.get("opponent")),
        "availability_context":clean(r.get("availability_context")),
        "opportunity_context":clean(r.get("opportunity_context")),
        "current_role_signal":role_signal,
        "current_interaction_family":family,
        "current_position_group":pos_group,
        "current_opponent_context":def_context,
        "role_evidence_gate":clean(role_gate.get("evidence_gate")) or "NO_ROLE_EVIDENCE_GATE",
        "role_direction_historically_supported":(
            "DIRECTIONAL_CONSISTENT" in clean(role_gate.get("evidence_gate"))
            or "DIRECTIONAL_MOSTLY_CONSISTENT" in clean(role_gate.get("evidence_gate"))
        ),
        "role_evidence_n":num(role_gate.get("n")),
        "role_mean_outcome_delta":num(role_gate.get("mean_outcome_delta")),
        "role_above_baseline_rate":num(role_gate.get("above_baseline_rate")),
        "combination_evidence_gate":clean(combo_gate_row.get("combination_evidence_gate")) or "NO_COMBINATION_GATE",
        "combination_evidence_n":num(combo_gate_row.get("n")),
        "combination_mean_outcome_delta":num(combo_gate_row.get("mean_outcome_delta")),
        "combination_above_baseline_rate":num(combo_gate_row.get("above_baseline_rate")),
        "defense_contrast_evidence_gate":clean(contrast_gate_row.get("defense_contrast_evidence_gate")) or "NO_ROLE_CONTROLLED_DEFENSE_CONTRAST",
        "role_controlled_defense_historically_supported":(
            clean(contrast_gate_row.get("defense_contrast_evidence_gate")).endswith("_SUPPORT")
        ),
        "defense_contrast_minimum_side_n":num(contrast_gate_row.get("minimum_side_n")),
        "defense_permissive_minus_suppressive_mean":num(contrast_gate_row.get("permissive_minus_suppressive_mean")),
        "defense_permissive_minus_suppressive_above_rate":num(contrast_gate_row.get("permissive_minus_suppressive_above_rate")),
        "evidence_readiness":readiness,
        "generated_at":NOW.isoformat(),
        "automatic_model_adjustment":False,
        "score_is_probability":False,
    })

player_evidence=pd.DataFrame(player_rows)
features=pd.DataFrame([
    {
        "feature":"role_evidence_gate",
        "definition":"Historical evidence maturity/direction for the current role signal.",
        "scope":"CURRENT_PLAYER",
    },
    {
        "feature":"combination_evidence_gate",
        "definition":"Historical pattern strength for the exact current role-state x opponent-context combination.",
        "scope":"CURRENT_PLAYER",
    },
    {
        "feature":"defense_contrast_evidence_gate",
        "definition":"Role-controlled evidence that strong permissive opponents separated from strong suppressive opponents for the same sport/position/role state.",
        "scope":"SPORT_POSITION_ROLE",
    },
    {
        "feature":"evidence_readiness",
        "definition":"Availability of mature/moderate/developing/thin historical evidence for the current player's exact context.",
        "scope":"CURRENT_PLAYER",
    },
    {
        "feature":"role_confounding_caution",
        "definition":"Marks raw opponent-context summaries as potentially confounded by player role; role-controlled contrast is preferred for defense claims.",
        "scope":"CALIBRATION_FACTOR",
    },
])
features["score_is_probability"]=False
features["automatic_model_adjustment"]=False
features["generated_at"]=NOW.isoformat()

sources=pd.DataFrame([
    {
        "source":"PLAYER_SIGNAL_CALIBRATION_SUMMARY.csv",
        "purpose":"factor evidence maturity and direction",
        "status":"ACTIVE",
    },
    {
        "source":"PLAYER_SIGNAL_COMBINATION_CALIBRATION.csv",
        "purpose":"exact role x opponent combination evidence",
        "status":"ACTIVE",
    },
    {
        "source":"PLAYER_SIGNAL_DEFENSE_CONTRASTS.csv",
        "purpose":"role-controlled permissive vs suppressive defense evidence",
        "status":"ACTIVE",
    },
    {
        "source":"PLAYER_DEFENSIVE_MATCHUP_CURRENT.csv",
        "purpose":"current player opponent defensive context",
        "status":"ACTIVE",
    },
    {
        "source":"PLAYER_OPPORTUNITY_CONTEXT_CURRENT.csv",
        "purpose":"current role metric and IDP opposing-volume context",
        "status":"ACTIVE",
    },
])
sources["generated_at"]=NOW.isoformat()
factor_gates.to_csv(FACTOR_OUT,index=False)
combo_gates.to_csv(COMBO_GATE_OUT,index=False)
contrast_gates.to_csv(CONTRAST_OUT,index=False)
player_evidence.to_csv(PLAYER_OUT,index=False)
sources.to_csv(SOURCE_OUT,index=False)
features.to_csv(FEATURE_OUT,index=False)

factor_gate_counts=factor_gates["evidence_gate"].value_counts().astype(int).to_dict()
combo_gate_counts=combo_gates["combination_evidence_gate"].value_counts().astype(int).to_dict()
contrast_gate_counts=contrast_gates["defense_contrast_evidence_gate"].value_counts().astype(int).to_dict()
readiness_counts=player_evidence["evidence_readiness"].value_counts().astype(int).to_dict()

receipt={
    "generated_at":NOW.isoformat(),
    "factor_gate_rows":int(len(factor_gates)),
    "combination_gate_rows":int(len(combo_gates)),
    "defense_contrast_gate_rows":int(len(contrast_gates)),
    "current_player_evidence_rows":int(len(player_evidence)),
    "factor_gate_counts":factor_gate_counts,
    "combination_gate_counts":combo_gate_counts,
    "defense_contrast_gate_counts":contrast_gate_counts,
    "current_player_readiness_counts":readiness_counts,
    "current_player_rows_by_sport":(
        player_evidence["sport"].value_counts().astype(int).to_dict()
        if not player_evidence.empty else {}
    ),
    "current_player_identity_duplicates":int(
        player_evidence.duplicated(["sport","opportunity_identity_key"]).sum()
    ),
    "mature_role_directional_rows":int(
        factor_gates[
            (factor_gates["factor_type"]=="ROLE_SIGNAL")
            & factor_gates["evidence_gate"].astype(str).str.startswith("MATURE_DIRECTIONAL")
        ].shape[0]
    ),
    "mature_role_controlled_defense_rows":int(
        contrast_gates[
            contrast_gates["defense_contrast_evidence_gate"]
            =="MATURE_ROLE_CONTROLLED_SUPPORT"
        ].shape[0]
    ),
    "explicit_gaps":[
        "MLB role evidence is calibrated from governed 2025-26 player-game history; opponent-pitching interaction evidence remains unmodeled.",
        "CBB and CFB player-level evidence gates remain unavailable because governed player-role histories do not yet exist.",
        "NFL offensive combination evidence remains thin/developing in many position states because only a few current-season weeks are available.",
        "Raw opponent-context factor gates carry role_confounding_caution=true; role-controlled defense contrasts are preferred for defense-specific evidence.",
        "Evidence gates are descriptive confidence/maturity metadata only and do not alter predictions, rankings, recommendations, or model weights automatically.",
    ],
    "automatic_model_adjustment":False,
    "score_is_probability":False,
    "paid_provider_required":False,
}
RECEIPT_OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True))

print("FACTOR GATES:",len(factor_gates))
print("COMBINATION GATES:",len(combo_gates))
print("DEFENSE CONTRAST GATES:",len(contrast_gates))
print("CURRENT PLAYER EVIDENCE:",len(player_evidence))
print("READINESS:",readiness_counts)
print("MATURE ROLE DIRECTIONAL:",receipt["mature_role_directional_rows"])
print("MATURE ROLE-CONTROLLED DEFENSE:",receipt["mature_role_controlled_defense_rows"])
print("IDENTITY DUPLICATES:",receipt["current_player_identity_duplicates"])
print("RESULT: EVIDENCE_GATES_READY")
