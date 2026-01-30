"""
WhatsApp Watcher - Monitors WhatsApp Web for important messages.

Uses Playwright for browser automation. First run requires manual QR code scan.

IMPORTANT: Be aware of WhatsApp's terms of service regarding automation.
This is for personal use only.

Usage:
    python -m src.watchers.whatsapp_watcher --vault ./AI_Employee_Vault

First run:
    1. Run the watcher
    2. Scan QR code with WhatsApp mobile app
    3. Session will be saved for future runs

Or programmatically:
    from src.watchers import WhatsAppWatcher
    watcher = WhatsAppWatcher('./AI_Employee_Vault', './config/whatsapp_session')
    watcher.run()
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

from .base_watcher import BaseWatcher

# Playwright imports - optional, graceful fallback
try:
    from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class WhatsAppWatcher(BaseWatcher):
    """Watch WhatsApp Web for important messages matching keywords."""

    def __init__(
        self,
        vault_path: str,
        session_path: Optional[str] = None,
        check_interval: int = 30,
        keywords: Optional[List[str]] = None,
        headless: bool = False,
        contacts_whitelist: Optional[List[str]] = None
    ):
        """
        Initialize WhatsApp Watcher.

        Args:
            vault_path: Path to the Obsidian vault
            session_path: Path to store browser session (for persistent login)
            check_interval: Seconds between checks
            keywords: Keywords that trigger action creation
            headless: Run browser in headless mode (set True after initial login)
            contacts_whitelist: Only monitor these contacts (None = all)
        """
        super().__init__(vault_path, check_interval, "WhatsAppWatcher")

        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright not installed. Run:\n"
                "pip install playwright\n"
                "playwright install chromium"
            )

        # Session storage for persistent login
        if session_path is None:
            session_path = str(self.vault_path.parent / 'config' / 'whatsapp_session')
        self.session_path = Path(session_path)
        self.session_path.mkdir(parents=True, exist_ok=True)

        # Configuration
        self.headless = headless
        self.contacts_whitelist = set(contacts_whitelist) if contacts_whitelist else None

        # Keywords that trigger action file creation
        self.keywords = keywords or [
            'urgent', 'asap', 'help', 'important',
            'invoice', 'payment', 'deadline', 'meeting',
            'call', 'emergency', 'please respond', 'need'
        ]

        # Track processed messages to avoid duplicates
        self.processed_messages: Set[str] = set()

        # Playwright objects
        self._playwright = None
        self._browser: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def _start_browser(self) -> bool:
        """Start Playwright browser with persistent context."""
        try:
            self._playwright = sync_playwright().start()

            # Use persistent context to maintain WhatsApp login
            self._browser = self._playwright.chromium.launch_persistent_context(
                str(self.session_path),
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox'
                ],
                viewport={'width': 1280, 'height': 800}
            )

            self._page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()

            # Navigate to WhatsApp Web
            self._page.goto('https://web.whatsapp.com', wait_until='domcontentloaded')

            self.logger.info("Browser started, navigating to WhatsApp Web")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            return False

    def _wait_for_login(self, timeout: int = 120000) -> bool:
        """Wait for user to scan QR code and login."""
        try:
            self.logger.info("Waiting for WhatsApp login (scan QR code if needed)...")

            # Wait for either the chat list (logged in) or QR code
            self._page.wait_for_selector(
                '[aria-label="Chat list"], [data-testid="qrcode"]',
                timeout=30000
            )

            # Check if QR code is shown (needs login)
            qr_code = self._page.query_selector('[data-testid="qrcode"]')
            if qr_code:
                self.logger.info("QR Code displayed - please scan with WhatsApp mobile app")
                # Wait for login to complete
                self._page.wait_for_selector('[aria-label="Chat list"]', timeout=timeout)

            self.logger.info("WhatsApp login successful")
            return True

        except Exception as e:
            self.logger.error(f"Login timeout or error: {e}")
            return False

    def _stop_browser(self) -> None:
        """Stop Playwright browser."""
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except:
            pass

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """Check WhatsApp for new messages matching keywords."""
        messages = []

        try:
            # Initialize browser if needed
            if self._page is None:
                if not self._start_browser():
                    return []
                if not self._wait_for_login():
                    return []

            # Wait a moment for any new messages to render
            self._page.wait_for_timeout(2000)

            # Find chats with unread messages
            unread_chats = self._find_unread_chats()

            for chat_info in unread_chats:
                # Check whitelist if configured
                if self.contacts_whitelist and chat_info['name'] not in self.contacts_whitelist:
                    continue

                # Check if any keyword matches in the preview
                preview_lower = chat_info['preview'].lower()
                matched_keywords = [kw for kw in self.keywords if kw.lower() in preview_lower]

                if matched_keywords:
                    # Get full conversation
                    full_messages = self._get_chat_messages(chat_info['name'])

                    msg_id = f"{chat_info['name']}_{hash(chat_info['preview'])}_{datetime.now().strftime('%Y%m%d%H%M')}"

                    if msg_id not in self.processed_messages:
                        messages.append({
                            'id': msg_id,
                            'contact': chat_info['name'],
                            'preview': chat_info['preview'],
                            'unread_count': chat_info.get('unread_count', 1),
                            'matched_keywords': matched_keywords,
                            'recent_messages': full_messages[-10:],  # Last 10 messages
                            'timestamp': datetime.now().isoformat()
                        })

        except Exception as e:
            self.logger.error(f"Error checking WhatsApp: {e}")
            # Don't stop - graceful degradation
            self.log_action('check_error', {'error': str(e)})

        return messages

    def _find_unread_chats(self) -> List[Dict[str, Any]]:
        """Find all chats with unread messages."""
        unread_chats = []

        try:
            # Wait for chat list
            self._page.wait_for_selector('[aria-label="Chat list"]', timeout=10000)

            # Find chat items with unread badges
            chat_items = self._page.query_selector_all('[data-testid="cell-frame-container"]')

            for chat in chat_items:
                try:
                    # Check for unread indicator
                    unread_badge = chat.query_selector('[data-testid="icon-unread-count"]')
                    if not unread_badge:
                        # Also check for unread dot
                        unread_dot = chat.query_selector('[data-icon="unread-count"]')
                        if not unread_dot:
                            continue

                    # Get contact name
                    name_element = chat.query_selector('[data-testid="cell-frame-title"]')
                    name = name_element.inner_text().strip() if name_element else "Unknown"

                    # Get message preview
                    preview_element = chat.query_selector('[data-testid="last-msg-status"]')
                    preview = preview_element.inner_text().strip() if preview_element else ""

                    if not preview:
                        preview_element = chat.query_selector('span[dir="ltr"]')
                        preview = preview_element.inner_text().strip() if preview_element else ""

                    # Get unread count if available
                    unread_count = 1
                    if unread_badge:
                        try:
                            count_text = unread_badge.inner_text().strip()
                            unread_count = int(count_text) if count_text.isdigit() else 1
                        except:
                            pass

                    unread_chats.append({
                        'name': name,
                        'preview': preview,
                        'unread_count': unread_count,
                        'element': chat
                    })

                except Exception as e:
                    self.logger.debug(f"Error parsing chat: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error finding unread chats: {e}")

        return unread_chats

    def _get_chat_messages(self, contact_name: str) -> List[Dict[str, str]]:
        """Get recent messages from a specific chat."""
        messages = []

        try:
            # Search for the contact
            search_box = self._page.query_selector('[data-testid="chat-list-search"]')
            if search_box:
                search_box.click()
                self._page.wait_for_timeout(500)
                self._page.keyboard.type(contact_name)
                self._page.wait_for_timeout(1000)

                # Click on the contact
                contact = self._page.query_selector(f'span[title="{contact_name}"]')
                if contact:
                    contact.click()
                    self._page.wait_for_timeout(1000)

                    # Get messages
                    msg_elements = self._page.query_selector_all('[data-testid="msg-container"]')

                    for msg in msg_elements[-15:]:  # Last 15 messages
                        try:
                            text_element = msg.query_selector('[data-testid="conversation-compose-box-input"], span.selectable-text')
                            if text_element:
                                text = text_element.inner_text().strip()
                                if text:
                                    # Determine if incoming or outgoing
                                    is_outgoing = 'message-out' in (msg.get_attribute('class') or '')

                                    messages.append({
                                        'text': text,
                                        'direction': 'outgoing' if is_outgoing else 'incoming'
                                    })
                        except:
                            continue

                # Clear search
                self._page.keyboard.press('Escape')

        except Exception as e:
            self.logger.error(f"Error getting chat messages: {e}")

        return messages

    def create_action_file(self, item: Dict[str, Any]) -> Path:
        """Create action file for a WhatsApp message."""
        msg_id = item['id']
        contact = item['contact']
        preview = item['preview']
        keywords = item['matched_keywords']
        messages = item.get('recent_messages', [])
        unread_count = item.get('unread_count', 1)

        # Determine priority based on keywords
        priority = self._determine_priority(keywords, preview)

        # Check if requires approval
        requires_approval = self._check_requires_approval(preview, keywords)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Format recent messages
        messages_md = ""
        if messages:
            messages_md = "\n".join([
                f"{'→' if m['direction'] == 'outgoing' else '←'} {m['text']}"
                for m in messages
            ])

        content = f'''---
type: whatsapp
message_id: "{msg_id}"
contact: "{self._escape_yaml(contact)}"
preview: "{self._escape_yaml(preview[:100])}"
unread_count: {unread_count}
matched_keywords: [{', '.join(f'"{kw}"' for kw in keywords)}]
received: "{datetime.now().isoformat()}"
priority: "{priority}"
status: pending
requires_approval: {str(requires_approval).lower()}
---

# WhatsApp: {contact}

## Message Details

| Field | Value |
|-------|-------|
| **From** | {contact} |
| **Unread** | {unread_count} message(s) |
| **Priority** | {priority} |
| **Keywords** | {', '.join(keywords)} |
| **Received** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |

## Latest Message

> {preview}

## Recent Conversation

```
{messages_md or 'No messages retrieved'}
```

## Suggested Actions

{self._get_suggested_actions(priority, requires_approval, keywords)}

## Draft Response

<!-- Write your response here -->

```
Hi {contact.split()[0] if ' ' in contact else contact},

[Your response here]
```

## Notes

<!-- Add any notes here -->

'''
        # Create action file
        safe_contact = self._sanitize_filename(contact[:30])
        action_filename = f'WHATSAPP_{timestamp}_{safe_contact}.md'
        action_path = self.needs_action / action_filename
        action_path.write_text(content, encoding='utf-8')

        # Mark as processed
        self.processed_messages.add(msg_id)

        return action_path

    def _determine_priority(self, keywords: List[str], message: str) -> str:
        """Determine message priority."""
        high_priority = {'urgent', 'asap', 'emergency', 'help', 'important'}
        medium_priority = {'meeting', 'call', 'deadline', 'payment', 'invoice'}

        keywords_lower = {kw.lower() for kw in keywords}

        if keywords_lower & high_priority:
            return 'high'
        if keywords_lower & medium_priority:
            return 'medium'
        return 'low'

    def _check_requires_approval(self, message: str, keywords: List[str]) -> bool:
        """Check if response requires approval."""
        approval_triggers = ['payment', 'invoice', 'contract', 'money', 'transfer']
        content = message.lower()
        return any(trigger in content for trigger in approval_triggers)

    def _get_suggested_actions(self, priority: str, requires_approval: bool, keywords: List[str]) -> str:
        """Get suggested actions based on context."""
        actions = []

        if requires_approval:
            actions.append("- [ ] **REQUIRES APPROVAL** - Move to Pending_Approval before responding")

        if priority == 'high':
            actions.append("- [ ] Respond promptly (high priority)")

        if 'meeting' in keywords or 'call' in keywords:
            actions.append("- [ ] Check calendar availability")
            actions.append("- [ ] Propose meeting time if needed")

        if 'payment' in keywords or 'invoice' in keywords:
            actions.append("- [ ] Verify payment/invoice details")
            actions.append("- [ ] Check financial records")

        actions.extend([
            "- [ ] Draft appropriate response",
            "- [ ] Send response via WhatsApp",
            "- [ ] Mark as handled"
        ])

        return '\n'.join(actions)

    def _sanitize_filename(self, text: str) -> str:
        """Create safe filename."""
        safe = re.sub(r'[<>:"/\\|?*]', '', text)
        safe = re.sub(r'\s+', '_', safe)
        return safe.strip('_') or 'message'

    def _escape_yaml(self, text: str) -> str:
        """Escape text for YAML."""
        return text.replace('"', '\\"').replace('\n', ' ')

    def run(self) -> None:
        """Main run loop with browser lifecycle management."""
        self.logger.info(f'Starting {self.watcher_name}')
        self.log_action('watcher_started', {'interval': self.check_interval})

        try:
            # Start browser and login
            if not self._start_browser():
                self.logger.error("Failed to start browser")
                return

            if not self._wait_for_login():
                self.logger.error("Failed to login to WhatsApp")
                return

            self.is_running = True

            # Main loop
            while self.is_running:
                try:
                    items = self.check_for_updates()

                    for item in items:
                        try:
                            filepath = self.create_action_file(item)
                            self.log_action('item_created', {
                                'filepath': str(filepath),
                                'contact': item['contact'],
                                'keywords': item['matched_keywords']
                            })
                            self.logger.info(f'Created action file: {filepath}')
                        except Exception as e:
                            self.logger.error(f'Error creating action file: {e}')

                    self._error_count = 0

                except Exception as e:
                    self._error_count += 1
                    self.logger.error(f'Error in check loop: {e}')

                    if self._error_count >= self._max_errors:
                        self.logger.critical('Max errors exceeded, stopping')
                        break

                self._page.wait_for_timeout(self.check_interval * 1000)

        finally:
            self._stop_browser()
            self.log_action('watcher_stopped', {'reason': 'run_complete'})

    def stop(self) -> None:
        """Stop the watcher and close browser."""
        super().stop()
        self._stop_browser()


# Standalone runner
if __name__ == '__main__':
    import argparse
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description='WhatsApp Watcher for AI Employee')
    parser.add_argument(
        '--vault',
        default='./AI_Employee_Vault',
        help='Path to Obsidian vault'
    )
    parser.add_argument(
        '--session',
        default='./config/whatsapp_session',
        help='Path to store browser session'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Check interval in seconds'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run in headless mode (after initial login)'
    )
    parser.add_argument(
        '--keywords',
        nargs='+',
        default=None,
        help='Keywords to monitor for'
    )

    args = parser.parse_args()

    try:
        watcher = WhatsAppWatcher(
            vault_path=args.vault,
            session_path=args.session,
            check_interval=args.interval,
            headless=args.headless,
            keywords=args.keywords
        )

        print("WhatsApp Watcher starting...")
        print(f"Session path: {args.session}")
        print(f"Check interval: {args.interval}s")
        print(f"Keywords: {watcher.keywords}")
        print("\nIf this is first run, scan the QR code with WhatsApp mobile app")
        print("Press Ctrl+C to stop...")

        watcher.run()

    except ImportError as e:
        print(f"Error: {e}")
        print("\nInstall Playwright with:")
        print("pip install playwright")
        print("playwright install chromium")
    except KeyboardInterrupt:
        print("\nStopping...")
