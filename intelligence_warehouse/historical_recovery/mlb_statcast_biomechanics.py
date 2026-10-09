"""Historical MLB measured player sprint speed & tracked bat swing speed.

Retrieve *completed* seasonal Baseball Savant public CSV leaderboards only,
save raw response plus normalized analytic attributes, and strictly prohibit
using same-season/future full-season leaderboards as earlier pregame features.
No commercial source rights or original source-time 2025 bytes are certified.
"""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
from pathlib import Path
import gzip
import hashlib
import io
import json
import os
import time

import pandas as pd
import requests

from .mlb_statcast_quarantine import ROOT,sha256
SOURCE_ROOT=ROOT/'reports/mlb_statcast_recovery_20261008/biomechanics'
ALLOWED_SPRINT_SEASONS=tuple(range(2016,2026))
ALLOWED_BAT_SEASONS=(2024,2025)
BASE='https://baseballsavant.mlb.com/leaderboard'
HISTORICAL_HARD_CAP=2_000_000


def eligible_prior_season(game_date:str,source_season:int)->bool:
    # Chronological candidate eligibility only, not original quote-time proof.
    try:return pd.Timestamp(game_date).year>int(source_season)
    except (ValueError,TypeError,OverflowError):return False


def validate_leaderboard_csv(raw:bytes,kind:str,season:int)->tuple[pd.DataFrame,dict]:
    if kind not in ('sprint_speed','bat_speed'):
        raise ValueError('Unsupported MLB biomechanics measurement')
    years=ALLOWED_SPRINT_SEASONS if kind=='sprint_speed' else ALLOWED_BAT_SEASONS
    if season not in years:
        raise ValueError('Historical season not in bounded source windows')
    if not raw or len(raw)>HISTORICAL_HARD_CAP or b'<html' in raw[:400].lower():
        raise ValueError('Source is not a valid CSV leaderboard')
    try:
        df=pd.read_csv(io.BytesIO(raw),encoding='utf-8-sig',low_memory=False)
    except Exception as exc:
        raise ValueError('Source is not a valid CSV leaderboard') from exc
    required=({'player_id','sprint_speed','competitive_runs'}
              if kind=='sprint_speed'
              else {'id','avg_bat_speed','swings_competitive'})
    missing=required-set(df.columns)
    if missing or df.empty:
        raise ValueError(f'Incomplete CSV leaderboard source: {sorted(missing)}, rows={len(df)}')
    if kind=='sprint_speed':
        ids=pd.to_numeric(df.player_id,errors='coerce')
        metric=pd.to_numeric(df.sprint_speed,errors='coerce')
        n=pd.to_numeric(df.competitive_runs,errors='coerce')
        min_valid,max_valid=10,36
    else:
        ids=pd.to_numeric(df.id,errors='coerce')
        metric=pd.to_numeric(df.avg_bat_speed,errors='coerce')
        n=pd.to_numeric(df.swings_competitive,errors='coerce')
        min_valid,max_valid=35,105
    if ids.isna().any() or (ids<=0).any() or ids.duplicated().any():
        raise ValueError('Source player identifiers missing, invalid or duplicated')
    if n.isna().any() or (n<0).any():
        raise ValueError('Source opportunity counts are missing or invalid')
    if ((metric.notna()) & ((metric<min_valid)|(metric>max_valid))).any():
        raise ValueError('Source biomechanics value implausible for declared units')
    out=df.copy()
    if kind=='bat_speed':
        out=out.rename(columns={'id':'player_id'})
    out['profile_season']=season
    out['feature_first_eligible_season']=season+1
    out['qualifies_minimum_opportunities']=(n >= (10 if kind=='sprint_speed' else 100)) & metric.notna()
    out['measurement_kind']=kind
    out['research_only']=True
    proof={
        'kind':kind,
        'season':season,
        'rows':len(out),
        'distinct_player_ids':int(ids.nunique()),
        'source_csv_sha256':sha256(raw),
        'source_csv_bytes':len(raw),
        'numeric_measurement_count':int(metric.notna().sum()),
        'minimum_opportunity_qualifying_players':int(out.qualifies_minimum_opportunities.sum()),
        'measurement_unit':'feet_per_second' if kind=='sprint_speed' else 'miles_per_hour',
        'first_feature_eligible_season':season+1,
        'source_name':'MLB_BASEBALL_SAVANT_STATCAST_SEASON_LEADERBOARD',
        'source_is_currently_retrieved_not_original_year_end_snapshot':True,
        'not_asof_eligible_within_same_season':True,
        'model_use_approved':False,
        'data_rights':'REVIEW_UPSTREAM_COMMERCIAL_REDISTRIBUTION_BEFORE_PUBLIC_PRODUCT_USE',
    }
    return out,proof


def leaderboard_spec(kind:str,season:int)->tuple[str,dict]:
    if kind=='sprint_speed' and season in ALLOWED_SPRINT_SEASONS:
        return f'{BASE}/sprint_speed',{
            'min_season':season,'max_season':season,
            'min':0,'position':'','team':'','csv':'true',
        }
    if kind=='bat_speed' and season in ALLOWED_BAT_SEASONS:
        return f'{BASE}/bat-tracking',{'seasonStart':season,'seasonEnd':season,'csv':'true'}
    raise ValueError('Invalid public leaderboard query/window')


def fetch_source(kind:str,season:int)->tuple[bytes,dict]:
    url,params=leaderboard_spec(kind,season)
    start=time.monotonic()
    with requests.get(url,params=params,
        timeout=(7,18),stream=True,
        headers={'User-Agent':'Sports-HULK-Baseball/1.1','Accept':'text/csv'}) as response:
        response.raise_for_status()
        raw=bytearray()
        for chunk in response.iter_content(chunk_size=128*1024):
            raw.extend(chunk)
            if len(raw)>HISTORICAL_HARD_CAP:
                raise ValueError('Leaderboards exceeding 2MB cap require manual review')
        meta={
            'http_status':response.status_code,
            'content_type':response.headers.get('Content-Type'),
            'source_url':url,
            'query_params':params,
            'source_http_elapsed_seconds':round(time.monotonic()-start,3),
            'actual_download_time_utc':datetime.now(timezone.utc).isoformat(),
        }
        return bytes(raw),meta


def save_leaderboard(folder:Path,kind:str,season:int,raw:bytes,df:pd.DataFrame,proof:dict,transport:dict)->dict:
    if folder.resolve()!=SOURCE_ROOT.resolve():
        raise ValueError('Refusing output outside canonical private historical research folder')
    folder.mkdir(parents=True,exist_ok=True)
    stem=(f'bat_speed_verified_{season}' if kind=='bat_speed' else f'{kind}_{season}')
    src=folder/f'{stem}.csv.gz'
    normalized=folder/f'{stem}_normalized.parquet'
    receipt=folder/f'{stem}_receipt.json'
    if receipt.exists():
        old=json.loads(receipt.read_text())
        if old['source_csv_sha256']!=sha256(raw):
            raise ValueError('Existing source bytes immutable; provider content changed')
        assert_leaderboard_receipt(folder,old)
        return old
    if src.exists() or normalized.exists():
        raise ValueError('Unreconciled partial source files already exist')
    packed=gzip.compress(raw,compresslevel=6,mtime=0)
    # pandas Parquet is staged under an ordinary file then hashed/verified.
    with src.open('xb') as f:
        f.write(packed);f.flush();os.fsync(f.fileno())
    df.to_parquet(normalized,index=False,compression='zstd')
    record={**proof,'transport':transport,
        'source_file':src.name,
        'compressed_source_sha256':sha256(src.read_bytes()),
        'normalized_parquet_file':normalized.name,
        'normalized_parquet_sha256':sha256(normalized.read_bytes()),
        'source_filename':stem,
        'not_original_season_capture':True,
    }
    with receipt.open('x') as f:
        json.dump(record,f,indent=2,sort_keys=True)
        f.write('\n');f.flush();os.fsync(f.fileno())
    assert_leaderboard_receipt(folder,record)
    return record


def assert_leaderboard_receipt(folder:Path,receipt:dict):
    s=folder/receipt['source_file']
    p=folder/receipt['normalized_parquet_file']
    if not s.is_file() or sha256(s.read_bytes())!=receipt['compressed_source_sha256']:
        raise ValueError('SHA256 mismatch of raw biomechanics source')
    if not p.is_file() or sha256(p.read_bytes())!=receipt['normalized_parquet_sha256']:
        raise ValueError('SHA256 mismatch of reencoded biomechanics leaderboard')
    if sha256(gzip.decompress(s.read_bytes()))!=receipt['source_csv_sha256']:
        raise ValueError('SHA256 source raw response differs from receipt')


def join_prior_season_biomechanics(sprint:pd.DataFrame,bat:pd.DataFrame,*,target_season:int)->pd.DataFrame:
    prior_year=int(target_season)-1
    for frame in (sprint,bat):
        if frame.empty or set(frame.profile_season)!={prior_year}:
            raise ValueError('Only the completed immediately prior season may be used for research features')
        if (frame.feature_first_eligible_season>target_season).any():
            raise ValueError('Future season cannot be pregame research input')
        if frame.player_id.duplicated().any():
            raise ValueError('Ambiguous duplicate player ID: no one-to-many future result joins')
    sprint_view=sprint[['player_id','sprint_speed','qualifies_minimum_opportunities']].copy()
    sprint_view['sprint_speed']=sprint_view.sprint_speed.where(sprint_view.qualifies_minimum_opportunities)
    sprint_view=sprint_view.rename(columns={
        'sprint_speed':'prior_season_sprint_speed_ft_per_sec',
        'qualifies_minimum_opportunities':'prior_season_sprint_qualified'})
    bat_view=bat[['player_id','avg_bat_speed','qualifies_minimum_opportunities']].copy()
    bat_view['avg_bat_speed']=bat_view.avg_bat_speed.where(bat_view.qualifies_minimum_opportunities)
    bat_view=bat_view.rename(columns={
        'avg_bat_speed':'prior_season_bat_speed_mph',
        'qualifies_minimum_opportunities':'prior_season_bat_qualified'})
    joined=sprint_view.merge(bat_view,on='player_id',how='outer',validate='one_to_one')
    joined['source_completed_season']=prior_year
    joined['feature_research_season']=target_season
    joined['data_source']='BASEBALL_SAVANT_RETROSPECTIVE_PRIOR_FULL_SEASON_NOT_FROZEN_PRE_QUOTE'
    joined['approved_for_live_model']=False
    return joined.sort_values('player_id').reset_index(drop=True)


def main():
    parser=argparse.ArgumentParser(description='Bounded, measured MLB sprint and bat speed season recovery')
    parser.add_argument('--output-dir',type=Path,default=SOURCE_ROOT)
    args=parser.parse_args()
    if args.output_dir.resolve()!=SOURCE_ROOT.resolve():
        raise SystemExit('Refusing recovery outside dedicated protected research path')
    data={}
    receipts=[]
    for kind,seasons in [('sprint_speed',ALLOWED_SPRINT_SEASONS),('bat_speed',ALLOWED_BAT_SEASONS)]:
        for season in seasons:
            stem=(f'bat_speed_verified_{season}' if kind=='bat_speed' else f'{kind}_{season}')
            target=args.output_dir/f'{stem}_receipt.json'
            if target.exists():
                record=json.loads(target.read_text())
                assert_leaderboard_receipt(args.output_dir,record)
                tab=pd.read_parquet(args.output_dir/record['normalized_parquet_file'])
                print('REUSED_IMMUTABLE_SOURCE',kind,season,'records',len(tab),flush=True)
            else:
                raw,meta=fetch_source(kind,season)
                tab,proof=validate_leaderboard_csv(raw,kind,season)
                record=save_leaderboard(args.output_dir,kind,season,raw,tab,proof,meta)
                print('RECOVERED_VERIFIED_SEASON',kind,season,'records',len(tab),
                      'qualified',record['minimum_opportunity_qualifying_players'],
                      'sha256',record['source_csv_sha256'][:17],flush=True)
            data[(kind,season)]=tab
            receipts.append(record)
            time.sleep(0.15)
    # The endpoint silently ignores year=YYYY. Reject all falsely dated bat
    # responses and never merge identical 2024 and 2025 raw source copies.
    bat2024=next(x for x in receipts if x['kind']=='bat_speed' and x['season']==2024)
    bat2025=next(x for x in receipts if x['kind']=='bat_speed' and x['season']==2025)
    if bat2024['source_csv_sha256']==bat2025['source_csv_sha256']:
        raise ValueError('BAT_TRACKING_SEASON_NOT_VERIFIED: 2024/2025 payloads are identical')
    if any(r['transport']['query_params'].get('seasonStart')!=r['season']
           or r['transport']['query_params'].get('seasonEnd')!=r['season']
           for r in receipts if r['kind']=='bat_speed'):
        raise ValueError('BAT_TRACKING_SEASON_NOT_VERIFIED: source filter not applied')
    # Research inputs only: completed 2025 values as candidate features in 2026.
    join=join_prior_season_biomechanics(data[('sprint_speed',2025)],data[('bat_speed',2025)],target_season=2026)
    joined=args.output_dir/'MLB_2026_PRIOR_2025_BIOMECHANICS_VERIFIED_RESEARCH_ONLY.parquet'
    if joined.exists():
        prev=pd.read_parquet(joined)
        if not prev.equals(join):
            raise ValueError('Existing 2026 prior-season feature staging is immutable')
    else:
        join.to_parquet(joined,index=False,compression='zstd')
    summary={
        'source_years_sprint_speed':list(ALLOWED_SPRINT_SEASONS),
        'source_years_bat_speed':list(ALLOWED_BAT_SEASONS),
        'sprint_season_row_total':sum(len(data[('sprint_speed',s)]) for s in ALLOWED_SPRINT_SEASONS),
        'bat_tracking_row_total':sum(len(data[('bat_speed',s)]) for s in ALLOWED_BAT_SEASONS),
        '2026_prior_season_2025_candidate_unique_player_ids':len(join),
        '2026_prior_2025_qualified_sprint_count':int(join.prior_season_sprint_speed_ft_per_sec.notna().sum()),
        '2026_prior_2025_qualified_bat_speed_count':int(join.prior_season_bat_speed_mph.notna().sum()),
        '2026_prior_2025_both_measured_count':int((join.prior_season_sprint_speed_ft_per_sec.notna()&join.prior_season_bat_speed_mph.notna()).sum()),
        'retrospective_data_last_downloaded_in_oct_2026_not_original_pre2026_archive':True,
        'staged_research_only':True,
        'commercial_rights_unverified':True,
        'not_model_approved':True,
        'not_betting_forward_outcomes':True,
        'source_receipt_sha256':[r['source_csv_sha256'] for r in receipts],
        'joined_parquet_sha256':sha256(joined.read_bytes()),
        'bat_tracking_corrected_source_filter':'seasonStart=YYYY&seasonEnd=YYYY; year=YYYY ALONE WAS IGNORED',
        'misfiltered_year_parameter_artifacts_preserved_but_not_used':True,
        '2024_bat_source_sha256':bat2024['source_csv_sha256'],
        '2025_bat_source_sha256':bat2025['source_csv_sha256'],
    }
    receipt=args.output_dir/'MLB_BIOMECHANICS_RECOVERY_CORRECTED_SUMMARY.json'
    if receipt.exists():
        old=json.loads(receipt.read_text())
        if old!=summary:
            raise ValueError('Completed biomechanics source manifest changed; no overwrite')
    else:
        receipt.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print('ALL_HISTORICAL_MEASURED_SPEED_SOURCE_RECOVERY',json.dumps({k:v for k,v in summary.items() if not k.endswith('sha256')},sort_keys=True))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
