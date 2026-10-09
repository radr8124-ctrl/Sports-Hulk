"""Frozen MLB 2h source price study: real MLBAM/official hits validation only."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest import mock

from intelligence_warehouse.mlb_pregame_capture import grade_future_price_movement as g
from intelligence_warehouse.mlb_pregame_capture import freeze_source_price_movement as m

AFTER=datetime(2026,10,11,8,tzinfo=timezone.utc)


def specimen():
    return json.loads(m.OUT.read_text().splitlines()[0])


def fake_verified_real_hitter():
    """Only unit-test data. No synthetic outcomes enter live user's research."""
    r=specimen()
    model=json.loads(g.MODEL.read_text().splitlines()[0])
    original=json.loads(g.FINAL.read_text().splitlines()[0])
    model.update({
        "official_game_pk":r["official_game_pk"],
        "source_provider":r["source_provider"],
        "source_provider_event_uuid":r["source_event_uuid"],
        "source_provider_player_uuid":r["source_player_provider_uuid"],
        "official_first_pitch_utc":r["source_start_utc"],
        "first_full_context_shadow_frozen_at_utc":"2026-10-10T23:30:00+00:00",
        "source_quote_at_utc":"2026-10-10T23:29:00+00:00",
        "original_lineup_sha256":"0"*64,
        "full_context_is_pre_first_pitch_source_frozen":True,
        "has_any_july_outcomes_in_fitted_coefficients":False,
    })
    original.update({
        "official_game_pk":r["official_game_pk"],
        "mlbam_player_id":model["mlbam_player_id"],
        "actual_hits_over_half":1,
        "official_player_hits":2,
        "official_status":"Final",
        "research_only":True,
        "model_promoted_to_live_play":False,
        "original_training_model_sha256":model["frozen_prejuly_model_sha256"],
        "original_official_pregame_source_sha256":model["original_lineup_sha256"],
        "original_model_prospectively_frozen_at_utc":model["first_full_context_shadow_frozen_at_utc"],
        "original_source_new_quote_at_utc":model["source_quote_at_utc"],
        "official_game_start_utc":r["source_start_utc"],
        "independent_game_block_id":str(r["official_game_pk"]),
        "source_final_checked_at_utc":"2026-10-11T04:00:00+00:00",
        "market_bookmaker":model["selected_sportsbook"],
    })
    mk=(int(model["official_game_pk"]),int(model["mlbam_player_id"]))
    return r,model,original,mk


class TestMLBOfficialMarketMovementGrades(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.spec=json.loads(g.SPEC.read_text())

    def one(self,model=None,final=None):
        r,x,y,mk=fake_verified_real_hitter()
        return g.official_grades_for_frozen(
            [r],{mk:[(model or x,"a"*64)]},
            {mk:[(final or y,"b"*64)]},
            now=AFTER,spec=self.spec,
        )

    def test_real_pending_source_does_not_invent_outcomes(self):
        real=m.records(m.OUT)
        originals=g.original_line_index(g.MODEL)
        finals=g.original_line_index(g.FINAL)
        found,waiting=g.official_grades_for_frozen(
            real,originals,finals,
            now=datetime.now(timezone.utc),spec=self.spec,
        )
        self.assertEqual(found,[])
        self.assertEqual(waiting.get("NO_PREKICKOFF_FULL16_MLBAM_PLAYER_UUID_BRIDGE"),len(real))

    def test_future_official_MLBAM_bridge_grades_one_research_player(self):
        found,waiting=self.one()
        self.assertEqual(len(found),1)
        self.assertEqual(waiting,{})
        r=found[0]
        self.assertEqual(r["official_hits_over_0_5_binary"],1)
        self.assertEqual(r["independent_official_player_hits"],2)
        self.assertAlmostEqual(
            r["original_raw_market_fair_brier"],
            (r["original_market_fair_probability"]-1)**2,places=9
        )
        self.assertFalse(r["production_model_changed"])
        self.assertFalse(r["real_wager_executed"])

    def test_without_exact_provider_UUID_MLBAM_bridge_never_grade(self):
        r,x,y,mk=fake_verified_real_hitter()
        x=dict(x,source_provider_player_uuid="different-original-player")
        found,waiting=g.official_grades_for_frozen(
            [r],{mk:[(x,"hash")]},{mk:[(y,"scorehash")]},
            now=AFTER,spec=self.spec)
        self.assertEqual(found,[])
        self.assertEqual(waiting,{"NO_PREKICKOFF_FULL16_MLBAM_PLAYER_UUID_BRIDGE":1})

    def test_before_official_final_missing_results_are_pending(self):
        r,x,y,mk=fake_verified_real_hitter()
        found,waiting=g.official_grades_for_frozen(
            [r],{mk:[(x,"hash")]},{},now=AFTER,spec=self.spec)
        self.assertEqual(found,[])
        self.assertEqual(waiting,{"OFFICIAL_COMPLETED_GAME_FINAL_NOT_YET_VERIFIED":1})

    def test_inconsistent_original_lineup_hash_rejected(self):
        _,x,y,_=fake_verified_real_hitter()
        y=dict(y,original_official_pregame_source_sha256="bad")
        with self.assertRaisesRegex(ValueError,"INDEPENDENT_OFFICIAL_MLB_FINAL"):
            self.one(final=y)

    def test_forged_final_points_and_behind_kickoff_rejected(self):
        _,_,y,_=fake_verified_real_hitter()
        for changes,error in [
            ({"official_player_hits":0},"OFFICIAL_PLAYER_HITS"),
            ({"actual_hits_over_half":0},"OFFICIAL_PLAYER_HITS"),
            ({"official_status":"In Progress"},"INDEPENDENT_OFFICIAL_MLB_FINAL"),
            ({"source_final_checked_at_utc":"2026-10-10T22:00:00+00:00"},"FUTURE_MLB_FINAL"),
            ({"source_final_checked_at_utc":"2026-10-18T22:00:00+00:00"},"FUTURE_MLB_FINAL"),
            ({"market_bookmaker":"wrong-original-book"},"INDEPENDENT_OFFICIAL_MLB_FINAL"),
        ]:
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ValueError,error):
                    self.one(final=dict(y,**changes))

    def test_official_identity_ambiguity_refused(self):
        r,x,y,mk=fake_verified_real_hitter()
        with self.assertRaisesRegex(ValueError,"DUPLICATE_INDEPENDENT"):
            g.official_grades_for_frozen([r],{mk:[(x,"a")]},
              {mk:[(y,"b"),(y,"b")]},now=AFTER,spec=self.spec)
        with self.assertRaisesRegex(ValueError,"MODEL_SOURCE_UUID_TO_MLBAM_AMBIGUOUS"):
            g.official_grades_for_frozen([r],
              {mk:[(x,"a"),(x,"a")]},{mk:[(y,"b")]},now=AFTER,spec=self.spec)

    def test_grade_append_is_idempotent_and_refuses_rewriting_wins(self):
        record=self.one()[0][0]
        path=self.base/"grades.jsonl"
        self.assertEqual(g.append_verified(path,[record]),1)
        before=path.read_bytes()
        self.assertEqual(g.append_verified(path,[record]),0)
        self.assertEqual(path.read_bytes(),before)
        fake=dict(record,official_hits_over_0_5_binary=0)
        with self.assertRaisesRegex(ValueError,"GRADE_WAS_REWRITTEN"):
            g.append_verified(path,[fake])
        self.assertEqual(path.read_bytes(),before)

    def test_small_game_count_not_market_edge_even_if_lower_brier(self):
        source=self.one()[0]
        report=g.summarize(source,{},1,spec=self.spec)
        self.assertEqual(report["official_independent_games_graded"],1)
        self.assertTrue(report["actual_profitability_betting_threshold_not_proven"])
        self.assertEqual(report["primary_4h_horizon_statistical_proof_status"],
                         "NOT_ENOUGH_INDEPENDENT_GAMES")
        self.assertIn("EARLY_DISCOVERY",report["by_fixed_horizon"])

    def test_original_first18_model_SHA_still_matches_training_baseline(self):
        original=b"".join(g.MODEL.read_bytes().splitlines(keepends=True)[:18])
        self.assertEqual(hashlib.sha256(original).hexdigest(),
                         self.spec["original_full16_existing_18_game_forecasts_sha256"])


if __name__=="__main__":unittest.main()
