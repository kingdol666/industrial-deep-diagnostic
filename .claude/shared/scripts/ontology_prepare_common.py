#!/usr/bin/env python
"""ontology_prepare_common.py — watch-family (stability / sentinel) ontology prepare core.

Profile-parametrized core shared by the stability-report and sentinel ontology
stages. Only genuinely profile-invariant logic lives here (single copy in
`.claude/shared/`, which is NOT mirrored): the watch context fingerprint
(mirrored 1:1 by `computeWatchContextFingerprint()` in ontology_store.mjs),
the store client (single write path via ontology_store.mjs), the
reuse/extend/build action state machine, the brief-required gate, strict JSON
writers, and the shipped physics-dictionary matcher. Per-skill adapters
(prior-ontology assembly, brief sections, context parsing, CLI surface) stay
inside each skill.

Discipline inherited from the DOE v1.1 ontology stage (do NOT weaken):
  * declarations only — a prior build never claims measured behaviour
    (`observed_data_behavior = "NOT_APPLICABLE"`, `behavior_match = "UNVERIFIED"`);
  * `rag_used` / `web_used` are reported from the ontology provenance, never
    invented — the deterministic paths always report False;
  * no wall clock inside the ontology body (stable content → stable store
    dedupe); timestamps live in brief/coverage artifacts only;
  * dictionary (`parameter_to_physics.json`) contributes unit / role /
    physical meaning / governing law ONLY — its `typical_ranges` are reference
    bands, never `normal_range`, never a Cpk spec (plan v2 principle 2).
"""

import datetime
import hashlib
import json
import math
import os
import re
import subprocess
import time
from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parent
REPO_ROOT = SHARED_DIR.parents[2]              # …/.claude/shared/scripts → repo root
STORE_JS = SHARED_DIR / "ontology_store.mjs"
ONTOLOGY_SCHEMA = (REPO_ROOT / ".claude" / "skills" / "industrial-ontology-builder"
                   / "schemas" / "ontology_schema.json")
PHYSICS_DICT = (REPO_ROOT / ".claude" / "skills" / "industrial-ontology-builder"
                / "resources" / "parameter_to_physics.json")
DEFAULT_STORE_DIR = REPO_ROOT / "data" / "ontology_store"
ONTOLOGY_MIN_BYTES = 1024                      # CP-2 floor (same constant as the store)

WATCH_CONTEXT_FP_VERSION = "watch-context-v1"
CONTEXT_FP_ABS_CUTOFF = 1e15
DEFAULT_PROFILE = "diagnosis"
ACTION_REUSED, ACTION_EXTENDED, ACTION_BUILT, ACTION_SKIPPED = "reused", "extended", "built", "skipped"
VALID_MODES = ("off", "auto", "full", "reuse", "extend")

GATE_BRIEF_REQUIRED = "ONTOLOGY_BRIEF_REQUIRED"


# ---------------------------------------------------------------- path utils

def contained(candidate, extra_root=None):
    cand = os.path.normpath(os.path.abspath(str(candidate)))
    if any(seg == ".." for seg in cand.replace("/", os.sep).split(os.sep)):
        raise ValueError(f"traversal segment rejected in path: {candidate}")
    if extra_root is not None:
        root = os.path.normpath(os.path.abspath(str(extra_root)))
        if not (cand == root or cand.startswith(root + os.sep)):
            raise ValueError(f"path outside allowed root: {candidate}")
    return Path(cand)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json_strict(path, payload):
    out = contained(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
                   encoding="utf-8")
    return out


def sha256_text(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ───────────────── watch context 指纹（与 ontology_store.mjs 同源） ────────

def canonical_number_token(value):
    """Canonical decimal token — must stay identical to canonicalNumberToken()
    in ontology_store.mjs ('' for absent, never 'null')."""
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return str(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return str(value)
    if abs(number) >= CONTEXT_FP_ABS_CUTOFF:
        # JS String(n) only switches to exponent notation at ~1e21; Python repr
        # switches at 1e15 — expand the in-between window so both sides agree.
        if abs(number) >= 1e21:
            return repr(number)
        if float(number).is_integer():
            return f"{number:.0f}"
        return format(number, "f").rstrip("0").rstrip(".")
    text = f"{number:.9f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("", "-0"):
        text = "0"
    return text


def compute_watch_context_fp(decl):
    """Stable fingerprint of a watch declaration contract. Sorted lines, no clock.

    `decl` shape: {"columns": [{"col","role","unit","lsl","usl"}],
                   "windows": [{"factor","lo","hi"}]} — mirrored 1:1 by
    computeWatchContextFingerprint() in ontology_store.mjs (watch-context-v1).
    """
    decl = decl if isinstance(decl, dict) else {}
    cols = [c for c in (decl.get("columns") or []) if isinstance(c, dict)]
    wins = [w for w in (decl.get("windows") or []) if isinstance(w, dict)]
    col_lines = sorted("|".join([
        "C",
        str(c.get("col") if c.get("col") is not None else (c.get("name") or "")),
        str(c.get("role") or ""),
        str(c.get("unit") or ""),
        canonical_number_token(c.get("lsl")),
        canonical_number_token(c.get("usl")),
    ]) for c in cols)
    win_lines = sorted("|".join([
        "W",
        str(w.get("factor") if w.get("factor") is not None else (w.get("col") or "")),
        canonical_number_token(w.get("lo")),
        canonical_number_token(w.get("hi")),
    ]) for w in wins)
    payload = "\n".join([f"v={WATCH_CONTEXT_FP_VERSION}", *col_lines, *win_lines])
    return sha256_text(payload)


# ───────────────────────────── store 客户端（读 index 就地；写走唯一写入口） ─

def resolve_store_dir(store_dir=None):
    if store_dir:
        return contained(store_dir)
    env = os.environ.get("ONTOLOGY_STORE_DIR")
    if env:
        return contained(env)
    return DEFAULT_STORE_DIR


def read_store_index(store_dir):
    path = Path(store_dir) / "index.json"
    if not path.is_file():
        return {"version": 1, "entries": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "entries": []}
    entries = data.get("entries") if isinstance(data, dict) else None
    return {"version": data.get("version", 1) if isinstance(data, dict) else 1,
            "entries": entries if isinstance(entries, list) else []}


def entry_profile(entry):
    value = entry.get("profile") if isinstance(entry, dict) else None
    return (value or DEFAULT_PROFILE).strip() if isinstance(value, str) and value.strip() else DEFAULT_PROFILE


def lookup(store_dir, *, profile, scene_key, context_fp):
    """profile+scene+context_fp lookup. exact | scene_only | miss (frozen enum).

    exact is matched across ALL scenes first: the same data context can be
    published under different scene keys (run name vs derived key), and a
    scene-first filter turns that into an avoidable miss + duplicate build.
    """
    entries = [e for e in read_store_index(store_dir)["entries"]
               if isinstance(e, dict)
               and entry_profile(e) == profile
               and e.get("quality") != "deprecated"]
    if context_fp:
        exact = [e for e in entries if (e.get("context_fp") or None) == context_fp]
        if exact:
            best = sorted(exact, key=lambda e: (-int(e.get("version") or 0), str(e.get("path") or "")))[0]
            return {"status": "exact", "entry": best,
                    "cross_scene": bool(scene_key) and best.get("scene_key") != scene_key}
    scoped = [e for e in entries if not scene_key or e.get("scene_key") == scene_key]
    if scene_key and scoped:
        best = sorted(scoped, key=lambda e: (-int(e.get("version") or 0), str(e.get("path") or "")))[0]
        return {"status": "scene_only", "entry": best}
    return {"status": "miss", "entry": None}


def store_call(*argv, store_dir, timeout=180):
    """Run ontology_store.mjs with an argument LIST (never a shell string).

    The store is the single write path for ontology assets — prepare never
    writes index.json itself.
    """
    env = dict(os.environ)
    env["ONTOLOGY_STORE_DIR"] = str(store_dir)
    argv = ["node", str(STORE_JS), *argv]
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                          shell=False, cwd=str(REPO_ROOT), env=env)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()[-800:])
    return json.loads(proc.stdout)


def resolve_action(mode, lookup_status):
    """Frozen action state machine (identical to the DOE stage). Returns
    (action, source_note_or_None)."""
    if mode == "reuse":
        if lookup_status == "exact":
            return ACTION_REUSED, None
        return ACTION_BUILT, "mode=reuse requested but no exact store match — fell back to build"
    if mode == "extend":
        if lookup_status in ("exact", "scene_only"):
            return ACTION_EXTENDED, None
        return ACTION_BUILT, "mode=extend requested but store has no compatible entry — fell back to build"
    if mode == "full":
        return ACTION_BUILT, "mode=full — reuse skipped by explicit request"
    action = {"exact": ACTION_REUSED, "scene_only": ACTION_EXTENDED, "miss": ACTION_BUILT}[lookup_status]
    return action, None


def commit_to_store(run_dir, *, store, store_dir, profile, scene, context_fp,
                    build_mode, data_stage, data_path, lookup_status, lookup_entry):
    """Reuse-copy on an exact hit, else publish the run's 01_ontology/ontology.json.

    ⚠ Key on the resolved ACTION at the call site, exactly like the DOE stage:
    call this helper only when action == ACTION_REUSED; for built/extended (even
    when lookup_status == "exact" — mode=full or an explicit adoption over an
    existing scene) publish directly via ``store_call("publish", …)`` instead.
    Reuse-copying a fresh build on an exact lookup silently overwrites the new
    ontology with the stale store asset (field-tested 2026-10-22).

    Returns (store_result, version). The ontology is already in the run dir when
    publishing — a store failure is downgraded to store.published=False with the
    error recorded: the store is an optimisation, not a gate.
    """
    store_result = {"lookup": lookup_status, "published": False,
                    "entry_version": lookup_entry.get("version") if lookup_entry else None}
    if lookup_status == "exact":
        store_result["reuse"] = store_call(
            "reuse", "--source", str(Path(store) / str(lookup_entry.get("path"))),
            "--run-dir", str(run_dir), store_dir=store_dir)
        store_result["published"] = True
        return store_result, (int(lookup_entry.get("version") or 0) or None)
    publish_args = ["publish", "--run-dir", str(run_dir), "--scene", scene,
                    "--profile", profile, "--context-fp", context_fp,
                    "--build-mode", str(build_mode), "--data-stage", data_stage]
    if data_path is not None and Path(data_path).suffix.lower() in (".csv", ".tsv"):
        publish_args += ["--data-file", str(data_path)]
    try:
        published = store_call(*publish_args, store_dir=store_dir)
        store_result.update({"published": True, "entry_version": published.get("version"),
                             "deduped": bool(published.get("deduped"))})
        return store_result, published.get("version")
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        store_result.update({"published": False, "error": str(exc)})
        return store_result, None


# ───────────────────────────────────────────── Phase 0 门禁（watch 家族形态） ─

def enforce_brief_gate(run_dir, ctx):
    """Watch-family ontology gate.

    Frozen semantics (deliberately narrower than the DOE gate — no analysis_plan
    requirement and no design_only statistics block: those are DOE-specific):
      * `ctx` not a dict, `ctx["ontology"]` missing, or mode in (None, "off")
          → no-op (gate off, keeps every pre-ontology fixture green);
      * mode != off and `01_ontology/ontology_brief.json` missing
          → SystemExit("ONTOLOGY_BRIEF_REQUIRED: …").
    """
    if not isinstance(ctx, dict):
        return
    ont = ctx.get("ontology")
    if not isinstance(ont, dict):
        return
    mode = ont.get("mode")
    if mode in (None, "off"):
        return
    run_dir_v = contained(run_dir)
    brief = run_dir_v / "01_ontology" / "ontology_brief.json"
    if not brief.is_file():
        raise SystemExit(
            f"{GATE_BRIEF_REQUIRED}: ontology mode='{mode}' requires "
            f"{brief} — run the ontology stage (the skill's ontology_prepare.py) "
            f"before analyzing"
        )
    return None


# ──────────────────────────────────────────────── 数据表探测（表头级，无重依赖） ─

MAX_PROBE_ROWS = 2000   # input-size guard: never scan a whole table for a header probe


def load_table_columns(path):
    """Minimal CSV/TSV header + emptiness probe (no pandas dependency).

    Only the first ``MAX_PROBE_ROWS`` data rows are streamed (stop as soon as the
    cap is reached) and the result carries ``truncated: bool`` so callers can
    disclose that the probe is a sample, not a full-table count.
    Non-tabular formats (xlsx/parquet/…) return None — the caller decides."""
    p = Path(path)
    if not p.is_file():
        return None
    if p.suffix.lower() not in (".csv", ".tsv"):
        return None
    delimiter = "\t" if p.suffix.lower() == ".tsv" else ","
    with p.open("r", encoding="utf-8", errors="replace") as fh:
        header_line = fh.readline()
        if not header_line:
            return None
        header = [h.strip() for h in header_line.rstrip("\r\n").split(delimiter)]
        empty_counts = {h: 0 for h in header}
        total = {h: 0 for h in header}
        rows_read = 0
        truncated = False
        for line in fh:
            if rows_read >= MAX_PROBE_ROWS:
                truncated = True
                break
            rows_read += 1
            if not line.strip():
                continue
            cells = line.split(delimiter)
            for idx, name in enumerate(header):
                total[name] += 1
                if idx >= len(cells) or not cells[idx].strip():
                    empty_counts[name] += 1
    return {"columns": header, "total": total, "empty": empty_counts,
            "truncated": truncated}


def resolve_data_path(run_dir, data, ctx, candidate_names=("data.csv",)):
    """Declaration-first data resolution — never a free directory scan.
    explicit --data > context data_path > fixed candidate names in 00_input."""
    if data:
        return contained(data, run_dir)
    declared = ctx.get("data_path") if isinstance(ctx, dict) else None
    if declared:
        candidate = Path(declared)
        if not candidate.is_absolute():
            candidate = Path(run_dir) / declared
        if candidate.is_file():
            return contained(candidate, run_dir)
    for name in candidate_names:
        candidate = Path(run_dir) / "00_input" / name
        if candidate.is_file():
            return candidate
    return None


# ───────────────────────────────────────────── shipped 物理词典（纪律见模块头） ─

_PARAM_NAME_RE = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")


def normalize_param_name(name):
    """Lowercase and strip separators for dictionary matching (CJK kept)."""
    return _PARAM_NAME_RE.sub("", str(name or "").lower())


def load_physics_dictionary():
    """Raw shipped dictionary file (contains `$schema` + a `parameters` map of
    families). Prefer `load_physics_families()` for matching."""
    try:
        data = read_json(PHYSICS_DICT)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def load_physics_families():
    """Family map consumed by `match_physics_entry` — the `parameters` sub-map
    of the shipped dictionary (families live under that key, field-tested
    2026-10-22; feeding the raw file to the matcher never matches)."""
    data = load_physics_dictionary()
    params = data.get("parameters")
    if isinstance(params, dict):
        return params
    return {k: v for k, v in data.items() if isinstance(v, dict)}


def match_physics_entry(dictionary, col_name):
    """Unique-candidate exact match only; zero or multiple candidates → None.

    The matcher never guesses: an ambiguous Chinese column colliding with
    several dictionary families is `mapping_status="unmatched"`, not a pick.
    """
    key = normalize_param_name(col_name)
    if not key:
        return None
    hits = []
    for family, entry in dictionary.items():
        if not isinstance(entry, dict):
            continue
        names = {normalize_param_name(family)}
        names.update(normalize_param_name(s) for s in (entry.get("synonyms") or []))
        if key in names:
            hits.append((family, entry))
    if len(hits) == 1:
        return {"family": hits[0][0], "entry": hits[0][1]}
    return None


def dictionary_reference_band(entry):
    """The dictionary's typical_ranges — REFERENCE BAND ONLY (plan v2 principle 2).

    Returns the raw declared bands for brief display ('参考区间（非规格）').
    Never feed these into normal_range / spec / Cpk.
    """
    if not isinstance(entry, dict):
        return None
    return entry.get("typical_ranges")


def make_watch_signal(*, column, role, unit=None, normal_range=None,
                      physical_meaning=None, governing_law=None,
                      knowledge_source="auto_inferred", inference_basis=None,
                      confidence="INFERRED", schema_role="predictor"):
    """Schema-shaped signal with honesty markers baked in.

    role: watch-family role (time/group/parameter/inspection/…, free text for
    the brief); schema_role: the ontology schema enum (target|predictor|
    confounder|control|metadata). normal_range accepts ONLY user/context
    declarations — callers must never pass dictionary_reference_band() here.
    """
    sig = {
        "name": str(column),
        "column": str(column),
        "role": schema_role,
        "auto_inferred": knowledge_source != "user_provided",
        "inference_basis": inference_basis or (
            "auto prior from shipped physics dictionary" if knowledge_source == "auto_inferred"
            else "declared by user/context"),
        "knowledge_source": knowledge_source,
        "physical_meaning_confidence": confidence,
        "observed_data_behavior": "NOT_APPLICABLE",
        "behavior_match": "UNVERIFIED",
    }
    if unit:
        sig["unit"] = str(unit)
    if normal_range is not None:
        sig["normal_range"] = [normal_range[0], normal_range[1]]
    if physical_meaning:
        sig["physical_meaning"] = str(physical_meaning)
    if governing_law:
        sig["governing_law"] = str(governing_law)
    return sig


def standard_provenance(*, profile, engine, build_mode, data_stage, source):
    """Provenance block shared by both watch prepares (rag_used/web_used are
    read from this block downstream — the deterministic paths report False)."""
    return {
        "engine": engine,
        "profile": profile,
        "build_mode": build_mode,
        "data_stage": data_stage,
        "rag_used": False,
        "web_used": False,
        "physics_prior_used": True,
        "source": source,
    }


def empty_ontology_skeleton(*, scene_name, process_type):
    """Minimal schema-valid ontology shell (scene/signals/relationships/metadata)."""
    return {
        "scene": {"name": str(scene_name), "process_type": str(process_type)},
        "signals": {
            "inspection_signals": [],
            "process_parameters": [],
            "control_variables": [],
            "events": [],
            "metadata_columns": [],
        },
        "relationships": [],
        "metadata": {"units": {}},
    }


def timed_result(started):
    return int((time.perf_counter() - started) * 1000)


def summary_view(result, keys=("action", "scene_key", "data_stage", "version", "context_fp",
                               "elapsed_ms", "rag_used", "web_used", "lookup", "store",
                               "brief_json", "coverage_path", "reason")):
    return {k: result.get(k) for k in keys if k in result}


def cli_main(prepare_fn, *, prog_desc, extra_args=()):
    """Shared CLI driver for the watch prepare scripts."""
    import argparse
    ap = argparse.ArgumentParser(description=prog_desc)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--data", default=None, help="primary table path (default: context data_path / 00_input)")
    ap.add_argument("--context", default=None,
                    help="context JSON path (default: RUN_DIR/00_input/report_context.json)")
    ap.add_argument("--mode", default="auto", choices=list(VALID_MODES))
    ap.add_argument("--scene", default=None, help="scene_key override")
    ap.add_argument("--store-dir", default=None, help="ontology store root (default: data/ontology_store)")
    for flag_args, flag_kwargs in extra_args:
        ap.add_argument(*flag_args, **flag_kwargs)
    ap.add_argument("--json", action="store_true", help="print the full result JSON")
    args = ap.parse_args()
    result = prepare_fn(args)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(summary_view(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    # 直接运行 = 指纹自检（与 ontology_store.mjs context-fp --profile stability 对拍）
    demo = {"columns": [{"col": "temp", "role": "parameter", "unit": "degC", "lsl": 10, "usl": 90}],
            "windows": [{"factor": "temp", "lo": 20, "hi": 80}]}
    print(json.dumps({"context_fp": compute_watch_context_fp(demo),
                      "version": WATCH_CONTEXT_FP_VERSION}, indent=2))
