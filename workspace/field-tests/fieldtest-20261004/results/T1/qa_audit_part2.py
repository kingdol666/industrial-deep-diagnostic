# -*- coding: utf-8 -*-
"""T1 audit continuation: downtime.html via stdlib HTMLParser (lxml absent in venv),
operator_notes.md, plus unified-view structural sparsity check."""
import re
from html.parser import HTMLParser
import pandas as pd

BASE = "cases/T1_preprocessor_mixed_inbox/inbox/"


class TableGrab(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.cur, self.cell = [], None, None
        self.in_table = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.in_table = True
        if self.in_table and tag == "tr":
            self.cur = []
        if self.in_table and tag in ("td", "th"):
            self.cell = []

    def handle_endtag(self, tag):
        if self.in_table and tag in ("td", "th"):
            self.cur.append("".join(self.cell).strip())
            self.cell = None
        elif self.in_table and tag == "tr":
            self.rows.append(self.cur)
            self.cur = None
        elif tag == "table":
            self.in_table = False

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


p = TableGrab()
p.feed(open(BASE + "downtime.html", encoding="utf-8").read())
df = pd.DataFrame(p.rows[1:], columns=p.rows[0])
print(f"[downtime.html] shape={df.shape}")
dup_rows = df[df.duplicated(keep=False)]
print(f"duplicate full rows: {len(dup_rows)}",
      f"at rows {sorted((dup_rows.index + 2).tolist())}" if len(dup_rows) else "")
print(f"duplicate start_time: {int(df['start_time'].duplicated().sum())}")
print(f"missing cells: {int(df.isna().sum().sum())}")
bad = df[pd.to_numeric(df["duration_min"], errors="coerce") <= 0]
for i, r in bad.iterrows():
    print(f"  IMPOSSIBLE: row{i+2} duration_min={r['duration_min']} "
          f"({r['start_time']} -> {r['end_time']}, {r['equipment']})")

df = pd.read_csv(BASE + "operator_notes.md", sep="|", skiprows=3, header=0,
                 engine="python").dropna(axis=1, how="all")
df.columns = [c.strip() for c in df.columns]
for c in df.columns:
    df[c] = df[c].astype(str).str.strip()
print(f"[operator_notes.md] shape={df.shape}")
print(f"duplicate shift_time: {int(df['shift_time'].duplicated().sum())}")
print(f"missing/empty cells: {int((df == '').sum().sum())}")
print(f"duplicate full rows: {int(df.duplicated(keep=False).sum())}")

# unified view: why missing — structural vs defect
uni = pd.read_csv("results/T1/preprocessed_data.csv")
print(f"[unified] shape={uni.shape}")
t = pd.to_datetime(uni["batch_time"])
print(f"unified time range: {t.min()} -> {t.max()}")
nonempty = uni.notna().sum()
print("non-null per column group:")
for c in uni.columns:
    print(f"  {c}: {nonempty[c]}/{len(uni)}")
# batch_records only covers 08:07-12:05 every 2-3 min -> sparse by construction
br = pd.DataFrame(__import__("json").load(open(BASE + "batch_records.json", encoding="utf-8")))
print("batch_records rows:", len(br), "so batch cols can be filled at most",
      len(br), "of", len(uni), "rows")
