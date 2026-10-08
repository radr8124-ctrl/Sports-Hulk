"""Prop V2 survives transient empty CSVs without inventing player markets."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from intelligence_warehouse.betting_v2 import build_prop_v2 as props


class LiveDecisionSourceStabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "live-decisions.csv"
        self.path.write_text("player,score\nBen Rice,94\n")

    def test_complete_live_source_is_read_without_retries(self):
        with patch.object(props.time, "sleep") as wait:
            frame = props.read_stable_live_decisions(self.path, attempts=5, delay=0)
        self.assertEqual(frame.loc[0, "player"], "Ben Rice")
        wait.assert_not_called()

    def test_transient_empty_csv_retries_until_data_returns(self):
        real = props.pd.read_csv
        readings = [
            pd.errors.EmptyDataError("temporarily truncated"),
            pd.errors.EmptyDataError("writer still active"),
        ]
        def reader(path, **kwargs):
            if readings:
                raise readings.pop(0)
            return real(path, **kwargs)
        with patch.object(props.pd, "read_csv", side_effect=reader) as read, \
             patch.object(props.time, "sleep") as wait:
            frame = props.read_stable_live_decisions(
                self.path, attempts=5, delay=0.1
            )
        self.assertEqual(frame.loc[0, "player"], "Ben Rice")
        self.assertEqual(read.call_count, 3)
        self.assertEqual(wait.call_count, 2)

    def test_fails_closed_after_exhausted_attempts(self):
        with patch.object(props.pd, "read_csv",
                          side_effect=pd.errors.EmptyDataError("still empty")), \
             patch.object(props.time, "sleep") as wait:
            with self.assertRaisesRegex(RuntimeError, "never became valid"):
                props.read_stable_live_decisions(self.path, attempts=4)
        self.assertEqual(wait.call_count, 3)

    def test_unexpected_parser_corruption_is_not_silently_accepted(self):
        with patch.object(props.pd, "read_csv",
                          side_effect=pd.errors.ParserError("broken record")), \
             patch.object(props.time, "sleep") as wait:
            with self.assertRaises(pd.errors.ParserError):
                props.read_stable_live_decisions(self.path)
        wait.assert_not_called()

    def test_current_csv_changed_during_read_must_be_reloaded(self):
        real = props.pd.read_csv
        count = 0
        def mutation(path, **kwargs):
            nonlocal count
            count += 1
            frame = real(path, **kwargs)
            if count == 1:
                Path(path).write_text("player,score\nBen Rice,94\nAranda,91\n")
            return frame
        with patch.object(props.pd, "read_csv", side_effect=mutation), \
             patch.object(props.time, "sleep") as wait:
            frame = props.read_stable_live_decisions(self.path, delay=0)
        self.assertEqual(count, 2)
        self.assertEqual(len(frame), 2)
        self.assertEqual(wait.call_count, 1)

    def test_bad_retries_rejected(self):
        for invalid in (0, -3, None, True):
            with self.subTest(value=invalid):
                with self.assertRaises((ValueError, TypeError)):
                    props.read_stable_live_decisions(self.path, attempts=invalid)


if __name__ == "__main__":
    unittest.main()
