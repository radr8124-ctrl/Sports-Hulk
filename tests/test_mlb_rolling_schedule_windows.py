"""MLB official results stay verifiable over seasons, not just 31 days."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import unittest
import tempfile

from intelligence_warehouse.betting_v2 import mlb_official_box_forward as mlb
from test_mlb_official_box_forward import (
    BOX, ENTRY, EVENT, SCHEDULE, SOURCE_ROW, Reply, csvfile,
)


FAR_EVENT = "new-mlb-provider-uuid"
FAR_TIME = "2026-12-06T21:00:00Z"
FAR_GAMEPK = "949834"


def season_schedule():
    data = deepcopy(SCHEDULE)
    day = data["dates"][0]
    day["date"] = "2026-12-06"
    game = day["games"][0]
    game["gamePk"] = int(FAR_GAMEPK)
    game["gameDate"] = FAR_TIME
    game["status"]["detailedState"] = "Final"
    return data


def season_box():
    data = deepcopy(BOX)
    data["gameData"]["game"]["pk"] = int(FAR_GAMEPK)
    data["gameData"]["datetime"]["dateTime"] = FAR_TIME
    return data


class MultiWindowSession:
    def __init__(self, fail_second=False):
        self.fail_second = fail_second
        self.calls = []
        self.boxes = {
            "849834": deepcopy(BOX),
            FAR_GAMEPK: season_box(),
        }

    def get(self, url, *, params=None, timeout):
        self.calls.append((url, params))
        if url == mlb.SCHEDULE_URL:
            if params["startDate"] < "2026-11-01":
                return Reply(deepcopy(SCHEDULE))
            if self.fail_second:
                return Reply({"bad": "Missing actual league schedule dates"})
            return Reply(season_schedule())
        game_pk = url.split("/")[-3]
        if game_pk not in self.boxes:
            raise TimeoutError("Not an official fixture in the fake feed")
        return Reply(self.boxes[game_pk])


class RollingMlbWindowsTests(unittest.TestCase):
    def historical_fixture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        archive = root / "mlb_live/decision/history/snapshots/20261005T180000Z_fixture/MLB_PROP_CANDIDATES.csv"
        csvfile(archive, [
            dict(SOURCE_ROW),
            dict(SOURCE_ROW, event_id=FAR_EVENT,
                 start="2026-12-06 21:00:00+00:00"),
        ])
        return root, archive

    def test_one_existing_october_window_unchanged(self):
        starts = [
            datetime(2026, 10, 5, 21, tzinfo=timezone.utc),
            datetime(2026, 10, 8, 0, tzinfo=timezone.utc),
        ]
        w = mlb.schedule_windows(starts)
        self.assertEqual(w, [(date(2026, 10, 4), date(2026, 10, 9))])

    def test_wide_gap_only_fetches_relevant_windows(self):
        dates = [
            datetime(2026, 10, 5, 21, tzinfo=timezone.utc),
            datetime(2026, 12, 6, 21, tzinfo=timezone.utc),
        ]
        w = mlb.schedule_windows(dates)
        self.assertEqual(w, [
            (date(2026, 10, 4), date(2026, 10, 6)),
            (date(2026, 12, 5), date(2026, 12, 7)),
        ])
        self.assertTrue(all((b-a).days+1 <= 31 for a, b in w))

    def test_continuous_calendar_history_splits_without_dropping_days(self):
        base = datetime(2026, 9, 1, 21, tzinfo=timezone.utc)
        dates = [base + timedelta(days=i) for i in range(140)]
        windows = mlb.schedule_windows(dates)
        self.assertGreaterEqual(len(windows), 5)
        self.assertLessEqual(len(windows), 6)
        self.assertTrue(all((b-a).days+1 <= 31 for a, b in windows))
        for dt in dates:
            self.assertTrue(any(a <= dt.date() <= b for a, b in windows))

    def test_calendar_year_boundary_leap_day_and_scheduling_margin(self):
        dates = [datetime(2027, 12, 30, 23, tzinfo=timezone.utc),
                 datetime(2028, 2, 29, 0, tzinfo=timezone.utc)]
        windows = mlb.schedule_windows(dates)
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0][0], date(2027, 12, 29))
        self.assertEqual(windows[1][1], date(2028, 3, 1))

    def test_protect_official_source_budget(self):
        starts = [
            datetime(2025, 1, 1, 20, tzinfo=timezone.utc)
            + timedelta(days=33 * i)
            for i in range(49)
        ]
        with self.assertRaisesRegex(ValueError, "TOO_MANY_OFFICIAL_SCHEDULE_WINDOWS"):
            mlb.schedule_windows(starts)

    def test_same_game_returned_by_overlapping_windows_deduplicates(self):
        old = mlb.read_schedule(SCHEDULE)[0]
        games = mlb.merge_official_schedules([old, dict(old)])
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0], old)

    def test_conflicting_official_game_pk_across_windows_is_integrity_hold(self):
        old = mlb.read_schedule(SCHEDULE)[0]
        with self.assertRaisesRegex(ValueError, "CONTRADICTORY_OFFICIAL_GAMEPK"):
            mlb.merge_official_schedules([old, dict(old, home="bostonredsox")])

    def test_no_windows_when_no_known_original_times(self):
        self.assertEqual(mlb.schedule_windows([]), [])
        self.assertEqual(mlb.schedule_windows([None]), [])

    def test_full_two_period_forward_replay_uses_both_official_final_games(self):
        # Use full logic, including original source snapshots, MLB player IDs,
        # unique official gamePk, first pitch, boxscore and original line.
        root, archive = self.historical_fixture()
        first = dict(ENTRY)
        second = dict(ENTRY,
                      event_id=FAR_EVENT,
                      event_start=FAR_TIME,
                      captured_at="2026-12-05T18:00:00Z",
                      forward_key="separate-december-frozen-entry")
        fake = MultiWindowSession()
        receipt, results = mlb.plan_mlb_settlement(
            root,
            {first["forward_key"]: first, second["forward_key"]: second},
            fake,
            now=datetime(2026, 12, 7, tzinfo=timezone.utc),
        )
        self.assertEqual(receipt["status"], "READY")
        self.assertEqual(receipt["schedule_window_count"], 2)
        self.assertEqual(receipt["mapped_official_events"], 2)
        self.assertEqual(receipt["official_final_games"], 2)
        self.assertEqual(receipt["official_schedule_games"], 2)
        self.assertEqual(len(results), 2)
        self.assertEqual({r["official_game_pk"] for r in results},
                         {"849834", FAR_GAMEPK})
        self.assertEqual({r["grade"] for r in results}, {"WIN"})
        self.assertEqual(
            len([c for c in fake.calls if c[0] == mlb.SCHEDULE_URL]), 2
        )
        self.assertEqual(len([c for c in fake.calls if "/feed/live" in c[0]]), 2)

    def test_second_window_failure_stops_entire_batch(self):
        root, archive = self.historical_fixture()
        second = dict(ENTRY, event_id=FAR_EVENT, event_start=FAR_TIME,
                      captured_at="2026-12-05T18:00:00Z",
                      forward_key="december-entry")
        before = archive.read_bytes()
        receipt, result = mlb.plan_mlb_settlement(
            root, {
                ENTRY["forward_key"]: dict(ENTRY),
                second["forward_key"]: second,
            }, MultiWindowSession(fail_second=True),
        )
        self.assertEqual(receipt["status"], "SOURCE_VALIDATION_FAILED")
        self.assertEqual(result, [])
        self.assertEqual(archive.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
