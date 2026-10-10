"""Evidence-backed review gate for attempted postgame model corrections.

Do not promote models based on anecdotes or an already-inspected diagnostic.
This file only reads independently versioned historical accuracy reports.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from intelligence_warehouse.historical_recovery.nfl_prior_score_form_model import HISTORICAL, MODEL
from intelligence_warehouse.historical_recovery.nfl_error_recovery_shadow import OUTPUT

TEST_YEARS=(2022,2023,2024,2025)
CANDIDATES=(
    "low_form_market_fallback",
    "winner_disagreement_market_fallback",
    "both_guards_market_fallback",
)
SCHEMA="ZENITH_MODEL_CORRECTION_REGISTRY_V1"


def review_report(report:dict,*, historical_sha:str, original_model_sha:str,
                  report_sha:str|None=None)->dict:
    """Fail closed unless old source/model identity and pre-specified folds agree."""
    if (report.get("schema")!="ZENITH_NFL_ERROR_RECOVERY_SHADOW_V1"
        or report.get("historical_source_sha256")!=historical_sha
        or report.get("original_frozen_model_sha256")!=original_model_sha
        or report.get("candidate_live_model_deployed") is not False
        or report.get("original_frozen_2026_predictions_modified") is not False
        or report.get("independent_positive_EV_proven") is not False
        or report.get("new_future_frozen_predictions_required") is not True
        or report.get("years")!=list(TEST_YEARS)
        or report.get("independent_test_games",0)<1000
        or report.get("study_status")!="EXPLORATORY_RETROSPECTIVE_ALREADY_INSPECTED_NOT_PROSPECTIVE"):
        raise ValueError("Historical correction report fails immutable model/evidence gate")
    folds=report.get("folds")
    pooled=report.get("pooled")
    if not isinstance(folds,list) or len(folds)!=4 or not isinstance(pooled,dict):
        raise ValueError("Incomplete independent-year model comparison")
    if [f.get("season") for f in folds]!=list(TEST_YEARS):
        raise ValueError("Test folds out of order")
    if sum(f.get("test_independent_games",0) for f in folds)!=report["independent_test_games"]:
        raise ValueError("Original game-block count no longer agrees")
    for f in folds:
        if (f.get("train_seasons")!=list(range(2016,f["season"]))
            or not f.get("no_same_game_or_same_season_train_test_overlap")
            or not isinstance(f.get("results"),dict)):
            raise ValueError("Historical fold lacks strict prior-year training provenance")
    reference=pooled.get("market_original",{}).get("brier")
    if not isinstance(reference,(float,int)) or not .1<reference<.3:
        raise ValueError("Source market benchmark missing")
    # Deny optimistic pooled numbers that do not reconcile with the four
    # independently scored historical years. These are not 4,000 bet legs.
    total=report["independent_test_games"]
    for name in ("market_original","original_model",*CANDIDATES):
        try:
            recomputed=sum(f["test_independent_games"]*f["results"][name]["brier"] for f in folds)/total
            declared=pooled[name]["brier"]
        except (KeyError,TypeError,ZeroDivisionError) as exc:
            raise ValueError("Declared pooled model evidence lacks season-by-season proof") from exc
        if not isinstance(declared,(float,int)) or abs(recomputed-declared)>1.5e-6:
            raise ValueError("Pooled Brier metric conflicts with original per-season folds")
    methods=[]
    for key,description in [
        ("original_model","Historical 9-feature market-assisted NFL model"),
        ("low_form_market_fallback","Use original bookmaker no-vig when either team has fewer than three previous same-season games"),
        ("winner_disagreement_market_fallback","Use original bookmaker favorite when experimental model reverses it"),
        ("both_guards_market_fallback","Apply both unverified-market safeguards together")
    ]:
        value=pooled.get(key,{}).get("brier")
        if not isinstance(value,(int,float)) or not 0<value<1:
            raise ValueError("Candidate missing published Brier value")
        year_results=[]
        for fold in folds:
            fm=fold["results"].get(key,{})
            base=fold["results"].get("market_original",{})
            if not isinstance(fm.get("brier"),(float,int)) or not isinstance(base.get("brier"),(float,int)):
                raise ValueError("Candidate independent-year outcome missing")
            ci=fold.get("week_block_bootstrap95_market_minus_candidate_brier",{}).get(key)
            if not isinstance(ci,list) or len(ci)!=2 or not all(isinstance(v,(int,float)) for v in ci):
                raise ValueError("Candidate source independent-week interval missing")
            year_results.append({
                "season":fold["season"],
                "test_independent_games":fold["test_independent_games"],
                "market_brier":round(base["brier"],6),
                "candidate_brier":round(fm["brier"],6),
                "market_minus_candidate_brier":round(base["brier"]-fm["brier"],6),
                "week_block_95ci_market_minus_candidate":ci,
            })
        gain=reference-value
        beats_seasons=sum(r["market_minus_candidate_brier"]>0 for r in year_results)
        robust=bool(gain>0 and beats_seasons>=3
                    and year_results[-1]["market_minus_candidate_brier"]>0
                    and all(r["week_block_95ci_market_minus_candidate"][0]>0 for r in year_results))
        if gain<=0:
            state="REJECTED_NOT_BETTER_THAN_BOOKMAKER"
        elif not robust:
            state="UNPROVEN_MIXED_HISTORICAL_RESULTS"
        else:
            state="ELIGIBLE_FOR_NEW_FORWARD_SHADOW_PROPOSAL_ONLY"
        methods.append({
            "hypothesis_id":key,
            "description":description,
            "status":state,
            "independent_historical_games":report["independent_test_games"],
            "retrospective_market_brier":round(reference,7),
            "retrospective_candidate_brier":round(value,7),
            "market_minus_candidate_brier":round(gain,7),
            "better_than_book_in_historical_test_years":beats_seasons,
            "tested_years":year_results,
            "source_bookmaker_lines_originally_timestamped":False,
            "training_source_semantics_independently_verified":False,
            "causal_explanation_proven":False,
            "live_model_update_approved":False,
            "historical_results_already_inspected":True,
        })
    return {
        "schema":SCHEMA,
        "status":"POSTGAME_CORRECTIONS_REVIEWED_NOT_PROMOTED",
        "historical_accuracy_source_sha256":historical_sha,
        "original_frozen_model_sha256":original_model_sha,
        "historical_report_sha256":report_sha,
        "original_game_cohort_count":report["independent_test_games"],
        "tested_hypotheses_count":len(methods),
        "rejected_against_market_count":sum(m["status"]=="REJECTED_NOT_BETTER_THAN_BOOKMAKER" for m in methods),
        "proposed_correction_count":len(CANDIDATES),
        "rejected_proposed_corrections_count":sum(m["hypothesis_id"] in CANDIDATES
            and m["status"]=="REJECTED_NOT_BETTER_THAN_BOOKMAKER" for m in methods),
        "candidate_models":methods,
        "fresh_unseen_2026_outcomes_required":True,
        "model_weights_changed":False,
        "odds_wager_or_betting_stake_created":False,
        "original_week5_future_predictions_preserved":True,
        "promotion_allowed_without_independent_future_evidence":False,
    }


def read_registry(*, source_path=OUTPUT,original_path=HISTORICAL,model_path=MODEL):
    """Atomic-read SHA checks. Invalid evidence is an error, never a PLAY."""
    raw=Path(source_path).read_bytes()
    expected_hash=hashlib.sha256(raw).hexdigest()
    source_bytes=Path(original_path).read_bytes()
    model_bytes=Path(model_path).read_bytes()
    source_hash=hashlib.sha256(source_bytes).hexdigest()
    model_hash=hashlib.sha256(model_bytes).hexdigest()
    report=review_report(json.loads(raw),
        historical_sha=source_hash,original_model_sha=model_hash,
        report_sha=expected_hash)
    if (hashlib.sha256(Path(source_path).read_bytes()).hexdigest()!=expected_hash
        or hashlib.sha256(Path(original_path).read_bytes()).hexdigest()!=source_hash
        or hashlib.sha256(Path(model_path).read_bytes()).hexdigest()!=model_hash):
        raise RuntimeError("Original evidence changed while model lesson registry was loaded")
    return report
