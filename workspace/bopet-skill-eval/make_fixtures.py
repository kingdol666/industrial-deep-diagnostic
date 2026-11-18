# -*- coding: utf-8 -*-
"""BOPET skill-eval fixtures — deterministic synthetic data (5 scenarios).

Each CSV is small (20-240 rows), utf-8, Chinese headers, hour/批级 sampling.
Injected faults are documented per-folder in ground_truth.md (出题人参考).
Run:  uv run --project .claude/shared/scripts python make_fixtures.py
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent


def _contained(path: Path) -> Path:
    """Fixture writes stay under this script's own directory (no .. escape)."""
    if ".." in path.parts:
        raise ValueError(f"path must not contain '..': {path}")
    resolved = path.resolve()
    if ROOT not in resolved.parents:
        raise ValueError(f"path outside fixture root: {resolved}")
    return resolved


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path = _contained(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    path.write_text(buf.getvalue(), encoding="utf-8", newline="")


def hours(start_day: int, n: int) -> list[str]:
    return [f"2026-10-{start_day:02d} {h // 24:02d}:{h % 24:02d}:00"
            for h in range(n)] if False else [
        (np.datetime64("2026-10-01T00:00:00") + np.timedelta64(int(i), "h")
         ).astype("datetime64[s]").astype(str) for i in range(n)]


def ar1(rng, n, sigma, rho=0.3):
    e = rng.normal(0, sigma, n)
    for i in range(1, n):
        e[i] += rho * e[i - 1]
    return e


# ---------------------------------------------------------------- S1 收卷稳定性
def s1_winding():
    rng = np.random.default_rng(101)
    n = 168
    t = np.arange(n)
    tension = 2270 + 8 * np.sin(2 * np.pi * t / 12) + ar1(rng, n, 5.0)
    osc = np.sin(2 * np.pi * t / 9) * 14 * (1 + np.clip(t - 96, 0, None) / 72)
    tension = tension + osc
    tape = 18.0 + ar1(rng, n, 0.4)
    roll_press = 2.5 + ar1(rng, n, 0.08)
    speed = 320 + ar1(rng, n, 1.2)
    thick = 12.0 + 0.0016 * (tension - 2270) + ar1(rng, n, 0.02)
    premium = 98.6 - 1.5 * np.maximum(0, np.abs(thick - 12.0) - 0.05) \
        + ar1(rng, n, 0.15)
    rows = [[ts, round(a, 1), round(b, 2), round(c, 2), round(d, 1),
             round(e, 4), round(f, 2)]
            for ts, a, b, c, d, e, f in
            zip(hours(1, n), tension, tape, roll_press, speed, thick, premium)]
    write_csv(ROOT / "S1_stability_winding/00_input/winding_week.csv",
              ["时间", "牵引入口张力", "收卷锥度张力", "展平辊压力", "收卷速度",
               "薄膜厚度", "优品率"], rows)


# ---------------------------------------------------------------- S2 MDO CCD
def s2_ccd():
    rng = np.random.default_rng(202)
    alpha = 1.682
    pts = []
    for a in (-1, 1):
        for b in (-1, 1):
            for c in (-1, 1):
                pts.append((a, b, c))
    for sign in (-1, 1):
        for k in range(3):
            p = [0, 0, 0]
            p[k] = sign * alpha
            pts.append(tuple(p))
    for _ in range(6):
        pts.append((0, 0, 0))
    T_C, v_C, r_C = 78.0, 52.0, 3.2
    T_S, v_S, r_S = 5.0, 2.0, 0.3
    order = rng.permutation(len(pts))
    rows = []
    for i, j in enumerate(order):
        a, b, c = pts[j]
        T = T_C + a * T_S
        v = v_C + b * v_S
        r = r_C + c * r_S
        strength = (230 - 2.2 * (T - 78.5) ** 2 - 1.8 * (v - 53.0) ** 2
                    - 15.0 * (r - 3.25) ** 2 + 0.5 * (T - 78) * (r - 3.25)
                    + rng.normal(0, 0.8))
        haze = (1.10 + 0.55 * (r - 3.1) ** 2 + 0.012 * (T - 78) ** 2
                + rng.normal(0, 0.05))
        ddev = (18 + 4.5 * (v - 52) ** 2 + 3.0 * (T - 78) ** 2
                + rng.normal(0, 1.5))
        rows.append([i + 1, round(T, 2), round(v, 2), round(r, 3),
                     round(strength, 2), round(haze, 3), round(ddev, 1)])
    write_csv(ROOT / "S2_doe_mdo_ccd/00_input/mdo_ccd_trials.csv",
              ["试验顺序", "预热辊温", "拉伸速度", "拉伸比", "拉伸强度", "雾度",
               "厚度偏差"], rows)


# ---------------------------------------------------------------- S3 哨兵
def s3_sentinel():
    rng = np.random.default_rng(303)
    n_hist = 240
    hist = {
        "熔体压力": 110 + ar1(rng, n_hist, 1.2),
        "铸片辊温度": 26.5 + ar1(rng, n_hist, 0.3),
        "纵拉预热辊温": 78 + ar1(rng, n_hist, 0.5),
        "TDO拉伸区温度CX4": 240 + ar1(rng, n_hist, 0.8),
        "TDO定型区温度CX6": 191 + ar1(rng, n_hist, 0.8),
        "牵引入口张力": 2270 + ar1(rng, n_hist, 25),
    }
    cols = list(hist)
    rows = [[ts] + [round(hist[c][i], 2) for c in cols]
            for i, ts in enumerate(hours(1, n_hist))]
    write_csv(ROOT / "S3_sentinel_tdo_watch/00_input/tdo_history_10d.csv",
              ["时间"] + cols, rows)

    n_w = 120
    t = np.arange(n_w)
    cx6 = 191 + 0.06 * t + ar1(rng, n_w, 0.8)
    press = 110 + ar1(rng, n_w, 1.2)
    for k, amp in [(30, 3.2), (54, 3.8), (78, 2.9), (100, 3.4)]:
        press[k] += amp
    watch = {
        "熔体压力": press,
        "铸片辊温度": 26.5 + ar1(rng, n_w, 0.3),
        "纵拉预热辊温": 78 + ar1(rng, n_w, 0.5),
        "TDO拉伸区温度CX4": 240 + ar1(rng, n_w, 0.8),
        "TDO定型区温度CX6": cx6,
        "牵引入口张力": 2270 + ar1(rng, n_w, 25),
    }
    rows = [[ts] + [round(watch[c][i], 2) for c in cols]
            for i, ts in enumerate(
                (np.datetime64("2026-10-11T00:00:00")
                 + np.timedelta64(1, "h") * np.arange(n_w)
                 ).astype("datetime64[s]").astype(str))]
    write_csv(ROOT / "S3_sentinel_tdo_watch/00_input/tdo_watch_5d.csv",
              ["时间"] + cols, rows)


# ---------------------------------------------------------------- S4 调优归因
def s4_tuning():
    rng = np.random.default_rng(404)
    n = 96
    t = np.arange(n)
    v = np.where(t < 40, 52.9, 53.4) + rng.normal(0, 0.03, n)
    cx4 = np.where(t < 64, 240.0, 242.0) + rng.normal(0, 0.15, n)
    thick = 12.0 + ar1(rng, n, 0.018)
    step_v = np.clip((t - 40) / 6, 0, 1)          # 6h 一阶过渡
    step_t = np.clip((t - 64) / 6, 0, 1)
    thick = thick - 0.12 * step_v + 0.035 * step_t
    rows = [[ts, round(a, 2), round(b, 2), round(c, 4)]
            for ts, a, b, c in zip(hours(1, n), v, cx4, thick)]
    write_csv(ROOT / "S4_tuning_traction/00_input/data.csv",
              ["时间", "纵拉拉伸速度", "TDO拉伸区温度CX4", "薄膜厚度"], rows)


# ---------------------------------------------------------------- S6 厚度超差
def s6_fault():
    rng = np.random.default_rng(606)
    n = 240
    t = np.arange(n)
    cx4 = 240 + 0.0125 * np.clip(t - 96, 0, None) + ar1(rng, n, 0.8)
    dpress = 0.8 + 0.05 * np.clip(t - 150, 0, None) / 1 + ar1(rng, n, 0.15)
    melt_p = 110 + 0.6 * (dpress - 0.8) + ar1(rng, n, 1.2)
    thick = 12.0 + 0.010 * (cx4 - 240) + 0.02 * (melt_p - 110) \
        + ar1(rng, n, 0.02)
    premium = (98.6 - 0.9 * np.clip(thick - 12.06, 0, None) / 0.06
               - 0.25 * np.clip(dpress - 2.0, 0, None) + ar1(rng, n, 0.12))
    steady = {
        "主挤计量段温度": 282 + ar1(rng, n, 0.35),
        "模头温度": 285 + ar1(rng, n, 0.3),
        "铸片辊温度": 26.5 + ar1(rng, n, 0.25),
        "铸片辊线速": 16.4 + ar1(rng, n, 0.05),
        "纵拉预热辊温": 78 + ar1(rng, n, 0.45),
        "纵拉拉伸速度": 52.9 + ar1(rng, n, 0.04),
        "TDO定型区温度CX6": 191 + ar1(rng, n, 0.8),
        "TDO出口轨宽": 6330 + ar1(rng, n, 4),
        "牵引入口张力": 2270 + ar1(rng, n, 22),
    }
    cols = ["主挤计量段温度", "熔体压力", "滤器压差", "模头温度", "铸片辊温度",
            "铸片辊线速", "纵拉预热辊温", "纵拉拉伸速度", "TDO拉伸区温度CX4",
            "TDO定型区温度CX6", "TDO出口轨宽", "牵引入口张力", "薄膜厚度",
            "优品率"]
    vals = {
        "熔体压力": melt_p, "滤器压差": dpress, "TDO拉伸区温度CX4": cx4,
        "薄膜厚度": thick, "优品率": premium, **steady,
    }
    rows = [[ts] + [round(vals[c][i], 3) for c in cols]
            for i, ts in enumerate(hours(1, n))]
    write_csv(ROOT / "S6_diagnosis_thickness/00_input/thickness_fault_10d.csv",
              ["时间"] + cols, rows)


if __name__ == "__main__":
    s1_winding()
    s2_ccd()
    s3_sentinel()
    s4_tuning()
    s6_fault()
    print("fixtures written under", ROOT)
