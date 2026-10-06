#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import math
import re

import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
OUT=ROOT/"intelligence_warehouse"/"signal_consensus"
OUT.mkdir(parents=True,exist_ok=True)

EVIDENCE_FILE=ROOT/"intelligence_warehouse"/"evidence_gates"/"PLAYER_EVIDENCE_CONTEXT_CURRENT.csv"
OPP_FILE=ROOT/"intelligence_warehouse"/"player_opportunity"/"PLAYER_OPPORTUNITY_CONTEXT_CURRENT.csv"
NEWS_PLAYER_FILE=ROOT/"intelligence_warehouse"/"news_graph"/"NEWS_PLAYER_CONTEXT_CURRENT.csv"
NEWS_NODE_FILE=ROOT/"intelligence_warehouse"/"news_graph"/"NEWS_EVENT_NODES_CURRENT.csv"

CURRENT_OUT=OUT/"PLAYER_SIGNAL_CONSENSUS_CURRENT.csv"
CONFLICT_OUT=OUT/"PLAYER_SIGNAL_CONFLICTS_CURRENT.csv"
SUMMARY_OUT=OUT/"SIGNAL_CONSENSUS_SUMMARY.csv"
SOURCE_OUT=OUT/"SIGNAL_CONSENSUS_SOURCE_CATALOG.csv"
FEATURE_OUT=OUT/"SIGNAL_CONSENSUS_FEATURE_CATALOG.csv"
RECEIPT_OUT=OUT/"SIGNAL_CONSENSUS_RECEIPT.json"

NOW=datetime.now(timezone.utc)
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

def norm(value):
    return re.sub(r"[^a-z0-9]+","",clean(value).lower())

def num(value):
    try:
        x=float(value)
        return None if math.isnan(x) else x
    except Exception:
        return None

def direction_label(value):
    if value>0: return "POSITIVE"
    if value<0: return "NEGATIVE"
    return "NEUTRAL"

def role_direction(role_signal,supported):
    if not supported:
        return 0,"ROLE_DIRECTION_NOT_HISTORICALLY_SUPPORTED"
    signal=clean(role_signal)
    if signal=="ROLE_UP":
        return 1,"HISTORICALLY_SUPPORTED_ROLE_UP"
    if signal=="ROLE_DOWN":
        return -1,"HISTORICALLY_SUPPORTED_ROLE_DOWN"
    return 0,"ROLE_REFERENCE_OR_NO_DIRECTION"

def defense_direction(context,supported):
    if not supported:
        return 0,"DEFENSE_DIRECTION_NOT_ROLE_CONTROLLED_SUPPORTED"
    value=clean(context)
    if "PERMISSIVE" in value:
        return 1,"ROLE_CONTROLLED_PERMISSIVE_DEFENSE_SUPPORT"
    if "SUPPRESSIVE" in value:
        return -1,"ROLE_CONTROLLED_SUPPRESSIVE_DEFENSE_CONSTRAINT"
    return 0,"ROLE_CONTROLLED_DEFENSE_NEUTRAL_OR_MIXED"

def market_direction(signal):
    value=clean(signal)
    if value in {"ADD_ACTIVITY","TOP_25_ADD_ACTIVITY"}:
        return 1,"UNCALIBRATED_ADD_ACTIVITY"
    if value in {"DROP_ACTIVITY","TOP_25_DROP_ACTIVITY"}:
        return -1,"UNCALIBRATED_DROP_ACTIVITY"
    if value in {"ADD_AND_DROP_ACTIVITY","TOP_ADD_AND_DROP_ACTIVITY"}:
        return 0,"UNCALIBRATED_MARKET_CONFLICT"
    if value=="SEVEN_DAY_ACTIVITY_ONLY":
        return 0,"UNCALIBRATED_SEVEN_DAY_ACTIVITY"
    return 0,"NO_MARKET_ACTIVITY_CONTEXT"

def style_direction(value):
    v=clean(value)
    if v in {"POSITION_STYLE_SUPPORT","IDP_VOLUME_SUPPORT","EVENT_VOLUME_SUPPORT"}:
        return 1,"UNCALIBRATED_STYLE_SUPPORT"
    if v in {"POSITION_STYLE_CONSTRAINT","IDP_VOLUME_CONSTRAINT","EVENT_VOLUME_CONSTRAINT"}:
        return -1,"UNCALIBRATED_STYLE_CONSTRAINT"
    return 0,"STYLE_NEUTRAL_OR_NOT_MODELED"
evidence=pd.read_csv(EVIDENCE_FILE,low_memory=False)
opportunity=pd.read_csv(OPP_FILE,low_memory=False)
news_player=pd.read_csv(NEWS_PLAYER_FILE,low_memory=False)
news_nodes=pd.read_csv(NEWS_NODE_FILE,low_memory=False)

base=evidence.merge(
    opportunity[[
        "sport","opportunity_identity_key","role_metric","market_activity_signal",
        "market_net_adds_24h","market_net_adds_168h","environment_signal",
        "position_style_context","starter_state","starter_role",
        "availability_status","availability_source_disagreement",
        "market_join_method","availability_join_method","matchup_coverage_status"
    ]],
    on=["sport","opportunity_identity_key"],
    how="left",
)

news_enriched=news_player.merge(
    news_nodes[[
        "event_node_id","published_or_effective_at","source","source_tier",
        "event_type","verified_status","provenance_status"
    ]],
    on="event_node_id",
    how="left",
)

news_by_key={}
for (sport,pkey),g in news_enriched.groupby(["sport","player_key"],dropna=False):
    if clean(pkey):
        news_by_key[(clean(sport),clean(pkey))]=g.copy()

news_by_name={}
for sport,g0 in news_enriched[news_enriched["sport"].astype(str)=="NBA"].groupby("sport"):
    for name,g in g0.groupby(g0["player"].map(norm)):
        if name:
            news_by_name[("NBA",name)]=g.copy()

def news_context_for(row):
    sport=clean(row.get("sport"))
    if sport in {"NFL","MLB"}:
        g=news_by_key.get((sport,clean(row.get("player_key"))))
        method="PLAYER_KEY"
    elif sport=="NBA":
        g=news_by_name.get(("NBA",norm(row.get("player"))))
        method="EXACT_NORMALIZED_PLAYER_NAME"
    else:
        g=None
        method="NO_SAFE_NEWS_IDENTITY_JOIN"

    if g is None or g.empty:
        return {
            "news_event_count":0,
            "news_join_method":method,
            "news_corroboration_status":"NO_LINKED_NEWS_CONTEXT",
            "news_contexts":"",
            "news_availability_states":"",
            "news_role_states":"",
            "news_source_disagreement":False,
            "latest_news_at":"",
        }

    contexts=sorted({clean(x) for x in g["combined_research_context"] if clean(x)})
    avails=sorted({clean(x) for x in g["availability_status"] if clean(x)})
    roles=sorted({clean(x) for x in g["role_signal"] if clean(x)})
    times=pd.to_datetime(g["published_or_effective_at"],errors="coerce",utc=True,format="mixed")
    latest=(times.max().isoformat() if times.notna().any() else "")
    disagreement=bool(g["source_disagreement"].fillna(False).astype(bool).any())
    return {
        "news_event_count":int(g["event_node_id"].nunique()),
        "news_join_method":method,
        "news_corroboration_status":"LINKED_NEWS_CONTEXT",
        "news_contexts":"|".join(contexts),
        "news_availability_states":"|".join(avails),
        "news_role_states":"|".join(roles),
        "news_source_disagreement":disagreement,
        "latest_news_at":latest,
    }
def operational_gate(row):
    avail=clean(row.get("availability_context"))
    status=clean(row.get("availability_status")).upper()
    disagreement=bool(row.get("availability_source_disagreement"))
    if avail=="AVAILABILITY_LIMITED" or status in {"OUT","IR","PUP","INACTIVE","DOUBTFUL","SUSPENDED"}:
        return "HARD_AVAILABILITY_BLOCK"
    if avail=="AVAILABILITY_RISK" or status in {"QUESTIONABLE","DAY_TO_DAY"}:
        return "AVAILABILITY_RISK"
    if avail=="AVAILABILITY_UNCERTAIN":
        return "AVAILABILITY_UNCERTAIN"
    if disagreement:
        return "AVAILABILITY_SOURCE_DISAGREEMENT"
    return "NO_AVAILABILITY_BLOCK"

def starter_confirmation(row):
    state=clean(row.get("starter_state"))
    if state in {"PROBABLE_OFFICIAL","CONFIRMED_OFFICIAL","CONFIRMED_SOURCE"}:
        return True,state
    return False,state or "NO_STARTER_CONTEXT"

def supported_consensus(role_dir,defense_dir,op_gate,no_upcoming,invalid):
    pos=sum(x>0 for x in [role_dir,defense_dir])
    neg=sum(x<0 for x in [role_dir,defense_dir])
    if no_upcoming:
        return "NO_UPCOMING_MODELED_GAME",pos,neg
    if invalid:
        return "INVALID_PLAYER_IDENTITY",pos,neg
    if op_gate=="HARD_AVAILABILITY_BLOCK":
        return "HARD_AVAILABILITY_BLOCK",pos,neg
    if pos and neg:
        return "SUPPORTED_EVIDENCE_CONFLICT",pos,neg
    if pos>=2:
        return "MULTI_CHANNEL_SUPPORTED_POSITIVE",pos,neg
    if neg>=2:
        return "MULTI_CHANNEL_SUPPORTED_NEGATIVE",pos,neg
    if pos==1:
        return "SINGLE_SUPPORTED_POSITIVE",pos,neg
    if neg==1:
        return "SINGLE_SUPPORTED_NEGATIVE",pos,neg
    return "NO_SUPPORTED_DIRECTIONAL_CONSENSUS",pos,neg

def conflict_types(row,role_dir,defense_dir,market_dir,style_dir,op_gate):
    conflicts=[]
    if role_dir and defense_dir and role_dir!=defense_dir:
        conflicts.append("SUPPORTED_ROLE_VS_DEFENSE_CONFLICT")
    supported_dir=role_dir if role_dir else defense_dir
    if role_dir and defense_dir and role_dir==defense_dir:
        supported_dir=role_dir
    elif role_dir and defense_dir and role_dir!=defense_dir:
        supported_dir=0
    if supported_dir and market_dir and supported_dir!=market_dir:
        conflicts.append("SUPPORTED_EVIDENCE_VS_UNCALIBRATED_MARKET")
    if supported_dir and style_dir and supported_dir!=style_dir:
        conflicts.append("SUPPORTED_EVIDENCE_VS_UNCALIBRATED_STYLE")
    if clean(row.get("market_activity_signal")) in {"ADD_AND_DROP_ACTIVITY","TOP_ADD_AND_DROP_ACTIVITY"}:
        conflicts.append("MARKET_INTERNAL_CONFLICT")
    if op_gate=="HARD_AVAILABILITY_BLOCK" and (role_dir>0 or defense_dir>0 or market_dir>0 or style_dir>0):
        conflicts.append("POSITIVE_CONTEXT_BLOCKED_BY_AVAILABILITY")
    if bool(row.get("availability_source_disagreement")):
        conflicts.append("AVAILABILITY_SOURCE_DISAGREEMENT")
    return sorted(set(conflicts))

MATURITY_RANK={"NONE":0,"THIN":1,"DEVELOPING":2,"MODERATE":3,"MATURE":4}

def gate_maturity(gate):
    value=clean(gate)
    for prefix in ["MATURE","MODERATE","DEVELOPING","THIN"]:
        if value.startswith(prefix):
            return prefix
    return "NONE"

def consensus_maturity(role_dir,defense_dir,role_gate,defense_gate):
    levels=[]
    if role_dir:
        levels.append(gate_maturity(role_gate))
    if defense_dir:
        levels.append(gate_maturity(defense_gate))
    if not levels:
        return "NO_SUPPORTED_DIRECTIONAL_CHANNELS","NONE","NONE"
    ranks=[MATURITY_RANK[x] for x in levels]
    floor=min(ranks)
    ceil=max(ranks)
    inverse={v:k for k,v in MATURITY_RANK.items()}
    scope="MULTI_CHANNEL" if len(levels)>=2 else "SINGLE_CHANNEL"
    return (
        f"{inverse[floor]}_{scope}_EVIDENCE",
        inverse[floor],
        inverse[ceil],
    )

def conflict_priority(conflicts,op_gate,invalid=False):
    c=set(conflicts)
    if invalid:
        return "INVALID_PLAYER_IDENTITY"
    if op_gate=="HARD_AVAILABILITY_BLOCK":
        return "OPERATIONAL_BLOCK"
    if "SUPPORTED_ROLE_VS_DEFENSE_CONFLICT" in c:
        return "SUPPORTED_EVIDENCE_CONFLICT"
    if "AVAILABILITY_SOURCE_DISAGREEMENT" in c:
        return "AVAILABILITY_SOURCE_CONFLICT"
    if "NEWS_CONTEXT_SOURCE_DISAGREEMENT" in c:
        return "NEWS_SOURCE_CONFLICT"
    if c & {
        "SUPPORTED_EVIDENCE_VS_UNCALIBRATED_MARKET",
        "SUPPORTED_EVIDENCE_VS_UNCALIBRATED_STYLE",
    }:
        return "SUPPORTED_VS_UNCALIBRATED_CROSSCHECK"
    if "MARKET_INTERNAL_CONFLICT" in c:
        return "UNCALIBRATED_MARKET_CONFLICT"
    if op_gate in {"AVAILABILITY_RISK","AVAILABILITY_UNCERTAIN"}:
        return "AVAILABILITY_CAUTION"
    return "NO_CONFLICT"

rows=[]
for row in base.to_dict("records"):
    role_supported=bool(row.get("role_direction_historically_supported"))
    defense_supported=bool(row.get("role_controlled_defense_historically_supported"))
    role_dir,role_basis=role_direction(row.get("current_role_signal"),role_supported)
    defense_dir,defense_basis=defense_direction(row.get("current_opponent_context"),defense_supported)
    market_dir,market_basis=market_direction(row.get("market_activity_signal"))
    style_dir,style_basis=style_direction(row.get("position_style_context"))
    op_gate=operational_gate(row)
    starter_ok,starter_state=starter_confirmation(row)

    no_upcoming=clean(row.get("matchup_coverage_status"))=="NO_UPCOMING_MODELED_GAME"
    invalid=clean(row.get("evidence_readiness"))=="INVALID_PLAYER_IDENTITY"
    consensus_state,pos_count,neg_count=supported_consensus(
        role_dir,defense_dir,op_gate,no_upcoming,invalid
    )
    conflicts=conflict_types(
        row,role_dir,defense_dir,market_dir,style_dir,op_gate
    )
    consensus_maturity_state,maturity_floor,maturity_ceiling=consensus_maturity(
        role_dir,
        defense_dir,
        row.get("role_evidence_gate"),
        row.get("defense_contrast_evidence_gate"),
    )
    news=news_context_for(row)
    if news.get("news_source_disagreement"):
        conflicts=sorted(set(conflicts+["NEWS_CONTEXT_SOURCE_DISAGREEMENT"]))
    priority=conflict_priority(conflicts,op_gate,invalid=invalid)

    role_and_defense_agree=(
        role_dir!=0 and defense_dir!=0 and role_dir==defense_dir
    )
    role_and_defense_conflict=(
        role_dir!=0 and defense_dir!=0 and role_dir!=defense_dir
    )

    if pos_count>0 and neg_count==0:
        supported_direction="POSITIVE"
    elif neg_count>0 and pos_count==0:
        supported_direction="NEGATIVE"
    elif pos_count>0 and neg_count>0:
        supported_direction="CONFLICT"
    else:
        supported_direction="NEUTRAL_OR_UNSUPPORTED"

    rows.append({
        "sport":clean(row.get("sport")),
        "opportunity_identity_key":clean(row.get("opportunity_identity_key")),
        "player_key":clean(row.get("player_key")),
        "player":clean(row.get("player")),
        "team":clean(row.get("team")),
        "position":clean(row.get("position")),
        "event_id":clean(row.get("event_id")),
        "start":clean(row.get("start")),
        "opponent":clean(row.get("opponent")),
        "availability_context":clean(row.get("availability_context")),
        "availability_status":clean(row.get("availability_status")),
        "operational_gate":op_gate,
        "current_role_signal":clean(row.get("current_role_signal")),
        "role_evidence_gate":clean(row.get("role_evidence_gate")),
        "role_direction_historically_supported":role_supported,
        "role_direction":direction_label(role_dir),
        "role_direction_basis":role_basis,
        "current_opponent_context":clean(row.get("current_opponent_context")),
        "defense_contrast_evidence_gate":clean(row.get("defense_contrast_evidence_gate")),
        "role_controlled_defense_historically_supported":defense_supported,
        "defense_direction":direction_label(defense_dir),
        "defense_direction_basis":defense_basis,
        "market_activity_signal":clean(row.get("market_activity_signal")),
        "market_direction":direction_label(market_dir),
        "market_direction_basis":market_basis,
        "position_style_context":clean(row.get("position_style_context")),
        "style_direction":direction_label(style_dir),
        "style_direction_basis":style_basis,
        "starter_confirmed_or_probable":starter_ok,
        "starter_state":starter_state,
        "evidence_readiness":clean(row.get("evidence_readiness")),
        "supported_positive_channel_count":pos_count,
        "supported_negative_channel_count":neg_count,
        "supported_direction":supported_direction,
        "role_and_defense_agree":role_and_defense_agree,
        "role_and_defense_conflict":role_and_defense_conflict,
        "consensus_state":consensus_state,
        "consensus_maturity":consensus_maturity_state,
        "supported_maturity_floor":maturity_floor,
        "supported_maturity_ceiling":maturity_ceiling,
        "conflict_priority":priority,
        "conflict_count":len(conflicts),
        "conflict_types":"|".join(conflicts),
        **news,
        "generated_at":NOW.isoformat(),
        "automatic_model_adjustment":False,
        "score_is_probability":False,
        "weighted_consensus_score_created":False,
    })

current=pd.DataFrame(rows)
conflict_mask=(
    (current["conflict_count"]>0)
    | current["consensus_state"].isin([
        "SUPPORTED_EVIDENCE_CONFLICT",
        "HARD_AVAILABILITY_BLOCK",
        "INVALID_PLAYER_IDENTITY",
    ])
    | current["operational_gate"].isin([
        "AVAILABILITY_RISK",
        "AVAILABILITY_UNCERTAIN",
        "AVAILABILITY_SOURCE_DISAGREEMENT",
    ])
    | current["news_source_disagreement"].astype(bool)
)
conflicts=current[conflict_mask].copy()

summary_rows=[]
for (sport,state),g in current.groupby(["sport","consensus_state"],dropna=False):
    summary_rows.append({
        "sport":clean(sport),
        "consensus_state":clean(state),
        "player_rows":len(g),
        "hard_availability_blocks":int((g["operational_gate"]=="HARD_AVAILABILITY_BLOCK").sum()),
        "availability_risk_rows":int((g["operational_gate"]=="AVAILABILITY_RISK").sum()),
        "rows_with_conflicts":int((g["conflict_count"]>0).sum()),
        "rows_with_linked_news":int((g["news_event_count"]>0).sum()),
        "rows_with_starter_confirmation":int(g["starter_confirmed_or_probable"].astype(bool).sum()),
        "historically_supported_role_rows":int(g["role_direction_historically_supported"].astype(bool).sum()),
        "historically_supported_defense_rows":int(g["role_controlled_defense_historically_supported"].astype(bool).sum()),
        "generated_at":NOW.isoformat(),
    })
summary=pd.DataFrame(summary_rows)
features=pd.DataFrame([
    {
        "feature":"consensus_state",
        "definition":"Categorical agreement/conflict state across historically supported role and defense channels, with hard availability blocks taking precedence.",
        "calibrated_directional_channels":"ROLE|ROLE_CONTROLLED_DEFENSE",
    },
    {
        "feature":"operational_gate",
        "definition":"Availability-driven operational state such as hard block, risk, uncertainty, or no block.",
        "calibrated_directional_channels":"NOT_APPLICABLE_OPERATIONAL_FACT",
    },
    {
        "feature":"consensus_maturity",
        "definition":"Minimum/maximum historical evidence maturity across the supported directional channels used in the current consensus.",
        "calibrated_directional_channels":"ROLE|ROLE_CONTROLLED_DEFENSE",
    },
    {
        "feature":"conflict_priority",
        "definition":"Categorical priority separating operational blocks, supported-evidence conflicts, source conflicts, and uncalibrated cross-check disagreements.",
        "calibrated_directional_channels":"MIXED",
    },
    {
        "feature":"conflict_types",
        "definition":"Named conflicts between supported evidence and other channels; no weighted score is produced.",
        "calibrated_directional_channels":"MIXED",
    },
    {
        "feature":"news_corroboration_status",
        "definition":"Safe identity-linked news provenance/context only; news is not double-counted as an independent directional vote.",
        "calibrated_directional_channels":"NOT_DIRECTIONAL",
    },
    {
        "feature":"starter_confirmed_or_probable",
        "definition":"Pregame starter/probable confirmation fact; not treated as a performance direction.",
        "calibrated_directional_channels":"NOT_DIRECTIONAL",
    },
    {
        "feature":"market_direction",
        "definition":"Fantasy-market add/drop direction retained as explicitly uncalibrated context.",
        "calibrated_directional_channels":"UNCALIBRATED",
    },
    {
        "feature":"style_direction",
        "definition":"Team/matchup style support or constraint retained as explicitly uncalibrated context.",
        "calibrated_directional_channels":"UNCALIBRATED",
    },
])
features["score_is_probability"]=False
features["automatic_model_adjustment"]=False
features["generated_at"]=NOW.isoformat()

sources=pd.DataFrame([
    {
        "source":"PLAYER_EVIDENCE_CONTEXT_CURRENT.csv",
        "purpose":"historically supported role and defense evidence gates",
        "status":"ACTIVE",
    },
    {
        "source":"PLAYER_OPPORTUNITY_CONTEXT_CURRENT.csv",
        "purpose":"availability, market, style, starter, matchup context",
        "status":"ACTIVE",
    },
    {
        "source":"NEWS_PLAYER_CONTEXT_CURRENT.csv + NEWS_EVENT_NODES_CURRENT.csv",
        "purpose":"safe news corroboration/provenance",
        "status":"ACTIVE_WITH_IDENTITY_LIMITS",
    },
])
sources["generated_at"]=NOW.isoformat()

current.to_csv(CURRENT_OUT,index=False)
conflicts.to_csv(CONFLICT_OUT,index=False)
summary.to_csv(SUMMARY_OUT,index=False)
sources.to_csv(SOURCE_OUT,index=False)
features.to_csv(FEATURE_OUT,index=False)

receipt={
    "generated_at":NOW.isoformat(),
    "current_player_rows":int(len(current)),
    "conflict_queue_rows":int(len(conflicts)),
    "summary_rows":int(len(summary)),
    "consensus_state_counts":current["consensus_state"].value_counts().astype(int).to_dict(),
    "operational_gate_counts":current["operational_gate"].value_counts().astype(int).to_dict(),
    "supported_direction_counts":current["supported_direction"].value_counts().astype(int).to_dict(),
    "consensus_maturity_counts":current["consensus_maturity"].value_counts().astype(int).to_dict(),
    "conflict_priority_counts":current["conflict_priority"].value_counts().astype(int).to_dict(),
    "conflict_type_counts":(
        pd.Series(
            [
                c
                for value in current["conflict_types"].dropna().astype(str)
                for c in value.split("|")
                if c
            ]
        ).value_counts().astype(int).to_dict()
        if len(current) else {}
    ),
    "historically_supported_role_rows":int(current["role_direction_historically_supported"].astype(bool).sum()),
    "historically_supported_defense_rows":int(current["role_controlled_defense_historically_supported"].astype(bool).sum()),
    "rows_with_linked_news":int((current["news_event_count"]>0).sum()),
    "rows_with_news_source_disagreement":int(current["news_source_disagreement"].astype(bool).sum()),
    "starter_confirmation_rows":int(current["starter_confirmed_or_probable"].astype(bool).sum()),
    "current_identity_duplicates":int(current.duplicated(["sport","opportunity_identity_key"]).sum()),
    "weighted_consensus_score_created":False,
    "explicit_gaps":[
        "NHL news corroboration is not identity-linked because the current news player naming does not safely align to the governed NHL player identities; no fuzzy join is used.",
        "NBA news corroboration uses exact normalized full-name identity only because provider player IDs are not present in the news graph.",
        "MLB has no historical role/defense calibration gate yet, so MLB role/defense direction is not counted as historically supported consensus.",
        "Fantasy-market and style directions are preserved as explicitly uncalibrated cross-checks and never promoted to supported consensus votes.",
        "Starter confirmation and news presence are confirmation/provenance facts, not performance votes.",
        "No weighted consensus score, probability, ranking adjustment, or automatic model weight is created.",
    ],
    "automatic_model_adjustment":False,
    "score_is_probability":False,
    "paid_provider_required":False,
}
RECEIPT_OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True))

print("CURRENT PLAYER CONSENSUS:",len(current))
print("CONFLICT QUEUE:",len(conflicts))
print("CONSENSUS STATES:",receipt["consensus_state_counts"])
print("OPERATIONAL GATES:",receipt["operational_gate_counts"])
print("SUPPORTED DIRECTIONS:",receipt["supported_direction_counts"])
print("CONSENSUS MATURITY:",receipt["consensus_maturity_counts"])
print("CONFLICT PRIORITY:",receipt["conflict_priority_counts"])
print("CONFLICT TYPES:",receipt["conflict_type_counts"])
print("LINKED NEWS:",receipt["rows_with_linked_news"])
print("STARTER CONFIRMATIONS:",receipt["starter_confirmation_rows"])
print("IDENTITY DUPLICATES:",receipt["current_identity_duplicates"])
print("RESULT: SIGNAL_CONSENSUS_READY")
