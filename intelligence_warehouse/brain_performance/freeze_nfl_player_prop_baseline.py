"""Frozen forward NFL prop/PrizePicks challenger, deliberately NOT a PLAY model.

Pre-registered before computing: reports/ZENITH_NFL_PLAYER_PROPS_FIRST_WEEK5_MODEL_CHALLENGER_PREREG_2026-10-09.json
Uses exactly weeks 1-4 of 2026 regular-season player game stats, not any
week-5 outcome. One official event/player/stat/side/line independent research
opportunity even if both NFL_PROP and NFL_PRIZEPICKS display the same outcome.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import math, json, os, re
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
REGISTER=ROOT/'reports/ZENITH_NFL_PLAYER_PROPS_FIRST_WEEK5_MODEL_CHALLENGER_PREREG_2026-10-09.json'
ADDENDUM=ROOT/'reports/ZENITH_NFL_PROP_WEEK5_PINNED_INPUT_ADDENDUM_2026-10-09.json'
FROZEN=ROOT/'intelligence_warehouse/brain_performance/preregistered/NFL_PLAYER_LINE_INDEPENDENT_FORM_CHALLENGER_2026_WEEK5.json'
PUBLIC=ROOT/'commercial_web/public/nfl_prop_independent_research.json'
DIST=ROOT/'commercial_web/dist/nfl_prop_independent_research.json'
SCHEMA='ZENITH_FIRST_NFL_PROP_PP_EMPIRICAL_INDEPENDENT_RESEARCH_V1'
STATS={
 'PLAYER_TOTAL_PASS_ATTEMPTS':'attempts',
 'PLAYER_TOTAL_PASS_COMPLETIONS':'completions',
 'PLAYER_TOTAL_INTERCEPTIONS':'passing_interceptions',
 'PLAYER_TOTAL_REC_YARDS':'receiving_yards',
 'PLAYER_TOTAL_RECEPTIONS':'receptions',
 'PLAYER_TOTAL_RUSH_YARDS':'rushing_yards',
 'PLAYER_TOTAL_RUSH_ATTEMPTS':'carries',
}
TEAM_ALIAS={'JAC':'JAX','WSH':'WAS','LAR':'LA'}
SOURCES={
 'nfl_player_stat_history':'nfl_live/player_context/raw/player_stats.parquet',
 'nfl_prop_v2_current':'commercial_web/public/prop_v2_current.json',
 'nfl_prop_identity_fusion':'nfl_live/fusion/NFL_PROP_CONTEXT_READY_V2.csv',
 'nfl_official_scheduled_games':'commercial_web/public/nfl_scores.json'
}

def checksum(p):return sha256(Path(p).read_bytes()).hexdigest()
def norm(s):return re.sub('[^a-z0-9]','',str(s or '').lower())
def utc(v):
 dt=pd.to_datetime(v,utc=True,errors='coerce')
 if pd.isna(dt):raise ValueError('Missing UTC source timestamp')
 return dt.to_pydatetime()
def qualify_float(x):
 value=float(x)
 if not math.isfinite(value):raise ValueError('Invalid numeric source')
 return value

def derive(prereg:dict, *, at:datetime)->dict:
 if at.tzinfo is None:raise ValueError('Require timezone-aware freeze')
 if prereg.get('schema')!='ZENITH_NFL_INDEPENDENT_PLAYER_LINE_BASELINE_PREREG_V1':raise ValueError('Missing preregistered research rules')
 pinned=json.loads(ADDENDUM.read_text())
 if pinned.get('schema')!='ZENITH_NFL_PLAYER_PROP_PREREG_INPUT_PINNING_ADDENDUM_V1':
  raise ValueError('Pinned source addendum must be registered')
 if pinned.get('original_preregistration_sha256')!=checksum(REGISTER):
  raise ValueError('Pinned source addendum references another original registration')
 checked={}
 for key,path in SOURCES.items():
  orig=prereg['source_sha256'][key]['sha256']
  info=pinned['pinned_inputs'][key]
  fp=(ROOT/info['path']).resolve()
  if not fp.is_relative_to(ROOT) or not fp.is_file():
   raise ValueError('Missing safe pinned research snapshot')
  current=checksum(fp)
  if current!=info['sha256'] or info['prereg_original_sha256']!=orig:
   raise ValueError('Original pinned source does not match prereg or addendum')
  if key!='nfl_official_scheduled_games' and current!=orig:
   raise ValueError('Non-scoreboard input was modified after prereg')
  checked[key]=fp
 picks=json.loads(checked['nfl_prop_v2_current'].read_text())
 data=[p for p in picks.get('picks',[]) if p.get('sport')=='NFL' and p.get('lane_key') in {'NFL_PROP','NFL_PRIZEPICKS'}]
 raw=pd.read_parquet(checked['nfl_player_stat_history'])
 assert set(STATS.values()).issubset(raw.columns)
 # This explicit cutoff also rejects already finalized Week-5 records captured early.
 hist=raw[(raw.season==2026)&(raw.season_type=='REG')&(raw.week>=1)&(raw.week<=4)].copy()
 fusion=pd.read_csv(checked['nfl_prop_identity_fusion'],low_memory=False)
 scores=json.loads(checked['nfl_official_scheduled_games'].read_text())
 fixtures=[f for key in ('games','next_games') for f in scores.get(key,[]) if isinstance(f,dict)]
 histories=defaultdict(list)
 for _,r in hist.iterrows():
  pname=norm(r['player_display_name'])
  if pname:histories[pname].append(r)
 opportunities=defaultdict(list)
 for p in data:
  key=(str(p['event_id']),str(p['player_key']),str(p['market_subtype']),
       str(p['side']),float(p['line']))
  opportunities[key].append(p)
 result=[]
 seen=set()
 for key,lanes in sorted(opportunities.items()):
  event_uuid,player_key,subtype,side,line=key
  if subtype not in STATS or side not in ('OVER','UNDER'):
   raise ValueError('Unregistered NFL prop stat or selection side')
  if any(x.get('shadow_decision')=='SHADOW_PLAY' for x in lanes):
   raise ValueError('Model source unexpectedly qualified as live bet')
  if len(lanes)!=len(set(x['lane_key'] for x in lanes)):
   raise ValueError('Duplicate same-lane market selection in source')
  if not all(x.get('v2_probability_pct')==x.get('market_reference_probability_pct') for x in lanes):
   raise ValueError('Unexpected independent model in source: prespec must be revised')
  if any(x.get('market_reference_type') not in ('DEVIG_FAIR','RAW_FALLBACK') for x in lanes):
   raise ValueError('Unexpected source reference type')
  f=fusion[
   (fusion['event_id_dfs'].astype(str)==event_uuid)&
   (fusion['player_key'].astype(str)==player_key)&
   (fusion['market_subtype'].astype(str)==subtype)&
   (fusion['side'].astype(str)==side)&
   (pd.to_numeric(fusion['line'],errors='coerce').round(4)==round(line,4))
  ]
  if f.empty:raise ValueError('Missing exact original fantasy/book source crosswalk')
  candidates=f[['away_team','home_team','start_dfs','newest_update','player_team']].drop_duplicates()
  if len(candidates)!=1:raise ValueError('Source provider identity or time ambiguity')
  matched=candidates.iloc[0]
  fixture_matches=[]
  for g in fixtures:
   if norm(g.get('away'))!=norm(matched['away_team']) or norm(g.get('home'))!=norm(matched['home_team']):
    continue
   if abs((utc(g['start_time'])-utc(matched['start_dfs'])).total_seconds())>180:continue
   if abs((utc(g['start_time'])-utc(lanes[0]['event_start'])).total_seconds())>180:continue
   fixture_matches.append(g)
  if len(fixture_matches)!=1:
   raise ValueError('No unique original official NFL fixture for prop: '+event_uuid)
  game=fixture_matches[0]
  scheduled=utc(game['start_time'])
  quoted=utc(matched['newest_update'])
  if not quoted<=at<scheduled:raise ValueError('Future/out-of-date source game or quote')
  h=histories.get(player_key,[])
  if len(h)!=4:raise ValueError('Four full prior completed weekly player games required: '+player_key)
  player_ids={str(r['player_id']) for r in h}
  if len(player_ids)!=1 or len({int(r['week']) for r in h})!=4:
   raise ValueError('Historical player identity or week mismatch')
  teams={str(r['team']) for r in h}
  home=TEAM_ALIAS.get(str(game['home_abbr']),str(game['home_abbr']))
  away=TEAM_ALIAS.get(str(game['away_abbr']),str(game['away_abbr']))
  player_team_name=norm(matched['player_team'])
  if player_team_name==norm(game['home']) and player_team_name!=norm(game['away']):
   actual_team=home
  elif player_team_name==norm(game['away']) and player_team_name!=norm(game['home']):
   actual_team=away
  else:
   raise ValueError('Provider player team name does not match one official game team')
  if not actual_team or teams!={actual_team} or actual_team not in (home,away):
   raise ValueError('Historical player-team roster/fixture crosswalk ambiguous')
  if norm(lanes[0]['player'])!=player_key:raise ValueError('Source player name normalized mismatch')
  values=[qualify_float(r[STATS[subtype]]) for r in sorted(h,key=lambda r:r['week'])]
  # Official football receiving/rushing yards can legitimately be negative.
  # Negative receptions, targets or pass/completion counts cannot.
  if any(v<0 for v in values) and STATS[subtype] not in ('rushing_yards','receiving_yards'):
   raise ValueError('Negative count statistic in source')
  success=sum(v>line if side=='OVER' else v<line for v in values)
  pushes=sum(v==line for v in values)
  # Beta(2,2) prior is fixed in the preregistration (NOT fitting outcome).
  independent=round(100*(success+2)/(4+4),3)
  variants=[]
  for lane in sorted(lanes,key=lambda l:l['lane_key']):
   reference=qualify_float(lane['market_reference_probability_pct'])
   if not 0.0<reference<100:raise ValueError('Unqualified baseline probability')
   variants.append({
     'lane':lane['lane_key'],
     'reference_type':lane['market_reference_type'],
     'market_reference_pct':reference,
     'model_current_pct_equal_market_pct':lane['v2_probability_pct'],
     'market_plus_empirical_20pct_challenger_pct':round(.8*reference+.2*independent,3),
     'original_book_count':lane['data_quality_book_count'],
     'devig_paired_books':lane['devig_paired_books'],
     'original_line_was_approved_play':False,
     'bookmaker_moneyline_price_not_prizepicks_pickem_payout':True,
   })
  label=(str(game['event_id']),str(player_ids.pop()),subtype,side,line)
  if label in seen:raise ValueError('Duplicate official independent prop outcome')
  seen.add(label)
  result.append({
    'source_game_id':str(game['event_id']),
    'book_provider_event_uuid':event_uuid,
    'start_utc':scheduled.isoformat(),
    'away_team':str(game['away_abbr']),
    'home_team':str(game['home_abbr']),
    'player':str(lanes[0]['player']),
    'verified_player_team_from_prior_season_games':actual_team,
    'market':subtype,
    'side':side,
    'line':line,
    'source_latest_book_quote_updated_at_utc':quoted.isoformat(),
    'original_provider_price_age_hours_at_freeze':round((at-quoted).total_seconds()/3600,3),
    'historical_previous_four_regular_2026_week_stats':values,
    'historical_week_numbers':[1,2,3,4],
    'history_games':4,
    'prior_week_hit_count':success,
    'prior_week_push_count':pushes,
    'prior_week_average':round(sum(values)/4,3),
    'empirical_smoothed_success_frequency_pct_NOT_CALIBRATED':independent,
    'same_player_prop_opportunity_source_lanes':variants,
    'unique_opportunity_not_game_independent_proof':True,
    'official_player_game_results_already_verified_for_prior_weeks':False,
    'official_pre_kickoff_player_injury_and_active_confirmation_verified':False,
    'historical_2026_four_week_form_only_no_matchup_player_model':True,
    'independent_model_beats_sportsbook_proven':False,
    'approved_play':False,
    'quoted_price_confirmed_executable_now':False,
  })
 result.sort(key=lambda r:(r['start_utc'],r['source_game_id'],r['player'],r['market'],r['side'],r['line']))
 return {
  'schema':SCHEMA,'frozen_at_utc':at.astimezone(timezone.utc).isoformat(),
  'prior_prereg_file_sha256':checksum(REGISTER),
  'input_sha256':{key:checksum(fp) for key,fp in checked.items()},
  'pinned_source_addendum_sha256':checksum(ADDENDUM),
  'first_forward_fixture_season':'2026_REGULAR_WEEK_5',
  'model':'BETA_2_2_FOUR_PRIOR_REGULAR_GAME_EMPIRICAL_BASELINE_V1',
  'all_selection_lanes_input_count':len(data),
  'unique_player_line_event_opportunity_count':len(result),
  'unique_official_game_blocks':len({r['source_game_id'] for r in result}),
  'NFL_PROP_input_count':sum(x['lane_key']=='NFL_PROP' for x in data),
  'NFL_PRIZEPICKS_input_count':sum(x['lane_key']=='NFL_PRIZEPICKS' for x in data),
  'overlap_source_rows_not_independent_outcomes':len(data)-len(result),
  'source_price_not_current_executable_offer':True,
  'all_research_only_and_uncalibrated':True,
  'no_preexisting_final_game_week5_outcome_as_model_feature':True,
  'no_predictions_retrained_or_promoted':True,
  'no_wagers_or_real_prizepicks_payouts':True,
  'official_future_player_grade_proof_pending':True,
  'rows':result
 }

def write_new(path:Path,data:dict):
 path.parent.mkdir(parents=True,exist_ok=True)
 blob=(json.dumps(data,indent=2,sort_keys=True)+'\n').encode()
 with path.open('xb') as handle:
  handle.write(blob);handle.flush();os.fsync(handle.fileno())
 assert path.read_bytes()==blob

def publish_view(original:dict, *, now:datetime|None=None) -> dict:
 timestamp=now or datetime.now(timezone.utc)
 if timestamp.tzinfo is None:raise ValueError('Naive timestamp')
 filtered=[x for x in original.get('rows',[]) if utc(x['start_utc'])>timestamp]
 clean=[]
 for raw in filtered:
  # Public web UI shows only research summary, never internal player IDs and
  # no source-private provider snapshots or betting access credentials.
  allowed=['source_game_id','start_utc','away_team','home_team','player','market','side','line',
           'historical_previous_four_regular_2026_week_stats','history_games','prior_week_hit_count',
           'prior_week_push_count','prior_week_average','empirical_smoothed_success_frequency_pct_NOT_CALIBRATED',
           'same_player_prop_opportunity_source_lanes','independent_model_beats_sportsbook_proven',
           'official_pre_kickoff_player_injury_and_active_confirmation_verified','approved_play']
  obj={key:raw[key] for key in allowed}
  obj['source_quote_age_hours_at_publication']=round((timestamp-utc(raw['source_latest_book_quote_updated_at_utc'])).total_seconds()/3600,2)
  obj['original_quote_over_24h_old']=obj['source_quote_age_hours_at_publication']>24
  obj['source_latest_book_quote_updated_at_utc']=raw['source_latest_book_quote_updated_at_utc']
  clean.append(obj)
 return {
  'schema':'ZENITH_NFL_PROP_PP_RESEARCH_PUBLIC_V1',
  'generated_at_utc':timestamp.astimezone(timezone.utc).isoformat(),
  'preregistered_model_sha256':original.get('prior_prereg_file_sha256'),
  'frozen_at_utc':original.get('frozen_at_utc'),
  'source_model':'BETA_2_2_FOUR_PRIOR_REGULAR_GAME_EMPIRICAL_BASELINE_V1',
  'sport':'NFL',
  'competition_regime':'2026_REGULAR_WEEK_5',
  'original_lane_observations':original.get('all_selection_lanes_input_count'),
  'independent_player_line_opportunities_at_freeze':original.get('unique_player_line_event_opportunity_count'),
  'independent_games_at_freeze':original.get('unique_official_game_blocks'),
  'source_PP_and_PROP_overlap_rows':original.get('overlap_source_rows_not_independent_outcomes'),
  'current_future_research_opportunities':len(clean),
  'unproven_model_not_recommendations':True,
  'must_verify_sportsbook_quote_and_game_day_injuries_before_any_bet':True,
  'prizepicks_payout_not_sportsbook_american_odds':True,
  'real_wagers_placed':False,
  'rows':clean,
 }

def main():
 prereg=json.loads(REGISTER.read_text())
 if FROZEN.exists():
  original=json.loads(FROZEN.read_text())
  if original.get('schema')!=SCHEMA or original.get('prior_prereg_file_sha256')!=checksum(REGISTER):
   raise ValueError('Existing frozen research must not be silently replaced')
  # Re-publishing may hide expired games but never rebuild prior forecasts.
 else:
  original=derive(prereg,at=datetime.now(timezone.utc))
  write_new(FROZEN,original)
  print('FROZEN_NEW_NFL_INDEPENDENT_PROP_RESEARCH',len(original['rows']))
 # One timestamp, one exact public payload to prevent data-version races
 # between the website source tree and the live compiled site.
 payload=publish_view(original)
 for output in (PUBLIC,DIST):
  output.parent.mkdir(parents=True,exist_ok=True)
  temp=output.with_name('.'+output.name+'.tmp')
  if temp.exists():raise ValueError('Another version of this public projection publishing')
  with temp.open('xb') as f:
   blob=(json.dumps(payload,sort_keys=True,indent=2)+'\n').encode()
   f.write(blob);f.flush();os.fsync(f.fileno())
  os.replace(temp,output)
 print('PUBLIC_FROZEN_PROP_PP_RESEARCH_FEED',len(payload['rows']))
 print('ORIGINAL_FROZEN_SHA256',checksum(FROZEN))
 print('NO_APPROVED_NFL_PROPS_OR_PP_BETS',payload['real_wagers_placed'])

if __name__=='__main__': main()
