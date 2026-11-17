"""report_design — single source for the IDD report design system.

Every HTML renderer in this repo (stability / advisory / DOE / diagnostic)
must load its stylesheet from HERE. Do not copy the CSS into a skill.

Because generated reports are single-file (双击即可打开、打印归档), the CSS is
inlined at render time via `inline_style()`. The file on disk stays the single
source of truth; a drift test compares rendered reports against it.
"""
from __future__ import annotations

from pathlib import Path

DESIGN_DIR = Path(__file__).resolve().parent
CSS_PATH = DESIGN_DIR / "report.css"


def css_text() -> str:
    """Return the shared stylesheet (raises if the design system is missing)."""
    return CSS_PATH.read_text(encoding="utf-8")


def inline_style() -> str:
    """`<style>…</style>` block for single-file reports."""
    return f"<style>{css_text()}</style>"


def css_sha256() -> str:
    import hashlib

    return hashlib.sha256(CSS_PATH.read_bytes()).hexdigest()
