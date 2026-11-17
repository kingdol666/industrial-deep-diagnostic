"""discover.py — raw-path resolution chain + source discovery (frozen I1).

Resolution order (plan v1.1 blocker B1):
  --raw-path  >  run_config.raw_data_path  >  input_manifest.raw_data_path
  >  preprocessing_report.json.input_path
A missing raw path is `raw_path_unresolved` (exit 4) — NEVER silently treated
as "no hetero sources": a silent no-op is exactly the image/text loss this
skill exists to fix.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
TABLE_EXTS = {".csv", ".tsv", ".txt", ".dat"}
TEXT_EXTS = {".md", ".markdown", ".txt", ".log"}
SKIP_DIR_NAMES = {"__pycache__", "node_modules", ".git"}
# our own stage dir if someone points --raw-path at a run dir
OWN_OUTPUT_DIR_NAMES = {"07_hetero", "00_input", "01_ontology", "02_processed", "03_figures", "04_diagnostics", "05_review", "06_scripts"}


@dataclass
class SourceSpec:
    source_id: str
    path: Path
    slug: str
    path_sha6: str
    kind: str                 # "csv" | "image_dir" | "image_index" | "text" | "table"
    shape_hint: str | None = None
    meta: dict = field(default_factory=dict)


def resolve_raw_path(raw_arg: str | None, run_dir: Path | None) -> tuple[Path | None, str | None]:
    """Return (path, how_resolved) or (None, None)."""
    if raw_arg:
        p = Path(raw_arg)
        return (p, "cli") if p.exists() else (None, None)
    if not run_dir:
        return None, None
    for rel, key in (("00_input/run_config.json", "raw_data_path"),
                     ("00_input/input_manifest.json", "raw_data_path"),
                     ("00_input/preprocessing_report.json", "input_path")):
        f = run_dir / rel
        if not f.exists():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        val = data.get(key)
        if val and Path(val).exists():
            return Path(val), f"{rel}:{key}"
    return None, None


def discover_sources(raw_path: Path, recursive: bool = False) -> list[Path]:
    """Top-level scan by default (matches E-1's discovery); recursive opt-in.
    Skips dot-dirs, __pycache__, node_modules and any run-dir stage dir found
    under the root (so pointing --raw-path at a run dir never re-ingests our
    own outputs)."""
    if raw_path.is_file():
        return [raw_path]
    out: list[Path] = []
    it = raw_path.rglob("*") if recursive else raw_path.iterdir()
    for p in it:
        if not p.is_file():
            continue
        rel = p.relative_to(raw_path)
        if any(part.startswith(".") or part in SKIP_DIR_NAMES for part in rel.parts[:-1]):
            continue
        if recursive and any(part in OWN_OUTPUT_DIR_NAMES for part in rel.parts[:-1]):
            continue
        if p.name.startswith("."):
            continue
        out.append(p)
    return sorted(out, key=lambda p: p.name.lower())


def quick_kind(p: Path) -> str:
    ext = p.suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in TABLE_EXTS:
        return "csv"
    if ext in TEXT_EXTS:
        return "text"
    return "other"


def probe_csv_text_column(path: Path, max_rows: int = 50) -> list[tuple[str, float]]:
    """Cheap scan: column name -> share of long free-text cells (heuristic for
    notes columns). Returns [(col_name, text_share)] sorted desc."""
    import csv

    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
            rows = _read_rows(f, max_rows)
    except Exception:
        return []
    if not rows:
        return []
    header = rows[0]
    scores: list[tuple[str, float]] = []
    n = len(rows) - 1
    for ci, name in enumerate(header or []):
        cells = [r[ci] for r in rows[1:] if ci < len(r)]
        if not cells:
            continue
        long_cells = sum(1 for c in cells if len(str(c)) >= 12 and not _looks_numeric(c))
        scores.append((name, long_cells / max(len(cells), 1)))
    return sorted(scores, key=lambda t: -t[1])


def _looks_numeric(cell: str) -> bool:
    try:
        float(str(cell).replace(",", ""))
        return True
    except ValueError:
        return False


def _read_rows(f, max_rows: int):
    import csv

    return list(csv.reader(f))[:max_rows]
