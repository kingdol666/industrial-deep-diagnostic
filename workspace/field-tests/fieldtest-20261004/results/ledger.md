# results/ledger.md — 全局命令台账（fieldtest-20261004）

Tester: blind execution of T1-T5 against real skill CLIs. Python = shared venv, Node = plain node.
Per-case detail: results/T*/commands.log. Conclusions: results/T1_result.md ... T5_result.md.
truth/ was never read. No LLM engine spawns. No writes outside results/ (cases/ untouched).

| case | step | command (short) | exit | 1-line observation |
|---|---|---|---|---|
| setup | 1 | mkdir -p results/T1..T5 | 0 | dirs created |
| T1 | 2 | data_preprocessor.py --data-path cases/T1.../inbox --output results/T1 --name fieldtest_T1 | 0 | tables_found=8, selected=sensor_log.csv 301×7, warning at data_preprocessor.py:425 |
| T1 | 3 | node -e dump preprocessing_report.json | 0 | 8 tables, merge=outer on timestamp, merged 4 files, missing 27.41% |
| T1 | 4 | head/file source files | 0 | GBK + semicolon + TAB confirmed |
| T1 | 5 | qa_audit.py (pandas per-file) | 1 | crashed at pd.read_html: venv lacks lxml (preprocessor itself unaffected, uses regex extractor at :372); dup timestamp sensor_log L152/302, B0058 moisture null, qa_lab 3 nulls, dcs outliers 999.9/-3.2 |
| T1 | 6 | qa_audit_part2.py (stdlib HTML parser) | 0 | html/md clean; unified view: dcs cols 181/301, process 201/301, batch 120/301, sensor 301/301 |
| T1 | 7 | grep/md checks + dup scan | 0 | unified view keeps duplicate 10:30:00 rows (L152/153); 999.9 and -3.2 pass through unflagged |
| T2 | 1 | build_baseline.py --history-csv history.csv --doe-run-dir doe_prior --out results/T2/baseline/watch_baseline.json | 0 | groups __ALL__; DOE window speed_rpm [1225,1275] registered field-by-field |
| T2 | 2 | sentinel_fast.py window_normal.csv (state/out in screen_normal/) | 0 | status=ok alerts=0, ring=240/300 |
| T2 | 3 | sentinel_fast.py window_drift.csv (screen_drift/) | 1 | status=alert alerts=7 (all speed_rpm: ROBUST_Z_OUTLIER×2, NELSON_R1×2, R5, R6 high; R2 warn) |
| T2 | 4 | sentinel.py watch --data window_changepoint.csv --out-dir watch_changepoint | 1 | alerts=3: ROBUST_Z_OUTLIER temp_c high n=113; REGIME_CHANGE_NEW cp_position=121; VARIANCE_RATIO_HIGH ratio=34.7975; projection speed_rpm info hours_to_edge 5228 |
| T2 | 5 | sentinel.py watch --data window_drift.csv --out-dir watch_drift | 1 | alerts=9: + WINDOW_DRIFT_PROJECTION high slope 3.6058/h hours_to_edge 3.4439 up; VARIANCE_RATIO_HIGH 11.937; projection level=high |
| T2 | 6 | sentinel_fast.py window_orphan.csv --baseline <nonexistent> | 2 | "no baseline (...) — refusing to run (exit 2)", no alert file; contract per sentinel_fast.py L15-21 + SKILL.md |
| T2 | 7 | quality_gate.mjs ×2 (changepoint, drift) | 0, 0 | 6/6 ALL PASS each |
| T3 | 1 | mkdir RUN_DIR + cp inputs + seed jsonl | 0 | results/T3/run/{00_input,06_experience} ready |
| T3 | 2 | tune_stats.py attribute --metric yield_pct --time-col t --settle-steps 30 | 0 | 2 estimable E1 + 1 not_estimable E0 min_points ("honest nulls") |
| T3 | 3 | experience_build.mjs build --run-dir results/T3/run | 0 | created ×2, SKIP not_estimable (admission rule), store=4 entries |
| T3 | 4 | match_playbook.mjs recommend --signature 00_input/fault_signature.json | 0 | playbook_hit @regime, match_score=1, hit seed recipe 2adda6ae, grade E1 corr 1/ref 0 |
| T3 | 5 | experience_build.mjs feedback --chunk-id ...2adda6ae --result effective | 0 | corroboration=2 refutation=0 grade=E2 label=verified |
| T3 | 6 | re-run recommend | 0 | refreshed: grade E2 corroboration 2 consistent with store |
| T3 | 7 | quality_gate.mjs results/T3/run | 0 | 8/8 ALL PASS (T1-T8) |
| T4 | 1 | optimizer.py init --run-dir results/T4/campaign --objective objective.json | 0 | campaign OPT-20261004-001, seed 42 |
| T4 | 2 | design (R1) → plant_sim → ingest | 0,0,0 | R001 lhs_fill 8 trials; exploring→exploiting; max_EI=0.0101 |
| T4 | 3 | design (R2) → plant_sim → ingest | 0,0,0 | R002 rsm_augment 8 trials; exploiting→confirming; max_EI=1.63e-06 < eps 0.003191 |
| T4 | 4 | design (R3) → plant_sim → ingest | 0,0,0 | R003 confirm_replicates 1×3 @ incumbent; confirming→converged (dual gate satisfied); 3/6 rounds, 17/24 trials |
| T4 | 5 | optimizer.py converge | 0 | optimization_conclusion.json + recipe.json + report.md + 2 experience files |
| T4 | 6 | node read conclusion/recipe | 0 | dual_gate all true, D=1=D_max; final_setpoints T=72.039091 C=0.28382; confirm mean 0.4607 sd 0.0201 n=3 |
| T4 | 7 | optimizer_gate.mjs results/T4/campaign | 0 | 16/16 ALL PASS |
| T5 | 1 | mkdir RUN_DIR/00_input + cp doe_table.csv analysis_context.json | 0 | ready |
| T5 | 2 | analyze.py all --run-dir results/T5/run | 0 | rows=12 design=full_factorial center_points=4; windows=2 plots=4; grade=A; report.html 99897 bytes |
| T5 | 3 | node read profile/effect/model/recommendations | 0 | significant q<0.05: ET +4.059375 (q=6.44e-5), DR -3.220625 (q=8.09e-5), ET:DR +1.741625 (q=6.11e-4); OW-001 DR [2,3.75], OW-002 ET [185,195]; setpoints ET=195 DR=2 CR=25 D=1 |
| T5 | 4 | grep unestimated terms | 0 | model_spec declares 10 terms, 7 estimated; 3 missing without reason_code (rough edge) |
| T5 | 5 | quality_gate.mjs results/T5/run | 0 | 21/21 ALL PASS |

All per-case exits are also in results/T*/commands.log. Total: 0 unexplained failures;
1 expected environment failure (T1 pandas read_html needs lxml, absent in venv — worked around
with stdlib HTMLParser inside results/T1/, skill itself unaffected).
