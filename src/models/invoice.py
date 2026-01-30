"""Invoice model for Odoo accounting integration."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class InvoiceState(str, Enum):
    """Invoice state in Odoo."""
    DRAFT = "draft"
    POSTED = "posted"
    CANCEL = "cancel"


class PaymentState(str, Enum):
    """Payment state for invoices."""
    NOT_PAID = "not_paid"
    PARTIAL = "partial"
    PAID = "paid"
    REVERSED = "reversed"


class InvoiceLine(BaseModel):
    """Line item on an invoice."""
    description: str
    quantity: Decimal = Field(ge=0)
    unit_price: Decimal = Field(ge=0)
    amount: Decimal = Field(ge=0)
    product_id: Optional[int] = None
    tax_ids: list[int] = Field(default_factory=list)

    @property
    def computed_amount(self) -> Decimal:
        """Calculate line amount."""
        return self.quantity * self.unit_price


class Invoice(BaseModel):
    """Odoo invoice synced to vault."""

    # Odoo identifiers
    odoo_id: int = Field(gt=0, description="Odoo record ID")
    number: str = Field(min_length=1, description="Invoice number")

    # Partner info
    partner_id: int = Field(gt=0)
    partner_name: str

    # Dates
    invoice_date: date
    due_date: date

    # State
    state: InvoiceState = InvoiceState.DRAFT
    payment_state: PaymentState = PaymentState.NOT_PAID

    # Amounts
    currency: str = "USD"
    amount_untaxed: Decimal = Field(ge=0)
    amount_tax: Decimal = Field(ge=0)
    amount_total: Decimal = Field(ge=0)
    amount_residual: Decimal = Field(ge=0)

    # Line items
    lines: list[InvoiceLine] = Field(default_factory=list)

    # Sync metadata
    synced_at: datetime
    source: str = "odoo"

    @field_validator("amount_residual")
    @classmethod
    def validate_residual(cls, v: Decimal, info) -> Decimal:
        """Ensure residual doesn't exceed total."""
        if "amount_total" in info.data and v > info.data["amount_total"]:
            raise ValueError("amount_residual cannot exceed amount_total")
        return v

    def to_markdown(self) -> str:
        """Convert invoice to vault markdown format."""
        lines_table = "\n".join([
            f"| {line.description} | {line.quantity} | ${line.unit_price:,.2f} | ${line.amount:,.2f} |"
            for line in self.lines
        ]) if self.lines else "| No line items | - | - | - |"

        return f"""---
type: invoice
source: {self.source}
odoo_id: {self.odoo_id}
number: "{self.number}"
partner_id: {self.partner_id}
partner_name: "{self.partner_name}"
invoice_date: {self.invoice_date.isoformat()}
due_date: {self.due_date.isoformat()}
state: {self.state.value}
payment_state: {self.payment_state.value}
currency: {self.currency}
amount_untaxed: {self.amount_untaxed}
amount_tax: {self.amount_tax}
amount_total: {self.amount_total}
amount_residual: {self.amount_residual}
synced_at: {self.synced_at.isoformat()}
---

# Invoice: {self.number}

**Customer**: {self.partner_name}
**Date**: {self.invoice_date}
**Due**: {self.due_date}
**Status**: {self.state.value.title()} ({self.payment_state.value.replace('_', ' ').title()})

## Line Items

| Description | Quantity | Unit Price | Amount |
|-------------|----------|------------|--------|
{lines_table}

## Totals

- Subtotal: ${self.amount_untaxed:,.2f}
- Tax: ${self.amount_tax:,.2f}
- **Total Due**: ${self.amount_total:,.2f}
- **Remaining**: ${self.amount_residual:,.2f}

## Notes

[Synced from Odoo on {self.synced_at.strftime('%Y-%m-%d')}]
"""

    @property
    def vault_filename(self) -> str:
        """Generate vault filename for this invoice."""
        safe_number = self.number.replace("/", "-")
        return f"INV-{safe_number}_{self.invoice_date.isoformat()}.md"
