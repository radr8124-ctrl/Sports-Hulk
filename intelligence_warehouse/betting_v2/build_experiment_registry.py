#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prop_intelligence.experiment_registry import (
    append_event,
    canonical_json,
    experiment_id,
    read_events,
    summarize,
    utc_now_iso,
)

OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
REG_DIR = ROOT / "intelligence_warehouse" / "experiment_registry"
REG_DIR.mkdir(parents=True, exist_ok=True)

LEDGER = REG_DIR / "SPORTS_HULK_EXPERIMENTS.jsonl"
SUMMARY = REG_DIR / "SPORTS_HULK_EXPERIMENT_SUMMARY.json"

PROP_VALIDATION = OUT_DIR / "PROP_V2_VALIDATION.json"
PROP_MODELS = OUT_DIR / "PROP_V2_MODELS.json"
PROP_CHALLENGERS = OUT_DIR / "PROP_V2_CHALLENGERS.json"
PROP_SEGMENTS = OUT_DIR / "PROP_V2_MARKET_SEGMENTS.json"
PROP_FORWARD = OUT_DIR / "PROP_V2_FORWARD_SUMMARY.json"
BEST_BETS_VALIDATION = OUT_DIR / "BETTING_V2_ALL_MARKETS_VALIDATION.json"
BEST_BETS_FORWARD = OUT_DIR / "BETTING_V2_ALL_MARKETS_FORWARD_SUMMARY.json"
BEST_BETS_CHALLENGERS = OUT_DIR / "BETTING_V2_GAME_CHALLENGERS.json"
BEST_BETS_CHALLENGER_FORWARD = OUT_DIR / "BETTING_V2_GAME_CHALLENGER_FORWARD_SUMMARY.json"
PARLAY_VALIDATION = OUT_DIR / "PARLAY_V2_VALIDATION.json"
PARLAY_FORWARD = OUT_DIR / "PARLAY_V2_FORWARD_SUMMARY.json"
DFS_SUMMARY = ROOT / "intelligence_warehouse" / "dfs_accountability" / "DFS_ACCOUNTABILITY_SUMMARY.json"
FANTASY_CURRENT = ROOT / "intelligence_warehouse" / "fantasy_accountability" / "FANTASY_V2_CURRENT.json"
FANTASY_FORWARD = ROOT / "intelligence_warehouse" / "fantasy_accountability" / "FANTASY_V2_FORWARD_SUMMARY.json"
SURVIVOR_FORWARD = ROOT / "intelligence_warehouse" / "survivor_accountability" / "SURVIVOR_V2_FORWARD_SUMMARY.json"


def read_json(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def result_signature(status, metrics, decision, reason, forward_only):
    return canonical_json({
        "status": status,
        "metrics": metrics,
        "decision": decision,
        "reason": reason,
        "forward_only": bool(forward_only),
    })


def existing_state():
    registered = set()
    latest_result = {}
    for event in read_events(LEDGER):
        exp_id = event.get("experiment_id")
        if not exp_id:
            continue
        if event.get("event_type") == "REGISTERED":
            registered.add(exp_id)
        elif event.get("event_type") == "RESULT":
            latest_result[exp_id] = result_signature(
                event.get("status"),
                event.get("metrics") or {},
                event.get("decision"),
                event.get("reason"),
                event.get("forward_only"),
            )
    return registered, latest_result


def decision_from_confidence(value):
    value = str(value or "").upper()
    if value == "SUPPORTED":
        return "CANDIDATE"
    if value in {"PROMISING_BUT_UNCERTAIN", "CALIBRATION_MEAN_ONLY"}:
        return "HOLD"
    if value in {"NO_INDEPENDENT_EDGE", "NEGATIVE_ORDERING_REJECTED"}:
        return "REJECTED"
    return "HOLD"


def ensure_experiment(spec, *, status, metrics, decision, reason, forward_only=False):
    exp_id = experiment_id(spec)
    registered, latest = ensure_experiment.state

    if exp_id not in registered:
        append_event(LEDGER, {
            "event_type": "REGISTERED",
            "schema_version": 1,
            "experiment_id": exp_id,
            "recorded_at": utc_now_iso(),
            "spec": spec,
        })
        registered.add(exp_id)

    signature = result_signature(
        status, metrics, decision, reason, forward_only
    )
    if latest.get(exp_id) != signature:
        append_event(LEDGER, {
            "event_type": "RESULT",
            "schema_version": 1,
            "experiment_id": exp_id,
            "recorded_at": utc_now_iso(),
            "status": status,
            "metrics": metrics,
            "decision": decision,
            "reason": reason,
            "forward_only": bool(forward_only),
        })
        latest[exp_id] = signature

    return exp_id


ensure_experiment.state = existing_state()


def register_prop_core():
    validation = read_json(PROP_VALIDATION)
    models = read_json(PROP_MODELS)
    model_version = models.get("model_version") or validation.get("model_version")

    for lane_key, lane in (validation.get("lanes") or {}).items():
        spec = {
            "family_id": f"PROP_CORE|{lane_key}",
            "sport": lane.get("sport"),
            "lane": lane.get("lane"),
            "market": "ALL_PROP_MARKETS",
            "features": lane.get("feature_names") or [],
            "calibration": "REGULARIZED_LOGISTIC_MARKET_RESIDUAL",
            "thresholds": {
                "minimum_history_rows": 40,
                "minimum_independent_blocks": 30,
                "market_baseline_required": True,
            },
            "training_window": f"history_rows:{lane.get('history_n')}",
            "validation_window": (
                f"walk_forward_rows:{lane.get('walk_forward_n')}|"
                f"folds:{lane.get('folds')}"
            ),
            "cluster_key": "GAME_EVENT_DATE_BLOCK",
            "notes": (
                f"PROP_CORE|{model_version}|"
                f"source:{lane.get('deployment_probability_source')}"
            ),
        }
        confidence = lane.get("historical_edge_confidence")
        ensure_experiment(
            spec,
            status=lane.get("status") or "UNKNOWN",
            metrics={
                "metrics": lane.get("metrics") or {},
                "paired_comparisons": lane.get("paired_comparisons") or {},
                "history_n": lane.get("history_n"),
                "independent_blocks": lane.get("independent_blocks"),
                "devig_history_pct": lane.get("devig_history_pct"),
                "old_score_status": lane.get("old_score_status"),
            },
            decision=decision_from_confidence(confidence),
            reason=str(confidence or "INSUFFICIENT_EVIDENCE"),
        )


def register_challengers():
    payload = read_json(PROP_CHALLENGERS)
    for lane_key, lane in (payload.get("lanes") or {}).items():
        if lane.get("status") == "INSUFFICIENT_HISTORY":
            continue
        choices = lane.get("inner_choices") or []
        spec = {
            "family_id": f"PROP_CHALLENGER|{lane_key}",
            "sport": lane_key.split("_", 1)[0],
            "lane": lane_key.split("_", 1)[1] if "_" in lane_key else lane_key,
            "market": "ALL_PROP_MARKETS",
            "features": sorted({
                feature
                for choice in choices
                for feature in (choice.get("features") or [])
            }),
            "calibration": "NESTED_WALK_FORWARD_FEATURE_ABLATION_L2",
            "thresholds": {
                "outer_folds": lane.get("outer_folds"),
                "automatic_live_change": False,
            },
            "training_window": f"history_rows:{lane.get('history_n')}",
            "validation_window": f"walk_forward_rows:{lane.get('walk_forward_n')}",
            "cluster_key": "GAME_EVENT_DATE_BLOCK",
            "notes": (
                f"PROP_CHALLENGER|status:{lane.get('status')}|"
                f"choices:{canonical_json(lane.get('choice_counts') or {})}"
            ),
        }
        keep_current = lane.get("status") == "KEEP_CURRENT_V2"
        ensure_experiment(
            spec,
            status=lane.get("status") or "UNKNOWN",
            metrics={
                "metrics": lane.get("metrics") or {},
                "comparisons": lane.get("comparisons") or {},
                "choice_counts": lane.get("choice_counts") or {},
            },
            decision="REJECTED" if keep_current else "HOLD",
            reason=(
                "CHALLENGER_DID_NOT_BEAT_CURRENT_V2"
                if keep_current
                else "CHALLENGER_REQUIRES_REVIEW"
            ),
        )


def register_segments():
    payload = read_json(PROP_SEGMENTS)
    for lane_key, lane in (payload.get("lanes") or {}).items():
        for market, segment in (lane.get("segments") or {}).items():
            spec = {
                "family_id": f"PROP_SEGMENT|{lane_key}|{market}",
                "sport": lane_key.split("_", 1)[0],
                "lane": lane_key.split("_", 1)[1] if "_" in lane_key else lane_key,
                "market": market,
                "features": segment.get("feature_names") or [],
                "calibration": "SEGMENT_ROLLING_ORIGIN_MARKET_RESIDUAL",
                "thresholds": {
                    "minimum_rows": payload.get("minimum_rows"),
                    "minimum_independent_blocks": payload.get(
                        "minimum_independent_blocks"
                    ),
                },
                "training_window": f"history_rows:{segment.get('history_n')}",
                "validation_window": f"walk_forward_rows:{segment.get('walk_forward_n')}",
                "cluster_key": "GAME_EVENT_DATE_BLOCK",
                "notes": (
                    f"PROP_SEGMENT|source:"
                    f"{segment.get('deployment_probability_source')}"
                ),
            }
            confidence = segment.get("historical_edge_confidence")
            ensure_experiment(
                spec,
                status=segment.get("status") or "UNKNOWN",
                metrics={
                    "metrics": segment.get("metrics") or {},
                    "paired_comparisons": segment.get("paired_comparisons") or {},
                    "rows": segment.get("rows"),
                    "independent_blocks": segment.get("independent_blocks"),
                },
                decision=decision_from_confidence(confidence),
                reason=str(confidence or "INSUFFICIENT_EVIDENCE"),
            )


def register_forward():
    payload = read_json(PROP_FORWARD)
    model_version = payload.get("model_version")
    if not model_version:
        return
    all_predictions = payload.get("all_predictions") or {}
    monitor = payload.get("monitor_selection") or {}
    spec = {
        "family_id": "PROP_FORWARD",
        "sport": "MULTI",
        "lane": "PROP_AND_PRIZEPICKS",
        "market": "FORWARD_SELECTION",
        "features": [],
        "calibration": "FROZEN_FORWARD_PROOF",
        "thresholds": {
            "minimum_decisions": (
                all_predictions.get("proof_requirements") or {}
            ).get("minimum_decisions"),
            "minimum_independent_blocks": (
                all_predictions.get("proof_requirements") or {}
            ).get("minimum_independent_blocks"),
            "automatic_promotion": False,
        },
        "training_window": "FROZEN_HISTORICAL_MODEL",
        "validation_window": "FORWARD_ONLY",
        "cluster_key": "GAME_EVENT_DATE_BLOCK",
        "notes": f"PROP_FORWARD|{model_version}",
    }
    ensure_experiment(
        spec,
        status=payload.get("status") or "UNKNOWN",
        metrics={
            "all_predictions": all_predictions,
            "monitor_selection": monitor,
            "by_lane": payload.get("by_lane") or {},
        },
        decision="HOLD",
        reason=str(
            monitor.get("proof_status")
            or all_predictions.get("proof_status")
            or "BUILDING_FORWARD_SAMPLE"
        ),
        forward_only=True,
    )



def register_best_bets():
    validation = read_json(BEST_BETS_VALIDATION)
    for lane_key, lane in (validation.get("lanes") or {}).items():
        confidence = lane.get("historical_edge_confidence")
        spec = {
            "family_id": f"BEST_BETS_CORE|{lane_key}",
            "sport": lane.get("sport"),
            "lane": "GAME",
            "market": lane.get("market"),
            "features": ["MARKET_REFERENCE", "HULK_EVIDENCE_SCORE"],
            "calibration": "SPORT_MARKET_BLOCKED_WALK_FORWARD",
            "thresholds": {
                "minimum_rows": 50,
                "minimum_independent_blocks": 25,
                "automatic_promotion": False,
            },
            "training_window": f"history_rows:{lane.get('history_n')}",
            "validation_window": f"walk_forward_rows:{lane.get('walk_forward_n')}",
            "cluster_key": "GAME",
            "notes": f"BEST_BETS|{validation.get('model_version')}|{lane_key}",
        }
        ensure_experiment(
            spec,
            status=lane.get("status") or "UNKNOWN",
            metrics={
                "metrics": lane.get("metrics") or {},
                "paired_comparisons": lane.get("paired_comparisons") or {},
                "history_n": lane.get("history_n"),
                "independent_blocks": lane.get("independent_blocks"),
                "old_score_status": lane.get("old_score_status"),
                "devig_history_pct": lane.get("devig_history_pct"),
            },
            decision=decision_from_confidence(confidence),
            reason=str(confidence or lane.get("status") or "INSUFFICIENT_EVIDENCE"),
        )

    forward = read_json(BEST_BETS_FORWARD)
    for lane_key, lane in (forward.get("by_lane") or {}).items():
        stats = lane.get("all_predictions") or {}
        promotion = lane.get("promotion") or {}
        spec = {
            "family_id": f"BEST_BETS_FORWARD|{lane_key}",
            "sport": lane_key.split("_", 1)[0],
            "lane": "GAME",
            "market": lane_key.split("_", 1)[1] if "_" in lane_key else lane_key,
            "features": [],
            "calibration": "FROZEN_FORWARD_PROOF",
            "thresholds": {
                "minimum_decisions": 50,
                "minimum_independent_blocks": 30,
                "automatic_promotion": False,
            },
            "training_window": "FROZEN_HISTORICAL_MODEL",
            "validation_window": "FORWARD_ONLY",
            "cluster_key": "GAME",
            "notes": f"BEST_BETS_FORWARD|{forward.get('current_model_version')}|{lane_key}",
        }
        recommendation = promotion.get("recommendation") or stats.get("proof_status")
        ensure_experiment(
            spec,
            status=forward.get("status") or "UNKNOWN",
            metrics={"all_predictions": stats, "promotion": promotion},
            decision="HOLD" if recommendation != "MANUAL_REVIEW_CANDIDATE" else "CANDIDATE",
            reason=str(recommendation or "BUILDING_FORWARD_SAMPLE"),
            forward_only=True,
        )



def register_best_bet_challengers():
    payload = read_json(BEST_BETS_CHALLENGERS)
    for lane_key, lane in (payload.get("lanes") or {}).items():
        if not lane_key.startswith("CFB_"):
            continue
        if lane.get("status") in {
            "RICH_CHALLENGER_NOT_YET_SUPPORTED",
            "INSUFFICIENT_INDEPENDENT_GAMES",
            "NO_RICH_FEATURES_WITH_SUFFICIENT_COVERAGE",
        }:
            continue
        spec = {
            "family_id": f"BEST_BETS_CHALLENGER|{lane_key}",
            "sport": lane_key.split("_",1)[0],
            "lane": "GAME",
            "market": lane_key.split("_",1)[1],
            "features": sorted({
                feature
                for group in (lane.get("feature_groups") or {}).values()
                for feature in group
            }),
            "calibration": "NESTED_WHOLE_GAME_PREDECLARED_FEATURE_FAMILY_SEARCH",
            "thresholds": {
                "minimum_independent_blocks": 40,
                "must_beat_current_v2": True,
                "must_beat_market_reference": True,
                "must_beat_calibrated_market": True,
                "automatic_live_change": False,
            },
            "training_window": f"history_rows:{lane.get('history_n')}",
            "validation_window": (
                f"walk_forward_rows:{lane.get('walk_forward_n')}|"
                f"blocks:{lane.get('walk_forward_blocks')}"
            ),
            "cluster_key": "GAME",
            "notes": f"BEST_BETS_CHALLENGER|{lane_key}|{lane.get('status')}",
        }
        status = lane.get("status")
        ensure_experiment(
            spec,
            status=status or "UNKNOWN",
            metrics={
                "metrics": lane.get("metrics") or {},
                "comparisons": lane.get("comparisons") or {},
                "choice_counts": lane.get("choice_counts") or {},
                "history_span_days": lane.get("history_span_days"),
            },
            decision=(
                "CANDIDATE"
                if status == "CHALLENGER_REVIEW_CANDIDATE"
                else "HOLD"
                if status == "PROMISING_NOT_PROVEN"
                else "REJECTED"
            ),
            reason=str(status or "UNKNOWN"),
        )

    forward = read_json(BEST_BETS_CHALLENGER_FORWARD)
    if forward:
        stats = forward.get("forward") or {}
        spec = {
            "family_id": "BEST_BETS_CHALLENGER_FORWARD|CFB_TOTAL",
            "sport": "CFB",
            "lane": "GAME",
            "market": "TOTAL",
            "features": [],
            "calibration": "FROZEN_FORWARD_CHALLENGER_PROOF",
            "thresholds": {
                "minimum_settled": stats.get("minimum_settled_for_review"),
                "minimum_independent_games": stats.get("minimum_independent_games_for_review"),
                "automatic_promotion": False,
            },
            "training_window": "LOCKED_HISTORICAL_CHALLENGER",
            "validation_window": "FORWARD_ONLY",
            "cluster_key": "GAME",
            "notes": f"BEST_BETS_CFB_TOTAL_FORWARD|{forward.get('model_version')}",
        }
        proof = stats.get("proof_status")
        ensure_experiment(
            spec,
            status=forward.get("status") or "UNKNOWN",
            metrics=stats,
            decision="CANDIDATE" if proof == "CHALLENGER_REVIEW_CANDIDATE" else "HOLD",
            reason=str(proof or "BUILDING_FORWARD_SAMPLE"),
            forward_only=True,
        )

def register_parlays():
    validation = read_json(PARLAY_VALIDATION)
    for sport, row in (validation.get("by_sport") or {}).items():
        diag = row.get("legacy_score_diagnostic") or {}
        spec = {
            "family_id": f"PARLAY_LEGACY_SCORE|{sport}",
            "sport": sport,
            "lane": "PARLAY",
            "market": "TWO_LEG_COMBOS",
            "features": ["LEGACY_PARLAY_SCORE"],
            "calibration": "ROLLING_ORIGIN_DIAGNOSTIC_ONLY",
            "thresholds": {"automatic_promotion": False},
            "training_window": f"unique_settled_combos:{row.get('settled_unique_combos')}",
            "validation_window": f"walk_forward_rows:{diag.get('walk_forward_n')}",
            "cluster_key": "COMBO_SIGNATURE",
            "notes": f"PARLAY_LEGACY|{validation.get('model_version')}|{sport}",
        }
        beats = diag.get("old_score_beats_base_rate") is True
        ensure_experiment(
            spec,
            status=diag.get("status") or "UNKNOWN",
            metrics={
                "hit_rate_pct": row.get("hit_rate_pct"),
                "legacy_score_diagnostic": diag,
            },
            decision="HOLD" if beats else "REJECTED",
            reason=(
                "MEAN_IMPROVEMENT_DIAGNOSTIC_ONLY"
                if beats else "OLD_SCORE_DID_NOT_BEAT_BASE_RATE"
            ),
        )

    forward = read_json(PARLAY_FORWARD)
    if forward:
        monitor = forward.get("monitor_selection") or {}
        promotion = forward.get("promotion") or {}
        spec = {
            "family_id": "PARLAY_FORWARD",
            "sport": "MULTI",
            "lane": "PARLAY",
            "market": "CROSS_GAME_TWO_LEG",
            "features": ["SOURCE_V2_LEG_PROBABILITIES"],
            "calibration": "DISJOINT_FORWARD_PARLAY_PROOF",
            "thresholds": {
                "minimum_decisions": 50,
                "minimum_disjoint_parlays": 30,
                "captured_combined_price_required": True,
                "automatic_promotion": False,
            },
            "training_window": "SOURCE_LEGS_FORWARD_PROVEN",
            "validation_window": "FORWARD_ONLY",
            "cluster_key": "UNDERLYING_EVENT_DISJOINT",
            "notes": f"PARLAY_FORWARD|{forward.get('current_model_version')}",
        }
        rec = promotion.get("recommendation") or monitor.get("proof_status")
        ensure_experiment(
            spec,
            status=forward.get("status") or "UNKNOWN",
            metrics={
                "all_predictions": forward.get("all_predictions") or {},
                "monitor_selection": monitor,
                "promotion": promotion,
            },
            decision="CANDIDATE" if rec == "MANUAL_REVIEW_CANDIDATE" else "HOLD",
            reason=str(rec or "BUILDING_FORWARD_SAMPLE"),
            forward_only=True,
        )


def register_dfs():
    payload = read_json(DFS_SUMMARY)
    version = payload.get("model_version")
    for row in (payload.get("replay") or {}).get("strategy_summary") or []:
        platform = row.get("platform")
        mode = row.get("mode")
        spec = {
            "family_id": f"DFS_REPLAY|{platform}|{mode}",
            "sport": "NFL",
            "lane": "DFS",
            "market": f"{platform}|{mode}",
            "features": [],
            "calibration": "PRELOCK_REPLAY_VS_SALARY_EFFICIENT_RANDOM_AND_MAX_PROJECTION",
            "thresholds": {
                "salary_floor_pct": 94,
                "replay_never_promotes": True,
            },
            "training_window": "HISTORICAL_PRELOCK_SNAPSHOTS",
            "validation_window": f"replay_slates:{row.get('slates')}",
            "cluster_key": "SLATE",
            "notes": f"DFS_REPLAY|{version}|{platform}|{mode}",
        }
        ensure_experiment(
            spec,
            status=row.get("evidence_status") or "RESEARCH_ONLY",
            metrics=row,
            decision="HOLD",
            reason=str(row.get("evidence_status") or "REPLAY_RESEARCH_ONLY"),
        )

    for row in (payload.get("forward") or {}).get("summary") or []:
        platform = row.get("platform")
        mode = row.get("mode")
        spec = {
            "family_id": f"DFS_FORWARD|{platform}|{mode}",
            "sport": "NFL",
            "lane": "DFS",
            "market": f"{platform}|{mode}",
            "features": [],
            "calibration": "FROZEN_PRELOCK_FORWARD_VS_MAX_PROJECTION",
            "thresholds": {
                "minimum_forward_slates": row.get("minimum_forward_slates_for_review"),
                "automatic_promotion": False,
            },
            "training_window": "CURRENT_MODEL_VERSION_ONLY",
            "validation_window": "FORWARD_ONLY",
            "cluster_key": "SLATE",
            "notes": f"DFS_FORWARD|{version}|{platform}|{mode}",
        }
        status = row.get("proof_status")
        ensure_experiment(
            spec,
            status=status or "UNKNOWN",
            metrics=row,
            decision="CANDIDATE" if status == "MANUAL_REVIEW_CANDIDATE" else "HOLD",
            reason=str(status or "BUILDING_FORWARD_SAMPLE"),
            forward_only=True,
        )


def register_fantasy():
    current = read_json(FANTASY_CURRENT)
    forward = read_json(FANTASY_FORWARD)
    lane_to_forward = {
        "WEEKLY": "weekly",
        "FAAB": "faab",
        "IR_STASH": "ir_stash",
        "DEFENSE_STREAMING": "defense_streaming",
        "IDP": "idp",
        "TRADE_RATE_TEAM": "trade_rate_team",
    }
    for lane, info in (current.get("lanes") or {}).items():
        frow = forward.get(lane_to_forward.get(lane, "")) or {}
        proof = frow.get("proof_status") or info.get("status")
        spec = {
            "family_id": f"FANTASY_FORWARD|{lane}",
            "sport": "NFL" if lane != "TRADE_RATE_TEAM" else "LEAGUE_CONTEXT",
            "lane": "FANTASY",
            "market": lane,
            "features": [],
            "calibration": "FROZEN_FORWARD_RANK_OR_UTILITY_PROOF",
            "thresholds": {
                "minimum_independent_weeks": 6,
                "automatic_promotion": False,
            },
            "training_window": f"current_rows:{info.get('rows')}",
            "validation_window": "FORWARD_ONLY",
            "cluster_key": "WEEK",
            "notes": f"FANTASY_FORWARD|{forward.get('model_version')}|{lane}",
        }
        ensure_experiment(
            spec,
            status=info.get("status") or "UNKNOWN",
            metrics={"current": info, "forward": frow},
            decision=(
                "CANDIDATE"
                if str(proof or "").endswith("REVIEW_CANDIDATE")
                else "HOLD"
            ),
            reason=str(proof or "BUILDING_FORWARD_SAMPLE"),
            forward_only=True,
        )


def register_survivor():
    payload = read_json(SURVIVOR_FORWARD)
    if not payload:
        return
    current = payload.get("current") or {}
    forward = payload.get("forward") or {}
    proof = forward.get("proof_status")
    spec = {
        "family_id": "SURVIVOR_FORWARD",
        "sport": "NFL",
        "lane": "SURVIVOR",
        "market": "WEEKLY_SURVIVAL",
        "features": ["MARKET_PROBABILITY", "CONTEXT", "FUTURE_VALUE"],
        "calibration": "FROZEN_WEEKLY_SURVIVAL_VS_SAFEST_MARKET_BASELINE",
        "thresholds": {
            "minimum_independent_weeks": 10,
            "minimum_distinct_baseline_weeks": 3,
            "official_rule_confirmation_required": True,
            "automatic_promotion": False,
        },
        "training_window": "NO_RETROACTIVE_MODEL_PICKS",
        "validation_window": "FORWARD_ONLY",
        "cluster_key": "POOL_WEEK",
        "notes": f"SURVIVOR_FORWARD|{payload.get('model_version')}",
    }
    ensure_experiment(
        spec,
        status=current.get("recommendation_status") or payload.get("status") or "UNKNOWN",
        metrics={"current_gate": current.get("recommendation_status"), "forward": forward},
        decision="CANDIDATE" if proof == "PROMISING_REVIEW_CANDIDATE" else "HOLD",
        reason=str(proof or current.get("recommendation_status") or "BUILDING_FORWARD_SAMPLE"),
        forward_only=True,
    )

def write_summary():
    base = summarize(LEDGER)
    events = read_events(LEDGER)
    registered_specs = {}
    for event in events:
        if event.get("event_type") == "REGISTERED":
            registered_specs.setdefault(
                event.get("experiment_id"),
                event.get("spec") or {},
            )

    families = {}
    for spec in registered_specs.values():
        family = str(spec.get("family_id") or "UNSPECIFIED")
        families[family] = families.get(family, 0) + 1

    base["family_counts"] = families
    base["families_with_multiple_tests"] = {
        key: value
        for key, value in families.items()
        if value > 1
    }
    base["multiple_testing_note"] = (
        "Experiment counts include rejected/failed tests. "
        "Future significance review must account for related-family search."
    )
    SUMMARY.write_text(json.dumps(base, indent=2))
    return base


def main():
    register_prop_core()
    register_challengers()
    register_segments()
    register_forward()
    register_best_bets()
    register_best_bet_challengers()
    register_parlays()
    register_dfs()
    register_fantasy()
    register_survivor()
    print(json.dumps(write_summary(), indent=2))


if __name__ == "__main__":
    main()
