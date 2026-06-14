# SOP-1500: TDD Development Workflow

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-17
**Last reviewed:** 2026-05-17
**Status:** Active
**Task tags:** [implement, feature, tdd, code, code-change, fix]
**Last executed:** —
**Workflow input:** task:routed
**Workflow output:** code:tested
**Disposition:** inherit-only

---

## What Is It?

A standardized Test-Driven Development workflow based on the Red-Green-Refactor cycle. Ensures every feature is built incrementally with tests written first, producing reliable, well-structured code.

---

## Why

Writing tests before code catches defects early, produces better-designed APIs, and provides a living specification that prevents regressions.

---

## When to Use

- New feature development
- Bug fixes (write a failing test that reproduces the bug first)
- Refactoring existing code (ensure tests exist before changing)
- Adding tests to legacy code (see Characterization Tests section below)

## When NOT to Use

- Quick prototypes or throwaway experiments
- Configuration-only changes
- Documentation updates
- Infrastructure/deployment scripts (Terraform, Dockerfiles)

---

## Prerequisites

- Test framework configured (e.g., pytest, jest, vitest)
- Linter/formatter configured (e.g., ruff, eslint, prettier)
- Coverage tooling configured (e.g., pytest-cov, c8, istanbul)
- Coverage threshold defined per project (recommended minimum: 80% line coverage for new code, enforced via `--cov-fail-under` / equivalent in CI)
- Clear requirements or acceptance criteria for the feature

---

## The Cycle: Red-Green-Refactor

### Phase 1: RED — Write a Failing Test

1. Pick the smallest testable behavior from requirements
2. Write the assertion first — think about the desired outcome before the mechanics
3. Write the rest of the test setup
4. Run the test — confirm it **fails**
5. Verify the failure is due to missing logic, not a broken test

```bash
# Run the single test for speed during development
pytest tests/test_feature.py::test_specific_behavior -v
# Expected: FAILED (red)
```

**Rules:**
- One behavior per test
- Test real behavior, not implementation details
- Include edge cases and error scenarios
- Each test must be independent — no shared mutable state, no ordering dependencies

#### Worker assignment

When the RED phase is dispatched to `<worker-agent>` (per COR-1619) AND the project's `<test-writer-worker-agent>` parameter is set to a value distinct from `<worker-agent>` (per COR-1622), the **test-writer worker** and the **implementer worker** for the GREEN phase MUST be distinct agent instances. "Distinct" means different model identifiers OR the same model with different `:instance` suffixes (e.g. `glm:writer` vs `glm:impl`).

Scope of the constraint: the same agent identity MUST NOT author both the failing tests and the GREEN-phase implementation for the **same task**, regardless of session boundaries (a fresh session by the same agent for the same task does not satisfy the rule). The rule applies until the CHG/PR is merged; subsequent CHGs are new tasks with their own assignment.

This rule subsumes COR-1500 §AI-Assisted TDD Protocol Mandatory Rule #3 ("Agent must not write test and implementation simultaneously"): a distinct-instance requirement is strictly stronger than the simultaneity ban.

When `<test-writer-worker-agent>` is unset (or equal to `<worker-agent>`), the two-worker split is OFF for this project; Rule #3 alone applies. The rest of this sub-section assumes the split is ON.

Opt out (use a single worker even when the split is ON; document the reason in the CHG `## Implementation Order` section):

| Opt-out class | Why single-worker is safe |
|---------------|---------------------------|
| Trivial single-function fix ≤ `<worker-min-loc>` (default 30) | COR-1619 routes this to the orchestrator already, so no worker is dispatched at all. |
| Refactor with pre-existing test coverage covering the changed surface | The existing tests are the spec; no new test authorship is needed. CHG must name the specific tests covering the change so the reviewer can assert adequacy. |
| Config / metadata-only change | No behaviour change to test; implement-to-fit bias has nothing to bias. |
| Characterization tests on legacy code | Tests capture *actual* behaviour, not desired behaviour; the bias mode does not apply. Same agent characterizes + refactors per COR-1500 §Characterization Tests (Legacy Code). |
| Generated test scaffolding | Deterministic codegen (e.g. pytest parametrize expansion, hypothesis strategies emitted from a schema); no human / agent judgment in the test body, so no bias to cross-validate. |
| Vendored code update with no behaviour change | Bumping a dependency / re-importing upstream code; the upstream tests are authoritative. |

Any other opt-out is a CHG-level argument and must be reviewed by the plan-review panel. In opt-out cases the two-worker split does not apply for this dispatch; COR-1500 §AI-Assisted TDD Protocol Mandatory Rule #3 (no simultaneous test+impl by one agent) alone governs.

**Test structure convention (Arrange-Act-Assert):**
```python
def test_empty_cart_returns_zero_total():
    # Arrange
    cart = ShoppingCart()

    # Act
    total = cart.get_total()

    # Assert
    assert total == 0
```
Use blank lines to separate each section. In BDD style this maps to Given-When-Then.

**Test naming convention:**
Use descriptive names that read like specifications:
- `test_login_rejects_invalid_password`
- `test_empty_cart_returns_zero_total`
- NOT: `test_login_2`, `test_case_a`

### Phase 2: GREEN — Make It Pass

1. Write the **minimum** code to make the test pass
2. No extra features, no premature optimization
3. Run all tests — confirm **all green**

```bash
# Run full suite before considering GREEN complete
pytest -v
# Expected: ALL PASSED (green)
```

**Rules:**
- Resist the urge to write more than needed
- If you need to break another test to pass this one, stop and rethink
- Prefer simple transformations: constant → variable → conditional → iteration (see Transformation Priority Premise in References)
- When the two-worker split is in effect (i.e. RED was dispatched to a distinct test-writer worker per Phase 1's "Worker assignment" sub-section), the implementer worker MUST NOT read the test-writer's structured report, prose commentary, or session transcripts. The implementer reads (a) the failing test files committed by the test-writer, (b) the CHG/PRP body, and (c) the production source tree being modified — i.e., the existing codebase under change. The constraint forbids only the test-writer's *commentary channel*; the test is the spec, and the source is the substrate. Commentary may leak the test-writer's intended implementation, defeating the cross-validation the split exists to provide.

### Phase 3: REFACTOR — Clean Up

1. Improve code quality without changing behavior
2. Remove duplication, improve naming, simplify logic
3. Run all tests — confirm **still green**

```bash
# Lint and format
ruff check . && ruff format .   # Python
# or: eslint . && prettier -w .  # JS/TS

# Run tests
pytest -v                        # Python
# or: npm test                   # JS/TS
# Expected: ALL PASSED (green)
```

**Rules:**
- Never refactor on red
- Small steps — one improvement at a time
- If tests break during refactor, revert and try smaller steps
- Do not introduce new abstractions unless explicitly needed

**Exit criteria — refactor is done when:**
1. No duplication exists between the new code and existing code
2. All names clearly express intent
3. No function exceeds a reasonable length (~20 lines)
4. Linter passes clean
5. You cannot simplify further without changing behavior

---

## Worked Example: One Full Cycle

**Requirement:** A shopping cart should calculate the total price of its items.

### RED — Write a failing test

```python
# tests/test_cart.py
def test_add_item_calculates_correct_total():
    # Arrange
    cart = ShoppingCart()

    # Act
    cart.add_item("Apple", price=1.50)
    cart.add_item("Bread", price=2.00)

    # Assert
    assert cart.get_total() == 3.50
```

```bash
$ pytest tests/test_cart.py::test_add_item_calculates_correct_total -v
# FAILED: NameError: name 'ShoppingCart' is not defined
# (import intentionally omitted — this IS the expected failure at RED)

```

### GREEN — Minimal implementation

```python
# cart.py
class ShoppingCart:
    def __init__(self):
        self.items = []

    def add_item(self, name, price):
        self.items.append(price)

    def get_total(self):
        return sum(self.items)
```

```bash
$ pytest -v
# PASSED ← all green
```

### REFACTOR — Clean up

```python
# cart.py (refactored: store item as named tuple for future extensibility)
from typing import NamedTuple

class Item(NamedTuple):
    name: str
    price: float

class ShoppingCart:
    def __init__(self):
        self.items: list[Item] = []

    def add_item(self, name: str, price: float):
        self.items.append(Item(name, price))

    def get_total(self) -> float:
        return sum(item.price for item in self.items)
```

```bash
$ pytest -v   # still green
$ ruff check . && ruff format .  # clean
```

---

## Characterization Tests (Legacy Code)

When adding TDD to existing untested code, write **characterization tests** first:

1. **Don't assume what the code should do** — test what it actually does
2. Write tests that capture the current behavior, even if it seems wrong
3. Run them to confirm they pass against the existing code
4. Now you have a safety net — apply Red-Green-Refactor as normal

```python
# Characterization test: capture existing behavior before changing anything
def test_legacy_calculate_tax_current_behavior():
    result = legacy_calculate_tax(100.0)
    assert result == 8.25  # whatever it currently returns — lock it in
```

Once characterized, any refactoring that breaks a characterization test means you changed behavior — either fix your refactor or update the spec intentionally.

> Reference: Michael Feathers — *Working Effectively with Legacy Code* (2004)

---

## AI-Assisted TDD Protocol

When delegating TDD work to an AI agent (Claude Code, Codex, GLM):

### Mandatory Rules

1. **Agent writes the failing test first** and runs it to confirm RED — do not let the agent skip running the test
2. **Agent must show test output** at each phase (RED, GREEN, REFACTOR) — no "trust me it passes"
3. **Agent must not write test and implementation simultaneously** — enforce the cycle even when the agent "knows" the answer
4. **Human reviews test quality** before approving GREEN phase — AI tends to write tests that mirror implementation rather than specify behavior
5. **During REFACTOR, agent must not over-refactor** — keep refactoring proportional to the code written, no new patterns or abstractions unless requested

### AI-Specific Pitfalls

| Pitfall | How to Detect |
|---------|--------------|
| Tests that are just mocks | Test has more mock setup than assertions |
| Tests that pass by coincidence | Hardcoded expected values that happen to match |
| Over-complex test fixtures | Setup is longer than the test itself |
| Skipping RED phase | Agent writes test + impl in one step |
| Over-refactoring | Agent introduces patterns/abstractions not in requirements |

### Prompt Templates

**Starting a TDD cycle:**
> "Write a failing test for [behavior]. Run it and confirm it fails. Do not write any implementation code yet. Show me the test output."

**Moving to GREEN:**
> "Now write the minimum code to make the test pass. Run all tests and show the output."

**Refactoring:**
> "Refactor the implementation. Do not add new features or abstractions. Run all tests to confirm they still pass."

---

## Test Execution Strategy

| Context | What to Run |
|---------|------------|
| During RED/GREEN (inner loop) | Single test for speed: `pytest tests/test_x.py::test_specific -v` |
| Before committing | Full test suite: `pytest -v` |
| Before PR/merge | Full suite + lint + format check |

---

## Definition of Done

### Cycle DoD — When is a single Red-Green-Refactor cycle complete?

| Check | Status |
|-------|--------|
| RED: Test written and confirmed failing | ☐ |
| GREEN: Minimum code makes test pass, full suite still green | ☐ |
| REFACTOR: Code cleaned up, lint passes, all tests still green | ☐ |

All three boxes must be checked before starting the next cycle.

### Phase DoD — When is a phase (batch of cycles) complete?

Customize per project. Template:

| Check | Status |
|-------|--------|
| All planned cycles completed | ☐ |
| Full test suite passes (`make check` or equivalent) | ☐ |
| Coverage meets project threshold (e.g., ≥ 90%) | ☐ |
| Module can be independently imported / deployed | ☐ |
| No unintended modifications to existing code | ☐ |
| Code reviewed or self-reviewed | ☐ |
| Progress Tracker fully checked off (see below) | ☐ |
| Changes committed and pushed | ☐ |

---

## Progress Tracker

Use this template to track TDD cycles within a phase. Copy and fill in per project/phase.

```markdown
### Phase: [Phase Name]

| # | Cycle Description | RED | GREEN | REFACTOR |
|---|-------------------|-----|-------|----------|
| 1 | [behavior]        | ☐   | ☐     | ☐        |
| 2 | [behavior]        | ☐   | ☐     | ☐        |
| 3 | [behavior]        | ☐   | ☐     | ☐        |
| … | …                 | ☐   | ☐     | ☐        |

**Phase DoD:**
- [ ] All cycles complete
- [ ] `make check` passes
- [ ] Coverage ≥ [threshold]%
- [ ] Reviewed
- [ ] Committed
```

---

## Commit Strategy

Two options — choose one per project and stay consistent:

**Option A: Commit per phase** (full traceability)

| Phase | Commit prefix | Example |
|-------|--------------|---------|
| RED | `test:` | `test: add failing test for user login` |
| GREEN | `feat:` or `fix:` | `feat: implement user login` |
| REFACTOR | `refactor:` or `style:` | `refactor: extract auth helper` |

**Option B: Squash RED+GREEN** (CI-friendly, no broken commits)

| Commit | Prefix | Example |
|--------|--------|---------|
| Test + implementation | `feat:` or `fix:` | `feat: add user login with tests` |
| Refactor (separate) | `refactor:` | `refactor: extract auth helper` |

> If your CI runs on every commit, prefer Option B to avoid red commits in history.

---

## Common Pitfalls

| Pitfall | How to Avoid |
|---------|-------------|
| Writing too many tests at once | One test at a time, one cycle at a time |
| Writing tests that test mocks, not behavior | Test inputs and outputs, not internal wiring |
| Skipping the refactor phase | Treat it as mandatory, not optional |
| Writing more code than needed in GREEN | If it's not needed to pass the test, don't write it |
| Testing implementation details | If you rename a private method and tests break, tests are too coupled |
| Shared mutable state between tests | Each test sets up and tears down its own state |

---

## Integration with CI/CD

```bash
# Python
ruff check .
ruff format --check .
pytest -v --tb=short --cov --cov-fail-under=80

# JavaScript/TypeScript
eslint .
prettier --check .
npm test -- --coverage --coverageThreshold='{"global":{"lines":80}}'
```

---

## Safety Notes

- Never merge code with failing tests
- Never disable a test to make CI pass — fix the code or fix the test
- If a test is flaky, fix it immediately or mark it with `@pytest.mark.xfail(reason="...")` / `it.skip("reason")` and link a tracking issue

---

## References

- Kent Beck — *Test Driven Development: By Example* (2002)
- Martin Fowler — [Refactoring Catalog](https://refactoring.com/catalog/)
- Martin Fowler — [TestDrivenDevelopment](https://martinfowler.com/bliki/TestDrivenDevelopment.html)
- Robert C. Martin — *Transformation Priority Premise*
- Michael Feathers — *Working Effectively with Legacy Code* (2004)

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-10 | Initial version | Claude Code |
| 2026-03-10 | Added AI-assisted TDD protocol, test naming/isolation, commit strategy options, test execution strategy, references (per GPT-5.2 review) | Claude Code |
| 2026-03-10 | Added coverage checklist item, flaky test marking guidance, TPP reference link (per GPT-5.2 second review) | Claude Code |
| 2026-03-10 | Added worked example, characterization tests for legacy code, AAA test structure, refactor exit criteria, coverage threshold defaults (targeting 10/10 per GPT-5.2 third review) | Claude Code |
| 2026-03-10 | Added --cov-fail-under to CI examples, clarified import omission in worked example (final 0.5 polish per GPT-5.2) | Claude Code |
| 2026-03-14 | PDCA + Johnny Decimal migration: renamed from ALF-1004 to ALF-2100 | Claude Code |
| 2026-03-15 | Added Definition of Done (Cycle DoD + Phase DoD) and Progress Tracker template | Claude Code |
| 2026-03-20 | Added Why section per FXA-2223 | Claude Code |
| 2026-05-17 | FXA-2287 (CHG-A of PRP-1507): added §Phase 1 (RED) "Worker assignment" sub-section gating on `<test-writer-worker-agent>` with 6-row opt-out table and Rule #3 subsumption sentence. FXA-2288 (CHG-B of PRP-1507): appended Phase 2 (GREEN) implementer reading constraint as new "Rules:" bullet. Two CHGs bundled in PR closing issue #175. | Claude Opus 4.7 |
