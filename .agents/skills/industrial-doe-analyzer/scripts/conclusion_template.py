"""Headless-mode deterministic conclusion builder (plan: `authored_by: "script"`).

The doe-analyst agent enriches key_findings statements in Phase 3 (flipping
authored_by to "agent") — computed numbers and the evidence grade are NEVER
changed by the agent (grade is checklist-computed per plan §2.5).
"""


def _model_adequacy(effect_table):
    """Model-adequacy checklist entry (designed only).

    FAIL when any response family is saturated or shows significant lack-of-fit
    (p<0.05); None when not evaluable (no families / no estimable LOF test)."""
    fams = (effect_table or {}).get("families") or []
    if not fams:
        return None
    evaluable = False
    for fam in fams:
        if fam.get("saturated"):
            return False
        lof = fam.get("lack_of_fit") or {}
        if lof.get("estimable") and lof.get("p_value") is not None:
            evaluable = True
            if lof["p_value"] < 0.05:
                return False
    return True if evaluable else None


def _checklist(profile, effect_table, correlation, stability):
    design = profile.get("design") or {}
    mode = design.get("mode")
    if mode == "designed":
        rand_ok = not any(c["code"] == "NON_RANDOMIZED" for c in profile.get("caveats", []))
        pe_ok = any((f.get("df_pure_error") or 0) > 0 for f in effect_table.get("families", []))
        res = design.get("resolution")
        res_ok = design.get("design_type") in ("full_factorial", "rsm_ccd", "rsm_bbd",
                                               "latin_hypercube") or (res is not None and res >= 5)
        # balanced=None means "not evaluated" — RSM/LHS replicate centers/axials
        # by design, so combo-count balance is not an evaluable criterion there
        # (same carve-out as the UNBALANCED_DESIGN caveat in analyze.py). It must
        # stay None (unrated), never be counted as a failure.
        balanced_raw = design.get("balanced")
        if design.get("design_type") in ("rsm_ccd", "rsm_bbd", "latin_hypercube"):
            balanced_raw = None
        return {
            "randomization_ok": bool(rand_ok),
            "pure_error_df_gt0": bool(pe_ok),
            "resolution_ok": bool(res_ok),
            "balanced": None if balanced_raw is None else bool(balanced_raw),
            "model_adequacy_ok": _model_adequacy(effect_table),
            "anti_spurious_ok": None,
            "overridden_by": "user" if design.get("mode_overridden") else None,
        }
    pairs = (correlation or {}).get("pairs", [])
    critical = [p for p in pairs if abs(p.get("r") or 0) >= 0.3 and p.get("anti_spurious_verdict") == "FAIL"]
    return {
        "randomization_ok": None,
        "pure_error_df_gt0": None,
        "resolution_ok": None,
        "balanced": None,
        "model_adequacy_ok": None,
        "anti_spurious_ok": len(critical) == 0,
        "overridden_by": "user" if design.get("mode_overridden") else None,
    }


def _grade(checklist, mode):
    if mode == "observational":
        return "B"
    vals = [v for k, v in checklist.items()
            if k != "overridden_by" and v is not None]
    fails = sum(1 for v in vals if v is False)
    if fails == 0:
        return "A"
    if fails == 1:
        return "A-"
    return "B"


def build(profile, effect_table, correlation, stability, recommendations,
          plot_manifest, models=None):
    design = profile.get("design") or {}
    mode = design.get("mode")
    checklist = _checklist(profile, effect_table, correlation, stability)
    grade = _grade(checklist, mode)
    findings = []
    limitations = []

    if mode == "designed" and effect_table:
        for fam in effect_table.get("families", [])[:3]:
            top = sorted([t for t in fam.get("tests", []) if t.get("pareto_rank")],
                         key=lambda t: t["pareto_rank"])[:2]
            for t in top:
                if t.get("q_value_bh") is None:
                    continue
                direction = "正向" if (t.get("coefficient") or 0) > 0 else "负向"
                findings.append({
                    "id": f"KF-{len(findings) + 1:03d}",
                    "statement": (f"因子/项 {t['term']} 对响应 {fam['response']} 存在{direction}效应："
                                  f"编码系数 {t.get('coefficient')}，q(BH)={t.get('q_value_bh')}，"
                                  f"partial η²={t.get('partial_eta_squared')}"),
                    "evidence_refs": [f"effect_table.json#{fam['response']}.{t['term']}"],
                    "confidence": "high" if t["q_value_bh"] < 0.01 else "medium",
                    "fdr_q": t.get("q_value_bh")})
        if design.get("resolution") is not None and design["resolution"] <= 4:
            limitations.append(
                f"部分因子设计分辨度为 {design['resolution']}：二阶交互存在别名，"
                f"不可作因果引用（别名链见 data_profile.json）")
        for fam in effect_table.get("families", []):
            if fam.get("saturated"):
                limitations.append(f"响应 {fam['response']} 的模型为饱和/池化误差 — "
                                   f"p 值按 pooled/saturated 规则处理")
            lof = fam.get("lack_of_fit") or {}
            if not lof.get("estimable") and lof.get("reason"):
                limitations.append(f"响应 {fam['response']}：失拟检验不可估（{lof['reason']}）")
    # --- script-authored limitations inherited from the model / correlation blocks
    for m in (models or []):
        rd = m.get("residual_diagnostics") or {}
        n_high = rd.get("n_high_residual_abs_gt3sigma")
        if n_high:
            limitations.append(
                f"响应 {m.get('response')} 残差诊断：{n_high}/{m.get('n')} 个样本的残差绝对值"
                f"超过 3σ — 存在离群运行，建议核对原始记录后复核系数")
        max_cooks = rd.get("max_cooks_d")
        n_m = m.get("n")
        if max_cooks is not None and n_m and max_cooks > 4.0 / n_m:
            limitations.append(
                f"响应 {m.get('response')} 的最大 Cook's D={max_cooks} 超过 4/n 截断 — "
                f"个别试验点对系数影响过大，删除该点可能改变结论")
        if m.get("mse") == 0:
            limitations.append(
                f"响应 {m.get('response')} 为零方差（常数）— 无法建立统计模型，相关结果仅作记录")
    if mode == "observational" and correlation:
        flagged = [p for p in correlation.get("pairs", [])
                   if (p.get("verdicts") or {}).get("outlier_sensitivity") == "SERIOUS"
                   or (p.get("anti_spurious_verdict") == "FAIL"
                       and any("outlier" in (n or "") for n in (p.get("notes") or [])))]
        for p in flagged[:5]:
            limitations.append(
                f"相关对 {p.get('parameter')}→{p.get('target')} 存在离群点敏感证据"
                f"（outlier_sensitivity=SERIOUS，r={p.get('r')}）— 结论对个别样本敏感，"
                f"需复核原始数据或做稳健性重算")
    if mode == "observational" and correlation:
        good = [p for p in correlation.get("pairs", [])
                if p.get("anti_spurious_verdict") in ("PASS", "CAUTION")
                and abs(p.get("r") or 0) >= 0.3]
        good.sort(key=lambda p: abs(p.get("r") or 0), reverse=True)
        for p in good[:5]:
            lag_txt = f"，滞后 {p['best_lag']} 步" if p.get("best_lag") else ""
            findings.append({
                "id": f"KF-{len(findings) + 1:03d}",
                "statement": (f"{p['parameter']} 与 {p['target']} 的相关 r={p['r']}"
                              f"{lag_txt}，q(BH)={p.get('q_value_bh')}，"
                              f"防伪裁决 {p['anti_spurious_verdict']} — 相关级证据，非因果"),
                "evidence_refs": [f"correlation_report.json#{p['target']}.{p['parameter']}"],
                "confidence": "low",
                "fdr_q": p.get("q_value_bh")})
        limitations.append("观察性数据：全部结论为相关级（evidence B），"
                           "执行任何操作窗口前必须完成 confirmations")
        if stability and stability.get("change_points"):
            limitations.append("检出过程变点 — 结论仅适用于 applicability_domain 所限工况")

    for c in profile.get("caveats", []):
        if c.get("severity") in ("warn", "critical"):
            limitations.append(c.get("message"))

    rec = recommendations or {}
    card = {
        "contract_version": rec.get("contract_version"),
        "n_windows": len(rec.get("operating_windows", [])),
        "n_confirmations": len(rec.get("confirmations", [])),
        "n_watchlist": len(rec.get("watchlist", [])),
        "usage_rules": rec.get("usage_rules", []),
    }
    return {
        "generated_at": _now(),
        "analysis_mode": mode,
        "design_type": design.get("design_type"),
        "evidence_grade": grade,
        "grade_checklist": checklist,
        "authored_by": "script",
        "key_findings": findings,
        "limitations": limitations,
        "figure_index": [{"file": p.get("file"), "title": p.get("title")}
                         for p in (plot_manifest or {}).get("plots", [])],
        "recommendations_ref": "conclusions/recommendations.json",
        "downstream_usage_card": card,
    }


def _now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
