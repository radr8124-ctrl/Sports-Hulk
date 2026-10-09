"""Official-outcome grading of FUTURE frozen MLB bookmaker-movement research.

No outcomes from a provider-player name guess. Requires later first-source
full16 verified lineups (UUID -> original MLBAM ID), original frozen model
and independent official MLB Final boxscore analytics. No actual bets/plays.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone
import fcntl,hashlib,json,math,os
from pathlib import Path

from . import freeze_source_price_movement as move
from .build_forward_readiness import ROOT,BASE,moment

OUT=BASE/"MLB_FUTURE_2H_MOVEMENT_SOURCE_OFFICIAL_GRADES.jsonl"
SUMMARY=BASE/"MLB_FUTURE_2H_MOVEMENT_OFFICIAL_GRADE_SUMMARY.json"
MODEL=BASE/"MLB_V4_SIXTEEN_FEATURE_ACTUAL_FORWARD_SHADOW.jsonl"
FINAL=BASE/"MLB_V4_FULL16_SAME_NEW_QUOTE_OFFICIAL_THREEWAY_SCORES.jsonl"
SPEC=move.SPEC
GRADE_SCHEMA="ZENITH_MLB_FUTURE_BOOK_MOVEMENT_ACTUAL_OFFICIAL_MLBAM_HITS_GRADE_V1"


def original_line_index(file):
    grouped=defaultdict(list)
    if not file.is_file():return grouped
    with file.open("rb") as fh:
        for line in fh:
            if not line.strip():continue
            row=json.loads(line)
            key=(int(row["official_game_pk"]),int(row["mlbam_player_id"]))
            grouped[key].append((row,hashlib.sha256(line).hexdigest()))
    return grouped


def unique_movements(movement_rows):
    keys={}
    for r in movement_rows:
        k=(int(r["official_game_pk"]),r["source_provider"],
           r["source_event_uuid"],r["source_player_provider_uuid"],
           r["fixed_asof_horizon"])
        if k in keys:raise ValueError("REPEATED_MOVEMENT_PRIOR_SOURCE")
        keys[k]=r
    return keys


def official_grades_for_frozen(
    movement_rows,full16_rows,official_rows,*,now,spec
):
    if now.tzinfo is None:raise ValueError("GRADE_CLOCK_NOT_OFFSET_AWARE")
    future=unique_movements(movement_rows)
    model_by_provider={}
    for values in full16_rows.values():
        for model,modelhash in values:
            if model.get("research_only") is not True or model.get("betting_play_approved") is not False:
                raise ValueError("SOURCE_MODEL_IS_NOT_OFFICIAL_PREGAME_RESEARCH")
            key=(int(model["official_game_pk"]),str(model["source_provider"]),
                 str(model["source_provider_event_uuid"]),
                 str(model["source_provider_player_uuid"]))
            if key in model_by_provider:
                raise ValueError("MODEL_SOURCE_UUID_TO_MLBAM_AMBIGUOUS")
            model_by_provider[key]=(model,modelhash)
    scored=[]
    waiting=Counter()
    for _,r in future.items():
        if r.get("schema")!=move.SCHEMA or r.get("research_only") is not True:
            raise ValueError("UNVERIFIED_ORIGINAL_PREKICKOFF_MARKET_MOVEMENT")
        if r.get("study_id")!=spec["study_id"]:
            raise ValueError("PREDECLARED_MODEL_STUDY_CHANGED")
        registered=moment(spec["registered_at_utc"])
        at=moment(r["original_current_quote_utc"])
        first=moment(r["source_start_utc"])
        if not all((registered,at,first)) or not registered<=at<first:
            raise ValueError("RESEARCH_MARKET_INPUT_NOT_FROZEN_AFTER_PREDECLARATION")
        k=(int(r["official_game_pk"]),r["source_provider"],
           r["source_event_uuid"],r["source_player_provider_uuid"])
        verified=model_by_provider.get(k)
        if verified is None:
            waiting["NO_PREKICKOFF_FULL16_MLBAM_PLAYER_UUID_BRIDGE"]+=1
            continue
        model,modelhash=verified
        if (not isinstance(model.get("mlbam_player_id"),int)
            or model.get("source_provider")!=r["source_provider"]
            or model.get("source_provider_event_uuid")!=r["source_event_uuid"]
            or model.get("source_provider_player_uuid")!=r["source_player_provider_uuid"]
            or moment(model.get("official_first_pitch_utc"))!=first
            or moment(model.get("first_full_context_shadow_frozen_at_utc")) is None
            or not moment(model["first_full_context_shadow_frozen_at_utc"])<first
            or model.get("has_any_july_outcomes_in_fitted_coefficients") is not False
            or model.get("full_context_is_pre_first_pitch_source_frozen") is not True):
            raise ValueError("NOT_SOURCE_VERIFIED_PREKICKOFF_MLBAM_PLAYER_ID")
        official_key=(int(r["official_game_pk"]),int(model["mlbam_player_id"]))
        actual=official_rows.get(official_key)
        if not actual:
            waiting["OFFICIAL_COMPLETED_GAME_FINAL_NOT_YET_VERIFIED"]+=1
            continue
        if len(actual)!=1:
            raise ValueError("DUPLICATE_INDEPENDENT_MLB_OFFICIAL_FINAL_PLAYER_GRADE")
        grade,original_grade_line_sha=actual[0]
        if (grade.get("research_only") is not True
            or grade.get("official_status")!="Final"
            or grade.get("model_promoted_to_live_play") is not False
            or grade.get("market_bookmaker")!=model.get("selected_sportsbook")
            or grade.get("original_training_model_sha256")!=model.get("frozen_prejuly_model_sha256")
            or grade.get("original_official_pregame_source_sha256")!=model.get("original_lineup_sha256")
            or grade.get("original_model_prospectively_frozen_at_utc")!=model.get("first_full_context_shadow_frozen_at_utc")
            or grade.get("original_source_new_quote_at_utc")!=model.get("source_quote_at_utc")
            or moment(grade.get("official_game_start_utc"))!=first
            or str(grade.get("independent_game_block_id"))!=str(r["official_game_pk"])):
            raise ValueError("INDEPENDENT_OFFICIAL_MLB_FINAL_DOES_NOT_MATCH_PREGAME_IDENTITY")
        final_clock=moment(grade.get("source_final_checked_at_utc"))
        if not final_clock or not first<final_clock<=now:
            raise ValueError("FUTURE_MLB_FINAL_RESULTS_OR_UNTRUSTED_SOURCE_CLOCK")
        hits=grade.get("official_player_hits")
        won=grade.get("actual_hits_over_half")
        if (type(won)!=int or won not in (0,1)
            or type(hits) not in (int,float)
            or not math.isfinite(hits)
            or hits<0 or not float(hits).is_integer()
            or int(hits>=1)!=won):
            raise ValueError("OFFICIAL_PLAYER_HITS_GRADE_WITHOUT_REAL_OUTCOME")
        fair=float(r["registered_unadjusted_market_over_probability"])
        trend=float(r["registered_fixed_trend_over_probability"])
        revert=float(r["registered_fixed_reversion_over_probability"])
        if not all(.02<=p<=.98 and math.isfinite(p) for p in (fair,trend,revert)):
            raise ValueError("FROZEN_PROBABILITY_OUT_OF_RANGE")
        body=json.dumps(r,sort_keys=True,separators=(",",":")).encode()
        scored.append({
            "schema":GRADE_SCHEMA,
            "study_id":spec["study_id"],
            "official_game_pk":int(r["official_game_pk"]),
            "mlbam_player_id":model["mlbam_player_id"],
            "source_provider":r["source_provider"],
            "source_event_uuid":r["source_event_uuid"],
            "source_player_provider_uuid":r["source_player_provider_uuid"],
            "fixed_asof_horizon":r["fixed_asof_horizon"],
            "source_provider_name_only_for_display":r["source_player_provider_name"],
            "source_sportsbook":r["source_sportsbook"],
            "book_price_venue_not_independently_verified_executable":True,
            "frozen_movement_original_record_sha256":hashlib.sha256(body).hexdigest(),
            "full16_verified_MLBAM_bridge_raw_line_sha256":modelhash,
            "independent_official_player_final_raw_line_sha256":original_grade_line_sha,
            "first_model_pre_game_time_utc":model["first_full_context_shadow_frozen_at_utc"],
            "final_independent_source_captured_utc":final_clock.isoformat(),
            "independent_official_game_block_id":str(r["official_game_pk"]),
            "independent_official_player_hits":int(hits),
            "official_hits_over_0_5_binary":won,
            "original_raw_market_fair_brier":round((fair-won)**2,10),
            "pre_registered_fixed_trend_model_brier":round((trend-won)**2,10),
            "pre_registered_fixed_reversion_control_brier":round((revert-won)**2,10),
            "original_market_fair_probability":fair,
            "pre_registered_trend_probability":trend,
            "pre_registered_reversion_probability":revert,
            "production_model_changed":False,
            "real_wager_executed":False,
            "research_only":True,
        })
    return scored,dict(waiting)


def same_key(row):
    return (
      int(row["official_game_pk"]),row["source_provider"],
      row["source_event_uuid"],row["source_player_provider_uuid"],
      row["fixed_asof_horizon"],
    )


def append_verified(path,proposed):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+".lock").open("a+b") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        existing=move.records(path)
        by_key={same_key(r):r for r in existing}
        if len(by_key)!=len(existing):
            raise ValueError("DUPLICATED_EXISTING_OFFICIAL_MOVEMENT_RESULTS")
        new=[];seen=set()
        for entry in proposed:
            key=same_key(entry)
            if key in seen:raise ValueError("DUPLICATED_GRADE_BATCH")
            seen.add(key)
            old=by_key.get(key)
            if old is not None:
                if old!=entry:
                    raise ValueError("OFFICIAL_PLAYER_GRADE_WAS_REWRITTEN_OR_CONTRADICTED")
                continue
            new.append(entry)
        if new:
            with path.open("a",encoding="utf8") as f:
                for entry in new:f.write(json.dumps(entry,sort_keys=True,separators=(",",":"))+"\n")
                f.flush();os.fsync(f.fileno())
        return len(new)


def summarize(grades,waiting,new,*,spec):
    horizons=defaultdict(list)
    for row in grades:
        if row["schema"]!=GRADE_SCHEMA or row["research_only"] is not True:
            raise ValueError("INVALID_OFFICIAL_RESEARCH_GRADE_SCHEME")
        horizons[row["fixed_asof_horizon"]].append(row)
    comparisons={}
    for name,values in sorted(horizons.items()):
        games={int(r["official_game_pk"]) for r in values}
        def score(field):
            return round(sum(r[field] for r in values)/len(values),8)
        mkt=score("original_raw_market_fair_brier")
        tr=score("pre_registered_fixed_trend_model_brier")
        rv=score("pre_registered_fixed_reversion_control_brier")
        comparisons[name]={
            "independent_game_blocks":len(games),
            "official_player_game_rows":len(values),
            "market_source_raw_brier":mkt,
            "fixed_trend_brier":tr,
            "fixed_reversion_brier":rv,
            "trend_minus_raw_market_brier_gain":round(mkt-tr,8),
            "profit_or_market_edge_proven":False,
        }
    primary=comparisons.get("H4")
    return {
      "schema":GRADE_SCHEMA,
      "original_first_known_MLB_Full16_game_is_not_part_of_frozen_movement_study":True,
      "new_official_player_outcomes_recorded":new,
      "source_frozen_price_movement_records":len(move.records(move.OUT)),
      "official_graded_movement_records":len(grades),
      "official_independent_games_graded":len({int(r["official_game_pk"]) for r in grades}),
      "pending_source_reasons":waiting,
      "by_fixed_horizon":comparisons,
      "primary_4h_horizon_statistical_proof_status":
          "NOT_ENOUGH_INDEPENDENT_GAMES" if not primary or
          primary["independent_game_blocks"]<spec["independent_future_game_blocks_needed_for_preliminary_review"]
          else "SAMPLE_SIZE_REACHED_REQUIRES_INDEPENDENT_CLUSTER_CI_AND_REAL_ODDS_PROOF",
      "actual_profitability_betting_threshold_not_proven":True,
      "source_book_quote_independently_executable":False,
      "live_betting_model_or_wagers_changed":False,
    }


def run(*,now=None,source=move.OUT,model=MODEL,official=FINAL,out=OUT,specfile=SPEC):
    observed=now or datetime.now(timezone.utc)
    if not observed.tzinfo:raise ValueError("NAIVE_OFFICIAL_RESEARCH_GRADE_CLOCK")
    spec=json.loads(specfile.read_text())
    freeze=move.records(source)
    move.verify_frozen_archive_lineage(freeze,spec=spec)
    first_original_model=b"".join(model.read_bytes().splitlines(keepends=True)[:18])
    if hashlib.sha256(first_original_model).hexdigest()!=spec["original_full16_existing_18_game_forecasts_sha256"]:
        raise ValueError("ORIGINAL_MLB_FULL16_FIRST_18_MODEL_SOURCE_CHANGED")
    originals=original_line_index(model)
    scores=original_line_index(official)
    possible,waiting=official_grades_for_frozen(
        freeze,originals,scores,now=observed,spec=spec)
    added=append_verified(out,possible)
    saved=move.records(out)
    return summarize(saved,waiting,added,spec=spec)


def main():
    report=run()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temporary=SUMMARY.with_suffix(".tmp")
    with temporary.open("w",encoding="utf8") as f:
        json.dump(report,f,indent=2,sort_keys=True);f.write("\n");f.flush();os.fsync(f.fileno())
    os.replace(temporary,SUMMARY)
    print("ZENITH_MLB_2H_BOOK_MOVEMENT_OFFICIAL_RESEARCH_GRADER",json.dumps(report,sort_keys=True))


if __name__=="__main__":main()
