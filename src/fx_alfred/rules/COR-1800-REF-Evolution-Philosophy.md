# REF-1800: Evolution Philosophy

**Applies to:** All projects using the COR document system
**Last updated:** 2026-04-04
**Last reviewed:** 2026-04-04
**Status:** Active

---

## What Is It?

Universal reference document providing principles, evaluation framework, and rubrics for project self-evolution. Projects create their own PRJ-layer evolve SOPs based on this REF.

---

## Core Principle

**Compression as Intelligence:**

```
Fitness = same behavior / (lines of code + document words)
```

Direction priority: determinism first, minimization second.

---

## Evolution Cycle

Universal, project-agnostic cycle. Each project defines its own signal sources and implementation workflow in PRJ-layer SOPs.

```
Signal Collection → Candidate Generation → Evaluation → Implementation → Review → PR
```

---

## Evaluation Rubric

Numeric, project-customizable via COR-to-PRJ override contract (see below).

### Code Evolution (default weights)

| Dimension | Weight | Measures |
|-----------|--------|----------|
| Test verifiability | 35% | Can tests cover the change? |
| Scope restraint | 30% | Clear boundary, no cascade? |
| Backward compatibility | 20% | Existing interfaces unchanged? |
| Necessity | 15% | Concrete evidence, not "feels improvable"? |

### Document Evolution (default weights)

| Dimension | Weight | Measures |
|-----------|--------|----------|
| Necessity | 30% | Evidence from validate/issues/logs? |
| Consistency | 25% | No conflict with other SOPs? |
| Atomicity | 20% | One SOP = one thing preserved? |
| Actionability | 15% | Agent can execute more precisely? |
| Impact | 10% | How frequently referenced? |

---

## Thresholds

| Parameter | Default | Notes |
|-----------|---------|-------|
| Candidate discard | < 7.0 | Below this, candidate is dropped |
| Review pass | >= 9.0 | Both reviewers must reach this |

---

## Signal Sources

Reference catalog. Projects pick what applies to their context.

| Signal | Applicable to |
|--------|--------------|
| Test failures | Any project with tests |
| Lint/type check issues | Any project with linter |
| Coverage gaps | Any project with coverage tooling |
| Source analysis (duplication, dead code) | All code projects |
| SOP vs implementation gap | Projects using alfred |
| Dependency audit | Projects with package managers |

---

## Guard Rails

- Evolution process must not modify its own philosophy/SOP documents (prohibited mutation surface)
- Threshold and weight updates require standard PRP/CHG lifecycle, not the evolve process itself

---

## COR-to-PRJ Override Contract

Projects customize evolution by creating a PRJ-layer REF that overrides COR-1800 defaults.

### How to Override

1. **Create** a PRJ REF (e.g., `FXA-2146-REF-Evolution-Philosophy.md`) that references COR-1800
2. **Override** any weight table by redefining it **in full** — partial tables are not allowed; overridden weight tables must sum to 100%
3. **Override** thresholds or signal sources by redefining the relevant table (also full-replace per table)
4. **Add** project-specific dimensions by defining a new weight table (must sum to 100%)
5. **Omit** sections to inherit COR-1800 defaults — only overridden tables need to be stated
6. Evolve SOPs in the PRJ layer reference the PRJ REF for weights; fall back to COR-1800 for anything not overridden

### Merge Semantics

**Full-replace per table.** A PRJ REF never partially merges with a COR table — it either replaces the entire table or inherits it unchanged.

---

## Relationship to Project SOPs

```
COR-1800-REF (philosophy + rubrics + override contract)
  └── PRJ: Evolution-Philosophy REF (weight/threshold overrides, optional)
  └── PRJ: Evolve-Code SOP (project-specific code evolution)
  └── PRJ: Evolve-SOP SOP (project-specific SOP evolution, optional)
```

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version per PRP FXA-2198 and CHG FXA-2199 | Claude Code |
