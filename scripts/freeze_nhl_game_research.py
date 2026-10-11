#!/usr/bin/env python3
"""Freeze a read-only NHL results/fixture receipt; never invent historical picks."""
import datetime,hashlib,json,pathlib,os,tempfile
ROOT=pathlib.Path('/home/ubuntu/sports-hulk')
IN=ROOT/'commercial_web/public/nhl_scores.json'
OUT=ROOT/'nfl_live/prediction_markets/nhl_game_research_latest.json'
def summarize(d):
 rows=[]
 for g in d.get('games',[]):
  state='FINAL_RESULT_ONLY' if g.get('final') is True else ('LIVE_NO_PREGAME_PICK' if g.get('live') else 'UPCOMING_RESEARCH_ONLY')
  rows.append({'event_id':str(g.get('event_id','')),'start_time':g.get('start_time'),'home':g.get('home'),'away':g.get('away'),'state':state,'score':{'home':g.get('home_score'),'away':g.get('away_score')} if state=='FINAL_RESULT_ONLY' else None,'frozen_pregame_projection':None,'prediction_market_matched':False,'approved_pick':False})
 return rows
def main():
 raw=IN.read_bytes();doc=json.loads(raw);rows=summarize(doc)
 out={'schema':'zenith.nhl.game_research.v1','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_generated_at':doc.get('generated_at'),'source_sha256':hashlib.sha256(raw).hexdigest(),'games':len(rows),'final_results':sum(r['state']=='FINAL_RESULT_ONLY' for r in rows),'upcoming':sum(r['state']=='UPCOMING_RESEARCH_ONLY' for r in rows),'live':sum(r['state']=='LIVE_NO_PREGAME_PICK' for r in rows),'frozen_predictions':0,'approved_picks':0,'limitations':['Final scores are outcomes, not evidence of predictions','NHL regulation, overtime and shootout contracts require separate settlement checks','Independent probabilities and executable quotes have not been checked'],'rows':rows}
 data=json.dumps(out,indent=2)+'\n'
 OUT.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(dir=OUT.parent,prefix='.nhl_research_')
 with os.fdopen(fd,'w') as f:f.write(data)
 os.replace(tmp,OUT)
 print(json.dumps({k:out[k] for k in ['games','final_results','upcoming','live','frozen_predictions','approved_picks']}))
if __name__=='__main__':main()
