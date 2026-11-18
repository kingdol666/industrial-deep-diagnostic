#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_tests.py — E-1H test harness (framework frozen at WS0; cases auto-discovered).

Case contract: each tests/cases/test_*.py exposes CASES = [(name, callable)].
A callable returns a list of (assertion_name, ok: bool, detail: str); any entry
with ok=False fails the case. CLI:

    python run_tests.py                # run all cases
    python run_tests.py ws0 P1         # run cases whose name contains any token (case-insensitive)
    python run_tests.py -v             # print every assertion

Exit 0 iff all assertions pass. Tests generate fixtures on the fly into a temp
dir (fixed seed) — nothing large is committed.
"""
from __future__ import annotations

import importlib.util
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES_DIR = HERE / "cases"
sys.path.insert(0, str(HERE.parent / "scripts"))


def load_cases():
    cases: list[tuple[str, callable]] = []
    for f in sorted(CASES_DIR.glob("test_*.py")):
        spec = importlib.util.spec_from_file_location(f"hetcase_{f.stem}", f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for name, fn in getattr(mod, "CASES", []):
            cases.append((name, fn))
    return cases


def main() -> int:
    argv = [a for a in sys.argv[1:]]
    verbose = "-v" in argv
    tokens = [a.lower() for a in argv if not a.startswith("-")]
    cases = load_cases()
    if tokens:
        cases = [(n, f) for n, f in cases if any(t in n.lower() for t in tokens)]
    if not cases:
        print("no test cases matched")
        return 2
    failures: list[str] = []
    total = 0
    for name, fn in cases:
        try:
            results = fn()
        except Exception:
            failures.append(f"{name}: EXCEPTION\n{traceback.format_exc()}")
            print(f"[FAIL] {name} (exception)")
            continue
        bad = [(a, d) for a, ok, d in results if not ok]
        total += len(results)
        if verbose:
            for a, ok, d in results:
                print(f"  {'ok  ' if ok else 'FAIL'} {name}::{a} {d if not ok else ''}")
        if bad:
            failures.append(f"{name}: " + "; ".join(f"{a} — {detail}" for a, detail in bad))
            print(f"[FAIL] {name} ({len(bad)}/{len(results)} assertions failed)")
        else:
            print(f"[PASS] {name} ({len(results)} assertions)")
    print(f"\n{len(cases)} case(s), {total} assertion(s), {len(failures)} failure(s)")
    for f in failures:
        print("----\n" + f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
