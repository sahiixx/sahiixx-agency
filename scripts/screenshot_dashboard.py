from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1600, "height": 900})
    page.goto("http://127.0.0.1:3000")
    page.wait_for_timeout(5000)
    page.screenshot(path="dashboard_screenshot.png", full_page=False)
    browser.close()
    print("screenshot saved: dashboard_screenshot.png")
