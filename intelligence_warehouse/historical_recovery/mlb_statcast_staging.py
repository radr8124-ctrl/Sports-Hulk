"""Rebuild an isolated September Statcast *addendum* from authenticated sources.

Never reproduce/overwrite an older 93-chunk blended 2025/26 model with just
these 2 recently re-downloaded 2026 chunks. Original combined raw absent.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
import argparse
import hashlib
import json

import pandas as pd

from .mlb_statcast_quarantine import (
    ROOT, RESEARCH, BOUND_WINDOWS, assert_recovery_manifest, names,
    HISTORICAL_REPORTED_COUNTS,
)

TARGET = RESEARCH.parent / 'staged_addendum'
CURRENT_PROFILE_FILES = [
    ROOT/'baseball_vault/derived/MLB_PITCHER_ARSENAL.csv',
    ROOT/'baseball_vault/derived/MLB_BATTER_VS_PITCH_TYPE.csv',
    ROOT/'baseball_vault/derived/MLB_BLENDED_PROFILE_BUILD.csv',
]


def _digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
    return h.hexdigest()


def eligible_research_window(event_start:str,latest_date_in_raw:str)->bool:
    """Temporal bound ONLY, not a claim the source was originally captured as-of."""
    event=pd.Timestamp(event_start)
    if event.tzinfo is None:
        raise ValueError('Require offset-aware future game start')
    prior_date=pd.Timestamp(latest_date_in_raw).date()
    return event.date()>prior_date


def stage_recovered_september(quarantine:Path=RESEARCH,output:Path=TARGET)->dict:
    if output.resolve()==(ROOT/'baseball_vault/derived').resolve() or not output.resolve().is_relative_to((ROOT/'reports').resolve()):
        raise ValueError('Refusing any production writes; staging only under reports')
    if quarantine.resolve()!=RESEARCH.resolve() or not quarantine.is_dir():
        raise ValueError('Missing canonical two-source quarantine; no partial synthesis')
    rawproof=[]
    chunks=[]
    for start,end in BOUND_WINDOWS:
        _,parquet_name,proof_name=names(start,end)
        source=quarantine/proof_name
        if not source.is_file():
            raise ValueError('Missing quarantine receipt for a required source chunk')
        proof=json.loads(source.read_text())
        assert_recovery_manifest(quarantine,proof)
        tab=pd.read_parquet(quarantine/parquet_name)
        if len(tab)!=proof['verified_pitch_rows'] or len(tab)!=HISTORICAL_REPORTED_COUNTS[(start,end)]:
            raise ValueError('Recovered Statcast source row count does not match original build')
        tab=tab.copy()
        tab['_new_retrieval_chunk_start']=start
        chunks.append(tab)
        rawproof.append({
            'source_chunk':str(source.relative_to(ROOT)),
            'source_proof_sha256':_digest(source),
            'rows':len(tab),
            'csv_sha256':proof['source_csv_sha256'],
            'parquet_sha256':_digest(quarantine/parquet_name),
        })
    if len(chunks)!=2:
        raise ValueError('Quarantine must contain both historical date windows')
    df=pd.concat(chunks,ignore_index=True,sort=False)
    if len(df)!=20968 or df['game_date'].astype(str).str[:10].min()<'2026-09-01' or df['game_date'].astype(str).str[:10].max()>'2026-09-05':
        raise ValueError('Recovered September subset does not match historical period/count')
    pid=['game_pk','at_bat_number','pitch_number','pitcher','batter']
    duplicate=int(df.duplicated(pid).sum())
    # Original backfill applied drop_duplicates to whole rows, not row-key
    # ordering. Never silently remove distinct same-source observations.
    duplicated_full=int(df.duplicated(subset=[c for c in df if not c.startswith('_')]).sum())
    if duplicated_full:
        raise ValueError(f'Exact duplicated source pitch rows ({duplicated_full}) require separate review')
    if any(not p.is_file() for p in CURRENT_PROFILE_FILES):
        raise ValueError('Live original science tables missing; never build without a verifiable snapshot')
    before={str(p.relative_to(ROOT)):_digest(p) for p in CURRENT_PROFILE_FILES}
    output.mkdir(parents=True,exist_ok=True)
    receipt=output/'STAGING_ADDENDUM_PROOF.json'
    if receipt.exists():
        saved=json.loads(receipt.read_text())
        for rel,h in saved['staged_sha256'].items():
            path=output/rel
            if not path.is_file() or _digest(path)!=h:
                raise ValueError('Existing staged dataset was modified')
        if saved['input_proof_sha256'] != [r['source_proof_sha256'] for r in rawproof]:
            raise ValueError('Existing staged receipt from different source; no overwrite allowed')
        return saved
    if list(output.iterdir()):
        raise ValueError('Output directory contains unverified partial staging files')
    from baseball_vault import statcast_backfill
    # This old routine normally writes under baseball_vault/derived; enforce a
    # temporary in-process path substitution for the read-only experiment.
    data=df.drop(columns=['_new_retrieval_chunk_start'])
    with patch.object(statcast_backfill,'DERIVED',output):
        pitcher,batter=statcast_backfill.derive_profiles(data)
    outfiles=[
        output/'MLB_PITCHER_ARSENAL.parquet',output/'MLB_PITCHER_ARSENAL.csv',
        output/'MLB_BATTER_VS_PITCH_TYPE.parquet',output/'MLB_BATTER_VS_PITCH_TYPE.csv',
    ]
    if not all(p.is_file() and p.stat().st_size>100 for p in outfiles):
        raise ValueError('Missing staged Statcast addendum profile outputs')
    after={str(p.relative_to(ROOT)):_digest(p) for p in CURRENT_PROFILE_FILES}
    if before!=after:
        raise RuntimeError('A production profile was changed: reject staged result')
    proof={
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'research_only':True,
        'source_is_original_september_2026_archive':False,
        'new_retrieval_not_original_bytes':True,
        'season':'2026',
        'period':['2026-09-01','2026-09-05'],
        'source_chunks':2,
        'input_proof_sha256':[r['source_proof_sha256'] for r in rawproof],
        'source_receipts':rawproof,
        'pitch_rows':len(df),
        'unique_pitch_keys':int(len(df)-duplicate),
        'distinct_game_ids':int(df['game_pk'].nunique()),
        'pitcher_pitch_type_profile_rows':len(pitcher),
        'batter_pitch_type_profile_rows':len(batter),
        'september_2026_original_logged_pitcher_profiles':1745,
        'september_2026_original_logged_batter_profiles':2854,
        'same_profile_group_counts_as_historical_run':len(pitcher)==1745 and len(batter)==2854,
        'historical_count_discrepancy_cannot_prove_cause':True,
        'old_93_chunk_build_does_not_have_source_raw':True,
        'not_a_full_95_chunk_blend':True,
        'no_automatic_change_to_live_profiles_or_model':True,
        'live_original_sha256_unchanged':after,
        'staged_sha256':{p.name:_digest(p) for p in outfiles},
        'historical_2016_2024_seasons_not_recovered':True,
        'asof_warning':'Analysis reconstructed in October 2026; historical inputs cannot retroactively be called September forward-model predictions.',
    }
    receipt.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
    return proof


def main():
    args=argparse.ArgumentParser(description='Safe isolated Statcast September addendum analysis')
    args.add_argument('--stage-only',action='store_true')
    cfg=args.parse_args()
    out=stage_recovered_september()
    print('STATCAST_REBUILT_STAGE_ONLY',json.dumps({
        'pitch_rows':out['pitch_rows'],
        'games':out['distinct_game_ids'],
        'pitcher_profiles':out['pitcher_pitch_type_profile_rows'],
        'batter_profiles':out['batter_pitch_type_profile_rows'],
        'not_full_blend':out['not_a_full_95_chunk_blend'],
        'live_original_unchanged':out['no_automatic_change_to_live_profiles_or_model'],
    },sort_keys=True))

if __name__=='__main__':
    main()
