# REF-2237: Agent Helpers And Skills Usage

**Applies to:** FXA project
**Last updated:** 2026-05-05
**Last reviewed:** 2026-05-05
**Status:** Active
**Tags:** agent-tools, helpers, skills, usage

---

## What Is It?

This reference explains the P0 agent-editable extension surface added by
FXA-2236:

- `af agent call` runs explicitly gated PRJ/USR Python helper functions.
- `af agent run` runs explicitly gated project-relative Python scripts.
- `af skill list` discovers REF/SOP documents that are explicitly tagged as
  `skill`.
- `af skill read` opens one skill document by ID, ACID, exact title, or slug.
- `af plan --with-skills --task ...` appends task-matched skill
  recommendations to a composed SOP plan.

These surfaces are intended for local agent workflows and project-specific
knowledge reuse. They do not add a new document type and they do not import
helper code during normal document scanning, skill listing, or planning.

---

## Content

## Safety Model

Agent helper execution is disabled by default. A command that can execute local
code must be run with the exact environment gate:

```bash
ALFRED_AGENT_TOOLS=1 af agent call <helper_name>
ALFRED_AGENT_TOOLS=1 af agent run <script_path>
```

Any other value, including `true`, is refused before Alfred imports helper
files or runs scripts.

Helper lookup order is:

1. PRJ: `<project-root>/.alfred/agent_helpers.py`
2. USR: `~/.alfred/agent_helpers.py`

PRJ overrides USR. If the PRJ helper file exists but fails to import, Alfred
returns that import failure and does not fall back to USR.

Only functions defined directly in the loaded helper module are callable. Names
beginning with `_` and imported callables are ignored.

## Calling Helpers

Create a project helper:

```python
# .alfred/agent_helpers.py
def release_note(version, package):
    return {"version": version, "package": package}
```

Call it:

```bash
ALFRED_AGENT_TOOLS=1 af agent call release_note \
  --arg version=1.9.2 \
  --arg package=fx-alfred \
  --json
```

`--arg` values are strings. Alfred splits on the first `=`, rejects duplicate
keys, and does not evaluate values.

JSON helper output uses a stable envelope:

```json
{
  "schema_version": "1",
  "helper": "release_note",
  "source": {"layer": "PRJ", "path": "/path/to/.alfred/agent_helpers.py"},
  "status": "ok",
  "result": {"version": "1.9.2", "package": "fx-alfred"}
}
```

If a helper raises or returns a value that cannot be serialized to JSON, Alfred
returns an error envelope instead of a partial result.

## Running Scripts

`af agent run` executes Python scripts with the current interpreter and no shell:

```bash
ALFRED_AGENT_TOOLS=1 af agent run scripts/check_release.py --json
```

Relative script paths resolve from the active project root. JSON output includes
`exit_code`, `stdout`, and `stderr`. Text output replays stdout/stderr and exits
with the script return code.

## Declaring Skills

A skill is an existing `REF` or `SOP` document with explicit metadata:

```markdown
**Tags:** skill, release, pypi
**Task tags:** release, pypi
```

Skill discovery intentionally ignores title conventions such as `Skill: ...`
unless the document also has `Tags: skill`.

Recommended skill documents should explain a reusable method, decision pattern,
checklist, tool recipe, or local workflow that an agent can apply across tasks.

## Discovering Skills

List all skills:

```bash
af skill list
af skill list --json
```

Score skills for a task:

```bash
af skill list --task "release fx-alfred to pypi" --json
```

Matching is local and deterministic. Task tokens score against:

- `Task tags`: +4
- `Tags`: +3
- title: +2
- body: +1

Results sort by score, then layer precedence `PRJ > USR > PKG`, then document
ID. Without `--task`, all skills are listed with `score: null`.

## Reading Skills

Read by full ID:

```bash
af skill read FXA-2237
```

Read by exact normalized slug:

```bash
af skill read skill-release-to-pypi --json
```

ACID-only lookup is allowed only when it is unambiguous across skill documents.

## Planning With Skills

Use `--with-skills` only with a task:

```bash
af plan --task "release fx-alfred to pypi" --with-skills FXA-2108
```

For JSON output, Alfred adds a top-level `recommended_skills` array and sets
`schema_version` to `"3"`:

```bash
af plan --task "release fx-alfred to pypi" --with-skills --json FXA-2108
```

For text output, Alfred appends `# Recommended Skills` after the normal plan
and graph output. If no skill matches the task, the text block is omitted and
the JSON array is `[]`.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-05 | Initial usage guidance for agent helpers and skills. | Codex |
