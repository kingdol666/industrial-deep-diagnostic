"""img.py — image_stream shape module (WS4, M1 minimal path; frozen interface I9).

Two detectable input layouts:
  1. index CSV  — a time column + a column whose majority cells are relative
                  paths ending in an image extension (.png/.jpg/.jpeg/.bmp/
                  .tif/.tiff);
  2. directory stream — image files whose names embed a timestamp, with
     `time_ingest.extract_filename_timestamp` hit rate >= 90%.

extract (M1 whole-frame quality vector only, method_notes §1):
  MEAN, STD, ENTROPY (64-bin grayscale histogram Shannon entropy), SATFRAC
  (>250 pixel fraction), DARKFRAC (<5 pixel fraction), FOCUS (variance of the
  4-neighbour Laplacian [[0,1,0],[1,-4,1],[0,1,0]] response), plus one
  whole-source N column (successfully decoded frames).
Time anchoring: index CSV -> time column (explicit format catalog); directory
stream -> filename timestamp. When both exist per row they are compared and a
row deviating by more than one median sampling interval is dropped as
`ts_conflict` (counted in the manifest source reason).

M1 deliberately does NOT emit Q-*/RADIAL/AZIM/DIFF/DEFECT/SHIFT columns (plan
D9: without a calibration sidecar q-space quantities are forbidden) and does
NOT write thumbnails (M2 deep path: img_deep.py + objects thumbnails).

Pillow is a declared dependency (.claude/shared/scripts/pyproject.toml). A
missing Pillow is a LOUD failure, never a silent skip: detect() raises
RuntimeError("pillow missing: uv sync --project .claude/shared/scripts") so
build.py exits 1 at the detect stage — silently dropping images is exactly the
loss this skill exists to prevent.
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

# make the sibling `heterocore` package importable no matter how this file is
# loaded (build.py importlib load, run_tests harness, or direct import)
_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from heterocore import CONTRACT_VERSION  # noqa: E402
from heterocore import discover as disc  # noqa: E402
from heterocore import manifest as mani  # noqa: E402
from heterocore import naming  # noqa: E402
from heterocore import time_ingest as ting  # noqa: E402

SHAPE = "image_stream"
METHOD = "img_whole_frame_stats"
FEATURES = ("MEAN", "STD", "ENTROPY", "SATFRAC", "DARKFRAC", "FOCUS")
PROBE_ROWS = 50          # detect() reads metadata only (frozen I9)
DIR_TS_HIT_RATE = 0.90   # plan §3.1: filename-timestamp hit rate threshold
MIN_MAJOR_SHARE = 0.50   # "majority of cells" for the image-path column
_TIME_COL_NAMES = {"时间", "timestamp", "datetime", "time", "时间戳", "date", "日期"}

# column contract content (frozen I5 fields; physical meaning pinned to
# "whole-frame statistics, uncalibrated, detector frame" per plan §3.1 IMG row)
_FEATURE_META = {
    "MEAN": {
        "unit": "graylevel_8bit", "tag_cn": "整图灰度均值", "tag_en": "whole-frame gray mean",
        "formula": "mean(g) over all pixels; g = 8-bit grayscale frame",
        "physics_basis": "探测器线性区内整帧亮度与入射辐射/样品散射强度单调相关；未标定，仅作相对漂移监测",
        "meaning": "整图统计量（未标定、探测器坐标系）：全图像素灰度均值，整帧亮度水平代理",
    },
    "STD": {
        "unit": "graylevel_8bit", "tag_cn": "整图灰度标准差", "tag_en": "whole-frame gray std",
        "formula": "std(g, ddof=1) over all pixels",
        "physics_basis": "灰度标准差正比于整帧空间对比度，对环带宽度、缺陷等结构变化敏感",
        "meaning": "整图统计量（未标定、探测器坐标系）：全图像素灰度标准差（ddof=1），整帧对比度代理",
    },
    "ENTROPY": {
        "unit": "bit", "tag_cn": "整图灰度熵（64-bin）", "tag_en": "frame histogram entropy (64-bin)",
        "formula": "-sum(p_k*log2(p_k)); p_k = mass of the 64-bin histogram of g over [0,256)",
        "physics_basis": "直方图熵度量灰度分布分散度；结构增多（环变粗、缺陷出现）改变灰度质量分布从而改变熵",
        "meaning": "整图统计量（未标定、探测器坐标系）：64-bin 灰度直方图 Shannon 熵，整帧纹理/灰度分布复杂度代理",
    },
    "SATFRAC": {
        "unit": "fraction", "tag_cn": "过曝像素占比（>250）", "tag_en": "saturated pixel fraction (>250)",
        "formula": "mean(g > 250)",
        "physics_basis": "探测器满阱/ADC 上限截断不可恢复，饱和占比升高指示过曝或光源异常",
        "meaning": "整图统计量（未标定、探测器坐标系）：灰度>250 像素占比，饱和/过曝面积代理",
    },
    "DARKFRAC": {
        "unit": "fraction", "tag_cn": "欠曝像素占比（<5）", "tag_en": "dark pixel fraction (<5)",
        "formula": "mean(g < 5)",
        "physics_basis": "读出噪声底附近像元占比升高指示遮挡、快门或光路异常",
        "meaning": "整图统计量（未标定、探测器坐标系）：灰度<5 像素占比，欠曝/无信号面积代理",
    },
    "FOCUS": {
        "unit": "graylevel_8bit^2", "tag_cn": "整图对焦清晰度（Laplacian 方差）", "tag_en": "Laplacian focus variance",
        "formula": "var(L), L[i,j] = 4*g[i,j] - g[i-1,j] - g[i+1,j] - g[i,j-1] - g[i,j+1] (interior pixels)",
        "physics_basis": "Laplacian 高通能量集中于边缘；离焦或运动模糊使高频能量下降、响应方差随之下降（MIA 2014 告诫：与相机漂移协变，解释需谨慎）",
        "meaning": "整图统计量（未标定、探测器坐标系）：4 邻域 Laplacian 响应方差，整帧清晰度（离焦/运动模糊）代理",
    },
}
_N_META = {
    "unit": "count", "tag_cn": "成功解码帧数", "tag_en": "decoded frame count",
    "formula": "count of rows in IMG-<SLUG>.csv (decoded, time-anchored frames)",
    "physics_basis": "数据完整性计数，非过程量",
    "meaning": "成功解码且通过时间冲突检查的图像帧数（整源常量，非过程量）",
}


# ───────────────────────────── helpers ─────────────────────────────

def _ctx_get(ctx, key, default=None):
    """build.py passes its Ctx dataclass; I9 names the 2nd arg frame_hint:dict.
    Accept both."""
    if ctx is None:
        return default
    if isinstance(ctx, dict):
        return ctx.get(key, default)
    return getattr(ctx, key, default)


def _require_pillow() -> None:
    """Loud dependency failure (plan §3.1: 'Pillow 显式声明'; never silently
    skip images). build.py turns this into a detect-stage exit 1."""
    try:
        import PIL  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            f"pillow missing: uv sync --project .claude/shared/scripts "
            f"(PIL import failed: {exc})") from exc


def _read_rows(path: Path, max_rows: int | None = None) -> list[list[str]]:
    rows: list[list[str]] = []
    with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        for i, row in enumerate(csv.reader(f)):
            if max_rows is not None and i >= max_rows:
                break
            if row and any(str(c).strip() for c in row):
                rows.append(row)
    return rows


def _member_path(base: Path, cell: str) -> Path:
    c = str(cell).strip().strip('"').strip()
    p = Path(c)
    if p.is_absolute():
        return p
    return base / Path(c.replace("\\", "/"))


def _find_image_path_col(header: list[str], body: list[list[str]]) -> int | None:
    for ci in range(len(header)):
        cells = [str(r[ci]).strip() for r in body if ci < len(r) and str(r[ci]).strip()]
        if len(cells) < 2:
            continue
        hits = sum(1 for c in cells if Path(c.replace("\\", "/")).suffix.lower() in disc.IMAGE_EXTS)
        if hits / len(cells) > MIN_MAJOR_SHARE:
            return ci
    return None


def _find_time_col(header: list[str], body: list[list[str]]) -> int | None:
    best: tuple[tuple[int, int], int] | None = None
    for ci in range(len(header)):
        vals = [r[ci] if ci < len(r) else "" for r in body]
        if not any(str(v).strip() for v in vals):
            continue
        s = ting.parse_series(vals)
        if s["ok_rate"] < 0.9:
            continue
        named = str(header[ci]).strip().lower() in {n.lower() for n in _TIME_COL_NAMES}
        rank = (0 if named else 1, ci)
        if best is None or rank < best[0]:
            best = (rank, ci)
    return best[1] if best else None


def _median_gap_s(timestamps: list[datetime]) -> float | None:
    ts = sorted(t for t in timestamps if t is not None)
    gaps = [(b - a).total_seconds() for a, b in zip(ts, ts[1:]) if b > a]
    return float(sorted(gaps)[len(gaps) // 2]) if gaps else None


# ───────────────────────────── detect ─────────────────────────────

def detect(paths: list[Path], ctx) -> list[dict]:
    """Metadata-only detection (frozen I9). Returns [{'shape': 'image_stream',
    'spec': {...}}, ...]; spec.path is the claiming key (CSV file for index
    mode, the directory for directory mode)."""
    _require_pillow()
    taken = _ctx_get(ctx, "taken_slugs", {})

    csv_files, image_files = [], []
    for p in paths:
        try:
            if not Path(p).is_file():
                continue
        except OSError:
            continue
        ext = Path(p).suffix.lower()
        if ext in disc.TABLE_EXTS:
            csv_files.append(Path(p))
        elif ext in disc.IMAGE_EXTS:
            image_files.append(Path(p))

    detections: list[dict] = []
    claimed_images: set[str] = set()
    index_member_dirs: set[str] = set()

    # 1) index CSV mode — unambiguous time column + majority image-path column
    for csv_path in sorted(csv_files, key=str):
        spec = _detect_index_csv(csv_path, taken, claimed_images)
        if spec is None:
            continue
        index_member_dirs.add(str(Path(str(spec["members_sample_dir"])).resolve()))
        detections.append({"shape": SHAPE, "spec": spec})

    # 2) directory stream mode — unclaimed images, >=90% filename ts hit rate
    by_dir: dict[Path, list[Path]] = {}
    for img in image_files:
        if str(img) in claimed_images or str(img.resolve()) in index_member_dirs or img.parent in index_member_dirs:
            continue
        by_dir.setdefault(img.parent, []).append(img)
    for d in sorted(by_dir, key=str):
        members = sorted(by_dir[d], key=str)
        hits = sum(1 for m in members if ting.extract_filename_timestamp(m.name) is not None)
        if len(members) >= 2 and hits / len(members) >= DIR_TS_HIT_RATE:
            slug, sha6 = naming.unique_slug(d.name, d, taken)
            detections.append({"shape": SHAPE, "spec": {
                "source_id": slug, "slug": slug, "path_sha6": sha6,
                "path": str(d), "kind": "image_dir", "mode": "filename",
                "time_col": None, "path_col": None, "base_dir": str(d),
                "members": [str(m) for m in members],
                "n_sample": len(members), "sample_hit_rate": hits / len(members),
                "shape": SHAPE,
            }})
    return detections


def _detect_index_csv(csv_path: Path, taken, claimed_images: set[str]) -> dict | None:
    try:
        # claim requires the FULL member list (a probe cap would leave the tail
        # to the directory stream and double-count the same frames, observed on
        # an L5 60-frame index: probe claimed 50, dir claimed the other 10)
        rows = _read_rows(csv_path, max_rows=None)
    except OSError:
        return None
    if len(rows) < 2:
        return None
    header, body = rows[0], rows[1:]
    path_col = _find_image_path_col(header, body)
    if path_col is None:
        return None
    time_col = _find_time_col(header, body)
    # without a time column the CSV only qualifies via filename timestamps
    cells = [str(r[path_col]).strip() for r in body if path_col < len(r) and str(r[path_col]).strip()]
    if len(cells) < 2:
        return None
    fhits = sum(1 for c in cells if ting.extract_filename_timestamp(Path(c.replace("\\", "/")).name))
    if time_col is None and (fhits / len(cells)) < DIR_TS_HIT_RATE:
        return None
    mode = "index_csv" if time_col is not None else "filename"
    # claim the sampled members so a directory stream never double-counts them
    members = [_member_path(csv_path.parent, c) for c in cells]
    for m in members:
        claimed_images.add(str(m))
    slug, sha6 = naming.unique_slug(csv_path.stem, csv_path, taken)
    return {
        "source_id": slug, "slug": slug, "path_sha6": sha6,
        "path": str(csv_path), "kind": "image_index", "mode": mode,
        "time_col": header[time_col] if time_col is not None else None,
        "path_col": header[path_col],
        "base_dir": str(csv_path.parent),
        "members": [],                      # index mode re-reads the full CSV in extract
        "members_sample_dir": str(members[0].parent),
        "n_sample": len(body), "sample_hit_rate": fhits / len(cells),
        "shape": SHAPE,
    }


# ───────────────────────────── extract ─────────────────────────────

def extract(src: dict, ctx) -> dict:
    """Frozen I9. Returns {source, rows, contract, annotations, objects}."""
    _require_pillow()
    from PIL import Image  # local import: only needed when frames are decoded

    run_dir = _ctx_get(ctx, "run_dir", None)
    if run_dir is None:
        raise RuntimeError("image_stream extract requires ctx.run_dir")
    run_dir = Path(run_dir)
    slug = src["slug"]
    mode = src.get("mode", "index_csv")

    records = _collect_records(src)
    n_rows_in = len(records)

    # ambiguous date order -> refuse the source (plan §4: never guess)
    n_ambiguous = sum(1 for rec in records if rec["index_tv"] is not None
                      and "ambiguous_date_order" in rec["index_tv"].flags)
    if n_ambiguous:
        return {"source": _source_meta(src, mode, 0, None, None, None,
                                       reason=f"ambiguous_date_order={n_ambiguous}; source refused (never guess D/M vs M/D)"),
                "rows": None, "contract": [], "annotations": [], "objects": [], "notes": []}

    # ---- time anchoring -----------------------------------------------------
    n_unparsed = 0
    for rec in records:
        primary = rec["index_ts"] if mode == "index_csv" else rec["file_ts"]
        if primary is None:
            n_unparsed += 1
    gap_hint = _median_gap_s([rec["index_ts"] if mode == "index_csv" else rec["file_ts"]
                              for rec in records])

    n_conflict = 0
    if mode == "index_csv" and gap_hint:
        for rec in records:
            if rec["index_ts"] is not None and rec["file_ts"] is not None:
                if abs((rec["index_ts"] - rec["file_ts"]).total_seconds()) > gap_hint:
                    rec["drop"] = "ts_conflict"
                    n_conflict += 1

    # ---- decode + whole-frame features ---------------------------------------
    kept: list[dict] = []
    n_missing = n_decode_failed = 0
    for rec in records:
        if rec.get("drop") or rec["ts"] is None:
            continue
        if not rec["image"].exists():
            n_missing += 1
            continue
        feats = _frame_features(Image, rec["image"])
        if feats is None:
            n_decode_failed += 1
            continue
        rec["feats"] = feats
        kept.append(rec)
    kept.sort(key=lambda r: (r["ts"], r["order"]))

    n = len(kept)
    reason = (f"{SHAPE}/{mode}: rows_in={n_rows_in}; ts_conflict={n_conflict}; "
              f"unparsed_ts={n_unparsed}; missing_file={n_missing}; decode_failed={n_decode_failed}")

    if n == 0:
        meta = _source_meta(src, mode, 0, None, None, None, reason=reason)
        meta["disposition"] = "insufficient_data"
        return {"source": meta, "rows": None, "contract": [], "annotations": [], "objects": [], "notes": []}

    # ---- rows table (frozen I4 prefix; NO Q-*/RADIAL/AZIM by design) ---------
    import pandas as pd

    feat_cols = {f: naming.feature_column(SHAPE, slug, f) for f in FEATURES}
    n_col = naming.feature_column(SHAPE, slug, "N")
    data: dict = {"ts": [r["iso"] for r in kept],
                  "_src_ts": [r["iso"] for r in kept],
                  "n_inputs": [1] * n}
    for f in FEATURES:
        data[feat_cols[f]] = [r["feats"][f] for r in kept]
    data[n_col] = [n] * n
    rows = pd.DataFrame(data)

    # ---- object cards + provenance fingerprint (metadata only, M1) -----------
    obj_dir = run_dir / "07_hetero" / "objects" / slug
    objects: list[dict] = []
    for i, rec in enumerate(kept):
        card = {"file": str(rec["image"]), "sha256": mani.sha256_file(rec["image"]),
                "ts": rec["iso"], "width": rec["feats"]["width"], "height": rec["feats"]["height"],
                "pil_mode": rec["feats"]["pil_mode"], "downsample": None,
                "note": "M1 metadata-only object card; thumbnails are M2 (img_deep.py)"}
        mani.write_json_atomic(obj_dir / f"{i:06d}_{rec['image'].stem}.json", card)
        objects.append(card)

    source_path, source_sha256 = _source_anchor(src, mode, obj_dir, kept)

    # ---- contract (frozen I5, all fields) ------------------------------------
    cadence = _median_gap_s([r["ts"] for r in kept])
    span = (kept[-1]["ts"] - kept[0]["ts"]).total_seconds() if n > 1 else 0.0
    last_iso = kept[-1]["iso"]
    ts_source = "index" if mode == "index_csv" else "camera"
    common = {
        "shape": "IMG", "source_id": slug, "source_path": source_path,
        "source_sha256": source_sha256 or "",
        "role": "predictor_candidate", "evidence_level": 1,
        "evidence_level_basis": "direct whole-frame measurement of a retained source (L1)",
        "method": METHOD, "method_version": CONTRACT_VERSION,
        "n_inputs": n, "coverage": 0.0, "effective_n": n,
        "sparse": True, "stats_eligible": False,   # I8: vs anchor coverage; align (WS5) updates
        "cadence_s": cadence, "ts_source": ts_source, "tz": "naive_local",
        "clock_offset_s": 0.0, "model_derived": False, "insufficient_data": False,
        "_src_ts": last_iso,
    }
    contract = []
    for f in FEATURES:
        m = _FEATURE_META[f]
        contract.append({**common, "column": feat_cols[f], "unit": m["unit"],
                         "physical_meaning": m["meaning"], "formula": m["formula"],
                         "physics_basis": m["physics_basis"],
                         "tag_cn": m["tag_cn"], "tag_en": m["tag_en"]})
    contract.append({**common, "column": n_col, "role": "metadata", "unit": _N_META["unit"],
                     "physical_meaning": _N_META["meaning"], "formula": _N_META["formula"],
                     "physics_basis": _N_META["physics_basis"],
                     "tag_cn": _N_META["tag_cn"], "tag_en": _N_META["tag_en"]})

    meta = _source_meta(src, mode, n, cadence, span, _ts_format(src, records, mode),
                        reason=reason, fmt=_majority_format(kept))
    meta["features"] = [c["column"] for c in contract]
    meta["objects_dir"] = f"07_hetero/objects/{slug}"
    return {"source": meta, "rows": rows, "contract": contract,
            "annotations": [], "objects": objects, "notes": []}


# ─────────────────────── record collection (time) ───────────────────────

def _collect_records(src: dict) -> list[dict]:
    records: list[dict] = []
    if src.get("mode") == "index_csv":
        rows = _read_rows(Path(src["path"]))
        if not rows:
            return records
        header, body = rows[0], rows[1:]
        ti = header.index(src["time_col"]) if src.get("time_col") in header else None
        tp = header.index(src["path_col"]) if src.get("path_col") in header else None
        if tp is None:
            return records
        base = Path(src.get("base_dir") or Path(src["path"]).parent)
        for order, r in enumerate(body):
            cell = str(r[tp]).strip() if tp < len(r) else ""
            if not cell:
                continue
            itv = ting.parse_ts(r[ti]) if ti is not None and ti < len(r) else None
            records.append({
                "order": order,
                "image": _member_path(base, cell),
                "index_tv": itv,
                "index_ts": itv.ts if itv else None,
                "file_ts": ting.extract_filename_timestamp(Path(cell.replace("\\", "/")).name),
            })
    else:
        for order, m in enumerate(src.get("members", [])):
            records.append({
                "order": order, "image": Path(m), "index_tv": None, "index_ts": None,
                "file_ts": ting.extract_filename_timestamp(Path(m).name),
            })
    for rec in records:
        primary = rec["index_ts"] if src.get("mode", "index_csv") == "index_csv" else rec["file_ts"]
        rec["ts"] = primary
        rec["iso"] = primary.strftime("%Y-%m-%d %H:%M:%S") if primary else None
    return records


def _ts_format(src: dict, records: list[dict], mode: str) -> str | None:
    if mode == "index_csv":
        fmts = sorted({rec["index_tv"].fmt for rec in records if rec["index_tv"] and rec["index_tv"].fmt})
        return "|".join(fmts) if fmts else None
    return "filename_embedded"


def _source_meta(src: dict, mode: str, n: int, cadence, span, ts_format,
                 reason: str = "", fmt: str | None = None) -> dict:
    return {
        "source_id": src["source_id"], "path": str(src["path"]),
        "path_sha6": src["path_sha6"], "slug": src["slug"], "shape": SHAPE,
        "format": fmt or "image_stream", "n_snapshots": int(n),
        "cadence_s": cadence, "span_s": span, "ts_format": ts_format,
        "ts_source": "index" if mode == "index_csv" else "camera",
        "tz": "naive_local", "duplicate_key_policy": "aggregate",
        "anchor_coverage": None, "effective_n": int(n),
        "sparse": True, "stats_eligible": False,
        "disposition": "featured", "reason": reason,
        "features": [], "objects_dir": None,
    }


def _majority_format(kept: list[dict]) -> str:
    exts = sorted({rec["image"].suffix.lower().lstrip(".") or "bin" for rec in kept})
    return exts[0] if len(exts) == 1 else "mixed"


def _source_anchor(src: dict, mode: str, obj_dir: Path, kept: list[dict]) -> tuple[str, str | None]:
    """Provenance anchor recomputable by gate H3 (it hashes a single FILE):
    index mode -> the index CSV itself; directory mode -> a deterministic
    stream fingerprint card written under 07_hetero/objects/<SLUG>/ whose
    payload carries every member's own sha256 (auditable Merkle-style)."""
    if mode == "index_csv":
        p = Path(src["path"])
        return str(p), mani.sha256_file(p)
    members = sorted({str(rec["image"]) for rec in kept})
    payload = {
        "kind": "image_stream_directory",
        "dir": str(src["path"]),
        "n_members": len(members),
        "members": [{"file": Path(m).name, "bytes": Path(m).stat().st_size,
                     "sha256": mani.sha256_file(Path(m))} for m in members],
    }
    fp_path = obj_dir / "_stream_fingerprint.json"
    mani.write_json_atomic(fp_path, payload)
    return str(fp_path), mani.sha256_file(fp_path)


# ─────────────────────── whole-frame features ───────────────────────

def _frame_features(Image, path: Path) -> dict | None:
    """method_notes §1: ENTROPY = 64-bin grayscale histogram Shannon entropy;
    FOCUS = variance of the [[0,1,0],[1,-4,1],[0,1,0]] Laplacian response.
    Returns None on undecodable frames (caller counts decode_failed)."""
    try:
        with Image.open(path) as im:
            width, height = im.size
            pil_mode = im.mode
            g = np.asarray(im.convert("L"), dtype=np.float64)
    except Exception:
        return None
    if g.ndim != 2 or g.size == 0:
        return None
    hist, _ = np.histogram(g, bins=64, range=(0.0, 256.0))
    p = hist / float(hist.sum())
    nz = p[p > 0]
    entropy = float(-(nz * np.log2(nz)).sum())
    if g.shape[0] >= 3 and g.shape[1] >= 3:
        lap = (4.0 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1]
               - g[1:-1, :-2] - g[1:-1, 2:])
        focus = float(lap.var())
    else:
        focus = float("nan")
    return {
        "MEAN": float(g.mean()),
        "STD": float(g.std(ddof=1)) if g.size >= 2 else float("nan"),
        "ENTROPY": entropy,
        "SATFRAC": float((g > 250).mean()),
        "DARKFRAC": float((g < 5).mean()),
        "FOCUS": focus,
        "width": int(width), "height": int(height), "pil_mode": pil_mode,
    }
