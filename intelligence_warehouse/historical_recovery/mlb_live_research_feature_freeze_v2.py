"""MLB first-seen lineup freeze with verified October postseason *prior* history.

This V2 source is separate/immutable from original V1 pregame research rows.
It verifies legacy official game history with newer MLB StatsAPI incremental
player-game ledger against actual Final game master and refuses disagreements.
A schedule-known lineup and completed prior game features may be frozen
BEFORE the next first pitch. It writes no prices/betting predictions/PLAYs.
"""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path

import pandas as pd

from .mlb_asof_feature_store import ROOT,SOURCE_BIOMECH,sha_file
from .mlb_incremental_history_merge import (
    merge_verified_recent_hitter_history,
    FULL,RECENT,MASTER,CHECK_STAT,
)
from .mlb_live_research_feature_freeze import (
    SOURCE,
    _load_recent_immutable_evidence,_utc,_iso,
    make_live_features,
)

OUTPUT=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_RESEARCH_ASOF_FEATURE_FREEZE_V2.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_RESEARCH_FEATURE_FREEZE_V2_SUMMARY.json'
SCHEMA='MLB_TRUE_PREGAME_RESEARCH_FEATURE_FREEZE_V2'
REVISION='OFFICIAL_FINAL_REGULAR_AND_POSTSEASON_V2'
OFFICIAL_HISTORY=['game_pk','player_id','season','official_date','game_date','game_type','status','group',*CHECK_STAT]
RECENT_HISTORY=['gamePk','player_id','season','officialDate','group',*CHECK_STAT]
OFFICIAL_GAMES=['gamePk','officialDate','gameDate','gameType','status']


def make_reconciled_pregame_v2(
    official_lineup_evidence:dict,reconciled_history:pd.DataFrame,
    completed_prior_season:pd.DataFrame,*,now:datetime,
    current_source_checksums:dict[str,str],
    source_last_verified_date:str,
)->list[dict]:
    if not current_source_checksums or any(
        len(s)!=64 or any(c not in '0123456789abcdef' for c in s.lower())
        for s in current_source_checksums.values()
    ):
        raise ValueError('Historical source checksums must be nonblank valid SHA256')
    if not {'source_history_origin','source_verified_before_quote_required'}.issubset(reconciled_history.columns):
        raise ValueError('Postseason source verification missing from merged history')
    observed=_utc(now)
    final_date=pd.Timestamp(source_last_verified_date)
    if final_date.date()>=observed.date():
        # Latest completed source *date* should only be fully eligible after
        # previous calendar date. New same-day game result always excluded.
        raise ValueError('Latest verified source game date not older than frozen pregame date')
    raw=make_live_features(
        official_lineup_evidence,reconciled_history,
        completed_prior_season,now=now,
        allow_verified_postseason_prior=True,
    )
    output=[]
    for source in raw:
        row=dict(source)
        row['schema']=SCHEMA
        row['source_history_revision']=REVISION
        row['source_history_verified_completed_through_date']=source_last_verified_date
        row['source_game_master_provenance']='OFFICIAL_GAME_PK_AND_FINAL_STATUS_XREF_ONLY'
        row['postseason_final_games_allowed_only_from_verified_master']=True
        row['source_original_grade_settlements_excluded']=True
        row['source_verified_before_quote_required']=True
        row['complete_reconciliation_provenance_sha256']=dict(current_source_checksums)
        row['lineup_snapshot_not_rewritten_from_legacy_v1']=True
        row['research_only']=True
        row['live_play_approved']=False
        row['betting_prediction_written']=False
        row['original_sports_hulk_picks_created']=0
        output.append(row)
    return output


def _ledger_index(path:Path)->tuple[set[tuple[int,int]],set[int]]:
    keys=set();games=set()
    if not path.exists():return keys,games
    with path.open('r',encoding='utf-8') as src:
        for line in src:
            if not line.strip():continue
            row=json.loads(line)
            if row.get('schema')!=SCHEMA:
                raise ValueError('Unrecognized V2 frozen feature ledger version')
            key=(int(row['game_pk']),int(row['player_id']))
            if key in keys:
                raise ValueError('Duplicate original V2 frozen game/player ID, refuse append')
            keys.add(key);games.add(key[0])
    return keys,games


def append_v2_only(path:Path,records:list[dict])->int:
    if not records:return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+'.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        old,_=_ledger_index(path)
        pending=[]
        for row in records:
            ident=(int(row['game_pk']),int(row['player_id']))
            if (
                row.get('schema')!=SCHEMA or
                row.get('source_history_revision')!=REVISION or
                _utc(row['source_capture_at_utc'])>_utc(row['feature_frozen_at_utc']) or
                _utc(row['feature_frozen_at_utc'])>=_utc(row['scheduled_first_pitch_utc']) or
                row.get('live_play_approved') or row.get('betting_prediction_written') or
                row.get('source_verified_before_quote_required') is not True
            ):
                raise ValueError('Invalid or postgame V2 immutable official source')
            if ident not in old:
                pending.append(row)
                old.add(ident)
        if pending:
            with path.open('a',encoding='utf-8') as f:
                for row in pending:
                    f.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n')
                f.flush();os.fsync(f.fileno())
        return len(pending)


def _unseen_lineup_events(source:Path,out:Path,when:datetime)->tuple[list[dict],int,int,set[int]]:
    candidates=_load_recent_immutable_evidence(source,when)
    existing,games=_ledger_index(out)
    selected=[]
    skipped=0
    for event in candidates:
        pk=int(event['game_pk'])
        keys=set()
        for side in ('home','away'):
            for raw in (event.get('lineups') or {}).get(side,{}).get('player_ids',[]):
                try:keys.add((pk,int(raw)))
                except (ValueError,TypeError):continue
        skipped+=len(keys & existing)
        if keys-existing:selected.append(event)
    return selected,len(candidates),skipped,games


def freeze_v2_cycle(
    source:Path=SOURCE,output:Path=OUTPUT,*,now:datetime|None=None,
    legacy_file:Path=FULL,incremental_file:Path=RECENT,
    game_master_file:Path=MASTER,prior_biomechanics_file:Path=SOURCE_BIOMECH,
)->dict:
    actual=now or datetime.now(timezone.utc)
    if actual.tzinfo is None:
        raise ValueError('Require offset-aware current observation clock')
    unseen,eligible,preexisting,pre_game_ids=_unseen_lineup_events(source,output,actual)
    added=0
    last=None
    report=None
    updated=[]
    heavy=bool(unseen)
    if unseen:
        legacy=pd.read_csv(legacy_file,usecols=OFFICIAL_HISTORY,low_memory=False)
        recent=pd.read_csv(incremental_file,usecols=RECENT_HISTORY,low_memory=False)
        master=pd.read_csv(game_master_file,usecols=OFFICIAL_GAMES,low_memory=False)
        verified,report=merge_verified_recent_hitter_history(legacy,recent,master,target_season=actual.year)
        if report['source_stat_conflict_count']!=0:
            raise ValueError('Unresolved official historical results mismatch')
        last=report['latest_official_completed_date']
        prior=pd.read_parquet(prior_biomechanics_file)
        digests={
            'legacy_full_official_game_history':sha_file(legacy_file),
            'incremental_official_boxscore_ledger':sha_file(incremental_file),
            'official_game_master':sha_file(game_master_file),
            'completed_prior_season_biomechanics':sha_file(prior_biomechanics_file),
        }
        for event in unseen:
            if _utc(actual)>=_utc(event['first_pitch_utc']):
                continue
            out=make_reconciled_pregame_v2(
                event,verified,prior,
                now=actual,
                current_source_checksums=digests,
                source_last_verified_date=last,
            )
            for row in out:
                row['original_append_only_line_sha256']=event['_source_immutable_line_sha256']
                row['official_history_reconciliation_source_stat_conflict_count']=report['source_stat_conflict_count']
            written=append_v2_only(output,out)
            added+=written
            updated.append({'game_pk':event['game_pk'],'source_lineup_at':event['captured_at_utc'],
                            'frozen_player_records_created':written,
                            'official_source_origin':'MLB_MASTER_VERIFIED_PREQUOTE_REG_AND_POSTSEASON'})
    stored,game_ids=_ledger_index(output)
    return {
        'schema':SCHEMA,
        'ran_at_utc':_iso(actual),
        'source':'ORIGINAL_PREGAME_MLB_SCHEDULE_LINEUP_PLUS_MLB_FINAL_GAMES_RECONCILED_V2',
        'eligible_recent_lineup_games':eligible,
        'unseen_lineup_games':len(unseen),
        'previously_frozen_player_ids_preserved':preexisting,
        'large_history_reconciliation_run':heavy,
        'source_merge_proof':report,
        'last_official_completed_date':last,
        'fresh_v2_player_features_appended':added,
        'total_v2_frozen_player_features':len(stored),
        'distinct_upcoming_game_ids':len(game_ids),
        'sources_by_game':updated,
        'automatic_model_change':False,
        'betting_forward_predictions_created':0,
        'sportsbook_source_prices_written':0,
        'paid_plays_promoted':0,
        'original_v1_historical_evidence_rewritten':False,
        'offsite_recovery_verified':False,
    }


def main():
    ap=argparse.ArgumentParser(description='Verified postseason source MLB research pregame freeze V2')
    ap.add_argument('--source-ledger',type=Path,default=SOURCE)
    ap.add_argument('--output-ledger',type=Path,default=OUTPUT)
    args=ap.parse_args()
    if args.source_ledger.resolve()!=SOURCE.resolve() or args.output_ledger.resolve()!=OUTPUT.resolve():
        raise SystemExit('Refusing unsafe V2 source ledger or output path')
    result=freeze_v2_cycle()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temporary=SUMMARY.with_suffix('.tmp')
    temporary.write_text(json.dumps(result,indent=2,default=str)+'\n')
    os.replace(temporary,SUMMARY)
    print('MLB_VERIFIED_POSTSEASON_ASOF_V2',json.dumps({
        k:v for k,v in result.items()
        if k not in ('source_merge_proof','sources_by_game')
    },sort_keys=True))


if __name__=='__main__':main()
