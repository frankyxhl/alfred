# SOP-1612: Respond To PR Review Comments

**Applies to:** All projects using the COR document system
**Last updated:** 2026-05-02
**Last reviewed:** 2026-05-02
**Status:** Draft

---

## What Is It?

The standard process for responding to review comments on a Pull Request. Covers comments from any source — human reviewers, automated tools (Codex bot, Copilot), trinity 4-reviewer panel results, or any other source. This SOP is a universal overlay that works with any workflow (COR-1600–1605).

### Reviewer Detector Classes (orthogonal, not interchangeable)

Different reviewer types catch different failure modes. Always treat them as a **set of orthogonal detectors**, not substitutes:

| Detector | Strengths (catches reliably) | Blind spots |
|---|---|---|
| **Codex bot inline** (`chatgpt-codex-connector[bot]`, auto-runs ~30s after each commit push) | Cross-reference inconsistencies, stale references, "shipped" / placeholder elision, shell-example execution failures (`set -e` brittleness, unmatched globs, invalid jq, syntax errors), cross-file contract drift | Architectural judgment, design tradeoffs, calibration scoring, out-of-scope debates |
| **Trinity 4-reviewer panel** (Codex / Gemini / GLM / DeepSeek via `/trinity`) | Architecture, risk awareness, scope precision, calibration scoring (COR-1608), competing-tradeoff judgments | Cross-reference drift after R+1 (panel internalizes a model and stops re-checking), shell-execution last-mile bugs, "review pack framed-out" issues |
| **Human reviewer** | Domain intent, "is this what the user actually wants", historical context, cross-PR strategic decisions | Patience for diff-mode rescanning, real-shell mental simulation |
| **Author self-review** | Knows intent + recent context | Author-self bias ("I just wrote this, it's fine"), inability to diff-mode read own work |

**Rule of thumb:**
- Doc-only PR (≤ 5 file changes, no architectural decision) → Codex bot inline alone is **likely sufficient** if iterated through every fix round. Trinity panel optional.
- PRP / architectural / cross-vendor protocol PR → Trinity panel **required**; bot still runs in parallel and catches what panel misses.
- Implementation PR with code → both. Bot's execution simulator extends to test code.

---

## Why

Without a standard process, review comments get fixed without replies, missed entirely, or self-resolved without reviewer confirmation. This leads to unverified fixes and broken review trust.

---

## When to Use

- A PR has received review comments (inline, review summary, or bot suggestions)
- After pushing code to a PR that has pending review threads
- Any workflow that involves a PR merge step

---

## When NOT to Use

- Review scoring during COR-1602 parallel review (that's a separate scoring flow)
- Draft PRs where comments are self-notes
- Comments on closed/merged PRs (address in a follow-up PR if needed)

---

## Steps

### 1. Fetch all PR review feedback

Fetch inline review comments, review summary comments, and top-level PR conversation comments:

```bash
# Inline review comments on changed lines
gh api repos/{owner}/{repo}/pulls/{number}/comments --paginate --jq '.[] | {type: "inline", id, path, line, body}'

# Review summary comments (review bodies). Keep CHANGES_REQUESTED reviews even if body is empty.
gh api repos/{owner}/{repo}/pulls/{number}/reviews --paginate --jq '.[] | select(.state == "CHANGES_REQUESTED" or (.body != null and .body != "")) | {type: "review_summary", id, state, body}'

# Top-level PR conversation comments
gh api repos/{owner}/{repo}/issues/{number}/comments --paginate --jq '.[] | {type: "issue_comment", id, body}'
```

### 2. Categorize each comment

Read each comment and classify:

| Category | Definition | Action required |
|----------|-----------|----------------|
| **Blocking** | Code bug, logic error, missing test, security issue | Must fix before merge |
| **Advisory** | Style suggestion, naming preference, minor improvement | Fix or explain why not |
| **Question** | Reviewer asks for clarification | Reply with explanation |
| **Incorrect** | Reviewer suggestion is wrong or inapplicable | Reply with reasoning, escalate to user |

### 3. Process each comment

**Blocking:**
1. Fix the code

**Advisory:**
1. If adopting: fix the code
2. If declining: reply with reasoning why the change is not needed

**Question:**
1. Reply with explanation on GitHub

**Incorrect:**
1. Reply on GitHub: explain why the suggestion is incorrect or inapplicable
2. Escalate to user for confirmation before proceeding

### 4. Push all fixes in one commit

If any blocking or adopted advisory comments required code changes, group those fixes into a single commit referencing the PR:

```bash
git add <changed-files>
git commit -m "fix: address PR review comments (#<PR>)"
git push
```

If there were no code changes (for example, only Question, Incorrect, or declined Advisory comments), skip this step and continue to Step 5.

### 5. Reply to each fixed comment — with VERIFIED behavior claims

If Step 4 produced a fix commit, reply on GitHub for each blocking or adopted advisory comment with:

GitHub only auto-marks line-anchored comments as outdated when the referenced diff line changes. Diff position comments with `line: null` (common for Codex/Copilot bot comments) and issue-level/top-level comments are not auto-outdated, so reply to those manually after the fix lands.

1. The commit hash
2. What changed
3. **Behaviour verification (mandatory when the reply asserts behaviour).** If the reply makes a claim about how the fixed code behaves under any condition (e.g., "real errors still surface", "set -e safe", "race resolves to content-identical"), that claim **MUST** be backed by an executed verification: either cite the test fixture that exercises it, or include the local sanity-test command + observed exit code + observed output. Reasoning-only assertions about behaviour are forbidden — they have produced reviewer-self-correction loops where a subsequent bot review caught the assertion was false (PR #84 R6 precedent).

If there was no fix commit, reply only where applicable for Question, Incorrect, or declined Advisory comments.

### 6. Wait for CI **and the next bot review pass**

Verify CI passes after the fix commit.

**Iteration is normal**: automated bot reviewers (Codex bot, etc.) auto-trigger a fresh review pass on every new commit, typically within 30–90 seconds of push. **Do NOT close the PR loop after one fix round** — wait at least 2 minutes after `git push` and re-fetch comments per Step 1 to detect any new bot findings on the fix commit itself. Real PRs have run 5+ rounds (PR #84 ran 6 rounds, each catching new shell / cross-reference bugs introduced by the previous fix).

Stopping conditions for the iteration loop:
- No new top-level inline comments since last fix push (run Step 1 to verify).
- All threads either replied or closed by the original reviewer.
- CI green.

### 7. Do NOT self-resolve threads

The reviewer (human or bot) must confirm the fix and resolve the thread. Never resolve your own fix.

If the reviewer is an automated tool that cannot resolve, inform the user and let them resolve.

### 8. Doc-shell example mandatory pre-publish test

When a PR adds or modifies any **shell example** intended for users to copy-paste (recipes inside fenced ```bash blocks in SOPs, READMEs, or other docs), the example MUST be executed at least once locally **under `set -euo pipefail`** before push, in **all of the following representative states**:

- Empty / fresh state (no input files, no archive, no rollover) — should exit 0 with no output, not halt.
- Populated state with the expected happy-path content — should produce the documented output.
- Edge cases relevant to the example (e.g., for log-reading recipes: rollover present, archive corrupt, no matching entry, multi-session same-day).

Capture the verification in the commit message or in the Step 5 reply (per the behaviour-verification rule). Doc-shell examples that haven't been run under `set -euo pipefail` consistently produce bot findings in subsequent rounds — pre-testing eliminates the most common source of iteration loops.

---

## Reply Format

When replying to a comment on GitHub, include:

- **Commit reference:** which commit contains the fix
- **What changed:** brief description of the fix
- **If declining:** reasoning for not making the change

Example:
```
Fixed in abc1234. Narrowed exception catch to `(ValueError, OSError, MalformedDocumentError)`.
```

Example (declining):
```
This suggestion is incorrect — the INC template places Date before Severity (see `src/fx_alfred/templates/inc.md`). No change needed.
```

---

## Pitfalls

- **Self-resolving:** Resolving your own thread is meaningless — the reviewer must verify
- **Silent fixes:** Fixing code without replying on GitHub leaves the thread unresolved and untracked
- **Blanket dismiss:** Dismissing bot suggestions without reading them — automated reviewers can catch real bugs
- **Batch replies:** Replying "fixed all" without per-comment responses makes it hard to verify each fix
- **Confident-but-unverified behaviour claims in replies:** Asserting behavioural correctness ("real errors still surface", "race resolves identically") without executing the fixed code under the failure mode is the single highest-frequency way that subsequent bot reviews catch the *replier* rather than the original code (PR #84 R6 precedent). Always verify behaviour before asserting it.
- **Closing the loop after one fix round:** Bot reviewers auto-re-review every new commit. If you push a fix and walk away, you'll miss the next bot pass — which catches bugs your fix introduced (PR #84 ran 6 rounds; rounds 4-6 each caught new shell brittleness introduced by the prior round's fix).
- **Treating bot findings as "just lint":** Bot's static-diff cross-reference detector class catches genuine spec / shell / contract bugs that human and trinity-panel reviewers miss systematically (see "Reviewer Detector Classes" above). They are not stylistic suggestions — they are a different failure-mode population.

## Why bot reviewers catch what humans/panels miss

Five structural mechanisms (PR #78 / #80 / #82 / #84 evidence base, 12+ caught bugs):

1. **Diff-mode vs prose-mode reading.** Bot reads each commit's patch in ~30s; humans/panels read the post-fix document holistically. Cross-reference inconsistencies are systematically caught by diff-mode and missed by prose-mode (which fills "this section is internally consistent" gaps with charity).
2. **No author-self / no internal-model bias.** Bot is stateless — every commit is a fresh look. Author and panel after R+1 have an internal model of the spec; new commits get squeezed into that model rather than re-checked from zero.
3. **Execution-model-aware vs concept-aware.** Bot maintains an effective bash + jq + unzip + posix execution simulator. Humans/panels read shell as "logically reasonable" without mentally executing under `set -euo pipefail`.
4. **Coverage > framing.** Trinity review packs (verification questions, paranoid scrutiny areas) inadvertently define what reviewers DON'T look at. Bot has no pack: it scans whole-diff. Bugs outside the framed area only surface from unframed scanning.
5. **"Will it run?" vs "Is it correct?"** Bot focuses on last-mile execution; humans/panels work at the concept level. For implementer-facing docs (recipes, examples), the last mile matters most.

These are orthogonal mechanisms — none is "bot is smarter." The defensive practices are: (a) force diff-mode re-reads of own commits; (b) treat just-written code as foreign; (c) mentally execute every shell example; (d) include "free scrutiny" sections in review packs; (e) default-test under `set -euo pipefail`.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-04-04 | Initial version per Issue #28 | Claude Code |
| 2026-04-04 | PR review fix: fetch 3 endpoints (inline + review summary + issue comments), add --paginate, fix declining example to cite template not COR-0002 | Claude Code |
| 2026-04-05 | PR review fix: include empty-body CHANGES_REQUESTED reviews, move replies after commit/push, add explicit git push step | Codex |
| 2026-04-05 | Add note that diff-position and top-level comments do not auto-mark outdated | Codex |
| 2026-04-05 | Make Step 4 conditional when review responses do not require code changes | Codex |
| 2026-05-02 | Major amendment driven by PR #78 / #80 / #82 / #84 evidence (12+ Codex bot real-bug catches missed by trinity panel + author): (a) Add Reviewer Detector Classes table to §What Is It (bot vs trinity vs human vs author — orthogonal, not interchangeable). (b) §Step 5 mandates behaviour-verification for any reply that asserts behaviour — reasoning-only assertions are forbidden (PR #84 R6 caught my own reply where I claimed errors surface when they didn't). (c) §Step 6 reframes "wait for CI" as "wait for CI AND the next bot review pass" — bot auto-re-reviews each commit within 30–90s; iteration is normal (PR #84 ran 6 rounds). (d) New §Step 8 mandates `set -euo pipefail` pre-publish testing of every doc-shell example in 3 representative states (fresh / happy-path / edge cases). (e) §Pitfalls expanded with 3 new entries (unverified behaviour claims, single-round closing, treating bot as lint). (f) New §Why bot reviewers catch what humans/panels miss section explains the 5 structural mechanisms (diff-mode, no-author-bias, exec-simulator, no-pack-framing, execution focus) and the 5 derived defensive practices. | Frank + Claude (PR #84 retrospective) |
