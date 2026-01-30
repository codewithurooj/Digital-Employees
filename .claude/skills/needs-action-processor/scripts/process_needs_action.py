#!/usr/bin/env python3
"""
Script for processing Needs_Action files in the AI Employee vault.
This script is designed to be used by Claude Code to process files
according to the Company Handbook rules.
"""

import os
import glob
import sys
from pathlib import Path
import re

def read_company_handbook(vault_path):
    """Read the Company Handbook rules."""
    handbook_path = Path(vault_path) / "Company_Handbook.md"
    if handbook_path.exists():
        return handbook_path.read_text(encoding='utf-8')
    return ""


def move_file_to_done(vault_path, file_path):
    """Move a processed file to the Done folder."""
    done_dir = os.path.join(vault_path, "Done")
    os.makedirs(done_dir, exist_ok=True)

    filename = os.path.basename(file_path)
    dest_path = os.path.join(done_dir, filename)

    os.rename(file_path, dest_path)
    return dest_path

def move_file_to_pending_approval(vault_path, file_path):
    """Move a file to the Pending_Approval folder."""
    pending_dir = os.path.join(vault_path, "Pending_Approval")
    os.makedirs(pending_dir, exist_ok=True)

    filename = os.path.basename(file_path)
    dest_path = os.path.join(pending_dir, filename)

    os.rename(file_path, dest_path)
    return dest_path

def analyze_and_process_file(vault_path, file_path):
    """Analyze a file and process it according to Company Handbook rules."""
    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Read the company handbook
    handbook_content = read_company_handbook(vault_path)

    # Apply rules based on content analysis
    # Check for payment-related keywords (requires approval for amounts > $100)
    payment_keywords = ['payment', 'pay', 'invoice', 'bill', 'expense', 'cost', 'charge']
    content_lower = content.lower()

    if any(keyword in content_lower for keyword in payment_keywords):
        # Check for amounts
        amount_pattern = r'\$([0-9,]+\.?[0-9]*)'
        amounts = re.findall(amount_pattern, content.replace(',', ''))

        for amount_str in amounts:
            try:
                amount = float(amount_str)
                # If amount is greater than 100, require approval
                if amount > 100:
                    print(f"Amount ${amount} detected in {file_path} - moving to Pending Approval")
                    new_path = move_file_to_pending_approval(vault_path, file_path)
                    return "PENDING_APPROVAL"
            except ValueError:
                continue

    # Check for urgency indicators
    urgency_keywords = ['urgent', 'asap', 'emergency', 'immediate', 'right now', 'today']
    if any(keyword in content_lower for keyword in urgency_keywords):
        print(f"Urgent task detected in {file_path} - processing with high priority")

    # Default: move to Done
    new_path = move_file_to_done(vault_path, file_path)
    return "DONE"

def scan_needs_action_folder(vault_path="./AI_Employee_Vault"):
    """Scan the Needs_Action folder for pending files."""
    needs_action_dir = os.path.join(vault_path, "Needs_Action")

    if not os.path.exists(needs_action_dir):
        print(f"Needs_Action directory does not exist: {needs_action_dir}")
        return []

    # Find all .md files in Needs_Action
    files = glob.glob(os.path.join(needs_action_dir, "*.md"))

    print(f"Found {len(files)} files in Needs_Action folder:")
    for file in files:
        print(f"  - {os.path.basename(file)}")

    return files

def process_needs_action_files(vault_path="./AI_Employee_Vault"):
    """Process all files in the Needs_Action directory."""
    files = scan_needs_action_folder(vault_path)

    if not files:
        print(f"No files found in Needs_Action directory: {os.path.join(vault_path, 'Needs_Action')}")
        return

    processed_count = 0
    pending_approval_count = 0

    for file_path in files:
        print(f"Processing: {file_path}")
        try:
            result = analyze_and_process_file(vault_path, file_path)
            if result == "PENDING_APPROVAL":
                pending_approval_count += 1
            processed_count += 1
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")

    print(f"Processing complete. Processed: {processed_count}, Pending Approval: {pending_approval_count}")

if __name__ == "__main__":
    # Allow vault path to be passed as command line argument
    vault_path = sys.argv[1] if len(sys.argv) > 1 else "./AI_Employee_Vault"
    process_needs_action_files(vault_path)
