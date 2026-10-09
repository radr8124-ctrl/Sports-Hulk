"""No backdated NFL 70% winners or artificially profitable prices."""
import copy,hashlib,json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest import mock
from intelligence_warehouse.selective_forward import nfl_70_forward_evidence as s

NOW=datetime(2026,10,9,6,23,tzinfo=timezone.utc)


def source():
    return json.loads(next(x for x in s.SOURCE.read_text().splitlines() if x.strip()))


def hypothetical_qualified():
    r=source()
    r["nine_feature_score_form_home_win_prob"]=0.76
    r["original_same_book_american_home_moneyline"]=-230.0
    r["original_same_book_american_away_moneyline"]=195.0
    a=s.implied(-230.0);b=s.implied(195.0)
    r["original_raw_book_home_fair"]=a/(a+b)
    return r


class TestNFLResearchSeventyPercent(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.spec=json.loads(s.SPEC.read_text())

    def tearDown(self):self.tmp.cleanup()

    def test_original_13_frozen_before_future_week_games(self):
        with mock.patch.object(s,"OUT",self.root/"selections.jsonl"):
            first=s.capture(clock=NOW)
            saved=(self.root/"selections.jsonl").read_bytes()
            self.assertEqual(first["total_original_game_selections_saved"],13)
            self.assertEqual(first["original_game_abstentions_saved"],13)
            self.assertEqual(first["provisional_paper_screen_pass_count"],0)
            self.assertEqual(s.capture(clock=NOW)["new_game_abstention_or_screen_records"],0)
            self.assertEqual(saved,(self.root/"selections.jsonl").read_bytes())
            for r in s.rows(self.root/"selections.jsonl"):
                self.assertLess(s.stamp(r["original_frozen_at_utc"]),s.stamp(r["official_first_pitch_utc"]))
                self.assertFalse(r["production_bet_allowed"])
                self.assertFalse(r["named_book_original_price_independently_executable"])

    def test_frozen_source_first_13_hash_stops_rewrite(self):
        data=s.SOURCE.read_bytes()
        altered=self.root/"tampered.jsonl"
        altered.write_bytes(data.replace(b"PHI",b"ZZZ",1))
        with mock.patch.object(s,"SOURCE",altered),mock.patch.object(s,"OUT",self.root/"selection.jsonl"):
            with self.assertRaisesRegex(ValueError,"ORIGINAL_13_NFL_PREDICTIONS_CHANGED"):
                s.capture(clock=NOW)
            self.assertFalse((self.root/"selection.jsonl").exists())

    def test_high_probability_alone_is_not_a_qualified_pick(self):
        r=source()
        out=s.make_selection(r,self.spec,NOW)
        self.assertGreater(out["original_model_probability"],0.7)
        self.assertFalse(out["fixed_research_screen_pass"])
        self.assertIn("BOOK_EDGE_BELOW_3PP",out["fixed_screen_blockers"])

    def test_large_model_edge_and_quote_ev_is_only_hypothetical_research(self):
        out=s.make_selection(hypothetical_qualified(),self.spec,NOW)
        self.assertTrue(out["fixed_research_screen_pass"])
        self.assertGreaterEqual(out["model_minus_book_pp"],3)
        self.assertGreaterEqual(out["priced_research_expected_roi_pct"],3)
        self.assertFalse(out["production_bet_allowed"])
        self.assertFalse(out["named_book_original_price_independently_executable"])

    def test_source_price_disagreement_rejected(self):
        r=hypothetical_qualified()
        r["original_raw_book_home_fair"]=0.5
        with self.assertRaisesRegex(ValueError,"ORIGINAL_PRICE_AND_NO_VIG_DISAGREE"):
            s.make_selection(r,self.spec,NOW)

    def test_cannot_infer_new_prediction_after_game_start(self):
        r=hypothetical_qualified()
        with self.assertRaisesRegex(ValueError,"PREGAME_SOURCE_CLOCK"):
            s.make_selection(r,self.spec,datetime(2026,10,14,tzinfo=timezone.utc))

    def test_source_quote_must_follow_original_features(self):
        r=hypothetical_qualified()
        r["source_qualified_book_quote_updated_at_utc"]=r["source_context_features_frozen_at_utc"]
        with self.assertRaisesRegex(ValueError,"PREGAME_SOURCE_CLOCK"):
            s.make_selection(r,self.spec,NOW)

    def test_append_conflicting_original_decision_rejected(self):
        path=self.root/"selections.jsonl"
        x=s.make_selection(source(),self.spec,NOW)
        self.assertEqual(s.append(path,[x]),1)
        before=path.read_bytes()
        altered={**x,"fixed_research_screen_pass":True}
        with self.assertRaisesRegex(ValueError,"WOULD_BE_REWRITTEN"):
            s.append(path,[altered])
        self.assertEqual(before,path.read_bytes())

    def official_fixture(self):
        x=s.make_selection(hypothetical_qualified(),self.spec,NOW)
        # Artificial unit-test Final: never part of real ledger.
        x["official_first_pitch_utc"]="2026-10-08T00:00:00+00:00"
        x["original_frozen_at_utc"]="2026-10-07T23:00:00+00:00"
        final={
           "official_espn_event_id":x["official_espn_event_id"],
           "research_only":True,"not_sportsbook_settlement_or_wager_win":True,
           "original_model_sha256":x["original_model_sha256"],
           "source_first_original_model_frozen_at_utc":x["original_frozen_at_utc"],
           "home_team":x["home_team"],"away_team":x["away_team"],
           "original_home_moneyline_win_binary_outcome":1,
           "official_home_points":27,"official_away_points":20,
           "source_real_original_final_observed_at_utc":"2026-10-08T04:00:00+00:00",
           "source_original_espn_final_scoreboard_sha256":"a"*64,
        }
        return x,final

    def test_synthetic_final_grades_only_matching_identity_once(self):
        x,final=self.official_fixture()
        sel=self.root/"selections.jsonl";grad=self.root/"grade.jsonl";result=self.root/"official.jsonl"
        s.append(sel,[x]);result.write_text(json.dumps(final)+"\n")
        with mock.patch.object(s,"OUT",sel),mock.patch.object(s,"OFFICIAL",result),mock.patch.object(s,"GRADES",grad):
            r=s.grade()
            self.assertEqual(r["new_official_final_games_graded"],1)
            self.assertEqual(r["qualifier_wins"],1)
            self.assertFalse(r["market_advantage_proven"])
            before=grad.read_bytes()
            self.assertEqual(s.grade()["new_official_final_games_graded"],0)
            self.assertEqual(before,grad.read_bytes())
            self.assertFalse(s.rows(grad)[0]["actual_wager_or_verified_execution"])

    def test_fake_or_future_final_rejected(self):
        x,final=self.official_fixture()
        sel=self.root/"selections.jsonl";grad=self.root/"grades.jsonl";result=self.root/"official.jsonl"
        s.append(sel,[x])
        for field,val in [("official_away_points",37),("source_real_original_final_observed_at_utc","2026-11-18T04:00:00+00:00")]:
            bad={**final,field:val}
            result.write_text(json.dumps(bad)+"\n")
            with mock.patch.object(s,"OUT",sel),mock.patch.object(s,"OFFICIAL",result),mock.patch.object(s,"GRADES",grad):
                with self.assertRaisesRegex(ValueError,"OFFICIAL"):
                    s.grade()
                self.assertFalse(grad.exists())


if __name__=="__main__":unittest.main()
