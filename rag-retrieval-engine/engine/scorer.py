"""
5-Dimension Relevance Scorer — evaluates every retrieved chunk against diagnostic context.
"""

import json, time, re
from typing import List, Dict, Optional
from collections import Counter
from .models import (
    ScoredChunk, ScoringResult, DimensionScores, Tier, KnowledgeChunk, ChunkSource
)

# ── Physical quantity token clusters ──────────────────────────
# Used for D2 fuzzy parameter matching. These are common industrial
# measurement categories — the list is intentionally broad to cover
# any process type. Unknown column names are matched via substring
# overlap (no list needed) — these clusters only handle common cases.
PHYSICAL_TOKEN_CLUSTERS: Dict[str, List[str]] = {
    "temp": ["temperature", "thermal", "heat", "cooling", "cryo"],
    "vib": ["vibration", "oscillation", "resonance", "displacement_amplitude"],
    "speed": ["velocity", "rpm", "angular", "rate", "frequency", "motor_speed"],
    "force": ["load", "stress", "torque", "tension", "compression", "strain"],
    "press": ["pressure", "vacuum", "hydraulic", "pneumatic", "differential_pressure"],
    "flow": ["flow_rate", "fluid", "circulation", "mass_flow", "volumetric_flow"],
    "surface": ["roughness", "finish", "texture", "profile", "waviness", "flatness"],
    "dimension": ["deviation", "error", "drift", "offset", "tolerance", "thickness", "width", "diameter"],
    "wear": ["tool", "wear", "degradation", "aging", "life", "condition", "health_index"],
    "material": ["material", "alloy", "grade", "substrate", "composition", "chemistry"],
    "position": ["position", "displacement", "gap", "clearance", "alignment", "level"],
    "power": ["power", "energy", "current", "voltage", "consumption", "efficiency"],
    "concentration": ["concentration", "purity", "yield", "conversion", "selectivity", "ph"],
    "time": ["duration", "cycle_time", "residence_time", "lag", "delay", "age"],
}

# Source credibility mapping — universal, not scenario-specific
SOURCE_CREDIBILITY: Dict[str, float] = {
    "local_reference": 10.0,
    "accumulated_diag_verified": 8.0,
    "user_documentation": 7.0,
    "web_authoritative": 6.0,
    "accumulated_diag_unverified": 4.0,
    "web_general": 3.0,
    "unknown": 1.0,
}


class RelevanceScorer:
    """Scores knowledge chunks against diagnostic context using 5 independent dimensions."""

    def __init__(self, config: Dict, chunks: List[KnowledgeChunk],
                 scenario: str, param_cols: List[str], target_cols: List[str],
                 pass_threshold: float = 6.5):
        self.chunks = chunks
        self.scenario = scenario
        self.param_set = set(self._normalize(param_cols))
        self.target_set = set(self._normalize(target_cols))

        # Scoring config
        sc = config.get("scoring", {})
        self.pass_threshold = pass_threshold
        self.weights = sc.get("weights", {
            "D1_semantic": 0.30, "D2_param_match": 0.25,
            "D3_scenario": 0.20, "D4_source": 0.15, "D5_crossref": 0.10,
        })
        ar = sc.get("auto_reject", {})
        self.reject_D1 = ar.get("D1_below", 3.0)    # Only reject truly irrelevant
        self.reject_D4 = ar.get("D4_below", 3.0)
        dr = ar.get("D2_and_D3", [1.0, 3.0])        # Catch only complete mismatches
        self.reject_D2 = dr[0] if isinstance(dr, list) else 4.0
        self.reject_D3 = dr[1] if isinstance(dr, list) and len(dr) > 1 else 5.0
        self.src_cred = sc.get("source_credibility", SOURCE_CREDIBILITY)

    # ═══════════════════════════════════════════════════════════

    def score_all(self) -> ScoringResult:
        """Score all chunks, apply gates, return results."""
        scored = []
        tiers = Counter()
        auto_rejected = Counter()

        for chunk in self.chunks:
            d1 = self._score_d1(chunk)
            d2 = self._score_d2(chunk)
            d3 = self._score_d3(chunk)
            d4 = self._score_d4(chunk)
            d5 = self._score_d5(chunk)

            composite = round(
                d1 * self.weights["D1_semantic"] +
                d2 * self.weights["D2_param_match"] +
                d3 * self.weights["D3_scenario"] +
                d4 * self.weights["D4_source"] +
                d5 * self.weights["D5_crossref"],
                2
            )

            # Auto-reject
            rejected = False
            reject_reason = None

            # Trusted source? Skip D1 and R3 reject — local KB is pre-vetted
            src_trusted = d4 >= 7.0

            if d1 < self.reject_D1 and not src_trusted:
                rejected = True
                reject_reason = "R1_semantic_too_low"
            elif d4 < self.reject_D4:
                rejected = True
                reject_reason = "R2_source_unreliable"
            elif d2 < self.reject_D2 and d3 < self.reject_D3 and not src_trusted:
                rejected = True
                reject_reason = "R3_no_param_or_scenario_match"
            elif d5 == 0 and str(chunk.source.type) == "web_general":
                rejected = True
                reject_reason = "R4_unverifiable_web_singleton"

            if rejected:
                tier = Tier.REJECTED
                auto_rejected[reject_reason] += 1
            elif composite >= 8.0:
                tier = Tier.CRITICAL
            elif composite >= 6.0:
                tier = Tier.ACCEPTED
            elif composite >= self.pass_threshold:
                tier = Tier.CONDITIONAL
            elif src_trusted and composite >= 3.5:
                # Local KB chunks with parameter match → at least CONDITIONAL
                tier = Tier.CONDITIONAL
            else:
                tier = Tier.REJECTED
                auto_rejected["below_composite_threshold"] += 1

            tiers[tier.value] += 1

            # Injectability: CRITICAL and ACCEPTED always injectable.
            # CONDITIONAL is injectable with reduced confidence — the
            # ontology builder handles the confidence downgrade.
            injectable = tier in (Tier.CRITICAL, Tier.ACCEPTED, Tier.CONDITIONAL)

            scored.append(ScoredChunk(
                chunk_id=chunk.chunk_id,
                content_preview=chunk.content[:200] if chunk.content else "",
                source=chunk.source,
                scores=DimensionScores(
                    D1_semantic=round(d1, 1),
                    D2_param_match=round(d2, 1),
                    D3_scenario=round(d3, 1),
                    D4_source=round(d4, 1),
                    D5_crossref=round(d5, 1),
                ),
                composite_score=composite,
                tier=tier,
                injectable=injectable,
                rejection_reason=reject_reason,
                injection_target=self._infer_target(chunk),
            ))

        # Single-source dominance check
        self._apply_source_dominance(scored, tiers)

        auto_proceed = tiers.get("critical", 0) >= 1
        human_needed = not (auto_proceed or tiers.get("accepted", 0) >= 2)

        return ScoringResult(
            retrieval_run_id="",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            scoring_version="2.0",
            input_chunks=len(self.chunks),
            critical=tiers.get("critical", 0),
            accepted=tiers.get("accepted", 0),
            conditional=tiers.get("conditional", 0),
            rejected=tiers.get("rejected", 0),
            auto_rejected=dict(auto_rejected),
            chunks=scored,
            auto_proceed=auto_proceed,
            human_review_required=human_needed,
            recommendation="AUTO_PROCEED" if auto_proceed else "HUMAN_REVIEW_REQUIRED",
        )

    # ═══════════════════════════════════════════════════════════
    # D1-D5 scoring functions
    # ═══════════════════════════════════════════════════════════

    def _score_d1(self, chunk: KnowledgeChunk) -> float:
        """D1: Semantic relevance (0-10). Uses embedding score when available,
        falls back to keyword overlap, boosted by source credibility."""
        sem = chunk.semantic_score
        if sem is not None and sem > 0:
            return max(0.0, min(10.0, sem * 10))

        # Fallback: keyword overlap
        content = (chunk.content or chunk.content_preview or "").lower()
        context_words = set(self.scenario.lower().split())
        for p in self.param_set:
            context_words.update(p.lower().replace("_", " ").split())
            context_words.add(p.lower().replace("_", ""))  # e.g., spindle_vibration_mm_s
        for t in self.target_set:
            context_words.update(t.lower().replace("_", " ").split())

        chunk_words = set(content.split())
        # Also add parameter names from tags as context boost
        for tag in chunk.parameter_tags:
            context_words.update(tag.lower().replace("_", " ").split())
            context_words.add(tag.lower().replace("_", ""))

        if not context_words:
            return 5.0
        overlap = len(context_words & chunk_words) / max(len(context_words), 1)
        base_score = min(9.0, overlap * 25 + 2.0)

        # Boost: trusted source + parameter match → floor D1
        st = str(chunk.source.type)
        if "." in st:
            st = st.split(".")[-1]
        if st in ("local_reference", "accumulated_diag_verified", "user_documentation"):
            # If chunk has parameter tags matching our context, it IS relevant
            chunk_params = set(t.lower() for t in chunk.parameter_tags)
            if chunk_params & self.param_set:
                base_score = max(base_score, 6.0)  # Trusted source + param match = floor of 6.0

        return max(2.0, base_score)

    def _score_d2(self, chunk: KnowledgeChunk) -> float:
        """D2: Parameter direct match (0-10). Uses overlap-based scoring.

        Matches work across three levels:
        1. Exact name match (column name == chunk tag)
        2. Token overlap (shared word fragments)
        3. Physical quantity cluster match (uses PHYSICAL_TOKEN_CLUSTERS)

        A chunk matching even one parameter well gets a decent score —
        this keeps the system useful for any industrial process, not just
        pre-known ones.
        """
        chunk_params = set(self._normalize(chunk.parameter_tags))
        if not chunk_params:
            content_lower = (chunk.content or chunk.content_preview or "").lower()
            for p in self.param_set:
                fragments = p.lower().replace("_", " ").split()
                if any(f in content_lower for f in fragments):
                    chunk_params.add(p.lower())
        if not chunk_params:
            return 2.0

        match_count = 0.0
        for param in self.param_set:
            param_l = param.lower()
            param_tokens = set(param_l.replace("_", " ").split())

            if param_l in chunk_params:
                match_count += 1.0
                continue

            # Token overlap
            for cp in chunk_params:
                if param_tokens & set(cp.replace("_", " ").split()):
                    match_count += 0.5
                    break
            else:
                # Physical cluster match — check any cluster
                for cluster_name, synonyms in PHYSICAL_TOKEN_CLUSTERS.items():
                    cluster_hit = any(
                        any(syn in param_l for syn in synonyms)
                        for cp in chunk_params
                        if any(syn in cp for syn in synonyms)
                    )
                    if cluster_hit:
                        match_count += 0.3
                        break

        effective_params = min(len(self.param_set), max(len(chunk_params), 1))
        score = (match_count / effective_params) * 10.0
        return min(10.0, max(1.5, score))

    def _score_d3(self, chunk: KnowledgeChunk) -> float:
        """D3: Scenario consistency (0-10).

        Uses word-overlap between the user's scenario description and the
        chunk's scenario tags + content. No hardcoded neighbor lists —
        any two descriptions with shared tokens get partial credit.
        """
        tags = set(t.lower().replace(" ", "_") for t in chunk.scenario_tags)
        scenario_key = self.scenario.lower().replace(" ", "_")
        scenario_words = set(scenario_key.replace("_", " ").split())

        if not tags:
            return 5.0  # Neutral — no scenario info available

        if scenario_key in tags:
            return 10.0

        # Dynamic: word overlap between scenario description and chunk tags
        best_overlap = 0.0
        for tag in tags:
            tag_words = set(tag.replace("_", " ").split())
            overlap = len(scenario_words & tag_words) / max(
                len(scenario_words | tag_words), 1)
            best_overlap = max(best_overlap, overlap)

        if best_overlap > 0.3:
            return 7.0  # Strong word overlap — likely related
        if best_overlap > 0.1:
            return 5.0  # Some overlap — partially related

        if "generic" in tags or "multi" in tags:
            return 5.0

        # Content-based: does the chunk text mention the scenario?
        content_lower = (chunk.content or chunk.content_preview or "").lower()
        scenario_terms = scenario_key.replace("_", " ").split()
        if any(term in content_lower for term in scenario_terms):
            return 5.0

        return 4.0  # Slight penalty — no relationship found

    def _score_d4(self, chunk: KnowledgeChunk) -> float:
        """D4: Source credibility (0-10). Handles both string and enum source types."""
        st = str(chunk.source.type)
        # SourceType enum strings look like "SourceType.local_reference"
        # → extract just the value part
        if "." in st:
            st = st.split(".")[-1]
        # Fallback for metadata-only chunks: use source_path hints
        if (not st or st == "unknown") and chunk.source.path:
            path_lower = chunk.source.path.lower()
            if "parameter_to_physics" in path_lower:
                st = "local_reference"
            elif "process_knowledge_base" in path_lower:
                st = "local_reference"
        return float(self.src_cred.get(st, 5.0))  # Default 5.0 — neutral, not zero

    def _score_d5(self, chunk: KnowledgeChunk) -> float:
        """D5: Cross-reference count (0-10)."""
        chunk_params = set(self._normalize(chunk.parameter_tags))
        confirms = 0
        for other in self.chunks:
            if other.chunk_id == chunk.chunk_id:
                continue
            if (other.source.path and other.source.path == chunk.source.path) or \
               (other.source.url and other.source.url == chunk.source.url):
                continue
            other_params = set(self._normalize(other.parameter_tags))
            if chunk_params & other_params:
                confirms += 1
        mapping = {10: 10, 7: 7, 4: 4}.get(confirms, 1)
        return float(mapping)

    # ═══════════════════════════════════════════════════════════

    def _apply_source_dominance(self, scored: List[ScoredChunk], tiers: Counter):
        """Demote excess CRITICAL chunks from the same source."""
        src_counts = Counter()
        for s in scored:
            if s.tier == Tier.CRITICAL:
                key = s.source.path or s.source.url or "unknown"
                src_counts[key] += 1
        for src, count in src_counts.items():
            if count > 3:
                excess = 0
                for s in scored:
                    if (s.source.path == src or s.source.url == src) and \
                       s.tier == Tier.CRITICAL:
                        excess += 1
                        if excess > 3:
                            s.tier = Tier.ACCEPTED
                            s.injectable = True
                            tiers["critical"] -= 1
                            tiers["accepted"] += 1

    @staticmethod
    def _infer_target(chunk: KnowledgeChunk) -> Optional[str]:
        """Infer which ontology field this chunk should inject into."""
        mt = chunk.mechanism_type
        if mt in ("causal_chain", "quantitative_rule"):
            return "relationships[]"
        if mt in ("equipment_spec",):
            return "signals.process_parameters[]"
        if mt in ("fault_pattern", "degradation_mechanism"):
            return "scene.expected_faults[]"
        if mt in ("confounder", "control_logic"):
            return "confounders[]"
        return None

    @staticmethod
    def _normalize(items: List[str]) -> List[str]:
        return [str(i).lower().strip() for i in (items or [])]
