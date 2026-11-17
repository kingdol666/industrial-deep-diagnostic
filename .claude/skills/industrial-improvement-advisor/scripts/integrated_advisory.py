#!/usr/bin/env python
"""integrated_advisory.py — host-embedding adapter for the improvement advisory.

One adapter for the three host flows (stability-report / deep-diagnosis / DOE):
  1. resolves an objective  (explicit file > host-derived > imacore inference)
  2. runs the SAME deterministic core as the standalone skill (imacore)
  3. writes the full advisory artifact set into `<run>/advisory/` including
     `chapter.md` (report chapter) and `step_status.json` (host audit record)
  4. appends a conditional pipeline event when the run has a run_manifest
  5. ALWAYS exits 0 — the host run must never fail because advisory did

Switch: `00_input/advisory_opt_out` (file) or callers simply not invoking the
adapter. `--force` ignores the opt-out file.

CLI:
  python integrated_advisory.py --run-dir DIR --origin stability|diagnosis|doe
      [--data PATH] [--time-col COL] [--objective PATH] [--doe-run-dir DIR]
      [--action-log PATH] [--scene KEY] [--store-dir DIR] [--max-actions N]
      [--force]
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_SCRIPTS = SCRIPT_DIR.parents[2] / "shared" / "scripts"
for _p in (SCRIPT_DIR, SHARED_SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ontology_prepare_common as oc  # noqa: E402

import improvement_analyzer  # noqa: E402

# Load OUR report_builder by path: the stability skill ships a same-named module
# that imacore's reuse path puts earlier on sys.path.
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "ima_report_builder", SCRIPT_DIR / "report_builder.py")
report_builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(report_builder)

from imacore import _io, objective as objective_mod, render  # noqa: E402

ORIGINS = ("stability", "diagnosis", "doe")
DATA_CANDIDATES = (
    "00_input/data.csv",
    "00_input/run_table.csv",
    "00_input/preprocessed_data.csv",
    "02_processed/cleaned_data_steady_only.csv",
    "02_processed/cleaned_data.csv",
)
_KPI_HINTS = ("thickness", "厚", "quality", "质量", "yield", "良率", "defect",
              "不良", "cv", "std", "md_", "basis_weight", "moisture")


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _pick_data(run_dir, data_arg):
    """Resolution order: run-dir-relative → cwd-relative (CLI callers pass
    repo-root-relative paths) → candidates → first csv in 00_input/02_processed."""
    if data_arg:
        p = Path(data_arg)
        if p.is_absolute():
            return p
        candidate = run_dir / p
        if candidate.is_file():
            return candidate
        candidate = Path.cwd() / p
        if candidate.is_file():
            return candidate
    for rel in DATA_CANDIDATES:
        p = run_dir / rel
        if p.is_file():
            return p
    for base in ("00_input", "02_processed"):
        d = run_dir / base
        if d.is_dir():
            csvs = sorted(d.glob("*.csv"))
            if csvs:
                return csvs[0]
    return None


def _derive_stability_objective(run_dir, numeric_cols):
    rep = _read(run_dir / "line_report" / "stability_report.json")
    if not isinstance(rep, dict):
        return None, None
    data = rep.get("data") or {}
    for col in (data.get("inspection_cols") or []):
        if col in numeric_cols:
            return {"contract_version": "1.0",
                    "targets": [{"metric": col,
                                 "direction": objective_mod.name_direction(col)}],
                    "notes": "derived from stability_report.json inspection_cols"}, "stability_report.inspection_cols"
    worst = None
    for prm in rep.get("parameters") or []:
        if prm.get("name") in numeric_cols:
            score = prm.get("score")
            if worst is None or (isinstance(score, (int, float))
                                 and score < (worst[1] if isinstance(worst[1], (int, float)) else 101)):
                worst = (prm.get("name"), score)
    if worst:
        return {"contract_version": "1.0",
                "targets": [{"metric": worst[0],
                             "direction": objective_mod.name_direction(worst[0])}],
                "notes": "derived from stability_report.json (lowest-score parameter)"}, "stability_report.parameters[]"
    return None, None


def _derive_diagnosis_objective(run_dir, numeric_cols):
    texts = []
    for rel in ("04_diagnostics/diagnosis.json", "04_diagnostics/evidence.json",
                "04_diagnostics/confidence.json"):
        doc = _read(run_dir / rel)
        if doc is not None:
            texts.append(json.dumps(doc, ensure_ascii=False))
    if not texts:
        return None, None
    blob = "\n".join(texts)[:400000]
    hits = [c for c in numeric_cols if c and c in blob]
    if not hits:
        return None, None
    preferred = [c for c in hits if any(k in c.lower() for k in _KPI_HINTS)]
    metric = (preferred or hits)[0]
    return {"contract_version": "1.0",
            "targets": [{"metric": metric,
                         "direction": objective_mod.name_direction(metric)}],
            "notes": "derived from 04_diagnostics artifacts (integration origin=diagnosis)"}, "04_diagnostics/*"


def _derive_doe_objective(run_dir, numeric_cols):
    recs = _read(run_dir / "conclusions" / "recommendations.json")
    if not isinstance(recs, dict):
        return None, None
    specs = recs.get("response_specs")
    rows = []
    if isinstance(specs, dict):
        rows = [dict(v or {}, metric=k) for k, v in specs.items() if isinstance(v, dict)] \
            if all(isinstance(v, dict) for v in specs.values()) else [
                dict(v or {}, metric=k) for k, v in specs.items()]
    elif isinstance(specs, list):
        rows = [x for x in specs if isinstance(x, dict)]
    for row in rows:
        metric = row.get("metric") or row.get("response")
        if metric not in numeric_cols:
            continue
        target = row.get("target")
        lsl, usl = row.get("lsl"), row.get("usl")
        if isinstance(target, (int, float)):
            tol = None
            if isinstance(lsl, (int, float)) and isinstance(usl, (int, float)):
                tol = (usl - lsl) / 2.0
            return {"contract_version": "1.0",
                    "targets": [{"metric": metric, "direction": "target",
                                 "target_value": float(target), "tolerance": tol}],
                    "notes": "derived from recommendations.json response_specs"}, "recommendations.response_specs"
        if isinstance(lsl, (int, float)) and isinstance(usl, (int, float)):
            # spec window only: aim at its midpoint with half-width tolerance
            return {"contract_version": "1.0",
                    "targets": [{"metric": metric, "direction": "target",
                                 "target_value": (lsl + usl) / 2.0,
                                 "tolerance": (usl - lsl) / 2.0}],
                    "notes": "derived from recommendations.json response_specs (lsl/usl midpoint)"}, "recommendations.response_specs"
        if isinstance(usl, (int, float)) and lsl is None:
            direction = "min"
        elif isinstance(lsl, (int, float)) and usl is None:
            direction = "max"
        else:
            direction = objective_mod.name_direction(metric)
        return {"contract_version": "1.0",
                "targets": [{"metric": metric, "direction": direction}],
                "notes": "derived from recommendations.json response_specs"}, "recommendations.response_specs"
    return None, None


def _numeric_cols_from_data(path):
    """Column probe without loading the whole table (header row only)."""
    try:
        import pandas as pd
        head = pd.read_csv(path, nrows=200)
        return [c for c in head.columns if pd.api.types.is_numeric_dtype(head[c])]
    except Exception:
        return []


def _append_event(run_dir, event, status, files, summary):
    if not (run_dir / "run_manifest.json").is_file():
        return
    try:
        oc.append_jsonl_contained(run_dir / ".pipeline_events.jsonl", {
            "event": event,
            "step": "improvement_advisory",
            "agent": "main-agent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "run_id": run_dir.name,
            "run_dir": str(run_dir),
            "files_written": files,
            "summary": summary,
        })
    except Exception:
        pass  # event logging is never allowed to break the host run


def _write_status(run_dir, payload):
    try:
        oc.write_json_strict(run_dir / "advisory" / "step_status.json", payload)
    except Exception:
        pass


def _analyze_argv(run_dir, *, data_path, objective_path, doe_run_dir, action_log,
                  time_col, scene, store_dir, max_actions):
    argv = ["analyze", "--run-dir", str(run_dir)]
    if data_path:
        argv += ["--data", str(data_path)]
    if time_col:
        argv += ["--time-col", str(time_col)]
    if objective_path:
        argv += ["--objective", str(objective_path)]
    if doe_run_dir:
        argv += ["--doe-run-dir", str(doe_run_dir)]
    if action_log:
        argv += ["--action-log", str(action_log)]
    if scene:
        argv += ["--scene", str(scene)]
    if store_dir:
        argv += ["--store-dir", str(store_dir)]
    if max_actions:
        argv += ["--max-actions", str(int(max_actions))]
    return argv


def run(run_dir, *, origin, data=None, time_col=None, objective=None,
        doe_run_dir=None, action_log=None, scene=None, store_dir=None,
        max_actions=None, force=False):
    started = datetime.now(timezone.utc)
    run_dir = Path(run_dir).resolve()
    base_status = {
        "contract_version": "improvement-advisory-step/1.0",
        "origin": origin,
        "run_dir": str(run_dir),
        "started_at": started.isoformat(),
    }
    if not run_dir.is_dir():
        payload = dict(base_status, status="failed", exit_code=3,
                       reason="run dir missing")
        return payload

    opt_out = run_dir / "00_input" / "advisory_opt_out"
    if opt_out.exists() and not force:
        payload = dict(base_status, status="skipped", exit_code=0,
                       reason="00_input/advisory_opt_out present",
                       generated_at=datetime.now(timezone.utc).isoformat())
        _write_status(run_dir, payload)
        _append_event(run_dir, "advisory_step_skipped", "skipped", [], payload)
        return payload

    data_path = _pick_data(run_dir, data)
    if data_path is None or not Path(data_path).is_file():
        payload = dict(base_status, status="failed", exit_code=2,
                       reason="no analysis data file found in run dir")
        _write_status(run_dir, payload)
        _append_event(run_dir, "advisory_step_failed", "failed", [], payload)
        return payload

    numeric_cols = _numeric_cols_from_data(data_path)
    objective_doc, objective_source = None, None
    explicit_obj = Path(objective) if objective else (run_dir / "00_input" / "objective.json")
    if explicit_obj.is_file():
        objective_doc, objective_source = None, "explicit"  # analyzer loads it itself
        objective_path = explicit_obj
    else:
        derivers = {"stability": _derive_stability_objective,
                    "diagnosis": _derive_diagnosis_objective,
                    "doe": _derive_doe_objective}
        derive = derivers.get(origin)
        objective_doc, objective_source = derive(run_dir, numeric_cols) if derive else (None, None)
        objective_path = None
        if objective_doc is not None:
            objective_path = run_dir / "advisory" / "_derived_objective.json"
            try:
                oc.write_json_strict(objective_path, objective_doc)
            except Exception as exc:
                payload = dict(base_status, status="failed", exit_code=3,
                               reason=f"cannot write derived objective: {exc}")
                _write_status(run_dir, payload)
                _append_event(run_dir, "advisory_step_failed", "failed", [], payload)
                return payload
        else:
            objective_source = "inferred"

    doe_dir = doe_run_dir
    if doe_dir is None and origin == "doe":
        doe_dir = run_dir  # recommendations.json lives in this run

    artifacts = []
    try:
        argv = _analyze_argv(run_dir, data_path=data_path,
                             objective_path=objective_path,
                             doe_run_dir=doe_dir, action_log=action_log,
                             time_col=time_col, scene=scene,
                             store_dir=store_dir, max_actions=max_actions)
        # Designed DOE tables are legitimately ~20 rows: relax the dataset
        # floor to the relation-level minimum for the doe origin.
        if origin == "doe":
            argv += ["--min-rows", "12"]
        code = improvement_analyzer.main(argv)
    except SystemExit as exc:  # analyzer's own strict input errors
        code = int(exc.code) if isinstance(exc.code, int) else 3
    except Exception as exc:  # defensive: adapter must never raise into host
        payload = dict(base_status, status="failed", exit_code=3,
                       reason=f"analyzer crashed: {type(exc).__name__}: {exc}")
        _write_status(run_dir, payload)
        _append_event(run_dir, "advisory_step_failed", "failed", [], payload)
        return payload

    advisory_json = run_dir / "advisory" / "advisory_actions.json"
    report = _read(advisory_json)
    chapter_written = False
    if isinstance(report, dict):
        # Projection for the stability-report builder: a fixed-name sibling of
        # stability_report.json keeps the host reader a same-directory read.
        line_dir = run_dir / "line_report"
        if line_dir.is_dir():
            try:
                oc.write_json_strict(line_dir / "advisory_actions.json", report)
            except Exception:
                pass
        try:
            oc.write_text_contained(run_dir / "advisory" / "chapter.md",
                                    render.render_markdown(report))
            chapter_written = True
        except Exception:
            pass
        try:
            report_builder.main([
                "--advisory", str(advisory_json),
                "--charts", str(run_dir / "advisory" / "charts.json"),
                "--out", str(run_dir / "advisory"),
            ])
        except Exception:
            pass
        for name in ("advisory_actions.json", "objective_resolved.json",
                     "charts.json", "improvement_advisory.html",
                     "improvement_advisory.md", "html_selfcheck.json",
                     "chapter.md"):
            p = run_dir / "advisory" / name
            if p.is_file():
                artifacts.append(str(p.relative_to(run_dir)).replace("\\", "/"))
        if (run_dir / "advisory" / "optimizer_seed.json").is_file():
            artifacts.append("advisory/optimizer_seed.json")

    status = "used" if isinstance(report, dict) else "failed"
    summary = {}
    if isinstance(report, dict):
        grades = {"A": 0, "B": 0, "C": 0}
        for a in report.get("actions") or []:
            if a.get("grade") in grades:
                grades[a["grade"]] += 1
        summary = {
            "report_status": report.get("status"),
            "n_actions": len(report.get("actions") or []),
            "grades": grades,
            "n_prescriptions": len(report.get("prescriptions") or []),
            "max_achievable_grade": (report.get("waterline") or {}).get("max_achievable_grade"),
            "report_id": report.get("report_id"),
        }
    payload = dict(base_status, status=status, exit_code=int(code),
                   objective_source=objective_source,
                   data_path=str(data_path),
                   artifacts=artifacts,
                   summary=summary,
                   chapter_written=chapter_written,
                   generated_at=datetime.now(timezone.utc).isoformat())
    _write_status(run_dir, payload)
    event = {"used": "advisory_step_completed", "failed": "advisory_step_failed"}.get(
        status, "advisory_step_failed")
    if code == 2 and status == "used":
        event = "advisory_step_completed"  # not_actionable is an honest used outcome
    _append_event(run_dir, event, status, artifacts, summary)
    return payload


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="host-embedding advisory adapter")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--origin", choices=list(ORIGINS), required=True)
    ap.add_argument("--data", default=None)
    ap.add_argument("--time-col", default=None)
    ap.add_argument("--objective", default=None)
    ap.add_argument("--doe-run-dir", default=None)
    ap.add_argument("--action-log", default=None)
    ap.add_argument("--scene", default=None)
    ap.add_argument("--store-dir", default=None)
    ap.add_argument("--max-actions", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    payload = run(args.run_dir, origin=args.origin, data=args.data,
                  time_col=args.time_col, objective=args.objective,
                  doe_run_dir=args.doe_run_dir, action_log=args.action_log,
                  scene=args.scene, store_dir=args.store_dir,
                  max_actions=args.max_actions, force=args.force)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0  # adapter contract: never fail the host


if __name__ == "__main__":
    raise SystemExit(main())
