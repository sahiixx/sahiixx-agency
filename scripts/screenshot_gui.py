"""Screenshot working Jarvis GUI."""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto("http://localhost:5173/#/jarvis/gui", timeout=10000)
    time.sleep(4)

    # Execute a command
    page.fill('input[placeholder*="Type a command"]', "system")
    page.keyboard.press("Enter")
    time.sleep(3)

    page.screenshot(path="C:/Users/sahii/sahiixx-agency/jarvis_gui_screenshot.png", full_page=False)
    browser.close()
    print("Done")
