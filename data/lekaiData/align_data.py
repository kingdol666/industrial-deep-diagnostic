"""Align scratch defects with 9-day process data"""
import pandas as pd
import numpy as np

base = "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic"

merged = pd.read_csv(f"{base}/data/lekaiData/merged_process_data_full.csv", parse_dates=['time'])
print(f"Process data: {len(merged)} rows, {merged['time'].min()} to {merged['time'].max()}")

scratch = pd.read_csv(f"{base}/data/lekaiData/scratch_defects.csv")
scratch['ts_start'] = pd.to_datetime(scratch['ts_start'], errors='coerce')
scratch['ts_end'] = pd.to_datetime(scratch['ts_end'], errors='coerce')
scratch['date'] = pd.to_datetime(scratch['date'], errors='coerce')

overlap = scratch[(scratch['date'] >= pd.Timestamp('2026-05-04')) &
                  (scratch['date'] <= pd.Timestamp('2026-05-14'))]
print(f"Overlap records: {len(overlap)}")

results = []
num_cols = [c for c in merged.columns if c != 'time' and merged[c].dtype in ('float64', 'int64')]

for idx, row in overlap.iterrows():
    ts_s, ts_e = row['ts_start'], row['ts_end']
    if pd.isna(ts_s) or pd.isna(ts_e):
        continue
    mask = (merged['time'] >= ts_s) & (merged['time'] <= ts_e)
    proc_window = merged[mask]
    if len(proc_window) < 5:
        continue

    stats = {'batch_id': row['轴号'], 'ts_start': ts_s, 'ts_end': ts_e,
             'scratch_count': row['scratch'], 'meters': row['米数'],
             'model': row['型号'], 'date': row['date']}

    for col in num_cols:
        vals = proc_window[col].dropna()
        if len(vals) > 0:
            stats[f'{col}_mean'] = vals.mean()
            stats[f'{col}_std'] = vals.std()
            stats[f'{col}_min'] = vals.min()
            stats[f'{col}_max'] = vals.max()

    results.append(stats)

aligned = pd.DataFrame(results)
print(f"Aligned records: {len(aligned)}")
print(f"Scratch: mean={aligned['scratch_count'].mean():.1f}, median={aligned['scratch_count'].median():.0f}, max={aligned['scratch_count'].max():.0f}")

print(f"\nTop 15 scratch batches:")
top = aligned.nlargest(15, 'scratch_count')[['batch_id', 'date', 'scratch_count', 'model']]
print(top.to_string())

aligned['group'] = pd.cut(aligned['scratch_count'], bins=[-1, 10, 30, 100, 10000],
                          labels=['normal', 'moderate', 'high', 'extreme'])
print(f"\nGroup counts: {dict(aligned['group'].value_counts())}")

daily = aligned.groupby(aligned['ts_start'].dt.date)['scratch_count'].agg(['mean', 'sum', 'count'])
print(f"\nDaily scratch:")
print(daily.to_string())

out = f"{base}/data/lekaiData/aligned_scratch_process_full.csv"
aligned.to_csv(out, index=False)
print(f"\nSaved: {out}")
print(f"Columns: {len(aligned.columns)}")
