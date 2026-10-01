#!/usr/bin/env python
"""Generate adversarial datasets for industrial-doe-analyzer red-teaming.
Writes ONLY under workspace/doe-redteam/<case>/run/00_input/."""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
rng = np.random.default_rng(20261001)


def dump(case, df, ctx=None, fname="data.csv"):
    if not re.fullmatch(r"[0-9A-Za-z_\-]+", case) or not re.fullmatch(r"[0-9A-Za-z_.\-]+", fname):
        raise ValueError(f"unsafe name: case={case!r} fname={fname!r}")
    d = (BASE / case / "run" / "00_input").resolve()
    if not d.is_relative_to(BASE):
        raise ValueError(f"path escapes redteam root: {case!r}")
    d.mkdir(parents=True, exist_ok=True)
    path = d / fname
    if fname.endswith(".parquet"):
        df.to_parquet(path, index=False)
    else:
        df.to_csv(path, index=False)
    if ctx is not None:
        (d / "analysis_context.json").write_text(
            json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", case)


def ctx(responses, factors, mode_override=None, time_col=None, group_col=None,
        run_order_col=None, blocks=None, covariates=None):
    return {
        "data_path": "00_input/data.csv",
        "mode_override": mode_override,
        "responses": responses,
        "factors": factors,
        "blocks": blocks or [],
        "covariates": covariates or [],
        "index_cols": [],
        "time_col": time_col,
        "group_col": group_col,
        "run_order_col": run_order_col,
        "max_lag": 20, "alpha": 0.05, "effect_size_threshold": 0.01,
        "constraints": [],
        "inference": {"assigned_by": "user", "notes": ["redteam"]},
    }


def R(col, goal=None, lsl=None, usl=None, target=None, weight=None):
    return {"col": col, "goal": goal, "lsl": lsl, "usl": usl,
            "target": target, "weight": weight}


def F(col, t):
    return {"col": col, "type": t}


# 1 all-categorical, no context (default auto-inference path)
n = 32
dump("01_all_categorical", pd.DataFrame({
    " Yield ": rng.normal(50, 2, n).round(3),
    "line": rng.choice(["L1", "L2"], n),
    "shift": rng.choice(["day", "night"], n),
    "batch_no": np.arange(1, n + 1),
}))

# 2a constant response, designed
n = 16
dump("02a_const_resp_designed", pd.DataFrame({
    "A": np.tile([-1, 1], 8), "B": np.repeat([-1, 1], 8),
    "quality": np.full(n, 50.0),
}), ctx([R("quality", "maximize", lsl=48, usl=52)],
        [F("A", "numeric"), F("B", "numeric")]))

# 2b constant response, observational
n = 240
t = pd.date_range("2026-01-01", periods=n, freq="h").strftime("%Y-%m-%d %H:%M:%S")
dump("02b_const_resp_obs", pd.DataFrame({
    "time": t,
    "temp": rng.normal(180, 3, n).round(3),
    "press": rng.normal(2.0, 0.1, n).round(4),
    "yield": np.full(n, 93.5),
}), ctx([R("yield", "maximize")], [F("temp", "numeric"), F("press", "numeric")],
        time_col="time"))

# 3 constant factor (designed ctx)
n = 20
B = rng.uniform(-1, 1, n).round(3)
dump("03_const_factor", pd.DataFrame({
    "A": np.full(n, 5.0),
    "B": B,
    "y": (2 * B + rng.normal(0, 0.2, n)).round(4),
}), ctx([R("y", "maximize")], [F("A", "numeric"), F("B", "numeric")]))

# 4a/4b tiny tables
dump("04a_one_row", pd.DataFrame({"A": [1.0], "y": [2.0]}),
     ctx([R("y")], [F("A", "numeric")]))
dump("04b_three_rows", pd.DataFrame({"A": [1.0, 2.0, 3.0], "y": [2.0, 4.1, 5.9]}),
     ctx([R("y")], [F("A", "numeric")]))
# 4c boundary: exactly 5 rows (passes gate)
dump("04c_five_rows", pd.DataFrame({
    "A": [-1, -1, 1, 1, 0.0], "B": [-1, 1, -1, 1, 0.0],
    "y": [10, 11, 12, 13, 14.0]}),
    ctx([R("y")], [F("A", "numeric"), F("B", "numeric")]))

# 5 messy mixed-format time strings
n = 120
fmts = ["%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%Y%m%d", "%b %d %Y %H:%M"]
times = []
base = pd.Timestamp("2026-03-01 08:00")
for i in range(n):
    ts = base + pd.Timedelta(minutes=5 * i)
    times.append(ts.strftime(fmts[i % len(fmts)]))
x = rng.normal(0, 1, n).round(4)
dump("05_messy_time", pd.DataFrame({
    "record_time": times,
    "feed": (10 + x).round(4),
    "purity": (95 + 2 * x + rng.normal(0, 0.5, n)).round(4),
}), ctx([R("purity", "maximize")], [F("feed", "numeric")], time_col="record_time"))

# 6 duplicate + unsorted timestamps
n = 200
idx = rng.integers(0, 100, n)
t = (pd.Series(idx).sort_values().astype(str).values)  # strings, duplicates, unsorted order
order = rng.permutation(n)
dump("06_dup_time_unsorted", pd.DataFrame({
    "time": pd.Series([f"2026-05-{1 + i // 20:02d} 0{i % 10}:00" for i in idx]).to_numpy()[order],
    "agitation": rng.normal(300, 15, n).round(2)[order],
    "viscosity": (1200 + 3 * rng.normal(0, 1, n)).round(2)[order],
}), ctx([R("viscosity", "minimize")], [F("agitation", "numeric")], time_col="time"))

# 7 heavy NaN (60%)
n = 150
mask_f = rng.random(n) < 0.6
mask_y = rng.random(n) < 0.6
dump("07_heavy_nan", pd.DataFrame({
    "A": np.where(mask_f, np.nan, rng.normal(0, 1, n)).round(4),
    "B": np.where(rng.random(n) < 0.6, np.nan, rng.normal(5, 1, n)).round(4),
    "strength": np.where(mask_y, np.nan, 30 + 4 * rng.normal(0, 1, n)).round(4),
}), ctx([R("strength", "maximize")], [F("A", "numeric"), F("B", "numeric")]))

# 8 text inside numeric columns
n = 100
vals = [f"{v}" for v in rng.normal(50, 5, n).round(2)]
for i in range(0, n, 7):
    vals[i] = vals[i] + "a"      # "48.32a"
dump("08_text_in_numeric", pd.DataFrame({
    "A": rng.normal(0, 1, n).round(4),
    "sensor_14": vals,
    "yield_pct": (88 + rng.normal(0, 1, n)).round(3),
}), ctx([R("yield_pct", "maximize")],
        [F("A", "numeric"), F("sensor_14", "numeric")]))

# 9 infinities
n = 100
A = rng.normal(0, 1, n)
A[3] = np.inf
A[17] = -np.inf
y = 10 + 3 * A + rng.normal(0, 0.5, n)
y[5] = np.inf
dump("09_inf_values", pd.DataFrame({"A": A.round(4), "y": y.round(4)}),
     ctx([R("y", "maximize")], [F("A", "numeric")]))

# 10 boolean dtype columns (real bool dtype via parquet)
n = 24
dump("10_bool_dtype", pd.DataFrame({
    "valve_open": rng.choice([True, False], n),
    "chiller_on": rng.choice([True, False], n),
    "output": (100 + 4 * rng.choice([1.0, -1.0], n) + 2 * rng.choice([1.0, -1.0], n)
               + rng.normal(0, 1, n)).round(3),
}), ctx([R("output", "maximize")],
        [F("valve_open", "categorical"), F("chiller_on", "categorical")]),
    fname="data.parquet")

# 10b boolean columns typed numeric in context (auto path would type them categorical;
# a user or agent may say numeric) -> probe the CCD-misread route
dump("10b_bool_numeric_typed", pd.DataFrame({
    "valve_open": rng.choice([True, False], 24),
    "chiller_on": rng.choice([True, False], 24),
    "output": (100 + 4 * rng.choice([1.0, -1.0], 24) + 2 * rng.choice([1.0, -1.0], 24)
               + rng.normal(0, 1, 24)).round(3),
}), ctx([R("output", "maximize")],
        [F("valve_open", "numeric"), F("chiller_on", "numeric")]),
    fname="data.parquet")

# 11 nullable Int64 with pd.NA (parquet required)
n = 80
A = [None if i in (2, 9, 33) else int(round(rng.normal(50, 10)))
     for i in range(n)]
y = [None if i == 7 else int(round(50 + 5 * rng.normal(0, 1)))
     for i in range(n)]
dump("11_nullable_int", pd.DataFrame({
    "batch_size": pd.Series(A, dtype="Int64"),
    "power": pd.Series([int(v) for v in rng.integers(40, 60, n)], dtype="Int64"),
    "purity": pd.Series(y, dtype="Int64")}),
    ctx([R("purity", "maximize")],
        [F("batch_size", "numeric"), F("power", "numeric")]),
    fname="data.parquet")

# 12 chinese + special-char column names, including term-name collisions
n = 40
A = np.tile([-1, 1], 20); B = np.repeat([-1, 1], 20)
dump("12_chinese_special_cols", pd.DataFrame({
    "反应 温度/℃": A, "压力(MPa)": B, "A:B": rng.normal(0, 1, n).round(4),
    "A^2": rng.normal(0, 1, n).round(4),
    "抗拉强度": (50 + 3 * A + 2 * B + rng.normal(0, 1, n)).round(4),
}), ctx([R("抗拉强度", "maximize", lsl=45, usl=60)],
        [F("反应 温度/℃", "numeric"), F("压力(MPa)", "numeric"),
         F("A:B", "numeric"), F("A^2", "numeric")]))

# 13a wide table: 500 numeric cols, observational default path
n = 300
cols = {f"x{i:03d}": rng.normal(0, 1, n).round(4) for i in range(498)}
cols["y_response"] = (rng.normal(100, 5, n) + 0.5 * cols["x007"]).round(4)
cols["sensor_time"] = pd.date_range("2026-01-01", periods=n, freq="min").strftime("%Y-%m-%d %H:%M")
dump("13a_wide_500", pd.DataFrame(cols))

# 13b wide table with explicit 60-factor designed context (term explosion probe)
n = 240
data = {}
for i in range(60):
    data[f"f{i:02d}"] = np.tile([-1, 1], n // 2)
y = rng.normal(50, 2, n)
for i in range(60):
    y += 0.8 * data[f"f{i:02d}"] * (1 if i % 3 else -1)
data["resp"] = y.round(4)
dump("13b_wide_designed_60f", pd.DataFrame(data),
     ctx([R("resp", "maximize")], [F(f"f{i:02d}", "numeric") for i in range(60)]))

# 14 long table 50k rows
n = 50_000
t = pd.date_range("2026-01-01", periods=n, freq="10s").strftime("%Y-%m-%d %H:%M:%S")
drift = np.linspace(0, 2, n)
dump("14_long_50k", pd.DataFrame({
    "time": t,
    "feed_rate": (200 + 5 * np.sin(np.linspace(0, 40, n)) + drift).round(4),
    "steam": (15 + rng.normal(0, 0.5, n)).round(4),
    "conversion": (92 + 0.8 * drift + rng.normal(0, 0.8, n)).round(4),
}), ctx([R("conversion", "maximize")],
        [F("feed_rate", "numeric"), F("steam", "numeric")], time_col="time"))

# 15a binary response, designed
n = 32
A = np.tile([-1, 1], 16); B = np.repeat([-1, 1], 16)
p = 1 / (1 + np.exp(-(0.5 * A + 0.8 * B)))
dump("15a_binary_resp_designed", pd.DataFrame({
    "A": A, "B": B, "pass_fail": rng.binomial(1, p)}),
    ctx([R("pass_fail", "maximize", lsl=0.5, usl=1.0)],
        [F("A", "numeric"), F("B", "numeric")]))

# 15b binary response observational with time
n = 400
x = rng.normal(0, 1, n)
dump("15b_binary_resp_obs", pd.DataFrame({
    "time": pd.date_range("2026-02-01", periods=n, freq="15min").strftime("%Y-%m-%d %H:%M"),
    "delta_temp": x.round(4),
    "defect": rng.binomial(1, 1 / (1 + np.exp(1.2 * x)))}),
    ctx([R("defect", "minimize", lsl=0.0, usl=0.2)],
        [F("delta_temp", "numeric")], time_col="time"))

# 16 count response, Poisson heavy tail
n = 500
lam = np.exp(1.5 + 0.4 * rng.normal(0, 1, n))
dump("16_poisson_response", pd.DataFrame({
    "catalyst": rng.normal(0, 1, n).round(4),
    "reactor": rng.normal(10, 2, n).round(4),
    "defect_count": rng.poisson(lam)}),
    ctx([R("defect_count", "minimize", usl=20)],
        [F("catalyst", "numeric"), F("reactor", "numeric")]))

# 17 rate response in [0,1]
n = 300
x = rng.normal(0, 1, n)
p = 1 / (1 + np.exp(-(1.5 * x)))
dump("17_rate_response", pd.DataFrame({
    "dosage": x.round(4),
    "first_pass_yield": np.clip(rng.binomial(500, p) / 500, 0, 1).round(4),
}), ctx([R("first_pass_yield", "maximize", lsl=0.9, usl=1.0, target=0.98)],
        [F("dosage", "numeric")]))

# 18 duplicated columns (A == C exactly), forced designed via mode_override
n = 32
A = np.tile([-1, 1], 16); B = np.repeat([-1, 1], 16)
dump("18_dup_cols_designed", pd.DataFrame({
    "A": A, "B": B, "C": A.copy(),
    "y": (5 + 2 * A + 1.5 * B + rng.normal(0, 0.5, n)).round(4)}),
    ctx([R("y", "maximize")],
        [F("A", "numeric"), F("B", "numeric"), F("C", "numeric")],
        mode_override="designed"))

# 19 group_col with small strata (each group 6 rows)
n = 60
g = np.repeat([f"G{i}" for i in range(10)], 6)
x = rng.normal(0, 1, n)
dump("19_small_groups", pd.DataFrame({
    "time": pd.date_range("2026-04-01", periods=n, freq="h").strftime("%Y-%m-%d %H:%M"),
    "lot": g,
    "pressure": (5 + x).round(4),
    "density": (1.2 + 0.05 * x + rng.normal(0, 0.01, n)).round(5),
}), ctx([R("density", "maximize")], [F("pressure", "numeric")],
        time_col="time", group_col="lot"))

# 20 all rows same timestamp
n = 150
dump("20_same_timestamp", pd.DataFrame({
    "time": ["2026-06-01 12:00:00"] * n,
    "current": rng.normal(50, 2, n).round(4),
    "torque": (30 + rng.normal(0, 1, n)).round(4),
}), ctx([R("torque", "maximize")], [F("current", "numeric")], time_col="time"))

# 21 observational parquet with a real datetime64 time column
#     (probe json serialization of pd.Timestamp in applicability_domain.time_span)
n = 300
dump("21_datetime_parquet", pd.DataFrame({
    "time": pd.date_range("2026-07-01", periods=n, freq="5min"),
    "flow": rng.normal(120, 4, n).round(4),
    "ph": (7.0 + rng.normal(0, 0.1, n)).round(4),
    "recovery": (90 + rng.normal(0, 1, n)).round(4),
}), ctx([R("recovery", "maximize")], [F("flow", "numeric"), F("ph", "numeric")],
        time_col="time"),
    fname="data.parquet")

# 22 all-NaN response named explicitly in context
n = 60
dump("22_all_nan_response", pd.DataFrame({
    "A": rng.normal(0, 1, n).round(4),
    "B": rng.normal(0, 1, n).round(4),
    "ghost": np.full(n, np.nan)}),
    ctx([R("ghost", "maximize", lsl=0, usl=10)], [F("A", "numeric"), F("B", "numeric")]))

print("all cases generated")
