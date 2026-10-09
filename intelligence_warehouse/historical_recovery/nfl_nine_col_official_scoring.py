"""Independent ESPN Final-only NFL game score vs three frozen pregame models.

Three probabilities refer to ONE original, SAME-book, SAME-timestamp,
source-verified future HOME-moneyline observation:
  (1) no-vig fair bookmaker,
  (2) earlier 2016-24 fit market-only calibrator,
  (3) same-trained nine-feature prior completed-week scoring form challenger.

Outcomes are scored only from separately fetched ESPN Final status+team score
matched to nflverse original game ID/teams. Missing official game = UNKNOWN,
ties are NOT losses or normal two-outcome moneyline wins. Research only;
no ROI/wager/profit/PLAY claim. NFL weeks/team opponents are correlated.
"""
from __future__ import annotations

from datetime import datetime,timezone
from pathlib import Path
import argparse,fcntl,json,math,os

import numpy as np
import pandas as pd

from .mlb_asof_feature_store import ROOT,sha_file
from .nfl_first_nine_col_forward_shadow import (
    OUTPUT as FORECASTS,SCHEMA as SHADOW_SCHEMA,
)
from .nfl_verified_2026_score_form import FINAL_SCHEMA
from .nfl_forward_individual_final_source import OUTPUT as FINALS

OUTPUT=ROOT/'intelligence_warehouse/nfl_advanced_pregame/NFL_NINE_FEATURE_SAME_BOOK_OFFICIAL_FINAL_SCORES.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/nfl_advanced_pregame/NFL_NINE_FEATURE_OFFICIAL_FINAL_COMPARISON_SUMMARY.json'
SCHEMA='NFL_2026_RESEARCH_NINE_FEATURE_SAME_BOOK_VS_INDEPENDENT_ESPN_FINAL_SCORE_V1'
SAMPLE_FLOOR=30


def _utc(val):
    x=pd.to_datetime(val,utc=True,errors='coerce')
    if pd.isna(x):raise ValueError('Missing original bookmaker/source/team kickoff timestamp')
    return x


def _read(path):
    if not path.is_file():return []
    with path.open('r',encoding='utf-8') as file:return [json.loads(s) for s in file if s.strip()]


def _aggregate(rows,name):
    if not rows:return None,None
    return (round(float(np.mean([r[name+'_squared_error'] for r in rows])),9),
            round(float(np.mean([r[name+'_log_loss'] for r in rows])),9))


def score_original_nfl_games_against_verified_final(
    original_forecasts:list[dict],official_finals:list[dict],*,now:datetime
)->tuple[list[dict],dict]:
    if now.tzinfo is None:raise ValueError('Original actual ESPN Final capture requires timezone')
    clock=_utc(now)
    forecasts={}
    official={}
    for p in original_forecasts:
        game=str(p.get('official_espn_event_id') or '')
        if game in forecasts:raise ValueError('Source has duplicate first-frozen ESPN NFL game model probability')
        if not game.isdigit() or p.get('schema')!=SHADOW_SCHEMA:
            raise ValueError('Non original ESPN independent-model source')
        if p.get('betting_play_approved') is not False or p.get('sportsbook_wager_created') is not False:
            raise ValueError('Source must remain genuine pregame RESEARCH and not already booked/live approved')
        if p.get('source_is_game_moneyline_not_player_proposition') is not True:
            raise ValueError('NFL original predictor not from HOME game moneyline')
        f=_utc(p['source_context_features_frozen_at_utc'])
        q=_utc(p['source_qualified_book_quote_updated_at_utc'])
        forecast=_utc(p['source_first_real_future_prediction_frozen_at_utc'])
        first=_utc(p['official_first_pitch_utc'])
        if not f<q<=forecast<first:
            raise ValueError('Original true pregame model and bookmaker quote were not frozen before kickoff')
        for col in ('original_raw_book_home_fair',
                    'market_only_calibrated_home_win_prob','nine_feature_score_form_home_win_prob'):
            val=float(p[col])
            if not np.isfinite(val) or not .001<val<.999:
                raise ValueError('Original score-form market probability invalid')
        forecasts[game]=p
    for f in official_finals:
        game=str(f.get('official_espn_game_id') or '')
        if game in official:raise ValueError('Source has duplicate independently verified ESPN Final game identity')
        if f.get('schema')!=FINAL_SCHEMA:
            raise ValueError('Unknown officially verified ESPN status or score schema')
        official[game]=f
    scored=[];ties=0
    for gid,fore in forecasts.items():
        final=official.get(gid)
        if final is None:continue
        if final.get('official_espn_final_confirmed') is not True:
            raise ValueError('Official ESPN fixture is not independently Final')
        if (final.get('season')!=fore.get('season')
            or final.get('week')!=fore.get('week')
            or final.get('home_team')!=fore.get('home_team')
            or final.get('away_team')!=fore.get('away_team')):
            raise ValueError('Official final team/season/week identity mismatch')
        if _utc(final['source_first_pitch_utc'])!=_utc(fore['official_first_pitch_utc']):
            raise ValueError('Original ESPN official Final and original pregame kickoffs do not agree')
        if not _utc(fore['official_first_pitch_utc'])<_utc(final['final_observed_at_utc'])<=clock:
            raise ValueError('Independently verified ESPN Final must be observed after first pitch, never future')
        hp=float(final['home_points']);ap=float(final['away_points'])
        if not np.isfinite(hp) or not np.isfinite(ap) or min(hp,ap)<0 or hp>150 or ap>150:
            raise ValueError('Official NFL final result has impossible team score')
        if hp==ap:
            ties+=1
            continue
        win=int(hp>ap)
        fields={}
        for key,col in [
            ('raw_book','original_raw_book_home_fair'),
            ('market_only','market_only_calibrated_home_win_prob'),
            ('score_form','nine_feature_score_form_home_win_prob'),
        ]:
            q=float(fore[col])
            fields[key+'_original_pregame_home_win_probability']=q
            fields[key+'_squared_error']=round((q-win)**2,12)
            fields[key+'_log_loss']=round(float(-math.log(q if win else 1-q)),12)
        scored.append({
            'schema':SCHEMA,
            'official_espn_event_id':gid,
            'original_source_schedule_game_id':fore['source_schedule_game_id'] if 'source_schedule_game_id' in fore else None,
            'home_team':fore['home_team'],'away_team':fore['away_team'],
            'season':fore['season'],'week':fore['week'],
            'official_home_points':int(hp),
            'official_away_points':int(ap),
            'original_home_moneyline_win_binary_outcome':win,
            'source_real_original_final_observed_at_utc':final['final_observed_at_utc'],
            'source_original_espn_final_scoreboard_sha256':final['source_weekly_espn_payload_sha256'],
            'source_original_final_schedule_sha256':final['source_season_schedule_sha256'],
            'source_first_original_model_frozen_at_utc':fore['source_first_real_future_prediction_frozen_at_utc'],
            'original_model_sha256':fore['source_frozen_model_sha256'],
            'source_original_book_name':fore['source_book_name'],
            'original_source_quote_updated_at_utc':fore['source_qualified_book_quote_updated_at_utc'],
            'independent_game_block_id':gid,
            'one_NFL_match_counts_as_one_independent_source_event':True,
            'not_sportsbook_settlement_or_wager_win':True,
            'research_only':True,'live_play_approved':False,
            'profitable_market_edge_proven':False,'sportsbook_wager_executed':False,
            **fields,
        })
    scored.sort(key=lambda x:(x['season'],x['week'],x['official_espn_event_id']))
    count=len({r['official_espn_event_id'] for r in scored})
    stats={}
    for name in ('raw_book','market_only','score_form'):
        stats[name+'_brier'],stats[name+'_logloss']=_aggregate(scored,name)
    return scored,{
        'schema':SCHEMA,
        'status':'WAITING_FOR_INDEPENDENT_OFFICIAL_FINAL_NFL_GAME' if not scored else 'FORWARD_MARKET_VS_MODEL_GAME_SCORES_ACCUMULATING_NOT_PROFITABILITY_PROOF',
        'source_pairs_scored':len(scored),
        'independent_final_game_blocks':count,
        'original_source_model_game_forecasts':len(original_forecasts),
        'ungraded_future_game_forecasts':len(original_forecasts)-count-ties,
        'official_final_tie_games_held_separately':ties,
        'independent_game_floor':SAMPLE_FLOOR,
        'remaining_final_games_to_first_floor':max(0,SAMPLE_FLOOR-count),
        'model_2025_retrospective_validation_was_worse_than_raw_market':True,
        'market_advantage_statistically_proven':False,
        'live_play_approved':False,'real_wagers_submitted_or_profitable_payoffs_proven':False,
        'minimum_sample_does_not_imply_edge':True,
        **stats,
    }


def append_first_true_nfl_market_comparisons(path:Path,rows:list[dict])->int:
    if not rows:return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+'.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        current={}
        for old in _read(path):
            if old.get('schema')!=SCHEMA:raise ValueError('Foreign official Final model score source')
            gid=str(old['official_espn_event_id'])
            if gid in current:raise ValueError('Duplicate original previously graded NFL game')
            current[gid]=old
        new=[];seen=set()
        for r in rows:
            if r.get('schema')!=SCHEMA or r.get('sportsbook_wager_executed') is not False:
                raise ValueError('A sportsbook wager cannot be inserted into research grade ledger')
            gid=str(r['official_espn_event_id'])
            if gid in seen:raise ValueError('Duplicate same-batch independent NFL game')
            seen.add(gid)
            if gid in current:
                if current[gid]!=r:
                    raise ValueError('Official first Final research score conflicts with a later provider correction')
                continue
            new.append(r)
        if new:
            with path.open('a',encoding='utf-8') as fd:
                for row in new:fd.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n')
                fd.flush();os.fsync(fd.fileno())
        return len(new)


def score_cycle(
    forecasts_file:Path=FORECASTS,
    official_final_file:Path=FINALS,
    output:Path=OUTPUT,*,now:datetime|None=None,
)->dict:
    clock=now or datetime.now(timezone.utc)
    if clock.tzinfo is None:raise ValueError('Real official Final scoring clock must be timezone aware')
    forecasts=_read(forecasts_file)
    official=_read(official_final_file)
    scored,summary=score_original_nfl_games_against_verified_final(forecasts,official,now=clock)
    appended=append_first_true_nfl_market_comparisons(output,scored)
    old=_read(output)
    if len(old)!=len(scored):
        raise ValueError('Immutable earlier independently graded NFL result disappeared')
    summary.update({
        'observed_utc':_utc(clock).isoformat(),
        'newly_scored_final_games':appended,
        'source_original_predicted_game_sha256':sha_file(forecasts_file) if forecasts_file.is_file() else None,
        'source_independent_original_ESPN_Final_game_sha256':sha_file(official_final_file) if official_final_file.is_file() else None,
        'production_model_coefficients_or_user_betting_picks_changed':False,
    })
    return summary


def main():
    p=argparse.ArgumentParser(description='True NFL Final ESPN independent scoreboard versus frozen same-book research model, never wagers')
    p.add_argument('--predictions',type=Path,default=FORECASTS)
    p.add_argument('--official',type=Path,default=FINALS)
    p.add_argument('--output',type=Path,default=OUTPUT)
    args=p.parse_args()
    if (args.predictions.resolve()!=FORECASTS.resolve()
        or args.official.resolve()!=FINALS.resolve()
        or args.output.resolve()!=OUTPUT.resolve()):
        raise SystemExit('Untrusted replacement of original NFL forward official source paths refused')
    state=score_cycle()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temp=SUMMARY.with_suffix('.tmp')
    temp.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
    os.replace(temp,SUMMARY)
    print('NFL_FIRST_SCORE_FORM_VS_MARKET_OFFICIAL_FINAL_RESEARCH',json.dumps(state,sort_keys=True))


if __name__=='__main__':main()
