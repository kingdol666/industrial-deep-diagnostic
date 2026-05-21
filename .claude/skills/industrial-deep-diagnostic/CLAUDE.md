# CLAUDE.md — Industrial Deep Diagnostic Skill

## Project Overview

This is a Claude Code Skill for industrial time-series analysis and diagnostic. It lives in `.claude/skills/industrial-deep-diagnostic/`.

## Architecture

The Skill is prompt-driven. Each analysis step is guided by a dedicated prompt file in `prompts/`. The main orchestration logic is in `SKILL.md`. Python scripts in `scripts/` are optional utilities — the Skill can operate purely through Claude's native capabilities (Bash, Read, Write, Agent, etc.).

## Key Conventions

- **Evidence hierarchy**: Always rank evidence by reliability (see SKILL.md). Direct data > user docs > statistics > charts > process logic > web references > hypotheses.
- **Anti-speculation**: Never state unsupported causal claims. Use observation/inference/hypothesis language templates.
- **Judge review**: Every analysis must pass judge verification (score >= 90) before finalizing.
- **Persistence**: All outputs go to `~/.claude/industrial-deep-diagnostic/runs/<timestamp>_<batch_id>/`.

## File Organization

```
SKILL.md              — Skill definition, workflow, commands
CLAUDE.md             — This file: project instructions
README.md             — User-facing documentation
prompts/              — Agent prompts (intake, reference, research, ontology, etc.)
schemas/              — JSON schemas for ontology, signals, analysis, etc.
templates/            — Report and output templates
scripts/              — Python helper utilities
resources/            — Reference rules and guides
examples/             — Example scenarios and sample configs
tests/                — Validation fixtures and checklists
```

## Development Notes

- Prompts are Markdown files loaded as instructions for each agent step
- Schemas use JSON Schema draft-07 for validation
- Scripts use Python 3.10+ with pandas, matplotlib, scipy
- All generated code must handle missing dependencies gracefully
- Test fixtures should be small synthetic datasets for validation
