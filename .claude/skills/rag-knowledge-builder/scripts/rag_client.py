#!/usr/bin/env python3
"""
RAG Engine HTTP Client (v3.1).

Called by the rag-knowledge-builder skill. Uses `uv run` for Python execution.
Phase 0-1 (retrieve + score) runs in the RAG engine (server.py).
Phase 2-4 (ontology + structured data + verification) run in the LLM agent.

Usage:
  uv run python scripts/rag_client.py build-ontology --domain "..." --target-concepts "..." --related-concepts "..." --output-dir <path>

Legacy CLI flags (--scenario, --target-cols, --param-cols, --group-cols) remain as hidden aliases.
"""

import argparse, json, os, sys, time
from pathlib import Path
from typing import Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Default engine endpoint
ENGINE_URL = os.environ.get("RAG_ENGINE_URL", "http://localhost:8765")

# Skill root (rag_client.py is at .claude/skills/rag-knowledge-builder/scripts/)
SKILL_ROOT = str(Path(__file__).resolve().parent.parent)


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


def _resolve_arg(primary, legacy, fallback=None):
    """Resolve CLI arg: prefer primary name, fall back to legacy alias."""
    return primary if primary is not None else (legacy if legacy is not None else fallback)


def _parse_context_dimensions(raw: Optional[str]) -> list:
    """Parse context_dimensions/group_cols, defaulting to empty list."""
    if not raw:
        return []
    return [c.strip() for c in raw.split(",") if c.strip()]


# ═══════════════════════════════════════════════════════════════
# Commands
# ═══════════════════════════════════════════════════════════════

def cmd_build_ontology(args):
    """PRIMARY command (v3.1). Phase 1 retrieve+score, then LLM handoff.

    This command:
    1. Calls the engine's /pipeline/retrieve-score (Retrieve + Score only)
    2. Saves scored chunks with FULL content to rag_scored_chunks.json
    3. Writes LLM handoff instructions for Phase 2-4

    The LLM agent (Claude/GPT) then reads agents/ontology-construction-agent.md
    and processes the chunks to build rag_ontology_draft.json.
    """
    domain = _resolve_arg(getattr(args, 'domain', None), getattr(args, 'scenario', None))
    target_concepts = _resolve_arg(getattr(args, 'target_concepts', None), getattr(args, 'target_cols', None))
    related_concepts = _resolve_arg(getattr(args, 'related_concepts', None), getattr(args, 'param_cols', None))
    context_dimensions_raw = _resolve_arg(getattr(args, 'context_dimensions', None), getattr(args, 'group_cols', None))

    if not domain or not target_concepts or not related_concepts:
        missing = []
        if not domain: missing.append("--domain")
        if not target_concepts: missing.append("--target-concepts")
        if not related_concepts: missing.append("--related-concepts")
        print(f"ERROR: Required parameters missing: {', '.join(missing)}")
        print(f"  Primary: --domain --target-concepts --related-concepts")
        print(f"  Legacy:  --scenario --target-cols --param-cols")
        sys.exit(1)

    mode = "hybrid" if args.use_web else args.mode
    payload = {
        "scenario": domain,
        "target_columns": [c.strip() for c in target_concepts.split(",")],
        "parameter_columns": [c.strip() for c in related_concepts.split(",")],
        "group_columns": _parse_context_dimensions(context_dimensions_raw),
        "mode": mode,
        "top_k": args.top_k,
    }

    print(f"{'=' * 70}")
    print(f"RAG Knowledge Builder v3.1 — build-ontology")
    print(f"{'=' * 70}")
    print(f"  Domain:   {payload['scenario']}")
    print(f"  Mode:     {payload['mode']}")
    print(f"  Targets:  {payload['target_columns']}")
    print(f"  Related:  {payload['parameter_columns']}")
    print(f"  Context:  {payload['group_columns']}")

    # === Phase 1: Retrieve + Score (engine) ===
    print(f"\n[Phase 1/4] Retrieve + Score (engine)...")
    result = _post("pipeline/retrieve-score", payload)

    scoring = result.get('scoring', {})
    print(f"  Run ID:    {result['run_id']}")
    print(f"  Retrieval: {result['retrieval']['total_chunks']} chunks")
    print(f"  Scoring:   {scoring.get('critical', 0)}C / "
          f"{scoring.get('accepted', 0)}A / "
          f"{scoring.get('conditional', 0)}COND / "
          f"{scoring.get('rejected', 0)}R -> "
          f"{scoring.get('injectable', 0)} injectable")

    # Count chunks with content
    chunks_with_content = sum(1 for c in result.get("chunks", []) if c.get("content"))
    print(f"  Content:   {chunks_with_content} chunks have full content (LLM needs this)")

    # === Save outputs ===
    if not args.output_dir:
        print("\n  (No output_dir specified — results not saved)")
        return

    od = Path(args.output_dir)
    input_dir = od / "00_input"
    input_dir.mkdir(parents=True, exist_ok=True)

    # Primary: full scored chunks (with content) — what LLM reads in Phase 2
    _save(str(input_dir / "rag_scored_chunks.json"), result)
    _save(str(input_dir / "rag_retrieval_result.json"), result.get("retrieval", {}))
    _save(str(input_dir / "rag_scoring_result.json"), result.get("scoring", {}))
    (od / ".last_rag_run_id").write_text(result["run_id"])

    # === LLM handoff instructions ===
    handoff = {
        "skill_root": SKILL_ROOT,
        "scenario": result.get("scenario", args.scenario),
        "target_columns": result.get("target_columns", payload["target_columns"]),
        "parameter_columns": result.get("parameter_columns", payload["parameter_columns"]),
        "group_columns": result.get("group_columns", payload["group_columns"]),
        "run_id": result["run_id"],
        "input_files": {
            "scored_chunks": str(input_dir / "rag_scored_chunks.json"),
        },
        "output_files": {
            "ontology_draft": str(input_dir / "rag_ontology_draft.json"),
            "structured_data": str(input_dir / "rag_structured_data.json"),
            "clarification_needed": str(input_dir / "rag_clarification_needed.json"),
            "audit_log": str(input_dir / "rag_audit_log.json"),
        },
        "llm_agents": {
            "phase_2_ontology": {
                "prompt_file": "agents/ontology-construction-agent.md",
                "input": "rag_scored_chunks.json -> chunks[] (each has 'content' field)",
                "output": "rag_ontology_draft.json",
                "key_steps": [
                    "Read scenario description and column lists",
                    "Read every chunk's FULL content (not just metadata/tags)",
                    "Judge applicability: APPLICABLE / PARTIALLY / NOT_APPLICABLE",
                    "Classify signals by physical meaning (NOT keyword matching)",
                    "Extract causal chains with physical mechanisms",
                    "Identify scenario-specific equipment (no hardcoded names)",
                    "Identify confounders with physical reasoning",
                    "Mark UNKNOWN for any uncertain physical meaning",
                ]
            },
            "phase_3_structured_data": {
                "prompt_file": "agents/structured-data-generator.md",
                "input": "rag_ontology_draft.json",
                "output": "rag_structured_data.json",
                "key_steps": [
                    "Generate sample data rows per role",
                    "Generate validation rules (physical plausibility bounds)",
                    "Generate causal query templates",
                    "Generate LLM prompt templates for downstream agents",
                    "Generate defect scenarios (concrete test cases)",
                ]
            },
            "phase_4_verification": {
                "prompt_file": "agents/quality-verification-agent.md",
                "input": "rag_ontology_draft.json + rag_structured_data.json",
                "output": "rag_audit_log.json (with PASS/CONDITIONAL/FAIL verdict)",
                "checks": [
                    "Schema compliance",
                    "Content plausibility",
                    "Logical consistency",
                    "Cross-source consistency",
                    "Downstream consumability",
                ]
            }
        },
        "anti_patterns": [
            "DO NOT keyword-match for signal classification",
            "DO NOT use hardcoded equipment names (spindle, bearing, cutter, etc.)",
            "DO NOT force-fit causal chains from wrong-process chunks",
            "DO NOT skip rejection documentation",
            "DO NOT use process_type='generic'",
        ]
    }
    _save(str(input_dir / ".llm_phase_2_3_instructions.json"), handoff)

    print(f"\n{'=' * 70}")
    print(f"[Phase 1/4] COMPLETE. Engine output saved.")
    print(f"{'=' * 70}")
    print(f"\nNEXT STEPS (LLM agent — the invoking LLM reads these):")
    print(f"  [Phase 2/4] LLM ontology construction")
    print(f"    Read: {handoff['llm_agents']['phase_2_ontology']['prompt_file']}")
    print(f"    Input: rag_scored_chunks.json (chunks[] with content)")
    print(f"    Output: rag_ontology_draft.json")
    print(f"")
    print(f"  [Phase 3/4] LLM structured data generation")
    print(f"    Read: {handoff['llm_agents']['phase_3_structured_data']['prompt_file']}")
    print(f"    Input: rag_ontology_draft.json")
    print(f"    Output: rag_structured_data.json")
    print(f"")
    print(f"  [Phase 4/4] Quality verification gate")
    print(f"    Read: {handoff['llm_agents']['phase_4_verification']['prompt_file']}")
    print(f"    Output: rag_audit_log.json")


def cmd_retrieve_score(args):
    """Phase 1 only: Retrieve + Score. LLM agent handles Phase 2+.

    Use this when you want fine-grained control between engine and LLM phases.
    For the recommended end-to-end flow, use `build-ontology` instead.
    """
    domain = _resolve_arg(args.domain, args.scenario)
    target_concepts = _resolve_arg(args.target_concepts, args.target_cols)
    related_concepts = _resolve_arg(args.related_concepts, args.param_cols)
    context_dimensions_raw = _resolve_arg(args.context_dimensions, args.group_cols)

    mode = "hybrid" if args.use_web else args.mode
    payload = {
        "scenario": domain,
        "target_columns": [c.strip() for c in target_concepts.split(",")],
        "parameter_columns": [c.strip() for c in related_concepts.split(",")],
        "group_columns": _parse_context_dimensions(context_dimensions_raw),
        "mode": mode,
        "top_k": args.top_k,
    }
    print(f"RAG Retrieve+Score: {payload['scenario']} | mode={payload['mode']}")
    print(f"  Targets: {payload['target_columns']}")
    print(f"  Related: {payload['parameter_columns']}")

    result = _post("pipeline/retrieve-score", payload)
    scoring = result.get('scoring', {})
    print(f"  Run ID:    {result['run_id']}")
    print(f"  Retrieval: {result['retrieval']['total_chunks']} chunks")
    print(f"  Scoring:   {scoring.get('critical', 0)}C / "
          f"{scoring.get('accepted', 0)}A / "
          f"{scoring.get('conditional', 0)}COND / "
          f"{scoring.get('rejected', 0)}R -> "
          f"{scoring.get('injectable', 0)} injectable")

    chunks_with_content = sum(1 for c in result.get("chunks", []) if c.get("content"))
    print(f"  Content:   {chunks_with_content} chunks have full content")

    if args.output_dir:
        od = Path(args.output_dir)
        input_dir = od / "00_input"
        input_dir.mkdir(parents=True, exist_ok=True)

        _save(str(input_dir / "rag_scored_chunks.json"), result)
        _save(str(input_dir / "rag_retrieval_result.json"), result.get("retrieval", {}))
        _save(str(input_dir / "rag_scoring_result.json"), result.get("scoring", {}))
        (od / ".last_rag_run_id").write_text(result["run_id"])

        print(f"\n  Phase 1 complete. Output saved to: {input_dir}/")
        print(f"  -> rag_scored_chunks.json (PRIMARY: chunks with full content for LLM)")
        print(f"  NEXT: Read agents/ontology-construction-agent.md and execute Phase 2")


def cmd_retrieve(args):
    """Execute retrieval only (no scoring)."""
    domain = _resolve_arg(args.domain, args.scenario)
    target_concepts = _resolve_arg(args.target_concepts, args.target_cols)
    related_concepts = _resolve_arg(args.related_concepts, args.param_cols)
    context_dimensions_raw = _resolve_arg(args.context_dimensions, args.group_cols)

    payload = {
        "scenario": domain,
        "target_columns": [c.strip() for c in target_concepts.split(",")],
        "parameter_columns": [c.strip() for c in related_concepts.split(",")],
        "group_columns": _parse_context_dimensions(context_dimensions_raw),
        "mode": args.mode,
        "top_k": args.top_k,
    }
    print(f"Retrieving: {payload['scenario']} | mode={payload['mode']} | "
          f"targets={len(payload['target_columns'])} params={len(payload['parameter_columns'])}")
    result = _post("retrieve", payload)
    run_id = result.get("retrieval_run_id")
    total = result.get("total_after_dedup", 0)
    print(f"  Run ID: {run_id}")
    print(f"  Chunks: {total} (after dedup)")

    if args.output:
        _save(args.output, result)
        id_path = Path(args.output).parent / ".last_run_id"
        id_path.write_text(run_id)
    return result


def cmd_score(args):
    """Execute scoring only (requires prior retrieval)."""
    run_id = args.run_id
    if not run_id and args.run_id_file:
        run_id = Path(args.run_id_file).read_text().strip()

    domain = _resolve_arg(args.domain, args.scenario)
    target_concepts = _resolve_arg(args.target_concepts, args.target_cols)
    related_concepts = _resolve_arg(args.related_concepts, args.param_cols)

    payload = {
        "retrieval_run_id": run_id,
        "scenario": domain,
        "parameter_columns": [c.strip() for c in related_concepts.split(",")],
        "target_columns": [c.strip() for c in target_concepts.split(",")],
        "pass_threshold": args.pass_threshold,
    }
    print(f"Scoring run {run_id}...")
    result = _post("score", payload)
    print(f"  CRITICAL: {result['critical']} | ACCEPTED: {result['accepted']} | "
          f"CONDITIONAL: {result['conditional']} | REJECTED: {result['rejected']}")
    print(f"  Auto-proceed: {result['auto_proceed']}")

    if args.output:
        _save(args.output, result)


def cmd_web_search(args):
    """Standalone web search."""
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
    import subprocess

    script_dir = os.path.dirname(os.path.realpath(__file__))
    project_root = os.path.realpath(os.path.join(script_dir, "..", "..", "..", ".."))
    ENGINE_DIR = args.engine_dir or os.path.join(project_root, "rag-retrieval-engine")
    ENGINE_DIR = os.path.realpath(ENGINE_DIR)

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


# ═══════════════════════════════════════════════════════════════
# Deprecated commands
# ═══════════════════════════════════════════════════════════════

def _deprecate_inject(_args):
    print("=" * 70)
    print("DEPRECATED: `inject` command REMOVED in v3.0")
    print("=" * 70)
    print("injector.py contained hardcoded CNC equipment (spindle_assembly)")
    print("and produced WRONG results for non-CNC scenarios.")
    print("")
    print("Use: rag_client.py build-ontology --domain '...' ...")
    sys.exit(2)


def _deprecate_pipeline(_args):
    print("=" * 70)
    print("DEPRECATED: `pipeline` command DEMOTED in v3.0")
    print("=" * 70)
    print("It called injector.py which hardcoded CNC-specific equipment.")
    print("")
    print("Use: rag_client.py build-ontology --domain '...' ...")
    sys.exit(2)


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="RAG Engine HTTP Client (v3.1). "
                    "Phase 1 (retrieve+score) via engine; Phase 2-4 via LLM agent.")
    sub = parser.add_subparsers(dest="command")

    # build-ontology (PRIMARY v3.1)
    p = sub.add_parser("build-ontology",
                       help="[PRIMARY] Phase 1 retrieve+score + LLM handoff for Phase 2-4")
    p.add_argument("--domain", help="Domain description (primary)")
    p.add_argument("--target-concepts", help="Target concept names, comma-separated (primary)")
    p.add_argument("--related-concepts", help="Related concept names, comma-separated (primary)")
    p.add_argument("--context-dimensions", default=None,
                   help="Context/categorical dimensions, comma-separated (primary)")
    # Legacy aliases (hidden from --help)
    p.add_argument("--scenario", dest="scenario", help=argparse.SUPPRESS)
    p.add_argument("--target-cols", dest="target_cols", help=argparse.SUPPRESS)
    p.add_argument("--param-cols", dest="param_cols", help=argparse.SUPPRESS)
    p.add_argument("--group-cols", dest="group_cols", default=None, help=argparse.SUPPRESS)
    p.add_argument("--mode", default="hybrid", choices=["local_only", "web_only", "hybrid"])
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--output-dir", help="Directory to save results for LLM agent")
    p.add_argument("--use-web", action="store_true", help="Enable web search (sets mode=hybrid)")

    # retrieve-score (Phase 1 only)
    p = sub.add_parser("retrieve-score",
                       help="Phase 1 only: Retrieve + Score (LLM handles Phase 2+)")
    p.add_argument("--domain", help="Domain description (primary)")
    p.add_argument("--target-concepts", help="Target concept names, comma-separated (primary)")
    p.add_argument("--related-concepts", help="Related concept names, comma-separated (primary)")
    p.add_argument("--context-dimensions", default=None,
                   help="Context/categorical dimensions, comma-separated (primary)")
    p.add_argument("--scenario", dest="scenario", help=argparse.SUPPRESS)
    p.add_argument("--target-cols", dest="target_cols", help=argparse.SUPPRESS)
    p.add_argument("--param-cols", dest="param_cols", help=argparse.SUPPRESS)
    p.add_argument("--group-cols", dest="group_cols", default=None, help=argparse.SUPPRESS)
    p.add_argument("--mode", default="hybrid", choices=["local_only", "web_only", "hybrid"])
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--output-dir", help="Directory to save results")
    p.add_argument("--use-web", action="store_true")

    # retrieve (raw retrieval only)
    p = sub.add_parser("retrieve", help="Retrieve knowledge chunks (no scoring)")
    p.add_argument("--domain", help="Domain description (primary)")
    p.add_argument("--target-concepts", help="Target concept names, comma-separated (primary)")
    p.add_argument("--related-concepts", help="Related concept names, comma-separated (primary)")
    p.add_argument("--context-dimensions", default=None,
                   help="Context/categorical dimensions, comma-separated (primary)")
    p.add_argument("--scenario", dest="scenario", help=argparse.SUPPRESS)
    p.add_argument("--target-cols", dest="target_cols", help=argparse.SUPPRESS)
    p.add_argument("--param-cols", dest="param_cols", help=argparse.SUPPRESS)
    p.add_argument("--group-cols", dest="group_cols", default=None, help=argparse.SUPPRESS)
    p.add_argument("--mode", default="hybrid", choices=["local_only", "web_only", "hybrid"])
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--output", help="Save results to JSON file")

    # score (scoring only)
    p = sub.add_parser("score", help="Score previously retrieved chunks")
    p.add_argument("--run-id")
    p.add_argument("--run-id-file", help="Read run ID from file")
    p.add_argument("--domain", help="Domain description (primary)")
    p.add_argument("--target-concepts", help="Target concept names, comma-separated (primary)")
    p.add_argument("--related-concepts", help="Related concept names, comma-separated (primary)")
    p.add_argument("--scenario", dest="scenario", help=argparse.SUPPRESS)
    p.add_argument("--param-cols", dest="param_cols", help=argparse.SUPPRESS)
    p.add_argument("--target-cols", dest="target_cols", help=argparse.SUPPRESS)
    p.add_argument("--pass-threshold", type=float, default=6.5)
    p.add_argument("--output")

    # web-search
    p = sub.add_parser("web-search", help="Standalone web search")
    p.add_argument("--keywords", required=True)
    p.add_argument("--scenario", default="generic")
    p.add_argument("--max-results", type=int, default=5)
    p.add_argument("--output", default=None)

    # health
    sub.add_parser("health", help="Check engine health")

    # start
    p = sub.add_parser("start", help="Auto-start RAG engine if not running")
    p.add_argument("--engine-dir", help="Path to rag-retrieval-engine (default: auto-detect)")

    # DEPRECATED commands
    p = sub.add_parser("inject",
                       help="[DEPRECATED] Use build-ontology instead")
    p = sub.add_parser("pipeline",
                       help="[DEPRECATED] Use build-ontology instead")

    args = parser.parse_args()

    commands = {
        "build-ontology": cmd_build_ontology,
        "retrieve-score": cmd_retrieve_score,
        "retrieve": cmd_retrieve,
        "score": cmd_score,
        "web-search": cmd_web_search,
        "health": cmd_health,
        "start": cmd_start,
        "inject": _deprecate_inject,
        "pipeline": _deprecate_pipeline,
    }

    if args.command not in commands:
        parser.print_help()
        sys.exit(1)

    commands[args.command](args)


if __name__ == "__main__":
    main()
