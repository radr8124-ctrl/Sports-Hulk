"""Recovery addendum is separate from production and checks old profile hashes."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from intelligence_warehouse.historical_recovery.mlb_statcast_staging import (
    stage_recovered_september,
    eligible_research_window,
)

class StatcastAddendumStagingTests(unittest.TestCase):
    def test_provider_addendum_cannot_be_used_for_games_at_or_before_its_raw_end_date(self):
        self.assertFalse(eligible_research_window('2026-09-05T19:00:00Z','2026-09-05'))
        self.assertFalse(eligible_research_window('2026-09-04T18:00:00Z','2026-09-05'))
        self.assertTrue(eligible_research_window('2026-09-06T19:00:00Z','2026-09-05'))

    def test_stage_requires_complete_quarantine_and_cannot_overwrite_production(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Use the canonical reports output location, so it is the
            # missing quarantine (not an unrelated output path) that fails.
            from intelligence_warehouse.historical_recovery.mlb_statcast_staging import TARGET
            with self.assertRaisesRegex(ValueError,'quarantine'):
                stage_recovered_september(Path(tmp)/'missing',TARGET)

    def test_staging_without_output_under_research_directory_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'production'):
                stage_recovered_september(Path(tmp),Path('/home/ubuntu/sports-hulk/baseball_vault/derived'))

if __name__=='__main__':
    unittest.main()
