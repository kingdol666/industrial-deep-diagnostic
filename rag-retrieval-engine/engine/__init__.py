"""
RAG Retrieval Engine — Core engine modules.

Architecture:
  models.py    → Pydantic request/response schemas
  storage.py   → SQLite persistence for retrieval runs
  retriever.py → Local (ChromaDB) + web (httpx) retrieval
  scorer.py    → 5-dimension relevance scoring + quality gates
  injector.py  → Schema-driven knowledge → ontology draft injection
"""

__version__ = "1.0.0"
