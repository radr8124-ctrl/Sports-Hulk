"""Pre-registered fixed NFL team score-form model 2016-24; 2025 diagnostic only."""
from __future__ import annotations
import json,copy,hashlib
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

from intelligence_warehouse.historical_recovery.nfl_prior_score_form_model import (
    historical_prior_scoring_matrix,
    fit_nfl_team_score_model,
    SOURCE_FEATURE_NAMES,
    _prob,
)

ROOT=Path(__file__).resolve().parents[1]

def game(week,home='MIA',away='CIN',score=(20,17),season=2024,rest=(7,7),neutral=False,
         money=(-120,110),game_id=None):
    return {
        'game_id':game_id or f'{season}_{week:02d}_{away}_{home}',
        'season':season,'week':week,'game_type':'REG',
        'gameday':f'{season}-09-{week+4:02d}','home_team':home,'away_team':away,
        'home_score':score[0],'away_score':score[1],
        'home_moneyline':money[0],'away_moneyline':money[1],
        'home_rest':rest[0],'away_rest':rest[1],
        'location':'Neutral' if neutral else 'Home',
    }

class HistoricalNoLeakNFLScoringResearchTests(unittest.TestCase):
    def test_one_source_game_per_row_uses_only_earlier_same_season_form(self):
        g=[game(1,score=(20,10)),game(2,score=(30,7)),game(3,score=(28,10)),game(4,score=(17,20))]
        matrix,meta=historical_prior_scoring_matrix(pd.DataFrame(g))
        self.assertEqual(len(matrix),4)
        self.assertEqual(len(matrix[0]['features']),9)
        self.assertEqual(matrix[0]['features'][2:6],[0.,0.,0.,0.])
        self.assertEqual(matrix[0]['features'][7],0.)
        self.assertEqual(matrix[3]['features'][7],1.)
        self.assertEqual(matrix[3]['prior_week_max_for_team_home'],3)
        self.assertEqual(matrix[3]['prior_week_max_for_team_away'],3)
        self.assertEqual(meta['future_game_scores_used'],0)

    def test_target_week_outcome_change_cannot_alter_its_own_prediction_features(self):
        data=pd.DataFrame([game(1,score=(20,14)),game(2,score=(31,10)),game(3,score=(13,17))])
        initial,_=historical_prior_scoring_matrix(data)
        changed=data.copy()
        changed.loc[changed.week.eq(3),'home_score']=52
        changed.loc[changed.week.eq(3),'away_score']=0
        altered,_=historical_prior_scoring_matrix(changed)
        self.assertEqual(initial[2]['features'],altered[2]['features'])

    def test_team_same_week_future_outcome_does_not_leak_to_other_same_week(self):
        x=[game(1),game(2)]
        x.append(game(3,home='MIA',away='PIT',game_id='2024_03_PIT_MIA',score=(77,0)))
        x.append(game(3,home='CIN',away='NYJ',game_id='2024_03_NYJ_CIN',score=(0,65)))
        matrix,_=historical_prior_scoring_matrix(pd.DataFrame(x))
        target=[r for r in matrix if r['game_id']=='2024_03_PIT_MIA'][0]
        changed=copy.deepcopy(x)
        changed[3]['home_score']=88
        changed[3]['away_score']=0
        matrix_changed,_=historical_prior_scoring_matrix(pd.DataFrame(changed))
        next_row=[r for r in matrix_changed if r['game_id']=='2024_03_PIT_MIA'][0]
        self.assertEqual(target['features'],next_row['features'])

    def test_forged_season_duplicates_futuristic_game_schema_rejected(self):
        x=pd.DataFrame([game(1),game(1)])
        with self.assertRaisesRegex(ValueError,'[Dd]uplicate'):
            historical_prior_scoring_matrix(x)
        x=pd.DataFrame([game(1,season=2026)])
        with self.assertRaisesRegex(ValueError,'2026'):
            historical_prior_scoring_matrix(x)
        x=pd.DataFrame([game(1,money=(-101,-101)),game(2,score=(20,20))])
        vec,meta=historical_prior_scoring_matrix(x)
        self.assertEqual(len(vec),1)
        self.assertEqual(meta['tied_games_skipped'],1)

    def test_original_ten_year_train_cutoff_2025_holdout_and_unproven_edge(self):
        h=pd.read_csv(ROOT/'data_vault/derived/NFL_GAME_MASTER.csv',low_memory=False)
        matrix,source=historical_prior_scoring_matrix(h)
        model=fit_nfl_team_score_model(matrix,source)
        self.assertEqual(len(model['features']),9)
        self.assertEqual(model['features'],list(SOURCE_FEATURE_NAMES))
        self.assertEqual(model['training_seasons'],list(range(2016,2025)))
        self.assertEqual(model['secondary_holdout_seasons'],[2025])
        self.assertGreater(model['training_independent_games'],2100)
        self.assertGreater(model['holdout_2025_independent_games'],200)
        self.assertEqual(len(model['training_game_ids']),model['training_independent_games'])
        self.assertTrue(max(model['training_seasons'])<min(model['secondary_holdout_seasons']))
        self.assertFalse(model['training_2025_outcomes_used'])
        self.assertFalse(model['training_2026_outcomes_used'])
        self.assertFalse(model['historical_game_weather_used_as_first_future_forecast'])
        self.assertFalse(model['2026_live_betting_play_approved'])
        self.assertFalse(model['real_bookmaker_market_edge_proven'])

    def test_model_fit_is_deterministic_without_changing_first_future_source(self):
        h=pd.read_csv(ROOT/'data_vault/derived/NFL_GAME_MASTER.csv',low_memory=False)
        source,meta=historical_prior_scoring_matrix(h)
        first=fit_nfl_team_score_model(source,meta)
        second=fit_nfl_team_score_model(source,meta)
        self.assertEqual(first['coefficients'],second['coefficients'])
        self.assertEqual(first['two_col_market_only_coefficients'],second['two_col_market_only_coefficients'])
        self.assertEqual(first['historical_train_matrix_and_results_sha256'],
                         second['historical_train_matrix_and_results_sha256'])
        self.assertTrue(0<_prob([1.,0.,0.,0.,0.,0.,0.,0.,0.],first['coefficients'])<1)

if __name__=='__main__':unittest.main()
