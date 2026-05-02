"""Click command for `af log-validate` — activity-log schema checker.

Per PRP-2230 §"`af log-validate`" (lines 150–172 of merged spec).
Transparent reader for both loose `*.jsonl` and entries inside
`archive.zip` via `core/activity_log.iter_records()`. Implementation
lands in CHG-2231 Phase 3 with 16 TDD tests including zip-aware paths
and `archive.zip::<member>:<lineno>:` violation notation.

This file is a Phase 0 scaffolding placeholder per CHG-2231 §Phase 0;
NOT wired into `cli.py` yet (registration lands with the Phase 3
implementation).
"""
