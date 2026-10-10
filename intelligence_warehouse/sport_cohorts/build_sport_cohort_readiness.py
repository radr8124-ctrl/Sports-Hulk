"""Read-only sport-aware official-result and competition-phase learning cohorts.

Uses original frozen ENTRY+SETTLED ledger (never edits it), full league
source-history files, and an immutable captured MLB StatsAPI schedule. A
qualified official final is useful for postgame *error review*; it does NOT
prove odds executable, independent model skill, or that the final was known
at the original prediction's freeze. Keeps NHL/CFB/NBA/MLB separate.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from intelligence_warehouse.outcome_learning.learning_core import (
    canonical, diagnosis, scored_grade, when,
)

ROOT=Path(__file__).resolve().parents[2]
LEDGER=Path("intelligence_warehouse/betting_v2/BETTING_V2_ALL_MARKETS_FORWARD_LEDGER.jsonl")
SOURCES={
    "NBA":Path("nba_live/history/NBA_GAME_HISTORY.csv"),
    "NHL":Path("nhl_live/history/NHL_GAME_HISTORY.csv"),
    "CFB":Path("cfb_live/history/CFB_GAME_HISTORY.csv"),
    "MLB":Path("intelligence_warehouse/sport_cohorts/sources/MLB_STATSAPI_POSTSEASON_SCHEDULE_20261010.raw.json"),
}
OUTPUT=Path("intelligence_warehouse/sport_cohorts/SPORT_COHORT_OFFICIAL_REPLAY.json")
PUBLIC=Path("commercial_web/public/zenith_sport_cohorts.json")
DIST=Path("commercial_web/dist/zenith_sport_cohorts.json")
RECOVERY=Path("intelligence_warehouse/sport_cohorts/SPORT_COHORT_OFFICIAL_FINAL_SHADOW_GRADES.json")
NBA_QUALIFIED_GRADE_SOURCE=Path("nba_live/decision/history/NBA_GRADED_RECOMMENDATIONS.csv")
SPORTS=("NHL","CFB","NBA","MLB")
NBA_TYPES={"1":("PRESEASON","PRESEASON"),"2":("REGULAR","REGULAR"),"3":("POSTSEASON","POSTSEASON")}
NHL_TYPES={"1":("PRESEASON","PRESEASON"),"2":("REGULAR","REGULAR"),"3":("POSTSEASON","PLAYOFFS")}
CFB_TYPES={"2":("REGULAR","REGULAR"),"3":("POSTSEASON","BOWL_OR_PLAYOFF")}
MLB_TYPES={"F":("POSTSEASON","WORLD_SERIES"),"L":("POSTSEASON","LEAGUE_CHAMPIONSHIP"),
           "D":("POSTSEASON","DIVISION_SERIES"),"W":("POSTSEASON","WILD_CARD")}
# Same actual NBA franchises use different abbreviations in original ESPN
# historical source and bookmaker market keys. Explicit one-to-one IDs only.
NBA_ESPN_TO_MARKET={"NY":"NYK","NO":"NOP","GS":"GSW","UTAH":"UTA","SA":"SAS","WSH":"WAS"}


def official_team_code(sport,value):
    return norm(NBA_ESPN_TO_MARKET.get(str(value),str(value)) if sport=="NBA" else value)



def read_exact(path:Path):
    raw=path.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
        raise RuntimeError("Source changed during official cohort snapshot: "+str(path))
    return raw,sha


def norm(value):
    return "".join(c for c in str(value or "").lower() if c.isalnum())


def as_number(x):
    try:
        if x in ("",None):return None
        v=float(x)
        return v if -1e6<v<1e6 else None
    except (TypeError,ValueError):return None


def is_true(x):
    return x is True or str(x).lower() in ("true","1")


def source_path_for_sport(root:Path,sport:str)->Path:
    """Latest immutable date-stamped MLB snapshot; older evidence retained."""
    if sport!="MLB":return root/SOURCES[sport]
    default=root/SOURCES["MLB"]
    matches=sorted(default.parent.glob("MLB_STATSAPI_POSTSEASON_SCHEDULE_????????.raw.json"))
    return matches[-1] if matches else default


def official_sources(root=ROOT):
    available={}
    hashes={}
    for sport in SOURCES:
        selected=source_path_for_sport(root,sport)
        try:
            raw,sha=read_exact(selected)
        except FileNotFoundError:
            available[sport]=[]
            hashes[sport]=None
            continue
        hashes[sport]=sha
        official=[]
        if sport!="MLB":
            rows=csv.DictReader(io.StringIO(raw.decode("utf-8")))
            for row in rows:
                source_type=row.get("game_type") if sport=="NHL" else row.get("season_type")
                lookup={"NBA":NBA_TYPES,"NHL":NHL_TYPES,"CFB":CFB_TYPES}[sport]
                classification=lookup.get(str(source_type))
                if not classification:continue
                original_start=when(row.get("start"))
                if original_start is None:continue
                away=row.get("away_team_id") if sport=="CFB" else row.get("away_team")
                home=row.get("home_team_id") if sport=="CFB" else row.get("home_team")
                if not away or not home:continue
                final=is_true(row.get("completed"))
                a,b=as_number(row.get("away_score")),as_number(row.get("home_score"))
                official.append({
                    "official_game_id":str(row.get("event_id") or ""),
                    "away_code":official_team_code(sport,away),
                    "home_code":official_team_code(sport,home),
                    "start":original_start,"phase":classification[0],
                    "stage":classification[1],"source_type":str(source_type),
                    "final":final,"away_score":a,"home_score":b,
                })
        else:
            payload=json.loads(raw)
            for entry in payload.get("dates",[]):
                for game in entry.get("games",[]):
                    classification=MLB_TYPES.get(game.get("gameType"))
                    if not classification:continue
                    original_start=when(game.get("gameDate"))
                    if original_start is None:continue
                    teams=game.get("teams") or {}
                    away=teams.get("away") or {}
                    home=teams.get("home") or {}
                    status=game.get("status") or {}
                    a,b=as_number(away.get("score")),as_number(home.get("score"))
                    official.append({
                        "official_game_id":str(game.get("gamePk") or ""),
                        "away_code":norm((away.get("team") or {}).get("name")),
                        "home_code":norm((home.get("team") or {}).get("name")),
                        "start":original_start,"phase":classification[0],
                        "stage":classification[1],"source_type":game.get("gameType"),
                        "final":status.get("abstractGameState")=="Final",
                        "away_score":a,"home_score":b,
                    })
        original_by_id={}
        for item in official:
            key=item["official_game_id"]
            prior=original_by_id.get(key)
            if prior is not None and prior!=item:
                # A changing final/status may be an ordinary source refresh,
                # but mixing inconsistent variants would contaminate grades.
                raise ValueError("Conflicting original official "+sport+" rows for event "+key)
            original_by_id[key]=item
        # NBA original history currently repeats seven byte-equivalent scheduled
        # events; one event must count once, not inflate a training cohort.
        available[sport]=list(original_by_id.values())
    return available,hashes


def match_official(row,official):
    """Require exact two teams + scheduled kickoff, never match by score alone."""
    parts=str(row.get("game_key") or "").split("|")
    if len(parts)!=3:
        return [],"INVALID_ORIGINAL_GAME_KEY"
    away,home=norm(parts[1]),norm(parts[2])
    start=when(row.get("original_start_utc"))
    if not away or not home or start is None:
        return [],"INVALID_ORIGINAL_SCHEDULE"
    options=[g for g in official if g["away_code"]==away and
             g["home_code"]==home and abs((g["start"]-start).total_seconds())<=30*60]
    if len(options)!=1:
        return options,"NO_UNIQUE_OFFICIAL_FIXTURE_MATCH"
    return options,None


def phase_claim(row,official):
    """An UNKNOWN original regime may be classified after results, never backfilled."""
    original=str(row.get("competition_regime") or "").strip().upper()
    if original not in {"","UNKNOWN"} and original!=official["phase"]:
        return "ORIGINAL_COMPETITION_PHASE_CONFLICT"
    return None


def nba_original_exact_grade_keys(raw:bytes)->set:
    """Only GAME recommendations already qualified with actual final grades."""
    keys=set()
    for line in csv.DictReader(io.StringIO(raw.decode("utf-8"))):
        if (str(line.get("lane") or "").upper()!="GAME"
            or str(line.get("grade") or "").upper() not in {"WIN","LOSS","PUSH"}):continue
        market=str(line.get("market") or "").upper()
        price_line=as_number(line.get("line"))
        if market!="MONEYLINE" and price_line is None:continue
        key=(str(line.get("game_key") or ""),market,norm(line.get("selection")),
             "" if market=="MONEYLINE" else format(price_line,".4f"))
        keys.add(key)
    return keys


def exact_grade_key(row):
    market=str(row.get("market") or "").upper()
    line=as_number(row.get("line"))
    return (str(row.get("game_key") or ""),market,norm(row.get("selection")),
           "" if market=="MONEYLINE" else format(line,".4f") if line is not None else "MISSING")


def derive_pending_official_final(row,official):
    """Pure final-score math only; never append a historic SETTLED event."""
    if row.get("grade")!="PENDING" or not official.get("final"):
        return None
    if official.get("away_score") is None or official.get("home_score") is None:
        return None
    payload={**row,"away_score":official["away_score"],
             "home_score":official["home_score"]}
    grade=scored_grade(payload)
    if grade not in ("WIN","LOSS","PUSH"):
        return None
    return {
        "original_forward_key":row["forward_key"],
        "original_game_key":row["game_key"],
        "original_capture_at":row["original_capture_utc"],
        "original_game_start":row["original_start_utc"],
        "original_selection_key":row.get("selection_key"),
        "original_line":row.get("line"),
        "market":row.get("market"),
        "sport":row.get("sport"),
        "official_game_id":official["official_game_id"],
        "official_phase":official["phase"],
        "official_stage":official["stage"],
        "official_away_score":official["away_score"],
        "official_home_score":official["home_score"],
        "calculated_result":grade,
        "market_probability_pct_at_original_freeze":row["market_probability_pct"],
        "original_experimental_model_probability_pct":row["model_probability_pct"],
        "original_probability_copied_market":abs(row["market_probability_pct"]-row["model_probability_pct"])<1e-8,
        "original_opposite_side_conflict":row.get("opposite_side_conflict") is True,
        "original_duplicate_line_variant":row.get("duplicate_line_variant") is True,
        "original_same_game_exposure_block":row.get("same_game_exposure_block") is True,
        "original_entry_betting_status":row.get("entry_shadow_decision"),
        "original_selection":row.get("selection"),
        "training_eligibility":"DENIED_NOT_AN_INDEPENDENT_PROVEN_FORECAST",
        "original_entry_remains_PENDING":True,
        "derived_postgame_from_official_result_only":True,
        "original_bookmaker_price_executable_verified":False,
        "independent_model_edge_proven":False,
        "official_result_may_have_arrived_after_model_freeze":True,
        "research_only_not_real_wager":True,
    }


def replay(root=ROOT,at=None):
    at=at or datetime.now(timezone.utc)
    if not at.tzinfo:raise ValueError("Evaluation clock requires UTC offset")
    blob,ledger_sha=read_exact(root/LEDGER)
    events=[json.loads(s) for s in blob.decode().splitlines() if s.strip()]
    frozen,invalid=canonical(events)
    official,source_hashes=official_sources(root)
    nba_grade_bytes,nba_grade_sha=read_exact(root/NBA_QUALIFIED_GRADE_SOURCE)
    nba_qualified_keys=nba_original_exact_grade_keys(nba_grade_bytes)
    bins=defaultdict(list)
    blocked=defaultdict(Counter)
    rows_by_sport=defaultdict(list)
    recovered=[]
    for row in frozen:
        sport=row.get("sport")
        if sport not in SPORTS:continue
        matched,fail=match_official(row,official[sport])
        if fail:
            kind="UNMATCHED_FROZEN_PENDING" if row.get("grade")=="PENDING" else "OFFICIAL_FINAL_IDENTITY_NOT_VERIFIED"
            blocked[sport][kind+":"+fail]+=1
            continue
        game=matched[0]
        if not game["official_game_id"]:
            blocked[sport]["MISSING_OFFICIAL_GAME_ID"]+=1
            continue
        failed=phase_claim(row,game)
        if failed:
            blocked[sport][failed]+=1
            continue
        grade=row.get("grade")
        captured=when(row.get("original_capture_utc"))
        if captured is None or captured>=game["start"]:
            blocked[sport]["PREDICTION_NOT_FROZEN_BEFORE_OFFICIAL_START"]+=1
            continue
        if grade in ("WIN","LOSS","PUSH"):
            if not game["final"] or game["away_score"] is None or game["home_score"] is None:
                blocked[sport]["ORIGINAL_SETTLEMENT_HAS_NO_OFFICIAL_FINAL"]+=1
                continue
            if row.get("away_score")!=game["away_score"] or row.get("home_score")!=game["home_score"]:
                blocked[sport]["RECORDED_FINAL_SCORE_CONFLICTS_OFFICIAL"]+=1
                continue
        elif game["final"]:
            shadow=derive_pending_official_final(row,game)
            if shadow is not None:
                if sport=="NBA":
                    present=exact_grade_key(row) in nba_qualified_keys
                    shadow["qualified_exact_original_game_grade_line_exists"]=present
                    shadow["original_unsettled_exact_line_missing_from_grade_source"]=not present
                recovered.append(shadow)
            else:
                blocked[sport]["OFFICIAL_FINAL_UNGRADABLE_ORIGINAL_RESEARCH_LINE"]+=1
            continue
        context={
            "game_key":row.get("game_key"),
            "official_event_id":game["official_game_id"],
            "sport":sport,
            "phase":game["phase"],"stage":game["stage"],
            "original_entry_phase":str(row.get("competition_regime") or "UNKNOWN"),
            "original_phase_explicitly_proven_at_freeze":False,
            "league_official_phase_verified_now":True,
            "source_league_type_code":game["source_type"],
            "original_capture_utc":row["original_capture_utc"],
            "scheduled_start_utc":row["original_start_utc"],
            "settled_at":row.get("settled_at_utc"),
            "grade":grade,
            "market":row.get("market"),
            "selected_side":row.get("selection_key"),
            "line":row.get("line"),
            "original_model_probability_pct":row["model_probability_pct"],
            "market_probability_pct":row["market_probability_pct"],
            "away_score":game["away_score"] if game["final"] else None,
            "home_score":game["home_score"] if game["final"] else None,
            "result_official_final_crosschecked":grade in ("WIN","LOSS","PUSH"),
            "model_has_independent_market_edge":False,
            "actual_wager_executed_or_price_verified":False,
        }
        rows_by_sport[sport].append(context)
        bins[(sport,game["phase"],game["stage"])].append(context)
    cohorts=[]
    for (sport,phase,stage),records in sorted(bins.items()):
        settled=[r for r in records if r["result_official_final_crosschecked"]]
        by_game=defaultdict(list)
        for r in settled:
            if r["grade"]=="PUSH":continue
            y=1 if r["grade"]=="WIN" else 0
            p=r["market_probability_pct"]/100
            q=r["original_model_probability_pct"]/100
            by_game[r["official_event_id"]].append(((p-y)**2,(q-y)**2))
        book_errors=[sum(x[0] for x in grp)/len(grp) for grp in by_game.values()]
        model_errors=[sum(x[1] for x in grp)/len(grp) for grp in by_game.values()]
        cohorts.append({
            "sport":sport,"competition":phase,"phase_stage":stage,
            "qualified_frozen_entries":len(records),
            "independently_verified_official_final_selections":len(settled),
            "unique_official_final_games":len({r["official_event_id"] for r in settled}),
            "pending_upcoming_predictions":sum(r["grade"]=="PENDING" for r in records),
            "market_probability_equals_model_count":sum(abs(r["market_probability_pct"]-
                r["original_model_probability_pct"])<1e-8 for r in settled),
            "game_weighted_book_brier":round(sum(book_errors)/len(book_errors),6) if book_errors else None,
            "game_weighted_model_brier":round(sum(model_errors)/len(model_errors),6) if model_errors else None,
            "status":"SOURCE_VERIFIED_RESEARCH_ONLY",
            "source_fixture_phase_verified_after_original_forecast":True,
            "independent_model_advantage_established":False,
            "same_game_multi_line_counts_once":True,
        })
    examples=[]
    for sport in SPORTS:
        errors=[r for r in rows_by_sport[sport] if r["grade"]=="LOSS"]
        errors.sort(key=lambda r:(r["scheduled_start_utc"],r["game_key"]),reverse=True)
        used=set()
        for r in errors:
            if r["official_event_id"] in used:continue
            used.add(r["official_event_id"])
            code,text=diagnosis({
                "grade":"LOSS","market":r["market"],
                "home_score":r["home_score"],"away_score":r["away_score"],
                "selection_key":r["selected_side"],"line":r["line"],
            })
            examples.append({
                "sport":sport,"competition":r["phase"],"game":r["game_key"],
                "official_event_id":r["official_event_id"],
                "market":r["market"],"observed_error_type":code,
                "observed_miss":text,
                "final_score_away_home":[r["away_score"],r["home_score"]],
                "independent_causal_feature_identified":False,
            })
            if len(used)>=2:break
    total_verified=sum(x["independently_verified_official_final_selections"] for x in cohorts)
    recovered.sort(key=lambda r:(r["sport"],r["official_game_id"],r["original_forward_key"]))
    recovered_summary=[]
    for sport in SPORTS:
        group=[r for r in recovered if r["sport"]==sport]
        if group:
            recovered_summary.append({
                "sport":sport,
                "derived_postgame_research_rows":len(group),
                "unique_official_games":len({r["official_game_id"] for r in group}),
                "grade_counts":dict(Counter(r["calculated_result"] for r in group)),
                "market_counts":dict(Counter(r["market"] for r in group)),
                "market_grade_counts":{m:dict(Counter(x["calculated_result"] for x in group if x["market"]==m))
                    for m in sorted({x["market"] for x in group})},
                "original_duplicate_line_variant_count":sum(r["original_duplicate_line_variant"] for r in group),
                "original_opposite_side_conflict_count":sum(r["original_opposite_side_conflict"] for r in group),
                "market_probability_copied_count":sum(r["original_probability_copied_market"] for r in group),
                "original_qualified_game_grade_line_missing_count":sum(
                    r.get("original_unsettled_exact_line_missing_from_grade_source") is True for r in group),
                "cannot_count_multiple_lines_as_independent_games":True,
                "original_forward_grade_was_not_rewritten":True,
            })
    return {
        "schema":"ZENITH_SPORT_PHASE_LEARNING_COHORTS_V1",
        "generated_at_utc":at.astimezone(timezone.utc).isoformat(),
        "status":"REVIEW_ONLY_NO_AUTOMATIC_MODEL_CHANGE",
        "source_hashes":{"frozen_betting_market_ledger_sha256":ledger_sha,
                         "original_nba_exact_game_grade_source_sha256":nba_grade_sha,
                         **{s+"_original_league_source_sha256":source_hashes[s] for s in SPORTS}},
        "official_source_files":{"frozen_ledger":str(LEDGER),
            "original_nba_exact_grade_history":str(NBA_QUALIFIED_GRADE_SOURCE),
            **{s:str(source_path_for_sport(root,s).relative_to(root)) for s in SPORTS}},
        "qualifying_sports":list(SPORTS),
        "source_verified_final_research_selections":total_verified,
        "source_verified_distinct_final_games":len({(x["sport"],x["official_event_id"])
                       for data in rows_by_sport.values() for x in data
                       if x["result_official_final_crosschecked"]}),
        "derived_pending_from_official_final_research_rows":len(recovered),
        "derived_pending_distinct_official_games":len({(r["sport"],r["official_game_id"]) for r in recovered}),
        "pending_official_final_recovery_by_sport":recovered_summary,
        "pending_shadow_results_added_to_original_ledger":0,
        "derived_only_from_prior_frozen_line_plus_official_final":True,
        "unverified_or_unmatched_entries_by_sport":{s:dict(blocked[s]) for s in SPORTS},
        "cross_sport_competition_leakage_blocked":True,
        "original_phase_fields_unchanged":True,
        "official_sources_fetched_after_original_frozen_prediction":True,
        "model_is_sportsbook_market_copy_for_current_game_betting":True,
        "independent_model_advantage_proven":False,
        "production_model_weights_changed":False,
        "model_bets_approved":0,
        "actual_sportsbook_wagers_placed":0,
        "cohorts":cohorts,"recent_observable_errors":examples,
        "_full_recovery_receipt_rows":recovered,
        "learning_note":"Sport-specific matches are validated against league official game type, teams, start and final score. Only future pre-frozen predictions with a separately validated model can demonstrate a prospective edge. Official final-source classification was not proven captured before original freeze.",
        "original_invalid_ledger_reasons":dict(invalid),
    }


def atomic_write(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    with NamedTemporaryFile("w",dir=path.parent,delete=False,suffix=".tmp") as f:
        temp=Path(f.name)
        json.dump(payload,f,sort_keys=True,indent=2)
        f.write("\n");f.flush();os.fsync(f.fileno())
    os.replace(temp,path)


def publish(root=ROOT):
    j=replay(root=root)
    recovered=j.pop("_full_recovery_receipt_rows")
    receipt={
        "schema":"ZENITH_ORIGINAL_FROZEN_FINAL_SHADOW_RECOVERY_V1",
        "generated_at_utc":j["generated_at_utc"],
        "original_source_hashes":j["source_hashes"],
        "status":"RESEARCH_ONLY_ORIGINAL_FORWARD_REMAINS_PENDING",
        "derived_rows_count":len(recovered),
        "recorded_original_betting_ledger_updates":0,
        "independent_profit_or_model_edge_proven":False,
        "rows":recovered,
    }
    atomic_write(root/RECOVERY,receipt)
    recover_sha=hashlib.sha256((root/RECOVERY).read_bytes()).hexdigest()
    j["full_official_shadow_receipt_sha256"]=recover_sha
    for p in (OUTPUT,PUBLIC,DIST):
        if p==DIST and not (root/p).parent.exists():continue
        atomic_write(root/p,j)
    return j


if __name__=="__main__":
    j=publish()
    print(json.dumps({
        "status":j["status"],
        "source_verified_final_selections":j["source_verified_final_research_selections"],
        "unique_final_games":j["source_verified_distinct_final_games"],
        "cohorts":[{key:c[key] for key in ("sport","competition","phase_stage",
            "independently_verified_official_final_selections","unique_official_final_games")}
           for c in j["cohorts"]],
        "blocked":j["unverified_or_unmatched_entries_by_sport"],
    },indent=2))
