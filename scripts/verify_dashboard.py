"""Actual local dashboard + Chromium smoke. No persistent service, no public hosting."""

import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


def main():
    root = Path(__file__).resolve().parents[1]
    reports = sorted(
        (root / "data/demo/runs").glob("*/processed/DEMO_report.html"),
        key=lambda p: p.stat().st_mtime,
    )
    if not reports:
        raise ValueError("Run goldintel demo first")
    run_id = reports[-1].parent.parent.name
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "mega_crawler.cli",
            "--demo-data",
            "dashboard",
            "--run-id",
            run_id,
            "--port",
            "9852",
        ],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    try:
        for _ in range(100):
            try:
                with urlopen("http://127.0.0.1:9852/", timeout=1) as response:
                    if response.status == 200:
                        break
            except (URLError, OSError):
                time.sleep(0.1)
        else:
            raise RuntimeError("Dashboard failed to start")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto("http://127.0.0.1:9852/")
            assert page.locator(".badge").inner_text() == "DEMO / DATA SINTETIS"
            assert page.locator("#posts tbody tr").count() == 12
            assert page.locator("#snapshots tbody tr").count() == 12
            assert page.locator("#rankings tbody tr").count() == 0
            page.select_option("#f_platform", "youtube")
            page.select_option("#f_brand_id", "mandiri")
            page.select_option("#f_segment", "direct")
            page.select_option("#f_ownership_type", "owned")
            page.select_option("#f_format", "shorts")
            assert page.locator("#posts tbody tr").count() == 12
            page.fill("#f_start", "2099-01-01")
            page.locator("#f_start").dispatch_event("change")
            assert page.locator("#posts tbody tr").count() == 0
            assert page.locator("#snapshots tbody tr").count() == 0
            page.fill("#f_start", "")
            page.locator("#f_start").dispatch_event("change")
            assert page.locator("#posts tbody tr").count() == 12
            # Server cannot expose workspace or secrets.
            assert page.request.get("http://127.0.0.1:9852/.env").status == 404
            assert not errors, errors
            screenshot = root / "data/demo/dashboard-smoke.png"
            page.screenshot(path=str(screenshot), full_page=True)
            browser.close()
        print(
            json.dumps(
                {
                    "status": "passed",
                    "run_id": run_id,
                    "post_rows": 12,
                    "snapshot_rows": 12,
                    "filter_checks": "platform/brand/segment/ownership/format/date/reset",
                    "javascript_errors": 0,
                    "private_path": "404",
                    "screenshot": str(screenshot),
                }
            )
        )
    finally:
        process.terminate()
        process.wait(timeout=10)


if __name__ == "__main__":
    main()
