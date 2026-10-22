#!/usr/bin/env python
"""Conformance tests for the shared ontology prepare core + ontology_store.mjs
profile scoping (plan v2 P0a.3).

Covers:
  * watch-context-v1 fingerprint cross-language parity (JS CLI vs Python);
  * profile-scoped version namespace: diagnosis keeps the legacy `<scene>/vN`
    layout, non-default profiles publish to `<scene>/<profile>/vN`, and no
    profile can overwrite another profile's directory;
  * profile-scoped pruning: exhausting one profile's version window can never
    delete another profile's assets;
  * lookup profile isolation + exact-across-scenes;
  * removeVersion profile qualification.

Run:  uv run --project .claude/shared/scripts python .claude/shared/scripts/test_ontology_prepare_common.py
"""

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

sys_path = str(HERE)
if sys_path not in os.sys.path:
    os.sys.path.insert(0, sys_path)
from ontology_prepare_common import (  # noqa: E402
    compute_watch_context_fp, lookup, resolve_action,
    load_physics_families, match_physics_entry,
    ACTION_REUSED, ACTION_EXTENDED, ACTION_BUILT,
)


def _node(*argv, store_dir):
    env = dict(os.environ)
    env["ONTOLOGY_STORE_DIR"] = str(store_dir)
    proc = subprocess.run(["node", str(STORE_JS), *argv], capture_output=True, text=True,
                          shell=False, cwd=str(REPO_ROOT), env=env, timeout=120)
    if proc.returncode != 0:
        raise AssertionError(f"store CLI failed: {argv}\n{proc.stderr or proc.stdout}")
    return json.loads(proc.stdout)


def _make_run(root, name, scene_name="场景X"):
    run_dir = Path(root) / name
    (run_dir / "01_ontology").mkdir(parents=True, exist_ok=True)
    # ≥1KB、合法 JSON、schema 宽松（publish 只做字节下限 + JSON 解析）
    ontology = {
        "scene": {"name": scene_name, "process_type": "test_process",
                  "production_goal": "x" * 64},
        "signals": {"inspection_signals": [], "process_parameters": [],
                    "control_variables": [], "events": [], "metadata_columns": []},
        "relationships": [],
        "metadata": {"units": {}, "note": "y" * 1024},
    }
    text = json.dumps(ontology, ensure_ascii=False, indent=2)
    while len(text.encode("utf-8")) < 1200:
        ontology["metadata"]["note"] += "y"
        text = json.dumps(ontology, ensure_ascii=False, indent=2)
    (run_dir / "01_ontology" / "ontology.json").write_text(text, encoding="utf-8")
    return run_dir


def _publish(store_dir, run_dir, profile, scene, fp, build_mode="prior_knowledge", data_stage="collected"):
    return _node("publish", "--run-dir", str(run_dir), "--scene", scene, "--profile", profile,
                 "--context-fp", fp, "--build-mode", build_mode, "--data-stage", data_stage,
                 store_dir=store_dir)


class PhysicsDictionaryMatcher(unittest.TestCase):
    def test_unique_synonym_matches(self):
        families = load_physics_families()
        self.assertTrue(families, "shipped dictionary must expose families")
        hit = match_physics_entry(families, "spindle_vibration")
        self.assertIsNotNone(hit, "unique synonym 'spindle_vibration' must match")
        entry = hit["entry"]
        self.assertIn("physical_unit_SI", entry)
        self.assertIn("typical_ranges", entry)

    def test_ambiguous_or_unknown_never_match(self):
        families = load_physics_families()
        # temp 是双族同义词（实测）→ 唯一候选纪律判 unmatched；temperature_C
        # 是族名本身 → 精确唯一命中
        self.assertIsNone(match_physics_entry(families, "temp"))
        self.assertIsNotNone(match_physics_entry(families, "temperature_C"))
        self.assertIsNone(match_physics_entry(families, "totally_unknown_column_xyz"))


class WatchFingerprintParity(unittest.TestCase):
    CASES = [
        {"columns": [{"col": "temp", "role": "parameter", "unit": "degC", "lsl": 10, "usl": 90}],
         "windows": [{"factor": "temp", "lo": 20, "hi": 80}]},
        {"columns": [
            {"col": "熔体压力", "role": "parameter", "unit": "MPa", "lsl": None, "usl": 12.5},
            {"col": "time", "role": "time", "unit": "", "lsl": "", "usl": ""},
            {"col": "batch", "role": "group", "unit": None, "lsl": None, "usl": None},
         ], "windows": []},
        {"columns": [{"col": "v", "role": "parameter", "unit": "mm/s", "lsl": 1e15, "usl": 0.1}],
         "windows": [{"factor": "v", "lo": -0.0, "hi": 1e15}]},
        {"columns": [], "windows": [{"factor": "w", "lo": 3, "hi": 7}]},
    ]

    def test_parity_with_js_cli(self):
        for i, decl in enumerate(self.CASES):
            py = compute_watch_context_fp(decl)
            js = _node("context-fp", "--profile", "stability",
                       "--context-json", json.dumps(decl, ensure_ascii=False), store_dir=REPO_ROOT / "data")
            self.assertEqual(py, js["context_fp"], f"case {i} diverged")
            self.assertEqual(js["version"], "watch-context-v1")

    def test_declaration_change_changes_fp(self):
        a = compute_watch_context_fp({"columns": [{"col": "t", "role": "parameter", "unit": "degC"}]})
        b = compute_watch_context_fp({"columns": [{"col": "t", "role": "parameter", "unit": "K"}]})
        self.assertNotEqual(a, b)


class ProfileVersionNamespace(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix=".tmp-ont-common-", dir=REPO_ROOT))
        self.store = self.root / "store"
        self.store.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _publish_all_profiles(self, scene="lineA"):
        out = {}
        for profile in ("diagnosis", "doe", "stability", "sentinel"):
            run = _make_run(self.root, f"run_{profile}", scene_name=scene)
            out[profile] = _publish(self.store, run, profile, scene, f"sha256:fp-{profile}-0")
        return out

    def test_profiles_do_not_share_version_directories(self):
        published = self._publish_all_profiles()
        # 非默认 profile 落 <scene>/<profile>/vN；diagnosis 保持 legacy <scene>/vN
        self.assertIn("\\v1\\ontology.json", published["diagnosis"]["path"])
        for profile in ("doe", "stability", "sentinel"):
            expected_tail = f"{profile}\\v1\\ontology.json"
            self.assertTrue(published[profile]["path"].replace("/", "\\").endswith(expected_tail),
                            f"{profile}: {published[profile]['path']}")
        # 同 scene 再发一版 → 各 profile 版本号独立递增，目录互不覆盖
        for profile in ("diagnosis", "stability"):
            run = _make_run(self.root, f"run2_{profile}")
            second = _publish(self.store, run, profile, "lineA", f"sha256:fp-{profile}-1")
            self.assertEqual(second["version"], 2, profile)

    def test_pruning_is_profile_scoped(self):
        self._publish_all_profiles()
        # stability 连发 12 版（非 endorsed）→ 只裁 stability 自己的旧版
        for i in range(12):
            run = _make_run(self.root, f"stab_{i}")
            _publish(self.store, run, "stability", "lineA", f"sha256:stab-{i}")
        idx = json.loads((self.store / "index.json").read_text(encoding="utf-8"))
        stab = [e for e in idx["entries"] if e.get("profile") == "stability"]
        diag = [e for e in idx["entries"] if (e.get("profile") in (None, "diagnosis"))]
        doe = [e for e in idx["entries"] if e.get("profile") == "doe"]
        sent = [e for e in idx["entries"] if e.get("profile") == "sentinel"]
        self.assertLessEqual(len(stab), 10, "stability window must cap at 10")
        self.assertEqual(len(diag), 1, "diagnosis asset must survive stability pruning")
        self.assertEqual(len(doe), 1, "doe asset must survive stability pruning")
        self.assertEqual(len(sent), 1, "sentinel asset must survive stability pruning")
        for e in diag + doe + sent:
            self.assertTrue((self.store / e["path"]).is_file(),
                            f"asset deleted by foreign pruning: {e['path']}")

    def test_lookup_profile_isolation_and_cross_scene_exact(self):
        self._publish_all_profiles(scene="lineA")
        # stability 的 lookup 永不命中 doe/diagnosis 资产：未知 fp + 未知 scene → miss
        miss = lookup(self.store, profile="stability", scene_key="nosuchscene", context_fp="sha256:nope")
        self.assertEqual(miss["status"], "miss")
        # 同 scene 存在但 fp 不同 → scene_only（extend 语义），绝不会跨 profile 命中
        scene_only = lookup(self.store, profile="stability", scene_key="lineA", context_fp="sha256:nope")
        self.assertEqual(scene_only["status"], "scene_only")
        foreign = lookup(self.store, profile="diagnosis", scene_key="lineA", context_fp="sha256:fp-stability-0")
        self.assertEqual(foreign["status"], "scene_only")
        # 同 context_fp 在另一 scene 命中 → exact 且标记 cross_scene（stability 的 fp 不会被别的 profile 认领）
        self.assertEqual(lookup(self.store, profile="doe", scene_key="lineC", context_fp="sha256:fp-stability-0")["status"], "miss")
        hit = lookup(self.store, profile="stability", scene_key="lineC", context_fp="sha256:fp-stability-0")
        self.assertEqual(hit["status"], "exact")
        self.assertTrue(hit["cross_scene"])

    def test_resolve_action_state_machine(self):
        self.assertEqual(resolve_action("reuse", "miss")[0], ACTION_BUILT)
        self.assertEqual(resolve_action("reuse", "exact")[0], ACTION_REUSED)
        self.assertEqual(resolve_action("extend", "scene_only")[0], ACTION_EXTENDED)
        self.assertEqual(resolve_action("extend", "miss")[0], ACTION_BUILT)
        self.assertEqual(resolve_action("full", "exact")[0], ACTION_BUILT)
        self.assertEqual(resolve_action("auto", "exact")[0], ACTION_REUSED)

    def test_remove_version_profile_qualified(self):
        self._publish_all_profiles()
        _node("remove", "lineA", "--version", "1", "--profile", "stability", store_dir=self.store)
        idx = json.loads((self.store / "index.json").read_text(encoding="utf-8"))
        profiles_left = {e.get("profile") or "diagnosis" for e in idx["entries"] if e["scene_key"] == "lineA"}
        self.assertNotIn("stability", profiles_left)
        self.assertEqual(profiles_left, {"diagnosis", "doe", "sentinel"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
