"""MLB player IDs are frozen at capture and checked against final boxes."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from intelligence_warehouse.betting_v2 import (
    mlb_forward_capture_identity as identity,
    build_prop_v2_forward as forward,
    build_prop_v2 as builder,
    mlb_official_box_forward as mlb,
)
from test_mlb_official_box_forward import (
    EVENT, ENTRY, SOURCE_ROW, FakeSession, csvfile,
)


def decision(**changes):
    row = {
        "sport": "MLB", "event_id": EVENT,
        "player": "Andrew Benintendi",
        "player_key": "andrewbenintendi",
        "player_id": 643217,
        "team": "Chicago White Sox",
        "away_team": "Chicago White Sox",
        "home_team": "Cleveland Guardians",
        "start": "2026-10-05T21:00:00Z",
    }
    row.update(changes)
    return row


def picked(**changes):
    source = decision()
    row = {
        "model_version": "MODEL_UNCHANGED",
        "sport": "MLB", "lane": "PROP",
        "lane_key": "MLB_PROP",
        "event_id": EVENT,
        "event_start": "2026-10-05T21:00:00Z",
        "player": source["player"],
        "player_key": source["player_key"],
        "market_subtype": "PLAYER_TOTAL_HITS",
        "line": 1.5, "side": "OVER",
        "shadow_decision": "PASS",
    }
    row.update(identity.frozen_mlb_identity(source))
    row.update(changes)
    return row


class MlbCaptureIdentityTests(unittest.TestCase):
    def test_all_original_decision_identity_fields_are_frozen(self):
        frozen = identity.frozen_mlb_identity(decision())
        self.assertEqual(frozen["mlb_source_player_id"], "643217")
        self.assertEqual(frozen["mlb_source_player_name"], "Andrew Benintendi")
        self.assertEqual(frozen["mlb_source_player_team"], "Chicago White Sox")
        self.assertEqual(frozen["mlb_source_home_team"], "Cleveland Guardians")
        self.assertEqual(frozen["mlb_source_identity_provenance"], identity.IDENTITY_PROVENANCE)
        self.assertFalse(frozen["mlb_source_box_verified_at_capture"])
        self.assertFalse(frozen["mlb_source_platform_payout_claimed"])

    def test_integer_float_and_numeric_string_ids_canonical(self):
        for value in (643217, 643217.0, "643217.0", "643217"):
            with self.subTest(value=value):
                self.assertEqual(identity.frozen_mlb_identity(decision(player_id=value))["mlb_source_player_id"], "643217")

    def test_invalid_id_or_mismatched_original_club_rejected(self):
        for changes in (
            {"player_id": "uuid-not-official"},
            {"player_id": None},
            {"player": "Another Batter"},
            {"player_key": "anotherplayer"},
            {"team": "Boston Red Sox"},
            {"away_team": "Cleveland Guardians"},
            {"home_team": "Chicago White Sox"},
            {"start": ""},
            {"event_id": ""},
        ):
            with self.subTest(changes=changes):
                self.assertEqual(identity.frozen_mlb_identity(decision(**changes)), {})

    def test_original_start_must_equal_frozen_pick_start(self):
        row = picked(event_start="2026-10-05T21:30:00Z")
        self.assertEqual(identity.frozen_mlb_identity(row), {})
        row = picked(mlb_source_original_start="2026-10-05T21:30:00Z")
        self.assertEqual(identity.frozen_mlb_identity(row), {})

    def test_forged_provenance_rejected(self):
        self.assertEqual(
            identity.frozen_mlb_identity(picked(
                mlb_source_identity_provenance="INFERRED_BY_NAME"
            )), {},
        )

    def test_legitimate_future_mlb_candidate_will_keep_unchanged_frozen_key(self):
        before = forward.primary_key(picked())
        row = picked()
        row["mlb_source_player_id"] = "999999"
        self.assertEqual(forward.primary_key(row), before)
        self.assertEqual(forward.identity_parts(row)["player_key"], "andrewbenintendi")

    def test_capture_writes_player_ids_only_when_valid_and_never_rewrites_old(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            current = base / "current.json"
            ledger = base / "forward.jsonl"
            valid = picked()
            invalid = picked(
                player_key="another", event_id="another-game",
                mlb_source_player_id="not-numeric",
            )
            current.write_text(json.dumps({
                "status": "READY", "model_version": "MODEL_UNCHANGED",
                "picks": [valid, invalid],
            }))
            with patch.object(forward, "CURRENT", current), \
                 patch.object(forward, "LEDGER", ledger), \
                 patch.object(forward, "now", return_value=datetime(2026, 10, 5, 12, tzinfo=timezone.utc)), \
                 patch.object(forward, "now_iso", return_value="2026-10-05T12:00:00Z"):
                before = forward.capture()
                self.assertEqual(before["entries_added"], 2)
                raw = ledger.read_bytes()
                entries = list(forward.canonical().values())
                self.assertEqual(len(entries), 2)
                a = next(r for r in entries if r["forward_key"] == forward.primary_key(valid))
                b = next(r for r in entries if r["forward_key"] == forward.primary_key(invalid))
                self.assertEqual(a["mlb_source_player_id"], "643217")
                self.assertEqual(a["mlb_source_identity_provenance"], identity.IDENTITY_PROVENANCE)
                self.assertNotIn("mlb_source_player_id", b)
                self.assertEqual(a["grade"], "PENDING")
                self.assertEqual(a["model_version"], "MODEL_UNCHANGED")
                again = forward.capture()
                self.assertEqual(again["entries_added"], 0)
                self.assertEqual(raw, ledger.read_bytes())

    def test_actual_prop_v2_builder_emits_original_id_without_changing_model(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "single-mlb-source.csv"
            data = {
                **decision(start="2099-10-08T00:00:00Z"),
                "market_subtype": "PLAYER_TOTAL_HITS",
                "side": "OVER", "line": 1.5,
                "decision": "HIGH_JUICE",
                "evidence_score": 94,
                "median_price_american": 140,
                "sportsbook_count": 3,
                "recent_games": 8,
                "season_games": 145,
                "recent_edge": 0.1,
                "season_edge": 0.1,
                "normalized_recent_edge": 0.2,
            }
            pd.DataFrame([data]).to_csv(file, index=False)
            config = dict(builder.LANES["MLB_PROP"], current=file)
            with patch.object(builder, "devig_data", return_value={}), \
                 patch.object(builder, "segment_data", return_value={}):
                rows = builder.build_current_lane(
                    "MLB_PROP", config, {"status": "INSUFFICIENT_HISTORY"},
                )
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["mlb_source_player_id"], "643217")
            self.assertEqual(row["mlb_source_away_team"], "Chicago White Sox")
            self.assertEqual(row["mlb_source_home_team"], "Cleveland Guardians")
            self.assertEqual(row["model_version"], builder.MODEL_VERSION)
            self.assertEqual(row["shadow_decision"], "PASS_INSUFFICIENT_HISTORY")
            self.assertFalse(row["live_pick_changed"])
            self.assertEqual(row["player_key"], "andrewbenintendi")
            self.assertEqual(row["event_id"], EVENT)

    def test_no_metadata_added_to_non_mlb_forward_picks(self):
        fake = picked(sport="NHL", lane_key="NHL_PROP")
        with tempfile.TemporaryDirectory() as folder:
            current = Path(folder)/"current.json"
            ledger = Path(folder)/"ledger.jsonl"
            current.write_text(json.dumps({"status": "READY", "picks": [fake]}))
            with patch.object(forward, "CURRENT", current), \
                 patch.object(forward, "LEDGER", ledger), \
                 patch.object(forward, "now", return_value=datetime(2026, 10, 5, 12, tzinfo=timezone.utc)):
                self.assertEqual(forward.capture()["entries_added"], 1)
                self.assertNotIn("mlb_source_player_id", list(forward.canonical().values())[0])


class FrozenMlbSettlementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.archived = self.root / "mlb_live/decision/history/snapshots/20261005T180000Z_a/MLB_PROP_CANDIDATES.csv"
        csvfile(self.archived, [dict(SOURCE_ROW, player_id="")])
        self.entry = dict(ENTRY, **identity.frozen_mlb_identity(decision()))

    def plan(self, entry=None, archive=None):
        if archive is not None:
            csvfile(self.archived, archive)
        row = self.entry if entry is None else entry
        return mlb.plan_mlb_settlement(self.root, {row["forward_key"]: row}, FakeSession())

    def test_frozen_original_id_matches_true_final_official_box_even_without_other_history(self):
        result, events = self.plan()
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["verified_new"], 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["grade"], "WIN")
        self.assertEqual(events[0]["official_player_id"], "643217")
        self.assertEqual(events[0]["settlement_match_type"], "MLB_FROZEN_SOURCE_PLAYER_ID_AND_OFFICIAL_FINAL_BOX")
        self.assertEqual(events[0]["player_id_provenance"], "FROZEN_MLB_DECISION_EXPLICIT_ID_AND_OFFICIAL_FINAL_BOX")

    def test_archived_official_id_disagreement_fails_closed(self):
        receipt, events = self.plan(archive=[dict(SOURCE_ROW, player_id="999999")])
        self.assertEqual(events, [])
        self.assertEqual(receipt["review_reasons"]["FROZEN_ID_CONFLICTS_WITH_ARCHIVED_PLAYER_ID"], 1)

    def test_frozen_team_opponent_pair_must_match_official_game(self):
        receipt, events = self.plan(dict(self.entry, mlb_source_home_team="Boston Red Sox"))
        self.assertEqual(events, [])
        # Conflicting archived and captured opponent pairs now poison the
        # provider event BEFORE any official game or player result is graded.
        self.assertEqual(receipt["review_reasons"]["NO_UNIQUE_OFFICIAL_GAME_MAPPING"], 1)

    def test_modified_frozen_id_without_valid_source_is_rejected(self):
        receipt, events = self.plan(dict(self.entry, mlb_source_player_id="wrong-player-id"))
        self.assertEqual(events, [])
        self.assertEqual(receipt["review_reasons"]["INVALID_FROZEN_OFFICIAL_PLAYER_ID_EVIDENCE"], 1)

    def test_valid_other_player_id_not_in_official_box_stays_pending(self):
        record = dict(self.entry, mlb_source_player_id="999999")
        receipt, events = self.plan(record)
        self.assertEqual(events, [])
        self.assertEqual(receipt["review_reasons"]["PLAYER_MISSING_OR_DUPLICATED_IN_FINAL_BOX"], 1)

    def test_frozen_official_id_disagreeing_with_historical_id_is_quarantined(self):
        from test_mlb_official_box_forward import BOX, SCHEDULE
        game_events = mlb.read_schedule(SCHEDULE)
        mapped, errors = mlb.map_official_games({
            EVENT: {("chicagowhitesox", "clevelandguardians",
                     datetime(2026, 10, 5, 21, tzinfo=timezone.utc))}
        }, game_events)
        self.assertEqual(errors, {})
        match = mlb.official_box(BOX, mapped[EVENT])
        self.assertIsNotNone(match)
        resolved, reason = mlb.verify_prediction(
            self.entry,
            mapped, {}, {"849834": match},
            {("andrewbenintendi", "chicagowhitesox"): {
                "player_id": "999999",
                "earliest_official_box_date": "2026-09-01",
            }},
        )
        self.assertIsNone(resolved)
        self.assertEqual(reason, "FROZEN_ID_CONFLICTS_WITH_OFFICIAL_HISTORY")

    def test_cannot_convert_prior_loss_to_win(self):
        record = dict(self.entry, grade="LOSS")
        receipt, events = self.plan(record)
        self.assertEqual(events, [])
        self.assertEqual(receipt["status"], "INTEGRITY_HOLD_PREVIOUS_GRADE_CONFLICT")

    def test_existing_original_archived_and_matching_frozen_id_stays_same(self):
        receipt, events = self.plan(archive=[dict(SOURCE_ROW)])
        self.assertEqual(receipt["status"], "READY")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["player_id_provenance"], "EXPLICIT_ORIGINAL_ARCHIVED_MLB_PLAYER_ID")


if __name__ == "__main__":
    unittest.main()
