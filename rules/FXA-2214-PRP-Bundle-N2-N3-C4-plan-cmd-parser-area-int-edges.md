# PRP-2214: Bundle N2 N3 plan-cmd parser edge tests

**Applies to:** FXA project
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Draft

---

## What Is It?

A proposal for a two-change test-only bundle from the FXA-2213 evolve-CLI run (N2, N3). Output of
the second FXA-2149 Evolve-CLI pass on the codebase.

**R1 → R2 scope reduction:** originally a three-change bundle (N2 + N3 + C4). R1 review
(Codex 6.1 FIX / Gemini 8.9 FIX) caught that C4's proposed fix was broken — `str(0) == "0"`,
not `"00"`, so the `area == "00"` check would still fail and the function still returns
`"0000"`. Any correct repair is either observably-dead (pyright blocks int callers upstream,
so the coercion never runs at runtime — same problem as the Evaluator-discarded N1) or requires
widening the public type contract (scope creep beyond evolve). C4 dropped in R2 as the honest
move; N2 + N3 stand.

---

## Problem

The codebase is healthy by every aggregate signal (663/663 tests pass, 0 ruff issues, 96% coverage,
228/228 docs valid per `af validate`). The FXA-2213 Generator still found three small, specific
improvements where current behaviour is either **silently untested at a user-observable branch** or
**relying on an informal caller-contract** that would fail silently if a future caller violated it.

### N2 — `plan_cmd.py:276` raw-section-text fallback (user-observable, untested)

`_build_todo_items` in `plan_cmd.py` has a three-way branch for producing TODO entries from a SOP's
`## Steps` section:

```python
def _build_todo_items(...) -> list[str]:
    steps_section = _extract_steps_section(body)
    if steps_section is None:
        return [f"{checkbox_prefix}{phase_num}.1 [{sop_id}] (no Steps section found)"]

    steps = _parse_steps_for_json(steps_section)
    if not steps:
        # Raw section text fallback
        return [f"{checkbox_prefix}{phase_num}.1 [{sop_id}] {steps_section.strip()}"]  # line 276
    # ...
```

`_parse_steps_for_json` only matches lines of the form `^(?:###\s+)?(\d+)\.\s+(.+)` (see
`plan_cmd.py:136–144`). So a SOP whose `## Steps` section contains prose (or a bulleted list, or a
"TODO fill in" placeholder) hits line 276 — the raw section text is embedded verbatim as the single
TODO item for that phase.

**This is user-observable behaviour** (someone running `af plan <ACID> --todo` sees the raw text)
and currently has **no test coverage**. A related test exists for the `_format_phase` rendering path
(`tests/test_plan_cmd.py::TestFormatPhaseLlmSnapshot::test_raw_section_fallback`), but that covers
human/LLM output, not the `--todo` flat-list code path. `_build_todo_items` is a separate function.

### N3 — `parser.py:194` "Change History heading but no table" fallback (untested)

`parse_metadata` in `core/parser.py` distinguishes documents with a proper Change History table from
documents where the `## Change History` heading exists but no table follows. Lines 185–204:

```python
table_header_end = None
for i in range(1, len(history_lines)):
    stripped = history_lines[i].strip()
    if stripped.startswith("|") and "---" in stripped:
        table_header_end = i
        break

if table_header_end is None:
    # Change History heading exists but no table — treat entire section as body
    return ParsedDocument(
        h1_line=h1_line,
        metadata_fields=metadata_fields,
        ...
        body=rest_text,
        history_header="",
        history_rows=[],
        ...
    )
```

This fallback preserves round-trip fidelity for in-progress documents (e.g., fresh `af create`
templates before the table is filled in). No test pins it; a regression that fails to return early
would cascade into unrelated failures (e.g. `fmt_cmd` trying to rewrite a nonexistent table).

### ~~C4 dropped in R2~~

~~`_next_acid_in_area` `area == "00"` fragility~~ — dropped after R1 review caught the proposed
fix does not fix the bug (`str(0) == "0"`, not `"00"`) and any correct repair either yields dead
code under FXA-2208's pyright gate or widens the public type annotation (scope creep). See the
*What Is It?* section for the full R1 → R2 rationale. The underlying brittleness observation
remains valid and will be re-seeded in the FXA-2213 run log for a future evolve pass.

## Proposed Solution

### N2 — test for `plan_cmd.py:276` raw-section-text fallback

Add `test_plan_todo_raw_section_text_fallback` to `tests/test_plan_cmd.py`.

Strategy: build a temporary `rules/` directory containing a SOP whose `## Steps` section has prose
but no numbered items. Invoke `af plan <ACID> --todo --root <tmp>` and assert the output contains
the raw section text attached to the `{phase}.1 [{sop_id}] ...` line.

Minimal test body:

```python
def test_plan_todo_raw_section_text_fallback(tmp_path):
    """plan --todo emits raw Steps-section text when no numbered items are found."""
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "TST-2100-SOP-Prose-Steps.md").write_text(
        "# SOP-2100: Prose Steps\n\n"
        "**Applies to:** Test\n"
        "**Last updated:** 2026-04-19\n"
        "**Last reviewed:** 2026-04-19\n"
        "**Status:** Active\n\n---\n\n"
        "## What Is It?\n\nA test SOP.\n\n"
        "## Why\n\nTest.\n\n## When to Use\n\nTest.\n\n"
        "## When NOT to Use\n\nTest.\n\n"
        "## Steps\n\nTODO: fill in the numbered steps.\n\n"
        "---\n\n## Change History\n\n"
        "| Date | Change | By |\n|------|--------|----|\n"
        "| 2026-04-19 | Initial | — |\n"
    )
    runner = CliRunner()
    result = runner.invoke(
        cli, ["plan", "TST-2100", "--todo", "--root", str(tmp_path)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "[TST-2100] TODO: fill in the numbered steps." in result.output
```

### N3 — test for `parser.py:194` "no table" early return

Add `test_parse_metadata_change_history_heading_without_table` to `tests/test_parser.py`.

Strategy: unit-test `parse_metadata` directly with a document that has `## Change History` heading
but no `|---|---|---|` separator row. Assert that `history_header == ""`, `history_rows == []`, and
the raw text lands in `body`.

Minimal test body:

```python
def test_parse_metadata_change_history_heading_without_table():
    """parse_metadata returns empty history when the heading exists but no table follows."""
    content = (
        "# SOP-2100: Test\n\n"
        "**Applies to:** Test\n"
        "**Status:** Active\n\n---\n\n"
        "## What Is It?\n\nBody.\n\n---\n\n"
        "## Change History\n\n"
        "Table will be added later.\n"
    )
    parsed = parse_metadata(content)
    assert parsed.history_header == ""
    assert parsed.history_rows == []
    assert "Change History" in parsed.body
```

### Test scope

- N2, N3: test-only. No production code change.

### Non-goals

- Not touching the Evaluator-discarded candidates (S1 FXA-2212 DAG graph, N1 dead-branch deletion).
- Not pursuing the C4 `_next_acid_in_area` int-tolerance fix — dropped in R2 after the proposed
  repair proved broken and all correct repairs fall outside evolve scope.
- Not changing CLI surface, JSON shape, diagnostic strings, or file output formats.

### Risks

- **N2 — fixture coupling.** The test constructs a full minimal-valid SOP document. If required
  metadata or sections change (FXA-2134 evolution), this fixture must be updated. Mitigation:
  docstring cites the concrete target line (`plan_cmd.py:276`) so a future reader understands why
  the unusual "prose-only Steps" shape is deliberate.
- **N3 — parse contract coupling.** The test asserts `parsed.history_header == ""` and
  `history_rows == []`. These are documented intermediate-state contracts. If `parse_metadata`
  ever chooses a different empty sentinel (e.g., `None`), the test breaks. Accepted tradeoff —
  that behaviour change would itself merit a test update.
- **Coverage vs. behaviour.** N2 and N3 add coverage for branches that work correctly today.
  Mitigation per Run 1 precedent: each test asserts a specific observable outcome (TODO text
  content, ParsedDocument field values), not merely "runs without error".

## Open Questions

None. All three changes target documented, currently-implemented behaviour. No design decisions
required.

---

## Change History

| Date       | Change                                                    | By             |
|------------|-----------------------------------------------------------|----------------|
| 2026-04-19 | Initial version                                                                                                                                  | —              |
| 2026-04-19 | Fill problem + proposed solution from FXA-2213 (N2+N3+C4)                                                                                        | Frank + Claude |
| 2026-04-19 | R1 Codex 6.1 / Gemini 8.9 both FIX: proposed C4 fix is empirically broken (`str(0)='0'`). R2: drop C4, ship N2+N3 only; other advisories resolved | Frank + Claude |
