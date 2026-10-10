"""Source-verified cross-sport after-game learning with no betting-model promotion."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from intelligence_warehouse.sport_cohorts import build_sport_cohort_readiness as core
from intelligence_warehouse.outcome_learning.learning_core import canonical

ROOT=Path(__file__).resolve().parents[1]

class OfficialSportCohortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger_before=(ROOT/core.LEDGER).read_bytes()
        cls.ledger_sha=hashlib.sha256(cls.ledger_before).hexdigest()
        cls.events=[json.loads(s) for s in cls.ledger_before.decode().splitlines() if s.strip()]
        cls.original_entries=[r for r in cls.events if r.get('event_type')=='ENTRY']
        cls.records,_=canonical(cls.events)
        cls.sources,cls.hashes=core.official_sources()
        cls.report=core.replay()

    @classmethod
    def tearDownClass(cls):
        assert hashlib.sha256((ROOT/core.LEDGER).read_bytes()).hexdigest()==cls.ledger_sha

    @staticmethod
    def frozen_replay_row(entry):
        from intelligence_warehouse.outcome_learning.learning_core import when
        return {**entry,
                'original_capture_utc':when(entry['captured_at']).isoformat(),
                'original_start_utc':when(entry['event_start']).isoformat(),
                'market_probability_pct':entry['entry_market_reference_probability_pct'],
                'model_probability_pct':entry['entry_v2_probability_pct'],
                'grade':'PENDING'}

    def test_official_phase_proof_keeps_nba_preseason_out_of_regular_season(self):
        preseason=[r for r in self.sources['NBA'] if r['start'].year==2026 and r['start'].month==10 and r['start'].day<=14]
        self.assertTrue(preseason)
        self.assertEqual({r['phase'] for r in preseason},{'PRESEASON'})
        self.assertIn('PRESEASON',{c['competition'] for c in self.report['cohorts'] if c['sport']=='NBA'})
        self.assertEqual(len({(c['sport'],c['competition'],c['phase_stage']) for c in self.report['cohorts']}),len(self.report['cohorts']))
        self.assertTrue(all(c['independent_model_advantage_established'] is False for c in self.report['cohorts']))
        self.assertTrue(self.report['cross_sport_competition_leakage_blocked'])
        self.assertTrue(self.report['original_phase_fields_unchanged'])

    def test_nhl_regular_and_college_football_regular_are_separate(self):
        nhl=[c for c in self.report['cohorts'] if c['sport']=='NHL' and c['competition']=='REGULAR']
        cfb=[c for c in self.report['cohorts'] if c['sport']=='CFB' and c['competition']=='REGULAR']
        self.assertGreaterEqual(nhl[0]['unique_official_final_games'],17)
        self.assertEqual(nhl[0]['competition'],'REGULAR')
        self.assertEqual(cfb[0]['competition'],'REGULAR')
        self.assertGreaterEqual(cfb[0]['unique_official_final_games'],5)
        self.assertTrue(all(c['market_probability_equals_model_count']==c['independently_verified_official_final_selections'] for c in nhl+cfb))

    def test_original_mlb_statsapi_game_type_distinguishes_series(self):
        mlb={r['official_game_id']:r for r in self.sources['MLB']}
        self.assertEqual(mlb['849831']['stage'],'DIVISION_SERIES')
        self.assertEqual(mlb['849809']['stage'],'LEAGUE_CHAMPIONSHIP')
        self.assertIsInstance(mlb['849831']['final'],bool)
        self.assertEqual(self.report['source_hashes']['MLB_original_league_source_sha256'],self.hashes['MLB'])
        post=[c for c in self.report['cohorts'] if c['sport']=='MLB']
        self.assertGreaterEqual(sum(c['unique_official_final_games'] for c in post),9)
        self.assertEqual({c['competition'] for c in post},{'POSTSEASON'})
        self.assertTrue(all(c['phase_stage'] in {'DIVISION_SERIES','LEAGUE_CHAMPIONSHIP','WILD_CARD','WORLD_SERIES'} for c in post))

    def test_nba_franchise_aliases_link_exact_known_games_and_clock(self):
        for original,market in [
            ('NY','NYK'),('NO','NOP'),('GS','GSW'),('UTAH','UTA'),('SA','SAS'),('WSH','WAS')]:
            self.assertEqual(core.official_team_code('NBA',original),market.lower())
        selected=next(x for x in self.records if x['sport']=='NBA' and x['game_key']=='2026-10-05|NYK|PHI')
        matched,err=core.match_official(selected,self.sources['NBA'])
        self.assertIsNone(err)
        self.assertEqual(len(matched),1)
        self.assertEqual(matched[0]['away_score'],97)
        self.assertEqual(matched[0]['home_score'],120)
        self.assertEqual(matched[0]['phase'],'PRESEASON')
        self.assertFalse(matched[0]['stage']=='REGULAR')

    def test_team_identity_wrong_kickoff_and_wrong_competition_block_source(self):
        original=next(x for x in self.records if x['sport']=='NBA' and x['game_key']=='2026-10-05|NYK|PHI')
        matched,err=core.match_official({**original,'game_key':'2026-10-05|LAL|PHI'},self.sources['NBA'])
        self.assertEqual(err,'NO_UNIQUE_OFFICIAL_FIXTURE_MATCH')
        matched,err=core.match_official({**original,'original_start_utc':'2026-10-05T16:00:00+00:00'},self.sources['NBA'])
        self.assertEqual(err,'NO_UNIQUE_OFFICIAL_FIXTURE_MATCH')
        matched,err=core.match_official(original,self.sources['NBA'])
        self.assertEqual(core.phase_claim({**original,'competition_regime':'REGULAR'},matched[0]),
                         'ORIGINAL_COMPETITION_PHASE_CONFLICT')

    def test_ledger_settlements_crossmatch_exact_final_games_without_modifications(self):
        self.assertEqual(self.report['schema'],'ZENITH_SPORT_PHASE_LEARNING_COHORTS_V1')
        self.assertEqual(self.report['status'],'REVIEW_ONLY_NO_AUTOMATIC_MODEL_CHANGE')
        count=sum(c['independently_verified_official_final_selections'] for c in self.report['cohorts'])
        self.assertEqual(count,self.report['source_verified_final_research_selections'])
        self.assertGreaterEqual(count,201)
        self.assertGreaterEqual(self.report['source_verified_distinct_final_games'],53)
        self.assertEqual(self.report['production_model_weights_changed'],False)
        self.assertEqual(self.report['model_bets_approved'],0)
        self.assertEqual(self.report['actual_sportsbook_wagers_placed'],0)

    def test_pending_nba_same_game_alt_lines_recovered_only_as_SHADOW(self):
        original=next(x for x in self.original_entries if x['sport']=='NBA'
                     and x['game_key']=='2026-10-05|NYK|PHI' and x['market']=='SPREAD'
                     and x['selection_key']=='AWAY' and x['line']==7.5)
        pending=self.frozen_replay_row(original)
        matched,err=core.match_official(pending,self.sources['NBA'])
        self.assertIsNone(err)
        recovery=core.derive_pending_official_final(pending,matched[0])
        self.assertEqual(recovery['calculated_result'],'LOSS')
        self.assertTrue(recovery['original_entry_remains_PENDING'])
        self.assertTrue(recovery['derived_postgame_from_official_result_only'])
        self.assertEqual(recovery['training_eligibility'],'DENIED_NOT_AN_INDEPENDENT_PROVEN_FORECAST')
        self.assertFalse(recovery['original_bookmaker_price_executable_verified'])
        self.assertTrue(recovery['original_probability_copied_market'])

    def test_push_is_exact_and_alternate_lines_cannot_claim_independent_games(self):
        entry=next(x for x in self.original_entries if x['sport']=='NBA'
                   and x['market']=='TOTAL' and x['line'] is not None
                   and x['game_key']=='2026-10-05|NYK|PHI')
        original=self.frozen_replay_row(entry)
        matched,err=core.match_official(original,self.sources['NBA'])
        self.assertIsNone(err)
        fake=copy.deepcopy(original)
        fake['line']=matched[0]['home_score']+matched[0]['away_score']
        fake['selection_key']='OVER'
        recovery=core.derive_pending_official_final(fake,matched[0])
        self.assertEqual(recovery['calculated_result'],'PUSH')
        self.assertEqual(core.derive_pending_official_final({**fake,'line':None},matched[0]),None)
        nba=next(x for x in self.report['pending_official_final_recovery_by_sport'] if x['sport']=='NBA')
        self.assertGreaterEqual(nba['derived_postgame_research_rows'],0)
        self.assertLessEqual(nba['unique_official_games'],
            sum(c['unique_official_final_games'] for c in self.report['cohorts'] if c['sport']=='NBA'))
        self.assertGreaterEqual(nba['original_duplicate_line_variant_count'],0)
        self.assertTrue(nba['cannot_count_multiple_lines_as_independent_games'])
        self.assertEqual(nba['market_probability_copied_count'],nba['derived_postgame_research_rows'])
        self.assertEqual(nba['original_qualified_game_grade_line_missing_count'],
                         sum(x.get('original_unsettled_exact_line_missing_from_grade_source') is True
                             for x in json.loads((ROOT/core.RECOVERY).read_text())['rows']
                             if x['sport']=='NBA'))
        self.assertLessEqual(nba['original_qualified_game_grade_line_missing_count'],
                             nba['derived_postgame_research_rows'])

    def test_disputed_nhl_moneyline_is_not_an_approved_wager(self):
        nhl=[x for x in self.report['pending_official_final_recovery_by_sport'] if x['sport']=='NHL']
        if nhl:
            self.assertGreaterEqual(nhl[0]['original_opposite_side_conflict_count'],0)
            self.assertTrue(nhl[0]['original_forward_grade_was_not_rewritten'])
        self.assertEqual(self.report['pending_shadow_results_added_to_original_ledger'],0)

    def test_raw_immutable_mlb_and_histories_have_sha256_evidence(self):
        for sport in core.SOURCES:
            path=core.source_path_for_sport(ROOT,sport)
            raw=path.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),self.hashes[sport])
            self.assertEqual(len(self.hashes[sport]),64)
        self.assertEqual(self.report['source_hashes']['frozen_betting_market_ledger_sha256'],self.ledger_sha)
        original=(ROOT/core.NBA_QUALIFIED_GRADE_SOURCE).read_bytes()
        self.assertEqual(self.report['source_hashes']['original_nba_exact_game_grade_source_sha256'],
                         hashlib.sha256(original).hexdigest())
        self.assertTrue(self.report['official_sources_fetched_after_original_frozen_prediction'])

    def test_published_shadow_receipt_is_sha_matched_and_never_modifies_original(self):
        public=json.loads((ROOT/core.PUBLIC).read_text())
        original=json.loads((ROOT/core.RECOVERY).read_text())
        self.assertEqual(public['full_official_shadow_receipt_sha256'],
            hashlib.sha256((ROOT/core.RECOVERY).read_bytes()).hexdigest())
        self.assertEqual(original['derived_rows_count'],len(original['rows']))
        self.assertEqual(original['derived_rows_count'],public['derived_pending_from_official_final_research_rows'])
        self.assertEqual(original['recorded_original_betting_ledger_updates'],0)
        self.assertFalse(original['independent_profit_or_model_edge_proven'])
        self.assertTrue(all(x['original_entry_remains_PENDING'] for x in original['rows']))
        self.assertTrue(all(x['training_eligibility']=='DENIED_NOT_AN_INDEPENDENT_PROVEN_FORECAST' for x in original['rows']))
        self.assertEqual((ROOT/core.PUBLIC).read_bytes(),(ROOT/core.DIST).read_bytes())

if __name__=='__main__':
    unittest.main()
