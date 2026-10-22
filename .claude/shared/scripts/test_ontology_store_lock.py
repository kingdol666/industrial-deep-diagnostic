#!/usr/bin/env python
"""Cross-process concurrency test for the ontology store write lock (D1).

Runs 10 concurrent `node` processes, each publishing two distinct ontology
versions of the SAME scene into the SAME store, and asserts the store ends
consistent: no lost index entries, no clobbered version directories, and every
index `content_sha256` still matches the `ontology.json` on disk.

Versions are published with `quality="endorsed"` on purpose: endorsed entries
are exempt from the per-scene version-pruning window, so all 20 publishes must
remain visible (with `unvalidated` the store would legitimately prune to the
newest 10 and the count assertion would be meaningless).

Run:  uv run --project .claude/shared/scripts python \
          .claude/shared/scripts/test_ontology_store_lock.py
"""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
STORE_JS = HERE / "ontology_store.mjs"

SCENE = "lock_scene"
N_PROCESSES = 10
PUBLISHES_PER_PROCESS = 2
EXPECTED_ENTRIES = N_PROCESSES * PUBLISHES_PER_PROCESS

# One child = two sequential publishes; all children start together.
CHILD_SCRIPT = """
const { pathToFileURL } = await import('node:url');
// argv[1] is a dummy token: with `node -e`, importing a module whose absolute
// path equals process.argv[1] would make its isDirectRun CLI branch fire.
const [, storeFile, scene, quality, ...runs] = process.argv.slice(1);
const store = await import(pathToFileURL(storeFile).href);
for (const runDir of runs) {
  store.publish({ runDir, scene, buildMode: 'full', quality, profile: 'diagnosis' });
}
console.log(JSON.stringify({ published: runs.length }));
"""


def _write_run(root: Path, index: int) -> Path:
    run_dir = root / f"run_{index:02d}"
    (run_dir / "01_ontology").mkdir(parents=True, exist_ok=True)
    ontology = {
        "scene": {"name": SCENE, "process_type": "concurrency_test"},
        "signals": {"inspection_signals": [], "process_parameters": [],
                    "control_variables": [], "events": [], "metadata_columns": []},
        "relationships": [],
        "metadata": {"units": {}, "note": f"run-{index:02d}-" + "x" * 1200},
    }
    text = json.dumps(ontology, ensure_ascii=False, indent=2)
    while len(text.encode("utf-8")) < 1200:
        ontology["metadata"]["note"] += "y"
        text = json.dumps(ontology, ensure_ascii=False, indent=2)
    (run_dir / "01_ontology" / "ontology.json").write_text(text, encoding="utf-8")
    return run_dir


class OntologyStoreConcurrentPublish(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix=".tmp-ontology-lock-", dir=str(HERE)))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.store_dir = self.base / "store"
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.runs = [_write_run(self.base, i) for i in range(EXPECTED_ENTRIES)]

    def test_concurrent_publish_preserves_all_entries(self):
        env = dict(os.environ)
        env["ONTOLOGY_STORE_DIR"] = str(self.store_dir)
        procs = []
        for i in range(N_PROCESSES):
            batch = self.runs[i * PUBLISHES_PER_PROCESS:(i + 1) * PUBLISHES_PER_PROCESS]
            procs.append(subprocess.Popen(
                ["node", "--input-type=module", "-e", CHILD_SCRIPT,
                 "__child__", str(STORE_JS), SCENE, "endorsed",
                 *[str(r) for r in batch]],
                cwd=str(REPO_ROOT), env=env, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True))
        failures = []
        for i, proc in enumerate(procs):
            out, err = proc.communicate(timeout=180)
            if proc.returncode != 0:
                failures.append(f"child {i} exit {proc.returncode}: {(err or out).strip()[-400:]}")
        self.assertEqual(failures, [], "concurrent publishers failed:\n" + "\n".join(failures))

        index_path = self.store_dir / "index.json"
        self.assertTrue(index_path.is_file(), "index.json was never written")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        entries = [e for e in index.get("entries", []) if e.get("scene_key") == SCENE]

        self.assertEqual(len(entries), EXPECTED_ENTRIES,
                         f"lost index entries: {len(entries)} != {EXPECTED_ENTRIES}")
        versions = sorted(e["version"] for e in entries)
        self.assertEqual(versions, list(range(1, EXPECTED_ENTRIES + 1)),
                         f"version numbering collided: {versions}")
        paths = [e["path"] for e in entries]
        self.assertEqual(len(set(paths)), EXPECTED_ENTRIES,
                         f"duplicate version directories: {paths}")

        for entry in entries:
            version_dir = (self.store_dir / entry["path"]).parent
            ontology_path = self.store_dir / entry["path"]
            self.assertTrue(version_dir.is_dir(),
                            f"missing version dir for v{entry['version']}: {version_dir}")
            self.assertTrue(ontology_path.is_file(),
                            f"missing ontology.json for v{entry['version']}")
            digest = "sha256:" + hashlib.sha256(ontology_path.read_bytes()).hexdigest()
            self.assertEqual(entry["content_sha256"], digest,
                             f"content hash drift on v{entry['version']}")
            self.assertTrue((version_dir / "provenance.json").is_file(),
                            f"missing provenance.json for v{entry['version']}")

        self.assertFalse((self.store_dir / ".lock").exists(),
                         "lock file leaked after all publishers exited")


if __name__ == "__main__":
    unittest.main(verbosity=2)
