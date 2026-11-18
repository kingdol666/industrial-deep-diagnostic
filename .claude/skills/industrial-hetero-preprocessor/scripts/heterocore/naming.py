"""naming.py — HX-* column naming contract (frozen interface I3).

Rules (plan v1.1 D12/D13):
- ASCII only: ^HX-(PROF|MAP|IMG|TXT|IDX)-[A-Z0-9]+-[A-Z0-9-]+$, max 64 chars.
- Forbidden tokens anywhere in a *file* name we emit: merged/merge/align/
  combined/_full/joined (E-1 `_looks_premerged` trap) and `_2` (E-1 dedup marker).
- Chinese/bilingual labels live in column_contract.json (tag_cn/tag_en), never
  inside machine identifiers.
- slug = [A-Za-z0-9] of the source stem, uppercased, truncated to 20; collisions
  disambiguated with `-<path_sha6>` (never `_2`).
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

SHAPE_CODES = {
    "profile": "PROF",
    "map": "MAP",
    "image_stream": "IMG",
    "text": "TXT",
    "index": "IDX",
}

COLUMN_RE = re.compile(r"^HX-(PROF|MAP|IMG|TXT|IDX)-[A-Z0-9]{1,32}-[A-Z0-9][A-Z0-9-]{0,61}$")
MAX_LEN = 64
FORBIDDEN_FILE_TOKENS = ("merged", "merge", "align", "combined", "_full", "joined")
GEOMETRY_FEATURES = ("EDGE", "ZONE", "CENTROID", "POSMAX", "ARGDEV", "SHIFT", "ASYM", "POS-DEV", "HOTAREA", "COLDAREA")


def slugify(stem: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", stem).upper()[:20] or "SRC"


def path_sha6(path: Path) -> str:
    return hashlib.sha256(str(path).lower().encode("utf-8")).hexdigest()[:6]


def unique_slug(stem: str, path: Path, taken: dict[str, str]) -> tuple[str, str]:
    """Return (slug, sha6); on slug collision append the path_sha6 WITHOUT a
    separator (COLUMN_RE forbids hyphens inside the slug segment)."""
    slug = slugify(stem)
    sha6 = path_sha6(path)
    if slug in taken and taken[slug] != sha6:
        slug = f"{slug[:14]}{sha6}"
    taken[slug] = sha6
    return slug, sha6


def feature_column(shape: str, slug: str, feature: str, arg: str | None = None) -> str:
    code = SHAPE_CODES.get(shape, shape.upper())
    name = f"HX-{code}-{slug}-{feature}"
    if arg:
        name = f"{name}-{arg}"
    return name.upper()[:MAX_LEN]


def validate_column_name(name: str) -> bool:
    return bool(COLUMN_RE.match(name)) and len(name) <= MAX_LEN


def is_geometry_feature(column: str) -> bool:
    """Geometry-interpreted features get physical_meaning_confidence=INFERRED;
    pure statistics of a named quantity are KNOWN (plan D7 rule)."""
    return any(tok in column for tok in GEOMETRY_FEATURES)


def check_file_name(name: str) -> list[str]:
    """Forbidden-token check for files WE emit (plan D13)."""
    low = name.lower()
    return [t for t in FORBIDDEN_FILE_TOKENS if t in low] + (["_2-suffix"] if low.endswith("_2") or "_2." in low else [])
