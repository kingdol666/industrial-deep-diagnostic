#!/usr/bin/env python
"""gen_T1_inbox.py — Examiner generator for T1 (mixed-format inbox).

Creates cases/T1_preprocessor_mixed_inbox/inbox/ with 8 files simulating 3 drop
batches. Injected defects (documented in truth/T1_truth.md):
  - sensor_log.csv          : row index 150 duplicated as the final row
                              (duplicate timestamp 2026-09-28 10:30:00)
  - qa_lab.xlsx             : 3 missing cells (rows 37/88/121, 0-based data idx)
  - batch_records.json      : record #57 moisture_pct = null
  - dcs_export_gbk.csv      : 2 outliers (temp 999.9 @ data row 51, speed -3.2 @ row 121)
  - process_log.tsv / operator_notes.md / downtime.html / heater_export.csv : clean
Seeded: numpy default_rng(20261001). Regenerate = byte-identical (xlsx zips may
carry timestamps; content identical).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261001
OUT = Path(__file__).resolve().parent.parent / "T1_preprocessor_mixed_inbox" / "inbox"
BASE_TS = pd.Timestamp("2026-09-28 08:00:00")


def ar1(rng, n, sigma, phi=0.3):
    e = rng.normal(0, sigma, n)
    x = np.zeros(n)
    x[0] = e[0]
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


def main():
    rng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- batch 1 -----------------------------------------------------------
    n = 300
    ts = pd.date_range(BASE_TS, periods=n, freq="min")
    sensor = pd.DataFrame({
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "temp_c": np.round(85.0 + ar1(rng, n, 0.8), 3),
        "pressure_mpa": np.round(2.40 + ar1(rng, n, 0.05), 4),
        "speed_rpm": np.round(1250.0 + ar1(rng, n, 6.0), 2),
        "flow_lpm": np.round(42.0 + ar1(rng, n, 1.2), 3),
        "vibration_mms": np.round(2.80 + ar1(rng, n, 0.15), 3),
        "motor_amp": np.round(36.0 + ar1(rng, n, 0.9), 2),
    })
    dup = sensor.iloc[[150]].copy()          # DEFECT: exact duplicate row
    sensor = pd.concat([sensor, dup], ignore_index=True)
    sensor.to_csv(OUT / "sensor_log.csv", index=False, encoding="utf-8")

    m = 150
    qa = pd.DataFrame({
        "sample_id": [f"S{i + 1:04d}" for i in range(m)],
        "thickness_um": np.round(185.0 + rng.normal(0, 3.0, m), 2),
        "gloss_gu": np.round(92.0 + rng.normal(0, 1.5, m), 2),
        "tensile_mpa": np.round(48.0 + rng.normal(0, 1.8, m), 2),
    })
    qa.loc[37, "thickness_um"] = None        # DEFECT: 3 missing cells
    qa.loc[88, "gloss_gu"] = None
    qa.loc[121, "tensile_mpa"] = None
    with pd.ExcelWriter(OUT / "qa_lab.xlsx", engine="openpyxl") as xw:
        qa.to_excel(xw, sheet_name="quality", index=False)

    # ---- batch 2 -----------------------------------------------------------
    k = 120
    recs = []
    bts = pd.date_range(BASE_TS + pd.Timedelta(minutes=7), periods=k, freq="2min")
    moist = np.round(0.42 + rng.normal(0, 0.03, k), 4)
    visc = np.round(2150.0 + rng.normal(0, 60, k), 1)
    for i in range(k):
        recs.append({
            "record_id": f"B{i + 1:04d}",
            "batch_time": bts[i].strftime("%Y-%m-%dT%H:%M:%S"),
            "batch_no": f"B0731_{i // 10 + 1:02d}",
            "moisture_pct": None if i == 57 else float(moist[i]),   # DEFECT: 1 null
            "viscosity_cp": float(visc[i]),
        })
    (OUT / "batch_records.json").write_text(
        json.dumps(recs, indent=1, ensure_ascii=False), encoding="utf-8")

    p = 200
    pts = pd.date_range(BASE_TS, periods=p, freq="min")
    proc = pd.DataFrame({
        "process_time": pts.strftime("%Y-%m-%d %H:%M:%S"),
        "reactor_pv": np.round(178.0 + ar1(rng, p, 1.5), 3),
        "jacket_sp": np.round(165.0 + ar1(rng, p, 0.5), 3),
        "feed_rate_kgh": np.round(320.0 + ar1(rng, p, 4.0), 2),
        "ph_value": np.round(7.20 + ar1(rng, p, 0.08), 3),
    })
    proc.to_csv(OUT / "process_log.tsv", sep="\t", index=False, encoding="utf-8")

    # ---- batch 3 -----------------------------------------------------------
    q = 40
    ots = pd.date_range(BASE_TS, periods=q, freq="10min")
    ops = ["张工", "李工", "王芳", "赵倩"]
    events = ["巡检", "取样", "清理模头", "换批", "调整牵引"]
    notes = ["一切正常", "膜面轻微条纹，已记录", "窗口值稳定", "已通知工艺员",
             "冷却水温度偏高，观察中", "无异常"]
    lines = ["# 交接班记录（2026-09-28 早班）", "",
             "以下为夜班交接的巡检与操作要点摘录，供工艺分析参考。", "",
             "| shift_time | operator | event | note |",
             "|---|---|---|---|"]
    for i in range(q):
        lines.append(f"| {ots[i].strftime('%Y-%m-%d %H:%M')} | {ops[i % 4]} | "
                     f"{events[int(rng.integers(0, len(events)))]} | "
                     f"{notes[int(rng.integers(0, len(notes)))]} |")
    lines += ["", "> 备注：以上记录由当班操作工手工填写。", ""]
    (OUT / "operator_notes.md").write_text("\n".join(lines), encoding="utf-8")

    d = 25
    dts = pd.date_range("2026-09-29 06:00", periods=d, freq="97min")
    eqs = ["压延机C线", "冷却辊R2", "牵引机T1", "卷取机W3"]
    reasons = ["换辊", "清理积料", "待料", "电气检修", "计划保养"]
    rows = ["<!DOCTYPE html>", "<html><head><meta charset=\"utf-8\">",
            "<title>停机记录 2026-09-29</title></head><body>",
            "<h2>停机记录（2026-09-29）</h2>",
            "<table border=\"1\">",
            "<tr><th>start_time</th><th>end_time</th><th>equipment</th>"
            "<th>reason</th><th>duration_min</th></tr>"]
    for i in range(d):
        start = dts[i]
        dur = int(rng.integers(5, 65))
        end = start + pd.Timedelta(minutes=dur)
        rows.append(f"<tr><td>{start.strftime('%Y-%m-%d %H:%M')}</td>"
                    f"<td>{end.strftime('%Y-%m-%d %H:%M')}</td>"
                    f"<td>{eqs[int(rng.integers(0, 4))]}</td>"
                    f"<td>{reasons[int(rng.integers(0, 5))]}</td>"
                    f"<td>{dur}</td></tr>")
    rows += ["</table>", "</body></html>", ""]
    (OUT / "downtime.html").write_text("\n".join(rows), encoding="utf-8")

    t = 180
    tts = pd.date_range(BASE_TS, periods=t, freq="min")
    dcs = pd.DataFrame({
        "时间": tts.strftime("%Y-%m-%d %H:%M:%S"),
        "温度": np.round(85.0 + ar1(rng, t, 0.9), 2),
        "压力": np.round(0.42 + ar1(rng, t, 0.01), 4),
        "转速": np.round(1250.0 + ar1(rng, t, 8.0), 1),
    })
    dcs.loc[51, "温度"] = 999.9              # DEFECT: 2 outlier values (DCS glitch)
    dcs.loc[121, "转速"] = -3.2
    dcs.to_csv(OUT / "dcs_export_gbk.csv", index=False, encoding="gbk")

    h = 90
    hts = pd.date_range("2026-09-30 06:00", periods=h, freq="min")
    heat = pd.DataFrame({
        "stamp": hts.strftime("%Y-%m-%d %H:%M:%S"),
        "zone1_sp": np.round(180.0 + rng.normal(0, 0.2, h), 2),
        "zone2_pv": np.round(178.5 + ar1(rng, h, 1.2), 2),
        "heater_kw": np.round(12.4 + ar1(rng, h, 0.6), 3),
    })
    heat.to_csv(OUT / "heater_export.csv", sep=";", index=False, encoding="utf-8")

    print("T1 inbox written to", OUT)
    for f in sorted(OUT.iterdir()):
        print(f"  {f.name:24s} {f.stat().st_size:>8d} bytes")


if __name__ == "__main__":
    main()
