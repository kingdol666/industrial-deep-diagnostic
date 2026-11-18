#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fresh minimal E2E dataset for industrial-hetero-preprocessor live verification.

Generic process (no domain words): DCS anchor 10-min cadence, one profile
scan (30-min), one 2D map (60-min), operator notes, and a tiny PNG image
stream (60-min) with an index CSV. Injected drift: edge gradient grows
mid-run; notes flag an event at that time.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
RUN = HERE / "run"
RAW.mkdir(parents=True, exist_ok=True)
(RUN / "00_input").mkdir(parents=True, exist_ok=True)
(RUN / "07_hetero").mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(7)

# ---- anchor: 10-min cadence, 5 days, 720 rows --------------------------------
t0 = pd.Timestamp("2026-03-01 00:00:00")
n = 720
ts = [t0 + pd.Timedelta(minutes=10 * i) for i in range(n)]
base = 80 + 3 * np.sin(np.arange(n) / 40) + rng.normal(0, 0.4, n)
drift = np.zeros(n)
drift[400:] = np.linspace(0, 6, n - 400)  # mid-run ramp
df = pd.DataFrame({
    "时间": [t.strftime("%Y-%m-%d %H:%M:%S") for t in ts],
    "TEMP01": np.round(base + drift, 3),
    "PRES01": np.round(50 + rng.normal(0, 0.5, n), 3),
    "FLOW01": np.round(12 + rng.normal(0, 0.2, n), 3),
    "YIELD01": np.round(99.0 - 0.35 * np.maximum(drift - 3, 0) + rng.normal(0, 0.15, n), 3),
})
df.to_csv(RUN / "00_input" / "preprocessed_data.csv", index=False, encoding="utf-8-sig")
df.to_csv(RAW / "line_dcs_10min.csv", index=False, encoding="utf-8-sig")

# ---- profile: 30-min cadence, 12 positions, wide layout -----------------------
m = 240
pts = [t0 + pd.Timedelta(minutes=30 * i) for i in range(m)]
pos_cols = {}
edge_lvl = np.zeros(m)
edge_lvl[130:] = np.linspace(0, 2.2, m - 130)
for j in range(12):
    edge = np.where(j >= 10, 1.0, np.where(j <= 1, -0.5, 0.0))  # right-edge bias
    pos_cols[f"pos_{j+1:02d}"] = np.round(
        100 + edge * edge_lvl + 0.8 * np.sin(np.arange(m) / 60 + j / 3) + rng.normal(0, 0.25, m), 3)
prof = pd.DataFrame({"时间": [t.strftime("%Y-%m-%d %H:%M:%S") for t in pts], **pos_cols})
prof.to_csv(RAW / "thk_profile_30min.csv", index=False, encoding="utf-8-sig")

# ---- map: 60-min cadence, 5x4 grid --------------------------------------------
g = 120
mt = [t0 + pd.Timedelta(minutes=60 * i) for i in range(g)]
rows = []
hot = np.where(np.arange(g) < 70, 0.0, 1.6)
for i, t in enumerate(mt):
    for x in range(5):
        for y in range(4):
            v = 25 + 0.6 * x + hot[i] * (1 if x == 4 else 0) + rng.normal(0, 0.2)
            rows.append({"时间": t.strftime("%Y-%m-%d %H:%M:%S"), "x": x, "y": y, "值": round(v, 3)})
pd.DataFrame(rows).to_csv(RAW / "zone_map_60min.csv", index=False, encoding="utf-8-sig")

# ---- text notes: sparse operator remarks --------------------------------------
notes = [
    ("2026-03-01 08:00:00", "接班检查正常，各段温度稳定"),
    ("2026-03-02 10:30:00", "右边缘手感略紧，做了微调"),
    ("2026-03-04 02:10:00", "右边缘出现轻微条纹，已通知工艺"),
    ("2026-03-04 06:00:00", "换卷后继续观察，问题仍在"),
    ("2026-03-04 22:40:00", "调整右侧风量后条纹减轻"),
]
pd.DataFrame(notes, columns=["时间", "备注"]).to_csv(
    RAW / "operator_notes.csv", index=False, encoding="utf-8-sig")

# ---- image stream: 120 PNG (60-min across the full 5 days) --------------------
# index file column convention: path relative to the index CSV's own directory
img_dir = RAW / "images"
img_dir.mkdir(exist_ok=True)
idx = []
img_ts = [t0 + pd.Timedelta(minutes=60 * i) for i in range(120)]
for i, t in enumerate(img_ts):
    arr = rng.normal(128, 12, (48, 48))
    if i >= 70:  # defect: dark blotch appears mid-run
        arr[18:30, 18:30] -= 60 * (1 + 0.3 * (i - 70))
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    fname = f"cam_{i:03d}.png"
    Image.fromarray(arr, mode="L").save(img_dir / fname)
    idx.append({"时间": t.strftime("%Y-%m-%d %H:%M:%S"), "filename": f"images/{fname}"})
pd.DataFrame(idx).to_csv(RAW / "image_index.csv", index=False, encoding="utf-8-sig")

# a context md (should be treated as context text, not a data source)
(RAW / "README.md").write_text(
    "# Line context\n\nGeneric verification dataset for the E-1H stage.\n", encoding="utf-8")

print(json.dumps({
    "raw": str(RAW), "run": str(RUN),
    "anchor_rows": len(df), "profile_rows": len(prof), "map_rows": len(rows),
    "notes": len(notes), "images": len(img_ts),
}, ensure_ascii=False, indent=2))
