"""
Shared pytest fixtures for AI Employee tests.

These fixtures are automatically available to all test files.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import json
from datetime import datetime


@pytest.fixture
def temp_vault(tmp_path):
    """
    Create a temporary vault structure for testing.

    Yields:
        Path: Path to the temporary vault directory
    """
    vault = tmp_path / "test_vault"
    vault.mkdir()

    # Create all required vault folders
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
        "Briefings",
        "Invoices"
    ]

    for folder in folders:
        (vault / folder).mkdir()

    # Create essential vault files
    (vault / "Dashboard.md").write_text("# Test Dashboard\n")
    (vault / "Company_Handbook.md").write_text("# Test Handbook\n")
    (vault / "Business_Goals.md").write_text("# Test Goals\n")

    yield vault

    # Cleanup is automatic with tmp_path


@pytest.fixture
def temp_drop_folder(temp_vault):
    """
    Get the Drop folder from temp vault.

    Yields:
        Path: Path to the Drop folder
    """
    return temp_vault / "Drop"


@pytest.fixture
def sample_text_file(temp_drop_folder):
    """
    Create a sample text file in the drop folder.

    Yields:
        Path: Path to the created file
    """
    file_path = temp_drop_folder / "sample.txt"
    file_path.write_text("This is a sample file for testing.")
    return file_path


@pytest.fixture
def sample_pdf_file(temp_drop_folder):
    """
    Create a sample PDF-like file in the drop folder.
    (Just creates a file with .pdf extension for testing)

    Yields:
        Path: Path to the created file
    """
    file_path = temp_drop_folder / "document.pdf"
    file_path.write_bytes(b"%PDF-1.4 fake pdf content")
    return file_path


@pytest.fixture
def sample_urgent_file(temp_drop_folder):
    """
    Create a file with urgent keyword in name.

    Yields:
        Path: Path to the created file
    """
    file_path = temp_drop_folder / "URGENT_invoice_review.xlsx"
    file_path.write_bytes(b"fake excel content")
    return file_path


@pytest.fixture
def multiple_files(temp_drop_folder):
    """
    Create multiple test files of different types.

    Yields:
        list[Path]: List of created file paths
    """
    files = []

    # Text file
    txt = temp_drop_folder / "notes.txt"
    txt.write_text("Some notes")
    files.append(txt)

    # CSV file
    csv = temp_drop_folder / "data.csv"
    csv.write_text("col1,col2\nval1,val2")
    files.append(csv)

    # JSON file
    json_file = temp_drop_folder / "config.json"
    json_file.write_text('{"key": "value"}')
    files.append(json_file)

    # Image file (fake)
    img = temp_drop_folder / "photo.jpg"
    img.write_bytes(b"fake image data")
    files.append(img)

    return files


@pytest.fixture
def mock_log_file(temp_vault):
    """
    Create a pre-existing log file for testing log append.

    Yields:
        Path: Path to the log file
    """
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = temp_vault / "Logs" / f"{today}.json"

    existing_logs = [
        {
            "timestamp": "2026-01-19T10:00:00",
            "watcher": "TestWatcher",
            "action_type": "existing_action",
            "details": {"test": True}
        }
    ]

    log_file.write_text(json.dumps(existing_logs, indent=2))
    return log_file


@pytest.fixture
def platinum_vault(temp_vault):
    """Create a vault with Platinum Tier folder structure."""
    platinum_folders = [
        "Needs_Action/email",
        "Needs_Action/accounting",
        "Needs_Action/social",
        "Needs_Action/local",
        "Pending_Approval/email",
        "Pending_Approval/accounting",
        "Pending_Approval/social",
        "Pending_Approval/payments",
        "In_Progress/cloud",
        "In_Progress/local",
        "Updates",
        "Signals",
        "Health",
    ]
    for folder in platinum_folders:
        (temp_vault / folder).mkdir(parents=True, exist_ok=True)
    return temp_vault


@pytest.fixture
def sample_task_file(platinum_vault):
    """Create a sample task file in Needs_Action/email/."""
    task_content = """---
type: email_triage
priority: high
created: 2026-01-28T10:00:00Z
---

# Email from client@acme.com

Subject: Invoice Request

Please send the January invoice at your earliest convenience.
"""
    task_path = platinum_vault / "Needs_Action" / "email" / "TASK_20260128_001.md"
    task_path.write_text(task_content, encoding="utf-8")
    return task_path
