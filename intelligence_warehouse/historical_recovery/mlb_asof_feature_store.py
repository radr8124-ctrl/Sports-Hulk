"""Versioned MLB retrospective pregame-style player features with strict as-of data.

Past-game hitter stats are calculated from completed games strictly BEFORE a
target game's official date. Completed 2025 sprint+bat season metrics may be
linked to 2026 by MLBAM ID, never player names or future/same-year aggregate.
The target participant universe is known from a postgame boxscore, so this is
for HISTORICAL RESEARCH ONLY, not evidence a lineup was known before first pitch.
Labels are separate from features and no current betting model reads either.
"""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'reports/mlb_feature_integration_20261008'
SOURCE_BIOMECH=ROOT/'reports/mlb_statcast_recovery_20261008/biomechanics/MLB_2026_PRIOR_2025_BIOMECHANICS_VERIFIED_RESEARCH_ONLY.parquet'
SOURCE_GAME_HISTORY=ROOT/'intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_HISTORY.csv'
FEATURE_VERSION='MLB_RESEARCH_ASOF_PREVIOUS_GAMES_AND_PRIOR_SEASON_SPEED_20261008_V1'
FEATURE_SCOPE='RETROSPECTIVE_POSTGAME_PARTICIPANT_UNIVERSE_WITH_PRIOR_COMPLETED_GAME_FEATURES'
KEYS=['game_pk','player_id']


def sha_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def _unique_speed_prior(prior:pd.DataFrame,target_season:int)->pd.DataFrame:
    necessary={
        'player_id','prior_season_sprint_speed_ft_per_sec','prior_season_bat_speed_mph',
        'prior_season_sprint_qualified','prior_season_bat_qualified',
        'source_completed_season','feature_research_season','approved_for_live_model',
    }
    if missing:=necessary-set(prior.columns):
        raise ValueError(f'Missing required prior-year source fields: {sorted(missing)}')
    if prior.empty or prior.player_id.isna().any() or prior.player_id.duplicated().any():
        raise ValueError('Invalid or duplicate source player identity')
    if set(pd.to_numeric(prior.source_completed_season,errors='coerce'))!={target_season-1} or set(pd.to_numeric(prior.feature_research_season,errors='coerce'))!={target_season}:
        raise ValueError('Only immediately prior season speed can enter this retrospective model')
    if prior.approved_for_live_model.fillna(False).astype(bool).any():
        raise ValueError('Source cannot falsely be approved for live betting')
    if not pd.api.types.is_numeric_dtype(prior.player_id):
        raise ValueError('MLBAM player IDs must be numeric')
    q=prior.copy()
    q['prior_season_sprint_speed_ft_per_sec']=pd.to_numeric(q['prior_season_sprint_speed_ft_per_sec'],errors='coerce')
    q['prior_season_bat_speed_mph']=pd.to_numeric(q['prior_season_bat_speed_mph'],errors='coerce')
    sp=q['prior_season_sprint_speed_ft_per_sec']
    bat=q['prior_season_bat_speed_mph']
    if ((sp.notna())&(~sp.between(10,36))).any() or ((bat.notna())&(~bat.between(35,105))).any():
        raise ValueError('Implausible speed value requires source review')
    # Eligibility is an AND of source-measured value and source minimum sample.
    q['prior_sprint_speed_ft_per_sec']=sp.where(q.prior_season_sprint_qualified.fillna(False).astype(bool))
    q['prior_bat_speed_mph']=bat.where(q.prior_season_bat_qualified.fillna(False).astype(bool))
    return q[['player_id','prior_sprint_speed_ft_per_sec','prior_bat_speed_mph']].copy()


def attach_prior_completed_season_speed(events:pd.DataFrame,prior:pd.DataFrame,*,target_season:int=2026)->pd.DataFrame:
    if not {'game_pk','player_id','official_start'}.issubset(events.columns):
        raise ValueError('Each original fixture needs official game/player IDs and a kickoff time')
    if events.player_id.isna().any() or events.game_pk.isna().any():
        raise ValueError('Missing source game/player identity')
    if events.duplicated(KEYS).any():
        raise ValueError('Duplicate game/player IDs in feature candidate rows')
    utc=pd.to_datetime(events.official_start,errors='coerce',utc=True)
    if utc.isna().any() or not utc.dt.year.eq(target_season).all():
        raise ValueError('Only fixtures in the requested target season are permitted')
    prior_table=_unique_speed_prior(prior,target_season)
    # Entire source is a previously completed calendar year, but re-downloaded
    # in October 2026. Never claim the source original file existed pre-quote.
    out=events.copy()
    out['player_id']=pd.to_numeric(out.player_id,errors='raise').astype('int64')
    out=out.merge(prior_table,on='player_id',how='left',validate='many_to_one')
    out['sprint_speed_observed']=out.prior_sprint_speed_ft_per_sec.notna()
    out['bat_speed_observed']=out.prior_bat_speed_mph.notna()
    out['prior_completed_season']=target_season-1
    out['source_time_class']=FEATURE_SCOPE
    out['source_origin']='BASEBALL_SAVANT_RETROSPECTIVE_COMPLETE_PRIOR_SEASON_REDOWNLOAD_OCTOBER_2026'
    out['source_proven_at_time_of_original_quote']=False
    out['roster_selection_known_before_game']=False
    out['live_betting_approved']=False
    out['original_hulk_forward_predictions_claimed']=False
    out['usable_as_original_live_hulk_prediction']=False
    return out


def _safe_avg(rows:list[dict],column:str)->float:
    xs=[float(x[column]) for x in rows if x.get(column) is not None and pd.notna(x[column])]
    return round(float(sum(xs)/len(xs)),6) if xs else float('nan')


def build_official_hitter_game_features(history:pd.DataFrame,prior:pd.DataFrame,*,target_season:int=2026)->tuple[pd.DataFrame,pd.DataFrame]:
    required={'game_pk','player_id','official_date','game_date','season',
              'group','status','game_type','hits','walks','strikeouts',
              'total_bases','plate_appearances','stolen_bases'}
    if missing:=required-set(history.columns):
        raise ValueError(f'Official hitter source lacks columns: {sorted(missing)}')
    if not target_season or target_season<2016:
        raise ValueError('Supported historical seasons start 2016')
    official=history[(history.season==target_season)&
                     history.group.astype(str).eq('HITTING')&
                     history.game_type.astype(str).eq('R')&
                     history.status.astype(str).eq('Final')].copy()
    if official.empty:
        raise ValueError('No officially completed regular-season hitting games')
    if official[['game_pk','player_id','official_date','game_date']].isna().any().any():
        raise ValueError('Missing essential official source identity/date fields')
    if official.duplicated(KEYS).any():
        raise ValueError('Ambiguous duplicate official hitter game/player IDs')
    official['_date']=pd.to_datetime(official.official_date,errors='coerce').dt.date
    official['_time']=pd.to_datetime(official.game_date,errors='coerce',utc=True)
    if official._date.isna().any() or official._time.isna().any() or not official._date.map(lambda x:x.year==target_season).all():
        raise ValueError('Invalid official source year/timestamp')
    if not official._time.dt.year.eq(target_season).all():
        raise ValueError('Official kickoff season does not match documented game season')
    for key in ('hits','walks','strikeouts','total_bases','plate_appearances','stolen_bases'):
        official[key]=pd.to_numeric(official[key],errors='coerce')
    official=official.sort_values(['player_id','_date','game_pk']).reset_index(drop=True)
    feature_rows=[];label_rows=[]
    # Single chronological pass: 51k records don't require 51k separate
    # pandas group-by objects and per-game DataFrame.iterrows allocations.
    # Historical deque/list is flushed ONLY on the NEXT official date.
    current_pid=None
    current_day=None
    pending_today=[]
    prior_last10=[]
    complete_prior_count=0
    previous_day=None
    cached={}
    for r in official.to_dict('records'):
        pid=int(r['player_id'])
        day=r['_date']
        if current_pid is None or pid!=current_pid:
            current_pid=pid
            current_day=None
            pending_today=[]
            prior_last10=[]
            complete_prior_count=0
            previous_day=None
        if day!=current_day:
            if current_day is not None and pending_today:
                prior_last10=(prior_last10+pending_today)[-10:]
                complete_prior_count+=len(pending_today)
                previous_day=current_day
            pending_today=[]
            current_day=day
            prior5=prior_last10[-5:]
            cached={
                'feature_version':FEATURE_VERSION,
                'prior_games_count':complete_prior_count,
                'prior_last_date':str(previous_day) if previous_day else None,
                'prior_last5_hits_avg':_safe_avg(prior5,'hits'),
                'prior_last10_hits_avg':_safe_avg(prior_last10,'hits'),
                'prior_last5_walks_avg':_safe_avg(prior5,'walks'),
                'prior_last10_walks_avg':_safe_avg(prior_last10,'walks'),
                'prior_last5_strikeouts_avg':_safe_avg(prior5,'strikeouts'),
                'prior_last10_total_bases_avg':_safe_avg(prior_last10,'total_bases'),
                'prior_last5_plate_appearances_avg':_safe_avg(prior5,'plate_appearances'),
                'prior_last10_stolen_bases_avg':_safe_avg(prior_last10,'stolen_bases'),
                'prior_pregame_sample_floor_5_games_met':complete_prior_count>=5,
                'feature_rule':'STRICTLY_PRIOR_OFFICIAL_CALENDAR_DATES_ONLY',
                'source_time_class':FEATURE_SCOPE,
                'roster_selection_known_before_game':False,
                'source_proven_at_time_of_original_quote':False,
                'live_betting_approved':False,
                'original_hulk_forward_predictions_claimed':False,
            }
        if previous_day is not None and previous_day>=day:
            raise RuntimeError('Detected future/current source date leakage')
        feature_rows.append({
            'game_pk':int(r['game_pk']),
            'player_id':pid,
            'official_start':r['_time'].isoformat(),
            'official_date':str(day),
            **cached,
        })
        label_rows.append({
            'game_pk':int(r['game_pk']),
            'player_id':pid,
            'official_date':str(day),
            'realized_hits':float(r['hits']) if pd.notna(r['hits']) else float('nan'),
            'realized_walks':float(r['walks']) if pd.notna(r['walks']) else float('nan'),
            'realized_stolen_bases':float(r['stolen_bases']) if pd.notna(r['stolen_bases']) else float('nan'),
            'grade_is_official_analytic_only_not_sportsbook_settlement':True,
            'source':'MLB_STATSAPI_OFFICIAL_FINAL_PLAYER_BOXSCORE',
        })
        pending_today.append(r)
    raw_features=pd.DataFrame(feature_rows)
    raw_labels=pd.DataFrame(label_rows)
    merged=attach_prior_completed_season_speed(raw_features,prior,target_season=target_season)
    if len(merged)!=len(raw_features) or merged.duplicated(KEYS).any():
        raise RuntimeError('Prior-speed player join unexpectedly multiplied game identities')
    return (merged.sort_values(KEYS).reset_index(drop=True),
            raw_labels.sort_values(KEYS).reset_index(drop=True))


def write_replay_checked(output:Path,features:pd.DataFrame,labels:pd.DataFrame,source:Path,prior:Path)->dict:
    if not output.resolve().is_relative_to((ROOT/'reports').resolve()) or output.resolve() == (ROOT/'baseball_vault/derived').resolve():
        raise ValueError('Output restricted to private research report staging')
    output.mkdir(parents=True,exist_ok=True)
    source_sha=sha_file(source);prior_sha=sha_file(prior)
    filenames=[
        ('MLB_2026_ASOF_HITTER_RESEARCH_FEATURES.parquet',features),
        ('MLB_2026_HITTER_OFFICIAL_RESEARCH_LABELS.parquet',labels),
    ]
    written={}
    for name,frame in filenames:
        target=output/name
        if target.exists():
            saved=pd.read_parquet(target)
            pd.testing.assert_frame_equal(saved,frame,check_dtype=True)
        else:
            frame.to_parquet(target,index=False,compression='zstd')
        written[name]={'bytes':target.stat().st_size,'sha256':sha_file(target),'rows':len(frame)}
    info={
        'version':FEATURE_VERSION,
        'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'source_history_sha256':source_sha,
        'source_completed_2025_sprint_bat_season_sha256':prior_sha,
        'research_only':True,
        'source_time_class':FEATURE_SCOPE,
        'current_game_outcomes_excluded_from_feature_matrix':True,
        'same_day_games_excluded_from_prior_player_form':True,
        'source_season':2025,'target_season':2026,
        'features':written,
        'unique_mlb_game_ids':int(features.game_pk.nunique()),
        'unique_official_player_ids':int(features.player_id.nunique()),
        'sprint_eligible_player_game_rows':int(features.sprint_speed_observed.sum()),
        'bat_eligible_player_game_rows':int(features.bat_speed_observed.sum()),
        'both_speed_eligible_player_game_rows':int((features.sprint_speed_observed & features.bat_speed_observed).sum()),
        'original_quote_capture_time_proven':False,
        'participant_universe_selection_is_postgame':True,
        'automatic_live_model_ingestion':False,
        'source_rights_require_separate_review':True,
        'no_artificial_betting_history_added':True,
    }
    m=output/'MLB_ASOF_FEATURE_STORE_MANIFEST.json'
    if m.exists():
        old=json.loads(m.read_text())
        comparable={k:v for k,v in old.items() if k!='created_at_utc'}
        new={k:v for k,v in info.items() if k!='created_at_utc'}
        if comparable!=new:raise ValueError('Versioned as-of store manifest changed; refuse overwrite')
        return old
    m.write_text(json.dumps(info,indent=2,sort_keys=True)+'\n')
    return info


def main():
    ap=argparse.ArgumentParser(description='2026 retrospective MLB hit form + prior-year true speed research store')
    ap.add_argument('--output-dir',type=Path,default=OUTPUT)
    args=ap.parse_args()
    if args.output_dir.resolve()!=OUTPUT.resolve():
        raise SystemExit('Refusing output outside approved research directory')
    source=SOURCE_GAME_HISTORY
    prior=SOURCE_BIOMECH
    columns=[
        'game_pk','player_id','official_date','game_date','season','group','status',
        'game_type','hits','walks','strikeouts','total_bases',
        'plate_appearances','stolen_bases',
    ]
    h=pd.read_csv(source,usecols=columns,low_memory=False)
    sp=pd.read_parquet(prior)
    features,labels=build_official_hitter_game_features(h,sp,target_season=2026)
    report=write_replay_checked(args.output_dir,features,labels,source,prior)
    print('MLB_VERSIONED_ASOF_RESEARCH_FEATURES',json.dumps({
        k:report[k] for k in ('unique_mlb_game_ids','unique_official_player_ids','sprint_eligible_player_game_rows','bat_eligible_player_game_rows','both_speed_eligible_player_game_rows','source_time_class','automatic_live_model_ingestion')
    },sort_keys=True))


if __name__=='__main__':main()
