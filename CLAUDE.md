# ai-lab plugin — development repo

This repo is the reusable *environment* (Claude Code plugin `ai-lab`), not research output. Research happens in separate workspaces created by `/ai-lab:new-lab`; never put research artifacts here. Labs run outside the company only; the company consumes offline releases (`/ai-lab:release`), so no company data ever enters a lab.

- `.claude-plugin/` plugin.json + marketplace.json (marketplace `ai-sci-cowork`, published at github.com/yhlee52/ai_sci_cowork)
- `agents/` researcher subagents (scout, engineer, critic, writer, ideator, archivist)
- `skills/` user workflows (lab-meeting [plan|progress|review|journal|retro|1on1], brainstorm, work, archive, release, lab-status, new-lab)
- `hooks/hooks.json` SessionStart → `scripts/lab.py status --hook` (silent outside a lab)
- `scripts/lab.py` stdlib-only: init, IDs, actions, inbox, status, KB index/find/show/context/history/digest, experiment verify
- `docs/처음_읽는_안내서.md` (concepts for AI-agent beginners + GitHub workflow) and `docs/사용설명서.md` (usage guide), both Korean — keep it in sync when commands or workflows change
- `templates/workspace/` copied verbatim by `lab.py init` (`{{LAB_NAME}}`, `{{TOPIC}}`, `{{DATE}}` substituted); KB rules in `templates/workspace/kb/README.md`, decision rules in `templates/workspace/LAB.md`, shared experiment code in `templates/workspace/labkit/`

The knowledge base borrows novel_project's canon discipline (one fact → one owning file, state vs. log separation, sharded files, index as cache) for research knowledge — it is not narrative writing.

Conventions: agent/skill instructions are in English (cheaper tokens), but **every output a lab produces is Korean** (records, briefs, plans, reports, KB values, code comments, logs, figure labels, lab.py messages); only identifiers, IDs, JSON keys, status values and tags stay English. Keep always-loaded text (workspace CLAUDE.md, descriptions, lab_state) short — it is paid on every turn. If you add an ID kind, update `KINDS`/`KB_DIRS`/`ID_RE` in lab.py and the table in kb/README.md together. Bump `version` in plugin.json when changing behavior.
