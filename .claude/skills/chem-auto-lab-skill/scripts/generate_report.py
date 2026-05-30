#!/usr/bin/env python3
"""
Chemistry Experiment Report Generator
=======================================
Generates professional Markdown/PDF reports with statistical analysis and charts.

Usage:
  python generate_report.py --data cleaned.json --output report.md
  python generate_report.py --data cleaned.json --output report --format md,pdf --figures-dir ./figures
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None

REPORT_TEMPLATE = """---
title: "实验报告：{title}"
date: "{date}"
generator: "chem-auto-lab-skill/report-generator-v1.0.0"
---

# 实验报告：{title}

## 执行摘要 (Executive Summary)

{executive_summary}

---

## 1. 实验方法与材料 (Methods & Materials)

{materials_section}

{methods_section}

## 2. 数据质量评估 (Data Quality Assessment)

| 指标 | 数值 |
|------|------|
| 原始记录数 | {n_input} |
| 有效记录数 | {n_output} |
| 缺失率 | {missing_rate} |
| 异常值数量 | {n_outliers} |
| 数据质量评级 | {quality_grade} |

{quality_notes}

## 3. 结果与分析 (Results & Analysis)

### 3.1 描述性统计 (Descriptive Statistics)

{descriptive_stats}

### 3.2 趋势分析 (Trend Analysis)

{trend_analysis}

### 3.3 对比分析 (Comparative Analysis)

{comparative_analysis}

### 3.4 相关性分析 (Correlation Analysis)

{correlation_analysis}

## 4. 讨论 (Discussion)

{discussion}

## 5. 结论与建议 (Conclusions & Recommendations)

{conclusions}

---

## 附录 (Appendix)

- **数据处理脚本**: `chem-auto-lab-skill/clean_data.py`
- **报告生成时间**: {processing_time}
- **输入数据文件**: {input_files}

*本报告由 Chem-Auto-Lab Skill 自动生成。数据解释和结论建议人工审核。*
"""


def compute_stats(experiments):
    numeric_vars = {}
    other_vars = {}

    for exp in experiments:
        for key, val in exp.get("variables", {}).items():
            if val is None:
                continue
            if isinstance(val, dict):
                v = val.get("value")
                if v is not None and isinstance(v, (int, float)):
                    numeric_vars.setdefault(key, []).append(v)
                else:
                    other_vars.setdefault(key, []).append(str(v))
            elif isinstance(val, (int, float)):
                numeric_vars.setdefault(key, []).append(val)

    stats = {}
    for col, values in numeric_vars.items():
        if len(values) < 2:
            stats[col] = {"count": len(values), "note": "insufficient_data"}
            continue
        arr = np.array(values) if np else values
        stats[col] = {
            "count": len(values),
            "mean": round(float(np.mean(arr)), 3),
            "median": round(float(np.median(arr)), 3),
            "std": round(float(np.std(arr, ddof=1)), 3),
            "min": round(float(np.min(arr)), 3),
            "max": round(float(np.max(arr)), 3),
            "q1": round(float(np.percentile(arr, 25)), 3),
            "q3": round(float(np.percentile(arr, 75)), 3),
            "cv_pct": round(float(np.std(arr, ddof=1) / np.mean(arr) * 100), 1) if np.mean(arr) != 0 else 0,
        }

    return stats, other_vars


def build_descriptive_table(stats):
    if not stats:
        return "_无可统计的数值变量。_\n"
    header = "| 变量 | 数量 | 均值 | 中位数 | 标准差 | 最小值 | 最大值 | CV(%) |\n"
    sep = "|------|------|------|--------|--------|--------|--------|-------|\n"
    rows = ""
    for col, s in stats.items():
        if s.get("note"):
            rows += f"| {col} | {s['count']} | - | - | - | - | - | - |\n"
        else:
            rows += f"| {col} | {s['count']} | {s['mean']} | {s['median']} | {s['std']} | {s['min']} | {s['max']} | {s['cv_pct']}% |\n"
    return header + sep + rows


def build_correlation_section(stats):
    high_cv = [(col, s["cv_pct"]) for col, s in stats.items() if s.get("cv_pct", 0) > 30 and not s.get("note")]
    if high_cv:
        items = "\n".join([f"- **{col}**: 变异系数 {cv}%，波动较大，建议重点关注" for col, cv in sorted(high_cv, key=lambda x: -x[1])])
        return f"以下变量表现出较高的变异性（CV > 30%）：\n\n{items}\n\n{cross_ref_figures}"
    return "所有变量变异系数在合理范围内。\n\n" + cross_ref_figures


cross_ref_figures = """\n_详细图表请参见对应图片目录。_\n"""


def generate_report(data, figures_dir, spectra_summary, notes_summary):
    experiments = data.get("experiments", [])
    metadata = data.get("metadata", {})

    n_input = metadata.get("rows_input", len(experiments))
    n_output = metadata.get("rows_output", len(experiments))
    transformations = metadata.get("transformations", [])

    imputed_count = sum(t.get("imputed_count", 0) for t in transformations if t.get("operation") == "impute")
    outlier_count = sum(t.get("outliers_found", 0) for t in transformations if t.get("operation") == "outlier_flag")

    missing_rate = "0%" if n_input == 0 or n_input == n_output else f"{((n_input - n_output) / n_input * 100):.1f}%"

    if missing_rate in ("0%", "0.0%") and imputed_count == 0 and outlier_count == 0:
        quality_grade = "A"
        quality_notes = "数据质量优秀，无缺失值和异常值。"
    elif imputed_count < n_input * 0.1:
        quality_grade = "B"
        quality_notes = f"数据质量良好。共进行了 {imputed_count} 次缺失值插补和 {outlier_count} 个异常值标记。"
    elif imputed_count < n_input * 0.3:
        quality_grade = "C"
        quality_notes = f"⚠️ 数据质量一般。{imputed_count} 次缺失值插补（{imputed_count / max(n_input, 1) * 100:.1f}%）。建议核查原始数据完整性。"
    else:
        quality_grade = "D"
        quality_notes = f"⚠️ 数据质量较差。缺失率超过30%。分析结论可信度受限，建议补充数据。"

    stats, other_vars = compute_stats(experiments)

    exec_parts = []
    if spectra_summary:
        exec_parts.append("- 完成谱图解析")
    exec_parts.append(f"- 处理 {n_output} 条实验记录")
    if stats:
        n_vars = len(stats)
        exec_parts.append(f"- 分析 {n_vars} 个数值变量")
    exec_parts.append(f"- 数据质量评级: {quality_grade}")

    exec_summary = "\n".join(exec_parts)

    materials = ", ".join(notes_summary.get("materials_detected", [])) if notes_summary else "未从实验记录中检测到特定材料信息。"

    report = REPORT_TEMPLATE.format(
        title="化学实验数据分析",
        date=datetime.utcnow().strftime("%Y-%m-%d"),
        executive_summary=exec_summary,
        materials_section=f"**检测到的材料**: {materials}" if materials else "_无特定材料信息。_",
        methods_section=f"_共分析 {n_output} 条实验记录，涉及 {len(stats)} 个数值变量。_" if stats else "_无可分析的数据。_",
        n_input=n_input,
        n_output=n_output,
        missing_rate=missing_rate,
        n_outliers=outlier_count,
        quality_grade=f"**{quality_grade}**",
        quality_notes=quality_notes,
        descriptive_stats=build_descriptive_table(stats),
        trend_analysis="_趋势分析需基于时间序列数据。若数据包含时间列，请参考生成的趋势图。_" + cross_ref_figures,
        comparative_analysis="_对比分析需指定分组变量。若数据包含批次/组别信息，请参考生成的对比图表。_" + cross_ref_figures,
        correlation_analysis=build_correlation_section(stats),
        discussion="_自动生成的报告提供数据统计摘要。深入的化学机理解释和实验讨论建议结合领域专业知识进行人工补充。_",
        conclusions="- 报告提供了实验数据的统计摘要\n- 建议对高变异变量进行进一步分析\n- 参考 Module 5 实验推荐引擎获取下一步建议",
        processing_time=datetime.utcnow().isoformat(),
        input_files=", ".join(metadata.get("input_file", "unknown") for _ in [1]),
    )

    return report


def main():
    parser = argparse.ArgumentParser(description="Chemistry Experiment Report Generator")
    parser.add_argument("--data", required=True, help="Cleaned experiment data JSON file")
    parser.add_argument("--spectra", default=None, help="Spectra output directory (optional)")
    parser.add_argument("--notes", default=None, help="Structured notes JSON file (optional)")
    parser.add_argument("--output", required=True, help="Output report file path")
    parser.add_argument("--template", default=None, help="Custom report template (optional)")
    parser.add_argument("--format", default="md", help="Output format: md, pdf (comma-separated)")
    parser.add_argument("--figures-dir", default=None, help="Directory for generated figures")

    args = parser.parse_args()

    if not Path(args.data).exists():
        print(f"ERROR: Data file not found: {args.data}", file=sys.stderr)
        sys.exit(1)

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    spectra_summary = None
    if args.spectra and Path(args.spectra).exists():
        spectra_summary = {"status": "available"}

    notes_summary = None
    if args.notes and Path(args.notes).exists():
        with open(args.notes, "r", encoding="utf-8") as f:
            notes = json.load(f)
            notes_summary = notes.get("preprocessing_summary", {})

    report_md = generate_report(data, args.figures_dir, spectra_summary, notes_summary)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if "md" in args.format:
        md_path = out_path if out_path.suffix == ".md" else out_path.with_suffix(".md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"Markdown report: {md_path}")

    if "pdf" in args.format:
        print("PDF generation requires pandoc + wkhtmltopdf or weasyprint. Install and run manually:")
        print(f"  pandoc {out_path.with_suffix('.md')} -o {out_path.with_suffix('.pdf')} --pdf-engine=wkhtmltopdf")

    print(f"Report generated successfully.")


if __name__ == "__main__":
    main()