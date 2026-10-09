"""Freeze future-only, exact-book MLB 0.5-hit fair-price movement research.

No model refit, player outcome inference, sportsbook wagers, live plays, or
postgame-grade writing. Provider capture timestamps are AGGREGATOR observations,
not independently verified individual sportsbook quote updates. Per-game
outcome testing requires a later separate authenticated MLBAM crosswalk.
"""
from __future__ import annotations

from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
import fcntl,hashlib,json,math,os
from pathlib import Path
import pandas as pd

from .audit_upcoming_market_alignment import source_proof,implied
from .build_forward_readiness import (
    ROOT,BASE,MASTER,SUMMARY as READINESS,CACHE,moment,
)

SPEC=ROOT/"reports/ZENITH_MLB_2H_SOURCE_PRICE_MOVEMENT_FUTURE_PREREG_2026-10-09.json"
HISTORY=ROOT/"mlb_live/markets/history"
OUT=BASE/"MLB_FUTURE_ASOF_2H_PRICE_MOVEMENT_FROZEN.jsonl"
SUMMARY=BASE/"MLB_FUTURE_ASOF_2H_PRICE_MOVEMENT_SUMMARY.json"
FROZEN=BASE/"MLB_V4_SIXTEEN_FEATURE_ACTUAL_FORWARD_SHADOW.jsonl"
SCHEMA="ZENITH_MLB_FUTURE_ASOF_BOOK_TWO_HOUR_PRICE_MOVEMENT_V1"
REQUIRED={
 "provider","sportsbook","event_id","start","away_team","home_team",
 "market","market_subtype","side","line","price_american",
 "player_id","player","captured_at",
}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def records(path):
    if not path.is_file():return []
    with path.open(encoding="utf8") as f:
        return [json.loads(line) for line in f if line.strip()]


def clip(v):
    return min(.975,max(.025,float(v)))


def horizon(lead,spec):
    tol=spec["horizon_tolerance_minutes"] / 60
    for name,h in (("H24",24),("H4",4),("H1",1)):
        if abs(lead-h)<=tol:return name
    if 24+tol<lead<=72:return "EARLY_DISCOVERY"
    return None


def _original_snapshot_at(path):
    try:
        at=datetime.strptime(path.stem.split("_")[-1],"%Y%m%dT%H%M%SZ")
        return at.replace(tzinfo=timezone.utc)
    except (ValueError,IndexError):
        raise ValueError("UNVERIFIED_VENDOR_ARCHIVE_ORIGINAL_TIME")


def audited_snapshot(path,fixtures,now):
    data=path.read_bytes()
    if len(data)>60*1024*1024:
        raise ValueError("UNBOUNDED_ORIGINAL_SPORTSBOOK_SNAPSHOT")
    frame=pd.read_csv(path,low_memory=False)
    if len(frame)>250000 or not REQUIRED.issubset(frame.columns):
        raise ValueError("SOURCE_MARKET_ARCHIVE_SCHEMA_OR_SIZE_CHANGED")
    expected=_original_snapshot_at(path)
    if expected>now+timedelta(minutes=2):
        raise ValueError("SOURCE_MARKET_ARCHIVE_SNAPSHOT_FROM_FUTURE")
    eligible={}
    sourcegroups=defaultdict(list)
    provider_event_games=defaultdict(set)
    reasons=Counter()
    for r in frame.itertuples(index=False):
        x=r._asdict()
        if (str(x["market"])!="PLAYER_TOTAL" or
            str(x["market_subtype"])!="PLAYER_TOTAL_HITS" or
            str(x["side"]).upper() not in ("OVER","UNDER")):
            continue
        if pd.isna(x["line"]) or abs(float(x["line"])-.5)>1e-9:continue
        by_name=[f for f in fixtures.values()
                 if x["home_team"]==f["home"] and x["away_team"]==f["away"]]
        if not by_name:
            reasons["UNMATCHED_OR_AMBIGUOUS_OFFICIAL_GAME"]+=1
            continue
        bookstart=moment(x["start"])
        matches=[f for f in by_name if bookstart is not None and
                 abs((bookstart-f["start"]).total_seconds())<=180]
        if not matches:
            reasons["WRONG_ORIGINAL_BOOK_GAME_START"]+=1
            continue
        if len(matches)!=1:
            reasons["TWO_GAMES_WITH_SAME_TEAMS_AND_NEAR_IDENTICAL_START"]+=1
            continue
        fixture=matches[0]
        captured=moment(x["captured_at"])
        if (captured is None or captured>=fixture["start"] or captured>now
            or abs((captured-expected).total_seconds())>120):
            reasons["ORIGINAL_AGGREGATOR_CAPTURE_TIME_NOT_ATTESTED"]+=1
            continue
        fields=["provider","sportsbook","event_id","player_id","player"]
        if any(not isinstance(x[k],str) or not x[k].strip() or x[k].lower()=="nan" for k in fields):
            reasons["UNIDENTIFIED_PROVIDER_BOOK_OR_PLAYER"]+=1
            continue
        bookprob=implied(x["price_american"])
        if bookprob is None:
            reasons["INVALID_ORIGINAL_BOOK_PRICE"]+=1
            continue
        key=(fixture["pk"],str(x["provider"]),str(x["event_id"]),
             str(x["sportsbook"]),str(x["player_id"]),str(x["player"]))
        sourcegroups[key].append((str(x["side"]).upper(),float(x["price_american"]),bookprob,captured))
        provider_event_games[(key[1],key[2])].add(key[0])
    for key,legs in sourcegroups.items():
        if len(provider_event_games[(key[1],key[2])])!=1:
            reasons["PROVIDER_EVENT_UUID_COLLIDES_BETWEEN_GAMES"]+=len(legs)
            continue
        if len(legs)!=2 or {x[0] for x in legs}!={"OVER","UNDER"}:
            reasons["SOURCE_NOT_UNIQUE_EXACT_SAME_BOOK_TWO_SIDES"]+=len(legs)
            continue
        if legs[0][3]!=legs[1][3]:
            reasons["OVER_UNDER_ORIGINAL_CAPTURE_TIME_NOT_SAME"]+=2
            continue
        prices={x[0]:x for x in legs}
        vig=prices["OVER"][2]+prices["UNDER"][2]
        if not 1.000001<vig<=1.25:
            reasons["INVALID_SOURCE_BOOK_OVERROUND"]+=2
            continue
        eligible[key]={
            "captured":legs[0][3],
            "source_file":str(path.relative_to(ROOT)),
            "source_sha256":sha(data),
            "original_book_start":fixture_start(fixtures[key[0]]),
            "book_over_american":prices["OVER"][1],
            "book_under_american":prices["UNDER"][1],
            "source_no_vig_over":prices["OVER"][2]/vig,
            "overround":vig,
        }
    return eligible,reasons


def fixture_start(fixture):
    return fixture["start"].isoformat()


def _book_ranking(name,spec):
    order=spec["book_deduplication_order"]
    return order.index(name) if name in order else len(order)


def movement_candidates(history,spec,fixtures,now,registered,*,scan_files=None):
    """Only append a fixed record for original current source AFTER registration."""
    sources=list(scan_files) if scan_files is not None else sorted(history.glob("MLB_PLAYER_PROP_MARKET_*.csv"))
    n=int(spec["maximum_market_history_source_csvs_per_run"])
    sources=sorted(sources)[-n:]
    snapgroups=[]
    rejected=Counter()
    for p in sources:
        if _original_snapshot_at(p)>now+timedelta(minutes=2):continue
        pairs,reasons=audited_snapshot(p,fixtures,now)
        rejected.update(reasons)
        snapgroups.append(pairs)
    source_event_game_ids=defaultdict(set)
    for group in snapgroups:
        for key in group:
            source_event_game_ids[(key[1],key[2])].add(key[0])
    collided={identity for identity,game_ids in source_event_game_ids.items() if len(game_ids)>1}
    if collided:
        for group in snapgroups:
            for key in list(group):
                if (key[1],key[2]) in collided:
                    rejected["PROVIDER_EVENT_UUID_REUSED_FOR_DIFFERENT_GAME_STARTS"]+=1
                    group.pop(key)
    latest={}
    for group in snapgroups:
        for key,rec in group.items():
            if rec["captured"]>=registered and rec["captured"]<=now:
                if key not in latest or rec["captured"]>latest[key]["captured"]:
                    latest[key]=rec
    fresh={}
    for key,r in latest.items():
        pk,provider,event_id,book,pid,player=key
        start=fixtures[pk]["start"]
        age=(now-r["captured"]).total_seconds()/60
        if age<0 or age>spec["max_age_of_current_quote_at_freeze_minutes"]:
            rejected["NEW_CURRENT_QUOTE_NOT_FRESH_TO_EVALUATION_CLOCK"]+=1
            continue
        lead=(start-r["captured"]).total_seconds()/3600
        label=horizon(lead,spec)
        if not label:
            rejected["NOT_IN_FIXED_PREKICKOFF_HORIZON"]+=1
            continue
        older=[]
        for group in snapgroups:
            prior=group.get(key)
            if prior is None or prior["captured"]>=r["captured"]:continue
            gap=(r["captured"]-prior["captured"]).total_seconds()/60
            if spec["earlier_comparison_min_minutes"]<=gap<=spec["earlier_comparison_max_minutes"]:
                older.append((abs(gap-spec["earlier_comparison_quote_target_minutes"]),
                              prior["captured"],prior,gap))
        if not older:
            rejected["MISSING_ORIGINAL_SAME_BOOK_TWO_HOUR_REFERENCE"]+=1
            continue
        _,_,old,minutes=min(older,key=lambda z:(z[0],z[1]))
        if (old["source_file"]==r["source_file"] or
            old["captured"]>=r["captured"] or
            r["source_no_vig_over"] is None):
            raise ValueError("NOT_DISTINCT_PREVIOUS_SAME_BOOK_SOURCE_QUOTES")
        fair=float(r["source_no_vig_over"])
        fair_before=float(old["source_no_vig_over"])
        movement=fair-fair_before
        # Fixed challengers were preregistered BEFORE eligible future games finish.
        trend=clip(fair+0.5*movement)
        reversion=clip(fair-0.5*movement)
        line={
          "schema":SCHEMA,
          "study_id":spec["study_id"],
          "official_game_pk":pk,
          "source_start_utc":start.isoformat(),
          "source_home_team":fixtures[pk]["home"],
          "source_away_team":fixtures[pk]["away"],
          "fixed_asof_horizon":label,
          "source_provider":provider,
          "source_event_uuid":event_id,
          "source_sportsbook":book,
          "source_player_provider_uuid":pid,
          "source_player_provider_name":player,
          "independent_MLBAM_player_identity_matched":False,
          "original_current_quote_utc":r["captured"].isoformat(),
          "original_prior_quote_utc":old["captured"].isoformat(),
          "original_current_raw_archive":r["source_file"],
          "original_current_raw_sha256":r["source_sha256"],
          "original_prior_raw_archive":old["source_file"],
          "original_prior_raw_sha256":old["source_sha256"],
          "source_prior_book_over_american":old["book_over_american"],
          "source_prior_book_under_american":old["book_under_american"],
          "source_current_book_over_american":r["book_over_american"],
          "source_current_book_under_american":r["book_under_american"],
          "original_book_overround_current":round(float(r["overround"]),9),
          "original_book_fair_over_half_at_prior_quote":round(fair_before,9),
          "original_book_fair_over_half_at_current_quote":round(fair,9),
          "source_2hour_book_fair_over_movement_pp":round(100*movement,6),
          "source_2hour_reference_age_minutes":round(minutes,2),
          "fixed_movement_exceeds_3pp":abs(movement)*100>=spec["prespecified_movement_threshold_pp"],
          "registered_fixed_trend_over_probability":round(trend,9),
          "registered_fixed_reversion_over_probability":round(reversion,9),
          "registered_unadjusted_market_over_probability":round(fair,9),
          "source_original_books_observed_not_executable":True,
          "original_game_over_or_under_hits_unknown":True,
          "production_bet_or_model_promotion":False,
          "research_only":True,
        }
        keep=(pk,provider,event_id,pid,label)
        existing=fresh.get(keep)
        if existing is None or (_book_ranking(book,spec),book)<(_book_ranking(existing["source_sportsbook"],spec),existing["source_sportsbook"]):
            fresh[keep]=line
    return sorted(fresh.values(),key=lambda r:(r["official_game_pk"],r["fixed_asof_horizon"],
                                              r["source_provider"],r["source_event_uuid"],
                                              r["source_player_provider_uuid"])),dict(rejected),len(snapgroups)


def append_rows(path,proposed):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+".lock").open("a+b") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        before=records(path)
        def unique(x):
            return (int(x["official_game_pk"]),x["source_provider"],x["source_event_uuid"],
                    x["source_player_provider_uuid"],x["fixed_asof_horizon"])
        existing={unique(x):x for x in before}
        if len(existing)!=len(before):raise ValueError("DUPLICATE_FROZEN_MLB_PRICE_MOVEMENT")
        additions=[]
        for line in proposed:
            k=unique(line)
            if k in existing:continue
            if k in {unique(x) for x in additions}:raise ValueError("DUPLICATE_NEW_SOURCE_PRICE_MOVEMENT")
            additions.append(line)
        if additions:
            with path.open("a",encoding="utf8") as f:
                for x in additions:
                    f.write(json.dumps(x,sort_keys=True,separators=(",",":"))+"\n")
                f.flush();os.fsync(f.fileno())
        return len(additions)


def verify_frozen_archive_lineage(saved:list[dict], *,root=ROOT, spec:dict|None=None):
    """Read back frozen original source hashes; if any changed, stop ALL new writes."""
    checked={}
    market_base=(Path(root)/"mlb_live/markets/history").resolve()
    validated=0
    for r in saved:
        if (r.get("schema")!=SCHEMA or r.get("research_only") is not True
            or r.get("production_bet_or_model_promotion") is not False
            or r.get("source_original_books_observed_not_executable") is not True
            or r.get("original_game_over_or_under_hits_unknown") is not True):
            raise ValueError("FROZEN_RESEARCH_ROW_HAS_INVALID_CONTRACT")
        if spec is not None and r.get("study_id")!=spec["study_id"]:
            raise ValueError("FROZEN_MOVEMENT_BELONGS_TO_DIFFERENT_STUDY")
        for name,hashname in (
            ("original_current_raw_archive","original_current_raw_sha256"),
            ("original_prior_raw_archive","original_prior_raw_sha256"),
        ):
            relative=Path(str(r.get(name) or ""))
            file=(Path(root)/relative).resolve()
            if not file.is_relative_to(market_base) or file.suffix!=".csv":
                raise ValueError("FROZEN_SOURCE_ARCHIVE_OUTSIDE_ORIGINAL_BOOK_HISTORY")
            if not file.is_file():
                raise ValueError("FROZEN_ORIGINAL_SOURCE_ARCHIVE_MISSING")
            if file not in checked:
                checked[file]=sha(file.read_bytes())
            if checked[file]!=r.get(hashname):
                raise ValueError("FROZEN_ORIGINAL_PRICE_SNAPSHOT_SHA256_CHANGED")
        at=moment(r.get("original_current_quote_utc"))
        prior=moment(r.get("original_prior_quote_utc"))
        start=moment(r.get("source_start_utc"))
        if (not at or not prior or not start or
            not prior<at<start or
            not r.get("source_sportsbook") or not r.get("source_player_provider_uuid")):
            raise ValueError("FROZEN_SOURCE_TIMESTAMPS_OR_IDENTITY_CHANGED")
        validated+=1
    return {"frozen_rows_hash_verified":validated,
            "distinct_original_market_snapshots_sha256_readback":len(checked)}


def run(*,clock=None,out=OUT,snapshots=None,specfile=SPEC):
    now=clock or datetime.now(timezone.utc)
    if not now.tzinfo:raise ValueError("NAIVE_CYCLE_CLOCK")
    spec=json.loads(specfile.read_text())
    reg=moment(spec["registered_at_utc"])
    if not reg or now<reg or spec["production_model_promotion_allowed"] is not False:
        raise ValueError("RESEARCH_PREREGISTRATION_NOT_VALID")
    frozen=FROZEN.read_bytes().splitlines(keepends=True)[:18]
    if sha(b"".join(frozen))!=spec["original_full16_existing_18_game_forecasts_sha256"]:
        raise ValueError("ORIGINAL_FULL16_MODEL_DATA_WAS_REWRITTEN")
    schedule=json.loads(CACHE.read_text())
    readiness=json.loads(READINESS.read_text())
    master=pd.read_csv(MASTER,low_memory=False)
    fixtures=source_proof(readiness,schedule,master,now)
    existing=records(out)
    verify_frozen_archive_lineage(existing,spec=spec)
    proposed,reasons,files=movement_candidates(
        HISTORY,spec,fixtures,now,reg,scan_files=snapshots,
    )
    verify_frozen_archive_lineage(proposed,spec=spec)
    accepted=append_rows(out,proposed)
    saved=records(out)
    lineage_proof=verify_frozen_archive_lineage(saved,spec=spec)
    if any(x["production_bet_or_model_promotion"] for x in saved):
        raise ValueError("UNAUTHORIZED_NON_RESEARCH_SOURCE")
    return {
      "schema":SCHEMA,
      "source_captured_at_utc":now.isoformat(),
      "preregistration_sha256":sha(specfile.read_bytes()),
      "existing_first_18_full16_sha256_preserved":sha(b"".join(frozen)),
      "original_official_future_fixture_count":len(fixtures),
      "market_source_snapshots_scanned":files,
      "new_frozen_forward_movement_records":accepted,
      "all_future_horizon_frozen_movement_records":len(saved),
      "distinct_future_official_games":len({x["official_game_pk"] for x in saved}),
      "by_predeclared_horizon":dict(sorted(Counter(x["fixed_asof_horizon"] for x in saved).items())),
      "fixed_gt_3pp_movement_source_records":sum(x["fixed_movement_exceeds_3pp"] for x in saved),
      "source_rejection_reasons":reasons,
      "independent_official_player_outcomes":0,
      "real_money_bets_executed":0,
      "new_model_retraining_or_promotion":False,
      "original_book_market_prices_verified_executable":False,
      "original_frozen_raw_history_lineage_sha256_readback":lineage_proof,
    }


def main():
    report=run()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temporary=SUMMARY.with_suffix(".tmp")
    with temporary.open("w",encoding="utf8") as f:
        json.dump(report,f,sort_keys=True,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
    os.replace(temporary,SUMMARY)
    print("ZENITH_MLB_FIXED_ASOF_SOURCE_MOVEMENT_FROZEN",json.dumps(report,sort_keys=True))


if __name__=="__main__":main()
