---
name: archive
description: Close the current (or given) ai-lab session — the archivist files it into the knowledge base (incl. null results and campaign lessons), the digest and research map are regenerated, the lab is checked for consistency, the handoff note and cycle progress are updated, and the session is committed to the lab's git history.
argument-hint: "[session NNN]"
disable-model-invocation: true
---

# Archive a session

Like a shift handover: the next session starts with no memory, so everything it needs must be in files, and the lab must be left in a clean, committed state.

1. Session: first 3-digit number in `$ARGUMENTS`, else the newest `meetings/session_*.md` without an `archived:` line. If none, say there is nothing to archive and stop.
2. Launch `ai-lab:archivist` (foreground) with only: `Session NNN. lab.py: python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py". Follow your agent instructions.`
3. Add `archived: <YYYY-MM-DD>` as the second line of `meetings/session_NNN.md`.
4. Rewrite `state/lab_state.md` (≤40 lines) with the **인계 메모** for the next session: what was in progress (incl. running campaigns), what is blocked (ASK ids), the very next command.
5. Add one line under `state/cycle.md` `## 진행`: `session NNN — <what advanced>`. If `lab.py status` shows the cycle is due (`→ 회고할 때입니다`), tell 교수님 the next meeting should be `/ai-lab:lab-meeting retro`.
6. `lab.py lint` — anything 실패 must be fixed now (or reported to 교수님 if it needs a decision).
7. If `lab.config.json → git.auto_commit` is true: `git add -A` then `git commit -m "세션 NNN 정리: <세션 제목>"` (local only; push only when 교수님 asks). Large artifacts are already excluded by `.gitignore`.
8. Relay the archivist's report (≤8 lines), the lint summary, the commit id, and any open ASK items.
