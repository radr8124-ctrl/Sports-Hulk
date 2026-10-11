#!/usr/bin/env python3
"""Read-only exact NFL contract discovery. Never approves an edge or order."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import urllib.request
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parents[1]
ALIASES = {'JAC':'jax', 'WSH':'was', 'LA':'lar'}
def instant(value):
    value = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if value.tzinfo is None: raise ValueError('Timezone required')
    return value.astimezone(dt.timezone.utc)
def array(value):
    return json.loads(value) if isinstance(value, str) else value
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'SportsZenithResearch/1.0'}), timeout=20) as response:
        return json.load(response)
def audit(events, games):
    index = {}
    for game in games:
        if game.get('sport', 'NFL') != 'NFL': continue
        try:
            day = instant(game['start_time']).astimezone(ZoneInfo('America/New_York')).date().isoformat()
            away, home = [ALIASES.get(game[k].upper(), game[k].lower()) for k in ('away_abbr','home_abbr')]
            index.setdefault(f'nfl-{away}-{home}-{day}', {})[str(game['event_id'])] = game
        except (KeyError, ValueError): continue
    rows, rejected, seen = [], [], set()
    for event in events:
        for market in event.get('markets', []):
            mid = str(market.get('id', ''))
            if mid in seen: continue
            seen.add(mid)
            reason = None
            candidates = list(index.get(event.get('slug'), {}).values())
            try:
                if len(candidates) != 1: raise ValueError('NO_UNIQUE_EXACT_SCHEDULE_MATCH')
                game = candidates[0]
                if market.get('sportsMarketType') != 'moneyline': raise ValueError('NOT_MONEYLINE')
                if market.get('active') is not True or market.get('closed') is not False: raise ValueError('NOT_OPEN')
                if instant(market['gameStartTime']) != instant(game['start_time']): raise ValueError('KICKOFF_MISMATCH')
                outcomes, tokens = array(market.get('outcomes')), array(market.get('clobTokenIds'))
                if not isinstance(outcomes,list) or not isinstance(tokens,list) or len(outcomes)!=2 or len(set(outcomes))!=2 or len(tokens)!=2 or len(set(tokens))!=2: raise ValueError('INVALID_OUTCOMES_OR_TOKENS')
                teams = []
                for outcome in outcomes:
                    matches = [game[k] for k in ('away','home') if re.search(r'(?:^|\s)'+re.escape(outcome)+r'$', game[k], re.I)]
                    if len(matches)!=1: raise ValueError('UNKNOWN_OUTCOME_TEAM')
                    teams.append(matches[0])
                if len(set(teams))!=2: raise ValueError('DUPLICATE_OUTCOME_TEAM')
                rules = market.get('description') or ''
                if not rules: raise ValueError('SETTLEMENT_TERMS_MISSING')
                rows.append(dict(provider='POLYMARKET', id=mid, espn_event_id=str(game['event_id']), event=f"{game['away']} vs {game['home']}", question=market.get('question') or event.get('title'), kickoff=game['start_time'], outcomes=outcomes, outcome_teams=teams, token_ids=tokens, display_prices=array(market.get('outcomePrices') or '[]'), rules=rules, rules_sha256=hashlib.sha256(rules.encode()).hexdigest(), resolution_source=market.get('resolutionSource'), fee_metadata=market.get('feeSchedule'), fees_enabled=market.get('feesEnabled'), approved_pick=False, independent_probability=None, price_basis='Captured indicative outcome prices'))
            except (KeyError, ValueError, TypeError) as exc: reason = str(exc)
            if reason: rejected.append(dict(id=mid,reason=reason))
    return rows, rejected

def save(path, data):
    tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(data,indent=2)+'\n'); tmp.replace(path)
def main():
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    sports = fetch('https://gamma-api.polymarket.com/sports')
    nfl = next(s for s in sports if s.get('sport') == 'nfl')
    events, urls = [], []
    complete = False
    for offset in range(0,500,100):
        url = f"https://gamma-api.polymarket.com/events?limit=100&offset={offset}&active=true&closed=false&series_id={nfl['series']}"
        page = fetch(url); events.extend(page); urls.append(url)
        if len(page)<100: complete=True; break
    schedule_path = ROOT/'commercial_web/public/nfl_scores.json'
    schedule_bytes = schedule_path.read_bytes(); scores = json.loads(schedule_bytes)
    rows, rejected = audit(events, scores.get('games',[])+scores.get('next_games',[]))
    output = dict(schema='zenith.polymarket.nfl.contract_audit.v1',captured_at_utc=now,source_urls=urls,pagination_complete=complete,events_seen=len(events),contracts_captured=len(rows),matched_games=len(set(r['espn_event_id'] for r in rows)),schedule_sha256=hashlib.sha256(schedule_bytes).hexdigest(),raw_source_sha256=hashlib.sha256(json.dumps(events,sort_keys=True).encode()).hexdigest(),approved_picks=0,contracts=rows,rejections=rejected)
    dest = ROOT/'nfl_live/prediction_markets'
    save(dest/'polymarket_nfl_contract_audit_latest.json',output)
    save(dest/('polymarket_nfl_contract_audit_'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json'),output)
    kalshi=json.loads((dest/'kalshi_nfl_contract_audit_latest.json').read_text())
    names = {str(g['event_id']): f"{g['away']} vs {g['home']}" for g in scores.get('games',[])+scores.get('next_games',[])}
    krows=[dict(provider='KALSHI',id=r['ticker'],event=names.get(str(r['espn_event_id']),r['event_ticker']),question=r['title'],yes_bid=r.get('yes_bid_dollars'),yes_ask=r.get('yes_ask_dollars'),price_basis='Captured indicative dollar quotes') for r in kalshi['contracts']]
    public=dict(schema='zenith.nfl.prediction_evidence.v1',generated_at_utc=now,approved_picks=0,providers={'POLYMARKET':dict(captured_at_utc=now,matched_games=output['matched_games'],terms_captured=len(rows),pagination_complete=complete,markets=[{k:r[k] for k in ('provider','id','event','question','outcomes','display_prices','price_basis')} for r in rows]),'KALSHI':dict(captured_at_utc=kalshi['captured_at_utc'],matched_games=len(set(r['espn_event_id'] for r in kalshi['contracts'])),terms_captured=len(krows),markets=krows)})
    save(ROOT/'commercial_web/public/prediction_market_nfl_evidence.json',public)
    print(json.dumps({k:output[k] for k in ('events_seen','matched_games','contracts_captured','pagination_complete','approved_picks')}))
if __name__ == '__main__': main()
