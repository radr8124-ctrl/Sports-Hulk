"""Honest NBA-total preseason forward-result audit; source ledgers READ ONLY.

This is a retrospective *diagnostic of an already examined 2026 preseason
sample*. It does not create a model, pick, future betting experiment, source
grade, sportsbook ROI certification or a claim of independent wagering.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random

import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SPEC=ROOT/"reports/ZENITH_NBA_TOTAL_PRESEASON_INDEPENDENCE_AUDIT_PREREG_2026-10-09.json"
OUT=ROOT/"reports/NBA_TOTAL_PRESEASON_SOURCE_INDEPENDENCE_RESULTS_2026-10-09.json"
REPORT_SCHEMA="ZENITH_NBA_TOTAL_2026_PRESEASON_ORIGINAL_LINE_INDEPENDENCE_RESEARCH_V1"
ALIASES={"NYK":"NY","GSW":"GS","NOP":"NO","UTA":"UTAH","WAS":"WSH","SAS":"SA"}


def digest(content):return hashlib.sha256(content).hexdigest()


def stamp(value):
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if dt.tzinfo is None:raise ValueError("MISSING_ORIGINAL_SOURCE_OFFSET")
    return dt.astimezone(timezone.utc)


def original_identity(row):
    # These four fields identify a specific *prediction market line*, while
    # forward_key may additionally contain an old or new regime label.
    return (
        str(row["sport"]),
        str(row["game_key"]),
        str(row["market"]),
        str(row["selection_key"]),
        float(row["line"]),
    )


def prices(american):
    odds=float(american)
    if not math.isfinite(odds) or not 100<=abs(odds)<=10000:
        raise ValueError("ORIGINAL_SOURCE_ODDS_NOT_REALISTIC")
    return odds/100 if odds>0 else 100/abs(odds)


def unit(row):
    label=str(row["grade"])
    if label=="PUSH":return 0.0
    if label=="LOSS":return -1.0
    if label=="WIN":return prices(row["entry_american_odds"])
    raise ValueError("CANNOT_USE_PENDING_GAME_GRADE_FOR_HISTORICAL_PERFORMANCE")


def official_nba_games(frame):
    if not {"event_id","start","season","season_type","home_team","away_team",
            "home_score","away_score","completed"}.issubset(frame.columns):
        raise ValueError("NBA_HISTORY_MISSING_ESPN_GAME_ID_SCORE")
    completed=frame[(frame.season==2027)&(frame.season_type==1)&(frame.completed==True)]
    result={}
    for row in completed.to_dict("records"):
        event=str(row["event_id"])
        at=stamp(row["start"])
        home=str(row["home_team"]);away=str(row["away_team"])
        pair=(away,home)
        if event in result:raise ValueError("DUPLICATED_ESPN_PRESEASON_FINAL_GAME_ID")
        h=float(row["home_score"]);a=float(row["away_score"])
        if any(not math.isfinite(v) or v<0 or not v.is_integer() for v in (h,a)):
            raise ValueError("OFFICIAL_ESPN_GAME_SCORE_NOT_VERIFIED")
        result[event]={"official_event_id":event,"start":at,"home":home,
                       "away":away,"total":int(h+a),"official_season":2027,
                       "official_season_type":"PRESEASON"}
    return result


def source_game_key(row):
    parts=str(row["game_key"]).split("|")
    if len(parts)!=3:raise ValueError("SOURCE_GAME_KEY_MISSING_OFFICIAL_TEAMS")
    # ESPN uses the following unambiguous team abbreviation aliases.
    return (ALIASES.get(parts[1],parts[1]),ALIASES.get(parts[2],parts[2]))


def attest_entries(source,official_games):
    verified=[]
    quarantined=[]
    official_events=set()
    future_violations=[]
    for r in source:
        if (r.get("model_version")!="BETTING_V2_ALL_MARKETS_2026_10_05"
            or r.get("sport")!="NBA" or r.get("lane_key")!="NBA_TOTAL"
            or r.get("market")!="TOTAL" or r.get("grade") not in ("WIN","LOSS","PUSH")
            or r.get("selection_key") not in ("OVER","UNDER")
            or r.get("live_rule_changed") is not False):
            raise ValueError("NON_FROZEN_OR_NON_TOTAL_OR_UNAUTHORIZED_ROW")
        at=stamp(r["event_start"])
        capture=stamp(r["captured_at"])
        if capture>=at:
            future_violations.append(r["forward_key"])
            continue
        if r.get("entry_probability_source") and r.get("entry_probability_source") not in (
             "MARKET_CALIBRATED","MARKET_RAW","MARKET_REFERENCE",
             "MARKET_REFERENCE_INSUFFICIENT_HISTORY"):
            raise ValueError("ORIGINAL_MARKET_PROBABILITY_SOURCE_CHANGED")
        pair=source_game_key(r)
        matches=[g for g in official_games.values() if
            (g["away"],g["home"])==pair and
            abs((g["start"]-at).total_seconds())<=180]
        if len(matches)!=1:
            # No guessed ESPN event when book-source start differs.
            # Preserve every original settled ledger row but exclude
            # ambiguous/off-time sources from strict source verification.
            nearby=[g for g in official_games.values() if
                (g["away"],g["home"])==pair and
                abs((g["start"]-at).total_seconds())<=3600]
            delta=(nearby[0]["start"]-at).total_seconds()/60 if len(nearby)==1 else None
            quarantined.append({
                "original_game_key":str(r["game_key"]),
                "reason":"NBA_BOOK_EVENT_START_DIFFERS_FROM_OFFICIAL_ESPN_FINAL"
                      if delta is not None else "NBA_NO_UNIQUE_ESPN_FINAL_IDENTITY",
                "original_start_to_ESPN_start_minutes":delta,
            })
            continue
        official=matches[0]
        line=float(r["line"])
        if not math.isfinite(line) or line<90 or line>350:
            raise ValueError("SOURCE_TOTAL_LINE_OUTSIDE_REAL_GAME_RANGE")
        expected=("PUSH" if float(official["total"])==line else
                  "WIN" if (r["selection_key"]=="OVER" and official["total"]>line) or
                         (r["selection_key"]=="UNDER" and official["total"]<line) else "LOSS")
        if expected!=r["grade"]:
            raise ValueError(f"NBA_ORIGINAL_FORWARD_GRADE_CONTRADICTS_ESPN_FINAL:{r['forward_key']}")
        if not r.get("forward_key") or r.get("entry_american_odds") is None:
            raise ValueError("ORIGINAL_PRICE_OR_FORWARD_KEY_MISSING")
        prices(r["entry_american_odds"])
        o=dict(r)
        o["_source_official_event_id"]=official["official_event_id"]
        o["_source_official_points_total"]=official["total"]
        o["_source_official_pregame_regime"]=official["official_season_type"]
        verified.append(o)
        official_events.add(official["official_event_id"])
    if future_violations:
        raise ValueError(f"NBA_SOURCE_QUOTE_CAPTURE_AFTER_OFFICIAL_KICKOFF:{len(future_violations)}")
    return verified,len(official_events),quarantined


def dedup_first_market_line(rows):
    by={}
    for row in rows:
        key=original_identity(row)
        current=by.get(key)
        if current is None or (row["captured_at"],row["forward_key"])<(
            current["captured_at"],current["forward_key"]):
            by[key]=row
    return sorted(by.values(),key=lambda r:(r["captured_at"],r["forward_key"]))


def one_first_per_game(unique_market_lines):
    by={}
    for row in unique_market_lines:
        key=row["_source_official_event_id"]
        current=by.get(key)
        if current is None or (row["captured_at"],row["forward_key"])<(
            current["captured_at"],current["forward_key"]):
            by[key]=row
    return sorted(by.values(),key=lambda r:(r["captured_at"],r["forward_key"]))


def metrics(rows,*,iterations=2000,seed=20261009):
    if not rows:raise ValueError("NO_NBA_QUALIFIED_SOURCE_SAMPLE")
    grouped=defaultdict(list)
    for r in rows:
        grouped[r["_source_official_event_id"]].append(r)
    order=sorted(grouped)
    units=[unit(r) for r in rows]
    total=sum(units)
    wins=sum(r["grade"]=="WIN" for r in rows)
    losses=sum(r["grade"]=="LOSS" for r in rows)
    n=len(rows)
    blocks=len(order)
    by_game=[sum(unit(r) for r in grouped[g])/len(grouped[g]) for g in order]
    rng=random.Random(seed)
    statistic=[]
    for _ in range(iterations):
        sampled=[order[rng.randrange(blocks)] for _ in order]
        samples=[unit(r) for g in sampled for r in grouped[g]]
        statistic.append(100*sum(samples)/len(samples))
    statistic.sort()
    def quantile(q):
        pos=q*(iterations-1)
        lo=int(math.floor(pos))
        hi=int(math.ceil(pos))
        return statistic[lo]+(statistic[hi]-statistic[lo])*(pos-lo)
    concentrations=sorted((sum(unit(r) for r in v) for v in grouped.values()),reverse=True)
    return {
        "original_source_line_records":n,
        "independent_official_game_blocks":blocks,
        "wins":wins,"losses":losses,
        "pushes":n-wins-losses,
        "win_rate_pct":round(100*wins/max(1,wins+losses),4),
        "source_price_paper_units":round(total,6),
        "source_price_paper_roi_pct":round(100*total/n,4),
        "independent_game_equal_weight_average_per_line_paper_roi_pct":round(
            100*sum(by_game)/blocks,4),
        "independent_game_bootstrap95_source_price_roi_interval_pct":[
            round(quantile(.025),3),round(quantile(.975),3)],
        "source_top_three_official_games_paper_profit_share_pct":
            round(100*sum(concentrations[:3])/total,3) if total>0 else None,
        "real_money_wager_return_or_book_executability_proven":False,
    }


def evaluate(preregistered,official):
    by_name=preregistered["source_relative_paths"]
    sources={}
    for name,path in by_name.items():
        f=ROOT/path
        digest_source=digest(f.read_bytes())
        if digest_source!=preregistered["source_input_sha256"][name]:
            raise ValueError("ORIGINAL_PRE_REGISTERED_FORWARD_SOURCE_CHANGED:"+name)
        sources[name]=f
    from intelligence_warehouse.betting_v2 import build_betting_v2_all_markets_forward as original
    captured=[x for x in original.canonical().values() if
              x.get("model_version")==preregistered["target_model_version"] and
              x.get("lane_key")==preregistered["source_lane"] and
              x.get("grade") in preregistered["source_grades"]]
    if len({r["forward_key"] for r in captured})!=len(captured):
        raise ValueError("DUPLICATE_FORWARD_ENTRIES_PRESENT_AFTER_CANONICALIZATION")
    as_report=json.loads(sources["original_game_forward_summary"].read_text())
    lane=as_report["by_lane"]["NBA_TOTAL"]["all_predictions"]
    if (len(captured)!=lane["settled"]
        or sum(r["grade"]=="WIN" for r in captured)!=lane["wins"]
        or sum(r["grade"]=="LOSS" for r in captured)!=lane["losses"]):
        raise ValueError("ORIGINAL_REPORT_TOTALS_CONTRADICT_SOURCE_EVENTS")
    official_by_event=official_nba_games(official)
    rows,games,quarantined=attest_entries(captured,official_by_event)
    if len(rows)+len(quarantined)!=len(captured):
        raise ValueError("ORIGINAL_SOURCE_PRESEASON_ROWS_LOST_DURING_OFFICIAL_AUDIT")
    if games>lane["independent_blocks"] or not games:
        raise ValueError("ESPN_OFFICIAL_GAME_BLOCK_COUNT_DIFFERS_FROM_COHORT")
    original_label_counts=Counter(r["grade"] for r in captured)
    if sum(original_label_counts.values())!=lane["settled"]:
        raise ValueError("OLD_REPORTED_ORIGINAL_RESULTS_WERE_REMOVED")
    unique=dedup_first_market_line(rows)
    pergame=one_first_per_game(unique)
    if len(unique)>=len(rows) or len(pergame)!=len({r["_source_official_event_id"] for r in unique}):
        raise ValueError("DUPLICATE_ANALYSIS_EXPECTED_OR_PER_GAME_IDENTITY_CHANGED")
    clean=metrics(unique,iterations=2000,seed=20261009)
    single=metrics(pergame,iterations=2000,seed=20261009)
    original_source_metrics={
        "original_ledger_quote_rows":len(captured),
        "original_source_research_grade_wins":lane["wins"],
        "original_source_research_grade_losses":lane["losses"],
        "original_source_research_game_blocks_claimed":lane["independent_blocks"],
        "original_undifferentiated_alt_line_paper_roi_pct":lane["roi_pct"],
        "original_undifferentiated_alt_line_paper_units":lane["units"],
        "NOT_all_verified_for_exact_current_official_game_start":True,
    }
    if round(sum(unit(r) for r in captured),4)!=round(float(lane["units"]),4):
        raise ValueError("ORIGINAL_FORWARD_ROI_NOT_REPRODUCIBLE")
    regime_rows=Counter(
        "SOURCE_REGIME_TAG_PRESEASON" if r.get("competition_regime")=="PRESEASON"
        else "SOURCE_REGIME_TAG_MISSING" if r.get("competition_regime") is None
        else "WRONG_TAG_"+str(r.get("competition_regime"))
        for r in rows
    )
    if set(regime_rows)-{"SOURCE_REGIME_TAG_PRESEASON","SOURCE_REGIME_TAG_MISSING"}:
        raise ValueError("INCORRECT_PRESEASON_MODEL_SCOPE")
    repeated=defaultdict(list)
    for r in rows:repeated[original_identity(r)].append(r)
    doubles={str(k):len(r) for k,r in repeated.items() if len(r)>1}
    if any(n!=2 for n in doubles.values()):
        raise ValueError("UNEXPECTED_MULTI_REGIME_SOURCE_RECORD_REPEAT_COUNT")
    if any({x["grade"] for x in items}!={items[0]["grade"]} for items in repeated.values() if len(items)>1):
        raise ValueError("SAME_SOURCE_TOTAL_GRADE_CONFLICT_BETWEEN_REGIME_VERSIONS")
    paired_brier=lambda frame:(
        round(sum((float(r["entry_market_reference_probability_pct"])/100-(r["grade"]=="WIN"))**2
                  for r in frame)/len(frame),6),
        round(sum((float(r["entry_v2_probability_pct"])/100-(r["grade"]=="WIN"))**2
                  for r in frame)/len(frame),6))
    bookb,modelb=paired_brier(unique)
    return {
        "schema":REPORT_SCHEMA,
        "status":"SOURCE_GRADE_RECONCILED_RETROSPECTIVE_NOT_PROSPECTIVE_PROOF",
        "source_preregistration_sha256":digest(SPEC.read_bytes()),
        "original_source_sha256":preregistered["source_input_sha256"],
        "first_version":preregistered["target_model_version"],
        "research_lane":"NBA_TOTAL",
        "competition_regime_verified":"2026_OCTOBER_NBA_PRESEASON_ONLY",
        "all_original_ledger_rows_accounted_for":len(rows)+len(quarantined)==len(captured),
        "original_ledger_grade_rows_held_for_official_start_disagreement":len(quarantined),
        "official_start_conflict_reason_counts":dict(Counter(q["reason"] for q in quarantined)),
        "official_start_conflicting_games":sorted(set(q["original_game_key"] for q in quarantined)),
        "official_start_conflict_minutes":sorted(set(q["original_start_to_ESPN_start_minutes"] for q in quarantined if q["original_start_to_ESPN_start_minutes"] is not None)),
        "independent_source_event_start_and_final_grade_all_verified":len(quarantined)==0,
        "independent_official_game_blocks_verified":games,
        "regime_source_tag_counts":dict(regime_rows),
        "exact_quote_grade_dupe_market_identities":len(doubles),
        "exact_regime_duplicate_rows_not_independent":len(rows)-len(unique),
        "number_of_games_with_more_than_one_alternative_total_line":sum(
            1 for count in Counter(r["_source_official_event_id"] for r in unique).values() if count>1),
        "original_all_alternative_quotes_as_original_ledger_report_NOT_fully_source_time_verified":original_source_metrics,
        "strict_official_time_matched_all_alternative_quotes":metrics(rows,iterations=2000,seed=20261009),
        "source_de_duplicated_exact_same_game_market_side_line_first_quote":clean,
        "retrospective_earliest_market_quote_only_one_per_ESPN_game":single,
        "unique_line_source_market_fair_Brier":bookb,
        "unique_line_model_Brier":modelb,
        "model_brier_better_than_book":modelb<bookb,
        "probability_market_edge_statistically_proven":False,
        "forward_regular_season_results_included":0,
        "future_unseen_precommitted_strategy_verified":False,
        "real_sportsbook_executable_market_price_verified":False,
        "new_model_training_or_live_betting_picks_changed":False,
        "qualified_as_money_making_invention":False,
        "research_only_not_true_executable_ROI":True,
    }


def main():
    prereg=json.loads(SPEC.read_text())
    if (prereg["model_promotion_allowed"] is not False or
        prereg["no_modification_to_original_ledgers_or_public_betting_dashboard"] is not True or
        prereg["class"]!="RETROSPECTIVE_SOURCE_TRUTH_DIAGNOSTIC_NOT_PRISTINE_UNSEEN_PROOF"):
        raise ValueError("ORIGINAL_SOURCE_AUDIT_PREREGISTRATION_CHANGED")
    sources=prereg["source_relative_paths"]
    if set(sources)!={"original_game_forward_ledger",
                      "original_game_forward_summary",
                      "independent_NBA_ESPN_game_history"}:
        raise ValueError("SCOPE_ORIGINAL_SOURCE_REPORT_CHANGED")
    original=pd.read_csv(ROOT/sources["independent_NBA_ESPN_game_history"],low_memory=False)
    result=evaluate(prereg,original)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open("x") as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write("\n")
        f.flush();os.fsync(f.fileno())
    print("ZENITH_NBA_PRESEASON_ORIGINAL_SOURCE_CORRELATION_AUDIT",json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
