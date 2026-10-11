#!/usr/bin/env python3
"""Read-only opposing-team cost scan. No orders, fills, or guaranteed profit."""
import hashlib
import itertools
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from audit_nfl_fee_sensitivity import kalshi_fee
from validate_prediction_contracts import number, poly_fee

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'nfl_live/prediction_markets'

def stamp(value):
    result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if result.utcoffset() is None:
        raise ValueError('Timezone required')
    return result

def evaluate(a, b, fee_a, fee_b, now, quantity=100, rules_equivalent=False):
    q = number(quantity)
    if q <= 0:
        raise ValueError('Positive quantity required')
    blockers = []
    if a['event_id'] != b['event_id'] or a['team'] == b['team'] or a['provider'] == b['provider']:
        raise ValueError('Distinct opposing cross-provider outcomes required')
    prices = [number(r['observed_ask']) for r in (a, b)]
    if any(not 0 < p < 1 for p in prices):
        raise ValueError('Invalid ask')
    for r in (a, b):
        try:
            age = (now - stamp(r['book_captured_at_utc'])).total_seconds()
            if not 0 <= age <= 900:
                blockers.append('STALE_OR_FUTURE_QUOTE')
            if now >= stamp(r['kickoff_utc']):
                blockers.append('GAME_STARTED')
            if number(r['observed_ask_depth']) < q:
                blockers.append('INSUFFICIENT_TOP_LEVEL_DEPTH')
        except (KeyError, ValueError, TypeError):
            blockers.append('INVALID_QUOTE_EVIDENCE')
    try:
        if stamp(a['kickoff_utc']) != stamp(b['kickoff_utc']):
            blockers.append('KICKOFF_MISMATCH')
        if abs((stamp(a['book_captured_at_utc']) - stamp(b['book_captured_at_utc'])).total_seconds()) > 30:
            blockers.append('QUOTE_TIME_SKEW')
    except (KeyError, ValueError, TypeError):
        blockers.append('INVALID_QUOTE_EVIDENCE')
    if not rules_equivalent:
        blockers.append('SETTLEMENT_RULES_NOT_EQUIVALENT')
    gross_cost = q * sum(prices)
    net_cost = stress_cost = None
    try:
        fees = fee_a(q, prices[0]) + fee_b(q, prices[1])
        net_cost = gross_cost + fees
        stressed = [p + Decimal('.01') for p in prices]
        if all(p < 1 for p in stressed):
            stress_cost = q * sum(stressed) + fee_a(q, stressed[0]) + fee_b(q, stressed[1])
    except (ValueError, TypeError, KeyError):
        blockers.append('FEE_EVIDENCE_UNAVAILABLE')
    # $1 total payout is conditional on compatible completion, NOT all resolution scenarios.
    if net_cost is not None and net_cost >= q:
        blockers.append('NO_POSITIVE_NET_GAP')
    return dict(event_id=a['event_id'], teams=[a['team'], b['team']],
                legs=[dict(provider=r['provider'], team=r['team'],
                           contract_or_token_id=r['contract_or_token_id'],
                           ask=r['observed_ask'], top_level_depth=r['observed_ask_depth'],
                           captured_at_utc=r['book_captured_at_utc']) for r in (a, b)],
                quantity=float(q), conditional_completion_payout=float(q),
                gross_cost=float(gross_cost), documented_fee_cost=None if net_cost is None else float(net_cost-gross_cost),
                conditional_net_profit=None if net_cost is None else float(q-net_cost),
                conditional_net_roi=None if net_cost is None else float((q-net_cost)/net_cost),
                one_cent_worse_fill_profit=None if stress_cost is None else float(q-stress_cost),
                blockers=sorted(set(blockers)), decision='BLOCKED' if blockers else 'CONDITIONAL_GAP_REQUIRES_FILL_VERIFICATION',
                approved_pick=False, execution_enabled=False)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    now = datetime.now(timezone.utc)
    quote_path = DATA / 'nfl_narrow_forward_quotes_latest.json'
    execution_path = DATA / 'execution_evidence_latest.json'
    validation_path = DATA / 'contract_validation_latest.json'
    contracts_path = DATA / 'polymarket_nfl_contract_audit_latest.json'
    observations = json.loads(quote_path.read_text())
    execution = json.loads(execution_path.read_text())
    validation = json.loads(validation_path.read_text())
    if observations['source_hashes']['execution'] != sha(execution_path):
        raise ValueError('Quotes do not match execution evidence; recapture quotes')
    schedules = {r['id']:r['fee_schedule'] for r in validation['polymarket']
                 if r['identity_checked'] and r['terms_reviewed'] and r['documented_fee_calculation_checked']}
    token_schedules = {t:schedules[c['id']] for c in json.loads(contracts_path.read_text())['contracts']
                       if c['id'] in schedules for t in c['token_ids']}
    books = {r['ticker']:r for r in execution['kalshi']}
    def fee_function(r):
        if r['provider'] == 'POLYMARKET':
            schedule = token_schedules.get(r['contract_or_token_id'])
            return lambda q,p: poly_fee(q,p,schedule or {})
        metadata = books.get(r['contract_or_token_id'],{}).get('fees',{})
        def calculate(q,p):
            if not metadata.get('metadata_complete') or metadata.get('series_fee_type') != 'quadratic_with_maker_fees':
                raise ValueError('Unsupported Kalshi fee evidence')
            return kalshi_fee(q,p,metadata['series_fee_multiplier'])
        return calculate
    rows = []
    for a,b in itertools.combinations(observations['rows'],2):
        if a['event_id'] == b['event_id'] and a['team'] != b['team'] and a['provider'] != b['provider']:
            rows.append(evaluate(a,b,fee_function(a),fee_function(b),now))
    counts = Counter(code for r in rows for code in r['blockers'])
    out = dict(schema='zenith.nfl.cross_market_scan.v1', scanned_at_utc=now.isoformat(),
               source_snapshot_created_at_utc=observations['captured_at_utc'],
               source_quotes_captured_at_utc=min((leg['captured_at_utc'] for row in rows for leg in row['legs']), default=None),
               source_hashes=dict(quotes=sha(quote_path),execution=sha(execution_path),
                                  validation=sha(validation_path),contracts=sha(contracts_path)),
               paired_games=len({r['event_id'] for r in rows}), pairs_checked=len(rows),
               raw_positive_pairs=sum(r['gross_cost']<r['quantity'] for r in rows),
               positive_after_documented_fees=sum(r['conditional_net_profit'] is not None and r['conditional_net_profit']>0 for r in rows),
               unblocked_pairs=sum(not r['blockers'] for r in rows), blocker_counts=dict(counts),rows=rows,
               actual_trades=0,approved_picks=0,execution_enabled=False,
               limitations=['Only saved matched NFL winner asks; no sharp sportsbook benchmark',
                            'Cross-provider postponement and cancellation payoffs are not equivalent',
                            'Top-level 100-contract hypothetical single fills; simultaneous fills unverified',
                            'No funding costs, actual execution fees, realized ROI, or historical fills validated'])
    target=DATA/'nfl_cross_market_scan_latest.json'
    target.write_text(json.dumps(out,indent=2)+'\n')
    archive=DATA/('nfl_cross_market_scan_'+now.strftime('%Y%m%dT%H%M%SZ')+'.json')
    archive.write_text(target.read_text())
    public_path=ROOT/'commercial_web/public/prediction_market_nfl_evidence.json'
    public=json.loads(public_path.read_text())
    public['cross_market_scan']=out
    public_path.write_text(json.dumps(public,indent=2)+'\n')
    print(json.dumps({k:out[k] for k in ('paired_games','pairs_checked','raw_positive_pairs','positive_after_documented_fees','unblocked_pairs','blocker_counts')}))
if __name__ == '__main__':
    main()
