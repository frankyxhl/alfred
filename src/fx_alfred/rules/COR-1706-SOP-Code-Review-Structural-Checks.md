# SOP-1706: Code Review — Structural Checks

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-06
**Last reviewed:** 2026-05-06
**Status:** Active
**Related:** COR-1705 (REF — Classification System), COR-1602, COR-1610
**Task tags:** [review, code-review, structural, architecture, api, database]
**Disposition:** inherit-only

---

## What Is It?

Domain-specific checklist for structural code review: architecture, file/module organization, function design, class design, code style, API contracts, and database/persistence. Use this SOP alongside COR-1602 when reviewing code changes in these areas.

---

## Why

Structural issues — misplaced business logic, God classes, leaky abstractions, broken API contracts — are the hardest to fix later. This checklist gives reviewers a consistent set of items to check per domain.

---

## When to Use

- Code review where the change touches: architecture/design, new or modified APIs, database schema/migrations, new modules or classes, significant function-level changes
- As a reference during COR-1602 multi-model parallel review

## When NOT to Use

- Trivial changes (typo fixes, config values, documentation-only)
- When the change is purely cross-cutting (use COR-1707) or domain-specific (use COR-1708)

---

## Item Type and Severity Legend

Per COR-1705 REF: **G** = Gate (tool/CI), **A** = Automated (should be tool-enforced), **H** = Human Review.
**P0** = Blocker, **P1** = Should Fix, **P2** = Nit.

---

## Steps

### 1. Architecture and Design

- [ ] H-1.1 Code is in the correct module, directory, and layer. [P0]
- [ ] H-1.2 Business logic is not in controllers, views, route handlers, or script entry points. [P0]
- [ ] H-1.3 Infrastructure details do not leak into domain layer. [P1]
- [ ] H-1.4 No temporary requirement pollution of public abstractions. [P1]
- [ ] H-1.5 Dependency direction matches architecture (outer depends on inner, not reverse). [P0]
- [ ] H-1.6 No circular dependencies introduced. [P0]
- [ ] H-1.7 No bypass of dependency boundaries via globals, singletons, or static state. [P1]
- [ ] H-1.8 External service calls are encapsulated behind clear boundaries for testability. [P1]
- [ ] H-1.9 No over-engineering or premature abstraction for hypothetical future use. [P1]
- [ ] H-1.10 New abstractions have clear current use cases; naming matches business concepts. [P1]
- [ ] H-1.11 No copy-paste of existing logic without abstraction. [P1]
- [ ] H-1.12 Public APIs, events, and DB schemas are backward-compatible (or have a migration plan). [P0]
- [ ] H-1.13 Old clients, mobile apps, caches, CDNs, and queued messages considered for compatibility. [P1]

### 2. File and Module Level

- [ ] H-2.1 Each file expresses one primary concept or responsibility. [P1]
- [ ] H-2.2 File name accurately reflects content. [P1]
- [ ] H-2.3 File does not mix business logic, I/O, formatting, config, and test data. [P1]
- [ ] A-2.4 File length is within threshold; tooling alerts on violations. [P2]
- [ ] H-2.5 Large files are still structurally clear, not "God files." [P1]
- [ ] H-2.6 Imports are clean: no duplicates, no unused imports. [P2]
- [ ] A-2.7 Import order is automated by tooling. [P2]
- [ ] H-2.8 Public API and private helpers are clearly separated. [P1]
- [ ] H-2.9 Module exports only what is necessary; no internal helpers leaked. [P1]
- [ ] H-2.10 No relative-path penetration of internal implementations (e.g., `../../internal/...`). [P1]
- [ ] H-2.11 No new module-level side effects that are hard to test. [P1]
- [ ] G-3.1 Generated code is not manually modified and has documented generation command and source. [P0]
- [ ] H-3.2 Reviewer reviews generation config/schema/templates, not generated output line-by-line. [P1]
- [ ] G-3.3 Third-party vendored code has source, version, and license recorded. [P1]

### 3. Function and Method Level

- [ ] H-4.1 Function does one primary thing; name captures actual behavior. [P1]
- [ ] H-4.2 Function name includes a verb or clear intent (e.g., `calculateTotal`, `validateRequest`). [P2]
- [ ] H-4.3 Function does not simultaneously validate, query, compute, write, send messages, and format responses. [P1]
- [ ] A-5.1 Function length checked by tooling; hard max 100 lines. [P1]
- [ ] H-5.2 Reviewer judges split when function exceeds 50 lines. [P1]
- [ ] H-5.3 Functions over 100 lines require documented justification in PR. [P1]
- [ ] A-6.1 Cyclomatic complexity checked by tooling (prefer ≤ 10). [P1]
- [ ] A-6.2 Cognitive complexity checked by tooling (prefer ≤ 15). [P1]
- [ ] A-6.3 Nesting depth checked by tooling (prefer ≤ 3-4). [P1]
- [ ] H-6.4 Deep `if/else`, `switch`, or loop nesting reduced via guard clauses or early return. [P1]
- [ ] H-6.5 Table-driven logic, strategy pattern, polymorphism, or map dispatch used where appropriate. [P2]
- [ ] H-6.6 Multiple boolean flags do not control disparate flows in one function. [P1]
- [ ] A-7.1 Parameter count checked by tooling (prefer ≤ 3, hard max 5). [P1]
- [ ] H-7.2 Multiple same-type parameters → consider parameter object, DTO, or named arguments. [P1]
- [ ] H-7.3 Boolean parameters that cause two distinct behaviors → consider splitting into two functions. [P1]
- [ ] H-7.4 Optional parameters have clear defaults. [P2]
- [ ] H-7.5 Parameters are not mutated inside the function. [P1]
- [ ] H-8.1 Return value type is consistent (not mixing null, undefined, exception, error code). [P1]
- [ ] H-8.2 Null/empty returns are explicit and documented. [P1]
- [ ] H-9.1 Functions are pure where possible; side effects are explicit and documented. [P1]
- [ ] H-9.2 No hidden mutations of shared or global state. [P0]
- [ ] H-10.1 Error handling covers all failure modes; not swallowing exceptions silently. [P0]
- [ ] H-10.2 Error messages contain enough context for debugging. [P1]
- [ ] H-11.1 Input validation at system boundaries; trust boundary is explicit. [P0]
- [ ] H-11.2 Untrusted input never reaches dangerous operations without validation. [P0]
- [ ] H-12.1 Mutable state is minimized; immutable data structures preferred. [P1]
- [ ] H-13.1 Async/concurrent code handles cancellation, timeouts, and error propagation. [P1]
- [ ] H-13.2 Shared mutable state in concurrent contexts is properly synchronized. [P0]
- [ ] H-14.1 Functions are testable: dependencies injectable, side effects mockable. [P1]
- [ ] H-15.1 Obvious algorithmic performance issues (O(n²) where O(n log n) is standard). [P1]
- [ ] A-16.1 Tooling can check function-level metrics; reviewer checks exceptions only. [P2]

### 4. Class Level

- [ ] H-17.1 Class has a single responsibility. [P1]
- [ ] H-17.2 Internal state is encapsulated; public API is minimal. [P1]
- [ ] H-17.3 Inheritance used only for true "is-a" relationships; composition preferred. [P1]
- [ ] H-17.4 Dependencies are injected, not created or looked up internally. [P1]

### 5. Code Style

- [ ] H-18.1 Names are clear and consistent with project conventions. [P2]
- [ ] H-18.2 Types are explicit where ambiguity exists; null safety is handled. [P1]
- [ ] H-18.3 Data structures chosen appropriately (list vs set vs map vs tree). [P2]
- [ ] H-18.4 Constants and enums used instead of magic values. [P1]
- [ ] H-18.5 No commented-out code without explanation and issue reference. [P2]

### 6. API Contracts

- [ ] H-19.1 Request input is validated at the boundary. [P0]
- [ ] H-19.2 Response output does not leak internal details (stack traces, internal IDs, DB errors). [P0]
- [ ] H-19.3 API documentation is updated and matches implementation. [P1]
- [ ] H-19.4 Contract tests cover request/response shapes. [P1]
- [ ] H-19.5 Breaking changes are versioned or communicated to consumers. [P0]

### 7. Database and Persistence

- [ ] H-20.1 Migrations are reversible (or documented as irreversible with justification). [P1]
- [ ] H-20.2 Migrations are safe for the table size (no locking full-table writes on large tables). [P0]
- [ ] H-20.3 Queries are efficient: appropriate indexes, no N+1, no full table scans on large tables. [P1]
- [ ] H-20.4 Transaction boundaries are correct; consistency guarantees match business requirements. [P0]
- [ ] H-20.5 Data integrity constraints are defined at the database level, not just application level. [P1]
- [ ] H-20.6 Sensitive data is encrypted at rest or hashed where appropriate. [P1]

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-06 | Initial version — content migrated from code-review-checklist.md v2.0 §3-9 | Frank Xu |
