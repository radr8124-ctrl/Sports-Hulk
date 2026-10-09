"""Source-replay controls for NFL research-only bookmaker snapshots."""
import csv
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from nfl_live.game_fusion.build_nfl_research_book_refs import (
    archived_capture, quote_is_recent, research_payload, run,
)

BASE = datetime(2026, 10, 9, 20, 0, tzinfo=timezone.utc)
START = BASE + timedelta(days=2)
CAPTURE = BASE - timedelta(hours=14)


def row(market="MONEYLINE", side="HOME", *, book="fanduel",
        line="", price="-120", updated=None, event_id="original-sw-id"):
    return {
        "provider": "sportwizzard", "sportsbook": book, "event_id": event_id,
        "game_key": "PHI@JAX", "away_team": "Philadelphia Eagles",
        "home_team": "Jacksonville Jaguars", "away_abbr": "PHI", "home_abbr": "JAX",
        "start": START.isoformat(), "market": market,
        "market_subtype": "TOTAL_POINTS" if market == "TOTAL" else market,
        "side": side if market == "TOTAL" else side,
        "team_side": "" if market == "TOTAL" else side,
        "line": line, "price_american": price,
        "updated": (updated or (CAPTURE - timedelta(minutes=1))).isoformat(),
    }


def complete_rows():
    return [
        row(side="HOME", price="-120"), row(side="AWAY", price="+105"),
        row("SPREAD", "HOME", line="-1.5", price="-110"),
        row("SPREAD", "AWAY", line="1.5", price="-110"),
        row("TOTAL", "OVER", line="42.5", price="-110"),
        row("TOTAL", "UNDER", line="42.5", price="-110"),
    ]


def score():
    return {"next_games": [{
        "event_id": "espn-original-id", "start_time": START.isoformat(),
        "away_abbr": "PHI", "home_abbr": "JAC"
    }]}


def payload(rows, official=None, capture=CAPTURE, at=BASE):
    return research_payload(rows, score() if official is None else official,
                            capture, {"archive": "source.csv", "sha256": "sourcehash"}, at)


class NflResearchBookSourceTests(unittest.TestCase):
    def test_unique_same_book_source_observations_generate_only_research(self):
        p = payload(complete_rows())
        self.assertEqual(p["paired_quote_games"], 1)
        self.assertEqual(p["paired_market_counts"], {"MONEYLINE": 1, "SPREAD": 1, "TOTAL": 1})
        f = p["fixtures"][0]
        self.assertEqual(f["official_espn_event_id"], "espn-original-id")
        self.assertEqual(f["game_key"], "PHI@JAX")
        self.assertFalse(f["approved_play"])
        self.assertFalse(p["model_advantage_proven"])
        for m in f["markets"].values():
            self.assertFalse(m["is_verified_main_line"])
            self.assertFalse(m["is_executable_current_offer"])
            self.assertFalse(m["is_approved_bet"])
            self.assertEqual(m["source_event_id"], "original-sw-id")

    def test_price_sides_are_not_inferred(self):
        p = payload([r for r in complete_rows() if r["team_side"] != "AWAY" and r["side"] != "UNDER"])
        self.assertEqual(p["paired_quote_games"], 0)

    def test_conflicting_same_book_prices_block_only_affected_market(self):
        rows = complete_rows()
        rows.append(dict(rows[0], price_american="-145"))
        p = payload(rows)
        self.assertEqual(p["paired_market_counts"], {"SPREAD": 1, "TOTAL": 1})
        self.assertNotIn("MONEYLINE", p["fixtures"][0]["markets"])

    def test_multiple_plausible_spread_lines_fail_closed_not_guess_mainline(self):
        rows = complete_rows()
        rows.extend([row("SPREAD", "HOME", line="-2.5", price="-111"),
                     row("SPREAD", "AWAY", line="2.5", price="-109")])
        p = payload(rows)
        self.assertNotIn("SPREAD", p["fixtures"][0]["markets"])
        self.assertFalse(p["main_line_verified"])

    def test_unpaired_alternative_extreme_prices_are_never_substituted(self):
        rows = complete_rows()
        rows = [r for r in rows if r["market"] == "MONEYLINE"]
        rows.extend([row("SPREAD", "HOME", line="-15.5", price="-1500"),
                     row("SPREAD", "AWAY", line="15.5", price="+700")])
        self.assertNotIn("SPREAD", payload(rows)["fixtures"][0]["markets"])

    def test_original_event_and_kickoff_must_be_unambiguous(self):
        for bad in (
            [dict(x, game_key="PHI@NYG") for x in complete_rows()],
            [dict(x, home_abbr="NYG") for x in complete_rows()],
            [dict(x, start=(START + timedelta(hours=1)).isoformat()) for x in complete_rows()],
            complete_rows() + [row(event_id="different-original-event")],
        ):
            self.assertEqual(payload(bad)["paired_quote_games"], 0)

    def test_unknown_official_game_or_duplicate_official_id_fails(self):
        self.assertEqual(payload(complete_rows(), official={"next_games": []})["paired_quote_games"], 0)
        duplicate = score()
        duplicate["next_games"].append(dict(duplicate["next_games"][0], event_id="other-espn-id"))
        self.assertEqual(payload(complete_rows(), official=duplicate)["paired_quote_games"], 0)

    def test_timestamp_and_future_rule_are_strict(self):
        ref = payload(complete_rows())["fixtures"][0]["markets"]["MONEYLINE"]
        self.assertTrue(quote_is_recent(ref, START.isoformat(), BASE))
        self.assertFalse(quote_is_recent(ref, START.isoformat(), START))
        self.assertFalse(quote_is_recent(ref, START.isoformat(), BASE + timedelta(hours=12)))
        self.assertFalse(quote_is_recent(dict(ref, source_captured_at=(BASE + timedelta(hours=1)).isoformat()),
                                         START.isoformat(), BASE))
        self.assertEqual(payload(complete_rows(), at=START)["paired_quote_games"], 0)

    def test_provider_timestamp_must_not_follow_collector(self):
        rows = [dict(x, updated=(CAPTURE + timedelta(minutes=30)).isoformat()) for x in complete_rows()]
        self.assertEqual(payload(rows)["paired_quote_games"], 0)

    def test_expired_current_prices_remain_separate_as_historical_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "nfl_live/game_fusion/NFL_GAME_SPORTWIZZARD_RAW.csv"
            source.parent.mkdir(parents=True)
            archive = source.parent / "history/NFL_GAME_SPORTWIZZARD_20261009T060000Z.csv"
            archive.parent.mkdir(parents=True)
            with source.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(complete_rows()[0]))
                writer.writeheader()
                writer.writerows(complete_rows())
            archive.write_bytes(source.read_bytes())
            official = root / "commercial_web/public/nfl_scores.json"
            official.parent.mkdir(parents=True)
            official.write_text(json.dumps(score()))
            # Less than 24h to game, 39h after the original quote:
            # absolutely no live source candidate may survive.
            day_after = BASE + timedelta(hours=25)
            expired = run(root, now=day_after)
            self.assertEqual(expired["paired_quote_games"], 0)
            self.assertEqual(expired["fixtures"], [])
            archived = expired["archived_snapshot"]
            self.assertEqual(archived["status"], "ARCHIVED_SOURCE_ONLY_NOT_CURRENT")
            self.assertEqual(archived["paired_quote_games_at_capture"], 1)
            self.assertEqual(len(archived["fixtures"]), 1)
            self.assertFalse(archived["is_current_quote"])
            self.assertFalse(archived["is_approved_bet"])
            self.assertFalse(archived["model_advantage_proven"])
            self.assertEqual(archived["original_archive_sha256"],
                             hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(
                json.loads((root/"commercial_web/public/nfl_research_book_refs.json").read_text()),
                expired,
            )

    def test_original_archive_checksum_controls_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = root/"nfl_live/game_fusion"
            (files/"history").mkdir(parents=True)
            original = files/"NFL_GAME_SPORTWIZZARD_RAW.csv"
            archive = files/"history/NFL_GAME_SPORTWIZZARD_20261009T060000Z.csv"
            with original.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(complete_rows()[0]))
                writer.writeheader();writer.writerows(complete_rows())
            archive.write_bytes(original.read_bytes())
            when, source = archived_capture(root, original)
            self.assertIsNotNone(when)
            self.assertEqual(source["sha256"], hashlib.sha256(original.read_bytes()).hexdigest())
            score_file = root/"commercial_web/public/nfl_scores.json"
            score_file.parent.mkdir(parents=True)
            score_file.write_text(json.dumps(score()))
            result = run(root, now=BASE)
            self.assertEqual(result["paired_quote_games"], 1)
            public = root/"commercial_web/public/nfl_research_book_refs.json"
            before = public.read_bytes()
            original.write_text("tampered source, no longer SHA-equal")
            with self.assertRaises(RuntimeError):
                run(root, now=BASE)
            self.assertEqual(before, public.read_bytes())

if __name__ == "__main__":
    unittest.main()
