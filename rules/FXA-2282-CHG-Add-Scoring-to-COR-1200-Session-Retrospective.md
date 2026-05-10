# CHG-2282: Add §Scoring to COR-1200 Session Retrospective

**Applies to:** FXA project
**Last updated:** 2026-05-10
**Last reviewed:** 2026-05-10
**Status:** Proposed
**Date:** 2026-05-10
**Requested by:** Frank Xu (session 2026-05-10)
**Priority:** Medium
**Change Type:** Normal
**Targets:** `src/fx_alfred/rules/COR-1200-SOP-Session-Retrospective.md`
**Closes:** #134

---

## What

Add `## Scoring` section to COR-1200 (Session Retrospective) containing:

1. Signal taxonomy — six named finding classes (five specific + one catch-all)
2. Scoring rubric — four weighted dimensions (Frequency 35% / Actionability 30% / Impact 20% / Detection gap 15%), each scored 0–10 with anchor descriptions at 0, 5, 10
3. Action thresholds — ≥7.5 → create GitHub issue; 5.0–7.4 → log only; <5.0 → discard
4. Calibration examples — four worked examples with numeric composites

Also add one-line §Scoring references to §Step 2, §Step 3, and §Step 4; add `### Scored Findings` subsection to §Step 5 template.

## Why

COR-1200 §Steps 2–4 identify patterns qualitatively but provide no scoring rubric and no objective criterion for when a finding should become a tracked GitHub issue. This leads to over-escalation of one-off noise and under-escalation of recurrent systematic gaps. Issue #133 (per-PR loop retrospective in COR-1617 §Phase 11) also needs a principled threshold rather than a hard-coded count rule.

## Surfaces

| File | Change |
|------|--------|
| `src/fx_alfred/rules/COR-1200-SOP-Session-Retrospective.md` | Insert `## Scoring` section after `## Steps`; add one line to §Step 2, §Step 3, §Step 4; add `### Scored Findings` subsection to §Step 5 template; add Change History row |

**Out of scope:** New document creation, changes to COR-1617, PRJ-layer override contract.

**Soft dependency:** After issue #135 (COR-1802 SOP) merges, add one back-reference line in §Scoring rubric intro pointing to COR-1802. Ships independently — §Scoring is self-contained.

## Implementation Plan

1. Edit `COR-1200`: insert `## Scoring` section after `## Steps` (before `## Example`)
2. Add "Score the finding per §Scoring; proceed with the indicated action" to §Step 2, §Step 3, §Step 4
3. Add `### Scored Findings` subsection to §Step 5 template (after Key Learnings)
4. Add Change History row
5. `af validate --root /Users/frank/Projects/alfred` — must pass
6. Push branch, open PR with `Closes #134`; verify `closingIssuesReferences`
7. Trinity fast-review (glm + deepseek); iterate until both ≥ 9.0 and codex bot clean

## §Scoring Draft Content

> Inserted in COR-1200 as `## Scoring`, after `## Steps`.

### Signal taxonomy

Six finding classes. Classify each retro finding into the most specific matching class:

| Class | Description |
|-------|-------------|
| **Recurrent finding** | Same finding type appeared in ≥2 distinct contexts (rounds, PRs, or sessions) |
| **Detection gap** | Primary detector (trinity panel) missed what secondary caught (codex bot, human) |
| **Late convergence** | Finding required R3+ rounds to resolve — not caught or prevented early |
| **Process skip** | A mandatory SOP guard rail or step was not executed |
| **Tooling gap** | Repeated manual step that could be scripted or added as an `af` command |
| **Other** | Finding does not match any class above; describe in one sentence |

### Scoring rubric

Score 0–10 on each dimension. Composite = Σ(weight × score).

| Dimension | Weight | 0 | 5 | 10 |
|-----------|--------|---|---|-----|
| **Frequency** | 35% | First time seen in any context | Appeared in 2 distinct contexts | ≥3 distinct PRs or sessions |
| **Actionability** | 30% | Vague ("be more careful"); no concrete target | Has a target SOP/file but amendment wording unclear | Specific target section + one-sentence amendment drafted now |
| **Impact** | 20% | No visible slowdown | Caused +1 review round or ~30 min lost | Caused R3+ or equivalent user rework / >1 h lost |
| **Detection gap** | 15% | Caught by primary (trinity) on first pass | Caught by primary on re-review after initial miss | Missed by primary entirely; caught by secondary (codex) or human |

### Action thresholds

| Composite | Action |
|-----------|--------|
| **≥ 7.5** | **Create GitHub issue** — include the drafted amendment in the issue body (per COR-1501 §Step 3: gh issue create). Present score breakdown to user before creating. |
| **5.0 – 7.4** | **Log only** — record in §Step 5 `### Scored Findings` with composite, dimension scores, and class. Re-evaluate on next iteration; Frequency score rises if the class recurs, potentially crossing the issue threshold. |
| **< 5.0** | **Discard** — noise, one-off, or already covered by an existing MEMORY entry or open issue. |

> **Threshold geometry note:** Reaching the Issue band (≥7.5) requires at least two dimensions to score strongly. Frequency=10 with all other dims at 5 yields only 6.75 (Log band) — intentional: a high-frequency but low-impact, vague, internally-caught finding warrants tracking, not an issue. Actionability is the second-strongest lever; Frequency=10 + Actionability=10 yields 6.5 at minimum (others at 0, Log band) and 8.25 with others at 5 (Issue band). Reaching the Issue band from Freq+Act=10 requires at least Impact=5 (composite = 7.5, exactly at threshold).

### Calibration examples

**Example 1 — First codex catch, trinity missed** (`--repo` gap, PR #131 R1):
Frequency=0, Actionability=8, Impact=5, Detection gap=10
→ 0×0.35 + 8×0.30 + 5×0.20 + 10×0.15 = **4.9 → Discard** (first occurrence; if this class recurs next PR, Frequency rises to 5 and composite crosses into Log band at 6.95)

**Example 2 — Same class recurs in the next PR**:
Frequency=5, Actionability=9, Impact=5, Detection gap=10
→ 1.75 + 2.70 + 1.00 + 1.50 = **6.95 → Log and re-evaluate**

**Example 3 — Third PR, same class** (pattern confirmed):
Frequency=10, Actionability=9, Impact=5, Detection gap=8
→ 3.50 + 2.70 + 1.00 + 1.20 = **8.40 → Create issue**

**Example 4 — Single late-convergence, high impact, no recurrence**:
Frequency=0, Actionability=9, Impact=10, Detection gap=5
→ 0 + 2.70 + 2.00 + 0.75 = **5.45 → Log**

### §Step 5 template addition

> Add `### Scored Findings` as the last subsection in the §Step 5 template, after Key Learnings:

```markdown
### Scored Findings
| Class | Frequency | Actionability | Impact | Detection gap | Composite | Action |
|-------|-----------|---------------|--------|----------------|-----------|--------|
| <class> | <0–10> | <0–10> | <0–10> | <0–10> | <n.n> | Log / Discard |
```

## Acceptance Criteria

- [ ] `COR-1200` has `## Scoring` section with signal taxonomy, scoring rubric, action thresholds, and ≥4 calibration examples
- [ ] Signal taxonomy has 6 rows including Other/Unclassified catch-all
- [ ] Scoring rubric: 4 dimensions named Frequency/Actionability/Impact/Detection gap, weights sum to 100%, anchor descriptions at 0/5/10
- [ ] Action thresholds: three bands; ≥7.5 band explicitly requires GitHub issue creation per COR-1501 §Step 3
- [ ] "Log only" band references §Step 5 `### Scored Findings` table
- [ ] ≥1 calibration example scores below the issue threshold
- [ ] COR-1200 §Steps 2, 3, and 4 each add one line referencing §Scoring
- [ ] COR-1200 §Step 5 template gains `### Scored Findings` subsection
- [ ] No new document created; `af status` document count unchanged
- [ ] `af validate --root /Users/frank/Projects/alfred` passes
- [ ] Trinity fast-review (glm + deepseek) both ≥ 9.0

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-10 | Initial version per issue #134 | Claude Code |
| 2026-05-10 | R1 fixes: geometry note arithmetic (B1); Log-only storage defined via §Step 5 Scored Findings (B2); Recurrence→Frequency rename (A2); Other catch-all row added (A1) | Claude Code |
| 2026-05-10 | R2 advisories: Detection gap score=5 anchor clarified; template Action column "Deferred"→"Discard"; template placeholder `<0/5/10>`→`<0–10>` | Claude Code |
