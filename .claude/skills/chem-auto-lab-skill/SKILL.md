---
name: chem-auto-lab-skill
description: "Use when the user provides chemistry laboratory data (Excel, CSV, TXT, instrument exports) and asks about data cleaning, spectrum analysis (FTIR/Raman/UV-Vis/HPLC/NMR), experiment log structuring, report generation, or next-experiment recommendations. Also triggers on: 化学数据处理, 谱图解析, 实验记录结构化, 化学实验报告, 实验推荐, 数据清洗, spectroscopy parsing, lab notes structuring. Make sure to use this skill whenever the user mentions chemistry experiment data processing, lab automation, instrument data analysis, or wants to standardize/normalize laboratory records, even if they don't explicitly ask for a 'skill' or 'pipeline.' Do NOT trigger for: general-purpose data science, non-chemistry CSV processing, financial data, social science surveys, or bioinformatics without chemistry context."
version: 1.0.0
---

# Chem-Auto-Lab Skill

## Language Default

默认输出语言为中文。报告、分析结论使用中文。JSON 字段名、枚举值使用英文。化学命名遵循 IUPAC 规范。

## Core Principle

Every module is independently callable, producing schema-validated JSON output. The full pipeline composes these modules sequentially. Data integrity is paramount — every transformation is logged and reversible.

## Loading Guide — What to Read and When

This skill uses progressive loading. Read only what each step needs:

| When | Read | Why |
|------|------|-----|
| Skill triggered | This file (SKILL.md) | Intent routing, module selection |
| Module 1: Data Cleaning | `references/module-1-data-cleaning.md` | Cleaning protocol, edge cases, configuration |
| Module 2: Spectroscopy | `references/module-2-spectroscopy.md` | Spectrum type detection, peak analysis rules |
| Module 3: Log Structuring | `references/module-3-log-structuring.md` | Few-shot examples, abbreviation mappings |
| Module 4: Report Generation | `references/module-4-report-generation.md` | Report structure, chart selection rules |
| Module 5: Recommendations | `references/module-5-experiment-recommend.md` | Recommendation types, iterative reasoning |
| Full pipeline mode | `pipeline-execution.md` | Orchestration sequence, error recovery, logging |
| Schema validation | `schemas/*.json` matching output type | Validate module outputs |

**Do NOT load everything upfront.** Each module reference is self-contained — read it only when that module is invoked.

---

## Intent Routing

When a user makes a request, classify it and route to the correct module:

```
User Request
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Intent Classification                     │
├──────────┬──────────┬───────────┬───────────┬──────────────┤
│ 清洗/整理 │ 解析谱图  │ 结构化笔记 │ 生成报告   │ 推荐实验      │
│ 标准化   │          │           │           │              │
│          │          │           │           │              │
│ Module 1 │ Module 2 │ Module 3  │ Module 4  │ Module 5     │
│ + clean  │ + parse  │+structure│+generate  │ + recommend  │
│ _data.py │_spectrum │_notes.py │_report.py │ .py          │
│          │ .py      │           │           │              │
└──────────┴──────────┴───────────┴───────────┴──────────────┘
    │                                            
    │  "帮我分析这个文件夹的化学数据" → Full Pipeline
    ▼
┌─────────────────────────────────┐
│         Full Pipeline           │
│  run_pipeline.py --mode full    │
│  (Step 1→2→3→4→5 顺序执行)      │
└─────────────────────────────────┘
```

### Routing Keywords

| User says (any language) | Route to |
|--------------------------|----------|
| 清洗/清理/标准化/归一化/缺失值/异常值/clean/normalize/preprocess data | → Module 1 |
| FTIR/Raman/UV-Vis/HPLC/NMR/光谱/色谱/谱图/peak/峰检测/波数 | → Module 2 |
| 实验记录/笔记/结构化/log/note/lab notebook/实验参数提取 | → Module 3 |
| 报告/周报/summary/report/图表/趋势分析/统计摘要 | → Module 4 |
| 推荐/建议/下一步/optimize/recommend/实验设计/参数优化 | → Module 5 |
| 全部/整个流程/完整分析/pipeline/end-to-end/帮我分析 | → Full Pipeline |

---

## Module Execution Protocol

Each module follows the same execution pattern:

```
Step 0: Read the module reference file (references/module-N-*.md)
Step 1: Validate input — check file exists, format matches
Step 2: Run the script with appropriate arguments
Step 3: Validate output against schema (schemas/*.json)
Step 4: Report results to user
```

### Script Invocation Pattern

All scripts follow a consistent CLI interface:

```bash
# Direct file input
python scripts/<script>.py --input <path> --output <path> [options]

# Pipeline mode (stdin JSON)
cat <previous_output.json> | python scripts/<script>.py --stdin --output <path>

# Get help
python scripts/<script>.py --help
```

### Output Validation

After each module execution, validate the output against its schema:

```bash
python -c "
import json, jsonschema
with open('<schema_path>') as sf: schema = json.load(sf)
with open('<output_path>') as of: data = json.load(of)
jsonschema.validate(data, schema)
print('Validation PASSED')
"
```

If validation fails, report the specific schema violation to the user and stop the pipeline.

---

## Full Pipeline — Quick Start

When the user wants end-to-end processing:

```bash
python scripts/run_pipeline.py \
  --input-dir <path_to_raw_data_folder> \
  --output-dir <path_to_results_folder> \
  --mode full \
  --skill-path <path_to_this_skill>
```

The pipeline:
1. Scans input directory for all supported file types
2. Auto-classifies each file (data / spectrum / lab notes)
3. Runs Module 1 (data cleaning) on spreadsheets
4. Runs Module 2 (spectroscopy) on spectral files (if present)
5. Runs Module 3 (log structuring) on text notes (if present)
6. Merges all structured data
7. Runs Module 4 (report + visualization generation)
8. Runs Module 5 (experiment recommendations)
9. Outputs all results with a `pipeline_manifest.json` summary

See `pipeline-execution.md` for detailed orchestration rules, error recovery, and logging format.

---

## Supported Input Formats

| Category | Formats |
|----------|---------|
| Spreadsheets | `.xlsx`, `.xls`, `.csv`, `.tsv` |
| Text notes | `.txt`, `.md`, `.log` |
| Spectroscopy | `.csv` (xy), `.txt` (xy), `.jdx` (JCAMP-DX), `.spc` (limited) |
| JSON | Already-structured experiment data |

---

## Output Standards

- All module outputs are **NDJSON** (newline-delimited JSON) or single JSON objects
- All JSON keys are `snake_case` in English
- All dates are ISO 8601 (`YYYY-MM-DDTHH:MM:SS`)
- All numeric values include `unit` field where applicable
- All outputs include `metadata` block with provenance (script version, timestamp, input file)

---

## Error Handling

1. **Input not found** — Report to user, ask for correct path
2. **Format not recognized** — Try auto-detection; if fails, report supported formats
3. **Module script error** — Capture stderr, report with context, suggest fixes
4. **Schema validation failure** — Report exact field and constraint violated
5. **Pipeline partial failure** — Continue remaining modules, mark failed step in manifest

---

## Quick Reference — Script Arguments

| Script | Key Arguments |
|--------|--------------|
| `clean_data.py` | `--input`, `--output`, `--imputation`, `--outlier`, `--normalize`, `--target-units` |
| `parse_spectrum.py` | `--input`, `--output`, `--type` (ftir/raman/uvvis/nmr/hplc), `--baseline`, `--smooth` |
| `structure_notes.py` | `--input`, `--output`, `--context` (additional experiment context) |
| `generate_report.py` | `--data`, `--output`, `--template`, `--format` (md/pdf), `--figures-dir` |
| `visualize.py` | `--data`, `--output-dir`, `--type` (timeseries/correlation/distribution/comparison) |
| `recommend.py` | `--experiments`, `--output`, `--mode` (optimize/explore/validate), `--n-recommendations` |
| `run_pipeline.py` | `--input-dir`, `--output-dir`, `--mode`, `--skill-path` |