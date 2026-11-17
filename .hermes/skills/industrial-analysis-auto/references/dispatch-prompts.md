# Dispatch Prompt Templates (moved verbatim from SKILL.md §Dispatch)

> Read in full before any `Agent(...)` dispatch. The four audit lines every dispatch prompt must carry
> (HARD_BUDGET / MODE / SINGLE_READ / REUSE_MANDATE) and the skipped-stage event rule stay in `SKILL.md` §Dispatch.

```javascript
// Step 2+2.5: Ontology Builder
Agent({
  subagent_type: "context-builder",
  prompt: `DATA_PATH=<data-path>
RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-ontology-builder>
SHARED_PATH=<path-to-.claude/shared>
INTERACTION_MODE=auto

Read skill://industrial-ontology-builder and execute the ontology construction protocol.
`
})

// Step 3+3.3: Data Processor
Agent({
  subagent_type: "data-processor",
  prompt: `DATA_PATH=<data-path>
RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-data-processor>
SHARED_PATH=<path-to-.claude/shared>

Read skill://industrial-data-processor and execute. ontology_first — read ontology before any statistical work.
`
})

// Step 4: Diagnostician
Agent({
  subagent_type: "diagnostician",
  prompt: `DATA_PATH=<data-path>
RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-diagnostician>
SHARED_PATH=<path-to-.claude/shared>

Read skill://industrial-diagnostician and execute. Fuses data + ontology + physics + VLM + time-lag.
For repair loops, pass REPAIR_INSTRUCTIONS=<instructions>.
`
})

// Step 5a: Judge + Step 5b: Physical Auditor (parallel)
Agent({
  subagent_type: "judge",
  prompt: `RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-judge>
SHARED_PATH=<path-to-.claude/shared>

Read skill://industrial-judge and execute. 10-item quality gate → judge_feedback.json.
`
})
Agent({
  subagent_type: "report-reviewer",
  prompt: `RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-physical-auditor>
SHARED_PATH=<path-to-.claude/shared>
PRE_REPORT_AUDIT=true

Read skill://industrial-physical-auditor and execute pre-report audit.
`
})

// Step 6: Reporter
Agent({
  subagent_type: "reporter",
  prompt: `RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-reporter>
SHARED_PATH=<path-to-.claude/shared>

Read skill://industrial-reporter and execute. Judge-gated.
`
})

// Step 7: Physical Auditor (Final)
Agent({
  subagent_type: "report-reviewer",
  prompt: `RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-physical-auditor>
SHARED_PATH=<path-to-.claude/shared>

Read skill://industrial-physical-auditor (final mode). Audit report.md → optimizer.md.
`
})

// Step 8: HTML Visualizer (AUTO)
Agent({
  subagent_type: "html-visualizer",
  prompt: `RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-html-visualizer>
SHARED_PATH=<path-to-.claude/shared>

Read skill://industrial-html-visualizer and execute. Non-interactive — after CP-8 ENDORSED, immediately launch.
`
})

// Step 8.5: HTML Reviewer
Agent({
  subagent_type: "html-reviewer",
  prompt: `RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-html-reviewer>
SHARED_PATH=<path-to-.claude/shared>

Read skill://industrial-html-reviewer and execute. Review → pass/needs_revision.
`
})
```