"""MLB 2025 park and proven prequote probable pitcher source is immutable/private."""
from pathlib import Path
import hashlib
import json
import unittest
from unittest.mock import patch

from intelligence_warehouse.historical_recovery.mlb_pitcher_park_source_asof import (
    freeze_cycle,
)

ROOT=Path(__file__).resolve().parents[1]
BASE='intelligence_warehouse/mlb_pregame_capture'
LEDGER=f'{BASE}/MLB_V3_PROBABLE_PITCHER_PRIOR_PARK_RESEARCH.jsonl'
SUMMARY=f'{BASE}/MLB_V3_PROBABLE_PITCHER_PRIOR_PARK_SUMMARY.json'
REPORT='reports/SPORTS_ZENITH_MLB_PITCHER_PARK_TRUE_PREGAME_SOURCE_2026-10-08.md'

class PitcherParkSourceRecoveryAndScheduledSafety(unittest.TestCase):
    def test_current_original_game_has_exact_hash_and_prior_2025_park(self):
        p=ROOT/LEDGER
        rows=[json.loads(s) for s in p.read_text().splitlines() if s.strip()]
        original_game=[r for r in rows if r['official_game_pk']==849832]
        self.assertEqual(len(original_game),18)
        self.assertIn(849832,{r['official_game_pk'] for r in rows})
        self.assertEqual({r['prior_park_venue_id'] for r in original_game},{4})
        self.assertEqual({r['reference_prior_full_park_season'] for r in original_game},{2025})
        self.assertTrue(all(r['prior_regular_season_park_games']>=40 for r in rows))
        self.assertTrue(all(r['stale_game_master_first_pitch_disagreement_flag'] for r in original_game))
        self.assertEqual({r['game_master_original_kickoff_discrepancy_minutes'] for r in original_game},{-180.})
        self.assertFalse(any(r['opposing_probable_pitcher_confirmed_starter'] for r in rows))
        self.assertFalse(any(r['model_probabilities_predicted'] or r['betting_picks_created'] for r in rows))
        self.assertTrue(all(r['source_pitcher_and_park_context_frozen_at_utc']<r['official_source_game_first_pitch_utc'] for r in rows))
        original=(ROOT/f'{BASE}/MLB_PREGAME_SOURCE_EVIDENCE.jsonl').read_text().splitlines(keepends=True)
        valid={hashlib.sha256(line.encode()).hexdigest() for line in original if line.strip()}
        self.assertTrue(all(r['original_batting_order_line_sha256'] in valid for r in rows))

    def test_duplicate_scheduled_v3_capture_does_not_reload_big_pitcher_sources(self):
        from datetime import datetime,timezone
        now=datetime(2026,10,8,23,17,tzinfo=timezone.utc)
        with patch('intelligence_warehouse.historical_recovery.mlb_pitcher_park_source_asof.pd.read_csv',
                   side_effect=AssertionError('Already frozen V3 research cannot reload 85MB player history')):
            status=freeze_cycle(now=now)
        self.assertEqual(status['new_source_records'],0)
        self.assertEqual(status['previously_frozen_preserved'],18)
        self.assertFalse(status['large_history_loaded'])

    def test_schedule_after_official_game_master_refresh_and_before_betting_markets(self):
        text=(ROOT/'mlb_live/run_mlb_refresh.sh').read_text()
        command='intelligence_warehouse.historical_recovery.mlb_pitcher_park_source_asof --stage freeze_research_context'
        self.assertEqual(text.count(command),1)
        self.assertIn('SPORTS_LABEL=mlb-probable-pitcher-park-research',text)
        self.assertIn('SPORTS_MAX_SECONDS=45',text)
        self.assertLess(text.index('=== OFFICIAL MLB MASTER STATUS FRESHNESS ==='),text.index(command))
        self.assertLess(text.index(command),text.index('=== MLB MARKETS ==='))
        self.assertIn('older source research preserved',text)

    def test_new_source_artifacts_and_report_archive_and_private_backup(self):
        manifest=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        back=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        ignore=(ROOT/'.gitignore').read_text()
        expected=[
            (LEDGER,'mlb_v3_new_true_pregame_probable_pitcher_prior_park_research'),
            (SUMMARY,'mlb_v3_new_true_pregame_probable_pitcher_prior_park_receipt'),
            (REPORT,'mlb_v3_prior_park_and_verified_pitcher_source_acceptance_report'),
        ]
        for p,lane in expected:
            with self.subTest(source=p):
                hits=[x for x in manifest['files'] if x.get('path')==p]
                self.assertEqual(len(hits),1)
                self.assertEqual(hits[0]['lane'],lane)
                self.assertEqual(hits[0]['sport'],'MLB')
                self.assertTrue((ROOT/p).is_file())
                self.assertIn(f'copy_if_exists "{p}"',back)
                if p!=REPORT:self.assertIn(p,ignore)

if __name__=='__main__':unittest.main()
