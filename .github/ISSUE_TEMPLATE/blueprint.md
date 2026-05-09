---
name: Iterwheel Blueprint
about: File a task / feature / docs request that the iterwheel-blueprint bot can intake automatically.
title: "[Task]: <one-line summary>"
labels: []
assignees: []
---

<!--
Iterwheel Blueprint intake template.

The iterwheel-blueprint bot watches new issues filed against this repository
and applies the `blueprint-ready` label + 🚀 reaction when the body contains
the required H2 sections AND at least one concrete acceptance criterion
(a `- [ ]` checkbox item under ## Acceptance Criteria).

Keep the H2 section headings (## Work Type, ## Problem / Goal, etc.) so the
bot can detect them. Sections with placeholder values (e.g. "TBD") will not
satisfy the intake check — fill each one with a concrete answer before submit.
-->

## Work Type

<!-- One short paragraph: what kind of work is this? Code, docs, refactor,
     repo hygiene, governance / SOP, infra, etc. -->

## Problem / Goal

<!-- What is broken / missing / desired? State the user-visible outcome,
     not the implementation. -->

## Context

<!-- Background a maintainer needs to understand the request: prior PRs,
     related issues, governance docs, constraints, deadlines. -->

## Expected Outcome

<!-- What does "done" look like? One paragraph describing the end state
     a future reader could verify against. -->

## Acceptance Criteria

<!-- At least one concrete checkbox item is REQUIRED for blueprint-ready
     intake. Each item should be independently verifiable. -->

- [ ] <first concrete, verifiable acceptance criterion>
- [ ] <add more as needed>

## Reproduction Steps / Task Plan

<!-- For bugs: minimal reproduction. For tasks: numbered task plan
     (the agent will refine, not execute verbatim). -->

1.
2.
3.

## Priority

<!-- One of P0 (incident / blocker), P1 (important, schedule soon),
     P2 (normal), P3 (nice-to-have). Add a one-line justification. -->

P2 - <one-line justification>

## Requester / Owner

<!-- Requester: who is asking for this. Owner: who will do or coordinate
     the work (TBD is fine; the maintainer will assign). -->

- **Requester**: @<github-handle>
- **Owner**: TBD

## Out of Scope (optional)

<!-- Explicit non-goals to prevent scope creep. Delete this section if
     not applicable. -->

-
