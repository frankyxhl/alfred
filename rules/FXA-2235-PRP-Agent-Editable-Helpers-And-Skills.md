# PRP-2235: Agent Editable Helpers And Skills

**Applies to:** FXA project
**Last updated:** 2026-05-05
**Last reviewed:** 2026-05-05
**Status:** Approved
**Related:** GitHub issue #94, PRD_alfred_agent_helpers_and_skills.md
**Reviewed by:** Trinity fast-review (GLM 9.1/10, DeepSeek 9.0/10; review_id=FXA-2235-prp-r6)

---

## What Is It?

Add a controlled "learn-by-doing" surface to Alfred through two explicit CLI families:

- `af agent` executes local helper code only when the caller opts in with `ALFRED_AGENT_TOOLS=1`.
- `af skill` discovers and reads Alfred skill documents without executing helper code.

The goal is to borrow browser-harness's skill sedimentation mechanism, not its browser/CDP architecture: a current Agent session writes a one-off helper, calls Alfred as a subprocess, reuses the helper, then promotes stable behavior into a REF, SOP, PRP/CHG, or core CLI command when justified.

---

## Problem

Alfred already gives agents a deterministic runbook system: `af guide`, `af plan`, `af search`, `af read`, and document validation. It does not yet provide a sanctioned place for agents to keep reusable local helper functions that are useful during real work but not mature enough to become package code.

Without an explicit surface, agents either:

- keep rewriting temporary scripts that disappear after the task,
- hide reusable logic in ad hoc files with no source/audit contract,
- over-promote immature logic directly into package commands, or
- risk contaminating safe commands if helper loading is bolted into existing paths.

The hard safety constraint is that ordinary Alfred commands must remain deterministic and safe by default. In particular, `af guide`, `af plan`, `af validate`, and `af skill` must not implicitly import or execute project-local Python.

Concrete FXA use cases include reusable review-pack collection for GitHub PR review loops, release verification summaries, validation-repair helpers, and project-specific document migration checks. These are useful during real sessions before they are stable enough to deserve a maintained package command.

---

## Scope

In scope for P0:

- Add lazy subcommands:
  - `af agent call <helper_name> [--json] [--arg key=value ...]`
  - `af agent run <script_path> [--json]`
  - `af skill list [--task "..."] [--layer PKG|USR|PRJ|all] [--json]`
  - `af skill read <id_or_name> [--json]`
- Support the existing Alfred `--root` option for all new command paths.
- Add `af plan --with-skills`, requiring `--task` in P0.
- Support helper files:
  - PRJ: `./.alfred/agent_helpers.py`
  - USR: `~/.alfred/agent_helpers.py`
- Resolve helpers by `PRJ > USR`.
- Register only public functions defined in the loaded helper module itself.
- Support sync and async helper functions.
- Pass `--arg key=value` values as strings only.
- Return structured JSON envelopes for agent consumption.
- Add tests proving safe commands do not import helper files.
- Add one PRJ REF or SOP doc explaining Agent Helpers and Skills usage.
  - Create it with `af create ref --prefix FXA --area 22 --title "Agent Helpers And Skills Usage"` during implementation; the ACID is auto-assigned.

Out of scope for P0:

- Internal LLM runtime, nested Agent session, daemon, or browser/CDP control.
- PKG-layer helper registry.
- Full sandbox, allowlist, denylist, or capability policy.
- Helper promotion telemetry, call-frequency tracking, or stability scoring.
- Automatic helper-to-SOP or helper-to-core-command suggestions.
- New `SKL` document type.
- Schema expansion for `Skill status` or `Helper functions` metadata.
- Typed/JSON kwargs such as `--kwargs-json`.
- Skill recommendation inferred from explicit SOP IDs or composed plan content when no `--task` is provided.
- Auto-commit, auto-push, or auto-promotion of helper files.

---

## Proposed Solution

### Execution Model

Alfred does not start a new LLM session in P0.

```text
current Agent / LLM session
  -> invokes Alfred CLI subprocess
  -> Alfred loads an explicit helper or reads skill docs
  -> Alfred returns stdout / JSON / exit code
  -> current Agent / LLM session continues reasoning
```

`af agent call` may import and execute the selected helper inside the Alfred CLI process after the opt-in gate passes. `af agent run` executes the explicit script path as a process-style operation and reports stdout, stderr, and exit code. Neither command creates a daemon or persistent worker.

### CLI Registration

Add lazy subcommands in `src/fx_alfred/cli.py`:

```python
"agent": "fx_alfred.commands.agent_cmd:agent_cmd",
"skill": "fx_alfred.commands.skill_cmd:skill_cmd",
```

Add new modules:

```text
src/fx_alfred/commands/agent_cmd.py
src/fx_alfred/commands/skill_cmd.py
src/fx_alfred/core/agent_helpers.py
src/fx_alfred/core/skills.py
```

Modify:

```text
src/fx_alfred/commands/plan_cmd.py
```

The `agent` and `skill` commands are nested Click groups. The root `LazyGroup` lazy-loads only the top-level group; after that, the nested group registers its `call`/`run` or `list`/`read` subcommands normally. Add lazy-loading regression tests proving that `af agent --help`, `af agent call --help`, `af skill --help`, and `af skill list --help` all resolve. Add `--with-skills` as a Click option on the existing `plan_cmd`.

### `af agent call`

Command:

```bash
ALFRED_AGENT_TOOLS=1 af agent call <helper_name> [--json] [--arg key=value ...]
```

Behavior:

1. Refuse to execute unless `ALFRED_AGENT_TOOLS=1`.
2. Discover helper files in `PRJ > USR` order.
3. Use the existing Alfred `--root` option; the PRJ helper path resolves under `get_root(ctx)`. If `--root` is omitted, existing Alfred behavior applies: `get_root(ctx)` returns `Path.cwd()`.
4. The gate passes only when `os.environ.get("ALFRED_AGENT_TOOLS") == "1"` using an exact string comparison. Values such as `true`, `yes`, `0`, or `1 ` do not pass.
5. Import helper files only inside the `af agent` command path.
6. Load helper files by precedence and short-circuit: import PRJ first; if the requested helper exists there, do not import USR. Import USR only if PRJ is absent or imports successfully but does not define the requested helper.
7. If a higher-precedence helper file exists but fails to import, return that import failure and do not fall back to a lower-precedence layer. This prevents a broken or malicious PRJ file from being silently bypassed by USR code.
8. Load helper modules with a synthetic unique module name per command invocation, generated from `uuid.uuid4().hex`, and remove that synthetic name from `sys.modules` in a `finally` block after the command finishes. This avoids stale module-cache behavior inside the CLI process even when helper execution raises.
9. Register public helper functions:
   - `inspect.isfunction(value)`,
   - `value.__module__ == loaded_module.__name__`,
   - name does not start with `_`.
10. Do not register imported callables, classes, modules, or constants.
11. Select the first matching helper by precedence.
12. Pass repeated `--arg key=value` flags as string keyword arguments.
13. Split `--arg key=value` on the first `=` only, so values may contain `=`.
14. Reject duplicate `--arg` keys with a Click `UsageError`; do not silently overwrite.
15. Do not use `eval`, `ast.literal_eval`, YAML parsing, or implicit type conversion for `--arg` values.
16. Use `inspect.iscoroutinefunction(value)` after registration only to decide whether to await the helper call.
17. Run async helpers with `asyncio.run(helper(**kwargs))`. P0 assumes the Click command is running in a synchronous CLI process with no active event loop.
18. Return non-zero exit on missing helper, import failure, argument error, helper exception, or JSON serialization failure.
19. Always surface source layer and path when a source is known.

Helpers used with `--json` must return JSON-serializable values. If a helper completes but its result cannot be serialized, return an error envelope with `status: "error"`, `error.type: "TypeError"`, and an error message describing the serialization failure. In text mode, print the helper result with `str(result)`.

JSON success envelope:

```json
{
  "schema_version": "1",
  "helper": "collect_review_pack",
  "source": {
    "layer": "PRJ",
    "path": "./.alfred/agent_helpers.py"
  },
  "status": "ok",
  "result": {}
}
```

JSON error envelope:

```json
{
  "schema_version": "1",
  "helper": "collect_review_pack",
  "source": {
    "layer": "PRJ",
    "path": "./.alfred/agent_helpers.py"
  },
  "status": "error",
  "error": {
    "type": "TypeError",
    "message": "missing required argument: root"
  }
}
```

Runtime exception envelope:

```json
{
  "schema_version": "1",
  "helper": "collect_review_pack",
  "source": {
    "layer": "PRJ",
    "path": "./.alfred/agent_helpers.py"
  },
  "status": "error",
  "error": {
    "type": "RuntimeError",
    "message": "review pack failed"
  }
}
```

Gate failure envelope:

```json
{
  "schema_version": "1",
  "helper": "collect_review_pack",
  "source": null,
  "status": "error",
  "error": {
    "type": "PermissionError",
    "message": "set ALFRED_AGENT_TOOLS=1 to enable agent helper execution"
  }
}
```

Import failure envelope:

```json
{
  "schema_version": "1",
  "helper": "collect_review_pack",
  "source": {
    "layer": "PRJ",
    "path": "./.alfred/agent_helpers.py"
  },
  "status": "error",
  "error": {
    "type": "SyntaxError",
    "message": "invalid syntax"
  }
}
```

Missing helper envelope:

```json
{
  "schema_version": "1",
  "helper": "collect_review_pack",
  "source": null,
  "status": "error",
  "error": {
    "type": "HelperNotFound",
    "message": "helper not found: collect_review_pack"
  }
}
```

### `af agent run`

Command:

```bash
ALFRED_AGENT_TOOLS=1 af agent run <script_path> [--json]
```

Behavior:

1. Refuse to execute unless `ALFRED_AGENT_TOOLS=1`.
2. Resolve the explicit script path to an absolute path. Absolute paths are used as-is; relative paths resolve against `get_root(ctx)` so `--root` controls project-relative script execution. If `--root` is omitted, existing Alfred behavior applies: `get_root(ctx)` returns `Path.cwd()`.
3. Execute only that script path via `subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)`. Do not use shell execution, shebang dispatch, `exec()`, or `importlib`.
4. Return a process-style envelope, not a Python return-value envelope.
5. Use `source.layer == "explicit"`.
6. Preserve stdout, stderr, and exit code.
7. In text mode, print captured stdout to stdout, captured stderr to stderr, and exit with the script exit code.
8. If the resolved script path does not exist or is not a file, return a non-zero error before invoking Python.

JSON envelope:

```json
{
  "schema_version": "1",
  "script": "tmp_collect_context.py",
  "source": {
    "layer": "explicit",
    "path": "/absolute/path/to/tmp_collect_context.py"
  },
  "status": "ok",
  "exit_code": 0,
  "stdout": "...",
  "stderr": ""
}
```

If the script exits non-zero, `status` is `error`, the command exits non-zero, and the envelope still includes `stdout`, `stderr`, and `exit_code`.

Missing script JSON envelope:

```json
{
  "schema_version": "1",
  "script": "tmp_collect_context.py",
  "source": {
    "layer": "explicit",
    "path": "/absolute/path/to/tmp_collect_context.py"
  },
  "status": "error",
  "exit_code": null,
  "stdout": "",
  "stderr": "script not found: /absolute/path/to/tmp_collect_context.py"
}
```

Gate failure JSON for `af agent run --json` uses the same process-style fields:

```json
{
  "schema_version": "1",
  "script": "tmp_collect_context.py",
  "source": null,
  "status": "error",
  "exit_code": null,
  "stdout": "",
  "stderr": "set ALFRED_AGENT_TOOLS=1 to enable agent helper execution"
}
```

### `af skill list`

Command:

```bash
af skill list [--task "..."] [--layer PKG|USR|PRJ|all] [--json]
```

Behavior:

1. Scan Alfred documents using existing document scanning APIs.
2. Use the existing Alfred `--root` option; PRJ document scanning uses `scan_documents(get_root(ctx))`.
3. Never import or execute helper files.
4. Treat a document as a skill only if:
   - document type is `REF` or `SOP`, and
   - `Tags` contains `skill`.
5. Use `Task tags`, `Tags`, title, and lightweight content matching only for ranking/filtering already-qualified skill docs.
6. Do not treat `Task tags` alone as the skill marker; that would scoop up ordinary SOPs.
7. Support layer filtering across `PKG`, `USR`, `PRJ`, and `all`; default to `all`.
8. Return JSON with `schema_version` and a `results` array.

`af skill list` is not equivalent to `af list --tag skill`: it filters to skill-classified REF/SOP docs, ranks by task relevance, returns skill-specific JSON fields, and shares the same recommendation engine with `af plan --with-skills`.

Task matching:

1. Normalize task text to lowercase tokens split on non-alphanumeric boundaries. This tokenization is intentionally local to skill matching in P0 and does not change `compose.tokenize()`.
2. Normalize `Tags` and `Task tags` to lowercase tokens. Skill classification checks for `skill` case-insensitively, using the existing lowercased `Document.tags` surface where possible.
3. Normalize title tokens from `doc.title`, not the H1 prefix text.
4. Score already-qualified skill docs:
   - `+4` for each task token found in `Task tags`,
   - `+3` for each task token found in `Tags`,
   - `+2` for each task token found in title tokens,
   - `+1` for each task token found in body text.
5. With `--task`, include only docs with score `> 0`.
6. Sort by score descending, then source precedence `PRJ > USR > PKG`, then document ID. Local skills sort first because this command is a task-context recall surface; project/user skills should override generic package suggestions.
7. Without `--task`, list all skill docs sorted by source precedence `PRJ > USR > PKG`, then document ID.

JSON result item:

```json
{
  "id": "FXA-2236",
  "prefix": "FXA",
  "acid": "2236",
  "type_code": "REF",
  "title": "Skill: Release To PyPI",
  "source": {
    "layer": "PRJ",
    "path": "rules/FXA-2236-REF-Skill-Release-To-PyPI.md"
  },
  "tags": ["skill", "release", "pypi"],
  "task_tags": ["release", "pypi"],
  "score": 9,
  "match_reasons": ["task_tags:release", "tags:pypi"]
}
```

When `--task` is omitted, result items use the same shape with `"score": null` and `"match_reasons": []`.

Text output format:

```text
Matched skills for task: release pypi

PKG COR-2102 REF Skill: Release To PyPI
  path: src/fx_alfred/rules/COR-2102-REF-Skill-Release-To-PyPI.md
  tags: skill, release, pypi
```

### `af skill read`

Command:

```bash
af skill read <id_or_name> [--json]
```

Behavior:

1. Resolve only within skill-classified documents.
2. Use the existing Alfred `--root` option; PRJ document scanning uses `scan_documents(get_root(ctx))`.
3. Resolution order:
   - full document ID, such as `FXA-2235`,
   - acid-only ID when unambiguous,
   - exact normalized title,
   - exact normalized slug.
4. A normalized title is lowercase `doc.title` text with leading/trailing whitespace stripped and punctuation or consecutive whitespace collapsed to single spaces. A normalized slug is the same normalized title with spaces replaced by `-`.
5. Ambiguous or missing matches return a Click error; P0 does not perform fuzzy matching.
   - Acid-only matches across multiple documents or layers are ambiguous and must error.
6. Keep this resolver in `core/skills.py` / `skill_cmd.py`; do not broaden `core/scanner.find_document()` for all commands.
7. Print the selected document in text mode.
8. Return document metadata and content in JSON mode.
9. Never import or execute helper code.

JSON shape:

```json
{
  "schema_version": "1",
  "document": {
    "id": "FXA-2236",
    "prefix": "FXA",
    "acid": "2236",
    "type_code": "REF",
    "title": "Skill: Release To PyPI",
    "source": {
      "layer": "PRJ",
      "path": "rules/FXA-2236-REF-Skill-Release-To-PyPI.md"
    },
    "tags": ["skill", "release", "pypi"],
    "task_tags": ["release", "pypi"]
  },
  "content": "# REF-2236: Skill: Release To PyPI\n..."
}
```

### `af plan --with-skills`

Command:

```bash
af plan --task "release pypi" --with-skills
```

Behavior:

1. Require `--task` in P0. Without `--task`, return a Click `UsageError`, including when `--json` is also set; P0 does not define JSON error envelopes for Click usage errors.
2. Compose the normal SOP plan exactly as today.
3. Recommend related skill documents using the same read-only skill discovery engine.
4. Do not import helper files.
5. In JSON mode, include `recommended_skills`.
6. When no skills match, omit the Recommended Skills block in text mode and emit `"recommended_skills": []` in JSON mode.
7. In text mode, append a short "Recommended Skills" block at the very end of command output, after all normal plan output and after any rendered graph. This block is never inserted inside Mermaid/ASCII graph text. This applies equally to default, `--human`, `--todo`, and `--graph` text modes.

Text output block:

```text
# Recommended Skills

- [PKG] COR-2102 REF Skill: Release To PyPI
  tags: skill, release, pypi
```

JSON `recommended_skills` shape uses the same result item shape as `af skill list --json`.

In `af plan --json --with-skills`, `recommended_skills` is a top-level key on the existing plan JSON object, alongside `schema_version`, `sop_ids`, `phases`, `composition_valid`, and `edges`. When `recommended_skills` is present, `schema_version` is `"3"`.

---

## Layer Behavior

Helper code paths:

```text
PRJ: ./.alfred/agent_helpers.py
USR: ~/.alfred/agent_helpers.py
```

The PRJ helper path resolves under `get_root(ctx)`, so the existing `--root` option controls which project's helper file is eligible. The USR helper path resolves with `Path.home()`.

Resolution order:

```text
PRJ > USR
```

Skill documents reuse existing Alfred document layers through `scan_documents()`:

```text
PKG: bundled fx_alfred/rules/*.md
USR: ~/.alfred/**/*.md
PRJ: ./rules/*.md
```

P0 does not add a PKG helper registry. This is intentional: package helpers create a stronger maintenance and security commitment than local helper files.

PRJ helpers live in `./.alfred/` instead of `./rules/` because `rules/` is the document scanner's document directory and must remain Markdown-only. Keeping executable helper code outside `rules/` reduces accidental scan/import confusion and makes the executable surface visually distinct.

---

## Safety Contract

Hard rules:

- `af guide` must not import `agent_helpers.py`.
- `af plan` must not import `agent_helpers.py`.
- `af validate` must not import `agent_helpers.py`.
- `af skill list/read` must not import or execute helper code.
- `af plan --with-skills` recommends documents only.
- `af agent call` and `af agent run` refuse execution unless `ALFRED_AGENT_TOOLS=1`.
- Helper/script execution surfaces source layer and path.
- `--arg` values are strings only.
- Duplicate `--arg` keys are a usage error.
- P0 does not claim sandboxing. The protection is explicit opt-in plus narrow command surface, not containment.

Future safety work may add allowlists, denylists, sandboxing, and audit logs. Those require a separate PRP/CHG because they change the trust model.

---

## Implementation Plan

1. Add CLI lazy command registration for `agent` and `skill`.
2. Implement `core/agent_helpers.py`:
   - opt-in gate,
   - helper path discovery,
   - import isolation by explicit command path,
   - public helper registration,
   - PRJ > USR resolution,
   - string-only `--arg` parsing,
   - async helper support,
   - JSON-serializable success/error envelopes.
3. Implement `commands/agent_cmd.py`:
   - Click group,
   - `call`,
   - `run`,
   - text and JSON output,
   - correct exit codes.
4. Add RED tests for helper loading and safety.
5. Implement `core/skills.py`:
   - skill classification,
   - task matching,
   - layer filtering,
   - ID/name resolution,
   - JSON-ready result shapes.
6. Implement `commands/skill_cmd.py`.
7. Extend `commands/plan_cmd.py` with `--with-skills`.
8. Add RED tests for skill discovery and `plan --with-skills`.
9. Add a PRJ REF/SOP usage document for Agent Helpers and Skills.
10. Run full verification and code review before PR.

---

## Acceptance Criteria

Agent helper loading:

- [ ] Without `ALFRED_AGENT_TOOLS=1`, `af agent call <helper>` refuses with a clear message and does not import helper code.
- [ ] Without `ALFRED_AGENT_TOOLS=1`, `af agent run <script>` refuses with a clear message and does not execute the script.
- [ ] `ALFRED_AGENT_TOOLS=1` is the only value that passes the execution gate.
- [ ] `call --json` without the gate returns the gate-failure JSON envelope.
- [ ] With the gate set, public functions in `~/.alfred/agent_helpers.py` are callable.
- [ ] With both USR and PRJ helpers present, PRJ overrides USR for the same helper name.
- [ ] When PRJ defines the requested helper, the USR helper file is not imported.
- [ ] When a PRJ helper file exists but fails to import, the command returns the PRJ import failure and does not fall back to USR.
- [ ] Imported callables such as `from pathlib import Path` are not registered.
- [ ] `async def` helpers are registered and awaited correctly.
- [ ] `--arg key=value` passes string kwargs and performs no implicit type parsing.
- [ ] `--arg url=https://example.com?a=1` splits on the first `=` and preserves the remaining value.
- [ ] Duplicate `--arg` keys fail with a Click usage error.
- [ ] Successful `call --json` returns valid JSON with `schema_version`, `helper`, `source`, `status`, and `result`.
- [ ] Failed `call --json` returns valid JSON with helper/source/error details and exits non-zero.
- [ ] Helper runtime exceptions return the runtime-exception JSON envelope.
- [ ] Helper import failures return the import-failure JSON envelope and do not leak stale modules through `sys.modules`.
- [ ] Missing helpers return the missing-helper JSON envelope.
- [ ] Non-JSON-serializable helper results return a structured TypeError envelope in JSON mode.
- [ ] `run --json` returns valid JSON with `script`, `source.layer == "explicit"`, `stdout`, `stderr`, and `exit_code`.
- [ ] `run --json` for a missing script path returns the missing-script JSON envelope.
- [ ] `run --json` without the gate returns the process-style gate-failure JSON envelope.
- [ ] `run` text mode prints captured stdout/stderr and exits with the script exit code.
- [ ] Relative `af agent run <script_path>` paths resolve against `--root` / `get_root(ctx)`.
- [ ] `af agent run` executes through `sys.executable`, not shell or system `python3`.
- [ ] Helper/script failures return non-zero exit.

Safety:

- [ ] `af guide` does not import a malformed or malicious `./.alfred/agent_helpers.py`.
- [ ] `af plan` does not import a malformed or malicious `./.alfred/agent_helpers.py`.
- [ ] `af validate` does not import a malformed or malicious `./.alfred/agent_helpers.py`.
- [ ] `af skill list/read` does not import or execute helper code.
- [ ] `af plan --with-skills` recommends skills without importing helper code.

Skill discovery:

- [ ] `af skill list` returns only REF/SOP docs that satisfy the skill-classification rule.
- [ ] `Tags: Skill` and `Tags: skill` both classify a REF/SOP as a skill.
- [ ] A SOP with `Task tags` but no `skill` marker is not returned by `af skill list`.
- [ ] A document titled with `Skill:` but lacking `Tags: skill` is not returned by `af skill list` in P0.
- [ ] `af skill list` defaults to all layers when `--layer` is omitted.
- [ ] `af skill list --task <topic>` matches qualifying skill docs by tags, task tags, title, and lightweight content ranking.
- [ ] `af skill list --task <topic> --json` returns result items with `id`, metadata, source, tags, task tags, score, and match reasons.
- [ ] `af skill list --task <topic>` returns no text block beyond "No matching skills found." when no skill matches.
- [ ] `af skill list --json` returns valid JSON with `schema_version` and `results`.
- [ ] `af skill read <id>` prints the selected skill doc.
- [ ] `af skill read <id_or_name>` resolves by full ID, acid-only ID, exact normalized title, then exact normalized slug, and errors on ambiguity.
- [ ] `af skill read <id> --json` returns valid JSON with metadata and content.
- [ ] `af plan --with-skills --task ... --json` includes `recommended_skills`.
- [ ] `af plan --with-skills --task ... --json` puts `recommended_skills` at the top level and sets `schema_version` to `"3"`.
- [ ] `af plan --with-skills --task ... --json` returns `recommended_skills: []` when no skills match.
- [ ] `af plan --with-skills --task ...` omits the Recommended Skills block when no skills match.
- [ ] `af plan --with-skills` without `--task` raises a Click `UsageError`.
- [ ] `af plan --with-skills --json` without `--task` also raises a Click `UsageError`.
- [ ] Lazy loading resolves nested Click groups: `af agent --help` lists `call` and `run`; `af agent call --help` resolves; `af skill --help` lists `list` and `read`; `af skill list --help` resolves.
- [ ] A PRJ REF usage document for Agent Helpers and Skills is created with `af create ref --prefix FXA --area 22`.

Verification commands:

```bash
PYTHONPATH=src .venv/bin/pytest tests/test_agent_cmd.py tests/test_skill_cmd.py tests/test_plan_cmd.py tests/test_lazy.py -v
PYTHONPATH=src .venv/bin/pytest -q
PYTHONPATH=src .venv/bin/ruff check .
PYTHONPATH=src .venv/bin/ruff format --check .
PYTHONPATH=src .venv/bin/pyright src/
PYTHONPATH=src .venv/bin/af validate --root .
```

---

## Test Coverage

Add:

```text
tests/test_agent_cmd.py
tests/test_skill_cmd.py
tests/test_plan_cmd.py
tests/test_lazy.py
```

Test fixtures should create temporary PRJ roots and isolated fake HOME directories so that PRJ/USR precedence and safety behavior are deterministic. Tests must include malicious helper files that raise on import to prove ordinary commands do not touch them.

---

## Risks And Trade-Offs

- **No sandbox in P0.** This is acceptable only because execution is explicitly gated and scoped to `af agent`. The documentation must not imply stronger isolation than exists.
- **Helper import can still run module top-level code.** That is inherent to Python imports. P0 mitigates with explicit opt-in and source reporting; a future sandbox/allowlist PRP can reduce this further.
- **Helper import can fail before registration.** Syntax errors and import errors are expected failure modes. P0 returns structured errors and keeps ordinary commands from importing helpers at all.
- **Module cache could preserve stale helper state.** P0 mitigates this by loading helpers under a synthetic unique module name per command invocation and removing that name from `sys.modules` after execution.
- **Users can defeat the opt-in gate by exporting it globally.** If `ALFRED_AGENT_TOOLS=1` is placed in a shell profile, the explicit per-command safety boundary becomes weaker. The usage REF must instruct users and agents to set the variable only for the command that needs helper execution.
- **Skill classification may be too strict.** Requiring `Tags: skill` avoids conflating ordinary tagged SOPs with skills. False negatives are easier to fix by adding a marker than false positives are to reason about.
- **Text output shape can drift.** JSON envelopes are the stable contract for agents; text output can remain human-oriented.
- **`af plan --with-skills` may duplicate `af skill list --task`.** This is intentional: `af plan` is the session entry point, while `af skill` is the direct recall tool.

---

## Open Questions

No unresolved open questions for P0 approval.

Resolved decisions:

1. P0 does not start a nested LLM session.
2. P0 supports PRJ and USR helper files only; PKG helpers are deferred.
3. P0 does not add a new `SKL` document type.
4. P0 does not expand metadata schema fields.
5. P0 uses `ALFRED_AGENT_TOOLS=1` as the execution gate.
6. P0 treats `--arg` values as strings only.
7. P0 requires `--task` for `af plan --with-skills`.
8. P0 rejects duplicate `--arg` keys instead of silently overwriting.
9. P0 uses `sys.executable` for `af agent run` script execution.
10. P0 classifies skill docs by `Tags: skill` only.
11. P0 adds `recommended_skills` as a top-level `af plan --json` key and bumps that JSON schema to `"3"` when present.

---

## Change History

| Date       | Change                                                                                                                                                                                         | By    |
|------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------|
| 2026-05-05 | Initial version from GitHub issue #94 and attached PRD.                                                                                                                                        | Codex |
| 2026-05-05 | Round-1 Trinity review revisions: define duplicate arg handling, run interpreter/path base, skill resolution/classification, JSON serialization errors, and `--with-skills` usage errors.      | Codex |
| 2026-05-05 | Round-2 Trinity review revisions: define exact gate semantics, short-circuit helper imports, async execution strategy, skill matching algorithm, JSON result shapes, and empty-match behavior. | Codex |
| 2026-05-05 | Round-3 Trinity review revisions: define `recommended_skills` JSON placement/schema, PRJ import-failure no-fallback behavior, per-command `--root` usage, and global gate risk.                | Codex |
| 2026-05-05 | Round-4 advisory cleanup: relocate skill-list no-task JSON note, define `agent run` text/missing-script behavior, and clarify tokenization/module-name details.                                | Codex |
| 2026-05-05 | Round-5 Trinity review revisions: add gate-failure/runtime-exception envelopes, case-insensitive skill classification, exact final text placement, and default root behavior.                  | Codex |
| 2026-05-05 | COR-1602/COR-1608/COR-1613 strict review PASS via Trinity fast-review: GLM 9.1/10, DeepSeek 9.0/10; status set to Approved.                                                                    | Codex |
