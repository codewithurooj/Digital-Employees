"""Payment model for Odoo accounting integration."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PaymentType(str, Enum):
    """Direction of payment."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class PaymentMethodType(str, Enum):
    """Payment method type."""
    MANUAL = "manual"
    CHECK = "check"
    BANK_TRANSFER = "bank_transfer"


class PaymentStatus(str, Enum):
    """Payment status in Odoo."""
    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"


class Payment(BaseModel):
    """Odoo payment record synced to vault."""

    # Odoo identifiers
    odoo_id: int = Field(gt=0, description="Odoo record ID")
    name: str = Field(min_length=1, description="Payment reference")

    # Partner info
    partner_id: int = Field(gt=0)
    partner_name: str

    # Payment details
    payment_type: PaymentType
    payment_date: date
    journal_id: int
    journal_name: str

    # Amount
    currency: str = "USD"
    amount: Decimal = Field(gt=0)

    # State and reconciliation
    state: PaymentStatus = PaymentStatus.DRAFT
    reconciled_invoice_ids: list[int] = Field(default_factory=list)

    # Sync metadata
    synced_at: datetime
    source: str = "odoo"

    # Optional fields
    memo: Optional[str] = None
    payment_method: PaymentMethodType = PaymentMethodType.MANUAL

    def to_markdown(self) -> str:
        """Convert payment to vault markdown format."""
        type_display = "Customer Payment (Inbound)" if self.payment_type == PaymentType.INBOUND else "Supplier Payment (Outbound)"

        invoice_links = ", ".join([str(inv_id) for inv_id in self.reconciled_invoice_ids]) if self.reconciled_invoice_ids else "None"

        return f"""---
type: payment
source: {self.source}
odoo_id: {self.odoo_id}
name: "{self.name}"
partner_id: {self.partner_id}
partner_name: "{self.partner_name}"
payment_type: {self.payment_type.value}
payment_date: {self.payment_date.isoformat()}
journal_id: {self.journal_id}
journal_name: "{self.journal_name}"
currency: {self.currency}
amount: {self.amount}
state: {self.state.value}
reconciled_invoice_ids: {self.reconciled_invoice_ids}
synced_at: {self.synced_at.isoformat()}
---

# Payment: {self.name}

**From/To**: {self.partner_name}
**Date**: {self.payment_date}
**Type**: {type_display}
**Status**: {self.state.value.title()}

## Details

- Amount: ${self.amount:,.2f} {self.currency}
- Journal: {self.journal_name}
- Method: {self.payment_method.value.replace('_', ' ').title()}
- Applied to Invoices: {invoice_links}

{f"## Memo{chr(10)}{chr(10)}{self.memo}" if self.memo else ""}

## Notes

[Synced from Odoo on {self.synced_at.strftime('%Y-%m-%d')}]
"""

    @property
    def vault_filename(self) -> str:
        """Generate vault filename for this payment."""
        safe_name = self.name.replace("/", "-")
        return f"PAY-{safe_name}_{self.payment_date.isoformat()}.md"
