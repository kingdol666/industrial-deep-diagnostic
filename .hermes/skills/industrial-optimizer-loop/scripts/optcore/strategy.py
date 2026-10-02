"""strategy.py — pure state machine + method decision tree (unit-testable, no IO).

Phases (closedloop_enums.json optimizer.phases):
  initialized -> exploring -> exploiting -> confirming -> converged
  confirming -> exploiting      (fake-summit fallback; LHS points injected next)
  any active -> paused          (2 consecutive all-fail rounds | deadline passed
                                 | guardrail pressure)
  any active -> exhausted       (rounds/trials budget exhausted | duplication>0.5)
  any active -> aborted         (safety_aborted trial result; human closes)

Convergence is the USER-DECIDED dual gate (closedloop_enums.optimizer.convergence):
  m >= 3 confirm replicates all inside target_range
  AND one-sided 95% CI within limits
  AND D(x) >= 0.8 * D_max.

Method decision tree (deterministic, plan §5.1):
  confirming                                -> confirm_replicates
  R1 and prior has valid windows            -> window_seed
  R1 (no prior)                             -> lhs_fill
  k > 8                                     -> screen_first
  fake-summit fallback pending              -> lhs_fill (injected LHS points)
  batch >= 2k+4 and curvature evidence      -> rsm_augment
  GP healthy                                -> gp_ei
  GP ill-conditioned                        -> poly_refine
"""

from . import (DELTA_CONFIRM, DUAL_GATE_D_FRAC, DUP_RATIO_MAX, EPS_EI_FRAC,
               EXPLORE_N_MIN, MC_SAMPLES, MC_SEED, STALL_ROUNDS)

ACTIVE_PHASES = ("initialized", "exploring", "exploiting", "confirming")
TERMINAL_PHASES = ("converged", "paused", "exhausted", "aborted")

DESIGN_PHASE_OF = {
    "initialized": "explore",
    "exploring": "explore",
    "exploiting": "exploit",
    "confirming": "confirm",
}


def explore_target_n(k):
    """exploring -> exploiting requires n_data >= max(2k+3, 8)."""
    return max(2 * k + 3, EXPLORE_N_MIN)


def choose_method(*, round_no, phase, k, n_data, prior_valid, batch_size,
                  curvature, gp_healthy, fallback_pending):
    """Pure decision tree. round_no is 1-based (the round about to be designed)."""
    if phase == "confirming":
        return "confirm_replicates"
    if round_no == 1 and prior_valid:
        return "window_seed"
    if round_no == 1:
        return "lhs_fill"
    if k > 8:
        return "screen_first"
    if fallback_pending:
        return "lhs_fill"
    if batch_size is not None and batch_size >= 2 * k + 4 and curvature:
        return "rsm_augment"
    if gp_healthy:
        return "gp_ei"
    return "poly_refine"


def default_batch(method, *, k, n_data, trials_per_round, budget_left):
    """Deterministic batch size per method. trials_per_round = [min, max] or None."""
    lo, hi = (trials_per_round or (1, max(2, 2 * k + 4)))
    lo, hi = int(lo), int(hi)
    if method == "lhs_fill":
        need = max(explore_target_n(k) - n_data, min(2, hi))
        batch = min(max(need, lo), hi)
    elif method == "rsm_augment":
        batch = 2 * k + 4
    elif method == "screen_first":
        batch = min(max(2 * k, lo), hi)
    elif method == "window_seed":
        batch = 3  # W2 optimum + window center + current baseline
    elif method == "confirm_replicates":
        batch = 1
    else:  # gp_ei / poly_refine — single-point rounds by default
        batch = 1
    return max(1, min(batch, budget_left))


def evaluate_enter_confirm(*, phase, n_data, k, in_window, max_ei, d_span,
                           stall_rounds):
    """exploiting -> confirming trigger: candidate in window AND (EI<eps OR stall)."""
    if phase != "exploiting":
        return False, []
    if n_data < explore_target_n(k):
        return False, ["data below exploring threshold"]
    eps = eps_ei(d_span)
    reasons = []
    if not in_window:
        return False, ["candidate not in window"]
    if max_ei is not None and max_ei < eps:
        reasons.append(f"EI {max_ei:.4g} < eps_EI {eps:.4g}")
    if stall_rounds is not None and stall_rounds >= STALL_ROUNDS:
        reasons.append(f"stall {stall_rounds} >= {STALL_ROUNDS}")
    return bool(reasons), reasons


def eps_ei(d_span):
    """eps_EI = 0.005 * D_span (pinned fraction; D_span = observed D range)."""
    span = d_span if d_span and d_span > 1e-12 else 1.0
    return EPS_EI_FRAC * span


def evaluate_confirm_gate(*, values, target_range, ci_in_limits,
                          desirability_gate):
    """Dual convergence gate. Returns (converged: bool, reasons: [str]).

    values = the m replicate measurements of the confirmed point (target metric).
    m >= CONFIRM_MIN_REPLICATES and (goal=target: all values in range).
    """
    reasons = []
    m = len([v for v in values if v is not None])
    if m < 3:
        reasons.append(f"only {m} confirm replicate(s), need >= 3")
        return False, reasons
    if target_range is not None:
        lo, hi = float(target_range[0]), float(target_range[1])
        outside = [v for v in values if v is not None and not (lo <= v <= hi)]
        if outside:
            reasons.append(f"{len(outside)} replicate(s) outside target_range")
    if not ci_in_limits:
        reasons.append("one-sided 95% CI not within limits")
    if not desirability_gate:
        reasons.append(f"D < {DUAL_GATE_D_FRAC}*D_max")
    return not reasons, reasons


def transition(state):
    """Pure phase transition.

    state: dict with keys phase, stall_rounds, rounds_used, trials_used,
           budget(max_rounds, max_trials), duplication_ratio, deadline_passed,
           all_fail_streak, safety_aborted, confirm_pending, confirm_result

    Returns (new_phase, next_action, reasons, updates dict).
    """
    phase = state["phase"]
    reasons = []
    updates = {}
    b = state.get("budget") or {}
    budget_gone = (b.get("max_rounds") and state.get("rounds_used", 0) >= b["max_rounds"]) \
        or (b.get("max_trials") and state.get("trials_used", 0) >= b["max_trials"])

    if state.get("safety_aborted"):
        return ("aborted", "needs_human",
                ["trial_result status=safety_aborted — safety limit hit; "
                 "human must close the campaign (O-G5)"], {})

    if phase in TERMINAL_PHASES:
        return (phase, "stop", [f"campaign already {phase}"], {})

    # confirm round resolution takes priority over budget accounting: the
    # confirm round already ran; its verdict must not be swallowed by
    # exhaustion (the confirm re-measures the incumbent by design). A FAILED
    # confirm with an exhausted budget has no room for the fake-summit
    # fallback, so the honest terminal state is exhausted.
    if phase == "confirming" and state.get("confirm_result") is not None:
        converged, creasons = state["confirm_result"]
        if converged:
            return ("converged", "stop",
                    ["dual gate satisfied"] + creasons, {})
        if budget_gone:
            return ("exhausted", "stop",
                    ["confirm failed the dual gate and budget is exhausted"]
                    + creasons, {})
        updates["fallback_pending"] = True
        updates["all_fail_streak"] = 0
        return ("exploiting", "resume_exploit",
                ["confirm failed the dual gate — fake-summit fallback, LHS "
                 "points injected next round"] + creasons, updates)

    # deadline / all-fail pauses come before exhaustion (needs_human wins)
    if state.get("deadline_passed"):
        return ("paused", "needs_human", ["deadline passed"], {})
    if state.get("all_fail_streak", 0) >= STALL_ROUNDS:
        return ("paused", "needs_human",
                [f"{state['all_fail_streak']} consecutive all-failed rounds"], {})

    # initialized -> exploring happens at first design
    if phase == "initialized":
        return ("exploring", "continue_exploit",
                ["campaign initialized — design R001"], {})

    # exploring -> exploiting
    k = state.get("k", 0)
    n_data = state.get("n_data", 0)
    if phase == "exploring":
        if n_data >= explore_target_n(k) and state.get("y_variance_ok", False):
            return ("exploiting", "continue_exploit",
                    [f"n_data {n_data} >= max(2k+3, 8) and response variance > 0"],
                    {})
        return (phase, "continue_exploit",
                ["exploring: accumulate space-filling data"], {})

    # exploiting -> confirming? Evaluated BEFORE budget exhaustion: a campaign
    # that hits its budget exactly when the confirm signal fires overdrafts a
    # single confirm design point instead of stranding (pinned in
    # references/method_notes.md "confirm 透支 1 个设计点").
    if phase == "exploiting":
        enter, ereasons = evaluate_enter_confirm(
            phase=phase, n_data=n_data, k=k,
            in_window=state.get("in_window", False),
            max_ei=state.get("max_ei_last"), d_span=state.get("d_span"),
            stall_rounds=state.get("stall_rounds"))
        if enter:
            return ("confirming", "enter_confirm",
                    ["entering confirmation"] + ereasons, {})

    # budget / duplication exhaustion (after confirm resolution/entry so the
    # confirm verdict or the confirm entry is never swallowed)
    if budget_gone:
        return ("exhausted", "stop", ["budget exhausted"], {})
    if (state.get("duplication_ratio") or 0) > DUP_RATIO_MAX:
        return ("exhausted", "stop",
                [f"duplication_ratio {state.get('duplication_ratio'):.2f} > "
                 f"{DUP_RATIO_MAX}"], {})

    if phase == "exploiting":
        return (phase, "continue_exploit",
                ["exploiting — no confirm signal yet"], {})

    return (phase, "continue_exploit", ["no transition condition met"], {})


def stall_update(prev_best_d, new_best_d, d_span):
    """stall_rounds += 1 when round improvement < eps_EI on the D scale."""
    eps = eps_ei(d_span)
    improved = (new_best_d is not None
                and (prev_best_d is None or new_best_d - prev_best_d >= eps))
    return 0 if improved else None  # None = caller increments


def coded_distance(a, b, numeric):
    """Euclidean distance in coded [-1,1] space over numeric factors."""
    import math
    return math.sqrt(sum((float(a[f]) - float(b[f])) ** 2 for f in numeric))
