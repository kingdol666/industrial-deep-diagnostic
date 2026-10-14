#!/usr/bin/env python3
"""Build the self-contained Chinese HTML landing page from stability artifacts.

Usage: report_builder.py --report stability_report.json --charts charts.json
                         [--out line_stability_report.html]

Design rules (house style, mirroring diagnostic-html-visualizer):
  conclusion-first hero, evidence-backed finding cards, appendix formulas,
  ECharts via 3-source CDN with static-table fallback, advisory disclaimer.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time

GRADE_COLORS = {"A": "#22a06b", "B": "#d8a516", "C": "#e0703a", "D": "#c9312b",
                None: "#7a8699"}
SEV_COLORS = {"info": "#4a7fb5", "warn": "#d8a516", "high": "#e0703a",
              "critical": "#c9312b"}
SEV_LABELS = {"info": "提示", "warn": "关注", "high": "严重", "critical": "危急"}
ROLE_LABELS = {"parameter": "加工参数", "inspection": "检测指标"}


def _esc(v) -> str:
    return html.escape(str(v), quote=True)


def _num(v, nd=4):
    if v is None:
        return "—"
    if isinstance(v, float):
        s = f"{v:.{nd}f}".rstrip("0").rstrip(".")
        return s if s else "0"
    return str(v)


def _period_label(period: dict) -> str:
    def short(v):
        return _esc(str(v).replace("T", " ").split("+")[0].split("Z")[0]) if v else "—"
    return f"{short(period.get('start'))} ~ {short(period.get('end'))}"


def build(report: dict, charts: dict) -> str:
    c = report["conclusion"]
    grade_color = GRADE_COLORS.get(c.get("grade"))
    not_assessable = report["status"] != "ok"
    data = report["data"]
    findings = report.get("findings", [])
    params = report["parameters"]

    grade_cn = {"A": "稳定", "B": "亚稳定", "C": "波动", "D": "不稳定",
                None: "无法评估"}.get(c.get("grade"), c.get("label") or "")

    # ---------- hero ----------
    hero = f"""
    <section class="hero">
      <div class="hero-main">
        <div class="hero-title">产线运行稳定性报告</div>
        <div class="hero-sub">
          <span class="chip">{_esc(report['line'].get('line_id') or '未命名产线')}</span>
          {f'<span class="chip ghost">{_esc(report["line"].get("product"))}</span>' if report['line'].get('product') else ''}
          <span class="chip ghost">时段：{_period_label(report['period'])}</span>
        </div>
        <div class="statement">{_esc(c['statement'])}</div>
      </div>
      <div class="hero-score" style="--g:{grade_color}">
        <div class="score-num">{_num(c.get('score'), 1) if not not_assessable else '—'}</div>
        <div class="score-grade">{_esc(c.get('grade') or 'N/A')} · {_esc(grade_cn)}</div>
        <div class="score-cap">综合稳定性评分（0–100）</div>
      </div>
    </section>"""

    # ---------- findings ----------
    fc = []
    for f in findings:
        ev_rows = "".join(
            f"<tr><td>{_esc(e['metric'])}</td><td class=num>{_num(e.get('value'))}</td>"
            f"<td class=num>{_esc(e.get('threshold', '—'))}</td>"
            f"<td>{_esc(e.get('source', '—'))}{' <span class=\"derived\">derived</span>' if e.get('derived') else ''}</td></tr>"
            for e in f.get("evidence", []))
        conf = f.get("confidence")
        mech = f.get("mechanism") or {}
        mech_line = ""
        if mech.get("level"):
            mech_txt = {"known": "本体因果边支持", "same_domain": "同参数组（物理同域）",
                        "unknown": "无本体机制支持 [MECHANISM_UNKNOWN]"}.get(mech["level"], mech["level"])
            extra = f" — {_esc(mech.get('mechanism'))}" if mech.get("mechanism") else ""
            eq = f" 控制方程：<code>{_esc(mech['governing_equation'])}</code>" \
                if mech.get("governing_equation") else ""
            mech_line = (f"<div class='f-mech'>物理机制：{_esc(mech_txt)}{extra}{eq}</div>")
        fc.append(f"""
        <div class="finding sev-{f['severity']}">
          <div class="f-head">
            <span class="pill" style="--s:{SEV_COLORS[f['severity']]}">{SEV_LABELS[f['severity']]}</span>
            <span class="f-title">{_esc(f['title'])}</span>
            <span class="f-conf">置信度 {_num(conf, 0) if conf is not None else '—'}</span>
            <span class="f-id">{_esc(f['finding_id'])}</span>
          </div>
          <div class="f-detail">{_esc(f['detail'])}</div>
          {mech_line}
          <table class="ev-table"><thead><tr>
            <th>证据项</th><th>数值</th><th>阈值/口径</th><th>来源</th>
          </tr></thead><tbody>{ev_rows}</tbody></table>
        </div>""")
    findings_html = ("".join(fc) if fc
                     else '<div class="empty">本时段无分级发现。</div>')

    # ---------- parameter table ----------
    pt_rows = []
    for p in params:
        s = p.get("score")
        color = "#22a06b" if (s or 0) >= 85 else "#d8a516" if (s or 0) >= 70 \
            else "#e0703a" if (s or 0) >= 50 else "#c9312b"
        cap = p.get("capability") or {}
        dr = p.get("drift") or {}
        br = p.get("baseline_ref") or {}
        pt_rows.append(f"""
        <tr>
          <td>{_esc(p['name'])}<span class="role-tag">{ROLE_LABELS.get(p['role'], '')}</span></td>
          <td class=num>{_num(p['n'])}</td>
          <td class=num>{_num(p['median'])}</td>
          <td class=num>{_num(p.get('cv', 0), 6)}</td>
          <td class=num>{p['n_violation_points']}</td>
          <td class=num>{_num(dr.get('per_day_relative'), 6)}{'<span class="drift-flag">显著</span>' if dr.get('significant') else ''}</td>
          <td class=num>{_num(cap.get('cpk'))}</td>
          <td class=num>{_num(br.get('robust_z')) if br else '—'}</td>
          <td><div class="score-cell"><div class="score-bar" style="--w:{max(0, min(100, s or 0))}%;--c:{color}"></div><span style="color:{color}">{_num(s)}</span></div></td>
        </tr>""")
    params_html = "".join(pt_rows) or '<tr><td colspan="9" class="empty">无可评估参数</td></tr>'

    payload = json.dumps({"report_id": report["report_id"], "charts": charts,
                          "notAssessable": not_assessable},
                         ensure_ascii=False, separators=(",", ":"))

    condition_html = _condition_html(report)
    corr = report.get("correlations") or {}
    contrib_note = ("" if corr.get("contributions") else
                    "<div class='empty' style='padding:8px'>未声明检测/响应指标"
                    "（context.inspection_cols 或本体 role=response）——贡献分析未执行，"
                    "声明目标指标后启用。</div>")
    prep = data.get("preprocessing")
    prep_s = (prep if isinstance(prep, str)
              else json.dumps(prep, ensure_ascii=False)) if prep else None
    prep_row = ""
    if isinstance(prep, dict) and prep.get("mode") == "directory_adaptive":
        dispositions = prep.get("source_dispositions") or []
        primary = prep.get("selected_table") or {}
        rows = "".join(f"<tr><td>{_esc(x.get('relative_path', ''))}</td><td>{_esc(x.get('role', ''))}</td><td>{_esc(x.get('disposition', ''))}</td><td>{_esc(x.get('reason', ''))}</td></tr>" for x in dispositions)
        prep_row = (f"<tr><th>文件夹自适应输入</th><td>评分主表 {_esc(primary.get('file') or '—')}；"
                    f"时间列 {_esc(primary.get('time_column') or '—')}；{primary.get('n_rows', 0)} 行。"
                    f"完整来源及 SHA-256：<code>{_esc(prep.get('manifest_path') or '00_input/input_manifest.json')}</code></td></tr>"
                    f"<tr><td colspan=2><table><thead><tr><th>来源</th><th>角色</th><th>处置</th><th>原因</th></tr></thead><tbody>{rows}</tbody></table></td></tr>")
    elif prep_s:
        prep_row = f"<tr><th>预处理溯源</th><td>{_esc(prep_s)}</td></tr>"
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>产线运行稳定性报告 · {_esc(report['line'].get('line_id') or report['report_id'])}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<script src="https://unpkg.com/echarts@5.5.0/dist/echarts.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.0/echarts.min.js"></script>
<style>
  :root {{ --bg:#101418; --panel:#171d24; --line:#26303b; --tx:#dfe7ee; --mut:#8a99a8;
          --acc:#e8a33d; --good:#22a06b; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--tx);
        font:14px/1.65 "Segoe UI","Microsoft YaHei",sans-serif; }}
  .wrap {{ max-width:1180px; margin:0 auto; padding:28px 20px 60px; }}
  .hero {{ display:flex; gap:24px; background:var(--panel); border:1px solid var(--line);
         border-radius:14px; padding:26px 28px; align-items:center; justify-content:space-between;
         flex-wrap:wrap; }}
  .hero-title {{ font-size:24px; font-weight:700; letter-spacing:.5px; }}
  .hero-sub {{ margin:10px 0 12px; display:flex; gap:8px; flex-wrap:wrap; }}
  .chip {{ background:rgba(232,163,61,.14); color:var(--acc); border:1px solid rgba(232,163,61,.35);
          border-radius:999px; padding:2px 12px; font-size:12px; }}
  .chip.ghost {{ background:transparent; color:var(--mut); border-color:var(--line); }}
  .statement {{ font-size:15px; max-width:640px; }}
  .hero-score {{ text-align:center; min-width:190px; border:1px solid var(--g);
               border-radius:14px; padding:16px 22px; }}
  .score-num {{ font-size:46px; font-weight:800; color:var(--g); line-height:1.1; }}
  .score-grade {{ color:var(--g); font-weight:700; margin-top:4px; }}
  .score-cap {{ color:var(--mut); font-size:12px; margin-top:6px; }}
  h2 {{ font-size:17px; margin:34px 0 12px; padding-left:10px; border-left:3px solid var(--acc); }}
  .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:12px;
          padding:16px 18px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:14px; }}
  .finding {{ background:var(--panel); border:1px solid var(--line); border-left:3px solid var(--s);
            border-radius:10px; padding:14px 16px; margin-bottom:12px; }}
  .f-head {{ display:flex; align-items:center; gap:10px; }}
  .pill {{ background:var(--s); color:#fff; border-radius:999px; padding:1px 10px;
          font-size:12px; flex:0 0 auto; }}
  .f-title {{ font-weight:700; }}
  .f-id {{ margin-left:auto; color:var(--mut); font-size:12px; }}
  .f-detail {{ color:#b9c6d2; margin:8px 0; }}
  .f-mech {{ font-size:12.5px; color:#a8c0d8; background:rgba(90,140,190,.08);
           border:1px dashed rgba(90,140,190,.35); border-radius:6px; padding:6px 10px; margin:6px 0; }}
  .f-conf {{ margin-left:auto; color:var(--mut); font-size:12px; white-space:nowrap; }}
  .f-id {{ color:var(--mut); font-size:12px; margin-left:10px; }}
  .derived {{ font-size:10px; color:var(--acc); border:1px solid rgba(232,163,61,.4);
            border-radius:4px; padding:0 4px; margin-left:4px; }}
  table {{ border-collapse:collapse; width:100%; }}
  th,td {{ border-bottom:1px solid var(--line); padding:7px 10px; text-align:left;
         font-size:13px; vertical-align:top; }}
  th {{ color:var(--mut); font-weight:600; white-space:nowrap; }}
  td.num, .num {{ font-variant-numeric:tabular-nums; }}
  .ev-table {{ margin-top:8px; }}
  .ev-table th {{ font-size:12px; }}
  .role-tag {{ margin-left:8px; font-size:11px; color:var(--mut); border:1px solid var(--line);
             border-radius:4px; padding:0 6px; }}
  .drift-flag {{ margin-left:6px; color:#e0703a; font-size:11px; border:1px solid #e0703a;
               border-radius:4px; padding:0 5px; }}
  .score-cell {{ display:flex; align-items:center; gap:8px; min-width:130px; }}
  .score-bar {{ height:8px; width:var(--w); max-width:120px; background:var(--c);
              border-radius:4px; }}
  .chart {{ height:300px; background:var(--panel); border:1px solid var(--line);
          border-radius:12px; }}
  .chart + .chart {{ margin-top:14px; }}
  .chart-title {{ padding:10px 14px 0; color:var(--mut); font-size:13px; }}
  .empty {{ color:var(--mut); padding:10px 4px; }}
  .static-table {{ max-height:220px; overflow:auto; margin-top:8px; }}
  .foot {{ margin-top:40px; color:var(--mut); font-size:12px; border-top:1px solid var(--line);
         padding-top:14px; }}
  .foot b {{ color:#b9c6d2; }}
  code {{ background:#0c1013; border:1px solid var(--line); border-radius:4px;
        padding:0 5px; font-size:12px; }}
  @media print {{ body {{ background:#fff; color:#111; }} }}
</style>
</head>
<body>
<div class="wrap">
  {hero}

  <h2>工况理解（本体优先）</h2>
  {condition_html}

  <h2>核心发现（结论与证据）</h2>
  {findings_html}

  <h2>参数稳定性总览</h2>
  <div class="panel" style="overflow:auto">
    <table>
      <thead><tr>
        <th>参数</th><th>样本数</th><th>中位数</th><th>CV</th><th>SPC违规点</th>
        <th>漂移/天(相对)</th><th>Cpk</th><th>基线z</th><th>评分</th>
      </tr></thead>
      <tbody>{params_html}</tbody>
    </table>
  </div>

  <h2>趋势与控制限</h2>
  <div id="trend-charts"></div>
  <noscript><div class="panel empty">已禁用 JavaScript：请查看上方参数总览表与证据附录，
    或使用导出的 charts.json。</div></noscript>

  <h2>参数相关与波动驱动</h2>
  <div class="grid">
    <div class="panel" id="contrib-panel"><div class="chart-title">对检测/目标指标的方差解释占比</div>
      <div id="contrib-chart" class="chart"></div>{contrib_note}</div>
    <div class="panel" id="heat-panel"><div class="chart-title">参数相关热力图（滞后补偿 |Spearman|）</div>
      <div id="heat-chart" class="chart"></div></div>
  </div>

  <h2>协同分析输入</h2>
  <div class="panel" id="integrations">{_integrations_html(report)}</div>

  <h2>数据与口径（证据链附录）</h2>
  <div class="panel">
    <table>
      <tr><th>数据文件</th><td>{_esc(data['path'])}</td></tr>
      <tr><th>数据指纹</th><td class="num">{_esc(data['sha256'])}</td></tr>
      <tr><th>行数（原始/入评）</th><td class="num">{data['n_rows_raw']} / {data['n_rows_used']}</td></tr>
      <tr><th>时间列 / 采样间隔</th><td>{_esc(data['time_col'])} /
        <span class="num">{_num(data.get('sampling_interval_median_seconds'), 2)} s</span></td></tr>
      <tr><th>缺失率 / 覆盖率</th><td class="num">{data.get('missing_rate', 0):.2%} /
        {data.get('coverage_ratio', 1):.2%}</td></tr>
      <tr><th>评估参数</th><td>{_esc('、'.join(data['parameter_cols'])) or '—'}</td></tr>
      <tr><th>检测指标</th><td>{_esc('、'.join(data['inspection_cols'])) or '—'}</td></tr>
      {prep_row}
    </table>
    {_methods_html(report)}
    {_limitations_html(report)}
  </div>

  <div class="foot">
    <b>报告性质：</b>本报告由确定性统计脚本生成（零 LLM 参与，全部数值可复算），
    属咨询性分析产物，不构成参数下发或控制指令；行动决策归生产线管理方。<br>
    <b>生成物：</b>{_esc(report['report_id'])} ·
    contract {_esc(report['contract_version'])} ·
    script v{_esc(report['provenance']['script_version'])} ·
    {report['generated_at']}
  </div>
</div>

<script id="payload" type="application/json">{payload}</script>
<script>
(function () {{
  var DATA = {{}};
  try {{ DATA = JSON.parse(document.getElementById('payload').textContent); }} catch (e) {{}}
  function fallback() {{
    var host = document.getElementById('trend-charts');
    var rows = [];
    (DATA.charts.trend || []).forEach(function (s) {{
      var vs = s.v.filter(function (x) {{ return x !== null; }});
      var mn = Math.min.apply(null, vs), mx = Math.max.apply(null, vs);
      var nBad = s.violation_indices_in_plot.length;
      rows.push('<tr><td>' + s.name + '</td><td>' + vs.length + '</td><td>' +
        mn.toFixed(4) + '</td><td>' + mx.toFixed(4) + '</td><td>' + nBad + '</td></tr>');
    }});
    host.innerHTML = '<div class="panel"><div class="chart-title">静态模式（ECharts CDN 不可用）' +
      '——各参数趋势摘要</div><div class="static-table"><table><thead><tr>' +
      '<th>参数</th><th>点数</th><th>最小</th><th>最大</th><th>违规点</th></tr></thead>' +
      '<tbody>' + rows.join('') + '</tbody></table></div></div>';
    ['contrib-chart', 'heat-chart'].forEach(function (id) {{
      var el = document.getElementById(id);
      if (el) el.parentNode.style.display = 'none';
    }});
  }}
  function init() {{
    if (!window.echarts) {{ fallback(); return; }}
    var charts = DATA.charts || {{}};
    var host = document.getElementById('trend-charts');
    (charts.trend || []).forEach(function (s) {{
      var box = document.createElement('div');
      box.className = 'chart';
      box.innerHTML = '<div class="chart-title">' + s.name +
        '（中心=中位数，虚线=±3σ_within' + (s.spec && s.spec.lsl != null ? '，红线=规格限' : '') + '）</div>' +
        '<div style="height:calc(100% - 30px)"></div>';
      host.appendChild(box);
      var el = box.lastChild;
      var ch = echarts.init(el); allCharts.push(ch);
      var series = [{{ name: s.name, type: 'line', showSymbol: false,
        data: s.t.map(function (t, i) {{ return [t, s.v[i]]; }}),
        lineStyle: {{ width: 1.2, color: '#5b8dbf' }} }}];
      [['UCL', s.ucl, '#e0703a', 'dashed'], ['LCL', s.lcl, '#e0703a', 'dashed'],
       ['LSL', s.spec && s.spec.lsl, '#c9312b', 'solid'],
       ['USL', s.spec && s.spec.usl, '#c9312b', 'solid']].forEach(function (m) {{
        if (m[1] !== null && m[1] !== undefined)
          series.push({{ name: m[0], type: 'line', data: [[s.t[0], m[1]], [s.t[s.t.length - 1], m[1]]],
            symbol: 'none', lineStyle: {{ color: m[2], type: m[3], width: 1 }},
            endLabel: {{ show: true, formatter: m[0], color: m[2] }} }});
      }});
      var bad = s.violation_indices_in_plot || [];
      if (bad.length)
        series.push({{ name: '违规点', type: 'scatter',
          data: bad.map(function (i) {{ return [s.t[i], s.v[i]]; }}),
          itemStyle: {{ color: '#c9312b' }}, symbolSize: 7 }});
      ch.setOption({{
        grid: {{ left: 60, right: 60, top: 18, bottom: 44 }},
        tooltip: {{ trigger: 'axis' }},
        xAxis: {{ type: 'time' }},
        yAxis: {{ type: 'value', scale: true }},
        series: series
      }});
    }});
    if ((charts.trend || []).length === 0) {{
      host.innerHTML = '<div class="panel empty">无可绘制的趋势数据。</div>';
    }}
    var contrib = document.getElementById('contrib-chart');
    if (contrib && (charts.contribution_bar || []).length) {{
      var cb = echarts.init(contrib); allCharts.push(cb);
      var items = charts.contribution_bar.slice(0, 10);
      cb.setOption({{
        grid: {{ left: 90, right: 30, top: 18, bottom: 40 }},
        tooltip: {{}},
        xAxis: {{ type: 'value', max: 1, axisLabel: {{ formatter: function (v) {{
          return (v * 100).toFixed(0) + '%'; }} }} }},
        yAxis: {{ type: 'category', data: items.map(function (d) {{
          return d.driver + ' → ' + d.target; }}).reverse() }},
        series: [{{ type: 'bar', data: items.map(function (d) {{
          return Math.round(d.share * 1000) / 10; }}).reverse(),
          itemStyle: {{ color: '#e8a33d' }}, barMaxWidth: 18 }}]
      }});
    }} else if (contrib) {{ contrib.parentNode.style.display = 'none'; }}
    var heat = document.getElementById('heat-chart');
    if (heat && charts.corr_heatmap && charts.corr_heatmap.labels.length > 1) {{
      var hm = echarts.init(heat); allCharts.push(hm);
      var pts = [];
      charts.corr_heatmap.matrix.forEach(function (row, i) {{
        row.forEach(function (v, j) {{
          if (v !== null && i !== j)
            pts.push([j, charts.corr_heatmap.labels.length - 1 - i, v]);
        }});
      }});
      hm.setOption({{
        grid: {{ left: 110, right: 60, top: 18, bottom: 60 }},
        tooltip: {{ position: 'top' }},
        xAxis: {{ type: 'category', data: charts.corr_heatmap.labels,
          axisLabel: {{ rotate: 30 }} }},
        yAxis: {{ type: 'category', data: charts.corr_heatmap.labels.slice().reverse() }},
        visualMap: {{ min: 0, max: 1, calculable: true, orient: 'horizontal',
          left: 'center', bottom: 0, inRange: {{ color: ['#1d2a36', '#e8a33d', '#c9312b'] }} }},
        series: [{{ type: 'heatmap', data: pts,
          label: {{ show: charts.corr_heatmap.labels.length <= 8, formatter: function (p) {{
            return p.value[2].toFixed(2); }} }} }}]
      }});
    }} else if (heat) {{ heat.parentNode.style.display = 'none'; }}
  }}
  var allCharts = [];
  function reflowCharts() {{ allCharts.forEach(function (c) {{ try {{ c.resize(); }} catch (e) {{}} }}); }}
  window.addEventListener('resize', reflowCharts);
  if (document.readyState === 'complete') init();
  else window.addEventListener('load', init);
  // 布局稳定后强制重测一次尺寸：在后台/延迟渲染环境下，init 时容器宽度
  // 可能被读成 0（canvas 宽 0、图空白），双 rAF 确保 DOM 布局完成后再 resize。
  function reflowWhenSettled() {{
    requestAnimationFrame(function () {{ requestAnimationFrame(reflowCharts); }});
  }}
  if (document.readyState === 'complete') reflowWhenSettled();
  else window.addEventListener('load', reflowWhenSettled);
  setTimeout(function () {{ if (!window.echarts) fallback(); }}, 4000);
}})();
</script>
</body>
</html>"""
    return doc


def _condition_html(report: dict) -> str:
    """工况理解 section: ontology narrative + per-column understanding + regimes."""
    cond = report.get("condition") or {}
    ont = cond.get("ontology") or {}
    scene = cond.get("scene") or {}
    if ont.get("mode") == "ontology":
        head = (f"本体来源：{_esc(ont.get('source'))}（{_esc(ont.get('path'))}）。"
                if ont.get("path") else "本体来源：本体资产。")
    else:
        head = ("未命中本体资产（<code>00_input/ontology.json</code>、"
                "<code>01_ontology/</code>、本体资产库均未命中）——以下列角色/单位/规格为"
                "确定性启发推断（assigned_by=auto），可由 industrial-ontology-builder "
                "先建本体后复跑以获得物理语义与控制方程级解读。")
    scene_rows = []
    for k, label in (("name", "场景"), ("process_type", "过程类型"),
                     ("production_goal", "生产目标")):
        if scene.get(k):
            scene_rows.append(f"<tr><th>{label}</th><td>{_esc(scene[k])}</td></tr>")

    col_rows = []
    for p in report.get("parameters", []):
        doc = (cond.get("columns") or {}).get(p["name"]) or {}
        cd = p.get("condition") or {}
        spec = p.get("spec") or {}
        spec_s = "—"
        if spec.get("lsl") is not None or spec.get("usl") is not None:
            src = {"user": "用户提供", "ontology": "本体资产"}.get(spec.get("source"), spec.get("source"))
            spec_s = f"[{_num(spec.get('lsl'))}, {_num(spec.get('usl'))}]（{src}）"
        col_rows.append(
            f"<tr><td class=strong>{_esc(p['name'])}"
            f"<span class='role-tag'>{_esc(cd.get('label') or doc.get('label') or '')}</span></td>"
            f"<td>{_esc(cd.get('unit') or doc.get('unit') or '—')}</td>"
            f"<td>{'检测指标' if p['role'] == 'inspection' else '加工参数'}</td>"
            f"<td>{spec_s}</td>"
            f"<td>{_esc((cd.get('governing_law') or doc.get('governing_law')) or '—')}</td>"
            f"<td><span class='role-tag'>{_esc(cd.get('assigned_by') or doc.get('assigned_by') or 'auto')}</span></td>"
            f"</tr>")
    col_table = (f"<table><thead><tr><th>参数（本体名）</th><th>单位</th><th>角色</th>"
                 f"<th>规格/正常范围</th><th>控制方程</th><th>assigned_by</th></tr></thead>"
                 f"<tbody>{''.join(col_rows) or '<tr><td colspan=6 class=empty>—</td></tr>'}</tbody></table>")

    regimes = (cond.get("regimes") or {})
    regime_html = ""
    snap = cond.get("snapshot") or []
    snap_html = ""
    if snap:
        rows = []
        for s in snap:
            unit = f" {_esc(s['unit'])}" if s.get("unit") else ""
            rows.append(f"<tr><td class=strong>{_esc(s.get('column'))}"
                        f"<span class='role-tag'>{_esc(s.get('label') or '')}</span></td>"
                        f"<td>{_esc(s.get('stage') or '—')}</td>"
                        f"<td class=num>{_num(s.get('value'))}{unit}</td>"
                        f"<td>{_esc(s.get('governing_law') or '—')}</td></tr>")
        snap_html = (f"<div style='margin-top:10px'><b>当前工况快照（数据为单时刻快照导出，"
                     f"以下为导出时刻的瞬时值，非时段统计）</b>"
                     f"<table><thead><tr><th>参数（本体名）</th><th>工段</th><th>瞬时值</th>"
                     f"<th>控制方程</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>")
    if regimes.get("available") and regimes.get("regimes"):
        rows = []
        for i, seg in enumerate(regimes["regimes"]):
            rows.append(f"<tr><td>段 {i + 1}</td><td class=num>行 {seg['start']}–{seg['end']}"
                        f"（{seg['n_rows']} 行）</td><td>{_esc(seg['label'])}</td></tr>")
        regime_html = (f"<div style='margin-top:10px'><b>工况分段（sentinel C3，"
                       f"方法 { _esc(regimes.get('method')) }；变点 {len(regimes.get('change_points', []))} 个）</b>"
                       f"<table><thead><tr><th>段</th><th>行范围</th><th>主导状态</th></tr></thead>"
                       f"<tbody>{''.join(rows)}</tbody></table></div>")
    elif regimes.get("method"):
        regime_html = (f"<div class='empty' style='margin-top:8px'>工况分段未启用"
                       f"（{_esc(regimes.get('method'))}）。</div>")

    return (f"<div class='panel'><p style='margin:0 0 8px'>{head}</p>"
            f"<table>{''.join(scene_rows)}</table>"
            f"<div style='overflow:auto;margin-top:8px'>{col_table}</div>"
            f"{snap_html}{regime_html}</div>")


def _integrations_html(report: dict) -> str:
    integ = report.get("integrations", {})
    rows = []
    sb = integ.get("sentinel_baseline") or {}
    rows.append("<tr><th>sentinel 基线对照</th><td>" +
                (_esc(sb.get("path")) if sb.get("used") else
                 f"未启用（{_esc(sb.get('reason') or '未提供基线')}）") + "</td></tr>")
    tm = integ.get("tuning_memory") or {}
    if tm.get("used"):
        acts = tm.get("estimable") or []
        tm_txt = (f"已归因 {tm.get('n_actions', '?')} 个动作，其中 estimable "
                  f"{len(acts)} 个：" +
                  "；".join(f"{_esc(a.get('parameter'))}→{_num(a.get('to'))}"
                            f"（Δ{_num(a.get('delta_metric'))}，{a.get('direction')}）"
                            for a in acts[:5]) or "无 estimable 动作")
    else:
        tm_txt = f"未启用（{_esc(tm.get('reason') or '未提供 action_log')}）"
    rows.append(f"<tr><th>tuning-memory 调优归因</th><td>{tm_txt}</td></tr>")
    doe = integ.get("doe_analyzer") or {}
    if doe.get("used"):
        w = doe.get("operating_windows") or []
        doe_txt = (f"已读取 {len(w)} 条推荐操作窗" +
                   (f"，{len(doe.get('violations') or [])} 项超窗" if doe.get("violations") else ""))
    else:
        doe_txt = f"未启用（{_esc(doe.get('reason') or '未提供 doe_run_dir')}）"
    rows.append(f"<tr><th>doe-analyzer 操作窗</th><td>{doe_txt}</td></tr>")
    degr = report.get("degradations") or []
    if degr:
        rows.append("<tr><th>降级说明</th><td>" +
                    "；".join(f"{_esc(d['check'])}: {_esc(d['reason'])}" for d in degr) +
                    "</td></tr>")
    return "<table><tbody>" + "".join(rows) + "</tbody></table>"


def _methods_html(report: dict) -> str:
    prov = report.get("provenance", {})
    methods = prov.get("methods", [])
    doc = {
        "sentinelcore_nelson_episodes": "Nelson 判异复用 industrial-sentinel sentinelcore "
                                        "（R1 单点越 3σ；R2 连续 9 点同侧；R3 连续 6 点同向；"
                                        "R5 三点中两点越 2σ；R6 五点中四点越 1σ），单一事实源。",
        "mrbar_sigma_1.128": "σ_within 由移动极差估计：σ = MR̄ / 1.128（与 industrial-sentinel 同口径）。",
        "cpk_within_ppk_overall": "Cpk 用组内 σ（MR̄ 法），Ppk 用整体标准差；"
                                  "规格限来源：用户上下文 > 本体资产 normal_range > 不计算。",
        "theil_sen_mk_drift": "漂移：Theil–Sen 稳健斜率（每行斜率 ÷ 采样间隔换算每秒）"
                              "+ Mann–Kendall 显著性（p&lt;0.01 且相对漂移≥0.1%/天才计入）。",
        "lagged_spearman_max10": "相关性：滞后 0–10 行逐行 Spearman 取最强，并记录领先行数；"
                                 "物理机制由本体 relationships/参数组校验（darwin 四条件）。",
        "contribution_r2_share": "贡献分解：目标指标上各驱动参数滞后补偿后 |r|² 归一化占比"
                                 "（阈值 |r|≥0.3），领先行数一并记录。",
        "regime_segmentation_c3": "工况分段：复用 industrial-sentinel regime_map（方差比+漂移坡道"
                                  "融合 + 二分分割显著变点），变点与主导状态逐段列出。",
        "ontology_first_condition": "本体优先：先于任何统计构建工况理解"
                                    "（显式路径 > 00_input/01_ontology 产物 > 本体资产库），"
                                    "每个推断字段带 assigned_by=ontology|user|auto。",
        "weighted_penalty_score_v1": "评分：每参数 100 分起，按 SPC 违规剧集率/CV/Cpk/漂移/基线偏离"
                                     "分档扣分，综合分为参数加权均值；A≥85 稳定，B≥70 亚稳定，"
                                     "C≥50 波动，D&lt;50 不稳定。",
        "darwin_limitations": "数据真值与局限：全部数值可由原始表复算；推导字段标记 derived；"
                              "假设、混杂因子与规格覆盖显式列出（见下）。",
    }
    lis = "".join(f"<li><code>{_esc(m)}</code> — {doc.get(m, '')}</li>" for m in methods)
    return (f"<div style='margin-top:12px'><b>方法与阈值（可复算）</b><ul>{lis}</ul>"
            f"<span style='color:var(--mut)'>python {prov.get('python')} · "
            f"numpy {prov.get('numpy')} · pandas {prov.get('pandas')} · "
            f"spc {prov.get('spc_source')} · input {prov.get('input_sha256')}</span></div>")


def _limitations_html(report: dict) -> str:
    lim = report.get("limitations") or {}
    if not lim:
        return ""
    sampling = lim.get("sampling") or {}
    conf = lim.get("confounders") or []
    uncontrolled = "<b style='color:#e0703a'>未控</b>"
    conf_rows = "".join(
        f"<tr><td>{_esc(c.get('variable'))}</td><td>{_esc(c.get('why'))}</td>"
        f"<td>{'已控' if c.get('controlled') else uncontrolled}</td></tr>"
        for c in conf) or "<tr><td colspan=3 class=empty>本体未登记混杂因子</td></tr>"
    spec_cov = lim.get("spec_coverage") or {}
    assumptions = "".join(f"<li>{_esc(a)}</li>" for a in lim.get("model_assumptions", []))
    return f"""
    <div style='margin-top:16px'>
      <b>假设与局限（darwin 数据真值条款）</b>
      <table>
        <tr><th>数据来源</th><td>{_esc(lim.get('data_source', ''))}</td></tr>
        <tr><th>抽样</th><td>{'系统抽样 stride=' + _esc(sampling.get('stride')) if sampling.get('sampled') else '全量入评（' + _esc(sampling.get('n_rows_analyzed')) + ' 行）'}</td></tr>
        <tr><th>规格覆盖</th><td>用户提供：{_esc('、'.join(spec_cov.get('user', [])) or '无')} ·
          本体资产：{_esc('、'.join(spec_cov.get('ontology', [])) or '无')} ·
          无规格（不评 Cpk）：{_esc('、'.join(spec_cov.get('none', [])) or '无')}</td></tr>
      </table>
      <div style='margin-top:6px'><b>模型假设</b><ul>{assumptions or '<li>—</li>'}</ul></div>
      <div style='margin-top:6px'><b>混杂因子（本体登记）</b>
        <table><thead><tr><th>变量</th><th>影响说明</th><th>状态</th></tr></thead>
        <tbody>{conf_rows}</tbody></table></div>
    </div>"""


def selfcheck(html_path: str, report: dict) -> dict:
    size = os.path.getsize(html_path)
    with open(html_path, "r", encoding="utf-8") as f:
        text = f.read()
    checks = {
        "min_size": size >= 8192,
        "hero_conclusion": "产线运行稳定性报告" in text and "statement" in text.replace("'", '"'),
        "condition_section": "工况理解" in text,
        "findings_section": "核心发现" in text,
        "evidence_table": "ev-table" in text,
        "limitations_section": "假设与局限" in text,
        "charts_payload": "payload" in text and '"trend"' in text,
        "echarts_cdn_3source": text.count("echarts") >= 3,
        "static_fallback": "fallback" in text,
        "appendix_methods": "方法与阈值" in text,
        "advisory_disclaimer": "不构成参数下发" in text,
        "no_placeholder": "PLACEHOLDER" not in text.upper().replace("PLACEHOLDER_TEXT", ""),
        "snapshot_iff": ("当前工况快照" in text) == bool((report.get("condition") or {}).get("snapshot")),
    }
    return {
        "contract_version": "line-stability-html-selfcheck/1.0",
        "html_path": os.path.abspath(html_path),
        "size_bytes": size,
        "report_id": report.get("report_id"),
        "checks": checks,
        "pass": all(checks.values()),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def build_markdown(report: dict) -> str:
    """Chinese Markdown companion report (same numbers as the HTML, darwin
    traceability preserved: derived marks + limitations + provenance)."""
    c = report["conclusion"]
    data = report["data"]
    lines: list[str] = []
    ap = lines.append
    ap(f"# 产线运行稳定性报告 · {report['line'].get('line_id') or report['report_id']}")
    ap("")
    ap(f"- **报告编号**：{report['report_id']}（{report['contract_version']}）")
    ap(f"- **时段**：{report['period'].get('start')} ~ {report['period'].get('end')}")
    ap(f"- **综合评分**：**{c.get('score')}（{c.get('grade')} 级 · {c.get('label')}）**"
       if c.get("score") is not None else "- **综合评分**：无法评估")
    ap(f"- **结论**：{c.get('statement')}")
    ap("")
    cond = report.get("condition") or {}
    if cond.get("scene"):
        scene = cond["scene"]
        ap("## 工况理解（本体优先）")
        ap("")
        ap(f"- 场景：{scene.get('name') or '—'}（{scene.get('process_type') or '—'}）；"
           f"生产目标：{scene.get('production_goal') or '—'}")
        ap(f"- 本体来源：{cond['ontology'].get('mode')}（{cond['ontology'].get('source') or '—'}）")
        ap("")
        ap("| 参数 | 本体名 | 单位 | 角色 | 规格 | 控制方程 | assigned_by |")
        ap("|---|---|---|---|---|---|---|")
        for p in report.get("parameters", []):
            doc = (cond.get("columns") or {}).get(p["name"], {})
            spec = p.get("spec") or {}
            spec_s = (f"[{_num(spec.get('lsl'))}, {_num(spec.get('usl'))}]"
                      f"（{spec.get('source') or '—'}）") if (spec.get("lsl") is not None
                                                        or spec.get("usl") is not None) else "—"
            ap(f"| {p['name']} | {doc.get('label') or '—'} | {doc.get('unit') or '—'} | "
               f"{'检测指标' if p['role'] == 'inspection' else '加工参数'} | {spec_s} | "
               f"{doc.get('governing_law') or '—'} | {doc.get('assigned_by') or 'auto'} |")
        snap = cond.get("snapshot") or []
        if snap:
            ap("")
            ap("### 当前工况快照（单时刻瞬时值，非时段统计）")
            ap("")
            ap("| 参数 | 本体名 | 工段 | 瞬时值 | 控制方程 |")
            ap("|---|---|---|---|---|")
            for s in snap:
                ap(f"| {s.get('column')} | {s.get('label') or '—'} | {s.get('stage') or '—'} | "
                   f"{_num(s.get('value'))}{(' ' + s['unit']) if s.get('unit') else ''} | "
                   f"{s.get('governing_law') or '—'} |")
        regimes = (cond.get("regimes") or {})
        if regimes.get("available") and regimes.get("regimes"):
            ap("")
            ap(f"**工况分段**（sentinel C3，方法 {regimes.get('method')}；"
               f"变点 {len(regimes.get('change_points', []))} 个）")
            ap("")
            ap("| 段 | 行范围 | 主导状态 |")
            ap("|---|---|---|")
            for i, seg in enumerate(regimes["regimes"]):
                ap(f"| 段 {i + 1} | {seg['start']}–{seg['end']}（{seg['n_rows']} 行） | {seg['label']} |")
        ap("")

    ap("## 核心发现（结论与证据）")
    ap("")
    for f in report.get("findings", []):
        mech = f.get("mechanism") or {}
        mech_s = ""
        if mech.get("level"):
            mech_s = {"known": "｜本体因果边支持", "same_domain": "｜同参数组",
                      "unknown": "｜[MECHANISM_UNKNOWN]"}.get(mech["level"], "")
        ap(f"### {f['finding_id']} [{f['severity']}] {f['title']}"
           f"（置信度 {f.get('confidence')}）{mech_s}")
        ap("")
        ap(f"{f['detail']}")
        if mech.get("mechanism"):
            ap(f"> 物理机制：{mech['mechanism']}"
               + (f"（{mech['governing_equation']}）" if mech.get("governing_equation") else ""))
        ap("")
        ap("| 证据项 | 数值 | 阈值/口径 | 来源 |")
        ap("|---|---|---|---|")
        for e in f.get("evidence", []):
            dv = "（derived）" if e.get("derived") else ""
            ap(f"| {e.get('metric')} | {_num(e.get('value'))} | {e.get('threshold', '—')} | "
               f"{e.get('source', '—')}{dv} |")
        ap("")

    ap("## 参数稳定性总览")
    ap("")
    ap("| 参数 | 角色 | 样本 | 中位数 | CV | SPC剧集 | 漂移/天 | Cpk | 评分 |")
    ap("|---|---|---|---|---|---|---|---|---|")
    for p in report.get("parameters", []):
        dr = p.get("drift") or {}
        cap = p.get("capability") or {}
        ap(f"| {p['name']} | {'检测' if p['role'] == 'inspection' else '参数'} | {p['n']} | "
           f"{_num(p['median'])} | {_num(p.get('cv'), 6)} | {p['n_violation_points']} | "
           f"{_num(dr.get('per_day_relative'), 6)}{'（显著）' if dr.get('significant') else ''} | "
           f"{_num(cap.get('cpk'))} | {p.get('score')} |")
    ap("")

    ap("## 数据与口径")
    ap("")
    ap(f"- 数据：`{data['path']}`（{data['sha256']}）")
    ap(f"- 行数（原始/入评）：{data['n_rows_raw']} / {data['n_rows_used']}"
       + (f"（系统抽样 stride={data.get('stride')}）" if data.get("sampled") else ""))
    ap(f"- 时间列/采样间隔：{data['time_col']} / "
       f"{_num(data.get('sampling_interval_median_seconds'), 2)} s；缺失率 {data.get('missing_rate', 0):.2%}")
    prep = data.get("preprocessing")
    if isinstance(prep, dict) and prep.get("mode") == "directory_adaptive":
        primary = prep.get("selected_table") or {}
        ap(f"- 输入模式：自适应目录 `{prep.get('source_directory')}`；评分主表 `{primary.get('file')}`（{primary.get('n_rows')} 行，时间列 `{primary.get('time_column')}`）。")
        ap(f"- 逐文件来源角色/处置及 SHA-256：`{prep.get('manifest_path') or '00_input/input_manifest.json'}`")
        ap("")
        ap("| 来源文件 | 角色 | 处置 | 原因 |")
        ap("|---|---|---|---|")
        for item in prep.get("source_files", []):
            ap(f"| {item.get('relative_path')} | {item.get('role')} | {item.get('disposition')} | {item.get('reason')} |")
    elif prep:
        prep_s = prep if isinstance(prep, str) else json.dumps(prep, ensure_ascii=False)
        ap(f"- 预处理溯源：{prep_s}")
    lim = report.get("limitations") or {}
    if lim:
        ap("")
        ap("### 假设与局限（darwin 条款）")
        ap("")
        ap(f"- {lim.get('data_source')}")
        for a in lim.get("model_assumptions", []):
            ap(f"- 假设：{a}")
        for cnf in lim.get("confounders", []):
            ap(f"- 混杂因子：{cnf.get('variable')} — {cnf.get('why')}"
               f"（{'已控' if cnf.get('controlled') else '**未控**'}）")
    ap("")
    ap("---")
    ap("")
    ap(f"> 本报告由确定性统计脚本生成（零 LLM，全部数值可复算），属咨询性分析产物，"
       f"不构成参数下发指令。{report['report_id']} · "
       f"script v{report['provenance'].get('script_version')} · {report['generated_at']}")
    return "\n".join(lines)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="report_builder.py")
    ap.add_argument("--report", required=True)
    ap.add_argument("--charts", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--md", default=None,
                    help="also write a Markdown companion report at this path")
    args = ap.parse_args(argv)
    with open(args.report, "r", encoding="utf-8") as f:
        report = json.load(f)
    with open(args.charts, "r", encoding="utf-8") as f:
        charts_data = json.load(f)
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.report)),
                                   "line_stability_report.html")
    doc = build(report, charts_data)
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(build_markdown(report))
        print(f"[line-stability] md written {args.md}")
    check = selfcheck(out, report)
    check_path = os.path.join(os.path.dirname(out), "html_selfcheck.json")
    with open(check_path, "w", encoding="utf-8") as f:
        json.dump(check, f, ensure_ascii=False, indent=2)
    print(f"[line-stability] html {os.path.getsize(out)}B pass={check['pass']}")
    return 0 if check["pass"] else 3


if __name__ == "__main__":
    sys.exit(main())
