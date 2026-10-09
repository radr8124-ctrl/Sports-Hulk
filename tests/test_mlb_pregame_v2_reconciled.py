"""V2 can capture official-verified completed postseason form, never rewrite V1."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
import json
import tempfile
import unittest

import pandas as pd

from tests.test_mlb_live_research_feature_freeze import (
    NOW, START, source, prior_year_speed, past_player_games,
)
from intelligence_warehouse.historical_recovery.mlb_live_research_feature_freeze import make_live_features
from intelligence_warehouse.historical_recovery.mlb_live_research_feature_freeze_v2 import (
    make_reconciled_pregame_v2,
    append_v2_only,
    freeze_v2_cycle,
)

def official_prior():
    regular=past_player_games()
    regular['source_history_origin']='LEGACY_OFFICIAL_FINAL_BOXSCORE'
    regular['source_verified_before_quote_required']=True
    game=regular.iloc[0:1].copy()
    game['player_id']=501
    game['game_pk']=314159
    game['official_date']='2026-10-07'
    game['game_date']='2026-10-07T14:30:00Z'
    game['game_type']='D'
    game['hits']=3.
    game['walks']=4.
    game['plate_appearances']=5.
    game['source_history_origin']='INCREMENTAL_OFFICIAL_FINAL_POSTSEASON_CROSSCHECKED_WITH_GAME_MASTER'
    game['source_verified_before_quote_required']=True
    return pd.concat([regular,game],ignore_index=True)


class NHLMLBReconciledV2Tests(unittest.TestCase):
    def test_v1_legacy_does_not_count_postseason_but_v2_verified_does(self):
        h=official_prior()
        v1=make_live_features(source(),h,prior_year_speed(),now=NOW)
        v2=make_reconciled_pregame_v2(source(),h,prior_year_speed(),now=NOW,
                                    current_source_checksums={'legacy':'a'*64,'incremental':'b'*64,'master':'c'*64},
                                    source_last_verified_date='2026-10-07')
        self.assertEqual(len(v1),9)
        self.assertEqual(len(v2),9)
        base=next(r for r in v1 if r['player_id']==501)
        upgraded=next(r for r in v2 if r['player_id']==501)
        self.assertGreater(upgraded['prior_games_available'],base['prior_games_available'])
        self.assertEqual(upgraded['last_prior_date'],'2026-10-07')
        self.assertEqual(upgraded['source_history_revision'],'OFFICIAL_FINAL_REGULAR_AND_POSTSEASON_V2')
        self.assertFalse(upgraded['betting_prediction_written'])
        self.assertFalse(upgraded['live_play_approved'])
        self.assertTrue(upgraded['postseason_final_games_allowed_only_from_verified_master'])

    def test_forged_postseason_without_verified_source_flag_is_rejected(self):
        h=official_prior()
        h.loc[h.game_pk.eq(314159),'source_verified_before_quote_required']=False
        with self.assertRaisesRegex(ValueError,'verification'):
            make_reconciled_pregame_v2(source(),h,prior_year_speed(),now=NOW,
                                     current_source_checksums={'legacy':'a'*64},
                                     source_last_verified_date='2026-10-07')

    def test_future_or_same_day_postseason_result_is_excluded(self):
        h=official_prior()
        h.loc[h.game_pk.eq(314159),'official_date']='2026-10-08'
        h.loc[h.game_pk.eq(314159),'hits']=99999
        v2=make_reconciled_pregame_v2(source(),h,prior_year_speed(),now=NOW,
                                     current_source_checksums={'legacy':'a'*64},
                                     source_last_verified_date='2026-10-07')
        first=next(r for r in v2 if r['player_id']==501)
        self.assertLess(first['prior_last5_hits_avg'],99999)
        self.assertNotEqual(first['last_prior_date'],'2026-10-08')

    def test_v2_append_only_preserves_original_first_snapshot_and_independent_game_ids(self):
        with tempfile.TemporaryDirectory() as root:
            ledger=Path(root)/'V2.jsonl'
            h=official_prior()
            records=make_reconciled_pregame_v2(source(),h,prior_year_speed(),now=NOW,
                                     current_source_checksums={'legacy':'a'*64},
                                     source_last_verified_date='2026-10-07')
            self.assertEqual(append_v2_only(ledger,records),9)
            content=ledger.read_bytes()
            self.assertEqual(append_v2_only(ledger,records),0)
            self.assertEqual(ledger.read_bytes(),content)
            self.assertEqual(len({(r['game_pk'],r['player_id']) for r in records}),9)

    def test_frozen_version_is_distinct_and_never_silent_v1_overwrite(self):
        from intelligence_warehouse.historical_recovery import mlb_live_research_feature_freeze as legacy
        from intelligence_warehouse.historical_recovery import mlb_live_research_feature_freeze_v2 as v2
        self.assertNotEqual(v2.OUTPUT,legacy.OUTPUT)
        self.assertNotEqual(v2.SCHEMA,legacy.SCHEMA)
        self.assertNotEqual(v2.SUMMARY,legacy.SUMMARY)

if __name__=='__main__':unittest.main()

class V2NoRedundantRecomputeTests(unittest.TestCase):
    def test_v2_existing_frozen_player_ids_skip_the_expensive_official_history_merge(self):
        from unittest.mock import patch
        from tests.test_mlb_pregame_v2_reconciled import official_prior
        with tempfile.TemporaryDirectory() as temp:
            source_file=Path(temp)/'MLB_SOURCE.jsonl'
            out=Path(temp)/'V2.jsonl'
            fixture=source()
            source_file.write_text(json.dumps(fixture)+'\n')
            snapshot=make_reconciled_pregame_v2(
                fixture,official_prior(),prior_year_speed(),now=NOW,
                current_source_checksums={'history':'a'*64},
                source_last_verified_date='2026-10-07'
            )
            self.assertEqual(append_v2_only(out,snapshot),9)
            original=out.read_bytes()
            with patch('intelligence_warehouse.historical_recovery.mlb_live_research_feature_freeze_v2.pd.read_csv',
                       side_effect=AssertionError('No large official source read for duplicate event')):
                state=freeze_v2_cycle(
                    source_file,out,now=NOW,
                    legacy_file=Path(temp)/'UNAVAILABLE_LEGACY.csv',
                    incremental_file=Path(temp)/'UNAVAILABLE_RECENT.csv',
                    game_master_file=Path(temp)/'UNAVAILABLE_GAMES.csv',
                    prior_biomechanics_file=Path(temp)/'UNAVAILABLE_SPEED.parquet',
                )
            self.assertEqual(state['fresh_v2_player_features_appended'],0)
            self.assertEqual(state['previously_frozen_player_ids_preserved'],9)
            self.assertFalse(state['large_history_reconciliation_run'])
            self.assertEqual(out.read_bytes(),original)

    def test_a_2027_feature_capture_rejects_2025_completed_speed_as_not_prior(self):
        recent=source(captured=NOW.replace(year=2027),first_pitch=START.replace(year=2027))
        h=official_prior().copy()
        h['season']=2027
        with self.assertRaisesRegex(ValueError,'immediately prior season'):
            make_reconciled_pregame_v2(
                recent,h,prior_year_speed(),now=NOW.replace(year=2027),
                current_source_checksums={'old':'a'*64},
                source_last_verified_date='2027-10-07'
            )
