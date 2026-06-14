# REF-1705: Code Review Classification System

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-06
**Last reviewed:** 2026-05-06
**Status:** Active
**Related:** COR-1706, COR-1707, COR-1708, COR-1709, COR-1602, COR-1608, COR-1610
**Supersedes:** code-review-checklist.md v2.0 (Issue #99)
**Disposition:** inherit-only

---

## What Is It?

The classification vocabulary used by all Code Review Checklist SOPs (COR-1706 through COR-1709). Defines item types (G/A/H), severity levels (P0/P1/P2), merge standards, per-language tooling baselines, and core principles. Read this REF once before using any checklist SOP.

---

## Item Types

| Type | Label | Meaning | Who Acts |
|------|-------|---------|----------|
| **G** | Gate | Quality gate. Must be enforced by tooling, CI, configuration, or process. | Tooling / CI |
| **A** | Automated | Should be checked by formatter, linter, type checker, test runner, SAST, SCA, or secret scanner. | Tooling |
| **H** | Human Review | Requires reviewer judgment. Tools cannot fully substitute. | Reviewer |

## Severity Levels

| Level | Label | Meaning | Action |
|-------|-------|---------|--------|
| **P0** | Blocker | Must fix. Cannot merge without resolution. | Fix before merge |
| **P1** | Should Fix | Strongly recommended this PR. If deferred, must have a follow-up issue with owner. | Fix or file issue |
| **P2** | Nit | Minor style, readability, or preference suggestion. Does not block merge. | Optional |
| **N/A** | Not Applicable | The check does not apply to this change. | Skip |

## Merge Standards

The minimum bar for merging any PR:

- All **G / Gate** items pass
- **P0 = 0** (no unresolved blockers)
- Changes touching security, auth, database, dependencies, CI/CD, production config, or privacy data require review by a domain owner or expert
- Core functionality has tests. If no tests, the PR must document the reason, risk, and mitigation plan
- High-risk changes have a release, canary, rollback, or feature flag plan

## Per-Language Tooling Baseline

### JavaScript / TypeScript

| Tool Type | Recommended |
|-----------|------------|
| Formatter | Prettier |
| Linter | ESLint |
| Type Checker | `tsc --noEmit` |
| Test Runner | Jest, Vitest, Playwright, Cypress |
| Coverage | c8, nyc |
| Package Manager | npm, pnpm, yarn (lockfile committed) |

### Python

| Tool Type | Recommended |
|-----------|------------|
| Formatter | Black, Ruff format |
| Linter | Ruff |
| Type Checker | mypy, pyright |
| Test Runner | pytest |
| Coverage | coverage.py |
| Dependency/Security | pip-audit, OSV-Scanner, Bandit, Semgrep |
| Lockfile | requirements.txt, poetry.lock, uv.lock, Pipfile.lock |

### Go

| Tool Type | Recommended |
|-----------|------------|
| Formatter | `gofmt`, `go fmt` |
| Linter | `golangci-lint` |
| Vet | `go vet` |
| Test Runner | `go test ./...` |
| Coverage | `go test -cover` |
| Modules | go.mod + go.sum committed |

### Java / Kotlin

| Tool Type | Recommended |
|-----------|------------|
| Formatter | Spotless, ktlint |
| Linter | Checkstyle, PMD, SpotBugs, Detekt |
| Test Runner | JUnit |
| Coverage | JaCoCo |
| Build | Maven, Gradle (lockfile or version management clear) |

### Rust

| Tool Type | Recommended |
|-----------|------------|
| Formatter | `cargo fmt --check` |
| Linter | `cargo clippy` |
| Test Runner | `cargo test` |
| Coverage | cargo tarpaulin |
| Lockfile | Cargo.lock (commit per project convention) |

### Language-Agnostic (all projects)

| Tool Type | Recommended |
|-----------|------------|
| Secret Scanner | Gitleaks, TruffleHog, GitHub secret scanning |
| Dependency Scanner (SCA) | Dependabot, Renovate, npm audit, pip-audit, OSV-Scanner, OWASP Dependency-Check |
| Security Scanner (SAST) | Semgrep, CodeQL, Bandit, SonarQube |
| Container/IaC Scanner | Trivy, Grype, Checkov, tfsec, Terrascan |
| API Contract | OpenAPI validator, GraphQL schema check, Pact |

---

## Quality Gate Requirements

Every repository must have:

1. **Unified check command** — a single entry point (e.g., `make check`, `npm run check`, `pnpm check`) that runs at minimum: format check, lint, type check, unit tests
2. **CI runs the same command** as local development
3. **README documents** how to install and run these tools
4. **Tool versions are locked** — lockfile, tool version manager, Docker image, or CI action version pin
5. **CI fails closed** — formatter/linter/type checker/test/secret scan/SAST failures all block merge
6. **Exceptions are trackable** — `eslint-disable`, `# noqa`, `# type: ignore`, `// @ts-ignore` must have a reason referencing an issue or ticket. Whole-file suppression of checks requires owner approval
7. **Generated code is excluded** — generated code, vendored third-party code, and migration dumps have explicit exclude rules

---

## Suggested Automation Thresholds

Defaults; adjust per team and language. Thresholds must be in tool config and enforced by CI.

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| Line length | hard max 120 | Exceeding 120 harms side-by-side review |
| Function length | hard max 100, prefer 20-50 | Over 100 needs justification; split otherwise |
| File length | prefer < 500 | Large files suggest too many responsibilities; test files may exceed |
| Class length | prefer < 300-500 | Over this checks for God class |
| Parameter count | prefer ≤ 3, hard max 5 | Too many → parameter object, DTO, builder |
| Nesting depth | hard max 3-4 | Deep nesting → early return, guard clause, extract function |
| Cyclomatic complexity | prefer ≤ 10 | Over → split branches, strategy pattern, table-driven |
| Cognitive complexity | prefer ≤ 15 | More aligned with reading difficulty than cyclomatic |
| Statement count | prefer ≤ 30-50 | More stable than line count for JS/TS, Python |
| TODO count | zero ownerless TODOs | Every TODO must have an owner or issue |
| Test coverage | not below main branch baseline | Don't blindly chase percentages, but don't allow regression |

---

## Core Principles

1. **Tools over manual checks.** If a reviewer finds a recurring style or structural issue, the response is: "add this rule to tooling/CI." Do not nitpick individual violations that tools can catch.
2. **CI fails closed.** Every quality gate fails loudly. No silent degradation.
3. **Exceptions are tracked.** Every suppression references a ticket or documented reason.
4. **Reviewer judges context, not syntax.** Tools handle formatting and static rules. The reviewer focuses on design, business logic, security context, and risk.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-06 | Initial version — content migrated from code-review-checklist.md v2.0 §0, §1, §23 | Frank Xu |
