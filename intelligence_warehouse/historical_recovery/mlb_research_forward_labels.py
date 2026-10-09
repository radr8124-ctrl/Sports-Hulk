"""Append-only official MLB player-outcome labels tied to true pregame V2 evidence.

This is an observed feature/outcome *research cohort*, not a frozen probability,
bookmaker wager, bet result, paid pick, or claim of predictive skill.

Identity = unique official gamePk + MLBAM player ID. Grade only if BOTH the
official MLB game master calls the game Final and the independent official MLB
player boxscore ledger has a matching hitting row for that game/player.
A missing hitter is UNKNOWN, NOT A ZERO, because a lineup player might be
scratched/injured and betting markets can void. Any disagreement must halt.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime,timezone
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from .mlb_asof_feature_store import ROOT,sha_file
from .mlb_live_research_feature_freeze_v2 import (
    OUTPUT as FROZEN_SOURCE,
    SCHEMA as FROZEN_SCHEMA,
    REVISION as FROZEN_REVISION,
)

ORIGINAL_PREGAME_LINEUPS=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_PREGAME_SOURCE_EVIDENCE.jsonl'
MASTER=ROOT/'baseball_vault/derived/MLB_GAME_MASTER.csv'
INCREMENTAL=ROOT/'intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_LEDGER.csv'
OUTPUT=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V2_OFFICIAL_FORWARD_RESEARCH_LABELS.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V2_OFFICIAL_FORWARD_LABEL_SUMMARY.json'
SCHEMA='MLB_V2_OFFICIAL_FINAL_FORWARD_RESEARCH_LABEL_V1'
STAT_LABELS={
    'hits':'official_hits',
    'walks':'official_walks',
    'strikeouts':'official_strikeouts',
    'total_bases':'official_total_bases',
    'stolen_bases':'official_stolen_bases',
    'plate_appearances':'official_plate_appearances',
}
MASTER_FIELDS=['gamePk','officialDate','gameDate','gameType','status']
PLAYER_FIELDS=['gamePk','officialDate','player_id','group',*STAT_LABELS]
MINIMAL_COMPARISON_FIELDS=[
    'official_game_pk','player_id','source_frozen_feature_at_utc','source_frozen_capture_at_utc',
    'source_game_pk_from_original_lineup','original_source_line_sha256',
    *STAT_LABELS.values(),
]


def _utc(x)->pd.Timestamp:
    t=pd.to_datetime(x,errors='coerce',utc=True)
    if pd.isna(t):raise ValueError('Missing or invalid official capture datetime')
    return t


def _iso(x)->str:
    return _utc(x).isoformat(timespec='seconds')


def _unique(df:pd.DataFrame,keys:list[str],description:str)->None:
    if not set(keys).issubset(df.columns):
        raise ValueError(f'Missing {description} identity columns')
    if df[keys].isna().any().any() or df.duplicated(keys).any():
        raise ValueError(f'Provider source has duplicate or missing {description} identity')


def _frozen_ok(record:dict,now:pd.Timestamp)->None:
    if record.get('schema')!=FROZEN_SCHEMA or record.get('source_history_revision')!=FROZEN_REVISION:
        raise ValueError('Unrecognized source V2 frozen feature version')
    try:
        quote=_utc(record.get('source_capture_at_utc'))
        frozen=_utc(record.get('feature_frozen_at_utc'))
        start=_utc(record.get('scheduled_first_pitch_utc'))
    except ValueError as exc:
        raise ValueError('No valid original pregame frozen source') from exc
    if not quote<=frozen<start<=now:
        if now<start:return
        raise ValueError('Missing or forged original pregame source event')
    if record.get('live_play_approved') is not False or record.get('betting_prediction_written') is not False:
        raise ValueError('The source must be research-only, not an approved sportsbook wager')
    if (
        record.get('source_history_revision')!=FROZEN_REVISION or
        record.get('source_history_verified_completed_through_date') is None
    ):
        raise ValueError('Missing original independently reconciled source revision')
    if not record.get('original_append_only_line_sha256') or len(str(record['original_append_only_line_sha256']))!=64:
        # Original V2 source reference is the SHA-256 of the append-only
        # official pregame schedule+lineup record captured before first pitch.
        raise ValueError('Missing original source row reference and checksum')


def verify_original_pregame_source(frozen:list[dict],original_source_path:Path)->dict:
    """Cryptographically link each frozen feature to its exact MLB lineup line.

    The original first-pitch-before game/player lineup must be in our OWN
    append-only source ledger; an arbitrary SHA string is not enough.
    """
    if not frozen:
        return {'verified_original_frozen_player_ids':0,'missing_original_source_rows':0}
    if not original_source_path.is_file():
        raise ValueError('Missing original MLB official source event ledger; refuse result labeling')
    observed={}
    with original_source_path.open('r',encoding='utf-8') as f:
        for line in f:
            if not line.strip():continue
            try:raw=json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError('Invalid original source JSONL; cannot prove official pregame lineup') from exc
            if raw.get('schema')!='MLB_PREGAME_SOURCE_EVIDENCE_V1':
                raise ValueError('Unexpected original source version')
            digest=hashlib.sha256(line.encode()).hexdigest()
            if digest in observed:
                raise ValueError('Duplicate original immutable source entry SHA')
            observed[digest]=raw
    checked=0
    for record in frozen:
        expected=str(record.get('original_append_only_line_sha256') or '')
        if expected not in observed:
            raise ValueError('Original pregame source sha mismatch; cannot establish true original capture')
        src=observed[expected]
        if str(src.get('evidence_id') or '')!=str(record.get('source_evidence_id') or ''):
            raise ValueError('Original source event ID mismatch')
        if int(src.get('game_pk') or 0)!=int(record.get('game_pk') or 0):
            raise ValueError('Original pregame gamePk mismatch')
        if _utc(src.get('captured_at_utc'))!=_utc(record.get('source_capture_at_utc')):
            raise ValueError('Original pregame source capture time mismatch')
        first=_utc(src.get('first_pitch_utc'))
        if _utc(record.get('scheduled_first_pitch_utc'))!=first:
            raise ValueError('Original pregame scheduled first-pitch mismatch')
        if _utc(src.get('captured_at_utc'))>=first:
            raise ValueError('Original source not observed before game')
        if _utc(record.get('feature_frozen_at_utc'))>=first:
            raise ValueError('Original frozen feature is not pregame')
        if str((src.get('fixture') or {}).get('official_status_at_capture','')).upper() not in (
            'SCHEDULED','PRE-GAME','PRE-GAME WARMUP','WARMUP'
        ):
            raise ValueError('Original fixture not observed as pregame')
        side=record.get('team_side_at_capture')
        if side not in ('home','away'):
            raise ValueError('Original pregame side is invalid')
        lineup=src.get('lineups') or {}
        if lineup.get('status') not in (
            'ONLY_ONE_TEAM_LINEUP_VISIBLE_PREGAME',
            'OFFICIAL_BATTING_ORDER_VISIBLE_BEFORE_KICKOFF',
        ):
            raise ValueError('Original lineup was not observed before the match')
        playerlist=lineup.get(side) or {}
        raw_ids=playerlist.get('player_ids') or []
        if (
            len(raw_ids)!=9 or len(set(str(x) for x in raw_ids))!=9
            or playerlist.get('source')!='LIVE_FEED_OFFICIAL_BATTING_ORDER_CAPTURED_PREGAME'
            or playerlist.get('confirmed_asof_capture') is not True
        ):
            raise ValueError('Original pregame lineup lacks nine official published identifiers')
        if str(record.get('player_id') or '') not in {str(x) for x in raw_ids}:
            raise ValueError('Original pregame player ID not included in observed lineup')
        checked+=1
    return {
        'verified_original_frozen_player_ids':checked,
        'missing_original_source_rows':0,
        'original_source_ledger_sha256':sha_file(original_source_path),
        'original_lineup_source':'EXACT_ORIGINAL_MLB_PREGAME_SOURCE_JSONL_SHA256_AND_PLAYER_ID',
        'official_lineup_capture_times_before_kickoff_verified':True,
        'bookmaker_prices_or_picks_included':False,
    }


def select_verified_final_labels(
    frozen:list[dict],
    master:pd.DataFrame,
    player_boxscore:pd.DataFrame,
    *,now:datetime,
)->tuple[list[dict],dict]:
    if now.tzinfo is None:
        raise ValueError('Require aware observation clock for source-time grading')
    observation=_utc(now)
    if not {'gamePk','officialDate','gameDate','gameType','status'}.issubset(master.columns):
        raise ValueError('No complete official MLB game status/identity')
    if master.gamePk.isna().any() or master.duplicated(['gamePk']).any():
        raise ValueError('Official game master duplicate gamePk identity')
    if player_boxscore is None:
        player_boxscore=pd.DataFrame(columns=PLAYER_FIELDS)
    required={'gamePk','officialDate','player_id','group',*STAT_LABELS.keys()}
    if missing:=required-set(player_boxscore.columns):
        raise ValueError(f'Player grade source missing required stats: {sorted(missing)}')
    box=player_boxscore[player_boxscore.group.astype(str).eq('HITTING')].copy()
    _unique(box,['gamePk','player_id'],'final player hitter result')
    games=master.set_index('gamePk')
    players=box.set_index(['gamePk','player_id'])
    frozen_ids=set()
    proposed=[]
    count=Counter()
    seen_games=set()
    for record in frozen:
        gid=int(record['game_pk'])
        pid=int(record['player_id'])
        key=(gid,pid)
        if key in frozen_ids:
            raise ValueError('Frozen feature ledger has duplicate official player/game identity')
        frozen_ids.add(key)
        if gid not in games.index:
            count['missing_game_master']+=1
            continue
        g=games.loc[gid]
        if str(g['status'])!='Final':
            count['non_final_games_deferred']+=1
            continue
        start=_utc(record.get('scheduled_first_pitch_utc'))
        if observation<=start:
            count['non_final_games_deferred']+=1
            continue
        _frozen_ok(record,observation)
        official_start=_utc(g['gameDate'])
        # Changes in kickoff schedule/identity require a separate reschedule
        # provenance audit before matching a timestamped pregame lineup.
        if abs((official_start-start).total_seconds())>180:
            raise ValueError('Original frozen first-pitch and official completed game start mismatch')
        expected_date=str(g['officialDate'])
        # The original feature's fixture official date is not always in
        # the frozen record, so source MLB master and player ledger date
        # crosscheck is mandatory.
        if key not in players.index:
            count['missing_frozen_player_boxscore_rows']+=1
            continue
        p=players.loc[key]
        if str(p['officialDate'])!=expected_date:
            raise ValueError('Official MLB game/boxscore player date mismatch')
        stats={}
        for field,label in STAT_LABELS.items():
            val=pd.to_numeric(p[field],errors='coerce')
            if pd.isna(val) or not np.isfinite(val) or val<0:
                raise ValueError('Invalid official completed-game player result')
            stats[label]=float(val)
        raw_ref=str(record['original_append_only_line_sha256'])
        proposed.append({
            'schema':SCHEMA,
            'official_game_pk':gid,
            'player_id':pid,
            'official_game_date':expected_date,
            'game_type':str(g['gameType']),
            'scheduled_first_pitch_utc':_iso(start),
            'source_frozen_capture_at_utc':_iso(record['source_capture_at_utc']),
            'source_frozen_feature_at_utc':_iso(record['feature_frozen_at_utc']),
            'source_game_pk_from_original_lineup':gid,
            'original_source_line_sha256':raw_ref,
            'original_frozen_player_source_schema':FROZEN_SCHEMA,
            'official_final_status_from_mlb_master':'Final',
            'official_outcome_checked_at_utc':_iso(observation),
            'outcome_from':'MLB_STATSAPI_OFFICIAL_FINAL_HITTER_BOXSCORE_LEDGER',
            'research_grade_class':'ACTUAL_HITTING_STATS_NOT_SPORTSBOOK_SETTLEMENT',
            'pregame_frozen_before_official_game_start':True,
            'missing_playing_time_not_inferred':True,
            'sportsbook_bet_settled':False,
            'model_win_or_probability_qualified':False,
            'live_play_approved':False,
            'prediction_or_price_ever_created_by_this_grader':False,
            **stats,
        })
        seen_games.add(gid)
    receipt={
        'grade_source':'INDEPENDENT_MLB_OFFICIAL_FINAL_GAME_MASTER_AND_HITTER_BOXSCORE',
        'observed_at_utc':_iso(observation),
        'frozen_player_feature_records_checked':len(frozen),
        'official_final_player_grade_rows_ready':len(proposed),
        'official_grade_ready_games':len(seen_games),
        'missing_frozen_player_boxscore_rows':count['missing_frozen_player_boxscore_rows'],
        'non_final_games_deferred':count['non_final_games_deferred'],
        'missing_game_master_count':count['missing_game_master'],
        'sportsbook_settlements_claimed':0,
        'paid_bet_plausibility_not_inferred':True,
        'model_promotion_authorized':False,
    }
    return sorted(proposed,key=lambda x:(x['official_game_pk'],x['player_id'])),receipt


def append_unique_official_labels(path:Path,records:list[dict])->int:
    if not records:return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+'.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        saved={}
        if path.exists():
            with path.open('r',encoding='utf-8') as infile:
                for line in infile:
                    if not line.strip():continue
                    p=json.loads(line)
                    if p.get('schema')!=SCHEMA:raise ValueError('Foreign research grade schema, refuse to append')
                    key=(int(p['official_game_pk']),int(p['player_id']))
                    if key in saved:
                        raise ValueError('Duplicate historical settled research source, refuse to append')
                    saved[key]=p
        incoming=set()
        unseen=[]
        for r in records:
            if r.get('schema')!=SCHEMA or r.get('sportsbook_bet_settled') is not False or r.get('model_win_or_probability_qualified') is not False:
                raise ValueError('Only official, non-betting research labels accepted')
            key=(int(r['official_game_pk']),int(r['player_id']))
            if key in incoming:
                raise ValueError('Duplicate grade candidate in the same source batch')
            incoming.add(key)
            if key in saved:
                if any(saved[key].get(field)!=r.get(field) for field in MINIMAL_COMPARISON_FIELDS):
                    raise ValueError('Official source conflicting historical result; manual correction audit required')
                continue
            unseen.append(r)
        if unseen:
            with path.open('a',encoding='utf-8') as out:
                for r in unseen:
                    out.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
                out.flush()
                os.fsync(out.fileno())
        return len(unseen)


def _read_frozen(path:Path)->list[dict]:
    if not path.is_file():return []
    seen=set();records=[]
    with path.open('r',encoding='utf-8') as f:
        for line in f:
            if not line.strip():continue
            rec=json.loads(line)
            key=(int(rec['game_pk']),int(rec['player_id']))
            if key in seen:
                raise ValueError('Repeated frozen feature player/game record')
            seen.add(key);records.append(rec)
    return records


def _existing_grade_index(path:Path)->set[tuple[int,int]]:
    if not path.exists():return set()
    keys=set()
    with path.open('r',encoding='utf-8') as f:
        for line in f:
            if not line.strip():continue
            x=json.loads(line)
            if x.get('schema')!=SCHEMA:raise ValueError('Unexpected existing grade source format')
            key=(int(x['official_game_pk']),int(x['player_id']))
            if key in keys:raise ValueError('Duplicate existing research grade')
            keys.add(key)
    return keys


def grade_cycle(
    pregame:Path=FROZEN_SOURCE,
    output:Path=OUTPUT,
    master_file:Path=MASTER,
    player_file:Path=INCREMENTAL,
    *,now:datetime|None=None,original_source_file:Path=ORIGINAL_PREGAME_LINEUPS,
)->dict:
    observation=now or datetime.now(timezone.utc)
    if observation.tzinfo is None:raise ValueError('Offset-aware actual grade time required')
    frozen=_read_frozen(pregame)
    old_index=_existing_grade_index(output)
    missing=[r for r in frozen if (int(r['game_pk']),int(r['player_id'])) not in old_index]
    # Avoid loading large official season/game tables while every scheduled
    # game remains ahead or all player IDs have already been truthfully graded.
    due=[r for r in missing if _utc(r['scheduled_first_pitch_utc'])< _utc(observation)]
    if not due:
        return {
            'schema':SCHEMA,
            'ran_at_utc':_iso(observation),
            'frozen_feature_records':len(frozen),
            'ungraded_records_with_game_started':0,
            'non_final_games_deferred':len(missing),
            'missing_official_player_results':0,
            'labels_appended':0,
            'total_official_research_labels':len(old_index),
            'independent_games_with_official_labels':len({g for g,_ in old_index}),
            'official_boxscore_source_read':False,
            'sportsbook_predictions_scored_or_promoted':False,
            'original_recommendation_ledger_changed':False,
            'source_rights_still_require_review':True,
        }
    games=pd.read_csv(master_file,usecols=MASTER_FIELDS,low_memory=False)
    # Screen official game statuses BEFORE opening the potentially missing
    # player-data file. There is no honest "zero hits" on an unfinished game.
    finals=set(pd.to_numeric(
        games.loc[games.status.eq('Final'),'gamePk'],errors='coerce'
    ).dropna().astype(int))
    newly_final=[r for r in due if int(r['game_pk']) in finals]
    postponed=len(due)-len(newly_final)
    if not newly_final:
        return {
            'schema':SCHEMA,
            'ran_at_utc':_iso(observation),
            'frozen_feature_records':len(frozen),
            'ungraded_records_with_game_started':len(due),
            'non_final_games_deferred':postponed,
            'missing_official_player_results':0,
            'labels_appended':0,
            'total_official_research_labels':len(old_index),
            'independent_games_with_official_labels':len({g for g,_ in old_index}),
            'official_boxscore_source_read':False,
            'sportsbook_predictions_scored_or_promoted':False,
            'original_recommendation_ledger_changed':False,
            'source_rights_still_require_review':True,
        }
    original_lineup_proof=verify_original_pregame_source(newly_final,original_source_file)
    if player_file.exists():
        boxes=pd.read_csv(player_file,usecols=PLAYER_FIELDS,low_memory=False)
    else:
        boxes=pd.DataFrame(columns=PLAYER_FIELDS)
    official,rec=select_verified_final_labels(newly_final,games,boxes,now=observation)
    appended=append_unique_official_labels(output,official)
    final=_existing_grade_index(output)
    return {
        'schema':SCHEMA,
        'ran_at_utc':_iso(observation),
        'frozen_feature_records':len(frozen),
        'ungraded_records_with_game_started':len(due),
        'non_final_games_deferred':postponed+rec['non_final_games_deferred'],
        'missing_official_player_results':rec['missing_frozen_player_boxscore_rows'],
        'labels_appended':appended,
        'total_official_research_labels':len(final),
        'independent_games_with_official_labels':len({g for g,_ in final}),
        'official_boxscore_source_read':True,
        'original_pregame_lineup_proof':original_lineup_proof,
        'last_provider_sources':{
            'official_game_master_sha256':sha_file(master_file),
            'official_incremental_player_history_sha256':sha_file(player_file) if player_file.exists() else None,
            'pregame_features_v2_sha256':sha_file(pregame),
            'original_live_source_lineup_ledger_sha256':sha_file(original_source_file),
        },
        'sportsbook_predictions_scored_or_promoted':False,
        'original_recommendation_ledger_changed':False,
        'source_rights_still_require_review':True,
    }


def main():
    parser=argparse.ArgumentParser(description='Research-only MLB final game labels paired to true pregame frozen features')
    parser.add_argument('--pregame',type=Path,default=FROZEN_SOURCE)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args()
    if args.pregame.resolve()!=FROZEN_SOURCE.resolve() or args.output.resolve()!=OUTPUT.resolve():
        raise SystemExit('Unrecognized official grade source, refusing to backfill or overwrite')
    result=grade_cycle()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temp=SUMMARY.with_suffix('.tmp')
    temp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    os.replace(temp,SUMMARY)
    print('MLB_OFFICIAL_PREQUOTE_V2_RESEARCH_OUTCOMES',json.dumps(result,sort_keys=True))


if __name__=='__main__':
    main()
