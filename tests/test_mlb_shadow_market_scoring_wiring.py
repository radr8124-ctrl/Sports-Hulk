"""MLB source-time market+shadow must score only after independent Official Final."""
from pathlib import Path
import json,unittest

ROOT=Path(__file__).resolve().parents[1]
DIR='intelligence_warehouse/mlb_pregame_capture'
SCORED=f'{DIR}/MLB_V2_MARKET_SHADOW_OFFICIAL_COMPARISON.jsonl'
SUMMARY=f'{DIR}/MLB_V2_MARKET_SHADOW_OFFICIAL_COMPARISON_SUMMARY.json'

class RealShadowLearningAutomationTests(unittest.TestCase):
 def test_scorer_runs_after_independent_official_hit_grade_as_research_only(self):
  s=(ROOT/'mlb_live/decision/run_mlb_learning_postrefresh.sh').read_text()
  frozen='intelligence_warehouse.historical_recovery.mlb_research_forward_labels'
  evaluator='intelligence_warehouse.historical_recovery.mlb_shadow_market_official_scoring'
  self.assertEqual(s.count(evaluator),1)
  self.assertIn('SPORTS_LABEL=mlb-research-market-shadow-scoring',s)
  self.assertIn('SPORTS_MAX_SECONDS=15',s)
  self.assertLess(s.index(frozen),s.index(evaluator))
  self.assertIn('original scoring history preserved',s)

 def test_research_only_scored_sources_persist_in_content_archive(self):
  catalog=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
  for path,lane in [
   (SCORED,'mlb_v2_forward_market_only_shadow_vs_market_official_scored_history'),
   (SUMMARY,'mlb_v2_forward_market_only_shadow_vs_market_official_score_receipt'),
  ]:
   with self.subTest(path=path):
    rows=[x for x in catalog['files'] if x['path']==path]
    self.assertEqual(len(rows),1)
    self.assertEqual(rows[0]['lane'],lane)
    self.assertEqual(rows[0]['sport'],'MLB')
    self.assertTrue((ROOT/path).is_file())

 def test_scored_ledgers_protected_by_backup_and_not_public(self):
  back=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
  ignore=(ROOT/'.gitignore').read_text()
  for p in (SCORED,SUMMARY):
   self.assertIn(f'copy_if_exists "{p}"',back)
   self.assertIn(p,ignore)

 def test_current_game_unfinished_no_false_win_or_market_edge(self):
  rows=[json.loads(s) for s in (ROOT/SCORED).read_text().splitlines() if s.strip()]
  a=json.loads((ROOT/SUMMARY).read_text())
  self.assertEqual(a['settled_player_market_comparisons'],len(rows))
  self.assertEqual(a['independent_games_with_settled_comparisons'],len({r['official_game_pk'] for r in rows}))
  self.assertFalse(any(r['sportsbook_wager_placed'] for r in rows))
  self.assertFalse(a['commercial_betting_edge_claim_permitted'])
  self.assertEqual(a['minimum_independent_games_for_first_sample_floor'],30)

if __name__=='__main__': unittest.main()
