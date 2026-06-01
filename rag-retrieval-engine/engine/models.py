"""
Pydantic models — all request/response types for the RAG engine API.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime


# ═══════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════

class RetrievalMode(str, Enum):
    local_only = "local_only"
    web_only = "web_only"
    hybrid = "hybrid"

class MechanismType(str, Enum):
    causal_chain = "causal_chain"
    quantitative_rule = "quantitative_rule"
    fault_pattern = "fault_pattern"
    degradation_mechanism = "degradation_mechanism"
    equipment_spec = "equipment_spec"
    confounder = "confounder"
    control_logic = "control_logic"
    knowledge_general = "knowledge_general"

class SourceType(str, Enum):
    local_reference = "local_reference"
    accumulated_diag_verified = "accumulated_diag_verified"
    user_documentation = "user_documentation"
    web_authoritative = "web_authoritative"
    accumulated_diag_unverified = "accumulated_diag_unverified"
    web_general = "web_general"
    unknown = "unknown"

class Tier(str, Enum):
    CRITICAL = "CRITICAL"
    ACCEPTED = "ACCEPTED"
    CONDITIONAL = "CONDITIONAL"
    REJECTED = "REJECTED"

class InjectionMode(str, Enum):
    auto = "auto"
    review = "review"


# ═══════════════════════════════════════════════════════════════
# Request Models
# ═══════════════════════════════════════════════════════════════

class RetrieveRequest(BaseModel):
    """Request to retrieve knowledge for a diagnostic scenario."""
    scenario: str = Field(..., description="Process scenario, e.g. 'CNC machining'")
    target_columns: List[str] = Field(default=[],
                                      description="Quality target column names")
    parameter_columns: List[str] = Field(default=[],
                                         description="Candidate predictor column names")
    group_columns: List[str] = Field(default=[],
                                     description="Grouping/confounder column names")
    mode: RetrievalMode = Field(default=RetrievalMode.hybrid,
                                description="Retrieval mode")
    top_k: int = Field(default=5, ge=1, le=20,
                       description="Max chunks per query perspective")
    custom_query: Optional[str] = Field(default=None,
                                        description="Override search query for web-only mode")

    class Config:
        json_schema_extra = {
            "example": {
                "scenario": "CNC machining",
                "target_columns": ["surface_roughness_Ra_um", "thermal_deviation_mm"],
                "parameter_columns": ["spindle_vibration_mm_s", "spindle_temp_C",
                                      "tool_age_parts", "feed_rate_mm_min"],
                "group_columns": ["material", "tool_id"],
                "mode": "hybrid",
                "top_k": 5
            }
        }


class ScoreRequest(BaseModel):
    """Request to score retrieved chunks against diagnostic context."""
    retrieval_run_id: str = Field(..., description="Run ID from retrieve step")
    scenario: str
    parameter_columns: List[str]
    target_columns: List[str]
    pass_threshold: float = Field(default=6.5, ge=0, le=10)


class InjectRequest(BaseModel):
    """Request to build ontology draft from scored chunks."""
    retrieval_run_id: str = Field(..., description="Run ID from retrieve+score step")
    column_details: List[Dict[str, Any]] = Field(...,
        description="Column manifest from input_manifest.json")
    mode: InjectionMode = Field(default=InjectionMode.auto)


class IndexRequest(BaseModel):
    """Request to rebuild the knowledge index from config.yaml sources only.

    NOTE: `sources` field is retained for backward compatibility of the JSON
    schema but is intentionally ignored by the server. Only pre-configured
    sources listed in config.yaml `knowledge_base.index_sources` are indexed.
    User-supplied paths are rejected to prevent arbitrary file access.
    """
    sources: List[Dict[str, str]] = Field(
        default=[],
        description="IGNORED — sources must be configured in config.yaml"
    )
    rebuild: bool = Field(
        default=False,
        description="If true, clear and rebuild entire index. Requires API key."
    )


class AccumulateRequest(BaseModel):
    """Request to accumulate verified diagnosis into KB."""
    run_dir: str = Field(..., description="Path to completed diagnostic run")
    confidence_threshold: float = Field(default=0.8, ge=0, le=1)


# ═══════════════════════════════════════════════════════════════
# Knowledge Models
# ═══════════════════════════════════════════════════════════════

class ChunkSource(BaseModel):
    type: SourceType
    path: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None


class KnowledgeChunk(BaseModel):
    chunk_id: str
    content: str
    content_preview: Optional[str] = None
    source: ChunkSource
    scenario_tags: List[str] = Field(default=[])
    parameter_tags: List[str] = Field(default=[])
    mechanism_type: Optional[str] = None
    semantic_score: Optional[float] = None
    perspective: Optional[str] = None
    retrieval_query: Optional[str] = None


class RetrievalResult(BaseModel):
    retrieval_run_id: str
    timestamp: str
    mode: str
    scenario: str
    queries_executed: int = 4
    total_chunks_retrieved: int
    total_after_dedup: int
    chunks: List[KnowledgeChunk]
    errors: List[str] = Field(default=[])


class DimensionScores(BaseModel):
    D1_semantic: float
    D2_param_match: float
    D3_scenario: float
    D4_source: float
    D5_crossref: float


class ScoredChunk(BaseModel):
    chunk_id: str
    content_preview: Optional[str] = None
    source: ChunkSource
    scores: DimensionScores
    composite_score: float
    tier: Tier
    injectable: bool
    rejection_reason: Optional[str] = None
    injection_target: Optional[str] = None
    scoring_notes: Optional[str] = None


class ScoringResult(BaseModel):
    retrieval_run_id: str
    timestamp: str
    scoring_version: str = "2.0"
    input_chunks: int
    critical: int
    accepted: int
    conditional: int
    rejected: int
    auto_rejected: Dict[str, int]
    chunks: List[ScoredChunk]
    auto_proceed: bool
    human_review_required: bool
    recommendation: str


class InjectionMetadata(BaseModel):
    total_chunks_injected: int
    total_columns: int
    columns_matched: int
    columns_without_knowledge: List[str]
    match_rate_pct: float
    confidence_scores: List[float]
    auto_proceed: bool


class OntologyDraft(BaseModel):
    scene: Dict[str, Any] = Field(default_factory=dict)
    signals: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    confounders: List[Dict[str, Any]] = Field(default_factory=list)
    equipment: List[Dict[str, Any]] = Field(default_factory=list)
    rag_injection_metadata: Optional[InjectionMetadata] = None


# ═══════════════════════════════════════════════════════════════
# Storage Models (SQLite-serialized)
# ═══════════════════════════════════════════════════════════════

class StoredRun(BaseModel):
    run_id: str
    created_at: str
    scenario: str
    mode: str
    target_columns: List[str]
    parameter_columns: List[str]
    status: str = "pending"         # pending, retrieved, scored, injected
    retrieval_result_path: Optional[str] = None
    scoring_result_path: Optional[str] = None
    ontology_path: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    kb_ready: bool
    total_chunks: int
    uptime_seconds: float
