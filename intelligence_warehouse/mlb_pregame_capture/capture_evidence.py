"""Capture MLB pregame source facts before first pitch; no betting decisions.

Research-only capture from official MLB schedule/feed and NWS weather forecasts.
Store source/time/provenance independently of mutable current MLB models. Never
claim a postgame boxscore is a pregame lineup, an assigned probable starter is
confirmed, forecast is actual weather, or a repeat capture is a new game.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Callable

import pandas as pd
import requests

ROOT=Path(__file__).resolve().parents[2]
LEDGER=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_PREGAME_SOURCE_EVIDENCE.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_PREGAME_CAPTURE_SUMMARY.json'
GAME_MASTER=ROOT/'baseball_vault/derived/MLB_GAME_MASTER.csv'
SCHEDULE_URL='https://statsapi.mlb.com/api/v1/schedule'
GAME_FEED_ROOT='https://statsapi.mlb.com/api/v1.1/game'
NWS_ROOT='https://api.weather.gov'
SCHEMA='MLB_PREGAME_SOURCE_EVIDENCE_V1'
USER_AGENT='SportsHULKResearch/1.0 (MLB pregame forecast and fixture research, read-only)'
PREGAME_STATES={'SCHEDULED','PRE-GAME','PRE-GAME WARMUP','WARMUP','PREVIEW','DELAYED START'}
DEFAULT_LOOKAHEAD_HOURS=48


def _utc(value):
    try:
        dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except (ValueError,TypeError,OverflowError):
        return None


def _iso(dt:datetime)->str:
    return dt.astimezone(timezone.utc).isoformat(timespec='seconds')


def _now():
    return datetime.now(timezone.utc)


def _json_fetch(url:str,params:dict|None=None):
    h={'User-Agent':USER_AGENT,'Accept':'application/geo+json,application/json'}
    r=requests.get(url,params=params,headers=h,timeout=(3,7))
    r.raise_for_status()
    if len(r.content)>2_000_000:
        raise ValueError('Unexpectedly large source reply; refused')
    return r.json()


def _is_pregame(status:object)->bool:
    return str(status or '').strip().upper() in PREGAME_STATES


def parse_schedule(schedule:dict,now:datetime,*,lookahead_hours:int=DEFAULT_LOOKAHEAD_HOURS)->list[dict]:
    """Return only unstarted MLB games with resolved team IDs and first pitch."""
    if now.tzinfo is None:
        raise ValueError('An offset-aware capture timestamp is required')
    if not 1<=lookahead_hours<=72:
        raise ValueError('Allowed lookahead is 1..72h')
    output=[]
    for day in schedule.get('dates',[]) if isinstance(schedule,dict) else []:
        for g in day.get('games',[]) or []:
            if not isinstance(g,dict) or g.get('startTimeTBD') is True:
                continue
            start=_utc(g.get('gameDate'))
            if start is None or start<=now or start>now+timedelta(hours=lookahead_hours):
                continue
            status=(g.get('status') or {}).get('detailedState')
            abstract=(g.get('status') or {}).get('abstractGameState')
            if not (_is_pregame(status) and _is_pregame(abstract)):
                continue
            teams=g.get('teams') or {}
            home=teams.get('home') or {}
            away=teams.get('away') or {}
            home_team=home.get('team') or {}
            away_team=away.get('team') or {}
            if not all([home_team.get('id'),away_team.get('id'),home_team.get('name'),away_team.get('name'),g.get('gamePk')]):
                continue
            if any(x in str(home_team['name'])+' '+str(away_team['name']) for x in ('TBD','/','Winner')):
                continue
            venue=g.get('venue') or {}
            row={
                'game_pk':int(g['gamePk']),
                'first_pitch_utc':_iso(start),
                'lead_minutes':round((start-now).total_seconds()/60,2),
                'official_game_type':g.get('gameType'),
                'official_date':g.get('officialDate') or day.get('date'),
                'home_team_id':int(home_team['id']),
                'home_team':str(home_team['name']),
                'away_team_id':int(away_team['id']),
                'away_team':str(away_team['name']),
                'venue_id':int(venue['id']) if venue.get('id') is not None else None,
                'venue':venue.get('name'),
                'official_status_at_capture':str(status),
                'source':'MLB_STATSAPI_SCHEDULE_DIRECT',
                'source_url':SCHEDULE_URL,
                'probable_status':'OFFICIAL_SCHEDULE_PROBABLE_NOT_CONFIRMED',
            }
            for side,block in (('home',home),('away',away)):
                probable=(block.get('probablePitcher') or {})
                pid=probable.get('id')
                row[f'{side}_probable_pitcher_id']=int(pid) if pid is not None else None
                row[f'{side}_probable_pitcher_name']=probable.get('fullName')
            output.append(row)
    return sorted(output,key=lambda row:(row['first_pitch_utc'],row['game_pk']))


def extract_official_pregame_lineups(feed:dict,game_pk:int,now:datetime,first_pitch:str)->dict:
    if now.tzinfo is None:
        raise ValueError('Offset-aware capture time required')
    start=_utc(first_pitch)
    if start is None or now>=start:
        return {'status':'CAPTURE_NOT_BEFORE_KICKOFF'}
    if not isinstance(feed,dict) or int(feed.get('gamePk') or 0)!=game_pk:
        return {'status':'FEED_GAME_ID_MISMATCH'}
    meta=feed.get('gameData') or {}
    status=(meta.get('status') or {})
    if not (_is_pregame(status.get('detailedState')) and _is_pregame(status.get('abstractGameState'))):
        return {'status':'FEED_IS_NOT_PREGAME'}
    feed_start=_utc((meta.get('datetime') or {}).get('dateTime'))
    if feed_start is None or abs((start-feed_start).total_seconds())>180:
        return {'status':'FEED_KICKOFF_CHANGED_REVIEW_REQUIRED'}
    sides=(feed.get('liveData') or {}).get('boxscore',{}).get('teams',{})
    if not isinstance(sides,dict):
        return {'status':'NOT_YET_PUBLISHED'}
    available={}
    for side in ('away','home'):
        side_data=sides.get(side) or {}
        batting=side_data.get('battingOrder') or []
        if len(batting)!=9 or len(set(str(pid) for pid in batting))!=9:
            continue
        lookup=side_data.get('players') or {}
        ids=[];names=[]
        for raw in batting:
            try:pid=int(raw)
            except (TypeError,ValueError):break
            player=lookup.get(f'ID{pid}') or {}
            person=player.get('person') or {}
            if person.get('id') is not None and int(person['id'])!=pid:break
            ids.append(pid)
            names.append(person.get('fullName'))
        if len(ids)==9:
            available[side]={
                'player_ids':ids,
                'player_names':names,
                'source':'LIVE_FEED_OFFICIAL_BATTING_ORDER_CAPTURED_PREGAME',
                'confirmed_asof_capture':True,
            }
    if not available:
        return {'status':'NOT_YET_PUBLISHED'}
    # Partial one-sided lineup still useful as source provenance, but the
    # card explicitly does not call it both-team confirmed.
    label='OFFICIAL_BATTING_ORDER_VISIBLE_BEFORE_KICKOFF' if len(available)==2 else 'ONLY_ONE_TEAM_LINEUP_VISIBLE_PREGAME'
    return {'status':label,'source_url':f'{GAME_FEED_ROOT}/{game_pk}/feed/live',**available}


def extract_nws_hourly_forecast(data:dict,now:datetime,first_pitch:str,*,source_url:str)->dict:
    start=_utc(first_pitch)
    if start is None or now.tzinfo is None or now>=start:
        return {'status':'QUOTE_NOT_BEFORE_FIRST_PITCH'}
    props=data.get('properties') if isinstance(data,dict) else None
    if not isinstance(props,dict):
        return {'status':'INVALID_NWS_FORECAST'}
    generated=_utc(props.get('generatedAt'))
    updated=_utc(props.get('updateTime'))
    if generated is None or updated is None or generated>now or updated>now:
        return {'status':'FORECAST_GENERATED_AFTER_CAPTURE'}
    if now-updated>timedelta(hours=14):
        return {'status':'FORECAST_TOO_STALE_FOR_PREGAME'}
    for period in props.get('periods',[]) or []:
        a=_utc(period.get('startTime'));b=_utc(period.get('endTime'))
        if a is None or b is None or not a<=start<b:
            continue
        temp=period.get('temperature')
        unit=period.get('temperatureUnit')
        if unit not in ('F','C') or not isinstance(temp,(int,float)):
            return {'status':'FORECAST_TEMPERATURE_INVALID'}
        precipitation=(period.get('probabilityOfPrecipitation') or {}).get('value')
        wind=period.get('windSpeed') or ''
        match=re.search(r'(\d+(?:\.\d+)?)',str(wind))
        speed=float(match.group(1)) if match else None
        return {
            'status':'CAPTURED_NWS_FORECAST_NOT_OBSERVED_WEATHER',
            'source_url':source_url,
            'source_generated_at_utc':_iso(generated),
            'forecast_generated_at_utc':_iso(generated),
            'forecast_updated_at_utc':_iso(updated),
            'source_captured_at_utc':_iso(now),
            'forecast_hour_start_utc':_iso(a),
            'forecast_hour_end_utc':_iso(b),
            'forecast_temperature_f':float(temp) if unit=='F' else round(temp*1.8+32,1),
            'forecast_wind_mph':speed,
            'forecast_precipitation_probability_pct':precipitation,
            'forecast_short_summary':period.get('shortForecast'),
            'roof_status_asof':'UNKNOWN_NOT_CAPTURED',
            'weather_model_use':'RESEARCH_ONLY_NO_CONFIRMED_ROOF_STATE',
        }
    return {'status':'NO_FORECAST_PERIOD_CONTAINING_FIRST_PITCH'}


def resolve_venue_coordinates(game:dict,master:pd.DataFrame)->dict:
    """Use existing mapped home-team coordinates ONLY for a verified 2025 park."""
    home=((game.get('teams') or {}).get('home') or {}).get('team') or {}
    name=home.get('name')
    venue=(game.get('venue') or {}).get('id')
    if not name or venue is None:
        return {'status':'VENUE_COORDINATES_NOT_VERIFIED'}
    if name=='Toronto Blue Jays':
        return {'status':'NO_US_NWS_FORECAST'}
    from baseball_vault.weather import PARKS
    coords=PARKS.get(name)
    if not coords:
        return {'status':'VENUE_COORDINATES_NOT_VERIFIED'}
    needed={'gamePk','officialDate','home_team','venue_id','gameType','status'}
    if not needed.issubset(master.columns):
        return {'status':'VENUE_OFFICIAL_CROSSWALK_UNAVAILABLE'}
    historical=master[
        master.officialDate.astype(str).str.startswith('2025')
        & master.gameType.astype(str).eq('R')
        & master.status.astype(str).eq('Final')
        & master.home_team.astype(str).eq(str(name))
    ]
    venues=historical.groupby('venue_id').gamePk.nunique().sort_values(ascending=False)
    if venues.empty or int(venues.iloc[0])<20 or int(venues.index[0])!=int(venue):
        return {'status':'VENUE_COORDINATES_NOT_VERIFIED'}
    return {'status':'PRIOR_OFFICIAL_VENUE_ID_MATCHED','latitude':float(coords[0]),'longitude':float(coords[1]),
            'venue_id':int(venue),'crosswalk_source_season':2025,
            'coordinates_origin':'EXISTING_HULK_KNOWN_HOME_PARK_APPROXIMATION'}


def compose_evidence(game:dict,now:datetime,*,feed_lineups:dict,weather:dict,capture_interval_minutes:int=10)->dict:
    if now.tzinfo is None or _utc(game.get('first_pitch_utc')) is None or now>=_utc(game['first_pitch_utc']):
        raise ValueError('No evidence capture can occur at/after scheduled first pitch')
    stamp=_iso(now)
    if capture_interval_minutes not in (10,60,180):
        raise ValueError('Unsupported evidence capture interval')
    seconds=capture_interval_minutes*60
    t=int(now.timestamp())
    slot=_iso(datetime.fromtimestamp((t//seconds)*seconds,timezone.utc))
    game_pk=int(game['game_pk'])
    key=f'{SCHEMA}|{game_pk}|{slot}'
    return {
        'schema':SCHEMA,
        'evidence_id':hashlib.sha256(key.encode()).hexdigest()[:32],
        'captured_at_utc':stamp,
        'capture_slot_utc':slot,
        'capture_interval_minutes':capture_interval_minutes,
        'game_pk':game_pk,
        'first_pitch_utc':game['first_pitch_utc'],
        'lead_minutes_at_capture':round((_utc(game['first_pitch_utc'])-now).total_seconds()/60,2),
        'fixture':{k:game.get(k) for k in ('home_team_id','home_team','away_team_id','away_team','venue_id','venue','official_date','official_game_type','official_status_at_capture')},
        'probable_pitchers':{k:game.get(k) for k in ('home_probable_pitcher_id','home_probable_pitcher_name','away_probable_pitcher_id','away_probable_pitcher_name','probable_status')},
        'probable_pitcher_source':game.get('source_url'),
        'lineups':feed_lineups,
        'weather':weather,
        'is_confirmed_starting_pitcher':False,
        'historical_model_approved':False,
        'forward_model_picks_recorded':False,
        'model_use_status':'AS_OF_RESEARCH_CAPTURE_NOT_VALIDATED_PROBABILITY_SIGNAL',
        'source_rights_status':'VERIFY_MLB_AND_NWS_PROVIDER_RIGHTS_BEFORE_COMMERCIAL_REUSE',
    }


def append_snapshot_once(path:Path,record:dict)->bool:
    """Immutable JSONL append. Concurrent invocations use a separate lock."""
    now=_utc(record.get('captured_at_utc'))
    start=_utc(record.get('first_pitch_utc'))
    if record.get('schema')!=SCHEMA or now is None or start is None or now>=start:
        raise ValueError('Invalid source-evidence timestamp or schema')
    path.parent.mkdir(parents=True,exist_ok=True)
    lock=path.with_suffix(path.suffix+'.lock')
    with lock.open('a+b') as l:
        fcntl.flock(l,fcntl.LOCK_EX)
        if path.exists():
            with path.open('r',encoding='utf-8') as existing:
                for line in existing:
                    if not line.strip():continue
                    try:prior=json.loads(line)
                    except json.JSONDecodeError:raise ValueError('Corrupted append-only evidence: refused to write')
                    if prior.get('evidence_id')==record.get('evidence_id'):
                        return False
        with path.open('a',encoding='utf-8') as out:
            out.write(json.dumps(record,separators=(',',':'),ensure_ascii=False)+'\n')
            out.flush();os.fsync(out.fileno())
        return True


def _schedule_dates(now:datetime,lookahead_hours:int)->tuple[str,str]:
    today=now.date()
    end=(now+timedelta(hours=lookahead_hours)).date()
    return today.isoformat(),end.isoformat()


def _forecast_from_nws(game_raw:dict,master:pd.DataFrame,now:datetime,start:str,fetcher:Callable,*,prior_weather:dict|None=None,observed_clock:Callable|None=None)->dict:
    coord=resolve_venue_coordinates(game_raw,master)
    if coord['status']!='PRIOR_OFFICIAL_VENUE_ID_MATCHED':
        return {'status':coord['status']}
    if prior_weather and prior_weather.get('status')=='CAPTURED_NWS_FORECAST_NOT_OBSERVED_WEATHER':
        earlier=_utc(prior_weather.get('source_captured_at_utc'))
        if earlier and timedelta(0)<=now-earlier<=timedelta(minutes=50):
            reused={**prior_weather,'reused_previous_capture':True,
                    'source_age_minutes':round((now-earlier).total_seconds()/60,1)}
            return reused
    try:
        lat,lon=coord['latitude'],coord['longitude']
        points=fetcher(f'{NWS_ROOT}/points/{lat:.4f},{lon:.4f}')
        url=(points.get('properties') or {}).get('forecastHourly')
        if not url or not str(url).startswith('https://api.weather.gov/'):
            return {'status':'NWS_FORECAST_LINK_INVALID'}
        data=fetcher(url)
        # The weather snapshot's actual observation clock MUST be after the
        # HTTP response, not before its request (including slow networks).
        observed_at=observed_clock() if observed_clock is not None else _now()
        if observed_at>=_utc(start):
            return {'status':'WEATHER_SOURCE_ARRIVED_AFTER_FIRST_PITCH'}
        forecast=extract_nws_hourly_forecast(data,observed_at,start,source_url=url)
        forecast['venue_coordinates_source']=coord['coordinates_origin']
        return forecast
    except Exception as exc:
        return {'status':'NWS_SOURCE_UNAVAILABLE','source_error_type':type(exc).__name__}


def _last_weather(path:Path,game_pk:int,now:datetime)->dict|None:
    if not path.exists():return None
    previous=None
    with path.open('r',encoding='utf-8') as f:
        for line in f:
            if not line.strip():continue
            rec=json.loads(line)
            if rec.get('game_pk')==game_pk:
                weather=rec.get('weather') or {}
                if weather.get('status')=='CAPTURED_NWS_FORECAST_NOT_OBSERVED_WEATHER':
                    age=_utc(weather.get('source_captured_at_utc'))
                    if age and age<=now:previous=weather
    return previous


def _rotating_budget(rows:list[dict],now:datetime,budget:int)->set[int]:
    if not rows or budget<=0:
        return set()
    # At every 10-minute official refresh, rotate through all imminent games
    # instead of repeatedly querying the same 4 fixtures.
    offset=(int(now.timestamp())//600)%len(rows)
    selected=(rows[offset:]+rows[:offset])[:budget]
    return {r['game_pk'] for r in selected}


def _capture_frequency_minutes(lead_minutes:float)->int:
    if lead_minutes<=240:
        return 10
    if lead_minutes<=1440:
        return 60
    return 180


def _evidence_identifier(game_pk:int,now:datetime,interval:int)->str:
    rounded=(int(now.timestamp())//(60*interval))*(60*interval)
    slot=_iso(datetime.fromtimestamp(rounded,timezone.utc))
    return hashlib.sha256(f'{SCHEMA}|{game_pk}|{slot}'.encode()).hexdigest()[:32]


def _previous_capture_state(path:Path,now:datetime)->tuple[set[str],dict[int,dict]]:
    ids=set()
    weather={}
    if not path.exists():
        return ids,weather
    with path.open('r',encoding='utf-8') as infile:
        for line in infile:
            if not line.strip():continue
            previous=json.loads(line)
            if previous.get('schema')!=SCHEMA:continue
            ids.add(previous.get('evidence_id'))
            val=previous.get('weather') or {}
            pk=previous.get('game_pk')
            ts=_utc(val.get('source_captured_at_utc'))
            if (pk is not None and val.get('status')=='CAPTURED_NWS_FORECAST_NOT_OBSERVED_WEATHER'
                    and ts is not None and ts<=now):
                older=weather.get(int(pk))
                if older is None or _utc(older.get('source_captured_at_utc'))<ts:
                    weather[int(pk)]=val
    return ids,weather


def capture_once(path:Path=LEDGER,*,now:datetime|None=None,fetch_json:Callable|None=None,
                 weather_enabled:bool=True,lookahead_hours:int=DEFAULT_LOOKAHEAD_HOURS,
                 feed_max_games:int=4,weather_max_games:int=2,master_path:Path=GAME_MASTER)->dict:
    """One bounded capture. Every game gets probable/fixture evidence;
    live feed/NOAA requests rotate among eligible games within strict caps.
    """
    captured=now or _now()
    if captured.tzinfo is None:
        raise ValueError('Require real offset-aware observation clock')
    if not 1<=feed_max_games<=12 or not 0<=weather_max_games<=5:
        raise ValueError('API-call budget caps out of bounds')
    getter=fetch_json or _json_fetch
    start_day,end_day=_schedule_dates(captured,lookahead_hours)
    schedule=getter(SCHEDULE_URL,{'sportId':1,'startDate':start_day,'endDate':end_day,'hydrate':'team,venue,probablePitcher'})
    candidates=parse_schedule(schedule,captured,lookahead_hours=lookahead_hours)
    raw_map={int(g['gamePk']):g for day in schedule.get('dates',[]) for g in day.get('games',[]) if isinstance(g,dict) and g.get('gamePk') is not None}
    # Full slate is preserved; the feed-call budget does NOT truncate the slate.
    # Lineups are typically first posted close to kickoff, so only check those
    # within 4h and rotate every 10m. Weather checks may start 36h early.
    imminent=[g for g in candidates if g['lead_minutes']<=240]
    weather_eligible=[g for g in candidates if g['lead_minutes']<=2160]
    feed_ids=_rotating_budget(imminent,captured,feed_max_games)
    weather_ids=_rotating_budget(weather_eligible,captured,weather_max_games) if weather_enabled else set()
    existing_ids,recent_weather=_previous_capture_state(path,captured)
    master=None
    if weather_ids and master_path.exists():
        master=pd.read_csv(master_path,low_memory=False,usecols=['gamePk','officialDate','gameType','status','home_team','venue_id'])
    counter=Counter()
    added=0
    errors=0
    duplicated=0
    for candidate in candidates:
        pk=candidate['game_pk']
        freq=_capture_frequency_minutes(candidate['lead_minutes'])
        if _evidence_identifier(pk,captured,freq) in existing_ids:
            duplicated+=1
            continue
        observation_time=now or _now()
        lineups={'status':'LIVE_FEED_NOT_CHECKED_DUE_API_BUDGET'}
        if pk in feed_ids:
            try:
                feed=getter(f'{GAME_FEED_ROOT}/{pk}/feed/live')
                observation_time=now or _now()
                lineups=extract_official_pregame_lineups(feed,pk,observation_time,candidate['first_pitch_utc'])
            except Exception as exc:
                observation_time=now or _now()
                lineups={'status':'OFFICIAL_LIVE_FEED_UNAVAILABLE','source_error_type':type(exc).__name__}
                errors+=1
        if (observation_time>=_utc(candidate['first_pitch_utc'])
                or lineups.get('status') in {
                    'FEED_IS_NOT_PREGAME','CAPTURE_NOT_BEFORE_KICKOFF',
                    'FEED_GAME_ID_MISMATCH','FEED_KICKOFF_CHANGED_REVIEW_REQUIRED'
                }):
            # A stale schedule cannot authorize a pregame record after the
            # live game feed has identified a started/rescheduled fixture.
            counter['SKIPPED_STARTED_DURING_CAPTURE']+=1
            continue
        weather={'status':'WEATHER_NOT_CHECKED_DUE_API_BUDGET'} if weather_enabled else {'status':'NOT_CHECKED'}
        if weather_enabled and pk in weather_ids and master is not None:
            prior=recent_weather.get(pk)
            raw=raw_map.get(pk,{})
            weather=_forecast_from_nws(raw,master,observation_time,candidate['first_pitch_utc'],getter,
                    prior_weather=prior,observed_clock=(lambda:now) if now else _now)
            observation_time=now or _now()
            if observation_time>=_utc(candidate['first_pitch_utc']):
                counter['SKIPPED_STARTED_DURING_CAPTURE']+=1
                continue
        record=compose_evidence(candidate,observation_time,feed_lineups=lineups,weather=weather,capture_interval_minutes=freq)
        if append_snapshot_once(path,record):
            added+=1
            existing_ids.add(record['evidence_id'])
        counter[lineups.get('status','UNSPECIFIED')]+=1
        counter['WEATHER_'+weather.get('status','UNKNOWN')]+=1
    return {
        'schema':SCHEMA,
        'captured_at_utc':_iso(now or _now()),
        'source':'MLB_STATSAPI_SCHEDULE_AND_PREGAME_FEED;NOAA_NWS_HOURLY_FORECAST_OPTIONAL',
        'eligible_total_schedule':len(candidates),
        'games_eligible':len(candidates),
        'added':added,
        'errors':errors,
        'existing_time_slots_preserved':duplicated,
        'lineup_feed_api_limit':feed_max_games,
        'weather_api_limit_games':weather_max_games,
        'lineups':{k:v for k,v in counter.items() if not k.startswith('WEATHER_') and k!='SKIPPED_STARTED_DURING_CAPTURE'},
        'weather':{k.removeprefix('WEATHER_'):v for k,v in counter.items() if k.startswith('WEATHER_')},
        'started_during_capture':counter['SKIPPED_STARTED_DURING_CAPTURE'],
        'model_changed':False,
        'picks_written':False,
    }


def main():
    p=argparse.ArgumentParser(description='Append-only pregame sports-data capture; never betting recommendations')
    p.add_argument('--ledger',type=Path,default=LEDGER)
    p.add_argument('--lookahead-hours',type=int,default=48)
    p.add_argument('--no-weather',action='store_true')
    p.add_argument('--feed-max-games',type=int,default=4)
    p.add_argument('--weather-max-games',type=int,default=2)
    args=p.parse_args()
    result=capture_once(args.ledger,lookahead_hours=args.lookahead_hours,
                        weather_enabled=not args.no_weather,feed_max_games=args.feed_max_games,weather_max_games=args.weather_max_games)
    if args.ledger==LEDGER:
        SUMMARY.parent.mkdir(parents=True,exist_ok=True)
        # Derived summary may change, unlike the immutable evidence ledger.
        fd,temp=tempfile.mkstemp(dir=str(SUMMARY.parent),prefix='.pregame_summary_',suffix='.json')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump(result,f,indent=2);f.flush();os.fsync(f.fileno())
            os.replace(temp,SUMMARY)
        finally:
            if os.path.exists(temp):os.unlink(temp)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
