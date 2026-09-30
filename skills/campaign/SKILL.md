---
name: campaign
description: Autonomous exploration in an ai-lab workspace, started whenever 교수님 asks (run it now, or leave it running unattended/overnight) — 교수님 approves a bounded search contract once; then the explorer proposes one change per trial while lab.py runs every trial on a fixed time budget and decides keep/discard from the metric; the campaign ends with a fresh-seed confirmation, a summary, a review, and a decision request. Use when 교수님 asks for 자율 탐색 / autonomous exploration, or for a search over one metric (hyperparameters, architecture tweaks, training tricks).
argument-hint: "[<EXP-id> — plan and start] | plan <EXP-id|IDEA-id> | run <CMP-id> | status <CMP-id> | stop <CMP-id>"
---

# Campaign — bounded autonomy (proposals by AI, judgement by code)

Karpathy's autoresearch loop (fixed-time trials, keep-or-discard, a ledger) with this lab's safeguards: the contract is approved by 교수님 (class C); only listed files may change; the evaluation code is hash-protected; keep/discard is computed by `lab.py` from the metric with a noise threshold measured on the baseline — never by an agent's self-assessment (self-evaluating loops "see" progress that isn't there); the winner is re-checked on fresh seeds; nothing becomes a finding without review and 교수님.
Tool: `python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py" campaign …` (every call runs at most one trial, so it always fits in one command).

Subcommand = first word of `$ARGUMENTS`. Without one — 교수님 simply asked to explore (e.g. "EXP-003으로 자율 탐색해") — an approved, unfinished campaign for that experiment → `run` it; otherwise `plan` on the named experiment (ask which one if unclear) and, once approved, go straight on to `run` in this session. Autonomy is not tied to a time of day.

## plan <EXP-id | IDEA-id>
1. Read the source (plan.md, pilot result, `lab.py context <id>`). A campaign needs a **pilot that worked** and one clear metric.
2. Campaign-ready code (delegate to `ai-lab:engineer` via a short brief if missing): in the experiment's `src/`, `train.py` = what may change; `evaluate.py` = fixed evaluation that prints `LAB_METRIC <metric>=<value>` via `labkit.report_metric` (so the metric can't be faked from train.py); one run finishes within the trial budget (fixed steps or `labkit.Run(max_minutes=…)`) and fits `lab.config.json → compute.limits`; data from `data/` via `LAB_ROOT`; seed from `labkit.seed_from_env()`.
3. `lab.py campaign init --from <src> --title "<한글 제목>" --slug <slug> --metric <m> --goal min|max --run "uv run python train.py" --eval "uv run python evaluate.py" --editable train.py --protected evaluate.py --trial-minutes <≤7> --max-trials <n> --max-hours <h> --patience <p>` — defaults from `lab.config.json → campaign`.
4. Fill `campaign.md` (Korean): goal chain, allowed kinds of changes, anything forbidden beyond the defaults.
5. Measure the baseline: `lab.py campaign baseline <CMP>` repeatedly until it prints 완료 (each call = one run, Bash timeout 600000). Report the noise and the keep threshold δ.
6. Put the contract to 교수님 — **class C**. Use the AskUserQuestion tool: options `승인하고 바로 시작` / `승인만 (시작은 나중에)` / `예산을 줄여 승인` / `보류`, each with one line (trials × minutes ≈ hours, metric, what may change). On approval: `lab.py campaign approve <CMP> --note "<교수님 말씀 요약>"`; record the decision in the minutes.
7. Start: on `승인하고 바로 시작`, continue with `run` right away in this session. Otherwise tell them both ways to start: now, with `/ai-lab:campaign run <CMP>`; or unattended for hours (away, overnight), with the `/goal` line (see **자리를 비우고 오래 돌리기**).

## run <CMP-id>
Preconditions: approved and baseline done (else explain and stop). If `lab.config.json → git.auto_commit`, commit locally: `git add -A && git commit -m "캠페인 <CMP> 시작"`.
Loop — **do not ask 교수님 anything during the run**: the approved contract is the permission, and 교수님 may be away. If 교수님 speaks up (상황 알려줘, 멈춰), answer or stop as asked:
1. `lab.py campaign status <CMP>`. If it prints `판정: 종료`, go to wrap-up.
2. Launch `ai-lab:explorer` (foreground): `Campaign <CMP>. Batch: <campaign_batch from the profile>. lab.py: python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py". Follow your agent instructions.`
3. Append its report to the current `meetings/session_NNN.md` under `## 캠페인 <CMP>` (create/continue the session as lab-meeting does). Every 3 batches, rewrite the 인계 메모 in `state/lab_state.md` (so an interruption loses nothing).
4. Repeat. Don't stop early because the conversation is long — after a compaction, re-run status and continue.
If something needs a human (environment keeps crashing, the contract looks wrong): `lab.py campaign stop <CMP> --reason "…"`, `lab.py inbox add --from explorer --question "…"`, then wrap up.

Wrap-up (still unattended):
1. `lab.py campaign confirm <CMP>` repeatedly until it prints 완료 (fresh seeds, baseline vs best, CI).
2. `ai-lab:writer` → `summary.md`; `ai-lab:critic` → a REV on the campaign (kept patches, confirmation, gaming check); `lab.py audit <CMP>` must pass.
3. `lab.py inbox add --from lead --question "<CMP> 결과를 결과(F-)로 확정할까요? <한 줄 요약>" --options "확정|잠정으로 두기|추가 확인 실험|기각" --ref <CMP>`.
4. `lab.py report <CMP> --auto` (HTML report: progress chart, kept trials, confirmation). Rewrite `state/lab_state.md` (인계 메모: what ran, the verdict, the ASK id); local git commit `캠페인 <CMP> 종료` if auto_commit.
5. Final message (≤10 lines, Korean): trials run, best vs baseline, confirmation verdict with CI, review verdict, the ASK id, the report path, and what 교수님 should look at first.

## status <CMP-id> / stop <CMP-id>
`lab.py campaign status <CMP>` (or `stop <CMP> --reason "교수님 요청"`) and explain in ≤8 Korean lines. After 교수님 decides on the result, `lab.py campaign close <CMP> --note "<결정>"`.

## 자리를 비우고 오래 돌리기 (e.g. overnight — tell 교수님 this at the end of `plan` unless the run already started)
1. PC가 잠자기 모드로 들어가지 않게 설정 (Windows: 설정 → 시스템 → 전원 → 절전 모드 "안 함").
2. 연구실 폴더에서 새 세션을 열고 아래 한 줄을 붙여 넣는다 (`/goal`은 조건이 충족될 때까지 Claude가 스스로 다음 턴을 이어 가게 하는 기능으로, 사용 한도에 걸리면 풀린 뒤 자동으로 이어 간다):
```
/goal 캠페인 <CMP>를 /ai-lab:campaign run <CMP> 로 끝까지 진행한다. 완료 조건: lab.py campaign status <CMP> 출력에 "판정: 종료"가 있고, 확인 실험이 끝났고, summary.md와 리뷰가 저장되었고, 결정 대기함에 확정 여부 질문이 올라가 있다. 진행 중에는 교수님께 질문하지 않는다.
```
3. 권한 창이 뜨면 돌아올 때까지 멈추므로, 연구실의 `.claude/settings.json` 허용 목록(lab.py, 연구 폴더 편집)이 그대로인지 확인한다. 필요하면 auto 모드로 시작한다.
4. 돌아와서 `/ai-lab:lab-status` → 결정 대기함의 질문에 답한다.
