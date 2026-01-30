"""
Tests for LinkedIn Watcher

Run with: pytest tests/test_linkedin_watcher.py -v
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sys

# Check if playwright is installed, skip tests if not
pytest.importorskip("playwright", reason="Playwright not installed")

from src.watchers.linkedin_watcher import LinkedInWatcher


class TestLinkedInWatcherInit:
    """Test LinkedIn Watcher initialization."""

    @pytest.fixture
    def temp_vault(self, tmp_path):
        """Create a temporary vault structure."""
        vault = tmp_path / "AI_Employee_Vault"
        folders = ["Inbox", "Needs_Action", "Logs", "Drop"]
        for folder in folders:
            (vault / folder).mkdir(parents=True, exist_ok=True)
        return vault

    def test_init_sets_vault_path(self, temp_vault):
        """Watcher initializes with correct vault path."""
        watcher = LinkedInWatcher(vault_path=str(temp_vault))
        assert watcher.vault_path == temp_vault

    def test_init_sets_watcher_name(self, temp_vault):
        """Watcher has correct name."""
        watcher = LinkedInWatcher(vault_path=str(temp_vault))
        assert watcher.watcher_name == "LinkedInWatcher"

    def test_init_default_check_interval(self, temp_vault):
        """Default check interval is 120 seconds."""
        watcher = LinkedInWatcher(vault_path=str(temp_vault))
        assert watcher.check_interval == 120

    def test_init_custom_check_interval(self, temp_vault):
        """Can set custom check interval."""
        watcher = LinkedInWatcher(vault_path=str(temp_vault), check_interval=300)
        assert watcher.check_interval == 300

    def test_init_default_session_path(self, temp_vault):
        """Session path defaults correctly."""
        watcher = LinkedInWatcher(vault_path=str(temp_vault))
        assert 'linkedin_session' in str(watcher.session_path)

    def test_init_custom_session_path(self, temp_vault, tmp_path):
        """Can set custom session path."""
        session_path = tmp_path / "custom_session"
        watcher = LinkedInWatcher(
            vault_path=str(temp_vault),
            session_path=str(session_path)
        )
        assert watcher.session_path == session_path

    def test_init_default_keywords(self, temp_vault):
        """Default keywords are set."""
        watcher = LinkedInWatcher(vault_path=str(temp_vault))
        assert 'urgent' in watcher.keywords
        assert 'opportunity' in watcher.keywords
        assert 'job' in watcher.keywords

    def test_init_custom_keywords(self, temp_vault):
        """Can set custom keywords."""
        keywords = ['custom', 'keywords']
        watcher = LinkedInWatcher(
            vault_path=str(temp_vault),
            keywords=keywords
        )
        assert watcher.keywords == keywords

    def test_init_monitoring_flags(self, temp_vault):
        """Monitoring flags default to True."""
        watcher = LinkedInWatcher(vault_path=str(temp_vault))
        assert watcher.monitor_messages is True
        assert watcher.monitor_connections is True
        assert watcher.monitor_notifications is True

    def test_init_custom_monitoring_flags(self, temp_vault):
        """Can disable specific monitoring."""
        watcher = LinkedInWatcher(
            vault_path=str(temp_vault),
            monitor_messages=False,
            monitor_connections=False
        )
        assert watcher.monitor_messages is False
        assert watcher.monitor_connections is False
        assert watcher.monitor_notifications is True

    def test_init_processed_sets_empty(self, temp_vault):
        """Processed sets start empty."""
        watcher = LinkedInWatcher(vault_path=str(temp_vault))
        assert len(watcher.processed_messages) == 0
        assert len(watcher.processed_connections) == 0
        assert len(watcher.processed_notifications) == 0


class TestClassifyNotification:
    """Test notification classification."""

    @pytest.fixture
    def watcher(self, tmp_path):
        """Create watcher for testing."""
        vault = tmp_path / "vault"
        (vault / "Needs_Action").mkdir(parents=True)
        (vault / "Logs").mkdir(parents=True)
        (vault / "Inbox").mkdir(parents=True)
        return LinkedInWatcher(vault_path=str(vault))

    def test_profile_view(self, watcher):
        """Profile view notification classified correctly."""
        result = watcher._classify_notification("John viewed your profile")
        assert result == 'profile_view'

    def test_comment(self, watcher):
        """Comment notification classified correctly."""
        result = watcher._classify_notification("Jane commented on your post")
        assert result == 'comment'

    def test_reaction(self, watcher):
        """Reaction notification classified correctly."""
        result = watcher._classify_notification("Bob liked your post")
        assert result == 'reaction'

        result = watcher._classify_notification("Alice reacted to your article")
        assert result == 'reaction'

    def test_mention(self, watcher):
        """Mention notification classified correctly."""
        result = watcher._classify_notification("Sam mentioned you in a comment")
        assert result == 'mention'

    def test_share(self, watcher):
        """Share notification classified correctly."""
        result = watcher._classify_notification("Mike shared your post")
        assert result == 'share'

    def test_career_update(self, watcher):
        """Career update notification classified correctly."""
        result = watcher._classify_notification("Lisa has a work anniversary")
        assert result == 'career_update'

        result = watcher._classify_notification("Tom started a new position")
        assert result == 'career_update'

    def test_endorsement(self, watcher):
        """Endorsement notification classified correctly."""
        result = watcher._classify_notification("Chris endorsed you for Python")
        assert result == 'endorsement'

    def test_unknown(self, watcher):
        """Unknown notification classified as other."""
        result = watcher._classify_notification("Something random happened")
        assert result == 'other'


class TestCreateActionFiles:
    """Test action file creation."""

    @pytest.fixture
    def watcher(self, tmp_path):
        """Create watcher for testing."""
        vault = tmp_path / "vault"
        (vault / "Needs_Action").mkdir(parents=True)
        (vault / "Logs").mkdir(parents=True)
        (vault / "Inbox").mkdir(parents=True)
        return LinkedInWatcher(vault_path=str(vault))

    def test_create_message_action(self, watcher):
        """Message action file created correctly."""
        item = {
            'type': 'linkedin_message',
            'id': 'msg_123',
            'sender': 'John Doe',
            'preview': 'Hello, I have an opportunity for you',
            'timestamp': '2h ago',
            'matched_keywords': ['opportunity'],
            'received_at': datetime.now().isoformat()
        }

        action_path = watcher.create_action_file(item)

        assert action_path.exists()
        assert action_path.suffix == '.md'
        assert 'LINKEDIN_MSG_' in action_path.name

        content = action_path.read_text()
        assert 'type: linkedin_message' in content
        assert 'John Doe' in content
        assert 'opportunity' in content
        assert 'priority: "high"' in content  # Has keyword

    def test_create_connection_action(self, watcher):
        """Connection action file created correctly."""
        item = {
            'type': 'linkedin_connection',
            'id': 'conn_456',
            'name': 'Jane Smith',
            'headline': 'Software Engineer at Tech Co',
            'mutual_connections': '5',
            'matched_keywords': [],
            'received_at': datetime.now().isoformat()
        }

        action_path = watcher.create_action_file(item)

        assert action_path.exists()
        assert 'LINKEDIN_CONN_' in action_path.name

        content = action_path.read_text()
        assert 'type: linkedin_connection' in content
        assert 'Jane Smith' in content
        assert 'Software Engineer' in content

    def test_create_notification_action(self, watcher):
        """Notification action file created correctly."""
        item = {
            'type': 'linkedin_notification',
            'id': 'notif_789',
            'text': 'Bob mentioned you in a comment',
            'notification_type': 'mention',
            'timestamp': '1h ago',
            'matched_keywords': [],
            'received_at': datetime.now().isoformat()
        }

        action_path = watcher.create_action_file(item)

        assert action_path.exists()
        assert 'LINKEDIN_NOTIF_' in action_path.name

        content = action_path.read_text()
        assert 'type: linkedin_notification' in content
        assert 'mention' in content
        assert 'Bob mentioned you' in content

    def test_message_with_keywords_high_priority(self, watcher):
        """Message with keywords gets high priority."""
        item = {
            'type': 'linkedin_message',
            'id': 'msg_urgent',
            'sender': 'HR Manager',
            'preview': 'URGENT: Job interview scheduled',
            'timestamp': 'now',
            'matched_keywords': ['urgent', 'job', 'interview'],
            'received_at': datetime.now().isoformat()
        }

        action_path = watcher.create_action_file(item)
        content = action_path.read_text()

        assert 'priority: "high"' in content

    def test_message_without_keywords_medium_priority(self, watcher):
        """Message without keywords gets medium priority."""
        item = {
            'type': 'linkedin_message',
            'id': 'msg_regular',
            'sender': 'Colleague',
            'preview': 'How are you doing?',
            'timestamp': '3h ago',
            'matched_keywords': [],
            'received_at': datetime.now().isoformat()
        }

        action_path = watcher.create_action_file(item)
        content = action_path.read_text()

        assert 'priority: "medium"' in content

    def test_marks_message_as_processed(self, watcher):
        """Creating action marks message as processed."""
        item = {
            'type': 'linkedin_message',
            'id': 'msg_unique',
            'sender': 'Test User',
            'preview': 'Test message',
            'timestamp': 'now',
            'matched_keywords': [],
            'received_at': datetime.now().isoformat()
        }

        watcher.create_action_file(item)
        assert 'msg_unique' in watcher.processed_messages

    def test_marks_connection_as_processed(self, watcher):
        """Creating action marks connection as processed."""
        item = {
            'type': 'linkedin_connection',
            'id': 'conn_unique',
            'name': 'Test Person',
            'headline': 'Title',
            'mutual_connections': '0',
            'matched_keywords': [],
            'received_at': datetime.now().isoformat()
        }

        watcher.create_action_file(item)
        assert 'conn_unique' in watcher.processed_connections


class TestHelperMethods:
    """Test helper methods."""

    @pytest.fixture
    def watcher(self, tmp_path):
        """Create watcher for testing."""
        vault = tmp_path / "vault"
        (vault / "Needs_Action").mkdir(parents=True)
        (vault / "Logs").mkdir(parents=True)
        (vault / "Inbox").mkdir(parents=True)
        return LinkedInWatcher(vault_path=str(vault))

    def test_sanitize_filename_removes_special_chars(self, watcher):
        """Sanitize removes special characters."""
        result = watcher._sanitize_filename('Hello<World>Test')
        assert '<' not in result
        assert '>' not in result

    def test_sanitize_filename_replaces_spaces(self, watcher):
        """Sanitize replaces spaces with underscores."""
        result = watcher._sanitize_filename('Hello World')
        assert result == 'Hello_World'

    def test_sanitize_filename_empty_returns_default(self, watcher):
        """Sanitize returns default for empty input."""
        result = watcher._sanitize_filename('***')
        assert result == 'item'

    def test_escape_yaml_quotes(self, watcher):
        """Escape YAML handles quotes."""
        result = watcher._escape_yaml('Say "Hello"')
        assert result == 'Say \\"Hello\\"'

    def test_escape_yaml_newlines(self, watcher):
        """Escape YAML replaces newlines."""
        result = watcher._escape_yaml('Line1\nLine2')
        assert '\n' not in result


class TestGetStatus:
    """Test status reporting."""

    @pytest.fixture
    def watcher(self, tmp_path):
        """Create watcher for testing."""
        vault = tmp_path / "vault"
        (vault / "Needs_Action").mkdir(parents=True)
        (vault / "Logs").mkdir(parents=True)
        (vault / "Inbox").mkdir(parents=True)
        return LinkedInWatcher(vault_path=str(vault))

    def test_get_status_returns_dict(self, watcher):
        """Get status returns dictionary."""
        status = watcher.get_status()
        assert isinstance(status, dict)

    def test_get_status_includes_name(self, watcher):
        """Status includes watcher name."""
        status = watcher.get_status()
        assert status['name'] == 'LinkedInWatcher'

    def test_get_status_includes_running(self, watcher):
        """Status includes running state."""
        status = watcher.get_status()
        assert 'is_running' in status

    def test_stop_sets_running_false(self, watcher):
        """Stop sets is_running to False."""
        watcher.is_running = True
        watcher.stop()
        assert watcher.is_running is False
