"""Integration tests for Odoo draft invoice flow (T061)."""

import pytest
from pathlib import Path


class TestOdooDraftFlow:
    """Tests for cloud-safe Odoo draft operations."""

    def test_create_draft_invoice(self, tmp_path):
        from src.cloud.cloud_odoo_mcp import CloudOdooMCP

        mcp = CloudOdooMCP(vault_path=str(tmp_path))
        result = mcp.create_draft_invoice(
            partner_name="Acme Corp",
            lines=[
                {"description": "Consulting", "quantity": 10, "unit_price": 150.00},
                {"description": "Development", "quantity": 5, "unit_price": 200.00},
            ],
            notes="Net 30 terms",
        )
        assert result["success"] is True
        assert "draft_id" in result

    def test_draft_creates_approval_request(self, tmp_path):
        from src.cloud.cloud_odoo_mcp import CloudOdooMCP

        mcp = CloudOdooMCP(vault_path=str(tmp_path))
        mcp.create_draft_invoice(
            partner_name="Test Client",
            lines=[{"description": "Service", "quantity": 1, "unit_price": 500.00}],
        )
        approval_files = list(
            (tmp_path / "Pending_Approval" / "accounting").glob("*.md")
        )
        assert len(approval_files) >= 1

    def test_draft_calculates_total(self, tmp_path):
        from src.cloud.cloud_odoo_mcp import CloudOdooMCP

        mcp = CloudOdooMCP(vault_path=str(tmp_path))
        result = mcp.create_draft_invoice(
            partner_name="Client",
            lines=[
                {"description": "Item A", "quantity": 2, "unit_price": 100.00},
                {"description": "Item B", "quantity": 3, "unit_price": 50.00},
            ],
        )
        assert result["success"] is True
        assert result["amount_total"] == "350.00"

    def test_draft_rejects_empty_lines(self, tmp_path):
        from src.cloud.cloud_odoo_mcp import CloudOdooMCP

        mcp = CloudOdooMCP(vault_path=str(tmp_path))
        result = mcp.create_draft_invoice(
            partner_name="Client",
            lines=[],
        )
        assert result["success"] is False

    def test_draft_logs_action(self, tmp_path):
        from src.cloud.cloud_odoo_mcp import CloudOdooMCP

        mcp = CloudOdooMCP(vault_path=str(tmp_path))
        mcp.create_draft_invoice(
            partner_name="Client",
            lines=[{"description": "Test", "quantity": 1, "unit_price": 100.00}],
        )
        log_files = list((tmp_path / "Logs").glob("*.jsonl"))
        assert len(log_files) >= 1
