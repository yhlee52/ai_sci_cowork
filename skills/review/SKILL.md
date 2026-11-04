---
name: review
description: Strict verification in an ai-lab workspace, only when 교수님 asks — the verifier runs the experiment code (plan-code alignment, leakage, label shuffle, tiny overfit, seeds), the critic reviews design, statistics and claims, and the theorist tests mechanism claims; independent checks run in parallel and each writes a REV. Use when 교수님 says 엄격하게 검증해 / 리뷰해 줘 / 검증해 줘 for an experiment, campaign, plan, or draft.
argument-hint: "<EXP-/CMP-/IDEA-id | draft path> [코드|설계|주장|메커니즘 — focus, default all that apply]"
---

# Strict review — on request only

The default check is code (`lab.py audit`). This skill adds LLM reviewers when 교수님 wants more certainty, e.g. before a release to the company, for a surprisingly good result, a mechanism claim, or before a long full run. Tool: `python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py"`.

## 1. Pick reviewers (one line to 교수님, then go)
Target = first token of `$ARGUMENTS`; focus = the rest. Default by target:

| target | reviewers (parallel, one message) |
|---|---|
| EXP before approval (plan + pilot) | `verifier` (code: plan-code alignment, eval split, leakage, label shuffle, tiny overfit, seeds — runs as `pilot-verify-*`) + `critic` (plan) |
| EXP after a full run | `critic` (results; reads the audit) + `verifier` if code doubts were raised |
| CMP | `critic` (kept patches, eval gaming, confirmation) + `verifier` (can `train.py` influence the metric other than by training better?) |
| a mechanism claim ("왜 좋아졌나") | `theorist` mode `mechanism` + `critic` |
| vague predictions in a plan | `theorist` mode `predict` |
| a draft (paper, release, report) | `critic` (claims vs evidence) + `summarizer` mode `reverse` (given only the draft) |

Focus words narrow it: `코드` → verifier, `설계`/`주장` → critic, `메커니즘` → theorist. If 교수님 says "깊게", add a second critic with a different focus (methods/statistics vs. claims/scope).

## 2. Run
- `lab.py audit <id>` first (for drafts: `lab.py audit --report <path> --sources <ids>`); every reviewer gets its output.
- For each reviewer: `lab.py next rev` (or `next summary` for the summarizer) and a brief `briefs/REV-xxx.md` (≤20 lines: target, focus, what to read, output path). Prompt: brief path, output id, session, mode, `lab.py: python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py"`, "Follow your agent instructions."
- Launch the independent reviewers **in one message**. No reviewer fixes code — fixes go back to the engineer as actions.

## 3. Report and record
- Tell 교수님 (≤10 lines, Korean): each verdict (accept/minor/major/reject) with its top issue, whether it is safe to proceed, and what to fix. A `major`/`reject` → no automatic rerun; propose the fix as an action.
- Append `## 엄격 검증 <id>` to the current `meetings/session_NNN.md`: REV ids, verdicts, 교수님's call. The archivist sets the finding's `review_level` to `strict` from this.
- Mechanism claims without a regime-shift check stay scoped to the tested setting; the theorist's proposed check becomes an action (a new experiment is class C).
