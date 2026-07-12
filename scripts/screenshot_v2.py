from playwright.sync_api import sync_playwright
import os

OUTPUT_DIR = r"C:\Users\sahii\sahiixx-agency\screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1600, "height": 900})
    
    page.goto("http://127.0.0.1:8082/dashboard/")
    page.wait_for_timeout(3000)
    
    if page.locator("input[type='password']").count() > 0:
        page.fill("input[type='password']", "admin")
        page.click("button[type='submit']")
        page.wait_for_timeout(2000)
    
    # Navigate to Device
    page.keyboard.press("6")
    page.wait_for_timeout(3000)
    
    # Screenshot Overview tab (should have heatmap + process tree now)
    page.screenshot(path=os.path.join(OUTPUT_DIR, "tab_overview_v2.png"))
    print("Overview v2 saved")
    
    # Click Processes tab
    for btn in page.locator("button").all():
        if btn.text_content() and btn.text_content().strip() == "Processes":
            btn.click()
            page.wait_for_timeout(2000)
            break
    page.screenshot(path=os.path.join(OUTPUT_DIR, "tab_processes_v2.png"))
    print("Processes v2 saved")
    
    # Click HUD tab and launch fullscreen
    for btn in page.locator("button").all():
        if btn.text_content() and btn.text_content().strip() == "HUD":
            btn.click()
            page.wait_for_timeout(1500)
            break
    page.screenshot(path=os.path.join(OUTPUT_DIR, "tab_hud_v2.png"))
    print("HUD v2 saved")
    
    # Launch fullscreen HUD
    hud_btn = page.locator("button:has-text('Launch Fullscreen')")
    if hud_btn.count() > 0:
        hud_btn.click()
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "tab_hud_fullscreen_v2.png"))
        print("HUD fullscreen v2 saved")
    
    browser.close()
    print("All screenshots done!")
