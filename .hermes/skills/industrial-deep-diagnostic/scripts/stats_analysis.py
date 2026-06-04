#!/usr/bin/env python3
"""Lightweight statistical analysis — fallback when stats.mjs is too slow.

Usage: uv run python stats_analysis.py <data.json> <output_dir> \\
          [--target-cols col1 col2 ...] \\
          [--predictor-cols col1 col2 ...] \\
          [--group-col product_grade] \\
          [--time-col timestamp] \\
          [--exclude-cols col1 col2 ...]

This script is a GENERIC TEMPLATE. It has NO hardcoded column names, process-
specific keywords, or domain assumptions. The data-processor agent reads the
ontology and passes the actual column names as CLI arguments.

If --target-cols is omitted, the script infers targets from statistical
signatures (not keyword matching): columns with outlier-heavy distributions,
trends, or high variance relative to their neighbors.
"""
import json, sys, os, math, argparse
from statistics import mean, stdev

parser = argparse.ArgumentParser(description="Generic Statistical Analysis Engine")
parser.add_argument("data_json", help="Path to cleaned_data.json")
parser.add_argument("output_dir", nargs="?", default=".", help="Output directory")
parser.add_argument("--target-cols", nargs="+", default=[], help="Target/quality column names")
parser.add_argument("--predictor-cols", nargs="+", default=[], help="Predictor/parameter column names")
parser.add_argument("--group-col", nargs="+", default=[], help="Group/stratification column(s)")
parser.add_argument("--time-col", default=None, help="Timestamp column to exclude from numerics")
parser.add_argument("--exclude-cols", nargs="+", default=[], help="Additional columns to exclude from analysis")
parser.add_argument("--max-lag", type=int, default=20, help="Max CCF lag")
args = parser.parse_args()

DATA_PATH = args.data_json
OUTPUT_DIR = args.output_dir

if not os.path.exists(DATA_PATH):
    print(f"ERROR: Data file not found: {DATA_PATH}", file=sys.stderr)
    sys.exit(1)
with open(DATA_PATH) as f:
    rows = json.load(f)

if isinstance(rows, dict):
    for key in ["data", "rows", "records"]:
        if key in rows and isinstance(rows[key], list):
            rows = rows[key]
            break
    else:
        rows = list(rows.values())

n = len(rows)
all_col_names = list(rows[0].keys())

# ── Smart column classification (no hardcoded keywords) ──
# Exclude categorical/derived/metadata columns
def _is_categorical(col, sample=100):
    """Heuristic: if <20 unique values in first N rows → categorical"""
    vals = set()
    for r in rows[:min(sample, n)]:
        v = r.get(col, '')
        try:
            float(v)  # is numeric?
            # Still could be categorical if very few unique values
            vals.add(str(v))
            if len(vals) > 20:
                break
        except (ValueError, TypeError):
            return True  # non-numeric → definitely categorical
    # If we collected every value in the sample and still <20 uniques → categorical
    all_vals = set()
    for r in rows[:min(1000, n)]:
        all_vals.add(str(r.get(col, '')))
    return len(all_vals) < 15

categorical_cols = set(c for c in all_col_names if _is_categorical(c))

exclude = set(args.exclude_cols)
time_col = args.time_col or ('timestamp' if 'timestamp' in all_col_names else None)
if time_col: exclude.add(time_col)

numeric_cols = []
for c in all_col_names:
    if c in exclude or c in categorical_cols:
        continue
    try:
        float(rows[0].get(c, ''))
        numeric_cols.append(c)
    except (ValueError, TypeError):
        continue

# ── Target detection (no keyword guessing) ──
if args.target_cols:
    target_cols = [c for c in args.target_cols if c in all_col_names]
else:
    # Infer targets from statistical signatures: columns with strongest trends
    # or highest variance are likely quality/defect metrics
    score = {}
    for c in numeric_cols:
        vals = [float(r.get(c, 0)) for r in rows]
        if len(vals) < 2: continue
        trend = abs(vals[-1] - vals[0]) / (max(abs(v) for v in vals[:10] if v != 0) + 1)
        cv = stdev(vals) / (abs(mean(vals)) + 1) if mean(vals) != 0 else stdev(vals)
        score[c] = trend * 0.6 + cv * 0.4
    # Top ~6 are likely quality targets
    sorted_cols = sorted(score, key=score.get, reverse=True)[:6]
    target_cols = sorted_cols

predictor_cols = args.predictor_cols if args.predictor_cols else [
    c for c in numeric_cols if c not in target_cols
]

# ── Group column ──
group_col = args.group_col[0] if args.group_col else None
if not group_col:
    for c in categorical_cols:
        vals = set(str(rows[i].get(c, '')) for i in range(min(1000, n)))
        if 2 <= len(vals) <= 20:
            group_col = c
            break

print(f"Rows: {n}, Numeric: {len(numeric_cols)}, Targets: {len(target_cols)}, Predictors: {len(predictor_cols)}")
if target_cols: print(f"  Targets: {target_cols[:8]}")
if group_col: print(f"  Group: {group_col}")

# ── Core statistics (pure math — no domain assumptions) ──
def pearson(x, y):
    ni = len(x)
    mx, my = mean(x), mean(y)
    num = sum((x[i]-mx)*(y[i]-my) for i in range(ni))
    den = math.sqrt(sum((xi-mx)**2 for xi in x) * sum((yi-my)**2 for yi in y))
    return num/den if den != 0 else 0

def spearman(x, y):
    rx = {v: i for i, v in enumerate(sorted(set(x)))}
    ry = {v: i for i, v in enumerate(sorted(set(y)))}
    return pearson([rx[v] for v in x], [ry[v] for v in y])

def detrended(x, y):
    t = list(range(len(x)))
    mt, mx = mean(t), mean(x)
    sx = sum((t[i]-mt)*(x[i]-mx) for i in range(len(x))) / max(sum((ti-mt)**2 for ti in t), 1)
    xr = [x[i] - sx*(t[i]-mt) - mx for i in range(len(x))]
    my = mean(y)
    sy = sum((t[i]-mt)*(y[i]-my) for i in range(len(x))) / max(sum((ti-mt)**2 for ti in t), 1)
    yr = [y[i] - sy*(t[i]-mt) - my for i in range(len(x))]
    return pearson(xr, yr)

def stratified(x, y, gc):
    groups = {}
    for i, r in enumerate(rows):
        g = str(r.get(gc, 'unknown'))
        groups.setdefault(g, {'x': [], 'y': []})
        groups[g]['x'].append(x[i]); groups[g]['y'].append(y[i])
    return {g: round(pearson(v['x'], v['y']), 3) for g, v in groups.items() if len(v['x']) > 5}

def ccf(x, y, max_lag=20):
    ni = len(x)
    mx, my = mean(x), mean(y)
    dx, dy = [xi-mx for xi in x], [yi-my for yi in y]
    var = math.sqrt(sum(d**2 for d in dx) * sum(d**2 for d in dy))
    lags = {}
    for lag in range(-max_lag, max_lag + 1):
        k = abs(lag)
        if k >= ni: continue
        xy = sum(dx[i]*dy[i+k] for i in range(ni-k)) if lag < 0 else sum(dx[i+k]*dy[i] for i in range(ni-k))
        lags[lag] = round(xy/var, 3) if var else 0
    return lags

# Extract
values = {c: [float(r[c]) for r in rows] for c in numeric_cols}

result = {
    "metadata": {"n_rows": n, "n_columns": len(numeric_cols), "target_columns": target_cols},
    "trends": {},
    "correlations": {},
    "detrended_correlations": {},
    "spearman_correlations": {},
    "stratified_correlations": {},
    "cross_correlations": {},
    "statistical_warnings": []
}

for c in numeric_cols:
    v = values[c]
    t = list(range(len(v)))
    mt, mv = mean(t), mean(v)
    slope = sum((t[i]-mt)*(v[i]-mv) for i in range(len(v))) / max(sum((ti-mt)**2 for ti in t), 1)
    s = sorted(v); q1, q3 = s[n//4], s[3*n//4]
    result["trends"][c] = {"mean": round(mean(v), 3), "std": round(stdev(v), 3),
                           "slope": round(slope, 6), "trending": abs(slope) > 0.001}

for target in target_cols:
    if target not in values: continue
    tv = values[target]
    result["correlations"][target] = {}
    result["detrended_correlations"][target] = {}
    result["spearman_correlations"][target] = {}
    result["stratified_correlations"][target] = {}

    for col in predictor_cols:
        if col not in values: continue
        cv = values[col]
        r = pearson(tv, cv)
        dr = detrended(tv, cv)
        sr = spearman(tv, cv)

        result["correlations"][target][col] = round(r, 4)
        result["detrended_correlations"][target][col] = round(dr, 4)
        result["spearman_correlations"][target][col] = round(sr, 4)

        if group_col:
            sc = stratified(tv, cv, group_col)
            result["stratified_correlations"][target][col] = sc
            if sc:
                avg = mean(sc.values())
                if abs(avg) > 0.3 and avg * r < 0:
                    result["statistical_warnings"].append({
                        "type": "SIMPSONS_PARADOX", "target": target, "predictor": col,
                        "aggregate_r": round(r, 3), "avg_within_group_r": round(avg, 3)})

        if abs(r) > 0.3 and dr != 0:
            att = abs((abs(r)-abs(dr))/r)*100 if r != 0 else 0
            if att > 50:
                result["statistical_warnings"].append({
                    "type": "TREND_CONFOUNDING", "target": target, "predictor": col,
                    "raw_r": round(r, 3), "detrended_r": dr, "attenuation_pct": round(att, 1)})

        if abs(r - sr) > 0.15:
            result["statistical_warnings"].append({
                "type": "OUTLIER_SENSITIVITY", "target": target, "predictor": col,
                "pearson_r": round(r, 3), "spearman_r": sr, "divergence": round(abs(r-sr), 3)})

top_pairs = set()
for t in target_cols:
    if t not in result["correlations"]: continue
    for col, r in sorted(result["correlations"][t].items(), key=lambda x: abs(x[1]), reverse=True)[:10]:
        top_pairs.add((col, t))
for a, b in top_pairs:
    result["cross_correlations"][f"{a} vs {b}"] = ccf(values[a], values[b], args.max_lag)

print(f"Warnings: {len(result['statistical_warnings'])}")
for t in target_cols[:5]:
    if t not in result["correlations"]: continue
    for c, r in sorted(result["correlations"][t].items(), key=lambda x: abs(x[1]), reverse=True)[:3]:
        dr = result["detrended_correlations"][t].get(c, 0)
        print(f"  {t} vs {c}: r={r:.3f} (detrended={dr:.3f})")

output_path = os.path.join(OUTPUT_DIR, "feature_summary.json")
with open(output_path, 'w') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
print(f"Written to {output_path}")
