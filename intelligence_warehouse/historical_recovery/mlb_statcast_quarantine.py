"""Safely restore *new* historical Statcast source data into quarantined research.

This is a newly retrieved public source, NOT the exact original September 2026
MacBook file. Never rewrites live MLB pitcher/batter profiles or betting models.
Each chunk is bounded by date/byte-size and has SHA-verified raw/Parquet copies.
"""
from __future__ import annotations

from datetime import datetime,timezone
from pathlib import Path
import argparse
import gzip
import hashlib
import io
import json
import os
import tempfile
import time
from typing import Any

import pandas as pd
import requests

SAVANT_SOURCE = 'https://baseballsavant.mlb.com/statcast_search/csv'
BOUND_WINDOWS = [('2026-09-01','2026-09-03'),('2026-09-04','2026-09-05')]
ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / 'reports/mlb_statcast_recovery_20261008/quarantine'
MAX_CSV_BYTES = 28_000_000
MANDATORY = {
    'pitch_type','game_date','release_speed','release_spin_rate',
    'pfx_x','pfx_z','launch_speed','launch_angle',
    'pitcher','batter','game_pk','at_bat_number','pitch_number',
    'description','events',
}
PARAMS = {
    'all':'true','type':'details','player_type':'pitcher',
    'hfGT':'R|PO|S|','min_pitches':'0','min_results':'0',
    'group_by':'name','sort_col':'pitches','sort_order':'desc','min_abs':'0',
}
HISTORICAL_REPORTED_COUNTS = {
    ('2026-09-01','2026-09-03'):11928,
    ('2026-09-04','2026-09-05'):9040,
}


def sha256(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()


def validate_statcast_csv(raw:bytes,start_date:str,end_date:str)->tuple[pd.DataFrame,dict]:
    """Validate provider source: content, era, key types, and stable pitch schema."""
    if not raw or len(raw)>MAX_CSV_BYTES or (not raw.lstrip(b'\xef\xbb\xbf \t\r\n').startswith(b'"pitch_type"') and not raw.lstrip(b'\xef\xbb\xbf \t\r\n').startswith(b'pitch_type,')):
        raise ValueError('Source response is not valid Statcast CSV or exceeds byte cap')
    if pd.Timestamp(end_date)<pd.Timestamp(start_date):
        raise ValueError('Invalid historical date window')
    try:
        df=pd.read_csv(io.BytesIO(raw),encoding='utf-8-sig',low_memory=False)
    except Exception as exc:
        raise ValueError('Source response is not valid Statcast CSV') from exc
    missing=MANDATORY-set(df.columns)
    if missing or df.empty:
        raise ValueError(f'Statcast schema incomplete: missing {sorted(missing)} or no pitch rows')
    parsed=pd.to_datetime(df['game_date'],errors='coerce',utc=True)
    if parsed.isna().any() or (parsed.dt.date<pd.Timestamp(start_date).date()).any() or (parsed.dt.date>pd.Timestamp(end_date).date()).any():
        raise ValueError('Statcast dates outside requested date range or invalid')
    ids=pd.to_numeric(df['game_pk'],errors='coerce')
    pit=pd.to_numeric(df['pitcher'],errors='coerce')
    bat=pd.to_numeric(df['batter'],errors='coerce')
    if ids.isna().any() or (ids<=0).any() or pit.isna().any() or bat.isna().any() or (pit<=0).any() or (bat<=0).any():
        raise ValueError('Statcast contains invalid source fixture or pitcher/batter IDs')
    pitch_ids=['game_pk','at_bat_number','pitch_number','pitcher','batter']
    duplicates=int(df.duplicated(pitch_ids).sum())
    completeness={column:round(float(df[column].notna().mean()),6) for column in sorted(MANDATORY)}
    proof={
        'start_date':start_date,
        'end_date':end_date,
        'verified_pitch_rows':len(df),
        'games':int(ids.nunique()),
        'day_count':int(parsed.dt.date.nunique()),
        'first_game_date':parsed.min().date().isoformat(),
        'last_game_date':parsed.max().date().isoformat(),
        'source_csv_bytes':len(raw),
        'source_csv_sha256':sha256(raw),
        'source_columns':list(df.columns),
        'source_column_count':len(df.columns),
        'required_source_columns_present':True,
        'pitch_key_duplicate_count':duplicates,
        'source_numeric_non_null':completeness,
        'historical_original_receipt_count':HISTORICAL_REPORTED_COUNTS.get((start_date,end_date)),
        'matches_reported_historical_row_count':len(df)==HISTORICAL_REPORTED_COUNTS.get((start_date,end_date)),
        'source_provenance':'NEW_PUBLIC_BASEBALL_SAVANT_DOWNLOAD_NOT_ORIGINAL_STORED_SOURCE',
        'time_leakage_rule':'This is postgame historical raw, not automatically valid pregame model features.',
        'production_model_authorized':False,
    }
    return df,proof


def names(start:str,end:str)->tuple[str,str,str]:
    return (
        f'raw_statcast_{start}_{end}.csv.gz',
        f'statcast_{start}_{end}.parquet',
        f'proof_statcast_{start}_{end}.json',
    )


def assert_recovery_manifest(directory:Path,receipt:dict)->None:
    if not isinstance(receipt,dict) or receipt.get('production_model_authorized') is not False:
        raise ValueError('Invalid recovery manifest authorization flags')
    for kind in ('raw_gz','parquet'):
        ent=receipt.get('stored_files',{}).get(kind)
        if not ent or '/' in ent['file'] or '\\' in ent['file']:
            raise ValueError('Incomplete source manifest file path')
        p=directory/ent['file']
        if not p.is_file() or sha256(p.read_bytes())!=ent['sha256']:
            raise ValueError(f'SHA256 immutable historical source mismatch: {kind}')
    raw=gzip.decompress((directory/receipt['stored_files']['raw_gz']['file']).read_bytes())
    if sha256(raw)!=receipt['source_csv_sha256']:
        raise ValueError('SHA256 raw source mismatch')


def save_quarantined_chunk(directory:Path,df:pd.DataFrame,raw:bytes,proof:dict)->dict:
    if directory.resolve()==(ROOT/'baseball_vault/raw/statcast').resolve() or str(directory.resolve()).startswith(str(ROOT/'baseball_vault/derived')):
        raise ValueError('Refusing any live baseball vault write path')
    csv_name,parquet_name,receipt_name=names(proof['start_date'],proof['end_date'])
    directory.mkdir(parents=True,exist_ok=True)
    receipt_file=directory/receipt_name
    if receipt_file.exists():
        saved=json.loads(receipt_file.read_text())
        if saved.get('source_csv_sha256')!=sha256(raw):
            raise ValueError('Existing quarantined source is immutable; never overwrite it')
        assert_recovery_manifest(directory,saved)
        return saved
    if sha256(raw)!=proof['source_csv_sha256'] or len(df)!=proof['verified_pitch_rows']:
        raise ValueError('Raw source changed after validation')
    for entry in [directory/csv_name,directory/parquet_name]:
        if entry.exists():
            raise ValueError('Partial unreconciled historical source exists; not overwriting')
    compressed=gzip.compress(raw,compresslevel=6,mtime=0)
    # Never modify historical production sources. Parquet preserves all fields.
    import pyarrow as pa
    import pyarrow.parquet as pq
    output=pa.BufferOutputStream()
    pq.write_table(pa.Table.from_pandas(df,preserve_index=False),output,compression='zstd')
    parquet=output.getvalue().to_pybytes()
    output.close()
    receipt={
        **proof,
        'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),
        'original_source_url':SAVANT_SOURCE,
        'source_query_parameters':{**PARAMS,'game_date_gt':proof['start_date'],'game_date_lt':proof['end_date']},
        'stored_files':{
            'raw_gz':{'file':csv_name,'sha256':sha256(compressed),'bytes':len(compressed)},
            'parquet':{'file':parquet_name,'sha256':sha256(parquet),'bytes':len(parquet)},
        },
        'staging_only':True,
        'production_model_authorized':False,
    }
    # Exclusive creation fails if another worker already reserved a path.
    try:
        with (directory/csv_name).open('xb') as f:
            f.write(compressed);f.flush();os.fsync(f.fileno())
        with (directory/parquet_name).open('xb') as f:
            f.write(parquet);f.flush();os.fsync(f.fileno())
        with receipt_file.open('x') as f:
            json.dump(receipt,f,indent=2,sort_keys=True)
            f.write('\n');f.flush();os.fsync(f.fileno())
    except Exception:
        # Leave evidence for investigation rather than silently deleting
        # unexpected partial source artifacts.
        raise
    assert_recovery_manifest(directory,receipt)
    return receipt


def request_raw_chunk(start_date:str,end_date:str,*,timeout:int=45)->tuple[bytes,dict]:
    if (start_date,end_date) not in BOUND_WINDOWS:
        raise ValueError('Recovery is restricted to two dated missing chunks')
    params={**PARAMS,'game_date_gt':start_date,'game_date_lt':end_date}
    begin=time.monotonic()
    with requests.get(SAVANT_SOURCE,params=params,timeout=(8,timeout),stream=True,
                      headers={'User-Agent':'Sports-HULK-Baseball/1.1',
                               'Accept':'text/csv'}) as response:
        response.raise_for_status()
        data=bytearray()
        for chunk in response.iter_content(chunk_size=1024*1024):
            data.extend(chunk)
            if len(data)>MAX_CSV_BYTES:
                raise ValueError('Upstream historical CSV exceeds 28 MB source cap')
        return bytes(data),{
            'http_status':response.status_code,
            'upstream_content_type':response.headers.get('Content-Type'),
            'request_elapsed_seconds':round(time.monotonic()-begin,3),
            'source':SAVANT_SOURCE,
            'retrieval_is_not_original_binary_archive':True,
        }


def main()->int:
    ap=argparse.ArgumentParser(description='Quarantined 2026-09-01..05 Statcast source recovery')
    ap.add_argument('--output-dir',type=Path,default=RESEARCH)
    ap.add_argument('--max-windows',type=int,default=2)
    args=ap.parse_args()
    if not 1<=args.max_windows<=2:
        raise SystemExit('Bounded recovery permits 1 or 2 windows only')
    if args.output_dir.resolve()!=(RESEARCH.resolve()):
        raise SystemExit('Refusing unsanctioned recovery path; use canonical quarantined directory')
    receipts=[]
    for start,end in BOUND_WINDOWS[:args.max_windows]:
        _,_,proof_name=names(start,end)
        if (args.output_dir/proof_name).exists():
            receipt=json.loads((args.output_dir/proof_name).read_text())
            assert_recovery_manifest(args.output_dir,receipt)
            print('PRESERVED_NO_REFETCH',start,end,receipt['verified_pitch_rows'],flush=True)
            receipts.append(receipt)
            continue
        raw,query_receipt=request_raw_chunk(start,end)
        df,proof=validate_statcast_csv(raw,start,end)
        proof['transport']=query_receipt
        receipt=save_quarantined_chunk(args.output_dir,df,raw,proof)
        print('QUARANTINED_SOURCE_CHUNK',start,end,'rows',receipt['verified_pitch_rows'],
              'games',receipt['games'],'source_original_count_match',receipt['matches_reported_historical_row_count'],
              'rawsha',receipt['source_csv_sha256'][:20],flush=True)
        receipts.append(receipt)
    summary={
        'source_recovered_as_new_download_not_original_bytes':True,
        'chunks':len(receipts),
        'raw_pitch_rows':sum(r['verified_pitch_rows'] for r in receipts),
        'historical_build_receipt_expected_pitch_rows':sum(r['historical_original_receipt_count'] or 0 for r in receipts),
        'matches_exact_original_reported_counts':all(r['matches_reported_historical_row_count'] for r in receipts),
        'raw_chunk_source':SAVANT_SOURCE,
        'raw_original_mac_archives_restored':False,
        'full_93_chunk_prior_cache_restored':False,
        'source_files_preserved_only_in_quarantine':True,
        'live_mlb_model_or_profiles_changed':False,
    }
    summary_file=args.output_dir.parent/'STAGING_RECOVERY_SUMMARY.json'
    if summary_file.exists():
        old=json.loads(summary_file.read_text())
        if old.get('raw_pitch_rows')!=summary['raw_pitch_rows']:
            raise ValueError('Immutable discovery summary changed; manual review needed')
    else:
        summary_file.write_text(json.dumps(summary,indent=2)+'\n')
    print('FINAL_RECOVERY_SUMMARY',json.dumps(summary,sort_keys=True),flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
