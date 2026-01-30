#!/usr/bin/env python3
"""
Verify Playwright and WhatsApp Watcher setup.

Usage:
    python verify_setup.py [--session path/to/session]

Checks:
1. Playwright installed
2. Chromium browser installed
3. Session folder exists (if specified)
4. Can launch browser
"""

import sys
from pathlib import Path


def check_playwright():
    """Check if Playwright is installed."""
    print("Checking Playwright installation...")

    try:
        from playwright.sync_api import sync_playwright
        print("  ✓ playwright package installed")
        return True
    except ImportError:
        print("  ✗ playwright NOT installed")
        print("\n❌ Install with:")
        print("   pip install playwright")
        return False


def check_chromium():
    """Check if Chromium browser is installed."""
    print("Checking Chromium browser...")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # Try to get browser executable
            browser_type = p.chromium
            executable = browser_type.executable_path

            if Path(executable).exists():
                print(f"  ✓ Chromium installed at: {executable[:50]}...")
                return True
            else:
                print("  ✗ Chromium executable not found")
                return False

    except Exception as e:
        print(f"  ✗ Error checking Chromium: {e}")
        print("\n❌ Install browser with:")
        print("   playwright install chromium")
        return False


def check_session(session_path):
    """Check if session folder exists."""
    print(f"Checking session folder: {session_path}")

    session = Path(session_path)
    if session.exists():
        # Check for key files
        has_cookies = any(session.rglob("Cookies*"))
        has_storage = any(session.rglob("Local Storage*"))

        if has_cookies or has_storage:
            print("  ✓ Session folder exists with data")
            print("    (WhatsApp should remember login)")
            return True
        else:
            print("  ⚠ Session folder exists but may be empty")
            print("    (Will need to scan QR code)")
            return True
    else:
        print("  ⚠ Session folder not found")
        print("    (Will create on first run - QR scan required)")
        return True


def test_browser_launch():
    """Test that browser can launch."""
    print("Testing browser launch...")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://www.google.com", timeout=10000)
            title = page.title()
            browser.close()

            print(f"  ✓ Browser launched successfully")
            print(f"    Test page title: {title}")
            return True

    except Exception as e:
        print(f"  ✗ Browser launch failed: {e}")
        return False


def test_whatsapp_reachable():
    """Test that WhatsApp Web is reachable."""
    print("Testing WhatsApp Web accessibility...")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            response = page.goto(
                "https://web.whatsapp.com",
                wait_until="domcontentloaded",
                timeout=15000
            )

            if response and response.status == 200:
                print("  ✓ WhatsApp Web is reachable")
                browser.close()
                return True
            else:
                print(f"  ✗ WhatsApp Web returned status: {response.status if response else 'None'}")
                browser.close()
                return False

    except Exception as e:
        print(f"  ✗ Cannot reach WhatsApp Web: {e}")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Verify WhatsApp Watcher setup')
    parser.add_argument(
        '--session',
        default='./config/whatsapp_session',
        help='Path to session folder'
    )

    args = parser.parse_args()

    print("=" * 50)
    print("WhatsApp Watcher Setup Verification")
    print("=" * 50)
    print()

    results = []

    # Check Playwright
    results.append(("Playwright", check_playwright()))
    print()

    # Check Chromium (only if Playwright installed)
    if results[-1][1]:
        results.append(("Chromium", check_chromium()))
        print()

    # Check session
    results.append(("Session", check_session(args.session)))
    print()

    # Test browser launch (only if Chromium OK)
    if len(results) >= 2 and results[1][1]:
        results.append(("Browser Launch", test_browser_launch()))
        print()

        # Test WhatsApp reachable
        if results[-1][1]:
            results.append(("WhatsApp Web", test_whatsapp_reachable()))
            print()

    # Summary
    print("=" * 50)
    print("Summary")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("✅ WhatsApp Watcher setup is ready!")
        print()
        print("Next steps:")
        print("  1. Run: python -m src.watchers.whatsapp_watcher --vault ./AI_Employee_Vault")
        print("  2. Scan QR code with WhatsApp mobile app (first time only)")
        print("  3. Messages matching keywords will create action files")
    else:
        print("❌ Setup incomplete. Fix issues above and re-run verification.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
