"""Official-Final-only MLB player results: research-only missing pipeline link.

Original pregame lineup/game identity + independent official Final master +
fresh original MLB live feed Final + fresh official boxscore => append-only
player ledger & original boxscore receipt. Missing hitter != zero hits, and
no saved historical rows, probabilities, picks or wagers may be rewritten.
"""
from __future__ import annotations

import argparse,csv,fcntl,hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .mlb_asof_feature_store import ROOT,sha_file
from .mlb_live_research_feature_freeze_v2 import OUTPUT as FROZEN,SCHEMA as V2,REVISION
from .mlb_research_forward_labels import ORIGINAL_PREGAME_LINEUPS,verify_original_pregame_source
from intelligence_warehouse.mlb_player_history.build_mlb_player_game_history import rows_from_box

MASTER=ROOT/'baseball_vault/derived/MLB_GAME_MASTER.csv'
LEDGER=ROOT/'intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_LEDGER.csv'
OUTPUT=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_FINAL_PLAYER_BOX_SOURCE_RECEIPTS.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_FINAL_PLAYER_BOX_BRIDGE_SUMMARY.json'
SCHEMA='MLB_OFFICIAL_FINAL_ONLY_FROZEN_PLAYER_SOURCE_BRIDGE_V1'
KEYS=['gamePk','player_id','group']
HITTER_FIELDS=('plateAppearances','atBats','hits','baseOnBalls','strikeOuts',
               'stolenBases','doubles','triples','homeRuns','rbi','runs')
PITCHER_FIELDS=('inningsPitched','hits','baseOnBalls','strikeOuts','homeRuns','battersFaced')
CHECK_STATS=('hits','walks','strikeouts','stolen_bases','plate_appearances',
             'total_bases','hits_allowed','walks_allowed','pitcher_strikeouts','outs')

def _utc(value):
    dt=pd.to_datetime(value,utc=True,errors='coerce')
    if pd.isna(dt):raise ValueError('Unverified official source first pitch/clock')
    return dt

def _read(path:Path):
    if not path.is_file():return []
    with path.open('r',encoding='utf8') as f:return [json.loads(x) for x in f if x.strip()]

def _validate_frozen(rows):
    games={};seen=set()
    for row in rows:
        if row.get('schema')!=V2 or row.get('source_history_revision')!=REVISION:
            raise ValueError('Unknown original frozen official MLB source')
        if row.get('betting_prediction_written') is not False or row.get('live_play_approved') is not False:
            raise ValueError('Original player evidence is not research-only')
        key=(int(row['game_pk']),int(row['player_id']))
        if key in seen:raise ValueError('Duplicate original frozen game/player')
        seen.add(key)
        if not _utc(row['source_capture_at_utc'])<=_utc(row['feature_frozen_at_utc'])<_utc(row['scheduled_first_pitch_utc']):
            raise ValueError('Original pregame player source chronology incorrect')
        games.setdefault(key[0],[]).append(row)
    return games

def discover_due_game_pks(frozen,master,already_collected,*,now,receipt_games=None):
    if now.tzinfo is None:raise ValueError('Official status check requires timezone')
    needed={'gamePk','officialDate','gameDate','gameType','status','home_team','away_team','home_team_id','away_team_id'}
    if needed-set(master.columns):raise ValueError('Incomplete independent final game master')
    if master.gamePk.isna().any() or master.gamePk.duplicated().any():
        raise ValueError('Duplicate official gamePk in master')
    if not already_collected.empty and (set(KEYS)-set(already_collected.columns)
                                         or already_collected.duplicated(KEYS).any()):
        raise ValueError('Corrupted official player source ledger identity')
    done=(set(pd.to_numeric(already_collected.gamePk,errors='raise').astype(int))
          if not already_collected.empty else set())
    groups=_validate_frozen(frozen)
    lookup=master.set_index('gamePk')
    due=[];notfinal=0;already=0
    for game,people in sorted(groups.items()):
        if game not in lookup.index:raise ValueError('Original research gamePk not in master')
        x=lookup.loc[game]
        starts={_utc(p['scheduled_first_pitch_utc']) for p in people}
        if len(starts)!=1 or abs((_utc(x['gameDate'])-next(iter(starts))).total_seconds())>180:
            raise ValueError('Original first-pitch source differs from independent final game master start')
        if str(x['status'])!='Final' or _utc(now)<=next(iter(starts)):
            notfinal+=1;continue
        if str(x['gameType']) not in ('R','D','F','L','W'):
            raise ValueError('Unexpected final official baseball game type')
        if game in done:
            # If a previous run appended official player rows but crashed
            # before saving the original full boxscore receipt, fetch the
            # fresh Final source again and cross-check exact prior rows.
            # Otherwise older source rows would silently lack evidence.
            if receipt_games is None or game in receipt_games:
                already+=1;continue
        due.append(game)
    return due,{
        'original_frozen_official_player_games':len(groups),
        'final_games_pending_boxscores':len(due),
        'nonfinal_or_not_started_games_deferred':notfinal,
        'already_in_official_player_ledger_deferred':already,
        'game_ids_to_collect':due,
    }

def verified_final_boxscore_player_rows(game_pk,official,fresh_feed,original_boxscore,frozen,*,now):
    if now.tzinfo is None:raise ValueError('Final source arrival time must have timezone')
    gid=int(game_pk)
    if not frozen or int(official['gamePk'])!=gid or official['status']!='Final':
        raise ValueError('Game not authenticated official Final')
    _validate_frozen(frozen)
    feed=fresh_feed.get('gameData') or {}
    if str((feed.get('status') or {}).get('detailedState'))!='Final':
        raise ValueError('Fresh independent MLB live feed does not confirm Final')
    if int((feed.get('game') or {}).get('pk') or -1)!=gid:
        raise ValueError('Official gamePk feed and master identity mismatch')
    if str((feed.get('datetime') or {}).get('officialDate'))!=str(official['officialDate']):
        raise ValueError('Original game official date mismatch')
    start=_utc((feed.get('datetime') or {}).get('dateTime'))
    if (_utc(now)<=start
        or abs((start-_utc(official['gameDate'])).total_seconds())>180
        or abs((start-_utc(frozen[0]['scheduled_first_pitch_utc'])).total_seconds())>180):
        raise ValueError('Original official first pitch disagrees with independent Final feed')
    seen_hitters=set()
    for side in ('home','away'):
        block=(original_boxscore.get('teams') or {}).get(side) or {}
        team=block.get('team') or {}
        if (int(team.get('id') or -1)!=int(official[f'{side}_team_id'])
             or str(team.get('name'))!=str(official[f'{side}_team'])):
            raise ValueError('Original official team identity mismatch in final boxscore')
        for player in (block.get('players') or {}).values():
            pid=(player.get('person') or {}).get('id')
            if pid is None or int(pid)<=0:raise ValueError('Final source has unknown player identity')
            stats=player.get('stats') or {}
            bat=stats.get('batting') or {}
            pit=stats.get('pitching') or {}
            if bat and float(bat.get('plateAppearances') or 0)>0:
                missing=[k for k in HITTER_FIELDS if bat.get(k) is None]
                if missing:raise ValueError(f'Official final source incomplete hitter stat fields: {missing}')
                if not all(np.isfinite(float(bat[k])) and float(bat[k])>=0 for k in HITTER_FIELDS):
                    raise ValueError('Invalid official final hitter stats')
                if float(bat['hits'])>float(bat['atBats']):
                    raise ValueError('Hits exceed official at-bats in boxscore')
                seen_hitters.add(int(pid))
            if pit and (pit.get('inningsPitched') not in (None,'') or float(pit.get('battersFaced') or 0)>0):
                missing=[k for k in PITCHER_FIELDS if pit.get(k) is None]
                if missing:raise ValueError(f'Official final boxscore incomplete pitcher stat fields: {missing}')
    rows=pd.DataFrame(rows_from_box(official,original_boxscore))
    if rows.empty or not seen_hitters:raise ValueError('Official final boxscore empty or incomplete')
    if rows[KEYS].isna().any().any() or rows.duplicated(KEYS).any():
        raise ValueError('Duplicated source Final player game/role identity')
    if set(pd.to_numeric(rows.gamePk).astype(int))!={gid}:
        raise ValueError('Original boxscore official gamePk mismatch')
    athlete_ids={int(x['player_id']) for x in frozen}
    present=athlete_ids&seen_hitters
    raw=json.dumps(original_boxscore,sort_keys=True,separators=(',',':'))
    return rows,{
        'schema':SCHEMA,'game_pk':gid,'official_final_status':'Final',
        'official_date':str(official['officialDate']),
        'verified_first_pitch_utc':start.isoformat(),
        'source_frozen_lineup_players':len(athlete_ids),
        'source_frozen_lineup_players_present_in_hitting_stats':len(present),
        'missing_frozen_hitter_boxscore_records':len(athlete_ids-present),
        'official_player_role_rows':len(rows),
        'source_original_final_boxscore_sha256':hashlib.sha256(raw.encode()).hexdigest(),
        'official_game_counts_as_one_independent_event':True,
        'sportsbook_wins_or_bets_inferred':False,
    }

def append_verified_final_game_once(path,source_rows):
    if source_rows.empty:return 0,{'status':'NO_FINAL_ROWS_TO_APPEND'}
    if source_rows.duplicated(KEYS).any():raise ValueError('Duplicate final source row')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+'.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        known=pd.read_csv(path,low_memory=False) if path.is_file() else pd.DataFrame()
        if not known.empty and known.duplicated(KEYS).any():
            raise ValueError('Duplicate original official ledger rows')
        existing={(int(r.gamePk),int(r.player_id),str(r.group)):r
                  for r in known.itertuples(index=False)}
        pending=[]
        for row in source_rows.to_dict('records'):
            key=(int(row['gamePk']),int(row['player_id']),str(row['group']))
            if key in existing:
                prior=existing[key]
                for field in CHECK_STATS:
                    old=pd.to_numeric(getattr(prior,field,None),errors='coerce')
                    new=pd.to_numeric(row.get(field),errors='coerce')
                    if pd.isna(old) and pd.isna(new):continue
                    if pd.isna(old)!=pd.isna(new) or abs(float(old)-float(new))>1e-6:
                        raise ValueError('Official existing player grade conflicts with updated provider source')
            else:pending.append(row)
        if not pending:return 0,{'status':'ORIGINAL_FINAL_ROWS_IDENTICAL_NO_APPEND'}
        if path.is_file():
            with path.open('r',encoding='utf-8',newline='') as fd:cols=next(csv.reader(fd))
            extras=set(source_rows.columns)-set(cols)
            if extras:raise ValueError(f'Original player ledger cannot append new unexpected columns {sorted(extras)}')
            if path.stat().st_size:
                with path.open('rb') as fd:
                    fd.seek(-1,os.SEEK_END)
                    if fd.read(1)!=b'\n':raise ValueError('Original player ledger trailing record is damaged')
        else:
            cols=list(source_rows.columns)
        with path.open('a',encoding='utf-8',newline='') as fd:
            w=csv.DictWriter(fd,fieldnames=cols,extrasaction='raise')
            if fd.tell()==0:w.writeheader()
            w.writerows(pending)
            fd.flush();os.fsync(fd.fileno())
        return len(pending),{'status':'VERIFIED_FINAL_OFFICIAL_PLAYER_ROWS_APPENDED_PAST_BYTES_PRESERVED',
                             'prior_source_rows_preserved':len(known),'new_player_role_rows':len(pending)}

def bridge_cycle(frozen_file=FROZEN,master_file=MASTER,ledger_file=LEDGER,receipt_file=OUTPUT,
                 *,now=None,original_source_file=ORIGINAL_PREGAME_LINEUPS):
    clock=now or datetime.now(timezone.utc)
    if clock.tzinfo is None:raise ValueError('Offset-aware clock required')
    frozen=_read(frozen_file)
    master=pd.read_csv(master_file,low_memory=False)
    ledger=pd.read_csv(ledger_file,low_memory=False) if ledger_file.is_file() else pd.DataFrame()
    receipt_games={int(x['game_pk']) for x in _read(receipt_file)}
    due,precheck=discover_due_game_pks(
        frozen,master,ledger,now=clock,receipt_games=receipt_games,
    )
    info={
      'schema':SCHEMA,'observed_at_utc':_utc(clock).isoformat(),
      'status':'AWAITING_INDEPENDENT_FINAL_GAME_AND_NEW_OFFICIAL_BOXSCORE',
      'original_frozen_player_sources':len(frozen),
      'official_final_games_with_new_hitter_results':0,
      'new_official_final_player_rows_added':0,
      'independent_game_ids_with_new_verified_boxscore_sources':[],
      'final_precheck':precheck,'network_requests_to_official_mlb_only':0,
      'original_first_pregame_lineups_rewritten':False,
      'betting_play_or_original_model_predictions_unchanged':True,
    }
    if not due:return info
    groups=_validate_frozen(frozen)
    for game in due[:3]:
        verify_original_pregame_source(groups[game],original_source_file)
        if game in receipt_games:
            raise ValueError('Final source previously recorded but original player ledger missing')
        official=master.loc[master.gamePk.eq(game)].iloc[0].to_dict()
        feed_url=f'https://statsapi.mlb.com/api/v1.1/game/{game}/feed/live'
        box_url=f'https://statsapi.mlb.com/api/v1/game/{game}/boxscore'
        def fetch(url):
            r=requests.get(url,timeout=(3,9),
                           headers={'User-Agent':'Sports-Zenith-Final-Research/1.0'})
            r.raise_for_status()
            info['network_requests_to_official_mlb_only']+=1
            return r.json()
        feed=fetch(feed_url)
        if str((feed.get('gameData') or {}).get('status',{}).get('detailedState'))!='Final':
            info['status']='INDEPENDENT_FEED_NOT_YET_FINAL_RETRY_ON_NEXT_REFRESH'
            continue
        box=fetch(box_url)
        source,proof=verified_final_boxscore_player_rows(game,official,feed,box,groups[game],now=clock)
        appended,append_status=append_verified_final_game_once(ledger_file,source)
        receipt={
            **proof,'source_received_utc':_utc(clock).isoformat(),
            'source_official_feed_url':feed_url,
            'source_official_boxscore_url':box_url,
            'source_original_frozen_lineup_sha256':sha_file(original_source_file),
            'source_master_sha256':sha_file(master_file),
            'source_original_final_boxscore_full_payload':box,
            'newly_appended_player_role_rows':appended,
            'previous_official_player_history_preserved':True,
            'actual_stored_sportsbook_wagers_changed':False,
        }
        receipt_file.parent.mkdir(parents=True,exist_ok=True)
        with receipt_file.with_suffix('.jsonl.lock').open('a+b') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            if game in {int(x['game_pk']) for x in _read(receipt_file)}:
                raise ValueError('Final source receipt already stored, refuse changed original result')
            with receipt_file.open('a',encoding='utf-8') as fd:
                fd.write(json.dumps(receipt,sort_keys=True,separators=(',',':'))+'\n')
                fd.flush();os.fsync(fd.fileno())
        info['official_final_games_with_new_hitter_results']+=1
        info['new_official_final_player_rows_added']+=appended
        info['independent_game_ids_with_new_verified_boxscore_sources'].append(game)
    if info['official_final_games_with_new_hitter_results']:
        info['status']='INDEPENDENT_VERIFIED_OFFICIAL_FINAL_PLAYER_SOURCE_APPEND_COMPLETE'
    return info

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--frozen',type=Path,default=FROZEN)
    ap.add_argument('--master',type=Path,default=MASTER)
    ap.add_argument('--ledger',type=Path,default=LEDGER)
    ap.add_argument('--receipts',type=Path,default=OUTPUT)
    a=ap.parse_args()
    if (a.frozen.resolve()!=FROZEN.resolve() or a.master.resolve()!=MASTER.resolve()
        or a.ledger.resolve()!=LEDGER.resolve() or a.receipts.resolve()!=OUTPUT.resolve()):
        raise SystemExit('Refusing unknown official MLB player Final input path')
    result=bridge_cycle()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temp=SUMMARY.with_suffix('.tmp')
    temp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    os.replace(temp,SUMMARY)
    print('MLB_OFFICIAL_PLAYER_FINAL_BRIDGE',json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
