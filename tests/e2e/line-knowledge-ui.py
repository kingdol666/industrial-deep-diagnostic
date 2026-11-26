"""Real browser + HTTP test. Run against a disposable authenticated localhost instance only.

Usage: shared-venv-python tests/e2e/line-knowledge-ui.py http://localhost:43267 [screenshot-dir]
The test creates synthetic folders, lines, pending jobs and one asset. It never executes a job.
"""
import argparse
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


def data(response):
    assert response.ok, f"{response.status} {urlsplit(response.url).path}: {response.text()}"
    envelope = response.json()
    assert envelope["success"], envelope.get("code")
    return envelope["data"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("disposable_url")
    parser.add_argument("screenshots", type=Path, nargs="?")
    args = parser.parse_args()
    base = args.disposable_url.rstrip("/")
    origin = urlsplit(base)
    if origin.scheme != "http" or origin.hostname not in {"localhost", "127.0.0.1"} or origin.port in {None, 3210, 5180}:
        parser.error("Use a disposable HTTP backend on a non-default loopback port")
    nonce = secrets.token_hex(4)
    line_name = f"Synthetic line {nonce}"
    title = f"Synthetic vibration {nonce}"
    synthetic_text = f"Synthetic test note {nonce}: verify sensor placement."
    folder_a, folder_b = (f"synthetic-{suffix}-{nonce}" for suffix in ("a", "b"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="en-US")
        context.set_default_timeout(8000)
        context.add_init_script("localStorage.setItem('idd.harness', 'claude'); localStorage.setItem('idd.locale', 'en');")
        executed = []
        context.on("request", lambda request: executed.append(request.url) if any(
            fragment in urlsplit(request.url).path for fragment in ("/diagnosis/execute/", "/diagnosis/stream/", "/diagnosis/continue/")) else None)
        page_errors = []

        def new_page():
            page = context.new_page()
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto(base, wait_until="domcontentloaded")
            return page

        http = context.request
        data(http.post(f"{base}/api/auth/register", data={"username": f"line_ui_{nonce}", "password": "Synthetic1-" + secrets.token_hex(12)}))
        user = data(http.get(f"{base}/api/auth/me"))["user"]
        for folder in (folder_a, folder_b):
            data(http.post(f"{base}/api/files/data/folder", headers={"Origin": base}, data={"name": folder}))
            data(http.post(f"{base}/api/files/data/upload?folder={folder}", headers={"Origin": base}, multipart={"files": {
                "name": "synthetic.csv", "mimeType": "text/csv", "buffer": b"time,value\n0,1\n1,2\n2,1\n",
            }}))

        page = new_page()
        page.get_by_test_id("nav-lines").click()
        expect(page.get_by_role("heading", name="Production lines", exact=True)).to_be_visible()

        def create_line():
            page.get_by_label("Line name", exact=True).fill(line_name)
            with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/api/lines")) as created:
                page.get_by_role("button", name="Create line", exact=True).click()
            return data(created.value)["line_id"]

        line_a, line_b = create_line(), create_line()
        assert line_a != line_b
        expect(page.locator(".line-list").get_by_role("button").filter(has_text=line_a)).to_be_visible()
        expect(page.locator(".line-list").get_by_role("button").filter(has_text=line_name)).to_have_count(2)

        def select_input(line, folder):
            page.get_by_test_id("nav-data").click()
            page.get_by_text(folder, exact=True).dblclick()
            page.get_by_role("button", name="Analyze Entire Folder", exact=True).click()
            page.get_by_role("combobox", name="Choose a line", exact=False).select_option(line)

        def create_run(line, policy, name):
            page.get_by_placeholder("Scene name", exact=False).fill(name)
            with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/api/diagnosis/start")) as started:
                page.get_by_role("button", name="Create pending job", exact=True).click()
            response = started.value
            run_id = data(response)["runId"]
            request = response.request.post_data_json
            assert request["lineId"] == line and request["knowledgePolicy"] == policy and request["datasetRefs"] == []
            expect(page.get_by_text("The job is pending.", exact=False)).to_be_visible()
            assert data(http.get(f"{base}/api/diagnosis/status/{run_id}"))["status"] == "pending"
            return run_id

        select_input(line_b, folder_b)
        create_run(line_b, {"mode": "disabled", "own_line": False, "references": []}, f"synthetic-b-{nonce}")
        page.get_by_test_id("nav-lines").click()
        page.locator(".line-list").get_by_role("button").filter(has_text=line_b).click()
        page.get_by_label("Title", exact=True).fill(title)
        page.get_by_label("Summary", exact=True).fill("Synthetic vibration example; no production data.")
        page.get_by_label("Content", exact=True).fill(synthetic_text)
        page.get_by_label("When it applies", exact=True).fill("Synthetic fixture only")
        with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith(f"/api/lines/{line_b}/assets")) as created:
            page.get_by_role("button", name="Save private draft", exact=True).click()
        asset = data(created.value)
        version = {"asset_id": asset["asset_id"], "version": asset["version"]}
        asset_path = f"/api/knowledge/assets/{version['asset_id']}/versions/{version['version']}"
        page.get_by_role("combobox", name="Visibility", exact=False).select_option("catalog")
        page.get_by_label("I checked this version", exact=False).check()
        page.get_by_role("button", name="Publish version", exact=True).click()
        expect(page.get_by_text("Version published.", exact=True)).to_be_visible()
        page.get_by_label("Recipient user ID", exact=True).fill(str(user["id"]))
        page.get_by_label("Reuse in diagnosis", exact=True).check()
        page.get_by_role("button", name="Save grant", exact=True).click()
        expect(page.get_by_text("Grant saved.", exact=True)).to_be_visible()
        if args.screenshots:
            page.screenshot(path=args.screenshots / "publication.png", full_page=True)

        select_input(line_a, folder_a)
        page.get_by_role("combobox", name="Knowledge policy", exact=False).select_option("on_demand")
        page.get_by_label("Include eligible knowledge from this line", exact=True).uncheck()
        page.get_by_text("Knowledge catalog · 0", exact=True).click()
        catalog = page.get_by_role("region", name="Knowledge catalog", exact=True)
        catalog.get_by_role("searchbox").fill(nonce)
        catalog.get_by_role("button", name="Search", exact=True).click()
        catalog.get_by_role("listitem").filter(has_text=title).get_by_role("button", name="Select experience version", exact=True).click()
        run_a = create_run(line_a, {"mode": "on_demand", "own_line": False, "references": [version]}, f"synthetic-a-{nonce}")
        expect(page.get_by_role("button", name="Execute pending job", exact=True)).to_be_disabled()
        expect(page.get_by_text("Execution with shared references", exact=False)).to_be_visible()
        panel = page.get_by_role("region", name="Run knowledge", exact=True)
        panel.get_by_role("searchbox").fill("vibration")
        panel.get_by_role("button", name="Search preview", exact=True).click()
        expect(panel.get_by_text(title, exact=True)).to_be_visible()
        panel.get_by_role("button", name="Verify and view details", exact=True).click()
        expect(panel.get_by_text(synthetic_text, exact=True)).to_be_visible()
        expect(panel.get_by_text("Console preview: Retrieved", exact=True)).to_be_visible()
        expect(panel.get_by_text("Agent retrieval: Not retrieved", exact=True)).to_be_visible()
        if args.screenshots:
            page.screenshot(path=args.screenshots / "pending-preview.png", full_page=True)

        manager = new_page()
        manager.get_by_test_id("nav-lines").click()
        manager.locator(".line-list").get_by_role("button").filter(has_text=line_b).click()
        manager.get_by_text("Manage an existing version by ID", exact=True).click()
        manager.get_by_label("Asset ID", exact=True).fill(version["asset_id"])
        manager.get_by_label("Version number", exact=True).fill(str(version["version"]))
        manager.get_by_role("button", name="Open version controls", exact=True).click()
        manager.get_by_label("Block future reads", exact=False).check()
        with manager.expect_response(lambda r: r.url.endswith(f"{asset_path}/withdraw")) as withdrawn:
            manager.get_by_role("button", name="Withdraw version", exact=True).click()
        data(withdrawn.value)
        expect(manager.get_by_text("Version withdrawn.", exact=True)).to_be_visible()
        expect(manager.get_by_role("region", name="Knowledge catalog", exact=True).get_by_text(title, exact=True)).to_have_count(0)

        panel.get_by_role("button", name="Verify and view details", exact=True).click()
        expect(panel.get_by_role("alert").get_by_text("This item or preview is no longer available or authorized.", exact=True)).to_be_visible()
        expect(panel.get_by_text(synthetic_text, exact=True)).to_have_count(0)
        panel.get_by_role("button", name="Recheck last search", exact=True).click()
        expect(panel.get_by_text("No matches in the currently authorized sources.", exact=False)).to_be_visible()
        audits = data(http.get(f"{base}/api/knowledge/runs/{run_a}/retrievals"))["items"]
        assert all(row["channel"] == "preview" for row in audits), audits
        assert any(row["outcome"] == "KNOWLEDGE_ITEM_NOT_FOUND" for row in audits), audits
        assert any(row["outcome"] == "ok" and row["item_count"] == 1 and row["refs"][0]["source_version"] == str(version["version"]) for row in audits), audits
        assert data(http.get(f"{base}/api/diagnosis/status/{run_a}"))["status"] == "pending"
        assert not executed, executed

        page.locator(".app-lang-toggle").click()
        expect(page.get_by_role("region", name="作业知识", exact=True).get_by_role("heading", name="授权预览", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="执行待运行作业", exact=True)).to_be_disabled()
        if args.screenshots:
            page.screenshot(path=args.screenshots / "withdrawn-preview-zh.png", full_page=True)
        assert not page_errors, page_errors
        browser.close()
        print("PASS: same-name lines, two pending jobs, publication/grant, pinned preview/audit, withdrawal, zh/en; no execution requests")


if __name__ == "__main__":
    main()
