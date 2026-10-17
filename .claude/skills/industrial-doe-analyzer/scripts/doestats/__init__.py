"""doestats — deterministic statistics core of industrial-doe-analyzer.

Every number the skill publishes is computed here with numpy/scipy only.
LLM agents interpret; they never compute. (plan: industrial-doe-analyzer-skill-v1.md)

1.1.0 — downstream contract v1.1: four distinct interval types, marginal windows
demoted to diagnostics, constraint-aware joint setpoints, factor x response matrix.
"""

VERSION = "1.1.0"
