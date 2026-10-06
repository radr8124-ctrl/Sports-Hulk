#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import math
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
OUT=ROOT/"intelligence_warehouse"/"cohort_learning"
OUT.mkdir(parents=True,exist_ok=True)

GRADES=ROOT/"intelligence_warehouse"/"postgame_grading"/"POSTGAME_RESEARCH_GRADES_CURRENT.csv"

PERF_OUT=OUT/"COHORT_PERFORMANCE_CURRENT.csv"
COMPARE_OUT=OUT/"RESEARCH_READY_VS_CONTROL_CURRENT.csv"
MATURITY_OUT=OUT/"LEARNING_MATURITY_CURRENT.csv"
SOURCE_OUT=OUT/"COHORT_LEARNING_SOURCE_CATALOG.csv"
FEATURE_OUT=OUT/"COHORT_LEARNING_FEATURE_CATALOG.csv"
RECEIPT_OUT=OUT/"COHORT_LEARNING_RECEIPT.json"

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

def sample_gate(n):
    n=int(n or 0)
    if n>=500: return "MATURE_POSTGAME_SAMPLE"
    if n>=200: return "MODERATE_POSTGAME_SAMPLE"
    if n>=75: return "DEVELOPING_POSTGAME_SAMPLE"
    if n>=25: return "THIN_POSTGAME_SAMPLE"
    return "INSUFFICIENT_POSTGAME_SAMPLE"
d=pd.read_csv(GRADES,low_memory=False)
graded=d[d["graded"].fillna(False).astype(bool)].copy()

perf_rows=[]
if not graded.empty:
    for keys,g in graded.groupby(["sport","cohort_class","role_metric"],dropna=False):
        sport,cohort,role_metric=keys
        delta=pd.to_numeric(g["realized_delta_vs_pregame_baseline"],errors="coerce")
        align=g["directional_alignment"].astype(str)
        directional=align.isin(["ALIGNED","NOT_ALIGNED"])
        perf_rows.append({
            "sport":clean(sport),
            "cohort_class":clean(cohort),
            "role_metric":clean(role_metric),
            "graded_rows":int(len(g)),
            "unique_events":int(g["event_id"].nunique()),
            "mean_delta_vs_pregame_baseline":float(delta.mean()) if delta.notna().any() else None,
            "median_delta_vs_pregame_baseline":float(delta.median()) if delta.notna().any() else None,
            "above_baseline_rate":float((delta>0).mean()) if delta.notna().any() else None,
            "below_baseline_rate":float((delta<0).mean()) if delta.notna().any() else None,
            "directional_test_rows":int(directional.sum()),
            "directional_alignment_rate":float((align[directional]=="ALIGNED").mean()) if directional.any() else None,
            "sample_gate":sample_gate(len(g)),
            "generated_at":NOW.isoformat(),
        })

PERF_COLUMNS=[
    "sport","cohort_class","role_metric","graded_rows","unique_events",
    "mean_delta_vs_pregame_baseline","median_delta_vs_pregame_baseline",
    "above_baseline_rate","below_baseline_rate","directional_test_rows",
    "directional_alignment_rate","sample_gate","generated_at",
]
performance=pd.DataFrame(perf_rows,columns=PERF_COLUMNS)
performance.to_csv(PERF_OUT,index=False)
compare_rows=[]
sports=sorted({clean(x) for x in d["sport"].dropna().astype(str)})
for sport in sports:
    sg=graded[graded["sport"].astype(str)==sport].copy()
    ready=sg[sg["cohort_class"].astype(str)=="RESEARCH_READY"].copy()
    control=sg[sg["cohort_class"].astype(str)=="OBSERVE_CONTROL"].copy()

    ready_delta=pd.to_numeric(ready["realized_delta_vs_pregame_baseline"],errors="coerce")
    control_delta=pd.to_numeric(control["realized_delta_vs_pregame_baseline"],errors="coerce")

    ready_n=int(ready_delta.notna().sum())
    control_n=int(control_delta.notna().sum())
    min_n=min(ready_n,control_n)

    if ready_n and control_n:
        ready_mean=float(ready_delta.mean())
        control_mean=float(control_delta.mean())
        ready_above=float((ready_delta>0).mean())
        control_above=float((control_delta>0).mean())
        mean_gap=ready_mean-control_mean
        above_gap=ready_above-control_above
    else:
        ready_mean=control_mean=ready_above=control_above=mean_gap=above_gap=None

    if min_n<25:
        comparison_state="INSUFFICIENT_POSTGAME_SAMPLE"
    elif min_n<75:
        comparison_state="THIN_COMPARISON_SAMPLE"
    elif min_n<200:
        comparison_state="DEVELOPING_COMPARISON_SAMPLE"
    elif min_n<500:
        comparison_state="MODERATE_COMPARISON_SAMPLE"
    else:
        comparison_state="MATURE_COMPARISON_SAMPLE"

    compare_rows.append({
        "sport":sport,
        "research_ready_rows":ready_n,
        "observe_control_rows":control_n,
        "minimum_side_n":min_n,
        "research_ready_mean_delta":ready_mean,
        "observe_control_mean_delta":control_mean,
        "research_ready_minus_control_mean":mean_gap,
        "research_ready_above_baseline_rate":ready_above,
        "observe_control_above_baseline_rate":control_above,
        "research_ready_minus_control_above_rate":above_gap,
        "comparison_state":comparison_state,
        "comparison_interpretation_allowed":bool(min_n>=75),
        "generated_at":NOW.isoformat(),
    })

COMPARE_COLUMNS=[
    "sport","research_ready_rows","observe_control_rows","minimum_side_n",
    "research_ready_mean_delta","observe_control_mean_delta",
    "research_ready_minus_control_mean","research_ready_above_baseline_rate",
    "observe_control_above_baseline_rate","research_ready_minus_control_above_rate",
    "comparison_state","comparison_interpretation_allowed","generated_at",
]
comparison=pd.DataFrame(compare_rows,columns=COMPARE_COLUMNS)
comparison.to_csv(COMPARE_OUT,index=False)
maturity_rows=[]
for keys,g in d.groupby(["sport","cohort_class"],dropna=False):
    sport,cohort=keys
    graded_mask=g["graded"].fillna(False).astype(bool)
    n_total=int(len(g))
    n_graded=int(graded_mask.sum())
    n_pending=int((g["grade_status"].astype(str)=="NOT_GRADED_YET").sum())
    n_not_modeled=int((g["grade_status"].astype(str)=="SPORT_NOT_GRADED").sum())
    gate=sample_gate(n_graded)
    maturity_rows.append({
        "sport":clean(sport),
        "cohort_class":clean(cohort),
        "tracked_rows":n_total,
        "graded_rows":n_graded,
        "pending_rows":n_pending,
        "sport_not_graded_rows":n_not_modeled,
        "graded_coverage_rate":(n_graded/n_total) if n_total else None,
        "learning_sample_gate":gate,
        "learning_interpretation_allowed":bool(n_graded>=75),
        "generated_at":NOW.isoformat(),
    })

MATURITY_COLUMNS=[
    "sport","cohort_class","tracked_rows","graded_rows","pending_rows",
    "sport_not_graded_rows","graded_coverage_rate","learning_sample_gate",
    "learning_interpretation_allowed","generated_at",
]
maturity=pd.DataFrame(maturity_rows,columns=MATURITY_COLUMNS)
maturity.to_csv(MATURITY_OUT,index=False)

features=pd.DataFrame([
    {
        "feature":"sample_gate",
        "definition":"Postgame sample maturity for a cohort/role-metric group; interpretation is blocked below the configured minimum.",
    },
    {
        "feature":"research_ready_minus_control_mean",
        "definition":"Difference in realized primary-role delta between research-ready and observe-control cohorts; descriptive only and interpreted only after minimum sample gates are met.",
    },
    {
        "feature":"comparison_interpretation_allowed",
        "definition":"True only when both research-ready and observe-control sides have at least 75 graded rows.",
    },
    {
        "feature":"learning_sample_gate",
        "definition":"Tracked/graded maturity state for each sport and cohort class.",
    },
])
features["generated_at"]=NOW.isoformat()
features["automatic_model_adjustment"]=False
features["score_is_probability"]=False
features.to_csv(FEATURE_OUT,index=False)

sources=pd.DataFrame([
    {
        "source":"POSTGAME_RESEARCH_GRADES_CURRENT.csv",
        "purpose":"graded and pending realized outcomes for frozen pregame research cohorts",
        "status":"ACTIVE",
    },
])
sources["generated_at"]=NOW.isoformat()
sources.to_csv(SOURCE_OUT,index=False)
receipt={
    "generated_at":NOW.isoformat(),
    "input_grade_rows":int(len(d)),
    "graded_rows":int(len(graded)),
    "performance_rows":int(len(performance)),
    "comparison_rows":int(len(comparison)),
    "maturity_rows":int(len(maturity)),
    "comparison_state_counts":comparison["comparison_state"].value_counts().astype(int).to_dict() if len(comparison) else {},
    "learning_gate_counts":maturity["learning_sample_gate"].value_counts().astype(int).to_dict() if len(maturity) else {},
    "interpretable_comparison_rows":int(comparison["comparison_interpretation_allowed"].astype(bool).sum()) if len(comparison) else 0,
    "interpretable_learning_rows":int(maturity["learning_interpretation_allowed"].astype(bool).sum()) if len(maturity) else 0,
    "automatic_model_adjustment":False,
    "prediction_weight_change_allowed":False,
    "score_is_probability":False,
    "paid_provider_required":False,
    "explicit_gaps":[
        "No cohort performance conclusion is permitted until completed postgame rows meet the configured sample gate.",
        "Research-ready vs observe-control comparison requires at least 75 graded rows on both sides within a sport before interpretation is allowed.",
        "MLB player-level grading is active, but interpretation remains blocked until completed live cohorts meet the configured sample gates.",
        "Cohort learning summaries are descriptive evidence only and do not alter prediction, recommendation, or ranking weights automatically.",
    ],
}
RECEIPT_OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True))

print("INPUT GRADES:",len(d))
print("GRADED:",len(graded))
print("PERFORMANCE ROWS:",len(performance))
print("COMPARISON ROWS:",len(comparison))
print("MATURITY ROWS:",len(maturity))
print("COMPARISON STATES:",receipt["comparison_state_counts"])
print("LEARNING GATES:",receipt["learning_gate_counts"])
print("INTERPRETABLE COMPARISONS:",receipt["interpretable_comparison_rows"])
print("INTERPRETABLE LEARNING GROUPS:",receipt["interpretable_learning_rows"])
print("RESULT: COHORT_LEARNING_READY")
