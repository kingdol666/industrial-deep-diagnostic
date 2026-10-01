"""report_html.py — deterministic single-file interactive HTML report renderer.

The page is a FAITHFUL rendering of the 9 artifact JSONs (+ read-only raw data
for §7 series): every number on the page is computed here (server-side, from
the artifacts) or drawn from them by the page JS (which only builds SVG and
wires hover/click interactions — it never computes statistics). Zero external
requests: no CDN, no external script/css/img; everything inline.

Discipline:
- No raw open(): all reads/writes via pathlib read_text/write_text/read_bytes.
- All numbers pass through the artifacts (already NaN-cleaned by analyze.py);
  anything this module derives is sanitized with _safe_float (non-finite ->
  None) and rendered as "—" (G7e: no NaN/Infinity/undefined/null in body text).
- Readings (three-line chart captions) are generated HERE from the data —
  deterministic sentences, not template filler.
"""

import datetime
import hashlib
import html
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent          # scripts/doestats
SKILL_DIR = SCRIPT_DIR.parent.parent                  # industrial-doe-analyzer/
REPO_ROOT = SKILL_DIR.parents[2]
IDP_SCRIPTS = REPO_ROOT / ".claude" / "skills" / "industrial-data-processor" / "scripts"
TEMPLATE_PATH = SKILL_DIR / "templates" / "report.html.tmpl"

sys.path.insert(0, str(SCRIPT_DIR))
from doestats import VERSION  # noqa: E402
from doestats import effects_anova  # noqa: E402

ARTIFACTS = [
    "00_input/analysis_context.json",
    "01_profile/data_profile.json",
    "02_analysis/effect_table.json",
    "02_analysis/model.json",
    "02_analysis/correlation_report.json",
    "02_analysis/stability_report.json",
    "03_figures/plot_manifest.json",
    "conclusions/doe_conclusion.json",
    "conclusions/recommendations.json",
]
REQUIRED_BY_MODE = {
    "designed": ["00_input/analysis_context.json", "01_profile/data_profile.json",
                 "02_analysis/effect_table.json", "02_analysis/model.json",
                 "03_figures/plot_manifest.json", "conclusions/doe_conclusion.json",
                 "conclusions/recommendations.json"],
    "observational": ["00_input/analysis_context.json", "01_profile/data_profile.json",
                      "02_analysis/correlation_report.json", "02_analysis/stability_report.json",
                      "03_figures/plot_manifest.json", "conclusions/doe_conclusion.json",
                      "conclusions/recommendations.json"],
}
SERIES_MAX_POINTS = 2000
CONTOUR_GRID = 25
CONTOUR_MAX_PAIRS = 3
INTERACT_MAX_TERMS = 3
HEATMAP_MAX_PARAMS = 12
DESIGN_TYPE_CN = {
    "full_factorial": "全因子设计",
    "fractional_factorial": "部分因子设计",
    "rsm_ccd": "中心复合设计 (CCD)",
    "rsm_bbd": "Box-Behnken 设计",
    "latin_hypercube": "拉丁超立方 (LHS)",
    "orthogonal_array": "正交表设计",
    "observational": "观察性数据（未匹配任何设计签名）",
}
CHECKLIST_LABELS = [
    ("randomization_ok", "随机化检查（因子 × 运行顺序 ρ）"),
    ("pure_error_df_gt0", "纯误差自由度 > 0（存在重复）"),
    ("resolution_ok", "分辨度 / 设计类型充分"),
    ("balanced", "设计平衡"),
    ("model_adequacy_ok", "模型适切性（失拟不显著且非饱和）"),
    ("anti_spurious_ok", "防伪检查（|r|≥0.3 对无 FAIL）"),
]
MODE_SECTIONS = {
    "designed": [("sec-hero", "10 秒结论"), ("sec-0", "导读"), ("sec-1", "数据概貌"),
                 ("sec-2", "模式判定依据"), ("sec-3", "分析流程总览"),
                 ("sec-4", "效应与 ANOVA"), ("sec-5", "模型与残差诊断"),
                 ("sec-6", "响应面与驻点"), ("sec-8", "操作窗口"),
                 ("sec-9", "结论与等级"), ("sec-10", "局限与确认实验"),
                 ("sec-appendix", "附录：工件索引")],
    "observational": [("sec-hero", "10 秒结论"), ("sec-0", "导读"), ("sec-1", "数据概貌"),
                      ("sec-2", "模式判定依据"), ("sec-3", "分析流程总览"),
                      ("sec-6b", "相关与防伪"), ("sec-7", "稳定性与能力"),
                      ("sec-8", "操作窗口"), ("sec-9", "结论与等级"),
                      ("sec-10", "局限与确认实验"), ("sec-appendix", "附录：工件索引")],
}


class _Tmpl:
    """@@NAME@@ token template. A dedicated class (not string.Template):
    CSS braces and JS `${}` stay literal, and the 2-char opening delimiter
    needs an explicit matching close tag to avoid self-echo."""
    _PAT = re.compile(r"@@([A-Za-z_][A-Za-z0-9_]*)@@")

    def __init__(self, template):
        self.template = template

    def substitute(self, mapping=None, **kw):
        merged = dict(mapping or {})
        merged.update(kw)
        return self._PAT.sub(lambda m: str(merged[m.group(1)]), self.template)


# ------------------------------------------------------------------ utils

def _contained(candidate, extra_root=None):
    """Same containment contract as analyze.py (normpath + no traversal + root)."""
    cand = os.path.normpath(os.path.abspath(str(candidate)))
    if any(seg == ".." for seg in cand.replace("/", os.sep).split(os.sep)):
        raise ValueError(f"traversal segment rejected in path: {candidate}")
    roots = [os.path.normpath(str(REPO_ROOT))]
    if extra_root is not None:
        roots.append(os.path.normpath(os.path.abspath(str(extra_root))))
    for root in roots:
        if cand == root or cand.startswith(root + os.sep):
            return Path(cand)
    raise ValueError(f"path outside allowed roots: {candidate}")


def _sha256_path(path):
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


_SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
_FLOAT_RE = re.compile(r"-?\d+\.\d+(?:[eE][+-]?\d+)?")


def _short_float(m):
    """Shorten raw full-precision floats in artifact prose (visual gate):
    1.6176013532478293e-10 -> 1.62×10⁻¹⁰, 0.87123456789 -> 0.8712."""
    try:
        v = float(m.group(0))
    except ValueError:
        return m.group(0)
    a = abs(v)
    if a == 0:
        return "0"
    if a >= 1e5 or a < 1e-4:
        exp = int(math.floor(math.log10(a)))
        mant = v / (10.0 ** exp)
        return f"{mant:.2f}×10{str(exp).translate(_SUP)}"
    return f"{v:.4g}"


def esc(v):
    return _FLOAT_RE.sub(_short_float, html.escape(str(v), quote=True))


def _sf(v):
    """Safe float: None / non-finite -> None (rendered as — later)."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _r6(v):
    f = _sf(v)
    return round(f, 6) if f is not None else None


def fmt(v, digits=4):
    f = _sf(v)
    if f is None:
        return "—"
    if isinstance(v, int) or (isinstance(v, float) and float(v).is_integer() and abs(v) < 1e15):
        return str(int(round(float(v))))
    return f"{f:.{digits}g}"


def _tip(pairs):
    """Tooltip text from (label, value) pairs; None values render as —."""
    lines = [f"{k}: {fmt(v) if not isinstance(v, str) else v}" for k, v in pairs]
    return esc("\n".join(lines))


def _json_for_script(obj):
    """JSON dump safe for embedding in a <script> element."""
    return json.dumps(obj, ensure_ascii=False, allow_nan=False).replace("</", "<\\/")


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _load_df(data_file):
    sys.path.insert(0, str(IDP_SCRIPTS))
    from file_inspect import load_file
    return load_file(str(data_file))


def _downsample(vals, max_points=SERIES_MAX_POINTS):
    """Equal-stride downsample; returns (values, stride, n_total)."""
    n = len(vals)
    if n <= max_points:
        return list(vals), 1, n
    stride = int(math.ceil(n / max_points))
    return list(vals[::stride]), stride, n


def _reading(seen, means, matters):
    return (f'<div class="chart-reading">'
            f'<span class="cr-label">看到了什么</span><span>{seen}</span>'
            f'<span class="cr-label">意味着什么</span><span>{means}</span>'
            f'<span class="cr-label">为何重要</span><span>{matters}</span></div>')


def _chart(fig_id, kind, key, title, reading, note=None):
    note_html = f'<span class="chart-note">{note}</span>' if note else ""
    return (f'<figure class="chart" id="{fig_id}">'
            f'<figcaption class="chart-head"><span class="chart-title">{title}</span>'
            f'{note_html}</figcaption>'
            f'<div class="chart-body" data-chart="{kind}" data-key="{key}"></div>'
            f'{reading}</figure>')


# ------------------------------------------------------------------ builder

class ReportBuilder:
    def __init__(self, run_dir):
        self.run_dir = _contained(run_dir)
        self.art = {}
        for rel in ARTIFACTS:
            p = self.run_dir / rel
            if p.exists():
                try:
                    self.art[rel] = json.loads(p.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    self.art[rel] = None
        self.conclusion = self.art.get("conclusions/doe_conclusion.json") or {}
        self.profile = self.art.get("01_profile/data_profile.json") or {}
        self.ctx = self.art.get("00_input/analysis_context.json") or {}
        self.effect = self.art.get("02_analysis/effect_table.json")
        self.models = self.art.get("02_analysis/model.json")
        self.corr = self.art.get("02_analysis/correlation_report.json")
        self.stab = self.art.get("02_analysis/stability_report.json")
        self.manifest = self.art.get("03_figures/plot_manifest.json") or {"plots": []}
        self.recs = self.art.get("conclusions/recommendations.json") or {}
        self.mode = (self.conclusion.get("analysis_mode")
                     or (self.profile.get("design") or {}).get("mode") or "observational")
        self.design = self.profile.get("design") or {}
        self.sections = []
        self.nav = []
        self.nav_plan = []
        self.rendered = set()
        self.charts = {}
        self.n_charts = 0
        self.df = None
        self.raw_sha = None
        self.meta = {"artifacts": {}}

    # ---------------- helpers
    def add_section(self, sec_id, num, title, body, in_nav=True):
        self.rendered.add(sec_id)
        self.sections.append(
            f'<section class="sec" id="{sec_id}">'
            f'<h2><span class="sec-num">{num}</span>{esc(title)}</h2>'
            f'{body}</section>')
        if in_nav:
            self.nav.append((sec_id, title))

    def add_chart(self, kind, data, title, reading_triplet, note=None, key=None):
        self.n_charts += 1
        cid = f"chart-{self.n_charts:02d}"
        key = key or cid
        self.charts[key] = data
        seen, means, matters = reading_triplet
        return _chart(cid, kind, key, title, _reading(seen, means, matters), note)

    # ---------------- load raw data (read-only, for §7 series)
    def load_raw(self):
        data_path = self.profile.get("data_path")
        if not data_path:
            return
        try:
            f = _contained(data_path)
            self.df = _load_df(f)
            self.raw_sha = _sha256_path(f)
        except (ValueError, FileNotFoundError, OSError):
            self.df = None

    # ---------------- HERO
    def sec_hero(self):
        conc = self.conclusion
        grade = conc.get("evidence_grade") or "—"
        grade_cls = {"A": "g-green", "A-": "g-gold", "B": "g-warm"}.get(grade, "g-warm")
        findings = conc.get("key_findings") or []
        card = conc.get("downstream_usage_card") or {}
        lims = conc.get("limitations") or []
        top_lim = lims[0] if lims else "当前没有记录在案的限制"
        items = []
        for f in findings[:3]:
            items.append(f'<li><span class="kf-id">{esc(f.get("id") or "")}</span>'
                         f'{esc(f.get("statement") or "")}'
                         f'<span class="mono kf-q">q={fmt(f.get("fdr_q"))}</span></li>')
        body = f"""
<div class="hero-card">
  <div class="hero-badges">
    <span class="grade-badge {grade_cls}" title="证据等级（checklist 计算）">{esc(grade)}</span>
    <span class="mode-badge">{esc("designed" if self.mode == "designed" else "observational")} · {esc(DESIGN_TYPE_CN.get(conc.get("design_type") or self.design.get("design_type"), str(conc.get("design_type") or self.design.get("design_type") or "—")))}</span>
    <span class="mono hero-meta">script v{esc(VERSION)} · {esc((conc.get("generated_at") or "—")[:19])}</span>
  </div>
  <div class="hero-grid">
    <div class="hero-main">
      <h3 class="hero-sub">前三条关键发现（脚本产出，agent 仅解读）</h3>
      <ul class="hero-findings">{''.join(items) or '<li>— 无关键发现（见 §10 局限）</li>'}</ul>
    </div>
    <div class="hero-side">
      <div class="hero-num"><b>{fmt(card.get("n_windows"), 0)}</b><span>操作窗口</span></div>
      <div class="hero-num"><b>{fmt(card.get("n_confirmations"), 0)}</b><span>需确认试验</span></div>
      <div class="hero-num"><b>{fmt(card.get("n_watchlist"), 0)}</b><span>观察清单条目</span></div>
    </div>
  </div>
  <div class="hero-limit"><span class="cr-label">最重要限制</span>{esc(top_lim)}</div>
</div>"""
        self.add_section("sec-hero", "★", "10 秒结论", body)

    # ---------------- §0 导读
    def sec_0(self):
        rows = "".join(
            f'<li><a href="#{sid}">{esc(title)}</a></li>' for sid, title in self.nav_plan)
        num_note = ("章节编号为全局编号，按模式裁剪：observational 模式不产生设计实验章节 "
                    "§4–§6，designed 模式不产生观测章节 §6b–§7 — 因此各自存在一次跳号，属预期。")
        body = f"""
<div class="twocol">
<div>
<h3 class="block-title">三层读法</h3>
<ol class="read-layers">
<li><b>10 秒</b> — 只看上方 10 秒结论卡：等级徽标、前三条发现、窗口/确认数与最重要限制。</li>
<li><b>1 分钟</b> — 顺着左侧导航读 §2（这个结论凭什么在 designed/observational 档）→ §9（等级四门）→ §10（必须做什么才能闭环）。</li>
<li><b>深读</b> — 在证据章节（§4–§7 按模式裁剪）逐图核对：每张图都带三行读图，悬停可查看每个点/格/带的完整统计明细。</li>
</ol>
<p class="body-note">本页由脚本确定性渲染 9 个工件 JSON，页面内不做任何统计计算；数字如与工件不符即视为被篡改（附录含每个工件的 sha256）。</p>
</div>
<div>
<h3 class="block-title">章节地图（本报告模式：{esc(self.mode)}）</h3>
<ul class="chap-map">{rows}</ul>
<p class="body-note">{num_note}</p>
</div>
</div>"""
        sec = (f'<section class="sec" id="sec-0"><h2><span class="sec-num">§0</span>导读</h2>{body}</section>')
        self.sections.append(sec)
        self.nav.append(("sec-0", "导读"))
        self.rendered.add("sec-0")

    # ---------------- §1 数据概貌
    def sec_1(self):
        prof = self.profile
        role_cls = {"response": "r-response", "factor": "r-factor", "block": "r-block",
                    "covariate": "r-covariate", "index": "r-index", "ignore": "r-ignore"}
        sev_cls = {"warn": "sev-warn", "critical": "sev-crit", "info": "sev-info"}
        cols = prof.get("columns") or []
        rows = "".join(
            f'<tr><td class="mono">{esc(c.get("name"))}</td>'
            f'<td><span class="role-chip {role_cls.get(c.get("role"), "r-ignore")}">{esc(c.get("role"))}</span></td>'
            f'<td class="mono">{esc(c.get("dtype"))}</td>'
            f'<td class="num">{fmt(c.get("n_missing"), 0)}</td>'
            f'<td class="num">{fmt(c.get("n_unique"), 0)}</td></tr>'
            for c in cols)
        caveats = prof.get("caveats") or []
        cav = "".join(
            f'<li><span class="sev-badge {sev_cls.get(c.get("severity"), "sev-info")}">{esc(c.get("severity") or "info")}</span>'
            f'<b class="mono">{esc(c.get("code") or "")}</b> {esc(c.get("message") or "")}</li>'
            for c in caveats)
        q = prof.get("quality") or {}
        body = f"""
<p class="body-l">数据文件 <code class="mono">{esc(prof.get("data_path") or "—")}</code>：
<b>{fmt(prof.get("n_rows"), 0)}</b> 行 × <b>{fmt(prof.get("n_cols"), 0)}</b> 列
（重复行 {fmt(q.get("duplicate_rows"), 0)}，高缺失列 {esc(",".join(q.get("high_missing_cols") or []) or "无")}）。</p>
<figure class="chart"><figcaption class="chart-head"><span class="chart-title">列角色面板</span></figcaption>
<table class="stat-table"><thead><tr><th>列名</th><th>角色</th><th>类型</th><th>缺失</th><th>唯一值</th></tr></thead>
<tbody>{rows or '<tr><td colspan="5">—</td></tr>'}</tbody></table>
{_reading("每列按 profile 赋予的角色着色：响应（蓝）/因子（绿）/区组·协变量（金）/索引（灰）。",
          "角色由 user context 或自动推断赋予，决定它进入模型的位置。",
          "看错角色（例如把运行序当成因子）是工况分析最常见的翻车点。")}</figure>
<h3 class="block-title">质量警示（caveats）</h3>
<ul class="caveat-list">{cav or '<li class="t3">无（本轮未检出结构性质量警示）</li>'}</ul>"""
        self.add_section("sec-1", "§1", "数据概貌", body)

    # ---------------- §2 模式判定依据
    def sec_2(self):
        d = self.design
        caveats = self.profile.get("caveats") or []
        sig_rows = [
            ("design_type", DESIGN_TYPE_CN.get(d.get("design_type"), str(d.get("design_type") or "—"))),
            ("runs × 因子列 × 不同组合", f"{fmt(d.get('n_runs'), 0)} × {fmt(d.get('n_factor_cols'), 0)} × {fmt(d.get('n_distinct_combos'), 0)}"),
            ("resolution / 生成子", (f"{d.get('resolution')}（定义关系 {' × '.join(d.get('defining_relation') or []) or '—'}）"
                                     if d.get("resolution") else "—") +
                                     (f"；生成子：{'; '.join(d.get('generators') or [])}" if d.get("generators") else "")),
            ("中心点 / 轴点 / α", f"{fmt(d.get('center_points'), 0)} / {fmt(d.get('axial_points'), 0)} / {fmt(d.get('alpha_axial'), 3)}"),
            ("balanced / balance_ratio", f"{fmt(d.get('balanced'))} / {fmt(d.get('balance_ratio'), 3)}"),
            ("replicates / 最大|因子相关|", f"{fmt(d.get('replicates'), 0)} / {fmt(d.get('max_abs_factor_corr'), 3)}"),
        ]
        sig_html = "".join(
            f'<tr><th>{esc(k)}</th><td class="mono">{esc(v)}</td></tr>' for k, v in sig_rows)
        chains = d.get("alias_chains") or {}
        chain_items = "".join(
            f'<li><span class="mono">{esc(term)}</span> ← '
            f'<span class="mono t2">{esc(", ".join(aliases) or "—")}</span></li>'
            for term, aliases in list(chains.items())[:10])
        if chain_items:
            chain_html = (f'<details class="alias-probe"><summary>别名链下探表'
                          f'（{len(chains)} 条，展开前 10 条）</summary><ul class="alias-list">{chain_items}</ul></details>')
        else:
            chain_html = '<p class="t3">无别名链记录（全因子 / RSM / 观察档）</p>'
        notes = "".join(f'<li class="mono t2">{esc(n)}</li>' for n in (d.get("detection_notes") or []))
        cards = []
        for code, title, note in (
                ("NON_RANDOMIZED", "未随机化检查卡", "因子与运行顺序强相关 — 效应与时序混杂，所有窗口执行前必须确认试验。"),
                ("UNBALANCED_DESIGN", "不平衡设计卡", "extra-SS ANOVA 语义：正交设计下等价经典 Type-II；不平衡时 p 值依赖编码方式。")):
            hits = [c for c in caveats if c.get("code") == code]
            for h in hits:
                ev = h.get("evidence") or {}
                ev_txt = "；".join(f"{k}={fmt(v)}" for k, v in ev.items()) if ev else ""
                cards.append(f'<div class="check-card check-warn"><b>{title}</b>'
                             f'<p>{esc(h.get("message") or "")}</p>'
                             + (f'<p class="mono t3">{esc(ev_txt)}</p>' if ev_txt else "")
                             + f'<p class="t3">{note}</p></div>')
        override = ""
        if d.get("mode_overridden"):
            override = ('<div class="check-card check-info"><b>mode_override 生效</b>'
                        '<p>用户 context 将模式覆盖为 ' + esc(d.get("mode")) +
                        '（证据等级仍由 checklist 独立计算，不受覆盖影响）。</p></div>')
        sort_card = ""
        if self.mode == "observational":
            sv = (self.corr or {}).get("sorting_validation") or {}
            state = "g-green" if sv.get("time_sorted") else "g-warm"
            sort_card = (f'<div class="check-card"><b>时序校验（sorting_validation）</b>'
                         f'<p><span class="sev-badge {state}">{"已按时间排序" if sv.get("time_sorted") else "未排序/无法确认"}</span> '
                         f'时间列 <span class="mono">{esc(sv.get("time_column") or "—")}</span>，'
                         f'{fmt(sv.get("n_rows"), 0)} 行；{esc(sv.get("message") or "")}</p>'
                         f'<p class="t3">观察档窗口取自稳态段 — 数据未按时间排序时稳态/变点结果不可信。</p></div>')
        verdict = ("检测到试验设计签名 → 判定 <b>designed</b>（效应可作因果级解读，受别名约束）"
                   if self.mode == "designed" else
                   "未匹配任何试验设计签名 → 保守判定 <b>observational</b>（全部结论为相关级证据）")
        why = f'<p class="body-l">判定信号摘要：{verdict}。</p>'
        body = (why + f'<table class="stat-table"><tbody>{sig_html}</tbody></table>'
                + f'<h3 class="block-title">判定过程记录（detection_notes）</h3><ul class="mono-list">{notes or "<li class=t3>—</li>"}</ul>'
                + chain_html + override + "".join(cards) + sort_card)
        self.add_section("sec-2", "§2", "模式判定依据", body)

    # ---------------- §3 流程总览（静态 SVG 流程带）
    def sec_3(self):
        steps = [
            ("Phase 0/1", "profile", "清单 + 探查 + 设计检测", "run_manifest · data_profile"),
            ("分派", "mode", "designed / observational", "模式决定方法链"),
            ("Phase 2", "stats", "确定性统计（numpy/scipy）", "effect_table · model · correlation · stability"),
            ("Phase 3", "agent", "agent 仅解读，不改数", "key_findings 措辞"),
            ("G1–G7", "gate", "质量门（Node 独立复核）", "gate PASS 才允许交付"),
            ("报告", "report", "本页 report.html", "9 工件确定性渲染"),
        ]
        W, H, bh, gap = 1180, 128, 92, 28
        bw = (W - gap * (len(steps) - 1)) / len(steps)
        parts = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="分析流程带">']
        colors = {"profile": "#1e3a54", "mode": "#8a6d3b", "stats": "#1e3a54",
                  "agent": "#8a6d3b", "gate": "#2d7d4f", "report": "#1e3a54"}
        for i, (ph, key, t1, t2) in enumerate(steps):
            x = i * (bw + gap)
            c = colors[key]
            parts.append(
                f'<rect x="{x:.0f}" y="16" width="{bw:.0f}" height="{bh}" rx="8" fill="#ffffff" stroke="{c}" stroke-width="1.4"/>'
                f'<text x="{x + bw / 2:.0f}" y="46" text-anchor="middle" font-size="16" font-weight="700" fill="{c}">{esc(ph)}</text>'
                f'<text x="{x + bw / 2:.0f}" y="68" text-anchor="middle" font-size="13.5" fill="#1a1a1a">{esc(t1)}</text>'
                f'<text x="{x + bw / 2:.0f}" y="88" text-anchor="middle" font-size="12" fill="#555">{esc(t2)}</text>')
            if i < len(steps) - 1:
                ax = x + bw + 3
                parts.append(
                    f'<line x1="{ax:.0f}" y1="62" x2="{ax + gap - 7:.0f}" y2="62" stroke="#1a1a1a" stroke-width="1.4"/>'
                    f'<polygon points="{ax + gap - 7:.0f},57 {ax + gap - 7:.0f},67 {ax + gap - 1:.0f},62" fill="#1a1a1a"/>')
        parts.append("</svg>")
        body = (f'<figure class="chart"><figcaption class="chart-head"><span class="chart-title">Phase 0 → 报告 流程带</span></figcaption>'
                + "".join(parts)
                + _reading("六段流程：profile 探查 → 模式分派 → 确定性统计 → agent 解读 → G1–G7 质量门 → 本页渲染。",
                           "脚本算数（numpy/scipy 固定口径），agent 只改措辞；质量门用独立 Node 进程复核工件。",
                           "数字的产出与审计分离 — 页面上任何统计量都能在附录工件里找到原值与 sha256。")
                + "</figure>")
        self.add_section("sec-3", "§3", "分析流程总览", body)

    # ---------------- §4 效应与 ANOVA（designed）
    def sec_4(self):
        fams = (self.effect or {}).get("families") or []
        if not fams:
            return
        tabs, blocks = [], []
        for fam in fams:
            resp = fam.get("response")
            tests = [t for t in fam.get("tests", []) if t.get("std_err") not in (None, 0)]
            tests.sort(key=lambda t: abs((t.get("coefficient") or 0) / t["std_err"]), reverse=True)
            if not tests:
                continue
            df_r = fam.get("df_resid")
            from scipy import stats as sps
            ref = float(sps.t.ppf(0.975, df_r)) if df_r else None
            rows = []
            for t in tests:
                coef, se = t.get("coefficient"), t.get("std_err")
                tval = _sf(abs(coef / se)) if (coef is not None and se) else None
                q = _sf(t.get("q_value_bh"))
                rows.append({"term": t.get("term"), "t": _r6(tval), "coef": _r6(coef),
                             "se": _r6(se), "q": q, "eta": _sf(t.get("partial_eta_squared")),
                             "p": _sf(t.get("p_value")), "sig": bool(q is not None and q < 0.05),
                             "rank": t.get("pareto_rank")})
            n_over = sum(1 for r in rows if ref and r["t"] is not None and r["t"] > ref)
            n_sig = sum(1 for r in rows if r["sig"])
            pareto = self.add_chart(
                "pareto", {"rows": rows, "ref": _r6(ref), "response": resp},
                f"Pareto 图 — {resp}（|t| = |系数|/标准误）",
                (f"{len(rows)} 个项按 |t| 排序；{n_over} 个越过 t*={fmt(ref, 3)} 参考线（红虚线）",
                 f"其中 {n_sig} 个 q(BH)<0.05（橙色）— 在多重校正后仍显著",
                 "Pareto 前几项是后续窗口/响应面的候选驱动因子；参考线右边的项才值得逐个解读"),
                key=f"pareto:{resp}")
            eta_rows = sorted((r for r in rows if r["eta"] is not None),
                              key=lambda r: r["eta"], reverse=True)[:8]
            eta_html = ""
            if eta_rows:
                eta_html = self.add_chart(
                    "eta", {"rows": eta_rows, "response": resp},
                    f"η² 贡献条形 — {resp}（partial η²，前 8 项）",
                    (f"最大贡献项 {esc(eta_rows[0]['term'])}（η²={fmt(eta_rows[0]['eta'], 3)}）",
                     "η² 衡量该项解释的响应变异占比，可与显著性正交地比较重要性",
                     "小 p 值 + 大 η² 才值得投入工艺调整；只有 p 小的项效应量可能撑不起动作"),
                    key=f"eta:{resp}")
            # ANOVA table
            trs = []
            for t in fam.get("tests", []):
                q = t.get("q_value_bh")
                sig = q is not None and q < 0.05
                status = ""
                if t.get("estimable") is False:
                    reason = t.get("reason_code") or "excluded"
                    tip = t.get("alias_chain") or []
                    status = (f'<span class="sev-badge sev-warn" data-tip="{_tip([("别名链", ", ".join(tip)) if tip else ("原因", reason)])}">'
                              f'{esc(reason)}</span>')
                elif sig:
                    status = '<span class="sev-badge sev-ok">q&lt;0.05</span>'
                trs.append(
                    f'<tr data-sig="{1 if sig else 0}">'
                    f'<td class="mono">{esc(t.get("term"))}</td>'
                    f'<td class="num">{fmt(t.get("coefficient"))}</td>'
                    f'<td class="num">{fmt(t.get("std_err"))}</td>'
                    f'<td class="num">{fmt(t.get("f_stat"), 3)}</td>'
                    f'<td class="num">{fmt(t.get("df"), 0)}</td>'
                    f'<td class="num">{fmt(t.get("ss_extra_ss"), 3)}</td>'
                    f'<td class="num">{fmt(t.get("p_value"), 3)}</td>'
                    f'<td class="num {"hi" if sig else "lo"}">{fmt(q, 3)}</td>'
                    f'<td class="num">{fmt(t.get("partial_eta_squared"), 3)}</td>'
                    f'<td>{status or "—"}</td></tr>')
            anova = (f'<figure class="chart"><figcaption class="chart-head"><span class="chart-title">ANOVA 全表 — {esc(resp)}</span>'
                     f'<label class="toggle"><input type="checkbox" class="toggle-sig"/>只看显著</label></figcaption>'
                     f'<div class="table-wrap"><table class="stat-table anova-table"><thead><tr>'
                     f'<th>项</th><th>系数</th><th>SE</th><th>F</th><th>df</th><th>SS(extra)</th>'
                     f'<th>p</th><th>q(BH)</th><th>partial η²</th><th>状态</th></tr></thead>'
                     f'<tbody>{"".join(trs)}</tbody></table></div>'
                     + _reading(f"{len(trs)} 行 = 全部模型项；非可估行带 aliased/saturated/pooled 徽标（悬停看别名链）。",
                                "extra-SS 单删法口径：正交设计下等价 Type-II；不平衡设计 p 值依赖编码（见 §2 警示卡）。",
                                "这是 §4 所有图的数据源 — 页面只做过滤与排序，不做任何重算。")
                     + "</figure>")
            mde_card = ""
            if fam.get("mde") is not None:
                mde_card = (f'<div class="check-card check-info"><b>MDE — 最小可检效应（{esc(resp)}）</b>'
                            f'<p>2 水平编码主效应在 α=0.05、power=0.8 下能检出的最小编码系数约为 '
                            f'<span class="mono">{fmt(fam.get("mde"), 3)}</span>（n={fmt(fam.get("n"), 0)}，df_pe={fmt(fam.get("df_pure_error"), 0)}）。</p>'
                            f'<p class="t3">低于 MDE 的「不显著」可能只是试验规模不足 — 不显著 ≠ 无效应。</p></div>')
            blocks.append(
                f'<div class="resp-block{" resp-active" if not blocks else ""}" data-response="{esc(resp)}"><h3 class="block-title">响应：{esc(resp)}</h3>'
                f'{pareto}{eta_html}{anova}{mde_card}</div>')
        first = (fams[0].get("response") if fams else "")
        tab_html = ""
        if len({f.get("response") for f in fams}) > 1:
            btns = "".join(
                f'<button class="tab-btn{" active" if f.get("response") == first else ""} '
                f'data-target="{esc(f.get("response"))}">{esc(f.get("response"))}</button>'
                for f in fams)
            tab_html = f'<div class="tab-bar"><span class="t3">响应切换：</span>{btns}</div>'
        body = (f'<p class="body-l">效应估计口径：偏差编码 + extra-SS 单删法 + BH 校正（详见 §3 流程与 §2 警示卡）。</p>'
                + tab_html + "".join(blocks))
        self.add_section("sec-4", "§4", "效应与 ANOVA", body)

    # ---------------- §5 模型与残差诊断（designed）
    def sec_5(self):
        models = self.models or []
        if not models:
            return
        blocks = []
        for m in models:
            resp = m.get("response")
            rd = m.get("residual_diagnostics") or {}
            lof = m.get("lack_of_fit") or {}
            cards = [
                ("R²", fmt(m.get("r_squared"), 3), f"调整后 {fmt(m.get('adj_r_squared'), 3)}"),
                ("Q² (LOO)", fmt(m.get("q_squared_loo"), 3), esc(m.get("q_squared_note") or "hat 矩阵留一交叉验证")),
                ("失拟检验", f"p={fmt(lof.get('p_value'), 3)}" if lof.get("estimable") else "不可估",
                 esc(lof.get("reason") or (f"F={fmt(lof.get('f_stat'), 3)}（不显著 → 模型阶数够用）" if lof.get("estimable") else "无纯误差重复"))),
                ("饱和/池化", "是" if m.get("saturated") else "否",
                 "池化项: " + (", ".join(m.get("pooled_terms") or []) or "无")),
            ]
            cards_html = "".join(
                f'<div class="kpi"><span class="kpi-label">{k}</span>'
                f'<span class="kpi-value mono">{v}</span><span class="kpi-note">{n}</span></div>'
                for k, v, n in cards)
            lev = ""
            if rd.get("max_leverage") is not None:
                lev = (f'<div class="check-card"><b>杠杆点 / 影响点摘要</b>'
                       f'<p>max leverage = <span class="mono">{fmt(rd.get("max_leverage"), 3)}</span>'
                       f'（截断 2p/n = <span class="mono">{fmt(rd.get("leverage_cutoff_2p_over_n"), 3)}</span>，'
                       f'超限 {fmt(rd.get("n_leverage_gt"), 0)} 点）；'
                       f'max Cook\'s D = <span class="mono">{fmt(rd.get("max_cooks_d"), 4)}</span>；'
                       f'残差 &gt;3σ 共 {fmt(rd.get("n_high_residual_abs_gt3sigma"), 0)} 点。</p>'
                       f'<p class="t3">高杠杆 + 大 Cook\'s D 的点对系数有不成比例的影响 — 删除重算可检验结论稳健性。</p></div>')
            resid_chart = ""
            preview = rd.get("residuals_preview") or []
            if preview:
                resid_vals = [p["resid"] for p in preview if p.get("resid") is not None]
                fitted_vals = [p["yhat"] for p in preview if p.get("yhat") is not None]
                qq = _qq_pairs(resid_vals)
                counts, edges = _hist(resid_vals)
                note = (f"共 {fmt(rd.get('n'), 0)} 行" +
                        (f"，等步长降采样 1/{rd.get('preview_stride')}（{len(preview)} 点）"
                         if rd.get("preview_truncated") else ""))
                resid_chart = self.add_chart(
                    "resid",
                    {"fitted": fitted_vals, "resid": resid_vals, "qq": qq,
                     "hist": {"counts": counts, "edges": edges},
                     "order": list(range(len(resid_vals))),
                     "rows": preview, "response": resp},
                    f"残差四联图 — {resp}", 
                    ("左上：残差对拟合值应无喇叭形/系统弯曲；右上：QQ 点应沿对角线；左下：直方应近似对称；右下：残差对运行序应无趋势（随机化检查）",
                     "任何一格违背 → 误差结构假设存疑，p 值与窗口置信界都打折扣",
                     "残差诊断是否通过，直接决定 §4 结论能被信任到什么程度"),
                    note=note, key=f"resid:{resp}")
            blocks.append(
                f'<div class="resp-block{" resp-active" if not blocks else ""}" data-response="{esc(resp)}"><h3 class="block-title">响应：{esc(resp)}</h3>'
                f'<div class="kpi-row">{cards_html}</div>{resid_chart}{lev}</div>')
        first = (models[0].get("response") if models else "")
        tab_html = ""
        if len(models) > 1:
            btns = "".join(
                f'<button class="tab-btn{" active" if m.get("response") == first else ""} '
                f'data-target="{esc(m.get("response"))}">{esc(m.get("response"))}</button>'
                for m in models)
            tab_html = f'<div class="tab-bar"><span class="t3">响应切换：</span>{btns}</div>'
        pooled_note = ""
        spec = ((self.effect or {}).get("model_spec") or {})
        pooled = spec.get("pooled_terms") or []
        if pooled:
            pooled_note = (f'<p class="body-note">跨响应池化项（饱和策略 C3）：'
                           f'<span class="mono">{esc(", ".join(pooled))}</span> — 只报系数不报 p（不虚构自由度）。</p>')
        body = tab_html + pooled_note + "".join(blocks)
        self.add_section("sec-5", "§5", "模型与残差诊断", body)

    # ---------------- §6 响应面与驻点（designed, 有二次模型时）
    def sec_6(self):
        models = [m for m in (self.models or []) if m.get("predictor")]
        blocks = []
        any_chart = False
        for m in models:
            resp = m.get("response")
            predict = effects_anova.rebuild_predictor(m.get("predictor"))
            if predict is None:
                continue
            has_quad = any(s["fn"] == "square" or (s["fn"] == "product" and len(s["inputs"]) == 2)
                           for t in m["predictor"]["terms"] for s in t["specs"])
            if not has_quad:
                continue
            info = self._factor_anchor_info(m)
            ordered = self._pareto_order(m, resp)
            charts_html = ""
            pairs = [(a, b) for i, a in enumerate(ordered[:3])
                     for b in ordered[:3][i + 1:]][:CONTOUR_MAX_PAIRS]
            for (f1, f2) in pairs:
                z, axes = self._contour_grid(predict, info, f1, f2)
                if z is None:
                    continue
                st = (m.get("stationary_point") or {})
                stp = None
                if st.get("coded") and f1 in st["coded"] and f2 in st["coded"]:
                    stp = {"x": st["coded"][f1], "y": st["coded"][f2],
                           "classification": st.get("classification") or "—",
                           "inside": bool(st.get("inside_design_region"))}
                st_txt = ""
                if stp:
                    cls_cn = {"max": "极大", "min": "极小", "saddle": "鞍点"}.get(stp["classification"], stp["classification"])
                    st_txt = f"驻点分类 {cls_cn}"
                flat = [v for row in z for v in row if v is not None]
                if not flat:
                    continue
                charts_html += self.add_chart(
                    "contour",
                    {"z": z, "xraw": axes[0], "yraw": axes[1],
                     "xlabel": f1, "ylabel": f2, "st": stp, "response": resp},
                    f"预测响应面等高线 — {resp}（{f1} × {f2}，其余因子取中心）",
                    (f"颜色由低（墨蓝）到高（暖橙）；网格 {CONTOUR_GRID}×{CONTOUR_GRID}，"
                     f"由 model.json 的 predict_raw 预计算；{st_txt or '未标注驻点'}",
                     "等高线密集处响应变化快 — 是工艺最敏感的方向；驻点若为鞍点/域外则只能取盒内最优",
                     "看面找最优区，而不是只看一维主效应 — 交互与曲率只有在面上才可见"),
                    key=f"contour:{resp}:{f1}:{f2}")
                any_chart = True
            # interaction line charts (kept 2FI terms)
            terms_2fi = []
            for fam in (self.effect or {}).get("families", []):
                if fam.get("response") != resp:
                    continue
                for t in fam.get("tests", []):
                    if t.get("order") == 2 and ":" in (t.get("term") or "") and t.get("estimable"):
                        terms_2fi.append(t)
            terms_2fi.sort(key=lambda t: (t.get("q_value_bh") is None,
                                          -(t.get("partial_eta_squared") or 0)))
            for t in terms_2fi[:INTERACT_MAX_TERMS]:
                data = self._interaction_lines(predict, info, t["term"], resp)
                if data is None:
                    continue
                q = _sf(t.get("q_value_bh"))
                charts_html += self.add_chart(
                    "interact", data,
                    f"交互效应线图 — {resp}（{t['term']}，q={fmt(q, 3)}）",
                    (f"每个系列是一个 {esc(data['sname'])} 水平；线不平行 → 存在交互",
                     "线交叉/张合意味着一个因子的最优设置随另一因子变化 — 单因子窗口会误导",
                     "存在显著交互时，§8 的单因子窗口必须配套使用（窗口随另一因子水平移动）"),
                    key=f"interact:{resp}:{t['term']}")
                any_chart = True
            if charts_html:
                blocks.append(f'<div class="resp-block{" resp-active" if not blocks else ""}" data-response="{esc(resp)}">'
                              f'<h3 class="block-title">响应：{esc(resp)}</h3>{charts_html}</div>')
        if not any_chart:
            return
        first = (models[0].get("response") if models else "")
        tab_html = ""
        if len(blocks) > 1:
            btns = "".join(
                f'<button class="tab-btn{" active" if m.get("response") == first else ""} '
                f'data-target="{esc(m.get("response"))}">{esc(m.get("response"))}</button>'
                for m in models if m.get("predictor"))
            tab_html = f'<div class="tab-bar"><span class="t3">响应切换：</span>{btns}</div>'
        body = (f'<p class="body-l">z 值由 model.json 序列化的 predict_raw 在 {CONTOUR_GRID}×{CONTOUR_GRID} 网格上预计算 — '
                f'页面只负责绘制，不做任何浏览器端统计。</p>' + tab_html + "".join(blocks))
        self.add_section("sec-6", "§6", "响应面与驻点", body)

    def _factor_anchor_info(self, m):
        """Anchor raw values + per-factor coding info rebuilt from model.json's
        serialized predictor (numeric mean/half_range; categorical level set)."""
        info = {}
        levels_by_factor = {}
        for name, spec in (m["predictor"].get("base") or {}).items():
            f = spec["factor"]
            if spec["kind"] == "numeric_main":
                info[f] = spec
            else:
                levels_by_factor.setdefault(f, set()).update(
                    [spec.get("level"), spec.get("reference")])
        for f, lv in levels_by_factor.items():
            ls = sorted([x for x in lv if x is not None], key=str)
            if ls:
                info[f] = {"kind": "level", "factor": f, "levels": ls}
        anchor = {}
        for f, spec in info.items():
            if spec["kind"] == "numeric_main":
                anchor[f] = spec.get("mean")
            else:
                ls = spec["levels"]
                anchor[f] = ls[len(ls) // 2]
        return {"info": info, "anchor": anchor}

    def _pareto_order(self, m, resp):
        """Core factors ordered by the response's Pareto ranking (rank asc)."""
        factors = []
        for name, spec in (m["predictor"].get("base") or {}).items():
            if spec["kind"] == "numeric_main" and spec["factor"] not in factors:
                factors.append(spec["factor"])
        tests = []
        for fam in (self.effect or {}).get("families", []):
            if fam.get("response") == resp:
                tests = [t for t in fam.get("tests", []) if t.get("pareto_rank")]
        tests.sort(key=lambda t: t["pareto_rank"])
        order = []
        for t in tests:
            for f in (t.get("term") or "").split(":"):
                if f in factors and f not in order:
                    order.append(f)
        return [f for f in order if f in factors] + [f for f in factors if f not in order]

    def _contour_grid(self, predict, info, f1, f2):
        i1, i2 = info["info"].get(f1), info["info"].get(f2)
        if not i1 or not i2 or i1["kind"] != "numeric_main" or i2["kind"] != "numeric_main":
            return None, None
        coded = np.linspace(-1, 1, CONTOUR_GRID)
        z = []
        for cv in coded:
            row = []
            for cc in coded:
                raw = dict(info["anchor"])
                raw[f1] = i1["mean"] + float(cv) * i1["half_range"]
                raw[f2] = i2["mean"] + float(cc) * i2["half_range"]
                yv = _sf(predict(raw))
                row.append(_r6(yv))
            z.append(row)
        ticks = [i1["mean"] + float(v) * i1["half_range"] for v in (-1, -0.5, 0, 0.5, 1)]
        ticky = [i2["mean"] + float(v) * i2["half_range"] for v in (-1, -0.5, 0, 0.5, 1)]
        return z, [ticks, ticky]

    def _interaction_lines(self, predict, info, term, resp):
        fa, fb = term.split(":")
        ia, ib = info["info"].get(fa), info["info"].get(fb)
        if not ia or not ib:
            return None
        anchor = dict(info["anchor"])
        # x-axis = fa levels
        if ia["kind"] == "numeric_main":
            xcoded = [-1, -0.5, 0, 0.5, 1]
            xt = [{"coded": c, "raw": _r6(ia["mean"] + c * ia["half_range"])} for c in xcoded]
        else:
            xt = [{"coded": None, "level": lv} for lv in ia.get("levels") or []]
        if not xt:
            return None
        # series = fb levels
        if ib["kind"] == "numeric_main":
            slevels = [(-1.0, "低(-1)"), (1.0, "高(+1)")]
        else:
            slevels = [(lv, lv) for lv in ib.get("levels") or []]
        if not slevels:
            return None
        series = []
        for sv, sname in slevels:
            vals = []
            for x in xt:
                raw = dict(anchor)
                if ia["kind"] == "numeric_main":
                    raw[fa] = ia["mean"] + x["coded"] * ia["half_range"]
                else:
                    raw[fa] = x["level"]
                if ib["kind"] == "numeric_main":
                    raw[fb] = ib["mean"] + float(sv) * ib["half_range"]
                else:
                    raw[fb] = sv
                vals.append(_r6(_sf(predict(raw))))
            if any(v is None for v in vals):
                return None
            series.append({"name": sname, "values": vals})
        return {"xt": xt, "series": series, "xlabel": fa, "sname": fb, "ylabel": resp,
                "xnumeric": ia["kind"] == "numeric_main"}

    # ---------------- §6b 相关与防伪（observational）
    def sec_6b(self):
        corr = self.corr
        if not corr:
            return
        pairs = [p for p in (corr.get("pairs") or [])
                 if (p.get("q_value_bh") is not None and p["q_value_bh"] < 0.05)
                 or p.get("anti_spurious_verdict") != "FAIL"]
        if not pairs:
            body = ('<p class="body-l">没有通过筛选（q&lt;0.05 或非 FAIL）的相关对 — '
                    '原始相关全部不可信，无可用观察档证据。</p>')
            self.add_section("sec-6b", "§6b", "相关与防伪", body)
            return
        targets = sorted({p["target"] for p in pairs})
        all_params = sorted({p["parameter"] for p in pairs},
                            key=lambda c: -max(abs(p.get("r") or 0) for p in pairs
                                               if p["parameter"] == c))
        params = all_params[:HEATMAP_MAX_PARAMS]
        truncated = len(all_params) > HEATMAP_MAX_PARAMS
        cells = []
        for p in pairs:
            if p["parameter"] in params and p["target"] in targets:
                detail = {
                    "r": _sf(p.get("r")), "p": _sf(p.get("p_value")), "q": _sf(p.get("q_value_bh")),
                    "n": p.get("n"), "best_lag": p.get("best_lag"),
                    "detrended_r": _sf(p.get("detrended_r")),
                    "trend_confounded": bool(p.get("trend_confounded")),
                    "outlier": (p.get("verdicts") or {}).get("outlier_sensitivity"),
                    "loo": (p.get("verdicts") or {}).get("loo_leverage"),
                    "simpson": (p.get("verdicts") or {}).get("simpson"),
                    "verdict": p.get("anti_spurious_verdict"),
                }
                cells.append({"ti": targets.index(p["target"]),
                              "pi": params.index(p["parameter"]),
                              "r": _sf(p.get("r")), "q": _sf(p.get("q_value_bh")),
                              "verdict": p.get("anti_spurious_verdict"),
                              "tip": _tip([(k, v) for k, v in detail.items()])})
        n_pass = sum(1 for c in cells if c["verdict"] == "PASS")
        n_caution = sum(1 for c in cells if c["verdict"] == "CAUTION")
        heat = self.add_chart(
            "corrheat",
            {"targets": targets, "params": params, "cells": cells,
             "truncated": truncated, "n_total": len(all_params)},
            f"验证相关热图（q&lt;0.05 或非 FAIL 对；悬停看该对完整防伪记录）",
            (f"{len(cells)} 个通过筛选的相关格：PASS {n_pass} / CAUTION {n_caution} / FAIL 已剔除",
             "PASS = 防伪链全过；CAUTION = 存在趋势/离群警示 — 可引用但要确认；FAIL 对已从视图剔除",
             "颜色深浅只代表相关强度，是否可信由防伪裁决决定 — 引用任何相关前先看裁决色环"),
            key="corrheat")
        top = (corr.get("top_contributors") or [])[:10]
        dr2 = ""
        if top:
            dr2 = self.add_chart(
                "dr2", {"rows": [{"label": f"{t['factor']} → {t['response']}",
                                   "value": _sf(t.get("delta_r2"))} for t in top]},
                "留一因子 ΔR² 贡献排名（前 10）",
                (f"最大贡献 {esc(top[0]['factor'])}→{esc(top[0]['response'])}（ΔR²={fmt(top[0].get('delta_r2'), 3)}）",
                 "ΔR² 是把该因子从多元回归中移除后 R² 的降幅 — 衡量边际贡献而非单变量相关",
                 "高 r 低 ΔR² 的因子多为冗余/共线 — 窗口优先落在高 ΔR² 的因子上"),
                key="dr2")
        legend = (f'<div class="check-card check-info"><b>防伪图例</b>'
                  f'<p><span class="sev-badge sev-ok">PASS</span> 滞后补偿 CCF + 去趋势 + 离群留一 + Simpson 分层 全部通过；'
                  f'<span class="sev-badge sev-warn">CAUTION</span> 存在时间趋势/离群敏感 — 结论可用但需确认；'
                  f'<span class="sev-badge sev-crit">FAIL</span> 离群驱动/LOO 不稳/Simpson 悖论 — 已剔除，不得引用。</p>'
                  f'<p class="t3">防伪链实现见 industrial-data-processor anti_spurious（v1 口径），本页只展示其裁决。</p></div>')
        sig = ((corr.get("multiple_testing") or {}).get("total_significant_q05"))
        body = ('<p class="body-note">编号说明：章节编号为全局编号 — observational 模式不产生'
                '设计实验章节 §4–§6，故本章由 §3 直接跳至 §6b（跳号属预期，非内容缺失）。</p>'
                f'<p class="body-l">共 {fmt((corr.get("multiple_testing") or {}).get("total_tests"), 0)} 个原始相关对，'
                f'BH 校正后显著（q&lt;0.05）{fmt(sig, 0)} 个；本节只渲染通过筛选的对。</p>'
                + heat + dr2 + legend)
        self.add_section("sec-6b", "§6b", "相关与防伪", body)

    # ---------------- §7 稳定性/能力（observational）
    def sec_7(self):
        if not self.stab:
            return
        segs = self.stab.get("steady_segments") or []
        cps = {c["response"]: c.get("positions") or []
               for c in (self.stab.get("change_points") or [])}
        caps = {c["response"]: c for c in (self.stab.get("capability") or [])}
        targets = []
        for p in (self.corr or {}).get("pairs", []):
            if p["target"] not in targets:
                targets.append(p["target"])
        if not targets:
            targets = list(caps.keys())[:2]
        blocks = []
        for resp in targets[:2]:
            if self.df is None or resp not in self.df.columns:
                continue
            vals = pd_to_series(self.df[resp])
            series, stride, n_total = _downsample(vals)
            seg_scaled = [{"start": s["start"] // stride, "end": s["end"] // stride,
                           "selected": bool(s.get("selected_for_windows")),
                           "label": f"{s['start']}–{s['end']}"}
                          for s in segs if s.get("end", 0) < n_total]
            cps_scaled = [cp // stride for cp in cps.get(resp, []) if cp < n_total]
            tl = self.add_chart(
                "timeline",
                {"values": [_r6(v) for v in series], "segments": seg_scaled,
                 "cps": cps_scaled, "stride": stride, "n_total": n_total,
                 "response": resp},
                f"稳态时间线 — {resp}" + (f"（降采样 1/{stride}，{len(series)} 点）" if stride > 1 else ""),
                (f"{len(seg_scaled)} 个稳态段（绿色阴影，加深的为入选窗口的段）；虚线为变点位置（{len(cps_scaled)} 个）",
                 "窗口证据只能来自稳态段 — 段外数据含过渡/漂移，进入统计会污染均值与方差",
                 "若变点紧随最后一个稳态段之后（见 §10），说明过程仍在漂移，窗口有效期存疑"),
                key=f"timeline:{resp}")
            cap = caps.get(resp) or {}
            # capability KPI card: always when the stats exist (spec-less runs
            # still carry mean/sigma/normality/n_eff — §7 must not go dark)
            if cap:
                kpi = [("n", fmt(cap.get("n"), 0)), ("mean", fmt(cap.get("mean"), 4)),
                       ("σ overall", fmt(cap.get("std_overall"), 4))]
                if cap.get("sigma_within_mr") is not None:
                    kpi.append(("σ within (MR)", fmt(cap.get("sigma_within_mr"), 4)))
                nm = cap.get("normality") or {}
                if nm:
                    if nm.get("normal"):
                        nval = f"是（AD={fmt(nm.get('ad_statistic'), 3)} < {fmt(nm.get('ad_critical_5pct'), 3)}）"
                    else:
                        nval = f"否（AD={fmt(nm.get('ad_statistic'), 3)} ≥ {fmt(nm.get('ad_critical_5pct'), 3)}）"
                    kpi.append(("正态", nval))
                if cap.get("n_eff") is not None:
                    kpi.append(("n_eff (AR1)", fmt(cap.get("n_eff"), 0)))
                note = esc(cap.get("note") or "")
                label_extra = esc(cap.get("cpk_label") or "")
                tl += ('<div class="kpi-row">' + "".join(
                    f'<div class="kpi"><span class="kpi-label">{esc(k)}</span>'
                    f'<span class="kpi-value mono">{v}</span></div>' for k, v in kpi)
                    + (f'<div class="kpi kpi-wide"><span class="kpi-label">口径</span>'
                       f'<span class="kpi-note">{label_extra}{" · " if label_extra and note else ""}{note}</span></div>'
                       if (label_extra or note) else "")
                    + '</div>')
            hist = ""
            if cap.get("has_specs") and cap.get("std_overall"):
                counts, edges = _hist(vals)
                mean, sd = cap.get("mean"), cap.get("std_overall")
                hist = self.add_chart(
                    "hist",
                    {"counts": counts, "edges": edges, "lsl": _sf(cap.get("lsl")),
                     "usl": _sf(cap.get("usl")), "target": _sf(cap.get("target")),
                     "mean": _sf(mean), "response": resp},
                    f"能力直方图 — {resp}（含 LSL/USL/T 规格线）",
                    (f"均值 {fmt(mean, 4)}，整体 σ {fmt(sd, 4)}；红线为规格限，蓝虚线为目标值",
                     "直方相对规格限的位置与展开程度就是过程能力的直观形态（Cp 看宽度，Cpk 看偏移）",
                     "指标卡再精确，也不该和直方图矛盾 — 两者对不上时先怀疑数据分组或规格录入"),
                    key=f"hist:{resp}")
                kpi = []
                for k, label in (("cp", "Cp"), ("cpk", "Cpk"), ("pp", "Pp"), ("ppk", "Ppk"),
                                 ("cnp", "Cnp(分位)")):
                    if cap.get(k) is not None:
                        kpi.append((label, fmt(cap.get(k), 3)))
                label_extra = esc(cap.get("cpk_label") or "")
                note = esc(cap.get("note") or "")
                hist += (f'<div class="kpi-row">' + "".join(
                    f'<div class="kpi"><span class="kpi-label">{k}</span>'
                    f'<span class="kpi-value mono">{v}</span></div>' for k, v in kpi)
                    + f'<div class="kpi kpi-wide"><span class="kpi-label">口径</span>'
                    f'<span class="kpi-note">{label_extra}{" · " if label_extra and note else ""}{note}</span></div></div>')
            blocks.append(f'<div class="resp-block{" resp-active" if not blocks else ""}" data-response="{esc(resp)}">{tl}{hist}</div>')
        body = ("".join(blocks)
                or '<p class="t3">无可绘制的时间序列（原始数据不可读或无响应列）。</p>')
        self.add_section("sec-7", "§7", "稳定性与能力", body)

    # ---------------- §8 操作窗口（双模式 forest）
    def sec_8(self):
        wins = self.recs.get("operating_windows") or []
        ranges = ((self.recs.get("applicability_domain") or {}).get("factor_observed_ranges")) or {}
        baseline = ((self.recs.get("current_baseline") or {}).get("point")) or {}
        chosen = {c for c in (self.recs.get("conflicts") or []) if c.get("chosen")}
        losers = {lid for c in (self.recs.get("conflicts") or [])
                  for lid in (c.get("between") or []) if lid != c.get("chosen")}
        rows = []
        for w in wins:
            wid = w.get("id")
            obs = ranges.get(w.get("factor")) or {}
            ci = (w.get("expected_effect") or {}).get("ci95")
            rows.append({
                "id": wid, "factor": w.get("factor"), "response": w.get("response"),
                "lo": _sf((w.get("range") or [None])[0]), "hi": _sf((w.get("range") or [None, None])[1]),
                "obsmin": _sf(obs.get("min")), "obsmax": _sf(obs.get("max")),
                "baseline": _sf(baseline.get(w.get("factor"))),
                "ci": [_sf(ci[0]), _sf(ci[1])] if ci else None,
                "confidence": w.get("confidence") or "—",
                "confirm": bool(w.get("confirmation_needed")),
                "loser": wid in losers,
                "chosen_conflict": wid in chosen,
                "delta": _sf((w.get("expected_effect") or {}).get("delta")),
                "unit": w.get("expected_effect", {}).get("unit"),
            })
        conf_info = [{"factor": c.get("factor"), "between": c.get("between"),
                      "chosen": c.get("chosen"), "resolution": c.get("resolution")}
                     for c in (self.recs.get("conflicts") or [])]
        if rows:
            n_conf = sum(1 for r in rows if r["confirm"])
            chart = self.add_chart(
                "forest", {"rows": rows},
                f"操作窗口 Forest 图（{len(rows)} 个窗口；灰带=观测域，色带=窗口，菱形=当前基线，须=CI95）",
                (f"{n_conf} 个窗口需要确认试验后才能执行；"
                 f"{len(conf_info)} 个因子存在多响应窗口冲突（已标注 chosen/落选）",
                 "窗口色带落在灰带边缘甚至触边 → 外推风险；菱形（当前基线）离窗口越远，调整代价越大",
                 "这是全报告最直接的动作清单 — 每个 OW 的 range 都可对照灰带判断「调多少、往哪调」"),
                key="forest")
            toggle = ('<label class="toggle"><input type="checkbox" id="toggle-ci" checked/>显示 CI95</label>')
            chart = chart.replace("</figcaption>", f"{toggle}</figcaption>")
            conf_html = ""
            if conf_info:
                conf_html = ('<h3 class="block-title">窗口冲突（同一因子、区间不相交）</h3><ul class="caveat-list">'
                             + "".join(f'<li><b class="mono">{esc(c["factor"])}</b>：{" vs ".join(c["between"] or [])} '
                                       f'→ 采纳 <span class="mono">{esc(c["chosen"] or "—")}</span>'
                                       f'（|效应|大者），落选窗口降入 watchlist。</li>' for c in conf_info)
                             + "</ul>")
            body = chart + conf_html
        else:
            body = ('<p class="body-l">本运行没有产出数值操作窗口 — 见 §10 的确认实验与观察清单，'
                    '先满足其条件再谈窗口。</p>')
        if self.mode == "designed":
            body = ('<p class="body-note">编号说明：章节编号为全局编号 — designed 模式不产生'
                    '观测章节 §6b–§7，故本章由 §6 直接跳至 §8（跳号属预期，非内容缺失）。</p>') + body
        self.add_section("sec-8", "§8", "操作窗口", body)

    # ---------------- §9 结论与等级
    def sec_9(self):
        conc = self.conclusion
        checklist = conc.get("grade_checklist") or {}
        cells = []
        for key, label in CHECKLIST_LABELS:
            v = checklist.get(key)
            if v is True:
                cls, txt = "sev-ok", "通过"
            elif v is False:
                cls, txt = "sev-crit", "未过"
            else:
                cls, txt = "sev-na", "— 未评估"
            cells.append(f'<div class="gate-cell"><span class="sev-badge {cls}">{txt}</span>'
                         f'<span>{esc(label)}</span></div>')
        if checklist.get("overridden_by"):
            cells.append(f'<div class="gate-cell"><span class="sev-badge sev-warn">覆盖</span>'
                         f'<span>模式由 {esc(checklist["overridden_by"])} 覆盖（等级未覆盖）</span></div>')
        rules = "".join(f'<li>{esc(r)}</li>' for r in (conc.get("downstream_usage_card", {})
                                                       or {}).get("usage_rules", []) or [])
        findings = []
        for f in (conc.get("key_findings") or []):
            refs = " ".join(f'<a class="mono ev-ref" title="{esc(r)}" href="#sec-appendix">{esc(r)}</a>'
                            for r in (f.get("evidence_refs") or []))
            findings.append(f'<li><span class="kf-id">{esc(f.get("id") or "")}</span>'
                            f'{esc(f.get("statement") or "")} {refs}'
                            f'<span class="sev-badge sev-na">{esc(f.get("confidence") or "—")}</span></li>')
        body = (f'<figure class="chart"><figcaption class="chart-head"><span class="chart-title">'
                f'等级四门（evidence_grade = {esc(conc.get("evidence_grade") or "—")}）</span>'
                f'<span class="chart-note">未评估项（—）不计入 fail，见 method_notes C11 等级规则</span></figcaption>'
                f'<div class="gate-grid">{"".join(cells)}</div>'
                + _reading("每扇门是一个机械判据（随机化/纯误差/分辨度/平衡/模型适切/防伪），未评估显示 — 不计失败。",
                           "等级由 checklist 逐门计算：0 败=A、1 败=A−、其余=B；observational 恒为 B。",
                           "等级决定下游能把它用到哪：A 才可作因果结论，B 只能作方向参考。")
                + "</figure>"
                + f'<h3 class="block-title">关键发现 ↔ 证据链接（悬停证据 chip 看全名）</h3><ul class="kf-list">{"".join(findings) or "<li class=t3>无（本轮无关键发现）</li>"}</ul>'
                + (f'<h3 class="block-title">使用规则（usage_rules）</h3><ul class="caveat-list">{rules}</ul>' if rules else ""))
        self.add_section("sec-9", "§9", "结论与等级", body)

    # ---------------- §10 局限与确认实验
    def sec_10(self):
        rec = self.recs
        lims = "".join(f'<li>{esc(x)}</li>' for x in (self.conclusion.get("limitations") or []))
        conf_rows = "".join(
            f'<tr><td class="mono">{esc(c.get("id") or "—")}</td>'
            f'<td><span class="sev-badge sev-warn">{esc(c.get("reason_code") or "—")}</span></td>'
            f'<td>{esc(c.get("reason") or "")}</td>'
            f'<td>{esc(c.get("design_hint") or "—")}</td>'
            f'<td class="num">{fmt(c.get("runs"), 0)}</td></tr>'
            for c in (rec.get("confirmations") or []))
        watch = "".join(
            f'<li><b class="mono">{esc(w.get("code") or "")}</b> {esc(w.get("message") or "")}</li>'
            for w in (rec.get("watchlist") or []))
        inval = "".join(f'<li>{esc(x)}</li>' for x in (rec.get("invalidation_conditions") or []))
        dom = rec.get("applicability_domain") or {}
        range_rows = "".join(
            f'<tr><td class="mono">{esc(f)}</td><td class="num">{fmt(r.get("min"), 4)}</td>'
            f'<td class="num">{fmt(r.get("max"), 4)}</td></tr>'
            for f, r in (dom.get("factor_observed_ranges") or {}).items())
        body = (
            f'<h3 class="block-title">局限（script-authored，全量）</h3><ul class="caveat-list">{lims or "<li class=t3>无（本轮无脚本产出的局限条目）</li>"}</ul>'
            + (f'<h3 class="block-title">确认实验（执行任何窗口前必须完成）</h3>'
               f'<table class="stat-table"><thead><tr><th>ID</th><th>reason_code</th><th>原因</th>'
               f'<th>设计提示</th><th class="num">runs</th></tr></thead><tbody>'
               f'{conf_rows or "<tr><td colspan=5 class=t3>无（本轮无待确认项）</td></tr>"}</tbody></table>'
               if conf_rows else '<p class="body-note">无（本轮无待确认项 — 无确认实验要求）</p>')
            + f'<h3 class="block-title">观察清单（watchlist）</h3><ul class="caveat-list">{watch or "<li class=t3>无（本轮无观察项）</li>"}</ul>'
            + f'<h3 class="block-title">失效条件（invalidation_conditions）</h3><ol class="caveat-list">{inval or "<li class=t3>无（本轮无失效条件）</li>"}</ol>'
            + f'<div class="check-card"><b>适用域（applicability_domain）</b>'
            f'<p>行数 {fmt(dom.get("n_rows"), 0)}；时间跨度 {esc(dom.get("time_span") or "—")}；'
            f'工况 {esc(dom.get("regime") or "—")}。</p>'
            f'<table class="stat-table"><thead><tr><th>因子</th><th class="num">观测 min</th><th class="num">观测 max</th></tr></thead>'
            f'<tbody>{range_rows or "<tr><td colspan=3 class=t3>无（无因子观测范围记录）</td></tr>"}</tbody></table>'
            f'<p class="t3">越出观测域 ±20% 或触发新变点即视为失效 — 见上方失效条件。</p></div>')
        self.add_section("sec-10", "§10", "局限与确认实验", body)

    # ---------------- 附录
    def sec_appendix(self):
        gen_map = {}
        for rel, art in self.art.items():
            if isinstance(art, dict) and art.get("generated_at"):
                gen_map[rel] = art["generated_at"]
        rows = "".join(
            f'<tr><td class="mono">{esc(rel)}</td>'
            f'<td class="mono sha">{esc((self.meta.get("artifacts") or {}).get(rel) or "—")}</td>'
            f'<td class="mono t3">{esc((gen_map.get(rel) or "—")[:19])}</td>'
            f'<td>{"在" if rel in self.art else "<b>缺</b>" if rel in REQUIRED_BY_MODE[self.mode] else "不适用（" + esc(self.mode) + " 模式）"}</td></tr>'
            for rel in ARTIFACTS)
        plots = (self.manifest.get("plots") or [])
        ink_ok_badge = '<span class="sev-badge sev-ok">ink PASS</span>'
        ink_bad = '<span class="sev-badge sev-crit">ink FAIL</span>'
        prow = "".join(
            f'<tr><td class="mono">{esc(p.get("file"))}</td><td>{esc(p.get("type"))}</td>'
            f'<td>{esc(p.get("title"))}</td>'
            f'<td>{ink_ok_badge if p.get("ink_ok") else ink_bad}</td>'
            f'<td class="num">{fmt(p.get("bytes"), 0)}</td>'
            f'<td class="mono t3">{esc(p.get("ink_detail") or "")}</td></tr>'
            for p in plots)
        note = esc(self.manifest.get("notes") or "")
        body = (f'<h3 class="block-title">工件索引（sha256 — 篡改检测的锚点）</h3>'
                f'<div class="table-wrap"><table class="stat-table"><thead><tr><th>工件</th><th>sha256（前 16）</th>'
                f'<th>generated_at</th><th>状态</th></tr></thead><tbody>{rows}</tbody></table></div>'
                + (f'<p class="body-note">原始数据 sha256：<span class="mono sha">{esc(self.raw_sha or "—")}</span>'
                   f'（只读输入；观测档用于稳定性序列图形，designed 档仅作指纹留存）</p>'
                   if self.raw_sha else "")
                + f'<h3 class="block-title">plot_manifest 逐图 ink 结果</h3>'
                f'<div class="table-wrap"><table class="stat-table"><thead><tr><th>文件</th><th>类型</th><th>标题</th>'
                f'<th>ink</th><th>bytes</th><th>详情</th></tr></thead><tbody>'
                + (prow or '<tr><td colspan="6" class="t3">（本运行 0 图 — 见 manifest notes）</td></tr>')
                + "</tbody></table></div>"
                + (f'<p class="body-note">{note}</p>' if note else ""))
        self.add_section("sec-appendix", "附录", "工件索引", body)

    # ---------------- orchestration
    def _has_rsm(self):
        """True when at least one model carries quadratic/2FI terms (§6 content)."""
        for m in (self.models or []):
            for t in ((m.get("predictor") or {}).get("terms") or []):
                for s in t.get("specs") or []:
                    if s.get("fn") == "square" or (s.get("fn") == "product"
                                                   and len(s.get("inputs") or []) == 2):
                        return True
        return False

    def _planned_sections(self):
        plan = []
        for sid, title in MODE_SECTIONS[self.mode]:
            if sid == "sec-6" and not self._has_rsm():
                continue
            plan.append((sid, title))
        return plan

    def build(self):
        self.load_raw()
        self.meta = {
            "generated_at": _now(), "script_version": VERSION,
            "mode": self.mode, "design_type": self.conclusion.get("design_type")
            or self.design.get("design_type"),
            "artifacts": {}, "raw_data_sha256": self.raw_sha,
        }
        for rel in ARTIFACTS:
            p = self.run_dir / rel
            if p.exists():
                self.meta["artifacts"][rel] = _sha256_path(p)
        self.nav_plan = self._planned_sections()
        self.rendered = set()

        self.sec_hero()
        self.sec_0()
        self.sec_1()
        self.sec_2()
        self.sec_3()
        if self.mode == "designed":
            self.sec_4()
            self.sec_5()
            self.sec_6()
        else:
            self.sec_6b()
            self.sec_7()
        self.sec_8()
        self.sec_9()
        self.sec_10()
        self.sec_appendix()

        payload = {"mode": self.mode, "charts": self.charts}
        meta_json = _json_for_script(self.meta)
        payload_json = _json_for_script(payload)
        nav_html = "".join(
            f'<a href="#{sid}">{esc(title)}</a>'
            for sid, title in self.nav if sid in self.rendered)
        tmpl = _Tmpl(TEMPLATE_PATH.read_text(encoding="utf-8"))
        out_html = tmpl.substitute(
            TITLE=f"DOE 工况分析报告 — {esc(self.run_dir.name)}",
            MODE=self.mode, DESIGN_TYPE=esc(str(self.meta.get("design_type") or "—")),
            META_JSON=meta_json, PAYLOAD_JSON=payload_json,
            NAV=nav_html, SECTIONS="".join(self.sections),
            SCRIPT_VERSION=esc(VERSION), GENERATED_AT=esc(self.meta["generated_at"][:19]),
        )
        out = self.run_dir / "report.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(out_html, encoding="utf-8")
        return out


# ------------------------------------------------------------------ small stats helpers (server-side only)

def _qq_pairs(vals):
    """Normal QQ pairs (theoretical ordered-statistic positions, sample sorted)."""
    vals = sorted(v for v in vals if v is not None)
    n = len(vals)
    if n < 3:
        return []
    try:
        from scipy import stats as sps
        osm, osr = sps.probplot(np.asarray(vals, dtype=float), fit=False)
        return [[_r6(a), _r6(b)] for a, b in zip(osm, osr)]
    except Exception:
        return []


def _hist(vals, max_bins=24):
    vals = [v for v in vals if v is not None]
    if not vals:
        return [], []
    counts, edges = np.histogram(np.asarray(vals, dtype=float),
                                 bins=max(6, min(max_bins, max(6, len(vals) // 8))))
    return [int(c) for c in counts], [_r6(e) for e in edges]


def pd_to_series(col):
    import pandas as pd
    return pd.to_numeric(col, errors="coerce").dropna().to_numpy(dtype=float)


# ------------------------------------------------------------------ entry

def build(run_dir, out_path=None):
    builder = ReportBuilder(run_dir)
    out = builder.build()
    if out_path:
        target = _contained(out_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
        return target
    return out


if __name__ == "__main__":
    print(build(sys.argv[1]))
