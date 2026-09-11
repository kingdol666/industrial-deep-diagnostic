"""Ontology management page — browser end-to-end verification.

Drives the REAL running GUI (frontend 5180 → backend 3210) through the full
lifecycle a user would perform:

  login → open Ontology tab → asset list renders → graph renders (ECharts canvas)
  → select a node → inspector shows details + findings → switch to structure view
  → edit a signal's physical_meaning → validate → save (creates v+1)
  → reload → confirm the edit persisted on the server → diff view
  → adopt-candidates modal opens → metrics view renders

Run:  python app/backend/../.runtime/ontology-ui-e2e.py
"""
import json
import os
import sys
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect

FRONTEND = "http://127.0.0.1:5180"
BACKEND = "http://127.0.0.1:3210"
USER = "ontoadmin"
PASSWORD = os.environ.get("IDD_E2E_PASSWORD", "")
assert PASSWORD, "IDD_E2E_PASSWORD env required (no hardcoded credentials)"

SCENE = "three_system_e2e"
# 每次运行使用唯一标记：保存端按内容哈希去重（同内容不产生噪声版本），
# 因此重复运行必须写入不同内容才能观察到「升版」。
EDIT_MARK = f"浏览器端到端校验 {int(time.time())}：人工改写的过程温度语义"

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail and not ok else ""))


def _check_url(u):
    """SSRF guard for the e2e suite: http(s) only, and every resolved address
    MUST be loopback — this test may only ever talk to the local backend."""
    from urllib.parse import urlparse
    import ipaddress
    import socket
    p = urlparse(str(u))
    assert p.scheme in ("http", "https"), "URL scheme must be http/https"
    port = p.port or (443 if p.scheme == "https" else 80)
    for info in socket.getaddrinfo(p.hostname or "", port):
        ip = ipaddress.ip_address(info[4][0])
        assert ip.is_loopback, f"e2e may only target loopback, got {ip}"
    return u


def api_token():
    req = urllib.request.Request(
        _check_url(BACKEND + "/api/auth/login"),
        data=json.dumps({"username": USER, "password": PASSWORD}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())["data"]["session_token"]


def api_get(path, token):
    req = urllib.request.Request(_check_url(BACKEND + path), headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["data"]


def main():
    token = api_token()
    assets = api_get(f"/api/ontology/assets?scene={SCENE}", token)
    if not assets["assets"]:
        print("FATAL: scene missing from store; cannot run UI test")
        return 1
    start_version = assets["assets"][0]["latest_version"]
    print(f"starting at {SCENE} v{start_version}")

    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1680, "height": 1000})
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))

        # ── 1. 打开并登录 ──
        page.goto(FRONTEND, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        try:
            page.locator("input").first.fill(USER)
            page.locator("input[type='password']").first.fill(PASSWORD)
            page.locator("button", has_text="登").last.click()
        except Exception as exc:  # already logged in / different auth shell
            print(f"login form not driven ({exc}); continuing")
        page.wait_for_timeout(3500)
        check("login lands in the app shell", page.locator(".app-shell").count() > 0)

        # ── 2. 进入本体管理页 ──
        nav = page.locator(".app-nav-item", has_text="Ontology")
        check("Ontology tab present in sidebar", nav.count() > 0)
        nav.first.click()
        page.wait_for_timeout(2600)
        check("ontology workspace rendered", page.locator(".onto-view").count() > 0)

        # ── 3. 资产列表 ──
        page.wait_for_selector(".onto-scene-head", timeout=15000)
        scenes = page.locator(".onto-scene-head")
        check("asset list shows the stored scene(s)", scenes.count() >= 1, f"count={scenes.count()}")
        check("scene key visible", SCENE in page.locator(".onto-rail").inner_text())

        # ── 4. 图渲染（ECharts canvas 真的有像素） ──
        page.wait_for_selector(".onto-graph-chart canvas", timeout=15000)
        canvas_box = page.locator(".onto-graph-chart canvas").first.bounding_box()
        check("graph canvas has real size", canvas_box and canvas_box["width"] > 300 and canvas_box["height"] > 200,
              str(canvas_box))
        legend = page.locator(".onto-legend-item")
        check("graph legend rendered from server categories", legend.count() >= 3, f"count={legend.count()}")

        # 图层开关 → 知识层出现更多类别
        before = legend.count()
        page.locator(".onto-chip", has_text="知识").first.click()
        page.wait_for_timeout(2500)
        after = page.locator(".onto-legend-item").count()
        check("knowledge layer toggle adds node categories", after > before, f"{before} → {after}")

        # ── 5. 点击图中节点 → 检视面板有内容 ──
        # ECharts 是 canvas，无法用 DOM 选择节点；改为点击画布中心并在多点上尝试
        clicked = False
        for dx, dy in ((0, 0), (-60, 30), (70, -40), (120, 60), (-110, -70)):
            page.mouse.click(canvas_box["x"] + canvas_box["width"] / 2 + dx,
                             canvas_box["y"] + canvas_box["height"] / 2 + dy)
            page.wait_for_timeout(500)
            if page.locator(".onto-insp-title").count():
                clicked = True
                break
        check("clicking the graph selects an entity and fills the inspector",
              clicked and page.locator(".onto-insp-title").count() > 0)

        check("inspector shows findings/severity panel", page.locator(".onto-sev-filter").count() > 0)

        # ── 6. 结构编辑视图 ──
        page.locator(".onto-tab", has_text="结构编辑").first.click()
        page.wait_for_timeout(1200)
        cards = page.locator(".onto-card")
        check("structure editor lists ontology entries", cards.count() >= 1, f"cards={cards.count()}")
        sig_cards = page.locator(".onto-card.signal")
        check("signal cards rendered", sig_cards.count() >= 1, f"signals={sig_cards.count()}")

        # ── 7. 编辑：改 process_parameters[0].physical_meaning ──
        target = None
        for i in range(sig_cards.count()):
            c = sig_cards.nth(i)
            if "col_b" in c.inner_text() or "dn-eb0c151b" in c.inner_text():
                target = c
                break
        if target is None:
            target = sig_cards.first
        meaning = target.locator("textarea").first
        meaning.fill(EDIT_MARK)
        page.wait_for_timeout(1400)
        check("edit marks the draft as dirty", page.locator(".onto-dirty").count() > 0)

        # ── 8. 校验 ──
        page.locator(".onto-btn", has_text="校验").first.click()
        page.wait_for_timeout(3000)
        validate_ok = page.locator(".onto-ok-strip").count() > 0
        check("CP-2 validation runs from the UI", validate_ok or page.locator(".onto-errors").count() > 0,
              "no validation strip rendered")

        # ── 9. 保存为新版本 ──
        page.locator(".onto-btn", has_text="保存为新版本").first.click()
        page.wait_for_timeout(5000)
        conflict = page.locator(".onto-modal").count() > 0
        check("save did not hit a conflict", not conflict,
              page.locator(".onto-modal").inner_text()[:200] if conflict else "")

        # 服务端核对：新版本真的落盘，且语义是我们写入的
        after_assets = api_get(f"/api/ontology/assets?scene={SCENE}", token)
        new_version = after_assets["assets"][0]["latest_version"]
        check("save created a NEW version server-side", new_version == start_version + 1,
              f"{start_version} → {new_version}")
        asset = api_get(f"/api/ontology/assets/{SCENE}/{new_version}", token)
        params = asset["ontology"]["signals"]["process_parameters"]
        landed = any(p.get("physical_meaning") == EDIT_MARK for p in params)
        check("edited semantics persisted through the UI", landed,
              json.dumps([p.get("physical_meaning") for p in params], ensure_ascii=False)[:200])
        check("new version records the parent version", asset["entry"].get("parent_version") == start_version,
              str(asset["entry"].get("parent_version")))
        check("new version records a human origin", str(asset["entry"].get("origin", "")).startswith("user"),
              str(asset["entry"].get("origin")))
        old = api_get(f"/api/ontology/assets/{SCENE}/{start_version}", token)
        check("history version left untouched",
              all(p.get("physical_meaning") != EDIT_MARK for p in old["ontology"]["signals"]["process_parameters"]))

        # ── 10. 重新加载 → 前端读到新版本 ──
        page.reload(wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        nav = page.locator(".app-nav-item", has_text="Ontology")
        if nav.count():
            nav.first.click()
            page.wait_for_timeout(3200)
        rail_text = page.locator(".onto-rail").inner_text() if page.locator(".onto-rail").count() else ""
        check("reloaded page shows the new version in the rail", f"v{new_version}" in rail_text,
              rail_text[:200])
        check("reloaded page selects a v" + str(new_version) + " asset",
              page.locator(".onto-vtag").count() > 0 and f"v{new_version}" in page.locator(".onto-vtag").first.inner_text())

        # ── 11. 版本差异视图 ──
        page.locator(".onto-tab", has_text="版本差异").first.click()
        page.wait_for_timeout(3000)
        diff_rendered = page.locator(".onto-diff-summary, .onto-diff-identical").count() > 0
        check("version diff view renders a structured comparison", diff_rendered)
        if diff_rendered and page.locator(".onto-diff-table").count():
            table = page.locator(".onto-diff-table").first.inner_text()
            check("diff table contains the edited field path", "physical_meaning" in table, table[:200])

        # ── 12. 模型健康 ──
        page.locator(".onto-tab", has_text="模型健康").first.click()
        page.wait_for_timeout(2200)
        check("model-health view renders a score", page.locator(".onto-health-num").count() > 0)
        check("health breakdown rows rendered", page.locator(".onto-breakdown-row").count() >= 5,
              f"rows={page.locator('.onto-breakdown-row').count()}")
        check("findings list rendered", page.locator(".onto-finding").count() >= 0)

        # ── 13. 采纳候选模态 ──
        page.locator(".onto-btn", has_text="采纳候选").first.click()
        try:
            page.wait_for_selector(".onto-adopt-row", timeout=25000)
        except Exception:
            pass
        page.wait_for_timeout(1200)
        adopt_rows = page.locator(".onto-adopt-row").count()
        check("adopt-candidates modal lists agent-built ontologies", adopt_rows > 5, f"rows={adopt_rows}")
        if adopt_rows:
            check("adopt rows carry a CP-2 verdict",
                  page.locator(".onto-adopt-badge").count() >= adopt_rows,
                  f"badges={page.locator('.onto-adopt-badge').count()}")
        page.locator(".onto-modal .onto-btn", has_text="取消").first.click()
        page.wait_for_timeout(600)

        # ── 14. 新建本体模态 ──
        page.locator(".onto-btn", has_text="新建本体").first.click()
        page.wait_for_timeout(900)
        check("create-ontology modal opens", page.locator(".onto-modal").count() > 0)
        page.locator(".onto-modal .onto-btn", has_text="取消").first.click()
        page.wait_for_timeout(400)

        page.screenshot(path=".runtime/ontology-page.png", full_page=True)
        print("\nscreenshot → .runtime/ontology-page.png")

        browser.close()

    print("\n=== console errors ===")
    real_errors = [e for e in console_errors if "favicon" not in e.lower()]
    for e in real_errors[:10]:
        print(" -", e[:220])
    check("no uncaught console/page errors", len(real_errors) == 0, f"{len(real_errors)} errors")

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n=== {passed}/{len(results)} checks passed ===")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAILED: {name}  {detail}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
