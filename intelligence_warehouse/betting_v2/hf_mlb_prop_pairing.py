"""Research-only exact-snapshot paired prop odds: never mix books or timestamps."""
from __future__ import annotations
from .hf_mlb_prop_pilot import _utc_timestamp, clean_player_name, market_implied_probability, safe_number


def evaluate_exact_quote_pair(verified_source: dict, offers: list[dict]) -> dict:
    """Return de-vigged fair probability only with a complete trustworthy pair.

    The input source must have already passed official player, game, and grade
    matching. Odds must be for exact same event/player/market/line/book/minute.
    """
    status = lambda value: {'status': value}
    if verified_source.get('status') not in ('VERIFIED_HISTORICAL','OFFICIAL_DERIVED_HISTORICAL'):
        return status('SOURCE_NOT_VERIFIED')
    source_ts = _utc_timestamp(verified_source.get('ts'))
    official_start = _utc_timestamp(verified_source.get('official_start'))
    if source_ts is None or official_start is None or source_ts >= official_start:
        return status('QUOTE_NOT_PREGAME')
    side = str(verified_source.get('side') or '').lower()
    if side not in ('over','under'):
        return status('INVALID_SELECTION')
    original_prob = market_implied_probability(verified_source.get('odds'))
    line = safe_number(verified_source.get('line'))
    if original_prob is None or line is None:
        return status('INVALID_ORIGINAL_ODDS_OR_LINE')
    matched = []
    for entry in offers:
        if entry.get('game_id') != verified_source.get('game_id'):
            continue
        if clean_player_name(entry.get('player')) != clean_player_name(verified_source.get('player')):
            continue
        if str(entry.get('market') or '').lower() != str(verified_source.get('market') or '').lower():
            continue
        if safe_number(entry.get('line')) != line:
            continue
        if str(entry.get('book') or '').lower() != str(verified_source.get('book') or '').lower():
            continue
        if _utc_timestamp(entry.get('ts')) != source_ts:
            continue
        entry_side = str(entry.get('side') or '').lower()
        if entry_side in ('over','under'):
            matched.append((entry_side,safe_number(entry.get('odds'))))
    by_side = {name:{x for s,x in matched if s==name} for name in ('over','under')}
    if not by_side['over'] or not by_side['under']:
        return status('NO_EXACT_OPPOSITE_SIDE')
    if any(len(values)!=1 for values in by_side.values()):
        return status('CONFLICTING_SAME_SIDE_PRICE')
    odds = {name:next(iter(values)) for name,values in by_side.items()}
    if any(market_implied_probability(value) is None for value in odds.values()):
        return status('INVALID_PAIRED_ODDS')
    if abs(odds[side]-float(verified_source['odds'])) > 1e-6:
        return status('ORIGINAL_PRICE_NOT_REPRODUCED')
    raw={k:market_implied_probability(odds[k]) for k in odds}
    hold=raw['over']+raw['under']-1.0
    if not 0<=hold<=0.25:
        return status('UNREASONABLE_BOOKMAKER_OVERROUND')
    fair=raw[side]/(raw['over']+raw['under'])
    opposite='under' if side=='over' else 'over'
    return {'status':'VERIFIED_SAME_BOOK_TIME_PAIR',
            'source_provider_game_id':verified_source.get('game_id'),
            'official_game_pk':verified_source.get('official_game_pk'),
            'book':verified_source.get('book'),
            'quoted_at':source_ts.isoformat(),
            'market':verified_source.get('market'),
            'side':side,'line':line,
            'side_decimal_odds':odds[side],
            'opposite_decimal_odds':odds[opposite],
            'raw_implied_probability':round(raw[side],8),
            'fair_probability':round(fair,8),
            'overround':round(hold,8),
            'research_only':True}
