# ai-lab plugin — development repo

This repo is the reusable *environment* (Claude Code plugin `ai-lab`), not research output. Research happens in separate workspaces created by `/ai-lab:new-lab`; never put research artifacts here. Labs run outside the company only; only markdown files can be carried into the company, so releases (`/ai-lab:release`) are .md documents plus an optional restorable code bundle (`lab.py pack-md`/`unpack-md`). No company data ever enters a lab; the company side is out of scope.

- `.claude-plugin/` plugin.json + marketplace.json (marketplace `ai-sci-cowork`, published at github.com/yhlee52/ai_sci_cowork)
- `agents/` researcher subagents (scout, engineer, explorer, critic, writer, ideator, archivist)
- `skills/` user workflows (lab-meeting [plan|progress|review|journal|retro|1on1], brainstorm, work, campaign, paper, archive, release, lab-status, new-lab)
- `hooks/hooks.json` SessionStart → `scripts/lab.py status --hook` (silent outside a lab)
- `scripts/lab.py` stdlib-only: init, IDs, actions, inbox, status, KB index/find/show/context/history/digest/map/lint, audit, campaign engine, rank, lit, doctor, pack-md
- `templates/workspace/` copied verbatim by `lab.py init` (`{{LAB_NAME}}`, `{{TOPIC}}`, `{{DATE}}` substituted); KB rules in `templates/workspace/kb/README.md`, decision rules and research lifecycle in `templates/workspace/LAB.md`, shared experiment code (Run, results, stats, leakage) in `templates/workspace/labkit/`
- `docs/` 처음_읽는_안내서 (concepts + GitHub workflow), 사용설명서 (usage), 설계_근거 (benchmarks and design principles) — all Korean; keep them in sync when commands or workflows change
- `tests/` + `.github/workflows/tests.yml` — run `python -m unittest discover -s tests` before committing; CI runs Windows/Linux × Python 3.10/3.13

Design principles (see docs/설계_근거.md): the human decides direction, code decides numbers — never let an agent judge its own results (campaign keep/discard, stats and audits are deterministic in lab.py/labkit); every claim traceable to result files and verified citations; honest failure and null results are recorded, with no completion pressure in prompts.

The knowledge base borrows novel_project's canon discipline (one fact → one owning file, state vs. log separation, sharded files, index as cache) for research knowledge — it is not narrative writing.

Conventions: agent/skill instructions are in English (cheaper tokens), but **every output a lab produces is Korean** (records, briefs, plans, reports, KB values, code comments, logs, figure labels, lab.py messages); only identifiers, IDs, JSON keys, status values and tags stay English. Keep always-loaded text (workspace CLAUDE.md, descriptions, lab_state) short — it is paid on every turn. lab.py must stay stdlib-only and Python 3.10-compatible (no backslashes inside f-string expressions). If you add an ID kind, update `KINDS`/`KB_DIRS`/`ARTIFACT_GLOBS`/`ID_RE`/`TYPE_KO` in lab.py and the table in kb/README.md together. Bump `version` in plugin.json when changing behavior.
