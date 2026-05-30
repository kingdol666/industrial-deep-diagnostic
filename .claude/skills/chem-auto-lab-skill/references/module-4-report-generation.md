# Module 4: Auto Report Generator

You generate professional chemistry experiment reports with statistical analysis and visualization.

## Core Principle

A chemistry report is not a data dump. It tells a story: what was done, what was observed, what it means, and what to do next. Prioritize clarity over completeness. The executive summary must be understandable by a non-specialist manager.

## Report Structure

```
1. 执行摘要 (Executive Summary)
2. 实验方法与材料 (Methods & Materials)
3. 数据质量评估 (Data Quality Assessment)
4. 结果与分析 (Results & Analysis)
   4.1 描述性统计 (Descriptive Statistics)
   4.2 趋势分析 (Trend Analysis)
   4.3 对比分析 (Comparative Analysis)
   4.4 相关性分析 (Correlation Analysis)
5. 讨论 (Discussion)
6. 结论与建议 (Conclusions & Recommendations)
附录 (Appendix)
```

### Section Writing Guidelines

**1. Executive Summary (中文, 3-5 bullet points)**
- What was the goal?
- What were the key findings (with numbers)?
- What was unexpected?
- What's the bottom-line recommendation?

**2. Methods & Materials**
- List materials with CAS numbers if available
- Instrument models and settings
- Key procedure steps (not every detail)
- Any deviations from standard protocol

**3. Data Quality Assessment**
- Total records processed
- Missing value rate per column
- Outlier summary
- Data quality score (A/B/C/D)
- If score C or D: flag for review, do not draw strong conclusions

**4.1 Descriptive Statistics**
- Per-variable: mean, median, std, min, max, Q1, Q3
- Highlight variables with high variance (CV > 30%) or unexpected ranges

**4.2 Trend Analysis**
- Time-series plots for temporal data
- Identify trends: increasing, decreasing, cyclic, stable
- Annotate significant change points

**4.3 Comparative Analysis**
- Group comparisons (e.g., control vs. treatment, batch A vs. B)
- Statistical tests (t-test, ANOVA) where applicable
- Effect size, not just p-value

**4.4 Correlation Analysis**
- Correlation matrix (heatmap)
- Top 3 strongest correlations (positive and negative)
- Causal interpretation caveat: "correlation ≠ causation"

**5. Discussion**
- Interpret results in context of the experiment goal
- Compare with expected/literature values
- Acknowledge limitations
- Propose mechanisms for unexpected findings

**6. Conclusions & Recommendations**
- 3-5 actionable conclusions
- Concrete next-step suggestions (link to Module 5)

## Visualization Selection Guide

| Data Pattern | Chart Type | When to Use |
|-------------|-----------|-------------|
| Single variable over time | Line plot | Temporal trends, stability monitoring |
| Multiple variables, same y-scale | Multi-panel line plot | Compare evolution patterns |
| Multiple variables, different scales | Normalized overlay | Show relative changes |
| Relationship between 2 variables | Scatter plot + regression | Correlation visualization |
| Many variables correlation | Heatmap | Global correlation structure |
| Distribution of single variable | Histogram + KDE | Normality check, modality |
| Group comparisons | Box plot / Violin plot | Batch effects, treatment effects |
| Composition data | Stacked bar / Pie chart | Formulation comparison |
| Before/after comparison | Paired bar chart | Treatment effect size |

**Anti-patterns to avoid**:
- 3D charts (distort perception)
- Pie charts with >5 categories (use bar chart)
- Dual y-axes (misleading unless carefully annotated)
- Charts without labeled axes and units

## Figures Generation

Use `scripts/visualize.py` for all figures:

```bash
python scripts/visualize.py \
  --data <merged_experiments.json> \
  --output-dir <figures_dir> \
  --type auto
```

`--type auto` uses the selection guide above to choose appropriate chart types.

The script outputs a `plot_manifest.json`:
```json
{
  "figures": [
    {"id": 1, "file": "01_timeseries.png", "type": "multi_panel_line", "variables": ["temperature_C", "pressure_MPa"], "description": "Process parameters over time"},
    {"id": 2, "file": "02_correlation_heatmap.png", "type": "heatmap", "variables": ["all_numeric"], "description": "Correlation matrix of all measured variables"}
  ]
}
```

## Report Generation

```bash
# Generate Markdown report
python scripts/generate_report.py \
  --data <cleaned_data.json> \
  --output report.md \
  --figures-dir <figures_dir> \
  --format md

# Generate both Markdown and PDF
python scripts/generate_report.py \
  --data <cleaned_data.json> \
  --spectra <spectra_dir/> \
  --notes <structured_notes.json> \
  --output report \
  --format md,pdf \
  --figures-dir <figures_dir>
```

The report generator:
1. Computes all statistics from the data
2. Embeds figure references
3. Generates discussion text using LLM reasoning (based on statistical findings)
4. Formats as clean Markdown with YAML frontmatter
5. Optionally converts to PDF (requires `weasyprint` or `pandoc` + `wkhtmltopdf`)

## Output Format

Report follows `templates/report_template.md` structure. Key formatting rules:

- Markdown headings: `#` for title, `##` for sections, `###` for subsections
- Tables: pipe-style Markdown tables, aligned columns
- Figures: `![caption](path/to/figure.png)` with sequential numbering
- Numbers: 3 significant figures for measured values, 2 for derived statistics
- Units: SI/metric, consistent throughout
- Chemical formulas: Proper subscripts using `<sub>` in HTML or Unicode (CO₂, H₂O)

## Edge Cases

1. **No time column** → Skip trend analysis section, note in methods.
2. **Single variable only** → Skip correlation analysis. Focus on distribution and statistics.
3. **Very small dataset (n < 10)** → Use non-parametric statistics. Flag `small_sample_warning`.
4. **All values constant** → Flag as potential instrument error or trivial experiment.
5. **Mixed languages in labels** → Preserve original labels, add English translations in parentheses.
6. **Confidential data** → Use generic labels if column names contain sensitive info.