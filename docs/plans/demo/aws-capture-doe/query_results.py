#!/usr/bin/env python
"""Keyword search over the committed result index.

    python query_results.py 厚度
    python query_results.py "联合设定点" --json
    python query_results.py 漂移 --index path/to/results_index.json

The index is built by run_demo.py. Paths in `evidence/results_index.json` are
relative to the index's own directory, so the search works in a fresh clone.
Exit 0 = at least one hit, 1 = none.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_INDEX = HERE / "evidence" / "results_index.json"


def search(index_path: Path, query: str) -> list[dict]:
    doc = json.loads(index_path.read_text(encoding="utf-8"))
    base = index_path.parent
    q = query.strip().lower()
    hits = []
    for e in doc.get("entries") or []:
        hay = " ".join([str(e.get("id", "")), str(e.get("title", "")),
                        " ".join(str(t) for t in e.get("tags") or []),
                        str(e.get("summary", ""))]).lower()
        if q in hay:
            path = Path(e.get("path", ""))
            hits.append({
                "id": e.get("id"), "title": e.get("title"),
                "path": str(path if path.is_absolute() else (base / path)),
                "summary": e.get("summary"), "metrics": e.get("metrics") or {},
            })
    return hits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", help="keyword (Chinese or English)")
    ap.add_argument("--index", default=str(DEFAULT_INDEX))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    index = Path(args.index).resolve()
    if not index.is_file():
        print(f"ERROR: index not found: {index}", file=sys.stderr)
        return 1
    hits = search(index, args.query)
    if args.json:
        print(json.dumps({"query": args.query, "hits": hits}, ensure_ascii=False, indent=2))
    else:
        print(f"[query] {args.query!r}: {len(hits)} hit(s)")
        for h in hits:
            print(f"- {h['id']}  {h['title']}")
            print(f"  {h['path']}")
            print(f"  {h['summary']}")
            if h["metrics"]:
                print(f"  metrics: {json.dumps(h['metrics'], ensure_ascii=False)[:300]}")
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
