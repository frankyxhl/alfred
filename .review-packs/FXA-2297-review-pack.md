# FXA-2297 Review Pack — CLAUDE.md Refresh + Docs Drift Guards

## Review request

Review this docs+test diff for the fx-alfred CLI with the COR-1610 rubric pinned below. The unit is the full branch diff vs main: a rewrite of the project CLAUDE.md (agent runbook) plus a new drift-guard test file. Cross-reference the actual codebase at HEAD to verify the runbook's claims.

## What & why

CLAUDE.md is the per-session instruction surface for every agent in this repo. The 2026-06-10 review found it two release cycles stale: 6 of 20 CLI commands undocumented (agent, issue, skill, star, starred, unstar); 13 of 19 core/ modules + 6 of 22 commands/ modules missing from the architecture tree; version pinned at v1.17.1 (actual 1.18.0); the Active-PRPs table referencing ALF-2203 which NO LONGER EXISTS; and §Workflow's session-start smoke commands pointing at /Users/frank/Projects/alfred/fx_alfred — a directory that does not exist (an agent following the runbook literally gets exit failure).

The change: (1) complete the Commands section and Architecture tree (log_* Phase 0 scaffolding annotated as NOT wired, per CHG-2231); (2) fix the broken paths; (3) DELETE two drift classes instead of guarding them — hardcoded version → `af --version`/pyproject pointer, static PRP table → `af list --type PRP` pointer; (4) new tests/test_docs_drift.py pinning: every cli.py lazy-subcommand appears as `af <name>`; every commands/*.py + core/*.py filename appears; the dead path string stays absent; no `fx-alfred vX.Y` pattern returns.

Verified: both smoke commands now exit 0 exactly as written in the doc; 981 tests pass (976 → 981); ruff/format/pyright clean.

NOT in scope (do not deduct per COR-1610 rule 4): README.md (verified current); restructuring CLAUDE.md sections or changing workflow-policy content (routing rules, review gates, release SOP references are factual carryovers); guarding free-text accuracy beyond mechanically-checkable surfaces; the user-level ~/.claude/CLAUDE.md.

## Pinned rubric — COR-1610 (use EXACTLY these dimensions and weights)

| Dimension | Weight | What to check |
|-----------|--------|---------------|
| Correctness | 25% | Logic correct? Handles edge cases? No regressions? For docs: are the runbook's claims TRUE against the code? |
| Test Coverage | 25% | All new behavior has tests? Tests test behavior not implementation? |
| Code Style | 15% | Consistent with existing codebase? Linter clean? |
| Security | 15% | No injection, no secrets, no unsafe operations? |
| Simplicity | 20% | Minimal change for the task? No over-engineering? |

Rules (COR-1610): deductions cite file:line; distinguish BLOCKING vs ADVISORY; do NOT deduct for out-of-scope; verify test results before scoring; weighted average rounded to ONE decimal; 8.9 = FIX, 9.0 = PASS. Recompute arithmetic from your own table before printing.

Required output: Decision Matrix + weighted average + PASS/FIX + findings labeled BLOCKING/ADVISORY with file:line.

Special attention requested: (a) fact-check the new architecture tree one-line descriptions against the actual modules — any description that is WRONG about what a module does? (b) are the drift-guard assertions appropriately low-brittleness (would they false-fire on legitimate future edits)? (c) did the rewrite accidentally DROP any policy content from the old CLAUDE.md that agents still need?

## The diff (vs main)

diff --git a/CLAUDE.md b/CLAUDE.md
index 88b2d78..005b8a9 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -2,7 +2,7 @@
 
 ## Project
 
-- **Package:** fx-alfred v1.17.1
+- **Package:** fx-alfred (version: `af --version` / `pyproject.toml`)
 - **Description:** Alfred — Agent Runbook: workflow routing, SOP checklists, and document management
 - **Language:** Python 3.10+, Click 8.0+
 - **Entry point:** `af = fx_alfred.cli:cli`
@@ -15,6 +15,7 @@
 af guide [--root DIR] [--json]              # workflow routing (PKG → USR → PRJ)
 af plan SOP_ID [...] [--root DIR] [--json]  # LLM-optimized workflow checklist from SOPs
 af plan --human SOP_ID [...]                # human-readable checklist
+af plan --task "DESC" [SOP_ID ...]          # auto-compose SOPs via Task tags
 af setup                                    # suggested prompts for agent config
 af list [--type TYPE] [--prefix PREFIX] [--source SOURCE] [--tag TAG] [--json]
 af read IDENTIFIER [--json]                 # read by PREFIX-ACID or ACID only
@@ -23,10 +24,16 @@ af update IDENTIFIER [--status] [--field KEY VALUE] [--history TEXT] [--by TEXT]
 af where IDENTIFIER [--json]               # print absolute file path of a document
 af fmt [DOC_IDS...] [--write] [--check]     # format documents to canonical style
 af search PATTERN [--json]                  # case-insensitive content search
-af validate [--root DIR] [--json]           # structural correctness checks
+af validate [--root DIR] [--json]           # structural checks; warns on unknown TYPE codes
 af status [--json]                          # document counts by source/type/prefix
 af index                                    # regenerate PRJ layer index
 af changelog                                # show version changelog
+af star ID / af starred / af unstar ID      # bookmark documents
+af skill list [--json]                      # list explicit skill documents
+af skill read ID [--json]                   # read a skill document
+af issue lint BODY_FILE|-                   # pre-creation GitHub issue body lint
+af agent call HELPER [--arg k=v ...] [--json]  # PRJ/USR helper exec (needs ALFRED_AGENT_TOOLS=1)
+af agent run SCRIPT [--json]                # run script via current interpreter (same gate)
 ```
 
 ## Architecture
@@ -37,32 +44,54 @@ src/fx_alfred/
 ├── lazy.py             # LazyGroup class (importlib on demand)
 ├── context.py          # --root option, get_root()
 ├── commands/
-│   ├── _helpers.py     # scan_or_fail(), find_or_fail()
+│   ├── _helpers.py     # scan_or_fail(), find_or_fail(), atomic_write()
+│   ├── agent_cmd.py    # af agent call/run (env-gated helper + script execution)
+│   ├── changelog_cmd.py
+│   ├── create_cmd.py   # create from template or spec
+│   ├── fmt_cmd.py      # format to canonical style (metadata order, whitespace, table align)
 │   ├── guide_cmd.py    # workflow routing (layered PKG→USR→PRJ)
-│   ├── plan_cmd.py     # workflow checklist from SOPs
-│   ├── setup_cmd.py    # agent configuration prompts
+│   ├── index_cmd.py    # regenerate document index (COR-0002 compliant)
+│   ├── issue_cmd.py    # af issue lint (TBD-phrase detection)
 │   ├── list_cmd.py     # list + filtering + --json
+│   ├── log_cmd.py          # Phase 0 scaffolding (CHG-2231) — NOT wired into cli.py
+│   ├── log_archive_cmd.py  # Phase 0 scaffolding (CHG-2231) — NOT wired into cli.py
+│   ├── log_validate_cmd.py # Phase 0 scaffolding (CHG-2231) — NOT wired into cli.py
+│   ├── plan_cmd.py     # workflow checklist from SOPs (text/JSON/todo/graph modes)
 │   ├── read_cmd.py     # read + --json
-│   ├── create_cmd.py   # create from template or spec
-│   ├── update_cmd.py   # metadata/history/rename updates; --spec FILE
-│   ├── fmt_cmd.py      # format to canonical style (metadata order, whitespace, table align)
-│   ├── where_cmd.py    # find absolute file path of a document (--json)
 │   ├── search_cmd.py   # content search
-│   ├── validate_cmd.py # metadata + status + SOP section validation
+│   ├── setup_cmd.py    # agent configuration prompts
+│   ├── skill_cmd.py    # skill document discovery/read
+│   ├── star_cmd.py     # star/starred/unstar bookmarks
 │   ├── status_cmd.py   # summary counts + --json
-│   ├── index_cmd.py    # regenerate document index (COR-0002 compliant)
-│   └── changelog_cmd.py
+│   ├── update_cmd.py   # metadata/history/rename updates; --spec FILE
+│   ├── validate_cmd.py # metadata + status + SOP section validation; unknown-TYPE warnings
+│   └── where_cmd.py    # find absolute file path of a document (--json)
 ├── core/
-│   ├── document.py     # Document dataclass, FILENAME_PATTERN
-│   ├── parser.py       # parse_metadata(), render_document(), extract_section()
-│   ├── scanner.py      # scan_documents(), find_document(), layer validation
-│   ├── schema.py       # DocType/DocRole enums, ALLOWED_STATUSES, REQUIRED_METADATA/SECTIONS
-│   ├── normalize.py    # slugify(), sort_metadata(), normalize_date(), strip_trailing_whitespace()
-│   └── source.py       # Source type, SOURCE_LABELS, SOURCE_ORDER
+│   ├── activity_log.py    # Phase 0 scaffolding docstring (CHG-2231)
+│   ├── agent_helpers.py   # af agent engine: env gate, helper loading, script exec
+│   ├── ascii_graph.py     # flat ASCII workflow graph renderer
+│   ├── branch_geometry.py # pure branch-layout geometry (wcwidth)
+│   ├── branch_layout.py   # branch lane layout for sub-step rendering
+│   ├── compose.py         # af plan --task auto-composition; raises CompositionError
+│   ├── dag_graph.py       # nested phase-box DAG renderer
+│   ├── document.py        # Document dataclass, FILENAME_PATTERN
+│   ├── mermaid.py         # Mermaid diagram renderer
+│   ├── normalize.py       # slugify(), sort_metadata(), normalize_date(), strip_trailing_whitespace()
+│   ├── parser.py          # parse_metadata(), render_document(), extract_section(), fence-state iterator
+│   ├── phases.py          # PhaseDict/StepDict typed shapes
+│   ├── preferences.py     # ~/.alfred preferences store (star bookmarks)
+│   ├── scanner.py         # scan_documents(), find_document(), layer validation
+│   ├── schema.py          # DocType/DocRole enums, ALLOWED_STATUSES, REQUIRED_METADATA/SECTIONS
+│   ├── skills.py          # skill document discovery
+│   ├── source.py          # Source type, SOURCE_LABELS, SOURCE_ORDER
+│   ├── steps.py           # shared step parsing (flush-left + fence-aware + heading-form preference)
+│   └── workflow.py        # Workflow signature/loops/branches parsing + validation
 ├── rules/              # PKG layer (bundled COR-* documents, read-only)
 └── templates/          # Document templates for af create (5W1H SOP template)
 ```
 
+`core/` is framework-agnostic — no Click imports (enforced by `tests/test_architecture.py`); failures surface as domain exceptions converted at the commands layer.
+
 ## Three-Layer Document Model
 
 | Layer | Location | Source | Writable |
@@ -85,6 +114,7 @@ src/fx_alfred/
 .venv/bin/pytest -v --tb=short        # run tests
 .venv/bin/ruff check .                 # lint
 .venv/bin/ruff format --check .        # format check
+.venv/bin/pyright src/                 # type check
 
 # Install (editable)
 pip install -e .
@@ -99,9 +129,10 @@ af list --root /Users/frank/Projects/alfred
 
 - **scan_or_fail(ctx)** / **find_or_fail(docs, id)** — all commands use these helpers from `_helpers.py`
 - **LazyGroup** — cli.py imports zero command modules at startup; all loaded on demand via `importlib`
-- **core/ is framework-agnostic** — no Click imports in `core/`; Click dependency lives in `commands/`
+- **core/ is framework-agnostic** — no Click imports in `core/` (enforced by `tests/test_architecture.py`); domain exceptions (`CompositionError`, scanner errors) convert to `ClickException` at the commands boundary
 - **Atomic writes** — `update_cmd` uses tempfile + os.replace for safe file updates
-- **extract_section(body, heading)** — reusable section extraction in `parser.py`
+- **extract_section(body, heading)** — fence-aware section extraction in `parser.py` (CHG-2294)
+- **Docs drift guards** — `tests/test_docs_drift.py` pins this file's command list and module inventory to the code
 
 ## Key COR SOPs (PKG layer)
 
@@ -121,16 +152,17 @@ af list --root /Users/frank/Projects/alfred
 | COR-1623 | PR Review Thread Verification — verify unresolved PR threads against exact PR head source content |
 | COR-1503 | Diagnose Feedback Loop — 6-phase bug/perf diagnosis with enforcement gates |
 
-## Active PRPs (Draft)
+## Active PRPs
 
-| ACID | Title | Dependency |
-|------|-------|-----------|
-| FXA-2117 | AF Filter + Section Update | FXA-2116 (done) |
-| ALF-2203 | Multi-CHG Implementation Workflow | None |
+Static tables drift (a previous revision listed a PRP that no longer exists). Query live instead:
+
+```bash
+af list --type PRP --root /Users/frank/Projects/alfred
+```
 
 ## Workflow
 
-- **Session start:** Run COR-1208 (Session Startup Sanity Check — `pwd`, `git status`/`log`, smoke test, load tracker, surface anomalies) before anything else. Then `af guide --root /Users/frank/Projects/alfred/fx_alfred`. Smoke for this project: `.venv/bin/pytest -v --tb=short` and `af validate --root /Users/frank/Projects/alfred/fx_alfred`.
+- **Session start:** Run COR-1208 (Session Startup Sanity Check — `pwd`, `git status`/`log`, smoke test, load tracker, surface anomalies) before anything else. Then `af guide --root /Users/frank/Projects/alfred`. Smoke for this project: `.venv/bin/pytest -v --tb=short` and `af validate --root /Users/frank/Projects/alfred`.
 - **Before every task:** Declare active SOP per COR-1402 before starting work (or flag if none exist)
 - **Workflow checklist:** `af plan <SOP_IDs>` (LLM-optimized, follow each phase)
 - **First time:** `af setup` (suggested prompts for agent config)
diff --git a/tests/test_docs_drift.py b/tests/test_docs_drift.py
new file mode 100644
index 0000000..b751d68
--- /dev/null
+++ b/tests/test_docs_drift.py
@@ -0,0 +1,57 @@
+"""Docs drift guards for the project CLAUDE.md agent runbook (CHG-2297).
+
+CLAUDE.md is the per-session instruction surface for agents working in
+this repo. These tests pin the mechanically-checkable claims so the
+runbook cannot silently diverge from the code again (the 2026-06-10
+review found 6 undocumented commands, 19 undocumented modules, a stale
+version, and broken smoke-command paths).
+"""
+
+from __future__ import annotations
+
+import re
+from pathlib import Path
+
+import pytest
+
+pytestmark = pytest.mark.docs
+
+_REPO = Path(__file__).parent.parent
+_CLAUDE_MD = (_REPO / "CLAUDE.md").read_text(encoding="utf-8")
+
+
+def _lazy_subcommands() -> list[str]:
+    cli_src = (_REPO / "src" / "fx_alfred" / "cli.py").read_text(encoding="utf-8")
+    return re.findall(r'"([a-z]+)":\s*"fx_alfred\.commands\.', cli_src)
+
+
+def test_every_cli_command_is_documented() -> None:
+    """Every command registered in cli.py appears as `af <name>` in CLAUDE.md."""
+    commands = _lazy_subcommands()
+    assert commands, "no commands parsed from cli.py — parser broken?"
+    missing = [c for c in commands if f"af {c}" not in _CLAUDE_MD]
+    assert missing == [], f"CLI commands missing from CLAUDE.md: {missing}"
+
+
+@pytest.mark.parametrize("package", ["commands", "core"])
+def test_every_module_is_documented(package: str) -> None:
+    """Every commands/*.py and core/*.py module appears in CLAUDE.md."""
+    pkg_dir = _REPO / "src" / "fx_alfred" / package
+    modules = sorted(
+        p.name for p in pkg_dir.glob("*.py") if p.stem not in ("__init__",)
+    )
+    assert modules, f"no modules found under {package}/ — path broken?"
+    missing = [m for m in modules if m not in _CLAUDE_MD]
+    assert missing == [], f"{package}/ modules missing from CLAUDE.md: {missing}"
+
+
+def test_no_dead_fx_alfred_root_path() -> None:
+    """The nonexistent `Projects/alfred/fx_alfred` path must not reappear
+    (it broke the documented session-start smoke commands)."""
+    assert "Projects/alfred/fx_alfred" not in _CLAUDE_MD
+
+
+def test_no_hardcoded_package_version() -> None:
+    """CLAUDE.md must not pin `fx-alfred vX.Y.Z` — that drift class is
+    removed in favor of `af --version` / pyproject.toml pointers."""
+    assert not re.search(r"fx-alfred v\d+\.\d+", _CLAUDE_MD)
