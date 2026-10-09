"""Survivor Week 5 may review lines without inventing an approved pick."""
import unittest

import pandas as pd

from intelligence_warehouse.survivor_accountability import build_survivor_v2 as v2


class SurvivorMarketReadinessTests(unittest.TestCase):
    def test_stale_primary_rejects_impressive_market_probability(self):
        data = {
            "primary_market_fresh_enough_for_live_decision": "False",
            "market_status": "STALE_PRIMARY_MARKET",
            "market_prob_pct": 84.3,
            "strategy_index": 92,
            "strategy_action": "VIABLE",
            "hulk_decision_tier": "TOP_TIER",
        }
        self.assertFalse(v2.authentic_current_market_ready(pd.Series(data)))
        data["primary_market_fresh_enough_for_live_decision"] = "True"
        self.assertFalse(v2.authentic_current_market_ready(pd.Series(data)))
        data["market_status"] = "LIVE"
        self.assertTrue(v2.authentic_current_market_ready(pd.Series(data)))

    def test_unknown_juice_model_or_rank_blocks_pick(self):
        base = {
            "primary_market_fresh_enough_for_live_decision": True,
            "market_status": "LIVE",
            "market_prob_pct": 76.1,
            "strategy_index": 83,
            "strategy_action": "VIABLE",
            "hulk_decision_tier": "TOP_TIER",
        }
        for change in [
            {"market_prob_pct": None},
            {"market_prob_pct": float("nan")},
            {"market_prob_pct": 100},
            {"market_prob_pct": 0},
            {"strategy_index": None},
            {"strategy_index": float("nan")},
            {"strategy_action": "WAIT_FOR_FRESH_PRICES"},
            {"strategy_action": "AVOID"},
            {"hulk_decision_tier": "CAUTION"},
        ]:
            with self.subTest(change=change):
                self.assertFalse(v2.authentic_current_market_ready(pd.Series(base|change)))

    def test_actual_week5_private_state_no_fake_recommendation(self):
        current = v2.current_payload()
        self.assertEqual(current["pool_current_week"],5)
        self.assertTrue(current["rule_confirmed"])
        self.assertEqual(current["required_picks"],1)
        self.assertEqual(current["recommendation_status"],"WAIT_FOR_FRESH_VERIFIED_MARKET_QUOTES")
        self.assertEqual(current["shadow_recommendation"],[])
        self.assertEqual(current["safest_market_baseline"],[])
        self.assertTrue(current["candidates"])
        self.assertTrue(all(row["eligible_for_shadow"] is False for row in current["candidates"]))
        self.assertTrue(all(row["spread"] is None for row in current["candidates"]))

    def test_public_week5_has_no_private_entry_or_stale_primary_spread(self):
        current = v2.current_payload()
        public = v2.public_current_payload(current)
        self.assertEqual(public["mode"],"GENERIC_RESEARCH_ONLY")
        self.assertEqual(public["recommendation_status"],"PERSONAL_CONTEXT_REQUIRED")
        self.assertNotIn("used_teams",public)
        self.assertNotIn("active_entry",public)
        self.assertEqual(public["shadow_recommendation"],[])
        self.assertTrue(all(row["eligible_for_shadow"] is False for row in public["candidates"]))
        self.assertTrue(all(row["spread"] is None for row in public["candidates"]))

    def test_future_week_double_picks_preserved(self):
        for week, expected in [(5,1),(6,2),(9,2),(12,2)]:
            with self.subTest(week=week):
                _,got,_,confirmed=v2.rule_state({},week)
                self.assertTrue(confirmed)
                self.assertEqual(got,expected)

if __name__=="__main__":
    unittest.main()
