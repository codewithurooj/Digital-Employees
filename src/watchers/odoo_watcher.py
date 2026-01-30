"""
Odoo Watcher - Monitor Odoo for new invoices and payments.

Extends BaseWatcher to poll Odoo via XML-RPC and create action files
for new/updated invoices and payments.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from .base_watcher import BaseWatcher
from src.lib.odoo_client import OdooClient, OdooConnectionError, OdooAuthenticationError
from src.models import Invoice, Payment


class OdooWatcher(BaseWatcher):
    """
    Watcher for Odoo accounting events.

    Monitors Odoo for:
    - New/updated invoices
    - New/updated payments
    - Creates action files in Needs_Action for processing
    """

    def __init__(
        self,
        vault_path: str,
        config_path: str,
        check_interval: int = 300,
    ):
        """
        Initialize Odoo watcher.

        Args:
            vault_path: Path to the Obsidian vault
            config_path: Path to odoo_config.json
            check_interval: Seconds between checks (default: 5 minutes)
        """
        super().__init__(
            vault_path=vault_path,
            check_interval=check_interval,
            watcher_name="OdooWatcher"
        )

        self.config_path = Path(config_path)
        self._client: Optional[OdooClient] = None
        self._last_sync: Optional[datetime] = None
        self._circuit_open = False
        self._failure_count = 0
        self._max_failures = 5
        self._circuit_reset_time: Optional[datetime] = None

        # Vault paths for accounting
        self.invoices_path = self.vault_path / "Accounting" / "Invoices"
        self.payments_path = self.vault_path / "Accounting" / "Payments"
        self.transactions_path = self.vault_path / "Accounting" / "Transactions"

        # Ensure directories exist
        self.invoices_path.mkdir(parents=True, exist_ok=True)
        self.payments_path.mkdir(parents=True, exist_ok=True)
        self.transactions_path.mkdir(parents=True, exist_ok=True)

        # Load last sync time
        self._load_sync_state()

    def _load_sync_state(self) -> None:
        """Load last sync timestamp from config."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    last_sync = config.get("last_sync")
                    if last_sync:
                        self._last_sync = datetime.fromisoformat(last_sync)
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(f"Failed to load sync state: {e}")

    def _save_sync_state(self) -> None:
        """Save last sync timestamp to config."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)

                config["last_sync"] = datetime.utcnow().isoformat()

                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2)
            except Exception as e:
                self.logger.warning(f"Failed to save sync state: {e}")

    def _get_client(self) -> OdooClient:
        """Get or create Odoo client."""
        if self._client is None:
            self._client = OdooClient.from_config(self.config_path)
        return self._client

    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker allows requests."""
        if not self._circuit_open:
            return True

        # Check if circuit should reset
        if self._circuit_reset_time and datetime.utcnow() >= self._circuit_reset_time:
            self._circuit_open = False
            self._failure_count = 0
            self.logger.info("Circuit breaker reset")
            return True

        return False

    def _record_failure(self) -> None:
        """Record a failure and potentially open circuit breaker."""
        self._failure_count += 1
        if self._failure_count >= self._max_failures:
            self._circuit_open = True
            self._circuit_reset_time = datetime.utcnow() + timedelta(minutes=10)
            self.logger.warning(
                f"Circuit breaker opened after {self._failure_count} failures. "
                f"Will reset at {self._circuit_reset_time}"
            )

    def _record_success(self) -> None:
        """Record a success and reset failure count."""
        self._failure_count = 0

    def check_for_updates(self) -> list[Any]:
        """
        Check Odoo for new invoices and payments.

        Returns:
            List of Invoice and Payment objects to process
        """
        # Check circuit breaker
        if not self._check_circuit_breaker():
            self.logger.info("Circuit breaker open, skipping Odoo check")
            return []

        items = []

        try:
            client = self._get_client()

            # Authenticate if needed
            if not client.is_connected:
                client.authenticate()

            # Fetch invoices since last sync
            since = self._last_sync or datetime.utcnow() - timedelta(days=7)
            invoices = client.search_invoices(since=since)
            items.extend(invoices)

            self.logger.info(f"Found {len(invoices)} invoices since {since}")

            # Fetch payments since last sync
            payments = client.search_payments(since=since)
            items.extend(payments)

            self.logger.info(f"Found {len(payments)} payments since {since}")

            # Update sync state
            self._save_sync_state()
            self._record_success()

        except OdooAuthenticationError as e:
            self.logger.error(f"Odoo authentication failed: {e}")
            self._record_failure()
            self.log_action("auth_error", {"error": str(e)})

        except OdooConnectionError as e:
            self.logger.error(f"Odoo connection failed: {e}")
            self._record_failure()
            self.log_action("connection_error", {"error": str(e)})

        except Exception as e:
            self.logger.error(f"Unexpected error checking Odoo: {e}")
            self._record_failure()
            self.log_action("error", {"error": str(e)})

        return items

    def create_action_file(self, item: Any) -> Path:
        """
        Create action file and save to vault.

        For invoices and payments, we:
        1. Save the record to the appropriate accounting folder
        2. Create an action file if it needs human attention

        Args:
            item: Invoice or Payment object

        Returns:
            Path to created file
        """
        if isinstance(item, Invoice):
            return self._process_invoice(item)
        elif isinstance(item, Payment):
            return self._process_payment(item)
        else:
            raise ValueError(f"Unknown item type: {type(item)}")

    def _process_invoice(self, invoice: Invoice) -> Path:
        """Process and save an invoice."""
        # Save invoice to vault
        invoice_path = self.invoices_path / invoice.vault_filename
        invoice_path.write_text(invoice.to_markdown(), encoding="utf-8")

        self.logger.info(f"Saved invoice to {invoice_path}")

        # Create action file for unpaid invoices that are past due
        from datetime import date
        if invoice.payment_state == "not_paid" and invoice.due_date < date.today():
            action_path = self._create_invoice_action(invoice, "overdue")
            return action_path

        # Create action file for new draft invoices
        if invoice.state == "draft":
            action_path = self._create_invoice_action(invoice, "draft_review")
            return action_path

        return invoice_path

    def _create_invoice_action(self, invoice: Invoice, action_type: str) -> Path:
        """Create an action file for an invoice."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"INVOICE_{action_type.upper()}_{invoice.number.replace('/', '-')}_{timestamp}.md"
        action_path = self.needs_action / filename

        content = f"""---
type: invoice_action
action_type: {action_type}
source: odoo
priority: {'high' if action_type == 'overdue' else 'medium'}
created_at: {datetime.utcnow().isoformat()}
---

# Invoice Action Required: {invoice.number}

**Action Type**: {action_type.replace('_', ' ').title()}
**Customer**: {invoice.partner_name}
**Amount**: ${invoice.amount_total:,.2f}
**Due Date**: {invoice.due_date}
**Status**: {invoice.state.value} / {invoice.payment_state.value}

## Details

This invoice requires attention:

{"- **Overdue**: Payment is past the due date" if action_type == 'overdue' else ""}
{"- **Draft Review**: Invoice is in draft status and needs approval to send" if action_type == 'draft_review' else ""}

## Invoice Location

`Accounting/Invoices/{invoice.vault_filename}`

## Suggested Actions

{"1. Send payment reminder to customer" if action_type == 'overdue' else ""}
{"2. Review and follow up on outstanding balance" if action_type == 'overdue' else ""}
{"1. Review invoice details for accuracy" if action_type == 'draft_review' else ""}
{"2. Approve and post invoice for delivery" if action_type == 'draft_review' else ""}

---
*Created by OdooWatcher*
"""

        action_path.write_text(content, encoding="utf-8")
        return action_path

    def _process_payment(self, payment: Payment) -> Path:
        """Process and save a payment."""
        # Save payment to vault
        payment_path = self.payments_path / payment.vault_filename
        payment_path.write_text(payment.to_markdown(), encoding="utf-8")

        self.logger.info(f"Saved payment to {payment_path}")

        # Create action file for large payments that need review
        from decimal import Decimal
        import os

        threshold = Decimal(os.environ.get("REQUIRE_APPROVAL_THRESHOLD", "100"))
        if payment.amount >= threshold and payment.state == "draft":
            action_path = self._create_payment_action(payment)
            return action_path

        return payment_path

    def _create_payment_action(self, payment: Payment) -> Path:
        """Create an action file for a payment needing approval."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"PAYMENT_REVIEW_{payment.name.replace('/', '-')}_{timestamp}.md"
        action_path = self.needs_action / filename

        payment_direction = "from" if payment.payment_type == "inbound" else "to"

        content = f"""---
type: payment_action
action_type: approval_required
source: odoo
priority: high
created_at: {datetime.utcnow().isoformat()}
requires_approval: true
---

# Payment Approval Required: {payment.name}

**Type**: {payment.payment_type.value.title()}
**{payment_direction.title()}**: {payment.partner_name}
**Amount**: ${payment.amount:,.2f}
**Date**: {payment.payment_date}
**Status**: {payment.state.value}

## Details

This payment requires human approval before processing:

- Amount exceeds auto-approval threshold
- Please review payment details and approve or reject

## Payment Location

`Accounting/Payments/{payment.vault_filename}`

## Actions

- [ ] Review payment details
- [ ] Verify recipient/source
- [ ] Approve or reject

---
*Created by OdooWatcher*
"""

        action_path.write_text(content, encoding="utf-8")
        return action_path

    def poll_invoices(self) -> list[Invoice]:
        """
        Poll Odoo for invoices only.

        Returns:
            List of Invoice objects
        """
        if not self._check_circuit_breaker():
            return []

        try:
            client = self._get_client()
            if not client.is_connected:
                client.authenticate()

            since = self._last_sync or datetime.utcnow() - timedelta(days=7)
            return client.search_invoices(since=since)

        except Exception as e:
            self.logger.error(f"Failed to poll invoices: {e}")
            self._record_failure()
            return []

    def poll_payments(self) -> list[Payment]:
        """
        Poll Odoo for payments only.

        Returns:
            List of Payment objects
        """
        if not self._check_circuit_breaker():
            return []

        try:
            client = self._get_client()
            if not client.is_connected:
                client.authenticate()

            since = self._last_sync or datetime.utcnow() - timedelta(days=7)
            return client.search_payments(since=since)

        except Exception as e:
            self.logger.error(f"Failed to poll payments: {e}")
            self._record_failure()
            return []

    def get_status(self) -> dict[str, Any]:
        """Get watcher status including Odoo connection info."""
        status = super().get_status()
        status.update({
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "circuit_open": self._circuit_open,
            "failure_count": self._failure_count,
            "odoo_connected": self._client.is_connected if self._client else False,
        })
        return status
