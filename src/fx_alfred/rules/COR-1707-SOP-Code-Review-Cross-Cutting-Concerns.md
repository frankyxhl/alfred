# SOP-1707: Code Review — Cross-Cutting Concerns

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-06
**Last reviewed:** 2026-05-06
**Status:** Active
**Related:** COR-1705 (REF — Classification System), COR-1706, COR-1602, COR-1610
**Task tags:** [review, code-review, security, privacy, performance, testing, observability]

---

## What Is It?

Domain-specific checklist for cross-cutting concerns in code review: security, privacy, dependencies/supply chain, tests, performance, and observability. Use this SOP alongside COR-1602 when reviewing changes that touch any of these areas.

---

## Why

Cross-cutting concerns are the most common source of production incidents — and the hardest to catch without a structured checklist. Security vulnerabilities, performance regressions, and observability gaps often pass review because reviewers focus on logic correctness.

---

## When to Use

- Code review where the change touches: auth, data access, external services, new dependencies, performance-sensitive paths, logging/metrics
- Any change that handles user data or credentials
- As a reference during COR-1602 multi-model parallel review

## When NOT to Use

- Trivial changes with no security, performance, or data implications
- Pure documentation or configuration changes (use COR-1708 for config/IaC)

---

## Item Type and Severity Legend

Per COR-1705 REF: **G** = Gate (tool/CI), **A** = Automated (should be tool-enforced), **H** = Human Review.
**P0** = Blocker, **P1** = Should Fix, **P2** = Nit.

---

## Steps

### 1. Security

- [ ] H-1.1 All user input is validated, sanitized, or parameterized. No string concatenation into SQL, shell, or HTML. [P0]
- [ ] H-1.2 Authentication and authorization checks are present on every protected endpoint/operation. [P0]
- [ ] H-1.3 Secrets (API keys, tokens, passwords, private keys) are never hardcoded, committed, or logged. [P0]
- [ ] A-1.4 Secret scanning passes in CI (Gitleaks, TruffleHog, etc.). [P0]
- [ ] H-1.5 Session and token management: secure, httponly, SameSite flags on cookies; short-lived tokens; refresh token rotation. [P1]
- [ ] H-1.6 Encryption uses standard libraries and accepted algorithms. No custom cryptography. [P0]
- [ ] H-1.7 Error messages and logs do not leak sensitive data (PII, credentials, internal paths, stack traces in production). [P0]
- [ ] H-1.8 Access control is enforced server-side; client-side checks are UX only. [P0]
- [ ] H-1.9 File uploads have size limits, type validation, and are scanned if applicable. [P1]
- [ ] A-1.10 SAST passes in CI (Semgrep, CodeQL, etc.). [P1]

### 2. Privacy

- [ ] H-2.1 Data collected is minimal for the feature's purpose. [P1]
- [ ] H-2.2 PII is stored only when necessary; encrypted at rest and in transit. [P0]
- [ ] H-2.3 Data retention and deletion policies are respected. [P1]
- [ ] H-2.4 Compliance requirements (GDPR, CCPA, HIPAA, etc.) are considered for the data involved. [P1]
- [ ] H-2.5 Logging and analytics do not capture PII without explicit user consent. [P1]

### 3. Dependencies and Supply Chain

- [ ] H-3.1 New dependencies are justified: does the dependency solve a non-trivial problem? Is there a stdlib alternative? [P1]
- [ ] H-3.2 Dependency license is compatible with the project. [P1]
- [ ] H-3.3 Dependency is actively maintained (recent commits, responsive to security issues). [P1]
- [ ] H-3.4 Dependency is pinned to a specific version or range. [P1]
- [ ] A-3.5 Dependency scan passes in CI (Dependabot, Renovate, OSV-Scanner, etc.). [P0 for Critical/High CVEs]
- [ ] H-3.6 Build artifacts are reproducible; no unreproducible binary blobs committed. [P1]

### 4. Tests

- [ ] H-4.1 New behavior has corresponding tests. [P0]
- [ ] H-4.2 Tests verify behavior, not implementation details. [P1]
- [ ] H-4.3 Edge cases are covered: empty input, null, boundary values, error paths. [P1]
- [ ] H-4.4 Tests are deterministic — no flaky tests introduced. [P1]
- [ ] H-4.5 Test names describe the scenario and expected outcome. [P2]
- [ ] H-4.6 Test coverage does not drop below the main branch baseline. [P1]
- [ ] H-4.7 Integration tests cover external service boundaries (DB, API, message queue). [P1]
- [ ] H-4.8 Tests are maintainable: shared fixtures are clear, test helpers are documented. [P2]

### 5. Performance

- [ ] H-5.1 Algorithmic complexity is appropriate for expected input size. [P1]
- [ ] H-5.2 Database queries are efficient: no N+1 queries, appropriate indexes exist. [P1]
- [ ] H-5.3 I/O operations (network calls, file reads) are batched, cached, or parallelized where appropriate. [P1]
- [ ] H-5.4 Caching strategy is documented: TTL, invalidation, cache key design. [P1]
- [ ] H-5.5 Memory usage is bounded: no unbounded collections, streaming for large payloads. [P1]
- [ ] H-5.6 Cost implications considered (cloud resource provisioning, API rate limits, data transfer). [P2]

### 6. Observability

- [ ] H-6.1 Key operations are logged at appropriate levels (INFO for business events, DEBUG for diagnostics, ERROR for failures). [P1]
- [ ] H-6.2 Log messages include enough context for debugging (request ID, user ID, operation). [P1]
- [ ] H-6.3 Metrics are emitted for business-critical operations (latency, error rate, throughput). [P1]
- [ ] H-6.4 Distributed tracing context is propagated across service boundaries. [P1]
- [ ] H-6.5 Alerts are defined for new failure modes; dashboards updated if relevant. [P2]
- [ ] H-6.6 Release control: feature flags, canary deployment, or gradual rollout plan exists for high-risk changes. [P1]
- [ ] H-6.7 Health check endpoints reflect actual service health, not just "process is running." [P1]

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-06 | Initial version — content migrated from code-review-checklist.md v2.0 §10-15 | Frank Xu |
