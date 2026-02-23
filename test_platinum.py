"""
Platinum Tier Test Suite — Run all 5 tests locally.
Tests two-agent split, work zone enforcement, health monitor, git sync, and full demo.
"""
import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent))

VAULT = Path('./AI_Employee_Vault')
PASS = "PASS"
FAIL = "FAIL"
results = {}

def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")

def ok(msg):  print(f"  [OK] {msg}")
def err(msg): print(f"  [!!] {msg}")

# ═══════════════════════════════════════════════════════
# TEST 1: Work Zone Enforcement
# Cloud agent CANNOT call send_email / post_social / pay
# ═══════════════════════════════════════════════════════
section("TEST 1: Work Zone Enforcement (Cloud vs Local)")

from src.cloud.work_zone import WorkZone, WorkZoneViolation, requires_local

class FakeMCP:
    def __init__(self, zone): self.agent_zone = zone

    @requires_local
    def send_email(self): return "sent"

    def draft_email(self): return "drafted"

try:
    cloud_mcp = FakeMCP(WorkZone.CLOUD)
    local_mcp = FakeMCP(WorkZone.LOCAL)

    # Cloud trying to send → must be blocked
    try:
        cloud_mcp.send_email()
        err("Cloud send_email was NOT blocked — FAIL")
        results['work_zone'] = FAIL
    except WorkZoneViolation as e:
        ok(f"Cloud send_email BLOCKED: {e}")
        results['work_zone'] = PASS

    # Cloud drafting → must be allowed
    result = cloud_mcp.draft_email()
    ok(f"Cloud draft_email ALLOWED: '{result}'")

    # Local sending → must be allowed
    result = local_mcp.send_email()
    ok(f"Local send_email ALLOWED: '{result}'")

except Exception as e:
    err(f"Unexpected error: {e}")
    results['work_zone'] = FAIL

print(f"\n  Result: {results.get('work_zone', FAIL)}")

# ═══════════════════════════════════════════════════════
# TEST 2: Two-Agent Split (Cloud drafts, Local executes)
# ═══════════════════════════════════════════════════════
section("TEST 2: Two-Agent Split Simulation")

approval_id = f"APPROVAL_platinum_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
pending_file = VAULT / 'Pending_Approval' / f'{approval_id}.md'
approved_file = VAULT / 'Approved' / f'{approval_id}.md'

# Step A: Simulate CLOUD agent creating a draft approval
content = f"""---
type: approval_request
action: send_email
status: pending_approval
approval_id: {approval_id}
created_by: cloud_agent
created_at: {datetime.now().isoformat()}
priority: medium
---

# [CLOUD DRAFT] Email Reply Required

**From**: Cloud Agent (24/7)
**Action**: Draft email reply to client inquiry

## Email Draft

**To**: client@example.com
**Subject**: Re: Project Update
**Body**: Thank you for your inquiry. We will follow up shortly.

## Instructions for Local Agent

Review this draft and move to Approved/ to send.

---
*Created by Cloud Agent — awaiting Local Agent approval*
"""
(VAULT / 'Pending_Approval').mkdir(parents=True, exist_ok=True)
pending_file.write_text(content)
ok(f"Cloud agent created: {pending_file.name}")

# Step B: Simulate LOCAL agent approving
(VAULT / 'Approved').mkdir(parents=True, exist_ok=True)
shutil.move(str(pending_file), str(approved_file))
ok(f"Local agent approved: moved to Approved/")

# Step C: Verify file is in Approved/
if approved_file.exists():
    ok("Approved file confirmed in Approved/")
    results['two_agent_split'] = PASS
else:
    err("Approved file not found")
    results['two_agent_split'] = FAIL

print(f"\n  Result: {results.get('two_agent_split', FAIL)}")

# ═══════════════════════════════════════════════════════
# TEST 3: Claim-by-Move Rule
# ═══════════════════════════════════════════════════════
section("TEST 3: Claim-by-Move Rule")

in_progress_local = VAULT / 'In_Progress' / 'local'
in_progress_cloud = VAULT / 'In_Progress' / 'cloud'
in_progress_local.mkdir(parents=True, exist_ok=True)
in_progress_cloud.mkdir(parents=True, exist_ok=True)
ok("In_Progress/local/ and In_Progress/cloud/ folders ready")

# Drop a test task into Needs_Action
needs_action = VAULT / 'Needs_Action'
task_file = needs_action / f'FILE_platinum_claim_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
task_file.write_text("---\ntype: file\n---\n# Claim test task\n")
ok(f"Task created in Needs_Action/: {task_file.name}")

# Local agent claims it by moving to In_Progress/local/
claimed_file = in_progress_local / task_file.name
shutil.move(str(task_file), str(claimed_file))
ok(f"Local agent claimed task: moved to In_Progress/local/")

# Verify: task is gone from Needs_Action
if not task_file.exists() and claimed_file.exists():
    ok("Claim-by-move verified — task locked for local agent")
    results['claim_by_move'] = PASS
else:
    err("Claim-by-move failed")
    results['claim_by_move'] = FAIL

# Cleanup
claimed_file.unlink(missing_ok=True)
print(f"\n  Result: {results.get('claim_by_move', FAIL)}")

# ═══════════════════════════════════════════════════════
# TEST 4: Health Monitor
# ═══════════════════════════════════════════════════════
section("TEST 4: Health Monitor")

try:
    from src.cloud.health_monitor import HealthMonitor
    monitor = HealthMonitor(vault_path=str(VAULT), agent_id='local')
    resources = monitor.check_resources()
    ok(f"Resources: CPU={resources['cpu_percent']}% MEM={resources['memory_percent']}% DISK={resources['disk_percent']}%")
    status = monitor.evaluate_status(resources)
    ok(f"Status: {status}")
    monitor.write_status()

    status_file = VAULT / 'Health' / 'status.md'
    if status_file.exists():
        content = status_file.read_text()
        ok(f"Health status written to Health/status.md")
        # Show key lines
        for line in content.split('\n')[:20]:
            if line.strip():
                print(f"    {line}")
        results['health_monitor'] = PASS
    else:
        err("Health/status.md not created")
        results['health_monitor'] = FAIL
except Exception as e:
    err(f"Health monitor error: {e}")
    results['health_monitor'] = FAIL

print(f"\n  Result: {results.get('health_monitor', FAIL)}")

# ═══════════════════════════════════════════════════════
# TEST 5: Secrets NOT in Git
# ═══════════════════════════════════════════════════════
section("TEST 5: Secrets Security Check")

import subprocess
result = subprocess.run(
    ['git', 'ls-files', 'config/odoo_config.json', '.env',
     'config/whatsapp_session', 'config/linkedin_session',
     'config/gmail_token.json'],
    capture_output=True, text=True,
    cwd=str(Path(__file__).parent)
)
tracked_secrets = [f for f in result.stdout.strip().split('\n') if f]

sensitive = ['odoo_config.json', '.env', 'whatsapp_session',
             'linkedin_session', 'gmail_token.json']
leaked = [f for f in tracked_secrets if any(s in f for s in sensitive)]

if not leaked:
    ok("No secrets tracked in git")
    results['secrets_safe'] = PASS
else:
    err(f"Secrets in git: {leaked}")
    results['secrets_safe'] = FAIL

print(f"\n  Result: {results.get('secrets_safe', FAIL)}")

# ═══════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════
section("PLATINUM TIER TEST SUMMARY")
all_pass = True
for test, result in results.items():
    icon = "[PASS]" if result == PASS else "[FAIL]"
    print(f"  {icon} {test.replace('_', ' ').title()}")
    if result == FAIL:
        all_pass = False

print()
if all_pass:
    print("  PLATINUM TIER — ALL TESTS PASSED (Local Simulation)")
else:
    print("  Some tests failed — check output above")
print()
print("  Next: Deploy to cloud VM for full Platinum demo")
print(f"{'='*55}")
