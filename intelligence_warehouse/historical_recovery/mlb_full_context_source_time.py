"""Freeze all non-price 16-model source inputs from prior official MLB games.

This is a VERSIONED retrospective-type-provenance/true-time observed research
snapshot created BEFORE future first pitch, but AFTER earlier market quotes.
Only a NEW same-book priced quote collected strictly AFTER this snapshot can
support a valid prospective 16-feature probability model comparison.

Existing 90-game previously trained 16-column model is never re-fitted here.
Past completed pitching is opponent-TEAM form, NOT a confirmed current starter.
Prior 2025 full-season venue factor is source-verified, not 2026 future park.
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
from .mlb_live_research_feature_freeze_v2 import (
    OUTPUT as FIRST_HITTER_SOURCE,SCHEMA as FIRST_HITTER_SCHEMA
)
from .mlb_pitcher_park_source_asof import (
    OUT as PITCHER_PARK_SOURCE,SCHEMA as PITCHER_PARK_SCHEMA,
    MASTER,FULL,INCREMENTAL,FULL_FIELDS,RECENT_FIELDS,GAME_FIELDS,
    reconcile_official_pitcher_history,
)
from .mlb_incremental_history_merge import (
    CHECK_STAT,merge_verified_recent_hitter_history
)

OUT=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V4_TEAM_PARK_HITTER_16FEATURE_ASOF_CONTEXT.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V4_TEAM_PARK_HITTER_16FEATURE_ASOF_CONTEXT_SUMMARY.json'
SCHEMA='MLB_V4_TRUE_PREGAME_BEFORE_FUTURE_QUOTE_16TERM_CONTEXT_INPUTS_V1'
MODEL_SOURCE=ROOT/'reports/mlb_feature_integration_20261008/MLB_SPEED_WALKS_FROZEN_RESEARCH_MODEL.json'

BASE_CONTEXT_KEYS=(
 'prior_player_trend',
 'opponent_team_last10_pitching_hits_allowed_per_9',
 'opponent_team_last10_runs_allowed',
 'prior_2025_park_factor',
 'prior_player_last10_pa_role',
 'player_rest_days',
 'player_previous_vs_opponent_hits_delta',
 'home_away_flag',
 'prior_2025_sprint_speed',
 'sprint_source_measurement_available',
 'prior_2025_bat_swing_speed',
 'bat_source_measurement_available',
 'prior_completed_5_games_walks',
 'prior_5_game_walks_source_available',
)


def _utc(value)->pd.Timestamp:
    a=pd.to_datetime(value,utc=True,errors='coerce')
    if pd.isna(a):raise ValueError('Invalid source time in original player/fixture/odds evidence')
    return a


def _clip(value:float,shift:float,scale:float,lower:float,upper:float)->float:
    v=float(value)
    if not np.isfinite(v):raise ValueError('Nonfinite source-time model input')
    return float(np.clip((v-shift)/scale,lower,upper))


def _read_jsonl(file:Path)->list[dict]:
    if not file.exists():return []
    with file.open('r',encoding='utf-8') as f:
        return [json.loads(x) for x in f if x.strip()]


def _source_id(r:dict,v3:bool=False)->tuple[int,int]:
    return (
        int(r['official_game_pk'] if v3 else r['game_pk']),
        int(r['mlbam_player_id'] if v3 else r['player_id'])
    )


def build_frozen_prequote_full_context(
    first_v2:list[dict],source_park_pitcher:list[dict],
    hitters:pd.DataFrame,pitchers:pd.DataFrame,games:pd.DataFrame,
    *,now:datetime,min_prior_player:int=5,min_prior_opp_pitch_games:int=5,
    min_prior_opp_runs_games:int=5,
)->tuple[list[dict],dict]:
    if now.tzinfo is None:raise ValueError('True pregame source must have a timezone-aware observation clock')
    observed=_utc(now)
    if not first_v2 or not source_park_pitcher:return [],{'status':'MISSING_TRUTHFUL_PREQUOTE_SOURCE','source_ineligible_player_contexts':len(first_v2)}
    if min_prior_player<5 or min_prior_opp_pitch_games<5 or min_prior_opp_runs_games<5:
        raise ValueError('Minimum historical sample floors not allowed to relax')
    if not {'game_pk','player_id','official_date','game_date','hits','plate_appearances','opponent','team','source_verified_before_quote_required'}.issubset(hitters.columns):
        raise ValueError('Source-verified official hitter history columns missing')
    if not {'game_pk','team','official_date','game_date','outs','hits_allowed','source_verified_before_quote_required'}.issubset(pitchers.columns):
        raise ValueError('Source-verified official pitching team context missing')
    if not {'gamePk','officialDate','gameDate','gameType','status','home_team','away_team','home_score','away_score'}.issubset(games.columns):
        raise ValueError('Independent final source scoreboard data missing')
    if hitters.duplicated(['game_pk','player_id']).any() or pitchers.duplicated(['game_pk','player_id']).any():
        raise ValueError('Source player-game rows are not truly unique')
    v2={}
    for x in first_v2:
        key=_source_id(x)
        if key in v2:raise ValueError('Duplicate official first-frozen hitter identity')
        v2[key]=x
    v3={}
    for x in source_park_pitcher:
        key=_source_id(x,True)
        if key in v3:raise ValueError('Duplicate source-verified probable pitcher/park context identity')
        v3[key]=x
    if set(v2)!=set(v3):
        raise ValueError('First verified hitter and prospective pitcher/park source game.player identities differ')
    # Materialize only earlier completed calendar dates AND at least 12 hours
    # elapsed between official recorded fixture kickoff and today's source.
    h=hitters.copy()
    h['_date']=pd.to_datetime(h.official_date,errors='coerce').dt.date
    h['_start']=pd.to_datetime(h.game_date,utc=True,errors='coerce')
    h=h[
        h.source_verified_before_quote_required.eq(True)
        & h._date.map(lambda x:x is not None and pd.notna(x) and x<observed.date())
        & h._start.le(observed-pd.Timedelta(hours=12))
    ].copy()
    p=pitchers.copy()
    p['_date']=pd.to_datetime(p.official_date,errors='coerce').dt.date
    p['_start']=pd.to_datetime(p.game_date,utc=True,errors='coerce')
    p=p[
        p.source_verified_before_quote_required.eq(True)
        & p._date.map(lambda x:x is not None and pd.notna(x) and x<observed.date())
        & p._start.le(observed-pd.Timedelta(hours=12))
    ].copy()
    p['outs']=pd.to_numeric(p.outs,errors='coerce')
    p['hits_allowed']=pd.to_numeric(p.hits_allowed,errors='coerce')
    p=p[p.outs.notna() & p.outs.ge(0) & p.hits_allowed.notna() & p.hits_allowed.ge(0)]
    pit_games=p.groupby(['game_pk','team'],dropna=False).agg(
        outs=('outs','sum'),hits_allowed=('hits_allowed','sum'),
        game_date=('_start','first'),official_date=('_date','first')
    ).reset_index()
    pit_games=pit_games[pit_games.outs.ge(15)].copy()
    pitch_teams={team:part.sort_values(['game_date','game_pk'])
                 for team,part in pit_games.groupby('team',sort=False)}
    player_hist={int(pid):rows.sort_values(['_start','game_pk'])
                 for pid,rows in h.groupby('player_id',sort=False)}
    g=games[
        games.gameType.isin(['R','D','F','L','W']) & games.status.eq('Final')
    ].copy()
    g['_date']=pd.to_datetime(g.officialDate,errors='coerce').dt.date
    g['_start']=pd.to_datetime(g.gameDate,utc=True,errors='coerce')
    g['home_score']=pd.to_numeric(g.home_score,errors='coerce')
    g['away_score']=pd.to_numeric(g.away_score,errors='coerce')
    g=g[
        g._date.map(lambda x:x is not None and pd.notna(x) and x<observed.date())
        & g._start.le(observed-pd.Timedelta(hours=12))
        & g.home_score.notna() & g.away_score.notna()
    ].copy()
    scores={}
    for r in g.to_dict('records'):
        scores.setdefault(str(r['home_team']),[]).append((r['_start'],int(r['gamePk']),float(r['away_score']),r['_date']))
        scores.setdefault(str(r['away_team']),[]).append((r['_start'],int(r['gamePk']),float(r['home_score']),r['_date']))
    scores={team:sorted(records) for team,records in scores.items()}
    results=[]
    rejected=[]
    for key in sorted(v2):
        old=v2[key];v=v3[key]
        if old.get('schema')!=FIRST_HITTER_SCHEMA or v.get('schema')!=PITCHER_PARK_SCHEMA:
            raise ValueError('Only originally frozen official player and certified park/pitcher source accepted')
        if old.get('live_play_approved') is not False or v.get('live_play_approved') is not False:
            raise ValueError('The sources cannot be paid model picks')
        if (
            old.get('original_append_only_line_sha256')!=v.get('original_batting_order_line_sha256')
            or old.get('source_evidence_id')!=v.get('original_pregame_evidence_id')
        ):
            raise ValueError('Original player pregame source SHA differs from probable pitcher/park source')
        kickoff=_utc(v['official_source_game_first_pitch_utc'])
        if observed>=kickoff:
            return [],{
                'status':'FIRST_PITCH_ALREADY_PASSED_NO_CONTEXT_FREEZE',
                'source_ineligible_player_contexts':len(v2),
                'full_model_ever_trained_or_changed':False,
            }
        v3_time=_utc(v['source_pitcher_and_park_context_frozen_at_utc'])
        v2_time=_utc(old['feature_frozen_at_utc'])
        if not v2_time<=v3_time<=observed<kickoff:
            raise ValueError('Original source chronology contains future context or wrongly backdated data')
        if int(v['reference_prior_full_park_season'])!=observed.year-1:
            raise ValueError('Source prior park season is not the completed previous season')
        if int(v['prior_regular_season_park_games'])<40:
            raise ValueError('Too little prior regular-season park data')
        if v.get('opposing_probable_pitcher_confirmed_starter') is not False:
            raise ValueError('Scheduled probable pitcher may not be called confirmed starter')
        if old['team_side_at_capture']!=v['source_team_side']:
            raise ValueError('Original team side of player is inconsistent')
        prior=player_hist.get(key[1])
        opp=str(v['source_opponent_team'])
        if prior is None or len(prior)<min_prior_player:
            rejected.append((key,'NO_FIVE_PREVIOUS_OFFICIAL_HITTER_APPEARANCES'))
            continue
        role=prior.tail(10)
        player_pa=pd.to_numeric(role.plate_appearances,errors='coerce')
        if player_pa.notna().sum()<5:
            rejected.append((key,'MISSING_TRUE_PRIOR_PLAYER_ROLE_STATS'))
            continue
        last=prior.iloc[-1]
        if last['_date']>=observed.date():
            raise RuntimeError('Same-day player outcome entered source model')
        rest=(observed.date()-last['_date']).days
        if rest<1:
            raise RuntimeError('Future or current-game player rest as-of misuse')
        pitching=pitch_teams.get(opp)
        runs=scores.get(opp)
        if pitching is None or runs is None or len(pitching)<min_prior_opp_pitch_games or len(runs)<min_prior_opp_runs_games:
            rejected.append((key,'NO_FIVE_COMPLETED_OPPONENT_TEAM_PITCH_OR_RUN_GAMES'))
            continue
        last_pitch=pitching.tail(10)
        outs=float(last_pitch.outs.sum())
        if outs<=0:raise ValueError('No authenticated prior pitching team outs')
        opp_hits=float(last_pitch.hits_allowed.sum()*27/outs)
        last_runs=runs[-10:]
        runs_allowed=float(np.mean([item[2] for item in last_runs]))
        h2h=prior[prior.opponent.astype(str).eq(opp)].tail(5)
        h2h_hits=pd.to_numeric(h2h.hits,errors='coerce')
        last5hit=float(old.get('prior_last5_hits_avg'))
        last5w=old.get('prior_last5_walks_avg')
        known5=(old.get('prior_history_at_least_5_completed_games') is True
                and old.get('last_prior_date') is not None
                and pd.Timestamp(old['last_prior_date']).date()<observed.date()
                and last5w is not None and pd.notna(last5w))
        sprint=old.get('prior_sprint_speed_ft_per_sec')
        bat=old.get('prior_bat_speed_mph')
        sprint_ok=old.get('prior_speed_observed') is True
        bat_ok=old.get('prior_bat_observed') is True
        if sprint_ok and (not isinstance(sprint,(float,int)) or not 10<=float(sprint)<=36):
            raise ValueError('Source prior completed 2025 sprint speed invalid')
        if bat_ok and (not isinstance(bat,(float,int)) or not 35<=float(bat)<=105):
            raise ValueError('Source prior completed 2025 bat swing speed invalid')
        if known5 and not 0<=float(last5w)<=5:
            raise ValueError('Source prior five-game walks value invalid')
        signal=float(np.clip((last5hit-.5)/math.sqrt(1.5),-4,4))
        park=float(v['prior_park_run_factor'])
        features=[
            float(np.clip(signal,-3,3)),
            _clip(opp_hits,8.5,3,-2,2),
            _clip(runs_allowed,4.5,2.5,-2,2),
            _clip(park,1.0,.2,-1.5,1.5),
            _clip(float(player_pa.mean()),4.2,1.4,-2,2),
            _clip(float(min(rest,14)),2,5,-1.5,2.5),
            (_clip(float(h2h_hits.mean()),last5hit,1,-1.5,1.5)
                if len(h2h)>=2 and h2h_hits.notna().all() else 0.),
            .5 if old['team_side_at_capture']=='home' else -.5,
            _clip(float(sprint),27,3,-2,2) if sprint_ok else 0.,
            1. if sprint_ok else 0.,
            _clip(float(bat),72,7,-2,2) if bat_ok else 0.,
            1. if bat_ok else 0.,
            _clip(float(last5w),.5,1.5,-2,2) if known5 else 0.,
            1. if known5 else 0.,
        ]
        if len(features)!=14 or not np.isfinite(features).all():
            raise ValueError('Full contextual historical model has invalid as-of research feature')
        results.append({
            'schema':SCHEMA,
            'game_pk':key[0],
            'player_id':key[1],
            'historical_training_16_feature_model_schema':'MLB_HF_SPORTS_ZENITH_ASOF_MARKET_CONTEXT_SPEED_WALKS_RESEARCH_V1_20261008',
            'original_prequote_hitter_source_sha256':old['original_append_only_line_sha256'],
            'source_v3_probable_pitcher_park_sha256':v['original_batting_order_line_sha256'],
            'official_prequote_v2_hitter_frozen_at_utc':old['feature_frozen_at_utc'],
            'verified_probable_park_source_first_frozen_at_utc':v['source_pitcher_and_park_context_frozen_at_utc'],
            'full_team_context_first_frozen_at_utc':observed.isoformat(),
            'original_game_first_pitch_utc':kickoff.isoformat(),
            'original_park_completed_season':int(v['reference_prior_full_park_season']),
            'park_prior_year_factor':park,
            'prior_player_last_date':str(last['_date']),
            'prior_player_last10_pa_role':round(float(player_pa.mean()),6),
            'player_rest_days':rest,
            'prior_opponent_pitching_games':len(last_pitch),
            'opp_prior_pitching_hits_allowed_per_9':round(opp_hits,6),
            'opp_prior_runs_allowed_last10':round(runs_allowed,6),
            'opponent_team':opp,
            'opponent_pitcher_source_type':'COMPLETED_PRIOR_TEAM_PITCHING_NOT_CONFIRMED_STARTER_PERFORMANCE',
            'probable_pitcher_is_confirmed':False,
            'weather_and_roof_actual_at_first_pitch_unknown':True,
            'prior_hitter_vs_opp_game_count':len(h2h),
            'prior_hitter_vs_opp_mean_hits':round(float(h2h_hits.mean()),6) if len(h2h) and h2h_hits.notna().all() else None,
            'verified_historical_role_player_games':len(prior),
            'sixteen_model_components_except_market':[round(float(x),10) for x in features],
            'sixteen_model_component_names_except_market':list(BASE_CONTEXT_KEYS),
            'requires_new_2026_same_book_quote_after_context_capture':True,
            'needs_new_sportsbook_quote_after_context_freeze':True,
            'source_2026_postseason_domain_shift_vs_regular_training':True,
            'full_model_ever_trained_or_changed':False,
            'source_model_probability_or_bet_created':False,
            'live_play_approved':False,
            'first_eligible_new_quote_utc_exclusive':observed.isoformat(),
            'source_provenance_status':'PROSPECTIVE_BEFORE_FIRST_PITCH_BUT_NOT_ORIGINAL_EARLIER_QUOTE',
        })
    return results,{
        'status':'COMPLETE_PRIOR_OPPONENT_TEAM_ROLE_AND_2025_PARK_FEATURES_READY_NO_ODDS',
        'eligible_source_complete_player_contexts':len(results),
        'source_ineligible_player_contexts':len(rejected),
        'reason_for_ineligible':{str(k):reason for k,reason in rejected},
        'complete_model_coefficient_changed':False,
        'full_model_ever_trained_or_changed':False,
        'source_team_and_player_only_prior_completed_game_dates':True,
        'same_day_or_future_game_rows_in_model_features':False,
        'first_later_book_quote_required_to_fit_model_prediction':True,
        'source_one_game_is_not_statistical_proof':True,
    }


def _key(x:dict)->tuple[int,int]:
    return int(x['game_pk']),int(x['player_id'])


def append_original_prequote_full_context(path:Path,records:list[dict])->int:
    if not records:return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+'.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        old={}
        for x in _read_jsonl(path):
            if x.get('schema')!=SCHEMA:raise ValueError('Corrupted original 16-feature research source ledger')
            k=_key(x)
            if k in old:raise ValueError('Duplicate historical context identity')
            old[k]=x
        added=[];present=set()
        for x in records:
            if x.get('schema')!=SCHEMA or x.get('live_play_approved') is not False or x.get('source_model_probability_or_bet_created') is not False:
                raise ValueError('Only isolated prequote prior-only contextual model inputs eligible')
            if _utc(x['full_team_context_first_frozen_at_utc'])>=_utc(x['original_game_first_pitch_utc']):
                raise ValueError('Cannot pretend postgame reconstructed context was pregame')
            k=_key(x)
            if k in present:raise ValueError('Duplicate per-game/player source context batch')
            present.add(k)
            if k in old:
                if old[k]!=x:
                    raise ValueError('First captured full model inputs conflict with updated source; preserve original')
                continue
            added.append(x)
        if added:
            with path.open('a',encoding='utf-8') as f:
                for x in added:
                    f.write(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n')
                f.flush();os.fsync(f.fileno())
        return len(added)


def freeze_cycle(now:datetime|None=None)->dict:
    observed=now or datetime.now(timezone.utc)
    if observed.tzinfo is None:raise ValueError('Source-time 16-feature research needs timezone aware clock')
    previously=_read_jsonl(OUT)
    known={_key(x) for x in previously}
    v2=_read_jsonl(FIRST_HITTER_SOURCE)
    v3=_read_jsonl(PITCHER_PARK_SOURCE)
    available={_source_id(x,True):x for x in v3}
    eligible=[x for x in v2
              if _source_id(x) not in known
              and _source_id(x) in available
              and _utc(x['feature_frozen_at_utc'])<=_utc(observed)
              and _utc(available[_source_id(x)]['source_pitcher_and_park_context_frozen_at_utc'])<=_utc(observed)
              and _utc(observed)<_utc(x['scheduled_first_pitch_utc'])]
    if not eligible:
        return {
            'status':'ALL_ELIGIBLE_OFFICIAL_GAME_HITTER_CONTEXT_ALREADY_FROZEN',
            'source_observed_at_utc':_utc(observed).isoformat(),
            'new_context_rows':0,'total_source_context_rows':len(previously),
            'large_historical_player_csv_loaded':False,
            'source_model_or_live_bets_changed':False,
        }
    sourcepark=[available[_source_id(x)] for x in eligible]
    master=pd.read_csv(MASTER,usecols=GAME_FIELDS,low_memory=False)
    old=pd.read_csv(FULL,usecols=list(set(FULL_FIELDS)|{'opponent','plate_appearances','hits','walks','stolen_bases'}),low_memory=False)
    recent=pd.read_csv(INCREMENTAL,usecols=list(set(RECENT_FIELDS)|{'opponent','plate_appearances','hits','walks','stolen_bases'}),low_memory=False)
    h,hp=merge_verified_recent_hitter_history(
        old[old.group.eq('HITTING')][['game_pk','player_id','season','official_date','game_date','game_type','status','group','opponent','team',*CHECK_STAT]],
        recent[recent.group.eq('HITTING')][['gamePk','player_id','season','officialDate','group','opponent','team',*CHECK_STAT]],
        master[GAME_FIELDS]
    )
    p,pp=reconcile_official_pitcher_history(old, recent, master)
    out,proof=build_frozen_prequote_full_context(
        eligible,sourcepark,h,p,master,now=observed,
    )
    receipts={key:sha_file(file) for key,file in {
        'original_v2_hitter_lineup':FIRST_HITTER_SOURCE,
        'first_v3_pitcher_park_research':PITCHER_PARK_SOURCE,
        'legacy_player_game_history':FULL,'new_official_boxscore_ledger':INCREMENTAL,
        'final_official_game_master':MASTER,
        'previously_frozen_16_model_beta':MODEL_SOURCE,
    }.items()}
    for r in out:
        r['original_source_sha256_at_v4_frozen']=dict(receipts)
        r['source_hitter_pregame_game_conflicts_in_reconciliation']=0
        r['source_pitcher_pregame_game_conflicts_in_reconciliation']=0
    added=append_original_prequote_full_context(OUT,out)
    saved=_read_jsonl(OUT)
    return {
        'status':proof['status'],
        'source_observed_at_utc':_utc(observed).isoformat(),
        'source_counts':proof,
        'new_context_rows':added,
        'total_source_context_rows':len(saved),
        'independent_games':len({r['game_pk'] for r in saved}),
        'large_historical_player_csv_loaded':True,
        'source_hitter_final_reconciliation':hp,
        'source_pitcher_final_reconciliation':pp,
        'source_input_sha256':receipts,
        'source_model_or_live_bets_changed':False,
        'original_bookmaker_price_not_applied_until_after_context_frozen':True,
    }


def main():
    ap=argparse.ArgumentParser(description='Freeze 2025 park/opponent/team/hitter-role 16-feature source before the next book quote')
    ap.add_argument('--stage',required=True,choices=['freeze_prior_context'])
    args=ap.parse_args()
    result=freeze_cycle()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temp=SUMMARY.with_suffix('.tmp')
    temp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    os.replace(temp,SUMMARY)
    print('MLB_BEFORE_NEW_BOOK_QUOTE_FULL_HISTORICAL_CONTEXT_RESEARCH',
          json.dumps({k:v for k,v in result.items()
                      if k not in ('source_counts','source_hitter_final_reconciliation','source_pitcher_final_reconciliation','source_input_sha256')},
                    sort_keys=True))


if __name__=='__main__':
    main()
