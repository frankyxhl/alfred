# PRP-2198: COR-Evolution-Philosophy-Reference

**Applies to:** All projects using the COR document system
**Last updated:** 2026-04-04
**Last reviewed:** 2026-04-04
**Status:** Approved

---

## What Is It?

Proposal to create **COR-1800-REF-Evolution-Philosophy** — a universal reference document that provides the principles, evaluation framework, and rubrics for project self-evolution. Projects create their own PRJ-layer evolve SOPs based on this REF.

---

## Problem

The evolution methodology (signal → evaluate → implement → review) is currently locked inside FXA-specific documents (FXA-2146, FXA-2148, FXA-2149). Other projects cannot reuse the approach without copy-pasting and adapting. There is no COR-layer guidance for self-evolution.

## Proposed Solution

Create **COR-1800-REF-Evolution-Philosophy** containing:

### 1. Core Principle
- **Compression as Intelligence**: `Fitness = same behavior / (lines of code + document words)`
- Direction priority: determinism first, minimization second

### 2. Evolution Cycle (universal, project-agnostic)
```
Signal Collection → Candidate Generation → Evaluation → Implementation → Review → PR
```
Each project defines its own signal sources and implementation workflow in PRJ-layer SOPs.

### 3. Evaluation Rubric (numeric, project-customizable)

**Default weights (code evolution):**

| Dimension | Weight | Measures |
|-----------|--------|----------|
| Test verifiability | 35% | Can tests cover the change? |
| Scope restraint | 30% | Clear boundary, no cascade? |
| Backward compatibility | 20% | Existing interfaces unchanged? |
| Necessity | 15% | Concrete evidence, not "feels improvable"? |

**Default weights (document evolution):**

| Dimension | Weight | Measures |
|-----------|--------|----------|
| Necessity | 30% | Evidence from validate/issues/logs? |
| Consistency | 25% | No conflict with other SOPs? |
| Atomicity | 20% | One SOP = one thing preserved? |
| Actionability | 15% | Agent can execute more precisely? |
| Impact | 10% | How frequently referenced? |

### 4. Thresholds

| Parameter | Default | Notes |
|-----------|---------|-------|
| Candidate discard | < 7.0 | Below this, candidate is dropped |
| Review pass | >= 9.0 | Both reviewers must reach this |

### 5. Signal Sources (reference catalog, pick what applies)

| Signal | Applicable to |
|--------|--------------|
| Test failures | Any project with tests |
| Lint/type check issues | Any project with linter |
| Coverage gaps | Any project with coverage tooling |
| Source analysis (duplication, dead code) | All code projects |
| SOP vs implementation gap | Projects using alfred |
| Dependency audit | Projects with package managers |

### 6. Guard Rails
- Evolution process must not modify its own philosophy/SOP documents (prohibited mutation surface)
- Threshold and weight updates require standard PRP/CHG lifecycle, not the evolve process itself

### 7. COR-to-PRJ Override Contract

Projects customize evolution by creating a PRJ-layer REF that overrides COR-1800 defaults:

1. **Create** a PRJ REF (e.g., `FXA-2146-REF-Evolution-Philosophy.md`) that references COR-1800
2. **Override** any weight table by redefining it **in full** — partial tables are not allowed; overridden weight tables must sum to 100%. This is a full-replace semantic: the PRJ table completely replaces the COR table for that rubric
3. **Override** thresholds or signal sources by redefining the relevant table (also full-replace per table)
4. **Add** project-specific dimensions by defining a new weight table (must sum to 100%)
5. **Omit** sections to inherit COR-1800 defaults — only overridden tables need to be stated
6. Evolve SOPs in the PRJ layer reference the PRJ REF for weights; fall back to COR-1800 for anything not overridden

**Merge semantics:** full-replace per table. A PRJ REF never partially merges with a COR table — it either replaces the entire table or inherits it unchanged.

### 8. Relationship to Project SOPs
```
COR-1800-REF (philosophy + rubrics + override contract)
  └── PRJ: Evolution-Philosophy REF (weight/threshold overrides, optional)
  └── PRJ: Evolve-Code SOP (project-specific code evolution)
  └── PRJ: Evolve-SOP SOP (project-specific SOP evolution, optional)
```

**Files created:** `src/fx_alfred/rules/COR-1800-REF-Evolution-Philosophy.md` (1 file, PKG layer — bundled with fx-alfred)

### 9. Migration from FXA-2146

After COR-1800 is created:
1. FXA-2146 retains only FXA-specific overrides (weights that differ from COR-1800 defaults, prohibited mutation surface for FXA files)
2. FXA-2148/2149 reference COR-1800 for philosophy, FXA-2146 for project overrides
3. No breaking changes — FXA-2146 currently defines the same values that become COR-1800 defaults

This migration is **out of scope** for this PRP; it will be a separate CHG after COR-1800 ships.

## Scope

| In scope | Out of scope |
|----------|-------------|
| Universal evolution principles | Project-specific SOPs (FXA-2148, FXA-2149) |
| Default rubric weights + thresholds | Implementation details (branches, CI, `/trinity`) |
| Signal source catalog | Signal collection commands |
| Guard rails + prohibited mutation surface | Workflow selection (use COR-1606) |
| COR-to-PRJ override contract | Migrating FXA-2146 to inherit from COR-1800 (separate CHG) |

## Risk Awareness

1. **Over-generalization**: Defaults may not fit all project types (e.g., a pure documentation project has no "test verifiability"). Mitigated by the override contract — projects replace any dimension.
2. **Scoring inconsistency across projects**: Different PRJ overrides may make cross-project comparisons meaningless. Acceptable — evolution is project-internal, not cross-project.
3. **Drift from COR defaults**: Projects may override so heavily that COR-1800 provides no value. Mitigated by keeping COR-1800 minimal (philosophy + defaults, not enforcement).
4. **Two-layer maintenance overhead**: Projects now maintain both a PRJ REF and evolve SOPs. Mitigated by making the PRJ REF optional — projects can use COR-1800 defaults directly.

## Open Questions

None.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version | — |
| 2026-04-04 | R2: Add Risk Awareness, COR-to-PRJ override contract, migration plan, fix metadata/path (Codex 7.9, Gemini 7.9) | Claude Code |
| 2026-04-04 | R3: Define full-replace merge semantics, require weight tables sum to 100% (Codex 8.9, Gemini 9.6) | Claude Code |
