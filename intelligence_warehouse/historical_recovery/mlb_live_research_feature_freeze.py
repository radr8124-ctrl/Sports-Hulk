"""Freeze MLB observed lineup+prior-only form/speed as genuine *future* evidence.

This observes an authenticated append-only first-pitch-before MLB source
capture, then computes pregame features BEFORE the scheduled first pitch.
Only known official current *lineup IDs* enter this lane, unlike the
retrospective past-game participant universe. No betting odds, probabilities,
recommender, authorizations or historical pick history are changed.
"""
from __future__ import annotations

import argparse
from datetime import datetime,timezone,timedelta
import fcntl
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from .mlb_asof_feature_store import (
    ROOT,SOURCE_BIOMECH,SOURCE_GAME_HISTORY,_unique_speed_prior,sha_file,
)

SOURCE=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_PREGAME_SOURCE_EVIDENCE.jsonl'
OUTPUT=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_RESEARCH_ASOF_FEATURE_FREEZE.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_RESEARCH_FEATURE_FREEZE_SUMMARY.json'
SCHEMA='MLB_TRUE_PREGAME_RESEARCH_FEATURE_FREEZE_V1'
MAX_SOURCE_CAPTURE_AGE_MINUTES=20
HISTORY_LAG_HOURS=12
HISTORY_FIELDS=[
    'game_pk','player_id','official_date','game_date','season',
    'group','game_type','status','hits','walks','plate_appearances','stolen_bases',
]
OFFICIAL_LINEUP_SOURCE='LIVE_FEED_OFFICIAL_BATTING_ORDER_CAPTURED_PREGAME'
OFFICIAL_LINEUP_STATUSES={
    'OFFICIAL_BATTING_ORDER_VISIBLE_BEFORE_KICKOFF',
    'ONLY_ONE_TEAM_LINEUP_VISIBLE_PREGAME',
}


def _utc(value)->pd.Timestamp:
    result=pd.to_datetime(value,utc=True,errors='coerce')
    if pd.isna(result):
        raise ValueError('Invalid observed source timestamp')
    return result


def _iso(value)->str:
    return _utc(value).isoformat(timespec='seconds')


def _prior_stat_avg(rows:pd.DataFrame,col:str)->float|None:
    if rows.empty or col not in rows:return None
    v=pd.to_numeric(rows[col],errors='coerce').dropna()
    return round(float(v.mean()),6) if len(v) else None


def _verified_weather(weather:dict,source_at:pd.Timestamp)->dict:
    out={
        'forecast_source_status':'UNVERIFIED_ASOF_NOT_USED',
        'forecast_temperature_f':None,
        'forecast_wind_mph':None,
        'forecast_precipitation_probability_pct':None,
        'actual_weather_at_first_pitch_verified':False,
        'stadium_roof_open_closed_verified_asof':False,
    }
    if weather.get('status')!='CAPTURED_NWS_FORECAST_NOT_OBSERVED_WEATHER':
        return out
    try:
        issued=_utc(weather.get('forecast_generated_at_utc'))
        observed=_utc(weather.get('source_captured_at_utc'))
    except ValueError:
        return out
    if issued>observed or observed>source_at:
        return out
    temp=weather.get('forecast_temperature_f')
    wind=weather.get('forecast_wind_mph')
    precip=weather.get('forecast_precipitation_probability_pct')
    try:
        temperature=float(temp) if temp is not None else None
        windspeed=float(wind) if wind is not None else None
        precipval=float(precip) if precip is not None else None
    except (TypeError,ValueError):
        return out
    if temperature is not None and not -50<=temperature<=135:return out
    if windspeed is not None and not 0<=windspeed<=200:return out
    if precipval is not None and not 0<=precipval<=100:return out
    out.update({
        'forecast_source_status':'SOURCE_OBSERVED_BEFORE_LINEUP_FREEZE_FORECAST_ONLY',
        'forecast_temperature_f':temperature,
        'forecast_wind_mph':windspeed,
        'forecast_precipitation_probability_pct':precipval,
        'nws_forecast_source_observed_at_utc':_iso(observed),
        'nws_forecast_generated_at_utc':_iso(issued),
    })
    return out


def make_live_features(source:dict,history:pd.DataFrame,completed_year:pd.DataFrame,*,now:datetime,allow_verified_postseason_prior:bool=False)->list[dict]:
    if now.tzinfo is None:
        raise ValueError('Now must be a truthful offset-aware UTC observation clock')
    observed=_utc(now)
    try:
        when=_utc(source.get('captured_at_utc'))
        start=_utc(source.get('first_pitch_utc'))
    except ValueError:
        return []
    if (
        source.get('schema')!='MLB_PREGAME_SOURCE_EVIDENCE_V1'
        or not source.get('evidence_id') or not source.get('game_pk')
        or when>=start or observed>=start
        or when>observed or observed-when>pd.Timedelta(minutes=MAX_SOURCE_CAPTURE_AGE_MINUTES)
    ):
        return []
    fixture=source.get('fixture') or {}
    if str(fixture.get('official_status_at_capture','')).upper() not in ('SCHEDULED','PRE-GAME','PRE-GAME WARMUP','WARMUP'):
        return []
    lineup=source.get('lineups') or {}
    if lineup.get('status') not in OFFICIAL_LINEUP_STATUSES:
        return []
    target_season=when.year
    # This source currently has 2025 completed-year leaderboards, only valid
    # for explicitly selected 2026 source comparisons. For 2027 fail closed.
    prior=_unique_speed_prior(completed_year,target_season)
    table={int(r.player_id):r for _,r in prior.iterrows()}
    if not all(col in history.columns for col in HISTORY_FIELDS):
        raise ValueError('Official player-history source missing required independent data fields')
    # The original V1 ledger used only regular-season histories. V2 may
    # include OFFICIALLY VERIFIED completed playoff game rows, but only when
    # every source carries its independent master-crosscheck flag.
    if allow_verified_postseason_prior:
        if not {'source_verified_before_quote_required','source_history_origin'}.issubset(history.columns):
            raise ValueError('Postseason source verification and origin metadata missing')
        candidate=history[
            history.season.eq(target_season)
            & history.group.eq('HITTING')
            & history.game_type.isin(['R','D','F','L','W'])
            & history.status.eq('Final')
        ]
        if candidate['source_verified_before_quote_required'].ne(True).any():
            raise ValueError('Postseason source verification flag absent or false')
        if candidate.source_history_origin.isna().any() or not candidate.source_history_origin.isin([
            'LEGACY_OFFICIAL_FINAL_BOXSCORE',
            'INCREMENTAL_OFFICIAL_FINAL_POSTSEASON_CROSSCHECKED_WITH_GAME_MASTER',
        ]).all():
            raise ValueError('Postseason source verification origin invalid')
        valid=candidate.copy()
    else:
        valid=history[
            history.season.eq(target_season)
            & history.group.eq('HITTING')
            & history.game_type.eq('R')
            & history.status.eq('Final')
        ].copy()
    valid['_official_date']=pd.to_datetime(valid.official_date,errors='coerce').dt.date
    valid['_game_start']=pd.to_datetime(valid.game_date,errors='coerce',utc=True)
    # Crucial: "prior" means known BEFORE THE SOURCE SNAPSHOT, not merely
    # known before the scheduled first pitch (quotes can be hours earlier).
    valid=valid[
        valid._official_date.lt(when.date())
        & valid._game_start.le(when-pd.Timedelta(hours=HISTORY_LAG_HOURS))
    ].copy()
    indexed={int(pid):part.sort_values(['_game_start','game_pk'])
             for pid,part in valid.groupby('player_id',sort=False)}
    weather=_verified_weather(source.get('weather') or {},when)
    probable=source.get('probable_pitchers') or {}
    out=[]
    for side in ('home','away'):
        players=lineup.get(side)
        if not isinstance(players,dict):
            continue
        ids=players.get('player_ids') or []
        if (
            len(ids)!=9 or len(set(str(x) for x in ids))!=9
            or players.get('confirmed_asof_capture') is not True
            or players.get('source')!=OFFICIAL_LINEUP_SOURCE
        ):
            return []
        for raw_id in ids:
            try:
                pid=int(raw_id)
                if pid<=0:return []
            except (TypeError,ValueError):
                return []
            prior_games=indexed.get(pid)
            if prior_games is None:
                prior_games=pd.DataFrame(columns=valid.columns)
            latest=prior_games.tail(10)
            latest5=latest.tail(5)
            last_day=str(latest.iloc[-1]['_official_date']) if len(latest) else None
            if last_day is not None and last_day>=str(when.date()):
                raise RuntimeError('Detected source-time cheating: historical result from quote day')
            sp=table.get(pid)
            speed=float(sp['prior_sprint_speed_ft_per_sec']) if sp is not None and pd.notna(sp['prior_sprint_speed_ft_per_sec']) else None
            bat=float(sp['prior_bat_speed_mph']) if sp is not None and pd.notna(sp['prior_bat_speed_mph']) else None
            opponent_side='away' if side=='home' else 'home'
            p_status=(probable.get('probable_status')=='OFFICIAL_SCHEDULE_PROBABLE_NOT_CONFIRMED')
            row={
                'schema':SCHEMA,
                'game_pk':int(source['game_pk']),
                'player_id':pid,
                'team_side_at_capture':side,
                'lineup_source_status':'OFFICIAL_BATTING_ORDER_CAPTURED_BEFORE_FIRST_PITCH',
                'source_evidence_id':source['evidence_id'],
                'source_capture_at_utc':_iso(when),
                'feature_frozen_at_utc':_iso(observed),
                'scheduled_first_pitch_utc':_iso(start),
                'frozen_before_scheduled_first_pitch':True,
                'first_observed_lineup_policy':'ONE_INITIAL_FROZEN_FEATURE_PER_GAME_AND_PLAYER_ID',
                'source_game_type':fixture.get('official_game_type'),
                'source_feature_year':target_season,
                'completed_season_biomechanics_year':target_season-1,
                'source_prior_history_first_eligible_before_day':str(when.date()),
                'prior_games_available':int(len(prior_games)),
                'prior_last5_hits_avg':_prior_stat_avg(latest5,'hits'),
                'prior_last5_walks_avg':_prior_stat_avg(latest5,'walks'),
                'prior_last5_pa_avg':_prior_stat_avg(latest5,'plate_appearances'),
                'prior_last10_stolen_bases_avg':_prior_stat_avg(latest,'stolen_bases'),
                'last_prior_date':last_day,
                'prior_history_at_least_5_completed_games':len(prior_games)>=5,
                'prior_sprint_speed_ft_per_sec':speed,
                'prior_bat_speed_mph':bat,
                'prior_speed_observed':speed is not None,
                'prior_bat_observed':bat is not None,
                'opposing_probable_pitcher_id':(
                    probable.get(f'{opponent_side}_probable_pitcher_id') if p_status else None
                ),
                'opposing_pitcher_confirmation_status':'PROBABLE_NOT_CONFIRMED' if p_status else 'NOT_VERIFIED',
                'starter_confirmed':False,
                'source_provenance_class':'OFFICIAL_PREGAME_LINEUP_PLUS_PRIOR_COMPLETED_STATS_ASOF',
                'confirmed_current_team_via_pregame_lineup_not_boxscore':True,
                'original_lineup_source_observed_before_first_pitch':True,
                'sportsbook_quote_time_or_price_not_observed':True,
                'source_biomechanics_retrieved_prior_to_game_oct_2026':True,
                'actual_game_outcome_in_features':False,
                'market_odds_or_vig_verified':False,
                'betting_prediction_written':False,
                'live_play_approved':False,
                **weather,
            }
            out.append(row)
    return sorted(out,key=lambda r:(r['game_pk'],r['player_id']))


def append_first_observation_once(path:Path,records:list[dict])->int:
    if not records:
        return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    lock=path.with_suffix(path.suffix+'.lock')
    with lock.open('a+b') as fd:
        fcntl.flock(fd,fcntl.LOCK_EX)
        existing=set()
        if path.exists():
            with path.open('r',encoding='utf-8') as f:
                for line in f:
                    if not line.strip():continue
                    try:
                        row=json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError('Corrupted evidence; do not append to a damaged forward freeze ledger') from exc
                    existing.add((int(row['game_pk']),int(row['player_id'])))
        new=[]
        for r in records:
            key=(int(r['game_pk']),int(r['player_id']))
            if (
                r.get('schema')!=SCHEMA or
                _utc(r['source_capture_at_utc'])>_utc(r['feature_frozen_at_utc']) or
                _utc(r['feature_frozen_at_utc'])>=_utc(r['scheduled_first_pitch_utc']) or
                r.get('live_play_approved') or r.get('betting_prediction_written')
            ):
                raise ValueError('Invalid or postgame frozen source candidate')
            if key not in existing:
                new.append(r)
                existing.add(key)
        if new:
            with path.open('a',encoding='utf-8') as f:
                for r in new:
                    f.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
                f.flush();os.fsync(f.fileno())
        return len(new)


def _load_recent_immutable_evidence(file:Path,now:datetime)->list[dict]:
    if not file.is_file():
        raise ValueError('Source ledger missing. No authentic pregame lineup evidence')
    selected=[]
    with file.open('r',encoding='utf-8') as f:
        for line in f:
            if not line.strip():continue
            data=json.loads(line)
            try:
                captured=_utc(data.get('captured_at_utc'))
                start=_utc(data.get('first_pitch_utc'))
            except ValueError:continue
            if (
                data.get('lineups',{}).get('status') in OFFICIAL_LINEUP_STATUSES
                and captured<=_utc(now)<start
                and _utc(now)-captured <= pd.Timedelta(minutes=MAX_SOURCE_CAPTURE_AGE_MINUTES)
            ):
                data['_source_immutable_line_sha256']=hashlib.sha256(line.encode()).hexdigest()
                selected.append(data)
    # A newer verified lineup supersedes an older partial lineup when
    # choosing which *new players* to freeze; previously frozen rows never
    # disappear or change.
    by_game={}
    for r in selected:
        key=int(r['game_pk'])
        if key not in by_game or _utc(r['captured_at_utc'])>_utc(by_game[key]['captured_at_utc']):
            by_game[key]=r
    return sorted(by_game.values(),key=lambda r:(r['first_pitch_utc'],r['game_pk']))


def _recorded_game_player_keys(path:Path)->tuple[set[tuple[int,int]],set[int]]:
    """Lightweight ledger index; fail closed instead of tolerating corruption."""
    keys=set()
    games=set()
    if not path.exists():
        return keys,games
    with path.open('r',encoding='utf-8') as f:
        for line in f:
            if not line.strip():continue
            row=json.loads(line)
            if row.get('schema')!=SCHEMA:
                raise ValueError('Unrecognized frozen feature ledger; no unsafe append')
            key=(int(row['game_pk']),int(row['player_id']))
            if key in keys:
                raise ValueError('Duplicate frozen game/player in append-only source')
            keys.add(key)
            games.add(key[0])
    return keys,games


def freeze_cycle(ledger:Path=SOURCE,output:Path=OUTPUT,*,now:datetime|None=None,
                 history_file:Path=SOURCE_GAME_HISTORY,prior_file:Path=SOURCE_BIOMECH)->dict:
    observed=now or datetime.now(timezone.utc)
    if observed.tzinfo is None:
        raise ValueError('Current clock must be timezone aware')
    candidates=_load_recent_immutable_evidence(ledger,observed)
    already_known,previous_games=_recorded_game_player_keys(output)
    # Critical performance guard: the 85MB official player-history file must
    # never be parsed every ten minutes for already-frozen teams/players.
    # A later newly published opposing lineup still triggers a bounded build.
    unseen=[]
    already_frozen=0
    for evidence in candidates:
        possible=set()
        lineups=evidence.get('lineups') or {}
        for side in ('home','away'):
            roster=(lineups.get(side) or {}).get('player_ids') or []
            if isinstance(roster,list):
                for raw in roster:
                    try:possible.add((int(evidence['game_pk']),int(raw)))
                    except (ValueError,TypeError):continue
        already_frozen+=len(possible.intersection(already_known))
        if possible-already_known:
            unseen.append(evidence)
    added=0
    seen_source=[]
    if unseen:
        source=pd.read_csv(history_file,usecols=HISTORY_FIELDS,low_memory=False)
        prior=pd.read_parquet(prior_file)
        history_digest=sha_file(history_file)
        prior_digest=sha_file(prior_file)
        for evidence in unseen:
            if not _utc(observed)<_utc(evidence['first_pitch_utc']):
                continue
            records=make_live_features(evidence,source,prior,now=observed)
            # Source plaintext digest always refers to the exact captured
            # append-only JSONL row, NOT a later derived model prediction.
            for entry in records:
                entry['original_append_only_line_sha256']=evidence['_source_immutable_line_sha256']
                entry['official_history_source_sha256']=history_digest
                entry['prior_completed_2025_biomechanics_source_sha256']=prior_digest
            new=append_first_observation_once(output,records)
            added+=new
            seen_source.append({'game_pk':evidence['game_pk'],'captured_at':evidence['captured_at_utc'],
                                'source_evidence_id':evidence['evidence_id'],
                                'new_players':new,'eligible_lineup_player_ids':len(records)})
    # Reconcile the end-state after an attempted append. The empty/duplicate
    # path requires zero large CSV loads and zero sportsbook/model touches.
    recorded,games=_recorded_game_player_keys(output)
    total=len(recorded)
    return {
        'schema':SCHEMA,
        'ran_at_utc':_iso(observed),
        'source':'EXISTING_OFFICIAL_MLB_PREGAME_CAPTURE_APPEND_ONLY',
        'eligible_recent_official_pregame_lineup_games':len(candidates),
        'fresh_frozen_lineup_player_observations_added':added,
        'existing_player_ids_already_frozen':already_frozen,
        'eligible_snapshots_with_new_player_ids':len(unseen),
        'expensive_history_read_performed':bool(unseen),
        'total_frozen_player_observations':total,
        'independent_upcoming_game_ids_seen':len(games),
        'recent_fixture_processing':seen_source,
        'source_labels_added_to_betting_forward_ledger':0,
        'live_betting_model_changed':False,
        'automatic_bet_prediction_approved':False,
        'archive_offsite_status':'VPS_LOCAL_ONLY',
    }


def main():
    parser=argparse.ArgumentParser(description='Research-only live pregame MLB hitter/speed context freeze')
    parser.add_argument('--source-ledger',type=Path,default=SOURCE)
    parser.add_argument('--output-ledger',type=Path,default=OUTPUT)
    args=parser.parse_args()
    if args.source_ledger.resolve()!=SOURCE.resolve() or args.output_ledger.resolve()!=OUTPUT.resolve():
        raise SystemExit('Refusing alternate unproven sources or output paths for scheduled future source')
    info=freeze_cycle(args.source_ledger,args.output_ledger)
    if not SUMMARY.exists():
        SUMMARY.write_text(json.dumps(info,indent=2)+'\n')
    else:
        # Operational summary is not a frozen wager or source; safe to update
        # independently of immutable source/feature ledgers.
        temporary=SUMMARY.with_suffix('.tmp')
        temporary.write_text(json.dumps(info,indent=2)+'\n')
        os.replace(temporary,SUMMARY)
    print('MLB_PREQUOTE_LIVE_RESEARCH_FEATURE_CAPTURE',json.dumps(info,sort_keys=True))


if __name__=='__main__':
    main()
