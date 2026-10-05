# -*- coding: utf-8 -*-
"""T1 helper: per-source-file data quality audit (duplicates / missing / outliers).
Written under results/T1/ per brief rule (no writes outside results/T1/)."""
import json
import sys
import io

import pandas as pd

BASE = "cases/T1_preprocessor_mixed_inbox/inbox/"
OUT = []

def show(name, df, time_col, numeric_bounds=None):
    print("=" * 70)
    print(f"[{name}] shape={df.shape} time_col={time_col}")
    # missing cells
    miss = df.isna()
    total_missing = int(miss.sum().sum())
    print(f"missing cells total: {total_missing}")
    if total_missing:
        locs = []
        for col in df.columns:
            idx = df.index[miss[col]]
            for i in idx:
                locs.append(f"row{i+2}(data row {i}): {col}")
        print("  locations (first 20):", "; ".join(locs[:20]))
    # duplicate timestamps
    if time_col and time_col in df.columns:
        t = pd.to_datetime(df[time_col], errors="coerce")
        dup_t = t[t.duplicated(keep=False)]
        print(f"duplicate timestamps: {0 if len(dup_t)==0 else len(dup_t)} values, "
              f"{dup_t.nunique() if len(dup_t) else 0} distinct, "
              f"rows: {sorted((dup_t.index + 2).tolist())[:20] if len(dup_t) else '-'}")
        print(f"time range: {t.min()} -> {t.max()}, parse-fail NaT: {int(t.isna().sum())}")
    # duplicate full rows (excluding timestamp)
    dup_rows = df[df.drop(columns=[c for c in [time_col] if c]).duplicated(keep=False)]
    print(f"duplicate full rows (excl time col): {len(dup_rows)}",
          f"at rows {sorted((dup_rows.index + 2).tolist())[:20]}" if len(dup_rows) else "")
    # outliers: physically impossible values
    if numeric_bounds:
        for col, (lo, hi) in numeric_bounds.items():
            if col not in df.columns:
                continue
            v = pd.to_numeric(df[col], errors="coerce")
            bad = df.index[(v < lo) | (v > hi)]
            for i in bad:
                print(f"  IMPOSSIBLE outlier: row{i+2} {col}={df.at[i, col]} (allowed {lo}..{hi})")

# 1. sensor_log.csv
df = pd.read_csv(BASE + "sensor_log.csv")
show("sensor_log.csv", df, "timestamp",
     {"temp_c": (0, 300), "pressure_mpa": (0, 50), "speed_rpm": (0, 5000),
      "flow_lpm": (0, 1000), "vibration_mms": (0, 100), "motor_amp": (0, 500)})

# 2. process_log.tsv
df = pd.read_csv(BASE + "process_log.tsv", sep="\t")
show("process_log.tsv", df, "process_time",
     {"reactor_pv": (0, 400), "jacket_sp": (0, 400), "feed_rate_kgh": (0, 2000),
      "ph_value": (0, 14)})

# 3. batch_records.json
with open(BASE + "batch_records.json", encoding="utf-8") as f:
    df = pd.DataFrame(json.load(f))
show("batch_records.json", df, "batch_time",
     {"moisture_pct": (0, 100), "viscosity_cp": (0, 100000)})

# 4. dcs_export_gbk.csv  (GBK encoding)
df = pd.read_csv(BASE + "dcs_export_gbk.csv", encoding="gbk")
show("dcs_export_gbk.csv", df, "时间",
     {"温度": (0, 300), "压力": (0, 50), "转速": (0, 5000)})

# 5. heater_export.csv (semicolon)
df = pd.read_csv(BASE + "heater_export.csv", sep=";")
show("heater_export.csv", df, "stamp",
     {"zone1_sp": (0, 400), "zone2_pv": (0, 400), "heater_kw": (0, 100)})

# 6. qa_lab.xlsx (sheet quality)
xl = pd.ExcelFile(BASE + "qa_lab.xlsx")
print("=" * 70)
print("[qa_lab.xlsx] sheets:", xl.sheet_names)
df = xl.parse("quality")
show("qa_lab.xlsx::quality", df, None,
     {"thickness_um": (0, 5000), "gloss_gu": (0, 2000), "tensile_mpa": (0, 500)})

# 7. downtime.html
tables = pd.read_html(BASE + "downtime.html")
df = tables[0]
show("downtime.html", df, "start_time", {"duration_min": (0, 100000)})

# 8. operator_notes.md (markdown pipe table)
df = pd.read_csv(BASE + "operator_notes.md", sep="|", skiprows=3, header=0,
                 engine="python").dropna(axis=1, how="all")
df.columns = [c.strip() for c in df.columns]
for c in df.columns:
    if df[c].dtype == object:
        df[c] = df[c].astype(str).str.strip()
show("operator_notes.md", df, "shift_time")

# 9. unified view missing-cell breakdown
print("=" * 70)
uni = pd.read_csv("results/T1/preprocessed_data.csv")
print(f"[unified preprocessed_data.csv] shape={uni.shape}")
mp = uni.isna().mean().sort_values(ascending=False)
for col, pct in mp.items():
    print(f"  {col}: missing {pct*100:.1f}%")
print(f"total missing cell pct: {uni.isna().sum().sum() / uni.size * 100:.2f}%")
