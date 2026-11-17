# AC.md — industrial-enhanced-html-reviewer (enhanced review gate)

> Gate: `scripts/quality_gate.mjs` — runs `scripts/html_reviewer.py` (byte-identical, not modified) on
> `<run>/enhancement/{enhanced_knowledge.json, enhanced-analysis.html}` and maps its verdict.
> Entry point: `.claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-enhanced-html-reviewer/tests/run_tests.py`
> Fixtures are generated on the fly in a temp dir — nothing committed.
> Verdict mapping: `pass` → exit 0; `warn` → exit 3 (fix and re-review) unless `--allow-warn`;
> `fail` → exit 3; missing inputs → exit 2; python/script failure → exit 1.

| AC | Assertion | Command | Evidence |
|----|-----------|---------|----------|
| AC1 | End-to-end: real builder artifacts → gate runs the reviewer → verdict `pass` → exit 0, review artifact written | `run_tests.py e2e_pass` | 4/4 assertions PASS |
| AC2 | Required input artifact absent → exit 2 `undetermined` | `run_tests.py absent` | 2/2 assertions PASS |
| AC3 | Corrupt page (truncated) → reviewer verdict `fail` → exit 3 with blocking issues reported | `run_tests.py corrupt` | 2/2 assertions PASS |
| AC4 | `warn` verdict → exit 3 by default, exit 0 with `--allow-warn` (informational) | `run_tests.py warn` | 2/2 assertions PASS |
| AC5 | `--no-run` consumes an existing review JSON; missing artifact → exit 2 | `run_tests.py no_run` | 2/2 assertions PASS |
| AC6 | Full battery | `run_tests.py` | `[TESTS] 12/12 passed — ALL GREEN` |

Exit-code contract: `0 ok | 1 hard error | 2 undetermined (artifact absent) | 3 gate-fail`.
