# REF-0001: Glossary

**Applies to:** All projects using the COR document system
**Last updated:** 2026-03-15
**Last reviewed:** 2026-03-15

---

## What Is It?

A reference document defining all terms, abbreviations, and conventions used in the document system. Read this first if you are new to the system.

---

## System Terms

| Term | Meaning | Origin |
|------|---------|--------|
| **ACID** | Area + Category + ID. The 4-digit document number (e.g., 1402). First digit = Area, second digit = Category, last two digits = Item. | Inspired by Johnny Decimal |
| **Johnny Decimal** | A system for organizing files using a 2-level numbering scheme (AC.ID). We use it without the dot. | https://johnnydecimal.com/ |
| **PDCA** | Plan-Do-Check-Act. The Deming cycle used to structure the meta-layer areas (10xx–14xx). | W. Edwards Deming, quality management |
| **COR** | Core. Prefix for universal meta-layer documents that apply to all projects. | Internal convention |
| **Project prefix** | 3-letter code identifying a project (e.g., ALF, BLA, CLR). Each project defines its own. Used for business-layer documents. | Internal convention |

## Document Type Codes

| Code | Full Name | Purpose |
|------|-----------|---------|
| **SOP** | Standard Operating Procedure | Step-by-step process for a single atomic operation |
| **ADR** | Architecture / Any Decision Record | Records a decision with context, options, rationale, and consequences |
| **CHG** | Change Request | Proposes a change with impact analysis, implementation plan, and approval |
| **INC** | Incident Record | Documents an incident: what happened, impact, resolution, and follow-up |
| **PLN** | Plan | A roadmap, backlog, or project plan |
| **PRP** | Proposal | A proposal for a new tool, feature, or system change before implementation |
| **REF** | Reference | Non-procedural reference material (glossary, index, lookup tables) |

## Area Structure (Meta Layer)

| Area | PDCA Phase | Description |
|------|------------|-------------|
| 00xx | — | System index and reference |
| 10xx | Do | Document creation and reading |
| 11xx | Plan | Decision and change planning |
| 12xx | Check | Review and retrospective |
| 13xx | Act | Update, deprecation, and index maintenance |
| 14xx | Constraint | Universal rules and principles |
| 15xx | Development | Universal development workflows |

## Area Structure (Business Layer)

| Area | Description |
|------|-------------|
| 20xx | Infrastructure |
| 21xx | (available) |
| 22xx | Planning |
| 23xx | Incident |
| 24xx+ | Extended per project |

## Other Terms

| Term | Meaning |
|------|---------|
| **Meta layer** | Universal documents (COR-) that apply to all projects |
| **Business layer** | Project-specific documents (ALF-, BLA-, CLR-) |
| **Atomic SOP** | An SOP that does exactly one thing (see COR-1400) |
| **Declare Active Process** | The practice of stating which SOP is being followed (see COR-1402) |

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-15 | Initial version | Claude Code |
