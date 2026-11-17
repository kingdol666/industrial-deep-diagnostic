#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build.py — E-1H orchestrator (industrial-hetero-preprocessor).

Pipeline stage order (plan v1.1 §5): runs immediately AFTER the E-1 stage in
the SAME chained bash block of Step 0.5, so "stage skipped" can never masquerade
as "stage ran and found nothing".

CLI (frozen I1):
  uv run --project .claude/shared/scripts python build.py \
    --raw-path <file|dir> [--anchor <00_input/preprocessed_data.csv>] \
    [--run-dir RUN_DIR] [--config 07_hetero/hetero_config.json] \
    [--images-only] [--strict-no-rolling] [--enable-vlm] [--enable-llm] [--enable-pca]

Exit codes (frozen I2): 0 ok|no_hetero_sources, 1 hard error, 2 undetermined,
3 gate-fail, 4 raw_path_unresolved.

Shape modules are discovered dynamically from heterocore/shapes/*.py (interface
I9): adding a shape = adding a file; build.py never changes. Detection
precedence when several shapes claim the same file (unambiguous first):
  image_stream(index) > map > profile > text
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from heterocore import CONTRACT_VERSION  # noqa: E402
from heterocore import contracts as contracts_mod  # noqa: E402
from heterocore import discover as disc  # noqa: E402
from heterocore import manifest as mani  # noqa: E402
from heterocore import naming  # noqa: E402
from heterocore import time_ingest as ting  # noqa: E402

OUT_DIR = "07_hetero"
DETECT_PRECEDENCE = {"image_stream": 0, "map": 1, "profile": 2, "text": 3}


@dataclass
class Ctx:
    run_dir: Path
    raw_path: Path | None
    config: dict
    enable_vlm: bool = False
    enable_llm: bool = False
    enable_pca: bool = False
    strict_no_rolling: bool = True
    seed: int = 20261015
    taken_slugs: dict = field(default_factory=dict)


def load_shape_modules():
    shapes_dir = Path(__file__).resolve().parent / "heterocore" / "shapes"
    modules = []
    if not shapes_dir.is_dir():
        return modules
    for f in sorted(shapes_dir.glob("*.py")):
        if f.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"hetshape_{f.stem}", f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        modules.append(mod)
    return modules


def detect_anchor(anchor_path: Path | None) -> tuple[pd.DataFrame | None, str | None]:
    if anchor_path is None or not Path(anchor_path).exists():
        return None, None
    df = pd.read_csv(anchor_path, encoding="utf-8-sig", nrows=5)
    cols = list(df.columns)
    # reuse E-1's convention: the canonical table's time column is first/named 时间
    time_col = None
    for c in cols:
        if str(c).strip().lower() in ("时间", "timestamp", "datetime", "time", "时间戳"):
            time_col = c
            break
    if time_col is None:
        parsed = pd.to_datetime(df[cols[0]], errors="coerce", format="%Y-%m-%d %H:%M:%S")
        time_col = cols[0] if parsed.notna().any() else None
    return df, time_col


def count_rows(path: Path) -> int:
    with open(path, "rb") as f:
        return max(sum(1 for _ in f) - 1, 0)


def main() -> int:
    ap = argparse.ArgumentParser(description="E-1H: heterogeneous data preprocessing")
    ap.add_argument("--raw-path", default=None, help="original user data folder or file")
    ap.add_argument("--anchor", default=None, help="00_input/preprocessed_data.csv (E-1 output)")
    ap.add_argument("--run-dir", default=".", help="diagnostic run directory")
    ap.add_argument("--config", default=None, help="07_hetero/hetero_config.json")
    ap.add_argument("--images-only", action="store_true")
    ap.add_argument("--strict-no-rolling", action="store_true", default=True)
    ap.add_argument("--enable-vlm", action="store_true")
    ap.add_argument("--enable-llm", action="store_true")
    ap.add_argument("--enable-pca", action="store_true")
    ap.add_argument("--recursive", action="store_true", help="discover sources recursively")
    args = ap.parse_args()

    run_dir = Path(args.run_dir).resolve()
    out_dir = run_dir / OUT_DIR
    cfg = {}
    cfg_path = Path(args.config) if args.config else out_dir / "hetero_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(json.dumps({"status": "error", "reason": f"bad config {cfg_path}: {exc}"}))
            return 1
    if cfg.get("enabled") == "off":
        m = mani.base_manifest(run_dir, "off", None, None, 0, None, None, [])
        m["notes"].append("hetero disabled via config")
        mani.write_json_atomic(out_dir / "hetero_manifest.json", m)
        print(json.dumps({"status": "off"}))
        return 0

    raw_path, raw_source = disc.resolve_raw_path(args.raw_path, run_dir)
    if raw_path is None:
        # Never a silent no-op: without the raw folder we cannot know whether
        # images/notes exist (plan B1 / exit 4).
        print(json.dumps({"status": "error", "reason": "raw_path_unresolved",
                          "hint": "pass --raw-path or persist raw_data_path in run_config/input_manifest"}))
        return 4

    anchor_path = Path(args.anchor) if args.anchor else (run_dir / "00_input" / "preprocessed_data.csv")
    if not args.images_only and not anchor_path.exists():
        anchor_path = None
    anchor_df, anchor_time_col = detect_anchor(anchor_path) if anchor_path else (None, None)
    anchor_n = count_rows(anchor_path) if anchor_path and Path(anchor_path).exists() else 0
    anchor_columns = (list(pd.read_csv(anchor_path, encoding="utf-8-sig", nrows=0).columns)
                      if anchor_path and Path(anchor_path).exists() else None)

    # H7 pre-state: hashes of files we must never touch
    guard_files = []
    for rel in ("00_input/preprocessed_data.csv", "00_input/preprocessing_report.json",
                "00_input/run_config.json", "00_input/input_manifest.json"):
        f = run_dir / rel
        if f.exists():
            guard_files.append({"path": rel, "sha256": mani.sha256_file(f)})

    ctx = Ctx(run_dir=run_dir, raw_path=raw_path, config=cfg,
              enable_vlm=args.enable_vlm, enable_llm=args.enable_llm,
              enable_pca=args.enable_pca, strict_no_rolling=args.strict_no_rolling)

    try:
        candidates = disc.discover_sources(raw_path, recursive=args.recursive)
        # the anchor's RAW source table is by definition NOT a hetero source —
        # without this guard the text detector claims DCS tables whose batch-id
        # string column looks like free text (observed on L5 e2e). The anchor
        # file itself is E-1's OUTPUT (a re-serialization); the raw source path
        # lives in the preprocessing report's selected_table.
        anchor_sources: set[str] = set()
        if anchor_path is not None and Path(anchor_path).exists():
            anchor_sources.add(str(Path(anchor_path).resolve()))
            try:
                rep = json.loads((run_dir / "00_input" / "preprocessing_report.json").read_text(encoding="utf-8"))
                sel = ((rep.get("selected_table") or {}).get("file"))
                if sel:
                    sp = Path(sel)
                    # stability-mode audits record a raw-path-RELATIVE name
                    if not sp.is_absolute():
                        sp = Path(raw_path) / sp
                    anchor_sources.add(str(sp.resolve()))
            except Exception:
                pass
            candidates = [p for p in candidates if str(p.resolve()) not in anchor_sources]
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": f"discover failed: {exc}"}))
        return 1

    detections: list[dict] = []
    for mod in load_shape_modules():
        try:
            found = mod.detect(candidates, ctx) or []
        except Exception as exc:
            print(json.dumps({"status": "error", "reason": f"detect failed in {mod.__name__}: {exc}"}))
            return 1
        for d in found:
            d["_module"] = mod.__name__
            detections.append(d)

    # one file feeds exactly one shape: unambiguous shape wins; a module may
    # UPGRADE an existing claim of the same shape (meta["upgrade"]=true, used by
    # the calibrated deep-image path to take over from the minimal image path)
    claimed: dict[str, dict] = {}
    for d in sorted(detections, key=lambda x: (DETECT_PRECEDENCE.get(x.get("shape", ""), 9),
                                               1 if x.get("meta", {}).get("upgrade") else 0)):
        key = str(d["spec"]["path"])
        if key not in claimed or (d.get("meta", {}).get("upgrade")
                                  and d.get("shape") == claimed[key].get("shape")):
            claimed[key] = d
    assignments = list(claimed.values())

    written: list[str] = []

    if not assignments:
        status = "no_hetero_sources"
        manifest = mani.base_manifest(run_dir, status, anchor_path if anchor_path.exists() else None,
                                      anchor_time_col, anchor_n,
                                      raw_path, raw_source, guard_files)
        manifest["anchor"]["columns"] = anchor_columns
        manifest["time_ingest"]["formats"] = ting.FORMATS
        manifest["notes"].append("no heterogeneous sources detected in raw path")
        mani.write_json_atomic(out_dir / "hetero_manifest.json", manifest)
        written.append(f"{OUT_DIR}/hetero_manifest.json")
        manifest["h7_guard"]["written"] = written
        mani.write_json_atomic(out_dir / "hetero_manifest.json", manifest)
        print(json.dumps({"status": status, "sources": 0, "manifest": str(out_dir / "hetero_manifest.json")}))
        return 0

    # ---- extract per source ------------------------------------------------
    contract_rows: list[dict] = []
    feature_frames: dict[str, pd.DataFrame] = {}
    annotations: list[dict] = []
    objects: list[dict] = []
    manifest_sources: list[dict] = []
    max_age_factor = float(cfg.get("max_age_factor", 3.0))
    images_only = args.images_only and all(d["shape"] == "image_stream" for d in assignments)

    for d in sorted(assignments, key=lambda x: DETECT_PRECEDENCE.get(x.get("shape", ""), 9)):
        mod = _module_by_name(d["_module"])
        try:
            result = mod.extract(d["spec"], ctx)
        except Exception as exc:
            manifest_sources.append({"source_id": d["spec"].get("source_id", "?"),
                                     "path": str(d["spec"]["path"]),
                                     "shape": d.get("shape", "?"),
                                     "disposition": "skipped",
                                     "reason": f"extract failed: {exc}"})
            continue
        src_meta = result["source"]
        src_meta.setdefault("disposition", "featured")
        src_meta.setdefault("reason", "")
        manifest_sources.append(src_meta)
        rows = result.get("rows")
        if rows is not None and len(rows):
            fname = f"{naming.SHAPE_CODES.get(src_meta['shape'], src_meta['shape'].upper()[:3])}-{src_meta['slug']}.csv"
            fpath = out_dir / "features" / fname
            mani.write_csv_atomic(fpath, rows)
            written.append(f"{OUT_DIR}/features/{fname}")
            feature_frames[src_meta["source_id"]] = rows
        contract_rows.extend(result.get("contract", []))
        annotations.extend(result.get("annotations", []))
        objects.extend(result.get("objects", []))

    # ---- fill contract defaults + naming gate ------------------------------
    for col in contract_rows:
        col.setdefault("model_derived", False)
        col.setdefault("insufficient_data", False)
        col.setdefault("sparse", True)
        col.setdefault("stats_eligible", False)
        col.setdefault("coverage", 0.0)
        col.setdefault("effective_n", 0)
        col.setdefault("evidence_level", 1)
        col.setdefault("evidence_level_basis", "direct measurement of a retained source (L1); see method_notes for derived-feature levelling")
        col.setdefault("method_version", CONTRACT_VERSION)
    bad_names = [c["column"] for c in contract_rows if not naming.validate_column_name(c["column"])]

    # ---- contract + explicit_cols ------------------------------------------
    contract_doc = {
        "contract_version": CONTRACT_VERSION,
        "generated_at": mani.now_iso(),
        "anchor_sha256": mani.sha256_file(anchor_path) if anchor_path and Path(anchor_path).exists() else None,
        "columns": contract_rows,
    }
    explicit = contracts_mod.derive_explicit_cols(contract_doc)
    mani.write_json_atomic(out_dir / "column_contract.json", contract_doc)
    mani.write_json_atomic(out_dir / "explicit_cols.json", explicit)
    written += [str(out_dir / "column_contract.json"), str(out_dir / "explicit_cols.json")]

    if annotations:
        mani.write_json_atomic(out_dir / "annotations.json", annotations)
        written.append(f"{OUT_DIR}/annotations.json")

    # ---- join onto anchor ---------------------------------------------------
    joined_rel = None
    if not images_only and anchor_df is not None:
        from heterocore import align as align_mod

        try:
            full_anchor = pd.read_csv(anchor_path, encoding="utf-8-sig")
            joined, contract_updates = align_mod.anchor_join(
                full_anchor, feature_frames,
                {"max_age_factor": max_age_factor,
                 "duplicate_key_policy": cfg.get("duplicate_key_policy", "aggregate"),
                 "transport_lag_s": cfg.get("transport_lag_s", {}),
                 "anchor_time_col": anchor_time_col,
                 "contract_rows": contract_rows})
            merged = {c["column"]: c for c in contract_rows}
            for upd in contract_updates:
                if upd["column"] in merged:
                    merged[upd["column"]].update(upd)
            contract_doc["columns"] = list(merged.values())
            explicit = contracts_mod.derive_explicit_cols(contract_doc)
            mani.write_json_atomic(out_dir / "column_contract.json", contract_doc)
            mani.write_json_atomic(out_dir / "explicit_cols.json", explicit)
            jname = "preprocessed_images_only.csv" if images_only else "preprocessed_data_hetero.csv"
            jpath = out_dir / jname
            mani.write_csv_atomic(jpath, joined)
            written.append(f"{OUT_DIR}/{jpath.name}")
            joined_rel = f"{OUT_DIR}/{jname}"
        except align_mod.AlignNotAvailable:
            joined_rel = None
        except Exception as exc:
            print(json.dumps({"status": "error", "reason": f"align failed: {exc}"}))
            return 1
    elif images_only:
        # images-only: the feature table itself is the analysis table
        sid = next(iter(feature_frames), None)
        if sid is not None:
            jpath = out_dir / "preprocessed_images_only.csv"
            mani.write_csv_atomic(jpath, feature_frames[sid])
            written.append(f"{OUT_DIR}/{jpath.name}")
            joined_rel = f"{OUT_DIR}/preprocessed_images_only.csv"

    # ---- always-marker manifest (last write) --------------------------------
    status = "ok" if any(s.get("disposition") == "featured" for s in manifest_sources) else "no_hetero_sources"
    manifest = mani.base_manifest(
        run_dir, status, anchor_path if anchor_path and Path(anchor_path).exists() else None,
        anchor_time_col, anchor_n, raw_path, raw_source, guard_files)
    manifest["anchor"]["columns"] = anchor_columns
    manifest["sources"] = manifest_sources
    manifest["outputs"]["joined_table"] = joined_rel
    manifest["outputs"]["annotations"] = "07_hetero/annotations.json" if annotations else None
    manifest["outputs"]["objects_dir"] = "07_hetero/objects" if objects else None
    manifest["alignment"]["max_age_factor"] = max_age_factor
    manifest["time_ingest"]["formats"] = ting.FORMATS
    if images_only:
        manifest["notes"].append("images-only run: no process tags; analysis table is the derived image-feature series")
    manifest["h7_guard"]["written"] = written
    mani.write_json_atomic(out_dir / "hetero_manifest.json", manifest)

    print(json.dumps({"status": status, "sources": len(manifest_sources),
                      "columns": len(contract_rows), "joined_table": joined_rel,
                      "manifest": str(out_dir / "hetero_manifest.json")}, ensure_ascii=False))
    return 0


_module_cache: dict[str, object] = {}


def _module_by_name(name: str):
    if name not in _module_cache:
        path = Path(name)
        if not path.exists():
            # module was registered by its __name__ ("hetshape_<stem>")
            stem = name.split("_", 1)[1] if "_" in name else name
            path = Path(__file__).resolve().parent / "heterocore" / "shapes" / f"{stem}.py"
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _module_cache[name] = mod
    return _module_cache[name]


if __name__ == "__main__":
    sys.exit(main())
