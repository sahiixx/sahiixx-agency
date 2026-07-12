from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    
    # Go to dashboard on API port (serves built dist/)
    page.goto("http://127.0.0.1:8082/dashboard/")
    
    # Wait for app to load
    page.wait_for_timeout(3000)
    
    # If login screen appears, auto-login with dev credentials
    if page.locator("text=SAHIIXX OS").count() > 0 and page.locator("input[type='password']").count() > 0:
        page.fill("input[type='email']", "admin@sahiixx.os")
        page.fill("input[type='password']", "sahiixx")
        page.click("button:has-text('LOGIN')")
        page.wait_for_timeout(3000)
    
    # Navigate to Device tab
    page.click("text=Device")
    page.wait_for_timeout(5000)
    
    # Screenshot the device control panel
    page.screenshot(path="jarvis_device_overview.png", full_page=False)
    print("screenshot saved: jarvis_device_overview.png")
    
    # Click Processes tab
    page.click("text=Processes")
    page.wait_for_timeout(3000)
    page.screenshot(path="jarvis_device_processes.png", full_page=False)
    print("screenshot saved: jarvis_device_processes.png")
    
    # Click Services tab
    page.click("text=Services")
    page.wait_for_timeout(3000)
    page.screenshot(path="jarvis_device_services.png", full_page=False)
    print("screenshot saved: jarvis_device_services.png")
    
    # Click Terminal tab
    page.click("text=Terminal")
    page.wait_for_timeout(3000)
    page.screenshot(path="jarvis_device_terminal.png", full_page=False)
    print("screenshot saved: jarvis_device_terminal.png")
    
    # Click Voice tab
    page.click("text=Voice")
    page.wait_for_timeout(3000)
    page.screenshot(path="jarvis_device_voice.png", full_page=False)
    print("screenshot saved: jarvis_device_voice.png")
    
    # Click HUD tab
    page.click("text=HUD")
    page.wait_for_timeout(3000)
    page.screenshot(path="jarvis_device_hud.png", full_page=False)
    print("screenshot saved: jarvis_device_hud.png")
    
    browser.close()
