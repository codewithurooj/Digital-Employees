"""
Odoo Client Library - XML-RPC integration with Odoo Community Edition.

Provides authenticated access to Odoo models for accounting data sync.
Uses Python's built-in xmlrpc.client for zero external dependencies.
"""

import json
import logging
import xmlrpc.client
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from src.models import Invoice, InvoiceLine, InvoiceState, PaymentState
from src.models import Payment, PaymentType, PaymentStatus


class OdooConnectionError(Exception):
    """Raised when connection to Odoo fails."""
    pass


class OdooAuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class OdooClient:
    """
    Client for Odoo XML-RPC API.

    Provides methods to authenticate and access Odoo models
    for accounting integration (invoices, payments, accounts).
    """

    def __init__(
        self,
        url: str,
        database: str,
        username: str,
        api_key: str,
        timeout: int = 30,
    ):
        """
        Initialize Odoo client.

        Args:
            url: Odoo instance URL (e.g., https://mycompany.odoo.com)
            database: Odoo database name
            username: Odoo username
            api_key: API key (not password)
            timeout: Request timeout in seconds
        """
        self.url = url.rstrip("/")
        self.database = database
        self.username = username
        self.api_key = api_key
        self.timeout = timeout

        # Connection state
        self._uid: Optional[int] = None
        self._common: Optional[xmlrpc.client.ServerProxy] = None
        self._models: Optional[xmlrpc.client.ServerProxy] = None
        self._last_error: Optional[str] = None

        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1.0  # Exponential backoff base

        # Logger
        self.logger = logging.getLogger("OdooClient")

    @property
    def is_connected(self) -> bool:
        """Check if client is authenticated."""
        return self._uid is not None

    @property
    def uid(self) -> Optional[int]:
        """Get authenticated user ID."""
        return self._uid

    @property
    def last_error(self) -> Optional[str]:
        """Get last error message."""
        return self._last_error

    def authenticate(self) -> int:
        """
        Authenticate with Odoo and get user ID.

        Returns:
            User ID on success

        Raises:
            OdooAuthenticationError: If authentication fails
        """
        try:
            self._common = xmlrpc.client.ServerProxy(
                f"{self.url}/xmlrpc/2/common",
                allow_none=True,
            )

            self._uid = self._common.authenticate(
                self.database,
                self.username,
                self.api_key,
                {}
            )

            if not self._uid:
                raise OdooAuthenticationError(
                    f"Authentication failed for user {self.username}"
                )

            # Initialize models proxy
            self._models = xmlrpc.client.ServerProxy(
                f"{self.url}/xmlrpc/2/object",
                allow_none=True,
            )

            self.logger.info(f"Authenticated as user {self._uid}")
            self._last_error = None
            return self._uid

        except xmlrpc.client.Fault as e:
            self._last_error = str(e)
            raise OdooAuthenticationError(f"XML-RPC fault: {e}")
        except Exception as e:
            self._last_error = str(e)
            raise OdooConnectionError(f"Connection failed: {e}")

    def _ensure_connected(self) -> None:
        """Ensure client is authenticated."""
        if not self.is_connected:
            self.authenticate()

    def _execute(
        self,
        model: str,
        method: str,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute a method on an Odoo model with retry logic.

        Args:
            model: Odoo model name (e.g., 'account.move')
            method: Method to call (e.g., 'search_read')
            *args: Positional arguments for the method
            **kwargs: Keyword arguments for the method

        Returns:
            Method result

        Raises:
            OdooConnectionError: If execution fails after retries
        """
        self._ensure_connected()

        last_error = None
        for attempt in range(self.max_retries):
            try:
                result = self._models.execute_kw(
                    self.database,
                    self._uid,
                    self.api_key,
                    model,
                    method,
                    args,
                    kwargs,
                )
                self._last_error = None
                return result

            except xmlrpc.client.Fault as e:
                last_error = f"XML-RPC fault: {e}"
                self.logger.warning(f"Attempt {attempt + 1} failed: {last_error}")

            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"Attempt {attempt + 1} failed: {last_error}")

            # Exponential backoff
            if attempt < self.max_retries - 1:
                import time
                delay = self.retry_delay * (2 ** attempt)
                time.sleep(delay)

        self._last_error = last_error
        raise OdooConnectionError(f"Failed after {self.max_retries} attempts: {last_error}")

    def test_connection(self) -> dict[str, Any]:
        """
        Test connection and return server info.

        Returns:
            Dict with version and server info
        """
        try:
            self._ensure_connected()
            version = self._common.version()
            return {
                "status": "connected",
                "uid": self._uid,
                "server_version": version.get("server_version", "unknown"),
                "protocol_version": version.get("protocol_version", 1),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def search_invoices(
        self,
        since: Optional[datetime] = None,
        states: Optional[list[str]] = None,
        limit: int = 100,
    ) -> list[Invoice]:
        """
        Search for invoices in Odoo.

        Args:
            since: Only fetch invoices modified after this datetime
            states: Filter by invoice states (default: ['posted'])
            limit: Maximum number of invoices to return

        Returns:
            List of Invoice objects
        """
        domain = [
            ["move_type", "in", ["out_invoice", "out_refund"]],
        ]

        if states:
            domain.append(["state", "in", states])
        else:
            domain.append(["state", "=", "posted"])

        if since:
            domain.append(["write_date", ">=", since.isoformat()])

        fields = [
            "name",
            "partner_id",
            "invoice_date",
            "invoice_date_due",
            "state",
            "payment_state",
            "currency_id",
            "amount_untaxed",
            "amount_tax",
            "amount_total",
            "amount_residual",
            "invoice_line_ids",
        ]

        records = self._execute(
            "account.move",
            "search_read",
            domain,
            fields=fields,
            limit=limit,
            order="write_date desc",
        )

        invoices = []
        for rec in records:
            try:
                # Fetch line items
                lines = self._get_invoice_lines(rec.get("invoice_line_ids", []))

                invoice = Invoice(
                    odoo_id=rec["id"],
                    number=rec["name"],
                    partner_id=rec["partner_id"][0] if rec.get("partner_id") else 0,
                    partner_name=rec["partner_id"][1] if rec.get("partner_id") else "Unknown",
                    invoice_date=date.fromisoformat(rec["invoice_date"]) if rec.get("invoice_date") else date.today(),
                    due_date=date.fromisoformat(rec["invoice_date_due"]) if rec.get("invoice_date_due") else date.today(),
                    state=InvoiceState(rec.get("state", "draft")),
                    payment_state=PaymentState(rec.get("payment_state", "not_paid")),
                    currency=rec["currency_id"][1] if rec.get("currency_id") else "USD",
                    amount_untaxed=Decimal(str(rec.get("amount_untaxed", 0))),
                    amount_tax=Decimal(str(rec.get("amount_tax", 0))),
                    amount_total=Decimal(str(rec.get("amount_total", 0))),
                    amount_residual=Decimal(str(rec.get("amount_residual", 0))),
                    lines=lines,
                    synced_at=datetime.utcnow(),
                )
                invoices.append(invoice)
            except Exception as e:
                self.logger.warning(f"Failed to parse invoice {rec.get('name')}: {e}")

        return invoices

    def _get_invoice_lines(self, line_ids: list[int]) -> list[InvoiceLine]:
        """Fetch invoice line items."""
        if not line_ids:
            return []

        fields = ["name", "quantity", "price_unit", "price_subtotal", "product_id"]

        lines = self._execute(
            "account.move.line",
            "search_read",
            [["id", "in", line_ids], ["display_type", "=", False]],
            fields=fields,
        )

        return [
            InvoiceLine(
                description=line.get("name", ""),
                quantity=Decimal(str(line.get("quantity", 1))),
                unit_price=Decimal(str(line.get("price_unit", 0))),
                amount=Decimal(str(line.get("price_subtotal", 0))),
                product_id=line["product_id"][0] if line.get("product_id") else None,
            )
            for line in lines
        ]

    def search_payments(
        self,
        since: Optional[datetime] = None,
        payment_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[Payment]:
        """
        Search for payments in Odoo.

        Args:
            since: Only fetch payments modified after this datetime
            payment_type: Filter by payment type ('inbound' or 'outbound')
            limit: Maximum number of payments to return

        Returns:
            List of Payment objects
        """
        domain = []

        if payment_type:
            domain.append(["payment_type", "=", payment_type])

        if since:
            domain.append(["write_date", ">=", since.isoformat()])

        fields = [
            "name",
            "partner_id",
            "payment_type",
            "date",
            "journal_id",
            "currency_id",
            "amount",
            "state",
            "reconciled_invoice_ids",
            "memo",
        ]

        records = self._execute(
            "account.payment",
            "search_read",
            domain,
            fields=fields,
            limit=limit,
            order="date desc",
        )

        payments = []
        for rec in records:
            try:
                payment = Payment(
                    odoo_id=rec["id"],
                    name=rec.get("name", ""),
                    partner_id=rec["partner_id"][0] if rec.get("partner_id") else 0,
                    partner_name=rec["partner_id"][1] if rec.get("partner_id") else "Unknown",
                    payment_type=PaymentType(rec.get("payment_type", "inbound")),
                    payment_date=date.fromisoformat(rec["date"]) if rec.get("date") else date.today(),
                    journal_id=rec["journal_id"][0] if rec.get("journal_id") else 0,
                    journal_name=rec["journal_id"][1] if rec.get("journal_id") else "Unknown",
                    currency=rec["currency_id"][1] if rec.get("currency_id") else "USD",
                    amount=Decimal(str(rec.get("amount", 0))),
                    state=PaymentStatus(rec.get("state", "draft")),
                    reconciled_invoice_ids=rec.get("reconciled_invoice_ids", []),
                    synced_at=datetime.utcnow(),
                    memo=rec.get("memo"),
                )
                payments.append(payment)
            except Exception as e:
                self.logger.warning(f"Failed to parse payment {rec.get('name')}: {e}")

        return payments

    def get_account_balances(self) -> dict[str, Decimal]:
        """
        Get current account balances.

        Returns:
            Dict mapping account code to balance
        """
        # Fetch account balances
        fields = ["code", "name", "current_balance"]

        accounts = self._execute(
            "account.account",
            "search_read",
            [["deprecated", "=", False]],
            fields=fields,
            limit=500,
        )

        balances = {}
        for acc in accounts:
            code = acc.get("code", "")
            balance = Decimal(str(acc.get("current_balance", 0)))
            if balance != 0:  # Only include accounts with balance
                balances[code] = balance

        return balances

    @classmethod
    def from_config(cls, config_path: Path) -> "OdooClient":
        """
        Create OdooClient from config file.

        Args:
            config_path: Path to odoo_config.json

        Returns:
            Configured OdooClient instance
        """
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        return cls(
            url=config["url"],
            database=config["database"],
            username=config["username"],
            api_key=config["api_key"],
        )
