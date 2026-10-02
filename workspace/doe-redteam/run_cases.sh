#!/usr/bin/env bash
# Run every redteam case through analyze.py all; record exit code + tail + wall time.
cd "D:\codes\myskills\industrial-deep-diagnostic" || exit 1
PY() { uv run --project .claude/shared/scripts python "$@"; }
mkdir -p workspace/doe-redteam/_results
for case in workspace/doe-redteam/*/; do
  name=$(basename "$case")
  [ "$name" = "_results" ] && continue
  [ -d "$case/run" ] || continue
  start=$(date +%s.%N)
  PY .claude/skills/industrial-doe-analyzer/scripts/analyze.py all \
     --run-dir "workspace/doe-redteam/$name/run" \
     > "workspace/doe-redteam/_results/$name.out" 2> "workspace/doe-redteam/_results/$name.err"
  rc=$?
  end=$(date +%s.%N)
  dur=$(echo "$end $start" | awk '{printf "%.1f", $1-$2}')
  echo "$name rc=$rc time=${dur}s" | tee -a workspace/doe-redteam/_results/summary.txt
done
