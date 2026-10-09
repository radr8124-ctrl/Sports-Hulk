"""Pregame feature enrichment must not observe target or later MLB games."""
from __future__ import annotations
import unittest
from datetime import datetime, timezone, timedelta
import pandas as pd

from intelligence_warehouse.betting_v2.hf_mlb_prop_asof import (
    enrich_strictly_pregame, compare_model_vs_market,
)


def make_history():
    rows=[]
    for i in range(7):
        day=f'2026-04-{i+1:02d}'
        rows.append(dict(game_pk=i+100,player='José Ramírez',player_id=555,group='HITTING',
            official_date=day,game_date=f'{day}T19:00:00Z',game_type='R',status='Final',
            hits=float(i%2),total_bases=float(1+i),home_runs=0.0,rbi=0.0,walks=1.0,strikeouts=0.0))
    rows.append(dict(game_pk=999,player='José Ramírez',player_id=555,group='HITTING',
        official_date='2026-04-08',game_date='2026-04-08T22:40:00Z',game_type='R',status='Final',
        hits=10.0,total_bases=99.0,home_runs=8.0,rbi=11.0,walks=0.0,strikeouts=0.0))
    rows.append(dict(game_pk=1000,player='José Ramírez',player_id=555,group='HITTING',
        official_date='2026-04-09',game_date='2026-04-09T19:00:00Z',game_type='R',status='Final',
        hits=10.0,total_bases=1000.0,home_runs=5.0,rbi=0.0,walks=1.0,strikeouts=0.0))
    return pd.DataFrame(rows)


def verified():
    return dict(status='VERIFIED_HISTORICAL',official_game_pk=999,
        official_group='HITTING',provider_game_id='m~1',player='jose ramirez',
        market='player bases',side='over',line=3.5,odds=2.1,
        market_implied_probability=1/2.1,
        official_start='2026-04-08T22:40:00+00:00',ts='2026-04-08T18:00:00',
        verified_win=True)


class StrictPregameFeatureTests(unittest.TestCase):
    def test_future_and_target_box_scores_cannot_affect_pregame_feature(self):
        rows=enrich_strictly_pregame([verified()],make_history(),minimum_games=5)
        self.assertEqual(len(rows),1)
        r=rows[0]
        self.assertEqual(r['asof_status'],'PREGAME_FEATURE_VERIFIED')
        self.assertEqual(r['prior_games_available'],7)
        self.assertEqual(r['last5_stat_avg'],5.0) # games day3-day7 have stats 3..7
        self.assertEqual(r['prior_latest_date'],'2026-04-07')
        self.assertLess(r['prior_latest_date'],'2026-04-08')
        self.assertNotEqual(r['last5_stat_avg'],99)

    def test_analytically_official_derived_grade_can_supply_test_only_pregame_features(self):
        row=verified()
        row['status']='OFFICIAL_DERIVED_HISTORICAL'
        row['platform_settlement_claim']=False
        result=enrich_strictly_pregame([row],make_history(),minimum_games=5)
        self.assertEqual(result[0]['asof_status'],'PREGAME_FEATURE_VERIFIED')

    def test_quote_earlier_in_same_day_cannot_use_same_day_result(self):
        row=verified(); row['ts']='2026-04-07T12:00:00'
        x=enrich_strictly_pregame([row],make_history(),minimum_games=5)[0]
        self.assertEqual(x['prior_games_available'],6)
        self.assertEqual(x['prior_latest_date'],'2026-04-06')

    def test_identity_mismatch_and_short_history_fail_closed(self):
        bad=verified();bad['official_game_pk']=12345
        a=enrich_strictly_pregame([bad],make_history(),minimum_games=5)[0]
        self.assertEqual(a['asof_status'],'NO_UNIQUE_PLAYER_ID_MATCH')
        b=enrich_strictly_pregame([verified()],make_history(),minimum_games=8)[0]
        self.assertEqual(b['asof_status'],'INSUFFICIENT_PREGAME_PLAYER_GAMES')

    def test_comparison_is_illustrative_only_and_never_an_edge_approval(self):
        base=datetime(2026,4,1,tzinfo=timezone.utc)
        rows=[]
        for i in range(35):
            rows.append(dict(status='VERIFIED_HISTORICAL',official_game_pk=i+1,
                official_start=(base+timedelta(days=i)).isoformat(),
                market_implied_probability=0.45+(i%3)*0.03,verified_win=bool(i%2),
                asof_status='PREGAME_FEATURE_VERIFIED',pregame_context_signal=0.1*i))
        result=compare_model_vs_market(rows)
        self.assertTrue(result['chronological_no_game_overlap'])
        self.assertTrue(result['chronological_no_time_overlap'])
        self.assertEqual(result['historical_scope'],'RESEARCH_ONLY_NOT_PRODUCTION_APPROVED')
        self.assertEqual(result['train_games']+result['holdout_games'],35)
        self.assertIn('market_plus_pregame_brier',result)
        self.assertIsInstance(result['market_plus_pregame_brier'],float)


if __name__=='__main__': unittest.main()
