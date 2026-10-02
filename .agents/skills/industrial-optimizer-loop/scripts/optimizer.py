#!/usr/bin/env python
"""optimizer.py — single deterministic entry of industrial-optimizer-loop.

Subcommands (all take --run-dir RUN_DIR; RUN_DIR contract = run_manifest.json +
00_input/objective.json + 01_state/optimizer_state.json + 02_rounds/R00n/
{trial_design,trial_result}.json + conclusions/{optimization_conclusion,recipe}.json
+ report.md):

  init      --run-dir RD [--objective PATH]   create skeleton + O-G1 validation
  design    --run-dir RD                      method decision tree -> trial_design.json
  ingest    --run-dir RD [--result PATH]      trial_result -> state machine transition
  status    --run-dir RD                      print state summary (exit 0)
  converge  --run-dir RD                      terminal phase -> conclusions + experience

Discipline (plan industrial-closedloop-skills-v1 §5, v1.4 ruling):
  - IDD is a PURE ANALYSIS system: this tool produces design/analysis artifacts
    only. It NEVER dispatches parameters; trial execution is AWS/manual.
  - Every number is script-computed (provenance.authored_by="script"); the agent
    only interprets. Zero LLM, zero network.
  - File IO: every path passes _contained(); reads/writes via pathlib; no bare
    open(); no dynamic-argv subprocess.

Exit codes: 0 ok, 1 contract/execution error (message names the missing action).
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

import numpy as np

OPTCORE_PARENT = Path(__file__).resolve().parent
if str(OPTCORE_PARENT) not in sys.path:
    sys.path.insert(0, str(OPTCORE_PARENT))

from optcore import (CONFIRM_MIN_REPLICATES, DEFAULT_SEED, DELTA_CONFIRM,
                     DUP_RATIO_MAX, DUAL_GATE_D_FRAC, EXPLORE_N_MIN, NEIGHBORHOOD,
                     SCRIPTS_DIR, STALL_ROUNDS, VERSION, _contained, _read_json,
                     _write_json, _write_text, now, sha256_file)
from optcore import acquisition as acq
from optcore import objective as obj_mod
from optcore import strategy
from optcore import windows_seed as wins
from optcore.experience import verification_of, write_experience
from optcore.gp import GPDegenerateError, lhs_uniform
from optcore.rsm_model import (combined_desirability, fit_quadratic,
                               propose_poly_refine, propose_rsm_augment,
                               split_grid)

SCENE = "optimizer_campaign"


class ExecutionError(RuntimeError):
    """Contract violation that blocks the step (CLI -> exit 1)."""


# ------------------------------------------------------------------ campaign io

def run_manifest(run_dir):
    return {"run_id": Path(run_dir).name, "scene": SCENE, "created_at": now(),
            "skill": "industrial-optimizer-loop", "script_version": VERSION,
            "steps": []}


def _state_path(rd):
    return rd / "01_state" / "optimizer_state.json"


def load_state(rd):
    p = _state_path(rd)
    if not p.exists():
        raise ExecutionError(f"optimizer_state.json missing under {rd} — run `init` first")
    return _read_json(p)


def rounds_dir(rd):
    return rd / "02_rounds"


def round_ids(rd):
    d = rounds_dir(rd)
    if not d.exists():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir() and p.name.startswith("R")
                  and p.name[1:].isdigit())


def load_round(rd, rid):
    base = rounds_dir(rd) / rid
    design = _read_json(base / "trial_design.json") \
        if (base / "trial_design.json").exists() else None
    result = _read_json(base / "trial_result.json") \
        if (base / "trial_result.json").exists() else None
    return design, result


def write_state(rd, state):
    state.setdefault("provenance", {})["authored_by"] = "script"
    state["provenance"]["script_version"] = VERSION
    state["provenance"]["input_sha256"] = state.get("objective_sha256")
    _write_json(_state_path(rd), state)


# ------------------------------------------------------------------ data pool

def build_pool(rd):
    """Replay all rounds -> observation pool. Deterministic; single source of
    truth is the trial_design/trial_result file pairs."""
    pool = []
    for rid in round_ids(rd):
        design, result = load_round(rd, rid)
        if not design or not result:
            continue
        by_id = {t["trial_id"]: t for t in design.get("trials", [])}
        for rt in result.get("trials", []):
            tid = rt["trial_id"]
            design_t = by_id.get(tid, {})
            sp = design_t.get("setpoints") or rt.get("setpoints") or {}
            metrics = {}
            for m, vals in (rt.get("measurements") or {}).items():
                clean = [v for v in (vals or []) if isinstance(v, (int, float))]
                arr = np.asarray(clean, dtype=float)
                metrics[m] = {
                    "values": clean,
                    "mean": float(arr.mean()) if arr.size else None,
                    "sd": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
                    "n": int(arr.size),
                }
            pool.append({"round_id": rid, "trial_id": tid,
                         "status": rt.get("status"),
                         "setpoints": sp, "metrics": metrics,
                         "failure_reason": rt.get("failure_reason")})
        for late in result.get("late_results") or []:
            metrics = {}
            for m, vals in (late.get("measurements") or {}).items():
                clean = [v for v in (vals or []) if isinstance(v, (int, float))]
                arr = np.asarray(clean, dtype=float)
                metrics[m] = {"values": clean,
                              "mean": float(arr.mean()) if arr.size else None,
                              "sd": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
                              "n": int(arr.size)}
            assign = late.get("assigned_round") or rid
            pool.append({"round_id": assign, "trial_id": late.get("trial_id"),
                         "status": "late", "setpoints": {},
                         "metrics": metrics, "late": True})
    return pool


def completed_points(pool, target_metric):
    """Pool entries usable for modeling (numeric setpoints + measured mean)."""
    pts = []
    for e in pool:
        if e.get("late") or e["status"] not in ("completed", "partial", "late"):
            continue
        m = e["metrics"].get(target_metric)
        if not m or m["mean"] is None or not e["setpoints"]:
            continue
        pts.append(e)
    return pts


# ------------------------------------------------------------------ model glue

def metric_grid(observed_means_by_metric):
    return {m: (float(np.min(v)), float(np.max(v)))
            for m, v in observed_means_by_metric.items() if len(v) >= 2}


def d_per_point(pts, specs):
    clean, grid = split_grid(specs)
    out = []
    for e in pts:
        means = {m: mm["mean"] for m, mm in e["metrics"].items()
                 if mm["mean"] is not None}
        d, _ = combined_desirability(means, clean, grid)
        out.append(float(d))
    return out


def fit_models(pts, domain_numeric, specs, target_metric):
    """Fit GP per metric (numeric factors only; categoricals held at the
    campaign level). Returns (fits, model_info, failures)."""
    names = acq.numeric_names(domain_numeric)
    X = np.array([[acq.code_point(e["setpoints"], domain_numeric)[f"x{i}"]
                   for i in range(len(names))] for e in pts], dtype=float)
    per_metric, rep_vars = {}, {}
    for m in specs:
        ys, rvs = [], []
        for e in pts:
            mm = e["metrics"].get(m)
            if not mm or mm["mean"] is None:
                ys.append(np.nan)
                rvs.append(0.0)
                continue
            ys.append(mm["mean"])
            rvs.append((mm["sd"] ** 2) / mm["n"] if mm["n"] > 1 else 0.0)
        ys = np.asarray(ys, dtype=float)
        if np.isnan(ys).any():
            keep = ~np.isnan(ys)
            per_metric[m], rep_vars[m] = ys[keep], np.asarray(rvs)[keep]
        else:
            per_metric[m], rep_vars[m] = ys, np.asarray(rvs)
    fits, failures = {}, {}
    from optcore.gp import GPFit
    for m, ys in per_metric.items():
        if len(ys) < 3 or float(np.std(ys)) <= 0:
            failures[m] = "insufficient_or_zero_variance_data"
            continue
        try:
            fits[m] = GPFit(X, ys, replicate_var=rep_vars[m]).fit()
            failures.pop(m, None)
        except GPDegenerateError as exc:
            failures[m] = str(exc)
        except Exception as exc:  # noqa: BLE001 — numeric degeneracy is honest
            failures[m] = f"{type(exc).__name__}: {exc}"
    model_info = {
        "kind": "gp_ard_rbf" if fits and not failures else (
            "gp_ard_rbf_partial" if fits else "unavailable"),
        "fallback_active": bool(failures) and not fits,
        "data_n": len(pts),
        "noise_source": None,
        "fit_quality": {"log_ml": None, "cond_K": None},
    }
    if fits:
        ref = next(iter(fits.values()))
        model_info["fit_quality"] = {"log_ml": float(ref.log_ml),
                                     "cond_K": float(ref.cond_K)}
        if any(float(np.sum(rv)) > 0 for rv in rep_vars.values()):
            model_info["noise_source"] = "replicates"
        else:
            model_info["noise_source"] = "residual_pool"
    return fits, model_info, failures, X


def curvature_of(pts, domain_numeric, target_metric):
    """Curvature evidence flag from coded quadratic t-tests. Full quadratic
    (x, x^2, x:x) when n supports it; otherwise the reduced 1+x+x^2 probe so
    curvature is detectable from the minimal exploring batch (pinned in
    references/method_notes.md)."""
    ys = [e["metrics"].get(target_metric, {}).get("mean") for e in pts]
    X = [acq.code_point(e["setpoints"], domain_numeric) for e in pts]
    keep = [i for i, y in enumerate(ys) if y is not None]
    if len(keep) < 3:
        return False, None
    Xc = acq.coded_to_matrix([X[i] for i in keep])
    y = np.asarray([ys[i] for i in keep], dtype=float)
    k = Xc.shape[1]
    n_full = 1 + 2 * k + k * (k - 1) // 2
    model = None
    try:
        if len(keep) > n_full:
            model = fit_quadratic(Xc, y, with_2fi=True)
        else:
            model = fit_quadratic(Xc, y, with_2fi=False)
        return bool(model["curvature"]), {
            "r2": model["r2"], "stationary": model["stationary"],
            "n_params": model["n_params"], "n": int(len(keep)),
            "with_2fi": any(":" in nm for nm in model["names"])}
    except Exception:  # noqa: BLE001
        return False, None


# ------------------------------------------------------------------ commands

def cmd_init(run_dir, objective_path=None):
    rd = _contained(run_dir)
    rd.mkdir(parents=True, exist_ok=True)
    for sub in ("00_input", "01_state", "02_rounds", "conclusions", "06_experience"):
        (rd / sub).mkdir(parents=True, exist_ok=True)
    if objective_path:
        src = _contained(objective_path)
        dst = rd / "00_input" / "objective.json"
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    o, meta = obj_mod.load(rd)
    recs = wins.load_prior_recommendations(o, rd)
    domain = obj_mod.resolve_domain(o, obj_mod.prior_observed_ranges(recs))
    if not (rd / "run_manifest.json").exists():
        _write_json(rd / "run_manifest.json", run_manifest(rd))
    seed = int(o.get("seed") or DEFAULT_SEED)
    b = o["budget"]
    safety = obj_mod.safety_constraints(o)
    review_needed = any(s["factor"] is None and s["expr"] for s in safety)
    state = {
        "state_version": "1.0",
        "campaign_id": o["campaign_id"],
        "objective_ref": "00_input/objective.json",
        "objective_sha256": meta["sha256"],
        "phase": "initialized",
        "round_count": 0,
        "trial_count": 0,
        "budget": {"max_rounds": int(b["max_rounds"]),
                   "max_trials": int(b["max_trials"]),
                   "deadline": b.get("deadline"), "rounds_used": 0,
                   "trials_used": 0, "replicates_used": 0},
        "incumbent": None,
        "target_status": {"hit_ratio_history": [], "ci_in_limits": None,
                          "desirability_gate": None},
        "model": None,
        "belief": {"stall_rounds": 0, "max_ei_last": None,
                   "duplication_ratio": None, "domain_coverage": None},
        "history": [],
        "next_action": {
            "recommendation": "continue_exploit",
            "reasons": ["campaign initialized — run `design` to produce R001"],
            "agent_review_required": bool(review_needed)},
        "stop_resume": {"can_pause": True,
                        "resume_hint": "ingest each round's trial_result.json"},
        "guardrail_log": [],
        "provenance": {"input_sha256": meta["sha256"],
                       "script_version": VERSION, "seed": seed,
                       "authored_by": "script"},
    }
    write_state(rd, state)
    print(f"[init] campaign {o['campaign_id']} initialized at {rd}")
    print(f"[init] domain: {json.dumps({k: v for k, v in domain.items()})}")
    return 0


def _campaign(run_dir):
    rd = _contained(run_dir)
    o, meta = obj_mod.load(rd)
    state = load_state(rd)
    recs = wins.load_prior_recommendations(o, rd)
    domain = obj_mod.resolve_domain(o, obj_mod.prior_observed_ranges(recs))
    if state.get("objective_sha256") not in (None, meta["sha256"]):
        raise ExecutionError(
            "objective.json changed after init (sha256 mismatch) — re-init the "
            "campaign; mid-flight objective edits are a contract violation")
    return rd, o, meta, state, domain, recs


def _latest_round(rd):
    ids = round_ids(rd)
    return ids[-1] if ids else None


def _deadline_passed(state):
    dl = (state.get("budget") or {}).get("deadline")
    if not dl:
        return False
    try:
        return datetime.datetime.fromisoformat(str(dl)) < \
            datetime.datetime.now(datetime.timezone.utc)
    except ValueError:
        return False


def _all_fail_streak(rd, pool):
    """Consecutive latest rounds where every designed trial failed/aborted."""
    streak = 0
    for rid in reversed(round_ids(rd)):
        design, result = load_round(rd, rid)
        if not design or not result:
            break
        n = len(design.get("trials", []))
        bad = sum(1 for t in result.get("trials", [])
                  if t.get("status") in ("failed", "safety_aborted"))
        if n > 0 and bad == n:
            streak += 1
        else:
            break
    return streak


def _had_safety_abort(rd):
    for rid in round_ids(rd):
        _, result = load_round(rd, rid)
        if result and any(t.get("status") == "safety_aborted"
                          for t in result.get("trials", [])):
            return True
    return False


def _fallback_pending(rd, state):
    """True when the latest confirm round failed the dual gate (fake summit).
    Derived from history notes — the state keeps only schema-declared keys."""
    for h in reversed(state.get("history", [])):
        if "confirm_failed_dual_gate" in (h.get("notes") or ""):
            return True
        if h.get("method") == "confirm_replicates":
            return "confirm_failed_dual_gate" in (h.get("notes") or "")
    return False


def _d_span(d_vals):
    return (max(d_vals) - min(d_vals)) if len(d_vals) >= 2 else 1.0


def _predicted_dmax(fits, specs, cands):
    if not fits:
        return 0.0
    from optcore.rsm_model import split_grid
    clean, grid = split_grid(specs)
    X = acq.coded_to_matrix(cands)
    best = 0.0
    chunk = 128
    for i in range(0, X.shape[0], chunk):
        sub = X[i:i + chunk]
        means = {}
        for m, fit in fits.items():
            mu, _sd = fit.predict_raw(sub)
            means[m] = mu
        for j in range(sub.shape[0]):
            d, _ = combined_desirability({m: float(means[m][j]) for m in means},
                                         clean, grid)
            best = max(best, float(d))
    return best


def cmd_design(run_dir):
    rd, o, meta, state, domain, recs = _campaign(run_dir)
    if state["phase"] in strategy.TERMINAL_PHASES:
        raise ExecutionError(
            f"campaign phase is {state['phase']} (terminal) — `design` refused")
    latest = _latest_round(rd)
    if latest:
        _, result = load_round(rd, latest)
        if result is None:
            raise ExecutionError(
                f"round {latest} has a design but no trial_result.json — "
                f"EXECUTION CONTRACT: run trials (AWS/manual), place "
                f"02_rounds/{latest}/trial_result.json, then run `ingest`")
    seed = int(state.get("provenance", {}).get("seed") or DEFAULT_SEED)
    numeric = obj_mod.numeric_factors_from_domain(domain)
    cats = obj_mod.categorical_factors_from_domain(domain)
    k = len(numeric)
    target = obj_mod.primary_metric(o)
    pool = build_pool(rd)
    pts = completed_points(pool, target)

    round_no = (state["budget"]["rounds_used"] or 0) + 1
    obs_coded = [acq.code_point(e["setpoints"], domain) for e in pts]
    obs_matrix = acq.coded_to_matrix(obs_coded)

    # model health + curvature evidence
    fits, model_info, failures = {}, {}, {}
    curvature, cur_detail = False, None
    if pts:
        obs_means = {m: [e["metrics"][m]["mean"] for e in pts
                         if e["metrics"].get(m, {}).get("mean") is not None]
                     for m in list(spec_keys(o))}
        specs = obj_mod.metric_specs(o, metric_grid(obs_means))
        fits, model_info, failures, _X = fit_models(pts, domain, specs, target)
        curvature, cur_detail = curvature_of(pts, domain, target)
    else:
        specs = obj_mod.metric_specs(o, None)
    gp_healthy = bool(fits) and not (failures and set(failures) >= set(fits))

    fallback = _fallback_pending(rd, state) and state["phase"] == "exploiting"
    budget_left = max(int(state["budget"]["max_trials"]) -
                      int(state["budget"]["trials_used"]), 0)
    if budget_left <= 0 and state["phase"] != "confirming":
        raise ExecutionError("trial budget exhausted — campaign should be "
                             "`converge`d (phase will flip to exhausted on ingest)")
    # a confirm round may overdraw ONE design point when the budget ran out
    # exactly as the loop entered confirming (otherwise campaigns strand in
    # confirming with no way to close); pinned in references/method_notes.md
    budget_left = max(budget_left, 1)
    affordable_rsm = budget_left >= 2 * k + 4
    method = strategy.choose_method(
        round_no=round_no, phase=state["phase"], k=k, n_data=len(pts),
        prior_valid=wins.prior_valid(recs),
        batch_size=(2 * k + 4) if affordable_rsm else None,
        curvature=curvature, gp_healthy=gp_healthy, fallback_pending=fallback)
    batch = strategy.default_batch(
        method, k=k, n_data=len(pts),
        trials_per_round=(o["budget"].get("trials_per_round") or None),
        budget_left=budget_left)

    design_phase = strategy.DESIGN_PHASE_OF[state["phase"]]
    m_confirm = max(CONFIRM_MIN_REPLICATES,
                    int(((o.get("noise") or {}).get("replicates_for_sigma"))
                        or CONFIRM_MIN_REPLICATES))

    trials, guard = [], []

    def _coded_dist(c1, c2):
        return float(np.sqrt(sum((c1[f"x{i}"] - c2[f"x{i}"]) ** 2
                                 for i in range(len(numeric)))))

    def _clip_guard(sp):
        clipped, moved = obj_mod.clip_to_domain(sp, domain)
        if moved:
            guard.append({"code": "OG2_CLIP", "ts": now(),
                          "detail": f"setpoints clipped into domain: {moved}"})
        for c in obj_mod.safety_constraints(o):
            f = c.get("factor")
            if f and f in clipped and isinstance(clipped[f], (int, float)):
                v = float(clipped[f])
                v2 = v
                if c.get("min") is not None:
                    v2 = max(v2, float(c["min"]))
                if c.get("max") is not None:
                    v2 = min(v2, float(c["max"]))
                if abs(v2 - v) > 1e-12:
                    guard.append({"code": "OG5_CLIP", "ts": now(),
                                  "detail": f"safety limit clip on {f}: "
                                            f"{v} -> {v2} ({c.get('expr') or 'limit'})"})
                    clipped[f] = v2
        return clipped

    def _finish(coded_list, reasons, method_label, replicates=None,
                model_preds=True):
        """coded dicts (x0..) -> schema trial dicts (raw setpoints)."""
        out = []
        inc_c = _incumbent_coded(state, domain)
        for _i, coded in enumerate(coded_list):
            raw = acq.decode_point(coded, domain)
            raw = _clip_guard(raw)
            for cf in cats:  # categoricals held at campaign level (v1 scope)
                raw.setdefault(cf, _campaign_level(recs, cf, domain))
            for f in numeric:
                raw.setdefault(f, (domain[f]["lo"] + domain[f]["hi"]) / 2.0)
            coded2 = acq.code_point(raw, domain)
            d_near = acq.nearest_distance(coded2, obs_matrix) \
                if obs_matrix.size else float("inf")
            dup = d_near < DELTA_CONFIRM - 1e-9
            entry = {
                "trial_id": f"R{round_no:03d}-T{len(out) + 1:02d}",
                "setpoints": {f: round(float(raw[f]), 6) for f in sorted(raw)},
                "extrapolation": bool(d_near > NEIGHBORHOOD
                                      or acq.is_boundary(coded2)),
                "safety_checked": True,
            }
            if replicates:
                entry["replicates"] = int(replicates)
            if inc_c is not None:
                entry["distance_to_incumbent_coded"] = round(
                    _coded_dist(coded2, inc_c), 6)
            if model_preds and fits:
                names = acq.numeric_names(domain)
                mu_sd = {m: fit.predict_raw(
                    np.array([[coded2[f"x{i}"] for i in range(len(names))]]))
                    for m, fit in fits.items()}
                exp = {}
                for m, (mu, sd) in mu_sd.items():
                    exp[m] = {"mean": round(float(mu[0]), 6),
                              "ci95": [round(float(mu[0] - 1.96 * sd[0]), 6),
                                       round(float(mu[0] + 1.96 * sd[0]), 6)]}
                entry["expected"] = exp
                clean, grid = split_grid(specs)
                pd_val, _ = combined_desirability(
                    {m: float(v["mean"]) for m, v in exp.items()}, clean, grid)
                entry["predicted_D"] = round(float(pd_val), 6)
            entry["selection_reason"] = "; ".join(
                reasons + [f"{method_label}; dup_to_existing={dup}; "
                           f"nearest_data_coded="
                           f"{'inf' if d_near == float('inf') else round(d_near, 3)}"])
            out.append((entry, coded2, dup))
        return out

    def _dedupe_fill(coded_list, n_target, reason_prefix):
        """Drop batch members inside the duplication radius of observed points
        or of each other; refill the deficit with deterministic LHS."""
        keep = []
        avoid = list(obs_coded)
        for c in coded_list:
            if len(keep) >= n_target:
                break
            if avoid and acq.nearest_distance(c, acq.coded_to_matrix(avoid)) \
                    < DELTA_CONFIRM:
                continue
            if any(_coded_dist(c, k2) < DELTA_CONFIRM for k2 in keep):
                continue
            keep.append(c)
            avoid = avoid + [c]
        deficit = n_target - len(keep)
        if deficit > 0:
            keep = keep + _lhs_points(len(numeric), deficit, seed + round_no + 77,
                                      avoid)
        return keep[:n_target]

    if method == "window_seed":
        seeds = wins.seed_points(recs, domain)
        if not seeds:
            raise ExecutionError("window_seed selected but prior carries no "
                                 "usable seeds — prior invalid")
        coded_seeds = [acq.code_point(s["setpoints"], domain) for s in seeds]
        for s, c in zip(seeds, coded_seeds):
            if s.get("moved"):
                guard.append({"code": "OG2_CLIP", "ts": now(),
                              "detail": f"prior seed {s['kind']} clipped: "
                                        f"{s['moved']}"})
        fill_n = max(batch - len(coded_seeds), 0)
        fill = _lhs_points(k, fill_n, seed + round_no, obs_coded)
        entries = _finish(coded_seeds + fill,
                          [f"window_seed {s['kind']}" for s in seeds] +
                          [f"lhs fill {i}" for i in range(fill_n)],
                          "prior window seeds")
    elif method == "lhs_fill":
        pts_c = _lhs_points(k, batch, seed + round_no, obs_coded)
        entries = _finish(pts_c, ["space-filling LHS (exploring)"], "lhs_fill")
    elif method == "screen_first":
        pts_c = _lhs_points(k, batch, seed + round_no, obs_coded)
        entries = _finish(pts_c, ["screen_first: k>8 — screen factors, then "
                                  "delegate full screening analysis to "
                                  "industrial-doe-analyzer"], "screen_first")
    elif method == "rsm_augment":
        inc = _incumbent_coded(state, domain) or _center_coded(domain)
        center = dict(inc)
        center_note = "incumbent-centered"
        ys = [e["metrics"].get(target, {}).get("mean") for e in pts]
        keep = [i for i, y in enumerate(ys) if y is not None]
        if len(keep) >= 3:
            n_full = 1 + 2 * k + k * (k - 1) // 2
            qm = fit_quadratic(acq.coded_to_matrix([obs_coded[i] for i in keep]),
                               np.asarray([ys[i] for i in keep], dtype=float),
                               with_2fi=len(keep) > n_full)
            st = qm.get("stationary")
            if st and st.get("inside_box"):
                center = {f"x{i}": float(v) for i, v in enumerate(st["coded"])}
                center_note = f"quadratic stationary-centered (class={st['classification']})"
        batch_rsm = 2 * k + 4 if budget_left >= 2 * k + 4 else budget_left
        raw_pts = propose_rsm_augment(center, k, batch_rsm)
        pts_c = _dedupe_fill(raw_pts, batch_rsm, "rsm")
        entries = _finish(pts_c, [f"rsm_augment: axial/corner augmentation, "
                                  f"{center_note}"], "rsm_augment")
    elif method == "poly_refine":
        ys = [e["metrics"].get(target, {}).get("mean") for e in pts]
        keep = [i for i, y in enumerate(ys) if y is not None]
        if len(keep) >= 3:
            Xc = acq.coded_to_matrix([obs_coded[i] for i in keep])
            qm = fit_quadratic(Xc, np.asarray([ys[i] for i in keep], dtype=float))
            raw_pts = propose_poly_refine(qm, specs, domain, batch, seed=seed)
            pts_c = _dedupe_fill(
                [{f"x{i}": float(p[f"x{i}"]) for i in range(k)} for p in raw_pts],
                batch, "poly")
            entries = _finish(pts_c, ["poly_refine: GP ill-conditioned — quadratic "
                                      f"model (R2={qm['r2']:.3f}) optimum + LHS filler"],
                              "poly_refine")
        else:
            pts_c = _lhs_points(k, batch, seed + round_no, obs_coded)
            entries = _finish(pts_c, ["poly_refine fallback: insufficient data "
                                      "for quadratic — LHS filler"], "poly_refine")
    elif method == "confirm_replicates":
        inc_sp = (state.get("incumbent") or {}).get("setpoints")
        if not inc_sp:
            raise ExecutionError("confirm requested but no incumbent — cannot "
                                 "confirm an unmeasured point")
        c = acq.code_point(inc_sp, domain)
        entries = _finish([c], ["confirm_replicates: incumbent confirmation "
                                "under the dual gate"], "confirm_replicates",
                          replicates=m_confirm)
    else:  # gp_ei
        if not fits:
            raise ExecutionError("gp_ei selected but GP unavailable — internal "
                                 "decision-tree inconsistency")
        extra = obs_coded + ([_incumbent_coded(state, domain)]
                             if state.get("incumbent") else [])
        cands = acq.make_candidates(domain, n_cand=256, seed=seed + round_no,
                                    extra_coded=None)
        picks = acq.greedy_batch(fits, specs, cands, obs_coded, batch, None,
                                 domain, seed=seed)
        if not picks:
            picks_c = _lhs_points(k, batch, seed + round_no, obs_coded)
            entries = _finish(picks_c, ["gp_ei fallback: candidate set masked — "
                                        "LHS filler"], "gp_ei")
        else:
            entries = _finish([p["coded"] for p in picks],
                              [f"gp_ei pick (EI={p['ei']:.4g}, "
                               f"path={p['ranking_path']})" for p in picks],
                              "gp_ei")
            for (entry, _c, _d), p in zip(entries, picks):
                entry["ei"] = round(float(p["ei"]), 6)
                entry["ucb"] = round(float(p["predicted"][target]
                                           + 1.96 * p["predicted_sd"][target]), 6)

    # duplication bookkeeping (O-G8 gating + belief). A confirm round
    # deliberately re-measures the incumbent — that is its purpose, not
    # duplication, so the ratio is pinned to 0.0 for it.
    if method == "confirm_replicates":
        dup_ratio = 0.0
    else:
        n_dup = sum(1 for (_e, _c, dup) in entries if dup)
        dup_ratio = round(n_dup / max(len(entries), 1), 6)
    design = {
        "design_version": "1.0",
        "campaign_id": o["campaign_id"],
        "round_id": f"R{round_no:03d}",
        "phase": design_phase,
        "method": method,
        "trials": [e for (e, _c, _d) in entries],
        "model_summary": None,
        "gating": {"domain_ok": True, "safety_ok": True,
                   "duplication_ratio": dup_ratio},
        "provenance": {"input_sha256": meta["sha256"],
                       "script_version": VERSION, "seed": seed,
                       "authored_by": "script"},
    }
    if fits:
        ref = next(iter(fits.values()))
        design["model_summary"] = {
            "kind": model_info["kind"],
            "log_ml": round(float(ref.log_ml), 6),
            "lengthscales": {f"x{i}": round(float(v), 6)
                             for i, v in enumerate(ref.theta[:len(numeric)])},
            "sigma_noise": round(float(ref.noise_level_std or 0.0)
                                 * float(ref.y_sd), 6),
            "fallback_active": bool(failures) and not fits,
        }
    rid = design["round_id"]
    _write_json(rounds_dir(rd) / rid / "trial_design.json", design)
    for g in guard:
        state.setdefault("guardrail_log", []).append(g)

    # state update (schema-clean keys only)
    state["budget"]["rounds_used"] = round_no
    state["budget"]["trials_used"] = int(state["budget"]["trials_used"]) + len(entries)
    state["round_count"] = round_no
    state["trial_count"] = int(state["budget"]["trials_used"])
    reps = sum(int((e.get("replicates") or 1)) for (e, _c, _d) in entries)
    state["budget"]["replicates_used"] = int(
        state["budget"]["replicates_used"] or 0) + reps
    state["belief"]["duplication_ratio"] = dup_ratio
    if state["phase"] == "initialized":
        state["phase"] = "exploring"
    state["next_action"] = {
        "recommendation": "await_results",
        "reasons": [f"round {rid} designed (method={method}, "
                    f"n={len(entries)}) — execute trials (AWS/manual), then "
                    f"place 02_rounds/{rid}/trial_result.json and run `ingest`"],
        "agent_review_required": state["next_action"].get(
            "agent_review_required", False),
    }
    hist = {h["round_id"]: h for h in state.get("history", [])}
    hist[rid] = {"round_id": rid, "phase": design_phase, "method": method,
                 "n_trials": len(entries), "best_D": None, "failures": 0,
                 "notes": f"duplication_ratio={dup_ratio}"}
    state["history"] = [hist[k2] for k2 in sorted(hist)]
    write_state(rd, state)
    print(f"[design] {rid} method={method} trials={len(entries)} "
          f"dup_ratio={dup_ratio} -> {rounds_dir(rd) / rid / 'trial_design.json'}")
    return 0


def spec_keys(o):
    keys = [obj_mod.primary_metric(o)]
    keys += [m.get("metric") for m in o.get("secondary_metrics") or []
             if m.get("metric")]
    return [k2 for k2 in keys if k2]


def _campaign_level(recs, factor, domain):
    lv = domain[factor]["levels"]
    bp = ((recs or {}).get("current_baseline") or {}).get("point") or {}
    if bp.get(factor) in lv:
        return bp[factor]
    return lv[0]


def _lhs_points(k, n, seed, avoid_coded):
    """LHS points in the coded box, deterministically avoiding the duplication
    radius of existing points (3 regeneration attempts, then accept)."""
    from optcore import DELTA_CONFIRM
    if n <= 0:
        return []
    avoid = acq.coded_to_matrix(avoid_coded)
    for attempt in range(3):
        u = lhs_uniform(n, k, seed + 1000 * attempt)
        cands = [dict(zip((f"x{i}" for i in range(k)), (2.0 * r - 1.0).tolist()))
                 for r in u]
        keep = [c for c in cands
                if avoid.size == 0
                or acq.nearest_distance(c, avoid) >= DELTA_CONFIRM]
        if len(keep) >= n:
            return keep[:n]
        best = keep
    # last resort: keep whatever passed, top up with raw LHS
    return (best + cands)[:n]


def _center_coded(domain):
    return {f"x{i}": 0.0 for i in range(len(domain))}


def _incumbent_coded(state, domain):
    inc = state.get("incumbent") or {}
    sp = inc.get("setpoints")
    if not sp:
        return None
    try:
        return acq.code_point(sp, domain)
    except (KeyError, TypeError, ValueError):
        return None


def cmd_ingest(run_dir, result_path=None):
    rd, o, meta, state, domain, recs = _campaign(run_dir)
    if state["phase"] in strategy.TERMINAL_PHASES:
        raise ExecutionError(f"campaign already {state['phase']} — nothing to ingest")
    rid = _latest_round(rd)
    if not rid:
        raise ExecutionError("no designed round found — run `design` first")
    design, _existing = load_round(rd, rid)
    rpath = _contained(result_path) if result_path \
        else rounds_dir(rd) / rid / "trial_result.json"
    if not rpath.exists():
        raise ExecutionError(
            f"trial_result.json not found for {rid} — EXECUTION CONTRACT: "
            f"execute the designed trials (AWS/manual) and write "
            f"{rpath} first")
    result = _read_json(rpath)
    _validate_result(result, design, o)

    # fold late results into their historical rounds before pooling
    if result.get("late_results"):
        state.setdefault("guardrail_log", []).append({
            "code": "LATE_RESULTS", "ts": now(),
            "detail": f"{len(result['late_results'])} late result(s) merged "
                      "into their historical rounds; no verdict rollback"})
    pool = build_pool(rd)
    target = obj_mod.primary_metric(o)
    pts = completed_points(pool, target)
    obs_means = {m: [e["metrics"][m]["mean"] for e in pts
                     if e["metrics"].get(m, {}).get("mean") is not None]
                 for m in spec_keys(o)}
    specs = obj_mod.metric_specs(o, metric_grid(obs_means))
    d_vals = d_per_point(pts, specs)
    d_span = _d_span(d_vals)

    this_round = [e for e in pool if e["round_id"] == rid and not e.get("late")]
    round_completed = [e for e in this_round
                       if e["status"] in ("completed", "partial")]
    n_fail = len(this_round) - len(round_completed)
    safety_abort = any(e["status"] == "safety_aborted" for e in this_round)

    fits, model_info, failures, _X = ([], {"kind": "unavailable"}, {}, None)
    if pts:
        fits, model_info, failures, _X = fit_models(pts, domain, specs, target)

    # incumbent + D_max
    numeric = obj_mod.numeric_factors_from_domain(domain)
    k = len(numeric)
    D_max = max(d_vals) if d_vals else 0.0
    if fits:
        cands = acq.make_candidates(domain, n_cand=256,
                                    seed=int(state["provenance"]["seed"]))
        D_max = max(D_max, _predicted_dmax(fits, specs, cands))
        ei_grid, _ei_path, ei_span = acq.evaluate_ei(fits, specs, cands,
                                                     d_span=d_span)
        max_ei = float(np.max(ei_grid))
        cov = acq.domain_coverage([acq.code_point(e["setpoints"], domain)
                                   for e in pts], domain)
    else:
        max_ei, cov, ei_span = None, None, d_span

    prev_inc = state.get("incumbent") or None
    best_e, best_d = None, None
    for e, d in zip(pts, d_vals):
        if best_d is None or d > best_d:
            best_e, best_d = e, float(d)
    if best_e:
        tgt_mean = best_e["metrics"].get(target, {}).get("mean")
        in_t = _in_target(o, tgt_mean)
        state["incumbent"] = {
            "setpoints": {f: round(float(best_e["setpoints"][f]), 6)
                          for f in sorted(best_e["setpoints"])},
            "measured": {m: {"mean": round(mm["mean"], 6),
                             "sd": round(mm["sd"], 6), "n": int(mm["n"])}
                         for m, mm in best_e["metrics"].items()
                         if mm["mean"] is not None},
            "in_target": in_t,
            "predicted_D": round(best_d, 6),
            "round_id": best_e["round_id"],
        }
    # keep the pre-update incumbent identity for the stall computation
    _prev_inc_setpoints = (prev_inc or {}).get("setpoints")

    # confirm gate evaluation when this round was the confirm round
    confirm_result = None
    confirm_values = None
    if state["phase"] == "confirming" and design.get("method") == \
            "confirm_replicates" and round_completed:
        conf = round_completed[0]
        confirm_values = conf["metrics"].get(target, {}).get("values") or []
        ci_ok, d_ok, gate_detail = _confirm_gate(o, conf, specs, D_max)
        state["target_status"]["ci_in_limits"] = bool(ci_ok)
        state["target_status"]["desirability_gate"] = bool(d_ok)
        converged, creasons = strategy.evaluate_confirm_gate(
            values=confirm_values,
            target_range=o.get("target_range"),
            ci_in_limits=bool(ci_ok), desirability_gate=bool(d_ok))
        confirm_result = (converged, creasons)
        confirm_payload = gate_detail

    # stall update: stall = consecutive rounds without finding a strictly better
    # point (incumbent setpoint identity; grid-free and deterministic — the D
    # grid rescales as data arrives, so D deltas across rounds are not signed)
    prev_sp = tuple(sorted((_prev_inc_setpoints or {}).items())) \
        if _prev_inc_setpoints else None
    new_sp = tuple(sorted(((state.get("incumbent") or {}).get("setpoints")
                           or {}).items())) if state.get("incumbent") else None
    same_point = prev_sp is not None and new_sp == prev_sp
    if state["phase"] in ("exploring", "exploiting"):
        stall = int(state["belief"].get("stall_rounds") or 0) + \
            (1 if same_point else 0)
    else:
        stall = int(state["belief"].get("stall_rounds") or 0)

    # in-window check (enter-confirm precondition)
    inc = state.get("incumbent") or {}
    if o["goal"] == "target":
        mean = (inc.get("measured") or {}).get(target, {}).get("mean")
        lo, hi = o["target_range"]
        in_window = mean is not None and bool(lo <= mean <= hi)
    else:
        in_window = bool((inc.get("predicted_D") or 0) >= DUAL_GATE_D_FRAC * D_max)

    tr = state["target_status"]
    hit = tr.get("hit_ratio_history") or []
    hit.append(round(sum(1 for e in pts
                         if _in_target(o, e["metrics"].get(target, {}).get("mean")))
                    / max(len(pts), 1), 6) if pts else 0.0)
    tr["hit_ratio_history"] = hit[-20:]

    tstate = {
        "phase": state["phase"],
        "stall_rounds": stall,
        "rounds_used": state["budget"]["rounds_used"],
        "trials_used": state["budget"]["trials_used"],
        "budget": {"max_rounds": state["budget"]["max_rounds"],
                   "max_trials": state["budget"]["max_trials"]},
        "duplication_ratio": state["belief"].get("duplication_ratio"),
        "deadline_passed": _deadline_passed(state),
        "all_fail_streak": _all_fail_streak(rd, pool),
        "safety_aborted": _had_safety_abort(rd),
        "confirm_result": confirm_result,
        "k": k,
        "n_data": len(pts),
        "y_variance_ok": bool(len(pts) >= 2 and
                              float(np.std([e["metrics"][target]["mean"]
                                            for e in pts])) > 0),
        "max_ei_last": max_ei,
        "d_span": ei_span,
        "in_window": in_window,
    }
    new_phase, next_rec, reasons, updates = strategy.transition(tstate)
    state["phase"] = new_phase
    state["belief"]["stall_rounds"] = stall
    state["belief"]["max_ei_last"] = max_ei
    state["belief"]["domain_coverage"] = cov
    state["model"] = {"kind": model_info.get("kind"),
                      "fallback_active": bool(model_info.get("fallback_active")),
                      "data_n": model_info.get("data_n"),
                      "noise_source": model_info.get("noise_source"),
                      "fit_quality": model_info.get("fit_quality")}
    state["next_action"] = {
        "recommendation": next_rec,
        "reasons": reasons,
        "agent_review_required": bool(safety_abort)
        or state["next_action"].get("agent_review_required", False),
    }
    if new_phase == "confirming":
        state["next_action"]["reasons"] = [
            "entering confirmation — next `design` emits confirm_replicates "
            f"(m>={m_confirm_default(o)}) at the incumbent"] + reasons
    if confirm_values is not None:
        state.setdefault("guardrail_log", []).append({
            "code": "CONFIRM_EVAL", "ts": now(),
            "detail": f"confirm round {rid}: values={confirm_values}, "
                      f"ci_in_limits={state['target_status']['ci_in_limits']}, "
                      f"desirability_gate={state['target_status']['desirability_gate']}"})
    if safety_abort:
        state.setdefault("guardrail_log", []).append({
            "code": "OG5_SAFETY_ABORT", "ts": now(),
            "detail": f"round {rid} contains a safety_aborted trial — "
                      "campaign aborted, human closure required"})
    hist = {h["round_id"]: h for h in state.get("history", [])}
    h = hist.setdefault(rid, {"round_id": rid, "phase": design.get("phase"),
                              "method": design.get("method"),
                              "n_trials": len(design.get("trials", [])),
                              "best_D": None, "failures": 0, "notes": None})
    h["failures"] = int(n_fail)
    round_d = [d for e, d in zip(pts, d_vals) if e["round_id"] == rid]
    # best_D is the cumulative campaign best at round close (grid rescaling
    # makes per-round-only values non-comparable across rounds)
    prev_best = None
    for h2 in state.get("history", []):
        if h2.get("best_D") is not None:
            prev_best = h2["best_D"] if prev_best is None else max(prev_best,
                                                                   h2["best_D"])
    cur_best = max(round_d) if round_d else None
    h["best_D"] = round(max(x for x in (prev_best, cur_best)
                            if x is not None), 6) \
        if (prev_best is not None or cur_best is not None) else None
    h["notes"] = (h.get("notes") or "") + \
        ("" if confirm_result is None else
         ("; dual_gate=PASS" if confirm_result[0] else
          "; confirm_failed_dual_gate"))
    state["history"] = [hist[k2] for k2 in sorted(hist)]
    write_state(rd, state)
    print(f"[ingest] {rid}: phase {tstate['phase']} -> {new_phase} "
          f"({next_rec}); stall={stall}, max_EI={max_ei}, "
          f"best_D={h['best_D']}")
    return 0


def m_confirm_default(o):
    return max(CONFIRM_MIN_REPLICATES,
               int(((o.get("noise") or {}).get("replicates_for_sigma"))
                   or CONFIRM_MIN_REPLICATES))


def _in_target(o, mean):
    """Window membership of a measured value. goal=target -> target_range;
    minimize/maximize with tolerance -> at/beyond the tolerance limit; a goal
    that declares no window cannot be judged, so it stays permissive (True)."""
    if mean is None:
        return False
    if o["goal"] == "target":
        lo, hi = o["target_range"]
        return lo <= mean <= hi
    if o["goal"] == "minimize" and o.get("tolerance") is not None:
        return mean <= float(o["tolerance"])
    if o["goal"] == "maximize" and o.get("tolerance") is not None:
        return mean >= float(o["tolerance"])
    return True


def _confirm_gate(o, conf_entry, specs, d_max):
    """One-sided 95% CI within limits + D gate. Returns (ci_ok, d_ok, detail)."""
    from scipy.stats import t as _t
    target = obj_mod.primary_metric(o)
    mm = conf_entry["metrics"].get(target)
    values = [v for v in (mm.get("values") if mm else None) or []
              if isinstance(v, (int, float))]
    n = len(values)
    mean = float(np.mean(values)) if n else None
    sd = float(np.std(values, ddof=1)) if n > 1 else 0.0
    lo = hi = None
    ci_ok = True
    if n >= 2 and mean is not None:
        half = float(_t.ppf(0.95, n - 1)) * sd / np.sqrt(n)
        lo, hi = mean - half, mean + half
        if o["goal"] == "target":
            rlo, rhi = o["target_range"]
            ci_ok = bool(lo >= rlo and hi <= rhi)
        elif o["goal"] == "maximize":
            lsl = (specs.get(target, {}).get("lsl"))
            ci_ok = True if lsl is None else bool(lo >= float(lsl))
        else:
            usl = (specs.get(target, {}).get("usl"))
            ci_ok = True if usl is None else bool(hi <= float(usl))
    means = {m: e["mean"] for m, e in conf_entry["metrics"].items()
             if e["mean"] is not None}
    clean, grid = split_grid(specs)
    d_val, _ = combined_desirability(means, clean, grid)
    d_ok = bool(d_val >= DUAL_GATE_D_FRAC * d_max) if d_max > 0 else False
    return ci_ok, d_ok, {"replicates_in_window":
                         all(_in_target(o, v) for v in values) if values else False,
                         "ci_in_limits": bool(ci_ok), "desirability_gate": d_ok,
                         "D": round(float(d_val), 6), "D_max": round(float(d_max), 6),
                         "mean": mean, "one_sided_ci": [lo, hi]}


def _validate_result(result, design, o):
    from optcore import TRIAL_STATUS
    if result.get("result_version") != "1.0":
        raise ExecutionError("trial_result.result_version must be '1.0'")
    if result.get("campaign_id") != design.get("campaign_id"):
        raise ExecutionError("trial_result.campaign_id mismatch")
    if result.get("round_id") != design.get("round_id"):
        raise ExecutionError(
            f"trial_result.round_id {result.get('round_id')} != designed "
            f"{design.get('round_id')}")
    design_ids = {t["trial_id"] for t in design.get("trials", [])}
    for t in result.get("trials", []):
        if t["trial_id"] not in design_ids:
            raise ExecutionError(
                f"trial {t['trial_id']} not in design {design['round_id']} — "
                "only designed trials may be reported")
        if t.get("status") not in TRIAL_STATUS:
            raise ExecutionError(
                f"trial {t['trial_id']}: status {t.get('status')} not in "
                f"{TRIAL_STATUS}")
        if t.get("status") in ("failed", "safety_aborted") and \
                not (t.get("failure_reason") or "").strip():
            raise ExecutionError(
                f"trial {t['trial_id']}: status={t['status']} requires a "
                "failure_reason (O-G6b)")
        for m, vals in (t.get("measurements") or {}).items():
            for v in vals or []:
                if v is not None and not isinstance(v, (int, float)):
                    raise ExecutionError(
                        f"trial {t['trial_id']} metric {m}: non-numeric "
                        f"measurement {v!r}")


def cmd_status(run_dir):
    rd, o, meta, state, domain, recs = _campaign(run_dir)
    summary = {
        "campaign_id": state["campaign_id"],
        "phase": state["phase"],
        "round_count": state["round_count"],
        "budget": state["budget"],
        "incumbent": state.get("incumbent"),
        "belief": state.get("belief"),
        "model": state.get("model"),
        "next_action": state.get("next_action"),
        "state_path": str(_state_path(rd)),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=float))
    return 0


def cmd_converge(run_dir):
    rd, o, meta, state, domain, recs = _campaign(run_dir)
    phase = state["phase"]
    if phase not in strategy.TERMINAL_PHASES:
        raise ExecutionError(
            f"phase={phase} is not terminal — EXECUTION CONTRACT: continue the "
            "design->execute->ingest loop until converged/paused/exhausted/"
            "aborted, then run `converge`")
    pool = build_pool(rd)
    target = obj_mod.primary_metric(o)
    pts = completed_points(pool, target)
    obs_means = {m: [e["metrics"][m]["mean"] for e in pts
                     if e["metrics"].get(m, {}).get("mean") is not None]
                 for m in spec_keys(o)}
    specs = obj_mod.metric_specs(o, metric_grid(obs_means))
    d_vals = d_per_point(pts, specs)
    d_span = _d_span(d_vals)
    D_max = max(d_vals) if d_vals else 0.0

    confirm_round = None
    for rid in reversed(round_ids(rd)):
        design, result = load_round(rd, rid)
        if design and design.get("method") == "confirm_replicates" and result:
            confirm_round = rid
            break
    confirm_values = []
    dual_gate = {"replicates_in_window": None, "ci_in_limits":
                 state["target_status"].get("ci_in_limits"),
                 "desirability_gate": state["target_status"].get(
                     "desirability_gate"), "D": None, "D_max": round(D_max, 6)}
    if confirm_round:
        pool_conf = [e for e in pool if e["round_id"] == confirm_round
                     and e["status"] in ("completed", "partial")]
        if pool_conf:
            confirm_values = pool_conf[0]["metrics"].get(target, {}).get(
                "values") or []
            dual_gate["replicates_in_window"] = bool(confirm_values) and all(
                _in_target(o, v) for v in confirm_values)
            clean, grid = split_grid(specs)
            means = {m: pool_conf[0]["metrics"][m]["mean"]
                     for m in pool_conf[0]["metrics"]
                     if pool_conf[0]["metrics"][m]["mean"] is not None}
            d_val, _ = combined_desirability(means, clean, grid)
            dual_gate["D"] = round(float(d_val), 6)

    stationary = None
    if len(pts) >= 3:
        curvature, cur_detail = curvature_of(pts, domain, target)
        if cur_detail:
            stationary = (cur_detail or {}).get("stationary")

    conclusion = {
        "contract_version": "1.0",
        "campaign_id": o["campaign_id"],
        "phase": phase,
        "verification": verification_of(state),
        "objective": {"target_metric": target, "goal": o["goal"],
                      "target_range": o.get("target_range"),
                      "tolerance": o.get("tolerance")},
        "incumbent": state.get("incumbent"),
        "confirm_round": confirm_round,
        "confirm_values": {target: confirm_values} if confirm_values else {},
        "dual_gate": dual_gate,
        "D_max": round(D_max, 6),
        "D_span": round(d_span, 6),
        "domain": domain,
        "model": state.get("model"),
        "stationary_point": stationary,
        "history": state.get("history", []),
        "guardrail_log": state.get("guardrail_log", []),
        "budget": state.get("budget"),
        "generated_at": now(),
        "provenance": {"script_version": VERSION,
                       "input_sha256": state.get("provenance", {}).get(
                           "input_sha256"),
                       "seed": state.get("provenance", {}).get("seed"),
                       "authored_by": "script"},
    }
    _write_json(rd / "conclusions" / "optimization_conclusion.json", conclusion)

    from optcore.experience import (achieved_metrics, guardrail_envelope,
                                    regime_key)
    inc = state.get("incumbent") or {}
    recipe = {
        "contract_version": "1.0",
        "campaign_id": o["campaign_id"],
        "regime_key": regime_key(state, o),
        "final_setpoints": inc.get("setpoints") or {},
        "achieved": achieved_metrics(
            {target: confirm_values} if confirm_values else
            {m: [mm.get("mean")] for m, mm in (inc.get("measured") or {}).items()
             if mm.get("mean") is not None}),
        "guardrails": guardrail_envelope(inc.get("setpoints") or {}, domain),
        "verification_status": verification_of(state),
        "dual_gate": dual_gate,
        "usage_rules": [
            "本文件为纯分析建议（advisory），IDD 不下发参数；执行决策由 AWS 侧做出",
            "仅在 guardrails 包络内、非外推点直接复用；越包络或越支撑需重新验证",
            "regime_key 场景化复用；跨工况使用前必须重新验证",
        ],
        "provenance": conclusion["provenance"],
    }
    _write_json(rd / "conclusions" / "recipe.json", recipe)

    report = render_report(conclusion, recipe, o, state)
    _write_text(rd / "report.md", report)

    written = write_experience(rd, state, o, conclusion)
    state["stop_resume"] = {"can_pause": False,
                            "resume_hint": f"campaign {phase} closed"}
    write_state(rd, state)
    print(f"[converge] phase={phase}; wrote conclusions/"
          f"optimization_conclusion.json, conclusions/recipe.json, report.md"
          + (f", {len(written)} experience file(s)" if written else ""))
    return 0


def render_report(conclusion, recipe, o, state):
    from optcore import DUAL_GATE_D_FRAC as DG
    inc = conclusion.get("incumbent") or {}
    dg = conclusion.get("dual_gate") or {}
    hist_rows = "\n".join(
        f"| {h['round_id']} | {h.get('phase')} | {h.get('method')} | "
        f"{h.get('n_trials')} | {h.get('best_D')} | {h.get('failures')} |"
        for h in conclusion.get("history") or [])
    return f"""# 优化闭环报告 · {o['campaign_id']}

> 本报告由 `optimizer.py converge` 确定性生成（零 LLM）；全部数字为脚本产出，
> agent 只做解读，绝不改写数值。IDD 为纯分析系统：本报告只产分析工件，不下发参数。

## 概要

- 阶段：**{conclusion['phase']}**（验证状态：{conclusion.get('verification')}）
- 目标：{o['target_metric']} · goal={o['goal']} · target_range={o.get('target_range')}
- 预算使用：{state['budget'].get('rounds_used')}/{state['budget']['max_rounds']} 轮，
  {state['budget'].get('trials_used')}/{state['budget']['max_trials']} 试验点，
  重复 {state['budget'].get('replicates_used')} 次

## 最优点（incumbent）

```json
{json.dumps(inc.get('setpoints') or {}, ensure_ascii=False, indent=2)}
```

{json.dumps(inc.get('measured') or {}, ensure_ascii=False)}

## 收敛判定（双门槛）

- m≥3 重复全落窗：{dg.get('replicates_in_window')}
- 单侧 95% CI 在限内：{dg.get('ci_in_limits')}
- D ≥ {DG}·D_max：{dg.get('desirability_gate')}（D={dg.get('D')}，
  D_max={dg.get('D_max')}）

## 轮次历史

| 轮 | 阶段 | 方法 | 试验数 | best_D | 失败 |
|---|---|---|---|---|---|
{hist_rows}

## 护栏事件

{json.dumps(conclusion.get('guardrail_log') or [], ensure_ascii=False, indent=2)}

## 复用

见 `conclusions/recipe.json`（含 guardrails 包络与 usage_rules）与
`06_experience/kb_summary.md`（regime_key 场景化摘要，供 AWS 经 kb_agent 入库）。
"""


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="optimizer.py",
        description="industrial-optimizer-loop — pure-analysis closed-loop "
                    "optimization (design/analysis artifacts only; never "
                    "dispatches parameters)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_common(p):
        p.add_argument("--run-dir", required=True)
    p_init = sub.add_parser("init", help="create campaign skeleton + O-G1 check")
    add_common(p_init)
    p_init.add_argument("--objective", default=None,
                        help="objective.json to copy into 00_input/")
    p_design = sub.add_parser("design", help="produce next round trial_design.json")
    add_common(p_design)
    p_ing = sub.add_parser("ingest", help="ingest trial_result.json + transition")
    add_common(p_ing)
    p_ing.add_argument("--result", default=None,
                       help="trial_result.json path (default: latest round)")
    p_status = sub.add_parser("status", help="print campaign state summary")
    add_common(p_status)
    p_conv = sub.add_parser("converge", help="terminal phase -> conclusions + recipe")
    add_common(p_conv)

    args = ap.parse_args(argv)
    try:
        if args.cmd == "init":
            return cmd_init(args.run_dir, args.objective)
        if args.cmd == "design":
            return cmd_design(args.run_dir)
        if args.cmd == "ingest":
            return cmd_ingest(args.run_dir, args.result)
        if args.cmd == "status":
            return cmd_status(args.run_dir)
        if args.cmd == "converge":
            return cmd_converge(args.run_dir)
    except (ExecutionError, obj_mod.ObjectiveError) as exc:
        print(f"[optimizer] CONTRACT ERROR: {exc}", file=sys.stderr)
        print("EXECUTION CONTRACT: fix the named artifact or run the named "
              "step, then re-run this subcommand. Never hand-edit numbers "
              "authored_by=script.", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
