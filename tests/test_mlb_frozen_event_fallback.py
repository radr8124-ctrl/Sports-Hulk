"""Frozen MLB source identity remains gradeable when archive snapshots lag.

Missing archived files never justify guessing games or player IDs. New frozen
decisions with complete original MLB opponent/start and numeric player IDs
can be matched against their unique official gamePk and final boxscore.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from intelligence_warehouse.betting_v2 import (
    mlb_official_box_forward as mlb,
    mlb_forward_capture_identity as identity,
)
from test_mlb_official_box_forward import (
    EVENT, ENTRY, SOURCE_ROW, FakeSession, csvfile,
)


class FrozenProviderEventsTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.original = {
            "player_id": "643217", "player": "Andrew Benintendi",
            "player_key": "andrewbenintendi", "team": "Chicago White Sox",
            "away_team": "Chicago White Sox",
            "home_team": "Cleveland Guardians",
            "event_id": EVENT, "start": "2026-10-05T21:00:00Z",
        }
        self.entry = dict(ENTRY, **identity.frozen_mlb_identity(self.original))
        self.archive = self.root / "mlb_live/decision/history/snapshots/fixture/MLB_PROP_CANDIDATES.csv"

    def plan(self, picks=None):
        picks = picks or [self.entry]
        return mlb.plan_mlb_settlement(
            self.root, {r["forward_key"]: r for r in picks}, FakeSession(),
        )

    def test_pregame_frozen_source_suffices_for_verified_official_game_without_archive(self):
        receipt, events = self.plan()
        self.assertEqual(receipt["status"], "READY")
        self.assertEqual(receipt["archived_provider_events"], 0)
        self.assertEqual(receipt["mapped_archived_events"], 0)
        self.assertEqual(receipt["mapped_provider_events_with_original_capture"], 1)
        self.assertEqual(receipt["frozen_event_reconciliation"][
            "provider_events_from_original_capture"], 1)
        self.assertEqual(receipt["mapped_official_events"], 1)
        self.assertEqual(receipt["official_final_games"], 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["grade"], "WIN")
        self.assertEqual(events[0]["official_game_pk"], "849834")
        self.assertEqual(events[0]["official_player_id"], "643217")
        self.assertEqual(events[0]["settlement_match_type"],
                         "MLB_FROZEN_SOURCE_PLAYER_ID_AND_OFFICIAL_FINAL_BOX")
        self.assertFalse(events[0]["platform_payout_claimed"])

    def test_snapshot_and_frozen_source_consistent_only_one_event(self):
        csvfile(self.archive, [dict(SOURCE_ROW)])
        receipt, events = self.plan()
        self.assertEqual(receipt["status"], "READY")
        self.assertEqual(receipt["archived_provider_events"], 1)
        self.assertEqual(receipt["frozen_event_reconciliation"][
            "provider_events_from_original_capture"], 0)
        self.assertEqual(receipt["frozen_event_reconciliation"][
            "provider_events_with_frozen_corroboration"], 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["player_id_provenance"],
                         "EXPLICIT_ORIGINAL_ARCHIVED_MLB_PLAYER_ID")

    def test_conflicting_snapshot_club_poison_event_not_graded(self):
        csvfile(self.archive, [dict(SOURCE_ROW, home_team="New York Yankees")])
        receipt, events = self.plan()
        self.assertEqual(receipt["status"], "READY")
        self.assertEqual(events, [])
        self.assertEqual(receipt["unmatched_events"][EVENT],
                         "AMBIGUOUS_PROVIDER_OFFICIAL_GAME")
        self.assertEqual(receipt["review_reasons"][
            "NO_UNIQUE_OFFICIAL_GAME_MAPPING"], 1)

    def test_conflicting_capture_evidence_across_same_provider_uuid_rejected(self):
        other = deepcopy(self.entry)
        other["forward_key"] = "second-entry-same-provider-game"
        other["mlb_source_home_team"] = "New York Yankees"
        receipt, results = self.plan([self.entry, other])
        self.assertEqual(receipt["status"], "READY")
        self.assertEqual(results, [])
        self.assertEqual(receipt["review_reasons"][
            "NO_UNIQUE_OFFICIAL_GAME_MAPPING"], 2)

    def test_without_snapshot_or_original_capture_identity_no_results(self):
        untagged = dict(ENTRY)
        receipt, events = self.plan([untagged])
        self.assertEqual(receipt["status"], "SOURCE_UNAVAILABLE")
        self.assertEqual(events, [])

    def test_invalid_missing_frozen_id_never_infers_identity_from_player_name(self):
        broken = dict(self.entry, mlb_source_player_id="")
        receipt, events = self.plan([broken])
        self.assertEqual(receipt["status"], "SOURCE_UNAVAILABLE")
        self.assertEqual(events, [])

    def test_wrong_frozen_clock_not_used_as_event_proof(self):
        broken = dict(self.entry, mlb_source_original_start="2026-10-06T21:00:00Z")
        receipt, events = self.plan([broken])
        self.assertEqual(receipt["status"], "SOURCE_UNAVAILABLE")
        self.assertEqual(events, [])

    def test_post_first_pitch_original_prediction_cannot_settle(self):
        after_start = dict(self.entry, captured_at="2026-10-05T21:01:00Z")
        receipt, events = self.plan([after_start])
        self.assertEqual(receipt["status"], "READY")
        self.assertEqual(events, [])
        self.assertEqual(receipt["review_reasons"][
            "NOT_VERIFIED_PREGAME_OR_START"], 1)

    def test_an_existing_conflicting_result_still_holds_entire_frozen_batch(self):
        prior = dict(self.entry, grade="LOSS", forward_key="prior-loss")
        receipt, events = self.plan([prior, self.entry])
        self.assertEqual(receipt["status"],
                         "INTEGRITY_HOLD_PREVIOUS_GRADE_CONFLICT")
        self.assertEqual(receipt["conflicting_previous_grades_count"], 1)
        self.assertEqual(events, [])

    def test_an_exactly_proven_unplayed_player_is_not_an_under_win(self):
        fake = FakeSession()
        fake.boxes["849834"]["liveData"]["boxscore"]["teams"]["away"]["batters"] = []
        receipt, events = mlb.plan_mlb_settlement(
            self.root, {self.entry["forward_key"]: self.entry}, fake,
        )
        self.assertEqual(receipt["status"], "READY")
        self.assertEqual(events, [])
        self.assertEqual(receipt["review_reasons"]["PLAYER_NOT_VERIFIED_PLAYED"], 1)


if __name__ == "__main__":
    unittest.main()
