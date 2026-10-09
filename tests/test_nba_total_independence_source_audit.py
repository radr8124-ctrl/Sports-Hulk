"""NBA preseason source truth, timing holds and correlated quote repeat checks."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

import pandas as pd

from intelligence_warehouse.brain_performance import audit_nba_total_independence as a


def official(*,start='2026-10-05T23:00:00Z',home='ATL',away='MEM',h=123,vis=132):
    return pd.DataFrame([{
        "event_id":401800001,"start":start,"season":2027,"season_type":1,
        "home_team":home,"away_team":away,
        "home_score":h,"away_score":vis,"completed":True,
    }])


def quote(*,line=227.5,side='OVER',grade='WIN',event_start='2026-10-05T23:00:00Z',
          captured='2026-10-05T12:59:53+00:00',price=-110,source=None):
    return {
        "forward_key":source or f'BETTING_V2_ALL_MARKETS_2026_10_05|NBA|2026-10-05|MEM|ATL|TOTAL|{side}|{line}',
        "model_version":"BETTING_V2_ALL_MARKETS_2026_10_05",
        "sport":"NBA","lane_key":"NBA_TOTAL","game_key":"2026-10-05|MEM|ATL",
        "market":"TOTAL","selection_key":side,"selection":side,"line":line,
        "grade":grade,"entry_american_odds":price,
        "entry_market_reference_probability_pct":55.,
        "entry_v2_probability_pct":55.,
        "entry_probability_source":"MARKET_REFERENCE_INSUFFICIENT_HISTORY",
        "event_start":event_start,"captured_at":captured,
        "live_rule_changed":False,"proof_lane_key":None,"competition_regime":None,
    }


class TestNBASourceIndependence(unittest.TestCase):
    def test_provenance_based_on_true_2027_preseason_final(self):
        games=a.official_nba_games(official())
        rows,n,held=a.attest_entries([quote()],games)
        self.assertEqual(len(rows),1)
        self.assertEqual(n,1)
        self.assertEqual(held,[])
        self.assertEqual(rows[0]['_source_official_points_total'],255)
        self.assertEqual(rows[0]['_source_official_pregame_regime'],'PRESEASON')

    def test_source_15_minute_stale_start_held_even_if_result_wins(self):
        games=a.official_nba_games(official(start='2026-10-05T23:15:00Z'))
        rows,n,held=a.attest_entries([quote()],games)
        self.assertEqual(len(rows),0)
        self.assertEqual(n,0)
        self.assertEqual(held[0]['original_start_to_ESPN_start_minutes'],15.)
        self.assertEqual(held[0]['reason'],'NBA_BOOK_EVENT_START_DIFFERS_FROM_OFFICIAL_ESPN_FINAL')

    def test_one_wrong_original_market_grade_cannot_enter_verified_set(self):
        with self.assertRaisesRegex(ValueError,'NBA_ORIGINAL_FORWARD_GRADE_CONTRADICTS'):
            a.attest_entries([quote(grade='LOSS')],a.official_nba_games(official()))

    def test_late_after_tipoff_quote_cannot_be_counted(self):
        with self.assertRaisesRegex(ValueError,'NBA_SOURCE_QUOTE_CAPTURE_AFTER_OFFICIAL_KICKOFF'):
            a.attest_entries([quote(captured='2026-10-06T00:00:00+00:00')],
                             a.official_nba_games(official()))

    def test_missing_or_duplicate_espn_event_id_fails(self):
        dupe=pd.concat([official(),official()],ignore_index=True)
        with self.assertRaisesRegex(ValueError,'DUPLICATED_ESPN_PRESEASON_FINAL'):
            a.official_nba_games(dupe)

    def test_duplicate_market_regime_keys_use_earliest_before_outcome(self):
        games=a.official_nba_games(official())
        early=quote(price=-135,captured='2026-10-05T11:00:00+00:00')
        late=quote(source='BETTING_V2_ALL_MARKETS_2026_10_05|COMPETITION_REGIME_V1|PRESEASON|PRESEASON|NBA|2026-10-05|MEM|ATL|TOTAL|OVER|227.5000',
                   price=-110,captured='2026-10-05T21:00:00+00:00')
        rows,n,held=a.attest_entries([late,early],games)
        selected=a.dedup_first_market_line(rows)
        self.assertEqual(len(selected),1)
        self.assertEqual(selected[0]['entry_american_odds'],-135)
        self.assertEqual(a.metrics(selected)['wins'],1)

    def test_multiple_alternate_lines_same_game_are_not_independent_games(self):
        games=a.official_nba_games(official())
        rows,_,_=a.attest_entries([quote(line=227.5),quote(line=228.5)],games)
        self.assertEqual(a.metrics(rows)['independent_official_game_blocks'],1)
        one=a.one_first_per_game(rows)
        self.assertEqual(len(one),1)

    def test_original_price_format_rejection(self):
        with self.assertRaisesRegex(ValueError,'SOURCE_ODDS_NOT_REALISTIC'):
            a.prices(-10.)

    def test_original_first_payload_hash_freeze_is_used(self):
        spec=json.loads(a.SPEC.read_text())
        spec['source_input_sha256']['original_game_forward_ledger']='0'*64
        with self.assertRaisesRegex(ValueError,'ORIGINAL_PRE_REGISTERED_FORWARD_SOURCE_CHANGED'):
            a.evaluate(spec,official())

    def test_source_recomputed_from_frozen_receipt_has_official_time_holds(self):
        saved=json.loads(a.OUT.read_text())
        self.assertEqual(saved['original_all_alternative_quotes_as_original_ledger_report_NOT_fully_source_time_verified']['original_ledger_quote_rows'],106)
        self.assertEqual(saved['original_ledger_grade_rows_held_for_official_start_disagreement'],7)
        self.assertEqual(saved['official_start_conflict_minutes'],[15.0])
        self.assertEqual(saved['exact_quote_grade_dupe_market_identities'],8)
        strict=saved['source_de_duplicated_exact_same_game_market_side_line_first_quote']
        self.assertEqual((strict['original_source_line_records'],strict['independent_official_game_blocks']), (91,19))
        self.assertEqual((strict['wins'],strict['losses']),(69,22))
        lo,hi=strict['independent_game_bootstrap95_source_price_roi_interval_pct']
        self.assertLess(lo,0)
        self.assertGreater(hi,0)
        self.assertFalse(saved['model_brier_better_than_book'])
        self.assertEqual(saved['forward_regular_season_results_included'],0)

    def test_retrospective_win_rate_cannot_prove_actual_profit(self):
        r=json.loads(a.OUT.read_text())
        self.assertTrue(r['research_only_not_true_executable_ROI'])
        self.assertFalse(r['probability_market_edge_statistically_proven'])
        self.assertFalse(r['qualified_as_money_making_invention'])
        self.assertFalse(r['real_sportsbook_executable_market_price_verified'])
        self.assertFalse(r['new_model_training_or_live_betting_picks_changed'])


if __name__=='__main__':
    unittest.main()
