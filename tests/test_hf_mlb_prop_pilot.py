"""External historical odds are research only, never retroactive forward picks."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
import pandas as pd

from intelligence_warehouse.betting_v2.hf_mlb_prop_pilot import (
    audit_rows, chronological_split, clean_player_name, fair_grade_from_stat,
    market_implied_probability, summarize_pilot,
)


def official(game_pk=823885, player='Eugenio Suárez', stat=3.0, game_time='2026-04-08T22:40:00Z', **fields):
    return dict(game_pk=game_pk, player=player, group='HITTING', game_date=game_time,
                game_type='R', status='Final', team='Arizona Diamondbacks',
                total_bases=stat, hits=2.0, home_runs=0.0, rbi=1.0,
                walks=0.0, strikeouts=0.0, **fields)


def source(**overrides):
    raw=dict(game_id='m~one',start_time='2026-04-08T22:41:00',ts='2026-04-08T17:20:00',
             player='eugenio suarez', market='player bases',line=2.5,side='over',
             book='bet365',odds=1.85,result=3.0,won=True)
    raw.update(overrides)
    return raw


class HuggingFaceMLBHistoricalPilotTests(unittest.TestCase):
    def test_valid_outcome_is_cross_checked_with_official_player_stats_and_kickoff(self):
        rows=audit_rows([source()],pd.DataFrame([official()]))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['status'],'VERIFIED_HISTORICAL')
        self.assertEqual(rows[0]['official_game_pk'],823885)
        self.assertEqual(rows[0]['kickoff_difference_minutes'],1.0)
        self.assertTrue(rows[0]['timestamp_before_official_start'])
        self.assertEqual(clean_player_name('Eugenio Suárez'),'eugeniosuarez')

    def test_conflicting_vendor_result_is_rejected_not_trained(self):
        rows=audit_rows([source(result=2.0,won=False)],pd.DataFrame([official()]))
        self.assertEqual(rows[0]['status'],'RESULT_DISAGREES_WITH_OFFICIAL')

    def test_vendor_win_flag_must_match_stat_and_line(self):
        rows=audit_rows([source(won=False)],pd.DataFrame([official()]))
        self.assertEqual(rows[0]['status'],'WON_FLAG_DISAGREES_WITH_OFFICIAL')

    def test_missing_outcomes_and_post_start_quotes_not_validated(self):
        hist=pd.DataFrame([official()])
        self.assertEqual(audit_rows([source(won=None,result=None)],hist)[0]['status'],'MISSING_VENDOR_OUTCOME')
        self.assertEqual(audit_rows([source(ts='2026-04-08T22:40:00')],hist)[0]['status'],'NOT_PREGAME_AT_OFFICIAL_START')
        self.assertEqual(audit_rows([source(ts='2026-04-08T22:41:00')],hist)[0]['status'],'NOT_PREGAME_AT_PROVIDER_START')

    def test_wrong_kickoff_and_ambiguous_official_games_fail_closed(self):
        self.assertEqual(audit_rows([source(start_time='2026-04-08T21:00:00')],pd.DataFrame([official()]))[0]['status'],'NO_UNIQUE_PLAYER_GAME_MATCH')
        hist=pd.DataFrame([official(game_pk=1),official(game_pk=2,game_time='2026-04-08T22:41:00Z')])
        self.assertEqual(audit_rows([source()],hist)[0]['status'],'NO_UNIQUE_PLAYER_GAME_MATCH')

    def test_only_supported_proposition_semantics_allowed(self):
        self.assertEqual(audit_rows([source(market='unverified exotic prop')],pd.DataFrame([official()]))[0]['status'],'UNSUPPORTED_MARKET')
        self.assertEqual(fair_grade_from_stat('under',1.5,2.0),False)
        self.assertIsNone(fair_grade_from_stat('over',2.0,2.0))
        self.assertIsNone(market_implied_probability(0.99))

    def test_duplicate_snapshots_cannot_fake_independent_games(self):
        hist=pd.DataFrame([official()])
        data=audit_rows([source(),source(ts='2026-04-08T17:30:00')],hist)
        summary=summarize_pilot(data)
        self.assertEqual(summary['verified_records'],2)
        self.assertEqual(summary['verified_independent_games'],1)
        self.assertFalse(summary['minimum_25_distinct_games_met'])

    def test_chronological_holdout_never_leaks_a_game_across_splits(self):
        rows=[]
        for i in range(30):
            dt=datetime(2026,4,1,tzinfo=timezone.utc)+timedelta(days=i)
            rows.append(dict(status='VERIFIED_HISTORICAL',official_game_pk=i+1,
                official_start=dt.isoformat(),provider_game_id=f'm~{i}',market_implied_probability=0.58,verified_win=bool(i%2)))
        train,holdout=chronological_split(rows,train_fraction=0.6)
        self.assertEqual((len(train),len(holdout)),(18,12))
        self.assertTrue(set(x['official_game_pk'] for x in train).isdisjoint(x['official_game_pk'] for x in holdout))
        self.assertLess(max(x['official_start'] for x in train),min(x['official_start'] for x in holdout))


if __name__ == '__main__':
    unittest.main()
