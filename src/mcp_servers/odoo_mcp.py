"""
Odoo MCP Server - Accounting integration with Odoo Community Edition.

This MCP server provides accounting capabilities for the AI Employee system.
Syncs invoices, payments, and account balances from Odoo to the vault.

Usage:
    from src.mcp_servers import OdooMCP

    server = OdooMCP(
        vault_path='./AI_Employee_Vault',
        config_path='./config/odoo_config.json'
    )

    # Sync invoices
    result = server.sync_invoices()

    # Get health status
    status = server.health()

Tools provided:
- health: Check Odoo connection status
- sync_invoices: Fetch and save invoices to vault
- sync_payments: Fetch and save payments to vault
- create_draft_invoice: Create a new draft invoice
- get_account_balances: Get current account balances
- get_daily_transactions: Generate daily transaction log
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from src.cloud.work_zone import requires_local
from src.lib.odoo_client import OdooClient, OdooConnectionError, OdooAuthenticationError
from src.models import (
    Invoice, Payment, Transaction, TransactionEntry,
    InvoiceState, PaymentState, PaymentType,
)
from src.utils.retry_handler import RateLimiter, CircuitBreaker


# Rate limit: 100 requests per hour
REQUESTS_PER_HOUR = 100


@dataclass
class OdooResult:
    """Result of an Odoo operation."""
    success: bool
    action: str
    data: Optional[Any] = None
    count: int = 0
    error: Optional[str] = None
    error_type: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "success": self.success,
            "action": self.action,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.data is not None:
            result["data"] = self.data
        if self.count:
            result["count"] = self.count
        if self.error:
            result["error"] = self.error
            result["error_type"] = self.error_type
        return result


class OdooMCP:
    """
    Odoo MCP Server for accounting integration.

    Provides tools to sync accounting data from Odoo to the vault
    and perform basic accounting operations.
    """

    def __init__(
        self,
        vault_path: str,
        config_path: str,
        dry_run: bool = True,
        agent_zone=None,
    ):
        """
        Initialize Odoo MCP server.

        Args:
            vault_path: Path to the Obsidian vault
            config_path: Path to odoo_config.json
            dry_run: If True, don't make changes to Odoo (only sync)
            agent_zone: WorkZone enum value for work-zone enforcement
        """
        self.agent_zone = agent_zone
        self.vault_path = Path(vault_path)
        self.config_path = Path(config_path)
        self.dry_run = dry_run

        # Vault paths
        self.invoices_path = self.vault_path / "Accounting" / "Invoices"
        self.payments_path = self.vault_path / "Accounting" / "Payments"
        self.transactions_path = self.vault_path / "Accounting" / "Transactions"
        self.logs_path = self.vault_path / "Logs"

        # Ensure directories exist
        self.invoices_path.mkdir(parents=True, exist_ok=True)
        self.payments_path.mkdir(parents=True, exist_ok=True)
        self.transactions_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)

        # Client (lazy initialization)
        self._client: Optional[OdooClient] = None

        # Rate limiter and circuit breaker
        self._rate_limiter = RateLimiter(
            max_calls=REQUESTS_PER_HOUR,
            period=3600,
        )
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            reset_timeout=600,
        )

        # Logger
        self.logger = logging.getLogger("OdooMCP")

    def _get_client(self) -> OdooClient:
        """Get or create Odoo client."""
        if self._client is None:
            self._client = OdooClient.from_config(self.config_path)
        return self._client

    def _check_rate_limit(self) -> bool:
        """Check if we can make a request."""
        return self._rate_limiter.can_proceed()

    def _log_action(self, action: str, details: dict[str, Any]) -> None:
        """Log an action to the daily log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_path / f"{today}.jsonl"

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "component": "odoo_mcp",
            "action_type": action,
            "details": details,
        }

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    def health(self) -> OdooResult:
        """
        Check Odoo connection health.

        Returns:
            OdooResult with connection status
        """
        try:
            client = self._get_client()
            info = client.test_connection()

            if info.get("status") == "connected":
                self._log_action("health_check", {"status": "healthy", **info})
                return OdooResult(
                    success=True,
                    action="health",
                    data=info,
                )
            else:
                self._log_action("health_check", {"status": "unhealthy", **info})
                return OdooResult(
                    success=False,
                    action="health",
                    error=info.get("error", "Connection failed"),
                    error_type="connection_error",
                )

        except Exception as e:
            self._log_action("health_check", {"status": "error", "error": str(e)})
            return OdooResult(
                success=False,
                action="health",
                error=str(e),
                error_type="exception",
            )

    def sync_invoices(
        self,
        since_days: int = 7,
        limit: int = 100,
    ) -> OdooResult:
        """
        Sync invoices from Odoo to vault.

        Args:
            since_days: Fetch invoices from last N days
            limit: Maximum number of invoices

        Returns:
            OdooResult with sync statistics
        """
        if not self._check_rate_limit():
            return OdooResult(
                success=False,
                action="sync_invoices",
                error="Rate limit exceeded",
                error_type="rate_limit",
            )

        if not self._circuit_breaker.can_execute():
            return OdooResult(
                success=False,
                action="sync_invoices",
                error="Circuit breaker open",
                error_type="circuit_breaker",
            )

        try:
            client = self._get_client()
            if not client.is_connected:
                client.authenticate()

            since = datetime.utcnow() - timedelta(days=since_days)
            invoices = client.search_invoices(since=since, limit=limit)

            # Save to vault
            saved_count = 0
            for invoice in invoices:
                try:
                    file_path = self.invoices_path / invoice.vault_filename
                    file_path.write_text(invoice.to_markdown(), encoding="utf-8")
                    saved_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to save invoice {invoice.number}: {e}")

            self._circuit_breaker.record_success()
            self._log_action("sync_invoices", {
                "fetched": len(invoices),
                "saved": saved_count,
                "since_days": since_days,
            })

            return OdooResult(
                success=True,
                action="sync_invoices",
                count=saved_count,
                data={
                    "fetched": len(invoices),
                    "saved": saved_count,
                    "path": str(self.invoices_path),
                },
            )

        except (OdooConnectionError, OdooAuthenticationError) as e:
            self._circuit_breaker.record_failure()
            self._log_action("sync_invoices", {"error": str(e)})
            return OdooResult(
                success=False,
                action="sync_invoices",
                error=str(e),
                error_type="odoo_error",
            )

        except Exception as e:
            self._circuit_breaker.record_failure()
            self._log_action("sync_invoices", {"error": str(e)})
            return OdooResult(
                success=False,
                action="sync_invoices",
                error=str(e),
                error_type="exception",
            )

    def sync_payments(
        self,
        since_days: int = 7,
        limit: int = 100,
    ) -> OdooResult:
        """
        Sync payments from Odoo to vault.

        Args:
            since_days: Fetch payments from last N days
            limit: Maximum number of payments

        Returns:
            OdooResult with sync statistics
        """
        if not self._check_rate_limit():
            return OdooResult(
                success=False,
                action="sync_payments",
                error="Rate limit exceeded",
                error_type="rate_limit",
            )

        if not self._circuit_breaker.can_execute():
            return OdooResult(
                success=False,
                action="sync_payments",
                error="Circuit breaker open",
                error_type="circuit_breaker",
            )

        try:
            client = self._get_client()
            if not client.is_connected:
                client.authenticate()

            since = datetime.utcnow() - timedelta(days=since_days)
            payments = client.search_payments(since=since, limit=limit)

            # Save to vault
            saved_count = 0
            for payment in payments:
                try:
                    file_path = self.payments_path / payment.vault_filename
                    file_path.write_text(payment.to_markdown(), encoding="utf-8")
                    saved_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to save payment {payment.name}: {e}")

            self._circuit_breaker.record_success()
            self._log_action("sync_payments", {
                "fetched": len(payments),
                "saved": saved_count,
                "since_days": since_days,
            })

            return OdooResult(
                success=True,
                action="sync_payments",
                count=saved_count,
                data={
                    "fetched": len(payments),
                    "saved": saved_count,
                    "path": str(self.payments_path),
                },
            )

        except (OdooConnectionError, OdooAuthenticationError) as e:
            self._circuit_breaker.record_failure()
            self._log_action("sync_payments", {"error": str(e)})
            return OdooResult(
                success=False,
                action="sync_payments",
                error=str(e),
                error_type="odoo_error",
            )

        except Exception as e:
            self._circuit_breaker.record_failure()
            self._log_action("sync_payments", {"error": str(e)})
            return OdooResult(
                success=False,
                action="sync_payments",
                error=str(e),
                error_type="exception",
            )

    def create_draft_invoice(
        self,
        partner_name: str,
        lines: list[dict[str, Any]],
        notes: Optional[str] = None,
    ) -> OdooResult:
        """
        Create a draft invoice.

        Note: This only creates a local draft file for review.
        Actual Odoo invoice creation requires approval.

        Args:
            partner_name: Customer name
            lines: List of line items with description, quantity, unit_price
            notes: Optional notes

        Returns:
            OdooResult with draft info
        """
        if self.dry_run:
            # Create local draft only
            timestamp = datetime.utcnow()
            draft_id = f"DRAFT-{timestamp.strftime('%Y%m%d%H%M%S')}"

            # Calculate totals
            total = Decimal("0")
            for line in lines:
                qty = Decimal(str(line.get("quantity", 1)))
                price = Decimal(str(line.get("unit_price", 0)))
                total += qty * price

            draft_content = f"""---
type: invoice_draft
draft_id: {draft_id}
status: pending_approval
partner_name: "{partner_name}"
amount_total: {total}
created_at: {timestamp.isoformat()}
---

# Invoice Draft: {draft_id}

**Customer**: {partner_name}
**Created**: {timestamp.strftime('%Y-%m-%d %H:%M')}
**Status**: Pending Approval

## Line Items

| Description | Quantity | Unit Price | Amount |
|-------------|----------|------------|--------|
"""
            for line in lines:
                desc = line.get("description", "")
                qty = Decimal(str(line.get("quantity", 1)))
                price = Decimal(str(line.get("unit_price", 0)))
                amount = qty * price
                draft_content += f"| {desc} | {qty} | ${price:,.2f} | ${amount:,.2f} |\n"

            draft_content += f"""
## Totals

- **Total**: ${total:,.2f}

{f"## Notes{chr(10)}{chr(10)}{notes}" if notes else ""}

---

**Action Required**: Review and approve this draft to create invoice in Odoo.

*Created by OdooMCP in dry-run mode*
"""

            # Save draft
            draft_path = self.invoices_path / f"{draft_id}.md"
            draft_path.write_text(draft_content, encoding="utf-8")

            self._log_action("create_draft_invoice", {
                "draft_id": draft_id,
                "partner": partner_name,
                "amount": str(total),
                "dry_run": True,
            })

            return OdooResult(
                success=True,
                action="create_draft_invoice",
                data={
                    "draft_id": draft_id,
                    "path": str(draft_path),
                    "amount_total": str(total),
                    "dry_run": True,
                },
            )

        # Real Odoo invoice creation would go here
        # Requires HITL approval before execution
        return OdooResult(
            success=False,
            action="create_draft_invoice",
            error="Direct invoice creation not implemented - use approval workflow",
            error_type="not_implemented",
        )

    def get_account_balances(self) -> OdooResult:
        """
        Get current account balances from Odoo.

        Returns:
            OdooResult with account balances
        """
        if not self._check_rate_limit():
            return OdooResult(
                success=False,
                action="get_account_balances",
                error="Rate limit exceeded",
                error_type="rate_limit",
            )

        try:
            client = self._get_client()
            if not client.is_connected:
                client.authenticate()

            balances = client.get_account_balances()

            self._log_action("get_account_balances", {
                "account_count": len(balances),
            })

            return OdooResult(
                success=True,
                action="get_account_balances",
                count=len(balances),
                data={
                    "balances": {k: str(v) for k, v in balances.items()},
                },
            )

        except Exception as e:
            self._log_action("get_account_balances", {"error": str(e)})
            return OdooResult(
                success=False,
                action="get_account_balances",
                error=str(e),
                error_type="exception",
            )

    def get_daily_transactions(
        self,
        target_date: Optional[date] = None,
    ) -> OdooResult:
        """
        Generate daily transaction log from synced data.

        Args:
            target_date: Date to generate log for (default: today)

        Returns:
            OdooResult with transaction log path
        """
        if target_date is None:
            target_date = date.today()

        try:
            # Read invoices and payments for the date
            inbound_total = Decimal("0")
            outbound_total = Decimal("0")
            inbound_entries: list[TransactionEntry] = []
            outbound_entries: list[TransactionEntry] = []

            # Scan invoices for the date
            for invoice_file in self.invoices_path.glob("*.md"):
                if target_date.isoformat() in invoice_file.name:
                    content = invoice_file.read_text(encoding="utf-8")
                    # Parse amount from frontmatter
                    if "amount_total:" in content:
                        for line in content.split("\n"):
                            if line.startswith("amount_total:"):
                                amount = Decimal(line.split(":")[1].strip())
                                inbound_total += amount
                                break

            # Scan payments for the date
            for payment_file in self.payments_path.glob("*.md"):
                if target_date.isoformat() in payment_file.name:
                    content = payment_file.read_text(encoding="utf-8")
                    # Parse payment type and amount
                    is_inbound = "payment_type: inbound" in content
                    for line in content.split("\n"):
                        if line.startswith("amount:"):
                            amount = Decimal(line.split(":")[1].strip())
                            if is_inbound:
                                inbound_total += amount
                            else:
                                outbound_total += amount
                            break

            # Create transaction log
            transaction = Transaction(
                log_date=target_date,
                total_inbound=inbound_total,
                total_outbound=outbound_total,
                inbound_transactions=inbound_entries,
                outbound_transactions=outbound_entries,
                synced_at=datetime.utcnow(),
            )

            # Save to vault
            log_path = self.transactions_path / transaction.vault_filename
            log_path.write_text(transaction.to_markdown(), encoding="utf-8")

            self._log_action("get_daily_transactions", {
                "date": target_date.isoformat(),
                "inbound": str(inbound_total),
                "outbound": str(outbound_total),
            })

            return OdooResult(
                success=True,
                action="get_daily_transactions",
                data={
                    "date": target_date.isoformat(),
                    "path": str(log_path),
                    "total_inbound": str(inbound_total),
                    "total_outbound": str(outbound_total),
                    "net_change": str(inbound_total - outbound_total),
                },
            )

        except Exception as e:
            self._log_action("get_daily_transactions", {"error": str(e)})
            return OdooResult(
                success=False,
                action="get_daily_transactions",
                error=str(e),
                error_type="exception",
            )

    def get_status(self) -> dict[str, Any]:
        """Get MCP server status."""
        return {
            "name": "OdooMCP",
            "dry_run": self.dry_run,
            "rate_limiter": {
                "remaining": self._rate_limiter.remaining_calls,
                "reset_at": self._rate_limiter.reset_time.isoformat() if hasattr(self._rate_limiter, 'reset_time') else None,
            },
            "circuit_breaker": {
                "state": "open" if not self._circuit_breaker.can_execute() else "closed",
                "failures": getattr(self._circuit_breaker, '_failure_count', 0),
            },
            "vault_path": str(self.vault_path),
        }
