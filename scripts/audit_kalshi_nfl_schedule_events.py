#!/usr/bin/env python3
"""Read-only NFL matchup discovery; exact date + both ESPN team abbreviations."""
import urllib.request,json,datetime,re,pathlib
ROOT=pathlib.Path('/home/ubuntu/sports-hulk')
URL='https://external-api.kalshi.com/trade-api/v2/events?limit=200&status=open&series_ticker=KXNFLGAME'
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'SportsZenithResearch/1.0'})
 with urllib.request.urlopen(req,timeout=15) as response:return json.load(response)
def audit(events,games):
 bykey={}
 for g in games:
  try:day=datetime.datetime.fromisoformat(g['start_time'].replace('Z','+00:00')).astimezone(datetime.timezone(datetime.timedelta(hours=-4))).strftime('%y%b%d').upper()
  except (ValueError,KeyError):continue
  a,b=str(g.get('away_abbr','')).upper(),str(g.get('home_abbr','')).upper()
  if a and b:bykey[(day,a,b)]=g
 matches=[];rejections=[]
 for event in events:
  ticker=str(event.get('event_ticker',''))
  match=re.fullmatch(r'KXNFLGAME-(\d{2}[A-Z]{3}\d{2})([A-Z]{2,3})([A-Z]{2,3})',ticker)
  if not match:rejections.append({'id':ticker,'reason':'UNRECOGNIZED_TICKER'});continue
  day,away,home=match.groups()
  game=bykey.get((day,away,home))
  if game:matches.append({'provider':'KALSHI','event_ticker':ticker,'sport':'NFL','espn_event_id':str(game['event_id']),'away_abbr':away,'home_abbr':home,'status':'SCHEDULE_MATCH_ONLY_NO_CONTRACT_VERIFICATION'})
  else:rejections.append({'id':ticker,'reason':'NO_EXACT_MATCH_IN_CURRENT_SCHEDULE'})
 return matches,rejections
def main():
 events=fetch(URL).get('events',[])
 scores=json.loads((ROOT/'commercial_web/public/nfl_scores.json').read_text())
 matches,rejections=audit(events,scores.get('games',[])+scores.get('next_games',[]))
 out={'schema':'zenith.kalshi.nfl.schedule_candidates.v1','captured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_url':URL,'events_seen':len(events),'schedule_matches':len(matches),'rejections':len(rejections),'approved_contract_mappings':0,'approved_picks':0,'matches':matches,'rejected_examples':rejections[:15],'limits':['Matches event ticker date and both team abbreviations only','No exact market outcome/settlement verification','No executable quote, liquidity or fee validation']}
 dest=ROOT/'nfl_live/prediction_markets/kalshi_nfl_schedule_candidates_latest.json';dest.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'events_seen':len(events),'schedule_matches':len(matches),'rejections':len(rejections),'examples':matches[:3]}))
if __name__=='__main__':main()
