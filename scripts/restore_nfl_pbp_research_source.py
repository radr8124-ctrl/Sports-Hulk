#!/usr/bin/env python3
"""Restore one official historical NFLverse source and prior-week research features."""
import hashlib,json,sys,urllib.request
from pathlib import Path
from datetime import datetime,timezone
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def prior_features(games):
 out=[]
 for (season,team),group in games.groupby(['season','team']):
  previous=[]
  for week,slate in group.sort_values(['week','game_id']).groupby('week'):
   history=previous[-5:]
   value=sum(x[0] for x in history)/len(history) if history else None
   for row in slate.itertuples(index=False):out.append(dict(season=int(season),team=team,game_id=row.game_id,week=int(week),prior_games=len(history),prior_max_week=max((x[1] for x in history),default=None),prior5_off_epa_per_play=value))
   previous.extend((float(row.epa),int(week)) for row in slate.itertuples(index=False))
 return pd.DataFrame(out)
def main():
 season=2024
 directory=ROOT/'data_vault/raw/nflverse_research_replay';directory.mkdir(parents=True,exist_ok=True)
 url=f'https://api.github.com/repos/nflverse/nflverse-data/releases/tags/pbp'
 req=urllib.request.Request(url,headers={'User-Agent':'SportsZenithResearch/1.0'})
 with urllib.request.urlopen(req,timeout=20) as response:release=json.load(response)
 asset=next(a for a in release['assets'] if a['name']==f'play_by_play_{season}.parquet')
 path=directory/asset['name']
 if not path.exists():
  with urllib.request.urlopen(urllib.request.Request(asset['browser_download_url'],headers={'User-Agent':'SportsZenithResearch/1.0'}),timeout=60) as response:raw=response.read()
  if len(raw)!=asset['size']:raise ValueError('Incomplete source download')
  temporary=path.with_suffix('.tmp');temporary.write_bytes(raw);temporary.replace(path)
 raw=path.read_bytes()
 if len(raw)!=asset['size']:raise ValueError('Source size changed')
 digest=hashlib.sha256(raw).hexdigest()
 advertised=asset.get('digest')
 if advertised and advertised.startswith('sha256:') and advertised!='sha256:'+digest:raise ValueError('Publisher digest mismatch')
 fields=['game_id','play_id','season','week','posteam','epa','rush_attempt','pass_attempt','qb_kneel','qb_spike']
 frame=pd.read_parquet(path,columns=fields)
 if not frame.season.eq(season).all():raise ValueError('Season contamination')
 if frame.duplicated(['game_id','play_id']).any():raise ValueError('Duplicate play identity')
 plays=frame[frame.epa.notna()&frame.posteam.notna()&((frame.rush_attempt==1)|(frame.pass_attempt==1))&(frame.qb_kneel!=1)&(frame.qb_spike!=1)]
 games=plays.groupby(['season','week','game_id','posteam'],as_index=False).epa.mean().rename(columns={'posteam':'team'})
 features=prior_features(games)
 if not features[features.prior_max_week.notna()].eval('prior_max_week < week').all():raise ValueError('Same-week source contamination')
 feature_path=directory/f'prior_week_off_epa_{season}.csv';features.to_csv(feature_path,index=False)
 receipt=dict(schema='zenith.nfl.pbp_replay_receipt.v1',captured_at_utc=datetime.now(timezone.utc).isoformat(),season=season,source_url=asset['browser_download_url'],asset_id=asset['id'],source_sha256=digest,source_bytes=len(raw),publisher_digest=advertised,raw_plays=len(frame),eligible_offensive_plays=len(plays),games=int(frame.game_id.nunique()),feature_rows=len(features),feature_sha256=hashlib.sha256(feature_path.read_bytes()).hexdigest(),same_week_or_future_results_in_features=False,source_replay_complete=True,model_trained=False,validated_edge=False,approved_picks=0,limitations=['Current NFLverse revised data is retrospective, not original as-of play capture','Offense EPA only; no independent advantage test yet','One season restored; not the full training history','Off-server restoration not verified'])
 dest=ROOT/'reports/NFL_2024_PBP_REPLAY_RECEIPT_20261011.json';dest.write_text(json.dumps(receipt,indent=2)+'\n')
 if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Source readback failed')
 print(json.dumps(receipt))
if __name__=='__main__':main()
