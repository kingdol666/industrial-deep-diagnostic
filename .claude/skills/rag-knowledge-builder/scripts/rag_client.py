#!/usr/bin/env python3
"""
RAG Engine HTTP Client.

Called by the rag-knowledge-builder skill. Uses `uv run` for Python execution.
The diagnostic skill's uv_env_setup.mjs ensures uv is available.
All retrieval, scoring, and injection happens server-side via the RAG engine HTTP API.

Usage:
  uv run python scripts/rag_client.py pipeline --scenario "..." --target-cols "..." --param-cols "..." --output-dir <path>
"""

import argparse, json, os, sys, time
from pathlib import Path
from typing import Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Default engine endpoint
ENGINE_URL = os.environ.get("RAG_ENGINE_URL", "http://localhost:8765")


def _post(endpoint: str, data: dict) -> dict:
    """Send POST request to engine. Returns parsed JSON response."""
    url = f"{ENGINE_URL}/{endpoint.lstrip('/')}"
    body = json.dumps(data).encode('utf-8')
    req = Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except HTTPError as e:
        msg = e.read().decode('utf-8') if e.fp else str(e)
        raise RuntimeError(f"Engine returned {e.code}: {msg}") from e
    except URLError as e:
        raise RuntimeError(
            f"Cannot reach engine at {ENGINE_URL}. Is the service running?\n"
            f"  Start: cd rag-retrieval-engine && python server.py\n"
            f"  Error: {e.reason}"
        ) from e


def _get(endpoint: str) -> dict:
    """Send GET request to engine."""
    url = f"{ENGINE_URL}/{endpoint.lstrip('/')}"
    try:
        with urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except URLError as e:
        raise RuntimeError(f"Cannot reach engine at {ENGINE_URL}. Error: {e.reason}")


def _save(path: str, data: dict):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"  -> Saved: {path}")


def check_health() -> dict:
    """Check if the engine is running and KB is ready."""
    return _get("health")


def cmd_retrieve(args):
    """Execute retrieval via engine API."""
    payload = {
        "scenario": args.scenario,
        "target_columns": [c.strip() for c in args.target_cols.split(",")],
        "parameter_columns": [c.strip() for c in args.param_cols.split(",")],
        "group_columns": [c.strip() for c in (args.group_cols or "material").split(",")],
        "mode": args.mode,
        "top_k": args.top_k,
    }
    print(f"Retrieving: {payload['scenario']} | mode={payload['mode']} | "
          f"targets={len(payload['target_columns'])} params={len(payload['parameter_columns'])}")
    result = _post("retrieve", payload)
    run_id = result.get("retrieval_run_id")
    total = result.get("total_after_dedup", 0) if "total_after_dedup" in result else result.get("total_chunks_retrieved", 0)
    print(f"  Run ID: {run_id}")
    print(f"  Chunks: {total} (after dedup)")

    if args.output:
        _save(args.output, result)
        # Also save run ID for subsequent steps
        id_path = Path(args.output).parent / ".last_run_id"
        id_path.write_text(run_id)
    return result


def cmd_score(args):
    """Execute scoring via engine API."""
    run_id = args.run_id
    if not run_id and args.run_id_file:
        run_id = Path(args.run_id_file).read_text().strip()

    # Build context from args or file
    payload = {
        "retrieval_run_id": run_id,
        "scenario": args.scenario,
        "parameter_columns": [c.strip() for c in args.param_cols.split(",")],
        "target_columns": [c.strip() for c in args.target_cols.split(",")],
        "pass_threshold": args.pass_threshold,
    }
    print(f"Scoring run {run_id}...")
    result = _post("score", payload)
    print(f"  CRITICAL: {result['critical']} | ACCEPTED: {result['accepted']} | "
          f"CONDITIONAL: {result['conditional']} | REJECTED: {result['rejected']}")
    print(f"  Auto-proceed: {result['auto_proceed']}")

    if args.output:
        _save(args.output, result)


def cmd_inject(args):
    """Execute ontology injection via engine API."""
    run_id = args.run_id
    if not run_id and args.run_id_file:
        run_id = Path(args.run_id_file).read_text().strip()

    manifest = json.loads(Path(args.manifest).read_text())
    payload = {
        "retrieval_run_id": run_id,
        "column_details": manifest.get("column_details", []),
        "mode": args.mode,
    }
    print(f"Injecting from run {run_id}...")
    result = _post("inject", payload)
    meta = result.get("rag_injection_metadata", {})
    print(f"  Columns matched: {meta.get('columns_matched', 0)}/"
          f"{meta.get('total_columns', 0)} ({meta.get('match_rate_pct', 0)}%)")
    print(f"  Chunks injected: {meta.get('total_chunks_injected', 0)}")
    print(f"  Gaps: {meta.get('columns_without_knowledge', [])}")

    if args.output:
        _save(args.output, result)


def cmd_web_search(args):
    """Standalone web search — directly query the internet for knowledge."""
    result = _post("retrieve", {
        "scenario": args.scenario,
        "target_columns": [],
        "parameter_columns": [],
        "group_columns": [],
        "mode": "web_only",
        "top_k": args.max_results,
        "custom_query": args.keywords,
    })
    n = len(result.get("chunks", []))
    print(f"Web search for '{args.keywords}': {n} results")
    if args.output:
        _save(args.output, result)
    return result


def cmd_pipeline(args):
    """Execute full Retrieve-Score-Inject via engine API.

    Output files saved in diagnostic workspace:
      output_dir/00_input/rag_ontology_draft.json     -- consumed by context-builder
      output_dir/00_input/rag_retrieval_result.json   -- audit trail
      output_dir/00_input/rag_scoring_result.json     -- audit trail
    """
    mode = "hybrid" if args.use_web else args.mode
    if args.use_web:
        print("  Web search enabled (hybrid mode)")
    payload = {
        "scenario": args.scenario,
        "target_columns": [c.strip() for c in args.target_cols.split(",")],
        "parameter_columns": [c.strip() for c in args.param_cols.split(",")],
        "group_columns": [c.strip() for c in (args.group_cols or "material").split(",")],
        "mode": mode,
        "top_k": args.top_k,
    }
    print(f"RAG Pipeline: {payload['scenario']} | mode={payload['mode']}")
    print(f"  Targets: {payload['target_columns']}")
    print(f"  Params:  {payload['parameter_columns']}")
    result = _post("pipeline/full", payload)
    ontology = result.get("ontology", {})
    meta = ontology.get("rag_injection_metadata", {})

    print(f"  Run ID:     {result['run_id']}")
    print(f"  Retrieval:  {result['retrieval']['total_chunks']} chunks")
    print(f"  Scoring:    {result['scoring']['critical']}C / "
          f"{result['scoring']['accepted']}A -> "
          f"{result['scoring']['injectable']} injectable")
    print(f"  Ontology:   {len(ontology.get('relationships', []))} relationships, "
          f"{len(ontology.get('signals', {}).get('process_parameters', []))} params")
    print(f"  Match rate: {meta.get('match_rate_pct', 0)}% "
          f"({meta.get('columns_matched', 0)}/{meta.get('total_columns', 0)})")
    print(f"  Gaps:       {meta.get('columns_without_knowledge', [])}")

    if args.output_dir:
        od = Path(args.output_dir)
        # Ensure diagnostic workspace structure
        input_dir = od / "00_input"
        input_dir.mkdir(parents=True, exist_ok=True)

        # Main deliverable: ontology draft consumed by context-builder
        _save(str(input_dir / "rag_ontology_draft.json"), ontology)

        # Audit trail: raw retrieval + scoring results
        _save(str(input_dir / "rag_retrieval_result.json"),
              {"run_id": result["run_id"],
               "total_chunks": result["retrieval"]["total_chunks"]})
        _save(str(input_dir / "rag_scoring_result.json"),
              {"run_id": result["run_id"],
               "critical": result["scoring"]["critical"],
               "accepted": result["scoring"]["accepted"],
               "injectable": result["scoring"]["injectable"]})

        # Persist run_id for subsequent score/inject steps
        (od / ".last_rag_run_id").write_text(result["run_id"])
        print(f"\n  Output saved to: {input_dir}/")
        print(f"  -> rag_ontology_draft.json  (consumed by context-builder Step 2.1)")
        print(f"  -> rag_retrieval_result.json (audit trail)")


def cmd_health(_args):
    """Check engine health."""
    try:
        h = check_health()
        print(f"Engine: {h['status']} | KB ready: {h['kb_ready']} | "
              f"Chunks: {h['total_chunks']} | Uptime: {h['uptime_seconds']}s")
    except RuntimeError as e:
        print(f"Engine UNREACHABLE: {e}")
        sys.exit(1)


def cmd_start(args):
    """Check RAG engine, auto-start if not running."""
    import subprocess, time

    # Detect engine dir: rag_client.py is at .claude/skills/rag-knowledge-builder/scripts/
    script_dir = os.path.dirname(os.path.realpath(__file__))
    # Go up 4 levels: scripts -> rag-knowledge-builder -> skills -> .claude -> project root
    project_root = os.path.realpath(os.path.join(script_dir, "..", "..", "..", ".."))
    ENGINE_DIR = args.engine_dir or os.path.join(project_root, "rag-retrieval-engine")
    ENGINE_DIR = os.path.realpath(ENGINE_DIR)

    # First check if already running
    try:
        h = check_health()
        print(f"Engine already running: {h['total_chunks']} chunks | uptime={h['uptime_seconds']}s")
        return
    except RuntimeError:
        print("Engine not running — auto-starting...")

    if not os.path.exists(os.path.join(ENGINE_DIR, "server.py")):
        print(f"ERROR: server.py not found in {ENGINE_DIR}")
        print(f"Set RAG_ENGINE_DIR env var or pass --engine-dir")
        sys.exit(1)

    # Start engine
    engine = subprocess.Popen(
        ["uv", "run", "python", "server.py"],
        cwd=ENGINE_DIR,
        stdout=open("/tmp/rag_engine.log", "w"),
        stderr=subprocess.STDOUT,
        env={**os.environ, "VIRTUAL_ENV": "", "http_proxy": "", "https_proxy": "",
             "HTTP_PROXY": "", "HTTPS_PROXY": "", "ALL_PROXY": "", "all_proxy": ""},
    )
    print(f"Started RAG engine (PID: {engine.pid})")
    print("Waiting for engine to be ready...", end="", flush=True)

    # Wait for startup (up to 30s)
    for i in range(30):
        time.sleep(1)
        print(".", end="", flush=True)
        try:
            h = check_health()
            print(f"\nReady after {i+1}s: {h['total_chunks']} chunks | KB ready: {h['kb_ready']}")
            return
        except RuntimeError:
            continue

    print("\nERROR: Engine failed to start within 30s. Check /tmp/rag_engine.log")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="RAG Engine HTTP Client")
    sub = parser.add_subparsers(dest="command")

    # retrieve
    p = sub.add_parser("retrieve", help="Retrieve knowledge chunks")
    p.add_argument("--scenario", required=True)
    p.add_argument("--target-cols", required=True)
    p.add_argument("--param-cols", required=True)
    p.add_argument("--group-cols")
    p.add_argument("--mode", default="hybrid",
                   choices=["local_only", "web_only", "hybrid"])
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--output", help="Save results to JSON file")

    # score
    p = sub.add_parser("score", help="Score retrieved chunks")
    p.add_argument("--run-id")
    p.add_argument("--run-id-file", help="Read run ID from file")
    p.add_argument("--scenario", required=True)
    p.add_argument("--param-cols", required=True)
    p.add_argument("--target-cols", required=True)
    p.add_argument("--pass-threshold", type=float, default=6.5)
    p.add_argument("--output")

    # inject
    p = sub.add_parser("inject", help="Inject knowledge into ontology")
    p.add_argument("--run-id")
    p.add_argument("--run-id-file")
    p.add_argument("--manifest", required=True,
                   help="Path to input_manifest.json")
    p.add_argument("--mode", default="auto", choices=["auto", "review"])
    p.add_argument("--output")

    # web-search (standalone web search)
    p = sub.add_parser("web-search", help="Search the web for knowledge and save results")
    p.add_argument("--keywords", required=True, help="Keywords to search for")
    p.add_argument("--scenario", default="generic", help="Scenario tag for the results")
    p.add_argument("--max-results", type=int, default=5)
    p.add_argument("--output", default=None, help="Save results to JSON file")

    # pipeline (full)
    p = sub.add_parser("pipeline", help="Run full Retrieve->Score->Inject")
    p.add_argument("--scenario", required=True)
    p.add_argument("--target-cols", required=True)
    p.add_argument("--param-cols", required=True)
    p.add_argument("--group-cols")
    p.add_argument("--mode", default="hybrid", choices=["local_only", "web_only", "hybrid"])
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--output-dir", help="Directory to save all results")
    p.add_argument("--use-web", action="store_true", help="Enable web search alongside local KB (sets mode=hybrid)")

    # health
    sub.add_parser("health", help="Check engine health")

    # start (auto-start engine if not running)
    p = sub.add_parser("start", help="Check RAG engine, auto-start if not running")
    p.add_argument("--engine-dir", help="Path to rag-retrieval-engine directory (default: auto-detect)")

    args = parser.parse_args()

    commands = {
        "retrieve": cmd_retrieve,
        "score": cmd_score,
        "inject": cmd_inject,
        "pipeline": cmd_pipeline,
        "health": cmd_health,
        "start": cmd_start,
        "web-search": cmd_web_search,
    }

    if args.command not in commands:
        parser.print_help()
        sys.exit(1)

    commands[args.command](args)


if __name__ == "__main__":
    main()
