"""Pure original-source receipt tests. No API calls, player data, or wagers."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import unittest
from intelligence_warehouse.brain_performance import publish_nfl_frozen_game_intelligence as p

class TestOriginalFrozenNFLResearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=[json.loads(line) for line in p.SOURCE.read_text().splitlines() if line.strip()]
        cls.games=json.loads(p.SCHEDULE.read_text())
        cls.byid={str(g['event_id']):g for g in (cls.games['games']+cls.games['next_games'])}
        cls.source_sha=p.sha(p.SOURCE)

    def test_original_13_independent_forecasts_are_unchanged_and_not_bets(self):
        self.assertEqual(len(self.raw),13)
        self.assertEqual(len({row['official_espn_event_id'] for row in self.raw}),13)
        self.assertEqual(self.source_sha,'b74351d24c0cf591624a74c8dc2d33f84ea34f1374c65d782219bc5d95b60602')
        for row in self.raw:
            self.assertTrue(row['research_only'])
            self.assertFalse(row['betting_play_approved'])
            self.assertFalse(row['sportsbook_wager_created'])
            self.assertFalse(row['predicted_market_advantage_proven'])
            self.assertTrue(row['historic_2025_diagnostic_slightly_worse_than_raw_market'])

    def test_model_pred_reference_source_timestamp_and_game_start_match(self):
        for row in self.raw:
            result=p.score_model_source_row(row,self.byid[str(row['official_espn_event_id'])])
            self.assertEqual(result['event_id'],str(row['official_espn_event_id']))
            self.assertEqual(result['book_name'],'Pinnacle')
            self.assertFalse(result['approved_play'])
            self.assertAlmostEqual(result['forecast_home_pct']+result['forecast_away_pct'],100,1)
            self.assertAlmostEqual(result['book_market_fair_home_pct']+result['book_market_fair_away_pct'],100,1)
            self.assertFalse(result['actual_sportsbook_executable_current_price_verified'])
            self.assertTrue(result['model_uses_market_input'])

    def test_project_preserves_original_SHA_and_reports_no_proven_edge(self):
        at=datetime(2026,10,9,18,30,tzinfo=timezone.utc)
        r=p.project(now=at)
        self.assertEqual(r['source_original_nine_feature_ledger_sha256'],self.source_sha)
        self.assertEqual(len(r['rows']),13)
        self.assertEqual(len(set(x['event_id'] for x in r['rows'])),13)
        self.assertEqual(r['current_original_future_games'],13)
        self.assertFalse(r['historic_2025_holdout_model_better_than_market'])
        self.assertFalse(r['wagers_created_or_bets_promoted'])
        self.assertFalse(r['real_book_executability_verified'])
        self.assertEqual({x['source_model_version'] for x in r['rows']},{p.EXPECTED_MODEL})

    def test_official_game_identity_mismatch_fails_closed(self):
        row=self.raw[0];fixture=deepcopy(self.byid[str(row['official_espn_event_id'])])
        fixture['home_abbr']='KC'
        with self.assertRaisesRegex(ValueError,'team identity'):p.score_model_source_row(row,fixture)

    def test_official_kickoff_mismatch_fails_closed(self):
        row=self.raw[0];fixture=deepcopy(self.byid[str(row['official_espn_event_id'])])
        fixture['start_time']='2026-10-11T14:00:00Z'
        with self.assertRaisesRegex(ValueError,'kickoff mismatch'):p.score_model_source_row(row,fixture)

    def test_future_or_unsafe_book_quote_cannot_be_promoted(self):
        row=deepcopy(self.raw[0])
        row['source_qualified_book_quote_updated_at_utc']='2026-10-12T17:00:00Z'
        with self.assertRaisesRegex(ValueError,'time violates'):p.score_model_source_row(row,self.byid[str(row['official_espn_event_id'])])
        row=deepcopy(self.raw[0]);row['predicted_market_advantage_proven']=True
        with self.assertRaisesRegex(ValueError,'non-play guard'):p.score_model_source_row(row,self.byid[str(row['official_espn_event_id'])])

    def test_invalid_prices_or_fake_probabilities_fail(self):
        row=deepcopy(self.raw[0]);row['original_same_book_american_home_moneyline']=-9
        with self.assertRaisesRegex(ValueError,'Invalid bookmaker'):p.score_model_source_row(row,self.byid[str(row['official_espn_event_id'])])
        row=deepcopy(self.raw[0]);row['nine_feature_score_form_home_win_prob']=1.2
        with self.assertRaisesRegex(ValueError,'Bad source-model'):p.score_model_source_row(row,self.byid[str(row['official_espn_event_id'])])

    def test_previously_started_games_disappear_not_archive_rewritten(self):
        after=datetime(2026,10,12,3,1,tzinfo=timezone.utc)
        r=p.project(now=after)
        self.assertEqual(r['rows'],[])
        self.assertEqual(r['source_original_nine_feature_ledger_sha256'],self.source_sha)
        self.assertEqual(p.sha(p.SOURCE),self.source_sha)


if __name__=='__main__':unittest.main()
