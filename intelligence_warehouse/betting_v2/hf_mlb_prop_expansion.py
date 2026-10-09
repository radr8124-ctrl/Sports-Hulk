"""Bounded read-only HF MLB odds discovery for independent historical research.

Only samples exact paired sportsbook odds at known pregametime. Does not
screen outcomes when choosing quotes, or modify any live betting pipeline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .hf_mlb_prop_pilot import market_implied_probability

SOURCE_REPO = 'SmartStake/mlb-player-props'
MARKETS = ('player hits', 'player bases', 'player rbis', 'player strikeouts')
READ_COLS = ('game_id', 'start_time', 'player', 'market', 'line', 'side', 'book', 'ts', 'odds', 'result', 'won')
PAIR_COLS = ('game_id', 'start_time', 'player', 'market', 'line', 'book', 'ts')
SOURCE_SAMPLING_SEED = 'SPORTS_ZENITH_HF_MLB_PAIRED_PREGAME_V1'


def record_fingerprint(row: dict) -> str:
    fields = ['game_id', 'market', 'player', 'line', 'side', 'book', 'ts']
    identity = '|'.join(str(row.get(k,'')) for k in fields)
    return hashlib.sha256(identity.encode('utf8')).hexdigest()[:24]


def deterministic_side(game_id: object, market: object) -> str:
    content = f'{SOURCE_SAMPLING_SEED}|{game_id}|{market}'
    return ('over', 'under')[hashlib.sha256(content.encode('utf8')).digest()[0] % 2]


def _plain(value):
    if value is None or pd.isna(value):
        return None
    if hasattr(value,'item'):
        try:return value.item()
        except (AttributeError,ValueError):pass
    return value


def choose_exact_paired_quotes(frame: pd.DataFrame, *, min_lead_hours: float=2.0,
                              target_lead_hours: float=6.0) -> list[dict]:
    """One deterministic time-matched pair per game and market in this batch.

    Selection is based strictly on pregame timestamps, event/market identity,
    exact paired prices, and stable source identifiers. The result/won columns
    are never used to choose a quote or source bookmaker.
    """
    if frame.empty or not set(READ_COLS).issubset(frame.columns):
        return []
    d = frame[frame.market.isin(MARKETS)].copy()
    if d.empty:
        return []
    d = d[d.side.isin(('over','under')) & d.game_id.notna() & d.player.notna() & d.book.notna() & d.line.notna()].copy()
    d['odds'] = pd.to_numeric(d['odds'],errors='coerce')
    d['line'] = pd.to_numeric(d['line'],errors='coerce')
    d['_start'] = pd.to_datetime(d['start_time'], errors='coerce',utc=True)
    d['_ts'] = pd.to_datetime(d['ts'],errors='coerce',utc=True)
    d['_lead'] = (d['_start'] - d['_ts']).dt.total_seconds()/3600
    d = d[d['_lead'].between(min_lead_hours,72.0)
          & d['odds'].between(1.000001,1000)
          & d['line'].between(0,1000)
          & d['_start'].notna() & d['_ts'].notna()].copy()
    if d.empty:return []

    # Group both sides of a SAME BOOK+GAME+MARKET+LINE+MINUTE offer; do not
    # infer a counterpart from other bookmakers or neighboring timestamps.
    keys=list(PAIR_COLS)
    # Built-in C-level grouped nunique is far faster than Python lambdas over
    # millions of minute-price groups. Sentinels preserve dropna=False checks.
    d['_result_key'] = d['result'].where(d['result'].notna(), -987654321.0)
    d['_won_key'] = d['won'].astype(object).where(d['won'].notna(), '__MISSING__')
    g=d.groupby(keys+['side'],dropna=False,sort=False).agg(
        odds=('odds','first'),odds_n=('odds','nunique'),
        result=('result','first'),won=('won','first'),
        result_n=('_result_key','nunique'),
        won_n=('_won_key','nunique'),
    ).reset_index()
    g=g[(g.odds_n==1)&(g.result_n<=1)&(g.won_n<=1)]
    if g.empty:return []
    over=g[g.side.eq('over')].drop(columns=['side'])
    under=g[g.side.eq('under')].drop(columns=['side'])
    if over.empty or under.empty:return []
    pairs=over.merge(under,on=keys,how='inner',suffixes=('_over','_under'),validate='one_to_one')
    if pairs.empty:return []
    pairs['_overround']=1/pairs.odds_over+1/pairs.odds_under-1
    pairs=pairs[pairs['_overround'].between(0,0.25)].copy()
    if pairs.empty:return []
    pairs['_lead_hours']=(pd.to_datetime(pairs.start_time,utc=True)-pd.to_datetime(pairs.ts,utc=True)).dt.total_seconds()/3600
    pairs['_distance']=(pairs['_lead_hours']-target_lead_hours).abs()
    # Fixed time target and alphabetical tie-breakers are outcome-blind.
    pairs=pairs.sort_values(['game_id','market','_distance','book','player','line','ts'])
    pairs=pairs.drop_duplicates(['game_id','market'],keep='first')
    chosen=[]
    for _,r in pairs.iterrows():
        side=deterministic_side(r.game_id,r.market)
        event_start=pd.Timestamp(r.start_time).isoformat()
        capture=pd.Timestamp(r.ts).isoformat()
        outcome=_plain(r['won_'+side]);result=_plain(r['result_'+side])
        odds={'over':float(r.odds_over),'under':float(r.odds_under)}
        entry={
            'game_id':str(r.game_id),
            'start_time':event_start,
            'player':str(r.player),
            'market':str(r.market),
            'line':float(r.line),
            'side':side,
            'book':str(r.book),
            'ts':capture,
            'odds':odds[side],
            'result':result,
            'won':outcome,
            'pair_status':'PAIRED_AT_SAME_BOOK_AND_TIME',
            'lead_time_hours':round(float(r._lead_hours),4),
            'pair_overround':round(float(r._overround),8),
            'paired_offers':[
                { 'game_id':str(r.game_id),'player':str(r.player),
                  'market':str(r.market),'line':float(r.line),'book':str(r.book),
                  'ts':capture,'side':name,'odds':odds[name] }
                for name in ('over','under')
            ],
            'sampling_rule':'ONE_PAIR_PER_PROVIDER_GAME_MARKET_CLOSEST_TO_MINUS_6_HOURS_UNFILTERED_BY_RESULT',
        }
        entry['quote_fingerprint']=record_fingerprint(entry)
        chosen.append(entry)
    return chosen


def group_indices(num_groups: int, samples_per_shard: int) -> list[int]:
    if not 1<=samples_per_shard<=num_groups:
        raise ValueError('samples_per_shard must be between 1 and num_groups')
    return sorted(set(round(i*(num_groups-1)/(samples_per_shard-1)) for i in range(samples_per_shard))) if samples_per_shard>1 else [0]


def sample_shards(paths: list[Path], *, groups_per_shard: int=36) -> tuple[list[dict],dict]:
    all_candidates:dict[tuple,str]={}
    progress=[]
    groups_processed=0
    for p in paths:
        parq=pq.ParquetFile(p)
        ix=group_indices(parq.metadata.num_row_groups,groups_per_shard)
        shard_candidates=0
        for index in ix:
            data=parq.read_row_group(index,columns=list(READ_COLS)).to_pandas()
            rows=choose_exact_paired_quotes(data)
            groups_processed+=1
            for row in rows:
                row['source_shard']=p.name
                row['source_row_group']=index
                key=(row['game_id'],row['market'])
                distance=abs(row['lead_time_hours']-6)
                if key not in all_candidates or (distance,row['book'],row['quote_fingerprint'])<(
                    abs(all_candidates[key]['lead_time_hours']-6),all_candidates[key]['book'],all_candidates[key]['quote_fingerprint']):
                    all_candidates[key]=row
                    shard_candidates+=1
            del data
        progress.append({'source_shard':p.name,'total_row_groups':parq.metadata.num_row_groups,'sampled_row_groups':len(ix),'shard_compressed_bytes':p.stat().st_size,'sampled_candidate_insertions':shard_candidates})
        print('SHARD_PROGRESS',json.dumps(progress[-1]),'TOTAL_DISTINCT_GAME_MARKETS',len(all_candidates),flush=True)
        parq.close()
    rows=sorted(all_candidates.values(),key=lambda x:(x['start_time'],x['game_id'],x['market']))
    for idx,row in enumerate(rows):
        row['sample_index']=idx
    manifest={
        'dataset':SOURCE_REPO,'source_url':'https://huggingface.co/datasets/SmartStake/mlb-player-props',
        'selection_seed':SOURCE_SAMPLING_SEED,
        'selection_method':'Evenly spaced parquet row groups, one exact paired quote per provider game and market closest to 6hr prestart, stable alphabetical tie break; side selected by fixed hash, never by result.',
        'source_license_claim':'Dataset card CC-BY-4.0; upstream rights unverified',
        'num_parquet_shards_examined':len(paths),
        'groups_sampled':groups_processed,
        'source_shards':progress,
        'paired_provider_game_market_candidates':len(rows),
        'source_distinct_provider_games':len({r['game_id'] for r in rows}),
        'markets':dict(Counter(r['market'] for r in rows)),
        'forbidden_live_import':True,
    }
    return rows,manifest


def main():
    ap=argparse.ArgumentParser(description='Bounded paired-odds research sampling across public HF shards')
    ap.add_argument('--input-shard',action='append',required=True,type=Path)
    ap.add_argument('--groups-per-shard',type=int,default=36)
    ap.add_argument('--output-dir',required=True,type=Path)
    args=ap.parse_args()
    if any(n in args.output_dir.parts for n in ('commercial_web','public','decision','latest')):
        raise SystemExit('Refusing to write to any live output folder')
    rows,manifest=sample_shards(args.input_shard,groups_per_shard=args.groups_per_shard)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/'source_candidates.json').write_text(json.dumps(rows,indent=2,default=str)+'\n')
    (args.output_dir/'discovery_manifest.json').write_text(json.dumps(manifest,indent=2,default=str)+'\n')
    print('SOURCE_EXPANSION_SUMMARY',json.dumps(manifest),flush=True)

if __name__=='__main__':main()
