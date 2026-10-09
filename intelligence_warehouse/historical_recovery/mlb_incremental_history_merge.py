"""MLB recent official postseason boxscore records reconnect to historical files.

The legacy full official source stopped Oct 1 2026, but a different official
incremental source continued through Oct 7. Join by exact gamePk/player/group,
verify original dates, official Final status and metrics, never silently
resolve a contradictory source or assume a future game has already completed.
This builds *past observed outcomes* for pregame feature formation only.
"""
from __future__ import annotations

from datetime import datetime,timezone
from pathlib import Path
import argparse
import json

import pandas as pd

from .mlb_asof_feature_store import ROOT,sha_file

FULL=ROOT/'intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_HISTORY.csv'
RECENT=ROOT/'intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_LEDGER.csv'
MASTER=ROOT/'baseball_vault/derived/MLB_GAME_MASTER.csv'
OUT=ROOT/'reports/mlb_feature_integration_20261008/MLB_INCREMENTAL_POSTSEASON_HISTORY_RECONCILIATION.json'
CHECK_STAT=('hits','walks','plate_appearances','stolen_bases')
STUDY_TYPES={'R','D','F','L','W'}


def _source_identity(df:pd.DataFrame,keys:list[str],description:str):
    if not set(keys).issubset(df.columns):
        raise ValueError(f'{description} source key columns missing')
    if df[keys].isna().any().any() or df.duplicated(keys).any():
        raise ValueError(f'{description} duplicate or invalid official game.player IDs')


def merge_verified_recent_hitter_history(
    full:pd.DataFrame,recent:pd.DataFrame,master:pd.DataFrame,
    *,target_season:int=2026
)->tuple[pd.DataFrame,dict]:
    must_full={
        'game_pk','player_id','season','official_date','game_date',
        'game_type','status','group',*CHECK_STAT,
    }
    must_recent={
        'gamePk','player_id','season','officialDate','group',*CHECK_STAT,
    }
    must_master={'gamePk','officialDate','gameDate','gameType','status'}
    for label,missing in (
        ('full',must_full-set(full.columns)),
        ('recent',must_recent-set(recent.columns)),
        ('master',must_master-set(master.columns)),
    ):
        if missing:
            raise ValueError(f'Missing {label} historical provenance fields: {sorted(missing)}')
    _source_identity(master,['gamePk'],'official game master')
    _source_identity(recent,['gamePk','player_id','group'],'incremental ledger')
    _source_identity(full,['game_pk','player_id','group'],'legacy full history')
    old=full[
        full.season.eq(target_season)
        & full.group.astype(str).eq('HITTING')
        & full.game_type.astype(str).isin(STUDY_TYPES)
        & full.status.astype(str).eq('Final')
    ].copy()
    _source_identity(old,['game_pk','player_id'],'final legacy hitter history')
    old['game_pk']=pd.to_numeric(old.game_pk,errors='raise').astype('int64')
    old['player_id']=pd.to_numeric(old.player_id,errors='raise').astype('int64')
    old['source_history_origin']='LEGACY_OFFICIAL_FINAL_BOXSCORE'
    old['source_verified_before_quote_required']=True
    new=recent[
        recent.season.eq(target_season)
        & recent.group.astype(str).eq('HITTING')
    ].copy()
    new=new.rename(columns={'gamePk':'game_pk','officialDate':'official_date'})
    _source_identity(new,['game_pk','player_id'],'incremental hitter history')
    new['game_pk']=pd.to_numeric(new.game_pk,errors='raise').astype('int64')
    new['player_id']=pd.to_numeric(new.player_id,errors='raise').astype('int64')
    games=master.rename(columns={
        'gamePk':'game_pk','officialDate':'master_official_date',
        'gameDate':'game_date','gameType':'game_type','status':'status',
    })
    joined=new.merge(games[['game_pk','master_official_date','game_date','game_type','status']],
                     on='game_pk',how='left',validate='many_to_one')
    no_fixture=joined.game_date.isna()
    missing_source=int(no_fixture.sum())
    valid=joined[~no_fixture].copy()
    wrong_date=valid.official_date.astype(str).ne(valid.master_official_date.astype(str))
    if wrong_date.any():
        raise ValueError('Incremental official date mismatch: source and official game master disagree')
    skip_nonfinal=~valid.status.astype(str).eq('Final')
    skip_wrong_type=~valid.game_type.astype(str).isin(STUDY_TYPES)
    non_final=int(skip_nonfinal.sum())
    skipped_game_type=int(skip_wrong_type.sum())
    valid=valid[~skip_nonfinal & ~skip_wrong_type].copy()
    if valid.empty:
        raise ValueError('No verified recent completed official player history available')
    for col in CHECK_STAT:
        valid[col]=pd.to_numeric(valid[col],errors='coerce')
        old[col]=pd.to_numeric(old[col],errors='coerce')
    overlap=valid.merge(old[['game_pk','player_id',*CHECK_STAT]],
                        on=['game_pk','player_id'],how='inner',
                        suffixes=('_recent','_old'),validate='one_to_one')
    missing_metrics=0;disagree=0
    for key in CHECK_STAT:
        a=overlap[f'{key}_recent']
        b=overlap[f'{key}_old']
        missing_metrics+=int((a.isna() ^ b.isna()).sum())
        disagree+=int(((a.notna() & b.notna())&(a-b).abs().gt(1e-6)).sum())
    if missing_metrics or disagree:
        raise ValueError(f'Official sources have conflicting or asymmetric MLB hitter stats (mismatch={disagree}, missing={missing_metrics})')
    old_keys=set(zip(old.game_pk,old.player_id))
    added=valid[[
        key not in old_keys
        for key in zip(valid.game_pk,valid.player_id)
    ]].copy()
    added=added.drop(columns=['master_official_date'],errors='ignore')
    added['source_history_origin']='INCREMENTAL_OFFICIAL_FINAL_POSTSEASON_CROSSCHECKED_WITH_GAME_MASTER'
    added['source_verified_before_quote_required']=True
    out=pd.concat([old,added],ignore_index=True,sort=False)
    if out.duplicated(['game_pk','player_id']).any():
        raise RuntimeError('Game/player dedup failed in reconciled official history')
    out=out.sort_values(['official_date','game_date','game_pk','player_id']).reset_index(drop=True)
    max_date=str(out.official_date.max())
    proof={
        'schema':'MLB_OFFICIAL_FINAL_HITTER_HISTORY_RECONCILIATION_V2',
        'target_season':target_season,
        'legacy_final_hitter_player_game_rows':len(old),
        'incremental_eligible_hitter_player_game_rows':len(valid),
        'overlap_source_player_game_rows':len(overlap),
        'source_stat_conflict_count':0,
        'new_incremental_official_player_game_rows':len(added),
        'new_incremental_distinct_official_game_ids':int(added.game_pk.nunique()),
        'missing_official_fixture_rows_refused':missing_source,
        'non_final_incremental_rows_refused':non_final,
        'non_supported_incremental_game_type_rows_refused':skipped_game_type,
        'unified_hitter_player_game_rows':len(out),
        'unified_distinct_game_ids':int(out.game_pk.nunique()),
        'latest_official_completed_date':max_date,
        'recent_by_game_type':{
            key:int(value) for key,value in added.game_type.value_counts().items()
        },
        'source_grade_class':'MLB_STATSAPI_FINAL_ONLY_NOT_BOOKMAKER_SETTLEMENT',
        'time_gate':'REQUIRES_SOURCE_GAME_BEFORE_CAPTURE_DATE_AND_AT_LEAST_12_HOUR_AGE',
        'current_game_or_postquote_inputs_forbidden':True,
        'production_model_or_forward_bet_writes':False,
    }
    return out,proof


def main():
    parser=argparse.ArgumentParser(description='Read-only source reconciliation before player-prop research freezing')
    parser.add_argument('--output',type=Path,default=OUT)
    args=parser.parse_args()
    if args.output.resolve()!=OUT.resolve():
        raise SystemExit('Output must stay in private MLB research reports')
    full=pd.read_csv(FULL,usecols=[
        'game_pk','player_id','season','official_date','game_date','game_type','status',
        'group',*CHECK_STAT,
    ],low_memory=False)
    recent=pd.read_csv(RECENT,usecols=[
        'gamePk','player_id','season','officialDate','group',*CHECK_STAT,
    ],low_memory=False)
    master=pd.read_csv(MASTER,usecols=['gamePk','officialDate','gameDate','gameType','status'],low_memory=False)
    _,proof=merge_verified_recent_hitter_history(full,recent,master)
    proof['source_sha256']={str(p.relative_to(ROOT)):sha_file(p) for p in (FULL,RECENT,MASTER)}
    proof['generated_at_utc']=datetime.now(timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
    print('VERIFIED_MLB_HITTER_RECENT_GAME_MERGE',json.dumps(proof,sort_keys=True))


if __name__=='__main__':
    main()
