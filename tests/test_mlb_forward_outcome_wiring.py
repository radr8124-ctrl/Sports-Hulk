"""Future official MLB outcomes must be tied only to real frozen research features."""
from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
PREFIX='intelligence_warehouse/mlb_pregame_capture'
LEDGER=f'{PREFIX}/MLB_V2_OFFICIAL_FORWARD_RESEARCH_LABELS.jsonl'
SUMMARY=f'{PREFIX}/MLB_V2_OFFICIAL_FORWARD_LABEL_SUMMARY.json'

class ForwardResearchLabelsWiringTests(unittest.TestCase):
    def test_official_labels_recheck_runs_after_existing_learning_and_results(self):
        s=(ROOT/'mlb_live/decision/run_mlb_learning_postrefresh.sh').read_text()
        x='intelligence_warehouse.historical_recovery.mlb_research_forward_labels'
        self.assertEqual(s.count(x),1)
        self.assertIn('SPORTS_LABEL=mlb-research-forward-official-labels',s)
        self.assertIn('SPORTS_MAX_SECONDS=25',s)
        self.assertLess(s.index('SPORTS_LABEL=mlb-prop-grade-context'),s.index(x))
        self.assertIn('research labeling failed; no existing frozen outcomes overwritten',s)

    def test_archive_has_separate_research_outcome_ledger_and_operational_receipt(self):
        j=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        for lane,file in [
            ('mlb_v2_true_forward_research_official_player_outcome_labels',LEDGER),
            ('mlb_v2_true_forward_research_official_player_outcome_receipt',SUMMARY)
        ]:
            with self.subTest(file=file):
                hits=[v for v in j['files'] if v['path']==file]
                self.assertEqual(len(hits),1)
                self.assertEqual(hits[0]['sport'],'MLB')
                self.assertEqual(hits[0]['lane'],lane)
                self.assertTrue((ROOT/file).is_file())

    def test_private_backup_and_ignore_keep_no_paid_research_labels_private(self):
        s=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        ignore=(ROOT/'.gitignore').read_text()
        for path in (LEDGER,SUMMARY):
            self.assertIn(f'copy_if_exists "{path}"',s)
            self.assertIn(path,ignore)
        self.assertIn(f'{PREFIX}/*.lock',ignore)

    def test_final_checkpoint_has_a_versioned_archived_recovery_manifest(self):
        rel='reports/SPORTS_ZENITH_MLB_POSTSEASON_ASOF_FORWARD_RESEARCH_ACCEPTANCE_2026-10-08.md'
        path=ROOT/rel
        self.assertTrue(path.is_file())
        self.assertIn('source',path.read_text().lower())
        j=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        matches=[x for x in j['files'] if x.get('path')==rel]
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0]['sport'],'MLB')
        self.assertEqual(matches[0]['lane'],'mlb_v2_forward_history_recovery_acceptance_report')
        self.assertIn(f'copy_if_exists "{rel}"',
                      (ROOT/'scripts/backup_sports_zenith_state.sh').read_text())

    def test_no_betting_results_fabricated_for_upcoming_game(self):
        path=ROOT/LEDGER
        rows=[json.loads(s) for s in path.read_text().splitlines() if s.strip()]
        receipt=json.loads((ROOT/SUMMARY).read_text())
        self.assertEqual(receipt['total_official_research_labels'],len(rows))
        self.assertEqual(len({(r['official_game_pk'],r['player_id']) for r in rows}),len(rows))
        self.assertTrue(all(r['official_final_status_from_mlb_master']=='Final' for r in rows))
        self.assertFalse(any(r['sportsbook_bet_settled'] or r['model_win_or_probability_qualified'] or r['live_play_approved'] for r in rows))
        self.assertFalse(receipt['sportsbook_predictions_scored_or_promoted'])

if __name__=='__main__': unittest.main()
