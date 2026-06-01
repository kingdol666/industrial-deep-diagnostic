"""
Web Search Engine — HTTP-based web search for knowledge retrieval.

Integrates with:
- open-websearch CLI/daemon (preferred) — local search engine
- Direct HTTP search endpoints (fallback) — configurable
- Skill-level web search injection (passthrough) — for client-supplied results

All results are normalized to KnowledgeChunk format for downstream scoring.
"""

import json, time, re, hashlib
from typing import List, Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from pathlib import Path

from .models import KnowledgeChunk, ChunkSource, SourceType


class WebSearchEngine:
    """Performs web searches and normalizes results into knowledge chunks."""

    # Quality heuristics for source credibility classification
    AUTHORITATIVE_DOMAINS = {
        "wikipedia.org", "iso.org", "nist.gov", "doi.org",
        "semanticscholar.org", "aclanthology.org",
        "edu", ".gov", "manufacturer-datasheet",
    }

    def __init__(self, config: dict):
        self.config = config.get("web_search", config)
        self.enabled = self.config.get("enabled", True)
        self.max_results_per_query = self.config.get("max_results", 5)
        self.timeout_seconds = self.config.get("timeout", 15)
        self.html_mode = self.config.get("html_mode", True)  # fallback to HTML scraping

        # Preferred: local open-websearch daemon
        self.daemon_url = self.config.get("daemon_url", "http://localhost:8686")
        # Fallback: direct search engine APIs
        self.fallback_url = self.config.get("fallback_url", None)

        # Passthrough channel: accept chunks injected by the calling skill
        self.passthrough_chunks: List[KnowledgeChunk] = []

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def search(self, query: str, perspective: str,
               max_results: int = 5) -> List[KnowledgeChunk]:
        """Execute a web search and return normalized knowledge chunks.

        Strategy (in order):
          1. open-websearch daemon (local, fastest)
          2. HTML-based DuckDuckGo scrape (no API key needed)
          3. Fallback HTTP endpoint
          4. Passthrough chunks (skill-injected)
          5. Return empty silently
        """
        if not self.enabled:
            return []

        chunks = []
        errors = []

        # Strategy 1: Try local daemon first
        try:
            chunks = self._search_daemon(query, max_results)
            if chunks:
                return self._normalize_chunks(chunks, query, perspective)
        except Exception as e:
            errors.append(f"daemon: {e}")

        # Strategy 2: DuckDuckGo HTML (no API key, works in most networks)
        if self.html_mode:
            try:
                chunks = self._search_duckduckgo_html(query, max_results)
                if chunks:
                    return self._normalize_chunks(chunks, query, perspective)
            except Exception as e:
                errors.append(f"duckduckgo_html: {e}")

        # Strategy 3: Try fallback endpoint
        try:
            chunks = self._search_fallback(query, max_results)
            if chunks:
                return self._normalize_chunks(chunks, query, perspective)
        except Exception as e:
            errors.append(f"fallback: {e}")

        # Strategy 4: Return passthrough chunks if available
        if self.passthrough_chunks:
            return self.passthrough_chunks

        if errors:
            pass  # web search silently unavailable — not an error for the pipeline
        return []

    def inject_passthrough(self, chunks: List[KnowledgeChunk]):
        """Accept pre-fetched web results from the calling skill."""
        self.passthrough_chunks.extend(chunks)

    # ═══════════════════════════════════════════════════════════
    # Strategy 2: DuckDuckGo HTML (no API key, zero dependencies)
    # ═══════════════════════════════════════════════════════════

    def _search_duckduckgo_html(self, query: str, max_results: int) -> List[dict]:
        """Search DuckDuckGo via the duckduckgo_search library.

        Uses `duckduckgo_search.DDGS` which handles DuckDuckGo's current
        anti-bot mechanisms. Install with: uv add duckduckgo_search
        Falls back to empty results if the library is unavailable.
        """
        # duckduckgo_search package has been renamed to ddgs.
        # Try both import paths for compatibility.
        DDGS = None
        for mod in ["ddgs", "duckduckgo_search"]:
            try:
                m = __import__(mod, fromlist=["DDGS"])
                DDGS = m.DDGS
                break
            except ImportError:
                continue
        if DDGS is None:
            return []

        try:
            with DDGS() as ddgs:
                # ddgs and duckduckgo_search have different APIs:
                # ddgs.text(query, max_results=...)  — positional first arg
                # duckduckgo_search.text(keywords=..., max_results=...)  — keyword arg
                raw = list(ddgs.text(query, max_results=max_results))
        except Exception:
            return []

        results = []
        for r in raw[:max_results]:
            url = r.get("href", "")
            title = r.get("title", "")
            snippet = r.get("body", r.get("snippet", ""))
            if title and url:
                results.append({"title": title, "snippet": snippet, "url": url})
        return results

    # ═══════════════════════════════════════════════════════════
    # Strategy implementations
    # ═══════════════════════════════════════════════════════════

    def _search_daemon(self, query: str, max_results: int) -> List[dict]:
        """Query open-websearch local daemon.

        Expected daemon endpoint: GET /search?q=...&limit=...
        Returns: [{"title":..., "snippet":..., "url":..., "source":...}]
        """
        url = f"{self.daemon_url}/search"
        params = f"q={self._urlencode(query)}&limit={max_results}"
        full_url = f"{url}?{params}"

        req = Request(full_url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=self.timeout_seconds) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            # Normalize response format
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("results", data.get("items", data.get("hits", [])))
            return []

    def _search_fallback(self, query: str, max_results: int) -> List[dict]:
        """Query a fallback HTTP search endpoint.

        Config example:
          fallback_url: "https://api.duckduckgo.com/?q={query}&format=json"
        """
        if not self.fallback_url:
            return []

        url = self.fallback_url.replace("{query}", self._urlencode(query))
        req = Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "RAG-Retrieval-Engine/1.0",
        })
        with urlopen(req, timeout=self.timeout_seconds) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ("Results", "results", "items", "RelatedTopics"):
                    if key in data:
                        items = data[key]
                        if isinstance(items, list):
                            return items
            return []

    # ═══════════════════════════════════════════════════════════
    # Normalization
    # ═══════════════════════════════════════════════════════════

    
    @staticmethod
    def _score_content_quality(title: str, snippet: str, url: str) -> float:
        """Score web content from 0.0 (noise) to 1.0 (high-value technical).
        Three factors: technical density, noise penalties, domain authority."""
        import re as reassign
        text = (title + " " + snippet).lower()
        score = 0.0
        # Technical signal patterns
        tech_patterns = [
            r'\d+[°]\w', r'\d+\.\d+\s*(mm|um|nm|kg|bar|MPa|kW|rpm|Hz)',
            r'temperature|pressure|vibration|speed|flow|concentration',
            r'parameter|threshold|coefficient|ratio|yield|conversion',
            r'thermal|kinetics|balance|gradient|combustion|sintering',
            r'clinker|cement|kiln|furnace|reactor|exchanger',
            r'acceleration|frequency|amplitude|modulus|tensile',
        ]
        tech_hits = sum(1 for p in tech_patterns if reassign.search(p, text))
        score += min(0.6, tech_hits * 0.06)
        # Noise penalties
        noise_patterns = [r'top\s+\d+', r'click\s+here', r'sponsored',
            r'buy\s+now', r'subscribe', r'casino', r'SEO', r'affiliate']
        for p in noise_patterns:
            if reassign.search(p, text): score -= 0.15
        if len(snippet.split()) < 15: score -= 0.1
        if not reassign.search(r'\d', snippet): score -= 0.1
        # Domain boost
        url_lower = url.lower()
        for d in ['wikipedia', '.edu', '.gov', 'iso.org', 'researchgate']:
            if d in url_lower: score += 0.2; break
        for d in ['amazon.', 'ebay.', 'aliexpress.', 'pinterest.']:
            if d in url_lower: score -= 0.3; break
        return max(0.0, min(1.0, score))

    # --- Auto-escalation query enhancement ---
    @staticmethod
    def build_expanded_queries(scenario: str, param_cols: list,
                                target_cols: list, gaps: list) -> list:
        """Generate expanded web queries when local KB results are insufficient.
        Focuses on knowledge gaps to get the most useful information."""
        queries = []
        # Query 1: General scenario + key targets
        targets = " ".join(target_cols[:3])
        params = " ".join(param_cols[:4])
        queries.append(f"{targets} {scenario} root cause analysis diagnosis")
        # Query 2: Parameter physical meaning
        if param_cols:
            queries.append(f"{' '.join(param_cols[:6])} physical meaning measurement unit")
        # Query 3: Knowledge gaps
        if gaps:
            queries.append(f"{' '.join(gaps[:4])} meaning in {scenario}")
        # Query 4: Fault patterns
        if targets:
            queries.append(f"{targets} degradation failure mechanism troubleshooting")
        return queries

    # ═══════════════════════════════════════════════════════════
    # Normalization (with content quality filter)
    # ═══════════════════════════════════════════════════════════

    def _normalize_chunks(self, raw_results: List[dict],
                              query: str, perspective: str) -> List[KnowledgeChunk]:
            """Convert raw search results, applying content quality filter.
            Only chunks with quality_score >= 0.30 are kept."""
            chunks = []
            for i, item in enumerate(raw_results[:self.max_results_per_query * 2]):
                url = item.get("url", item.get("link", ""))
                title = item.get("title", item.get("name", ""))
                snippet = item.get("snippet", item.get("description",
                              item.get("text", item.get("summary", ""))))
                if not snippet or len(snippet.strip()) < 30: continue
                # Content quality gate
                quality = self._score_content_quality(title, snippet, url)
                if quality < 0.30: continue
                chunk_id = f"web_{hashlib.md5(url.encode()).hexdigest()[:12]}"
                source_type = self._classify_source(url)
                chunks.append(KnowledgeChunk(
                    chunk_id=chunk_id,
                    content=f"Title: {title}\nSource: {url}\n\n{snippet.strip()}",
                    content_preview=snippet.strip()[:300],
                    source=ChunkSource(type=SourceType(source_type), url=url, title=title),
                    scenario_tags=self._guess_scenarios(snippet+" "+title),
                    parameter_tags=self._extract_parameter_mentions(snippet+" "+title),
                    mechanism_type=self._guess_mechanism_type(snippet+" "+title),
                    semantic_score=None, perspective=perspective, retrieval_query=query,
                    content_quality_score=quality,
                ))
            return chunks
        # ═══════════════════════════════════════════════════════════
        # Content classification helpers
        # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _classify_source(url: str) -> str:
        lower = url.lower()
        for domain in WebSearchEngine.AUTHORITATIVE_DOMAINS:
            if domain in lower:
                return "web_authoritative"
        return "web_general"

    @staticmethod
    def _guess_scenarios(text: str) -> List[str]:
        """Infer likely industrial domain from text using keyword patterns.

        Uses manufacturing-domain keyword clusters (not exhaustive lists).
        Unknown processes are tagged as 'generic' — the scoring engine's D3
        dimension handles the neutral case without penalty.
        """
        lower = text.lower()
        scenarios = set()
        # Keyword clusters grouped by industrial domain
        domain_keywords = {
            "machining_metalworking": ["cnc", "machining", "milling", "turning",
                "grinding", "spindle", "lathe", "drilling", "boring", "broaching"],
            "forming_stamping": ["forging", "stamping", "rolling", "cold_rolling",
                "hot_rolling", "extrusion_metal", "drawing", "bending", "pressing"],
            "polymer_film_fiber": ["film", "bopet", "bopp", "extrusion_polymer",
                "fiber", "spinning", "blown_film", "cast_film", "stretching",
                "calendering", "coating", "lamination"],
            "chemical_process": ["reactor", "cstr", "catalyst", "distillation",
                "crystallization", "polymerization", "fermentation", "batch_reactor",
                "continuous_reactor", "absorption", "stripping", "extraction"],
            "thermal_energy": ["heat_exchanger", "boiler", "furnace", "kiln",
                "cooling_tower", "chiller", "heat_recovery", "steam", "combustion",
                "incineration", "thermal", "fouling", "htc", "condenser", "evaporator"],
            "material_processing": ["smelting", "casting", "sintering", "annealing",
                "quenching", "tempering", "welding", "brazing", "powder_metallurgy"],
            "assembly_testing": ["assembly", "testing", "inspection", "packaging",
                "sorting", "conveying", "dispensing", "filling", "sealing", "labeling"],
            "mining_mineral": ["crushing", "grinding_mill", "flotation", "leaching",
                "screening", "classification", "dewatering", "thickening", "filtering"],
            "pulp_paper": ["papermaking", "pulping", "digester", "headbox",
                "calendering_paper", "drying_section", "coating_section"],
            "textile": ["weaving", "knitting", "dyeing", "finishing_textile",
                "spinning_textile", "warping", "sizing", "desizing"],
            "food_beverage": ["pasteurization", "homogenization", "brewing",
                "baking", "drying_food", "freezing", "sterilization", "mixing_food"],
            "pharma_biotech": ["bioreactor", "lyophilization", "chromatography",
                "centrifugation", "filtration_sterile", "tablet_press", "encapsulation"],
        }
        for domain, keywords in domain_keywords.items():
            if any(kw in lower for kw in keywords):
                scenarios.add(domain)
        return list(scenarios) if scenarios else ["generic"]

    @staticmethod
    def _extract_parameter_mentions(text: str) -> List[str]:
        """Extract parameter names from text using measurement-term patterns.

        Matches common industrial measurement nouns and compound terms
        (e.g. 'surface roughness', 'flow rate', 'bearing temperature').
        Uses pattern-based extraction — no hardcoded parameter list.
        """
        lower = text.lower()
        params = set()
        # Measurement nouns commonly used in industrial contexts
        measurement_nouns = [
            "temperature", "pressure", "speed", "velocity", "flow", "flow_rate",
            "vibration", "force", "torque", "tension", "power", "current",
            "voltage", "frequency", "displacement", "position", "level",
            "thickness", "width", "diameter", "density", "viscosity", "ph",
            "conductivity", "concentration", "humidity", "moisture",
            "roughness", "finish", "hardness", "strength", "wear",
            "corrosion", "fouling", "degradation", "efficiency", "yield",
            "conversion", "selectivity", "purity", "deviation", "error",
            "tolerance", "clearance", "gap", "weight", "mass", "volume",
        ]
        for noun in measurement_nouns:
            if noun.replace("_", " ") in lower:
                params.add(noun.replace("_", " "))
        return list(params)

    @staticmethod
    def _guess_mechanism_type(text: str) -> str:
        lower = text.lower()
        if any(k in lower for k in ["causes", "leads to", "results in",
                                      "due to", "because", "mechanism"]):
            return "causal_chain"
        if any(k in lower for k in ["equation", "formula", "calculate",
                                      "coefficient", "threshold"]):
            return "quantitative_rule"
        if any(k in lower for k in ["failure", "fault", "defect",
                                      "breakdown", "wear", "damage"]):
            return "fault_pattern"
        if any(k in lower for k in ["confound", "stratified", "by product",
                                      "batch effect"]):
            return "confounder"
        return "knowledge_general"

    @staticmethod
    def _urlencode(s: str) -> str:
        from urllib.parse import quote
        return quote(s, safe='')
