#!/usr/bin/env python3
"""association_graph_builder.py — E3.5 CLI entry point.

Builds ``RUN_DIR/enhancement/association_graph.json`` from the deep-data
analysis and the full pairwise scan. Thin wrapper over
``inference_engine.build_association_graph`` so the orchestrator can run the
graph stage independently of the E3 relationship computation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from inference_engine import (  # noqa: E402
    build_association_graph,
    pairwise_scan,
)


def main() -> None:
    ap = argparse.ArgumentParser(description="E3.5: Association graph builder")
    ap.add_argument("--run-dir", required=True, help="Path to diagnostic RUN_DIR")
    ap.add_argument("--output", default=None, help="Output JSON path")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"ERROR: run-dir does not exist: {run_dir}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output) if args.output else run_dir / "enhancement" / "association_graph.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(p: Path) -> dict:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)

    ontology = _load(run_dir / "01_ontology" / "ontology.json")
    selection = _load(run_dir / "02_processed" / "analysis_parameter_selection.json")

    deep_path = run_dir / "enhancement" / "deep_data_analysis.json"
    relationships = _load(deep_path).get("relationships", []) if deep_path.is_file() else []

    csv = run_dir / "enhancement" / "derived_data.csv"
    if not csv.is_file():
        csv = run_dir / "02_processed" / "cleaned_data.csv"
    df = pd.read_csv(csv)

    # Numeric analysis columns: drop metadata, time, deviation aggregates and
    # regime one-hot partitions (they are moderators, not numeric drivers).
    meta = set(selection.get("metadata_cols", []) or [])
    exclude = {c for c in df.columns if c.lower() in
               ("timestamp", "time", "datetime", "date", "time_hours") or c.lower().startswith("ts_")}
    exclude |= meta
    exclude |= {c for c in df.columns if c.endswith("_dev") or c.startswith("regime_")}
    numeric_cols = [c for c in df.columns
                    if c not in exclude
                    and pd.to_numeric(df[c], errors="coerce").nunique(dropna=True) > 1]

    pairwise = pairwise_scan(df, numeric_cols)
    graph = build_association_graph(df, numeric_cols, ontology, selection,
                                    relationships, pairwise)

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(graph, fh, indent=2, ensure_ascii=False, default=str)
    print(f"[association_graph_builder] {len(graph['nodes'])} nodes, "
          f"{len(graph['edges'])} edges → {out_path}")


if __name__ == "__main__":
    main()
