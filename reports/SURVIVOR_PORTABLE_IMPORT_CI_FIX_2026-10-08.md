# Survivor importer CI portability fix

The October 8 GitHub CI run failed on PermissionError at /home/ubuntu because a Survivor import module created an absolute VPS directory upon import. Both Survivor parsers now derive the current checkout root from their module file, and never create directories on module import. Explicit commit/upload functions create output directories only when invoked.

12 Survivor importer tests pass, including duplicate PDF/XLSX/CSV tickets, a sandbox full-pool confirm that preserves a Week 4 Vikings WIN, and new tests for arbitrary checkout roots and no filesystem mutation on parser import. No live personal Survivor data or existing import snapshots are changed by this fix.
