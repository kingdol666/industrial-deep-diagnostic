"""Align multiple defect types with 9-day process data"""
import pandas as pd
import numpy as np

base = "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic"

merged = pd.read_csv(f"{base}/data/lekaiData/merged_process_data_full.csv", parse_dates=['time'])
print(f"Process data: {len(merged)} rows, {merged['time'].min()} to {merged['time'].max()}")

defects = pd.read_excel(f"{base}/data/lekaiData/2026年杂质点统计.xlsx", sheet_name="CCD点子统计")

# Parse date and time
defects['date_int'] = pd.to_numeric(defects['日期'], errors='coerce')
defects['date'] = defects['date_int'].apply(lambda d: pd.to_datetime(str(int(d)), format='%Y%m%d') if pd.notna(d) else pd.NaT)

def parse_time_window(time_str):
    if pd.isna(time_str): return None, None
    try:
        s = str(time_str).replace('：', ':')
        parts = s.split('-')
        if len(parts) != 2: return None, None
        return parts[0].strip(), parts[1].strip()
    except: return None, None

defects['ts_s'], defects['ts_e'] = zip(*defects['下轴时间'].apply(parse_time_window))

def build_ts(row):
    if pd.isna(row['date']): return None, None
    try:
        if row['ts_s'] and row['ts_e']:
            bd = row['date']
            ps, pe = row['ts_s'].split(':'), row['ts_e'].split(':')
            sh, sm = int(ps[0]), int(ps[1])
            eh, em = int(pe[0]), int(pe[1])
            start = bd.replace(hour=sh, minute=sm)
            end = (bd + pd.Timedelta(days=1)).replace(hour=eh, minute=em) if eh < sh else bd.replace(hour=eh, minute=em)
            return start, end
    except: pass
    return None, None

defects['ts_start'], defects['ts_end'] = zip(*defects.apply(build_ts, axis=1))

# Target defect types (melt quality related)
target_defects = {
    '膜内点': 'film_points',
    '低聚物': 'oligomer',
    '粉尘': 'dust',
    '气泡': 'bubbles',
    '熔体斑': 'melt_spots',
}

# Convert target columns to numeric
for col in target_defects:
    defects[col] = pd.to_numeric(defects[col], errors='coerce')

# Filter to process data range
overlap = defects[(defects['date'] >= pd.Timestamp('2026-05-04')) &
                  (defects['date'] <= pd.Timestamp('2026-05-14'))]
print(f"Overlap records: {len(overlap)}")

# Build aligned dataset
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

    stats = {
        'batch_id': row['轴号'], 'ts_start': ts_s, 'ts_end': ts_e,
        'meters': row['米数'], 'model': row['型号'], 'date': row['date'],
    }
    # Add all defect counts
    for col, eng_name in target_defects.items():
        stats[eng_name] = row[col] if pd.notna(row[col]) else 0

    # Add process parameter stats
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
for col, eng in target_defects.items():
    s = aligned[eng]
    print(f"  {col}({eng}): mean={s.mean():.1f}, median={s.median():.0f}, max={s.max():.0f}, sum={s.sum():.0f}")

out = f"{base}/data/lekaiData/aligned_multidefect.csv"
aligned.to_csv(out, index=False)
print(f"\nSaved: {out}")
print(f"Columns: {len(aligned.columns)}")
