# Baseball HULK — Blended Profiles Hotfix

The 2025 backfill succeeded, but the existing Statcast script writes active derived profiles from the most recent run only. Because 2025 was run after the August 2026 sample, the active profiles became 2025-only.

This hotfix rebuilds the active profiles from cached 2025 + 2026 Statcast chunks.

Default weights:
- 2026 = 1.00
- 2025 = 0.55

It does not lower betting thresholds to create artificial picks.
It does not touch app.py or .env.
It makes no network calls.
