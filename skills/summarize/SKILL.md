---
name: summarize
description: Summaries in an ai-lab workspace by the 요약 연구원 — deep-read external papers (one summarizer per paper, in parallel), a one-page brief of the lab's own experiments, campaigns, sessions or the current cycle for 교수님, or an independent reverse read of a draft. Numbers come from their sources only.
argument-hint: "<P-/arXiv ids | EXP-/CMP-/F- ids | session NNN | cycle | path.md> [독자: 교수님|회의|회사]"
---

# Summarize

Tool: `python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py"`. The 요약 연구원 (`ai-lab:summarizer`) does the reading; you only route and relay.

1. Parse `$ARGUMENTS` into targets and an audience (default 교수님). Mode per target:
   - `P-xxx`, an arXiv id or a DOI → `paper` (one subagent **per paper**);
   - `EXP-`/`CMP-`/`F-`/`REV-` ids, `session NNN`, `cycle` → `brief` (one subagent for all of them together — it is one brief);
   - a `.md` path (draft, release, report) → `reverse`.
   If a target already has a SUM (`lab.py find <id> --type summary`) and its source hasn't changed since, show that one instead of re-summarizing.
2. For each subagent: `lab.py next summary` → `SUM-xxx`. Prompt: `Mode <mode>. Target <ids or path>. Audience <독자>. Output SUM-xxx (research/summaries/SUM-xxx-<slug>.md). Session NNN. lab.py: python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py". Follow your agent instructions.` Launch all of them **in one message** (parallel), at most `max_parallel_agents` at a time from the budget profile.
3. Relay each one-line summary and its path (≤10 lines total). Don't paste the files. Append `## 요약` (one line per SUM id) to the current `meetings/session_NNN.md` if a session is open, so the archivist links it.
