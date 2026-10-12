"""Challenger folds cannot leak players from the same game into training."""
import unittest
from unittest.mock import patch
from intelligence_warehouse.betting_v2 import build_prop_v2 as base
from intelligence_warehouse.betting_v2 import build_prop_v2_challengers as challenger
from tests.test_prop_v2_game_blocked_validation import sample

class ChallengerGameSplitTests(unittest.TestCase):
    def test_fifteen_games_cannot_support_challenger(self):
        frame=sample(games=15)
        result=challenger.nested_lane(frame,base.LANES['NFL_PROP'])
        self.assertEqual(result['status'],'INSUFFICIENT_INDEPENDENT_GAMES')
        self.assertEqual(result['independent_game_blocks'],15)
    def test_challenger_uses_blocked_folds(self):
        frame=sample(games=40)
        for name in base.LANES['NFL_PROP']['features']:
            if name not in frame:frame[name]=0.1
        original=base.game_blocked_rolling_origin_folds
        observed=[]
        def observe(f):
            folds=original(f)
            for train,test in folds:
                self.assertTrue(set(train.block_key).isdisjoint(set(test.block_key)))
            observed.extend(folds)
            return folds
        with patch.object(challenger.prop,'game_blocked_rolling_origin_folds',side_effect=observe):
            result=challenger.nested_lane(frame,base.LANES['NFL_PROP'])
        self.assertTrue(observed)
        self.assertIn(result['status'],('KEEP_CURRENT_V2','CHALLENGER_REVIEW_CANDIDATE','PROMISING_NOT_PROVEN','IMPROVES_FEATURE_MODEL_BUT_STILL_LOSES_TO_MARKET'))

class InnerFeatureGameSplitTests(unittest.TestCase):
    def test_inner_selection_never_shares_games_or_violates_embargo(self):
        frame=sample(games=40)
        for name in base.LANES['NFL_PROP']['features']:
            if name not in frame:frame[name]=0.1
        seen=[]
        original=base.matrix
        def inspect(part,features,**kwargs):
            seen.append((set(part.block_key),part.event_start.max(),part.time.min()))
            return original(part,features,**kwargs)
        with patch.object(challenger.prop,'matrix',side_effect=inspect):
            challenger.inner_choice(frame,list(base.LANES['NFL_PROP']['features']))
        self.assertGreaterEqual(len(seen),2)
        self.assertTrue(seen[0][0].isdisjoint(seen[1][0]))
        self.assertLessEqual(seen[0][1]+base.pd.Timedelta(hours=24),seen[1][2])
