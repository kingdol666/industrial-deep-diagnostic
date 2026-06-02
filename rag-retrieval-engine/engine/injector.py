"""
Knowledge Injector — STUB ONLY (v3.0)

⚠️  DEPRECATION NOTICE (v3.0)
═══════════════════════════════════════════════════════════════════════════
This module is RETAINED FOR BACKWARD COMPATIBILITY ONLY. It is no longer
the path from scored chunks to ontology. Starting in v3.0:

  • The LLM-driven `agents/ontology-construction-agent.md` is the
    ONLY valid path from chunks to ontology.
  • `inject()` here returns a scaffold ontology with a clear warning
    banner; downstream consumers should ignore it.
  • The legacy hardcoded mappings (spindle_assembly, 刀具, 换热器)
    have been REMOVED.

Why: When tested against the BOPET biaxial stretching scenario, this
injector produced wrong results:
  - Injected `spindle_assembly` equipment (CNC false positive)
  - Mapped `melt_temp_C` → "轴承/主轴温度" (wrong physical meaning)
  - Added `cutter_wear → Ra` causal chains (BOPET has no cutter)
LLM-driven construction correctly rejected all of these.

The kept code below is a MINIMAL scaffold + the column→role bucketing
heuristics (target/predictor/control/metadata) which are still useful
as a SAFETY NET signal — but no physical meaning, equipment, or causal
chains are produced here.
═══════════════════════════════════════════════════════════════════════════
"""

import re, time, warnings
from typing import List, Dict, Optional, Tuple
from .models import ScoredChunk, OntologyDraft, InjectionMetadata, Tier

# Column-name → role bucketing (language-agnostic, no scenario hardcoding).
# These are FALLBACK heuristics only. The LLM agent overrides them.
QUALITY_PATTERNS = [
    "roughness", "defect", "quality", "deviation", "error", "tolerance",
    "scrap", "reject", "yield", "thickness", "haze", "conversion",
    "selectivity", "particle_size", "purity", "uniformity",
    "粗糙度", "缺陷", "质量", "偏差", "厚度", "雾度", "转化率", "纯度",
]
CONTROL_PATTERNS = [
    "setpoint", "sp", "target_", "command_",
]
META_PATTERNS = [
    "timestamp", "time", "date", "_id", "batch", "shift", "operator",
    "product", "material", "grade", "lot", "serial",
]


class KnowledgeInjector:
    """v3.0 STUB: Returns a minimal ontology scaffold.

    The real ontology construction happens in
    `agents/ontology-construction-agent.md` (LLM-driven).

    This class still does one useful thing: bucketing columns into roles
    (target/predictor/control/metadata) based on column-name patterns.
    The LLM agent can use this as a hint but always validates.
    """

    def __init__(self, scored_chunks: List[ScoredChunk],
                 column_details: List[Dict],
                 scenario: str = "unclear"):
        self.chunks = [c for c in scored_chunks if c.injectable]
        self.columns = column_details
        self.scenario = scenario
        self._chunk_param_map = self._build_chunk_param_map()
        warnings.warn(
            "KnowledgeInjector is DEPRECATED in v3.0. "
            "Use the LLM-driven agent (agents/ontology-construction-agent.md) "
            "to construct the ontology. The injector now returns a scaffold only.",
            DeprecationWarning,
            stacklevel=2,
        )

    def inject(self) -> OntologyDraft:
        """Build a MINIMAL scaffold ontology. LLM agent is expected to override.

        Returns:
            OntologyDraft with:
            - process_type="unclear" (forces LLM to identify the real type)
            - equipment=[] (forces LLM to identify scenario-specific equipment)
            - inspection_signals with role bucketing but physical_meaning=None
            - relationships=[]
            - confounders=[]
            - rag_injection_metadata with a clear "stub_used" flag
        """
        warnings.warn(
            "DEPRECATED injector.inject() called. Returning SCAFFOLD. "
            "The diagnostic skill should use the LLM-driven agent instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        col_names = [c.get("name", "") for c in self.columns]
        matched = set()
        process_params = []
        inspection_signals = []
        control_vars = []
        meta_cols = []

        for col in self.columns:
            name = col.get("name", "")
            if not name:
                continue
            if self._is_meta(name):
                meta_cols.append(self._make_signal(
                    name, col, role="metadata", meaning=None))
                matched.add(name)
                continue

            if self._is_quality(name):
                signal = self._make_signal(
                    name, col, role="target", meaning=None)
                inspection_signals.append(signal)
                matched.add(name)
            elif self._is_control(name):
                signal = self._make_signal(
                    name, col, role="control", meaning=None)
                control_vars.append(signal)
                matched.add(name)
            else:
                signal = self._make_signal(
                    name, col, role="predictor", meaning=None)
                process_params.append(signal)
                matched.add(name)

        unmatched = [c.get("name", "") for c in self.columns
                     if c.get("name", "") not in matched and c.get("name")]

        return OntologyDraft(
            scene={
                "name": self.scenario,
                "process_type": "unclear",
                "process_type_confidence": "UNKNOWN",
                "scenario_summary": "Stub: LLM agent must fill this in.",
                "primary_quality_drivers": [],
            },
            signals={
                "inspection_signals": inspection_signals,
                "process_parameters": process_params,
                "control_variables": control_vars,
                "events": [],
                "metadata_columns": meta_cols,
            },
            relationships=[],
            confounders=[],
            equipment=[],
            process_stages=[],
            rag_injection_metadata=InjectionMetadata(
                total_chunks_injected=len(self.chunks),
                total_columns=len(self.columns),
                columns_matched=len(matched),
                columns_without_knowledge=unmatched,
                match_rate_pct=round(
                    100.0 * len(matched) / max(1, len(self.columns)), 1),
                injection_mode="DEPRECATED_STUB_v3.0",
                llm_construction_required=True,
                llm_agent_prompt="agents/ontology-construction-agent.md",
                notes=(
                    "v3.0 STUB: This ontology was produced by the deprecated "
                    "KnowledgeInjector. Physical meanings, equipment, and "
                    "causal relationships are EMPTY. The LLM-driven agent "
                    "MUST be invoked to produce a real ontology."
                ),
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            ),
        )

    # ── Role bucketing (column name pattern matching, language-agnostic) ──
    def _is_quality(self, name: str) -> bool:
        n = name.lower()
        return any(p in n for p in QUALITY_PATTERNS)

    def _is_control(self, name: str) -> bool:
        n = name.lower()
        return any(p in n for p in CONTROL_PATTERNS)

    def _is_meta(self, name: str) -> bool:
        n = name.lower()
        return any(p in n for p in META_PATTERNS)

    def _build_chunk_param_map(self) -> Dict[str, List[str]]:
        """Map chunk_id → list of column names mentioned in chunk content."""
        m = {}
        for c in self.chunks:
            cols = []
            for col in self.columns:
                cn = col.get("name", "")
                if cn and (cn in (c.content_preview or "") or
                           cn in (c.content or "")):
                    cols.append(cn)
            m[c.chunk_id] = cols
        return m

    def _best_match(self, col_name: str) -> Optional[ScoredChunk]:
        """Return the highest-scoring chunk that mentions this column."""
        candidates = [c for c in self.chunks
                      if col_name in (c.content_preview or "") or
                      col_name in (c.content or "")]
        if not candidates:
            return None
        return max(candidates, key=lambda c: c.composite_score)

    def _extract_meaning(self, chunk: ScoredChunk) -> Optional[str]:
        """Stub: NO LONGER EXTRACTS PHYSICAL MEANING.
        Returns None so the LLM agent is forced to fill it in."""
        return None

    def _make_signal(self, name: str, col: Dict, role: str,
                     meaning: Optional[str],
                     best_chunk: Optional[ScoredChunk] = None) -> Dict:
        """Make a signal record. Physical meaning is always None in v3.0 stub."""
        return {
            "name": name,
            "role": role,
            "physical_meaning": meaning,
            "physical_meaning_confidence": "UNKNOWN" if meaning is None else "INFERRED",
            "unit": col.get("unit", "unknown"),
            "expected_range": None,
            "knowledge_source": best_chunk.chunk_id if best_chunk else None,
            "reasoning": "Stub: LLM agent must provide physical_meaning.",
        }

    def _build_relationships(self) -> List[Dict]:
        """Stub: NEVER builds causal chains. LLM agent must do this."""
        return []

    def _build_confounders(self) -> List[Dict]:
        """Stub: NEVER identifies confounders. LLM agent must do this."""
        return []

    def _confidence(self, c: ScoredChunk) -> float:
        return getattr(c, "composite_score", 0.0) / 10.0
