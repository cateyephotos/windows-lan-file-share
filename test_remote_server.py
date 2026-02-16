#!/usr/bin/env python3
"""
Playwright tests for Windows LAN File Share
Tests connectivity and functionality against a remote server at 192.168.1.192:8000
"""

import asyncio
from playwright.async_api import async_playwright

REMOTE_HOST = "192.168.1.192"
REMOTE_PORT = 8000
REMOTE_URL = f"http://{REMOTE_HOST}:{REMOTE_PORT}"


async def test_tcp_reachability():
    """Test 1: Basic TCP connectivity to the remote server port"""
    import socket
    print("\n" + "=" * 60)
    print("TEST 1: TCP Reachability")
    print("=" * 60)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((REMOTE_HOST, REMOTE_PORT))
        sock.close()
        if result == 0:
            print(f"  [PASS] Port {REMOTE_PORT} is OPEN on {REMOTE_HOST}")
            return True
        else:
            print(f"  [FAIL] Port {REMOTE_PORT} is CLOSED on {REMOTE_HOST} (error code: {result})")
            return False
    except Exception as e:
        print(f"  [FAIL] Could not connect: {e}")
        return False


async def test_http_response():
    """Test 2: HTTP GET to root — check for valid HTML response"""
    import urllib.request
    print("\n" + "=" * 60)
    print("TEST 2: HTTP Response (urllib)")
    print("=" * 60)
    try:
        req = urllib.request.Request(REMOTE_URL)
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read().decode("utf-8", errors="replace")
            print(f"  Status: {status}")
            print(f"  Content-Type: {content_type}")
            print(f"  Body length: {len(body)} chars")
            if "LAN File Share" in body:
                print("  [PASS] Response contains 'LAN File Share' — server identified")
            else:
                print("  [WARN] Response does not contain expected title")
            return True
    except Exception as e:
        print(f"  [FAIL] HTTP request failed: {e}")
        return False


async def test_browser_navigation(playwright):
    """Test 3: Open the page in a real Chromium browser via Playwright"""
    print("\n" + "=" * 60)
    print("TEST 3: Playwright Browser Navigation")
    print("=" * 60)
    browser = await playwright.chromium.launch(headless=True)
    try:
        context = await browser.new_context()
        page = await context.new_page()

        response = await page.goto(REMOTE_URL, timeout=15000)
        print(f"  URL: {page.url}")
        print(f"  Status: {response.status if response else 'N/A'}")

        title = await page.title()
        print(f"  Page title: {title}")

        if response and response.ok:
            print("  [PASS] Page loaded successfully")
        else:
            print(f"  [FAIL] Page returned non-OK status")
            return False

        return True
    except Exception as e:
        print(f"  [FAIL] Browser navigation failed: {e}")
        return False
    finally:
        await browser.close()


async def test_page_content(playwright):
    """Test 4: Verify page content — heading, file list area, styles"""
    print("\n" + "=" * 60)
    print("TEST 4: Page Content Verification")
    print("=" * 60)
    browser = await playwright.chromium.launch(headless=True)
    try:
        page = await browser.new_page()
        await page.goto(REMOTE_URL, timeout=15000)

        # Check for heading
        heading = await page.query_selector("h1")
        if heading:
            heading_text = await heading.inner_text()
            print(f"  Heading: {heading_text}")
            print("  [PASS] H1 heading found")
        else:
            print("  [FAIL] No H1 heading found")

        # Check for container
        container = await page.query_selector(".container")
        if container:
            print("  [PASS] .container element found")
        else:
            print("  [WARN] No .container element found")

        # Check for file items or no-files message
        file_items = await page.query_selector_all(".file-item")
        no_files = await page.query_selector(".no-files")

        if file_items:
            print(f"  [PASS] Found {len(file_items)} shared file(s)")
            for i, item in enumerate(file_items):
                name_el = await item.query_selector(".file-name")
                if name_el:
                    name = await name_el.inner_text()
                    print(f"    File {i+1}: {name}")
        elif no_files:
            msg = await no_files.inner_text()
            print(f"  [INFO] No files shared: '{msg}'")
        else:
            print("  [WARN] Could not determine file list state")

        return True
    except Exception as e:
        print(f"  [FAIL] Content verification failed: {e}")
        return False
    finally:
        await browser.close()


async def test_download_links(playwright):
    """Test 5: If files are shared, verify download links are functional"""
    print("\n" + "=" * 60)
    print("TEST 5: Download Link Verification")
    print("=" * 60)
    browser = await playwright.chromium.launch(headless=True)
    try:
        page = await browser.new_page()
        await page.goto(REMOTE_URL, timeout=15000)

        download_links = await page.query_selector_all("a.download-btn")
        if not download_links:
            print("  [SKIP] No download links found (no files shared)")
            return True

        print(f"  Found {len(download_links)} download link(s)")

        # Test first download link with a HEAD request
        first_link = download_links[0]
        href = await first_link.get_attribute("href")
        if href:
            download_url = f"{REMOTE_URL}{href}" if href.startswith("/") else href
            print(f"  Testing download URL: {download_url}")

            import urllib.request
            req = urllib.request.Request(download_url, method="HEAD")
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    print(f"  Status: {resp.status}")
                    content_length = resp.headers.get("Content-Length", "unknown")
                    content_disp = resp.headers.get("Content-Disposition", "none")
                    print(f"  Content-Length: {content_length}")
                    print(f"  Content-Disposition: {content_disp}")
                    print("  [PASS] Download endpoint is responsive")
            except Exception as e:
                print(f"  [FAIL] Download HEAD request failed: {e}")
                return False
        else:
            print("  [WARN] Download link has no href")

        return True
    except Exception as e:
        print(f"  [FAIL] Download link test failed: {e}")
        return False
    finally:
        await browser.close()


async def test_screenshot(playwright):
    """Test 6: Take a screenshot of the remote server page"""
    print("\n" + "=" * 60)
    print("TEST 6: Screenshot Capture")
    print("=" * 60)
    browser = await playwright.chromium.launch(headless=True)
    try:
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        await page.goto(REMOTE_URL, timeout=15000)
        await page.wait_for_load_state("networkidle")

        screenshot_path = "test_remote_screenshot.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"  [PASS] Screenshot saved to {screenshot_path}")
        return True
    except Exception as e:
        print(f"  [FAIL] Screenshot failed: {e}")
        return False
    finally:
        await browser.close()


async def main():
    print("=" * 60)
    print(f"  LAN File Share — Remote Server Tests")
    print(f"  Target: {REMOTE_URL}")
    print("=" * 60)

    results = {}

    # Test 1: TCP
    results["TCP Reachability"] = await test_tcp_reachability()

    if not results["TCP Reachability"]:
        print("\n[ABORT] Server is not reachable. Skipping browser tests.")
        print_summary(results)
        return

    # Test 2: HTTP
    results["HTTP Response"] = await test_http_response()

    if not results["HTTP Response"]:
        print("\n[ABORT] HTTP not responding. Skipping browser tests.")
        print_summary(results)
        return

    # Playwright tests
    async with async_playwright() as pw:
        results["Browser Navigation"] = await test_browser_navigation(pw)
        results["Page Content"] = await test_page_content(pw)
        results["Download Links"] = await test_download_links(pw)
        results["Screenshot"] = await test_screenshot(pw)

    print_summary(results)


def print_summary(results):
    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    passed = 0
    failed = 0
    for name, result in results.items():
        status = "PASS" if result else "FAIL"
        icon = "✓" if result else "✗"
        print(f"  {icon} {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    print(f"\n  Total: {passed + failed} | Passed: {passed} | Failed: {failed}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
