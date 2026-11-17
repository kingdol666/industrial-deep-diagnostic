# AC.md — industrial-html-visualizer (Step 8 page gate)

> Gate: `scripts/quality_gate.mjs` (additive; does not replace CP-8A/8B/8C or the reviewer).
> Entry point (shared venv or any python3):
> `.claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-html-visualizer/tests/run_tests.py`
> Fixtures are generated on the fly in a temp dir — nothing committed.

| AC | Assertion | Command | Evidence |
|----|-----------|---------|----------|
| AC1 | Valid page (`diagnostic-report.html` ≥5120B, `<title>`, html/head/body, balanced tags) → exit 0, verdict `ok` with byte count + title | `run_tests.py valid` | 2/2 assertions PASS |
| AC2 | Page absent → exit 2 `undetermined` (Step 8 has not run) | `run_tests.py absent` | 2/2 assertions PASS |
| AC3 | Corrupt page → exit 3 `gate_fail`: no title, truncated <5120B, unbalanced `<script>` tags | `run_tests.py corrupt` | 3/3 assertions PASS |
| AC4 | Bad invocation (no `--run-dir`/`--html`) → exit 1 `hard_error` | `run_tests.py hard_error` | 1/1 assertion PASS |
| AC5 | Full battery | `run_tests.py` | `[TESTS] 8/8 passed — ALL GREEN` |

Exit-code contract: `0 ok | 1 hard error | 2 undetermined (artifact absent) | 3 gate-fail`.
