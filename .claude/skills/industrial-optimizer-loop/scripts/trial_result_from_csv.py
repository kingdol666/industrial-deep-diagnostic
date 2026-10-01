#!/usr/bin/env python
"""trial_result_from_csv.py — manual CSV -> trial_result.json converter (AC C11).

Column convention (template, see tests/fixtures C11):
  trial_id, status, [failure_reason], [measured_at], [operator_note],
  then per metric either one column `<metric>` (single replicate) or replicate
  columns `<metric>#1`, `<metric>#2`, ... (contiguous from 1; `metric_1` also
  accepted).

Discipline (inbox 错误回执协议, plan §7):
  - validation failure -> write `<out>.error.json` with human-readable Chinese
    error + fix guidance, exit 1, and NEVER write a half-baked result JSON.
  - statuses/failure rules mirror the trial_result contract (O-G6b):
    failed/safety_aborted require failure_reason; only designed trials may be
    reported is checked at ingest (needs the design file, not the CSV).
"""

import csv
import json
import sys
from pathlib import Path

OPTCORE_PARENT = Path(__file__).resolve().parent
if str(OPTCORE_PARENT) not in sys.path:
    sys.path.insert(0, str(OPTCORE_PARENT))

from optcore import TRIAL_STATUS, _contained, now  # noqa: E402

RESERVED = {"trial_id", "status", "failure_reason", "measured_at", "operator_note",
            "round_id", "campaign_id"}


def error_receipt(out_path, errors, hints):
    receipt = {
        "error_file": True,
        "generated_at": now(),
        "converter": "trial_result_from_csv.py",
        "errors": errors,
        "fix_guidance": hints,
        "message": "CSV 转换失败：未产出 trial_result.json。请按 fix_guidance 修正后重试；"
                   "本文件为 inbox 错误回执协议的人类可读回执。",
    }
    out = _contained(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"[csv] ERROR receipt written: {out}", file=sys.stderr)


def parse_metric_columns(header):
    """Map metric base name -> ('single'|'replicates', ordered columns).

    `<metric>` + `<metric>#2..#n` (or `_2.._n`) siblings => replicates with
    the bare column counting as replicate #1.
    """
    single_cols, rep_cols = set(), {}
    for col in header:
        if col in RESERVED or not col:
            continue
        base, sep, idx = col.rpartition("#")
        if not sep:
            base2, sep2, idx2 = col.rpartition("_")
            if sep2 and idx2.isdigit() and base2 and base2 not in RESERVED:
                base, idx = base2, idx2
            else:
                single_cols.add(col)
                continue
        rep_cols.setdefault(base, set()).add((int(idx), col))
    bases = {}
    for col in sorted(single_cols):
        if col in rep_cols:
            rep_cols[col].add((1, col))  # bare column = replicate #1
            bases[col] = "replicates"
        else:
            bases[col] = "single"
    for base in rep_cols:
        bases.setdefault(base, "replicates")
    return bases, {b: sorted(v) for b, v in rep_cols.items()}


def convert(csv_path, out_path, campaign_id=None, round_id=None):
    src = _contained(csv_path)
    out = _contained(out_path)
    errors, hints = [], []
    with src.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or [])
        rows = list(reader)
    if "trial_id" not in header:
        errors.append("缺少 trial_id 列")
        hints.append("CSV 必须包含 trial_id 列（格式 R001-T01，与 trial_design 一致）")
    if "status" not in header:
        errors.append("缺少 status 列")
        hints.append(f"CSV 必须包含 status 列，允许值: {TRIAL_STATUS}")
    if errors:
        error_receipt(out.with_suffix(out.suffix + ".error.json"), errors, hints)
        return 1
    bases, rep_cols = parse_metric_columns(header)
    if not bases:
        errors.append("未识别任何测量列（metric 列）")
        hints.append("测量列命名：单次 `<metric>`；重复 `<metric>#1..<metric>#n`（或 `_1`）")
        error_receipt(out.with_suffix(out.suffix + ".error.json"), errors, hints)
        return 1

    trials, seen = [], set()
    for i, row in enumerate(rows, start=2):
        tid = (row.get("trial_id") or "").strip()
        status = (row.get("status") or "").strip()
        where = f"第 {i} 行 (trial_id={tid or '<空>'})"
        if not tid:
            errors.append(f"{where}: trial_id 为空")
            hints.append("每个布点一行；trial_id 必须与 trial_design.json 的 trial_id 一致")
            continue
        if tid in seen:
            errors.append(f"{where}: trial_id 重复")
            hints.append("一个布点一行；重复测量请用重复列 `<metric>#2` 等")
            continue
        seen.add(tid)
        if status not in TRIAL_STATUS:
            errors.append(f"{where}: status '{status}' 不在允许枚举 {TRIAL_STATUS}")
            hints.append("status 取值: completed / failed / partial / safety_aborted / late")
            continue
        if status in ("failed", "safety_aborted") and \
                not (row.get("failure_reason") or "").strip():
            errors.append(f"{where}: status={status} 但 failure_reason 为空（契约 O-G6b）")
            hints.append("failed / safety_aborted 行必须填写 failure_reason（中文可读原因）")
        measurements = {}
        for base, kind in bases.items():
            if kind == "single":
                raw = (row.get(base) or "").strip()
                if raw == "":
                    continue
                try:
                    measurements[base] = [float(raw)]
                except ValueError:
                    errors.append(f"{where}: 列 {base} 值 '{raw}' 不是数值")
                    hints.append(f"测量列 {base} 只接受数值（空 = 缺测）")
            else:
                cols = sorted(rep_cols.get(base, []))
                vals = []
                for _idx, col in cols:
                    raw = (row.get(col) or "").strip()
                    if raw == "":
                        continue
                    try:
                        vals.append(float(raw))
                    except ValueError:
                        errors.append(f"{where}: 列 {col} 值 '{raw}' 不是数值")
                        hints.append(f"重复列 {col} 只接受数值（空 = 该次缺测）")
                if vals:
                    measurements[base] = vals
        entry = {"trial_id": tid, "status": status, "measurements": measurements}
        if (row.get("failure_reason") or "").strip():
            entry["failure_reason"] = row["failure_reason"].strip()
        if (row.get("measured_at") or "").strip():
            entry["measured_at"] = row["measured_at"].strip()
        if (row.get("operator_note") or "").strip():
            entry["operator_note"] = row["operator_note"].strip()
        trials.append(entry)
    if errors:
        error_receipt(out.with_suffix(out.suffix + ".error.json"), errors,
                      sorted(set(hints)))
        return 1
    payload = {"result_version": "1.0",
               "campaign_id": campaign_id or "UNKNOWN",
               "round_id": round_id or "R000",
               "trials": trials,
               "ingest_meta": {"source": "manual_csv", "ingested_at": now()}}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"[csv] wrote {out} ({len(trials)} trials)")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--template" in argv:
        print("trial_id,status,failure_reason,measured_at,operator_note,"
              "purity,purity#2,purity#3")
        print("R001-T01,completed,,,,73.2,72.9,73.4")
        print("R001-T02,failed,反应釜温度超限报警中断,,,,,")
        return 0
    if len(argv) < 2:
        print("Usage: python trial_result_from_csv.py <in.csv> <out.json> "
              "[--campaign-id ID] [--round-id Rnnn] | --template", file=sys.stderr)
        return 2
    csv_path, out_path = argv[0], argv[1]
    cid = argv[argv.index("--campaign-id") + 1] if "--campaign-id" in argv else None
    rid = argv[argv.index("--round-id") + 1] if "--round-id" in argv else None
    return convert(csv_path, out_path, campaign_id=cid, round_id=rid)


if __name__ == "__main__":
    sys.exit(main())
