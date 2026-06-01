"""
Persistent storage layer — SQLite for run metadata + JSON files for raw results.
"""

import sqlite3, json, os, time, uuid
from pathlib import Path
from typing import List, Dict, Optional
from contextlib import contextmanager


class StorageManager:
    """Manages persistence for retrieval runs, scoring results, and ontologies."""

    def __init__(self, db_path: str, results_dir: str):
        self.db_path = Path(db_path)
        self.results_dir = Path(results_dir)
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        self.results_dir.mkdir(parents=True, exist_ok=True)

        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS retrieval_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    scenario TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    target_columns TEXT NOT NULL,
                    parameter_columns TEXT NOT NULL,
                    group_columns TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    retrieval_result_path TEXT,
                    scoring_result_path TEXT,
                    ontology_path TEXT,
                    num_chunks_retrieved INTEGER DEFAULT 0,
                    num_chunks_scored INTEGER DEFAULT 0,
                    num_chunks_injected INTEGER DEFAULT 0,
                    errors TEXT DEFAULT '[]'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_sources (
                    source_path TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    indexed_at TEXT NOT NULL,
                    num_chunks INTEGER NOT NULL,
                    last_verified TEXT
                )
            """)
            conn.commit()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ─── Run CRUD ──────────────────────────────────────────────

    def create_run(self, scenario: str, mode: str,
                   target_cols: List[str], param_cols: List[str],
                   group_cols: List[str] = None) -> str:
        """Create a new retrieval run and return its ID."""
        run_id = f"run_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        with self._conn() as conn:
            conn.execute(
                """INSERT INTO retrieval_runs
                   (run_id, created_at, scenario, mode, target_columns,
                    parameter_columns, group_columns, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
                (run_id, now, scenario, mode,
                 json.dumps(target_cols), json.dumps(param_cols),
                 json.dumps(group_cols or []))
            )
            conn.commit()
        return run_id

    def get_run(self, run_id: str) -> Optional[Dict]:
        """Get run metadata by ID."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM retrieval_runs WHERE run_id = ?",
                (run_id,)
            ).fetchone()
        if row:
            d = dict(row)
            d["target_columns"] = json.loads(d["target_columns"])
            d["parameter_columns"] = json.loads(d["parameter_columns"])
            d["group_columns"] = json.loads(d["group_columns"])
            d["errors"] = json.loads(d.get("errors", "[]"))
            return d
        return None

    def list_runs(self, limit: int = 20) -> List[Dict]:
        """List recent runs."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT run_id, created_at, scenario, status FROM retrieval_runs "
                "ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def update_run_status(self, run_id: str, status: str, **kwargs):
        """Update run status and optional file paths."""
        fields = ["status = ?"]
        values = [status]
        for key in ["retrieval_result_path", "scoring_result_path", "ontology_path",
                     "num_chunks_retrieved", "num_chunks_scored", "num_chunks_injected"]:
            if key in kwargs:
                fields.append(f"{key} = ?")
                values.append(kwargs[key])
        values.append(run_id)

        with self._conn() as conn:
            conn.execute(
                f"UPDATE retrieval_runs SET {', '.join(fields)} WHERE run_id = ?",
                values
            )
            conn.commit()

    def add_error(self, run_id: str, error: str):
        """Append an error to a run."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT errors FROM retrieval_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row:
                errors = json.loads(row["errors"] or "[]")
                errors.append(error)
                conn.execute(
                    "UPDATE retrieval_runs SET errors = ? WHERE run_id = ?",
                    (json.dumps(errors), run_id)
                )
                conn.commit()

    # ─── File-based result persistence ─────────────────────────

    def save_result(self, run_id: str, result_type: str, data: Dict) -> str:
        """Save a retrieval/scoring/ontology result as JSON file. Returns path."""
        run_dir = self.results_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        fpath = run_dir / f"{result_type}.json"
        fpath.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str),
                         encoding='utf-8')
        return str(fpath)

    def load_result(self, run_id: str, result_type: str) -> Optional[Dict]:
        """Load a previously saved result."""
        fpath = self.results_dir / run_id / f"{result_type}.json"
        if fpath.exists():
            return json.loads(fpath.read_text(encoding='utf-8'))
        return None

    # ─── Knowledge source tracking ─────────────────────────────

    def mark_source_indexed(self, source_path: str, source_type: str, num_chunks: int):
        """Record that a source has been indexed."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO knowledge_sources
                   (source_path, source_type, indexed_at, num_chunks, last_verified)
                   VALUES (?, ?, ?, ?, ?)""",
                (source_path, source_type, now, num_chunks, now)
            )
            conn.commit()

    def get_indexed_sources(self) -> List[Dict]:
        """List all indexed knowledge sources."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM knowledge_sources ORDER BY indexed_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    # ─── Maintenance ───────────────────────────────────────────

    def cleanup_old_runs(self, days: int = 90):
        """Delete runs older than N days."""
        if days <= 0:
            return
        cutoff = time.time() - days * 86400
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT run_id FROM retrieval_runs WHERE "
                "strftime('%%s', created_at) < ?", (str(cutoff),)
            ).fetchall()
            for row in rows:
                run_dir = self.results_dir / row["run_id"]
                if run_dir.exists():
                    import shutil
                    shutil.rmtree(run_dir)
                conn.execute("DELETE FROM retrieval_runs WHERE run_id = ?",
                            (row["run_id"],))
            conn.commit()

    def get_stats(self) -> Dict:
        """Get storage statistics."""
        with self._conn() as conn:
            total_runs = conn.execute(
                "SELECT COUNT(*) FROM retrieval_runs"
            ).fetchone()[0]
            total_sources = conn.execute(
                "SELECT COUNT(*) FROM knowledge_sources"
            ).fetchone()[0]
        total_chunks = sum(
            json.loads(str(p)).get("total_chunks_retrieved", 0) or 0
            for p in self.results_dir.rglob("retrieval_result.json") if p.is_file()
        ) or 0
        return {
            "total_runs": total_runs,
            "total_indexed_sources": total_sources,
            "total_persisted_chunks": total_chunks,
            "results_disk_usage_mb": self._disk_usage(),
        }

    def _disk_usage(self) -> float:
        total = 0
        for f in self.results_dir.rglob("*.json"):
            total += f.stat().st_size
        return round(total / (1024 * 1024), 2)
