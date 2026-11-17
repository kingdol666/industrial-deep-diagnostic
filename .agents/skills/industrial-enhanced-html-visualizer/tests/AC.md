# AC.md — industrial-enhanced-html-visualizer (enhanced build gate)

> Gate: `scripts/quality_gate.mjs` — validates `<run>/enhancement/enhanced-analysis.html` PLUS the
> `html_selfcheck.json` builder marker written by `scripts/html_builder.py` (byte-identical, not modified).
> Entry point: `.claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-enhanced-html-visualizer/tests/run_tests.py`
> Fixtures are generated on the fly in a temp dir — nothing committed; the marker fixture mirrors
> `generate_selfcheck()` exactly, and the roundtrip case rebuilds via the real builder.

| AC | Assertion | Command | Evidence |
|----|-----------|---------|----------|
| AC1 | Valid page + marker → exit 0; real-builder roundtrip page also exit 0 | `run_tests.py valid` | 3/3 assertions PASS |
| AC2 | Page or marker absent → exit 2 `undetermined` | `run_tests.py absent` | 2/2 assertions PASS |
| AC3 | Corrupt → exit 3: unparseable marker (E3), wrong builder identity (E4), false marker claims (E5), single CDN source (E6), missing chart containers / fallback wiring (E7), undersized page (E2) | `run_tests.py corrupt` | 6/6 assertions PASS |
| AC4 | Full battery | `run_tests.py` | `[TESTS] 11/11 passed — ALL GREEN` |

Exit-code contract: `0 ok | 1 hard error | 2 undetermined (artifact absent) | 3 gate-fail`.
