# AC.md — industrial-html-reviewer (Step 8.5 review-artifact gate)

> Gate: `scripts/quality_gate.mjs` (structural validity of `05_review/html_review.json`; deeper schema
> validation remains `validate.mjs` with `schemas/html_review_schema.json`).
> Entry point: `.claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-html-reviewer/tests/run_tests.py`
> Fixtures are generated on the fly in a temp dir — nothing committed.
> Verdict semantics: the review verdict VALUE (pass/warn/fail) is a legitimate outcome and does not gate;
> the gate fails on structurally invalid or self-contradictory artifacts only.

| AC | Assertion | Command | Evidence |
|----|-----------|---------|----------|
| AC1 | Valid artifact (pass and warn verdicts) → exit 0; reports verdict/score/check count | `run_tests.py valid` | 3/3 assertions PASS |
| AC2 | Artifact absent → exit 2 `undetermined` | `run_tests.py absent` | 1/1 assertion PASS |
| AC3 | Corrupt → exit 3: unparseable JSON (R1), missing required fields (R2), bad verdict enum (R3), `blocking_issues` objects (R5), check name outside schema enum (R6), pass-with-blockers (R7) | `run_tests.py corrupt` | 6/6 assertions PASS |
| AC4 | Gate enum/required agree with `schemas/html_review_schema.json` (no drift) | `run_tests.py schema_agreement` | 2/2 assertions PASS |
| AC5 | Full battery | `run_tests.py` | `[TESTS] 12/12 passed — ALL GREEN` |

Exit-code contract: `0 ok | 1 hard error | 2 undetermined (artifact absent) | 3 gate-fail`.
