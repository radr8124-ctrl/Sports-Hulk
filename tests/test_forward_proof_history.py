"""Regression proof for the immutable "How Good Is The Brain" performance trail."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import hashlib,json,tempfile,unittest
from pathlib import Path
from intelligence_warehouse.brain_performance import build_forward_proof_history as p


class TestProofHistorySourceTruth(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for key,relative in p.SOURCE_FILES.items():
            f=self.root/relative
            f.parent.mkdir(parents=True,exist_ok=True)
            if key=="game_forward":
                x={"status":"READY","model_version":"FROZEN_V1","current_model_version":"FROZEN_V1",
                   "generated_at":"2026-10-09T07:00:00+00:00",
                   "all_predictions":{
                       "tracked":4,"settled":3,"pending":1,
                       "wins":2,"losses":1,"pushes":0,
                       "independent_blocks":3,"priced_settled":3,
                       "hit_rate_pct":66.7,"market_brier":0.245,"v2_brier":0.240,
                       "units":.5,"roi_pct":16.67,"roi_lcb90_pct":-22.,
                       "proof_status":"NOT_PROVEN","live_rule_changed":False,
                   }}
            elif key=="props_forward":
                x={"status":"READY","model_version":"PROP_FIXED_V1",
                   "generated_at":"2026-10-09T07:10:00+00:00",
                   "all_predictions":{
                       "tracked":5,"settled":4,"pending":1,"wins":2,"losses":2,"pushes":0,
                       "independent_blocks":3,"priced_settled":4,
                       "hit_rate_pct":50.0,"market_brier":0.200,"v2_brier":0.205,
                       "units":-1,"roi_pct":-25.0,"roi_lcb90_pct":-30,
                       "proof_status":"NOT_PROVEN","live_rule_changed":False,
                   }}
            elif key=="mlb_full16":
                x={"independent_official_game_blocks":1,
                   "original_true_full16_shadow_forecasts":18,
                   "book_raw_brier":0.216,"full16_brier":0.215}
            elif key=="mlb_price_movement":
                x={"new_model_retraining_or_promotion":False,
                   "all_future_horizon_frozen_movement_records":4,
                   "distinct_future_official_games":2,
                   "by_predeclared_horizon":{"EARLY_DISCOVERY":4},
                   "fixed_gt_3pp_movement_source_records":1,
                   "original_book_market_prices_verified_executable":False}
            elif key=="mlb_movement_final":
                x={"official_graded_movement_records":0,
                   "pending_source_reasons":{"NO_PREKICKOFF_FULL16_MLBAM_PLAYER_UUID_BRIDGE":4},
                   "by_fixed_horizon":{}}
            elif key=="mlb_forward70":
                x={"production_model_or_wagers_changed":False}
            elif key=="nfl_forward70":
                x={"research_only_not_live_betting_picks":True,
                   "capture":{"original_frozen_nfl_models":13,
                               "total_original_game_selections_saved":13,
                               "original_game_abstentions_saved":13,
                               "provisional_paper_screen_pass_count":0},
                   "grade":{"all_official_games_graded":0}}
            elif key=="cfb_learning":
                x={"generated_at":"2026-10-09T07:05:00+00:00",
                   "automatic_model_adjustment":False,"unique_recommendations":4,
                   "settled":2,
                   "grade_counts":{"WIN":1,"LOSS":1,"PUSH":0,"PENDING":2}}
            f.write_text(json.dumps(x,sort_keys=True))
        self.clock=datetime(2026,10,9,8,tzinfo=timezone.utc)

    def file(self,key):
        return self.root/p.SOURCE_FILES[key]

    def modify(self,key,update):
        q=self.file(key)
        old=json.loads(q.read_text())
        update(old)
        q.write_text(json.dumps(old,sort_keys=True))

    def history(self):
        return self.root/p.BASE/p.HISTORY

    def test_initial_scorecard_and_accurate_roi_metric_source(self):
        outcome=p.capture(root=self.root,clock=self.clock)
        self.assertEqual(outcome["state"],"APPENDED_VERIFIED_SOURCE_CHANGE")
        self.assertEqual(outcome["history_entries"],1)
        view=outcome["latest"]["view"]
        self.assertEqual(view["game_lines"]["wins"],2)
        self.assertEqual(view["game_lines"]["settled"],3)
        self.assertEqual(view["props_and_pickem"]["source_book_quoted_paper_roi_pct"],-25)
        self.assertFalse(view["experiment_result"]["profitable_70_percent_betting_strategy_proven"])
        self.assertFalse(view["mlb_full16"]["statistically_supported_model_improvement"])
        self.assertEqual(view["mlb_source_price_movement"]["independent_upcoming_games"],2)
        self.assertEqual(view["nfl_frozen_70_screen"]["all_source_abstentions_saved"],13)
        self.assertEqual(view["cfb_original_research_learning"]["settled_research_grades"],2)

    def test_rerun_identical_source_does_not_append(self):
        a=p.capture(root=self.root,clock=self.clock)
        before=self.history().read_bytes()
        b=p.capture(root=self.root,clock=self.clock+timedelta(hours=1))
        self.assertEqual(b["state"],"ORIGINAL_SOURCE_UNCHANGED_NO_DUPLICATE_CHECKPOINT")
        self.assertEqual(a["latest"]["entry_sha256"],b["latest"]["entry_sha256"])
        self.assertEqual(before,self.history().read_bytes())

    def test_verified_new_settled_result_adds_chained_snapshot(self):
        x=p.capture(root=self.root,clock=self.clock)
        original=self.history().read_bytes()
        def update(r):
            v=r["all_predictions"]
            v["settled"]=4;v["wins"]=3;v["pending"]=0
            v["hit_rate_pct"]=75.;v["independent_blocks"]=4
            v["priced_settled"]=4;v["units"]=1.5;v["roi_pct"]=37.5
            r["generated_at"]="2026-10-09T08:30:00+00:00"
        self.modify("game_forward",update)
        y=p.capture(root=self.root,clock=self.clock+timedelta(hours=1))
        self.assertEqual(y["history_entries"],2)
        self.assertTrue(self.history().read_bytes().startswith(original))
        chain=p.verify_history(self.history())
        self.assertEqual(len(chain),2)
        self.assertEqual(chain[1]["previous_entry_sha256"],chain[0]["entry_sha256"])
        self.assertEqual(chain[1]["view"]["game_lines"]["settled"],4)

    def test_missing_current_view_rebuilt_from_original_verified_history(self):
        initial=p.capture(root=self.root,clock=self.clock)
        before=self.history().read_bytes()
        current=self.root/p.BASE/p.CURRENT
        current.unlink()
        repaired=p.capture(root=self.root,clock=self.clock+timedelta(hours=1))
        self.assertEqual(repaired['state'],'CURRENT_VIEW_RESTORED_FROM_VERIFIED_ORIGINAL_HISTORY')
        self.assertEqual(self.history().read_bytes(),before)
        self.assertEqual(json.loads(current.read_text()),initial['latest'])

    def test_current_view_content_tamper_cannot_be_silently_overwritten(self):
        p.capture(root=self.root,clock=self.clock)
        prior=self.history().read_bytes()
        current=self.root/p.BASE/p.CURRENT
        cached=json.loads(current.read_text())
        cached['view']['game_lines']['hit_rate_pct']=100.0
        current.write_text(json.dumps(cached))
        with self.assertRaisesRegex(ValueError,'CURRENT_SCORECARD_HASH_CHAIN_READBACK_MISMATCH'):
            p.capture(root=self.root,clock=self.clock+timedelta(hours=1))
        self.assertEqual(prior,self.history().read_bytes())

    def test_deleted_or_zeroed_original_history_never_resets_proof_chain(self):
        p.capture(root=self.root,clock=self.clock)
        h=self.history();current=self.root/p.BASE/p.CURRENT
        history_backup=h.read_bytes()
        h.unlink()
        with self.assertRaisesRegex(ValueError,'HISTORY_MISSING_BUT_CURRENT_EXISTS'):
            p.capture(root=self.root,clock=self.clock+timedelta(hours=1))
        h.write_bytes(b'')
        with self.assertRaisesRegex(ValueError,'HISTORY_TRUNCATED_TO_ZERO'):
            p.capture(root=self.root,clock=self.clock+timedelta(hours=1))
        h.write_bytes(history_backup)
        self.assertEqual(len(p.verify_history(h)),1)

    def test_missing_source_preserves_existing_proof_history(self):
        p.capture(root=self.root,clock=self.clock)
        prior=self.history().read_bytes()
        self.file("props_forward").unlink()
        with self.assertRaisesRegex(ValueError,"MISSING_REQUIRED_ORIGINAL"):
            p.capture(root=self.root,clock=self.clock+timedelta(hours=1))
        self.assertEqual(prior,self.history().read_bytes())

    def test_truncated_or_rewritten_hash_line_refused(self):
        p.capture(root=self.root,clock=self.clock)
        text=self.history().read_text()
        self.history().write_text(text.replace('"settled":3','"settled":4'))
        with self.assertRaisesRegex(ValueError,"SCORECARD_HASH_CHAIN_CHANGED"):
            p.capture(root=self.root,clock=self.clock+timedelta(hours=1))

    def test_incomplete_history_row_is_rejected(self):
        p.capture(root=self.root,clock=self.clock)
        with self.history().open("ab") as f:f.write(b'{"incomplete"')
        with self.assertRaisesRegex(ValueError,"INCOMPLETE_ORIGINAL_SCORECARD"):
            p.capture(root=self.root,clock=self.clock+timedelta(hours=1))

    def test_disappearing_older_game_loss_is_detected_not_reset(self):
        p.capture(root=self.root,clock=self.clock)
        prior=self.history().read_bytes()
        def update(r):
            v=r["all_predictions"]
            v["settled"]=2;v["losses"]=0;v["pending"]=2
            v["hit_rate_pct"]=100;v["priced_settled"]=2
            v["units"]=1.5;v["roi_pct"]=75
        self.modify("game_forward",update)
        with self.assertRaisesRegex(ValueError,"SILENT_DELETION"):
            p.capture(root=self.root,clock=self.clock+timedelta(hours=1))
        self.assertEqual(prior,self.history().read_bytes())

    def test_broken_grade_count_never_becomes_100_percent(self):
        def corrupt(r):
            r["all_predictions"]["tracked"]=3
        self.modify("props_forward",corrupt)
        with self.assertRaisesRegex(ValueError,"RESULT_LEDGER_COUNTS"):
            p.capture(root=self.root,clock=self.clock)

    def test_roi_must_equal_paper_units_divided_by_original_priced_settled(self):
        def corrupt(r):
            r["all_predictions"]["roi_pct"]=75.
        self.modify("props_forward",corrupt)
        with self.assertRaisesRegex(ValueError,"ROI_NOT_MATCHING"):
            p.capture(root=self.root,clock=self.clock)

    def test_brier_worse_than_market_does_not_promote_model(self):
        r=p.capture(root=self.root,clock=self.clock)["latest"]["view"]
        self.assertFalse(r["props_and_pickem"]["model_probabilities_outperform_market_point_estimate"])
        self.assertFalse(r["props_and_pickem"]["model_outperforming_market_proven"])
        self.assertFalse(r["game_lines"]["model_outperforming_market_proven"])

    def test_nfl_abstentions_are_not_wins(self):
        def change(r):
            r["capture"]["original_game_abstentions_saved"]=12
        self.modify("nfl_forward70",change)
        with self.assertRaisesRegex(ValueError,"ABSTENTIONS"):
            p.capture(root=self.root,clock=self.clock)

    def test_missing_cfbs_are_not_counted_as_wagers(self):
        def change(r):
            r["grade_counts"]["WIN"]=4
        self.modify("cfb_learning",change)
        with self.assertRaisesRegex(ValueError,"CFB_GRADE_PROOF"):
            p.capture(root=self.root,clock=self.clock)

    def test_no_automatic_play_if_source_contract_changes(self):
        def change(r):
            r["automatic_model_adjustment"]=True
        self.modify("cfb_learning",change)
        with self.assertRaisesRegex(ValueError,"CHANGED_MODEL_AUTOMATICALLY"):
            p.capture(root=self.root,clock=self.clock)


if __name__=="__main__":unittest.main()
