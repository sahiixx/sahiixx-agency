from playwright.sync_api import sync_playwright
import time
import os

OUTPUT_DIR = r"C:\Users\sahii\sahiixx-agency\screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TABS = [
    ("overview", "Overview"),
    ("processes", "Processes"),
    ("services", "Services"),
    ("terminal", "Terminal"),
    ("voice", "Voice"),
    ("profiler", "Profiler"),
    ("updates", "Updates"),
    ("events", "Events"),
    ("hud", "HUD"),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1600, "height": 900})
    
    page.goto("http://127.0.0.1:8082/dashboard/")
    page.wait_for_timeout(3000)
    
    if page.locator("input[type='password']").count() > 0:
        page.fill("input[type='password']", "admin")
        page.click("button[type='submit']")
        page.wait_for_timeout(2000)
    
    # Navigate to Device using keyboard shortcut 6
    page.keyboard.press("6")
    page.wait_for_timeout(3000)
    
    for tab_id, tab_name in TABS:
        # Find button with exact text match
        buttons = page.locator("button").all()
        found = False
        for btn in buttons:
            text = btn.text_content()
            if text and text.strip() == tab_name:
                btn.click()
                page.wait_for_timeout(2000)
                found = True
                break
        if not found:
            print(f"Tab {tab_name} not found, skipping")
            continue
        
        path = os.path.join(OUTPUT_DIR, f"tab_{tab_id}.png")
        page.screenshot(path=path, full_page=False)
        print(f"Screenshot saved: {path}")
    
    # Also capture the HUD fullscreen
    hud_btn = page.locator("button:has-text('Launch Fullscreen')")
    if hud_btn.count() > 0:
        hud_btn.click()
        page.wait_for_timeout(2000)
        path = os.path.join(OUTPUT_DIR, "tab_hud_fullscreen.png")
        page.screenshot(path=path, full_page=False)
        print(f"Screenshot saved: {path}")
    
    browser.close()
    print("All screenshots captured!")
