#!/usr/bin/env python
"""AgentWorkShop capture -> wide table / DOE run table.

The platform (AgentWorkShop) captures data as DAQ exports:

    <export>/manifest.json          aw.daq-export/1
    <export>/nodes/<node>.csv       ts_iso,ts_ms,value,state

One export is one time window of one line; a DOE campaign is a folder of
exports, one per trial run. This adapter is the missing deterministic bridge:

    pivot   one export  -> wide time-series CSV (sentinel / stability input)
    build   campaign    -> 00_input/run_table.csv + 00_input/doe_context.json
                           (then doe_context_adapter.py -> analysis_context.json)
    inspect one export  -> node inventory (id/name/unit/rows/range/states)

Everything here is deterministic, offline and path-contained: no network, no
LLM, no bare open(). The mapping file is the single place where platform
semantics (which node is which response, specs, recipe params, hard limits)
are declared; nothing is guessed silently.

Usage:
    python aws_capture.py inspect --export <export-dir> [--json]
    python aws_capture.py pivot   --export <export-dir> --out <wide.csv>
                                  [--names id|name] [--format iso|ms]
    python aws_capture.py build   --capture-root <dir> --mapping <mapping.json>
                                  --out-dir <run-dir> [--exclusions <csv>] [--json]

Exit codes: 0 ok, 2 contract violation (missing file/column/node, bad json).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

ADAPTER_VERSION = "1.0.0"
ALLOWED_AGGREGATES = ("steady_mean", "mean", "median", "end_mean")
DEFAULT_MIN_ROWS = 5
EPS = 1e-12


# ---------------------------------------------------------------- plumbing

def _contained(path: Path, root: Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = root / p
    p = p.resolve()
    r = Path(root).resolve()
    if r != p and r not in p.parents:
        raise ValueError(f"path outside the capture root rejected: {path}")
    return p


def _read_json(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"BAD_JSON: {path}: {exc}") from exc


def _read_csv(path: Path) -> tuple[list[str], list[dict]]:
    text = Path(path).read_text(encoding="utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    return list(reader.fieldnames or []), [dict(r) for r in reader]


def _write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in header})
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(buf.getvalue(), encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _num(value) -> float | None:
    try:
        v = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _fmt(v: float | None) -> str:
    if v is None:
        return ""
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return repr(round(v, 6))


def _slug(name: str) -> str:
    return "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in str(name)).strip("_") or "node"


# ---------------------------------------------------------------- export io

def load_manifest(export_dir: Path) -> tuple[dict, dict[str, dict]]:
    manifest_path = export_dir / "manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"MISSING_MANIFEST: {manifest_path}")
    manifest = _read_json(manifest_path)
    if not str(manifest.get("schema", "")).startswith("aw.daq-export/"):
        raise SystemExit(f"UNSUPPORTED_MANIFEST: schema={manifest.get('schema')!r} "
                         f"(expected aw.daq-export/1)")
    nodes = {}
    for node in manifest.get("nodes") or []:
        if not isinstance(node, dict) or not node.get("id"):
            continue
        nodes[str(node["id"])] = node
    if not nodes:
        raise SystemExit(f"NO_NODES: {manifest_path}")
    return manifest, nodes


def _node_file(export_dir: Path, node: dict) -> Path:
    rel = node.get("file")
    if not rel:
        rel = f"nodes/{_slug(str(node['id']))}.csv"
    path = _contained(export_dir / rel, export_dir)
    if not path.is_file():
        raise SystemExit(f"MISSING_NODE_FILE: {rel} (node {node.get('id')})")
    return path


def read_node(path: Path) -> list[dict]:
    header, rows = _read_csv(path)
    need = {"ts_ms", "value"}
    if not need.issubset(set(header)):
        raise SystemExit(f"BAD_NODE_CSV: {path} header={header} (need ts_ms,value)")
    out = []
    for row in rows:
        ts = _num(row.get("ts_ms"))
        if ts is None:
            continue
        out.append({
            "ts_ms": int(ts),
            "ts_iso": (row.get("ts_iso") or "").strip(),
            "value": _num(row.get("value")),
            "state": (row.get("state") or "ok").strip() or "ok",
        })
    out.sort(key=lambda r: r["ts_ms"])
    return out


def resolve_node(nodes: dict[str, dict], ref: str) -> dict:
    if ref in nodes:
        return nodes[ref]
    by_name = {str(n.get("name")): n for n in nodes.values() if n.get("name")}
    if ref in by_name:
        return by_name[ref]
    raise SystemExit(f"UNKNOWN_NODE: {ref!r} (available: {', '.join(sorted(nodes))})")


def aggregate_node(rows: list[dict], *, method: str = "steady_mean",
                   warmup_trim: float = 0.2, keep_states: tuple[str, ...] = ("ok",),
                   min_rows: int = DEFAULT_MIN_ROWS) -> dict:
    """Deterministic per-run scalar from one node's time series.

    steady_mean: drop non-ok states, drop the first `warmup_trim` fraction of
    the rows (warm-up), average the rest. mean/median use all finite rows of
    the kept states. end_mean averages the last 10% (>=1 row).
    """
    if method not in ALLOWED_AGGREGATES:
        raise SystemExit(f"BAD_AGGREGATE: {method} (allowed: {', '.join(ALLOWED_AGGREGATES)})")
    if not 0 <= warmup_trim < 1:
        raise SystemExit(f"BAD_WARMUP_TRIM: {warmup_trim}")
    states = tuple(s for s in keep_states if s) or ("ok",)
    kept = [r for r in rows if r["state"] in states and r["value"] is not None]
    if not kept:
        return {"value": None, "n_rows": 0, "n_input": len(rows), "state_filtered": len(rows)}
    if method == "steady_mean":
        cut = int(len(kept) * warmup_trim)
        used = kept[cut:] or kept[-1:]
    elif method == "end_mean":
        cut = max(1, int(math.ceil(len(kept) * 0.1)))
        used = kept[-cut:]
    elif method == "median":
        vals = sorted(r["value"] for r in kept)
        mid = len(vals) // 2
        med = vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2
        return {"value": med, "n_rows": len(kept), "n_input": len(rows),
                "state_filtered": len(rows) - len(kept)}
    else:
        used = kept
    if len(used) < min_rows:
        raise SystemExit(f"INSUFFICIENT_NODE_ROWS: {len(used)} usable rows < {min_rows}")
    vals = [r["value"] for r in used]
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1) if len(vals) > 1 else 0.0
    return {
        "value": mean,
        "std": math.sqrt(var),
        "min": min(vals),
        "max": max(vals),
        "n_rows": len(used),
        "n_input": len(rows),
        "state_filtered": len(rows) - len(kept),
        "window": {"from_ms": used[0]["ts_ms"], "to_ms": used[-1]["ts_ms"]},
    }


# ---------------------------------------------------------------- pivot

def pivot_export(export_dir: Path, out_path: Path, *, names: str = "id",
                 fmt: str = "iso") -> dict:
    manifest, nodes = load_manifest(export_dir)
    series: dict[str, dict[int, float]] = {}
    labels: dict[str, str] = {}
    for nid, node in nodes.items():
        label = str(node.get("name") or nid) if names == "name" else nid
        label = _slug(label)
        if label in labels.values():
            label = _slug(nid)
        labels[nid] = label
        rows = read_node(_node_file(export_dir, node))
        series[nid] = {r["ts_ms"]: r["value"] for r in rows if r["value"] is not None}
    all_ts = sorted({ts for s in series.values() for ts in s})
    if not all_ts:
        raise SystemExit(f"NO_DATA_ROWS: {export_dir}")
    time_header = "ts_iso" if fmt == "iso" else "ts_ms"
    header = [time_header] + [labels[nid] for nid in nodes]
    rows_out = []
    import datetime as _dt

    for ts in all_ts:
        row = {time_header: (_dt.datetime.fromtimestamp(ts / 1000, _dt.timezone.utc)
                             .isoformat(timespec="milliseconds").replace("+00:00", "Z")
                             if fmt == "iso" else ts)}
        for nid in nodes:
            v = series[nid].get(ts)
            row[labels[nid]] = _fmt(v)
        rows_out.append(row)
    _write_csv(out_path, header, rows_out)
    return {"out": str(out_path), "rows": len(rows_out), "columns": len(header),
            "nodes": len(nodes), "window": {"from_ms": all_ts[0], "to_ms": all_ts[-1]},
            "manifest_sha256": _sha256(export_dir / "manifest.json")}


# ---------------------------------------------------------------- build

def _load_mapping(path: Path, capture_root: Path) -> dict:
    mapping = _read_json(path)
    if not isinstance(mapping.get("factors"), list) or len(mapping["factors"]) < 2:
        raise SystemExit("CONTRACT_VIOLATION: mapping.factors needs >= 2 entries")
    if not isinstance(mapping.get("responses"), list) or not mapping["responses"]:
        raise SystemExit("CONTRACT_VIOLATION: mapping.responses needs >= 1 entry")
    trial = mapping.get("trial_design_file") or "trial_design.csv"
    trial_path = _contained(capture_root / trial, capture_root)
    if not trial_path.is_file():
        raise SystemExit(f"MISSING_TRIAL_DESIGN: {trial_path}")
    qc = mapping.get("qc_file")
    if qc and not _contained(capture_root / qc, capture_root).is_file():
        raise SystemExit(f"MISSING_QC_FILE: {qc}")
    return mapping


def _normalize_platform_ref(ref: dict | None, unit: str | None) -> dict | None:
    """Keep platform_ref inside the frozen contract (unit_conversion is a number).

    A mapping may spell the conversion as {"scale": n, "offset": m}; the
    contract has no offset slot, so a non-zero offset is a hard error rather
    than a silent lie about the setpoint the platform will receive.
    """
    if not isinstance(ref, dict):
        return ref
    out = {k: v for k, v in ref.items() if k != "unit_conversion"}
    conv = ref.get("unit_conversion")
    if isinstance(conv, dict):
        scale = _num(conv.get("scale", conv.get("factor", 1.0)))
        offset = _num(conv.get("offset", 0.0)) or 0.0
        if offset not in (0.0, None):
            raise SystemExit("UNSUPPORTED_UNIT_CONVERSION_OFFSET: platform_ref.unit_conversion "
                             "may only carry a scale; fold the offset into the recipe parameter")
        out["unit_conversion"] = scale if scale is not None else 1.0
    else:
        out["unit_conversion"] = conv
    if unit and not out.get("unit"):
        out["unit"] = unit
    return out


def _infer_factor_type(values: list[str], declared: str | None) -> str:
    if declared in ("numeric", "categorical"):
        return declared
    seen = 0
    for v in values:
        s = (v or "").strip()
        if not s:
            continue
        seen += 1
        if _num(s) is None:
            return "categorical"
    return "numeric" if seen else "numeric"


def build_capture(capture_root: Path, mapping_path: Path, out_dir: Path,
                  *, exclusions_path: Path | None = None) -> dict:
    capture_root = Path(capture_root).resolve()
    out_dir = Path(out_dir).resolve()
    mapping = _load_mapping(mapping_path, capture_root)

    trial_rel = mapping.get("trial_design_file") or "trial_design.csv"
    trial_path = _contained(capture_root / trial_rel, capture_root)
    header, trial_rows = _read_csv(trial_path)
    if "run_id" not in header:
        raise SystemExit(f"MISSING_COLUMN: run_id in {trial_path}")
    seen = set()
    for row in trial_rows:
        rid = (row.get("run_id") or "").strip()
        if not rid:
            raise SystemExit("CONTRACT_VIOLATION: empty run_id in trial design")
        if rid in seen:
            raise SystemExit(f"DUPLICATE_RUN_ID: {rid}")
        seen.add(rid)

    excluded: dict[str, str] = {}
    if exclusions_path:
        ex_path = _contained(exclusions_path, capture_root)
        if not ex_path.is_file():
            raise SystemExit(f"MISSING_EXCLUSIONS: {ex_path}")
        _, ex_rows = _read_csv(ex_path)
        for row in ex_rows:
            rid = (row.get("run_id") or "").strip()
            if rid:
                excluded[rid] = (row.get("reason") or "").strip() or "excluded"

    factors = mapping["factors"]
    for f in factors:
        col = f.get("col") or f.get("name")
        if col not in header:
            raise SystemExit(f"MISSING_COLUMN: factor {col!r} not in {trial_path.name}")

    # ---- per-run node aggregation --------------------------------------
    runs_dir = _contained(capture_root / (mapping.get("runs_dir") or "runs"), capture_root)
    defaults = mapping.get("aggregation") or {}
    method = defaults.get("method") or "steady_mean"
    warmup = float(defaults.get("warmup_trim", 0.2))
    keep_states = tuple(defaults.get("state_filter") or ["ok"])
    min_rows = int(defaults.get("min_rows", DEFAULT_MIN_ROWS))

    needed_nodes = []
    for spec in list(mapping.get("responses") or []) + list(mapping.get("covariates") or []):
        if (spec.get("source") or "qc") == "node" and spec.get("node"):
            needed_nodes.append(str(spec["node"]))
    node_cache: dict[str, dict[str, dict]] = {}
    provenance_runs: dict[str, dict] = {}

    def node_stat(rid: str, ref: str, spec: dict) -> dict:
        run_dir = _contained(runs_dir / rid, capture_root)
        if not run_dir.is_dir():
            raise SystemExit(f"MISSING_RUN_CAPTURE: {rid} ({run_dir})")
        if rid not in node_cache:
            _, nodes = load_manifest(run_dir)
            node_cache[rid] = nodes
        node = resolve_node(node_cache[rid], ref)
        rows = read_node(_node_file(run_dir, node))
        stat = aggregate_node(rows,
                              method=spec.get("aggregate") or method,
                              warmup_trim=float(spec.get("warmup_trim", warmup)),
                              keep_states=tuple(spec.get("state_filter") or keep_states),
                              min_rows=int(spec.get("min_rows", min_rows)))
        provenance_runs.setdefault(rid, {"nodes": {}})["nodes"][ref] = {
            "unit": node.get("unit"), "file": node.get("file"),
            "rows": len(rows), "n_used": stat["n_rows"],
            "state_filtered": stat["state_filtered"],
        }
        return stat

    qc_rows: dict[str, dict] = {}
    if mapping.get("qc_file"):
        qc_path = _contained(capture_root / mapping["qc_file"], capture_root)
        qc_header, rows = _read_csv(qc_path)
        if "run_id" not in qc_header:
            raise SystemExit(f"MISSING_COLUMN: run_id in {qc_path.name}")
        for row in rows:
            qc_rows[(row.get("run_id") or "").strip()] = row

    feature_rows: dict[str, dict] = {}
    for key in ("features_file", "notes_features_file"):
        rel = mapping.get(key)
        if not rel:
            continue
        path = _contained(capture_root / rel, capture_root)
        if not path.is_file():
            raise SystemExit(f"MISSING_FEATURES_FILE: {path}")
        f_header, f_rows = _read_csv(path)
        if "run_id" not in f_header:
            raise SystemExit(f"MISSING_COLUMN: run_id in {path.name}")
        for row in f_rows:
            rid = (row.get("run_id") or "").strip()
            if rid:
                feature_rows.setdefault(rid, {}).update(
                    {k: v for k, v in row.items() if k != "run_id"})

    # ---- assemble the run table ----------------------------------------
    structural = [c for c in ("run_id", "design_point_id", "replicate_group",
                              "replicate_kind", "run_order", "block") if c in header]
    headers = list(structural)
    for f in factors:
        headers.append(f.get("col") or f.get("name"))
    response_cols = []
    for r in mapping["responses"]:
        col = r.get("col") or r.get("name")
        if col not in response_cols:
            response_cols.append(col)
    headers.extend(response_cols)
    covariates = []
    for c in mapping.get("covariates") or []:
        col = c.get("col") or c.get("name")
        if col not in covariates:
            covariates.append(col)
    headers.extend(covariates)
    feature_cols = sorted({k for row in feature_rows.values() for k in row})
    headers.extend([c for c in feature_cols if c not in headers])

    rows_out = []
    dropped = []
    for row in trial_rows:
        rid = (row.get("run_id") or "").strip()
        if rid in excluded:
            dropped.append({"run_id": rid, "reason": excluded[rid]})
            continue
        out = {c: (row.get(c) or "").strip() for c in structural}
        for f in factors:
            col = f.get("col") or f.get("name")
            out[col] = (row.get(col) or "").strip()
        for r in mapping["responses"]:
            col = r.get("col") or r.get("name")
            if (r.get("source") or "qc") == "node":
                stat = node_stat(rid, str(r["node"]), r)
                out[col] = _fmt(stat["value"])
            else:
                qrow = qc_rows.get(rid)
                out[col] = (qrow.get(col) or "").strip() if qrow else ""
        for c in mapping.get("covariates") or []:
            col = c.get("col") or c.get("name")
            if (c.get("source") or "qc") == "node":
                out[col] = _fmt(node_stat(rid, str(c["node"]), c)["value"])
            else:
                qrow = qc_rows.get(rid)
                out[col] = (qrow.get(col) or "").strip() if qrow else ""
        for c in feature_cols:
            out[c] = (feature_rows.get(rid) or {}).get(c, "")
        rows_out.append(out)

    if not rows_out:
        raise SystemExit("NO_RUNS: every trial run was excluded")

    run_table = out_dir / "00_input" / "run_table.csv"
    _write_csv(run_table, headers, rows_out)

    # ---- doe_context ----------------------------------------------------
    f_out, f_bounds = [], {}
    for f in factors:
        col = f.get("col") or f.get("name")
        vals = [r.get(col, "") for r in rows_out]
        ftype = _infer_factor_type(vals, f.get("type"))
        numeric = [_num(v) for v in vals]
        lo, hi = f.get("min"), f.get("max")
        if ftype == "numeric":
            finite = [v for v in numeric if v is not None]
            if lo is None and finite:
                lo = min(finite)
            if hi is None and finite:
                hi = max(finite)
            f_bounds[col] = [lo, hi]
            levels = f.get("levels")
        else:
            levels = f.get("levels") or sorted({v for v in vals if v.strip()})
            lo = hi = None
        f_out.append({
            "name": f.get("name") or col, "col": col, "type": ftype,
            "unit": f.get("unit"), "min": lo, "max": hi, "levels": levels,
            "role": f.get("role") or "control",
            "expected_sign": f.get("expected_sign"),
            "physical_meaning": f.get("physical_meaning"),
            "ontology_signal": f.get("ontology_signal"),
            "platform_ref": _normalize_platform_ref(f.get("platform_ref"), f.get("unit")),
        })

    r_out, measured = [], 0
    for r in mapping["responses"]:
        col = r.get("col") or r.get("name")
        vals = [(row.get(col) or "").strip() for row in rows_out]
        if any(v for v in vals):
            measured += 1
        spec = {"name": r.get("name") or col, "col": col, "unit": r.get("unit"),
                "goal": r.get("goal"), "lsl": r.get("lsl"), "usl": r.get("usl"),
                "target": r.get("target"), "weight": r.get("weight"),
                "ontology_signal": r.get("ontology_signal"),
                "platform_metric_ref": r.get("platform_metric_ref")}
        if r.get("source") == "node":
            spec["derivation"] = {
                "source": "node", "node": r.get("node"),
                "aggregate": r.get("aggregate") or method,
                "warmup_trim": float(r.get("warmup_trim", warmup)),
                "state_filter": list(r.get("state_filter") or keep_states),
            }
        r_out.append(spec)

    c_out = []
    for c in mapping.get("covariates") or []:
        col = c.get("col") or c.get("name")
        spec = {"name": c.get("name") or col, "col": col, "unit": c.get("unit")}
        if c.get("source") == "node":
            spec["derivation"] = {
                "source": "node", "node": c.get("node"),
                "aggregate": c.get("aggregate") or method,
                "warmup_trim": float(c.get("warmup_trim", warmup)),
                "state_filter": list(c.get("state_filter") or keep_states),
            }
        c_out.append(spec)

    ontology = mapping.get("ontology") or {}
    data_stage = "collected" if measured else "design_only"
    doe_ctx = {
        "contract_version": "1.0",
        "experiment_id": mapping.get("experiment_id") or "doe-unknown",
        "parent_experiment_id": mapping.get("parent_experiment_id"),
        "round_no": mapping.get("round_no", 1),
        "campaign_id": mapping.get("campaign_id"),
        "line_id": mapping.get("line_id"),
        "product_id": mapping.get("product_id"),
        "recipe_id": mapping.get("recipe_id"),
        "objective": mapping.get("objective"),
        "design_type_declared": mapping.get("design_type_declared"),
        "design_region": mapping.get("design_region") or {
            "factorial_bounds": f_bounds,
            "design_hull": mapping.get("design_hull") or "imported",
        },
        "data_stage": data_stage,
        "data_file": "run_table.csv",
        "factors": f_out,
        "responses": r_out,
        "blocks": mapping.get("blocks") or [],
        "covariates": [c["col"] for c in c_out],
        "covariate_specs": c_out,
        "constraints": mapping.get("constraints") or [],
        "replicates_col": "replicate_group" if "replicate_group" in headers else None,
        "run_order_col": "run_order" if "run_order" in headers else None,
        "group_col": "run_id",
        "time_col": None,
        "current_setpoint": mapping.get("current_setpoint"),
        "baseline_source": mapping.get("baseline_source") or "platform_recipe",
        "ontology": {
            "profile": ontology.get("profile") or "doe",
            "mode": ontology.get("mode") or "auto",
            "scene_key": ontology.get("scene_key"),
            "version": ontology.get("version"),
            "data_stage": data_stage,
            "source": ontology.get("source"),
        },
        "provenance": {
            "platform": "AgentWorkShop",
            "created_by": f"aws_capture.py {ADAPTER_VERSION}",
            "capture_root": capture_root.name,
            "mapping_file": mapping_path.name,
            "mapping_sha256": _sha256(mapping_path),
            "trial_design_sha256": _sha256(trial_path),
            "runs": len(rows_out),
            "excluded": dropped,
            "node_aggregation": {
                "default_method": method, "warmup_trim": warmup,
                "state_filter": list(keep_states), "min_rows": min_rows,
            },
        },
    }
    ctx_path = out_dir / "00_input" / "doe_context.json"
    ctx_path.write_text(json.dumps(doe_ctx, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    # exclusions live beside the data, never in the data directory itself
    exclusion_out = out_dir / "00_input" / "exclusions" / "run_exclusions.csv"
    if dropped:
        _write_csv(exclusion_out, ["run_id", "reason", "excluded_at", "by"],
                   [{"run_id": d["run_id"], "reason": d["reason"],
                     "excluded_at": "", "by": "capture_adapter"} for d in dropped])

    prov = {
        "contract_version": "1.0",
        "adapter_version": ADAPTER_VERSION,
        "capture_root": str(capture_root),
        "mapping_sha256": _sha256(mapping_path),
        "run_table_sha256": _sha256(run_table),
        "runs": provenance_runs,
        "excluded": dropped,
        "nodes_used": sorted(set(needed_nodes)),
    }
    # `*_manifest.json` is on the analyzer's aux-skip list; a provenance file with
    # any other name would be picked up as the run table by the 00_input scan.
    (out_dir / "00_input" / "capture_manifest.json").write_text(
        json.dumps(prov, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "run_table": str(run_table),
        "doe_context": str(ctx_path),
        "rows": len(rows_out),
        "excluded": len(dropped),
        "factors": len(f_out),
        "responses": len(r_out),
        "covariates": len(c_out),
        "features": len(feature_cols),
        "data_stage": data_stage,
        "headers": headers,
    }


# ---------------------------------------------------------------- inspect

def inspect_export(export_dir: Path) -> dict:
    manifest, nodes = load_manifest(export_dir)
    out_nodes = []
    for nid, node in nodes.items():
        path = _node_file(export_dir, node)
        rows = read_node(path)
        vals = [r["value"] for r in rows if r["value"] is not None]
        states: dict[str, int] = {}
        for r in rows:
            states[r["state"]] = states.get(r["state"], 0) + 1
        out_nodes.append({
            "id": nid, "name": node.get("name"), "unit": node.get("unit"),
            "file": node.get("file"), "rows": len(rows),
            "range": node.get("range"), "observed_range": [min(vals), max(vals)] if vals else None,
            "states": states, "semantics": node.get("semantics") or "",
        })
    return {
        "schema": manifest.get("schema"), "export_id": manifest.get("export_id"),
        "window": manifest.get("window"), "lines": manifest.get("lines") or [],
        "totals": manifest.get("totals"), "nodes": out_nodes,
    }


# ---------------------------------------------------------------- cli

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("inspect", help="node inventory of one export")
    p.add_argument("--export", required=True)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("pivot", help="one export -> wide time-series CSV")
    p.add_argument("--export", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--names", choices=("id", "name"), default="id")
    p.add_argument("--format", choices=("iso", "ms"), default="iso")

    p = sub.add_parser("build", help="campaign -> run_table.csv + doe_context.json")
    p.add_argument("--capture-root", required=True)
    p.add_argument("--mapping", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--exclusions", default=None)
    p.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)
    try:
        if args.cmd == "inspect":
            rep = inspect_export(Path(args.export).resolve())
            if args.json:
                print(json.dumps(rep, ensure_ascii=False, indent=2))
            else:
                print(f"[capture] {rep['export_id']} nodes={len(rep['nodes'])} "
                      f"rows={sum(n['rows'] for n in rep['nodes'])}")
                for n in rep["nodes"]:
                    print(f"  {n['id']:<24} {str(n['unit'] or '-'):<6} rows={n['rows']:<6} "
                          f"range={n['observed_range']} {n['name']}")
            return 0
        if args.cmd == "pivot":
            rep = pivot_export(Path(args.export).resolve(), Path(args.out).resolve(),
                               names=args.names, fmt=args.format)
            print(f"[pivot] {rep['rows']} rows x {rep['columns']} cols -> {rep['out']}")
            return 0
        rep = build_capture(Path(args.capture_root).resolve(), Path(args.mapping).resolve(),
                            Path(args.out_dir).resolve(),
                            exclusions_path=(Path(args.exclusions).resolve()
                                             if args.exclusions else None))
        if args.json:
            print(json.dumps(rep, ensure_ascii=False))
        else:
            print(f"[capture] {rep['rows']} runs, {rep['excluded']} excluded, "
                  f"{rep['factors']} factors, {rep['responses']} responses, "
                  f"{rep['features']} feature cols, stage={rep['data_stage']}")
            print(f"[capture] {rep['run_table']}")
            print(f"[capture] {rep['doe_context']}")
        return 0
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
