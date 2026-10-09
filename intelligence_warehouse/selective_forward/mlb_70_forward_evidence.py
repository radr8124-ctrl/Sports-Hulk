"""MLB Full16: register ONLY NEW future games for 70% confidence+price research.

Existing gamePk 849832 was already settled before this registration and is
never counted as a prospective selection. No model fitting, price calls or bets.
"""
from __future__ import annotations
import argparse,fcntl,hashlib,json,math,os
from datetime import datetime,timezone
from pathlib import Path
from .nfl_70_forward_evidence import stamp,implied,profit

ROOT=Path(__file__).resolve().parents[2]
SPEC=ROOT/"reports/ZENITH_MLB_FULL16_SELECTIVE_70_FORWARD_PREREG_2026-10-09.json"
SOURCE=ROOT/"intelligence_warehouse/mlb_pregame_capture/MLB_V4_SIXTEEN_FEATURE_ACTUAL_FORWARD_SHADOW.jsonl"
OFFICIAL=ROOT/"intelligence_warehouse/mlb_pregame_capture/MLB_V4_FULL16_SAME_NEW_QUOTE_OFFICIAL_THREEWAY_SCORES.jsonl"
OUT=ROOT/"intelligence_warehouse/selective_forward/MLB_FULL16_70_FIXED_VALUE_SHADOW.jsonl"
GRADES=ROOT/"intelligence_warehouse/selective_forward/MLB_FULL16_70_FIXED_VALUE_OFFICIAL_GRADES.jsonl"
SUMMARY=ROOT/"intelligence_warehouse/selective_forward/MLB_FULL16_70_FIXED_VALUE_RESEARCH_SUMMARY.json"
SCHEMA="ZENITH_MLB_NEW_POST_REGISTERED_FULL16_PLAYER_HITS_SEVENTY_VALUE_RESEARCH_V1"

def sha(b):return hashlib.sha256(b).hexdigest()

def records(p):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.is_file() else []

def key(x):return (int(x["official_game_pk"]),int(x["mlbam_player_id"]))

def create_selection(r,spec,now):
    game,player=key(r)
    if game==spec['excluded_already_graded_game_pk']:
        raise ValueError("PREVIOUSLY_SETTLED_FIRST_FULL16_GAME_EXCLUDED")
    if r.get('research_only') is not True or r.get('betting_play_approved') is not False or r.get('wager_executed') is not False:
        raise ValueError("SOURCE_FULL16_NOT_RESEARCH_ONLY")
    if r.get('market_metric')!='hits' or float(r.get('line',-1))!=.5 or r.get('canonical_probability_side')!='OVER':
        raise ValueError("NOT_PROVEN_EXACT_HITS_OVER_HALF_MARKET")
    if r.get('frozen_prejuly_model_sha256')!=spec['fixed_prejuly_ninefeature_market_context_plus_fourteen_prior_statistics_model_sha256']:
        raise ValueError("ORIGINAL_FROZEN_FULL16_COEFFICIENTS_DIFFER")
    if len(r.get('model_16_features') or [])!=16 or len(r.get('model_feature_names') or [])!=16:
        raise ValueError("NOT_ORIGINAL_16_COLUMN_MODEL")
    if r.get('probable_pitcher_confirmed_starter_model_input') is not False or r.get('actual_weather_or_roof_used_in_frozen_trained_model') is not False:
        raise ValueError("UNVERIFIED_STARTER_OR_ACTUAL_WEATHER_CLAIM")
    first=stamp(r['official_first_pitch_utc'])
    ctx=stamp(r['source_team_context_frozen_at_utc'])
    quote=stamp(r['source_quote_at_utc'])
    frozen=stamp(r['first_full_context_shadow_frozen_at_utc'])
    registered=stamp(spec['registered_at_utc'])
    if not (registered<frozen<first and ctx<quote<=frozen and now<first):
        raise ValueError("MLB_NEW_PROSPECTIVE_CONTEXT_QUOTE_CLOCK_INVALID")
    odds_over=float(r['source_raw_over_american'])
    odds_under=float(r['source_raw_under_american'])
    p_over=implied(odds_over);p_under=implied(odds_under)
    vig=p_over+p_under
    if not(1<vig<=1.25) or abs(vig-float(r['source_book_overround']))>2e-6:
        raise ValueError("MLB_ORIGINAL_PRICE_OVERROUND_INCONSISTENT")
    fair_over=p_over/vig
    if abs(fair_over-float(r['market_fair_prob_at_exact_new_quote']))>2e-6:
        raise ValueError("MLB_BOOK_QUOTE_AND_ORIGINAL_NO_VIG_NOT_PAIRED")
    model_over=float(r['sixteen_feature_context_shadow_prob'])
    if not math.isfinite(model_over) or not(.001<model_over<.999):
        raise ValueError("MALFORMED_ORIGINAL_FULL16_PROBABILITY")
    chosen="OVER_0_5" if model_over>=.5 else "UNDER_0_5"
    p=model_over if chosen=="OVER_0_5" else 1-model_over
    market=fair_over if chosen=="OVER_0_5" else 1-fair_over
    price=odds_over if chosen=="OVER_0_5" else odds_under
    age=(frozen-quote).total_seconds()
    edge=(p-market)*100
    paper_ev=(p*(1+profit(price))-1)*100
    t=spec['predeclared_thresholds']
    blockers=[]
    if p<t['minimum_chosen_win_probability']:blockers.append("MODEL_PROBABILITY_BELOW_70")
    if edge<t['minimum_advantage_over_same_book_no_vig_pp']:blockers.append("BOOK_EDGE_BELOW_3PP")
    if paper_ev<t['minimum_quoted_price_paper_ev_pct']:blockers.append("BOOK_PRICE_EV_BELOW_3PCT")
    if age<0 or age>t['maximum_original_price_age_seconds']:
        blockers.append("BOOK_QUOTE_TOO_OLD_AT_MODEL_FREEZE")
    for name in ('selected_sportsbook','source_provider','source_provider_event_uuid','source_provider_player_uuid','original_lineup_sha256'):
        if not str(r.get(name) or '').strip():raise ValueError("UNVERIFIED_ORIGINAL_PLAYER_GAME_PRICE_IDENTITY")
    return {
       'schema':SCHEMA,'experiment_id':spec['experiment_id'],
       'official_game_pk':game,'mlbam_player_id':player,'original_athlete':r['player_name_official'],
       'original_source_lineup_sha256':r['original_lineup_sha256'],
       'original_full16_model_sha256':r['frozen_prejuly_model_sha256'],
       'original_source_athlete_provider_uuid':r['source_provider_player_uuid'],
       'original_source_event_uuid':r['source_provider_event_uuid'],
       'source_provider':r['source_provider'],'original_book':r['selected_sportsbook'],
       'original_source_start_utc':first.isoformat(),
       'original_model_frozen_at_utc':frozen.isoformat(),
       'original_quote_time_utc':quote.isoformat(),
       'original_market_line':.5,'chosen_side':chosen,
       'original_book_selected_american_price':price,
       'original_full16_selected_win_probability':round(p,9),
       'source_book_no_vig_selected_win_probability':round(market,9),
       'model_over_book_advantage_pp':round(edge,6),
       'source_quoted_price_paper_ev_pct':round(paper_ev,6),
       'age_original_quote_at_model_freeze_seconds':round(age,1),
       'fixed_provisional_research_screen_pass':not blockers,
       'fixed_screen_blocker_reasons':blockers,
       'independent_source_game_block_id':str(game),
       'named_book_price_proven_executable':False,
       'research_only':True,'production_wager_approved':False
    }

def append(path,items):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+".lock").open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        old=records(path); prior={key(x):x for x in old}
        if len(prior)!=len(old):raise ValueError("DUPLICATED_OLD_MLB_RESEARCH")
        fresh=[];seen=set()
        for r in items:
            k=key(r)
            if k in seen:raise ValueError("DUPLICATED_NEW_MLB_RESEARCH")
            seen.add(k)
            if k in prior:
                if prior[k]!=r:raise ValueError("ORIGINAL_FROZEN_MLB_RESEARCH_WOULD_CHANGE")
                continue
            fresh.append(r)
        if fresh:
            with path.open('a',encoding='utf8') as f:
                for r in fresh:f.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
                f.flush();os.fsync(f.fileno())
        return len(fresh)

def capture(clock=None):
    now=clock or datetime.now(timezone.utc)
    if not now.tzinfo:raise ValueError("NAIVE_CAPTURE_CLOCK")
    spec=json.loads(SPEC.read_text())
    if spec['no_model_promotion_or_plays'] is not True:raise ValueError("MODEL_BET_CHANGE_NOT_AUTHORIZED")
    source=records(SOURCE)
    first=int(spec['preserved_initial_old_records'])
    prefix=b''.join(SOURCE.read_bytes().splitlines(keepends=True)[:first])
    if sha(prefix)!=spec['preserved_original_first_18_full16_sha256']:
        raise ValueError("ORIGINAL_ALREADY_GRADED_MLB_MODEL_SOURCE_CHANGED")
    original={key(r) for r in source}
    if len(original)!=len(source):raise ValueError("DUPLICATE_FROZEN_MLB_PLAYER_GAME")
    old={key(x) for x in records(OUT)}
    proposals=[];late=[]
    for r in source:
        if key(r) in old:continue
        if int(r['official_game_pk'])==int(spec['excluded_already_graded_game_pk']):continue
        if stamp(r['official_first_pitch_utc'])<=now:
            late.append(key(r));continue
        proposals.append(create_selection(r,spec,now))
    added=append(OUT,proposals)
    all_=records(OUT)
    return {
      'all_original_full16_player_forecasts':len(source),
      'old_scored_game_player_records_explicitly_excluded':first,
      'new_future_player_selection_or_abstention_records':added,
      'total_recorded_future_research_player_legs':len(all_),
      'independent_future_games_covered':len({x['official_game_pk'] for x in all_}),
      'provisional_paper_screen_pass_player_legs':sum(x['fixed_provisional_research_screen_pass'] for x in all_),
      'source_time_missed_frozen_new_players':len(late),
      'executed_wagers':0,'full16_model_was_retrained':False
    }

def grade():
    selections={key(r):r for r in records(OUT)}
    previous={key(r) for r in records(GRADES)}
    official=records(OFFICIAL)
    if len({key(r) for r in official})!=len(official):raise ValueError("DUPLICATE_MLB_OFFICIAL_ANALYTIC_GRADE")
    entries=[]
    for r in official:
        k=key(r)
        if k not in selections or k in previous:continue
        x=selections[k]
        if r.get('official_status')!='Final' or r.get('research_only') is not True or r.get('model_promoted_to_live_play') is not False:
            raise ValueError("GRADE_NOT_GENUINE_OFFICIAL_FINAL")
        if (r['original_training_model_sha256']!=x['original_full16_model_sha256']
           or r['original_official_pregame_source_sha256']!=x['original_source_lineup_sha256']
           or r['market_bookmaker']!=x['original_book']):
            raise ValueError("GRADE_NOT_SAME_ORIGINAL_PLAYER_LINEUP_BOOK_MODEL")
        if (stamp(r['original_model_prospectively_frozen_at_utc'])!=stamp(x['original_model_frozen_at_utc'])
           or stamp(r['original_source_new_quote_at_utc'])!=stamp(x['original_quote_time_utc'])
           or stamp(r['official_game_start_utc'])!=stamp(x['original_source_start_utc'])):
            raise ValueError("GRADE_ORIGINAL_MODEL_GAME_TIME_NOT_PRESERVED")
        y=r['actual_hits_over_half']
        hits=r['official_player_hits']
        if type(y)!=int or y not in (0,1) or not isinstance(hits,(int,float)) or hits<0 or bool(hits>=1)!=bool(y):
            raise ValueError("OFFICIAL_MLB_HITS_RESULT_NOT_GROUNDED")
        if not(stamp(x['original_source_start_utc'])<stamp(r['source_final_checked_at_utc'])<=datetime.now(timezone.utc)):
            raise ValueError("GAME_FINAL_WAS_NOT_INDEPENDENTLY_OBSERVED_AFTER_KICKOFF")
        win=(y==1) if x['chosen_side']=="OVER_0_5" else (y==0)
        entries.append({
         'schema':SCHEMA,'experiment_id':x['experiment_id'],
         'official_game_pk':k[0],'mlbam_player_id':k[1],
         'independent_game_block_id':str(k[0]),
         'original_research_screen_pass':x['fixed_provisional_research_screen_pass'],
         'original_chosen_side':x['chosen_side'],'official_actual_player_hits':hits,
         'original_selection_won':win,
         'original_book_quote_paper_unit_result':round(profit(x['original_book_selected_american_price']) if win else -1,9),
         'real_sportsbook_execution_or_payout_verified':False,
         'research_only':True
        })
    added=append(GRADES,entries)
    all_=records(GRADES);passing=[r for r in all_ if r['original_research_screen_pass']]
    return {
      'new_real_official_player_hits_grades':added,
      'total_official_player_grade_rows':len(all_),
      'independent_official_game_blocks':len({r['independent_game_block_id'] for r in all_}),
      'fixed_research_qualifier_wins':sum(x['original_selection_won'] for x in passing),
      'fixed_research_qualifier_losses':sum(not x['original_selection_won'] for x in passing),
      'fixed_research_qualified_paper_units':round(sum(x['original_book_quote_paper_unit_result'] for x in passing),6),
      'betting_profitability_or_model_edge_proven':False,
      'real_wagers_placed':0
    }

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['capture','grade','both'],required=True)
    args=p.parse_args()
    info={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'production_model_or_wagers_changed':False}
    if args.stage in ('capture','both'):info['capture']=capture()
    if args.stage in ('grade','both'):info['grade']=grade()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    tmp=SUMMARY.with_suffix('.tmp')
    with tmp.open('w') as f:
        json.dump(info,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,SUMMARY)
    print("ZENITH_MLB_FULL16_70_PRICE_VALUE_FUTURE_RESEARCH",json.dumps(info,sort_keys=True))

if __name__=='__main__':main()
