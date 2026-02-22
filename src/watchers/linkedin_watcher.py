"""
LinkedIn Watcher - Monitors LinkedIn for messages, connection requests, and notifications.

Uses Playwright for browser automation. First run requires manual login.

IMPORTANT: Be aware of LinkedIn's terms of service regarding automation.
This is for personal productivity use only - monitoring your own account.

Usage:
    python -m src.watchers.linkedin_watcher --vault ./AI_Employee_Vault

First run:
    1. Run the watcher
    2. Log in manually with your credentials
    3. Session will be saved for future runs

Or programmatically:
    from src.watchers import LinkedInWatcher
    watcher = LinkedInWatcher('./AI_Employee_Vault', './config/linkedin_session')
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


class LinkedInWatcher(BaseWatcher):
    """Watch LinkedIn for messages, connection requests, and notifications."""

    def __init__(
        self,
        vault_path: str,
        session_path: Optional[str] = None,
        check_interval: int = 120,
        keywords: Optional[List[str]] = None,
        headless: bool = False,
        monitor_messages: bool = True,
        monitor_connections: bool = True,
        monitor_notifications: bool = True
    ):
        """
        Initialize LinkedIn Watcher.

        Args:
            vault_path: Path to the Obsidian vault
            session_path: Path to store browser session (for persistent login)
            check_interval: Seconds between checks (default 120 - LinkedIn rate limits)
            keywords: Keywords that trigger high priority
            headless: Run browser in headless mode (set True after initial login)
            monitor_messages: Monitor direct messages/InMail
            monitor_connections: Monitor connection requests
            monitor_notifications: Monitor notifications
        """
        super().__init__(vault_path, check_interval, "LinkedInWatcher")

        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright not installed. Run:\n"
                "pip install playwright\n"
                "playwright install chromium"
            )

        # Session storage for persistent login
        if session_path is None:
            session_path = str(self.vault_path.parent / 'config' / 'linkedin_session')
        self.session_path = Path(session_path)
        self.session_path.mkdir(parents=True, exist_ok=True)

        # Configuration
        self.headless = headless
        self.monitor_messages = monitor_messages
        self.monitor_connections = monitor_connections
        self.monitor_notifications = monitor_notifications

        # Keywords that trigger high priority action files
        self.keywords = keywords or [
            'urgent', 'opportunity', 'job', 'interview', 'offer',
            'meeting', 'call', 'partnership', 'collaboration',
            'project', 'proposal', 'deadline', 'asap'
        ]

        # Track processed items to avoid duplicates
        self.processed_messages: Set[str] = set()
        self.processed_connections: Set[str] = set()
        self.processed_notifications: Set[str] = set()

        # Playwright objects
        self._playwright = None
        self._browser: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def _cleanup_session_locks(self) -> None:
        """Remove stale Chromium lock files that cause crash-on-start."""
        for lock_name in ('lockfile', 'SingletonLock', 'SingletonCookie', 'SingletonSocket'):
            lock_path = self.session_path / lock_name
            if lock_path.exists():
                try:
                    lock_path.unlink()
                    self.logger.info(f"Removed stale lock: {lock_name}")
                except Exception as e:
                    self.logger.warning(f"Could not remove {lock_name}: {e}")

    def _start_browser(self) -> bool:
        """Start Playwright browser with persistent context."""
        try:
            self._cleanup_session_locks()
            self._playwright = sync_playwright().start()

            # Use persistent context to maintain LinkedIn login
            self._browser = self._playwright.chromium.launch_persistent_context(
                str(self.session_path),
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox'
                ],
                viewport={'width': 800, 'height': 600},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            self._page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()

            # Navigate to LinkedIn
            self._page.goto('https://www.linkedin.com/feed/', wait_until='domcontentloaded')

            self.logger.info("Browser started, navigating to LinkedIn")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            return False

    def _wait_for_login(self, timeout: int = 300000) -> bool:
        """Wait for user to log in manually."""
        try:
            self.logger.info("Waiting for LinkedIn login...")

            # Check if already logged in (feed visible) or need login
            self._page.wait_for_selector(
                'div.feed-shared-update-v2, input[id="session_key"], input[id="username"]',
                timeout=120000
            )

            # Check if login form is shown
            login_form = self._page.query_selector('input[id="session_key"]')
            if login_form:
                self.logger.info("Login required - please log in manually in the browser window")
                # Wait for feed to appear (indicates successful login)
                self._page.wait_for_selector('div.feed-shared-update-v2', timeout=timeout)

            self.logger.info("LinkedIn login successful")
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
        """Check LinkedIn for new messages, connections, and notifications."""
        items = []

        try:
            # Initialize browser if needed
            if self._page is None:
                if not self._start_browser():
                    return []
                if not self._wait_for_login():
                    return []

            # Check messages
            if self.monitor_messages:
                messages = self._check_messages()
                items.extend(messages)

            # Check connection requests
            if self.monitor_connections:
                connections = self._check_connections()
                items.extend(connections)

            # Check notifications
            if self.monitor_notifications:
                notifications = self._check_notifications()
                items.extend(notifications)

        except Exception as e:
            self.logger.error(f"Error checking LinkedIn: {e}")
            self.log_action('check_error', {'error': str(e)})

        return items

    def _check_messages(self) -> List[Dict[str, Any]]:
        """Check for unread messages."""
        messages = []

        try:
            # Navigate to messaging
            self._page.goto('https://www.linkedin.com/messaging/', wait_until='networkidle')
            self._page.wait_for_timeout(2000)

            # Find unread conversations (they have a blue dot/badge)
            conversations = self._page.query_selector_all('li.msg-conversation-listitem')

            for conv in conversations[:10]:  # Check first 10
                try:
                    # Check for unread indicator
                    unread = conv.query_selector('.msg-conversation-card__unread-count')
                    if not unread:
                        continue

                    # Get sender name
                    name_elem = conv.query_selector('.msg-conversation-listitem__participant-names')
                    name = name_elem.inner_text().strip() if name_elem else "Unknown"

                    # Get message preview
                    preview_elem = conv.query_selector('.msg-conversation-card__message-snippet')
                    preview = preview_elem.inner_text().strip() if preview_elem else ""

                    # Get timestamp
                    time_elem = conv.query_selector('.msg-conversation-card__time-stamp')
                    timestamp = time_elem.inner_text().strip() if time_elem else ""

                    # Generate unique ID
                    msg_id = f"linkedin_msg_{hash(name + preview)}"

                    if msg_id not in self.processed_messages:
                        # Check for keyword matches
                        preview_lower = preview.lower()
                        matched_keywords = [kw for kw in self.keywords if kw.lower() in preview_lower]

                        messages.append({
                            'type': 'linkedin_message',
                            'id': msg_id,
                            'sender': name,
                            'preview': preview,
                            'timestamp': timestamp,
                            'matched_keywords': matched_keywords,
                            'received_at': datetime.now().isoformat()
                        })

                except Exception as e:
                    self.logger.debug(f"Error parsing message: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error checking messages: {e}")

        return messages

    def _check_connections(self) -> List[Dict[str, Any]]:
        """Check for pending connection requests."""
        connections = []

        try:
            # Navigate to network/invitations
            self._page.goto('https://www.linkedin.com/mynetwork/invitation-manager/', wait_until='networkidle')
            self._page.wait_for_timeout(2000)

            # Find invitation cards
            invitations = self._page.query_selector_all('li.invitation-card')

            for inv in invitations[:10]:  # Check first 10
                try:
                    # Get requester name
                    name_elem = inv.query_selector('.invitation-card__title')
                    name = name_elem.inner_text().strip() if name_elem else "Unknown"

                    # Get headline/title
                    headline_elem = inv.query_selector('.invitation-card__subtitle')
                    headline = headline_elem.inner_text().strip() if headline_elem else ""

                    # Get mutual connections if shown
                    mutual_elem = inv.query_selector('.member-insights__count')
                    mutual = mutual_elem.inner_text().strip() if mutual_elem else "0"

                    # Generate unique ID
                    conn_id = f"linkedin_conn_{hash(name + headline)}"

                    if conn_id not in self.processed_connections:
                        # Check for keyword matches in headline
                        headline_lower = headline.lower()
                        matched_keywords = [kw for kw in self.keywords if kw.lower() in headline_lower]

                        connections.append({
                            'type': 'linkedin_connection',
                            'id': conn_id,
                            'name': name,
                            'headline': headline,
                            'mutual_connections': mutual,
                            'matched_keywords': matched_keywords,
                            'received_at': datetime.now().isoformat()
                        })

                except Exception as e:
                    self.logger.debug(f"Error parsing connection: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error checking connections: {e}")

        return connections

    def _check_notifications(self) -> List[Dict[str, Any]]:
        """Check for new notifications."""
        notifications = []

        try:
            # Navigate to notifications
            self._page.goto('https://www.linkedin.com/notifications/', wait_until='networkidle')
            self._page.wait_for_timeout(2000)

            # Find notification items (unread have different styling)
            notif_items = self._page.query_selector_all('article.nt-card')

            for notif in notif_items[:10]:  # Check first 10
                try:
                    # Check if unread (has unread class/style)
                    is_unread = notif.query_selector('.nt-card--unread') is not None

                    if not is_unread:
                        continue

                    # Get notification text
                    text_elem = notif.query_selector('.nt-card__headline')
                    text = text_elem.inner_text().strip() if text_elem else ""

                    # Get timestamp
                    time_elem = notif.query_selector('.nt-card__time-ago')
                    timestamp = time_elem.inner_text().strip() if time_elem else ""

                    # Generate unique ID
                    notif_id = f"linkedin_notif_{hash(text)}"

                    if notif_id not in self.processed_notifications:
                        # Check for keyword matches
                        text_lower = text.lower()
                        matched_keywords = [kw for kw in self.keywords if kw.lower() in text_lower]

                        # Determine notification type
                        notif_type = self._classify_notification(text)

                        notifications.append({
                            'type': 'linkedin_notification',
                            'id': notif_id,
                            'text': text,
                            'notification_type': notif_type,
                            'timestamp': timestamp,
                            'matched_keywords': matched_keywords,
                            'received_at': datetime.now().isoformat()
                        })

                except Exception as e:
                    self.logger.debug(f"Error parsing notification: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error checking notifications: {e}")

        return notifications

    def _classify_notification(self, text: str) -> str:
        """Classify the type of notification."""
        text_lower = text.lower()

        if 'viewed your profile' in text_lower:
            return 'profile_view'
        elif 'commented' in text_lower:
            return 'comment'
        elif 'liked' in text_lower or 'reacted' in text_lower:
            return 'reaction'
        elif 'mentioned' in text_lower:
            return 'mention'
        elif 'shared' in text_lower:
            return 'share'
        elif 'posted' in text_lower:
            return 'post'
        elif 'birthday' in text_lower:
            return 'birthday'
        elif 'work anniversary' in text_lower or 'new position' in text_lower:
            return 'career_update'
        elif 'endorsed' in text_lower:
            return 'endorsement'
        else:
            return 'other'

    def create_action_file(self, item: Dict[str, Any]) -> Path:
        """Create action file for a LinkedIn item."""
        item_type = item['type']

        if item_type == 'linkedin_message':
            return self._create_message_action(item)
        elif item_type == 'linkedin_connection':
            return self._create_connection_action(item)
        elif item_type == 'linkedin_notification':
            return self._create_notification_action(item)
        else:
            raise ValueError(f"Unknown item type: {item_type}")

    def _create_message_action(self, item: Dict[str, Any]) -> Path:
        """Create action file for a LinkedIn message."""
        sender = item['sender']
        preview = item['preview']
        keywords = item.get('matched_keywords', [])
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        priority = 'high' if keywords else 'medium'
        requires_approval = any(kw in ['opportunity', 'offer', 'partnership'] for kw in keywords)

        content = f'''---
type: linkedin_message
message_id: "{item['id']}"
sender: "{self._escape_yaml(sender)}"
preview: "{self._escape_yaml(preview[:100])}"
matched_keywords: [{', '.join(f'"{kw}"' for kw in keywords)}]
received: "{datetime.now().isoformat()}"
priority: "{priority}"
status: pending
requires_approval: {str(requires_approval).lower()}
---

# LinkedIn Message from {sender}

## Message Details

| Field | Value |
|-------|-------|
| **From** | {sender} |
| **Priority** | {priority} |
| **Keywords** | {', '.join(keywords) or 'None'} |
| **Received** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |

## Message Preview

> {preview}

## Suggested Actions

{self._get_message_actions(priority, requires_approval, keywords)}

## Draft Response

<!-- Write your response here -->

```
Hi {sender.split()[0] if ' ' in sender else sender},

Thank you for reaching out.

[Your response here]

Best regards,
[Your name]
```

## Notes

<!-- Add any notes here -->

'''
        # Create action file
        safe_sender = self._sanitize_filename(sender[:30])
        action_filename = f'LINKEDIN_MSG_{timestamp}_{safe_sender}.md'
        action_path = self.needs_action / action_filename
        action_path.write_text(content, encoding='utf-8')

        # Mark as processed
        self.processed_messages.add(item['id'])

        return action_path

    def _create_connection_action(self, item: Dict[str, Any]) -> Path:
        """Create action file for a connection request."""
        name = item['name']
        headline = item['headline']
        mutual = item.get('mutual_connections', '0')
        keywords = item.get('matched_keywords', [])
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Determine priority based on keywords and mutual connections
        priority = 'high' if keywords or int(mutual.split()[0] if mutual else '0') > 5 else 'medium'

        content = f'''---
type: linkedin_connection
connection_id: "{item['id']}"
name: "{self._escape_yaml(name)}"
headline: "{self._escape_yaml(headline[:100])}"
mutual_connections: "{mutual}"
matched_keywords: [{', '.join(f'"{kw}"' for kw in keywords)}]
received: "{datetime.now().isoformat()}"
priority: "{priority}"
status: pending
requires_approval: false
---

# LinkedIn Connection Request: {name}

## Profile Details

| Field | Value |
|-------|-------|
| **Name** | {name} |
| **Headline** | {headline} |
| **Mutual Connections** | {mutual} |
| **Priority** | {priority} |
| **Keywords** | {', '.join(keywords) or 'None'} |

## Suggested Actions

- [ ] Review profile on LinkedIn
- [ ] Check mutual connections for context
- [ ] Decide: Accept or Ignore
- [ ] If accepting, consider sending a welcome message

## Decision

**Action**: [ ] Accept  [ ] Ignore  [ ] Later

## Notes

<!-- Add any notes here -->

'''
        # Create action file
        safe_name = self._sanitize_filename(name[:30])
        action_filename = f'LINKEDIN_CONN_{timestamp}_{safe_name}.md'
        action_path = self.needs_action / action_filename
        action_path.write_text(content, encoding='utf-8')

        # Mark as processed
        self.processed_connections.add(item['id'])

        return action_path

    def _create_notification_action(self, item: Dict[str, Any]) -> Path:
        """Create action file for a notification."""
        text = item['text']
        notif_type = item['notification_type']
        keywords = item.get('matched_keywords', [])
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Determine priority
        high_priority_types = {'mention', 'comment', 'share'}
        priority = 'high' if notif_type in high_priority_types or keywords else 'low'

        content = f'''---
type: linkedin_notification
notification_id: "{item['id']}"
notification_type: "{notif_type}"
text: "{self._escape_yaml(text[:100])}"
matched_keywords: [{', '.join(f'"{kw}"' for kw in keywords)}]
received: "{datetime.now().isoformat()}"
priority: "{priority}"
status: pending
requires_approval: false
---

# LinkedIn Notification: {notif_type.replace('_', ' ').title()}

## Notification Details

| Field | Value |
|-------|-------|
| **Type** | {notif_type.replace('_', ' ').title()} |
| **Priority** | {priority} |
| **Keywords** | {', '.join(keywords) or 'None'} |
| **Received** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |

## Content

> {text}

## Suggested Actions

{self._get_notification_actions(notif_type)}

## Notes

<!-- Add any notes here -->

'''
        # Create action file
        safe_type = self._sanitize_filename(notif_type[:20])
        action_filename = f'LINKEDIN_NOTIF_{timestamp}_{safe_type}.md'
        action_path = self.needs_action / action_filename
        action_path.write_text(content, encoding='utf-8')

        # Mark as processed
        self.processed_notifications.add(item['id'])

        return action_path

    def _get_message_actions(self, priority: str, requires_approval: bool, keywords: List[str]) -> str:
        """Get suggested actions for messages."""
        actions = []

        if requires_approval:
            actions.append("- [ ] **REQUIRES APPROVAL** - Professional opportunity detected")

        if priority == 'high':
            actions.append("- [ ] Respond promptly (high priority)")

        if 'opportunity' in keywords or 'job' in keywords:
            actions.append("- [ ] Review opportunity details")
            actions.append("- [ ] Check company/sender background")

        if 'meeting' in keywords or 'call' in keywords:
            actions.append("- [ ] Check calendar availability")
            actions.append("- [ ] Propose meeting time if needed")

        actions.extend([
            "- [ ] Draft appropriate response",
            "- [ ] Send response via LinkedIn",
            "- [ ] Mark as handled"
        ])

        return '\n'.join(actions)

    def _get_notification_actions(self, notif_type: str) -> str:
        """Get suggested actions based on notification type."""
        actions = {
            'profile_view': """- [ ] Check who viewed your profile
- [ ] Evaluate if follow-up is appropriate
- [ ] Consider connecting if relevant""",
            'comment': """- [ ] Read the full comment
- [ ] Reply if appropriate
- [ ] Thank commenter if positive""",
            'reaction': """- [ ] Note engagement on your content
- [ ] No action usually required""",
            'mention': """- [ ] Read the full post/comment
- [ ] Respond to mention
- [ ] Engage with the conversation""",
            'share': """- [ ] See who shared your content
- [ ] Thank them if appropriate
- [ ] Engage with their post""",
            'career_update': """- [ ] Congratulate the person
- [ ] Strengthen connection if relevant""",
            'endorsement': """- [ ] Thank the person
- [ ] Consider endorsing back""",
        }

        return actions.get(notif_type, """- [ ] Review notification
- [ ] Take appropriate action
- [ ] Archive if no action needed""")

    def _sanitize_filename(self, text: str) -> str:
        """Create safe filename."""
        safe = re.sub(r'[<>:"/\\|?*]', '', text)
        safe = re.sub(r'\s+', '_', safe)
        return safe.strip('_') or 'item'

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
                self.logger.error("Failed to login to LinkedIn")
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
                                'type': item['type'],
                                'keywords': item.get('matched_keywords', [])
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

                # Use longer sleep to respect LinkedIn's rate limits
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

    parser = argparse.ArgumentParser(description='LinkedIn Watcher for AI Employee')
    parser.add_argument(
        '--vault',
        default='./AI_Employee_Vault',
        help='Path to Obsidian vault'
    )
    parser.add_argument(
        '--session',
        default='./config/linkedin_session',
        help='Path to store browser session'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=120,
        help='Check interval in seconds (default 120 for rate limits)'
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
    parser.add_argument(
        '--no-messages',
        action='store_true',
        help='Disable message monitoring'
    )
    parser.add_argument(
        '--no-connections',
        action='store_true',
        help='Disable connection request monitoring'
    )
    parser.add_argument(
        '--no-notifications',
        action='store_true',
        help='Disable notification monitoring'
    )

    args = parser.parse_args()

    try:
        watcher = LinkedInWatcher(
            vault_path=args.vault,
            session_path=args.session,
            check_interval=args.interval,
            headless=args.headless,
            keywords=args.keywords,
            monitor_messages=not args.no_messages,
            monitor_connections=not args.no_connections,
            monitor_notifications=not args.no_notifications
        )

        print("LinkedIn Watcher starting...")
        print(f"Session path: {args.session}")
        print(f"Check interval: {args.interval}s")
        print(f"Keywords: {watcher.keywords}")
        print(f"Monitoring: Messages={not args.no_messages}, Connections={not args.no_connections}, Notifications={not args.no_notifications}")
        print("\nIf this is first run, log in manually in the browser window")
        print("Press Ctrl+C to stop...")

        watcher.run()

    except ImportError as e:
        print(f"Error: {e}")
        print("\nInstall Playwright with:")
        print("pip install playwright")
        print("playwright install chromium")
    except KeyboardInterrupt:
        print("\nStopping...")
