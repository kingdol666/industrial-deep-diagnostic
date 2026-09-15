"""Render every ```mermaid block from the READMEs with the real mermaid parser.

GitHub renders mermaid natively, and a syntax error shows up as an ugly red
error box in the published README. This pulls each block out, feeds it to
mermaid.js in a real browser, and reports parse failures plus the SVG node
count so a silently-empty diagram is caught too.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

MERMAID_RE = re.compile(r"```mermaid\n(.*?)```", re.S)
CDN = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"


def main() -> int:
    blocks: list[tuple[str, int, str]] = []
    for f in ("README.md", "README-zh.md"):
        text = Path(f).read_text(encoding="utf-8")
        for i, b in enumerate(MERMAID_RE.findall(text), 1):
            blocks.append((f, i, b.strip()))

    print(f"found {len(blocks)} mermaid block(s)\n")

    html = """<!doctype html><html><body><div id="out"></div>
<script src="%s"></script>
<script>
window.run = async (sources) => {
  mermaid.initialize({ startOnLoad: false, theme: 'dark' });
  const results = [];
  for (const src of sources) {
    try {
      await mermaid.parse(src);              // throws on syntax error
      const { svg } = await mermaid.render('g' + results.length, src);
      const nodes = (svg.match(/class="[^"]*node[^"]*"/g) || []).length;
      const edges = (svg.match(/class="[^"]*edge[^"]*"/g) || []).length;
      results.push({ ok: true, nodes, edges, len: svg.length });
    } catch (e) {
      results.push({ ok: false, error: String(e && e.message || e).slice(0, 300) });
    }
  }
  return results;
};
</script></body></html>""" % CDN

    ok = True
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        page.wait_for_function("() => typeof window.run === 'function'", timeout=30000)

        results = page.evaluate("sources => window.run(sources)", [b[2] for b in blocks])
        browser.close()

    for (fname, idx, _), r in zip(blocks, results):
        label = f"{fname} block #{idx}"
        if r.get("ok"):
            print(f"  PASS  {label:28} nodes={r['nodes']:<4} edges={r['edges']:<4} svg={r['len']}B")
            if r["nodes"] == 0:
                print(f"        ! parsed but rendered 0 nodes — diagram may be empty")
                ok = False
        else:
            ok = False
            print(f"  FAIL  {label}\n        {r.get('error')}")

    print()
    print("all mermaid diagrams render" if ok else "MERMAID ERRORS PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
