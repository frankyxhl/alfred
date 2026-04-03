# PRP-2168: Deduplicate Plan Cmd Phase Formatters

**Applies to:** FXA project
**Last updated:** 2026-04-01
**Last reviewed:** 2026-04-01
**Status:** Draft

---

## What Is It?

Proposal to deduplicate `_format_phase_llm` and `_format_phase_human` in `plan_cmd.py` into a single parameterized function.

---

## Problem

`plan_cmd.py` lines 72-125 contain two functions that share ~80% of their logic:

```python
def _format_phase_llm(phase_num, sop_id, title, summary, body) -> str:
    # heading: f"## Phase {phase_num}: {sop_id} ({title})"
    # summary prefix: "What: "
    # checkbox: "- [ ] "
    # fallback: raw section text

def _format_phase_human(phase_num, sop_id, title, summary, body) -> str:
    # heading: f"═══ Phase {phase_num}: {sop_id} ({title}) ═══"
    # summary: bare first paragraph (no prefix)
    # checkbox: "□ "
    # fallback: raw section text
```

Both functions: extract steps section, parse numbered items, format checkboxes, handle missing steps fallback. Only heading format, summary prefix, and checkbox style differ.

**Evidence:** Source analysis during Evolve-Run FXA-2167.

## Proposed Solution

Replace both functions with a single `_format_phase` that receives pre-built strings from callers:

```python
def _format_phase(
    heading: str, summary: str | None, body: str,
    summary_prefix: str, checkbox: str,
) -> str:
```

Callers construct the heading themselves and pass simple string parameters:

```python
# In plan_cmd (LLM path):
heading = f"## Phase {phase_num}: {sop_id} ({title})"
_format_phase(heading, summary, body, summary_prefix="What: ", checkbox="- [ ] ")

# In plan_cmd (human path):
heading = f"═══ Phase {phase_num}: {sop_id} ({title}) ═══"
_format_phase(heading, summary, body, summary_prefix="", checkbox="□ ")
```

The unified function contains only the shared logic: append heading, format summary, extract steps, format checkboxes, handle fallback. No internal string interpolation.

Net effect: ~20 fewer lines, identical output.

## Scope

**In scope:** `plan_cmd.py` only — merge `_format_phase_llm` and `_format_phase_human` into `_format_phase`.

**Out of scope:** No changes to `_extract_steps_section`, `_parse_numbered_items`, `_parse_steps_for_json`, or the `plan_cmd` click command itself. No changes to any other file.

**Affected documents:** None. This is an internal refactor of private helper functions.

## Risks

- **Readability trade-off:** Two explicit functions are slightly easier to read at a glance than one parameterized function. Mitigated by the callers being 2 lines apart in the same `plan_cmd` function and by clear parameter names.
- **Test regression:** Mitigated by existing tests covering both LLM and human output paths. TDD approach ensures output is byte-identical before and after.

## Open Questions

None — all resolved.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-01 | Initial version | — |
| 2026-04-01 | R2: simplified to pre-built heading, added scope/risks per Gemini R1 feedback (7.4) | Claude |
