#!/usr/bin/env python
"""report_builder.py — standalone advisory landing page (thin CLI over imacore.render).

The shared renderer (`imacore/render.py`) is the single source of the visual
system and components, so the standalone page, the stability-report section and
the DOE section can never drift apart. Deterministic: numbers are read verbatim
from advisory_actions.json / charts.json; the only agent-writable field is
actions[].interpretation, rendered in a clearly-marked block.

Outputs (next to the advisory JSON):
  improvement_advisory.html   design-authority page, inline SVG, no CDN
  improvement_advisory.md     Chinese Markdown companion
  html_selfcheck.json         8-key self check
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_SCRIPTS = SCRIPT_DIR.parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ontology_prepare_common as oc  # noqa: E402

from imacore import render  # noqa: E402


def _read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def selfcheck(html_text, md_text, report):
    checks = {}
    checks["sections_goal"] = 'id="sec-goal"' in html_text
    checks["sections_roadmap"] = 'id="sec-roadmap"' in html_text
    checks["sections_actions"] = 'id="sec-actions"' in html_text
    checks["sections_evidence"] = 'id="sec-evidence"' in html_text
    checks["sections_execution"] = 'id="sec-execution"' in html_text
    checks["sections_data"] = 'id="sec-data"' in html_text
    checks["footer_disclaimer"] = ('id="sec-footer"' in html_text
                                   and "咨询边界声明" in html_text)
    # "}}" is legal CSS (nested media rules); only unrendered "{{" markers and
    # textual placeholders are disqualifying.
    checks["no_placeholder"] = not any(x in html_text for x in
                                       ("TODO", "FIXME", "<待填>", "{{"))
    checks["inline_svg"] = "<svg" in html_text
    checks["hash_in_page"] = str(report.get("data", {}).get("sha256")) in html_text
    checks["md_companion"] = len(md_text.strip()) > 200
    checks["advisory_language"] = "绝不下发参数" in html_text
    checks["pass"] = all(checks.values())
    return checks


def main(argv=None):
    ap = argparse.ArgumentParser(description="improvement advisory report builder")
    ap.add_argument("--advisory", required=True)
    ap.add_argument("--charts", required=True)
    ap.add_argument("--out", required=True, help="output directory or .html path")
    ap.add_argument("--no-md", action="store_true")
    args = ap.parse_args(argv)
    report = _read(args.advisory)
    charts = _read(args.charts)
    out = Path(args.out)
    if out.suffix.lower() == ".html":
        html_path = out
        out_dir = out.parent
    else:
        out_dir = out
        html_path = out_dir / "improvement_advisory.html"
    html_text = render.render_page(report, charts)
    md_text = render.render_markdown(report)
    oc.write_text_contained(html_path, html_text)
    md_path = out_dir / "improvement_advisory.md"
    if not args.no_md:
        oc.write_text_contained(md_path, md_text)
    checks = selfcheck(html_text, md_text, report)
    selfcheck_path = out_dir / "html_selfcheck.json"
    oc.write_json_strict(selfcheck_path, {
        "contract_version": "improvement-advisory-selfcheck/1.0",
        "checks": checks,
        "html_bytes": len(html_text.encode("utf-8")),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })
    print(json.dumps({"html": str(html_path), "md": str(md_path),
                      "selfcheck": str(selfcheck_path),
                      "pass": checks["pass"]}, ensure_ascii=False))
    return 0 if checks["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
