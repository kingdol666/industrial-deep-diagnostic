#!/usr/bin/env python
"""sentinel.py — watch entry point of industrial-sentinel (production sentinel).

Usage (from repo root, inside the shared uv venv):
  uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-sentinel/scripts/sentinel.py watch \
      (--run-dir RUN_DIR | --data PATH) \
      [--baseline PATH] [--config PATH] [--out-dir DIR]

Watch = batch screening of one data window (1k-100k rows) with four checks:
  C1 SPC Nelson R1/R2/R3/R5/R6        (spc.py, sigma = MRbar/1.128)
  C2 window drift projection           (projection.py, hours_to_edge)
  C3 regime / change-point mapping     (regime_map.py, in-process detector)
  C4 robust z + Mahalanobis            (robust.py, four-level degradation)
followed by the anti-storm layer (suppress.py: same-key merge, quiet zones,
hysteresis) and a Chinese watch_report.md.

Outputs (under --out-dir, default: <run-dir>/sentinel or <data-dir>/sentinel):
  alert.json       sentinel-alert/1.0 contract (schema-validated, gate-checked)
  watch_report.md  Chinese report rendered from templates/alert_report_template.md

Cold start: no baseline -> self baseline from the first >= 100 steady rows of
the window per group (Mahalanobis disabled), every run is marked
baseline.mode="self" with a SELF_BASELINE alert + 48h TTL reminder.

Exit codes: 0 ok · 1 findings (warn/high/critical) · 2 undetermined (bad
input / cold start impossible) · 3 self-check (gate) failure.
ZERO LLM / ZERO NETWORK on this path — numpy/scipy/pandas only, no raw open().
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from sentinelcore import (  # noqa: E402
    ALERT_CONTRACT_VERSION,
    BASELINE_CONTRACT_VERSION,
    BASELINE_DEFAULTS,
    CHECK,
    EXIT_FINDINGS,
    EXIT_GATE_FAIL,
    EXIT_OK,
    EXIT_UNDETERMINED,
    MODE,
    NEXT_SKILL,
    NS,
    RULE,
    SCRIPT_VERSION,
    SEV,
    SEV_RANK,
    STATUS,
    SUPPRESSION_DEFAULTS,
    URG,
)
from sentinelcore import _io, projection, regime_map, robust, spc, suppress  # noqa: E402
from sentinelcore.suppress import downgrade_severity, make_suppression_key  # noqa: E402

DATA_SUFFIXES = (".csv", ".tsv", ".tab", ".parquet", ".pq")
ALERT_ID_PATTERN = re.compile(r"^ALT-[0-9]{8}-[0-9]{6}-[0-9]{3}$")

DEFAULT_THRESHOLDS = {
    "run_length_r2": 9,
    "run_length_r3": 6,
    "r5_count": 2,
    "r5_of": 3,
    "r6_count": 4,
    "r6_of": 5,
    "min_points": 5,
    "robust_z_limit": 3.5,
    "mahalanobis_q": 0.999,
    "variance_ratio_high": 2.0,
    "hours_warn": 24.0,
    "hours_alarm": 8.0,
    "abnormal_ratio_warn": 0.15,
    "abnormal_ratio_critical": 0.3,
    "cp_min_shift_z": 0.5,
}


# ------------------------------------------------------------------ helpers

def find_data_file(run_dir):
    rd = _io._contained(run_dir)
    input_dir = rd / "00_input"
    search_dirs = [input_dir if input_dir.exists() else rd]
    for d in search_dirs:
        for entry in sorted(d.iterdir()):
            if entry.is_file() and entry.suffix.lower() in DATA_SUFFIXES \
                    and not entry.name.startswith("watch_baseline"):
                return entry
    return None


def load_config(path):
    if path is None:
        return {}, None
    p = _io._contained(path)
    if not p.exists():
        return {}, None
    cfg = _io.read_json(p)
    return cfg, p


def merged_thresholds(cfg):
    th = dict(DEFAULT_THRESHOLDS)
    th.update({k: v for k, v in (cfg.get("thresholds") or {}).items()
               if v is not None})
    return th


def build_alert(*, check_type, rule_name, severity, urgency, group,
                parameter=None, indicator=None, observed=None, threshold=None,
                evidence=None, advisory=False, suggested_check=None,
                suggested_next_skill=None, suppression_key=None, serial=0,
                generated_at=None):
    return {
        "alert_id": make_alert_id(generated_at, serial),
        "check_type": check_type,
        "rule_name": rule_name,
        "parameter": parameter,
        "indicator": indicator,
        "group": group,
        "severity": severity,
        "urgency": urgency,
        "observed": observed or {},
        "threshold": threshold or {},
        "evidence": evidence or {},
        "suggested_check": suggested_check,
        "suggested_next_skill": suggested_next_skill,
        "advisory": bool(advisory),
        "suppression_key": suppression_key
        or suppress.make_suppression_key(group, check_type, rule_name,
                                         parameter or indicator),
        "repeat_count": 1,
    }


def make_alert_id(generated_at, serial):
    stamp = (generated_at or _io.now_iso())
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})", stamp)
    base = "".join(m.groups()) if m else datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"ALT-{base[:8]}-{base[8:14]}-{serial:03d}"


def severity_rank(sev):
    return SEV_RANK.get(sev, -1)


def _repeat_totals(alerts):
    """suppression_key -> summed repeat_count (gate S4 cross-check basis)."""
    totals = {}
    for a in alerts:
        k = a.get("suppression_key")
        totals[k] = totals.get(k, 0) + int(a.get("repeat_count", 1))
    return totals


def urgency_for(sev):
    if sev == SEV["critical"]:
        return URG["immediate"]
    if sev == SEV["high"]:
        return URG["same_shift"]
    return URG["routine"]


def safe_std(v):
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    if v.size < 2:
        return None
    s = float(np.std(v, ddof=1))
    return s if s > 0 else None


# ------------------------------------------------------------------ checks

def check_group_spc(group, arrays, cols, store, th, quiet, time_hours,
                    generated_at):
    """C1 — Nelson SPC per parameter (baseline sigma_within_mr), quiet-zone
    filtered, plus one re-centered pass after the last new change point."""
    alerts = []
    n = len(next(iter(arrays.values()))) if arrays else 0
    quiet_arr = np.asarray(quiet, dtype=bool)
    # rows before the last quiet zone are judged by the baseline center line;
    # rows after it by the re-estimated center — the two passes never overlap
    quiet_end = int(np.max(np.flatnonzero(quiet_arr))) + 1 if quiet_arr.any() else 0
    for col in cols:
        p = (store.get("parameters") or {}).get(col) or {}
        center = p.get("center")
        sigma = p.get("sigma_within_mr")
        if center is None or sigma is None or not sigma or sigma <= 0:
            continue
        x = arrays[col]
        with np.errstate(invalid="ignore"):
            z = (x - float(center)) / float(sigma)

        def collect(zz, offset):
            found = []
            for e in spc.evaluate(zz, th):
                e = dict(e)
                e["index"] = e["index"] + int(offset)
                if not quiet_arr[e["index"]]:
                    found.append(e)
            return found

        # no change points -> whole series on the baseline center line;
        # with change points -> pre-quiet rows on the baseline line, the rest
        # on the re-estimated line (the two passes never overlap)
        main_slice = z[:quiet_end] if quiet_end else z
        episodes = collect(main_slice, 0)

        # re-estimated center line for the post-change segment
        if quiet_end and (n - quiet_end) >= int(th["min_points"]):
            seg = x[quiet_end:]
            seg_valid = seg[np.isfinite(seg)]
            if seg_valid.size >= int(th["min_points"]):
                z2 = (seg - float(np.mean(seg_valid))) / float(sigma)
                episodes.extend(collect(z2, quiet_end))

        for e in episodes:
            idx = int(e["index"])
            sev = spc.severity_for(e["rule_name"])
            sigma_level = 3.0 if e["rule_name"] == RULE["NELSON_R1"] else (
                2.0 if e["rule_name"] == RULE["NELSON_R5"] else (
                    1.0 if e["rule_name"] == RULE["NELSON_R6"] else None))
            ts = None
            if time_hours is not None and idx < len(time_hours):
                ts = f"row {idx}"
            alerts.append(build_alert(
                check_type=CHECK["spc"], rule_name=e["rule_name"],
                severity=sev, urgency=urgency_for(sev), group=group,
                parameter=col,
                observed={"value": _finite(x[idx]), "statistic": _finite(e.get("statistic")),
                          "index": idx, "timestamp": ts,
                          "run_length": int(e.get("run_length") or 1)},
                threshold={"bound": _finite(sigma * sigma_level) if sigma_level else None,
                           "sigma_level": sigma_level},
                evidence={"n_points": int(e.get("run_length") or 1)},
                suggested_check=_spc_suggestion(e["rule_name"], col),
                suggested_next_skill=NEXT_SKILL["spc"],
                generated_at=generated_at))
    return alerts


def _spc_suggestion(rule_name, col):
    if rule_name == RULE["NELSON_R1"]:
        return f"{col} 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录"
    if rule_name == RULE["NELSON_R2"]:
        return f"{col} 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况"
    if rule_name == RULE["NELSON_R3"]:
        return f"{col} 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度）"
    if rule_name == RULE["NELSON_R5"]:
        return f"{col} 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源"
    return f"{col} 窗口内多点超出 1σ 同侧，离散度升高，建议关注"


def _finite(v):
    try:
        f = float(v)
        return f if np.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def check_regime(group, arrays, cols, store, det, cps_new, th, generated_at):
    """C3 — REGIME_CHANGE_NEW / REGIME_ABNORMAL / VARIANCE_RATIO_HIGH."""
    alerts = []
    for cp in cps_new:
        alerts.append(build_alert(
            check_type=CHECK["regime"], rule_name=RULE["REGIME_CHANGE_NEW"],
            severity=SEV["warn"], urgency=URG["routine"], group=group,
            observed={"index": int(cp)},
            threshold={},
            evidence={"cp_position": int(cp)},
            suggested_check=f"{group} 组在第 {cp} 行附近检出新的工况变化点，"
                            f"其后 {SUPPRESSION_DEFAULTS['post_changepoint_quiet_rows']} 行已静默并重估中心线",
            suggested_next_skill=NEXT_SKILL["regime"],
            suppression_key=suppress.make_suppression_key(
                group, CHECK["regime"], RULE["REGIME_CHANGE_NEW"], f"cp_{int(cp)}"),
            generated_at=generated_at))

    sev = regime_map.abnormal_severity(det["abnormal_ratio"], th)
    if sev is not None:
        alerts.append(build_alert(
            check_type=CHECK["regime"], rule_name=RULE["REGIME_ABNORMAL"],
            severity=sev, urgency=urgency_for(sev), group=group,
            observed={"value": _finite(det["abnormal_ratio"])},
            threshold={"bound": float(th["abnormal_ratio_warn"])},
            evidence={"ratio": _finite(det["abnormal_ratio"])},
            suggested_check=f"{group} 组异常工况行占比 "
                            f"{det['abnormal_ratio']:.1%}，请核对报警时段的工艺参数与操作记录",
            suggested_next_skill=NEXT_SKILL["regime"],
            generated_at=generated_at))

    steady = np.array([lab == "steady" for lab in det["labels"]], dtype=bool)
    for col in cols:
        base_std = ((store.get("parameters") or {}).get(col) or {}).get(
            "variance_ratio_baseline_std")
        if not base_std or base_std <= 0:
            continue
        v = arrays[col]
        vs = v[steady & np.isfinite(v)]
        if vs.size < 30:
            continue
        cur_std = float(np.std(vs, ddof=1))
        if not np.isfinite(cur_std) or cur_std <= 0:
            continue
        ratio = cur_std / float(base_std)
        if ratio > float(th["variance_ratio_high"]):
            alerts.append(build_alert(
                check_type=CHECK["regime"], rule_name=RULE["VARIANCE_RATIO_HIGH"],
                severity=SEV["warn"], urgency=URG["routine"], group=group,
                parameter=col,
                observed={"value": _finite(cur_std),
                          "statistic": _finite(ratio)},
                threshold={"bound": float(th["variance_ratio_high"])},
                evidence={"ratio": _finite(ratio)},
                suggested_check=f"{col} 稳态段标准差为基线的 {ratio:.1f} 倍，"
                                f"离散度显著升高，建议检查波动来源",
                suggested_next_skill=NEXT_SKILL["regime"],
                generated_at=generated_at))
    return alerts


def check_projection(group, arrays, store, steady, time_hours, th,
                     generated_at):
    """C2 — window drift projection + indicator spec bounds."""
    alerts = []
    summary = []
    windows = (store or {}).get("operating_windows") or []
    indicators = (store or {}).get("indicators") or {}

    if time_hours is not None:
        for w in windows:
            factor = str(w.get("factor") or "")
            rng = w.get("range") or [None, None]
            if factor not in arrays or len(rng) != 2:
                continue
            lo, hi = rng
            confirmation = bool(w.get("confirmation_needed"))
            v = np.asarray(arrays[factor], dtype=float)[steady]
            h = np.asarray(time_hours, dtype=float)[steady]
            proj = projection.project(v, h, lo, hi, confirmation, th)
            if proj is None:
                continue
            level = proj["level"]
            check_type, rule = projection.alert_fields(level)
            if proj["out_of_range"]:
                check_type, rule = projection.out_of_range_fields()
            if level in (SEV["warn"], SEV["high"], SEV["critical"]) or proj["out_of_range"]:
                hours = proj["hours_to_edge"]
                if proj["out_of_range"]:
                    suggestion = (f"{factor} 当前值 {proj['current']:.4g} 已越出操作窗口 "
                                  f"[{lo}, {hi}]，请立即核实工艺状态")
                elif hours is not None:
                    suggestion = (f"{factor} 按当前漂移速率预计 {hours:.1f} 小时后触及窗口边界 "
                                  f"[{lo}, {hi}]，请提前安排核查")
                else:
                    suggestion = f"{factor} 存在趋势性漂移，建议关注"
                alerts.append(build_alert(
                    check_type=check_type, rule_name=rule,
                    severity=level, urgency=projection.urgency_for(level),
                    group=group, parameter=factor,
                    observed={"value": _finite(proj["current"]),
                              "statistic": _finite(proj["slope_per_hour"])},
                    threshold={"lsl": _finite(lo) if lo is not None else None,
                               "usl": _finite(hi) if hi is not None else None,
                               "hours_warn": float(th["hours_warn"]),
                               "hours_alarm": float(th["hours_alarm"])},
                    evidence={"n_points": proj["n_points"],
                              "slope_per_hour": _finite(proj["slope_per_hour"]),
                              "hours_to_edge": _finite(hours),
                              "direction": proj["direction"]},
                    advisory=confirmation,
                    suggested_check=suggestion,
                    suggested_next_skill=NEXT_SKILL["window_projection"],
                    generated_at=generated_at))
            summary.append({
                "factor": factor,
                "current": _finite(proj["current"]),
                "window": [_finite(lo) if lo is not None else None,
                           _finite(hi) if hi is not None else None],
                "slope_per_hour": _finite(proj["slope_per_hour"]),
                "hours_to_edge": _finite(proj["hours_to_edge"]),
                "level": level,
            })

    for ind, spec in indicators.items():
        if ind not in arrays:
            continue
        lsl, usl = spec.get("lsl"), spec.get("usl")
        if lsl is None and usl is None:
            continue
        v = np.asarray(arrays[ind], dtype=float)
        mask = np.isfinite(v) & (
            (v < lsl) if lsl is not None else np.zeros(v.shape, dtype=bool)) | (
            np.isfinite(v) & ((v > usl) if usl is not None else np.zeros(v.shape, dtype=bool)))
        if not mask.any():
            continue
        idxs = np.flatnonzero(mask)
        worst = int(idxs[np.argmax([_violation(v[i], lsl, usl) for i in idxs])])
        alerts.append(build_alert(
            check_type=CHECK["window_projection"], rule_name=RULE["WINDOW_OUT_OF_RANGE"],
            severity=SEV["critical"], urgency=URG["immediate"], group=group,
            indicator=ind,
            observed={"value": _finite(v[worst]), "index": int(worst)},
            threshold={"lsl": _finite(lsl), "usl": _finite(usl)},
            evidence={"n_points": int(mask.sum())},
            suggested_check=f"指标 {ind} 在第 {worst} 行越出规格界 "
                            f"[{lsl}, {usl}]，请立即核实产品质量与放行流程",
            suggested_next_skill=None,
            suppression_key=suppress.make_suppression_key(
                group, CHECK["window_projection"], RULE["WINDOW_OUT_OF_RANGE"], ind),
            generated_at=generated_at))
    return alerts, summary


def _violation(v, lsl, usl):
    if lsl is not None and v < lsl:
        return lsl - v
    if usl is not None and v > usl:
        return v - usl
    return 0.0


def check_multivariate(group, arrays, cols, store, steady, th, generated_at):
    """C4 — robust z + Mahalanobis (with degradation ladder)."""
    alerts = []
    n_out = 0
    max_d2 = None
    skipped_rows = 0
    degradations = []
    n_steady = int(steady.sum())

    for col in cols:
        p = (store.get("parameters") or {}).get(col) or {}
        v = np.asarray(arrays[col], dtype=float)[steady]
        zr = robust.robust_z(v, p.get("median"), p.get("mad"), p.get("sigma_overall"))
        for e in robust.robust_outliers(zr, float(th["robust_z_limit"])):
            abs_idx = int(np.flatnonzero(steady)[e["index"]])
            alerts.append(build_alert(
                check_type=CHECK["multivariate"], rule_name=robust.rule_robust(),
                severity=SEV["high"], urgency=urgency_for(SEV["high"]),
                group=group, parameter=col,
                observed={"value": _finite(v[e["index"]]),
                          "statistic": _finite(e["statistic"]),
                          "index": abs_idx, "run_length": int(e["run_length"])},
                threshold={"bound": float(th["robust_z_limit"])},
                evidence={"n_points": int(e["run_length"])},
                suggested_check=f"{col} 稳健 z 分数 |{e['statistic']:.2f}| 超过 "
                                f"{th['robust_z_limit']}，疑似离群点，请核对该行原始记录",
                suggested_next_skill=NEXT_SKILL["multivariate"],
                generated_at=generated_at))
            n_out += 1

    corr_store = (store or {}).get("correlation") or {}
    if corr_store.get("cols") and corr_store.get("cholesky_lower"):
        kept_names = corr_store["cols"]
        variances = [((store.get("parameters") or {}).get(c) or {}).get(
            "sigma_overall") for c in corr_store["cols"]]
        variances = [float(v) ** 2 if v else 0.0 for v in variances]
        L, kept, degradations = robust.prepare_mahalanobis(
            kept_names, corr_store["corr_matrix_flat"],
            corr_store["cholesky_lower"], variances=variances,
            n_steady=n_steady, thresholds=th)
        if L is not None:
            medians = [((store.get("parameters") or {}).get(c) or {}).get("median")
                       for c in kept]
            mads = [((store.get("parameters") or {}).get(c) or {}).get("mad")
                    for c in kept]
            sos = [((store.get("parameters") or {}).get(c) or {}).get("sigma_overall")
                   for c in kept]
            mat = np.column_stack([
                robust.robust_z(np.asarray(arrays[c], dtype=float)[steady],
                                medians[i], mads[i], sos[i])
                for i, c in enumerate(kept)])
            d2 = robust.mahalanobis_d2(mat, L)
            valid = np.isfinite(d2)
            skipped_rows = int((~valid).sum())
            if valid.sum() >= 2:
                max_d2 = float(np.nanmax(d2))
            for e in robust.mahalanobis_outlier_episodes(
                    d2, q=float(th["mahalanobis_q"]), k=len(kept)):
                abs_idx = int(np.flatnonzero(steady)[e["index"]])
                row = mat[e["index"]]
                contrib = sorted(
                    [{"name": c, "z_robust": float(round(row[i], 4))}
                     for i, c in enumerate(kept)
                     if np.isfinite(row[i])],
                    key=lambda d: -abs(d["z_robust"]))[:3]
                alerts.append(build_alert(
                    check_type=CHECK["multivariate"],
                    rule_name=robust.rule_mahalanobis(),
                    severity=SEV["high"], urgency=urgency_for(SEV["high"]),
                    group=group,
                    observed={"value": _finite(max_d2), "statistic": _finite(e["statistic"]),
                              "index": abs_idx, "run_length": int(e["run_length"])},
                    threshold={"d2_limit": _finite(e["d2_limit"])},
                    evidence={"d2": _finite(e["statistic"]),
                              "contributing_params": contrib},
                    suggested_check=f"多参数联合距离 d2={e['statistic']:.1f} 超过 "
                                    f"χ²({len(kept)}, {th['mahalanobis_q']})="
                                    f"{e['d2_limit']:.1f}，组合模式异常，"
                                    f"主要贡献参数：{', '.join(d['name'] for d in contrib)}",
                    suggested_next_skill=NEXT_SKILL["multivariate"],
                    generated_at=generated_at))
                n_out += 1
    return alerts, {"n_outliers": n_out, "max_d2": max_d2,
                    "rows_skipped": skipped_rows, "degradations": degradations}


# ------------------------------------------------------------------ baseline

def build_self_baseline(groups_arrays, cols, group_names, time_col, group_col, th):
    """Cold start: per-group self store from the first >= 100 steady rows."""
    stores = {}
    for g in group_names:
        from build_baseline import build_group_store  # in-process reuse

        arrays = groups_arrays[g]
        store = build_group_store(arrays, cols, None, thresholds=th)
        if store["validity"]["n_steady_rows"] < BASELINE_DEFAULTS["min_steady_rows_per_group"]:
            continue
        store["validity"]["self_baseline_ttl_hours"] = int(
            BASELINE_DEFAULTS["self_baseline_ttl_hours"])
        store["validity"]["invalidation_conditions"] = [
            "self 基线仅来自当前窗口，TTL 48 小时；超期或工况变化后必须用历史数据重建",
            f"稳态行数 {store['validity']['n_steady_rows']} 低于正式基线标准，统计功效有限",
        ]
        stores[g] = store
    baseline = {
        "contract_version": BASELINE_CONTRACT_VERSION,
        "baseline_version": f"self:v{SCRIPT_VERSION}",
        "generated_at": _io.now_iso(),
        "generated_from": {"doe_recommendations_path": None, "doe_run_dir": None,
                           "history_csv_sha256": None,
                           "recommendations_contract_version": None},
        "global": {"time_col": time_col, "group_col": group_col,
                   "numeric_columns": list(cols),
                   "fast_path_min_rows": int(BASELINE_DEFAULTS["fast_path_min_rows"]),
                   "window_rows": None},
        "groups": stores,
        "state": None,
        "provenance": {"input_sha256": None, "script_version": SCRIPT_VERSION,
                       "authored_by": "script"},
    }
    return baseline


# ------------------------------------------------------------------ report

def render_report(template, context):
    out = template
    for key, value in context.items():
        out = out.replace("{{" + key + "}}", str(value))
    return out


def alerts_table_md(alerts):
    rows = ["| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |",
            "|---|------|------|-----------|------|------|--------|------|"]
    for i, a in enumerate(alerts, 1):
        target = a.get("parameter") or a.get("indicator") or "-"
        idx = a.get("observed", {}).get("index")
        idx = idx if idx is not None else "-"
        val = a.get("observed", {}).get("value")
        val = f"{val:.4g}" if isinstance(val, float) else (val if val is not None else "-")
        rows.append(f"| {i} | {a['severity']} | {a['rule_name']} | {target} | "
                    f"{a.get('group') or '-'} | {idx} | {val} | "
                    f"{(a.get('suggested_check') or '-').replace('|', '\\|')} |")
    return "\n".join(rows) + "\n"


# ------------------------------------------------------------------ main

def cmd_watch(args):
    t0 = datetime.datetime.now(datetime.timezone.utc)

    run_dir = args.run_dir
    data_path = args.data
    out_dir = args.out_dir
    if run_dir:
        found = find_data_file(run_dir)
        if found is None:
            print(f"[sentinel] bad input: no data file under {_io._contained(run_dir)}")
            return EXIT_UNDETERMINED
        data_path = found
        out_dir = out_dir or (_io._contained(run_dir) / "sentinel")
    if not data_path:
        print("[sentinel] bad input: --run-dir or --data required")
        return EXIT_UNDETERMINED
    data_path = _io._contained(data_path)
    out_dir = _io._contained(out_dir) if out_dir else data_path.parent / "sentinel"

    cfg, cfg_path = load_config(args.config or
                                (data_path.parent / "watch_config.json"))
    th = merged_thresholds(cfg)
    checks_cfg = {"spc": True, "window_projection": True, "regime": True,
                  "multivariate": True}
    checks_cfg.update(cfg.get("checks") or {})

    try:
        df = _io.load_table(data_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[sentinel] bad input: cannot load {data_path}: {exc}")
        return EXIT_UNDETERMINED
    if df.empty:
        print("[sentinel] bad input: empty table")
        return EXIT_UNDETERMINED

    time_col, group_col = _io.identify_columns(
        df, cfg.get("time_col") or args.time_col, cfg.get("group_col") or args.group_col)
    groups = _io.split_groups(df, group_col)

    # ---- baseline
    baseline = None
    baseline_path = None
    baseline_path_arg = args.baseline or cfg.get("baseline_path")
    if baseline_path_arg:
        bp = Path(str(baseline_path_arg))
        if not bp.exists() and run_dir:
            candidate = _io._contained(run_dir) / "sentinel" / "watch_baseline.json"
            if candidate.exists():
                bp = candidate
        if bp.exists():
            baseline = _io.read_json(bp)
            baseline_path = str(_io._contained(bp))
    baseline_mode = "prior" if baseline is not None else "self"

    if baseline is None and args.no_self_baseline:
        print("[sentinel] undetermined: no baseline and self baseline disabled")
        return EXIT_UNDETERMINED

    generated_at = _io.now_iso()
    cold_start_note = ""

    # parameter columns
    if cfg.get("parameters"):
        cols = [c for c in cfg["parameters"] if c in df.columns]
    elif baseline is not None:
        cols = [c for c in (baseline.get("global", {}).get("numeric_columns") or [])
                if c in df.columns]
    else:
        cols = _io.numeric_columns(df, exclude=[time_col, group_col])
    if not cols:
        print("[sentinel] bad input: no usable numeric parameter columns")
        return EXIT_UNDETERMINED

    groups_arrays = {g: _io.to_arrays(sub, sorted(set(cols) |
                                                 {i for s in
                                                  ((baseline or {}).get("groups", {}) or {}).values()
                                                  for i in (s.get("indicators") or {})
                                                  if i in sub.columns})
                                     ) for g, sub in groups.items()}

    # ---- cold-start self baseline
    self_baseline_alert = None
    if baseline_mode == "self":
        baseline = build_self_baseline(groups_arrays, cols, list(groups),
                                       time_col, group_col, th)
        if not baseline["groups"]:
            print("[sentinel] undetermined: cold start needs >= "
                  f"{BASELINE_DEFAULTS['min_steady_rows_per_group']} steady rows per group")
            return EXIT_UNDETERMINED
        cold_start_note = ("本次运行为冷启动 self 基线（窗口前段稳态行自建，已跳过马氏距离），"
                           "TTL 48 小时，请尽快用历史数据运行 build_baseline.py 固化正式基线")
        self_baseline_alert = build_alert(
            check_type=CHECK["baseline"], rule_name=RULE["SELF_BASELINE"],
            severity=SEV["warn"], urgency=URG["routine"], group=None,
            observed={"value": None},
            threshold={"hours_warn": 48},
            evidence={"n_points": sum(
                s["validity"]["n_steady_rows"] for s in baseline["groups"].values())},
            advisory=True,
            suggested_check="self 基线仅覆盖本窗口，统计功效有限；"
                            "48 小时内请用历史数据运行 build_baseline.py 固化正式基线",
            suggested_next_skill=None,
            suppression_key=suppress.make_suppression_key(
                None, CHECK["baseline"], RULE["SELF_BASELINE"], None),
            generated_at=generated_at)
        # self baseline never uses Mahalanobis (frozen cold-start rule)
        checks_cfg["multivariate"] = False

    bgroups = baseline.get("groups") or {}

    # ---- per-group checks
    raw_alerts = []
    regime_labels_summary = {}
    n_cps_new = 0
    projection_summary = []
    mv_summary = {"n_outliers": 0, "max_d2": None, "rows_skipped": 0}
    quiet_rows_n = int(th.get("post_changepoint_quiet_rows",
                              SUPPRESSION_DEFAULTS["post_changepoint_quiet_rows"]))

    for g, sub in groups.items():
        arrays = groups_arrays[g]
        time_hours = _io.hours_axis(sub, time_col) if time_col else None
        store = bgroups.get(g)

        if store is None:
            if baseline_mode == "prior":
                raw_alerts.append(build_alert(
                    check_type=CHECK["baseline"], rule_name=RULE["UNSEEN_GROUP"],
                    severity=SEV["warn"], urgency=URG["routine"], group=g,
                    observed={"value": None},
                    threshold={},
                    evidence={"n_points": int(len(sub))},
                    suggested_check=f"分组 {g} 未在基线登记，请扩充基线（build_baseline.py）"
                                    f"或核对分组列取值",
                    suggested_next_skill=None,
                    generated_at=generated_at))
            # baseline-free regime scan still applies (self-contained detector)
            det = regime_map.detect(arrays, z_mean=None, thresholds=th)
            regime_labels_summary[g] = regime_map.label_counts(det["labels"])
            sev = regime_map.abnormal_severity(det["abnormal_ratio"], th)
            if sev is not None:
                raw_alerts.append(build_alert(
                    check_type=CHECK["regime"], rule_name=RULE["REGIME_ABNORMAL"],
                    severity=sev, urgency=urgency_for(sev), group=g,
                    observed={"value": _finite(det["abnormal_ratio"])},
                    threshold={"bound": float(th["abnormal_ratio_warn"])},
                    evidence={"ratio": _finite(det["abnormal_ratio"])},
                    suggested_check=f"未登记分组 {g} 的异常工况行占比 "
                                    f"{det['abnormal_ratio']:.1%}，请人工确认该分组是否应存在",
                    suggested_next_skill=NEXT_SKILL["regime"],
                    generated_at=generated_at))
            continue

        n = len(next(iter(arrays.values()))) if arrays else 0
        pnames = [c for c in cols if c in arrays]

        # z_mean for the change-point significance filter (baseline scale);
        # per-row MEDIAN across parameters so a single spiking parameter
        # cannot fabricate a level shift (spikes are R1's job, not C3's)
        z_mean = None
        if pnames and n:
            zs = []
            for c in pnames:
                p = (store.get("parameters") or {}).get(c) or {}
                center, sigma = p.get("center"), p.get("sigma_overall") or p.get("sigma_within_mr")
                if center is None or not sigma:
                    continue
                zs.append((arrays[c] - float(center)) / float(sigma))
            if zs:
                zmat = np.column_stack(zs)
                with np.errstate(invalid="ignore"):
                    z_mean = np.nanmedian(zmat, axis=1)

        det = regime_map.detect({c: arrays[c] for c in pnames}, z_mean=z_mean,
                                thresholds=th)
        known_cps = ((store.get("regime") or {}).get("known_change_points") or [])
        cps_new = regime_map.new_change_points(det["change_points"], known_cps)
        n_cps_new += len(cps_new)
        regime_labels_summary[g] = regime_map.label_counts(det["labels"])
        quiet = suppress.quiet_mask(n, cps_new, quiet_rows_n)
        steady = np.array([lab == "steady" for lab in det["labels"]], dtype=bool)

        if checks_cfg.get("spc", True):
            raw_alerts.extend(check_group_spc(g, arrays, pnames, store, th,
                                              quiet, time_hours, generated_at))
        if checks_cfg.get("regime", True):
            raw_alerts.extend(check_regime(g, arrays, pnames, store, det,
                                           cps_new, th, generated_at))
        if checks_cfg.get("window_projection", True):
            pa, psum = check_projection(g, arrays, store, steady, time_hours,
                                        th, generated_at)
            raw_alerts.extend(pa)
            projection_summary.extend(psum)
        if checks_cfg.get("multivariate", True):
            mv_alerts, mv = check_multivariate(g, arrays, pnames, store, steady,
                                               th, generated_at)
            raw_alerts.extend(mv_alerts)
            mv_summary = {
                "n_outliers": mv_summary["n_outliers"] + mv["n_outliers"],
                "max_d2": mv["max_d2"] if mv["max_d2"] is not None
                else mv_summary["max_d2"],
                "rows_skipped": mv_summary["rows_skipped"] + mv["rows_skipped"],
            }

    # ---- anti-storm merge + finalize
    raw_alerts.sort(key=lambda a: (a["suppression_key"],
                                   (a.get("observed") or {}).get("index") or 0))
    merged = suppress.merge_by_key(
        raw_alerts, max_gap_rows=SUPPRESSION_DEFAULTS["suppress_window_minutes"])
    if self_baseline_alert is not None:
        merged.append(self_baseline_alert)
    merged.sort(key=lambda a: (-severity_rank(a["severity"]), a["check_type"],
                               a["rule_name"], str(a.get("group")),
                               str(a.get("parameter"))))
    for i, a in enumerate(merged, 1):
        a["alert_id"] = make_alert_id(generated_at, i)

    rules_hit = {}
    spc_n = 0
    proj_n = 0
    for a in merged:
        if a["check_type"] == CHECK["spc"]:
            spc_n += 1
            rules_hit[a["rule_name"]] = rules_hit.get(a["rule_name"], 0) + 1
        elif a["check_type"] == CHECK["window_projection"]:
            proj_n += 1
    if any(severity_rank(a["severity"]) >= severity_rank(SEV["high"])
           for a in merged):
        status = STATUS["alert"]
    elif any(a["severity"] == SEV["warn"] for a in merged):
        status = STATUS["warn"]
    else:
        status = STATUS["ok"]

    duration_ms = int((datetime.datetime.now(datetime.timezone.utc) - t0).total_seconds() * 1000)
    window_start = window_end = None
    if time_col and time_col in df.columns:
        window_start = str(df[time_col].iloc[0])
        window_end = str(df[time_col].iloc[-1])
    payload = {
        "contract_version": ALERT_CONTRACT_VERSION,
        "alert_id": make_alert_id(generated_at, 0),
        "mode": MODE["watch"],
        "status": status,
        "group_scope": (group_col if len(groups) > 1 else
                        (group_col if group_col else None)),
        "generated_at": generated_at,
        "source": {
            "data_path": str(data_path),
            "sha256": _io.sha256_file(data_path),
            "window_start": window_start,
            "window_end": window_end,
            "n_rows": int(len(df)),
            "time_col": time_col,
            "group_col": group_col,
        },
        "baseline": {
            "path": baseline_path,
            "baseline_version": (baseline or {}).get("baseline_version"),
            "mode": baseline_mode,
            "generated_from": (baseline or {}).get("generated_from", {}).get("doe_run_dir")
            if baseline else None,
        },
        "checks_summary": {
            "spc": {"n_triggered": spc_n, "rules_hit": rules_hit},
            "window_projection": {"n_triggered": proj_n},
            "regime": {"labels": regime_labels_summary,
                       "n_change_points_new": n_cps_new},
            "multivariate": {"n_outliers": mv_summary["n_outliers"],
                             "max_d2": mv_summary["max_d2"]},
            "rows_skipped": mv_summary["rows_skipped"],
        },
        "alerts": merged,
        "regime_summary": {
            g: {"labels": regime_labels_summary.get(g, {})} for g in groups
        },
        "projection_summary": projection_summary or None,
        "suppression": {
            "applied": [
                {"suppression_key": k, "repeat_count": int(v)}
                for k, v in sorted(
                    _repeat_totals(merged).items()) if int(v) > 1
            ],
            "config": {
                "suppress_window_minutes": SUPPRESSION_DEFAULTS["suppress_window_minutes"],
                "hysteresis_points": SUPPRESSION_DEFAULTS["hysteresis_points"],
                "post_changepoint_quiet_rows": quiet_rows_n,
            },
        },
        "provenance": {
            "input_sha256": _io.sha256_file(data_path),
            "script_version": SCRIPT_VERSION,
            "duration_ms": duration_ms,
            "zero_llm": True,
            "authored_by": "script",
        },
    }

    # ---- self-check (in-process gate; failure -> exit 3)
    problems = self_check(payload)
    if problems:
        for p in problems:
            print(f"[sentinel] SELF-CHECK FAIL: {p}")
        _io.write_json(out_dir / "alert.json", payload)
        return EXIT_GATE_FAIL

    _io.write_json(out_dir / "alert.json", payload)

    # ---- Chinese report
    template_path = SCRIPT_DIR.parent / "templates" / "alert_report_template.md"
    template = template_path.read_text(encoding="utf-8") if template_path.exists() \
        else "# 哨兵巡检报告 {{GENERATED_AT}}\n\n{{ALERTS_SECTION}}"
    base_line = (f"模式：{baseline_mode}"
                 + (f"（{(baseline or {}).get('baseline_version') or ''}）" if baseline else "")
                 + (f"，路径：{baseline_path}" if baseline_path else ""))
    report = render_report(template, {
        "GENERATED_AT": generated_at,
        "MODE": payload["mode"],
        "STATUS": status,
        "ALERT_COUNT": len(merged),
        "DATA_PATH": str(data_path),
        "N_ROWS": len(df),
        "TIME_COL": time_col or "-",
        "GROUP_COL": group_col or "-",
        "BASELINE_LINE": base_line,
        "COLD_START_SECTION": (f"> **冷启动提示**：{cold_start_note}\n" if cold_start_note else ""),
        "ALERTS_SECTION": alerts_table_md(merged),
        "REGIME_SECTION": "\n".join(
            f"- **{g}**：" + "、".join(f"{k}={v}" for k, v in
                                       regime_labels_summary.get(g, {}).items())
            for g in groups) or "-",
        "PROJECTION_SECTION": ("\n".join(
            f"- **{p['factor']}**：当前 {p['current']:.4g}，斜率 {p['slope_per_hour']:.4g}/h，"
            f"距边界 {p['hours_to_edge'] if p['hours_to_edge'] is not None else '∞'} h"
            f"（级别 {p['level']}）" for p in projection_summary) or "- 无操作窗口投影"),
        "SUPPRESSION_SECTION": (
            f"合并触发 {len(payload['suppression']['applied'])} 组同 key 重复；"
            f"静默期 {quiet_rows_n} 行；同类抑制窗口 "
            f"{SUPPRESSION_DEFAULTS['suppress_window_minutes']} 分钟；迟滞 "
            f"{SUPPRESSION_DEFAULTS['hysteresis_points']} 点"),
        "DURATION_MS": duration_ms,
    })
    _io.write_text(out_dir / "watch_report.md", report)

    print(f"[sentinel] status={status} alerts={len(merged)} -> "
          f"{out_dir / 'alert.json'} ({duration_ms}ms)")
    return EXIT_OK if status == STATUS["ok"] else EXIT_FINDINGS


def self_check(payload):
    """In-process contract check (mirror of quality_gate.mjs; exit 3 path)."""
    problems = []
    if payload.get("contract_version") != ALERT_CONTRACT_VERSION:
        problems.append("contract_version mismatch")
    if payload.get("mode") not in MODE.values():
        problems.append("mode not in enum")
    if payload.get("status") not in STATUS.values():
        problems.append("status not in enum")
    for key in ("alert_id", "generated_at", "source", "baseline",
                "checks_summary", "alerts", "provenance"):
        if key not in payload:
            problems.append(f"missing top-level key {key}")
    if not ALERT_ID_PATTERN.match(payload.get("alert_id") or ""):
        problems.append("alert_id pattern mismatch")
    ids = set()
    for a in payload.get("alerts") or []:
        for key in ("alert_id", "check_type", "rule_name", "severity", "urgency",
                    "observed", "threshold", "suppression_key"):
            if key not in a:
                problems.append(f"alert missing {key}")
        if a.get("check_type") not in CHECK.values():
            problems.append(f"check_type not in enum: {a.get('check_type')}")
        if a.get("rule_name") not in RULE.values():
            problems.append(f"rule_name not in enum: {a.get('rule_name')}")
        if a.get("severity") not in SEV.values():
            problems.append(f"severity not in enum: {a.get('severity')}")
        if a.get("urgency") not in URG.values():
            problems.append(f"urgency not in enum: {a.get('urgency')}")
        nxt = a.get("suggested_next_skill")
        if nxt is not None and nxt not in list(NS.values()) + [None]:
            problems.append(f"suggested_next_skill not in enum: {nxt}")
        if not ALERT_ID_PATTERN.match(a.get("alert_id") or ""):
            problems.append(f"alert_id pattern mismatch: {a.get('alert_id')}")
        if a["alert_id"] in ids:
            problems.append(f"duplicate alert_id {a['alert_id']}")
        ids.add(a["alert_id"])
        if int(a.get("repeat_count") or 1) < 1:
            problems.append("repeat_count < 1")
    # same-key episodes are legal BEYOND the suppression window (60 rows at
    # the canonical cadence); duplicates inside it mean a storm slipped through
    per_key = {}
    for a in payload.get("alerts") or []:
        idx = (a.get("observed") or {}).get("index")
        per_key.setdefault(a.get("suppression_key"), []).append(idx)
    for key, idxs in per_key.items():
        known = [i for i in idxs if i is not None]
        if len(known) != len(idxs) and len(idxs) > 1:
            problems.append(f"same-key alerts without positions: {key}")
        known.sort()
        for x, y in zip(known, known[1:]):
            if y - x <= SUPPRESSION_DEFAULTS["suppress_window_minutes"]:
                problems.append(f"same-key alerts within suppression window: {key}")
    if payload.get("provenance", {}).get("zero_llm") is not True:
        problems.append("zero_llm must be true")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description="industrial-sentinel watch")
    sub = ap.add_subparsers(dest="command", required=True)
    w = sub.add_parser("watch", help="batch screening of one data window")
    w.add_argument("--run-dir", default=None)
    w.add_argument("--data", default=None)
    w.add_argument("--baseline", default=None)
    w.add_argument("--config", default=None)
    w.add_argument("--out-dir", default=None)
    w.add_argument("--time-col", default=None)
    w.add_argument("--group-col", default=None)
    w.add_argument("--no-self-baseline", action="store_true")
    w.set_defaults(func=cmd_watch)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
