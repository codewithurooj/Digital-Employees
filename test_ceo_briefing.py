"""Test CEO Briefing Skill — generates weekly executive summary from vault data."""
import os
import sys
from pathlib import Path

os.environ['VAULT_PATH'] = './AI_Employee_Vault'
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 55)
print("CEO BRIEFING TEST")
print("=" * 55)
print("Generating executive briefing from vault data...\n")

from src.skills.ceo_briefing import CEOBriefingSkill

skill = CEOBriefingSkill(vault_path='./AI_Employee_Vault')

print("Running generate_briefing()...\n")
briefing = skill.generate_briefing()

print(f"Period       : {briefing.period_start} to {briefing.period_end}")
print(f"Generated at : {briefing.generated_at}")
print(f"Generator    : {briefing.generator} v{briefing.version}")
print()

metrics = briefing.metrics
print("METRICS:")
print(f"  Total Revenue   : ${metrics.total_revenue:,.2f}")
print(f"  Total Expenses  : ${metrics.total_expenses:,.2f}")
print(f"  Net Income      : ${metrics.net_income:,.2f}")
print(f"  Tasks Completed : {metrics.tasks_completed}")
print(f"  Tasks Pending   : {metrics.tasks_pending}")
print(f"  Bottlenecks     : {metrics.bottleneck_count}")
print(f"  Suggestions     : {metrics.suggestion_count}")
print()

if briefing.bottlenecks:
    print(f"BOTTLENECKS ({len(briefing.bottlenecks)}):")
    for b in briefing.bottlenecks:
        print(f"  - {b.description}")
    print()

if briefing.suggestions:
    print(f"SUGGESTIONS ({len(briefing.suggestions)}):")
    for s in briefing.suggestions:
        print(f"  - {s.title}: {s.description}")
    print()

if briefing.next_week_focus:
    print("NEXT WEEK FOCUS:")
    for f in briefing.next_week_focus:
        print(f"  - {f}")
    print()

# Check if briefing was saved to Briefings/
briefings_dir = Path('./AI_Employee_Vault/Briefings')
briefing_files = list(briefings_dir.glob('*.md')) if briefings_dir.exists() else []
print(f"Briefing files in Briefings/: {len(briefing_files)}")
for f in briefing_files[-3:]:
    print(f"  - {f.name}")

print()
print("=" * 55)
print("TEST COMPLETE")
print("Check AI_Employee_Vault/Briefings/ for the briefing file")
print("=" * 55)
