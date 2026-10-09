"""Freeze real pre-kickoff same-book two-sided MLB prop prices as market baselines.

Strictly retrospective research evidence, NOT price offers or executable bets.
Explicit source: original official MLB lineup + V2 source-time player features +
official MLBAM player identity in existing game/prop fusion +
provider's named UUID in two genuine sportsbook prices on the SAME line,
book, event, provider, and capture instant. Any cross-book or cross-line de-vig
is refused. Quotes and source receipts are immutable after first acceptance.
"""
from __future__ import annotations

from collections import Counter,defaultdict
from datetime import datetime,timezone
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import unicodedata

import numpy as np
import pandas as pd

from .mlb_asof_feature_store import ROOT,sha_file
from .mlb_live_research_feature_freeze_v2 import (
    OUTPUT as FROZEN_V2,SCHEMA as FROZEN_SCHEMA,REVISION as FROZEN_REVISION,
)
from .mlb_research_forward_labels import (
    ORIGINAL_PREGAME_LINEUPS,
    verify_original_pregame_source,
)

OUTPUT=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V2_PREGAME_SAME_BOOK_FAIR_PRICE_BASELINES.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V2_PREGAME_FAIR_PRICE_BASELINE_SUMMARY.json'
FUSION=ROOT/'mlb_live/markets/current/MLB_PROP_FUSION.csv'
MARKET_HISTORY=ROOT/'mlb_live/markets/history'
SCHEMA='MLB_V2_PREGAME_SAME_BOOK_FAIR_PRICE_BASELINE_V1'
SOURCE_SCHEMA='MLB_PREGAME_SOURCE_EVIDENCE_V1'
METRIC={'PLAYER_TOTAL_HITS':'hits','PLAYER_TOTAL_BATTER_WALKS':'walks',
        'PLAYER_TOTAL_TOTAL_BASES':'total_bases','PLAYER_TOTAL_STOLEN_BASES':'stolen_bases'}
MAX_QUOTE_AGE_MINUTES=90
EXPECTED_FUSION_FIELDS={
    'event_id','start','away_team','home_team','player_id','player','team','market_subtype',
}
EXPECTED_QUOTE_FIELDS={
    'provider','sportsbook','event_id','start','away_team','home_team','market_subtype',
    'side','line','price_american','player_id','player','captured_at',
}


def _utc(value:object)->pd.Timestamp:
    time=pd.to_datetime(value,utc=True,errors='coerce')
    if pd.isna(time):
        raise ValueError('Invalid or missing source timestamp')
    return time


def _name(value:object)->str:
    txt=unicodedata.normalize('NFKD',str(value or '')).encode('ascii','ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]','',txt.lower())


def _american_odds_probability(value)->float|None:
    try:
        odds=float(value)
    except (ValueError,TypeError):
        return None
    if not np.isfinite(odds) or odds==0 or abs(odds)<100 or abs(odds)>10000:
        return None
    return 100/(odds+100) if odds>0 else (-odds)/((-odds)+100)


def _official_player_map(original:dict,frozen:list[dict],now:datetime)->dict[int,dict]:
    if now.tzinfo is None:raise ValueError('Research time must include timezone')
    try:
        captured=_utc(original.get('captured_at_utc'))
        start=_utc(original.get('first_pitch_utc'))
    except ValueError:return {}
    if original.get('schema')!=SOURCE_SCHEMA or not original.get('evidence_id') or not original.get('game_pk'):
        return {}
    if captured>=start or _utc(now)>=start or captured>_utc(now):
        return {}
    fx=original.get('fixture') or {}
    if str(fx.get('official_status_at_capture','')).upper() not in ('SCHEDULED','PRE-GAME','WARMUP','PRE-GAME WARMUP'):
        return {}
    people={}
    lineup=original.get('lineups') or {}
    if lineup.get('status') not in ('ONLY_ONE_TEAM_LINEUP_VISIBLE_PREGAME','OFFICIAL_BATTING_ORDER_VISIBLE_BEFORE_KICKOFF'):
        return {}
    for side in ('home','away'):
        sideinfo=lineup.get(side)
        if not isinstance(sideinfo,dict):continue
        ids=sideinfo.get('player_ids') or []
        names=sideinfo.get('player_names') or []
        if not (len(ids)==len(names)==9 and len(set(map(str,ids)))==9 and
                sideinfo.get('source')=='LIVE_FEED_OFFICIAL_BATTING_ORDER_CAPTURED_PREGAME' and
                sideinfo.get('confirmed_asof_capture') is True):
            return {}
        for pid,player in zip(ids,names):
            try:pid=int(pid)
            except (TypeError,ValueError):return {}
            if pid<=0 or pid in people or not _name(player):
                return {}
            people[pid]={
                'player_name_official':str(player),
                'normalized_name':_name(player),
                'team_side':side,
                'team_name':fx.get(f'{side}_team'),
            }
    authorized={}
    seen=set()
    for source in frozen:
        if source.get('schema')!=FROZEN_SCHEMA or source.get('source_history_revision')!=FROZEN_REVISION:
            raise ValueError('Unrecognized frozen V2 source in market baseline pairing')
        if source.get('live_play_approved') is not False or source.get('betting_prediction_written') is not False:
            raise ValueError('A frozen research feature must not assert an approved betting pick')
        try:
            pid=int(source['player_id'])
        except (ValueError,KeyError,TypeError):
            raise ValueError('Missing original official player ID') from None
        key=(int(source['game_pk']),pid)
        if key in seen:
            raise ValueError('Duplicate frozen official MLB game/player identity')
        seen.add(key)
        if key[0]!=int(original['game_pk']) or pid not in people:
            continue
        if (
            source.get('source_evidence_id')!=original.get('evidence_id') or
            source.get('team_side_at_capture')!=people[pid]['team_side'] or
            _utc(source['source_capture_at_utc'])!=captured or
            _utc(source['feature_frozen_at_utc'])>=start or
            _utc(source['scheduled_first_pitch_utc'])!=start
        ):
            continue
        authorized[pid]={**people[pid],'original_pregame_evidence_id':source['source_evidence_id'],
                         'source_frozen_feature_at_utc':source['feature_frozen_at_utc'],
                         'original_lineup_source_line_sha256':source.get('original_append_only_line_sha256')}
    return authorized


def select_paired_market_sources(
    original:dict,frozen:list[dict],fusion:pd.DataFrame,raw_market:pd.DataFrame,*,now:datetime,
    source_file_sha256:str,fusion_file_sha256:str,
)->tuple[list[dict],dict]:
    if now.tzinfo is None:raise ValueError('Truthful timestamp-aware market snapshot time required')
    if not source_file_sha256 or not fusion_file_sha256:
        raise ValueError('Original provider source and player fusion SHA256 required')
    start=_utc(original.get('first_pitch_utc'))
    if _utc(now)>=start:
        return [],{'eligible_pairs':0,'independent_games_with_qualifying_source_pairs':0,
                   'reason':'GAME_STARTED_BEFORE_SOURCE_FREEZE'}
    if not EXPECTED_FUSION_FIELDS.issubset(fusion.columns) or not EXPECTED_QUOTE_FIELDS.issubset(raw_market.columns):
        raise ValueError('Incomplete original provider market or MLBAM fusion schema')
    people=_official_player_map(original,frozen,now)
    if not people:
        return [],{'eligible_pairs':0,'independent_games_with_qualifying_source_pairs':0,
                   'reason':'NO_VERIFIED_SOURCE_LINEUP_AND_FROZEN_PLAYER_CROSSWALK'}
    fx=original['fixture']
    roster={}
    # Prop fusion provides the official numeric player ID; market raw supplies
    # a DIFFERENT provider UUID. Never guess UUID from the MLBAM digits alone.
    for f in fusion[['event_id','start','away_team','home_team','player_id','player','team','market_subtype']].drop_duplicates().itertuples(index=False):
        try:
            pid=int(f.player_id)
            fixture=_utc(f.start)
        except (ValueError,TypeError):
            continue
        if pid not in people or abs((fixture-start).total_seconds())>180:
            continue
        official=people[pid]
        if (
            f.away_team!=fx.get('away_team') or f.home_team!=fx.get('home_team')
            or f.team!=official['team_name'] or _name(f.player)!=official['normalized_name']
            or f.market_subtype not in METRIC
        ):
            continue
        id_=(str(f.event_id),official['normalized_name'],f.market_subtype)
        if id_ in roster and roster[id_]['player_id']!=pid:
            raise ValueError('Ambiguous official MLBAM player ID for same quote identity')
        roster[id_]={'player_id':pid,**official}
    rows=raw_market.copy()
    rows['side']=rows.side.astype(str).str.upper()
    rows=rows[rows.side.isin(['OVER','UNDER']) & rows.market_subtype.isin(METRIC)].copy()
    rows['_name_key']=rows.player.map(_name)
    rows['line']=pd.to_numeric(rows.line,errors='coerce')
    # Raw timestamps must be original provider captured_at, NOT file mtime.
    rows['_quote_time']=pd.to_datetime(rows.captured_at,utc=True,errors='coerce')
    rows['_start_time']=pd.to_datetime(rows.start,utc=True,errors='coerce')
    captured=_utc(now)
    rows=rows[
        rows._quote_time.notna() & rows._start_time.notna()
        & rows._quote_time.le(captured)
        & rows._quote_time.lt(start)
        & rows._quote_time.ge(captured-pd.Timedelta(minutes=MAX_QUOTE_AGE_MINUTES))
        & ((rows._start_time-start).abs().dt.total_seconds()<=180)
        & rows.line.notna()
        & rows.line.ge(0)
        & rows.away_team.eq(fx.get('away_team'))
        & rows.home_team.eq(fx.get('home_team'))
        & rows.provider.astype(str).str.len().gt(0)
        & rows.sportsbook.astype(str).str.len().gt(0)
    ].copy()
    key=['provider','sportsbook','event_id','_name_key','player_id',
         'market_subtype','line','captured_at']
    if rows.duplicated(key+['side']).any():
        raise ValueError('Duplicate same-book exact-market side in original quote snapshot')
    generated=[]
    totals=Counter()
    for values,book_rows in rows.groupby(key,dropna=False,sort=False):
        provider,book,event_id,normalized,uuid,market,line,source_time=values
        mapped=roster.get((str(event_id),str(normalized),str(market)))
        if mapped is None:
            totals['no_official_identity_crosswalk']+=1
            continue
        if set(book_rows.side)!={'OVER','UNDER'} or len(book_rows)!=2:
            totals['not_pairable_same_book_time_line']+=1
            continue
        paired={side:book_rows.loc[book_rows.side.eq(side)].iloc[0] for side in ('OVER','UNDER')}
        over=_american_odds_probability(paired['OVER'].price_american)
        under=_american_odds_probability(paired['UNDER'].price_american)
        if over is None or under is None:
            totals['invalid_american_price']+=1
            continue
        overround=over+under
        if not 1<overround<=1.25:
            totals['implausible_overround']+=1
            continue
        # Official sportsbook sources can disagree with a provider selection
        # text: each side must be explicitly over/under its displayed line.
        if any(str(paired[side].player_id)!=str(uuid) or
               _name(paired[side].player)!=normalized
               for side in ('OVER','UNDER')):
            totals['provider_player_uuid_or_name_conflict']+=1
            continue
        if source_time is None or not source_time:
            totals['missing_source_quote_time']+=1
            continue
        q=_utc(source_time)
        if q< _utc(mapped['source_frozen_feature_at_utc']):
            # A price originally published before the observed lineup may
            # be valid research but not contemporaneously matched with
            # this proof; do not backdate lineup information.
            totals['price_predates_verified_lineup_freeze']+=1
            continue
        pid=mapped['player_id']
        record={
            'schema':SCHEMA,
            'official_game_pk':int(original['game_pk']),
            'mlbam_player_id':pid,
            'player_name_official':mapped['player_name_official'],
            'player_name_provider':str(paired['OVER'].player),
            'player_team':mapped['team_name'],
            'provider_player_id':str(uuid),
            'provider_event_id':str(event_id),
            'provider':str(provider),
            'sportsbook':str(book),
            'market_subtype':str(market),
            'market_metric':METRIC[market],
            'line':float(line),
            'price_over_american':float(paired['OVER'].price_american),
            'price_under_american':float(paired['UNDER'].price_american),
            'book_implied_over':round(float(over),12),
            'book_implied_under':round(float(under),12),
            'book_overround':round(float(overround),12),
            'market_fair_probability_over':round(float(over/overround),12),
            'market_fair_probability_under':round(float(under/overround),12),
            'source_snapshot_quote_at_utc':q.isoformat(),
            'source_market_provenance':'ORIGINAL_TWO_SIDED_SAME_PROVIDER_BOOK_EVENT_PLAYER_LINE_AND_CAPTURE_TIME',
            'quote_captured_before_first_pitch':True,
            'original_lineup_source_line_sha256':mapped['original_lineup_source_line_sha256'],
            'original_frozen_lineup_feature_at_utc':str(mapped['source_frozen_feature_at_utc']),
            'original_pregame_evidence_id':mapped['original_pregame_evidence_id'],
            'fixture_scheduled_start_utc':start.isoformat(),
            'source_raw_market_csv_sha256':source_file_sha256,
            'source_mlbam_fusion_csv_sha256':fusion_file_sha256,
            'prediction_probability_not_estimated':True,
            'model_prediction_created':False,
            'betting_selection_approved':False,
            'wager_executed':False,
            'sportsbook_settlement_claimed':False,
            'commercial_market_redistribution_approved':False,
            'independent_game_evidence_key':str(int(original['game_pk'])),
            'per_quote_is_independent_game_proof':False,
            'over_provider_source_row':{
                col: (float(paired['OVER'][col]) if col in ('line','price_american')
                      else str(paired['OVER'][col]))
                for col in sorted(EXPECTED_QUOTE_FIELDS)
            },
            'under_provider_source_row':{
                col: (float(paired['UNDER'][col]) if col in ('line','price_american')
                      else str(paired['UNDER'][col]))
                for col in sorted(EXPECTED_QUOTE_FIELDS)
            },
            'product_eligible_for_profit_claim':False,
        }
        generated.append(record)
    generated.sort(key=lambda x:(x['official_game_pk'],x['mlbam_player_id'],x['market_subtype'],
                                 x['sportsbook'],x['line'],x['source_snapshot_quote_at_utc']))
    return generated,{
        'eligible_pairs':len(generated),
        'independent_games_with_qualifying_source_pairs':len({x['official_game_pk'] for x in generated}),
        'verified_official_lineup_players':len(people),
        'eligible_players_quoted':len({x['mlbam_player_id'] for x in generated}),
        'same_book_market_pairs_by_type':dict(Counter(x['market_metric'] for x in generated)),
        'bookmakers_by_name':dict(Counter(x['sportsbook'] for x in generated)),
        'source_rejected':dict(totals),
        'status':'SOURCE_ONLY_NO_MODEL_EDGE_CLAIM',
    }


def _first_quote_key(row:dict)->tuple:
    return (
        int(row['official_game_pk']),int(row['mlbam_player_id']),
        str(row['provider']),str(row['sportsbook']),
        str(row['market_subtype']),float(row['line']),
    )


def append_verified_paired_baselines(path:Path,records:list[dict])->int:
    if not records:return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+'.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        seen={}
        if path.exists():
            with path.open('r',encoding='utf-8') as f:
                for line in f:
                    if not line.strip():continue
                    existing=json.loads(line)
                    if existing.get('schema')!=SCHEMA:
                        raise ValueError('Foreign or invalid paired market baseline ledger')
                    key=_first_quote_key(existing)
                    if key in seen:raise ValueError('Duplicated prior immutable market baseline identity')
                    seen[key]=existing
        new=[];batch=set()
        for r in records:
            if (
                r.get('schema')!=SCHEMA or
                r.get('betting_selection_approved') is not False or
                r.get('model_prediction_created') is not False or
                _utc(r['source_snapshot_quote_at_utc'])>=_utc(r['fixture_scheduled_start_utc'])
            ):
                raise ValueError('Not an eligible pregame research-only market quote')
            key=_first_quote_key(r)
            if key in batch:
                raise ValueError('Duplicate batch member for same original paired price baseline')
            batch.add(key)
            if key in seen:continue
            new.append(r)
            seen[key]=r
        if new:
            with path.open('a',encoding='utf-8') as f:
                for r in new:
                    f.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
                f.flush();os.fsync(f.fileno())
        return len(new)


def _read_jsonl(path:Path)->list[dict]:
    if not path.is_file():raise ValueError('Missing authentic immutable original research evidence')
    rows=[]
    with path.open('r',encoding='utf-8') as f:
        for line in f:
            if line.strip():rows.append(json.loads(line))
    return rows


def freeze_market_cycle(
    original_ledger:Path=ORIGINAL_PREGAME_LINEUPS,
    frozen_ledger:Path=FROZEN_V2,
    fusion_file:Path=FUSION,
    market_source_file:Path|None=None,
    output:Path=OUTPUT,
    *,now:datetime|None=None,
)->dict:
    current=now or datetime.now(timezone.utc)
    if current.tzinfo is None:raise ValueError('Source time must be offset-aware')
    if market_source_file is None:
        sources=sorted(MARKET_HISTORY.glob('MLB_PLAYER_PROP_MARKET_*.csv'))
        if not sources:
            raise ValueError('No original historical time-stamped sportsbook source available')
        market_source_file=sources[-1]
    if not market_source_file.is_file():
        raise ValueError('Missing original provider player market snapshot')
    original_lines={}
    with original_ledger.open('r',encoding='utf-8') as src:
        for line in src:
            if line.strip():
                digest=hashlib.sha256(line.encode()).hexdigest()
                if digest in original_lines:
                    raise ValueError('Duplicate original MLB schedule/lineup raw source line')
                original_lines[digest]=json.loads(line)
    frozen=_read_jsonl(frozen_ledger)
    by_source=defaultdict(list)
    for r in frozen:
        digest=r.get('original_append_only_line_sha256')
        if not digest or digest not in original_lines:
            raise ValueError('Frozen official lineup referenced a missing original source hash')
        by_source[digest].append(r)
    if not by_source:
        return {
            'schema':SCHEMA,'ran_at_utc':_utc(current).isoformat(),
            'market_baseline_pairs_frozen':0,'independent_game_ids':0,
            'source_status':'NO_FROZEN_OFFICIAL_PREGAME_LINES',
            'paid_bets_approved':False,'model_fitted_or_promoted':False,
        }
    fusion=pd.read_csv(fusion_file,low_memory=False)
    raw=pd.read_csv(market_source_file,low_memory=False)
    previously=[]
    if output.is_file():
        previously=_read_jsonl(output)
    prior_identifiers={_first_quote_key(x) for x in previously}
    candidates=[]
    receipts=[]
    for digest,records in by_source.items():
        # Use the exact verified original source, never a substitute current
        # lineup or inferred official player ID.
        verify_original_pregame_source(records,original_ledger)
        originals=original_lines[digest]
        rows,info=select_paired_market_sources(
            originals,records,fusion,raw,now=current,
            source_file_sha256=sha_file(market_source_file),
            fusion_file_sha256=sha_file(fusion_file),
        )
        candidates.extend(rows)
        receipts.append(info)
    # When source collector stored multiple lineup versions, the game's
    # player was originally frozen only once; repeat market paired sources
    # for the same independently matched game/book/player are not new games.
    new_count=append_verified_paired_baselines(output,candidates)
    after=_read_jsonl(output) if output.is_file() else []
    return {
        'schema':SCHEMA,
        'ran_at_utc':_utc(current).isoformat(),
        'source_market_snapshot_path':str(market_source_file.relative_to(ROOT))
             if market_source_file.is_relative_to(ROOT) else str(market_source_file),
        'source_market_snapshot_sha256':sha_file(market_source_file),
        'source_fusion_sha256':sha_file(fusion_file),
        'source_lineup_sha256':sha_file(original_ledger),
        'source_frozen_research_sha256':sha_file(frozen_ledger),
        'original_source_verified_groups':len(by_source),
        'source_eligible_pairs_this_check':len(candidates),
        'market_baseline_pairs_frozen':new_count,
        'total_frozen_first_eligible_book_line_baselines':len(after),
        'previously_frozen_market_lines_preserved':len(prior_identifiers),
        'independent_game_ids':len({x['official_game_pk'] for x in after}),
        'actual_games_with_market_probability_predictions':0,
        'source_matched_player_baselines':len({(x['official_game_pk'],x['mlbam_player_id']) for x in after}),
        'paired_book_source_checks':receipts,
        'source_rights_for_public_redistribution_verification_pending':True,
        'paid_bets_approved':False,
        'model_fitted_or_promoted':False,
        'wager_or_payout_record_created':False,
    }


def main():
    ap=argparse.ArgumentParser(description='Freeze source-backed MLB real paired book baseline, no betting picks')
    ap.add_argument('--source',type=Path,default=ORIGINAL_PREGAME_LINEUPS)
    ap.add_argument('--frozen',type=Path,default=FROZEN_V2)
    ap.add_argument('--fusion',type=Path,default=FUSION)
    ap.add_argument('--market-source',type=Path)
    ap.add_argument('--output',type=Path,default=OUTPUT)
    args=ap.parse_args()
    if (
        args.source.resolve()!=ORIGINAL_PREGAME_LINEUPS.resolve() or
        args.frozen.resolve()!=FROZEN_V2.resolve() or
        args.fusion.resolve()!=FUSION.resolve() or
        args.output.resolve()!=OUTPUT.resolve()
    ):
        raise SystemExit('Refusing mismatched original source paths outside verified private MLB research lane')
    if args.market_source and args.market_source.resolve().parent!=MARKET_HISTORY.resolve():
        raise SystemExit('Refusing noncanonical market snapshot location')
    result=freeze_market_cycle(args.source,args.frozen,args.fusion,args.market_source,args.output)
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temp=SUMMARY.with_suffix('.tmp')
    temp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    os.replace(temp,SUMMARY)
    print('MLB_SOURCE_VERIFIED_PAIRED_BOOK_RESEARCH',json.dumps({
        k:v for k,v in result.items() if k not in ('paired_book_source_checks',)
    },sort_keys=True))


if __name__=='__main__':
    main()
