"""Retrospective MLB research features must never read future game outcomes."""
from __future__ import annotations

import unittest
from copy import deepcopy

import pandas as pd

from intelligence_warehouse.historical_recovery.mlb_asof_feature_store import (
    attach_prior_completed_season_speed,
    build_official_hitter_game_features,
    FEATURE_SCOPE,
)


def biomechanics(season=2025,first_eligible=2026):
    return pd.DataFrame([
        {'player_id':501,'prior_season_sprint_speed_ft_per_sec':29.1,
         'prior_season_bat_speed_mph':73.3,'prior_season_sprint_qualified':True,
         'prior_season_bat_qualified':True,'source_completed_season':season,
         'feature_research_season':first_eligible,'approved_for_live_model':False},
        {'player_id':502,'prior_season_sprint_speed_ft_per_sec':None,
         'prior_season_bat_speed_mph':None,'prior_season_sprint_qualified':False,
         'prior_season_bat_qualified':False,'source_completed_season':season,
         'feature_research_season':first_eligible,'approved_for_live_model':False},
    ])


def player_row(game,day,player=501,hits=2,walks=1,pa=4):
    return dict(game_pk=game,player_id=player,official_date=day,
        game_date=f'{day}T19:05:00Z',season=2026,group='HITTING',
        status='Final',game_type='R',hits=hits,walks=walks,
        strikeouts=1,plate_appearances=pa,total_bases=float(hits),
        stolen_bases=0)


class MLBAsOfFeatureStoreTests(unittest.TestCase):
    def test_prior_season_sprint_speed_joins_by_exact_id_not_player_name(self):
        source=biomechanics()
        dates=pd.DataFrame([
            {'game_pk':100,'player_id':501,'official_start':'2026-04-01T19:05:00Z'},
            {'game_pk':101,'player_id':999,'official_start':'2026-04-01T19:05:00Z'},
        ])
        result=attach_prior_completed_season_speed(dates,source,target_season=2026)
        a=result.set_index('game_pk')
        self.assertEqual(a.loc[100,'prior_sprint_speed_ft_per_sec'],29.1)
        self.assertEqual(a.loc[100,'prior_bat_speed_mph'],73.3)
        self.assertTrue(pd.isna(a.loc[101,'prior_sprint_speed_ft_per_sec']))
        self.assertFalse(a.loc[101,'sprint_speed_observed'])
        self.assertFalse(a.loc[100,'source_proven_at_time_of_original_quote'])
        self.assertFalse(a.loc[100,'live_betting_approved'])

    def test_same_year_or_future_season_source_rejected(self):
        dates=pd.DataFrame([{'game_pk':100,'player_id':501,'official_start':'2026-04-01T19:05:00Z'}])
        for src in (biomechanics(2026,2027),biomechanics(2024,2025)):
            with self.subTest(src=src.iloc[0].to_dict()):
                with self.assertRaisesRegex(ValueError,'immediately prior season'):
                    attach_prior_completed_season_speed(dates,src,target_season=2026)
        old=dates.copy()
        old.loc[0,'official_start']='2025-06-11T19:05:00Z'
        with self.assertRaisesRegex(ValueError,'target season'):
            attach_prior_completed_season_speed(old,biomechanics(),target_season=2026)

    def test_duplicate_biomechanics_id_rejected(self):
        d=biomechanics()
        dates=pd.DataFrame([{'game_pk':100,'player_id':501,'official_start':'2026-04-01T19:05:00Z'}])
        with self.assertRaisesRegex(ValueError,'duplicate'):
            attach_prior_completed_season_speed(dates,pd.concat([d,d.iloc[:1]]),target_season=2026)

    def test_prior_game_window_excludes_target_and_same_date_doubleheader(self):
        hist=pd.DataFrame([
            player_row(10,'2026-03-20',hits=0,walks=0),
            player_row(11,'2026-03-21',hits=1,walks=1),
            player_row(12,'2026-03-22',hits=2,walks=2),
            player_row(13,'2026-03-23',hits=3,walks=3),
            player_row(14,'2026-03-24',hits=4,walks=4),
            player_row(16,'2026-03-25',hits=99,walks=99),
            player_row(15,'2026-03-25',hits=60,walks=60),
            player_row(17,'2026-03-27',hits=0,walks=0),
        ])
        features,labels=build_official_hitter_game_features(hist,biomechanics(),target_season=2026)
        f=features.set_index('game_pk')
        self.assertEqual(f.loc[15,'prior_games_count'],5)
        self.assertEqual(f.loc[16,'prior_games_count'],5)
        self.assertEqual(f.loc[15,'prior_last5_hits_avg'],2.0)
        self.assertEqual(f.loc[16,'prior_last5_hits_avg'],2.0)
        self.assertEqual(f.loc[17,'prior_last5_hits_avg'],(2+3+4+60+99)/5)
        self.assertEqual(f.loc[15,'prior_last_date'],'2026-03-24')
        self.assertEqual(f.loc[17,'prior_last_date'],'2026-03-25')
        self.assertEqual(labels.set_index('game_pk').loc[16,'realized_hits'],99)
        self.assertNotIn('realized_hits',features.columns)
        self.assertNotIn('current_game_hits',features.columns)
        self.assertEqual(f.loc[15,'source_time_class'],FEATURE_SCOPE)
        self.assertFalse(f.loc[15,'roster_selection_known_before_game'])
        self.assertFalse(f.loc[15,'usable_as_original_live_hulk_prediction'])

    def test_mutating_target_game_result_changes_labels_not_its_features(self):
        hist=pd.DataFrame([
            player_row(10,'2026-03-20',hits=1),
            player_row(11,'2026-03-21',hits=1),
            player_row(12,'2026-03-22',hits=1),
            player_row(13,'2026-03-23',hits=1),
            player_row(14,'2026-03-24',hits=1),
            player_row(15,'2026-03-25',hits=3),
        ])
        before,outcomes=build_official_hitter_game_features(hist,biomechanics())
        after=hist.copy()
        after.loc[after.game_pk.eq(15),'hits']=9999
        after.loc[after.game_pk.eq(15),'walks']=999
        after.loc[after.game_pk.eq(15),'total_bases']=10000
        result,outcomes_after=build_official_hitter_game_features(after,biomechanics())
        pd.testing.assert_frame_equal(before.sort_index(axis=1),result.sort_index(axis=1))
        self.assertNotEqual(outcomes.iloc[-1]['realized_hits'],outcomes_after.iloc[-1]['realized_hits'])

    def test_leakage_from_postgame_participant_universe_is_explicitly_flagged(self):
        hist=pd.DataFrame([player_row(10,'2026-03-20')])
        features,labels=build_official_hitter_game_features(hist,biomechanics())
        self.assertFalse(features['roster_selection_known_before_game'].any())
        self.assertFalse(features['live_betting_approved'].any())
        self.assertTrue(labels['grade_is_official_analytic_only_not_sportsbook_settlement'].all())

if __name__=='__main__':unittest.main()
