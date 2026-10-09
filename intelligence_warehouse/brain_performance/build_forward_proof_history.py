"""Versioned, append-only, hash-chained Sports Zenith forward proof scorecard.

Built exclusively from existing read-only research receipts. No outcomes,
moneyline prices, trained models, frozen bets or previous history get edited.
ROI is explicitly PAPER PRICED at SOURCE odds, not real financial return.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE="intelligence_warehouse/brain_performance"
HISTORY="FORWARD_PROOF_TREND_APPEND_ONLY.jsonl"
CURRENT="FORWARD_PROOF_CURRENT.json"
PUBLIC_FILENAME="forward_proof_current.json"
PUBLIC_SCHEMA="ZENITH_RESEARCH_ONLY_PUBLIC_FORWARD_PROOF_V1"
SCHEMA="ZENITH_AUDITABLE_FORWARD_PROOF_TREND_V1"
SOURCE_FILES={
    "game_forward":"intelligence_warehouse/betting_v2/BETTING_V2_ALL_MARKETS_FORWARD_SUMMARY.json",
    "props_forward":"intelligence_warehouse/betting_v2/PROP_V2_FORWARD_SUMMARY.json",
    "mlb_full16":"intelligence_warehouse/mlb_pregame_capture/MLB_V4_FULL16_SAME_NEW_QUOTE_SCORE_SUMMARY.json",
    "mlb_price_movement":"intelligence_warehouse/mlb_pregame_capture/MLB_FUTURE_ASOF_2H_PRICE_MOVEMENT_SUMMARY.json",
    "mlb_movement_final":"intelligence_warehouse/mlb_pregame_capture/MLB_FUTURE_2H_MOVEMENT_OFFICIAL_GRADE_SUMMARY.json",
    "mlb_forward70":"intelligence_warehouse/selective_forward/MLB_FULL16_70_FIXED_VALUE_RESEARCH_SUMMARY.json",
    "nfl_forward70":"intelligence_warehouse/selective_forward/NFL_70_FIXED_VALUE_RESEARCH_SUMMARY.json",
    "cfb_learning":"cfb_live/decision/history/CFB_LEARNING_SUMMARY.json",
}


def canonical(payload):
    return json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_reports(root):
    reports={}
    digests={}
    for name,path in SOURCE_FILES.items():
        original=Path(root)/path
        if not original.is_file():
            raise ValueError(f"MISSING_REQUIRED_ORIGINAL_SCORECARD_SOURCE:{name}")
        data=original.read_bytes()
        try:report=json.loads(data)
        except (json.JSONDecodeError,ValueError) as exc:
            raise ValueError(f"INVALID_SOURCE_JSON:{name}") from exc
        if not isinstance(report,dict):
            raise ValueError(f"INVALID_SOURCE_OBJECT:{name}")
        digests[name]={"source":path,"sha256":sha(data)}
        reports[name]=report
    return reports,digests


def bounded_number(value,label):
    if value is None:return None
    try:
        n=float(value)
    except (TypeError,ValueError) as exc:
        raise ValueError(f"INVALID_SCORECARD_NUMBER:{label}") from exc
    if not math.isfinite(n):
        raise ValueError(f"NONFINITE_SCORECARD_NUMBER:{label}")
    return n


def selected_stats(category,source,name):
    a=source["all_predictions"]
    for k in ("tracked","settled","pending","wins","losses","pushes","independent_blocks",
              "priced_settled"):
        if not isinstance(a.get(k),int) or a[k]<0:
            raise ValueError(f"INVALID_GAME_OR_PROP_GRADE_COUNT:{category}:{k}")
    if (a["tracked"]!=a["settled"]+a["pending"]
        or a["settled"]!=a["wins"]+a["losses"]+a["pushes"]
        or a["priced_settled"]>a["settled"]):
        raise ValueError(f"RESULT_LEDGER_COUNTS_DO_NOT_RECONCILE:{category}")
    rate=bounded_number(a.get("hit_rate_pct"),f"{category}:hit_rate")
    roi=bounded_number(a.get("roi_pct"),f"{category}:roi")
    units=bounded_number(a.get("units"),f"{category}:units")
    market=bounded_number(a.get("market_brier"),f"{category}:market_brier")
    model=bounded_number(a.get("v2_brier"),f"{category}:model_brier")
    lcb=bounded_number(a.get("roi_lcb90_pct"),f"{category}:game_block_roi_lcb")
    if a["wins"]+a["losses"]:
        exact=100*a["wins"]/(a["wins"]+a["losses"])
        if rate is None or abs(rate-exact)>.06:
            raise ValueError(f"WIN_RATE_NOT_MATCHING_OFFICIAL_RESEARCH_GRADES:{category}")
    if units is not None and a["priced_settled"]:
        if roi is None or abs(roi - (100*units/a["priced_settled"]))>.06:
            raise ValueError(f"ROI_NOT_MATCHING_RECORDED_SOURCE_UNITS:{category}")
    if a["settled"] and (not isinstance(market,float) or not isinstance(model,float)):
        raise ValueError(f"NO_PAIR_MARKET_COMPARISON_FOR_SETTLED_SOURCE:{category}")
    if source.get("status")!="READY" or a.get("live_rule_changed") is not False:
        raise ValueError(f"NOT_COMPLETED_SEPARATE_FORWARD_RESEARCH_REPORT:{category}")
    model_version=source.get("current_model_version") or source.get("model_version")
    if not model_version:
        raise ValueError(f"MISSING_ORIGINAL_MODEL_VERSION:{category}")
    return {
        "category":name,
        "model_version":model_version,
        "source_generated_at_utc":source["generated_at"],
        "original_tracked":a["tracked"],
        "pending":a["pending"],
        "settled":a["settled"],
        "wins":a["wins"],"losses":a["losses"],"pushes":a["pushes"],
        "hit_rate_pct":rate,
        "independent_game_blocks":a["independent_blocks"],
        "source_book_priced_settled":a["priced_settled"],
        "source_book_quoted_paper_units":units,
        "source_book_quoted_paper_roi_pct":roi,
        "equal_game_block_profit_lcb90_pct":lcb,
        "roi_and_game_block_lcb_are_different_weighted_estimands":True,
        "source_no_vig_market_brier":market,
        "model_frozen_brier":model,
        "model_minus_market_brier":round(model-market,7) if market is not None and model is not None else None,
        "model_probabilities_outperform_market_point_estimate":model<market if market is not None and model is not None else False,
        "source_promotion_proof_status":a["proof_status"],
        "model_outperforming_market_proven":False,
        "true_financial_profit_proven":False,
        "real_wagers_claimed":0,
        "warning":"These are already-priced research simulations; probabilities and simulated ROI are not proven executable at original sportsbooks.",
    }


def build_view(reports,digests,now):
    games=selected_stats("GAMES",reports["game_forward"],"GAME_LINES")
    props=selected_stats("PROPS",reports["props_forward"],"PROPS_AND_PICKEM")
    mlb=reports["mlb_full16"]
    movement=reports["mlb_price_movement"]
    grade=reports["mlb_movement_final"]
    nfl=reports["nfl_forward70"]
    mlb70=reports["mlb_forward70"]
    cfb=reports["cfb_learning"]
    if (mlb.get("independent_official_game_blocks",0)<1 or
        grade.get("official_graded_movement_records",0)<0 or
        not movement.get("new_model_retraining_or_promotion") is False or
        mlb.get("play_authorized",False) is True):
        raise ValueError("UNPROVEN_OR_CHANGED_MLB_MODEL_STATE")
    # The original first genuinely frozen Full16 single game does NOT belong
    # to the new future price-movement holdout, even if summaries overlap.
    early=int(movement.get("all_future_horizon_frozen_movement_records",0))
    pending=int(sum(grade.get("pending_source_reasons",{}).values()))
    graded=int(grade.get("official_graded_movement_records",0))
    if pending + graded != early:
        raise ValueError("FUTURE_MLB_SOURCE_SIGNAL_GRADING_COUNTS_DONT_RECONCILE")
    if movement.get("original_book_market_prices_verified_executable") is not False:
        raise ValueError("UNVERIFIED_VENDOR_PRICE_PROMOTED_TO_EXECUTABLE")
    if not nfl.get("research_only_not_live_betting_picks") is True:
        raise ValueError("NFL_SOURCE_SELECTION_IS_NOT_RESEARCH_ONLY")
    if not mlb70.get("production_model_or_wagers_changed") is False:
        raise ValueError("MLB_FROZEN_RESEARCH_CHANGED_COMMERCIAL_BETS")
    if cfb.get("automatic_model_adjustment") is not False:
        raise ValueError("CFB_RESEARCH_RESULTS_CHANGED_MODEL_AUTOMATICALLY")
    counts=cfb["grade_counts"]
    if int(cfb["unique_recommendations"])!=sum(int(v) for v in counts.values()):
        raise ValueError("CFB_GRADE_PROOF_COUNTS_INVALID")
    if int(cfb["settled"])!=sum(int(counts.get(v,0)) for v in ("WIN","LOSS","PUSH")):
        raise ValueError("CFB_RESEARCH_RESULTS_NOT_SETTLED_CONSISTENTLY")
    n_select=nfl["capture"]
    n_grade=nfl["grade"]
    if n_select["total_original_game_selections_saved"] != (
          n_select["original_game_abstentions_saved"]+n_select["provisional_paper_screen_pass_count"]):
        raise ValueError("NFL_FROZEN_SCREEN_ABSTENTIONS_DO_NOT_SUM_TO_GAME_SOURCES")
    mlb_score={
      "completed_independent_original_full16_games":mlb["independent_official_game_blocks"],
      "completed_original_hit_predictions_in_same_game":mlb.get("original_true_full16_shadow_forecasts",18),
      "source_book_market_brier":mlb["book_raw_brier"],
      "frozen_16_feature_model_brier":mlb["full16_brier"],
      "brier_difference_market_minus_full16":round(float(mlb["book_raw_brier"])-float(mlb["full16_brier"]),9),
      "market_beaten_on_one_game_only":float(mlb["full16_brier"])<float(mlb["book_raw_brier"]),
      "statistically_supported_model_improvement":False,
    }
    move_score={
      "source_frozen_future_two_hour_book_move_rows":early,
      "independent_upcoming_games":movement["distinct_future_official_games"],
      "fixed_early_source_horizon_exploratory_only":movement["by_predeclared_horizon"].get("EARLY_DISCOVERY",0),
      "fixed_three_pp_movement_flags":movement["fixed_gt_3pp_movement_source_records"],
      "future_graded_player_market_rows":graded,
      "future_movement_blocked_pending_official_player_identity":pending,
      "unseen_future_primary_h4_completed_game_blocks":grade.get("by_fixed_horizon",{}).get("H4",{}).get("independent_game_blocks",0),
      "preregistered_model_hypothesis_result":"PENDING_OUTCOMES_NOT_PROVEN",
    }
    return {
      "schema":SCHEMA,
      "observed_at_utc":now.isoformat(),
      "sources_sha256":digests,
      "research_model_records_only":True,
      "game_lines":games,
      "props_and_pickem":props,
      "mlb_full16":mlb_score,
      "mlb_source_price_movement":move_score,
      "nfl_frozen_70_screen":{
         "original_forward_games":n_select["original_frozen_nfl_models"],
         "all_source_abstentions_saved":n_select["original_game_abstentions_saved"],
         "provisional_70_and_value_qualifiers":n_select["provisional_paper_screen_pass_count"],
         "official_future_game_results":n_grade["all_official_games_graded"],
         "profitable_strategy_proven":False,
      },
      "cfb_original_research_learning":{
         "source_generated_at_utc":cfb["generated_at"],
         "unique_recommendations":cfb["unique_recommendations"],
         "settled_research_grades":cfb["settled"],
         "wins":counts.get("WIN",0),"losses":counts.get("LOSS",0),
         "pushes":counts.get("PUSH",0),"pending":counts.get("PENDING",0),
         "source_grade_labels_are_not_executed_wagers":True,
      },
      "experiment_result":{
         "profitable_70_percent_betting_strategy_proven":False,
         "automatic_model_promotion_authorized":False,
         "real_sportsbook_execution_or_paid_return_verified":False,
         "separate_game_cohorts_must_never_be_added_as_independent_bets":True,
      },
    }


def _without_time_and_provenance(view):
    return {k:v for k,v in view.items() if k not in ("observed_at_utc",)}


def verify_history(path):
    previous="0"*64
    history=[]
    if not path.exists():return history
    if path.stat().st_size==0:
        raise ValueError("ORIGINAL_SCORECARD_HISTORY_TRUNCATED_TO_ZERO")
    with path.open("rb") as f:
        for line in f:
            if not line.endswith(b"\n"):
                raise ValueError("INCOMPLETE_ORIGINAL_SCORECARD_HISTORY_LINE")
            try:x=json.loads(line)
            except json.JSONDecodeError as e:raise ValueError("TAMPERED_SCORECARD_HISTORY") from e
            digest=x.get("entry_sha256")
            plain={k:v for k,v in x.items() if k!="entry_sha256"}
            if (x.get("previous_entry_sha256")!=previous or
                sha(canonical(plain))!=digest or not digest):
                raise ValueError("SCORECARD_HASH_CHAIN_CHANGED_OR_TRUNCATED")
            previous=digest
            history.append(x)
    return history


def capture(*,root=ROOT,history=None,current=None,clock=None):
    base=Path(root)/BASE
    history=Path(history) if history else base/HISTORY
    current=Path(current) if current else base/CURRENT
    now=clock or datetime.now(timezone.utc)
    if not now.tzinfo:raise ValueError("NAIVE_SCORECARD_TIME")
    reports,refs=source_reports(root)
    view=build_view(reports,refs,now)
    history.parent.mkdir(parents=True,exist_ok=True)
    with history.with_suffix(history.suffix+".lock").open("a+b") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if current.is_file() and not history.is_file():
            raise ValueError("ORIGINAL_SCORECARD_HISTORY_MISSING_BUT_CURRENT_EXISTS")
        old=verify_history(history)
        last=old[-1] if old else None
        if last and current.is_file():
            try:
                prior_current=json.loads(current.read_bytes())
            except (ValueError,json.JSONDecodeError) as exc:
                raise ValueError("CURRENT_SCORECARD_HASH_CHAIN_READBACK_INVALID") from exc
            if prior_current!=last:
                raise ValueError("CURRENT_SCORECARD_HASH_CHAIN_READBACK_MISMATCH")
        if last:
            # A corrected source that removes prior settled grades is a distinct
            # integrity incident, not an invisible negative-performance reset.
            for tag in ("game_lines","props_and_pickem"):
                before=last["view"][tag]
                after=view[tag]
                if (before["model_version"]==after["model_version"] and
                    (after["settled"]<before["settled"] or
                     after["wins"]<before["wins"] or after["losses"]<before["losses"])):
                    raise ValueError("SILENT_DELETION_OR_RESCORE_OF_PRIOR_FORWARD_RESULTS")
            if (last["view"]["sources_sha256"]==refs):
                if not current.is_file():
                    current.parent.mkdir(parents=True,exist_ok=True)
                    restored=current.with_suffix(".tmp")
                    with restored.open("wb") as f:
                        f.write(json.dumps(last,sort_keys=True,indent=2).encode()+b"\n")
                        f.flush();os.fsync(f.fileno())
                    os.replace(restored,current)
                    if json.loads(current.read_bytes())!=last:
                        raise ValueError("CURRENT_SCORECARD_RECOVERY_FAILED")
                    return {"state":"CURRENT_VIEW_RESTORED_FROM_VERIFIED_ORIGINAL_HISTORY",
                            "history_entries":len(old),"latest":last}
                return {"state":"ORIGINAL_SOURCE_UNCHANGED_NO_DUPLICATE_CHECKPOINT",
                        "history_entries":len(old),"latest":last}
        entry={"previous_entry_sha256":last["entry_sha256"] if last else "0"*64,
               "view":view}
        entry["entry_sha256"]=sha(canonical(entry))
        with history.open("ab") as f:
            f.write(canonical(entry)+b"\n")
            f.flush();os.fsync(f.fileno())
        current.parent.mkdir(parents=True,exist_ok=True)
        temp=current.with_suffix(".tmp")
        with temp.open("wb") as f:
            f.write(json.dumps(entry,sort_keys=True,indent=2).encode()+b"\n")
            f.flush();os.fsync(f.fileno())
        os.replace(temp,current)
        final=verify_history(history)
        if final[-1]!=entry:
            raise ValueError("SAVED_SCORECARD_HASH_HISTORY_READBACK_FAILED")
        return {"state":"APPENDED_VERIFIED_SOURCE_CHANGE",
                "history_entries":len(final),"latest":entry}


def public_projection(entry:dict, *,history_entries:int) -> dict:
    """Whitelist ONLY aggregate research metrics; no athletes, source paths or raw odds."""
    view=entry["view"]
    if (view.get("schema")!=SCHEMA or
        view.get("research_model_records_only") is not True or
        view.get("experiment_result",{}).get("profitable_70_percent_betting_strategy_proven") is not False or
        len(str(entry.get("entry_sha256") or ""))!=64):
        raise ValueError("PUBLIC_FORWARD_PROOF_MUST_DERIVE_FROM_VERIFIED_RESEARCH")
    src={}
    for name,source in (("game_lines",view["game_lines"]),
                        ("props_and_pickem",view["props_and_pickem"])):
        src[name]={
          "model_version":source["model_version"],
          "source_generated_at_utc":source["source_generated_at_utc"],
          "wins":source["wins"],"losses":source["losses"],"pushes":source["pushes"],
          "settled":source["settled"],"independent_game_blocks":source["independent_game_blocks"],
          "hit_rate_pct":source["hit_rate_pct"],
          "source_book_quoted_paper_roi_pct":source["source_book_quoted_paper_roi_pct"],
          "source_market_brier":source["source_no_vig_market_brier"],
          "model_brier":source["model_frozen_brier"],
          "model_minus_market_brier":source["model_minus_market_brier"],
          "proof_status":source["source_promotion_proof_status"],
          "actual_real_money_roi_proven":False,
        }
    mlb=view["mlb_full16"]
    movement=view["mlb_source_price_movement"]
    nfl=view["nfl_frozen_70_screen"]
    cfb=view["cfb_original_research_learning"]
    return {
      "schema":PUBLIC_SCHEMA,
      "research_only":True,
      "proof_status":"NOT_PROVEN",
      "updated_at_utc":view["observed_at_utc"],
      "verified_append_only_history_checkpoints":history_entries,
      "source_receipt_hash_prefix":entry["entry_sha256"][:16],
      "game_lines":src["game_lines"],"props_and_pickem":src["props_and_pickem"],
      "mlb_full16":{
         "completed_independent_game_blocks":mlb["completed_independent_original_full16_games"],
         "same_game_player_predictions":mlb["completed_original_hit_predictions_in_same_game"],
         "source_market_brier":mlb["source_book_market_brier"],
         "original_full16_model_brier":mlb["frozen_16_feature_model_brier"],
         "improvement_statistically_proven":False,
      },
      "mlb_price_movement":{
         "frozen_source_observations":movement["source_frozen_future_two_hour_book_move_rows"],
         "independent_upcoming_games":movement["independent_upcoming_games"],
         "graded_official_player_results":movement["future_graded_player_market_rows"],
         "waiting_for_official_player_bridge":movement["future_movement_blocked_pending_official_player_identity"],
         "research_price_signal_proven":False,
      },
      "nfl_forward":{
         "pregame_frozen_games":nfl["original_forward_games"],
         "source_grade_pending":max(0,nfl["original_forward_games"]-nfl["official_future_game_results"]),
         "fixed_seventy_pct_plus_value_qualifiers":nfl["provisional_70_and_value_qualifiers"],
         "official_game_results":nfl["official_future_game_results"],
         "profitable_betting_strategy_proven":False,
      },
      "cfb_research":{
         "latest_distinct_recommendations":cfb["unique_recommendations"],
         "historically_settled_research_grades":cfb["settled_research_grades"],
         "not_executable_real_money_bets":True,
      },
      "truthfulness":{
         "all_values_based_on_original_source_snapshots":True,
         "paper_roi_not_sportsbook_winnings":True,
         "book_offer_executability_proven":False,
         "automatic_model_promotion_allowed":False,
         "not_real_wager_profit_or_guaranteed_win_rate":True,
         "mlb_price_observations_are_correlated_within_independent_games":True,
      },
    }


def publish_public_proof(*,root=ROOT,history=None,output_paths=None):
    """Only publish a sanitized snapshot copied from a VERIFIED private chain."""
    root=Path(root)
    original=Path(history) if history else root/BASE/HISTORY
    entries=verify_history(original)
    if not entries:raise ValueError("PUBLIC_PROOF_CANNOT_PUBLISH_EMPTY_HISTORY")
    latest=entries[-1]
    if json.loads((root/BASE/CURRENT).read_bytes())!=latest:
        raise ValueError("PRIVATE_CURRENT_NOT_EQUAL_VERIFIED_PROOF_HISTORY")
    public=public_projection(latest,history_entries=len(entries))
    if output_paths is None:
        destinations=[root/"commercial_web/public"/PUBLIC_FILENAME]
        if (root/"commercial_web/dist").is_dir():
            destinations.append(root/"commercial_web/dist"/PUBLIC_FILENAME)
    else:
        destinations=[Path(v) for v in output_paths]
    payload=json.dumps(public,sort_keys=True,indent=2).encode()+b"\n"
    for dest in destinations:
        dest.parent.mkdir(parents=True,exist_ok=True)
        pending=dest.with_suffix(dest.suffix+".tmp")
        with pending.open("wb") as f:
            f.write(payload)
            f.flush();os.fsync(f.fileno())
        os.replace(pending,dest)
        if dest.read_bytes()!=payload:
            raise ValueError("PUBLISHED_SCORECARD_READBACK_CHANGED")
    return {"published":[str(v) for v in destinations],
            "public_payload_bytes":len(payload),
            "public_payload_sha256":sha(payload),
            "history_checkpoint_count":len(entries)}


def main():
    r=capture()
    publish=publish_public_proof()
    view=r["latest"]["view"]
    summary={
        "status":r["state"],"history_entries":r["history_entries"],
        "source_observed_at_utc":view["observed_at_utc"],
        "game_lines":{k:view["game_lines"][k] for k in
                      ("settled","hit_rate_pct","source_book_quoted_paper_roi_pct",
                       "source_promotion_proof_status")},
        "props":{k:view["props_and_pickem"][k] for k in
                 ("settled","hit_rate_pct","source_book_quoted_paper_roi_pct",
                  "source_promotion_proof_status")},
        "mlb_future_market_research":view["mlb_source_price_movement"],
        "all_betting_proven":False,
    }
    print("ZENITH_FORWARD_EVIDENCE_APPEND_ONLY_SCORECARD",json.dumps(summary,sort_keys=True))


if __name__=="__main__":main()
