"""Test APScheduler — loads orchestrator.yaml, registers jobs, triggers each immediately."""
import os
import sys
import json
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

os.environ['DRY_RUN'] = 'true'
os.environ['VAULT_PATH'] = './AI_Employee_Vault'

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 55)
print("SCHEDULER TEST (DRY RUN MODE)")
print("=" * 55)
print("Loads config/orchestrator.yaml and triggers all jobs\n")

# ── Patch heavy imports so orchestrator loads without credentials ─────────────
with patch.dict('sys.modules', {
    'google': MagicMock(),
    'google.oauth2': MagicMock(),
    'google.oauth2.credentials': MagicMock(),
    'google_auth_oauthlib': MagicMock(),
    'google_auth_oauthlib.flow': MagicMock(),
    'google.auth': MagicMock(),
    'google.auth.transport': MagicMock(),
    'google.auth.transport.requests': MagicMock(),
    'googleapiclient': MagicMock(),
    'googleapiclient.discovery': MagicMock(),
    'googleapiclient.errors': MagicMock(),
    'playwright': MagicMock(),
    'playwright.sync_api': MagicMock(),
}):
    from orchestrator import Orchestrator, OrchestratorConfig

# ── Create orchestrator in dry-run, filesystem-only (no credentials needed) ───
config = OrchestratorConfig(
    vault_path='./AI_Employee_Vault',
    dry_run=True,
    enabled_watchers=['filesystem'],       # only filesystem — no Gmail/WhatsApp/LinkedIn
    scheduler_config_path='./config/orchestrator.yaml',
    enable_reasoning_loop=False,           # skip reasoning loop for this test
)

print("Initializing orchestrator (filesystem watcher only) ...")
with patch('orchestrator.ApprovalWatcher'), \
     patch('orchestrator.RalphWiggumLoop'):
    orch = Orchestrator(config)

# ── Show registered jobs ──────────────────────────────────────────────────────
jobs = orch.scheduler.get_jobs()
print(f"\nRegistered scheduler jobs: {len(jobs)}")
print("-" * 55)
for job in jobs:
    trigger_str = str(job.trigger)
    next_run = getattr(job, 'next_run_time', None) or getattr(job, 'next_fire_time', 'starts when scheduler runs')
    print(f"  [{job.id}]")
    print(f"    Trigger  : {trigger_str}")
    print(f"    Next run : {next_run}")
print()

if not jobs:
    print("No jobs registered — check config/orchestrator.yaml scheduled_tasks section")
    sys.exit(1)

# ── Trigger each job NOW (dry-run — just logs, no real actions) ───────────────
print("Triggering all jobs immediately (DRY RUN) ...")
print("=" * 55)

job_handlers = {
    'ceo_briefing':    orch._job_ceo_briefing,
    'odoo_sync':       orch._job_sync_odoo,
    'engagement_fetch':orch._job_fetch_engagement,
    'log_cleanup':     lambda: orch._job_cleanup_logs(retention_days=90),
}

for job in jobs:
    print(f"\nRunning: [{job.id}]")
    print("-" * 30)
    handler = job_handlers.get(job.id)
    if handler:
        try:
            handler()
            print(f"  Result: OK")
        except Exception as e:
            print(f"  Error : {e}")
    else:
        print(f"  (no direct handler mapping for '{job.id}')")

# ── Check that log entries were written ───────────────────────────────────────
print()
print("=" * 55)
print("Checking today's log file ...")
from datetime import datetime
today = datetime.now().strftime('%Y-%m-%d')
log_file = Path('./AI_Employee_Vault/Logs') / f'{today}.json'

if log_file.exists():
    entries = json.loads(log_file.read_text())
    scheduler_entries = [e for e in entries if 'scheduled_job' in e.get('event', '')]
    print(f"Log file : {log_file}")
    print(f"Total entries : {len(entries)}")
    print(f"Scheduler entries : {len(scheduler_entries)}")
    for e in scheduler_entries[-8:]:  # last 8 scheduler entries
        print(f"  [{e['timestamp']}] {e['event']} — {e['details']}")
else:
    print(f"Log file not found: {log_file}")

print()
print("=" * 55)
print("SCHEDULER TEST COMPLETE")
print("All jobs ran in DRY RUN mode — no real actions taken")
print("=" * 55)
