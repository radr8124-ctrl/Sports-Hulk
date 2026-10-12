#!/usr/bin/env python3
"""Refresh visible NHL PrizePicks research watches; never approve wagers."""
import csv,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'nhl_live/decision/NHL_PRIZEPICKS_DECISIONS.csv'
OUTPUTS=[ROOT/'commercial_web/public/nhl_prizepicks_unpriced_watches.json',ROOT/'commercial_web/dist/nhl_prizepicks_unpriced_watches.json']

def build(rows):
    watches=[]
    for row in rows:
        if row.get('decision')!='HIGH_JUICE_WATCH':continue
        if str(row.get('prizepicks_actual_bookmaker_price_verified')).lower()=='true':continue
        watches.append({k:row.get(k) for k in ('player','market_subtype','side','line','start_dt','away_team','home_team')})
    return {'generated_at':datetime.now(timezone.utc).isoformat(),'status':'UNPRICED_RESEARCH_ONLY','approved_picks':0,'bookmaker_prices_verified':0,'watches':watches}

def main():
    with SOURCE.open(newline='') as f:payload=build(csv.DictReader(f))
    content=json.dumps(payload,indent=2)+'\n'
    for output in OUTPUTS:
        output.parent.mkdir(parents=True,exist_ok=True)
        fd,temp=tempfile.mkstemp(dir=output.parent,prefix='.unpriced-')
        try:
            with os.fdopen(fd,'w') as f:f.write(content)
            os.replace(temp,output)
        finally:
            if os.path.exists(temp):os.unlink(temp)
    print('Refreshed',len(payload['watches']),'unpriced watches in public and dist')
if __name__=='__main__':main()
