"""Post-registered MLB Full16 70% value filter never counts old game as forward."""
import json,tempfile,unittest,copy
from datetime import datetime,timezone
from pathlib import Path
from unittest import mock

from intelligence_warehouse.selective_forward import mlb_70_forward_evidence as m

NOW=datetime(2026,10,9,6,32,tzinfo=timezone.utc)


def original():
    return json.loads(m.SOURCE.read_text().splitlines()[0])


def synthetic_future(p=.8,price_over=-160,price_under=135):
    r=original()
    r['official_game_pk']=849831
    r['independent_game_block_id']="849831"
    r['official_first_pitch_utc']="2026-10-11T00:00:00+00:00"
    r['source_team_context_frozen_at_utc']="2026-10-10T21:00:00+00:00"
    r['source_quote_at_utc']="2026-10-10T21:02:00+00:00"
    r['first_full_context_shadow_frozen_at_utc']="2026-10-10T21:04:00+00:00"
    r['source_raw_over_american']=price_over
    r['source_raw_under_american']=price_under
    a,b=m.implied(price_over),m.implied(price_under)
    r['source_book_overround']=a+b
    r['market_fair_prob_at_exact_new_quote']=a/(a+b)
    r['sixteen_feature_context_shadow_prob']=p
    return r


class TestMLBFull16SeventyForward(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.tmp.name)
        self.spec=json.loads(m.SPEC.read_text())

    def tearDown(self):self.tmp.cleanup()

    def test_prior_grading_is_excluded_from_all_future_selection(self):
        with mock.patch.object(m,'OUT',self.home/'new_only.jsonl'),mock.patch.object(m,'GRADES',self.home/'graded.jsonl'):
            a=m.capture(clock=NOW)
            self.assertEqual(a['all_original_full16_player_forecasts'],18)
            self.assertEqual(a['old_scored_game_player_records_explicitly_excluded'],18)
            self.assertEqual(a['total_recorded_future_research_player_legs'],0)
            self.assertEqual(m.grade()['total_official_player_grade_rows'],0)
            self.assertFalse((self.home/'new_only.jsonl').exists())

    def test_true_future_high_probability_and_ev_still_only_research(self):
        row=m.create_selection(synthetic_future(),self.spec,NOW)
        self.assertTrue(row['fixed_provisional_research_screen_pass'])
        self.assertGreater(row['model_over_book_advantage_pp'],3)
        self.assertGreater(row['source_quoted_price_paper_ev_pct'],3)
        self.assertFalse(row['production_wager_approved'])
        self.assertFalse(row['named_book_price_proven_executable'])

    def test_original_full16_earlier_settled_game_cannot_be_recalled(self):
        with self.assertRaisesRegex(ValueError,"PREVIOUSLY_SETTLED"):
            m.create_selection(original(),self.spec,NOW)

    def test_changed_original_model_source_rejected(self):
        f=self.home/'corrupt.jsonl'
        f.write_bytes(m.SOURCE.read_bytes().replace(b'849832',b'000000',1))
        with mock.patch.object(m,'SOURCE',f),mock.patch.object(m,'OUT',self.home/'new.jsonl'):
            with self.assertRaisesRegex(ValueError,"ORIGINAL_ALREADY_GRADED_MLB_MODEL_SOURCE_CHANGED"):
                m.capture(clock=NOW)

    def test_original_source_american_odds_pair_must_balance(self):
        r=synthetic_future()
        r['market_fair_prob_at_exact_new_quote']=0.5
        with self.assertRaisesRegex(ValueError,"BOOK_QUOTE_AND_ORIGINAL_NO_VIG"):
            m.create_selection(r,self.spec,NOW)

    def test_source_context_frozen_before_new_book_quote(self):
        r=synthetic_future()
        r['source_quote_at_utc']=r['source_team_context_frozen_at_utc']
        with self.assertRaisesRegex(ValueError,"MLB_NEW_PROSPECTIVE"):
            m.create_selection(r,self.spec,NOW)

    def test_stale_price_fails_value_qualification(self):
        r=synthetic_future()
        r['first_full_context_shadow_frozen_at_utc']="2026-10-10T21:42:00+00:00"
        out=m.create_selection(r,self.spec,NOW)
        self.assertIn("BOOK_QUOTE_TOO_OLD_AT_MODEL_FREEZE",out['fixed_screen_blocker_reasons'])
        self.assertFalse(out['fixed_provisional_research_screen_pass'])

    def test_original_game_pk_player_id_duplicate_rejected(self):
        path=self.home/'frozen.jsonl'
        r=m.create_selection(synthetic_future(),self.spec,NOW)
        self.assertEqual(m.append(path,[r]),1)
        prior=path.read_bytes()
        self.assertEqual(m.append(path,[r]),0)
        self.assertEqual(path.read_bytes(),prior)
        with self.assertRaisesRegex(ValueError,"WOULD_CHANGE"):
            m.append(path,[dict(r,chosen_side='UNDER_0_5')])
        self.assertEqual(path.read_bytes(),prior)

    def test_under_side_allowed_but_no_bet(self):
        r=synthetic_future(p=.2)
        x=m.create_selection(r,self.spec,NOW)
        self.assertEqual(x['chosen_side'],"UNDER_0_5")
        self.assertFalse(x['production_wager_approved'])

    def synthetic_final_fixture(self):
        x=m.create_selection(synthetic_future(),self.spec,NOW)
        x['original_source_start_utc']="2026-10-08T00:00:00+00:00"
        x['original_model_frozen_at_utc']="2026-10-07T23:58:00+00:00"
        x['original_quote_time_utc']="2026-10-07T23:57:00+00:00"
        f={
          'official_game_pk':x['official_game_pk'],'mlbam_player_id':x['mlbam_player_id'],
          'official_status':'Final','research_only':True,'model_promoted_to_live_play':False,
          'original_training_model_sha256':x['original_full16_model_sha256'],
          'original_official_pregame_source_sha256':x['original_source_lineup_sha256'],
          'market_bookmaker':x['original_book'],
          'original_model_prospectively_frozen_at_utc':x['original_model_frozen_at_utc'],
          'original_source_new_quote_at_utc':x['original_quote_time_utc'],
          'official_game_start_utc':x['original_source_start_utc'],
          'actual_hits_over_half':1,'official_player_hits':2,
          'source_final_checked_at_utc':'2026-10-08T04:00:00+00:00'
        }
        return x,f

    def test_synthetic_official_final_grade_once(self):
        x,f=self.synthetic_final_fixture()
        src=self.home/'original.jsonl';out=self.home/'graded.jsonl';official=self.home/'official.jsonl'
        m.append(src,[x]);official.write_text(json.dumps(f)+'\n')
        with mock.patch.object(m,'OUT',src),mock.patch.object(m,'GRADES',out),mock.patch.object(m,'OFFICIAL',official):
            first=m.grade()
            self.assertEqual(first['new_real_official_player_hits_grades'],1)
            self.assertEqual(first['fixed_research_qualifier_wins'],1)
            before=out.read_bytes()
            self.assertEqual(m.grade()['new_real_official_player_hits_grades'],0)
            self.assertEqual(out.read_bytes(),before)
            self.assertFalse(m.records(out)[0]['real_sportsbook_execution_or_payout_verified'])

    def test_wrong_player_hits_grade_or_quote_source_rejected(self):
        x,f=self.synthetic_final_fixture()
        src=self.home/'original.jsonl';out=self.home/'graded.jsonl';official=self.home/'official.jsonl'
        m.append(src,[x])
        for column,bad in [('official_player_hits',0),('market_bookmaker','different')]:
            official.write_text(json.dumps(dict(f,**{column:bad}))+'\n')
            with mock.patch.object(m,'OUT',src),mock.patch.object(m,'GRADES',out),mock.patch.object(m,'OFFICIAL',official):
                with self.assertRaisesRegex(ValueError,'GRADE|OFFICIAL'):
                    m.grade()
                self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
