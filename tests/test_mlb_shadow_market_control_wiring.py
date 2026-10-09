"""Frozen pregame hits shadow market-control baseline must survive cleanup."""
from pathlib import Path
import json,hashlib,unittest

ROOT=Path(__file__).resolve().parents[1]
DIR='intelligence_warehouse/mlb_pregame_capture'
FROZEN=f'{DIR}/MLB_V2_MARKET_CALIBRATION_SHADOW_FORECASTS.jsonl'
RECEIPT=f'{DIR}/MLB_V2_MARKET_CALIBRATION_SHADOW_SUMMARY.json'

class TrueForwardResearchShadowWiringTests(unittest.TestCase):
 def test_shadow_runs_after_verified_two_sided_source_but_before_any_betting_decision(self):
  txt=(ROOT/'mlb_live/run_mlb_refresh.sh').read_text()
  source='intelligence_warehouse.historical_recovery.mlb_paired_pregame_market_freeze'
  shadow='intelligence_warehouse.historical_recovery.mlb_shadow_market_control'
  self.assertEqual(txt.count(shadow),1)
  self.assertIn('SPORTS_LABEL=mlb-market-only-shadow-model',txt)
  self.assertIn('SPORTS_MAX_SECONDS=20',txt)
  self.assertLess(txt.index(source),txt.index(shadow))
  self.assertLess(txt.index(shadow),txt.index('=== MLB DECISION BRAIN ==='))
  self.assertIn('prior source-time shadow forecasts preserved',txt)

 def test_immutable_control_and_research_receipt_are_in_content_archive(self):
  j=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
  for rel,lane in [
   (FROZEN,'mlb_v2_forward_market_only_calibration_frozen_research'),
   (RECEIPT,'mlb_v2_forward_market_only_calibration_research_receipt')
  ]:
   with self.subTest(rel=rel):
    got=[e for e in j['files'] if e['path']==rel]
    self.assertEqual(len(got),1)
    self.assertEqual(got[0]['sport'],'MLB')
    self.assertEqual(got[0]['lane'],lane)
    self.assertTrue((ROOT/rel).is_file())

 def test_real_first_forecasts_are_only_one_independent_game_and_not_bets(self):
  records=[json.loads(s) for s in (ROOT/FROZEN).read_text().splitlines() if s.strip()]
  first=[r for r in records if r['game_pk']==849832]
  self.assertEqual(len(first),18)
  self.assertIn(849832,{x['game_pk'] for x in records})
  self.assertEqual(len({(r['game_pk'],r['mlbam_player_id'],r['market_metric'],r['line']) for r in records}),len(records))
  self.assertEqual(hashlib.sha256(''.join((ROOT/FROZEN).read_text().splitlines(keepends=True)[:18]).encode()).hexdigest(),
                   'a7cbaf78dec8a932eb5751ada54ac79d4e0d6fe46affad0737fb6692d17420cd')
  self.assertTrue(all(r['frozen_shadow_at_utc']<r['actual_game_event_start_utc'] for r in records))
  self.assertTrue(all(r['market_metric']=='hits' and r['line']==.5 for r in records))
  self.assertTrue(all(not r['wager_submitted'] and not r['betting_play_authorized'] for r in records))
  self.assertFalse(any(r['proprietary_speed_walks_model_evaluated'] for r in records))

 def test_private_state_recovery_and_gitignore_do_not_expose_original_odds(self):
  s=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
  ignore=(ROOT/'.gitignore').read_text()
  for path in (FROZEN,RECEIPT):
   self.assertIn(f'copy_if_exists "{path}"',s)
   self.assertIn(path,ignore)

if __name__=='__main__':unittest.main()
