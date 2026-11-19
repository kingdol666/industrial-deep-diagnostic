#!/usr/bin/env python
"""run_segment_selector.py — defect-workaround runner for segment_selector.py.

DEFECT RECORDED (not fixed — .claude/ sources must not be edited):
  segment_selector.py cmd_select (L282) calls pd.to_numeric but the module only
  imports pandas INSIDE _load_dataframe (function-local), so the standalone
  `select` CLI dies with NameError: name 'pd' is not defined for any metric.
  tune_stats.py is unaffected (it imports pandas locally inside attribute()).

This runner injects pandas into the module namespace at runtime (numerics and
logic untouched) and then invokes the script's own argparse/CLI verbatim.
"""

import sys
from pathlib import Path

import pandas as pd  # noqa: F401  — supplied to segment_selector's namespace

SKILL_SCRIPTS = Path(r"D:\codes\myskills\idd-doe-impl\.claude\skills"
                     r"\industrial-tuning-memory\scripts")
sys.path.insert(0, str(SKILL_SCRIPTS))

import segment_selector as ss  # noqa: E402

ss.pd = pd  # the missing module-global import (workaround, no source edit)

if __name__ == "__main__":
    sys.argv = ["segment_selector.py"] + sys.argv[1:]
    args = ss.build_parser().parse_args()
    if args.cmd == "select":
        sys.exit(ss.cmd_select(args))
    sys.exit(2)
