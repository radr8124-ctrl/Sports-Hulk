#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
OUT=ROOT/"intelligence_warehouse"/"decision_readiness"
OUT.mkdir(parents=True,exist_ok=True)

CONSENSUS_FILE=ROOT/"intelligence_warehouse"/"signal_consensus"/"PLAYER_SIGNAL_CONSENSUS_CURRENT.csv"

CURRENT_OUT=OUT/"PLAYER_DECISION_READINESS_CURRENT.csv"
READY_OUT=OUT/"RESEARCH_READY_PLAYERS_CURRENT.csv"
HOLD_OUT=OUT/"PLAYER_READINESS_REVIEW_QUEUE.csv"
SUMMARY_OUT=OUT/"DECISION_READINESS_SUMMARY.csv"
SOURCE_OUT=OUT/"DECISION_READINESS_SOURCE_CATALOG.csv"
FEATURE_OUT=OUT/"DECISION_READINESS_FEATURE_CATALOG.csv"
RECEIPT_OUT=OUT/"DECISION_READINESS_RECEIPT.json"

NOW=datetime.now(timezone.utc)

def clean(v):
    if v is None: return ""
    try:
        if pd.isna(v): return ""
    except Exception:
        pass
    return str(v).strip()

def classify(r):
    state=clean(r.get("consensus_state"))
    maturity=clean(r.get("consensus_maturity"))
    op=clean(r.get("operational_gate"))
    priority=clean(r.get("conflict_priority"))
    readiness=clean(r.get("evidence_readiness"))
    direction=clean(r.get("supported_direction"))

    if state=="INVALID_PLAYER_IDENTITY":
        return "INVALID_PLAYER_IDENTITY","INVALID_IDENTITY",False,True
    if state=="NO_UPCOMING_MODELED_GAME":
        return "NO_UPCOMING_MODELED_GAME","NO_CURRENT_EVENT",False,False
    if op=="HARD_AVAILABILITY_BLOCK":
        return "BLOCKED_AVAILABILITY","OPERATIONAL_BLOCK",False,True
    if op in {"AVAILABILITY_RISK","AVAILABILITY_UNCERTAIN"}:
        return "HOLD_AVAILABILITY_CAUTION","AVAILABILITY_CAUTION",False,True
    if priority=="AVAILABILITY_SOURCE_CONFLICT":
        return "HOLD_SOURCE_CONFLICT","AVAILABILITY_SOURCE_CONFLICT",False,True
    if state=="SUPPORTED_EVIDENCE_CONFLICT":
        return "HOLD_SUPPORTED_EVIDENCE_CONFLICT","SUPPORTED_ROLE_DEFENSE_CONFLICT",False,True
    if readiness=="NOT_YET_CALIBRATED_SPORT":
        return "DESCRIPTIVE_ONLY_UNCALIBRATED","NO_HISTORICAL_CALIBRATION",False,False

    crosscheck = priority in {
        "SUPPORTED_VS_UNCALIBRATED_CROSSCHECK",
        "UNCALIBRATED_MARKET_CONFLICT",
    }

    if state in {"MULTI_CHANNEL_SUPPORTED_POSITIVE","MULTI_CHANNEL_SUPPORTED_NEGATIVE"}:
        if maturity=="MATURE_MULTI_CHANNEL_EVIDENCE":
            lane="RESEARCH_READY_MATURE_MULTI_CHANNEL"
        elif maturity=="MODERATE_MULTI_CHANNEL_EVIDENCE":
            lane="RESEARCH_READY_MODERATE_MULTI_CHANNEL"
        else:
            return "OBSERVE_DEVELOPING_MULTI_CHANNEL","DEVELOPING_MULTI_CHANNEL_EVIDENCE",False,crosscheck
        if crosscheck:
            lane+="_WITH_UNCALIBRATED_CROSSCHECK"
        return lane,direction,True,crosscheck

    if state in {"SINGLE_SUPPORTED_POSITIVE","SINGLE_SUPPORTED_NEGATIVE"}:
        if maturity=="MATURE_SINGLE_CHANNEL_EVIDENCE":
            lane="RESEARCH_READY_MATURE_SINGLE_CHANNEL"
            if crosscheck:
                lane+="_WITH_UNCALIBRATED_CROSSCHECK"
            return lane,direction,True,crosscheck
        if maturity in {"MODERATE_SINGLE_CHANNEL_EVIDENCE","DEVELOPING_SINGLE_CHANNEL_EVIDENCE"}:
            return "OBSERVE_DEVELOPING_SINGLE_CHANNEL","DEVELOPING_SINGLE_CHANNEL_EVIDENCE",False,crosscheck
        return "OBSERVE_THIN_SINGLE_CHANNEL","THIN_SINGLE_CHANNEL_EVIDENCE",False,crosscheck

    if readiness in {"THIN_CURRENT_COMBINATION_EVIDENCE","DEVELOPING_CURRENT_COMBINATION_EVIDENCE"}:
        return "OBSERVE_THIN_OR_DEVELOPING_EVIDENCE",readiness,False,crosscheck
    if state=="NO_SUPPORTED_DIRECTIONAL_CONSENSUS":
        return "OBSERVE_NO_SUPPORTED_DIRECTION","NO_SUPPORTED_DIRECTION",False,crosscheck

    return "OBSERVE_OTHER","NO_READINESS_RULE",False,True

d=pd.read_csv(CONSENSUS_FILE,low_memory=False)
rows=[]
for r in d.to_dict("records"):
    lane,reason,research_ready,needs_review=classify(r)
    rows.append({
        "sport":clean(r.get("sport")),
        "opportunity_identity_key":clean(r.get("opportunity_identity_key")),
        "player_key":clean(r.get("player_key")),
        "player":clean(r.get("player")),
        "team":clean(r.get("team")),
        "position":clean(r.get("position")),
        "event_id":clean(r.get("event_id")),
        "start":clean(r.get("start")),
        "opponent":clean(r.get("opponent")),
        "availability_context":clean(r.get("availability_context")),
        "availability_status":clean(r.get("availability_status")),
        "operational_gate":clean(r.get("operational_gate")),
        "consensus_state":clean(r.get("consensus_state")),
        "consensus_maturity":clean(r.get("consensus_maturity")),
        "supported_direction":clean(r.get("supported_direction")),
        "conflict_priority":clean(r.get("conflict_priority")),
        "conflict_types":clean(r.get("conflict_types")),
        "evidence_readiness":clean(r.get("evidence_readiness")),
        "role_evidence_gate":clean(r.get("role_evidence_gate")),
        "defense_contrast_evidence_gate":clean(r.get("defense_contrast_evidence_gate")),
        "news_corroboration_status":clean(r.get("news_corroboration_status")),
        "starter_confirmed_or_probable":bool(r.get("starter_confirmed_or_probable")),
        "decision_readiness_lane":lane,
        "readiness_reason":reason,
        "research_ready":research_ready,
        "needs_review":needs_review,
        "prediction_weight_change_allowed":False,
        "automatic_model_adjustment":False,
        "score_is_probability":False,
        "generated_at":NOW.isoformat(),
    })

current=pd.DataFrame(rows)
ready=current[current["research_ready"].astype(bool)].copy()
review=current[current["needs_review"].astype(bool)].copy()

summary=(
    current.groupby(["sport","decision_readiness_lane"],dropna=False)
    .agg(
        player_rows=("opportunity_identity_key","size"),
        research_ready_rows=("research_ready","sum"),
        review_rows=("needs_review","sum"),
    )
    .reset_index()
)
summary["generated_at"]=NOW.isoformat()

features=pd.DataFrame([
    {
        "feature":"decision_readiness_lane",
        "definition":"Evidence-governance lane describing whether a current player context is research-ready, observe-only, conflicted, blocked, uncalibrated, or has no current event.",
    },
    {
        "feature":"research_ready",
        "definition":"True only for mature/moderate supported directional contexts without operational or supported-evidence conflicts.",
    },
    {
        "feature":"needs_review",
        "definition":"True for operational blocks, supported conflicts, source conflicts, or uncalibrated cross-check disagreements that warrant human/model inspection before downstream use.",
    },
    {
        "feature":"prediction_weight_change_allowed",
        "definition":"Always false in this layer; readiness classification does not alter prediction logic.",
    },
])
features["generated_at"]=NOW.isoformat()
features["automatic_model_adjustment"]=False
features["score_is_probability"]=False

sources=pd.DataFrame([
    {
        "source":"PLAYER_SIGNAL_CONSENSUS_CURRENT.csv",
        "purpose":"sole current-player input for readiness classification",
        "status":"ACTIVE",
    },
])
sources["generated_at"]=NOW.isoformat()

current.to_csv(CURRENT_OUT,index=False)
ready.to_csv(READY_OUT,index=False)
review.to_csv(HOLD_OUT,index=False)
summary.to_csv(SUMMARY_OUT,index=False)
sources.to_csv(SOURCE_OUT,index=False)
features.to_csv(FEATURE_OUT,index=False)

receipt={
    "generated_at":NOW.isoformat(),
    "current_rows":int(len(current)),
    "research_ready_rows":int(len(ready)),
    "review_queue_rows":int(len(review)),
    "lane_counts":current["decision_readiness_lane"].value_counts().astype(int).to_dict(),
    "research_ready_by_sport":ready["sport"].value_counts().astype(int).to_dict() if len(ready) else {},
    "review_by_sport":review["sport"].value_counts().astype(int).to_dict() if len(review) else {},
    "identity_duplicates":int(current.duplicated(["sport","opportunity_identity_key"]).sum()),
    "research_ready_operational_blocks":int((ready["operational_gate"]=="HARD_AVAILABILITY_BLOCK").sum()) if len(ready) else 0,
    "research_ready_supported_conflicts":int((ready["consensus_state"]=="SUPPORTED_EVIDENCE_CONFLICT").sum()) if len(ready) else 0,
    "research_ready_uncalibrated_sports":int((ready["evidence_readiness"]=="NOT_YET_CALIBRATED_SPORT").sum()) if len(ready) else 0,
    "automatic_model_adjustment":False,
    "prediction_weight_change_allowed":False,
    "score_is_probability":False,
    "paid_provider_required":False,
    "explicit_gaps":[
        "Readiness is evidence governance only; it is not a recommendation, ranking, pick, bet, projection, or probability.",
        "MLB remains descriptive-only until governed historical player-level calibration exists.",
        "Developing/thin NFL evidence is observe-only unless later history matures it.",
        "Uncalibrated fantasy-market/style conflicts can trigger review but do not block supported evidence by themselves.",
    ],
}
RECEIPT_OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True))

print("CURRENT READINESS:",len(current))
print("RESEARCH READY:",len(ready))
print("REVIEW QUEUE:",len(review))
print("LANES:",receipt["lane_counts"])
print("READY BY SPORT:",receipt["research_ready_by_sport"])
print("DUPS:",receipt["identity_duplicates"])
print("READY BLOCKS:",receipt["research_ready_operational_blocks"])
print("READY SUPPORTED CONFLICTS:",receipt["research_ready_supported_conflicts"])
print("READY UNCALIBRATED:",receipt["research_ready_uncalibrated_sports"])
print("RESULT: DECISION_READINESS_READY")
