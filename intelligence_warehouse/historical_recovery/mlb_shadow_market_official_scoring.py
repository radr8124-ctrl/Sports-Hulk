"""Actual prospective MLB market-only shadow calibration vs no-vig book.

Everything is tied to the original source-time pregame market-only forecast
AND a later, separately authenticated official Final hitter result. Each
player comparison is descriptive; correlated players in one game are one
independent calendar/game block. No P&L or approved bookmaker bets inferred.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime,timezone
import argparse
import fcntl
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

from .mlb_asof_feature_store import ROOT,sha_file
from .mlb_shadow_market_control import (
    OUTPUT as SHADOW,
    SCHEMA as SHADOW_SCHEMA,
)
from .mlb_research_forward_labels import (
    OUTPUT as OFFICIAL_GRADES,
    SCHEMA as OFFICIAL_SCHEMA,
)

OUTPUT=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V2_MARKET_SHADOW_OFFICIAL_COMPARISON.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V2_MARKET_SHADOW_OFFICIAL_COMPARISON_SUMMARY.json'
SCHEMA='MLB_V2_MARKET_ONLY_SHADOW_VS_OFFICIAL_HITS_RESEARCH_SCORE_V1'
SAMPLE_INDEPENDENT_GAME_FLOOR=30


def _utc(raw):
    time=pd.to_datetime(raw,utc=True,errors='coerce')
    if pd.isna(time):raise ValueError('Missing official or source-time record timestamp')
    return time


def _key(p:dict)->tuple[int,int,str,float]:
    gid=int(p.get('game_pk',p.get('official_game_pk')))
    player=int(p.get('mlbam_player_id',p.get('player_id')))
    return (gid,player,str(p.get('market_metric','hits')),float(p.get('line',0.5)))


def _normal_summary(count:int,independent:int,pending:int,brier_market=None,brier_shadow=None,logloss_market=None,logloss_shadow=None)->dict:
    status=('AWAITING_NEW_FINAL_MLB_OFFICIAL_OUTCOME_EVIDENCE' if count==0
            else 'BUILDING_MORE_INDEPENDENT_GAMES_FOR_RESEARCH'
            if independent<SAMPLE_INDEPENDENT_GAME_FLOOR
            else 'HISTORICAL_SCORE_REQUIRES_INDEPENDENT_CALIBRATION_AND_CONFIDENCE_REVIEW')
    return {
        'schema':SCHEMA,
        'status':status,
        'settled_player_market_comparisons':count,
        'independent_games_with_settled_comparisons':independent,
        'ungraded_player_forecasts':pending,
        'minimum_independent_games_for_first_sample_floor':SAMPLE_INDEPENDENT_GAME_FLOOR,
        'remaining_games_to_first_sample_floor':max(0,SAMPLE_INDEPENDENT_GAME_FLOOR-independent),
        'market_raw_brier':brier_market,
        'market_calibrated_brier':brier_shadow,
        'market_raw_logloss':logloss_market,
        'market_calibrated_logloss':logloss_shadow,
        'market_only_model_no_advanced_velocity_features':True,
        'statistically_proven_market_improvement':False,
        'commercial_betting_edge_claim_permitted':False,
        'live_play_approvals':0,
        'wagers_or_settlement_recorded':0,
        'grade_types':'HITTER_STATS_ONLY_NOT_SPORTSBOOK_MARKET_SETTLEMENT',
    }


def score_graded_shadow_research(
    shadow:list[dict],grades:list[dict],*,now:datetime,
)->tuple[list[dict],dict]:
    if now.tzinfo is None:
        raise ValueError('Real official results comparison requires offset-aware observation time')
    observed=_utc(now)
    shadow_keys={};grade_keys={}
    for source in shadow:
        key=_key(source)
        if key in shadow_keys:raise ValueError('Shadow source has duplicate player game/market forecast')
        shadow_keys[key]=source
        if source.get('schema')!=SHADOW_SCHEMA:
            raise ValueError('Unrecognized genuine original shadow model schema')
        if source.get('betting_play_authorized') is not False or source.get('wager_submitted') is not False:
            raise ValueError('Shadow source must be research-only and not imply bookmaker settlement')
        if source.get('market_metric')!='hits' or float(source.get('line',0))!=.5:
            raise ValueError('Market only player-hits 0.5 calibration model was never trained for these other prices')
        if _utc(source['frozen_shadow_at_utc'])>=_utc(source['actual_game_event_start_utc']):
            raise ValueError('Market control was not frozen pregame and cannot count as a real forward comparison')
        if not source.get('source_original_lineup_sha256') or len(source['source_original_lineup_sha256'])!=64:
            raise ValueError('Missing source lineup SHA and original player proof')
    for grade in grades:
        if grade.get('schema')!=OFFICIAL_SCHEMA:
            raise ValueError('Unknown independent official game/outcome source')
        key=(int(grade['official_game_pk']),int(grade['player_id']))
        if key in grade_keys:raise ValueError('Official source has duplicate player/game grades')
        grade_keys[key]=grade
    result=[]
    for (game,player,metric,line),source in shadow_keys.items():
        grade=grade_keys.get((game,player))
        if grade is None:continue
        if (
            grade.get('official_final_status_from_mlb_master')!='Final'
            or grade.get('sportsbook_bet_settled') is not False
            or grade.get('model_win_or_probability_qualified') is not False
            or grade.get('live_play_approved') is not False
        ):
            raise ValueError('Official grade must be research-only, independently verified and Final')
        if grade.get('original_source_line_sha256')!=source['source_original_lineup_sha256']:
            raise ValueError('Original pregame source player/lineup SHA mismatch, not the same original source')
        first=_utc(source['actual_game_event_start_utc'])
        checked=_utc(grade['official_outcome_checked_at_utc'])
        if observed<checked or checked<=first or _utc(source['frozen_shadow_at_utc'])>=first:
            raise ValueError('Postgame official result not actually available after frozen pregame forecast')
        hits=pd.to_numeric(grade['official_hits'],errors='coerce')
        if pd.isna(hits) or not np.isfinite(float(hits)) or float(hits)<0:
            raise ValueError('Invalid completed official hits: cannot fabricate player loss')
        true=int(float(hits)>line)
        market=float(source['raw_no_vig_market_probability_over'])
        predicted=float(source['calibrated_market_control_probability_over'])
        if not (.001<market<.999 and .001<predicted<.999):
            raise ValueError('Invalid frozen forecast probability')
        report={
            'schema':SCHEMA,
            'official_game_pk':game,
            'mlbam_player_id':player,
            'market_metric':metric,
            'line':line,
            'frozen_pregame_market_over_probability':market,
            'frozen_pregame_market_only_calibrated_probability':predicted,
            'source_forecast_frozen_at_utc':source['frozen_shadow_at_utc'],
            'original_pregame_lineup_sha256':source['source_original_lineup_sha256'],
            'model_source_sha256':source['baseline_model_coefficients_sha256'],
            'official_checked_at_utc':grade['official_outcome_checked_at_utc'],
            'official_original_final_source_frozen_player_at_utc':grade['source_frozen_feature_at_utc'],
            'official_game_status':'Final',
            'observed_player_hits':int(hits),
            'hit_over_line_outcome':true,
            'market_raw_squared_error':round((market-true)**2,12),
            'market_calibrated_squared_error':round((predicted-true)**2,12),
            'market_raw_log_loss':round(float(-math.log(max(1e-9,market if true else 1-market))),12),
            'market_calibrated_log_loss':round(float(-math.log(max(1e-9,predicted if true else 1-predicted))),12),
            'independent_game_block':str(game),
            'market_probability_baseline_only':True,
            'full_16_feature_speed_walk_model_evaluated':False,
            'sportsbook_wager_placed':False,
            'sportsbook_bet_settled':False,
            'profitability_claim_approved':False,
            'proven_model_market_advantage':False,
        }
        result.append(report)
    result.sort(key=lambda x:(x['official_game_pk'],x['mlbam_player_id']))
    count=len(result)
    groups={x['official_game_pk'] for x in result}
    summary=_normal_summary(
        count,len(groups),len(shadow)-count,
        brier_market=round(float(np.mean([x['market_raw_squared_error'] for x in result])),9) if count else None,
        brier_shadow=round(float(np.mean([x['market_calibrated_squared_error'] for x in result])),9) if count else None,
        logloss_market=round(float(np.mean([x['market_raw_log_loss'] for x in result])),9) if count else None,
        logloss_shadow=round(float(np.mean([x['market_calibrated_log_loss'] for x in result])),9) if count else None,
    )
    return result,summary


def append_first_official_shadow_scores(path:Path,results:list[dict])->int:
    if not results:return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+'.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        old={}
        if path.exists():
            with path.open('r',encoding='utf-8') as f:
                for line in f:
                    if not line.strip():continue
                    row=json.loads(line)
                    if row.get('schema')!=SCHEMA:
                        raise ValueError('Unknown archived official source grade')
                    key=_key(row)
                    if key in old:raise ValueError('Duplicate immutable original grade')
                    old[key]=row
        seen=set();new=[]
        for record in results:
            if record.get('schema')!=SCHEMA or record.get('sportsbook_wager_placed') is not False:
                raise ValueError('Only research comparisons may enter official grade archive')
            key=_key(record)
            if key in seen:raise ValueError('Duplicate newly generated grade identity')
            seen.add(key)
            if key in old:
                # Every date/grade/result field except potentially local
                # observation metadata should be unchanged. Do not silently
                # overwrite a finalized score if the data provider corrects
                # the game after the original first published boxscore.
                if old[key]!=record:
                    raise ValueError('Official grade conflicts with first frozen source result; manual correction required')
                continue
            new.append(record);old[key]=record
        if new:
            with path.open('a',encoding='utf-8') as fd:
                for row in new:
                    fd.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n')
                fd.flush();os.fsync(fd.fileno())
        return len(new)


def _read_lines(path:Path)->list[dict]:
    if not path.exists():return []
    with path.open('r',encoding='utf-8') as f:
        return [json.loads(x) for x in f if x.strip()]


def score_cycle(
    shadow_file:Path=SHADOW,grade_file:Path=OFFICIAL_GRADES,
    output:Path=OUTPUT,*,now:datetime|None=None,
)->dict:
    observed=now or datetime.now(timezone.utc)
    if observed.tzinfo is None:raise ValueError('Research scoring time must have timezone')
    forecasts=_read_lines(shadow_file)
    grades=_read_lines(grade_file)
    proposed,summary=score_graded_shadow_research(forecasts,grades,now=observed)
    added=append_first_official_shadow_scores(output,proposed)
    prior=_read_lines(output)
    if len(prior)!=len(proposed):
        # Scored summary must preserve older finalized outcomes if newer
        # selection changed or provider data becomes temporarily unavailable.
        raise ValueError('Existing official shadow outcome evidence unexpectedly disappeared')
    summary.update({
        'run_at_utc':_utc(observed).isoformat(),
        'newly_scored_research_rows':added,
        'official_grade_source_sha256':sha_file(grade_file) if grade_file.is_file() else None,
        'original_pregame_shadow_source_sha256':sha_file(shadow_file) if shadow_file.is_file() else None,
        'historical_model_changed':False,
        'commercial_betting_edge_claim_permitted':False,
        'official_players_graded_are_not_independent_games':True,
    })
    return summary


def main():
    ap=argparse.ArgumentParser(description='MLB original bookmaker fair market vs true pregame shadow and later Final hits')
    ap.add_argument('--shadow',type=Path,default=SHADOW)
    ap.add_argument('--grades',type=Path,default=OFFICIAL_GRADES)
    ap.add_argument('--output',type=Path,default=OUTPUT)
    args=ap.parse_args()
    if args.shadow.resolve()!=SHADOW.resolve() or args.grades.resolve()!=OFFICIAL_GRADES.resolve() or args.output.resolve()!=OUTPUT.resolve():
        raise SystemExit('Refusing alternate unverified MLB shadow or official label source')
    report=score_cycle(args.shadow,args.grades,args.output)
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temp=SUMMARY.with_suffix('.tmp')
    temp.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    os.replace(temp,SUMMARY)
    print('MLB_RESEARCH_ONLY_SHADOW_VS_MARKET_OFFICIAL_SCORE',json.dumps(report,sort_keys=True))


if __name__=='__main__':
    main()
