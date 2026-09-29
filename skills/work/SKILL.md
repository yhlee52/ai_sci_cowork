---
name: work
description: Execute open lab action items in an ai-lab workspace by delegating each to the right researcher subagent (scout, engineer, critic, writer) with a compact task brief, enforcing the decision rules (pilots autonomous, full runs and findings need 교수님), then log results. Use after a lab meeting or brainstorm produced action items.
argument-hint: "[action ids | all]"
---

# Work session — execute action items

Tool: `python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py"` (`action`, `inbox`, `next`, `find|context`, `audit`, `doctor`, `index`).

## 1. Select
- `lab.py action list`. Take the ids in `$ARGUMENTS`, or all open items not owned by `professor`.
- Profile from `lab.config.json` (`max_parallel_agents`, `review_passes`, `literature_sources`) and `compute`.
- Skip items that depend on an open inbox (ASK) decision — say so.
- Order by dependency (literature → plan/pilot → full run → report → review). At most `max_parallel_agents` subagents at once; independent items may run in parallel.

## 2. Brief each task (the main token saver)
Context via `kb/digest.md`, `lab.py find` / `context <id>` — not by opening directories. `lab.py next task` and the output id (`next lit|exp|rev`, or an existing EXP id). Write `briefs/TASK-xxx.md` (Korean, ≤40 lines):
```
# TASK-xxx → <agent> → <output id>   (할 일 A-xxx, 세션 NNN, 실험이면 단계 pilot|full)
## 목적의 사슬      MS-n → Q-xxx → H-xxx → EXP-xxx   (이 일이 왜 중요한가)
## 단계            (실험이면) 재현 / 공정한 기준선 / 파일럿 / 본 실험 / 절제 / 조건 이동 점검
## 목표            "완료"의 의미, 1~2문장
## 맥락            필요한 사실만, ID로 인용 (D-, H-, F-, P-, DS-, M-, L-). 관련 교훈(L-) 포함
## 읽을 것         정확한 ID/경로 (agent는 `lab.py show`로 펼쳐 읽는다)
## 산출물          정확한 경로 (형식은 agent 명세를 따른다)
## 제약            예산 (문헌 수 / 시드 / GPU 분), 결정 등급 한계, 하지 말 것
## 보고            10줄 이하. A 등급을 넘는 것은 `NEEDS DECISION:` 줄로
```

## 3. Delegate
- Owners → subagents: `scout` → `ai-lab:scout`, `engineer` → `ai-lab:engineer`, `critic` → `ai-lab:critic`, `writer` → `ai-lab:writer`. Owner `lead` → do it yourself.
- Prompt: brief path, output id, session number, stage, `lab.py: python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py"`, "Follow your agent instructions." Nothing else.
- **Experiment gates**
  - First experiment in this lab: the engineer runs `lab.py doctor` first.
  - Pilot: autonomous. After it, the plan (with pilot numbers, labelled as pilot) goes to 교수님 for full-run approval — or, if the next step is a search over one metric, to `/ai-lab:campaign plan`.
  - Full run: only if plan.md status is `approved`. Otherwise ask 교수님 now (see §4).
  - After a full run: `lab.py audit` must PASS → writer report (audit again: no unknown numbers) → critic review. With `review_passes` ≥ 2, run that many critics **in parallel** with different focus (methods/statistics vs. claims/scope) and merge their verdicts.
  - A mechanism claim needs a regime-shift check (or a scope limited to the tested setting) before it can become a finding — add it as an action when the critic asks for it.
  - A `major`/`reject` verdict → no automatic rerun; it goes to the next `review` meeting.

## 4. Decisions raised during work
When a subagent returns `NEEDS DECISION:` (or you hit a class-C matter):
- If 교수님 is in the conversation, ask right away with the **AskUserQuestion** tool: the question, options with one-line trade-offs (your recommendation first), the critic/engineer view if relevant. **Wait** for the answer, record it (minutes `답과 결정`, plan status if an approval), then continue.
- If 교수님 defers, `lab.py inbox add --from <agent> --question "..." --options "..." --ref <id>` and continue only with independent items.
- Class B: get a peer view (usually a short critic call) before proceeding, and log it.
- Honest failure is a valid result: if an agent reports that something is infeasible or failed, record it as such — never ask it to "make it work somehow" with substitute data.

## 5. Log (after each return)
- `lab.py action done A-xxx --result "<one line>"`; add follow-ups with `lab.py action add`.
- Append to the current `meetings/session_NNN.md` under `## 작업 로그`: `A-xxx · <담당> · <output id> · <one-line result>`. State failures, surprises, deviations and lessons explicitly — the archivist files them.
- Relay subagent reports (≤10 lines); never paste their files.

## 6. Finish
`lab.py index`. Rewrite `state/lab_state.md` (≤40 lines; 인계 메모 first). Report to 교수님 in Korean: table (action · 담당 · 결과), decisions waiting (ASK ids), next step (usually `/ai-lab:lab-meeting review`, then `/ai-lab:archive`).
