"""Official MLB probable pitcher/2025 park research frozen before the next game.

A PROSPECTIVE, source-time version-3 research lane that doesn't change
original V1/V2, first bookmaker quotes or already frozen 8-feature forecasts.
Pitcher numbers are strictly prior completed games, with original StatsAPI
final game master crosschecks and dual-source per-stat conflict detection.
The probable starter is NOT called confirmed, and "park context" comes from
the 2025 completed regular season, not 2026 final-season aggregate data.
"""
from __future__ import annotations

from datetime import datetime,timezone
from pathlib import Path
from collections import Counter
import argparse
import fcntl
import hashlib
import json
import os

import numpy as np
import pandas as pd

from .mlb_asof_feature_store import ROOT,sha_file
from .mlb_live_research_feature_freeze_v2 import (
    OUTPUT as V2_SOURCE,
    SCHEMA as V2_SCHEMA,
    REVISION as V2_REVISION,
)
from .mlb_live_research_feature_freeze import SOURCE as ORIGINAL_LINEUPS

OUT=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V3_PROBABLE_PITCHER_PRIOR_PARK_RESEARCH.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V3_PROBABLE_PITCHER_PRIOR_PARK_SUMMARY.json'
FULL=ROOT/'intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_HISTORY.csv'
INCREMENTAL=ROOT/'intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_LEDGER.csv'
MASTER=ROOT/'baseball_vault/derived/MLB_GAME_MASTER.csv'

SCHEMA='MLB_V3_TRUE_PREGAME_PROBABLE_PITCHER_AND_PRIOR_2025_PARK_RESEARCH_V1'
ALLOWED_TYPES={'R','D','F','L','W'}
STAT_KEYS=('outs','hits_allowed','walks_allowed','strikeouts','home_runs_allowed','games_started')
FULL_FIELDS=[
    'game_pk','player_id','season','official_date','game_date','status',
    'game_type','group','team',*STAT_KEYS,
]
RECENT_FIELDS=[
    'gamePk','player_id','season','officialDate','group','team',
    'outs','hits_allowed','walks_allowed','pitcher_strikeouts',
    'home_runs_allowed','games_started',
]
GAME_FIELDS=[
    'gamePk','officialDate','gameDate','gameType','status','venue_id',
    'home_team','away_team','home_score','away_score',
]


def _utc(value)->pd.Timestamp:
    dt=pd.to_datetime(value,errors='coerce',utc=True)
    if pd.isna(dt):raise ValueError('Invalid or missing original source-time fixture/feature clock')
    return dt


def _unique(frame:pd.DataFrame,keys:list[str],label:str)->None:
    if not set(keys).issubset(frame.columns) or frame[keys].isna().any().any() or frame.duplicated(keys).any():
        raise ValueError(f'Duplicate or missing {label} official source ID')


def prior_season_park(
    master:pd.DataFrame,*,venue_id:int,source_year:int,home_team:str,
    min_park_games:int=40,
)->tuple[float,dict]:
    needed={'gamePk','officialDate','gameType','status','venue_id','home_team','home_score','away_score'}
    if missing:=needed-set(master.columns):
        raise ValueError(f'Missing original official park fixture fields: {sorted(missing)}')
    if source_year<2017 or not venue_id or not home_team:
        raise ValueError('Expected verified official venue and completed prior park season')
    _unique(master,['gamePk'],'park official game master')
    prior=master[
        master.officialDate.astype(str).str[:4].eq(str(source_year-1))
        & master.gameType.eq('R') & master.status.eq('Final')
    ].copy()
    prior['runs']=pd.to_numeric(prior.home_score,errors='coerce')+pd.to_numeric(prior.away_score,errors='coerce')
    prior=prior[prior.runs.notna()&prior.runs.ge(0)&prior.runs.le(60)].copy()
    if len(prior)<min_park_games:
        raise ValueError('Insufficient prior regular-season league park source')
    park=prior[prior.venue_id.eq(venue_id)&prior.home_team.eq(home_team)]
    if len(park)<min_park_games:
        raise ValueError('Insufficient prior park sample at the official home team venue')
    prior_avg=float(prior.runs.mean())
    venue_avg=float(park.runs.mean())
    if not 2<=prior_avg<=20 or not np.isfinite(venue_avg):
        raise ValueError('Prior park season official run samples invalid')
    result=venue_avg/prior_avg
    if not .4<result<2.:
        raise ValueError('Prior park factor outside plausible descriptive range')
    return round(result,6),{
        'source_completed_park_season':source_year-1,
        'prior_regular_season_park_games':len(park),
        'prior_league_completed_regular_games':len(prior),
        'prior_park_average_total_runs':round(venue_avg,6),
        'prior_league_average_total_runs':round(prior_avg,6),
        'same_season_or_future_games_used':0,
        'park_inference_not_confirmed_weather_or_roof':True,
        'prior_park_factor_is_descriptive_not_intrinsic_pitcher_advantage':True,
    }


def reconcile_official_pitcher_history(
    older:pd.DataFrame,recent:pd.DataFrame,master:pd.DataFrame,
    *,season:int=2026,
)->tuple[pd.DataFrame,dict]:
    if missing:=set(FULL_FIELDS)-set(older.columns):
        raise ValueError(f'Missing legacy pitching stats: {sorted(missing)}')
    if missing:=set(RECENT_FIELDS)-set(recent.columns):
        raise ValueError(f'Missing incremental pitching stats: {sorted(missing)}')
    if missing:=set(GAME_FIELDS)-set(master.columns):
        raise ValueError(f'Missing independently verified game master: {sorted(missing)}')
    _unique(master,['gamePk'],'official game master')
    old=older[
        older.season.eq(season)&older.group.eq('PITCHING')
        &older.status.eq('Final')&older.game_type.isin(ALLOWED_TYPES)
    ].copy()
    new=recent[(recent.season.eq(season))&recent.group.eq('PITCHING')].copy()
    _unique(old,['game_pk','player_id'],'old official pitching game/player')
    _unique(new,['gamePk','player_id'],'new official pitching game/player')
    old['game_pk']=old.game_pk.astype(int)
    old['player_id']=old.player_id.astype(int)
    old['source_history_origin']='LEGACY_OFFICIAL_FINAL_PITCHER_BOXSCORE'
    new=new.rename(columns={'gamePk':'game_pk','officialDate':'official_date',
                            'pitcher_strikeouts':'strikeouts'})
    new['game_pk']=new.game_pk.astype(int)
    new['player_id']=new.player_id.astype(int)
    games=master.rename(columns={
        'gamePk':'game_pk','officialDate':'master_official_date',
        'gameDate':'master_game_date','gameType':'master_game_type',
        'status':'master_status','home_team':'master_home_team',
        'away_team':'master_away_team',
    })
    fields=['game_pk','master_official_date','master_game_date','master_game_type',
            'master_status','master_home_team','master_away_team']
    ref=games[fields]
    enriched_old=old.merge(ref,on='game_pk',how='left',validate='many_to_one')
    enriched_new=new.merge(ref,on='game_pk',how='left',validate='many_to_one')
    # For an official Final game whose fixture identity is already in the
    # independently verified game master, a date/team conflict is an
    # actionable data-quality failure, not a record to be silently discarded.
    final_recent=enriched_new[enriched_new.master_status.eq('Final')]
    if final_recent.official_date.astype(str).ne(final_recent.master_official_date.astype(str)).any():
        raise ValueError('Incremental pitcher official date differs from independent Final game master')
    if (~final_recent.apply(lambda r:r.team in (r.master_home_team,r.master_away_team),axis=1)).any():
        raise ValueError('Incremental pitcher official team conflicts with independent Final fixture')
    # The final game master is separate from the original player source; both
    # must independently certify the game was already Final, and same team,
    # game/date type. Do NOT trust a player result for a scheduled game.
    def valid(df,legacy):
        no=(
            df.master_status.ne('Final')
            | df.master_game_type.isna()
            | ~df.master_game_type.isin(ALLOWED_TYPES)
            | df.master_official_date.astype(str).ne(df.official_date.astype(str))
            | ~df.apply(lambda r:r.team in (r.master_home_team,r.master_away_team),axis=1)
        )
        if legacy:
            no |= df.game_type.astype(str).ne(df.master_game_type.astype(str))
        return df[~no].copy(),int(no.sum())
    old,old_rejected=valid(enriched_old,True)
    new,new_rejected=valid(enriched_new,False)
    for name,frame in [('legacy',old),('incremental',new)]:
        for col in STAT_KEYS:
            frame[col]=pd.to_numeric(frame[col],errors='coerce')
            if frame[col].isna().any() or (frame[col]<0).any():
                raise ValueError(f'Conflicting or invalid {name} official pitching stat {col}')
    overlap=new.merge(old[['game_pk','player_id','official_date','team',*STAT_KEYS]],
                      on=['game_pk','player_id'],how='inner',
                      suffixes=('_new','_old'),validate='one_to_one')
    count=0
    for col in ('official_date','team'):
        count+=int((overlap[f'{col}_new'].astype(str)!=overlap[f'{col}_old'].astype(str)).sum())
    for col in STAT_KEYS:
        count+=int(((overlap[f'{col}_new']-overlap[f'{col}_old']).abs()>1e-6).sum())
    if count:
        raise ValueError(f'Official pitching sources conflict on {count} shared game/player/stat values')
    oldkeys=set(zip(old.game_pk,old.player_id))
    additions=new[[x not in oldkeys for x in zip(new.game_pk,new.player_id)]].copy()
    additions['game_date']=additions.master_game_date
    additions['game_type']=additions.master_game_type
    additions['status']='Final'
    additions['source_history_origin']='INCREMENTAL_OFFICIAL_FINAL_PITCHER_MASTER_CROSSCHECKED'
    out=pd.concat([old,additions],ignore_index=True,sort=False)
    _unique(out,['game_pk','player_id'],'reconciled official pitcher history')
    out['game_date']=pd.to_datetime(out.game_date,utc=True,errors='coerce')
    if out.game_date.isna().any() or out.official_date.isna().any():
        raise ValueError('Pitcher history has missing official dates or kickoff')
    # The source game master may preserve an older scheduled start; only prior
    # completed/calendar dates enter, never results of games later that day.
    out['source_verified_before_quote_required']=True
    out=out.sort_values(['official_date','game_date','game_pk','player_id']).reset_index(drop=True)
    proof={
        'old_eligible_final_pitcher_player_game_rows':len(old),
        'incremental_eligible_final_pitcher_player_game_rows':len(new),
        'verified_overlap_pitcher_player_games':len(overlap),
        'new_final_pitcher_player_game_rows':len(additions),
        'new_final_distinct_game_ids':int(additions.game_pk.nunique()),
        'not_final_or_unsupported_rows_rejected':old_rejected+new_rejected,
        'source_date_and_team_and_game_status_crosschecked':True,
        'stat_source_conflict_count':0,
        'unified_completed_pitcher_player_game_rows':len(out),
        'no_current_game_or_future_pitching_results_used_by_model':True,
    }
    return out,proof


def _snapshot_metrics(history:pd.DataFrame,pitcher:int,team:str,source_at:pd.Timestamp,
                     *,min_games:int)->dict:
    h=history[
        history.player_id.eq(int(pitcher))
        & history.team.eq(team)
        & history.source_verified_before_quote_required.eq(True)
        & history.official_date.astype(str).str[:10].lt(str(source_at.date()))
        & history.game_date.le(source_at-pd.Timedelta(hours=12))
    ].sort_values(['game_date','game_pk'])
    last10=h.tail(10)
    last5=h.tail(5)
    n=len(h)
    outs=float(last10.outs.sum()) if n else 0.
    if n and (last10[['outs','hits_allowed','walks_allowed','strikeouts']].isna().any().any() or outs<0):
        raise ValueError('Recent pitcher official source stats corrupt')
    gamesstarted=int(last10.games_started.sum()) if n else 0
    if n>=min_games and outs>0:
        rate=lambda col:round(float(last10[col].sum()*27/outs),6)
        return {
            'opposing_probable_pitcher_prior_game_count':n,
            'opposing_probable_pitcher_prior_last10_sample_games':len(last10),
            'opposing_probable_pitcher_recent_10_starts':gamesstarted,
            'opposing_probable_pitcher_prior_hits_allowed_total':int(last10.hits_allowed.sum()),
            'opposing_probable_pitcher_prior_strikeouts_total':int(last10.strikeouts.sum()),
            'opposing_probable_pitcher_recent_10_hits_allowed_per_9':rate('hits_allowed'),
            'opposing_probable_pitcher_recent_10_strikeouts_per_9':rate('strikeouts'),
            'opposing_probable_pitcher_recent_10_walks_allowed_per_9':rate('walks_allowed'),
            'opposing_probable_pitcher_recent_10_hr_allowed_per_9':rate('home_runs_allowed'),
            'opposing_probable_pitcher_recent_last5_outs_per_appearance':round(float(last5.outs.mean()),6),
            'opposing_probable_pitcher_prior_most_recent_official_date':str(h.iloc[-1].official_date),
            'opposing_probable_pitcher_prior_metric_sample_eligible':True,
        }
    return {
        'opposing_probable_pitcher_prior_game_count':n,
        'opposing_probable_pitcher_prior_last10_sample_games':len(last10),
        'opposing_probable_pitcher_recent_10_starts':gamesstarted,
        'opposing_probable_pitcher_prior_hits_allowed_total':int(last10.hits_allowed.sum()) if n else 0,
        'opposing_probable_pitcher_prior_strikeouts_total':int(last10.strikeouts.sum()) if n else 0,
        'opposing_probable_pitcher_recent_10_hits_allowed_per_9':None,
        'opposing_probable_pitcher_recent_10_strikeouts_per_9':None,
        'opposing_probable_pitcher_recent_10_walks_allowed_per_9':None,
        'opposing_probable_pitcher_recent_10_hr_allowed_per_9':None,
        'opposing_probable_pitcher_recent_last5_outs_per_appearance':None,
        'opposing_probable_pitcher_prior_most_recent_official_date':str(h.iloc[-1].official_date) if n else None,
        'opposing_probable_pitcher_prior_metric_sample_eligible':False,
    }


def construct_true_pregame_pitcher_park(
    original_line:str,event:dict,frozen:list[dict],history:pd.DataFrame,
    master:pd.DataFrame,*,now:datetime,min_pitcher_prior_games:int=5,
    min_park_games:int=40,
)->tuple[list[dict],dict]:
    if now.tzinfo is None:
        raise ValueError('Observational source time cannot be naive')
    captured=_utc(now)
    original_time=_utc(event.get('captured_at_utc'))
    kickoff=_utc(event.get('first_pitch_utc'))
    if captured>=kickoff:
        return [],{
            'status':'PAST_FIRST_PITCH_CONTEXT_FREEZE_REFUSED',
            'frozen_source_rows':0,
            'no_postgame_model_features_added':True,
        }
    if event.get('schema')!='MLB_PREGAME_SOURCE_EVIDENCE_V1' or original_time>=kickoff or original_time>captured:
        raise ValueError('Original MLB source was not captured before the upcoming fixture')
    if not original_line.endswith('\n') or json.loads(original_line)!=event:
        raise ValueError('Original MLB source JSONL bytes required, no approximated SHA')
    digest=hashlib.sha256(original_line.encode()).hexdigest()
    fx=event.get('fixture') or {}
    if str(fx.get('official_status_at_capture','')).upper() not in ('PRE-GAME','SCHEDULED','WARMUP','PRE-GAME WARMUP'):
        raise ValueError('Source fixture not originally verified as pregame')
    venue=fx.get('venue_id')
    park,parkproof=prior_season_park(
        master,venue_id=int(venue),source_year=kickoff.year,
        home_team=str(fx.get('home_team')),min_park_games=min_park_games,
    )
    game=master[master.gamePk.eq(int(event['game_pk']))]
    if len(game)!=1:
        raise ValueError('Current source fixture gamePk not unique in independent official master')
    cur=game.iloc[0]
    if cur.home_team!=fx.get('home_team') or cur.away_team!=fx.get('away_team') or int(cur.venue_id)!=int(venue):
        raise ValueError('Official current team/venue identity differs from original captured source')
    if str(cur.status) not in ('Scheduled','Pre-Game','In Progress','Live'):
        raise ValueError('Current official fixture has already become Final, not eligible for prospective freeze')
    start_master=_utc(cur.gameDate)
    delta=round(float((start_master-kickoff).total_seconds()/60),3)
    if fx.get('official_date')!=str(cur.officialDate):
        raise ValueError('Current official fixture date does not match source schedule')
    p=event.get('probable_pitchers') or {}
    if p.get('probable_status')!='OFFICIAL_SCHEDULE_PROBABLE_NOT_CONFIRMED':
        raise ValueError('Probable pitcher has not been independently captured from original official schedule')
    if not frozen:
        raise ValueError('No exact first frozen player/game source observations')
    seen=set();rows=[]
    for original in frozen:
        if original.get('schema')!=V2_SCHEMA or original.get('source_history_revision')!=V2_REVISION:
            raise ValueError('Unknown original official source feature schema')
        if original.get('betting_prediction_written') is not False or original.get('live_play_approved') is not False:
            raise ValueError('Only original research-only player-feature sources accepted')
        if original.get('original_append_only_line_sha256')!=digest:
            raise ValueError('Original official pregame batting order source SHA mismatch')
        if original.get('source_evidence_id')!=event.get('evidence_id'):
            raise ValueError('Original lineup event ID differs from first frozen source')
        pid=int(original.get('player_id'))
        gid=int(original.get('game_pk'))
        if gid!=int(event['game_pk']) or (gid,pid) in seen:
            raise ValueError('Duplicate/mismatched game and official player ID')
        seen.add((gid,pid))
        side=str(original.get('team_side_at_capture') or '')
        if side not in ('home','away'):
            raise ValueError('Team side must come from original confirmed lineup')
        lineup=(event.get('lineups') or {}).get(side) or {}
        identifiers=lineup.get('player_ids') or []
        if (
            len(identifiers)!=9 or len(set(map(str,identifiers)))!=9 or
            str(pid) not in {str(x) for x in identifiers} or
            lineup.get('confirmed_asof_capture') is not True or
            lineup.get('source')!='LIVE_FEED_OFFICIAL_BATTING_ORDER_CAPTURED_PREGAME'
        ):
            raise ValueError('Player missing original 9-person official batting order')
        source_freeze=_utc(original.get('feature_frozen_at_utc'))
        if not original_time<=source_freeze<=captured<kickoff or _utc(original.get('scheduled_first_pitch_utc'))!=kickoff:
            raise ValueError('Source chronology cannot be a postgame or future-context pregame claim')
        opponent_side='away' if side=='home' else 'home'
        raw_probable=p.get(f'{opponent_side}_probable_pitcher_id')
        if raw_probable is None:
            raise ValueError('Missing original source-captured opponent probable pitcher ID')
        opponent_pid=int(raw_probable)
        if opponent_pid!=int(original.get('opposing_probable_pitcher_id') or -1):
            raise ValueError('Original player source probable pitcher not identity matched')
        opponent_team=fx.get(f'{opponent_side}_team')
        metrics=_snapshot_metrics(history,opponent_pid,str(opponent_team),captured,min_games=min_pitcher_prior_games)
        weather=(event.get('weather') or {})
        forecast_known=weather.get('status')=='CAPTURED_NWS_FORECAST_NOT_OBSERVED_WEATHER'
        forecast_time=_utc(weather['forecast_generated_at_utc']) if forecast_known else None
        weather_safe=bool(forecast_known and forecast_time<=original_time)
        row={
            'schema':SCHEMA,
            'official_game_pk':gid,
            'mlbam_player_id':pid,
            'original_batting_order_line_sha256':digest,
            'original_pregame_evidence_id':event['evidence_id'],
            'source_original_lineup_captured_at_utc':original_time.isoformat(),
            'source_original_v2_player_frozen_at_utc':source_freeze.isoformat(),
            'source_pitcher_and_park_context_frozen_at_utc':captured.isoformat(),
            'official_source_game_first_pitch_utc':kickoff.isoformat(),
            'frozen_before_source_scheduled_first_pitch':True,
            'source_team_side':side,
            'source_opponent_team':opponent_team,
            'opposing_probable_pitcher_id':opponent_pid,
            'opposing_probable_pitcher_confirmed_starter':False,
            'opposing_pitcher_status':'OFFICIALLY_LISTED_PROBABLE_NOT_CONFIRMED_STARTER',
            'prior_park_venue_id':int(venue),
            'prior_park_venue_label':fx.get('venue'),
            'reference_prior_full_park_season':kickoff.year-1,
            'prior_park_run_factor':park,
            **parkproof,
            'stale_game_master_first_pitch_disagreement_flag':abs(delta)>3.,
            'game_master_original_kickoff_discrepancy_minutes':delta,
            'current_game_master_kickoff_for_predictions_permitted':False,
            'source_nws_forecast_only':weather_safe,
            'forecast_temperature_f':weather.get('forecast_temperature_f') if weather_safe else None,
            'forecast_wind_mph':weather.get('forecast_wind_mph') if weather_safe else None,
            'actual_first_pitch_weather_verified':False,
            'source_stadium_roof_status_confirmed':False,
            'current_game_result_or_postgame_pitcher_stats_used':False,
            'historical_source_time_class':'RESEARCH_LATER_PREKICKOFF_CONTEXT_NOT_AT_FIRST_BOOK_PRICE',
            'model_probabilities_predicted':False,
            'betting_picks_created':False,
            'live_play_approved':False,
            'independent_game_evidence_key':str(gid),
            **metrics,
        }
        rows.append(row)
    rows.sort(key=lambda x:(x['official_game_pk'],x['mlbam_player_id']))
    return rows,{
        'status':'TRUE_PREGAME_PITCHER_PARK_RESEARCH_CONTEXT_READY_NO_MODEL',
        'frozen_source_rows':len(rows),
        'independent_game_blocks':len({r['official_game_pk'] for r in rows}),
        'source_original_lineup_sha256':digest,
        'park_factor':park,
        'park_reference':parkproof,
        'different_current_master_start_source_detected':abs(delta)>3.,
        'unconfirmed_probable_pitcher_still_not_starting_lineup_verification':True,
        'probable_pitcher_history_player_rows_available':sum(r['opposing_probable_pitcher_prior_metric_sample_eligible'] for r in rows),
        'source_snapshot_eligible_for_first_earlier_book_price_prediction':False,
        'no_first_frozen_model_or_wager_changed':True,
    }


def _key(x:dict)->tuple:
    return int(x['official_game_pk']),int(x['mlbam_player_id'])


def _load(file:Path)->list[dict]:
    if not file.exists():return []
    with file.open('r',encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def append_once_source_context(path:Path,rows:list[dict])->int:
    if not rows:return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+'.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        old={}
        for x in _load(path):
            if x.get('schema')!=SCHEMA:
                raise ValueError('Unrecognized original frozen pitcher/park source context')
            k=_key(x)
            if k in old:raise ValueError('Duplicate pitcher/park source context identity')
            old[k]=x
        new=[];seen=set()
        for x in rows:
            if x.get('schema')!=SCHEMA or x.get('live_play_approved') is not False or x.get('model_probabilities_predicted') is not False:
                raise ValueError('Not the expected frozen source-only pregame context')
            if _utc(x['source_pitcher_and_park_context_frozen_at_utc'])>=_utc(x['official_source_game_first_pitch_utc']):
                raise ValueError('Cannot backdate pitcher source after first pitch')
            key=_key(x)
            if key in seen:raise ValueError('Duplicate current batch source context')
            seen.add(key)
            if key in old:
                # Stable original context is never updated later, even if
                # 2025 park data revised or pitcher starter assignments change.
                if old[key]!=x:
                    raise ValueError('First captured source context conflicts with a new source; preserve original')
                continue
            new.append(x)
        if new:
            with path.open('a',encoding='utf-8') as fd:
                for x in new:fd.write(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n')
                fd.flush();os.fsync(fd.fileno())
        return len(new)


def freeze_cycle(now:datetime|None=None)->dict:
    observed=now or datetime.now(timezone.utc)
    if observed.tzinfo is None:raise ValueError('Require timezone-aware original live source observation')
    originals={}
    with ORIGINAL_LINEUPS.open('r',encoding='utf-8') as src:
        for line in src:
            if line.strip():originals[hashlib.sha256(line.encode()).hexdigest()]=(line,json.loads(line))
    source_records=_load(V2_SOURCE)
    old={_key(x) for x in _load(OUT)}
    eligible_groups={}
    for x in source_records:
        k=_key({'official_game_pk':x['game_pk'],'mlbam_player_id':x['player_id']})
        if k in old:continue
        if _utc(x['feature_frozen_at_utc'])>_utc(observed):continue
        if _utc(observed)>=_utc(x['scheduled_first_pitch_utc']):continue
        sha=x.get('original_append_only_line_sha256')
        if sha not in originals:raise ValueError('Lost immutable original official lineup source SHA')
        eligible_groups.setdefault(sha,[]).append(x)
    if not eligible_groups:
        return {
            'status':'NO_NEW_ORIGINAL_PREGAME_PLAYER_CONTEXT_TO_CAPTURE',
            'time_utc':_utc(observed).isoformat(),
            'new_source_records':0,
            'previously_frozen_preserved':len(old),
            'large_history_loaded':False,
            'model_or_betting_picks_changed':False,
        }
    master=pd.read_csv(MASTER,usecols=GAME_FIELDS,low_memory=False)
    old_source=pd.read_csv(FULL,usecols=FULL_FIELDS,low_memory=False)
    incremental=pd.read_csv(INCREMENTAL,usecols=RECENT_FIELDS,low_memory=False)
    history,proof=reconcile_official_pitcher_history(old_source,incremental,master)
    new=0;details=[]
    for sha,players in eligible_groups.items():
        line,event=originals[sha]
        rows,audit=construct_true_pregame_pitcher_park(
            line,event,players,history,master,now=observed,
        )
        for r in rows:
            r['source_full_pitcher_ledger_sha256']=sha_file(FULL)
            r['source_recent_pitcher_ledger_sha256']=sha_file(INCREMENTAL)
            r['source_official_game_master_sha256']=sha_file(MASTER)
            r['source_reconciliation_conflicts']=proof['stat_source_conflict_count']
        amount=append_once_source_context(OUT,rows)
        new+=amount
        details.append(audit)
    records=_load(OUT)
    return {
        'status':'OFFICIAL_SOURCE_PITCHER_PARK_PROSPECTIVE_RESEARCH_CAPTURE_COMPLETE',
        'time_utc':_utc(observed).isoformat(),
        'new_source_records':new,
        'total_frozen_player_records':len(records),
        'independent_games':len({r['official_game_pk'] for r in records}),
        'previously_frozen_preserved':len(old),
        'large_history_loaded':True,
        'history_reconciliation':proof,
        'source_audits':details,
        'source_explicitly_starts_after_first_book_quote':True,
        'model_or_betting_picks_changed':False,
    }


def main():
    ap=argparse.ArgumentParser(description='As-of MLB official probable pitcher and completed previous-season park research')
    ap.add_argument('--stage',required=True,choices=['freeze_research_context'])
    args=ap.parse_args()
    state=freeze_cycle()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temporary=SUMMARY.with_suffix('.tmp')
    temporary.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
    os.replace(temporary,SUMMARY)
    print('MLB_PROBABLE_PITCHER_PRIOR_PARK_RESEARCH_FROZEN',json.dumps({
        k:v for k,v in state.items() if k not in ('history_reconciliation','source_audits')
    },sort_keys=True))


if __name__=='__main__':
    main()
