import unittest
from datetime import datetime, timezone
from dfs_timing_evidence import slate_timing_evidence

NOW = datetime(2026, 10, 11, 18, 30, tzinfo=timezone.utc)
def row(time, slate="a"):
    return {"slate_id": slate, "game_time": time}

class TimingEvidenceTests(unittest.TestCase):
    def test_future_times_are_observed_without_claiming_entry_or_late_swap(self):
        out = slate_timing_evidence([row("2026-10-11T20:00:00Z")], "a", NOW)
        self.assertEqual(out["status"], "PREGAME_TIMES_OBSERVED")
        self.assertFalse(out["contest_entry_verified"])
        self.assertFalse(out["late_swap_verified"])

    def test_exact_kickoff_and_earlier_times_are_started(self):
        for value in ["2026-10-11T18:30:00Z", "2026-10-11T13:00:00-04:00"]:
            self.assertEqual(slate_timing_evidence([row(value)], "a", NOW)["status"], "SLATE_STARTED")

    def test_missing_invalid_and_naive_times_are_unverified(self):
        for value in [None, "", "invalid", "2026-10-11T20:00:00"]:
            self.assertEqual(slate_timing_evidence([row(value)], "a", NOW)["status"], "GAME_TIMES_UNVERIFIED")

    def test_any_missing_row_prevents_pregame_claim(self):
        out = slate_timing_evidence([row("2026-10-11T20:00:00Z"), row(None)], "a", NOW)
        self.assertEqual(out["status"], "GAME_TIMES_UNVERIFIED")
        self.assertEqual(out["missing_game_time_rows"], 1)

    def test_other_slates_cannot_change_selected_timing(self):
        out = slate_timing_evidence([row("2026-10-11T20:00:00Z"), row("2026-10-11T17:00:00Z", "b")], "a", NOW)
        self.assertEqual(out["status"], "PREGAME_TIMES_OBSERVED")
        self.assertEqual(out["rows_checked"], 1)
        self.assertEqual(slate_timing_evidence([], "a", NOW)["status"], "GAME_TIMES_UNVERIFIED")

    def test_naive_clock_is_rejected(self):
        with self.assertRaises(ValueError):
            slate_timing_evidence([], "a", datetime(2026, 10, 11, 18, 30))

if __name__ == "__main__":
    unittest.main()
