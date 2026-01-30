#!/usr/bin/env python3
"""
Quick check for unread WhatsApp messages without running full watcher.

Usage:
    python check_unread.py [--session path/to/session]

Requires existing WhatsApp session (QR already scanned).
"""

import sys
import json
from pathlib import Path


def check_unread(session_path: str):
    """Check for unread messages and print summary."""

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Error: Playwright not installed")
        print("Run: pip install playwright && playwright install chromium")
        return 1

    session = Path(session_path)
    if not session.exists():
        print(f"Error: Session not found at {session_path}")
        print("Run the watcher first to authenticate via QR code")
        return 1

    print("Launching browser...")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                str(session),
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )

            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto('https://web.whatsapp.com', wait_until='domcontentloaded')

            print("Waiting for WhatsApp to load...")

            # Wait for chat list
            try:
                page.wait_for_selector('[aria-label="Chat list"]', timeout=30000)
            except:
                print("Error: Could not load WhatsApp")
                print("Session may have expired - re-authenticate with QR code")
                browser.close()
                return 1

            # Give time for messages to load
            page.wait_for_timeout(3000)

            # Find unread chats
            unread_chats = []
            chat_items = page.query_selector_all('[data-testid="cell-frame-container"]')

            for chat in chat_items:
                try:
                    # Check for unread indicator
                    unread_badge = chat.query_selector('[data-testid="icon-unread-count"]')
                    if not unread_badge:
                        unread_dot = chat.query_selector('[data-icon="unread-count"]')
                        if not unread_dot:
                            continue

                    # Get contact name
                    name_el = chat.query_selector('[data-testid="cell-frame-title"]')
                    name = name_el.inner_text().strip() if name_el else "Unknown"

                    # Get preview
                    preview_el = chat.query_selector('span[dir="ltr"]')
                    preview = preview_el.inner_text().strip()[:50] if preview_el else ""

                    # Get count
                    count = 1
                    if unread_badge:
                        try:
                            count_text = unread_badge.inner_text().strip()
                            count = int(count_text) if count_text.isdigit() else 1
                        except:
                            pass

                    unread_chats.append({
                        'contact': name,
                        'preview': preview,
                        'unread_count': count
                    })

                except:
                    continue

            browser.close()

            # Print results
            if not unread_chats:
                print("\n✓ No unread messages")
                return 0

            print(f"\n📬 Found {len(unread_chats)} chats with unread messages:\n")
            print("-" * 60)

            for chat in unread_chats:
                count_str = f"({chat['unread_count']})" if chat['unread_count'] > 1 else ""
                print(f"  {chat['contact']} {count_str}")
                if chat['preview']:
                    print(f"    └─ {chat['preview']}...")
                print()

            print("-" * 60)
            print(f"Total: {sum(c['unread_count'] for c in unread_chats)} unread messages")

            return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Check unread WhatsApp messages')
    parser.add_argument(
        '--session',
        default='./config/whatsapp_session',
        help='Path to session folder'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    return check_unread(args.session)


if __name__ == "__main__":
    sys.exit(main())
