#!/usr/bin/env python3
"""Read-only multi-league readiness inventory. Scores do not establish betting edge."""
import json,pathlib,datetime,hashlib
ROOT=pathlib.Path('/home/ubuntu/sports-hulk')
LEAGUES=('NFL','NBA','NHL','MLB','CFB','CBB')
def inspect(league,doc):
    if league=='MLB':
        games=doc.get('today_games',[])+doc.get('recent_games',[])+doc.get('next_games',[])
    else:games=doc.get('games',[])
    games=games if isinstance(games,list) else []
    return {'league':league,'scoreboard_games':len(games),'source_generated_at':doc.get('generated_at'),'scoreboard_status':doc.get('status') or 'STATUS_NOT_SPECIFIED','verified_model_edge':False,'approved_prediction_market_picks':0,'stage':'SCOREBOARD_ONLY_REQUIRES_SPORT_SPECIFIC_MODEL_AND_MARKET_AUDIT'}
def main():
    rows=[];checks={}
    for league in LEAGUES:
        p=ROOT/'commercial_web/public'/f'{league.lower()}_scores.json'
        if not p.exists():rows.append({'league':league,'stage':'SOURCE_MISSING','scoreboard_games':0});continue
        raw=p.read_bytes()
        checks[league]=hashlib.sha256(raw).hexdigest()
        rows.append(inspect(league,json.loads(raw)))
    out={'schema':'zenith.multisport.readiness.v1','generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'leagues':rows,'source_sha256':checks,'approved_new_picks':0,'notes':['An active scoreboard is not an independent forecast','No league inherited NFL probabilities, fees or settlement rules','Research-only readiness inventory']}
    dest=ROOT/'nfl_live/prediction_markets/multisport_readiness_latest.json'
    dest.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps([{'league':r['league'],'games':r['scoreboard_games'],'stage':r['stage']} for r in rows]))
if __name__=='__main__':main()
