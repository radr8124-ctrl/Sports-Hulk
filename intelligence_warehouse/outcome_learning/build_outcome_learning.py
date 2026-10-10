#!/usr/bin/env python3
"""Replay frozen bets/results and publish a non-destructive model-learning review."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from .learning_core import (
    VERSION, canonical, diagnosis, lane_rollup, block,
    scored_grade, shadow_calibration, shadow_metrics, when,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "intelligence_warehouse/outcome_learning"
ORIGINAL = ROOT / "intelligence_warehouse/betting_v2/BETTING_V2_ALL_MARKETS_FORWARD_LEDGER.jsonl"
ORIGINAL_NFL = ROOT / "intelligence_warehouse/nfl_advanced_pregame/NFL_FIRST_PREKICKOFF_NINE_FEATURE_SCORE_FORM_SHADOW.jsonl"
NFL_SCORE = ROOT / "intelligence_warehouse/nfl_advanced_pregame/NFL_NINE_FEATURE_OFFICIAL_FINAL_COMPARISON_SUMMARY.json"
NFL_OFFICIAL_SCORED_LEDGER = ROOT / "intelligence_warehouse/nfl_advanced_pregame/NFL_NINE_FEATURE_SAME_BOOK_OFFICIAL_FINAL_SCORES.jsonl"
GRADED_NFL = ROOT / "nfl_live/decision/history/NFL_GRADED_RECOMMENDATIONS.csv"
SHADOW_LOG = OUT / "FROZEN_CALIBRATION_SHADOW.jsonl"
PUBLIC = ROOT / "commercial_web/public/zenith_learning_review.json"
DIST = ROOT / "commercial_web/dist/zenith_learning_review.json"
CURRENT = OUT / "ZENITH_LEARNING_REVIEW_CURRENT.json"
CASE_EVENT = "401872976"


def read_verified(path):
    if not path.exists():
        return b"", None
    original = path.read_bytes()
    sha = hashlib.sha256(original).hexdigest()
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise RuntimeError(f"Original source changed during read: {path}")
    return original, sha


def events_from_raw(data):
    out=[]
    for idx, line in enumerate(data.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row=json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Corrupt original forward row {idx}") from exc
        if not isinstance(row, dict):
            raise ValueError("Unexpected non-object forward row")
        out.append(row)
    return out


def write_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", delete=False, dir=path.parent, suffix=".tmp") as fd:
        temp=Path(fd.name)
        json.dump(payload, fd, indent=2, sort_keys=True)
        fd.write("\n")
        fd.flush()
        os.fsync(fd.fileno())
    os.replace(temp, path)


def score_week4_case(grade_bytes):
    """Retrospective *research* case, never part of first-nine-feature model."""
    if not grade_bytes:
        return {"status":"UNAVAILABLE_NO_ORIGINAL_GRADE_SOURCE","cases":[]}
    rows=list(csv.DictReader(io.StringIO(grade_bytes.decode("utf-8"))))
    saved=[]
    for row in rows:
        if (str(row.get("espn_event_id") or "").replace(".0","")!=CASE_EVENT
            or row.get("lane")!="GAME"
            or row.get("market") not in {"MONEYLINE","SPREAD","TOTAL"}
            or row.get("grade") not in {"WIN","LOSS","PUSH"}):
            continue
        ts=when(row.get("snapshot_at"))
        start=when(row.get("start"))
        if not ts or not start or ts>=start:
            continue
        home,away=row.get("home_score"),row.get("away_score")
        num=lambda x:float(x) if x not in (None,"") else None
        market=row["market"]
        selection=(row.get("selection") or "").strip()
        side=("AWAY" if market in {"MONEYLINE","SPREAD"} else selection.upper())
        # This exact archival matchup was Kansas City AWAY @ Las Vegas HOME;
        # refuse to infer opposing team from an unmatched or unrelated event.
        if market in {"MONEYLINE","SPREAD"} and selection not in {"Kansas City Chiefs","Las Vegas Raiders"}:
            continue
        if market in {"MONEYLINE","SPREAD"}:
            side="AWAY" if selection=="Kansas City Chiefs" else "HOME"
        candidate={
            "market":market,"selection":selection,"selection_key":side,
            "line":(None if market=="MONEYLINE" else num(row.get("line"))),
            "home_score":num(home),"away_score":num(away),
            "grade":row["grade"],
            "original_prediction_utc":ts.isoformat(),
            "kickoff_utc":start.isoformat(),
            "original_decision":row.get("decision"),
            "archived_research_score_not_win_probability":num(row.get("score")),
            "original_recorded_quote_or_line":num(row.get("line")),
            "original_result_event_id":CASE_EVENT,
        }
        if scored_grade(candidate)!=candidate["grade"]:
            continue
        saved.append(candidate)
    # Last source-frozen candidate before kickoff per exact market and side:
    # never choose based on outcome/grade.
    selected={}
    for row in sorted(saved,key=lambda r:r["original_prediction_utc"]):
        selected[(row["market"],row["selection_key"])]=row
    output=[{**r,
        "diagnostic_code":diagnosis(r)[0],
        "observed_reason":diagnosis(r)[1],
        "feature_cause_verified":False,
        "model_nine_feature_forecast_replayed_from_2026_week4":False,
        "actual_wager_or_profitability_proven":False,
    } for r in selected.values()]
    output.sort(key=lambda r:({"MONEYLINE":0,"SPREAD":1,"TOTAL":2}[r["market"]],r["selection"]))
    actuals={(r["away_score"],r["home_score"]) for r in output}
    original_game_identity_consistent=len(actuals)==1 and len(output)==3
    actual_away,actual_home=next(iter(actuals)) if original_game_identity_consistent else (None,None)
    if not original_game_identity_consistent:
        # Do not display one outcome as if it were verified when original
        # market-grade sources disagree on the final game identity/score.
        output=[]
    return {
        "status":"ARCHIVED_PREGAME_RESEARCH_ONLY" if original_game_identity_consistent else "INCONSISTENT_OR_INCOMPLETE_ORIGINAL_RESULT",
        "event_id":CASE_EVENT,"away":"Kansas City Chiefs","home":"Las Vegas Raiders",
        "original_cases":output,"number_of_original_game_market_cases":len(output),
        "postgame_feature_cause_proven":False,
        "outcomes_are_not_executed_wagers":True,
        "result_score_away":actual_away,
        "result_score_home":actual_home,
    }


def nfl_first13_error_review(predictions, original_scorer_rows):
    """Review only same-event pre-frozen model vs independently scored ESPN Final."""
    forecasts={}
    for row in predictions:
        if row.get("research_only") is not True or row.get("betting_play_approved") is not False:
            continue
        key=str(row.get("official_espn_event_id") or "")
        if key in forecasts:
            raise ValueError("Duplicate first pregame NFL frozen forecast")
        forecasts[key]=row
    summaries=[]
    seen=set()
    for r in original_scorer_rows:
        gid=str(r.get("official_espn_event_id") or "")
        if gid in seen:
            raise ValueError("Duplicate independent NFL Final result source")
        seen.add(gid)
        f=forecasts.get(gid)
        if not f:
            continue
        if (r.get("schema")!="NFL_2026_RESEARCH_NINE_FEATURE_SAME_BOOK_VS_INDEPENDENT_ESPN_FINAL_SCORE_V1"
            or r.get("research_only") is not True
            or r.get("sportsbook_wager_executed") is not False
            or r.get("profitable_market_edge_proven") is not False
            or f.get("home_team")!=r.get("home_team")
            or f.get("away_team")!=r.get("away_team")
            or f.get("source_frozen_model_sha256")!=r.get("original_model_sha256")
            or not when(f.get("source_first_real_future_prediction_frozen_at_utc"))
            or not when(r.get("source_real_original_final_observed_at_utc"))
            or not when(f.get("source_first_real_future_prediction_frozen_at_utc"))<when(f.get("official_first_pitch_utc"))
            or not when(f.get("official_first_pitch_utc"))<when(r.get("source_real_original_final_observed_at_utc"))):
            raise ValueError("NFL first original model and official Final evidence conflict")
        model=float(f["nine_feature_score_form_home_win_prob"])
        raw=float(f["original_raw_book_home_fair"])
        if abs(model-float(r["score_form_original_pregame_home_win_probability"]))>1e-7:
            raise ValueError("Frozen NFL original model probability was retrospectively changed")
        if abs(raw-float(r["raw_book_original_pregame_home_win_probability"]))>1e-7:
            raise ValueError("Original NFL sportsbook quote has changed after result")
        home=float(r["official_home_points"]);away=float(r["official_away_points"])
        if home==away or int(home>away)!=r.get("original_home_moneyline_win_binary_outcome"):
            raise ValueError("NFL official final score and binary outcome conflict")
        predicted_home=model>=.5
        winner_home=home>away
        win_correct=predicted_home==winner_home
        summaries.append({
            "event_id":gid,"home":f["home_team"],"away":f["away_team"],
            "official_home_points":int(home),"official_away_points":int(away),
            "predicted_winner":f["home_team"] if predicted_home else f["away_team"],
            "actual_winner":f["home_team"] if winner_home else f["away_team"],
            "model_winner_correct":win_correct,
            "model_pregame_home_probability_pct":round(model*100,3),
            "book_pregame_home_probability_pct":round(raw*100,3),
            "model_brier":round(float(r["score_form_squared_error"]),8),
            "book_brier":round(float(r["raw_book_squared_error"]),8),
            "model_minus_book_brier":round(float(r["score_form_squared_error"])-float(r["raw_book_squared_error"]),8),
            "observed_error_type":"WRONG_MONEYLINE_WINNER" if not win_correct else "CORRECT_MONEYLINE_WINNER",
            "feature_root_cause_verified":False,
            "independent_verified_official_final":True,
            "original_model_coefficients_changed":False,
        })
    summaries.sort(key=lambda x:x["event_id"])
    return {
        "source_type":"FIRST_13_FROZEN_NFL_GAMES_VS_INDEPENDENT_ESPN_FINAL",
        "independently_verified_graded_games":len(summaries),
        "model_correct_winner_count":sum(x["model_winner_correct"] for x in summaries),
        "wrong_winner_count":sum(not x["model_winner_correct"] for x in summaries),
        "pending_original_nfl_games":max(0,len(forecasts)-len(summaries)),
        "no_manual_backfilling_of_predictions":True,
        "individual_games":summaries,
    }


def failure_review(records, limit=18):
    losses=[r for r in records if r.get("grade")=="LOSS"]
    # Stable chronological ordering, not cherry-picked by best/worst ROI.
    losses.sort(key=lambda r:(r["original_start_utc"],r["forward_key"]),reverse=True)
    return [{
        "sport":r.get("sport"),"game_key":r.get("game_key"),
        "lane":r.get("lane_key"),"market":r.get("market"),
        "selection":r.get("selection"),"side":r.get("selection_key"),
        "line":r.get("line"),"grade":"LOSS",
        "predicted_probability_pct":r["model_probability_pct"],
        "market_probability_pct":r["market_probability_pct"],
        "probability_is_market_copy":abs(r["model_probability_pct"]-r["market_probability_pct"])<1e-7,
        "final_away_score":r.get("away_score"),"final_home_score":r.get("home_score"),
        "observed_miss_type":diagnosis(r)[0],
        "what_happened":diagnosis(r)[1],
        "pregame_feature_root_cause_proven":False,
        "original_quote_executable_verified":False,
        "source_event_identity_recorded":r.get("result_source_identity_recorded"),
    } for r in losses[:limit]]


def learning_ideas(lanes):
    research=[]
    actions={
        "MONEYLINE":(
            "CALIBRATE_OUTRIGHT_WIN_PROBABILITY",
            "Test winner-probability calibration on time-separated games against the same-book market baseline."
        ),
        "SPREAD":(
            "MODEL_MARGIN_DISTRIBUTION",
            "Separate margin-of-victory / cover probability from simple game winner; evaluate by exact handicap."
        ),
        "TOTAL":(
            "MODEL_PACE_AND_SCORING_VARIANCE",
            "Investigate pace, offensive efficiency and scoring variance with only pregame inputs."
        ),
    }
    for lane in lanes:
        m=lane["lane"].split("_")[-1]
        if m not in actions:
            continue
        action,why=actions[m]
        n=lane["independent_game_blocks"]
        state="READY_TO_DESIGN_SHADOW_EXPERIMENT" if n>=30 else "WAIT_MORE_INDEPENDENT_GAMES"
        research.append({
            "lane":lane["lane"],"experiment_key":action,
            "why_test_this":why,"independent_completed_games":n,
            "minimum_independent_games_for_fitting":30,"state":state,
            "automatically_applied_to_live_model":False,
            "causal_conclusion_from_single_loss_permitted":False,
            "base_rate_compared_before_promotion":True,
        })
    return research


def generate(root=ROOT, now=None):
    now=now or datetime.now(timezone.utc)
    if not now.tzinfo:
        raise ValueError("Timezone-aware evaluation date required")
    originals, ledger_sha=read_verified(root/ORIGINAL.relative_to(ROOT))
    records,invalid=canonical(events_from_raw(originals))
    settled=[r for r in records if r.get("grade") in {"WIN","LOSS","PUSH"}]
    future=[r for r in records if r.get("grade")=="PENDING"
            and when(r.get("original_start_utc")) and when(r["original_start_utc"])>now]
    groups={block_key for block_key in
            (r["sport"]+"|"+r["game_key"] for r in settled)}
    copied=sum(abs(r["market_probability_pct"]-r["model_probability_pct"])<1e-7 for r in settled)
    lanes=lane_rollup(records)
    # An as-of challenger may freeze only while the ORIGINAL wager remains
    # future. No after-game training, same-game fitting, or retroactive edits.
    queued=[]
    blockers=Counter()
    for row in future:
        if row.get("market") not in {"MONEYLINE","SPREAD","TOTAL"}:
            continue
        proposal=shadow_calibration(row,records)
        if proposal["status"]=="ASOF_SHADOW_RESEARCH_ONLY":
            queued.append(proposal)
        else:
            blockers[proposal["status"]]+=1
    source, frozen_sha=read_verified(root/ORIGINAL_NFL.relative_to(ROOT))
    frozen_first=events_from_raw(source)
    scorer_raw, scorer_sha=read_verified(root/NFL_OFFICIAL_SCORED_LEDGER.relative_to(ROOT))
    first13_postgame=nfl_first13_error_review(frozen_first, events_from_raw(scorer_raw))
    known_outcomes, _=read_verified(root/NFL_SCORE.relative_to(ROOT))
    official_summary=json.loads(known_outcomes.decode()) if known_outcomes else {}
    original_case, case_sha=read_verified(root/GRADED_NFL.relative_to(ROOT))
    shadows_raw, shadow_sha=read_verified(root/SHADOW_LOG.relative_to(ROOT))
    shadows=events_from_raw(shadows_raw)
    report={
        "schema":"ZENITH_POSTGAME_ERROR_REVIEW_V1",
        "generated_at_utc":now.astimezone(timezone.utc).isoformat(),
        "status":"LEARNING_IN_SHADOW_ONLY",
        "mode":"READ_ONLY_REPLAY_NO_LIVE_WEIGHT_CHANGES",
        "source_hashes":{
            "original_betting_v2_all_markets_forward_sha256":ledger_sha,
            "original_nfl_nine_feature_future_sha256":frozen_sha,
            "independently_graded_nfl_first13_source_sha256":scorer_sha,
            "original_nfl_oct4_archive_grade_sha256":case_sha,
            "separate_shadow_ledger_sha256":shadow_sha,
        },
        "snapshot":{
            "frozen_forward_entry_count":sum(r.get("event_type")=="ENTRY" for r in events_from_raw(originals)),
            "valid_event_records":len(records),
            "valid_settled_market_research":len(settled),
            "distinct_settled_game_blocks":len(groups),
            "market_based_predictions_same_as_market":copied,
            "losses_observed":sum(r.get("grade")=="LOSS" for r in settled),
            "original_prediction_snapshot_field_is_pregame_for_settled":sum(r.get("grade_snapshot_is_original_pregame_time") is True for r in settled),
            "outcome_identity_in_original_grade":sum(bool(r.get("result_source_identity_recorded")) for r in settled),
            "grade_consistent_with_recorded_final_scores":len(settled),
            "independent_full_boxscore_source_correlations_performed":0,
            "quarantined_or_invalid_event_reasons":dict(sorted(invalid.items())),
            "frozen_nfl_nine_feature_games":len(frozen_first),
            "frozen_nfl_nine_feature_games_officially_settled":official_summary.get("independent_final_game_blocks",0),
            "live_new_model_adjustments_applied":0,
        },
        "recent_losses":failure_review(records),
        "by_lane":lanes,
        "previous_game_case":score_week4_case(original_case),
        "first_frozen_nfl_model_postgame_review":first13_postgame,
        "hypotheses_for_shadow_tests":learning_ideas(lanes),
        "pre_registered_calibration_shadow":{
            "model_version":VERSION,
            "ready_asof_future_predictions":len(queued),
            "unready_counts":dict(sorted(blockers.items())),
            "sample_pending_candidate":queued[:2],
            "automatic_recommendation_or_model_change":False,
        },
        "frozen_forward_challenger_score":shadow_metrics(records,shadows),
        "review_principles":[
            "A lost probability event is not by itself a broken model: evaluate reliability across independent games.",
            "Explain what the final score shows; do not invent the causal reason for a miss.",
            "An original recommendation snapshot timestamp is not evidence that the final game was known then.",
            "Training outcomes must have been recorded settled before each forecast freeze, on a distinct game.",
            "Same game with multiple lines counts once for precision/confidence; no train/test overlap.",
            "Benchmark Brier, log loss, price and ROI separately; require real closing quotes for CLV.",
            "Every proposed correction stays a frozen forward shadow until a new, independent holdout proves advantage.",
            "No automatic bet, bankroll change, or live model-weight promotion.",
        ],
    }
    return report,queued,ledger_sha


def main(root=ROOT):
    OUT.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=OUT/"outcome_learning_update.lock"
    with lock.open("a+") as fd:
        fcntl.flock(fd,fcntl.LOCK_EX)
        report,ready,original_sha=generate(root=root)
        old_bytes,_=read_verified(SHADOW_LOG)
        already={r.get("original_forward_key") for r in events_from_raw(old_bytes)}
        added=0
        for candidate in ready:
            key=candidate["original_forward_key"]
            if key in already:
                continue
            if when(candidate["game_start_utc"]) <= datetime.now(timezone.utc):
                continue
            candidate["frozen_at_utc"]=datetime.now(timezone.utc).isoformat()
            with SHADOW_LOG.open("a",encoding="utf8") as out:
                out.write(json.dumps(candidate,sort_keys=True,separators=(",",":"))+"\n")
                out.flush()
                os.fsync(out.fileno())
            already.add(key)
            added+=1
        if added:
            report,_,_=generate(root=root)
        report["shadow_entries_newly_frozen"]=added
        for target in [CURRENT, PUBLIC, DIST]:
            if target==DIST and not DIST.parent.exists():
                continue
            write_atomic(target,report)
        print(json.dumps({
            "status":report["status"],
            "settled":report["snapshot"]["valid_settled_market_research"],
            "independent_games":report["snapshot"]["distinct_settled_game_blocks"],
            "model_same_as_market":report["snapshot"]["market_based_predictions_same_as_market"],
            "original_oct4_games":report["previous_game_case"].get("number_of_original_game_market_cases"),
            "shadow_created":added,
            "pending_frozen_nfl":report["snapshot"]["frozen_nfl_nine_feature_games"],
            "quarantine":report["snapshot"]["quarantined_or_invalid_event_reasons"],
        },indent=2))


if __name__=="__main__":
    main()
