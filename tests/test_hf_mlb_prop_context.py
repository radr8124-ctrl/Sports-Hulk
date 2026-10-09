"""Historical MLB opponent/park/role context cannot peek at target or later games."""
from __future__ import annotations
import copy
import unittest
from datetime import date,timedelta
import pandas as pd
from intelligence_warehouse.betting_v2.hf_mlb_prop_context import enrich_historical_context


def fixture():
    master=[]
    for i in range(12):
        day=date(2025,8,1)+timedelta(days=i)
        master.append(dict(gamePk=500+i,officialDate=str(day),gameDate=f'{day}T19:00:00Z',gameType='R',status='Final',
                           venue='Alpha Park' if i%2==0 else 'Other Park',venue_id=10 if i%2==0 else 20,
                           home_team='Alpha' if i%2==0 else 'Gamma',away_team='Beta',home_score=4,away_score=5 if i%2==0 else 3))
    hitters=[]
    for i in range(12):
        day=date(2026,5,1)+timedelta(days=i)
        pk=1000+i
        base=dict(game_pk=pk,official_date=str(day),game_date=f'{day}T12:00:00Z',game_type='R',status='Final')
        hitters.append({**base,'player':'Jane Hitter','player_id':9,'group':'HITTING','team':'Alpha','opponent':'Beta' if i%3==0 else 'Gamma',
                        'hits':1,'plate_appearances':4 if i%2 else 5,'batting_order':100})
        hitters.append({**base,'player':'Opp Pitcher','player_id':50+i,'group':'PITCHING','team':'Beta','opponent':'Alpha',
                        'hits_allowed':7+i%3,'outs':25,'pitcher_strikeouts':7})
        master.append(dict(gamePk=pk,officialDate=str(day),gameDate=f'{day}T12:00:00Z',gameType='R',status='Final',
                           venue='Other Park',venue_id=20,home_team='Beta',away_team='Alpha',home_score=2,away_score=5))
    # Current game is POSTGAME factual source; may be used to identify fixture,
    # NEVER to supply features, outcomes, current starter or actual lineup.
    master.append(dict(gamePk=9999,officialDate='2026-05-15',gameDate='2026-05-15T22:00:00Z',gameType='R',status='Final',
                       venue='Alpha Park',venue_id=10,home_team='Alpha',away_team='Beta',home_score=70,away_score=90))
    hitters.append(dict(game_pk=9999,official_date='2026-05-15',game_date='2026-05-15T22:00:00Z',game_type='R',status='Final',
                        player='Jane Hitter',player_id=9,group='HITTING',team='Alpha',opponent='Beta',hits=1000,plate_appearances=19,batting_order=100))
    hitters.append(dict(game_pk=9999,official_date='2026-05-15',game_date='2026-05-15T22:00:00Z',game_type='R',status='Final',
                        player='Current Starter',player_id=99,group='PITCHING',team='Beta',opponent='Alpha',hits_allowed=100,outs=27,pitcher_strikeouts=20))
    return pd.DataFrame(hitters),pd.DataFrame(master)


def row():
    return dict(status='VERIFIED_HISTORICAL',asof_status='PREGAME_FEATURE_VERIFIED',
                pair_status='VERIFIED_SAME_BOOK_TIME_PAIR',
                official_player_id=9,official_game_pk=9999,official_group='HITTING',
                official_team='Alpha',official_opponent='Beta',player='jane hitter',
                ts='2026-05-15T16:00:00',official_start='2026-05-15T22:00:00Z',
                market='player hits',side='over',line=.5,odds=1.8,
                official_stat=1000,verified_win=True,market_fair_probability=.53,
                last5_stat_avg=1.0,pregame_context_signal=.1)


class HistoricalMLBContextTests(unittest.TestCase):
    def test_park_only_from_prior_season_and_current_game_results_not_used(self):
        hist,games=fixture()
        a=enrich_historical_context([row()],hist,games,min_prior_park_games=3,min_opp_games=5)
        self.assertEqual(a[0]['context_status'],'PREGAME_CONTEXT_VERIFIED')
        self.assertEqual(a[0]['park_reference_season'],2025)
        self.assertEqual(a[0]['park_source'],'PRIOR_SEASON_REGULAR_SEASON_COMPLETED_ONLY')
        self.assertLess(a[0]['park_run_factor'],2)
        self.assertEqual(a[0]['opp_last10_pitching_hits_allowed_per_9']<20,True)
        self.assertEqual(a[0]['opposing_starter_verified_asof'],False)
        # Future/target outcome edits cannot change a single pregame signal.
        altered=games.copy()
        altered.loc[altered.gamePk.eq(9999),'home_score']=99999
        altered.loc[altered.gamePk.eq(9999),'away_score']=100000
        later=hist.copy()
        later.loc[later.game_pk.eq(9999),'hits']=888888
        later.loc[later.game_pk.eq(9999),'hits_allowed']=888888
        b=enrich_historical_context([row()],later,altered,min_prior_park_games=3,min_opp_games=5)
        for key in ('park_run_factor','opp_last10_pitching_hits_allowed_per_9','opp_last10_runs_allowed',
                    'player_last10_pa_avg','player_rest_days','hitter_vs_opponent_prior_hits_per_game'):
            self.assertEqual(a[0][key],b[0][key],key)

    def test_same_day_game_not_used_and_prior_role_comes_only_from_before_quote(self):
        hist,games=fixture()
        x=enrich_historical_context([row()],hist,games,min_prior_park_games=3,min_opp_games=5)[0]
        self.assertEqual(x['player_prior_latest_official_date'],'2026-05-12')
        self.assertEqual(x['opp_prior_latest_official_date'],'2026-05-12')
        self.assertEqual(x['player_last10_pa_avg'],4.5)
        self.assertEqual(x['player_rest_days'],3)
        self.assertEqual(x['opponent_starter_source_status'],'NO_TIMESTAMPED_PREGAME_PROBABLE_STARTER')

    def test_wrong_current_team_or_missing_park_cannot_be_imputed_from_future(self):
        hist,games=fixture()
        mismatch=row();mismatch['official_team']='Different Team'
        self.assertEqual(enrich_historical_context([mismatch],hist,games,min_prior_park_games=3,min_opp_games=5)[0]['context_status'],'FIXTURE_TEAM_MISMATCH')
        missing=games[~games.officialDate.astype(str).str.startswith('2025')].copy()
        result=enrich_historical_context([row()],hist,missing,min_prior_park_games=3,min_opp_games=5)[0]
        self.assertEqual(result['context_status'],'NO_PRIOR_SEASON_PARK_SAMPLE')
        self.assertIsNone(result.get('park_run_factor'))

    def test_future_contemporary_probable_starter_not_taken_from_boxscore(self):
        hist,games=fixture()
        output=enrich_historical_context([row()],hist,games,min_prior_park_games=3,min_opp_games=5)[0]
        self.assertNotIn('current_starting_pitcher_name',output)
        self.assertFalse(output['opposing_starter_verified_asof'])
        self.assertGreaterEqual(output['opp_prior_games_available'],5)

if __name__=='__main__':unittest.main()
