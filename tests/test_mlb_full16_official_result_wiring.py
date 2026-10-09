"""Final MLB same-book 16-column shadow grader stays private, later, and immutable."""
from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
BASE='intelligence_warehouse/mlb_pregame_capture'
SCORES=f'{BASE}/MLB_V4_FULL16_SAME_NEW_QUOTE_OFFICIAL_THREEWAY_SCORES.jsonl'
RECEIPT=f'{BASE}/MLB_V4_FULL16_SAME_NEW_QUOTE_SCORE_SUMMARY.json'
FIX='reports/MLB_849832_ORIGINAL_OFFICIAL_PREGAME_KICKOFF_ATTESTATION_2026-10-08.json'

class FullContextModelAndMasterRecoveryWiring(unittest.TestCase):
    def test_original_final_grade_runs_before_new_full16_threeway_scoring(self):
        script=(ROOT/'mlb_live/decision/run_mlb_learning_postrefresh.sh').read_text()
        cmd='intelligence_warehouse.historical_recovery.mlb_full16_forward_official_scoring'
        self.assertEqual(script.count(cmd),1)
        self.assertIn('SPORTS_LABEL=mlb-v4-full16-official-score',script)
        self.assertIn('SPORTS_MAX_SECONDS=15',script)
        self.assertLess(script.index('intelligence_warehouse.historical_recovery.mlb_research_forward_labels'),script.index(cmd))
        self.assertIn('previous first-graded full-model research results preserved',script)

    def test_all_verified_result_and_kickoff_repair_records_archived_and_backed_up(self):
        c=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        b=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        ignore=(ROOT/'.gitignore').read_text()
        for rel,lane in [
            (SCORES,'mlb_v4_original_final_16term_market_same_quote_threeway_scored_ledger'),
            (RECEIPT,'mlb_v4_original_final_16term_market_same_quote_scoring_receipt'),
            (FIX,'mlb_source_two_original_lineups_attested_3h_start_time_correction'),
            ('baseball_vault/derived/MLB_MASTER_FRESHNESS_RECEIPT.json','mlb_official_game_master_status_source_freshness_audit'),
        ]:
            with self.subTest(rel=rel):
                matches=[r for r in c['files'] if r['path']==rel]
                self.assertEqual(len(matches),1)
                self.assertEqual(matches[0]['sport'],'MLB')
                self.assertEqual(matches[0]['lane'],lane)
                self.assertTrue((ROOT/rel).is_file())
                self.assertIn(f'copy_if_exists "{rel}"',b)
                if rel in (SCORES,RECEIPT):
                    self.assertIn(rel,ignore)

    def test_two_official_source_attestations_and_only_targeted_master_change(self):
        j=json.loads((ROOT/FIX).read_text())
        self.assertEqual(j['game_pk'],849832)
        self.assertEqual(j['old_first_pitch_utc'],'2026-10-08T21:00:00Z')
        self.assertEqual(j['corrected_first_pitch_utc'],'2026-10-09T00:00:00Z')
        self.assertEqual(len(j['two_original_verified_lineup_source_sha256']),2)
        self.assertEqual(j['only_modified_official_master_fields'],['gameDate','status'])
        self.assertFalse(j['model_probabilities_or_betting_predictions_changed'])
        self.assertEqual(j['other_unverified_game_ids_remain_held'],[849809,849831])
        m=(ROOT/'baseball_vault/derived/MLB_GAME_MASTER.csv')
        import pandas as pd
        f=pd.read_csv(m,usecols=['gamePk','gameDate','status'])
        row=f.loc[f.gamePk.eq(849832)].iloc[0]
        self.assertEqual(row.gameDate,'2026-10-09T00:00:00Z')

    def test_before_game_no_false_official_hits_or_model_score(self):
        results=[json.loads(s) for s in (ROOT/SCORES).read_text().splitlines() if s.strip()]
        j=json.loads((ROOT/RECEIPT).read_text())
        self.assertEqual(j['source_player_comparisons'],len(results))
        self.assertEqual(j['independent_official_game_blocks'],len({r['official_game_pk'] for r in results}))
        self.assertFalse(any(r['sportsbook_wager_executed'] or r['model_promoted_to_live_play'] for r in results))
        self.assertFalse(j['play_authorized'])
        self.assertFalse(j['profitable_market_edge_qualified'])

if __name__=='__main__':unittest.main()
