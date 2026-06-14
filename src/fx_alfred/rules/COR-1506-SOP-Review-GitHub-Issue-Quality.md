# SOP-1506: Review GitHub Issue Quality

**Applies to:** All projects using the COR document system and iterwheel intake bots
**Last updated:** 2026-05-17
**Last reviewed:** 2026-05-17
**Status:** Active
**Related:** COR-1501 (Create GitHub Issue — creation companion), COR-1617 (§Phase 1 auto-pick gate), COR-1618 (consent auto-pick bypass), COR-1802 (scoring framework)
**Disposition:** inherit-only

---

## What Is It?

A structured content quality review for GitHub issues, applied after `iterwheel-blueprint[bot]` grants `blueprint-ready`. Scores five dimensions (0–10 each) against a weighted rubric and produces an action: Approve, Request revision, or Reject.

---

## Why

`iterwheel-blueprint[bot]` checks structural compliance — required H2 sections present, at least one `- [ ]` under Acceptance Criteria. It does not check:

- Whether AC items are independently verifiable by a fresh implementer
- Whether the task plan is executable cold with no clarifying questions
- Whether stated dependencies are complete and correctly ordered
- Whether problem evidence is concrete (PR/log/session) vs. vague impressions
- Whether Out of Scope prevents common creep for this issue's actual size

An issue that passes the bot can still be unimplementable. This happened with issues #133–#135 (2026-05-10), where a post-`blueprint-ready` review found 28 gaps the bot missed — resulting in blocked agents and rework.

---

## When to Use

- Before assigning an issue to an implementer (human or agent)
- During COR-1617 Phase 1 auto-pick eligibility check (rows 2–4 — autonomous triggers: loop-start (user-initiated), continuation, loop-driven)
- When an issue author requests a quality review before submitting for auto-pick

## When NOT to Use

- Issues without `blueprint-ready` label — run COR-1501 first; this SOP reviews content, not structure
- Draft or WIP issues not yet submitted for intake
- Issues authored by the reviewer — conflict of interest; request a different reviewer

---

## Definitions

**Fresh implementer** — an LLM coding agent with the repo HEAD, `CLAUDE.md`, and PKG-layer COR-* documents in context; no prior session memory of this issue; no access to the issue author for clarification. Every AC item must be independently checkable and every task plan step independently executable by this agent.

---

## Structural Pre-check

Before scoring, confirm:

1. Issue has `blueprint-ready` label (run `gh issue view <number> --repo <owner>/<repo> --json labels --jq '.labels[].name'` to verify).
2. If `blueprint-ready` is absent: stop. Run COR-1501 to address structural gaps first.
3. If `needs-revision` label is also present: the issue is in re-scoring window; check that the body was edited since the label was applied before proceeding.

---

## Scoring

Score each dimension 0–10 using the anchor table below. Composite = Σ(weight × score).

| Dimension | Weight | Score 0 | Score 5 | Score 10 |
|-----------|--------|---------|---------|----------|
| **AC verifiability** | 30% | ACs are vague or untestable ("works correctly", "feels right") | Most ACs checkable but ≥1 requires subjective judgment or re-reading the implementation | Every AC item in `## Acceptance Criteria` is a concrete binary check runnable by the fresh implementer independently — no implementation knowledge required |
| **Task plan executability** | 25% | Steps missing, out of order, or require implicit knowledge absent from the issue | Steps mostly ordered and concrete but ≥1 step is missing a tool invocation, uses wrong verb (e.g. "arm" vs "execute"), or has incorrect ordering | Steps in `## Reproduction Steps / Task Plan` are fully ordered, name exact commands/tools, and are self-contained — fresh implementer can execute without clarification |
| **Problem evidence** | 20% | No evidence cited; problem stated as vague impression ("it seemed wrong", "was observed") | Evidence partially concrete (e.g., "PR #131" without specifying what failed there) | Specific evidence: PR/issue numbers with failure description, session dates, exact error messages, or log excerpts |
| **Dependency completeness** | 15% | No "Depends on" stated despite visible upstream deps; downstream impact unmentioned | "Depends on" present but informal — buried in prose rather than Context §Depends on; downstream impact missing | All upstream deps in Context §Depends on with merge-order note; downstream impact explicitly stated (who to notify on merge) |
| **Scope precision** | 10% | No Out of Scope section; obvious creep risks unnamed | Out of Scope present but misses ≥1 obvious creep risk given this issue's actual size | Out of Scope calibrated to actual scope: small-atomic issues may have ≤1 item; large cross-cutting issues name 2–3 most likely creep risks. Penalizes both omission of obvious risks AND padding with fabricated boundaries |

Score dimensions independently — an issue can have an executable task plan and vague ACs simultaneously; each dimension scores only its declared section. The rubric structure (0/5/10 anchors, weighted composite) follows COR-1802 (Build Weighted Decision Matrix).

---

## Action Thresholds

| Composite | Action |
|-----------|--------|
| **≥ 8.0** | **Approve** — issue is eligible for COR-1617 autonomous auto-pick; post approval comment with score breakdown; remove `needs-revision` label if present |
| **6.0 – 7.9** | **Request revision** — post comment with score breakdown + specific asks per failing dimension; apply `needs-revision` label; issue is ineligible for autonomous auto-pick until re-scored ≥ 8.0 |
| **< 6.0** | **Reject** — fundamental gaps; post comment recommending full rewrite per COR-1501; apply `needs-revision` label; remove `blueprint-ready` label if present |

---

## Feedback Format

Post the score as an issue comment. Prohibit vague comments ("needs work") without a score — every feedback comment must include the full dimension table.

```
COR-1506 Quality Score: <composite> → <Approve | Request revision | Reject>

| Dimension         | Weight | Score | Note                    |
|-------------------|--------|-------|-------------------------|
| AC verifiability  | 30%    | X     | <one-line observation>  |
| Task plan exec.   | 25%    | X     | <one-line observation>  |
| Problem evidence  | 20%    | X     | <one-line observation>  |
| Dependency compl. | 15%    | X     | <one-line observation>  |
| Scope precision   | 10%    | X     | <one-line observation>  |

Composite: <score>

Findings:
- P1: <specific gap with section reference>
- P2: <specific gap>

Action: <approve with no changes | specific revision asks | rewrite from COR-1501 template>
```

Post via:

```bash
gh issue comment <number> --repo <owner>/<repo> --body-file /tmp/cor1506-score.md
```

---

## Calibration Examples

### Example A — Deep Reject (composite ≤ 4.0)

**Context:** A new feature request with no concrete AC, no task plan, and no evidence.

| Dimension | Score | Reasoning |
|-----------|-------|-----------|
| AC verifiability | 2 | Two ACs use "should work correctly" and "users can access it" — no binary check |
| Task plan executability | 1 | No task plan section; three bullet points without commands or ordering |
| Problem evidence | 3 | One vague reference ("previously discussed") with no PR or session link |
| Dependency completeness | 0 | No Depends on; three upstream deps visible in issue body prose |
| Scope precision | 4 | Out of Scope present but lists unrelated items; misses the most obvious creep risk |

**Composite:** 2×0.30 + 1×0.25 + 3×0.20 + 0×0.15 + 4×0.10 = 0.60 + 0.25 + 0.60 + 0.00 + 0.40 = **1.85 → Reject**

---

### Example B — Borderline Reject (composite 5.0–5.9)

**Context:** Issue #133 pre-fix state (2026-05-10 Opus 4.7 review): grep sweep missing, arm/execute verb confusion, no dependency declared.

| Dimension | Score | Reasoning |
|-----------|-------|-----------|
| AC verifiability | 5 | Two phase-list location ACs unspecified — reviewer must infer from context |
| Task plan executability | 4 | grep step missing; step 8 uses "arm" where COR-1617 expects "execute"; step ordering unclear |
| Problem evidence | 9 | Specific PRs cited with failure description |
| Dependency completeness | 2 | Clear dep on #134 exists but not declared anywhere in issue |
| Scope precision | 7 | Out of Scope present; misses one obvious creep risk |

**Composite:** 5×0.30 + 4×0.25 + 9×0.20 + 2×0.15 + 7×0.10 = 1.50 + 1.00 + 1.80 + 0.30 + 0.70 = **5.30 → Reject**

---

### Example C — Request Revision (composite 6.0–7.9)

**Context:** A well-intentioned issue with strong evidence but partially vague ACs and informal dependency listing.

| Dimension | Score | Reasoning |
|-----------|-------|-----------|
| AC verifiability | 6 | Most ACs binary, but two use "properly" and "as expected" without defining the expected value |
| Task plan executability | 8 | Steps are ordered and name commands; one step says "update config" without specifying which key |
| Problem evidence | 9 | Three PR references with specific failure lines |
| Dependency completeness | 5 | Dep mentioned in Context prose but not in formal §Depends on; downstream unmentioned |
| Scope precision | 7 | Out of Scope covers main creep risks; misses one boundary case |

**Composite:** 6×0.30 + 8×0.25 + 9×0.20 + 5×0.15 + 7×0.10 = 1.80 + 2.00 + 1.80 + 0.75 + 0.70 = **7.05 → Request revision**

**Revision asks:** (1) AC items 3 and 7 — replace "properly" / "as expected" with concrete observable value. (2) §Depends on — add explicit entry for the dep named in Context prose. (3) Task plan step 4 — specify config key being updated.

---

### Example D — Approve (composite ≥ 8.0)

**Context:** Issue #133 post-fix state (2026-05-10): grep step added, arm→execute fixed, dependency declared.

| Dimension | Score | Reasoning |
|-----------|-------|-----------|
| AC verifiability | 9 | All ACs independently checkable; one AC slightly relies on grep output format |
| Task plan executability | 9 | Steps fully ordered, exact commands named, verb corrected |
| Problem evidence | 9 | Specific PRs with failure description |
| Dependency completeness | 8 | §Depends on entry added; downstream impact noted for one of two consumers |
| Scope precision | 7 | Out of Scope covers main risks; minor calibration gap |

**Composite:** 9×0.30 + 9×0.25 + 9×0.20 + 8×0.15 + 7×0.10 = 2.70 + 2.25 + 1.80 + 1.20 + 0.70 = **8.65 → Approve**

---

## Integration with COR-1617

COR-1506 applies **only to autonomous auto-pick** (COR-1617 Phase 1, rows 2–4 — loop-start (user-initiated), continuation, and loop-driven triggers). It does **not** apply to user-directed picks (row 1), which bypass per COR-1618 §Normative Bypass Clause.

**Orchestrator behavior at Phase 1 auto-pick:**

1. Run Structural Pre-check (§Structural Pre-check above).
2. Score the issue per §Scoring.
3. If composite ≥ 8.0 → remove `needs-revision` label if present; proceed with auto-pick.
4. If composite 6.0–7.9 → post revision request comment; apply `needs-revision` label; skip this issue; advance to next eligible issue.
5. If composite < 6.0 → post rejection comment; apply `needs-revision` label; remove `blueprint-ready` label; skip this issue; advance to next eligible issue.

**User-directed picks:** orchestrator MAY surface the COR-1506 score as informational but MUST NOT block. If the user explicitly names an issue, proceed regardless of score.

**Re-scoring:** Once the issue author edits the body (which re-triggers `iterwheel-blueprint[bot]`) and `blueprint-ready` re-applies, the issue is eligible for COR-1506 re-review — even while `needs-revision` is still present (§Structural Pre-check step 3 explicitly permits scoring in this state). The orchestrator treats a re-labeled `blueprint-ready` issue as a fresh candidate and runs steps 1–5 above; if the re-score is ≥ 8.0, step 3 removes `needs-revision` as part of the approval action.

---

## Guard Rails

- Do not apply COR-1506 to issues still in draft/WIP state — wait for `blueprint-ready`.
- Do not self-review issues you authored — the conflict of interest invalidates the score.
- Do not post a score without the full dimension table — vague feedback is prohibited.
- `needs-revision` label must accompany every Reject or Request revision action; its absence is a guard-rail violation.
- Scores are point-in-time; a post-fix re-score is not retroactively applied to the original score.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-10 | Initial version — 5-dimension scoring rubric, 4 calibration examples (all 3 bands), COR-1617 Phase 1 integration gate, feedback format, re-scoring mechanism. Issue #136. | Claude Sonnet 4.6 |
| 2026-05-11 | PR #154 codex-bot threads: (1) Approve action removes `needs-revision` label if present — §Action Thresholds + §Integration step 3; (2) COR-1617 Phase 1 wired to apply COR-1506 quality gate after consent pass; (3) Re-scoring paragraph rewritten — `needs-revision` removal is now an outcome of ≥8.0 re-score (step 3), not a precondition for re-review eligibility. | Claude Sonnet 4.6 |
| 2026-05-17 | issue #166 R4 (PR #180 codex bot P2): COR-1617 §Phase 1 gained a new "Loop-start (user-initiated)" trigger row (row 2 of 4 autonomous rows). COR-1506's §When to Use and §Integration with COR-1617 still scoped to "rows 2–3 (continuation + loop-driven)" — mechanical follower would skip the ≥8.0 issue-quality gate for the first loop-start pick. Fix: row references updated to "rows 2–4" + trigger list extended to include loop-start. | Claude Opus 4.7 |
