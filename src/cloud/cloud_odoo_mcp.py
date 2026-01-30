"""Cloud-safe Odoo MCP wrapper for draft-only operations.

This wrapper ensures the cloud agent can only create draft invoices
without posting them to Odoo. Actual posting requires local agent approval.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CloudOdooMCP:
    """Cloud-safe Odoo MCP that only creates drafts.

    This wraps Odoo operations to ensure the cloud agent
    can never post invoices or payments directly.
    """

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.invoices_path = self.vault_path / "Accounting" / "Invoices"
        self.pending_path = self.vault_path / "Pending_Approval" / "accounting"
        self.logs_path = self.vault_path / "Logs"

        self.invoices_path.mkdir(parents=True, exist_ok=True)
        self.pending_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)

    def create_draft_invoice(
        self,
        partner_name: str,
        lines: list[dict[str, Any]],
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a draft invoice file and approval request.

        This NEVER posts to Odoo. It only creates local files
        for the local agent to review and post.

        Args:
            partner_name: Customer/partner name
            lines: List of line items with description, quantity, unit_price
            notes: Optional notes

        Returns:
            Dict with success, draft_id, amount_total, etc.
        """
        if not lines:
            return {
                "success": False,
                "error": "Invoice must have at least one line item",
            }

        if not partner_name or not partner_name.strip():
            return {
                "success": False,
                "error": "Partner name is required",
            }

        timestamp = datetime.now()
        draft_id = f"DRAFT-{timestamp.strftime('%Y%m%d%H%M%S')}"

        total = Decimal("0")
        line_details = []
        for line in lines:
            qty = Decimal(str(line.get("quantity", 1)))
            price = Decimal(str(line.get("unit_price", 0)))
            amount = qty * price
            total += amount
            line_details.append({
                "description": line.get("description", ""),
                "quantity": str(qty),
                "unit_price": str(price),
                "amount": str(amount),
            })

        invoice_content = f"""---
type: invoice_draft
draft_id: {draft_id}
status: pending_approval
partner_name: "{partner_name}"
amount_total: {total}
created_at: {timestamp.isoformat()}
source_agent: cloud
requires_local_action: true
---

# Invoice Draft: {draft_id}

**Customer**: {partner_name}
**Created**: {timestamp.strftime('%Y-%m-%d %H:%M')}
**Status**: Pending Approval

## Line Items

| Description | Quantity | Unit Price | Amount |
|-------------|----------|------------|--------|
"""
        for line in line_details:
            invoice_content += (
                f"| {line['description']} "
                f"| {line['quantity']} "
                f"| ${Decimal(line['unit_price']):,.2f} "
                f"| ${Decimal(line['amount']):,.2f} |\n"
            )

        invoice_content += f"""
## Totals

- **Total**: ${total:,.2f}

"""
        if notes:
            invoice_content += f"## Notes\n\n{notes}\n\n"

        invoice_content += """---

**Action Required**: Review and approve this draft to create invoice in Odoo.

*Created by Cloud Agent (draft-only mode)*
"""

        invoice_path = self.invoices_path / f"{draft_id}.md"
        invoice_path.write_text(invoice_content, encoding="utf-8")

        approval_content = f"""---
type: approval_request
domain: accounting
action: create_invoice
draft_id: {draft_id}
partner_name: "{partner_name}"
amount_total: {total}
urgency: normal
created: {timestamp.isoformat()}
source_agent: cloud
requires_local_action: true
---

# Approval Request: Create Invoice

**Draft ID**: {draft_id}
**Customer**: {partner_name}
**Amount**: ${total:,.2f}

## Summary

Cloud agent has created a draft invoice for {partner_name}.
Review and approve to post to Odoo.

## Invoice Details

See: [[Accounting/Invoices/{draft_id}.md]]

## Approve/Reject

- [ ] I have reviewed this invoice
- [ ] I approve posting to Odoo

---
*Created by Cloud Agent at {timestamp.isoformat()}*
"""
        approval_path = self.pending_path / f"approve_{draft_id}.md"
        approval_path.write_text(approval_content, encoding="utf-8")

        self._log_action("create_draft_invoice", {
            "draft_id": draft_id,
            "partner": partner_name,
            "amount_total": str(total),
            "line_count": len(lines),
        })

        return {
            "success": True,
            "draft_id": draft_id,
            "amount_total": f"{total:.2f}",
            "invoice_path": str(invoice_path),
            "approval_path": str(approval_path),
        }

    def _log_action(self, action: str, details: dict[str, Any]) -> None:
        """Log action to daily log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_path / f"{today}.jsonl"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "component": "cloud_odoo_mcp",
            "action": action,
            "details": details,
        }

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
