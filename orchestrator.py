"""
AI Employee Orchestrator

Central coordinator that manages all watchers, approval workflows,
and scheduled tasks. This is the main entry point for running the
AI Employee system.

Usage:
    python orchestrator.py --vault ./AI_Employee_Vault

    # With specific watchers
    python orchestrator.py --vault ./AI_Employee_Vault --watchers filesystem gmail

    # Dry run mode (no actions executed)
    python orchestrator.py --vault ./AI_Employee_Vault --dry-run
"""

import os
import sys
import json
import signal
import logging
import argparse
import threading
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, Future

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.watchers import FileSystemWatcher, GmailWatcher, WhatsAppWatcher, LinkedInWatcher
from src.utils.hitl import ApprovalManager, ApprovalWatcher
from src.utils.retry_handler import CircuitBreaker, RateLimiter, get_rate_limiter
from src.utils.ralph_wiggum import RalphWiggumLoop, LoopConfig, LoopState


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""
    vault_path: str
    dry_run: bool = True
    enabled_watchers: List[str] = field(default_factory=lambda: ['filesystem'])
    check_interval: int = 60
    max_workers: int = 4

    # Watcher-specific config
    gmail_credentials: Optional[str] = None
    gmail_query: str = 'is:unread is:important'
    whatsapp_session: Optional[str] = None
    whatsapp_keywords: Optional[List[str]] = None
    filesystem_watch_folder: Optional[str] = None
    linkedin_session: Optional[str] = None
    linkedin_keywords: Optional[List[str]] = None

    # Scheduler config
    scheduler_config_path: str = './config/orchestrator.yaml'

    # Reasoning loop config
    enable_reasoning_loop: bool = True
    max_loop_iterations: int = 10
    loop_timeout_seconds: int = 300
    task_process_interval: int = 30  # Seconds between task processing checks


class Orchestrator:
    """
    Central orchestrator for the AI Employee system.

    Manages:
    - Multiple watchers running in parallel
    - Approval workflow monitoring
    - Health checks and logging
    - Graceful shutdown
    """

    def __init__(self, config: OrchestratorConfig):
        """
        Initialize the orchestrator.

        Args:
            config: Orchestrator configuration
        """
        self.config = config
        self.vault_path = Path(config.vault_path)
        self.logs_path = self.vault_path / 'Logs'
        self.logs_path.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self._setup_logging()

        # Component instances
        self.watchers: Dict[str, Any] = {}
        self.watcher_threads: Dict[str, threading.Thread] = {}
        self.approval_manager = ApprovalManager(str(self.vault_path))
        self.approval_watcher: Optional[ApprovalWatcher] = None

        # Circuit breakers for external services
        self.circuit_breakers: Dict[str, CircuitBreaker] = {
            'gmail': CircuitBreaker('gmail', failure_threshold=5),
            'whatsapp': CircuitBreaker('whatsapp', failure_threshold=3),
            'linkedin': CircuitBreaker('linkedin', failure_threshold=3),
        }

        # Rate limiters
        self.rate_limiters: Dict[str, RateLimiter] = {
            'email': get_rate_limiter('email'),
            'payment': get_rate_limiter('payment'),
            'social': get_rate_limiter('social_post'),
        }

        # State
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self._shutdown_event = threading.Event()

        # Scheduler
        self.scheduler = BackgroundScheduler(timezone='UTC')
        self._setup_scheduler()

        # Reasoning loop
        self.reasoning_loop: Optional[RalphWiggumLoop] = None
        self.task_processor_thread: Optional[threading.Thread] = None
        self._processing_tasks: Dict[str, LoopState] = {}  # Track active loops
        self._task_locks: Dict[str, threading.Lock] = {}  # Prevent duplicate processing

        if config.enable_reasoning_loop:
            loop_config = LoopConfig(
                max_iterations=config.max_loop_iterations,
                timeout_seconds=config.loop_timeout_seconds
            )
            self.reasoning_loop = RalphWiggumLoop(
                vault_path=str(self.vault_path),
                config=loop_config
            )
            self.logger.info("Reasoning loop initialized")

        self.logger.info(f"Orchestrator initialized. Vault: {self.vault_path}")
        self.logger.info(f"Dry run mode: {config.dry_run}")

    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        self.logger = logging.getLogger('Orchestrator')
        self.logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(console_handler)

        # File handler
        log_file = self.logs_path / 'orchestrator.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(file_handler)

    def _initialize_watchers(self) -> None:
        """Initialize enabled watchers."""
        for watcher_name in self.config.enabled_watchers:
            try:
                if watcher_name == 'filesystem':
                    watch_folder = self.config.filesystem_watch_folder or str(self.vault_path / 'Drop')
                    self.watchers['filesystem'] = FileSystemWatcher(
                        vault_path=str(self.vault_path),
                        watch_folder=watch_folder,
                        check_interval=self.config.check_interval
                    )
                    self.logger.info(f"FileSystemWatcher initialized: {watch_folder}")

                elif watcher_name == 'gmail':
                    if GmailWatcher is None:
                        self.logger.warning("Gmail API not installed, skipping GmailWatcher")
                        continue

                    credentials = self.config.gmail_credentials or './config/gmail_credentials.json'
                    if not Path(credentials).exists():
                        self.logger.warning(f"Gmail credentials not found: {credentials}")
                        continue

                    self.watchers['gmail'] = GmailWatcher(
                        vault_path=str(self.vault_path),
                        credentials_path=credentials,
                        query=self.config.gmail_query,
                        check_interval=self.config.check_interval
                    )
                    self.logger.info("GmailWatcher initialized")

                elif watcher_name == 'whatsapp':
                    if WhatsAppWatcher is None:
                        self.logger.warning("Playwright not installed, skipping WhatsAppWatcher")
                        continue

                    session = self.config.whatsapp_session or './config/whatsapp_session'
                    self.watchers['whatsapp'] = WhatsAppWatcher(
                        vault_path=str(self.vault_path),
                        session_path=session,
                        keywords=self.config.whatsapp_keywords,
                        check_interval=self.config.check_interval
                    )
                    self.logger.info("WhatsAppWatcher initialized")

                elif watcher_name == 'linkedin':
                    if LinkedInWatcher is None:
                        self.logger.warning("Playwright not installed, skipping LinkedInWatcher")
                        continue

                    session = self.config.linkedin_session or './config/linkedin_session'
                    self.watchers['linkedin'] = LinkedInWatcher(
                        vault_path=str(self.vault_path),
                        session_path=session,
                        keywords=self.config.linkedin_keywords,
                        check_interval=max(self.config.check_interval, 120)  # Min 120s for LinkedIn
                    )
                    self.logger.info("LinkedInWatcher initialized")

                else:
                    self.logger.warning(f"Unknown watcher type: {watcher_name}")

            except Exception as e:
                self.logger.error(f"Failed to initialize {watcher_name} watcher: {e}")

    # ------------------------------------------------------------------
    # Scheduler
    # ------------------------------------------------------------------

    def _load_yaml_config(self) -> dict:
        """Load orchestrator.yaml; return empty dict on any error."""
        config_path = Path(self.config.scheduler_config_path)
        if not config_path.exists():
            self.logger.warning(f"Scheduler config not found: {config_path}")
            return {}
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"Failed to load scheduler config: {e}")
            return {}

    def _setup_scheduler(self) -> None:
        """Register cron jobs from orchestrator.yaml scheduled_tasks section."""
        yaml_cfg = self._load_yaml_config()
        tasks = yaml_cfg.get('scheduled_tasks', {})

        if not tasks:
            self.logger.info("No scheduled tasks found in config")
            return

        # Map task names / action values to handler methods
        handlers = {
            # skill-based tasks
            'ceo_briefing': self._job_ceo_briefing,
            # action-based tasks
            'sync_odoo':        self._job_sync_odoo,
            'fetch_engagement': self._job_fetch_engagement,
            'cleanup_logs':     self._job_cleanup_logs,
        }

        for task_name, task_cfg in tasks.items():
            if not task_cfg.get('enabled', True):
                self.logger.info(f"Scheduler: '{task_name}' is disabled, skipping")
                continue

            cron_expr = task_cfg.get('schedule', '')
            if not cron_expr:
                self.logger.warning(f"Scheduler: '{task_name}' has no schedule, skipping")
                continue

            # Resolve handler: prefer skill/action key, fall back to task_name
            handler_key = task_cfg.get('skill') or task_cfg.get('action') or task_name
            handler = handlers.get(handler_key)
            if handler is None:
                self.logger.warning(
                    f"Scheduler: no handler for '{task_name}' (key='{handler_key}'), skipping"
                )
                continue

            # Parse cron string "MIN HOUR DOM MON DOW"
            parts = cron_expr.split()
            if len(parts) != 5:
                self.logger.error(f"Scheduler: invalid cron '{cron_expr}' for '{task_name}'")
                continue

            minute, hour, day, month, day_of_week = parts
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone='UTC',
            )

            # Pass retention_days for cleanup_logs
            kwargs = {}
            if handler_key == 'cleanup_logs':
                kwargs['retention_days'] = task_cfg.get('retention_days', 90)

            self.scheduler.add_job(
                handler,
                trigger=trigger,
                id=task_name,
                name=task_name,
                kwargs=kwargs,
                replace_existing=True,
                misfire_grace_time=300,  # Allow up to 5-min late start
            )
            self.logger.info(f"Scheduler: registered '{task_name}' -> cron '{cron_expr}'")

    # ------------------------------------------------------------------
    # Job handlers
    # ------------------------------------------------------------------

    def _job_ceo_briefing(self) -> None:
        """Generate the Monday Morning CEO Briefing."""
        self.logger.info("[Scheduler] Running CEO Briefing job")
        self._log_event('scheduled_job_start', {'job': 'ceo_briefing'})
        try:
            if self.config.dry_run:
                self.logger.info("[Scheduler][DRY RUN] Would generate CEO briefing")
                return

            from src.skills.ceo_briefing import CEOBriefingSkill
            skill = CEOBriefingSkill(vault_path=str(self.vault_path))
            result = skill.generate_briefing()
            self.logger.info(f"[Scheduler] CEO Briefing generated: {result}")
            self._log_event('scheduled_job_done', {'job': 'ceo_briefing', 'result': str(result)})
        except Exception as e:
            self.logger.error(f"[Scheduler] CEO Briefing failed: {e}")
            self._log_event('scheduled_job_error', {'job': 'ceo_briefing', 'error': str(e)})

    def _job_sync_odoo(self) -> None:
        """Trigger an Odoo sync check."""
        self.logger.info("[Scheduler] Running Odoo sync job")
        self._log_event('scheduled_job_start', {'job': 'sync_odoo'})
        try:
            if self.config.dry_run:
                self.logger.info("[Scheduler][DRY RUN] Would sync Odoo")
                return

            from src.watchers.odoo_watcher import OdooWatcher
            watcher = OdooWatcher(vault_path=str(self.vault_path))
            items = watcher.check_for_updates()
            for item in items:
                watcher.create_action_file(item)
            self.logger.info(f"[Scheduler] Odoo sync: {len(items)} item(s) queued")
            self._log_event('scheduled_job_done', {'job': 'sync_odoo', 'items': len(items)})
        except Exception as e:
            self.logger.error(f"[Scheduler] Odoo sync failed: {e}")
            self._log_event('scheduled_job_error', {'job': 'sync_odoo', 'error': str(e)})

    def _job_fetch_engagement(self) -> None:
        """Fetch social media engagement metrics."""
        self.logger.info("[Scheduler] Running engagement fetch job")
        self._log_event('scheduled_job_start', {'job': 'fetch_engagement'})
        try:
            if self.config.dry_run:
                self.logger.info("[Scheduler][DRY RUN] Would fetch engagement metrics")
                return

            from src.skills.social_posting import SocialPostingSkill
            skill = SocialPostingSkill(vault_path=str(self.vault_path))
            summary = skill.fetch_engagement_summary()
            self.logger.info(f"[Scheduler] Engagement fetched: {summary}")
            self._log_event('scheduled_job_done', {'job': 'fetch_engagement', 'summary': str(summary)})
        except Exception as e:
            self.logger.error(f"[Scheduler] Engagement fetch failed: {e}")
            self._log_event('scheduled_job_error', {'job': 'fetch_engagement', 'error': str(e)})

    def _job_cleanup_logs(self, retention_days: int = 90) -> None:
        """Delete log files older than retention_days."""
        self.logger.info(f"[Scheduler] Running log cleanup (retain {retention_days} days)")
        self._log_event('scheduled_job_start', {'job': 'cleanup_logs', 'retention_days': retention_days})
        try:
            cutoff = datetime.now() - timedelta(days=retention_days)
            removed = 0
            for log_file in self.logs_path.glob('*.json'):
                # Filenames are YYYY-MM-DD.json
                try:
                    file_date = datetime.strptime(log_file.stem, '%Y-%m-%d')
                    if file_date < cutoff:
                        log_file.unlink()
                        removed += 1
                        self.logger.info(f"[Scheduler] Deleted old log: {log_file.name}")
                except ValueError:
                    pass  # Skip files that don't match date format
            self.logger.info(f"[Scheduler] Log cleanup done: {removed} file(s) removed")
            self._log_event('scheduled_job_done', {'job': 'cleanup_logs', 'removed': removed})
        except Exception as e:
            self.logger.error(f"[Scheduler] Log cleanup failed: {e}")
            self._log_event('scheduled_job_error', {'job': 'cleanup_logs', 'error': str(e)})

    def _start_watcher(self, name: str, watcher: Any) -> None:
        """Start a watcher in a separate thread."""
        def run_watcher():
            try:
                self.logger.info(f"Starting {name} watcher thread")
                if hasattr(watcher, 'run_with_observer'):
                    watcher.run_with_observer()
                else:
                    watcher.run()
            except Exception as e:
                self.logger.error(f"Watcher {name} crashed: {e}")
            finally:
                self.logger.info(f"Watcher {name} stopped")

        thread = threading.Thread(target=run_watcher, name=f"watcher-{name}", daemon=True)
        thread.start()
        self.watcher_threads[name] = thread

    def _start_approval_watcher(self) -> None:
        """Start the approval workflow watcher."""
        self.approval_watcher = ApprovalWatcher(str(self.vault_path))

        # Register action handlers
        self._register_approval_handlers()

        def run_approval_watcher():
            try:
                self.approval_watcher.run()
            except Exception as e:
                self.logger.error(f"Approval watcher crashed: {e}")

        thread = threading.Thread(target=run_approval_watcher, name="approval-watcher", daemon=True)
        thread.start()
        self.watcher_threads['approval'] = thread

    def _register_approval_handlers(self) -> None:
        """Register handlers for approved actions."""
        if self.approval_watcher is None:
            return

        # Handler for approved emails
        def handle_email(details: dict, filepath: Path) -> bool:
            if self.config.dry_run:
                self.logger.info(f"[DRY RUN] Would send email: {details.get('subject')}")
                return True

            if not self.rate_limiters['email'].allow():
                self.logger.warning("Email rate limit reached")
                return False

            # Actual email sending would go here
            self.logger.info(f"Sending email: {details.get('subject')}")
            return True

        # Handler for approved payments
        def handle_payment(details: dict, filepath: Path) -> bool:
            if self.config.dry_run:
                self.logger.info(f"[DRY RUN] Would process payment: ${details.get('amount')}")
                return True

            if not self.rate_limiters['payment'].allow():
                self.logger.warning("Payment rate limit reached")
                return False

            # Actual payment processing would go here
            self.logger.info(f"Processing payment: ${details.get('amount')}")
            return True

        # Handler for social media posts
        def handle_social_post(details: dict, filepath: Path) -> bool:
            if self.config.dry_run:
                self.logger.info(f"[DRY RUN] Would post to {details.get('platform')}")
                return True

            if not self.rate_limiters['social'].allow():
                self.logger.warning("Social post rate limit reached")
                return False

            self.logger.info(f"Posting to {details.get('platform')}")
            return True

        self.approval_watcher.register_handler('send_email', handle_email)
        self.approval_watcher.register_handler('payment', handle_payment)
        self.approval_watcher.register_handler('post_social', handle_social_post)

    def _start_task_processor(self) -> None:
        """Start the task processor thread for reasoning loops."""
        if not self.reasoning_loop:
            return

        def run_task_processor():
            self.logger.info("Task processor started")
            while self.is_running and not self._shutdown_event.is_set():
                try:
                    self._process_needs_action_tasks()
                except Exception as e:
                    self.logger.error(f"Task processor error: {e}")

                # Wait for interval or shutdown
                self._shutdown_event.wait(timeout=self.config.task_process_interval)

            self.logger.info("Task processor stopped")

        self.task_processor_thread = threading.Thread(
            target=run_task_processor,
            name="task-processor",
            daemon=True
        )
        self.task_processor_thread.start()

    def _process_needs_action_tasks(self) -> None:
        """Process pending tasks in Needs_Action using the reasoning loop."""
        if not self.reasoning_loop:
            return

        needs_action_dir = self.vault_path / 'Needs_Action'
        if not needs_action_dir.exists():
            return

        for task_file in needs_action_dir.glob('*.md'):
            if self._shutdown_event.is_set():
                break

            # Skip if already being processed
            task_key = str(task_file)
            if task_key in self._processing_tasks:
                continue

            # Skip if locked
            if task_key in self._task_locks:
                if self._task_locks[task_key].locked():
                    continue

            # Create lock for this task
            if task_key not in self._task_locks:
                self._task_locks[task_key] = threading.Lock()

            # Try to acquire lock
            if not self._task_locks[task_key].acquire(blocking=False):
                continue

            try:
                self.logger.info(f"Processing task: {task_file.name}")

                # Build prompt from task file
                prompt = self._build_prompt_from_task(task_file)

                if self.config.dry_run:
                    self.logger.info(f"[DRY RUN] Would process task: {task_file.name}")
                    self.logger.debug(f"[DRY RUN] Prompt preview: {prompt[:200]}...")
                    continue

                # Start reasoning loop in a thread
                def process_task(tf: Path, p: str, key: str):
                    try:
                        result = self.reasoning_loop.start_loop(
                            prompt=p,
                            task_file=tf
                        )
                        self._processing_tasks[key] = result

                        self._log_event('task_processed', {
                            'task_file': str(tf),
                            'loop_id': result.loop_id,
                            'status': result.status,
                            'iterations': result.iterations
                        })

                        self.logger.info(
                            f"Task {tf.name} completed: status={result.status}, iterations={result.iterations}"
                        )
                    except Exception as e:
                        self.logger.error(f"Error processing task {tf.name}: {e}")
                    finally:
                        # Cleanup
                        if key in self._processing_tasks:
                            del self._processing_tasks[key]
                        if key in self._task_locks:
                            try:
                                self._task_locks[key].release()
                            except:
                                pass

                # Run in separate thread to not block other tasks
                thread = threading.Thread(
                    target=process_task,
                    args=(task_file, prompt, task_key),
                    name=f"task-{task_file.stem[:20]}",
                    daemon=True
                )
                thread.start()

            except Exception as e:
                self.logger.error(f"Error starting task {task_file.name}: {e}")
                if task_key in self._task_locks:
                    try:
                        self._task_locks[task_key].release()
                    except:
                        pass

    def _build_prompt_from_task(self, task_file: Path) -> str:
        """
        Build a prompt for Claude from a task file.

        Args:
            task_file: Path to the task markdown file

        Returns:
            Prompt string for Claude
        """
        try:
            content = task_file.read_text(encoding='utf-8')
        except Exception as e:
            self.logger.error(f"Error reading task file {task_file}: {e}")
            return f"Process the task in file: {task_file.name}"

        # Build comprehensive prompt
        prompt = f"""# Task Processing Request

You are an AI Employee assistant. Process the following task from the Needs_Action folder.

## Task File
**Filename**: {task_file.name}
**Path**: {task_file}

## Task Content

{content}

## Instructions

1. Analyze the task content above
2. Determine what actions need to be taken
3. Execute the required actions using available tools
4. If any action requires human approval (payments, emails, sensitive operations), output REQUIRES_APPROVAL with details
5. Move the task file to the appropriate folder when done:
   - Move to `Done/` if task is completed successfully
   - Move to `Pending_Approval/` if waiting for human approval
6. When fully complete, output: <promise>TASK_COMPLETE</promise>

## Company Rules

Follow the Company Handbook rules:
- Auto-approve small recurring payments (< $50) to known vendors
- Require approval for payments > $100, new recipients, international transfers
- Never auto-approve crypto, wire transfers, or personal accounts
- Flag unknown senders for email
- All social media posts require approval

## Available Actions

You can:
- Read and analyze files
- Create approval requests in Pending_Approval/
- Move files between folders
- Send emails (with approval if to external recipients)
- Update the Dashboard

Begin processing this task now.
"""

        return prompt

    def _is_task_locked(self, task_file: Path) -> bool:
        """Check if a task file is currently being processed."""
        task_key = str(task_file)
        if task_key in self._task_locks:
            return self._task_locks[task_key].locked()
        return False

    def _update_dashboard(self) -> None:
        """Update the dashboard with current status."""
        dashboard_path = self.vault_path / 'Dashboard.md'

        # Count items in each folder
        needs_action = len(list((self.vault_path / 'Needs_Action').glob('*.md')))
        pending_approval = len(list((self.vault_path / 'Pending_Approval').glob('*.md')))
        done_today = len(list((self.vault_path / 'Done').glob(f'*{datetime.now().strftime("%Y%m%d")}*.md')))

        # Get watcher status
        watcher_status = []
        for name, watcher in self.watchers.items():
            status = watcher.get_status() if hasattr(watcher, 'get_status') else {'name': name}
            watcher_status.append(f"- **{name}**: {'Running' if status.get('is_running', True) else 'Stopped'}")

        uptime = ""
        if self.start_time:
            delta = datetime.now() - self.start_time
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            uptime = f"{hours}h {minutes}m"

        content = f'''# AI Employee Dashboard

> Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## System Status

- **Status**: {'🟢 Online' if self.is_running else '🔴 Offline'}
- **Mode**: {'🧪 DRY RUN' if self.config.dry_run else '🚀 LIVE'}
- **Uptime**: {uptime or 'N/A'}
- **Active Watchers**: {len(self.watchers)}

## Active Watchers

{chr(10).join(watcher_status) or '- None active'}

## Queue Status

| Queue | Count |
|-------|-------|
| Needs Action | {needs_action} |
| Pending Approval | {pending_approval} |
| Completed Today | {done_today} |

## Rate Limits

| Service | Remaining | Resets In |
|---------|-----------|-----------|
| Email | {self.rate_limiters['email'].remaining()}/{self.rate_limiters['email'].max_calls} | {int(self.rate_limiters['email'].time_until_reset())}s |
| Payment | {self.rate_limiters['payment'].remaining()}/{self.rate_limiters['payment'].max_calls} | {int(self.rate_limiters['payment'].time_until_reset())}s |
| Social | {self.rate_limiters['social'].remaining()}/{self.rate_limiters['social'].max_calls} | {int(self.rate_limiters['social'].time_until_reset())}s |

## Circuit Breakers

| Service | State |
|---------|-------|
| Gmail | {self.circuit_breakers['gmail'].state.value} |
| WhatsApp | {self.circuit_breakers['whatsapp'].state.value} |
| LinkedIn | {self.circuit_breakers['linkedin'].state.value} |

## Reasoning Loop

- **Enabled**: {'Yes' if self.config.enable_reasoning_loop else 'No'}
- **Active Tasks**: {len(self._processing_tasks)}
- **Max Iterations**: {self.config.max_loop_iterations}
- **Timeout**: {self.config.loop_timeout_seconds}s per iteration

## Recent Activity

<!-- Auto-updated by orchestrator -->

---
*Dashboard auto-updated by AI Employee Orchestrator*
'''

        dashboard_path.write_text(content, encoding='utf-8')

    def _log_event(self, event_type: str, details: dict) -> None:
        """Log an event to the daily log file."""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_path / f'{today}.json'

        entry = {
            'timestamp': datetime.now().isoformat(),
            'component': 'Orchestrator',
            'event': event_type,
            'details': details
        }

        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text())
            except:
                logs = []

        logs.append(entry)
        log_file.write_text(json.dumps(logs, indent=2), encoding='utf-8')

    def _health_check(self) -> dict:
        """Perform health check on all components."""
        health = {
            'orchestrator': 'healthy',
            'watchers': {},
            'approval_watcher': 'unknown',
            'timestamp': datetime.now().isoformat()
        }

        # Check watchers
        for name, thread in self.watcher_threads.items():
            health['watchers'][name] = 'running' if thread.is_alive() else 'stopped'

        return health

    def start(self) -> None:
        """Start the orchestrator and all components."""
        self.logger.info("=" * 50)
        self.logger.info("Starting AI Employee Orchestrator")
        self.logger.info("=" * 50)

        self.is_running = True
        self.start_time = datetime.now()

        # Initialize and start watchers
        self._initialize_watchers()

        for name, watcher in self.watchers.items():
            self._start_watcher(name, watcher)

        # Start approval watcher
        self._start_approval_watcher()

        # Start task processor (reasoning loop)
        if self.config.enable_reasoning_loop:
            self._start_task_processor()
            self.logger.info("Task processor started (reasoning loop enabled)")

        # Start APScheduler for cron-based tasks
        self.scheduler.start()
        job_count = len(self.scheduler.get_jobs())
        self.logger.info(f"Scheduler started with {job_count} job(s)")

        # Log startup
        self._log_event('orchestrator_started', {
            'watchers': list(self.watchers.keys()),
            'dry_run': self.config.dry_run,
            'reasoning_loop_enabled': self.config.enable_reasoning_loop
        })

        # Update dashboard
        self._update_dashboard()

        self.logger.info(f"Orchestrator started with {len(self.watchers)} watchers")

    def run(self) -> None:
        """Run the main orchestrator loop."""
        self.start()

        try:
            while self.is_running and not self._shutdown_event.is_set():
                # Periodic tasks
                self._update_dashboard()

                # Health check
                health = self._health_check()

                # Restart crashed watchers
                for name, status in health['watchers'].items():
                    if status == 'stopped' and name in self.watchers:
                        self.logger.warning(f"Restarting crashed watcher: {name}")
                        self._start_watcher(name, self.watchers[name])

                # Wait for shutdown or interval
                self._shutdown_event.wait(timeout=30)

        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the orchestrator and all components."""
        self.logger.info("Stopping orchestrator...")
        self.is_running = False
        self._shutdown_event.set()

        # Stop all watchers
        for name, watcher in self.watchers.items():
            try:
                watcher.stop()
            except:
                pass

        # Stop scheduler
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.logger.info("Scheduler stopped")

        # Stop approval watcher
        if self.approval_watcher:
            self.approval_watcher.stop()

        # Wait for threads to finish
        for name, thread in self.watcher_threads.items():
            thread.join(timeout=5)

        # Final dashboard update
        self._update_dashboard()

        # Log shutdown
        self._log_event('orchestrator_stopped', {
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        })

        self.logger.info("Orchestrator stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='AI Employee Orchestrator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Basic start with filesystem watcher
  python orchestrator.py --vault ./AI_Employee_Vault

  # Enable multiple watchers
  python orchestrator.py --vault ./AI_Employee_Vault --watchers filesystem gmail

  # Live mode (execute actions)
  python orchestrator.py --vault ./AI_Employee_Vault --live

  # With custom Gmail query
  python orchestrator.py --vault ./AI_Employee_Vault --watchers gmail --gmail-query "is:unread"
        '''
    )

    parser.add_argument(
        '--vault',
        default='./AI_Employee_Vault',
        help='Path to Obsidian vault'
    )
    parser.add_argument(
        '--watchers',
        nargs='+',
        default=['filesystem'],
        choices=['filesystem', 'gmail', 'whatsapp', 'linkedin'],
        help='Watchers to enable'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Dry run mode (default: True)'
    )
    parser.add_argument(
        '--live',
        action='store_true',
        help='Live mode (execute actions)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Check interval in seconds'
    )
    parser.add_argument(
        '--gmail-credentials',
        default='./config/gmail_credentials.json',
        help='Path to Gmail credentials'
    )
    parser.add_argument(
        '--gmail-query',
        default='is:unread is:important',
        help='Gmail search query'
    )
    parser.add_argument(
        '--whatsapp-session',
        default='./config/whatsapp_session',
        help='Path to WhatsApp session'
    )
    parser.add_argument(
        '--linkedin-session',
        default='./config/linkedin_session',
        help='Path to LinkedIn session'
    )
    parser.add_argument(
        '--scheduler-config',
        default='./config/orchestrator.yaml',
        help='Path to scheduler YAML config (default: ./config/orchestrator.yaml)'
    )

    # Reasoning loop arguments
    parser.add_argument(
        '--enable-reasoning-loop',
        action='store_true',
        default=True,
        help='Enable reasoning loop for task processing (default: True)'
    )
    parser.add_argument(
        '--disable-reasoning-loop',
        action='store_true',
        help='Disable reasoning loop'
    )
    parser.add_argument(
        '--max-loop-iterations',
        type=int,
        default=10,
        help='Max iterations per reasoning loop (default: 10)'
    )
    parser.add_argument(
        '--loop-timeout',
        type=int,
        default=300,
        help='Per-iteration timeout in seconds (default: 300)'
    )
    parser.add_argument(
        '--task-process-interval',
        type=int,
        default=30,
        help='Seconds between task processing checks (default: 30)'
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create config
    config = OrchestratorConfig(
        vault_path=args.vault,
        dry_run=not args.live,
        enabled_watchers=args.watchers,
        check_interval=args.interval,
        gmail_credentials=args.gmail_credentials,
        gmail_query=args.gmail_query,
        whatsapp_session=args.whatsapp_session,
        linkedin_session=args.linkedin_session,
        scheduler_config_path=args.scheduler_config,
        enable_reasoning_loop=not args.disable_reasoning_loop,
        max_loop_iterations=args.max_loop_iterations,
        loop_timeout_seconds=args.loop_timeout,
        task_process_interval=args.task_process_interval
    )

    # Create and run orchestrator
    orchestrator = Orchestrator(config)

    # Handle signals
    def signal_handler(signum, frame):
        orchestrator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run
    print("\n" + "=" * 50)
    print("AI EMPLOYEE ORCHESTRATOR")
    print("=" * 50)
    print(f"Vault: {args.vault}")
    print(f"Watchers: {', '.join(args.watchers)}")
    print(f"Mode: {'DRY RUN' if config.dry_run else 'LIVE'}")
    print(f"Reasoning Loop: {'ENABLED' if config.enable_reasoning_loop else 'DISABLED'}")
    if config.enable_reasoning_loop:
        print(f"  - Max iterations: {config.max_loop_iterations}")
        print(f"  - Timeout: {config.loop_timeout_seconds}s per iteration")
        print(f"  - Task check interval: {config.task_process_interval}s")
    print(f"Scheduler Config: {config.scheduler_config_path}")
    print("=" * 50)
    print("\nPress Ctrl+C to stop\n")

    orchestrator.run()


if __name__ == '__main__':
    main()
