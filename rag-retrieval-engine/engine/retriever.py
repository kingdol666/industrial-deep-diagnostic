"""
Knowledge Retriever — Local (ChromaDB) + Web (WebSearchEngine) retrieval with 4-perspective multi-query.
"""

import json, time, re, hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from .models import KnowledgeChunk, ChunkSource, RetrievalResult
from .web_search import WebSearchEngine

# Lazy imports
_chromadb = None
_ST = None

def _get_chromadb():
    global _chromadb
    if _chromadb is None:
        import chromadb
        from chromadb.config import Settings
        _chromadb = chromadb
    return _chromadb

def _get_embedder():
    global _ST
    if _ST is None:
        from sentence_transformers import SentenceTransformer
        _ST = SentenceTransformer
    return _ST


class KnowledgeRetriever:
    """Multi-perspective retriever for the industrial knowledge base."""

    # 4 query templates
    QUERY_TEMPLATES = {
        "parameter_physics": {
            "template": "{params} physical meaning equipment specification {scenario}",
            "mechanism_filter": ["equipment_spec", "quantitative_rule", "causal_chain"],
        },
        "fault_patterns": {
            "template": "{targets} degradation root cause fault pattern {scenario}",
            "mechanism_filter": ["fault_pattern", "degradation_mechanism", "causal_chain"],
        },
        "quantitative_rules": {
            "template": "{params} relationship governing equation threshold {targets}",
            "mechanism_filter": ["quantitative_rule", "causal_chain"],
        },
        "confounders": {
            "template": "{groups} confounding factor process parameter relationship {scenario}",
            "mechanism_filter": ["confounder", "control_logic"],
        },
    }

    def __init__(self, chroma_dir: str, collection_name: str,
                 embedding_model: str = "all-MiniLM-L6-v2",
                 top_k: int = 5, config: dict = None):
        self.chroma_dir = Path(chroma_dir)
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        self.top_k = top_k
        self.config = config or {}
        self._client = None
        self._collection = None
        self._model = None
        self._web_engine: Optional[WebSearchEngine] = None

    @property
    def web_engine(self) -> WebSearchEngine:
        if self._web_engine is None:
            self._web_engine = WebSearchEngine(self.config)
        return self._web_engine

    @property
    def client(self):
        if self._client is None:
            Chroma = _get_chromadb()
            self._client = Chroma.PersistentClient(
                path=str(self.chroma_dir),
                settings=_get_chromadb().Settings(anonymized_telemetry=False)
            )
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            try:
                self._collection = self.client.get_collection(self.collection_name)
            except Exception:
                self._collection = None
        return self._collection

    @property
    def model(self):
        if self._model is None:
            ST = _get_embedder()
            self._model = ST(self.embedding_model_name)
        return self._model

    def kb_ready(self) -> bool:
        """Check if the knowledge base is initialized."""
        return self.collection is not None and self.collection.count() > 0

    def total_chunks(self) -> int:
        """Return total indexed chunks."""
        if self.collection is None:
            return 0
        return self.collection.count()

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def retrieve(self, scenario: str, target_cols: List[str],
                 param_cols: List[str], group_cols: List[str],
                 mode: str = "hybrid", top_k: int = 5,
                 custom_query: Optional[str] = None) -> RetrievalResult:
        """Execute multi-perspective retrieval. If custom_query is provided
        (used for standalone web search), the 4-perspective templates are
        bypassed and only web search is performed with the custom query."""
        self.top_k = top_k
        params_str = " ".join(param_cols[:4])
        targets_str = " ".join(target_cols[:2])
        groups_str = " ".join(group_cols[:3])
        all_chunks = []
        errors = []

        # custom_query mode: standalone web search, skip 4-perspective
        if custom_query:
            if mode in ("web_only", "hybrid"):
                web_chunks = self._retrieve_web(custom_query, "web_search")
                for c in web_chunks:
                    c.perspective = "web_search"
                    c.retrieval_query = custom_query
                all_chunks.extend(web_chunks)
            unique = self._deduplicate(all_chunks)
            filtered = self._filter_by_content(unique)
            run_id = f"ret_{int(time.time())}"
            return RetrievalResult(
                retrieval_run_id=run_id,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                mode=mode, scenario=scenario,
                queries_executed=1, total_chunks_retrieved=len(all_chunks),
                total_after_dedup=len(filtered), chunks=filtered, errors=errors,
            )

        for perspective, cfg in self.QUERY_TEMPLATES.items():
            query = cfg["template"].format(
                params=params_str, targets=targets_str,
                groups=groups_str or "material batch",
                scenario=scenario
            )
            try:
                if mode in ("local_only", "hybrid"):
                    chunks = self._retrieve_local(query, cfg["mechanism_filter"])
                else:
                    chunks = []
                if mode in ("web_only", "hybrid"):
                    web_chunks = self._retrieve_web(query, perspective)
                    chunks.extend(web_chunks)
                for c in chunks:
                    c.perspective = perspective
                    c.retrieval_query = query
                all_chunks.extend(chunks)
            except Exception as e:
                errors.append(f"[{perspective}] {e}")

        # Auto-escalation: if local results are insufficient, trigger
        # expanded web queries targeting knowledge gaps in the column names.
        if mode in ("hybrid", "web_only") and len(all_chunks) < self.top_k * 4:
            # Build expanded queries for the specific scenario
            gap_cols = []
            local_param_cols = set()
            for c in all_chunks:
                for t in c.parameter_tags:
                    local_param_cols.add(t.lower())
            # Find columns not covered by local results
            for col in param_cols + target_cols:
                col_lower = col.lower().replace("_", " ")
                if not any(col_lower in tag or tag in col_lower for tag in local_param_cols):
                    gap_cols.append(col)

            # Generate expanded web queries
            from .web_search import WebSearchEngine
            expanded = WebSearchEngine.build_expanded_queries(
                scenario, param_cols, target_cols, gap_cols)
            for i, eq in enumerate(expanded[:3]):
                try:
                    web_chunks = self._retrieve_web(eq, f"expanded_{i}")
                    for c in web_chunks:
                        c.perspective = f"auto_escalated_{i}"
                        c.retrieval_query = eq
                    all_chunks.extend(web_chunks)
                except Exception as e:
                    errors.append(f"[expanded_{i}] {e}")

        # Deduplicate
        unique = self._deduplicate(all_chunks)
        # Content filter
        filtered = self._filter_by_content(unique)

        run_id = f"ret_{int(time.time())}"
        return RetrievalResult(
            retrieval_run_id=run_id,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            mode=mode,
            scenario=scenario,
            queries_executed=4,
            total_chunks_retrieved=len(all_chunks),
            total_after_dedup=len(filtered),
            chunks=filtered,
            errors=errors,
        )

    # ═══════════════════════════════════════════════════════════
    # Local retrieval (ChromaDB)
    # ═══════════════════════════════════════════════════════════

    def _retrieve_local(self, query: str, mechanism_filter: List[str]) -> List[KnowledgeChunk]:
        if not self.kb_ready():
            return []

        try:
            embedding = self.model.encode(query).tolist()
        except Exception:
            return []

        where = {"mechanism_type": {"$in": mechanism_filter}}

        try:
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=self.top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            return []

        chunks = []
        if results.get("ids") and results["ids"][0]:
            for i, cid in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                dist = results["distances"][0][i] if results.get("distances") else 0.5
                chunks.append(KnowledgeChunk(
                    chunk_id=cid,
                    content=results["documents"][0][i] if results["documents"] else "",
                    source=ChunkSource(
                        type=meta.get("source_type", "unknown"),
                        path=meta.get("source_path", ""),
                    ),
                    scenario_tags=(meta.get("scenario_types", "") or "").split(","),
                    parameter_tags=(meta.get("parameter_tags", "") or "").split(","),
                    mechanism_type=meta.get("mechanism_type", "unknown"),
                    semantic_score=round(1.0 - float(dist), 4),
                ))
        return chunks

    # ═══════════════════════════════════════════════════════════
    # Web retrieval via WebSearchEngine
    # ═══════════════════════════════════════════════════════════

    def _retrieve_web(self, query: str, perspective: str) -> List[KnowledgeChunk]:
        """Search the web via open-websearch daemon (or configured fallback)."""
        return self.web_engine.search(
            query=query,
            perspective=perspective,
            max_results=self.top_k,
        )

    def inject_web_results(self, chunks: List[KnowledgeChunk]):
        """Accept pre-fetched web results from the calling skill.

        This is the passthrough channel: the skill does its own web search
        (e.g., via Claude's built-in tools), normalizes results to
        KnowledgeChunk format, and injects them here for scoring + ontology building.
        """
        self.web_engine.inject_passthrough(chunks)

    # ═══════════════════════════════════════════════════════════
    # AI-Driven Dynamic Query Enhancement
    # ═══════════════════════════════════════════════════════════

    def enhance_queries(self, scenario: str, param_cols: List[str],
                        target_cols: List[str], group_cols: List[str]) -> Dict[str, str]:
        """Generate context-aware query variants from column names.

        Uses the actual column names to construct more specific queries than the
        4 static templates. Works for ANY industrial process — no hardcoded
        parameter lists. The column names themselves drive the query construction.

        Returns a dict of {perspective: enhanced_query} that overrides defaults.
        """
        enhanced = {}
        params_str = " ".join(param_cols[:6])
        targets_str = " ".join(target_cols[:3])

        # Dynamic: use the actual parameter and target names directly.
        # The 4-template system already handles generic cases; this adds
        # specificity by injecting real column name tokens that the embedding
        # model will use for better semantic matching.
        if param_cols and target_cols:
            enhanced["parameter_physics"] = (
                f"{' '.join(param_cols[:4])} physical meaning "
                f"equipment specification governing law {scenario}"
            )
            enhanced["quantitative_rules"] = (
                f"{' '.join(param_cols[:3])} relationship to {' '.join(target_cols[:2])} "
                f"governing equation formula threshold quantitative relationship"
            )
        if target_cols:
            enhanced["fault_patterns"] = (
                f"{' '.join(target_cols[:2])} degradation root cause "
                f"fault pattern failure mechanism {scenario}"
            )
        if group_cols:
            enhanced["confounders"] = (
                f"{' '.join(group_cols[:3])} confounding factor stratification "
                f"Simpson paradox batch effect {scenario}"
            )

        return enhanced

        return enhanced

    # ═══════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════

    def _deduplicate(self, chunks: List[KnowledgeChunk]) -> List[KnowledgeChunk]:
        """Remove near-duplicate chunks by Jaccard similarity on token set."""
        seen_ids = set()
        seen_sigs = []
        unique = []
        for c in chunks:
            if c.chunk_id in seen_ids:
                continue
            tokens = set(c.content.lower().split())
            sig = frozenset(list(tokens)[:200])
            is_dup = False
            for prev_sig in seen_sigs:
                intersection = len(sig & prev_sig)
                union = len(sig | prev_sig)
                jaccard = intersection / union if union > 0 else 0
                if jaccard > 0.85:
                    is_dup = True
                    break
            if not is_dup:
                unique.append(c)
                seen_ids.add(c.chunk_id)
                seen_sigs.append(sig)
        return unique

    def _filter_by_content(self, chunks: List[KnowledgeChunk]) -> List[KnowledgeChunk]:
        """Filter out chunks that are too short or clearly irrelevant."""
        out = []
        for c in chunks:
            content_len = len(c.content.strip())
            if content_len < 50:
                continue
            # Check for obviously irrelevant content
            lower = c.content.lower()
            if any(term in lower for term in
                   ["medical diagnosis", "financial analysis", "stock market",
                    "software deployment", "api endpoint", "javascript"]):
                continue
            if content_len > 5000:  # Truncate very long chunks
                c.content = c.content[:5000] + "..."
            out.append(c)
        return out
