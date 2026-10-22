"""Ontology-first condition understanding.

Discovery order (house rule: ontology first, data second):
  1. --ontology explicit path
  2. <run_dir>/00_input/ontology.json then <run_dir>/01_ontology/ontology.json
     (artifacts of industrial-ontology-builder)
  3. scene match in <repo>/data/ontology_store/index.json (ontology asset store,
     built by industrial-ontology-builder / rag-knowledge-builder)
  4. none -> auto mode: every inferred field carries assigned_by:"auto"

Every understood column gets {label, unit, role, normal_range, target,
tolerance, stage, equipment, governing_law, physical_meaning, group} with an
`assigned_by` provenance of "ontology" | "user" | "auto". report_context wins
over ontology; ontology wins over heuristics. Relationship edges and
confounders feed the counterfactual constraints (physical mechanism,
uncontrolled confounders).
"""
from __future__ import annotations

import json
import os
import re

AUTO = "auto"
ONTOLOGY = "ontology"
USER = "user"

# ontology role values that mark a column as an inspection/quality signal
_TARGET_ROLES = {"target", "quality", "inspection", "response"}

_WS_RE = re.compile(r"[\s\u3000]+")


def _norm(name: str) -> str:
    """Normalization for ontology column matching only (report never renames):
    drop all whitespace (Excel multi-line headers like 压\n膜\n线), unify
    full-width parens, lower-case ASCII."""
    return (_WS_RE.sub("", str(name)).replace("（", "(").replace("）", ")")
            .lower())


def resolve_store_root(repo_root: str | None, store_dir: str | None = None) -> str | None:
    """Store root: explicit arg > ONTOLOGY_STORE_DIR env > <repo>/data/ontology_store."""
    if store_dir:
        return os.path.normpath(os.path.abspath(store_dir))
    env = os.environ.get("ONTOLOGY_STORE_DIR")
    if env:
        return os.path.normpath(os.path.abspath(env))
    if repo_root:
        return os.path.join(repo_root, "data", "ontology_store")
    return None


def _store_asset_candidates(store_root: str, scene_hint: str,
                            profile: str | None) -> list[str]:
    """Index-derived asset paths for a scene, profile-scoped, newest first.

    With a non-diagnosis `profile`, entries of that profile are preferred and
    default-profile (diagnosis) assets serve as fallback — an ontology built
    for another lens is still a valid condition understanding, and its
    provenance stays truthful in the asset itself.
    """
    try:
        with open(os.path.join(store_root, "index.json"), encoding="utf-8") as f:
            index = json.load(f)
    except Exception:
        return []
    entries = index.get("entries") if isinstance(index, dict) else None
    if not isinstance(entries, list):
        return []
    cands = [e for e in entries
             if isinstance(e, dict) and e.get("scene_key") == scene_hint
             and e.get("quality") != "deprecated"]
    if profile and profile != "diagnosis":
        own = [e for e in cands if (e.get("profile") or "diagnosis") == profile]
        cands = own or [e for e in cands if (e.get("profile") or "diagnosis") == "diagnosis"]
    elif profile == "diagnosis":
        cands = [e for e in cands if (e.get("profile") or "diagnosis") == "diagnosis"]
    cands.sort(key=lambda e: (-int(e.get("version") or 0), str(e.get("path") or "")))
    return [os.path.join(store_root, e["path"]) for e in cands if e.get("path")]


def _scan_asset_dirs(store_root: str, scene_hint: str, profile: str | None) -> list[str]:
    """Directory-scan fallback (index drift): `<scene>/<profile>/vN` namespaces
    first (when a non-default profile is requested), then legacy `<scene>/vN`."""
    scene_dir = os.path.join(store_root, scene_hint)
    if not os.path.isdir(scene_dir):
        return []
    ordered: list[str] = []
    namespaces: list[str] = []
    if profile and profile != "diagnosis":
        namespaces.append(os.path.join(scene_dir, profile))
    namespaces.append(scene_dir)
    for ns_dir in namespaces:
        if not os.path.isdir(ns_dir):
            continue
        for v in sorted((d for d in os.listdir(ns_dir) if d.startswith("v")), reverse=True):
            p = os.path.join(ns_dir, v, "ontology.json")
            if os.path.isfile(p):
                ordered.append(p)
    return ordered


def discover_ontology(run_dir: str | None, explicit: str | None,
                      scene_hint: str | None, repo_root: str | None,
                      *, profile: str | None = None,
                      store_dir: str | None = None) -> dict:
    """Return {path, source, ontology|None, reason}."""
    candidates = []
    if explicit and os.path.isfile(explicit):
        return _load(explicit, "explicit")
    if run_dir:
        candidates += [
            os.path.join(run_dir, "00_input", "ontology.json"),
            os.path.join(run_dir, "01_ontology", "ontology.json"),
        ]
    for cand in candidates:
        if os.path.isfile(cand):
            return _load(cand, "run_dir")
    store_root = resolve_store_root(repo_root, store_dir)
    if scene_hint and store_root:
        for path in _store_asset_candidates(store_root, scene_hint, profile):
            loaded = _load(path, "asset_store")
            if loaded["ontology"] is not None:
                return loaded
        for path in _scan_asset_dirs(store_root, scene_hint, profile):
            loaded = _load(path, "asset_store")
            if loaded["ontology"] is not None:
                return loaded
    return {"path": None, "source": None, "ontology": None,
            "reason": "no ontology artifact found (auto mode)"}


def _load(path: str, source: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return {"path": path, "source": source,
                    "ontology": json.load(f), "reason": None}
    except Exception as exc:
        return {"path": path, "source": source, "ontology": None,
                "reason": f"unreadable: {exc}"}


def _sig_maps(ontology: dict) -> tuple[dict, dict]:
    """Flatten signals.{process_parameters,inspection_signals,...} to
    column -> signal entry, plus group -> [columns]."""
    col_map: dict[str, dict] = {}
    groups: dict[str, list[str]] = {}
    signals = ontology.get("signals") or {}
    for group_name, entries in signals.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            col = entry.get("column")
            if not col:
                continue
            col_map[str(col)] = entry
            groups.setdefault(str(group_name), []).append(str(col))
    pg = ontology.get("parameter_groups") or {}
    if isinstance(pg, dict):
        for group_name, cols in pg.items():
            if isinstance(cols, list):
                groups.setdefault(str(group_name), []).extend(
                    str(c) for c in cols if str(c) not in groups.get(str(group_name), []))
    # normalized lookup tables: ontology authors often name signals with the
    # original Excel header (spaces / newlines / full-width parens) while the
    # tidy table uses cleaned names — match on the normalized form as fallback.
    norm_map = {_norm(k): v for k, v in col_map.items()}
    norm_groups = {g: {_norm(c) for c in cols} for g, cols in groups.items()}
    return col_map, groups, norm_map, norm_groups


def build_understanding(ontology: dict | None, columns: list[str],
                        context: dict) -> dict:
    """Per-column condition understanding + scene narrative + mechanism graph."""
    ontology = ontology or {}
    scene = ontology.get("scene") or {}
    col_map, groups, norm_map, norm_groups = _sig_maps(ontology)
    meta_units = (ontology.get("metadata") or {}).get("units") or {}
    ctx_specs = context.get("spec_limits") or {}
    ctx_roles_p = set(context.get("parameter_cols") or [])
    ctx_roles_i = set(context.get("inspection_cols") or [])

    columns_doc = {}
    for col in columns:
        sig = col_map.get(col) or norm_map.get(_norm(col)) or {}
        assigned = ONTOLOGY if sig else AUTO
        role = None
        if col in ctx_roles_i:
            role, assigned = "inspection", USER
        elif col in ctx_roles_p:
            role, assigned = "parameter", USER
        elif sig.get("role"):
            role = ("inspection" if str(sig.get("role")).lower() in _TARGET_ROLES
                    else "parameter")
        else:
            role = ("inspection" if any(h in col.lower() for h in
                    ("yield", "quality", "defect", "reject", "purity", "pct_good"))
                    else "parameter")
        spec = None
        if col in ctx_specs:
            spec = {**ctx_specs[col], "source": USER}
            assigned = USER if assigned == AUTO else assigned
        elif sig.get("normal_range") and isinstance(sig["normal_range"], list) \
                and len(sig["normal_range"]) == 2:
            spec = {"lsl": sig["normal_range"][0], "usl": sig["normal_range"][1],
                    "target": sig.get("target"), "source": ONTOLOGY}
        columns_doc[col] = {
            "assigned_by": assigned,
            "label": sig.get("name") or col,
            "unit": sig.get("unit") or meta_units.get(col),
            "role": role,
            "spec": spec,
            "normal_range": sig.get("normal_range"),
            # knowledge provenance of the signal itself: a dictionary-inferred
            # (auto_inferred) signal must never feed a Cpk spec downstream —
            # the analyzer's spec_for() guard reads this field (defense in
            # depth on top of prepare never writing typical_ranges to
            # normal_range). Legacy signals without the field keep working.
            "knowledge_source": sig.get("knowledge_source"),
            "stage": sig.get("stage_ref"),
            "equipment": sig.get("equipment_ref"),
            "governing_law": sig.get("governing_law"),
            "physical_meaning": sig.get("physical_meaning"),
            "group": next((g for g, cols in groups.items() if col in cols),
                          next((g for g, ns in norm_groups.items()
                                if _norm(col) in ns), None)),
        }

    relationships = [
        {"from": r.get("from"), "to": r.get("to"), "type": r.get("type"),
         "strength": r.get("strength"),
         "mechanism": r.get("mechanism"),
         "governing_equation": r.get("governing_equation")}
        for r in (ontology.get("relationships") or []) if isinstance(r, dict)
    ]
    confounders = [
        {"variable": c.get("variable"), "why": c.get("why"),
         "controlled": bool(c.get("controlled"))}
        for c in (ontology.get("confounders") or []) if isinstance(c, dict)
    ]
    return {
        "mode": ONTOLOGY if ontology else AUTO,
        "scene": {
            "name": scene.get("name"),
            "process_type": scene.get("process_type"),
            "production_goal": scene.get("production_goal"),
            "equipment": scene.get("equipment"),
            "stages": scene.get("stages"),
        } if scene else None,
        "columns": columns_doc,
        "relationships": relationships,
        "confounders": confounders,
    }


def mechanism_for(understanding: dict, a: str, b: str) -> dict:
    """Physical-mechanism check for a correlated pair.

    Returns {level: known|same_domain|unknown, mechanism, governing_equation}.
    "known"    — the ontology asserts a causal edge between the two columns.
    "same_domain" — both columns belong to one parameter group (same physical
    state), mechanism plausible but not asserted.
    "unknown"  — no ontological support; finding must carry [MECHANISM_UNKNOWN].
    Column names are matched on the normalized form (see _norm).
    """
    na, nb = _norm(a), _norm(b)
    for r in understanding.get("relationships") or []:
        pair = {_norm(r.get("from")), _norm(r.get("to"))}
        if {na, nb} == pair and None not in pair:
            return {"level": "known", "mechanism": r.get("mechanism"),
                    "governing_equation": r.get("governing_equation"),
                    "direction": f"{r.get('from')} -> {r.get('to')}"}
    groups = {}
    for col, doc in (understanding.get("columns") or {}).items():
        g = doc.get("group")
        if g:
            groups.setdefault(g, set()).add(_norm(col))
    for g, cols in groups.items():
        if na in cols and nb in cols:
            return {"level": "same_domain", "mechanism": None,
                    "governing_equation": None, "group": g}
    return {"level": "unknown", "mechanism": None, "governing_equation": None}


def systematic_sample(n_rows: int, max_rows: int = 100_000) -> int:
    """Deterministic stride to cap rows (>100K systematic sampling)."""
    if n_rows <= max_rows:
        return 1
    return int((n_rows + max_rows - 1) // max_rows)
