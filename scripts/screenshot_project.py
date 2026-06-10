"""Log in as the QA user and screenshot a project page.

Usage: python scripts/screenshot_project.py [project_id] [out_path]
"""

import sys

from playwright.sync_api import sync_playwright

PROJECT_ID = sys.argv[1] if len(sys.argv) > 1 else "3"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/project_screenshot.png"
USERNAME = "qa_admin"
PASSWORD = "QaTest!2026"
BASE = "http://localhost:3000"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_context(viewport={"width": 1280, "height": 1600}).new_page()

    # 1. Log in
    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.wait_for_selector("input", timeout=15000)
    page.locator("input:not([type=password])").first.fill(USERNAME)
    page.locator("input[type=password]").first.fill(PASSWORD)
    page.get_by_role("button", name="Sign in").click()

    # 2. Wait for redirect away from /login (auth_token lands in LocalStorage)
    try:
        page.wait_for_url(lambda u: "/login" not in u, timeout=15000)
    except Exception:
        pass
    page.wait_for_timeout(1500)

    # 3. Open the project page and let media load
    page.goto(f"{BASE}/project/{PROJECT_ID}", wait_until="networkidle")
    page.wait_for_timeout(3500)

    page.screenshot(path=OUT, full_page=True)
    print(f"saved {OUT}; final url={page.url}")
    browser.close()
