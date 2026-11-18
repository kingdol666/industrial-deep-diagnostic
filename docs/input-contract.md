# Input Contract — what data each stage accepts, and the thresholds it enforces

> Every claim below was verified against the actual script code, cited as `path:line`.
> Authoritative sources: `.claude/skills/industrial-data-preprocessor/scripts/data_preprocessor.py`
> (stage E-1, the only format-adaptation stage), `.claude/skills/industrial-analysis-auto/scripts/inspect.mjs`
> + `file_inspect.py` (Step 1 read-only inspection), and
> `.claude/skills/industrial-hetero-preprocessor/scripts/quality_gate.mjs` (stage E-1H).

## 1. Data-format support — who adapts what

| Format | Extensions | Adapting stage | Evidence |
|---|---|---|---|
| CSV / TSV / delimited text | `.csv .tsv .txt .dat` | E-1 `_parse_delimited_text` with delimiter auto-detection (`,` `;` `\t` `\|`, header-repetition rows dropped) | `data_preprocessor.py:55-56` (`_TABLE_EXTS`), `:74-89` (delimiter), `:168` (parser), `:396-403` (repeated-header drop) |
| Excel (multi-sheet) | `.xlsx .xlsm .xls` | E-1 `_parse_excel`: **every** sheet becomes a scored candidate; 1-row stubs / junk sheets scored down but preserved in the report; sheet whose name matches the file stem wins (≥100 rows) | `data_preprocessor.py:243-270`, `:227-240` (sheet score), `:717` (stem match ≥100 rows) |
| JSON records | `.json` | E-1 `_parse_json`: top-level array, or first non-empty list under `data/records/rows/values/items/result`, or single record object | `data_preprocessor.py:296-326`, keys at `:308-311` |
| Markdown | `.md .markdown` | E-1 `_parse_markdown`: **pipe tables only**; a file with no pipe table becomes a preserved CONTEXT file | `data_preprocessor.py:329-360`, context fallback at `:642-645` |
| HTML | `.html .htm` | E-1 `_parse_html`: regex-based `<table>` extraction (≥2 rows), no lxml dependency | `data_preprocessor.py:363-386` |
| Parquet | `.parquet .pq` | E-1 via `pd.read_parquet` (directory mode: `:988-990`); Step-1 inspection also reads it | `data_preprocessor.py:56`, `:988-990`; `file_inspect.py:45-46` |
| Feather / Arrow | `.feather .ipc .arrow` | Step-1 inspection only (`file_inspect.py:47-48`); not in E-1 `_TABLE_EXTS` | `file_inspect.py:31-51` |
| Free text / documents | `.txt .rst .doc .docx .pdf` | **Never parsed as tables** — preserved as context files (`_CONTEXT_EXTS`); note `.txt` is first *attempted* as delimited text because it is also in `_TABLE_EXTS` | `data_preprocessor.py:48` vs `:55-56`, classify order at `:577-582` |
| Images (PNG/JPG/GIF/SVG, …) | `.png .jpg .jpeg .gif .svg` | **Skipped by E-1** (`_SKIP_EXTS`); image *sequences* enter only through E-1H's IMG shape (image files + a timestamp→filename index CSV) | `data_preprocessor.py:49-54`; `.claude/skills/industrial-hetero-preprocessor/SKILL.md` (IMG shape) |
| Explicitly ignored | `.py .mjs .js .db .zip .log .bak .ini .cfg .yml …`, dot-dirs, `node_modules/`, `__pycache__/`, and `07_hetero/` (E-1H outputs are never re-ingested) | E-1 `_SKIP_EXTS` + `_discover_sources` | `data_preprocessor.py:49-54`, `:556-577` |

Directory mode: `_discover_sources` (non-recursive by default, `--recursive` to descend), sorting
case-insensitively; excluded paths are honored (`data_preprocessor.py:556-575`).
Encoding fallback chain for text: `utf-8-sig → utf-8 → gb18030 → latin-1` (`:63-71`).
E-1 output is written as UTF-8-BOM CSV plus a JSON-records twin (`:912-915`).

### The four heterogeneous shapes (E-1H · `industrial-hetero-preprocessor`)

Non-scalar data is projected into deterministic `HX-<SHAPE>-<SRC>-<FEATURE>` scalar columns, anchored
to the canonical time axis. The five shape codes (the `IDX` variant is the timestamp→filename index,
emitted with `role=metadata`):

| Shape | Code | Input examples |
|---|---|---|
| Profile / vector over time | `PROF` | 膜厚剖面, 时间×位置 TD profiles (long or wide) |
| Regular-grid 2D field | `MAP` | x,y,value snapshots — 温度场, 浓度场, 网格数据 |
| Image stream over time | `IMG` | WAXS/SAXS diffraction, CCD inspection, 热成像 (image files + index CSV) |
| Time-anchored free text | `TXT` | 操作备注, 交接班记录, 批注 |
| Directory index | `IDX` | the timestamp→filename index CSV itself (metadata role) |

Evidence: `.claude/skills/industrial-hetero-preprocessor/scripts/heterocore/naming.py:4,19-26`
(ASCII naming regex `^HX-(PROF|MAP|IMG|TXT|IDX)-…$`), `heterocore/contracts.py:25,43,59`
(IDX → metadata, PROF/MAP/IMG → process_parameters). Column counts are validated per shape by
`scripts/quality_gate.mjs` (H1-H8); it is a shape contract, not a row-count gate.

## 2. Row thresholds (the constants, verified)

| Constant | Value | What it actually gates | Evidence |
|---|---|---|---|
| Minimum table candidate | ≥2 rows and ≥1 column | Anything smaller is dropped before scoring | `data_preprocessor.py:658` |
| Markdown / HTML table snippet | <5 data rows → demo(snippet) | Demoted to a **context** file, not data. So **md pipe-tables with ≥5 rows do become data candidates** (and are also merge-eligible only at ≥100 rows, below) | `data_preprocessor.py:660-669` |
| Merge eligibility | ≥100 rows **and** a usable (parseable) time column | Only tables ≥100 rows participate in the multi-table time-axis merge; tables below get an explicit `below_min_rows` merge-exclusion reason | `data_preprocessor.py:732`, `:857-858`; documented at `industrial-data-preprocessor/SKILL.md:55,57` |
| Premerged-file / Excel stem-match preference | ≥100 rows | A file named merged/align/combined/汇总/合并/_full… or a stem-matching sheet wins primary selection only at ≥100 rows | `data_preprocessor.py:709`, `:717`, `:452-458` |
| Merge overlap | ≥0.3 of the smaller time range | Below → `low_overlap` exclusion; merge also aborts if the joined table exceeds 1.5× the largest source (anti-bloat) | `data_preprocessor.py:789-799`, `:831-844` |

**Correction to a common misreading** (verified in code, previously stated imprecisely elsewhere):
E-1 does **not** "drop <100-row tables". The 100-row constant is a **merge-eligibility** threshold
and a primary-selection *preference*, not a discovery cut: a <100-row table can still be selected as
the primary (highest table score, `:723`) or appear as an audited exclusion (`:857-858`). The only
hard discovery cuts are `<2 rows / <1 col` (`:658`) and the `<5`-row markdown/HTML snippet rule (`:662`).

| Stage-specific minimum | Value | Evidence |
|---|---|---|
| Line-stability report (`--stability-single-primary` folder profile) | one **≥50-row** time-series primary; below the single-primary policy, a table <50 rows gets code `below_min_rows` and is not even a candidate for the policy | `industrial-data-preprocessor/SKILL.md:30`; `data_preprocessor.py:1062` |
| Line-stability report (analyzer) | **<50 rows** or no numeric parameter column → `status=not_assessable` (exit 2, honest refusal); >100k rows → systematic sample + `data.sampled` flag | `industrial-line-stability-report/SKILL.md:16` |
| Sentinel watch | window **1k-100k rows**; fast-screen **1-500 rows** ≤5 s | `industrial-sentinel/SKILL.md:3` |
| Sentinel cold start | self-baseline needs **≥100 steady rows** (Mahalanobis skipped, 48 h TTL reminder) | `industrial-sentinel/SKILL.md:3` |
| Sentinel settle/视界 ("settle horizon") | **not documented** anywhere in the skill (grep of SKILL.md/references found no such constant) — the only documented minimums are the three above. Flagged as a doc gap, not asserted here. | — |
| DOE analyzer | no global row minimum documented; tiny-count behavior is covered by a **6-row** regression case ("0 plots legal, gate PASS"), and model-term reason codes include `insufficient_df` | `industrial-doe-analyzer/tests/run_tests.py` docstring (F10, F12) |
| Optimizer-loop convergence | **m≥3** confirm replicates in the target window (dual-gate with 95% CI + D≥0.8·D_max) | `industrial-optimizer-loop/SKILL.md` (frontmatter/dual gate) |
| Step-1 inspection (`inspect.mjs`) | <2 parsed data rows → hard error (exit 1); >100k rows → statistics computed on a ~50k systematic/reservoir sample (flagged in output) | `industrial-analysis-auto/scripts/inspect.mjs:209`, `:186`, `:197-198` |

## 3. Time-column requirements

Detection runs in two passes (`data_preprocessor.py:432-448`):

1. **Name-based pass** — a column whose lowercase name contains one of
   `_TIME_HINTS = ("time", "timestamp", "datetime", "date", "zeit", "ts_", "时间", "日期", "时刻")`
   (`:57`) AND whose first 50 non-null values parse as datetime at **>0.5** (`:437-439`).
2. **Value-based fallback** — any column that does **not** look numeric (columns numeric at >0.7 are
   skipped so nanosecond-epoch integers cannot masquerade as dates, `:440-446`) whose first 100
   non-null values parse at **>0.8** (`:447`).

Accepted datetime formats: whatever `pandas.to_datetime` parses, **plus** Chinese-calendar
normalization `2026年5月1日 08:00:00` / `2026/5/1 8:00` / `2026.5.1 08:00` → ISO
(`_normalize_cn_datetime`, `:407-419`). The emitted canonical time column is rewritten to
`%Y-%m-%d %H:%M:%S` for all clearly-parseable rows (`:891-900`).

Semantics downstream:

- A table with **no** detectable time column is a supported scenario (cross-sectional / batch data) —
  no error; it is simply merge-ineligible (`:865`, gate note D4 in `industrial-data-preprocessor/scripts/quality_gate.mjs`).
- Multi-table merges are **outer joins on the shared time axis**, values normalized to ISO before the
  join; duplicate non-time columns are dropped from the right side (`:818-829`).
- Line-stability folder mode requires the primary's time column to be **≥80% parseable** and never
  merges across different sampling cadences (`industrial-line-stability-report/SKILL.md:54`).
- E-1H derives `_src_ts ≤ ts` provenance per column — no look-ahead is permitted across the canonical
  axis (`industrial-hetero-preprocessor/scripts/quality_gate.mjs`, check H3).

## 4. Where these numbers are enforced (gate exit codes)

| Gate | Path | Exit codes |
|---|---|---|
| E-1 quality gate | `.claude/skills/industrial-data-preprocessor/scripts/quality_gate.mjs` | 0 ok / 1 hard error / 2 undetermined (stage absent / `no_tabular_data` passthrough) / 3 gate-fail |
| E-1H quality gate | `.claude/skills/industrial-hetero-preprocessor/scripts/quality_gate.mjs` | 0 ok (incl. honest marker statuses `off` / `no_hetero_sources` when every check passes) / 1 hard error (`:104`, manifest unparseable) / 2 undetermined (`:99`, marker manifest absent — the stage did not run) / 3 gate-fail |
| Step-1 inspection | `.claude/skills/industrial-analysis-auto/scripts/inspect.mjs` | exit 1 on "no data rows" (`:209`) |
