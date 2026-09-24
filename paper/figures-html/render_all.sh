#!/usr/bin/env bash
# render_all.sh — render every paper figure HTML/drawio to PNG (3x, then trim)
set -e
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
FIGS="D:/codes/myskills/industrial-deep-diagnostic/paper/figures"
HTML="D:/codes/myskills/industrial-deep-diagnostic/paper/figures-html"
shot () { # name w h
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=3 \
    --window-size=$2,$3 \
    --screenshot="$FIGS\\$1.png" "file:///$HTML/$1.html" 2>&1 | tail -1
}
# data figures (html)
shot fig_benchmark    1500 1120
shot fig_calibration  1500 990
shot fig_forest       1500 780
shot fig_tep_perfault 1240 1360
shot fig_suite_matrix 1500 1030
shot fig_consistency  1500 1330
shot fig_casestudy    1240 1360
shot fig_trace        1500 2050
# drawio-derived (svg wrappers)
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=3 \
  --window-size=1500,700  --screenshot="$FIGS\\fig_pipeline.png" "file:///$HTML/fig_pipeline_svg.html" 2>&1 | tail -1
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=3 \
  --window-size=1500,1980 --screenshot="$FIGS\\fig_architecture.png" "file:///$HTML/fig_architecture_svg.html" 2>&1 | tail -1
cd "$HTML" && python trim_white.py "$FIGS/fig_benchmark.png" "$FIGS/fig_calibration.png" \
  "$FIGS/fig_forest.png" "$FIGS/fig_tep_perfault.png" "$FIGS/fig_suite_matrix.png" \
  "$FIGS/fig_consistency.png" "$FIGS/fig_casestudy.png" "$FIGS/fig_trace.png" \
  "$FIGS/fig_pipeline.png" "$FIGS/fig_architecture.png"
