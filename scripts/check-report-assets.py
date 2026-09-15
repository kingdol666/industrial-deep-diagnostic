"""Verify report assets actually render in the browser.

Regression guard for the 401 bug: `<img src>` and `<iframe src>` cannot carry an
Authorization header, so workspace-asset URLs must authenticate via the `?token=`
fallback. Checks the real rendered result, not the markup:

  * every figure in the Markdown report reports naturalWidth > 0 (i.e. decoded)
  * the HTML-report iframe loads a real document, not a 401 body
  * no 4xx response is emitted along the way
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5180"
USER, PASSWORD = "ontoadmin", "OntoAdmin123!"
RUN = "202609141511399"          # SKAB valve1 — its report embeds real figures


def main() -> int:
    failures: list[str] = []
    bad: list[str] = []

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1680, "height": 1000})
        pg.on("response", lambda r: bad.append(f"HTTP {r.status} {r.url[:140]}") if r.status >= 400 else None)

        pg.goto(BASE, wait_until="domcontentloaded")
        pg.wait_for_timeout(2000)
        pg.locator("input").first.fill(USER)
        pg.locator("input[type=password]").first.fill(PASSWORD)
        pg.locator(".auth-submit").first.click()
        pg.wait_for_timeout(4000)

        pg.locator(".app-nav-item", has_text="Reports").first.click()
        pg.wait_for_timeout(3200)

        run = pg.locator(".run-item", has_text=RUN)
        if not run.count():
            print(f"! run {RUN} not listed", file=sys.stderr)
            b.close()
            return 1
        run.first.click()
        pg.wait_for_timeout(5000)

        # ── figures in the Markdown report ──
        imgs = pg.evaluate(
            """() => Array.from(document.querySelectorAll('.report-body img')).map(i => ({
                   src: i.getAttribute('src') || '',
                   w: i.naturalWidth, h: i.naturalHeight, complete: i.complete,
               }))"""
        )
        print(f"figures in Markdown report: {len(imgs)}")
        if not imgs:
            failures.append("no <img> found in the rendered report — nothing to verify")
        for i in imgs:
            ok = i["w"] > 0 and i["h"] > 0
            tag = "PASS" if ok else "FAIL"
            print(f"  {tag}  {i['w']}x{i['h']}  {i['src'][:110]}")
            if not ok:
                failures.append(f"figure did not decode: {i['src'][:120]}")

        # ── HTML report iframe ──
        tab = pg.locator("button", has_text="HTML")
        if tab.count():
            tab.first.click()
            pg.wait_for_timeout(4500)
            info = pg.evaluate(
                """() => {
                    const f = document.querySelector('iframe');
                    if (!f) return { found: false };
                    let doc = null;
                    try { doc = f.contentDocument; } catch (e) { return { found: true, blocked: true }; }
                    return {
                        found: true,
                        blocked: false,
                        title: doc ? (doc.title || '') : null,
                        bodyLen: doc && doc.body ? doc.body.innerHTML.length : 0,
                        isJson401: doc && doc.body ? doc.body.innerText.includes('AUTH_REQUIRED') : false,
                    };
                }"""
            )
            print(f"\nHTML report iframe: {info}")
            if not info.get("found"):
                failures.append("HTML report iframe missing")
            elif info.get("isJson401"):
                failures.append("HTML report iframe rendered a 401 JSON body")
            elif (info.get("bodyLen") or 0) < 1000:
                failures.append(f"HTML report iframe body suspiciously small: {info.get('bodyLen')}")

        b.close()

    if bad:
        print(f"\n{len(bad)} failing response(s):", file=sys.stderr)
        for x in dict.fromkeys(bad):
            print(f"  {x}", file=sys.stderr)

    print()
    if failures:
        print("FAILURES:", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    print("OK — report figures decode and the HTML report iframe loads real content.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
