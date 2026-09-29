---
name: new-lab
description: Create a new, separate ai-lab research workspace (its own folder/git repo) from the plugin template.
argument-hint: "<path> [research topic]"
disable-model-invocation: true
---

# Create a research workspace

1. Parse `$ARGUMENTS`: first token = target path (required; ask if missing), the rest = research topic (optional).
2. Run: `python "${CLAUDE_PLUGIN_ROOT}/scripts/lab.py" init "<path>" --topic "<topic>" --git`
   (`--name` defaults to the folder name.) If it fails because the folder isn't empty, report and stop — never delete anything.
3. Tell 교수님 in Korean:
   - where the lab was created,
   - the hardware line `lab.py init` printed: it detected this PC and set the lab's constraints automatically (re-detected when the lab is opened on another PC; 교수님 can narrow them in `lab.config.json → compute.overrides`),
   - to open that folder as the working directory in a new Claude Code session and accept the workspace trust prompt (the session hook then loads the lab state, and `lab.py` lookups run without permission prompts),
   - the Python/torch environment is set up by 강태오 (engineer) on the first experiment, so nothing to install now (`lab.py doctor` shows what is ready),
   - first step: `/ai-lab:lab-meeting plan 연구 주제와 첫 마일스톤 정하기` (the first cycle-planning meeting fills ROADMAP.md and state/cycle.md with 교수님).
