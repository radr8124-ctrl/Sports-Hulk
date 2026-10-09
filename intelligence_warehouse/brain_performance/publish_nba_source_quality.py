"""Publish only whitelisted historic NBA TOTAL source-quality caveat aggregates.

This is an immutable, 2026-10-09 retrospective audit of a specific
version-locked game-line scorecard. Never call the sensitivity the official
corrected result or silently replace user-facing original research ledgers.
"""
from __future__ import annotations

from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/"reports/NBA_TOTAL_PRESEASON_SOURCE_INDEPENDENCE_RESULTS_2026-10-09.json"
SENSITIVITY=ROOT/"reports/NBA_TOTAL_FORWARD_POOLED_ROI_SENSITIVITY_2026-10-09.json"
PUBLIC_NAME="nba_total_source_quality.json"
SCHEMA="ZENITH_NBA_TOTAL_SOURCE_QUALITY_SENSITIVITY_PUBLIC_V1"


def digest(b):return hashlib.sha256(b).hexdigest()


def project(audit,conflict,*,original_audit_sha):
    old=audit["original_all_alternative_quotes_as_original_ledger_report_NOT_fully_source_time_verified"]
    strict=audit["source_de_duplicated_exact_same_game_market_side_line_first_quote"]
    if (audit.get("schema")!="ZENITH_NBA_TOTAL_2026_PRESEASON_ORIGINAL_LINE_INDEPENDENCE_RESEARCH_V1"
        or audit.get("competition_regime_verified")!="2026_OCTOBER_NBA_PRESEASON_ONLY"
        or audit.get("qualified_as_money_making_invention") is not False
        or audit.get("probability_market_edge_statistically_proven") is not False
        or conflict.get("schema")!="ZENITH_NBA_TOTAL_RETROSPECTIVE_SOURCE_QUALITY_SENSITIVITY_RECEIPT_V1"
        or conflict.get("sensitivity_NOT_corrected_official_full_ledger") is not True
        or conflict.get("sensitivity_keeping_all_non_NBA_TOTAL_lanes_UNAUDITED_unchanged") is not True
        or conflict.get("source_retrospective_audit_sha256")!=original_audit_sha
        or conflict.get("original_forward_summary_sha256")!=audit["original_source_sha256"]["original_game_forward_summary"]
        or conflict.get("original_forward_ledger_sha256")!=audit["original_source_sha256"]["original_game_forward_ledger"]
        or not audit.get("all_original_ledger_rows_accounted_for")):
        raise ValueError("UNVERIFIED_NBA_AUDIT_OR_POOLED_SENSITIVITY_HASH_RELATION")
    if (old["original_ledger_quote_rows"]!=106 or
        strict["original_source_line_records"]!=91 or
        strict["independent_official_game_blocks"]!=19 or
        audit["original_ledger_grade_rows_held_for_official_start_disagreement"]!=7 or
        audit["exact_regime_duplicate_rows_not_independent"]!=8 or
        len(audit["official_start_conflict_minutes"])!=1 or
        audit["official_start_conflict_minutes"][0]!=15.0):
        raise ValueError("UNEXPECTED_LOCKED_NBA_SOURCE_COHORT_COUNTS")
    original_count=int(conflict["original_all_game_lines_settled_source_raw"])
    filtered_count=int(conflict["sensitivity_unique_line_all_game_lines_count"])
    if (original_count-filtered_count !=15
        or conflict["strict_original_game_unique_source_total_lines"]!=strict["original_source_line_records"]
        or conflict["strict_original_source_verified_wins"]!=strict["wins"]
        or conflict["strict_original_source_verified_losses"]!=strict["losses"]
        or conflict["sensitivity_unique_line_all_game_lines_wins"]+
           conflict["sensitivity_unique_line_all_game_lines_losses"]!=filtered_count):
        raise ValueError("NBA_SOURCE_QUALITY_CANNOT_HIDE_OLD_LOSSES")
    interval=strict["independent_game_bootstrap95_source_price_roi_interval_pct"]
    if (len(interval)!=2 or not (interval[0]<0<interval[1])
        or audit["unique_line_model_Brier"]!=audit["unique_line_source_market_fair_Brier"]):
        raise ValueError("SOURCE_QUALITY_CANNOT_CLAIM_MODEL_OUTPERFORMED_BOOKMAKER")
    return {
        "schema":SCHEMA,
        "retroactive_as_of_utc":conflict["generated_utc"],
        "audited_original_snapshot_only":True,
        "retrospective_original_game_lines":{
           "priced_line_observations":original_count,
           "wins":conflict["original_all_game_lines_wins_source_raw"],
           "losses":conflict["original_all_game_lines_losses_source_raw"],
           "original_quoted_paper_roi_pct":conflict["original_all_game_lines_simulated_roi_pct"],
        },
        "isolated_source_quality_sensitivity":{
           "quote_observations":filtered_count,
           "wins":conflict["sensitivity_unique_line_all_game_lines_wins"],
           "losses":conflict["sensitivity_unique_line_all_game_lines_losses"],
           "hypothetical_quote_paper_roi_pct":conflict["sensitivity_unique_line_all_game_lines_simulated_roi_pct"],
           "not_official_restatement_of_all_sports":True,
           "all_other_sport_market_lanes_not_yet_source_graded":True,
        },
        "nba_preseason_audit":{
           "original_total_line_records":old["original_ledger_quote_rows"],
           "duplicate_regime_positions":audit["exact_regime_duplicate_rows_not_independent"],
           "incorrect_original_start_rows_held":audit["original_ledger_grade_rows_held_for_official_start_disagreement"],
           "held_source_start_difference_minutes":15,
           "source_ESPN_start_matched_unique_lines":strict["original_source_line_records"],
           "independent_preseason_games":strict["independent_official_game_blocks"],
           "strict_quote_wins":strict["wins"],
           "strict_quote_losses":strict["losses"],
           "strict_quoted_paper_roi_pct":strict["source_price_paper_roi_pct"],
           "game_cluster_95pct_quote_paper_roi_interval_pct":interval,
           "model_Brier":audit["unique_line_model_Brier"],
           "bookmaker_Brier":audit["unique_line_source_market_fair_Brier"],
           "model_probability_edge_proven":False,
        },
        "audit_sha256_prefix":original_audit_sha[:16],
        "real_money_wagers_or_executable_prices_verified":False,
        "source_frozen_model_or_grade_ledger_mutated":False,
        "genuine_unseen_NBA_regular_season_profitability_proven":False,
    }


def publish(*,audit=AUDIT,sensitivity=SENSITIVITY,paths=None):
    raw=Path(audit).read_bytes()
    r=json.loads(raw)
    j=json.loads(Path(sensitivity).read_bytes())
    public=project(r,j,original_audit_sha=digest(raw))
    destinations=paths if paths is not None else [
        ROOT/"commercial_web/public"/PUBLIC_NAME,
        ROOT/"commercial_web/dist"/PUBLIC_NAME,
    ]
    rawbytes=json.dumps(public,sort_keys=True,indent=2).encode()+b"\n"
    for path in destinations:
        out=Path(path)
        out.parent.mkdir(parents=True,exist_ok=True)
        temp=out.with_suffix(out.suffix+".tmp")
        with temp.open("wb") as f:
            f.write(rawbytes)
            f.flush();os.fsync(f.fileno())
        os.replace(temp,out)
        if out.read_bytes()!=rawbytes:
            raise ValueError("PUBLIC_NBA_QUALITY_DATA_WAS_NOT_WRITTEN_ATOMICALLY")
    return {
        "output_count":len(destinations),
        "public_aggregate_bytes":len(rawbytes),
        "public_aggregate_sha256":digest(rawbytes),
        "quality_result":"ORIGINAL_2026_PRESEASON_SENSITIVITY_NOT_OFFICIAL_PAYOUT"
    }


if __name__=="__main__":
    print("ZENITH_NBA_SOURCE_QUALITY_PUBLIC_CAVEAT",json.dumps(publish(),sort_keys=True))
