---
name: paper
description: Draft a Korean paper or technical report from the lab's findings in an ai-lab workspace — claims only from reviewed findings, numbers only from result files, citations only from verified paper entries — then audit it; a conference-style review only when 교수님 asks.
argument-hint: "<F-ids or topic> [report|workshop]"
disable-model-invocation: true
---

# Paper — an evidence-traceable write-up

Every claim → a finding (F-) → its evidence (EXP/CMP result files); every number → a result file; every citation → a verified P- entry. This is what separates a real write-up from a plausible-sounding one. Tool: `python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py"`.

## 1. Gather (you)
- Findings: the ids in `$ARGUMENTS`, or `lab.py find <topic> --type finding`. For each: `lab.py context <F-id>` (evidence, reviews, papers). Only `accepted` findings are claims; `provisional` ones may appear only labelled "잠정"; null/negative results that bound the claims belong in the paper too.
- `lab.py lit check` must be clean for every paper you will cite.
- Missing evidence (audit fails, no regime-shift check for a mechanism claim) → list it; don't paper over it. Show each finding's `review_level` (audit / strict) so 교수님 can decide whether a strict review is wanted first.

## 2. Outline — class C, confirm with 교수님
Show: working title, the 1–3 claims (with F-ids), what is explicitly **not** claimed, figure list, target form (`report` 기술 보고서 / `workshop` 4쪽 논문). Use AskUserQuestion (`이대로 진행` / `수정` / `보류`). Wait.

## 3. Draft (`ai-lab:writer`, brief with the approved outline)
`research/papers/<slug>/paper.md` (Korean; English only if 교수님 asks):
`# 제목` + `> status: draft | tags | session | summary`; 초록 · 서론 · 관련 연구 ([P-xxx]로 인용) · 방법 · 실험 설정 · 결과 (표와 그림은 결과 파일에서 다시 생성) · 한계와 검증하지 않은 범위 · 부정적 결과 · 결론 · 재현 정보 · 참고문헌 (P- 항목의 제목, 저자, 연도, 링크).

## 4. Audit (you)
`lab.py audit --report research/papers/<slug>/paper.md --sources <EXP/CMP ids>` → fix every unknown number (실패) and missing citation; numbers from papers stay in sentences that cite their P- id.

## 5. Report
Tell 교수님 (≤8 lines): path, claims made, audit result, what remains weak, and the review level of the findings it rests on. Record in the minutes; status stays `draft` until 교수님 approves it.

## 6. Review and revise (only if 교수님 asks)
`/ai-lab:review research/papers/<slug>/paper.md` — a conference-style critic REV (요약, 강점, 약점, 질문, 재현 가능성, 주장-증거 일치, 점수 1–10) plus a summarizer reverse read given **only** the draft. Any claim stronger than, missing from, or new to the outline approved in §2 is a revision item; the writer revises once and the audit is re-run.
