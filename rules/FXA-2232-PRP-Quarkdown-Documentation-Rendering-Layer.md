# PRP-2232: Quarkdown Documentation Rendering Layer

**Applies to:** FXA project
**Last updated:** 2026-05-03
**Last reviewed:** 2026-05-03
**Status:** Draft

---

## What Is It?

Evaluate Quarkdown (v2.0.0) as a supplementary documentation renderer alongside the existing MkDocs Material site. A thin preprocessor converts the project's Markdown SOP documents into Quarkdown-compatible syntax and produces HTML/PDF output — without modifying the canonical `.md` files that `af` depends on.

A working demo compiles SOP-2102 at `/tmp/qd-demo/` (converted `.qd` with directives; see §Demo Evidence below).

---

## Problem

The project already has a deployed MkDocs Material documentation site (`mkdocs.yml`, `gh-pages` branch, CI/CD via GitHub Actions). MkDocs Material provides Mermaid diagrams, admonition callouts, search, auto-generated navigation, and dark/light themes. However:

- **PDF export** requires a plugin (`mkdocs-with-pdf`) with known rendering gaps around Mermaid diagrams and wide tables
- **Typography defaults** are functional but plain — custom fonts require CSS overrides in `mkdocs.yml`
- **Collapsible sections** require inline HTML (`<details><summary>`) rather than native Markdown
- **Single-file PDF output** (all SOPs in one document) is not supported by MkDocs without custom tooling

Quarkdown offers these natively: `.font` directive for Google Fonts, `.collapse` for collapsible sections, and `--pdf` for PDF export. The proposal is to add it as an opt-in supplementary renderer — MkDocs remains the primary site.

---

## Scope

In scope:
- `quarkdown/` directory with `_setup.qd`, `_nav.qd`, `main.qd`
- Preprocessor script that copies `.md` → temp `.qd`, converting ` ```mermaid ` fenced blocks to `.mermaid` directives (no source files modified)
- `just docs-qd` command: preprocess + compile all PRJ docs to HTML
- `just docs-qd-pdf` command: same pipeline, PDF output
- Nav covers ~10 representative documents (SOPs, PRPs, CHGs) — not all 80+

Out of scope:
- Replacing or removing MkDocs Material
- Modifying canonical `.md` files in any way
- Modifying COR PKG layer documents
- GitHub Pages deployment (MkDocs already handles this)
- `af serve` integration
- Search functionality (not in Quarkdown v2.0.0; MkDocs provides it)

---

## Proposed Solution

### Architecture

```
.md files (canonical, unchanged)
    │
    ▼  preprocess.sh (temp copy + ```mermaid → .mermaid)
    │
    ▼  quarkdown c (compile .qd → HTML/PDF)
    │
    ▼  quarkdown-output/ (gitignored)
```

### Phase 1: Setup (1 session)

Create the Quarkdown project scaffold:

```
quarkdown/
  _setup.qd       # Shared config: fonts, doclang, docauthors, docdescription
  _nav.qd          # Curated nav (~10 representative documents)
  main.qd          # Entry point: .include {docs} + document listing
  preprocess.sh    # Converts ```mermaid → .mermaid + strips YAML --- (temp copies)
```

`_setup.qd`:
```quarkdown
.doclang {English}
.docauthors
  - Frank Xu
.docdescription {FXA Alfred Agent Runbook — SOP Documents}
.font {GoogleFonts:Zilla Slab} code:{GoogleFonts:JetBrains Mono}
```

`preprocess.sh`:
```bash
#!/bin/bash
# Copies .md files to temp dir, converting ```mermaid fenced blocks
# to .mermaid directives for Quarkdown compatibility.
# Source .md files are NEVER modified.
SRC="$1"   # source .md file
DST="$2"   # temp .qd file
sed '
  /^---$/d
  /^```mermaid$/,/^```$/ {
    /^```mermaid$/ { s/```mermaid/.mermaid/; n; }
    /^```$/d
  }
' "$SRC" > "$DST"
```

`main.qd`:
```quarkdown
.include {docs}

# FXA Alfred Agent Runbook

Browse SOPs, PRPs, and CHGs for the fx-alfred project.

## SOP Documents
- [SOP-2102: Release To PyPI](/tmp/qd-build/FXA-2102-SOP-Release-To-PyPI.qd)

## Proposals (PRP)
- [PRP-2232: Quarkdown Docs Layer](/tmp/qd-build/FXA-2232-PRP-Quarkdown-Documentation-Rendering-Layer.qd)

## Change Requests (CHG)
- [CHG-2103: Root Option And Spacing](/tmp/qd-build/FXA-2103-CHG-Root-Option-And-Spacing.qd)
```

### Phase 2: Verify rendering fidelity (1 session)

Test compilation of 3 document types (SOP, PRP, CHG) through the preprocessor + Quarkdown pipeline:

```bash
mkdir -p /tmp/qd-render-test
for f in rules/FXA-2102-SOP-Release-To-PyPI.md \
         rules/FXA-2232-PRP-Quarkdown-Documentation-Rendering-Layer.md \
         rules/FXA-2103-CHG-Root-Option-And-Spacing.md; do
  base=$(basename "$f" .md)
  quarkdown/preprocess.sh "$f" "/tmp/qd-render-test/$base.qd"
done
quarkdown c /tmp/qd-render-test/*.qd
```

Verify each of these constructs renders correctly:

| Construct | Present in | Expectation |
|-----------|-----------|-------------|
| ` ```mermaid ` fenced blocks | Multiple SOPs | Render as diagrams (via preprocessor) |
| Pipe tables (Change History) | Every document | Render as tables |
| `**Key:** value` metadata lines | Every document | Render as bold+text (no `---` interpreted as HR) |
| Fenced code blocks (`bash`, `python`) | Multiple SOPs | Syntax highlighted |
| `[!WARNING]` / `[!NOTE]` alerts | Some SOPs | Styled callouts |
| Numbered + bullet lists | Every document | Correct indentation |
| Inline code | Every document | Monospace, no escaping issues |

**Rejection threshold**: If any construct renders in a way that would require modifying canonical `.md` files to fix (excluding the preprocessor which is already scoped), the PRP closes as Rejected and `quarkdown/` directory is removed.

### Phase 3: Justfile integration (1 session)

```makefile
docs-qd:
    mkdir -p /tmp/qd-build
    for f in rules/FXA-*.md; do \
      quarkdown/preprocess.sh "$$f" "/tmp/qd-build/$$(basename $$f .md).qd"; \
    done
    quarkdown c quarkdown/main.qd

docs-qd-pdf:
    # same preprocess, then:
    quarkdown c quarkdown/main.qd --pdf
```

### Comparison: MkDocs Material vs Quarkdown

| Capability | MkDocs Material (existing) | Quarkdown (proposed) | Notes |
|------------|---------------------------|---------------------|-------|
| Mermaid diagrams | ` ```mermaid ` fenced blocks | `.mermaid` directive | Preprocessor converts (see Phase 1) |
| Alert callouts | `!!! note`, `!!! warning` | `[!NOTE]`, `[!WARNING]` | Both support GitHub syntax |
| Collapsible sections | `<details><summary>` HTML | `.collapse {title}` native | Quarkdown cleaner |
| Search | Built-in (lunr.js) | Not available | MkDocs wins |
| Navigation | Auto-generated from directory | Manual `_nav.qd` | MkDocs wins for 80+ docs |
| PDF export | Plugin (`mkdocs-with-pdf`) | Built-in (`--pdf`) | Quarkdown wins |
| Fonts | CSS overrides | `.font` directive | Quarkdown wins (zero config) |
| Live reload | `mkdocs serve` | `quarkdown c -p -w` | Equivalent |
| Themes | `material` theme | Color + layout themes | MkDocs more mature |
| CI/CD integration | Already wired | Manual `just` commands | MkDocs wins |
| Maturity | 8+ years, 20K+ stars | v2.0.0 (April 2026), 10K+ stars | MkDocs wins |

**Why not just improve MkDocs?** MkDocs covers most needs. The remaining gaps (PDF, typography, collapsible syntax) each have workarounds — but they add maintenance burden (plugins, CSS overrides, raw HTML). Quarkdown bundles these natively in a single binary. The question is whether that simplicity is worth the immaturity cost. Phase 2 answers this empirically.

---

## Demo Evidence

The demo at `/tmp/qd-demo/` compiles SOP-2102 (Release To PyPI) through Quarkdown with the following results:

| Feature | Syntax used | Result |
|---------|------------|--------|
| Mermaid flowchart | `.mermaid` directive | Rendered correctly with Yes/No branch labels |
| Mermaid sequence diagram | `.mermaid` directive | Rendered correctly with participant lifelines |
| `[!WARNING]` alert | GitHub-style blockquote | Styled warning callout |
| `.collapse` section | Quarkdown directive | Click-to-expand toggle |
| Pipe table (Change History) | Standard Markdown | Rendered correctly |
| Fenced code blocks (`bash`) | Standard Markdown | Syntax highlighted correctly |
| Google Fonts (Zilla Slab, JetBrains Mono) | `.font` directive | Loaded at view time |

**Key finding**: The demo used converted `.mermaid` directives, not fenced ` ```mermaid ` blocks. A test with raw fenced blocks confirmed Quarkdown renders them as `<pre><code>` (code block, not diagram). This is why the preprocessor is required in Phase 1.

---

## Acceptance Criteria

- [ ] `quarkdown/` directory with `_setup.qd`, `_nav.qd`, `main.qd`, `preprocess.sh` committed
- [ ] `just docs-qd` compiles without errors
- [ ] `just docs-qd-pdf` produces a single PDF
- [ ] Preprocessor correctly converts ` ```mermaid ` fenced blocks to `.mermaid` directives (verified: temp `.qd` files contain `.mermaid`, not fenced blocks)
- [ ] At least 1 document of each type (SOP, PRP, CHG) renders with correct structure through the pipeline
- [ ] Pipe tables (Change History) render as tables in all tested documents
- [ ] `quarkdown-output/` and `/tmp/qd-build/` are gitignored
- [ ] MkDocs site continues to build and deploy unchanged
- [ ] No canonical `.md` files modified

---

## Verification Plan

1. **Preprocessor test**: Run `preprocess.sh` on SOP-2102, verify output `.qd` has `.mermaid` not ` ```mermaid `
2. **Pipeline test**: `just docs-qd` → open HTML, verify nav sidebar with ~10 documents, verify Mermaid diagrams render
3. **PDF test**: `just docs-qd-pdf` → open PDF, verify: (a) tables not split mid-row across pages, (b) code blocks not broken across pages, (c) section headings not widowed (orphaned at page bottom), (d) Mermaid diagrams render at readable scale
4. **Fidelity check**: Side-by-side comparison of MkDocs HTML vs Quarkdown HTML for the same 3 documents — catalog differences
5. **MkDocs non-regression**: `mkdocs build` → `mkdocs serve` → confirm existing site unchanged
6. **Go/no-go**: If any document requires `.md` modification to render acceptably → Reject; if all pass → Approve implementation

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Quarkdown v2.0.0 API changes | Medium | Pin version in justfile; `brew install quarkdown-labs/quarkdown/quarkdown` pins to current bottle; CI installs same version |
| Preprocessor incomplete (misses edge cases) | Medium | Start with sed-based converter for ` ```mermaid ` only; add cases as discovered in Phase 2 |
| ` ```mermaid ` inside fenced code blocks (demonstrating syntax) | Low | Preprocessor only matches lines starting exactly with ` ```mermaid `; code blocks showing the syntax are indented or inside another fence |
| No search in Quarkdown output | Low | MkDocs remains primary searchable site; Quarkdown is supplementary (PDF + offline viewing) |
| `_nav.qd` maintenance for curated docs | Low | ~10 documents, updated only when new doc types or major SOPs are added |
| Single maintainer (iamgio) | Low | Open source (GPL-3.0), 10K+ stars; worst case: delete `quarkdown/`, revert to MkDocs-only |
| Quarkdown requires Node.js | Low | CI already has Node (MkDocs Mermaid plugin uses it); `brew install` handles dependency |
| `quarkdown-labs/quarkdown` tap availability | Low | Fallback: npm install `quarkdown` if brew tap unavailable |

---

## Rejection Cleanup

If Phase 2 verification fails (any document requires `.md` modification to render acceptably):
1. Delete `quarkdown/` directory
2. Remove `docs-qd` and `docs-qd-pdf` from justfile
3. Mark this PRP as Rejected with a summary of findings
4. No `.md` files were modified — zero rollback cost

---

## Open Questions

- Is PDF export + better typography sufficient to justify a second renderer alongside MkDocs?
- Should we invest the equivalent effort in improving MkDocs fonts/CSS instead?
- Is the preprocessor approach acceptable, or does it defeat the "simpler than MkDocs" thesis?

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-03 | Initial version | — |
| 2026-05-03 | R2: Added MkDocs comparison, AC, verification plan, risk mitigations (Codex 6.25 + DeepSeek FIX) | Claude Code |
| 2026-05-03 | R3: Added preprocessor (Mermaid gap confirmed), demo evidence table, rejection cleanup, nav scoped to ~10 docs, Phase 2 rejection threshold made precise | Claude Code |
| 2026-05-03 | R4: Added main.qd template, preprocessor now strips YAML --- delimiters, PDF criteria made objective (DeepSeek R3 FIX 8.0 → target 9.0) | Claude Code |
