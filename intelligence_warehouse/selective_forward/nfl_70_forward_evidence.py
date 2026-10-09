"""Frozen NFL 70%-probability plus priced-value research, never live bets."""
from __future__ import annotations
import argparse,fcntl,hashlib,json,math,os
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SPEC=ROOT/"reports/ZENITH_NFL_70_TRUE_FORWARD_PRICE_EXPERIMENT_PREREG_2026-10-09.json"
SOURCE=ROOT/"intelligence_warehouse/nfl_advanced_pregame/NFL_FIRST_PREKICKOFF_NINE_FEATURE_SCORE_FORM_SHADOW.jsonl"
OFFICIAL=ROOT/"intelligence_warehouse/nfl_advanced_pregame/NFL_NINE_FEATURE_SAME_BOOK_OFFICIAL_FINAL_SCORES.jsonl"
OUT=ROOT/"intelligence_warehouse/selective_forward/NFL_70_FIXED_VALUE_SHADOW.jsonl"
GRADES=ROOT/"intelligence_warehouse/selective_forward/NFL_70_FIXED_VALUE_OFFICIAL_GRADES.jsonl"
SUMMARY=ROOT/"intelligence_warehouse/selective_forward/NFL_70_FIXED_VALUE_RESEARCH_SUMMARY.json"
SCHEMA="ZENITH_NFL_ORIGINAL_FROZEN_70_PRICE_VALUE_RESEARCH_V1"

def stamp(v):
    if not isinstance(v,str):raise ValueError("MISSING_SOURCE_TIME")
    d=datetime.fromisoformat(v.replace("Z","+00:00"))
    if not d.tzinfo:raise ValueError("NAIVE_SOURCE_TIME")
    return d.astimezone(timezone.utc)

def rows(p):
    return [json.loads(s) for s in p.read_text().splitlines() if s.strip()] if p.is_file() else []

def sha(b):return hashlib.sha256(b).hexdigest()

def implied(odds):
    x=float(odds)
    if not math.isfinite(x) or abs(x)<100 or abs(x)>10000:raise ValueError("INVALID_PRICE")
    return -x/(100-x) if x<0 else 100/(100+x)

def profit(odds):
    x=float(odds)
    return 100/abs(x) if x<0 else x/100

def make_selection(original,spec,now):
    eid=str(original['official_espn_event_id'])
    if not eid.isdigit() or original.get('research_only') is not True or original.get('betting_play_approved') is not False:
        raise ValueError("ORIGINAL_SOURCE_NOT_PROSPECTIVE_RESEARCH")
    if original.get('source_is_game_moneyline_not_player_proposition') is not True:
        raise ValueError("NOT_PROVEN_GAME_MONEYLINE_IDENTITY")
    start=stamp(original['official_first_pitch_utc'])
    context=stamp(original['source_context_features_frozen_at_utc'])
    quote=stamp(original['source_qualified_book_quote_updated_at_utc'])
    frozen=stamp(original['source_first_real_future_prediction_frozen_at_utc'])
    if not(context<quote<=frozen<start and stamp(spec['registered_at_utc'])<start and now<start):
        raise ValueError("PREGAME_SOURCE_CLOCK_OR_REGISTRATION_MISMATCH")
    modelhome=float(original['nine_feature_score_form_home_win_prob'])
    homeodd=float(original['original_same_book_american_home_moneyline'])
    awayodd=float(original['original_same_book_american_away_moneyline'])
    fair=implied(homeodd)/(implied(homeodd)+implied(awayodd))
    if not(.001<modelhome<.999) or not 1<implied(homeodd)+implied(awayodd)<=1.25:
        raise ValueError("INVALID_MODEL_OR_BOOK_MONEYLINE")
    if abs(fair-float(original['original_raw_book_home_fair']))>2e-6:
        raise ValueError("ORIGINAL_PRICE_AND_NO_VIG_DISAGREE")
    side="HOME" if modelhome>=.5 else "AWAY"
    model=modelhome if side=="HOME" else 1-modelhome
    market=fair if side=="HOME" else 1-fair
    price=homeodd if side=="HOME" else awayodd
    edgepp=(model-market)*100
    evpct=(model*(1+profit(price))-1)*100
    age=(frozen-quote).total_seconds()
    t=spec['thresholds_fixed_before_game_outcomes']
    blockers=[]
    if model<t['minimum_model_win_probability']:blockers.append("MODEL_PROBABILITY_BELOW_70")
    if edgepp<t['minimum_advantage_over_no_vig_book_probability_pp']:blockers.append("BOOK_EDGE_BELOW_3PP")
    if evpct<t['minimum_paper_expected_roi_at_original_book_price_pct']:blockers.append("PRICE_EV_BELOW_3PCT")
    if age<0 or age>t['max_age_of_quote_at_original_model_freeze_seconds']:
        blockers.append("ORIGINAL_QUOTE_NOT_FRESH_AT_MODEL_FREEZE")
    if any(not str(original.get(k) or '').strip() for k in
           ('home_team','away_team','source_book_name','source_provider','original_source_provider_event_uuid')):
        raise ValueError("UNVERIFIED_PROVIDER_OR_TEAM_IDENTITY")
    return {
      'schema':SCHEMA,'experiment_id':spec['experiment_id'],'official_espn_event_id':eid,
      'home_team':original['home_team'],'away_team':original['away_team'],
      'official_first_pitch_utc':start.isoformat(),'original_frozen_at_utc':frozen.isoformat(),
      'original_book_quote_at_utc':quote.isoformat(),
      'provider':original['source_provider'],'book':original['source_book_name'],
      'provider_event_uuid':original['original_source_provider_event_uuid'],
      'original_model_sha256':original['source_frozen_model_sha256'],
      'selected_side':side,'original_american_price':price,
      'original_model_probability':round(model,9),
      'original_book_no_vig_probability':round(market,9),
      'model_minus_book_pp':round(edgepp,6),'priced_research_expected_roi_pct':round(evpct,6),
      'original_quote_age_seconds':round(age,1),
      'fixed_research_screen_pass':not blockers,'fixed_screen_blockers':blockers,
      'named_book_original_price_independently_executable':False,
      'production_bet_allowed':False,'source_model_or_picks_changed':False,
      'research_only':True
    }

def append(path,items):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+".lock").open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        old=rows(path)
        keys={x['official_espn_event_id']:x for x in old}
        if len(keys)!=len(old):raise ValueError("DUPLICATED_IMMUTABLE_SELECTION_LEDGER")
        new=[]
        for r in items:
            eid=r['official_espn_event_id']
            if eid in keys:
                if keys[eid]!=r:raise ValueError("ORIGINAL_SELECTION_LEDGER_WOULD_BE_REWRITTEN")
                continue
            if eid in {x['official_espn_event_id'] for x in new}:
                raise ValueError("DUPLICATE_CAPTURE_BATCH")
            new.append(r)
        if new:
            with path.open('a',encoding='utf8') as f:
                for r in new:f.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
                f.flush();os.fsync(f.fileno())
        return len(new)

def capture(clock=None):
    now=clock or datetime.now(timezone.utc)
    if not now.tzinfo:raise ValueError("OBSERVATION_CLOCK_NAIVE")
    spec=json.loads(SPEC.read_text())
    if spec.get('live_play_approved') is not False or spec.get('automatic_wager') is not False:
        raise ValueError("NO_LIVE_BETTING_PERMITTED")
    predictions=rows(SOURCE)
    first=int(spec['frozen_original_13_game_count'])
    source_lines=SOURCE.read_bytes().splitlines(keepends=True)
    if len(predictions)<first or sha(b''.join(source_lines[:first]))!=spec['original_pre_registration_nfl_predictions_sha256']:
        raise ValueError("ORIGINAL_13_NFL_PREDICTIONS_CHANGED")
    if len({r['official_espn_event_id'] for r in predictions})!=len(predictions):
        raise ValueError("DUPLICATE_ORIGINAL_NFL_PREDICTION")
    if any(r['model_version']!=spec['model_version'] or r['source_frozen_model_sha256']!=spec['model_coef_sha256'] for r in predictions):
        raise ValueError("ORIGINAL_FROZEN_NFL_MODEL_COHORT_CHANGED")
    prior={r['official_espn_event_id'] for r in rows(OUT)}
    new=[]; late=[]
    for r in predictions:
        if r['official_espn_event_id'] in prior:continue
        if stamp(r['official_first_pitch_utc'])<=now:
            late.append(r['official_espn_event_id']);continue
        new.append(make_selection(r,spec,now))
    added=append(OUT,new)
    all_rows=rows(OUT)
    return {
     'original_frozen_nfl_models':len(predictions),'new_game_abstention_or_screen_records':added,
     'total_original_game_selections_saved':len(all_rows),
     'provisional_paper_screen_pass_count':sum(r['fixed_research_screen_pass'] for r in all_rows),
     'original_game_abstentions_saved':sum(not r['fixed_research_screen_pass'] for r in all_rows),
     'new_forward_eligible_games_that_missed_capture':len(late),
     'source_prediction_sha256_latest':sha(SOURCE.read_bytes()),
     'no_proven_executable_book_prices_or_live_bets':True,
     'new_frozen_predictions_retrained':False
    }

def grade():
    selections={r['official_espn_event_id']:r for r in rows(OUT)}
    previous={r['official_espn_event_id'] for r in rows(GRADES)}
    official=rows(OFFICIAL)
    if len({str(r['official_espn_event_id']) for r in official})!=len(official):
        raise ValueError("DUPLICATE_ESPN_FINAL_GRADE")
    incoming=[]
    for r in official:
        eid=str(r['official_espn_event_id'])
        if eid not in selections or eid in previous:continue
        x=selections[eid]
        if r.get('research_only') is not True or r.get('not_sportsbook_settlement_or_wager_win') is not True:
            raise ValueError("NO_VERIFIED_OFFICIAL_RESEARCH_FINAL")
        if r['original_model_sha256']!=x['original_model_sha256'] or stamp(r['source_first_original_model_frozen_at_utc'])!=stamp(x['original_frozen_at_utc']):
            raise ValueError("OFFICIAL_GRADE_PRE_FREEZE_PROVENANCE_MISMATCH")
        if r['home_team']!=x['home_team'] or r['away_team']!=x['away_team']:
            raise ValueError("OFFICIAL_GRADE_OPPONENT_IDENTITY_MISMATCH")
        result=r['original_home_moneyline_win_binary_outcome']
        if type(result)!=int or result not in (0,1):
            raise ValueError("OFFICIAL_FINAL_UNRESOLVED")
        home,away=int(r['official_home_points']),int(r['official_away_points'])
        if not(0<=home<=150 and 0<=away<=150 and home!=away and int(home>away)==result):
            raise ValueError("OFFICIAL_ESPN_FINAL_POINTS_DO_NOT_SUPPORT_WINNER")
        final_at=stamp(r['source_real_original_final_observed_at_utc'])
        if not(stamp(x['official_first_pitch_utc'])<final_at<=datetime.now(timezone.utc)):
            raise ValueError("OFFICIAL_FINAL_NOT_IN_PAST_OR_SOURCE_TIME_MISMATCH")
        source_hash=r.get('source_original_espn_final_scoreboard_sha256')
        if not isinstance(source_hash,str) or len(source_hash)!=64:
            raise ValueError("MISSING_INDEPENDENT_OFFICIAL_FINAL_HASH")
        win=(result==1) if x['selected_side']=="HOME" else (result==0)
        incoming.append({
           'schema':SCHEMA,'experiment_id':x['experiment_id'],
           'official_espn_event_id':eid,'original_research_screen_pass':x['fixed_research_screen_pass'],
           'source_verified_final_scoreboard_sha256':r['source_original_espn_final_scoreboard_sha256'],
           'chosen_side':x['selected_side'],'original_selection_won':bool(win),
           'source_book_priced_simulated_unit_result':round(profit(x['original_american_price']) if win else -1.,9),
           'actual_wager_or_verified_execution':False,'research_only':True,
        })
    added=append(GRADES,incoming)
    existing=rows(GRADES)
    qualified=[x for x in existing if x['original_research_screen_pass']]
    return {
        'new_official_final_games_graded':added,'all_official_games_graded':len(existing),
        'original_research_screen_qualifying_games_graded':len(qualified),
        'qualifier_wins':sum(x['original_selection_won'] for x in qualified),
        'qualifier_losses':sum(not x['original_selection_won'] for x in qualified),
        'qualifier_simulated_units':round(sum(x['source_book_priced_simulated_unit_result'] for x in qualified),6),
        'actual_verified_wagers':0,'market_advantage_proven':False,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--stage',choices=('capture','grade','both'),required=True)
    a=p.parse_args()
    summary={'observed_at_utc':datetime.now(timezone.utc).isoformat(),
             'research_only_not_live_betting_picks':True}
    if a.stage in ('capture','both'):summary['capture']=capture()
    if a.stage in ('grade','both'):summary['grade']=grade()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temp=SUMMARY.with_suffix('.tmp')
    with temp.open('w') as f:
        json.dump(summary,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(temp,SUMMARY)
    print('ZENITH_NFL_70_PRICE_VALUE_SHADOW',json.dumps(summary,sort_keys=True))

if __name__=='__main__':main()
