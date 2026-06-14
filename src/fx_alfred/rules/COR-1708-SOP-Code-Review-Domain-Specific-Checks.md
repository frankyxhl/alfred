# SOP-1708: Code Review — Domain-Specific Checks

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-06
**Last reviewed:** 2026-05-06
**Status:** Active
**Related:** COR-1705 (REF — Classification System), COR-1706, COR-1707, COR-1602
**Task tags:** [review, code-review, frontend, backend, config, iac, pr-checklist]
**Disposition:** inherit-only

---

## What Is It?

Domain-specific checklist for code review: PR/MR entry checks, frontend, backend, configuration/IaC, and documentation/review quality. Use this SOP alongside COR-1602 when reviewing changes in these domains.

---

## Why

Different surfaces have different failure modes. Frontend bugs manifest as UI glitches or accessibility violations. Backend bugs manifest as data corruption or service outages. Config changes can take down production silently. A generic checklist misses domain-specific risks.

---

## When to Use

- Code review touching frontend, backend, config, or infrastructure code
- As a reference during COR-1602 multi-model parallel review for domain-specific changes

## When NOT to Use

- Changes that are purely structural (use COR-1706) or purely cross-cutting (use COR-1707)

---

## Item Type and Severity Legend

Per COR-1705 REF: **G** = Gate (tool/CI), **A** = Automated (should be tool-enforced), **H** = Human Review.
**P0** = Blocker, **P1** = Should Fix, **P2** = Nit.

---

## Steps

### 1. PR/MR Entry Checks

- [ ] H-1.1 PR title clearly describes the change. [P1]
- [ ] H-1.2 Description explains: why, what changed, how to verify. [P1]
- [ ] H-1.3 Linked to issue, ticket, requirement, design doc, or incident postmortem. [P1]
- [ ] H-1.4 Reviewer does not need to guess business context. [P1]
- [ ] H-1.5 Change is focused on one topic. [P1]
- [ ] H-1.6 No unrelated formatting, refactoring, dependency upgrades, or experimental code mixed in. [P1]
- [ ] H-1.7 Large PR can be split into smaller, reviewable PRs. [P1]
- [ ] H-1.8 Deleted code has no remaining callers, feature flag dependencies, or historical data dependencies. [P1]
- [ ] G-1.9 Author has run the unified check command. [P0]
- [ ] H-1.10 Author has described testing approach. [P1]
- [ ] H-1.11 Author has noted risks, known limitations, and rollback plan. [P1]
- [ ] H-1.12 Author has flagged files or logic needing focused review. [P1]

### 2. Frontend

- [ ] H-2.1 Component state management is clear: loading, empty, error, and edge-case states are handled. [P1]
- [ ] H-2.2 UI is responsive; no layout breakage at common viewport sizes. [P1]
- [ ] H-2.3 Accessibility: semantic HTML, ARIA labels where needed, keyboard navigation, focus management. [P1]
- [ ] H-2.4 No render-blocking resources; lazy loading where appropriate. [P1]
- [ ] H-2.5 User input is validated client-side AND server-side. [P1]
- [ ] H-2.6 No sensitive data exposed in client-side code or bundled assets. [P0]
- [ ] H-2.7 Bundle size impact is considered for new dependencies. [P2]

### 3. Backend

- [ ] H-3.1 Service boundaries are respected; no direct cross-service database access. [P1]
- [ ] H-3.2 Operations are idempotent where required (retry-safe). [P1]
- [ ] H-3.3 Background jobs and message handlers handle partial failures and poison messages. [P1]
- [ ] H-3.4 Timeouts are configured for all external calls; no unbounded waits. [P1]
- [ ] H-3.5 Graceful degradation: service remains functional (possibly degraded) when dependencies are unavailable. [P1]
- [ ] H-3.6 Rate limiting and circuit breaking are applied to external-facing endpoints. [P1]

### 4. Configuration and Infrastructure as Code

- [ ] H-4.1 Configuration changes are scoped to the intended environment only. [P0]
- [ ] H-4.2 Secrets are not in configuration files; use secret management (vault, secrets manager, sealed secrets). [P0]
- [ ] H-4.3 IaC changes have a clear plan/apply diff; no unexpected resource destruction. [P0]
- [ ] H-4.4 New infrastructure resources are tagged, have cost labels, and comply with naming conventions. [P1]
- [ ] H-4.5 Deployment order is considered: schema migrations before code, config before deployment, etc. [P1]
- [ ] H-4.6 Rollback plan is documented and tested for IaC changes. [P1]

### 5. Documentation and Review Quality

- [ ] H-5.1 Relevant documentation is updated (README, API docs, runbooks, ADRs). [P1]
- [ ] H-5.2 Review comments are actionable: specific file:line, clear expected change. [P2]
- [ ] H-5.3 Reviewer distinguishes blocking (P0) from advisory (P1/P2). [P2]
- [ ] H-5.4 Reviewer prioritizes: tools should catch style/formatter issues; reviewer focuses on design, security, and correctness. [P1]

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-06 | Initial version — content migrated from code-review-checklist.md v2.0 §2, §16-19 | Frank Xu |
