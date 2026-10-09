"""Compare three SAME-new-quote probabilities against official MLB Final hits.

These are strictly original PRE-pitch source-frozen model predictions from the
original bookmaker two-sided price and 90-game earlier pre-July trained
market-only and full16 restricted context model. Original official lineup SHA
and final official game/player hits must match exactly.

This is NOT a bet settlement or evidence of profitable edge. All 18 hitters
from this fixture share ONE independent game block. No automatic PLAY change.
"""
from __future__ import annotations

from datetime import datetime,timezone
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import math
import os

import numpy as np
import pandas as pd

from .mlb_asof_feature_store import ROOT,sha_file
from .mlb_full_context_true_forward_shadow import (
    OUT as FULL_SOURCE,
    SHADOW_SCHEMA as FULL_SCHEMA,
)
from .mlb_research_forward_labels import (
    OUTPUT as OFFICIAL_LABELS,
    SCHEMA as GRADE_SCHEMA,
)

OUTPUT=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V4_FULL16_SAME_NEW_QUOTE_OFFICIAL_THREEWAY_SCORES.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V4_FULL16_SAME_NEW_QUOTE_SCORE_SUMMARY.json'
SCHEMA='MLB_V4_FULL16_SAME_LATER_PAIR_BOOK_PRICE_OFFICIAL_FINAL_HITS_SCORE_V1'
MIN_INDEPENDENT_GAME_FLOOR=30


def _utc(when)->pd.Timestamp:
    value=pd.to_datetime(when,utc=True,errors='coerce')
    if pd.isna(value):
        raise ValueError('Missing first pitch, quote, model or official Final source timestamp')
    return value


def _read(file:Path)->list[dict]:
    if not file.is_file():return []
    with file.open('r',encoding='utf-8') as f:
        return [json.loads(s) for s in f if s.strip()]


def _metrics(report:list[dict],name:str)->tuple[float|None,float|None]:
    if not report:return None,None
    a=[x[f'{name}_squared_error'] for x in report]
    b=[x[f'{name}_logloss'] for x in report]
    return round(float(np.mean(a)),9),round(float(np.mean(b)),9)


def score_after_original_final(
    source:list[dict],official:list[dict],*,now:datetime
)->tuple[list[dict],dict]:
    if now.tzinfo is None:
        raise ValueError('Game-result model grading requires truthful timezone-aware observation clock')
    clock=_utc(now)
    original={}
    for record in source:
        key=(int(record['official_game_pk']),int(record['mlbam_player_id']))
        if key in original:
            raise ValueError('Source has duplicate genuinely frozen full16 official player/game forecast')
        original[key]=record
        if record.get('schema')!=FULL_SCHEMA:
            raise ValueError('Unknown full 16-feature previously frozen model source')
        if record.get('betting_play_approved') is not False or record.get('wager_executed') is not False:
            raise ValueError('This source is research-only, never already approved/executed bookmaker bet')
        if record.get('market_metric')!='hits' or float(record.get('line',-1))!=.5:
            raise ValueError('Historical 16 model was not fitted for this non-player-hits or different line')
        if (
            record.get('full_context_is_pre_first_pitch_source_frozen') is not True
            or record.get('full_context_is_after_first_earlier_price_not_backdated') is not True
        ):
            raise ValueError('Missing original source-time provenance for context/model')
        start=_utc(record['official_first_pitch_utc'])
        contextual=_utc(record['source_team_context_frozen_at_utc'])
        quote=_utc(record['source_quote_at_utc'])
        prediction=_utc(record['first_full_context_shadow_frozen_at_utc'])
        if not contextual<quote<=prediction<start:
            raise ValueError('Original pregame context/quote/forecast not frozen before first pitch')
        if not record.get('original_lineup_sha256') or len(record['original_lineup_sha256'])!=64:
            raise ValueError('Missing original official pregame player lineup SHA')
        if not record.get('frozen_prejuly_model_sha256') or len(record['frozen_prejuly_model_sha256'])!=64:
            raise ValueError('Missing originally fixed 90-game training model SHA-256')
        if len(record.get('model_16_features') or [])!=16:
            raise ValueError('Model is missing one or more original sixteen source-time components')
        if not np.isfinite(np.asarray(record['model_16_features'],dtype=float)).all():
            raise ValueError('Original sixteen source-time features contain nonfinite data')
        for p in ['market_fair_prob_at_exact_new_quote',
                  'market_only_calibrated_prob_at_same_new_quote',
                  'sixteen_feature_context_shadow_prob']:
            v=float(record[p])
            if not .001<v<.999:
                raise ValueError(f'Original source probability invalid: {p}')
    by_grade={}
    for grade in official:
        if grade.get('schema')!=GRADE_SCHEMA:
            raise ValueError('Unknown official source player hits result schema')
        key=(int(grade['official_game_pk']),int(grade['player_id']))
        if key in by_grade:
            raise ValueError('Provider source contains duplicate independent player/game official grades')
        by_grade[key]=grade
    results=[]
    for key,forecast in original.items():
        grade=by_grade.get(key)
        if grade is None:
            continue
        if (
            grade.get('official_final_status_from_mlb_master')!='Final'
            or grade.get('sportsbook_bet_settled') is not False
            or grade.get('model_win_or_probability_qualified') is not False
            or grade.get('live_play_approved') is not False
        ):
            raise ValueError('Official result not authenticated Final independent research-only source')
        if grade.get('original_source_line_sha256')!=forecast['original_lineup_sha256']:
            raise ValueError('Official result does not match exact original frozen lineup SHA')
        event_start=_utc(forecast['official_first_pitch_utc'])
        graded_at=_utc(grade['official_outcome_checked_at_utc'])
        if not event_start<graded_at<=clock:
            raise ValueError('Official Final result must have been observed after first pitch')
        hits=pd.to_numeric(grade.get('official_hits'),errors='coerce')
        if pd.isna(hits) or not np.isfinite(hits) or float(hits)<0:
            raise ValueError('Invalid official player hits: no fabricated zero for missing/scratched player')
        outcome=int(float(hits)>.5)
        performance={}
        for name,col in (
            ('book_raw','market_fair_prob_at_exact_new_quote'),
            ('market_only','market_only_calibrated_prob_at_same_new_quote'),
            ('full16','sixteen_feature_context_shadow_prob'),
        ):
            p=float(forecast[col])
            performance[name+'_over_probability']=p
            performance[name+'_squared_error']=round((p-outcome)**2,12)
            performance[name+'_logloss']=round(-math.log(p if outcome else 1-p),12)
        results.append({
            'schema':SCHEMA,
            'official_game_pk':key[0],
            'mlbam_player_id':key[1],
            'market':'player_hits_OVER_0_5',
            'official_player_hits':int(hits),
            'actual_hits_over_half':outcome,
            'original_official_pregame_source_sha256':forecast['original_lineup_sha256'],
            'original_source_new_quote_at_utc':forecast['source_quote_at_utc'],
            'original_model_prospectively_frozen_at_utc':forecast['first_full_context_shadow_frozen_at_utc'],
            'original_training_model_sha256':forecast['frozen_prejuly_model_sha256'],
            'official_game_start_utc':forecast['official_first_pitch_utc'],
            'source_final_checked_at_utc':grade['official_outcome_checked_at_utc'],
            'independent_game_block_id':str(key[0]),
            'official_status':'Final',
            'market_bookmaker':forecast['selected_sportsbook'],
            'same_original_book_quote_used_for_all_three_predictions':True,
            'original_forward_model_was_full16_pregame_context':True,
            'independent_market_outperformance_not_proven':True,
            'research_only':True,
            'sportsbook_wager_executed':False,
            'model_promoted_to_live_play':False,
            **performance,
        })
    results.sort(key=lambda x:(x['official_game_pk'],x['mlbam_player_id']))
    n=len({x['official_game_pk'] for x in results})
    m={}
    for name in ['book_raw','market_only','full16']:
        m[name+'_brier'],m[name+'_logloss']=_metrics(results,name)
    summary={
        'schema':SCHEMA,
        'status':'WAITING_FOR_AUTHENTIC_MLB_FINAL_PLAYER_HITS' if not results else (
            'ACCUMULATING_INDEPENDENT_GAME_AND_PLAYER_BLOCKS_EDGE_NOT_PROVEN' if n<MIN_INDEPENDENT_GAME_FLOOR
            else 'SAMPLE_FLOOR_ONLY_INDEPENDENT_PROFITABILITY_REVIEW_REQUIRED'),
        'source_player_comparisons':len(results),
        'original_true_full16_shadow_forecasts':len(source),
        'pending_ungraded_player_forecasts':len(source)-len(results),
        'independent_official_game_blocks':n,
        'sample_floor_independent_games':MIN_INDEPENDENT_GAME_FLOOR,
        'games_remaining_until_first_floor':max(0,MIN_INDEPENDENT_GAME_FLOOR-n),
        'bookmaker_and_market_only_challenger_same_original_later_quote':True,
        'real_first_result_not_three_independent_models_of_one_game':True,
        'statistically_proven_market_advantage':False,
        'profitable_market_edge_qualified':False,
        'play_authorized':False,
        'wagers_settled':0,
        'confidence_interval_not_computed_until_multiple_independent_game_blocks':True,
        'game_venue_probable_pitcher_and_weather_source_not_confirmed_starter':True,
        **m,
    }
    return results,summary


def append_immutable_full16_scores(path:Path,records:list[dict])->int:
    if not records:return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+'.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        old={}
        for x in _read(path):
            if x.get('schema')!=SCHEMA:
                raise ValueError('Unrecognized official full16 source grade history')
            key=(int(x['official_game_pk']),int(x['mlbam_player_id']))
            if key in old:raise ValueError('Duplicate previously frozen final full16 grader')
            old[key]=x
        new=[];batch=set()
        for x in records:
            if x.get('schema')!=SCHEMA or x.get('sportsbook_wager_executed') is not False:
                raise ValueError('Only research-only authentic original official full16 result')
            key=(int(x['official_game_pk']),int(x['mlbam_player_id']))
            if key in batch:raise ValueError('Duplicate newly graded official player/game')
            batch.add(key)
            if key in old:
                if old[key]!=x:
                    raise ValueError('Original first official full16 score conflicts with a later provider revision')
                continue
            new.append(x)
        if new:
            with path.open('a',encoding='utf-8') as f:
                for r in new:
                    f.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
                f.flush();os.fsync(f.fileno())
        return len(new)


def score_cycle(
    forecasts_file:Path=FULL_SOURCE,
    official_file:Path=OFFICIAL_LABELS,
    output:Path=OUTPUT,*,now:datetime|None=None,
)->dict:
    clock=now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise ValueError('True source-time result summary requires timezone-aware clock')
    original=_read(forecasts_file)
    grades=_read(official_file)
    proposed,summary=score_after_original_final(original,grades,now=clock)
    saved=append_immutable_full16_scores(output,proposed)
    existing=_read(output)
    if len(existing)!=len(proposed):
        raise ValueError('Previously graded authenticated official research source unexpectedly disappeared')
    summary.update({
        'observed_at_utc':_utc(clock).isoformat(),
        'newly_official_player_results_compared':saved,
        'total_saved_final_research_player_comparisons':len(existing),
        'original_full16_model_source_sha256':sha_file(forecasts_file) if forecasts_file.is_file() else None,
        'independent_final_player_grade_source_sha256':sha_file(official_file) if official_file.is_file() else None,
        'betting_model_or_live_play_threshold_unchanged':True,
        'original_source_and_original_model_coefficients_unchanged':True,
    })
    return summary


def main():
    parser=argparse.ArgumentParser(description='MLB original-book RAW vs market model vs full16 shadow after original official Final')
    parser.add_argument('--forecasts',type=Path,default=FULL_SOURCE)
    parser.add_argument('--official',type=Path,default=OFFICIAL_LABELS)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args()
    if any([
        args.forecasts.resolve()!=FULL_SOURCE.resolve(),
        args.official.resolve()!=OFFICIAL_LABELS.resolve(),
        args.output.resolve()!=OUTPUT.resolve(),
    ]):
        raise SystemExit('Refusing untrusted alternative original 16-feature/official source grades')
    result=score_cycle()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temp=SUMMARY.with_suffix('.tmp')
    temp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    os.replace(temp,SUMMARY)
    print('MLB_FROZEN_FULL16_MARKET_VS_OFFICIAL_RESULTS_RESEARCH',json.dumps(result,sort_keys=True))


if __name__=='__main__':
    main()
