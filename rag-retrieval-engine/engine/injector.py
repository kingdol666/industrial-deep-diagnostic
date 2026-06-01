"""
Knowledge Injector — maps scored chunks to ontology fields via schema-driven injection.

Produces ontology_draft.json compatible with industrial-deep-diagnostic's
ontology_schema.json (v6.2).  Extra fields (knowledge_confidence, knowledge_source,
injected_from_chunk) are intentionally added — the diagnostic schema permits
additional properties, and the context-builder agent uses them for provenance.
"""

import re, time
from typing import List, Dict, Optional, Tuple
from .models import ScoredChunk, OntologyDraft, InjectionMetadata, Tier

# Column naming → role heuristics
QUALITY_PATTERNS = [
    "roughness", "defect", "quality", "deviation", "error", "tolerance",
    "scrap", "reject", "yield", "thickness_dev", "conversion", "selectivity",
    "粗糙度", "缺陷", "质量", "偏差",
]
CONTROL_PATTERNS = [
    "speed", "feed", "depth", "setpoint", "rpm",
]
META_PATTERNS = [
    "timestamp", "time", "date", "id", "batch", "shift", "operator",
    "product", "material", "tool_id",
]


class KnowledgeInjector:
    """Transforms scored knowledge chunks into an industrial process ontology draft
    compatible with the diagnostic skill's ontology_schema.json (v6.2)."""

    def __init__(self, scored_chunks: List[ScoredChunk],
                 column_details: List[Dict],
                 scenario: str = "generic"):
        self.chunks = [c for c in scored_chunks if c.injectable]
        self.columns = column_details
        self.scenario = scenario
        # Cache chunk info for parameter matching
        self._chunk_param_map = self._build_chunk_param_map()

    def inject(self) -> OntologyDraft:
        """Build complete ontology draft."""
        col_names = [c.get("name", "") for c in self.columns]

        matched = set()
        process_params = []
        inspection_signals = []
        control_vars = []
        meta_cols = []

        for col in self.columns:
            name = col.get("name", "")
            if not name or self._is_meta(name):
                if name:
                    meta_cols.append(self._make_signal(
                        name, col, role="metadata", meaning=None))
                    matched.add(name)
                continue

            best = self._best_match(name)
            meaning_text = self._extract_meaning(best) if best else None

            if self._is_quality(name):
                signal = self._make_signal(
                    name, col, role="target", meaning=meaning_text,
                    best_chunk=best)
                inspection_signals.append(signal)
                matched.add(name)
            elif self._is_control(name):
                signal = self._make_signal(
                    name, col, role="control", meaning=meaning_text,
                    best_chunk=best)
                control_vars.append(signal)
                matched.add(name)
            else:
                signal = self._make_signal(
                    name, col, role="predictor", meaning=meaning_text,
                    best_chunk=best)
                process_params.append(signal)
                matched.add(name)

        unmatched = [c.get("name", "") for c in self.columns
                     if c.get("name", "") not in matched and c.get("name")]
        confidences = [self._confidence(c) for c in self.chunks]

        return OntologyDraft(
            scene={
                "name": self.scenario,
                "process_type": self.scenario,
                "equipment": self._build_equipment(),
                "expected_faults": self._build_faults(),
            },
            signals={
                "inspection_signals": inspection_signals,
                "process_parameters": process_params,
                "control_variables": control_vars,
                "events": [],
                "metadata_columns": meta_cols,
            },
            relationships=self._build_relationships(),
            confounders=self._build_confounders(),
            equipment=self._build_equipment(),
            rag_injection_metadata=InjectionMetadata(
                total_chunks_injected=len(self.chunks),
                total_columns=len(self.columns),
                columns_matched=len(matched),
                columns_without_knowledge=unmatched,
                match_rate_pct=round(
                    len(matched) / max(len(self.columns), 1) * 100, 1),
                confidence_scores=confidences,
                auto_proceed=len(matched) >= 2,
            ),
        )

    # ═══════════════════════════════════════════════════════════
    # Signal construction — diagnostic-schema-compliant
    # ═══════════════════════════════════════════════════════════

    def _make_signal(self, name: str, col: Dict, role: str,
                     meaning: Optional[str] = None,
                     best_chunk: Optional[ScoredChunk] = None) -> Dict:
        """Build a signal entry compatible with ontology_schema.json signal_v6."""
        entry = {
            "name": name,
            "column": name,
            "role": role,
            "unit": col.get("unit") or self._guess_unit(name),
        }

        if best_chunk and meaning:
            entry["physical_meaning"] = meaning
            entry["governing_law"] = self._extract_law(best_chunk)
            entry["physical_meaning_confidence"] = (
                "KNOWN" if self._confidence(best_chunk) >= 0.8 else "INFERRED")
            entry["auto_inferred"] = False
            entry["inference_basis"] = (
                f"RAG knowledge base retrieval — source: "
                f"{best_chunk.source.path or best_chunk.source.url or 'rag'}")
            entry["knowledge_confidence"] = self._confidence(best_chunk)
            entry["knowledge_source"] = (
                best_chunk.source.path or best_chunk.source.url or "rag")
            entry["injected_from_chunk"] = best_chunk.chunk_id
        else:
            entry["physical_meaning_confidence"] = "UNKNOWN"
            entry["auto_inferred"] = True
            entry["inference_basis"] = "no matching knowledge chunk in RAG KB"
            entry["knowledge_confidence"] = 0.0

        # Role-specific extras
        if role == "target":
            entry["target"] = None
            entry["tolerance"] = None
        elif role == "predictor":
            entry["normal_range"] = [None, None]
            entry["control_type"] = "measurement"

        return entry

    # ═══════════════════════════════════════════════════════════

    def _build_faults(self) -> List[Dict]:
        faults = []
        for c in self.chunks:
            if c.injection_target == "scene.expected_faults":
                faults.append({
                    "symptom": (c.content_preview or "")[:200],
                    "root_cause": self._extract_mechanism(c.content_preview or "") or "",
                    "knowledge_source": c.source.path or "",
                    "knowledge_confidence": self._confidence(c),
                })
        return faults

    def _build_relationships(self) -> List[Dict]:
        rels = []
        # Collect known column names so we can map chain endpoints back to columns
        all_col_names = {c.get("name", "").lower() for c in self.columns}

        for c in self.chunks:
            if c.injection_target != "relationships[]":
                continue
            mechanism = self._extract_mechanism(c.content_preview or "")
            if not mechanism:
                continue

            # Try to map endpoints to actual column names
            from_col, to_col = self._map_endpoints_to_columns(
                c.content_preview or "", all_col_names)

            rels.append({
                "from": from_col or "unknown_parameter",
                "to": to_col or "unknown_target",
                "type": "causal",
                "strength": "strong",
                "mechanism": mechanism,
                "time_lag": "",
                "inferred": False,
                # RAG extras — compatible with diagnostic schema
                "governing_equation": self._extract_law(c),
                "knowledge_confidence": self._confidence(c),
                "knowledge_source": c.source.path or "rag",
                "injected_from_chunk": c.chunk_id,
            })
        return rels

    def _build_confounders(self) -> List[Dict]:
        group_cols = [
            c.get("name", "") for c in self.columns
            if any(p in c.get("name", "").lower()
                   for p in ["material", "product", "batch", "tool", "shift",
                             "grade", "type", "operator", "lot"])
        ]
        return [
            {
                "variable": gc,
                "why": "分组变量 — 需要在每个子组内验证相关性（Simpson's Paradox 检查）",
                "controlled": False,
            }
            for gc in group_cols
        ]

    def _build_equipment(self) -> List[Dict]:
        equip = []
        for c in self.chunks:
            content = c.content_preview or ""
            if any(kw in content for kw in ["主轴", "spindle"]):
                equip.append({
                    "id": "spindle_assembly",
                    "name": "主轴总成",
                    "type": "rotating_equipment",
                    "function": "驱动刀具旋转进行切削加工",
                })
                break
        if not equip:
            equip.append({
                "id": "equipment_01",
                "name": self.scenario,
                "type": "industrial_process",
                "function": self.scenario,
            })
        return equip

    # ═══════════════════════════════════════════════════════════
    # Endpoint mapping — connect chain tokens to column names
    # ═══════════════════════════════════════════════════════════

    # ── Universal chain-endpoint→column-name resolver ──────────
    # Uses PHYSICAL_TOKEN_CLUSTERS from scorer + fuzzy token matching.
    # No hardcoded Chinese→English mapping — works for any process.
    # The resolver tries: (1) direct column name match (2) physical
    # token cluster match (3) character-level overlap for CJK text.

    def _map_endpoints_to_columns(self, text: str,
                                  col_names: set) -> Tuple[Optional[str], Optional[str]]:
        """Given causal chain text, map chain endpoints to actual column names.
        Uses a Chinese→English parameter mapping table for CNC/film/chemical
        terminology, falling back to substring matching against column names."""
        chain_from, chain_to = self._parse_endpoints(text)
        if not chain_from:
            return None, None

        # Step 1: Direct mapping via CN_PARAM_MAP
        from_col = self._resolve_cn_param(chain_from, col_names)
        to_col = self._resolve_cn_param(chain_to, col_names)

        # Step 2: If direct mapping failed, try token-based fuzzy match
        if not from_col:
            from_tokens = set(chain_from.replace("↑", "").replace("↓", "").split())
            from_col = self._fuzzy_match_tokens(from_tokens, col_names)
        if not to_col:
            to_tokens = set(chain_to.replace("↑", "").replace("↓", "").split())
            to_col = self._fuzzy_match_tokens(to_tokens, col_names)

        return (from_col or chain_from, to_col or chain_to)

    def _resolve_cn_param(self, token: str, col_names: set) -> Optional[str]:
        """Match a causal-chain endpoint token to an actual data column.

        Uses three strategies (tried in order):
        1. Direct substring match: token appears inside a column name
        2. Token overlap: shared word fragments between token and column
        3. Physical cluster match: token belongs to same measurement category
        """
        token_lower = token.lower().replace("↑", "").replace("↓", "").strip()
        token_chars = set(token_lower)
        best, best_score = None, 0.0

        for cn in col_names:
            cn_lower = cn.lower().replace("_", " ")
            cn_tokens = set(cn_lower.split())

            # Strategy 1: Direct substring
            if token_lower in cn_lower or cn_lower in token_lower:
                return cn

            # Strategy 2: Token overlap
            token_words = set(token_lower.split())
            overlap = len(token_words & cn_tokens)
            if overlap > 0:
                score = overlap * 0.8
                # Bonus: CJK character overlap (handles Chinese text)
                cn_chars = set(cn_lower)
                char_overlap = len(token_chars & cn_chars)
                score += char_overlap * 0.1
                if score > best_score:
                    best_score, best = score, cn

        if best and best_score > 0.3:
            return best

        # Strategy 3: Physical cluster match via external token clusters
        try:
            from .scorer import PHYSICAL_TOKEN_CLUSTERS
            for cluster_name, synonyms in PHYSICAL_TOKEN_CLUSTERS.items():
                if any(syn in token_lower for syn in synonyms):
                    for cn in col_names:
                        if any(syn in cn.lower().replace("_", " ") for syn in synonyms):
                            return cn
        except ImportError:
            pass

        return best if best_score > 0.2 else None

    @staticmethod
    def _fuzzy_match_tokens(tokens: set, col_names: set) -> Optional[str]:
        """Fuzzy match Chinese/English tokens against column names."""
        best, best_score = None, 0
        for cn in col_names:
            cn_tokens = set(re.split(r'[_\s]+', cn.lower()))
            cn_chars = set(cn.lower().replace("_", " "))
            score = len(tokens & cn_tokens) + len(
                set("".join(tokens)) & cn_chars) * 0.2
            if score > best_score:
                best_score, best = score, cn
        return best if best_score > 0 else None

    def _build_chunk_param_map(self) -> Dict[str, List[ScoredChunk]]:
        """Index chunks by the parameter names they discuss.
        Web search results use source.url instead of source.path — handle both."""
        pmap = {}
        for c in self.chunks:
            src_text = c.source.path or c.source.url or ""
            for tag in src_text.lower().replace("_", " ").split():
                pmap.setdefault(tag, []).append(c)
        return pmap

    # ═══════════════════════════════════════════════════════════
    # Match & extract helpers
    # ═══════════════════════════════════════════════════════════

    def _best_match(self, col_name: str) -> Optional[ScoredChunk]:
        """Find the best matching chunk for a column name using
        direct param tag match → token overlap → content keyword scan."""
        best, best_score = None, 0.0
        cn = col_name.lower()
        cn_tokens = set(re.split(r'[_\s]+', cn))

        for c in self.chunks:
            score = 0.0

            # Tier 1: direct parameter tag match (strongest signal)
            for tag in c.parameter_tags if hasattr(c, 'parameter_tags') else []:
                tag_l = tag.lower().replace("_", " ")
                if tag_l == cn or tag_l in cn or cn in tag_l:
                    score += 0.8
                else:
                    tag_tokens = set(tag_l.split())
                    overlap = len(cn_tokens & tag_tokens)
                    score += 0.2 * overlap

            # Tier 2: check source path for parameter hints
            src = (c.source.path or "").lower()
            if cn.replace("_", " ") in src or any(
                t in src for t in cn_tokens):
                score += 0.3

            # Tier 3: content keyword scan
            preview = (c.content_preview or "").lower()
            for token in cn_tokens:
                if token in preview:
                    score += 0.15

            score = min(score, 1.0)
            if score > best_score:
                best_score, best = score, c

        return best if best_score >= 0.2 else None

    @staticmethod
    def _extract_meaning(chunk: ScoredChunk) -> str:
        text = chunk.content_preview or ""
        for line in text.split("\n"):
            if "Physical" in line or "physical" in line:
                return line.split(":", 1)[-1].strip()
            if "Quantity" in line:
                return line.split(":", 1)[-1].strip()
        return text[:150]

    @staticmethod
    def _extract_law(chunk: ScoredChunk) -> Optional[str]:
        text = chunk.content_preview or ""
        for line in text.split("\n"):
            if "Governing" in line or "governing" in line or "ISO" in line:
                return line.strip()
        return None

    @staticmethod
    def _extract_mechanism(text: str) -> Optional[str]:
        for line in text.split("\n"):
            if "mechanism" in line.lower() or "Causal Chain" in line:
                return line.split(":", 1)[-1].strip()
            if "→" in line and len(line) > 20:
                return line.strip()
        return None

    @staticmethod
    def _parse_endpoints(text: str) -> Tuple[Optional[str], Optional[str]]:
        for line in text.split("\n"):
            if "→" in line:
                parts = [p.strip() for p in line.split("→")]
                if len(parts) >= 2:
                    return (parts[0].split()[-1] if parts[0].split() else None,
                            parts[-1].split()[-1] if parts[-1].split() else None)
        return None, None

    @staticmethod
    def _confidence(chunk: ScoredChunk) -> float:
        return {"CRITICAL": 0.95, "ACCEPTED": 0.80,
                "CONDITIONAL": 0.60}.get(
                    str(chunk.tier.value if hasattr(chunk.tier, 'value')
                        else chunk.tier), 0.50)

    @staticmethod
    def _guess_unit(col_name: str) -> str:
        lower = col_name.lower()
        if "temp" in lower: return "°C"
        if "pressure" in lower: return "bar"
        if "speed" in lower or "rpm" in lower: return "rpm"
        if "vibration" in lower: return "mm/s"
        if "force" in lower: return "N"
        if "flow" in lower: return "L/min"
        if "roughness" in lower: return "μm"
        if "deviation" in lower: return "mm"
        if "thickness" in lower: return "μm"
        if "rate" in lower: return "%"
        return ""

    def _is_quality(self, name: str) -> bool:
        return any(p in name.lower() for p in QUALITY_PATTERNS)

    def _is_control(self, name: str) -> bool:
        return any(p in name.lower() for p in CONTROL_PATTERNS)

    def _is_meta(self, name: str) -> bool:
        return any(p in name.lower() for p in META_PATTERNS)
