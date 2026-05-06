# SOP-1207: Zoom Out

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-07
**Last reviewed:** 2026-05-07
**Status:** Active
**Related:** COR-1204-REF (CTX Format — glossary supplies the map's vocabulary), COR-1203 (Pre-Task Alignment — zoom-out is the disambiguation move when alignment surfaces unfamiliar code), COR-1402 (Declare Active Process — zoom-out is invoked by declaration)
**Inspired by:** mattpocock/skills `engineering/zoom-out` (Round 5 of skills-absorption initiative; prior rounds shipped COR-1613, COR-1503, COR-1203, COR-1204-REF, and the `/caveman` command)

---

## What Is It?

A 30-second discipline for navigating unfamiliar code. When the agent does not know the area well, **before diving into the specific function or file**, the agent requests a higher-level map — modules, callers, and key data structures — using the project's CTX glossary as the vocabulary anchor.

The output is a domain-vocabulary-anchored map, not a code summary. *"User session token store, called by auth middleware and rotation worker"* beats *"JWT helpers in auth.py"*.

The original `mattpocock/skills` skill is a single-line directive: *"Go up a layer of abstraction. Give me a map of all the relevant modules and callers, using the project's domain glossary vocabulary."* This SOP keeps that core and adds two missing pieces: explicit **altitude** selection (module / data-flow / decision) and a **stop condition** so zoom-out does not silently expand into a full-codebase tour.

## Why

Diving into unfamiliar code without context produces three failure modes:

1. **Local optimization at global expense.** The agent fixes a symptom that wasn't actually the cause because it could not see the upstream constraint. The same defect-pattern cited in COR-1503 (Diagnose Loop) — an unmapped territory is a hypothesis-free territory.
2. **Glossary drift.** The agent invents new names ("the token thing") instead of using the project's canonical terms (e.g. `SessionToken`). Drift accumulates session over session and erodes COR-1204's CTX value.
3. **Surface-feature blindness.** The agent works only on what's visible in the prompt; cross-cutting concerns (callers, data flow, runtime triggers) stay invisible until they fail in production.

Zoom-out costs ~30 seconds of model time. Fixing the consequences of skipping it does not.

## When to Use

- The agent has not touched this module / area in the current session
- The operator hands the agent a function or file in isolation without surrounding context
- The proposed change spans ≥ 2 files
- The agent's first instinct is *"I'll need to look at how this is called"* — that itself is the zoom-out signal
- Sibling to COR-1203 (Pre-Task Alignment): if alignment surfaces an area the agent is unfamiliar with, zoom-out is the disambiguation move

## When NOT to Use

- The agent already has a complete mental model from recent session work in the same area
- Trivial changes confined to one function with no callers
- Pure additions to greenfield code with no existing context to map
- Time-pressed hotfix with a known-good local fix and a low blast radius
- Pure documentation edits where no code reasoning is required

## Steps

1. **State the unfamiliarity explicitly.** Open with: *"I don't know this area well. Zooming out before diving in."* The declaration is for the operator's record per COR-1402.

2. **Load the project glossary.** If a CTX document exists per COR-1204-REF, read it before mapping. The glossary supplies the vocabulary the map will use. If no CTX exists, note *"no glossary loaded — using inferred vocabulary"* in the map header.

3. **Pick an altitude. Pick exactly one.** Three altitudes:
   - **Module map** (default for code questions) — relevant modules, their responsibility, and which other modules call them
   - **Data flow map** — how a piece of state enters, mutates, and exits the system
   - **Decision map** — what conditions trigger which code path (state-machine view)

   The right altitude depends on the underlying question. *"Is this safe to change?"* → module map. *"Why does this state look wrong?"* → data flow. *"When does this branch fire?"* → decision map. State the picked altitude in one line so the operator can correct if wrong.

4. **Express the map in glossary terms.** Use the CTX vocabulary (or note divergence). Format: bullet list, one node per line, with explicit relationships. Example:

   ```
   Altitude: module map
   - SessionTokenStore — owner of session token lifecycle
     - called by AuthMiddleware (validates on each request)
     - called by RotationWorker (renews near expiry)
     - depends on RedisCache for storage
   ```

5. **Stop when the territory is mapped, not when it is exhausted.** Zoom-out is complete when the agent can answer: *"given the proposed change, what else might break?"* Not when every module is listed. A 6-bullet map that answers the question beats a 30-bullet map that includes everything.

6. **Record glossary divergences.** If during mapping the code uses a term the CTX glossary does not have, surface it: *"Term `sessionRing` appears in code but is not in CTX — should it be added?"*. This naturally feeds COR-1203's glossary-update pattern; over sessions the CTX grows from real-code observations rather than theoretical declarations.

---

## Change History

| Date | Change | By |
|---|---|---|
| 2026-05-07 | Initial SOP, Round 5 of the skills-absorption initiative. Absorbed from mattpocock/skills `engineering/zoom-out`. Additions over the source skill: explicit altitude selection (module / data-flow / decision), CTX-anchored vocabulary requirement (binds to COR-1204), and an explicit stop condition. | Claude Code (Opus 4.7) |
