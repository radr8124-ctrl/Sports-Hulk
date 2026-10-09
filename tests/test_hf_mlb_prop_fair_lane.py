"""Per-prop historical price-vs-feature tests must not confer live approval."""
import unittest
from datetime import datetime,timedelta,timezone
from intelligence_warehouse.betting_v2.hf_mlb_prop_fair_lane import evaluate_fair_price_lane


def generated(n=70,market='player hits'):
    start=datetime(2026,3,20,tzinfo=timezone.utc)
    return [dict(status='VERIFIED_HISTORICAL',pair_status='VERIFIED_SAME_BOOK_TIME_PAIR',
        market=market,official_game_pk=i+100,official_start=(start+timedelta(days=i)).isoformat(),
        market_fair_probability=.4+(i%4)*.04,market_implied_probability=.45+(i%4)*.04,
        pregame_context_signal=(i%7-3)*.2,asof_status='PREGAME_FEATURE_VERIFIED',
        verified_win=bool(i%3==0),book='fanduel') for i in range(n)]


class FairPriceLaneTests(unittest.TestCase):
    def test_separate_market_with_exact_de_vig_prices_has_game_blocked_holdout(self):
        result=evaluate_fair_price_lane(generated(),train_fraction=.6)
        self.assertEqual(result['status'],'HISTORICAL_HOLDOUT_COMPLETED')
        self.assertEqual(result['historical_scope'],'EXTERNAL_BACKTEST_ONLY')
        self.assertEqual((result['training_independent_games'],result['holdout_independent_games']),(42,28))
        self.assertTrue(result['no_game_or_time_overlap'])
        self.assertIsInstance(result['fair_market_brier'],float)
        self.assertIsInstance(result['market_calibrated_brier'],float)
        self.assertIsInstance(result['fair_market_plus_pregame_brier'],float)
        self.assertEqual(result['live_play_approved'],False)
        self.assertIn('paired_game_brier_delta_lcb90',result)
        self.assertIn('paired_game_brier_delta_lcb95',result)
        self.assertIn('paired_game_brier_delta_lcb9875',result)
        self.assertLessEqual(result['paired_game_brier_delta_lcb9875'],result['paired_game_brier_delta_lcb95'])
        self.assertLessEqual(result['paired_game_brier_delta_lcb95'],result['paired_game_brier_delta_lcb90'])
        self.assertLessEqual(result['paired_game_brier_delta_ucb90'],result['paired_game_brier_delta_ucb95'])
        self.assertLess(result['training_last_start'],result['holdout_first_start'])

    def test_smaller_lanes_mark_insufficient_not_passed(self):
        result=evaluate_fair_price_lane(generated(22))
        self.assertEqual(result['status'],'INSUFFICIENT_LANE_INDEPENDENT_GAMES')
        self.assertEqual(result['live_play_approved'],False)

    def test_mixed_markets_forbidden_and_no_book_timestamp_pair_excluded(self):
        rows=generated()
        rows[1]['market']='player rbis'
        self.assertEqual(evaluate_fair_price_lane(rows)['status'],'MIXED_MARKET_LANES_FORBIDDEN')
        rows=generated()
        rows[1]['pair_status']='NO_EXACT_OPPOSITE_SIDE'
        result=evaluate_fair_price_lane(rows)
        self.assertEqual(result['eligible_independent_games'],69)

    def test_duplicate_snapshots_cannot_multiply_game_count(self):
        data=generated(40)
        duplicate=[{**r,'book':'other'} for r in data]
        result=evaluate_fair_price_lane(data+duplicate)
        self.assertEqual(result['eligible_independent_games'],40)

    def test_wrong_status_or_missing_fair_price_never_enters_proof(self):
        data=generated(25)
        for row in data:
            row['market_fair_probability']=None
        self.assertEqual(evaluate_fair_price_lane(data)['eligible_independent_games'],0)


if __name__=='__main__':unittest.main()
