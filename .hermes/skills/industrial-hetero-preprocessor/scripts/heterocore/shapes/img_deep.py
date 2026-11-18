"""img_deep.py — image_stream DEEP path (WS10, plan v1.1 §3.1 IMG row / M2).

Upgrade mechanism (build.py claim rule): this module re-detects the SAME two
image-stream layouts as the M1 minimal path (shapes/img.py) but claims a source
ONLY when a calibration sidecar exists, and marks the claim
``meta={"upgrade": true}`` so it TAKES OVER the file from img.py. Without a
valid sidecar this module returns [] and the M1 minimal path keeps the source —
"无标定即无深路径" (plan D9: without calibration, q-space quantities are
forbidden and must never be invented).

Sidecar lookup order (frozen):
  1. ctx.config["detector_json"] (explicit path);
  2. ``detector.json`` beside the source (index-CSV directory / image directory);
  3. ``detector.json`` in the raw-path root.
Required fields: pixel_size_um, beam_center_px [cx, cy], detector_distance_mm,
wavelength_angstrom. The FIRST existing candidate file is THE sidecar; if it
misses any field or fails validation the deep path refuses the source (never
guesses a replacement).

extract (all deterministic numpy/scipy, zero LLM/network):
  Q-RADIAL-P<k>   k=1..8  pixel-radius bins around beam_center, bin width
                          bin_w = max(1, round(min(h, w)/64)) fixed by the first
                          decoded frame; bin mean of grayscale; only bins FULLY
                          inside the frame are kept (outer radius <= distance
                          from beam center to the nearest edge). Calibrated
                          columns are named Q-* and carry the q position of the
                          bin mid-radius:
                          q = 4*pi*sin(theta)/lambda,
                          theta = atan(r*pixel_size_um/1000/detector_distance_mm)/2
                          (small-angle linearization q ~= 2*pi*r*p/(lambda*d)
                          corresponds).
  Q-AZIM-P<k>     k=1..8  azimuthal 45-degree sector means (radius <= half the
                          fully-inside radius); q reported at the sector's
                          outer radius.
  DIFF-RMSE               sqrt(mean((g - ref_median)^2)) vs the in-control
                          reference frame (per-pixel median of the frames inside
                          config["in_control_window"], or of the first 20% of
                          snapshots — precomputed ONCE, O(n) overall).
  DEFECT-COUNT            per-pixel robust z = (g - ref_median)/max(ref_MAD, 1
                          graylevel) with |z| > 5; connected components
                          (scipy.ndimage.label, 8-connectivity) with component
                          area >= 8 px are defects; count of such components.
  DEFECT-AREA-FRAC        defect pixels (components >= 8 px) / all pixels.
  SHIFT-X / SHIFT-Y       registration drift: exhaustive cross-correlation of
                          the frame vs the reference over +/-10 px (coarse
                          search on the 4x block-mean image, full-resolution
                          refinement in a +/-4 px window; positive = frame
                          content displaced toward +x / +y vs reference).
  N                       decoded & time-anchored frame count (whole source).

rows: ts, _src_ts, n_inputs, <all deep feature columns>, N.
objects: per-frame card (file/sha256/ts/width/height/calibration params) plus
PNG thumbnails <= 200 (64x64, stride-sampled frames) under
07_hetero/objects/<SLUG>/thumbs/ (vlm_image_reader reads png/jpg only).

Complexity discipline (500-frame pressure): every frame is decoded exactly
twice (features pass + diff/defect/shift pass); the reference statistics and
both downsampled references are precomputed once; every per-frame step is
O(pixels) — no O(n^2) anywhere; memory stays O(reference window).
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import numpy as np  # noqa: E402

from heterocore import CONTRACT_VERSION  # noqa: E402
from heterocore import manifest as mani  # noqa: E402
from heterocore import naming  # noqa: E402
from heterocore import time_ingest as ting  # noqa: E402

SHAPE = "image_stream"
METHOD = "img_deep_calibrated (radial/azimuthal binning + in-control reference diff/defect/registration-shift)"
SIDECAR_NAME = "detector.json"

N_RADIAL_BINS = 8
N_AZIM_SECTORS = 8
REF_FALLBACK_FRAC = 0.2          # first-20% snapshots when no in_control_window
REF_BUFFER_CAP_BYTES = 256 << 20  # stop buffering reference frames beyond this
ROBUST_Z_THRESHOLD = 5.0
DEFECT_MIN_AREA_PX = 8   # noise-cluster evidence (P4deep fixture): max 5 px across 50 clean frames; a radius-3 defect spot is ~29 px
MAD_FLOOR = 1.0                   # graylevel floor: MAD below 1 level cannot scale z
SHIFT_SEARCH_PX = 10
SHIFT_DS_FACTOR = 4
EPS = 1e-12

THUMB_MAX = 200
THUMB_SIZE = 64

_MIN_MOD: object = None           # lazily loaded M1 module (img.py)
_GRID_CACHE: dict = {}            # (h, w, bin_w, cx, cy) -> precomputed index maps
_GRID_CACHE_MAX = 32


# ───────────────────────── M1 module (reuse, never fork) ─────────────────────────

def _img_min():
    """Load shapes/img.py the same way build.py loads shape modules."""
    global _MIN_MOD
    if _MIN_MOD is None:
        path = Path(__file__).resolve().parent / "img.py"
        spec = importlib.util.spec_from_file_location("hetshape_img_min_for_deep", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MIN_MOD = mod
    return _MIN_MOD


def _ctx_get(ctx, key, default=None):
    if ctx is None:
        return default
    if isinstance(ctx, dict):
        return ctx.get(key, default)
    return getattr(ctx, key, default)


# ───────────────────────────── calibration sidecar ─────────────────────────────

def _sidecar_candidates(spec: dict, ctx):
    cfg = _ctx_get(ctx, "config", {}) or {}
    key = cfg.get("detector_json")
    if key:
        yield Path(str(key))
    base = spec.get("base_dir") or str(Path(str(spec["path"])).parent)
    yield Path(str(base)) / SIDECAR_NAME
    raw = _ctx_get(ctx, "raw_path", None)
    if raw:
        yield Path(str(raw)) / SIDECAR_NAME


def _validate_sidecar(data) -> dict | None:
    """All four calibration fields must be present, finite and positive."""
    if not isinstance(data, dict):
        return None
    try:
        px = float(data["pixel_size_um"])
        dist = float(data["detector_distance_mm"])
        lam = float(data["wavelength_angstrom"])
        cx_raw, cy_raw = data["beam_center_px"]
        cx, cy = float(cx_raw), float(cy_raw)
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    vals = (px, dist, lam, cx, cy)
    if not all(math.isfinite(v) for v in vals) or px <= 0 or dist <= 0 or lam <= 0:
        return None
    return {"pixel_size_um": px, "beam_center_px": [cx, cy],
            "detector_distance_mm": dist, "wavelength_angstrom": lam}


def _find_calibration(spec: dict, ctx) -> dict | None:
    """First EXISTING sidecar candidate wins; an existing-but-invalid sidecar
    REFUSES the deep path (never guesses a replacement file)."""
    for cand in _sidecar_candidates(spec, ctx):
        if cand.is_file():
            try:
                data = json.loads(cand.read_text(encoding="utf-8"))
            except Exception:
                return None
            cal = _validate_sidecar(data)
            if cal is None:
                return None
            cal["sidecar_path"] = str(cand)
            cal["sidecar_sha256"] = mani.sha256_file(cand)
            return cal
    return None


def q_of_radius_px(r_px: float, cal: dict) -> float:
    """q = 4*pi*sin(theta)/lambda, theta = atan(r*pixel_size_um/1000 /
    detector_distance_mm)/2 (exact arctan form; the small-angle linearization
    q ~= 2*pi*r*p/(lambda*d) corresponds)."""
    r_mm = float(r_px) * float(cal["pixel_size_um"]) / 1000.0
    theta = 0.5 * math.atan(r_mm / float(cal["detector_distance_mm"]))
    return 4.0 * math.pi * math.sin(theta) / float(cal["wavelength_angstrom"])


# ───────────────────────────── detect (upgrade claim) ─────────────────────────────

def detect(paths: list, ctx) -> list:
    """Same two layouts as img.py, but claim ONLY with a valid calibration
    sidecar, and mark meta={"upgrade": true} so build.py lets this module take
    the file over from the M1 minimal path. No sidecar => [] (M1 keeps it)."""
    min_mod = _img_min()
    min_mod._require_pillow()
    out: list[dict] = []
    for base in min_mod.detect(paths, ctx) or []:
        cal = _find_calibration(base["spec"], ctx)
        if cal is None:
            continue                      # D9: no calibration -> no deep path
        spec = dict(base["spec"])
        spec["calibration"] = cal
        out.append({"shape": SHAPE, "spec": spec, "meta": {"upgrade": True}})
    return out


# ───────────────────────────── geometry index maps ─────────────────────────────

def _geometry(h: int, w: int, bin_w: int, cx: float, cy: float) -> dict:
    """Per-frame-geometry precomputed maps: radial bin index (0..7 valid,
    8=sentinel beyond the feature range), per-bin pixel counts, azimuth sector
    index (0..7 valid, 8=outside the sector radius), sector counts, the
    fully-inside radius. Cached per distinct geometry (bounded)."""
    key = (h, w, bin_w, cx, cy)
    hit = _GRID_CACHE.get(key)
    if hit is not None:
        return hit
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(yy - cy, xx - cx)
    r_in = float(min(cx, (w - 1) - cx, cy, (h - 1) - cy))  # inscribed-circle radius (px)
    bidx = np.floor(r / bin_w).astype(np.int64)
    bidx[bidx >= N_RADIAL_BINS] = N_RADIAL_BINS
    kept_bins = [k for k in range(N_RADIAL_BINS) if (k + 1) * bin_w <= r_in + EPS]
    bcnt = np.bincount(bidx.ravel(), minlength=N_RADIAL_BINS + 1)
    r_azim = r_in / 2.0                                    # "半径取有效区一半"
    theta = np.arctan2(yy - cy, xx - cx)
    sector = np.floor((theta + np.pi) / (np.pi / N_AZIM_SECTORS)).astype(np.int64)
    sector = np.clip(sector, 0, N_AZIM_SECTORS - 1)
    sidx = np.where(r <= r_azim, sector, N_AZIM_SECTORS)
    scnt = np.bincount(sidx.ravel(), minlength=N_AZIM_SECTORS + 1)
    geo = {"bidx": bidx.ravel(), "bcnt": bcnt, "kept_bins": kept_bins,
           "sidx": sidx.ravel(), "scnt": scnt, "r_in": r_in, "r_azim": r_azim}
    if len(_GRID_CACHE) >= _GRID_CACHE_MAX:
        _GRID_CACHE.clear()
    _GRID_CACHE[key] = geo
    return geo


def _bin_means(g: np.ndarray, geo: dict) -> tuple[np.ndarray, np.ndarray]:
    """O(pixels): two bincounts give the 8 radial + 8 azimuthal bin means."""
    flat = g.ravel()
    bsum = np.bincount(geo["bidx"], weights=flat, minlength=N_RADIAL_BINS + 1)
    ssum = np.bincount(geo["sidx"], weights=flat, minlength=N_AZIM_SECTORS + 1)
    rad = np.full(N_RADIAL_BINS, np.nan)
    azim = np.full(N_AZIM_SECTORS, np.nan)
    for k in geo["kept_bins"]:
        c = int(geo["bcnt"][k])
        if c > 0:
            rad[k] = bsum[k] / c
    for k in range(N_AZIM_SECTORS):
        c = int(geo["scnt"][k])
        if c > 0:
            azim[k] = ssum[k] / c
    return rad, azim


# ───────────────────────────── reference frame selection ─────────────────────────────

def _ref_indices(candidates: list[dict], cfg: dict) -> tuple[list[int], str]:
    """Snapshot positions (into the time-sorted candidate list) used to build
    the in-control reference: config in_control_window {start, end} when
    declared AND matching, else the first REF_FALLBACK_FRAC of snapshots."""
    n = len(candidates)
    icw = (cfg or {}).get("in_control_window") or {}
    start = ting.parse_ts(icw.get("start")).ts if icw.get("start") else None
    end = ting.parse_ts(icw.get("end")).ts if icw.get("end") else None
    if start is not None or end is not None:
        idx = [i for i, r in enumerate(candidates)
               if ((start is None or r["ts"] >= start) and (end is None or r["ts"] <= end))]
        if idx:
            return idx, "in_control_window"
        return list(range(max(1, int(round(REF_FALLBACK_FRAC * n))))), "first20pct(empty_window_fallback)"
    return list(range(max(1, int(round(REF_FALLBACK_FRAC * n))))), "first20pct"


# ───────────────────────────── shift / defect estimators ─────────────────────────────

def _downsample4(a: np.ndarray) -> np.ndarray:
    h, w = a.shape
    h2, w2 = h - h % SHIFT_DS_FACTOR, w - w % SHIFT_DS_FACTOR
    if h2 < 1 or w2 < 1:
        return a
    a = a[:h2, :w2]
    f = SHIFT_DS_FACTOR
    return a.reshape(h2 // f, f, w2 // f, f).mean(axis=(1, 3))


def _ncc_flat(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:               # mixed frame sizes vs reference
        return -1.0
    am = a.ravel() - a.mean()
    bm = b.ravel() - b.mean()
    da = math.sqrt(float((am * am).sum()))
    db = math.sqrt(float((bm * bm).sum()))
    if da < EPS or db < EPS:
        return -1.0
    return float((am * bm).sum() / (da * db))


def _ncc_at(g: np.ndarray, ref: np.ndarray, dy: int, dx: int) -> float:
    """Normalized correlation of g vs ref under content displacement (dx, dy):
    g[y, x] compared with ref[y - dy, x - dx] over the in-bounds overlap."""
    h, w = g.shape
    a = g[max(0, dy): h + min(0, dy), max(0, dx): w + min(0, dx)]
    b = ref[max(0, -dy): h + min(0, -dy), max(0, -dx): w + min(0, -dx)]
    return _ncc_flat(a, b)


def _estimate_shift(g: np.ndarray, ref: np.ndarray, ref_ds: np.ndarray | None) -> tuple[int, int]:
    """Exhaustive +/-SHIFT_SEARCH_PX integer search: coarse pass on the 4x
    block-mean images (4-px grid, covers +/-8), then full-resolution refinement
    in a +/-4 px window (clamped to +/-10) — the reported shift is an exact
    original-pixel integer (grid point nearest any true peak is at most 2 px
    away per axis, so the refine window always contains it)."""
    lo, hi = -SHIFT_SEARCH_PX, SHIFT_SEARCH_PX

    def refine(cy0: int, cx0: int) -> tuple[int, int]:
        best_s, best = -2.0, (0, 0)
        for dy in range(max(lo, cy0 - SHIFT_DS_FACTOR), min(hi, cy0 + SHIFT_DS_FACTOR) + 1):
            for dx in range(max(lo, cx0 - SHIFT_DS_FACTOR), min(hi, cx0 + SHIFT_DS_FACTOR) + 1):
                s = _ncc_at(g, ref, dy, dx)
                if s > best_s:
                    best_s, best = s, (dy, dx)
        return best

    h, w = g.shape
    if ref_ds is not None and min(h, w) >= SHIFT_DS_FACTOR * 4:
        g_ds = _downsample4(g)
        best_s, c = -2.0, (0, 0)
        step = SHIFT_DS_FACTOR
        rng = max(1, SHIFT_SEARCH_PX // step)
        for dy in range(-rng * step, rng * step + 1, step):
            for dx in range(-rng * step, rng * step + 1, step):
                s = _ncc_at(g_ds, ref_ds, dy // step, dx // step)
                if s > best_s:
                    best_s, c = s, (dy, dx)
        return refine(c[0], c[1])
    return refine(0, 0)


def _defect_stats(g: np.ndarray, med: np.ndarray, mad: np.ndarray) -> tuple[int, float]:
    """|z| > 5 with z = (g - median)/max(MAD, 1 graylevel); 8-connected
    components with area >= DEFECT_MIN_AREA_PX are defects (small isolated
    clusters are estimation noise of the 12-sample per-pixel MAD, not
    defects). Returns (count, area_fraction)."""
    z = (g - med) / np.maximum(mad, MAD_FLOOR)
    mask = np.abs(z) > ROBUST_Z_THRESHOLD
    if not mask.any():
        return 0, 0.0
    from scipy import ndimage  # lazy: only needed when candidate defect pixels exist

    lbl, nlab = ndimage.label(mask, structure=np.ones((3, 3), dtype=int))
    if nlab == 0:
        return 0, 0.0
    areas = np.bincount(lbl.ravel())[1:]
    keep = areas >= DEFECT_MIN_AREA_PX
    count = int(keep.sum())
    area_px = int(areas[keep].sum())
    return count, area_px / float(g.size)


# ───────────────────────────── column contract content ─────────────────────────────

def _column_meta(cal: dict | None, bin_w: int, geo: dict) -> list[dict]:
    """One entry per emitted feature column, in frame order (frozen I5 fields)."""
    calibrated = cal is not None
    q_prefix = "Q-" if calibrated else ""
    unit_q = "1/Å" if calibrated else None
    sidecar_txt = ""
    if calibrated:
        sidecar_txt = (f" 标定来源 {Path(cal['sidecar_path']).name} "
                       f"sha256={cal.get('sidecar_sha256') or 'unavailable'}")
    r_azim = geo["r_azim"]
    q_azim = q_of_radius_px(r_azim, cal) if calibrated else None

    cols: list[dict] = []
    for k in range(N_RADIAL_BINS):
        lo, hi = k * bin_w, (k + 1) * bin_w
        if calibrated:
            r_mid = (k + 0.5) * bin_w
            q_k = q_of_radius_px(r_mid, cal)
            formula = (f"value = mean grayscale of pixels with radius r in [{lo},{hi}) px from beam_center; "
                       f"bin position q_k = 4π·sin(θ)/λ, θ = atan(r·pixel_size_um/1000/detector_distance_mm)/2 "
                       f"= {q_k:.6g} 1/Å at mid-radius r={r_mid:.1f}px "
                       f"(small-angle: q ≈ 2π·r·p/(λ·d)); bins not fully inside the frame are NaN")
            meaning = f"标定 q 空间径向分箱强度 P{k + 1}（bin [{lo},{hi}) px）：衍射环位置/强度随时间的漂移代理"
        else:
            formula = (f"value = mean grayscale of pixels with radius r in [{lo},{hi}) px from beam_center; "
                       f"未标定（无 sidecar），禁止 Q-* 命名（D9）；不完全落在图内的 bin 为 NaN")
            meaning = f"像素半径分箱均值 P{k + 1}（bin [{lo},{hi}) px，未标定探测器坐标系）"
        cols.append({
            "feature": f"{q_prefix}RADIAL-P{k + 1}", "unit": unit_q,
            "tag_cn": f"径向分箱均值 P{k + 1}" + ("（q 空间标定）" if calibrated else "（像素）"),
            "tag_en": f"radial bin mean P{k + 1}" + (" (calibrated q-space)" if calibrated else " (pixel)"),
            "formula": formula,
            "physics_basis": "衍射/散射环的径向强度分布；环半径与宽度漂移反映晶格参数、应力或几何变化" + sidecar_txt,
            "meaning": meaning,
        })
    for k in range(N_AZIM_SECTORS):
        lo_deg, hi_deg = k * 45, (k + 1) * 45
        if calibrated:
            formula = (f"value = mean grayscale of pixels with radius ≤ {r_azim:.2f} px and azimuth in "
                       f"[{lo_deg}°,{hi_deg}°) from beam_center (atan2, 0°=+x); sector position q = "
                       f"4π·sin(θ)/λ = {q_azim:.6g} 1/Å at the sector outer radius (representative)")
            meaning = f"标定方位角扇区均值 P{k + 1}（[{lo_deg}°,{hi_deg}°)）：衍射环各向异性/织构漂移代理"
        else:
            formula = (f"value = mean grayscale of pixels with radius ≤ {r_azim:.2f} px and azimuth in "
                       f"[{lo_deg}°,{hi_deg}°) from beam_center; 未标定（无 sidecar），禁止 Q-* 命名（D9）")
            meaning = f"方位角扇区均值 P{k + 1}（[{lo_deg}°,{hi_deg}°)，未标定探测器坐标系）"
        cols.append({
            "feature": f"{q_prefix}AZIM-P{k + 1}", "unit": unit_q,
            "tag_cn": f"方位角扇区均值 P{k + 1}" + ("（q 空间标定）" if calibrated else "（像素）"),
            "tag_en": f"azimuthal sector mean P{k + 1}" + (" (calibrated q-space)" if calibrated else " (pixel)"),
            "formula": formula,
            "physics_basis": "方位角强度分布对织构/各向异性敏感；扇区间差异变化指示择优取向或局部缺陷" + sidecar_txt,
            "meaning": meaning,
        })
    cols.append({
        "feature": "DIFF-RMSE", "unit": None,
        "tag_cn": "参考帧差 RMSE", "tag_en": "reference-frame difference RMSE",
        "formula": "sqrt(mean((g - ref_median)^2)) over all pixels; ref_median = per-pixel median of "
                   "in-control reference frames (config in_control_window, else first 20% of snapshots)",
        "physics_basis": "整帧残差能量相对 in-control 参考帧（逐像素中位数基线）的升高指示环强度/位置漂移或缺陷出现；"
                         "逐像素基线消去静态背景与固定纹理，比整图 MEAN/STD 更抗光照共模漂移（MIA 2014 告诫）",
        "meaning": "当前帧相对 in-control 参考帧（逐像素中位数）的整帧 RMSE：帧间漂移能量代理",
    })
    cols.append({
        "feature": "DEFECT-COUNT", "unit": None,
        "tag_cn": "缺陷连通域计数", "tag_en": "defect component count",
        "formula": f"count of 8-connected components (scipy.ndimage.label) of |z| > {ROBUST_Z_THRESHOLD:g} "
                   f"with component area >= {DEFECT_MIN_AREA_PX} px; "
                   f"z = (g - ref_median)/max(ref_MAD, {MAD_FLOOR:g} graylevel), per-pixel reference statistics",
        "physics_basis": "逐像素稳健 z 对每像元自身噪声水平归一：孤立单像元噪声尖峰不计数（面积门限），"
                         "成片亮点/暗点缺陷被直接计数；对整体光照漂移不敏感（逐像元基线）",
        "meaning": "帧内缺陷（稳健 z 超阈且面积≥8px 的连通域）个数：点缺陷出现/增多计数",
    })
    cols.append({
        "feature": "DEFECT-AREA-FRAC", "unit": None,
        "tag_cn": "缺陷面积占比", "tag_en": "defect area fraction",
        "formula": "(pixels in counted defect components) / (all pixels); same |z| mask as DEFECT-COUNT",
        "physics_basis": "缺陷总面积占比是缺陷严重度/扩展（划痕、污染、团聚）的面积代理；与计数互补（计数×面积=形貌）",
        "meaning": "缺陷像元总面积占整帧比例：缺陷严重度面积代理",
    })
    for axis in ("X", "Y"):
        cols.append({
            "feature": f"SHIFT-{axis}", "unit": "px",
            "tag_cn": f"配准漂移 {axis}", "tag_en": f"registration drift {axis}",
            "formula": f"argmax over integer (dy, dx) in [-{SHIFT_SEARCH_PX},{SHIFT_SEARCH_PX}]^2 of the "
                       f"normalized cross-correlation of g vs ref_median under content displacement (dx, dy); "
                       f"coarse search on the 4x block-mean grid then full-resolution refinement (+/-4 px); "
                       f"positive = frame content displaced toward +{axis}",
            "physics_basis": "相机/机械配准漂移会把几何变化伪装成强度变化（MIA 2014 告诫）；"
                             "解释 RADIAL/AZIM/EDGE 类特征变化前先看 SHIFT",
            "meaning": f"相对参考帧的整帧平移 {axis} 分量（px，内容沿 +{axis} 为正）：相机配准/机械漂移代理",
        })
    cols.append({
        "feature": "N", "unit": "count",
        "tag_cn": "成功解码帧数", "tag_en": "decoded frame count",
        "formula": "count of rows in IMG-<SLUG>.csv (decoded, time-anchored frames)",
        "physics_basis": "数据完整性计数，非过程量",
        "meaning": "成功解码且通过时间冲突检查的图像帧数（整源常量，非过程量）",
        "role": "metadata",
    })
    return cols


# ───────────────────────────── extract ─────────────────────────────

def extract(src: dict, ctx) -> dict:
    """Frozen I9. Returns {source, rows, contract, annotations, objects, notes}.

    Two decode passes, both O(n): pass 1 validates + radial/azimuth features
    (buffering only the reference-window frames), pass 2 diff/defect/shift +
    thumbnails + object cards. Reference statistics are computed once between
    the passes — never O(n^2)."""
    min_mod = _img_min()
    min_mod._require_pillow()
    from PIL import Image

    run_dir = _ctx_get(ctx, "run_dir", None)
    if run_dir is None:
        raise RuntimeError("image_stream extract requires ctx.run_dir")
    run_dir = Path(run_dir)
    cfg = _ctx_get(ctx, "config", {}) or {}
    slug = src["slug"]
    mode = src.get("mode", "index_csv")
    cal: dict | None = src.get("calibration")
    q_prefix = "Q-" if cal is not None else ""

    # ---- records + time anchoring (same discipline as M1) --------------------
    records = min_mod._collect_records(src)
    n_rows_in = len(records)
    n_ambiguous = sum(1 for rec in records if rec["index_tv"] is not None
                      and "ambiguous_date_order" in rec["index_tv"].flags)
    if n_ambiguous:
        meta = _source_meta(src, mode, 0, None, None, None,
                            reason=f"ambiguous_date_order={n_ambiguous}; source refused (never guess D/M vs M/D)")
        meta["disposition"] = "insufficient_data"
        return {"source": meta, "rows": None, "contract": [], "annotations": [], "objects": [], "notes": []}

    n_unparsed = sum(1 for rec in records
                     if (rec["index_ts"] if mode == "index_csv" else rec["file_ts"]) is None)
    gap_hint = min_mod._median_gap_s([rec["index_ts"] if mode == "index_csv" else rec["file_ts"]
                                      for rec in records])
    n_conflict = 0
    if mode == "index_csv" and gap_hint:
        for rec in records:
            if rec["index_ts"] is not None and rec["file_ts"] is not None:
                if abs((rec["index_ts"] - rec["file_ts"]).total_seconds()) > gap_hint:
                    rec["drop"] = "ts_conflict"
                    n_conflict += 1

    candidates = [rec for rec in records
                  if not rec.get("drop") and rec["ts"] is not None and rec["image"].exists()]
    n_missing = sum(1 for rec in records
                    if not rec.get("drop") and rec["ts"] is not None and not rec["image"].exists())
    candidates.sort(key=lambda r: (r["ts"], r["order"]))

    ref_idx, ref_src = _ref_indices(candidates, cfg)
    ref_want = set(ref_idx)

    # ---- pass 1: decode once, geometry features, buffer reference frames -----
    kept: list[dict] = []
    n_decode_failed = 0
    rad_list: list[np.ndarray] = []
    azim_list: list[np.ndarray] = []
    ref_buf: list[np.ndarray] = []
    ref_bytes = 0
    h0 = w0 = 0
    bin_w = 1
    geo = None
    for i, rec in enumerate(candidates):
        try:
            with Image.open(rec["image"]) as im:
                width, height = im.size
                pil_mode = im.mode
                g8 = np.asarray(im.convert("L"))
        except Exception:
            n_decode_failed += 1
            continue
        if g8.ndim != 2 or g8.size == 0:
            n_decode_failed += 1
            continue
        rec["width"], rec["height"], rec["pil_mode"] = int(width), int(height), pil_mode
        if geo is None:
            h0, w0 = int(height), int(width)
            bin_w = max(1, int(round(min(h0, w0) / 64)))   # first decoded frame fixes bin width
            cx0, cy0 = ((float(cal["beam_center_px"][0]), float(cal["beam_center_px"][1]))
                        if cal is not None else ((w0 - 1) / 2.0, (h0 - 1) / 2.0))
            geo = _geometry(h0, w0, bin_w, cx0, cy0)
        g = g8.astype(np.float64)
        if g.shape == (h0, w0):
            rad, azim = _bin_means(g, geo)
        else:
            cx0, cy0 = ((float(cal["beam_center_px"][0]), float(cal["beam_center_px"][1]))
                        if cal is not None else ((g.shape[1] - 1) / 2.0, (g.shape[0] - 1) / 2.0))
            rad, azim = _bin_means(g, _geometry(g.shape[0], g.shape[1], bin_w, cx0, cy0))
        rad_list.append(rad)
        azim_list.append(azim)
        if i in ref_want and ref_bytes + g8.nbytes <= REF_BUFFER_CAP_BYTES:
            ref_buf.append(g8)
            ref_bytes += g8.nbytes
        kept.append(rec)
    n = len(kept)

    reason_tail = (f"rows_in={n_rows_in}; ts_conflict={n_conflict}; unparsed_ts={n_unparsed}; "
                   f"missing_file={n_missing}; decode_failed={n_decode_failed}")
    if n == 0:
        meta = _source_meta(src, mode, 0, None, None, None,
                            reason=f"no decodable frames; {reason_tail}")
        meta["disposition"] = "insufficient_data"
        return {"source": meta, "rows": None, "contract": [], "annotations": [], "objects": [], "notes": []}
    if not ref_buf:                     # every reference-window decode failed
        with Image.open(kept[0]["image"]) as im:
            ref_buf = [np.asarray(im.convert("L"))]
        ref_src += "(single_frame_fallback)"

    stack = np.stack([b.astype(np.float64) for b in ref_buf])
    ref_median = np.median(stack, axis=0)
    ref_mad = np.median(np.abs(stack - ref_median), axis=0)
    ref_ds = _downsample4(ref_median)

    # ---- pass 2: diff / defect / shift + thumbnails + cards ------------------
    obj_dir = run_dir / "07_hetero" / "objects" / slug
    thumbs_dir = obj_dir / "thumbs"
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    stride = int(math.ceil(n / THUMB_MAX))
    thumb_idx = set(range(0, n, stride))
    diff_rmse = np.full(n, np.nan)
    defect_count = np.zeros(n, dtype=np.int64)
    defect_frac = np.full(n, np.nan)
    shift_x = np.zeros(n, dtype=np.int64)
    shift_y = np.zeros(n, dtype=np.int64)
    objects: list[dict] = []
    params_card = {
        "pixel_size_um": cal["pixel_size_um"] if cal else None,
        "beam_center_px": cal["beam_center_px"] if cal else None,
        "detector_distance_mm": cal["detector_distance_mm"] if cal else None,
        "wavelength_angstrom": cal["wavelength_angstrom"] if cal else None,
        "bin_w_px": bin_w, "n_radial_bins": N_RADIAL_BINS, "n_azim_sectors": N_AZIM_SECTORS,
        "sidecar_path": cal["sidecar_path"] if cal else None,
        "sidecar_sha256": cal["sidecar_sha256"] if cal else None,
        "ref_source": ref_src, "ref_frames": len(ref_buf),
        "z_threshold": ROBUST_Z_THRESHOLD, "defect_min_area_px": DEFECT_MIN_AREA_PX,
        "shift_search_px": SHIFT_SEARCH_PX,
    }
    for i, rec in enumerate(kept):
        with Image.open(rec["image"]) as im:
            g8 = np.asarray(im.convert("L"))
            thumb_rel = None
            if i in thumb_idx:
                th = im.convert("L").resize((THUMB_SIZE, THUMB_SIZE))
                tpath = thumbs_dir / f"{i:06d}_{rec['image'].stem}.png"
                th.save(tpath, format="PNG")
                thumb_rel = f"thumbs/{tpath.name}"
        g = g8.astype(np.float64)
        diff_rmse[i] = math.sqrt(float(((g - ref_median) ** 2).mean())) if g.shape == ref_median.shape else float("nan")
        cnt, frac = _defect_stats(g, ref_median, ref_mad) if g.shape == ref_median.shape else (0, 0.0)
        defect_count[i] = cnt
        defect_frac[i] = frac
        dy, dx = _estimate_shift(g, ref_median, ref_ds if g.shape == ref_median.shape else None)
        shift_y[i], shift_x[i] = dy, dx
        card = {"file": str(rec["image"]), "sha256": mani.sha256_file(rec["image"]),
                "ts": rec["iso"], "width": rec["width"], "height": rec["height"],
                "pil_mode": rec["pil_mode"],
                "downsample": f"{THUMB_SIZE}x{THUMB_SIZE}" if thumb_rel else None,
                "thumb": thumb_rel, "params": params_card,
                "note": "M2 deep-path object card (img_deep.py); calibration + reference-window provenance"}
        mani.write_json_atomic(obj_dir / f"{i:06d}_{rec['image'].stem}.json", card)
        objects.append(card)

    # ---- rows table (frozen I4 prefix) ---------------------------------------
    import pandas as pd

    coldefs = _column_meta(cal, bin_w, geo)
    feat_cols = [naming.feature_column(SHAPE, slug, c["feature"]) for c in coldefs]
    radial_arr = np.stack(rad_list) if rad_list else np.empty((n, N_RADIAL_BINS))
    azim_arr = np.stack(azim_list) if azim_list else np.empty((n, N_AZIM_SECTORS))
    data: dict = {"ts": [r["iso"] for r in kept],
                  "_src_ts": [r["iso"] for r in kept],
                  "n_inputs": [1] * n}
    for j, cdef in enumerate(coldefs):
        col = feat_cols[j]
        feat = cdef["feature"].replace(q_prefix, "", 1)
        if feat.startswith("RADIAL-P"):
            data[col] = radial_arr[:, int(feat.split("P")[1]) - 1]
        elif feat.startswith("AZIM-P"):
            data[col] = azim_arr[:, int(feat.split("P")[1]) - 1]
        elif feat == "DIFF-RMSE":
            data[col] = diff_rmse
        elif feat == "DEFECT-COUNT":
            data[col] = defect_count
        elif feat == "DEFECT-AREA-FRAC":
            data[col] = defect_frac
        elif feat == "SHIFT-X":
            data[col] = shift_x
        elif feat == "SHIFT-Y":
            data[col] = shift_y
        elif feat == "N":
            data[col] = [n] * n
        else:                            # defensive: unknown feature must never happen
            data[col] = np.full(n, np.nan)
    rows = pd.DataFrame(data)

    # ---- provenance + contract ------------------------------------------------
    source_path, source_sha256 = min_mod._source_anchor(src, mode, obj_dir, kept)
    cadence = min_mod._median_gap_s([r["ts"] for r in kept])
    span = (kept[-1]["ts"] - kept[0]["ts"]).total_seconds() if n > 1 else 0.0
    last_iso = kept[-1]["iso"]
    ts_source = "index" if mode == "index_csv" else "camera"
    common = {
        "shape": "IMG", "source_id": slug, "source_path": source_path,
        "source_sha256": source_sha256 or "",
        "role": "predictor_candidate", "evidence_level": 1,
        "evidence_level_basis": ("direct frame measurement of a retained source (L1); the calibration "
                                 "sidecar is user-provided configuration, not a model output"),
        "method": METHOD, "method_version": CONTRACT_VERSION,
        "n_inputs": n, "coverage": 0.0, "effective_n": n,
        "sparse": True, "stats_eligible": False,   # I8: vs anchor coverage; align (WS5) updates
        "cadence_s": cadence, "ts_source": ts_source, "tz": "naive_local",
        "clock_offset_s": 0.0, "model_derived": False, "insufficient_data": False,
        "_src_ts": last_iso,
    }
    contract = []
    for cdef, col in zip(coldefs, feat_cols):
        contract.append({**common, "column": col, "unit": cdef["unit"],
                         "physical_meaning": cdef["meaning"], "formula": cdef["formula"],
                         "physics_basis": cdef["physics_basis"],
                         "tag_cn": cdef["tag_cn"], "tag_en": cdef["tag_en"],
                         "role": cdef.get("role", "predictor_candidate")})

    reason = (f"image_stream/{mode} [deep:img_deep calibrated={str(cal is not None).lower()}] "
              f"sidecar={Path(cal['sidecar_path']).name if cal else 'none'} "
              f"sidecar_sha256={cal['sidecar_sha256'] if cal else 'none'} "
              f"ref={ref_src} ref_frames={len(ref_buf)}; {reason_tail}")
    meta = _source_meta(src, mode, n, cadence, span, _ts_format(src, records, mode), reason=reason,
                        fmt=_majority_format(kept) + ("+calibrated" if cal is not None else ""))
    meta["features"] = [c["column"] for c in contract]
    meta["objects_dir"] = f"07_hetero/objects/{slug}"
    return {"source": meta, "rows": rows, "contract": contract,
            "annotations": [], "objects": objects, "notes": []}


# ───────────────────────────── shared M1 helpers ─────────────────────────────

def _ts_format(src: dict, records: list[dict], mode: str) -> str | None:
    if mode == "index_csv":
        fmts = sorted({rec["index_tv"].fmt for rec in records if rec["index_tv"] and rec["index_tv"].fmt})
        return "|".join(fmts) if fmts else None
    return "filename_embedded"


def _majority_format(kept: list[dict]) -> str:
    exts = sorted({rec["image"].suffix.lower().lstrip(".") or "bin" for rec in kept})
    return exts[0] if len(exts) == 1 else "mixed"


def _source_meta(src: dict, mode: str, n: int, cadence, span, ts_format,
                 reason: str = "", fmt: str | None = None) -> dict:
    """Schema-exact mirror of img.py's _source_meta (H1b strict extra keys)."""
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
