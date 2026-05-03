# CTX-2123: Alfred Glossary

**Applies to:** FXA project
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Active
**Source:** Pilot CTX instance per FXA-2121 PRP (COR-1204-REF format); 90-day review horizon

---

## Alfred Project Glossary

| Term | Definition | Source | Updated |
|------|------------|--------|----------|
| **ACID** | A unique document identifier composed of a 3-letter prefix and a 4-digit number (e.g., `COR-1613`, `FXA-2121`) | COR-0002 | 2026-05-03 |
| **ADR** | Architecture Decision Record — a durable record of a past design decision with accepted trade-offs. Created via `af create adr` (COR-1100) or as free-form narrative in `docs/adr/`. | COR-1100 | 2026-05-03 |
| **CHG** | Change Request — a document proposing a change to an existing system, config, or architecture. | COR-1101 | 2026-05-03 |
| **Council Review** | The process defined by COR-1613: a dispatcher declares a Review Unit naming the decision mechanism, threshold, and reviewer set before any multi-reviewer evaluation begins. | COR-1613 | 2026-05-03 |
| **CTX** | A project glossary document following COR-1204-REF format: term/definition/source/updated table of domain-specific canonical terms. | COR-1204 | 2026-05-03 |
| **Decision Matrix** | A Council Review mechanism: multi-dimensional weighted scoring with a pass threshold. Used by default for PRP/CHG/code reviews. | COR-1613 | 2026-05-03 |
| **Diagnose Loop** | The 6-phase procedure defined by COR-1503: build feedback loop → reproduce → hypothesise → instrument → fix → regression-test. | COR-1503 | 2026-05-03 |
| **Dispatcher** | The entity responsible for declaring the Review Unit, convening reviewers, aggregating results, and recording the outcome. | COR-1613 | 2026-05-03 |
| **Evidence Artefact** | A concrete, machine-runnable or reviewer-verifiable record that a SOP phase has completed. Named gates in COR-1503 §Phase Enforcement Gates; specified in COR-1504-REF. | COR-1504 | 2026-05-03 |
| **Gate** | A named, required evidence artefact that marks a phase complete per COR-1503. Each phase has a minimum gate; without the gate, the phase has not closed. | COR-1503 | 2026-05-03 |
| **Mechanism** | A voting/decision rule applied to a Review Unit per COR-1613 §Mechanism Library. Examples: Decision Matrix, Simple Majority, Veto, Consensus. | COR-1613 | 2026-05-03 |
| **Operator** | The entity invoking a SOP — human or LLM. Always declared per COR-1402 before work begins. | COR-1402 | 2026-05-03 |
| **PKG / USR / PRJ** | The three Alfred document layers: PKG (bundled with `fx-alfred`, read-only), USR (`~/.alfred/`, user-level), PRJ (`./rules/`, project-level). | COR-1103 | 2026-05-03 |
| **PRP** | Proposal — a document capturing the design of a new feature, tool, or system change before implementation begins. | COR-1102 | 2026-05-03 |
| **Review Unit** | The frozen declaration per COR-1613 §Step 1: review_id + target + mechanism + rubric + threshold + reviewers + optional fields (quorum, abstention_rule, tie_break, deadline, etc.). | COR-1613 | 2026-05-03 |
| **SOP** | A Standard Operating Procedure document — a 5W1H workflow definition (What/Why/When/How). | COR-1000 | 2026-05-03 |
| **Universality Contract** | The constraint that PKG-layer SOPs must not name specific harnesses, providers, agents, or fixed reviewer counts. Each SOP carries a greppable token blocklist. | COR-1613 | 2026-05-03 |

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-03 | Initial pilot version — ~17 core Alfred terms per FXA-2121 PRP. 90-day review horizon per OQ3. | Frank Xu |
