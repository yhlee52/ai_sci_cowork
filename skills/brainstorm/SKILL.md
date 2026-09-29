---
name: brainstorm
description: Multi-agent brainstorm in an ai-lab workspace — several ideator subagents with different lenses generate ideas independently and in parallel; the ideas are merged, checked for prior-art collisions, ranked by pairwise comparison, refined, optionally piloted, and the shortlist is brought to 교수님 to decide. Use when the lab needs new research ideas or hypotheses on a topic.
argument-hint: "<topic or question> [lenses: theory,empirical,...]"
---

# Brainstorm (generate → merge → prior-art check → pairwise rank → refine → pilot → 교수님 decides)

Design (from the co-scientist / ideation literature): independent parallel generation keeps ideas diverse; ideas are compared **in pairs** (absolute LLM scores are poorly calibrated); prior art is checked with real bibliographic search; and because ideas look better on paper than after execution, the top candidates can get a 2-minute **pilot** before 교수님 chooses. Tool: `python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py"`.

## 0. Setup
1. Profile from `lab.config.json`: `brainstorm_agents` (N), `ideas_per_agent`, `pilot_tournament`, compute budget. Lenses: those named in `$ARGUMENTS`, else the first N rows of the lens table in `team.md`.
2. `lab.py next brainstorm` → `BS-xxx`; create `research/brainstorms/BS-xxx/`.
3. Write `brief.md` there (≤40 lines, Korean): topic, goal chain (ROADMAP milestone → Q-/H-), constraints (the hardware limits from `lab.config.json → compute.limits` in one line, pilot ≤2 min, full-run budget), **what the lab already knows** and **what already failed** — from `kb/digest.md` ("실패한 방향", "효과 없음" sections) and 1–3 `lab.py find` queries, as one-liners with ids.

## 1. Generate — parallel, independent
Launch N `ai-lab:ideator` subagents **in one message** (parallel). Each prompt: `Brainstorm dir research/brainstorms/BS-xxx/. Lens: <lens>. Ideas: <ideas_per_agent>. lab.py: python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py". Follow your agent instructions.` Nothing else — no hints from other lenses.

## 2. Merge (you, cheap)
Read the N `<lens>.md` files. Deduplicate and cluster near-identical ideas (keep the best elements, credit all source lenses). Write `candidates.md`: C1…Ck (k ≤ 6), each 3 lines: idea, falsifiable hypothesis, pilot + cost. Keep one high-novelty "wildcard" even if risky.

## 3. Prior-art check (`ai-lab:scout`, mode `scoop-check`)
Brief: candidates.md, ≤3 sources per candidate, output `research/brainstorms/BS-xxx/scoop.md`. A candidate that is `이미 있음` is dropped or reframed around its stated difference.

## 4. Pairwise ranking (`ai-lab:critic`)
`lab.py rank schedule C1 C2 … Ck` → put the printed pair list in the critic's brief; the critic writes `research/brainstorms/BS-xxx/pairs.md` with one `Cx > Cy | 이유` line per pair (it also sees scoop.md). Then `lab.py rank score --file research/brainstorms/BS-xxx/pairs.md` → ranking table (deterministic Bradley-Terry). Save the table to `ranking.md`.

## 5. Refine the top 3 (you)
One improvement pass per top candidate: fix the critic's main objection, simplify, or combine complementary candidates. Don't invent new directions here.

## 6. Pilot tournament (if `pilot_tournament` is on in the profile)
For the top 2: an `ai-lab:engineer` pilot each (class A, ≤2 min, 1 seed, clearly labelled pilot). A pilot says only "code works / any signal / real cost", never "better".

## 7. Bring it to 교수님 — class C, wait for the answer
Present in Korean:
```
| 후보 | 가설 (반증 조건) | 선행연구 확인 | 순위(점수) | 파일럿 신호 | 비용 | 가장 큰 위험 |
```
top 3 + wildcard, then a short **하진의 추천** with the reason. Ask with the AskUserQuestion tool (options: 1순위 진행 / 2순위 진행 / 결합 / 한 라운드 더 — each with a one-line trade-off; 교수님 can always type something else). **Wait.** Discuss in the lab-meeting voice if 교수님 wants to debate.

## 8. Record the decision
- `summary.md` in the BS dir: `# BS-xxx: <topic>` + `> status: decided | tags: … | session: NNN | summary: <what was chosen>`; the table, 교수님's decision and reasons, and rejected candidates in one line each (they stay searchable).
- For each chosen idea: `lab.py next idea` → `research/ideas/IDEA-xxx-<slug>.md` (format in the lab-meeting skill) and action items (`lab.py action add`): usually the full plan with pre-registration, or a campaign plan if it is a search over one metric.
- Append `## 브레인스토밍 BS-xxx` (5–8 lines) to the current `meetings/session_NNN.md`. Update `state/lab_state.md`.
