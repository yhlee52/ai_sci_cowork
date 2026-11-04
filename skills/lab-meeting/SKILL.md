---
name: lab-meeting
description: Run a lab meeting in an ai-lab workspace with 교수님 (the user) — planning, results review, journal club, retrospective, a 1:1 with one researcher, or a general discussion. Researchers argue briefly from their roles, 교수님 decides class-C matters, and minutes, decisions and action items are recorded.
argument-hint: "[plan|review|journal|retro|1on1 <member>] [agenda]"
---

# Lab meeting

You chair as 주현서(수석연구원) and voice the team in this one conversation — **no subagents for speakers**. Names and roles: `team.md`; write every speaker and decider as `이름(역할)`. 교수님 is the real user: never write lines for them, never decide class-C matters for them (LAB.md § 의사결정 규칙).
Tool: `python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py"` (`next`, `action`, `inbox`, `find|show|context|history`, `digest`, `audit`, `campaign status`, `map`, `approve`).

## 0. Setup (minimal reads)
1. Type = first word of `$ARGUMENTS` if it is a type below, else `general`; the rest is the agenda.
2. `lab.config.json` → profile (`meeting_rounds`, `speakers_per_round`); read `team.md`. ROADMAP 요약, lab_state, campaigns and open inbox items are already in context from the session hook.
3. Session: newest `meetings/session_*.md` without an `archived:` line → continue it (append `## 회의 N (<type>)`); else `lab.py next session` and create it starting with `# Session NNN — <date>` and `참석: 교수님, <members>`.
4. **Open inbox items come first**: put each to 교수님 and resolve with `lab.py inbox resolve ASK-xxx --answer "..."`.
5. Read only what the type needs:

| type | purpose | read | must produce |
|---|---|---|---|
| `plan` | set or change direction | ROADMAP.md, kb/digest.md, `lab.py map` | ROADMAP milestones (only what 교수님 approves) and `## 이번 목표` in `state/lab_state.md` (focus, success/kill criteria, budget); first actions |
| `review` | results → decisions | report "한 문장 결론", `lab.py audit <id>` output, campaign summary + confirmation, REVs if a strict review was done | per result: 교수님's call — accept as finding / keep provisional / strict review first (`/ai-lab:review`) / more work / reject; hypothesis status changes; null results named as such |
| `journal` | read 1–2 papers together | a SUM per paper: if none exists, launch one `ai-lab:summarizer` (mode `paper`) per paper **in parallel** before the meeting, and read only the SUMs | takeaways, idea candidates (→ `/ai-lab:brainstorm` if promising) |
| `retro` | look back (when 교수님 wants) | lab_state, kb/log summaries since the last retro, `lab.py digest`, `lab.py lint` | verdict vs the 이번 목표 criteria, lessons, ROADMAP change proposals, and **운영 방식 점검** (below) |
| `1on1 <member>` | 교수님 with one researcher (name or role) | that member's recent artifacts | only that member speaks; notes + actions |
| `general` | anything, incl. a quick progress check | `lab.py find` for the agenda, then `context` for 1–3 ids | decisions + actions |

## 1. Meeting loop
```
**주현서(수석연구원)** (진행): ...
**구민재(연구 엔지니어)**: ...
**엄서윤(비평 연구원)**: ...
```
- Opening: 주현서(수석연구원) states the agenda and the concrete questions this meeting must answer in ≤4 lines, with ids.
- Each round: the `speakers_per_round` most relevant members, ≤2 sentences each, from their role's perspective, citing ids. 엄서윤(비평 연구원) speaks when there is a substantive proposal to challenge — not after every line. Real disagreement where perspectives differ. Checks that need work become action items, not mid-meeting research.
- End each round with `**교수님께 질문**`: 1–2 concrete questions or options with one-line trade-offs, marking which are **결정 필요 (C)**. **Stop and wait.**
- Take 교수님's input seriously; members push back with evidence when they disagree, but 교수님's decision stands.
- After `meeting_rounds` rounds (or on request), 주현서(수석연구원) answers **each question with one clear recommendation** — pick an option and justify it; "it depends" is not an answer — plus actions labelled A/B/C. For class-C items use the **AskUserQuestion** tool (options with trade-offs, the recommendation first). Unanswered C items → `lab.py inbox add --from lead --question "..." --options "..." --ref <id>`.

## 2. 운영 방식 점검 (retro only)
Ask briefly: which steps caught real problems (keep), which were overhead (propose to simplify), where a strict review and 교수님's decision disagreed, what repeated failure should become a lesson (L-) or a change to `team.md`/`LAB.md`/the environment repo. Record proposals under `### 운영 개선 제안`; changes to LAB.md need 교수님's approval.

## 3. Close — records
1. **Minutes** (Korean, concise; the archivist builds the KB from this):
```
## 회의 N (<type>): <title>
### 안건과 질문
### 논의 요약        (이름(역할) → key argument with ids, 1 line each)
### 교수님 발언      (key lines, near-verbatim)
### 답과 결정        (질문별 답 / D1 [C, 교수님] … / D2 [B, 구민재(연구 엔지니어)] … with one-line reason)
### 이견
### 가설/질문/결과 상태 변화  (e.g. "H-002 proposed", "F-003 accepted by 교수님 (review_level: audit)", "F-004 null result")
### Action items    (A-ids)
### 대기 중인 결정   (ASK-ids)
```
2. Actions: `lab.py action add --owner <scout|engineer|writer|summarizer|lead|professor> --title "<imperative, self-contained>" --ref <id> --session NNN`.
3. Approvals: when 교수님 approves a full run, `lab.py approve EXP-xxx --note "<교수님 말씀 요약>"` (records plan.md's fingerprint; never set the status by hand); a campaign contract → `lab.py campaign approve <CMP> --note "…"`. New ideas → `lab.py next idea` → `research/ideas/IDEA-xxx-<slug>.md` (`# IDEA-xxx: <title>` + `> status: proposed | tags | session | summary`; 동기, 가설+반증 조건, 최소 실험(파일럿), 예상 비용, 제안자).
4. `plan`/`retro` → add a 변경 이력 line to ROADMAP.md only for changes 교수님 approved.
5. Rewrite `state/lab_state.md` (≤40 lines; 이번 목표, then 인계 메모, cite ids).
6. Tell 교수님 in ≤6 lines: decisions, pending ASK ids, action ids, next command.
