"""test_p5.py — WS2 (TXT shape) acceptance cases (plan hetero v1.1 §4 WS2).

P5 acceptance:
  1. three known bilingual remarks (CN / EN / mixed) -> exact event_ts,
     correct tag_slug, line_no and shift_bucket (CSV remarks table AND prose
     log paths both exercised);
  2. an ambiguous-date source ("05/07/2026 ...") is skipped WHOLE with a
     reason containing "ambiguous" — never guessed;
  3. annotations.json passes `node validate.mjs schemas/annotations_schema.json`;
  4. EVT contract columns carry evt_window_s=3600 (overridable via
     ctx.config["event_window_s"]) with stats_eligible=false;
  plus: quality gate exit 0 on the produced artifacts.

Fixtures are generated on the fly into a temp dir with fixed contents (the
shape is deterministic; no RNG involved).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent          # tests/cases
SKILL = HERE.parent.parent                       # skill root
SCRIPTS = SKILL / "scripts"
REPO = SCRIPTS.parent.parent.parent.parent      # repo root
sys.path.insert(0, str(SCRIPTS))
SHARED_PY = REPO / ".claude" / "shared" / "scripts" / ".venv" / "Scripts" / "python.exe"
if not SHARED_PY.exists():
    SHARED_PY = REPO / ".claude" / "shared" / "scripts" / ".venv" / "bin" / "python"
VALIDATE = REPO / ".claude" / "shared" / "scripts" / "validate.mjs"
GATE = SCRIPTS / "quality_gate.mjs"
ANN_SCHEMA = SKILL / "schemas" / "annotations_schema.json"

# (时间, 备注, 记录时间) — data rows 1-3 are the three known remarks; rows 4-5 are
# realistic filler rows that lift the notes column's long-text share over the
# 0.5 detection threshold (short Chinese remarks alone fall below it).
NOTES_ROWS = [
    ("2026-10-15 08:00", "换辊完成", "2026-10-15 08:05"),
    ("2026-10-15 10:30", "recipe change: recycle 8->12%", "2026-10-15 10:31"),
    ("2026-10-15 12:15", "现场清洗 15min", "2026-10-15 12:40"),
    ("2026-10-15 14:02", "本班无异常，各参数在工艺范围内", "2026-10-15 14:10"),
    ("2026-10-15 16:35", "已完成现场巡检，动静密封点无泄漏", "2026-10-15 16:40"),
]
KNOWN = [
    ("2026-10-15 08:00:00", {"ROLL_CHANGE"}, 1, "A", "2026-10-15 08:05:00"),
    ("2026-10-15 10:30:00", {"RECIPE_CHANGE"}, 2, "A", "2026-10-15 10:31:00"),
    ("2026-10-15 12:15:00", {"CLEANING"}, 3, "A", "2026-10-15 12:40:00"),
]
PROSE_LINES = [
    "2026-10-15 08:00 换辊完成",
    "2026-10-15 10:30 recipe change: recycle 8->12%",
    "2026-10-15 12:15 现场清洗 15min",
    "2026-10-15 22:05 film break at winding position 3, shutdown 20min",
    "2026-10-15 23:40 alarm cleared after cleaning of die",
    "2026-10-16 02:10 startup complete, calibration finished",
]
PROSE_EXPECT = [
    ("2026-10-15 08:00:00", {"ROLL_CHANGE"}, 1, "A", 8.0),
    ("2026-10-15 10:30:00", {"RECIPE_CHANGE"}, 2, "A", 10.5),
    ("2026-10-15 12:15:00", {"CLEANING"}, 3, "A", 12.25),
    ("2026-10-15 22:05:00", {"FILM_BREAK", "STOP"}, 4, "B", 22 + 5 / 60),
    ("2026-10-15 23:40:00", {"ALARM_CLEAR", "CLEANING"}, 5, "B", 23 + 40 / 60),
    ("2026-10-16 02:10:00", {"STARTUP", "CALIBRATION"}, 6, "C", 2 + 10 / 60),
]
MEMO_LINES = [
    "05/07/2026 备忘：本月点检计划",
    "05/07/2026 夜班交接完成",
]


def _run(cmd: list, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Fixed argument-list subprocess (never a shell string)."""
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                          shell=False, cwd=cwd, timeout=300)


def _py() -> str:
    return str(SHARED_PY if SHARED_PY.exists() else sys.executable)


def _tail(r: subprocess.CompletedProcess, n: int = 300) -> str:
    return (r.stdout + r.stderr)[-n:]


def _make_run(td: Path, with_prose: bool = False, with_memo: bool = False) -> tuple[Path, Path]:
    run_dir = td / "run"
    (run_dir / "00_input").mkdir(parents=True)
    pd.DataFrame({"时间": ["2026-10-15 08:00:00", "2026-10-15 08:10:00", "2026-10-15 08:20:00"],
                  "温度": [25.1, 25.2, 25.3]}).to_csv(
        run_dir / "00_input" / "preprocessed_data.csv", index=False, encoding="utf-8-sig")
    raw = td / "raw"
    raw.mkdir()
    pd.DataFrame(NOTES_ROWS, columns=["时间", "备注", "记录时间"]).to_csv(
        raw / "operator_notes.csv", index=False, encoding="utf-8-sig")
    if with_prose:
        (raw / "shift_log.md").write_text("\n".join(PROSE_LINES) + "\n", encoding="utf-8")
    if with_memo:
        (raw / "memo.txt").write_text("\n".join(MEMO_LINES) + "\n", encoding="utf-8")
    return run_dir, raw


def _build(run_dir: Path, raw: Path, extra: list | None = None) -> subprocess.CompletedProcess:
    cmd = [_py(), SCRIPTS / "build.py", "--raw-path", raw, "--run-dir", run_dir] + (extra or [])
    return _run(cmd)


def _het(run_dir: Path) -> Path:
    return run_dir / "07_hetero"


def _read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _assert_known_remarks(ann: list[dict], offset: int, out: list):
    """offset = annotations-list index of the first known remark."""
    for k, (ets, slugs, ln, bucket, rts) in enumerate(KNOWN):
        a = ann[offset + k] if offset + k < len(ann) else {}
        out.append((f"known remark {k + 1} event_ts exact", a.get("event_ts") == ets,
                    repr(a.get("event_ts"))))
        got = {t.get("tag_slug") for t in (a.get("tags") or [])}
        out.append((f"known remark {k + 1} tag_slug correct", got == slugs,
                    f"got {got}, want {slugs}"))
        tags = a.get("tags") or []
        out.append((f"known remark {k + 1} lexicon only / not model derived",
                    bool(tags) and all(t.get("method") == "lexicon"
                                       and t.get("model_derived") is False
                                       and t.get("matched_term") for t in tags),
                    json.dumps(tags, ensure_ascii=False)))
        out.append((f"known remark {k + 1} line_no", a.get("line_no") == ln,
                    repr(a.get("line_no"))))
        out.append((f"known remark {k + 1} shift_bucket", a.get("shift_bucket") == bucket,
                    repr(a.get("shift_bucket"))))
        out.append((f"known remark {k + 1} recorded_ts", a.get("recorded_ts") == rts,
                    repr(a.get("recorded_ts"))))


def case_remarks_csv():
    """Acceptance 1 (CSV path) + 3 (schema) + 4 (contract) + gate exit 0."""
    out = []
    with tempfile.TemporaryDirectory() as td:
        run_dir, raw = _make_run(Path(td))
        r = _build(run_dir, raw)
        out.append(("build exits 0", r.returncode == 0, _tail(r, 400)))
        try:
            payload = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            return [("build stdout parseable", False, _tail(r, 400))]
        out.append(("status ok", payload.get("status") == "ok", r.stdout[-200:]))

        ann_path = _het(run_dir) / "annotations.json"
        out.append(("annotations.json written", ann_path.exists(), str(ann_path)))
        ann = _read_json(ann_path)
        out.append(("5 annotations (3 known + 2 filler)", len(ann) == 5,
                    f"n={len(ann)}: {json.dumps([a.get('text') for a in ann], ensure_ascii=False)}"))
        _assert_known_remarks(ann, 0, out)

        # acceptance 3: validate.mjs against annotations_schema.json
        v = _run(["node", VALIDATE, ANN_SCHEMA, ann_path])
        try:
            report = json.loads(v.stdout)
        except Exception:
            report = {"valid": False, "errors": [{"message": (v.stdout + v.stderr)[-300:]}]}
        out.append(("annotations.json valid per validate.mjs",
                    v.returncode == 0 and report.get("valid") is True,
                    json.dumps(report.get("errors"))[:400]))

        # acceptance 4: EVT contract columns — extract-time declaration is
        # stats_eligible=false (sparse); after WS5's align recomputes
        # post-join bookkeeping (frozen I8) the consumer guarantee is that
        # every TXT column lands in explicit_cols.excludes (role=metadata).
        import importlib.util

        _spec = importlib.util.spec_from_file_location("hetshape_txt", SCRIPTS / "heterocore" / "shapes" / "txt.py")
        _txt = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_txt)

        class _Ctx:
            config = {}

        _found = _txt.detect([Path(raw) / "operator_notes.csv"], None)
        out.append(("extract detect finds the notes CSV", len(_found) == 1, str(_found)))
        _res = _txt.extract(_found[0]["spec"], _Ctx()) if _found else {"contract_rows": []}
        for c in _res.get("contract_rows", []):
            n = c["column"]
            if "-EVT-" in n:
                out.append((f"extract-time {n} evt_window_s=3600", c.get("evt_window_s") == 3600,
                            repr(c.get("evt_window_s"))))
                out.append((f"extract-time {n} stats_eligible=false", c.get("stats_eligible") is False,
                            repr(c.get("stats_eligible"))))
                out.append((f"extract-time {n} role=metadata/sparse/L2/lexicon/not-model",
                            c.get("role") == "metadata" and c.get("sparse") is True
                            and c.get("evidence_level") == 2
                            and c.get("method") == "lexicon_event_window"
                            and c.get("model_derived") is False,
                            json.dumps({k: c.get(k) for k in
                                        ("role", "sparse", "evidence_level", "method", "model_derived")})))

        cdoc = _read_json(_het(run_dir) / "column_contract.json")
        cols = {c["column"]: c for c in cdoc["columns"]}
        evt = sorted(n for n in cols if "-EVT-" in n)
        out.append(("three EVT columns", evt == [
            "HX-TXT-OPERATORNOTES-EVT-CLEANING",
            "HX-TXT-OPERATORNOTES-EVT-RECIPE-CHANGE",
            "HX-TXT-OPERATORNOTES-EVT-ROLL-CHANGE"], str(evt)))
        for n in evt:
            out.append((f"written {n} keeps evt_window_s=3600", cols[n].get("evt_window_s") == 3600,
                        repr(cols[n].get("evt_window_s"))))
        from heterocore import contracts as _contracts
        explicit = _contracts.derive_explicit_cols(cdoc)
        txt_cols = [n for n in cols if n.startswith("HX-TXT-")]
        out.append(("all TXT columns excluded from core_stats (role=metadata)",
                    bool(txt_cols) and all(n in explicit["excludes"] for n in txt_cols)
                    and not (set(explicit["targets"]) | set(explicit["predictors"])) & set(txt_cols),
                    json.dumps(explicit)))
        cov = sorted(n for n in cols if "HOUR-OF-DAY" in n or "SHIFT-BUCKET-ID" in n)
        out.append(("two clock covariate columns", len(cov) == 2, str(cov)))

        # features table: one row per event, EVT one-hot, covariates present
        fpath = _het(run_dir) / "features" / "TXT-OPERATORNOTES.csv"
        out.append(("features TXT-OPERATORNOTES.csv written", fpath.exists(), str(fpath)))
        fdf = pd.read_csv(fpath)
        out.append(("features rows == 5 events", len(fdf) == 5, str(fdf.shape)))
        out.append(("features ts ISO ascending",
                    list(fdf["ts"]) == sorted(fdf["ts"]) and str(fdf["ts"][0]) == "2026-10-15 08:00:00",
                    str(list(fdf["ts"]))))
        for col, rowi in (("EVT-ROLL-CHANGE", 0), ("EVT-RECIPE-CHANGE", 1), ("EVT-CLEANING", 2)):
            full = f"HX-TXT-OPERATORNOTES-{col}"
            out.append((f"{col} one-hot row {rowi}",
                        full in fdf.columns and int(fdf[full][rowi]) == 1
                        and int(fdf[full].sum()) == 1, str(list(fdf.columns))))
        hour_full = "HX-TXT-OPERATORNOTES-HOUR-OF-DAY"
        shift_full = "HX-TXT-OPERATORNOTES-SHIFT-BUCKET-ID"
        out.append(("hour_of_day covariate exact", float(fdf[hour_full][0]) == 8.0
                    and abs(float(fdf[hour_full][1]) - 10.5) < 1e-9, str(list(fdf[hour_full]))))
        out.append(("shift buckets A,A,A,A,B -> ids 1,1,1,1,2",
                    [int(x) for x in fdf[shift_full]] == [1, 1, 1, 1, 2],
                    str([int(x) for x in fdf[shift_full]])))

        g = _run(["node", GATE, "--run-dir", run_dir, "--raw-path", raw])
        out.append(("quality gate exit 0", g.returncode == 0, _tail(g, 500)))
    return out


def case_ambiguous_skip():
    """Acceptance 2: ambiguous-date source skipped whole, reason says ambiguous."""
    out = []
    with tempfile.TemporaryDirectory() as td:
        run_dir, raw = _make_run(Path(td), with_memo=True)
        r = _build(run_dir, raw)
        out.append(("build exits 0", r.returncode == 0, _tail(r, 400)))
        m = _read_json(_het(run_dir) / "hetero_manifest.json")
        by_slug = {s.get("slug"): s for s in m.get("sources", [])}
        out.append(("two sources registered", len(m.get("sources", [])) == 2,
                    json.dumps([s.get("slug") for s in m.get("sources", [])])))
        memo = by_slug.get("MEMO", {})
        out.append(("memo.txt registered", bool(memo), json.dumps(memo, ensure_ascii=False)[:300]))
        out.append(("memo disposition skipped", memo.get("disposition") == "skipped",
                    repr(memo.get("disposition"))))
        out.append(("memo reason mentions ambiguous",
                    "ambiguous" in str(memo.get("reason", "")).lower(),
                    repr(memo.get("reason"))))
        out.append(("memo contributed no features", memo.get("features") == []
                    and memo.get("n_snapshots") == 0,
                    json.dumps({"features": memo.get("features"), "n": memo.get("n_snapshots")})))
        notes = by_slug.get("OPERATORNOTES", {})
        out.append(("notes CSV unaffected (featured)", notes.get("disposition") == "featured",
                    repr(notes.get("disposition"))))
        ann = _read_json(_het(run_dir) / "annotations.json")
        out.append(("annotations only from the featured source",
                    len(ann) == 5 and all(a.get("source_id") == notes.get("source_id") for a in ann),
                    f"n={len(ann)}"))
    return out


def case_prose_log():
    """Prose path: md log with CN/EN/mixed lines, B/C buckets, multi-tag line,
    longest-match suppression (alarm cleared != alarm)."""
    out = []
    with tempfile.TemporaryDirectory() as td:
        run_dir, raw = _make_run(Path(td), with_prose=True)
        r = _build(run_dir, raw)
        out.append(("build exits 0", r.returncode == 0, _tail(r, 400)))
        m = _read_json(_het(run_dir) / "hetero_manifest.json")
        src = next((s for s in m.get("sources", []) if s.get("slug") == "SHIFTLOG"), {})
        out.append(("shift_log.md detected as text source", src.get("shape") == "text"
                    and src.get("disposition") == "featured",
                    json.dumps(src, ensure_ascii=False)[:300]))
        ann = [a for a in _read_json(_het(run_dir) / "annotations.json")
               if a.get("source_id") == src.get("source_id")]
        out.append(("6 prose annotations", len(ann) == 6, f"n={len(ann)}"))
        for k, (ets, slugs, ln, bucket, hour) in enumerate(PROSE_EXPECT):
            a = ann[k] if k < len(ann) else {}
            got = {t.get("tag_slug") for t in (a.get("tags") or [])}
            out.append((f"prose line {k + 1} event_ts exact", a.get("event_ts") == ets,
                        repr(a.get("event_ts"))))
            out.append((f"prose line {k + 1} tags exact", got == slugs, f"got {got}"))
            out.append((f"prose line {k + 1} line_no", a.get("line_no") == ln, repr(a.get("line_no"))))
            out.append((f"prose line {k + 1} shift_bucket", a.get("shift_bucket") == bucket,
                        repr(a.get("shift_bucket"))))
            out.append((f"prose line {k + 1} hour_of_day",
                        a.get("hour_of_day") is not None
                        and abs(float(a["hour_of_day"]) - hour) < 1e-6,
                        repr(a.get("hour_of_day"))))
        fdf = pd.read_csv(_het(run_dir) / "features" / "TXT-SHIFTLOG.csv")
        want_cols = {"HX-TXT-SHIFTLOG-EVT-ROLL-CHANGE", "HX-TXT-SHIFTLOG-EVT-RECIPE-CHANGE",
                     "HX-TXT-SHIFTLOG-EVT-CLEANING", "HX-TXT-SHIFTLOG-EVT-FILM-BREAK",
                     "HX-TXT-SHIFTLOG-EVT-STOP", "HX-TXT-SHIFTLOG-EVT-ALARM-CLEAR",
                     "HX-TXT-SHIFTLOG-EVT-STARTUP", "HX-TXT-SHIFTLOG-EVT-CALIBRATION"}
        got_cols = set(fdf.columns)
        out.append(("8 EVT columns, bare ALARM suppressed by longest match",
                    want_cols <= got_cols and "HX-TXT-SHIFTLOG-EVT-ALARM" not in got_cols,
                    str(sorted(c for c in fdf.columns if "-EVT-" in c))))
        out.append(("multi-tag row sets both EVT flags",
                    int(fdf["HX-TXT-SHIFTLOG-EVT-ALARM-CLEAR"][4]) == 1
                    and int(fdf["HX-TXT-SHIFTLOG-EVT-CLEANING"][4]) == 1,
                    str(fdf.iloc[4].to_dict())))
        out.append(("night shift bucket id 3 on row 3",
                    [int(x) for x in fdf["HX-TXT-SHIFTLOG-SHIFT-BUCKET-ID"]] == [1, 1, 1, 2, 2, 3],
                    str([int(x) for x in fdf["HX-TXT-SHIFTLOG-SHIFT-BUCKET-ID"]])))
    return out


def case_window_config():
    """Acceptance 4 (override): ctx.config event_window_s=7200 reaches the contract."""
    out = []
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        run_dir, raw = _make_run(tdp)
        cfg = tdp / "hetero_config.json"
        cfg.write_text(json.dumps({"event_window_s": 7200}), encoding="utf-8")
        r = _build(run_dir, raw, ["--config", cfg])
        out.append(("build exits 0", r.returncode == 0, _tail(r, 400)))
        cdoc = _read_json(_het(run_dir) / "column_contract.json")
        evt = [c for c in cdoc["columns"] if "-EVT-" in c["column"]]
        out.append(("EVT columns present", len(evt) == 3, str([c["column"] for c in evt])))
        out.append(("evt_window_s overridden to 7200",
                    all(c.get("evt_window_s") == 7200 for c in evt),
                    str([c.get("evt_window_s") for c in evt])))
        out.append(("formula mentions the configured window",
                    all("7200" in c.get("formula", "") for c in evt),
                    repr(evt[0].get("formula") if evt else None)))
    return out


CASES = [
    ("p5-remarks-csv", case_remarks_csv),
    ("p5-ambiguous-skip", case_ambiguous_skip),
    ("p5-prose-log", case_prose_log),
    ("p5-window-config", case_window_config),
]
