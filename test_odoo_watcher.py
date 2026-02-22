"""Test Odoo Watcher — connects to real Odoo and fetches invoices/payments."""
import os
import sys
import logging
from pathlib import Path

os.environ['VAULT_PATH'] = './AI_Employee_Vault'

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 55)
print("ODOO WATCHER TEST")
print("=" * 55)
print("Connecting to Odoo and fetching invoices/payments...\n")

from src.watchers.odoo_watcher import OdooWatcher

# ── Initialize watcher ────────────────────────────────────────────────────────
watcher = OdooWatcher(
    vault_path='./AI_Employee_Vault',
    config_path='./config/odoo_config.json',
    check_interval=300
)

print("Watcher initialized. Checking for invoices and payments...\n")

# ── Run one check cycle ───────────────────────────────────────────────────────
items = watcher.check_for_updates()

print(f"\nFound {len(items)} item(s) from Odoo")

if items:
    print("\nCreating action files in Needs_Action/ ...")
    for item in items:
        try:
            path = watcher.create_action_file(item)
            print(f"  Created: {path.name}")
        except Exception as e:
            print(f"  Error creating action file: {e}")
else:
    print("\nNo new invoices or payments found.")
    print("This is normal if your Odoo account has no recent records.")
    print("Try creating a draft invoice in Odoo first, then re-run.")

# ── Show watcher status ───────────────────────────────────────────────────────
print()
status = watcher.get_status()
print("Watcher Status:")
print(f"  Connected    : {status.get('odoo_connected')}")
print(f"  Last sync    : {status.get('last_sync')}")
print(f"  Circuit open : {status.get('circuit_open')}")
print(f"  Failures     : {status.get('failure_count')}")

print()
print("=" * 55)
print("TEST COMPLETE")
print("Check AI_Employee_Vault/Needs_Action/ for INVOICE_*.md")
print("Check AI_Employee_Vault/Accounting/ for saved records")
print("=" * 55)
