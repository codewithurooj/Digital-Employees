"""
CEO Briefing Skill - Generate weekly executive summary reports.

This skill aggregates data from the vault to generate comprehensive
CEO briefings covering revenue, expenses, tasks, bottlenecks, and suggestions.

Usage:
    from src.skills import CEOBriefingSkill

    skill = CEOBriefingSkill(vault_path='./AI_Employee_Vault')

    # Generate weekly briefing
    briefing = skill.generate_briefing()

    # Get just revenue summary
    revenue = skill.get_revenue_summary()

Features:
- Revenue aggregation from Accounting/Invoices/
- Expense tracking from Accounting/Payments/
- Task completion scanning from Done/
- Bottleneck detection from Needs_Action/
- Business goal progress from Business_Goals.md
- Proactive optimization suggestions
"""

import logging
import re
import yaml
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from src.models import (
    CEOBriefing,
    BriefingMetrics,
    RevenueSource,
    ExpenseCategory,
    OutstandingInvoice,
    Bottleneck,
    Suggestion,
    GoalProgress,
)


class CEOBriefingSkill:
    """
    Skill for generating weekly CEO briefings.

    Aggregates vault data to produce executive summaries with
    financial metrics, task tracking, bottleneck identification,
    and proactive suggestions.
    """

    def __init__(
        self,
        vault_path: str,
        timeout: int = 600,
    ):
        """
        Initialize CEO Briefing skill.

        Args:
            vault_path: Path to the Obsidian vault
            timeout: Maximum generation time in seconds
        """
        self.vault_path = Path(vault_path)
        self.timeout = timeout

        # Vault paths
        self.invoices_path = self.vault_path / "Accounting" / "Invoices"
        self.payments_path = self.vault_path / "Accounting" / "Payments"
        self.done_path = self.vault_path / "Done"
        self.needs_action_path = self.vault_path / "Needs_Action"
        self.briefings_path = self.vault_path / "Briefings"
        self.business_goals_path = self.vault_path / "Business_Goals.md"

        # Ensure briefings directory exists
        self.briefings_path.mkdir(parents=True, exist_ok=True)

        # Logger
        self.logger = logging.getLogger("CEOBriefingSkill")

    def _parse_frontmatter(self, content: str) -> dict[str, Any]:
        """Extract YAML frontmatter from markdown file."""
        match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if match:
            try:
                return yaml.safe_load(match.group(1)) or {}
            except yaml.YAMLError:
                return {}
        return {}

    def get_revenue_summary(
        self,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> dict[str, Any]:
        """
        Aggregate revenue from invoices.

        Args:
            period_start: Start of period (default: 7 days ago)
            period_end: End of period (default: today)

        Returns:
            Dict with revenue sources and totals
        """
        if period_end is None:
            period_end = date.today()
        if period_start is None:
            period_start = period_end - timedelta(days=7)

        total_revenue = Decimal("0")
        outstanding_total = Decimal("0")
        sources: dict[str, Decimal] = {}
        outstanding: list[OutstandingInvoice] = []

        # Scan invoice files
        if self.invoices_path.exists():
            for file_path in self.invoices_path.glob("*.md"):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    fm = self._parse_frontmatter(content)

                    # Check if in period
                    inv_date_str = fm.get("invoice_date", "")
                    if inv_date_str:
                        inv_date = date.fromisoformat(str(inv_date_str))
                        if not (period_start <= inv_date <= period_end):
                            continue

                    amount = Decimal(str(fm.get("amount_total", 0)))
                    residual = Decimal(str(fm.get("amount_residual", 0)))
                    payment_state = fm.get("payment_state", "")
                    partner = fm.get("partner_name", "Unknown")

                    # Track by source (using partner as proxy for source)
                    source_key = partner[:20] if partner else "Other"
                    sources[source_key] = sources.get(source_key, Decimal("0")) + amount
                    total_revenue += amount

                    # Track outstanding
                    if payment_state in ("not_paid", "partial") and residual > 0:
                        due_date_str = fm.get("due_date", "")
                        due = date.fromisoformat(str(due_date_str)) if due_date_str else date.today()
                        outstanding.append(OutstandingInvoice(
                            number=fm.get("number", "Unknown"),
                            partner=partner,
                            amount=residual,
                            due_date=due,
                        ))
                        outstanding_total += residual

                except Exception as e:
                    self.logger.warning(f"Error parsing invoice {file_path}: {e}")

        # Convert to RevenueSource objects
        revenue_sources = [
            RevenueSource(name=name, amount=amount)
            for name, amount in sorted(sources.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        return {
            "total_revenue": total_revenue,
            "outstanding_total": outstanding_total,
            "sources": revenue_sources,
            "outstanding_invoices": sorted(outstanding, key=lambda x: x.due_date)[:5],
        }

    def get_expense_summary(
        self,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> dict[str, Any]:
        """
        Aggregate expenses from payments.

        Args:
            period_start: Start of period (default: 7 days ago)
            period_end: End of period (default: today)

        Returns:
            Dict with expense categories and totals
        """
        if period_end is None:
            period_end = date.today()
        if period_start is None:
            period_start = period_end - timedelta(days=7)

        total_expenses = Decimal("0")
        categories: dict[str, Decimal] = {}

        # Scan payment files
        if self.payments_path.exists():
            for file_path in self.payments_path.glob("*.md"):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    fm = self._parse_frontmatter(content)

                    # Only outbound payments are expenses
                    if fm.get("payment_type") != "outbound":
                        continue

                    # Check if in period
                    pay_date_str = fm.get("payment_date", "")
                    if pay_date_str:
                        pay_date = date.fromisoformat(str(pay_date_str))
                        if not (period_start <= pay_date <= period_end):
                            continue

                    amount = Decimal(str(fm.get("amount", 0)))
                    journal = fm.get("journal_name", "Other")

                    # Categorize by journal (simplified)
                    categories[journal] = categories.get(journal, Decimal("0")) + amount
                    total_expenses += amount

                except Exception as e:
                    self.logger.warning(f"Error parsing payment {file_path}: {e}")

        # Convert to ExpenseCategory objects
        expense_categories = [
            ExpenseCategory(name=name, amount=amount)
            for name, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True)
        ]

        return {
            "total_expenses": total_expenses,
            "categories": expense_categories,
        }

    def get_task_summary(
        self,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> dict[str, Any]:
        """
        Scan completed tasks from Done folder.

        Args:
            period_start: Start of period (default: 7 days ago)
            period_end: End of period (default: today)

        Returns:
            Dict with task counts and highlights
        """
        if period_end is None:
            period_end = date.today()
        if period_start is None:
            period_start = period_end - timedelta(days=7)

        completed = 0
        pending = 0
        highlights: list[str] = []

        # Count completed tasks
        if self.done_path.exists():
            for file_path in self.done_path.glob("*.md"):
                try:
                    # Check file modification time for period
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime).date()
                    if period_start <= mtime <= period_end:
                        completed += 1
                        # Extract title for highlights
                        content = file_path.read_text(encoding="utf-8")
                        lines = content.split("\n")
                        for line in lines:
                            if line.startswith("# "):
                                highlights.append(line[2:].strip())
                                break
                except Exception as e:
                    self.logger.warning(f"Error scanning done file {file_path}: {e}")

        # Count pending tasks
        if self.needs_action_path.exists():
            pending = len(list(self.needs_action_path.glob("*.md")))

        return {
            "completed": completed,
            "pending": pending,
            "highlights": highlights[:5],  # Top 5 highlights
        }

    def get_bottlenecks(self, age_threshold_hours: int = 48) -> list[Bottleneck]:
        """
        Identify bottlenecks from aged items in Needs_Action.

        Args:
            age_threshold_hours: Consider items older than this as bottlenecks

        Returns:
            List of Bottleneck objects
        """
        bottlenecks: list[Bottleneck] = []
        threshold = datetime.now() - timedelta(hours=age_threshold_hours)

        if self.needs_action_path.exists():
            for file_path in self.needs_action_path.glob("*.md"):
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < threshold:
                        age_days = (datetime.now() - mtime).days

                        # Parse file for context
                        content = file_path.read_text(encoding="utf-8")
                        fm = self._parse_frontmatter(content)

                        title = file_path.stem.replace("_", " ")
                        priority = fm.get("priority", "medium")

                        # Determine impact and recommendation based on type
                        action_type = fm.get("type", "unknown")
                        if "invoice" in action_type.lower():
                            impact = "Potential revenue delay"
                            recommendation = "Review and send invoice or follow up"
                        elif "payment" in action_type.lower():
                            impact = "Cash flow impact"
                            recommendation = "Process payment or escalate"
                        else:
                            impact = "Workflow delay"
                            recommendation = "Review and take action"

                        bottlenecks.append(Bottleneck(
                            title=title[:50],
                            age_days=age_days,
                            impact=impact,
                            location="Needs_Action",
                            recommendation=recommendation,
                        ))

                except Exception as e:
                    self.logger.warning(f"Error analyzing bottleneck {file_path}: {e}")

        # Sort by age (oldest first) and return top 5
        return sorted(bottlenecks, key=lambda x: x.age_days, reverse=True)[:5]

    def generate_suggestions(
        self,
        revenue_data: dict[str, Any],
        expense_data: dict[str, Any],
    ) -> list[Suggestion]:
        """
        Generate proactive optimization suggestions.

        Args:
            revenue_data: Output from get_revenue_summary
            expense_data: Output from get_expense_summary

        Returns:
            List of Suggestion objects
        """
        suggestions: list[Suggestion] = []

        # Check for outstanding invoices
        outstanding = revenue_data.get("outstanding_invoices", [])
        if len(outstanding) >= 3:
            total_outstanding = sum(inv.amount for inv in outstanding)
            suggestions.append(Suggestion(
                title="Follow Up on Outstanding Invoices",
                potential_savings=total_outstanding * Decimal("0.05"),  # 5% potential recovery
                description=f"You have {len(outstanding)} outstanding invoices totaling ${total_outstanding:,.2f}. "
                           "Consider implementing payment reminders or early payment discounts.",
                action="Review outstanding invoices and send payment reminders to overdue accounts.",
            ))

        # Check expense categories for optimization
        categories = expense_data.get("categories", [])
        for cat in categories:
            if cat.amount > Decimal("1000"):
                suggestions.append(Suggestion(
                    title=f"Review {cat.name} Expenses",
                    description=f"${cat.amount:,.2f} spent on {cat.name} this period. "
                               "Consider reviewing for cost optimization opportunities.",
                    action=f"Audit {cat.name} expenses for potential savings.",
                ))
                break  # Only one expense suggestion

        # Revenue diversification
        sources = revenue_data.get("sources", [])
        if len(sources) == 1 and sources[0].amount > Decimal("5000"):
            suggestions.append(Suggestion(
                title="Diversify Revenue Sources",
                description="Revenue is concentrated in a single source. "
                           "Consider expanding customer base to reduce risk.",
                action="Identify 2-3 potential new customers or revenue streams.",
            ))

        return suggestions[:3]  # Max 3 suggestions

    def get_goal_progress(self) -> list[GoalProgress]:
        """
        Compare actual performance against Business_Goals.md.

        Returns:
            List of GoalProgress objects
        """
        goals: list[GoalProgress] = []

        if not self.business_goals_path.exists():
            return goals

        try:
            content = self.business_goals_path.read_text(encoding="utf-8")

            # Simple parsing - look for goal patterns
            # Expected format: "- **Goal Name**: Target X, Current Y"
            lines = content.split("\n")
            for line in lines:
                if "**" in line and ":" in line:
                    # Extract goal name
                    match = re.search(r'\*\*([^*]+)\*\*:\s*(.+)', line)
                    if match:
                        goal_name = match.group(1).strip()
                        details = match.group(2).strip()

                        # Try to extract target and actual
                        target = "TBD"
                        actual = "TBD"
                        status = "Unknown"

                        if "target" in details.lower():
                            target_match = re.search(r'target[:\s]+([^,]+)', details, re.IGNORECASE)
                            if target_match:
                                target = target_match.group(1).strip()

                        goals.append(GoalProgress(
                            goal=goal_name,
                            target=target,
                            actual=actual,
                            status=status,
                        ))

        except Exception as e:
            self.logger.warning(f"Error parsing business goals: {e}")

        return goals[:5]  # Max 5 goals

    def generate_briefing(
        self,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> CEOBriefing:
        """
        Generate complete CEO briefing.

        Args:
            period_start: Start of period (default: 7 days ago)
            period_end: End of period (default: today/Sunday)

        Returns:
            CEOBriefing object
        """
        if period_end is None:
            period_end = date.today()
        if period_start is None:
            period_start = period_end - timedelta(days=7)

        self.logger.info(f"Generating CEO briefing for {period_start} to {period_end}")

        # Gather data
        revenue_data = self.get_revenue_summary(period_start, period_end)
        expense_data = self.get_expense_summary(period_start, period_end)
        task_data = self.get_task_summary(period_start, period_end)
        bottlenecks = self.get_bottlenecks()
        suggestions = self.generate_suggestions(revenue_data, expense_data)
        goals = self.get_goal_progress()

        # Calculate metrics
        total_revenue = revenue_data["total_revenue"]
        total_expenses = expense_data["total_expenses"]
        net_income = total_revenue - total_expenses

        metrics = BriefingMetrics(
            total_revenue=total_revenue,
            total_expenses=total_expenses,
            net_income=net_income,
            tasks_completed=task_data["completed"],
            tasks_pending=task_data["pending"],
            bottleneck_count=len(bottlenecks),
            suggestion_count=len(suggestions),
        )

        # Build briefing
        briefing = CEOBriefing(
            period_start=period_start,
            period_end=period_end,
            metrics=metrics,
            revenue_sources=revenue_data["sources"],
            outstanding_invoices=revenue_data["outstanding_invoices"],
            expense_categories=expense_data["categories"],
            task_highlights=task_data["highlights"],
            bottlenecks=bottlenecks,
            suggestions=suggestions,
            goal_progress=goals,
            next_week_focus=[
                f"Clear {len(bottlenecks)} bottleneck{'s' if len(bottlenecks) != 1 else ''}" if bottlenecks else "Maintain momentum",
                f"Follow up on ${revenue_data['outstanding_total']:,.2f} outstanding" if revenue_data["outstanding_total"] > 0 else "Continue revenue growth",
                "Review and implement suggestions" if suggestions else "Identify optimization opportunities",
            ],
        )

        # Save to vault
        briefing_path = self.briefings_path / briefing.vault_filename
        briefing_path.write_text(briefing.to_markdown(), encoding="utf-8")

        self.logger.info(f"CEO briefing saved to {briefing_path}")

        return briefing

    def get_status(self) -> dict[str, Any]:
        """Get skill status."""
        return {
            "name": "CEOBriefingSkill",
            "vault_path": str(self.vault_path),
            "timeout": self.timeout,
            "paths_exist": {
                "invoices": self.invoices_path.exists(),
                "payments": self.payments_path.exists(),
                "done": self.done_path.exists(),
                "needs_action": self.needs_action_path.exists(),
                "business_goals": self.business_goals_path.exists(),
            },
        }
