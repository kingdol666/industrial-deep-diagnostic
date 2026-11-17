"""txt.py — TXT shape (WS2): time-anchored text annotations (plan v1.1 §3.1 TXT row).

Two accepted layouts:
  1. CSV remarks table  — a table with a parseable time column AND a long
     free-text column (found via discover.probe_csv_text_column, text share
     >= 0.5), at least 2 data rows.
  2. Prose log          — a .md/.markdown/.txt/.log file where >= 2 sampled
     lines contain a timestamp candidate (line start or inline).

Outputs (frozen I9 / I5 / I6):
  annotations.json entries — {event_ts, recorded_ts, text, tags[], source_id,
    source_sha256, line_no, hour_of_day, shift_bucket}; tags are LEXICON hits
    only (method="lexicon", model_derived=false); unparsable timestamps are
    recorded with event_ts=null and counted, never guessed.
  rows DataFrame           — one row per timestamped event: ts,_src_ts(=ts),
    n_inputs(=1), EVT-<SLUG>(=1) plus two clock covariates
    (HOUR-OF-DAY, SHIFT-BUCKET-ID). Event windows are NOT applied here:
    the join layer (WS5 align) reads evt_window_s from the contract and
    expires flags forward-only ([t-window, t], never backward).
  contract rows            — EVT columns: role=metadata, stats_eligible=false
    (sparse), evidence_level=2 (user documents), evt_window_s (default 3600,
    overridable via ctx.config["event_window_s"]).

Ambiguity discipline (plan §4): a source where a date admits both DD/MM and
MM/DD readings is skipped WHOLE (disposition="skipped", reason mentions
"ambiguous") — no guessing.

Tag slugs use "_" (annotations_schema pattern ^[A-Z0-9_]+$); column names use
"-" because the frozen I3 machine-name alphabet is [A-Z0-9-] only.
line_no semantics: prose = 1-based physical file line; CSV = 1-based data-row
index (header excluded).
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from heterocore import CONTRACT_VERSION  # noqa: E402
from heterocore import discover as disc  # noqa: E402
from heterocore import manifest as mani  # noqa: E402
from heterocore import naming  # noqa: E402
from heterocore import time_ingest as ting  # noqa: E402

SHAPE = "text"
TS_SOURCE = "manual"
PROSE_EXTS = {".md", ".markdown", ".txt", ".log"}
CSV_EXTS = {".csv", ".tsv", ".dat"}
RECORDED_COL_NAMES = ("recorded_ts", "recorded", "recorded_at", "记录时间", "登记时间")
PROSE_SAMPLE_LINES = 400
CSV_PROBE_ROWS = 50
MIN_PARSE_RATE = 0.90  # plan §7: below 90% the whole source is skipped

# ---------------------------------------------------------------------------
# Lexicon (deterministic, zero-LLM). slug uses "_"; column names use "-".
# Matching is case-insensitive longest-span-first: a longer term subsumes any
# shorter overlapping one (报警解除 wins over 报警, 配方变更 wins over 变更).
# ---------------------------------------------------------------------------
LEXICON = [
    ("ROLL_CHANGE", "换辊", "roll change",
     ["换辊", "换辊筒", "roll change", "roller change"]),
    ("SCREEN_CHANGE", "换网", "screen change",
     ["换网", "screen change", "screen swap"]),
    ("CLEANING", "清洗/清理", "cleaning",
     ["清洗", "清理", "cleaning", "clean up", "cleanup", "cleaned"]),
    ("MAINTENANCE", "检修", "maintenance",
     ["检修", "maintenance", "overhaul"]),
    ("STOP", "停机", "shutdown",
     ["停机", "停车", "shutdown", "shut down", "stopped"]),
    ("STARTUP", "开机", "startup",
     ["开机", "开车", "startup", "start up", "restart"]),
    ("ALARM", "报警", "alarm",
     ["报警", "alarm"]),
    ("ALARM_CLEAR", "报警解除", "alarm clear",
     ["报警解除", "解除报警", "alarm clear", "alarm cleared", "alarm reset"]),
    ("TRIAL_MOLD", "试模", "trial mold",
     ["试模", "trial mold", "mold trial", "trial mould", "mould trial"]),
    ("MOLD_CHANGE", "换模", "mold change",
     ["换模", "mold change", "mould change", "die change",
      "mold changeover", "mould changeover"]),
    ("RECIPE_CHANGE", "配方变更", "recipe change",
     ["配方变更", "配方更改", "recipe change", "recipe changeover", "recipe changed"]),
    ("MATERIAL_SWITCH", "原料切换", "material switch",
     ["原料切换", "换料", "material switch", "material changeover"]),
    ("CHANGEOVER", "变更", "changeover",
     ["变更", "changeover"]),
    ("CALIBRATION", "校准", "calibration",
     ["校准", "标定", "calibration", "calibrated", "calibrate"]),
    ("COOLDOWN", "降温", "cooldown",
     ["降温", "cooldown", "cool down", "cooled down"]),
    ("HEATUP", "升温", "heatup",
     ["升温", "heatup", "heat up", "heated up"]),
    ("BLOCKAGE", "堵塞", "blockage",
     ["堵塞", "阻塞", "blockage", "blocked", "clog", "clogged", "clogging"]),
    ("FILM_BREAK", "破膜", "film break",
     ["破膜", "破泡", "film break", "film rupture", "film broke", "web break"]),
    ("PRODUCT_SWITCH", "成品转产", "product switch",
     ["成品转产", "转产", "product switch", "product changeover", "grade change"]),
]
_COMPILED_LEXICON = [
    (slug, cn, en, [t.lower() for t in terms]) for slug, cn, en, terms in LEXICON
]
_LEX_BY_SLUG = {slug: {"cn": cn, "en": en} for slug, cn, en, _ in _COMPILED_LEXICON}

# ---------------------------------------------------------------------------
# Line-level timestamp scanning
# ---------------------------------------------------------------------------
_TS_PATTERNS = [
    # year-first ISO-ish (dash / slash / dot), optional time
    re.compile(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?"),
    # Chinese year-month-day, optional time
    re.compile(r"\d{4}年\d{1,2}月\d{1,2}日(?:\s*\d{1,2}:\d{2}(?::\d{2})?)?"),
    # day/month-first slash dates, optional time — ambiguity resolved or refused
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?"),
    # compact catalog formats
    re.compile(r"\b\d{8}[-_]\d{6}\b"),
]
_DATE_FIRST_RE = re.compile(
    r"^(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$")


def _resolve_candidate(raw: str):
    """One timestamp candidate -> ("ok", dt, fmt) | ("ambiguous", raw) | ("bad", raw).

    Catalog formats go through time_ingest (its ambiguity flags are honoured);
    day/month-first dates are resolved here ONLY when a >12 field fixes the
    order (or a==b); otherwise they are ambiguous and the caller refuses.
    """
    v = ting.parse_ts(raw)
    if v.ts is not None:
        return ("ok", v.ts, v.fmt)
    if "ambiguous_date_order" in v.flags:
        return ("ambiguous", raw)
    m = _DATE_FIRST_RE.match(raw.strip())
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        hh, mi, ss = int(m.group(4) or 0), int(m.group(5) or 0), int(m.group(6) or 0)
        try:
            if a <= 12 and b <= 12:
                if a == b:
                    return ("ok", datetime(y, a, a, hh, mi, ss), "%d/%m/%Y")
                return ("ambiguous", raw)
            if a > 12:
                return ("ok", datetime(y, b, a, hh, mi, ss), "%d/%m/%Y")
            return ("ok", datetime(y, a, b, hh, mi, ss), "%m/%d/%Y")
        except ValueError:
            return ("bad", raw)
    return ("bad", raw)


def scan_line(text: str) -> dict:
    """Scan one prose line. First determinate candidate anchors the line; any
    ambiguous candidate condemns the whole source; junk candidates are counted
    (they feed the parse-rate rule)."""
    cands = []
    for pat in _TS_PATTERNS:
        for m in pat.finditer(text):
            cands.append((m.start(), m.group(0)))
    cands.sort()
    out = {"dt": None, "fmt": None, "tz_original": None, "ambiguous": False,
           "ambiguous_example": None, "n_candidates": len(cands), "n_unparsed": 0}
    for _, raw in cands:
        kind, *rest = _resolve_candidate(raw)
        if kind == "ok":
            if out["dt"] is None:
                out["dt"], out["fmt"] = rest[0], rest[1]
                v = ting.parse_ts(raw)
                if v.tz_original:
                    out["tz_original"] = v.tz_original
        elif kind == "ambiguous":
            out["ambiguous"] = True
            out["ambiguous_example"] = raw
            break
        else:
            out["n_unparsed"] += 1
    return out


# ---------------------------------------------------------------------------
# Lexicon matching
# ---------------------------------------------------------------------------
def match_tags(text: str) -> list[dict]:
    """Deterministic lexicon hits, longest-span-first with overlap suppression."""
    low = text.lower()
    hits = []
    for slug, cn, en, terms in _COMPILED_LEXICON:
        for term in terms:
            start = 0
            while True:
                i = low.find(term, start)
                if i < 0:
                    break
                hits.append({"start": i, "end": i + len(term), "slug": slug,
                             "cn": cn, "en": en, "term": term})
                start = i + 1
    hits.sort(key=lambda h: (-(h["end"] - h["start"]), h["start"], h["slug"]))
    accepted, taken = [], []
    for h in hits:
        if any(h["start"] < e and s < h["end"] for s, e in taken):
            continue
        accepted.append(h)
        taken.append((h["start"], h["end"]))
    accepted.sort(key=lambda h: h["start"])
    return [{"tag": h["cn"], "tag_slug": h["slug"], "method": "lexicon",
             "matched_term": h["term"], "model_derived": False} for h in accepted]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _cfg(ctx) -> dict:
    cfg = getattr(ctx, "config", None)
    return cfg if isinstance(cfg, dict) else {}


def _shift(dt: datetime) -> str:
    """A=[08:00,16:00) B=[16:00,24:00) C=[00:00,08:00) — handover-hour strata."""
    if 8 <= dt.hour < 16:
        return "A"
    if dt.hour >= 16:
        return "B"
    return "C"


_SHIFT_ID = {"A": 1, "B": 2, "C": 3}


def _hour_of_day(dt: datetime) -> float:
    return dt.hour + dt.minute / 60.0 + dt.second / 3600.0


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _clean(v) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return ""
    return str(v).strip()


def _base_spec(p: Path, taken: dict, kind: str, meta: dict) -> dict:
    slug, sha6 = naming.unique_slug(p.stem, p, taken)
    return {"source_id": f"text-{slug.lower()}", "path": p, "slug": slug,
            "path_sha6": sha6, "kind": kind, "shape": SHAPE, "meta": meta}


def _probe_rows(p: Path, limit: int) -> list[list[str]]:
    try:
        with open(p, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
            return list(csv.reader(f))[:limit]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# detect
# ---------------------------------------------------------------------------
def _detect_csv(p: Path, taken: dict) -> dict | None:
    """CSV remarks table: long-text column (share >= 0.5, NOT time-like) +
    parseable time column (probe rate >= 0.5) + >= 2 data rows. A datetime
    column also satisfies the probe's long-cell heuristic, so text-column
    candidates are filtered by parse rate first."""
    rows = _probe_rows(p, CSV_PROBE_ROWS)
    if len(rows) < 3:  # header + >= 2 data rows
        return None
    header = rows[0]
    data = rows[1:]
    rates = {}
    for ci, name in enumerate(header):
        rates[name] = ting.parse_series([r[ci] if ci < len(r) else "" for r in data])["ok_rate"]
    text_col, share = next(((n, sh) for n, sh in
                            disc.probe_csv_text_column(p, max_rows=CSV_PROBE_ROWS)
                            if sh >= 0.5 and rates.get(n, 1.0) < 0.5), (None, 0.0))
    if text_col is None:
        return None
    best_name, best_rate = None, 0.0
    for name in header:
        if name == text_col:
            continue
        if rates[name] > best_rate:
            best_name, best_rate = name, rates[name]
    if best_name is None or best_rate < 0.5:
        return None
    return _base_spec(p, taken, "csv_notes",
                      {"text_col": text_col, "time_col": best_name,
                       "probe_rows": len(data)})


def _detect_prose(p: Path, taken: dict) -> dict | None:
    """Prose log: >= 2 sampled lines carry a timestamp candidate."""
    n_cand = 0
    try:
        with open(p, "r", encoding="utf-8-sig", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= PROSE_SAMPLE_LINES:
                    break
                if scan_line(line)["n_candidates"] > 0:
                    n_cand += 1
    except Exception:
        return None
    if n_cand < 2:
        return None
    return _base_spec(p, taken, "prose", {"candidate_lines": n_cand})


def detect(candidates, ctx) -> list[dict]:
    """I9 detect — claims only metadata, never parses whole files."""
    taken: dict[str, str] = {}
    claimed: list[dict] = []
    for c in candidates:
        p = Path(c)
        ext = p.suffix.lower()
        try:
            spec = None
            if ext in CSV_EXTS:
                spec = _detect_csv(p, taken)
            elif ext == ".txt":  # ambiguous extension: notes table first, prose second
                spec = _detect_csv(p, taken) or _detect_prose(p, taken)
            elif ext in PROSE_EXTS:
                spec = _detect_prose(p, taken)
        except Exception:
            spec = None
        if spec is not None:
            claimed.append({"shape": SHAPE, "spec": spec})
    return claimed


# ---------------------------------------------------------------------------
# extract — result assembly
# ---------------------------------------------------------------------------
def _skipped(spec, fmt_label: str, reason: str, extra: dict | None = None) -> dict:
    p = Path(spec["path"])
    src = {"source_id": spec["source_id"], "path": str(p),
           "path_sha6": spec["path_sha6"], "slug": spec["slug"], "shape": SHAPE,
           "format": fmt_label, "n_snapshots": 0, "cadence_s": None, "span_s": None,
           "ts_format": None, "ts_source": TS_SOURCE, "tz": None,
           "duplicate_key_policy": "keep_all", "anchor_coverage": None,
           "effective_n": 0, "sparse": True, "stats_eligible": False,
           "disposition": "skipped", "reason": reason, "features": [],
           "objects_dir": None}
    if extra:
        src.update(extra)
    return {"source": src, "rows": None, "columns": [], "contract": [],
            "contract_rows": [], "annotations": [], "objects": [],
            "notes": [reason]}


def _evt_contract_row(colname: str, spec, sha: str, tag: dict, window: int,
                      n_hits: int, coverage: float, first_ts, last_ts, tz: str) -> dict:
    return {
        "column": colname, "shape": "TXT", "source_id": spec["source_id"],
        "source_path": str(spec["path"]), "source_sha256": sha, "unit": "0/1",
        "role": "metadata",
        "physical_meaning": (
            f"时间锚定事件窗标志：t 时刻值=1 表示该源在 [t-{window}s, t] 内记录过一次"
            f"「{tag['cn']}」({tag['en']})；窗口只向前过期（forward-only），"
            f"由对齐层按 evt_window_s 实施，绝不向未来泄漏"),
        "formula": (f"1 if any {tag['slug']} annotation has event_ts in "
                    f"[t - evt_window_s, t] else 0; evt_window_s={window}"),
        "physics_basis": (
            "换辊/清洗/停机/报警等操作事件直接改变产线状态，是其后时序变化的候选原因；"
            "前向窗口保证因果方向（事件先于被解释的过程变化）"),
        "evidence_level": 2,
        "evidence_level_basis": "L2 用户文档：操作员备注/交接班/维护日志的文字记录，时间由记录者给出",
        "method": "lexicon_event_window", "method_version": CONTRACT_VERSION,
        "n_inputs": n_hits, "coverage": round(coverage, 6), "effective_n": n_hits,
        "sparse": True, "stats_eligible": False, "cadence_s": None,
        "ts_source": TS_SOURCE, "tz": tz, "clock_offset_s": 0.0,
        "tag_cn": tag["cn"], "tag_en": tag["en"], "model_derived": False,
        "evt_window_s": window,
        "_src_ts": "= ts (an annotation row is stamped with its own event time)",
        "insufficient_data": False, "first_ts": first_ts, "last_ts": last_ts,
    }


def _cov_contract_row(colname: str, spec, sha: str, feature: str, n_rows: int,
                      tz: str, first_ts, last_ts) -> dict:
    if feature == "HOUR-OF-DAY":
        unit, meaning, formula = "h", (
            "时刻协变量：事件发生的当日至小数小时（0-24）。"
            "班次/时刻协变量——交接班整点混杂的显式对照项"), (
            "hour + minute/60 + second/3600 from event_ts")
    else:
        unit, meaning, formula = "id", (
            "班次桶协变量：A[08:00,16:00)→1, B[16:00,24:00)→2, C[00:00,08:00)→3。"
            "班次/时刻协变量——交接班整点混杂的显式对照项"), (
            "shift_bucket(event_ts): A->1, B->2, C->3")
    return {
        "column": colname, "shape": "TXT", "source_id": spec["source_id"],
        "source_path": str(spec["path"]), "source_sha256": sha,
        "unit": unit, "role": "metadata", "physical_meaning": meaning,
        "formula": formula,
        "physics_basis": (
            "交接班与昼夜班次惯例使事件时刻与工艺状态/人员行为系统相关，"
            "作为协变量显式对照交接班整点混杂"),
        "evidence_level": 2,
        "evidence_level_basis": "L2 用户文档：由事件记录的时间戳确定性换算（不引入外部信息）",
        "method": "clock_covariate", "method_version": CONTRACT_VERSION,
        "n_inputs": n_rows, "coverage": 1.0, "effective_n": n_rows,
        "sparse": False, "stats_eligible": False, "cadence_s": None,
        "ts_source": TS_SOURCE, "tz": tz, "clock_offset_s": 0.0,
        "tag_cn": "时刻协变量" if feature == "HOUR-OF-DAY" else "班次桶",
        "tag_en": "hour-of-day covariate" if feature == "HOUR-OF-DAY" else "shift bucket id",
        "model_derived": False,
        "_src_ts": "= ts (covariate computed from the event's own timestamp)",
        "insufficient_data": False, "first_ts": first_ts, "last_ts": last_ts,
    }


def _featured(spec, fmt_label: str, ts_fmts: list[str], tz: str, rows: pd.DataFrame,
              contract_rows: list[dict], annotations: list[dict], notes: list[str]) -> dict:
    p = Path(spec["path"])
    sha = mani.sha256_file(p) or "sha256:unavailable"
    columns = [c["column"] for c in contract_rows]
    ts_list = [datetime.strptime(v, "%Y-%m-%d %H:%M:%S") for v in rows["ts"]]
    stats = ting.bucket_stats([type("P", (), {"ts": t}) for t in ts_list])
    src = {"source_id": spec["source_id"], "path": str(p),
           "path_sha6": spec["path_sha6"], "slug": spec["slug"], "shape": SHAPE,
           "format": fmt_label, "n_snapshots": int(len(rows)),
           "cadence_s": stats["cadence_s"], "span_s": stats["span_s"],
           "ts_format": "|".join(sorted(set(ts_fmts))) if ts_fmts else None,
           "ts_source": TS_SOURCE, "tz": tz,
           "duplicate_key_policy": "keep_all", "anchor_coverage": None,
           "effective_n": int(len(rows)), "sparse": True, "stats_eligible": False,
           "disposition": "featured", "reason": "", "features": columns,
           "objects_dir": None}
    return {"source": src, "rows": rows, "columns": columns, "contract": contract_rows,
            "contract_rows": contract_rows, "annotations": annotations,
            "objects": [], "notes": notes}


# ---------------------------------------------------------------------------
# extract — CSV remarks table
# ---------------------------------------------------------------------------
def _pick_columns(header: list[str], df: pd.DataFrame, hint: dict):
    """(text_col, time_info|None) over the FULL table. Text col = long-text
    share >= 0.5 among non-time-like columns (parse rate < 0.5); time col =
    highest parse rate among the rest, earliest column wins ties."""
    rates = {name: ting.parse_series(list(df[name]))["ok_rate"] for name in header}
    text_col = hint.get("text_col")
    if (text_col not in header or rates.get(text_col, 1.0) >= 0.5
            or _text_share(df[text_col]) < 0.5):
        cands = [(n, _text_share(df[n])) for n in header
                 if rates[n] < 0.5 and _text_share(df[n]) >= 0.5]
        if not cands:
            return None, None
        text_col = cands[0][0]
    best = None  # (rate, col_index, name, series_info)
    for ci, name in enumerate(header):
        if name == text_col:
            continue
        s = ting.parse_series(list(df[name]))
        if s["ok_rate"] >= 0.5 and (best is None or s["ok_rate"] > best[0]):
            best = (s["ok_rate"], ci, name, s)
    return text_col, best


def _text_share(series) -> float:
    vals = [_clean(v) for v in series]
    if not vals:
        return 0.0
    long_cells = sum(1 for c in vals if len(c) >= 12 and not _looks_numeric(c))
    return long_cells / len(vals)


def _looks_numeric(cell: str) -> bool:
    try:
        float(cell.replace(",", ""))
        return True
    except ValueError:
        return False


def _extract_csv(spec, ctx, window: int) -> dict:
    p = Path(spec["path"])
    df = pd.read_csv(p, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    if len(df) < 2:
        return _skipped(spec, "csv", f"only {len(df)} data row(s) (<2); source skipped", None)
    header = list(df.columns)
    text_col, best = _pick_columns(header, df, spec.get("meta") or {})
    if text_col is None:
        return _skipped(spec, "csv", "no long-text column (share >= 0.5) at extract time", None)
    if best is None:
        return _skipped(spec, "csv", "no time column with parse rate >= 0.5; source skipped", None)
    rate, _, time_col, series = best
    if series["ambiguous"]:
        example = _first_ambiguous_value(df[time_col], series)
        return _skipped(spec, "csv",
                        f"ambiguous_date_order: {series['ambiguous']} time value(s) admit both "
                        f"DD/MM and MM/DD readings (e.g. '{example}'); "
                        f"refusing to guess — whole source skipped", None)
    if rate < MIN_PARSE_RATE:
        return _skipped(spec, "csv",
                        f"time parse rate {rate:.2f} < {MIN_PARSE_RATE:.2f} over column "
                        f"'{time_col}'; whole source skipped", None)
    recorded_col = next((h for h in header if h.strip().lower() in
                         tuple(x.lower() for x in RECORDED_COL_NAMES)
                         and h != text_col and h != time_col), None)
    fmt_label = "csv"
    annotations, unparsed_ts = [], 0
    for i, row in df.iterrows():
        text = _clean(row[text_col])
        if not text:
            continue
        tv = ting.parse_ts(row[time_col])
        if tv.ts is None:
            unparsed_ts += 1
        rec = None
        if recorded_col is not None:
            rec = ting.parse_ts(row[recorded_col]).ts
        dt = tv.ts
        annotations.append({
            "event_ts": _iso(dt) if dt else None,
            "recorded_ts": _iso(rec) if rec else None,
            "text": text,
            "tags": match_tags(text),
            "source_id": spec["source_id"],
            "source_sha256": mani.sha256_file(p) or "sha256:unavailable",
            "line_no": int(i) + 1,
            "hour_of_day": round(_hour_of_day(dt), 6) if dt else None,
            "shift_bucket": _shift(dt) if dt else None,
        })
    ts_fmts = [series["format"]] if series["format"] else []
    return _assemble(spec, ctx, fmt_label, ts_fmts, annotations, unparsed_ts,
                     series["tz_originals"], window)


def _first_ambiguous_value(col, series) -> str:
    for raw, pv in zip(list(col), series["parsed"]):
        if pv.ts is not None and "ambiguous_date_order" in pv.flags:
            return _clean(raw)
    return ""


# ---------------------------------------------------------------------------
# extract — prose log
# ---------------------------------------------------------------------------
def _extract_prose(spec, ctx, window: int) -> dict:
    p = Path(spec["path"])
    lines = p.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    scans = [(i + 1, line, scan_line(line)) for i, line in enumerate(lines)]
    cand = [(ln, line, sc) for ln, line, sc in scans if sc["n_candidates"] > 0]
    fmt_label = p.suffix.lower().lstrip(".") or "txt"
    if len(cand) < 2:
        return _skipped(spec, fmt_label,
                        f"only {len(cand)} line(s) with timestamp candidates (<2); source skipped",
                        None)
    amb = [(ln, sc) for ln, _, sc in cand if sc["ambiguous"]]
    if amb:
        ln, sc = amb[0]
        return _skipped(spec, fmt_label,
                        f"ambiguous_date_order: {len(amb)} line(s) admit both DD/MM and MM/DD "
                        f"readings (line {ln}: '{sc['ambiguous_example']}'); "
                        f"refusing to guess — whole source skipped", None)
    parsed = [(ln, line, sc) for ln, line, sc in cand if sc["dt"] is not None]
    rate = len(parsed) / len(cand)
    if rate < MIN_PARSE_RATE:
        return _skipped(spec, fmt_label,
                        f"time parse rate {rate:.2f} < {MIN_PARSE_RATE:.2f} over "
                        f"{len(cand)} candidate line(s); whole source skipped", None)
    annotations, unparsed_ts = [], 0
    sha = mani.sha256_file(p) or "sha256:unavailable"
    tz_orig: set = set()
    for ln, line, sc in parsed:
        dt, fmt = sc["dt"], sc["fmt"]
        if sc["tz_original"]:
            tz_orig.add(sc["tz_original"])
        unparsed_ts += sc["n_unparsed"]
        annotations.append({
            "event_ts": _iso(dt),
            "recorded_ts": None,
            "text": line.rstrip("\r"),
            "tags": match_tags(line),
            "source_id": spec["source_id"],
            "source_sha256": sha,
            "line_no": ln,
            "hour_of_day": round(_hour_of_day(dt), 6),
            "shift_bucket": _shift(dt),
        })
    return _assemble(spec, ctx, fmt_label, [sc["fmt"] for *_, sc in parsed],
                     annotations, unparsed_ts, tz_orig, window)


# ---------------------------------------------------------------------------
# shared assembly: rows DataFrame + contract rows
# ---------------------------------------------------------------------------
def _assemble(spec, ctx, fmt_label: str, ts_fmts: list[str], annotations: list[dict],
              unparsed_ts: int, tz_orig: set, window: int) -> dict:
    tagged = [a for a in annotations if a["event_ts"] is not None]
    if not tagged:
        return _skipped(spec, fmt_label,
                        "no parseable event timestamps after extraction; source skipped", None)
    tagged_sorted = sorted(tagged, key=lambda a: a["event_ts"])  # stable: doc order on ties

    tag_order, tag_meta = [], {}
    for a in tagged:
        for t in a["tags"]:
            slug = t["tag_slug"]
            if slug not in tag_meta:
                lex = _LEX_BY_SLUG.get(slug, {"cn": t.get("tag", slug), "en": slug})
                tag_meta[slug] = {"slug": slug, "cn": lex["cn"], "en": lex["en"]}
                tag_order.append(slug)
    evt_cols = {slug: naming.feature_column("text", spec["slug"], "EVT-" + slug.replace("_", "-"))
                for slug in tag_order}
    hour_col = naming.feature_column("text", spec["slug"], "HOUR-OF-DAY")
    shift_col = naming.feature_column("text", spec["slug"], "SHIFT-BUCKET-ID")

    records = []
    for a in tagged_sorted:
        rec = {"ts": a["event_ts"], "_src_ts": a["event_ts"], "n_inputs": 1}
        hits = {t["tag_slug"] for t in a["tags"]}
        for slug in tag_order:
            rec[evt_cols[slug]] = 1 if slug in hits else 0
        rec[hour_col] = a["hour_of_day"]
        rec[shift_col] = _SHIFT_ID[a["shift_bucket"]]
        records.append(rec)
    rows = pd.DataFrame(records, columns=["ts", "_src_ts", "n_inputs"]
                        + [evt_cols[s] for s in tag_order] + [hour_col, shift_col])

    sha = tagged[0]["source_sha256"]
    tz = ";".join(sorted(tz_orig)) if tz_orig else "anchor_local"
    n = len(rows)
    contract_rows = []
    for slug in tag_order:
        hits = sum(1 for a in tagged if any(t["tag_slug"] == slug for t in a["tags"]))
        firsts = [a["event_ts"] for a in tagged if any(t["tag_slug"] == slug for t in a["tags"])]
        contract_rows.append(_evt_contract_row(
            evt_cols[slug], spec, sha, tag_meta[slug], window, hits, hits / n,
            firsts[0], firsts[-1], tz))
    contract_rows.append(_cov_contract_row(hour_col, spec, sha, "HOUR-OF-DAY", n, tz,
                                           tagged_sorted[0]["event_ts"], tagged_sorted[-1]["event_ts"]))
    contract_rows.append(_cov_contract_row(shift_col, spec, sha, "SHIFT-BUCKET-ID", n, tz,
                                           tagged_sorted[0]["event_ts"], tagged_sorted[-1]["event_ts"]))

    notes = [f"annotations={len(annotations)} events={n} unparsed_ts={unparsed_ts} "
             f"tags={len(tag_order)} evt_window_s={window} (window applied forward-only by the align layer)"]
    return _featured(spec, fmt_label, ts_fmts, tz, rows, contract_rows, annotations, notes)


# ---------------------------------------------------------------------------
# I9 entry point
# ---------------------------------------------------------------------------
def extract(spec, ctx) -> dict:
    """I9 extract — one TXT source -> ShapeResult dict.

    build.py consumes: result["source"], result["rows"], result["contract"],
    result["annotations"], result["objects"]; "columns"/"contract_rows"/"notes"
    are carried for direct consumers and debugging."""
    window = int(_cfg(ctx).get("event_window_s", 3600))
    kind = spec.get("kind", "prose")
    try:
        if kind == "csv_notes":
            return _extract_csv(spec, ctx, window)
        return _extract_prose(spec, ctx, window)
    except Exception as exc:  # never crash the orchestrator: skip with reason
        return _skipped(spec, "text", f"extract failed: {exc}", None)
