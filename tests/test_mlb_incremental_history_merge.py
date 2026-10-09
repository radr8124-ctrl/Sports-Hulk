"""Late official MLB postseason games supplement legacy source with no double count."""
from __future__ import annotations
import unittest
import pandas as pd

from intelligence_warehouse.historical_recovery.mlb_incremental_history_merge import (
    merge_verified_recent_hitter_history,
)


def legacy():
    return pd.DataFrame([
        {'game_pk':10,'player_id':501,'season':2026,'official_date':'2026-09-29',
         'game_date':'2026-09-29T21:00:00Z','game_type':'R','status':'Final','group':'HITTING',
         'hits':2.,'walks':1.,'plate_appearances':4.,'stolen_bases':0.}
    ])


def incremental():
    return pd.DataFrame([
        {'gamePk':10,'player_id':501,'season':2026,'officialDate':'2026-09-29','group':'HITTING',
         'hits':2.,'walks':1.,'plate_appearances':4.,'stolen_bases':0.},
        {'gamePk':20,'player_id':501,'season':2026,'officialDate':'2026-10-07','group':'HITTING',
         'hits':3.,'walks':2.,'plate_appearances':5.,'stolen_bases':1.},
    ])


def master():
    return pd.DataFrame([
        {'gamePk':10,'officialDate':'2026-09-29','gameDate':'2026-09-29T21:00:00Z',
         'gameType':'R','status':'Final'},
        {'gamePk':20,'officialDate':'2026-10-07','gameDate':'2026-10-07T18:05:00Z',
         'gameType':'D','status':'Final'},
        {'gamePk':30,'officialDate':'2026-10-08','gameDate':'2026-10-09T00:00:00Z',
         'gameType':'D','status':'Scheduled'},
    ])


class MLBHistoricalIncrementalMergeTests(unittest.TestCase):
    def test_current_postseason_pitcher_hitter_results_only_when_official_final(self):
        merged,proof=merge_verified_recent_hitter_history(legacy(),incremental(),master(),target_season=2026)
        self.assertEqual(len(merged),2)
        self.assertEqual(proof['overlap_source_player_game_rows'],1)
        self.assertEqual(proof['new_incremental_official_player_game_rows'],1)
        self.assertEqual(proof['source_stat_conflict_count'],0)
        self.assertEqual(proof['latest_official_completed_date'],'2026-10-07')
        p=merged.set_index('game_pk')
        self.assertEqual(p.loc[20,'game_type'],'D')
        self.assertEqual(p.loc[20,'hits'],3.)
        self.assertEqual(p.loc[20,'game_date'],'2026-10-07T18:05:00Z')
        self.assertTrue(p.loc[20,'source_verified_before_quote_required'])
        self.assertEqual(p.loc[10,'source_history_origin'],'LEGACY_OFFICIAL_FINAL_BOXSCORE')

    def test_conflicting_overlap_is_blocked_not_silently_overwritten(self):
        older=legacy();recent=incremental()
        recent.loc[recent.gamePk.eq(10),'hits']=15
        with self.assertRaisesRegex(ValueError,'conflicting'):
            merge_verified_recent_hitter_history(older,recent,master())

    def test_scheduled_game_cannot_supply_prior_postgame_stats(self):
        recent=incremental()
        extra=recent.iloc[-1:].copy()
        extra['gamePk']=30
        extra['officialDate']='2026-10-08'
        extra['hits']=99.
        merged,proof=merge_verified_recent_hitter_history(legacy(),pd.concat([recent,extra]),master())
        self.assertEqual(len(merged),2)
        self.assertEqual(proof['non_final_incremental_rows_refused'],1)
        self.assertNotIn(30,set(merged.game_pk))

    def test_missing_or_wrong_fixture_crosswalk_is_excluded(self):
        recent=incremental()
        bad=recent.iloc[-1:].copy()
        bad.loc[:,'gamePk']=999
        merged,proof=merge_verified_recent_hitter_history(legacy(),pd.concat([recent,bad]),master())
        self.assertEqual(len(merged),2)
        self.assertEqual(proof['missing_official_fixture_rows_refused'],1)
        bad2=incremental()
        bad2.loc[bad2.gamePk.eq(20),'officialDate']='2026-10-05'
        with self.assertRaisesRegex(ValueError,'official date mismatch'):
            merge_verified_recent_hitter_history(legacy(),bad2,master())

    def test_duplicate_source_game_ids_fail_closed(self):
        m=pd.concat([master(),master().iloc[:1]],ignore_index=True)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            merge_verified_recent_hitter_history(legacy(),incremental(),m)
        recent=pd.concat([incremental(),incremental().iloc[:1]],ignore_index=True)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            merge_verified_recent_hitter_history(legacy(),recent,master())

if __name__=='__main__':unittest.main()
