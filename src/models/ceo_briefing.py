"""CEOBriefing model for weekly executive summary reports."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RevenueSource(BaseModel):
    """Revenue breakdown by source."""
    name: str
    amount: Decimal
    previous_amount: Optional[Decimal] = None

    @property
    def change_percent(self) -> Optional[float]:
        """Calculate percentage change from previous period."""
        if self.previous_amount is None or self.previous_amount == 0:
            return None
        return float((self.amount - self.previous_amount) / self.previous_amount * 100)


class ExpenseCategory(BaseModel):
    """Expense breakdown by category."""
    name: str
    amount: Decimal
    budget: Optional[Decimal] = None

    @property
    def budget_status(self) -> str:
        """Determine budget status."""
        if self.budget is None:
            return "No budget"
        if self.amount <= self.budget * Decimal("0.9"):
            return "Under budget"
        elif self.amount <= self.budget:
            return "On budget"
        return "Over budget"


class OutstandingInvoice(BaseModel):
    """Invoice awaiting payment."""
    number: str
    partner: str
    amount: Decimal
    due_date: date


class Bottleneck(BaseModel):
    """Identified workflow bottleneck."""
    title: str
    age_days: int
    impact: str
    location: str  # folder path
    recommendation: str


class Suggestion(BaseModel):
    """Proactive optimization suggestion."""
    title: str
    potential_savings: Optional[Decimal] = None
    description: str
    action: str


class GoalProgress(BaseModel):
    """Progress toward business goal."""
    goal: str
    target: str
    actual: str
    status: str  # On Track, Exceeding, Needs Attention


class BriefingMetrics(BaseModel):
    """Summary metrics for the briefing."""
    total_revenue: Decimal = Field(ge=0)
    total_expenses: Decimal = Field(ge=0)
    net_income: Decimal = Field(default=Decimal("0"))
    tasks_completed: int = Field(ge=0)
    tasks_pending: int = Field(ge=0)
    bottleneck_count: int = Field(ge=0)
    suggestion_count: int = Field(ge=0)


class CEOBriefing(BaseModel):
    """Weekly CEO briefing report."""

    # Period
    period_start: date
    period_end: date

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generator: str = "ceo_briefing_skill"
    version: str = "1.0"

    # Summary metrics
    metrics: BriefingMetrics

    # Revenue details
    revenue_sources: list[RevenueSource] = Field(default_factory=list)
    outstanding_invoices: list[OutstandingInvoice] = Field(default_factory=list)

    # Expense details
    expense_categories: list[ExpenseCategory] = Field(default_factory=list)

    # Task tracking
    task_highlights: list[str] = Field(default_factory=list)

    # Issues
    bottlenecks: list[Bottleneck] = Field(default_factory=list, max_length=5)

    # Recommendations
    suggestions: list[Suggestion] = Field(default_factory=list, min_length=0)

    # Goals
    goal_progress: list[GoalProgress] = Field(default_factory=list)

    # Focus areas
    next_week_focus: list[str] = Field(default_factory=list)

    @field_validator("period_end")
    @classmethod
    def validate_period_end(cls, v: date, info) -> date:
        """Ensure period_end is after period_start."""
        if "period_start" in info.data and v < info.data["period_start"]:
            raise ValueError("period_end must be after period_start")
        return v

    def to_markdown(self) -> str:
        """Convert briefing to vault markdown format."""
        # Revenue table
        revenue_rows = "\n".join([
            f"| {r.name} | ${r.amount:,.2f} | {f'+{r.change_percent:.0f}%' if r.change_percent and r.change_percent > 0 else f'{r.change_percent:.0f}%' if r.change_percent else 'N/A'} |"
            for r in self.revenue_sources
        ]) if self.revenue_sources else "| No revenue data | - | - |"

        # Outstanding invoices
        invoice_list = "\n".join([
            f"- {i.number} - {i.partner} - ${i.amount:,.2f} (Due: {i.due_date.strftime('%b %d')})"
            for i in self.outstanding_invoices
        ]) if self.outstanding_invoices else "- No outstanding invoices"

        # Expense table
        expense_rows = "\n".join([
            f"| {e.name} | ${e.amount:,.2f} | {e.budget_status} |"
            for e in self.expense_categories
        ]) if self.expense_categories else "| No expense data | - | - |"

        # Task highlights
        highlights = "\n".join([f"- {h}" for h in self.task_highlights]) if self.task_highlights else "- No highlights this week"

        # Bottlenecks
        bottleneck_sections = ""
        for i, b in enumerate(self.bottlenecks, 1):
            bottleneck_sections += f"""
### {i}. {b.title}
- **Age**: {b.age_days} days in {b.location}
- **Impact**: {b.impact}
- **Recommendation**: {b.recommendation}
"""

        # Suggestions
        suggestion_sections = ""
        for i, s in enumerate(self.suggestions, 1):
            savings = f"\n**Potential Savings**: ${s.potential_savings:,.2f}/month" if s.potential_savings else ""
            suggestion_sections += f"""
### {i}. {s.title}
{savings}

{s.description}

**Action**: {s.action}
"""

        # Goals table
        goals_rows = "\n".join([
            f"| {g.goal} | {g.target} | {g.actual} | {g.status} |"
            for g in self.goal_progress
        ]) if self.goal_progress else "| No goals defined | - | - | - |"

        # Next week focus
        focus_list = "\n".join([f"{i}. {f}" for i, f in enumerate(self.next_week_focus, 1)]) if self.next_week_focus else "1. Review this briefing and set priorities"

        completion_rate = (
            round(self.metrics.tasks_completed / (self.metrics.tasks_completed + self.metrics.tasks_pending) * 100)
            if (self.metrics.tasks_completed + self.metrics.tasks_pending) > 0
            else 0
        )

        return f"""---
type: ceo_briefing
period_start: {self.period_start.isoformat()}
period_end: {self.period_end.isoformat()}
generated_at: {self.generated_at.isoformat()}
generator: {self.generator}
version: "{self.version}"
sections:
  - revenue_summary
  - expense_summary
  - task_completion
  - bottlenecks
  - suggestions
metrics:
  total_revenue: {self.metrics.total_revenue}
  total_expenses: {self.metrics.total_expenses}
  net_income: {self.metrics.net_income}
  tasks_completed: {self.metrics.tasks_completed}
  tasks_pending: {self.metrics.tasks_pending}
  bottleneck_count: {self.metrics.bottleneck_count}
  suggestion_count: {self.metrics.suggestion_count}
---

# CEO Briefing: Week of {self.period_start.strftime('%B %d')} - {self.period_end.strftime('%d, %Y')}

**Generated**: {self.generated_at.strftime('%A, %B %d, %Y at %I:%M %p')}
**Period**: {self.period_start.strftime('%B %d')} - {self.period_end.strftime('%B %d, %Y')}

---

## Executive Summary

This week showed {'strong' if self.metrics.net_income > 0 else 'challenging'} financial performance with ${self.metrics.total_revenue:,.2f} in revenue against ${self.metrics.total_expenses:,.2f} in expenses, yielding a net income of ${self.metrics.net_income:,.2f}. Task completion rate was {completion_rate}% ({self.metrics.tasks_completed}/{self.metrics.tasks_completed + self.metrics.tasks_pending} tasks), with {self.metrics.bottleneck_count} bottleneck{'s' if self.metrics.bottleneck_count != 1 else ''} requiring attention.

---

## Revenue Summary

| Source | Amount | vs. Last Week |
|--------|--------|---------------|
{revenue_rows}
| **Total** | **${self.metrics.total_revenue:,.2f}** | - |

### Outstanding Invoices

{invoice_list}

---

## Expense Summary

| Category | Amount | vs. Budget |
|----------|--------|------------|
{expense_rows}
| **Total** | **${self.metrics.total_expenses:,.2f}** | - |

---

## Task Completion

**Completed This Week**: {self.metrics.tasks_completed} tasks
**Still Pending**: {self.metrics.tasks_pending} tasks
**Completion Rate**: {completion_rate}%

### Highlights

{highlights}

---

## Bottlenecks
{bottleneck_sections if bottleneck_sections else "*No significant bottlenecks identified this week.*"}

---

## Proactive Suggestions
{suggestion_sections if suggestion_sections else "*No suggestions generated this week.*"}

---

## Goals Progress (from Business_Goals.md)

| Goal | Target | Actual | Status |
|------|--------|--------|--------|
{goals_rows}

---

## Next Week Focus

{focus_list}

---

*This briefing was automatically generated by the AI Employee.*
*Review and verify all figures before taking action.*
"""

    @property
    def vault_filename(self) -> str:
        """Generate vault filename for this briefing."""
        # Briefings are named after the Monday following the period
        return f"{self.period_end.isoformat()}_Monday_Briefing.md"
