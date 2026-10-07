"""Batch-safe recovered MLB IDs must be corroborated by two league sources."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from intelligence_warehouse.betting_v2 import (
    build_prop_v2_forward as props,
    mlb_official_box_forward as mlb,
    mlb_verified_player_crosswalk as crosswalk,
)
from test_mlb_official_box_forward import (
    SOURCE_ROW, ENTRY, FakeSession, csvfile,
)


def official_context(*, player_id="643217", player="Andrew Benintendi",
                     team="Chicago White Sox"):
    return {"player_id": player_id, "player": player, "team": team}


def official_history(*, player_id="643217", player="Andrew Benintendi",
                     team="Chicago White Sox", season="2026",
                     official_date="2026-09-28",
                     source="MLB_STATSAPI_OFFICIAL_BOXSCORE",
                     source_tier="OFFICIAL_LEAGUE_FEED",
                     status="Final"):
    return {
        "player_id": player_id, "player": player, "team": team,
        "season": season, "official_date": official_date,
        "source": source, "source_tier": source_tier, "status": status,
    }


class StrictCrosswalkTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.archive = (self.root / "mlb_live/decision/history/snapshots"
                        / "20261005T180000Z_fixture/MLB_PROP_CANDIDATES.csv")
        self.context = self.root / crosswalk.CROSSWALK_FILES[0]
        self.history = self.root / crosswalk.CROSSWALK_FILES[1]
        self.entry = dict(ENTRY)
        self.sources()

    def sources(self, archive=None, context=None, history=None):
        csvfile(self.archive, archive if archive is not None else [
            dict(SOURCE_ROW, player_id=""),
        ])
        csvfile(self.context, context if context is not None else [official_context()])
        csvfile(self.history, history if history is not None else [official_history()])

    def plan(self, entries=None, session=None):
        arr = [self.entry] if entries is None else entries
        return mlb.plan_mlb_settlement(
            self.root, {r["forward_key"]: r for r in arr},
            session or FakeSession(),
        )

    def setup_ledger(self, entries=None):
        folder = self.root / "intelligence_warehouse/betting_v2"
        folder.mkdir(parents=True, exist_ok=True)
        ledger = folder / "PROP_V2_FORWARD_LEDGER.jsonl"
        entries = [self.entry] if entries is None else entries
        ledger.write_text("".join(json.dumps(r) + "\n" for r in entries))
        receipt = folder / "MLB_OFFICIAL_BOX_FORWARD_RECEIPT.json"
        return ledger, receipt

    def test_two_official_sources_and_unique_final_box_prove_numeric_id(self):
        receipt, events = self.plan()
        self.assertEqual(receipt["status"], "READY")
        self.assertEqual(receipt["id_crosswalk"]["status"], "READY")
        self.assertEqual(receipt["verified_new"], 1)
        self.assertEqual(receipt["verified_new_by_player_id_provenance"], {
            "TWO_STATSAPI_ID_SOURCES_EXACT_NAME_AND_TEAM": 1,
        })
        self.assertEqual(len(receipt["id_source_fingerprints"]), 2)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["official_player_id"], "643217")
        self.assertEqual(event["settlement_match_type"], "MLB_VERIFIED_HISTORICAL_ID_CROSSWALK")
        self.assertEqual(event["grade"], "WIN")
        self.assertEqual(event["actual_value"], 2)
        self.assertFalse(event["automatic_model_promotion"])
        self.assertFalse(event["platform_payout_claimed"])

    def test_missing_one_or_both_independent_sources_cannot_grade(self):
        for missing in (self.context, self.history):
            with self.subTest(missing=str(missing)):
                content = missing.read_bytes()
                missing.unlink()
                receipt, events = self.plan()
                self.assertEqual(receipt["status"], "READY")
                self.assertEqual(events, [])
                self.assertEqual(receipt["review_reasons"]["NO_INDEPENDENT_VERIFIED_OFFICIAL_ID_CROSSWALK"], 1)
                missing.parent.mkdir(parents=True, exist_ok=True)
                missing.write_bytes(content)

    def test_distinct_conflicting_player_ids_fail_closed(self):
        for context, history in (
            ([official_context(player_id="999999")], [official_history()]),
            ([official_context()], [official_history(player_id="999999")]),
            ([official_context(), official_context(player_id="999999")],
             [official_history()]),
            ([official_context()],
             [official_history(), official_history(player_id="999999")]),
        ):
            with self.subTest(context=context, history=history):
                self.sources(context=context, history=history)
                receipt, events = self.plan()
                self.assertEqual(events, [])
                self.assertEqual(receipt["status"], "READY")
                self.assertEqual(receipt["review_reasons"]["NO_INDEPENDENT_VERIFIED_OFFICIAL_ID_CROSSWALK"], 1)
                self.assertGreater(receipt["id_crosswalk"].get("conflicting_official_identity_pairs", 0), 0)

    def test_exact_player_name_and_team_must_agree(self):
        for context, history in (
            ([official_context(player="Another Batter")], [official_history()]),
            ([official_context()], [official_history(player="Another Batter")]),
            ([official_context(team="Tampa Bay Rays")], [official_history()]),
            ([official_context()], [official_history(team="Tampa Bay Rays")]),
        ):
            with self.subTest(context=context, history=history):
                self.sources(context=context, history=history)
                receipt, events = self.plan()
                self.assertEqual(events, [])

    def test_exact_unicode_player_names_normalize_without_fuzzy_matching(self):
        self.sources(
            context=[official_context(player="Andréw Beníntendi")],
            history=[official_history(player="Andréw Beníntendi")],
        )
        receipt, events = self.plan()
        self.assertEqual(receipt["status"], "READY")
        self.assertEqual(len(events), 1)
        self.sources(
            context=[official_context(player="Andrew Another")],
            history=[official_history(player="Andrew Another")],
        )
        _, events = self.plan()
        self.assertEqual(events, [])

    def test_only_league_official_game_history_qualifies(self):
        for change in (
            {"source": "USER_PROVIDED"},
            {"source_tier": "THIRD_PARTY_ESTIMATE"},
            {"status": "Scheduled"},
            {"season": "2025"},
            {"official_date": "invalid"},
        ):
            with self.subTest(change=change):
                self.sources(history=[official_history(**change)])
                receipt, events = self.plan()
                self.assertEqual(events, [])
                self.assertEqual(receipt["status"], "READY")

    def test_identity_evidence_must_exist_before_original_capture(self):
        self.sources(history=[official_history(official_date="2026-10-06")])
        receipt, events = self.plan()
        self.assertEqual(events, [])
        self.assertEqual(receipt["review_reasons"]["NO_INDEPENDENT_VERIFIED_OFFICIAL_ID_CROSSWALK"], 1)

    def test_unique_exact_id_cannot_be_swapped_to_someone_else_in_final_box(self):
        self.sources(context=[official_context(player_id="999999")],
                     history=[official_history(player_id="999999")])
        receipt, events = self.plan()
        self.assertEqual(receipt["status"], "READY")
        self.assertEqual(events, [])
        self.assertEqual(receipt["review_reasons"]["PLAYER_MISSING_OR_DUPLICATED_IN_FINAL_BOX"], 1)

    def test_exact_id_in_box_but_player_did_not_play_remains_pending(self):
        fake = FakeSession()
        fake.boxes["849834"]["liveData"]["boxscore"]["teams"]["away"]["batters"] = []
        receipt, events = self.plan(session=fake)
        self.assertEqual(events, [])
        self.assertEqual(receipt["review_reasons"]["PLAYER_NOT_VERIFIED_PLAYED"], 1)

    def test_ambiguous_original_archived_ids_do_not_use_crosswalk_fallback(self):
        self.sources(archive=[
            dict(SOURCE_ROW, player_id="111111"),
            dict(SOURCE_ROW, player_id="222222"),
        ])
        receipt, events = self.plan()
        self.assertEqual(events, [])
        self.assertEqual(receipt["review_reasons"]["CONFLICTING_ARCHIVED_OFFICIAL_PLAYER_IDS"], 1)

    def test_source_fingerprint_stable_and_detects_changed_history(self):
        before = crosswalk.source_fingerprint(self.root)
        self.assertEqual(len(before), 2)
        self.assertEqual(crosswalk.source_fingerprint(self.root), before)
        self.sources(history=[official_history(official_date="2026-09-27")])
        self.assertNotEqual(crosswalk.source_fingerprint(self.root), before)

    def test_history_changes_during_research_fail_closed(self):
        stamp = crosswalk.source_fingerprint(self.root)
        stale = dict(stamp)
        stale[crosswalk.CROSSWALK_FILES[1]] = "changed-source"
        with patch.object(mlb, "source_fingerprint",
                          side_effect=[stamp, stale]):
            receipt, events = self.plan()
        self.assertEqual(receipt["status"], "PLAYER_ID_SOURCES_CHANGED_DURING_RESEARCH")
        self.assertEqual(events, [])

    def test_history_changes_before_append_never_writes(self):
        ledger, output = self.setup_ledger()
        before = ledger.read_bytes()
        stamp = crosswalk.source_fingerprint(self.root)
        stale = dict(stamp)
        stale[crosswalk.CROSSWALK_FILES[0]] = "modified"
        with patch.object(props, "ROOT", self.root), \
             patch.object(props, "LEDGER", ledger), \
             patch.object(props, "MLB_BOX_RECEIPT", output), \
             patch.object(mlb, "source_fingerprint",
                          side_effect=[stamp, stamp]), \
             patch.object(crosswalk, "source_fingerprint", return_value=stale):
            receipt = props.settle_mlb_official_box(session=FakeSession())
        self.assertEqual(receipt["status"], "OFFICIAL_ID_EVIDENCE_CHANGED_BEFORE_APPEND")
        self.assertEqual(receipt["settled_now"], 0)
        self.assertEqual(ledger.read_bytes(), before)

    def test_small_batched_settlements_are_append_only_and_idempotent(self):
        other = dict(self.entry, forward_key="frozen-mlb-two", line=0.5)
        ledger, output = self.setup_ledger([self.entry, other])
        before = ledger.read_bytes()
        with patch.object(props, "ROOT", self.root), \
             patch.object(props, "LEDGER", ledger), \
             patch.object(props, "MLB_BOX_RECEIPT", output):
            first = props.settle_mlb_official_box(session=FakeSession(), max_events=1)
            self.assertEqual(first["settled_now"], 1)
            self.assertEqual(first["pending_verified_next_batch"], 1)
            self.assertEqual(first["batch_limit"], 1)
            middle = ledger.read_bytes()
            self.assertTrue(middle.startswith(before))
            second = props.settle_mlb_official_box(session=FakeSession(), max_events=1)
            self.assertEqual(second["settled_now"], 1)
            self.assertEqual(second["pending_verified_next_batch"], 0)
            third = props.settle_mlb_official_box(session=FakeSession(), max_events=1)
            self.assertEqual(third["settled_now"], 0)
            self.assertEqual(third["existing_verified"], 2)
            self.assertEqual(len(ledger.read_text().splitlines()), 4)
            self.assertTrue(ledger.read_bytes().startswith(before))
            self.assertTrue(all(x["grade"] == "WIN" for x in props.canonical().values()))

    def test_reject_zero_negative_or_oversized_batches(self):
        for amount in (0, -1, 501, 0.5, None):
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    props.settle_mlb_official_box(session=FakeSession(), max_events=amount)


if __name__ == "__main__":
    unittest.main()
