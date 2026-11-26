"""Exercise the same human review from Results, Reports and Line Memory."""
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

base, username, password, workspace_name = sys.argv[1:5]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="chrome")
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    response = context.request.post(f"{base}/api/auth/login", data={"username": username, "password": password})
    assert response.ok, response.status
    page = context.new_page()
    page.goto(base, wait_until="networkidle")
    page.get_by_test_id("nav-results").click()
    page.get_by_test_id("results-search").fill("hitl-browser-source")
    page.get_by_test_id("results-detail-btn-0").click()
    panel = page.get_by_test_id("human-review")
    status = panel.get_by_test_id("review-status")
    expect(status).to_have_value("unreviewed")
    status.select_option("confirmed")
    panel.get_by_test_id("review-comment").fill("复测后缺陷率下降")
    panel.get_by_test_id("review-takeaway").fill("先核对测温校准")
    panel.get_by_test_id("review-save").click()
    expect(panel.get_by_test_id("review-synthesis")).to_contain_text("复测后缺陷率下降")
    expect(panel.get_by_role("status")).to_have_text("已保存")
    page.get_by_test_id("results-report-btn-0").click()
    expect(page.get_by_test_id("report-body")).to_contain_text("浏览器验收原始报告")
    expect(status).to_have_value("confirmed")
    panel.get_by_test_id("review-summary").fill("人工复核：核对测温校准后再验证")
    panel.get_by_test_id("review-save").click()
    expect(panel.get_by_test_id("review-synthesis")).to_contain_text("人工复核：核对测温校准后再验证")
    page.get_by_test_id("nav-memory").click()
    page.get_by_test_id("lm-open-reviewed").click()
    page.get_by_role("button", name="hitl-browser-source", exact=True).click()
    expect(status).to_have_value("confirmed")
    panel.get_by_test_id("review-undo").click()
    expect(status).to_have_value("unreviewed")
    status.select_option("ineffective")
    panel.get_by_test_id("review-comment").fill("对照批次未复现")
    panel.get_by_test_id("review-save").click()
    expect(panel.get_by_test_id("review-synthesis")).to_contain_text("对照批次未复现")
    panel.get_by_test_id("review-history").click()
    expect(panel.locator("li")).to_have_count(4)
    page.get_by_test_id("lm-review-filter").select_option("ineffective")
    expect(page.get_by_role("button", name="hitl-browser-source", exact=True)).to_be_visible()
    if len(sys.argv) > 5:
        page.get_by_role("button", name="hitl-browser-source", exact=True).click()
        expect(status).to_have_value("ineffective")
        page.screenshot(path=str(Path(sys.argv[5])), full_page=True)
    browser.close()
    print(f"PASS: Results → Reports ({workspace_name}) → Memory; confirm, edit, undo, reject, retain, history")
