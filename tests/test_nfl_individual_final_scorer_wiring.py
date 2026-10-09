"""NFL source-time moneyline model grades individual games after official Final.

This must NEVER mutate the 13 first-frozen pregame probabilities or Survivor.
"""
from pathlib import Path
import json,hashlib,unittest

ROOT=Path(__file__).resolve().parents[1]
DIR='intelligence_warehouse/nfl_advanced_pregame'
FINALS=f'{DIR}/NFL_2026_FIRST_FUTURE_EVENT_ESPN_FINAL_ORIGINAL_SOURCE.jsonl'
FINAL_SUM=f'{DIR}/NFL_2026_FIRST_FUTURE_EVENT_ESPN_FINAL_SOURCE_SUMMARY.json'
SCORES=f'{DIR}/NFL_NINE_FEATURE_SAME_BOOK_OFFICIAL_FINAL_SCORES.jsonl'
SCORE_SUM=f'{DIR}/NFL_NINE_FEATURE_OFFICIAL_FINAL_COMPARISON_SUMMARY.json'
REPORT='reports/SPORTS_ZENITH_NFL_2026_FIRST_13_FORWARD_MODEL_AND_OFFICIAL_FINAL_2026-10-09.md'

class NFLResearchOnlyIndependentFinalGradeDurabilityTests(unittest.TestCase):
 def test_individual_final_result_source_before_threeway_research_score(self):
  shell=(ROOT/'nfl_live/decision/run_nfl_learning_postrefresh.sh').read_text()
  collector='intelligence_warehouse.historical_recovery.nfl_forward_individual_final_source --stage collect_original_game_finals'
  grader='intelligence_warehouse.historical_recovery.nfl_nine_col_official_scoring'
  self.assertEqual(shell.count(collector),1)
  self.assertEqual(shell.count(grader),1)
  self.assertIn('SPORTS_LABEL=nfl-first-original-final-game-research',shell)
  self.assertIn('SPORTS_LABEL=nfl-first-9feature-market-final-scorer',shell)
  self.assertIn('SPORTS_MAX_SECONDS=25',shell)
  self.assertIn('SPORTS_MAX_SECONDS=15',shell)
  self.assertLess(shell.index('SURVIVOR RC: $SURVIVOR_RC'),shell.index(collector))
  self.assertLess(shell.index(collector),shell.index(grader))
  self.assertIn('original NFL research score preserved',shell)

 def test_source_code_scoring_reads_original_individual_final_not_full_week(self):
  from intelligence_warehouse.historical_recovery import nfl_nine_col_official_scoring as grader
  self.assertEqual(grader.FINALS,ROOT/FINALS)

 def test_new_original_final_event_grade_scores_and_checkpoint_are_backed_up(self):
  registry=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
  backup=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
  ignore=(ROOT/'.gitignore').read_text()
  for path,lane in (
    (FINALS,'nfl_2026_first_individual_official_final_espn_event_proofs'),
    (FINAL_SUM,'nfl_2026_first_individual_final_source_receipt'),
    (SCORES,'nfl_2026_first_independent_true_final_model_vs_book_scored_ledger'),
    (SCORE_SUM,'nfl_2026_first_independent_true_final_model_vs_book_scoring_receipt'),
    (REPORT,'nfl_2026_first_thirteen_moneyline_model_research_acceptance'),
  ):
   with self.subTest(source=path):
    rows=[r for r in registry['files'] if r['path']==path]
    self.assertEqual(len(rows),1)
    self.assertEqual(rows[0]['sport'],'NFL')
    self.assertEqual(rows[0]['lane'],lane)
    self.assertTrue((ROOT/path).is_file())
    self.assertIn(f'copy_if_exists "{path}"',backup)
    if path.startswith(DIR):self.assertIn(path,ignore)

 def test_earliest_week5_forecasts_first_thirteen_have_immutable_first_source_sha(self):
  p=ROOT/DIR/'NFL_FIRST_PREKICKOFF_NINE_FEATURE_SCORE_FORM_SHADOW.jsonl'
  data=[json.loads(line) for line in p.read_text().splitlines() if line.strip()]
  self.assertGreaterEqual(len(data),13)
  self.assertEqual(len({x['official_espn_event_id'] for x in data}),len(data))
  self.assertEqual(
    hashlib.sha256(''.join(p.read_text().splitlines(keepends=True)[:13]).encode()).hexdigest(),
    'b74351d24c0cf591624a74c8dc2d33f84ea34f1374c65d782219bc5d95b60602',
  )
  self.assertTrue(all(x['source_context_features_frozen_at_utc']<x['source_qualified_book_quote_updated_at_utc']<x['source_first_real_future_prediction_frozen_at_utc']<x['official_first_pitch_utc'] for x in data))
  self.assertFalse(any(x['betting_play_approved'] or x['sportsbook_wager_created'] for x in data))

 def test_no_false_nfl_final_grades_are_implied_by_unplayed_games(self):
  grades=[json.loads(s) for s in (ROOT/SCORES).read_text().splitlines() if s.strip()]
  source=[json.loads(s) for s in (ROOT/FINALS).read_text().splitlines() if s.strip()]
  summary=json.loads((ROOT/SCORE_SUM).read_text())
  self.assertEqual(len(grades),summary['source_pairs_scored'])
  self.assertEqual(len({r['official_espn_event_id'] for r in grades}),len(grades))
  self.assertFalse(summary['market_advantage_statistically_proven'])
  self.assertFalse(summary['live_play_approved'])
  self.assertEqual(len({r['official_espn_game_id'] for r in source}),len(source))
  self.assertTrue(all(r['official_espn_final_confirmed'] and r['real_original_ESPN_game_event_payload_retained'] for r in source))

if __name__=='__main__':unittest.main()
