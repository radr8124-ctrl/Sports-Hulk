"""Model-independent exact NFL contract/order-book matching; read-only."""
from collections import Counter
from capture_nfl_narrow_forward_quotes import best_ask, canonical
from audit_polymarket_nfl_contracts import instant

def collect_scan_quotes(execution, kalshi, poly, validation, games, aliases, now):
    schedule={};conflicts=set();rejected=Counter();rows=[]
    for game in games:
        if game.get('sport','NFL')!='NFL':continue
        try:
            identity=str(game['event_id'])
            record=(instant(game['start_time']),frozenset(canonical(game[k]) for k in ('home_abbr','away_abbr')))
            if len(record[1])!=2:raise ValueError('Not two teams')
            if identity in schedule and schedule[identity]!=record:conflicts.add(identity)
            schedule[identity]=record
        except (KeyError,ValueError,TypeError):
            rejected['INVALID_SCHEDULE']+=1
    for identity in conflicts:schedule.pop(identity,None)
    name_map={name:canonical(team) for team,names in aliases.items() for name in names}
    kvalidation={r['id']:r for r in validation['kalshi']}
    pvalidation={r['id']:r for r in validation['polymarket']}
    books={r['ticker']:r for r in execution['kalshi']}
    probes={}
    for probe in execution['polymarket_probes']:
        if probe.get('status')!='CAPTURED':continue
        token=probe.get('data',{}).get('asset_id')
        if token and probe.get('source_url')=='https://clob.polymarket.com/book?token_id='+token:
            probes[token]=probe
    for provider,contracts in [('KALSHI',kalshi),('POLYMARKET',poly)]:
        for c in contracts:
            identity=str(c['espn_event_id'])
            if identity not in schedule:
                rejected['SCHEDULE_MISSING_OR_CONFLICTING']+=1;continue
            kickoff,teams=schedule[identity]
            if kickoff<=now:
                rejected['GAME_STARTED']+=1;continue
            check=(kvalidation if provider=='KALSHI' else pvalidation).get(c['ticker'] if provider=='KALSHI' else c['id'],{})
            if check.get('terms_reviewed') is not True or check.get('live_open') is not True:
                rejected['CONTRACT_CLOSED_OR_UNREVIEWED']+=1;continue
            try:
                if provider=='KALSHI':
                    team=canonical(c['yes_team_abbr'])
                    if team not in teams:raise ValueError('Outcome mismatch')
                    book=books.get(c['ticker'],{})
                    if book.get('book_status')!='CAPTURED' or not book.get('book',{}).get('usable_observed_spread'):
                        rejected['BOOK_UNAVAILABLE_OR_CROSSED']+=1;continue
                    outcomes=[(c['ticker'],team,book['captured_at_utc'],book['book']['yes_ask'],book['book']['ask_contracts'])]
                else:
                    if check.get('identity_checked') is not True or instant(c['kickoff'])!=kickoff:
                        raise ValueError('Identity or kickoff mismatch')
                    tokens=c['token_ids'];outcome_teams=[name_map[name] for name in c['outcome_teams']]
                    if len(tokens)!=2 or len(set(tokens))!=2 or len(outcome_teams)!=2 or set(outcome_teams)!=set(teams):
                        raise ValueError('Outcome mapping mismatch')
                    outcomes=[]
                    for token,team in zip(tokens,outcome_teams):
                        probe=probes.get(token)
                        if not probe:
                            rejected['TOKEN_BOOK_IDENTITY_UNAVAILABLE']+=1;continue
                        ask,depth=best_ask(probe['data'])
                        outcomes.append((token,team,probe['captured_at_utc'],ask,depth))
                for token,team,capture,ask,depth in outcomes:
                    age=(now-instant(capture)).total_seconds()
                    if not 0<=age<=900:
                        rejected['STALE_OR_FUTURE_QUOTE']+=1;continue
                    if ask is None or depth is None or not 0<ask<1 or depth<=0:
                        rejected['ASK_DEPTH_UNAVAILABLE']+=1;continue
                    rows.append(dict(provider=provider,contract_or_token_id=token,event_id=identity,
                        team=team,kickoff_utc=kickoff.isoformat(),book_captured_at_utc=capture,
                        observed_ask=ask,observed_ask_depth=depth,rules_sha256=c['rules_sha256'],
                        approved_pick=False,fill_guaranteed=False))
            except (KeyError,ValueError,TypeError):
                rejected['CONTRACT_IDENTITY_OR_BOOK_INVALID']+=1
    return dict(rows=rows,rejected=dict(rejected),model_forecasts_required=False,
                scheduled_future_games=sum(kickoff>now for kickoff,teams in schedule.values()))
