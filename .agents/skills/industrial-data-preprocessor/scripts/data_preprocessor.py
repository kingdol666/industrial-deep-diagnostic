#!/usr/bin/env python3
"""data_preprocessor.py — E-1: adaptive data preprocessing stage.

Turns ANY user-supplied data source — a single file or a whole directory, in
any mix of CSV/TSV/delimited text, Excel (.xlsx/.xlsm/.xls), JSON records,
Markdown tables, HTML tables, or free-text notes — into ONE canonical table
that the industrial diagnostic pipeline can consume unchanged.

Deterministic. Depends only on the Python standard library + pandas +
openpyxl (already required by the pipeline). Never modifies the input.

Outputs (written under ``--output``, typically ``RUN_DIR/00_input/``):

* ``preprocessed_data.csv``      — canonical tabular data (the pipeline input)
* ``preprocessed_data.json``     — same data as JSON records (fallback reader)
* ``preprocessing_report.json``  — full audit: per-source disposition, format
                                   detection, merge keys, quality flags
* ``context/``                   — non-tabular files (process descriptions,
                                   ground truth, notes) preserved verbatim for
                                   the ontology/context builder

CLI::

    python data_preprocessor.py --data-path <file|dir> --output <dir>
                                [--name <run_name>]
                                [--stability-single-primary | --integrate-merge]
                                [--allow-cadence-mismatch]

Three modes: the default adaptive single-table pass (time-axis merge of the
raw exports behind overlap/anti-bloat gates), the stability folder contract
(one primary time-series table, no merge), and ``--integrate-merge``
(stability-rule primary selection plus a gated outer merge of the other
sources onto it — cadence gate, overlap gate, anti-bloat gate, duplicate-
column semantics audit). ``--integrate-merge`` exits 2 when no usable primary
exists or the merged primary has fewer than 50 rows.

Default mode exits 0 with a report even when nothing tabular is found (the
report then says ``no_tabular_data`` and the caller decides); exit 1 only on
hard errors.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Table extraction: one source file → list of candidate tables
# ---------------------------------------------------------------------------

_CONTEXT_EXTS = {".md", ".markdown", ".txt", ".rst", ".doc", ".docx", ".pdf"}
_SKIP_EXTS = {
    ".py", ".mjs", ".js", ".ts", ".ipynb", ".sh", ".bat", ".db", ".db-shm",
    ".db-wal", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf", ".docx",
    ".doc", ".zip", ".tar", ".gz", ".7z", ".gitkeep", ".ini", ".cfg", ".yml",
    ".yaml", ".log", ".bak",
}
_TABLE_EXTS = {".csv", ".tsv", ".txt", ".dat", ".xlsx", ".xlsm", ".xls",
               ".json", ".md", ".markdown", ".html", ".htm", ".parquet", ".pq"}
_TIME_HINTS = ("time", "timestamp", "datetime", "date", "zeit", "ts_", "时间",
               "日期", "时刻")
_MAIN_SHEET_HINTS = ("data", "记录", "统计", "历史", "history", "export", "查询")
_JUNK_SHEET_HINTS = ("query", "sheet", "说明", "注释", "note", "readme")


def _read_text_adaptive(path: Path) -> Tuple[str, str]:
    """Read text with encoding fallback: utf-8(-sig) → gb18030 → latin-1."""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8(replace)"


def _detect_delimiter(lines: List[str]) -> str:
    """Delimiter detection over the first non-empty lines: the delimiter that
    appears in the most lines wins (junk title lines must not veto the real
    delimiter present in header/data rows)."""
    sample = [ln.strip() for ln in lines[:12] if ln.strip()]
    if not sample:
        return ","
    cands = {"\t": 0, ";": 0, ",": 0, "|": 0}
    for ln in sample:
        for d in cands:
            if d in ln:
                cands[d] += 1
    best = max(cands, key=lambda d: (cands[d], d != ","))
    # require the winner to actually appear somewhere
    if cands[best] == 0:
        return ","
    return best


def _split_line(line: str, delim: str) -> List[str]:
    if delim == "\t":
        return [c.strip() for c in line.rstrip("\n").split("\t")]
    if delim == ";":
        return [c.strip() for c in line.rstrip("\n").split(";")]
    if delim == "|":
        return [c.strip() for c in line.rstrip("\n").split("|")]
    # comma with optional quotes
    out: List[str] = []
    cur: List[str] = []
    in_q = False
    for ch in line.rstrip("\n"):
        if ch == '"':
            in_q = not in_q
        elif ch == "," and not in_q:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur).strip())
    return out


def _is_header_row(cells: List[str]) -> bool:
    """Header heuristics: mostly non-numeric, short, unique."""
    if not cells:
        return False
    nonempty = [c for c in cells if c != ""]
    if not nonempty:
        return False
    numeric = 0
    for c in nonempty:
        try:
            float(c.replace(",", "").replace("%", "").replace(" ", ""))
            numeric += 1
        except ValueError:
            pass
    return numeric / len(nonempty) < 0.5


def _numeric_density(cells: List[str]) -> float:
    if not cells:
        return 0.0
    ok = 0
    for c in cells:
        if c == "" or c is None:
            continue
        try:
            float(str(c).replace(",", "").replace("%", "").strip())
            ok += 1
        except ValueError:
            pass
    return ok / max(1, len([c for c in cells if c not in ("", None)]))


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Trim names, de-dup, drop fully-empty columns."""
    cols: List[str] = []
    seen: Dict[str, int] = {}
    for c in df.columns:
        name = str(c).strip()
        if not name:
            name = "column"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        cols.append(name)
    df.columns = cols
    blank = df.apply(lambda s: s.astype(str).str.strip() == "")
    df = df.loc[:, ~(df.isna().all() | blank.all())]
    return df.reset_index(drop=True)


def _parse_delimited_text(path: Path) -> List[dict]:
    """Parse CSV/TSV/delimited text, skipping junk header lines; returns
    candidate tables (multi-block files yield several candidates)."""
    text, enc = _read_text_adaptive(path)
    lines = text.splitlines()
    if not lines:
        return []
    delim = _detect_delimiter(lines)
    # find the first plausible header row (skip title/junk lines)
    start = 0
    for i, ln in enumerate(lines[:20]):
        cells = _split_line(ln, delim)
        if len(cells) >= 2 and _is_header_row(cells):
            start = i
            break
    blocks: List[dict] = []
    cur_rows: List[List[str]] = []
    header: Optional[List[str]] = None
    n_cols = 0

    def flush() -> None:
        nonlocal cur_rows, header, n_cols
        if header is not None and len(cur_rows) >= 2:
            blocks.append({"source": path.name, "sheet": None,
                           "format": "delimited", "encoding": enc,
                           "delimiter": delim,
                           "header": header, "rows": cur_rows})
        cur_rows = []
        header = None

    for i, ln in enumerate(lines[start:], start=start):
        if not ln.strip():
            flush()
            continue
        cells = _split_line(ln, delim)
        if header is None:
            if len(cells) >= 2 and _is_header_row(cells):
                header = cells
                n_cols = len(cells)
            continue
        # start of a new block: a new header-like line with different width
        if (len(cells) >= 2 and _is_header_row(cells)
                and len(cells) != n_cols and len(cur_rows) >= 2):
            flush()
            header = cells
            n_cols = len(cells)
            continue
        # pad/trim to header width
        while len(cells) < n_cols:
            cells.append("")
        cur_rows.append(cells[:n_cols])
    flush()
    return blocks


def _sheet_score(sheet_name: str, n_rows: int, n_cols: int,
                 numeric_density: float) -> float:
    """Score a worksheet: big real-data sheets win; junk sheets lose."""
    score = 0.0
    if n_rows >= 100:
        score += 4.0
    elif n_rows >= 10:
        score += 2.0
    score += min(n_cols / 10.0, 2.0)
    score += numeric_density * 2.0
    low = sheet_name.lower()
    if any(k in low for k in _JUNK_SHEET_HINTS):
        score -= 5.0
    if any(k in low for k in _MAIN_SHEET_HINTS):
        score += 1.5
    if n_rows <= 2 or n_cols <= 1:
        score -= 10.0
    return score


def _parse_excel(path: Path) -> List[dict]:
    """Parse .xlsx/.xlsm/.xls: every sheet becomes a candidate; junk sheets
    (1x1, 1-row query stubs) are scored down but preserved in the report."""
    try:
        import openpyxl
    except ImportError:
        return [{"source": path.name, "error": "openpyxl not installed",
                 "format": "excel"}]
    blocks: List[dict] = []
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:  # pragma: no cover
        return [{"source": path.name, "error": f"excel open failed: {exc}",
                 "format": "excel"}]
    try:
        for ws in wb.worksheets:
            n_rows = ws.max_row or 0
            n_cols = ws.max_column or 0
            if n_rows <= 1:
                continue
            # stream rows (read_only mode)
            rows: List[List[str]] = []
            for r in ws.iter_rows(values_only=True):
                cells = ["" if v is None else str(v).strip() for v in r]
                rows.append(cells)
            if len(rows) < 2:
                continue
            # find header: first row that is not junk
            header_idx = 0
            for i, r in enumerate(rows[:5]):
                if _is_header_row(r) and len([c for c in r if c]) >= 1:
                    header_idx = i
                    break
            header = rows[header_idx]
            data_rows = rows[header_idx + 1:]
            n_cols = len(header)
            data_rows = [r[:n_cols] + [""] * (n_cols - len(r)) for r in data_rows]
            # numeric density of first 200 data rows
            sample = [c for r in data_rows[:200] for c in r]
            density = _numeric_density(sample)
            blocks.append({
                "source": path.name, "sheet": ws.title,
                "format": "excel", "encoding": "xlsx",
                "header": header, "rows": data_rows,
                "score": _sheet_score(ws.title, len(data_rows), n_cols, density),
                "n_rows": len(data_rows), "n_cols": n_cols,
                "numeric_density": round(density, 3),
            })
    finally:
        wb.close()
    return blocks


def _parse_json(path: Path) -> List[dict]:
    """Parse JSON: array of records, {data: [...]}, or single object."""
    text, enc = _read_text_adaptive(path)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        return [{"source": path.name, "error": f"json parse failed: {exc}",
                 "format": "json"}]
    arr = None
    if isinstance(obj, list):
        arr = obj
    elif isinstance(obj, dict):
        for key in ("data", "records", "rows", "values", "items", "result"):
            if isinstance(obj.get(key), list) and obj[key]:
                arr = obj[key]
                break
        if arr is None:
            # single record object
            arr = [obj]
    if not arr:
        return [{"source": path.name, "error": "empty json", "format": "json"}]
    if not all(isinstance(r, dict) for r in arr):
        return [{"source": path.name,
                 "error": "json is not a record array", "format": "json"}]
    df = pd.DataFrame(arr)
    df = _normalize_columns(df)
    blocks = [{
        "source": path.name, "sheet": None, "format": "json", "encoding": enc,
        "header": list(df.columns), "rows": df.astype(str).values.tolist(),
    }]
    return blocks


_MD_TABLE_RE = re.compile(
    r"^\s*\|(.+)\|\s*$", re.MULTILINE)


def _parse_markdown(path: Path) -> List[dict]:
    """Extract pipe tables from Markdown; if none, the file is CONTEXT."""
    text, _ = _read_text_adaptive(path)
    lines = text.splitlines()
    tables: List[dict] = []
    cur: List[List[str]] = []
    in_table = False
    for ln in lines:
        if _MD_TABLE_RE.match(ln):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if not in_table:
                cur = []
                in_table = True
            # skip separator rows like |---|---|
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c.strip()):
                continue
            cur.append(cells)
        else:
            if in_table and len(cur) >= 2:
                tables.append({"source": path.name, "sheet": None,
                               "format": "markdown", "encoding": "utf-8",
                               "header": cur[0], "rows": cur[1:]})
            in_table = False
    if in_table and len(cur) >= 2:
        tables.append({"source": path.name, "sheet": None,
                       "format": "markdown", "encoding": "utf-8",
                       "header": cur[0], "rows": cur[1:]})
    return tables


_HTML_TABLE_RE = re.compile(r"<table[^>]*>(.*?)</table>", re.IGNORECASE | re.DOTALL)
_HTML_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
_HTML_CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)


def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).replace("&nbsp;", " ").strip()


def _parse_html(path: Path) -> List[dict]:
    """Lightweight regex-based HTML table extractor (no lxml dependency)."""
    text, _ = _read_text_adaptive(path)
    tables: List[dict] = []
    for m in _HTML_TABLE_RE.finditer(text):
        rows = []
        for rm in _HTML_ROW_RE.finditer(m.group(1)):
            cells = [_strip_tags(cm.group(1)) for cm in _HTML_CELL_RE.finditer(rm.group(1))]
            if cells:
                rows.append(cells)
        if len(rows) >= 2:
            tables.append({"source": path.name, "sheet": None,
                           "format": "html", "encoding": "utf-8",
                           "header": rows[0], "rows": rows[1:]})
    return tables


# ---------------------------------------------------------------------------
# Candidate → DataFrame
# ---------------------------------------------------------------------------

def _block_to_df(block: dict) -> pd.DataFrame:
    df = pd.DataFrame(block["rows"], columns=block["header"])
    df = _normalize_columns(df)
    # YAMATAKE-style exports repeat the header row inside the data stream —
    # drop any row that is byte-identical to the (normalized) header.
    if df.shape[0] > 0 and df.shape[1] > 0:
        hdr = np.array([str(h) for h in df.columns])
        if len(hdr) == df.shape[1]:
            mask = (df.astype(str).to_numpy() == hdr).all(axis=1)
            if mask.any():
                df = df.loc[~mask].reset_index(drop=True)
    return df


def _normalize_cn_datetime(value: str) -> str:
    """Normalize Chinese calendar formats pandas cannot parse natively:
    '2026年5月1日 08:00:00' -> '2026-05-01 08:00:00'. Also handles
    '2026/5/1 8:00' and '2026.5.1 08:00' variants."""
    s = str(value).strip()
    m = re.match(
        r"(\d{4})\s*[年./-]\s*(\d{1,2})\s*[月./-]\s*(\d{1,2})\s*[日]?"
        r"(?:\s*(\d{1,2}):(\d{2})(?::(\d{2}))?)?", s)
    if m:
        y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
        hh, mm, ss = m.group(4) or "0", m.group(5) or "0", m.group(6) or "00"
        return f"{y}-{mo:02d}-{d:02d} {hh}:{mm}:{ss}"
    return s


def _parses_as_time(values) -> float:
    """Fraction of values parseable as datetime after CN-format normalization."""
    normed = [_normalize_cn_datetime(v) for v in values]
    try:
        parsed = pd.to_datetime(pd.Series(normed), errors="coerce")
        return float(parsed.notna().mean())
    except Exception:
        return 0.0


def _detect_time_col(df: pd.DataFrame) -> Optional[str]:
    for c in df.columns:
        low = str(c).lower()
        if any(k in low for k in _TIME_HINTS):
            # verify it parses as datetime (at least partially)
            sample = df[c].dropna().head(50).astype(str)
            if _parses_as_time(sample) > 0.5:
                return str(c)
    for c in df.columns:
        # numeric columns would parse as nanosecond-epoch datetimes — skip them
        try:
            if pd.to_numeric(df[c], errors="coerce").notna().mean() > 0.7:
                continue
        except Exception:
            continue
        if _parses_as_time(df[c].dropna().head(100).astype(str)) > 0.8:
            return str(c)
    return None


def _looks_premerged(name: str) -> bool:
    """A file that already IS the merged/alignment product of the raw exports
    (e.g. merged_process_data_full.csv) must be used as-is, never re-merged."""
    low = Path(name).stem.lower()
    return any(k in low for k in ("merged", "merge", "align", "aligned",
                                  "combined", "汇总", "合并", "对齐", "_full",
                                  "joined"))


def _score_table(df: pd.DataFrame, time_col: Optional[str]) -> float:
    n_rows, n_cols = df.shape
    if n_cols == 0:
        return -1.0
    numeric = 0
    for c in df.columns:
        try:
            if pd.to_numeric(df[c], errors="coerce").notna().mean() > 0.7:
                numeric += 1
        except Exception:
            pass
    score = min(n_rows / 1000.0, 3.0) + min(n_cols / 5.0, 3.0) + numeric * 0.5
    if time_col:
        score += 1.0
    return score


def _quality_flags(df: pd.DataFrame, block: dict) -> dict:
    """Per-source quality disclosure (read-only audit — nothing is cleaned or
    deduplicated here; downstream cleaning owns that). Reported per parsed
    table: exact duplicate rows, null/empty cell count, and the encoding +
    delimiter actually used to parse this table."""
    dup_involved = df.duplicated(keep=False)   # every row that has a twin
    dup_extra = df.duplicated(keep="first")    # redundant occurrences only
    n_involved = int(dup_involved.sum())
    empty_mask = df.astype(str).apply(lambda s: s.str.strip() == "")
    null_cells = int((df.isna() | empty_mask).sum().sum())
    return {
        "exact_duplicate_rows": {
            "count": int(dup_extra.sum()),
            "row_indices_0based": [int(i) for i in df.index[dup_involved]][:10],
            "row_indices_truncated": n_involved > 10,
            "note": ("count = redundant occurrences beyond the first (dedup is NOT "
                     "applied); row_indices_0based lists the rows involved in exact "
                     "duplication, 0-based within the parsed table (header excluded), "
                     "capped at 10"),
        },
        "null_cell_count": null_cells,
        "encoding": block.get("encoding"),
        "delimiter": block.get("delimiter"),
    }


def _file_role(path: Path) -> Tuple[str, str]:
    """Conservative name-based role hint for audit; never merges event/context roles."""
    low = path.stem.lower()
    compact = low.replace("-", "_").replace(" ", "_")
    if any(k in compact for k in ("maintenance", "repair", "维修", "检修", "event", "事件", "alarm", "告警")):
        return "event", "filename indicates sparse events/maintenance; not a continuous sample series"
    if any(compact.startswith(k) or f"_{k}" in compact for k in ("qc", "quality", "inspection", "质检", "检测", "lab")):
        return "auxiliary", "filename indicates lower-frequency quality/inspection measurements"
    if "manifest" in compact:
        return "metadata", "filename identifies a data-generation manifest; retained as provenance, not a scoring table"
    if "ontology" in compact or "本体" in compact:
        return "metadata", "filename identifies an ontology model; retained as context for semantic wiring, not a scoring table"
    if any(k in compact for k in ("readme", "ground_truth", "truth", "题目", "说明", "manual")):
        return "context", "filename indicates documentation/metadata rather than process time series"
    return "candidate", "tabular candidate; role determined by table score and time-axis checks"


def _same_column_meaning(left: pd.Series, right: pd.Series) -> bool:
    """Require overlapping values in shared numeric columns to agree before joining."""
    lnum = pd.to_numeric(left, errors="coerce")
    rnum = pd.to_numeric(right, errors="coerce")
    both = lnum.notna() & rnum.notna()
    if both.sum() == 0:
        both_s = left.notna() & right.notna()
        return not both_s.any() or bool((left[both_s].astype(str) == right[both_s].astype(str)).all())
    lv, rv = lnum[both].to_numpy(), rnum[both].to_numpy()
    scale = np.maximum(1.0, np.maximum(np.abs(lv), np.abs(rv)))
    return bool((np.abs(lv - rv) <= 1e-8 * scale).all())


def _numeric_columns(df: pd.DataFrame) -> set:
    return {str(col) for col in df.columns
            if pd.to_numeric(df[col], errors="coerce").notna().mean() > 0.7}


def _median_interval_seconds(cand: dict) -> Optional[float]:
    """Median spacing (seconds) of a candidate's parsed time axis; None when
    fewer than two distinct usable timestamps survive parsing."""
    tc = cand.get("time_column")
    if not tc:
        return None
    try:
        normed = [_normalize_cn_datetime(v) for v in cand["df"][tc].dropna().tolist()]
        parsed = (pd.to_datetime(pd.Series(normed), errors="coerce", format="mixed")
                  .dropna().sort_values())
        if len(parsed) < 2:
            return None
        secs = parsed.diff().dropna().dt.total_seconds()
        secs = secs[secs > 0]
        return float(secs.median()) if not secs.empty else None
    except Exception:
        return None


def _dup_columns_agree(base: pd.DataFrame, base_time: str, right: pd.DataFrame,
                       col: str) -> bool:
    """_same_column_meaning over the time-aligned overlap of a duplicated
    column (positional comparison alone would be meaningless across tables
    of different length/order)."""
    aligned = (base[[base_time, col]].rename(columns={col: "__left"})
               .merge(right[[base_time, col]].rename(columns={col: "__right"}),
                      on=base_time, how="inner"))
    if aligned.empty:
        return True  # nothing comparable on the shared time axis
    return _same_column_meaning(aligned["__left"], aligned["__right"])


def _blank_to_nan(s: pd.Series) -> pd.Series:
    """Treat blank strings as missing so combine_first can fill them."""
    if s.dtype == object or isinstance(s.dtype, pd.StringDtype):
        return s.mask(s.astype(str).str.strip() == "")
    return s


def _merge_onto_time_axis(
    primary: Tuple[str, dict],
    candidates: List[Tuple[str, dict]],
    *,
    premerged_selected: bool = False,
    primary_always_joins: bool = False,
    cadence_gate: bool = False,
    allow_cadence_mismatch: bool = False,
    column_audit: bool = False,
) -> Tuple[Tuple[str, dict], Optional[str], Optional[dict], List[dict]]:
    """Shared time-axis merge engine behind the default mode and
    --integrate-merge: attempt an outer merge of several raw exports sharing a
    time axis, bounded by an anti-bloat gate so a failed join can never produce
    a garbage mega-table. Every table that does not make the unified view gets
    an explicit per-file exclusion reason (below_min_rows | no_timestamp |
    low_overlap | cadence_mismatch, plus premerged_file_used /
    merge_not_attempted when the merge itself was skipped).

    ``primary_always_joins`` keeps the primary table in the merge pool even
    below the 100-row threshold (an integrate-merge primary may have as few as
    50 rows). ``cadence_gate`` computes each source's median time interval,
    discloses source_cadence_seconds/cadence_ratio in merge_info, and excludes
    candidates whose ratio against the primary exceeds 10 unless
    ``allow_cadence_mismatch``. ``column_audit`` tracks column provenance
    (column_source) and vets duplicated columns with _same_column_meaning on
    the aligned time axis: agreeing copies fill the merged view's gaps,
    disagreeing copies are dropped with a duplicate_column_semantics_mismatch
    exclusion.

    Returns ``(primary, selected_kind_override, merge_info, merge_exclusions)``;
    ``selected_kind_override`` is "score_fallback" when the anti-bloat gate
    abandoned the merge and the largest-score single table was restored."""
    large = [c for c in candidates
             if c[1]["n_rows"] >= 100 or (primary_always_joins and c[1] is primary[1])]
    merge_exclusions: List[dict] = []
    merge_info: Optional[dict] = None
    skip_reasons: Dict[int, Tuple[str, str]] = {}  # id(cand dict) -> (code, detail)
    merged_dfs: List[Tuple[str, pd.DataFrame, str, dict]] = []
    merged_cand_ids: set = set()  # id(cand dict) of tables merged into the view
    fallback: Optional[str] = None
    merge_attempted = (not premerged_selected and len(large) >= 2
                       and primary[1]["time_column"])

    if premerged_selected:
        for fname, cand in candidates:
            if cand is primary[1]:
                continue
            skip_reasons[id(cand)] = (
                "premerged_file_used",
                "directory contains an already-merged product file; "
                "per-file time-axis merge skipped")
    elif not merge_attempted:
        note = ("primary table has no usable time column; merge skipped"
                if not primary[1]["time_column"]
                else "fewer than 2 merge-eligible tables (rows>=100 with usable time axis)")
        for fname, cand in candidates:
            if cand is primary[1]:
                continue
            if cand["n_rows"] >= 100 and cand["time_column"]:
                skip_reasons[id(cand)] = ("merge_not_attempted", note)

    cadence_allowed: List[str] = []
    cadences: Dict[str, Optional[float]] = {}
    if merge_attempted and cadence_gate:
        cadences[primary[0]] = _median_interval_seconds(primary[1])

    if merge_attempted:
        pname, pcand = primary
        ptime = pcand["time_column"]

        def _time_axis(cand: dict) -> Optional[np.ndarray]:
            tc = cand["time_column"]
            if not tc:
                return None
            try:
                parsed = pd.to_datetime(cand["df"][tc], errors="coerce")
                return parsed.astype("int64").to_numpy()
            except Exception:
                return None

        base_axis = _time_axis(pcand)
        for fname, cand in large:
            ctime = cand["time_column"]
            if not ctime:
                skip_reasons[id(cand)] = ("no_timestamp", "no time column detected")
                continue
            axis = _time_axis(cand)
            if axis is None or len(axis) == 0:
                skip_reasons[id(cand)] = (
                    "no_timestamp",
                    f"time column '{ctime}' did not parse to a usable time axis")
                continue
            if base_axis is None:
                skip_reasons[id(cand)] = (
                    "merge_not_attempted",
                    f"primary table's time column '{ptime}' did not parse; merge skipped")
                continue
            if cadence_gate:
                cad = _median_interval_seconds(cand)
                cadences[fname] = cad
                pcad = cadences.get(pname)
                if cad is not None and pcad:
                    ratio = max(cad, pcad) / min(cad, pcad)
                    if ratio > 10:
                        if allow_cadence_mismatch:
                            cadence_allowed.append(fname)
                        else:
                            skip_reasons[id(cand)] = (
                                "cadence_mismatch",
                                f"median cadence {cad:g}s vs primary {pcad:g}s "
                                f"(ratio {ratio:.1f} > 10)")
                            continue
            # overlap = |intersection of ranges| / |smaller range|
            lo = max(float(np.nanmin(axis)), float(np.nanmin(base_axis)))
            hi = min(float(np.nanmax(axis)), float(np.nanmax(base_axis)))
            span = min(float(np.nanmax(axis)) - float(np.nanmin(axis)),
                       float(np.nanmax(base_axis)) - float(np.nanmin(base_axis)))
            overlap = (hi - lo) / span if span > 0 else 0.0
            if span <= 0:
                skip_reasons[id(cand)] = ("low_overlap",
                                          "degenerate or non-overlapping time ranges")
                continue
            if overlap < 0.3:
                skip_reasons[id(cand)] = (
                    "low_overlap",
                    f"time-axis overlap with primary {max(overlap, 0.0):.0%} < 30% gate")
                continue
            merged_dfs.append((fname, cand["df"], ctime, cand))
            merged_cand_ids.add(id(cand))
        if len(merged_dfs) >= 2:
            base = merged_dfs[0][1].copy()
            base_time = merged_dfs[0][2]
            merge_info = {
                "strategy": "outer_merge_on_time_column",
                "key": base_time,
                "primary_time_column": ptime,
                "source_time_columns": {f: t for f, _, t, _c in merged_dfs},
                "note": ("outer merge on the normalized time axis; 'key' is the join "
                         "column actually used (the FIRST merged table's time column — "
                         "it can differ from the primary table's own, which is reported "
                         "in primary_time_column); values normalized to ISO before join"),
                "merged_files": sorted({f for f, _, _, _ in merged_dfs}),
            }
            if cadence_gate:
                merge_info["source_cadence_seconds"] = {
                    f: (round(c, 3) if c is not None else None)
                    for f, c in sorted(cadences.items())}
                positive = [c for c in cadences.values() if c]
                merge_info["cadence_ratio"] = (round(max(positive) / min(positive), 3)
                                               if positive else None)
                if cadence_allowed:
                    merge_info["cadence_mismatch_allowed"] = sorted(cadence_allowed)
            base[base_time] = pd.to_datetime(base[base_time], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
            column_source: Dict[str, str] = {c: merged_dfs[0][0] for c in base.columns}
            for fname, df, ctime, cand in merged_dfs[1:]:
                right = df.copy()
                right[ctime] = pd.to_datetime(right[ctime], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
                if ctime != base_time:
                    right = right.rename(columns={ctime: base_time})
                dup = [c for c in right.columns
                       if c in base.columns and c != base_time]
                fill_cols: List[str] = []
                if column_audit and dup:
                    drop_cols: List[str] = []
                    for c in dup:
                        if _dup_columns_agree(base, base_time, right, c):
                            fill_cols.append(c)
                        else:
                            drop_cols.append(c)
                            merge_exclusions.append({
                                "file": fname, "sheet": cand.get("sheet"), "column": c,
                                "reason_code": "duplicate_column_semantics_mismatch",
                                "detail": (f"column '{c}' also exists in the merged view and its values "
                                           "disagree on the aligned time axis; right-table copy dropped")})
                    right = right.drop(columns=drop_cols)
                else:
                    right = right.drop(columns=dup)
                if column_audit:
                    for c in right.columns:
                        if c != base_time and c not in column_source:
                            column_source[c] = fname
                    base = base.merge(right, on=base_time, how="outer", sort=True,
                                      suffixes=("", "__merge_fill"))
                    for c in fill_cols:
                        filled = f"{c}__merge_fill"
                        if filled in base.columns:
                            base[c] = _blank_to_nan(base[c]).combine_first(
                                _blank_to_nan(base[filled]))
                            base = base.drop(columns=[filled])
                else:
                    base = base.merge(right, on=base_time, how="outer", sort=True)
            base = _normalize_columns(base)
            if column_audit:
                merge_info["column_source"] = {c: column_source.get(c, merged_dfs[0][0])
                                               for c in base.columns}
            # Anti-bloat gate: a clean time-axis join never grows beyond the
            # largest source table by much (rows = union of timestamps). If it
            # balloons (failed key alignment), abandon the merge and keep the
            # largest single table instead.
            max_src = max(m.shape[0] for _, m, _, _c in merged_dfs)
            if base.shape[0] > 1.5 * max_src:
                merge_info = {
                    "strategy": "abandoned",
                    "reason": f"merged rows {base.shape[0]} > 1.5x largest source ({max_src}); "
                              "time keys did not align — keeping largest single table",
                    "merged_files": sorted({f for f, _, _, _ in merged_dfs}),
                }
                primary = max(candidates, key=lambda c: c[1]["score"])
                fallback = "score_fallback"
            else:
                primary = (primary[0], {**primary[1], "df": base,
                                        "n_rows": int(base.shape[0]),
                                        "n_cols": int(base.shape[1]),
                                        "time_column": base_time})

    # ---- per-file exclusion reasons for every table outside the unified view ----
    for fname, cand in candidates:
        if cand is primary[1]:
            continue  # the selected (possibly merged) table is never "excluded"
        if id(cand) in merged_cand_ids and merge_info is not None:
            continue  # actually merged; merged-then-abandoned is disclosed in merge_info
        if cand["n_rows"] < 100:
            code, detail = "below_min_rows", f"{cand['n_rows']} rows < 100 merge threshold"
        elif not cand["time_column"]:
            code, detail = "no_timestamp", "no time column detected"
        else:
            code, detail = skip_reasons.get(id(cand)) or (
                "merge_not_attempted",
                "only one merge-eligible table (needs >=2); merge skipped"
                if id(cand) in merged_cand_ids else "merge did not execute")
        merge_exclusions.append({"file": fname, "sheet": cand.get("sheet"),
                                 "reason_code": code, "detail": detail})
    return primary, fallback, merge_info, merge_exclusions


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def _discover_sources(data_path: Path, recursive: bool = False, exclude_paths: Optional[set] = None) -> List[Path]:
    if data_path.is_file():
        return [data_path]
    exclude_paths = exclude_paths or set()
    iterator = data_path.rglob('*') if recursive else data_path.iterdir()
    out: List[Path] = []
    for path in iterator:
        if path.is_dir() or path.is_symlink():
            continue
        resolved = path.resolve()
        if resolved in exclude_paths:
            continue
        if any(part.startswith('.') or part in {'node_modules', '__pycache__'} for part in path.relative_to(data_path).parts):
            continue
        out.append(path)
    return sorted(out, key=lambda path: path.relative_to(data_path).as_posix().casefold())


def _classify(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in _TABLE_EXTS:
        return "table"
    if ext in _CONTEXT_EXTS:
        return "context"
    return "skip"


def preprocess(data_path: Path, output_dir: Path, run_name: str = "") -> dict:
    """Main entry: discover → extract → select/merge → normalize → emit."""
    output_dir.mkdir(parents=True, exist_ok=True)
    context_dir = output_dir / "context"
    context_dir.mkdir(parents=True, exist_ok=True)

    sources = _discover_sources(data_path)
    if not sources:
        return _fail_report(output_dir, run_name, "no files found", str(data_path))

    report: Dict[str, Any] = {
        "run_name": run_name,
        "input_path": str(data_path),
        "input_is_directory": data_path.is_dir(),
        "sources": [],
        "tables": [],
        "selected_table": None,
        "merge": None,
        "merge_exclusions": [],
        "quality": {},
        "context_files": [],
        "skipped_files": [],
        "status": "ok",
    }

    candidates: List[Tuple[str, dict]] = []  # (file_name, block)
    for src in sources:
        cls = _classify(src)
        if cls == "skip":
            report["skipped_files"].append({"file": src.name,
                                            "reason": f"extension {src.suffix or '(none)'} not tabular/context"})
            continue
        if cls == "context":
            dest = context_dir / src.name
            shutil.copy2(src, dest)
            report["context_files"].append(str(dest))
            report["sources"].append({"file": src.name, "role": "context",
                                      "reason": "non-tabular document preserved for ontology/context builder"})
            continue

        ext = src.suffix.lower()
        blocks: List[dict] = []
        try:
            if ext in (".csv", ".tsv", ".txt", ".dat"):
                blocks = _parse_delimited_text(src)
            elif ext in (".xlsx", ".xlsm", ".xls"):
                blocks = _parse_excel(src)
            elif ext == ".json":
                blocks = _parse_json(src)
            elif ext in (".parquet", ".pq"):
                frame = pd.read_parquet(src)
                blocks = [{"source": src.name, "sheet": None, "format": "parquet",
                           "encoding": None, "header": [str(c) for c in frame.columns],
                           "rows": frame.astype(object).where(pd.notna(frame), None).values.tolist()}]
            elif ext in (".md", ".markdown"):
                blocks = _parse_markdown(src)
            elif ext in (".html", ".htm"):
                blocks = _parse_html(src)
        except Exception as exc:
            # one broken source must not sink the whole run — record and move on
            report["sources"].append({"file": src.name, "role": "error",
                                      "reason": f"table parse failed: {exc}"})
            continue

        if not blocks:
            report["sources"].append({"file": src.name, "role": "no_tabular",
                                      "reason": "no tabular content detected"})
            if ext in (".md", ".markdown", ".txt"):
                dest = context_dir / src.name
                shutil.copy2(src, dest)
                report["context_files"].append(str(dest))
            continue

        if any("error" in b for b in blocks):
            for b in blocks:
                if "error" in b:
                    report["sources"].append({"file": src.name, "role": "error",
                                              "reason": b["error"]})
            continue

        # materialize every block as a scored DataFrame candidate
        for bi, b in enumerate(blocks):
            df = _block_to_df(b)
            if df.shape[0] < 2 or df.shape[1] < 1:
                continue
            # Markdown/HTML tables with <5 data rows are snippets (e.g. a table
            # inside a process description), not the dataset — keep as context.
            if b.get("format") in ("markdown", "html") and df.shape[0] < 5:
                report["sources"].append({"file": src.name, "role": "context",
                                          "reason": f"tiny {b.get('format')} table ({df.shape[0]} rows) — document snippet"})
                dest = context_dir / src.name
                if not dest.exists():
                    shutil.copy2(src, dest)
                    report["context_files"].append(str(dest))
                continue
            tcol = _detect_time_col(df)
            score = _score_table(df, tcol)
            cand = {
                "file": src.name,
                "sheet": b.get("sheet"),
                "format": b.get("format", ext.lstrip(".")),
                "n_rows": int(df.shape[0]),
                "n_cols": int(df.shape[1]),
                "time_column": tcol,
                "score": round(score, 3),
                "numeric_density": round(b.get("numeric_density", _numeric_density(
                    [str(v) for v in df.iloc[:200].to_numpy().ravel()])), 3),
                "block_index": bi,
                "df": df,
            }
            candidates.append((src.name, cand))
            report["tables"].append({
                "file": src.name,
                "sheet": b.get("sheet"),
                "format": b.get("format"),
                "n_rows": int(df.shape[0]),
                "n_cols": int(df.shape[1]),
                "time_column": tcol,
                "score": round(score, 3),
                "quality_flags": _quality_flags(df, b),
            })

    if not candidates:
        report["status"] = "no_tabular_data"
        _write_report(output_dir, report)
        return report

    # ---- selection / merge --------------------------------------------
    primary: Optional[Tuple[str, dict]] = None
    merge_info: Optional[dict] = None
    selected_kind = "score"

    # 1) already-merged product files win outright (user-aligned final data)
    premerged = [c for c in candidates
                 if _looks_premerged(c[0]) and c[1]["n_rows"] >= 100]
    if premerged:
        primary = max(premerged, key=lambda c: c[1]["n_rows"])
        selected_kind = "premerged_file"
    if primary is None:
        # 2) Excel sheet whose name matches the file stem is THE data
        for fname, cand in candidates:
            stem = Path(fname).stem.lower()
            if cand["sheet"] and cand["sheet"].lower() == stem and cand["n_rows"] >= 100:
                primary = (fname, cand)
                selected_kind = "excel_stem_match"
                break
    if primary is None:
        # 3) largest by score
        primary = max(candidates, key=lambda c: c[1]["score"])

    # 3) attempt merge ONLY when no premerged product exists: several raw
    #    exports sharing a time axis, bounded by an anti-bloat gate (see
    #    _merge_onto_time_axis). Every table that does not make the unified
    #    view gets an explicit per-file exclusion reason in
    #    report["merge_exclusions"].
    primary, fallback_kind, merge_info, merge_exclusions = _merge_onto_time_axis(
        primary, candidates, premerged_selected=(selected_kind == "premerged_file"))
    if fallback_kind:
        selected_kind = fallback_kind
    report["merge_exclusions"] = merge_exclusions

    fname, cand = primary
    df = cand["df"].copy()
    report["selected_table"] = {
        "file": fname,
        "sheet": cand["sheet"],
        "format": cand["format"],
        "n_rows": int(df.shape[0]),
        "n_cols": int(df.shape[1]),
        "time_column": cand["time_column"],
        "score": cand["score"],
        "why": {
            "premerged_file": "file is an already-merged/alignment product of the raw exports",
            "excel_stem_match": "sheet name matches file stem",
            "score": "highest table score",
            "score_fallback": "merge abandoned (anti-bloat); largest single table",
        }.get(selected_kind, selected_kind),
    }
    if merge_info:
        report["merge"] = merge_info

    # ---- normalize + emit ---------------------------------------------
    time_col = cand["time_column"]
    if time_col is not None:
        try:
            parsed = pd.to_datetime(df[time_col], errors="coerce")
            # keep original values but report parseability; normalize
            # ISO-format copies only for clearly-parseable rows
            df[time_col] = parsed.dt.strftime("%Y-%m-%d %H:%M:%S").where(
                parsed.notna(), df[time_col].astype(str))
        except Exception:
            pass

    missing_pct = round(float(df.isna().mean().mean()) * 100, 2)
    report["quality"] = {
        "missing_cell_pct": missing_pct,
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "time_column": time_col,
        "numeric_columns": _numeric_cols(df),
        "note": "missing cells stay NaN; downstream cleaning handles them",
    }

    csv_out = output_dir / "preprocessed_data.csv"
    json_out = output_dir / "preprocessed_data.json"
    df.to_csv(csv_out, index=False, encoding="utf-8-sig")
    df.to_json(json_out, orient="records", force_ascii=False, indent=1)

    report["outputs"] = {
        "preprocessed_data.csv": str(csv_out),
        "preprocessed_data.json": str(json_out),
        "context_dir": str(context_dir),
    }
    report["status"] = "ok"
    _write_report(output_dir, report)
    return report




def _preprocess_stability_folder(data_path: Path, output_dir: Path, run_name: str = "", recursive: bool = True) -> dict:
    """Folder contract for stability reports: discover every source, score one time-series primary, audit the rest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    context_dir = output_dir / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    excluded_prefix = ()
    if data_path.is_dir() and output_dir.resolve().is_relative_to(data_path.resolve()):
        excluded_prefix = output_dir.resolve().relative_to(data_path.resolve()).parts
    sources = _discover_sources(data_path, recursive=recursive)
    if excluded_prefix:
        sources = [p for p in sources if p.relative_to(data_path).parts[:len(excluded_prefix)] != excluded_prefix]

    audit = {
        "run_name": run_name, "input_path": str(data_path), "input_is_directory": data_path.is_dir(),
        "recursive_discovery": recursive, "mode": "stability_single_primary_v1",
        "sources": [], "source_dispositions": [], "tables": [], "selected_table": None,
        "merge": None, "merge_exclusions": [], "quality": {}, "context_files": [],
        "skipped_files": [], "status": "ok",
    }
    candidates = []
    for source in sources:
        relative_path = source.relative_to(data_path).as_posix() if data_path.is_dir() else source.name
        protected_name = source.stem.casefold()
        if any(token in protected_name for token in ("ground_truth", "groundtruth", "truth", "answer", "solution", "评分参考", "标准答案")):
            audit["source_dispositions"].append({"relative_path": relative_path, "role": "protected_truth", "disposition": "protected_excluded",
                                                 "reason": "truth/answer reference is excluded without reading or copying its contents"})
            continue
        role_hint, role_reason = _file_role(source)
        cls = _classify(source)
        if cls == "skip":
            reason = f"extension {source.suffix or '(none)'} is not a supported table/context format"
            audit["skipped_files"].append({"file": relative_path, "reason": reason})
            audit["source_dispositions"].append({"relative_path": relative_path, "role": "skipped", "disposition": "skipped", "reason": reason})
            continue
        if role_hint in ("context", "metadata") or cls == "context":
            destination = context_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            audit["context_files"].append(relative_path)
            role = "metadata" if role_hint == "metadata" else "context"
            reason = role_reason if role_hint in ("context", "metadata") else "non-tabular document preserved as context"
            audit["sources"].append({"file": relative_path, "role": role, "reason": reason})
            audit["source_dispositions"].append({"relative_path": relative_path, "role": role,
                                                 "disposition": "context_only", "reason": reason})
            continue
        if role_hint in ("event", "auxiliary"):
            audit["sources"].append({"file": relative_path, "role": role_hint, "reason": role_reason})
            audit["source_dispositions"].append({"relative_path": relative_path, "role": role_hint,
                                                 "disposition": "excluded_from_scoring", "reason": role_reason})
            continue

        ext = source.suffix.lower()
        try:
            if ext in (".csv", ".tsv", ".txt", ".dat"):
                blocks = _parse_delimited_text(source)
            elif ext in (".xlsx", ".xlsm", ".xls"):
                blocks = _parse_excel(source)
            elif ext == ".json":
                blocks = _parse_json(source)
            elif ext in (".parquet", ".pq"):
                frame = pd.read_parquet(source)
                blocks = [{"source": source.name, "sheet": None, "format": "parquet",
                           "encoding": None, "header": [str(c) for c in frame.columns],
                           "rows": frame.astype(object).where(pd.notna(frame), None).values.tolist()}]
            elif ext in (".md", ".markdown"):
                blocks = _parse_markdown(source)
            elif ext in (".html", ".htm"):
                blocks = _parse_html(source)
            else:
                blocks = []
        except Exception as exc:
            reason = f"table parse failed: {exc}"
            audit["sources"].append({"file": relative_path, "role": "error", "reason": reason})
            audit["source_dispositions"].append({"relative_path": relative_path, "role": "error", "disposition": "error", "reason": reason})
            continue

        if not blocks or any("error" in block for block in blocks):
            reason = next((block["error"] for block in blocks if "error" in block), "no tabular content detected")
            role = "error" if any("error" in block for block in blocks) else "no_tabular"
            audit["sources"].append({"file": relative_path, "role": role, "reason": reason})
            audit["source_dispositions"].append({"relative_path": relative_path, "role": role,
                                                 "disposition": "error" if role == "error" else "excluded_from_scoring",
                                                 "reason": reason})
            continue

        for block_index, block in enumerate(blocks):
            frame = _block_to_df(block)
            if frame.shape[0] < 2 or frame.shape[1] < 1:
                continue
            if block.get("format") in ("markdown", "html") and frame.shape[0] < 5:
                audit["sources"].append({"file": relative_path, "role": "context", "reason": "small document table is context, not process data"})
                audit["source_dispositions"].append({"relative_path": relative_path, "role": "context", "disposition": "context_only", "reason": "small document table is context, not process data"})
                continue
            time_col = _detect_time_col(frame)
            time_parseability = 0.0
            if time_col:
                time_parseability = float(pd.to_datetime(frame[time_col], errors="coerce").notna().mean())
            score = _score_table(frame, time_col)
            table = {"file": relative_path, "sheet": block.get("sheet"), "format": block.get("format", ext.lstrip('.')),
                     "n_rows": int(len(frame)), "n_cols": int(len(frame.columns)), "time_column": time_col,
                     "time_parseability": round(time_parseability, 4),
                     "score": round(score, 3), "quality_flags": _quality_flags(frame, block),
                     "block_index": block_index, "df": frame}
            audit["tables"].append({k: v for k, v in table.items() if k not in ("df", "block_index")})
            if time_col:
                candidates.append(table)
                audit["source_dispositions"].append({"relative_path": relative_path, "sheet": block.get("sheet"),
                    "role": "time_series_candidate", "disposition": "candidate", "reason": role_reason,
                    "rows": len(frame), "columns": len(frame.columns), "time_column": time_col,
                    "score": table["score"], "time_parseability": table["time_parseability"]})
            else:
                audit["source_dispositions"].append({"relative_path": relative_path, "sheet": block.get("sheet"),
                    "role": "tabular_without_time", "disposition": "excluded_from_scoring",
                    "reason": "stability score requires a parseable time column", "rows": len(frame),
                    "columns": len(frame.columns), "time_column": None})

    eligible = [item for item in candidates if item["n_rows"] >= 50 and item["time_parseability"] >= 0.8]
    if not eligible:
        audit["status"] = "no_time_series"
        audit["reason"] = "no time-series table with at least 50 rows was found"
        _write_report(output_dir, audit)
        return audit
    primary = max(eligible, key=lambda item: (int(_looks_premerged(item["file"])), item["score"], item["time_parseability"], item["n_rows"], item["file"].casefold()))
    for item in candidates:
        if item is primary:
            for disposition in audit["source_dispositions"]:
                if disposition.get("relative_path") == item["file"] and disposition.get("sheet") == item.get("sheet"):
                    disposition.update({"role": "primary_time_series", "disposition": "selected",
                                        "reason": "highest-scoring eligible time-series table"})
                    break
            continue
        role, reason = _file_role(Path(item["file"]))
        detail = f"{reason}; stability folder mode uses one primary time-series table; no resampling or blind merge"
        code = "below_min_rows" if item["n_rows"] < 50 else "single_primary_policy"
        audit["merge_exclusions"].append({"file": item["file"], "sheet": item.get("sheet"),
                                          "reason_code": code, "detail": detail})
        for disposition in audit["source_dispositions"]:
            if disposition.get("relative_path") == item["file"] and disposition.get("sheet") == item.get("sheet"):
                disposition.update({"role": role, "disposition": "excluded_from_scoring",
                                    "reason": detail, "reason_code": code})
                break

    df = primary["df"].copy()
    time_col = primary["time_column"]
    parsed = pd.to_datetime(df[time_col], errors="coerce")
    df[time_col] = parsed.dt.strftime("%Y-%m-%d %H:%M:%S").where(parsed.notna(), df[time_col].astype(str))
    audit["selected_table"] = {k: v for k, v in primary.items() if k not in ("df", "block_index", "quality_flags")}
    audit["selected_table"]["why"] = "highest-scoring time-series candidate (premerged filename gets priority)"
    audit["merge"] = {"strategy": "single_primary_no_merge", "reason": "folder stability mode does not resample or combine different acquisition cadences", "merged_files": []}
    audit["quality"] = {"rows": len(df), "cols": len(df.columns), "time_column": time_col,
                        "numeric_columns": _numeric_cols(df),
                        "missing_cell_pct": round(float(df.isna().mean().mean()) * 100, 2)}
    csv_out = output_dir / "preprocessed_data.csv"
    json_out = output_dir / "preprocessed_data.json"
    df.to_csv(csv_out, index=False, encoding="utf-8-sig")
    df.to_json(json_out, orient="records", force_ascii=False, indent=1)
    audit["outputs"] = {"preprocessed_data.csv": str(csv_out), "preprocessed_data.json": str(json_out), "context_dir": str(context_dir)}
    _write_report(output_dir, audit)
    return audit


def _preprocess_integrate_merge(data_path: Path, output_dir: Path, run_name: str = "",
                                recursive: bool = True,
                                allow_cadence_mismatch: bool = False) -> dict:
    """Folder contract for multi-source integration: pick ONE canonical primary
    by the stability rules (>=50 rows, >=80% parseable time axis), then
    outer-merge every other large (>=100 rows) time-aligned source onto it via
    _merge_onto_time_axis (cadence gate + overlap gate + anti-bloat gate +
    duplicate-column semantics audit). Strict exit contract surfaced by main():
    no usable primary or a merged primary below 50 rows is a usage-grade
    failure (exit 2)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    context_dir = output_dir / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    excluded_prefix = ()
    if data_path.is_dir() and output_dir.resolve().is_relative_to(data_path.resolve()):
        excluded_prefix = output_dir.resolve().relative_to(data_path.resolve()).parts
    sources = _discover_sources(data_path, recursive=recursive)
    if excluded_prefix:
        sources = [p for p in sources if p.relative_to(data_path).parts[:len(excluded_prefix)] != excluded_prefix]

    audit = {
        "run_name": run_name, "input_path": str(data_path), "input_is_directory": data_path.is_dir(),
        "recursive_discovery": recursive, "mode": "integrate_merge_v1",
        "sources": [], "source_dispositions": [], "tables": [], "selected_table": None,
        "merge": None, "merge_exclusions": [], "quality": {}, "context_files": [],
        "skipped_files": [], "status": "ok",
    }
    if not sources:
        audit["status"] = "no_usable_primary"
        audit["reason"] = "no files found"
        _write_report(output_dir, audit)
        return audit

    candidates = []
    for source in sources:
        relative_path = source.relative_to(data_path).as_posix() if data_path.is_dir() else source.name
        protected_name = source.stem.casefold()
        if any(token in protected_name for token in ("ground_truth", "groundtruth", "truth", "answer", "solution", "评分参考", "标准答案")):
            audit["source_dispositions"].append({"relative_path": relative_path, "role": "protected_truth", "disposition": "protected_excluded",
                                                 "reason": "truth/answer reference is excluded without reading or copying its contents"})
            continue
        role_hint, role_reason = _file_role(source)
        cls = _classify(source)
        if cls == "skip":
            reason = f"extension {source.suffix or '(none)'} is not a supported table/context format"
            audit["skipped_files"].append({"file": relative_path, "reason": reason})
            audit["source_dispositions"].append({"relative_path": relative_path, "role": "skipped", "disposition": "skipped", "reason": reason})
            continue
        if role_hint in ("context", "metadata") or cls == "context":
            destination = context_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            audit["context_files"].append(relative_path)
            role = "metadata" if role_hint == "metadata" else "context"
            reason = role_reason if role_hint in ("context", "metadata") else "non-tabular document preserved as context"
            audit["sources"].append({"file": relative_path, "role": role, "reason": reason})
            audit["source_dispositions"].append({"relative_path": relative_path, "role": role,
                                                 "disposition": "context_only", "reason": reason})
            continue
        # event/auxiliary filename hints stay in the merge pool here: the
        # cadence/overlap/anti-bloat gates — not the filename — decide what
        # integrates onto the primary

        ext = source.suffix.lower()
        try:
            if ext in (".csv", ".tsv", ".txt", ".dat"):
                blocks = _parse_delimited_text(source)
            elif ext in (".xlsx", ".xlsm", ".xls"):
                blocks = _parse_excel(source)
            elif ext == ".json":
                blocks = _parse_json(source)
            elif ext in (".parquet", ".pq"):
                frame = pd.read_parquet(source)
                blocks = [{"source": source.name, "sheet": None, "format": "parquet",
                           "encoding": None, "header": [str(c) for c in frame.columns],
                           "rows": frame.astype(object).where(pd.notna(frame), None).values.tolist()}]
            elif ext in (".md", ".markdown"):
                blocks = _parse_markdown(source)
            elif ext in (".html", ".htm"):
                blocks = _parse_html(source)
            else:
                blocks = []
        except Exception as exc:
            reason = f"table parse failed: {exc}"
            audit["sources"].append({"file": relative_path, "role": "error", "reason": reason})
            audit["source_dispositions"].append({"relative_path": relative_path, "role": "error", "disposition": "error", "reason": reason})
            continue

        if not blocks or any("error" in block for block in blocks):
            reason = next((block["error"] for block in blocks if "error" in block), "no tabular content detected")
            role = "error" if any("error" in block for block in blocks) else "no_tabular"
            audit["sources"].append({"file": relative_path, "role": role, "reason": reason})
            audit["source_dispositions"].append({"relative_path": relative_path, "role": role,
                                                 "disposition": "error" if role == "error" else "excluded_from_scoring",
                                                 "reason": reason})
            continue

        for block_index, block in enumerate(blocks):
            frame = _block_to_df(block)
            if frame.shape[0] < 2 or frame.shape[1] < 1:
                continue
            if block.get("format") in ("markdown", "html") and frame.shape[0] < 5:
                audit["sources"].append({"file": relative_path, "role": "context", "reason": "small document table is context, not process data"})
                audit["source_dispositions"].append({"relative_path": relative_path, "role": "context", "disposition": "context_only", "reason": "small document table is context, not process data"})
                continue
            time_col = _detect_time_col(frame)
            time_parseability = 0.0
            if time_col:
                time_parseability = float(pd.to_datetime(frame[time_col], errors="coerce").notna().mean())
            score = _score_table(frame, time_col)
            table = {"file": relative_path, "sheet": block.get("sheet"), "format": block.get("format", ext.lstrip('.')),
                     "n_rows": int(len(frame)), "n_cols": int(len(frame.columns)), "time_column": time_col,
                     "time_parseability": round(time_parseability, 4),
                     "score": round(score, 3), "quality_flags": _quality_flags(frame, block),
                     "block_index": block_index, "df": frame}
            audit["tables"].append({k: v for k, v in table.items() if k not in ("df", "block_index")})
            if time_col:
                candidates.append(table)
                audit["source_dispositions"].append({"relative_path": relative_path, "sheet": block.get("sheet"),
                    "role": "time_series_candidate", "disposition": "candidate",
                    "reason": role_reason, "rows": len(frame), "columns": len(frame.columns),
                    "time_column": time_col, "score": table["score"],
                    "time_parseability": table["time_parseability"]})
            else:
                audit["source_dispositions"].append({"relative_path": relative_path, "sheet": block.get("sheet"),
                    "role": "tabular_without_time", "disposition": "excluded_from_merge",
                    "reason": "integrate-merge joins on the time axis; table has no usable time column",
                    "rows": len(frame), "columns": len(frame.columns), "time_column": None})

    eligible = [item for item in candidates if item["n_rows"] >= 50 and item["time_parseability"] >= 0.8]
    if not eligible:
        audit["status"] = "no_usable_primary"
        audit["reason"] = "no table with at least 50 rows and >=80% parseable time column was found"
        _write_report(output_dir, audit)
        return audit
    selected = max(eligible, key=lambda item: (int(_looks_premerged(item["file"])), item["score"],
                                               item["time_parseability"], item["n_rows"], item["file"].casefold()))
    merge_pool = [(selected["file"], selected)]
    merge_pool += [(item["file"], item) for item in candidates if item is not selected]
    primary_pair, fallback_kind, merge_info, merge_exclusions = _merge_onto_time_axis(
        merge_pool[0], merge_pool, primary_always_joins=True, cadence_gate=True,
        allow_cadence_mismatch=allow_cadence_mismatch, column_audit=True)
    audit["merge_exclusions"] = merge_exclusions
    audit["merge"] = merge_info or {
        "strategy": "no_merge",
        "reason": "no other merge-eligible table (rows>=100 with a usable time axis)",
        "merged_files": [],
    }

    sel_file, sel_cand = primary_pair
    df = sel_cand["df"].copy()
    time_col = sel_cand["time_column"]
    if df.shape[0] < 50:
        audit["status"] = "merged_primary_too_small"
        audit["reason"] = (f"merged primary table has {df.shape[0]} rows < 50 minimum; "
                           "outputs are still written for inspection")
    if time_col is not None:
        try:
            parsed = pd.to_datetime(df[time_col], errors="coerce")
            df[time_col] = parsed.dt.strftime("%Y-%m-%d %H:%M:%S").where(parsed.notna(), df[time_col].astype(str))
        except Exception:
            pass
    audit["selected_table"] = {k: v for k, v in sel_cand.items() if k not in ("df", "block_index", "quality_flags")}
    audit["selected_table"]["why"] = ("highest-scoring eligible time-series table (premerged filename gets priority); "
                                      "other time-aligned sources outer-merged onto it behind the cadence/overlap/anti-bloat gates")

    # disposition pass: selected / merged / merge_abandoned / excluded_from_merge
    merge_block = audit["merge"]
    merged_files = set(merge_block.get("merged_files") or [])
    merge_ok = merge_block.get("strategy") == "outer_merge_on_time_column"
    merge_dropped = merge_block.get("strategy") == "abandoned"
    excluded_by_key = {(e["file"], e.get("sheet")): e
                       for e in audit["merge_exclusions"] if "column" not in e}
    for disposition in audit["source_dispositions"]:
        if disposition.get("disposition") != "candidate":
            continue
        key = (disposition.get("relative_path"), disposition.get("sheet"))
        if key == (sel_file, sel_cand.get("sheet")):
            disposition.update({"role": "primary_time_series", "disposition": "selected",
                                "reason": "highest-scoring eligible time-series table; merge base"})
        elif merge_ok and disposition.get("relative_path") in merged_files:
            disposition.update({"role": "merged_source", "disposition": "merged",
                                "reason": "outer-merged onto the primary time axis"})
        elif merge_dropped and disposition.get("relative_path") in merged_files:
            disposition.update({"role": "merged_source", "disposition": "merge_abandoned",
                                "reason": merge_block.get("reason")})
        else:
            exclusion = excluded_by_key.get(key)
            if exclusion:
                disposition.update({"disposition": "excluded_from_merge",
                                    "reason": exclusion.get("detail"),
                                    "reason_code": exclusion.get("reason_code")})

    audit["quality"] = {"rows": len(df), "cols": len(df.columns), "time_column": time_col,
                        "numeric_columns": _numeric_cols(df),
                        "missing_cell_pct": round(float(df.isna().mean().mean()) * 100, 2)}
    csv_out = output_dir / "preprocessed_data.csv"
    json_out = output_dir / "preprocessed_data.json"
    df.to_csv(csv_out, index=False, encoding="utf-8-sig")
    df.to_json(json_out, orient="records", force_ascii=False, indent=1)
    audit["outputs"] = {"preprocessed_data.csv": str(csv_out), "preprocessed_data.json": str(json_out), "context_dir": str(context_dir)}
    _write_report(output_dir, audit)
    return audit


def _numeric_cols(df: pd.DataFrame) -> List[str]:
    out = []
    for c in df.columns:
        try:
            if pd.to_numeric(df[c], errors="coerce").notna().mean() > 0.7:
                out.append(str(c))
        except Exception:
            pass
    return out


def _fail_report(output_dir: Path, run_name: str, reason: str,
                 input_path: str) -> dict:
    report = {
        "run_name": run_name,
        "input_path": input_path,
        "status": "no_tabular_data",
        "reason": reason,
        "sources": [],
        "tables": [],
        "selected_table": None,
        "merge": None,
        "merge_exclusions": [],
        "quality": {},
        "context_files": [],
        "skipped_files": [],
    }
    _write_report(output_dir, report)
    return report


def _write_report(output_dir: Path, report: dict) -> None:
    # strip live DataFrames before serializing
    clean = json.loads(json.dumps(report, default=lambda o: None, ensure_ascii=False))
    (output_dir / "preprocessing_report.json").write_text(
        json.dumps(clean, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="E-1: adaptive data preprocessing")
    ap.add_argument("--data-path", required=True, help="file or directory")
    ap.add_argument("--output", required=True, help="output dir (RUN_DIR/00_input)")
    ap.add_argument("--name", default="", help="run name (optional)")
    ap.add_argument("--recursive", action="store_true", help="discover sources recursively")
    mode_group = ap.add_mutually_exclusive_group()
    mode_group.add_argument("--stability-single-primary", "--single-primary", dest="stability_single_primary",
                            action="store_true", help="adaptive folder audit with one primary table; no multi-cadence merge")
    mode_group.add_argument("--integrate-merge", dest="integrate_merge", action="store_true",
                            help="folder multi-source integration: stability-rule primary selection, then a gated outer "
                                 "merge of the other sources onto it (strict exits: no usable primary or merged primary "
                                 "<50 rows -> exit 2)")
    ap.add_argument("--allow-cadence-mismatch", dest="allow_cadence_mismatch", action="store_true",
                    help="integrate-merge only: merge sources whose median cadence ratio exceeds the gate "
                         "instead of excluding them as cadence_mismatch")
    args = ap.parse_args()

    data_path = Path(args.data_path)
    if not data_path.exists():
        print(f"ERROR: data path does not exist: {data_path}", file=sys.stderr)
        sys.exit(1)
    output = Path(args.output)
    single_primary = getattr(args, "stability_single_primary", False)
    integrate = getattr(args, "integrate_merge", False)
    if single_primary:
        report = _preprocess_stability_folder(data_path, output, args.name, recursive=True)
    elif integrate:
        report = _preprocess_integrate_merge(data_path, output, args.name,
                                             allow_cadence_mismatch=bool(args.allow_cadence_mismatch))
    else:
        report = preprocess(data_path, output, args.name)
    print(json.dumps({
        "status": report["status"],
        "selected": report.get("selected_table"),
        "tables_found": len(report.get("tables", [])),
        "context_files": len(report.get("context_files", [])),
        "skipped_files": len(report.get("skipped_files", [])),
        "source_files_found": (len(report.get("source_dispositions", []))
                               if single_primary or integrate
                               else len(report.get("sources", [])) + len(report.get("tables", []))),
        "source_dispositions": report.get("source_dispositions", []),
        "report": str(output / "preprocessing_report.json"),
    }, indent=2, ensure_ascii=False))
    if integrate:
        # strict contract: only a completed integration run is ok;
        # no_usable_primary / merged_primary_too_small are usage-grade (exit 2)
        if report["status"] == "ok":
            sys.exit(0)
        sys.exit(2 if report["status"] in ("no_usable_primary", "merged_primary_too_small") else 1)
    ok_statuses = ("ok",) if single_primary else ("ok", "no_tabular_data")
    sys.exit(0 if report["status"] in ok_statuses else 1)


if __name__ == "__main__":
    main()
