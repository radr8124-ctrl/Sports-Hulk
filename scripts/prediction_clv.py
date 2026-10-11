"""Same-contract acquisition-price CLV; a diagnostic, never proof of ROI.

Closing benchmark: observed executable-side ask within 15 minutes before
scheduled kickoff. No prices from after kickoff or a different contract.
Fees are total dollars for the same quantity, not a flat probability buffer.
"""
import re
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from audit_prediction_roi import number

def stamp(value):
    result=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if result.utcoffset() is None:raise ValueError('Timezone required')
    return result

def summarize_clv(trades, mode='PAPER', now=None):
    if mode not in ('PAPER','ACTUAL'):raise ValueError('Unknown mode')
    now=now or datetime.now(timezone.utc)
    seen=set();values=[];cost_values=[];excluded=Counter()
    for r in trades:
        if r.get('mode')!=mode:raise ValueError('Cannot mix paper and actual CLV')
        identity=r.get('trade_id')
        if not identity or identity in seen:raise ValueError('Missing or duplicate trade identity')
        seen.add(identity)
        close=r.get('closing_quote')
        if not close:
            excluded['CLOSING_QUOTE_MISSING']+=1;continue
        try:
            q,p,cp=map(number,(r['quantity'],r['fill_price'],close['ask']))
            entry_at,close_at,kickoff=map(stamp,(r['entry_at_utc'],close['captured_at_utc'],r['kickoff_utc']))
            if not(q>0 and 0<p<1 and 0<cp<1):raise ValueError('Invalid quantity or price')
            if not entry_at<=close_at<kickoff or close_at>now or (kickoff-close_at).total_seconds()>900:
                excluded['CLOSING_TIME_INVALID']+=1;continue
            if not r.get('contract_or_token_id') or not r.get('provider') or close.get('contract_or_token_id')!=r['contract_or_token_id'] or close.get('provider')!=r['provider']:
                excluded['CONTRACT_MISMATCH']+=1;continue
            if close.get('source_verified') is not True or not re.fullmatch('[0-9a-f]{64}',close.get('source_sha256','')):
                excluded['CLOSING_SOURCE_UNVERIFIED']+=1;continue
            if number(close['ask_depth'])<q:
                excluded['INSUFFICIENT_CLOSING_DEPTH']+=1;continue
        except (KeyError,ValueError,TypeError,ArithmeticError):
            excluded['INVALID_EVIDENCE']+=1;continue
        raw=cp-p
        values.append((q,raw))
        try:
            entry_fee,close_fee=number(r['entry_fee']),number(close['fee_for_quantity'])
            if r.get('fees_verified') is not True or close.get('fees_verified') is not True or min(entry_fee,close_fee)<0:
                raise ValueError('Unverified fees')
            cost_values.append((q,cp+close_fee/q-p-entry_fee/q))
        except (KeyError,ValueError,TypeError,ArithmeticError):
            excluded['COST_CLV_UNAVAILABLE']+=1
    def average(items):
        return None if not items else float(sum((q*v for q,v in items),Decimal(0))/sum((q for q,v in items),Decimal(0)))
    return dict(mode=mode,benchmark='SAME_CONTRACT_PREKICKOFF_ASK_WITHIN_15_MINUTES',
                compared_entries=len(values),cost_compared_entries=len(cost_values),
                quantity_weighted_raw_clv=average(values),quantity_weighted_cost_clv=average(cost_values),
                positive_entry_fraction=None if not values else sum(v>0 for q,v in values)/len(values),
                exclusion_counts=dict(excluded),validated_profitable_edge=False,
                interpretation='Positive CLV means a lower acquisition price than this closing ask benchmark; it does not establish realized profit or guarantee an edge.')
