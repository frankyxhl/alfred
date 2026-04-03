# PRP-2189: Fix-FXA-2185-Invalid-CHG-Status

**Applies to:** FXA project
**Last updated:** 2026-04-04
**Last reviewed:** 2026-04-04
**Status:** Approved

---

## What Is It?

Fix invalid status value on CHG document FXA-2185 to comply with COR-0002.

---

## Problem

FXA-2185 (CHG: Add COR-1201 Discussion Tracker Step To AF Setup) has Status "Implemented", which is not a valid status for CHG documents per COR-0002. The allowed CHG statuses are: Proposed, Approved, In Progress, Completed, Rolled Back.

`af validate` reports this as a validation error.

## Proposed Solution

Change FXA-2185 Status from "Implemented" to "Completed". The change described in FXA-2185 was implemented and is done, so "Completed" is the correct status.

## Open Questions

None. COR-0002 is unambiguous about allowed CHG statuses.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version | — |
