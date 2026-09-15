"""Capture the running console UI as PNGs.

Two consumers:

  1. Design review — `--set review` writes every page plus a responsive sweep
     to .runtime/ui-shots/, and reports any console error it saw.
  2. README assets — `--set readme` drives the console into *populated* states
     (a real diagnostic report open, a real ontology asset selected) and writes
     the curated, named set straight into docs/screenshots/.

Usage
-----
    python scripts/capture-ui-shots.py --set review
    python scripts/capture-ui-shots.py --set readme
    python scripts/capture-ui-shots.py --set readme --base http://127.0.0.1:5180

Requires a running frontend. Playwright + chromium must be importable.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

from playwright.sync_api import sync_playwright

USER = os.environ.get("IDD_USER", "ontoadmin")
PASSWORD = os.environ.get("IDD_PASSWORD", "OntoAdmin123!")

# Pages are addressed by the tab's i18n label. Both locales are listed so the
# script works whichever language the console opens in.
PAGES = [
    ("data", ["数据", "Data"]),
    ("diagnose", ["诊断", "Diagnose"]),
    ("chat", ["对话", "Chat"]),
    ("reports", ["报告", "Reports"]),
    ("ontology", ["本体", "Ontology"]),
    ("history", ["历史", "History"]),
]

RESPONSIVE = [
    ("1920x1080", 1920, 1080),
    ("1440x900", 1440, 900),
    ("1280x800", 1280, 800),
    ("1024x768", 1024, 768),
    ("900x600", 900, 600),
    ("768x1024", 768, 1024),
    ("390x844", 390, 844),
]

# Below this width the sidebar reflows from a vertical rail to a top band.
BAND_BREAKPOINT = 900

# Real runs in this workspace, used to open a populated report / ontology asset
# so the README shows a finished diagnosis rather than an empty viewer.
REPORT_RUN = "202609141511399"        # SKAB valve1 — COMPETING_SET, honest cap
ONTOLOGY_SCENE = "Tennessee_Eastman"  # the richest asset in the store

# The ontology list has been restructured more than once; try each handle.
ONTOLOGY_ITEM_SELECTORS = [
    ".onto-asset-item", ".asset-item", ".asset-row",
    ".onto-list-item", ".onto-scene", ".ip-row",
]


def slug(text: str) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text).strip("-").lower()
    return text or "page"


def login(page, base: str) -> None:
    page.goto(base, wait_until="domcontentloaded")
    page.wait_for_timeout(1800)
    if page.locator(".auth-submit").count():
        page.locator("input").first.fill(USER)
        page.locator("input[type='password']").first.fill(PASSWORD)
        page.locator(".auth-submit").first.click()
        page.wait_for_timeout(3800)


def goto_tab(page, labels) -> str | None:
    """Click the nav item whose label matches, return the label that worked."""
    for label in labels:
        item = page.locator(".app-nav-item", has_text=label)
        if item.count():
            item.first.click()
            page.wait_for_timeout(1700)
            return label
    return None


def audit_shell(page) -> dict:
    """Measure the shell for band overlap / page overflow at the current size."""
    return page.evaluate(
        """
        () => {
          const r = (s) => { const el = document.querySelector(s); return el ? el.getBoundingClientRect() : null; };
          const sb = r('.app-sidebar'), body = r('.app-body'),
                top = r('.app-topbar'), content = r('.app-content');
          const stacked = window.innerWidth <= %d;
          return {
            stacked,
            vw: window.innerWidth, vh: window.innerHeight,
            sidebarW: sb ? Math.round(sb.width) : null,
            sidebarH: sb ? Math.round(sb.height) : null,
            // positive = the two bands overlap; must be <= 0 in both layouts
            separation: (sb && body)
              ? Math.round((stacked ? (sb.bottom - body.top) : (sb.right - body.left)) * 100) / 100
              : null,
            headerContentOverlap: (top && content) ? Math.round((top.bottom - content.top) * 100) / 100 : null,
            hPageOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
            vPageOverflow: document.documentElement.scrollHeight > window.innerHeight + 1,
          };
        }
        """ % BAND_BREAKPOINT
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["review", "readme"], default="review")
    ap.add_argument("--base", default="http://127.0.0.1:5180")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    readme = args.set == "readme"
    out = args.out or ("docs/screenshots" if readme else ".runtime/ui-shots")
    viewport = {"width": 1680, "height": 1000} if readme else {"width": 1440, "height": 900}

    os.makedirs(out, exist_ok=True)
    errors: list[str] = []
    bad_responses: list[str] = []
    written: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=viewport, device_scale_factor=2 if readme else 1)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: errors.append(f"console.error: {m.text}") if m.type == "error" else None)
        # A console "401" says a request failed but not which one — record the
        # URL too, so a genuinely unauthenticated call is distinguishable from
        # a benign probe.
        page.on(
            "response",
            lambda r: bad_responses.append(f"HTTP {r.status} {r.request.method} {r.url}")
            if r.status >= 400 else None,
        )

        # ── login screen (captured before authenticating) ──
        page.goto(args.base, wait_until="domcontentloaded")
        page.wait_for_timeout(2200)
        path = f"{out}/01-access.png" if readme else f"{out}/login.png"
        page.screenshot(path=path)
        written.append(path)

        login(page, args.base)

        # ── one shot per page ──
        for idx, (key, labels) in enumerate(PAGES):
            if not goto_tab(page, labels):
                print(f"  ! tab not found: {key} ({'/'.join(labels)})", file=sys.stderr)
                continue

            if readme and key == "reports":
                # open a finished run so the viewer shows a real report
                run = page.locator(".run-item", has_text=REPORT_RUN)
                if run.count():
                    run.first.click()
                    page.wait_for_timeout(4200)
                else:
                    print(f"  ! report run {REPORT_RUN} not listed", file=sys.stderr)

            if readme and key == "ontology":
                # select the richest asset so the graph + inspector are populated
                clicked = False
                for sel in ONTOLOGY_ITEM_SELECTORS:
                    loc = page.locator(sel)
                    for i in range(min(loc.count(), 12)):
                        try:
                            if ONTOLOGY_SCENE.lower() in (loc.nth(i).inner_text() or "").lower():
                                loc.nth(i).click()
                                page.wait_for_timeout(4500)
                                clicked = True
                                break
                        except Exception:
                            continue
                    if clicked:
                        print(f"    ontology asset selected via {sel}")
                        break
                if not clicked:
                    print("  ! ontology asset not selectable; capturing default state", file=sys.stderr)

            name = f"{idx + 2:02d}-{key}.png" if readme else f"page-{key}.png"
            path = f"{out}/{name}"
            page.screenshot(path=path)
            written.append(path)

        # engine-runs tab, when the active engine exposes one
        nav_count = page.locator(".app-nav-item").count()
        if nav_count > len(PAGES):
            page.locator(".app-nav-item").nth(nav_count - 1).click()
            page.wait_for_timeout(1900)
            name = "08-engine-runs.png" if readme else "page-engine-runs.png"
            path = f"{out}/{name}"
            page.screenshot(path=path)
            written.append(path)

            if readme:
                # a run detail is the most information-dense view in the product
                card = page.locator(".omp-run-card")
                if card.count():
                    card.first.click()
                    page.wait_for_timeout(3200)
                    path = f"{out}/09-engine-run-detail.png"
                    page.screenshot(path=path)
                    written.append(path)

        # ── responsive ──
        if readme:
            # phone: the command bar with the nav drawer open
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(900)
            path = f"{out}/10-phone.png"
            page.screenshot(path=path)
            written.append(path)
            toggle = page.locator(".app-nav-toggle")
            if toggle.count():
                toggle.first.click()
                page.wait_for_timeout(800)
                path = f"{out}/11-phone-nav.png"
                page.screenshot(path=path)
                written.append(path)
        else:
            print(f"{'viewport':11} {'layout':6} {'sbW':>5} {'sbH':>5} {'sep':>7} {'hdrOv':>7} {'hOvfl':>6} {'vOvfl':>6}")
            for label, w, h in RESPONSIVE:
                page.set_viewport_size({"width": w, "height": h})
                page.wait_for_timeout(750)
                d = audit_shell(page)
                flag = "" if (d["separation"] or 0) <= 0 and not d["hPageOverflow"] else "  <-- DEFECT"
                print(
                    f"{label:11} {('band' if d['stacked'] else 'rail'):6} {str(d['sidebarW']):>5} {str(d['sidebarH']):>5} "
                    f"{str(d['separation']):>7} {str(d['headerContentOverlap']):>7} "
                    f"{str(d['hPageOverflow']):>6} {str(d['vPageOverflow']):>6}{flag}"
                )
                path = f"{out}/responsive-{label}.png"
                page.screenshot(path=path)
                written.append(path)

        browser.close()

    print(f"\n{len(written)} shots -> {out}/")
    for w in written:
        print(f"  {w}")
    if bad_responses:
        print(f"\n{len(bad_responses)} failing HTTP response(s):", file=sys.stderr)
        for r in dict.fromkeys(bad_responses):
            print(f"  {r}", file=sys.stderr)
    if errors:
        print(f"\n{len(errors)} console error(s):", file=sys.stderr)
        for e in dict.fromkeys(errors):
            print(f"  {e}", file=sys.stderr)
    else:
        print("console errors: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
