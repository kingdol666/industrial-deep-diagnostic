#!/usr/bin/env python3
"""
AI Experiment Recommendation Engine
=====================================
Analyzes past experiment results and recommends next-step experiments.

Usage:
  python recommend.py --experiments cleaned.json --output recommendations.json
  python recommend.py --experiments cleaned.json --output recs.json --mode optimize --n-recommendations 3
  python recommend.py --experiments cleaned.json --goal "Maximize transmittance" --output recs.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None


def analyze_experiments(experiments):
    numeric_vars = {}
    categorical_vars = {}

    for exp in experiments:
        for key, val in exp.get("variables", {}).items():
            if val is None:
                continue
            if isinstance(val, dict):
                v = val.get("value")
                u = val.get("unit")
                if v is not None and isinstance(v, (int, float)):
                    numeric_vars.setdefault(key, []).append({"value": v, "unit": u})
            elif isinstance(val, (int, float)):
                numeric_vars.setdefault(key, []).append({"value": val, "unit": None})
            else:
                categorical_vars.setdefault(key, set()).add(str(val))

    param_summary = {}
    for col, entries in numeric_vars.items():
        values = [e["value"] for e in entries]
        unit = entries[0]["unit"]
        if len(values) >= 2:
            param_summary[col] = {
                "min": round(min(values), 3),
                "max": round(max(values), 3),
                "mean": round(float(np.mean(values)), 3),
                "std": round(float(np.std(values, ddof=1)), 3),
                "n": len(values),
                "unit": unit,
                "n_unique": len(set(round(v, 4) for v in values)),
            }
        else:
            param_summary[col] = {
                "value": values[0] if values else None,
                "unit": unit,
                "n": len(values),
                "n_unique": 1,
            }

    return param_summary, categorical_vars


def identify_gaps(param_summary, parameters_varied):
    gaps = []
    for col, info in param_summary.items():
        if info.get("n_unique", 0) <= 1:
            continue
        if info.get("n_unique", 0) <= 2:
            gaps.append({
                "parameter": col,
                "unexplored_range": f"Between {info['min']} and {info['max']}",
                "resolution": "coarse",
                "reason": f"Only {info['n']} data points covering {info['n_unique']} unique values. Finer steps needed.",
            })
        if "min" in info and "max" in info:
            span = info["max"] - info["min"]
            if span > 0 and info.get("n_unique", 0) / span < 0.5:
                gaps.append({
                    "parameter": col,
                    "range": [info["min"], info["max"]],
                    "resolution": "sparse",
                    "reason": "Wide range with few data points. Resolution may be insufficient.",
                })

    return gaps[:5]


def generate_recommendations(param_summary, goal, n_recommendations, mode):
    recommendations = []

    varied_params = [col for col, info in param_summary.items() if info.get("n_unique", 0) > 1]
    fixed_params = [col for col, info in param_summary.items() if info.get("n_unique", 0) <= 1]

    if varied_params and mode in ("optimize", "auto"):
        best_param = varied_params[0]
        info = param_summary[best_param]
        if info.get("n_unique", 0) > 1 and "min" in info and "max" in info:
            mid = (info["min"] + info["max"]) / 2
            step = (info["max"] - info["min"]) / max(info["n_unique"] - 1, 1) / 2
            recommendations.append({
                "id": 1, "type": "optimize", "priority": 1,
                "title": f"Fine-tune {best_param} around current optimum",
                "description": f"Current {best_param} range: {info['min']}-{info['max']} {info.get('unit', '')}. Test finer steps to locate the true optimum.",
                "parameters": {
                    best_param: [round(x, 3) for x in [mid - step, mid, mid + step]],
                },
                "justification": {
                    "data_evidence": f"{best_param} varies across {info['n_unique']} levels (range: {info['min']}-{info['max']})",
                    "chemical_principle": "Parameter optimization requires sufficient resolution to detect non-linear effects.",
                    "expected_outcome": f"Identify the {best_param} value yielding optimal performance.",
                    "success_metric": f"Optimal {best_param} value identified",
                    "failure_modes": "If no clear optimum found, broaden parameter range.",
                    "safety_notes": "Standard lab safety procedures.",
                },
                "confidence": "medium",
            })

    gaps = identify_gaps(param_summary, varied_params)
    gap_id = len(recommendations) + 1
    for gap in gaps[:2]:
        if len(recommendations) >= n_recommendations:
            break
        recommendations.append({
            "id": gap_id, "type": "explore", "priority": 2,
            "title": f"Explore {gap['parameter']} parameter space",
            "description": gap["reason"],
            "parameters": {"action": "explore", "parameter": gap["parameter"]},
            "justification": {
                "data_evidence": f"Current data has {gap['resolution']} coverage of {gap['parameter']}.",
                "chemical_principle": "Systematic parameter exploration reveals structure-property relationships.",
                "expected_outcome": "Better understanding of parameter effects.",
                "success_metric": "Complete parameter-response mapping",
                "failure_modes": "If no effect found, parameter may not be relevant.",
                "safety_notes": "Standard lab safety.",
            },
            "confidence": "medium",
        })
        gap_id += 1

    if len(recommendations) < n_recommendations:
        recommendations.append({
            "id": len(recommendations) + 1, "type": "validate", "priority": 3,
            "title": "Replicate key experiments for statistical validity",
            "description": "Running replicates of the most promising conditions ensures reproducibility.",
            "parameters": {"action": "replicate", "n_replicates": 3},
            "justification": {
                "data_evidence": "Single measurements lack statistical power.",
                "chemical_principle": "Reproducibility is fundamental to scientific validity.",
                "expected_outcome": "Confidence intervals for key measurements.",
                "success_metric": "Coefficient of variation < 5%",
                "failure_modes": "High variance suggests uncontrolled variables.",
                "safety_notes": "Standard lab safety.",
            },
            "confidence": "high",
        })

    strategy_steps = []
    for r in recommendations:
        strategy_steps.append(f"{r['priority']}) {r['title']}")

    return recommendations, strategy_steps


def main():
    parser = argparse.ArgumentParser(description="AI Experiment Recommendation Engine")
    parser.add_argument("--experiments", required=True, help="Cleaned experiment data JSON file")
    parser.add_argument("--output", required=True, help="Output recommendations JSON file")
    parser.add_argument("--mode", default="auto", choices=["auto", "optimize", "explore", "validate"], help="Recommendation mode")
    parser.add_argument("--goal", default=None, help="Experiment goal description")
    parser.add_argument("--n-recommendations", type=int, default=3, help="Number of recommendations to generate")
    parser.add_argument("--constraints", default=None, help="Constraints JSON file or string")

    args = parser.parse_args()

    if not Path(args.experiments).exists():
        print(f"ERROR: Experiments file not found: {args.experiments}", file=sys.stderr)
        sys.exit(1)

    with open(args.experiments, "r", encoding="utf-8") as f:
        data = json.load(f)

    experiments = data.get("experiments", [])
    if not experiments:
        print("WARNING: No experiments found in data. Output will be minimal.", file=sys.stderr)

    param_summary, categorical_vars = analyze_experiments(experiments)

    varied_params = [col for col, info in param_summary.items() if info.get("n_unique", 0) > 1]
    fixed_params = [col for col, info in param_summary.items() if info.get("n_unique", 0) <= 1]

    recommendations, strategy_steps = generate_recommendations(
        param_summary, args.goal, args.n_recommendations, args.mode
    )

    result = {
        "metadata": {
            "script": "recommend.py",
            "version": "1.0.0",
            "n_experiments_analyzed": len(experiments),
            "processing_timestamp": datetime.utcnow().isoformat() + "Z",
            "mode": args.mode,
            "goal": args.goal,
        },
        "current_state_summary": {
            "parameters_varied": varied_params,
            "parameters_fixed": fixed_params,
            "parameter_details": param_summary,
            "trends_observed": [],
        },
        "information_gaps": identify_gaps(param_summary, varied_params),
        "recommendations": recommendations,
        "iterative_strategy": " → ".join(strategy_steps),
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(recommendations)} recommendations")
    for r in recommendations:
        print(f"  [{r['id']}] ({r['type']}) {r['title']}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()