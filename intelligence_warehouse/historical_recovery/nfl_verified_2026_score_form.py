"""NFL 2026 prior team scoring/defence form independently ESPN-Final verified.

Never uses future games or 2026 completed-season totals. The 2026 nflverse
schedule's first four weeks' results must agree EXACTLY with independent ESPN
Final scores, event ID, numeric team IDs/aliases, game week and original kickoff
before becoming eligible as source inputs for an upcoming Week5 NFL game.

Preserves full original four ESPN scoreboard responses in append-only private
receipts, one canonical game per original 2026 Final in another private ledger,
and one frozen source-only team-form context per ESPN future fixture. No
bookmaker model predictions / betting picks / Survivor records changed.
"""
from __future__ import annotations

from datetime import datetime,timezone
from collections import defaultdict,Counter
from pathlib import Path
import argparse,fcntl,hashlib,json,os

import numpy as np
import pandas as pd
import requests

from .mlb_asof_feature_store import ROOT,sha_file
from nfl_live.decision.espn_injury_identity import ESPN_NFL_TEAMS

SCHEDULE=ROOT/'nfl_live/derived/NFLVERSE_2026_SCHEDULE.csv'
ESPN_PREGAME=ROOT/'intelligence_warehouse/pregame_source_evidence/NFL_PREGAME_SOURCE_EVIDENCE.jsonl'
HISTORICAL=ROOT/'data_vault/derived/NFL_GAME_MASTER.csv'
ESPN_RAW=ROOT/'intelligence_warehouse/nfl_advanced_pregame/NFL_2026_ORIGINAL_ESPN_FINAL_WEEKLY_SCOREBOARDS.jsonl'
FINALS=ROOT/'intelligence_warehouse/nfl_advanced_pregame/NFL_2026_VERIFIED_PRIOR_FINAL_SCORES.jsonl'
CONTEXT=ROOT/'intelligence_warehouse/nfl_advanced_pregame/NFL_2026_FIRST_PREGAME_TEAM_FORM_CONTEXT.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/nfl_advanced_pregame/NFL_2026_FINAL_GAME_AND_TEAM_FORM_SOURCE_RECEIPT.json'
FROZEN_MODEL=ROOT/'reports/NFL_2016_2024_PRIOR_SCORE_FORM_9COL_FROZEN_MODEL_20261009.json'
RAW_SCHEMA='NFL_2026_ESPNSCOREBOARD_POST_FINAL_ORIGINAL_WEEK_RESPONSE_V1'
FINAL_SCHEMA='NFL_2026_ESPN_GAME_ID_SCORE_FINAL_SOURCE_MATCH_V1'
CONTEXT_SCHEMA='NFL_2026_PREGAME_SOURCE_FROZEN_PRIOR_TEAM_SCORE_FORM_V1'
ESPN_ALIAS={'LAR':'LA','WSH':'WAS'}
REPORT_THRESHOLD=12
URL='https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard'


def _utc(val):
    a=pd.to_datetime(val,utc=True,errors='coerce')
    if pd.isna(a):
        raise ValueError('Original ESPN score source has invalid/missing timestamp')
    return a


def _team(abbr):
    a=str(abbr or '').upper()
    return ESPN_ALIAS.get(a,a)


def _hash(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _read(path):
    if not path.is_file():return []
    with path.open('r',encoding='utf-8') as f:return [json.loads(x) for x in f if x.strip()]


def _unique_key(record,kind):
    if kind=='score':return str(record['official_espn_game_id'])
    if kind=='context':return str(record['official_espn_event_id'])
    if kind=='week':return int(record['week'])
    raise ValueError('Unrecognized source identity type')


def append_first_source_rows(path:Path,rows:list[dict],*,kind:str='context')->int:
    if not rows:return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    lock=path.with_suffix(path.suffix+'.lock')
    with lock.open('a+b') as mutex:
        fcntl.flock(mutex,fcntl.LOCK_EX)
        previous={}
        for row in _read(path):
            key=_unique_key(row,kind)
            if key in previous:raise ValueError('Original verified NFL source already has duplicate identity')
            previous[key]=row
        ready=[];batch=set()
        for record in rows:
            key=_unique_key(record,kind)
            if key in batch:raise ValueError('Duplicate submitted original NFL source batch')
            batch.add(key)
            if key in previous:
                if previous[key]!=record:
                    raise ValueError('Previously captured official NFL source conflicts with corrected source')
                continue
            ready.append(record)
        if ready:
            with path.open('a',encoding='utf-8') as f:
                for rec in ready:
                    f.write(json.dumps(rec,sort_keys=True,separators=(',',':'))+'\n')
                f.flush();os.fsync(f.fileno())
        return len(ready)


def verify_completed_nfl_weeks(
    schedule:pd.DataFrame,original_scoreboards:dict[int,dict],*,
    captured_at_utc:datetime,source_schedule_sha256:str
)->tuple[list[dict],dict]:
    if captured_at_utc.tzinfo is None:raise ValueError('Original ESPN capture time must be timezone aware')
    observed=_utc(captured_at_utc)
    required={'espn','game_id','season','week','game_type','gameday',
              'home_team','away_team','home_score','away_score'}
    if absent:=required-set(schedule.columns):
        raise ValueError('nflverse original 2026 season schedule missing fields '+str(sorted(absent)))
    if schedule.duplicated(['game_id']).any() or schedule.espn.notna().sum()!=schedule.espn.nunique():
        raise ValueError('Duplicate original NFL game or ESPN game ID')
    if set(schedule.season.dropna())!={2026}:
        raise ValueError('Not original 2026 NFL season schedule')
    finished=schedule[schedule.home_score.notna()&schedule.away_score.notna()].copy()
    finished=finished[finished.week.isin(original_scoreboards)].copy()
    if not finished.empty and finished.duplicated(['espn']).any():
        raise ValueError('Duplicate ESPN id in scored NFL game source')
    by_id={str(int(rec.espn)):rec for rec in finished.itertuples(index=False)}
    result=[];used=set()
    for week,payload in sorted(original_scoreboards.items()):
        if not isinstance(week,int) or not 1<=week<=22:
            raise ValueError('Invalid independently captured ESPN football week')
        events=payload.get('events') or []
        if not isinstance(events,list):raise ValueError('Malformed ESPN weekly original scoreboard')
        for event in events:
            gid=str(event.get('id') or '')
            if gid in used:raise ValueError('Duplicate ESPN official game ID in weekly Final sources')
            used.add(gid)
            old=by_id.get(gid)
            if old is None:
                # The schedule may be stale while ESPN Final has new results.
                # Refuse; do not infer new scores without two-source match.
                if str((event.get('status') or {}).get('type',{}).get('name'))=='STATUS_FINAL':
                    raise ValueError('Original nflverse schedule missing final score for independent ESPN Final event')
                continue
            if int(old.week)!=int(week) or int(old.season)!=2026 or str(old.game_type) not in ('REG','WC','DIV','CON','SB'):
                raise ValueError('ESPN source and original 2026 week/season/game-type conflict')
            state=(event.get('status') or {}).get('type') or {}
            if state.get('name')!='STATUS_FINAL' or state.get('completed') is not True:
                raise ValueError('Scheduled game already has score but ESPN did not verify Final')
            if str((event.get('season') or {}).get('year',2026))!='2026':
                raise ValueError('ESPN original scoreboard season differs from NFL source')
            if (event.get('week') or {}).get('number',week)!=week:
                raise ValueError('Official ESPN source week number conflict')
            start=_utc(event.get('date'))
            if start>=observed:
                raise ValueError('An official NFL future kickoff cannot have completed final scores')
            if (observed-start)<pd.Timedelta(hours=REPORT_THRESHOLD):
                # For ordinary same-day Final source, 12h buffer is a
                # conservative policy to avoid accidental very fresh result
                # used for an imminent betting recommendation.
                raise ValueError('ESPN final source too near original kickoff for safe historic score form')
            if abs((start-pd.Timestamp(old.gameday,tz='UTC')).total_seconds())>36*3600:
                raise ValueError('Source NFL fixture official scheduled date inconsistent with ESPN kickoff')
            competition=(event.get('competitions') or [{}])[0]
            sides={}
            for participant in competition.get('competitors') or []:
                side=participant.get('homeAway')
                if side not in ('home','away') or side in sides:raise ValueError('Duplicate or unknown ESPN team side')
                club=participant.get('team') or {}
                abbr=str(club.get('abbreviation') or '')
                club_id=str(club.get('id') or '')
                canonical=_team(abbr)
                expected=str(getattr(old,f'{side}_team'))
                if canonical!=expected:
                    raise ValueError('ESPN final team abbreviation conflicts with original NFL fixture')
                if _team(ESPN_NFL_TEAMS.get(club_id))!=expected:
                    raise ValueError('ESPN final numeric team ID conflicts with original NFL fixture team identity')
                try:score=float(participant['score'])
                except (ValueError,TypeError,KeyError):raise ValueError('Missing original ESPN Final team score') from None
                if not np.isfinite(score) or score<0 or not score.is_integer() or score>150:
                    raise ValueError('Invalid original ESPN Final score')
                if score!=float(getattr(old,f'{side}_score')):
                    raise ValueError('Official ESPN Final score differs from original 2026 schedule')
                sides[side]=(int(score),club_id,abbr,canonical)
            if set(sides)!={'home','away'}:raise ValueError('Not both final NFL source team records')
            result.append({
                'schema':FINAL_SCHEMA,'game_id':str(old.game_id),
                'official_espn_game_id':gid,'season':2026,'week':week,
                'home_team':sides['home'][3],'away_team':sides['away'][3],
                'original_espn_home_abbreviation':sides['home'][2],
                'original_espn_away_abbreviation':sides['away'][2],
                'home_espn_team_id':sides['home'][1],
                'away_espn_team_id':sides['away'][1],
                'home_points':sides['home'][0],
                'away_points':sides['away'][0],
                'source_first_pitch_utc':start.isoformat(),
                'final_observed_at_utc':observed.isoformat(),
                'official_espn_final_confirmed':True,
                'source_weekly_espn_payload_sha256':_hash(payload),
                'source_season_schedule_sha256':source_schedule_sha256,
                'final_score_not_verifiable_at_target_game_kickoff_without_prior_date':True,
                'market_model_or_wager_created':False,
            })
    if len(result)!=len(finished):
        raise ValueError('Some supposedly scored NFL games were not independently verified as ESPN Final')
    return sorted(result,key=lambda x:(x['week'],x['official_espn_game_id'])),{
        'schema':'NFL_2026_FINAL_2SOURCE_VERIFIED_PRIOR_SCORES_V1',
        'verified_unique_final_game_ids':len(result),
        'source_disagreements':0,
        'source_checked_weeks':sorted(original_scoreboards),
        'original_espn_rams_la_and_washington_was_aliases_preserved':True,
        'same_week_future_result_used_in_pregame_feature':False,
        'official_game_outcomes_only_from_final_source':True,
    }


def verified_prior_nfl_game_form(
    official_prior_games:pd.DataFrame,team:str,season:int,week:int,
    upcoming_kickoff:datetime,*,asof:datetime,
)->dict:
    if asof.tzinfo is None or upcoming_kickoff.tzinfo is None:
        raise ValueError('Need timezone-aware frozen NFL source')
    clock=_utc(asof)
    start=_utc(upcoming_kickoff)
    if clock>=start:raise ValueError('Cannot compute first pregame prior team form after kickoff')
    required={'game_id','season','week','home_team','away_team','home_points','away_points',
              'source_first_pitch_utc','final_observed_at_utc','official_espn_final_confirmed'}
    if required-set(official_prior_games.columns):
        raise ValueError('Missing verified official ESPN Final score-form source fields')
    d=official_prior_games.copy()
    if d.duplicated(['game_id']).any():raise ValueError('Duplicate previous NFL team-form game')
    prior=d[
        d.season.eq(season)&d.week.lt(week)&d.official_espn_final_confirmed.eq(True)
        & (d.home_team.eq(team)|d.away_team.eq(team))
    ].copy()
    prior['_start']=pd.to_datetime(prior.source_first_pitch_utc,utc=True,errors='coerce')
    prior['_observed']=pd.to_datetime(prior.final_observed_at_utc,utc=True,errors='coerce')
    if prior._start.isna().any() or prior._observed.isna().any():
        raise ValueError('Unverified official previous Final source timestamp')
    prior=prior[prior._start.lt(clock-pd.Timedelta(hours=REPORT_THRESHOLD))
               &prior._start.lt(start)
               &prior._observed.le(clock)].copy()
    if prior.week.duplicated().any():
        raise ValueError('Two official team results in one week require manual review')
    prior=prior.sort_values(['week','_start','game_id']).tail(3)
    result=[]
    for r in prior.itertuples(index=False):
        home=r.home_team==team
        pf=int(r.home_points if home else r.away_points)
        pa=int(r.away_points if home else r.home_points)
        result.append((pf,pa,int(r.week),str(r.game_id)))
    return {
        'team':team,'games_available':len(result),
        'prior_last_3_mean_points_scored':float(np.mean([x[0] for x in result])) if result else None,
        'prior_last_3_mean_points_allowed':float(np.mean([x[1] for x in result])) if result else None,
        'prior_last_3_mean_point_margin':float(np.mean([x[0]-x[1] for x in result])) if result else None,
        'source_official_game_ids':[x[3] for x in result],
        'max_prior_week':max((x[2] for x in result),default=None),
        'zero_current_target_week_games_entered':True,
        'all_scores_were_authentic_official_Final_before_capture':True,
    }


def _clip(val,scale):
    return float(np.clip(float(val)/scale,-2,2))


def make_features(home:dict,away:dict,home_rest,away_rest,neutral)->list[float]:
    h_n=int(home['games_available']);a_n=int(away['games_available'])
    if h_n and a_n:
        h_for=float(home['prior_last_3_mean_points_scored'])
        a_for=float(away['prior_last_3_mean_points_scored'])
        h_against=float(home['prior_last_3_mean_points_allowed'])
        a_against=float(away['prior_last_3_mean_points_allowed'])
        vals=[
            _clip((h_for-h_against)-(a_for-a_against),14),
            _clip((h_for-a_against)-(a_for-h_against),20),
            _clip(h_for-a_for,12),
            _clip(a_against-h_against,12),
        ]
    else:vals=[0.,0.,0.,0.]
    for days in (home_rest,away_rest):
        if days is None or pd.isna(days) or not 0<=float(days)<=30:
            raise ValueError('Original scheduled rest days invalid')
    vals.extend([_clip(float(home_rest)-float(away_rest),7),min(h_n,a_n,3)/3,float(bool(neutral))])
    if len(vals)!=7 or not np.isfinite(vals).all():raise ValueError('Invalid as-of score form vector')
    return [round(x,10) for x in vals]


def freeze_nfl_current_team_context(
    original_espn:list[dict],schedule:pd.DataFrame,official_final:pd.DataFrame,*,
    now:datetime,official_espn_source_sha256:str,
    schedule_snapshot_sha256:str,historical_model_sha256:str,
)->tuple[list[dict],dict]:
    if now.tzinfo is None:raise ValueError('Future context has no original observation timezone')
    for h in (official_espn_source_sha256,schedule_snapshot_sha256,historical_model_sha256):
        if len(h)!=64:raise ValueError('Missing full source lineage hash')
    clock=_utc(now)
    if 'espn' not in schedule or schedule.espn.dropna().duplicated().any():
        raise ValueError('Original 2026 future schedule ESPN fixture identity duplicates')
    candidates={str(int(r.espn)):r for r in schedule.itertuples(index=False) if pd.notna(r.espn)}
    seen=set();rows=[]
    for first in original_espn:
        eid=str(first.get('official_game_id') or '')
        if not eid.isdigit():raise ValueError('Unknown original ESPN pregame event ID')
        if eid in seen:
            # Same fixture may have multiple source snapshots. Exactly one
            # first-frozen TeamForm context is produced per ESPN game.
            continue
        seen.add(eid)
        fixture=first.get('fixture') or {}
        start=_utc(first.get('scheduled_start_utc'))
        captured=_utc(first.get('captured_at_utc'))
        if captured>=start or captured>clock or clock>=start:
            continue
        if fixture.get('game_state_asof') not in ('STATUS_SCHEDULED','STATUS_PRE_GAME','STATUS_WARMUP'):
            continue
        scheduled=candidates.get(eid)
        if scheduled is None:raise ValueError('Official ESPN pregame event missing from signed 2026 source schedule')
        if (int(scheduled.season)!=2026 or int(scheduled.week)!=int(fixture['week'])
            or _team(scheduled.home_team)!=_team(fixture['home_team'])
            or _team(scheduled.away_team)!=_team(fixture['away_team'])):
            raise ValueError('Original NFL Week5 fixture/source team identity mismatch')
        if fixture.get('actual_stadium_roof_state')!='UNKNOWN_NOT_OBSERVED':
            raise ValueError('Indoor attribute is NOT verified real roof state')
        home=verified_prior_nfl_game_form(official_final,_team(scheduled.home_team),2026,int(scheduled.week),start,asof=now)
        away=verified_prior_nfl_game_form(official_final,_team(scheduled.away_team),2026,int(scheduled.week),start,asof=now)
        x=make_features(home,away,scheduled.home_rest,scheduled.away_rest,
                        str(scheduled.location).lower()=='neutral')
        rows.append({
            'schema':CONTEXT_SCHEMA,
            'official_espn_event_id':eid,
            'source_schedule_game_id':str(scheduled.game_id),
            'season':2026,'week':int(scheduled.week),
            'home_team':_team(scheduled.home_team),
            'away_team':_team(scheduled.away_team),
            'source_espn_home_abbreviation':str(fixture['home_team']),
            'source_espn_away_abbreviation':str(fixture['away_team']),
            'original_pregame_espn_captured_at_utc':captured.isoformat(),
            'source_team_form_first_frozen_at_utc':clock.isoformat(),
            'official_first_pitch_utc':start.isoformat(),
            'home_prior_team_scoring_form':home,
            'away_prior_team_scoring_form':away,
            'source_2026_prior_final_team_home_games':home['games_available'],
            'source_2026_prior_final_team_away_games':away['games_available'],
            'scheduled_rest_home_days':float(scheduled.home_rest),
            'scheduled_rest_away_days':float(scheduled.away_rest),
            'scheduled_venue_is_neutral':str(scheduled.location).lower()=='neutral',
            'nine_features_excluding_market':x,
            'source_original_2026_scoreboard_sha256':official_espn_source_sha256,
            'source_2026_schedule_sha256':schedule_snapshot_sha256,
            'source_frozen_training_model_sha256':historical_model_sha256,
            'actual_stadium_roof_state_confirmed':False,
            'source_future_2026_weather_forecast_observed':False,
            'source_prior_2016_2025_epa_replayed_from_original_pbp':False,
            'prior_injury_report_verified_active_starter':False,
            'must_capture_new_bookmaker_quote_after_context_frozen':True,
            'original_first_market_only_quote_reused_as_prospective_model':False,
            'research_only':True,'betting_play_authorized':False,'wager_executed':False,
            'independent_source_game_block_id':eid,
        })
    rows.sort(key=lambda x:(x['official_first_pitch_utc'],x['official_espn_event_id']))
    return rows,{
        'schema':CONTEXT_SCHEMA,'unique_future_espn_games':len(rows),
        'source_current_season_2026_only':True,
        'model_fitted_or_wager_promoted':False,
        'upcoming_2026_game_outcomes_missing_as_required':True,
        'source_historical_match_score_inputs_were_independently_ESPN_Final':True,
    }


def completed_full_week_numbers(schedule:pd.DataFrame)->list[int]:
    """Never commit an ESPN week source on Thursday while Sunday is unplayed.

    Snapshot the entire original week's official games only when both
    numeric score columns are present for EVERY game in that football week.
    This prevents first-append receipts that would miss later Final results.
    """
    if not {'week','home_score','away_score','game_id'}.issubset(schedule.columns):
        raise ValueError('Missing complete NFL full-week schedule source')
    if schedule.game_id.duplicated().any():
        raise ValueError('Duplicated NFL schedule game identity')
    return sorted(int(week) for week,part in schedule.groupby('week') if (
        len(part)>0 and part.home_score.notna().all() and part.away_score.notna().all()
    ))


def collect_verified_completed_2026(*,now:datetime)->dict:
    if now.tzinfo is None:raise ValueError('Need source capture with UTC offset')
    current=_utc(now)
    latest=_read(ESPN_RAW)
    weeks={int(x['week']) for x in latest}
    original=pd.read_csv(SCHEDULE,low_memory=False)
    if set(original.season.dropna())!={2026}:raise ValueError('Current schedule is not uniquely 2026')
    # A partially played NFL Week5 does not become immutable prior-only
    # historical source after Thursday while Sunday and Monday remain future.
    season_weeks=completed_full_week_numbers(original)
    if not season_weeks:return {'status':'NO_COMPLETED_PRIOR_NFL_WEEKS_AVAILABLE','new_final_rows':0}
    pending=[week for week in season_weeks if week not in weeks]
    snapshots={}
    for week in pending:
        response=requests.get(URL,params={'dates':2026,'seasontype':2,'week':week,'limit':100},
                              headers={'User-Agent':'Sports-Zenith-NFL-Original-Final-Research/1.0'},
                              timeout=(3,10))
        response.raise_for_status()
        snapshots[week]=response.json()
    original_pages={int(x['week']):x['source_original_complete_espn_weekly_payload'] for x in latest}
    combined={**original_pages,**snapshots}
    verified,proof=verify_completed_nfl_weeks(
        original,combined,captured_at_utc=now,source_schedule_sha256=sha_file(SCHEDULE),
    )
    all_prior={x['official_espn_game_id']:x for x in _read(FINALS)}
    new=[r for r in verified if r['official_espn_game_id'] not in all_prior]
    all_orig=[]
    for week,payload in sorted(snapshots.items()):
        all_orig.append({
            'schema':RAW_SCHEMA,'week':week,'season':2026,
            'captured_at_utc':current.isoformat(),
            'source_uri':URL+f'?dates=2026&seasontype=2&week={week}&limit=100',
            'source_original_complete_espn_weekly_payload':payload,
            'source_original_json_sha256':_hash(payload),
            'source_verified_same_game_scores_against_original_nflverse':True,
            'future_games_not_silently_marked_final':True,
        })
    appended_pages=append_first_source_rows(ESPN_RAW,all_orig,kind='week')
    appended_games=append_first_source_rows(FINALS,new,kind='score')
    return {
        **proof,
        'status':'INDEPENDENT_ESPN_FINAL_SCORES_VERIFIED_VS_2026_NFLVERSE',
        'captured_at_utc':current.isoformat(),
        'source_first_original_scoreboard_weeks_added':appended_pages,
        'new_final_rows':appended_games,
        'total_independent_official_verified_finals':len(_read(FINALS)),
        'source_final_score_game_ids_have_not_become_forward_wagers':True,
    }


def freeze_cycle(now:datetime|None=None)->dict:
    clock=now or datetime.now(timezone.utc)
    if clock.tzinfo is None:raise ValueError('Real original NFL context clock requires timezone')
    existing=_read(CONTEXT)
    known={r['official_espn_event_id'] for r in existing}
    pending=[x for x in _read(ESPN_PREGAME) if x.get('official_game_id') not in known
             and _utc(x['scheduled_start_utc'])>_utc(clock)]
    if not pending:
        return {'status':'NO_NEW_ORIGINAL_NFL_PREQUOTE_TEAM_FORM_CONTEXT','new':0,
                'total_first_frozen_future_context':len(existing),'ESPN_network_requests':0}
    source=pd.read_csv(SCHEDULE,low_memory=False)
    final=pd.DataFrame(_read(FINALS))
    if final.empty:raise ValueError('No independent ESPN Final verified source exists for NFL 2026 team form')
    if not FROZEN_MODEL.is_file():raise ValueError('No earlier-pre-July? NFL source model must be frozen before future context')
    rows,proof=freeze_nfl_current_team_context(
        pending,source,final,now=clock,
        official_espn_source_sha256=sha_file(FINALS),
        schedule_snapshot_sha256=sha_file(SCHEDULE),
        historical_model_sha256=sha_file(FROZEN_MODEL),
    )
    amount=append_first_source_rows(CONTEXT,rows,kind='context')
    return {
        **proof,
        'status':'VERIFIED_PRIOR_2026_ESPN_FINAL_TEAM_FORM_CONTEXT_FROZEN_BEFORE_NEXT_BOOK',
        'source_context_observed_utc':_utc(clock).isoformat(),
        'new':amount,
        'total_first_frozen_future_context':len(_read(CONTEXT)),
        'independent_ESPN_game_blocks':len({r['official_espn_event_id'] for r in _read(CONTEXT)}),
        'source_2026_schedule_sha256':sha_file(SCHEDULE),
        'source_original_ESPN_final_canonical_sha256':sha_file(FINALS),
        'source_model_frozen_training_sha256':sha_file(FROZEN_MODEL),
        'model_predictive_edge_qualified':False,
        'bets_submitted':0,
    }


def main():
    p=argparse.ArgumentParser(description='Original 2026 ESPN final results independently cross-verified before NFL future form')
    p.add_argument('--stage',required=True,choices=['verify_prior_finals','freeze_future_team_form'])
    args=p.parse_args()
    if args.stage=='verify_prior_finals':
        result=collect_verified_completed_2026(now=datetime.now(timezone.utc))
    else:result=freeze_cycle()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temp=SUMMARY.with_suffix('.tmp')
    temp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    os.replace(temp,SUMMARY)
    print('NFL_INDEPENDENT_ESPN_FINAL_SCORES_ASOF_TEAM_FORM',json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
