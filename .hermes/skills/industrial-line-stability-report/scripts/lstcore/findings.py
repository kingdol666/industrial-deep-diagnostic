"""Finding generation with counterfactual constraints.

Every finding carries machine-checkable evidence, a deterministic confidence
(0-100, rubric below) and — for correlation/driver findings — a physical
mechanism check against the ontology (four-conditions alignment: statistical
significance + temporal precedence come from the metrics; physical mechanism
comes from ontology relationships/groups; "no contradiction" is covered by the
baseline/constraint checks). Mechanism-unsupported driver findings are tagged
[MECHANISM_UNKNOWN] and confidence-capped.

Severity literals reuse the shared closed-loop enum: info|warn|high|critical.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lstcore import ontology as _ontology  # noqa: E402

MAX_FINDINGS = 20
SEVERITIES = ["critical", "high", "warn", "info"]


def _ev(metric, value, threshold=None, source="lstcore", derived=False):
    e = {"metric": metric, "value": value, "source": source}
    if threshold is not None:
        e["threshold"] = threshold
    if derived:
        e["derived"] = True
    return e


def _f(seq, severity, category, title, detail, evidence, affected=None,
       confidence=None, mechanism=None):
    item = {
        "finding_id": f"F{len(seq) + 1:03d}",
        "severity": severity,
        "category": category,
        "title": title,
        "detail": detail,
        "evidence": evidence,
        "affected": affected or [],
        "confidence": confidence,
    }
    if mechanism:
        item["mechanism"] = mechanism
    seq.append(item)


def _fmt(v, nd=4):
    if isinstance(v, float):
        return f"{v:.{nd}f}".rstrip("0").rstrip(".")
    return str(v)


def _sample_penalty(report: dict) -> int:
    return -20 if (report.get("data") or {}).get("sampled") else 0


def generate(report: dict) -> list[dict]:
    out: list[dict] = []
    params = report["parameters"]
    data = report["data"]
    condition = report.get("condition") or {}
    spen = _sample_penalty(report)

    # data quality first (context for everything else)
    if data.get("missing_rate", 0) > 0.05:
        _f(out, "warn", "data_quality", "数据缺失率偏高",
           f"参数列缺失率 {data['missing_rate']:.1%}（阈值 5%），相关统计可能受影响。",
           [_ev("missing_rate", data["missing_rate"], "<=0.05")], confidence=85 + spen)
    if data.get("coverage_ratio", 1.0) < 0.98:
        _f(out, "info", "data_quality", "时段覆盖不完整",
           f"按中位采样间隔推算的时段覆盖率 {data['coverage_ratio']:.1%}，可能存在停线或采样中断。",
           [_ev("coverage_ratio", data["coverage_ratio"], ">=0.98")], confidence=80 + spen)
    inv = data.get("time_invariant_channels") or {}
    if inv.get("count"):
        share = float(inv.get("share") or 0.0)
        sev = "high" if share >= 0.5 else "warn"
        _f(out, sev, "data_quality", "时间不变量通道",
           f"{inv['count']}/{inv['total']} 个数值通道在整个时段取值完全不变"
           f"（占比 {share:.0%}）— 疑似快照式导出、死点或未投入的测点；"
           "这些通道已从稳定性评分中剔除，结论仅覆盖其余通道。",
           [_ev("time_invariant_count", inv["count"], "0"),
            _ev("time_invariant_share", share, "<0.5", derived=True)],
           affected=list(inv.get("examples") or [])[:10], confidence=95)

    total_violations = 0
    for p in params:
        name = p["name"]
        unit = (p.get("condition") or {}).get("unit")
        unit_s = f" {unit}" if unit else ""
        n_vp = p["n_violation_points"]
        total_violations += n_vp
        if n_vp > 0:
            rate = 100.0 * n_vp / p["n"] if p["n"] else 0.0
            rules_hit = sorted(r for r in p["nelson"]
                               if p["nelson"][r]["n_episodes"] > 0)
            sev = "high" if rate >= 2.0 else "warn"
            sigma = p.get("sigma_within_mr")
            _f(out, sev, "spc", f"{name} 检出 SPC 违规",
               f"共 {n_vp} 个判异剧集命中（每百点 {rate:.1f} 个，规则：{'/'.join(rules_hit)}），"
               f"控制限为中心值{_fmt(p['median'])}{unit_s}±3σ_within（σ={_fmt(sigma)}）。",
               [_ev("violation_episodes", n_vp, "0"),
                _ev("rate_per_100", round(rate, 2), "<2 for warn; >=2 for high"),
                _ev("sigma_within_mr", sigma)],
               affected=[name], confidence=90 + spen)
        dr = p.get("drift") or {}
        if dr.get("significant"):
            per_day = dr.get("per_day_relative")
            sev = "high" if (per_day or 0) >= 0.01 else "warn"
            _f(out, sev, "drift", f"{name} 存在显著漂移",
               f"Theil–Sen 斜率显著（Mann–Kendall p={dr.get('mk_p')}，且相对漂移≥0.1%/天才计入），"
               f"相对漂移约 {per_day:.3%}/天，方向对应斜率 {_fmt(dr.get('slope_per_second'))}/秒。",
               [_ev("mk_p", dr.get("mk_p"), "<0.01 且 >=0.1%/天"),
                _ev("per_day_relative", per_day, "<0.001 ok; >=0.01 high"),
                _ev("slope_per_second", dr.get("slope_per_second"))],
               affected=[name], confidence=80 + spen)
        cap = p.get("capability") or {}
        cpk = cap.get("cpk")
        if cpk is not None:
            sev = "high" if cpk < 1.0 else "warn" if cpk < 1.33 else None
            if sev:
                spec_src = (p.get("spec") or {}).get("source") or "user"
                _f(out, sev, "capability", f"{name} 规格能力不足",
                   f"Cpk={_fmt(cpk)}（阈值：≥1.33 合格，<1.0 不足），"
                   f"规格界限 LSL={_fmt(p['spec'].get('lsl'))} / USL={_fmt(p['spec'].get('usl'))}"
                   f"（来源：{'本体资产' if spec_src == 'ontology' else '用户提供'}）。",
                   [_ev("cpk", cpk, ">=1.33"), _ev("ppk", cap.get("ppk")),
                    _ev("spec_source", spec_src)],
                   affected=[name], confidence=85 + spen)
        br = p.get("baseline_ref") or {}
        if br and br.get("robust_z") is not None and abs(br["robust_z"]) > 3.5:
            sev = "high" if abs(br["robust_z"]) > 6.7 else "warn"
            _f(out, sev, "baseline_deviation", f"{name} 偏离历史基线",
               f"时段中位数相对 sentinel 基线的稳健 z={_fmt(br['robust_z'])}"
               f"（基线中位 {_fmt(br.get('baseline_median'))}），超出 ±3.5 参考带。",
               [_ev("robust_z", br["robust_z"], "|z|<=3.5", derived=True),
                _ev("baseline_median", br.get("baseline_median"), None,
                    "sentinel baseline")],
               affected=[name], confidence=75 + spen)

    if params and total_violations == 0:
        _f(out, "info", "spc", "全部参数无 SPC 违规",
           f"评估的 {len(params)} 个参数在 Nelson R1/R2/R3/R5/R6 下均无判异剧集。",
           [_ev("total_violation_episodes", 0, "0")], confidence=90 + spen)

    # ── regime (working-condition) switch ──────────────────────────────────
    regimes_res = (condition.get("regimes") or {})
    cps = regimes_res.get("change_points") or []
    if regimes_res.get("available") and cps:
        first = cps[0]
        _f(out, "warn", "regime", f"运行状态发生结构性切换（{len(cps)} 个显著分段变点）",
           f"sentinel C3 分段在本时段检出 {len(cps)} 个显著变点"
           f"（首个位于第 {first} 行附近）；全时段评分可能混合不同工况，"
           f"请结合下方运行状态分段表分段解读。",
           [_ev("change_points", len(cps), "0", derived=True),
            _ev("segmentation_method", regimes_res.get("method"), None,
                "sentinel regime_map")],
           confidence=70 + spen)

    # ── correlation drivers with mechanism check ───────────────────────────
    pairs = report.get("correlations", {}).get("pairs", [])
    top_pairs = [p for p in pairs if abs(p["best_abs_r"]) >= 0.7][:3]
    for pair in top_pairs:
        mech = _ontology.mechanism_for(condition, pair["a"], pair["b"])
        lead = (f"（{pair['leader']} 领先 {pair['best_lag_rows']} 行）"
                if pair.get("leader") else "（零滞后同步）")
        if mech["level"] == "known":
            conf = min(85, 70 + (10 if pair.get("leader") else 0) + spen)
            mech_note = f"本体机制佐证：{mech.get('mechanism') or '存在因果边'}"
            if mech.get("governing_equation"):
                mech_note += f"；控制方程：{mech['governing_equation']}"
            tag = ""
        elif mech["level"] == "same_domain":
            conf = min(70, 60 + spen)
            mech_note = f"两参数同属本体参数组「{mech.get('group')}」，物理同域但未见直接因果边"
            tag = ""
        else:
            conf = max(35, 45 + spen)
            mech_note = "本体未提供物理机制支持——仅是统计共变，不可作因果线索使用"
            tag = " [MECHANISM_UNKNOWN]"
        _f(out, "info", "driver", f"强相关对：{pair['a']} ↔ {pair['b']}{tag}",
           f"滞后补偿后最强 |Spearman|={_fmt(pair['best_abs_r'])}{lead}；"
           f"零滞后 Pearson={_fmt(pair['pearson'])}。{mech_note}。"
           f"置信度 {conf}（统计证据充分度 × 机制支持度）。",
           [_ev("best_abs_r", pair["best_abs_r"], ">=0.7", derived=True),
            _ev("best_lag_rows", pair["best_lag_rows"]),
            _ev("mechanism_level", mech["level"], None, "ontology")],
           affected=[pair["a"], pair["b"]], confidence=conf,
           mechanism={"level": mech["level"], "mechanism": mech.get("mechanism"),
                      "governing_equation": mech.get("governing_equation")})
    contribs = [c for c in report.get("correlations", {}).get("contributions", [])
                if c.get("share", 0) >= 0.4][:3]
    for c in contribs:
        mech = _ontology.mechanism_for(condition, c["driver"], c["target"])
        conf = (min(80, 65 + spen) if mech["level"] == "known"
                else max(35, 50 + spen))
        mech_s = ("本体有因果边支持" if mech["level"] == "known" else
                  "本体未见因果边——占比仅为统计分解" if mech["level"] == "unknown"
                  else "同参数组物理同域")
        _f(out, "info", "driver", f"{c['driver']} 是 {c['target']} 波动的主要解释项",
           f"滞后补偿后 |r|² 归一，{c['driver']} 解释了 {c['target']} 约 {c['share']:.0%} 的方差"
           f"（|r|={_fmt(c['abs_r'])}，领先 {c.get('best_lag_rows', 0)} 行）。{mech_s}。"
           f"置信度 {conf}。",
           [_ev("share", c["share"], ">=0.4", derived=True),
            _ev("abs_r", c["abs_r"], derived=True),
            _ev("mechanism_level", mech["level"], None, "ontology")],
           affected=[c["driver"], c["target"]], confidence=conf,
           mechanism={"level": mech["level"], "mechanism": mech.get("mechanism")})

    tm = report.get("integrations", {}).get("tuning_memory") or {}
    for act in (tm.get("estimable") or [])[:3]:
        direction = "改善" if act.get("direction") == "improved" else "恶化"
        _f(out, "info", "action", f"调优动作 {act.get('parameter')}→{_fmt(act.get('to'))} {direction}",
           f"tuning-memory 归因状态 {act.get('status')}，指标变化 {_fmt(act.get('delta_metric'))}"
           f"（动作 {act.get('action_id')}）。",
           [_ev("delta_metric", act.get("delta_metric"), None,
                "tuning-memory attribution", derived=True),
            _ev("attribution_status", act.get("status"), None,
                "tuning-memory attribution")],
           affected=[act.get("parameter") or ""], confidence=70 + spen)
    if tm.get("used") and not tm.get("estimable"):
        _f(out, "info", "action", "本期调优动作均不可归因",
           f"tuning-memory 对本期 {tm.get('n_actions', 0)} 个动作未产出 estimable 归因"
           f"（死区/样本不足/动作重叠），如实记录，不做效果声明。",
           [_ev("estimable_count", 0, None, "tuning-memory attribution")],
           confidence=80 + spen)

    doe = report.get("integrations", {}).get("doe_analyzer") or {}
    for w in (doe.get("violations") or [])[:3]:
        role = w.get("window_role") or "legacy_window"
        joint = "；可执行联合点见 doe_analyzer.joint_setpoints" if doe.get("joint_setpoints") else ""
        _f(out, "warn", "window", f"{w['parameter']} 超出推荐操作窗",
           f"时段中位 {_fmt(w['median'])} 在推荐窗 [{_fmt(w.get('low'))}, {_fmt(w.get('high'))}] 之外"
           f"（来源 doe-analyzer recommendations；window_role={role}{joint}）。",
           [_ev("median", w["median"], f"[{w.get('low')}, {w.get('high')}]",
                "doe-analyzer recommendations.json", derived=True)],
           affected=[w["parameter"]], confidence=75 + spen)

    out.sort(key=lambda f: (SEVERITIES.index(f["severity"]), -(f.get("confidence") or 0)))
    for i, f in enumerate(out):
        f["finding_id"] = f"F{i + 1:03d}"
    return out[:MAX_FINDINGS]
