"""Publish source-verifiable frozen NFL model vs sportsbook research. No betting promotions.

This is a *read-only projection* of original future-frozen 9-feature research,
NOT a model retrain, sportsbook execution price, spread selection, or endorsed
bet. Crosswalk against independent ESPN event IDs and exact pregame kickoff.
Only sanitized non-secret facts are ever copied to the public site.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
import os
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'intelligence_warehouse/nfl_advanced_pregame/NFL_FIRST_PREKICKOFF_NINE_FEATURE_SCORE_FORM_SHADOW.jsonl'
SCHEDULE = ROOT / 'commercial_web/public/nfl_scores.json'
PUBLIC = ROOT / 'commercial_web/public/nfl_frozen_game_intelligence.json'
DIST = ROOT / 'commercial_web/dist/nfl_frozen_game_intelligence.json'
EXPECTED_MODEL = 'NFL_PREQUOTE_SCORE_FORM_9COL_2016_2024_RIDGE20_RESEARCH_V1'
EXPECTED_SCHEMA = 'NFL_2026_FIRST_RESEARCH_NINE_FEATURE_SAME_NEW_QUOTE_MARKET_COMPARISON_V1'
ALIAS = {'JAC':'JAX','WSH':'WAS','LA':'LAR'}
OFFICIAL_MAX_TIP_DELTA_SECONDS = 180


def dt(value):
    if not isinstance(value,str) or not value.strip():
        raise ValueError('No verified source date')
    x = datetime.fromisoformat(value.replace('Z','+00:00'))
    if x.tzinfo is None:
        raise ValueError('Need timezone-aware true source date')
    return x.astimezone(timezone.utc)


def sha(source:Path) -> str:
    return hashlib.sha256(source.read_bytes()).hexdigest()


def fraction(value):
    x = float(value)
    if not math.isfinite(x) or not 0.0 < x < 1.0:
        raise ValueError('Bad source-model probability')
    return x


def valid_price(value):
    if isinstance(value,bool) or value is None: raise ValueError('Missing price')
    x = float(value)
    if not math.isfinite(x) or not x.is_integer() or abs(x) < 100 or abs(x) > 10000:
        raise ValueError('Invalid bookmaker-source American price')
    return int(x)


def american_prob(price:int) -> float:
    return 100.0/(100+price) if price>0 else abs(price)/(abs(price)+100.0)


def score_model_source_row(raw:dict, fixture:dict) -> dict:
    if raw.get('schema')!=EXPECTED_SCHEMA or raw.get('model_version')!=EXPECTED_MODEL:
        raise ValueError('Unapproved source-model version')
    if raw.get('source_book_name')!='pinnacle' or raw.get('source_provider')!='sportwizzard':
        raise ValueError('Bookmaker source not original frozen quote')
    for guard in ('research_only','source_outcome_still_unknown_before_first_kickoff',
                  'historic_2025_diagnostic_slightly_worse_than_raw_market',
                  'original_source_bookmaker_price_not_a_verified_executable_offer'):
        if raw.get(guard) is not True:raise ValueError('Original caution flag absent: '+guard)
    for guard in ('betting_play_approved','sportsbook_wager_created','predicted_market_advantage_proven',
                  'same_game_result_used_for_features','verified_current_quarterback_starter_or_inactive_status_claimed'):
        if raw.get(guard) is not False:raise ValueError('Original non-play guard missing: '+guard)
    if str(raw.get('official_espn_event_id'))!=str(fixture.get('event_id')):
        raise ValueError('Official ESPN event identity does not match')
    away=ALIAS.get(str(fixture.get('away_abbr')),str(fixture.get('away_abbr')))
    home=ALIAS.get(str(fixture.get('home_abbr')),str(fixture.get('home_abbr')))
    if (away,home)!=(raw.get('away_team'),raw.get('home_team')):
        raise ValueError('Official ESPN team identity mismatch')
    kickoff=dt(fixture['start_time'])
    frozen_kickoff=dt(raw['official_first_pitch_utc'])
    if abs((kickoff-frozen_kickoff).total_seconds())>OFFICIAL_MAX_TIP_DELTA_SECONDS:
        raise ValueError('NFL official kickoff mismatch')
    source_form=dt(raw['source_context_features_frozen_at_utc'])
    quote_updated=dt(raw['source_qualified_book_quote_updated_at_utc'])
    source_frozen=dt(raw['source_first_real_future_prediction_frozen_at_utc'])
    if not source_form<=quote_updated<=source_frozen<kickoff:
        raise ValueError('Model/quote time violates frozen pregame order')
    model=fraction(raw['nine_feature_score_form_home_win_prob'])
    fair=fraction(raw['original_raw_book_home_fair'])
    marketonly=fraction(raw['market_only_calibrated_home_win_prob'])
    home_price=valid_price(raw['original_same_book_american_home_moneyline'])
    away_price=valid_price(raw['original_same_book_american_away_moneyline'])
    rawhome=american_prob(home_price)
    rawaway=american_prob(away_price)
    if abs(rawhome/(rawhome+rawaway)-fair)>0.007:
        raise ValueError('Source book moneyline does not de-vig to original fair reference')
    names=raw.get('model_feature_names') or []
    vect=raw.get('model_feature_vector') or []
    if len(names)!=9 or len(vect)!=9 or len(set(names))!=9:
        raise ValueError('Original independent pregame nine-feature model changed')
    if not all(math.isfinite(float(z)) for z in vect):
        raise ValueError('Nonfinite frozen NFL feature data')
    if int(raw.get('model_training_independent_games',0))<1000:
        raise ValueError('Model training original source unexpectedly missing')
    model_delta_pp=round(100*(model-fair),2)
    favorite='HOME' if model>=.5 else 'AWAY'
    return {
       'event_id':str(fixture['event_id']),
       'game_key':raw['source_schedule_game_id'],
       'away':away, 'home':home,
       'kickoff_utc':kickoff.isoformat(),
       'book_name':'Pinnacle',
       'quote_received_from':'SportWizzard original as-of provider quote',
       'book_quote_last_updated_at_utc':quote_updated.isoformat(),
       'forecast_frozen_at_utc':source_frozen.isoformat(),
       'forecast_side_home_or_away':favorite,
       'forecast_side_team':home if favorite=='HOME' else away,
       'forecast_home_pct':round(100*model,2),
       'forecast_away_pct':round(100*(1-model),2),
       'book_market_fair_home_pct':round(100*fair,2),
       'book_market_fair_away_pct':round(100*(1-fair),2),
       'market_only_calibrated_home_pct':round(100*marketonly,2),
       'delta_model_minus_book_home_pp':model_delta_pp,
       'original_home_american_price':home_price,
       'original_away_american_price':away_price,
       'actual_sportsbook_executable_current_price_verified':False,
       'score_form_model_training_independent_games_not_forward_proof':int(raw['model_training_independent_games']),
       'model_uses_market_input':True,
       'features_type':'frozen_market_plus_prior_2026_scoring_form_rest_and_neutral_venue',
       'source_sample_actual_home_away_previous_three_game_margin_diff_scaled14':round(float(vect[2]),3),
       'source_sample_opp_defense_scoring_matchup_scaled20':round(float(vect[3]),3),
       'score_form_model_historical_2025_worse_than_market_baseline':True,
       'model_beats_market_out_of_sample_proven':False,
       'approved_play':False,
       'market_status':'FROZEN_RESEARCH_SNAPSHOT_PROVIDER_PRICE_MAY_HAVE_MOVED',
       'score_or_game_result_included':False,
       'source_model_version':raw['model_version'],
    }


def project(source:Path=SOURCE, schedule:Path=SCHEDULE, *, now:datetime|None=None) -> dict:
    moment=now or datetime.now(timezone.utc)
    if moment.tzinfo is None:raise ValueError('Local clock not timezone-aware')
    raw=[json.loads(line) for line in source.read_text().splitlines() if line.strip()]
    fixtures=json.loads(schedule.read_text())
    official=(fixtures.get('games') or [])+(fixtures.get('next_games') or [])
    ids={}
    for fixture in official:
        game_id=str(fixture.get('event_id') or '')
        if not game_id: continue
        if game_id in ids:
            if fixture!=ids[game_id]:raise ValueError('Contradictory official game identity')
            continue
        ids[game_id]=fixture
    output=[]
    seen=set()
    for r in raw:
        identity=str(r.get('official_espn_event_id') or '')
        if not identity or identity in seen:raise ValueError('Duplicate missing or conflicting source prediction')
        seen.add(identity)
        fixture=ids.get(identity)
        if not fixture:raise ValueError('Frozen NFL forecast missing official source fixture '+identity)
        row=score_model_source_row(r,fixture)
        # The original record stays frozen for the permanent audit even after
        # the game; we simply do not present old matchups as upcoming.
        if dt(row['kickoff_utc'])<=moment:continue
        row['original_quoted_price_age_hours_at_publication']=round(
          (moment-dt(row['book_quote_last_updated_at_utc'])).total_seconds()/3600,2)
        row['original_book_price_under_24_hour_recency_limit_at_publication']=(0<=
          row['original_quoted_price_age_hours_at_publication']<=24)
        output.append(row)
    output.sort(key=lambda r:(r['kickoff_utc'],r['event_id']))
    return {
      'schema':'ZENITH_READONLY_NFL_NINE_FEATURE_FROZEN_GAME_INTELLIGENCE_V1',
      'generated_at':moment.astimezone(timezone.utc).isoformat(),
      'data_kind':'FROZEN_PRIOR_QUOTE_PREGAME_PAPER_MODEL_V_BOOK_RESEARCH',
      'source_original_nine_feature_ledger_sha256':sha(source),
      'source_original_NFL_ESPN_fixture_snapshot_sha256':sha(schedule),
      'current_original_future_games':len(output),
      'model_training_proof_is_not_unseen_forward_edge':True,
      'historic_2025_holdout_model_better_than_market':False,
      'wagers_created_or_bets_promoted':False,
      'real_book_executability_verified':False,
      'odds_and_game_status_recheck_required':True,
      'market_source_cannot_upgrade_stale_primary_NFL_live_best_bets':True,
      'rows':output,
    }


def write_atomic(path:Path,data:dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    blob=(json.dumps(data,sort_keys=True,indent=2)+'\n').encode()
    with NamedTemporaryFile(mode='wb',dir=path.parent,prefix='.nfl_intelligence_',delete=False) as f:
        tmp=Path(f.name)
        f.write(blob);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
    if path.read_bytes()!=blob:raise RuntimeError('Projected payload did not verify after publish')


def main():
    expected_ledger=sha(SOURCE)
    expected_scoreboard=sha(SCHEDULE)
    data=project()
    if sha(SOURCE)!=expected_ledger or sha(SCHEDULE)!=expected_scoreboard:
        raise ValueError('Source moved while creating projection; restart with new immutable inputs')
    assert data['source_original_nine_feature_ledger_sha256']==expected_ledger
    assert data['source_original_NFL_ESPN_fixture_snapshot_sha256']==expected_scoreboard
    for p in (PUBLIC,DIST):write_atomic(p,data)
    print('NFL_SOURCE_VERIFIED_FORECASTS',len(data['rows']),'WRITTEN_TO_PUBLIC_AND_DIST')
    print('SOURCE_HASH',data['source_original_nine_feature_ledger_sha256'])
    print('APPROVED_BETS_OR_INDEPENDENT_EDGES',data['wagers_created_or_bets_promoted'])
    print('ALL_RESULTS_CURRENT_SOURCE_QUOTES_NOT_VERIFIED_EXECUTABLE',data['real_book_executability_verified'])


if __name__=='__main__':main()
