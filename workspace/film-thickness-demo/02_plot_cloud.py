#!/usr/bin/env python
"""02_plot_cloud.py — film thickness cloud (TD x time) with truth overlays.

pcolormesh: x = time (h), y = width position 1..21, colour = thickness (um).
Overlays: dashed vertical lines at the three process events T1/T2/T3 (the
+5 min lag puts their thickness effect 5 min later) and a horizontal line at
the stripe position pos_07. All annotation text in English (font-safe).
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
LAG_MIN = 5

scans = pd.read_csv(HERE / "thickness_scans.csv", parse_dates=["timestamp"])
POS_COLS = [f"pos_{i:02d}" for i in range(1, 22)]
X = scans[POS_COLS].to_numpy(dtype=float)          # (1200, 21)

hours = (scans["timestamp"] - scans["timestamp"].iloc[0]).dt.total_seconds() / 3600.0
y = np.arange(1, 22, dtype=float)

fig, ax = plt.subplots(figsize=(13, 4.8))
pc = ax.pcolormesh(hours, y, X.T, shading="auto", cmap="turbo",
                   vmin=np.percentile(X, 0.5), vmax=np.percentile(X, 99.5))
cbar = fig.colorbar(pc, ax=ax, pad=0.015)
cbar.set_label("Thickness (um)")

events = [("T1 bolt-T3 ramp +6%", 800), ("T2 melt temp +2.5C", 1400),
          ("T3 lip step -0.02mm", 1900)]
for label, minute in events:
    h = (minute + LAG_MIN) / 60.0
    ax.axvline(h, color="white", ls="--", lw=1.2)
    ax.text(h + 0.15, 21.6, f"{label} (m+{LAG_MIN})", color="white",
            fontsize=8, rotation=90, va="top")

ax.axhline(7, color="white", ls=":", lw=1.2)
ax.text(0.3, 7.35, "stripe position pos_07", color="white", fontsize=8)

ax.set_title("Film thickness cloud (TD x time)")
ax.set_xlabel("Time (h)")
ax.set_ylabel("Width position (1-21)")
ax.set_ylim(1, 22)
fig.tight_layout()

out = HERE / "03_figures" / "thickness_cloud.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=150)
print(f"02_plot_cloud: wrote {out} ({out.stat().st_size} bytes)")
