---
name: release
description: Package accepted research results as markdown-only documents that 교수님 can carry into the company (only .md files can be brought in) — a self-contained report, plus optionally the code packed into a restorable .md.
argument-hint: "<F-/EXP-/H- ids to release> [purpose]"
disable-model-invocation: true
---

# Release — results for use inside the company (markdown files only)

The lab runs outside the company. Only **.md files** can be brought inside, and inside there is no Claude, no git, and no lab tooling. So a release is a small set of markdown documents that stand on their own: they explain the result honestly and, if 교수님 wants, carry the code in a form that can be restored to files. Everything is written in Korean. Tool: `python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py"`.

## 1. Scope — class C, confirm with 교수님 first
1. Resolve the ids in `$ARGUMENTS` with `lab.py context <id>`. Collect findings (F-), their experiments (EXP-), reports, reviews, datasets (DS-), methods (M-), and the code the experiments use (`src/`, imported `labkit` modules).
2. Check before proposing:
   - Findings should be `accepted`. `provisional` or pilot-only results go in only if 교수님 explicitly agrees, and are marked **"미확정"** everywhere.
   - `lab.py audit` PASS for each included experiment or campaign (for a campaign: confirmation on fresh seeds done).
   - Licenses of datasets, pretrained models and copied code (P-/DS-/M- entries): note whether **company use** is allowed. Unknown → flag it.
3. Ask 교수님 and **wait**:
   - what goes in / what is left out, license flags, open caveats;
   - whether to include the **code bundle** (yes/no, and which files).
   - Note that images and model weights cannot travel as .md: key figures become tables, and weights must be re-trained inside with the included code (say how long it took here).

## 2. Build `research/releases/REL-xxx-<slug>/` (`lab.py next release`)

**`REL-xxx-<slug>.md` — the main document** (always). First lines `# REL-xxx: <title>` and `> status: released | tags | session | summary`. Sections:
- `## 한 줄 요약`
- `## 무엇을 주는가` — the method/finding in plain words, and when to use it
- `## 근거` — F-/EXP-/CMP- ids (for traceability), result tables copied exactly from results.json / confirm.json (condition × metric, mean±std, n, 기준선 대비 개선과 95% 신뢰구간), what the review concluded
- `## 적용 범위와 한계` — `scope_limits`, untested conditions, what must NOT be claimed
- `## 사용 방법` — step by step for someone inside the company: restore the code (if bundled), required packages with pinned versions, the command to run, expected output and runtime, hardware used here
- `## 재현 정보` — git commit, seeds, configs (inline, short), environment
- `## 라이선스` — per dataset/model/code, company-use yes/no/unknown
- `## 미확정 항목` — if any
- `## 부록: 핵심 그림을 표로` — the numbers behind each important figure

**`REL-xxx-<slug>-코드.md` — the code bundle** (only if approved):
- Collect exactly the files needed to run: experiment `src/` + the `labkit` modules it imports + configs + a `requirements.txt` written with `uv export --format requirements-txt --no-hashes`. Rewrite imports/paths so the code runs from the bundle root, in a temporary staging folder (not in the lab's own sources).
- Pack: `lab.py pack-md <staging paths> --root <staging> --out research/releases/REL-xxx-<slug>/REL-xxx-<slug>-코드.md --title "REL-xxx 코드 묶음"`. The bundle embeds its own restore script and a sha256 list.
- **Round-trip test (mandatory):** `lab.py unpack-md <bundle> --out <temp dir>`, then in that temp dir `uv venv .rel-venv && uv pip install -r requirements.txt --python .rel-venv`, run the smallest command from `## 사용 방법`, confirm it works, then delete the temp dir.

Never include: `kb/`, `meetings/`, `briefs/`, agent memory, API keys/tokens, `.env`, absolute personal paths, data files.

Before recording: `lab.py audit --report <main .md> --sources <EXP/CMP ids>` must find no unknown numbers.

## 3. Record
- Append to the current `meetings/session_NNN.md` under `## 릴리스`: REL id, included ids, whether code was bundled, 교수님's approval, caveats. The archivist files it.
- Tell 교수님 (≤8 lines): the file paths (these .md files are what to carry in), their sizes, what they contain, license flags, and what must NOT be claimed from them.
