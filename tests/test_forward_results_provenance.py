"""Cross-sport forward settlement and accountability acceptance tests."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from intelligence_warehouse.betting_v2 import build_prop_v2_forward as props
from intelligence_warehouse.betting_v2 import build_betting_v2_all_markets_forward as games
from intelligence_warehouse.betting_v2 import build_parlay_v2_forward as parlays
from intelligence_warehouse.betting_v2.forward_result_evidence import register_evidence, trusted_result
from intelligence_warehouse.betting_v2.forward_results_audit import (
    audit_forward_ledgers, canonical_ledger, summarize, event_start,
)


def prop_entry(*, sport="MLB", event="provider-event-42",
               game_key="", market="PLAYER_TOTAL_HITS",
               event_start="2026-10-05T21:00:00+00:00"):
    return {
        "forward_key": "frozen-entry-1",
        "model_version": "PROP_V2_2026",
        "sport": sport, "lane": "PROP",
        "event_id": event, "game_key": game_key,
        "event_start": event_start,
        "player_key": "johndoe", "market": market,
        "side": "OVER", "line": "0.5", "grade": "PENDING",
    }


def match_row(entry, *, grade="WIN", source_event=None, game_key=None):
    return {
        "grade": grade,
        "source_event_id": entry["event_id"] if source_event is None else source_event,
        "game_key": entry["game_key"] if game_key is None else game_key,
        "actual_value": 2,
        "grade_snapshot_at": "2026-10-06T03:00:00Z",
    }


class EvidenceTests(unittest.TestCase):
    def test_same_verified_grade_keeps_latest_and_most_complete_source(self):
        doc = {}
        register_evidence(doc, "event|a", {"grade": "WIN", "actual_value": None})
        register_evidence(doc, "event|a", {"grade": "WIN", "actual_value": 2})
        self.assertTrue(trusted_result(doc["event|a"]))
        self.assertEqual(doc["event|a"]["actual_value"], 2)

    def test_changed_grade_quarantines_and_cannot_be_unpoisoned(self):
        doc = {}
        register_evidence(doc, "event|a", {"grade": "WIN", "actual_value": 2})
        register_evidence(doc, "event|a", {"grade": "LOSS", "actual_value": 2})
        register_evidence(doc, "event|a", {"grade": "WIN", "actual_value": 2})
        self.assertFalse(trusted_result(doc["event|a"]))
        self.assertIn("CONFLICTING_GRADES", doc["event|a"]["reason"])

    def test_same_grade_but_different_official_scores_blocks_settlement(self):
        doc = {}
        register_evidence(doc, "game|a", {"grade": "WIN", "home_score": 122, "away_score": 120})
        register_evidence(doc, "game|a", {"grade": "WIN", "home_score": 125, "away_score": 120})
        self.assertFalse(trusted_result(doc["game|a"]))
        self.assertIn("CONFLICTING_HOME_SCORE", doc["game|a"]["reason"])

    def test_one_provider_event_cannot_claim_two_different_games(self):
        lookup = {}
        register_evidence(lookup, "event|x", {
            "grade": "WIN", "game_key": "2026-10-05|A|B",
        })
        register_evidence(lookup, "event|x", {
            "grade": "WIN", "game_key": "2026-10-05|C|D",
        })
        self.assertFalse(trusted_result(lookup["event|x"]))
        self.assertIn("CONFLICTING_GAME_KEY", lookup["event|x"]["reason"])

    def test_parlay_component_grade_conflict_blocks_settlement(self):
        doc = {}
        register_evidence(doc, "combo", {"grade": "WIN", "leg1_grade": "WIN"})
        register_evidence(doc, "combo", {"grade": "WIN", "leg1_grade": "LOSS"})
        self.assertFalse(trusted_result(doc["combo"]))
        self.assertIn("CONFLICTING_LEG1_GRADE", doc["combo"]["reason"])

    def test_cross_game_event_id_conflict_blocks_settlement(self):
        doc = {}
        register_evidence(doc, "game|a", {"grade": "WIN", "source_event_id": "1"})
        register_evidence(doc, "game|a", {"grade": "WIN", "source_event_id": "2"})
        self.assertFalse(trusted_result(doc["game|a"]))
        self.assertIn("CONFLICTING_SOURCE_EVENT_ID", doc["game|a"]["reason"])


class PropSettlementTests(unittest.TestCase):
    def settlement(self, entry, lookup):
        out = []
        with patch.object(props, "canonical", return_value={entry["forward_key"]: entry}), \
             patch.object(props, "grade_lookup", return_value=lookup), \
             patch.object(props, "append_jsonl", side_effect=lambda path, event: out.append(event)):
            n = props.settle()
        return n, out

    def test_frozen_entry_uses_legacy_market_field(self):
        row = prop_entry()
        self.assertIn("PLAYER_TOTAL_HITS", props.identity_keys(row)[0])
        self.assertIn("market", props.identity_parts(row))
        self.assertEqual(props.identity_parts(row)["market"], "PLAYER_TOTAL_HITS")

    def test_current_and_frozen_market_form_same_forward_key(self):
        current = {**prop_entry(), "market_subtype": "PLAYER_TOTAL_HITS", "market": ""}
        frozen = props.identity_parts(current)
        self.assertEqual(props.identity_keys(current), props.identity_keys(frozen))
        self.assertEqual(props.primary_key(current), props.primary_key(frozen))

    def test_exact_event_verified_across_three_sports(self):
        for sport in ("NFL", "MLB", "NHL"):
            with self.subTest(sport=sport):
                entry = prop_entry(sport=sport)
                match = match_row(entry)
                n, rows = self.settlement(entry, {props.identity_keys(entry)[0]: match})
                self.assertEqual(n, 1)
                self.assertEqual(rows[0]["grade"], "WIN")
                self.assertEqual(rows[0]["settlement_match_type"], "event")
                self.assertEqual(rows[0]["forward_key"], "frozen-entry-1")

    def test_no_date_only_grade_even_if_player_line_matches(self):
        entry = prop_entry()
        date_key = next(k for k in props.identity_keys(entry) if k.startswith("date|"))
        n, rows = self.settlement(entry, {date_key: match_row(entry)})
        self.assertEqual((n, rows), (0, []))

    def test_event_match_with_conflicting_game_is_blocked(self):
        entry = prop_entry(game_key="2026-10-05|NYM|MIA")
        key = props.identity_keys(entry)[0]
        n, rows = self.settlement(
            entry, {key: match_row(entry, game_key="2026-10-05|NYY|BOS")}
        )
        self.assertEqual((n, rows), (0, []))

    def test_conflicting_event_ids_block_game_fallback(self):
        entry = prop_entry(game_key="2026-10-05|NYM|MIA")
        game_key = next(k for k in props.identity_keys(entry) if k.startswith("game|"))
        n, rows = self.settlement(entry, {
            game_key: match_row(entry, source_event="another-event")
        })
        self.assertEqual((n, rows), (0, []))

    def test_missing_source_event_id_can_fall_back_to_full_game_key(self):
        entry = prop_entry(event="", game_key="2026-10-05|NYM|MIA")
        game_key = next(k for k in props.identity_keys(entry) if k.startswith("game|"))
        n, rows = self.settlement(entry, {
            game_key: match_row(entry, source_event="")
        })
        self.assertEqual(n, 1)
        self.assertEqual(rows[0]["settlement_match_type"], "game")

    def test_poisoned_event_id_can_not_fall_back(self):
        entry = prop_entry(game_key="2026-10-05|NYM|MIA")
        keys = props.identity_keys(entry)
        n, rows = self.settlement(entry, {
            keys[0]: {"ambiguous": True, "reason": "CONFLICTING_GRADES"},
            keys[1]: match_row(entry),
        })
        self.assertEqual((n, rows), (0, []))

    def test_already_settled_does_not_append_duplicate(self):
        entry = {**prop_entry(), "grade": "WIN", "status": "SETTLED"}
        n, rows = self.settlement(entry, {props.identity_keys(entry)[0]: match_row(entry)})
        self.assertEqual((n, rows), (0, []))


class OtherSettlementTests(unittest.TestCase):
    def test_ambiguous_game_result_does_not_settle(self):
        entry = {
            "sport": "MLB", "game_key": "2026-10-05|NYM|MIA",
            "market": "MONEYLINE", "selection": "NYM",
            "line": None, "grade": "PENDING", "forward_key": "a",
        }
        with patch.object(games, "canonical", return_value={"a": entry}), \
             patch.object(games, "history_lookup", return_value={
                 "MLB|2026-10-05|NYM|MIA|MONEYLINE|nym|": {
                     "ambiguous": True, "reason": "CONFLICTING_GRADES",
                 }
             }), patch.object(games, "append_jsonl") as append:
            self.assertEqual(games.settle(), 0)
            append.assert_not_called()

    def test_ambiguous_parlay_result_does_not_settle(self):
        entry = {"sport": "NBA", "combo_signature": "combo-1",
                 "grade": "PENDING", "forward_key": "a"}
        with patch.object(parlays, "canonical", return_value={"a": entry}), \
             patch.object(parlays, "result_lookup", return_value={
                 ("NBA", "combo-1"): {"ambiguous": True}
             }), patch.object(parlays, "append_jsonl") as append:
            self.assertEqual(parlays.settle(), 0)
            append.assert_not_called()


class AccountabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.out = self.root / "intelligence_warehouse" / "betting_v2"
        self.out.mkdir(parents=True)
        self.clock = datetime(2026, 10, 7, 20, 0, tzinfo=timezone.utc)

    def write(self, name, events):
        (self.out / name).write_text("".join(
            json.dumps(item) + "\n" for item in events
        ))

    def test_pending_is_not_loss_and_parlay_last_leg_controls_overdue(self):
        pending = {"grade": "PENDING", "event_start": "2026-10-05T12:00:00Z"}
        summary = summarize([pending], "PROPS", self.clock)
        self.assertEqual(summary["pending_overdue_48h"], 1)
        self.assertEqual(summary["losses"], 0)
        parlay = {"grade": "PENDING", "legs": [
            {"source_event_start": "2026-10-04T12:00:00Z"},
            {"source_event_start": "2026-10-09T12:00:00Z"},
        ]}
        result = summarize([parlay], "PARLAYS", self.clock)
        self.assertEqual(result["pending_overdue_12h"], 0)
        self.assertEqual(result["pending_future_or_grace"], 1)

    def test_unverified_leg_time_never_marks_parlay_overdue(self):
        parlay = {"grade": "PENDING", "first_leg_start": "2026-10-04T12:00:00Z",
                  "legs": [{"source_event_start": "2026-10-04T12:00:00Z"}, {}]}
        self.assertIsNone(event_start(parlay, "PARLAYS"))
        report = summarize([parlay], "PARLAYS", self.clock)
        self.assertEqual(report["pending_missing_verified_start"], 1)
        self.assertEqual(report["pending_overdue_12h"], 0)

    def test_orphan_settled_event_cannot_invent_a_win(self):
        name = "PROP_V2_FORWARD_LEDGER.jsonl"
        self.write(name, [
            {"event_type": "SETTLED", "forward_key": "fake", "grade": "WIN"},
            {"event_type": "ENTRY", "forward_key": "real", "grade": "PENDING"},
        ])
        entries, state = canonical_ledger(self.out / name)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries["real"]["grade"], "PENDING")
        self.assertEqual(state["issues"]["ORPHAN_EVENT"], 1)

    def test_contradictory_settlements_do_not_change_frozen_result(self):
        name = "PROP_V2_FORWARD_LEDGER.jsonl"
        self.write(name, [
            {"event_type": "ENTRY", "forward_key": "a", "grade": "PENDING"},
            {"event_type": "SETTLED", "forward_key": "a", "grade": "WIN"},
            {"event_type": "SETTLED", "forward_key": "a", "grade": "LOSS"},
        ])
        entries, state = canonical_ledger(self.out / name)
        self.assertEqual(entries["a"]["grade"], "WIN")
        self.assertEqual(state["issues"]["CONFLICTING_SETTLEMENT"], 1)

    def test_all_sports_always_visible_with_distinct_families(self):
        self.write("PROP_V2_FORWARD_LEDGER.jsonl", [{
            "event_type": "ENTRY", "forward_key": "mlb-prop",
            "grade": "PENDING", "sport": "MLB",
            "event_start": "2026-10-05T12:00:00Z",
        }])
        report = audit_forward_ledgers(self.root, at=self.clock)
        self.assertEqual(set(report["by_sport"]), {"NFL","CFB","CBB","MLB","NBA","NHL"})
        self.assertEqual(report["by_sport"]["CBB"]["PROPS"]["status"], "NO_FORWARD_ENTRIES")
        self.assertEqual(report["by_sport"]["MLB"]["PROPS"]["pending_overdue_12h"], 1)
        self.assertEqual(report["by_sport"]["MLB"]["PROPS"]["losses"], 0)
        self.assertEqual(report["summary"]["pending_overdue_12h"], 1)
        self.assertFalse(report["rules"]["auto_model_promotion"])


if __name__ == "__main__":
    unittest.main()
