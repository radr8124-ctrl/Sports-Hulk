"""NFL first true future moneyline bookmaker-control and decade source audit.

Input sources ALREADY installed for Sports Zenith:
- 2,761 completed historical NFL games in 2016-2025, historical weather,
  roof, sportsbook lines, historical pre5 team EPA/defense/pace;
- original ESPN event ID/time/injury source snapshots captured BEFORE kickoff;
- original sportwizzard same-book/same-update HOME+AWAY American prices.

No new supplier, remote API, model fitting or wagers. Only one first prospectively
frozen quote per ESPN event; same-book no-vig reference, NOT betting edge.
The old historical actual weather or observed roof cannot masquerade as
2026 game-time forecast/confirmed roof. Injury "Active" 9 days ago cannot
become verified current clearance. Already kicked-off games excluded entirely.
"""
from __future__ import annotations

from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import math
import os
import re
import unicodedata

import numpy as np
import pandas as pd

from .mlb_asof_feature_store import ROOT,sha_file
from nfl_live.decision.espn_injury_identity import ESPN_NFL_TEAMS

SOURCE_FILE=ROOT/'intelligence_warehouse/pregame_source_evidence/NFL_PREGAME_SOURCE_EVIDENCE.jsonl'
SOURCE_RECEIPT=ROOT/'intelligence_warehouse/pregame_source_evidence/NFL_PREGAME_CAPTURE_SUMMARY.json'
HISTORICAL=ROOT/'data_vault/derived/NFL_GAME_MASTER.csv'
ALIASES=ROOT/'nfl_live/identity/team_aliases.json'
PROVIDER_MONEYLINE=ROOT/'nfl_live/game_fusion/NFL_GAME_SPORTWIZZARD_RAW.csv'
OUTPUT=ROOT/'intelligence_warehouse/pregame_source_evidence/NFL_FIRST_TRUE_PREGAME_PAIRED_BOOK_MONEYLINE_CONTROL.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/pregame_source_evidence/NFL_FIRST_TRUE_PREGAME_MARKET_HISTORY_PROVENANCE_SUMMARY.json'
SCHEMA='NFL_FIRST_VALIDATED_POST_ESPN_PREKICKOFF_BOOK_MONEYLINE_SOURCE_ONLY_V1'
PREGAME_SCHEMA='SPORTS_NHL_NFL_PREGAME_SOURCE_V1'
MAX_PRICE_AGE_MINUTES=120
VALID_STATES={'STATUS_SCHEDULED','STATUS_PRE_GAME','STATUS_PREGAME','STATUS_WARMUP'}
# ESPN week-of-game scoreboard can call Washington 'WSH' while the official
# ESPN team-id 28 and existing NFL historical/identity catalog use 'WAS'.
ESPN_ABBR_TO_HISTORICAL={'WSH':'WAS'}
MIN_VIG=1.000001
MAX_VIG=1.25
HIST_YEARS=list(range(2016,2026))


def _utc(raw)->pd.Timestamp:
    r=pd.to_datetime(raw,errors='coerce',utc=True)
    if pd.isna(r):
        raise ValueError('Original NFL source timestamp invalid or omitted')
    return r


def _n(text)->str:
    src=unicodedata.normalize('NFKD',str(text or '')).encode('ascii','ignore').decode('ascii').lower()
    return re.sub('[^a-z0-9]','',src)


def _odd_probability(american)->float|None:
    try:
        a=float(american)
        if not np.isfinite(a) or 100>abs(a) or abs(a)>10000:return None
        return float(100/(a+100) if a>0 else -a/(-a+100))
    except (ValueError,TypeError,ZeroDivisionError):
        return None


def audit_nfl_tenyear_history(master:pd.DataFrame)->tuple[list[dict],dict]:
    """Counts include full historical game results; no as-of original forecast claim."""
    required={
        'game_id','season','game_type','gameday','away_team','home_team','home_score',
        'away_score','roof','temp','wind','spread_line','total_line',
        'home_pre5_off_epa_per_play','away_pre5_def_epa_per_play'
    }
    if missing:=required-set(master.columns):
        raise ValueError('Historical NFL source is missing required game/decade fields '+str(sorted(missing)))
    if master.game_id.isna().any() or master.game_id.duplicated().any():
        raise ValueError('Historical NFL game master duplicate original game IDs')
    seasons=sorted({int(x) for x in master.season.dropna()})
    if seasons!=HIST_YEARS:
        raise ValueError('Historical NFL full archive must be preserved separately 2016-2025, not future 2026 or a cherry-picked season')
    # Football season is NOT the same as calendar year: Week 17/18 NFL
    # regular-season games can occur the FOLLOWING January. This is 142
    # authentic 2016-25 regular-season records, not a corrupt game date.
    regular=master[master.game_type.eq('REG')].copy()
    reg_date=pd.to_datetime(regular.gameday,errors='coerce')
    reg_year=reg_date.dt.year
    reg_month=reg_date.dt.month
    official_season=regular.season.astype(int)
    valid_reg=(reg_year.eq(official_season)
               | (reg_year.eq(official_season+1)&reg_month.eq(1)))
    if reg_date.isna().any() or not valid_reg.all():
        raise ValueError('Regular NFL season dates must be in season or the following January')
    if not set(master.game_type.dropna()).issubset({'REG','WC','DIV','CON','SB'}):
        raise ValueError('Unknown historical NFL season stage')
    observed_roof={'dome','closed','open','outdoors'}
    if not set(master.roof.dropna().unique()).issubset(observed_roof):
        raise ValueError('Unrecognized roof state in original historical NFL source')
    results=[]
    for yr,group in master.groupby('season',sort=True):
        field_count=lambda name:int(group[name].notna().sum())
        results.append({
            'season':int(yr),
            'independent_games':len(group),
            'verified_source_unique_game_ids':int(group.game_id.nunique()),
            'final_score_rows':int((group.home_score.notna()&group.away_score.notna()).sum()),
            'historical_roof_rows':field_count('roof'),
            'historical_temp_rows':field_count('temp'),
            'historical_wind_rows':field_count('wind'),
            'recorded_historical_spread_rows':field_count('spread_line'),
            'recorded_historical_total_rows':field_count('total_line'),
            'prior5_off_epa_rows':field_count('home_pre5_off_epa_per_play'),
            'prior5_def_epa_rows':field_count('away_pre5_def_epa_per_play'),
        })
    return results,{
        'schema':'NFL_DECADE_HISTORICAL_SOURCE_AND_PRIOR_TIMING_AUDIT_20261008',
        'seasons':seasons,
        'historical_games':len(master),
        'unique_game_ids':int(master.game_id.nunique()),
        'season_counts':results,
        'historical_weather_is_original_pregame_forecast':False,
        'historical_temp_wind_are_game_OBSERVED_NOT_KICKOFF_FORECAST':True,
        'stored_roof_is_verified_future_2026_open_closed_state':False,
        'history_was_retrospectively_collected_for_past_games':True,
        'pre5_epa_columns_require_provenance_before_forward_model':True,
        'current_2026_games_must_be_separately_captured':True,
        'history_source_does_not_prove_2026_sportsbook_market_edge':True,
    }


def _validated_espn_sources(source:list[dict],now:pd.Timestamp,aliases:dict)->dict:
    valid={}
    duplicates=set()
    for event in source:
        if event.get('schema')!=PREGAME_SCHEMA or event.get('sport') not in (None,'NFL'):
            raise ValueError('Unrecognized original NFL ESPN immutable pregame evidence')
        if event.get('starter_confirmed') is not False or event.get('model_pick_approved') is not False or event.get('bankroll_or_sportsbook_action') is not False:
            raise ValueError('ESPN original pregame record falsely indicates starter or betting approval')
        gid=str(event.get('official_game_id') or '')
        if not gid.isdigit():raise ValueError('Unverified original ESPN event id')
        ts=_utc(event.get('captured_at_utc'))
        kickoff=_utc(event.get('scheduled_start_utc'))
        if ts>=kickoff or ts>now or kickoff<=now:
            continue
        fx=event.get('fixture') or {}
        if fx.get('game_state_asof') not in VALID_STATES:
            continue
        for side in ('home','away'):
            team=str(fx.get(f'{side}_team') or '')
            historic_team=ESPN_ABBR_TO_HISTORICAL.get(team,team)
            ident=str(fx.get(f'{side}_espn_team_id') or '')
            actual=str(fx.get(f'{side}_espn_team_name') or '')
            if ESPN_NFL_TEAMS.get(ident)!=historic_team:
                raise ValueError('ESPN source team ID conflicts with canonical NFL abbreviation')
            approved=[_n(x) for x in aliases.get(historic_team,[]) if ' ' in str(x).strip()]
            if _n(actual) not in approved:
                raise ValueError('Official ESPN team name conflicts with canonical NFL team ID')
        if fx['home_team']==fx['away_team']:
            raise ValueError('Invalid ESPN original same-team fixture')
        if fx.get('season_year')!=2026:
            raise ValueError('Not the current 2026 official NFL game season')
        if fx.get('actual_stadium_roof_state')!='UNKNOWN_NOT_OBSERVED':
            # This collector did not capture verified roof status, so a new
            # "confirmed open/closed" assertion is not safe.
            raise ValueError('ESPN venue indoor flag cannot be treated as actual roof status')
        k=(gid,ts.isoformat())
        if k in duplicates:
            raise ValueError('Repeated original NFL ESPN source event capture slot')
        duplicates.add(k)
        previous=valid.get(gid)
        if previous is not None:
            old_start=_utc(previous['scheduled_start_utc'])
            if abs((old_start-kickoff).total_seconds())>180:
                raise ValueError('Conflicting original NFL ESPN scheduled kickoff snapshots')
        if previous is None or ts>_utc(previous['captured_at_utc']):
            valid[gid]=event
    return valid


def build_verified_nfl_bookmaker_baselines(
    original_espn:list[dict], raw_quotes:pd.DataFrame, *,now:datetime,
    market_file_mtime_utc:datetime,
    original_source_file_sha256:str,
    source_market_file_sha256:str,
    tenyear_history_sha256:str,
    aliases:dict|None=None,
    minimum_quote_time_by_espn_event_id:dict[str,datetime]|None=None,
)->tuple[list[dict],dict]:
    if now.tzinfo is None:
        raise ValueError('Research freeze requires an actual UTC-offset-aware source time')
    current=_utc(now)
    file_time=_utc(market_file_mtime_utc)
    for digest in (original_source_file_sha256,source_market_file_sha256,tenyear_history_sha256):
        if len(digest)!=64:
            raise ValueError('Each original ESPN, bookmaker and historical source requires SHA256')
    if file_time>current:
        return [],{'independent_future_game_blocks':0,'status':'MARKET_SOURCE_FILE_NOT_YET_OBSERVED'}
    if aliases is None:
        aliases=json.loads(ALIASES.read_text())
    events=_validated_espn_sources(original_espn,current,aliases)
    required={
        'provider','sportsbook','event_id','start','away_team','home_team','market_subtype',
        'side','price_american','updated'
    }
    if missing:=required-set(raw_quotes.columns):
        raise ValueError('Incomplete original bookmaker paired market fields '+str(sorted(missing)))
    q=raw_quotes.copy()
    q=q[q.market_subtype.astype(str).eq('MONEYLINE')].copy()
    q['side']=q.side.astype(str).str.upper()
    q=q[q.side.isin(['HOME','AWAY'])].copy()
    q['_start']=pd.to_datetime(q.start,utc=True,errors='coerce')
    q['_quoted']=pd.to_datetime(q.updated,utc=True,errors='coerce')
    q=q[q._start.notna()&q._quoted.notna()].copy()
    q=q[q._quoted.le(current)
        & q._quoted.le(file_time+pd.Timedelta(seconds=5))
        & q._quoted.ge(current-pd.Timedelta(minutes=MAX_PRICE_AGE_MINUTES))].copy()
    # Some upstream bookmakers label DIFFERENT prices as the same bookmaker,
    # event, update timestamp and moneyline side. Mixing those into a synthetic
    # two-sided pair would be fake precision. Quarantine *all* such ambiguous
    # groups, while retaining unambiguous books for that fixture.
    key=['provider','sportsbook','event_id','updated','side']
    proposals=defaultdict(list)
    suppressed=Counter()
    ambiguous=q.duplicated(key,keep=False)
    if ambiguous.any():
        ambiguous_books=q.loc[ambiguous].groupby(key[:-1],dropna=False).ngroups
        suppressed['ambiguous_duplicate_book_side_source']+=int(ambiguous_books)
        bad=q.loc[ambiguous,key[:-1]].drop_duplicates()
        to_skip={
          tuple(str(v) for v in values)
          for values in bad.itertuples(index=False,name=None)
        }
        q=q.loc[[
          tuple(str(v) for v in values) not in to_skip
          for values in q[key[:-1]].itertuples(index=False,name=None)
        ]].copy()
    for (provider,book,event,updated),group in q.groupby(key[:-1],sort=False,dropna=False):
        if len(group)!=2 or set(group.side)!={'HOME','AWAY'}:
            suppressed['not_two_sided_at_same_book_quote_time']+=1
            continue
        home=group.loc[group.side.eq('HOME')].iloc[0]
        away=group.loc[group.side.eq('AWAY')].iloc[0]
        if (home.home_team!=away.home_team or home.away_team!=away.away_team
            or home.start!=away.start):
            suppressed['mixed_fixture_or_book_group']+=1
            continue
        quote_time=_utc(updated)
        market_start=_utc(home.start)
        if quote_time>=market_start:
            suppressed['no_pregame_book_quote']+=1
            continue
        fixture_candidates=[]
        for eid,captured in events.items():
            fx=captured['fixture']
            if (str(home.home_team)!=str(fx['home_espn_team_name'])
                or str(home.away_team)!=str(fx['away_espn_team_name'])):
                continue
            official_start=_utc(captured['scheduled_start_utc'])
            if abs((official_start-market_start).total_seconds())>180:
                continue
            original_capture=_utc(captured['captured_at_utc'])
            if not original_capture<quote_time<official_start:
                continue
            fixture_candidates.append((eid,captured))
        if len(fixture_candidates)>1:
            raise ValueError('Ambiguous original ESPN event crosswalk for one sportsbook market game')
        if not fixture_candidates:
            suppressed['unmatched_original_espn_identity_or_start']+=1
            continue
        eid,captured=fixture_candidates[0]
        if minimum_quote_time_by_espn_event_id is not None:
            # The original first-market baseline is allowed to use its
            # earlier pregame quote, but an advanced-context model can ONLY
            # take a new actual quote observed AFTER all input features
            # have been source-frozen. Never backdate completed team results.
            cutoff=minimum_quote_time_by_espn_event_id.get(eid)
            if cutoff is None or quote_time<=_utc(cutoff):
                suppressed['price_before_new_advanced_source_context_freeze']+=1
                continue
        away_price=_odd_probability(away.price_american)
        home_price=_odd_probability(home.price_american)
        if away_price is None or home_price is None:
            suppressed['invalid_original_american_price']+=1
            continue
        vig=home_price+away_price
        if not MIN_VIG<vig<=MAX_VIG:
            suppressed['invalid_original_book_overround']+=1
            continue
        original_capture=_utc(captured['captured_at_utc'])
        fixture=captured['fixture']
        injured=captured.get('injuries') or {}
        injury_entries=[x for side in ('home','away') for x in injured.get(side,[]) or []]
        stale_count=0
        for injury in injury_entries:
            reported=injury.get('source_reported_at_utc')
            if reported is None:
                stale_count+=1;continue
            reporttime=pd.to_datetime(reported,utc=True,errors='coerce')
            if pd.isna(reporttime) or reporttime>original_capture or (original_capture-reporttime)>pd.Timedelta(hours=48):
                stale_count+=1
        candidate={
            'schema':SCHEMA,
            'official_espn_event_id':eid,
            'source_provider_event_id':str(event),
            'source_provider':str(provider),
            'source_book':str(book),
            'original_source_espn_captured_at_utc':original_capture.isoformat(),
            'source_original_book_quote_updated_at_utc':quote_time.isoformat(),
            'book_provider_snapshot_file_mtime_utc':file_time.isoformat(),
            'observed_source_only_research_frozen_at_utc':current.isoformat(),
            'official_espn_kickoff_utc':_utc(captured['scheduled_start_utc']).isoformat(),
            'source_provider_game_start_utc':market_start.isoformat(),
            'official_espn_home_team_id':str(fixture['home_espn_team_id']),
            'official_espn_away_team_id':str(fixture['away_espn_team_id']),
            'home_team_abbr':ESPN_ABBR_TO_HISTORICAL.get(str(fixture['home_team']),str(fixture['home_team'])),
            'away_team_abbr':ESPN_ABBR_TO_HISTORICAL.get(str(fixture['away_team']),str(fixture['away_team'])),
            'source_original_espn_home_abbr':str(fixture['home_team']),
            'source_original_espn_away_abbr':str(fixture['away_team']),
            'home_team_full_name':str(fixture['home_espn_team_name']),
            'away_team_full_name':str(fixture['away_espn_team_name']),
            'season':2026,
            'week':int(fixture['week']),
            'venue_name_from_ESPN':str(fixture.get('venue_name')),
            'venue_indoor_attribute':bool(fixture.get('venue_indoor_attribute')),
            'actual_stadium_roof_status':'UNKNOWN_NOT_OBSERVED',
            'indoor_venue_does_not_confirm_roof':True,
            'source_last_2026_weather_forecast_confirmed':False,
            'source_2025_historical_weather_not_future_2026_forecast':True,
            'original_injury_source_reports_checked':len(injury_entries),
            'stale_or_unverified_injury_source_reports':stale_count,
            'stale_injury_reported_as_game_clearance':False,
            'injury_reporting_not_verified_active_or_starting_player':True,
            'source_record_time_published_asof_espn_fixture_not_game_outcome':True,
            'original_book_away_american':float(away.price_american),
            'original_book_home_american':float(home.price_american),
            'raw_book_overround':round(float(vig),12),
            'raw_fair_home_prob':round(float(home_price/vig),12),
            'raw_fair_away_prob':round(float(away_price/vig),12),
            'original_over_under_moneyline_home_source':{
                'provider':str(home.provider),'event_id':str(home.event_id),
                'sportsbook':str(home.sportsbook),'side':'HOME',
                'price_american':float(home.price_american),'updated':str(home.updated),
            },
            'original_over_under_moneyline_away_source':{
                'provider':str(away.provider),'event_id':str(away.event_id),
                'sportsbook':str(away.sportsbook),'side':'AWAY',
                'price_american':float(away.price_american),'updated':str(away.updated),
            },
            'source_original_nfl_espn_evidence_sha256':original_source_file_sha256,
            'source_original_bookmaker_market_sha256':source_market_file_sha256,
            'source_2016_2025_historical_game_master_sha256':tenyear_history_sha256,
            'verified_original_pre_kickoff_source':True,
            'model_prediction_calculated':False,
            'model_trained_or_promoted':False,
            'game_outcome_not_yet_known_at_freeze':True,
            'betting_play_approved':False,
            'sportsbook_wager_executed':False,
            'book_prices_independently_confirmed_at_named_book':False,
            'commercial_redistribution_rights_verified':False,
            'this_quote_counts_as_independent_game_block_only_once':True,
        }
        proposals[eid].append(candidate)
    winner=[]
    for gid,rows in proposals.items():
        # First quote selection independent of outcome: minimum SOURCE vig.
        # If multiple books qualify, store one original canonical book only.
        selected=min(rows,key=lambda x:(
            x['raw_book_overround'],
            x['source_original_book_quote_updated_at_utc'],
            x['source_book'],
            x['source_provider'],
        ))
        winner.append(selected)
    winner.sort(key=lambda x:(x['official_espn_kickoff_utc'],x['official_espn_event_id']))
    return winner,{
        'status':'FROZEN_FUTURE_SOURCE_PAIRED_MONEYLINE_RESEARCH_CONTROL_ONLY',
        'independent_future_game_blocks':len(winner),
        'future_original_espn_games_checked':len(events),
        'quote_book_groups_matched_to_original_espn':sum(map(len,proposals.values())),
        'book_groups_rejected':dict(suppressed),
        'original_source_archive_is_not_a_confirmed_current_roof_or_injury_clearance':True,
        'model_probability_or_play_promoted':False,
        'historical_weather_is_recovered_observed_game_history_only':True,
    }


def _read_jsonl(path:Path)->list[dict]:
    if not path.exists():return []
    with path.open('r',encoding='utf-8') as f:
        return [json.loads(x) for x in f if x.strip()]


def append_immutable_nfl_book_control(path:Path,rows:list[dict])->int:
    if not rows:return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix('.jsonl.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        seen={}
        for saved in _read_jsonl(path):
            if saved.get('schema')!=SCHEMA:raise ValueError('Existing source baseline has foreign schema')
            gid=saved['official_espn_event_id']
            if gid in seen:raise ValueError('Duplicated first original NFL source fixture baseline')
            seen[gid]=saved
        new=[];batch=set()
        for x in rows:
            if x.get('schema')!=SCHEMA or x.get('betting_play_approved') is not False or x.get('model_prediction_calculated') is not False:
                raise ValueError('An executable betting decision cannot masquerade as paired book source')
            if _utc(x['observed_source_only_research_frozen_at_utc'])>=_utc(x['official_espn_kickoff_utc']):
                raise ValueError('Never create a newly backdated source after NFL kickoff')
            gid=x['official_espn_event_id']
            if gid in batch:raise ValueError('Duplicate new future official ESPN game')
            batch.add(gid)
            if gid not in seen:new.append(x)
        if new:
            with path.open('a',encoding='utf-8') as fd:
                for item in new:fd.write(json.dumps(item,sort_keys=True,separators=(',',':'))+'\n')
                fd.flush();os.fsync(fd.fileno())
        return len(new)


def freeze_cycle(now:datetime|None=None)->dict:
    current=now or datetime.now(timezone.utc)
    if current.tzinfo is None:raise ValueError('NFL pregame research source-time clock naive')
    original=_read_jsonl(SOURCE_FILE)
    if not original:raise ValueError('No original NFL source-time ESPN event snapshots')
    history=pd.read_csv(HISTORICAL,low_memory=False)
    seasons,historical=audit_nfl_tenyear_history(history)
    q=pd.read_csv(PROVIDER_MONEYLINE,low_memory=False)
    aliases=json.loads(ALIASES.read_text())
    odds,summary=build_verified_nfl_bookmaker_baselines(
        original,q,now=current,
        market_file_mtime_utc=datetime.fromtimestamp(PROVIDER_MONEYLINE.stat().st_mtime,timezone.utc),
        original_source_file_sha256=sha_file(SOURCE_FILE),
        source_market_file_sha256=sha_file(PROVIDER_MONEYLINE),
        tenyear_history_sha256=sha_file(HISTORICAL),
        aliases=aliases,
    )
    appended=append_immutable_nfl_book_control(OUTPUT,odds)
    saved=_read_jsonl(OUTPUT)
    receipt={
        'schema':SCHEMA,
        'observed_at_utc':_utc(current).isoformat(),
        'status':summary.get('status'),
        'original_frozen_source_espn_games':summary.get('future_original_espn_games_checked',0),
        'independent_games_in_first_accepted_future_market_baseline':len({x['official_espn_event_id'] for x in saved}),
        'new_first_bookmaker_price_game_baselines_added':appended,
        'total_immutable_game_moneyline_price_baselines':len(saved),
        'current_source_pairing_audit':summary,
        'historical_ten_year_source':historical,
        'source_paths_sha256':{
            'official_espn_pregame_capture':sha_file(SOURCE_FILE),
            'source_multibook_game_prices':sha_file(PROVIDER_MONEYLINE),
            'original_10_year_historical_games':sha_file(HISTORICAL),
            'canonical_team_identity_aliases':sha_file(ALIASES),
        },
        'original_spreads_and_totals_as_proof_of_wagers':False,
        'game_outcomes_used_to_select_book_quotes':False,
        'real_money_bets_created':False,
        'model_with_proven_market_edge_deployed':False,
    }
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temp=SUMMARY.with_suffix('.tmp')
    temp.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    os.replace(temp,SUMMARY)
    print('NFL_DECADE_HISTORICAL_AND_PREKICKOFF_PAIRED_MONEYLINE_RESEARCH',{
        k:receipt[k] for k in (
            'observed_at_utc','independent_games_in_first_accepted_future_market_baseline',
            'new_first_bookmaker_price_game_baselines_added','total_immutable_game_moneyline_price_baselines',
            'real_money_bets_created'
        )})
    return receipt


def main():
    ap=argparse.ArgumentParser(description='True as-of NFL historical sources and first paired bookmaker-only moneyline controls')
    ap.add_argument('--stage',choices=['freeze_source_only'],required=True)
    args=ap.parse_args()
    freeze_cycle()

if __name__=='__main__':main()
