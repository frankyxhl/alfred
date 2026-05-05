# PRP-2124: Code Review Checklist v2.0 as Alfred SOP-REF

**Applies to:** FXA project
**Last updated:** 2026-05-06
**Last reviewed:** 2026-05-06
**Status:** Draft
**Related:** Issue #99, COR-1602, COR-1608, COR-1610, COR-1611, COR-1615, COR-0002
**Reviewed by:** —

---

## What Is It?

Convert the 1022-line Chinese `code-review-checklist.md` (Code Review Checklist v2.0, 24 sections) into PKG-layer Alfred documents: one REF defining the G/A/H classification and P0/P1/P2 severity system, plus four SOPs covering domain-specific review checklists (structural checks, cross-cutting concerns, domain-specific checks, AI-assisted code + quick reference). English-only, complementary to existing COR-160x review workflow SOPs.

---

## Problem

`code-review-checklist.md` is a thorough, battle-tested code review checklist covering 24 domains — quality gates, per-language tooling baselines, architecture through IaC checks, AI-generated code specifics, and a short-form PR checklist. But it has no home in the Alfred document system:

- It is untracked, undiscoverable via `af list` / `af search` / `af plan`
- It is in Chinese while all COR PKG documents are English (COR-1401)
- 1022 lines in one file violates COR-0002 atomicity — no reviewer can hold it all in context
- It cannot be composed into workflow plans via `af plan --task`
- It duplicates none of the existing COR-160x SOPs (which define *how* to review) but fills the gap of *what to check* per domain

Without Alfred-native documents, agents and human reviewers lack a discoverable, executable checklist to consult during code review.

---

## Scope

**In scope (v1):**
- Create one REF: G/A/H classification, P0/P1/P2 severity, merge standards, per-language tooling baseline, core principles
- Create SOP 1: structural checks (architecture, file/module, function, class, code style, API contracts, DB/persistence)
- Create SOP 2: cross-cutting concerns (security, privacy, dependencies, tests, performance, observability, release control)
- Create SOP 3: domain-specific checks (change-level checks, frontend, backend, config/IaC, docs/review quality)
- Create SOP 4: AI-assisted code review + short-form PR checklist + example tool configs
- Add cross-reference line in COR-1602 Steps section pointing to new checklists
- Archive original `code-review-checklist.md` to `docs/archive/` with supersession note

**Out of scope (v1):**
- Modifying COR-1608/1610/1611 scoring rubrics (they are process, the new docs are domain checklists)
- Creating zh-CN companions (English only per user decision)
- Tooling configuration changes (the docs reference tool types, not install/configure them)
- Automated enforcement of checklist items in CI

---

## Proposed Solution

### Document Structure

| ACID (proposed) | Type | Working Title | Draft Sections | Reviewer Context |
|-----------------|------|---------------|----------------|------------------|
| COR-1705 | REF | Code Review Classification System | §0, §1, §23 | Read once to understand G/A/H, P0/P1/P2, tooling baseline, principles |
| COR-1706 | SOP | Code Review — Structural Checks | §3-9 | Architecture, file/module, function, class, code style, API, DB |
| COR-1707 | SOP | Code Review — Cross-Cutting Concerns | §10-15 | Security, privacy, dependencies, tests, performance, observability |
| COR-1708 | SOP | Code Review — Domain-Specific Checks | §2, §16-19 | Change-level, frontend, backend, config/IaC, docs |
| COR-1709 | SOP | Code Review — AI-Assisted Code + Quick Reference | §20-22 | AI code review, short-form checklist, example tool configs |

### REF (COR-1705): Classification System

Defines the vocabulary all four SOPs use:

- **G/A/H classification**: Gate (tool/CI-enforced), Automated (should be automated), Human Review (reviewer judgment)
- **P0/P1/P2 severity**: Blocker (must fix), Should Fix (follow-up issue if deferred), Nit (advisory)
- **Merge standards**: minimum bar for merging (all Gates pass, P0=0, owner review for sensitive areas, test coverage or documented reason)
- **Per-language tooling baseline**: JS/TS (ESLint, Prettier, tsc), Python (Ruff, mypy, pytest), Go (golangci-lint, go test), Java/Kotlin (Checkstyle, Detekt, JUnit), Rust (Clippy, rustfmt, cargo test)
- **Core principles**: tools over manual checks, fail-closed CI, trackable exceptions

### SOP 1 (COR-1706): Structural Checks

Checklist items for design-level and code-structure review:

- Architecture: design location, dependency direction, abstraction level, compatibility
- File/module: responsibility, size, boundaries, generated/third-party code handling
- Function: responsibility, length, complexity, parameters, return values, side effects, error handling, input validation, state/mutability, async/concurrency, testability, performance, comments
- Class: responsibility, encapsulation, inheritance vs composition, dependency injection
- Code style: naming, types/nulls, data structures, constants/enums
- API contracts: request input, response output, API docs/contract tests
- DB/persistence: migrations, queries, transactions/consistency, data integrity

### SOP 2 (COR-1707): Cross-Cutting Concerns

Checklist items for non-functional requirements:

- Security: input/injection, authN/authZ, secrets, session/token/cookie, encryption, error/log safety
- Privacy: data minimization, storage/transmission, compliance
- Dependencies: new dependency review, dependency security, build/artifacts
- Tests: coverage, quality, stability, maintainability
- Performance: algorithmic complexity, I/O and network, caching, cost
- Observability: logs, metrics/tracing, alerts/dashboards, release control

### SOP 3 (COR-1708): Domain-Specific Checks

Checklist items that vary by surface:

- Change-level: intent clarity, scope appropriateness, author self-check
- Frontend: UI/state, accessibility, performance, security
- Backend: service boundaries, idempotency, tasks/messaging
- Config/IaC: configuration changes, infrastructure-as-code, deployment
- Docs/review quality: documentation updates, review comment quality

### SOP 4 (COR-1709): AI-Assisted Code + Quick Reference

- AI code review: responsibility for AI-generated code, LLM/AI system changes
- Short-form PR checklist: condensed version for quick PRs
- Example tool configs: ESLint, Prettier, Ruff, Makefile examples

### Integration with Existing SOPs

Add to COR-1602 §Steps, after step 1 ("Leader identifies artifact"):

```
Reference: COR-1706 through COR-1709 (Code Review Checklists) for domain-specific review items.
Consult the relevant SOP(s) based on the artifact's surface (structural, cross-cutting, domain-specific, AI-assisted).
```

No changes to COR-1608, COR-1610, or COR-1611 — they score *how well* the review was done; the new SOPs list *what to check*.

### Implementation Plan

1. Create COR-1705 REF via spec file
2. Create COR-1706 through COR-1709 SOPs via spec files, translating content from Chinese draft
3. Add cross-reference to COR-1602
4. Archive `code-review-checklist.md` (attached to Issue #99) to `docs/archive/code-review-checklist-v1.0.md`
5. Run `af index` to register all new documents
6. Open PR, trigger COR-1615 review bot

### Maintenance

Maintained by the COR-1602 reviewer pool. Updates follow standard CHG workflow (COR-1101).

---

### Risks and Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Fragmentation cost** — reviewers navigate 5 docs instead of 1 monolithic file | Each SOP is self-contained for its domain; the REF is read once. COR-1602 cross-reference directs reviewers to the right SOP per artifact surface. |
| **Content overlap** — e.g., security checks may appear in both SOP 1 (API) and SOP 2 (security) | During implementation, deduplicate cross-cutting items: each check lives in exactly one SOP. Cross-reference between SOPs where related (e.g., "see also COR-1707 §Security"). |
| **Translation fidelity** — Chinese draft → English SOPs may lose nuance | AI-assisted translation with human review of classification terms (G/A/H, P0/P1/P2). Original Chinese draft archived for reference. |
| **G/A/H classification drift** — the REF's classification system may be inconsistently applied across SOPs | The REF is the single source of truth; each SOP references it. Review of new SOPs verifies consistent G/A/H and P0/P1/P2 tagging. |
| **Maintenance burden** — 5 docs to update instead of 1 file | Each doc covers an independent domain; changes rarely cascade across all 5. Standard CHG workflow (COR-1101) applies per-document. |
| **Adoption risk** — reviewers may not consult the new SOPs | COR-1602 cross-reference creates discoverability. SOPs are tagged for `af plan --task` auto-composition on review tasks. |

---

## Open Questions

All resolved during COR-1203 pre-task alignment + multi-model review:

1. **Form** → 1 REF + 4 SOPs (unanimous reviewer agreement)
2. **Scope** → 5 documents, grouped by coherence cluster (unanimous)
3. **Integration** → Complementary, cross-reference from COR-1602 (unanimous)
4. **Language** → English only (user decision)
5. **Layer** → PKG, ships with `fx_alfred` package (user decision + unanimous reviewer agreement)
6. **Backward compatibility** → Archive v1.0, new docs supersede with cross-reference (unanimous)

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-06 | Initial version | Frank Xu |
