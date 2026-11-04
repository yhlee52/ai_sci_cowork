---
name: work
description: Execute open lab action items in an ai-lab workspace by delegating each to the right researcher subagent (scout, engineer, writer, summarizer) with a compact brief, enforcing the decision rules (pilots autonomous, full runs and findings need 교수님), then log results. Results are checked by code (`lab.py audit`); LLM reviews only when 교수님 asks. Use after a lab meeting or brainstorm produced action items, or when 교수님 asks for a task.
argument-hint: "[action ids | all]"
---

# Work session — execute action items

Tool: `python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py"` (`action`, `inbox`, `next`, `find|context`, `audit`, `approve`, `doctor`, `index`).

## 1. Select
- `lab.py action list`. Take the ids in `$ARGUMENTS`, or all open items not owned by `professor`. If 교수님 asked for something with no action yet, `lab.py action add` it first.
- Profile from `lab.config.json` (`max_parallel_agents`, `literature_sources`) and `compute.limits` (every plan must fit them).
- Skip items that depend on an open inbox (ASK) decision — say so.
- Order by dependency (literature → plan/pilot → full run → report). At most `max_parallel_agents` subagents at once; independent items may run in parallel.

## 2. Brief each task (the main token saver)
Context via `kb/digest.md`, `lab.py find` / `context <id>` — not by opening directories. Output id from `lab.py next lit|exp|summary` (or an existing EXP id). Write `briefs/A-xxx.md` (named after the action, Korean, ≤30 lines):
```
# A-xxx → <agent> → <output id>   (세션 NNN, 실험이면 단계 pilot|full)
## 목표            "완료"의 의미, 1~2문장 (아는 만큼 목적의 사슬: MS → Q → H → EXP)
## 맥락            필요한 사실만, ID로 인용 (D-, H-, F-, P-, DS-, M-, L-). 관련 교훈(L-) 포함
## 읽을 것         정확한 ID/경로 (agent는 `lab.py show`로 펼쳐 읽는다)
## 산출물          정확한 경로 (형식은 agent 명세를 따른다)
## 제약            예산 (문헌 수 / 시드 / GPU 분), 결정 등급 한계, 하지 말 것
## 보고            10줄 이하. A 등급을 넘는 것은 `NEEDS DECISION:` 줄로
```

## 3. Delegate
- Owners → subagents: `scout` → `ai-lab:scout`, `engineer` → `ai-lab:engineer`, `writer` → `ai-lab:writer`, `summarizer` → `ai-lab:summarizer`. Owner `lead` → do it yourself. Review-type owners (`critic`, `verifier`, `theorist`) are strict verification → hand them to `/ai-lab:review` only if 교수님 asked for it; otherwise ask 교수님 in one line whether it's still wanted.
- Prompt: brief path, output id, session number, stage (or mode), `lab.py: python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py"`, "Follow your agent instructions." Nothing else.
- Parallel only where the work is independent (e.g. one scout per sub-question). Never two agents writing the same file, or GPU runs beyond `compute.limits.parallel_runs`.
- **Experiment gates**
  - First experiment in this lab: the engineer runs `lab.py doctor` first.
  - Pilot: autonomous. Then bring the plan (pilot numbers labelled as pilot, cost of the full run) to 교수님 for full-run approval — or, if the next step is a search over one metric, to `/ai-lab:campaign plan`. If something in the pilot looks risky (too good, odd curves, leakage suspicion), say so in one line and offer `/ai-lab:review <EXP>`; don't run it unasked.
  - Full run: only after 교수님 approved it and you recorded it with `lab.py approve EXP-xxx --note "…"` (`labkit.Run` refuses non-pilot runs without that record).
  - After a full run the engineer writes the short `report.md` and `lab.py audit` must PASS. That is the default check. A writer is needed only for a longer write-up 교수님 asked for.

## 4. Decisions raised during work
When a subagent returns `NEEDS DECISION:` (or you hit a class-C matter):
- If 교수님 is in the conversation, ask right away with the **AskUserQuestion** tool: the question, options with one-line trade-offs (your recommendation first). **Wait** for the answer, record it (minutes `답과 결정`; a full-run approval with `lab.py approve`), then continue.
- If 교수님 defers, `lab.py inbox add --from <agent> --question "..." --options "..." --ref <id>` and continue only with independent items.
- Class B: record the reason in the work log and tell 교수님 in one line.
- Honest failure is a valid result: if an agent reports that something is infeasible or failed, record it as such — never ask it to "make it work somehow" with substitute data.

## 5. Log (after each return)
- `lab.py action done A-xxx --result "<one line>"`; add follow-ups with `lab.py action add`.
- Append to the current `meetings/session_NNN.md` under `## 작업 로그`: `A-xxx · <담당> · <output id> · <one-line result>`. State failures, surprises, deviations and lessons explicitly — the archivist files them.
- Relay subagent reports (≤10 lines); never paste their files.

## 6. Finish
`lab.py index`. Rewrite `state/lab_state.md` (≤40 lines; 인계 메모 first). Report to 교수님 in Korean: table (action · 담당 · 결과 · 감사), decisions waiting (ASK ids), next step (e.g. `/ai-lab:lab-meeting review`, or `/ai-lab:archive` at the end of the session).
