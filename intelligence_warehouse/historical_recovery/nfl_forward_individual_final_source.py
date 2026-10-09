"""Individual future NFL game results, no need to wait for full week.

The prior-week FORM archive ingests only FULLY completed NFL weeks, to stop
Thursday from poisoning Sunday feature snapshots. In contrast, the source
model's RESULTS may settle an independently Final game as soon as:
- original first pre-kickoff ESPN fixture and trained model were frozen;
- original independently collected 2026 nflverse game schedule has the
  same official ESPN game ID/teams/week with both FINAL scores;
- newly fetched ESPN SCOREBOARD for that week ALSO independently says Final,
  matches team numeric ESPN IDs and aliases and the exact two scores.

A partially completed game is never a fabricated loss, a postponed kickoff
is not backdated, and a late result cannot overwrite the original grade.
Original weekly pregame form and underlying model coefficients are untouched.
"""
from __future__ import annotations

from datetime import datetime,timezone
from collections import defaultdict
from pathlib import Path
import argparse,fcntl,hashlib,json,os

import numpy as np
import pandas as pd
import requests

from .mlb_asof_feature_store import ROOT,sha_file
from .nfl_verified_2026_score_form import (
    SCHEDULE,FINAL_SCHEMA,URL,_utc,_team,_hash,
)
from .nfl_first_nine_col_forward_shadow import (
    OUTPUT as FROZEN,SCHEMA as SHADOW_SCHEMA,
)

OUTPUT=ROOT/'intelligence_warehouse/nfl_advanced_pregame/NFL_2026_FIRST_FUTURE_EVENT_ESPN_FINAL_ORIGINAL_SOURCE.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/nfl_advanced_pregame/NFL_2026_FIRST_FUTURE_EVENT_ESPN_FINAL_SOURCE_SUMMARY.json'
MAX_WEEKS_PER_CHECK=2


def _read(path):
    if not path.is_file():return []
    with path.open('r',encoding='utf-8') as fd:
        return [json.loads(s) for s in fd if s.strip()]


def _validate_original_forecasts(forecasts,*,now):
    if now.tzinfo is None:raise ValueError('Official NFL Final source clock must have timezone')
    past=set()
    for prediction in forecasts:
        game=str(prediction.get('official_espn_event_id') or '')
        if not game.isdigit() or game in past:
            raise ValueError('Duplicate or invalid originally frozen source-game ESPN ID')
        past.add(game)
        if prediction.get('schema')!=SHADOW_SCHEMA or prediction.get('betting_play_approved') is not False or prediction.get('sportsbook_wager_created') is not False:
            raise ValueError('Original future model must be research-only and pre-kickoff')
        first=_utc(prediction['official_first_pitch_utc'])
        model=_utc(prediction['source_first_real_future_prediction_frozen_at_utc'])
        if model>=first:raise ValueError('Claimed original pregame model prediction was after actual kickoff')
        if int(prediction['season'])!=2026 or int(prediction['week']) not in range(1,23):
            raise ValueError('Unknown NFL independent original football season/week source')


def verify_future_final_events(
    original_forecasts:list[dict],
    season_schedule:pd.DataFrame,
    ESPN_scoreboard:dict,*,now:datetime,schedule_sha256:str
)->tuple[list[dict],dict]:
    """Pure source audit and canonical official Final research records, no I/O."""
    _validate_original_forecasts(original_forecasts,now=now)
    if len(schedule_sha256)!=64:raise ValueError('Original independently collected NFL schedule SHA missing')
    required={'espn','game_id','season','week','home_team','away_team','home_score','away_score'}
    if required-set(season_schedule.columns):
        raise ValueError('Current NFL source schedule does not expose independently verified game scores')
    if season_schedule.espn.dropna().duplicated().any():
        raise ValueError('Duplicated source ESPN game id in original NFLverse schedule')
    games={str(int(x.espn)):x for x in season_schedule.itertuples(index=False) if pd.notna(x.espn)}
    original={str(p['official_espn_event_id']):p for p in original_forecasts}
    scoreboard={}
    for event in ESPN_scoreboard.get('events') or []:
        eid=str(event.get('id') or '')
        if not eid.isdigit() or eid in scoreboard:
            raise ValueError('Duplicated/unknown NFL Final source event in ESPN scoreboard')
        scoreboard[eid]=event
    rows=[];unmatched=0;pending_schedule=0;pending_espn=0
    for eid,forecast in original.items():
        scheduled=games.get(eid)
        if scheduled is None:raise ValueError('Original model ESPN event not found in NFLverse 2026 season')
        if (
            int(scheduled.season)!=2026 or int(scheduled.week)!=int(forecast['week'])
            or _team(scheduled.home_team)!=_team(forecast['home_team'])
            or _team(scheduled.away_team)!=_team(forecast['away_team'])
        ):
            raise ValueError('Original independent nflverse team/season/week identity mismatch')
        if pd.isna(scheduled.home_score) or pd.isna(scheduled.away_score):
            pending_schedule+=1
            continue
        event=scoreboard.get(eid)
        if event is None:
            unmatched+=1;continue
        state=(event.get('status') or {}).get('type') or {}
        if state.get('name')!='STATUS_FINAL' or state.get('completed') is not True:
            pending_espn+=1;continue
        start=_utc(event.get('date'))
        frozen_first=_utc(forecast['official_first_pitch_utc'])
        if start!=frozen_first:
            raise ValueError('Original prospective event kickoff differs from independent official Final source')
        if _utc(now)<=start:
            raise ValueError('Official NFL Final outcome claimed before kickoff')
        if str((event.get('season') or {}).get('year',2026))!='2026':
            raise ValueError('Final score is not original 2026 NFL season')
        if int((event.get('week') or {}).get('number',forecast['week']))!=int(forecast['week']):
            raise ValueError('Original scoreboard Final week differs from first frozen model')
        competitors=(event.get('competitions') or [{}])[0].get('competitors') or []
        teams={}
        for competitor in competitors:
            side=str(competitor.get('homeAway'))
            if side not in ('home','away') or side in teams:
                raise ValueError('Original ESPN scoreboard Final team sides ambiguous')
            team=competitor.get('team') or {}
            label=str(team.get('abbreviation') or '')
            expected=str(forecast[f'{side}_team'])
            if _team(label)!=expected:
                raise ValueError('Actual ESPN Final team abbreviation does not match original model team identity')
            from nfl_live.decision.espn_injury_identity import ESPN_NFL_TEAMS
            if _team(ESPN_NFL_TEAMS.get(str(team.get('id') or '')))!=expected:
                raise ValueError('Actual ESPN Final numeric team ID conflicts with original model source team')
            try:score=float(competitor['score'])
            except (ValueError,TypeError,KeyError):
                raise ValueError('Official ESPN Final has incomplete numeric team score') from None
            if not np.isfinite(score) or not score.is_integer() or score<0 or score>150:
                raise ValueError('Original ESPN Final score is not valid nonnegative integer')
            if score!=float(getattr(scheduled,f'{side}_score')):
                raise ValueError('Independent original NFLverse source score and ESPN final score conflict')
            teams[side]=(int(score),label,str(team['id']))
        if set(teams)!={'home','away'}:
            raise ValueError('Official ESPN Final event does not contain both teams')
        rows.append({
            'schema':FINAL_SCHEMA,
            'official_espn_game_id':eid,
            'game_id':str(scheduled.game_id),
            'season':2026,'week':int(scheduled.week),
            'home_team':str(forecast['home_team']),
            'away_team':str(forecast['away_team']),
            'original_espn_home_abbreviation':teams['home'][1],
            'original_espn_away_abbreviation':teams['away'][1],
            'home_espn_team_id':teams['home'][2],
            'away_espn_team_id':teams['away'][2],
            'home_points':teams['home'][0],
            'away_points':teams['away'][0],
            'source_first_pitch_utc':start.isoformat(),
            'final_observed_at_utc':_utc(now).isoformat(),
            'official_espn_final_confirmed':True,
            'source_weekly_espn_payload_sha256':_hash(ESPN_scoreboard),
            'source_season_schedule_sha256':schedule_sha256,
            'source_original_espn_final_event_sha256':_hash(event),
            'source_original_ESPN_final_event_payload':event,
            'real_original_ESPN_game_event_payload_retained':True,
            'no_prior_week_form_changed_by_incomplete_current_week':True,
            'same_game_post_kickoff_result_was_never_a_model_input':True,
            'market_model_or_wager_created':False,
        })
    return rows,{
        'status':'SOURCE_REAL_ESPN_FINAL_MATCHED_TO_INDEPENDENT_NFLVERSE_SCORE_RESEARCH_ONLY',
        'independent_football_games_with_verified_Final':len(rows),
        'scoreboard_game_events_checked':len(original),
        'independent_nflverse_final_scores_still_missing':pending_schedule,
        'original_ESPN_feed_not_yet_Final_or_event_missing':pending_espn+unmatched,
        'final_source_score_disagreements':0,
        'does_not_wait_for_whole_week_to_finish':True,
        'no_current_week_result_backfilled_into_older_frozen_features':True,
        'market_advantage_proven':False,
        'real_money_wagers_created':0,
    }


def append_first_espn_event_final(path:Path,results:list[dict])->int:
    if not results:return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+'.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        old={}
        for row in _read(path):
            if row.get('schema')!=FINAL_SCHEMA:
                raise ValueError('Unrecognized historical future NFL official score grade')
            key=row['official_espn_game_id']
            if key in old:raise ValueError('Duplicate first official ESPN Final source identity')
            old[key]=row
        new=[];seen=set()
        for row in results:
            if row.get('schema')!=FINAL_SCHEMA or row.get('market_model_or_wager_created') is not False:
                raise ValueError('Only authentic official Final source game rows allowed')
            key=row['official_espn_game_id']
            if key in seen:raise ValueError('Same official Final game provided twice')
            seen.add(key)
            if key in old:
                if old[key]!=row:
                    raise ValueError('Original first-graded ESPN score conflicts with later source revision')
                continue
            new.append(row)
        if new:
            with path.open('a',encoding='utf-8') as fd:
                for row in new:fd.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n')
                fd.flush();os.fsync(fd.fileno())
        return len(new)


def collect_cycle(
    forecast_file:Path=FROZEN,schedule_file:Path=SCHEDULE,output:Path=OUTPUT,
    *,now:datetime|None=None,
)->dict:
    current=now or datetime.now(timezone.utc)
    if current.tzinfo is None:raise ValueError('Original true final NFL event observation clock requires timezone')
    original=_read(forecast_file)
    _validate_original_forecasts(original,now=current)
    existing=_read(output)
    old={r['official_espn_game_id'] for r in existing}
    pending=[x for x in original if x['official_espn_event_id'] not in old]
    summary={
        'schema':FINAL_SCHEMA,
        'observed_utc':_utc(current).isoformat(),
        'status':'WAITING_FOR_ESPN_AND_NFLVERSE_INDEPENDENT_FINAL_SCORES',
        'original_frozen_true_forward_games':len(original),
        'remaining_to_verify_original_game_count':len(pending),
        'already_source_verified_finals_preserved':len(old),
        'verified_new_independent_final_games':0,
        'total_saved_verified_final_games':len(existing),
        'source_HTTP_calls':0,
        'postgame_results_never_written_to_old_pregame_features':True,
        'live_bets_or_original_model_predictions_changed':False,
    }
    if not pending:return summary
    schedule=pd.read_csv(schedule_file,low_memory=False)
    available={str(int(row.espn)):row for row in schedule.itertuples(index=False) if pd.notna(row.espn)}
    due=[]
    for x in pending:
        game=available.get(x['official_espn_event_id'])
        if game is None:
            raise ValueError('Original pregame ESPN game ID disappeared from 2026 source schedule')
        if _utc(current)<_utc(x['official_first_pitch_utc']):
            continue
        if pd.isna(game.home_score) or pd.isna(game.away_score):
            continue
        due.append(x)
    if not due:return summary
    received=[]
    for week in sorted({int(x['week']) for x in due})[:MAX_WEEKS_PER_CHECK]:
        response=requests.get(URL,params={'dates':2026,'seasontype':2,'week':week,'limit':100},
                headers={'User-Agent':'Sports-Zenith-NFL-Genuine-Forward-Official-Final/1.0'},
                timeout=(3,9))
        response.raise_for_status()
        summary['source_HTTP_calls']+=1
        verified,proof=verify_future_final_events(
            [x for x in due if int(x['week'])==week],schedule,response.json(),
            now=current,schedule_sha256=sha_file(schedule_file)
        )
        received.extend(verified)
    added=append_first_espn_event_final(output,received)
    summary.update({
        'status':'VERIFIED_NEW_ESPN_ORIGINAL_GAME_FINAL_RESULTS_RECEIVED_RESEARCH_ONLY' if added else summary['status'],
        'verified_new_independent_final_games':added,
        'total_saved_verified_final_games':len(_read(output)),
        'source_independently_verified_game_ids':[x['official_espn_game_id'] for x in received],
    })
    return summary


def main():
    ap=argparse.ArgumentParser(description='Collect source-verified NFL final for each originally pregame-frozen game independently of unfinished week')
    ap.add_argument('--stage',required=True,choices=['collect_original_game_finals'])
    ap.parse_args()
    result=collect_cycle()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temp=SUMMARY.with_suffix('.tmp')
    temp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    os.replace(temp,SUMMARY)
    print('NFL_TRUE_PREKICKOFF_MODEL_INDIVIDUAL_OFFICIAL_FINAL_RESEARCH',json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
