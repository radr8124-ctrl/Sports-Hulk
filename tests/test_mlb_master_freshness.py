"""MLB master freshness: official states and historical rows are preserved."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from baseball_vault import refresh_mlb_master_status as master


def game(pk, *, status="Final", start="2026-10-05T21:00:00Z",
         away="Chicago White Sox", home="Cleveland Guardians",
         away_id=145, home_id=114, away_score=4, home_score=3,
         game_type="D"):
    return {
        "gamePk": pk, "gameDate": start, "officialDate": "2026-10-05",
        "gameType": game_type, "status": status,
        "away_team": away, "away_team_id": away_id,
        "home_team": home, "home_team_id": home_id,
        "away_score": away_score, "home_score": home_score,
        "gameNumber": 1,
    }


def baseline():
    rows = [
        {**game(849834, status="Scheduled", away_score=None, home_score=None),
         "venue": "Progressive Field", "home_days_since_last": 2,
         "away_days_since_last": 1},
        {**game(849839, start="2026-10-06T00:00:00Z",
                away="New York Yankees", home="Tampa Bay Rays",
                away_id=147, home_id=139, away_score=2, home_score=5),
         "venue": "Tropicana Field", "home_days_since_last": 4,
         "away_days_since_last": 5},
        {**game(2024001, status="Final", start="2024-04-03T16:00:00Z",
                away="Boston Red Sox", home="New York Yankees",
                away_id=111, home_id=147, game_type="R"),
         "venue": "Old Stadium", "home_days_since_last": 1,
         "away_days_since_last": 3},
    ]
    for x in rows:
        x["total_runs"] = (
            None if x["home_score"] is None else x["home_score"] + x["away_score"]
        )
        x["home_run_margin"] = (
            None if x["home_score"] is None else x["home_score"] - x["away_score"]
        )
    return pd.DataFrame(rows)


def schedule_row(item):
    return {
        "gamePk": item["gamePk"], "gameDate": item["gameDate"],
        "gameType": item["gameType"],
        "gameNumber": 1,
        "status": {"detailedState": item["status"]},
        "teams": {
            "away": {
                "team": {"id": item["away_team_id"], "name": item["away_team"]},
                "score": item["away_score"],
            },
            "home": {
                "team": {"id": item["home_team_id"], "name": item["home_team"]},
                "score": item["home_score"],
            },
        },
    }


def payload(*games):
    return {"dates": [{"date": "2026-10-05", "games": [
        schedule_row(x) for x in games
    ]}]}


class Response:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return self.content


class FakeSession:
    def __init__(self, content):
        self.content = content

    def get(self, url, *, params, timeout):
        assert url == master.SCHEDULE and params["sportId"] == 1
        assert timeout >= 10
        return Response(self.content)


class MlbMasterFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root / "baseball_vault/derived/MLB_GAME_MASTER.csv"
        self.parquet = self.file.with_suffix(".parquet")
        self.file.parent.mkdir(parents=True)
        self.frame = baseline()
        self.frame.to_csv(self.file, index=False)
        self.frame.to_parquet(self.parquet, index=False)
        self.clock = datetime(2026, 10, 7, 22, 0, tzinfo=timezone.utc)
        self.new = game(849834)

    def update(self, new=None, *, dry_run=False):
        return master.run(
            self.root, FakeSession(payload(self.new if new is None else new)),
            days_back=8, days_forward=3, clock=self.clock,
            dry_run=dry_run,
        )

    def test_updates_only_stale_completed_game(self):
        result = self.update()
        self.assertEqual(result["status"], "UPDATED")
        self.assertEqual(result["updated_game_ids"], ["849834"])
        after = pd.read_csv(self.file)
        self.assertEqual(len(after), 3)
        current = after[after.gamePk.eq(849834)].iloc[0]
        self.assertEqual(current.status, "Final")
        self.assertEqual((current.away_score, current.home_score), (4, 3))
        self.assertEqual(current.total_runs, 7)
        self.assertEqual(current.home_run_margin, -1)
        past = after[after.gamePk.eq(2024001)].iloc[0]
        self.assertEqual(past.venue, "Old Stadium")
        self.assertEqual(past.away_score, 4)
        self.assertEqual(pd.read_parquet(self.parquet).shape[0], 3)

    def test_repeat_same_status_and_score_is_idempotent(self):
        self.assertEqual(self.update()["status"], "UPDATED")
        before = self.file.read_bytes()
        repeat = self.update()
        self.assertEqual(repeat["status"], "NO_UPDATES")
        self.assertEqual(self.file.read_bytes(), before)

    def test_dry_run_has_zero_byte_changes(self):
        before = self.file.read_bytes()
        prior_parquet = self.parquet.read_bytes()
        r = self.update(dry_run=True)
        self.assertEqual(r["status"], "DRY_RUN_READY")
        self.assertEqual(self.file.read_bytes(), before)
        self.assertEqual(self.parquet.read_bytes(), prior_parquet)
        self.assertFalse((self.file.parent / "MLB_MASTER_FRESHNESS_RECEIPT.json").exists())

    def test_final_game_not_downgraded_to_pregame(self):
        r = self.update(game(849839, start="2026-10-06T00:00:00Z",
                             away="New York Yankees", home="Tampa Bay Rays",
                             away_id=147, home_id=139,
                             status="Scheduled", away_score=None, home_score=None))
        self.assertEqual(r["status"], "NO_UPDATES")
        self.assertEqual(r["held_for_review"][0]["reason"], "ATTEMPTED_OFFICIAL_STATUS_DOWNGRADE")

    def test_frozen_final_score_conflict_blocks_all_updates(self):
        o = game(849839, start="2026-10-06T00:00:00Z",
                 away="New York Yankees", home="Tampa Bay Rays",
                 away_id=147, home_id=139, away_score=9, home_score=9)
        before = self.file.read_bytes()
        r = self.update(o)
        self.assertEqual(r["status"], "INTEGRITY_HOLD")
        self.assertEqual(r["held_for_review"][0]["reason"], "CONTRADICTORY_FINAL_SCORE")
        self.assertEqual(self.file.read_bytes(), before)

    def test_team_or_game_type_mismatch_is_not_forced(self):
        for change in (
            {"away_team": "Other Team"},
            {"gameType": "R"},
            {"away_team_id": 999},
        ):
            with self.subTest(change=change):
                r = self.update(dict(self.new, **change))
                self.assertEqual(r["status"], "NO_UPDATES")
                self.assertEqual(r["held_for_review"][0]["reason"],
                                 "OFFICIAL_GAME_TEAM_OR_TYPE_CONFLICT")

    def test_rescheduled_far_start_is_reviewed(self):
        r = self.update(dict(self.new, gameDate="2026-10-06T01:30:00Z"))
        self.assertEqual(r["status"], "NO_UPDATES")
        self.assertEqual(r["held_for_review"][0]["reason"], "KICKOFF_CHANGED_BEYOND_TWO_HOURS")

    def test_unknown_official_game_never_deletes_history(self):
        r = self.update(game(999999))
        self.assertEqual(r["status"], "NO_UPDATES")
        self.assertEqual(r["new_games_not_in_cached_master"], ["999999"])
        self.assertEqual(len(pd.read_csv(self.file)), 3)

    def test_current_live_score_refresh(self):
        r = self.update(dict(self.new, status="In Progress",
                             away_score=2, home_score=0))
        self.assertEqual(r["status"], "UPDATED")
        after = pd.read_csv(self.file)
        row = after[after.gamePk.eq(849834)].iloc[0]
        self.assertEqual(row.status, "In Progress")
        self.assertEqual(row.total_runs, 2)
        self.assertEqual(row.home_run_margin, -2)
        pregame = self.update(dict(self.new, status="Pre-Game",
                                   away_score=None, home_score=None))
        self.assertEqual(pregame["status"], "NO_UPDATES")
        self.assertEqual(pregame["held_for_review"][0]["reason"],
                         "ATTEMPTED_OFFICIAL_STATUS_DOWNGRADE")

    def test_conflicting_official_duplicate_gamepk_holds(self):
        data = payload(self.new, dict(self.new, away_score=7))
        before = self.file.read_bytes()
        result = master.run(self.root, FakeSession(data), clock=self.clock)
        self.assertEqual(result["status"], "INTEGRITY_HOLD")
        self.assertEqual(self.file.read_bytes(), before)

    def test_source_missing_or_malformed_fails_closed(self):
        before = self.file.read_bytes()
        r = master.run(self.root, FakeSession({"bad": "response"}), clock=self.clock)
        self.assertEqual(r["status"], "SOURCE_UNAVAILABLE_OR_INVALID")
        self.assertEqual(self.file.read_bytes(), before)

    def test_active_season_does_not_reuse_stale_yearwide_schedule(self):
        from baseball_vault.mlb_game_master import use_finalized_cache
        yearcache = self.root / "mlb_schedule_2026.json"
        yearcache.write_text("{}")
        self.assertFalse(use_finalized_cache(2026, yearcache, self.clock))

    def test_prior_season_finalized_cache_is_safe_to_reuse(self):
        import os
        from datetime import datetime, timezone
        from baseball_vault.mlb_game_master import use_finalized_cache
        cache = self.root / "mlb_schedule_2025.json"
        cache.write_text("{}")
        os.utime(cache, (datetime(2026, 1, 5, tzinfo=timezone.utc).timestamp(),) * 2)
        self.assertTrue(use_finalized_cache(2025, cache, self.clock))
        os.utime(cache, (datetime(2025, 10, 3, tzinfo=timezone.utc).timestamp(),) * 2)
        self.assertFalse(use_finalized_cache(2025, cache, self.clock))

    def test_master_missing_duplicate_id_fails_closed(self):
        d = baseline()
        d.loc[1, "gamePk"] = 849834
        with self.assertRaises(ValueError):
            master.update_frame(d, {"849834": self.new})


if __name__ == "__main__":
    unittest.main()
