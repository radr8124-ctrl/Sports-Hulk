"""Sports Zenith: source-grounded diagnosis of BAD betting predictions.

READ-ONLY: original immutable game and prop forward ledgers, market odds,
actual official source-grade summaries and Hugging Face historical controls.
This is a retrospective failure audit, not new forward model training.
"""
from __future__ import annotations

from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib,json,math,os
from pathlib import Path
from statistics import mean

from intelligence_warehouse.betting_v2 import build_betting_v2_all_markets_forward as game
from intelligence_warehouse.betting_v2 import build_prop_v2_forward as prop

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"reports/ZENITH_PREDICTION_FAILURE_ROOT_CAUSE_AUDIT_2026-10-09.json"
SUMMARY=ROOT/"reports/SPORTS_ZENITH_PREDICTION_FAILURE_REASONS_2026-10-09.md"
SOURCE={
    "game_ledger":"intelligence_warehouse/betting_v2/BETTING_V2_ALL_MARKETS_FORWARD_LEDGER.jsonl",
    "game_summary":"intelligence_warehouse/betting_v2/BETTING_V2_ALL_MARKETS_FORWARD_SUMMARY.json",
    "prop_ledger":"intelligence_warehouse/betting_v2/PROP_V2_FORWARD_LEDGER.jsonl",
    "prop_summary":"intelligence_warehouse/betting_v2/PROP_V2_FORWARD_SUMMARY.json",
    "nba_spread_audit":"reports/ZENITH_NBA_SPREAD_PRESEASON_SOURCE_AUDIT_2026-10-09.json",
    "nba_total_audit":"reports/NBA_TOTAL_PRESEASON_SOURCE_INDEPENDENCE_RESULTS_2026-10-09.json",
    "nba_hf_benchmark":"reports/hf_nba_closinglines_audit_20261009/nba_research_comparison_summary.json",
}
GAME_VERSION="BETTING_V2_ALL_MARKETS_2026_10_05"
PROP_VERSION="PROP_V2_PHASE4_SUBTYPE_VETO_2026_10_05"
SCHEMA="ZENITH_SOURCE_TIME_MODEL_MARKET_FAILURE_ROOT_CAUSE_V1"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def numeric(v):
    x=float(v)
    if not math.isfinite(x):raise ValueError("NONFINITE_FROZEN_ORIGINAL_PROBABILITY")
    return x


def probabilities(rows):
    if not rows:raise ValueError("NO_ORIGINAL_FORWARD_RESULT_ROWS")
    model=[];market=[];outcome=[]
    for r in rows:
        p=numeric(r["v2_probability_pct"])/100
        q=numeric(r["market_reference_probability_pct"])/100
        if p<0 or p>1 or q<0 or q>1 or r["grade"] not in ("WIN","LOSS","PUSH"):
            raise ValueError("INVALID_ORIGINAL_PROBABILITY_OR_GRADE")
        y=float(r["grade"]=="WIN")
        model.append(p);market.append(q);outcome.append(y)
    return {
        "model_brier":round(mean((p-y)**2 for p,y in zip(model,outcome)),6),
        "source_market_brier":round(mean((q-y)**2 for q,y in zip(market,outcome)),6),
        "model_minus_market_brier":round(mean((p-y)**2-(q-y)**2 for p,q,y in zip(model,market,outcome)),6),
        "average_abs_model_market_probability_shift_pp":round(100*mean(abs(p-q) for p,q in zip(model,market)),3),
        "same_market_probability_rows":sum(p==q for p,q in zip(model,market)),
    }


def game_results(rows,report):
    chosen=[r for r in rows if r.get("model_version")==GAME_VERSION and r.get("grade") in ("WIN","LOSS","PUSH")]
    expected=report["all_predictions"]
    if len(chosen)!=expected["settled"]:
        raise ValueError("ORIGINAL_GAME_SOURCE_AND_SETTLED_TOTALS_MISMATCH")
    outcomes=Counter(x["grade"] for x in chosen)
    if outcomes["WIN"]!=expected["wins"] or outcomes["LOSS"]!=expected["losses"]:
        raise ValueError("ORIGINAL_GAME_WIN_AND_LOSS_TALLY_MISMATCH")
    equal=sum(
        x.get("entry_v2_probability_pct")==x.get("entry_market_reference_probability_pct")
        for x in chosen)
    origin=Counter(x.get("entry_probability_source") for x in chosen)
    decisions=Counter(x.get("entry_shadow_decision") for x in chosen)
    if sum(origin.values())!=len(chosen) or sum(decisions.values())!=len(chosen):
        raise ValueError("ORIGINAL_GAME_PROVENANCE_MISSING")
    if equal!=len(chosen) or set(decisions)!={
        "PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE","PASS_CONTRADICTORY_GAME_SIDES"
    }:
        raise ValueError("ORIGINAL_MARKET_MIRROR_DIAGNOSTIC_OUTDATED_REAUDIT_REQUIRED")
    by_lane={}
    for lane in sorted(set(x["lane_key"] for x in chosen)):
        parts=[r for r in chosen if r["lane_key"]==lane]
        by_lane[lane]={
            "settled_source_line_observations":len(parts),
            "independent_source_game_blocks":len({r["game_key"] for r in parts}),
            "wins":sum(r["grade"]=="WIN" for r in parts),
            "losses":sum(r["grade"]=="LOSS" for r in parts),
            "market_mirror_probabilities":sum(
                r.get("entry_v2_probability_pct")==r.get("entry_market_reference_probability_pct")
                for r in parts),
            "source_market_reference_only":True,
            "not_live_approved":all(str(r.get("entry_shadow_decision","")).startswith("PASS_") for r in parts),
        }
    return {
        "original_settled_alternative_game_line_observations":len(chosen),
        "model_probability_exactly_equal_market_count":equal,
        "no_independent_game_model_edge_shown":True,
        "original_price_reference_type_counts":dict(origin),
        "original_frozen_research_decision_counts":dict(decisions),
        "original_all_settled_game_line_paper_roi_pct":expected["roi_pct"],
        "original_all_settled_game_line_ROI_proven_executable":False,
        "by_lane":by_lane,
    }


def prop_results(rows,report):
    chosen=[r for r in rows if r.get("model_version")==PROP_VERSION and r.get("grade") in ("WIN","LOSS","PUSH")]
    original=report["all_predictions"]
    if len(chosen)!=original["settled"]:
        raise ValueError("ORIGINAL_PROP_SOURCE_COUNT_MISMATCH")
    if sum(r["grade"]=="WIN" for r in chosen)!=original["wins"]:
        raise ValueError("ORIGINAL_PROP_WIN_COUNT_MISMATCH")
    origins=Counter(r.get("probability_source") for r in chosen)
    nhl_core=[r for r in chosen if r["lane_key"]=="NHL_PROP" and r.get("probability_source")=="LANE_CORE_MODEL"]
    nhl_market=[r for r in chosen if r["lane_key"]=="NHL_PROP" and r.get("probability_source")=="MARKET_REFERENCE"]
    mlb_market=[r for r in chosen if r["lane_key"]=="MLB_PROP" and r.get("probability_source")=="MARKET_REFERENCE"]
    if len(nhl_core)!=799 or len(nhl_market)!=772 or len(mlb_market)!=988:
        raise ValueError("ORIGINAL_PROP_MODEL_SOURCE_REGIME_CHANGED")
    core_stats=probabilities(nhl_core)
    market_stats=probabilities(nhl_market)
    mlb_stats=probabilities(mlb_market)
    if not(core_stats["model_brier"]>core_stats["source_market_brier"] and
           market_stats["model_brier"]==market_stats["source_market_brier"] and
           mlb_stats["model_brier"]==mlb_stats["source_market_brier"]):
        raise ValueError("CORE_MODEL_MARKET_MIRROR_OUTCOME_DISAGREES")
    subtype={}
    for name in sorted({r.get("market") or r.get("market_subtype") or "UNKNOWN" for r in nhl_core}):
        subset=[r for r in nhl_core if (r.get("market") or r.get("market_subtype") or "UNKNOWN")==name]
        if len(subset)<20:continue
        s=probabilities(subset)
        subtype[name]={
            "research_source_rows":len(subset),
            "independent_nhl_game_blocks":len({prop.independent_block(r) for r in subset}),
            **s,
        }
    conf={}
    for name,low,high in (("MODEL_70_TO_80",70,80),("MODEL_OVER_80",80,101)):
        matched=[r for r in nhl_core if low<=float(r["v2_probability_pct"])<high]
        conf[name]={
            "correlated_player_prop_rows":len(matched),
            "original_predicted_probability_mean_pct":round(mean(float(r["v2_probability_pct"]) for r in matched),2),
            "realized_grade_WIN_pct":round(100*sum(r["grade"]=="WIN" for r in matched)/len(matched),2),
            "independent_games_not_line_count":len({prop.independent_block(r) for r in matched}),
        }
    return {
        "all_settled_prop_quote_rows":len(chosen),
        "market_reference_only_MLB_player_props":len(mlb_market),
        "source_MLB_prop_high_wins_not_necessarily_valuable":{
            "games":len({prop.independent_block(r) for r in mlb_market}),
            "wins":sum(r["grade"]=="WIN" for r in mlb_market),
            "losses":sum(r["grade"]=="LOSS" for r in mlb_market),
            "original_priced_paper_roi_pct":report["by_lane"]["MLB_PROP"]["all_predictions"]["roi_pct"],
            **mlb_stats,
        },
        "source_model_provenance_count":dict(origins),
        "NHL_core_model":{
            "correlated_player_quote_rows":len(nhl_core),
            "independent_game_blocks":len({prop.independent_block(r) for r in nhl_core}),
            "original_model_adjustments_on_average_make_Brier_worse":True,
            **core_stats,
            "by_player_prop_market":subtype,
            "model_confidence_buckets_diagnostic_only":conf,
        },
        "NHL_source_market_reference_only":{
            "correlated_player_quote_rows":len(nhl_market),
            "independent_game_blocks":len({prop.independent_block(r) for r in nhl_market}),
            **market_stats,
        },
        "source_paper_roi_not_real_paid_bets":True,
    }


def review_from_sources(data,hashes):
    market=game_results(data["game_rows"],data["game_summary"])
    props=prop_results(data["prop_rows"],data["prop_summary"])
    spread=data["nba_spread"]
    totals=data["nba_totals"]
    historical=data["nba_hf"]["market_comparisons"]
    if (spread["official_independent_games"]!=8 or
        spread["all_alternate_lines"]["entries"]!=39 or
        spread["retrospective_earliest_frozen_line_per_event_not_predeclared_strategy"]["wins"]!=3 or
        totals["exact_regime_duplicate_rows_not_independent"]!=8 or
        totals["original_ledger_grade_rows_held_for_official_start_disagreement"]!=7):
        raise ValueError("NBA_HISTORICAL_SOURCE_QUALITY_RECEIPTS_CHANGED")
    if historical["NBA_TOTAL_REGULAR_SEASON"]["test_games"]!=503 or (
        historical["NBA_TOTAL_REGULAR_SEASON"]["frozen_feature_challenger"]["brier"]<=
        historical["NBA_TOTAL_REGULAR_SEASON"]["raw_close_market"]["brier"]
    ):
        raise ValueError("HUGGING_FACE_NBA_MARKET_BENCHMARK_SOURCE_CHANGED")
    return {
        "schema":SCHEMA,
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "scope":"RETROSPECTIVE_SOURCE_FAILURE_DIAGNOSTIC_NOT_NEW_PROSPECTIVE_BETTING_EDGE",
        "frozen_original_source_sha256":hashes,
        "game_predictions":market,
        "player_props":props,
        "NBA_spread_eight_game_preseason":{
            "source_evidence_spread_lines":spread["all_alternate_lines"],
            "independent_official_preseason_game_blocks":spread["official_independent_games"],
            "one_quote_per_game_RETROSPECTIVE_ONLY":
                spread["retrospective_earliest_frozen_line_per_event_not_predeclared_strategy"],
            "all_39_source_lines_graded_against_official_NBA_scores":True,
            "all_39_shadow_PASS_not_real_bets":True,
        },
        "NBA_totals_source_defects":{
            "duplicate_semantic_total_lines":totals["exact_regime_duplicate_rows_not_independent"],
            "incorrect_original_tipoff_source_rows":totals["original_ledger_grade_rows_held_for_official_start_disagreement"],
            "strict_qualified_unique_preseason_lines":
                 totals["source_de_duplicated_exact_same_game_market_side_line_first_quote"]["original_source_line_records"],
            "independent_strictly_verified_preseason_games":
                 totals["source_de_duplicated_exact_same_game_market_side_line_first_quote"]["independent_official_game_blocks"],
            "model_brier_equals_bookmaker":totals["unique_line_model_Brier"]==totals["unique_line_source_market_fair_Brier"],
            "other_sports_not_yet_fully_source_audited":True,
        },
        "hugging_face_independent_market_benchmark":{
            "original_historical_dataset":"minmaxxxer/nba-closing-lines-ats-2025-26",
            "original_regular_season_games_source_matched":data["nba_hf"]["data_audit"]["verified_regular_game_rows"],
            "independent_historical_holdout_regular_season_games":503,
            "source_close_original_book_updated_at_and_executable_market_not_verified":True,
            "NBA_total_market_Brier":historical["NBA_TOTAL_REGULAR_SEASON"]["raw_close_market"]["brier"],
            "NBA_total_feature_model_Brier":historical["NBA_TOTAL_REGULAR_SEASON"]["frozen_feature_challenger"]["brier"],
            "NBA_spread_market_Brier":historical["NBA_SPREAD_REGULAR_SEASON"]["raw_close_market"]["brier"],
            "NBA_spread_feature_model_Brier":historical["NBA_SPREAD_REGULAR_SEASON"]["frozen_feature_challenger"]["brier"],
            "NBA_spread_statistically_proven_edge":False,
            "new_2026_NBA_regular_season_forward_games_used":0,
        },
        "separate_failure_cause_codes":[
            "MARKET_REFERENCE_OUTPUTS_MISTAKEN_FOR_MODEL_INDEPENDENT_GAME_PREDICTIONS",
            "FROZEN_ALTERNATE_LINES_CORRELATED_WITHIN_OFFICIAL_GAME_BLOCKS",
            "PRESEASON_NOT_COMPARABLE_TO_REGULAR_SEASON",
            "NBA_TOTAL_DUPLICATE_REGIME_SOURCE_AND_WRONG_15_MIN_KICKOFF",
            "NHL_CORE_PLAYER_MODEL_CALIBRATION_WORSE_THAN_SPORTSBOOK",
            "HIGH_FAVORITE_WIN_RATE_NOT_EQUAL_PROFIT_AFTER_QUOTED_PRICE",
            "INSUFFICIENT_INDEPENDENT_GAMES_FOR_FUTURE_EDGE_PROOF",
            "NO_INDEPENDENT_EXECUTABLE_NAMED_BOOK_QUOTES_OR_REAL_WAGERS",
        ],
        "experiment_release_guardrails":{
            "preserve_current_independent_NFL_MLB_future_freezes":True,
            "game_markets_in_same_sport_must_be_evaluated_separately":True,
            "all_source_market_reference_only_results_label_as_BENCHMARK_NOT_ZENITH_EDGE":True,
            "NHL_core_adjustments_only_as_research_challenger_until_proven":True,
            "one_precommitted_line_or_team_per_independent_game_for_primary_profitability":True,
            "verify_kickoff_sport_team_player_source_quote_and_final_at_original_event_time":True,
            "require_market_v_model_Brier_game_cluster_interval_and_source_priced_paper_ROI":True,
            "no_cherry_pick_ex_post_70percent_hits_or_favorites":True,
            "live_bet_model_or_wager_changes_authorized":False,
        },
        "actual_live_model_or_betting_play_modified":False,
        "statistically_or_commercially_proven_predictive_edge":False,
    }


def run():
    files={k:ROOT/v for k,v in SOURCE.items()}
    originals={k:digest(p) for k,p in files.items()}
    data={
        "game_rows":list(game.canonical().values()),
        "prop_rows":list(prop.canonical().values()),
        "game_summary":json.loads(files["game_summary"].read_bytes()),
        "prop_summary":json.loads(files["prop_summary"].read_bytes()),
        "nba_spread":json.loads(files["nba_spread_audit"].read_bytes()),
        "nba_totals":json.loads(files["nba_total_audit"].read_bytes()),
        "nba_hf":json.loads(files["nba_hf_benchmark"].read_bytes()),
    }
    result=review_from_sources(data,originals)
    if any(digest(p)!=originals[k] for k,p in files.items()):
        raise ValueError("SOURCE_LEDGER_MODIFIED_DURING_READONLY_DIAGNOSTIC")
    return result


def main():
    data=run()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open("x",encoding="utf8") as f:
        json.dump(data,f,indent=2,sort_keys=True)
        f.write("\n");f.flush();os.fsync(f.fileno())
    print("ZENITH_GAME_PREDICTION_ROOT_CAUSE_FROZEN_SOURCE_AUDIT",json.dumps({
        "game_market_mirrored":data["game_predictions"]["model_probability_exactly_equal_market_count"],
        "NHL_adjusted_model_rows":data["player_props"]["NHL_core_model"]["correlated_player_quote_rows"],
        "NHL_adjusted_model_vs_market_brier":data["player_props"]["NHL_core_model"]["model_minus_market_brier"],
        "NBA_spread_game_blocks":data["NBA_spread_eight_game_preseason"]["independent_official_preseason_game_blocks"],
        "changes_to_live_bets":data["actual_live_model_or_betting_play_modified"],
        "report":str(OUT.relative_to(ROOT)),
    },sort_keys=True))


if __name__=="__main__":
    main()
