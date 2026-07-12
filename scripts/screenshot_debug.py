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
    
    # Save screenshot of initial state
    page.screenshot(path=os.path.join(OUTPUT_DIR, "debug_initial.png"))
    
    # Try to find and click Device
    print("Looking for Device link...")
    all_links = page.locator("a").all()
    for i, link in enumerate(all_links):
        text = link.text_content()
        if text and "Device" in text:
            print(f"Found link {i}: '{text}'")
            link.click()
            page.wait_for_timeout(3000)
            break
    else:
        print("No Device link found, trying keyboard shortcut")
        page.keyboard.press("6")
        page.wait_for_timeout(3000)
    
    # Save debug screenshot
    page.screenshot(path=os.path.join(OUTPUT_DIR, "debug_after_device.png"))
    
    # Print all buttons on page
    all_buttons = page.locator("button").all()
    print(f"Found {len(all_buttons)} buttons:")
    for btn in all_buttons:
        text = btn.text_content()
        if text:
            print(f"  - '{text.strip()}'")
    
    browser.close()
    print("Debug screenshots saved!")
