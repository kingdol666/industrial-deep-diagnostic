"""experience.py — recipe envelope writeback (converged -> verified,
paused/exhausted -> observation). LOCAL FILES ONLY: 06_experience/
experience_candidates.jsonl + kb_summary.md. Per the v1.4 three-system split
(closedloop_enums.responsibility_rule) IDD never connects to the knowledge
base — the kb-ready markdown is ingested by the AWS agent via rag-bridge
kb_agent with the regime_key scenario title.

Envelope field alignment with the tuning-memory (B) interface, per plan
contract bus row "recipe 回流" + experience_distill.mjs envelope:
  experience_type / payload / applicability / provenance /
  confidence_label / corroboration_count / refutation_count
payload carries final_setpoints / achieved / guardrails / verification.
"""

import json

from . import (CONFIRM_MIN_REPLICATES, DUAL_GATE_D_FRAC, VERSION, _contained,
               now, sha256_obj)

EXPERIENCE_TYPE = "optimization_recipe"


def regime_key(state, objective):
    """Scenario key: campaign scene = target metric + factor count + goal."""
    k = len(objective.get("factors") or [])
    return f"{objective.get('target_metric', 'metric')}_{k}f_{objective.get('goal', 'target')}"


def guardrail_envelope(incumbent_setpoints, domain, delta_raw_frac=None):
    """Recommended adjustment envelope per numeric factor: +/- delta_confirm
    coded units around the final point, translated to raw units."""
    out = {}
    from . import DELTA_CONFIRM
    for name, spec in domain.items():
        if "lo" not in spec or name not in incumbent_setpoints:
            continue
        v = float(incumbent_setpoints[name])
        half = (spec["hi"] - spec["lo"]) / 2.0
        d = DELTA_CONFIRM * half
        out[name] = {"value": v,
                     "envelope": [max(spec["lo"], v - d), min(spec["hi"], v + d)]}
    return out


def achieved_metrics(confirm_result, all_results=None):
    """{metric: {mean, sd, n, ci95_one_sided}} from the confirm replicate set."""
    import numpy as np
    out = {}
    for metric, values in (confirm_result or {}).items():
        vals = [v for v in values if v is not None]
        if not vals:
            continue
        arr = np.asarray(vals, dtype=float)
        n = arr.size
        mean = float(arr.mean())
        sd = float(arr.std(ddof=1)) if n > 1 else 0.0
        ci = None
        if n >= 2:
            from scipy.stats import t as _t
            tcrit = float(_t.ppf(0.95, n - 1))
            half = tcrit * sd / np.sqrt(n)
            ci = [mean - half, mean + half]
        out[metric] = {"mean": mean, "sd": sd, "n": int(n),
                       "ci95_one_sided": ci, "values": [float(v) for v in vals]}
    return out


def build_envelope(run_dir, state, objective, conclusion, verification):
    """recipe envelope dict aligned with the B-group /experience/accumulate
    interface (experience_type/payload/applicability/provenance/confidence)."""
    inc = state.get("incumbent") or {}
    setpoints = inc.get("setpoints") or {}
    conf_vals = conclusion.get("confirm_values") or {}
    payload = {
        "final_setpoints": dict(setpoints),
        "achieved": achieved_metrics(conf_vals),
        "in_target": bool(inc.get("in_target", False)),
        "desirability_D": inc.get("predicted_D"),
        "guardrails": guardrail_envelope(setpoints, conclusion.get("domain") or {}),
        "verification_status": verification,
        "dual_gate": conclusion.get("dual_gate"),
        "rounds_used": (state.get("budget") or {}).get("rounds_used"),
        "trials_used": (state.get("budget") or {}).get("trials_used"),
    }
    rk = regime_key(state, objective)
    return {
        "contract_version": "1.0",
        "experience_type": EXPERIENCE_TYPE,
        "experience_id": None,  # assigned by the receiving side (deterministic hash)
        "campaign_id": state.get("campaign_id"),
        "payload": payload,
        "applicability": {
            "scenario_genus": rk,
            "regime_key": rk,
            "factor_domains": {n: (s.get("lo"), s.get("hi"))
                               for n, s in (conclusion.get("domain") or {}).items()
                               if "lo" in s},
        },
        "provenance": {
            "run_id": state.get("campaign_id"),
            "scene_key": rk,
            "built_from": f"industrial-optimizer-loop/{VERSION}",
            "evidence_grade": "E2" if verification == "verified" else "E1",
            "authored_by": "script",
            "created_at": now(),
            "input_sha256": state.get("provenance", {}).get("input_sha256"),
        },
        "confidence_label": "verified" if verification == "verified" \
            else "observation",
        "corroboration_count": 1,
        "refutation_count": 0,
        "usage_note": "纯分析建议（advisory）。是否执行、如何执行由 AWS 侧决定；"
                      "IDD 不下发参数。envelope 外或外推点使用前需重新验证。",
    }


def verification_of(state):
    if state.get("phase") == "converged":
        return "verified"
    if state.get("phase") in ("paused", "exhausted"):
        return "observation"
    return None  # aborted / active: no reusable recipe


def write_experience(run_dir, state, objective, conclusion):
    """Write 06_experience/experience_candidates.jsonl + kb_summary.md.
    Returns list of written paths ([] when nothing admissible)."""
    verification = verification_of(state)
    if verification is None:
        return []
    rd = _contained(run_dir)
    envelope = build_envelope(run_dir, state, objective, conclusion, verification)
    exp_dir = rd / "06_experience"
    line = json.dumps(envelope, ensure_ascii=False, default=float)
    (exp_dir / "experience_candidates.jsonl").write_text(
        line + "\n", encoding="utf-8")
    (exp_dir / "kb_summary.md").write_text(
        kb_summary_markdown(envelope), encoding="utf-8")
    return [str(exp_dir / "experience_candidates.jsonl"),
            str(exp_dir / "kb_summary.md")]


def kb_summary_markdown(envelope):
    """Scenario-keyed kb-ready summary (AWS agent ingests this via kb_agent)."""
    p = envelope["payload"]
    rk = envelope["applicability"]["regime_key"]
    lines = [
        f"# 优化配方 · {rk}",
        "",
        f"- campaign: `{envelope['campaign_id']}`",
        f"- 验证状态: **{p['verification_status']}** "
        f"(证据等级 {envelope['provenance']['evidence_grade']}, "
        f"confidence_label={envelope['confidence_label']})",
        "",
        "## 最终设定点（建议，不下发）",
        "",
        "| 因子 | 值 | 建议包络 |",
        "|---|---|---|",
    ]
    for name, g in (p["guardrails"] or {}).items():
        lines.append(f"| {name} | {g['value']} | [{g['envelope'][0]:.6g}, "
                     f"{g['envelope'][1]:.6g}] |")
    lines += ["", "## 达成指标", ""]
    for m, a in (p["achieved"] or {}).items():
        ci = a.get("ci95_one_sided")
        ci_s = f" (95% CI ≈ [{ci[0]:.6g}, {ci[1]:.6g}])" if ci else ""
        lines.append(f"- {m}: mean={a['mean']:.6g}, sd={a['sd']:.6g}, "
                     f"n={a['n']}{ci_s}")
    dg = p.get("dual_gate") or {}
    lines += [
        "",
        "## 收敛判定（双门槛）",
        "",
        f"- 重复数 m ≥ {CONFIRM_MIN_REPLICATES} 且全落窗: "
        f"{dg.get('replicates_in_window')}",
        f"- 单侧 95% CI 在限内: {dg.get('ci_in_limits')}",
        f"- D ≥ {DUAL_GATE_D_FRAC}·D_max: {dg.get('desirability_gate')} "
        f"(D={dg.get('D')}, D_max={dg.get('D_max')})",
        "",
        f"> regime_key: `{rk}` — 同工况复用；跨工况使用前必须重新验证。",
    ]
    return "\n".join(lines) + "\n"
