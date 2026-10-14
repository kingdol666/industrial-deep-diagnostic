"""Phase 2.5 evidence: batch -> product-model timeline and switch boundaries.

Source: data/lekaiData/aligned_multidefect.csv (read-only), columns
batch_id / ts_start / ts_end / model. The `model` label carries trailing
whitespace in the raw file -> stripped here (dirty-label handling is recorded).

Output: 00_input/model_switch_boundaries.json  (timeline + boundaries + counts)
"""
from __future__ import annotations

import csv
import json
import os

REPO = r"D:\codes\industrial-deep-diagnostic"
SRC = os.path.join(REPO, "data", "lekaiData", "aligned_multidefect.csv")
OUT = os.path.join(REPO, "workspace", "lekai", "run-stability-full",
                   "00_input", "model_switch_boundaries.json")


def main() -> None:
    rows = []
    with open(SRC, encoding="utf-8-sig", newline="") as f:
        for rec in csv.DictReader(f):
            rows.append({
                "batch_id": rec["batch_id"],
                "ts_start": rec["ts_start"],
                "ts_end": rec["ts_end"],
                "model_raw": rec["model"],
                "model": rec["model"].strip(),
            })

    dirty = sorted({r["model_raw"] for r in rows if r["model_raw"] != r["model"]})
    rows.sort(key=lambda r: (r["ts_start"], r["batch_id"]))

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["model"]] = counts.get(r["model"], 0) + 1

    boundaries = []
    for prev, cur in zip(rows, rows[1:]):
        if prev["model"] != cur["model"]:
            boundaries.append({
                "at_ts": cur["ts_start"],
                "from_model": prev["model"],
                "to_model": cur["model"],
                "prev_batch": prev["batch_id"],
                "next_batch": cur["batch_id"],
                "gap_minutes_between_batches": _gap_min(prev["ts_end"], cur["ts_start"]),
            })

    payload = {
        "source_file": "data/lekaiData/aligned_multidefect.csv",
        "purpose": "Phase 2.5 交叉印证：把报告工况分段表中的变点对应到产品型号切换上",
        "batch_count": len(rows),
        "model_count": len(counts),
        "window": {"first_ts_start": rows[0]["ts_start"],
                   "last_ts_end": max(r["ts_end"] for r in rows)},
        "dirty_labels": {
            "note": "model 原始标签带尾随空格，已在比对前 strip；原始值见 model_raw_count",
            "raw_count": len({r["model_raw"] for r in rows}),
            "distinct_raw_with_trailing_space": dirty,
        },
        "model_counts": dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "boundaries": boundaries,
        "timeline": [{k: r[k] for k in ("batch_id", "ts_start", "ts_end", "model")} for r in rows],
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"batches={len(rows)} models={len(counts)} boundaries={len(boundaries)}")
    print("model_counts:", json.dumps(payload["model_counts"], ensure_ascii=False))
    print("window:", payload["window"])
    print("boundaries:")
    for b in boundaries:
        print(f"  {b['at_ts']}  {b['from_model']} -> {b['to_model']} "
              f"(prev_end->start gap={b['gap_minutes_between_batches']} min)")


def _gap_min(end_prev: str, start_cur: str) -> float | None:
    from datetime import datetime
    try:
        a = datetime.fromisoformat(end_prev)
        b = datetime.fromisoformat(start_cur)
    except ValueError:
        return None
    return round((b - a).total_seconds() / 60.0, 1)


if __name__ == "__main__":
    main()
