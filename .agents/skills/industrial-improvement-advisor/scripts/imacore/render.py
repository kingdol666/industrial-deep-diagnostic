"""imacore.render — single-source advisory rendering (HTML + Markdown).

Visual authority: the IDD report design system (`.claude/shared/report-design/
report.css`) — evidence-ledger skeleton: left chapter rail, numbered sections,
three-column body with margin notes, seal-style score/grade, hairline rules,
serif headings + sans body + mono numerals.

Three surfaces consume this module:
  * standalone advisory page      -> render_page()      (full A shell)
  * stability-report / DOE HTML   -> render_section()   (embedded A section)
  * diagnosis step 5c markdown    -> render_markdown()  (chapter.md)

Numbers come verbatim from advisory_actions.json; nothing is recomputed here.
All actions and prescriptions are rendered in full — no truncation: the report
must be as complete as the JSON contract.
"""

import html
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------- design system
SKILL_DIR = Path(__file__).resolve().parents[2]
_HARNESS = SKILL_DIR.parents[1]
_SHARED_DESIGN = _HARNESS.parent / ".claude" / "shared" / "report-design"
if str(_SHARED_DESIGN) not in sys.path:
    sys.path.insert(0, str(_SHARED_DESIGN))
try:
    import report_design  # type: ignore
except Exception:  # pragma: no cover - degraded checkout without shared design
    report_design = None

GRADE = {
    "A": {"label": "可立即执行", "cls": "rpt-g-a"},
    "B": {"label": "需小试验证", "cls": "rpt-g-b"},
    "C": {"label": "仅方向参考", "cls": "rpt-g-c"},
}
STATUS_LABEL = {
    "actionable": "可执行建议",
    "advisory_only": "仅方向参考",
    "not_actionable": "无建议（处方模式）",
}
DIRECTION_LABEL = {"increase": "上调", "decrease": "下调"}


def css_text() -> str:
    if report_design is None:
        return ""
    return report_design.css_text()


def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def fmt(value, digits=4):
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return esc(value)
    if not math.isfinite(v):
        return "—"
    if v == 0:
        return "0"
    av = abs(v)
    if av >= 1000 or av < 0.001:
        return f"{v:.3e}"
    return f"{v:.{digits}g}"


def fmt_ci(ci):
    if not ci or len(ci) < 2 or ci[0] is None or ci[1] is None:
        return "不可估（effect=null）"
    return f"[{fmt(ci[0])}, {fmt(ci[1])}]"


def grade_badge(grade):
    info = GRADE.get(str(grade), {"label": str(grade), "cls": "rpt-g-c"})
    return (f'<span class="rpt-grade {info["cls"]}" '
            f'style="width:26px;height:26px;font-size:13px" '
            f'title="{esc(info["label"])}">{esc(grade)}</span>')


def css_block():
    return f"<style>{css_text()}</style>"


# ------------------------------------------------------------------ svg bits

def _svg_polyline(points, color="#1e3a54", width=560, height=110):
    if not points:
        return '<div class="rpt-empty">无图表数据</div>'
    xs = [p[0] for p in points]
    ys = [p[1] if p[1] is not None else 0.0 for p in points]
    lo, hi = min(ys), max(ys)
    span = hi - lo if hi - lo > 1e-12 else 1.0
    x0, x1 = min(xs), max(xs)
    xspan = x1 - x0 if x1 - x0 > 0 else 1
    parts = []
    for px, py in points:
        X = 10 + (px - x0) / xspan * (width - 20)
        Y = height - 12 - ((py if py is not None else 0.0) - lo) / span * (height - 24)
        parts.append(f"{X:.1f},{Y:.1f}")
    return (f'<svg class="rpt-chart" viewBox="0 0 {width} {height}" width="100%" '
            f'height="{height}" role="img" aria-label="时序曲线">'
            f'<polyline fill="none" stroke="{color}" stroke-width="1.4" '
            f'points="{" ".join(parts)}"/></svg>')


def _svg_dose(bins, slope, width=560, height=180):
    pts = [(b.get("x"), b.get("y")) for b in (bins or [])
           if b.get("x") is not None and b.get("y") is not None]
    if len(pts) < 2:
        return '<div class="rpt-empty">剂量-响应数据不足</div>'
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    xlo, xhi = min(xs), max(xs)
    ylo, yhi = min(ys), max(ys)
    xspan = xhi - xlo if xhi - xlo > 1e-12 else 1.0
    yspan = yhi - ylo if yhi - ylo > 1e-12 else 1.0
    dots = []
    for x, y in pts:
        X = 20 + (x - xlo) / xspan * (width - 40)
        Y = height - 20 - (y - ylo) / yspan * (height - 40)
        dots.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="4" fill="#1e3a54"/>')
    line = ""
    if slope is not None:
        xbar = sum(xs) / len(xs)
        ybar = sum(ys) / len(ys)
        y1 = slope * xlo + (ybar - slope * xbar)
        y2 = slope * xhi + (ybar - slope * xbar)
        Y1 = height - 20 - (y1 - ylo) / yspan * (height - 40)
        Y2 = height - 20 - (y2 - ylo) / yspan * (height - 40)
        line = (f'<line x1="20" y1="{Y1:.1f}" x2="{width - 20}" y2="{Y2:.1f}" '
                f'stroke="#c2673a" stroke-width="1.6" stroke-dasharray="5 3"/>')
    return (f'<svg class="rpt-chart" viewBox="0 0 {width} {height}" width="100%" '
            f'height="{height}" role="img" aria-label="剂量-响应分箱图">'
            f'{line}{"".join(dots)}</svg>')


# ------------------------------------------------------------------ fragments

def _goal_block(report):
    goal = report.get("goal") or {}
    inferred = goal.get("mode") == "inferred"
    targets = "".join(
        f"<tr><td class='rpt-strong'>{esc(t.get('metric'))}</td>"
        f"<td>{esc(t.get('direction'))}</td>"
        f"<td class='rpt-n'>{fmt(t.get('target_value'))}</td>"
        f"<td class='rpt-n'>{fmt(t.get('tolerance'))}</td></tr>"
        for t in (goal.get("targets") or []))
    note = ('<div class="rpt-note" style="color:#8a5a34"><b>目标为系统推断</b>：由数据按'
            '「偏离度 × 传导强度 × 数据充分度」确定性推断；未确认前全部建议封顶 B 级。'
            '显式声明 objective.json 重跑即可解锁 A 级路径。</div>' if inferred else
            '<div class="rpt-note"><b>显式目标</b>：来自 objective.json，不触发'
            '「未确认目标封顶 B」条款。</div>')
    conflicts = goal.get("conflicts") or []
    conflict_html = ""
    if conflicts:
        items = "".join(
            f"<li>杠杆 <span class='rpt-strong'>{esc(c.get('lever'))}</span>："
            f"{esc(c.get('target_a'))} 要求 {esc(c.get('direction_a'))} vs "
            f"{esc(c.get('target_b'))} 要求 {esc(c.get('direction_b'))} —— 需人工裁决，"
            f"本报告不隐式加权合成</li>" for c in conflicts)
        conflict_html = (f'<div class="rpt-note" style="color:#8a5a34">'
                         f'<b>目标冲突声明</b><ul style="margin:6px 0 0 16px;">{items}</ul></div>')
    water = report.get("waterline") or {}
    factors = water.get("factors") or {}
    labels = {
        "attribution_available": "动作日志归因",
        "mechanism_edges": "本体机制边",
        "dead_time_provided": "dead_time 声明",
        "designed_window_available": "设计试验窗",
        "objective_confirmed": "目标已确认",
    }
    f_rows = ""
    for key, label in labels.items():
        val = factors.get(key)
        if isinstance(val, bool):
            ok, shown = val, ("可用" if val else "缺失")
        else:
            ok = bool(val)
            shown = f"{val} 条" if key == "mechanism_edges" else str(val)
        f_rows += (f'<li><i class="{"is-no" if not ok else ""}">{"✓" if ok else "○"}</i>'
                   f'{label}<span>{esc(shown)}</span></li>')
    raw_grade = water.get("max_achievable_grade")
    blank = raw_grade in (None, "", "none")
    grade = "—" if blank else str(raw_grade)
    grade_label = ("证据不足以评级" if blank else
                   {"A": "可立即执行", "B": "需小试验证",
                    "C": "仅方向参考"}.get(raw_grade, str(raw_grade)))
    return f"""
<div class="rpt-grid-2">
  <div>
    <h3 class="rpt-h3">优化目标</h3>
    <div class="rpt-panel">
      {note}
      <table class="rpt-table"><tr><th>KPI</th><th>方向</th><th>目标值</th><th>容差</th></tr>
      {targets or '<tr><td colspan=4 class="rpt-empty">无显式目标</td></tr>'}</table>
      {conflict_html}
    </div>
  </div>
  <div>
    <h3 class="rpt-h3">证据水位线 · 本次最高可达 {esc(grade)}</h3>
    <div class="rpt-wl">
      <div class="rpt-wl-top"><span class="rpt-wl-grade">{esc(grade)}</span>
        <span style="font-size:12px;color:var(--muted)">{esc(grade_label)}</span></div>
      <ul>{f_rows}</ul>
      <p class="rpt-note">{esc(water.get("note"))}</p>
    </div>
  </div>
</div>"""


GRADE_RANK = {"A": 0, "B": 1, "C": 2}


def _sorted_actions(report):
    """A→B→C, then priority desc. Grade order is the contract, not gain size."""
    acts = report.get("actions") or []
    return sorted(acts, key=lambda a: (GRADE_RANK.get(a.get("grade"), 9),
                                       -(a.get("priority_score") or 0)))


def _roadmap(report):
    actions = _sorted_actions(report)
    if actions:
        max_score = max((a.get("priority_score") or 0.0 for a in actions), default=1.0) or 1.0
        rows = []
        for a in actions:
            score = a.get("priority_score") or 0.0
            pct = max(4.0, min(100.0, score / max_score * 100.0))
            gain = a.get("expected_gain") or {}
            rows.append(
                f"<tr><td>{grade_badge(a.get('grade'))}</td>"
                f"<td class='rpt-strong'>{esc(a.get('lever_param'))}"
                f"<div class='rpt-note' style='margin:0'>{esc(a.get('lever_column'))}</div></td>"
                f"<td>{esc(DIRECTION_LABEL.get(a.get('direction'), a.get('direction')))}"
                f" → {esc(gain.get('metric'))}</td>"
                f"<td class='rpt-n'>{fmt(gain.get('point'))}</td>"
                f"<td class='rpt-n'>{fmt_ci(gain.get('ci95'))}</td>"
                f"<td><div class='rpt-bar'><span style='width:{pct:.1f}%'></span></div></td></tr>")
        table = ("<div class='rpt-table-wrap'><table class='rpt-table'><tr><th>级别</th>"
                 "<th>杠杆</th><th>方向 → KPI</th><th>预期收益</th><th>95%CI</th>"
                 "<th>优先级</th></tr>" + "".join(rows) + "</table></div>")
    elif report.get("prescriptions"):
        table = ('<div class="rpt-note"><b>本次没有建议进入建议区</b>——数据撑不起可执行行动，'
                 '系统给出的是可执行的处方（见下）。</div>')
    else:
        table = '<div class="rpt-empty">无建议</div>'
    return table


def _prescriptions(report):
    pres = report.get("prescriptions") or []
    if not pres:
        return ('<div class="rpt-empty">无处方：所有进入评估的杠杆均已获得分级判定。</div>')
    items = "".join(
        f'<li><span class="rpt-kind">[{esc(p.get("kind"))}]</span>'
        f'<span>{esc(p.get("detail"))}<span class="rpt-addr">addresses: '
        f'{esc(" ; ".join(p.get("addresses") or []))}</span></span></li>' for p in pres)
    return (f'<div class="rpt-presc" style="margin-top:0;border-top:none;padding-top:0">'
            f'<h3>处方清单（{len(pres)} 条 · 全部展示）</h3><ol>{items}</ol>'
            f'<p class="rpt-note">处方是「接下来该补什么」的清单，不是参数指令。</p></div>')


def _card(a):
    gain = a.get("expected_gain") or {}
    mag = a.get("magnitude") or {}
    refs = a.get("evidence_refs") or []
    affected = "".join(
        f"<li>{esc(x.get('metric'))}：{esc(x.get('direction'))}"
        f"{'（显著）' if x.get('significant') else ''}</li>"
        for x in (a.get("affected_kpis") or [])) or "<li>无显著联动</li>"
    mech = "".join(
        f"<li>{esc(step.get('step'))} "
        f"<span class='rpt-mono'>{esc(step.get('ontology_ref'))}</span></li>"
        for step in (a.get("mechanism_chain") or []))
    pres = "".join(f"<li>{esc(x)}</li>" for x in (a.get("preconditions") or []))
    risk = "".join(f"<li>{esc(x)}</li>"
                   for x in ((a.get("risk") or {}).get("assumptions") or []))
    reasons = "".join(f"<li>{esc(x)}</li>" for x in (a.get("grade_reasons") or []))
    ref_rows = "".join(
        f"<tr><td>{esc(r.get('type'))}</td><td class='rpt-mono'>{esc(r.get('source_file'))}</td>"
        f"<td class='rpt-mono'>{esc(r.get('finding_id'))}</td></tr>" for r in refs)
    interp = a.get("interpretation")
    interp_html = ""
    if isinstance(interp, dict) and interp.get("text"):
        interp_html = (f'<div class="rpt-note"><b>解读</b>（{esc(interp.get("authored_by"))}）'
                       f'<p style="margin:4px 0 0;">{esc(interp.get("text"))}</p></div>')
    verify = a.get("verification_plan") or {}
    grade = str(a.get("grade") or "")
    info = GRADE.get(grade, {"label": grade, "cls": "rpt-g-c"})
    return f"""
<article class="rpt-entry">
  <div><div class="rpt-grade {info["cls"]}">{esc(grade)}</div>
    <div class="rpt-grade-cap">{esc(info["label"])}</div></div>
  <div>
    <div class="rpt-entry-head">
      <span class="rpt-lever">{esc(a.get("lever_param"))}
        <code>{esc(a.get("lever_column"))} · {esc(a.get("action_id"))}</code></span>
      <span class="rpt-arrow">→</span><b>{esc(gain.get("metric"))}</b>
    </div>
    <div class="rpt-entry-gain">
      <span class="rpt-gain-num">{fmt(gain.get("point"))}
        <small>预期收益（{esc(gain.get("method"))}）</small></span>
      <span class="rpt-gain-ci">95%CI {fmt_ci(gain.get("ci95"))}</span>
    </div>
    <dl>
      <dt>动作</dt><dd>{esc(DIRECTION_LABEL.get(a.get("direction"), a.get("direction")))}：
        {fmt(mag.get("from"))} → {fmt(mag.get("to"))}
        <span class="rpt-note">（Δ {fmt(mag.get("delta"))} {esc(mag.get("unit") or "单位未声明")}）</span></dd>
      <dt>机理</dt><dd>{esc(a.get("mechanism_status"))}</dd>
      <dt>前提条件</dt><dd><ul>{pres}</ul></dd>
      <dt>联动影响</dt><dd><ul>{affected}</ul></dd>
      <dt>风险假设</dt><dd><ul>{risk}</ul></dd>
      <dt>验证方案</dt><dd>{esc(verify.get('metric'))} · 窗 {esc(verify.get('window'))} ·
        阈值 {esc(verify.get('threshold'))}</dd>
      <dt>回滚条件</dt><dd>{esc(a.get("rollback_condition"))}</dd>
    </dl>
    <details class="rpt-details"><summary>物理机理链（{len(mech)} 环）</summary><ol>{mech}</ol></details>
    <details class="rpt-details"><summary>分级理由（{len(reasons)} 条）</summary><ol>{reasons}</ol></details>
    <details class="rpt-details"><summary>证据引用（{len(refs)} 条）</summary>
      <table class="rpt-table"><tr><th>类型</th><th>来源工件</th><th>finding</th></tr>
      {ref_rows}</table></details>
    {interp_html}
  </div>
</article>"""


def _actions(report):
    acts = _sorted_actions(report)
    if not acts:
        return '<div class="rpt-empty">本次无动作卡（见处方区）。</div>'
    return "".join(_card(a) for a in acts)


def _evidence(report, charts):
    doses = "".join(
        f"<div class='rpt-figure' style='margin:14px 0'><div class='rpt-fig-head'>"
        f"<b>{esc(d.get('lever'))} → {esc(d.get('metric'))}</b>"
        f"<span>slope {fmt(d.get('slope'))} · CI {fmt_ci(d.get('slope_ci95'))}</span></div>"
        f"{_svg_dose(d.get('bins'), d.get('slope'))}</div>"
        for d in (charts.get("dose_response") or []))
    series = "".join(
        f"<div class='rpt-figure' style='margin:14px 0'><div class='rpt-fig-head'>"
        f"<b>{esc(s.get('metric'))} 时序</b>"
        f"<span>n={esc(s.get('n'))} · 方向 {esc(s.get('direction'))}</span></div>"
        f"{_svg_polyline(s.get('points'))}</div>"
        for s in (charts.get("kpi_series") or []))
    return series + doses or '<div class="rpt-empty">无图表数据</div>'


# ------------------------------------------------------------------ surfaces

def render_section(report, *, mode="full", include_style=True,
                   anchor="improvement-advisory", title="改善建议与验证计划",
                   number="03"):
    """Embeddable advisory section (A skeleton, all actions + prescriptions)."""
    charts = report.get("_charts") or {}
    style = css_block() if include_style else ""
    status = report.get("status")
    water = report.get("waterline") or {}
    head = ""
    if title:
        water_grade = water.get("max_achievable_grade")
        water_grade = "—" if water_grade in (None, "", "none") else str(water_grade)
        head = (f'<div class="rpt-sec-head"><span class="rpt-sec-no">{esc(number)}</span>'
                f'<h2>{esc(title)}</h2><div class="rpt-sec-sub">状态 '
                f'{esc(STATUS_LABEL.get(status, status))} · 建议 '
                f'{len(report.get("actions") or [])} 条 · 处方 '
                f'{len(report.get("prescriptions") or [])} 条 · 水位线 '
                f'{esc(water_grade)}</div></div>')
    inner = f"""
  <div id=\"sec-goal\">{_goal_block(report)}</div>
  <div id=\"sec-roadmap\"><h3 class="rpt-h3" style="margin-top:26px">改善路线图</h3>{_roadmap(report)}</div>
  <div id=\"sec-actions\"><h3 class="rpt-h3" style="margin-top:26px">动作卡</h3>{_actions(report)}</div>
  <div id=\"sec-evidence\"><h3 class="rpt-h3" style="margin-top:26px">证据链（剂量-响应与时序）</h3>
    {_evidence(report, charts)}</div>
  <div id=\"sec-prescriptions\"><h3 class="rpt-h3" style="margin-top:26px">处方区（不成建议）</h3>
    {_prescriptions(report)}</div>
  <div class="rpt-foot" style="margin-top:30px"><b>咨询边界：</b>本节为确定性脚本生成的咨询建议
    （advisory），不构成参数下发或控制指令，绝不下发参数；执行须经产线审批 /
    optimizer-campaign 验证。数值与分级不可手改（quality_gate 重算密封）。</div>"""
    if title:
        body = (f'<div class="rpt-body-grid"><div class="rpt-content">{inner}</div>'
                f'<aside class="rpt-margin"><h4>分级口径</h4>'
                f'<p>A ＝ 干预性证据（设计窗 / 随机化 DOE / 归因 CI 不含 0）；'
                f'B ＝ 观察性证据，需小试验证；C ＝ 方向可信但不足以执行。</p>'
                f'<p>收益一律给 95%CI；不可估时写 <code>effect=null</code> 并说明原因，'
                f'不给点估计。</p>'
                f'<p style="color:var(--accent)">本节不构成参数下发指令。</p>'
                f'</aside></div>')
    else:
        body = inner
    return (f'{style}<section class="rpt-scope" id="{esc(anchor)}" '
            f'aria-label="{esc(title or anchor)}">{head}{body}</section>')


def render_markdown(report, *, heading="## 改善建议与验证计划",
                    include_disclaimer=True):
    """Deterministic Chinese Markdown chapter for report.md (verbatim contract)."""
    status = STATUS_LABEL.get(report.get("status"), report.get("status"))
    goal = report.get("goal") or {}
    water = report.get("waterline") or {}
    lines = [heading, "", f"**状态**：{status} · 目标模式 {goal.get('mode')} · "
             f"证据水位线 {water.get('max_achievable_grade')}", ""]
    targets = goal.get("targets") or []
    if targets:
        lines.append("| KPI | 方向 | 目标值 | 容差 |")
        lines.append("| --- | --- | --- | --- |")
        for t in targets:
            lines.append(f"| {t.get('metric')} | {t.get('direction')} | "
                         f"{fmt(t.get('target_value'))} | {fmt(t.get('tolerance'))} |")
        lines.append("")
    if goal.get("conflicts"):
        lines.append("**目标冲突声明**：" + "；".join(
            f"{c.get('lever')} 对 {c.get('target_a')}/{c.get('target_b')} 方向相反，需人工裁决"
            for c in goal["conflicts"]) + "")
        lines.append("")
    acts = _sorted_actions(report)
    if acts:
        lines.append("| 级别 | 杠杆 | 动作 | KPI | 预期收益 | 95%CI | 机理 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for a in acts:
            g = a.get("expected_gain") or {}
            lines.append(
                f"| {a.get('grade')} | {a.get('lever_param')} | "
                f"{DIRECTION_LABEL.get(a.get('direction'), a.get('direction'))} "
                f"{fmt((a.get('magnitude') or {}).get('from'))} → "
                f"{fmt((a.get('magnitude') or {}).get('to'))} | {g.get('metric')} | "
                f"{fmt(g.get('point'))} | {fmt_ci(g.get('ci95'))} | "
                f"{a.get('mechanism_status')} |")
        lines.append("")
        for a in acts:
            g = a.get("expected_gain") or {}
            verify = a.get("verification_plan") or {}
            lines.append(f"### {a.get('action_id')}（{a.get('grade')}）")
            lines.append(f"- 预期收益：{fmt(g.get('point'))} · 95%CI {fmt_ci(g.get('ci95'))}"
                         f" · 方法 {g.get('method')}")
            lines.append(f"- 验证：{verify.get('metric')} · {verify.get('window')} · "
                         f"{verify.get('threshold')}")
            lines.append(f"- 回滚：{a.get('rollback_condition')}")
            chain = "；".join(str(s.get("step")) for s in (a.get("mechanism_chain") or [])[:3])
            if chain:
                lines.append(f"- 机理链：{chain}")
            lines.append("")
    else:
        lines.append("本次没有建议进入建议区（数据撑不起可执行行动）。")
        lines.append("")
    pres = report.get("prescriptions") or []
    if pres:
        lines.append("### 处方区（不成建议）")
        for p in pres:
            lines.append(f"- [{p.get('kind')}] {p.get('detail')}")
        lines.append("")
    if include_disclaimer:
        lines.append("> 本节为确定性脚本生成的咨询建议（advisory），不构成参数下发；"
                     "执行须经产线审批 / optimizer-campaign 验证。")
        lines.append("")
    return "\n".join(lines)


def _execution_block(report):
    b_actions = [a for a in (report.get("actions") or []) if a.get("grade") == "B"]
    if b_actions:
        items = "".join(
            f"<li><span class='rpt-strong'>{esc(a.get('action_id'))}</span>：按验证方案执行"
            f"小试（≥3 批同工况），可用 optimizer_seed.json 一键升级为闭环验证 campaign</li>"
            for a in b_actions)
    else:
        items = "<li>本次无可执行的小试验证项（见处方区）。</li>"
    return (f"<ul>{items}</ul>"
            f"<p class='rpt-note'>advisory/optimizer_seed.json 为 B 级 top-1 动作序列化的 "
            f"optimizer-loop objective 种子（需人工确认后使用）。</p>")


def render_page(report, charts, *, title="产线优化改善指导报告"):
    """Standalone advisory page — A ledger shell, inline SVG, no CDN."""
    enriched = dict(report)
    enriched["_charts"] = charts or {}
    data = report.get("data") or {}
    lim = "".join(f"<li>{esc(x)}</li>" for x in (report.get("limitations") or []))
    reuses = "".join(f"<li class='rpt-mono'>{esc(x)}</li>"
                     for x in ((report.get("provenance") or {}).get("reuses") or []))
    excl = report.get("excluded_levers") or []
    excl_html = ""
    if excl:
        excl_html = ("<h3 class='rpt-h3' style='margin-top:20px'>被排除的杠杆</h3>"
                     "<div class='rpt-table-wrap'><table class='rpt-table'>"
                     "<tr><th>参数</th><th>原因</th><th>详情</th></tr>"
                     + "".join(f"<tr><td>{esc(e.get('param'))}</td>"
                               f"<td>{esc(e.get('reason'))}</td>"
                               f"<td>{esc(e.get('detail'))}</td></tr>" for e in excl)
                     + "</table></div>")
    degr = report.get("degradations") or []
    degr_html = ("<h3 class='rpt-h3' style='margin-top:20px'>复用与降级披露</h3>"
                 "<div class='rpt-table-wrap'><table class='rpt-table'>"
                 "<tr><th>证据腿</th><th>状态</th><th>原因</th></tr>"
                 + "".join(f"<tr><td>{esc(d.get('leg'))}</td><td>{esc(d.get('status'))}</td>"
                           f"<td>{esc(d.get('reason'))}</td></tr>" for d in degr)
                 + "</table></div>")
    acts = report.get("actions") or []
    rank = {"A": 0, "B": 1, "C": 2}
    top = sorted(acts, key=lambda a: (rank.get(a.get("grade"), 9),
                                      -(a.get("priority_score") or 0)))[0] if acts else {}
    max_grade = (sorted((a.get("grade") or "C" for a in acts),
                        key=lambda g: rank.get(g, 9))[0] if acts else "—")
    water = report.get("waterline") or {}
    status = report.get("status")
    nav_items = [("sec-goal", "01", "目标与水位线"), ("sec-roadmap", "02", "路线图"),
                 ("sec-actions", "03", "动作卡"), ("sec-evidence", "04", "证据链"),
                 ("sec-prescriptions", "05", "处方区"), ("sec-execution", "06", "执行验证"),
                 ("sec-data", "07", "数据口径")]
    nav = "".join(f'<a href="#{sid}"{" class=\'is-on\'" if i == 0 else ""}>'
                  f'<b>{no}</b>{label}</a>' for i, (sid, no, label) in enumerate(nav_items))
    if acts:
        verdict = (f"本次数据给出 <em>{len(acts)} 条分级建议</em>：最高 "
                   f"{esc(top.get('grade'))} 级 {esc(top.get('lever_param'))}，预期收益 "
                   f"{fmt((top.get('expected_gain') or {}).get('point'))} "
                   f"{esc((top.get('expected_gain') or {}).get('metric'))}；"
                   f"其余条目见路线图与动作卡。")
    else:
        verdict = (f"本次数据没有进入建议区的动作（{esc(STATUS_LABEL.get(status, status))}）："
                   f"系统给出 {len(report.get('prescriptions') or [])} 条处方，"
                   f"指明下一步该补什么证据。")
    sections = (
        f"<section class='rpt-sec' id=\"sec-goal\">"
        f"<div class='rpt-sec-head'><span class='rpt-sec-no'>01</span>"
        f"<h2>优化目标与证据水位线</h2><div class='rpt-sec-sub'>目标是谁定的、"
        f"这次数据最高能支撑到哪一级。</div></div>"
        f"<div class='rpt-body-grid'><div class='rpt-content'>{_goal_block(report)}</div>"
        f"<aside class='rpt-margin'><h4>分级口径</h4><p>A ＝ 干预性证据（设计窗 / 随机化 "
        f"DOE / 归因 CI 不含 0）；B ＝ 观察性证据，需小试验证；C ＝ 方向可信但不足以执行。</p>"
        f"<p>收益一律给 95%CI；不可估时写 <code>effect=null</code> 并说明原因，不给点估计。</p>"
        f"</aside></div></section>"
        f"<section class='rpt-sec' id=\"sec-roadmap\">"
        f"<div class='rpt-sec-head'><span class='rpt-sec-no'>02</span><h2>改善路线图</h2>"
        f"<div class='rpt-sec-sub'>按 priority_score 排序；优先级条为相对值，"
        f"不是收益绝对值。</div></div>{_roadmap(report)}</section>"
        f"<section class='rpt-sec' id=\"sec-actions\">"
        f"<div class='rpt-sec-head'><span class='rpt-sec-no'>03</span><h2>动作卡</h2>"
        f"<div class='rpt-sec-sub'>等级 / 杠杆 / 方向 / 收益 95%CI / 机理 / 验证 / 回滚；"
        f"全部 {len(acts)} 条展示。</div></div>"
        f"<div class='rpt-body-grid'><div class='rpt-content'>{_actions(report)}</div>"
        f"<aside class='rpt-margin'><h4>执行边界</h4><p>建议是「决议」，处方是「待补清单」；"
        f"两者不可混淆。A 级可直接进入验证，B 级须小试，C 级仅方向。</p>"
        f"<p style='color:var(--accent)'>本报告不构成参数下发指令。</p></aside></div></section>"
        f"<section class='rpt-sec' id=\"sec-evidence\">"
        f"<div class='rpt-sec-head'><span class='rpt-sec-no'>04</span>"
        f"<h2>证据链（剂量-响应与时序）</h2><div class='rpt-sec-sub'>图表数值直接来自 "
        f"charts.json；页面不做统计计算。</div></div>{_evidence(report, charts)}</section>"
        f"<section class='rpt-sec' id=\"sec-prescriptions\">"
        f"<div class='rpt-sec-head'><span class='rpt-sec-no'>05</span>"
        f"<h2>处方区（不成建议）</h2><div class='rpt-sec-sub'>「接下来该补什么」的清单，"
        f"不是参数指令。</div></div>{_prescriptions(report)}</section>"
    )
    return (f"<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{esc(title)}</title>{css_block()}</head><body class='rpt-scope'>"
            f"<div class='rpt-page'>"
            f"<aside class='rpt-rail'><div class='rpt-brand'>IDD<span>改善建议</span></div>"
            f"<nav class='rpt-nav'>{nav}</nav>"
            f"<div class='rpt-rail-foot'>纯咨询 · 不下发参数<br>"
            f"A/B/C 三重门 · 95%CI<br><code>{esc(report.get('report_id'))}</code></div></aside>"
            f"<main class='rpt-main'>"
            f"<header class='rpt-masthead'><p class='rpt-kicker'>Industrial Deep Diagnostic · "
            f"Improvement Advisory</p><h1>{esc(title)}</h1>"
            f"<div class='rpt-meta'><span>目标 <b>{esc(((report.get('goal') or {}).get('targets') or [{}])[0].get('metric'))}"
            f"</b></span><span>建议 <b>{len(acts)} 条</b></span>"
            f"<span>处方 <b>{len(report.get('prescriptions') or [])} 条</b></span>"
            f"<span>水位线 <b>{esc(water.get('max_achievable_grade'))}</b></span>"
            f"<span>生成 <b>{esc(str(report.get('generated_at') or '')[:16].replace('T', ' '))}</b></span></div>"
            f"<div class='rpt-verdict'><blockquote>{verdict}</blockquote>"
            f"<div class='rpt-seal {'is-a' if max_grade == 'A' else 'is-c' if max_grade == 'C' else ''}'>"
            f"<div class='rpt-seal-in'><div class='rpt-seal-num'>{esc(max_grade)}</div>"
            f"<div class='rpt-seal-grade'>{len(acts)} 条建议</div>"
            f"<div class='rpt-seal-cap'>{esc(max_grade)} 级 · 水位线 "
            f"{esc(water.get('max_achievable_grade'))}</div></div></div></div></header>"
            f"{sections}"
            f"<section class='rpt-sec' id=\"sec-execution\">"
            f"<div class='rpt-sec-head'><span class='rpt-sec-no'>06</span>"
            f"<h2>执行与验证计划</h2><div class='rpt-sec-sub'>B 级自动序列化 optimizer_seed；"
            f"执行须经审批或 campaign 验证。</div></div>"
            f"<div class='rpt-panel'>{_execution_block(report)}</div></section>"
            f"<section class='rpt-sec rpt-appendix' id=\"sec-data\">"
            f"<h2>07 · 数据与口径（证据链附录）</h2>"
            f"<dl class='rpt-kv'>"
            f"<dt>数据文件</dt><dd><code>{esc(data.get('path'))}</code></dd>"
            f"<dt>数据指纹</dt><dd><code>{esc(data.get('sha256'))}</code></dd>"
            f"<dt>行数</dt><dd>{esc(data.get('n_rows'))}</dd>"
            f"<dt>口径</dt><dd>BH-FDR q&lt;0.05（每 KPI 内全部杠杆×滞后为一族）· "
            f"|r|≥0.2 · 分箱≥5 且每箱≥8 · 外推越包络即未验证 · 收益一律 95%CI</dd></dl>"
            f"<h3 class='rpt-h3' style='margin-top:20px'>假设与局限</h3><ul>{lim}</ul>"
            f"{excl_html}{degr_html}"
            f"<h3 class='rpt-h3' style='margin-top:20px'>复用组件状态</h3><ul>{reuses}</ul>"
            f"<footer class='rpt-foot' id=\"sec-footer\"><span><b>咨询边界声明</b>：本页为纯分析"
            f"咨询产物（advisory），不构成参数下发指令，绝不下发参数；执行须经产线审批 / "
            f"optimizer-campaign 验证流程。数值与分级由确定性脚本产出，agent 仅追加解读。</span>"
            f"<span>{esc(report.get('report_id'))} · generated "
            f"{datetime.now(timezone.utc).isoformat()}</span></footer></section>"
            f"</main></div></body></html>")
