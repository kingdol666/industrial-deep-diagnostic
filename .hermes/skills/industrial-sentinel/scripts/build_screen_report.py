# -*- coding: utf-8 -*-
"""Build the self-contained HTML quick-screen report from sentinel outputs.

Deterministic (zero LLM, zero network): reads `<run-dir>/sentinel/alert.json`
(sentinel-alert/1.0) plus the screened window CSV, and writes
`<run-dir>/sentinel/quick_screen_report.html` — a self-contained Chinese
page (inline SVG sparklines, no external JS/CDN) so the report is viewable
in the web console and offline.

Usage:
  python build_screen_report.py --run-dir <dir> [--out <file>] [--data <window.csv>]

Exit codes: 0 ok | 1 report written with alerts | 2 not renderable
(no alert.json / no data file) | 3 input error.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_SPARK_POINTS = 240
SEVERITY_ORDER = {"critical": 0, "high": 1, "warn": 2, "info": 3}


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent and not (p / ".git").exists():
        p = p.parent
    return p


def _contained(path: Path) -> Path:
    if ".." in path.parts:
        raise ValueError(f"path must not contain '..': {path}")
    resolved = path.resolve()
    root = _repo_root()
    if root not in resolved.parents:
        raise ValueError(f"path outside repo: {resolved}")
    return resolved


def _load_alert(run_dir: Path) -> dict:
    for cand in (run_dir / "sentinel" / "alert.json", run_dir / "alert.json"):
        if cand.is_file():
            with open(cand, encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("sentinel alert.json not found under run dir")


def _find_window_csv(run_dir: Path, alert: dict, explicit: str | None) -> Path | None:
    if explicit:
        p = _contained(run_dir / explicit) if not Path(explicit).is_absolute() else Path(explicit)
        return p if p.is_file() else None
    source = alert.get("source") or {}
    for key in ("data", "path", "window"):
        v = source.get(key) if isinstance(source, dict) else None
        if isinstance(v, str) and v:
            p = Path(v)
            if not p.is_absolute():
                p = _contained(run_dir / v)
            if p.is_file():
                return p
    # last resort: first CSV/TSV in 00_input
    inp = run_dir / "00_input"
    if inp.is_dir():
        for f in sorted(inp.iterdir()):
            if f.suffix.lower() in (".csv", ".tsv"):
                return f
    return None


def _read_series(csv_path: Path, columns: list[str]) -> dict[str, list[float | None]]:
    """Read the alerted columns (downsampled to <=MAX_SPARK_POINTS points)."""
    series: dict[str, list[float | None]] = {}
    if csv_path is None:
        return series
    delim = "\t" if csv_path.suffix.lower() == ".tsv" else ","
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=delim)
        rows = list(reader)
    if len(rows) > MAX_SPARK_POINTS:
        stride = -(-len(rows) // MAX_SPARK_POINTS)
        rows = rows[::stride]
    for col in columns:
        vals: list[float | None] = []
        for r in rows:
            raw = (r.get(col) or "").strip()
            try:
                vals.append(float(raw))
            except ValueError:
                vals.append(None)
        series[col] = vals
    return series


def _sparkline(vals: list[float | None], bad_idx: set[int], width: int = 560,
               height: int = 90) -> str:
    pts = [v for v in vals if v is not None]
    if len(pts) < 2:
        return ""
    lo, hi = min(pts), max(pts)
    span = (hi - lo) or 1.0
    n = len(vals)
    step_x = width / max(n - 1, 1)

    def xy(i: int, v: float) -> tuple[float, float]:
        return round(i * step_x, 1), round(height - 8 - (v - lo) / span * (height - 16), 1)

    polyline, dots = [], []
    prev: tuple[float, float] | None = None
    for i, v in enumerate(vals):
        if v is None:
            prev = None
            continue
        x, y = xy(i, v)
        if prev is not None:
            polyline.append(f"M{prev[0]},{prev[1]} L{x},{y}")
        prev = (x, y)
        if i in bad_idx:
            dots.append(f'<circle cx="{x}" cy="{y}" r="3.2" fill="#d9534f"/>')
    line = "".join(
        f'<path d="{d}" fill="none" stroke="#2b6cb0" stroke-width="1.4"/>'
        for d in polyline
    )
    return (f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
            f'role="img">{line}{"".join(dots)}</svg>')


def _esc(v) -> str:
    return html.escape("—" if v is None else str(v))


def _ontology_section(ont) -> str:
    """'本体理解' section from the alert's optional top-level ontology block.

    Absent block -> empty string (backward compatible). Zero-JS: a plain unit
    table plus honest window-source / rag_used lines; columns missing from the
    units map read as 单位未声明 (declared-window alerts are capped at warn).
    """
    if not isinstance(ont, dict) or not ont:
        return ""
    units = ont.get("units") or {}
    roles = ont.get("roles") or {}
    unit_rows = "".join(
        f"<tr><td>{_esc(col)}</td><td>{_esc(roles.get(col, '—'))}</td>"
        f"<td class='num'>{_esc(unit)}</td></tr>"
        for col, unit in sorted(units.items()))
    unit_table = (
        "<table><thead><tr><th>列</th><th>角色</th><th>单位（本体声明）</th></tr></thead>"
        f"<tbody>{unit_rows}</tbody></table>"
        "<p class='meta'>未列出的列 = 单位未声明（unit undeclared）。</p>"
        if unit_rows else
        "<p class='ok'>本体未声明任何单位——所有列一律视为“单位未声明”。</p>")
    try:
        n_windows = int(ont.get("declared_window_count") or 0)
    except (TypeError, ValueError):
        n_windows = 0
    window_line = (
        f"本体声明窗口 {n_windows} 个（window_source=ontology_declared，"
        "未经 DOE 验证；越界/触界告警一律封顶 warn）。"
        if n_windows else
        "本体未声明操作窗口（C2 仅在基线含窗口时启用）。")
    rag_used = bool(ont.get("rag_used"))
    rag_line = (f"rag_used={str(rag_used).lower()}（如实标注；确定性制备路径为 false，"
                "本数值取自本体 provenance）。")
    return (
        "<h2>本体理解</h2>"
        f"<p class='meta'>场景：{_esc(ont.get('scene') or '—')} · "
        f"来源：{_esc(ont.get('source_path') or '—')}</p>"
        f"{unit_table}"
        f"<p>{_esc(window_line)}</p>"
        f"<p>{_esc(rag_line)}</p>")


def build_html(alert: dict, series: dict[str, list[float | None]],
               bad_by_param: dict[str, set[int]], generated_at: str) -> str:
    status = alert.get("status", "ok")
    alerts = sorted(alert.get("alerts", []),
                    key=lambda a: SEVERITY_ORDER.get(a.get("severity", "info"), 9))
    checks = alert.get("checks_summary", {})
    spc = checks.get("spc", {})
    rows_html = []
    seen_params: list[str] = []
    for a in alerts:
        param = a.get("parameter") or a.get("indicator") or "?"
        if param not in seen_params:
            seen_params.append(param)
        sev = a.get("severity", "info")
        obs = a.get("observed", {})
        thr = a.get("threshold", {})
        rows_html.append(
            f"<tr><td><span class='badge {sev}'>{_esc(sev)}</span></td>"
            f"<td>{_esc(a.get('rule_name', ''))}</td>"
            f"<td>{_esc(param)}</td>"
            f"<td>{_esc(obs.get('index', '—'))}</td>"
            f"<td class='num'>{_esc(obs.get('value', '—'))}</td>"
            f"<td class='num'>{_esc(thr.get('bound', '—'))}</td>"
            f"<td>{_esc(a.get('suggested_check', ''))}</td></tr>")
    alerts_table = ("<table><thead><tr><th>级别</th><th>规则</th><th>参数</th>"
                    "<th>位置(行)</th><th>观测值</th><th>阈值</th><th>建议核查</th></tr>"
                    "</thead><tbody>" + "".join(rows_html) + "</tbody></table>") \
        if rows_html else "<p class='ok'>无告警。</p>"

    spark_html = []
    for param in seen_params:
        vals = series.get(param)
        if not vals:
            continue
        spark = _sparkline(vals, bad_by_param.get(param, set()))
        if spark:
            spark_html.append(f"<h3>{_esc(param)}</h3>{spark}")
    spark_section = ("<h2>参数趋势（红点=判异位置）</h2>" + "".join(spark_html)) \
        if spark_html else ""

    skipped = checks.get("checks_skipped") or []
    skip_lines = "".join(
        f"<li>{_esc(s.get('check', ''))} — {_esc(s.get('reason', ''))}</li>" for s in skipped)
    skipped_section = ("<h2>降级项（如实披露）</h2><ul>" + skip_lines + "</ul>") \
        if skip_lines else ""

    ontology_section = _ontology_section(alert.get("ontology"))

    return f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<title>产线快筛报告 — {_esc(alert.get('alert_id', ''))}</title>
<style>
body{{font-family:"Microsoft YaHei",system-ui,sans-serif;margin:24px;color:#1a202c}}
h1{{font-size:22px;border-bottom:2px solid #2b6cb0;padding-bottom:8px}}
h2{{font-size:17px;margin-top:28px}} h3{{font-size:14px;margin:14px 0 4px}}
.badge{{padding:2px 8px;border-radius:10px;color:#fff;font-size:12px}}
.badge.high{{background:#c53030}}.badge.critical{{background:#7b1010}}
.badge.warn{{background:#b7791f}}.badge.info{{background:#2f855a}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin-top:8px}}
th,td{{border:1px solid #cbd5e0;padding:6px 8px;text-align:left}}
th{{background:#edf2f7}} td.num{{text-align:right;font-variant-numeric:tabular-nums}}
.cards{{display:flex;gap:14px;margin:14px 0}}
.card{{border:1px solid #cbd5e0;border-radius:8px;padding:10px 16px;min-width:130px}}
.card b{{display:block;font-size:22px}} .ok{{color:#2f855a}}
.meta{{color:#4a5568;font-size:12px}}
footer{{margin-top:30px;padding-top:10px;border-top:1px solid #cbd5e0;
color:#4a5568;font-size:12px}}
</style></head><body>
<h1>产线数据快筛报告（industrial-sentinel）</h1>
<p class="meta">alert_id: {_esc(alert.get('alert_id', '—'))} · 模式: {_esc(alert.get('mode', '—'))} ·
状态: <b>{_esc(status)}</b> · 基线: {_esc((alert.get('baseline') or {}).get('path') or 'self/未知')} ·
生成时间: {_esc(generated_at)}</p>
<div class="cards">
<div class="card"><b>{len(alerts)}</b>告警条数</div>
<div class="card"><b>{_esc(spc.get('n_triggered', 0))}</b>SPC 触发</div>
<div class="card"><b>{_esc(len(seen_params))}</b>涉及参数</div>
</div>
<h2>告警清单</h2>
{alerts_table}
{spark_section}
{ontology_section}
{skipped_section}
<footer>本报告由确定性脚本（build_screen_report.py）从 sentinel/alert.json 与监视窗数据生成，
全部数值可在原始表中复算；仅描述"发生了什么"，不构成任何参数下发指令。</footer>
</body></html>"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="sentinel quick-screen HTML report builder")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--data", default=None, help="window csv path relative to run dir")
    a = ap.parse_args(argv)

    run_dir = _contained(Path(a.run_dir))
    try:
        alert = _load_alert(run_dir)
    except FileNotFoundError as exc:
        print(f"[quick-screen-html] not renderable: {exc}", file=sys.stderr)
        return 2

    alerts = alert.get("alerts", [])
    bad_by_param: dict[str, set[int]] = {}
    columns: list[str] = []
    for item in alerts:
        param = item.get("parameter")
        idx = (item.get("observed") or {}).get("index")
        if param is None or idx is None:
            continue
        bad_by_param.setdefault(param, set()).add(int(idx))
        if param not in columns:
            columns.append(param)

    csv_path = _find_window_csv(run_dir, alert, a.data)
    series = _read_series(csv_path, columns)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    page = build_html(alert, series, bad_by_param, generated_at)

    out = Path(a.out) if a.out else run_dir / "sentinel" / "quick_screen_report.html"
    out = _contained(out if out.is_absolute() else run_dir / out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"[quick-screen-html] wrote {out} ({len(page)} bytes, "
          f"{len(alerts)} alerts, {len(series)} sparklines)")
    return 1 if alerts else 0


if __name__ == "__main__":
    raise SystemExit(main())
