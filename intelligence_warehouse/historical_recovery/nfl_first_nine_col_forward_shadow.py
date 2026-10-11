"""Frozen NFL 2026 score-form + moneyline prospective probabilities (NO BETS).

An independently ESPN-verified prior-WEEK score-form context and original
2016-24 fixed model MUST both be frozen BEFORE a NEW source bookmaker same
book HOME+AWAY moneyline pair is actually quoted. Raw/no-vig, fitted
market-only and nine-column player/team-source research probabilities
share exactly one original source bookmaker/quote time. Prior 13 source-only
market baselines remain immutable; no production NFL/Survivor picks changed.

Secondary 2025 diagnostic showed challenger WORSE than market. Therefore
this challenger is PROSPECTIVE RESEARCH ONLY, without model-edge claim.
"""
from __future__ import annotations

from datetime import datetime,timezone
from pathlib import Path
import argparse,fcntl,hashlib,json,math,os

import numpy as np
import pandas as pd

from .mlb_asof_feature_store import ROOT,sha_file
from .nfl_verified_2026_score_form import (
    CONTEXT,CONTEXT_SCHEMA,ESPN_PREGAME,HISTORICAL,SCHEDULE,_team,
)
from .nfl_prior_score_form_model import (
    MODEL,VERSION,SOURCE_FEATURE_NAMES,_prob,_logit,
)
from .nfl_tenyear_forward_market_provenance import (
    build_verified_nfl_bookmaker_baselines,SOURCE_FILE,PROVIDER_MONEYLINE,
    ALIASES,SCHEMA as PRICE_SOURCE_SCHEMA,
)

OUTPUT=ROOT/'intelligence_warehouse/nfl_advanced_pregame/NFL_FIRST_PREKICKOFF_NINE_FEATURE_SCORE_FORM_SHADOW.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/nfl_advanced_pregame/NFL_NINE_FEATURE_PROSPECTIVE_SHADOW_SOURCE_SUMMARY.json'
SCHEMA='NFL_2026_FIRST_RESEARCH_NINE_FEATURE_SAME_NEW_QUOTE_MARKET_COMPARISON_V1'


def _utc(v):
    x=pd.to_datetime(v,errors='coerce',utc=True)
    if pd.isna(x):raise ValueError('Source-time original moneyline or model context timestamp unknown')
    return x


def _read(path):
    if not path.is_file():return []
    with path.open('r',encoding='utf-8') as fd:return [json.loads(x) for x in fd if x.strip()]


def _eligible_model(model:dict,sha:str):
    if model.get('model_version')!=VERSION or model.get('features')!=list(SOURCE_FEATURE_NAMES):
        raise ValueError('Unrecognized originally fixed NFL historical nine-feature market challenger')
    if len(model.get('coefficients') or [])!=9 or len(model.get('two_col_market_only_coefficients') or [])!=2:
        raise ValueError('Missing trained nine-column or same-cohort market-only model coefficients')
    if model.get('training_2025_outcomes_used') is not False or model.get('training_2026_outcomes_used') is not False:
        raise ValueError('Research training cohort is contaminated with 2025/2026 future result')
    if model.get('2026_live_betting_play_approved') is not False or model.get('real_bookmaker_market_edge_proven') is not False:
        raise ValueError('Prospective training model cannot be declared approved/live')
    if model.get('training_seasons')!=list(range(2016,2025)) or model.get('secondary_holdout_seasons')!=[2025]:
        raise ValueError('Original frozen 2016-24 train and 2025 heldout scopes changed')
    if not model.get('training_independent_games',0)>=2000:
        raise ValueError('Insufficient originally frozen real independent team games')
    if len(sha)!=64:
        raise ValueError('Missing frozen model source SHA')
    for name in ('coefficients','two_col_market_only_coefficients'):
        if not np.isfinite(np.asarray(model[name],dtype=float)).all():
            raise ValueError('Unstable or altered frozen NFL source model')


def _fair(raw_book):
    home=float(raw_book['original_book_home_american'])
    away=float(raw_book['original_book_away_american'])
    def p(x):
        if not 100<=abs(x)<=10000:raise ValueError('Invalid original bookmaker American source price')
        return 100/(100+x) if x>0 else (-x)/(100-x)
    ho=p(home);aw=p(away)
    overround=ho+aw
    if not 1.000001<overround<=1.25:
        raise ValueError('Invalid same-book genuine bookmaker overround')
    fair=float(ho/overround)
    if (abs(fair-float(raw_book['raw_fair_home_prob']))>2e-6
        or abs(1-fair-float(raw_book['raw_fair_away_prob']))>2e-6
        or abs(overround-float(raw_book['raw_book_overround']))>2e-6):
        raise ValueError('Original sportsbook two-sided de-vig calculation is inconsistent')
    return fair


def build_same_quote_nfl_shadow(
    original_context:list[dict],paired_quotes:list[dict],model:dict,*,
    now:datetime,model_file_sha256:str,source_market_sha256:str,
)->tuple[list[dict],dict]:
    if now.tzinfo is None:raise ValueError('Prospective research freeze must carry original clock timezone')
    _eligible_model(model,model_file_sha256)
    if len(source_market_sha256)!=64:raise ValueError('Original sportsbook source file SHA missing')
    t=_utc(now)
    fixed_at=_utc(model['trained_frozen_at_utc'])
    ctx={}
    for item in original_context:
        if item.get('schema')!=CONTEXT_SCHEMA or item.get('betting_play_authorized') is not False:
            raise ValueError('Unrecognized 2026 source-verified pregame prior-form context')
        eid=str(item['official_espn_event_id'])
        if eid in ctx:raise ValueError('Duplicated prequote ESPN event context')
        ctx[eid]=item
        if item['source_frozen_training_model_sha256']!=model_file_sha256:
            raise ValueError('Future team scoring source was frozen against different historical model SHA')
        if len(item.get('nine_features_excluding_market') or [])!=7:
            raise ValueError('Incomplete source verified 2026 pregame feature vector')
        if item.get('actual_stadium_roof_state_confirmed') is not False:
            raise ValueError('Roof status not verified by the 2026 ESPN original source')
    proposals={}
    for quote in paired_quotes:
        if quote.get('schema')!=PRICE_SOURCE_SCHEMA or quote.get('betting_play_approved') is not False or quote.get('model_prediction_calculated') is not False:
            raise ValueError('Original source pair must not be a claimed bookmaker bet/model prediction')
        eid=str(quote['official_espn_event_id'])
        if eid not in ctx:
            raise ValueError('Same-book provider source NFL game/event identity cannot match new original ESPN model source')
        item=ctx[eid]
        if (_team(item['home_team'])!=_team(quote['home_team_abbr'])
            or _team(item['away_team'])!=_team(quote['away_team_abbr'])):
            raise ValueError('Same-book opponent team identity disagrees with frozen ESPN context')
        start=_utc(item['official_first_pitch_utc'])
        market_start=_utc(quote['official_espn_kickoff_utc'])
        context_at=_utc(item['source_team_form_first_frozen_at_utc'])
        quoted=_utc(quote['source_original_book_quote_updated_at_utc'])
        source_created=_utc(quote['observed_source_only_research_frozen_at_utc'])
        if start!=market_start:
            raise ValueError('Official ESPN first-pitch source disagrees with source bookmaker')
        # No provider/price can be attached retrospectively to inputs first
        # assembled after that quote. Final outcome cannot appear here.
        if not (fixed_at<context_at<quoted<=source_created<=t<start):
            continue
        if item['season']!=2026 or item.get('week') is None:
            raise ValueError('Wrong original 2026 season pregame source')
        if eid in proposals:raise ValueError('Expected one first chosen same-book moneyline per original ESPN event')
        fair=_fair(quote)
        x=[1.,_logit(fair),*[float(z) for z in item['nine_features_excluding_market']]]
        if len(x)!=9 or not np.isfinite(np.asarray(x)).all():
            raise ValueError('Prospective fixed nine-feature source vector missing values')
        calibrated=_prob(x[:2],model['two_col_market_only_coefficients'])
        full=_prob(x,model['coefficients'])
        if not all(.001<v<.999 for v in [calibrated,full]):
            raise ValueError('Malformed original research model probability')
        proposals[eid]={
            'schema':SCHEMA,
            'official_espn_event_id':eid,
            'source_schedule_game_id':item['source_schedule_game_id'],
            'season':2026,'week':int(item['week']),
            'home_team':item['home_team'],'away_team':item['away_team'],
            'source_original_current_week_espn_capture_at_utc':item['original_pregame_espn_captured_at_utc'],
            'source_independent_2026_final_games_sha256':item['source_original_2026_scoreboard_sha256'],
            'source_2026_schedule_sha256':item['source_2026_schedule_sha256'],
            'source_original_feature_context_sha256':item['source_2026_schedule_sha256'],
            'source_context_features_frozen_at_utc':context_at.isoformat(),
            'source_qualified_book_quote_updated_at_utc':quoted.isoformat(),
            'source_book_name':quote['source_book'],
            'source_provider':quote['source_provider'],
            'original_source_provider_event_uuid':quote['source_provider_event_id'],
            'original_source_market_snapshot_sha256':source_market_sha256,
            'source_frozen_model_sha256':model_file_sha256,
            'model_version':VERSION,
            'model_training_seasons':model['training_seasons'],
            'model_training_independent_games':model['training_independent_games'],
            'original_same_book_american_home_moneyline':quote['original_book_home_american'],
            'original_same_book_american_away_moneyline':quote['original_book_away_american'],
            'original_same_book_overround':quote['raw_book_overround'],
            'original_raw_book_home_fair':float(fair),
            'market_only_calibrated_home_win_prob':round(float(calibrated),12),
            'nine_feature_score_form_home_win_prob':round(float(full),12),
            'model_feature_vector':[round(float(z),10) for z in x],
            'model_feature_names':list(SOURCE_FEATURE_NAMES),
            'source_first_real_future_prediction_frozen_at_utc':t.isoformat(),
            'official_first_pitch_utc':start.isoformat(),
            'original_source_bookmaker_price_not_a_verified_executable_offer':True,
            'historic_2025_diagnostic_slightly_worse_than_raw_market':True,
            'source_2025_holdout_was_already_evaluated_and_not_pristine_future':True,
            'source_2026_current_final_scores_are_prior_week_features_only':True,
            'same_game_result_used_for_features':False,
            '2016_2025_original_EPA_pbp_independent_replay_completed':False,
            'source_outcome_still_unknown_before_first_kickoff':True,
            'source_is_game_moneyline_not_player_proposition':True,
            'actual_roof_or_game_weather_confirmed':False,
            'verified_current_quarterback_starter_or_inactive_status_claimed':False,
            'original_first_13_book_source_only_baselines_changed':False,
            'independent_game_block_id':eid,
            'research_only':True,
            'betting_play_approved':False,
            'sportsbook_wager_created':False,
            'predicted_market_advantage_proven':False,
        }
    rows=sorted(proposals.values(),key=lambda r:(r['official_first_pitch_utc'],r['official_espn_event_id']))
    return rows,{
        'schema':SCHEMA,
        'source_frozen_before_all_kickoffs':True,
        'independent_forward_game_blocks':len(rows),
        'market_vig_and_two_original_prices_per_one_game_matched':True,
        'source_2025_out_of_sample_historical_comparison_inspected_not_a_profit_claim':True,
        'frozen_original_source_model_market_not_retrained':True,
        'model_market_edge_proven':False,
        'new_wagers':0,
    }


def _read(path):
    if not path.is_file():return []
    with path.open('r',encoding='utf-8') as f:
        return [json.loads(x) for x in f if x.strip()]


def append_first_immutable_game_shadow(path:Path,rows:list[dict])->int:
    if not rows:return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+'.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        seen={}
        for item in _read(path):
            if item.get('schema')!=SCHEMA:raise ValueError('Old NFL model-probability ledger has foreign schema')
            id_=str(item['official_espn_event_id'])
            if id_ in seen:raise ValueError('Duplicate previous original NFL score-form shadow game')
            seen[id_]=item
        pending=[];added=set()
        for item in rows:
            if (item.get('schema')!=SCHEMA or item.get('betting_play_approved') is not False
                or item.get('sportsbook_wager_created') is not False):
                raise ValueError('Only research-only predictions from original source accepted')
            id_=str(item['official_espn_event_id'])
            if id_ in added:raise ValueError('Duplicate new forward model game')
            added.add(id_)
            if _utc(item['source_first_real_future_prediction_frozen_at_utc'])>=_utc(item['official_first_pitch_utc']):
                raise ValueError('Model cannot create first pregame forecast AFTER first kickoff')
            if id_ in seen:
                if seen[id_]!=item:
                    raise ValueError('First saved NFL model prediction conflicts with later quote/retrain, do not overwrite')
                continue
            pending.append(item)
        if pending:
            with path.open('a',encoding='utf-8') as fd:
                for x in pending:fd.write(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n')
                fd.flush();os.fsync(fd.fileno())
        return len(pending)


def freeze_cycle(now:datetime|None=None)->dict:
    clock=now or datetime.now(timezone.utc)
    if clock.tzinfo is None:raise ValueError('Observation timezone required')
    already=_read(OUTPUT)
    known={r['official_espn_event_id'] for r in already}
    contexts=[x for x in _read(CONTEXT)
              if x['official_espn_event_id'] not in known
              and _utc(clock)<_utc(x['official_first_pitch_utc'])]
    if not contexts:
        return {
            'schema':SCHEMA,'status':'ALL_PRIOR_FIRST_GAME_SHADOW_PREDICTIONS_PROTECTED_OR_GAME_STARTED',
            'observed_at_utc':_utc(clock).isoformat(),
            'new_9feature_original_game_forecasts':0,
            'total_first_frozen_game_forecasts':len(already),
            'original_market_book_source_read':False,
            'live_bets_changed':False,
        }
    model=json.loads(MODEL.read_text())
    sha=sha_file(MODEL)
    _eligible_model(model,sha)
    raw=pd.read_csv(PROVIDER_MONEYLINE,low_memory=False)
    source=_read(ESPN_PREGAME)
    cutoffs={r['official_espn_event_id']:_utc(r['source_team_form_first_frozen_at_utc'])
             for r in contexts}
    books,source_receipt=build_verified_nfl_bookmaker_baselines(
        source,raw,now=clock,
        market_file_mtime_utc=datetime.fromtimestamp(PROVIDER_MONEYLINE.stat().st_mtime,timezone.utc),
        original_source_file_sha256=sha_file(ESPN_PREGAME),
        source_market_file_sha256=sha_file(PROVIDER_MONEYLINE),
        tenyear_history_sha256=sha_file(HISTORICAL),
        minimum_quote_time_by_espn_event_id=cutoffs,
    )
    matched=[x for x in books if x['official_espn_event_id'] in cutoffs]
    proposed,details=build_same_quote_nfl_shadow(
        contexts,matched,model,now=clock,
        model_file_sha256=sha,
        source_market_sha256=sha_file(PROVIDER_MONEYLINE),
    )
    newly=append_first_immutable_game_shadow(OUTPUT,proposed)
    saved=_read(OUTPUT)
    return {
        'schema':SCHEMA,
        'status':'PROSPECTIVE_FIRST_NFL_GAME_MONEYLINE_MODEL_FROZEN_RESEARCH_ONLY' if newly else 'WAITING_FOR_NEW_GENUINE_BOOK_PRICE_AFTER_SOURCE_FORM_FREEZE',
        'observed_at_utc':_utc(clock).isoformat(),
        'new_9feature_original_game_forecasts':newly,
        'total_first_frozen_game_forecasts':len(saved),
        'independent_future_game_blocks':len({r['official_espn_event_id'] for r in saved}),
        'candidate_official_espn_pregame_games':len(contexts),
        'book_pair_original_quote_current_source_status':source_receipt,
        'source_2016_2024_training_model_sha256':sha,
        'source_2026_independent_pregame_team_form_sha256':sha_file(CONTEXT),
        'source_current_original_book_quotes_sha256':sha_file(PROVIDER_MONEYLINE),
        'full_epa_or_actual_weather_used':False,
        '2025_secondary_diag_market_was_better':True,
        'market_edge_proven_or_wagers_submitted':False,
    }


def main():
    p=argparse.ArgumentParser(description='First true pregame NFL historical score-form versus same-new-quote market baseline')
    p.add_argument('--stage',required=True,choices=['freeze_after_new_quote'])
    p.parse_args()
    result=freeze_cycle()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    temporary=SUMMARY.with_suffix('.tmp')
    temporary.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    os.replace(temporary,SUMMARY)
    print('NFL_2026_PREQUOTE_NINE_FEATURE_SCORE_FORM_RESEARCH',json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
