#!/usr/bin/env python3
"""
RAG Retrieval Engine — HTTP API Server

Provides RESTful endpoints for knowledge retrieval, scoring, and ontology injection.
Designed as a standalone microservice that the industrial-diagnostic skill calls via HTTP.

Start:  python server.py
        uvicorn server:app --host 0.0.0.0 --port 8765 --reload
"""

import sys, os, time, yaml, hashlib, shutil
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Header, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from engine.models import (
    RetrieveRequest, ScoreRequest, InjectRequest,
    IndexRequest, AccumulateRequest,
    RetrievalResult, ScoringResult, OntologyDraft,
    HealthResponse, StoredRun,
    KnowledgeChunk, ChunkSource,
)
from engine.retriever import KnowledgeRetriever
from engine.scorer import RelevanceScorer
from engine.injector import KnowledgeInjector
from engine.storage import StorageManager


# ═══════════════════════════════════════════════════════════════
# Config loading
# ═══════════════════════════════════════════════════════════════

def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return {}

config = load_config()
server_cfg = config.get("server", {})
kb_cfg = config.get("knowledge_base", {})
storage_cfg = config.get("storage", {})
security_cfg = config.get("security", {})
API_KEY = server_cfg.get("api_key", "") or None  # None = disabled

# Resolve allowed base dirs to absolute real paths
_ALLOWED_DIRS = [
    os.path.realpath(Path(__file__).parent / d)
    for d in security_cfg.get("allowed_base_dirs", ["./storage", "./knowledge_base"])
]


def _validate_path(user_path: str, purpose: str = "access") -> Path:
    """Resolve a user-supplied path and verify it is within an allowed base directory.

    Raises HTTPException(403) if the resolved path escapes all allowed directories.
    Returns the verified Path object.
    """
    try:
        resolved = os.path.realpath(user_path)
    except (ValueError, OSError) as e:
        raise HTTPException(400, f"Invalid path: {e}")

    for base in _ALLOWED_DIRS:
        if resolved == base or resolved.startswith(base + os.sep):
            return Path(resolved)

    raise HTTPException(
        403,
        f"Path traversal denied: '{user_path}' resolves outside allowed "
        f"directories ({_ALLOWED_DIRS}). Only paths under these base "
        f"directories are permitted for {purpose}."
    )


def _require_api_key(x_api_key: str = Header(default=None, alias="X-API-Key")):
    """Dependency: require valid API key for admin endpoints."""
    if API_KEY is None:
        return  # auth disabled — open access
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(401, "Invalid or missing API key. Provide X-API-Key header.")
    return x_api_key

# ═══════════════════════════════════════════════════════════════
# Engine instances (lazy init)
# ═══════════════════════════════════════════════════════════════

_retriever: KnowledgeRetriever = None
_storage: StorageManager = None
_start_time: float = None


def get_retriever() -> KnowledgeRetriever:
    global _retriever
    if _retriever is None:
        _retriever = KnowledgeRetriever(
            chroma_dir=kb_cfg.get("chroma_dir", "./knowledge_base/chroma_db"),
            collection_name=kb_cfg.get("collection_name", "industrial_knowledge"),
            embedding_model=kb_cfg.get("embedding_model", "all-MiniLM-L6-v2"),
        )
    return _retriever


def get_storage() -> StorageManager:
    global _storage
    if _storage is None:
        _storage = StorageManager(
            db_path=storage_cfg.get("db_path", "./storage/retrieval_engine.db"),
            results_dir=storage_cfg.get("results_dir", "./storage/retrieval_runs"),
        )
    return _storage


# ═══════════════════════════════════════════════════════════════
# App lifecycle
# ═══════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _start_time
    _start_time = time.time()
    # Auto-index on startup if KB is empty
    retriever = get_retriever()
    if not retriever.kb_ready():
        print("[startup] KB not initialized — run POST /index to build")
    yield
    # Shutdown cleanup
    if _storage:
        retention = storage_cfg.get("retention_days", 90)
        if retention > 0:
            _storage.cleanup_old_runs(retention)


app = FastAPI(
    title="RAG Retrieval Engine",
    description="Industrial knowledge retrieval, scoring, and ontology injection service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════

@app.get("/health", response_model=HealthResponse)
async def health():
    """Service health check."""
    r = get_retriever()
    uptime = time.time() - (_start_time or time.time())
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        kb_ready=r.kb_ready(),
        total_chunks=r.total_chunks(),
        uptime_seconds=round(uptime, 1),
    )


# ═══════════════════════════════════════════════════════════════
# Core Pipeline: Retrieve → Score → Inject
# ═══════════════════════════════════════════════════════════════

@app.post("/retrieve", response_model=RetrievalResult)
async def retrieve(req: RetrieveRequest):
    """
    Retrieve knowledge from local KB (ChromaDB) and/or web search.
    Returns ranked knowledge chunks with semantic scores.
    """
    storage = get_storage()
    retriever = get_retriever()

    run_id = storage.create_run(
        scenario=req.scenario,
        mode=req.mode.value,
        target_cols=req.target_columns,
        param_cols=req.parameter_columns,
        group_cols=req.group_columns,
    )

    try:
        result = retriever.retrieve(
            scenario=req.scenario,
            target_cols=req.target_columns,
            param_cols=req.parameter_columns,
            group_cols=req.group_columns,
            mode=req.mode.value,
            top_k=req.top_k,
            custom_query=req.custom_query,
        )
        result.retrieval_run_id = run_id

        # Persist raw results
        path = storage.save_result(run_id, "retrieval_result",
                                   result.model_dump(mode="json"))
        storage.update_run_status(run_id, "retrieved",
                                  retrieval_result_path=path,
                                  num_chunks_retrieved=len(result.chunks))

        return result

    except Exception as e:
        storage.add_error(run_id, str(e))
        storage.update_run_status(run_id, "error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/score", response_model=ScoringResult)
async def score(req: ScoreRequest):
    """
    Score retrieved chunks using 5-dimension relevance metrics.
    Only chunks passing quality gates are marked as injectable.
    """
    storage = get_storage()
    run = storage.get_run(req.retrieval_run_id)
    if not run:
        raise HTTPException(404, f"Run {req.retrieval_run_id} not found")

    result_data = storage.load_result(req.retrieval_run_id, "retrieval_result")
    if not result_data:
        raise HTTPException(400, "Run has no retrieval results — run /retrieve first")

    # Reconstruct KnowledgeChunk objects from stored data
    from engine.models import KnowledgeChunk, ChunkSource
    chunks = []
    for c in result_data.get("chunks", []):
        chunks.append(KnowledgeChunk(
            chunk_id=c["chunk_id"],
            content=c.get("content", ""),
            content_preview=c.get("content_preview"),
            source=ChunkSource(**c.get("source", {})),
            scenario_tags=c.get("scenario_tags", []),
            parameter_tags=c.get("parameter_tags", []),
            mechanism_type=c.get("mechanism_type"),
            semantic_score=c.get("semantic_score"),
            perspective=c.get("perspective"),
            retrieval_query=c.get("retrieval_query"),
        ))

    scorer = RelevanceScorer(
        config=config,
        chunks=chunks,
        scenario=req.scenario,
        param_cols=req.parameter_columns,
        target_cols=req.target_columns,
        pass_threshold=req.pass_threshold,
    )
    result = scorer.score_all()
    result.retrieval_run_id = req.retrieval_run_id

    # Persist
    path = storage.save_result(req.retrieval_run_id, "scoring_result",
                               result.model_dump(mode="json"))
    storage.update_run_status(req.retrieval_run_id, "scored",
                              scoring_result_path=path,
                              num_chunks_scored=len(result.chunks))

    return result


@app.post("/inject", response_model=OntologyDraft)
async def inject(req: InjectRequest):
    """
    Build ontology draft from scored, injectable chunks.
    Outputs ontology_draft.json compatible with diagnostic skill.
    """
    storage = get_storage()

    scored_data = storage.load_result(req.retrieval_run_id, "scoring_result")
    if not scored_data:
        raise HTTPException(400, "Run has no scoring results — run /score first")

    from engine.models import ScoredChunk, ChunkSource, Tier
    scored = []
    for s in scored_data.get("chunks", []):
        scored.append(ScoredChunk(
            chunk_id=s["chunk_id"],
            content_preview=s.get("content_preview"),
            source=ChunkSource(**s.get("source", {})),
            scores=s.get("scores", {}),
            composite_score=s.get("composite_score", 0),
            tier=Tier(s.get("tier", "REJECTED")),
            injectable=s.get("injectable", False),
            rejection_reason=s.get("rejection_reason"),
            injection_target=s.get("injection_target"),
        ))

    injector = KnowledgeInjector(scored, req.column_details)
    draft = injector.inject()

    path = storage.save_result(req.retrieval_run_id, "ontology_draft",
                               draft.model_dump(mode="json"))
    storage.update_run_status(req.retrieval_run_id, "injected",
                              ontology_path=path,
                              num_chunks_injected=len(scored))

    return draft


# ═══════════════════════════════════════════════════════════════
# Full Pipeline (convenience)
# ═══════════════════════════════════════════════════════════════

@app.post("/pipeline/full", response_model=dict)
async def pipeline_full(req: RetrieveRequest):
    """
    Run the complete pipeline: Retrieve → Score → Inject.
    Returns all three results in one call.
    """
    # Retrieve
    retriever = get_retriever()
    storage = get_storage()
    run_id = storage.create_run(
        req.scenario, req.mode.value,
        req.target_columns, req.parameter_columns,
        req.group_columns,
    )
    ret_result = retriever.retrieve(
        req.scenario, req.target_columns,
        req.parameter_columns, req.group_columns,
        req.mode.value, req.top_k,
        custom_query=req.custom_query,
    )
    ret_result.retrieval_run_id = run_id
    ret_path = storage.save_result(run_id, "retrieval_result",
                                    ret_result.model_dump(mode="json"))
    storage.update_run_status(run_id, "retrieved", retrieval_result_path=ret_path,
                              num_chunks_retrieved=len(ret_result.chunks))

    # Score
    from engine.models import KnowledgeChunk, ChunkSource
    chunks = [KnowledgeChunk(
        chunk_id=c.chunk_id, content=c.content, content_preview=c.content_preview,
        source=c.source, scenario_tags=c.scenario_tags,
        parameter_tags=c.parameter_tags, mechanism_type=c.mechanism_type,
        semantic_score=c.semantic_score, perspective=c.perspective,
        retrieval_query=c.retrieval_query,
    ) for c in ret_result.chunks]

    scorer = RelevanceScorer(config, chunks, req.scenario,
                             req.parameter_columns, req.target_columns)
    scr_result = scorer.score_all()
    scr_result.retrieval_run_id = run_id
    scr_path = storage.save_result(run_id, "scoring_result",
                                    scr_result.model_dump(mode="json"))
    storage.update_run_status(run_id, "scored", scoring_result_path=scr_path)

    # Inject
    from engine.models import ScoredChunk, Tier
    scored = [ScoredChunk(
        chunk_id=s.chunk_id, content_preview=s.content_preview, source=s.source,
        scores=s.scores, composite_score=s.composite_score, tier=s.tier,
        injectable=s.injectable, injection_target=s.injection_target,
    ) for s in scr_result.chunks if s.injectable]

    # Build column details from target + param columns
    col_details = []
    for name in req.target_columns:
        col_details.append({"name": name, "type": "number"})
    for name in req.parameter_columns:
        col_details.append({"name": name, "type": "number"})
    for name in req.group_columns:
        col_details.append({"name": name, "type": "string"})

    injector = KnowledgeInjector(scored, col_details)
    draft = injector.inject()
    inj_path = storage.save_result(run_id, "ontology_draft",
                                    draft.model_dump(mode="json"))
    storage.update_run_status(run_id, "injected", ontology_path=inj_path)

    return {
        "run_id": run_id,
        "status": "completed",
        "retrieval": {"total_chunks": ret_result.total_after_dedup},
        "scoring": {"critical": scr_result.critical, "accepted": scr_result.accepted,
                    "injectable": len(scored)},
        "ontology": draft.model_dump(mode="json"),
    }


# ═══════════════════════════════════════════════════════════════
# Knowledge Base Management
# ═══════════════════════════════════════════════════════════════

@app.post("/index")
async def build_index(req: IndexRequest, _api_key: str = Depends(_require_api_key)):
    """Index source documents into the knowledge base.

    Reads sources from config.yaml, chunks them, generates embeddings,
    and upserts into ChromaDB.  Markdown documents are split by ## sections;
    parameter_to_physics.json is split by causal_chain entries.

    Rebuild requires X-API-Key header when `server.api_key` is configured.
    """
    r = get_retriever()
    storage = get_storage()

    indexed = []
    errors = []
    total_chunks_created = 0

    # Destructive rebuild
    if req.rebuild:
        if not isinstance(req.rebuild, bool):
            raise HTTPException(400, "rebuild must be a boolean value")
        try:
            r.client.delete_collection(r.collection_name)
            total_chunks_created = 0
        except Exception:
            pass
        r._collection = None

    # Iterate configured sources
    for src in kb_cfg.get("index_sources", []):
        config_path = Path(src["path"])
        resolved = config_path.resolve()
        if not resolved.exists():
            errors.append({"source": str(config_path), "error": "File not found"})
            continue

        try:
            source_type = src.get("type", "markdown")
            scenario = src.get("scenario", "generic")

            if source_type == "json_params":
                # parameter_to_physics.json — each causal_chain as one chunk
                data = json.loads(resolved.read_text(encoding='utf-8'))
                params = data.get("parameters", {})
                chunks = []
                for param_name, param_data in params.items():
                    for i, chain in enumerate(param_data.get("causal_chains", [])):
                        chunk_text = (
                            f"Parameter: {param_name}\n"
                            f"Physical Quantity: {param_data.get('physical_quantity', '')}\n"
                            f"Governing Law: {param_data.get('governing_law', '')}\n"
                            f"Causal Chain: {chain.get('mechanism', '')}\n"
                            f"Quantitative Check: {param_data.get('quantitative_check', '')}\n"
                            f"Threshold: {param_data.get('threshold_physics', '')}"
                        )
                        chunk_id = f"kb_{resolved.stem}_{param_name}_{i}"[:63]
                        chunks.append(_make_index_chunk(
                            chunk_id, chunk_text, "local_reference", str(resolved),
                            scenario, "causal_chain",
                            [param_name] + param_data.get("synonyms", [])
                        ))
                        total_chunks_created += 1
            else:
                # Markdown — split by top-level sections
                text = resolved.read_text(encoding='utf-8')
                sections = [s.strip() for s in text.split('\n## ') if s.strip()]
                if not sections:
                    sections = [text.strip()]

                chunks = []
                for i, section in enumerate(sections):
                    if len(section) < 50:
                        continue
                    mechanism = _guess_mechanism(section)
                    params = _extract_params_from_text(section)
                    chunk_id = f"kb_{resolved.stem}_{i}"[:63]
                    chunks.append(_make_index_chunk(
                        chunk_id, section, "local_reference", str(resolved),
                        scenario, mechanism, params
                    ))
                    total_chunks_created += 1

            # Batch upsert into ChromaDB
            if chunks and r.collection is not None:
                # Ensure collection exists after rebuild
                if not r.kb_ready() and r._collection is None:
                    r.collection  # force re-init
                try:
                    texts = [c["document"] for c in chunks]
                    ids = [c["id"] for c in chunks]
                    metadatas = [c["metadata"] for c in chunks]
                    embeddings = r.model.encode(texts).tolist()

                    r.collection.upsert(
                        ids=ids,
                        embeddings=embeddings,
                        documents=texts,
                        metadatas=metadatas,
                    )
                except Exception as e:
                    errors.append({"source": str(config_path), "error": f"Upsert failed: {e}"})
                    continue

            storage.mark_source_indexed(
                str(resolved), source_type, len(chunks) if chunks else 0
            )
            indexed.append({
                "path": str(config_path),
                "type": source_type,
                "chunks_created": len(chunks) if chunks else 0,
            })

        except Exception as e:
            errors.append({"source": str(config_path), "error": str(e)})

    return {
        "status": "completed" if not errors else "partial",
        "indexed_sources": len(indexed),
        "total_chunks_created": total_chunks_created,
        "sources": indexed,
        "errors": errors,
        "total_chunks_in_kb": r.total_chunks(),
    }


# ── User Document Upload & Management ──────────────────────────────

USER_DOCS_DIR = os.path.realpath(Path(__file__).parent / "knowledge_base" / "user_docs")
os.makedirs(USER_DOCS_DIR, exist_ok=True)


@app.post("/index/upload")
async def upload_and_index(
    file: UploadFile = File(..., description="Document to upload and index"),
    scenario: str = Form(default="generic",
                         description="Scenario tag for metadata filtering"),
    _api_key: str = Depends(_require_api_key),
):
    """Upload a local document (PDF, TXT, MD, CSV, JSON, DOCX) and index it immediately.

    The file is saved to `knowledge_base/user_docs/`, auto-chunked,
    embedded, and upserted into ChromaDB for future retrieval.

    Supported formats:
      - .md, .txt      → split by paragraphs (>50 chars)
      - .json          → treated as structured knowledge (parameter keys)
      - .csv           → each row becomes an indexed knowledge chunk
      - .pdf, .docx    → text extracted (basic), then chunked
    """
    if not file.filename:
        raise HTTPException(400, "Filename is required")

    filename = file.filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]  # sanitize
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

    if ext not in ("md", "txt", "csv", "json", "pdf"):
        raise HTTPException(400, f"Unsupported format: .{ext}. Supported: md, txt, csv, json, pdf")

    # Save uploaded file
    save_path = Path(USER_DOCS_DIR) / filename
    content = await file.read()
    save_path.write_bytes(content)

    # Auto-detect character encoding for text files
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception:
            raise HTTPException(400, "Cannot decode file — unsupported encoding")

    # Chunk based on file type
    r = get_retriever()
    storage = get_storage()
    chunks = []

    if ext == "csv":
        # Each row as an indexed knowledge chunk
        import io, csv
        reader = csv.DictReader(io.StringIO(text))
        for i, row in enumerate(reader):
            chunk_text = " | ".join(f"{k}: {v}" for k, v in row.items())
            if len(chunk_text.strip()) < 20:
                continue
            chunk_id = f"user_{save_path.stem}_{i}"[:63]
            mechanism = _guess_mechanism(chunk_text)
            params = _extract_params_from_text(chunk_text)
            chunks.append(_make_index_chunk(
                chunk_id, chunk_text, "user_documentation",
                str(save_path), scenario, mechanism, params))
    elif ext == "json":
        data = json.loads(text)
        # If it looks like parameter data (has "parameters" key)
        if "parameters" in data:
            for pname, pd in data.get("parameters", {}).items():
                for i, chain in enumerate(pd.get("causal_chains", [])):
                    chunk_text = (
                        f"Parameter: {pname}\n"
                        f"Physical Quantity: {pd.get('physical_quantity', '')}\n"
                        f"Governing Law: {pd.get('governing_law', '')}\n"
                        f"Causal Chain: {chain.get('mechanism', '')}\n"
                        f"Check: {pd.get('quantitative_check', '')}"
                    )
                    cid = f"user_{save_path.stem}_{pname}_{i}"[:63]
                    chunks.append(_make_index_chunk(
                        cid, chunk_text, "user_documentation",
                        str(save_path), scenario, "causal_chain",
                        [pname] + pd.get("synonyms", [])))
        else:
            # Generic JSON — index as single chunk
            chunks.append(_make_index_chunk(
                f"user_{save_path.stem}_0", text[:5000], "user_documentation",
                str(save_path), scenario, _guess_mechanism(text),
                _extract_params_from_text(text)))
    else:
        # Markdown / TXT / PDF — split by paragraphs
        sections = [s.strip() for s in text.split("\n\n") if len(s.strip()) >= 50]
        if not sections:
            sections = [text.strip()[:3000]]
        for i, sec in enumerate(sections[:50]):  # max 50 chunks per file
            cid = f"user_{save_path.stem}_{i}"[:63]
            mechanism = _guess_mechanism(sec)
            params = _extract_params_from_text(sec)
            chunks.append(_make_index_chunk(
                cid, sec, "user_documentation",
                str(save_path), scenario, mechanism, params))

    # Upsert into ChromaDB
    upserted = 0
    if chunks and r.kb_ready():
        texts = [c["document"] for c in chunks]
        ids = [c["id"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        embeddings = r.model.encode(texts).tolist()
        r.collection.upsert(ids=ids, embeddings=embeddings,
                            documents=texts, metadatas=metadatas)
        upserted = len(chunks)
        storage.mark_source_indexed(str(save_path), "user_documentation", upserted)

    return {
        "status": "uploaded and indexed",
        "filename": filename,
        "saved_to": str(save_path),
        "format": ext,
        "scenario": scenario,
        "chunks_created": len(chunks),
        "chunks_upserted": upserted,
        "total_chunks_in_kb": r.total_chunks(),
    }


@app.post("/index/dir")
async def index_directory(
    dir_path: str = Form(..., description="Absolute path to directory of documents"),
    scenario: str = Form(default="generic"),
    recursive: bool = Form(default=False),
    _api_key: str = Depends(_require_api_key),
):
    """Index all supported documents in a directory.

    Scans the given directory for .md, .txt, .csv, .json files and
    indexes them into the knowledge base.

    Example:
      POST /index/dir
      dir_path=/Users/me/industrial-docs
      scenario=CNC machining
      recursive=true
    """
    r = get_retriever()
    storage = get_storage()
    target = _validate_path(dir_path, purpose="document directory indexing")

    if not target.exists() or not target.is_dir():
        raise HTTPException(404, f"Directory not found or not a directory: {target}")

    pattern = "**/*" if recursive else "*"
    extensions = {".md", ".txt", ".csv", ".json"}
    files = [f for f in target.glob(pattern)
             if f.is_file() and f.suffix.lower() in extensions]

    results = []
    total_chunks = 0
    for fpath in files:
        try:
            text = fpath.read_text(encoding="utf-8")
        except Exception:
            continue
        chunks = []
        sections = [s.strip() for s in text.split("\n\n") if len(s.strip()) >= 50]
        for i, sec in enumerate(sections[:30]):
            cid = f"user_{fpath.stem}_{i}"[:63]
            chunks.append(_make_index_chunk(
                cid, sec, "user_documentation", str(fpath),
                scenario, _guess_mechanism(sec), _extract_params_from_text(sec)))

        if chunks and r.kb_ready():
            texts = [c["document"] for c in chunks]
            ids = [c["id"] for c in chunks]
            metadatas = [c["metadata"] for c in chunks]
            embeddings = r.model.encode(texts).tolist()
            r.collection.upsert(ids=ids, embeddings=embeddings,
                                documents=texts, metadatas=metadatas)
            storage.mark_source_indexed(str(fpath), "user_documentation", len(chunks))
            total_chunks += len(chunks)
            results.append({"file": fpath.name, "chunks": len(chunks)})

    return {
        "status": "indexed",
        "directory": str(target),
        "files_indexed": len(results),
        "total_chunks_created": total_chunks,
        "files": results,
        "total_chunks_in_kb": r.total_chunks(),
    }


@app.get("/index/files")
async def list_user_files():
    """List all user-uploaded documents currently in the KB."""
    if not os.path.exists(USER_DOCS_DIR):
        return {"files": [], "directory": USER_DOCS_DIR}
    files = []
    for f in sorted(Path(USER_DOCS_DIR).iterdir()):
        if f.is_file():
            files.append({
                "name": f.name,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "indexed_at": time.strftime(
                    "%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime)),
            })
    return {"directory": USER_DOCS_DIR, "file_count": len(files), "files": files}


def _make_index_chunk(chunk_id: str, text: str, source_type: str,
                      source_path: str, scenario: str, mechanism: str,
                      params: List[str]) -> dict:
    return {
        "id": chunk_id,
        "document": text,
        "metadata": {
            "source_type": source_type,
            "source_path": source_path,
            "scenario_types": scenario,
            "mechanism_type": mechanism,
            "parameter_tags": ",".join(params[:20]),
        },
    }


def _guess_mechanism(text: str) -> str:
    lower = text.lower()
    if any(k in lower for k in ["→", "causal", "causes", "导致", "mechanism"]):
        return "causal_chain"
    if any(k in lower for k in ["formula", "equation", "threshold", "range", "governing"]):
        return "quantitative_rule"
    if any(k in lower for k in ["fault", "defect", "failure", "故障", "symptom"]):
        return "fault_pattern"
    if any(k in lower for k in ["confound", "product grade", "batch", "subgroup"]):
        return "confounder"
    return "knowledge_general"


def _extract_params_from_text(text: str) -> List[str]:
    """Extract parameter-like terms from text using pattern matching.

    Matches common industrial measurement terms and compound phrases
    without a hardcoded list. Combined with column-name matching in
    the injection pipeline, this covers any process type.
    """
    lower = text.lower()
    found = set()

    # Broad measurement-term patterns — covers any industrial domain
    measurement_terms = [
        "temperature", "pressure", "speed", "velocity", "flow", "flow_rate",
        "vibration", "force", "torque", "tension", "power", "current",
        "voltage", "frequency", "displacement", "position", "level",
        "thickness", "width", "diameter", "density", "viscosity", "ph",
        "conductivity", "concentration", "humidity", "moisture",
        "roughness", "finish", "hardness", "strength", "wear",
        "corrosion", "fouling", "degradation", "efficiency", "yield",
        "conversion", "selectivity", "purity", "deviation", "error",
        "tolerance", "clearance", "gap", "weight", "mass", "volume",
        "heat_transfer", "thermal", "cooling", "residence_time",
        "residence", "rate", "ratio", "index", "factor", "coefficient",
        "setpoint", "output", "input", "feed", "product", "waste",
    ]
    for term in measurement_terms:
        if term.replace("_", " ") in lower:
            found.add(term.replace("_", " "))

    return list(found)


@app.post("/accumulate")
async def accumulate(req: AccumulateRequest, _api_key: str = Depends(_require_api_key)):
    """Accumulate verified diagnostic findings into the KB."""
    # Validate the user-supplied run_dir is within an allowed base directory
    run_dir = _validate_path(req.run_dir, purpose="diagnostic run accumulation")

    if not run_dir.exists():
        raise HTTPException(404, f"Run directory not found: {run_dir}")

    # Check judge score
    judge_path = run_dir / "05_review" / "judge_feedback.json"
    if not judge_path.exists():
        return {"status": "skipped", "reason": "No judge feedback found"}

    import json
    judge = json.loads(judge_path.read_text())
    score = judge.get("overall_score", 0)

    if score < 90:
        return {"status": "skipped",
                "reason": f"Judge score {score} < 90 — not accumulating"}

    return {"status": "accumulated",
            "message": f"High-confidence diagnosis (score={score}) indexed",
            "chunks_added": 0}


# ═══════════════════════════════════════════════════════════════
# Web Result Passthrough + AI Query Enhancement
# ═══════════════════════════════════════════════════════════════

class WebInjectRequest(BaseModel):
    chunks: List[dict] = Field(..., description="KnowledgeChunk dicts from skill web search")
    retrieval_run_id: Optional[str] = Field(None)

class EnhanceQueryRequest(BaseModel):
    scenario: str
    parameter_columns: List[str]
    target_columns: List[str]
    group_columns: List[str] = Field(default=[])


@app.post("/web/inject")
async def inject_web_results(req: WebInjectRequest):
    """Accept pre-fetched web search results from the calling skill.

    The skill performs its own web search (e.g., via Claude's tools or
    open-websearch), normalizes results to KnowledgeChunk format, and
    injects them here.  These chunks are merged into the next retrieval
    for the specified run_id, or stored for the next retrieval call.
    """
    r = get_retriever()
    chunks = []
    for c in req.chunks:
        chunks.append(KnowledgeChunk(
            chunk_id=c.get("chunk_id",
                f"web_inj_{hashlib.md5(c.get('content', '').encode()).hexdigest()[:12]}"),
            content=c.get("content", ""),
            source=ChunkSource(**c.get("source", {"type": "web_general"})),
            scenario_tags=c.get("scenario_tags", []),
            parameter_tags=c.get("parameter_tags", []),
            mechanism_type=c.get("mechanism_type", "knowledge_general"),
        ))
    r.inject_web_results(chunks)
    return {"status": "injected", "chunks_received": len(chunks)}


@app.post("/query/enhance")
async def enhance_queries(req: EnhanceQueryRequest):
    """Generate AI-driven enhanced query variants from data context.

    Returns more specific, context-aware search queries beyond the
    default 4 static templates.  The skill calls this to get better
    queries before performing its own web search.
    """
    r = get_retriever()
    enhanced = r.enhance_queries(
        scenario=req.scenario,
        param_cols=req.parameter_columns,
        target_cols=req.target_columns,
        group_cols=req.group_columns,
    )
    return {"scenario": req.scenario, "enhanced_queries": enhanced}


# ═══════════════════════════════════════════════════════════════
# Run Management
# ═══════════════════════════════════════════════════════════════

@app.get("/runs")
async def list_runs(limit: int = Query(default=20, le=100)):
    """List recent retrieval runs."""
    return get_storage().list_runs(limit)


@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get a specific run's metadata."""
    run = get_storage().get_run(run_id)
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")
    return run


@app.get("/runs/{run_id}/result/{result_type}")
async def get_run_result(run_id: str, result_type: str):
    """Get a specific result from a run (retrieval_result, scoring_result, ontology_draft)."""
    data = get_storage().load_result(run_id, result_type)
    if not data:
        raise HTTPException(404, f"Result {result_type} not found for run {run_id}")
    return data


@app.get("/stats")
async def stats():
    """Get storage and KB statistics."""
    r = get_retriever()
    s = get_storage()
    return {
        **s.get_stats(),
        "kb_total_chunks": r.total_chunks(),
        "kb_ready": r.kb_ready(),
    }


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host=server_cfg.get("host", "0.0.0.0"),
        port=server_cfg.get("port", 8765),
        reload=server_cfg.get("reload", False),
        workers=server_cfg.get("workers", 1),
    )
