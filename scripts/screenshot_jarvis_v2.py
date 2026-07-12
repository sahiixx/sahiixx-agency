from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    
    # Go to dashboard on API port
    page.goto("http://127.0.0.1:8082/dashboard/")
    page.wait_for_timeout(3000)
    
    # Auto-login if needed
    if page.locator("text=SAHIIXX OS").count() > 0 and page.locator("input[type='password']").count() > 0:
        page.fill("input[type='email']", "admin@sahiixx.os")
        page.fill("input[type='password']", "sahiixx")
        page.click("button:has-text('LOGIN')")
        page.wait_for_timeout(3000)
    
    # Navigate to Device tab
    page.click("text=Device")
    page.wait_for_timeout(8000)  # Wait for SSE data to populate
    
    # Screenshot Overview with data
    page.screenshot(path="jarvis_overview_data.png", full_page=False)
    print("screenshot saved: jarvis_overview_data.png")
    
    # Click Voice tab with longer wait
    page.click("text=Voice")
    page.wait_for_timeout(5000)
    page.screenshot(path="jarvis_voice_tab.png", full_page=False)
    print("screenshot saved: jarvis_voice_tab.png")
    
    browser.close()
