"""Source-time legal 16-column MLB challenger cannot overwrite original shadow."""
from pathlib import Path
import hashlib
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
PREFIX='intelligence_warehouse/mlb_pregame_capture'
CTX=f'{PREFIX}/MLB_V4_TEAM_PARK_HITTER_16FEATURE_ASOF_CONTEXT.jsonl'
CTX_REPORT=f'{PREFIX}/MLB_V4_TEAM_PARK_HITTER_16FEATURE_ASOF_CONTEXT_SUMMARY.json'
FULL=f'{PREFIX}/MLB_V4_SIXTEEN_FEATURE_ACTUAL_FORWARD_SHADOW.jsonl'
FULL_REPORT=f'{PREFIX}/MLB_V4_SIXTEEN_FEATURE_SHADOW_CAPTURE_SUMMARY.json'
PRE='reports/mlb_feature_integration_20261008/MLB_SIXTEEN_FEATURE_PREQUOTE_FULL_CONTEXT_SHADOW_PREREGISTRATION_2026-10-08.md'
REPORT='reports/SPORTS_ZENITH_MLB_FROZEN_FULL_CONTEXT_PROSPECTIVE_SHADOW_2026-10-08.md'

class MLBFullContextSourceTimeModelWiringTests(unittest.TestCase):
    def test_context_feature_sources_ordered_before_market_snapshot(self):
        s=(ROOT/'mlb_live/run_mlb_refresh.sh').read_text()
        context='intelligence_warehouse.historical_recovery.mlb_full_context_source_time --stage freeze_prior_context'
        quote='intelligence_warehouse.historical_recovery.mlb_full_context_true_forward_shadow --stage freeze_latest_pregame_quote'
        self.assertEqual(s.count(context),1)
        self.assertEqual(s.count(quote),1)
        self.assertIn('SPORTS_LABEL=mlb-v4-full-team-source-context',s)
        self.assertIn('SPORTS_LABEL=mlb-v4-full-sixteen-shadow',s)
        self.assertIn('SPORTS_MAX_SECONDS=45',s)
        self.assertLess(s.index('intelligence_warehouse.historical_recovery.mlb_pitcher_park_source_asof'),
                        s.index(context))
        self.assertLess(s.index(context),s.index('=== MLB MARKETS ==='))
        self.assertLess(s.index('=== MLB FUSION ==='),s.index(quote))
        self.assertLess(s.index('intelligence_warehouse.historical_recovery.mlb_shadow_market_control'),
                        s.index(quote))
        self.assertLess(s.index(quote),s.index('=== MLB DECISION BRAIN ==='))
        self.assertIn('previous context model forecasts preserved',s)
        self.assertNotIn('mlb_full_context_true_forward_shadow --train',s)

    def test_new_model_context_and_research_evidence_are_immutable_private_archive_inputs(self):
        j=json.loads((ROOT/'intelligence_warehouse/catalog.json').read_text())
        backup=(ROOT/'scripts/backup_sports_zenith_state.sh').read_text()
        ignore=(ROOT/'.gitignore').read_text()
        expected=[
            (CTX,'mlb_v4_completed_opponent_team_role_prior_park_original_context'),
            (CTX_REPORT,'mlb_v4_completed_opponent_team_role_prior_park_capture_receipt'),
            (FULL,'mlb_v4_frozen_16term_context_same_book_new_quote_immutable_shadow'),
            (FULL_REPORT,'mlb_v4_frozen_16term_context_same_book_capture_receipt'),
            (PRE,'mlb_v4_frozen_16term_context_original_prior_preregistration'),
            (REPORT,'mlb_v4_frozen_16term_true_forward_acceptance_report'),
        ]
        for rel,lane in expected:
            with self.subTest(rel=rel):
                hits=[x for x in j['files'] if x.get('path')==rel]
                self.assertEqual(len(hits),1)
                self.assertEqual(hits[0]['sport'],'MLB')
                self.assertEqual(hits[0]['lane'],lane)
                self.assertTrue((ROOT/rel).is_file())
                if rel in (CTX,CTX_REPORT,FULL,FULL_REPORT):
                    self.assertIn(f'copy_if_exists "{rel}"',backup)
                    self.assertIn(rel,ignore)

    def test_all_new_16_model_quotes_really_postdate_v4_original_context(self):
        rows=[json.loads(x) for x in (ROOT/FULL).read_text().splitlines() if x.strip()]
        original_game=[r for r in rows if r['official_game_pk']==849832]
        self.assertEqual(len(original_game),18)
        self.assertIn(849832,{r['official_game_pk'] for r in rows})
        original=[json.loads(x) for x in (ROOT/CTX).read_text().splitlines() if x.strip()]
        first={(r['game_pk'],r['player_id']):r for r in original}
        self.assertEqual(len(first),len(original))
        self.assertEqual(len({r['player_id'] for r in original if r['game_pk']==849832}),18)
        self.assertEqual(hashlib.sha256(''.join((ROOT/FULL).read_text().splitlines(keepends=True)[:18]).encode()).hexdigest(),
                         '0cea5e38c94451cacbc1ff552276c5df7aa1e341296b127fd0cfa6a2d19c66a8')
        model=ROOT/'reports/mlb_feature_integration_20261008/MLB_SPEED_WALKS_FROZEN_RESEARCH_MODEL.json'
        model_sha=hashlib.sha256(model.read_bytes()).hexdigest()
        for r in rows:
            a=first[(r['official_game_pk'],r['mlbam_player_id'])]
            self.assertGreater(r['source_quote_at_utc'],a['full_team_context_first_frozen_at_utc'])
            self.assertLess(r['first_full_context_shadow_frozen_at_utc'],r['official_first_pitch_utc'])
            self.assertEqual(r['frozen_prejuly_model_sha256'],model_sha)
            self.assertEqual(r['original_lineup_sha256'],a['original_prequote_hitter_source_sha256'])
            self.assertEqual(len(r['model_16_features']),16)
            self.assertFalse(r['probable_pitcher_confirmed_starter_model_input'])
            self.assertFalse(r['betting_play_approved'])
            self.assertFalse(r['wager_executed'])

    def test_original_90_game_controls_and_eight_speed_forecast_not_modified_by_challenger(self):
        root=ROOT/PREFIX
        e=root/'MLB_V2_MARKET_CALIBRATION_SHADOW_FORECASTS.jsonl'
        prior=root/'MLB_V2_RESTRICTED_SPEED_WALKS_SHADOW_FORECASTS.jsonl'
        self.assertEqual(hashlib.sha256(''.join(e.read_text().splitlines(keepends=True)[:18]).encode()).hexdigest(),
                         'a7cbaf78dec8a932eb5751ada54ac79d4e0d6fe46affad0737fb6692d17420cd')
        self.assertEqual(hashlib.sha256(''.join(prior.read_text().splitlines(keepends=True)[:18]).encode()).hexdigest(),
                         '23267a3176615ef5adb5945c4ddb22a00e05e743c24576a7a9127fd2ba87d2f2')

if __name__=='__main__':unittest.main()
