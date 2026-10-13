#!/usr/bin/env python3
"""verify_enhancement.py — one-shot verifier for the E1→E3.5 outputs.

Replaces the per-phase checkbox loop in the deep-analysis protocol: a single
run asserts every structural invariant the agent protocol asks for and exits
non-zero on the first violation, printing the exact failing rule.

Checked artifacts (present + non-empty):
    RUN_DIR/enhancement/analysis_coverage.json      (E1)
    RUN_DIR/enhancement/derived_features.json       (E2)
    RUN_DIR/enhancement/derived_data.csv            (E2)
    RUN_DIR/enhancement/deep_data_analysis.json     (E3 + E4 tradeoffs)
    RUN_DIR/enhancement/association_graph.json      (E3.5, emitted by E3)

CLI::

    python verify_enhancement.py --run-dir RUN_DIR
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

COVERAGE_STATUSES = {
    "covered_primary", "covered_conditional", "pruned_physics",
    "pruned_confounded", "not_applicable", "insufficient_data",
    "derived_and_used",
}
OPERABILITY = {
    "ENDOGENOUS_RESPONSE", "CONFOUNDED", "CONSTRAINT_UNCONTROLLABLE",
    "NOT_IDENTIFIABLE", "LEVER_IDENTIFIED", "LEVER_OBSERVATIONAL",
}
EDGE_RELATIONS = {"supports", "inhibits", "contradicts"}
TRADEOFF_FIELDS = [
    "parameter", "controllability", "effects_on_targets", "tradeoff_summary",
    "operability_assessment", "support_domain", "extrapolation_warning",
    "open_questions",
]
VALIDITY_FLAGS = [
    "simpson_paradox_checked", "confounding_checked", "trend_confounding_checked",
    "change_point_tested", "batch_effect_tested", "lag_significant",
    "outlier_influence_checked", "insufficient_data",
]


class Failures(list):
    def check(self, cond: bool, rule: str) -> None:
        if not cond:
            self.append(rule)


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    ap = argparse.ArgumentParser(description="One-shot enhancement verifier")
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    run = Path(args.run_dir)
    f: Failures = Failures()

    for rel in (
        "01_ontology/ontology.json",
        "02_processed/feature_summary.json",
        "02_processed/cleaned_data.csv",
        "enhancement/analysis_coverage.json",
        "enhancement/derived_features.json",
        "enhancement/derived_data.csv",
        "enhancement/deep_data_analysis.json",
        "enhancement/association_graph.json",
    ):
        f.check((run / rel).is_file(), f"missing artifact: {rel}")
    if f:
        print(json.dumps({"ok": False, "failures": list(f)}, ensure_ascii=False, indent=1))
        return 1

    # ---- input columns ----
    with open(run / "02_processed/cleaned_data.csv", encoding="utf-8-sig") as fh:
        csv_cols = next(csv.reader(fh))
    ontology = load(run / "01_ontology/ontology.json")
    onto_rels = ontology.get("relationships", []) or []

    # ---- E1 coverage ----
    cov = load(run / "enhancement/analysis_coverage.json")
    cov_cols = {c.get("column") for c in cov.get("columns", [])}
    f.check(bool(cov_cols), "E1: columns[] is empty")
    missing = [c for c in csv_cols if c not in cov_cols]
    f.check(not missing, f"E1: cleaned columns missing from coverage: {missing[:5]}")
    for c in cov.get("columns", []):
        st = c.get("coverage_status")
        f.check(st in COVERAGE_STATUSES, f"E1: bad coverage_status {st!r} on {c.get('column')}")
        f.check("unit" in c, f"E1: {c.get('column')} lacks unit")
        f.check("support_domain" in c, f"E1: {c.get('column')} lacks support_domain")
        if st in ("pruned_physics", "pruned_confounded", "not_applicable", "insufficient_data"):
            f.check(bool(c.get("reason")), f"E1: {c.get('column')} pruned without reason")

    # ---- E2 derived features ----
    feats = load(run / "enhancement/derived_features.json").get("features", [])
    with open(run / "enhancement/derived_data.csv", encoding="utf-8-sig") as fh:
        derived_cols = set(next(csv.reader(fh)))
    for feat in feats:
        name = feat.get("name", "")
        if feat.get("status") == "computed":
            f.check(feat.get("derived") is True, f"E2: computed {name} lacks derived:true")
            f.check(name in derived_cols, f"E2: computed {name} absent from derived_data.csv")
        else:
            f.check(feat.get("derived") is False, f"E2: non-computed {name} has derived:true")
            f.check(bool(feat.get("formula")), f"E2: skipped {name} lacks formula")
            f.check(bool(feat.get("reason")), f"E2: skipped {name} lacks reason")

    # ---- E3 relationships + E4 tradeoffs ----
    deep = load(run / "enhancement/deep_data_analysis.json")
    rels = deep.get("relationships", [])
    f.check(bool(rels), "E3: relationships[] is empty")
    seen_pairs = set()
    for r in rels:
        pair = (r.get("predictor"), r.get("target"))
        seen_pairs.add(pair)
        tag = f"{pair[0]}->{pair[1]}"
        f.check(pair[0] != pair[1], f"E3: predictor == target on {tag}")
        q = r.get("q_value")
        f.check(isinstance(q, (int, float)) and 0.0 <= q <= 1.0, f"E3: q_value out of range on {tag}")
        f.check(q != 0.0 or r.get("p_floor_hit") is True, f"E3: q=0 without p_floor_hit on {tag}")
        flags = r.get("validity_flags", {})
        for k in VALIDITY_FLAGS:
            f.check(k in flags, f"E3: {tag} lacks validity flag {k}")
        op = r.get("operability")
        f.check(op in OPERABILITY, f"E3: bad operability {op!r} on {tag}")
        pf = r.get("partial_full", {})
        f.check("method" in pf and "partial_r" in pf, f"E3: {tag} lacks partial_full record")
    for rel in onto_rels:
        a, b = rel.get("from", ""), rel.get("to", "")
        if a and b and (a, b) not in seen_pairs and (b, a) not in seen_pairs:
            # ontology edges may resolve to suffixed column names; warn only
            print(f"NOTE: ontology edge {a}->{b} not matched verbatim in relationships[]")
    tradeoffs = deep.get("tradeoff_and_operability", [])
    f.check(bool(tradeoffs), "E4: tradeoff_and_operability[] is empty")
    for t in tradeoffs:
        for k in TRADEOFF_FIELDS:
            f.check(k in t, f"E4: tradeoff {t.get('parameter')} lacks {k}")
        f.check(t.get("operability_assessment") in OPERABILITY,
                f"E4: bad operability on {t.get('parameter')}")

    # ---- E3.5 graph ----
    g = load(run / "enhancement/association_graph.json")
    f.check(len(g.get("nodes", [])) > 0, "E3.5: graph has no nodes")
    node_ids = {n.get("id") for n in g.get("nodes", [])}
    for e in g.get("edges", []):
        tag = f"{e.get('source')}->{e.get('target')}"
        f.check(e.get("source") in node_ids and e.get("target") in node_ids,
                f"E3.5: edge {tag} references unknown node")
        f.check(e.get("relationship") in EDGE_RELATIONS, f"E3.5: bad relationship on {tag}")
        for k in ("sign", "confidence", "causal_ceiling", "ontology_contradiction",
                  "statistical_evidence"):
            f.check(k in e, f"E3.5: edge {tag} lacks {k}")
    f.check(int(g.get("n_nodes", -1)) == len(g.get("nodes", [])) and
            int(g.get("n_edges", -1)) == len(g.get("edges", [])),
            "E3.5: n_nodes/n_edges disagree with nodes[]/edges[]")

    ok = not f
    print(json.dumps({"ok": ok, "n_failures": len(f), "n_relationships": len(rels),
                      "n_tradeoffs": len(tradeoffs), "n_nodes": len(node_ids),
                      "n_edges": len(g.get("edges", []))},
                     ensure_ascii=False))
    for rule in f:
        print("FAIL:", rule)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
