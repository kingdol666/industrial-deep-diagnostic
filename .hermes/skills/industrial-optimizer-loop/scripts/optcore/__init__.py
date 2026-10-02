"""optcore — deterministic core of industrial-optimizer-loop (no LLM, no IO here).

Package layout (plan industrial-closedloop-skills-v1 §5, C line):
  objective.py     objective loading + O-G1/O-G1a validation + domain resolution
  windows_seed.py  prior recommendations.json -> R001 window_seed points
  strategy.py      pure state-machine transitions + method decision tree
  gp.py            numpy ARD-RBF GP (heteroscedastic nugget) + closed-form EI
  rsm_model.py     quadratic RSM / poly_refine (reuses doe-analyzer doestats)
  acquisition.py   LHS + greedy MC-EI batch selection + support flags
  experience.py    recipe envelope writeback (local files only, v1.4 pure-analysis)

Constants are pinned from the single enum source
`.claude/shared/schemas/closedloop_enums.json` (via closedloop_common.enums);
changing a literal there is a breaking contract (see method_notes.md).
"""

import datetime
import hashlib
import json
import math
import os
import sys
from pathlib import Path

OPTCORE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = OPTCORE_DIR.parent
SKILL_DIR = SCRIPTS_DIR.parent
REPO_ROOT = SKILL_DIR.parents[2]
SHARED_SCRIPTS = REPO_ROOT / ".claude" / "shared" / "scripts"
DOE_SCRIPTS = REPO_ROOT / ".claude" / "skills" / "industrial-doe-analyzer" / "scripts"
REPO_ROOT_NORM = os.path.normpath(os.path.abspath(str(REPO_ROOT)))

# single enum source (M0 contract) --------------------------------------------
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from closedloop_common.enums import (  # noqa: E402
    CONTRACT_VERSIONS,
    OPTIMIZER_CONSTANTS,
    OPTIMIZER_GOALS,
    OPTIMIZER_METHODS,
    OPTIMIZER_NEXT_ACTIONS,
    OPTIMIZER_PHASES,
    TRIAL_STATUS,
)

VERSION = "1.0.0"

# pinned constants (closedloop_enums.json optimizer.constants) -----------------
EPS_EI_FRAC = float(OPTIMIZER_CONSTANTS["epsilon_ei_frac"])            # 0.005
STALL_ROUNDS = int(OPTIMIZER_CONSTANTS["stall_rounds"])                # 2
DELTA_CONFIRM = float(OPTIMIZER_CONSTANTS["delta_confirm_coded"])      # 0.05
DUP_RATIO_MAX = float(
    OPTIMIZER_CONSTANTS["domain_coverage_duplication_ratio_max"])      # 0.5
NEIGHBORHOOD = float(OPTIMIZER_CONSTANTS["neighborhood_coded"])        # 0.8

# GP / acquisition pinning (plan §5.1; see references/method_notes.md)
MC_SEED = 42
MC_SAMPLES = 1024
GP_BOUND_LO = math.log(0.05)
GP_BOUND_HI = math.log(2.0)
GP_N_STARTS = 3
GP_COND_MAX = 1e10
GP_NUGGET_RETRY = 3
EXPLORE_N_MIN = 8                      # exploring -> exploiting needs n >= max(2k+3, 8)
DUAL_GATE_D_FRAC = 0.8                 # D(x) >= 0.8 * D_max (USER DECISION)
CONFIRM_MIN_REPLICATES = 3
DEFAULT_SEED = 42
DUPLICATE_EPS_CODED = 1e-9

CONTRACT_VERSION = CONTRACT_VERSIONS.get("objective", "1.0")


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _contained(candidate, extra_root=None):
    """Inline path containment: normpath -> reject `..` segments -> repo-root
    (or extra_root) prefix whitelist. Mirrors doe-analyzer analyze.py _contained."""
    cand = os.path.normpath(os.path.abspath(str(candidate)))
    if any(seg == ".." for seg in cand.replace("/", os.sep).split(os.sep)):
        raise ValueError(f"traversal segment rejected in path: {candidate}")
    roots = [REPO_ROOT_NORM]
    if extra_root is not None:
        roots.append(os.path.normpath(os.path.abspath(str(extra_root))))
    for root in roots:
        if cand == root or cand.startswith(root + os.sep):
            return Path(cand)
    raise ValueError(f"path outside allowed roots: {candidate}")


def _read_json(path, extra_root=None):
    return json.loads(_contained(path, extra_root).read_text(encoding="utf-8"))


def _write_json(path, payload, extra_root=None):
    out = _contained(path, extra_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=float),
                   encoding="utf-8")
    return out


def _write_text(path, text, extra_root=None):
    out = _contained(path, extra_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out


def sha256_obj(payload):
    canon = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=float)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with _contained(path).open("rb") as fh:  # binary read, not text open()
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
