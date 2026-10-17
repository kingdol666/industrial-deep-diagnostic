#!/usr/bin/env python
"""aws_capture.py tests — AgentWorkShop capture -> run table / wide table.

Usage (repo root, shared venv):
  uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-doe-analyzer/tests/test_aws_capture.py [case|all]

Cases:
  inspect   node inventory: units, rows, observed range, state counts
  pivot     wide table: one column per node, ascending time, non-ok rows dropped
  build     run table join: factors from trial design, node responses aggregated
            (warm-up trimmed), QC responses joined, hetero features joined
  context   doe_context contract: factors/responses/units/limits/platform_ref/
            ontology/data_stage/provenance; schema validation via validate.mjs
  exclude   run_exclusions.csv drops runs and is written beside the data
  errors    fail-closed on missing factor column / duplicate run_id / unknown
            node / too few rows / bad manifest
  repeat    two builds are byte-identical (determinism)
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPTS = SKILL / "scripts"
REPO = SKILL.parents[2]
SCHEMA = REPO / "docs" / "plans" / "contracts" / "doe_context.schema.json"
VALIDATE = REPO / ".claude" / "shared" / "scripts" / "validate.mjs"

sys.path.insert(0, str(SCRIPTS))
import aws_capture as ac  # noqa: E402

RESULTS = []
TMP = Path(tempfile.mkdtemp(prefix="aws_capture_"))

NODE_META = {
    "tdo_z4_temp": ("TDO Z4 温度", "°C", 196.0),
    "mdo_speed": ("MDO 车速", "m/min", 310.0),
    "tdo_ratio": ("TDO 拉伸比", "-", 2.9),
    "thickness_gauge": ("在线测厚", "um", 50.0),
    "chiller_pressure": ("冷冻水压力", "bar", 3.0),
    "ambient_temp": ("环境温度", "°C", 24.0),
}


def record(case, ok, detail=""):
    RESULTS.append((case, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {case}  {'' if ok else detail}")


def write_csv(path, header, rows):
    import csv
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in header})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buf.getvalue(), encoding="utf-8")


def make_run(root, rid, factor_vals, response_val, *, n=20, frozen_node=None):
    run_dir = root / "runs" / rid
    nodes = []
    for idx, (nid, (name, unit, base)) in enumerate(NODE_META.items()):
        rows = []
        for i in range(n):
            if nid == frozen_node:
                v = base  # stuck sensor
            elif nid == "tdo_z4_temp":
                v = factor_vals[0]
            elif nid == "mdo_speed":
                v = factor_vals[1]
            elif nid == "tdo_ratio":
                v = factor_vals[2]
            elif nid == "thickness_gauge":
                v = response_val + 0.01 * i
            elif nid == "chiller_pressure":
                v = base + 0.02 * (factor_vals[0] - 200)
            else:
                v = base + 0.1 * ((i * 7 + idx) % 5)
            rows.append({"ts_iso": f"2026-10-17T0{i % 9}:{i:02d}:00Z",
                         "ts_ms": 1760670000000 + i * 5000,
                         "value": f"{v:.5f}", "state": "ok"})
        write_csv(run_dir / "nodes" / f"{nid}.csv",
                  ["ts_iso", "ts_ms", "value", "state"], rows)
        nodes.append({"id": nid, "name": name, "unit": unit, "file": f"nodes/{nid}.csv",
                      "range": {"min": base - 20, "max": base + 20},
                      "warn": {"low": None, "high": None},
                      "rows": n, "semantics": f"{name}测点"})
    (run_dir / "manifest.json").write_text(json.dumps({
        "schema": "aw.daq-export/1", "export_id": f"daqexp-{rid}",
        "window": {"from_ms": 1760670000000, "to_ms": 1760670000000 + n * 5000},
        "lines": [{"lineId": "bopet-1", "runId": rid, "productId": "P12"}],
        "nodes": nodes, "totals": {"files": len(nodes), "rows": len(nodes) * n},
        "truncated_nodes": [],
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def make_capture(root, *, runs=3, drop_factor=False):
    root.mkdir(parents=True, exist_ok=True)
    design = []
    for i in range(runs):
        rid = f"doerun-{i + 1:03d}"
        zt = 196.0 + 4.0 * (i % 3)
        ms = 310.0 + 10.0 * ((i // 3) % 3)
        rr = 2.9 + 0.1 * ((i // 9) % 3)
        make_run(root, rid, (zt, ms, rr), 50.0 + 0.8 * (zt - 200) - 0.3 * (ms - 320))
        design.append({"run_id": rid, "design_point_id": f"dp-{i + 1:02d}",
                       "replicate_group": f"rg-{i + 1:02d}", "replicate_kind": "extra",
                       "run_order": i + 1, "block": f"B{i % 2 + 1}",
                       "tdo_z4_temp": zt, "mdo_speed": ms, "tdo_ratio": rr})
    header = ["run_id", "design_point_id", "replicate_group", "replicate_kind",
              "run_order", "block", "tdo_z4_temp", "mdo_speed", "tdo_ratio"]
    if drop_factor:
        header.remove("tdo_ratio")
        for r in design:
            r.pop("tdo_ratio", None)
    write_csv(root / "trial_design.csv", header, design)
    write_csv(root / "qc_measurements.csv",
              ["run_id", "haze_pct", "thickness_lab"],
              [{"run_id": r["run_id"], "haze_pct": 1.8 + 0.01 * i,
                "thickness_lab": 50.1 + 0.2 * (r["tdo_z4_temp"] - 200)}
               for i, r in enumerate(design)])
    write_csv(root / "features.csv",
              ["run_id", "HX-PROF-TD-EDGE-L-DEV", "HX-PROF-TD-STD"],
              [{"run_id": r["run_id"], "HX-PROF-TD-EDGE-L-DEV": f"{0.02 * i:.4f}",
                "HX-PROF-TD-STD": f"{0.15 + 0.001 * i:.4f}"}
               for i, r in enumerate(design)])
    mapping = {
        "contract_version": "1.0",
        "experiment_id": "doe-aws-test",
        "line_id": "bopet-1", "product_id": "P12", "recipe_id": "R-12um",
        "objective": "tune thickness and haze",
        "design_type_declared": "full_factorial",
        "trial_design_file": "trial_design.csv",
        "qc_file": "qc_measurements.csv",
        "features_file": "features.csv",
        "aggregation": {"method": "steady_mean", "warmup_trim": 0.2,
                        "state_filter": ["ok"], "min_rows": 5},
        "factors": [
            {"name": "tdo_z4_temp", "col": "tdo_z4_temp", "unit": "°C",
             "expected_sign": "+", "platform_ref": {
                 "recipe_param": "TDO_Z4_TEMP", "node_id": "tdo_z4_temp",
                 "unit_conversion": {"scale": 1, "offset": 0}, "rounding": 0.1,
                 "hard_limits": {"min": 185, "max": 215, "reason": "安全限"}}},
            {"name": "mdo_speed", "col": "mdo_speed", "unit": "m/min",
             "platform_ref": {"recipe_param": "MDO_SPEED", "node_id": "mdo_speed"}},
            {"name": "tdo_ratio", "col": "tdo_ratio", "unit": "-"},
        ],
        "responses": [
            {"name": "thickness_um", "col": "thickness_lab", "source": "qc",
             "unit": "um", "goal": "target", "lsl": 48, "usl": 52, "target": 50},
            {"name": "haze_pct", "col": "haze_pct", "source": "qc",
             "unit": "%", "goal": "minimize"},
            {"name": "gauge_mean", "col": "gauge_mean", "source": "node",
             "node": "thickness_gauge", "unit": "um", "goal": "target",
             "lsl": 48, "usl": 52, "target": 50},
        ],
        "covariates": [
            {"name": "ambient_temp", "col": "ambient_temp", "source": "node",
             "node": "ambient_temp", "unit": "°C"},
        ],
        "blocks": ["block"],
        "constraints": [
            {"factor": "tdo_z4_temp", "type": "box", "min": 185, "max": 215,
             "hard": True, "reason": "安全限", "source": "ontology"},
        ],
        "ontology": {"profile": "doe", "mode": "auto",
                     "scene_key": "bopet-line1-12um", "data_stage": "collected"},
    }
    (root / "mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    return mapping


def case_inspect():
    root = TMP / "inspect"
    make_capture(root, runs=2)
    rep = ac.inspect_export(root / "runs" / "doerun-001")
    record("inspect.schema", rep["schema"] == "aw.daq-export/1")
    record("inspect.nodes", len(rep["nodes"]) == len(NODE_META), str(len(rep["nodes"])))
    zt = next(n for n in rep["nodes"] if n["id"] == "tdo_z4_temp")
    record("inspect.unit", zt["unit"] == "°C")
    record("inspect.value", abs(zt["observed_range"][0] - 196.0) < 1e-6,
           str(zt["observed_range"]))
    record("inspect.states", zt["states"] == {"ok": 20}, str(zt["states"]))


def case_pivot():
    root = TMP / "pivot"
    make_capture(root, runs=1)
    out = root / "wide.csv"
    rep = ac.pivot_export(root / "runs" / "doerun-001", out, names="id", fmt="ms")
    header, rows = ac._read_csv(out)
    record("pivot.rows", rep["rows"] == 20, str(rep["rows"]))
    record("pivot.header", header[0] == "ts_ms" and "tdo_z4_temp" in header, str(header))
    record("pivot.cols", len(header) == len(NODE_META) + 1, str(len(header)))
    ts = [int(r["ts_ms"]) for r in rows]
    record("pivot.sorted", ts == sorted(ts))
    record("pivot.value", abs(float(rows[10]["tdo_z4_temp"]) - 196.0) < 1e-6,
           rows[10]["tdo_z4_temp"])
    out2 = root / "wide_iso.csv"
    ac.pivot_export(root / "runs" / "doerun-001", out2, names="name", fmt="iso")
    h2, r2 = ac._read_csv(out2)
    record("pivot.names", "TDO_Z4_温度" in h2, str(h2))
    record("pivot.iso", r2[0]["ts_iso"].endswith("Z"), r2[0]["ts_iso"])


def case_build():
    root = TMP / "build"
    make_capture(root, runs=3)
    out = TMP / "build_out"
    rep = ac.build_capture(root, root / "mapping.json", out)
    record("build.ok", rep["ok"] is True)
    record("build.rows", rep["rows"] == 3, str(rep["rows"]))
    header, rows = ac._read_csv(out / "00_input" / "run_table.csv")
    record("build.structural", header[:6] == ["run_id", "design_point_id", "replicate_group",
                                              "replicate_kind", "run_order", "block"], str(header[:6]))
    record("build.feature_cols", "HX-PROF-TD-EDGE-L-DEV" in header, str(header))
    record("build.qc_join", abs(float(rows[0]["haze_pct"]) - 1.8) < 1e-9, rows[0]["haze_pct"])
    # node response: warm-up trimmed mean of thickness_gauge = response_val + 0.01*mean(4..19)
    used = list(range(4, 20))
    expect = 50.0 + 0.8 * (196.0 - 200) - 0.3 * (310 - 320) + 0.01 * (sum(used) / len(used))
    got = float(rows[0]["gauge_mean"])
    record("build.node_agg", abs(got - expect) < 1e-4, f"{got} vs {expect}")
    record("build.covariate", abs(float(rows[0]["ambient_temp"]) - 24.1) < 0.2,
           rows[0]["ambient_temp"])
    record("build.feature_join", rows[0]["HX-PROF-TD-EDGE-L-DEV"] == "0.0000",
           rows[0]["HX-PROF-TD-EDGE-L-DEV"])
    record("build.determinism", True)  # handled by case_repeat


def case_context():
    root = TMP / "context"
    make_capture(root, runs=3)
    out = TMP / "context_out"
    ac.build_capture(root, root / "mapping.json", out)
    ctx = json.loads((out / "00_input" / "doe_context.json").read_text(encoding="utf-8"))
    record("context.contract", ctx["contract_version"] == "1.0")
    record("context.stage", ctx["data_stage"] == "collected", ctx["data_stage"])
    record("context.factors", len(ctx["factors"]) == 3, str(len(ctx["factors"])))
    record("context.responses", len(ctx["responses"]) == 3, str(len(ctx["responses"])))
    record("context.covariates", ctx["covariates"] == ["ambient_temp"], str(ctx["covariates"]))
    zt = next(f for f in ctx["factors"] if f["col"] == "tdo_z4_temp")
    record("context.bounds", zt["min"] == 196.0 and zt["max"] == 204.0,
           f"{zt['min']}..{zt['max']}")
    record("context.platform_ref", zt["platform_ref"]["recipe_param"] == "TDO_Z4_TEMP")
    gauge = next(r for r in ctx["responses"] if r["col"] == "gauge_mean")
    record("context.derivation", gauge["derivation"]["warmup_trim"] == 0.2,
           str(gauge.get("derivation")))
    record("context.ontology", ctx["ontology"]["scene_key"] == "bopet-line1-12um")
    record("context.provenance", ctx["provenance"]["runs"] == 3
           and len(ctx["provenance"]["mapping_sha256"]) == 64,
           str(ctx["provenance"].get("runs")))
    prov = json.loads((out / "00_input" / "capture_manifest.json").read_text(encoding="utf-8"))
    record("context.prov_nodes", "tdo_z4_temp" not in prov["nodes_used"], str(prov["nodes_used"]))
    record("context.prov_sha", len(prov["run_table_sha256"]) == 64)
    if SCHEMA.is_file() and VALIDATE.is_file():
        p = subprocess.run(["node", str(VALIDATE), str(SCHEMA),
                            str(out / "00_input" / "doe_context.json")],
                           capture_output=True, text=True)
        record("context.schema", p.returncode == 0, (p.stdout or p.stderr)[-400:])
    else:
        record("context.schema", True, "skipped (schema/validate missing)")


def case_exclude():
    root = TMP / "exclude"
    make_capture(root, runs=3)
    write_csv(root / "exclusions.csv", ["run_id", "reason", "excluded_at", "by"],
              [{"run_id": "doerun-002", "reason": "gauge lost", "excluded_at": "",
                "by": "operator"}])
    out = TMP / "exclude_out"
    rep = ac.build_capture(root, root / "mapping.json", out, exclusions_path=root / "exclusions.csv")
    record("exclude.rows", rep["rows"] == 2, str(rep["rows"]))
    record("exclude.count", rep["excluded"] == 1, str(rep["excluded"]))
    ex = out / "00_input" / "exclusions" / "run_exclusions.csv"
    record("exclude.file", ex.is_file())
    _, rows = ac._read_csv(ex)
    record("exclude.reason", rows and rows[0]["reason"] == "gauge lost", str(rows))
    _, data_rows = ac._read_csv(out / "00_input" / "run_table.csv")
    record("exclude.absent", all(r["run_id"] != "doerun-002" for r in data_rows))


def case_errors():
    base = TMP / "errors"
    make_capture(base, runs=2)

    root = TMP / "err_factor"
    shutil.copytree(base, root)
    m = json.loads((root / "mapping.json").read_text(encoding="utf-8"))
    m["factors"].append({"name": "missing", "col": "missing_factor"})
    (root / "mapping.json").write_text(json.dumps(m), encoding="utf-8")
    try:
        ac.build_capture(root, root / "mapping.json", TMP / "err_out1")
        record("errors.factor", False, "no exception")
    except SystemExit as exc:
        record("errors.factor", "MISSING_COLUMN" in str(exc), str(exc))

    root = TMP / "err_dup"
    shutil.copytree(base, root)
    text = (root / "trial_design.csv").read_text(encoding="utf-8").splitlines()
    text.append(text[-1])
    (root / "trial_design.csv").write_text("\n".join(text) + "\n", encoding="utf-8")
    try:
        ac.build_capture(root, root / "mapping.json", TMP / "err_out2")
        record("errors.dup", False, "no exception")
    except SystemExit as exc:
        record("errors.dup", "DUPLICATE_RUN_ID" in str(exc), str(exc))

    root = TMP / "err_node"
    shutil.copytree(base, root)
    m = json.loads((root / "mapping.json").read_text(encoding="utf-8"))
    m["responses"][2]["node"] = "not_a_node"
    (root / "mapping.json").write_text(json.dumps(m), encoding="utf-8")
    try:
        ac.build_capture(root, root / "mapping.json", TMP / "err_out3")
        record("errors.node", False, "no exception")
    except SystemExit as exc:
        record("errors.node", "UNKNOWN_NODE" in str(exc), str(exc))

    root = TMP / "err_rows"
    shutil.copytree(base, root)
    p = root / "runs" / "doerun-001" / "nodes" / "thickness_gauge.csv"
    lines = p.read_text(encoding="utf-8").splitlines()
    p.write_text("\n".join(lines[:6]) + "\n", encoding="utf-8")
    try:
        ac.build_capture(root, root / "mapping.json", TMP / "err_out4")
        record("errors.rows", False, "no exception")
    except SystemExit as exc:
        record("errors.rows", "INSUFFICIENT_NODE_ROWS" in str(exc), str(exc))

    empty = TMP / "err_manifest"
    (empty / "nodes").mkdir(parents=True)
    (empty / "manifest.json").write_text(json.dumps({"schema": "other/1"}), encoding="utf-8")
    try:
        ac.inspect_export(empty)
        record("errors.manifest", False, "no exception")
    except SystemExit as exc:
        record("errors.manifest", "UNSUPPORTED_MANIFEST" in str(exc), str(exc))


def case_repeat():
    root = TMP / "repeat"
    make_capture(root, runs=3)
    a, b = TMP / "repeat_a", TMP / "repeat_b"
    ac.build_capture(root, root / "mapping.json", a)
    ac.build_capture(root, root / "mapping.json", b)
    ta = (a / "00_input" / "run_table.csv").read_bytes()
    tb = (b / "00_input" / "run_table.csv").read_bytes()
    record("repeat.table", ta == tb)
    ca = json.loads((a / "00_input" / "doe_context.json").read_text(encoding="utf-8"))
    cb = json.loads((b / "00_input" / "doe_context.json").read_text(encoding="utf-8"))
    record("repeat.context", ca == cb)


def main():
    cases = sys.argv[1:] or ["all"]
    if "all" in cases:
        cases = ["inspect", "pivot", "build", "context", "exclude", "errors", "repeat"]
    print(f"== aws_capture tests: {', '.join(cases)} ==")
    for c in cases:
        print(f"-- {c}")
        {
            "inspect": case_inspect, "pivot": case_pivot, "build": case_build,
            "context": case_context, "exclude": case_exclude, "errors": case_errors,
            "repeat": case_repeat,
        }[c]()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\n{passed}/{len(RESULTS)} passed")
    shutil.rmtree(TMP, ignore_errors=True)
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
