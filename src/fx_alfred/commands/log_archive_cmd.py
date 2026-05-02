"""Click command for `af log-archive` — explicit archival.

Per PRP-2230 §"`af log-archive`" (lines 174–196 of merged spec). Calls
`core/activity_log.archive_directory()` on the resolved log directory.
Implements the 5-step §Archival procedure: step 0 `fcntl.flock` lock
(try-lock-and-skip on contention), step 1 build
`archive.zip.tmp.<pid>.<rand6>`, step 2 `os.replace`, step 3 unlink raw
files with self-healing on partial failure, step 4 PID-based stale
tmpfile cleanup.

CLI options: `--root <DIR>` (layer resolution), `--force` (overwrite
corrupt existing archive). Exit codes: 0 (archived or nothing to do),
2 (invalid CLI args), 4 (filesystem error), 5 (corrupt archive without
--force). Standalone lock-contention behavior: exit code 0 with stderr
"another archiver is running, skipping" (preserves try-lock-and-skip
semantics consistent with lazy `af log` path; avoids blocking cron/CI).

Implementation lands in CHG-2231 Phase 4 with 12 TDD tests (8 archive
behavior + 4 scanner-skip enforcement regression tests).

This file is a Phase 0 scaffolding placeholder per CHG-2231 §Phase 0;
NOT wired into `cli.py` yet.
"""
