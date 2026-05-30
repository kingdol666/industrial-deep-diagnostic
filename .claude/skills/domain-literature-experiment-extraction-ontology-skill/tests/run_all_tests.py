#!/usr/bin/env python3
"""
Run all tests for the domain-literature-experiment-extraction-ontology-skill.
"""

import subprocess
import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = TEST_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))


def run_test(module_name: str) -> bool:
    test_path = TEST_DIR / f"{module_name}.py"
    print(f"\n{'=' * 60}")
    print(f"Running: {module_name}")
    print(f"{'=' * 60}")
    try:
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=False,
            cwd=str(TEST_DIR),
        )
        return result.returncode == 0
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def main():
    tests = [
        "test_schemas",
        "test_normalizer",
        "test_ontology",
    ]

    results = {}
    for test_name in tests:
        results[test_name] = run_test(test_name)

    print(f"\n{'=' * 60}")
    print("Test Summary")
    print(f"{'=' * 60}")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  {name}: {status}")

    print(f"\n{passed}/{total} test suites passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())