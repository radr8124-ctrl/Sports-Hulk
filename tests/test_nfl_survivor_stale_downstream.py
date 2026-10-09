"""Stop stale primary sportsbook odds leaking into deeper Survivor strategy."""
from __future__ import annotations
from pathlib import Path
from copy import deepcopy
import json
import unittest
import pandas as pd

from nfl_live.decision.nfl_market_primary_freshness import gate_survivor_stale_primary_source

ROOT=Path(__file__).resolve().parents[1]

class SourceTimeVerifiedSurvivorStrategyGates(unittest.TestCase):
    def test_market_source_stale_context_not_elite_market(self):
        src=pd.DataFrame([
          {'primary_market_fresh_enough_for_live_decision':False,
           'survivor_grade':'PRICE STALE',
           'survivor_win_prob':.81,
           'hulk_context_score':87.5,
           'hulk_context_flags':'ELITE_MARKET_FAVORITE|HOME|TD_PLUS_FAVORITE|STRONG_RECENT_RECORD',
           'market_status':'STALE_PRIMARY_MARKET'},
        ])
        result=gate_survivor_stale_primary_source(src)
        self.assertTrue(pd.isna(result['hulk_context_score'].iloc[0]))
        self.assertEqual(result['historical_hulk_context_score_unverified_old_primary_market'].iloc[0],87.5)
        self.assertEqual(result['hulk_context_flags'].iloc[0],'HOME|STRONG_RECENT_RECORD|PRIMARY_MARKET_PRICE_STALE')
        self.assertEqual(result['survivor_grade'].iloc[0],'PRICE STALE')
        self.assertTrue(result['requires_new_source_time_verified_book_quote'].iloc[0])

    def test_downstream_decision_not_qualified_viable_strong_or_top_tier(self):
        src=pd.DataFrame([
          {'primary_market_fresh_enough_for_live_decision':False,
           'market_prob_pct':81.0,'hulk_decision_tier':'TOP_TIER',
           'hulk_disagreement':'MARKET_HULK_AGREE',
           'positive_signals':'ELITE_MARKET|BIG_SPREAD|HOME_FIELD',
           'risk_signals':'ROAD_FAVORITE'},
        ])
        result=gate_survivor_stale_primary_source(src)
        self.assertEqual(result['hulk_decision_tier'].iloc[0],'WAIT_FOR_FRESH_PRICES')
        self.assertEqual(result['hulk_disagreement'].iloc[0],'MARKET_SOURCE_STALE')
        self.assertEqual(result['risk_signals'].iloc[0],'ROAD_FAVORITE|STALE_PRIMARY_MARKET')
        self.assertEqual(result['positive_signals'].iloc[0],'HOME_FIELD')
        self.assertTrue(pd.isna(result['market_prob_pct'].iloc[0]))
        self.assertEqual(result['historical_market_prob_pct_from_stale_source'].iloc[0],81.0)

    def test_future_value_strategy_must_not_claim_viable_from_stale_old_price(self):
        source=pd.DataFrame([
          {'primary_market_fresh_enough_for_live_decision':False,
           'market_prob_pct':80.0,'strategy_index':75.,
           'strategy_action':'VIABLE','future_value_index':40,
           'survivor_team':'Cincinnati Bengals'},
        ])
        out=gate_survivor_stale_primary_source(source)
        self.assertEqual(out['strategy_action'].iloc[0],'WAIT_FOR_FRESH_PRICES')
        self.assertTrue(pd.isna(out['strategy_index'].iloc[0]))
        self.assertTrue(pd.isna(out['market_prob_pct'].iloc[0]))
        self.assertEqual(out['historical_market_prob_pct_from_stale_source'].iloc[0],80.)
        self.assertEqual(out['future_value_index'].iloc[0],40)

    def test_real_verified_fresh_remains_original_qualified_classification(self):
        source=pd.DataFrame([
          {'primary_market_fresh_enough_for_live_decision':True,
           'hulk_context_score':78.2,'hulk_decision_tier':'STRONG',
           'strategy_action':'USE_NOW_VALUE',
           'market_prob_pct':75.,'survivor_grade':'A',
           'hulk_context_flags':'STRONG_MARKET_FAVORITE|HOME'},
        ])
        out=gate_survivor_stale_primary_source(source)
        self.assertEqual(out['hulk_context_score'].iloc[0],78.2)
        self.assertEqual(out['hulk_decision_tier'].iloc[0],'STRONG')
        self.assertEqual(out['strategy_action'].iloc[0],'USE_NOW_VALUE')
        self.assertEqual(out['survivor_grade'].iloc[0],'A')
        self.assertFalse(out['requires_new_source_time_verified_book_quote'].iloc[0])

    def test_unknown_or_missing_quote_source_fails_closed(self):
        source=pd.DataFrame([{'strategy_action':'STRONG_OPTION','market_prob_pct':70}])
        with self.assertRaisesRegex(ValueError,'source.*freshness|freshness.*required'):
            gate_survivor_stale_primary_source(source)

    def test_actual_survivor_context_decision_and_future_value_outputs_obey_source_gate(self):
        for rel in [
            'nfl_live/derived/NFL_SURVIVOR_HULK_CONTEXT.csv',
            'nfl_live/derived/NFL_SURVIVOR_HULK_DECISION.csv',
            'nfl_live/derived/NFL_SURVIVOR_HULK_STRATEGY.csv',
        ]:
            data=pd.read_csv(ROOT/rel,low_memory=False)
            stale=~data.primary_market_fresh_enough_for_live_decision.astype(str).str.lower().eq('true')
            self.assertEqual(len(data),14)
            if 'hulk_context_score' in data:
                self.assertTrue(data.loc[stale,'hulk_context_score'].isna().all())
            if 'market_prob_pct' in data:
                self.assertTrue(data.loc[stale,'market_prob_pct'].isna().all())
            if 'hulk_decision_tier' in data:
                self.assertTrue(data.loc[stale,'hulk_decision_tier'].eq('WAIT_FOR_FRESH_PRICES').all())
            if 'strategy_action' in data:
                self.assertTrue(data.loc[stale,'strategy_action'].eq('WAIT_FOR_FRESH_PRICES').all())

    def test_saved_original_survivor_entry_teams_survive_every_source_age_gate(self):
        previous=ROOT/'.deploy_backups/nfl_survivor_deep_strategy_source_price_age_Before_20261009T004506Z/nfl_live/derived/SURVIVOR_ENTRIES.json'
        current=ROOT/'nfl_live/derived/SURVIVOR_ENTRIES.json'
        if not previous.exists():
            self.skipTest('Private original pre-edit VPS backup is unavailable on this checkout')
        # Hourly official-score refresh updates last_checked_at and rollover
        # timestamps by design. The user's actual saved Survivor entries,
        # teams, picks, weeks and win/loss results must remain IDENTICAL.
        volatile={'last_checked_at','last_rollover_at','last_result_refresh_at'}
        def core(x):
            if isinstance(x,dict):
                return {k:core(v) for k,v in x.items() if k not in volatile}
            if isinstance(x,list):
                return [core(v) for v in x]
            return x
        self.assertEqual(core(json.loads(previous.read_text())),
                         core(json.loads(current.read_text())))

    def test_deep_survivor_research_source_assets_registered_for_replay_and_backup(self):
        catalog=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        protected=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        for rel in [
            'nfl_live/derived/SURVIVOR_ENTRIES.json',
            'nfl_live/derived/NFL_SURVIVOR_BOARD.csv',
            'nfl_live/derived/NFL_SURVIVOR_HULK_CONTEXT.csv',
            'nfl_live/derived/NFL_SURVIVOR_HULK_DECISION.csv',
            'nfl_live/derived/NFL_SURVIVOR_HULK_STRATEGY.csv',
            'nfl_live/build_hulk_survivor_context.py',
            'nfl_live/build_hulk_survivor_decision.py',
            'nfl_live/build_survivor_future_value.py',
            'tests/test_nfl_survivor_stale_downstream.py',
        ]:
            with self.subTest(path=rel):
                self.assertEqual(len([x for x in catalog['files'] if x['path']==rel]),1)
                self.assertIn(f'copy_if_exists "{rel}"',protected)

    def test_actual_hulk_survivor_pipeline_calls_guard_before_each_output(self):
        for rel,target in [
            ('nfl_live/build_hulk_survivor_context.py','NFL_SURVIVOR_HULK_CONTEXT.csv'),
            ('nfl_live/build_hulk_survivor_decision.py','NFL_SURVIVOR_HULK_DECISION.csv'),
            ('nfl_live/build_survivor_future_value.py','NFL_SURVIVOR_HULK_STRATEGY.csv'),
        ]:
            with self.subTest(source=rel):
                s=(ROOT/rel).read_text()
                self.assertIn('from nfl_live.decision.nfl_market_primary_freshness import gate_survivor_stale_primary_source',s)
                self.assertEqual(s.count('result = gate_survivor_stale_primary_source(result)'),1)
                self.assertLess(s.index('result = gate_survivor_stale_primary_source(result)'),s.index('result.to_csv('))
                self.assertIn(target,s)
                self.assertNotIn('SURVIVOR_ENTRIES.json',s)

if __name__=='__main__':
    unittest.main()
