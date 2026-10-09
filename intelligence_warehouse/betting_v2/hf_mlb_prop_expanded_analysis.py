"""Bounded independent-MLB-game historical research, isolated from live betting.

Source is a deterministic research-only subset of public HF parquet odds,
not original Sports HULK frozen pregame recommendations.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pandas as pd

from .hf_mlb_prop_pilot import ROOT, MARKETS as SOURCE_MARKETS, REQUIRED_OFFICIAL_COLUMNS, audit_rows
from .hf_mlb_prop_asof import enrich_strictly_pregame
from .hf_mlb_prop_pairing import evaluate_exact_quote_pair
from .hf_mlb_prop_fair_lane import evaluate_fair_price_lane
from .hf_mlb_prop_expansion import MARKETS as STUDIED_MARKETS
from .hf_mlb_prop_official_derived import derive_missing_vendor_outcomes

ROOT_OUTPUT = ROOT / 'reports'


def analyze_expanded_samples(candidates: list[dict], official_history:pd.DataFrame, *, run_model_comparisons:bool=True, allow_official_derivation:bool=False) -> dict:
    if not candidates or len(candidates)>3000:
        raise ValueError('Expected bounded list of 1..3000 external source rows')
    seen=set()
    for row in candidates:
        i=row.get('sample_index')
        if i is None or i in seen:
            raise ValueError('Every candidate must have its own unique sample_index')
        seen.add(i)
        if row.get('pair_status')!='PAIRED_AT_SAME_BOOK_AND_TIME' or not isinstance(row.get('paired_offers'),list):
            raise ValueError('Source must have timestamp-matched candidate paired offers')
    official=official_history.copy()
    audit=audit_rows(candidates,official)
    if allow_official_derivation:
        audit=derive_missing_vendor_outcomes(audit,official)
    source_by_index={r['sample_index']:r for r in candidates}
    for row in audit:
        pair={'status':'OFFICIAL_IDENTITY_OR_RESULT_NOT_VERIFIED'}
        if row.get('status') in ('VERIFIED_HISTORICAL','OFFICIAL_DERIVED_HISTORICAL'):
            source=source_by_index[row['sample_index']]
            pair=evaluate_exact_quote_pair(row,source['paired_offers'])
        row['pair_status']=pair['status']
        if pair['status']=='VERIFIED_SAME_BOOK_TIME_PAIR':
            row['market_fair_probability']=pair['fair_probability']
            row['paired_overround']=pair['overround']
            row['paired_raw_probability']=pair['raw_implied_probability']
            row['market_reference_type']='SAME_BOOK_SAME_MINUTE_DEVIG_FAIR'
            row['quote_fingerprint']=source_by_index[row['sample_index']].get('quote_fingerprint')
        else:
            row['market_reference_type']='UNVERIFIED_NO_PAIRED_FAIR_PRICE'
    asof=enrich_strictly_pregame(audit,official)
    fully_verified=[r for r in asof if r.get('status') in ('VERIFIED_HISTORICAL','OFFICIAL_DERIVED_HISTORICAL')
                    and r.get('pair_status')=='VERIFIED_SAME_BOOK_TIME_PAIR'
                    and r.get('asof_status')=='PREGAME_FEATURE_VERIFIED']
    if not all(r['timestamp_before_official_start'] for r in fully_verified):
        raise RuntimeError('A post-start quote escaped the historical validator')
    fair_lane=({market:evaluate_fair_price_lane([r for r in asof if r.get('market')==market]) for market in STUDIED_MARKETS}
               if run_model_comparisons else {})
    summary={
        'status':'RESEARCH_AUDIT_COMPLETE_NOT_LIVE_BETTING_PROOF',
        'source':'SmartStake/mlb-player-props',
        'source_rows':len(candidates),
        'distinct_source_game_ids':len({r.get('game_id') for r in candidates}),
        'source_candidates_by_market':dict(Counter(str(r.get('market')) for r in candidates)),
        'official_derived_analytical_grades':sum(r.get('status')=='OFFICIAL_DERIVED_HISTORICAL' for r in audit),
        'audit_status_counts':dict(Counter(r.get('status') for r in audit)),
        'pair_status_counts':dict(Counter(r.get('pair_status') for r in audit)),
        'asof_status_counts':dict(Counter(r.get('asof_status') for r in asof)),
        'verified_official_game_count':len({r['official_game_pk'] for r in audit if r.get('status') in ('VERIFIED_HISTORICAL','OFFICIAL_DERIVED_HISTORICAL')}),
        'verified_grade_and_pair_games':len({r['official_game_pk'] for r in audit if r.get('status') in ('VERIFIED_HISTORICAL','OFFICIAL_DERIVED_HISTORICAL') and r['pair_status']=='VERIFIED_SAME_BOOK_TIME_PAIR'}),
        'asof_feature_games':len({r['official_game_pk'] for r in fully_verified}),
        'fully_verified_rows':len(fully_verified),
        'fully_verified_by_market':dict(Counter(r['market'] for r in fully_verified)),
        'fully_verified_distinct_games_by_market':{market:len({r['official_game_pk'] for r in fully_verified if r['market']==market}) for market in STUDIED_MARKETS},
        'quote_selection':'RESULT_BLIND_6_HOUR_TARGET_EXACT_PAIR_BY_HASHED_SIDE',
        'primary_grade_source':'OFFICIAL_MLB_STATSAPI_BOXSCORE_ARCHIVE',
        'probability_source':'SAME_BOOK_SAME_MINUTE_FAIR_PROBABILITY',
        'historical_scope':'EXTERNAL_HISTORICAL_BACKTEST_NO_ORIGINAL_HULK_FROZEN_PICKS',
        'commercial_source_rights':'UNVERIFIED_UPSTREAM_BOOKMAKER_LICENSE',
        'live_decisions_changed':False,
        'live_forward_ledgers_changed':False,
    }
    return {'summary':summary,'audit':audit,'asof':asof,'fair_lane':fair_lane}


def run(source_manifest:Path,out:Path) -> dict:
    if 'reports' not in out.parts or any(part in out.parts for part in ('commercial_web','public','decision','latest')):
        raise ValueError('Research output must remain under reports; never a live model folder')
    if source_manifest.stat().st_size>6*1024*1024:
        raise ValueError('Refusing an unbounded source candidate manifest')
    candidates=json.loads(source_manifest.read_text())
    if not isinstance(candidates,list):raise ValueError('Source candidate manifest must contain a list')
    cols=sorted(set(REQUIRED_OFFICIAL_COLUMNS)|{'player_id','plate_appearances','outs'})
    official=pd.read_csv(ROOT/'intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_HISTORY.csv',usecols=cols,low_memory=False)
    result=analyze_expanded_samples(candidates,official)
    summary=result['summary']
    summary['generated_at']=datetime.now(timezone.utc).isoformat()
    summary['input_manifest_sha256']=hashlib.sha256(source_manifest.read_bytes()).hexdigest()
    out.mkdir(parents=True,exist_ok=True)
    for name,rows in [('official_audit.json',result['audit']),('asof_audit.json',result['asof']),('fair_lane_results.json',result['fair_lane']),('summary.json',summary)]:
        (out/name).write_text(json.dumps(rows,indent=2,default=str)+'\n')
    print(json.dumps({'summary':summary,'fair_lane':result['fair_lane']},indent=2))
    return result


def main():
    ap=argparse.ArgumentParser(description='Read-only external historical MLB odds x official boxscore x fair-price audit')
    ap.add_argument('--source-candidates',type=Path,required=True)
    ap.add_argument('--output-dir',type=Path,required=True)
    args=ap.parse_args()
    run(args.source_candidates,args.output_dir)

if __name__=='__main__':main()
