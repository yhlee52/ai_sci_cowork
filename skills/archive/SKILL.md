---
name: archive
description: Close the current (or given) ai-lab session — the archivist files it into the knowledge base, the digest is regenerated, and the handoff note and cycle progress are updated.
argument-hint: "[session NNN]"
disable-model-invocation: true
---

# Archive a session

1. Session: first 3-digit number in `$ARGUMENTS`, else the newest `meetings/session_*.md` without an `archived:` line. If none, say there is nothing to archive and stop.
2. Launch `ai-lab:archivist` (foreground) with only: `Session NNN. lab.py: python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py". Follow your agent instructions.`
3. Add `archived: <YYYY-MM-DD>` as the second line of `meetings/session_NNN.md`.
4. Rewrite `state/lab_state.md` (≤40 lines) with the **인계 메모** for the next session: what was in progress, what is blocked (ASK ids), the very next command.
5. Add one line under `state/cycle.md` `## 진행`: `session NNN — <what advanced>`. If `lab.py status` shows the cycle is due (`→ retro due`), tell 교수님 the next meeting should be `/ai-lab:lab-meeting retro`.
6. Relay the archivist's report (≤8 lines) and any open ASK items.
