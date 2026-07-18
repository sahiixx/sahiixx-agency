@echo off
rem Daily site monitor — invoked by Windows Task Scheduler (OPA-SiteMonitor, 06:05).
rem Runs the site-monitor workflow through the OPA CLI; output appended to the log.
set PYTHONIOENCODING=utf-8
cd /d C:\Users\sahii\sahiixx-agency
"C:\Users\sahii\sahiixx-agency\.venv\Scripts\opa.exe" workflow run site-monitor >> "C:\Users\sahii\sahiixx-agency\logs\site-monitor.log" 2>&1
