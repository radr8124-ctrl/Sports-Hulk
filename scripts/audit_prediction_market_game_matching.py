#!/usr/bin/env python3
"""Conservative evidence-only market-to-game matcher; does not approve picks."""
import datetime,json,pathlib,re,collections
ROOT=pathlib.Path('/home/ubuntu/sports-hulk')
def normalize(s):return re.sub(r'[^a-z0-9]+',' ',str(s).lower()).strip()
def source_games():
    games=[]
    for league in ['nfl','nba','nhl','cfb','cbb']:
        file=ROOT/'commercial_web/public'/f'{league}_scores.json'
        doc=json.loads(file.read_text())
        for game in doc.get('games',[]):
            if all(game.get(k) for k in ('home','away','start_time')):
                games.append({'league':league.upper(),'event_id':str(game.get('event_id','')),'home':game['home'],'away':game['away'],'start_time':game['start_time']})
    return games
def audit(markets,games):
    result=collections.Counter();examples=[];matches=[]
    for row in markets:
        text=normalize(str(row.get('event',''))+' '+str(row.get('question','')))
        possibilities=[g for g in games if normalize(g['home']) in text and normalize(g['away']) in text]
        if len(possibilities)==1:
            g=possibilities[0]
            # This remains only a candidate: unknown settlement, contract type and mapping.
            result['TWO_TEAM_TEXT_CANDIDATE_NOT_VERIFIED']+=1
            if len(examples)<8:examples.append({'provider':row.get('provider'),'market':row.get('question'),'game':g})
            matches.append({'provider':row.get('provider'),'market_id':row.get('id'),'game_event_id':g['event_id'],'league':g['league'],'status':'CANDIDATE_REQUIRES_DATE_AND_CONTRACT_VERIFICATION'})
        elif len(possibilities)>1:result['AMBIGUOUS_MATCH']+=1
        else:result['NO_EXACT_TWO_TEAM_MATCH']+=1
    return dict(result),examples,matches
def main():
    snap=json.loads((ROOT/'nfl_live/prediction_markets/latest.json').read_text())
    games=source_games()
    counts,examples,matches=audit(snap['markets'],games)
    output={'schema':'zenith.prediction_market.game_matching_audit.v1','audited_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'snapshot_at_utc':snap['captured_at_utc'],'scoreboard_games_seen':len(games),'markets_seen':len(snap['markets']),'counts':counts,'verified_matches':0,'approved_picks':0,'limitations':['Exact full team names required on both sides','No date/time and specific contract settlement verified','Text candidates are NOT verified game mappings','No prediction probabilities or approved picks'],'examples':examples,'candidate_mappings':matches}
    folder=ROOT/'nfl_live/prediction_markets'
    (folder/'game_matching_audit_latest.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:output[k] for k in ('scoreboard_games_seen','markets_seen','counts','verified_matches')}))
if __name__=='__main__':main()
