#!/usr/bin/env python3
"""Step 3: Data Processing - Statistical analysis for CSTR Reactor Catalyst"""
import pandas as pd
import numpy as np
import json, os, sys

DATA = sys.argv[1] if len(sys.argv) > 1 else "data/eval_reactor_catalyst/data.csv"
RUN_DIR = sys.argv[2] if len(sys.argv) > 2 else "workspace/diagnostic-runs/202606021103187_reactor_catalyst"
OUT = f"{RUN_DIR}/02_processed"
os.makedirs(OUT, exist_ok=True)

df = pd.read_csv(DATA)

# 1. Feature Summary
feature_summary = {}
for col in df.select_dtypes(include=[np.number]).columns:
    s = df[col].dropna()
    feature_summary[col] = {
        "count": int(len(s)), "mean": round(float(s.mean()), 2),
        "std": round(float(s.std()), 2), "min": round(float(s.min()), 2),
        "p25": round(float(s.quantile(0.25)), 2), "p50": round(float(s.median()), 2),
        "p75": round(float(s.quantile(0.75)), 2), "max": round(float(s.max()), 2)
    }

# 2. Correlation Analysis
targets = ['conversion_pct', 'byproduct_ppm', 'selectivity_pct', 'quality_index']
predictors = ['reactor_temp_C', 'reactor_pressure_bar', 'h2_partial_pressure_bar',
              'feed_rate_kg_hr', 'feed_sulfur_ppm', 'cooling_duty_kW', 'delta_T_reactor_C', 'cooling_water_temp_C']
corr_matrix = {}
for t in targets:
    corr_matrix[t] = {}
    for p in predictors:
        r = df[t].corr(df[p])
        corr_matrix[t][p] = round(float(r), 4)

# 3. Pre vs Post Regeneration
pre = df[df['catalyst_bed_id'] == 'CAT-A']
post = df[df['catalyst_bed_id'] == 'CAT-A-regenerated']
regen = {}
for col in targets + ['reactor_temp_C', 'cooling_duty_kW', 'reactor_pressure_bar']:
    regen[col] = {
        "pre_mean": round(float(pre[col].mean()), 2),
        "post_mean": round(float(post[col].mean()), 2),
        "change_pct": round(float((post[col].mean() - pre[col].mean()) / pre[col].mean() * 100), 1)
    }

# 4. Trend: Early vs Late (before regeneration)
early = df[(df.index < 200)]
late_pre = df[(df.index >= 1000) & (df.index < 1200)]
trend = {}
for col in targets + ['reactor_temp_C', 'cooling_duty_kW', 'reactor_pressure_bar']:
    trend[col] = {
        "early_mean": round(float(early[col].mean()), 2),
        "late_mean": round(float(late_pre[col].mean()), 2),
        "change": round(float(late_pre[col].mean() - early[col].mean()), 2)
    }

# 5. Post-regen re-deactivation trend
post_first = df[(df['catalyst_bed_id'] == 'CAT-A-regenerated') & (df.index < 1320)]
post_later = df[df['catalyst_bed_id'] == 'CAT-A-regenerated'].tail(100)
post_trend = {}
for col in targets + ['reactor_temp_C']:
    if len(post_first) > 0 and len(post_later) > 0:
        post_trend[col] = {
            "post_early_mean": round(float(post_first[col].mean()), 2),
            "post_late_mean": round(float(post_later[col].mean()), 2),
            "re_deactivation": round(float(post_later[col].mean() - post_first[col].mean()), 2)
        }

# 6. Distractor events
events = {
    "feed_pump_trip_t750_754": {
        "feed_rate_normal": round(float(df.iloc[740:750]['feed_rate_kg_hr'].mean()), 1),
        "feed_rate_trip_min": round(float(df.iloc[750:754]['feed_rate_kg_hr'].min()), 1),
        "conversion_trip_drop": round(float(df.iloc[754:758]['conversion_pct'].mean() - df.iloc[750:754]['conversion_pct'].min()), 1),
        "duration_hours": 4,
        "recovery": "full within 4h"
    },
    "h2_maintenance_t550_560": {
        "h2_before": round(float(df.iloc[540:550]['h2_partial_pressure_bar'].mean()), 2),
        "h2_during_min": round(float(df.iloc[550:560]['h2_partial_pressure_bar'].min()), 2),
        "h2_after": round(float(df.iloc[560:570]['h2_partial_pressure_bar'].mean()), 2),
        "duration_hours": 10,
        "recovery": "full"
    }
}

key_corrs = {
    "conversion_vs_byproduct": round(float(df['conversion_pct'].corr(df['byproduct_ppm'])), 4),
    "conversion_vs_selectivity": round(float(df['conversion_pct'].corr(df['selectivity_pct'])), 4),
    "conversion_vs_temp": round(float(df['conversion_pct'].corr(df['reactor_temp_C'])), 4),
    "conversion_vs_cooling": round(float(df['conversion_pct'].corr(df['cooling_duty_kW'])), 4),
    "temp_vs_cooling_water": round(float(df['reactor_temp_C'].corr(df['cooling_water_temp_C'])), 4),
    "temp_vs_pressure": round(float(df['reactor_temp_C'].corr(df['reactor_pressure_bar'])), 4)
}

result = {
    "feature_summary": feature_summary,
    "correlation_matrix": corr_matrix,
    "key_correlations": key_corrs,
    "regeneration_comparison": regen,
    "trend_analysis": trend,
    "post_regen_trend": post_trend,
    "distractor_events": events
}

with open(f"{OUT}/feature_summary.json", 'w') as f:
    json.dump(result, f, indent=2)

# Print critical stats for Diagnostician
print("=== FEATURE SUMMARY ===")
for col in targets:
    print(f"{col}: μ={feature_summary[col]['mean']}, σ={feature_summary[col]['std']}, [{feature_summary[col]['min']}-{feature_summary[col]['max']}]")

print("\n=== KEY CORRELATIONS ===")
for k, v in key_corrs.items():
    print(f"{k}: r={v}")

print("\n=== REGENERATION IMPACT ===")
for col, v in regen.items():
    print(f"{col}: pre={v['pre_mean']} → post={v['post_mean']} ({v['change_pct']}%)")

print("\n=== TREND (pre-regeneration) ===")
for col, v in trend.items():
    print(f"{col}: early={v['early_mean']} → late={v['late_mean']} (Δ={v['change']})")

if post_trend:
    print("\n=== POST-REGENERATION RE-DEACTIVATION ===")
    for col, v in post_trend.items():
        print(f"{col}: early={v['post_early_mean']} → late={v['post_late_mean']} (Δ={v['re_deactivation']})")

print("\n=== DISTRACTOR EVENTS ===")
for evt_name, evt_data in events.items():
    print(f"{evt_name}: {json.dumps(evt_data)}")

print(f"\nResults saved to {OUT}/feature_summary.json")