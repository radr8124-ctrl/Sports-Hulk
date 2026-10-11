#!/usr/bin/env python3
"""Audit literal Kalshi NFL rule text, without claiming exchange or trade settlement verification."""
import json,pathlib,re,hashlib,datetime
ROOT=pathlib.Path('/home/ubuntu/sports-hulk/nfl_live/prediction_markets')
IN=ROOT/'kalshi_nfl_contract_audit_latest.json'
OUT=ROOT/'kalshi_nfl_settlement_terms_review_latest.json'
def review(c):
    primary=str(c.get('rules_primary') or '')
    secondary=str(c.get('rules_secondary') or '')
    checks={
      'contract_team_in_event': str(c.get('ticker','')).endswith('-'+str(c.get('yes_team_abbr',''))),
      'yes_wins_condition': bool(re.search(r'^If .+ wins the .+ game originally scheduled for .+, then the market resolves to Yes\.$',primary)),
      'tie_half_dollar': 'If the game ends in a tie, the market will resolve to $0.50 for each team.' in secondary,
      'postponed_within_48h': 'If the game is postponed but begins within 48 hours from its originally scheduled start time' in secondary,
      'not_started_48h_fair_price': 'If the game is not started within 48 hours, the market will resolve to a fair price.' in secondary,
      'official_final_result': 'based on the official final result' in secondary,
      'exact_rules_hash':hashlib.sha256((primary+'\n'+secondary).encode()).hexdigest()==c.get('rules_sha256')
    }
    return {'ticker':c.get('ticker'),'espn_event_id':c.get('espn_event_id'),'rule_checks':checks,
      'literal_rule_check_passed':all(checks.values()),
      'status':'RULE_TEXT_REVIEWED_NOT_FINAL_SETTLEMENT_VERIFIED' if all(checks.values()) else 'RULE_TEXT_REQUIRES_REVIEW',
      'settlement_verified_for_live_trade':False,'approved_pick':False}
def main():
 d=json.loads(IN.read_text())
 rows=[review(c) for c in d['contracts']]
 o={'schema':'zenith.kalshi.nfl.settlement_terms_review.v1','audited_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'input_contract_capture_utc':d['captured_at_utc'],'contracts_checked':len(rows),
 'literal_rules_reviewed':sum(r['literal_rule_check_passed'] for r in rows),
 'contracts_needing_review':sum(not r['literal_rule_check_passed'] for r in rows),
 'exchange_final_settlement_verified':False,'approved_picks':0,
 'notes':['Exact captured rule language is checked; no official final settlement independently validated','Tie pays $0.50 for each side, not a normal binary $1 win or $0 loss','Postponed game fair-price settlement is not modeled as ordinary win/loss','Model and market fee evidence still missing'],'rows':rows}
 OUT.write_text(json.dumps(o,indent=2)+'\n')
 print(json.dumps({k:o[k] for k in ('contracts_checked','literal_rules_reviewed','contracts_needing_review','exchange_final_settlement_verified')}))
if __name__=='__main__':main()
