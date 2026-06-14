# SOP-1709: Code Review — AI-Assisted Code + Quick Reference

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-06
**Last reviewed:** 2026-05-06
**Status:** Active
**Related:** COR-1705 (REF — Classification System), COR-1706, COR-1707, COR-1708, COR-1602
**Task tags:** [review, code-review, ai-code, checklist, quick-reference]
**Disposition:** inherit-only

---

## What Is It?

Checklist for reviewing AI-generated or AI-assisted code changes, a condensed short-form PR checklist for quick reviews, and example tooling configurations. Use alongside COR-1602 and the domain-specific SOPs (COR-1706-1708).

---

## Why

AI-generated code has distinct failure modes: plausible-looking but incorrect logic, subtle security gaps, hallucinated APIs, and missing edge-case handling. Reviewers need a dedicated lens for these risks. The short-form checklist provides a lightweight alternative when full-domain checklists are overkill.

---

## When to Use

- Reviewing code that was generated or assisted by an LLM/AI tool
- Quick PR reviews that don't warrant the full COR-1706/1707/1708 checklists
- As a reference during COR-1602 multi-model parallel review

## When NOT to Use

- High-risk changes touching security, auth, or data integrity (use full COR-1707)
- Complex architectural changes (use full COR-1706)

---

## Item Type and Severity Legend

Per COR-1705 REF: **G** = Gate (tool/CI), **A** = Automated (should be tool-enforced), **H** = Human Review.
**P0** = Blocker, **P1** = Should Fix, **P2** = Nit.

---

## Steps

### 1. AI-Generated Code Review

- [ ] H-1.1 Authorship is transparent: AI-generated or AI-assisted sections are clearly identified. [P0]
- [ ] H-1.2 A human has reviewed, understood, and takes responsibility for every line. [P0]
- [ ] H-1.3 No hallucinated APIs, libraries, or functions — verify imports and calls exist. [P0]
- [ ] H-1.4 Generated code follows project conventions (naming, structure, patterns). [P1]
- [ ] H-1.5 Edge cases and error handling are complete — AI often omits these. [P1]
- [ ] H-1.6 No subtle security issues: hardcoded credentials, disabled validation, weak cryptography. [P0]
- [ ] H-1.7 Tests are meaningful, not just coverage-matching stubs. [P1]
- [ ] H-1.8 Generated comments are accurate — verify they describe what the code actually does. [P2]
- [ ] H-1.9 LLM/AI system changes: prompt changes, model version bumps, and output format changes are documented with before/after examples. [P1]
- [ ] H-1.10 AI system changes include evaluation results or manual validation evidence. [P1]

### 2. Short-Form PR Checklist

For quick PRs where full domain checklists are excessive. Still covers the essentials:

- [ ] H-2.1 Change is focused and well-described. [P1]
- [ ] H-2.2 Author self-check: tests pass locally, lint/format clean. [P0]
- [ ] H-2.3 No hardcoded secrets, no debug code left in. [P0]
- [ ] H-2.4 New behavior has tests; edge cases considered. [P1]
- [ ] H-2.5 No breaking changes without communication. [P0]
- [ ] H-2.6 Dependencies added are necessary and safe. [P1]
- [ ] H-2.7 Logging and error handling are adequate for production debugging. [P1]
- [ ] H-2.8 Performance impact is negligible or explicitly documented. [P2]

### 3. Example Tool Configurations

#### ESLint (JavaScript/TypeScript)

```json
{
  "rules": {
    "max-lines-per-function": ["warn", { "max": 100, "skipBlankLines": true, "skipComments": true }],
    "max-len": ["error", { "code": 120 }],
    "max-params": ["error", { "max": 5 }],
    "max-depth": ["error", { "max": 4 }],
    "complexity": ["warn", { "max": 10 }],
    "no-console": ["warn"],
    "no-unused-vars": ["error"],
    "no-duplicate-imports": ["error"]
  }
}
```

#### Prettier

```json
{
  "printWidth": 120,
  "tabWidth": 2,
  "semi": true,
  "singleQuote": true,
  "trailingComma": "all"
}
```

#### Ruff (Python)

```toml
[tool.ruff]
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.ruff.lint.pylint]
max-args = 5
max-branches = 12
max-returns = 6
max-statements = 50
```

#### Makefile (Unified Check Entry Point)

```makefile
.PHONY: check format lint type test

check: format lint type test
	@echo "All checks passed"

format:
	prettier --check .
	ruff format --check .

lint:
	eslint .
	ruff check .

type:
	tsc --noEmit
	mypy src/

test:
	pytest --cov --cov-report=term
```

---

## Core Principle

> If a reviewer finds a recurring pattern issue, the response is: **"Please add this rule to tooling/CI."** Do not nitpick individual violations. Reviewers focus on design, security, business logic, and risk — not formatting.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-06 | Initial version — content migrated from code-review-checklist.md v2.0 §20-22 | Frank Xu |
