# CHG-2314: USR Sub-Project Layer Via Projects-JSON Mapping

**Applies to:** FXA project
**Last updated:** 2026-06-28
**Last reviewed:** 2026-06-28
**Status:** Approved
**Date:** 2026-06-27
**Requested by:** Frank Xu
**Priority:** Medium (risk: High — touches the shared scan core)
**Change Type:** Normal
**Issue:** frankyxhl/alfred#243

---

## What

Teach the scan core to treat a subdirectory of the USR home (`~/.alfred/<NAME>/`) as a per-project PRJ-equivalent layer, selected by a new `~/.alfred/projects.json` mapping that points an external project root path at that subdirectory.

Concretely:

1. **New config** `~/.alfred/projects.json` — maps an absolute external project root to a USR subdirectory name:
   ```json
   { "projects": { "/Users/frank/Projects/marvin/prefrontal-cortex": "NRV" } }
   ```
   Loader contract: no module-level cache (re-read each call, so tests/long-lived processes never see stale data). The two entry points (`context.discover_root` and `scanner.scan_documents`) each load it once per CLI invocation; collapsing the two small reads into one invocation-scoped read was judged unnecessary at code review (harmless; not worth threading the mapping through the `ctx` call-chain). Missing file, malformed JSON, wrong shape, or unknown top-level keys ⇒ empty mapping (graceful, **and a one-line warning to stderr on a present-but-unparseable file** — not silent). Keys MUST be absolute paths; relative keys are ignored with a warning. Values MUST be a single subdirectory leaf name under `~/.alfred/` — a value containing a path separator, or equal to `.`, `..`, or empty, is rejected and ignored with a warning (guards against `~/.alfred/.` resolving to the USR home itself). Many-to-one is allowed (several roots may map to the same `<NAME>`).

2. **PRJ-layer redirect (mapping wins)** — when the active root matches a mapping key, `scan_documents` loads `~/.alfred/<NAME>/` as the PRJ layer (`source="prj"`). The mapping **always** fires for a registered root. If that root *also* has its own populated `<root>/rules/`, the local `rules/` is **shadowed with a warning** — the explicit `projects.json` opt-in wins. **Why mapping-wins (not real-`rules/`-wins):** §What-4's USR exclusion is necessarily *global* (a registered subproject must be hidden from the flat USR layer in **every** context, or the original "2 active routing docs in USR" warning re-fires from any unmapped directory and the isolation property breaks). If the redirect were instead gated on the absence of a local `rules/` (the R2 design), a mapped root that also had `rules/` would have its subproject docs excluded from USR **and** not loaded as PRJ → they vanish from every scan (the "orphan-docs" interaction MiniMax flagged in R2). Making the redirect unconditional for registered roots keeps it consistent with the global exclusion and makes the orphan state unreachable. The hybrid config (a mapped repo that also hosts `rules/`) is near-pathological — you register a repo in `projects.json` precisely *because* it cannot host `rules/` — so shadow-with-warning is the right contract, not a silent drop.

3. **Redirected PRJ scan is recursive** — the redirected `~/.alfred/<NAME>/` is scanned **recursively** (same depth semantics the USR scan gave these docs before this change), with the same `logs/` skip. This prevents the silent loss of docs nested under `~/.alfred/<NAME>/<subdir>/` that a non-recursive PRJ scan would cause (resolves R1 blocking #1). The ordinary `<root>/rules/` PRJ scan stays non-recursive (unchanged).

4. **USR-scan exclusion** — the recursive USR scan excludes **every** registered subproject directory (top-level leaf names from the mapping), so those docs never appear in the flat USR layer. This is what prevents the duplicate `prefix+ACID` `LayerValidationError` (the same file would otherwise be scanned as both `usr` and `prj`).

5. **Path normalization** — both `projects.json` keys and the candidate path (cwd, its ancestors, or explicit `--root`) are compared **after `Path(...).resolve()` on both sides**, so symlinks (e.g. macOS `/var`→`/private/var`), trailing slashes, and `..` segments match correctly. `get_root`/`discover_root` currently compare an unresolved `Path.cwd()`; this change resolves it before matching. Matching is exact-resolved-path equality (the operator authors absolute paths).

6. **cwd auto-resolution (new code path)** — today a third-party repo with no `rules/` is NOT recognized as an Alfred root (`discover_root` only accepts dirs whose `rules/` holds non-COR docs). This change adds mapping-aware recognition: if the resolved cwd or an ancestor is a `projects.json` key, that directory becomes the active root and its subproject PRJ layer loads — no `--root` needed. When several ancestors are mapping keys, the **nearest mapped ancestor wins** (the deepest matching directory, consistent with how `discover_root` already prefers the nearest `rules/`). If both a `rules/`-bearing ancestor and a mapped ancestor match at different depths, the **deepest match wins** (one uniform nearest-wins rule across both root kinds). Explicit `--root` still wins over cwd. This is a genuinely new branch in `context.py`, called out here so reviewers can target it.

7. **Missing target dir** — if a mapping value points to a `~/.alfred/<NAME>/` that does not exist, the PRJ layer is empty and a warning is emitted; no crash, no fallback to `<root>/rules/` resurrection.

8. **`Document.directory` field** — for redirected PRJ docs this leaf label becomes `<NAME>` (e.g. `"NRV"`) instead of the USR scan's `"alfred"`. This field is an **opaque display/label value**; file resolution uses `base_path` (`Document.resolve_resource`), not `directory`, so no behavior depends on the change. A test pins the field value so the shift is intentional and visible, not silent.

9. **Backward compatible** — absent/malformed `projects.json`, or an unregistered subdir, ⇒ behavior is exactly as today (recursive USR, PRJ = `<root>/rules/`).


## Why

`af guide` currently emits `Warning: 2 active routing docs in USR layer, using lowest ACID`, and the PRJ section shows `(no active routing document found)`.

Root cause: docs under `~/.alfred/NRV/` are flattened into USR by the recursive USR scan (`scanner._scan_path_dir(..., recursive=True)`). The `prefrontal-cortex` repo is **third-party** — we cannot add a `rules/` directory to someone else's repo — so the only place for its PRJ-layer docs is a USR subdir, which then collides with the genuine USR routing doc (ALF-2207).

After this change: ALF-2207 stays the sole USR routing doc, NRV-2500 becomes the PRJ routing doc → warning gone, PRJ no longer empty. Because the fix lives in the shared `scan_documents`, every command that routes through it (`list`, `read`, `validate`, `status`, `search`, `where`, `export`, `plan`, `guide`, …) inherits the corrected classification automatically.


## Design / Rejected Alternatives

**Chosen:** projects.json path→subdir mapping + unconditional (mapping-wins) recursive PRJ redirect for registered roots + global USR exclusion of registered subdirs + resolve-both-sides path matching.

| # | Alternative | Why rejected |
|---|-------------|--------------|
| A | `--project NRV` flag or `ALFRED_PROJECT` env var to select the subproject | Requires the operator to remember and pass it on every call. cwd auto-match against `projects.json` is zero-friction. A flag/env can be layered on later without breaking the mapping (kept Out of Scope). |
| B | Add a new `Source` label (e.g. `"sub"`) + extend `SOURCE_ORDER` to a 4-layer model | Invasive: every consumer (`guide`, `list`, `status`, sort keys, `SOURCE_LABELS`) would need a 4th layer. Redirecting the existing PRJ layer reuses the proven 3-layer model and keeps the diff small. |
| C | Make the USR scan non-recursive globally | Breaks backward compatibility for any USR layout that relies on recursive discovery. We only exclude **registered** subprojects; unregistered subdirs keep recursing. |
| D | Move NRV docs into a real `rules/` inside the `prefrontal-cortex` repo | The repo is third-party — polluting it with a `rules/` dir is the exact constraint that created this problem. |
| E | Real `<root>/rules/` wins over the mapping (precedence-gated redirect — the R2 design) | Combined with the necessarily-global USR exclusion (§What-4), a mapped root that also has `rules/` would have its subproject docs excluded from USR *and* not loaded as PRJ → silent vanish (the "orphan-docs" interaction, MiniMax R2). Also needs a fuzzy "populated `rules/`" threshold. Chose mapping-wins + shadow-warning instead (§What-2) — orphan state unreachable, no threshold needed. AC reworded to scope "no behavior change" to **unregistered** repos. |
| F | Make USR exclusion conditional (exclude only when the redirect actually fires for the active root) | Fails the core fix: from an unmapped context the redirect never fires, so the subproject would reappear in USR and the "2 active routing docs" warning returns globally + isolation breaks. Global exclusion is required, which forces mapping-wins (Alt E). |

**Isolation semantics (accepted trade-off):** once `NRV` is registered, its docs are visible (as PRJ) **only** in the mapped repo context; from an unmapped directory `af list`/`af read` will not surface them. This mirrors how genuine `<root>/rules/` PRJ docs are already scoped to their own repo, and is what prevents the duplicate-ID collision. A future cross-subproject view (`af list --all-subprojects`) is Out of Scope.


## Impact Analysis

- **Systems affected:**
  - `src/fx_alfred/core/scanner.py` — `scan_documents` (unconditional mapping-wins recursive PRJ redirect + global USR exclusion). Reuses existing `_scan_path_dir(..., recursive=True)` and its `logs/` skip for the redirected layer.
  - `src/fx_alfred/context.py` — `discover_root`/`get_root` gain resolve-both-sides matching + mapping-aware root recognition (new branch, §What-6).
  - **New** `src/fx_alfred/core/projects.py` — load/parse `~/.alfred/projects.json` once with graceful fallback; expose a shared `resolve_subproject(root: Path) -> str | None` consumed by both the scanner exclusion and `context` root discovery (single source of truth, the concrete REFACTOR target).
  - `tests/` — new coverage in `test_scanner.py`, `test_guide_cmd.py`, `test_list_cmd.py`, and a new `test_projects.py` for the loader.
  - Docs — `README.md` / `CLAUDE.md` three-layer-model section gains a `projects.json` note (pairs with the existing `af create --subdir`).
  - **No change** to command logic — every scan-routing command (`guide`, `list`, `read`, `validate`, `status`, `search`, `where`, `export`, `plan`, **`index`**) inherits via `scan_documents`/`scan_or_fail`; confirmed `index_cmd.py` and `validate_cmd.py` route through it (no private scan path).
- **`af create --subdir` interaction:** `af create --subdir <NAME>` always **writes** to `~/.alfred/<NAME>/` (unchanged — create targets the USR subdir, never a shadowed local `rules/`). Only the *scan-time* classification differs afterwards: an UNREGISTERED subdir's docs stay USR-visible (recursive USR), exactly as today; a REGISTERED subdir's docs become PRJ-in-context and USR-hidden. Documented so the write-target vs scan-classification asymmetry is intentional.
- **`Document.directory` consumers:** audited — `resolve_resource` uses `base_path`; `directory` is informational. No behavioral consumer; pinned by a test on both the dataclass attr and `list --json` output (§What-8).
- **Observability:** each of these cases emits a `click.echo`-to-stderr warning where user-facing (guide), consistent with the existing "2 active routing docs" warning style: ignored mapping, **shadowed local `rules/`** (registered root that also hosts `rules/`), missing target dir, relative key, and rejected value (`.`/`..`/separator/empty). Warnings are de-duplicated per `(root, NAME)` per invocation to avoid noise on high-frequency commands. A verbose per-scan debug log is **deferred** (advisory) to avoid introducing a logging dependency this CHG doesn't otherwise need.
- **Data / config migration:** after release + reinstall, add `prefrontal-cortex → NRV` to `~/.alfred/projects.json` (user-layer config, not in this repo).
- **Risk:** High — `scan_documents` is shared by all scan-routing commands. Mitigated by: additive config (absent file ⇒ old behavior), mapping-wins redirect (orphan-docs state unreachable) + global USR exclusion + shadow-warning for a registered root's own `rules/`, explicit duplicate-prevention + nested-doc + normalization tests, and COR-1602 parallel review (GLM + DeepSeek + MiniMax).
- **Rollback plan:** revert the implementation commit; `~/.alfred/projects.json` is additive and inert without the code, so no data migration to undo. Removing/renaming the file also restores prior behavior. Downgrade safety: an older `af` simply ignores `projects.json` (it never reads it), and the loader ignores unknown keys so a newer config never breaks an older reader of the same file. Post-rollback symptom (documented for ops): registered subproject docs reappear in USR and the original "2 active routing docs" warning returns — that is the expected signal the rollback took effect, not a new fault.


## Implementation Plan

TDD per COR-1500; implementation dispatched via `/trinity glm`, reviewed via GLM + DeepSeek + MiniMax (FXA-2100). Test fixtures: `monkeypatch` `Path.home` to a `tmp_path` sandbox; build `~/.alfred/`, subproject dirs, and an external repo root under it; `CliRunner` for `guide`/`list` assertions.

1. **RED** — add failing tests:
   - **loader** (`test_projects.py`): valid map parses; missing file ⇒ `{}`; malformed JSON ⇒ `{}` **+ warning**; wrong shape / unknown keys ⇒ `{}`; relative key ignored + warned; value with path separator / `.` / `..` / empty ignored + warned; parsed once per invocation.
   - **scanner — happy path:** mapped root loads `~/.alfred/<NAME>/` as `source=prj`; registered subdir excluded from USR; no `LayerValidationError`.
   - **scanner — recursion:** doc at `~/.alfred/<NAME>/<subdir>/X.md` IS found under PRJ (nested-doc regression guard, R1 #1).
   - **scanner — mapping-wins / orphan-unreachable:** mapped root that ALSO has populated `<root>/rules/` ⇒ subproject docs load with `source=prj` (assert specific doc IDs), `_validate_layers` passes (no `LayerValidationError`), the shadow warning is emitted, and **no local `rules/` doc appears in PRJ** (`assert not any(d.base_path == local_rules_dir for d in prj_docs)`) — shadow enforced independently of any coincidental collision (MiniMax R2/R3 orphan guard).
   - **scanner — normalization:** key vs candidate that differ only by a symlink (built with a `tmp_path` symlink fixture, not the real `/var`→`/private/var`) / trailing slash / `..` still match after resolve (R1 #3).
   - **scanner — missing dir:** mapping value with no such `~/.alfred/<NAME>/` ⇒ empty PRJ + warning, no crash.
   - **scanner — backward compat:** absent/malformed json ⇒ current behavior; UNREGISTERED subdir still recurses into USR (locks `test_scan_usr_recursive`).
   - **scanner — directory field:** redirected PRJ doc has `directory == "<NAME>"` on the dataclass AND in `af list --json` output (pins §What-8).
   - **context:** resolved cwd under a mapped root resolves without `--root`; explicit `--root` overrides; nested mapped ancestors ⇒ nearest (deepest) wins; many-to-one mapping resolves each key.
   - **guide:** mapped root ⇒ no "2 active routing docs" warning, PRJ shows the subproject routing doc.
   - **list (`--json`):** subproject docs labelled PRJ in mapped context (assert via `CliRunner` `--json`); `--source usr` excludes them; unmapped context hides them.
   - **index / validate:** run in mapped context ⇒ they see the subproject docs as PRJ (locks the "inherits via shared `scan_documents`" claim in CI).
2. **GREEN** — implement `core/projects.py` (loader + `resolve_subproject`); wire the unconditional mapping-wins recursive PRJ redirect + global USR exclusion into `scan_documents`; wire resolve-both-sides + mapping-aware recognition into `context`.
3. **REFACTOR** — route both the scanner USR-exclusion and `context` root discovery through the single `resolve_subproject(root)` / registered-subdir-set helper in `core/projects.py`; confirm `projects.json` is read once per invocation. **Implementation note:** the shadow-warning dedup state MUST be per-call (e.g. a set threaded through the scan), NOT a module-level global — a module-level set leaks across invocations and would silently suppress warnings on later calls in long-lived processes/tests.
4. **Verify** — full `pytest` + `ruff` clean; manual `af guide --root <prefrontal-cortex>` against a temp `projects.json` shows the fixed output.
5. **Release** — FXA-2102 (PyPI) → `pipx` reinstall → register NRV in `~/.alfred/projects.json` → confirm warning gone in the user's live `af`.


## Acceptance Criteria

- [ ] `~/.alfred/projects.json` parsed once in core; missing/malformed/wrong-shape/unknown-keys ⇒ empty mapping (no crash; malformed-but-present ⇒ warning); relative keys and values containing a separator / `.` / `..` / empty ignored + warned
- [ ] Mapped active root ⇒ `~/.alfred/<NAME>/` docs load with `source=prj` (mapping always fires for a registered root)
- [ ] Redirected PRJ layer is scanned recursively — docs nested under `~/.alfred/<NAME>/<subdir>/` are found (no silent loss)
- [ ] Mapped root that ALSO has populated `<root>/rules/` ⇒ mapping wins (subproject loads as PRJ), local `rules/` shadowed + warned, subproject docs do NOT vanish (orphan-unreachable)
- [ ] Path matching resolves both sides — symlinked / trailing-slash / `..` candidates match their `projects.json` key
- [ ] Mapping value pointing to a non-existent `~/.alfred/<NAME>/` ⇒ empty PRJ + warning, no crash
- [ ] Recursive USR scan excludes every registered subproject dir (no duplicate `prefix+ACID` error)
- [ ] Redirected PRJ doc exposes `Document.directory == "<NAME>"` (pinned, intentional)
- [ ] `af guide --root <mapped repo>` emits no USR-layer warning and shows the subproject routing doc under PRJ
- [ ] `af list` labels subproject docs PRJ in mapped context; `--source usr` excludes them; unmapped context hides them
- [ ] cwd/ancestor under a mapped root resolves without `--root`; explicit `--root` overrides; nearest (deepest) mapped/`rules/` ancestor wins
- [ ] `af index` / `af validate` run in a mapped context see the subproject docs as PRJ (shared-scan inheritance locked in CI)
- [ ] Unregistered `~/.alfred/` subdirs retain recursive-USR behavior
- [ ] No behavior change for **unregistered** repos using a real `<root>/rules/` PRJ layer
- [ ] `pytest` + `ruff` clean; new tests cover all of the above

---

## Change History

| Date       | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | By          |
|------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|
| 2026-06-27 | Initial version (issue #243; CHG over PRP — design pre-settled, carried in Design/Rejected Alternatives)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Claude Code |
| 2026-06-27 | R1 fixes (GLM 7.6 / DeepSeek 7.7 / MiniMax 7.05, all FIX): recursive redirected-PRJ scan (nested-doc loss); real-`rules/`-wins precedence (AC contradiction); resolve-both-sides path normalization; missing-dir + relative-key + unknown-key handling; `Document.directory` field pinned; new-context-path called out; concrete REFACTOR target (`resolve_subproject`); fixture mechanism + expanded RED list; reviewer roster corrected to GLM/DeepSeek/MiniMax                                                                                                                                           | Claude Code |
| 2026-06-28 | R2 fixes (GLM 9.5 PASS / DeepSeek 9.0 PASS / MiniMax 8.5 FIX): flipped redirect to **mapping-wins** to make the orphan-docs interaction (MiniMax — precedence-gate vs global USR exclusion) unreachable; dropped the "populated `rules/`" threshold; added Alt E/F design record; value validation rejects `.`/`..`/separator/empty; malformed-JSON warns; `af index`/`validate` confirmed on shared scan; `af create --subdir` interaction + rollback post-mortem hint documented; `list --json` directory pin; symlink test uses `tmp_path` fixture; AC "no behavior change" scoped to unregistered repos | Claude Code |
| 2026-06-28 | R3 doc-consistency fixes (GLM 9.5 PASS / DeepSeek 8.8 FIX / MiniMax 8.75 FIX — all confirmed the mapping-wins flip sound; sole deduction was stale text): corrected the two stale "precedence gate (real `rules/` wins)" lines in §Impact (Systems-affected + Risk) and the GREEN step to mapping-wins; added "nearest mapped ancestor wins" (§What-6); added shadowed-`rules/` to the Observability warning enumeration + per-`(root,NAME)` dedup; clarified `af create --subdir` write target; strengthened orphan-unreachable RED assertions; added `index`/`validate` inheritance RED test              | Claude Code |
| 2026-06-28 | APPROVED via COR-1602 — R4 unanimous PASS (GLM 9.5 / DeepSeek 9.85 / MiniMax 9.5, all >=9.0). Absorbed final non-blocking advisories: deepest-ancestor tiebreaker, per-call shadow-warning dedup, AC bullets for nearest-ancestor + index/validate inheritance. Status -> Approved; proceed to implementation per FXA-2100.                                                                                                                                                                                                                                                                                 | Claude Code |
| 2026-06-28 | Code review COR-1610 — all PASS (GLM 9.6 / DeepSeek 9.55 / MiniMax 9.4, zero blocking). Folded convergent advisories: COR- filter parity in shadow-warning check (scanner.py), dedicated index/validate mapped-context tests, USR directory-field assertion. Double-read of projects.json accepted as harmless (no cache added). Tests 1256 passed, ruff clean.                                                                                                                                                                                                                                             | Claude Code |
