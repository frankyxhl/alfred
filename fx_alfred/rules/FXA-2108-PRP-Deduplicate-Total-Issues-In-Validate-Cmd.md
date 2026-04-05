# PRP-2108: Deduplicate-Total-Issues-In-Validate-Cmd

**Applies to:** FXA project
**Last updated:** 2026-04-06
**Last reviewed:** 2026-04-06
**Status:** Draft

---

## What Is It?

Deduplicate the `total_issues` calculation in `validate_cmd.py` to eliminate redundant computation and improve readability.

---

## Problem

In `src/fx_alfred/commands/validate_cmd.py`, the expression `sum(len(i) for i in issues_by_doc.values())` appears twice:
- Inside the text-output branch, used to print the summary message
- After the if/else block, used to determine the exit code

The second calculation is redundant — the same `issues_by_doc` dict is used in both places with no mutation between them.

## Proposed Solution

Move the `total_issues` calculation to before the `if output_json:` block. Reuse the variable in both the text-output summary and the exit-code check. This eliminates one redundant `sum()` call and makes the data flow clearer.

**Scope:** Single file (`validate_cmd.py`), ~3 lines changed. No interface change.

## Open Questions

None — straightforward refactor with no behavioral change.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-06 | Initial version | — |
