"""Frozen historical 16-input context MLB research model on NEW pregame quotes.

The older 90-game original coefficients are reused without refitting. Extra
prior opponent TEAM pitching, defensive scores, 2025 park and hitter-form
context was really source-frozen BEFORE the new paired book snapshot (not
backdated into the first already-frozen sportsbook/model probabilities).

This is a true prospective challenger for source-verified MLB hits OVER 0.5.
A listed probable starter and NWS forecast are retained as provenance, but
the original 16-col model was NOT trained on a known current starter/weather.
No live wagering or betting model promotion is possible from this module.
"""
from __future__ import annotations

from collections import Counter
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
from .mlb_full_context_source_time import (
    OUT as SOURCE_CONTEXT,
    SCHEMA as V4_SCHEMA,
    BASE_CONTEXT_KEYS,
)
from .mlb_speed_walks_research import (
    BASE_FEATURE_NAMES,EXTRA_FEATURE_NAMES,
    MODEL_VERSION as FULL_MODEL_VERSION,
)
from .mlb_paired_pregame_market_freeze import (
    select_paired_market_sources,
    SCHEMA as PAIR_SCHEMA,
    FUSION,
    MARKET_HISTORY,
    ORIGINAL_PREGAME_LINEUPS,
)
from .mlb_live_research_feature_freeze_v2 import (
    OUTPUT as V2,
    SCHEMA as V2_SCHEMA,
)
from .mlb_research_forward_labels import verify_original_pregame_source

MODEL=ROOT/'reports/mlb_feature_integration_20261008/MLB_SPEED_WALKS_FROZEN_RESEARCH_MODEL.json'
PREREGISTRATION=ROOT/'reports/mlb_feature_integration_20261008/MLB_SIXTEEN_FEATURE_PREQUOTE_FULL_CONTEXT_SHADOW_PREREGISTRATION_2026-10-08.md'
OUT=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V4_SIXTEEN_FEATURE_ACTUAL_FORWARD_SHADOW.jsonl'
SUMMARY=ROOT/'intelligence_warehouse/mlb_pregame_capture/MLB_V4_SIXTEEN_FEATURE_SHADOW_CAPTURE_SUMMARY.json'
SHADOW_SCHEMA='MLB_V4_FULL_16_FEATURE_PREQUOTE_POST_CONTEXT_SAME_BOOK_SHADOW_V1'
MODEL_POSITIONAL_MAPPING=tuple(zip(BASE_CONTEXT_KEYS,[*BASE_FEATURE_NAMES[2:],*EXTRA_FEATURE_NAMES]))
MAX_QUOTES=5000


def _utc(x)->pd.Timestamp:
    a=pd.to_datetime(x,utc=True,errors='coerce')
    if pd.isna(a):
        raise ValueError('Missing or ambiguous historical source pregame/quote timestamp')
    return a


def _read_jsonl(path:Path)->list[dict]:
    if not path.exists():return []
    with path.open('r',encoding='utf-8') as f:
        return [json.loads(x) for x in f if x.strip()]


def _p_american(odds)->float:
    o=float(odds)
    if not np.isfinite(o) or abs(o)<100 or abs(o)>10000:
        raise ValueError('Invalid original bookmaker American odds')
    return float(100/(100+o)) if o>0 else float((-o)/(100-o))


def _logit(prob)->float:
    p=float(prob)
    if not .001<p<.999 or not np.isfinite(p):
        raise ValueError('Invalid bookmaker de-vigged fair probability for market model')
    return math.log(p/(1-p))


def _sigmoid(x)->float:
    if x>=0:
        a=math.exp(-min(700,x))
        return 1/(1+a)
    a=math.exp(max(-700,x))
    return a/(1+a)


def _model_ok(frozen:dict,sha:str)->None:
    if frozen.get('model_version')!=FULL_MODEL_VERSION:
        raise ValueError('Unrecognized earlier pre-July frozen historical 16-column model')
    if frozen.get('feature_names')!=[*BASE_FEATURE_NAMES,*EXTRA_FEATURE_NAMES] or len(frozen.get('with_speed_walks_beta') or [])!=16:
        raise ValueError('Frozen historical 16-col feature schema/coefficients differ')
    if frozen.get('training_independent_games')!=90 or len(set(frozen.get('training_official_game_pks') or []))!=90:
        raise ValueError('Different training cohort or duplicated independent MLB game IDs')
    if frozen.get('train_july_outcomes_used') is not False or frozen.get('live_plays_approved') is not False:
        raise ValueError('July outcomes entered frozen model or incorrectly marked LIVE PLAY approved')
    if len(frozen.get('market_calibration_beta') or [])!=2:
        raise ValueError('No same-trained-market-calibration baseline coefficients')
    if len(sha)!=64:
        raise ValueError('Original saved frozen training model SHA-256 is missing')


def _key(row:dict)->tuple:
    return int(row['official_game_pk'] if 'official_game_pk' in row else row['game_pk']),int(row['mlbam_player_id'] if 'mlbam_player_id' in row else row['player_id'])


def _pair_ok(quote:dict,source:dict,now:pd.Timestamp)->bool:
    if quote.get('schema')!=PAIR_SCHEMA or quote.get('betting_selection_approved') is not False or quote.get('model_prediction_created') is not False:
        raise ValueError('Not an original two-sided same-book research source')
    if quote.get('market_metric')!='hits' or float(quote.get('line',-1))!=.5:
        return False
    for side in ('over','under'):
        raw=quote.get(f'{side}_provider_source_row')
        if not isinstance(raw,dict):
            raise ValueError('Original over and under bookmaker provider rows both required')
        if (
            raw.get('sportsbook')!=quote.get('sportsbook') or
            raw.get('provider')!=quote.get('provider') or
            raw.get('player_id')!=quote.get('provider_player_id') or
            raw.get('event_id')!=quote.get('provider_event_id') or
            raw.get('market_subtype')!=quote.get('market_subtype') or
            str(raw.get('side')).upper()!=side.upper() or
            float(raw.get('line'))!=float(quote['line']) or
            _utc(raw.get('captured_at'))!=_utc(quote.get('source_snapshot_quote_at_utc'))
        ):
            raise ValueError('Not the same-book/line/player/provider/time original over-under pair')
    implied_over=_p_american(quote['price_over_american'])
    implied_under=_p_american(quote['price_under_american'])
    overround=implied_over+implied_under
    if abs(overround-float(quote['book_overround']))>2e-6:
        raise ValueError('Original paired American prices have inconsistent overround')
    fair=implied_over/overround
    if abs(fair-float(quote['market_fair_probability_over']))>2e-6:
        raise ValueError('Original source no-vig fair price calculation inconsistent')
    quote_at=_utc(quote['source_snapshot_quote_at_utc'])
    context_at=_utc(source['full_team_context_first_frozen_at_utc'])
    start=_utc(source['original_game_first_pitch_utc'])
    if (
        quote_at<=context_at or quote_at>now or quote_at>=start
        or now>=start
        or _utc(quote['fixture_scheduled_start_utc'])!=start
    ):
        return False
    if quote.get('original_lineup_source_line_sha256')!=source['original_prequote_hitter_source_sha256']:
        raise ValueError('Different original official MLBAM player lineup SHA between contexts and book odds')
    return True


def eligible_same_quote_full_context_shadow(
    sources:list[dict], paired_book_quotes:list[dict],frozen_model:dict,
    *,now:datetime,original_model_sha256:str,
    source_fusion_sha256:str,source_market_snapshot_sha256:str,
)->tuple[list[dict],dict]:
    if now.tzinfo is None:raise ValueError('Now must carry official prospective timezone')
    _model_ok(frozen_model,original_model_sha256)
    obs=_utc(now)
    if not all(len(x)==64 for x in [source_fusion_sha256,source_market_snapshot_sha256]):
        raise ValueError('Original source market and MLBAM fusion digests missing')
    lookup={}
    for source in sources:
        if source.get('schema')!=V4_SCHEMA or source.get('live_play_approved') is not False or source.get('source_model_probability_or_bet_created') is not False:
            raise ValueError('Only original as-of research context can enter frozen 16-col model')
        key=_key(source)
        if key in lookup:raise ValueError('Source context contains duplicate official game.player identity')
        if source.get('historical_training_16_feature_model_schema')!=FULL_MODEL_VERSION:
            raise ValueError('Prospective source feature version is not original trained 16-col model')
        if source.get('sixteen_model_component_names_except_market')!=[a for a,b in MODEL_POSITIONAL_MAPPING]:
            raise ValueError('16-feature source positional mapping schema differs')
        numeric=source.get('sixteen_model_components_except_market') or []
        if len(numeric)!=14 or not np.isfinite(np.asarray(numeric,dtype=float)).all():
            raise ValueError('Missing one of fourteen original prior-only feature sources')
        lookup[key]=source
    possible={}
    for quote in paired_book_quotes:
        key=_key(quote)
        if key not in lookup:
            raise ValueError('Original bookmaker paired price player identity cannot join official as-of source')
        source=lookup[key]
        if _pair_ok(quote,source,obs):
            possible.setdefault(key,[]).append(quote)
    result=[]
    beta=np.asarray(frozen_model['with_speed_walks_beta'],dtype=float)
    market_beta=np.asarray(frozen_model['market_calibration_beta'],dtype=float)
    if not np.isfinite(beta).all() or not np.isfinite(market_beta).all():
        raise ValueError('Corrupted original frozen model coefficients')
    for key,options in possible.items():
        # Book selection is deterministic from pregame source OVERROUND only,
        # independent of any outcome/model-favored probability.
        chosen=min(options,key=lambda x:(
            float(x['book_overround']),
            str(x['source_snapshot_quote_at_utc']),
            str(x['sportsbook']),
            str(x['provider']),
        ))
        source=lookup[key]
        fair=float(chosen['market_fair_probability_over'])
        vec=[1.,_logit(fair)]+[float(x) for x in source['sixteen_model_components_except_market']]
        if len(vec)!=16:
            raise ValueError('Unexpected model feature vector length')
        challenger=_sigmoid(float(np.dot(beta,np.asarray(vec))))
        calibrator=_sigmoid(float(np.dot(market_beta,np.asarray(vec[:2]))))
        if not .001<challenger<.999 or not .001<calibrator<.999:
            raise ValueError('Implausible fitted prospective probability')
        if key[0] in frozen_model['training_official_game_pks'] or _utc(frozen_model['training_last_start'])>=_utc(source['original_game_first_pitch_utc']):
            raise ValueError('Frozen current fixture overlaps prior training or fitted model is from future')
        row={
            'schema':SHADOW_SCHEMA,
            'official_game_pk':key[0],
            'mlbam_player_id':key[1],
            'player_name_official':chosen['player_name_official'],
            'market_metric':'hits',
            'line':.5,
            'canonical_probability_side':'OVER',
            'selected_sportsbook':chosen['sportsbook'],
            'source_provider':chosen['provider'],
            'source_provider_player_uuid':chosen['provider_player_id'],
            'source_provider_event_uuid':chosen['provider_event_id'],
            'source_quote_at_utc':chosen['source_snapshot_quote_at_utc'],
            'source_team_context_frozen_at_utc':source['full_team_context_first_frozen_at_utc'],
            'source_probable_pitcher_and_park_frozen_at_utc':source['verified_probable_park_source_first_frozen_at_utc'],
            'original_lineup_sha256':source['original_prequote_hitter_source_sha256'],
            'frozen_model_version':frozen_model['model_version'],
            'frozen_prejuly_model_sha256':original_model_sha256,
            'frozen_training_independent_games':90,
            'source_fusion_sha256':source_fusion_sha256,
            'source_raw_market_sha256':source_market_snapshot_sha256,
            'source_prequote_context_input_sha256':sha_file(SOURCE_CONTEXT) if SOURCE_CONTEXT.exists() else None,
            'model_feature_names':[*BASE_FEATURE_NAMES,*EXTRA_FEATURE_NAMES],
            'model_16_features':[round(float(x),10) for x in vec],
            'source_raw_over_american':chosen['price_over_american'],
            'source_raw_under_american':chosen['price_under_american'],
            'source_book_overround':chosen['book_overround'],
            'market_fair_prob_at_exact_new_quote':fair,
            'market_only_calibrated_prob_at_same_new_quote':round(float(calibrator),12),
            'sixteen_feature_context_shadow_prob':round(float(challenger),12),
            'first_full_context_shadow_frozen_at_utc':obs.isoformat(),
            'official_first_pitch_utc':source['original_game_first_pitch_utc'],
            'probable_pitcher_confirmed_starter_model_input':False,
            'actual_weather_or_roof_used_in_frozen_trained_model':False,
            'source_training_is_historical_regular_to_postseason_domain_shift':True,
            'has_any_july_outcomes_in_fitted_coefficients':False,
            'full_context_is_pre_first_pitch_source_frozen':True,
            'full_context_is_after_first_earlier_price_not_backdated':True,
            'existing_first_market_only_and_restricted_8_feature_predictions_untouched':True,
            'independent_game_block_id':str(key[0]),
            'research_only':True,
            'model_market_edge_proven':False,
            'betting_play_approved':False,
            'wager_executed':False,
        }
        result.append(row)
    result.sort(key=lambda r:(r['official_game_pk'],r['mlbam_player_id']))
    return result,{
        'status':'BEFORE_KICKOFF_16TERM_CONTEXT_AND_NEW_PAIR_BOOK_SOURCE_PROSPECTIVE_MODEL_FROZEN',
        'rows':len(result),
        'independent_games':len({r['official_game_pk'] for r in result}),
        'distinct_official_player_ids':len({r['mlbam_player_id'] for r in result}),
        'same_quote_context_before_odds_verified':True,
        'fit_model_training_games':frozen_model['training_independent_games'],
        'frozen_model_vs_market_advantage_unproven':True,
        'profitability_proven':False,
        'play_authorized':False,
        'upstream_provider_redistribution_rights_unverified':True,
    }


def _key_out(row:dict)->tuple:
    return int(row['official_game_pk']),int(row['mlbam_player_id']),float(row['line'])


def append_first_full_context_prediction(path:Path,rows:list[dict])->int:
    if not rows:return 0
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix(path.suffix+'.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        old={}
        for x in _read_jsonl(path):
            if x.get('schema')!=SHADOW_SCHEMA:
                raise ValueError('Unknown prior 16-col prediction source')
            key=_key_out(x)
            if key in old:raise ValueError('Duplicate original prospective player forecast')
            old[key]=x
        incoming=set();new=[]
        for x in rows:
            if x.get('schema')!=SHADOW_SCHEMA or x.get('betting_play_approved') is not False or x.get('wager_executed') is not False:
                raise ValueError('Only research-only source-time probability may be first-frozen')
            if _utc(x['first_full_context_shadow_frozen_at_utc'])>=_utc(x['official_first_pitch_utc']):
                raise ValueError('Postgame probability must not masquerade as frozen pregame source')
            k=_key_out(x)
            if k in incoming:raise ValueError('Duplicate same-batch official first-frozen player/market')
            incoming.add(k)
            if k in old:
                if old[k]!=x:
                    raise ValueError('Original 16-feature pregame forecast conflicts with a later quote/model result')
                continue
            new.append(x)
        if new:
            with path.open('a',encoding='utf-8') as fd:
                for x in new:
                    fd.write(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n')
                fd.flush();os.fsync(fd.fileno())
        return len(new)


def freeze_cycle(now:datetime|None=None)->dict:
    obs=now or datetime.now(timezone.utc)
    if obs.tzinfo is None:raise ValueError('No timezone-aware original pregame model observation clock')
    original=_read_jsonl(OUT)
    known={(int(x['official_game_pk']),int(x['mlbam_player_id'])) for x in original}
    prior=_read_jsonl(SOURCE_CONTEXT)
    unseen=[x for x in prior
            if (int(x['game_pk']),int(x['player_id'])) not in known
            and _utc(obs)<_utc(x['original_game_first_pitch_utc'])]
    if not unseen:
        return {
            'status':'NO_NEW_VERIFIED_PLAYER_TO_FREEZE_FULL_16_MODEL_OR_FIRST_PITCH_PASSED',
            'captured_at_utc':_utc(obs).isoformat(),
            'new_full_context_forecasts':0,
            'total_first_frozen_context_forecasts':len(original),
            'independent_game_blocks':len({x['official_game_pk'] for x in original}),
            'expensive_source_market_not_loaded':True,
            'research_only_no_wager':True,
        }
    paths=sorted(MARKET_HISTORY.glob('MLB_PLAYER_PROP_MARKET_*.csv'))
    if not paths:raise ValueError('Missing originally timestamped sportsbook snapshot files')
    target=paths[-1]
    raw=pd.read_csv(target,low_memory=False)
    if len(raw)>200000:
        raise ValueError('Unexpectedly large source snapshot, bounded source-only import refused')
    fusion=pd.read_csv(FUSION,low_memory=False)
    original_source={}
    with ORIGINAL_PREGAME_LINEUPS.open('r',encoding='utf-8') as f:
        for line in f:
            if line.strip():
                k=hashlib.sha256(line.encode()).hexdigest()
                original_source[k]=(line,json.loads(line))
    rows=_read_jsonl(V2)
    groups={}
    for r in unseen:
        digest=r['original_prequote_hitter_source_sha256']
        if digest not in original_source:
            raise ValueError('Lost originally published first pregame batting order event source SHA')
        groups.setdefault(digest,[]).append(r)
    joined=[]
    for digest,contexts in groups.items():
        old_v2=[x for x in rows if x.get('original_append_only_line_sha256')==digest]
        verify_original_pregame_source(old_v2,ORIGINAL_PREGAME_LINEUPS)
        _,official=original_source[digest]
        original_quotes,_=select_paired_market_sources(
            official,old_v2,fusion,raw,now=obs,
            source_file_sha256=sha_file(target),
            fusion_file_sha256=sha_file(FUSION),
        )
        keys={(int(x['game_pk']),int(x['player_id'])) for x in contexts}
        eligible=[x for x in original_quotes if (int(x['official_game_pk']),int(x['mlbam_player_id'])) in keys]
        model=json.loads(MODEL.read_text())
        proposed,_=eligible_same_quote_full_context_shadow(
            contexts,eligible,model,now=obs,
            original_model_sha256=sha_file(MODEL),
            source_fusion_sha256=sha_file(FUSION),
            source_market_snapshot_sha256=sha_file(target),
        )
        joined.extend(proposed)
    added=append_first_full_context_prediction(OUT,joined)
    saved=_read_jsonl(OUT)
    return {
        'status':'FROZEN_SOURCE_TIME_16TERM_TEAM_PARK_SPEED_WALKS_NEXT_QUOTE_RESEARCH_ONLY',
        'captured_at_utc':_utc(obs).isoformat(),
        'original_quote_source_path':str(target.relative_to(ROOT)),
        'original_quote_source_sha256':sha_file(target),
        'frozen_historical_model_sha256':sha_file(MODEL),
        'new_full_context_forecasts':added,
        'total_first_frozen_context_forecasts':len(saved),
        'independent_game_blocks':len({x['official_game_pk'] for x in saved}),
        'eligible_from_latest_paired_sportsbook_snapshot':len(joined),
        'unseen_official_player_with_prequote_context':len(unseen),
        'observed_original_context_frozen_after_the_first_earlier_market_price':True,
        'new_qualified_quote_must_be_after_full_context_source_capture':True,
        'first_market_only_and_restricted_eight_feature_frozen_predictions_repriced':False,
        'research_only_no_wager':True,
        'verified_model_over_book_profitability':False,
    }


def main():
    ap=argparse.ArgumentParser(description='Freeze historical 16-col team/park/speed model on a new later paired sportsbook quote')
    ap.add_argument('--stage',choices=['freeze_latest_pregame_quote'],required=True)
    args=ap.parse_args()
    result=freeze_cycle()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    tmp=SUMMARY.with_suffix('.tmp')
    tmp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    os.replace(tmp,SUMMARY)
    print('MLB_TRUE_FORWARD_COMPLETE_16_FEATURE_SHADOW',json.dumps(result,sort_keys=True))


if __name__=='__main__':
    main()
