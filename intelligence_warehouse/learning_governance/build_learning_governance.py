#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import math
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
OUT=ROOT/"intelligence_warehouse"/"learning_governance"
OUT.mkdir(parents=True,exist_ok=True)

FACTOR_FILE=ROOT/"intelligence_warehouse"/"evidence_gates"/"SIGNAL_EVIDENCE_GATES_CURRENT.csv"
DEFENSE_FILE=ROOT/"intelligence_warehouse"/"evidence_gates"/"DEFENSE_CONTRAST_EVIDENCE_GATES.csv"
LIVE_FILE=ROOT/"intelligence_warehouse"/"cohort_learning"/"RESEARCH_READY_VS_CONTROL_CURRENT.csv"
LEARNING_FILE=ROOT/"intelligence_warehouse"/"cohort_learning"/"LEARNING_MATURITY_CURRENT.csv"
POSTGAME_FILE=ROOT/"intelligence_warehouse"/"postgame_grading"/"POSTGAME_RESEARCH_GRADES_CURRENT.csv"

REGISTRY_OUT=OUT/"SIGNAL_CHANGE_ELIGIBILITY_CURRENT.csv"
SPORT_OUT=OUT/"LIVE_VALIDATION_STATUS_CURRENT.csv"
POLICY_OUT=OUT/"LEARNING_CHANGE_POLICY.csv"
SOURCE_OUT=OUT/"LEARNING_GOVERNANCE_SOURCE_CATALOG.csv"
FEATURE_OUT=OUT/"LEARNING_GOVERNANCE_FEATURE_CATALOG.csv"
RECEIPT_OUT=OUT/"LEARNING_GOVERNANCE_RECEIPT.json"

NOW=datetime.now(timezone.utc)

def clean(v):
    if v is None: return ""
    try:
        if pd.isna(v): return ""
    except Exception:
        pass
    return str(v).strip()

def num(v):
    try:
        x=float(v)
        return None if math.isnan(x) else x
    except Exception:
        return None

def position_group(sport,position):
    s=clean(sport).upper(); p=clean(position).upper()
    if s=="NBA":
        if p in {"G","PG","SG"}: return "G"
        if p in {"F","SF","PF"}: return "F"
        if p=="C": return "C"
    if s=="NHL":
        if p=="C": return "C"
        if p in {"L","R","LW","RW"}: return "W"
        if p=="D": return "D"
    if s=="NFL":
        if p=="QB": return "QB"
        if p in {"RB","FB"}: return "RB"
        if p=="WR": return "WR"
        if p=="TE": return "TE"
        return "IDP"
    return p or "UNKNOWN"

def sample_gate(n):
    n=int(n or 0)
    if n>=500: return "MATURE_LIVE_SAMPLE"
    if n>=200: return "MODERATE_LIVE_SAMPLE"
    if n>=75: return "DEVELOPING_LIVE_SAMPLE"
    if n>=25: return "THIN_LIVE_SAMPLE"
    if n>0: return "INSUFFICIENT_LIVE_SAMPLE"
    return "NO_LIVE_SAMPLE"

def sign(v,tol=0.0):
    x=num(v)
    if x is None: return "UNKNOWN"
    if x>tol: return "POSITIVE"
    if x<-tol: return "NEGATIVE"
    return "NEUTRAL"

def historical_state(gate):
    g=clean(gate)
    if g in {"MATURE_DIRECTIONAL_CONSISTENT","MATURE_DIRECTIONAL_MOSTLY_CONSISTENT","MATURE_ROLE_CONTROLLED_SUPPORT"}:
        return "MATURE_HISTORICAL_SUPPORT"
    if g in {"MODERATE_DIRECTIONAL_CONSISTENT","MODERATE_ROLE_CONTROLLED_SUPPORT"}:
        return "MODERATE_HISTORICAL_SUPPORT"
    if g in {"DEVELOPING_DIRECTIONAL_CONSISTENT","DEVELOPING_ROLE_CONTROLLED_SUPPORT"}:
        return "DEVELOPING_HISTORICAL_SUPPORT"
    if "CONTRADICT" in g:
        return "HISTORICAL_CONTRADICTED"
    if "MIXED" in g:
        return "HISTORICAL_MIXED"
    if "REFERENCE" in g:
        return "REFERENCE_ONLY"
    return "HISTORICAL_NOT_SUPPORTED"

factors=pd.read_csv(FACTOR_FILE,low_memory=False)
defense=pd.read_csv(DEFENSE_FILE,low_memory=False)
live=pd.read_csv(LIVE_FILE,low_memory=False)
learning=pd.read_csv(LEARNING_FILE,low_memory=False)
grades=pd.read_csv(POSTGAME_FILE,low_memory=False)

grades["position_group"]=grades.apply(
    lambda r:position_group(r.get("sport"),r.get("position")),
    axis=1,
)
graded=grades[grades["grade_status"].astype(str)=="GRADED"].copy()

sport_rows=[]
for r in live.to_dict("records"):
    sport=clean(r.get("sport"))
    min_n=int(num(r.get("minimum_side_n")) or 0)
    if min_n==0:
        state="NO_COMPLETED_LIVE_VALIDATION"
    elif min_n<25:
        state="INSUFFICIENT_LIVE_SYSTEM_COVERAGE"
    elif min_n<75:
        state="THIN_LIVE_SYSTEM_COVERAGE"
    elif min_n<200:
        state="DEVELOPING_LIVE_SYSTEM_COVERAGE"
    elif min_n<500:
        state="MODERATE_LIVE_SYSTEM_COVERAGE"
    else:
        state="MATURE_LIVE_SYSTEM_COVERAGE"
    sport_rows.append({
        "sport":sport,
        "research_ready_rows":int(num(r.get("research_ready_rows")) or 0),
        "observe_control_rows":int(num(r.get("observe_control_rows")) or 0),
        "minimum_side_n":min_n,
        "comparison_state":clean(r.get("comparison_state")),
        "comparison_interpretation_allowed":bool(r.get("comparison_interpretation_allowed")),
        "live_system_coverage_state":state,
        "system_coverage_review_floor_met":bool(min_n>=75),
        "generated_at":NOW.isoformat(),
    })

sport_status=pd.DataFrame(sport_rows)
sport_status.to_csv(SPORT_OUT,index=False)
sport_lookup={clean(r["sport"]):r for r in sport_rows}

def role_live_result(frame,expected):
    delta=pd.to_numeric(frame["realized_delta_vs_pregame_baseline"],errors="coerce")
    x=frame[delta.notna()].copy()
    delta=pd.to_numeric(x["realized_delta_vs_pregame_baseline"],errors="coerce")
    n=len(x)
    mean=float(delta.mean()) if n else None
    median=float(delta.median()) if n else None
    above=float((delta>0).mean()) if n else None
    mean_dir=sign(mean)
    median_dir=sign(median)
    rate_dir=sign((above-.5) if above is not None else None,0.01)
    votes=sum(v==expected for v in [mean_dir,median_dir,rate_dir])
    opposite="NEGATIVE" if expected=="POSITIVE" else "POSITIVE"
    opposite_votes=sum(v==opposite for v in [mean_dir,median_dir,rate_dir])
    gate=sample_gate(n)
    if n>=75:
        if votes>=2: gate+="_CONSISTENT"
        elif opposite_votes>=2: gate+="_CONTRADICTED"
        else: gate+="_MIXED"
    return {
        "live_n":n,"live_mean_delta":mean,"live_median_delta":median,
        "live_above_baseline_rate":above,"live_directional_votes":votes,
        "live_opposite_votes":opposite_votes,"live_validation_gate":gate,
    }

def defense_live_result(frame):
    p=frame[frame["current_opponent_context"].astype(str)=="STRONG_PERMISSIVE_PROFILE"].copy()
    s=frame[frame["current_opponent_context"].astype(str)=="STRONG_SUPPRESSIVE_PROFILE"].copy()
    pdlt=pd.to_numeric(p["realized_delta_vs_pregame_baseline"],errors="coerce").dropna()
    sdlt=pd.to_numeric(s["realized_delta_vs_pregame_baseline"],errors="coerce").dropna()
    pn=len(pdlt); sn=len(sdlt); n=min(pn,sn)
    if pn and sn:
        mean_gap=float(pdlt.mean()-sdlt.mean())
        rate_gap=float((pdlt>0).mean()-(sdlt>0).mean())
    else:
        mean_gap=rate_gap=None
    supports_mean=mean_gap is not None and mean_gap>0
    supports_rate=rate_gap is not None and rate_gap>0
    gate=sample_gate(n)
    if n>=75:
        if supports_mean and supports_rate: gate+="_CONSISTENT"
        elif not supports_mean and not supports_rate: gate+="_CONTRADICTED"
        else: gate+="_MIXED"
    return {
        "live_n":n,"live_permissive_n":pn,"live_suppressive_n":sn,
        "live_mean_gap":mean_gap,"live_above_rate_gap":rate_gap,
        "live_directional_votes":int(supports_mean)+int(supports_rate),
        "live_opposite_votes":int(mean_gap is not None and mean_gap<=0)+int(rate_gap is not None and rate_gap<=0),
        "live_validation_gate":gate,
    }

def change_state(hist_state,live_gate,live_n,system_floor):
    if hist_state in {"HISTORICAL_CONTRADICTED","HISTORICAL_MIXED","HISTORICAL_NOT_SUPPORTED","REFERENCE_ONLY"}:
        return "NOT_ELIGIBLE_HISTORICAL_EVIDENCE",False
    if live_n==0:
        return "SHADOW_AWAITING_LIVE_VALIDATION",False
    if live_n<75:
        return "SHADOW_THIN_LIVE_SAMPLE",False
    if "CONTRADICTED" in live_gate:
        return "HOLD_LIVE_CONTRADICTION",False
    if "MIXED" in live_gate:
        return "HOLD_LIVE_MIXED_EVIDENCE",False
    if "CONSISTENT" not in live_gate:
        return "SHADOW_LIVE_DIRECTION_UNRESOLVED",False
    if not system_floor:
        return "SHADOW_NEEDS_SYSTEM_LIVE_COVERAGE",False
    if hist_state!="MATURE_HISTORICAL_SUPPORT":
        return "SHADOW_NEEDS_HISTORICAL_MATURITY",False
    if live_n<200:
        return "SHADOW_DEVELOPING_LIVE_VALIDATION",False
    return "ELIGIBLE_FOR_MANUAL_CHANGE_REVIEW",True

registry_rows=[]
role_candidates=factors[
    (factors["factor_type"].astype(str)=="ROLE_SIGNAL")
    & factors["factor_value"].astype(str).isin(["ROLE_UP","ROLE_DOWN"])
].copy()

for r in role_candidates.to_dict("records"):
    sport=clean(r.get("sport")); pos=clean(r.get("position_group")); signal=clean(r.get("factor_value"))
    expected="POSITIVE" if signal=="ROLE_UP" else "NEGATIVE"
    g=graded[
        (graded["sport"].astype(str)==sport)
        & (graded["position_group"].astype(str)==pos)
        & (graded["current_role_signal"].astype(str)==signal)
    ].copy()
    live_result=role_live_result(g,expected)
    hist_state=historical_state(r.get("evidence_gate"))
    sys=sport_lookup.get(sport,{})
    state,eligible=change_state(
        hist_state,live_result["live_validation_gate"],
        live_result["live_n"],bool(sys.get("system_coverage_review_floor_met",False)),
    )
    registry_rows.append({
        "candidate_key":f"ROLE|{sport}|{pos}|{signal}",
        "candidate_type":"ROLE_DIRECTION","sport":sport,
        "position_group":pos,"signal_state":signal,
        "historical_gate":clean(r.get("evidence_gate")),
        "historical_state":hist_state,
        "historical_n":int(num(r.get("n")) or 0),
        "historical_mean_delta":num(r.get("mean_outcome_delta")),
        "historical_above_baseline_rate":num(r.get("above_baseline_rate")),
        **live_result,
        "live_system_coverage_state":clean(sys.get("live_system_coverage_state")),
        "live_system_minimum_side_n":int(sys.get("minimum_side_n",0) or 0),
        "change_eligibility_state":state,
        "manual_change_review_eligible":eligible,
        "automatic_weight_change_allowed":False,
        "generated_at":NOW.isoformat(),
    })

for r in defense.to_dict("records"):
    sport=clean(r.get("sport")); pos=clean(r.get("position_group")); signal=clean(r.get("pregame_role_signal"))
    g=graded[
        (graded["sport"].astype(str)==sport)
        & (graded["position_group"].astype(str)==pos)
        & (graded["current_role_signal"].astype(str)==signal)
    ].copy()
    live_result=defense_live_result(g)
    hist_state=historical_state(r.get("defense_contrast_evidence_gate"))
    sys=sport_lookup.get(sport,{})
    state,eligible=change_state(
        hist_state,live_result["live_validation_gate"],
        live_result["live_n"],bool(sys.get("system_coverage_review_floor_met",False)),
    )
    registry_rows.append({
        "candidate_key":f"DEFENSE|{sport}|{pos}|{signal}",
        "candidate_type":"ROLE_CONTROLLED_DEFENSE","sport":sport,
        "position_group":pos,"signal_state":signal,
        "historical_gate":clean(r.get("defense_contrast_evidence_gate")),
        "historical_state":hist_state,
        "historical_n":int(num(r.get("minimum_side_n")) or 0),
        "historical_mean_delta":num(r.get("permissive_minus_suppressive_mean")),
        "historical_above_baseline_rate":num(r.get("permissive_minus_suppressive_above_rate")),
        **live_result,
        "live_system_coverage_state":clean(sys.get("live_system_coverage_state")),
        "live_system_minimum_side_n":int(sys.get("minimum_side_n",0) or 0),
        "change_eligibility_state":state,
        "manual_change_review_eligible":eligible,
        "automatic_weight_change_allowed":False,
        "generated_at":NOW.isoformat(),
    })

registry=pd.DataFrame(registry_rows)
registry.to_csv(REGISTRY_OUT,index=False)

policy=pd.DataFrame([
    {
        "policy_id":"HISTORICAL_MATURITY",
        "requirement":"Candidate must have mature historical support before change review.",
        "threshold":"MATURE_HISTORICAL_SUPPORT",
    },
    {
        "policy_id":"SIGNAL_LIVE_SAMPLE",
        "requirement":"Candidate must have at least 200 signal-specific graded live rows with consistent direction before change review.",
        "threshold":"live_n >= 200 and live gate CONSISTENT",
    },
    {
        "policy_id":"SYSTEM_LIVE_COVERAGE",
        "requirement":"Sport must have at least 75 graded research-ready and observe-control rows before change review.",
        "threshold":"minimum_side_n >= 75",
    },
    {
        "policy_id":"NO_AUTOMATIC_CHANGE",
        "requirement":"Eligibility only opens manual review; no data layer may change prediction weights automatically.",
        "threshold":"automatic_weight_change_allowed = false",
    },
    {
        "policy_id":"CONTRADICTION_HOLD",
        "requirement":"Live contradiction or mixed live evidence blocks change review.",
        "threshold":"HOLD_LIVE_CONTRADICTION or HOLD_LIVE_MIXED_EVIDENCE",
    },
])
policy["generated_at"]=NOW.isoformat()
policy.to_csv(POLICY_OUT,index=False)

features=pd.DataFrame([
    {
        "feature":"change_eligibility_state",
        "definition":"Governed state describing whether a signal remains shadow-only, is held by contradiction/mixed evidence, or is eligible for manual change review.",
    },
    {
        "feature":"manual_change_review_eligible",
        "definition":"True only when historical maturity, signal-specific live validation, and sport-level live coverage all meet policy floors.",
    },
    {
        "feature":"live_validation_gate",
        "definition":"Signal-specific live sample maturity and directional consistency derived from exact postgame grades.",
    },
    {
        "feature":"automatic_weight_change_allowed",
        "definition":"Always false; this layer never changes prediction weights automatically.",
    },
])
features["generated_at"]=NOW.isoformat()
features["automatic_model_adjustment"]=False
features["score_is_probability"]=False
features.to_csv(FEATURE_OUT,index=False)

sources=pd.DataFrame([
    {"source":"SIGNAL_EVIDENCE_GATES_CURRENT.csv","purpose":"historical role-signal evidence maturity","status":"ACTIVE"},
    {"source":"DEFENSE_CONTRAST_EVIDENCE_GATES.csv","purpose":"historical role-controlled defense evidence","status":"ACTIVE"},
    {"source":"POSTGAME_RESEARCH_GRADES_CURRENT.csv","purpose":"signal-specific realized live validation rows","status":"ACTIVE"},
    {"source":"RESEARCH_READY_VS_CONTROL_CURRENT.csv","purpose":"sport-level live coverage floor","status":"ACTIVE"},
    {"source":"LEARNING_MATURITY_CURRENT.csv","purpose":"cohort learning maturity context","status":"ACTIVE"},
])
sources["generated_at"]=NOW.isoformat()
sources.to_csv(SOURCE_OUT,index=False)

receipt={
    "generated_at":NOW.isoformat(),
    "candidate_rows":int(len(registry)),
    "candidate_type_counts":registry["candidate_type"].value_counts().astype(int).to_dict() if len(registry) else {},
    "historical_state_counts":registry["historical_state"].value_counts().astype(int).to_dict() if len(registry) else {},
    "change_state_counts":registry["change_eligibility_state"].value_counts().astype(int).to_dict() if len(registry) else {},
    "manual_change_review_eligible_rows":int(registry["manual_change_review_eligible"].astype(bool).sum()) if len(registry) else 0,
    "automatic_weight_change_allowed_rows":int(registry["automatic_weight_change_allowed"].astype(bool).sum()) if len(registry) else 0,
    "sport_validation_rows":int(len(sport_status)),
    "sport_system_coverage_floor_met":int(sport_status["system_coverage_review_floor_met"].astype(bool).sum()) if len(sport_status) else 0,
    "graded_live_rows":int(len(graded)),
    "automatic_model_adjustment":False,
    "prediction_weight_change_allowed":False,
    "score_is_probability":False,
    "paid_provider_required":False,
    "explicit_gaps":[
        "No signal can enter manual change review until signal-specific live grades reach policy sample floors.",
        "Sport-level ready-vs-control coverage is a governance prerequisite, not proof that an individual signal works.",
        "Raw opponent-context factors with role confounding are excluded from change candidates; role-controlled defense contrasts are used instead.",
        "Eligibility for manual review is not approval to change a model and never changes prediction weights automatically.",
    ],
}
RECEIPT_OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True))

print("CANDIDATES:",len(registry))
print("BY TYPE:",receipt["candidate_type_counts"])
print("HISTORICAL:",receipt["historical_state_counts"])
print("CHANGE STATES:",receipt["change_state_counts"])
print("MANUAL REVIEW ELIGIBLE:",receipt["manual_change_review_eligible_rows"])
print("AUTO WEIGHT CHANGES:",receipt["automatic_weight_change_allowed_rows"])
print("SPORT COVERAGE FLOOR MET:",receipt["sport_system_coverage_floor_met"])
print("GRADED LIVE ROWS:",receipt["graded_live_rows"])
print("RESULT: LEARNING_GOVERNANCE_READY")
