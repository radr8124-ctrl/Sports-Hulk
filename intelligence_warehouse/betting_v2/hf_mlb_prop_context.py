"""Historical MLB fixture/role/park/opponent context reconstructed STRICTLY as-of.

For retrospective, external betting research only. Do not use any current-game
results, confirmed current starting lineup, same-season full-season park factor,
or starting-pitcher identity obtained from after the game.
"""
from __future__ import annotations

from collections import defaultdict
import math
import pandas as pd

from .hf_mlb_prop_pilot import _utc_timestamp, safe_number

CONTEXT_VERSION = 'HF_MLB_ASOF_OPPONENT_PARK_ROLE_V1_2026_10_08'
HISTORY_SAFE_LAG_HOURS = 12


def _frame(history:pd.DataFrame, games:pd.DataFrame):
    required_players={'game_pk','player_id','player','team','opponent','group','official_date','game_date','status','game_type',
                      'plate_appearances','hits','outs','hits_allowed'}
    required_games={'gamePk','gameDate','officialDate','gameType','status','venue_id','away_team','home_team','away_score','home_score'}
    if required_players - set(history.columns):
        raise ValueError(f'Historical players missing required context fields: {sorted(required_players-set(history.columns))}')
    if required_games - set(games.columns):
        raise ValueError(f'Historical fixture data missing fields: {sorted(required_games-set(games.columns))}')
    h=history.copy()
    g=games.copy()
    h['_date']=pd.to_datetime(h.official_date,errors='coerce').dt.date
    h['_start']=pd.to_datetime(h.game_date,errors='coerce',utc=True)
    g['_date']=pd.to_datetime(g.officialDate,errors='coerce').dt.date
    g['_start']=pd.to_datetime(g.gameDate,errors='coerce',utc=True)
    h=h[h.game_type.astype(str).str.upper().eq('R') & h.status.astype(str).str.upper().eq('FINAL') & h._start.notna()].copy()
    g=g[g.gameType.astype(str).str.upper().eq('R') & g.status.astype(str).str.upper().eq('FINAL') & g._start.notna()].copy()
    g['away_score']=pd.to_numeric(g.away_score,errors='coerce')
    g['home_score']=pd.to_numeric(g.home_score,errors='coerce')
    return h,g


def _prior_year_park_reference(games:pd.DataFrame,year:int,*,min_games:int)->dict:
    prior=games[(games._date.map(lambda d:d.year if d else -1)==year-1)&games.away_score.notna()&games.home_score.notna()].copy()
    if prior.empty:return {}
    prior['_runs']=prior.away_score+prior.home_score
    league=float(prior._runs.mean())
    if not math.isfinite(league) or league<=0:return {}
    reference={}
    for park,group in prior.groupby('venue_id',dropna=True):
        if len(group)<min_games:continue
        avg=float(group._runs.mean())
        if not math.isfinite(avg):continue
        reference[int(park)]=dict(factor=round(avg/league,6),games=len(group),season=year-1,
                                  source='PRIOR_SEASON_REGULAR_SEASON_COMPLETED_ONLY')
    return reference


def enrich_historical_context(rows:list[dict],historical_players:pd.DataFrame,game_master:pd.DataFrame,
                              *,min_prior_park_games:int=40,min_opp_games:int=5,
                              min_player_games:int=5)->list[dict]:
    h,g=_frame(historical_players,game_master)
    games_by_pk={int(pk):group for pk,group in g.groupby('gamePk',sort=False)}
    by_player={pid:part.sort_values('_start') for pid,part in h[h.group.astype(str).str.upper().eq('HITTING')].groupby('player_id',dropna=True,sort=False)}
    pitching=h[h.group.astype(str).str.upper().eq('PITCHING')].copy()
    pitching['outs']=pd.to_numeric(pitching.outs,errors='coerce')
    pitching['hits_allowed']=pd.to_numeric(pitching.hits_allowed,errors='coerce')
    pitching=pitching[(pitching.outs>=0)&pitching.hits_allowed.notna() & pitching.hits_allowed.ge(0)]
    groups=pitching.groupby(['game_pk','team'],dropna=False,sort=False)
    pitch_games=groups.agg(hits_allowed=('hits_allowed','sum'),outs=('outs','sum'),
                           official_start=('_start','first'),official_date=('_date','first')).reset_index()
    pitch_games=pitch_games[pitch_games.outs.ge(15)]
    by_pitching_team={team:part.sort_values('official_start') for team,part in pitch_games.groupby('team',dropna=True,sort=False)}
    team_games=[]
    scores=g[g.home_score.notna() & g.away_score.notna()]
    for _,r in scores.iterrows():
        team_games.append({'team':r['home_team'],'date':r['_date'],'start':r['_start'],'runs_allowed':r['away_score'],
                           'runs_scored':r['home_score'],'gamePk':r['gamePk']})
        team_games.append({'team':r['away_team'],'date':r['_date'],'start':r['_start'],'runs_allowed':r['home_score'],
                           'runs_scored':r['away_score'],'gamePk':r['gamePk']})
    team_games=pd.DataFrame(team_games)
    by_team_games={team:part.sort_values('start') for team,part in team_games.groupby('team',dropna=False,sort=False)} if not team_games.empty else {}
    reference_cache={}
    outputs=[]
    for input_row in rows:
        row=dict(input_row)
        row['context_version']=CONTEXT_VERSION
        row['opposing_starter_verified_asof']=False
        row['opponent_starter_source_status']='NO_TIMESTAMPED_PREGAME_PROBABLE_STARTER'
        row['confirmed_lineup_verified_asof']=False
        row['lineup_source_status']='NO_TIMESTAMPED_PREGAME_CONFIRMED_LINEUP'
        row['weather_verified_asof']=False
        row['weather_source_status']='NO_TIMESTAMPED_HISTORICAL_WEATHER_AT_BET_CAPTURE'
        row['context_status']='RESEARCH_ROW_NOT_ELIGIBLE'
        if row.get('asof_status')!='PREGAME_FEATURE_VERIFIED' or row.get('official_group')!='HITTING':
            outputs.append(row);continue
        quote=_utc_timestamp(row.get('ts'))
        kickoff=_utc_timestamp(row.get('official_start'))
        if quote is None or kickoff is None or quote>=kickoff:
            row['context_status']='INVALID_SOURCE_PREGAME_TIME'
            outputs.append(row);continue
        try:pk=int(row.get('official_game_pk'))
        except (TypeError,ValueError):
            row['context_status']='MISSING_CURRENT_FIXTURE'
            outputs.append(row);continue
        fixture=games_by_pk.get(pk)
        if fixture is None or len(fixture)!=1:
            row['context_status']='MISSING_UNIQUE_CURRENT_FIXTURE'
            outputs.append(row);continue
        cur=fixture.iloc[0]
        fixture_start=cur['_start']
        if abs((fixture_start-kickoff).total_seconds())>180:
            row['context_status']='FIXTURE_START_MISMATCH'
            outputs.append(row);continue
        team=row.get('official_team')
        opponent=row.get('official_opponent')
        if not team or not opponent or {str(team),str(opponent)}!={str(cur.home_team),str(cur.away_team)}:
            row['context_status']='FIXTURE_TEAM_MISMATCH'
            outputs.append(row);continue
        if not cur['_date'] or cur['_date'].year<2024:
            row['context_status']='INVALID_FIXTURE_DATE'
            outputs.append(row);continue
        if quote < pd.Timestamp(f'{cur["_date"]}T00:00:00Z') - pd.Timedelta(days=2):
            row['context_status']='QUOTE_TOO_FAR_FROM_FIXTURE'
            outputs.append(row);continue
        season=cur['_date'].year
        if season not in reference_cache:
            reference_cache[season]=_prior_year_park_reference(g,season,min_games=min_prior_park_games)
        try:venue_id=int(cur.venue_id)
        except (ValueError,TypeError):venue_id=None
        park=reference_cache[season].get(venue_id)
        if park is None:
            row['context_status']='NO_PRIOR_SEASON_PARK_SAMPLE'
            outputs.append(row);continue
        pid=row.get('official_player_id')
        prior_hitter=by_player.get(pid)
        if prior_hitter is None:
            row['context_status']='NO_PRIOR_HITTER_IDENTITY'
            outputs.append(row);continue
        cutoff_day=quote.date()
        age_cutoff=quote-pd.Timedelta(hours=HISTORY_SAFE_LAG_HOURS)
        previous=prior_hitter[(prior_hitter._date<cutoff_day)&(prior_hitter._start<=age_cutoff)]
        if len(previous)<min_player_games:
            row['context_status']='INSUFFICIENT_PRIOR_PLAYER_ROLE_GAMES'
            outputs.append(row);continue
        last_team=previous.iloc[-1]['team']
        if str(last_team)!=str(team):
            row['context_status']='CURRENT_TEAM_NOT_VERIFIED_FROM_PRIOR_PLAYER_GAME'
            outputs.append(row);continue
        last10=previous.tail(10)
        pa=pd.to_numeric(last10['plate_appearances'],errors='coerce')
        if pa.notna().sum()<min(5,min_player_games):
            row['context_status']='MISSING_PRIOR_PLAYER_ROLE_STATS'
            outputs.append(row);continue
        team_pitches=by_pitching_team.get(opponent)
        team_runs=by_team_games.get(opponent)
        if team_pitches is None or team_runs is None:
            row['context_status']='NO_PRIOR_OPPONENT_TEAM_DATA'
            outputs.append(row);continue
        prior_pitch=team_pitches[(team_pitches.official_date<cutoff_day)&(team_pitches.official_start<=age_cutoff)].tail(10)
        previous_runs=team_runs[(team_runs.date<cutoff_day)&(team_runs.start<=age_cutoff)].tail(10)
        if len(prior_pitch)<min_opp_games or len(previous_runs)<min_opp_games:
            row['context_status']='INSUFFICIENT_PRIOR_OPPONENT_GAMES'
            outputs.append(row);continue
        pitch_outs=float(prior_pitch.outs.sum())
        if pitch_outs<=0:
            row['context_status']='MISSING_PRIOR_PITCHING_OUTS'
            outputs.append(row);continue
        matchup=previous[previous.opponent.astype(str).eq(str(opponent))].tail(5)
        last_date=previous.iloc[-1]['_date']
        prior_matchup_hits=pd.to_numeric(matchup.hits,errors='coerce')
        run_allowed=pd.to_numeric(previous_runs.runs_allowed,errors='coerce')
        if run_allowed.notna().sum()<min_opp_games:
            row['context_status']='MISSING_PRIOR_TEAM_RUNS_ALLOWED'
            outputs.append(row);continue
        row.update({
            'context_status':'PREGAME_CONTEXT_VERIFIED',
            'feature_asof_date':str(cutoff_day),
            'feature_minimum_prior_game_age_hours':HISTORY_SAFE_LAG_HOURS,
            'venue_id':venue_id,
            'park_run_factor':park['factor'],
            'park_reference_season':park['season'],
            'park_reference_games':park['games'],
            'park_source':park['source'],
            'player_home_flag':int(str(team)==str(cur.home_team)),
            'player_prior_latest_official_date':str(last_date),
            'player_last10_pa_avg':round(float(pa.mean()),6),
            'player_rest_days':(cutoff_day-last_date).days,
            'player_prior_role_games':len(previous),
            'hitter_vs_opponent_prior_games':len(matchup),
            'hitter_vs_opponent_prior_hits_per_game':round(float(prior_matchup_hits.mean()),6) if len(matchup) and prior_matchup_hits.notna().all() else None,
            'opponent_team_prior_games':len(previous_runs),
            'opp_prior_latest_official_date':str(previous_runs.iloc[-1]['date']),
            'opp_prior_games_available':len(prior_pitch),
            'opp_last10_pitching_hits_allowed_per_9':round(float(prior_pitch.hits_allowed.sum())*27/pitch_outs,6),
            'opp_last10_runs_allowed':round(float(run_allowed.mean()),6),
            'context_feature_provenance':'PRIOR_2025_REG_SEASON_PARK_AND_PRIOR_COMPLETED_TEAM_PLAYER_GAMES_ONLY',
        })
        outputs.append(row)
    return outputs
