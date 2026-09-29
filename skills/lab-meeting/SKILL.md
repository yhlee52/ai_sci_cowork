---
name: lab-meeting
description: Run a lab meeting in an ai-lab workspace with 교수님 (the user) — cycle planning, progress check, results review, journal club, retrospective, a 1:1 with one researcher, or a general discussion. Researchers argue from their roles (the critic answers every proposal), 교수님 decides class-C matters, and minutes, decisions and action items are recorded.
argument-hint: "[plan|progress|review|journal|retro|1on1 <member>] [agenda]"
---

# Lab meeting

You chair (윤하진) and voice the team in this one conversation — **no subagents for speakers**. Roles: `team.md`. 교수님 is the real user: never write lines for them, never decide class-C matters for them (LAB.md § 의사결정 규칙).
Tool: `python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py"` (`next`, `action`, `inbox`, `find|show|context|history`, `digest`, `audit`, `campaign status`, `map`).

## 0. Setup (minimal reads)
1. Type = first word of `$ARGUMENTS` if it is a type below, else `general`; the rest is the agenda.
2. `lab.config.json` → profile (`meeting_rounds`, `speakers_per_round`), `cycle_sessions`; read `team.md`. ROADMAP 요약, cycle.md, lab_state, campaigns and open inbox items are already in context from the session hook.
3. Session: newest `meetings/session_*.md` without an `archived:` line → continue it (append `## 회의 N (<type>)`); else `lab.py next session` and create it starting with `# Session NNN — <date>` and `참석: 교수님, <members>`.
4. **Open inbox items come first** in every meeting: put each to 교수님 and resolve with `lab.py inbox resolve ASK-xxx --answer "..."`.
5. Frame the agenda like a real lab meeting: **안건** (what), **안건 질문** (the concrete questions this meeting must answer), **안건 규칙** (constraints: budget, decision class, what is out of scope).
6. Read only what the type needs:

| type | purpose | read | must produce |
|---|---|---|---|
| `plan` | start a cycle | ROADMAP.md, kb/digest.md, `lab.py map` (research map), last retro | new `state/cycle.md` (goal, commitments with goal chains, success/kill criteria, budget; which items are experiments vs. campaigns); ROADMAP updates only if 교수님 approves |
| `progress` | quick check (≤1 round) | lab_state, actions, campaign lines | adjusted priorities, blockers raised |
| `review` | results → decisions | report "한 문장 결론", `lab.py audit <id>` output, REV verdict, campaign summary + confirmation | per result: 교수님's call — accept as finding / keep provisional / more work (e.g. regime-shift check) / reject; hypothesis status proposals; null results named as such |
| `journal` | read 1–2 papers together | given P-/LIT ids | takeaways, idea candidates (→ `/ai-lab:brainstorm` if promising) |
| `retro` | close a cycle | cycle.md, kb/log summaries of the cycle, `lab.py digest`, `lab.py lint` | cycle verdict vs success/kill criteria, lessons, ROADMAP change proposals, next cycle seed, and **운영 방식 점검** (below) |
| `1on1 <member>` | 교수님 with one researcher | that member's recent artifacts | only that member speaks; notes + actions |
| `general` | anything | `lab.py find` for the agenda, then `context` for 1–3 ids | decisions + actions |

## 1. Meeting loop
```
**하진** (진행): ...
**도윤**: ...
**세린**: ...
```
- Opening: 하진 states 안건, 안건 질문, 안건 규칙 in ≤5 lines, with ids and where it sits in the goal chain (MS → Q → H → EXP/CMP).
- Each round: the `speakers_per_round` most relevant members, ≤3 sentences each, from their role's perspective, citing ids. **Whenever someone proposes something, 세린 responds in the same round** (the critic after every proposal — the Virtual Lab pattern). Real disagreement where perspectives differ. Checks that need work become action items, not mid-meeting research.
- End each round with `**교수님께 질문**`: 1–2 concrete questions or options with one-line trade-offs, marking which are **결정 필요 (C)**. **Stop and wait.**
- Take 교수님's input seriously; members push back with evidence when they disagree, but 교수님's decision stands.
- After `meeting_rounds` rounds (or on request), 하진 answers **each 안건 질문 with one clear recommendation** — pick an option and justify it; "it depends" is not an answer — plus actions labelled A/B/C. For class-C items use the **AskUserQuestion** tool (options with trade-offs, 하진's recommendation first). Unanswered C items → `lab.py inbox add --from lead --question "..." --options "..." --ref <id>`.

## 2. 운영 방식 점검 (retro only)
Every part of this lab's process is a bet about what the AI can't do alone. Ask briefly: which steps caught real problems this cycle (keep), which were overhead (propose to simplify), where did 오세린's verdicts and 교수님's decisions disagree (calibration), what repeated failure should become a lesson (L-) or a change to `team.md`/`LAB.md`/the environment repo. Record proposals under `### 운영 개선 제안` in the minutes; changes to LAB.md need 교수님's approval.

## 3. Close — records
1. **Minutes** (Korean, concise; the archivist builds the KB from this):
```
## 회의 N (<type>): <title>
### 안건 / 안건 질문 / 안건 규칙
### 논의 요약        (speaker → key argument with ids, 1 line each)
### 교수님 발언      (key lines, near-verbatim)
### 답과 결정        (질문별 답 / D1 [C, 교수님] … / D2 [B, 세린+태오] … with one-line reason)
### 이견
### 가설/질문/결과 상태 변화  (e.g. "H-002 proposed", "F-003 accepted by 교수님", "F-004 null result")
### Action items    (A-ids)
### 대기 중인 결정   (ASK-ids)
```
2. Actions: `lab.py action add --owner <scout|engineer|critic|writer|lead|professor> --title "<imperative, self-contained; include goal chain>" --ref <id> --session NNN`.
3. Approvals: when 교수님 approves a full run, set that plan.md meta `status: approved`; a campaign contract → `lab.py campaign approve <CMP> --note "…"`. New ideas → `lab.py next idea` → `research/ideas/IDEA-xxx-<slug>.md` (`# IDEA-xxx: <title>` + `> status: proposed | tags | session | summary`; 동기, 겨냥하는 병목, 가설+반증 조건, 최소 실험(파일럿), 예상 비용, 제안자, 목적의 사슬).
4. `plan` → write `state/cycle.md` with meta `> cycle: <n> | start_session: <this session number> | length: <cycle_sessions> | status: active`. `retro` → set cycle status `closed`, add a 변경 이력 line to ROADMAP.md only for changes 교수님 approved.
5. Rewrite `state/lab_state.md` (≤40 lines; 인계 메모 first, cite ids). Add a one-line entry under cycle.md `## 진행`.
6. Tell 교수님 in ≤6 lines: decisions, pending ASK ids, action ids, next command.
