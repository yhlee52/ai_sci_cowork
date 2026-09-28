---
name: release
description: Package accepted research results (findings, code, reports) into a self-contained release that 교수님 can carry into an offline company network and use without Claude, the internet, or the lab's tooling.
argument-hint: "<F-/EXP-/H- ids to release> [purpose]"
disable-model-invocation: true
---

# Release — results for use inside the company

The lab runs outside; inside the company only releases are used. A release must work **offline, without Claude and without this workspace**, and must say honestly what it does and does not show. Tool: `python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py"`.

## 1. Scope — class C, confirm with 교수님 first
1. Resolve the ids in `$ARGUMENTS` with `lab.py context <id>`. Collect: findings (F-), their experiments (EXP-), reports, the code paths (`src/`, the `labkit` modules they import), datasets (DS-) and methods (M-).
2. Check before proposing:
   - Findings should be `accepted`. `provisional` or pilot-only results may go only if 교수님 explicitly agrees, and are labelled **"미확정"** everywhere in the release.
   - `lab.py verify` PASS for each included experiment.
   - Licenses: for every dataset, pretrained model, and copied code (P-/DS-/M- entries, their URLs), note the license and whether **commercial/company use** is allowed. Unknown = flag it.
3. Show 교수님 a short list: what goes in (code, report, figures, config, optional weights with size), what is excluded, license flags, open caveats. **Wait for approval.**

## 2. Build `research/releases/REL-xxx-<slug>/` (`lab.py next release`)
```
README.md          (Korean) — first lines: `# REL-xxx: <title>` and `> status: released | tags | session | summary`
                   sections: 무엇을 주는가 · 근거 (F-/EXP- ids, 결과 표 mean±std, n) · 적용 범위와 한계 (scope_limits, 검증하지 않은 조건)
                   · 사용법 (offline install, run commands, expected output) · 재현 정보 (git commit, seeds, env, GPU) · 라이선스 · 미확정 항목
code/              only what is needed: experiment src + the labkit modules it imports (copied, so it runs standalone)
configs/           the configs that produced the reported numbers
results/           results.json, report.md, figures/
requirements.txt   `uv export --format requirements-txt --no-hashes > requirements.txt` (pinned versions)
weights/           only if approved (large files are delivered separately; list sha256 in README)
MANIFEST.txt       every file with sha256 (generate with a short python script)
```
- All release text is Korean (README, comments, messages). Rewrite imports/paths so `code/` runs from the release root; do a clean-room test in a fresh venv with only `requirements.txt` (`uv venv .rel-venv && uv pip install -r requirements.txt --python .rel-venv`), run the smallest command from 사용법, then delete the venv.
- Offline install note in README: on an internet-connected machine run `pip download -r requirements.txt -d wheels/`, carry `wheels/` in, then `pip install --no-index --find-links wheels/ -r requirements.txt` (CUDA torch wheels: from the PyTorch index matching the company GPU/driver).
- Never include: `kb/`, `meetings/`, `briefs/`, agent memory, API keys/tokens, `.env`, absolute personal paths.

## 3. Record
- Zip it (`REL-xxx-<slug>.zip` next to the folder; zips and weights stay out of git — add to `.gitignore` if needed).
- Append a line to the current `meetings/session_NNN.md` under `## 릴리스`: REL id, included ids, 교수님's approval, caveats. The archivist files it.
- Tell 교수님 (Korean, ≤8 lines): path, size, what it contains, license flags, and what must NOT be claimed from it.
