---
name: brainstorm
description: Multi-agent brainstorm in an ai-lab workspace — several ideator subagents with different lenses generate ideas independently and in parallel, the ideas are merged, scored by the critic, refined, and the shortlist is brought to 교수님 to decide. Use when the lab needs new research ideas or hypotheses on a topic.
argument-hint: "<topic or question> [lenses: theory,empirical,...]"
---

# Brainstorm (generate → merge → critique → refine → 교수님 decides)

Design: independent parallel generation keeps ideas diverse (agents never see each other's answers); a single critic pass ranks them; 교수님 makes the call. Tool: `python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py"`.

## 0. Setup
1. Profile from `lab.config.json`: `brainstorm_agents` (N), `ideas_per_agent`, compute budget. Lenses: those named in `$ARGUMENTS`, else the first N rows of the lens table in `team.md`.
2. `lab.py next brainstorm` → `BS-xxx`; create `research/brainstorms/BS-xxx/`.
3. Write `brief.md` there (≤40 lines, Korean): topic (from `$ARGUMENTS`), goal chain (ROADMAP milestone → Q-/H- if any), constraints (8GB GPU, pilot ≤2 min, full-run budget), and **what the lab already knows/tried** — from `kb/digest.md` and 1–3 `lab.py find` queries, as one-liners with ids (include refuted hypotheses and failed experiments: they prevent repeats).

## 1. Generate — parallel, independent
Launch N `ai-lab:ideator` subagents **in one message** (parallel). Each prompt: `Brainstorm dir research/brainstorms/BS-xxx/. Lens: <lens>. Ideas: <ideas_per_agent>. lab.py: python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py". Follow your agent instructions.` Nothing else — no hints from other lenses.

## 2. Merge (you, cheap)
Read the N `<lens>.md` files. Deduplicate and cluster near-identical ideas (keep the best elements of each and credit all source lenses). Write `candidates.md`: C1…Ck (k ≤ 8), each 3 lines: idea, falsifiable hypothesis, pilot + cost. Keep one high-novelty "wildcard" even if risky.

## 3. Critique and rank
One `ai-lab:critic` subagent with a short brief: score candidates.md on novelty, feasibility, testability, fit to goal chain (1–5 each) → write `research/brainstorms/BS-xxx/scores.md`. (In the `deep` profile, also ask `ai-lab:scout` for a quick "done-before?" check on the top 3, ≤3 sources each.)

## 4. Refine the top 3 (you)
One improvement pass per top candidate: fix the critic's main objection, simplify, or combine complementary candidates. Don't invent new directions here.

## 5. Bring it to 교수님 — class C, wait for the answer
Present in Korean:
```
| 후보 | 가설 (반증 조건) | 파일럿 비용 | 점수 N/F/T/Fit | 가장 큰 위험 | 출처 lens |
```
top 3 + wildcard, then a short **하진의 추천** with the reason, then ask: 어떤 것을 진행할까요? (선택 / 결합 / 수정 / 전부 보류 / 한 라운드 더). **Stop and wait.** Discuss in the lab-meeting voice if 교수님 wants to debate.

## 6. Record the decision
- `summary.md` in the BS dir: first lines `# BS-xxx: <topic>` and `> status: decided | tags: … | session: NNN | summary: <what was chosen>`; then the table, 교수님's decision and reasons, and the rejected candidates in one line each (they stay searchable for later).
- For each chosen idea: `lab.py next idea` → `research/ideas/IDEA-xxx-<slug>.md` (format in the lab-meeting skill), and action items (`lab.py action add`): usually a scout novelty check and an engineer **pilot** (class A).
- Append `## 브레인스토밍 BS-xxx` (5–8 lines: lenses used, candidates, decision, actions) to the current `meetings/session_NNN.md` (create/continue the session as the lab-meeting skill does). Update `state/lab_state.md`.
