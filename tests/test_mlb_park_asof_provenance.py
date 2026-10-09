"""Whole-season venue results must only inform FOLLOWING seasons."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from baseball_vault import park_factors, historical_pregame_features


def fixture_game(pk,yr,kind='R',status='Final',total=9,venue='Sample Park',venue_id=42):
    return dict(gamePk=pk,officialDate=f'{yr}-07-12',gameDate=f'{yr}-07-12T20:00:00Z',
                gameType=kind,status=status,venue=venue,venue_id=venue_id,
                home_team='Alpha',away_team='Beta',home_score=4,away_score=total-4,
                home_days_since_last=1,away_days_since_last=1)


class ParkTimeProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        games=[fixture_game(1,2024,total=8),fixture_game(2,2025,total=10),
               fixture_game(3,2025,kind='S',total=200),fixture_game(4,2026,total=300),
               fixture_game(5,2025,venue='Other',venue_id=71,total=6)]
        pd.DataFrame(games).to_csv(self.folder/'MLB_GAME_MASTER.csv',index=False)

    def test_park_factor_aggregator_excludes_exhibition_and_postseason(self):
        with patch.object(park_factors,'DERIVED',self.folder):
            park_factors.build()
        parks=pd.read_csv(self.folder/'MLB_PARK_RUN_FACTORS.csv')
        year2025=parks[(parks.season==2025)&(parks.venue_id==42)]
        self.assertEqual(int(year2025.games.iloc[0]),1)
        self.assertLess(float(year2025.avg_total_runs.iloc[0]),20)

    def test_pregame_features_use_previous_year_not_same_year_final_park_factor(self):
        pf=pd.DataFrame([
            {'season':2024,'venue_id':42,'venue':'Sample Park','run_factor':.90,'games':80},
            {'season':2025,'venue_id':42,'venue':'Sample Park','run_factor':1.12,'games':80},
            {'season':2026,'venue_id':42,'venue':'Sample Park','run_factor':9.99,'games':80},
            {'season':2024,'venue_id':71,'venue':'Other','run_factor':1.02,'games':80},
        ])
        pf.to_csv(self.folder/'MLB_PARK_RUN_FACTORS.csv',index=False)
        with patch.object(historical_pregame_features,'DERIVED',self.folder):
            historical_pregame_features.build()
        d=pd.read_csv(self.folder/'MLB_HISTORICAL_PREGAME_FEATURES.csv')
        reference=d.set_index('gamePk')
        self.assertAlmostEqual(float(reference.loc[2,'park_run_factor']),.90)
        self.assertEqual(int(reference.loc[2,'park_factor_reference_season']),2024)
        self.assertAlmostEqual(float(reference.loc[4,'park_run_factor']),1.12)
        self.assertEqual(int(reference.loc[4,'park_factor_reference_season']),2025)
        self.assertTrue(pd.isna(reference.loc[1,'park_run_factor']))
        self.assertTrue(pd.isna(reference.loc[1,'park_factor_reference_season']))

    def test_park_factor_unmatched_venue_must_remain_unknown(self):
        pf=pd.DataFrame([
            {'season':2025,'venue_id':999,'venue':'Unrelated','run_factor':10,'games':100}
        ])
        pf.to_csv(self.folder/'MLB_PARK_RUN_FACTORS.csv',index=False)
        with patch.object(historical_pregame_features,'DERIVED',self.folder):
            historical_pregame_features.build()
        d=pd.read_csv(self.folder/'MLB_HISTORICAL_PREGAME_FEATURES.csv')
        self.assertTrue(d.park_run_factor.isna().all())

if __name__=='__main__':unittest.main()
