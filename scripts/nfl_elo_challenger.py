"""Fixed NFL Elo challenger, never used for approved picks or sizing."""
import math
from collections import defaultdict
from itertools import groupby
from capture_nfl_narrow_forward_quotes import canonical

CONFIG=dict(k=20,home_adv=48,revert=.75,mov_scale=2.2)
class SportElo:
    def __init__(self):
        self.r=defaultdict(lambda:1500.)
    def win_prob(self,home,away,neutral=False):
        home,away=canonical(home),canonical(away)
        if not home or not away or home==away:raise ValueError('Distinct teams required')
        diff=self.r[home]+(0 if neutral else CONFIG['home_adv'])-self.r[away]
        x=diff*math.log(10)/400
        return 1/(1+math.exp(-x)) if x>=0 else math.exp(x)/(1+math.exp(x))
    def update(self,home,away,home_pts,away_pts,neutral=False):
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<0 or int(x)!=x for x in (home_pts,away_pts)):
            raise ValueError('Finite nonnegative integer scores required')
        home,away=canonical(home),canonical(away)
        p=self.win_prob(home,away,neutral)
        result=1. if home_pts>away_pts else 0. if home_pts<away_pts else .5
        margin=max(abs(home_pts-away_pts),1)
        mult=math.log(margin+1)*CONFIG['mov_scale']/(.001*abs(self.r[home]-self.r[away])+CONFIG['mov_scale'])
        delta=CONFIG['k']*mult*(result-p)
        self.r[home]+=delta;self.r[away]-=delta
    def new_season(self):
        for team in list(self.r):
            self.r[team]=1500+CONFIG['revert']*(self.r[team]-1500)

def replay(games):
    if len({g['game_id'] for g in games})!=len(games):raise ValueError('Duplicate game identity')
    model=SportElo();predictions={};last_season=None
    ordered=sorted(games,key=lambda g:(g['gameday'],g['game_id']))
    for day,block in groupby(ordered,key=lambda g:g['gameday']):
        block=list(block);seasons={g['season'] for g in block}
        if len(seasons)!=1:raise ValueError('Conflicting seasons on one day')
        season=next(iter(seasons))
        if last_season is not None and season<last_season:raise ValueError('Nonchronological seasons')
        if last_season is not None and season!=last_season:model.new_season()
        last_season=season
        for g in block:
            if g.get('location') not in ('Home','Neutral'):raise ValueError('Unknown home/neutral field')
            predictions[g['game_id']]=model.win_prob(g['home_team'],g['away_team'],g['location']=='Neutral')
        # Conservative date-blocked replay: no same-day game can see another result.
        for g in block:
            model.update(g['home_team'],g['away_team'],g['home_score'],g['away_score'],g['location']=='Neutral')
    return predictions
