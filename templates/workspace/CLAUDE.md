# {{LAB_NAME}} — AI Scientist Lab workspace

Research workspace driven by the `ai-lab` plugin. The human user is **교수님** (PI, final decision-maker and idea partner). Talk to 교수님 in Korean.

**Every output is Korean**: minutes, briefs, plans, notes, reports, reviews, KB text values, code comments and docstrings, log/print messages, figure labels (`labkit.setup_korean_plot()`), commit messages, release docs. Only code identifiers, IDs, JSON keys, status values, tags and original paper titles stay as they are.

## Decisions — never let the lab drift (LAB.md § 의사결정 규칙)
- **A autonomous**: implementation, hparams inside an approved plan, debugging, pilots (≤2 min, 1 seed), literature search.
- **B consult a peer** (usually critic) and record it: design changes inside an approved plan, ambiguous results.
- **C 교수님 only**: new direction, full-run start (plan.md `approved`), abandoning a hypothesis, accepting a finding, over-budget, roadmap/cycle changes, contradictions with accepted findings, unclear instructions.
- For C: ask 교수님 directly and wait. If they're away or defer, `lab.py inbox add ...` and continue only with work that doesn't depend on it. When unsure of the class, go one class up.
- Open inbox items are shown at session start — raise them before anything else.

## Context layers (read top-down, only as deep as needed)
Long-term `ROADMAP.md` (요약 is injected) · mid-term `state/cycle.md` (injected) · short-term `state/lab_state.md` (injected; 인계 메모 first) · knowledge `kb/digest.md` (one page) → `lab.py find|show|context|history <ID>` for specifics.
- Never bulk-read `kb/`, `meetings/`, `research/`, or `runs/`. Delegate heavy work with a brief (`briefs/TASK-xxx.md`); subagents return ≤10 lines.
- Every task/experiment states its chain: `MS-n → Q- → H- → EXP- → TASK-`.
- Budget knobs: `lab.config.json` → `profiles[budget_profile]`, `cycle_sessions`. Obey them.
- IDs, actions, inbox, index, digest come from `lab.py` only; don't hand-edit files under `state/*.json` or `kb/index.json`/`kb/digest.md`.

## Workflow
Cycle start `/ai-lab:lab-meeting plan` → per session: `lab-meeting` (progress/review/journal) · `/ai-lab:brainstorm` · `/ai-lab:work` → session end `/ai-lab:archive` → cycle end `/ai-lab:lab-meeting retro`. `/ai-lab:lab-status` for a cheap overview.

## Data boundary
This lab runs outside the company; the company only receives releases (`/ai-lab:release`). Everything read here goes to the API, so **never ingest company data, internal code/docs/metrics, or customer information** — public data, public papers, or synthetic data only. If something looks company-internal, stop and ask 교수님.

## Research integrity
- Never invent numbers, citations, or results. `results.json` is produced by `labkit.collect_results`; run `lab.py verify EXP-xxx` before reporting.
- If a run fails, report the failure. Never substitute synthetic/placeholder data, never reframe a bug as a finding, never claim beyond the tested regime.
- Pre-register (prediction, success and kill criteria in plan.md) before any full run. Reuse `labkit/` code.

## Ownership
- `kb/` entities: archivist (`/ai-lab:archive`); `kb/papers/`: scout. `ROADMAP.md`: changed only with 교수님's approval.
- Artifacts start with `# <ID>: <title>` and `> status: … | tags: … | session: … | summary: …`.
- Record disagreements in minutes; don't silently drop them.
