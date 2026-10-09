"""Research-only official adjudication of a *new* shard against frozen weights.

Does not train, select a winning model, or alter the historical originals.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path

import pandas as pd

from .hf_mlb_prop_pilot import ROOT,REQUIRED_OFFICIAL_COLUMNS
from .hf_mlb_prop_expanded_analysis import analyze_expanded_samples
from .hf_mlb_prop_locked_holdout import evaluate_new_shard_holdout


def audit_unseen_shard(frozen:dict,source_rows:list[dict],official_history:pd.DataFrame) -> dict:
    source_id=frozen.get('new_source_shard_reserved')
    observed={r.get('source_shard') for r in source_rows}
    if source_id and observed!={source_id}:
        raise ValueError(f'Unexpected source shard {observed}, locked manifest requires {source_id}')
    audited=analyze_expanded_samples(source_rows,official_history,run_model_comparisons=False,allow_official_derivation=True)
    asof=audited['asof']
    valid_hits=[r for r in asof if r.get('market')=='player hits' and r.get('status') in ('VERIFIED_HISTORICAL','OFFICIAL_DERIVED_HISTORICAL')
                and r.get('pair_status')=='VERIFIED_SAME_BOOK_TIME_PAIR'
                and r.get('asof_status')=='PREGAME_FEATURE_VERIFIED'
                and r.get('official_start')>frozen['train_last_start']
                and r.get('official_game_pk') not in set(frozen['train_official_game_pks'])]
    locked=evaluate_new_shard_holdout(frozen,asof)
    return {
        'summary': {
            'status':'SEALED_SHARD_OFFICIAL_AUDIT_COMPLETE',
            'source_rows':len(source_rows),
            'provider_game_ids':len({r.get('game_id') for r in source_rows}),
            'officially_verified_records':len([r for r in asof if r.get('status') in ('VERIFIED_HISTORICAL','OFFICIAL_DERIVED_HISTORICAL')]),
            'vendor_supplied_grade_count':sum(r.get('status')=='VERIFIED_HISTORICAL' for r in asof),
            'official_derived_only_grade_count':sum(r.get('status')=='OFFICIAL_DERIVED_HISTORICAL' for r in asof),
            'provider_settlement_claim':False,
            'officially_verified_independent_games':audited['summary']['verified_official_game_count'],
            'source_status_counts':audited['summary']['audit_status_counts'],
            'paired_status_counts':audited['summary']['pair_status_counts'],
            'asof_status_counts':audited['summary']['asof_status_counts'],
            'full_verified_by_market':audited['summary']['fully_verified_distinct_games_by_market'],
            'eligible_new_game_hits':len({r['official_game_pk'] for r in valid_hits}),
            'frozen_train_last_start':frozen['train_last_start'],
            'no_refit_on_holdout':True,
            'live_model_modified':False,
            'external_research_only':True,
        },
        'audit':audited['audit'],
        'asof':asof,
        'locked':locked,
    }


def main():
    p=argparse.ArgumentParser(description='Research-only untouched HF archive shard vs pre-frozen MLB player hits model')
    p.add_argument('--frozen-model',required=True,type=Path)
    p.add_argument('--source-candidates',required=True,type=Path)
    p.add_argument('--output-dir',required=True,type=Path)
    args=p.parse_args()
    if 'reports' not in args.output_dir.parts or any(word in args.output_dir.parts for word in ('decision','commercial_web','public','latest')):
        raise SystemExit('The unseen shard cannot write into a live model or site folder')
    frozen_sha=hashlib.sha256(args.frozen_model.read_bytes()).hexdigest()
    frozen=json.loads(args.frozen_model.read_text())
    if frozen.get('deployment')!='RESEARCH_ONLY_NO_LIVE_MODEL_ACCESS' or not frozen.get('new_source_shard_reserved'):
        raise ValueError('Only an explicitly pre-frozen external model with reserved shard may be evaluated')
    sample=json.loads(args.source_candidates.read_text())
    if len(sample)>3000:raise ValueError('Unbounded sample refused')
    data=pd.read_csv(ROOT/'intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_HISTORY.csv',
        usecols=sorted(set(REQUIRED_OFFICIAL_COLUMNS)|{'player_id','plate_appearances','outs'}),low_memory=False)
    result=audit_unseen_shard(frozen,sample,data)
    if hashlib.sha256(args.frozen_model.read_bytes()).hexdigest()!=frozen_sha:
        raise RuntimeError('Frozen model changed during supposedly locked evaluation')
    result['summary'].update({'generated_at':datetime.now(timezone.utc).isoformat(),
       'frozen_model_sha256':frozen_sha,
       'new_source_candidates_sha256':hashlib.sha256(args.source_candidates.read_bytes()).hexdigest(),
       'production_publish_gate':'DENIED_EXTERNAL_RETROSPECTIVE_BACKTEST'})
    args.output_dir.mkdir(parents=True,exist_ok=True)
    for fname,payload in [('unseen_official_audit.json',result['audit']),('unseen_asof_audit.json',result['asof']),('unseen_locked_result.json',{'summary':result['summary'],'locked':result['locked']})]:
        (args.output_dir/fname).write_text(json.dumps(payload,indent=2,default=str)+'\n')
    print(json.dumps({'summary':result['summary'],'locked':result['locked']},indent=2))

if __name__=='__main__':main()
