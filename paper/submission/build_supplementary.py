#!/usr/bin/env python3
"""build_supplementary.py — assemble the paper's supplementary artifact layer zip.

Run from anywhere; paths are resolved against the repository root and confined to it.
Output: paper/submission/supplementary_artifact_layer.zip
"""
import sys
import zipfile
from pathlib import Path

_BASE = Path(__file__).resolve().parents[2]
# The canonical run directories live on a Windows junction pointing to the
# run archive outside the repository; resolving follows the junction, so the
# archive root is an explicitly allowlisted confinement root.
_ROOTS = [_BASE.resolve(), Path("D:/codes/idd-run-archive").resolve()]


def safe_path(rel):
    """Resolve rel and confine it to the repo root or the run-archive root."""
    p = (_BASE / rel).resolve()
    if not any(str(p).startswith(str(r) + chr(92)) or p == r for r in _ROOTS):
        raise ValueError("path escapes allowed roots: %s" % p)
    return p


RUN_DIRS = [
    "202609171630389_bench_skab_valve1_1",
    "202609171630579_bench_skab_cavitation_13",
    "202609171631116_bench_skab_normal_control",
    "202609171632332_bench_tep_d01_ac_feed_ratio",
    "202609171632563_bench_tep_d03_hard",
    "202609171633136_bench_tep_d00_normal_control",
    "202609171633340_bench_indpensim_batch093",
    "202609171636045_bench_indpensim_batch001_control",
    "202609171639066_bench_tep_d04_reactor_cooling_step",
    "202609171639214_bench_tep_d07_header_pressure",
    "202609171639527_bench_tep_d11_reactor_cooling_random",
    "202609171640072_bench_tep_d14_reactor_valve_sticking",
    "202609172247007_bench_tep_d11_reactor_cooling_random",
]

BENCH_FILES = [
    "README-artifact-fields.md",
    "rubric.json",
    "metrics.json",
    "baselines.json",
    "baselines_input_audit.json",
    "suite_determinism.json",
    "consistency_audit.json",
    "retest_selection.json",
    "repro_report.json",
    "benchmark_report_en.md",
    "dataset_manifest.json",
    "baseline_pca_rca.json",
    "tier_state.json",
    "report.md",
]

PIPELINE_SCRIPTS = [
    "run-benchmark-pipeline.mjs",
    "run-tier.mjs",
    "judge-rubric.mjs",
    "aggregate.mjs",
    "verify-repro.mjs",
    "select-retest-case.mjs",
    "consistency-audit.mjs",
    "build-english-benchmark-report.mjs",
    "cases/benchmark_cases.json",
]

EXTRA = [
    ("baseline-lab/scripts/verify-fe.mjs", "scripts/verify-fe.mjs"),
    ("paper/supplementary_fe_table1_transcription.md",
     "supplementary_fe_table1_transcription.md"),
]

# Figure sources, released with the paper as claimed in the Fig. 1 / Fig. 2
# captions: the two drawio diagrams plus the HTML/CSS sources of the data
# figures and the render chain that produces the manuscript PNGs from them.
FIGURE_SOURCES = [
    "paper/figures-html/fig_architecture.drawio",
    "paper/figures-html/fig_pipeline.drawio",
    "paper/figures-html/fig_trace.html",
    "paper/figures-html/fig_architecture.html",
    "paper/figures-html/fig_pipeline.html",
    "paper/figures-html/fig_benchmark.html",
    "paper/figures-html/fig_calibration.html",
    "paper/figures-html/fig_casestudy.html",
    "paper/figures-html/fig_tep_perfault.html",
    "paper/figures-html/fig_forest.html",
    "paper/figures-html/fig_suite_matrix.html",
    "paper/figures-html/fig_consistency.html",
    "paper/figures-html/aei_template.css",
    "paper/figures-html/drawio_render.py",
    "paper/figures-html/render_all.sh",
    "paper/figures-html/trim_white.py",
]


def main():
    out = safe_path("paper/submission/supplementary_artifact_layer.zip")
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for rd in RUN_DIRS:
            base = safe_path("workspace/diagnostic-runs/" + rd)
            for p in sorted(base.rglob("*")):
                if p.is_file() and ".mimosa" not in p.parts:
                    z.write(p, "run_dirs/" + rd + "/" + p.relative_to(base).as_posix())
                    n += 1
        for f in BENCH_FILES:
            p = safe_path("results/benchmark/" + f)
            z.write(p, "results_benchmark/" + f)
            n += 1
        for f in PIPELINE_SCRIPTS:
            p = safe_path("scripts/benchmark/" + f)
            z.write(p, "scripts/benchmark/" + f)
            n += 1
        for src, dst in EXTRA:
            p = safe_path(src)
            z.write(p, dst)
            n += 1
        for f in FIGURE_SOURCES:
            p = safe_path(f)
            z.write(p, "figure_sources/" + p.name)
            n += 1
    print("wrote %s (%d files, %.1f MB)" % (out.name, n, out.stat().st_size / 1e6))


if __name__ == "__main__":
    sys.exit(main())
