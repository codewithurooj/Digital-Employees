"""
End-to-End Tests for Bronze Tier: File Watcher Creates Action Files

This test verifies the complete workflow:
1. File dropped into Drop folder
2. FileSystemWatcher detects it
3. Action file created in Needs_Action
4. Original file copied to Inbox
5. Log entry created in Logs

Run with: pytest tests/test_e2e_bronze_tier.py -v
"""

import json
import time
import tempfile
import threading
from pathlib import Path
from datetime import datetime, date

import pytest

from src.watchers.filesystem_watcher import FileSystemWatcher


class TestBronzeTierE2E:
    """End-to-end tests for the Bronze Tier file watcher workflow."""

    @pytest.fixture
    def e2e_vault(self, tmp_path):
        """Create a complete vault structure for E2E testing."""
        vault = tmp_path / "AI_Employee_Vault"

        # Create all required folders
        folders = [
            "Inbox",
            "Needs_Action",
            "Plans",
            "Pending_Approval",
            "Approved",
            "Rejected",
            "Done",
            "Logs",
            "Drop",
            "Accounting",
            "Invoices",
            "Briefings",
        ]

        for folder in folders:
            (vault / folder).mkdir(parents=True, exist_ok=True)

        return vault

    def test_e2e_file_drop_creates_action_file(self, e2e_vault):
        """
        E2E: Dropping a file creates an action file in Needs_Action.

        This is the core Bronze Tier workflow.
        """
        # Arrange
        watcher = FileSystemWatcher(
            vault_path=str(e2e_vault),
            check_interval=1
        )

        drop_folder = e2e_vault / "Drop"
        needs_action = e2e_vault / "Needs_Action"

        # Act: Drop a test file
        test_file = drop_folder / "test_document.txt"
        test_file.write_text("This is a test document for E2E testing.")

        # Wait for watcher to detect (using polling check)
        new_files = watcher.check_for_updates()

        # Process the file
        assert len(new_files) == 1
        action_path = watcher.create_action_file(new_files[0])

        # Assert: Action file was created
        assert action_path.exists()
        assert action_path.parent == needs_action
        assert action_path.suffix == ".md"

        # Verify action file content
        content = action_path.read_text()
        assert "test_document.txt" in content
        assert "type: file_drop" in content
        assert "status: pending" in content

    def test_e2e_file_copied_to_inbox(self, e2e_vault):
        """
        E2E: Dropped file is copied to Inbox for processing.
        """
        # Arrange
        watcher = FileSystemWatcher(
            vault_path=str(e2e_vault),
            check_interval=1
        )

        drop_folder = e2e_vault / "Drop"
        inbox = e2e_vault / "Inbox"

        # Act: Drop a file
        test_file = drop_folder / "important_invoice.pdf"
        test_file.write_bytes(b"%PDF-1.4 fake pdf content for testing")

        new_files = watcher.check_for_updates()
        watcher.create_action_file(new_files[0])

        # Assert: File was copied to Inbox
        inbox_copy = inbox / "important_invoice.pdf"
        assert inbox_copy.exists()
        assert inbox_copy.read_bytes() == test_file.read_bytes()

    def test_e2e_high_priority_pdf_workflow(self, e2e_vault):
        """
        E2E: PDF files get high priority and document type.
        """
        # Arrange
        watcher = FileSystemWatcher(
            vault_path=str(e2e_vault),
            check_interval=1
        )

        drop_folder = e2e_vault / "Drop"

        # Act: Drop a PDF
        pdf_file = drop_folder / "contract.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 contract content")

        new_files = watcher.check_for_updates()
        action_path = watcher.create_action_file(new_files[0])

        # Assert: High priority and document type
        content = action_path.read_text()
        assert 'priority: "high"' in content
        assert 'file_type: "document"' in content

    def test_e2e_urgent_keyword_gets_high_priority(self, e2e_vault):
        """
        E2E: Files with 'urgent' keyword get high priority regardless of type.
        """
        # Arrange
        watcher = FileSystemWatcher(
            vault_path=str(e2e_vault),
            check_interval=1
        )

        drop_folder = e2e_vault / "Drop"

        # Act: Drop a file with urgent in name (even if low priority extension)
        urgent_file = drop_folder / "URGENT_report.txt"
        urgent_file.write_text("This is urgent!")

        new_files = watcher.check_for_updates()
        action_path = watcher.create_action_file(new_files[0])

        # Assert: High priority due to keyword
        content = action_path.read_text()
        assert 'priority: "high"' in content

    def test_e2e_log_entry_created(self, e2e_vault):
        """
        E2E: Processing a file creates a log entry.
        """
        # Arrange
        watcher = FileSystemWatcher(
            vault_path=str(e2e_vault),
            check_interval=1
        )

        drop_folder = e2e_vault / "Drop"
        logs_folder = e2e_vault / "Logs"

        # Act: Drop and process a file
        test_file = drop_folder / "data.csv"
        test_file.write_text("col1,col2\nval1,val2")

        new_files = watcher.check_for_updates()
        action_path = watcher.create_action_file(new_files[0])

        # Log the action (as would happen in run loop)
        watcher.log_action('file_processed', {
            'original_file': str(test_file),
            'action_file': str(action_path),
            'size': test_file.stat().st_size
        })

        # Assert: Log file was created (format is YYYY-MM-DD.json)
        today = date.today().isoformat()
        log_file = logs_folder / f"{today}.json"
        assert log_file.exists()

        # Verify log content
        log_content = json.loads(log_file.read_text())
        assert len(log_content) > 0

        last_entry = log_content[-1]
        assert last_entry['action_type'] == 'file_processed'
        assert last_entry['watcher'] == 'FileSystemWatcher'

    def test_e2e_multiple_files_workflow(self, e2e_vault):
        """
        E2E: Multiple files can be dropped and processed correctly.
        """
        # Arrange
        watcher = FileSystemWatcher(
            vault_path=str(e2e_vault),
            check_interval=1
        )

        drop_folder = e2e_vault / "Drop"
        needs_action = e2e_vault / "Needs_Action"
        inbox = e2e_vault / "Inbox"

        # Act: Drop multiple files of different types
        files = [
            ("report.pdf", b"%PDF content"),
            ("data.xlsx", b"Excel content"),
            ("notes.txt", "Plain text notes"),
            ("photo.jpg", b"\xFF\xD8\xFF image data"),
        ]

        for name, content in files:
            file_path = drop_folder / name
            if isinstance(content, bytes):
                file_path.write_bytes(content)
            else:
                file_path.write_text(content)

        # Process all files
        new_files = watcher.check_for_updates()
        assert len(new_files) == 4

        for file_path in new_files:
            watcher.create_action_file(file_path)

        # Assert: All action files created
        action_files = list(needs_action.glob("FILE_*.md"))
        assert len(action_files) == 4

        # Assert: All files copied to inbox
        inbox_files = [f for f in inbox.iterdir() if f.name != ".gitkeep"]
        assert len(inbox_files) == 4

    def test_e2e_hidden_files_ignored(self, e2e_vault):
        """
        E2E: Hidden files (starting with .) are ignored.
        """
        # Arrange
        watcher = FileSystemWatcher(
            vault_path=str(e2e_vault),
            check_interval=1
        )

        drop_folder = e2e_vault / "Drop"

        # Act: Drop hidden files
        hidden_file = drop_folder / ".hidden_config"
        hidden_file.write_text("secret config")

        temp_file = drop_folder / "~tempfile.tmp"
        temp_file.write_text("temp content")

        # Check for updates
        new_files = watcher.check_for_updates()

        # Assert: Hidden/temp files are ignored
        assert len(new_files) == 0

    def test_e2e_file_not_reprocessed(self, e2e_vault):
        """
        E2E: Once processed, a file is not processed again.
        """
        # Arrange
        watcher = FileSystemWatcher(
            vault_path=str(e2e_vault),
            check_interval=1
        )

        drop_folder = e2e_vault / "Drop"

        # Act: Drop a file
        test_file = drop_folder / "once_only.txt"
        test_file.write_text("Process me once")

        # First check
        new_files_1 = watcher.check_for_updates()
        assert len(new_files_1) == 1
        watcher.create_action_file(new_files_1[0])

        # Second check (same file should not appear)
        new_files_2 = watcher.check_for_updates()
        assert len(new_files_2) == 0

    def test_e2e_action_file_has_correct_structure(self, e2e_vault):
        """
        E2E: Action file has all required fields for downstream processing.
        """
        # Arrange
        watcher = FileSystemWatcher(
            vault_path=str(e2e_vault),
            check_interval=1
        )

        drop_folder = e2e_vault / "Drop"

        # Act: Drop a file
        test_file = drop_folder / "structured_test.docx"
        test_file.write_bytes(b"DOCX content simulation")

        new_files = watcher.check_for_updates()
        action_path = watcher.create_action_file(new_files[0])
        content = action_path.read_text()

        # Assert: Required frontmatter fields
        required_fields = [
            "type: file_drop",
            "original_name:",
            "original_path:",
            "size_bytes:",
            "size_human:",
            "extension:",
            "file_type:",
            "received:",
            "priority:",
            "status: pending",
            "requires_approval:",
        ]

        for field in required_fields:
            assert field in content, f"Missing required field: {field}"

        # Assert: Required markdown sections
        required_sections = [
            "# New File Dropped:",
            "## File Details",
            "## Location",
            "## Suggested Actions",
        ]

        for section in required_sections:
            assert section in content, f"Missing required section: {section}"

    def test_e2e_invoice_keyword_high_priority(self, e2e_vault):
        """
        E2E: Files with 'invoice' keyword get high priority.
        """
        # Arrange
        watcher = FileSystemWatcher(
            vault_path=str(e2e_vault),
            check_interval=1
        )

        drop_folder = e2e_vault / "Drop"

        # Act: Drop a file with invoice in name
        invoice_file = drop_folder / "invoice_2024_001.csv"
        invoice_file.write_text("item,amount\nService,100")

        new_files = watcher.check_for_updates()
        action_path = watcher.create_action_file(new_files[0])

        # Assert: High priority
        content = action_path.read_text()
        assert 'priority: "high"' in content

    def test_e2e_complete_bronze_workflow(self, e2e_vault):
        """
        E2E: Complete Bronze Tier workflow - from drop to action file ready for processing.

        This is the comprehensive test that verifies the entire Bronze Tier promise:
        "Files dropped trigger action files that can be processed by Claude Code"
        """
        # Arrange
        watcher = FileSystemWatcher(
            vault_path=str(e2e_vault),
            check_interval=1
        )

        drop_folder = e2e_vault / "Drop"
        needs_action = e2e_vault / "Needs_Action"
        inbox = e2e_vault / "Inbox"
        logs_folder = e2e_vault / "Logs"

        # Act: Simulate a realistic workflow
        # 1. Drop an invoice PDF
        invoice = drop_folder / "Invoice_URGENT_Company_2024.pdf"
        invoice.write_bytes(b"%PDF-1.4 Invoice content")

        # 2. Watcher detects the file
        new_files = watcher.check_for_updates()
        assert len(new_files) == 1, "Watcher should detect exactly one new file"

        # 3. Watcher creates action file
        action_path = watcher.create_action_file(new_files[0])

        # 4. Log the processing
        watcher.log_action('file_processed', {
            'original_file': str(invoice),
            'action_file': str(action_path),
            'size': invoice.stat().st_size
        })

        # VERIFY: All Bronze Tier guarantees

        # Guarantee 1: Action file exists in Needs_Action
        assert action_path.exists(), "Action file must exist"
        assert action_path.parent == needs_action, "Action file must be in Needs_Action"

        # Guarantee 2: Original file copied to Inbox
        inbox_copy = inbox / invoice.name
        assert inbox_copy.exists(), "File must be copied to Inbox"

        # Guarantee 3: Action file has correct priority (high due to URGENT keyword)
        content = action_path.read_text()
        assert 'priority: "high"' in content, "URGENT files must be high priority"

        # Guarantee 4: Action file has pending status (ready for processing)
        assert 'status: pending' in content, "New actions must have pending status"

        # Guarantee 5: Log entry created (format is YYYY-MM-DD.json)
        today = date.today().isoformat()
        log_file = logs_folder / f"{today}.json"
        assert log_file.exists(), "Log file must exist"

        log_content = json.loads(log_file.read_text())
        assert any(
            entry['action_type'] == 'file_processed'
            for entry in log_content
        ), "Must have file_processed log entry"

        # Guarantee 6: File not reprocessed
        new_files_again = watcher.check_for_updates()
        assert len(new_files_again) == 0, "Processed files must not be redetected"

        print("\n✅ Bronze Tier E2E Test Passed!")
        print(f"   - Action file: {action_path.name}")
        print(f"   - Priority: high")
        print(f"   - Status: pending")
        print(f"   - Log created: {log_file.name}")
